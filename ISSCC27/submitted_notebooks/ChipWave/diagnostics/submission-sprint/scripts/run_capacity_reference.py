"""Run one reference-module physical attempt using the existing public backend."""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from capacity_budget import finish, reserve
from study_protocol import digest, write_json
from study_portability import case_root

ROOT = Path(__file__).resolve().parents[1]
CASE = case_root(ROOT)
sys.path.append(str(CASE/"scripts"))
from benchmark_physical import prepare, postroute
from classify_study_failures import classify, read_reports
from collect_physical import collect
from run_frequency_search import collect_failed
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore


def execute_physical(output, manifest, task_name, integrated=True, *, physical_deadline=None):
    """Execute one prepared project; allocation and terminal accounting remain with the caller."""
    row = {}
    status = "failed"
    from capacity_process import remaining
    timeout=remaining(physical_deadline,14400)
    cmd = [sys.executable, "-m", "chip_nebula.cli.commands", "--project-root", str(output/"project"),
           "run", str(output/"project/.chip_nebula/recipes/benchmark-physical.yaml"),
           "--workflow", "benchmark-physical", "--workers", "1", "--resume"]
    with (output/"workflow.log").open("w") as log:
        process = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            row["timed_out"] = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            status = "timeout"
    post_started = time.monotonic()
    with StaticTaskGraphStore(output/"project/.chip_nebula/shared/memory/taskgraph-v2.db") as store:
        state = store.task_state("benchmark-physical:physical").value
        attempts = store.list_attempts("benchmark-physical:physical")
        if state == "satisfied":
            collect(output/"project", "benchmark-physical", output/"evidence")
        elif attempts:
            collect_failed(output/"project", attempts[-1], output/"evidence")
    raw, native, errors = read_reports(output/"evidence")
    unchanged = (digest(output/"project/physical/chip-nebula/constraints.sdc")==manifest["sdc_sha256"]
        and digest(output/"project/physical/chip-nebula/config.mk")==manifest["config_sha256"]
        and all(digest(output/"project"/p)==h for p,h in manifest["rtl_sha256"].items()))
    physical = dict(physical_qualified=process.returncode==0 and state=="satisfied" and not row.get("timed_out"),
                    task_state=state, frozen_inputs_unchanged=unchanged, failure_classes=errors)
    failures = classify(physical, raw, native)
    gate = None
    if physical["physical_qualified"] and not failures:
        remaining = 1800-(time.monotonic()-post_started)
        if remaining <= 0:
            raise subprocess.TimeoutExpired("postprocessing", 1800)
        with (output/"postroute-driver.log").open("w") as log:
            command = ([sys.executable, str(ROOT/"scripts/measure_capacity_integration.py"),
                "--run", str(output), "--task", task_name] if integrated else
                [sys.executable, str(Path(__file__).resolve()), "--postroute", task_name])
            child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                child.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
                raise
        if child.returncode == 0:
            gate = json.loads((output/"postroute/qualification.json").read_text())
    row.update(physical=physical, failure_classes=failures, raw_metrics=raw,
               native_summary=native, postroute=gate, exit_code=process.returncode,
               qualified=bool(physical["physical_qualified"] and not failures and unchanged
                              and gate and gate["passed"]))
    if row["qualified"]:
        status = "passed"
    return row, status


def run(task_name, integrated=False, calibration=False):
    if task_name not in ("A1", "A2", "B1", "B2"):
        raise ValueError("Unknown reference task")
    task = ROOT/"tasks"/task_name
    local = json.loads((task/"qualification/qualification.json").read_text())
    if not local["local_checks_passed"]:
        raise ValueError("Reference/checker/mutant prerequisite failed")
    meta = json.loads((task/"build.json").read_text())
    if any(digest(task/p)!=h for p,h in meta["source_sha256"].items()):
        raise ValueError("Task changed after its contract receipt")
    identity = ("reference-integration-" if integrated else "reference-module-") + task_name
    category = "reference_integration" if integrated else "reference_module"
    original_identity = identity
    if calibration:
        if not integrated:
            raise ValueError("This calibration entry targets CPU integrations")
        prior = json.loads((ROOT/"physical"/identity/"qualification.json").read_text())
        if prior["qualified"]:
            raise ValueError("Do not recalibrate an already qualified reference")
        identity = "calibration-integration-"+task_name
        category = "preformal_calibration"
    output = ROOT/"physical"/identity
    if output.exists():
        raise ValueError("Prior physical attempt is preserved")
    if integrated:
        from capacity_integration_physical import prepare as prepare_integration, verified_integration
        verified_integration(task_name)
        for receipt in ("integration-measurement.json", "integration-physical-preparation-v2.json"):
            if not json.loads((ROOT/"checks"/receipt).read_text())["passed"]:
                raise ValueError("Integrated measurement/configuration preflight failed")
    reserve(ROOT, category, identity, identity)
    output.mkdir(parents=True)
    started = time.monotonic()
    row = dict(identity=identity, task=task_name, qualified=False, period_ns=10.526 if integrated else 100,
               category=category, model_calls=0)
    if calibration:
        row["original_failed_reference"] = original_identity
    status = "failed"
    os.environ.update(ORFS_ROOT=str(CASE/"toolchain/orfs"), NUM_CORES="2")
    try:
        manifest = (prepare_integration(output/"project", task_name) if integrated else
                    prepare(output/"project", task, task/"grader/reference", period_ps=100000))
        write_json(output/"manifest.json", manifest)
        result, status = execute_physical(output, manifest, task_name, integrated,physical_deadline=started+14400)
        row.update(result)
    except Exception as error:
        import traceback
        (output/"error.log").write_text(traceback.format_exc())
        row.update(error_class=type(error).__name__, error=str(error))
        status = "timeout" if isinstance(error, subprocess.TimeoutExpired) else "infrastructure_error"
    row.update(status=status, total_seconds=time.monotonic()-started,
               integrated_95mhz_qualified=bool(integrated and row["qualified"]), scored_task_qualified=False)
    write_json(output/"qualification.json", row)
    finish(ROOT, identity, status, str((output/"qualification.json").relative_to(ROOT)))
    print(json.dumps({k:row[k] for k in ("identity","status","qualified","total_seconds")}),flush=True)
    return row


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task",choices=("A1","A2","B1","B2"))
    parser.add_argument("--postroute",choices=("A1","A2","B1","B2"))
    parser.add_argument("--integrated", action="store_true")
    parser.add_argument("--calibration", action="store_true")
    args=parser.parse_args()
    if args.postroute:
        output=ROOT/"physical"/("reference-module-"+args.postroute)
        row=postroute(ROOT/"tasks"/args.postroute,output/"evidence",output/"postroute")
        raise SystemExit(0 if row["passed"] else 1)
    if not args.task:
        parser.error("--task is required")
    row=run(args.task, args.integrated, args.calibration)
    raise SystemExit(0 if row["qualified"] else 1)

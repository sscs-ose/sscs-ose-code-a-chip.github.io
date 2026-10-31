#!/usr/bin/env python3
"""Fixed-port T09 functional scorer; PPA and delivery are separate gates."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

from t09_oracle_check import ELFS, ORACLES, run as run_oracles
from t09_timing_check import apply_timing_groups, run as run_timing

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DIRECTED = HERE / "t09_data" / "programs" / "directed"
RANDOM = HERE / "t09_data" / "programs" / "random"
from public_check import run as run_public
from score_run import load_rules, score_run

HAZARD_TEMPLATES = {"load_use_immediate", "load_to_branch",
                    "load_to_store_data", "both_sources_same_register"}
FLUSH_TEMPLATES = {"jal_link_flush", "jalr_lsb_x0",
                   "load_branch_flush_adjacent", "branch_target_misaligned"}


def group(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("empty T09 score group")
    return {"cases_passed": sum(bool(row["passed"]) for row in rows),
            "cases_total": len(rows)}


def run_script(name: str, submission: Path, work: Path) -> dict:
    output = work / f"{name}.json"
    command = [sys.executable, str(HERE / f"t09_{name}_check.py"),
               "--submission", str(submission), "--output", str(output)]
    executed = subprocess.run(command, text=True, capture_output=True, timeout=600)
    if not output.is_file():
        raise RuntimeError(f"{name} runner produced no result: " +
                           (executed.stdout + executed.stderr)[-1000:])
    result = json.loads(output.read_text())
    if name == "wait":
        if result.get("runs") != 80 or len(result.get("outcomes", [])) != 80:
            raise ValueError("T09 wait test count changed")
    elif result.get("cases_total") != len(result.get("outcomes", [])):
        raise ValueError(f"T09 {name} test count changed")
    return result


def run(submission: Path, seed: int, elapsed_seconds: float,
        delivery_qualified: bool,
        ppa_measurement: Path | None, ppa_reference: Path | None) -> dict:
    started = time.monotonic()
    diagnostics = {}
    with tempfile.TemporaryDirectory(prefix="ic_bcmk_t09_score_") as directory:
        work = Path(directory)
        suite_results = {}
        for name, oracle_root, elf_root in (("act", ORACLES, ELFS),
                                            ("directed", DIRECTED, DIRECTED),
                                            ("random", RANDOM, RANDOM)):
            with contextlib.redirect_stdout(io.StringIO()) as captured:
                result = run_oracles(submission, seed, None, oracle_root, elf_root,
                                     f"CPU-{name.upper()}")
            diagnostics[name] = {"phase": result.get("phase"),
                                 "cases_passed": result.get("cases_passed"),
                                 "cases_total": result.get("cases_total"),
                                 "error": result.get("error"),
                                 "log_tail": captured.getvalue()[-1500:]}
            if result.get("phase") not in {"run", "compile"}:
                raise RuntimeError(f"T09 {name} infrastructure failure: {result}")
            suite_results[name] = result
        if any(suite_results[name]["phase"] == "compile" for name in suite_results):
            raise ValueError("T09 candidate RTL does not compile in evaluator bus platform")
        directed_manifest = json.loads((DIRECTED / "MANIFEST.json").read_text())
        random_manifest = json.loads((RANDOM / "MANIFEST.json").read_text())
        by_directed = {row["elf"]: row for row in directed_manifest["cases"]}
        by_random = {row["elf"]: row for row in random_manifest["cases"]}
        if len(suite_results["directed"]["outcomes"]) != 108 or \
                len(suite_results["random"]["outcomes"]) != 100 or \
                len(suite_results["act"]["outcomes"]) != 45:
            raise RuntimeError("T09 frozen ACT4/directed/random program count changed")
        groups = {"CPU-ACT": group(suite_results["act"]["outcomes"])}
        for category in ("INT", "MEM", "HAZ", "TRAP", "CSR"):
            rows = [row for row in suite_results["directed"]["outcomes"]
                    if by_directed[row["elf"]]["group"] == category]
            groups[f"CPU-DIR-{category}"] = group(rows)
        for category in ("INT", "MEM", "TRAP"):
            rows = [row for row in suite_results["random"]["outcomes"]
                    if by_random[row["elf"]]["category"] == category]
            groups[f"CPU-DIFF-{category}"] = group(rows)
        hazards = [row for row in suite_results["directed"]["outcomes"]
                   if by_directed[row["elf"]]["template"] in HAZARD_TEMPLATES]
        flushes = [row for row in suite_results["directed"]["outcomes"]
                   if by_directed[row["elf"]]["template"] in FLUSH_TEMPLATES]
        groups["CPU-PIPE-HAZ"] = group(hazards)
        groups["CPU-PIPE-FLUSH"] = group(flushes)
        for name, score_group in (("wait", "CPU-PIPE-MEM"),
                                  ("reset", "CPU-PIPE-RESET"),
                                  ("spec", "CPU-DIR-TRAP")):
            result = run_script(name, submission, work)
            diagnostics[name] = {"cases_passed": result.get("passed", result.get("cases_passed")),
                                 "cases_total": result.get("runs", result.get("cases_total")),
                                 "first_failure": next((row for row in result["outcomes"]
                                                        if not row["passed"]), None)}
            if name == "spec":
                groups[score_group]["cases_passed"] += result["cases_passed"]
                groups[score_group]["cases_total"] += result["cases_total"]
            else:
                groups[score_group] = group(result["outcomes"])
        latency = run_public("T09", submission, seed, 8, 3, 4)
        diagnostics["latency"] = latency
        groups["CPU-PIPE-LAT"] = {"cases_passed": 64 if latency["passed"] else 0,
                                  "cases_total": 64}
        timing = run_timing(submission)
        diagnostics["timing_cycles"] = timing
        apply_timing_groups(groups, timing)
        diagnostics["pipeline_timing"] = {
            "method": "port_timing_v1_latency_throughput_paired_penalty_workload_budget",
            "latency_passed": groups["CPU-PIPE-LAT"]["cases_passed"] == 64,
            "timing_cases_passed": timing["cases_passed"],
            "timing_cases_total": timing["cases_total"],
            "scope": "observable timing only; internal stage boundaries are not claimed",
        }
    manifest = yaml.safe_load((ROOT / "benchmark/manifest.yaml").read_text())
    task = next(row for row in manifest["tasks"] if row["id"] == "T09")
    payload = {"task_id": "T09", "groups": groups,
               "elapsed_seconds": elapsed_seconds,
               "time_limit_seconds": task["time_limit_minutes"] * 60,
               "delivery_qualified": delivery_qualified}
    if ppa_measurement is not None and ppa_reference is not None:
        payload["ppa_measurement"] = json.loads(ppa_measurement.read_text())
        payload["ppa_reference"] = json.loads(ppa_reference.read_text())
    rules = load_rules()
    result = score_run(payload, rules)
    return {"task_id": "T09", "phase": "scored", "seed": seed,
            "scoring_policy": "t09_group_cycles10_v1",
            "elapsed_grading_seconds": round(time.monotonic() - started, 3),
            "groups": groups, "score": result, "diagnostics": diagnostics}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission", type=Path)
    parser.add_argument("--seed", type=int, default=20260925)
    parser.add_argument("--elapsed-seconds", type=float, required=True)
    parser.add_argument("--delivery-qualified", action="store_true")
    parser.add_argument("--ppa-measurement", type=Path)
    parser.add_argument("--ppa-reference", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if (args.ppa_measurement is None) != (args.ppa_reference is None):
        parser.error("both PPA measurement and reference are required")
    try:
        result = run(args.submission.resolve(), args.seed, args.elapsed_seconds,
                     args.delivery_qualified,
                     args.ppa_measurement, args.ppa_reference)
    except (OSError, ValueError, KeyError, RuntimeError,
            subprocess.SubprocessError) as exc:
        result = {"task_id": "T09", "phase": "infrastructure", "error": str(exc)}
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    else:
        print(json.dumps(result, indent=2))
    return 0 if result["phase"] == "scored" else 1


if __name__ == "__main__":
    raise SystemExit(main())

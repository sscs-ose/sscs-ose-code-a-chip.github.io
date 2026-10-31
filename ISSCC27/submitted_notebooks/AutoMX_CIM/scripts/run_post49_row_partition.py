"""Targeted TT PEX check of two sequential 2-row reads on the existing core.

This is a *new stimulus* for the passive 4x4 core, not an ADC or wrapper
sign-off. Each half is simulated from a fresh precharge; the integer partial
sums are combined digitally only after both analog reads. Existing receipts
and their hash-linked source files are never changed by this script.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import shutil
import subprocess

from automx_cim.spice import parse_measurements
from scripts.analyze_post49_decoder_architectures import (
    _nearest, _read_reports, observations,
)
from scripts.run_core_candidate_full_tt import (
    LOAD_FF, PWM_UNIT_PS, _checkpoint, _digest, _expected, _provenance,
    analyze_transfer,
)
from scripts.run_core_candidate_pex import make_pex_deck
from scripts.run_core_pex_coverage import Case


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("results/sky130/post49_row_partition")
PARTITIONS = {
    "adjacent": ((0, 1), (2, 3)),
    "interleaved": ((0, 2), (1, 3)),
    "crossed": ((0, 3), (1, 2)),
}


def select_hard_cases(reports: dict, max_cases: int = 16) -> list[dict]:
    """Rank known-level scalar errors using training only; retain old cases.

    The old 16 were previously inspected and are *not* a fresh holdout. Their
    inclusion here is only to diagnose a proposed circuit change cheaply.
    """
    if max_cases < 4:
        raise ValueError("at least four cases are needed for the screen")
    training_jobs = reports["cell49"]["jobs"] + reports["calibration"]["jobs"]
    old_jobs = reports["old_holdout"]["jobs"]
    train = observations(training_jobs, source="training")
    old = observations(old_jobs, source="previously_inspected")
    by_column = {col: [item for item in train if item["column"] == col]
                 for col in range(4)}

    def errors(queries: list[dict], *, leave_case_out: bool) -> Counter:
        counts: Counter = Counter()
        for query in queries:
            pool = by_column[query["column"]]
            if leave_case_out:
                pool = [item for item in pool if item["case"] != query["case"]]
            if query["sum"] not in {item["sum"] for item in pool}:
                continue  # An unseen class is not evidence of analog ambiguity.
            predicted, _, _ = _nearest(pool, query, cm_weight=0, condition=None)
            if predicted != query["sum"]:
                counts[query["case"]] += 1
        return counts

    train_errors = errors(train, leave_case_out=True)
    old_errors = errors(old, leave_case_out=False)
    old_slots = min(4, max_cases // 4)
    old_ranked = sorted(old_jobs, key=lambda job: (-old_errors[job["case"]], job["case"]))
    train_ranked = sorted(training_jobs,
                          key=lambda job: (-train_errors[job["case"]], job["case"]))
    selected = []
    for source, ranked, limit, counts in (
        ("training", train_ranked, max_cases - old_slots, train_errors),
        ("previously_inspected", old_ranked, old_slots, old_errors),
    ):
        for job in ranked[:limit]:
            if not re.fullmatch(r"[A-Za-z0-9_]+", job["case"]):
                raise ValueError(f"unsafe case name: {job['case']!r}")
            selected.append({"source": source, "case": job["case"],
                             "known_level_scalar_errors": counts[job["case"]],
                             "activation_x2": job["activation_x2"],
                             "ternary_weights": job["ternary_weights"],
                             "integer_sums": job["integer_sums"]})
    if len(selected) != max_cases:
        raise ValueError("insufficient cases for requested screen")
    return selected


def split_case(parent: dict, partition: str) -> tuple[Case, Case]:
    """Set inactive row PWM to zero while keeping all 16 stored weights."""
    if partition not in PARTITIONS:
        raise ValueError(f"unknown 2+2 partition: {partition}")
    acts = tuple(int(value) for value in parent["activation_x2"])
    weights = tuple(tuple(int(value) for value in row)
                    for row in parent["ternary_weights"])
    phases = tuple(Case(f"{parent['case']}_{label}",
                        tuple(acts[row] if row in active else 0 for row in range(4)),
                        weights)
                   for label, active in zip(("a", "b"), PARTITIONS[partition]))
    if any(sum(phase.sums[col] for phase in phases) != parent["integer_sums"][col]
           for col in range(4)):
        raise ValueError(f"partition changed integer result: {parent['case']}")
    return phases


def summarize_partition(jobs: list[dict]) -> dict:
    """Measure partial-level ordering; never infer unmeasured ADC accuracy."""
    phases = {}
    for label in ("a", "b"):
        subset = [job for job in jobs if job["phase"] == label]
        phases[label] = analyze_transfer(subset)
    return {
        "phases": phases,
        "both_partial_transfers_ordered_in_selected_set": all(
            item["transfer_observation"] == "ORDERED_IN_MEASURED_SET"
            for item in phases.values()),
        "scope_warning": "Selected TT PEX cases only. Arithmetic partial-sum identity is not a measured ADC decoder; full input space, noise, PVT and wrapper are unproven.",
    }


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 600,
        max_cases: int = 16, partition: str = "adjacent") -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0 or partition not in PARTITIONS:
        raise ValueError("positive timeout and a supported partition are required")
    reports, report_hashes = _read_reports(root)
    selected = select_hard_cases(reports, max_cases=max_cases)
    _, _, model, pex = _provenance(root)
    if ({reports[name]["pex_sha256"] for name in reports} != {_digest(pex)} or
            {reports[name]["model_sha256"] for name in reports} != {_digest(model)}):
        raise ValueError("measured reports do not match current PEX/PDK model")
    folder = root / OUTPUT / partition
    folder.mkdir(parents=True, exist_ok=True)
    ngspice = shutil.which("ngspice") if execute else None
    failures = ["ngspice not on PATH"] if execute and not ngspice else []
    version = None
    if ngspice:
        result = subprocess.run([ngspice, "-v"], text=True, capture_output=True,
                                timeout=15, check=False)
        version = (result.stdout + result.stderr).strip()
        if version != reports["cell49"]["ngspice_version"]:
            failures.append("ngspice version differs from the measured TT reports")
    jobs = []
    for parent in selected:
        for phase, case in zip(("a", "b"), split_case(parent, partition)):
            deck = folder / f"{case.name}.spice"
            deck.write_text(make_pex_deck(case, model, pex, LOAD_FF, PWM_UNIT_PS),
                            encoding="utf-8")
            log = folder / f"{case.name}.log"
            checkpoint = folder / f"{case.name}.receipt.json"
            jobs.append({"case": case.name, "parent_case": parent["case"],
                         "phase": phase, "activation_x2": list(case.acts),
                         "ternary_weights": [list(row) for row in case.weights],
                         "integer_sums": list(case.sums),
                         "deck": str(deck.relative_to(root)),
                         "deck_sha256": _digest(deck),
                         "log": str(log.relative_to(root)),
                         "checkpoint": str(checkpoint.relative_to(root))})
    for index, job in enumerate(jobs if execute and not failures else [], start=1):
        deck, log, checkpoint = (root / job[key]
                                 for key in ("deck", "log", "checkpoint"))
        saved = _checkpoint(checkpoint, deck_sha256=job["deck_sha256"],
                            pex_sha256=_digest(pex), model_sha256=_digest(model),
                            ngspice_version=version, log=log)
        if saved:
            values = saved["measurements_v"]
            job["reused_checkpoint"] = True
        else:
            if log.is_file():
                log.unlink()  # Only this runner's exact generated log path.
            try:
                result = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                        cwd=folder, text=True, capture_output=True,
                                        timeout=timeout_s, check=False)
            except subprocess.TimeoutExpired:
                failures.append(f"{job['case']}: ngspice timeout after {timeout_s}s")
                break
            output = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
            values = parse_measurements(output, _expected())
            if (result.returncode or set(values) != set(_expected()) or
                    not all(math.isfinite(value) for value in values.values())):
                failures.append(f"{job['case']}: incomplete ngspice result; see {log}")
                break
            checkpoint.write_text(json.dumps({
                "status": "PASS", "deck_sha256": job["deck_sha256"],
                "pex_sha256": _digest(pex), "model_sha256": _digest(model),
                "ngspice_version": version, "log_sha256": _digest(log),
                "measurements_v": values}, indent=2) + "\n", encoding="utf-8")
        job["measurements_v"] = values
        if index == 1 or index % 8 == 0 or index == len(jobs):
            print(f"2+2 TT PEX: {index}/{len(jobs)} ({job['case']})", flush=True)
    complete = sum("measurements_v" in job for job in jobs)
    analysis = summarize_partition(jobs) if execute and not failures and complete == len(jobs) else None
    report = {"format": "automx-cim-post49-row-partition-v1",
              "status": "FAIL" if failures else
                        "MEASURED_PARTITION_TT_DIAGNOSTIC" if execute else "PREPARED",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "partition": partition, "row_groups": PARTITIONS[partition],
              "stimulus": {"load_ff": LOAD_FF, "pwm_unit_ps": PWM_UNIT_PS,
                           "separate_precharge_per_group": True},
              "input_report_sha256": report_hashes,
              "pex_sha256": _digest(pex), "model_sha256": _digest(model),
              "ngspice_version": version, "selected_parents": selected,
              "planned_sims": len(jobs), "completed_sims": complete,
              "reused_checkpoints": sum(job.get("reused_checkpoint", False) for job in jobs),
              "analysis": analysis, "failures": failures, "jobs": jobs,
              "not_signoff": "Selected 2+2 passive-core TT diagnostic only; no physical ADC, PVT or clocked-wrapper proof"}
    target = folder / ("measured.json" if execute else "prepared.json")
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=600)
    parser.add_argument("--max-cases", type=int, default=16)
    parser.add_argument("--partition", choices=tuple(PARTITIONS), default="adjacent")
    args = parser.parse_args()
    result = run(args.root, execute=args.run, timeout_s=args.timeout_s,
                 max_cases=args.max_cases, partition=args.partition)
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ("jobs", "analysis", "selected_parents")}, indent=2))
    if result["status"] == "FAIL":
        raise SystemExit(1)

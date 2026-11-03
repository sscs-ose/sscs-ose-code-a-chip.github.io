"""Measure 16 previously unseen MHA-derived TT PEX cases at 800 fF/50 ps.

Requires a complete, ordered 101-case cell-4.9 report. The held-out cases are
not used by the 4.5/4.7/4.8/4.9 selection screens. This is a diagnostic,
not a noise, ADC, PVT or wrapper sign-off receipt.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.config import Sky130MHAConfig  # noqa: E402
from automx_cim.spice import parse_measurements  # noqa: E402
from scripts.run_core_candidate_full_tt import (  # noqa: E402
    LOAD_FF, PWM_UNIT_PS, _checkpoint, _digest, _expected, _provenance,
    _read, analyze_transfer,
)
from scripts.run_core_candidate_pex import make_pex_deck  # noqa: E402
from scripts.run_core_pex_coverage import Case, mha_cases  # noqa: E402

OUTPUT = Path("results/sky130/post49_holdout_tt")


def heldout_cases(config: Sky130MHAConfig, baseline_jobs: list[dict[str, object]]) -> list[Case]:
    """Reserve deterministic MHA ranks 16–31, rejecting any earlier vector."""
    previous = {
        (tuple(int(value) for value in job["activation_x2"]),
         tuple(tuple(int(value) for value in row) for row in job["ternary_weights"]))
        for job in baseline_jobs
    }
    cases = mha_cases(config, 32)[16:32]
    if len(cases) != 16 or any((case.acts, case.weights) in previous for case in cases):
        raise ValueError("MHA ranks 16–31 are not an independent held-out set")
    return cases


def _verified_stage49(root: Path, coverage: dict[str, object], candidate: dict[str, object],
                      model: Path, pex: Path) -> dict[str, object]:
    path = root / "results/sky130/core_candidate_full_tt/measured.json"
    if not path.is_file():
        raise ValueError(f"cell 4.9 measured report is missing: {path}")
    report = _read(path)
    jobs = report.get("jobs", [])
    analysis = report.get("analysis") if isinstance(report.get("analysis"), dict) else {}
    checks = {
        "report format": report.get("format") == "automx-cim-core-candidate-full-tt-v1",
        "measurement status": report.get("status") == "MEASURED_TT_CANDIDATE_SCREEN",
        "no failures": not report.get("failures"),
        "101 planned simulations": report.get("planned_sims") == 101,
        "101 completed simulations": report.get("completed_sims") == 101,
        "101 case records": isinstance(jobs, list) and len(jobs) == 101,
        "800 fF load": report.get("load_ff") == LOAD_FF,
        "50 ps PWM unit": report.get("pwm_unit_ps") == PWM_UNIT_PS,
        "cell 4.5 receipt hash": report.get("stage4p5_sha256") == _digest(
            root / "results/receipts/physical/core_pex_coverage.json"),
        "cell 4.8 report hash": report.get("stage4p8_sha256") == _digest(
            root / "results/sky130/core_candidate_pex/measured.json"),
        "Stage-5 summary hash": report.get("stage5_summary_sha256") == _digest(
            root / "results/receipts/physical/stage5_summary.json"),
        "PEX hash": report.get("pex_sha256") == _digest(pex),
        "PDK model hash": report.get("model_sha256") == _digest(model),
        "ordered measured levels": analysis.get("transfer_observation") ==
        "ORDERED_IN_MEASURED_SET",
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("cell 4.9 is missing, stale, incomplete or unordered; failed: "
                         + ", ".join(failed))
    baseline = {str(job["case"]): job for job in coverage["jobs"]}
    if len(baseline) != 101 or {job["case"] for job in jobs} != set(baseline):
        raise ValueError("cell 4.9 case set differs from cell 4.5")
    for job in jobs:
        original = baseline[job["case"]]
        if (job["activation_x2"] != original["activation_x2"] or
                job["ternary_weights"] != original["ternary_weights"] or
                job["integer_sums"] != original["integer_sums"] or
                set(job.get("measurements_v", {})) != set(_expected()) or
                not all(math.isfinite(float(value)) for value in job["measurements_v"].values())):
            raise ValueError(f"cell 4.9 case data incomplete: {job['case']}")
        deck = (root / job["deck"]).resolve()
        if not deck.is_relative_to(root) or not deck.is_file() or _digest(deck) != job["deck_sha256"]:
            raise ValueError(f"cell 4.9 deck changed: {job['case']}")
    if analyze_transfer(jobs)["transfer_observation"] != "ORDERED_IN_MEASURED_SET":
        raise ValueError("cell 4.9 raw measurements are unordered; reject cached summary")
    if candidate.get("status") != "MEASURED_PEX_SCREEN":
        raise ValueError("cell 4.8 PEX evidence changed")
    return report


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 180) -> dict[str, object]:
    root = Path(root).resolve()
    coverage, candidate, model, pex = _provenance(root)
    stage49 = _verified_stage49(root, coverage, candidate, model, pex)
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    cases = heldout_cases(config, coverage["jobs"])
    folder = root / OUTPUT
    folder.mkdir(parents=True, exist_ok=True)
    ngspice = shutil.which("ngspice") if execute else None
    failures = ["ngspice not on PATH"] if execute and not ngspice else []
    version = ""
    if ngspice:
        response = subprocess.run([ngspice, "-v"], text=True, capture_output=True,
                                  timeout=15, check=False)
        version = (response.stdout + response.stderr).strip()
    jobs = []
    for case in cases:
        deck = folder / f"{case.name}.spice"
        deck.write_text(make_pex_deck(case, model, pex, LOAD_FF, PWM_UNIT_PS),
                        encoding="utf-8")
        jobs.append({"case": case.name, "activation_x2": list(case.acts),
                     "ternary_weights": [list(row) for row in case.weights],
                     "integer_sums": list(case.sums),
                     "deck": str(deck.relative_to(root)), "deck_sha256": _digest(deck),
                     "log": str((folder / f"{case.name}.log").relative_to(root)),
                     "checkpoint": str((folder / f"{case.name}.receipt.json").relative_to(root))})
    for index, job in enumerate(jobs if execute and not failures else [], start=1):
        deck, log, checkpoint = (root / job[key] for key in ("deck", "log", "checkpoint"))
        saved = _checkpoint(checkpoint, deck_sha256=job["deck_sha256"],
                            pex_sha256=_digest(pex), model_sha256=_digest(model),
                            ngspice_version=version, log=log)
        if saved:
            job["measurements_v"] = saved["measurements_v"]
            job["reused_checkpoint"] = True
            print(f"Holdout PEX: {index}/{len(jobs)} ({job['case']}, checkpoint)", flush=True)
            continue
        if log.is_file():
            log.unlink()
        try:
            completed = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                       cwd=folder, text=True, capture_output=True,
                                       timeout=timeout_s, check=False)
        except subprocess.TimeoutExpired:
            failures.append(f"{job['case']}: timeout after {timeout_s}s")
            break
        content = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
        values = parse_measurements(content, _expected())
        if completed.returncode or set(values) != set(_expected()) or not all(
                math.isfinite(value) for value in values.values()):
            failures.append(f"{job['case']}: incomplete ngspice result; inspect {log}")
            break
        job["measurements_v"] = values
        checkpoint.write_text(json.dumps({
            "status": "PASS", "deck_sha256": job["deck_sha256"],
            "pex_sha256": _digest(pex), "model_sha256": _digest(model),
            "ngspice_version": version, "log_sha256": _digest(log),
            "measurements_v": values}, indent=2) + "\n", encoding="utf-8")
        print(f"Holdout PEX: {index}/{len(jobs)} ({job['case']})", flush=True)
    completed = sum("measurements_v" in job for job in jobs)
    combined = (analyze_transfer(stage49["jobs"] + jobs)
                if execute and not failures and completed == 16 else None)
    report = {"format": "automx-cim-post49-holdout-tt-v1",
              "status": "FAIL" if failures else "MEASURED_HOLDOUT_TT" if execute else "PREPARED",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "16 new deterministic MHA-derived cases plus 101 prior TT PEX cases; no ADC/noise/PVT PASS",
              "load_ff": LOAD_FF, "pwm_unit_ps": PWM_UNIT_PS,
              "stage49_sha256": _digest(root / "results/sky130/core_candidate_full_tt/measured.json"),
              "pex_sha256": _digest(pex), "model_sha256": _digest(model),
              "ngspice_version": version or None,
              "heldout_case_names": [case.name for case in cases],
              "planned_sims": len(jobs), "completed_sims": completed,
              "reused_checkpoints": sum(job.get("reused_checkpoint", False) for job in jobs),
              "combined_117_case_analysis": combined,
              "failures": failures, "jobs": jobs}
    target = folder / ("measured.json" if execute else "prepared.json")
    report["report_path"] = str(target.relative_to(root))
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=180)
    args = parser.parse_args()
    result = run(args.root, execute=args.run, timeout_s=args.timeout_s)
    print(json.dumps({key: value for key, value in result.items() if key != "jobs"}, indent=2))
    if result["status"] == "FAIL":
        raise SystemExit(1)

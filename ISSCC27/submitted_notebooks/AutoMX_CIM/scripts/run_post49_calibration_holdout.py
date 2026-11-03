"""Independent TT PEX holdout after 87-level calibration expansion.

MHA ranks 32-63 were not in the original 101-case screen, the inspected
16-case holdout, or the synthetic calibration sweep. All conclusions are
passive-core TT diagnostics, never physical ADC or Stage-8 sign-off.
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
from scripts.run_post49_calibration_tt import (  # noqa: E402
    FEATURES, analyze_feature_holdout, analyze_feature_training,
    calibration_cases, reachable_sums,
)
from scripts.run_post49_decoder_diagnostic import run as validate_prior_evidence  # noqa: E402

OUTPUT = Path("results/sky130/post49_calibration_holdout")


def new_holdout_cases(config: Sky130MHAConfig,
                      prior_jobs: list[dict]) -> list[Case]:
    previous = {(tuple(job["activation_x2"]),
                 tuple(tuple(row) for row in job["ternary_weights"]))
                for job in prior_jobs}
    selected = mha_cases(config, 64)[32:64]
    if (len(selected) != 32 or
            [case.name for case in selected] !=
            [f"mha_{index:02d}" for index in range(32, 64)] or
            any((case.acts, case.weights) in previous for case in selected) or
            len({(case.acts, case.weights) for case in selected}) != 32):
        raise ValueError("MHA 32-63 are not an independent holdout")
    return selected


def _verified_calibration(root: Path, pex: Path, model: Path,
                          prior: dict) -> dict:
    path = root / "results/sky130/post49_calibration_tt/measured.json"
    report = _read(path)
    jobs = report.get("jobs", [])
    expected = calibration_cases()
    if (report.get("format") != "automx-cim-post49-calibration-tt-v1" or
            report.get("status") != "MEASURED_CALIBRATION_TT" or
            report.get("conclusion") != "TRAINING_ONLY_MARGIN_CANDIDATE" or
            report.get("failures") or
            report.get("old_holdout_consumed_for_design") is not True or
            report.get("cell49_sha256") != prior["cell49_sha256"] or
            report.get("old_holdout_sha256") != prior["holdout_sha256"] or
            report.get("requirements_sha256") != _digest(
                root / "configs/sky130_post49_requirements.json") or
            report.get("script_sha256") != _digest(
                root / "scripts/run_post49_calibration_tt.py") or
            report.get("pex_sha256") != _digest(pex) or
            report.get("model_sha256") != _digest(model) or
            report.get("reachable_sums") != reachable_sums() or
            report.get("load_ff") != LOAD_FF or report.get("pwm_unit_ps") != PWM_UNIT_PS or
            report.get("planned_sims") != len(expected) or
            report.get("completed_sims") != len(expected) or
            len(jobs) != len(expected) or
            [job.get("case") for job in jobs] != [case.name for case in expected]):
        raise ValueError("complete ordered TT calibration is required before new holdout")
    version = report.get("ngspice_version")
    if not isinstance(version, str) or not version:
        raise ValueError("calibration ngspice version missing")
    for job, case in zip(jobs, expected):
        deck = (root / job["deck"]).resolve()
        log = (root / job["log"]).resolve()
        checkpoint = (root / job["checkpoint"]).resolve()
        if any(not path.is_relative_to(root) for path in (deck, log, checkpoint)):
            raise ValueError(f"calibration path escapes project: {case.name}")
        saved = _checkpoint(checkpoint, deck_sha256=job["deck_sha256"],
                            pex_sha256=_digest(pex), model_sha256=_digest(model),
                            ngspice_version=version, log=log)
        if (not deck.is_file() or _digest(deck) != job["deck_sha256"] or
                saved is None or saved.get("measurements_v") != job.get("measurements_v") or
                job.get("activation_x2") != list(case.acts) or
                job.get("ternary_weights") != [list(row) for row in case.weights] or
                job.get("integer_sums") != list(case.sums)):
            raise ValueError(f"calibration evidence changed: {case.name}")
    old_training = (_read(root / "results/sky130/core_candidate_full_tt/measured.json")["jobs"] +
                    _read(root / "results/sky130/post49_holdout_tt/measured.json")["jobs"])
    recomputed = analyze_transfer(old_training + jobs)
    screens = {feature: analyze_feature_training(old_training + jobs, feature)
               for feature in FEATURES}
    acceptance = _read(root / "configs/sky130_post49_requirements.json")["acceptance"]
    budget = (acceptance["maximum_input_referred_offset_abs_v"] +
              5 * acceptance["maximum_input_referred_noise_rms_v"] +
              acceptance["maximum_reference_threshold_error_abs_v"] +
              acceptance["maximum_aperture_induced_shift_abs_v"])
    selected = next((feature for feature in FEATURES
                     if screens[feature]["all_levels_ordered"] and
                     screens[feature]["minimum_gap_equivalent_v"] > 2 * budget), None)
    if (report.get("analysis") != recomputed or
            report.get("feature_screens") != screens or
            report.get("selected_feature") != selected or
            any(any(col["sum_levels"] != reachable_sums()
                    for col in screen["columns"]) for screen in screens.values()) or
            selected is None):
        raise ValueError("calibration raw data do not meet TT threshold/margin gate")
    return report


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    prior = validate_prior_evidence(root)
    _, _, model, pex = _provenance(root)
    calibration = _verified_calibration(root, pex, model, prior)
    stage49 = _read(root / "results/sky130/core_candidate_full_tt/measured.json")
    old_holdout = _read(root / "results/sky130/post49_holdout_tt/measured.json")
    training = stage49["jobs"] + old_holdout["jobs"] + calibration["jobs"]
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    cases = new_holdout_cases(config, training)
    folder = root / OUTPUT
    folder.mkdir(parents=True, exist_ok=True)
    ngspice = shutil.which("ngspice") if execute else None
    failures = ["ngspice not on PATH"] if execute and not ngspice else []
    version = ""
    if ngspice:
        process = subprocess.run([ngspice, "-v"], text=True, capture_output=True,
                                 timeout=15, check=False)
        version = (process.stdout + process.stderr).strip()
        if not version or version != calibration.get("ngspice_version"):
            failures.append("ngspice version differs from TT calibration")
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
            values = saved["measurements_v"]
            job["reused_checkpoint"] = True
        else:
            if log.is_file():
                log.unlink()
            try:
                process = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                         cwd=folder, text=True, capture_output=True,
                                         timeout=timeout_s, check=False)
            except subprocess.TimeoutExpired:
                failures.append(f"{job['case']}: ngspice timeout after {timeout_s}s")
                break
            output = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
            values = parse_measurements(output, _expected())
            if (process.returncode or set(values) != set(_expected()) or
                    not all(math.isfinite(value) for value in values.values())):
                failures.append(f"{job['case']}: incomplete ngspice result; see {log}")
                break
            checkpoint.write_text(json.dumps({
                "status": "PASS", "deck_sha256": job["deck_sha256"],
                "pex_sha256": _digest(pex), "model_sha256": _digest(model),
                "ngspice_version": version, "log_sha256": _digest(log),
                "measurements_v": values}, indent=2) + "\n", encoding="utf-8")
        job["measurements_v"] = values
        if index == 1 or index % 5 == 0 or index == len(jobs):
            print(f"New holdout PEX: {index}/{len(jobs)} ({job['case']})", flush=True)
    completed = sum("measurements_v" in job for job in jobs)
    assessment = None
    conclusion = "NOT_MEASURED"
    if execute and not failures and completed == len(jobs):
        acceptance = _read(root / "configs/sky130_post49_requirements.json")["acceptance"]
        budget = (acceptance["maximum_input_referred_offset_abs_v"] +
                  5 * acceptance["maximum_input_referred_noise_rms_v"] +
                  acceptance["maximum_reference_threshold_error_abs_v"] +
                  acceptance["maximum_aperture_induced_shift_abs_v"])
        selected = calibration["selected_feature"]
        decoder = analyze_feature_holdout(
            analyze_feature_training(training, selected), jobs, budget)
        transfer = analyze_transfer(training + jobs)
        combined_feature = analyze_feature_training(training + jobs, selected)
        assessment = {"decoder": decoder, "combined_transfer": transfer,
                      "combined_feature_transfer": combined_feature}
        conclusion = ("DETERMINISTIC_TT_HOLDOUT_TARGET_MET" if
                      decoder["decode_mismatches"] == 0 and
                      decoder["unseen_sum_samples"] == 0 and
                      decoder["samples_below_error_budget"] == 0 and
                      decoder["common_mode_outside_training_samples"] == 0 and
                      combined_feature["all_levels_ordered"] and
                      combined_feature["minimum_gap_equivalent_v"] > 2 * budget else
                      "HOLDOUT_ERRORS_OR_INSUFFICIENT_MARGIN")
    report = {"format": "automx-cim-post49-calibration-holdout-v1",
              "status": "FAIL" if failures else "MEASURED_NEW_HOLDOUT_TT" if execute else "PREPARED",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "32 new MHA-derived TT PEX cases after full-sum calibration; no ADC/noise/PVT sign-off",
              "calibration_sha256": _digest(root / "results/sky130/post49_calibration_tt/measured.json"),
              "selected_feature": calibration["selected_feature"],
              "requirements_sha256": _digest(root / "configs/sky130_post49_requirements.json"),
              "script_sha256": _digest(root / "scripts/run_post49_calibration_holdout.py"),
              "pex_sha256": _digest(pex), "model_sha256": _digest(model),
              "ngspice_version": version or None,
              "load_ff": LOAD_FF, "pwm_unit_ps": PWM_UNIT_PS,
              "planned_sims": len(jobs), "completed_sims": completed,
              "reused_checkpoints": sum(job.get("reused_checkpoint", False) for job in jobs),
              "conclusion": conclusion, "assessment": assessment,
              "failures": failures, "jobs": jobs}
    target = folder / ("measured.json" if execute else "prepared.json")
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=600)
    args = parser.parse_args()
    result = run(args.root, execute=args.run, timeout_s=args.timeout_s)
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ("jobs", "assessment")}, indent=2))
    if result["status"] == "FAIL":
        raise SystemExit(1)

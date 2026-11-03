"""Expand TT PEX calibration to every reachable four-row signed sum.

The earlier 16-case holdout was inspected while choosing this screen and is
therefore calibration data, not an independent validation set. Results never
replace Stage-5 receipts or claim a physical ADC PASS. Run with --run on the
server; hash-validated per-case checkpoints allow continuation after timeout.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from bisect import bisect_right
from itertools import product
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.circuit.sky130 import E2M1_MAGNITUDES_X2  # noqa: E402
from automx_cim.spice import parse_measurements  # noqa: E402
from scripts.run_core_candidate_full_tt import (  # noqa: E402
    LOAD_FF, PWM_UNIT_PS, _checkpoint, _digest, _expected, _provenance,
    _read, analyze_transfer,
)
from scripts.run_core_candidate_pex import make_pex_deck  # noqa: E402
from scripts.run_core_pex_coverage import Case  # noqa: E402
from scripts.run_post49_decoder_diagnostic import run as validate_prior_evidence  # noqa: E402

OUTPUT = Path("results/sky130/post49_calibration_tt")
WEIGHTS = tuple(product((-1, 0, 1), repeat=4))
FEATURES = ("differential_v", "differential_over_common_mode")


def reachable_sums() -> list[int]:
    single = set(E2M1_MAGNITUDES_X2) | {-x for x in E2M1_MAGNITUDES_X2}
    totals = {0}
    for _ in range(4):
        totals = {a + b for a in totals for b in single}
    return sorted(totals)


def calibration_cases() -> list[Case]:
    """One deterministic high-activity valid pattern per reachable sum.

    All four columns see the target sum, but may use different row weights.
    Existing 117 cases supply additional within-sum patterns. This sweep
    does not establish full activation/weight combination coverage.
    """
    best: dict[int, tuple[tuple, tuple[int, ...], tuple[int, ...]]] = {}
    magnitudes = tuple(sorted(set(E2M1_MAGNITUDES_X2)))
    for acts in product(magnitudes, repeat=4):
        for weights in WEIGHTS:
            total = sum(a * w for a, w in zip(acts, weights))
            activity = sum(a * abs(w) for a, w in zip(acts, weights))
            # Prefer active/cancelling cases, then a stable deterministic tie-break.
            score = (activity, sum(w != 0 for w in weights),
                     tuple(-a for a in acts), tuple(-w for w in weights))
            if total not in best or score > best[total][0]:
                best[total] = (score, acts, weights)
    expected = reachable_sums()
    if sorted(best) != expected:
        raise ValueError("calibration generator missed reachable sums")
    cases = []
    for total in expected:
        _, magnitudes_for_case, base_weights = best[total]
        # Exercise both signed row-PWM phases without changing any dot product.
        signs = (1, -1, 1, -1) if total % 2 else (-1, 1, -1, 1)
        acts = tuple(a * sign for a, sign in zip(magnitudes_for_case, signs))
        corrected = tuple(w * sign for w, sign in zip(base_weights, signs))
        options = [weights for weights in WEIGHTS
                   if sum(a * w for a, w in zip(acts, weights)) == total]
        options.sort(key=lambda weights: (-sum(a != 0 and w != 0
                                               for a, w in zip(acts, weights)), weights))
        if corrected not in options:
            raise ValueError(f"signed-row mapping lost target {total}")
        chosen = [corrected]
        chosen.extend(weights for weights in options if weights != corrected)
        columns = [chosen[index % len(chosen)] for index in range(4)]
        matrix = tuple(tuple(columns[col][row] for col in range(4))
                       for row in range(4))
        name = f"cal_{'p' if total >= 0 else 'n'}{abs(total):02d}"
        case = Case(name, acts, matrix)
        if case.sums != (total,) * 4:
            raise ValueError(f"calibration case {name} has wrong dot product")
        cases.append(case)
    return cases


def _observation(job: dict, col: int, time: str, feature: str) -> tuple[float, float, float]:
    if feature not in FEATURES:
        raise ValueError(f"unsupported decoder feature: {feature}")
    values = job["measurements_v"]
    diff = float(values[f"diff_c{col}_{time}"])
    cm = (float(values[f"blp_c{col}_{time}"]) +
          float(values[f"bln_c{col}_{time}"])) / 2
    if not math.isfinite(diff) or not math.isfinite(cm) or cm <= 0:
        raise ValueError(f"invalid differential/common-mode voltage: {job['case']} c{col} {time}")
    value = diff if feature == "differential_v" else diff / cm
    return value, diff, cm


def analyze_feature_training(jobs: list[dict], feature: str) -> dict:
    """Fit monotone midpoint thresholds using training measurements only."""
    if not jobs:
        raise ValueError("feature training requires measured jobs")
    columns = []
    for col in range(4):
        levels: dict[int, list[float]] = {}
        common_modes = []
        for job in jobs:
            for time in ("t19", "t21"):
                value, _, cm = _observation(job, col, time, feature)
                levels.setdefault(int(job["integer_sums"][col]), []).append(value)
                common_modes.append(cm)
        sums = sorted(levels)
        if len(sums) < 2:
            raise ValueError(f"column {col} has fewer than two measured sum levels")
        intervals = [{"sum": total, "min": min(levels[total]),
                      "max": max(levels[total]), "samples": len(levels[total])}
                     for total in sums]
        gaps = [higher["min"] - lower["max"]
                for lower, higher in zip(intervals, intervals[1:])]
        overlap_count = sum(gap <= 0 for gap in gaps)
        min_gap = min(gaps) if gaps else None
        min_cm = min(common_modes)
        # A dimensionless ratio gap is converted back to the conservative
        # voltage scale at the smallest observed common mode. This does not
        # account for noise or gain error in a future physical CM sensor.
        min_gap_equivalent_v = (min_gap if feature == "differential_v" else
                                min_gap * min_cm) if min_gap is not None else None
        thresholds = [(lower["max"] + higher["min"]) / 2
                      for lower, higher in zip(intervals, intervals[1:])]
        columns.append({"column": col, "sum_levels": sums,
                        "intervals": intervals, "thresholds": thresholds,
                        "overlap_count": overlap_count,
                        "min_gap": min_gap,
                        "min_gap_equivalent_v": min_gap_equivalent_v,
                        "training_common_mode_range_v": [min_cm, max(common_modes)]})
    return {"feature": feature, "columns": columns,
            "minimum_gap_equivalent_v": min(
                col["min_gap_equivalent_v"] for col in columns),
            "all_levels_ordered": all(col["overlap_count"] == 0 for col in columns),
            "scope_warning": "Deterministic TT passive-core feature; CM sensing, noise and PVT unmeasured"}


def analyze_feature_holdout(training: dict, holdout_jobs: list[dict],
                            error_budget_v: float) -> dict:
    """Evaluate a fixed training-only feature/threshold choice on new cases."""
    if not holdout_jobs or not math.isfinite(error_budget_v) or error_budget_v < 0:
        raise ValueError("nonempty holdout and finite nonnegative budget required")
    feature = training["feature"]
    columns = []
    for col in range(4):
        model = training["columns"][col]
        sums, thresholds = model["sum_levels"], model["thresholds"]
        low_cm, high_cm = model["training_common_mode_range_v"]
        details = []
        for job in holdout_jobs:
            expected = int(job["integer_sums"][col])
            for time in ("t19", "t21"):
                value, diff, cm = _observation(job, col, time, feature)
                predicted = sums[bisect_right(thresholds, value)]
                feature_distance = min(abs(value - threshold) for threshold in thresholds)
                distance_v = (feature_distance if feature == "differential_v" else
                              feature_distance * cm)
                details.append({"case": job["case"], "time": time,
                                "expected_sum": expected, "predicted_sum": predicted,
                                "expected_sum_unseen_in_training": expected not in sums,
                                "diff_v": diff, "common_mode_v": cm,
                                "feature_value": value,
                                "nearest_threshold_distance_equivalent_v": distance_v,
                                "below_error_budget": distance_v <= error_budget_v,
                                "common_mode_outside_training_range": not low_cm <= cm <= high_cm})
        columns.append({"column": col, "holdout_samples": len(details),
                        "decode_mismatches": sum(x["predicted_sum"] != x["expected_sum"]
                                                 for x in details),
                        "unseen_sum_samples": sum(x["expected_sum_unseen_in_training"]
                                                  for x in details),
                        "samples_below_error_budget": sum(x["below_error_budget"]
                                                          for x in details),
                        "common_mode_outside_training_samples": sum(
                            x["common_mode_outside_training_range"] for x in details),
                        "details": details})
    return {"feature": feature, "columns": columns,
            "decode_mismatches": sum(c["decode_mismatches"] for c in columns),
            "unseen_sum_samples": sum(c["unseen_sum_samples"] for c in columns),
            "samples_below_error_budget": sum(c["samples_below_error_budget"]
                                              for c in columns),
            "common_mode_outside_training_samples": sum(
                c["common_mode_outside_training_samples"] for c in columns),
            "sample_count": sum(c["holdout_samples"] for c in columns),
            "error_budget_v": error_budget_v,
            "scope_warning": "No physical common-mode sensor, converter, noise, PVT or error-rate proof"}


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    prior = validate_prior_evidence(root)
    _, _, model, pex = _provenance(root)
    stage49 = _read(root / "results/sky130/core_candidate_full_tt/measured.json")
    old_holdout = _read(root / "results/sky130/post49_holdout_tt/measured.json")
    cases = calibration_cases()
    folder = root / OUTPUT
    folder.mkdir(parents=True, exist_ok=True)
    ngspice = shutil.which("ngspice") if execute else None
    failures = ["ngspice not on PATH"] if execute and not ngspice else []
    version = ""
    if ngspice:
        process = subprocess.run([ngspice, "-v"], text=True, capture_output=True,
                                 timeout=15, check=False)
        version = (process.stdout + process.stderr).strip()
        if (not version or version != stage49.get("ngspice_version") or
                version != old_holdout.get("ngspice_version")):
            failures.append("ngspice version differs from the measured 101+16 TT cases")
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
        if index == 1 or index % 10 == 0 or index == len(jobs):
            print(f"Calibration PEX: {index}/{len(jobs)} ({job['case']})", flush=True)
    completed = sum("measurements_v" in job for job in jobs)
    analysis = None
    feature_screens = None
    selected_feature = None
    conclusion = "NOT_MEASURED"
    if execute and not failures and completed == len(jobs):
        analysis = analyze_transfer(stage49["jobs"] + old_holdout["jobs"] + jobs)
        levels = reachable_sums()
        training = stage49["jobs"] + old_holdout["jobs"] + jobs
        feature_screens = {feature: analyze_feature_training(training, feature)
                           for feature in FEATURES}
        if any(any(column["sum_levels"] != levels for column in screen["columns"])
               for screen in feature_screens.values()):
            raise ValueError("calibration did not cover all reachable sums per column")
        acceptance = _read(root / "configs/sky130_post49_requirements.json")["acceptance"]
        error_budget = (acceptance["maximum_input_referred_offset_abs_v"] +
                        5 * acceptance["maximum_input_referred_noise_rms_v"] +
                        acceptance["maximum_reference_threshold_error_abs_v"] +
                        acceptance["maximum_aperture_induced_shift_abs_v"])
        # Select by training only, in declared order. The new holdout cannot
        # influence this choice or the thresholds.
        for feature in FEATURES:
            screen = feature_screens[feature]
            if (screen["all_levels_ordered"] and
                    screen["minimum_gap_equivalent_v"] > 2 * error_budget):
                selected_feature = feature
                break
        conclusion = ("TRAINING_ONLY_MARGIN_CANDIDATE" if selected_feature else
                      "TRAINING_OVERLAP_OR_INSUFFICIENT_MARGIN")
    report = {"format": "automx-cim-post49-calibration-tt-v1",
              "status": "FAIL" if failures else "MEASURED_CALIBRATION_TT" if execute else "PREPARED",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "87 reachable signed sums per column at TT PEX; one synthetic high-activity pattern per sum plus 117 earlier cases; not ADC sign-off",
              "old_holdout_consumed_for_design": True,
              "cell49_sha256": prior["cell49_sha256"],
              "old_holdout_sha256": prior["holdout_sha256"],
              "requirements_sha256": _digest(root / "configs/sky130_post49_requirements.json"),
              "script_sha256": _digest(root / "scripts/run_post49_calibration_tt.py"),
              "pex_sha256": _digest(pex), "model_sha256": _digest(model),
              "ngspice_version": version or None,
              "load_ff": LOAD_FF, "pwm_unit_ps": PWM_UNIT_PS,
              "reachable_sums": reachable_sums(),
              "planned_sims": len(jobs), "completed_sims": completed,
              "reused_checkpoints": sum(job.get("reused_checkpoint", False) for job in jobs),
              "conclusion": conclusion, "analysis": analysis,
              "feature_screens": feature_screens,
              "selected_feature": selected_feature,
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
                      if key not in ("jobs", "analysis", "feature_screens")}, indent=2))
    if result["status"] == "FAIL":
        raise SystemExit(1)

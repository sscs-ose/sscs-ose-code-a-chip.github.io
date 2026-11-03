"""Train a scalar TT threshold decoder on cell 4.9; test only on cell 4.10.

This is an evidence-linked *diagnostic*, never an ADC, PVT or wrapper PASS.
No ngspice run and no existing measured report/receipt is overwritten.
"""

from __future__ import annotations

import argparse
from bisect import bisect_right
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_core_candidate_full_tt import (
    LOAD_FF, PWM_UNIT_PS, _checkpoint, _digest, _expected, _provenance,
    _read, analyze_transfer,
)
from scripts.run_post49_holdout_tt import _verified_stage49, heldout_cases
from automx_cim.config import Sky130MHAConfig


TRAINING = Path("results/sky130/core_candidate_full_tt/measured.json")
HOLDOUT = Path("results/sky130/post49_holdout_tt/measured.json")
OUTPUT = Path("results/sky130/post49_decoder_diagnostic.json")
TIMES = ("t19", "t21")


def analyze_decoder(training_jobs: list[dict], holdout_jobs: list[dict],
                    error_budget_v: float) -> dict:
    """Fit only training intervals; do not use holdout values to move thresholds."""
    if not training_jobs or not holdout_jobs or not math.isfinite(error_budget_v) or error_budget_v < 0:
        raise ValueError("nonempty training/holdout and finite nonnegative budget required")
    columns = []
    for col in range(4):
        levels: dict[int, list[float]] = {}
        training_cm = []
        for job in training_jobs:
            total = int(job["integer_sums"][col])
            for time in TIMES:
                values = job["measurements_v"]
                diff = float(values[f"diff_c{col}_{time}"])
                cm = (float(values[f"blp_c{col}_{time}"]) +
                      float(values[f"bln_c{col}_{time}"])) / 2
                if not math.isfinite(diff) or not math.isfinite(cm):
                    raise ValueError("non-finite training measurement")
                levels.setdefault(total, []).append(diff)
                training_cm.append(cm)
        sums = sorted(levels)
        if len(sums) < 2:
            raise ValueError(f"column {col} has fewer than two training sums")
        thresholds = []
        for lower, higher in zip(sums, sums[1:]):
            lower_max, higher_min = max(levels[lower]), min(levels[higher])
            if lower_max >= higher_min:
                raise ValueError(f"column {col}: training intervals overlap at {lower}->{higher}")
            thresholds.append((lower_max + higher_min) / 2)
        details = []
        cm_outside = 0
        for job in holdout_jobs:
            expected = int(job["integer_sums"][col])
            for time in TIMES:
                values = job["measurements_v"]
                diff = float(values[f"diff_c{col}_{time}"])
                cm = (float(values[f"blp_c{col}_{time}"]) +
                      float(values[f"bln_c{col}_{time}"])) / 2
                if not math.isfinite(diff) or not math.isfinite(cm):
                    raise ValueError("non-finite holdout measurement")
                predicted = sums[bisect_right(thresholds, diff)]
                threshold_distance = min(abs(diff - value) for value in thresholds)
                outside = not min(training_cm) <= cm <= max(training_cm)
                cm_outside += outside
                details.append({"case": job["case"], "time": time,
                                "expected_sum": expected, "predicted_sum": predicted,
                                "expected_sum_unseen_in_training": expected not in levels,
                                "diff_v": diff, "common_mode_v": cm,
                                "common_mode_outside_training_range": outside,
                                "nearest_threshold_distance_v": threshold_distance,
                                "below_error_budget": threshold_distance <= error_budget_v})
        columns.append({"column": col, "training_sum_levels": sums,
                        "thresholds_v": thresholds,
                        "training_common_mode_range_v": [min(training_cm), max(training_cm)],
                        "holdout_samples": len(details),
                        "decode_mismatches": sum(x["predicted_sum"] != x["expected_sum"]
                                                 for x in details),
                        "unseen_sum_samples": sum(x["expected_sum_unseen_in_training"]
                                                  for x in details),
                        "samples_below_error_budget": sum(x["below_error_budget"]
                                                          for x in details),
                        "common_mode_outside_training_samples": cm_outside,
                        "min_holdout_threshold_distance_v": min(
                            x["nearest_threshold_distance_v"] for x in details),
                        "details": details})
    return {"columns": columns,
            "decode_mismatches": sum(c["decode_mismatches"] for c in columns),
            "unseen_sum_samples": sum(c["unseen_sum_samples"] for c in columns),
            "samples_below_error_budget": sum(c["samples_below_error_budget"]
                                              for c in columns),
            "common_mode_outside_training_samples": sum(
                c["common_mode_outside_training_samples"] for c in columns),
            "sample_count": sum(c["holdout_samples"] for c in columns),
            "error_budget_v": error_budget_v,
            "scope_warning": "Thresholds fit 101 TT cases only; 16 held-out cases do not prove full code range, noise, PVT, or physical ADC"}


def run(root: str | Path) -> dict:
    root = Path(root).resolve()
    spec_path = root / "configs/sky130_post49_requirements.json"
    spec = _read(spec_path)
    if (spec.get("status") not in ("DESIGN_BASELINE_FROZEN_UNVERIFIED", "APPROVED") or
            spec.get("candidate_core_stimulus", {}).get("load_ff") != LOAD_FF or
            spec.get("candidate_core_stimulus", {}).get("pwm_unit_ps") != PWM_UNIT_PS):
        raise ValueError("frozen 800 fF/50 ps prototype requirements required")
    accept = spec["acceptance"]
    budget = (float(accept["maximum_input_referred_offset_abs_v"]) +
              5 * float(accept["maximum_input_referred_noise_rms_v"]) +
              float(accept["maximum_reference_threshold_error_abs_v"]) +
              float(accept["maximum_aperture_induced_shift_abs_v"]))
    coverage, candidate, model, pex = _provenance(root)
    stage49 = _verified_stage49(root, coverage, candidate, model, pex)
    holdout_path = root / HOLDOUT
    holdout = _read(holdout_path)
    jobs = holdout.get("jobs", [])
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    expected_cases = heldout_cases(config, coverage["jobs"])
    if (holdout.get("format") != "automx-cim-post49-holdout-tt-v1" or
            holdout.get("status") != "MEASURED_HOLDOUT_TT" or
            holdout.get("failures") or
            holdout.get("stage49_sha256") != _digest(root / TRAINING) or
            holdout.get("pex_sha256") != _digest(pex) or
            holdout.get("model_sha256") != _digest(model) or
            holdout.get("load_ff") != LOAD_FF or
            holdout.get("pwm_unit_ps") != PWM_UNIT_PS or
            holdout.get("planned_sims") != 16 or
            holdout.get("completed_sims") != 16 or
            len(jobs) != 16 or
            [job.get("case") for job in jobs] != [case.name for case in expected_cases]):
        raise ValueError("cell 4.10 measured holdout missing, stale or incomplete")
    for job, case in zip(jobs, expected_cases):
        deck = (root / job["deck"]).resolve()
        if (not deck.is_relative_to(root) or not deck.is_file() or
                _digest(deck) != job.get("deck_sha256") or
                job.get("activation_x2") != list(case.acts) or
                job.get("ternary_weights") != [list(row) for row in case.weights] or
                job.get("integer_sums") != list(case.sums)):
            raise ValueError(f"holdout source/deck changed: {case.name}")
    for report, group in ((stage49, stage49["jobs"]), (holdout, jobs)):
        version = report.get("ngspice_version")
        if not isinstance(version, str) or not version:
            raise ValueError("ngspice version missing from measured report")
        for job in group:
            log = (root / job["log"]).resolve()
            checkpoint = (root / job["checkpoint"]).resolve()
            if not log.is_relative_to(root) or not checkpoint.is_relative_to(root):
                raise ValueError(f"measurement path escapes project: {job['case']}")
            saved = _checkpoint(checkpoint, deck_sha256=job["deck_sha256"],
                                pex_sha256=_digest(pex), model_sha256=_digest(model),
                                ngspice_version=version, log=log)
            if (saved is None or saved.get("measurements_v") != job.get("measurements_v") or
                    set(job["measurements_v"]) != set(_expected())):
                raise ValueError(f"measurement log/checkpoint changed: {job['case']}")
    combined = analyze_transfer(stage49["jobs"] + jobs)
    if (combined["transfer_observation"] != "ORDERED_IN_MEASURED_SET" or
            holdout.get("combined_117_case_analysis") != combined):
        raise ValueError("combined 117-case transfer is not ordered")
    analysis = analyze_decoder(stage49["jobs"], jobs, budget)
    report = {"format": "automx-cim-post49-decoder-diagnostic-v1",
              "status": "MEASURED_TT_DECODER_DIAGNOSTIC",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "requirements_sha256": _digest(spec_path),
              "cell49_sha256": _digest(root / TRAINING),
              "holdout_sha256": _digest(holdout_path),
              "training_patterns": 101, "holdout_patterns": 16,
              "architecture_tested": "scalar per-column midpoint thresholds; common mode monitored, not decoded",
              "analysis": analysis,
              "not_signoff": "No physical comparator/DAC, noise, mismatch, continuous aperture, full reachable-sum/pattern coverage or PVT proof"}
    output = root / OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = run(args.root)
    print(json.dumps({key: value for key, value in result.items() if key != "analysis"}, indent=2))
    print(json.dumps({key: value for key, value in result["analysis"].items()
                      if key != "columns"}, indent=2))

"""Decompose the measured S/H difference into load, acquisition and droop.

Read the existing ngspice logs. No simulation is run and the measured report
is never changed. The comparison uses the same-run bitline t=2.1 ns values
that were printed by the original deck but not included in its short summary.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.spice import parse_measurements
from scripts.run_wrapper_sample_hold_tt import OUTPUT, SOURCE, _expected, _sha

REPORT = OUTPUT / "measured.json"


def _inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to((root / OUTPUT).resolve()) or not path.is_file():
        raise ValueError(f"missing or escaping sample/hold evidence: {relative}")
    return path


def _bitline_names() -> list[str]:
    return [f"{side}_c{col}_t21" for col in range(4)
            for side in ("blp", "bln")]


def _decompose(job: dict, bitline: dict[str, float]) -> list[dict]:
    rows = []
    source = job["source_measurements_v"]
    held = job["measurements_v"]
    for col in range(4):
        baseline = {side: float(source[f"{side}_c{col}_t21"])
                    for side in ("blp", "bln")}
        same_run = {side: float(bitline[f"{side}_c{col}_t21"])
                    for side in ("blp", "bln")}
        sampled = {side: float(held[f"h{side}_c{col}_t215"])
                   for side in ("blp", "bln")}
        later = {side: float(held[f"h{side}_c{col}_t24"])
                 for side in ("blp", "bln")}
        all_values = (*baseline.values(), *same_run.values(),
                      *sampled.values(), *later.values())
        if not all(math.isfinite(value) for value in all_values):
            raise ValueError(f"nonfinite voltage in {job['case']} column {col}")
        diff = lambda pair: pair["bln"] - pair["blp"]
        rows.append({
            "case": job["case"], "no_row_drive": job["no_row_drive"],
            "column": col,
            "original_820ff_bitline_v": baseline,
            "same_run_800ff_plus_switch_bitline_v": same_run,
            "held_2p15ns_v": sampled, "held_2p4ns_v": later,
            "load_profile_shift_v": {side: same_run[side] - baseline[side]
                                     for side in ("blp", "bln")},
            "acquisition_delta_v": {side: sampled[side] - same_run[side]
                                    for side in ("blp", "bln")},
            "total_vs_original_v": {side: sampled[side] - baseline[side]
                                     for side in ("blp", "bln")},
            "differential_load_shift_v": diff(same_run) - diff(baseline),
            "differential_acquisition_delta_v": diff(sampled) - diff(same_run),
            "differential_hold_drift_v": diff(later) - diff(sampled),
            "held_common_mode_2p15ns_v": sum(sampled.values()) / 2,
        })
    return rows


def _summary(rows: list[dict]) -> dict:
    def maximum(field: str) -> float:
        return max(abs(item[field]) for item in rows)
    def maximum_side(field: str) -> float:
        return max(abs(item[field][side]) for item in rows
                   for side in ("blp", "bln"))
    return {
        "maximum_abs_load_profile_shift_v": maximum_side("load_profile_shift_v"),
        "maximum_abs_acquisition_delta_v": maximum_side("acquisition_delta_v"),
        "maximum_abs_total_vs_original_v": maximum_side("total_vs_original_v"),
        "maximum_abs_differential_load_shift_v": maximum("differential_load_shift_v"),
        "maximum_abs_differential_acquisition_delta_v": maximum(
            "differential_acquisition_delta_v"),
        "maximum_abs_differential_hold_drift_v": maximum(
            "differential_hold_drift_v"),
        "held_common_mode_range_v": [min(item["held_common_mode_2p15ns_v"] for item in rows),
                                     max(item["held_common_mode_2p15ns_v"] for item in rows)],
    }


def analyze(root: str | Path) -> dict:
    root = Path(root).resolve()
    report_path = root / REPORT
    report = json.loads(report_path.read_text(encoding="utf-8"))
    source_path = root / SOURCE
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if (report.get("format") != "automx-cim-wrapper-sample-hold-tt-v1" or
            report.get("status") != "MEASURED_TT_SAMPLE_HOLD_DIAGNOSTIC" or
            report.get("planned_sims") != report.get("completed_sims") or
            report.get("planned_sims") != 3 or
            report.get("source_report_sha256") != _sha(source_path) or
            source.get("status") != "MEASURED_TT_IDLE_AUGMENTATION_DIAGNOSTIC" or
            report.get("pex_sha256") != source.get("pex_sha256") or
            report.get("model_sha256") != source.get("model_sha256")):
        raise ValueError("complete linked TT sample/hold report required")
    rows = []
    for job in report["jobs"]:
        deck = _inside(root, job["deck"])
        log = _inside(root, job["log"])
        receipt = _inside(root, job["checkpoint"])
        checkpoint = json.loads(receipt.read_text(encoding="utf-8"))
        text = log.read_text(encoding="utf-8", errors="replace")
        held = parse_measurements(text, _expected())
        bitline = parse_measurements(text, _bitline_names())
        if (job.get("deck_sha256") != _sha(deck) or
                job.get("log_sha256") != _sha(log) or
                checkpoint.get("status") != "PASS" or
                checkpoint.get("deck_sha256") != job["deck_sha256"] or
                checkpoint.get("log_sha256") != job["log_sha256"] or
                checkpoint.get("pex_sha256") != report["pex_sha256"] or
                checkpoint.get("model_sha256") != report["model_sha256"] or
                checkpoint.get("ngspice_version") != source.get("ngspice_version") or
                held != job.get("measurements_v") or
                held != checkpoint.get("measurements_v") or
                set(held) != set(_expected()) or
                set(bitline) != set(_bitline_names())):
            raise ValueError(f"sample/hold log or checkpoint differs: {job['case']}")
        rows.extend(_decompose(job, bitline))
    if len(rows) != 12:
        raise ValueError("expected all three cases and four columns")
    summary = _summary(rows)
    original = report.get("summary", {})
    if (not math.isclose(summary["maximum_abs_total_vs_original_v"],
                         original.get("maximum_hold_vs_original_820ff_bitline_v", math.nan),
                         rel_tol=0, abs_tol=1e-12) or
            not math.isclose(summary["maximum_abs_differential_hold_drift_v"],
                             original.get("maximum_held_differential_drift_v", math.nan),
                             rel_tol=0, abs_tol=1e-12)):
        raise ValueError("decomposition disagrees with original summary")
    result = {
        "format": "automx-cim-wrapper-sample-hold-decomposition-v1",
        "status": "DIAGNOSTIC_ONLY",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_measured_sha256": _sha(report_path),
        "cases": [job["case"] for job in report["jobs"]],
        "summary": summary,
        "worst_total_vs_original": max(rows, key=lambda item: max(
            abs(value) for value in item["total_vs_original_v"].values())),
        "worst_acquisition": max(rows, key=lambda item: max(
            abs(value) for value in item["acquisition_delta_v"].values())),
        "rows": rows,
        "interpretation": "load profile differs and held sample is 50 ps later; deltas cannot be called ADC error or full wrapper margin",
    }
    target = root / OUTPUT / "decomposition.json"
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    report = analyze(args.root)
    print(json.dumps({key: value for key, value in report.items() if key != "rows"},
                     indent=2))

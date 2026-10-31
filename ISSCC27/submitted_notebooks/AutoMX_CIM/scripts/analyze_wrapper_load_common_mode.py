"""Locate common-mode range violations in a measured 2+2 load holdout.

Recompute common mode from raw BLP/BLN job values. The result is a diagnostic
for selecting a physical input range, never an ADC or wrapper sign-off.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("results/sky130/wrapper_load_full_tt")
IDLE_BASE = Path("results/sky130/wrapper_idle_augmented_tt")


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def analyze(root: str | Path, *, load_ff: int = 820,
            idle_augmented: bool = False) -> dict:
    root = Path(root).resolve()
    path = root / (IDLE_BASE if idle_augmented else BASE) / f"c{load_ff}ff/measured.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    jobs = report.get("jobs", {}).get("fresh_holdout", [])
    training = report.get("training_analysis", {}).get("phases", {})
    published = report.get("fresh_holdout_analysis", {})
    expected_format = ("automx-cim-wrapper-idle-augmented-tt-v1" if idle_augmented else
                       "automx-cim-wrapper-load-full-tt-v1")
    expected_status = ("MEASURED_TT_IDLE_AUGMENTATION_DIAGNOSTIC" if idle_augmented else
                       "MEASURED_TT_LOAD_DIAGNOSTIC")
    planned = "planned_new_sims" if idle_augmented else "planned_sims"
    completed = "completed_new_sims" if idle_augmented else "completed_sims"
    if (report.get("format") != expected_format or
            report.get("status") != expected_status or
            report.get("load_ff") != load_ff or
            report.get(planned) != report.get(completed) or
            report.get(planned) != (74 if idle_augmented else 174) or
            len(jobs) != 64 or not all("measurements_v" in job for job in jobs) or
            set(training) != {"a", "b"} or not published):
        raise ValueError("complete measured load recharacterization required")
    previous_training = None
    if idle_augmented:
        previous_path = root / BASE / f"c{load_ff}ff/measured.json"
        if report.get("previous_820ff_report_sha256") != _sha(previous_path):
            raise ValueError("idle calibration is not linked to the previous 820 fF report")
        previous_training = json.loads(previous_path.read_text(encoding="utf-8"))[
            "training_analysis"]["phases"]
    groups = []
    violations = []
    for phase in ("a", "b"):
        phase_jobs = [job for job in jobs if job.get("phase") == phase]
        if len(phase_jobs) != 32:
            raise ValueError(f"phase {phase} lacks 32 fresh holdout jobs")
        columns = training[phase]["threshold_training"]["columns"]
        if len(columns) != 4:
            raise ValueError(f"phase {phase} lacks four trained column ranges")
        for col in range(4):
            if columns[col].get("column") != col:
                raise ValueError("trained column order changed")
            low, high = map(float, columns[col]["training_common_mode_range_v"])
            if not all(math.isfinite(x) for x in (low, high)) or low > high:
                raise ValueError("invalid trained common-mode range")
            samples = []
            for job in phase_jobs:
                values = job["measurements_v"]
                for time in ("t19", "t21"):
                    blp = float(values[f"blp_c{col}_{time}"])
                    bln = float(values[f"bln_c{col}_{time}"])
                    cm = (blp + bln) / 2
                    if not all(math.isfinite(x) for x in (blp, bln, cm)):
                        raise ValueError(f"nonfinite bitline: {job['case']} c{col} {time}")
                    below = max(low - cm, 0.0)
                    above = max(cm - high, 0.0)
                    item = {"case": job["case"], "phase": phase, "column": col,
                            "time": time, "common_mode_v": cm,
                            "extension_below_training_v": below,
                            "extension_above_training_v": above}
                    samples.append(item)
                    if below or above:
                        violations.append(item)
            groups.append({
                "phase": phase, "column": col, "training_range_v": [low, high],
                "previous_training_range_v": (
                    previous_training[phase]["threshold_training"]["columns"][col][
                        "training_common_mode_range_v"] if previous_training else None),
                "holdout_range_v": [min(item["common_mode_v"] for item in samples),
                                    max(item["common_mode_v"] for item in samples)],
                "holdout_samples": len(samples),
                "below_training_samples": sum(
                    bool(item["extension_below_training_v"]) for item in samples),
                "above_training_samples": sum(
                    bool(item["extension_above_training_v"]) for item in samples),
                "outside_training_samples": sum(
                    bool(item["extension_below_training_v"] or
                         item["extension_above_training_v"]) for item in samples),
                "maximum_below_extension_v": max(
                    item["extension_below_training_v"] for item in samples),
                "maximum_above_extension_v": max(
                    item["extension_above_training_v"] for item in samples),
            })
    expected = published.get("common_mode_outside_training_samples")
    if (len(violations) != expected or
            len(violations) != report.get("summary", {}).get(
                "holdout_common_mode_outside_training_samples")):
        raise ValueError("raw bitlines disagree with published common-mode count")
    worst = sorted(violations, key=lambda item: -max(
        item["extension_below_training_v"], item["extension_above_training_v"]))[:12]
    result = {
        "format": "automx-cim-wrapper-load-common-mode-diagnostic-v1",
        "status": "DIAGNOSTIC_ONLY", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_report_sha256": _sha(path), "source_format": expected_format,
        "load_ff": load_ff,
        "holdout_samples": sum(group["holdout_samples"] for group in groups),
        "below_training_samples": sum(group["below_training_samples"] for group in groups),
        "above_training_samples": sum(group["above_training_samples"] for group in groups),
        "outside_training_samples": len(violations),
        "maximum_below_extension_v": max(group["maximum_below_extension_v"]
                                          for group in groups),
        "maximum_above_extension_v": max(group["maximum_above_extension_v"]
                                          for group in groups),
        "groups": groups, "worst_violations": worst,
        "scope": "raw TT PEX bitline common-mode only; physical sample/hold and ADC input range unmeasured",
    }
    target = path.with_name("common_mode_diagnostic.json")
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--load-ff", type=int, default=820)
    parser.add_argument("--idle-augmented", action="store_true",
                        help="analyze the new idle-calibrated MHA 96..127 holdout")
    args = parser.parse_args()
    print(json.dumps(analyze(args.root, load_ff=args.load_ff,
                             idle_augmented=args.idle_augmented), indent=2))

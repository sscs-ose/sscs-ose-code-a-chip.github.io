#!/usr/bin/env python3
"""Freeze measured held-node requirements for a physical sense/readout design."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402
from scripts import run_flow2_recovery_pvt_diagnostic as diagnostic  # noqa: E402

OUTPUT = Path("results/sky130/wrapper_readout_requirements")


def derive(training: list[dict], validation: list[dict], decoder: dict) -> dict:
    if len(validation) != 64 or not decoder["training_margin_candidate"]:
        raise ValueError("frozen trained decoder and 64 held-out phase jobs required")
    values = []
    for cohort, jobs in (("training", training), ("observed_validation", validation)):
        for job in jobs:
            for col in range(4):
                raw = job["measurements_v"]
                positive = float(raw[f"aper_hblp_c{col}_late"])
                negative = float(raw[f"aper_hbln_c{col}_late"])
                values.append({"cohort": cohort, "case": job["case"], "phase": job["phase"],
                               "column": col, "positive_v": positive,
                               "negative_v": negative,
                               "common_mode_v": (positive + negative) / 2,
                               "differential_v": negative - positive,
                               "integer_sum": int(job["integer_sums"][col])})
    if len(values) != (len(training) + 64) * 4:
        raise ValueError("held-node set is incomplete")
    thresholds = {phase: [
        {"column": col, "sum_levels": item["sum_levels"],
         "thresholds_v": item["thresholds_v"],
         "training_common_mode_range_v": item["training_common_mode_range_v"]}
        for col, item in enumerate(decoder["phases"][phase]["columns"])]
        for phase in ("a", "b")}
    for phase in ("a", "b"):
        if any(len(item["sum_levels"]) != 39 or len(item["thresholds_v"]) != 38
               for item in thresholds[phase]):
            raise ValueError("complete 39-level 2+2 decoder required")
    return {
        "sampling_turnoff_start_ns": 2.100,
        "held_measure_time_ns": 2.400,
        "load_ff": 820,
        "switch_width_um": campaign.WIDTH_UM,
        "turnoff_fall_ps": campaign.FALL_PS,
        "target_total_differential_error_v": 0.0008,
        "required_partial_levels_per_phase_column": 39,
        "thresholds_per_phase_column": 38,
        "held_voltage_min_v": min(min(v["positive_v"], v["negative_v"]) for v in values),
        "held_voltage_max_v": max(max(v["positive_v"], v["negative_v"]) for v in values),
        "held_common_mode_min_v": min(v["common_mode_v"] for v in values),
        "held_common_mode_max_v": max(v["common_mode_v"] for v in values),
        "observed_validation_zero_cm_max_v": max(
            v["common_mode_v"] for v in values
            if v["cohort"] == "observed_validation" and v["integer_sum"] == 0),
        "observed_validation_sample_count": len(validation) * 4,
        "frozen_thresholds": thresholds,
        "unresolved": ["physical input common-mode and rail range",
                       "transistor-level comparator offset/noise",
                       "reference generation and 38-threshold realization",
                       "physical switch/clock PEX and continuous aperture",
                       "conversion latency and power",
                       "wrapper layout and seven sign-off checks"],
    }


def run(root: str | Path) -> dict:
    root = Path(root).resolve()
    recovery, inputs, training, decoder, source_sha = diagnostic._source(root)
    result = {"format": "automx-cim-wrapper-readout-requirements-v1",
              "status": "MEASURED_INPUT_RANGE_REQUIREMENTS_NOT_LAYOUT",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "source_recovery_sha256": source_sha,
              "script_sha256": campaign._sha(Path(__file__)),
              "pex_sha256": inputs["pex_sha"],
              "frozen_decoder_sha256": decoder["frozen_decoder_sha256"],
              "validation_status": recovery["status"],
              "validation_common_mode_outside_training_samples": recovery[
                  "groups"]["fresh_validation"]["analysis"][
                      "common_mode_outside_training_samples"],
              **derive(training, recovery["groups"]["fresh_validation"]["jobs"], decoder),
              "not_signoff": "measured TT input envelope and frozen thresholds only; no physical ADC, schematic or wrapper views"}
    folder = root / OUTPUT / (f"recovery_{source_sha[:12]}_runner_"
                              f"{result['script_sha256'][:12]}")
    path = folder / "requirements.json"
    if path.is_file():
        previous = campaign._read(path)
        if {k: v for k, v in previous.items() if k != "timestamp_utc"} != {
                k: v for k, v in result.items() if k != "timestamp_utc"}:
            raise FileExistsError(f"wrapper requirements changed: {path}")
        return previous
    campaign._save(path, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = run(args.root)
    print(json.dumps({key: value for key, value in result.items()
                      if key != "frozen_thresholds"}, indent=2))

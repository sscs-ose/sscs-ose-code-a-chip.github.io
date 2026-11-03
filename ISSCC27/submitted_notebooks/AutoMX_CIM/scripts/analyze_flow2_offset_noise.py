#!/usr/bin/env python3
"""Offline offset/noise sensitivity of the frozen Flow-2 decoder.

The input voltages are measured TT held nodes. Offset and Gaussian noise are
injected mathematically; this is not a transistor-noise or ADC measurement.
"""

from __future__ import annotations

import argparse
from bisect import bisect_right
from datetime import datetime, timezone
from math import erf, sqrt
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402
from scripts import run_flow2_recovery_pvt_diagnostic as diagnostic  # noqa: E402

OFFSETS_MV = (-0.8, -0.4, 0.0, 0.4, 0.8)
NOISE_RMS_MV = (0.0, 0.1, 0.2, 0.4, 0.8)
OUTPUT = Path("results/sky130/flow2_offset_noise")


def _correct_probability(value: float, expected: int, levels: list[int],
                         thresholds: list[float], offset_v: float,
                         noise_sigma_v: float) -> float:
    if expected not in levels or len(thresholds) != len(levels) - 1:
        raise ValueError("expected sum is absent from the frozen decoder")
    center = value + offset_v
    if noise_sigma_v == 0:
        return float(levels[bisect_right(thresholds, center)] == expected)
    index = levels.index(expected)
    def cdf(bound: float) -> float:
        return 0.5 * (1 + erf((bound - center) / (noise_sigma_v * sqrt(2))))
    low = 0.0 if index == 0 else cdf(thresholds[index - 1])
    high = 1.0 if index == len(levels) - 1 else cdf(thresholds[index])
    return max(0.0, min(1.0, high - low))


def analyze(jobs: list[dict], decoder: dict) -> dict:
    if len(jobs) != 64 or len({job["case"] for job in jobs}) != 64:
        raise ValueError("64 unique fresh MHA phase jobs required")
    samples = []
    for job in jobs:
        phase = job["phase"]
        for column in range(4):
            item = decoder["phases"][phase]["columns"][column]
            differential, common_mode = campaign._held(job, column)
            samples.append((differential, common_mode,
                            int(job["integer_sums"][column]),
                            item["sum_levels"], item["thresholds_v"]))
    grid = []
    for offset_mv in OFFSETS_MV:
        for sigma_mv in NOISE_RMS_MV:
            probabilities = [_correct_probability(value, expected, levels,
                             thresholds, offset_mv / 1000, sigma_mv / 1000)
                             for value, _, expected, levels, thresholds in samples]
            grid.append({"offset_mv": offset_mv, "assumed_noise_rms_mv": sigma_mv,
                         "expected_partial_decode_errors": sum(1 - p for p in probabilities),
                         "mean_partial_error_probability": sum(1 - p for p in probabilities) / len(samples),
                         "maximum_sample_error_probability": max(1 - p for p in probabilities),
                         "sample_count": len(samples)})
    return {"status": "OFFLINE_GAUSSIAN_INJECTION_DIAGNOSTIC",
            "sample_count": len(samples), "grid": grid,
            "held_common_mode_min_v": min(sample[1] for sample in samples),
            "held_common_mode_max_v": max(sample[1] for sample in samples),
            "assumptions": "independent additive differential Gaussian noise and fixed differential offset; no physical comparator, reference or common-mode error model",
            "not_signoff": "analytic sensitivity from measured TT held nodes; no transistor noise, ADC offset measurement, BER test or PVT sign-off"}


def run(root: str | Path) -> dict:
    root = Path(root).resolve()
    report, inputs, _, decoder, recovery_sha = diagnostic._source(root)
    jobs = report["groups"]["fresh_validation"]["jobs"]
    result = {"format": "automx-cim-flow2-offset-noise-offline-v1",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "source_recovery_sha256": recovery_sha,
              "script_sha256": campaign._sha(Path(__file__)),
              "pex_sha256": inputs["pex_sha"],
              "frozen_decoder_sha256": decoder["frozen_decoder_sha256"],
              **analyze(jobs, decoder)}
    folder = root / OUTPUT / (f"recovery_{recovery_sha[:12]}_runner_"
                              f"{result['script_sha256'][:12]}")
    path = folder / "summary.json"
    if path.is_file():
        prior = campaign._read(path)
        if {key: value for key, value in prior.items() if key != "timestamp_utc"} != {
                key: value for key, value in result.items() if key != "timestamp_utc"}:
            raise FileExistsError(f"offset/noise screen changed: {path}")
        return prior
    campaign._save(path, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    value = run(args.root)
    print(json.dumps({key: item for key, item in value.items() if key != "grid"}, indent=2))
    print("grid:", len(value["grid"]), "points")

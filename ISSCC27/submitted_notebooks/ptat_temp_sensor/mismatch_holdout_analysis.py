#!/usr/bin/env python3
"""Retrospective split-sample calibration robustness study for SKY130 mismatch MC.

The script tunes a six-anchor PWL schedule on one disjoint half of the retained
Monte-Carlo seeds, evaluates it on the other half, then repeats with the halves
reversed. It does not change the release architecture by itself.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import re
from pathlib import Path

SEED_RE = re.compile(r"sample_(\d+)\.csv$")


def percentile(xs: list[float], q: float) -> float:
    ys = sorted(xs)
    pos = (len(ys) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return ys[lo]
    return ys[lo] * (hi - pos) + ys[hi] * (pos - lo)


def wilson(k: int, n: int, z: float = 1.959963984540054) -> list[float]:
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [100 * (mid - half), 100 * (mid + half)]


def load_sample(path: Path) -> tuple[int, list[float], list[float]]:
    match = SEED_RE.search(path.name)
    if not match:
        raise ValueError(f"unexpected sample filename: {path.name}")
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, skipinitialspace=True))
    temps = [float(row["temp_c"]) for row in rows]
    volts = [float(row["dvgs_v"]) for row in rows]
    if temps != sorted(set(temps)) or len(temps) < 7:
        raise ValueError(f"{path}: invalid temperature grid")
    return int(match.group(1)), temps, volts


def max_error(
    temps: list[float],
    volts: list[float],
    anchors: tuple[float, ...],
) -> float:
    index = {temp: i for i, temp in enumerate(temps)}
    try:
        idx = [index[anchor] for anchor in anchors]
    except KeyError as exc:
        raise ValueError(f"anchor missing from grid: {exc.args[0]}") from exc
    worst = 0.0
    for ia, ib in zip(idx[:-1], idx[1:]):
        if volts[ib] == volts[ia]:
            raise ValueError("zero PWL voltage span")
        gain = (temps[ib] - temps[ia]) / (volts[ib] - volts[ia])
        offset = temps[ia] - gain * volts[ia]
        for j in range(ia, ib + 1):
            worst = max(worst, abs(gain * volts[j] + offset - temps[j]))
    return worst


def metrics(errors: list[float], target: float) -> dict:
    passes = sum(error <= target for error in errors)
    return {
        "samples": len(errors),
        "passes": passes,
        "yield_percent": 100 * passes / len(errors),
        "yield_wilson_95_percent_ci": wilson(passes, len(errors)),
        "mean_max_abs_error_c": sum(errors) / len(errors),
        "p50_max_abs_error_c": percentile(errors, 0.50),
        "p95_max_abs_error_c": percentile(errors, 0.95),
        "p99_max_abs_error_c": percentile(errors, 0.99),
        "worst_max_abs_error_c": max(errors),
    }


def choose(samples, temps, target: float):
    mandatory = 25.0
    if mandatory not in temps:
        raise ValueError("mandatory 25 C anchor missing")
    interior = [temp for temp in temps[1:-1] if temp != mandatory]
    best = None
    for extra in itertools.combinations(interior, 3):
        anchors = tuple(sorted((temps[0], *extra, mandatory, temps[-1])))
        errors = [
            max_error(sample_t, sample_v, anchors)
            for _, sample_t, sample_v in samples
        ]
        result = metrics(errors, target)
        key = (
            -result["yield_percent"],
            result["p95_max_abs_error_c"],
            result["worst_max_abs_error_c"],
            result["mean_max_abs_error_c"],
            anchors,
        )
        if best is None or key < best[0]:
            best = (key, anchors, result)
    return best[1], best[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-c", type=float, default=0.5)
    parser.add_argument("--artifact-id", type=int, default=10910494009)
    parser.add_argument(
        "--artifact-sha256",
        default="48987112cb7a7678d5b8cc0d279fa2ee4e4c51dd69fadcf34dcce85cbc77c3d9",
    )
    parser.add_argument("--workflow-run-id", type=int, default=36256551286)
    parser.add_argument(
        "--source-commit",
        default="54e8b2d46ec2ca3950c944390870cba29656594c",
    )
    args = parser.parse_args()

    samples = [
        load_sample(path)
        for path in sorted(args.input_dir.glob("sample_*.csv"))
    ]
    samples.sort(key=lambda item: item[0])
    if len(samples) != 100:
        raise SystemExit(f"expected 100 samples, got {len(samples)}")
    grid = samples[0][1]
    if any(sample[1] != grid for sample in samples):
        raise SystemExit("temperature grids differ across samples")

    first, second = samples[:50], samples[50:]
    anchors_a, train_a = choose(first, grid, args.target_c)
    holdout_b_errors = [
        max_error(sample_t, sample_v, anchors_a)
        for _, sample_t, sample_v in second
    ]
    anchors_b, train_b = choose(second, grid, args.target_c)
    holdout_a_errors = [
        max_error(sample_t, sample_v, anchors_b)
        for _, sample_t, sample_v in first
    ]
    all_errors = [
        max_error(sample_t, sample_v, anchors_a)
        for _, sample_t, sample_v in samples
    ]

    output = {
        "status": "PASS" if anchors_a == anchors_b else "WARN",
        "study_type": "retrospective two-fold split-sample robustness study",
        "evidence_boundary": (
            "The two 50-seed folds come from one retained 100-seed tt_mm run. "
            "This reduces tuning leakage relative to fitting all seeds, but it is "
            "not a new independent Monte-Carlo run and does not validate "
            "branch-current matching."
        ),
        "candidate_space": {
            "anchor_count": 6,
            "endpoints_fixed_c": [grid[0], grid[-1]],
            "mandatory_anchor_c": 25.0,
            "other_anchors": "choose 3 from remaining interior 5 C grid points",
            "selection_objective": [
                "maximize fraction with max abs temperature error <= target",
                "minimize p95 max abs error",
                "minimize worst max abs error",
                "minimize mean max abs error",
                "lexicographic anchor tie-break",
            ],
        },
        "target_max_abs_error_c": args.target_c,
        "fold_a_train_seeds": [first[0][0], first[-1][0]],
        "fold_b_holdout_seeds": [second[0][0], second[-1][0]],
        "fold_a_selected_anchors_c": list(anchors_a),
        "fold_a_training": train_a,
        "fold_b_holdout": metrics(holdout_b_errors, args.target_c),
        "fold_b_selected_anchors_c": list(anchors_b),
        "fold_b_training": train_b,
        "fold_a_reverse_holdout": metrics(holdout_a_errors, args.target_c),
        "same_schedule_selected_by_both_folds": anchors_a == anchors_b,
        "combined_point_estimate_for_shared_schedule": metrics(
            all_errors,
            args.target_c,
        ),
        "source": {
            "github_workflow_run_id": args.workflow_run_id,
            "artifact_id": args.artifact_id,
            "artifact_zip_sha256": args.artifact_sha256,
            "source_commit": args.source_commit,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

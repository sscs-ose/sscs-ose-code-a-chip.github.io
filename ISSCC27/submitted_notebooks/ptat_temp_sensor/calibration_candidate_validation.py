#!/usr/bin/env python3
"""Validate a pre-declared calibration candidate on retained mismatch samples.

This tool deliberately does not search for or tune anchor locations. The candidate
schedule must already be recorded in release_requirements.json. It evaluates that
fixed schedule on a separate Monte-Carlo sample set and reports calibration yield
separately from the analog branch-current mismatch yield.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).resolve().parent
SEED_RE = re.compile(r"sample_(\d+)\.csv$")


def candidate_status_is_unpromoted(status: object) -> bool:
    return isinstance(status, str) and status.endswith("NOT_RELEASE_VALIDATED")


def percentile(xs: list[float], q: float) -> float:
    ys = sorted(xs)
    if not ys:
        return math.nan
    pos = (len(ys) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ys[lo]
    return ys[lo] * (hi - pos) + ys[hi] * (pos - lo)


def read_rows(path: Path) -> list[dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        raw = list(csv.DictReader(handle, skipinitialspace=True))
    rows = [{k.strip(): float(v) for k, v in row.items()} for row in raw]
    required = {"temp_c", "dvgs_v", "branch_small_a", "branch_large_a"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"{path}: required columns are missing")
    if not all(all(math.isfinite(v) for v in row.values()) for row in rows):
        raise ValueError(f"{path}: non-finite value")
    return rows


def branch_mismatch_percent(branch_small_a: float, branch_large_a: float) -> float:
    small = abs(branch_small_a)
    large = abs(branch_large_a)
    denom = (small + large) / 2.0
    if denom <= 0.0:
        raise ValueError("branch currents must have a positive mean magnitude")
    return abs(small - large) / denom * 100.0


def calibration_errors(
    rows: list[dict[str, float]], anchors_c: list[float]
) -> list[float]:
    temps = [row["temp_c"] for row in rows]
    dvgs = [row["dvgs_v"] for row in rows]
    if any(b <= a for a, b in zip(temps, temps[1:])):
        raise ValueError("temperature grid must be strictly increasing")

    indices: list[int] = []
    for anchor in anchors_c:
        hits = [i for i, temp in enumerate(temps) if abs(temp - anchor) < 1e-9]
        if len(hits) != 1:
            raise ValueError(
                f"calibration anchor {anchor:g} C is missing or duplicated"
            )
        indices.append(hits[0])
    if indices != sorted(indices) or len(set(indices)) != len(indices):
        raise ValueError("calibration anchors must be unique and increasing")
    if indices[0] != 0 or indices[-1] != len(temps) - 1:
        raise ValueError(
            "calibration anchors must include both temperature endpoints"
        )

    estimated = [math.nan] * len(temps)
    for ia, ib in zip(indices[:-1], indices[1:]):
        span = dvgs[ib] - dvgs[ia]
        if span == 0.0:
            raise ValueError("zero PWL voltage span")
        gain = (temps[ib] - temps[ia]) / span
        offset = temps[ia] - gain * dvgs[ia]
        for index in range(ia, ib + 1):
            estimated[index] = gain * dvgs[index] + offset
    if any(not math.isfinite(value) for value in estimated):
        raise ValueError("calibration did not cover the full temperature grid")
    return [
        estimate - actual for estimate, actual in zip(estimated, temps)
    ]


def seed_from_path(path: Path) -> int:
    match = SEED_RE.search(path.name)
    if not match:
        raise ValueError(f"cannot infer seed from {path.name}")
    return int(match.group(1))


def summarize_errors(values: list[float], target_c: float) -> dict:
    return {
        "yield_percent_le_target": (
            100.0 * sum(v <= target_c for v in values) / len(values)
        ),
        "mean_c": mean(values),
        "std_c": pstdev(values) if len(values) > 1 else 0.0,
        "p50_c": percentile(values, 0.50),
        "p95_c": percentile(values, 0.95),
        "p99_c": percentile(values, 0.99),
        "worst_c": max(values),
    }


def analyze(
    files: list[Path],
    baseline_anchors_c: list[float],
    candidate_anchors_c: list[float],
    error_target_c: float,
    branch_target_percent: float,
    yield_target_percent: float,
    minimum_samples: int,
) -> dict:
    if len(files) < minimum_samples:
        raise ValueError(
            f"need at least {minimum_samples} samples for validation; "
            f"got {len(files)}"
        )

    baseline_max_errors: list[float] = []
    candidate_max_errors: list[float] = []
    branch_max_mismatch: list[float] = []
    seeds: list[int] = []
    reference_grid: list[float] | None = None

    for path in sorted(files):
        rows = read_rows(path)
        grid = [row["temp_c"] for row in rows]
        if reference_grid is None:
            reference_grid = grid
        elif grid != reference_grid:
            raise ValueError(
                f"{path}: temperature grid differs from other samples"
            )

        seeds.append(seed_from_path(path))
        baseline_max_errors.append(
            max(
                abs(value)
                for value in calibration_errors(rows, baseline_anchors_c)
            )
        )
        candidate_max_errors.append(
            max(
                abs(value)
                for value in calibration_errors(rows, candidate_anchors_c)
            )
        )
        branch_max_mismatch.append(
            max(
                branch_mismatch_percent(
                    row["branch_small_a"], row["branch_large_a"]
                )
                for row in rows
            )
        )

    if len(set(seeds)) != len(seeds):
        raise ValueError("duplicate Monte-Carlo seeds")

    baseline = summarize_errors(baseline_max_errors, error_target_c)
    candidate = summarize_errors(candidate_max_errors, error_target_c)
    branch_yield = (
        100.0
        * sum(value <= branch_target_percent for value in branch_max_mismatch)
        / len(branch_max_mismatch)
    )
    calibration_pass = (
        candidate["yield_percent_le_target"] >= yield_target_percent
        and candidate["p95_c"] <= error_target_c
    )
    branch_pass = branch_yield >= yield_target_percent

    return {
        "status": "PASS" if calibration_pass else "FAIL",
        "scope": "fixed calibration-candidate validation only",
        "samples": len(files),
        "seeds": {"min": min(seeds), "max": max(seeds)},
        "temperature_c": reference_grid,
        "targets": {
            "max_abs_error_c": error_target_c,
            "yield_percent": yield_target_percent,
            "branch_mismatch_percent": branch_target_percent,
        },
        "baseline": {
            "anchors_c": baseline_anchors_c,
            **baseline,
        },
        "candidate": {
            "anchors_c": candidate_anchors_c,
            **candidate,
            "status": "PASS" if calibration_pass else "FAIL",
        },
        "branch_mismatch": {
            "yield_percent_le_target": branch_yield,
            "p95_percent": percentile(branch_max_mismatch, 0.95),
            "worst_percent": max(branch_max_mismatch),
            "status": "PASS" if branch_pass else "FAIL",
            "note": (
                "Reported separately because digital calibration cannot repair "
                "analog branch-current mismatch."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=ROOT / "results" / "mismatch_mc",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "mismatch_mc"
        / "candidate_validation.json",
    )
    args = parser.parse_args()

    try:
        release = json.loads(
            (ROOT / "release_requirements.json").read_text(encoding="utf-8")
        )
        design = json.loads(
            (ROOT / "design_requirements.json").read_text(encoding="utf-8")
        )
        candidate_info = release["known_evidence"][
            "six_point_candidate_20260926"
        ]
        if not candidate_status_is_unpromoted(candidate_info.get("status")):
            raise ValueError(
                "candidate must remain pre-declared and unpromoted "
                "during validation"
            )

        files = sorted(args.input_dir.glob("sample_*.csv"))
        result = analyze(
            files=files,
            baseline_anchors_c=[
                float(x)
                for x in release["release_architecture"][
                    "calibration_anchors_c"
                ]
            ],
            candidate_anchors_c=[
                float(x) for x in candidate_info["calibration_anchors_c"]
            ],
            error_target_c=float(
                release["release_targets"][
                    "dense_grid_pwl_max_abs_error_c_max"
                ]
            ),
            branch_target_percent=float(
                design["mirror_branch_mismatch_percent_max"]
            ),
            yield_target_percent=float(
                release["release_targets"][
                    "mismatch_target_yield_percent"
                ]
            ),
            minimum_samples=int(
                release["release_targets"]["mismatch_min_samples"]
            ),
        )

        summary_path = args.input_dir / "summary.json"
        if summary_path.is_file():
            mismatch_summary = json.loads(
                summary_path.read_text(encoding="utf-8")
            )
            result["source_provenance"] = mismatch_summary.get(
                "provenance", {}
            )
        else:
            result["source_provenance"] = {}

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        print(
            f"CALIBRATION CANDIDATE VALIDATION: FAIL: {exc}",
            file=sys.stderr,
        )
        return 1

    print("CALIBRATION CANDIDATE VALIDATION:", result["status"])
    print(
        "candidate yield:",
        result["candidate"]["yield_percent_le_target"],
        "p95 C:",
        result["candidate"]["p95_c"],
        "branch-mismatch yield:",
        result["branch_mismatch"]["yield_percent_le_target"],
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

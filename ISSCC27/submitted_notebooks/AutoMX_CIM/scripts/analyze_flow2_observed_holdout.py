#!/usr/bin/env python3
"""Read-only scalar-decoder feasibility diagnostic on an already seen holdout.

Pooling the failed holdout with training is diagnostic only. The pooled values
must never be used as a frozen decoder or counted as independent validation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402


def analyze(path: str | Path) -> dict:
    report = campaign._read(Path(path))
    if (report.get("format") != "automx-cim-flow2-remaining-measurements-v1" or
            report.get("status") != "BLOCKED_FRESH_TT_HOLDOUT"):
        raise ValueError("measured failed Flow-2 campaign summary required")
    groups = report["groups"]
    training = groups["held_node_training"]["jobs"]
    observed = groups["fresh_mha_holdout"]["jobs"]
    if len(training) != 120 or len(observed) != 64 or any(
            "measurements_v" not in job for job in training + observed):
        raise ValueError("complete 120+64 measured cases required")
    budget = float(report["offline_sensitivity"]["combined_budget_v"])
    pooled = campaign._train(training + observed, budget)
    problematic = []
    for phase in ("a", "b"):
        for column in pooled["phases"][phase]["columns"]:
            intervals = column["intervals"]
            for lower, higher in zip(intervals, intervals[1:]):
                gap = higher["minimum_v"] - lower["maximum_v"]
                if gap <= 2 * budget:
                    problematic.append({"phase": phase,
                                        "column": column["column"],
                                        "lower_sum": lower["sum"],
                                        "higher_sum": higher["sum"],
                                        "best_possible_symmetric_margin_v": gap / 2,
                                        "gap_v": gap})
    return {"format": "automx-cim-observed-holdout-feasibility-v1",
            "source_sha256": campaign._sha(Path(path)),
            "source_status": report["status"],
            "training_cases": len(training),
            "observed_holdout_cases": len(observed),
            "required_adjacent_gap_v": 2 * budget,
            "pooled_minimum_gap_v": pooled["minimum_gap_v"],
            "too_small_or_overlapping_pairs": problematic,
            "scalar_threshold_possible_on_observed_set_at_budget": not problematic,
            "not_for_model_selection": "observed holdout values are included solely to test a necessary feasibility bound; a new holdout remains required"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze(args.summary), indent=2))

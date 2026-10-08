"""Read-only marginal failure counts from the complete published finest-row table."""

import argparse
import json

import pandas as pd

from presentation import pvt45_results as pvt


FACTORS = (
    ("corner", "Corner", pvt.CORNERS),
    ("vdd_v", "Supply (V)", pvt.VOLTAGES),
    ("temperature_c", "Temperature (C)", pvt.TEMPERATURES),
    ("differential_mv", "Input (mV)", pvt.INPUTS_MV),
)


def audit(frame: pd.DataFrame) -> dict:
    coverage = pvt.coverage_table(frame)
    for column in ("point_id", "finest_attempt_id"):
        if column not in frame or frame[column].isna().any() \
                or frame[column].eq("").any() or frame[column].duplicated().any():
            raise ValueError(f"Every finest record requires a unique {column}")
    for row in coverage.to_dict("records"):
        expected = (156, 0, 24) if (row["mode"], row["deadline_ns"]) == ("rc", 1) else (180, 0, 0)
        actual = tuple(row[f"confirmed_{label}"] for label in ("correct", "wrong", "unresolved"))
        if actual != expected or row["numerical_unknown"] != 0 or row["not_run"] != 0:
            raise ValueError("Coverage differs from the published SC/RC 1/2 ns counts")
    rc = frame[frame["mode"].eq("rc")]
    marginals = []
    for field, label, levels in FACTORS:
        partition = []
        for level in levels:
            part = rc[rc[field].eq(level)]
            record = {
                "factor": field, "factor_label": label,
                "level": level, "points": len(part),
                **{
                    f"{outcome}_{deadline}ns": int(part[f"outcome_{deadline}ns"].eq(outcome).sum())
                    for deadline in pvt.DEADLINES
                    for outcome in ("correct", "unresolved", "wrong")
                },
            }
            if record["points"] != 180 // len(levels):
                raise ValueError(f"Unexpected factor denominator: {field}/{level}")
            partition.append(record)
        if sum(row["points"] for row in partition) != 180 \
                or sum(row["unresolved_1ns"] for row in partition) != 24:
            raise ValueError(f"Marginal partition does not conserve the fixed grid: {field}")
        marginals.extend(partition)
    failed = rc[rc.outcome_1ns.eq("unresolved")].sort_values(list(pvt.POINT_KEY))
    return {
        "scope": "record_level_marginals_not_raw_waveform_remeasurement",
        "counts_reference": "published_full_grid_180_points_per_mode",
        "aggregation": "four_overlapping_views_of_the_same_points_not_independent_counts",
        "causal_or_statistical_significance_claim": False,
        "rc_model_physical_fidelity_qualified": False,
        "coverage": coverage.to_dict("records"),
        "marginals": marginals,
        "unresolved_1ns_records": failed[[
            "point_id", *pvt.POINT_KEY, "finest_attempt_id", "run_identity",
            "outcome_1ns", "outcome_2ns", "decision_time_ns_2ns",
        ]].to_dict("records"),
    }


def markdown_table(result: dict) -> str:
    lines = [
        "| Factor | Level | RC correct at 1 ns | RC unresolved at 1 ns | RC correct at 2 ns |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in result["marginals"]:
        level = row["level"]
        rendered = level.upper() if isinstance(level, str) else f"{level:g}"
        if row["factor"] == "differential_mv" and level > 0:
            rendered = "+" + rendered
        lines.append(
            f"| {row['factor_label']} | {rendered} | "
            f"{row['correct_1ns']}/{row['points']} | "
            f"{row['unresolved_1ns']}/{row['points']} | "
            f"{row['correct_2ns']}/{row['points']} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()
    try:
        result = audit(pvt.load_results()["frame"])
        result["source_csv_sha256"] = pvt.REFERENCE_FILES["measurements.csv"]
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        parser.exit(1, f"Full-grid failure audit FAILED: {error}\n")
    print(markdown_table(result) if args.format == "markdown"
          else json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

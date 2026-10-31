
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

INPUT_CSV = RESULTS / "baseline.csv"
OUTPUT_CSV = RESULTS / "comparison.csv"


def main():
    if not INPUT_CSV.is_file():
        raise FileNotFoundError(
            f"Baseline file not found: {INPUT_CSV}"
        )

    with INPUT_CSV.open(
        "r", newline="", encoding="utf-8"
    ) as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    measurements = {}

    for row in rows:
        architecture = row["architecture"]
        width = int(row["width"])
        cells = int(row["generic_logic_cells"])

        measurements.setdefault(width, {})[architecture] = cells

    report = []

    for width in sorted(measurements):
        values = measurements[width]

        if "conventional" not in values or "karatsuba" not in values:
            raise ValueError(
                f"Width {width} must have both architectures."
            )

        conventional = values["conventional"]
        karatsuba = values["karatsuba"]

        reduction = (
            (conventional - karatsuba)
            / conventional
            * 100
        )

        if conventional < karatsuba:
            lower_cells = "conventional"
        elif karatsuba < conventional:
            lower_cells = "karatsuba"
        else:
            lower_cells = "tie"

        report.append({
            "width": width,
            "conventional_cells": conventional,
            "karatsuba_cells": karatsuba,
            "cell_count_reduction_percent": round(reduction, 2),
            "lower_cell_count_architecture": lower_cells,
        })

    with OUTPUT_CSV.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        fields = [
            "width",
            "conventional_cells",
            "karatsuba_cells",
            "cell_count_reduction_percent",
            "lower_cell_count_architecture",
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report)

    print("\nAutoAccel Architecture Comparison")
    print("-" * 70)

    for row in report:
        print(
            f"N={row['width']:>2}: "
            f"Conventional={row['conventional_cells']:>6}, "
            f"Karatsuba={row['karatsuba_cells']:>6}, "
            f"Reduction={row['cell_count_reduction_percent']:>7.2f}%, "
            f"Lower count={row['lower_cell_count_architecture']}"
        )

    print(f"\nComparison saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()


import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
INPUT_CSV = RESULTS_DIR / "comparison.csv"
OUTPUT_CSV = RESULTS_DIR / "architecture_recommendations.csv"


def load_results(csv_path):
    if not csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    required = {
        "width",
        "conventional_cells",
        "karatsuba_cells",
    }

    with csv_path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(
                "CSV must contain width, conventional_cells, "
                "and karatsuba_cells."
            )

        results = []
        seen_widths = set()

        for line_number, row in enumerate(reader, start=2):
            try:
                width = int(row["width"])
                conventional = int(row["conventional_cells"])
                karatsuba = int(row["karatsuba_cells"])
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid numeric value on line {line_number}"
                ) from error

            if width <= 0 or conventional <= 0 or karatsuba <= 0:
                raise ValueError(
                    f"Values must be positive on line {line_number}"
                )

            if width in seen_widths:
                raise ValueError(f"Duplicate width in CSV: {width}")

            seen_widths.add(width)
            results.append({
                "width": width,
                "conventional_cells": conventional,
                "karatsuba_cells": karatsuba,
            })

    if not results:
        raise ValueError("Input CSV contains no data rows.")

    return sorted(results, key=lambda row: row["width"])


def select_architecture(row):
    conventional = row["conventional_cells"]
    karatsuba = row["karatsuba_cells"]

    if conventional < karatsuba:
        winner = "Conventional"
        reduction = (karatsuba - conventional) / karatsuba * 100
    elif karatsuba < conventional:
        winner = "Karatsuba"
        reduction = (conventional - karatsuba) / conventional * 100
    else:
        winner = "Tie"
        reduction = 0.0

    return winner, reduction


def save_recommendations(results, output_path):
    columns = [
        "width",
        "conventional_cells",
        "karatsuba_cells",
        "recommended_architecture",
        "cell_count_reduction_percent",
        "selection_metric",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()

        for row in results:
            winner, reduction = select_architecture(row)

            writer.writerow({
                "width": row["width"],
                "conventional_cells": row["conventional_cells"],
                "karatsuba_cells": row["karatsuba_cells"],
                "recommended_architecture": winner,
                "cell_count_reduction_percent": f"{reduction:.2f}",
                "selection_metric": "generic_logic_cell_count",
            })


def main():
    results = load_results(INPUT_CSV)

    print("=" * 72)
    print("AUTOACCEL - MEASURED-DATA ARCHITECTURE SELECTOR")
    print("=" * 72)
    print("Objective: minimize generic logic-cell count\n")

    print(
        f"{'Width':>7} {'Conventional':>14} {'Karatsuba':>12} "
        f"{'Recommendation':>18} {'Reduction':>12}"
    )
    print("-" * 72)

    for row in results:
        winner, reduction = select_architecture(row)

        print(
            f"{row['width']:>7} "
            f"{row['conventional_cells']:>14,} "
            f"{row['karatsuba_cells']:>12,} "
            f"{winner:>18} "
            f"{reduction:>10.2f}%"
        )

    save_recommendations(results, OUTPUT_CSV)

    print(f"\nRecommendation report saved to:\n{OUTPUT_CSV}")
    print("\nImportant: recommendations use generic logic-cell counts only.")
    print("They do not establish physical area, power, or timing.")


if __name__ == "__main__":
    main()


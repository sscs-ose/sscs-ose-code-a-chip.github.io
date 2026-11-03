
import csv
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
COMPARISON = RESULTS / "comparison.csv"
RECOMMENDATIONS = RESULTS / "architecture_recommendations.csv"
SKY130 = RESULTS / "sky130_comparison.csv"
OUTPUT = RESULTS / "project_summary.md"


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def main():
    comparison = read_csv(COMPARISON)
    recommendations = read_csv(RECOMMENDATIONS)
    sky130 = read_csv(SKY130)

    if not comparison or not recommendations:
        raise ValueError("Input CSV files must contain data rows.")

    recommendation_by_width = {
        int(row["width"]): row for row in recommendations
    }

    sky_by = {(int(r["width"]), r["architecture"]): r for r in sky130}
    sky_lines = []
    for w in (8, 16, 32, 64):
        rec = float(sky_by[(w, "karatsuba_recursive")]["area_change_percent"])
        sky_lines.append(
            f"recursive Karatsuba {rec:+.1f}% (N={w})")

    lines = [
        "# AutoAccel Project Summary",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## Project objective",
        "",
        "Evaluate conventional, single-level Karatsuba, and recursive "
        "(threshold-based) Karatsuba multiplier architectures using RTL "
        "simulation, synthesis-based generic logic-cell comparison, formal "
        "verification, and sky130_fd_sc_hd standard-cell PPA (area, static "
        "timing, static leakage).",
        "",
        "## Synthesis comparison and recommendations",
        "",
        "| Width | Conventional cells | Karatsuba cells | Recommended architecture | Cell-count reduction |",
        "|---:|---:|---:|---|---:|",
    ]

    for row in sorted(comparison, key=lambda item: int(item["width"])):
        width = int(row["width"])
        recommendation = recommendation_by_width.get(width)

        if recommendation is None:
            raise ValueError(
                f"No recommendation found for width {width}"
            )

        lines.append(
            f"| {width} | "
            f"{int(row['conventional_cells']):,} | "
            f"{int(row['karatsuba_cells']):,} | "
            f"{recommendation['recommended_architecture']} | "
            f"{recommendation['cell_count_reduction_percent']}% |"
        )

    lines.extend([
        "",
        "## sky130 mapped results (summary)",
        "",
        "Mapped cell area (um^2) versus conventional at tt_025C_1v80: "
        + "; ".join(sky_lines) + ". "
        "ABC static-timing delay favors the conventional design at every "
        "width under the area-oriented mapping. Details in "
        "results/sky130_baseline.csv and results/sky130_comparison.csv.",
        "",
        "## Verification status",
        "",
        "- Conventional simulation: 108 vectors each passed at N=8, N=16, and N=32 in the recorded audit run.",
        "- Karatsuba simulation: 1,045 vectors each passed at N=8, N=16, and N=32 in the recorded audit run.",
        "- Formal equivalence: N=8 passed with SymbiYosys and Bitwuzla for both Karatsuba variants; the recursive architecture was also verified against a bit-accurate software model (exhaustive N<=8; 150,000+ vectors each at N=16, 32, 64; see formal/logs/recursive_model_verify.log).",
        "- N=16 formal equivalence: unresolved; the full 32-bit output proof timed out. Bit 0 passed, but that does not prove the full output. No confirmed counterexample was established by the timeout runs.",
        "- Selector unit tests: 4 tests passed in the recorded audit run.",
        "",
        "## Interpretation and limitations",
        "",
        "Recommendations minimize the generic logic-cell count reported by "
        "the current synthesis flow. These counts are not physical silicon "
        "area measurements and do not establish power consumption or timing. "
        "The sky130 mapped results add cell area, ABC static timing, and "
        "static leakage at the tt_025C_1v80 corner, but still no placement, "
        "routing, or dynamic power.",
        "",
        "The recommendations apply to the tested operand widths and current "
        "RTL and synthesis configuration. Further verification and "
        "technology-specific implementation are needed before making broader "
        "hardware performance claims.",
        "",
        "The repository is licensed under Apache-2.0 (LICENSE at the "
        "repository root) and includes the openly licensed analysis notebook "
        "required by the IEEE SSCS Code-a-Chip submission instructions. "
        "Confirm both against the current submission checklist.",
        "",
    ])

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Project summary generated: {OUTPUT}")


if __name__ == "__main__":
    main()

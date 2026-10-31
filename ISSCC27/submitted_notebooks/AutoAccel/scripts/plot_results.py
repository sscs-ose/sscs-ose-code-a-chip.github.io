
import csv
from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
CSV_PATH = RESULTS / "comparison.csv"
PLOT_DIR = RESULTS / "plots"

PLOT_DIR.mkdir(parents=True, exist_ok=True)

with CSV_PATH.open("r", newline="", encoding="utf-8") as file:
    rows = list(csv.DictReader(file))

if not rows:
    raise ValueError(f"No data found in {CSV_PATH}")

widths = [int(row["width"]) for row in rows]
conventional = [int(row["conventional_cells"]) for row in rows]
karatsuba = [int(row["karatsuba_cells"]) for row in rows]
reduction = [float(row["cell_count_reduction_percent"]) for row in rows]

# Graph 1: Logic-cell count
plt.figure(figsize=(9, 5.5))
plt.plot(widths, conventional, marker="o", label="Conventional")
plt.plot(widths, karatsuba, marker="o", label="Karatsuba")
plt.xlabel("Operand width (bits)")
plt.ylabel("Generic logic-cell count")
plt.title("AutoAccel: Logic-Cell Count vs Operand Width")
plt.xticks(widths)
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig(PLOT_DIR / "cell_count_vs_width.png", dpi=200)
plt.close()

# Graph 2: Percentage reduction
plt.figure(figsize=(9, 5.5))
bars = plt.bar([str(width) for width in widths], reduction)
plt.axhline(0, linewidth=1)
plt.bar_label(bars, fmt="%.2f%%", padding=3)
plt.xlabel("Operand width (bits)")
plt.ylabel("Cell-count reduction (%)")
plt.title("AutoAccel: Karatsuba Cell-Count Reduction")
plt.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(PLOT_DIR / "karatsuba_cell_reduction.png", dpi=200)
plt.close()

print("Plot generation completed successfully.")
print(f"Output directory: {PLOT_DIR}")
for path in sorted(PLOT_DIR.glob("*.png")):
    print(f"Created: {path.name}")

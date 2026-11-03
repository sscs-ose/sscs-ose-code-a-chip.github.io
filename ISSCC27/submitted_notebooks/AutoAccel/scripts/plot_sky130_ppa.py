#!/usr/bin/env python3
"""Generate sky130 PPA comparison plots from results/sky130_baseline.csv."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
CSV_PATH = RESULTS / "sky130_baseline.csv"
PLOT_DIR = RESULTS / "plots"

PLOT_DIR.mkdir(parents=True, exist_ok=True)

with CSV_PATH.open("r", newline="", encoding="utf-8") as file:
    rows = list(csv.DictReader(file))

if not rows:
    raise ValueError(f"No data found in {CSV_PATH}")

widths = sorted({int(r["width"]) for r in rows})
arch_order = ["karatsuba_single", "karatsuba_recursive"]
labels = {
    "conventional": "Conventional",
    "karatsuba_single": "Karatsuba (single-level)",
    "karatsuba_recursive": "Karatsuba (recursive, threshold 8)",
}
by_key = {(int(r["width"]), r["architecture"]): r for r in rows}
bar_w = 0.35

# Graph 1: sky130 area vs width, all architectures
fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
for arch in ["conventional"] + arch_order:
    xs = sorted(w for (w, a) in by_key if a == arch)
    vals = [float(by_key[(w, arch)]["sky130_area_um2"]) for w in xs]
    style = {"marker": "o", "linewidth": 2} if arch == "conventional" \
        else {"marker": "s", "linewidth": 2}
    ax.plot(xs, vals, label=labels[arch], **style)
ax.set(xlabel="Operand width N (bits)", ylabel="sky130 cell area (um^2)",
       title="sky130_fd_sc_hd mapped area by multiplier architecture")
ax.set_yscale("log")
ax.set_xticks(widths)
ax.grid(True, which="both", alpha=0.3)
ax.legend()
fig.savefig(PLOT_DIR / "sky130_area_vs_width.png", dpi=200)
plt.close(fig)

# Graph 2: area change percent vs conventional
fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
for idx, arch in enumerate(arch_order):
    vals = []
    for w in widths:
        a = float(by_key[(w, arch)]["sky130_area_um2"])
        c = float(by_key[(w, "conventional")]["sky130_area_um2"])
        vals.append(100.0 * (a - c) / c)
    xs = [w + (idx - 0.5) * bar_w for w in widths]
    bars = ax.bar([str(x) for x in xs], vals, width=bar_w, label=labels[arch])
    ax.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=8)
ax.axhline(0, color="black", linewidth=0.8)
ax.set(xlabel="Operand width N (bits)", ylabel="sky130 area change vs conventional (%)",
       title="Karatsuba sky130 area change relative to conventional")
ax.grid(True, axis="y", alpha=0.3)
ax.legend()
fig.savefig(PLOT_DIR / "sky130_area_change.png", dpi=200)
plt.close(fig)

# Graph 3: critical path delay vs width
fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
for arch in ["conventional"] + arch_order:
    xs = sorted(w for (w, a) in by_key if a == arch)
    vals = [float(by_key[(w, arch)]["critical_path_delay_ps"]) / 1000.0 for w in xs]
    style = {"marker": "o", "linewidth": 2} if arch == "conventional" \
        else {"marker": "s", "linewidth": 2}
    ax.plot(xs, vals, label=labels[arch], **style)
ax.set(xlabel="Operand width N (bits)", ylabel="Critical path delay (ns)",
       title="sky130_fd_sc_hd critical path delay by multiplier architecture")
ax.set_xticks(widths)
ax.grid(True, alpha=0.3)
ax.legend()
fig.savefig(PLOT_DIR / "sky130_delay_vs_width.png", dpi=200)
plt.close(fig)

# Graph 4: static leakage vs width
fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
for arch in ["conventional"] + arch_order:
    xs = sorted(w for (w, a) in by_key if a == arch)
    vals = [float(by_key[(w, arch)]["static_leakage_nw"]) for w in xs]
    style = {"marker": "o", "linewidth": 2} if arch == "conventional" \
        else {"marker": "s", "linewidth": 2}
    ax.plot(xs, vals, label=labels[arch], **style)
ax.set(xlabel="Operand width N (bits)", ylabel="Static leakage (nW)",
       title="sky130_fd_sc_hd static leakage (tt_025C_1v80) by architecture")
ax.set_yscale("log")
ax.set_xticks(widths)
ax.grid(True, which="both", alpha=0.3)
ax.legend()
fig.savefig(PLOT_DIR / "sky130_leakage_vs_width.png", dpi=200)
plt.close(fig)

# Graph 5: area-delay product change vs conventional
fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
for idx, arch in enumerate(arch_order):
    vals = []
    for w in widths:
        a = float(by_key[(w, arch)]["sky130_area_um2"])
        d = float(by_key[(w, arch)]["critical_path_delay_ps"])
        c_a = float(by_key[(w, "conventional")]["sky130_area_um2"])
        c_d = float(by_key[(w, "conventional")]["critical_path_delay_ps"])
        vals.append(100.0 * (a * d) / (c_a * c_d) - 100.0)
    xs = [w + (idx - 0.5) * bar_w for w in widths]
    bars = ax.bar([str(x) for x in xs], vals, width=bar_w, label=labels[arch])
    ax.bar_label(bars, fmt="%.0f%%", padding=3, fontsize=8)
ax.axhline(0, color="black", linewidth=0.8)
ax.set(xlabel="Operand width N (bits)",
       ylabel="Area-Delay product change vs conventional (%)",
       title="Area-Delay product overhead relative to conventional")
ax.grid(True, axis="y", alpha=0.3)
ax.legend()
fig.savefig(PLOT_DIR / "sky130_adp_change.png", dpi=200)
plt.close(fig)

print("sky130 plot generation completed successfully.")
for path in sorted(PLOT_DIR.glob("sky130_*.png")):
    print(f"Created: {path.name}")

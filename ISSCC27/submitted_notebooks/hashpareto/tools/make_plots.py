#!/usr/bin/env python3
"""Regenerate the HashPareto Pareto plots from results/pareto.csv.

Usage:
    ~/venv/bin/python tools/make_plots.py

Inputs : results/pareto.csv  (populated by tools/make_pareto.py using *measured*
         cycles from results/cycles.csv)
Outputs : results/pareto_area_vs_throughput.png
          results/pareto_energy_vs_throughput.png
"""
import csv
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")

rows = []
with open(os.path.join(RES, "pareto.csv")) as f:
    for r in csv.DictReader(f):
        rows.append(
            {
                "unroll": int(r["unroll"]),
                "area_um2": float(r["area_um2"]),
                "throughput_Mhash": float(r["throughput_Mhash_s"]) / 1e6,
                "energy_nJ": float(r["energy_per_hash_nJ"]),
            }
        )
rows.sort(key=lambda r: r["unroll"])


def annotate(ax, xs, ys):
    for r in rows:
        ax.annotate(f"U{r['unroll']}", (xs(r), ys(r)), textcoords="offset points",
                    xytext=(8, 4))


# --- area vs throughput -----------------------------------------------------
fig, ax = plt.subplots(figsize=(6.4, 4.4))
ax.plot([r["throughput_Mhash"] for r in rows], [r["area_um2"] / 1e3 for r in rows],
        "--", alpha=0.5)
ax.scatter([r["throughput_Mhash"] for r in rows], [r["area_um2"] / 1e3 for r in rows],
           s=70, zorder=3)
annotate(ax, lambda r: r["throughput_Mhash"], lambda r: r["area_um2"] / 1e3)
ax.set_xlabel("Throughput (Mhash/s)")
ax.set_ylabel("Stdcell area (1k $\\mu$m$^2$)")
ax.set_title("HashPareto: area vs throughput (SKY130, 4 variants)")
ax.grid(alpha=0.3)
fig.tight_layout()
out1 = os.path.join(RES, "pareto_area_vs_throughput.png")
fig.savefig(out1, dpi=150)
plt.close(fig)

# --- energy per hash vs throughput ------------------------------------------
fig, ax = plt.subplots(figsize=(6.4, 4.4))
ax.plot([r["throughput_Mhash"] for r in rows], [r["energy_nJ"] for r in rows],
        "--", alpha=0.5)
ax.scatter([r["throughput_Mhash"] for r in rows], [r["energy_nJ"] for r in rows],
           s=70, zorder=3)
annotate(ax, lambda r: r["throughput_Mhash"], lambda r: r["energy_nJ"])
ax.set_xlabel("Throughput (Mhash/s)")
ax.set_ylabel("Energy per hash (nJ, vectorless STA estimate)")
ax.set_title("HashPareto: energy/hash vs throughput (SKY130, 4 variants)")
ax.grid(alpha=0.3)
fig.tight_layout()
out2 = os.path.join(RES, "pareto_energy_vs_throughput.png")
fig.savefig(out2, dpi=150)
plt.close(fig)

print("wrote", out1)
print("wrote", out2)

#!/usr/bin/env python3
"""Data figures of the restart closure work (written to results/figures/)."""
from __future__ import annotations

import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import parent_metric as pm  # noqa: E402
import shbench as sb  # noqa: E402

sys.path.insert(0, str(sb.REPO / "experiments" / "experiment_a" / "sky130"))
from figure_sketches import context_header  # noqa: E402

FIG = sb.REPO / "results" / "figures"
SCREEN = sb.REPO / "results" / "closure" / "screen"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "svg.hashsalt": "closure", "svg.fonttype": "path"})


def _save(fig, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.svg", bbox_inches="tight", metadata={"Date": None})
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight", dpi=150)
    plt.close(fig)


def f2_screening_map() -> None:
    """Figure 3: the first cut (F2) on the sequential bench at the screening conditions."""
    res = json.loads((SCREEN / "f2_screen.json").read_text())
    tags = [r["tag"].replace("_", " ").replace("V ", " V\n").replace("C", " °C") for r in res]
    y = np.array([r["max_abs_r_LSB"] for r in res])
    rs = np.array([abs(r["components_mV"]["rS"]) for r in res]) / (pm.VLSB * 1e3)
    rp = np.array([abs(r["components_mV"]["rP"]) for r in res]) / (pm.VLSB * 1e3)
    fig, ax = plt.subplots(figsize=(10, 3.9))
    fig.subplots_adjust(left=0.085, right=0.99, top=0.97, bottom=0.17)
    x = np.arange(len(res))
    ax.bar(x - 0.27, y, 0.27, color="#1f7a4d", label="parent metric: largest corrected held-sample residual")
    ax.bar(x, rs, 0.27, color="#c96f4a", label="diagnostic: largest pre-opening residual")
    ax.bar(x + 0.27, rp, 0.27, color="#e0b08f", label="diagnostic: largest change at opening (to the early read)")
    ax.axhline(1.0, color="#222222", lw=1.2, ls="--", label="limit: 1 LSB")
    for i, r in enumerate(res):
        if r["pass"]:
            ax.text(i - 0.27, max(y[i] * 1.25, 1.35), "pass", ha="center", va="bottom", fontsize=8, color="#1f7a4d",
                    weight="bold")
    gap = [i for i, r in enumerate(res) if r["max_abs_r_LSB"] > 10]
    for i in gap:
        ax.text(i, 330, "switch stops\nconducting", ha="center", va="center", fontsize=8, color="#7a3010")
    fs = [i for i, r in enumerate(res) if r["tag"].startswith("fs")]
    for i in fs:
        ax.text(i, 6.5, "driver tail\nheadroom", ha="center", va="center", fontsize=8, color="#7a3010")
    ax.set_yscale("log")
    ax.set_ylim(0.1, 900)
    ax.set_xticks(x, tags, fontsize=8.6)
    ax.set_xlabel("screening condition: process corner, supply, temperature", fontsize=9)
    ax.set_ylabel("max |residual| (LSB)")
    ax.legend(frameon=False, fontsize=8.2, loc="upper right", bbox_to_anchor=(1.0, 0.86))
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    context_header(fig, "Where does the first cut fail?", [
        ("Circuit", "first cut: two-stage Miller driver, 15/30 µm transmission gate, Cs = 1 pF"),
        ("Test", "sequential bench (each held sample is the next start state), seven screening PVT conditions"),
        ("Metric", "residual after two-point correction, in LSB (log scale); the bars are maxima over all cycles "
                   "and do not add"),
    ])
    _save(fig, "figure_f2_screening_map")


if __name__ == "__main__":
    f2_screening_map()

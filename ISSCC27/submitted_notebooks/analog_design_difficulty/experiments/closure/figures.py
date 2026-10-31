#!/usr/bin/env python3
"""Data figures of the restart closure work (written to results/figures/)."""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import parent_metric as pm  # noqa: E402
import shbench as sb  # noqa: E402

FIG = sb.REPO / "results" / "figures"
SCREEN = sb.REPO / "results" / "closure" / "screen"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "svg.hashsalt": "closure", "svg.fonttype": "path"})


def _save(fig, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.svg", bbox_inches="tight", metadata={"Date": None})
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight", dpi=150)
    plt.close(fig)


def f2_screening_map() -> None:
    """Figure 4: the first cut (F2) on the sequential bench at the screening conditions."""
    res = json.loads((SCREEN / "f2_screen.json").read_text())
    tags = [r["tag"].replace("_", " ").replace("V ", " V, ").replace("C", " °C") for r in res]
    y = np.array([r["max_abs_r_LSB"] for r in res])
    rs = np.array([r["components_mV"]["rS"] for r in res]) / (pm.VLSB * 1e3)
    rp = np.array([r["components_mV"]["rP"] for r in res]) / (pm.VLSB * 1e3)
    fig, ax = plt.subplots(figsize=(10, 3.8))
    x = np.arange(len(res))
    ax.bar(x - 0.27, y, 0.27, color="#1f7a4d", label="parent residual max|r|")
    ax.bar(x, rs, 0.27, color="#c96f4a", label="pre-opening part (static tracking, incomplete acquisition)")
    ax.bar(x + 0.27, rp, 0.27, color="#e0b08f", label="turn-off part")
    ax.axhline(1.0, color="#222222", lw=1.2, ls="--")
    ax.text(len(res) - 0.5, 1.15, "±1 LSB", ha="right", fontsize=9)
    ax.set_yscale("log")
    ax.set_ylim(0.1, 600)
    ax.set_xticks(x, tags, rotation=20, ha="right")
    ax.set_ylabel("max |residual| (LSB)")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    _save(fig, "figure_f2_screening_map")


if __name__ == "__main__":
    f2_screening_map()

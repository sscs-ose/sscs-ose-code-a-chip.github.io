"""Shared chart style for the notebook.

Implements the conventions of a validated data-visualization palette:
categorical hues assigned in a fixed order (validated for colour-vision
deficiency with the palette validator), recessive hairline grid and axes,
2 px lines, >= 8 px markers with a surface-coloured ring, a 2 px surface gap
between touching fills, and text that always uses ink colours rather than the
data colour.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
# categorical slots, fixed order; the first three validate on all pairs (light mode)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
CRITICAL = "#d03b3b"


def apply() -> None:
    mpl.rcParams.update({
        "figure.dpi": 110,
        "savefig.dpi": 160,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": ["DejaVu Sans"],
        "font.size": 10,
        "text.color": INK,
        "axes.labelcolor": INK_2,
        "axes.titlecolor": INK,
        "axes.titlesize": 11.5,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 10,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "grid.linestyle": "-",
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK_2,
        "ytick.labelcolor": INK_2,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "lines.linewidth": 2.0,
        "lines.solid_capstyle": "round",
        "lines.solid_joinstyle": "round",
        "legend.frameon": False,
        "legend.fontsize": 9.5,
        "legend.labelcolor": INK_2,
        "axes.prop_cycle": mpl.cycler(color=SERIES),
    })


def marker_kw(color: str) -> dict:
    """Scatter/end-marker: >= 8 px, filled with the series colour, 2 px surface ring."""
    return dict(s=90, color=color, edgecolors=SURFACE, linewidths=2, zorder=3)


def bar_kw(color: str) -> dict:
    """Bars and stacked segments: a 2 px surface gap separates touching fills."""
    return dict(color=color, edgecolor=SURFACE, linewidth=2)


def reference_line(ax, y: float, label: str | None = None, axis: str = "y") -> None:
    """A recessive solid hairline for a threshold, with an optional ink label."""
    if axis == "y":
        ax.axhline(y, color=MUTED, lw=1, zorder=1)
        if label:
            ax.annotate(label, (1, y), xycoords=("axes fraction", "data"), xytext=(-2, 3),
                        textcoords="offset points", ha="right", va="bottom", fontsize=8.5, color=INK_2)
    else:
        ax.axvline(y, color=MUTED, lw=1, zorder=1)


def thousands(ax, axis: str = "x") -> None:
    """Round tick labels with a thousands separator (4,000 rather than 4000)."""
    fmt = mpl.ticker.StrMethodFormatter("{x:,.0f}")
    (ax.xaxis if axis == "x" else ax.yaxis).set_major_formatter(fmt)


def finish(fig=None, title: str | None = None, subtitle: str | None = None) -> None:
    fig = fig or plt.gcf()
    if title:
        fig.suptitle(title, x=0.01, ha="left", fontsize=12.5, fontweight="bold", color=INK, y=1.02)
    if subtitle:
        fig.text(0.01, 0.975, subtitle, ha="left", va="top", fontsize=9.5, color=INK_2)
    fig.tight_layout()

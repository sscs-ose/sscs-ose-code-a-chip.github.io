"""Shared drawing helpers for the notebook's data figures: a question title with a
Circuit / Test / Metric context strip, and small testbench sketches.

Only Matplotlib primitives; no simulation data are read or written here.
"""
from __future__ import annotations

from matplotlib.patches import Polygon

INK = "#222222"
MUTED = "#666666"


def context_header(fig, question: str, rows: list[tuple[str, str]], top: float = 1.0, line: float = 0.042,
                   key_x: float = 0.085, size: float = 8.8) -> None:
    """Question title and a Circuit / Test / Metric strip placed above the axes area (figure coordinates).

    The strip sits above y = top so that it never overlaps the plotted data; figures are saved with
    bbox_inches="tight", which includes it.
    """
    n = len(rows)
    y0 = top + 0.02
    for i, (k, v) in enumerate(reversed(rows)):
        y = y0 + i * line
        fig.text(key_x, y, k, ha="right", va="bottom", fontsize=size, color=MUTED, weight="bold")
        fig.text(key_x + 0.01, y, v, ha="left", va="bottom", fontsize=size, color=INK)
    fig.text(0.01, y0 + n * line + 0.012, question, ha="left", va="bottom", fontsize=12, color=INK, weight="bold")


# ---------------------------------------------------------------------------- testbench sketches

def _wire(ax, *pts, color=INK, lw=1.3):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, lw=lw, solid_capstyle="round", zorder=2)


def _cap(ax, x, y, label=None, color=INK, note=None, note_color=INK):
    """Capacitor to ground hanging from (x, y)."""
    _wire(ax, (x, y), (x, y - 0.32), color=color)
    _wire(ax, (x - 0.2, y - 0.32), (x + 0.2, y - 0.32), color=color, lw=2)
    _wire(ax, (x - 0.2, y - 0.44), (x + 0.2, y - 0.44), color=color, lw=2)
    _wire(ax, (x, y - 0.44), (x, y - 0.68), color=color)
    _wire(ax, (x - 0.16, y - 0.68), (x + 0.16, y - 0.68), color=color)
    _wire(ax, (x - 0.08, y - 0.75), (x + 0.08, y - 0.75), color=color)
    if label:
        ax.text(x + 0.27, y - 0.33, label, fontsize=8, ha="left", va="center", color=INK)
    if note:
        ax.text(x + 0.27, y - 0.78, note, fontsize=7.6, ha="left", va="center", color=note_color, weight="bold")


def driver(ax, x, y, in_label, in_color=INK, step=False):
    """Unity-gain follower with its input pin at the left; returns the output-node x position."""
    ax.add_patch(Polygon([(x, y + 0.42), (x, y - 0.42), (x + 0.8, y)], closed=True, facecolor="white",
                         edgecolor=INK, lw=1.3, zorder=3))
    _wire(ax, (x - 0.55, y + 0.18), (x, y + 0.18), color=in_color, lw=1.6 if step else 1.3)
    ax.text(x - 0.6, y + 0.18, in_label, fontsize=7.8, ha="right", va="center", color=in_color,
            weight="bold" if step else "normal")
    xo = x + 1.05
    _wire(ax, (x + 0.8, y), (xo, y))
    _wire(ax, (xo, y), (xo, y - 0.62), (x - 0.18, y - 0.62), (x - 0.18, y - 0.18), (x, y - 0.18), color="#7a4fb0")
    ax.plot(xo, y, "o", ms=3.5, color=INK, zorder=4)
    return xo


def resistor(ax, x0, x1, y, color, label=None):
    import numpy as np
    xs = np.linspace(x0 + 0.08, x1 - 0.08, 9)
    ys = y + 0.09 * np.array([0, 1, -1, 1, -1, 1, -1, 1, 0])
    _wire(ax, (x0, y), (x0 + 0.08, y), color=color)
    ax.plot(xs, ys, color=color, lw=1.3, zorder=2)
    _wire(ax, (x1 - 0.08, y), (x1, y), color=color)
    if label:
        ax.text((x0 + x1) / 2, y + 0.2, label, fontsize=7.8, ha="center", va="bottom", color=color)


def transmission_gate(ax, x0, x1, y, color):
    xm = (x0 + x1) / 2
    a, b = xm - 0.18, xm + 0.18
    _wire(ax, (x0, y), (a, y), color=color)
    _wire(ax, (b, y), (x1, y), color=color)
    ax.add_patch(Polygon([(a, y + 0.14), (a, y - 0.14), (b, y)], closed=True, facecolor="white", edgecolor=color,
                         lw=1.3, zorder=3))
    ax.add_patch(Polygon([(b, y + 0.14), (b, y - 0.14), (a, y)], closed=True, facecolor="none", edgecolor=color,
                         lw=1.3, zorder=3))


def bench(ax, x, y, in_label, link, cs_note, in_color=INK, step=False, link_color=INK, link_label=None,
          cs_color=INK, arrow_label=None):
    """One small testbench: follower -> link ("rif", "tg", or "rif_closed") -> Cs."""
    xo = driver(ax, x, y, in_label, in_color=in_color, step=step)
    x1 = xo + 1.05
    if link == "tg":
        transmission_gate(ax, xo, x1, y, link_color)
    else:
        resistor(ax, xo, x1, y, link_color)
    if link_label:
        ax.text((xo + x1) / 2, y + 0.22, link_label, fontsize=7.8, ha="center", va="bottom", color=link_color)
    xc = x1 + 0.3
    _wire(ax, (x1, y), (xc, y))
    ax.plot(xc, y, "o", ms=3.5, color=INK, zorder=4)
    _cap(ax, xc, y, label="Cs", note=cs_note, note_color=cs_color)
    if arrow_label:
        ax.annotate(arrow_label, xy=((xo + x1) / 2, y + 0.05), xytext=((xo + x1) / 2 + 0.75, y + 0.8),
                    fontsize=7.6, ha="center", va="bottom", color=cs_color,
                    arrowprops=dict(arrowstyle="-|>", color=cs_color, lw=1.1))
    return xc

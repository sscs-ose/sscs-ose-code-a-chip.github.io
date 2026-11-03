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
# one meaning per hue across the notebook: the engine under study (NTT blue, Keccak orange; the lighter tone
# is the alternative HSKEM-1 did not choose) and the three NTT iterations (green, purple, amber)
NTT, NTT_ALT = "#2a78d6", "#7aaee8"
KECCAK, KECCAK_ALT = "#eb6834", "#f29a6c"
IT1, IT1_STEP = "#1baf7a", "#8fd6b8"
IT2, IT2_LIGHT = "#4a3aa7", "#a59ce0"
IT3 = "#eda100"
# categories that are not designs (cell classes, controller states, energy parts) use one slate ramp that
# varies in lightness only, so it stays readable in greyscale; ink on the two lightest shades, white on the rest
SLATE = ["#1f3a56", "#486886", "#7591ad", "#a7bccf", "#d4dee8"]
# categories that are not designs (controller states, cell classes, energy parts, sections of a decapsulation):
# clear, mostly warm hues that differ from each other in hue and lightness and from the design colours above
# (deep teal, raspberry, cream gold, sage, warm grey); white text on the first two, ink on the rest
CAT = ["#1d7874", "#d1495b", "#f2cc8f", "#81b29a", "#b8a99a"]
# one colour per hardware component in every figure that shows it
REG = CAT[0]          # flip-flops, registers and their clock network
XORC = "#c0559a"      # XOR/XNOR cells (magenta: kept apart from the critical red)
CODEC, CODEC_CMP = "#7b3f6e", "#d6a5c9"   # ciphertext encoding and comparison (plum)
BAND = "#ece6dc"      # the "no detectable leakage" band of the TVLA figures
MEM = CAT[2]          # SRAM macros and memory reads
MEM_W = "#b5833b"     # memory writes
LOGIC = CAT[3]        # combinational logic and arithmetic
OTHER = MUTED         # control and everything else (the same grey as "other" and "everything else" elsewhere)
CELL_CLASS = [REG, XORC, LOGIC]


def slate_text(colour: str) -> str:
    return INK if colour in SLATE[3:] else "white"


def apply() -> None:
    mpl.rcParams.update({
        "figure.dpi": 110,
        "savefig.dpi": 160,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": ["DejaVu Sans"],
        "font.size": 11,
        "text.color": INK,
        "axes.labelcolor": INK_2,
        "axes.titlecolor": INK,
        "axes.titlesize": 12,
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
        "legend.fontsize": 10,
        "legend.labelcolor": INK_2,
        "axes.prop_cycle": mpl.cycler(color=SERIES),
    })
    import os
    if os.path.exists("/tmp/hskem_overlap_check") and not getattr(plt.show, "_checked", False):
        _show = plt.show

        def show(*args, **kwargs):
            for num in plt.get_fignums():
                overlap_report(plt.figure(num))
            return _show(*args, **kwargs)
        show._checked = True
        plt.show = show


def overlap_report(fig, out: str = "/tmp/hskem_overlap.txt") -> None:
    """Layout check used while editing (off unless /tmp/hskem_overlap_check exists): lists pairs of texts
    whose boxes overlap and texts that a data line crosses."""
    import numpy as np
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    hidden = set()                       # tick labels outside the view are never drawn
    for ax in fig.axes:
        for axis, (lo, hi) in ((ax.xaxis, sorted(ax.get_xlim())), (ax.yaxis, sorted(ax.get_ylim()))):
            for tk in axis.get_major_ticks() + axis.get_minor_ticks():
                if not (lo - 1e-9 <= tk.get_loc() <= hi + 1e-9) or not tk.get_visible():
                    hidden.update((id(tk.label1), id(tk.label2)))
    texts = [t for t in fig.findobj(mpl.text.Text)
             if t.get_visible() and t.get_text().strip() and id(t) not in hidden]
    boxes = [(t, t.get_window_extent(r)) for t in texts]
    name = (fig._suptitle.get_text() if fig._suptitle else "") or " | ".join(
        a.get_title() for a in fig.axes if a.get_title())[:90]
    rows = []
    for i, (a, ba) in enumerate(boxes):
        for b, bb in boxes[i + 1:]:
            w = min(ba.x1, bb.x1) - max(ba.x0, bb.x0)
            h = min(ba.y1, bb.y1) - max(ba.y0, bb.y0)
            if w > 1 and h > 1:
                rows.append(f"  TEXT/TEXT {a.get_text()[:40]!r} x {b.get_text()[:40]!r} ({w:.0f}x{h:.0f} px)")
            elif (w > 1 and -3 < h <= 1) or (h > 1 and -3 < w <= 1):      # texts that almost touch
                rows.append(f"  TIGHT {a.get_text()[:40]!r} / {b.get_text()[:40]!r} (gap {-min(w, h):.0f} px)")
    for ax in fig.axes:
        clip = ax.get_window_extent(r)
        for ln in ax.lines:
            xy = ln.get_xydata()
            if len(xy) < 2 or ln.get_linestyle() in ("None", "none", ""):
                continue
            pts = ln.get_transform().transform(xy)
            dense = np.concatenate([np.linspace(p, q, 40) for p, q in zip(pts[:-1], pts[1:])])
            dense = dense[(dense[:, 0] >= clip.x0) & (dense[:, 0] <= clip.x1) &
                          (dense[:, 1] >= clip.y0) & (dense[:, 1] <= clip.y1)]
            for t, bb in boxes:
                if t.axes is ax and len(t.get_text()) > 2:
                    inside = ((dense[:, 0] > bb.x0 + 1) & (dense[:, 0] < bb.x1 - 1) &
                              (dense[:, 1] > bb.y0 + 1) & (dense[:, 1] < bb.y1 - 1)).any()
                    if inside:
                        rows.append(f"  LINE/TEXT line {ln.get_label()[:30]!r} crosses {t.get_text()[:40]!r}")
    with open(out, "a", encoding="utf-8") as f:
        f.write(f"FIGURE {name}\n" + ("\n".join(rows) if rows else "  ok") + "\n")


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


def title_with_detail(ax, title: str, detail: str, fontsize: float = 10) -> None:
    """A bold, centred panel title with a detail line (e.g. a size) below it in a smaller, lighter face,
    so that the two lines never read as one sentence wrapped onto a second line."""
    ax.set_title(title, fontsize=fontsize, loc="center", pad=fontsize * 1.9)
    ax.annotate(detail, (0.5, 1.0), xycoords="axes fraction", xytext=(0, fontsize * 0.5),
                textcoords="offset points", ha="center", va="bottom", fontsize=fontsize - 1.5,
                color=INK_2, fontweight="normal")


def thousands(ax, axis: str = "x") -> None:
    """Round tick labels with a thousands separator (4,000 rather than 4000)."""
    fmt = mpl.ticker.StrMethodFormatter("{x:,.0f}")
    (ax.xaxis if axis == "x" else ax.yaxis).set_major_formatter(fmt)


def scale_bar(ax, length: float, label: str, frac: tuple = (0.04, 0.04)) -> None:
    """A scale bar in data units (µm for layouts) near the lower-left corner of the axes."""
    (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
    x, y = x0 + frac[0] * (x1 - x0), y0 + frac[1] * (y1 - y0)
    ax.plot([x, x + length], [y, y], color=INK, lw=3, solid_capstyle="butt", zorder=6)
    ax.annotate(label, (x + length / 2, y), xytext=(0, 4), textcoords="offset points", ha="center", va="bottom",
                fontsize=9.5, color=INK, zorder=6,
                bbox=dict(boxstyle="round,pad=0.15", fc=SURFACE, ec="none", alpha=0.85))


def source(fig, text: str, y: float = -0.015) -> None:
    """The committed results a figure is drawn from, as a muted line under it."""
    fig.text(0.01, y, f"Data: {text}", ha="left", va="top", fontsize=8.5, color=MUTED)


def finish(fig=None, title: str | None = None, subtitle: str | None = None, y: float = 1.02) -> None:
    fig = fig or plt.gcf()
    if title:
        fig.suptitle(title, x=0.01, ha="left", fontsize=13, fontweight="bold", color=INK, y=y)
    if subtitle:
        fig.text(0.01, 0.955, subtitle, ha="left", va="top", fontsize=9.5, color=INK_2)
    fig.tight_layout()


def save_pdf(fig, name: str) -> None:
    """Keep a vector copy of a figure in figures/pdf/ (no creation date, so reruns do not change it)."""
    import pathlib
    out = pathlib.Path(__file__).resolve().parents[1] / "figures" / "pdf"
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / f"{name}.pdf", bbox_inches="tight", metadata={"CreationDate": None})

"""figures.py - figures that are drawn rather than plotted (the flow diagram). SPDX-License-Identifier: Apache-2.0"""
from __future__ import annotations
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def flow_diagram(path, R=None):
    """The flow at a glance. Numbers in the boxes come from the results registry R when available."""
    R = R or {}
    def g(k, fmt="{}", alt=""):
        v = R.get(k)
        return fmt.format(v) if v is not None else alt
    fig, ax = plt.subplots(figsize=(12.5, 5.2))
    ax.set_xlim(0, 125); ax.set_ylim(0, 52); ax.axis("off")
    C = dict(char="#d8e6f3", model="#e4ecd6", spice="#f6e2c8", out="#efe0ee", gray="#eeeeee")

    def box(x, y, w, h, title, body, color):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=color, ec="#555", lw=0.9))
        ax.text(x + w / 2, y + h - 2.0, title, ha="center", va="top", fontsize=9, weight="bold")
        ax.text(x + w / 2, y + h - 6.0, body, ha="center", va="top", fontsize=7.3, linespacing=1.35)

    def arrow(x0, y0, x1, y1):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", lw=1.0, color="#333"))

    y, h, w = 29, 21, 15.5
    xs = [1, 18.8, 36.6, 54.4, 72.2, 90.0, 107.8]
    box(xs[0], y, w, h, "1  Characterise", "SKY130 nfet / pfet,\none 5 µm finger,\nL 0.5–16 µm, V_SB axis;\nnoise, drain\n"
        "capacitance; " + g("n_corner_tables", "{} corner tables", "corner tables"), C["char"])
    box(xs[1], y, w, h, "2  Evaluate", "KCL operating point\n+ nodal solve: gain,\nR_out, bandwidth,\nheadroom, current,\ninput noise\n"
        + g("eval_ms", "{:.1f} ms / design"), C["model"])
    box(xs[2], y, w, h, "3  Screen", "the grid at tt, then\nat every other\ncorner" + g("n_corners", " ({} in all)") + "\n(LUT)\n"
        + g("n12_grid", "{:,} designs"), C["model"])
    box(xs[3], y, w, h, "4  Extend", "grow the grid where\nthe best designs\ntouch its edge; stop\nwhen noise gains < 0.5 %\n"
        + g("n12_ext", "+{:,} designs") + g("n12_rounds", ", {} rounds"), C["model"])
    box(xs[4], y, w, h, "5  Verify (SPICE)", "noise–current front,\nevery corner: gain,\nbandwidth, headroom\nat every step, noise\n"
        + g("n12_spice", "{} designs") + g("n12_pass", ", {} pass"), C["spice"])
    box(xs[5], y, w, h, "6  Pick + audit", "most targets met,\nthen lowest noise\n(ties: least area);\nno single-axis step\nwins under the rule", C["out"])
    lay = R.get("layout") or {}
    st_ = ("DRC " + ("✓" if lay.get("steps", {}).get("drc") else "✗") + ", LVS " + ("✓" if lay.get("steps", {}).get("lvs") else "✗")) if lay else "not yet run"
    box(xs[6], y, w, h, "7  Layout", "sizes file → GDS\n(generator); DRC,\nLVS, extraction; the\nsame SPICE gate on\nthe extracted net\n" + st_, C["out"])
    for a, b in zip(xs[:-1], xs[1:]):
        arrow(a + w + 0.5, y + h / 2, b - 0.5, y + h / 2)
    # bottom row: what the 9T did in this flow
    y2, h2 = 1.5, 16
    box(18.8, y2, 24, h2, "9T through steps 2–4", g("n9_screen", "{:,} sizings, ") + g("n9_feasible", "{} feasible\n", "") +
        g("r9_best", "best range in the bandwidth\nwindow {:.1f} dB (target 30):\nno design meets it (structural)"), C["gray"])
    box(49.5, y2, 26, h2, "Mechanism (model, §3–§4)", "output devices carry αI:\nr_o ∝ 1/α cancels the falling α\n"
        "→ a gain floor no sizing removes", C["gray"])
    box(82, y2, 25, h2, "12T: the minimal fix", "keep-alive sinks M10, M11 hold the\noutput devices' current; unit-device\n"
        "bias from I_ref (M12) → back to 2", C["gray"])
    arrow(43.3, y2 + h2 / 2, 49.0, y2 + h2 / 2)
    arrow(75.9, y2 + h2 / 2, 81.5, y2 + h2 / 2)
    # loop back: from the 12T box up between the rows, left, and up into "Evaluate"
    yl = 23.5
    ax.plot([94.5, 94.5], [y2 + h2 + 0.5, yl], color="#333", lw=1.0)
    ax.plot([94.5, xs[1] + w / 2], [yl, yl], color="#333", lw=1.0)
    arrow(xs[1] + w / 2, yl, xs[1] + w / 2, y - 0.5)
    ax.plot([xs[1] + w / 2, xs[1] + w / 2], [y2 + h2 + 0.5, yl], color="#333", lw=1.0, ls=":")
    fig.tight_layout(); fig.savefig(path, dpi=170); plt.close(fig)
    return path

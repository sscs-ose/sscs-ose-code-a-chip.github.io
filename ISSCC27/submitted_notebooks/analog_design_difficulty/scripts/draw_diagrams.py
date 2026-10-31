#!/usr/bin/env python3
"""Draw the explanatory diagrams shown in the notebook as static SVG assets.

    uv run python scripts/draw_diagrams.py

Writes assets/diagrams/{physical_network,design_scopes,four_tests,
reduced_model,sky130_circuit}.svg. These are explanatory drawings, not
simulation results: the notebook displays them and does not regenerate them
(REGENERATE=1 re-runs only the models and simulations). The diagrams
argument_chain.svg, design_brief_chain.svg, error_mechanisms.svg, and
interface_representation.svg in the same folder are written by hand.
The drawings use only Matplotlib primitives. Device names, sizes and node
names in sky130_circuit.svg are those of
experiments/experiment_a/sky130/netlists/source_two_stage.spice and the
sampling network in tb_t1_connected.spice.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle  # noqa: E402

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "diagrams"

INK = "#222222"
MUTED = "#666666"
CMD = "#2a77d4"     # external-input event (blue, as in the simulation figures)
CONN = "#e8613c"    # stored-charge event at the output port (orange, as in the simulation figures)
MODEL = "#2e8b57"   # sampler interface model (green, as in the simulation figures)
FB = "#7a4fb0"      # feedback path in the SKY130 schematic
SHADE = {"bias": "#f1f1f1", "stage1": "#eaf2fb", "stage2": "#fdeee8", "recv": "#eef6ee", "fix": "#f7f7f7"}
LW = 1.6
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "svg.hashsalt": "diagrams",
                     "svg.fonttype": "path"})


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------
def wire(ax, *pts, color=INK, lw=LW, ls="-", z=2):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, lw=lw, ls=ls, solid_capstyle="round", zorder=z)


def dot(ax, x, y, color=INK):
    ax.add_patch(Circle((x, y), 0.06, color=color, zorder=4))


def pin(ax, x, y, color=INK):
    ax.add_patch(Circle((x, y), 0.09, facecolor="white", edgecolor=color, lw=LW, zorder=4))


def text(ax, x, y, s, size=10, color=INK, ha="center", va="center", weight="normal", style="normal", z=5):
    ax.text(x, y, s, fontsize=size, color=color, ha=ha, va=va, fontweight=weight, fontstyle=style, zorder=z)


def gnd(ax, x, y, color=INK):
    wire(ax, (x, y), (x, y - 0.18), color=color)
    for i, w in enumerate((0.22, 0.14, 0.06)):
        wire(ax, (x - w, y - 0.18 - 0.08 * i), (x + w, y - 0.18 - 0.08 * i), color=color)


def vdd(ax, x, y, label="VDD", color=INK):
    wire(ax, (x, y), (x, y + 0.18), color=color)
    wire(ax, (x - 0.2, y + 0.18), (x + 0.2, y + 0.18), color=color)
    text(ax, x, y + 0.36, label, size=8, color=MUTED)


def mos(ax, x0, yc, kind="n", gate="left", name="", note="", name_side=None, color=INK):
    """MOSFET: drain/source lead at x0, centred at yc; returns terminal positions.

    NMOS: drain on top, source at the bottom. PMOS: source on top, drain at the bottom.
    """
    s = 1 if gate == "left" else -1          # +1: gate on the left
    xch, xg, xgt = x0 - 0.35 * s, x0 - 0.47 * s, x0 - 0.92 * s
    wire(ax, (xch, yc - 0.36), (xch, yc + 0.36), color=color, lw=2.2)
    wire(ax, (xg, yc - 0.28), (xg, yc + 0.28), color=color)
    wire(ax, (xg, yc), (xgt, yc), color=color)
    for dy in (0.25, -0.25):
        wire(ax, (xch, yc + dy), (x0, yc + dy), color=color)
    wire(ax, (x0, yc + 0.25), (x0, yc + 0.7), color=color)
    wire(ax, (x0, yc - 0.25), (x0, yc - 0.7), color=color)
    # arrow on the source stub: NMOS points out of the channel, PMOS into it
    ys = yc - 0.25 if kind == "n" else yc + 0.25
    a, b = (xch, x0) if kind == "n" else (x0, xch)
    xm = (a + b) / 2
    d = 0.09 * (1 if b > a else -1)
    ax.add_patch(Polygon([(xm + d, ys), (xm - d, ys + 0.07), (xm - d, ys - 0.07)], closed=True, color=color, zorder=3))
    side = name_side or ("right" if s == 1 else "left")
    tx = x0 + 0.12 if side == "right" else x0 - 0.12
    ha = "left" if side == "right" else "right"
    text(ax, tx, yc + 0.14, name, size=10, weight="bold", ha=ha, color=color)
    if note:
        text(ax, tx, yc - 0.16, note, size=7.5, ha=ha, color=MUTED)
    top, bot = (x0, yc + 0.7), (x0, yc - 0.7)
    return {"gate": (xgt, yc), "top": top, "bot": bot,
            "drain": top if kind == "n" else bot, "source": bot if kind == "n" else top}


def resistor_v(ax, x, y_top, y_bot, color=INK):
    n, w = 6, 0.12
    h = (y_top - y_bot) / n
    pts = [(x, y_top)]
    for i in range(n):
        pts.append((x + (w if i % 2 == 0 else -w), y_top - (i + 0.5) * h))
    pts.append((x, y_bot))
    wire(ax, *pts, color=color)


def resistor_h(ax, x_l, x_r, y, color=INK):
    n, w = 6, 0.12
    h = (x_r - x_l) / n
    pts = [(x_l, y)]
    for i in range(n):
        pts.append((x_l + (i + 0.5) * h, y + (w if i % 2 == 0 else -w)))
    pts.append((x_r, y))
    wire(ax, *pts, color=color)


def cap_h(ax, x, y, gap=0.1, h=0.26, color=INK):
    """Capacitor with vertical plates centred at x on a horizontal wire."""
    wire(ax, (x - gap / 2, y - h), (x - gap / 2, y + h), color=color, lw=2.2)
    wire(ax, (x + gap / 2, y - h), (x + gap / 2, y + h), color=color, lw=2.2)


def cap_v(ax, x, y, gap=0.1, w=0.26, color=INK):
    """Capacitor with horizontal plates centred at y on a vertical wire."""
    wire(ax, (x - w, y + gap / 2), (x + w, y + gap / 2), color=color, lw=2.2)
    wire(ax, (x - w, y - gap / 2), (x + w, y - gap / 2), color=color, lw=2.2)


def isrc_down(ax, x, yc, r=0.28, color=INK):
    ax.add_patch(Circle((x, yc), r, facecolor="white", edgecolor=color, lw=LW, zorder=3))
    ax.add_patch(FancyArrowPatch((x, yc + 0.17), (x, yc - 0.19), arrowstyle="-|>", mutation_scale=10, color=color,
                                 lw=1.3, zorder=4))


def switch_h(ax, x_l, x_r, y, closed=False, color=INK):
    """Ideal switch between x_l and x_r on a horizontal wire."""
    a, b = x_l + 0.12, x_r - 0.12
    wire(ax, (x_l, y), (a, y), color=color)
    wire(ax, (b, y), (x_r, y), color=color)
    ax.add_patch(Circle((a, y), 0.045, color=color, zorder=4))
    ax.add_patch(Circle((b, y), 0.045, color=color, zorder=4))
    if closed:
        wire(ax, (a, y), (b, y + 0.02), color=color)
    else:
        wire(ax, (a, y), (b - 0.04, y + 0.28), color=color)


def opamp(ax, x_l, yc, w=1.1, h=1.1, color=INK):
    """Op-amp triangle; returns (+ input, - input, output) positions."""
    ax.add_patch(Polygon([(x_l, yc + h / 2), (x_l, yc - h / 2), (x_l + w, yc)], closed=True, facecolor="white",
                         edgecolor=color, lw=LW, zorder=3))
    yp, yn = yc + h / 4, yc - h / 4
    text(ax, x_l + 0.14, yp, "+", size=11, color=color)
    text(ax, x_l + 0.14, yn, "−", size=11, color=color)
    return (x_l, yp), (x_l, yn), (x_l + w, yc)


def event_arrow(ax, xy_from, xy_to, color):
    ax.add_patch(FancyArrowPatch(xy_from, xy_to, arrowstyle="-|>", mutation_scale=16, color=color, lw=2.2, zorder=6))


def shade(ax, x0, y0, x1, y1, color, label="", label_pos="top", size=8.5):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0.02,rounding_size=0.12",
                                facecolor=color, edgecolor="none", zorder=0))
    if label:
        y = y1 - 0.2 if label_pos == "top" else y0 + 0.2
        text(ax, (x0 + x1) / 2, y, label, size=size, color=MUTED, style="italic")


def finish(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.svg"
    fig.savefig(path, bbox_inches="tight", facecolor="white", metadata={"Date": None})
    plt.close(fig)
    # scale with the page (keep the viewBox, drop the fixed size) so that wide drawings are not clipped
    svg = path.read_text()
    svg = re.sub(r'(<svg[^>]*?) width="[0-9.]+pt" height="[0-9.]+pt"', r'\1 width="100%"', svg, count=1)
    path.write_text(svg)
    print(f"wrote assets/diagrams/{name}.svg")


# --------------------------------------------------------------------------
# Figure 1.1 - the physical sampled-data network and its couplings
# --------------------------------------------------------------------------
def badge(ax, x, y, n, color=CONN):
    ax.add_patch(Circle((x, y), 0.2, facecolor="white", edgecolor=color, lw=1.6, zorder=7))
    text(ax, x, y - 0.01, str(n), size=9, color=color, weight="bold", z=8)


def physical_network() -> None:
    fig, ax = plt.subplots(figsize=(12.0, 8.6))
    ax.set_xlim(-0.3, 15.2)
    ax.set_ylim(-5.6, 5.0)
    ax.set_aspect("equal")
    ax.axis("off")
    yc = 2.7
    shade(ax, 0.0, yc - 1.95, 4.75, yc + 1.75, SHADE["stage1"], "driver: closed-loop amplifier", size=9)
    pin(ax, 0.35, yc + 0.35)
    wire(ax, (0.44, yc + 0.35), (1.3, yc + 0.35))
    text(ax, 0.35, yc + 0.8, "input =\nVtarget", size=9, color=CMD, weight="bold")
    ax.add_patch(Polygon([(1.3, yc + 0.7), (1.3, yc - 0.7), (2.7, yc)], closed=True, facecolor="white",
                         edgecolor=INK, lw=LW, zorder=3))
    text(ax, 1.45, yc + 0.35, "+", size=11)
    text(ax, 1.45, yc - 0.35, "−", size=11)
    dot(ax, 1.95, yc)
    text(ax, 1.98, yc + 0.18, "x", size=9, weight="bold", ha="left")
    xo = 4.2
    wire(ax, (2.7, yc), (xo, yc))
    dot(ax, xo, yc)
    text(ax, xo - 0.05, yc + 0.22, "out", size=9, ha="right", color=MUTED)
    wire(ax, (xo, yc), (xo, yc - 1.35), (1.0, yc - 1.35), (1.0, yc - 0.35), (1.3, yc - 0.35), color=FB, lw=2.0)
    text(ax, 2.6, yc - 1.6, "negative feedback", size=8.5, color=FB, weight="bold")
    text(ax, 2.0, yc - 0.95, "two-stage Miller amplifier;\nx = internal node (Section 5)", size=7.5, color=MUTED)
    badge(ax, 1.55, yc - 1.35, 2, color=FB)
    badge(ax, 3.45, yc + 0.45, 3, color=FB)
    badge(ax, 3.45, yc - 0.45, 7)

    shade(ax, 5.15, yc - 2.75, 11.4, yc + 1.75, SHADE["recv"], "sampling network: CMOS transmission gate + Cs", size=9)
    xn, xp = 6.4, 8.0
    ytg = yc - 0.75
    sn = mos(ax, xn, ytg, "n", gate="left", name="", name_side="right")
    sp = mos(ax, xp, ytg, "p", gate="right", name="", name_side="left")
    wire(ax, (xo, yc), (xp, yc))
    dot(ax, xn, yc)
    y_s = ytg - 0.7
    wire(ax, sn["bot"], (xn, y_s), (10.0, y_s))
    wire(ax, (xp, y_s), sp["bot"])
    dot(ax, xp, y_s)
    pin(ax, sn["gate"][0] - 0.09, ytg, color=CONN)
    pin(ax, sp["gate"][0] + 0.09, ytg, color=CONN)
    text(ax, sn["gate"][0] - 0.1, ytg + 0.42, "phi", size=9.5, weight="bold", color=CONN)
    text(ax, sp["gate"][0] + 0.1, ytg + 0.42, "phib", size=9.5, weight="bold", color=CONN)
    ax.add_patch(FancyArrowPatch((7.2, yc - 0.12), (7.2, y_s + 0.12), arrowstyle="<|-|>", mutation_scale=13,
                                 color=CONN, lw=2.0, zorder=6))
    badge(ax, 7.55, ytg, 1)
    badge(ax, 7.2, yc + 0.5, 4)
    badge(ax, sn["gate"][0] - 0.1, ytg - 0.45, 5)
    badge(ax, sp["gate"][0] + 0.1, ytg - 0.45, 5)
    text(ax, 7.2, y_s - 0.35, "width W sets Ron and the gate capacitances together", size=7.5, color=MUTED)
    badge(ax, 7.2, y_s - 0.75, 6)
    xc = 10.0
    dot(ax, xc, y_s)
    text(ax, xc + 0.08, y_s + 0.22, "samp", size=9, ha="left", color=MUTED)
    wire(ax, (xc, y_s), (xc, y_s - 0.32))
    cap_v(ax, xc, y_s - 0.39)
    wire(ax, (xc, y_s - 0.46), (xc, y_s - 0.75))
    gnd(ax, xc, y_s - 0.75)
    text(ax, xc + 0.35, y_s - 0.3, "Cs = 1 pF", size=9, ha="left", weight="bold")
    text(ax, xc + 0.35, y_s - 0.62, "holds the previous\nsample Vprev", size=8.5, ha="left", va="top", color=CONN,
         weight="bold")

    # acquisition timing
    y0, y1 = -1.55, -0.95
    t0, t1, t2, t3 = 0.5, 1.4, 4.4, 5.3
    wire(ax, (t0, y0), (t1, y0), (t1, y1), (t2, y1), (t2, y0), (t3, y0), color=INK, lw=1.4)
    text(ax, t0 - 0.1, (y0 + y1) / 2, "phi", size=8.5, ha="right", color=MUTED)
    ax.add_patch(FancyArrowPatch((t1, y1 + 0.22), (t2, y1 + 0.22), arrowstyle="<|-|>", mutation_scale=10, color=INK,
                                 lw=1.0, zorder=4))
    text(ax, (t1 + t2) / 2, y1 + 0.45, "acquisition, Tacq = 40 ns", size=8.5)
    dot(ax, t2, y1)
    text(ax, t1, y0 - 0.3, "switch closes", size=8, color=MUTED)
    text(ax, t2, y0 - 0.3, "switch opens:\nVsamp here is the sample", size=8, color=INK, va="top")
    badge(ax, t2 + 0.45, y1 + 0.05, 8)

    items = [
        "Charge sharing: when the switch closes, Cs at Vprev and the driver output exchange charge; Vtarget − Vprev sets its amount and direction.",
        "Feedback carries that output disturbance into the driver's internal node x.",
        "The output voltage sets the output stage's operating point (gm, output resistance, capacitance); the class-A stage supplies far more current than it sinks.",
        "The switch conductance depends on its terminal voltages: each device's gate overdrive changes with the signal level.",
        "Clock edges couple through gate and overlap capacitances into the driver output and Cs, when the switch closes and when it opens.",
        "Switch width lowers Ron but raises those capacitances and the channel charge released at turn-off.",
        "Cs, seen through the switch, loads the driver: settling and loop dynamics depend on it.",
        "Acquisition timing decides which point of the transient becomes the sampled value.",
    ]
    groups = [("Charge and sampled state", [1]), ("Feedback and driver dynamics", [2, 3]),
              ("Switch and clock", [4, 5, 6]), ("Load and timing", [7, 8])]
    yl = -0.2
    for title, members in groups:
        ax.text(5.8, yl, title, fontsize=8.6, color=INK, ha="left", va="center", fontweight="bold", zorder=5)
        yl -= 0.4
        for i in members:
            color = FB if i in (2, 3) else CONN
            badge(ax, 6.05, yl, i, color=color)
            ax.text(6.4, yl, items[i - 1], fontsize=8.0, color=INK, ha="left", va="center", zorder=5)
            yl -= 0.43
        yl -= 0.06
    fig.suptitle("One physically coupled network: driver, feedback, transmission gate, sampling capacitor, and clock",
                 fontsize=12, y=0.985)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.01)
    finish(fig, "physical_network")


# --------------------------------------------------------------------------
# Figure 2.4 - three design scopes for the same network
# --------------------------------------------------------------------------
def tg_symbol(ax, x_l, x_r, y, color=INK, label=True):
    """Transmission-gate symbol: two opposed triangles, phi above, phib (with bubble) below."""
    xm = (x_l + x_r) / 2
    a, b = xm - 0.28, xm + 0.28
    wire(ax, (x_l, y), (a, y), color=color)
    wire(ax, (b, y), (x_r, y), color=color)
    ax.add_patch(Polygon([(a, y + 0.2), (a, y - 0.2), (b, y)], closed=True, facecolor="white", edgecolor=color,
                         lw=LW, zorder=3))
    ax.add_patch(Polygon([(b, y + 0.2), (b, y - 0.2), (a, y)], closed=True, facecolor="none", edgecolor=color,
                         lw=LW, zorder=3))
    wire(ax, (xm, y + 0.12), (xm, y + 0.38), color=color)
    ax.add_patch(Circle((xm, y - 0.17), 0.05, facecolor="white", edgecolor=color, lw=1.2, zorder=4))
    wire(ax, (xm, y - 0.22), (xm, y - 0.38), color=color)
    if label:
        text(ax, xm, y + 0.52, "phi", size=7.5, color=color)
        text(ax, xm, y - 0.52, "phib", size=7.5, color=color)


def mini_network(ax, x0, yc):
    """Driver (with feedback), transmission gate, Cs.

    Returns the x positions of the driver output node, the left and right ends of the gate symbol, and the
    sampling node, so that scope boxes can be drawn between the actual circuit elements."""
    pin(ax, x0, yc + 0.22)
    wire(ax, (x0 + 0.09, yc + 0.22), (x0 + 0.4, yc + 0.22))
    ax.add_patch(Polygon([(x0 + 0.4, yc + 0.5), (x0 + 0.4, yc - 0.5), (x0 + 1.3, yc)], closed=True,
                         facecolor="white", edgecolor=INK, lw=LW, zorder=3))
    xo = x0 + 1.75
    wire(ax, (x0 + 1.3, yc), (xo, yc))
    dot(ax, xo, yc)
    wire(ax, (xo, yc), (xo, yc - 0.75), (x0 + 0.25, yc - 0.75), (x0 + 0.25, yc - 0.22), (x0 + 0.4, yc - 0.22),
         color=FB, lw=1.5)
    tg_symbol(ax, xo, xo + 1.6, yc, color=CONN)
    xs = xo + 2.15
    wire(ax, (xo + 1.6, yc), (xs, yc), (xs, yc - 0.3))
    dot(ax, xs, yc)
    cap_v(ax, xs, yc - 0.37)
    wire(ax, (xs, yc - 0.44), (xs, yc - 0.6))
    gnd(ax, xs, yc - 0.6)
    text(ax, xs + 0.3, yc - 0.37, "Cs", size=8.5, ha="left")
    xm = xo + 0.8
    return xo, xm - 0.28, xm + 0.28, xs


def scope_box(ax, x0, y0, x1, y1, color, label):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0.02,rounding_size=0.15",
                                facecolor="none", edgecolor=color, lw=2.0, ls="--", zorder=1))
    text(ax, (x0 + x1) / 2, y1 + 0.22, label, size=8, color=color, weight="bold")


def design_scopes() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13.0, 4.6))
    panels = [
        ("A  Joint scope", "driver, switch and Cs designed and verified together",
         "designed jointly: driver current, switch width, clock, Cs, Tacq\nacross the boundary: nothing inside the network\n"
         "verified: the connected circuit itself"),
        ("B  Boundary before the switch", "the driver characterized on its own",
         "across the boundary: Cs, range, Tacq, and a switch\nrepresentation (one R_if, a range, or a model)\n"
         "verified: driver block tests; the connected test at integration"),
        ("C  Boundary after the switch", "driver + switch characterized as one block",
         "across the boundary: Cs, range, Tacq, error limit at samp\ninside the block: turn-on disturbance, Ron(V)\n"
         "verified: the block over the operating points; a new switch = a new block"),
    ]
    for ax, (title, sub, notes), kind in zip(axes, panels, "ABC"):
        ax.set_xlim(-0.2, 5.4)
        ax.set_ylim(-3.3, 2.0)
        ax.set_aspect("equal")
        ax.axis("off")
        text(ax, -0.15, 1.8, title, size=11, ha="left", weight="bold")
        text(ax, -0.15, 1.45, sub, size=8.5, ha="left", color=MUTED, style="italic")
        yc = 0.25
        xo, xg0, xg1, xs = mini_network(ax, 0.25, yc)
        right = xs + 0.75  # leaves room for the "Cs" label
        if kind == "A":
            scope_box(ax, 0.0, -0.85, right, 0.95, CMD, "one design problem")
        elif kind == "B":
            # boundary on the wire between the driver output node and the switch
            scope_box(ax, 0.0, -0.85, xo + 0.2, 0.95, CMD, "driver block")
            scope_box(ax, xo + 0.32, -0.85, right, 0.95, MODEL, "sampling network")
        else:
            # boundary on the wire between the switch and the sampling node
            scope_box(ax, 0.0, -0.85, xg1 + 0.2, 0.95, CMD, "driver + switch block")
            scope_box(ax, xs - 0.4, -0.85, right, 0.95, MODEL, "Cs")
        ax.text(-0.15, -1.25, notes, fontsize=8.0, color=INK, ha="left", va="top", linespacing=1.5)
    fig.suptitle("Three possible design scopes for the same physically coupled network", fontsize=12, y=0.99)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.01, wspace=0.08)
    finish(fig, "design_scopes")


# --------------------------------------------------------------------------
# Diagram 4 - the interface and the four tests of the same source
# --------------------------------------------------------------------------
def source_with_feedback(ax, x, yc, vcmd_label, cmd_event):
    """Closed-loop (unity-gain) driver; returns the output-node position."""
    shade(ax, x - 0.15, yc - 1.05, x + 2.35, yc + 1.05, SHADE["stage1"], "driver: unity-gain amplifier",
          size=8)
    text(ax, x + 1.1, yc - 0.85, "identical in all four tests", size=7.5, color=MUTED, style="italic")
    pin(ax, x - 0.75, yc + 0.275)
    wire(ax, (x - 0.66, yc + 0.275), (x + 0.2, yc + 0.275))
    text(ax, x - 0.75, yc + 0.65, vcmd_label, size=8.5, color=CMD if cmd_event else INK)
    p, n, o = opamp(ax, x + 0.2, yc)
    xo = x + 1.95
    wire(ax, o, (xo, yc))
    dot(ax, xo, yc)
    wire(ax, (xo, yc), (xo, yc - 0.92), (x + 0.05, yc - 0.92), (x + 0.05, yc - 0.275), (x + 0.2, yc - 0.275))
    if cmd_event:
        event_arrow(ax, (x - 1.45, yc + 0.275), (x - 0.88, yc + 0.275), CMD)
    return xo, yc


def diagram_4() -> None:
    fig, axes = plt.subplots(4, 1, figsize=(10.6, 12.5))
    rows = [
        ("(a)  Block test of the driver at its external input: input step",
         "testbench tb_t0_command.spice",
         "input steps\nVprev → Vtarget", True, "direct",
         "excitation at the external input;\n1 pF hard-wired to the output",
         "last time |Vout − Vref| ≥ ε"),
        ("(b)  Block test of the driver at its output port: the switch represented by R_if",
         "testbench tb_t3_interface_model.spice",
         "input held\nat Vtarget", False, "model",
         "excitation at the output port:\nCs holds Vprev; linear on-resistance",
         "last time |Vsample − Vref| ≥ ε"),
        ("(c)  Connected test: the driver and the real sampling network",
         "testbench tb_t1_connected.spice",
         "input held\nat Vtarget", False, "closing",
         "excitation at the output port:\nCs holds Vprev; transmission gate",
         "last time |Vsample − Vref| ≥ ε"),
        ("(m)  Matched control for (c): input step through the closed gate",
         "testbench tb_t2_matched.spice",
         "input steps\nVprev → Vtarget", True, "closed",
         "excitation at the external input;\nsame gate, Cs, and initial Cs error as (c)",
         "compare with (c) on the same time axis"),
    ]
    for ax, (title, tb, vlabel, cmd_event, load, how, metric) in zip(axes, rows):
        ax.set_xlim(-0.3, 11.2)
        ax.set_ylim(-0.1, 2.85)
        ax.set_aspect("equal")
        ax.axis("off")
        text(ax, -0.25, 2.72, title, size=11, ha="left", weight="bold")
        text(ax, 11.15, 2.72, tb, size=7.5, ha="right", color=MUTED)
        yc = 1.15
        xo, _ = source_with_feedback(ax, 1.2, yc, vlabel, cmd_event)
        text(ax, xo + 0.07, yc + 0.2, "out", size=8.5, ha="left", color=MUTED)
        if load == "direct":
            shade(ax, 3.7, yc - 1.05, 6.35, yc + 1.05, SHADE["fix"], "block-test load (no switch)", size=8)
            xc = 4.6
            wire(ax, (xo, yc), (xc, yc), (xc, yc - 0.3))
            cap_v(ax, xc, yc - 0.37)
            wire(ax, (xc, yc - 0.44), (xc, yc - 0.65))
            gnd(ax, xc, yc - 0.65)
            text(ax, xc + 0.35, yc - 0.37, "Cchar = 1 pF\nalways connected", size=8.5, ha="left")
        elif load == "model":
            shade(ax, 3.7, yc - 1.05, 6.35, yc + 1.05, SHADE["fix"])
            text(ax, 5.6, yc + 0.78, "interface representation:\nideal switch, R_if, Cs", size=8, color=MUTED,
                 style="italic")
            xs0, xs1 = 3.85, 4.45
            wire(ax, (xo, yc), (xs0, yc))
            switch_h(ax, xs0, xs1, yc, closed=False, color=MODEL)
            resistor_h(ax, xs1, 5.15, yc, color=MODEL)
            # R_if = maximum DC Ron of the transmission gate over 0.6-1.2 V, sky130_summary.json "switch_ron"
            text(ax, 4.8, yc + 0.3, "R_if = Ron,max", size=7.5, color=MODEL)
            text(ax, 4.5, yc - 0.3, "closes at t = 0", size=7.5, color=MODEL)
            xc = 5.5
            wire(ax, (5.15, yc), (xc, yc), (xc, yc - 0.3))
            dot(ax, xc, yc)
            text(ax, xc + 0.07, yc + 0.2, "samp", size=8.5, ha="left", color=MUTED)
            cap_v(ax, xc, yc - 0.37)
            wire(ax, (xc, yc - 0.44), (xc, yc - 0.65))
            gnd(ax, xc, yc - 0.65)
            text(ax, xc + 0.33, yc - 0.25, "Cs 1 pF", size=8.5, ha="left")
            text(ax, xc + 0.33, yc - 0.52, "holds Vprev", size=8.5, ha="left", color=MODEL, weight="bold")
        else:
            shade(ax, 3.7, yc - 1.05, 6.35, yc + 1.05, SHADE["recv"])
            text(ax, 5.75, yc + 0.78, "sampling network:\ngate + Cs", size=8, color=MUTED, style="italic")
            xs0, xs1 = 3.95, 4.95
            wire(ax, (xo, yc), (xs0, yc))
            sw_color = CONN if load == "closing" else INK
            tg_symbol(ax, xs0, xs1, yc, color=sw_color, label=False)
            text(ax, (xs0 + xs1) / 2, yc - 0.55, "closes at t = 0" if load == "closing" else "already closed",
                 size=7.5, color=sw_color)
            xc = 5.5
            wire(ax, (xs1, yc), (xc, yc), (xc, yc - 0.3))
            dot(ax, xc, yc)
            text(ax, xc + 0.07, yc + 0.2, "samp", size=8.5, ha="left", color=MUTED)
            cap_v(ax, xc, yc - 0.37)
            wire(ax, (xc, yc - 0.44), (xc, yc - 0.65))
            gnd(ax, xc, yc - 0.65)
            text(ax, xc + 0.33, yc - 0.25, "Cs 1 pF", size=8.5, ha="left")
            if load == "closing":
                text(ax, xc + 0.33, yc - 0.52, "holds Vprev", size=8.5, ha="left", color=CONN, weight="bold")
                event_arrow(ax, ((xs0 + xs1) / 2, yc + 1.45), ((xs0 + xs1) / 2, yc + 0.45), CONN)
                text(ax, (xs0 + xs1) / 2 - 0.1, yc + 1.35, "stored charge\nenters here", size=8, ha="right",
                     va="top", color=CONN, weight="bold")
        color = CMD if cmd_event else (MODEL if load == "model" else CONN)
        x_note = 6.75
        text(ax, x_note, yc + 0.35, how, size=8.5, ha="left", color=color)
        text(ax, x_note, yc - 0.3, metric, size=8.5, ha="left")
        if load in ("closing", "model"):
            text(ax, x_note, yc - 0.72, "(an ideal fixture charges Cs to Vprev and opens before t = 0)", size=7.5,
                 ha="left", color=MUTED)
    fig.suptitle("One driver, the same 1 pF capacitance, excited at two different ports",
                 fontsize=13, y=0.995)
    fig.text(0.5, 0.004, "Blue: excitation at the external input.   Green and orange: excitation at the output port, "
             "with the switch represented by R_if (green) or the real transmission gate (orange).   "
             "Vref: settled output for the target.   ε = 0.29 mV.", ha="center", fontsize=8.0, color=MUTED)
    fig.subplots_adjust(hspace=0.08, left=0.02, right=0.98, top=0.962, bottom=0.025)
    finish(fig, "four_tests")


# --------------------------------------------------------------------------
# Diagram 5 - idealized two-state source model
# --------------------------------------------------------------------------
def block(ax, x0, y0, w, h, label, color=INK, fill="white", size=10):
    ax.add_patch(Rectangle((x0, y0), w, h, facecolor=fill, edgecolor=color, lw=LW, zorder=3))
    text(ax, x0 + w / 2, y0 + h / 2, label, size=size, color=color)


def arrow(ax, a, b, color=INK):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=12, color=color, lw=LW, zorder=3,
                                 shrinkA=0, shrinkB=0))


def diagram_5() -> None:
    fig, ax = plt.subplots(figsize=(10.6, 5.6))
    ax.set_xlim(-0.4, 12.6)
    ax.set_ylim(-1.3, 5.2)
    ax.set_aspect("equal")
    ax.axis("off")
    shade(ax, 1.0, 0.0, 7.3, 4.75, SHADE["stage1"],
          "amplifier with one internal state Vd (plays the role of node x in the SKY130 circuit)",
          label_pos="bottom", size=8.5)
    shade(ax, 7.5, 0.0, 12.4, 4.75, SHADE["stage2"], "output node and sampling network", label_pos="bottom", size=8.5)

    yc = 2.5
    # command input
    pin(ax, 0.0, yc)
    text(ax, 0.0, yc + 0.5, "Vin\nexternal input", size=9, color=CMD)
    wire(ax, (0.09, yc), (1.3, yc))
    block(ax, 1.3, yc - 0.35, 1.0, 0.7, "1 + Ae")
    arrow(ax, (2.3, yc), (3.05, yc))
    ax.add_patch(Circle((3.3, yc), 0.25, facecolor="white", edgecolor=INK, lw=LW, zorder=3))
    text(ax, 3.3, yc, "Σ", size=11)
    text(ax, 2.9, yc + 0.28, "+", size=10)
    text(ax, 3.55, yc + 0.42, "−", size=11)
    arrow(ax, (3.55, yc), (4.2, yc))
    block(ax, 4.2, yc - 0.45, 1.6, 0.9, "1\n1 + s·τd")
    text(ax, 5.0, yc - 0.75, "one time constant τd", size=8, color=MUTED)
    wire(ax, (5.8, yc), (6.6, yc))
    dot(ax, 6.6, yc)
    text(ax, 6.6, yc + 0.35, "Vd", size=11, weight="bold")
    text(ax, 6.6, yc - 0.45, "internal drive\nvoltage", size=8, color=MUTED)
    # Rout to output node
    wire(ax, (6.6, yc), (6.9, yc))
    resistor_h(ax, 6.9, 8.0, yc)
    text(ax, 7.45, yc + 0.35, "Rout", size=9.5)
    text(ax, 7.45, yc - 0.4, "output\nresistance", size=8, color=MUTED)
    wire(ax, (8.0, yc), (9.0, yc))
    dot(ax, 9.0, yc)
    text(ax, 8.85, yc + 0.3, "Vout", size=11, weight="bold", ha="right")
    text(ax, 9.15, yc - 0.25, "output node", size=8, ha="left", color=MUTED)
    # C_T to ground
    wire(ax, (9.0, yc), (9.0, 1.65))
    cap_v(ax, 9.0, 1.58)
    wire(ax, (9.0, 1.51), (9.0, 1.2))
    gnd(ax, 9.0, 1.2)
    text(ax, 8.65, 1.58, "C_T = Co + Cs\ndriver output +\nsampling capacitor", size=8, ha="right")
    # receiver disturbance current
    wire(ax, (9.0, yc), (10.6, yc), (10.6, 1.9))
    isrc_down(ax, 10.6, 1.6, color=CONN)
    wire(ax, (10.6, 1.32), (10.6, 1.2))
    gnd(ax, 10.6, 1.2)
    text(ax, 10.95, 1.75, "Idist", size=10, ha="left", color=CONN, weight="bold")
    text(ax, 10.95, 1.45, "charge drawn by the\nsampling network", size=8, ha="left", va="top", color=CONN)
    # feedback Ae from Vout to the summing node
    wire(ax, (9.0, yc), (9.0, 3.9), (6.2, 3.9))
    arrow(ax, (6.2, 3.9), (5.6, 3.9))
    block(ax, 4.6, 3.6, 1.0, 0.6, "Ae")
    wire(ax, (4.6, 3.9), (3.3, 3.9))
    arrow(ax, (3.3, 3.9), (3.3, yc + 0.25))
    text(ax, 7.4, 4.12, "negative feedback from the output", size=8, color=MUTED, style="italic")
    # where each event enters
    event_arrow(ax, (0.0, 1.0), (0.0, yc - 0.2), CMD)
    text(ax, -0.3, 0.55, "input step:\nVd starts displaced", size=8.5, ha="left", va="center", color=CMD)
    event_arrow(ax, (11.4, 4.3), (9.15, yc + 0.15), CONN)
    text(ax, 12.4, 4.85, "output-port disturbance: Vout jumps by charge\nsharing, Vd starts at its settled value",
         size=8.5, ha="right", va="bottom", color=CONN)
    text(ax, 6.0, -0.75, "τd·dVd/dt = Vin + Ae·(Vin − Vout) − Vd          C_T·dVout/dt = (Vd − Vout)/Rout − Idist",
         size=9.5)
    fig.suptitle("Reduced closed-loop driver: one internal state, one output node", fontsize=13,
                 y=0.995)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.02)
    finish(fig, "reduced_model")


# --------------------------------------------------------------------------
# Diagram 6 - SKY130 transistor-level circuit (netlist source_two_stage.spice + receiver of tb_t1_connected.spice)
# --------------------------------------------------------------------------
def diagram_6() -> None:
    fig, ax = plt.subplots(figsize=(12.5, 9.0))
    ax.set_xlim(-0.3, 15.0)
    ax.set_ylim(-0.3, 10.6)
    ax.set_aspect("equal")
    ax.axis("off")

    shade(ax, 0.05, 0.3, 1.95, 9.3, SHADE["bias"], "bias", size=9)
    shade(ax, 2.25, 0.3, 7.45, 9.3, SHADE["stage1"], "differential input stage (M1–M5)", size=9.5)
    shade(ax, 7.6, 0.3, 10.25, 9.3, SHADE["stage2"], "second stage (M6, M7)", size=9.5)
    shade(ax, 11.0, 0.3, 14.9, 9.3, SHADE["recv"], "sampling network: CMOS transmission gate + Cs", size=9.5)

    x_l, x_r, x_o = 3.4, 6.2, 9.4   # first-stage branches and second-stage column
    y_pair, y_mirror, y_bias = 4.6, 7.6, 2.0

    # bias: Iref into the diode-connected M8
    vdd(ax, 0.8, 8.55)
    wire(ax, (0.8, 8.55), (0.8, 8.0))
    isrc_down(ax, 0.8, 7.7)
    text(ax, 1.18, 7.7, "Iref\n10 µA", size=8.5, ha="left")
    m8 = mos(ax, 0.8, y_bias, "n", gate="right", name="M8", note="5/1 ×1", name_side="left")
    wire(ax, (0.8, 7.42), m8["drain"])
    wire(ax, m8["gate"], (m8["gate"][0], 3.1), (0.8, 3.1))
    dot(ax, 0.8, 3.1)
    text(ax, 0.72, 4.3, "ibias", size=8.5, ha="right", color=MUTED)
    gnd(ax, *m8["source"])

    # first stage
    m3 = mos(ax, x_l, y_mirror, "p", gate="right", name="M3", note="5/0.5 ×2 LVT", name_side="left")
    m4 = mos(ax, x_r, y_mirror, "p", gate="left", name="M4", note="5/0.5 ×2 LVT", name_side="right")
    vdd(ax, *m3["source"])
    vdd(ax, *m4["source"])
    wire(ax, m3["gate"], m4["gate"])
    wire(ax, m3["gate"], (m3["gate"][0], 6.55), (x_l, 6.55))
    dot(ax, m3["gate"][0], y_mirror)
    dot(ax, x_l, 6.55)
    text(ax, x_l - 0.12, 6.4, "d1", size=8.5, ha="right", color=MUTED)
    m1 = mos(ax, x_l, y_pair, "n", gate="left", name="M1", note="5/0.5 ×4 LVT", name_side="right")
    m2 = mos(ax, x_r, y_pair, "n", gate="right", name="M2", note="5/0.5 ×4 LVT", name_side="left")
    wire(ax, m3["drain"], m1["drain"])
    wire(ax, m4["drain"], m2["drain"])
    y_x = 6.1
    dot(ax, x_r, y_x)
    text(ax, x_r + 0.12, y_x - 0.22, "x", size=11, ha="left", weight="bold")
    text(ax, x_r + 0.12, y_x - 0.55, "internal node\n(first-stage output)", size=7.5, ha="left", va="top",
         color=MUTED)
    y_tail = 3.45
    wire(ax, m1["source"], (x_l, y_tail), (x_r, y_tail), m2["source"])
    x_t = (x_l + x_r) / 2
    dot(ax, x_t, y_tail)
    text(ax, x_t + 0.1, y_tail + 0.18, "tail", size=8.5, ha="left", color=MUTED)
    m5 = mos(ax, x_t, y_bias, "n", gate="left", name="M5", note="5/1 ×2", name_side="right")
    wire(ax, m5["drain"], (x_t, y_tail))
    gnd(ax, *m5["source"])
    wire(ax, m8["gate"], m5["gate"])
    dot(ax, m8["gate"][0], y_bias)
    # command input on M2
    pin(ax, 7.2, 3.6)
    wire(ax, m2["gate"], (7.2, y_pair), (7.2, 3.69))
    text(ax, 7.2, 3.25, "vcmd", size=10, weight="bold", color=CMD)
    text(ax, 7.2, 2.9, "external\ninput", size=7.5, color=CMD, va="top")

    # second stage
    m6 = mos(ax, x_o, y_mirror, "p", gate="left", name="M6", note="5/0.5 ×20 LVT", name_side="right")
    m7 = mos(ax, x_o, y_bias, "n", gate="left", name="M7", note="5/1 ×10", name_side="right")
    vdd(ax, *m6["source"])
    gnd(ax, *m7["source"])
    wire(ax, m6["drain"], m7["drain"])
    x_turn = 7.85
    wire(ax, (x_r, y_x), (x_turn, y_x), (x_turn, y_mirror), m6["gate"])
    # Rz + Cc from x to out
    wire(ax, (x_turn, y_x), (8.0, y_x))
    dot(ax, x_turn, y_x)
    y_c = y_x
    resistor_h(ax, 8.0, 8.6, y_c)
    text(ax, 8.3, y_c + 0.33, "Rz 1.5 kΩ", size=8)
    wire(ax, (8.6, y_c), (8.85, y_c))
    cap_h(ax, 8.9, y_c)
    wire(ax, (8.95, y_c), (x_o, y_c))
    text(ax, 8.9, y_c - 0.45, "Cc 0.5 pF", size=8)
    ax.add_patch(FancyBboxPatch((7.95, y_c - 0.7), 1.35, 1.35, boxstyle="round,pad=0.02,rounding_size=0.1",
                                facecolor="none", edgecolor=MUTED, lw=1.0, ls="--", zorder=1))
    text(ax, 8.62, y_c + 0.95, "Miller compensation", size=8.5, color=INK, style="italic")
    dot(ax, x_o, y_c)
    # M7 gate from ibias, routed below the ground symbols
    x_br = 2.9
    dot(ax, x_br, y_bias)
    wire(ax, (x_br, y_bias), (x_br, 0.55), (8.15, 0.55), (8.15, y_bias), m7["gate"])
    text(ax, 5.6, 0.72, "ibias", size=8.5, color=MUTED)

    # output node and unity-gain feedback to the M1 gate
    y_out = y_pair
    dot(ax, x_o, y_out)
    text(ax, x_o + 0.12, y_out + 0.22, "out", size=11, ha="left", weight="bold")
    text(ax, x_o + 0.12, y_out - 0.2, "driver\noutput", size=7.5, ha="left", va="top", color=MUTED)
    x_fb = 10.6
    wire(ax, (x_o, y_out), (x_fb, y_out))
    wire(ax, (x_fb, y_out), (x_fb, 9.75), (2.05, 9.75), (2.05, y_pair), m1["gate"], color=FB, lw=2.0)
    dot(ax, x_fb, y_out)
    text(ax, 6.3, 9.97, "feedback path: out → M1 gate (unity-gain feedback)", size=9.5, color=FB, weight="bold")
    text(ax, 2.12, y_pair + 0.2, "fb", size=8.5, ha="left", color=FB)

    # sampler: CMOS transmission gate (SWN, SWP in parallel) and Cs
    xn, xp, y_tg = 12.0, 13.5, 3.6
    sn = mos(ax, xn, y_tg, "n", gate="left", name="SWN", name_side="right")
    sp = mos(ax, xp, y_tg, "p", gate="right", name="SWP", name_side="left")
    wire(ax, (x_fb, y_out), (xp, y_out), sp["top"])
    dot(ax, xn, y_out)
    wire(ax, (xn, y_out), sn["top"])
    y_s = 2.6
    wire(ax, sn["bot"], (xn, y_s), (xp, y_s), sp["bot"])
    x_c = 12.75
    dot(ax, x_c, y_s)
    pin(ax, sn["gate"][0] - 0.09, y_tg, color=CONN)
    pin(ax, sp["gate"][0] + 0.09, y_tg, color=CONN)
    text(ax, sn["gate"][0] - 0.09, y_tg + 0.42, "phi", size=10, weight="bold", color=CONN)
    text(ax, sp["gate"][0] + 0.09, y_tg + 0.42, "phib", size=10, weight="bold", color=CONN)
    text(ax, 12.75, 5.55, "phi 0 → 1.8 V, phib 1.8 → 0 V,\n0.2 ns edges at the sampling event\n"
         "bulks: SWN at 0 V, SWP at VDD", size=7.5, color=CONN)
    text(ax, 12.75, 0.75, "SWN nfet_01v8 5/0.15 ×3 (15 µm)\nSWP pfet_01v8 5/0.15 ×6 (30 µm)", size=7.5, color=MUTED)
    text(ax, x_c + 0.12, y_s + 0.2, "samp", size=10, ha="left", weight="bold")
    wire(ax, (x_c, y_s), (x_c, 2.1))
    cap_v(ax, x_c, 2.03)
    wire(ax, (x_c, 1.96), (x_c, 1.3))
    gnd(ax, x_c, 1.3)
    text(ax, x_c - 0.38, 2.03, "Cs\n1 pF", size=9, ha="right")
    text(ax, x_c + 0.4, 1.95, "holds the previous\nsample Vprev until\nthe gate closes", size=7.5, ha="left",
         va="top", color=CONN)

    text(ax, 7.4, -0.12, "SKY130 1.8 V devices, W/L in µm × multiplier; device names as in the netlists. LVT: nfet_01v8_lvt / "
         "pfet_01v8_lvt; other NMOS: nfet_01v8.  Ideal Iref, Rz, Cc, Cs.  VDD = 1.8 V, 130 µA quiescent.\n"
         "In the connected test an ideal fixture (not drawn) charges Cs to Vprev and opens before the gate closes.",
         size=8, color=MUTED)
    fig.suptitle("The simulated SKY130 circuit: two-stage Miller-compensated amplifier in unity-gain "
                 "feedback,\ndriving a CMOS transmission gate and a sampling capacitor", fontsize=12, y=0.995)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.01)
    finish(fig, "sky130_circuit")


if __name__ == "__main__":
    physical_network()
    design_scopes()
    diagram_4()
    diagram_5()
    diagram_6()

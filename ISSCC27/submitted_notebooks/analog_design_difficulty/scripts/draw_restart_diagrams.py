#!/usr/bin/env python3
"""Explanatory diagrams of the rebuilt notebook (restart), drawn with Matplotlib primitives.

    uv run python scripts/draw_restart_diagrams.py

Writes assets/diagrams/requirement_vs_network.svg (Figure 1), sampling_cycle.svg (Figure 2), and
working_checks_cycle.svg (Figure 3). These are explanatory drawings, not simulation results. Quantities named in them are those of
experiments/closure/CLOSURE_BRIEF.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "diagrams"

INK = "#222222"
MUTED = "#777777"
REQ = "#2a5d9f"      # requirement tree
KNOB = "#555555"     # quantities treated as design variables
PHYS = "#b4532a"     # circuit responses, physical dependence
STATE = "#7a4fb0"    # stored state / cycle highlight
SUM = "#1f7a4d"      # signed sum (parent quantity)
RC = {"font.family": "DejaVu Sans", "font.size": 9.5, "svg.hashsalt": "restart", "svg.fonttype": "path"}
plt.rcParams.update(RC)


def box(ax, x, y, w, h, s, edge=INK, fill="white", size=9.5, weight="normal", lw=1.4, style="round,pad=0.02,rounding_size=0.08",
        color=None, z=3):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle=style, facecolor=fill, edgecolor=edge, lw=lw,
                                zorder=z))
    ax.text(x, y, s, ha="center", va="center", fontsize=size, color=color or INK, weight=weight, zorder=z + 1,
            linespacing=1.15)


def arr(ax, a, b, color=INK, lw=1.3, ls="-", rad=0.0, head=9, z=2, alpha=1.0, shrinkA=14, shrinkB=14):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=head, color=color, lw=lw, ls=ls, alpha=alpha,
                                 connectionstyle=f"arc3,rad={rad}", shrinkA=shrinkA, shrinkB=shrinkB, zorder=z))


def finish(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight", metadata={"Date": None})
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", dpi=150)
    plt.close(fig)


# --------------------------------------------------------------------------- Figure 1

def requirement_vs_network() -> None:
    fig, ax = plt.subplots(figsize=(14.5, 7.6))
    ax.set_xlim(0, 29)
    ax.set_ylim(-0.9, 15.2)
    ax.axis("off")

    # ---------------- left: requirement hierarchy (a tree)
    ax.text(4.6, 14.75, "Requirement hierarchy (a tree)", ha="center", fontsize=12, weight="bold", color=REQ)
    W = 9.0
    box(ax, 4.6, 13.55, W, 1.05, "System context\na high-impedance circuit reads the held voltage", edge=REQ, size=9)
    box(ax, 4.6, 12.0, W, 1.05, "Parent function\nacquire in 40 ns, hold for 60 ns; input 0.6–1.2 V", edge=REQ)
    box(ax, 4.6, 10.15, W, 1.65, "Parent requirement\nheld-sample residual within ±1 LSB (0.586 mV)\nafter two-point correction, any previous\nsample, declared PVT set", edge=REQ, lw=2.2)
    for y0, y1 in ((13.0, 12.55), (11.45, 11.0)):
        arr(ax, (4.6, y0), (4.6, y1), color=REQ, shrinkA=0, shrinkB=0)
    leaves = [("static\ntracking", 0.95), ("step at\nopening", 2.85), ("acquisition,\nhistory", 4.75),
              ("hold droop,\nfeedthrough", 6.65), ("reserve", 8.5)]
    leaf_y, bus_y = 7.4, 8.25
    # one stem from the parent requirement, a bus over the five leaves, short branches down to each leaf
    ax.plot([4.6, 4.6], [9.32, bus_y], color=REQ, lw=1.0, solid_capstyle="butt", zorder=2)
    ax.plot([leaves[0][1], leaves[-1][1]], [bus_y, bus_y], color=REQ, lw=1.0, solid_capstyle="butt", zorder=2)
    for label, x in leaves:
        box(ax, x, leaf_y, 1.75, 1.0, label, edge=REQ, size=8.0)
        arr(ax, (x, bus_y), (x, leaf_y + 0.5), color=REQ, shrinkA=0, shrinkB=0, lw=1.0, head=7)
    ax.text(4.35, 8.8, "provisional deterministic\nallocations", ha="right", va="center", fontsize=8.5, color=REQ,
            style="italic", linespacing=1.1)
    box(ax, 4.6, 5.95, 7.4, 0.75, "random noise (kT/C, driver): separate budget", edge=MUTED, size=8.5, color=MUTED,
        style="round,pad=0.02,rounding_size=0.08")
    ax.text(4.6, 4.55, "The tree organizes targets and checks.\n"
            "It does not say how the effects on the right\n"
            "share causes, trade against each other, or cancel.", ha="center", va="center",
            fontsize=9, color=INK, style="italic")

    # ---------------- right: physical / design dependency network
    ax.text(19.6, 14.75, "Physical and design dependencies (a network with cycles)", ha="center", fontsize=12,
            weight="bold", color=PHYS)
    K, P = (2.6, 1.05), (2.9, 1.05)
    nodes = {
        # treated as design variables in this formulation
        "bias": (12.6, 13.0, "driver bias\ncurrent", K, "var"),
        "comp": (12.6, 11.0, "compensation\ncapacitance", K, "var"),
        "W": (12.6, 8.4, "switch type,\nwidth", K, "var"),
        "clk": (12.6, 5.5, "clock edge,\nsequence", K, "var"),
        "Cs": (12.6, 3.0, "Cs", K, "var"),
        # circuit responses in this formulation
        "pwr": (16.6, 13.75, "supply current,\npower", (2.9, 0.95), "resp"),
        "Zout": (16.6, 11.75, "loop gain, output\nimpedance Zout(f)", P, "resp"),
        "Ron": (16.6, 9.4, "switch Ron(V)", P, "resp"),
        "q": (16.6, 7.0, "channel charge q(V),\nswitch capacitance", P, "resp"),
        "noise": (16.6, 2.2, "kT/C noise,\narea", P, "resp"),
        "kick": (19.6, 4.0, "charge sharing and\ninjection at closure", (3.2, 1.05), "resp"),
        "stat": (21.1, 13.6, "static tracking\nerror", P, "resp"),
        "acq": (21.1, 11.2, "acquisition error\nat 40 ns", P, "resp"),
        "off": (21.1, 6.2, "step at opening", P, "resp"),
        "hold": (21.1, 8.65, "hold droop,\nfeedthrough", P, "resp"),
        # parent quantity and stored state
        "sum": (25.6, 9.9, "held-sample\nerror\n(signed sum)", (2.4, 1.6), "sum"),
        "prev": (25.6, 4.0, "previous held\nvoltage", P, "state"),
    }
    style = {"var": (KNOB, "#e9e9e9", 1.4), "resp": (PHYS, "white", 1.4), "sum": (SUM, "white", 2.3),
             "state": (STATE, "white", 1.8)}
    for k, (x, y, s_, (w, h), kd) in nodes.items():
        ec, fc, lw = style[kd]
        box(ax, x, y, w, h, s_, edge=ec, fill=fc, size=8.8, lw=lw)

    def clip(k, toward):
        x, y, _, (w, h), _ = nodes[k]
        dx, dy = toward[0] - x, toward[1] - y
        t = min((w / 2 + 0.08) / abs(dx) if dx else 1e9, (h / 2 + 0.08) / abs(dy) if dy else 1e9)
        return (x + dx * t, y + dy * t)

    def e(a, b, color=PHYS, lw=1.3, rad=0.0, ls="-", style_="-|>"):
        pa, pb = nodes[a][:2], nodes[b][:2]
        ax.add_patch(FancyArrowPatch(clip(a, pb), clip(b, pa), arrowstyle=style_, mutation_scale=10, color=color,
                                     lw=lw, ls=ls, connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0, zorder=2))

    for a, b, rad in (("bias", "pwr", 0), ("bias", "Zout", 0), ("comp", "Zout", 0), ("Zout", "stat", 0),
                      ("bias", "stat", -0.1),
                      ("W", "Ron", 0), ("W", "q", 0), ("clk", "off", 0.0), ("q", "off", 0), ("Zout", "off", 0.0),
                      ("Ron", "acq", 0), ("Zout", "acq", 0), ("q", "hold", 0), ("q", "kick", 0),
                      ("Cs", "kick", 0), ("Cs", "noise", 0), ("Cs", "off", 0.0),
                      ("stat", "sum", 0), ("off", "sum", 0.12), ("hold", "sum", 0.0)):
        e(a, b, rad=rad)
    # the switch and Cs load the driver loop during acquisition
    e("Ron", "Zout", rad=0.0, style_="<|-|>")
    ax.text(16.45, 10.6, "Ron, Cs load\nthe loop", fontsize=7.6, color=PHYS, style="italic", va="center", ha="right")
    # stored-state cycle
    for a, b, rad in (("acq", "sum", 0), ("sum", "prev", 0), ("prev", "kick", 0), ("kick", "acq", -0.35)):
        e(a, b, color=STATE, lw=2.2, rad=rad)
    ax.text(27.2, 7.0, "sample k sets\nthe start of\nsample k+1", ha="center", fontsize=8.3, color=STATE,
            style="italic")
    # designer revision
    ax.add_patch(FancyArrowPatch((25.6, 10.75), (12.6, 13.6), arrowstyle="-|>", mutation_scale=10, color=SUM, lw=1.3,
                                 ls=(0, (4, 3)), connectionstyle="arc3,rad=0.32", zorder=2))
    ax.plot([11.05, 11.05], [2.6, 13.4], color=SUM, lw=1.2, ls=(0, (4, 3)))
    ax.text(10.85, 8.0, "revise", rotation=90, ha="center", va="center", fontsize=8.5, color=SUM, style="italic")

    # legend: node roles (formulation-dependent), then edge kinds
    ly = 1.05
    box(ax, 11.75, ly, 0.9, 0.5, "", edge=KNOB, fill="#e9e9e9", lw=1.4)
    ax.text(12.35, ly, "treated as a design variable here", va="center", fontsize=8.5, color=INK)
    box(ax, 18.15, ly, 0.9, 0.5, "", edge=PHYS, fill="white", lw=1.4)
    ax.text(18.75, ly, "circuit response here", va="center", fontsize=8.5, color=INK)
    box(ax, 23.0, ly, 0.9, 0.5, "", edge=SUM, fill="white", lw=2.3)
    ax.text(23.6, ly, "parent quantity", va="center", fontsize=8.5, color=INK)
    lx, ly2 = 11.3, 0.25
    items = [(PHYS, "physical dependence", "-"), (STATE, "stored-state cycle", "-"),
             (SUM, "designer revision", (0, (4, 3)))]
    for i, (c, s_, ls) in enumerate(items):
        x = lx + i * 4.9
        ax.plot([x, x + 0.8], [ly2, ly2], color=c, lw=2, ls=ls)
        ax.text(x + 0.95, ly2, s_, va="center", fontsize=8.5, color=INK)
    ax.text(11.3, -0.55, "Node roles belong to this formulation and change when the problem is reformulated:\n"
            "a reduced model may vary Ron directly; bias current may be set directly or follow from a bias design.",
            va="center", ha="left", fontsize=8.0, color=MUTED, style="italic")
    finish(fig, "requirement_vs_network")


# --------------------------------------------------------------------------- Figure 2

def sampling_cycle() -> None:
    import numpy as np
    sys.path.insert(0, str(ROOT / "scripts"))
    import draw_diagrams as dd  # noqa: E402  same schematic symbols as Figure 9 and the testbench sketches
    plt.rcParams.update(RC)     # draw_diagrams sets its own rcParams on import
    fig = plt.figure(figsize=(13.5, 5.0))
    ax = fig.add_axes([0.0, 0.08, 0.36, 0.84])
    ax.set_xlim(-1.05, 6.15); ax.set_ylim(-2.3, 2.3); ax.set_aspect("equal"); ax.axis("off")
    yc = 0.3
    # driver: unity-gain follower with its feedback path
    dd.pin(ax, -0.45, yc + 0.275, color=REQ)
    dd.wire(ax, (-0.36, yc + 0.275), (0.2, yc + 0.275))
    dd.text(ax, -0.45, yc + 0.62, "input u", size=9.5, color=REQ)
    _, _, out = dd.opamp(ax, 0.2, yc)
    xo = 1.75
    dd.wire(ax, out, (xo, yc))
    dd.dot(ax, xo, yc)
    dd.wire(ax, (xo, yc), (xo, yc - 0.92), (0.05, yc - 0.92), (0.05, yc - 0.275), (0.2, yc - 0.275))
    dd.text(ax, 0.85, yc - 1.38, "closed-loop driver\n(unity-gain follower)", size=9.5)
    # sampling switch, driven by the clock
    dd.wire(ax, (xo, yc), (2.0, yc))
    dd.switch_h(ax, 2.0, 2.9, yc)
    dd.text(ax, 2.45, yc + 0.75, "sampling switch\n(clock φ)", size=9.5, color=STATE)
    # sampling capacitor and the held node
    xs = 3.5
    dd.wire(ax, (2.9, yc), (xs, yc))
    dd.dot(ax, xs, yc)
    dd.text(ax, xs, yc + 0.3, "V(Cs)", size=9.5, color=PHYS)
    dd.wire(ax, (xs, yc), (xs, yc - 0.55))
    dd.cap_v(ax, xs, yc - 0.6)
    dd.wire(ax, (xs, yc - 0.65), (xs, yc - 1.0))
    dd.gnd(ax, xs, yc - 1.0)
    dd.text(ax, xs - 0.36, yc - 0.6, "Cs = 1 pF", size=9.5, ha="right")
    # high-impedance downstream use (not modelled)
    dd.wire(ax, (xs, yc), (4.35, yc))
    ax.add_patch(FancyBboxPatch((4.35, yc - 0.5), 1.7, 1.0, boxstyle="round,pad=0.02,rounding_size=0.12",
                                facecolor="white", edgecolor=MUTED, lw=1.3, ls="--", zorder=3))
    dd.text(ax, 5.2, yc + 0.13, "downstream use", size=9.0)
    dd.text(ax, 5.2, yc - 0.2, "high-Z, not modelled", size=7.6, color=MUTED, style="italic")

    # ---- time-domain half: one shared time axis, three layers
    T = 100.0
    t = np.linspace(0, 200, 4001)
    phi = ((t % T) < 40).astype(float)
    u = np.where(t < 41, 0.7, np.where(t < 141, 1.1, 0.8))
    v = np.zeros_like(t); vh = 0.75
    for i, ti in enumerate(t):
        k = int(ti // T); ph = ti - k * T
        tgt = 0.7 if k == 0 else (1.1 if k == 1 else 0.8)
        start = vh if k == 0 else (0.7 if k == 1 else 1.1)
        v[i] = tgt + (start - tgt) * np.exp(-ph / 4.0) if ph < 40 else tgt - 0.012
    x0, w = 0.47, 0.51
    a1 = fig.add_axes([x0, 0.74, w, 0.16])
    a2 = fig.add_axes([x0, 0.36, w, 0.36], sharex=a1)
    a3 = fig.add_axes([x0, 0.13, w, 0.20], sharex=a1)
    win_e = [(k * T + 50, k * T + 60) for k in range(2)]
    win_l = [((k + 1) * T - 6, (k + 1) * T - 1) for k in range(2)]
    for a in (a1, a2, a3):
        for s_ in ("top", "right", "left"):
            a.spines[s_].set_visible(False)
        a.set_yticks([])
        for lo, hi in win_e + win_l:
            a.axvspan(lo, hi, color=SUM, alpha=0.13, lw=0)
    # 1 clock
    a1.plot(t, phi, color=STATE, lw=1.7)
    a1.set_ylim(-0.25, 1.9)
    for k in range(2):
        a1.text(k * T + 20, 1.45, "switch closed: acquire 40 ns", ha="center", va="center", fontsize=8.6)
        a1.text(k * T + 70, 0.42, "switch open: hold 60 ns", ha="center", va="center", fontsize=8.6)
    fig.text(x0 - 0.012, 0.82, "1  clock φ", ha="right", va="center", fontsize=9.5, color=STATE, weight="bold")
    # 2 voltages
    a2.plot(t, u, color=REQ, lw=1.4, ls="--")
    a2.plot(t, v, color=PHYS, lw=2.0)
    a2.set_ylim(0.6, 1.2)
    a2.text(203, 0.80, "input u", fontsize=8.6, color=REQ, va="center")
    a2.text(203, 1.08, "V(Cs)", fontsize=8.6, color=PHYS, va="center")
    a2.annotate("previous held voltage is\nthe starting point", xy=(101, 0.70), xytext=(108, 0.63), fontsize=8.3,
                va="bottom", color=PHYS, arrowprops=dict(arrowstyle="-|>", color=PHYS, lw=1))
    fig.text(x0 - 0.012, 0.54, "2  voltages", ha="right", va="center", fontsize=9.5, color=INK, weight="bold")
    # 3 measurement / timing layer
    a3.set_ylim(0, 1)
    for lo, hi in win_e:
        a3.text((lo + hi) / 2, 0.62, "E", ha="center", va="center", fontsize=11, color=SUM, weight="bold")
    for lo, hi in win_l:
        a3.text((lo + hi) / 2, 0.62, "L", ha="center", va="center", fontsize=11, color=SUM, weight="bold")
    for k in range(2):
        a3.plot([k * T + 40 - 0.5] * 2, [0.42, 0.82], color=INK, lw=1.4)
        a3.text(k * T + 39, 0.62, "pre-opening\nread ", ha="right", va="center", fontsize=7.6, color=INK)
        a3.annotate("", xy=(k * T + 41, 0.35), xytext=(k * T + 41, 0.02),
                    arrowprops=dict(arrowstyle="-|>", color=REQ, lw=1.2))
    a3.text(43, 0.12, "next input level, 1 ns after opening", fontsize=7.8, color=REQ, va="center")
    fig.text(x0 + w / 2, 0.035, "E = early read, 10–20 ns after opening (step at opening, first coupling of the next input)"
             "     L = late read, 6–1 ns before the next acquisition (adds hold droop and feedthrough)",
             ha="center", va="center", fontsize=8.2, color=SUM)
    fig.text(x0 - 0.012, 0.23, "3  where the\nresidual is read", ha="right", va="center", fontsize=9.5, color=SUM,
             weight="bold")
    a3.set_xlim(-3, 200)
    a3.set_xlabel("time (ns)", fontsize=9, labelpad=1)
    a1.tick_params(labelbottom=False, bottom=False)
    a2.tick_params(labelbottom=False, bottom=False)
    a2.text(0, 1.2, "illustrative waveforms, not simulation", fontsize=7.6, color=MUTED, style="italic", va="top")
    finish(fig, "sampling_cycle")


# --------------------------------------------------------------------------- Figure 3

def working_checks_cycle() -> None:
    """Where the deterministic working checks of Table 2 act in one cycle, and the separate random-noise lane."""
    import numpy as np
    plt.rcParams.update(RC)
    fig = plt.figure(figsize=(13.5, 7.4))
    t = np.linspace(-12, 112, 4001)
    phi = ((t >= 0) & (t < 40) | (t >= 100)).astype(float)
    u = np.where(t < 1, 0.75, 1.05)
    u = np.where(t >= 41, 0.85, u)
    vt, vp = 1.05, 0.75
    v = np.where(t < 0, vp, vt + (vp - vt) * np.exp(-np.clip(t, 0, None) / 4.0))
    v = np.where(t >= 40, vt - 0.012, v)
    v = np.where(t >= 100, (vt - 0.012) + (0.85 - vt + 0.012) * (1 - np.exp(-(t - 100) / 4.0)), v)
    rng = np.random.default_rng(3)
    nz = np.convolve(rng.normal(0, 1, t.size), np.ones(15) / 15, mode="same") * 0.032
    ramp = np.clip((t - 38.8) / 1.2, 0, 1)
    nz = nz + (0.028 - float(np.interp(40, t, nz))) * ramp   # make the frozen value visible
    frozen = 0.028
    vn = np.where((t >= 0) & (t < 40), nz, np.where((t >= 40) & (t < 100), frozen, np.nan))
    x0, w = 0.20, 0.62
    a1 = fig.add_axes([x0, 0.86, w, 0.09])
    a2 = fig.add_axes([x0, 0.62, w, 0.22], sharex=a1)
    a3 = fig.add_axes([x0, 0.25, w, 0.35], sharex=a1)
    a4 = fig.add_axes([x0, 0.06, w, 0.16], sharex=a1)
    win = [(50, 60), (94, 99)]
    for a in (a1, a2, a3, a4):
        for s_ in ("top", "right", "left"):
            a.spines[s_].set_visible(False)
        a.set_yticks([])
        for lo, hi in win:
            a.axvspan(lo, hi, color=SUM, alpha=0.10, lw=0)
        a.axvline(40, color=MUTED, lw=0.8, ls=":")
        a.axvline(0, color=MUTED, lw=0.8, ls=":")
        a.axvline(100, color=MUTED, lw=0.8, ls=":")
    # 1 clock
    a1.plot(t, phi, color=STATE, lw=1.7)
    a1.set_ylim(-0.25, 1.9)
    a1.text(20, 1.45, "switch closed: acquire 40 ns", ha="center", va="center", fontsize=8.6)
    a1.text(70, 0.42, "switch open: hold 60 ns", ha="center", va="center", fontsize=8.6)
    fig.text(x0 - 0.012, 0.905, "1  clock φ", ha="right", va="center", fontsize=9.5, color=STATE, weight="bold")
    # 2 voltages
    a2.plot(t, u, color=REQ, lw=1.4, ls="--")
    a2.plot(t, v, color=PHYS, lw=2.0)
    a2.set_ylim(0.66, 1.14)
    a2.text(113, 0.85, "input u", fontsize=8.6, color=REQ, va="center")
    a2.text(113, 1.03, "V(Cs)", fontsize=8.6, color=PHYS, va="center")
    a2.text(-11, 0.80, "previous\nheld voltage", fontsize=8.0, color=PHYS, va="bottom")
    a2.text(52, 1.06, "E", fontsize=10, color=SUM, weight="bold", ha="left")
    a2.text(94, 1.06, "L", fontsize=10, color=SUM, weight="bold", ha="left")
    a2.text(-11, 1.14, "illustrative waveforms, not simulation", fontsize=7.6, color=MUTED, style="italic", va="top")
    fig.text(x0 - 0.012, 0.73, "2  voltages", ha="right", va="center", fontsize=9.5, color=INK, weight="bold")
    # 3 deterministic working checks
    a3.set_ylim(0, 5.2)
    rows = [
        (4.5, 0, 40, "acquisition left over, previous-sample history", "0.10 mV", "from closing through acquisition"),
        (3.5, 34, 40, "driver static tracking", "0.15 mV", "evaluated just before opening"),
        (2.5, 38.5, 46, "level-dependent step at opening", "0.15 mV", "switch opening, entry into hold"),
        (1.5, 50, 99, "hold droop, feedthrough of the next input", "0.10 mV", "from the early to the late read"),
    ]
    for y, lo, hi, name, alloc, when in rows:
        a3.add_patch(Rectangle((lo, y - 0.22), hi - lo, 0.44, facecolor=PHYS, alpha=0.75, lw=0))
        lx = hi + 1.5 if hi < 60 else lo - 1.5
        ha = "left" if hi < 60 else "right"
        a3.text(lx, y + 0.06, f"{name}   {alloc}", ha=ha, va="bottom", fontsize=8.6, color=INK)
        a3.text(lx, y - 0.06, when, ha=ha, va="top", fontsize=7.8, color=MUTED, style="italic")
    a3.text(113, 0.55, "reserve 0.086 mV:\nPVT spread, model and\nnumerical uncertainty;\nnot tied to a time",
            fontsize=8.0, color=INK, va="center", ha="left",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor=MUTED, ls="--", lw=1.0))
    a3.text(-11, 0.45, "magnitudes sum to 0.586 mV = 1 VLSB (conservative). The checks share causes; they are not\n"
            "independent physical components. Only the parent residual, read at E and L, is pass/fail.",
            fontsize=7.8, color=SUM, va="center")
    fig.text(x0 - 0.012, 0.43, "3  deterministic\nworking checks\n(Table 2)", ha="right", va="center", fontsize=9.5,
             color=PHYS, weight="bold")
    # 4 random sampled noise, separate lane
    a4.plot(t, vn, color=STATE, lw=1.1)
    a4.axhline(0, color=MUTED, lw=0.6)
    a4.plot([40], [frozen], "o", color=STATE, ms=5)
    a4.set_ylim(-0.075, 0.075)
    a4.text(20, 0.062, "switch and driver noise move V(Cs) while it tracks", ha="center", fontsize=8.0, color=STATE)
    a4.text(42, frozen + 0.012, "opening freezes one random value", fontsize=8.0, color=STATE, va="bottom")
    a4.text(70, -0.062, "sample uncertainty carried through the hold; evaluated as RMS (≤ 146 µV),\nnot added to the deterministic sum",
            ha="center", va="bottom", fontsize=8.0, color=STATE)
    a4.set_xlim(-12, 112)
    a4.set_xlabel("time (ns)", fontsize=9, labelpad=1)
    for a in (a1, a2, a3):
        a.tick_params(labelbottom=False, bottom=False)
    fig.text(x0 - 0.012, 0.14, "4  random sampled\nnoise (separate)", ha="right", va="center", fontsize=9.5,
             color=STATE, weight="bold")
    fig.text(x0 - 0.012, 0.075, "first cut: kT/C only", ha="right", va="center", fontsize=7.8, color=MUTED,
             style="italic")
    finish(fig, "working_checks_cycle")


if __name__ == "__main__":
    requirement_vs_network()
    sampling_cycle()
    working_checks_cycle()

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
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

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
    """Where in one sampling waveform each deterministic working check of Table 2 is defined, as the voltage
    difference it bounds; random sampled noise as uncertainty on V(Cs). Offsets are exaggerated, not to scale."""
    import numpy as np
    plt.rcParams.update(RC)
    fig = plt.figure(figsize=(13.5, 7.0))
    t = np.linspace(-12, 112, 6201)
    phi = ((t >= 0) & (t < 40) | (t >= 100)).astype(float)
    # zoomed view around the target level; offsets are exaggerated for legibility
    d_trk, d_acq, d_step, d_hold = 0.15, 0.10, 0.15, 0.10
    vin = np.where(t < 41, 0.0, -3.0)                              # next input level leaves the view 1 ns after opening
    vdrv = np.where(t < 41, -d_trk, -d_trk + (-3.0 + d_trk) * (1 - np.exp(-(t - 41) / 1.5)))
    v_pre = -d_trk - d_acq
    vcs = np.where(t < 0, -3.0, -d_trk - 1.4 * np.exp(-np.clip(t, 0, None) / 3.0)
                   - d_acq * np.exp(-(t - 40) / 40.0))
    v_e = v_pre - d_step
    v_l = v_e - d_hold
    hold = (t >= 40) & (t < 100)
    # hold: the step settles by E (55 ns), then droop and feedthrough carry V(Cs) down to L (96.5 ns)
    th = np.clip((t - 55) / (96.5 - 55), 0, None)
    vcs = np.where(hold, v_pre - d_step * (1 - np.exp(-(t - 40) / 1.2)) - d_hold * th, vcs)
    vcs = np.where(t >= 100, -3.0, vcs)
    x0, w = 0.07, 0.66
    a1 = fig.add_axes([x0, 0.86, w, 0.09])
    a2 = fig.add_axes([x0, 0.13, w, 0.71], sharex=a1)
    win = [(50, 60), (94, 99)]
    for a in (a1, a2):
        for s_ in ("top", "right", "left"):
            a.spines[s_].set_visible(False)
        a.set_yticks([])
        for lo, hi in win:
            a.axvspan(lo, hi, color=SUM, alpha=0.10, lw=0)
        for xv in (0, 40, 100):
            a.axvline(xv, color=MUTED, lw=0.8, ls=":")
    # 1 clock
    a1.plot(t, phi, color=STATE, lw=1.7)
    a1.set_ylim(-0.25, 1.9)
    a1.text(20, 1.45, "switch closed: acquire 40 ns", ha="center", va="center", fontsize=8.6)
    a1.text(70, 0.42, "switch open: hold 60 ns", ha="center", va="center", fontsize=8.6)
    a1.text(40, 1.55, "opening", ha="center", va="bottom", fontsize=8.0, color=MUTED)
    a1.text(-11.5, 1.45, "clock φ", ha="left", va="center", fontsize=9.0, color=STATE, weight="bold")
    # 2 voltages near the target level
    lo_y, hi_y = -0.86, 0.24
    a2.set_ylim(lo_y, hi_y)
    a2.set_xlim(-12, 112)
    sig = 0.03
    track = (t >= 0) & (t < 40)
    band_t = track & (vcs > lo_y)
    a2.fill_between(t[band_t], vcs[band_t] - sig, vcs[band_t] + sig, color=STATE, alpha=0.14, lw=0, zorder=1)
    a2.fill_between(t[hold], vcs[hold] - sig, vcs[hold] + sig, facecolor="none", edgecolor=STATE, alpha=0.45,
                    hatch="////", lw=0, zorder=1)
    a2.plot(t, vin, color=REQ, lw=1.5, ls="--", zorder=3)
    a2.plot(t, vdrv, color=KNOB, lw=1.5, ls="-.", zorder=3)
    a2.plot(t, vcs, color=PHYS, lw=2.2, zorder=4)
    a2.text(-11.5, 0.025, "Vin", fontsize=9.5, color=REQ, va="bottom", weight="bold")
    a2.text(-11.5, -d_trk + 0.025, "Vdrv", fontsize=9.5, color=KNOB, va="bottom", weight="bold")
    a2.text(101, v_l - 0.02, "V(Cs)", fontsize=9.5, color=PHYS, va="top", weight="bold")
    a2.annotate("previous held voltage\n(off scale): start of\nthis acquisition", xy=(1.6, -0.80), xytext=(5.5, -0.80),
                fontsize=8.0, color=PHYS, va="center", arrowprops=dict(arrowstyle="-|>", color=PHYS, lw=1))
    a2.annotate("next input level, 1 ns after\nopening (off scale)", xy=(41.4, -0.80), xytext=(62, -0.80),
                fontsize=8.0, color=REQ, va="center", arrowprops=dict(arrowstyle="-|>", color=REQ, lw=1))
    a2.text(55, hi_y - 0.02, "E", fontsize=11, color=SUM, weight="bold", ha="center", va="top")
    a2.text(96.5, hi_y - 0.02, "L", fontsize=11, color=SUM, weight="bold", ha="center", va="top")
    a2.text(96.5, hi_y - 0.10, "early / late read", fontsize=7.6, color=SUM, ha="right", va="top")

    def diff(x, y_a, y_b, label, alloc, where, tx, ty, ha="left"):
        a2.annotate("", xy=(x, y_b), xytext=(x, y_a),
                    arrowprops=dict(arrowstyle="<|-|>", color=INK, lw=1.4, mutation_scale=9, shrinkA=0, shrinkB=0),
                    zorder=6)
        a2.text(tx, ty, f"{label}  {alloc}", ha=ha, va="bottom", fontsize=8.8, color=INK, weight="bold", zorder=6)
        a2.text(tx, ty - 0.008, where, ha=ha, va="top", fontsize=7.9, color=INK, style="italic", zorder=6)

    # reference levels carried forward as thin dotted lines
    a2.plot([37.6, 58.5], [v_pre, v_pre], color=INK, lw=0.8, ls=(0, (1, 2)), zorder=5)
    a2.plot([55, 99], [v_e, v_e], color=INK, lw=0.8, ls=(0, (1, 2)), zorder=5)
    diff(34.5, 0.0, -d_trk, "driver static tracking", "0.15 mV", "Vin − Vdrv just before opening",
         33.3, -0.07, ha="right")
    diff(38.2, -d_trk, v_pre, "acquisition left over,\nprevious-sample history", "0.10 mV",
         "Vdrv − V(Cs) left just before opening", 37.0, -0.52, ha="right")
    a2.plot([37.1, 38.2], [-0.46, v_pre - 0.045], color=INK, lw=0.6, zorder=6)
    diff(58.5, v_pre, v_e, "level-dependent step at opening", "0.15 mV",
         "change in V(Cs) from just before opening to E\n(includes first coupling of the next input)",
         60.0, -0.06)
    a2.plot([59.9, 58.6], [-0.065, v_pre - 0.01], color=INK, lw=0.6, zorder=6)
    diff(97.5, v_e, v_l, "hold droop, feedthrough\nof the next input", "0.10 mV",
         "change in V(Cs) from E to L", 96.2, -0.30, ha="right")
    a2.plot([96.3, 97.4], [-0.335, v_e - 0.01], color=INK, lw=0.6, zorder=6)
    # random sampled noise on V(Cs)
    a2.annotate("random noise: spread of\nV(Cs) while it tracks", xy=(6, float(np.interp(6, t, vcs)) - sig),
                xytext=(9, -0.66), fontsize=8.0, color=STATE, ha="left", va="top",
                arrowprops=dict(arrowstyle="-|>", color=STATE, lw=0.9, shrinkA=1, shrinkB=1))
    a2.plot([40], [v_pre + 0.018], "o", color=STATE, ms=5.5, zorder=7, mec="white", mew=0.8)
    a2.text(42.8, v_pre - 0.065, "opening freezes\none random value", fontsize=8.0, color=STATE, ha="left",
            va="center")
    a2.annotate("same sampled spread carried\nwith the held value", xy=(70, -0.475), xytext=(62, -0.53),
                fontsize=8.0, color=STATE, ha="left", va="top",
                arrowprops=dict(arrowstyle="-|>", color=STATE, lw=0.9, shrinkA=1, shrinkB=1))
    a2.set_xlabel("time (ns)", fontsize=9, labelpad=1)
    a1.tick_params(labelbottom=False, bottom=False)
    a2.text(-11.5, lo_y - 0.115, "Illustrative, not simulation. Zoomed view near the target level; offsets exaggerated and not "
            "to scale.\nArrows mark the voltage difference each deterministic check bounds; the time axis only locates where "
            "it is evaluated.", transform=a2.transData, fontsize=7.8, color=MUTED, style="italic", va="top")
    # side notes, outside the waveform
    nx = x0 + w + 0.02
    fig.text(nx, 0.80, "Deterministic working checks (Table 2)\n"
             "four voltage differences on the waveform;\n"
             "magnitudes sum with the reserve to\n0.586 mV = 1 VLSB (conservative).\n"
             "They share causes and are not\nindependent physical components.\n"
             "Only the parent residual, read at\nE and L, is pass/fail.",
             fontsize=8.3, color=INK, va="top", ha="left", linespacing=1.3,
             bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor=INK, lw=1.0))
    fig.text(nx, 0.52, "Reserve 0.086 mV\n"
             "budget margin for PVT, model and\nnumerical uncertainty; not a physical,\n"
             "time-localized component, so it is\nnot drawn on the waveform.",
             fontsize=8.3, color=INK, va="top", ha="left", linespacing=1.3,
             bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor=MUTED, ls="--", lw=1.0))
    fig.text(nx, 0.30, "Random sampled noise (separate budget)\n"
             "shaded: spread of V(Cs) while tracking;\nhatched: the frozen sample carried\nthrough the hold.\n"
             "First cut: kT/C only. Final: RMS\nnoise ≤ 146 µV, evaluated separately,\n"
             "never added linearly to the\ndeterministic checks.",
             fontsize=8.3, color=STATE, va="top", ha="left", linespacing=1.3,
             bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor=STATE, lw=1.0))
    finish(fig, "working_checks_cycle")


if __name__ == "__main__":
    requirement_vs_network()
    sampling_cycle()
    working_checks_cycle()

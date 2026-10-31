#!/usr/bin/env python3
"""Explanatory diagrams of the rebuilt notebook (restart), drawn with Matplotlib primitives.

    uv run python scripts/draw_restart_diagrams.py

Writes assets/diagrams/requirement_vs_network.svg (Figure 1), sampling_cycle.svg
(Figure 2) and budget_phases.svg (Figure 3). These are explanatory drawings, not
simulation results. Quantities named in them are those of
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
KNOB = "#555555"     # design choices
PHYS = "#b4532a"     # physical quantities
STATE = "#7a4fb0"    # stored state / cycle highlight
SUM = "#1f7a4d"      # signed sum (parent quantity)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "svg.hashsalt": "restart",
                     "svg.fonttype": "path"})


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
    ax.set_ylim(0, 15.2)
    ax.axis("off")

    # ---------------- left: requirement hierarchy (a tree)
    ax.text(4.6, 14.75, "Requirement hierarchy (a tree)", ha="center", fontsize=12, weight="bold", color=REQ)
    W = 9.0
    box(ax, 4.6, 13.55, W, 1.05, "Downstream use\na high-impedance consumer reads the held voltage", edge=REQ, size=9)
    box(ax, 4.6, 12.0, W, 1.05, "Parent function\nacquire in 40 ns, hold for 60 ns; input 0.6–1.2 V", edge=REQ)
    box(ax, 4.6, 10.15, W, 1.65, "Parent requirement\nheld-sample residual within ±1 LSB (0.586 mV)\nafter two-point correction, any previous\nsample, declared PVT set", edge=REQ, lw=2.2)
    for y0, y1 in ((13.0, 12.55), (11.45, 11.0)):
        arr(ax, (4.6, y0), (4.6, y1), color=REQ, shrinkA=0, shrinkB=0)
    leaves = [
        ("static\ntracking", 0.95, "S"),
        ("turn-off\nstep", 2.85, "P"),
        ("acquisition,\nhistory", 4.75, "A"),
        ("hold drift,\nfeedthrough", 6.65, "H"),
        ("reserve", 8.5, "R"),
    ]
    leaf_y = 7.6
    for label, x, b in leaves:
        box(ax, x, leaf_y, 1.75, 1.0, label, edge=REQ, size=8.0)
        if b != "R":
            ax.text(x + 0.8, leaf_y + 0.48, b, ha="center", va="center", fontsize=8, color="white", weight="bold",
                    zorder=6, bbox=dict(boxstyle="circle,pad=0.18", fc=REQ, ec="none"))
        arr(ax, (4.6, 9.32), (x, leaf_y + 0.5), color=REQ, shrinkA=0, shrinkB=0, lw=1.0)
    ax.text(4.6, 8.55, "provisional allocations (deterministic)", ha="center", fontsize=8.5, color=REQ, style="italic")
    box(ax, 4.6, 5.95, 7.4, 0.75, "random noise (kT/C, driver): separate budget", edge=MUTED, size=8.5, color=MUTED,
        style="round,pad=0.02,rounding_size=0.08")
    ax.text(4.6, 4.65, "Each provisional allocation guides design checks.\n"
            "The physical effects on the right share causes.\n"
            "Final measured components are defined in §3.5.", ha="center", va="center",
            fontsize=9, color=INK, style="italic")

    # ---------------- right: physical / design dependency network
    ax.text(19.6, 14.75, "Physical and design dependencies (a network with cycles)", ha="center", fontsize=12,
            weight="bold", color=PHYS)
    K, P = (2.6, 1.05), (2.9, 1.05)
    nodes = {
        # design choices
        "bias": (12.6, 13.0, "driver bias\ncurrent, power", K, "knob"),
        "comp": (12.6, 11.0, "loop gain,\ncompensation", K, "knob"),
        "W": (12.6, 8.4, "switch type,\nwidth", K, "knob"),
        "clk": (12.6, 5.5, "clock edge,\nsequence", K, "knob"),
        "Cs": (12.6, 3.0, "Cs", K, "knob"),
        # circuit quantities
        "Zout": (16.6, 12.0, "driver output\nimpedance Zout(f)", P, "phys"),
        "Ron": (16.6, 9.4, "switch Ron(V)", P, "phys"),
        "q": (16.6, 7.0, "channel charge q(V),\nswitch capacitance", P, "phys"),
        "pwr": (16.6, 2.2, "area,\nkT/C noise", P, "phys"),
        "kick": (19.6, 4.0, "charge kickback\nwhen the switch closes", (3.2, 1.05), "phys"),
        # error components
        "stat": (21.1, 13.6, "static tracking\nerror", P, "comp"),
        "acq": (21.1, 11.2, "acquisition error\nat 40 ns", P, "comp"),
        "off": (21.1, 6.2, "turn-off step", P, "comp"),
        "hold": (21.1, 8.65, "hold drift,\nfeedthrough", P, "comp"),
        # parent quantity and stored state
        "sum": (25.6, 9.9, "held-sample\nerror\n(signed sum)", (2.4, 1.6), "sum"),
        "prev": (25.6, 4.0, "previous held\nvoltage Vprev", P, "state"),
    }
    style = {"knob": (KNOB, "#f2f2f2", 1.4), "phys": (PHYS, "white", 1.4), "comp": (PHYS, "#fbf1ec", 1.4),
             "sum": (SUM, "white", 2.3), "state": (STATE, "white", 1.8)}
    for k, (x, y, s_, (w, h), kd) in nodes.items():
        ec, fc, lw = style[kd]
        box(ax, x, y, w, h, s_, edge=ec, fill=fc, size=8.8, lw=lw)
    badges = {"stat": "S", "off": "P", "acq": "A", "hold": "H"}
    for k, b in badges.items():
        x, y, _, (w, h), _ = nodes[k]
        ax.text(x + w / 2 - 0.05, y + h / 2 - 0.02, b, ha="center", va="center", fontsize=8, color="white",
                weight="bold", zorder=6, bbox=dict(boxstyle="circle,pad=0.18", fc=REQ, ec="none"))

    def clip(k, toward):
        x, y, _, (w, h), _ = nodes[k]
        dx, dy = toward[0] - x, toward[1] - y
        t = min((w / 2 + 0.08) / abs(dx) if dx else 1e9, (h / 2 + 0.08) / abs(dy) if dy else 1e9)
        return (x + dx * t, y + dy * t)

    def e(a, b, color=PHYS, lw=1.3, rad=0.0, ls="-", style_="-|>"):
        pa, pb = nodes[a][:2], nodes[b][:2]
        ax.add_patch(FancyArrowPatch(clip(a, pb), clip(b, pa), arrowstyle=style_, mutation_scale=10, color=color,
                                     lw=lw, ls=ls, connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0, zorder=2))

    for a, b, rad in (("bias", "Zout", 0), ("comp", "Zout", 0), ("comp", "stat", -0.12), ("bias", "stat", -0.1),
                      ("W", "Ron", 0), ("W", "q", 0), ("clk", "off", 0.0), ("q", "off", 0), ("Zout", "off", 0.0),
                      ("Ron", "acq", 0), ("Zout", "acq", 0), ("q", "hold", 0), ("q", "kick", 0),
                      ("Cs", "kick", 0), ("Cs", "pwr", 0), ("Cs", "off", 0.0),
                      ("stat", "sum", 0), ("off", "sum", 0.12), ("hold", "sum", 0.0)):
        e(a, b, rad=rad)
    # the switch and Cs load the driver loop during acquisition
    e("Ron", "Zout", rad=0.0, style_="<|-|>")
    ax.text(16.45, 10.7, "Ron, Cs load\nthe loop", fontsize=7.6, color=PHYS, style="italic", va="center", ha="right")
    # stored-state cycle
    for a, b, rad in (("acq", "sum", 0), ("sum", "prev", 0), ("prev", "kick", 0), ("kick", "acq", -0.35)):
        e(a, b, color=STATE, lw=2.2, rad=rad)
    ax.text(27.2, 7.0, "sample k sets\nthe start of\nsample k+1", ha="center", fontsize=8.3, color=STATE,
            style="italic")
    # designer revision
    ax.add_patch(FancyArrowPatch((25.6, 10.75), (12.6, 13.6), arrowstyle="-|>", mutation_scale=10, color=SUM, lw=1.3,
                                 ls=(0, (4, 3)), connectionstyle="arc3,rad=0.32", zorder=2))
    ax.plot([11.05, 11.05], [2.6, 13.4], color=SUM, lw=1.2, ls=(0, (4, 3)))
    ax.text(18.6, 15.0 - 0.95, "", fontsize=1)
    ax.text(10.85, 8.0, "revise", rotation=90, ha="center", va="center", fontsize=8.5, color=SUM, style="italic")

    # legend
    lx, ly = 11.2, 0.55
    items = [(KNOB, "design choice", "-"), (PHYS, "physical dependence", "-"), (STATE, "stored-state cycle", "-"),
             (SUM, "designer revision", (0, (4, 3)))]
    for i, (c, s_, ls) in enumerate(items):
        x = lx + i * 4.3
        ax.plot([x, x + 0.8], [ly, ly], color=c, lw=2, ls=ls)
        ax.text(x + 0.95, ly, s_, va="center", fontsize=8.5, color=INK)
    finish(fig, "requirement_vs_network")




# --------------------------------------------------------------------------- Figure 2

def sampling_cycle() -> None:
    import numpy as np
    from matplotlib.patches import Polygon
    fig = plt.figure(figsize=(13.5, 4.3))
    ax = fig.add_axes([0.0, 0.0, 0.40, 1.0])
    ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.axis("off")
    # driver (unity-gain follower)
    ax.add_patch(Polygon([[1.6, 2.2], [1.6, 4.2], [3.4, 3.2]], closed=True, fc="white", ec=INK, lw=1.6))
    ax.text(1.85, 3.75, "+", fontsize=11); ax.text(1.85, 2.45, "−", fontsize=12)
    ax.plot([0.4, 1.6], [3.7, 3.7], color=INK, lw=1.6)
    ax.text(0.35, 4.0, "input u[k]", fontsize=9.5)
    ax.plot([3.4, 4.6], [3.2, 3.2], color=INK, lw=1.6)
    ax.plot([3.9, 3.9, 1.2, 1.2, 1.6], [3.2, 1.4, 1.4, 2.7, 2.7], color=INK, lw=1.4)
    ax.text(2.3, 1.05, "closed-loop driver", ha="center", fontsize=9.5)
    # switch
    ax.plot([4.6, 5.6], [3.2, 3.75], color=INK, lw=1.8)
    ax.plot([5.8, 6.6], [3.2, 3.2], color=INK, lw=1.6)
    ax.plot(5.75, 3.2, "o", ms=5, mfc="white", mec=INK)
    ax.text(5.2, 4.25, "sampling switch\n(clock φ)", ha="center", fontsize=9.5)
    # Cs
    ax.plot([6.6, 6.6], [3.2, 2.45], color=INK, lw=1.6)
    ax.plot([6.15, 7.05], [2.45, 2.45], color=INK, lw=2.2); ax.plot([6.15, 7.05], [2.2, 2.2], color=INK, lw=2.2)
    ax.plot([6.6, 6.6], [2.2, 1.6], color=INK, lw=1.6)
    ax.plot([6.3, 6.9], [1.6, 1.6], color=INK, lw=1.6); ax.plot([6.42, 6.78], [1.45, 1.45], color=INK, lw=1.4)
    ax.text(7.2, 2.3, "Cs = 1 pF", fontsize=9.5)
    ax.plot([6.6, 8.4], [3.2, 3.2], color=INK, lw=1.6)
    ax.annotate("", xy=(9.4, 3.2), xytext=(8.4, 3.2), arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.4))
    ax.text(8.9, 3.55, "held voltage\nto high-Z use", ha="center", fontsize=9.5)
    # timing
    tx = fig.add_axes([0.45, 0.14, 0.53, 0.78])
    T = 100.0
    t = np.linspace(0, 200, 4001)
    phi = ((t % T) < 40).astype(float)
    u = np.where(t < 41, 0.7, np.where(t < 141, 1.1, 0.8))
    v = np.zeros_like(t); vh = 0.75
    for i, ti in enumerate(t):
        k = int(ti // T); ph = ti - k * T
        tgt = 0.7 if k == 0 else (1.1 if k == 1 else 0.8)
        start = vh if k == 0 else (0.7 if k == 1 else 1.1)
        if ph < 40:
            v[i] = tgt + (start - tgt) * np.exp(-ph / 4.0)
        else:
            v[i] = tgt - 0.012
    tx.plot(t, 2.4 + 0.5 * phi, color=STATE, lw=1.6)
    tx.text(-3, 2.65, "φ", ha="right", va="center", fontsize=11, color=STATE)
    tx.plot(t, u, color=REQ, lw=1.4, ls="--", label="input u")
    tx.plot(t, v, color=PHYS, lw=2.0, label="V(Cs)")
    for k in range(2):
        to = k * T + 40
        tx.axvspan(to + 10, to + 20, color=SUM, alpha=0.15, lw=0)
        tx.axvspan((k + 1) * T - 6, (k + 1) * T - 1, color=SUM, alpha=0.15, lw=0)
        tx.text(to + 15, 1.32, "E", ha="center", fontsize=9, color=SUM)
        tx.text((k + 1) * T - 3.5, 1.32, "L", ha="center", fontsize=9, color=SUM)
        tx.text(k * T + 20, 3.05, "acquire 40 ns", ha="center", fontsize=9)
        tx.text(k * T + 70, 3.05, "hold 60 ns", ha="center", fontsize=9)
    tx.text(50, 2.12, "E (10–20 ns after opening): the held sample after\nthe opening step and first next-input coupling",
            ha="left", va="top", fontsize=8.3, color=SUM)
    tx.text(199, 1.82, "L (6–1 ns before the next acquisition):\nadds droop and next-input feedthrough\naccumulated over the hold",
            ha="right", va="top", fontsize=8.3, color=SUM)
    tx.annotate("next input applied\n1 ns after opening", xy=(141, 0.95), xytext=(150, 0.48), fontsize=8.5,
                arrowprops=dict(arrowstyle="-|>", color=REQ, lw=1), color=REQ)
    tx.annotate("previous held voltage\nis the starting point", xy=(101, 1.06), xytext=(55, 0.43), fontsize=8.5,
                arrowprops=dict(arrowstyle="-|>", color=PHYS, lw=1), color=PHYS)
    tx.set_ylim(0.35, 3.25); tx.set_xlim(-5, 205)
    tx.set_yticks([]); tx.set_xlabel("time (ns)")
    for s_ in ("top", "right", "left"):
        tx.spines[s_].set_visible(False)
    tx.legend(loc="upper left", bbox_to_anchor=(0.0, 0.62), frameon=False, fontsize=9)
    tx.text(-3, 1.33, "read windows", ha="right", fontsize=8.5, color=SUM)
    finish(fig, "sampling_cycle")


# --------------------------------------------------------------------------- Figure 3

def budget_phases() -> None:
    fig, ax = plt.subplots(figsize=(12, 3.4))
    items = [("S  static tracking", 0.15, "end of acquisition"), ("P  turn-off step", 0.15, "switch opening"),
             ("A  acquisition,\nhistory", 0.10, "during acquisition"), ("H  hold drift,\nfeedthrough", 0.10, "during hold"),
             ("reserve", 0.086, "PVT, model, numerics")]
    cols = ["#c96f4a", "#e09a6f", "#7a4fb0", "#9c7fc6", "#bbbbbb"]
    x = 0.0
    for (lab, w, when), c in zip(items, cols):
        ax.barh(1, w, left=x, color=c, edgecolor="white", height=0.55)
        ax.text(x + w / 2, 1, f"{lab}\n{w:.3g} mV", ha="center", va="center", fontsize=8.2, color="white" if c != "#bbbbbb" else INK)
        ax.text(x + w / 2, 0.55, when, ha="center", va="center", fontsize=8.3, color=MUTED, style="italic")
        x += w
    ax.plot([0.586, 0.586], [0.4, 1.45], color=SUM, lw=2)
    ax.text(0.586, 1.55, "±1 LSB = 0.586 mV (parent, deterministic)\nprovisional allocation budget", ha="center",
            fontsize=9, color=SUM)
    ax.text(0.0, -0.15, "Random sampled noise (rms) has its own budget and is not added to this deterministic budget.",
            va="center", fontsize=8.8, color=MUTED, style="italic")
    ax.set_xlim(0, 0.72); ax.set_ylim(-0.45, 1.85)
    ax.set_yticks([]); ax.set_xlabel("mV")
    for s_ in ("top", "right", "left"):
        ax.spines[s_].set_visible(False)
    finish(fig, "budget_phases")


if __name__ == "__main__":
    requirement_vs_network()
    sampling_cycle()
    budget_phases()

"""Three further scenes of the tour video, drawn only from committed results: the cycle staircase of Section 8, the leakage test
of HSKEM-2's NTT engine and a closing card. Each scene is written as its own clip, for make_board_clip.py's ffmpeg concat.

usage: python make_tour_scenes.py <out dir>          (needs ffmpeg; writes stairs.mp4, tvla.mp4, card.mp4)
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import plotstyle as ps

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = pathlib.Path(sys.argv[1])
FPS, W, H = 20, 1280, 720
LIMIT = 4.5


def writer(name):
    return subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-an", str(OUT / name)], stdin=subprocess.PIPE)


def frame(ff, fig):
    fig.canvas.draw()
    ff.stdin.write(fig.canvas.buffer_rgba().tobytes())


def heading(fig, title, sub, foot):
    fig.text(0.03, 0.91, title, fontsize=20, fontweight="bold", color=ps.INK)
    fig.text(0.03, 0.865, sub, fontsize=13, color=ps.INK_2)
    fig.text(0.03, 0.03, foot, fontsize=10.5, color=ps.MUTED)


def stairs():
    cs = json.loads((ROOT / "results/system_sim/packed_system.json").read_text())["configs"]
    ss = json.loads((ROOT / "results/system_sim/streamed_system.json").read_text())["decaps_cycles"]
    steps = [("HSKEM-1", cs["asic_sysR"]["decaps_cycles_valid_and_rejected"]), ("D", cs["sram_only_sysBCD"]["decaps_cycles_valid_and_rejected"])] \
        + [(m, ss[m]["sram_only"]) for m in "EFG"] + [("H = HSKEM-2", ss["H"]["sram_only"])]
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    heading(fig, "How the cycles went away", "each design point removes the bottleneck that the profile of the one before exposed",
            f"RTL simulation of one decapsulation, one-round Keccak. With the row-serialized Keccak, HSKEM-2 takes {ss['H']['asic']:,} cycles.")
    ax = fig.add_axes([0.08, 0.13, 0.88, 0.68])
    bars = ax.bar(range(len(steps)), [0] * len(steps), color=ps.NTT, width=0.62)
    nx = len(steps)                                    # the next point has no number: it hints at more to come and claims nothing
    nb = ax.bar([nx], [steps[-1][1] * 0.62], width=0.62, fill=False, edgecolor=ps.INK_2, ls=(0, (4, 3)), lw=1.6, alpha=0)[0]
    nq = ax.text(nx, steps[-1][1] * 0.62, "?", ha="center", va="bottom", fontsize=22, fontweight="bold", color=ps.INK_2, alpha=0)
    ax.set_xticks(range(nx + 1), [s[0] for s in steps] + ["next"], fontsize=13)
    ax.set_ylim(0, steps[0][1] * 1.12); ax.set_yticks([]); ax.grid(False)
    for s in ("left", "top", "right"):
        ax.spines[s].set_visible(False)
    labels = [ax.text(i, 0, "", ha="center", va="bottom", fontsize=15, fontweight="bold", color=ps.INK) for i in range(len(steps))]
    ff = writer("stairs.mp4")
    grow = 4.2 / len(steps)
    for f in range(6 * FPS):
        t = f / FPS
        for i, (b, l, (_, v)) in enumerate(zip(bars, labels, steps)):
            u = min(max((t - i * grow) / grow, 0), 1)
            b.set_height(v * u * u * (3 - 2 * u))
            l.set_position((i, b.get_height())); l.set_text(f"{v:,}" if u >= 1 else "")
        a = min(max((t - 4.6) / 0.5, 0), 1)
        nb.set_alpha(a); nq.set_alpha(a)
        frame(ff, fig)
    ff.stdin.close(); ff.wait()
    plt.close(fig)


def tvla():
    un = json.loads((ROOT / "results/leakage_packed2/tvla_summary.json").read_text())
    ma = json.loads((ROOT / "results/leakage_masked_packed2/tvla_summary.json").read_text())
    tu, tm = np.load(ROOT / "results/leakage_packed2/tvla_t.npy"), np.load(ROOT / "results/leakage_masked_packed2/tvla_t.npy")
    assert ma["cycles_over_4p5"] == 0 < un["cycles_over_4p5"]
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    heading(fig, "Does the NTT engine leak?", f"a leakage test on {un['traces']:,} traces; beyond the dashed lines, leakage is detectable",
            "Simulated leakage of the register model, not a power measurement. Masking was tested on the NTT engine alone, not on the whole chip.")
    lim = max(np.abs(tu).max(), np.abs(tm).max()) * 1.1
    lines = []
    for y, (t, c, name, s) in zip((0.47, 0.11), ((tu, ps.CRITICAL, "unmasked", un), (tm, ps.NTT, "first-order masked", ma))):
        ax = fig.add_axes([0.08, y, 0.88, 0.31])
        ax.axhspan(-LIMIT, LIMIT, color=ps.BAND, lw=0, zorder=0)
        for v in (LIMIT, -LIMIT):
            ax.axhline(v, color=ps.INK_2, lw=0.9, ls=(0, (4, 3)))
        ln, = ax.plot([], [], lw=0.9, color=c)
        ax.set_xlim(0, len(t)); ax.set_ylim(-lim, lim); ax.set_xticks([]); ax.set_ylabel("Welch t"); ax.grid(False)
        ax.set_title(f"{name}: largest |t| = {s['max_abs_t']:.1f}", loc="left", fontsize=14, fontweight="bold", color=ps.INK)
        lines.append((ln, t))
    ff = writer("tvla.mp4")
    for f in range(7 * FPS):
        u = min(f / (5 * FPS), 1)
        for ln, t in lines:
            n = int(len(t) * u)
            ln.set_data(np.arange(n), t[:n])
        frame(ff, fig)
    ff.stdin.close(); ff.wait()
    plt.close(fig)


def card():
    so = json.loads((ROOT / "results/fullchip/rev_c/summary.json").read_text())["signoff"]
    feol = json.loads((ROOT / "results/fullchip/rev_c/feol_drc.json").read_text())["after_implant_fix"]["markers_total"]
    assert so["drc_markers"] + feol == 0 and so["primary_compare"].lower().startswith("circuits match uniquely")
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    fig.text(0.07, 0.78, "Run it yourself", fontsize=34, fontweight="bold", color=ps.INK)
    rows = [("About 35 minutes", "for the whole notebook on a free Colab instance"),
            ("Open tools", "OpenROAD, OpenRAM, KLayout, Magic, Netgen and Icarus Verilog"),
            ("LVS match, 0 DRC markers", "on the final layout of HSKEM-2")]
    for i, (a, b) in enumerate(rows):
        fig.text(0.07, 0.61 - i * 0.17, a, fontsize=22, fontweight="bold", color=ps.INK)
        fig.text(0.07, 0.56 - i * 0.17, b, fontsize=15, color=ps.INK_2)
    fig.text(0.07, 0.09, "SRAMs verified separately; DRC counted once the implant gaps inside the macros are closed. Neither chip has been fabricated.",
             fontsize=11.5, color=ps.MUTED)
    ff = writer("card.mp4")
    for _ in range(5 * FPS):
        frame(ff, fig)
    ff.stdin.close(); ff.wait()
    plt.close(fig)


if __name__ == "__main__":
    ps.apply()
    stairs(); tvla(); card()

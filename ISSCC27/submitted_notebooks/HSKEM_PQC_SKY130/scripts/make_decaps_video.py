"""A short video of one decapsulation, drawn only from committed results: results/system_sim/decaps_timeline.json (activity
flags in every cycle) and results/fullchip/rev_c/block_map.csv.gz (the die by block). Part 1 lights the NTT engine and the
Keccak sponge on the die of HSKEM-2 as a decapsulation runs; part 2 races HSKEM-1 and HSKEM-2 cycle for cycle.

usage: python make_decaps_video.py          (needs ffmpeg; writes figures/decaps_race.mp4)
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import gzip
import json
import pathlib
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgb

import placement_map as pm
import plotstyle as ps

ROOT = pathlib.Path(__file__).resolve().parents[1]
FPS, W, H = 20, 1280, 720
PART1_S, HOLD_S, PART2_S = 12, 2, 12


def die_image():
    rows = gzip.decompress((ROOT / "results/fullchip/rev_c/block_map.csv.gz").read_bytes()).decode().splitlines()
    tiles = [r.split(",") for r in rows[2:] if not r.startswith("macro:")]
    n = max(max(int(t[0]), int(t[1])) for t in tiles) + 1
    base = np.full((n, n, 3), 0.97)
    masks = {"u_shared_ntt": np.zeros((n, n), bool), "u_shared_mlkem_sponge": np.zeros((n, n), bool)}
    for ix, iy, b in tiles:
        ix, iy = int(ix), int(iy)
        base[iy, ix] = 0.8 + 0.2 * np.array(to_rgb(pm.BLOCK_STYLE[b][1]))           # every block faint
        if b in masks:
            masks[b][iy, ix] = True
    return base, masks


def flags(seg, end):
    """Per-cycle boolean arrays of the two engines."""
    ntt, spo = np.zeros(end, bool), np.zeros(end, bool)
    for i, r in enumerate(seg):
        stop = seg[i + 1]["t"] if i + 1 < len(seg) else end
        ntt[r["t"]:stop], spo[r["t"]:stop] = bool(r["ntt"]), bool(r["sponge"])
    return ntt, spo


def strip(ax, f, c, scale_end, label):
    """One activity lane, revealed by a white curtain that the frame loop moves."""
    img = np.ones((1, 1600, 3))
    idx = np.minimum((np.arange(1600) * scale_end / 1600).astype(int), len(f) - 1)
    on = f[idx] & (np.arange(1600) * scale_end / 1600 < len(f))
    img[0, on] = to_rgb(c)
    ax.imshow(img, aspect="auto", extent=(0, scale_end, 0, 1), interpolation="nearest")
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    ax.set_ylabel(label, rotation=0, ha="right", va="center", fontsize=11, color=ps.INK_2)
    for s in ax.spines.values():
        s.set_visible(False)
    return ax.axvspan(0, scale_end, color="#efeee9", lw=0)


def main():
    ps.apply()
    tl = json.loads((ROOT / "results/system_sim/decaps_timeline.json").read_text())
    h1, h2 = tl["hskem1"], tl["hskem2"]
    n1, s1 = flags(h1["segments"], h1["cycles"]); n2, s2 = flags(h2["segments"], h2["cycles"])
    base, masks = die_image()
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    title = fig.text(0.03, 0.93, "", fontsize=20, fontweight="bold", color=ps.INK)
    sub = fig.text(0.03, 0.885, "", fontsize=13, color=ps.INK_2)
    fig.text(0.03, 0.03, "RTL simulation of one decapsulation, activity flags of every clock cycle. Slowed down; not a measurement on silicon.",
             fontsize=10.5, color=ps.MUTED)
    die = fig.add_axes([0.03, 0.09, 0.42, 0.75]); die.axis("off")
    im = die.imshow(base, origin="lower", interpolation="nearest")
    axs = [fig.add_axes([0.6, y, 0.37, 0.09]) for y in (0.68, 0.56)]
    cur2 = [strip(axs[0], n2, ps.NTT, len(n2), "NTT"), strip(axs[1], s2, ps.KECCAK, len(n2), "Keccak")]
    c2 = fig.text(0.6, 0.79, "", fontsize=17, fontweight="bold", color=ps.INK)
    bx = [fig.add_axes([0.13, y, 0.84, 0.08]) for y in (0.62, 0.52, 0.27, 0.17)]
    cur1 = [strip(bx[0], n1, ps.NTT, len(n1), "NTT"), strip(bx[1], s1, ps.KECCAK, len(n1), "Keccak")]
    cur3 = [strip(bx[2], n2, ps.NTT, len(n1), "NTT"), strip(bx[3], s2, ps.KECCAK, len(n1), "Keccak")]
    c1 = fig.text(0.13, 0.72, "", fontsize=17, fontweight="bold", color=ps.INK)
    c3 = fig.text(0.13, 0.37, "", fontsize=17, fontweight="bold", color=ps.INK)
    for a in bx:
        a.set_visible(False)
    ntt_c, kec_c = np.array(to_rgb(ps.NTT)), np.array(to_rgb(ps.KECCAK))
    ffmpeg = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "24", "-movflags", "+faststart", "-an",
                               str(ROOT / "figures/decaps_race.mp4")], stdin=subprocess.PIPE)
    total = (PART1_S + HOLD_S + PART2_S + HOLD_S) * FPS
    for f in range(total):
        t = f / FPS
        if t < PART1_S + HOLD_S:
            c = min(int(len(n2) * t / PART1_S), len(n2) - 1)
            title.set_text("HSKEM-2: one decapsulation on the die")
            sub.set_text("the NTT engine and the Keccak sponge light up when they are busy, and they overlap")
            a = base.copy()
            if n2[c]:
                a[masks["u_shared_ntt"]] = ntt_c
            if s2[c]:
                a[masks["u_shared_mlkem_sponge"]] = kec_c
            im.set_data(a)
            for cu in cur2:
                cu.set_x(c); cu.set_width(len(n2) - c)
            c2.set_text(f"cycle {min(c + 1, len(n2)):,} of {len(n2):,}")
        else:
            c = int(len(n1) * min((t - PART1_S - HOLD_S) / PART2_S, 1))
            title.set_text("The same work, clock for clock")
            sub.set_text(f"HSKEM-2 has finished before HSKEM-1 has gone far: {len(n1):,} against {len(n2):,} cycles")
            die.set_visible(False)
            for a_ in axs:
                a_.set_visible(False)
            c2.set_text("")
            for a_ in bx:
                a_.set_visible(True)
            for cu in cur1:
                cu.set_x(c); cu.set_width(len(n1) - c)
            for cu in cur3:
                cu.set_x(c); cu.set_width(len(n1) - c)
            c1.set_text(f"HSKEM-1: {min(c, len(n1)):,} cycles" + ("  done" if c >= len(n1) else ""))
            c3.set_text(f"HSKEM-2: {min(c, len(n2)):,} cycles" + ("  done" if c >= len(n2) else ""))
        fig.canvas.draw()
        ffmpeg.stdin.write(fig.canvas.buffer_rgba().tobytes())
    ffmpeg.stdin.close(); ffmpeg.wait()


if __name__ == "__main__":
    main()

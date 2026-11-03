import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.patches import Arc, Rectangle

ROOT = Path(__file__).resolve().parents[2]
src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build" / "cocotb" / "fibo_trace.json"
dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name("fibo_trace.png")
dst_spiral = dst.with_name("fibo_spiral.png")

INK = "#1f2933"
MUTED = "#6b7280"
GRID = "#e5e7eb"
LINE = "#2563eb"

data = json.load(open(src, encoding="utf-8"))
trace, outs, states = data["trace"], data["outs"], data["states"]
values = [o["value"] for o in outs]


def plot_trace():
    n = outs[-1]["cycle"] + 30
    tr = [t for t in trace if t["cycle"] < n]
    cyc = [t["cycle"] for t in tr]

    fig, ax = plt.subplots(
        3, 1, figsize=(11, 7.5), sharex=True, gridspec_kw={"height_ratios": [1, 1, 2.6]}
    )

    ax[0].step(cyc, [t["state"] for t in tr], where="post", color=LINE, linewidth=1.2)
    ax[0].set_yticks(range(6))
    ax[0].set_yticklabels(states, fontsize=8)
    ax[0].set_ylabel("state", color=INK)

    ax[1].step(cyc, [t["pc"] for t in tr], where="post", color=LINE, linewidth=1.4)
    ax[1].set_yticks([0, 4, 11])
    ax[1].set_yticklabels(["0", "4 (loop)", "11 (done)"], fontsize=8)
    ax[1].set_ylabel("pc", color=INK)

    ax[2].step(cyc, [t["gpio"] for t in tr], where="post", color=LINE, linewidth=1.6)
    ax[2].plot([o["cycle"] for o in outs], values, "o", color=LINE, markersize=5,
               markeredgecolor="white", markeredgewidth=1.2)
    for i, o in enumerate(outs):
        ax[2].annotate(str(o["value"]), (o["cycle"], o["value"]), xytext=(0, 8),
                       textcoords="offset points", ha="center", fontsize=8, color=INK)
    ax[2].set_ylabel("gpio_out", color=INK)
    ax[2].set_xlabel("clock cycle", color=INK)
    ax[2].set_ylim(-12, 262)

    first, second = outs[1]["cycle"], outs[2]["cycle"]
    for a in ax:
        for o in outs:
            a.axvline(o["cycle"], color=GRID, linewidth=0.8, zorder=0)
        a.grid(False)
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
        a.tick_params(colors=MUTED, labelsize=8)
    ax[2].annotate("", xy=(second, 250), xytext=(first, 250),
                   arrowprops=dict(arrowstyle="<->", color=MUTED, linewidth=1))
    ax[2].text((first + second) / 2, 237, f"{second - first} cycles per iteration",
               ha="center", fontsize=8, color=MUTED)

    fig.suptitle(f"Fibonacci ({data['hex']}) on cpu_core, sampled from cocotb",
                 color=INK, fontsize=11, y=0.995)
    fig.tight_layout()
    fig.savefig(dst, dpi=140, facecolor="white")
    plt.close(fig)


def tile(sides):
    rects = []
    x0 = y0 = x1 = y1 = 0
    for k, s in enumerate(sides):
        if k == 0:
            r = (0, 0, s, s)
            x1, y1 = s, s
        else:
            d = (k - 1) % 4
            if d == 0:
                r = (x1, y0, x1 + s, y0 + s)
                x1 += s
            elif d == 1:
                r = (x0, y1, x0 + s, y1 + s)
                y1 += s
            elif d == 2:
                r = (x0 - s, y0, x0, y0 + s)
                x0 -= s
            else:
                r = (x0, y0 - s, x0 + s, y0)
                y0 -= s
        rects.append(r)
    return rects


def arc_center(k, r):
    xa, ya, xb, yb = r
    if k == 0:
        return xb, yb
    return [(xa, yb), (xa, ya), (xb, ya), (xb, yb)][(k - 1) % 4]


def draw_spiral(ax, sides, rects, upto, label_min):
    colors = cm.Blues([0.18 + 0.62 * i / (len(sides) - 1) for i in range(len(sides))])
    ang = 180
    for k in range(upto):
        xa, ya, xb, yb = rects[k]
        s = sides[k]
        ax.add_patch(Rectangle((xa, ya), s, s, facecolor=colors[k],
                               edgecolor="white", linewidth=1.6))
        cx, cy = arc_center(k, rects[k])
        ax.add_patch(Arc((cx, cy), 2 * s, 2 * s, theta1=ang % 360, theta2=(ang + 90) % 360,
                         color=INK, linewidth=1.5))
        ang += 90
        lum = 0.299 * colors[k][0] + 0.587 * colors[k][1] + 0.114 * colors[k][2]
        if s >= label_min:
            ax.text((xa + xb) / 2, (ya + yb) / 2, str(s), ha="center", va="center",
                    fontsize=max(6.5, min(26, 6 + 26 * math.sqrt(s / max(sides[:upto])))),
                    color=INK if lum > 0.55 else "white", fontweight="bold")
    xs = [r[0] for r in rects[:upto]] + [r[2] for r in rects[:upto]]
    ys = [r[1] for r in rects[:upto]] + [r[3] for r in rects[:upto]]
    pad = 0.02 * max(max(xs) - min(xs), max(ys) - min(ys))
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.set_aspect("equal")
    ax.axis("off")


def plot_spiral():
    sides = [v for v in values if v > 0]
    rects = tile(sides)
    ok = all(
        abs((r[2] - r[0]) - (r[3] - r[1])) < 1e-9 for r in rects
    )
    fig, ax = plt.subplots(1, 2, figsize=(13, 6.4), gridspec_kw={"width_ratios": [0.9, 1.4]})
    draw_spiral(ax[0], sides, rects, len(sides), 34)
    ax[0].set_title(f"{len(sides)} values read from gpio_out (the initial 0 is skipped)", color=INK, fontsize=10)
    zoom = 8
    draw_spiral(ax[1], sides, rects, zoom, 1)
    ax[1].set_title(f"first {zoom} squares", color=INK, fontsize=10)
    fig.suptitle("Fibonacci spiral built from the gpio_out values of the simulated CPU",
                 color=INK, fontsize=12, y=0.99)
    fig.tight_layout()
    fig.savefig(dst_spiral, dpi=140, facecolor="white")
    plt.close(fig)


plot_trace()
plot_spiral()
print(dst)
print(dst_spiral)

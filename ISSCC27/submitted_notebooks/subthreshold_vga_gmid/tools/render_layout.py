#!/usr/bin/env python3
"""Render the committed GDS (layout/vga_core_12t.gds) to images/layout_12t.png: the drawn layers of the top cell,
flattened, with the pin and net labels. Needs gdstk and matplotlib only (no EDA tools).

  python tools/render_layout.py [--gds layout/vga_core_12t.gds] [--out images/layout_12t.png]
SPDX-License-Identifier: Apache-2.0
"""
import argparse, re
from pathlib import Path
import gdstk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

ROOT = Path(__file__).resolve().parents[1]
# sky130 drawing layers (layer, datatype): name, face colour, alpha, z-order
LAYERS = [((64, 20), "nwell", "#d9c9a3", 0.35, 1), ((65, 20), "diff", "#3fa34d", 0.55, 2), ((65, 44), "tap", "#2e7d32", 0.55, 2),
          ((66, 20), "poly", "#d32f2f", 0.55, 3), ((67, 20), "li1", "#8e6bbf", 0.35, 4), ((68, 20), "met1", "#1e88e5", 0.30, 5),
          ((69, 20), "met2", "#ef6c00", 0.30, 6), ((70, 20), "met3", "#6d4c41", 0.35, 7), ((71, 20), "met4", "#455a64", 0.35, 8)]
PIN_TEXT = {(67, 5), (68, 5), (69, 5), (70, 5), (71, 5), (67, 16), (68, 16), (69, 16), (70, 16), (71, 16)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gds", default=str(ROOT / "layout" / "vga_core_12t.gds"))
    ap.add_argument("--out", default=str(ROOT / "images" / "layout_12t.png"))
    a = ap.parse_args()
    lib = gdstk.read_gds(a.gds)
    top = [c for c in lib.top_level() if c.name == "vga_core_12t"] or lib.top_level()
    cell = top[0]
    polys = cell.get_polygons()
    by = {}
    for p in polys:
        by.setdefault((p.layer, p.datatype), []).append(p.points)
    (x0, y0), (x1, y1) = cell.bounding_box()
    w, h = x1 - x0, y1 - y0
    fig, ax = plt.subplots(figsize=(12, 12 * h / w + 0.6), dpi=170)
    handles = []
    for key, name, col, al, z in LAYERS:
        pts = by.get(key)
        if not pts:
            continue
        ax.add_collection(PolyCollection(pts, facecolors=col, edgecolors="none", alpha=al, zorder=z))
        handles.append(plt.Rectangle((0, 0), 1, 1, fc=col, alpha=min(1, al + 0.3), label=name))
    # pin and net labels: stacked in a column right of the cell, each with a leader line to where it sits
    labs, seen = [], set()
    for lb in cell.get_labels():
        t = lb.text.strip()
        if (lb.layer, lb.texttype) in PIN_TEXT and t not in seen and not t.startswith("$"):
            seen.add(t); labs.append((lb.origin[1], lb.origin[0], t))
    labs.sort(reverse=True)
    gap, ys = 0.045 * h, []
    for y, _, _ in labs:
        ys.append(min(y, ys[-1] - gap) if ys else y)
    for (y, x, t), yt in zip(labs, ys):
        ax.annotate(t, (x, y), xytext=(x1 + 0.06 * w, yt), fontsize=8, ha="left", va="center", zorder=20,
                    arrowprops=dict(arrowstyle="-", lw=0.5, color="0.35"))
    # the device arrays: clusters of active area, named in the order the generator's placement report lists them
    boxes = []
    for pts in sorted(by.get((65, 20), []), key=lambda q: -q[:, 1].max()):
        bx = (pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max())
        for i, b in enumerate(boxes):
            if bx[1] <= b[3] + 3 and bx[3] >= b[1] - 3:
                boxes[i] = (min(b[0], bx[0]), min(b[1], bx[1]), max(b[2], bx[2]), max(b[3], bx[3])); break
        else:
            boxes.append(bx)
    boxes.sort(key=lambda b: -b[3])
    place = Path(a.gds).with_name("vga_core_12t_placement.txt")
    names = []
    if place.exists():
        for m in re.finditer(r"^\[(\w+)\][^\n]*", place.read_text(), re.M):
            devs = sorted(set(re.findall(r"^\s+(M\d+)\s+units", place.read_text().split(m.group(0))[1].split("\n[")[0], re.M)),
                          key=lambda d: int(d[1:]))
            names.append(f"{m.group(1)}: {', '.join(devs)}")
    if len(names) == len(boxes):
        for b, n in zip(boxes, names):
            ax.text(b[0], b[3] + 0.012 * h, n, fontsize=9, ha="left", va="bottom", zorder=21, weight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))
    ax.set_xlim(x0, x1 + 0.16 * w); ax.set_ylim(y0, y1); ax.set_aspect("equal")
    ax.set_xlabel("x (µm)"); ax.set_ylabel("y (µm)")
    ax.set_title(f"vga_core_12t layout ({w:.0f} µm × {h:.0f} µm), drawn layers, flattened", fontsize=11, pad=16)
    ax.legend(handles=handles, loc="lower left", fontsize=8, frameon=False, ncol=len(handles), bbox_to_anchor=(0, -0.16))
    fig.tight_layout()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, bbox_inches="tight"); plt.close(fig)
    print(f"wrote {a.out}: {len(polys)} polygons, {w:.1f} x {h:.1f} um, labels {sorted(seen)}")


if __name__ == "__main__":
    main()

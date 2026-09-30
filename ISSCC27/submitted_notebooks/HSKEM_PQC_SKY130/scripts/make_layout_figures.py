"""Compose the layout renders used in the notebook into two compact JPEG figures.

figures/block_layouts.jpg  : KLayout renders (metal 1-5, scripts/render_gds.py) of four
                             routed blocks, drawn to a common scale using each run's die box.
figures/fullchip_layout.jpg: the full-chip render, downscaled. At about 2.5 um per pixel it shows
                             the floorplan only; no cell or wire can be resolved.

The source renders (results/asic/*/layout.png, results/fullchip/fullchip_layout.png) and the GDS
files are not part of the submission; this script documents how the figures were made.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import placement_map as pm  # noqa: E402
import plotstyle as ps      # noqa: E402

RUNS = [("ntt_sp_20ns", "NTT, original single-port"), ("ntt_opt_pipe_w12_20ns", "NTT, redesign (Section 7)"),
        ("keccak_r1_20ns", "Keccak, one round per clock"), ("keccak_s7_20ns", "Keccak, row-serialized")]


def blocks() -> None:
    ps.apply()
    boxes = {r: pm.load(r)[1] for r, _ in RUNS}                     # die box (x0, y0, x1, y1) in um
    side = max(max(b[2] - b[0], b[3] - b[1]) for b in boxes.values())
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.9))
    for ax, (run, title) in zip(axes, RUNS):
        x0, y0, x1, y1 = boxes[run]
        img = Image.open(ROOT / "results/asic" / run / "layout.png").convert("RGB")
        img = img.crop(ImageOps.invert(img).getbbox())             # drop the white margin around the die
        ax.imshow(img, extent=(0, x1 - x0, 0, y1 - y0))
        ax.set_xlim(0, side); ax.set_ylim(0, side); ax.set_aspect("equal")
        ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        for sp in ax.spines.values():
            sp.set_visible(False)
        ps.title_with_detail(ax, title, f"die {x1 - x0:.0f} × {y1 - y0:.0f} µm")
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.suptitle("Routed blocks at the 20 ns target (KLayout, metal layers 1–5), drawn to a common scale",
                 x=0.01, y=0.99, ha="left", fontsize=12, fontweight="bold")
    fig.savefig(ROOT / "figures/block_layouts.jpg", dpi=130, pil_kwargs={"quality": 85, "optimize": True})


def fullchip() -> None:
    img = Image.open(ROOT / "results/fullchip/fullchip_layout.png").convert("RGB")
    img.thumbnail((1400, 1400), Image.LANCZOS)
    img.save(ROOT / "figures/fullchip_layout.jpg", quality=85, optimize=True)


if __name__ == "__main__":
    blocks()
    fullchip()
    for f in ("block_layouts.jpg", "fullchip_layout.jpg"):
        p = ROOT / "figures" / f
        print(p.name, p.stat().st_size, Image.open(p).size)

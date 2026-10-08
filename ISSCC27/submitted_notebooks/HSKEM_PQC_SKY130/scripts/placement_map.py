"""Placement maps of the routed blocks, coloured by cell class.

Reads results/asic/<run>/cells.csv (written by flow/dump_cells.tcl), drops the
physical-only cells (fill, tap, decap, antenna diodes) and draws every
functional cell as a rectangle in one of the three classes used for the
synthesis area breakdown: flip-flops, XOR/XNOR, other logic.

usage: python placement_map.py            (all runs that have a cells.csv)
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import pathlib
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import plotstyle as ps  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
PHYSICAL = ("fill", "tap", "decap", "diode")
CLASSES = [("flip-flops", ps.SERIES[0]), ("XOR/XNOR", ps.SERIES[1]), ("other logic", ps.SERIES[2])]


def cell_class(master: str) -> str | None:
    cell = master.split("__")[-1]
    if cell.startswith(PHYSICAL):
        return None
    if cell.startswith(("df", "edf", "sdf", "dl")):
        return "flip-flops"
    if cell.startswith(("xor", "xnor")):
        return "XOR/XNOR"
    return "other logic"


def _read(path: pathlib.Path) -> tuple[pd.DataFrame, tuple]:
    df = pd.read_csv(path)
    die = df[df.master == "DIE"].iloc[0]
    df = df[df.master != "DIE"].copy()
    df["cls"] = [("macro" if mac else cell_class(m)) for m, mac in zip(df.master, df.is_macro)]
    return df.dropna(subset=["cls"]), (die.x0, die.y0, die.x1, die.y1)


def load(run: str) -> tuple[pd.DataFrame, tuple]:
    return _read(ROOT / "results" / "asic" / run / "cells.csv.gz")


def draw_chip(ax, path: pathlib.Path | None = None) -> None:
    """Full HSKEM core: standard cells by class, SRAM macros as labelled blocks."""
    df, (x0, y0, x1, y1) = _read(path or ROOT / "results" / "fullchip" / "cells.csv.gz")
    for name, colour in CLASSES:
        d = df[df.cls == name]
        rects = [Rectangle((r.x0, r.y0), r.x1 - r.x0, r.y1 - r.y0) for r in d.itertuples()]
        ax.add_collection(PatchCollection(rects, facecolor=colour, edgecolor="none", rasterized=True))
    for r in df[df.cls == "macro"].itertuples():
        ax.add_patch(Rectangle((r.x0, r.y0), r.x1 - r.x0, r.y1 - r.y0, facecolor="#e1e0d9",
                               edgecolor=ps.INK_2, lw=0.8, zorder=3))
        shape = r.master.replace("sky130_sram_1rw_", "").split("_")[0].replace("x", " × ")
        ax.text((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2, shape, ha="center", va="center",   # one line: bits × words
                fontsize=6.5, color=ps.INK_2, zorder=4)
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor=ps.AXIS, lw=1))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)


def draw(ax, run: str, title: str, extent: float | None = None) -> None:
    """Draw one block; with `extent` (µm) every panel shares the same scale."""
    df, (x0, y0, x1, y1) = load(run)
    for name, colour in CLASSES:
        d = df[df.cls == name]
        rects = [Rectangle((r.x0, r.y0), r.x1 - r.x0, r.y1 - r.y0) for r in d.itertuples()]
        ax.add_collection(PatchCollection(rects, facecolor=colour, edgecolor="none", rasterized=True))
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor=ps.AXIS, lw=1))
    span = extent or max(x1 - x0, y1 - y0)
    ax.set_xlim(x0, x0 + span); ax.set_ylim(y0, y0 + span); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ps.title_with_detail(ax, title, f"die {(x1 - x0):.0f} × {(y1 - y0):.0f} µm")


def compact(p: pathlib.Path) -> pathlib.Path:
    """Keep the die, the macros and the functional cells, rounded to 0.01 µm, gzip-compressed."""
    df = pd.read_csv(p)
    keep = (df.master == "DIE") | (df.is_macro == 1) | df.master.map(lambda m: cell_class(m) is not None)
    out = p.with_suffix(".csv.gz")
    df[keep].round(2).to_csv(out, index=False, compression="gzip")
    p.unlink()
    return out


if __name__ == "__main__":
    ps.apply()
    for p in sorted(ROOT.glob("results/*/*/cells.csv")) + sorted(ROOT.glob("results/fullchip/cells.csv")):
        out = compact(p)
        print("compacted", out.relative_to(ROOT), f"{out.stat().st_size / 1e6:.2f} MB")

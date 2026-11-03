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
CLASSES = [("flip-flops", ps.CELL_CLASS[0]), ("XOR/XNOR", ps.CELL_CLASS[1]), ("other logic", ps.CELL_CLASS[2])]


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
        ax.add_patch(Rectangle((r.x0, r.y0), r.x1 - r.x0, r.y1 - r.y0, facecolor=ps.MEM,
                               edgecolor=ps.INK_2, lw=0.8, zorder=3))
        shape = r.master.replace("sky130_sram_1rw_", "").split("_")[0].replace("x", " × ")
        ax.text((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2, shape, ha="center", va="center",   # one line: bits × words
                fontsize=6.5, color=ps.INK_2, zorder=4)
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor=ps.AXIS, lw=1))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)


# the blocks of the die map: name in the layout, label, colour; one hue per function, the shared engines as in every figure
BLOCK_STYLE = {"u_shared_ntt": ("NTT engine", ps.NTT), "u_shared_mlkem_sponge": ("Keccak sponge", ps.KECCAK),
               "u_mlkem512_kpke_partial": ("K-PKE and matrix", "#1d7874"),
               "u_mlkem512_encaps_partial": ("Encapsulation", "#3f9c8f"),
               "u_mlkem512_decaps_partial": ("Decapsulation", "#81b29a"),
               "u_c3_pk_pair_sram": ("Public-key buffer", "#b7d3c4"),
               "u_hsm_shell": ("HSM policy shell", ps.CODEC), "u_security_hmac": ("HMAC-SHA-256", "#b56aa3"),
               "u_bridge": ("SPI command bridge", ps.SLATE[1]), "u_spi": ("SPI front end", ps.SLATE[2]),
               "u_c2_shake_drbg": ("SHAKE DRBG", ps.MEM_W), "g_qualification_puf_vault": ("PUF root and key vault", "#d9b97e"),
               "u_puf": ("PUF interface", "#ecdcb4")}


def draw_blocks(ax, cells: pathlib.Path, block_map: pathlib.Path) -> dict:
    """The signed-off die by function: tiles coloured by the block that owns most of their cells, SRAM macros in the
    colour of their block, labelled in place. Returns the number of macros per block."""
    import gzip
    df, (x0, y0, x1, y1) = _read(cells)
    rows = gzip.decompress(block_map.read_bytes()).decode().splitlines()
    tile = float(rows[0].split(",")[1])
    tiles = pd.DataFrame([r.split(",") for r in rows[2:] if not r.startswith("macro:")], columns=["ix", "iy", "block"])
    tiles[["ix", "iy"]] = tiles[["ix", "iy"]].astype(int)
    pts = [r[6:].split(",") for r in rows if r.startswith("macro:")]
    macros, owner = df[df.cls == "macro"], []
    for r in macros.itertuples():
        d = [(max(r.x0 - float(x), float(x) - r.x1, 0) + max(r.y0 - float(y), float(y) - r.y1, 0), b) for x, y, b in pts]
        owner.append(min(d)[1])
    for b, g in tiles.groupby("block"):
        c = BLOCK_STYLE[b][1]
        ax.add_collection(PatchCollection([Rectangle((i * tile, j * tile), tile, tile) for i, j in zip(g.ix, g.iy)],
                                          facecolor=c, edgecolor="none", alpha=0.9, rasterized=True))
        n = int(max(tiles.ix.max(), tiles.iy.max())) + 1
        m = np.zeros((n, n), bool); m[g.ix, g.iy] = True
        if b not in ("u_c3_pk_pair_sram", "u_puf"):                        # the label sits where the block is densest
            w = 12
            I = np.pad(m.astype(int).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
            d = I[w:, w:] - I[:-w, w:] - I[w:, :-w] + I[:-w, :-w]
            i, j = np.unravel_index(int(d.argmax()), d.shape)
            i, j = i + w / 2, j + w / 2
            num = list(BLOCK_STYLE).index(b) + 1
            ax.text((i + 0.5) * tile, (j + 0.5) * tile, str(num), ha="center", va="center", fontsize=9.5, color=ps.INK,
                    fontweight="bold", zorder=6, bbox=dict(boxstyle="circle,pad=0.28", fc=ps.SURFACE, ec=ps.INK, lw=0.8))
    for r, b in zip(macros.itertuples(), owner):
        ax.add_patch(Rectangle((r.x0, r.y0), r.x1 - r.x0, r.y1 - r.y0, facecolor=ps.SURFACE, edgecolor=BLOCK_STYLE[b][1],
                               lw=2.2, zorder=3))
        shape = r.master.replace("sky130_sram_1rw_", "").split("_")[0].replace("x", " × ")
        ax.text((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2, shape, ha="center", va="center", fontsize=7, color=ps.INK_2, zorder=4)
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor=ps.AXIS, lw=1))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    return pd.Series(owner).value_counts().to_dict()


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

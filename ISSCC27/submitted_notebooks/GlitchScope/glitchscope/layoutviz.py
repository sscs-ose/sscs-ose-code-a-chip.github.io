"""Layout view of a placed design (DEF + LEF) with an optional per-cell value overlay,
e.g. GlitchScope's glitch energy per cell -> a glitch heat map on the real placement.

    from glitchscope.layoutviz import read_def, read_lef_sizes, plot_layout
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np


def read_lef_sizes(*paths):
    """{macro: (width_um, height_um)} from LEF files."""
    sizes = {}
    for p in paths:
        text = Path(p).read_text(errors="replace")
        for m in re.finditer(r"^\s*MACRO\s+(\S+)(.*?)^\s*END\s+\1\b", text, re.M | re.S):
            s = re.search(r"\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)", m.group(2))
            if s:
                sizes[m.group(1)] = (float(s.group(1)), float(s.group(2)))
    return sizes


def read_def(path):
    """Die area (um) and placed components {inst: (macro, x_um, y_um, orient)}."""
    p = Path(path)
    if p.suffix == ".gz":
        import gzip
        text = gzip.open(p, "rt", errors="replace").read()
    else:
        text = p.read_text(errors="replace")
    dbu = float(re.search(r"UNITS\s+DISTANCE\s+MICRONS\s+(\d+)", text).group(1))
    die = [float(v) / dbu for v in re.search(r"DIEAREA\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)",
                                            text).groups()]
    comps = {}
    sec = re.search(r"^COMPONENTS\s+\d+\s*;(.*?)^END COMPONENTS", text, re.M | re.S)
    for m in re.finditer(r"-\s+(\S+)\s+(\S+)(.*?);", sec.group(1), re.S):
        p = re.search(r"\+\s+(?:PLACED|FIXED)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)", m.group(3))
        if p:
            comps[m.group(1).replace("\\", "")] = (m.group(2), float(p.group(1)) / dbu, float(p.group(2)) / dbu, p.group(3))
    return dict(die=die, components=comps)


def plot_layout(ax, def_data, sizes, values=None, vmax=None, title="", highlight=None, cmap="Oranges", highlight2=None):
    """Draw cells as rectangles. ``values`` {inst: value} colours logic cells on a
    single-hue sequential scale; ``highlight`` {inst} (e.g. pipeline flops) is drawn
    in blue, ``highlight2`` (e.g. input/output flops) in light blue.  Physical-only cells (tap, fill, decap) are
    drawn faintly."""
    import matplotlib.pyplot as plt
    from matplotlib.collections import PatchCollection
    from matplotlib.patches import Rectangle
    x0, y0, x1, y1 = def_data["die"]
    phys, logic, logic_v, hi, hi2 = [], [], [], [], []
    for inst, (macro, x, y, _o) in def_data["components"].items():
        w, h = sizes.get(macro, (0.46, 2.72))
        r = Rectangle((x, y), w, h)
        base = macro.split("__")[-1]
        if re.match(r"(tapvpwrvgnd|decap|fill|diode)", base):
            phys.append(r)
        elif highlight and inst in highlight:
            hi.append(r)
        elif highlight2 and inst in highlight2:
            hi2.append(r)
        else:
            logic.append(r); logic_v.append((values or {}).get(inst, 0.0))
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=0.8, ec="#898781"))
    ax.add_collection(PatchCollection(phys, facecolor="#e1e0d9", edgecolor="none"))
    if values is not None:
        vm = vmax or (max(logic_v) if logic_v else 1.0) or 1.0
        pc = PatchCollection(logic, cmap=cmap, edgecolor="none")
        pc.set_array(np.asarray(logic_v)); pc.set_clim(0, vm)
        ax.add_collection(pc)
    else:
        pc = None
        ax.add_collection(PatchCollection(logic, facecolor="#c3c2b7", edgecolor="none"))
    if hi2:
        ax.add_collection(PatchCollection(hi2, facecolor="#9cc3ee", edgecolor="none"))
    if hi:
        ax.add_collection(PatchCollection(hi, facecolor="#2a78d6", edgecolor="none"))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal")
    ax.set_xlabel("µm"); ax.set_title(title); ax.grid(False)
    return pc

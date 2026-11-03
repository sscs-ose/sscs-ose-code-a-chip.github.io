"""Architecture figures: block diagram, cell-level slice, VCD waveform, workflow.

python make_arch_figures.py  ->  fig_arch_priorart, fig_arch_baselines,
fig_arch_block, fig_arch_cell, fig_timing, fig_workflow (.png/.pdf) and
cell_mix.csv. Prior-art panels are our own abstractions of
docs/related_work.md ([F] notes), not copies of published figures. Every parameter comes from
spec/spec.yaml, the RTL (cross-checked against the VCD's dumped parameters),
the newest finished sidecarcim_top_ff run, or tests/report.md.
"""
import bisect
import csv
import glob
import math
import os
import re
import sys
from collections import Counter, defaultdict

import numpy as np
import yaml
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "python"))
import golden  # noqa: E402

SPEC = yaml.safe_load(open(os.path.join(ROOT, "spec", "spec.yaml")))
ACC = "#D55E00"        # sidecar accent
INK = "#222222"
GREY = "#d9d9d9"
LGREY = "#f2f2f2"
MID = "#8c8c8c"


def clog2(v):
    return int(math.ceil(math.log2(v))) if v > 1 else 0


def params():
    """Widths with the RTL formulas (dcim_core.v, sidecar.v, sidecarcim_top.v)."""
    n, m = SPEC["array"]["n_inputs"], SPEC["array"]["n_outputs"]
    wb, ab = SPEC["dense"]["weight_bits"], SPEC["dense"]["act_bits"]
    vb, k = SPEC["outlier"]["weight_bits"], SPEC["outlier"]["budget_per_output"]
    p = dict(N_IN=n, N_OUT=m, WBITS=wb, ABITS=ab, VB=vb, K=k)
    p["AW"] = clog2(n)
    p["JW"] = max(1, clog2(m))
    p["ROWW"] = m * wb
    p["YW"] = clog2(n * (2 ** wb - 1) * (2 ** ab - 1) + 1)
    p["PARTW"] = clog2(n * (2 ** wb - 1) + 1)
    p["POPW"] = clog2(n + 1)                    # one popcount
    p["SLW"] = p["AW"] + vb
    p["SCW"] = vb + clog2(k * (2 ** ab - 1) + 1)
    p["SBW"] = clog2(vb)
    p["YTW"] = max(p["YW"] + vb, p["SCW"]) + 1
    p["CW"] = clog2(ab) if ab > 1 else 1
    p["XW"] = n * ab
    return p


# ---------------------------------------------------------------- style

def style():
    plt.rcParams.update({
        "font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"],
        "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
        "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.bbox": "tight",
        "mathtext.fontset": "stix",
    })


def save(fig, stem):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(HERE, stem + "." + ext), dpi=300)
    plt.close(fig)
    print("wrote", stem)


def box(ax, x, y, w, h, text="", fc="white", ec=INK, lw=0.9, ls="-",
        fs=7, bold=False, round_=0.0, tc=INK, va="center", z=2):
    if round_:
        p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=%g"
                           % round_, fc=fc, ec=ec, lw=lw, ls=ls, zorder=z)
    else:
        p = Rectangle((x, y), w, h, fc=fc, ec=ec, lw=lw, ls=ls, zorder=z)
    ax.add_patch(p)
    if text:
        ty = y + h / 2 if va == "center" else y + h - 0.012
        ax.text(x + w / 2, ty, text, ha="center", va=va, fontsize=fs,
                color=tc, weight="bold" if bold else "normal", zorder=z + 1,
                linespacing=1.15)
    return p


def arrow(ax, xy0, xy1, c=INK, lw=0.9, label=None, lpos=0.5, loff=(0, 0.012),
          fs=6.3, ha="center", style="-|>", z=3, ls="-", tc=None):
    ax.annotate("", xy=xy1, xytext=xy0, zorder=z,
                arrowprops=dict(arrowstyle=style, color=c, lw=lw, ls=ls,
                                shrinkA=0, shrinkB=0, mutation_scale=7))
    if label:
        lx = xy0[0] + (xy1[0] - xy0[0]) * lpos + loff[0]
        ly = xy0[1] + (xy1[1] - xy0[1]) * lpos + loff[1]
        ax.text(lx, ly, label, fontsize=fs, ha=ha, va="bottom",
                color=tc or c, zorder=z + 1)


def poly(ax, pts, c=INK, lw=0.9, ls="-", z=3):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=c, lw=lw, ls=ls, zorder=z, solid_capstyle="butt")


def blank(ax):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")


# ---------------------------------------------------------------- VCD

class VCD:
    """Minimal VCD reader: keeps only the requested hierarchical signals."""

    def __init__(self, path, want):
        self.path = path
        self.ids, self.width, self.params = {}, {}, {}
        scope, idmap = [], defaultdict(list)
        self.tv = {}
        with open(path) as f:
            for line in f:
                t = line.split()
                if not t:
                    continue
                if t[0] == "$scope":
                    scope.append(t[2])
                elif t[0] == "$upscope":
                    scope.pop()
                elif t[0] == "$var":
                    name = ".".join(scope + [t[4]])
                    if name in want:
                        idmap[t[3]].append(name)
                        self.width[name] = int(t[2])
                    if t[1] == "parameter" and len(scope) == 1:
                        idmap[t[3]].append("param:" + t[4])
                elif t[0] == "$enddefinitions":
                    break
            tnow = 0
            for nm in [n for v in idmap.values() for n in v]:
                self.tv[nm] = ([], [])
            for line in f:
                c = line[0]
                if c == "#":
                    tnow = int(line[1:])
                    continue
                if c in "bBrR":
                    val, code = line[1:].split()
                elif c in "01xXzZ":
                    val, code = c, line[1:].strip()
                else:
                    continue
                for nm in idmap.get(code, ()):
                    ts, vs = self.tv[nm]
                    if ts and ts[-1] == tnow:
                        vs[-1] = val
                    else:
                        ts.append(tnow)
                        vs.append(val)
        for k in list(self.tv):
            if k.startswith("param:"):
                self.params[k[6:]] = int(self.tv.pop(k)[1][-1], 2)

    def at(self, name, t):
        """Value in effect just before time t (what a flop samples at t)."""
        ts, vs = self.tv[name]
        i = bisect.bisect_left(ts, t) - 1
        return vs[i] if i >= 0 else "x"

    def int_at(self, name, t):
        v = self.at(name, t)
        return None if re.search("[xXzZ]", v) else int(v, 2)

    def rising(self, clk):
        ts, vs = self.tv[clk]
        return [t for t, v, pv in zip(ts[1:], vs[1:], vs[:-1])
                if v == "1" and pv == "0"]


def field(v, lo, w):
    return (v >> lo) & ((1 << w) - 1)


def sext(v, w):
    return v - (1 << w) if v >> (w - 1) & 1 else v


TOP = "sidecarcim_top"
SIGS = ["clk", "rst", "w_load_en", "w_load_addr", "w_load_row", "s_load_en",
        "s_load_col", "s_load_slots", "s_load_shift", "start", "x_in",
        "busy", "valid", "y", "yd", "ys", "xbit", "d_valid", "s_valid",
        "u_dense.cnt", "u_dense.state", "u_side.state"]


def find_vcd():
    p = os.path.join(HERE, "vcd", "sidecarcim_top_ff_pipe_s3.vcd")
    if os.path.exists(p):
        return p
    c = sorted(glob.glob(os.path.join(HERE, "vcd", "sidecarcim_top*.vcd")),
               key=os.path.getmtime)
    return c[-1]


def replay(vcd, p):
    """Rebuild w, slots, S, x from the load/start edges; golden-check each y."""
    n, m, wb, ab, aw, vb, k = (p[q] for q in ("N_IN", "N_OUT", "WBITS", "ABITS",
                                              "AW", "VB", "K"))
    g = lambda s, t: vcd.int_at(TOP + "." + s, t)  # noqa: E731
    edges = vcd.rising(TOP + ".clk")
    w = np.zeros((n, m), dtype=np.int64)
    idx = np.zeros((k, m), dtype=np.int64)
    val = np.zeros((k, m), dtype=np.int64)
    S = np.zeros(m, dtype=np.int64)
    busy_n, dots = 0, []
    for e_i, t in enumerate(edges):
        if g("rst", t):
            S[:] = 0
            busy_n = 0
            continue
        if busy_n:                       # COMPUTE edge
            busy_n -= 1
            if busy_n == 0:
                dots[-1]["valid_edge"] = e_i
            continue
        wl, sl = g("w_load_en", t), g("s_load_en", t)
        if wl:
            row, a = g("w_load_row", t), g("w_load_addr", t)
            for j in range(m):
                w[a, j] = field(row, j * wb, wb)
        if sl:
            sv, j = g("s_load_slots", t), g("s_load_col", t)
            for s in range(k):
                slot = field(sv, s * p["SLW"], p["SLW"])
                idx[s, j] = field(slot, 0, aw)
                val[s, j] = sext(field(slot, aw, vb), vb)
            S[j] = g("s_load_shift", t)
        if g("start", t) and not wl and not sl:
            xv = g("x_in", t)
            x = np.array([field(xv, i * ab, ab) for i in range(n)])
            exp = golden.sidecarcim_dot(w, x, idx, val, S, wb, ab, vb)
            dots.append(dict(start_edge=e_i, exp=exp, x=x, S=S.copy(),
                             yd=golden.dcim_dot(w, x, wb, ab),
                             ys=golden.sidecar_dot(idx, val, x, ab, vb)))
            busy_n = ab
    # the dense and sidecar results are ready after ABITS edges; with the
    # merge register (PIPE_MERGE=1) valid and y follow one edge later
    pipe = vcd.params.get("PIPE_MERGE", 0)
    for d in dots:
        if "valid_edge" not in d or d["valid_edge"] + pipe >= len(edges):
            d.pop("valid_edge", None)
            continue
        d["part_edge"] = d["valid_edge"]
        e = d["valid_edge"] = d["part_edge"] + pipe
        tq = edges[e + 1] if e + 1 < len(edges) else edges[e] + 1
        yv = g("y", tq)
        d["y"] = np.array([sext(field(yv, j * p["YTW"], p["YTW"]), p["YTW"])
                           for j in range(m)])
        d["ok"] = bool(np.array_equal(d["y"], d["exp"]))
        d["lat"] = e - d["start_edge"]
        d["valid_hi"] = g("valid", tq) == 1
    return edges, dots


# ---------------------------------------------------------------- RTL params

def rtl_defaults(name):
    """parameter NAME = int defaults of one RTL module."""
    src = open(os.path.join(ROOT, "rtl", name)).read()
    return {k: int(v) for k, v in
            re.findall(r"^\s*parameter\s+(\w+)\s*=\s*(\d+)", src, re.M)}


def designs(p):
    """Per design: latency (start->valid), storage bits per column and total."""
    mac, core = rtl_defaults("mac_baseline.v"), rtl_defaults("dcim_core.v")
    side, top = rtl_defaults("sidecar.v"), rtl_defaults("sidecarcim_top.v")
    src8 = open(os.path.join(ROOT, "rtl", "dcim_8bit.v")).read()
    wb8 = int(re.search(r"\.WBITS\((\d+)\)", src8).group(1))
    ab8 = int(re.search(r"\.ABITS\((\d+)\)", src8).group(1))
    for d in (mac, core, side, top):          # RTL defaults = spec
        for q in ("N_IN", "N_OUT", "WBITS", "ABITS", "VB", "K"):
            if q in d:
                assert d[q] == p[q], (q, d[q], p[q])
    n, m = core["N_IN"], core["N_OUT"]
    yw8 = clog2(n * (2 ** wb8 - 1) * (2 ** ab8 - 1) + 1)
    side_col = top["K"] * p["SLW"] + p["SBW"]
    return {
        "mac": dict(lat=mac["N_IN"] * mac["N_OUT"], wb=mac["WBITS"],
                    ab=mac["ABITS"], col=mac["N_IN"] * mac["WBITS"],
                    tot=n * m * mac["WBITS"], yw=p["YW"]),
        "dcim4": dict(lat=core["ABITS"], wb=core["WBITS"], ab=core["ABITS"],
                      col=n * core["WBITS"], tot=n * m * core["WBITS"],
                      yw=p["YW"], partw=p["PARTW"]),
        "dcim8": dict(lat=ab8, wb=wb8, ab=ab8, col=n * wb8, tot=n * m * wb8,
                      yw=yw8, partw=clog2(n * (2 ** wb8 - 1) + 1)),
        "sidecar": dict(lat=top["ABITS"], wb=top["WBITS"], ab=top["ABITS"],
                        col=n * top["WBITS"] + side_col,
                        tot=n * m * top["WBITS"] + m * side_col,
                        side_col=side_col, yw=p["YW"], partw=p["PARTW"]),
    }




# ---------------------------------------------------------------- panel grammar
# One grid for every block-diagram panel: input (X), storage (A), column
# logic (P), accumulator (C), output/merge (O); bottom row: control or
# outlier entry (F), outlier path (A2, P2, C2).
GRID = {"X": (0.000, 0.46, 0.125, 0.44), "A": (0.170, 0.46, 0.250, 0.44),
        "P": (0.465, 0.46, 0.130, 0.44), "C": (0.640, 0.46, 0.130, 0.44),
        "O": (0.815, 0.00, 0.125, 0.90), "F": (0.000, 0.00, 0.125, 0.28),
        "A2": (0.170, 0.00, 0.250, 0.28), "P2": (0.465, 0.00, 0.130, 0.28),
        "C2": (0.640, 0.00, 0.130, 0.28)}
YB = 0.62          # top-row bus height
YT = 0.37          # routing channel between the rows
KIND = {"store": dict(fc=LGREY, ec=INK), "logic": dict(fc="white", ec=INK),
        "ctrl": dict(fc="white", ec=MID, round_=0.012),
        "new": dict(fc="#fbe6da", ec=ACC),
        "newstore": dict(fc="#f6cdb5", ec=ACC),
        "off": dict(fc="white", ec=MID, ls="--"),
        "ghost": dict(fc="white", ec="#c4c4c4", ls=":")}
FS = 6.2


def gbox(ax, key, title, body="", kind="logic", fs=FS, sub=None, tc=INK):
    """Grid box: bold title at the top, body lines below it."""
    x, y, w, h = GRID[key] if sub is None else sub
    k = KIND[kind]
    box(ax, x, y, w, h, "", fc=k["fc"], ec=k["ec"], ls=k.get("ls", "-"),
        round_=k.get("round_", 0.0), lw=0.9 if kind != "ghost" else 0.7)
    col = "#9a9a9a" if kind == "ghost" else tc
    ax.annotate(title, (x + w / 2, y + h), xytext=(0, -2.5),
                textcoords="offset points", ha="center", va="top",
                fontsize=fs, weight="bold", color=col, zorder=6)
    if body:
        ax.annotate(body, (x + w / 2, y + h), xytext=(0, -2.5 - fs * 1.35),
                    textcoords="offset points", ha="center", va="top",
                    fontsize=fs - 0.4, color=col, zorder=6, linespacing=1.12)
    return x, y, w, h


def bus(ax, p0, p1, width=None, name=None, c=INK, head=True):
    """Arrow with '/width' above its middle and the signal name below."""
    if head:
        arrow(ax, p0, p1, c=c)
    else:
        poly(ax, [p0, p1], c=c)
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    if width is not None:
        ax.plot([mx - 0.003, mx + 0.003], [my - 0.035, my + 0.035], color=c,
                lw=0.7, zorder=6)
        ax.annotate("%s" % width, (mx, my), xytext=(0, 2.5),
                    textcoords="offset points", ha="center", va="bottom",
                    fontsize=FS - 0.9, color=c, zorder=6)
    if name:
        ax.annotate(name, (mx, my), xytext=(0, -2.5),
                    textcoords="offset points", ha="center", va="top",
                    fontsize=FS - 0.9, color=c, zorder=6, style="italic")


def edge(key, side, f=0.5):
    x, y, w, h = GRID[key]
    return {"l": (x, y + h * f), "r": (x + w, y + h * f),
            "t": (x + w * f, y + h), "b": (x + w * f, y)}[side]


def top_in(ax, key, label, f=0.5):
    x, y, w, h = GRID[key]
    xx = x + w * f
    arrow(ax, (xx, 1.04), (xx, y + h))
    ax.annotate(label, (xx, 1.0), xytext=(3, 0), textcoords="offset points",
                ha="left", va="center", fontsize=FS - 0.7, style="italic")


def mini_array(ax, key, bits, rows=4, cols=8, hl=(), hl_c=ACC, frac=0.52,
               whole=(), zero=()):
    """Weight grid in the lower part of a storage box; cells split by bit."""
    x, y, w, h = GRID[key]
    x, w = x + 0.012, w - 0.024
    y0, hh = y + 0.035, h * frac
    cw, rh = w / cols, hh / (rows + 0.7)
    for r in range(rows):
        ry = y0 + hh - (r + 1) * rh - (0.7 * rh if r == rows - 1 else 0)
        for c in range(cols):
            on = (r, c) in hl
            fc = hl_c if on else ("#9e9e9e" if (r, c) in zero else "white")
            ax.add_patch(Rectangle((x + c * cw + cw * 0.04, ry), cw * 0.92,
                                   rh * 0.8, fc=fc, ec=INK, lw=0.35,
                                   zorder=4))
            if bits > 1 and (r, c) not in whole and not on:
                for b in range(1, bits):
                    xx = x + c * cw + cw * 0.04 + b * cw * 0.92 / bits
                    ax.plot([xx, xx], [ry, ry + rh * 0.8], color=MID,
                            lw=0.25, zorder=4)
    ax.text(x + w / 2, y0 + hh - (rows - 0.62) * rh, r"$\vdots$",
            ha="center", va="center", fontsize=5, zorder=5)


def caption(ax, lines):
    for i, ln in enumerate(lines):
        ax.annotate(ln, (0, 0), xycoords="axes fraction",
                    xytext=(0, -4 - i * 8.2), textcoords="offset points",
                    ha="left", va="top", fontsize=FS + 0.3, color=INK)


def panel_title(ax, txt):
    ax.annotate(txt, (0, 1), xycoords="axes fraction", xytext=(0, 9),
                textcoords="offset points", ha="left", va="bottom",
                fontsize=7.4, weight="bold")


def stacked_axes(fig, n, top=0.35, cap=0.30, h=1.28):
    """n full-width panels stacked; sizes in inches."""
    W, H = fig.get_size_inches()
    axs, yy = [], H - top
    for _ in range(n):
        yy -= h
        axs.append(fig.add_axes([0.01, yy / H, 0.98, h / H]))
        yy -= cap + top
    for ax in axs:
        blank(ax)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1.06)
    return axs


def out_arrow(ax, width, name="y"):
    x, y, w, h = GRID["O"]
    bus(ax, (x + w, YB), (1.0, YB), width, name)


def draw_dcim_panel(ax, p, d, kind):
    """Bit-serial DCIM panel; kind = dcim4 / dcim8 / sidecar."""
    wb, ab, n, m = d["wb"], d["ab"], p["N_IN"], p["N_OUT"]
    gbox(ax, "X", "x register", "%d lanes x %d b\nshift left each cycle\n"
         "MSB of each lane\n= bit-plane xbit" % (n, ab))
    gbox(ax, "A", "weight array %dx%dx%d b" % (n, m, wb),
         "%d storage bits (FF)" % (n * m * wb), "store")
    mini_array(ax, "A", wb)
    gbox(ax, "P", "per column",
         "AND w & xbit\n%d popcounts\n(%d rows -> %d b)\nshift-add" %
         (wb, n, p["POPW"]))
    gbox(ax, "C", "shift-accumulate", "acc = 2 acc + part\n%d x %d b" %
         (m, d["yw"]))
    bus(ax, edge("X", "r", 0.37), edge("A", "l", 0.37), n, "xbit")
    bus(ax, edge("A", "r", 0.37), edge("P", "l", 0.37), n * m * wb,
        "w")
    bus(ax, edge("P", "r", 0.37), edge("C", "l", 0.37), "%dx%d" %
        (m, d["partw"]), "part")
    gbox(ax, "F", "control FSM", "LOAD/COMP/DONE\n%d compute cycles" %
         d["lat"], "ctrl")
    top_in(ax, "X", "x_in /%d" % (n * ab), 0.2)
    top_in(ax, "A", "w_load_row /%d, addr /%d" % (m * wb, p["AW"]), 0.5)
    if kind != "sidecar":
        gbox(ax, "O", "output y", "%d columns\nx %d b\nunsigned" %
             (m, d["yw"]))
        bus(ax, edge("C", "r", 0.37), (GRID["O"][0], YB),
            m * d["yw"], "y")
        gbox(ax, "A2", "(no outlier path)", "", "ghost")
        return
    gbox(ax, "A2", "sidecar slots, K=%d per column" % p["K"],
         "(row index %d b, value %d b signed)\n%d FF" %
         (p["AW"], p["VB"], m * p["K"] * p["SLW"]), "newstore")
    gbox(ax, "P2", "per slot", "mux xbit[index]\nAND value, add K",
         "new")
    gbox(ax, "C2", "shift-accumulate", "%d x %d b signed" % (m, p["SCW"]),
         "new")
    gbox(ax, "O", "merge", "S register\n%d x %d b\n\nY = (yd << S)\n+ ys\n\n"
         "%d x %d b signed\n0 extra cycles" % (m, p["SBW"], m, p["YTW"]),
         "new")
    bus(ax, edge("A2", "r", 0.4), edge("P2", "l", 0.4), m * p["K"] * p["SLW"],
        "slots", c=ACC)
    bus(ax, edge("P2", "r", 0.4), edge("C2", "l", 0.4), "%dx%d" %
        (m, p["VB"] + clog2(p["K"])), "sum", c=ACC)
    bus(ax, edge("C", "r", 0.37), (GRID["O"][0], YB - 0.0), m * d["yw"],
        "yd")
    bus(ax, edge("C2", "r", 0.4), (GRID["O"][0], edge("C2", "r", 0.4)[1]),
        m * p["SCW"], "ys", c=ACC)
    # shared bit-plane tap
    xt = GRID["X"][2] + 0.018
    yt = YT
    ax.plot([xt], [YB], marker="o", ms=2.4, color=ACC, zorder=7)
    x2 = GRID["P2"][0] + 0.025
    poly(ax, [(xt, YB), (xt, yt), (x2, yt)], c=ACC)
    arrow(ax, (x2, yt), (x2, GRID["P2"][1] + GRID["P2"][3]), c=ACC)
    ax.annotate("same xbit /%d (shared, no second x register)" % n,
                (GRID["A"][0] + 0.01, yt), xytext=(0, 1.0),
                textcoords="offset points", fontsize=FS - 0.7, color=ACC,
                ha="left", va="bottom")
    out_arrow(ax, m * p["YTW"])


def draw_mac_panel(ax, p, d):
    n, m, wb, ab = p["N_IN"], p["N_OUT"], d["wb"], d["ab"]
    gbox(ax, "X", "x register", "%d x %d b\nmux selects x[i]" % (n, ab))
    gbox(ax, "A", "register file %d x %d b" % (n, m * wb),
         "%d storage bits (FF), 1 read/cycle" % (n * m * wb), "store")
    mini_array(ax, "A", wb, hl={(0, 0)}, hl_c="#6e6e6e")
    gbox(ax, "P", "one MAC", "mux w[i][j]\n%d b x %d b\nmultiplier" %
         (wb, ab))
    gbox(ax, "C", "adder + acc", "%d b, one column\nat a time" % d["yw"])
    gbox(ax, "O", "output y", "%d x %d b\nregister,\none column\nper %d cycles"
         % (m, d["yw"], n))
    bus(ax, edge("A", "r", 0.37), edge("P", "l", 0.37), wb, "w[i][j]")
    bus(ax, edge("P", "r", 0.37), edge("C", "l", 0.37), wb + ab, "product")
    bus(ax, edge("C", "r", 0.37), (GRID["O"][0], YB),
        d["yw"], "y[j]")
    # x[i] runs under the register file
    xs = GRID["X"][2] * 0.5
    yx = YT
    poly(ax, [(xs, GRID["X"][1]), (xs, yx), (GRID["P"][0] + 0.03, yx)])
    arrow(ax, (GRID["P"][0] + 0.03, yx), (GRID["P"][0] + 0.03, GRID["P"][1]))
    ax.annotate("x[i] /%d" % ab, (GRID["A"][0] + 0.01, yx), xytext=(0, -1.5),
                textcoords="offset points", fontsize=FS - 0.7, ha="left",
                va="top", style="italic")
    gbox(ax, "F", "control FSM", "i, j counters\n%d compute cycles"
         % d["lat"], "ctrl")
    gbox(ax, "A2", "(no outlier path)", "", "ghost")
    top_in(ax, "X", "x_in /%d" % (n * ab), 0.2)
    top_in(ax, "A", "load_row /%d, addr /%d" % (m * wb, p["AW"]), 0.5)


def fig_arch_baselines(p):
    d = designs(p)
    fig = plt.figure(figsize=(7.16, 8.25))
    axs = stacked_axes(fig, 4, top=0.30, cap=0.24, h=1.42)
    order = [("mac", "(a) Conventional MAC baseline (rtl/mac_baseline.v)"),
             ("dcim4", "(b) Uniform 4-bit bit-serial DCIM (rtl/dcim_core.v)"),
             ("dcim8", "(c) Uniform 8-bit DCIM (rtl/dcim_8bit.v = dcim_core, "
                       "WBITS = ABITS = %d)" % d["dcim8"]["wb"]),
             ("sidecar", "(d) SidecarCIM, ours (rtl/sidecarcim_top.v = (b) "
                         "+ sidecar + merge)")]
    for ax, (k, title) in zip(axs, order):
        panel_title(ax, title)
        if k == "mac":
            draw_mac_panel(ax, p, d[k])
        else:
            draw_dcim_panel(ax, p, d[k], k)
        e = d[k]
        if k == "sidecar":
            st = "%d b/column (%d weight + %d slot + %d S)" % (
                e["col"], p["N_IN"] * e["wb"], p["K"] * p["SLW"], p["SBW"])
        else:
            st = "%d b/column" % e["col"]
        caption(ax, ["Cycles per MVM: %d (start to valid; %d with the DONE "
                     "cycle, back-to-back).   Storage: %s, %d b total."
                     % (e["lat"], e["lat"] + 1, st, e["tot"])])
    fig.text(0.01, 0.004, "Grey fill = weight storage; orange = what "
             "SidecarCIM adds. All widths from the RTL parameters "
             "(defaults = spec/spec.yaml); storage as laid out (flip-flops)."
             "\nMVM = %dx%d. Zero-point correction "
             "runs outside the macro in all four designs." %
             (p["N_IN"], p["N_OUT"]), fontsize=FS, ha="left", va="bottom",
             color="#333333")
    save(fig, "fig_arch_baselines")
    return d


# ---------------------------------------------------------------- prior art
# Simplified, own abstraction from docs/related_work.md ([F] entries only).
PRIOR = [
    dict(tag="chih", title="(a) Conventional bit-serial DCIM, no outlier "
         "handling (after Chih et al., ISSCC 2021)",
         cap=["Outlier format: none (uniform precision).",
              "Cost of handling: n/a; one cycle per input bit; energy tracks "
              "input toggle rate (89 vs 52 TOPS/W at 18 % vs 50 % toggle)."]),
    dict(tag="oacim", title="(b) OA-CIM (after He et al., JSSC 2026)",
         cap=["Outlier format: BF16 weight, element-wise inside the array; "
              "at most 1 per 32-value block, extras dropped.",
              "Cost of handling: 3 INT4 neighbours zeroed; BF16 activations "
              "+ FP-capable MAC; index memory 0.4 % area; 0 extra cycles "
              "(1 parallel cycle)."]),
    dict(tag="dac25", title="(c) DAC'25 OutlierCIM (after Zou et al., "
         "DAC 2025)",
         cap=["Outlier format: BF16 activation channels (3-sigma rule on "
              "calibration), clustered into the last 128-channel tile.",
              "Cost of handling: unified FP-INT MAC + offline channel "
              "reordering; removes the bit-serial wait (-25.3 % latency vs "
              "bit-serial baseline)."]),
    dict(tag="olaccel", title="(d) OLAccel, not CIM (after Park et al., "
         "ISCA 2018)",
         cap=["Outlier format: 16-bit (8-bit option) weights and activations, "
              "coordinate-list index, about 1 per 16-weight chunk.",
              "Cost of handling: separate outlier MAC lane beside 16 normal "
              "MACs; 0 extra cycles for 1 outlier per chunk, +1 cycle for a "
              "second."]),
]


def draw_prior(ax, tag):
    if tag == "chih":
        gbox(ax, "X", "inputs", "bit-serial,\nMSB first,\n1-8 b")
        gbox(ax, "A", "SRAM weight array", "6T + NOR cells, 4-16 b weights", "store")
        mini_array(ax, "A", 4)
        gbox(ax, "P", "column adder", "sum of\n1-b products")
        gbox(ax, "C", "shift-accumulate", "one cycle\nper input bit")
        gbox(ax, "O", "output", "integer\npartial sums")
        bus(ax, edge("X", "r", 0.37), edge("A", "l", 0.37), None, "input bit")
        bus(ax, edge("A", "r", 0.37), edge("P", "l", 0.37))
        bus(ax, edge("P", "r", 0.37), edge("C", "l", 0.37))
        bus(ax, edge("C", "r", 0.37), (GRID["O"][0], YB))
        gbox(ax, "A2", "(no outlier path)", "", "ghost")
    elif tag == "oacim":
        gbox(ax, "X", "activations", "INT4")
        gbox(ax, "F", "INT4 -> BF16", "for inputs paired\nwith an outlier",
             "new")
        gbox(ax, "A", "SRAM array of 16-b cells",
             "cell = 4 x INT4 or 1 x BF16 outlier", "store")
        mini_array(ax, "A", 4, hl={(1, 2)}, whole={(1, 2)})
        gbox(ax, "A2", "outlier index memory",
             "5-b position + 1-b flag per 32-value block;\n<= 1 outlier per "
             "block, extras dropped", "newstore")
        gbox(ax, "P", "LUT-based MAC", "INT4 and BF16,\nfully parallel,\n"
             "one cycle", "new")
        gbox(ax, "C", "column output", "(generic)")
        gbox(ax, "O", "output", "")
        bus(ax, edge("X", "r", 0.37), edge("A", "l", 0.37))
        bus(ax, edge("F", "t"), edge("X", "b"), None, None, c=ACC)
        bus(ax, edge("A", "r", 0.37), edge("P", "l", 0.37))
        ya = edge("A2", "r", 0.6)[1]
        bus(ax, edge("A2", "r", 0.6), (GRID["P"][0] + 0.03, ya), head=False,
            c=ACC)
        arrow(ax, (GRID["P"][0] + 0.03, ya),
              (GRID["P"][0] + 0.03, GRID["P"][1]), c=ACC)
        bus(ax, edge("P", "r", 0.37), edge("C", "l", 0.37))
        bus(ax, edge("C", "r", 0.37), (GRID["O"][0], YB))
        ax.annotate("outlier cell (orange); its 3 INT4 neighbours are zeroed",
                    (GRID["A"][0] + 0.012, GRID["A"][1] + 0.005),
                    xytext=(0, -1), textcoords="offset points", va="top",
                    fontsize=FS - 0.9, color=ACC)
    elif tag == "dac25":
        gbox(ax, "X", "activations", "per channel;\noutlier channels\nby "
             "3-sigma rule")
        gbox(ax, "F", "OCTS (offline)", "cluster outlier\nchannels, last tile", "new")
        gbox(ax, "A", "CIM macro, 128-channel tiles",
             "W4; last tile: BF16 activation channels", "store")
        mini_array(ax, "A", 4, hl={(3, c) for c in range(8)})
        gbox(ax, "P", "FP-INT MAC", "unified;\nINT4 x INT4 and\nBF16 x INT4",
             "new")
        gbox(ax, "C", "accumulate", "(generic)")
        gbox(ax, "O", "output", "")
        bus(ax, edge("X", "r", 0.37), edge("A", "l", 0.37))
        bus(ax, edge("F", "t"), edge("X", "b"), None, None, c=ACC)
        bus(ax, edge("A", "r", 0.37), edge("P", "l", 0.37))
        bus(ax, edge("P", "r", 0.37), edge("C", "l", 0.37))
        bus(ax, edge("C", "r", 0.37), (GRID["O"][0], YB))
        gbox(ax, "A2", "(no separate outlier lane)", "", "ghost")
    elif tag == "olaccel":
        gbox(ax, "X", "activations", "4 b;\noutliers 16 b")
        gbox(ax, "A", "weight buffer", "4-b dense weights in 16-weight "
             "chunks", "store")
        mini_array(ax, "A", 4)
        gbox(ax, "A2", "outlier list", "16-b outliers, coordinate-list "
             "index,\nabout 1 per 16-weight chunk", "newstore")
        gbox(ax, "P", "16 normal MACs", "4 b x 4 b")
        gbox(ax, "P2", "outlier MAC", "16 b, separate\nlane", "new")
        gbox(ax, "C", "accumulate", "(generic)")
        gbox(ax, "O", "output", "")
        bus(ax, edge("X", "r", 0.37), edge("A", "l", 0.37))
        bus(ax, edge("A", "r", 0.37), edge("P", "l", 0.37))
        bus(ax, edge("A2", "r", 0.5), edge("P2", "l", 0.5), c=ACC)
        bus(ax, edge("P", "r", 0.37), edge("C", "l", 0.37))
        x2 = GRID["P2"][0] + GRID["P2"][2]
        yo = edge("P2", "r", 0.5)[1]
        poly(ax, [(x2, yo), (GRID["C"][0] + 0.03, yo)], c=ACC)
        arrow(ax, (GRID["C"][0] + 0.03, yo),
              (GRID["C"][0] + 0.03, GRID["C"][1]), c=ACC)
        bus(ax, edge("C", "r", 0.37), (GRID["O"][0], YB))


def fig_arch_priorart():
    fig = plt.figure(figsize=(7.16, 7.75))
    axs = stacked_axes(fig, 4, top=0.25, cap=0.31, h=1.33)
    for ax, pr in zip(axs, PRIOR):
        panel_title(ax, pr["title"])
        draw_prior(ax, pr["tag"])
        caption(ax, pr["cap"])
    fig.text(0.01, 0.004, "Simplified block abstractions drawn from the "
             "cited papers; not copies of published figures.\nOrange = "
             "hardware that exists to handle outliers. 'generic' = not "
             "described in the paper.",
             fontsize=FS, ha="left", va="bottom", color="#333333")
    save(fig, "fig_arch_priorart")


# ---------------------------------------------------------------- netlist
PHYS = ("decap", "fill", "tapvpwrvgnd", "diode")     # no logic function
OUTPINS = {"X", "Y", "Q", "Q_N", "COUT", "SUM", "HI", "LO", "GCLK"}
BUFS = ("buf_", "clkbuf_", "dlygate", "clkdlybuf", "dlymetal")
ROLE = {"dfxtp": "D flip-flop (all state: weights, slots, S, x lanes, acc)",
        "mux2": "2:1 mux (datapath select; storage holds use clock gating)",
        "dlclkp": "integrated clock gate, one per row / column",
        "mux4": "4:1 mux (slot row select tree, xbit[idx])",
        "dlygate4sd3": "delay gate, hold-time fix (P&R)",
        "clkdlybuf4s25": "delay buffer, I/O and repair buffering (P&R)",
        "nand2": "NAND2 (AND of w and xbit; adder logic)",
        "nor2": "NOR2 (adder logic)", "xnor2": "XNOR2 (adder sum bits)",
        "xor2": "XOR2 (adder sum bits)", "or2": "OR2", "and2": "AND2",
        "a22o": "AND-OR (2x2)", "a21oi": "AND-OR-INV", "a21o": "AND-OR",
        "inv": "inverter", "and3": "AND3", "nand4": "NAND4", "buf": "buffer",
        "clkbuf": "clock tree buffer"}


def newest_run(flowdir="sidecarcim_top_ff"):
    """Newest RUN_* that has a final netlist (a running flow has none yet)."""
    runs = sorted(glob.glob(os.path.join(ROOT, "flow", flowdir, "runs",
                                         "RUN_*")))
    for r in reversed(runs):
        nl = glob.glob(os.path.join(r, "final", "nl", "*.nl.v"))
        if nl:
            return r, nl[0], runs
    raise FileNotFoundError(flowdir)


def read_netlist(path):
    """[(cell, inst, {pin: net})] for every sky130 instance."""
    src = open(path).read()
    out = []
    for m in re.finditer(r"^\s*sky130_fd_sc_hd__(\w+)\s+(\S+)\s*\((.*?)\);",
                         src, re.S | re.M):
        pins = {a: b.strip() for a, b in
                re.findall(r"\.(\w+)\(\s*([^()]*?)\s*\)", m.group(3))}
        out.append((m.group(1), m.group(2), pins))
    return out


def base(cell):
    """sky130 cell name without drive strength (dfxtp_2 -> dfxtp)."""
    return re.sub(r"_\d+$", "", cell)


def netlist_stats(path, p):
    """Cell counts, plus what drives and what reads each storage flop group."""
    inst = read_netlist(path)
    cnt = Counter(c for c, _, _ in inst)
    dmap, sinks = {}, defaultdict(list)
    for c, i, pins in inst:
        for pn, net in pins.items():
            if pn in OUTPINS:
                dmap[net] = (c, pins)
            else:
                sinks[net].append((c, pins))

    def thru_sinks(net, depth=5):
        """Logic cells reading a net, looking through inserted buffers."""
        res = []
        for c, pins in sinks.get(net, []):
            if c.startswith(BUFS) and depth:
                o = next(n for q, n in pins.items() if q in OUTPINS)
                res += thru_sinks(o, depth - 1)
            else:
                res.append(base(c))
        return res

    def thru_driver(net, depth=5):
        c, pins = dmap.get(net, ("port", {}))
        while c.startswith(BUFS) and depth:
            net = next(n for q, n in pins.items() if q not in OUTPINS)
            c, pins = dmap.get(net, ("port", {}))
            depth -= 1
        return base(c)

    def field_of(q):
        m = re.match(r"^\\u_side\.g_col\[\d+\]\.col\[(\d+)\]", q)
        if m:
            return "slot index" if int(m.group(1)) % p["SLW"] < p["AW"] \
                else "slot value"
        if re.match(r"^\\u_dense\.g_row\[", q):
            return "dense weight"
        if re.match(r"^\\g_sh\[", q):
            return "S register"
        return None

    grp = {}
    for c, i, pins in inst:
        if base(c) != "dfxtp":
            continue
        g = field_of(pins["Q"])
        if g is None:
            continue
        e = grp.setdefault(g, dict(n=0, d=Counter(), q=Counter(), hold=0,
                                   clk=Counter()))
        e["n"] += 1
        e["d"][thru_driver(pins["D"])] += 1
        e["clk"][thru_driver(pins["CLK"], 20)] += 1
        e["q"].update(thru_sinks(pins["Q"]))
        if any(base(cc).startswith("dlygate") for cc, _ in sinks[pins["Q"]]):
            e["hold"] += 1
    return cnt, grp


def write_cell_mix(cnt, path, run):
    """Top-10 cell mix; writes path only if given (cell_mix.csv is owned
    by the flow engineer, so main() passes None)."""
    logic = {c: n for c, n in cnt.items() if not base(c).startswith(PHYS)}
    phys = sum(n for c, n in cnt.items() if base(c).startswith(PHYS))
    tot = sum(logic.values())
    top = sorted(logic.items(), key=lambda t: -t[1])[:10]
    if path is None:
        return top, tot, phys
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "cell", "count", "pct_of_logic_cells", "role"])
        for k, (c, n) in enumerate(top, 1):
            w.writerow([k, "sky130_fd_sc_hd__" + c, n, "%.1f" % (100 * n / tot),
                        ROLE.get(re.sub(r"_\d+$", "", c), "")])
        rest = tot - sum(n for _, n in top)
        w.writerow(["", "other logic cell types (%d)" % (len(logic) - 10),
                    rest, "%.1f" % (100 * rest / tot), ""])
        w.writerow(["", "total logic cells", tot, "100.0", ""])
        w.writerow(["", "physical-only (decap, fill, tap, diode)", phys, "",
                    "not logic"])
        w.writerow(["", "source", os.path.relpath(run, ROOT), "",
                    "final/nl netlist"])
    print("wrote", os.path.basename(path))
    return top, tot, phys


# ---------------------------------------------------------------- fig 1: block

def fig_arch_block(p):
    n, m, wb, ab, k, vb = (p[q] for q in ("N_IN", "N_OUT", "WBITS", "ABITS",
                                          "K", "VB"))
    fig = plt.figure(figsize=(7.16, 3.5))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.axis("off")
    ax.set_xlim(-0.075, 1.005)
    ax.set_ylim(-0.10, 1.0)
    R = {"X": (0.0, 0.50, 0.115, 0.37), "A": (0.15, 0.50, 0.215, 0.37),
         "P": (0.40, 0.50, 0.12, 0.37), "C": (0.555, 0.50, 0.10, 0.37),
         "F": (0.0, 0.03, 0.115, 0.35), "A2": (0.15, 0.03, 0.215, 0.31),
         "P2": (0.40, 0.03, 0.12, 0.31), "C2": (0.555, 0.03, 0.10, 0.31),
         "O": (0.69, 0.03, 0.105, 0.84), "Z": (0.83, 0.03, 0.175, 0.84)}
    yb, y2 = 0.62, 0.155
    f = FS - 0.4
    gbox(ax, None, "x register", "%d lanes x %d b,\nloaded at start,\n"
         "shift <<1 / cycle\nxbit[i] = MSB of\nlane i = bit a\n(a = %d..0)"
         % (n, ab, ab - 1), sub=R["X"], fs=f)
    gbox(ax, None, "dense weight array", "%d rows x %d col x %d b\n= %d dfxtp, "
         "1 row written/cycle" % (n, m, wb, n * m * wb), "store", sub=R["A"],
         fs=f)
    xa, ya, wa, ha = R["A"]
    GRID["_A"] = (xa, ya, wa, ha)
    mini_array(ax, "_A", wb, frac=0.48)
    gbox(ax, None, "per column (x%d)" % m, "AND w & xbit\n%d popcounts\n"
         "(%d -> %d b)\nshift-add by b\n-> part %d b"
         % (wb, n, p["POPW"], p["PARTW"]), sub=R["P"], fs=f)
    gbox(ax, None, "shift-acc (x%d)" % m, "acc = 2 acc\n+ part\n%d b, cleared"
         "\nat start" % p["YW"], sub=R["C"], fs=f)
    gbox(ax, None, "sidecar slot store", "%d col x K=%d slots;\nslot = index "
         "%d b | value %d b\n%d dfxtp, 1 column/cycle"
         % (m, k, p["AW"], vb, m * k * p["SLW"]), "newstore", sub=R["A2"],
         fs=f)
    gbox(ax, None, "per slot (x%d)" % (m * k), "%d:1 mux\nxbit[index]\n"
         "AND %d-b value\nadd K -> %d b" % (n, vb, vb + clog2(k)), "new",
         sub=R["P2"], fs=f)
    gbox(ax, None, "shift-acc (x%d)" % m, "acc = 2 acc\n+ sum\n%d b signed"
         % p["SCW"], "new", sub=R["C2"], fs=f)
    gbox(ax, None, "merge (x%d)" % m, "S register %d b\n(s_load_shift,\n"
         "reset to 0)\n\nyd << S\n(%d -> %d b)\n+ sign-ext. ys\n\nY: %d b "
         "signed\ncombinational:\n0 extra cycles" % (p["SBW"], p["YW"],
                                                    p["YW"] + vb - 1,
                                                    p["YTW"]),
         "new", sub=R["O"], fs=f)
    gbox(ax, None, "off-macro (software)", "zero-point correction\n"
         "python/quant.py\n(signed_dot,\nsidecar_signed):\n\n"
         "Y - [(zw sum x + zx sum w\n- N zx zw) << S]\n- zx sum val\n\n"
         "then scale sx sw / 2^S\n+ bias (llm_layer.py)", "off", sub=R["Z"],
         fs=f)
    gbox(ax, None, "control FSM", "LOAD/COMP/DONE\ncnt %d b = a\none FSM "
         "per path:\nbusy = OR\nvalid = AND" % p["CW"], "ctrl", sub=R["F"],
         fs=f)

    def r(key, side, f=0.5):
        x, y, w, h = R[key]
        return {"l": (x, y + h * f), "r": (x + w, y + h * f),
                "t": (x + w * f, y + h), "b": (x + w * f, y)}[side]

    bus(ax, (R["X"][0] + R["X"][2], yb), (xa, yb), n, "xbit")
    bus(ax, (xa + wa, yb), (R["P"][0], yb), n * m * wb, "w")
    bus(ax, (R["P"][0] + R["P"][2], yb), (R["C"][0], yb), "%dx%d" %
        (m, p["PARTW"]), "part")
    bus(ax, (R["C"][0] + R["C"][2], yb), (R["O"][0], yb), m * p["YW"], "yd")
    bus(ax, (R["A2"][0] + R["A2"][2], y2), (R["P2"][0], y2),
        m * k * p["SLW"], "slots", c=ACC)
    bus(ax, (R["P2"][0] + R["P2"][2], y2), (R["C2"][0], y2), "%dx%d" %
        (m, vb + clog2(k)), "sum", c=ACC)
    bus(ax, (R["C2"][0] + R["C2"][2], y2), (R["O"][0], y2), m * p["SCW"],
        "ys", c=ACC)
    bus(ax, (R["O"][0] + R["O"][2], yb), (R["Z"][0], yb), m * p["YTW"],
        "y (raw)")
    # shared bit-plane tap
    xt, yt = R["X"][0] + R["X"][2] + 0.014, 0.43
    ax.plot([xt], [yb], marker="o", ms=2.6, color=ACC, zorder=7)
    x2 = R["P2"][0] + 0.03
    poly(ax, [(xt, yb), (xt, yt), (x2, yt)], c=ACC)
    arrow(ax, (x2, yt), (x2, R["P2"][1] + R["P2"][3]), c=ACC)
    ax.annotate("same bit-plane xbit /%d, MSB first: no second x register"
                % n, (xa + 0.005, yt), xytext=(0, 1.0),
                textcoords="offset points", fontsize=FS - 0.6, color=ACC,
                ha="left", va="bottom")
    # ports
    def pin_top(x, y0, label):
        arrow(ax, (x, 0.985), (x, y0))
        ax.annotate(label, (x, 0.985), xytext=(2.5, -1),
                    textcoords="offset points", ha="left", va="top",
                    fontsize=FS - 0.8, style="italic")
    pin_top(R["X"][0] + 0.02, R["X"][1] + R["X"][3], "x_in /%d" % (n * ab))
    pin_top(xa + 0.02, ya + ha, "w_load_en, w_load_addr /%d,\nw_load_row /%d"
            % (p["AW"], m * wb))

    def pin_bot(x, y1, label, c=INK):
        arrow(ax, (x, -0.085), (x, y1), c=c)
        ax.annotate(label, (x, -0.085), xytext=(2.5, 1),
                    textcoords="offset points", ha="left", va="bottom",
                    fontsize=FS - 0.8, style="italic", color=c)
    pin_bot(R["A2"][0] + 0.02, R["A2"][1], "s_load_en, s_load_col /%d, "
            "s_load_slots /%d" % (p["JW"], k * p["SLW"]), c=ACC)
    pin_bot(R["O"][0] + 0.02, R["O"][1], "s_load_shift /%d" % p["SBW"],
            c=ACC)
    for i, (lab, d) in enumerate((("start", 1), ("busy", -1),
                                  ("valid", -1))):
        yy = R["F"][1] + R["F"][3] * (0.72 - 0.22 * i)
        a0, a1 = (-0.065, 0.0) if d > 0 else (0.0, -0.065)
        arrow(ax, (a0, yy), (a1, yy))
        ax.text(-0.07, yy + 0.012, lab, fontsize=FS - 0.6, ha="left",
                va="bottom", style="italic")
    ax.annotate("clk, rst to all registers", (-0.07, R["F"][1] - 0.02),
                fontsize=FS - 0.9, ha="left", va="top", color=MID)
    ax.text(R["Z"][0] + R["Z"][2] / 2, R["Z"][1] - 0.025, "outside the macro",
            fontsize=FS - 0.7, ha="center", va="top", color=MID)
    del GRID["_A"]
    save(fig, "fig_arch_block")


# ---------------------------------------------------------------- fig 2: cell

def ff_sym(ax, x, y, w, h, label, sub=None, fc=LGREY, ec=INK):
    box(ax, x, y, w, h, "", fc=fc, ec=ec, lw=0.8)
    ax.add_patch(Polygon([(x, y + 0.02), (x + 0.018, y + 0.035),
                          (x, y + 0.05)], closed=True, fill=False, ec=ec,
                         lw=0.6, zorder=5))
    ax.text(x + w * 0.56, y + h * 0.62, label, ha="center", va="center",
            fontsize=FS - 0.6, zorder=6)
    if sub:
        ax.text(x + w * 0.56, y + h * 0.28, sub, ha="center", va="center",
                fontsize=FS - 1.4, zorder=6, color="#333333")


def mux_sym(ax, x, y, w, h, label, ec=INK, fc="white", fs=None):
    ax.add_patch(Polygon([(x, y), (x + w, y + h * 0.2), (x + w, y + h * 0.8),
                          (x, y + h)], closed=True, fc=fc, ec=ec, lw=0.8,
                         zorder=4))
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
            fontsize=fs or FS - 1.0, zorder=6, rotation=0)


def and_sym(ax, x, y, w, h, label="", ec=INK, fc="white"):
    t = np.linspace(-np.pi / 2, np.pi / 2, 25)
    pts = [(x, y), (x + w * 0.5, y)]
    pts += [(x + w * 0.5 + w * 0.5 * np.cos(a), y + h / 2 + h / 2 * np.sin(a))
            for a in t]
    pts += [(x, y + h)]
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=0.8, zorder=4))
    if label:
        ax.text(x + w * 0.45, y + h / 2, label, ha="center", va="center",
                fontsize=FS - 1.4, zorder=6)


def add_sym(ax, x, y, r, label="+", ec=INK, fc="white"):
    from matplotlib.patches import Ellipse
    ax.add_patch(Ellipse((x, y), 2 * r, 2 * r * 1.9, fc=fc, ec=ec, lw=0.8,
                         zorder=4))
    ax.text(x, y, label, ha="center", va="center", fontsize=FS + 0.5,
            zorder=6)


def fig_arch_cell(p, grp, top, tot, phys, run):
    n, m, wb, ab, k, vb = (p[q] for q in ("N_IN", "N_OUT", "WBITS", "ABITS",
                                          "K", "VB"))
    fig = plt.figure(figsize=(7.16, 5.6))
    axa = fig.add_axes([0.0, 0.40, 0.56, 0.56])
    axb = fig.add_axes([0.59, 0.40, 0.41, 0.56])
    axc = fig.add_axes([0.0, 0.0, 1.0, 0.33])
    for a in (axa, axb, axc):
        a.axis("off")
        a.set_xlim(0, 1)
        a.set_ylim(0, 1)
    panel_title(axa, "(a) One dense column j: %d storage cells, popcounts, "
                "shift-add" % n)
    panel_title(axb, "(b) One sidecar slot (K=%d per column)" % k)
    gw = grp["dense weight"]
    # (a) rows
    rows = [(0.86, "row 0"), (0.74, "row 1"), (0.56, "row %d" % (n - 1))]
    for yy, lab in rows:
        ax = axa
        ax.text(0.0, yy + 0.035, lab, fontsize=FS - 0.6, va="center")
        for b in range(wb):
            ff_sym(ax, 0.07 + b * 0.062, yy, 0.055, 0.07, "b%d" % (wb - 1 - b))
        and_sym(ax, 0.34, yy + 0.005, 0.045, 0.06, "x%d" % wb)
        poly(ax, [(0.07 + wb * 0.062 - 0.007, yy + 0.048),
                  (0.34, yy + 0.048)])
        poly(ax, [(0.30, yy - 0.012), (0.325, yy - 0.012),
                  (0.325, yy + 0.02), (0.34, yy + 0.02)], c=ACC)
        ax.text(0.30, yy - 0.012, "xbit[%s]" % lab.split()[1],
                fontsize=FS - 1.3, ha="right", va="center", color=ACC)
        poly(ax, [(0.385, yy + 0.035), (0.43, yy + 0.035)])
    axa.text(0.19, 0.665, r"$\vdots$", fontsize=8, ha="center")
    poly(axa, [(0.43, 0.595), (0.43, 0.895)], lw=2.0)
    axa.text(0.437, 0.91, "%d x %d\nproduct bits" % (n, wb), fontsize=FS - 1.2,
             ha="left", va="bottom")
    # popcounts
    for b in range(wb):
        yy = 0.86 - b * 0.085
        mux_sym(axa, 0.47, yy - 0.03, 0.09, 0.075, "pop%d\n%d->%d" %
                (b, n, p["POPW"]))
        poly(axa, [(0.43, yy + 0.008), (0.47, yy + 0.008)])
        poly(axa, [(0.56, yy + 0.008), (0.6, yy + 0.008)])
        axa.text(0.605, yy + 0.008, "<<%d" % b, fontsize=FS - 1.2, va="center")
        poly(axa, [(0.64, yy + 0.008), (0.66, yy + 0.008), (0.678, 0.73)])
    add_sym(axa, 0.70, 0.73, 0.022, "+")
    bus(axa, (0.722, 0.73), (0.798, 0.73), p["PARTW"], "part")
    add_sym(axa, 0.82, 0.73, 0.022, "+")
    ff_sym(axa, 0.87, 0.69, 0.10, 0.08, "acc %d b" % p["YW"], "dfxtp_2")
    arrow(axa, (0.842, 0.73), (0.87, 0.73))
    poly(axa, [(0.97, 0.73), (0.99, 0.73), (0.99, 0.62), (0.82, 0.62)])
    arrow(axa, (0.82, 0.62), (0.82, 0.69))
    axa.text(0.90, 0.605, "<<1 (shift-acc)", fontsize=FS - 1.2, ha="center",
             va="top")
    arrow(axa, (0.99, 0.73), (1.02, 0.73))
    axa.text(1.0, 0.75, "yd[j]", fontsize=FS - 1.0, ha="left")
    # bitcell detail
    box(axa, 0.0, 0.0, 1.0, 0.45, "", fc="white", ec=MID, ls="--", lw=0.7)
    axa.text(0.01, 0.44, "One weight bit as synthesized (final netlist, %s)"
             % os.path.basename(run), fontsize=FS - 0.4, va="top",
             weight="bold")
    # clock-gated storage: D = wd_q[b] directly, CLK from the row's ICG
    axa.text(0.0, 0.245, "wd_q[b]", fontsize=FS - 1.2, va="center")
    poly(axa, [(0.09, 0.245), (0.24, 0.245)])
    box(axa, 0.04, 0.06, 0.13, 0.12, "", fc=LGREY)
    axa.text(0.105, 0.12, "dlclkp_1\n(ICG, row i)", fontsize=FS - 1.6,
             ha="center", va="center", linespacing=1.0)
    poly(axa, [(0.0, 0.08), (0.04, 0.08)])
    axa.text(0.0, 0.07, "clk", fontsize=FS - 1.4, va="top")
    poly(axa, [(0.0, 0.155), (0.04, 0.155)])
    axa.text(0.0, 0.19, "en = we_q & row sel", fontsize=FS - 1.6,
             va="bottom")
    poly(axa, [(0.17, 0.12), (0.20, 0.12), (0.20, 0.16), (0.24, 0.16)])
    axa.text(0.205, 0.105, "gclk", fontsize=FS - 1.5, va="top")
    ff_sym(axa, 0.24, 0.13, 0.12, 0.15, "dfxtp_2", "D flip-flop")
    poly(axa, [(0.36, 0.205), (0.47, 0.205)])
    and_sym(axa, 0.47, 0.17, 0.06, 0.08)
    poly(axa, [(0.43, 0.185), (0.47, 0.185)], c=ACC)
    axa.text(0.43, 0.165, "xbit[i]", fontsize=FS - 1.4, color=ACC, ha="right",
             va="top")
    poly(axa, [(0.53, 0.21), (0.58, 0.21)])
    qs = [("%s %d" % (c, v)) for c, v in gw["q"].most_common(6)
          if c != "mux2"]
    axa.text(0.585, 0.40, "Clock-gated storage: %d of %d bits\nclocked "
             "through a dlclkp ICG\n(one per row), D straight from\nwd_q: "
             "mux2 on D in %d bits,\nhold delay gates on %d.\nAND w & "
             "xbit merged into the\nfirst popcount stage. Q fan-out:\n%s,\n"
             "%s." % (gw["clk"]["dlclkp"], gw["n"], gw["d"]["mux2"],
                      gw["hold"], ", ".join(qs[:3]), ", ".join(qs[3:])),
             fontsize=FS - 1.3, va="top", linespacing=1.15)
    # (b) sidecar slot
    ax = axb
    gi, gv = grp["slot index"], grp["slot value"]
    ff_sym(ax, 0.0, 0.80, 0.22, 0.09, "index %d b" % p["AW"], "dfxtp_2 x%d"
           % p["AW"], fc="#f6cdb5", ec=ACC)
    ff_sym(ax, 0.0, 0.52, 0.22, 0.09, "value %d b" % vb, "dfxtp_2 x%d" % vb,
           fc="#f6cdb5", ec=ACC)
    ax.text(0.11, 0.935, "slot s, column j", fontsize=FS - 1.0, ha="center")
    mux_sym(ax, 0.36, 0.64, 0.12, 0.26, "%d:1\nmux\n(mux4\ntree)" % n, ec=ACC,
            fs=FS - 1.0)
    ax.text(0.30, 0.86, "xbit\n/%d" % n, fontsize=FS - 1.2, ha="center",
            color=ACC, va="bottom")
    poly(ax, [(0.30, 0.86), (0.36, 0.84)], c=ACC)
    poly(ax, [(0.22, 0.845), (0.27, 0.845), (0.27, 0.61), (0.42, 0.61),
              (0.42, 0.665)], c=ACC)
    ax.text(0.28, 0.75, "sel", fontsize=FS - 1.4, color=ACC)
    and_sym(ax, 0.55, 0.53, 0.08, 0.11, "x%d" % vb, ec=ACC)
    poly(ax, [(0.48, 0.77), (0.52, 0.77), (0.52, 0.615), (0.55, 0.615)],
         c=ACC)
    ax.text(0.495, 0.79, "bit", fontsize=FS - 1.4, color=ACC)
    poly(ax, [(0.22, 0.565), (0.55, 0.565)], c=ACC)
    add_sym(ax, 0.72, 0.585, 0.03, "+", ec=ACC)
    poly(ax, [(0.63, 0.585), (0.69, 0.585)], c=ACC)
    ax.text(0.705, 0.49, "other %d\nslot(s)" % (k - 1), fontsize=FS - 1.4,
            ha="right", va="center", color=ACC)
    arrow(ax, (0.72, 0.47), (0.72, 0.53), c=ACC)
    add_sym(ax, 0.83, 0.585, 0.03, "+", ec=ACC)
    poly(ax, [(0.75, 0.585), (0.80, 0.585)], c=ACC)
    ax.text(0.775, 0.60, "%d" % (vb + clog2(k)), fontsize=FS - 1.4,
            color=ACC, ha="center", va="bottom")
    ff_sym(ax, 0.66, 0.30, 0.24, 0.09, "acc %d b signed" % p["SCW"],
           "dfxtp_2", fc="#fbe6da", ec=ACC)
    poly(ax, [(0.86, 0.585), (0.95, 0.585), (0.95, 0.345), (0.90, 0.345)],
         c=ACC)
    poly(ax, [(0.66, 0.345), (0.60, 0.345), (0.60, 0.42), (0.83, 0.42),
              (0.83, 0.53)], c=ACC)
    ax.text(0.62, 0.30, "<<1", fontsize=FS - 1.3, color=ACC, va="top")
    arrow(ax, (0.95, 0.345), (1.0, 0.345), c=ACC)
    ax.text(0.97, 0.36, "ys[j]", fontsize=FS - 1.2, color=ACC, va="bottom")
    qi = ", ".join("%s %d" % (c, v) for c, v in gi["q"].most_common(3))
    qv = ", ".join("%s %d" % (c, v) for c, v in gv["q"].most_common(4))
    ax.text(0.0, 0.25, "Final netlist: %d index + %d value flip-flops on "
            "the column's\ngated clock (%d + %d through a dlclkp ICG). Index "
            "bits drive the\nselect pins of the row-select tree (%s).\n"
            "Value bits feed %s;\nthe AND is merged into the adder's first "
            "stage." %
            (gi["n"], gv["n"], gi["clk"]["dlclkp"], gv["clk"]["dlclkp"],
             qi, qv),
            fontsize=FS - 1.3, va="top", linespacing=1.15)
    # (c) cell mix table
    panel_title(axc, "(c) Top-10 logic cells, final netlist of %s "
                "(results/cell_mix.csv)" % os.path.relpath(run, ROOT))
    rows = [["sky130_fd_sc_hd__" + c, "%d" % v, "%.1f" % (100 * v / tot),
             ROLE.get(base(c), "")] for c, v in top]
    rows.append(["all logic cells", "%d" % tot, "100.0",
                 "+ %d physical-only (decap, fill, tap, diode)" % phys])
    tb = axc.table(cellText=rows, colLabels=["cell", "count", "% of logic",
                                             "role in this design"],
                   colWidths=[0.27, 0.07, 0.08, 0.58], loc="upper left",
                   cellLoc="left", bbox=[0.0, 0.0, 1.0, 0.95])
    tb.auto_set_font_size(False)
    tb.set_fontsize(FS - 0.4)
    for (r_, c_), cell in tb.get_celld().items():
        cell.set_linewidth(0.4)
        cell.set_edgecolor("#999999")
        if r_ == 0:
            cell.set_text_props(weight="bold")
            cell.set_facecolor(LGREY)
    save(fig, "fig_arch_cell")


# ---------------------------------------------------------------- fig 3: VCD

def wave_bit(ax, xs, vs, y0, h=0.6, c=INK):
    px, py = [], []
    for i, (x, v) in enumerate(zip(xs, vs)):
        yy = y0 + (h if v == "1" else 0)
        if px:
            px.append(x)
            py.append(py[-1])
        px.append(x)
        py.append(yy)
    ax.plot(px, py, color=c, lw=0.9, solid_joinstyle="miter")


def wave_bus(ax, xs, vs, y0, fmt, h=0.6, c=INK, fill=None, minw=0.9,
             fs=FS - 0.6):
    """xs: segment starts (+ final end); vs: value per segment (None = blank)."""
    e = 0.12
    for x0, x1, v in zip(xs[:-1], xs[1:], vs):
        if v is None:
            ax.plot([x0, x1], [y0 + h / 2] * 2, color="#aaaaaa", lw=0.7)
            continue
        poly_ = [(x0, y0 + h / 2), (x0 + e, y0 + h), (x1 - e, y0 + h),
                 (x1, y0 + h / 2), (x1 - e, y0), (x0 + e, y0)]
        ax.add_patch(Polygon(poly_, closed=True, fc=fill or "white", ec=c,
                             lw=0.8, zorder=3))
        txt = fmt(v)
        if x1 - x0 >= minw and txt:
            ax.text((x0 + x1) / 2, y0 + h / 2, txt, ha="center", va="center",
                    fontsize=fs, zorder=4, color=c)


def fig_timing(p, vp=None):
    vp = vp or find_vcd()
    v = VCD(vp, {TOP + "." + s for s in SIGS})
    p = dict(p)
    if v.params.get("SBITS", p["SBW"]) != p["SBW"]:
        # narrower shift field (SBITS=3): S width and merged output width
        p["SBW"], p["YTW"] = v.params["SBITS"], v.params["YTW"]
    for q in ("N_IN", "N_OUT", "WBITS", "ABITS", "VB", "K", "YW", "SCW",
              "YTW", "SBW"):
        assert v.params[q] == p[q], (q, v.params[q], p[q])   # VCD = spec
    pipe = v.params.get("PIPE_MERGE", 0)
    edges, dots = replay(v, p)
    ab = p["ABITS"]
    nok = sum(d.get("ok", False) for d in dots)
    lat = Counter(d["lat"] for d in dots if "lat" in d)
    per = edges[1] - edges[0]
    show = dots[:2]
    pre, post = 1, ab + 1 + pipe
    FT = 8.5                     # printed at the full 7.16 in text width
    segs, off = [], 0.0
    for d in show:
        e0, e1 = d["start_edge"] - pre, d["start_edge"] + post
        segs.append((edges[e0], edges[e1], off, e0, e1))
        off += (edges[e1] - edges[e0]) / per + 2.2
    xmax = off - 2.2

    def X(t, seg):
        return (t - seg[0]) / per + seg[2]

    def changes(name, seg):
        ts, vs = v.tv[TOP + "." + name]
        i0 = bisect.bisect_right(ts, seg[0]) - 1
        i1 = bisect.bisect_right(ts, seg[1])
        tt = [seg[0]] + ts[i0 + 1:i1] + [seg[1]]
        vv = [vs[i0]] + vs[i0 + 1:i1]
        return [X(t, seg) for t in tt], vv

    def ival(s):
        return None if re.search("[xXzZ]", s) else int(s, 2)

    rows = [("clk", "clk", "bit"), ("rst", "rst", "bit"),
            ("w_load_en", "w_load_en", "bit"),
            ("s_load_en", "s_load_en", "bit"), ("start", "start", "bit"),
            ("busy", "busy", "bit"),
            ("bit-plane a", "u_dense.cnt", "cnt"),
            ("ones in xbit", "xbit", "hex"),
            ("dense valid", "d_valid", "bit"),
            ("sidecar valid", "s_valid", "bit"), ("valid", "valid", "bit"),
            ("y[0] (merged)", "y", "y0")]
    fig, ax = plt.subplots(figsize=(7.16, 3.75))
    fig.subplots_adjust(left=0.15, right=0.995, top=0.91, bottom=0.255)
    nr = len(rows)
    ytw = p["YTW"]
    for r_, (lab, sig, kind) in enumerate(rows):
        y0 = (nr - 1 - r_) * 1.0
        acc_c = ACC if lab.startswith("sidecar") else INK
        ax.text(-0.3, y0 + 0.3, lab, ha="right", va="center",
                fontsize=FT, color=acc_c)
        for seg in segs:
            xs, vs = changes(sig, seg)
            if kind == "bit":
                wave_bit(ax, xs + [xs[-1]], vs + [vs[-1]], y0, c=acc_c)
            elif kind == "cnt":
                bxs, bvs = changes("busy", seg)
                cut = sorted(set(xs[:-1] + bxs[:-1])) + [xs[-1]]
                vals = []
                for xx in cut[:-1]:
                    t = (xx - seg[2]) * per + seg[0] + 1
                    b_ = v.int_at(TOP + ".busy", t + 1)
                    c_ = v.int_at(TOP + ".u_dense.cnt", t + 1)
                    vals.append(c_ if b_ else None)
                wave_bus(ax, cut, vals, y0, lambda q: "a=%d" % q,
                         fs=FT - 0.5)
            elif kind == "hex":
                bxs, _ = changes("busy", seg)
                vals = []
                for xx in xs[:-1]:
                    t = (xx - seg[2]) * per + seg[0] + 1
                    vals.append(ival(v.at(TOP + ".xbit", t + 1))
                                if v.int_at(TOP + ".busy", t + 1) else None)
                # the 32-bit plane as its number of ones (decimal), readable
                wave_bus(ax, xs, vals, y0, lambda q: "%d" % bin(q).count("1"),
                         minw=0.9, fs=FT - 0.5)
            else:
                vals = []
                for s in vs:
                    q = ival(s)
                    vals.append(None if q is None else
                                sext(field(q, 0, ytw), ytw))
                vv = []
                for xx, q in zip(xs[:-1], vals):
                    t = (xx - seg[2]) * per + seg[0] + 1
                    ok = v.int_at(TOP + ".valid", t + 1)
                    vv.append(q if ok else None)
                wave_bus(ax, xs, vv, y0, lambda q: "%d" % q, minw=0.6,
                         fs=FT - 0.5)
    # gap marks
    for seg in segs[:-1]:
        xg = X(seg[1], seg) + 1.1
        ax.axvspan(xg - 0.9, xg + 0.9, color="white", zorder=5)
        skipped = segs[segs.index(seg) + 1][3] - seg[4]
        ax.text(xg, nr - 0.4, "//", ha="center", va="center", fontsize=FT,
                zorder=6)
        ax.text(xg, nr / 2, "%d\nedges\ncut\n(weight\nload)" % skipped,
                ha="center", va="center", fontsize=FT - 0.5, zorder=6)
    # latency annotations
    for d, seg in zip(show, segs):
        xs0 = X(edges[d["start_edge"]], seg)
        xv = X(edges[d["valid_edge"]], seg)
        for xx, c_ in ((xs0, MID), (xv, ACC)):
            ax.axvline(xx, color=c_, lw=0.6, ls=":", zorder=1)
        # phases: ABITS bit-planes through both paths, then the merge edge
        xa = X(edges[d["start_edge"] + ab], seg)
        phases = [(xs0, xa, "%d bit-planes" % ab, INK)]
        if pipe:
            phases.append((xa, xv, "merge", ACC))
        for x0_, x1_, lab_, c_ in phases:
            ax.annotate("", (x1_, nr + 0.05), (x0_, nr + 0.05),
                        arrowprops=dict(arrowstyle="<->", color=c_, lw=0.7,
                                        shrinkA=0, shrinkB=0))
            ax.text((x0_ + x1_) / 2, nr + 0.12, lab_, ha="center",
                    va="bottom", fontsize=FT - 0.5, color=c_)
    ax.set_xlim(-0.2, xmax + 0.2)
    ax.set_ylim(-0.25, nr + 0.6)
    ax.set_yticks([])
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    ticks, labs = [], []
    for seg in segs:
        for e in range(seg[3], seg[4] + 1):
            ticks.append(X(edges[e], seg))
            labs.append(str(e - show[segs.index(seg)]["start_edge"]))
    ax.set_xticks(ticks)
    ax.set_xticklabels(labs, fontsize=FT - 0.5)
    ax.set_xlabel("rising clock edges relative to the start edge k "
                  "(two consecutive 32x8 MVMs from the waveform)",
                  fontsize=FT)
    ax.tick_params(axis="x", length=2, width=0.5, pad=1.5)
    ax.spines["bottom"].set_linewidth(0.6)
    # the x-axis counts edges, so the testbench clock period (VCD time
    # stamps only) is not shown
    # the VCD checks (all MVMs equal golden) are stated in the caption
    save(fig, "fig_timing")
    return dict(vcd=vp, n=len(dots), ok=nok, lat=lat, show=show, per=per)


# ---------------------------------------------------------------- fig 4: flow

def tool_versions():
    src = open(os.path.join(ROOT, "docs", "references_verified.md")).read()
    pats = {"LibreLane": r"librelane \| V \| Version ([\d.]+)",
            "cocotb": r"cocotb \| V \| Version ([\d.]+)",
            "Icarus": r"icarus \| V\* \| Version ([\d.]+)",
            "Yosys": r"Yosys ([\d.]+) \(git",
            "OpenROAD": r"version = commit ([0-9a-f]+)",
            "Magic": r"Magic ([\d.]+)\s*\|",
            "KLayout": r"KLayout ([\d.]+)\s*\|",
            "Netgen": r"Netgen ([\d.]+)\s*\|"}
    out = {}
    for k_, rx in pats.items():
        mm = re.search(rx, src)
        out[k_] = mm.group(1) if mm else "?"
    return out


def test_counts():
    """Newest sign-off row of the primary build (sidecarcim_top, FF storage,
    PARALLEL=0): corners, random, real-layer, protocol + directed tests.
    Cases = corners + random + real-layer vectors."""
    src = open(os.path.join(ROOT, "tests", "report.md")).read()
    rows = []
    for line in src.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not line.startswith("|") or len(cells) < 5:
            continue
        lab = cells[0]
        if "PARALLEL=0" in lab and ("USE_LATCH=0" in lab or "FF" in lab) \
                and "spot" not in lab and "latch" not in lab.lower():
            rows.append(cells[1:])
    last = rows[-1]

    def passed(c):
        return sum(int(a.replace(",", "")) for a in
                   re.findall(r"([\d,]+)/[\d,]+", c))
    nums = [passed(c) for c in last[:3]]
    directed = sum(passed(c) for c in last[3:])
    return nums + [directed], sum(nums)


def fig_workflow(p):
    tv = tool_versions()
    parts, ntest = test_counts()
    fig = plt.figure(figsize=(7.16, 3.95))
    FW = 7.1                      # box text, printed at 7.16 in
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.16, 1.0)
    W, H = 0.153, 0.175
    xs = [0.002 + i * 0.1665 for i in range(6)]
    yt, ym, yr = 0.72, 0.41, 0.10

    def b(i, y, title, body, kind="logic"):
        gbox(ax, None, title, body, kind, sub=(xs[i], y, W, H), fs=FW)
        return (xs[i], y, W, H)

    def cen(bx, side):
        x, y, w, h = bx
        return {"l": (x, y + h / 2), "r": (x + w, y + h / 2),
                "t": (x + w / 2, y + h), "b": (x + w / 2, y)}[side]

    ax.text(0.005, 0.99, "Model side (python/; PyTorch + Hugging Face "
            "transformers)", fontsize=FW + 1.0, weight="bold", va="top")
    ax.text(0.005, yr + H + 0.03, "Hardware side\n(rtl/, tests/, flow/)",
            fontsize=FW + 1.0, weight="bold", va="bottom")
    m1 = b(0, yt, "HF model", "GPT-2 small,\nQwen2.5-0.5B")
    m2 = b(1, yt, "offline encode", "migration (alpha),\nMSE weight clip,\n"
           "top-K sidecar slots\n(llm_layer.encode)")
    m3 = b(2, yt, "integer forward", "llm_layer.int_forward;\nzero point "
           "and scale\nin software (quant.py)")
    m4 = b(3, yt, "perplexity", "WikiText-2\n(llm_layer.perplexity)")
    gv = b(1, ym, "test vectors", "python/vectors/*.npz\ncorners, random,\n"
           "real-layer tiles,\nexpected y from golden")
    gd = b(2, ym, "golden.py", "bit-exact integer\nreference: dcim_dot,\n"
           "sidecar_dot,\nsidecarcim_dot", "store")
    r1 = b(0, yr, "RTL", "Verilog-2005: top,\ndcim_core, dcim_8bit,\n"
           "mac_baseline")
    r2 = b(1, yr, "bit-exact RTL sim", "cocotb %s +\nIcarus %s\n%s cases\n"
           "(SidecarCIM, FF)" % (tv["cocotb"], tv["Icarus"],
                                 "{:,}".format(ntest)))
    r3 = b(2, yr, "LibreLane %s" % tv["LibreLane"], "SKY130A,\n"
           "sky130_fd_sc_hd;\nYosys %s,\nOpenROAD %s" % (tv["Yosys"],
                                                        tv["OpenROAD"][:7]))
    r4 = b(3, yr, "GDS sign-off", "DRC: Magic %s,\nKLayout %s\nLVS: Netgen "
           "%s" % (tv["Magic"], tv["KLayout"], tv["Netgen"]))
    r5 = b(4, yr, "gate-level VCD", "final-netlist sim\n(Icarus)")
    r6 = b(5, yr, "OpenSTA power", "post-layout\nestimate; area,\nfmax "
           "(ppa.csv)")
    for row in ((m1, m2, m3, m4), (r1, r2, r3, r4, r5, r6)):
        for a_, b_ in zip(row[:-1], row[1:]):
            arrow(ax, cen(a_, "r"), cen(b_, "l"))
    arrow(ax, cen(m2, "b"), cen(gv, "t"))
    ax.annotate("real-layer tiles", cen(m2, "b"), xytext=(3, -6),
                textcoords="offset points", fontsize=FW - 0.6, ha="left")
    arrow(ax, cen(gd, "l"), cen(gv, "r"))
    arrow(ax, cen(gv, "b"), cen(r2, "t"))

    def vlink(p0, p1, rad=0.0):
        ax.annotate("", p1, p0, arrowprops=dict(
            arrowstyle="<->", color=ACC, lw=1.4, ls="--", shrinkA=1,
            shrinkB=1, connectionstyle="arc3,rad=%g" % rad))

    # V1: golden <-> RTL sim
    vlink((gd[0] + W * 0.5, ym), (r2[0] + W * 0.85, yr + H))
    ax.text(gd[0] + W * 0.5 + 0.012, (ym + yr + H) / 2 + 0.005,
            "V1  RTL y = golden y\nfor every case", fontsize=FW - 0.2,
            color=ACC, weight="bold", ha="left", va="center")
    # V2: golden <-> integer LLM forward
    vlink((gd[0] + W * 0.5, ym + H), (m3[0] + W * 0.5, yt))
    ax.text(gd[0] + W * 0.5 + 0.012, (ym + H + yt) / 2,
            "V2  golden_check: integer parts of the LLM\nforward = golden "
            "dcim_dot / sidecar_dot, tile by tile", fontsize=FW - 0.2,
            color=ACC, weight="bold", ha="left", va="center")
    # V3: RTL <-> gate level
    vlink((r1[0] + W * 0.5, yr), (r5[0] + W * 0.5, yr), rad=0.12)
    ax.text((r1[0] + r5[0] + W) / 2, yr - 0.11, "V3  gate-level netlist y, "
            "busy, valid = RTL VCD at every edge (flow/gl_sim.py)",
            fontsize=FW - 0.2, color=ACC, ha="center", va="top",
            weight="bold")
    # join
    j = b(5, ym, "four-way\ncomparison", "", "store")
    ax.annotate("table_fourway", cen(j, "b"), xytext=(0, 3),
                textcoords="offset points", fontsize=FW - 0.6, ha="center",
                va="bottom")
    poly(ax, [cen(m4, "r"), (j[0] + W * 0.5, yt + H / 2)])
    arrow(ax, (j[0] + W * 0.5, yt + H / 2), cen(j, "t"))
    ax.annotate("accuracy", (j[0] + W * 0.5, yt + H / 2), xytext=(3, -12),
                textcoords="offset points", fontsize=FW - 0.6)
    arrow(ax, cen(r6, "t"), cen(j, "b"))
    ax.annotate("area, energy", cen(r6, "t"), xytext=(3, 3),
                textcoords="offset points", fontsize=FW - 0.6)
    save(fig, "fig_workflow")
    return tv, ntest


# ---------------------------------------------------------------- layouts

def die_um(row):
    """Die width, height in um: metrics.json of the run, else sqrt(area)."""
    mpath = os.path.join(ROOT, row["run_dir"], "final", "metrics.json")
    if os.path.exists(mpath):
        import json
        bb = json.load(open(mpath)).get("design__die__bbox")
        if bb:
            x0, y0, x1, y1 = (float(v) for v in bb.split())
            return x1 - x0, y1 - y0
    side = math.sqrt(float(row["die_area_um2"]))
    return side, side


def fig_layouts():
    """KLayout renders of six circuits at one common scale.

    Each results/gds/<design>_full.png shows the die on a black background;
    the non-black bounding box is the die (its aspect ratio is checked
    against the die from the run). Every panel spans the largest die, so
    the relative sizes are real; one scale bar per panel."""
    from PIL import Image
    rows = {r["design"]: r for r in csv.DictReader(
        open(os.path.join(HERE, "ppa.csv")))}
    order = [("mac_baseline", "(a) MAC baseline"),
             ("dcim_core_ff", "(b) W4A4 DCIM"),
             ("dcim_w6a4_ff", "(c) W6A4 DCIM"),
             ("sidecarcim_top_ff_pipe_s3", "(d) SidecarCIM"),
             ("dcim_w8a4_ff", "(e) W8A4 DCIM"),
             ("dcim_8bit_ff", "(f) W8A8 DCIM")]
    dies = {d: die_um(rows[d]) for d, _ in order}
    big = max(max(w, h) for w, h in dies.values())
    fig, axs = plt.subplots(1, len(order), figsize=(6.4, 1.62))
    fig.subplots_adjust(left=0.005, right=0.995, top=0.99, bottom=0.25,
                        wspace=0.06)
    for ax, (d, lab) in zip(axs, order):
        im = Image.open(os.path.join(HERE, "gds", d + "_full.png"))
        a = np.asarray(im.convert("RGB"))
        ys, xs = np.where((a.astype(int) > 20).any(2))
        crop = im.convert("RGB").crop((xs.min(), ys.min(), xs.max() + 1,
                                       ys.max() + 1))
        w, h = dies[d]
        assert abs(crop.size[0] / crop.size[1] - w / h) < 0.02, d
        px = int(round(420 * max(w, h) / big))       # same um per pixel
        crop = crop.resize((px, int(round(px * h / w))), Image.BOX)
        ax.imshow(np.asarray(crop), extent=(0, w, 0, h),
                  interpolation="nearest")
        ax.set_xlim(-0.02 * big, 1.02 * big)
        ax.set_ylim(-0.02 * big, 1.02 * big)
        ax.set_aspect("equal")
        ax.axis("off")
        if d == order[0][0]:      # one scale bar, in the smallest panel
            bar = 200.0
            ax.plot([0.05 * big, 0.05 * big + bar], [0.80 * big] * 2,
                    color="k", lw=2.0, solid_capstyle="butt")
            ax.text(0.05 * big, 0.84 * big, "%g um,\nall panels"
                    % bar, ha="left", va="bottom", fontsize=6.0)
        ax.text(0.5, -0.03, "%s\ndie %.0f x %.0f um\ncells %s um$^2$" %
                (lab, w, h, "{:,.0f}".format(float(rows[d]["area_um2"]))),
                transform=ax.transAxes, ha="center", va="top", fontsize=6.2,
                linespacing=1.1)
    save(fig, "fig_layouts")
    return dies


def main():
    style()
    p = params()
    fig_arch_priorart()
    d = fig_arch_baselines(p)
    fig_arch_block(p)
    run, nl, runs = newest_run()
    cnt, grp = netlist_stats(nl, p)
    top, tot, phys = write_cell_mix(cnt, None, run)
    fig_arch_cell(p, grp, top, tot, phys, run)
    tim = fig_timing(p)
    tv, ntest = fig_workflow(p)
    dies = fig_layouts()
    print("dies (um):", dies)
    print("netlist:", os.path.relpath(nl, ROOT))
    print("top10:", top, "logic", tot, "phys", phys)
    for g, e in grp.items():
        print(g, e["n"], "hold", e["hold"], dict(e["d"]),
              e["q"].most_common(5))
    print("timing:", tim["vcd"], tim["ok"], "/", tim["n"], dict(tim["lat"]))
    for dd in tim["show"]:
        print("  y0", dd["y"][0], "exp", dd["exp"][0], "yd", dd["yd"][0],
              "S", dd["S"][0], "ys", dd["ys"][0])
    print("tools:", tv, "cases:", ntest)
    print("designs:", {k_: (e["lat"], e["col"], e["tot"])
                       for k_, e in d.items()})


if __name__ == "__main__":
    main()

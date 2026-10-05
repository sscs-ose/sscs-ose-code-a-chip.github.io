"""
lut.py - gm/ID-style device characterisation of SKY130 nfet_01v8 / pfet_01v8 into a
lookup table, and interpolators over it. Methodology: Jespers & Murmann, "Systematic
Design of Analog CMOS Circuits Using Pre-Computed Lookup Tables" (CUP, 2017).
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import math, numpy as np, subprocess
from pathlib import Path
from scipy.interpolate import RegularGridInterpolator
import vga_flow as vf

W_REF = 5.0                                     # um; table is normalised per um of width
GRID = dict(
    L=[0.5, 1.0, 2.0],                          # um (design lengths are restricted to these)
    vgs=(0.0, 1.2, 0.005),                      # start, stop, step  [V]   (|Vsg| for pfet up to 1.8)
    vgs_p=(0.0, 1.8, 0.005),
    vds=(0.0, 1.8, 0.025),
    vsb=[0.0, 0.15, 0.3, 0.45, 0.6, 0.75],      # nfet only; pfet bodies sit at their source
)
PARS = ["id", "gm", "gds", "gmbs", "vth"]

def _deck(kind, L, vsb):
    m = f"msky130_fd_pr__{kind}_01v8"
    g = vf._geom(W_REF)
    if kind == "nfet":
        vg0, vg1, vgs = GRID["vgs"]
        dut = f"XM1 d g 0 b sky130_fd_pr__nfet_01v8 L={L} W={W_REF} nf=1 {g}\nVb b 0 {-vsb}"
        sw = f"dc Vg {vg0} {vg1} {vgs} Vd {GRID['vds'][0]} {GRID['vds'][1]} {GRID['vds'][2]}"
    else:  # pfet: source & body at 0, gate/drain swept negative -> report |Vsg|, |Vsd|
        vg0, vg1, vgs = GRID["vgs_p"]
        dut = f"XM1 d g 0 0 sky130_fd_pr__pfet_01v8 L={L} W={W_REF} nf=1 {g}"
        sw = f"dc Vg {-vg0} {-vg1} {-vgs} Vd {-GRID['vds'][0]} {-GRID['vds'][1]} {-GRID['vds'][2]}"
    saves = " ".join(f"@m.xm1.{m}[{p}]" for p in PARS)
    return f"""* LUT {kind} L={L} vsb={vsb}
.lib {vf.PDK_LIB} tt
{vf.SIM_OPTS}
Vg g 0 0
Vd d 0 0
{dut}
.control
save {saves}
{sw}
set wr_singlescale
set wr_vecnames
wrdata {vf.WORK}/lut_{kind}_{L}_{vsb}.txt {saves}
.endc"""

def sweep(kind, L, vsb):
    """One nested .dc sweep; returns dict of 2-D arrays indexed [vds, vgs]."""
    vf.run(_deck(kind, L, vsb), f"lut_{kind}")
    d = np.loadtxt(vf.WORK / f"lut_{kind}_{L}_{vsb}.txt", skiprows=1)
    g = GRID["vgs"] if kind == "nfet" else GRID["vgs_p"]
    nv = int(round((g[1] - g[0]) / g[2])) + 1
    nd = int(round((GRID["vds"][1] - GRID["vds"][0]) / GRID["vds"][2])) + 1
    cols = d[:, -len(PARS):]                     # last columns = saved vectors, in order
    out = {}
    for i, p in enumerate(PARS):
        a = cols[:, i].reshape(nd, nv)           # outer loop = Vd, inner = Vg
        out[p] = np.abs(a) if p in ("id", "gm", "gds", "gmbs", "vth") else a
    return out

def build(kinds=("nfet", "pfet"), verbose=True):
    """Run the full characterisation. Returns {kind: dict(arrays + axes)}."""
    lut = {}
    for kind in kinds:
        g = GRID["vgs"] if kind == "nfet" else GRID["vgs_p"]
        vgs = np.round(np.arange(g[0], g[1] + g[2] / 2, g[2]), 6)
        vds = np.round(np.arange(GRID["vds"][0], GRID["vds"][1] + GRID["vds"][2] / 2, GRID["vds"][2]), 6)
        vsbs = GRID["vsb"] if kind == "nfet" else [0.0]
        arr = {p: np.zeros((len(GRID["L"]), len(vsbs), len(vds), len(vgs)), np.float32) for p in PARS}
        for i, L in enumerate(GRID["L"]):
            for j, vsb in enumerate(vsbs):
                s = sweep(kind, L, vsb)
                for p in PARS: arr[p][i, j] = s[p]
                if verbose: print(f"  {kind} L={L} Vsb={vsb} done")
        lut[kind] = dict(L=np.array(GRID["L"]), vsb=np.array(vsbs), vds=vds, vgs=vgs, W_ref=W_REF, **arr)
    return lut

def save(lut, path):
    np.savez_compressed(path, **{f"{k}__{n}": v for k, d in lut.items() for n, v in d.items()})

def load(path):
    z = np.load(path); lut = {}
    for key in z.files:
        k, n = key.split("__"); lut.setdefault(k, {})[n] = z[key]
    return lut

class Device:
    """Interpolated device model at a fixed L. Inputs are |Vgs|, |Vds|, Vsb (V) and W (um).
    Current interpolated in log domain; gm, gds, gmbs interpolated as ratios to Id."""
    def __init__(self, lut, kind, L):
        d = lut[kind]; i = int(np.argmin(np.abs(d["L"] - L)))
        if abs(d["L"][i] - L) > 1e-9: raise ValueError(f"L={L} not on grid {d['L']}")
        idw = np.maximum(d["id"][i], 1e-30) / d["W_ref"]
        axes = (d["vsb"], d["vds"], d["vgs"]) if len(d["vsb"]) > 1 else (d["vds"], d["vgs"])
        sq = (lambda a: a) if len(d["vsb"]) > 1 else (lambda a: a[0])
        mk = lambda a: RegularGridInterpolator(axes, sq(a), bounds_error=False, fill_value=None)
        self.multi = len(d["vsb"]) > 1
        self._lid = mk(np.log(idw))
        self._gm, self._gds = mk(d["gm"][i] / np.maximum(d["id"][i], 1e-30)), mk(d["gds"][i] / np.maximum(d["id"][i], 1e-30))
        self._gmb = mk(d["gmbs"][i] / np.maximum(d["id"][i], 1e-30))
        self._vth = mk(d["vth"][i])
    def _pt(self, vgs, vds, vsb):
        return np.array([[vsb, vds, vgs] if self.multi else [vds, vgs]], dtype=float)
    @staticmethod
    def _f(interp, x):
        return float(np.ravel(interp(x))[0])
    def op(self, W, vgs, vds, vsb=0.0):
        x = self._pt(vgs, vds, vsb)
        i = W * math.exp(self._f(self._lid, x))
        return dict(id=i, gm=i * self._f(self._gm, x), gds=i * self._f(self._gds, x),
                    gmbs=i * self._f(self._gmb, x), vth=self._f(self._vth, x))
    def id(self, W, vgs, vds, vsb=0.0):
        return W * math.exp(self._f(self._lid, self._pt(vgs, vds, vsb)))

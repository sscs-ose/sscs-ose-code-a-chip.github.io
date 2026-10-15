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

W_REF = vf.W_F                                  # um; one finger. Table is stored per um of finger width; every
                                                # flow-sized device is an integer number of these fingers, so
                                                # scaling by width is exact (ngspice bins SKY130 models per finger)
GRID = dict(
    L=[0.5, 1.0, 2.0, 4.0, 8.0, 16.0],          # um (design lengths are restricted to these)
    vgs=(0.0, 1.2, 0.005),                      # start, stop, step  [V]   (|Vsg| for pfet up to 1.8)
    vgs_p=(0.0, 1.8, 0.005),
    vds=(0.0, 1.8, 0.025),
    vsb=[0.0, 0.15, 0.3, 0.45, 0.6, 0.75],      # nfet only; pfet bodies sit at their source
)
PARS = ["id", "gm", "gds", "gmbs", "vth"]
# Noise grid (Jespers & Murmann store thermal and flicker PSDs in the table as well). Drain-current noise is
# measured at V_SB = 0 and |V_DS| = NZ_VDS over a V_GS sweep, then stored normalised so that it depends only on the
# inversion level (g_m/I_D): S_th/I_D and S_fl(1 Hz)*W/I_D^2, with the flicker slope ef (S_fl ~ f^-ef).
NZ_VGS = dict(nfet=(0.15, 0.95, 0.01), pfet=(0.30, 1.20, 0.01))
NZ_VDS = 0.5
NZ_F = (1.0, 1e3, 1e6)          # flicker fitted between 1 Hz and 1 kHz; 1 MHz is thermal only
NZ_MIN_IDW = 1e-11              # A/um; noise data below this density is excluded (and clamped to its edge on lookup)
# Corner tables (ss, ff at 27 C; tt at -20 C and 85 C) let the evaluator predict the gate at every corner. They
# use a 2x coarser V_GS step (10 mV: interpolation error < 0.2 % in I_D, g_m, g_ds against the 5 mV table) and
# omit V_TH and noise (the noise gate is at tt), which halves their size; accuracy against SPICE: section 6.
GRID_CORNER = dict(GRID, vgs=(0.1, 1.0, 0.01), vgs_p=(0.3, 1.4, 0.01))   # the designs never leave these ranges
PARS_CORNER = ["id", "gm", "gds", "gmbs"]
# every process corner at 27 C, and every process corner at both temperature extremes (14 tables besides tt/27 C)
CORNERS = tuple((c, t) for t in (27, -20, 85) for c in ("tt", "ss", "ff", "sf", "fs") if (c, t) != ("tt", 27))
# Drain capacitance (for the output pole). Measured by a small-signal AC analysis at the drain of a one-finger and a
# two-finger device (gate, source and body AC-grounded, body at the source): a two-finger device shares one drain
# stripe between its two fingers, so C(nf) = m * (W_f/W_REF) * (n_d(nf) * a + nf * b), with n_d = (nf+1)//2 drain
# stripes - `a` is the per-stripe junction term, `b` the per-finger gate-side term (overlap, intrinsic, gate-edge
# sidewall). Solving the 1- and 2-finger measurements for a and b makes the model exact for every nf at that bias.
CAP_GRID = dict(vgs=(0.1, 1.0, 0.05), vgs_p=(0.3, 1.4, 0.05), vds=(0.1, 1.7, 0.1))
CAP_F = 1e5                     # Hz; far below every intrinsic time constant, far above the output pole's corner

def _deck(kind, L, vsb, corner="tt", temp=27, grid=GRID):
    GRID = grid
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
    return f"""* LUT {kind} L={L} vsb={vsb} {corner} {temp}C
.lib {vf.PDK_LIB} {corner}
{vf.SIM_OPTS}
.temp {temp}
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

def sweep(kind, L, vsb, corner="tt", temp=27, grid=GRID):
    """One nested .dc sweep; returns dict of 2-D arrays indexed [vds, vgs]."""
    GRID = grid
    vf.run(_deck(kind, L, vsb, corner, temp, grid), f"lut_{kind}")
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

def _noise_deck(kind, L, vgs_list):
    m = f"@m.xm1.msky130_fd_pr__{kind}_01v8"
    sgn = 1 if kind == "nfet" else -1
    g = vf._geom(W_REF)
    dut = (f"XM1 d g 0 0 sky130_fd_pr__{kind}_01v8 L={L} W={W_REF} nf=1 {g}")
    steps = []
    for k, v in enumerate(vgs_list):
        steps.append(f"alter vg dc = {sgn*v:.4f}\nop\nprint {m}[id] {m}[gm]\n"
                     f"noise v(out) vg dec 1 {NZ_F[0]:g} {NZ_F[2]:g}\nsetplot noise{2*k+1}\n"
                     f"print onoise_spectrum[0] onoise_spectrum[3] onoise_spectrum[6]")
    return f"""* noise LUT {kind} L={L}
.lib {vf.PDK_LIB} tt
{vf.SIM_OPTS}
Vg g 0 DC 0 AC 1
Vd d 0 {sgn*NZ_VDS}
{dut}
Hout out 0 Vd 1
.control
""" + "\n".join(steps) + "\n.endc"

def noise_sweep(kind, L):
    """Thermal and flicker drain-current noise of one finger versus V_GS (V_SB = 0, |V_DS| = NZ_VDS)."""
    import re
    a, b, st = NZ_VGS[kind]
    vgs = np.round(np.arange(a, b + st / 2, st), 4)
    out = vf.run(_noise_deck(kind, L, vgs), f"lutnz_{kind}")
    num = r"=\s*([-+]?[\d.]+(?:[eE][-+]?\d+)?)"
    ids = [abs(float(x)) for x in re.findall(r"\[id\]\s*" + num, out)]
    gms = [abs(float(x)) for x in re.findall(r"\[gm\]\s*" + num, out)]
    sp = [[float(x) for x in re.findall(r"onoise_spectrum\[%d\]\s*" % j + num, out)] for j in (0, 3, 6)]
    i, gm = np.array(ids), np.array(gms)
    s1, s3, s6 = (np.array(x) ** 2 for x in sp)          # A^2/Hz (1-ohm transimpedance)
    sth = s6
    fl1, fl3 = np.maximum(s1 - sth, 1e-60), np.maximum(s3 - sth, 1e-60)
    ef = np.log10(fl1 / fl3) / np.log10(NZ_F[1] / NZ_F[0])
    return dict(vgs=vgs, id=i, gm=gm, sth=sth, sfl1=fl1, ef=ef)

def _axis(t):
    return np.round(np.arange(t[0], t[1] + t[2] / 2, t[2]), 6)


def cap_sweep(kind, L, corner="tt", temp=27):
    """Drain capacitance of a one- and a two-finger device over (V_DS, V_GS), body at the source.
    Returns (a, b), each [vds, vgs] in F: per drain stripe and per finger (see CAP_GRID)."""
    import re
    sg = 1 if kind == "nfet" else -1
    vgs, vds = _axis(CAP_GRID["vgs"] if kind == "nfet" else CAP_GRID["vgs_p"]), _axis(CAP_GRID["vds"])
    C = {}
    for nf in (1, 2):
        W = W_REF * nf
        lines = [f"* cap {kind} L={L} nf={nf}", f".lib {vf.PDK_LIB} {corner}", vf.SIM_OPTS, f".temp {temp}",
                 "Vg g 0 DC 0", "Vd d 0 DC 0 AC 1",
                 f"XM1 d g 0 0 sky130_fd_pr__{kind}_01v8 L={L} W={W:g} nf={nf} {vf._geom(W, nf)}", ".control"]
        for i, vd in enumerate(vds):
            lines.append(f"alter vd dc = {sg*vd:.4f}")
            for j, vg in enumerate(vgs):
                lines += [f"alter vg dc = {sg*vg:.4f}", f"ac lin 1 {CAP_F:g} {CAP_F:g}",
                          f"print imag(i(vd))/{2*math.pi*CAP_F:.10g}"]
        lines.append(".endc")
        out = vf.run("\n".join(lines), f"cap_{kind}")
        v = [abs(float(x)) for x in re.findall(r"^imag\(i\(vd\)\)/\S+\s*=\s*([-+]?[\d.]+(?:[eE][-+]?\d+)?)", out, re.M)]
        if len(v) != len(vds) * len(vgs):
            raise RuntimeError(f"cap sweep {kind} L={L} nf={nf}: {len(v)} values, expected {len(vds)*len(vgs)}")
        C[nf] = np.array(v).reshape(len(vds), len(vgs))
    return 2 * C[1] - C[2], C[2] - C[1]


def build(kinds=("nfet", "pfet"), verbose=True, corner="tt", temp=27, grid=GRID, noise=True, pars=PARS, caps=True):
    """Run the full characterisation. Returns {kind: dict(arrays + axes)}."""
    GRID = grid
    lut = {}
    for kind in kinds:
        g = GRID["vgs"] if kind == "nfet" else GRID["vgs_p"]
        vgs = np.round(np.arange(g[0], g[1] + g[2] / 2, g[2]), 6)
        vds = np.round(np.arange(GRID["vds"][0], GRID["vds"][1] + GRID["vds"][2] / 2, GRID["vds"][2]), 6)
        vsbs = GRID["vsb"] if kind == "nfet" else [0.0]
        arr = {p: np.zeros((len(GRID["L"]), len(vsbs), len(vds), len(vgs)), np.float32) for p in pars}
        for i, L in enumerate(GRID["L"]):
            for j, vsb in enumerate(vsbs):
                s = sweep(kind, L, vsb, corner, temp, grid)
                for p in pars: arr[p][i, j] = s[p]
                if verbose: print(f"  {kind} L={L} Vsb={vsb} done")
        lut[kind] = dict(L=np.array(GRID["L"]), vsb=np.array(vsbs), vds=vds, vgs=vgs, W_ref=W_REF, **arr)
        if noise:
            nz = [noise_sweep(kind, L) for L in GRID["L"]]
            for key in ("vgs", "id", "gm", "sth", "sfl1", "ef"):
                lut[kind][f"nz_{key}"] = np.array([z[key] for z in nz], np.float64)
            if verbose: print(f"  {kind} noise done")
        if caps:
            ab = [cap_sweep(kind, L, corner, temp) for L in GRID["L"]]
            lut[kind].update(cap_vgs=_axis(CAP_GRID["vgs"] if kind == "nfet" else CAP_GRID["vgs_p"]),
                             cap_vds=_axis(CAP_GRID["vds"]), cap_a=np.array([x[0] for x in ab]),
                             cap_b=np.array([x[1] for x in ab]))
            if verbose: print(f"  {kind} drain capacitance done")
    return lut

def build_corners(corners=CORNERS, verbose=True, have=None):
    """{"ss_27": lut, ...}: the same characterisation at each process/temperature corner, coarser grid, no noise.
    `have`: tables already built (e.g. loaded from the cache); only the missing corners are characterised."""
    out = dict(have or {})
    for c, t in corners:
        if f"{c}_{t}" not in out:
            out[f"{c}_{t}"] = build(verbose=False, corner=c, temp=t, grid=GRID_CORNER, noise=False, pars=PARS_CORNER)
            if verbose: print(f"  corner table {c} {t} C done")
    return out

def save_corners(cl, path):
    np.savez_compressed(path, **{f"{c}__{k}__{n}": v for c, lut in cl.items() for k, d in lut.items() for n, v in d.items()})

def corners_current(path, corners=CORNERS, grid=GRID_CORNER):
    """True if the corner tables at `path` hold every corner in `corners`, on the grid and with the parameters
    build_corners() writes now. A table left by an older version of the flow (fewer corners, another grid) is stale."""
    try:
        cl = load_corners(path)
    except Exception:
        return False
    for c, t in corners:
        lut = cl.get(f"{c}_{t}")
        if not lut:
            return False
        for kind in ("nfet", "pfet"):
            d, g = lut.get(kind, {}), grid["vgs"] if kind == "nfet" else grid["vgs_p"]
            want = dict(L=np.array(grid["L"]), vsb=np.array(grid["vsb"] if kind == "nfet" else [0.0]),
                        vds=np.round(np.arange(grid["vds"][0], grid["vds"][1] + grid["vds"][2] / 2, grid["vds"][2]), 6),
                        vgs=np.round(np.arange(g[0], g[1] + g[2] / 2, g[2]), 6))
            if any(k not in d or np.shape(d[k]) != v.shape or not np.allclose(d[k], v) for k, v in want.items()):
                return False
            if any(p not in d for p in PARS_CORNER + ["cap_a", "cap_b"]):
                return False
    return True

def load_corners(path):
    z = np.load(path); out = {}
    for key in z.files:
        c, k, n = key.split("__"); out.setdefault(c, {}).setdefault(k, {})[n] = z[key]
    return out

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
        self.multi = len(d["vsb"]) > 1
        self._d, self._i, self._axes, self._ref = d, i, axes, None    # scipy reference built only on demand
        self._fast_init(d, i)
        self._nz = None
        if "nz_id" in d:          # noise vs current density per finger; the density fixes the inversion level
            idw = d["nz_id"][i] / d["W_ref"]
            ok = idw > NZ_MIN_IDW          # below this the extracted thermal floor is numerical, not physical
            x = np.log(idw[ok])
            self._nz = (x, d["nz_sth"][i][ok] / d["nz_id"][i][ok],
                        d["nz_sfl1"][i][ok] * d["W_ref"] / d["nz_id"][i][ok] ** 2, d["nz_ef"][i][ok])
        self._cap = None
        if "cap_a" in d:
            ax = (d["cap_vds"], d["cap_vgs"])
            self._cap = (ax, [(float(a[0]), float(a[1] - a[0]), len(a)) for a in ax],
                         d["cap_a"][i].tolist(), d["cap_b"][i].tolist())
    # Multilinear interpolation on the table's uniform axes, written out for scalar speed (the sweep calls it
    # millions of times). Outside the grid it extrapolates linearly from the edge cell, exactly as
    # scipy's RegularGridInterpolator(fill_value=None) does; the two agree to rounding (checked in section 5).
    def _fast_init(self, d, i):
        ax = [d["vds"], d["vgs"]] if not self.multi else [d["vsb"], d["vds"], d["vgs"]]
        self._ax = [(float(a[0]), float(a[1] - a[0]), len(a)) for a in ax]
        for a in ax:
            assert np.allclose(np.diff(a), a[1] - a[0]), "LUT axes must be uniform"
        idd = np.maximum(d["id"][i], 1e-30)
        q = [np.log(idd / d["W_ref"]), d["gm"][i] / idd, d["gds"][i] / idd, d["gmbs"][i] / idd,
             d["vth"][i] if "vth" in d else np.full_like(idd, np.nan)]
        if not self.multi:
            q = [x[0] for x in q]
        self._q = np.ascontiguousarray(np.stack(q), dtype=np.float64)     # [quantity, (vsb,) vds, vgs]
        self._qlist = self._q.tolist()
    def _w(self, vgs, vds, vsb):
        xs = (vds, vgs) if not self.multi else (vsb, vds, vgs)
        out = []
        for x, (x0, dx, n) in zip(xs, self._ax):
            t = (x - x0) / dx; k = int(math.floor(t))
            k = 0 if k < 0 else (n - 2 if k > n - 2 else k)
            out.append((k, t - k))
        return out
    def _get(self, qi, w):
        Q = self._qlist[qi]
        if not self.multi:
            (j, b), (k, c) = w
            r0, r1 = Q[j], Q[j + 1]
            return ((1 - b) * ((1 - c) * r0[k] + c * r0[k + 1]) + b * ((1 - c) * r1[k] + c * r1[k + 1]))
        (h, a), (j, b), (k, c) = w
        acc = 0.0
        for hh, wa in ((h, 1 - a), (h + 1, a)):
            P = Q[hh]; r0, r1 = P[j], P[j + 1]
            acc += wa * ((1 - b) * ((1 - c) * r0[k] + c * r0[k + 1]) + b * ((1 - c) * r1[k] + c * r1[k + 1]))
        return acc
    def op(self, W, vgs, vds, vsb=0.0):
        w = self._w(vgs, vds, vsb)
        i = W * math.exp(self._get(0, w))
        return dict(id=i, gm=i * self._get(1, w), gds=i * self._get(2, w), gmbs=i * self._get(3, w),
                    vth=self._get(4, w))
    def id(self, W, vgs, vds, vsb=0.0):
        return W * math.exp(self._get(0, self._w(vgs, vds, vsb)))
    def cdrain(self, W, nf, vgs, vds, m=1):
        """Small-signal capacitance at the drain (F) of m copies of an nf-finger device of total width W, gate,
        source and body AC-grounded, at |V_GS|, |V_DS| (clamped to the measured grid)."""
        if self._cap is None:
            raise ValueError("this LUT has no drain-capacitance data - rebuild it")
        _, ax, A, B = self._cap
        w = []
        for x, (x0, dx, n) in zip((vds, vgs), ax):
            t = min(max((x - x0) / dx, 0.0), n - 1 - 1e-9); k = int(t); w.append((k, t - k))
        (j, b), (k, c) = w
        bil = lambda Q: ((1 - b) * ((1 - c) * Q[j][k] + c * Q[j][k + 1]) + b * ((1 - c) * Q[j + 1][k] + c * Q[j + 1][k + 1]))
        nf = int(nf); nd = (nf + 1) // 2
        return m * (W / nf / W_REF) * (nd * bil(A) + nf * bil(B))
    # reference implementation (scipy), kept for the equivalence check
    def _pt(self, vgs, vds, vsb):
        return np.array([[vsb, vds, vgs] if self.multi else [vds, vgs]], dtype=float)
    @staticmethod
    def _f(interp, x):
        return float(np.ravel(interp(x))[0])
    def _build_ref(self):
        d, i, axes = self._d, self._i, self._axes
        sq = (lambda a: a) if self.multi else (lambda a: a[0])
        mk = lambda a: RegularGridInterpolator(axes, sq(a), bounds_error=False, fill_value=None)
        idd = np.maximum(d["id"][i], 1e-30)
        self._lid = mk(np.log(idd / d["W_ref"]))
        self._gm, self._gds, self._gmb = mk(d["gm"][i] / idd), mk(d["gds"][i] / idd), mk(d["gmbs"][i] / idd)
        self._vth = mk(d["vth"][i]); self._ref = True
    def op_ref(self, W, vgs, vds, vsb=0.0):
        if self._ref is None: self._build_ref()
        x = self._pt(vgs, vds, vsb)
        i = W * math.exp(self._f(self._lid, x))
        return dict(id=i, gm=i * self._f(self._gm, x), gds=i * self._f(self._gds, x),
                    gmbs=i * self._f(self._gmb, x), vth=self._f(self._vth, x))
    def noise(self, W, op):
        """Drain-current noise of a device of total width W at operating point `op`: thermal PSD (A^2/Hz), flicker
        PSD at 1 Hz (A^2/Hz) and flicker slope ef (S_fl ~ f^-ef). Looked up by current density I_D/W, which fixes
        the inversion level (and so carries the body effect); both PSDs scale exactly with the finger count."""
        if self._nz is None:
            raise ValueError("this LUT has no noise data - rebuild it")
        x, sth_n, sfl_n, ef = self._nz
        xi = math.log(max(op["id"] / W, 1e-30))
        f = lambda y: float(np.interp(xi, x, y))
        return dict(sth=f(sth_n) * op["id"], sfl1=f(sfl_n) * op["id"] ** 2 / W, ef=f(ef))


_DEV_CACHE = {}
def device(lut, kind, L):
    """Device objects are expensive to build (table re-layout); build each (table, kind, L) once."""
    key = (id(lut), kind, float(L))
    if key not in _DEV_CACHE:
        _DEV_CACHE[key] = Device(lut, kind, L)
    return _DEV_CACHE[key]


def density_vs_width(kind="nfet", L=1.0, vgs=0.45, vds=0.6, widths=(1, 2, 2.5, 4, 5, 7, 10, 20, 40, 80), fingered=(80, 16)):
    """SPICE drain current per um of width at a fixed bias, for single-finger devices of each width, plus one device of
    total width fingered[0] built from fingered[1] fingers. Shows why the table is characterised per finger."""
    import re
    sg = 1 if kind == "nfet" else -1
    devs = [(f"W{i}", w, 1) for i, w in enumerate(widths)] + [("F", fingered[0], fingered[1])]
    net = "\n".join(f"V{n} d{n} 0 {sg*vds}\nX{n} d{n} g 0 0 sky130_fd_pr__{kind}_01v8 L={L:g} W={w:g} nf={nf} "
                    f"{vf._geom(w, nf)}" for n, w, nf in devs)
    deck = f"""* density vs width
.lib {vf.PDK_LIB} tt
{vf.SIM_OPTS}
Vgate g 0 {sg*vgs}
{net}
.control
op
""" + "\n".join(f"print abs(i(V{n}))" for n, *_ in devs) + "\n.endc"
    r = vf.parse_print(vf.run(deck, "density"))
    cur = {n: r[f"abs(i(v{n.lower()}))"] for n, *_ in devs}
    return dict(kind=kind, L=L, vgs=vgs, vds=vds, widths=list(widths),
                density=[cur[f"W{i}"] / w for i, w in enumerate(widths)],
                fingered=dict(W=fingered[0], nf=fingered[1], density=cur["F"] / fingered[0]))

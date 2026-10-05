"""
evaluator.py - predicts the VGA core's operating point, gain, output resistance,
headroom and bandwidth from the gm/ID lookup table, with no SPICE in the loop.

Method:
 1. DC: solve the half-circuit KCL (tail, node_A, mirror node) with device currents
    interpolated from the LUT, including body effect (Vsb). With Vid = 0 the circuit
    is symmetric, so node_B = node_A and v_out = v_mirror (confirmed in SPICE to <0.1 mV).
 2. Small signal: assemble the full 5-node nodal (MNA) matrix from LUT gm, gds, gmbs and
    solve it for gain (Vid = 1) and output resistance (1 A injected at v_out).
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import math, numpy as np
from scipy.optimize import brentq
from lut import Device

class VGAModel:
    def __init__(self, lut, p):
        self.p = p
        self.nin  = Device(lut, "nfet", p["L_in"])
        self.nst  = Device(lut, "nfet", p["L_st"])
        self.ntl  = Device(lut, "nfet", p["L_tail"])
        self.pmir = Device(lut, "pfet", p["L_mir"])

    # ------------------------------------------------------------------ DC
    def dc(self, vctrl):
        p = self.p; vdd = p["vdd"]
        vcp, vcn = p["vctrl_cm"] + vctrl / 2, p["vctrl_cm"] - vctrl / 2
        def tail_for(vA):                       # v_tail such that I5 = 2*I2
            f = lambda vt: (self.ntl.id(p["W_tail"], p["vbias"], vt) -
                            2 * self.nin.id(p["W_in"], p["vin_cm"] - vt, vA - vt, vt))
            return brentq(f, 1e-4, min(vA, p["vin_cm"]) - 1e-4, xtol=1e-7)
        vm = vdd - 1.0
        for _ in range(30):
            def fA(vA):                          # I2(vA) - I6 - I7
                vt = tail_for(vA)
                i2 = self.nin.id(p["W_in"], p["vin_cm"] - vt, vA - vt, vt)
                i6 = self.nst.id(p["W_st"], vcp - vA, vm - vA, vA)
                i7 = self.nst.id(p["W_st"], vcn - vA, vdd - vA, vA)
                return math.log(i6 + i7) - math.log(i2)
            vA = brentq(fA, 0.02, min(vcp, vcn, vm) - 1e-3 if min(vcp, vcn, vm) > 0.05 else 0.04, xtol=1e-7)
            vt = tail_for(vA)
            i6 = self.nst.id(p["W_st"], vcp - vA, vm - vA, vA)
            fm = lambda v: math.log(self.pmir.id(p["W_mir"], vdd - v, vdd - v)) - math.log(i6)
            vm_new = brentq(fm, 1e-3, vdd - 1e-3, xtol=1e-7)
            if abs(vm_new - vm) < 1e-6: vm = vm_new; break
            vm = vm_new
        return dict(v_tail=vt, v_A=vA, v_B=vA, v_mir=vm, v_out=vm, vcp=vcp, vcn=vcn)

    # ------------------------------------------------------------------ small signal
    def _ops(self, s):
        p = self.p; vdd = p["vdd"]; vt, vA, vm = s["v_tail"], s["v_A"], s["v_mir"]
        o = {}
        o["m5"] = self.ntl.op(p["W_tail"], p["vbias"], vt, 0.0)
        o["m2"] = o["m3"] = self.nin.op(p["W_in"], p["vin_cm"] - vt, vA - vt, vt)
        o["m6"] = o["m9"] = self.nst.op(p["W_st"], s["vcp"] - vA, vm - vA, vA)
        o["m7"] = o["m8"] = self.nst.op(p["W_st"], s["vcn"] - vA, vdd - vA, vA)
        o["m1"] = o["m4"] = self.pmir.op(p["W_mir"], vdd - vm, vdd - vm)
        return o

    @staticmethod
    def _solve(o, vp, vn, itest):
        def kcl(v):
            t, A, B, m, out = v
            n = lambda d, vg, vd, vs: d["gm"] * (vg - vs) - d["gmbs"] * vs + d["gds"] * (vd - vs)
            i2, i3 = n(o["m2"], vp, A, t), n(o["m3"], vn, B, t)
            i5 = o["m5"]["gds"] * t
            i6, i7 = n(o["m6"], 0, m, A), n(o["m7"], 0, 0, A)
            i9, i8 = n(o["m9"], 0, out, B), n(o["m8"], 0, 0, B)
            i1 = -o["m1"]["gm"] * m - o["m1"]["gds"] * m          # into mirror node
            i4 = -o["m4"]["gm"] * m - o["m4"]["gds"] * out        # into v_out
            return np.array([i2 + i3 - i5, i6 + i7 - i2, i9 + i8 - i3, i1 - i6, i4 + itest - i9])
        b0 = kcl(np.zeros(5))
        M = np.column_stack([kcl(e) - b0 for e in np.eye(5)])
        return np.linalg.solve(M, -b0)

    def evaluate(self, vctrl, CL=1e-12):
        s = self.dc(vctrl); o = self._ops(s); p = self.p
        av = self._solve(o, 0.5, -0.5, 0.0)[4]
        rout = self._solve(o, 0.0, 0.0, 1.0)[4]
        vds = dict(m2=s["v_A"] - s["v_tail"], m6=s["v_mir"] - s["v_A"], m9=s["v_out"] - s["v_B"],
                   m5=s["v_tail"], m7=p["vdd"] - s["v_A"])
        i6, i7 = o["m6"]["id"], o["m7"]["id"]
        alpha = i6 / (i6 + i7)
        # textbook estimate: steering split x input gm x (ro4 || ro9), i.e. M9 treated as a plain ro
        naive = alpha * o["m2"]["gm"] / (o["m4"]["gds"] + o["m9"]["gds"])
        return dict(vctrl=vctrl, av=av, av_db=20 * math.log10(abs(av)), rout=rout, naive_av=naive,
                    naive_av_db=20 * math.log10(naive),
                    f3db=(1 / (2 * math.pi * rout * CL)) if rout > 0 else float("nan"), i_tot=o["m5"]["id"], power=p["vdd"] * o["m5"]["id"],
                    alpha=alpha, gm_in=o["m2"]["gm"], vov_in=(p["vin_cm"] - s["v_tail"]) - o["m2"]["vth"],
                    vds_min=min(vds.values()), **{f"vds_{k}": v for k, v in vds.items()}, **s)

def evaluate_design(lut, p, v_lo=0.0, v_hi=0.3, CL=1e-12):
    """Both control endpoints -> one summary row (the objective/constraint vector)."""
    m = VGAModel(lut, p); a, b = m.evaluate(v_lo, CL), m.evaluate(v_hi, CL)
    return dict(av_lo_db=a["av_db"], av_hi_db=b["av_db"], range_db=b["av_db"] - a["av_db"],
                f3db_hi=b["f3db"], f3db_lo=a["f3db"], i_tot=a["i_tot"], power=a["power"],
                vds_min=min(a["vds_min"], b["vds_min"]), vov_in=a["vov_in"],
                rout_lo=a["rout"], rout_hi=b["rout"], area_in=p["W_in"] * p["L_in"])

# ---------------------------------------------------------------------- design space
SPACE = dict(
    W_in=[10.0, 20.0, 40.0, 80.0], L_in=[1.0, 2.0],
    W_st=[2.5, 5.0, 10.0],         L_st=[1.0, 2.0],
    W_mir=[2.5, 5.0, 10.0],        L_mir=[1.0, 2.0],
    vctrl_cm=[1.05, 1.10, 1.15, 1.20, 1.25],
    vbias=[0.59, 0.61, 0.63],
)
VDS_MIN_LUT = 0.140   # 130 mV SPICE target + 10 mV LUT margin (see validation table)
I_TOT_MAX = 5e-6

_LUT = None
def _init(path):
    global _LUT
    import lut as _l; _LUT = _l.load(path)

def _eval_one(p):
    try:
        r = evaluate_design(_LUT, p); r.update(p); r["ok"] = True
    except Exception as e:
        r = dict(p); r["ok"] = False; r["err"] = str(e)[:80]
    return r

def sweep(lut_path, base, space=SPACE, procs=None):
    import itertools, multiprocessing as mp, pandas as pd
    keys = list(space); pts = []
    for combo in itertools.product(*space.values()):
        p = dict(base); p.update(dict(zip(keys, combo))); pts.append(p)
    with mp.Pool(procs, initializer=_init, initargs=(str(lut_path),)) as pool:
        rows = pool.map(_eval_one, pts, chunksize=16)
    df = pd.DataFrame(rows)
    df["feasible"] = df["ok"] & (df["vds_min"] >= VDS_MIN_LUT) & (df["i_tot"] <= I_TOT_MAX) & (df["vov_in"] <= 0)
    return df

def pareto(df, maximize=("range_db", "f3db_hi"), minimize=("power",)):
    """Non-dominated subset of the feasible designs."""
    f = df[df["feasible"]].copy()
    X = np.column_stack([-f[c].values for c in maximize] + [f[c].values for c in minimize])
    keep = np.ones(len(f), bool)
    for i in range(len(f)):
        if keep[i]:
            dom = np.all(X <= X[i], axis=1) & np.any(X < X[i], axis=1)
            if dom.any(): keep[i] = False
    return f[keep].sort_values("range_db", ascending=False)

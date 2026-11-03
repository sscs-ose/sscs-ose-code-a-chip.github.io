"""
evaluator.py - predicts the VGA core's operating point, gain, output resistance, bandwidth, headroom and
input-referred noise from the gm/ID lookup table, with no SPICE in the loop.

Two topologies share one model:
  9T  - current-mirror OTA (M1-M5) + current-steering stage (M6-M9); tail gate at a fixed voltage V_bias.
  12T - the 9T plus keep-alive sinks M10 (mirror node) and M11 (output), with the tail and both sinks mirrored
        from an external reference current through the diode-connected M12. In the flow form all four are copies
        of one unit device (W_u x L_u), so every ratio is an integer multiplicity.

Method:
 1. DC: with v_id = 0 the core is symmetric (node B = node A, v_out = mirror node; confirmed in SPICE to < 0.1 mV).
    KCL at the tail, node A and the mirror node is solved with device currents interpolated from the LUT at each
    device's (V_GS, V_DS, V_SB). In the 12T the bias voltage is first solved from I_D(M12) = I_ref.
 2. Small signal: LUT g_m, g_ds, g_mb populate the nodal (MNA) matrix of the full circuit - tail, A, B, mirror,
    output, and the bias node in the 12T. Solving it with v_id = 1 gives A_v; with 1 A injected at the output, R_out.
    The output pole uses the load plus the drain capacitance of M4, M9 and M11, from the table at their bias.
 3. Noise: each device's drain-current noise (thermal + flicker, from the LUT) is injected drain-to-source in turn;
    the same matrix gives its transimpedance to the output. Contributions add in power and are referred to the
    input through A_v. All poles are far above the audio band except the output pole, which the signal and every
    noise source share, so the input-referred spectrum follows from the low-frequency transfers alone.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import math, numpy as np
from pathlib import Path
from scipy.optimize import brentq
from lut import device as Device   # cached factory
import vga_flow as vf

GROUPS = ("in", "st", "mir")          # device groups sized by width (finger count) and length
# Local mismatch of an nfet in weak/moderate inversion, from the PDK's mismatch model (sky130_fd_pr__nfet_01v8__
# mismatch.corner.spice, bins used here): V_TH0 and V_OFF both shift the subthreshold current like a threshold
# shift, so they add in power; T_OX's effect on the current is two orders smaller and is left out. V*um.
NFET_VT_SLOPE = (3.356e-3 ** 2 + 7.0e-3 ** 2) ** 0.5


def finger_exact(p) -> bool:
    """True when every width-sized device is a whole number of W_F fingers - the LUT is then exact for it."""
    ok = all(abs(p[f"W_{g}"] / vf.nf_of(p, g) - vf.W_F) < 1e-9 for g in GROUPS)
    if vf.bias_mode(p) == "unit":
        ok = ok and abs(p.get("W_u", vf.W_F) / vf.nf_of(p, "u") - vf.W_F) < 1e-9
    if vf.bias_mode(p) == "voltage":
        ok = ok and abs(p["W_tail"] / vf.nf_of(p, "tail") - vf.W_F) < 1e-9
    return ok


class VGAModel:
    def __init__(self, lut, p):
        self.p = p
        self.mode = vf.bias_mode(p)
        if self.mode == "legacy":
            raise ValueError("the 8 Oct hand-screen bias (separately sized reference/sinks) is SPICE-only")
        self.nin = Device(lut, "nfet", p["L_in"])
        self.nst = Device(lut, "nfet", p["L_st"])
        self.pmir = Device(lut, "pfet", p["L_mir"])
        if self.mode == "unit":
            self.ntl = Device(lut, "nfet", p["L_u"])
            self.W_u = p.get("W_u", vf.W_F)
            self.W_tail = self.W_u * p["m_tail"]
            self.W_sink = self.W_u * p.get("m_sink", 0)
            self.vbias = brentq(lambda v: math.log(self.ntl.id(self.W_u, v, v)) - math.log(p["iref"]),
                                0.02, 1.4, xtol=1e-8)
            o12 = self.ntl.op(self.W_u, self.vbias, self.vbias)
            self.gmid_u = o12["gm"] / o12["id"]
        else:
            self.ntl = Device(lut, "nfet", p["L_tail"])
            self.W_tail, self.W_sink, self.vbias = p["W_tail"], 0.0, p["vbias"]

    # ------------------------------------------------------------------ DC
    def _isink(self, v):
        return self.ntl.id(self.W_sink, self.vbias, v) if self.W_sink else 0.0

    def _resid(self, x, vcp, vcn):
        p = self.p; vdd, vb = p["vdd"], self.vbias
        vt, vA, vm = x
        lg = math.log
        i5 = self.ntl.id(self.W_tail, vb, vt)
        i2 = self.nin.id(p["W_in"], p["vin_cm"] - vt, vA - vt, vt)
        i6 = self.nst.id(p["W_st"], vcp - vA, vm - vA, vA)
        i7 = self.nst.id(p["W_st"], vcn - vA, vdd - vA, vA)
        i1 = self.pmir.id(p["W_mir"], vdd - vm, vdd - vm)
        return [lg(i5) - lg(2 * i2), lg(i2) - lg(i6 + i7), lg(i1) - lg(i6 + self._isink(vm))]

    def _newton(self, x0, vcp, vcn, tol=1e-10, itmax=40):
        x = list(x0); r = self._resid(x, vcp, vcn)
        for _ in range(itmax):
            if max(abs(v) for v in r) < tol:
                return x
            h = 1e-6; J = np.empty((3, 3))
            for j in range(3):
                xp = list(x); xp[j] += h
                J[:, j] = (np.array(self._resid(xp, vcp, vcn)) - r) / h
            try:
                dx = np.linalg.solve(J, -np.array(r))
            except np.linalg.LinAlgError:
                return None
            lam = 1.0
            n0 = max(abs(v) for v in r)
            while lam > 1e-3:                       # backtracking: accept the first step that reduces the residual
                xn = [x[k] + lam * dx[k] for k in range(3)]
                if 0 < xn[0] < xn[1] < xn[2] < self.p["vdd"]:
                    rn = self._resid(xn, vcp, vcn)
                    if max(abs(v) for v in rn) < n0:
                        x, r = xn, rn; break
                lam *= 0.5
            else:
                return None
        return x if max(abs(v) for v in r) < 1e-7 else None

    def _dc_bracket(self, vcp, vcn):
        """Robust nested-bracket solve (the original method): slow but always converges."""
        p = self.p; vdd, vb = p["vdd"], self.vbias
        def tail_for(vA):                       # v_tail such that I5 = 2*I2
            f = lambda vt: (math.log(self.ntl.id(self.W_tail, vb, vt)) -
                            math.log(2 * self.nin.id(p["W_in"], p["vin_cm"] - vt, vA - vt, vt)))
            return brentq(f, 1e-4, min(vA, p["vin_cm"]) - 1e-4, xtol=1e-9)
        vm = vdd - 1.0
        for _ in range(60):
            def fA(vA):                          # I2(vA) - I6 - I7
                vt = tail_for(vA)
                i2 = self.nin.id(p["W_in"], p["vin_cm"] - vt, vA - vt, vt)
                i6 = self.nst.id(p["W_st"], vcp - vA, vm - vA, vA)
                i7 = self.nst.id(p["W_st"], vcn - vA, vdd - vA, vA)
                return math.log(i6 + i7) - math.log(i2)
            top = min(vcp, vcn, vm) - 1e-3
            vA = brentq(fA, 0.02, top if top > 0.05 else 0.04, xtol=1e-9)
            vt = tail_for(vA)
            i6 = self.nst.id(p["W_st"], vcp - vA, vm - vA, vA)
            fm = lambda v: math.log(self.pmir.id(p["W_mir"], vdd - v, vdd - v)) - math.log(i6 + self._isink(v))
            vm_new = brentq(fm, 1e-3, vdd - 1e-3, xtol=1e-9)
            if abs(vm_new - vm) < 1e-8:
                vm = vm_new; break
            vm = vm_new
        return [vt, vA, vm]

    def dc(self, vctrl, guess=None):
        p = self.p
        vcp, vcn = p["vctrl_cm"] + vctrl / 2, p["vctrl_cm"] - vctrl / 2
        x = self._newton(guess, vcp, vcn) if guess is not None else None
        if x is None:
            x = self._dc_bracket(vcp, vcn)
            x = self._newton(x, vcp, vcn) or x     # polish
        vt, vA, vm = x
        return dict(v_tail=vt, v_A=vA, v_B=vA, v_mir=vm, v_out=vm, v_bias=self.vbias, vcp=vcp, vcn=vcn)

    # ------------------------------------------------------------------ small signal
    def _ops(self, s):
        p = self.p; vdd = p["vdd"]; vt, vA, vm, vb = s["v_tail"], s["v_A"], s["v_mir"], s["v_bias"]
        o = {}
        o["m5"] = self.ntl.op(self.W_tail, vb, vt, 0.0)
        o["m2"] = o["m3"] = self.nin.op(p["W_in"], p["vin_cm"] - vt, vA - vt, vt)
        o["m6"] = o["m9"] = self.nst.op(p["W_st"], s["vcp"] - vA, vm - vA, vA)
        o["m7"] = o["m8"] = self.nst.op(p["W_st"], s["vcn"] - vA, vdd - vA, vA)
        o["m1"] = o["m4"] = self.pmir.op(p["W_mir"], vdd - vm, vdd - vm)
        if self.W_sink:
            o["m10"] = o["m11"] = self.ntl.op(self.W_sink, vb, vm, 0.0)
        if self.mode == "unit":
            o["m12"] = self.ntl.op(self.W_u, vb, vb, 0.0)
        return o

    # (drain, gate, source, kind) for every device; 'vdd', 'gnd', 'cp', 'cn' are AC ground, 'inp'/'inn' the input
    TOPO = {"m1": ("m", "m", "vdd", "p"), "m4": ("out", "m", "vdd", "p"),
            "m2": ("A", "inp", "t", "n"), "m3": ("B", "inn", "t", "n"), "m5": ("t", "vb", "gnd", "n"),
            "m6": ("m", "cp", "A", "n"), "m7": ("vdd", "cn", "A", "n"),
            "m8": ("vdd", "cn", "B", "n"), "m9": ("out", "cp", "B", "n"),
            "m10": ("m", "vb", "gnd", "n"), "m11": ("out", "vb", "gnd", "n"), "m12": ("vb", "vb", "gnd", "n")}

    def _nodes(self):
        return ["t", "A", "B", "m", "out"] + (["vb"] if self.mode == "unit" else [])

    def _system(self, o):
        """Nodal matrix G (unknown nodes) and the input vector for v_id = 1, from the device stamps."""
        nodes = self._nodes(); ix = {n: i for i, n in enumerate(nodes)}; n = len(nodes)
        G = np.zeros((n, n)); bin_ = np.zeros(n)
        inp = {"inp": 0.5, "inn": -0.5}
        for name, d in o.items():
            dn, gn, sn, kind = self.TOPO[name]
            # branch current (n: drain->source; p: into drain) as coefficients on node voltages
            if kind == "n":     # a list, not a dict: a diode-connected device has gate == drain
                coef = [(gn, d["gm"]), (sn, -(d["gm"] + d["gmbs"] + d["gds"])), (dn, d["gds"])]
                out_of, into = dn, sn
            else:
                coef = [(gn, -d["gm"]), (dn, -d["gds"])]
                out_of, into = None, dn
            for node, c in coef:
                for tgt, sgn in ((out_of, -1.0), (into, 1.0)):
                    if tgt in ix:
                        if node in ix:
                            G[ix[tgt], ix[node]] += sgn * c
                        elif node in inp:
                            bin_[ix[tgt]] += sgn * c * inp[node]
        return nodes, ix, G, bin_

    def _solve(self, o, vid=0.0, itest=0.0, inject=None):
        """Node voltages for a differential input vid, a test current itest into the output, or a 1 A
        drain-to-source noise current in device `inject`."""
        nodes, ix, G, bin_ = self._system(o)
        rhs = -vid * bin_
        rhs[ix["out"]] -= itest
        if inject:
            dn, gn, sn, kind = self.TOPO[inject]
            if kind == "n":
                if dn in ix: rhs[ix[dn]] += 1.0
                if sn in ix: rhs[ix[sn]] -= 1.0
            elif dn in ix:
                rhs[ix[dn]] -= 1.0
        x = np.linalg.solve(G, rhs)
        return {n: x[i] for i, n in enumerate(nodes)}

    def _transfers(self, o, devices):
        """Gain, output resistance and every device's noise transimpedance to the output, from one factorisation."""
        nodes, ix, G, bin_ = self._system(o)
        cols = [-bin_, np.eye(len(nodes))[ix["out"]] * -1.0]
        for name in devices:
            dn, gn, sn, kind = self.TOPO[name]; r = np.zeros(len(nodes))
            if kind == "n":
                if dn in ix: r[ix[dn]] += 1.0
                if sn in ix: r[ix[sn]] -= 1.0
            elif dn in ix:
                r[ix[dn]] -= 1.0
            cols.append(r)
        X = np.linalg.solve(G, np.column_stack(cols))
        k = ix["out"]
        return X[k, 0], X[k, 1], {name: X[k, 2 + j] for j, name in enumerate(devices)}

    def _noise_devices(self):
        p = self.p
        dev = {"m1": (self.pmir, p["W_mir"]), "m4": (self.pmir, p["W_mir"]),
               "m2": (self.nin, p["W_in"]), "m3": (self.nin, p["W_in"]), "m5": (self.ntl, self.W_tail),
               "m6": (self.nst, p["W_st"]), "m7": (self.nst, p["W_st"]), "m8": (self.nst, p["W_st"]),
               "m9": (self.nst, p["W_st"])}
        if self.W_sink:
            dev.update({"m10": (self.ntl, self.W_sink), "m11": (self.ntl, self.W_sink)})
        if self.mode == "unit":
            dev["m12"] = (self.ntl, self.W_u)
        return dev

    def noise(self, o, av, f1=20.0, f2=20e3, f_spot=1e3, z=None):
        """Input-referred noise: integrated over [f1, f2] (V rms), spot density at f_spot (V/sqrt(Hz)), and the
        per-device share of the integrated power. z: precomputed noise transimpedances (from _transfers)."""
        p = self.p
        dev = {"m1": (self.pmir, p["W_mir"]), "m4": (self.pmir, p["W_mir"]),
               "m2": (self.nin, p["W_in"]), "m3": (self.nin, p["W_in"]), "m5": (self.ntl, self.W_tail),
               "m6": (self.nst, p["W_st"]), "m7": (self.nst, p["W_st"]), "m8": (self.nst, p["W_st"]),
               "m9": (self.nst, p["W_st"])}
        if self.W_sink:
            dev.update({"m10": (self.ntl, self.W_sink), "m11": (self.ntl, self.W_sink)})
        if self.mode == "unit":
            dev["m12"] = (self.ntl, self.W_u)
        tot, spot, share, th = 0.0, 0.0, {}, 0.0
        for name, (D, W) in dev.items():
            zk = (z[name] if z is not None else self._solve(o, inject=name)["out"]) / av   # input-referred, V/A
            nz = D.noise(W, o[name]); ef = nz["ef"]
            fl_int = (f2 ** (1 - ef) - f1 ** (1 - ef)) / (1 - ef) if abs(ef - 1) > 1e-6 else math.log(f2 / f1)
            pw = zk * zk * (nz["sth"] * (f2 - f1) + nz["sfl1"] * fl_int)
            share[name] = pw; tot += pw; th += zk * zk * nz["sth"]
            spot += zk * zk * (nz["sth"] + nz["sfl1"] * f_spot ** (-ef))
        return dict(vrms=math.sqrt(tot), vn_spot=math.sqrt(spot), share={k: v / tot for k, v in share.items()},
                    vn_th=math.sqrt(th), vrms_th=math.sqrt(th * (f2 - f1)))

    def i_sigma(self, i_tot):
        """Relative one-sigma spread of the supply current from local mismatch of the bias units. Every copy carries
        I_ref (1 + gm/I_D * (dV_12 - dV_k)); the reference's shift dV_12 is common to all N copies, each copy group's
        own shifts average over its m units:  sigma(I)/I_unit = gm/I_D * sigma_u * sqrt(N^2 + N),
        sigma_u = NFET_VT_SLOPE / sqrt(W_u L_u). Zero for the voltage-biased 9T (its tail current has no mirror)."""
        if self.mode != "unit":
            return 0.0
        p = self.p; N = p["m_tail"] + 2 * p.get("m_sink", 0)
        su = NFET_VT_SLOPE / math.sqrt(self.W_u * p["L_u"])
        return math.sqrt(N * N + N) * self.gmid_u * su * p["iref"] / i_tot

    def c_out(self, s, CL):
        """Capacitance on v_out: the load plus the drains of M4, M9 and M11 at their operating points (tables
        built without drain-capacitance data give the load alone)."""
        p = self.p; vdd = p["vdd"]; c = CL
        if self.pmir._cap is None:
            return c
        c += self.pmir.cdrain(p["W_mir"], vf.nf_of(p, "mir"), vdd - s["v_mir"], vdd - s["v_out"])
        c += self.nst.cdrain(p["W_st"], vf.nf_of(p, "st"), s["vcp"] - s["v_B"], s["v_out"] - s["v_B"])
        if self.W_sink:
            c += self.ntl.cdrain(self.W_u, vf.nf_of(p, "u"), self.vbias, s["v_out"], m=p["m_sink"])
        return c

    def evaluate(self, vctrl, CL=1e-12, with_noise=False, guess=None, band=(20.0, 20e3)):
        s = self.dc(vctrl, guess); o = self._ops(s); p = self.p
        cout = self.c_out(s, CL)
        devs = list(self._noise_devices()) if with_noise else []
        av, rout, z = self._transfers(o, devs)
        vds = dict(m2=s["v_A"] - s["v_tail"], m6=s["v_mir"] - s["v_A"], m9=s["v_out"] - s["v_B"],
                   m5=s["v_tail"], m7=p["vdd"] - s["v_A"])
        i6, i7 = o["m6"]["id"], o["m7"]["id"]
        alpha = i6 / (i6 + i7)
        naive = alpha * o["m2"]["gm"] / (o["m4"]["gds"] + o["m9"]["gds"])   # textbook: M9 treated as a plain r_o
        i_tot = o["m5"]["id"] + (2 * o["m10"]["id"] if self.W_sink else 0.0) + (p["iref"] if self.mode == "unit" else 0.0)
        r = dict(vctrl=vctrl, av=av, av_db=20 * math.log10(abs(av)), rout=rout, naive_av=naive,
                 naive_av_db=20 * math.log10(naive), f3db=(1 / (2 * math.pi * rout * cout)) if rout > 0 else float("nan"),
                 c_out=cout,
                 i_tot=i_tot, power=p["vdd"] * i_tot, i_tail=o["m5"]["id"],
                 i_sink=o["m10"]["id"] if self.W_sink else 0.0,
                 alpha=alpha, gm_in=o["m2"]["gm"], vov_in=(p["vin_cm"] - s["v_tail"]) - o["m2"]["vth"],
                 vds_min=min(vds.values()), **{f"vds_{k}": v for k, v in vds.items()}, **s)
        if with_noise:
            nz = self.noise(o, av, *band, z=z)
            r.update(vrms=nz["vrms"], vn_1k=nz["vn_spot"], noise_share=nz["share"], vn_th=nz["vn_th"],
                     vrms_th=nz["vrms_th"])
        return r


def evaluate_design(lut, p, v_lo=0.0, v_hi=0.3, CL=1e-12):
    """Two-endpoint summary used for the 9T calibration tables (control span 0 -> 0.3 V)."""
    m = VGAModel(lut, p); a, b = m.evaluate(v_lo, CL), m.evaluate(v_hi, CL)
    return dict(av_lo_db=a["av_db"], av_hi_db=b["av_db"], range_db=b["av_db"] - a["av_db"],
                f3db_hi=b["f3db"], f3db_lo=a["f3db"], i_tot=a["i_tot"], power=a["power"],
                vds_min=min(a["vds_min"], b["vds_min"]), vov_in=a["vov_in"],
                rout_lo=a["rout"], rout_hi=b["rout"], area_in=p["W_in"] * p["L_in"])


# ---------------------------------------------------------------------- the gate, as the LUT sees it
VSTEPS = (0.3, 0.2, 0.1, 0.0, -0.1, -0.2, -0.3)     # control voltages evaluated, max gain first
VDS_VALID = 0.030                                     # below this V_DS the LUT (25 mV V_DS step) is not trusted
MONO_TOL_DB = 0.2                                     # a saturated top may droop this much per step


def evaluate_gate(lut, p, CL=1e-12, bw_min=10e3, vsteps=VSTEPS, band=(20.0, 20e3), noise=True):
    """Everything the adoption gate needs, predicted from the LUT: gain at each control step, the window from
    +0.3 V down to the last step whose bandwidth is still >= bw_min, monotonicity and range over that window,
    supply current, minimum headroom (M2, M5, M6, M9 at EVERY step - the input pair's minimum is mid-span, where
    the steering pairs share current) and input noise at maximum gain."""
    m = VGAModel(lut, p)
    pts, guess = [], None
    for i, v in enumerate(vsteps):                      # each step's DC solution warm-starts the next
        q = m.evaluate(v, CL, with_noise=(noise and i == 0), guess=guess, band=band)
        pts.append(q); guess = [q["v_tail"], q["v_A"], q["v_mir"]]
    g = np.array([q["av_db"] for q in pts]); bw = np.array([q["f3db"] for q in pts])
    k = 0
    while k + 1 < len(pts) and bw[k + 1] >= bw_min:
        k += 1
    win_ok = bw[0] >= bw_min
    mono = bool(win_ok and np.all(g[:k] - g[1:k + 1] > -MONO_TOL_DB))
    km = 0                                              # monotonic span from +0.3 V down, ignoring bandwidth
    while km + 1 < len(g) and g[km] - g[km + 1] > -MONO_TOL_DB:
        km += 1
    hi = pts[0]
    vmin = min(q[f"vds_{d}"] for q in pts for d in ("m2", "m5", "m6", "m9"))
    if min(q["vds_min"] for q in pts) < VDS_VALID:
        raise ValueError(f"a device is in deep triode (V_DS < {1e3*VDS_VALID:.0f} mV) at some control step; "
                         "the table's g/I_D ratios are not defined there - design rejected")
    return dict(av_max_db=g[0], window_lo_v=vsteps[k] if win_ok else float("nan"),
                mono_range_db=float(g[0] - g[km]), floor_db=float(g.min()),
                range_db=float(g[0] - g[k]) if win_ok else 0.0, monotonic=mono,
                bw_min=float(bw[:k + 1].min()) if win_ok else float(bw[0]), bw_maxgain=float(bw[0]),
                i_tot=max(q["i_tot"] for q in pts), power=max(q["power"] for q in pts), vds_min=vmin,
                vrms=hi.get("vrms", float("nan")), vn_1k=hi.get("vn_1k", float("nan")),
                vrms_th=hi.get("vrms_th", float("nan")), vn_th=hi.get("vn_th", float("nan")), c_out=hi["c_out"],
                i_sig=m.i_sigma(max(q["i_tot"] for q in pts)),
                noise_share=hi.get("noise_share", {}),
                vbias=m.vbias, i_tail=hi["i_tail"], i_sink=hi["i_sink"], av_curve_db=g.tolist(),
                bw_curve=bw.tolist(), vov_in=hi["vov_in"], finger_exact=finger_exact(p))


# ---------------------------------------------------------------------- design spaces
W_F = vf.W_F
SPACE_9T = dict(            # every width is a whole number of 5 um fingers
    nf_in=[2, 4, 8, 16],   L_in=[1.0, 2.0],
    nf_st=[1, 2],          L_st=[1.0, 2.0],
    nf_mir=[1, 2, 4],      L_mir=[1.0, 2.0],
    vctrl_cm=[1.00, 1.05, 1.10, 1.15, 1.20],
    vin_cm=[0.75, 0.80, 0.85, 0.90],     # input common mode, set by the preceding stage
    vbias=[0.59, 0.61, 0.63],
)
SPACE_12T = dict(
    nf_in=[4, 8, 16],      L_in=[1.0, 2.0],
    nf_st=[1, 2],          L_st=[1.0, 2.0],
    nf_mir=[1, 2, 4, 8],   L_mir=[1.0, 2.0],
    vctrl_cm=[1.00, 1.05, 1.10, 1.15, 1.20],
    vin_cm=[0.75, 0.80, 0.85, 0.90],
    L_u=[2.0, 4.0],
    m_tail=[6, 8, 10],     # tail = m_tail unit copies -> 1.5 / 2.0 / 2.5 uA at I_ref = 0.25 uA
    m_sink=[1, 2, 3],      # each keep-alive sink = m_sink unit copies
    nf_u=[1, 4],           # unit device = nf_u fingers of W_F (M5, M10, M11, M12); the search extension may widen it
)
I_UNIT = 0.25e-6           # reference current = current of one unit copy
# Where the evaluator's accuracy is measured (Table 9b): the 12T grid widened to every value the search extension
# can reach in practice (flow.EXTEND), so that the error bound covers the designs the extended flow decides on.
SPACE_ACC_12T = dict(
    nf_in=[4, 8, 16, 32, 64, 128], L_in=[1.0, 2.0, 4.0, 8.0, 16.0],
    nf_st=[1, 2, 4, 8],            L_st=[0.5, 1.0, 2.0, 4.0],
    nf_mir=[2, 4, 8, 16, 32, 64, 128], L_mir=[0.5, 1.0, 2.0, 4.0],
    vctrl_cm=[1.00, 1.05, 1.10, 1.15, 1.20, 1.25], vin_cm=[0.65, 0.70, 0.75, 0.80, 0.85, 0.90],
    L_u=[1.0, 2.0, 4.0, 8.0], m_tail=[6, 8, 10, 12, 14, 16], m_sink=[1, 2, 3], nf_u=[1, 2, 4, 8, 16, 32],
)


def materialise(base, point):
    """Design-space point (finger counts) -> full parameter dict (total widths)."""
    p = dict(base); p.update(point)
    for g in GROUPS:
        if f"nf_{g}" in point:
            p[f"W_{g}"] = point[f"nf_{g}"] * W_F
    if "m_tail" in point:
        p.setdefault("iref", I_UNIT)
        p["W_u"] = int(point.get("nf_u", p.get("nf_u", 1))) * W_F            # unit device: nf_u fingers
    return p


HEADROOM_SPICE = 0.150  # design margin enforced on SPICE-verified designs: 130 mV weak-inversion saturation limit
                        # (Table 2) plus 20 mV, because undistorted output swing collapses as headroom nears 130 mV
VDS_MIN_LUT = HEADROOM_SPICE + 0.010   # LUT screening margin (re-measured for the finger-exact table in section 6)
I_TOT_MAX = 5e-6

_LUT = None
_LUTC = None
def _init(path, corners_path=None):
    global _LUT, _LUTC
    import lut as _l
    _LUT = _l.load(path) if path else None
    _LUTC = _l.load_corners(corners_path) if corners_path else None

CORNER_COLS = ("range_db", "monotonic", "bw_min", "i_tot", "vds_min", "av_max_db", "i_sig")

def _eval_corners(args):
    p, CL, supplies, combos, tables = args
    jobs = [(c, _LUTC[c], p) for c in tables]
    if supplies:                                         # supply corners: the tt table at another V_DD
        jobs += [(f"vdd_{v:g}", _LUT, dict(p, vdd=v)) for v in supplies]
    for c, t, v in combos:                               # combined extremes: a corner table at another V_DD
        jobs.append((f"{c}_{t:g}_vdd_{v:g}", _LUTC[f"{c}_{t:g}"], dict(p, vdd=v)))
    out = {}
    for c, lt, q in jobs:
        try:
            r = evaluate_gate(lt, q, noise=False, CL=CL)
            out.update({f"{c}_{k}": r[k] for k in CORNER_COLS}); out[f"{c}_ok"] = True
        except Exception:
            out[f"{c}_ok"] = False
    return out

def sweep_corners(corners_path, points, procs=None, CL=1e-12, lut_path=None, supplies=(), combos=(), tables=None):
    """Evaluate a list of parameter dicts at the corner tables `tables` (default: all), at each supply in `supplies` on
    the tt table, and at each (process, temperature, V_DD) in `combos` on that corner's table
    (no noise). Returns a DataFrame aligned to points."""
    import multiprocessing as mp, pandas as pd
    if not Path(corners_path).exists():          # fail here: a pool whose initializer fails would respawn workers forever
        raise FileNotFoundError(f"{corners_path}: the corner tables are needed to screen new designs at the corners "
                                "(built by the notebook's §5 cell when ngspice/SKY130 is present)")
    with mp.Pool(procs, initializer=_init, initargs=(str(lut_path) if lut_path else None, str(corners_path))) as pool:
        import lut as _l
        tables = list(tables) if tables is not None else sorted(_l.load_corners(corners_path))
        rows = pool.map(_eval_corners, [(p, CL, tuple(supplies), tuple(combos), tuple(tables)) for p in points], chunksize=8)
    return pd.DataFrame(rows)

def _eval_one(args):
    p, kind, CL = args
    try:
        r = evaluate_gate(_LUT, p, CL=CL) if kind == "gate" else evaluate_design(_LUT, p, CL=CL)
        ns = r.get("noise_share") or {}
        r = {k: v for k, v in r.items() if k not in ("av_curve_db", "bw_curve", "noise_share")} | \
            {"noise_top": max(ns, key=ns.get) if ns else ""}
        r.update(p); r["ok"] = True
    except Exception as e:
        r = dict(p); r["ok"] = False; r["err"] = str(e)[:80]
    return r

def sweep_points(lut_path, points, kind="gate", procs=None, CL=1e-12):
    """Evaluate a list of full parameter dicts with the LUT model (the search extension's new points)."""
    import multiprocessing as mp, pandas as pd
    with mp.Pool(procs, initializer=_init, initargs=(str(lut_path),)) as pool:
        rows = pool.map(_eval_one, [(p, kind, CL) for p in points], chunksize=4)
    return pd.DataFrame(rows)

def sweep(lut_path, base, space, kind="gate", procs=None, CL=1e-12):
    """Evaluate every point of a design space (dict of lists) with the LUT model. Returns a DataFrame."""
    import itertools, multiprocessing as mp, pandas as pd
    keys = list(space)
    pts = [(materialise(base, dict(zip(keys, c))), kind, CL) for c in itertools.product(*space.values())]
    with mp.Pool(procs, initializer=_init, initargs=(str(lut_path),)) as pool:
        rows = pool.map(_eval_one, pts, chunksize=8)
    return pd.DataFrame(rows)


def pareto(df, maximize=(), minimize=()):
    """Non-dominated subset of df (already filtered to feasible designs)."""
    f = df.copy()
    X = np.column_stack([-f[c].values for c in maximize] + [f[c].values for c in minimize])
    keep = np.ones(len(f), bool)
    for i in range(len(f)):
        if keep[i]:
            dom = np.all(X <= X[i], axis=1) & np.any(X < X[i], axis=1)
            if dom.any(): keep[i] = False
    return f[keep]

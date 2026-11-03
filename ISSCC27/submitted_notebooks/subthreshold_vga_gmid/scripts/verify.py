"""
verify.py - the verification matrix for a sized design: every claim the notebook makes about the final design
is produced by one of these functions, in SPICE.

  gain_vs_temperature  gain law at -20 / 27 / 85 C, against the analytic steering law, and with a PTAT-scaled
                       control voltage (behavioural source) that removes the law's temperature dependence
  per_step             at each control step: gain, bandwidth, input and output noise, input amplitude and
                       output swing at THD = 1 %, output dynamic range
  supply               the adoption gate at V_DD +/- 10 %
  dc_match, monte_carlo  local mismatch with the PDK statistical model per instance: DC-match analysis, and a
                       Monte Carlo of the full gate with an ideal output DC servo
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import math, re
import numpy as np
import vga_flow as vf

K_LOG = 20 / math.log(10)                    # 8.686 dB per neper


def steering_range_db(n, temp_c, span=0.3):
    """Range of the pure steering law over -span..+span: alpha(+V)/alpha(-V) = exp(V/(n U_T))."""
    ut = vf.K_B * (temp_c + 273.15) / vf.Q
    return K_LOG * span / (n * ut)


def gain_vs_temperature(p, temps=(-20, 27, 85), vgrid=None, ptat=False, t_ref=27.0):
    """Gain curves at each temperature. ptat=True applies V_ctrl * T/T_ref (a PTAT-scaled control voltage)."""
    vgrid = np.round(np.arange(-0.3, 0.3001, 0.025), 4) if vgrid is None else np.asarray(vgrid)
    out = {}
    for t in temps:
        scale = (t + 273.15) / (t_ref + 273.15) if ptat else 1.0
        g = vf.gain_curve(dict(p, temp=t), vgrid * scale)
        out[f"{t:g}"] = (20 * np.log10(np.asarray(g))).tolist()
    return dict(vgrid=vgrid.tolist(), gain_db=out, ptat=ptat)


def _input_at_thd(p, vctrl, av, thd_limit=1.0, grid=(2e-5, 5e-5, 1e-4, 2e-4, 5e-4, 1e-3, 2e-3, 4e-3, 8e-3, 16e-3, 32e-3,
                                                       64e-3, 128e-3, 256e-3)):
    """Largest differential input amplitude (V peak) with THD <= thd_limit, interpolated (THD ~ amplitude^k)."""
    prev = None
    grid = [g for g in grid if abs(av) * g >= 1e-3] or [grid[-1]]   # start where the output is >= 1 mV: below that the
                                                                  # harmonic fit resolves numerical noise, not distortion
    for vin in grid:
        r = vf.thd(p, vctrl, vin); t1 = r["thd_pct"]
        if t1 > thd_limit:
            if prev is None:
                return dict(vin_pk=vin * thd_limit / t1, vout_pk=av * vin * thd_limit / t1, limited_by="first point")
            v0, t0, o0 = prev
            k = math.log(t1 / t0) / math.log(vin / v0) if t1 > t0 > 0 else 1.0
            best = v0 * (thd_limit / t0) ** (1 / k) if k > 0.2 else v0
            best = min(max(best, v0), vin)
            return dict(vin_pk=best, vout_pk=o0 * best / v0, limited_by="THD")
        prev = (vin, t1, r["vout_fund_pk"])
    return dict(vin_pk=grid[-1], vout_pk=prev[2], limited_by="grid end")


def per_step(p, steps=(0.3, 0.2, 0.1, 0.0, -0.1, -0.2, -0.3), CL=1e-12, band=(20.0, 20e3)):
    rows = []
    for v in steps:
        op = vf.characterise(p, v)
        bw = vf.bandwidth(p, v, CL)["f3db"]
        nz = vf.noise(p, v, *band)
        lin = _input_at_thd(p, v, op["av"])
        out_noise = nz["vrms"] * op["av"]
        rows.append(dict(vctrl=v, av_db=op["av_db"], f3db=bw, vin_noise=nz["vrms"], vn_1k=nz["vn_1k"],
                         vout_noise=out_noise, vin_pk_thd1=lin["vin_pk"], vout_pk_thd1=lin["vout_pk"],
                         limited_by=lin["limited_by"],
                         dr_db=20 * math.log10((lin["vout_pk"] / math.sqrt(2)) / out_noise), v_out_dc=op["v_out"]))
    return rows


def supply(p, vdds=(1.62, 1.8, 1.98), spec=None):
    import flow
    spec = spec or flow.Spec()
    out = {f"{v:.2f}": flow.spice_gate(dict(p, vdd=v), "tt", 27, spec) for v in vdds}
    for v, r in out.items():                 # the current limit is judged with the flow's mismatch margin
        r["i_sig"] = flow.current_sigma_abs(p, f"tt/27/{float(v):g}V" if float(v) != 1.8 else "tt/27") / r["i_tot"]
    return out


def stress_corners(spec=None):
    """Every corner of the full grid - five process corners x (-20, 27, 85 C) x (1.62, 1.8, 1.98 V) - that the flow's
    gate does not already hold."""
    import flow
    spec = spec or flow.Spec()
    gate = {(c, float(t), 1.8) for c, t in spec.corners} | {("tt", 27.0, float(v)) for v in spec.supplies} | \
           {(c, float(t), float(v)) for c, t, v in spec.combos}
    return tuple((c, t, v) for c in ("tt", "ss", "ff", "sf", "fs") for t in (-20, 27, 85) for v in (1.62, 1.8, 1.98)
                 if (c, float(t), float(v)) not in gate)


def stress(p, spec=None, corners=None):
    """Verification beyond the flow's gate: every remaining corner of the five-process x three-temperature x
    three-supply grid, each through the same SPICE gate (no noise), the current limit with the same mismatch margin."""
    import flow
    spec = spec or flow.Spec()
    corners = corners or stress_corners(spec)
    out = []
    for c, t, v in corners:
        r = flow.spice_gate(dict(p, vdd=v), c, t, spec, noise=False)
        r["corner"] = f"{c}/{t}/{v:g}V"
        r["i_sig"] = flow.current_sigma_abs(p, r["corner"]) / r["i_tot"]
        out.append(r)
    return out


def psrr(p, steps=(0.3, 0.0, -0.3), f=100.0):
    """Supply rejection at each control step: differential gain over the gain from an AC signal on V_DD (I_ref held)."""
    out = {}
    for v in steps:
        base = vf.circuit(p)
        dd = base.replace(f"VDD   vdd 0 {p['vdd']}", f"VDD   vdd 0 DC {p['vdd']} AC 1").replace("Vid   vid   0 DC 0 AC 1", "Vid   vid   0 DC 0 AC 0")
        r = vf.parse_print(vf.run(dd + f".control\nalter vctrl dc = {v}\nac lin 1 {f} {f}\nlet add = vm(v_out)\nprint add\n.endc", "psrr"))
        av = vf.gain_curve(p, [v], f)[0]
        out[f"{v:+.1f}"] = dict(av=float(av), a_dd=r["add"], psrr_db=20 * math.log10(av / r["add"]))
    return out


def cmrr(p, steps=(0.3, 0.0, -0.3), f=100.0):
    """Common-mode rejection at each control step: differential gain over the gain for the same AC signal on both
    inputs."""
    out = {}
    for v in steps:
        dd = vf.circuit(p).replace("Vid   vid   0 DC 0 AC 1", "Vid   vid   0 DC 0 AC 0\nVcm   vcm   0 DC 0 AC 1")
        dd = re.sub(r"(Bvinp vin_p 0 V = [^\n]*)", r"\1 + V(vcm)", dd)
        dd = re.sub(r"(Bvinn vin_n 0 V = [^\n]*)", r"\1 + V(vcm)", dd)
        r = vf.parse_print(vf.run(dd + f".control\nalter vctrl dc = {v}\nac lin 1 {f} {f}\nlet acm = vm(v_out)\nprint acm\n.endc", "cmrr"))
        av = float(vf.gain_curve(p, [v], f)[0])
        out[f"{v:+.1f}"] = dict(av=av, a_cm=r["acm"], cmrr_db=20 * math.log10(av / r["acm"]))
    return out


def control_step(p, v0=0.3, v1=0.0, t_step=2e-3, t_stop=0.02, vin_pk=0.0, f0=5e3, tmax=None, CL=0.0):
    """Large-signal response to a step of the gain control V_ctrl from v0 to v1 at t_step (rise 1 us).
    With vin_pk = 0: the control-to-output feedthrough - how far v_out moves and how long it takes to settle.
    With a sine input: the gain envelope (amplitude per input period, by least squares) and its settling.
    Time resolution 1 us (feedthrough) or 1/40 of the input period (gain); the gain envelope is one value per input
    period, so gain settling is resolved to one period. CL: load capacitance on v_out (F)."""
    tmax = tmax or (1 / (40 * f0) if vin_pk else 1e-6)
    src = f"Vctrl vctrl 0 PWL(0 {v0} {t_step} {v0} {t_step + 1e-6} {v1})"
    deck = vf.circuit(p).replace("Vctrl vctrl 0 DC 0", src)
    if vin_pk:
        deck = deck.replace("Vid   vid   0 DC 0 AC 1", f"Vid   vid   0 DC 0 SIN(0 {vin_pk} {f0})")
    if CL:
        deck += f"CL v_out 0 {CL}\n"
    W = vf.WORK; tag = f"cstep{abs(hash((v0, v1, vin_pk))) % 10000}"
    for abstol in (1e-14, 1e-13):
        d_ = deck + f""".options abstol={abstol:g}
.control
set wr_singlescale
set wr_vecnames
tran {tmax} {t_stop} 0 {tmax}
linearize v(v_out)
wrdata {W}/{tag}.txt v(v_out)
.endc"""
        try:
            vf.run(d_, tag); break
        except RuntimeError as e:
            if "imestep too small" not in str(e) or abstol == 1e-13:
                raise
    d = np.loadtxt(W / f"{tag}.txt", skiprows=1); t, v = d[:, 0], d[:, -1]
    if not vin_pk:
        pre = v[t < t_step].mean() if np.any(t < t_step) else v[0]
        fin = v[-1]; dv = fin - pre
        post = t >= t_step
        err = np.abs(v[post] - fin)
        band = max(0.01 * abs(dv), 1e-3)                    # settled: within 1 % of the step or 1 mV
        out_of = np.where(err > band)[0]
        ts = float(t[post][out_of[-1]] - t_step) if len(out_of) else 0.0
        return dict(v0=v0, v1=v1, v_pre=float(pre), v_final=float(fin), dv=float(dv),
                    overshoot=float(np.max(np.abs(v[post] - pre)) - abs(dv)), t_settle=ts, band=band,
                    t=t[::max(1, len(t) // 2000)].tolist(), v=v[::max(1, len(t) // 2000)].tolist())
    per = 1 / f0; n = int(t_stop / per)
    tc, amp = [], []
    for k in range(n):
        m = (t >= k * per) & (t < (k + 1) * per)
        if m.sum() < 8:
            continue
        A = np.column_stack([np.sin(2 * np.pi * f0 * t[m]), np.cos(2 * np.pi * f0 * t[m]), np.ones(m.sum())])
        c = np.linalg.lstsq(A, v[m], rcond=None)[0]
        tc.append((k + 0.5) * per); amp.append(float(np.hypot(c[0], c[1])))
    tc, amp = np.array(tc), np.array(amp)
    g = 20 * np.log10(amp / vin_pk)
    pre = g[(tc < t_step) & (tc > t_step - 5 * per)].mean(); fin = g[-5:].mean()
    post = tc > t_step
    out_of = np.where(np.abs(g[post] - fin) > 0.5)[0]         # settled: within 0.5 dB of the final gain
    ts = float(tc[post][out_of[-1]] - t_step + per / 2) if len(out_of) else per / 2
    return dict(v0=v0, v1=v1, vin_pk=vin_pk, f0=f0, g_pre_db=float(pre), g_final_db=float(fin), t_settle_gain=ts,
                t=tc.tolist(), g_db=g.tolist())


# ------------------------------------------------------------------------------------------- mismatch
# Local mismatch uses the PDK's own statistical model, per instance (vga_flow.mismatch_lib): every parameter SKY130
# varies for mismatch (V_TH0, V_OFF, T_OX for both devices; N_FACTOR for the pfet), with the slope of each device's
# model bin. A device built as m parallel copies averages m independent draws, so its draw is z / sqrt(m).
STEPS = (0.3, 0.2, 0.1, 0.0, -0.1, -0.2, -0.3)         # = evaluator.VSTEPS
HEAD_DEVS = {"m2": ("net2", "net5"), "m3": ("net3", "net5"), "m5": ("net5", "0"), "m6": ("net4", "net2"),
             "m9": ("v_out", "net3")}


def mm_devices(p):
    """(instance, kind, m) for every transistor of the core."""
    out = []
    for line in vf.circuit(p).splitlines():
        if line.startswith("XM"):
            t = line.split(); kind = "pfet" if "pfet" in t[5] else "nfet"
            kv = dict(x.split("=") for x in t[6:] if "=" in x)
            out.append((t[0][1:], kind, int(float(kv.get("m", 1)))))
    return out


def _ops_deck(p, steps, itest=None, tag="mmop"):
    """v_out at every control step (optionally with a DC current itest[k] injected at v_out at step k)."""
    body = []
    for i, v in enumerate(steps):
        body += [f"alter vctrl dc = {v}"] + ([f"alter itest dc = {itest[i]:.6e}"] if itest is not None else []) + \
                ["op", f"let vo{i} = v(v_out)", f"print vo{i}"]
    r = vf.parse_print(vf.run(vf.circuit(p) + "\n.control\n" + "\n".join(body) + "\n.endc", tag))
    return np.array([r[f"vo{i}"] for i in range(len(steps))])


def dc_match(p, steps=STEPS, delta=0.1):
    """DC-match analysis with the PDK mismatch model: d v_out / d z for every (device, parameter) by central
    differences of .op at every control step, the output resistance (1 nA injected at v_out) and the DC gain.
    sigma(v_out) = sqrt(sum (s_i / sqrt(m_i))^2); input-referred offset = sigma(v_out) / A_dc."""
    devs = mm_devices(p)
    keys = [(d, q, m) for d, kind, m in devs for q in vf.MM_PARAMS[kind]]
    vnom = _ops_deck(p, steps, tag="mm_nom")
    di = 1e-9
    rout = (_ops_deck(p, steps, itest=[di] * len(steps), tag="mm_rout") - vnom) / di
    gdc = (_ops_deck(dict(p, vid_dc=1e-4), steps, tag="mm_gp") - _ops_deck(dict(p, vid_dc=-1e-4), steps, tag="mm_gn")) / 2e-4
    sens = {}
    for d, q, m in keys:
        up = _ops_deck(dict(p, mm={d: {q: delta}}), steps, tag="mm_s")
        dn = _ops_deck(dict(p, mm={d: {q: -delta}}), steps, tag="mm_s")
        sens[f"{d}:{q}"] = ((up - dn) / (2 * delta) / math.sqrt(m)).tolist()   # per unit z of the instance
    S = np.array([sens[k] for k in sens])                                        # [param, step]
    sig_out = np.sqrt((S ** 2).sum(axis=0))
    share = {k: (np.array(sens[k]) ** 2 / sig_out ** 2).tolist() for k in sens}
    return dict(steps=list(steps), v_nom=vnom.tolist(), rout=rout.tolist(), a_dc=gdc.tolist(), sens=sens,
                sigma_vout=sig_out.tolist(), sigma_vin=(sig_out / np.abs(gdc)).tolist(), share=share,
                m={d: m for d, _, m in devs})


def _open_loop(q, steps, vdd, tag):
    """A die with no servo: v_out where mismatch puts it, and the headroom of every device at every control step -
    the gate's devices, plus the output devices that a drifting v_out squeezes (M4: V_DD - v_out; M11: v_out)."""
    body = []
    for i, v in enumerate(steps):
        body += [f"alter vctrl dc = {v}", "alter itest dc = 0", "op", f"let vo{i} = v(v_out)", f"print vo{i}"]
        body += [x for n, (a, b) in HEAD_DEVS.items()
                 for x in (f"let {n}_{i} = " + (f"v({a})-v({b})" if b != "0" else f"v({a})"), f"print {n}_{i}")]
    r = vf.parse_print(vf.run(vf.circuit(q) + "\n.control\n" + "\n".join(body) + "\n.endc", tag + "ol"))
    vo = np.array([r[f"vo{i}"] for i in range(len(steps))])
    vds = np.array([[r[f"{n}_{i}"] for n in HEAD_DEVS] + [vdd - vo[i], vo[i]] for i in range(len(steps))])
    return vo, vds


def _mc_sample(args):
    """One mismatch sample with an ideal output DC servo: the DC current injected at v_out is set, at every
    control step, so that v_out returns to its nominal value (predicted from the DC-match sensitivities, then two
    Newton corrections); the full gate is then measured at that operating point."""
    p, dm, z, idx, spec_d = args
    import flow
    spec = flow.Spec(**{k: v for k, v in spec_d.items() if k in ("CL", "c_wire", "bw_min_hz", "range_min_db", "band")})
    steps = dm["steps"]; vnom = np.array(dm["v_nom"]); rout = np.array(dm["rout"])
    mm = {}
    for key, zz in z.items():
        d, q = key.split(":"); mm.setdefault(d, {})[q] = zz / math.sqrt(dm["m"][d])
    q = dict(p, mm=mm)
    dv_lin = sum(np.array(dm["sens"][k]) * z[k] for k in z)                  # open-loop shift, linear prediction
    it = -dv_lin / rout
    tag = f"mc{idx}"
    vo_ol, vds_ol = _open_loop(q, steps, p.get("vdd", 1.8), tag)              # the same die without the servo
    v1 = _ops_deck(q, steps, itest=it, tag=tag); it1 = it - (v1 - vnom) / rout
    v2 = _ops_deck(q, steps, itest=it1, tag=tag); it2 = it1 - (v2 - vnom) / rout
    W = vf.WORK
    body = []
    for i, v in enumerate(steps):
        e = {n: f"v({a})-v({b})" if b != "0" else f"v({a})" for n, (a, b) in HEAD_DEVS.items()}
        body += [f"alter vctrl dc = {v}", f"alter itest dc = {it2[i]:.6e}", "op", f"let vo{i} = v(v_out)", f"print vo{i}",
                 f"let isup{i} = -i(vdd)", f"print isup{i}"] + \
                [x for n, ex in e.items() for x in (f"let {n}_{i} = {ex}", f"print {n}_{i}")] + \
                ["ac dec 40 1 100meg", f"wrdata {W}/{tag}_ac{i}.txt vm(v_out)"]
        if i == 0:
            body += ["noise v(v_out) vid dec 40 1 1meg", "setplot noise1", f"wrdata {W}/{tag}_nz.txt inoise_spectrum"]
    deck = vf.circuit(q) + f"CL v_out 0 {spec.CL + spec.c_wire}\n.control\nset wr_singlescale\nset wr_vecnames\n" + "\n".join(body) + "\n.endc"
    r = vf.parse_print(vf.run(deck, tag))
    g, bw = [], []
    for i in range(len(steps)):
        d_ = np.loadtxt(W / f"{tag}_ac{i}.txt", skiprows=1); fr, mg = d_[:, 0], d_[:, -1]
        g.append(20 * math.log10(float(np.interp(100.0, fr, mg))))
        a0 = mg[0]; tgt = a0 / math.sqrt(2); j = int(np.argmax(mg < tgt))
        bw.append(float(np.exp(np.interp(math.log(tgt), np.log([mg[j], mg[j - 1]]), np.log([fr[j], fr[j - 1]])))) if j else float("nan"))
    dn = np.loadtxt(W / f"{tag}_nz.txt", skiprows=1); fr, vn = dn[:, 0], dn[:, -1]
    mb = (fr >= spec.band[0]) & (fr <= spec.band[1])
    vrms = math.sqrt(vf._trapz(vn[mb] ** 2, fr[mb]))
    g, bw = np.array(g), np.array(bw)
    k = 0
    while k + 1 < len(steps) and bw[k + 1] >= spec.bw_min_hz:
        k += 1
    win = bool(bw[0] >= spec.bw_min_hz)
    mono = bool(win and np.all(g[:k] - g[1:k + 1] > -0.2))
    vds = {n: min(r[f"{n}_{i}"] for i in range(len(steps))) for n in HEAD_DEVS}
    return dict(idx=idx, gain_db=g.tolist(), bw=bw.tolist(), range_db=float(g[0] - g[k]) if win else 0.0, monotonic=mono,
                bw_min=float(bw[:k + 1].min()) if win else float(bw[0]), i_tot=max(r[f"isup{i}"] for i in range(len(steps))),
                vds_min=min(vds.values()), vds=vds, vrms=vrms, vn_1k=float(np.interp(1e3, fr, vn)),
                servo_i=it2.tolist(), dv_open=dv_lin.tolist(), v_open=vo_ol.tolist(),
                vds_open_min=float(vds_ol.min()), vds_open_by_step=vds_ol.min(axis=1).tolist(),
                resid_lin=(v1 - vnom).tolist(), resid_final=[r[f"vo{i}"] - vnom[i] for i in range(len(steps))])


def monte_carlo(p, n=200, seed=11, corner="tt", temp=27, procs=None, spec=None):
    """Local-mismatch Monte Carlo of the full gate with an ideal output DC servo (see _mc_sample). Returns the
    DC-match analysis it is built on and one record per sample."""
    import multiprocessing as mp, flow
    from dataclasses import asdict
    spec = spec or flow.Spec()
    q = dict(p, corner=corner, temp=temp)
    dm = dc_match(q)
    rng = np.random.default_rng(seed)
    keys = list(dm["sens"])
    draws = [{k: float(rng.standard_normal()) for k in keys} for _ in range(n)]
    with mp.Pool(procs) as pool:
        rows = pool.map(_mc_sample, [(q, dm, z, i, asdict(spec)) for i, z in enumerate(draws)], chunksize=1)
    return dict(corner=f"{corner}/{temp}", n=n, seed=seed, dc_match=dm, samples=rows)

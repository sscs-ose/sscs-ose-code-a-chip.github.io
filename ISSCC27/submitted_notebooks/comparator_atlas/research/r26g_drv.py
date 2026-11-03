"""r26g: is r26f's segment weakening a relative (DNL) error or a common gain error? r26f drove the seven segment
switches of each side from the CMOS decoder but left the two binary LSB switches (1 and 2 unit cells) on the ideal
testbench sources, so only the segments saw clock-edge gate kickback. Design family b5_k<100k>: d5_k<100k> with each
LSB switch gate driven through a two-inverter buffer whose output stage equals the decoder's output inverter
(nfet 0.65/L, pfet 1.0/L), 8 devices per side appended after the decoder devices (r26e/r26f draws unchanged).
Family s5_k<100k> (R26G_SCALE=1): b5 with every switch driver's output stage scaled with its switch (m = 4 on the
14 decoder output inverters, m = 2 on the bit-1 buffer output stage, m = 1 on bit 0), so that each switch gate's
driver capacitance is proportional to its coupling capacitance. R26F_HOLD=<H um> adds r26f's square nfet hold
capacitor to every segment gate (kick d / probe d only).

Dip law (FINDINGS r26g): dip = A m / (m + m0 + c_h H^2); `law` fits it per condition (linear least squares on
m / dip) to b5 (m = 4 / 2 / 1) and d5 H = 1 / 2 / 4, and predicts s5 as A / (1 + m0).

Weights (not usable, kept for the record): per DNL condition, the 63 boundaries are fitted by b(c) = b0 + sgn(c)
(w0 bit0 + w1 bit1 + ws nseg) per side; even g5 gives ws / (4 w0) = 0.84 - 1.19 because the transfer is curved.

  [R26G_SCALE=1] python -B r26g_drv.py dnl       # 63-code transfer of b5_k175 (s5_k175) at the 5 DNL conditions
  [R26G_SCALE=1] python -B r26g_drv.py kick      # LSB- and segment-gate dips + waveforms at code -31, b5 (s5)
  [R26F_HOLD=H] python -B r26g_drv.py kick d     # segment-gate dip + waveform of d5 (with hold capacitor H)
  python -B r26g_drv.py probe                    # fine boundaries at 0, +/-3, +/-28, +/-31: g5, d5, b5, s5
  R26F_HOLD=H python -B r26g_drv.py probe d      # the same for d5 with hold capacitor H
  python -B r26g_drv.py law                      # dip-law fit, writes out/r26g/dip_law_k175.json
  python -B r26g_drv.py weights                  # weight fit of g5 / d5 / b5 / s5 transfers
"""
import json
import os
import re
from concurrent.futures import ProcessPoolExecutor

import numpy as np

import r26f_dec as F

ARGS = F.ARGS
G, U, R3 = F.G, F.U, F.R3
OUT = F.OUT
OUT_F = R3.HERE / "out" / "r26g"
OUT_F.mkdir(parents=True, exist_ok=True)
_LSB_GATE = re.compile(r"^(Xs([pn])([01]) s\2\3 )t\2\3 ", re.M)
_is_d0, _ct_d, _check_d = F._is_d, F.circuit_text, F._check_circuit
SCALE = os.environ.get("R26G_SCALE", "") == "1"
_OUT_INV = re.compile(r"^(Xdc[pn]\d+ g([pn])\d dc\2\d_x (?:vdd|vss) .+\n\+ w=.*\n\+ ad=.*\n\+ pd=.*)$", re.M)


def _is_b(name):
    return name[:1] in "bs" and name[1:2].isdigit()


def _buffers(scale):
    dev = []
    for side in "pn":
        for b in (0, 1):
            x, y = f"lb{side}{b}_x", f"l{side}{b}"
            for i, (d, g, kind) in enumerate(((x, f"t{side}{b}", "p"), (x, f"t{side}{b}", "n"),
                                             (y, x, "p"), (y, x, "n"))):
                dev.append(F._mos(f"Xlb{side}{b}{i}", d, g, "vdd" if kind == "p" else "vss", kind)
                           + ("\n+ m=2" if scale and b == 1 and i >= 2 else ""))
    return "\n".join(dev)


def circuit_text(design):
    if not _is_b(design.name):
        return _ct_d(design)
    text = _ct_d(design)
    text, n = _LSB_GATE.subn(lambda mt: f"{mt.group(1)}l{mt.group(2)}{mt.group(3)} ", text)
    assert n == 4, n
    scale = design.name.startswith("s")
    if scale:
        text, n = _OUT_INV.subn(lambda mt: mt.group(1) + "\n+ m=4", text)
        assert n == 28, n
    return text.replace(".ends atlas", _buffers(scale) + "\n.ends atlas")


F._is_d = lambda name: _is_d0(name) or _is_b(name)
F.circuit_text = G.D.circuit_text = G.SP.circuit_text = R3.circuit_text = circuit_text


def _check_circuit(text):
    _check_d(text)
    n_buf = len(re.findall(r"^Xlb[pn][01]\d ", text, re.M))
    assert n_buf in (0, 16), n_buf  # 0 = d5 (probe shares this check), 16 = b5/s5
    assert len(re.findall(r"^\S*Xs([pn])([01])\b[^\n]*\bl\1\2\b", text, re.M)) == (4 if n_buf else 0)
    assert len(re.findall(r"^Xdc[^\n]*\n(?:\+[^\n]*\n){3}\+ m=4", text, re.M)) in ((0, 28) if n_buf else (0,))


G._check_circuit = _check_circuit


def register(k):
    return U.register(5, k, prefix="s" if SCALE else "b")


DESIGN = register(F.K)
G.register = register
for _p in "gbs":  # probe() workers need all four families registered
    U.register(5, F.K, prefix=_p)
PROBE_TOL_MV, PROBE_CODES = 0.01, (0, 3, -3, 28, -28, 31, -31)
_KICK = ["v(xdut.gn8)", "v(xdut.ln0)", "v(xdut.ln1)", "v(xdut.tail)"]


def _kick(job):
    cond, design = job if isinstance(job[0], tuple) else (job, DESIGN)
    vecs = _KICK if _is_b(design) else [_KICK[0], _KICK[3]]
    s = G._nominal(design, cond)
    p = F.replace(s.base, differential_v=0.0, trim_code=-31)
    header = s.sim._header(p).replace(R3.circuit_text(R3.get_design(s.design)), s.circuit)
    header = header.replace(".save v(clk)", ".save " + " ".join(vecs) + " v(clk)")
    lines = [header, ".control", "set wr_singlescale", "set wr_vecnames", "set numdgt=15"]
    lines += [f"alter Vt{side}{b} {cond[1] if side == 'n' else 0:.12g}" for side in "pn" for b in range(5)]
    lines += ["tran 1p 26n 21n 1p", "wrdata w.tsv " + " ".join(vecs), "quit 0", ".endc", ".end"]
    _, files = R3.ngspice("\n".join(lines) + "\n")
    v = np.loadtxt(files["w.tsv"].splitlines(), skiprows=1)
    t = v[:, 0]
    edge = (t > 21.9e-9) & (t < 25e-9)
    names = ("seg", "lsb0", "lsb1")[:len(vecs) - 1]
    dips = {n: float((cond[1] - np.min(v[:, i + 1][edge])) * 1e3) for i, n in enumerate(names)}
    win = (t > 21.9e-9) & (t < 23.5e-9)
    grid = np.arange(21.9e-9, 23.5e-9, 5e-12)
    wave = {"t_ps": [round(x * 1e12, 1) for x in grid]}
    for i, n in enumerate(names + ("tail",)):
        wave[n + "_mv"] = [round(float(x) * 1e3, 2) for x in np.interp(grid, t[win], v[:, i + 1][win])]
    return {"design": design, "hold_um": F.HOLD, "cond": list(cond), "dip_mv": dips, "wave": wave}


def kick(design=None):
    design = design or DESIGN
    conds = list(G.S.DNL_CONDS)
    with ProcessPoolExecutor(len(conds)) as ex:
        rows = list(ex.map(_kick, [(c, design) for c in conds]))
    for r in rows:
        print({k: r[k] for k in ("design", "hold_um", "cond", "dip_mv")}, flush=True)
    tag = f"_H{F.HOLD:g}" if F.HOLD else ""
    (OUT_F / f"kick_{design}{tag}.json").write_text(json.dumps(rows, indent=1))


def fit(b_mv):
    """Least-squares weights of one transfer: per side (w0, w1, ws) in mV, codes -31..31, sign-magnitude."""
    codes = np.arange(-31, 32)
    y = np.array([b_mv[str(c)] for c in codes])
    cols = [np.ones_like(codes, dtype=float)]
    for sgn in (1, -1):
        mag = np.where(np.sign(codes) == sgn, np.abs(codes), 0)
        cols += [mag & 1, (mag >> 1) & 1, mag >> 2]
    a = np.column_stack(cols).astype(float)
    coef, *_ = np.linalg.lstsq(a, y, rcond=None)
    resid = y - a @ coef
    out = {"offset_mv": float(coef[0]), "rms_resid_mv": float(np.sqrt(np.mean(resid ** 2)))}
    for i, side in enumerate(("pos", "neg")):
        w0, w1, ws = (float(x) for x in coef[1 + 3 * i: 4 + 3 * i])
        out[side] = {"w0_mv": w0, "w1_mv": w1, "ws_mv": ws, "rho_seg": ws / (4 * w0), "rho_lsb1": w1 / (2 * w0)}
    return out


def weights():
    k = f"k{int(round(F.K * 100))}"
    src = {"ideal decoder (g5)": OUT / f"dnl_g5_{k}.json", "CMOS decoder (d5)": OUT / f"dnl_d5_{k}.json",
           "CMOS decoder + LSB buffers (b5)": OUT / f"dnl_b5_{k}.json",
           "scaled drivers (s5)": OUT / f"dnl_s5_{k}.json"}
    src = {label: path for label, path in src.items() if path.exists()}
    rows = []
    for label, path in src.items():
        for r in json.loads(path.read_text()):
            f = fit(r["b_mv"])
            rows.append({"design": label, "cond": r["cond"], "lsb_mv": r["lsb_mv"], "dnl_max_lsb": r["dnl_max_lsb"],
                         "monotonic": r["monotonic"], **f})
            print(f"{label:34s} {r['cond']} rho_seg {f['pos']['rho_seg']:.4f}/{f['neg']['rho_seg']:.4f} "
                  f"rho_lsb1 {f['pos']['rho_lsb1']:.4f}/{f['neg']['rho_lsb1']:.4f} w0 {f['pos']['w0_mv']:.3f} "
                  f"dnl {r['dnl_max_lsb']:.2f} resid {f['rms_resid_mv']:.3f}", flush=True)
    (OUT_F / "weights_seg.json").write_text(json.dumps(rows, indent=1))


def _probe(job):
    design, cond = job
    R3.TOL_MV = PROBE_TOL_MV
    s = G.T._nominal(design, cond) if design.startswith("g") else G._nominal(design, cond)
    return {"design": design, "cond": list(cond), "tol_mv": PROBE_TOL_MV,
            "b_mv": {str(c): v for c, v in s.boundaries(list(PROBE_CODES), lo=-45.0, hi=45.0).items()}}


AREA_INV_UM2 = 0.65 * 0.5 + 1.0 * 0.5  # one driver inverter (nfet 0.65 / pfet 1.0 um, L = 0.5 um)
LAW_AREA_UM2 = {"d5": 0.0, "b5": 8 * AREA_INV_UM2, "s5": (8 + 3 * 14 + 2) * AREA_INV_UM2,
                "d5 H1": 14.0, "d5 H2": 56.0, "d5 H4": 224.0}


def law():
    """Fit dip = A m / (m + m0 + c_h a) per condition (a = hold-capacitor area per gate, um2) to b5 (m = 4 / 2 / 1)
    and d5 H = 1 / 2 / 4 (m = 4), predict s5 (A / (1 + m0)), and tabulate the probe span losses against g5."""
    k = int(round(F.K * 100))

    def dips(name):
        return {tuple(r["cond"]): r["dip_mv"] for r in json.loads((OUT_F / name).read_text())}

    b5, s5 = dips(f"kick_b5_k{k:03d}.json"), dips(f"kick_s5_k{k:03d}.json")
    dh = {h: dips(f"kick_d5_k{k:03d}" + (f"_H{h}" if h else "") + ".json") for h in (0, 1, 2, 4)}
    probes = {"d5": ("", "d5"), "b5": ("", "b5"), "s5": ("", "s5"), "d5 H1": ("_H1", "d5"), "d5 H2": ("_H2", "d5"),
              "d5 H4": ("_H4", "d5")}

    def gains(t, d):
        rows = json.loads((OUT_F / f"probe_drivers_k{k}{t}.json").read_text())
        return {tuple(r["cond"]): r["gain_vs_ideal"] for r in rows if r["design"][:2] == d}

    pb = {lab: gains(t, d) for lab, (t, d) in probes.items()}
    seg_dip = {"d5": dh[0], "b5": {c: v["seg"] for c, v in b5.items()}, "s5": {c: v["seg"] for c, v in s5.items()},
               "d5 H1": dh[1], "d5 H2": dh[2], "d5 H4": dh[4]}
    rows = []
    for cond in G.S.DNL_CONDS:
        pts = [(4, 0.0, b5[cond]["seg"]), (2, 0.0, b5[cond]["lsb1"]), (1, 0.0, b5[cond]["lsb0"])]
        pts += [(4, float(h * h), dh[h][cond]["seg"]) for h in (1, 2, 4)]
        a = np.array([[m, 1.0, area] for m, area, _ in pts])
        p = np.linalg.lstsq(a, np.array([m / y for m, _, y in pts]), rcond=None)[0]
        amp, m0, ch = 1 / p[0], p[1] / p[0], p[2] / p[0]
        err = max(abs(amp * m / (m + m0 + ch * area) / y - 1) for m, area, y in pts)
        s5_meas = [s5[cond][n] for n in ("seg", "lsb1", "lsb0")]
        designs = {}
        for lab in probes:
            d = seg_dip[lab][cond]
            dip = d["seg"] if isinstance(d, dict) else d
            gain = pb[lab][cond]
            designs[lab] = {"area_um2": round(LAW_AREA_UM2[lab], 2), "seg_dip_mv": dip,
                            "seg_loss_pct": 100 * (1 - gain["seg"]), "full_loss_pct": 100 * (1 - gain["all"]),
                            "seg_loss_pct_per_mv": 100 * (1 - gain["seg"]) / dip}
        rows.append({"cond": list(cond), "A_mv": amp, "m0": m0, "c_h_per_um2": ch, "max_rel_err": err,
                     "s5_pred_mv": amp / (1 + m0), "s5_meas_mv": s5_meas,
                     "s5_pred_err": max(abs(x / (amp / (1 + m0)) - 1) for x in s5_meas), "designs": designs})
        print(f"{cond} A {amp:.0f} m0 {m0:.2f} c_h {ch:.2f} err {100 * err:.1f}% s5 {amp / (1 + m0):.1f} vs "
              + " / ".join(f"{x:.1f}" for x in s5_meas), flush=True)
    (OUT_F / f"dip_law_k{k}.json").write_text(json.dumps(rows, indent=1))


def _read_jsonl(path):
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []


def probe(families="gdbs", workers=5):
    """Fine boundaries at codes 0, +/-3 (LSB cells only), +/-28 (segments only), +/-31 for g5, d5, b5, s5 (or the
    `families` subset; with R26F_HOLD set, the hold capacitor is on every segment gate). Spans are reported as gain
    vs g5: lsb = b3 - b-3 (LSBs near zero), lsb_top = (b31 - b-31) - (b28 - b-28) (LSBs on top of the segments),
    seg = b28 - b-28, all = b31 - b-31."""
    k = int(round(F.K * 100))
    tag = f"_H{F.HOLD:g}" if F.HOLD else ""
    assert not (tag and "g" in families), "g5 has no decoder; its reference comes from the H = 0 run"
    designs = [d for d in ("g5_k%03d" % k, "d5_k%03d" % k, U.register(5, F.K, prefix="b"),
                           U.register(5, F.K, prefix="s")) if d[0] in families]
    part = OUT_F / f"_probe_k{k}{tag}.jsonl"
    done = _read_jsonl(part)
    have = {(r["design"], tuple(r["cond"])) for r in done}
    jobs = [(d, c) for c in G.S.DNL_CONDS for d in designs if (d, tuple(c)) not in have]
    with ProcessPoolExecutor(workers) as ex, part.open("a") as fh:
        for r in ex.map(_probe, jobs):
            r["hold_um"] = F.HOLD
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            done.append(r)
    order = {d: i for i, d in enumerate(designs)}
    rows = sorted([r for r in done if r["design"] in order],
                  key=lambda r: (G.S.DNL_CONDS.index(tuple(r["cond"])), order[r["design"]]))
    ref = {tuple(r["cond"]): r["b_mv"] for r in _read_jsonl(OUT_F / f"_probe_k{k}.jsonl")
           if r["design"].startswith("g")}

    def span(x, c):
        return x[str(c)] - x[str(-c)]

    for r in rows:
        b, g = r["b_mv"], ref[tuple(r["cond"])]
        gain = {n: span(b, c) / span(g, c) for n, c in (("lsb", 3), ("seg", 28), ("all", 31))}
        gain["lsb_top"] = (span(b, 31) - span(b, 28)) / (span(g, 31) - span(g, 28))
        r["gain_vs_ideal"] = gain
        print(f"{r['design']} H{F.HOLD:g} {r['cond']} lsb {gain['lsb']:.4f} lsb_top {gain['lsb_top']:.4f} "
              f"seg {gain['seg']:.4f} all {gain['all']:.4f}", flush=True)
    (OUT_F / f"probe_drivers_k{k}{tag}.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    U.os.environ.pop("R24_PRIOR_MV", None)
    cmd = ARGS[0] if ARGS else ""
    if cmd == "dnl":
        G.dnl(F.K)
    elif cmd == "kick":
        kick({"d": "d5_k%03d" % round(F.K * 100)}.get(ARGS[1]) if len(ARGS) > 1 else None)
    elif cmd == "weights":
        weights()
    elif cmd == "law":
        law()
    elif cmd == "probe":
        probe(*ARGS[1:2])
    else:
        raise SystemExit(__doc__)

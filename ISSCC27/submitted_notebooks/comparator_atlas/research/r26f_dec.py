"""r26f: the r26e segmented trim with a transistor-level thermometer decoder. r26e drove the seven segment switches
of each side from ideal behavioural sources (no devices, energy or mismatch). Design family d5_k<100k>: g5_k<100k>
with each source replaced by a static CMOS gate and an output inverter from sky130 nfet_01v8 (0.65/0.5) and
pfet_01v8 (1.0/0.5), long-channel against hot leakage: segment i (2..8) is on when the 3-bit MSB value is >= i - 1,
  >=1 NOR3+INV, >=2 NOR2+INV, >=3 AOI21+INV, >=4 INV+INV, >=5 OAI21+INV, >=6 NAND2+INV, >=7 NAND3+INV,
48 devices per side on VDD/VSS, so their leakage is in the VDD energy and they get Monte Carlo draws. The decoder
devices are appended after every r26e device, so all r26e draws (and b0) are unchanged for the same seed.
The trim code is static within a decision, so the decoder adds no switching energy or delay in a decision.

  python -B r26f_dec.py leak                                     # decoder-only DC leakage, 8 codes x 45 conditions
  python -B r26f_dec.py dnl <k>                                  # 63-code transfer at the 5 DNL conditions
  python -B r26f_dec.py kick <k>                                 # segment-gate dip at the clock edge vs ideal sources
  python -B r26f_dec.py cost <k>                                 # TT energy, writes memory_energy_d5_k<100k>.json
  python -B r26f_dec.py mc <k> <corner> <vdd> <temp> [n_seeds]   # appends out/r26b/mc_<cond>_d5_k<100k>.jsonl
  python -B r26f_dec.py refine <k> <corner> <vdd> <temp> [n]     # as r26c_refine.py
  python -B r26f_dec.py compare [n_seeds]                        # d5 vs g5 per seed; writes out/r26f/compare_*.json
"""
import json
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

import numpy as np

if (len(sys.argv) > 2 and sys.argv[1] in ("dnl", "kick", "cost", "mc", "refine")
        and re.fullmatch(r"\d+(\.\d+)?", sys.argv[2])):  # workers inherit the environment, not argv
    os.environ["R26F_K"] = sys.argv[2]
import r26e_seg as G  # noqa: E402  (strips sys.argv into G.ARGS)

ARGS = G.ARGS
R3, E, U = G.R3, G.E, G.U
OUT = G.OUT
OUT_F = R3.HERE / "out" / "r26f"
K = float(os.environ.get("R26F_K", "1.75"))
N_W, P_W = 0.65, 1.0
L_DEC = float(os.environ.get("R26F_L", "0.5"))
HOLD = float(os.environ.get("R26F_HOLD", "0"))
_BDEC = re.compile(r"^Bdec.*\n?", re.M)
_g_text, _is_g0 = G.circuit_text, G._is_g


def _is_d(name):
    return name.startswith("d") and name[1:2].isdigit()


def _mos(name, d, g, s, kind):
    w = P_W if kind == "p" else N_W
    b = "vdd" if kind == "p" else "vss"
    return (f"{name} {d} {g} {s} {b} sky130_fd_pr__{kind}fet_01v8\n+ w={{{w:g}}} l={L_DEC:g}\n"
            f"+ ad={{0.29*({w:g})}} as={{0.29*({w:g})}}\n+ pd={{2*(0.29+({w:g}))}} ps={{2*(0.29+({w:g}))}}")


def _decoder_side(side):
    """Static CMOS thermometer decoder of one side: inputs t<side>2..4 (LSB..MSB), outputs g<side>2..8."""
    b2, b3, b4 = (f"t{side}{i}" for i in (2, 3, 4))
    dev = []
    n = [0]

    def m(d, g, s, kind):
        n[0] += 1
        dev.append(_mos(f"Xdc{side}{n[0]}", d, g, s, kind))

    def inv(a, y):
        m(y, a, "vdd", "p")
        m(y, a, "vss", "n")

    def nand(ins, y, tag):
        for a in ins:
            m(y, a, "vdd", "p")
        nodes = [y] + [f"dc{side}{tag}_s{j}" for j in range(len(ins) - 1)] + ["vss"]
        for j, a in enumerate(ins):
            m(nodes[j], a, nodes[j + 1], "n")

    def nor(ins, y, tag):
        for a in ins:
            m(y, a, "vss", "n")
        nodes = ["vdd"] + [f"dc{side}{tag}_s{j}" for j in range(len(ins) - 1)] + [y]
        for j, a in enumerate(ins):
            m(nodes[j + 1], a, nodes[j], "p")

    def aoi21(a1, a2, b, y, tag):  # y = !((a1 & a2) | b)
        mn, mp = f"dc{side}{tag}_n", f"dc{side}{tag}_p"
        m(y, a1, mn, "n")
        m(mn, a2, "vss", "n")
        m(y, b, "vss", "n")
        m(mp, a1, "vdd", "p")
        m(mp, a2, "vdd", "p")
        m(y, b, mp, "p")

    def oai21(a1, a2, b, y, tag):  # y = !((a1 | a2) & b)
        mn, mp = f"dc{side}{tag}_n", f"dc{side}{tag}_p"
        m(y, a1, mn, "n")
        m(y, a2, mn, "n")
        m(mn, b, "vss", "n")
        m(mp, a1, "vdd", "p")
        m(y, a2, mp, "p")
        m(y, b, "vdd", "p")

    x = {i: f"dc{side}{i}_x" for i in range(2, 9)}
    nor((b2, b3, b4), x[2], 2)
    nor((b3, b4), x[3], 3)
    aoi21(b2, b3, b4, x[4], 4)
    inv(b4, x[5])
    oai21(b2, b3, b4, x[6], 6)
    nand((b3, b4), x[7], 7)
    nand((b2, b3, b4), x[8], 8)
    for i in range(2, 9):
        inv(x[i], f"g{side}{i}")
    return dev


def decoder_text():
    text = _decoder_side("p") + _decoder_side("n")
    if HOLD:  # optional square nfet gate capacitor on each segment gate (r26f hold study)
        text += [f"Xhc{side}{i} vss g{side}{i} vss vss sky130_fd_pr__nfet_01v8\n+ w={{{HOLD:g}}} l={HOLD:g}\n"
                 f"+ ad={{0.29*({HOLD:g})}} as={{0.29*({HOLD:g})}}\n"
                 f"+ pd={{2*(0.29+({HOLD:g}))}} ps={{2*(0.29+({HOLD:g}))}}"
                 for side in "pn" for i in range(2, 9)]
    return "\n".join(text)


def circuit_text(design):
    if not _is_d(design.name):
        return _g_text(design)
    text = _BDEC.sub("", _g_text(design))
    return text.replace(".ends atlas", decoder_text() + "\n.ends atlas")


G._is_g = lambda name: _is_g0(name) or _is_d(name)
G.D.circuit_text = G.SP.circuit_text = R3.circuit_text = circuit_text


def register(k):
    return U.register(5, k, prefix="d")


def _check_circuit(text):
    assert "Bdec" not in text and re.search(r"^Xtp8 xp \S+ sp8 vss", text, re.M)
    assert len(re.findall(r"^Xdc[pn]\d+ ", text, re.M)) == 96
    assert re.search(r"Xeq_8 [^\n]*\n(\+[^\n]*\n){3}\+ m=4", text)
    assert re.search(r"Xeq_1 [^\n]*\n(\+[^\n]*\n){3}\+ m=2", text)
    assert "+ m=16" not in text and "+ m=8" not in text


G.register, G._check_circuit = register, _check_circuit
DESIGN = register(K)


def decoder_area_um2():
    devs = [d for d in R3.devices(DESIGN) if d["name"].startswith("Xdc")]
    return len(devs), sum(d["w"] * d["l"] for d in devs)


# ---------------------------------------------------------------------------------------------------- leakage
def _includes(corner):
    out = [f'.include "{R3.PDK / "models" / "parameters" / "lod.spice"}"']
    for dev in ("nfet_01v8", "pfet_01v8"):
        stem = f"sky130_fd_pr__{dev}"
        out += [f'.include "{R3.PDK / "cells" / dev / f"{stem}__mismatch.corner.spice"}"',
                f'.include "{R3.PDK / "cells" / dev / f"{stem}__{corner}.corner.spice"}"']
    return "\n".join(out)


def _leak(cond):
    corner, vdd, temp = cond
    deck = [f"dec\n.option scale=1u\n{_includes(corner)}\n.temp {temp:g}",
            f"Vdd vdd 0 {vdd:g}", "Vss vss 0 0"]
    deck += [f"Vt{s}{i} t{s}{i} 0 0" for s in "pn" for i in (2, 3, 4)]
    deck += [decoder_text(), ".control", "set numdgt=12"]
    for code in range(8):
        deck += [f"alter Vtp{i} {vdd * (code >> (i - 2) & 1):g}" for i in (2, 3, 4)]
        deck += ["op", f"echo LK {code} $&i(Vdd) " + " ".join(f"$&v(gp{i})" for i in range(2, 9))]
    deck += ["quit 0", ".endc", ".end"]
    out, _ = R3.ngspice("\n".join(deck) + "\n")
    rows = []
    for code, i, *v in (ln.split()[1:] for ln in out.splitlines() if ln.startswith("LK ")):
        v = [float(x) for x in v]
        want = [int(code) >= i - 1 for i in range(2, 9)]
        err = max(abs(x - (vdd if w else 0.0)) for x, w in zip(v, want))
        rows.append({"code": int(code), "i_vdd_na": -float(i) * 1e9, "max_out_error_mv": err * 1e3})
    assert len(rows) == 8 and all(r["max_out_error_mv"] < 10 for r in rows), (cond, rows)
    i_max = max(r["i_vdd_na"] for r in rows)
    # both sides: one side at the code, the other at 0 (p/n decoders are identical)
    worst = i_max + rows[0]["i_vdd_na"]
    return {"cond": list(cond), "rows": rows, "both_sides_worst_na": worst,
            "energy_per_10ns_fj": worst * 1e-9 * vdd * 10e-9 * 1e15}


def leak(workers=12):
    OUT_F.mkdir(parents=True, exist_ok=True)
    conds = list(G.S.R22.conditions())
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_leak, conds))
    n, area = decoder_area_um2()
    res = {"design": DESIGN, "devices": n, "gate_area_um2": area, "conditions": rows,
           "worst": max(rows, key=lambda r: r["both_sides_worst_na"])}
    (OUT_F / f"leak_decoder_L{L_DEC:g}.json").write_text(json.dumps(res, indent=1))
    w = res["worst"]
    print(f"{n} devices, gate area {area:.2f} um^2; worst {w['cond']} {w['both_sides_worst_na']:.2f} nA "
          f"= {w['energy_per_10ns_fj']:.3f} fJ per 10 ns cycle; max out error "
          f"{max(r['max_out_error_mv'] for c in rows for r in c['rows']):.3f} mV", flush=True)


# ---------------------------------------------------------------------------------------------------- energy
def _patch_probe():
    """As r26e_cost.py: the r24_probe energy path with unit-count equalizers and this module's netlist."""
    import r24_probe as P
    _equalize = P.equalize

    def equalize(h):
        text = _equalize(h)
        text = G._EQ.sub(lambda mt: f"{mt.group(1)}\n+ m={G.units('Xeq_' + mt.group(2))}", text)
        return G._INV.sub(lambda mt: f"{mt.group(1)}\n+ m={E.INV_M}", text)

    P.equalize = equalize
    P.N.circuit_text = circuit_text
    return P


if os.environ.get("R26F_COST"):  # energy workers
    _patch_probe()


def cost():
    os.environ["R26F_COST"] = "1"
    P = _patch_probe()
    h = P.variant_header(DESIGN, "tt", 1.8, 27.0, "equalize")
    _check_circuit(h)
    assert h.count("Xeq_") == 9 and f"+ m={E.INV_M}" in h, h[-2000:]
    P.R.OUT = G.OUT
    P.energy(DESIGN, 5)


# ---------------------------------------------------------------------------------------------------- compare
def _evals(r):
    import ast
    ev = r["evals"] if isinstance(r["evals"], list) else ast.literal_eval(r["evals"])
    return {(e["v_mv"], e["deadline_ns"]): (e["outcome"], e.get("t_ns")) for e in ev}


def compare(n=200):
    OUT_F.mkdir(parents=True, exist_ok=True)
    g = U.register(5, K, prefix="g")
    rows = []
    for cond in G.S.DNL_CONDS:
        tag = f"{cond[0]}{cond[1]:g}V{cond[2]:g}C"
        rd = {r["seed"]: r for r in map(json.loads, (OUT / f"mc_{tag}_{DESIGN}.jsonl").read_text().splitlines())}
        rg = {r["seed"]: r for r in map(json.loads, (OUT / f"mc_{tag}_{g}.jsonl").read_text().splitlines())}
        seeds = sorted(s for s in rd if s < n)
        assert seeds == list(range(n)) and all(s in rg for s in seeds), (cond, len(seeds))
        same_code = same_m = same_out = 0
        dm, dt, zdiff = [], [], 0.0
        passed = static = passed_g = static_g = 0
        for s in seeds:
            a, b = rd[s], rg[s]
            za = a["z"] if isinstance(a["z"], dict) else __import__("ast").literal_eval(a["z"])
            zb = b["z"] if isinstance(b["z"], dict) else __import__("ast").literal_eval(b["z"])
            zdiff = max(zdiff, max(abs(za[k] - zb[k]) for k in zb))
            same_code += a["code"] == b["code"]
            same_m += a["m_mv"] == b["m_mv"]
            dm.append(abs(a["m_mv"] - b["m_mv"]))
            ea, eb = _evals(a), _evals(b)
            same_out += all(ea[k][0] == eb[k][0] for k in eb)
            dt += [abs(ea[k][1] - eb[k][1]) for k in eb if ea[k][1] is not None and eb[k][1] is not None]
            static += abs(a["m_mv"]) <= 1.0
            passed += ea[(-1.0, 1.0)][0] == "correct" and ea[(1.0, 1.0)][0] == "correct"
            static_g += abs(b["m_mv"]) <= 1.0
            passed_g += eb[(-1.0, 1.0)][0] == "correct" and eb[(1.0, 1.0)][0] == "correct"
        rows.append({"cond": list(cond), "n": len(seeds), "same_code": same_code, "same_m": same_m,
                     "same_outcomes": same_out, "max_abs_dm_mv": max(dm), "max_abs_dt_ps": max(dt) * 1e3,
                     "max_shared_z_diff": zdiff, "static_1mv": static, "pass_1mv_1ns": passed,
                     "static_1mv_ref": static_g, "pass_1mv_1ns_ref": passed_g})
        print(rows[-1], flush=True)
    keys = ("n", "same_code", "same_m", "same_outcomes", "static_1mv", "pass_1mv_1ns", "static_1mv_ref",
            "pass_1mv_1ns_ref")
    res = {"design": DESIGN, "reference": g, "rows": rows, "pooled": {k: sum(r[k] for r in rows) for k in keys}}
    res["pooled"]["max_abs_dm_mv"] = max(r["max_abs_dm_mv"] for r in rows)
    res["pooled"]["max_abs_dt_ps"] = max(r["max_abs_dt_ps"] for r in rows)
    (OUT_F / f"compare_{DESIGN}.json").write_text(json.dumps(res, indent=1))
    print(res["pooled"], flush=True)


# ---------------------------------------------------------------------------------------------------- kick
_KICK = ["v(xdut.gn2)", "v(xdut.gn8)", "v(xdut.tail)"]


def _kick(job):
    name, cond = job
    design = DESIGN if name == "d" else U.register(5, K, prefix="g")
    s = G._nominal(design, cond) if name == "d" else G.T._nominal(design, cond)  # G._check_circuit is d-only
    p = replace(s.base, differential_v=0.0, trim_code=-31)
    header = s.sim._header(p).replace(R3.circuit_text(R3.get_design(s.design)), s.circuit)
    header = header.replace(".save v(clk)", ".save " + " ".join(_KICK) + " v(clk)")
    lines = [header, ".control", "set wr_singlescale", "set wr_vecnames", "set numdgt=15"]
    lines += [f"alter Vt{side}{b} {cond[1] if side == 'n' else 0:.12g}" for side in "pn" for b in range(5)]
    lines += ["tran 1p 26n 21n 1p", "wrdata w.tsv " + " ".join(_KICK), "quit 0", ".endc", ".end"]
    _, files = R3.ngspice("\n".join(lines) + "\n")
    v = np.loadtxt(files["w.tsv"].splitlines(), skiprows=1)
    t, g2, g8, tail = v[:, 0], v[:, 1], v[:, 2], v[:, 3]
    edge = (t > 21.9e-9) & (t < 25e-9)
    vdd = cond[1]
    low = edge & (np.minimum(g2, g8) < vdd - 0.01)
    return {"design": design, "cond": list(cond), "gate_min_v": float(np.min(np.minimum(g2, g8)[edge])),
            "dip_mv": float((vdd - np.min(np.minimum(g2, g8)[edge])) * 1e3),
            "below_10mv_ps": float((t[low].max() - t[low].min()) * 1e12) if low.any() else 0.0,
            "tail_pre_v": float(np.interp(21.99e-9, t, tail)), "tail_post_v": float(np.interp(23e-9, t, tail))}


def kick():
    """Segment-gate dip at the clock edge (code -31, both decoder and ideal sources) at the 5 DNL conditions."""
    OUT_F.mkdir(parents=True, exist_ok=True)
    jobs = [(n, c) for c in G.S.DNL_CONDS for n in "dg"]
    with ProcessPoolExecutor(len(jobs)) as ex:
        rows = list(ex.map(_kick, jobs))
    dnl = {k: json.loads((OUT / f"dnl_{k}5_k{int(round(K * 100))}.json").read_text()) for k in "dg"}
    for r in rows:
        ref = next(x for x in dnl[r["design"][0]] if list(x["cond"]) == r["cond"])
        r["lsb_mv"] = ref["lsb_mv"]
        print(r, flush=True)
    (OUT_F / f"kick_{DESIGN}.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    U.os.environ.pop("R24_PRIOR_MV", None)
    cmd = ARGS[0] if ARGS else ""
    if cmd == "leak":
        leak()
    elif cmd == "dnl":
        G.dnl(float(ARGS[1]))
    elif cmd == "cost":
        cost()
    elif cmd == "kick":
        kick()
    elif cmd == "mc":
        G.mc(float(ARGS[1]), (ARGS[2], float(ARGS[3]), float(ARGS[4])), range(int(ARGS[5]) if len(ARGS) > 5 else 200))
    elif cmd == "refine":
        G.refine(float(ARGS[1]), (ARGS[2], float(ARGS[3]), float(ARGS[4])), *[int(a) for a in ARGS[5:6]])
    elif cmd == "compare":
        compare(*[int(a) for a in ARGS[1:2]])
    else:
        raise SystemExit(__doc__)

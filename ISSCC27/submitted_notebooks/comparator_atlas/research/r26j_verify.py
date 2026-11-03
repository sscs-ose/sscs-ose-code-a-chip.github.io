"""r26j: checks of the r26i off-gate fixes beyond the nominal table -- mismatch Monte Carlo, energy, extracted
gate-route parasitics and a DRC-rule footprint. Each variant is configured as in r26i_drv.py (R26I_MN, R26I_MP,
R26I_PH, R26F_HOLD); R26J_REF=1 selects the ideal-source reference g5_k175 instead (mcloss and para only).

  [env] python -B r26j_verify.py mcloss [n_seeds] [workers]  # paired-seed b(+/-28) at the 5 DNL conditions vs g5
                                                             # (40 seeds; R26J_SEEDS sets the table's count)
  [env] python -B r26j_verify.py mcflow [n_seeds] [workers]  # r26f calibration MC (code, residual, 1 mV / 1 ns)
  [env] python -B r26j_verify.py para [workers]              # nominal b(+/-28) with b1 bit-2 gate-net caps x 1/4
  [env] python -B r26j_verify.py energy                      # TT energy per decision (codes 0, +/-31), leakage
  python -B r26j_verify.py table                             # writes out/r26j/verify_k175.json

Mismatch pairing is r26f's: the core, trim and decoder devices keep their draws for a seed, and the hold capacitors
are appended after the decoder, so every variant and g5 share the draws of every device they have in common. A
multiplied output-stage device (m = 4) keeps one draw for all fingers (its sigma is not divided by 2: conservative).
"""
import json
import re
import shutil
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import numpy as np

import r26i_drv as V

B, F, G, U, R3 = V.B, V.F, V.G, V.U, V.R3
os = V.os
OUT_J = R3.HERE / "out" / "r26j"
OUT_J.mkdir(parents=True, exist_ok=True)
G5 = U.register(5, F.K, prefix="g")
REF = os.environ.get("R26J_REF") == "1"
DESIGN = G5 if REF else V.DESIGN
TAG = "g5" if REF else V.TAG
CODES = (28, -28)
TOL_FLOW = R3.TOL_MV
# b1 extraction (layout_single_row/v2/native-b1), trim-gate net tp2 (= tn2): the 4-unit switch, as one segment (fF)
GATE_NET_FF = {"vss": 0.7731, "s": 0.2804, "vin": 0.0774, "tail": 0.0713, "x": 0.0102}
PARA_SCALES = (1, 4)  # x0 is the r26i nominal
_para = [0]
_ct_i = V.circuit_text


def _check_g(text):
    assert text.count("Bdec") == 14 and "Xdcp1 " not in text


if REF:
    G._check_circuit = _check_g


def _para_caps(k):
    out = []
    for s in "pn":
        for i in range(2, 9):
            nodes = {"vss": "vss", "s": f"s{s}{i}", "vin": f"vin{s}", "tail": "tail", "x": f"x{s}"}
            out += [f"Cpg{s}{i}{n} g{s}{i} {nodes[n]} {k * c:.6g}f" for n, c in GATE_NET_FF.items()]
    return "\n".join(out)


def circuit_text(design):
    text = _ct_i(design)
    if _para[0] and design.name in (V.DESIGN, G5):
        text = text.replace(".ends atlas", _para_caps(_para[0]) + "\n.ends atlas")
    return text


F.circuit_text = G.D.circuit_text = G.SP.circuit_text = R3.circuit_text = circuit_text


def _sim():
    return R3.Simulator(R3.HERE / "cache" / "r3_unused", workers=1)


def _sig():
    """Per-geometry mismatch sigma: r26f's cache plus the new hold-capacitor geometries (checked against the cache)."""
    if REF:
        return json.loads((R3.OUT / f"sigma_{DESIGN}.json").read_text())
    path = OUT_J / f"sigma_{TAG}.json"
    if not path.exists():
        old, tmp = R3.OUT, OUT_J / "_sigma" / TAG
        R3.OUT = tmp
        try:
            sig = R3.sigma(DESIGN)
        finally:
            R3.OUT = old
            shutil.rmtree(tmp, ignore_errors=True)
        base = json.loads((old / f"sigma_{DESIGN}.json").read_text())
        assert set(base) <= set(sig) and all(abs(sig[k] - v) < 1e-12 for k, v in base.items()), "sigma cache differs"
        path.write_text(json.dumps(sig, indent=1))
    return json.loads(path.read_text())


def _read_jsonl(path):
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []


def _pool(fn, jobs, path, workers):
    with ProcessPoolExecutor(workers) as ex, path.open("a") as fh:
        for r in ex.map(fn, jobs):
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            print(TAG, {k: r[k] for k in r if k in ("seed", "cond", "k", "b_mv", "code", "m_mv")}, flush=True)


# ---------------------------------------------------------------------------------------------------- Monte Carlo
def _loss_job(job):
    seed, cond, sig = job
    R3.TOL_MV = B.PROBE_TOL_MV
    s = G.Paired(DESIGN, seed, _sim(), sig, tuple(cond))
    b = s.boundaries(list(CODES), lo=-100.0, hi=100.0)
    assert all(abs(v) < 99 for v in b.values()), b
    return {"design": DESIGN, "tag": TAG, "seed": seed, "cond": list(cond), "b_mv": {str(c): b[c] for c in CODES}}


def mcloss(n=20, workers=2):
    sig = _sig()
    path = OUT_J / f"_mcloss_{TAG}.jsonl"
    have = {(r["seed"], tuple(r["cond"])) for r in _read_jsonl(path)}
    jobs = [(s, list(c), sig) for s in range(n) for c in G.S.DNL_CONDS if (s, tuple(c)) not in have]
    _pool(_loss_job, jobs, path, workers)


def _flow_job(job):
    seed, cond, sig = job
    R3.TOL_MV = TOL_FLOW
    res = G.Paired(DESIGN, seed, _sim(), sig, tuple(cond)).run()
    res["tag"] = TAG
    return res


def mcflow(n=40, workers=6):
    assert not REF
    sig = _sig()
    only = [c for c in os.environ.get("R26J_CONDS", "").split(",") if c]  # e.g. "sf,ff"; default all five
    for c in [c for c in G.S.DNL_CONDS if not only or c[0] in only]:
        path = OUT_J / f"mc_{c[0]}{c[1]:g}V{c[2]:g}C_{TAG}.jsonl"
        have = {r["seed"] for r in _read_jsonl(path)}
        _pool(_flow_job, [(s, list(c), sig) for s in range(n) if s not in have], path, workers)


# ---------------------------------------------------------------------------------------------------- parasitics
def _para_job(job):
    k, cond = job
    _para[0] = k
    R3.TOL_MV = B.PROBE_TOL_MV
    s = (G.T._nominal if REF else G._nominal)(DESIGN, tuple(cond))
    assert s.circuit.count("\nCpg") == 70
    b = s.boundaries(list(CODES), lo=-60.0, hi=60.0)
    assert all(abs(v) < 59 for v in b.values()), b
    return {"design": DESIGN, "tag": TAG, "k": k, "cond": list(cond), "b_mv": {str(c): b[c] for c in CODES}}


def para(workers=4):
    path = OUT_J / f"_para_{TAG}.jsonl"
    have = {(r["k"], tuple(r["cond"])) for r in _read_jsonl(path)}
    jobs = [(k, list(c)) for k in PARA_SCALES for c in G.S.DNL_CONDS if (k, tuple(c)) not in have]
    _pool(_para_job, jobs, path, workers)


# ---------------------------------------------------------------------------------------------------- energy
def _probe_module():
    P = F._patch_probe()
    P.N.circuit_text = circuit_text
    return P


if os.environ.get("R26J_COST"):  # energy workers
    _probe_module()


def _decoder_text():
    """The decoder as this variant changes it (output-stage multipliers, nfet and pfet hold capacitors)."""
    text, n = B._OUT_INV.subn(V._scale, F.decoder_text())
    assert n == 28, n
    full = _ct_i(R3.get_design(V.DESIGN))
    caps = re.findall(r"^Xhq[^\n]*\n(?:\+[^\n]*\n?){3}", full, re.M)
    assert len(caps) == (14 if V.PH else 0)
    return text + ("\n" + "".join(caps).rstrip("\n") if caps else "")


def energy():
    assert not REF
    os.environ["R26J_COST"] = "1"
    P = _probe_module()
    h = P.variant_header(DESIGN, "tt", 1.8, 27.0, "equalize")
    V._check_circuit(h)
    assert h.count("Xeq_") == 9
    jobs = [(DESIGN, "tt", 1.8, 27.0, "equalize", c, 5) for c in (0, 31, -31)]
    with ProcessPoolExecutor(3) as ex:
        tt = {str(j[5]): e for j, e in zip(jobs, ex.map(P._energy, jobs))}
    dec, dec0 = _decoder_text(), F.decoder_text
    F.decoder_text = lambda: dec  # _leak (threads below) builds its deck from this
    try:
        with ThreadPoolExecutor(8) as ex:
            rows = list(ex.map(F._leak, list(G.S.R22.conditions())))
    finally:
        F.decoder_text = dec0
    worst = max(rows, key=lambda r: r["both_sides_worst_na"])
    res = {"design": DESIGN, "tag": TAG, "tt_equalize": tt, "leak_conditions": len(rows),
           "max_out_error_mv": max(x["max_out_error_mv"] for r in rows for x in r["rows"]),
           "leak_worst": {k: worst[k] for k in ("cond", "both_sides_worst_na", "energy_per_10ns_fj")}}
    (OUT_J / f"energy_{TAG}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1), flush=True)


# ---------------------------------------------------------------------------------------------------- footprint
# SKY130 rules (um): contacted source / drain 0.285 (licon 0.17 + licon-to-gate 0.055 + diff enclosure 0.06), shared
# source / drain between fingers 0.28, poly end cap 0.13; half diff spacing 0.135 and half poly spacing 0.105 to
# neighbours. The pfet capacitor sits in the decoder's existing n-well (no extra well spacing).
def footprint_um2(mn, mp, h, ph):
    def mos(w, length):
        return (length + 2 * 0.285 + 0.27) * (w + 2 * 0.13 + 0.21)

    def fingers(w, length, n):
        return n * (length + 0.28) * (w + 2 * 0.13 + 0.21)

    return fingers(0.65, 0.5, mn - 1) + fingers(1.0, 0.5, mp - 1) + (mos(h, h) if h else 0) + (mos(ph, ph) if ph else 0)


# ---------------------------------------------------------------------------------------------------- table
VARIANTS = ((1, 1, 0, 0), (1, 1, 1, 0), (1, 1, 1.4, 0), (1, 1, 1.72, 0), (4, 1, 1, 0), (1, 1, 1, 1), (4, 1, 1, 1))


N_FLOW = 20
PAIRS = (("d5 H1.4", "d5 N4 H1"), ("d5 H1.4", "d5 H1 PH1"), ("d5 H1.72", "d5 N4 H1 PH1"), ("d5 N4 H1", "d5 H1"))


def _tag(mn, mp, h, ph):
    return f"d5_n{mn}_p{mp}_H{h:g}_P{ph:g}"


def _label(mn, mp, h, ph):
    return " ".join(x for x in ("d5", f"N{mn}" * (mn != 1), f"P{mp}" * (mp != 1), f"H{h:g}" * (h != 0),
                                f"PH{ph:g}" * (ph != 0)) if x)


def _span(b):
    return b["28"] - b["-28"]


def table():
    conds = [list(c) for c in G.S.DNL_CONDS]
    ci = {tuple(c): i for i, c in enumerate(conds)}
    nominal = json.loads((V.OUT_I / "fixes_k175.json").read_text())["designs"]
    gref = {(r["seed"], tuple(r["cond"])): _span(r["b_mv"]) for r in _read_jsonl(OUT_J / "_mcloss_g5.jsonl")}
    pref = {(r["k"], tuple(r["cond"])): _span(r["b_mv"]) for r in _read_jsonl(OUT_J / "_para_g5.jsonl")}
    done = [{(r["seed"], tuple(r["cond"])) for r in _read_jsonl(OUT_J / f"_mcloss_{_tag(*v)}.jsonl")} for v in VARIANTS]
    seeds = sorted(s for s in {s for s, _ in gref}
                   if all((s, tuple(c)) in d for d in [set(gref)] + done for c in conds))
    n_mc = int(os.environ.get("R26J_SEEDS", "40"))
    assert seeds[:n_mc] == list(range(n_mc)), seeds
    seeds = seeds[:n_mc]
    flow_d5 = {}
    for c in conds:
        tag = f"{c[0]}{c[1]:g}V{c[2]:g}C"
        flow_d5[tuple(c)] = {r["seed"]: r for r in map(json.loads, (G.OUT / f"mc_{tag}_{V.DESIGN}.jsonl")
                                                       .read_text().splitlines())}
    e0 = json.loads((OUT_J / f"energy_{_tag(1, 1, 0, 0)}.json").read_text())
    designs = {}
    for v in VARIANTS:
        tag, lab = _tag(*v), _label(*v)
        d = {"tag": tag, "mn": v[0], "mp": v[1], "hold_um": v[2], "ph_um": v[3],
             "gate_area_um2": round(V.area_um2(*v), 3), "footprint_um2": round(footprint_um2(*v), 3),
             "nominal_worst_pct": nominal[lab]["worst_loss_pct"],
             "nominal_loss_pct": [r["seg_loss_pct"] for r in nominal[lab]["rows"]]}
        rows = _read_jsonl(OUT_J / f"_mcloss_{tag}.jsonl")
        loss = np.full((len(seeds), len(conds)), np.nan)
        for r in rows:
            if r["seed"] in seeds:
                loss[seeds.index(r["seed"]), ci[tuple(r["cond"])]] = 100 * (
                    1 - _span(r["b_mv"]) / gref[(r["seed"], tuple(r["cond"]))])
        assert not np.isnan(loss).any(), (tag, int(np.isnan(loss).sum()))
        d["mc"] = {"n_seeds": len(seeds), "mean_pct": loss.mean(0).tolist(), "sd_pct": loss.std(0, ddof=1).tolist(),
                   "min_pct": loss.min(0).tolist(), "max_pct": loss.max(0).tolist(),
                   "per_seed_worst_pct": loss.max(1).tolist(), "per_seed_hot_pct": loss[:, 3:].max(1).tolist()}
        para_rows = {(r["k"], tuple(r["cond"])): _span(r["b_mv"]) for r in _read_jsonl(OUT_J / f"_para_{tag}.jsonl")}
        d["para"] = {str(k): [100 * (1 - para_rows[(k, tuple(c))] / pref[(k, tuple(c))]) for c in conds]
                     for k in PARA_SCALES}
        d["para"]["0"] = d["nominal_loss_pct"]
        d["para_worst_abs_pct"] = {k: max(abs(x) for x in v) for k, v in d["para"].items()}
        en = json.loads((OUT_J / f"energy_{tag}.json").read_text())
        d["energy"] = {"tt_vdd_fj": {c: en["tt_equalize"][c]["vdd_fj"] for c in ("0", "31", "-31")},
                       "tt_vdd_delta_fj": max(abs(en["tt_equalize"][c]["vdd_fj"] - e0["tt_equalize"][c]["vdd_fj"])
                                              for c in ("0", "31", "-31")),
                       "leak_worst_na": en["leak_worst"]["both_sides_worst_na"],
                       "leak_worst_cond": en["leak_worst"]["cond"],
                       "leak_fj_per_10ns": en["leak_worst"]["energy_per_10ns_fj"],
                       "max_out_error_mv": en["max_out_error_mv"]}
        flow = []
        for c in conds:
            p = OUT_J / f"mc_{c[0]}{c[1]:g}V{c[2]:g}C_{tag}.jsonl"
            ref = flow_d5[tuple(c)]
            if v == VARIANTS[0]:  # d5 itself: r26b's calibration Monte Carlo on the same seeds
                rd = {s: ref[s] for s in range(N_FLOW)}
            elif p.exists():
                rd = {r["seed"]: r for r in _read_jsonl(p)}
            else:
                continue
            row = {"cond": c, "n": len(rd), "same_code": 0, "static_1mv": 0, "pass_1mv_1ns": 0, "static_1mv_d5": 0,
                   "pass_1mv_1ns_d5": 0, "max_abs_m_mv": 0.0, "max_abs_dm_mv": 0.0}
            for s, a in rd.items():
                b = ref[s]
                ea, eb = F._evals(a), F._evals(b)
                row["same_code"] += a["code"] == b["code"]
                row["static_1mv"] += abs(a["m_mv"]) <= 1.0
                row["static_1mv_d5"] += abs(b["m_mv"]) <= 1.0
                row["pass_1mv_1ns"] += ea[(-1.0, 1.0)][0] == "correct" and ea[(1.0, 1.0)][0] == "correct"
                row["pass_1mv_1ns_d5"] += eb[(-1.0, 1.0)][0] == "correct" and eb[(1.0, 1.0)][0] == "correct"
                row["max_abs_m_mv"] = max(row["max_abs_m_mv"], abs(a["m_mv"]))
                row["max_abs_dm_mv"] = max(row["max_abs_dm_mv"], abs(a["m_mv"] - b["m_mv"]))
            flow.append(row)
        d["flow"] = flow
        designs[lab] = d
        mc = d["mc"]
        print(f"{lab:16s} gate {d['gate_area_um2']:.2f} fp {d['footprint_um2']:.2f} nominal worst "
              f"{d['nominal_worst_pct']:.2f} MC mean " + "/".join(f"{x:.2f}" for x in mc["mean_pct"])
              + f" sd max {max(mc['sd_pct']):.3f} seed-worst max {max(mc['per_seed_worst_pct']):.2f} para worst "
              + " ".join(f"x{k} {v:.2f}" for k, v in d["para_worst_abs_pct"].items())
              + f" dE {d['energy']['tt_vdd_delta_fj']:.2f} fJ leak {d['energy']['leak_worst_na']:.2f} nA"
              + (f" flow {sum(r['pass_1mv_1ns'] for r in flow)}/{sum(r['n'] for r in flow)}" if flow else ""))
    pairs = {}
    for a, b in PAIRS:
        wa, wb = (np.array(designs[x]["mc"]["per_seed_worst_pct"]) for x in (a, b))
        pairs[f"{a} < {b}"] = {"seeds": int((wa < wb).sum()), "n": len(seeds),
                               "mean_diff_pct": float((wa - wb).mean()), "sd_diff_pct": float((wa - wb).std(ddof=1))}
        print(f"{a} < {b}: {pairs[f'{a} < {b}']}", flush=True)
    res = {"conds": conds, "seeds": seeds, "gate_net_ff": GATE_NET_FF, "para_scales": list(PARA_SCALES),
           "designs": designs, "worst_rank_pairs": pairs}
    (OUT_J / "verify_k175.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    U.os.environ.pop("R24_PRIOR_MV", None)
    cmd, rest = (B.ARGS[0], [int(a) for a in B.ARGS[1:]]) if B.ARGS else ("", [])
    if cmd not in ("mcloss", "mcflow", "para", "energy", "table"):
        raise SystemExit(__doc__)
    globals()[cmd](*rest)

"""r26c: statistical confidence of the unit-cell trim over 200 paired MC seeds at all five DNL conditions (adds
the cold SS/FS corners to r26b), for u5_k150 (r26b) and e5_k150 (unit-cell equalizer, r26c_eqscale.py).

Two pass criteria per seed: static, |m| <= 1 mV (m re-bisected to 0.01 mV by r26c_refine.py where borderline,
else the r3 0.2 mV bisection, +-0.12 mV); and dynamic, both +-1 mV inputs decided correctly within 1 ns (the r3
evals at the coarse code, as in r26b; a small |v - m| can leave the latch unresolved at 1 ns). Exact
Clopper-Pearson 95% intervals over seeds. Misses are attributed to the nominal transfer step at the chosen code.

  python -B r26c_stats.py [design] [n_seeds]   # writes out/r26c/seeds_<design>.jsonl and out/r26c/stats_<design>.json
  python -B r26c_stats.py sweep                # clkb inverter sweep of e5_k150 -> out/r26c/inv_sweep.json
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SRC = HERE / "out" / "r26b"
OUT = HERE / "out" / "r26c"
CONDS = (("tt", 1.8, 27.0), ("ss", 1.62, -40.0), ("fs", 1.62, -40.0), ("sf", 1.95, 125.0), ("ff", 1.95, 125.0))


def _cdf(k, n, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def _solve(f, target):
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) > target else (lo, mid)
    return (lo + hi) / 2


def clopper_pearson(k, n, alpha=0.05):
    lower = 0.0 if k == 0 else _solve(lambda p: _cdf(k - 1, n, p), 1 - alpha / 2)
    upper = 1.0 if k == n else _solve(lambda p: _cdf(k, n, p), alpha / 2)
    return lower, upper


def _tag(cond):
    return f"{cond[0]}{cond[1]:g}V{cond[2]:g}C"


def _outcomes(r, band):
    return [e["outcome"] for e in sorted(r["evals"], key=lambda e: e["v_mv"])
            if abs(e["v_mv"]) == band and e["deadline_ns"] == 1.0]


def compact(design, n):
    """Per-seed summary of the raw MC (+ refinement); the raw files keep every eval and the mismatch draw."""
    out = []
    for cond in CONDS:
        path = SRC / f"mc_{_tag(cond)}_{design}.jsonl"
        if not path.exists():
            continue
        rows = {r["seed"]: r for r in map(json.loads, path.read_text().splitlines())}
        ref = SRC / f"refine_{_tag(cond)}_{design}.jsonl"
        fine = {f["seed"]: f for f in map(json.loads, ref.read_text().splitlines())} if ref.exists() else {}
        for s in range(n):
            if s not in rows:
                continue
            r = rows[s]
            o1, o3 = _outcomes(r, 1), _outcomes(r, 3)
            rec = {"design": design, "cond": list(cond), "seed": s, "covered": r["covered"], "b0_mv": r["b0_mv"],
                   "candidates": r["candidates"], "code": r["code"], "m_mv": r["m_mv"],
                   "out_1mv_1ns": o1, "out_3mv_1ns": o3}
            if s in fine:
                rec.update(fine_code=fine[s]["code"], fine_m_mv=fine[s]["m_mv"])
            out.append(rec)
    return out


def _transfer(design):
    data = json.loads((SRC / f"dnl_{design}.json").read_text())
    return {tuple(r["cond"])[0]: {int(c): v for c, v in r["b_mv"].items()} for r in data}


def summarize(seeds, transfer):
    m = np.array([r.get("fine_m_mv", r["m_mv"]) for r in seeds])
    n = len(seeds)
    k_static = int(np.sum(np.abs(m) <= 1.0))
    k1 = sum(all(o == "correct" for o in r["out_1mv_1ns"]) for r in seeds)
    k3 = sum(all(o == "correct" for o in r["out_3mv_1ns"]) for r in seeds)
    dec = [o for r in seeds for o in r["out_1mv_1ns"]]
    row = {"n": n, "covered": sum(r["covered"] for r in seeds), "static_1mv": k_static,
           "static_1mv_ci95": [round(x, 4) for x in clopper_pearson(k_static, n)],
           "pass_1mv_1ns": k1, "pass_1mv_1ns_ci95": [round(x, 4) for x in clopper_pearson(k1, n)],
           "pass_3mv_1ns": k3, "pass_3mv_1ns_lower95": round(clopper_pearson(k3, n)[0], 4),
           "decisions_1mv_1ns": {o: dec.count(o) for o in ("correct", "wrong", "unresolved")},
           "rms_m_mv": round(float(np.sqrt(np.mean(m ** 2))), 3), "max_abs_m_mv": round(float(np.max(np.abs(m))), 3),
           "sigma_b0_mv": round(float(np.std([r["b0_mv"] for r in seeds], ddof=1)), 2)}
    if transfer is not None:
        row["nominal_max_step_mv"] = round(max(abs(transfer[c] - transfer[c - 1]) for c in transfer if c - 1 in transfer), 3)
        row["static_misses"] = [{"seed": r["seed"], "code": r.get("fine_code", r["code"]),
                                 "m_mv": round(r.get("fine_m_mv", r["m_mv"]), 3)}
                                for r, mm in zip(seeds, m) if abs(mm) > 1.0]
    return row


def stats(design="u5_k150", n=200):
    OUT.mkdir(parents=True, exist_ok=True)
    seeds = compact(design, n)
    (OUT / f"seeds_{design}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in seeds))
    transfer = _transfer(design)
    report = {"design": design, "n_seeds": n, "conditions": []}
    for cond in CONDS:
        part = [r for r in seeds if tuple(r["cond"]) == cond]
        if part:
            report["conditions"].append({"cond": list(cond), **summarize(part, transfer[cond[0]])})
    report["pooled"] = summarize(seeds, None)
    (OUT / f"stats_{design}.json").write_text(json.dumps(report, indent=1))
    return report


def sweep(design="e5_k150"):
    rows = []
    for inv in (1, 2, 4, 8):
        t = "" if inv == 4 else f"_i{inv}"
        fine = json.loads((SRC / f"fine_transfer_{design}{t}.json").read_text())
        e = json.loads((SRC / f"memory_energy_{design}{t}.json").read_text())["equalize 0"]
        mem = json.loads((SRC / f"memory_{design}{t}.json").read_text())["equalize"]["decision_uv"]
        row = {"inv_m": inv, "energy_fj_code0": round(e["vdd_fj"] + e["clk_fj"], 1), "memory_uv": mem}
        for c in ("ss", "tt", "sf"):
            st = [abs(fine[c][str(i + 1)] - fine[c][str(i)]) for i in range(11)]
            row[f"{c}_step_min_mean_max_mv"] = [round(min(st), 3), round(float(np.mean(st)), 3), round(max(st), 3)]
        rows.append(row)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "inv_sweep.json").write_text(json.dumps(rows, indent=1))
    return rows


if __name__ == "__main__":
    if sys.argv[1:2] == ["sweep"]:
        for r in sweep():
            print(r)
        raise SystemExit
    rep = stats(*(sys.argv[1:2] or ["u5_k150"]), *([int(sys.argv[2])] if len(sys.argv) > 2 else []))
    for c in rep["conditions"] + [dict(rep["pooled"], cond=["pooled"])]:
        print(f"{c['cond'][0]:>6} n={c['n']:4d} cov={c['covered']:4d} static={c['static_1mv']:4d} {c['static_1mv_ci95']} "
              f"1mV@1ns={c['pass_1mv_1ns']:4d} {c['pass_1mv_1ns_ci95']} 3mV@1ns={c['pass_3mv_1ns']:4d} "
              f"dec={c['decisions_1mv_1ns']} rms={c['rms_m_mv']:.2f} max={c['max_abs_m_mv']:.2f} "
              f"misses={[(x['seed'], x['m_mv']) for x in c.get('static_misses', [])]}")

"""r22: does the selected design's trim range cover random mismatch at its narrowest PVT corners?

r21 found that, under an exact +4 % current skew, lvt_balanced_4b reaches the end of its +/-15 trim
range at SF 1.95 V 125 C. A fixed skew is not random mismatch, and r3 measured random-mismatch
coverage only at TT 1.8 V 27 C (100/100) and SS 1.62 V -40 C (40/40). Here:
  range : nominal devices, no skew; switching input (mV) of codes -max, 0, +max at 3.5 ns for the
          three sealed designs at the 45 PVT conditions (the trim range in mV, per condition)
  mc    : r3's local-mismatch Monte Carlo (same per-device Pelgrom vth0 sigma, same seeds) at chosen
          corners; the code is chosen as in r3 (zero-input scan, then the code with the smallest boundary)
Local only; the sealed record is unchanged.
  python -B r22_range_mc.py range
  python -B r22_range_mc.py mc <design> <corner> <vdd> <T> <start> <n>
  python -B r22_range_mc.py report
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r3_mismatch_mc as R3  # noqa: E402

OUT = R3.HERE / "out" / "r22"
DESIGNS3 = ("baseline", "lvt_base_3b", "lvt_balanced_4b")
LIMIT_MV = 150.0
_devices = R3.devices
BASELINE_PARAMS = {"pair_skew": 0.0, "input_w": 2.0, "input_l": 0.15, "trim_l": 1.0}  # baseline subckt defaults


def devices(design: str):
    """r3's device parser, extended to the hand-written baseline netlist (parameterised geometry)."""
    if design != "baseline":
        return _devices(design)
    lines = R3.circuit_text(R3.get_design(design)).splitlines()
    found = []
    for i, line in enumerate(lines):
        m = R3.MOS.match(line)
        if m:
            geo = R3.re.match(r"\+ w=(\S+) l=(\S+)", lines[i + 1])
            w, length = (float(eval(g.strip("{}"), {}, BASELINE_PARAMS)) for g in geo.groups())
            found.append({"name": m.group(1), "nodes": m.group(2, 3, 4, 5), "device": m.group(6),
                          "w": w, "l": length})
    return found


R3.devices = devices


def conditions() -> list:
    """The 45 PVT conditions of the sealed atlas (its +4 % skew cases)."""
    from comparator_atlas.experiments import cases
    conds = [(p.corner, p.vdd_v, p.temperature_c) for p in cases("full") if p.pair_skew == 0.04]
    assert len(conds) == 45, len(conds)
    return conds


def nominal_range(job) -> dict:
    design, cond = job
    sig = {f"{d['device']}|{d['w']:.6g}|{d['l']:.6g}": 0.0 for d in devices(design)}
    sample = R3.Sample(design, 0, R3.Simulator(R3.HERE / "cache" / "r3_unused", workers=1), sig, cond)
    mx = R3.get_design(design).max_code
    b = sample.boundaries([-mx, 0, mx], lo=-LIMIT_MV, hi=LIMIT_MV)
    row = {"design": design, "cond": list(cond), "max_code": mx,
           "b_neg_mv": b[-mx], "b0_mv": b[0], "b_pos_mv": b[mx],
           "half_range_mv": min(abs(b[-mx] - b[0]), abs(b[mx] - b[0]))}
    print(json.dumps(row), flush=True)
    return row


def run_range() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "range.jsonl"
    done = set()
    if path.exists():
        done = {(r["design"], tuple(r["cond"])) for r in map(json.loads, path.read_text().splitlines())}
    jobs = [(d, c) for d in DESIGNS3 for c in conditions() if (d, c) not in done]
    with ThreadPoolExecutor(max_workers=12) as pool, path.open("a") as f:
        for row in pool.map(nominal_range, jobs):
            f.write(json.dumps(row) + "\n")
            f.flush()


def run_mc(design: str, cond: tuple, start: int, n: int) -> None:
    R3.OUT = OUT
    OUT.mkdir(parents=True, exist_ok=True)
    sig = R3.HERE / "out" / "r3" / f"sigma_{design}.json"
    (OUT / sig.name).write_text(sig.read_text())  # same per-device sigma as r3
    R3.run(design, start, n, cond)


def report() -> dict:
    rng = [json.loads(line) for line in (OUT / "range.jsonl").read_text().splitlines()]
    rep = {"range": {}, "mc": {}}
    for d in DESIGNS3:
        rs = sorted((r for r in rng if r["design"] == d), key=lambda r: r["half_range_mv"])
        h = np.array([r["half_range_mv"] for r in rs])
        rep["range"][d] = {"n": len(rs), "min_mv": float(h.min()), "median_mv": float(np.median(h)),
                           "max_mv": float(h.max()), "narrowest": [[*r["cond"], r["half_range_mv"]] for r in rs[:5]]}
        print(f"{d:16s} half-range min/median/max {h.min():.1f}/{np.median(h):.1f}/{h.max():.1f} mV; narrowest "
              + "; ".join(f"{r['cond'][0]} {r['cond'][1]:g} V {r['cond'][2]:g} C {r['half_range_mv']:.1f}"
                          for r in rs[:3]))
    files = sorted(OUT.glob("mc_*.jsonl")) + sorted((R3.HERE / "out" / "r3").glob("mc_*lvt_balanced_4b*.jsonl"))
    rows = [json.loads(line) for f in files for line in f.read_text().splitlines()]
    groups = {}
    for r in rows:
        groups.setdefault((r["design"], tuple(r.get("cond", ("tt", 1.8, 27.0)))), {})[r["seed"]] = r
    for (d, c), by_seed in sorted(groups.items()):
        rs = list(by_seed.values())
        n = len(rs)
        b0 = np.array([r["b0_mv"] for r in rs])
        m = np.abs([r["m_mv"] for r in rs])
        cov = sum(r["covered"] for r in rs)
        out_of = sorted(r["seed"] for r in rs if not r["covered"])
        one = [e for r in rs for e in r["evals"] if abs(e["v_mv"]) == 1 and e["deadline_ns"] == 1.0]
        three = [e for r in rs for e in r["evals"] if abs(e["v_mv"]) == 3 and e["deadline_ns"] == 1.0]
        key = f"{d}@{c[0]}|{c[1]:g}V|{c[2]:g}C"
        rep["mc"][key] = {"n": n, "seeds": [min(by_seed), max(by_seed)], "sigma_b0_mv": float(b0.std(ddof=1)),
                          "max_abs_b0_mv": float(np.abs(b0).max()), "covered": cov, "uncovered_seeds": out_of,
                          "coverage_ci95": R3.wilson(cov, n), "abs_m_median_mv": float(np.median(m)),
                          "abs_m_max_mv": float(m.max()),
                          "correct_1mV_1ns": [sum(e["outcome"] == "correct" for e in one), len(one)],
                          "correct_3mV_1ns": [sum(e["outcome"] == "correct" for e in three), len(three)]}
        v = rep["mc"][key]
        print(f"MC {key}: n={n} sigma(b0)={v['sigma_b0_mv']:.2f} mV covered {cov}/{n} {out_of} "
              f"|m| med/max {v['abs_m_median_mv']:.2f}/{v['abs_m_max_mv']:.2f} mV "
              f"+/-1 mV@1ns {v['correct_1mV_1ns']} +/-3 mV@1ns {v['correct_3mV_1ns']}")
    (OUT / "r22_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    return rep


if __name__ == "__main__":
    if ARGS[0] == "range":
        run_range()
    elif ARGS[0] == "mc":
        run_mc(ARGS[1], (ARGS[2], float(ARGS[3]), float(ARGS[4])), int(ARGS[5]), int(ARGS[6]))
    elif ARGS[0] == "report":
        report()

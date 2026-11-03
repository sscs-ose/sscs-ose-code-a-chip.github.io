"""Voltage-aware glitch-aware register placement: choose the placement *and* the supply together.

Timing slack can be spent two ways: on removing glitches (registers where glitches are born) or on a lower supply
(registers that shorten the critical path).  GlitchScope's normal search optimises at a fixed supply.  Here:

  search   for tighter timing targets T, rerun the measured placement search on the 16x16 multiplier
           (arrival-time cuts + calibrated MILP), so the candidate set spans the energy/critical-path trade-off
           -> data/glitchfix/mul16_vdd/T<T>_{cuts,milp}.v and search_T<T>.json
  corners  measure every candidate (and the original, minimum-register and timing-driven retiming) with the PDK's
           -40 C Liberty corners at every characterised supply (ss 1.28-1.76 V, ff 1.56-1.95 V): energy per cycle
           and critical path -> data/glitchfix/mul16_vdd/corners.json
  select   for each throughput (clock = the original's critical path at each characterised supply), each design runs
           at the lowest supply that meets the clock (log-interpolated, never below the lowest characterised one);
           the voltage-aware choice is the lowest-energy measured placement at its own lowest supply, the reference
           retimings included -> data/glitchfix/mul16_vdd/select.json

    python scripts/vdd_aware_study.py search  <liberty> 5500        (one target per process; run several in parallel)
    python scripts/vdd_aware_study.py corners <PDK lib dir>
    python scripts/vdd_aware_study.py select
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.optimize import GlitchFix  # noqa: E402

OUT = ROOT / "data/glitchfix/mul16_vdd"
BASE = ROOT / "data/glitchfix/mul16_r"
NETLIST = ROOT / "bench/layout/mul16_v0.v"
FAMILIES = {"ss_n40C": ["1v28", "1v40", "1v60", "1v76"], "ff_n40C": ["1v56", "1v65", "1v76", "1v95"]}
VECTORS, SAMPLE = 40, 16


def cmd_search(lib, T):
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    fx = GlitchFix(NETLIST, lib, random_vectors=60, period_ps=15000, latency=0, sample=12, grid=10,
                   workdir=OUT / f"work_{T}")
    base, classic, best = fx.search(T=float(T))
    refs = [base, fx.min_register, classic, best, getattr(fx, "best_cuts", None), getattr(fx, "best_milp", None)]
    base, minreg, classic, best, bc, bm = fx.remeasure(refs, 40)
    row = dict(T_ps=float(T), seconds=round(time.time() - t0, 1))
    for k, c in (("cuts", bc), ("milp", bm)):
        if c is not None and c.energy and c.text:
            (OUT / f"T{T}_{k}.v").write_text(c.text)
            row[k] = c.row()
    (OUT / f"search_T{T}.json").write_text(json.dumps(row, indent=1))
    import shutil
    shutil.rmtree(OUT / f"work_{T}", ignore_errors=True)
    print(json.dumps({k: (v.get("flops"), round(v.get("total", 0)), round(v.get("period_ps", 0))) for k, v in row.items()
                      if isinstance(v, dict)}))


def designs():
    d = {"original": NETLIST, "min_register": BASE / "min_register.v", "timing_driven": BASE / "timing_driven.v",
         "gs_cuts": BASE / "best_cuts.v", "gs_milp": BASE / "best_milp.v"}
    for f in sorted(OUT.glob("T*_*.v")):
        d["gs_" + f.stem] = f
    return {k: v for k, v in d.items() if v.exists()}


def cmd_corners(libdir):
    out = OUT / "corners.json"
    res = json.loads(out.read_text()) if out.exists() else {}
    for fam, volts in FAMILIES.items():
        for v in volts:
            corner = f"{fam}_{v}"
            lib = Path(libdir) / f"sky130_fd_sc_hd__{corner}.lib"
            probe = GlitchFix(NETLIST, lib, random_vectors=VECTORS, period_ps=100000, sample=2, grid=2, log=lambda m: None)
            crit = probe.timing.analyze([e[3] for e in probe.rg.edges])[2]
            period = round(1.25 * crit / 100.0) * 100.0
            for k, path in designs().items():
                key = f"{corner}|{k}"
                if key in res:
                    continue
                fx = GlitchFix(path, lib, random_vectors=VECTORS, period_ps=period, sample=SAMPLE, grid=2, log=lambda m: None)
                c = fx.original()
                res[key] = dict(corner=corner, design=k, vdd=float(v[0] + "." + v[2:]), total=c.energy["total"],
                                glitch=c.energy["glitch"], flops=c.n_flops, critical_path_ps=round(c.period_ps, 1))
                out.write_text(json.dumps(res, indent=1))
                print(f"{corner:14s} {k:16s} {c.energy['total'] / 1e3:7.2f} pJ  crit {c.period_ps / 1e3:6.2f} ns  "
                      f"{c.n_flops} flops", flush=True)


def lowest_supply(rows, T):
    """rows: [(vdd, crit_ps, energy)] of one design in one family -> (vdd, energy) at the lowest supply meeting T."""
    rows = sorted(rows)
    V = np.array([r[0] for r in rows]); c = np.array([r[1] for r in rows]); e = np.array([r[2] for r in rows])
    if T < c.min():
        return None
    v = V.min() if T >= c.max() else float(np.interp(np.log(T), np.log(c[::-1]), V[::-1]))
    return v, float(np.interp(v, V, e))


def cmd_select():
    R = json.loads((OUT / "corners.json").read_text())
    out = {}
    for fam in FAMILIES:
        per = {}
        for r in R.values():
            if r["corner"].startswith(fam):
                per.setdefault(r["design"], []).append((r["vdd"], r["critical_path_ps"], r["total"]))
        clocks = [c for _, c, _ in sorted(per["original"])]
        rows = []
        for T in clocks:
            at = {k: lowest_supply(v, T) for k, v in per.items()}
            o = at["original"][1]
            gs = {k: v for k, v in at.items() if v is not None and k not in ("original",)}
            pick = min(gs, key=lambda k: gs[k][1])
            row = dict(clock_ns=round(T / 1e3, 2), original=dict(vdd=at["original"][0], energy_pJ=o / 1e3),
                       designs={k: dict(vdd=round(v[0], 3), energy_pJ=round(v[1] / 1e3, 2), saving=round(1 - v[1] / o, 3))
                                for k, v in gs.items()},
                       vdd_aware_choice=pick, vdd_aware_saving=round(1 - gs[pick][1] / o, 3))
            fixed = [k for k in gs if k in ("gs_milp",)]
            if fixed:
                row["fixed_supply_choice_saving"] = row["designs"]["gs_milp"]["saving"]
            rows.append(row)
            print(f"{fam} clock {row['clock_ns']:6.2f} ns: " + "  ".join(
                f"{k} {row['designs'][k]['vdd']:.2f} V {100 * row['designs'][k]['saving']:4.0f} %"
                for k in sorted(row["designs"])) + f"   -> {pick}")
        out[fam] = rows
    (OUT / "select.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "search":
        cmd_search(sys.argv[2], sys.argv[3])
    elif mode == "corners":
        cmd_corners(sys.argv[2])
    else:
        cmd_select()

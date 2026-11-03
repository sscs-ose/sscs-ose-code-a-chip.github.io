"""Glitch-aware retiming on standard sequential benchmarks, in the setting of GLOW
(Liu et al., IWLS/ICCAD 2026): every design must meet a target clock period that needs
retiming, and the question is which legal retiming burns the least power.

For each circuit (mapped by bench/fetch_benchmarks.py):
  T_min    shortest period any legal retiming reaches (same static-timing model)
  T        target = factor x T_min (default 1.1)
  classic  Leiserson-Saxe minimum-register retiming meeting T (exact: LP with lazily added
           critical-path constraints, no glitch term)
  timing   timing-driven (FEAS) retiming meeting T
  ours     the lowest measured of classic, timing and the measurement-calibrated MILP
           retiming meeting T (glitchscope.milp_retime; neighbourhood search when the full
           program finds no solution in time)
Both are written as netlists, verified cycle by cycle against the original and measured
by event simulation (M2 + flip-flop and clock-tree energy) on the same random stimulus.

    python scripts/retiming_benchmarks.py <liberty> [--factor F] [name ...]

Writes data/benchmarks/retiming.json.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.optimize import GlitchFix  # noqa: E402

NET = ROOT / "bench/external/netlists"
ITC_SET = ["b03", "b04", "b08", "b11", "b14", "b20", "b21", "b22"]


AREA_TIE = 0.05


def run(lib, name, factor, cycles, sample, iters, time_limit):
    t0 = time.time()
    probe = GlitchFix(NET / f"{name}.v", lib, random_vectors=cycles, period_ps=10000, sample=4, grid=4,
                      log=lambda m: None)
    t_orig = probe.timing.analyze([e[3] for e in probe.rg.edges])[2]
    t_min = probe.min_period()
    if factor <= 0:      # at the original design's own period (its registers already meet it)
        from glitchscope.milp_retime import model_arrival
        t = model_arrival(probe.rg, probe._delays, [e[3] for e in probe.rg.edges], probe.c2q_ps,
                          probe.timing.in_delay)
        T = round(max(t[:probe.rg.C]) + probe.timing.setup + 1.0, 1)
    else:
        T = round(factor * t_min, 1)
    fx = GlitchFix(NET / f"{name}.v", lib, random_vectors=cycles, period_ps=T, sample=sample, grid=4,
                   log=lambda m: print(m, flush=True))
    base = fx.original()
    fx.min_period()                                       # keeps a FEAS retiming as a fallback reference
    tl = max(time_limit, fx.rg.C / 25.0)
    from glitchscope.milp_retime import feas
    r = feas(fx.rg, fx._delays, T, fx.c2q_ps, fx.timing.setup, fx.timing.in_delay, fx.latency)
    timing = fx.measure(fx.candidate(r, "timing-driven (FEAS)")) if r is not None else None
    classic = fx.classic_min_area(T, time_limit=max(300.0, tl))
    ref_kind = "min-register (exact)"
    if classic is None:                                   # MILP timed out: timing-driven retiming instead
        classic, ref_kind = timing, "timing-driven (FEAS)"
    mb = fx.milp_search(T, base=base, iters=iters, time_limit=tl,
                        start=[classic] if classic is not None and classic.local else ())
    ours = fx.select([classic, timing, mb], tie=AREA_TIE)  # the tool's own rule (fewest flops within 5 %)
    import os
    if os.environ.get("GS_SAVE_NETLISTS"):                # keep the netlists (e.g. for a SPICE check); stay local
        sd = Path(os.environ["GS_SAVE_NETLISTS"]) / f"{name}@{factor}"
        sd.mkdir(parents=True, exist_ok=True)
        for tag, c in (("min_register", classic), ("feas", timing), ("glitchscope", ours)):
            if c is not None and getattr(c, "text", None):
                (sd / f"{tag}.v").write_text(c.text)
    row = dict(name=name, cells=fx.rg.C, flops=len(fx.design.flops), period_original_ps=round(t_orig, 1),
               period_min_ps=round(t_min, 1), target_ps=T, cycles=len(fx.sample_idx),
               original=base.row(), original_meets_target=t_orig <= T,
               classic=classic.row() if classic is not None else None,
               glitchscope=ours.row() if ours is not None else None, reference=ref_kind,
               timing_driven=timing.row() if timing is not None and timing.energy else None,
               milp_best=mb.row() if mb is not None and mb.energy else None, seconds=round(time.time() - t0, 1))
    if classic is not None and ours is not None and classic.energy and ours.energy:
        row["saving_vs_classic"] = 1 - ours.energy["total"] / classic.energy["total"]
    if timing is not None and ours is not None and timing.energy and ours.energy:
        row["saving_vs_timing_driven"] = 1 - ours.energy["total"] / timing.energy["total"]
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lib")
    ap.add_argument("names", nargs="*")
    ap.add_argument("--factor", type=float, default=1.1,
                    help="target period = factor x minimum period; 0 = the original design's own period")
    ap.add_argument("--cycles", type=int, default=40)
    ap.add_argument("--sample", type=int, default=16)
    ap.add_argument("--iters", type=int, default=3)
    ap.add_argument("--time-limit", type=float, default=90.0)
    a = ap.parse_args()
    import os
    out = Path(os.environ["GS_RETIME_OUT"]) if os.environ.get("GS_RETIME_OUT") else ROOT / "data/benchmarks/retiming.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    res = json.loads(out.read_text()) if out.exists() else {}
    for n in a.names or ITC_SET:
        print(f"== {n}", flush=True)
        try:
            row = run(a.lib, n, a.factor, a.cycles, a.sample, a.iters, a.time_limit)
        except Exception as e:                       # noqa: BLE001
            import traceback
            traceback.print_exc()
            print(f"{n} FAILED {e}", flush=True)
            continue
        row["factor"] = a.factor
        res[f"{n}@{a.factor}"] = row
        out.write_text(json.dumps(res, indent=1))
        c, g = row["classic"] or {}, row["glitchscope"] or {}
        print(f"{n:6s} {row['cells']:6d} cells {row['flops']:5d} flops  T_min {row['period_min_ps']:7.0f}  "
              f"T {row['target_ps']:7.0f}  classic {c.get('total', 0):9.1f} fJ ({c.get('flops')} ff)  "
              f"ours {g.get('total', 0):9.1f} fJ ({g.get('flops')} ff)  "
              f"saving {100 * row.get('saving_vs_classic', 0):5.1f} % (vs timing-driven "
              f"{100 * row.get('saving_vs_timing_driven', 0):5.1f} %)  {row['seconds']:.0f} s", flush=True)


if __name__ == "__main__":
    main()

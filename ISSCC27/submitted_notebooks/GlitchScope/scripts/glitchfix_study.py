"""Closed-loop glitch-power reduction study: glitch-aware register placement vs the
original design, min-register retiming and timing-driven (minimum-period) retiming,
all measured by GlitchScope on the same stimulus and verified cycle by cycle.

    python scripts/glitchfix_study.py <liberty> [case ...]

Cases: mul16_r (registered 16x16 multiplier, retiming), mul16_p (same, +1 cycle
pipelining), mac (registered MAC with its testbench, retiming), mul4_p
(combinational 4x4 multiplier, +1 cycle pipelining).  Writes
data/glitchfix/<case>/{optimize.json, optimized.v, timing_driven.v, min_register.v}.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.optimize import GlitchFix, write_result  # noqa: E402

CASES = {
    "mul16_r": dict(netlist="bench/layout/mul16_v0.v", random_vectors=60, period_ps=15000, latency=0,
                    margin=0.15, grid=10, sample=12, final=40),
    "mul16_p": dict(netlist="bench/layout/mul16_v0.v", random_vectors=60, period_ps=15000, latency=1,
                    margin=0.15, grid=10, sample=12, final=40),
    "mac": dict(netlist="bench/netlists/mac.v", vcd="bench/sim/mac.vcd", latency=0, margin=0.15, grid=12,
                sample=40, final=120),
    # registered 8x8 array multiplier (bench/gen_arraymul.py 8 --regs): small enough for a SPICE confirmation
    "mul8_r": dict(netlist="bench/netlists/mul8_v0.v", random_vectors=60, period_ps=7000, latency=0,
                   margin=0.15, grid=10, sample=12, final=40),
    # AI-accelerator PE (bench/rtl/dot4_i8.v): 4-lane int8 dot product, two multiplier architectures
    "dot4_plain": dict(netlist="bench/netlists/dot4_plain.v", random_vectors=60, period_ps=7500, latency=0,
                       margin=0.15, grid=10, sample=12, final=40),
    "dot4_booth": dict(netlist="bench/netlists/dot4_booth.v", random_vectors=60, period_ps=7500, latency=0,
                       margin=0.15, grid=10, sample=12, final=40),
    "mul4_p": dict(netlist="bench/netlists/mul4.v", random_vectors=300, period_ps=2000, latency=1, margin=0.15,
                   grid=12, sample=60, final=200),
}


AREA_TIE = 0.05      # final choice: fewest flip-flops within 5 % of the lowest measured energy (GlitchFix.select)


def run(lib, name, cfg):
    out = ROOT / "data/glitchfix" / name
    t0 = time.time()
    fx = GlitchFix(ROOT / cfg["netlist"], lib, vcd=ROOT / cfg["vcd"] if cfg.get("vcd") else None,
                   random_vectors=cfg.get("random_vectors"), period_ps=cfg.get("period_ps"),
                   latency=cfg["latency"], sample=cfg["sample"], grid=cfg["grid"], workdir=out / "work")
    T = fx.period_ps * (1 - cfg["margin"])
    print(f"== {name}: {len(fx.design.network.cells)} cells, {len(fx.design.flops)} flops, latency +{fx.latency}, "
          f"clock {fx.period_ps:.0f} ps (pre-layout limit {T:.0f} ps), {fx.n_banks()} register bank(s)")
    base, classic, best = fx.search(T=T, method=cfg.get("method", "both"))
    refs = [base, fx.min_register, classic, best, getattr(fx, "best_cuts", None), getattr(fx, "best_milp", None)]
    base, minreg, classic, best, bcut, bmilp = fx.remeasure(refs, cfg["final"])
    # final choice among every measured placement, the references included (as in retiming_benchmarks.py)
    best = fx.select([best, bcut, bmilp, minreg, classic], tie=cfg.get("area_tie", AREA_TIE)) or best
    s = write_result(fx, base, classic, best, out, min_register=minreg)
    if minreg is not None and minreg.text:
        (out / "min_register.v").write_text(minreg.text)
    s["seconds"] = round(time.time() - t0, 1)
    for k, c in (("best_cuts", bcut), ("best_milp", bmilp)):          # each search method on its own
        s[k] = c.row() if c is not None and c.energy else None
        if c is not None and c.text:
            (out / f"{k}.v").write_text(c.text)
    s["case"], s["config"] = name, {k: v for k, v in cfg.items()}
    (out / "optimize.json").write_text(json.dumps(s, indent=1))
    for k in ("original", "min_register", "timing_driven", "glitch_aware"):
        r = s.get(k)
        if r:
            print(f"   {k:14s} total {r.get('total', 0):9.1f} fJ/cycle  glitch {r.get('glitch', 0):8.1f}  "
                  f"flops {r['flops']:4d}  period {r['period_ps']:7.0f} ps  {r.get('power_uW', 0):8.1f} uW")
    import shutil
    shutil.rmtree(out / "work", ignore_errors=True)
    return s


def main():
    lib = sys.argv[1]
    names = sys.argv[2:] or list(CASES)
    for n in names:
        run(lib, n, CASES[n])


if __name__ == "__main__":
    main()

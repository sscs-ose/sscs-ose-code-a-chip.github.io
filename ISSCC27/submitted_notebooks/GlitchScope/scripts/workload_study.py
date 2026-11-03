"""Does the automatic fix depend on random operands?  The 16x16 multiplier's original, timing-driven and GlitchScope
placements (section 6) measured on operand streams with different statistics:

  uniform      every input bit random each cycle (the stimulus used everywhere else)
  dnn_int8     8-bit operands as in a quantised neural-network layer: activations after ReLU (half zero, the rest
               half-normal, sigma 40) times weight magnitudes (half-normal, sigma 30), upper 8 bits zero
  dsp_16bit    16-bit signal samples, slowly varying (AR(1), rho 0.95, sigma 6000) times a fixed-point
               coefficient stream (half-normal, sigma 8000)

    python scripts/workload_study.py <liberty> [cycles]      -> data/glitchfix/mul16_r/workloads.json
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import glitchscope.optimize as opt  # noqa: E402

DESIGNS = {"original": ROOT / "bench/layout/mul16_v0.v",
           "timing_driven": ROOT / "data/glitchfix/mul16_r/timing_driven.v",
           "glitchscope": ROOT / "data/glitchfix/mul16_r/optimized.v"}
PERIOD = 15000


def operands(kind, n, seed=1):
    r = random.Random(seed)
    hn = lambda s, hi: min(hi, int(abs(r.gauss(0, s))))                       # noqa: E731
    if kind == "uniform":
        return [(r.getrandbits(16), r.getrandbits(16)) for _ in range(n)]
    if kind == "dnn_int8":
        return [(0 if r.random() < 0.5 else hn(40, 255), hn(30, 255)) for _ in range(n)]
    if kind == "dsp_16bit":
        x, out = 0.0, []
        for _ in range(n):
            x = 0.95 * x + (1 - 0.95 ** 2) ** 0.5 * r.gauss(0, 6000)
            out.append((min(65535, int(abs(x))), hn(8000, 65535)))
        return out
    raise ValueError(kind)


def make_waves(kind):
    def waves(design, n_cycles, period_ps, seed=1, clock=None):
        clock = clock or (design.clocks[0] if design.clocks else "clk")
        P = int(round(period_ps * 1000))
        w = {clock: [(0, 0)]}
        for k in range(1, n_cycles + 2):
            w[clock] += [(k * P, 1), (k * P + P // 2, 0)]
        ops = operands(kind, n_cycles + 1, seed)
        for pi in design.real_inputs:
            port, bit = pi[0], int(pi[1:])
            val = lambda k: (ops[k][0] if port == "a" else ops[k][1]) >> bit & 1     # noqa: E731
            w[pi] = [(0, val(0))] + [(k * P + 1000, val(k)) for k in range(1, n_cycles + 1)]
        return w, clock
    return waves


def main():
    lib = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    res = {}
    for kind in ("uniform", "dnn_int8", "dsp_16bit"):
        opt.random_waves = make_waves(kind)
        row = {}
        for tag, path in DESIGNS.items():
            fx = opt.GlitchFix(path, lib, random_vectors=n, period_ps=PERIOD, sample=n, grid=2, log=lambda m: None)
            e = fx.original().energy
            row[tag] = dict(total=e["total"], glitch=e["glitch"], functional=e["functional"],
                            flops=len(fx.design.flops))
        o = row["original"]["total"]
        for tag in ("timing_driven", "glitchscope"):
            row[tag]["saving"] = 1 - row[tag]["total"] / o
        row["glitch_share_original"] = row["original"]["glitch"] / o
        res[kind] = row
        print(f"{kind:10s} original {o / 1e3:6.2f} pJ (glitch {100 * row['glitch_share_original']:4.1f} % of total)  "
              f"timing-driven {100 * row['timing_driven']['saving']:5.1f} %  GlitchScope {100 * row['glitchscope']['saving']:5.1f} %",
              flush=True)
    (ROOT / "data/glitchfix/mul16_r/workloads.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()

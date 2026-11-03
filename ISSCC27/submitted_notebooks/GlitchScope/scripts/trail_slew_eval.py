"""Effect of the trailing-edge slew correction (M2, ``trail_slew_alpha``) on glitch-transition
counts against the cached whole-circuit ngspice references of section 5.

    python scripts/trail_slew_eval.py <liberty> [alpha|model ...] [--pex]   -> data/m2/trail_slew_eval[_pex].json
("model": the per-cell, per-polarity alpha measured by scripts/trail_slew_sweep.py; --pex compares with
the SPICE references simulated on parasitic-extracted cells)
"""
import json
import random
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.functional import evaluate_stable  # noqa: E402
from glitchscope.liberty import LibertyDelayProvider, parse_liberty_file  # noqa: E402
from glitchscope.m2model import M2Model  # noqa: E402
from glitchscope.model import StimulusEpoch, ps_to_fs  # noqa: E402
from glitchscope.sim import PulseSimulator  # noqa: E402
from glitchscope.verilog import read_verilog  # noqa: E402

CASES = [("rca8", "bench/netlists/rca8.v", 60, "data/bench/spice_ref_rca8_60{s}.json"),
         ("ks8", "bench/netlists/ks8.v", 40, "data/bench/spice_ref_ks8_40{s}.json"),
         ("mul4", "bench/netlists/mul4.v", 40, "data/bench/spice_ref_mul4_40{s}.json"),
         ("c432", "bench/external/netlists/c432.v", 30, "data/bench/spice_ref_c432_30_6000ps{s}.json"),
         ("c880", "bench/external/netlists/c880.v", 30, "data/bench/spice_ref_c880_30_6000ps{s}.json"),
         ("arraymul8", "bench/netlists/arraymul8.v", 20, "data/bench/spice_ref_arraymul8_20_7000ps{s}.json")]


def glitch_ratio(lib, net, vecs, ref, alpha, dp, m2):
    sim = PulseSimulator(net, dp, "M2", r_filter=m2, default_input_slew_fs=ps_to_fs(40), engine="python",
                         trail_slew_alpha=alpha)
    prev, g_m2, g_sp = dict(net.initial_inputs), 0, 0
    for k, vec in enumerate(vecs):
        cur = {**prev, **vec}
        b, a = evaluate_stable(net, prev), evaluate_stable(net, cur)
        sim.network = replace(net, initial_inputs=dict(prev))
        tr = sim.run([StimulusEpoch(100_000, dict(vec), k + 1)])["trace"]
        cnt = Counter(e.net for e in tr if e.source_instance != "$PI")
        for n, x in ref[k]["crossings"].items():
            req = int(b[n] != a[n])
            g_m2 += cnt.get(n, 0) - req
            g_sp += x - req
        prev = cur
    return g_m2 / max(1, g_sp), g_m2, g_sp


def main():
    lib = sys.argv[1]
    alphas = [None if x == "model" else float(x) for x in sys.argv[2:] if x != "--pex"] or [0.0, None]
    suffix = "_pex" if len(sys.argv) > 1 and "--pex" in sys.argv else ""
    dp, m2 = LibertyDelayProvider(parse_liberty_file(lib)), M2Model()
    out = {}
    for name, path, nv, refp in CASES:
        rp = ROOT / refp.format(s=suffix)
        if not (ROOT / path).exists() or not rp.exists():
            continue
        net = read_verilog(ROOT / path)
        ref = json.loads(rp.read_text())
        rnd = random.Random(11)
        vecs = [{pi: rnd.randint(0, 1) for pi in net.primary_inputs} for _ in range(nv)]
        out[name] = {}
        for a in alphas:
            r, gm, gs = glitch_ratio(lib, net, vecs, ref, a, dp, m2)
            out[name]["model" if a is None else str(a)] = dict(ratio=r, m2=gm, spice=gs)
        print(f"{name:10s} " + "  ".join(f"alpha {'model' if a is None else a}: "
                                        f"{out[name]['model' if a is None else str(a)]['ratio']:.2f}x" for a in alphas), flush=True)
    (ROOT / f"data/m2/trail_slew_eval{suffix}.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

"""Glitch-energy analysis of the synthesized benchmarks under M0/M1/M2."""
import sys, time, random, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from glitchscope.verilog import read_verilog
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import ps_to_fs
from glitchscope.sim import PulseSimulator
from glitchscope.m2model import M2Model
from glitchscope.analyze import EnergyModel, analyze
LIB = sys.argv[1]; NV = int(sys.argv[2]) if len(sys.argv) > 2 else 300
benches = sys.argv[3].split(",") if len(sys.argv) > 3 else ["c17", "rca8", "ks8", "cmp8", "mul4"]
lib = parse_liberty_file(LIB); dp = LibertyDelayProvider(lib); m2 = M2Model()
out = {}
for t in benches:
    net = read_verilog(ROOT / f"bench/netlists/{t}.v"); em = EnergyModel(LIB, net)
    rnd = random.Random(7)
    vecs = [{pi: rnd.randint(0, 1) for pi in net.primary_inputs} for _ in range(NV)]
    for m in ["M0", "M1", "M2"]:
        t0 = time.time()
        sim = PulseSimulator(net, dp, m, r_filter=m2, default_input_slew_fs=ps_to_fs(40))
        r = analyze(sim, em, vecs)
        T, C = r["totals"], r["counts"]
        cons = abs(sum(r["causal"].values()) - T["E_glitch_fJ"]) < 1e-6 * max(1, T["E_glitch_fJ"])
        top = list(r["gci"].items())[:3]
        print(f"{t:5s} {m}  Efun/vec={T['E_functional_fJ']/NV:6.1f}fJ  Eglitch/vec={T['E_glitch_fJ']/NV:6.1f}fJ "
              f"frac={T['glitch_fraction']:.3f}  gen={C.get('GENERATED',0)} prop={C.get('PROPAGATED',0)} "
              f"merged={C.get('MERGED',0)} filt={C.get('FILTERED',0)} reruns={C.get('reruns',0)} "
              f"causal_conserved={cons} {time.time()-t0:.1f}s")
        print("      top GCI:", ", ".join(f"{k}={v:.2f}" for k, v in top))
        out[f"{t}/{m}"] = r
(ROOT / "data/bench").mkdir(parents=True, exist_ok=True)
(ROOT / "data/bench/energy_summary.json").write_text(json.dumps(
    {k: {"totals": v["totals"], "counts": v["counts"], "gci": v["gci"], "local": v["local"]} for k, v in out.items()}, indent=1))

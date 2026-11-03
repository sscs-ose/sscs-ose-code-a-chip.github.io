"""Interventional vs structural glitch attribution on a combinational benchmark (library version)."""
import sys, random, json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import numpy as np
from glitchscope.verilog import read_verilog
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import ps_to_fs
from glitchscope.m2model import M2Model
from glitchscope.analyze import EnergyModel
from glitchscope.attribution import InterventionalAttribution
LIB, BENCH = sys.argv[1], sys.argv[2]; NV = int(sys.argv[3]) if len(sys.argv) > 3 else 300
net = read_verilog(ROOT / f"bench/netlists/{BENCH}.v")
rnd = random.Random(7); vecs = [{p: rnd.randint(0, 1) for p in net.primary_inputs} for _ in range(NV)]
t0 = time.time()
ia = InterventionalAttribution(net, LibertyDelayProvider(parse_liberty_file(LIB)), M2Model(),
                               EnergyModel(LIB, net, spice_scale=True), vecs,
                               sim_kwargs=dict(default_input_slew_fs=ps_to_fs(40)))
# full single-gain map (all active cells) for the structural comparison
single = {c: ia.gain({c}) for c in ia.active}
r = ia.run(top_k=6, perms=24, candidates=10)
gci = r["structural"]
common = [c for c in single if c in gci]
rs = np.argsort(np.argsort([-single[c] for c in common])); rg = np.argsort(np.argsort([-gci[c] for c in common]))
sp = float(np.corrcoef(rs, rg)[0, 1])
top_s = sorted(single, key=lambda c: -single[c])[:5]; top_g = sorted(gci, key=lambda c: -gci[c])[:5]
blockers = [c for c in top_s if gci.get(c, 0) < 0.01]
print(f"{BENCH}: {len(ia.active)} active cells, {time.time() - t0:.0f}s, Spearman(structural, interventional) = {sp:.2f}")
print("  top-5 interventional: " + ", ".join(f"{c} {100 * single[c]:.1f}% (struct {100 * gci.get(c, 0):.1f}%)" for c in top_s))
print("  top-5 structural    : " + ", ".join(f"{c} {100 * gci[c]:.1f}% (interv {100 * single.get(c, 0):.1f}%)" for c in top_g))
print(f"  blockers (high potential, ~0 structural credit): {blockers}")
print(f"  joint top-6 {100 * r['joint_top']:.1f}% vs sum of singles {100 * r['sum_single_top']:.1f}%; "
      f"greedy: " + " -> ".join(f"{c} {100 * g:.1f}%" for c, g in r["greedy"]))
(ROOT / f"data/bench/counterfactual_{BENCH}.json").write_text(json.dumps(dict(
    single=single, structural=gci, spearman=sp, blockers=blockers, **{k: r[k] for k in ("top", "shapley", "joint_top", "sum_single_top", "greedy")}), indent=1))

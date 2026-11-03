"""How much glitch energy is consumed at a different cell than the one that caused it?"""
import sys, random, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from glitchscope.verilog import read_verilog
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import ps_to_fs
from glitchscope.sim import PulseSimulator
from glitchscope.m2model import M2Model
from glitchscope.analyze import EnergyModel, analyze
LIB = sys.argv[1]; NV = int(sys.argv[2])
dp = LibertyDelayProvider(parse_liberty_file(LIB)); m2 = M2Model(); out = {}
for b in ["rca8", "ks8", "cmp8", "mul4"]:
    net = read_verilog(ROOT / f"bench/netlists/{b}.v")
    rnd = random.Random(7); vecs = [{pi: rnd.randint(0, 1) for pi in net.primary_inputs} for _ in range(NV)]
    a = analyze(PulseSimulator(net, dp, "M2", r_filter=m2, default_input_slew_fs=ps_to_fs(40)),
                EnergyModel(LIB, net, spice_scale=True), vecs)
    L, C = a["local"], a["causal"]; tot = sum(L.values())
    displaced = 1 - sum(min(L.get(c, 0), C.get(c, 0)) for c in set(L) | set(C)) / tot
    topL = sorted(L, key=L.get, reverse=True)[:5]; topC = sorted(C, key=C.get, reverse=True)[:5]
    out[b] = dict(displaced_fraction=displaced, top5_local=topL, top5_causal=topC,
                  top5_overlap=len(set(topL) & set(topC)), top1_same=topL[0] == topC[0])
    print(f"{b:5s} energy displaced from consumer to cause = {displaced:.0%}   top-5 overlap {len(set(topL) & set(topC))}/5   top-1 same: {topL[0] == topC[0]}")
(ROOT / "data/bench/attribution_shift.json").write_text(json.dumps(out, indent=1))

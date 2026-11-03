"""Multi-toggle-per-cycle glitch detection (Antmicro trace2power style) vs GlitchScope causal analysis.

Baselines, per vector (= one clock cycle):
  ZD-MT  : zero-delay simulation (Verilator-like) + 'net toggles >1 per cycle'
  T-MT   : delay-annotated simulation (M1 = SDF-style inertial) + 'net toggles >1 per cycle';
           every transition of such a net is counted as glitch activity
GlitchScope: same timed trace, but only the EXCESS transitions beyond the functionally
           required one are glitch activity (energy with SPICE-calibrated M2 accounting).
"""
import sys, random, json
from dataclasses import replace
from collections import Counter, defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from glitchscope.verilog import read_verilog
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import ps_to_fs, StimulusEpoch
from glitchscope.sim import PulseSimulator
from glitchscope.m2model import M2Model
from glitchscope.functional import evaluate_stable
from glitchscope.analyze import EnergyModel, analyze
LIB = sys.argv[1]; NV = int(sys.argv[2])
dp = LibertyDelayProvider(parse_liberty_file(LIB)); m2 = M2Model(); out = {}
print(f"{'bench':6s} {'ZD-MT':>6s} {'T-MT':>8s} {'GS':>7s} {'mislabeled':>10s} | glitch energy fJ/vec: {'T-MT':>6s} {'GS-M2':>6s}")
for b in ["c17", "rca8", "ks8", "cmp8", "mul4"]:
    net = read_verilog(ROOT / f"bench/netlists/{b}.v"); em = EnergyModel(LIB, net, spice_scale=True)
    cells = {c.name: c for c in net.cells}
    rnd = random.Random(7); vecs = [{pi: rnd.randint(0, 1) for pi in net.primary_inputs} for _ in range(NV)]
    sim = PulseSimulator(net, dp, "M1", r_filter=m2, default_input_slew_fs=ps_to_fs(40))
    prev = dict(net.initial_inputs); mt_tr = gs_tr = mislab = 0; mt_e = 0.0
    for k, vec in enumerate(vecs, 1):
        cur = {**prev, **vec}; bf, af = evaluate_stable(net, prev), evaluate_stable(net, cur)
        sim.network = replace(net, initial_inputs=dict(prev))
        r = sim.run([StimulusEpoch(100_000, dict(vec), k)])
        evs = [e for e in r["trace"] if e.source_instance != "$PI"]
        cnt = Counter(e.net for e in evs)
        for n, x in cnt.items():
            need = int(bf[n] != af[n])
            gs_tr += x - need
            if x > 1:
                mt_tr += x; mislab += need
        for e in evs:
            if cnt[e.net] > 1:
                m = r["meta"][e.event_id]
                mt_e += em.transition_fj(cells[e.source_instance], e.new_value == 1, m.related_pin,
                                         m.slew_in_fs, r["loads"].get(e.net, 0.0))
        prev = cur
    gs = analyze(PulseSimulator(net, dp, "M2", r_filter=m2, default_input_slew_fs=ps_to_fs(40)), em, vecs)
    out[b] = dict(zd_mt=0, t_mt=mt_tr, gs_m1_excess=gs_tr, functional_mislabeled=mislab,
                  t_mt_energy_per_vec=mt_e / NV, gs_m2_glitch_energy_per_vec=gs["totals"]["E_glitch_fJ"] / NV,
                  gs_m2_functional_energy_per_vec=gs["totals"]["E_functional_fJ"] / NV)
    o = out[b]
    print(f"{b:6s} {0:6d} {mt_tr:8d} {gs_tr:7d} {mislab:10d} | {o['t_mt_energy_per_vec']:27.1f} {o['gs_m2_glitch_energy_per_vec']:6.1f}")
(ROOT / "data/bench/naive_vs_causal.json").write_text(json.dumps(out, indent=1))

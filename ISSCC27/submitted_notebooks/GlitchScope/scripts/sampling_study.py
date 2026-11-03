"""Cycle-sampling accuracy on the MAC testbench: estimate, 95 % CI width and coverage vs
sample size (20 seeds each) -> data/notebook/sampling_mac.json"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.verilog import read_design
from glitchscope.seq import read_vcd, read_clk_to_q, build_cycles
from glitchscope.sim import PulseSimulator
from glitchscope.m2model import M2Model
from glitchscope.analyze import EnergyModel, analyze
from glitchscope.model import ps_to_fs
from glitchscope.sampling import stratified_sample, estimate
L = sys.argv[1]
lib = parse_liberty_file(L); d = read_design(ROOT / "bench/netlists/mac.v", lib); net = d.network
cap = {f.d: lib.cells[f.libcell].pin_capacitance.get(f.d_pin, 0) for f in d.flops}
sim = PulseSimulator(net, LibertyDelayProvider(lib), "M2", r_filter=M2Model(), default_input_slew_fs=ps_to_fs(40),
                     primary_output_load_ff_by_net=cap)
waves, _ = read_vcd(ROOT / "bench/sim/mac.vcd")
init, cycles, _ = build_cycles(d, waves, lib, read_clk_to_q(L, {f.libcell for f in d.flops}), sim.loads)
em = EnergyModel(L, net, spice_scale=True)
t = time.time(); full = analyze(sim, em, cycles, initial=init); t_full = time.time() - t
per_all = {k: (v["E_glitch"], v["E_fun"]) for k, v in enumerate(full["per_vector"])}
N = len(cycles); truth = full["totals"]["E_glitch_fJ"] / N; truth_share = full["totals"]["glitch_fraction"]
out = dict(cycles=N, truth_glitch_fJ=truth, truth_share=truth_share, full_seconds=t_full, sizes={})
for n in (10, 20, 40, 80, 160):
    rows = []
    for seed in range(1, 21):
        idx, prevs, members, smp = stratified_sample(cycles, init, n, seed=seed)
        e = estimate({k: per_all[k] for k in idx}, members, smp, N)   # same per-cycle values as a sampled run
        g, r = e["E_glitch_fJ_per_cycle"], e["glitch_fraction"]
        rows.append(dict(seed=seed, n=len(idx), mean=g[0], lo=g[1], hi=g[2], share=r[0], share_lo=r[1], share_hi=r[2]))
    out["sizes"][n] = rows
    cov = sum(r["lo"] <= truth <= r["hi"] for r in rows)
    print(f"n={n:4d}: coverage {cov}/20, mean CI half-width {sum((r['hi'] - r['lo']) / 2 for r in rows) / 20 / truth * 100:.1f} % of truth")
(ROOT / "data/notebook/sampling_mac.json").write_text(json.dumps(out, indent=1))

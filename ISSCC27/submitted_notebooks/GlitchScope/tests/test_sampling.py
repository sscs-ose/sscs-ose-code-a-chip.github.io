"""Cycle sampling: independent steps reproduce the chained run; CI contains the truth."""
import random
from pathlib import Path

from glitchscope.test_support import lib_path_or_none

ROOT = Path(__file__).resolve().parents[1]


def test_prevs_reproduce_chained_run_and_ci_covers():
    lib_path = lib_path_or_none()
    if not lib_path:
        return
    from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
    from glitchscope.verilog import read_verilog
    from glitchscope.sim import PulseSimulator
    from glitchscope.m2model import M2Model
    from glitchscope.analyze import EnergyModel, analyze
    from glitchscope.model import ps_to_fs
    from glitchscope.sampling import stratified_sample, analyze_sampled
    lib = parse_liberty_file(lib_path)
    net = read_verilog(ROOT / "bench/netlists/mul4.v")
    sim = PulseSimulator(net, LibertyDelayProvider(lib), "M2", r_filter=M2Model(), default_input_slew_fs=ps_to_fs(40))
    em = EnergyModel(lib_path, net, spice_scale=True)
    rnd = random.Random(2)
    vecs = [{p: rnd.randint(0, 1) for p in net.primary_inputs} for _ in range(120)]
    init = {p: 0 for p in net.primary_inputs}
    full = analyze(sim, em, vecs, initial=init)
    idx, prevs, members, smp = stratified_sample(vecs, init, 30, seed=4)
    part = analyze(sim, em, [vecs[k] for k in idx], initial=init, prevs=[prevs[k] for k in idx])
    for k, v in zip(idx, part["per_vector"]):
        assert abs(v["E_glitch"] - full["per_vector"][k]["E_glitch"]) < 1e-9
        assert abs(v["E_fun"] - full["per_vector"][k]["E_fun"]) < 1e-9
    truth = full["totals"]["E_glitch_fJ"] / len(vecs)
    hits = 0
    for seed in range(1, 6):
        m, lo, hi = analyze_sampled(sim, em, vecs, init, n=40, seed=seed)["estimate"]["E_glitch_fJ_per_cycle"]
        hits += lo <= truth <= hi
    assert hits >= 4

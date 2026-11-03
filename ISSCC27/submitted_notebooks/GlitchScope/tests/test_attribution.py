"""Interventional attribution: oracle (ideal) cells and Shapley efficiency."""
from glitchscope import fixtures as F
from glitchscope.delay import ConstantDelayProvider
from glitchscope.sim import PulseSimulator
from glitchscope.test_support import lib_path_or_none


def test_ideal_cell_removes_its_glitch_and_keeps_final_state():
    net, ep = F.xor_reconvergent_fixture()
    b = PulseSimulator(net, ConstantDelayProvider(), "M0").run(ep)
    base = b["trace"]
    xor = [c for c in net.cells if c.kind == "XOR2"][0]
    n_base = sum(1 for e in base if e.source_instance == xor.name)
    assert n_base >= 2                       # the fixture's reconvergent XOR glitches
    res = PulseSimulator(net, ConstantDelayProvider(), "M0", ideal_cells={xor.name}).run(ep)
    n_ideal = sum(1 for e in res["trace"] if e.source_instance == xor.name)
    assert n_ideal <= 1 and n_ideal == (n_base % 2)
    assert res["final"] == b["final"]


def test_shapley_sums_to_joint_gain_rca8():
    lp = lib_path_or_none()
    if not lp:
        return
    import random
    from pathlib import Path
    from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
    from glitchscope.verilog import read_verilog
    from glitchscope.m2model import M2Model
    from glitchscope.analyze import EnergyModel
    from glitchscope.attribution import InterventionalAttribution
    from glitchscope.model import ps_to_fs
    root = Path(__file__).resolve().parents[1]
    net = read_verilog(root / "bench/netlists/rca8.v")
    rnd = random.Random(7); vecs = [{p: rnd.randint(0, 1) for p in net.primary_inputs} for _ in range(60)]
    ia = InterventionalAttribution(net, LibertyDelayProvider(parse_liberty_file(lp)), M2Model(),
                                   EnergyModel(lp, net, spice_scale=True), vecs,
                                   sim_kwargs=dict(default_input_slew_fs=ps_to_fs(40)))
    r = ia.run(top_k=4, perms=6, candidates=6)
    assert abs(sum(r["shapley"].values()) - r["joint_top"]) < 1e-9
    assert all(0.0 <= g <= 1.0 + 1e-9 for g in r["single"].values())

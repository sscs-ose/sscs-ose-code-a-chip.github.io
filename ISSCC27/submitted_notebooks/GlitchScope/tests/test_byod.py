"""Bring-your-own-design features. Tests needing the real SKY130 Liberty are
skipped (return early) when it is not configured in tools.env / GS_LIB."""
import itertools, os, random
from dataclasses import replace
from pathlib import Path
from glitchscope.logic import eval_primitive

ROOT = Path(__file__).resolve().parents[1]


def _lib_path():
    from glitchscope.test_support import lib_path_or_none
    return lib_path_or_none()


_LIB = {}


def _lib():
    if "lib" not in _LIB:
        from glitchscope.liberty import parse_liberty_file
        _LIB["lib"] = parse_liberty_file(_lib_path())
    return _LIB["lib"]


def test_liberty_function_eval_matches_handcoded():
    assert eval_primitive("LIB:(A1&A2) | (B1)", {"A1": 1, "A2": 1, "B1": 0}) == 1
    assert eval_primitive("LIB:!((A1&A2) | (B1))", {"A1": 1, "A2": 1, "B1": 0}) == eval_primitive(
        "A21OI", {"A1": 1, "A2": 1, "B1": 0})
    for a, b in itertools.product([0, 1], repeat=2):
        assert eval_primitive("LIB:(A&!B) | (!A&B)", {"A": a, "B": b}) == a ^ b


def test_mac_flow_matches_rtl_testbench():
    if not _lib_path():
        return
    from glitchscope.flow import run_design
    res = run_design(ROOT / "bench/netlists/mac.v", ROOT / "bench/sim/mac.vcd", _lib_path(), "M1", lib=_lib())
    chk = res["design"]["output_check"]
    assert chk["checked"] > 1000 and chk["mismatches"] == 0
    assert 0.0 < res["totals"]["glitch_fraction"] < 1.0


def test_m2_rollback_regression_mul4_vector78():
    """Stale rejection after an upstream rollback (fixed ordering bug)."""
    if not _lib_path():
        return
    from glitchscope.verilog import read_verilog
    from glitchscope.liberty import LibertyDelayProvider
    from glitchscope.model import ps_to_fs, StimulusEpoch
    from glitchscope.sim import PulseSimulator
    from glitchscope.m2model import M2Model
    m2 = M2Model(); net = read_verilog(ROOT / "bench/netlists/mul4.v")
    rnd = random.Random(7)
    vecs = [{pi: rnd.randint(0, 1) for pi in net.primary_inputs} for _ in range(78)]
    prev = dict(net.initial_inputs)
    for v in vecs[:77]:
        prev = {**prev, **v}
    rf = lambda c, pol, s, d: 50.0 if c.name == "_24_" else m2(c, pol, s, d)
    sim = PulseSimulator(replace(net, initial_inputs=prev), LibertyDelayProvider(_lib()), "M2", r_filter=rf,
                         default_input_slew_fs=ps_to_fs(40))
    res = sim.run([StimulusEpoch(100_000, dict(vecs[77]), 78)])
    assert res["reruns"] >= 1

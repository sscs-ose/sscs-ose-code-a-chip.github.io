"""Compiled core: event-for-event identical to the Python engine; fast lineage == reference."""
import random
from dataclasses import replace
from pathlib import Path

from glitchscope.test_support import lib_path_or_none

ROOT = Path(__file__).resolve().parents[1]


def _sig(res):
    tr = [(e.event_id, e.time_fs, e.epoch_id, e.net, e.old_value, e.new_value, e.source_instance,
           e.parent_event_ids) for e in res["trace"]]
    ids = {e.event_id for e in res["trace"]}
    return (tr, [tuple(s.__dict__.values()) for s in res["suppressed"]],
            {k: tuple(v.__dict__.values()) for k, v in res["meta"].items() if k in ids},
            res.get("reruns", 0), dict(res["final"]))


def test_native_core_matches_python():
    from glitchscope import fastsim
    lib_path = lib_path_or_none()
    if not lib_path or not fastsim.available():
        return
    from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
    from glitchscope.verilog import read_verilog
    from glitchscope.sim import PulseSimulator
    from glitchscope.m2model import M2Model
    from glitchscope.model import StimulusEpoch, ps_to_fs
    dp = LibertyDelayProvider(parse_liberty_file(lib_path))
    for bench in ("rca8", "mul4"):
        net = read_verilog(ROOT / f"bench/netlists/{bench}.v")
        for model, rollback, frac in (("M0", True, 0), ("M1", True, 0), ("M2", True, 0), ("M2", False, 0),
                                      ("M2", True, 0.25)):
            rnd = random.Random(3)
            ideal = frozenset(rnd.sample([c.name for c in net.cells], int(frac * len(net.cells))))
            kw = dict(default_input_slew_fs=ps_to_fs(40), rollback=rollback, ideal_cells=ideal,
                      r_filter=M2Model() if model == "M2" else None)
            py = PulseSimulator(net, dp, model, engine="python", **kw)
            nat = PulseSimulator(net, dp, model, engine="native", **kw)
            prev = {p: 0 for p in net.primary_inputs}
            for k in range(12):
                cur = {p: rnd.randint(0, 1) for p in net.primary_inputs}
                eps = [StimulusEpoch(100_000, cur, k + 1)]
                for s in (py, nat):
                    s.network = replace(net, initial_inputs=dict(prev))
                a, b = py.run(eps), nat.run(eps)
                assert b["engine"] == "native"
                assert _sig(a) == _sig(b), (bench, model, rollback, frac, k)
                prev = cur
            if model == "M2":
                assert py.r_filter.uncalibrated == nat.r_filter.uncalibrated


def test_fast_lineage_matches_reference():
    lib_path = lib_path_or_none()
    if not lib_path:
        return
    from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
    from glitchscope.verilog import read_verilog
    from glitchscope.sim import PulseSimulator
    from glitchscope.m2model import M2Model
    from glitchscope.model import StimulusEpoch, ps_to_fs
    from glitchscope.functional import evaluate_stable
    from glitchscope.classify import extract_pulses
    from glitchscope.lineage import classify_glitch_lineages, classify_glitch_lineages_reference
    dp = LibertyDelayProvider(parse_liberty_file(lib_path))
    net = read_verilog(ROOT / "bench/netlists/mul4.v")
    sim = PulseSimulator(net, dp, "M2", r_filter=M2Model(), default_input_slew_fs=ps_to_fs(40))
    rnd = random.Random(9)
    prev = {p: 0 for p in net.primary_inputs}
    n = 0
    for k in range(30):
        cur = {p: rnd.randint(0, 1) for p in net.primary_inputs}
        sim.network = replace(net, initial_inputs=dict(prev))
        tr = sim.run([StimulusEpoch(100_000, cur, 1)])["trace"]
        pulses = extract_pulses(tr, {1: evaluate_stable(net, prev)}, {1: evaluate_stable(net, cur)})
        n += len(pulses)
        assert classify_glitch_lineages(tr, pulses) == classify_glitch_lineages_reference(tr, pulses)
        prev = cur
    assert n > 50


def test_delay_scale_native_matches_python_and_changes_glitches():
    """Per-instance delay factors (local variation): both engines identical; factors of 1 change nothing."""
    from glitchscope import fastsim
    lib_path = lib_path_or_none()
    if not lib_path or not fastsim.available():
        return
    from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
    from glitchscope.verilog import read_verilog
    from glitchscope.sim import PulseSimulator
    from glitchscope.m2model import M2Model
    from glitchscope.model import StimulusEpoch, ps_to_fs
    dp = LibertyDelayProvider(parse_liberty_file(lib_path))
    net = read_verilog(ROOT / "bench/netlists/mul4.v")
    rnd = random.Random(9)
    scale = {c.name: rnd.gauss(1.0, 0.08) for c in net.cells}
    kw = dict(default_input_slew_fs=ps_to_fs(40), r_filter=M2Model())
    py = PulseSimulator(net, dp, "M2", engine="python", delay_scale=scale, **kw)
    nat = PulseSimulator(net, dp, "M2", engine="native", delay_scale=scale, **kw)
    one = PulseSimulator(net, dp, "M2", engine="native", delay_scale={c.name: 1.0 for c in net.cells}, **kw)
    ref = PulseSimulator(net, dp, "M2", engine="native", **kw)
    prev, differs = {p: 0 for p in net.primary_inputs}, 0
    for k in range(20):
        cur = {p: rnd.randint(0, 1) for p in net.primary_inputs}
        eps = [StimulusEpoch(100_000, cur, k + 1)]
        for s in (py, nat, one, ref):
            s.network = replace(net, initial_inputs=dict(prev))
        a, b, c, d = py.run(eps), nat.run(eps), one.run(eps), ref.run(eps)
        assert _sig(a) == _sig(b), k
        assert _sig(c) == _sig(d), k
        differs += _sig(b) != _sig(d)
        prev = cur
    assert differs > 0


def test_trailing_slew_native_matches_python():
    """M2 trailing-edge slew correction (calibrated per cell, and a global override): both engines identical;
    alpha = 0 reproduces the model without the correction and the calibrated alpha removes glitches."""
    from glitchscope import fastsim
    lib_path = lib_path_or_none()
    if not lib_path or not fastsim.available():
        return
    from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
    from glitchscope.verilog import read_verilog
    from glitchscope.sim import PulseSimulator
    from glitchscope.m2model import M2Model
    from glitchscope.model import StimulusEpoch, ps_to_fs
    dp = LibertyDelayProvider(parse_liberty_file(lib_path))
    net = read_verilog(ROOT / "bench/netlists/arraymul8.v")
    kw = dict(default_input_slew_fs=ps_to_fs(40), r_filter=M2Model())
    n_cal = n_zero = 0
    for alpha in (None, 0.45, 0.0):
        rnd = random.Random(5)                       # the same vectors for every alpha
        py = PulseSimulator(net, dp, "M2", engine="python", trail_slew_alpha=alpha, **kw)
        nat = PulseSimulator(net, dp, "M2", engine="native", trail_slew_alpha=alpha, **kw)
        prev = {p: 0 for p in net.primary_inputs}
        for k in range(4):
            cur = {p: rnd.randint(0, 1) for p in net.primary_inputs}
            eps = [StimulusEpoch(100_000, cur, k + 1)]
            for s in (py, nat):
                s.network = replace(net, initial_inputs=dict(prev))
            a, b = py.run(eps), nat.run(eps)
            assert _sig(a) == _sig(b), (alpha, k)
            if alpha is None:
                n_cal += len(b["trace"])
            elif alpha == 0.0:
                n_zero += len(b["trace"])
            prev = cur
    assert M2Model().trail_alpha(net.cells[0], "positive") >= 0.0
    assert n_cal < n_zero                        # the correction filters more glitches on the NOR array

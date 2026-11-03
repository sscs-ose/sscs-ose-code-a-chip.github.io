"""M2 checkpoint/rollback simulation must be event-identical to the reference
restart-from-zero simulation; generated array multiplier must be exact."""
import random
from dataclasses import replace
from pathlib import Path

from glitchscope.functional import evaluate_stable
from glitchscope.test_support import lib_path_or_none

ROOT = Path(__file__).resolve().parents[1]


def test_arraymul_generator_is_a_multiplier():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gen", ROOT / "bench" / "gen_arraymul.py")
    gen = importlib.util.module_from_spec(spec); spec.loader.exec_module(gen)
    text, ncells = gen.generate(4)
    tmp = ROOT / "tests" / "_am4.v"
    tmp.write_text(text)
    try:
        from glitchscope.verilog import read_verilog
        net = read_verilog(tmp)
    finally:
        tmp.unlink()
    for x in range(16):
        for y in range(16):
            inp = {f"a{i}": (x >> i) & 1 for i in range(4)}
            inp.update({f"b{i}": (y >> i) & 1 for i in range(4)})
            st = evaluate_stable(net, inp)
            assert sum(st[f"p{k}"] << k for k in range(8)) == x * y


def test_rollback_matches_reference():
    lib = lib_path_or_none()
    if not lib:
        return
    from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
    from glitchscope.model import ps_to_fs, StimulusEpoch
    from glitchscope.m2model import M2Model
    from glitchscope.sim import PulseSimulator
    from glitchscope.verilog import read_verilog
    dp = LibertyDelayProvider(parse_liberty_file(lib))
    for bench in ("rca8", "mul4"):
        net = read_verilog(ROOT / f"bench/netlists/{bench}.v")
        kw = dict(r_filter=M2Model(), default_input_slew_fs=ps_to_fs(40))
        fast = PulseSimulator(net, dp, "M2", rollback=True, checkpoint_every=2, **kw)
        ref = PulseSimulator(net, dp, "M2", rollback=False, **kw)
        rnd, prev, reruns = random.Random(5), {p: 0 for p in net.primary_inputs}, 0
        for _ in range(60):
            cur = {p: rnd.randint(0, 1) for p in net.primary_inputs}
            out = []
            for s in (fast, ref):
                s.network = replace(net, initial_inputs=dict(prev))
                r = s.run([StimulusEpoch(100_000, cur, 1)])
                out.append(([(e.event_id, e.time_fs, e.net, e.new_value) for e in r["trace"]],
                            [(x.instance, x.cause_fs, x.reason) for x in r["suppressed"]]))
                reruns += r["reruns"]
            assert out[0] == out[1], bench
            prev = cur
        assert reruns > 0, bench   # the rollback path was actually exercised

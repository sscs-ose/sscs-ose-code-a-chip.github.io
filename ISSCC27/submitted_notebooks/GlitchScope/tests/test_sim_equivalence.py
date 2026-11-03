"""The unified PulseSimulator must reproduce the closed B3 (M0) and B4 (M1)
engines event-for-event on every A/B fixture."""
from glitchscope import fixtures as F
from glitchscope.delay import ConstantDelayProvider
from glitchscope.timed import TransportSimulator
from glitchscope.inertial import InertialSimulator
from glitchscope.sim import PulseSimulator

FIXTURES = [F.inverter_fixture, F.xor_atomic_no_glitch_fixture, F.xor_reconvergent_fixture,
            F.propagated_glitch_fixture, F.static1_hazard_fixture,
            F.changed_final_state_glitch_fixture, F.two_epoch_glitch_fixture, F.merged_roots_fixture]


def _sig(trace):
    return [(e.time_fs, e.net, e.old_value, e.new_value, e.source_instance, e.epoch_id) for e in trace]


def test_m0_matches_b3_transport_on_fixtures():
    for f in FIXTURES:
        net, ep = f()
        ref, _ = TransportSimulator(net, ConstantDelayProvider()).run(ep)
        got = PulseSimulator(net, ConstantDelayProvider(), "M0").run(ep)["trace"]
        assert _sig(ref) == _sig(got), f.__name__


def test_m1_matches_b4_inertial_on_fixtures():
    for f in FIXTURES:
        net, ep = f()
        ref, _ = InertialSimulator(net, ConstantDelayProvider()).run(ep)
        got = PulseSimulator(net, ConstantDelayProvider(), "M1").run(ep)["trace"]
        assert _sig(ref) == _sig(got), f.__name__

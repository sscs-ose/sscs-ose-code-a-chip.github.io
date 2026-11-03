from __future__ import annotations
from glitchscope.model import Cell, Network, StimulusEpoch, ps_to_fs
from glitchscope.timed import TransportSimulator, TransportTemporalOrderError

def _inv(fall_ps, rise_ps):
    return Network(
        ["A"], ["Y"],
        [Cell("U_INV","INV",{"A":"A"},"Y",
              ps_to_fs(rise_ps),ps_to_fs(fall_ps))],
        {"A":0},
    )

def test_b7_m0_overtake_fails_closed_before_final_mismatch():
    # A rises at 100 ps -> Y fall scheduled at 200 ps.
    # A falls at 150 ps -> Y rise would be scheduled at 160 ps.
    # The second output event overtakes the still-pending first output event.
    n=_inv(fall_ps=100,rise_ps=10)
    sim=TransportSimulator(n)
    try:
        sim.run([
            StimulusEpoch(ps_to_fs(100),{"A":1},1),
            StimulusEpoch(ps_to_fs(150),{"A":0},2),
        ])
    except TransportTemporalOrderError as e:
        assert e.instance=="U_INV"
        assert e.net=="Y"
        assert e.previous_time_fs==ps_to_fs(200)
        assert e.new_time_fs==ps_to_fs(160)
        assert e.previous_target==0
        assert e.new_target==1
        assert sim.last_temporal_order_rejection["previous_time_fs"]==ps_to_fs(200)
        assert sim.last_temporal_order_rejection["new_time_fs"]==ps_to_fs(160)
        assert "Timed/final mismatch" not in str(e)
    else:
        raise AssertionError("Expected M0 temporal overtake to fail closed")

def test_b7_m0_equal_time_opposite_events_fail_closed():
    n=_inv(fall_ps=100,rise_ps=50)
    try:
        TransportSimulator(n).run([
            StimulusEpoch(ps_to_fs(100),{"A":1},1),
            StimulusEpoch(ps_to_fs(150),{"A":0},2),
        ])
    except TransportTemporalOrderError as e:
        assert e.previous_time_fs==ps_to_fs(200)
        assert e.new_time_fs==ps_to_fs(200)
    else:
        raise AssertionError("Expected equal-time opposite M0 events to fail closed")

def test_b7_m0_fifo_pending_events_preserve_transport_exactly():
    n=_inv(fall_ps=100,rise_ps=80)
    sim=TransportSimulator(n)
    tr,state=sim.run([
        StimulusEpoch(ps_to_fs(100),{"A":1},1),
        StimulusEpoch(ps_to_fs(150),{"A":0},2),
    ])
    assert [(e.time_fs,e.net,e.old_value,e.new_value) for e in tr]==[
        (ps_to_fs(100),"A",0,1),
        (ps_to_fs(150),"A",1,0),
        (ps_to_fs(200),"Y",1,0),
        (ps_to_fs(230),"Y",0,1),
    ]
    assert state["Y"]==1
    assert sim.last_temporal_order_rejection is None
    assert sim.last_temporal_order_guard_enabled is True

def test_b7_single_event_behavior_unchanged():
    n=_inv(fall_ps=100,rise_ps=80)
    sim=TransportSimulator(n)
    tr,state=sim.run([StimulusEpoch(ps_to_fs(100),{"A":1},1)])
    assert [(e.time_fs,e.net,e.old_value,e.new_value) for e in tr]==[
        (ps_to_fs(100),"A",0,1),
        (ps_to_fs(200),"Y",1,0),
    ]
    assert state["Y"]==0

def test_b7_rejection_error_is_deterministic_100_runs():
    sig=None
    for _ in range(100):
        n=_inv(fall_ps=100,rise_ps=10)
        try:
            TransportSimulator(n).run([
                StimulusEpoch(ps_to_fs(100),{"A":1},1),
                StimulusEpoch(ps_to_fs(150),{"A":0},2),
            ])
        except TransportTemporalOrderError as e:
            cur=(e.instance,e.net,e.previous_event_id,e.previous_time_fs,
                 e.new_time_fs,e.previous_target,e.new_target,str(e))
        else:
            raise AssertionError("Expected rejection")
        if sig is None: sig=cur
        assert cur==sig

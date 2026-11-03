from __future__ import annotations
from glitchscope.model import Cell, Network, StimulusEpoch, ps_to_fs
from glitchscope.timed import TransportSimulator

def _inv(delay_ps=100):
    return Network(
        ["A"], ["Y"],
        [Cell("U_INV", "INV", {"A":"A"}, "Y",
              ps_to_fs(delay_ps), ps_to_fs(delay_ps))],
        {"A":0},
    )

def test_b3_overlapping_pi_pulse_true_transport():
    n=_inv(100)
    epochs=[
        StimulusEpoch(ps_to_fs(100), {"A":1}, 1),
        StimulusEpoch(ps_to_fs(150), {"A":0}, 2),
    ]
    sim=TransportSimulator(n)
    tr,state=sim.run(epochs)
    assert [e.time_fs for e in tr] == [
        ps_to_fs(100), ps_to_fs(150), ps_to_fs(200), ps_to_fs(250)
    ]
    assert [e.net for e in tr] == ["A","A","Y","Y"]
    y=[e for e in tr if e.net=="Y"]
    assert [(e.old_value,e.new_value) for e in y] == [(1,0),(0,1)]
    assert y[0].parent_event_ids == (1,)
    assert y[1].parent_event_ids == (3,)
    assert y[0].epoch_id == 1
    assert y[1].epoch_id == 2
    assert sim.last_overlap_epoch_ids == (2,)
    assert sim.last_trace_time_monotonic is True
    assert state["Y"] == 1

def test_b3_nonoverlap_event_id_backward_compatibility():
    n=_inv(100)
    epochs=[
        StimulusEpoch(ps_to_fs(100), {"A":1}, 1),
        StimulusEpoch(ps_to_fs(400), {"A":0}, 2),
    ]
    sim=TransportSimulator(n)
    tr,state=sim.run(epochs)
    assert [(e.event_id,e.time_fs,e.net,e.old_value,e.new_value) for e in tr] == [
        (1,ps_to_fs(100),"A",0,1),
        (2,ps_to_fs(200),"Y",1,0),
        (3,ps_to_fs(400),"A",1,0),
        (4,ps_to_fs(500),"Y",0,1),
    ]
    assert sim.last_overlap_epoch_ids == ()
    assert state["Y"] == 1

def test_b3_two_stage_overlap_transport_pulse():
    n=Network(
        ["A"],["Y"],
        [
            Cell("U1","INV",{"A":"A"},"n1",ps_to_fs(100),ps_to_fs(100)),
            Cell("U2","BUF",{"A":"n1"},"Y",ps_to_fs(80),ps_to_fs(120)),
        ],
        {"A":0},
    )
    epochs=[
        StimulusEpoch(ps_to_fs(100),{"A":1},1),
        StimulusEpoch(ps_to_fs(150),{"A":0},2),
    ]
    sim=TransportSimulator(n)
    tr,state=sim.run(epochs)
    y=[e for e in tr if e.net=="Y"]
    assert [(e.time_fs,e.old_value,e.new_value) for e in y] == [
        (ps_to_fs(320),1,0),
        (ps_to_fs(330),0,1),
    ]
    assert y[1].time_fs-y[0].time_fs == ps_to_fs(10)
    assert sim.last_overlap_epoch_ids == (2,)
    assert state["Y"] == 1

def test_b3_same_time_epochs_fail_closed():
    n=_inv(100)
    epochs=[
        StimulusEpoch(ps_to_fs(100),{"A":1},1),
        StimulusEpoch(ps_to_fs(100),{"A":0},2),
    ]
    try:
        TransportSimulator(n).run(epochs)
    except ValueError as e:
        assert "ambiguous same-time stimulus epochs" in str(e)
    else:
        raise AssertionError("Expected same-time epochs to fail closed")

def test_b3_trace_time_monotonic_metadata():
    n=_inv(100)
    epochs=[
        StimulusEpoch(ps_to_fs(100),{"A":1},10),
        StimulusEpoch(ps_to_fs(150),{"A":0},20),
        StimulusEpoch(ps_to_fs(500),{"A":1},30),
    ]
    sim=TransportSimulator(n)
    tr,_=sim.run(epochs)
    assert [e.time_fs for e in tr] == sorted(e.time_fs for e in tr)
    assert sim.last_trace_time_monotonic is True
    assert sim.last_global_chronological_queue is True
    assert sim.last_overlap_epoch_ids == (20,)

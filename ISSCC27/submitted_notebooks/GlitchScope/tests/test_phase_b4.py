from __future__ import annotations

from glitchscope.model import Cell, Network, StimulusEpoch, ps_to_fs
from glitchscope.timed import TransportSimulator
from glitchscope.inertial import InertialSimulator
from glitchscope.fixtures import xor_reconvergent_fixture
from glitchscope.analysis import stable_epoch_maps
from glitchscope.classify import extract_pulses
from glitchscope.lineage import classify_glitch_lineages

def _inv(delay_ps=100):
    return Network(
        ["A"],["Y"],
        [Cell("U_INV","INV",{"A":"A"},"Y",
              ps_to_fs(delay_ps),ps_to_fs(delay_ps))],
        {"A":0},
    )

def test_b4_short_input_pulse_is_suppressed():
    n=_inv(100)
    e=[
        StimulusEpoch(ps_to_fs(100),{"A":1},1),
        StimulusEpoch(ps_to_fs(150),{"A":0},2),
    ]
    m0,_=TransportSimulator(n).run(e)
    s=InertialSimulator(n)
    m1,state=s.run(e)
    assert len([x for x in m0 if x.net=="Y"])==2
    assert len([x for x in m1 if x.net=="Y"])==0
    assert state["Y"]==1
    assert len(s.last_suppressed_transitions)==1
    q=s.last_suppressed_transitions[0]
    assert q.instance=="U_INV" and q.net=="Y"
    assert q.scheduled_time_fs==ps_to_fs(200)
    assert q.cancel_time_fs==ps_to_fs(150)
    assert q.reason=="logical_reversal_before_pending_output_fired"

def test_b4_exact_delay_boundary_is_suppressed_by_tie_policy():
    n=_inv(100)
    e=[
        StimulusEpoch(ps_to_fs(100),{"A":1},1),
        StimulusEpoch(ps_to_fs(200),{"A":0},2),
    ]
    s=InertialSimulator(n)
    tr,state=s.run(e)
    assert len([x for x in tr if x.net=="Y"])==0
    assert len(s.last_suppressed_transitions)==1
    q=s.last_suppressed_transitions[0]
    assert q.scheduled_time_fs==q.cancel_time_fs==ps_to_fs(200)
    assert s.last_inertial_tie_policy=="external_epoch_first_cancel_if_equal_time"
    assert state["Y"]==1

def test_b4_long_input_pulse_survives_and_matches_m0():
    n=_inv(100)
    e=[
        StimulusEpoch(ps_to_fs(100),{"A":1},1),
        StimulusEpoch(ps_to_fs(250),{"A":0},2),
    ]
    m0,_=TransportSimulator(n).run(e)
    s=InertialSimulator(n)
    m1,state=s.run(e)
    a=[(x.time_fs,x.net,x.old_value,x.new_value) for x in m0]
    b=[(x.time_fs,x.net,x.old_value,x.new_value) for x in m1]
    assert a==b
    assert len(s.last_suppressed_transitions)==0
    assert state["Y"]==1

def test_b4_downstream_stage_rejects_pulse():
    n=Network(
        ["A"],["Y"],
        [
            Cell("U_INV","INV",{"A":"A"},"n1",ps_to_fs(20),ps_to_fs(20)),
            Cell("U_BUF","BUF",{"A":"n1"},"Y",ps_to_fs(100),ps_to_fs(100)),
        ],
        {"A":0},
    )
    e=[
        StimulusEpoch(ps_to_fs(100),{"A":1},1),
        StimulusEpoch(ps_to_fs(150),{"A":0},2),
    ]
    s=InertialSimulator(n)
    tr,state=s.run(e)
    n1=[x for x in tr if x.net=="n1"]
    y=[x for x in tr if x.net=="Y"]
    assert len(n1)==2
    assert n1[1].time_fs-n1[0].time_fs==ps_to_fs(50)
    assert y==[]
    qs=[q for q in s.last_suppressed_transitions if q.instance=="U_BUF"]
    assert len(qs)==1
    assert state["Y"]==1

def test_b4_reconvergent_hazard_suppressed_at_slow_output_gate():
    n=Network(
        ["A"],["Y"],
        [
            Cell("U_FAST","BUF",{"A":"A"},"n_fast",ps_to_fs(40),ps_to_fs(40)),
            Cell("U_SLOW","BUF",{"A":"A"},"n_slow",ps_to_fs(100),ps_to_fs(100)),
            Cell("U_XOR","XOR2",{"A":"n_fast","B":"n_slow"},"Y",
                 ps_to_fs(100),ps_to_fs(100)),
        ],
        {"A":0},
    )
    e=[StimulusEpoch(ps_to_fs(0),{"A":1},1)]
    m0,_=TransportSimulator(n).run(e)
    assert [(x.time_fs,x.old_value,x.new_value) for x in m0 if x.net=="Y"]==[
        (ps_to_fs(140),0,1),(ps_to_fs(200),1,0)
    ]
    s=InertialSimulator(n)
    m1,state=s.run(e)
    assert [x for x in m1 if x.net=="Y"]==[]
    qs=[q for q in s.last_suppressed_transitions if q.instance=="U_XOR"]
    assert len(qs)==1
    assert qs[0].scheduled_time_fs==ps_to_fs(140)
    assert qs[0].cancel_time_fs==ps_to_fs(100)
    assert state["Y"]==0

def test_b4_surviving_reconvergent_hazard_keeps_lineage_semantics():
    n,e=xor_reconvergent_fixture()
    b,a=stable_epoch_maps(n,e)
    s=InertialSimulator(n)
    tr,state=s.run(e)
    pulses=extract_pulses(tr,b,a)
    lin,edges=classify_glitch_lineages(tr,pulses)
    y=[p for p in pulses if p.net=="Y"]
    assert len(y)==1 and y[0].width_fs==ps_to_fs(60)
    yl=[g for g in lin if g.net=="Y"]
    assert len(yl)==1
    assert yl[0].classification=="GENERATED"
    assert yl[0].root_ids==("GROOT0001",)
    assert s.last_suppressed_transitions==()
    assert state["Y"]==0

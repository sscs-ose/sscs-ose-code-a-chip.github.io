from __future__ import annotations

from glitchscope.model import Cell, Network, StimulusEpoch, ps_to_fs
from glitchscope.timed import TransportSimulator
from glitchscope.inertial import InertialSimulator
from glitchscope.analysis import stable_epoch_maps
from glitchscope.classify import extract_pulses
from glitchscope.lineage import classify_glitch_lineages

def _net(chain_delays, xor_delay):
    cells=[]
    prev="S"
    for i,d in enumerate(chain_delays,1):
        out="B%d"%i
        cells.append(Cell("U_B%d"%i,"BUF",{"A":prev},out,ps_to_fs(d),ps_to_fs(d)))
        prev=out
    cells.append(Cell("U_X","XOR2",{"A":"S","B":prev},"Y",
                      ps_to_fs(xor_delay),ps_to_fs(xor_delay)))
    return Network(["S"],["Y"],cells,{"S":0})

def _pulses(net, tr, ep):
    b,a=stable_epoch_maps(net,[ep])
    p=extract_pulses(tr,b,a)
    l,e=classify_glitch_lineages(tr,p)
    return p,l,e

def test_b6_short_real_style_reconvergence_m0_generated_m1_suppressed():
    n=_net([60],100)
    ep=StimulusEpoch(ps_to_fs(100),{"S":1},1)
    m0=TransportSimulator(n)
    t0,s0=m0.run([ep])
    p0,l0,_=_pulses(n,t0,ep)
    y=[p for p in p0 if p.net=="Y"]
    assert len(y)==1 and y[0].width_fs==ps_to_fs(60)
    gy=[g for g in l0 if g.net=="Y"]
    assert len(gy)==1 and gy[0].classification=="GENERATED"
    assert gy[0].root_ids==("GROOT0001",)

    m1=InertialSimulator(n)
    t1,s1=m1.run([ep])
    p1,_,_=_pulses(n,t1,ep)
    assert not [p for p in p1 if p.net=="Y"]
    assert not [e for e in t1 if e.net=="Y"]
    sx=[x for x in m1.last_suppressed_transitions if x.instance=="U_X"]
    assert len(sx)==1 and sx[0].net=="Y"
    assert sx[0].cancel_time_fs < sx[0].scheduled_time_fs
    assert s0["Y"]==0 and s1["Y"]==0

def test_b6_long_real_style_reconvergence_m1_survives_exactly():
    n=_net([80,80],100)
    ep=StimulusEpoch(ps_to_fs(100),{"S":1},1)
    m0=TransportSimulator(n); t0,s0=m0.run([ep])
    m1=InertialSimulator(n); t1,s1=m1.run([ep])
    y0=[(e.time_fs,e.old_value,e.new_value) for e in t0 if e.net=="Y"]
    y1=[(e.time_fs,e.old_value,e.new_value) for e in t1 if e.net=="Y"]
    assert y0==y1
    assert len(y1)==2
    assert y1[1][0]-y1[0][0]==ps_to_fs(160)
    assert not [x for x in m1.last_suppressed_transitions if x.instance=="U_X"]
    p,l,_=_pulses(n,t1,ep)
    gy=[g for g in l if g.net=="Y"]
    assert len(gy)==1 and gy[0].classification=="GENERATED"
    assert gy[0].root_ids==("GROOT0001",)
    assert s0["Y"]==0 and s1["Y"]==0

def test_b6_suppression_ledger_preserves_both_causal_sides():
    n=_net([60],100)
    ep=StimulusEpoch(ps_to_fs(100),{"S":1},7)
    sim=InertialSimulator(n)
    tr,_=sim.run([ep])
    sx=[x for x in sim.last_suppressed_transitions if x.instance=="U_X"]
    assert len(sx)==1
    s=sx[0]
    assert s.epoch_id==7
    assert len(s.original_parent_event_ids)==1
    assert len(s.cancel_parent_event_ids)==1
    ev={e.event_id:e for e in tr}
    assert ev[s.original_parent_event_ids[0]].net=="S"
    assert ev[s.cancel_parent_event_ids[0]].net=="B1"
    assert s.reason=="logical_reversal_before_pending_output_fired"

def test_b6_chain_skew_controls_m1_outcome():
    ep=StimulusEpoch(ps_to_fs(100),{"S":1},1)
    short=InertialSimulator(_net([60],100))
    ts,_=short.run([ep])
    long=InertialSimulator(_net([80,80],100))
    tl,_=long.run([ep])
    assert len([e for e in ts if e.net=="Y"])==0
    assert len([e for e in tl if e.net=="Y"])==2
    assert len([x for x in short.last_suppressed_transitions if x.instance=="U_X"])==1
    assert len([x for x in long.last_suppressed_transitions if x.instance=="U_X"])==0

def test_b6_reconvergent_m0_m1_determinism_100_runs():
    n=_net([60],100)
    ep=StimulusEpoch(ps_to_fs(100),{"S":1},1)
    def sig():
        m0=TransportSimulator(n); t0,_=m0.run([ep])
        m1=InertialSimulator(n); t1,_=m1.run([ep])
        return (
            tuple((e.event_id,e.time_fs,e.net,e.old_value,e.new_value,e.parent_event_ids)
                  for e in t0),
            tuple((e.event_id,e.time_fs,e.net,e.old_value,e.new_value,e.parent_event_ids)
                  for e in t1),
            tuple((x.event_id,x.instance,x.net,x.scheduled_time_fs,x.cancel_time_fs,
                   x.original_parent_event_ids,x.cancel_parent_event_ids,x.reason)
                  for x in m1.last_suppressed_transitions),
        )
    ref=sig()
    for _ in range(99):
        assert sig()==ref

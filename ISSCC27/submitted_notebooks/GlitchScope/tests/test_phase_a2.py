from __future__ import annotations
import hashlib,tempfile
from pathlib import Path
from glitchscope.fixtures import changed_final_state_glitch_fixture,two_epoch_glitch_fixture,merged_roots_fixture
from glitchscope.timed import TransportSimulator
from glitchscope.analysis import stable_epoch_maps
from glitchscope.classify import extract_pulses
from glitchscope.lineage import classify_glitch_lineages
from glitchscope.report import write_results
from glitchscope.model import ps_to_fs

def analyze(f):
    n,e=f(); b,a=stable_epoch_maps(n,e); tr,st=TransportSimulator(n).run(e)
    p=extract_pulses(tr,b,a); l,ed=classify_glitch_lineages(tr,p)
    return tr,p,l,ed,st,b,a

def test_changed_final_state_extra_pairing():
    tr,p,l,ed,st,b,a=analyze(changed_final_state_glitch_fixture)
    y=[e for e in tr if e.net=="Y"]
    assert [(e.time_fs,e.old_value,e.new_value) for e in y]==[(ps_to_fs(50),0,1),(ps_to_fs(110),1,0),(ps_to_fs(170),0,1)]
    yp=[x for x in p if x.net=="Y"]; assert len(yp)==1
    assert yp[0].width_fs==ps_to_fs(60) and yp[0].polarity=="positive"
    assert b[1]["Y"]==0 and a[1]["Y"]==1 and st["Y"]==1

def test_two_epochs_distinct_roots():
    _,_,l,_,st,_,_=analyze(two_epoch_glitch_fixture)
    ys=[g for g in l if g.net=="Y"]; assert len(ys)==2
    assert [g.epoch_id for g in ys]==[1,2]
    assert ys[0].root_ids==("GROOT0001",) and ys[1].root_ids==("GROOT0002",)
    assert all(g.classification=="GENERATED" and g.width_fs==ps_to_fs(60) for g in ys)

def test_merged_roots():
    _,_,l,_,st,_,_=analyze(merged_roots_fixture)
    d={g.net:g for g in l}
    assert d["n_g1"].classification=="GENERATED"
    assert d["n_g2"].classification=="GENERATED"
    assert d["Y"].classification=="MERGED"
    assert d["Y"].root_ids==("GROOT0001","GROOT0002")
    assert d["Y"].width_fs==ps_to_fs(80)

def test_a2_determinism_100_runs():
    hs=set()
    with tempfile.TemporaryDirectory() as td:
        for i in range(100):
            tr,p,l,ed,st,_,_=analyze(merged_roots_fixture)
            o=Path(td)/str(i); write_results(o,tr,p,st,l,ed)
            blob=b"".join((o/n).read_bytes() for n in ("events.csv","glitches.csv","lineages.csv","lineages.json","lineage_edges.csv","summary.json"))
            hs.add(hashlib.sha256(blob).hexdigest())
    assert len(hs)==1

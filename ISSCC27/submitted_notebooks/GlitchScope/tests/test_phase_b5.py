from __future__ import annotations
from pathlib import Path
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import Cell, Network, StimulusEpoch, ps_to_fs
from glitchscope.timed import TransportSimulator
from glitchscope.inertial import InertialSimulator

ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/"tests/fixtures/synthetic_b5.lib"

def _xor_cell():
    return Cell(
        "U_X","XOR2",{"A":"A","B":"B"},"X",0,0,
        library_cell="XOR2DUAL",library_output_pin="X"
    )

def test_b5_dual_sense_direct_arc_selection():
    lib=parse_liberty_file(LIB); p=LibertyDelayProvider(lib); c=_xor_cell()
    a=p.select_arc(
        c,1,related_pin="A",pin_values={"A":1,"B":0},input_transition=(0,1)
    )
    assert a.timing_sense=="positive_unate"
    a=p.select_arc(
        c,0,related_pin="A",pin_values={"A":1,"B":1},input_transition=(0,1)
    )
    assert a.timing_sense=="negative_unate"
    a=p.select_arc(
        c,1,related_pin="B",pin_values={"A":0,"B":1},input_transition=(0,1)
    )
    assert a.timing_sense=="positive_unate"
    a=p.select_arc(
        c,0,related_pin="B",pin_values={"A":1,"B":1},input_transition=(0,1)
    )
    assert a.timing_sense=="negative_unate"

def test_b5_xor_transport_uses_state_consistent_sense():
    lib=parse_liberty_file(LIB); p=LibertyDelayProvider(lib)
    # B=0: A rising => positive-unate, X rises.
    n=Network(["A","B"],["X"],[_xor_cell()],{"A":0,"B":0})
    tr,_=TransportSimulator(
        n,p,default_input_slew_fs=ps_to_fs(20),load_ff_by_net={"X":2.0}
    ).run([StimulusEpoch(ps_to_fs(100),{"A":1},1)])
    x=[e for e in tr if e.net=="X"]
    assert len(x)==1 and x[0].old_value==0 and x[0].new_value==1
    # B=1: A rising => negative-unate, X falls.
    n=Network(["A","B"],["X"],[_xor_cell()],{"A":0,"B":1})
    tr,_=TransportSimulator(
        n,p,default_input_slew_fs=ps_to_fs(20),load_ff_by_net={"X":2.0}
    ).run([StimulusEpoch(ps_to_fs(100),{"A":1},1)])
    x=[e for e in tr if e.net=="X"]
    assert len(x)==1 and x[0].old_value==1 and x[0].new_value==0

def test_b5_m1_uses_same_multi_arc_selection():
    lib=parse_liberty_file(LIB); p=LibertyDelayProvider(lib)
    n=Network(["A","B"],["X"],[_xor_cell()],{"A":0,"B":1})
    m0,_=TransportSimulator(
        n,p,default_input_slew_fs=ps_to_fs(20),load_ff_by_net={"X":2.0}
    ).run([StimulusEpoch(ps_to_fs(100),{"A":1},1)])
    m1,_=InertialSimulator(
        n,p,default_input_slew_fs=ps_to_fs(20),load_ff_by_net={"X":2.0}
    ).run([StimulusEpoch(ps_to_fs(100),{"A":1},1)])
    x0=[e for e in m0 if e.net=="X"]
    x1=[e for e in m1 if e.net=="X"]
    assert [(e.time_fs,e.old_value,e.new_value) for e in x1] == [
        (e.time_fs,e.old_value,e.new_value) for e in x0
    ]

def test_b5_duplicate_same_sense_remains_fail_closed():
    lib=parse_liberty_file(LIB); p=LibertyDelayProvider(lib)
    c=Cell(
        "U","BUF",{"A":"A"},"Y",0,0,
        library_cell="DUPPOS",library_output_pin="Y"
    )
    try:
        p.select_arc(
            c,1,related_pin="A",pin_values={"A":1},input_transition=(0,1)
        )
    except ValueError as e:
        assert "Ambiguous" in str(e)
    else:
        raise AssertionError("Duplicate same-sense arcs must remain fail-closed")

def test_b5_non_unate_duplicate_remains_fail_closed():
    lib=parse_liberty_file(LIB); p=LibertyDelayProvider(lib)
    c=Cell(
        "U","BUF",{"A":"A"},"Y",0,0,
        library_cell="DUPNON",library_output_pin="Y"
    )
    try:
        p.select_arc(
            c,1,related_pin="A",pin_values={"A":1},input_transition=(0,1)
        )
    except ValueError as e:
        assert "Ambiguous" in str(e)
    else:
        raise AssertionError("Duplicate non-unate arcs must remain fail-closed")

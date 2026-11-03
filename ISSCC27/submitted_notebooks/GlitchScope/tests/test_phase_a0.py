import hashlib, tempfile
from pathlib import Path
from glitchscope.logic import eval_primitive
from glitchscope.fixtures import inverter_fixture, xor_atomic_no_glitch_fixture, xor_reconvergent_fixture
from glitchscope.timed import TransportSimulator
from glitchscope.analysis import stable_epoch_maps
from glitchscope.classify import extract_pulses
from glitchscope.report import write_results
from glitchscope.model import ps_to_fs

def run_case(factory):
    net, epochs = factory()
    before, after = stable_epoch_maps(net, epochs)
    trace, final_state = TransportSimulator(net).run(epochs)
    pulses = extract_pulses(trace, before, after)
    return trace, pulses, final_state

def test_truth_tables():
    for a in (0,1):
        assert eval_primitive("BUF",{"A":a}) == a
        assert eval_primitive("INV",{"A":a}) == 1-a
    for a in (0,1):
        for b in (0,1):
            assert eval_primitive("AND2",{"A":a,"B":b}) == (a & b)
            assert eval_primitive("OR2",{"A":a,"B":b}) == (a | b)
            assert eval_primitive("NAND2",{"A":a,"B":b}) == 1-(a & b)
            assert eval_primitive("NOR2",{"A":a,"B":b}) == 1-(a | b)
            assert eval_primitive("XOR2",{"A":a,"B":b}) == (a ^ b)
            assert eval_primitive("XNOR2",{"A":a,"B":b}) == 1-(a ^ b)
            assert eval_primitive("MUX2",{"A":a,"B":b,"S":0}) == a
            assert eval_primitive("MUX2",{"A":a,"B":b,"S":1}) == b

def test_inverter():
    trace,pulses,state = run_case(inverter_fixture)
    y=[e for e in trace if e.net=="Y"]
    assert len(y)==1 and y[0].time_fs==ps_to_fs(150)
    assert (y[0].old_value,y[0].new_value)==(1,0)
    assert pulses==[]
    assert state["Y"]==0

def test_atomic_xor_no_false_glitch():
    trace,pulses,state = run_case(xor_atomic_no_glitch_fixture)
    assert [e for e in trace if e.net=="Y"] == []
    assert pulses == []
    assert state["Y"] == 0

def test_reconvergent_xor_60ps_glitch():
    trace,pulses,state = run_case(xor_reconvergent_fixture)
    y=[e for e in trace if e.net=="Y"]
    assert [(e.time_fs,e.old_value,e.new_value) for e in y] == [
        (ps_to_fs(60),0,1),(ps_to_fs(120),1,0)
    ]
    assert len(pulses)==1
    assert pulses[0].net=="Y"
    assert pulses[0].width_fs==ps_to_fs(60)
    assert pulses[0].polarity=="positive"
    assert state["Y"]==0

def test_determinism_100_runs():
    hs=set()
    with tempfile.TemporaryDirectory() as td:
        for i in range(100):
            trace,pulses,state = run_case(xor_reconvergent_fixture)
            out=Path(td)/str(i)
            write_results(out,trace,pulses,state)
            blob=b"".join((out/n).read_bytes() for n in ("events.csv","glitches.csv","summary.json"))
            hs.add(hashlib.sha256(blob).hexdigest())
    assert len(hs)==1

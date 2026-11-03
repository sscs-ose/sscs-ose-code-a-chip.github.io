from __future__ import annotations
from pathlib import Path
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider, eval_when
from glitchscope.model import Cell, Network, StimulusEpoch, ps_to_fs
from glitchscope.timed import TransportSimulator

ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'tests/fixtures/synthetic_b1.lib'

def test_b1_quoted_cap_unit_and_arc_inventory():
    lib=parse_liberty_file(LIB)
    assert lib.time_unit_ps==1000.0
    assert lib.capacitance_unit_ff==1000.0
    assert len(lib.cells['NAND2X1'].timing_arcs)==2
    assert set(a.related_pin for a in lib.cells['NAND2X1'].timing_arcs)=={'A','B'}

def test_b1_when_evaluator():
    assert eval_when('B',{'A':0,'B':1})
    assert not eval_when('B',{'A':0,'B':0})
    assert eval_when('A&!B',{'A':1,'B':0})
    assert eval_when('(A^B)|C',{'A':1,'B':0,'C':0})

def test_b1_multi_input_conditional_arc_selection():
    lib=parse_liberty_file(LIB); p=LibertyDelayProvider(lib)
    c=Cell('U1','NAND2',{'A':'a','B':'b'},'y',0,0,library_cell='NAND2X1',library_output_pin='Y')
    qa=p.delay(c,0,input_slew_fs=ps_to_fs(20),load_ff=2.0,related_pin='A',pin_values={'A':1,'B':1},input_transition=(0,1))
    qb=p.delay(c,0,input_slew_fs=ps_to_fs(20),load_ff=2.0,related_pin='B',pin_values={'A':1,'B':1},input_transition=(0,1))
    assert qa.delay_fs==ps_to_fs(51)
    assert qb.delay_fs==ps_to_fs(55)

def test_b1_timing_sense_fail_closed():
    lib=parse_liberty_file(LIB); p=LibertyDelayProvider(lib)
    c=Cell('U1','INV',{'A':'a'},'y',0,0,library_cell='INVX1',library_output_pin='Y')
    # Negative-unate A rising must produce Y falling.
    p.delay(c,0,input_slew_fs=ps_to_fs(20),load_ff=2.0,related_pin='A',pin_values={'A':1},input_transition=(0,1))
    try:
        p.delay(c,1,input_slew_fs=ps_to_fs(20),load_ff=2.0,related_pin='A',pin_values={'A':1},input_transition=(0,1))
    except ValueError as e:
        assert 'timing_sense' in str(e)
    else:
        raise AssertionError('Expected timing-sense mismatch to fail closed')

def test_b1_real_style_nand_simulation():
    lib=parse_liberty_file(LIB); p=LibertyDelayProvider(lib)
    net=Network(['A','B'],['Y'],[
        Cell('U1','NAND2',{'A':'A','B':'B'},'Y',0,0,library_cell='NAND2X1',library_output_pin='Y')
    ],{'A':0,'B':1})
    tr,state=TransportSimulator(net,p,default_input_slew_fs=ps_to_fs(20),load_ff_by_net={'Y':2.0}).run([
        StimulusEpoch(ps_to_fs(100),{'A':1},1)
    ])
    y=[e for e in tr if e.net=='Y']
    assert len(y)==1 and y[0].time_fs==ps_to_fs(151)
    assert state['Y']==0

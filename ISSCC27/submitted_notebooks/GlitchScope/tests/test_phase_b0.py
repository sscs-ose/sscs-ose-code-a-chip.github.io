from __future__ import annotations
from pathlib import Path
from glitchscope.model import Network,Cell,StimulusEpoch,ps_to_fs
from glitchscope.liberty import parse_liberty_file,bilinear,LibertyDelayProvider
from glitchscope.timed import TransportSimulator
ROOT=Path(__file__).resolve().parents[1]; LIB=ROOT/'tests/fixtures/synthetic_inv.lib'
def test_parse():
 l=parse_liberty_file(LIB); assert l.time_unit_ps==1000.0 and l.capacitance_unit_ff==1000.0; assert abs(l.cells['INVX1'].pin_capacitance['A']-2.0)<1e-12
def test_bilinear():
 l=parse_liberty_file(LIB); assert abs(bilinear(l.cells['INVX1'].timing_arcs[0].cell_rise,0.020,0.002)-0.040)<1e-12
def test_provider():
 l=parse_liberty_file(LIB); p=LibertyDelayProvider(l); c=Cell('U1','INV',{'A':'A'},'Y',0,0,library_cell='INVX1'); r=p.delay(c,1,ps_to_fs(20),2.0,'A'); f=p.delay(c,0,ps_to_fs(20),2.0,'A'); assert r.delay_fs==ps_to_fs(40) and r.output_slew_fs==ps_to_fs(18); assert f.delay_fs==ps_to_fs(50) and f.output_slew_fs==ps_to_fs(20)
def test_sim():
 l=parse_liberty_file(LIB); p=LibertyDelayProvider(l); n=Network(['A'],['Y'],[Cell('U','INV',{'A':'A'},'Y',0,0,library_cell='INVX1')],{'A':0}); tr,st=TransportSimulator(n,p,ps_to_fs(20),{'Y':2.0}).run([StimulusEpoch(ps_to_fs(100),{'A':1},1)]); y=[e for e in tr if e.net=='Y']; assert len(y)==1 and y[0].time_fs==ps_to_fs(150) and st['Y']==0

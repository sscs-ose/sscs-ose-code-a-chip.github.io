import sys, random, statistics; sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))))
from dataclasses import replace
from glitchscope.verilog import read_verilog
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import ps_to_fs, Cell
from glitchscope.sim import PulseSimulator
from glitchscope.m2model import M2Model
from glitchscope.analyze import EnergyModel, analyze
import csv
L=[l.split('=',1)[1] for l in open('tools.env') if l.startswith('GS_LIB=')][0].strip()
dp=LibertyDelayProvider(parse_liberty_file(L)); m2=M2Model()
def run(net,vecs):
    a=analyze(PulseSimulator(net,dp,'M2',r_filter=m2,default_input_slew_fs=ps_to_fs(40)),EnergyModel(L,net,spice_scale=True),vecs)
    return a['totals']
def ins(net,target,pin,n):
    cells=[c for c in net.cells if c.name!=target]; t=[c for c in net.cells if c.name==target][0]; src=t.inputs[pin]
    for i in range(n):
        o=f"{target}_b{i}"; cells.append(Cell(f"{target}_B{i}","BUF",{"A":src},o,1000,1000,library_cell="sky130_fd_sc_hd__buf_1",library_output_pin="X")); src=o
    cells.append(replace(t,inputs={**t.inputs,pin:src})); return replace(net,cells=cells)
for b,target in [('mul4','_41_'),('mul4','_36_'),('rca8','_53_')]:
    net=read_verilog(f'bench/netlists/{b}.v'); rnd=random.Random(7); vecs=[{p:rnd.randint(0,1) for p in net.primary_inputs} for _ in range(300)]
    rows=[r for r in csv.DictReader(open(f'data/bench/skew_{b}.csv')) if r['cell']==target]
    pin=statistics.mode(r['lead_pin'] for r in rows)
    T0=run(net,vecs); out=[]
    for n in range(1,9):
        T=run(ins(net,target,pin,n),vecs)
        out.append(f"{n}:{100*(T['E_glitch_fJ']-T0['E_glitch_fJ'])/T0['E_glitch_fJ']:+.0f}%/{100*(T['E_total_fJ']-T0['E_total_fJ'])/T0['E_total_fJ']:+.1f}%")
    print(b,target,'lead pin',pin,'| n_buf: glitch/total ->',' '.join(out))

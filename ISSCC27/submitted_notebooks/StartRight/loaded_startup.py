"""Loaded startup bench. All circuit power comes from VDD."""
import json
import numpy as np
from pilot import simulate
from widlar_confirm import setup
from widlar_pilot import STUDY

LOAD_STUDY=STUDY.parent/'loaded'
LOAD_STUDY.mkdir(exist_ok=True)

def load_circuit(resistance=1e5):
    return f'''RUSE vdd sense {resistance}
VSENSE sense out 0
XUSE out b 0 0 sky130_fd_pr__nfet_01v8 w=.42 l=20 ad=.1218 as=.1218 pd=1.42 ps=1.42
COUT out 0 100f
'''

def loaded_deck(width=.42,resistance=1e5,ramp=1e-6,op=False,dc_load=None,gmin=1e-15):
    head='Loaded inverse-Widlar startup bench\n'+setup(gmin,width).replace('.option scale=1u','.option method=gear maxord=2 scale=1u')
    if op:
        source='VDD vdd 0 1.8\n.nodeset v(a)=.27 v(b)=1.16 v(c)=.525\n'
        analysis='op';file='op.dat'
    else:
        stop=ramp+.02
        source=f'VDD vdd 0 PWL(0 0 1u 0 {ramp+1e-6} 1.8 {stop} 1.8)\n'
        analysis=f'tran 1u {stop} 0 10u';file='cold.dat'
    result=head+source+load_circuit(resistance)
    if dc_load is not None: result+=f'RDCLOAD b 0 {dc_load}\n'
    return result+f'''.control
set wr_singlescale
set wr_vecnames
{analysis}
wrdata {file} v(a) v(b) v(c) i(VDD) v(vdd) v(out) i(VSENSE)
quit
.endc
.end
'''

if __name__=='__main__':
    rows=[]
    for r in [1e4,1e5,1e6]:
        folder=simulate(f'loaded_op_r{r}',loaded_deck(resistance=r,op=True),compatibility='hsa',solver='klu',threads=1)
        d=np.loadtxt(folder/'op.dat',skiprows=1)
        row={'kind':'op','name':folder.name,'resistance_ohm':r,'b_V':float(d[2]),'source_A':float(-d[4]),'out_V':float(d[6]),'output_A':float(d[7])}
        rows.append(row);print(json.dumps(row),flush=True)
    target=next(r['output_A'] for r in rows if r['resistance_ohm']==1e5)
    for r in [1e4,1e5,1e6]:
        for w in [None,.42,1.0]:
            for ramp in [1e-6,1e-3]:
                folder=simulate(f'loaded_cold_r{r}_w{w}_ramp{ramp}',loaded_deck(w,r,ramp),compatibility='hsa',solver='klu',threads=1)
                d=np.loadtxt(folder/'cold.dat',skiprows=1)
                good=(abs(d[:,7]-target)<=.05*target)&(d[:,6]>=.3)&(d[:,5]>=1.7)
                outside=np.flatnonzero(~good);first=int(outside[-1]+1) if len(outside) else 0
                ready=float(d[first,0]) if first<len(d) and d[-1,0]-d[first,0]>=.002 else None
                energy=float(np.trapezoid(-d[:first+1,4]*d[:first+1,5],d[:first+1,0])) if ready is not None else None
                row={'kind':'cold','name':folder.name,'resistance_ohm':r,'startup_width_um':w,'ramp_s':ramp,'target_output_A':target,'final_b_V':float(d[-1,2]),'final_out_V':float(d[-1,6]),'final_output_A':float(d[-1,7]),'final_source_A':float(-d[-1,4]),'ready_time_s':ready,'source_energy_to_ready_J':energy,'deadline_s':ramp+1e-6+.001,'meets_contract':ready is not None and ready<=ramp+1e-6+.001}
                rows.append(row);print(json.dumps(row),flush=True)
                (LOAD_STUDY/'loaded_results.json').write_text(json.dumps({'contract':{'target_A':target,'tolerance_fraction':.05,'minimum_output_V':.3,'minimum_VDD_V':1.7,'hold_s':.002,'deadline_after_ramp_s':.001,'time_origin':'simulation t=0, initial source delay 1 us'},'cases':rows},indent=2))

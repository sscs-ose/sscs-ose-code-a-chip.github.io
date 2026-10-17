"""Confirm candidate equilibria in the intact inverse-Widlar circuit.
Initial conditions and nodesets are diagnostics, not a physical startup history.
"""
import json
import numpy as np
from pilot import simulate,models
from widlar_pilot import core,find_roots,STUDY

PARAMS={'pwidth':12,'mirror_width':.42,'mirror_length':20}

def junctions(text):
    lines=[]
    for line in text.splitlines():
        if line.startswith('XM') or line.startswith('XMS'):
            w=float(line.split(' w=')[1].split()[0])
            line+=f' ad={w*.29:.12g} as={w*.29:.12g} pd={2*(w+.29):.12g} ps={2*(w+.29):.12g}'
        lines.append(line)
    return '\n'.join(lines)+'\n'

def setup(gmin=1e-15,startup_width=None,broken=False):
    return models().replace('.option scale=1u',f'.option scale=1u gmin={gmin} abstol=1e-16 reltol=1e-6 vntol=1e-8')+'.temp 27\n'+junctions(core(**PARAMS,startup_width=startup_width,broken=broken))

def return_deck(gmin=1e-15,startup_width=None,direction=1):
    start,end,step=(0,1.8,.0005) if direction==1 else (1.8,0,-.0005)
    return 'Junction-aware inverse-Widlar DC return curve\n'+setup(gmin,startup_width,True)+f'''VDD vdd 0 1.8
VIN vin 0 0
.control
set wr_singlescale
set wr_vecnames
dc VIN {start} {end} {step}
wrdata return.dat v(b) v(a) v(c) i(VDD) i(VIN)
quit
.endc
.end
'''

def intact_deck(state,gmin=1e-15,startup_width=None,transient=False,perturb=0):
    a,b,c=state
    init=f'.ic v(a)={a} v(b)={b+perturb} v(c)={c}' if transient else f'.nodeset v(a)={a} v(b)={b} v(c)={c}'
    command='tran 1u 20m 0 10u uic' if transient else 'op'
    filename='transient.dat' if transient else 'op.dat'
    return 'Intact inverse-Widlar equilibrium diagnostic\n'+setup(gmin,startup_width)+f'''VDD vdd 0 1.8
{init}
.control
set wr_singlescale
set wr_vecnames
{command}
wrdata {filename} v(a) v(b) v(c) i(VDD)
quit
.endc
.end
'''

if __name__=='__main__':
    scans=[]
    for g in [1e-12,1e-15]:
        for direction in [1,-1]:
            name=f'widlar_confirm_g{g}_dir{direction}'
            folder=simulate(name,return_deck(g,direction=direction))
            d=np.loadtxt(folder/'return.dat',skiprows=1)
            row={'name':name,'gmin_S':g,'direction':direction,'roots':find_roots(d),'max_abs_cut_gate_current_A':float(abs(d[:,5]).max())}
            scans.append(row);print(json.dumps(row),flush=True)
    (STUDY/'confirmed_return_scans.json').write_text(json.dumps(scans,indent=2))
    source=np.loadtxt(folder.parent/'widlar_confirm_g1e-15_dir1'/'return.dat',skiprows=1)
    roots=find_roots(source)
    intact=[]
    for k,root in enumerate(roots):
        b=root['vin_V'];a=np.interp(b,source[:,0],source[:,2]);c=np.interp(b,source[:,0],source[:,3])
        state=[a,b,c]
        folder=simulate(f'widlar_intact_op_{k}',intact_deck(state))
        d=np.loadtxt(folder/'op.dat',skiprows=1)
        row={'root_index':k,'candidate_b_V':b,'intact_a_V':float(d[1]),'intact_b_V':float(d[2]),'intact_c_V':float(d[3]),'intact_supply_A':float(-d[4]),'b_error_V':float(abs(d[2]-b))}
        intact.append(row);print(json.dumps(row),flush=True)
    (STUDY/'intact_operating_points.json').write_text(json.dumps(intact,indent=2))

import json
import numpy as np
from pilot import simulate
from widlar_pilot import STUDY,find_roots
from widlar_confirm import return_deck,intact_deck,setup

if __name__=='__main__':
    rows=[]
    for w in [.42,1]:
        folder=simulate(f'widlar_startup_return_w{w}',return_deck(startup_width=w))
        d=np.loadtxt(folder/'return.dat',skiprows=1)
        row={'kind':'startup_return','width_um':w,'roots':find_roots(d)}
        rows.append(row);print(json.dumps(row),flush=True)
    op=json.loads((STUDY/'intact_operating_points.json').read_text())
    for k,delta in [(0,.005),(0,-.005),(1,.001),(1,-.001),(2,.005),(2,-.005)]:
        row=op[k];state=[row['intact_a_V'],row['intact_b_V'],row['intact_c_V']]
        name=f'widlar_perturb_root{k}_delta{delta}'
        deck=intact_deck(state,transient=True,perturb=delta)
        deck=deck.replace('10u uic','10u').replace('.option scale=1u','.option method=gear maxord=2 scale=1u')
        folder=simulate(name,deck)
        d=np.loadtxt(folder/'transient.dat',skiprows=1)
        result={'kind':'perturbation','name':name,'initial_root':k,'delta_b_V':delta,'final_b_V':float(d[-1,2]),'final_source_A':float(-d[-1,4]),'tstop_s':float(d[-1,0])}
        rows.append(result);print(json.dumps(result),flush=True)
    (STUDY/'startup_and_stability.json').write_text(json.dumps(rows,indent=2))

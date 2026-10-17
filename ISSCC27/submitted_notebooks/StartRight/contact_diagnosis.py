"""Separate compatibility, solver and thread settings from contact geometry."""
import json
import numpy as np
from pilot import simulate
from widlar_confirm import return_deck
from widlar_pilot import STUDY,find_roots,audit_return_case

def contact_deck(gmin=1e-15,step=.01):
    deck=return_deck(gmin).replace('dc VIN 0 1.8 0.0005',f'dc VIN 0 1.8 {step}')
    lines=[]
    for line in deck.splitlines():
        if line.startswith('XM'):
            w=float(line.split(' w=')[1].split()[0]);line+=f' nrd={.29/w:.12g} nrs={.29/w:.12g}'
        lines.append(line)
    return '\n'.join(lines)+'\n'

if __name__=='__main__':
    rows=[]
    for compat,solver,threads in [('hs','sparse',1),('hsa','klu',1),('hs','klu',1),('hsa','sparse',1),('hs','sparse',8),('hsa','klu',8)]:
        name=f'contact_diagnosis_{compat}_{solver}_t{threads}'
        folder=simulate(name,contact_deck(),compatibility=compat,solver=solver,threads=threads)
        audit=audit_return_case(folder,181)
        d=np.loadtxt(folder/'return.dat',skiprows=1)
        row={'name':name,'compatibility':compat,'solver':solver,'threads':threads,'audit':audit,'roots':find_roots(d) if audit['accepted'] else []}
        rows.append(row)
        print(json.dumps(row),flush=True)
        (STUDY/'contact_diagnosis.json').write_text(json.dumps(rows,indent=2))

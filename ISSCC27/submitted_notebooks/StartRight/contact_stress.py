import json
import numpy as np
from pilot import simulate
from widlar_confirm import return_deck
from widlar_pilot import STUDY,audit_return_case,find_roots
rows=[]
for choice,options in [('pivot','.option pivtol=1e-22 pivrel=1e-9'),('loose','.option abstol=1e-14 reltol=1e-4')]:
    deck=return_deck().replace('dc VIN 0 1.8 0.0005','dc VIN 0 1.8 0.02')
    lines=[]
    for line in deck.splitlines()[1:]:
        if line.startswith('XM'):
            w=float(line.split(' w=')[1].split()[0]);line+=f' nrd={.29/w:.12g} nrs={.29/w:.12g}'
        lines.append(line)
    deck='Contact numerical stress test\n'+'\n'.join(lines)+'\n'
    deck=deck.replace('.control',options+'\n.control')
    folder=simulate(f'contact_stress_{choice}',deck,compatibility='hsa',solver='klu',threads=1)
    audit=audit_return_case(folder,91)
    row={'name':folder.name,'audit':audit};rows.append(row);print(json.dumps(row),flush=True)
(STUDY/'contact_stress.json').write_text(json.dumps(rows,indent=2))

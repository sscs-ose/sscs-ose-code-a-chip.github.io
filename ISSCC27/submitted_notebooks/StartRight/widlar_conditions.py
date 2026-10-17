import json
import numpy as np
from pilot import simulate
from widlar_confirm import return_deck
from widlar_pilot import STUDY,find_roots
rows=[]
for corner in ['tt','ff','ss','sf','fs']:
    for temp in [-20,27,85]:
        for w in [None,.42]:
            deck=return_deck(startup_width=w).replace('__tt.corner.spice',f'__{corner}.corner.spice').replace('.temp 27',f'.temp {temp}').replace('dc VIN 0 1.8 0.0005','dc VIN 0 1.8 0.002')
            name=f'widlar_conditions_{corner}_{temp}_w{w}'
            try:
                folder=simulate(name,deck)
                d=np.loadtxt(folder/'return.dat',skiprows=1)
                roots=find_roots(d)
                row={'name':name,'corner':corner,'temperature_C':temp,'startup_width_um':w,'roots':roots,'status':'complete','points':len(d)}
            except Exception as e:
                row={'name':name,'corner':corner,'temperature_C':temp,'startup_width_um':w,'status':'failed','error':str(e)[-1200:]}
            rows.append(row)
            print(json.dumps({k:v for k,v in row.items() if k!='roots'}|{'root_count':len(row.get('roots',[]))}),flush=True)
            (STUDY/'condition_screen.json').write_text(json.dumps(rows,indent=2))

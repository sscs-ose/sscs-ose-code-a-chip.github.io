import json
import numpy as np
from pilot import simulate
from widlar_cold import cold_deck
from widlar_pilot import STUDY

rows=[]
for method in ['gear','trap']:
    for g in [1e-15,1e-18]:
        for w in [None,.42]:
            name=f'widlar_numerical_{method}_g{g}_w{w}'
            deck=cold_deck(1e-6,w,g,max_step=1e-5).replace('method=gear',f'method={method}')
            folder=simulate(name,deck)
            d=np.loadtxt(folder/'cold.dat',skiprows=1)
            good=(d[:,2]>=1.16009189*.95)&(d[:,2]<=1.16009189*1.05)&(d[:,5]>=1.7)
            outside=np.flatnonzero(~good)
            start=int(outside[-1]+1) if len(outside) else 0
            ready=float(d[start,0]) if start<len(d) and d[-1,0]-d[start,0]>=.002 else None
            row={'name':name,'method':method,'gmin_S':g,'startup_width_um':w,'max_step_s':1e-5,'final_b_V':float(d[-1,2]),'ready_time_s':ready,'contract':'b within +/-5% of 1.16009189 V with VDD>=1.7 V, through end of run for at least 2 ms','final_source_A':float(-d[-1,4])}
            rows.append(row); print(json.dumps(row),flush=True)
            (STUDY/'numerical_checks.json').write_text(json.dumps(rows,indent=2))

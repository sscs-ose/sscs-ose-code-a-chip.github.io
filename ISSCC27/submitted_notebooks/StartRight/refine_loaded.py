import json
import numpy as np
from pilot import simulate
from loaded_startup import loaded_deck,LOAD_STUDY
base=json.loads((LOAD_STUDY/'loaded_results.json').read_text())
target=base['contract']['target_A']
rows=[]
for w in [.42,1.0]:
    for ramp in [1e-6,1e-3]:
        deck=loaded_deck(w,1e5,ramp).replace('0 10u','0 1u').replace('reltol=1e-6','reltol=1e-7')
        folder=simulate(f'loaded_refined_w{w}_ramp{ramp}',deck,compatibility='hsa',solver='klu',threads=1)
        d=np.loadtxt(folder/'cold.dat',skiprows=1)
        good=(abs(d[:,7]-target)<=.05*target)&(d[:,6]>=.3)&(d[:,5]>=1.7)
        outside=np.flatnonzero(~good);first=int(outside[-1]+1) if len(outside) else 0
        ready=float(d[first,0]) if first<len(d) and d[-1,0]-d[first,0]>=.002 else None
        assert ready is not None and ready<=ramp+1e-6+.001
        energy=float(np.trapezoid(-d[:first+1,4]*d[:first+1,5],d[:first+1,0]))
        original=next(r for r in base['cases'] if r['kind']=='cold' and r['resistance_ohm']==1e5 and r['startup_width_um']==w and r['ramp_s']==ramp)
        row={'name':folder.name,'width_um':w,'ramp_s':ramp,'ready_s':ready,'energy_J':energy,'ready_relative_change':ready/original['ready_time_s']-1,'energy_relative_change':energy/original['source_energy_to_ready_J']-1,'output_relative_change':float(d[-1,7]/original['final_output_A']-1),'max_step_s':1e-6,'reltol':1e-7}
        rows.append(row);print(json.dumps(row),flush=True)
        (LOAD_STUDY/'refinement.json').write_text(json.dumps(rows,indent=2))

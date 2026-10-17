import json
import numpy as np
from pilot import OUT
from loaded_startup import LOAD_STUDY
from measurements import measure_loaded

# An independent analytic settling case validates the event/energy measurement.
t=np.linspace(0,.01,101);tau=.001;target=1e-6
fixture=np.zeros((len(t),8));fixture[:,0]=t;fixture[:,4]=-1e-3;fixture[:,5]=1.8;fixture[:,6]=1;fixture[:,7]=target*(1-np.exp(-t/tau))
a=measure_loaded(fixture,target,.004)
expected=-tau*np.log(.05)
assert abs(a['ready_time_s']-expected)<2e-6
assert abs(a['source_energy_to_ready_J']-1.8e-3*a['ready_time_s'])<1e-15
fixture[:,7]=0
assert measure_loaded(fixture,target,.004)['source_energy_to_ready_J'] is None

base=json.loads((LOAD_STUDY/'loaded_results.json').read_text());target=base['contract']['target_A']
rows=[]
for original in base['cases']:
    if original['kind']!='cold':continue
    d=np.loadtxt(OUT/original['name']/'cold.dat',skiprows=1)
    rows.append({'name':original['name'],'resistance_ohm':original['resistance_ohm'],'width_um':original['startup_width_um'],'ramp_s':original['ramp_s'],**measure_loaded(d,target,original['deadline_s'])})
refined=[]
for original in json.loads((LOAD_STUDY/'refinement.json').read_text()):
    d=np.loadtxt(OUT/original['name']/'cold.dat',skiprows=1)
    metric=measure_loaded(d,target,original['ramp_s']+1e-6+.001)
    coarse=next(r for r in rows if r['resistance_ohm']==1e5 and r['width_um']==original['width_um'] and r['ramp_s']==original['ramp_s'])
    refined.append({'name':original['name'],'width_um':original['width_um'],'ramp_s':original['ramp_s'],**metric,'energy_relative_change':metric['source_energy_to_ready_J']/coarse['source_energy_to_ready_J']-1,'ready_relative_change':metric['ready_time_s']/coarse['ready_time_s']-1})
assert all(r['meets_contract']==(r['width_um'] is not None) for r in rows)
assert max(abs(r['energy_relative_change']) for r in refined)<.01
assert max(abs(r['ready_relative_change']) for r in refined)<.005
result={'analytic_settling_event_error_s':a['ready_time_s']-expected,'contract':base['contract'],'cases':rows,'refined':refined,'limits':'Finite sampled data and interpolation; source work includes the entire circuit. Failed cases have no energy-to-readiness value.'}
(LOAD_STUDY/'measured_results.json').write_text(json.dumps(result,indent=2))
print('Analytic event error s:',result['analytic_settling_event_error_s'])
print('Working cases:',sum(r['meets_contract'] for r in rows),'/',len(rows))
print(json.dumps(refined,indent=2))


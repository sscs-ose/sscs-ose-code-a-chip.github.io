import json
import numpy as np
from pilot import simulate
from loaded_startup import loaded_deck,LOAD_STUDY
from measurements import measure_loaded
baseline=json.loads((LOAD_STUDY/'loaded_results.json').read_text())['contract']['target_A']
rows=[]
for low in [0,.6,1.2]:
    for duration in [1e-6,.001]:
        for width in [.42,1.0]:
            drop=.002;edge=1e-6;recovery=drop+edge+duration;stop=recovery+.003
            deck=loaded_deck(width)
            lines=deck.splitlines()
            lines=[f'VDD vdd 0 PWL(0 0 1u 0 2u 1.8 {drop} 1.8 {drop+edge} {low} {recovery} {low} {recovery+edge} 1.8 {stop} 1.8)' if l.startswith('VDD ') else l for l in lines]
            lines=[f'tran 1u {stop} 0 1u' if l.startswith('tran ') else l for l in lines]
            name=f'recovery_v{low}_hold{duration}_w{width}'
            folder=simulate(name,'\n'.join(lines)+'\n',compatibility='hsa',solver='klu',threads=1)
            d=np.loadtxt(folder/'cold.dat',skiprows=1)
            pre=d[np.argmin(abs(d[:,0]-(drop-1e-4)))]
            assert abs(pre[7]/baseline-1)<.05
            segment=d[d[:,0]>=recovery-1e-12].copy();segment[:,0]-=recovery
            metric=measure_loaded(segment,baseline,.001001)
            metric.pop('source_energy_to_ready_J',None)
            row={'name':name,'low_supply_V':low,'dip_hold_s':duration,'startup_width_um':width,'pre_dip_output_A':float(pre[7]),'time_origin':'beginning of the recovery ramp','energy_not_reported':'Stored capacitor energy is not accounted for as a recovery-energy comparison.',**metric}
            rows.append(row);print(low,duration,width,row['meets_contract'],flush=True)
            (LOAD_STUDY/'recovery.json').write_text(json.dumps(rows,indent=2))

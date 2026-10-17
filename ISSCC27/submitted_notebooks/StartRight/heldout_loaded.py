import datetime,json
import numpy as np
from pilot import simulate
from loaded_startup import loaded_deck,LOAD_STUDY
from measurements import measure_loaded
record={'declared_before_execution_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Additional unchanged-design tests at 10 and 60 C, 330 kohm load, 100 us ramp and GMIN 0.1 fS. Targets are condition-specific intended steady operating points, not PVT accuracy claims.','cases':[]}
(LOAD_STUDY/'heldout.json').write_text(json.dumps(record,indent=2))
for temp in [10,60]:
    def condition(deck):return deck.replace('.temp 27',f'.temp {temp}')
    folder=simulate(f'heldout_op_{temp}',condition(loaded_deck(resistance=330000,ramp=.0001,op=True,gmin=1e-16)),compatibility='hsa',solver='klu',threads=1)
    d=np.loadtxt(folder/'op.dat',skiprows=1);target=float(d[7])
    assert target>1e-8 and 'Transient op started' not in (folder/'ngspice.log').read_text()
    for width in [.42,1.0]:
        folder=simulate(f'heldout_cold_{temp}_w{width}',condition(loaded_deck(width,330000,.0001,gmin=1e-16)),compatibility='hsa',solver='klu',threads=1)
        d=np.loadtxt(folder/'cold.dat',skiprows=1)
        row={'name':folder.name,'temperature_C':temp,'startup_width_um':width,**measure_loaded(d,target,.001101)}
        record['cases'].append(row);print(temp,width,row['meets_contract'],flush=True)
        (LOAD_STUDY/'heldout.json').write_text(json.dumps(record,indent=2))

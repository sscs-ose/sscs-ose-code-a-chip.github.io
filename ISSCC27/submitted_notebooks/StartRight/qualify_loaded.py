"""Reach each condition's intended state; this is not a precision-current PVT specification."""
import json
import numpy as np
from pilot import simulate
from loaded_startup import loaded_deck,LOAD_STUDY
from measurements import measure_loaded
rows=[]
for corner in ['tt','ff','ss','sf','fs']:
    for temp in [-20,27,85]:
        def condition(deck):return deck.replace('__tt.corner.spice',f'__{corner}.corner.spice').replace('.temp 27',f'.temp {temp}')
        folder=simulate(f'qualify_op_{corner}_{temp}',condition(loaded_deck(op=True)),compatibility='hsa',solver='klu',threads=1)
        d=np.loadtxt(folder/'op.dat',skiprows=1);target=float(d[7])
        assert target>1e-8 and d[2]>.5 and d[6]>.3
        assert 'Transient op started' not in (folder/'ngspice.log').read_text()
        for width in [None,.42,1.0]:
            folder=simulate(f'qualify_cold_{corner}_{temp}_w{width}',condition(loaded_deck(width)),compatibility='hsa',solver='klu',threads=1)
            d=np.loadtxt(folder/'cold.dat',skiprows=1)
            result={'name':folder.name,'corner':corner,'temperature_C':temp,'startup_width_um':width,'target_output_A':target,'final_output_A':float(d[-1,7]),'final_bias_V':float(d[-1,2]),**measure_loaded(d,target,.001002)}
            rows.append(result)
            print(corner,temp,width,result['meets_contract'],flush=True)
            (LOAD_STUDY/'pvt_qualification.json').write_text(json.dumps({'scope':'Five corners at -20,27,85 C; target for each condition is its intended high-state operating point, computed before the cold start. This does not claim constant current across PVT.','cases':rows},indent=2))

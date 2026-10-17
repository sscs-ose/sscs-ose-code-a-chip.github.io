"""Repeat the matched slow-ramp sizing case on the current platform."""
from pathlib import Path
import hashlib,importlib.metadata,json,platform,sys
import numpy as np
from pilot import HERE,simulate
from loaded_startup import loaded_deck
from measurements import measure_loaded


def main():
    short=json.loads((HERE/'short_reproduction.json').read_text())
    assert short['status']=='passed'
    for name,digest in short['source_files'].items():
        assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==digest,name
    target=next(r['loaded_test']['nominal_target_A'] for r in short['runs'] if r['circuit']=='inverse_widlar' and r['parameters']['startup_width_um']==.42)
    cases=[]
    for width in [.42,1.0]:
        deck=loaded_deck(width,1e5,1e-3,gmin=1e-15).replace('reltol=1e-6','reltol=1e-7').replace('0 10u','0 1u')
        folder=simulate(f'portability_slow_width{width}',deck,compatibility='hsa',solver='klu',threads=1)
        data=np.loadtxt(folder/'cold.dat',skiprows=1)
        result={'width_um':width,'ramp_s':1e-3,'load_resistance_ohm':1e5,'maximum_step_s':1e-6,'reltol':1e-7,**measure_loaded(data,target,.002001)}
        assert result['meets_contract'],result
        cases.append(result)
        print('Matched slow-ramp width',width,':',result['source_energy_to_ready_J'],'J',flush=True)
    ratio=cases[1]['source_energy_to_ready_J']/cases[0]['source_energy_to_ready_J']-1
    record={'status':'passed','platform':platform.platform(),'python':sys.version.split()[0],'scope':'Fresh matched slow-ramp simulations after the five-case fresh short run. Both sizes use the same intended current target and contract. This is schematic evidence on the recorded platform.','short_runs':short['runs'],'sizing_cases':cases,'larger_width_energy_increase_fraction':ratio,'packages':{name:importlib.metadata.version(name) for name in ['numpy','matplotlib','nbclient','nbformat','ipykernel']},'numeric_source_hashes':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ['pilot.py','widlar_pilot.py','widlar_confirm.py','loaded_startup.py','measurements.py','startright.py','circuits.py']}}
    output=HERE/'results/reproduction';output.mkdir(exist_ok=True)
    (output/'portability_measurements.json').write_text(json.dumps(record,indent=2),encoding='utf8')
    print('PASS: both working sizes; wider-device energy change:',100*ratio,'percent',flush=True)

if __name__=='__main__':main()

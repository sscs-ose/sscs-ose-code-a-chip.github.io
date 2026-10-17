"""Fresh simulations through the shared verifier. No saved results are read."""
from pathlib import Path
import hashlib,json,platform,sys
import numpy as np
from pilot import PDK,EXE,HERE
from startright import verify_models,verify_case,verify_circuit
from circuits import CIRCUITS


def main():
    assert (HERE/'.startright_tools.json').exists(),'Run bootstrap.py first.'
    assert PDK.resolve().is_relative_to((HERE/'.cache').resolve())
    if sys.platform=='win32':assert EXE.resolve().is_relative_to((HERE/'.cache').resolve())
    records=[]
    for width,gmin,count,passes in [(None,1e-12,1,False),(None,1e-15,3,False),(.42,1e-15,1,True)]:
        result=verify_case(width,gmin)
        assert result['status']=='completed',result
        assert len(result['candidate_operating_points'])==count,result
        assert result['loaded_test']['meets_contract']==passes,result
        records.append(result)
        print('Original circuit:',width,gmin,result['startup_verdict'],flush=True)
    for circuit in CIRCUITS.values():
        result=verify_circuit(circuit)
        assert result['status']=='completed' and len(result['candidate_operating_points'])==1,result
        assert result['loaded_test']['meets_contract'],result
        records.append(result)
        print(circuit.name,result['startup_verdict'],flush=True)
    source_names=['bootstrap.py','pilot.py','widlar_pilot.py','widlar_confirm.py','loaded_startup.py','measurements.py','startright.py','circuits.py','reproduce_short.py','dependency_manifest.json']
    manifest={'status':'passed','scope':'Fresh nominal simulations with the shared verifier on this host. Dependencies are checksum-verified local files; inspect bootstrap download counts for download/cache status. No saved simulation data read. No independent OS or simulator validation.','python':sys.version.split()[0],'isolated_python':sys.prefix!=sys.base_prefix,'numpy':np.__version__,'platform':platform.platform(),'source':verify_models(),'runs':records,'source_files':{f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in source_names}}
    (HERE/'short_reproduction.json').write_text(json.dumps(manifest,indent=2))
    print('PASS: all three circuit families, including original failure/pass controls.',flush=True)

if __name__=='__main__':main()

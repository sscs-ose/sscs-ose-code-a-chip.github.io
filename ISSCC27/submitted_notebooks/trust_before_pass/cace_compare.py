"""Re-evaluate exported scalars with an existing pinned CACE checkout.

python cace_compare.py /path/to/cace
CACE's normal Python dependencies must already be present. This does not run
the CACE CLI, install a PDK, or modify CACE. The saved baseline is not overwritten.
"""
import hashlib
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parent
if len(sys.argv)!=2: raise SystemExit(__doc__)
checkout=Path(sys.argv[1]).resolve()
baseline=json.loads((root/'data/cace_baseline.json').read_text())
source=checkout/'cace/parameter/parameter.py'
if hashlib.sha256(source.read_bytes()).hexdigest()!=baseline['parameter_source_sha256']:
    raise SystemExit('CACE evaluator source differs from pinned baseline')
sys.path.insert(0,str(checkout))
from cace.parameter.parameter import NamedResult,ResultType
from cace.parameter.parameter_ngspice import ParameterNgspice
from cace.common.custom_semaphore import CustomSemaphore
for b in baseline['results']:
    spec={'minimum':{'value':.5},'maximum':{'value':2}}
    p=ParameterNgspice(pname='startup_time',config={},param={'name':'startup_time','tool':'ngspice',
        'unit':'ms','spec':{'value':spec}},datasheet={},pdk='sky130A',paths={},
        runtime_options={'sequential':True},run_dir=str(root),max_jobs=1,jobs_sem=CustomSemaphore(1))
    p.add_result(NamedResult('value'));p.result_type=ResultType.SUCCESS
    p.get_result('value').values=[b['exported_startup_s']];p.evaluate_result()
    assert p.result_type.name==b['cace_status'], b['run_id']
    assert p.get_result('value').status==b['subspec_status'], b['run_id']
    print(b['run_id'],p.result_type.name)
print('Pinned evaluator comparison reproduced; not an end-to-end CACE test.')

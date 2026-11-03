"""Run staged rejection paths without replacing a live measured helper."""
from pathlib import Path
import importlib.util
import json
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
CASE=ROOT.parents[1]/'CodeAChip_Submission/ISSCC27/submitted_notebooks/ChipNebula_CPU'
sys.path[:0]=[str(CASE/'runtime/src'),str(CASE/'scripts')]
from classify_study_failures import classify,read_reports
from study_protocol import BASELINE,write_json

spec=importlib.util.spec_from_file_location('staged_evaluation',Path(__file__).parent/'evaluate_study_physical.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def forbidden(*args):raise AssertionError('Rejected engineering report invoked workload measurement')
module.checked=forbidden


def run():
    for mode in ('drc','failed-task','malformed-native','nonfinite-raw'):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            physical={'physical_qualified':True,'configuration':BASELINE,'task_state':'satisfied',
                      'manifest':{'period_ps':10526},'physical_wall_seconds':1.,'failure_classes':[]}
            native={'detailed_routing_violations':0,'drc_violations':1 if mode=='drc' else 0,
                    'lvs':'matched','functional_simulation':'passed'}
            raw={'finish__timing__setup__ws':.1,'finish__timing__hold__ws':.1,
                 'finish__design__instance__area__stdcell':100,'finish__design__die__area':200,
                 **{'finish__timing__drv__'+key:0 for key in ('max_slew','max_cap','max_fanout')}}
            if mode=='failed-task':physical['task_state']='failed'
            write_json(root/'summary.json',physical);write_json(root/'evidence/summary.json',native)
            path=root/'evidence/orfs-work/logs/test/6_report.json';write_json(path,raw)
            if mode=='malformed-native':(root/'evidence/summary.json').write_text('{"incomplete":')
            if mode=='nonfinite-raw':path.write_text('{"bad":NaN}')
            result=module.evaluate(root)
            assert not result['physical_qualified'] and not result['rank_eligible']
            assert not result['postprocessing_commands'] and not result['energy_j'] and 'score' not in result
    for label,path in (('baseline',ROOT/'baseline/mhz95-run03'),('first-candidate',ROOT/'ppa/W1-3/candidates/01/physical')):
        physical=json.loads((path/'summary.json').read_text());raw,native,errors=read_reports(path/'evidence')
        assert not errors
        assert classify(physical,raw,native)==([] if label=='baseline' else ['electrical'])
    print('STAGED_MEASUREMENT_PASS: contradictory DRC/task status, corrupt/nonfinite reports rejected; actual baseline/candidate classification unchanged; zero EDA/model calls')


if __name__=='__main__':run()

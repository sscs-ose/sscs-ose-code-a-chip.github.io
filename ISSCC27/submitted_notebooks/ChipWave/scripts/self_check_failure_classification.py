"""Reject contradictory passing summaries and retain the failure class W0 consumes."""
from copy import deepcopy
import tempfile
from pathlib import Path
from classify_study_failures import classify,read_reports
from study_protocol import BASELINE,rule_candidate


def run():
    physical={'physical_qualified':True,'failure_classes':[],'frozen_inputs_unchanged':True,'task_state':'satisfied'}
    native={'detailed_routing_violations':0,'drc_violations':0,'lvs':'matched','functional_simulation':'passed'}
    raw={'finish__timing__setup__ws':.1,'finish__timing__hold__ws':.1,
         'finish__design__instance__area__stdcell':100,'finish__design__die__area':200,
         **{'finish__timing__drv__'+key:0 for key in ('max_slew','max_cap','max_fanout')}}
    assert classify(physical,raw,native)==[]
    assert 'physical_execution' in classify(dict(physical,task_state='failed'),raw,native)
    for field,label in (('detailed_routing_violations','routing'),('drc_violations','drc'),('lvs','lvs')):
        changed=dict(native);changed[field]='mismatched' if field=='lvs' else 1
        assert label in classify(physical,raw,changed)
    for key,label,value in (('finish__timing__setup__ws','timing',-.1),
                            ('finish__timing__hold__ws','incomplete_physical_metrics',None),
                            ('finish__timing__drv__max_slew','electrical',1),
                            ('finish__timing__drv__max_cap','incomplete_physical_metrics',float('nan'))):
        changed=dict(raw);changed[key]=value
        assert label in classify(physical,changed,native)
    assert 'source_or_constraint_changed' in classify(dict(physical,frozen_inputs_unchanged=False),raw,native)
    assert classify({'physical_qualified':False,'failure_classes':['physical_execution']},{},{})==['physical_execution']
    row={'configuration':BASELINE,'rank_eligible':False,'failure_classes':classify(physical,raw,dict(native,drc_violations=1))}
    candidate,reason=rule_candidate([row])
    assert candidate['utilization']==30 and reason['rule']=='routing_or_drc_failure'
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary);path=root/'orfs-work/logs/test/6_report.json';path.parent.mkdir(parents=True)
        for bad in ('{"incomplete":','[1,2]','{"bad":NaN}'):
            path.write_text(bad)
            result,summary,errors=read_reports(root)
            assert result=={} and errors==['invalid_physical_report']
        path.write_text('{}');(root/'physical-report.json').write_text('{"raw_flow_summary":{"drc_violations":2}}')
        result,summary,errors=read_reports(root)
        assert not errors and summary['drc_violations']==2
    print('PHYSICAL_FAILURE_CLASSIFICATION_PASS: route/DRC, timing, electrical, LVS, malformed metrics and frozen inputs')


if __name__=='__main__':run()

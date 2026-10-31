"""Pilot outcomes, missing data and duplicates cannot silently bypass stop rules."""
import copy
import json
from pathlib import Path

from capacity_protocol import MODELS,protocol
from decide_capacity_pilots import decide
from study_protocol import write_json


def check():
    jobs=protocol()['pilot_jobs']
    rows=[dict(job=job,model=job['model'],reasoning='high',terminal=True,
        measurement_valid=True,status='evaluated',frontend_status='native_exit',
        functional_pass=True,gds_pass=False,final_score=0) for job in jobs]
    assert decide(rows,jobs)['reason']=='all_luna_functional_pass'
    luna=[row for row in rows if row['model']==MODELS['luna']]
    for row in luna:row['functional_pass']=False
    assert decide(rows,jobs)['reason']=='all_luna_functional_fail'
    luna[0]['functional_pass']=True
    assert decide(rows,jobs)['formal_launch_allowed']
    for key,value in [('measurement_valid',False),('terminal',False),('frontend_status','infrastructure_error')]:
        invalid=copy.deepcopy(rows);invalid[0][key]=value
        assert not decide(invalid,jobs)['formal_launch_allowed']
    for invalid in (rows[:-1],[rows[0],*rows[:-1]]):
        try:decide(invalid,jobs)
        except ValueError:pass
        else:raise AssertionError('Missing/duplicate pilot accepted')
    report=dict(passed=True,model_calls=0,physical_runs=0,
        checks=['all-pass and all-fail stop','mixed valid outcomes permit formal launch',
                'missing, duplicate, invalid, unfinished and infrastructure outcomes cannot bypass gate'])
    write_json(Path(__file__).resolve().parents[1]/'checks/pilot-decision.json',report)
    return report


if __name__=='__main__':print(json.dumps(check()))

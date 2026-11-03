"""Check distinct failure diagnoses and whole-interval storage rejection.
SPDX-License-Identifier: Apache-2.0
"""
import numpy as np
from application_circuit import generate_application,measure_application
from applicability_evidence import audit,load_vectors

def checks(record=None):
    record=record or audit()
    for row in record['cases']:
        if row['kind']!='application':continue
        diagnosis=row['result']['diagnosis']
        if row['history']=='cold_storage':assert diagnosis=='not_exercised_cold_start'
        elif row['history']=='hot_shallow_reset':assert diagnosis=='functional_requirement_missed'
        else:assert diagnosis=='requirement_met'
    row=next(r for r in record['cases'] if r['group']=='ripple' and r['history']=='triangle' and r['variant']=='digital_guard')
    d=load_vectors(row);_,args=generate_application('triangle','digital_guard',row['max_step_s']);index=int(np.argmin(abs(d[:,0]-.027)))
    q=d.copy();q[index,1]=0;r=measure_application(q,args,'triangle')
    assert r['diagnosis']=='functional_requirement_missed' and not r['normal_storage_pass'] and r['reset_inactive_pass']
    q=d.copy();q[index,2]=0;r=measure_application(q,args,'triangle')
    assert r['diagnosis']=='functional_requirement_missed' and r['normal_storage_pass'] and not r['reset_inactive_pass']
    try:measure_application(d[:-10],args,'triangle')
    except ValueError:pass
    else:raise AssertionError('Incomplete observation accepted')
    assert record['choices']==dict(bounded='digital_guard',hot=None,cold=None)
    return dict(known_failure_diagnoses=True,storage_glitch_rejected=True,reset_glitch_separate=True,incomplete_observation_rejected=True,expanded_requirements_abstain=True,
                scope='Software negative fixtures corrupt copies of an actual stored trace. They are not additional SPICE acquisitions.')
if __name__=='__main__':print(checks())

"""Reject incomplete data and missing prior-state coverage using measured fixtures.
SPDX-License-Identifier: Apache-2.0
"""
import copy
from reference_circuit import generate,measure_application
from reference_evidence import load_vectors,policy_evidence
from guard_policy import choose

def checks(record):
    row=next(r for r in record['cases'] if r['id']=='primary/hot_shallow_reference_supervisor')
    d=load_vectors(row);_,args=generate(row['case'],row['variant'],row['max_step_s'])
    rejected=0
    for fixture in [d[:-1],d[:,:-1]]:
        try:measure_application(fixture,args,row['case'],row['variant'])
        except ValueError:rejected+=1
    assert rejected==2
    missing_prior=d.copy();before=.025-1e-7
    missing_prior[(d[:,0]>=before-6e-6)&(d[:,0]<=before+1e-7),1]=0.
    q=measure_application(missing_prior,args,row['case'],row['variant'])
    assert q['diagnosis']=='not_exercised_prior_state' and not q['qualified']
    evidence=copy.deepcopy(policy_evidence(record))
    failed=next(r for r in evidence['rows'] if r['condition']=='nominal_shallow' and r['variant']=='original')
    assert not failed['functional_requirement_met'];failed['source_work_delivered_J']=0.
    assert choose(evidence,required=['nominal_shallow'],anchor='nominal_shallow')!='original'
    assert choose(evidence,required=['nominal_storage','unmeasured_short_zero'],anchor='nominal_storage') is None
    return ['Truncated and missing-probe acquisitions rejected',
            'Completed restoration without the measured prior state does not qualify',
            'Cheap failed candidates excluded and missing evidence causes abstention']

if __name__=='__main__':
    from reference_evidence import audit
    print(checks(audit()))

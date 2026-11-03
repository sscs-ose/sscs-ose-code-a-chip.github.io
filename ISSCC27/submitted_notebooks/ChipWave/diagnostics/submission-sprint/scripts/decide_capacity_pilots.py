"""Apply the preregistered pilot stop rule; never adjust tasks or budgets."""
import json

from capacity_admission import admit_trial
from capacity_integration_physical import ROOT
from capacity_protocol import MODELS
from study_protocol import digest,write_json


def decide(rows,jobs):
    expected={job['id']:job for job in jobs}
    if len(expected)!=8 or len(rows)!=8 or {row['job']['id'] for row in rows}!=set(expected):
        raise ValueError('Exactly eight unique preregistered pilot results are required')
    errors=[];luna=[]
    for row in rows:
        job=expected[row['job']['id']]
        if row['job']!=job or row.get('model')!=job['model'] or row.get('reasoning')!='high':
            raise ValueError('Pilot identity/model/recipe changed')
        if row.get('terminal') is not True:errors.append(job['id']+': unfinished')
        if row.get('measurement_valid') is not True:errors.append(job['id']+': invalid measurement')
        if row.get('status')!='evaluated' or row.get('frontend_status')=='infrastructure_error':
            errors.append(job['id']+': infrastructure or collection error')
        if job['model']==MODELS['luna']:luna.append(row.get('functional_pass') is True)
    if len(luna)!=4:raise ValueError('Expected four light-model pilots')
    stop=all(luna) or not any(luna)
    return dict(formal_launch_allowed=not errors and not stop,stop_rule_triggered=stop,
        luna_functional_successes=sum(luna),luna_pilots=4,errors=errors,
        reason=('pilot_measurement_or_infrastructure_invalid' if errors else
                'all_luna_functional_pass' if all(luna) else
                'all_luna_functional_fail' if not any(luna) else 'preregistered_pilot_gate_passed'),
        policy='No task/model/budget changes or replacement runs; all physical outcomes remain reported')


def finalize():
    if (ROOT/'pilot-decision.json').exists():raise ValueError('Existing pilot decision is immutable')
    protocol=json.loads((ROOT/'protocol.json').read_text());rows=[];evidence={}
    for job in protocol['pilot_jobs']:
        assert admit_trial('pilot',job['id'])==job
        path=ROOT/'trials/pilot'/job['id']/'result.json'
        rows.append(json.loads(path.read_text()));evidence[str(path.relative_to(ROOT))]=digest(path)
    decision=decide(rows,protocol['pilot_jobs'])
    decision.update(pilot_evidence=evidence,campaign_sha256=digest(ROOT/'campaign-freeze.json'),
        outcomes=[{key:row.get(key) for key in ('job','functional_pass','gds_pass','joint_pass',
            'constraint_pass','final_score','measurement_valid','status','usage','physical_attempts')} for row in rows])
    write_json(ROOT/'pilot-decision.json',decision)
    protocol.update(pilot_launch_allowed=False,formal_launch_allowed=decision['formal_launch_allowed'],
        frozen_for_formal=decision['formal_launch_allowed'],
        phase='formal_ready' if decision['formal_launch_allowed'] else 'stopped_after_pilots')
    if decision['formal_launch_allowed']:
        write_json(ROOT/'formal-freeze.json',dict(campaign_sha256=decision['campaign_sha256'],
            pilot_decision_sha256=digest(ROOT/'pilot-decision.json')))
    write_json(ROOT/'protocol.json',protocol)
    return decision


if __name__=='__main__':print(json.dumps(finalize()))

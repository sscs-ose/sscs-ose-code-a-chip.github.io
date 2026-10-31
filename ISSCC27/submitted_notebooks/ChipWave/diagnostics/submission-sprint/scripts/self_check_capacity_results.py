"""Synthetic result accounting tests, never counted as study observations."""
import copy
import json
import tempfile
from pathlib import Path

from capacity_protocol import CHECKPOINTS,protocol
from capacity_results import analyze,invocation_costs,transitions
from capacity_notebook_cells import cells
from study_protocol import write_json


def reject(call):
    try:call()
    except ValueError:return
    raise AssertionError('Invalid result accepted')


def trial(job):
    point=dict(functional_pass=True,gds_pass=True,joint_pass=True,constraint_pass=True,
        final_score=50,measurement_valid=True,selection='latest_checkpoint',failure_reasons=[])
    return dict(job=job,model=job['model'],reasoning='high',terminal=True,status='evaluated',
        frontend_status='native_exit',**{k:v for k,v in point.items() if k!='selection'},
        usage=dict(measurement_valid=True,actual_tokens=1000,overshoot_tokens=0,cached_input_tokens=400),
        physical_attempts=[dict(identity='first'),dict(identity='second')],
        physical_diagnostics=[dict(point,physical_attempt=n,selection='physical_attempt_diagnostic') for n in ('first','second')],
        checkpoints=[dict(point,budget=b) for b in CHECKPOINTS])


def check():
    assert transitions({})=='unresolved_measurement'
    assert transitions(dict(physical_attempts=[]))=='fewer_than_two_attempts'
    with tempfile.TemporaryDirectory(prefix='capacity-results-test-') as temporary:
        root=Path(temporary);rules=protocol();write_json(root/'protocol.json',rules)
        pending=analyze(root)
        assert pending['planned']==84 and pending['terminal']==0 and not pending['complete']
        assert all(r['full_denominator'] is None for r in pending['cells'])
        assert all(r['equal_task_means'] is None for r in pending['checkpoints'])
        reject(lambda:cells(root))
        assert any('0 of 84' in c.source for c in cells(root,draft=True))
        for job in rules['formal_jobs']:
            record=trial(job)
            if job['model_group']=='luna' and job['workflow']=='C0' and job['task']=='A1':
                for target in [record,*record['checkpoints']]:
                    target.update(functional_pass=False,joint_pass=False,constraint_pass=False,final_score=0)
                # Old physical success remains diagnostic only.
                record['physical_diagnostics'][1].update(functional_pass=False,joint_pass=False,constraint_pass=False,final_score=0)
            write_json(root/'trials/formal'/job['id']/'result.json',record)
        results=analyze(root)
        assert results['complete'] and results['terminal']==84
        assert any('37.50' in c.source for c in cells(root))
        group=next(r for r in results['workflows'] if r['model']=='gpt-6-luna' and r['workflow']=='C0')
        assert group['equal_task_means']['average_score']==37.5
        assert group['equal_task_means']['gds_pass_rate']==1
        cell=next(r for r in results['cells'] if r['model']=='gpt-6-luna' and r['workflow']=='C0' and r['task']=='A1')
        assert cell['full_denominator']['conditional_gds_rate'] is None
        assert cell['physical_transitions']=={'qualified_to_unqualified':3}
        assert cell['costs']['active_frontend_seconds']['missing']==3
        assert cell['costs']['active_frontend_seconds']['total'] is None
        job=next(j for j in rules['formal_jobs'] if j['model_group']=='luna' and j['workflow']=='C3' and j['task']=='B2')
        path=root/'trials/formal'/job['id']/'result.json';original=json.loads(path.read_text())
        invalid=copy.deepcopy(original);invalid['measurement_valid']=False
        invalid['status']='measurement_or_infrastructure_invalid';invalid['usage']['measurement_valid']=False
        write_json(path,invalid)
        cell=next(r for r in analyze(root)['cells'] if r['model']=='gpt-6-luna' and r['workflow']=='C3' and r['task']=='B2')
        assert cell['n']==3 and cell['valid']==2 and cell['full_denominator']['average_score']==100/3
        assert cell['valid_samples']['average_score']==50
        broken=copy.deepcopy(original);broken['final_score']=99;write_json(path,broken)
        reject(lambda:analyze(root))
        broken=copy.deepcopy(original);broken['checkpoints'][-1]['selection']='physical_attempt_diagnostic';write_json(path,broken)
        reject(lambda:analyze(root))
        broken=copy.deepcopy(original);broken['model']='wrong-model';write_json(path,broken)
        reject(lambda:analyze(root))
        for target in ('usage','final'):
            broken=copy.deepcopy(original)
            (broken['usage'] if target=='usage' else broken['checkpoints'][-1])['measurement_valid']=False
            write_json(path,broken);reject(lambda:analyze(root))
        broken=copy.deepcopy(original);broken['physical_attempts'].append(dict(identity='third'));write_json(path,broken)
        reject(lambda:analyze(root))
        write_json(path,original)
        write_json(root/'trials/formal/unregistered/result.json',original)
        reject(lambda:analyze(root))
        runtime=root/'runtime'
        for index,(role,stage) in enumerate((('rtl','implementation'),('verify','verification'),('rtl','implementation')),1):
            folder=runtime/'invocations'/f'{index:04d}'
            write_json(folder/'request.json',dict(role=role,stage=stage))
            if index<3:write_json(folder/'result.json',dict(invocation_tokens=100,
                invocation_active_seconds=10,invocation_physical_seconds=30,reason='native_exit'))
        costs=invocation_costs(runtime)
        assert costs['call_count']==3 and costs['role_count']==2 and costs['role_switches']==2
        assert costs['repeated_stage_calls']==1 and costs['invocations'][-1]['tokens'] is None
    report=dict(passed=True,model_calls=0,physical_runs=0,synthetic=True,checks=[
        '84 planned slots retained; incomplete batches have no claimed rates',
        'equal-task mean and independent F/G with undefined conditional rate',
        'previous physical success never rescues final failure',
        'invalid measurement remains in full denominator; valid sample result separate',
        'missing costs remain unknown; role calls and repair proxies read actual receipts',
        'wrong identities, diagnostic substitution, third attempt and unregistered trials rejected',
        'valid trial cannot hide invalid usage or final measurement evidence'])
    write_json(Path(__file__).resolve().parents[1]/'checks/result-analysis.json',report)
    return report


if __name__=='__main__':print(json.dumps(check()))

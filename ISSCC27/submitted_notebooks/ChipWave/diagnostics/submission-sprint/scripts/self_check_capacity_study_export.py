"""Exercise complete roster export and restoration using disposable synthetic fixtures."""
import json
import tempfile
from pathlib import Path

from capacity_protocol import protocol
from capacity_results import analyze
from export_capacity_study import export
from restore_capacity_study import restore
from self_check_capacity_results import trial,reject
from study_protocol import digest,write_json


def check():
    with tempfile.TemporaryDirectory(prefix='capacity-study-export-') as temp:
        base=Path(temp);source=base/'source';source.mkdir();rules=protocol()
        write_json(source/'protocol.json',rules)
        write_json(source/'physical-ledger.json',dict(attempts=[dict(identity='failed-reference',
            category='reference_integration',status='failed',evidence='physical/failed-reference/qualification.json')]))
        write_json(source/'physical/failed-reference/qualification.json',dict(status='failed',qualified=False))
        for name,text in (('scripts/fixture.py','print("fixture")\n'),
                          ('task-packages/formal/A1/agent/spec/task.md','Synthetic task, not an experiment.\n'),
                          ('integration/A1/rtl/fixture.sv','module fixture; endmodule\n'),
                          ('private/auth.json','DO_NOT_EXPORT_THIS'),
                          ('integration/A1/qualification/obj/cache.log','DO_NOT_EXPORT_THIS')):
            path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
        reject(lambda:export(source,base/'not-complete'));assert not (base/'not-complete').exists()
        summary=export(source,base/'draft',draft=True)
        assert not summary['complete']
        assert not any('DO_NOT_EXPORT_THIS' in p.read_text() for p in (base/'draft').rglob('*') if p.is_file())
        restored=base/'restored';receipt=restore(base/'draft',restored)
        assert receipt['restored'] and not receipt['source_complete']
        assert digest(source/'scripts/fixture.py')==digest(restored/'scripts/fixture.py')
        assert not analyze(restored)['complete']
        reject(lambda:restore(base/'draft',restored))
        for category in ('pilot','formal'):
            for job in rules[category+'_jobs']:
                record=trial(job);record.update(physical_attempts=[],physical_diagnostics=[])
                for point in (record,*record['checkpoints']):
                    point.update(gds_pass=False,joint_pass=False,constraint_pass=False,final_score=0)
                write_json(source/'trials'/category/job['id']/'result.json',record)
        write_json(source/'checks/reference-calibration.json',dict(passed=True))
        write_json(source/'campaign-freeze.json',dict(qualified=True,files={'scripts/fixture.py':digest(source/'scripts/fixture.py')}))
        write_json(source/'pilot-decision.json',dict(formal_launch_allowed=True,stop_rule_triggered=False,
            campaign_sha256=digest(source/'campaign-freeze.json')))
        full=export(source,base/'complete');assert full['complete']
        restore(base/'complete',base/'full-restored')
        result=analyze(base/'full-restored');assert result['complete'] and result['terminal']==84
        assert analyze(base/'full-restored','pilot')['terminal']==8
        assert all(r['equal_task_means']['average_score']==0 for r in result['workflows'])
        modified=base/'complete/scripts/fixture.py';modified.write_text('changed\n')
        reject(lambda:restore(base/'complete',base/'changed'))
        assert not (base/'changed').exists()
    report=dict(passed=True,synthetic=True,model_calls=0,physical_runs=0,checks=[
        'incomplete final export refused; explicit draft retains omissions',
        'private directories and compiler caches excluded',
        'terminal failed physical evidence restored',
        'all 84 formal and eight pilot fixture results survive restore with unchanged scores',
        'changed source storage and existing destinations rejected'])
    write_json(Path(__file__).resolve().parents[1]/'checks/study-export.json',report)
    return report


if __name__=='__main__':print(json.dumps(check()))

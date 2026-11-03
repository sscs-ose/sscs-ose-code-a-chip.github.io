"""Exercise native trial finalization and launch gates without model or EDA calls."""
import json
import tempfile
import os
import shutil
import fcntl
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

import capacity_admission as admission
import run_capacity_trial as trial
from capacity_meter import TokenLedger
from capacity_protocol import protocol
from study_protocol import digest,write_json
from capacity_grade import function


def rejected(call):
    try:call()
    except (ValueError,FileNotFoundError):return
    raise AssertionError('Invalid launch accepted')


# Inherited-debit failures have their own explicit ledger tests.
@patch('import_capacity_prior.validate_inherited', return_value={})
def check(_inherited):
    with tempfile.TemporaryDirectory(prefix='capacity-trial-check-') as temp:
        root=Path(temp);job=protocol()['pilot_jobs'][0]
        with patch.object(admission,'ROOT',root),patch.object(admission.subprocess,'check_output',return_value='sha256:fixture\n'):
            rejected(lambda:admission.admit_trial('pilot',job['id']))
            rules=protocol();rules['pilot_launch_allowed']=True
            write_json(root/'protocol.json',rules)
            source=root/'frozen-input';source.write_text('original')
            frozen=dict(schema_version=2,qualified=True,files={'frozen-input':digest(source)},
                external_files={},tool_paths={},container_images={'fixture-image':'sha256:fixture'},
                service_fingerprint=admission.service_fingerprint(),
                runtime_paths=admission.runtime_paths(),
                native_binary=str(Path(os.environ.get('CHIP_STUDY_CODEX_BINARY') or shutil.which('codex-real') or
                    Path.home()/'.codex/packages/standalone/current/bin/codex').resolve()),
                protocol={k:v for k,v in rules.items() if k not in
                    ('phase','pilot_launch_allowed','formal_launch_allowed','frozen_for_formal')})
            write_json(root/'campaign-freeze.json',frozen)
            assert admission.admit_trial('pilot',job['id'])==job
            with patch.object(admission.subprocess,'check_output',return_value='sha256:wrong-image\n'):
                rejected(lambda:admission.admit_trial('pilot',job['id']))
            with patch.object(admission,'service_fingerprint',return_value='changed'):
                rejected(lambda:admission.admit_trial('pilot',job['id']))
            external=root/'external-runtime';external.write_text('version-one')
            frozen['external_files']={str(external):digest(external)}
            write_json(root/'campaign-freeze.json',frozen)
            assert admission.admit_trial('pilot',job['id'])==job
            external.write_text('version-two')
            rejected(lambda:admission.admit_trial('pilot',job['id']))
            external.write_text('version-one')
            source.write_text('changed')
            rejected(lambda:admission.admit_trial('pilot',job['id']))
            source.write_text('original')
            formal=rules['formal_jobs'][0]
            rejected(lambda:admission.admit_trial('formal',formal['id']))
            rules['formal_launch_allowed']=True;write_json(root/'protocol.json',rules)
            write_json(root/'pilot-decision.json',dict(formal_launch_allowed=False,stop_rule_triggered=True))
            rejected(lambda:admission.admit_trial('formal',formal['id']))
            cfg=dict(record=str(root/'trials/pilot'/job['id']/'runtime'),
                project=str(root/'trials/pilot'/job['id']/'project'),model=job['model'],
                eda=dict(category='pilot',trial=job['id'],task=job['task']))
            cfg['workspace']=cfg['project']
            assert admission.validate_runtime(cfg)==job
            rejected(lambda:admission.validate_runtime(dict(cfg,limit=2_000_000)))
            rejected(lambda:admission.validate_runtime(dict(cfg,record=str(root/'reset'))))
        package=root/'task-packages/pilot'/job['task'];(package/'agent/spec').mkdir(parents=True)
        (package/'agent/spec/task.md').write_text('Synthetic pipeline fixture, not a design trial.\n')
        write_json(package/'agent/spec/scorecard.json',dict(reference={}))
        write_json(package/'package.json',dict(passed=True,frozen=True,calibrated=True,
            source_sha256={str(p.relative_to(package)):digest(p) for p in (package/'agent').rglob('*') if p.is_file()}))
        write_json(root/'physical-ledger.json',dict(attempts=[]))
        def native(config,prompt):
            record=Path(config['record']);ledger=TokenLedger()
            ledger.record('fixture','response-1',dict(input_tokens=40,cached_input_tokens=10,
                output_tokens=10,reasoning_output_tokens=5,total_tokens=50))
            write_json(record/'usage.json',ledger.state)
            control=dict(reason='native_exit',exit_code=0,measurement_valid=True,
                invocation_tokens=50,invocation_active_seconds=0,invocation_physical_seconds=0)
            write_json(record/'invocations/0001/request.json',dict(role=None,stage=None))
            write_json(record/'invocations/0001/result.json',control)
            return control,record/'stdout'
        # Real checkpoint child processes grade an empty, measured submission as zero.
        with patch.object(trial,'ROOT',root),patch.object(trial,'admit_trial',return_value=job),\
             patch.object(trial,'run_native',side_effect=native),\
             patch.object(trial,'private_context',side_effect=lambda root,name:root/'private'/name):
            scripts=root/'scripts';scripts.symlink_to(Path(__file__).resolve().parent,target_is_directory=True)
            with (root/'.trial-execution.lock').open('a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                try:trial.run('pilot',job['id'])
                except BlockingIOError:pass
                else:raise AssertionError('Concurrent trial admitted')
                assert not (root/'trials').exists()
            result=trial.run('pilot',job['id'])
            assert result['terminal'] and result['measurement_valid'] and result['final_score']==0
            assert result['usage']['actual_tokens']==50 and len(result['checkpoints'])==3
            assert result['monetary_cost']['value'] is None
            before=digest(root/'trials/pilot'/job['id']/'result.json')
            rejected(lambda:trial.run('pilot',job['id']))
            assert digest(root/'trials/pilot'/job['id']/'result.json')==before
            (root/'physical-ledger.json').unlink()
            try:trial.run('pilot','synthetic-finalization-failure')
            except FileNotFoundError:pass
            else:raise AssertionError('Missing external ledger was accepted')
            failure=json.loads((root/'trials/pilot/synthetic-finalization-failure/result.json').read_text())
            assert failure['terminal'] and failure['status']=='infrastructure_error' and failure['final_score']==0
        snapshot=root/'source';(snapshot/'rtl').mkdir(parents=True)
        (snapshot/'rtl/design.sv').write_text('module fixture;endmodule\n')
        output=root/'rejected-candidate'
        rejected_tool=SimpleNamespace(synthesis=lambda *args,**kwargs:dict(status='failed',
            evidence=str(output/'synthesis/rejected.json')))
        with patch('capacity_grade.Backends',return_value=rejected_tool):
            candidate=function(snapshot,'A1',output)
        assert candidate['evaluation_valid'] and not candidate['function']
        output=root/'bad-evaluator'
        def admitted(*args,**kwargs):
            canonical=output/'synthesis/synthesis-0001/admitted/design.sv';canonical.parent.mkdir(parents=True)
            canonical.write_text((snapshot/'rtl/design.sv').read_text())
            return dict(status='passed',evidence=str(output/'synthesis/result.json'))
        invalid_package=root/'invalid-package';write_json(invalid_package/'package.json',dict(task='B2',passed=True))
        with patch('capacity_grade.Backends',return_value=SimpleNamespace(synthesis=admitted)):
            invalid=function(snapshot,'A1',output,task_package=invalid_package)
        assert not invalid['evaluation_valid'] and not invalid['function']
    report=dict(passed=True,model_calls=0,physical_runs=0,checks=[
        'missing/changed qualification, runtime, model service and failed pilot gate rejected',
        'accounting reset and raised Token limit rejected',
        'concurrent trials rejected before creating any launch evidence',
        'measured empty source gets three real zero-score checkpoints',
        'terminal trial cannot restart or overwrite evidence',
        'finalization infrastructure failure retains terminal zero result',
        'candidate rejection stays valid; wrong hidden checker invalidates evaluation'])
    write_json(Path(__file__).resolve().parents[1]/'checks/trial-orchestration.json',report)
    return report


if __name__=='__main__':print(json.dumps(check()))

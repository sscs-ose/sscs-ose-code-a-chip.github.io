"""Run one preregistered, frozen trial; never retry or replace an existing trial."""
from __future__ import annotations

import argparse
import datetime
import json
import shutil
import subprocess
import sys
import time
import os
import platform
import fcntl
from pathlib import Path

from capacity_admission import admit_trial
from capacity_context import ContextPool
from capacity_graph import freeze
from capacity_integration_physical import ROOT
from capacity_meter import TokenLedger
from capacity_process import remaining,run_group
from capacity_protocol import CHECKPOINTS, GDS_GATES, CONSTRAINT_GATES, score
from capacity_runtime import run as run_native
from capacity_results import invocation_costs,observation
from capacity_accounting_replay import export as export_accounting, replay as replay_accounting
from study_portability import private_context
from study_protocol import digest,write_json
from write_capacity_workflows import BASE,write


def prepare(project,package,job):
    receipt=json.loads((package/'package.json').read_text())
    if not receipt['passed'] or not receipt['frozen'] or not receipt['calibrated']:
        raise ValueError('Unqualified task package')
    for name,sha in receipt['source_sha256'].items():
        if digest(package/name)!=sha:raise ValueError('Frozen task-package source changed')
    shutil.copytree(package/'agent',project)
    for name in ('rtl','configuration','tests','reports','build'):(project/name).mkdir(exist_ok=True)
    if job['workflow']!='C0':return freeze(project,job['workflow'],job['model'])
    write(project,'C0',job['model'])
    (project/'.gitignore').write_text('tools/.capacity-results/\nbuild/\n__pycache__/\n*.pyc\n')
    for args in (['init','-q'],['config','user.name','ChipNebula experiment'],
                 ['config','user.email','automation@chipnebula.invalid'],['add','.'],
                 ['commit','-qm','Freeze common native task inputs']):
        subprocess.run(['git',*args],cwd=project,check=True,capture_output=True)
    return None


def unavailable(budget,reason):
    result=score(dict(function=False,integration=False),dict.fromkeys(GDS_GATES,False),
                 dict.fromkeys(CONSTRAINT_GATES,False))
    return dict(result,budget=budget,measurement_valid=False,errors=[reason],snapshot_id=None)


def execution_validity(output,frontend_status):
    """Keep measured hardware outcomes separate from a valid matched execution."""
    errors=[]
    invocations=sorted((output/'runtime/invocations').glob('*'))
    if not invocations:errors.append('No native invocation receipts')
    for folder in invocations:
        try:
            control=json.loads((folder/'result.json').read_text())
            reason=control.get('reason')
            if control.get('measurement_valid') is not True:
                errors.append(folder.name+': invalid native measurement')
            if type(control.get('exit_code')) is not int:
                errors.append(folder.name+': missing or malformed exit status')
            if reason not in ('native_exit','token_budget','active_time_budget'):
                errors.append(folder.name+': unexpected native stop')
            elif reason=='native_exit' and control.get('exit_code')!=0:
                errors.append(folder.name+': unexpected native exit')
        except (OSError,ValueError,TypeError,AttributeError):
            errors.append(folder.name+': missing or malformed native receipt')
    if frontend_status=='infrastructure_error':errors.append('Frontend infrastructure error')
    path=output/'interventions.json';events=[];count=0
    if path.exists():
        try:
            events=json.loads(path.read_text())
            if not isinstance(events,list) or any(not isinstance(e,dict) or
                    not isinstance(e.get('reason'),str) or not e['reason'].strip() or
                    not isinstance(e.get('recorded_at'),str) or not e['recorded_at'].strip()
                    for e in events):
                raise ValueError('Invalid intervention record')
            count=len(events)
            if count:errors.append('Manual intervention during the scored session')
        except (OSError,ValueError,TypeError):
            count=None;errors.append('Malformed intervention record; count unknown')
    return dict(valid=not errors,manual_interventions=count,errors=errors)


def _run(category,identity):
    start=time.monotonic()
    job=admit_trial(category,identity)
    output=ROOT/'trials'/category/identity
    private=private_context(ROOT,'capacity-'+category+'-'+identity)
    if output.exists() or private.exists():raise ValueError('Existing trial/context retained; no retry or reset')
    output.mkdir(parents=True)
    package=ROOT/'task-packages'/category/job['task']
    result=dict(job=job,category=category,terminal=False,model=job['model'],reasoning='high',
        started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),errors=[],
        manual_interventions=0,checkpoints=[],physical_attempts=[],frontend_status='not_started')
    result['monetary_cost']=dict(value=None,currency=None,source='not_captured',
        scope='This adapter captures native Token usage, not service invoices; no monetary price estimate is supplied')
    result['host']=dict(os=platform.platform(),logical_cpus=os.cpu_count(),
        load_average_start=os.getloadavg(),timing_scope='Shared host; serial study trials and two EDA threads')
    write_json(output/'launch.json',dict(result,package_sha256=digest(package/'package.json'),
        campaign_freeze_sha256=digest(ROOT/'campaign-freeze.json'),
        trial_resource_seconds=37800,grading_limit_seconds=1800,
        grading_scope='Offline evaluator work, separately timed and never fed back to the model'))
    runtime=output/'runtime'
    try:
        project=output/'project';database=prepare(project,package,job)
        config=dict(record=str(runtime),private=str(private),project=str(project),workspace=str(project),
            model=job['model'],limit=1_000_000,active_seconds=5400,scored=True,
            eda=dict(task=job['task'],trial=identity,category=category))
        write_json(output/'runtime-config.json',config)
        if job['workflow']=='C0':
            control,_=run_native(config,BASE+'\nRead spec/task.md, spec/resource-contract.md, '
                'spec/scorecard.json and expert-checklist.json. Autonomously implement the assigned '
                'subsystem, check its integration, deliver GDS and repair within the common budget. '
                'Finish with a truthful concise report; no additional agents or human intervention.')
            result.update(frontend_status=control['reason'],native_control=control)
        else:
            from chip_nebula.taskgraph.static_cli import run_workflow
            pool=ContextPool(private,output/'contexts.json',job['model'],runtime=config)
            status=run_workflow(project,database,'capacity',pool,workers=1)
            result['frontend_status']=status.value
            if (runtime/'trial-stop.json').exists():
                result['shared_stop']=json.loads((runtime/'trial-stop.json').read_text())
    except Exception as error:
        result.update(frontend_status='infrastructure_error')
        result['errors'].append(type(error).__name__+': '+str(error))
    frontend_end=time.monotonic()
    if (runtime/'clock.json').exists():
        clock=json.loads((runtime/'clock.json').read_text())
        result.update(preparation_seconds=clock['start']-start,
            active_frontend_seconds=frontend_end-clock['start']-clock['physical_seconds'],
            physical_wait_seconds=clock['physical_seconds'])
    else:
        result.update(preparation_seconds=frontend_end-start,active_frontend_seconds=0,physical_wait_seconds=0)
    result['active_frontend_overrun_seconds']=max(0,result['active_frontend_seconds']-5400)
    if (runtime/'usage.json').exists():
        ledger_state=json.loads((runtime/'usage.json').read_text())
        result['usage']=TokenLedger(ledger_state).summary()
        if ledger_state.get('transcript_prefixes'):
            try:
                accounting=output/'native-accounting.json'
                export_accounting(private,runtime,accounting,job['model'])
                result['accounting_replay']=replay_accounting(accounting,runtime)
                if not result['accounting_replay']['passed']:result['usage']['measurement_valid']=False
            except Exception as error:
                result['accounting_replay']=dict(passed=False,error=type(error).__name__+': '+str(error))
                result['usage']['measurement_valid']=False
                result['errors'].append('Offline accounting export/replay failed')
    else:
        result['usage']=dict(measurement_valid=False,actual_tokens=0,errors=['Missing native usage'])
    if (runtime/'tools/tool-ledger.json').exists():
        result['tools']=json.loads((runtime/'tools/tool-ledger.json').read_text())
    result['execution']=execution_validity(output,result['frontend_status'])
    result['manual_interventions']=result['execution']['manual_interventions']
    result['coordination']=invocation_costs(runtime)
    ledger=json.loads((ROOT/'physical-ledger.json').read_text())
    result['physical_attempts']=[r for r in ledger['attempts'] if r['trial']==identity]
    # Full use of the agent budget must not remove its independent evaluation time.
    grade_deadline=time.monotonic()+1800
    reference=json.loads((package/'agent/spec/scorecard.json').read_text())['reference']
    # Main endpoint first, then checkpoints and at most two diagnostic deliveries.
    evaluations=[(str(b),b,None) for b in reversed(CHECKPOINTS)]
    evaluations += [('physical-'+str(i+1),CHECKPOINTS[-1],row['identity'])
                    for i,row in enumerate(result['physical_attempts'])]
    result['physical_diagnostics']=[]
    for name,budget,physical_identity in evaluations:
        folder=output/'grading'/name
        request=dict(runtime=str(runtime),task=job['task'],budget=budget,reference=reference,
                     output=str(folder),task_package=str(package),deadline=grade_deadline,physical_identity=physical_identity)
        request_path=output/'grading'/f'{name}-request.json';write_json(request_path,request)
        if not result['usage']['measurement_valid']:
            graded=unavailable(budget,'Native Token/source measurement invalid')
        else:
            try:
                with (output/'grading'/f'{name}.log').open('w') as log:
                    done=run_group([sys.executable,str(ROOT/'scripts/capacity_grade.py'),'--request',str(request_path)],
                        stdout=log,stderr=subprocess.STDOUT,timeout=remaining(grade_deadline,1800))
                graded=json.loads((folder/'score.json').read_text()) if done.returncode==0 else unavailable(budget,'Grader infrastructure failure')
            except Exception as error:
                graded=unavailable(budget,type(error).__name__+': '+str(error))
        if not result['execution']['valid']:
            graded['measurement_valid']=False
            graded['errors']=graded.get('errors',[])+result['execution']['errors']
        if physical_identity:
            graded.update(selection='physical_attempt_diagnostic',physical_attempt=physical_identity)
            result['physical_diagnostics'].append(graded)
        else:
            result['checkpoints'].append(graded)
    result['checkpoints'].sort(key=lambda r:r['budget'])
    final=result['checkpoints'][-1]
    result['success_observation_scope']='Three budget checkpoints plus each submitted physical source; not every intermediate edit'
    observed=[r for r in result['checkpoints']+result['physical_diagnostics']
              if r.get('measurement_valid') and r.get('source_tokens') is not None]
    result['first_observed_success_tokens']={key:min((r['source_tokens'] for r in observed if r.get(key)),default=None)
        for key in ('functional_pass','joint_pass','constraint_pass')}
    result['first_observed_success_seconds']={key:min((r[field] for r in observed if r.get(key) and r.get(field) is not None),default=None)
        for key,field in (('functional_pass','source_elapsed_seconds'),('joint_pass','delivery_elapsed_seconds'),
                          ('constraint_pass','delivery_elapsed_seconds'))}
    result.update({key:final[key] for key in ('functional_pass','gds_pass','joint_pass','constraint_pass','final_score')})
    result.update(measurement_valid=result['usage']['measurement_valid'] and final['measurement_valid'],
        terminal=True,grading_seconds=time.monotonic()-frontend_end,total_wall_seconds=time.monotonic()-start,
        finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='evaluated' if result['usage']['measurement_valid'] and final['measurement_valid'] else 'measurement_or_infrastructure_invalid')
    result['host']['load_average_end']=os.getloadavg()
    result['credited_outcomes']=observation(result)
    write_json(output/'result.json',result)
    print(json.dumps({k:result[k] for k in ('status','measurement_valid','credited_outcomes','total_wall_seconds')}),flush=True)
    return result


def recorded_run(category,identity):
    output=ROOT/'trials'/category/identity
    existed=output.exists()
    try:
        return _run(category,identity)
    except BaseException as error:
        # A launched trial keeps a terminal failure even if collecting its receipts fails.
        if not existed and (output/'launch.json').is_file() and not (output/'result.json').exists():
            result=json.loads((output/'launch.json').read_text())
            result.update(terminal=True,status='infrastructure_error',measurement_valid=False,
                errors=[type(error).__name__+': '+str(error)],
                finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                checkpoints=[unavailable(b,'Trial finalization interrupted') for b in CHECKPOINTS])
            result.update({key:result['checkpoints'][-1][key] for key in
                ('functional_pass','gds_pass','joint_pass','constraint_pass','final_score')})
            write_json(output/'result.json',result)
        raise


def run(category,identity):
    with (ROOT/'.trial-execution.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return recorded_run(category,identity)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--category',choices=('pilot','formal'),required=True)
    parser.add_argument('--trial',required=True)
    args=parser.parse_args();run(args.category,args.trial)

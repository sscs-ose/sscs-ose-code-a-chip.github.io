"""Fresh requirements-to-RTL trials on qualified generated tasks, using native roles."""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import yaml

from chip_nebula.taskgraph.domain import Artifact,ArtifactContent,ArtifactProducer,TaskBrief
from chip_nebula.taskgraph.static_cli import load_compiled_recipe,run_workflow,cancel_workflow_attempts
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from qualify_benchmark import simulate
from study_budget import BudgetPool
from study_isolation import prepare_credentials
from study_portability import private_context
from study_protocol import MODEL,digest,write_json

CASE=Path(__file__).resolve().parents[1]
DESIGN='''Read spec/task.md, interface.json and the typed CSIR behavioral contract.
Implement the exact top-level interface and all behavior in rtl/. Develop with
python3 tools/check.py and optional tests/designer/. Write only rtl/, tests/designer/
and build/. Do not modify the task, checker, workflow or permissions, inspect
other trials or final evaluators, or invoke extra models/agents. Repair actionable
feedback within the shared 1200-second frontend budget. Return
NEBULA_OUTPUT: {"rtl":{"module":"the exact requested top-level module"}}.
'''
REVIEW='''Independently inspect and test delivered RTL against spec/task.md and
interface.json. Run python3 tools/check.py; add focused boundary/reset/protocol
tests under tests/reviewer/ if useful. Do not change RTL, task or public checker,
read other projects/final evaluators, or invoke extra models/agents. Your time
shares the original 1200-second frontend budget with the designer. Write
reports/review.json and return NEBULA_OUTPUT: {"report":{"subject":"benchmark-rtl",
"verdict":"passed or failed","repair_summary":"concrete findings"}}.
Use an actual verdict. Failed findings go back to the original designer.
'''


def git(project,*args):
    return subprocess.run(['git',*args],cwd=project,text=True,capture_output=True,check=True).stdout.strip()


def write_configuration(project):
    project=Path(project).resolve()
    for relative in ('.chip_nebula/roles','.chip_nebula/recipes','tests/designer','tests/reviewer','reports'):
        (project/relative).mkdir(parents=True,exist_ok=True)
    for name,prompt,accepted,produced in (
        ('benchmark-designer',DESIGN,['specification.source','verification.report'],['rtl.snapshot']),
        ('benchmark-verifier',REVIEW,['specification.source','rtl.snapshot'],['verification.report']),
        ('benchmark-auditor','Execute the fixed public check.',['rtl.snapshot','verification.report'],['verification.report'])):
        (project/'.chip_nebula/roles'/(name+'.yaml')).write_text(yaml.safe_dump(dict(name=name,version=1,system_prompt=prompt,
            accepted_types=accepted,produced_types=produced,framework='codex',model=MODEL),sort_keys=False))
    source=dict(type='specification.source',**{'from':'$parameters.source'})
    rtl=dict(type='rtl.snapshot',**{'from':'$tasks.designer.outputs.rtl'})
    permission=lambda write:dict(read=['spec/**','rtl/**','tb/**','tools/**','tests/**','reports/**','build/**'],
        write=write,tools=['python3','iverilog','vvp','verilator','git','make'])
    execution=dict(framework='codex',model=MODEL,reasoning_effort='high',timeout_seconds=1200)
    tasks=dict(
        designer=dict(role='benchmark-designer',intent=DESIGN,permission=permission(['rtl/**','tests/designer/**','build/**']),
            inputs=dict(source=source),outputs=dict(rtl=dict(type='rtl.snapshot',paths=['rtl/**'])),execution=execution,max_attempts=8),
        verifier=dict(role='benchmark-verifier',intent=REVIEW,permission=permission(['tests/reviewer/**','reports/**','build/**']),
            inputs=dict(source=source,rtl=rtl),outputs=dict(report=dict(type='verification.report',paths=['reports/**','tests/reviewer/**'])),execution=execution,max_attempts=8),
        audit=dict(role='benchmark-auditor',intent='Replay the unchanged public checker.',permission=permission(['build/**']),
            inputs=dict(rtl=rtl,review=dict(type='verification.report',**{'from':'$tasks.verifier.outputs.report'},release=dict(field='verdict',equals='passed'))),
            outputs=dict(report=dict(type='verification.report',paths=['build/smoke/**'])),
            execution=dict(executor='tool',command='python3 tools/check.py',timeout_seconds=120),max_attempts=8))
    feedback=[dict(source=name,verdict='fail',target='designer',kind='feedback',propagate=True,summary='Repair the reported task defect.',summary_field='report.repair_summary') for name in ('verifier','audit')]
    recipe=project/'.chip_nebula/recipes/benchmark.yaml'
    recipe.write_text(yaml.safe_dump(dict(name='benchmark-generation',version=2,parameters=dict(source='specification.source'),tasks=tasks,feedback=feedback),sort_keys=False))
    return recipe


def prepare(task,project):
    task,project=Path(task).resolve(),Path(project).resolve()
    spec=json.loads((task/'agent/spec/task.json').read_text())
    if not spec['task_validated']:raise ValueError('Benchmark reference calibration must precede new agent runs')
    shutil.copytree(task/'agent',project)
    recipe=write_configuration(project)
    (project/'.gitignore').write_text('.chip_nebula/\nbuild/\n__pycache__/\n*.pyc\n')
    for args in (('init','-q'),('config','user.name','ChipNebula benchmark automation'),('config','user.email','automation@chipnebula.invalid'),
                 ('add','.'),('add','-f','.chip_nebula/roles','.chip_nebula/recipes'),('commit','-qm','Freeze calibrated task and design workflow')):git(project,*args)
    commit,tree=git(project,'rev-parse','HEAD'),git(project,'rev-parse','HEAD^{tree}')
    compiled=load_compiled_recipe(recipe,workflow_id='benchmark-generation',goal='Implement one generated task from requirements',
        parameters=dict(source='generated-task'),baseline_commit=commit,workers=1)
    artifact=Artifact(id='generated-task',type='specification.source',schema_version=1,
        producer=ArtifactProducer('external','benchmark-contract','frozen-input','benchmark-author',1),
        content=ArtifactContent('git',commit,tree,('spec','tb','tools')),
        payload=dict(source_name=spec['id'],media_type='text/markdown',content=(project/'spec/task.md').read_text(),
            content_digest='sha256:'+digest(project/'spec/task.md'),received_at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    briefs={task.id:TaskBrief(objective=task.intent,deliverables=tuple(out.name+': '+out.artifact_type for out in task.outputs),
        responsibilities=('Implement/review the fixed task with real test evidence.',),exclusions=('No task/checker/permission changes or extra model calls.',),
        completion_criteria=('Publish exact RTL or an honest verification verdict.',),
        collaboration=tuple('task:'+other.id for other in compiled.tasks if other.id!=task.id)) for task in compiled.tasks}
    with StaticTaskGraphStore(project/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        store.create_workflow(compiled.workflow,compiled.roles,compiled.tasks,[artifact],compiled.joint_analysis_groups,compiled.feedback_routes)
        store.freeze_briefs('benchmark-generation',briefs)
    git(project,'update-ref','refs/chip-nebula/artifacts/generated-task',commit)
    return compiled


def worker(project,private):
    prepare_credentials(private);wrappers=private/'wrapper';wrappers.mkdir()
    wrapper=wrappers/'codex';wrapper.write_text('#!'+sys.executable+'\nimport os,sys\nos.execv(sys.executable,[sys.executable,'+repr(str(CASE/'scripts/study_isolation.py'))+',*sys.argv[1:]])\n');wrapper.chmod(0o700)
    os.environ.update(CHIP_STUDY_PROJECT=str(project),CHIP_STUDY_PRIVATE_HOME=str(private),
        PATH=str(wrappers)+os.pathsep+os.environ['PATH'])
    pool=BudgetPool(project.parent/'results/budget.json',total_deadline=time.monotonic()+1200)
    state=run_workflow(project,project/'.chip_nebula/shared/memory/taskgraph-v2.db','benchmark-generation',pool,workers=1)
    write_json(project.parent/'results/workflow.json',dict(state=state.value))


def run(campaign,task):
    campaign,task=Path(campaign).resolve(),Path(task).resolve();name=task.name
    folder=campaign/'benchmark/demonstrations'/name
    if folder.exists():raise ValueError('Existing scored frontend trial preserved')
    results=folder/'results';results.mkdir(parents=True);project=folder/'project';prepare(task,project)
    private=private_context(campaign,'benchmark-generation',name)
    if private.exists():raise ValueError('New task needs a fresh private context')
    started=time.monotonic();timed_out=False
    with (results/'workflow.log').open('w') as log:
        process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker',str(project),'--private',str(private)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:process.wait(timeout=1200)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=20)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            cancel_workflow_attempts(project,project/'.chip_nebula/shared/memory/taskgraph-v2.db','benchmark-generation',reason='Frozen 1200-second frontend budget exhausted')
    with StaticTaskGraphStore(project/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        delivery=store.deliveries('benchmark-generation:designer').get('rtl')
        artifact=store.get_artifact(delivery.artifact_id) if delivery else None
        status=store.get_workflow('benchmark-generation').status.value
    outcome=dict(task=name,functional_qualified=False,physical_qualified=False,frontend_seconds=time.monotonic()-started,
                 workflow_state=status,runner_exit_code=process.returncode,timed_out=timed_out,
                 manual_design_interventions=0,hidden_planner_calls=0,source_sha256={})
    if artifact:
        selected=results/'selected';selected.mkdir()
        for relative in git(project,'ls-tree','-r','--name-only',artifact.content.commit,'rtl').splitlines():
            if Path(relative).suffix not in ('.v','.sv'):continue
            destination=selected/relative;destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(subprocess.run(['git','show',artifact.content.commit+':'+relative],cwd=project,capture_output=True,check=True).stdout)
            outcome['source_sha256'][relative]=digest(destination)
        sources=[selected/p for p in outcome['source_sha256']]
        final=simulate(sources,task/'grader/acceptance_tb.sv',results/'independent-final')
        top=json.loads((task/'build.json').read_text())['top']
        command=['yosys','-Q','-T','-p','read_slang --top '+top+' '+' '.join(map(str,sources))+'; proc; opt; check -assert']
        synthesis=subprocess.run(command,text=True,capture_output=True,timeout=120)
        (results/'synthesis.log').write_text(synthesis.stdout+synthesis.stderr)
        outcome.update(functional_qualified=final['passed'] and synthesis.returncode==0,final=final,source_delivery=artifact.id,synthesis_exit_code=synthesis.returncode)
    from run_configuration_study import usage_and_repairs
    outcome['usage']=usage_and_repairs(private,results,{})
    write_json(results/'result.json',outcome)
    print(json.dumps(dict(task=name,functional_qualified=outcome['functional_qualified'],results=str(results))),flush=True)
    return outcome


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path);parser.add_argument('--task',type=Path)
    parser.add_argument('--worker',type=Path);parser.add_argument('--private',type=Path)
    a=parser.parse_args()
    if a.worker:worker(a.worker.resolve(),a.private.resolve())
    else:
        if not a.campaign or not a.task:parser.error('--campaign and --task required')
        run(a.campaign,a.task)

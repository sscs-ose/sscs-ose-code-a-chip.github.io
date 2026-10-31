"""F0/F1/F2 use one TaskGraph kernel, shared actions, gates and physical budgets."""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

from benchmark_ppa_proposal import validate
from benchmark_rtl_actions import materialize
from campaign_budget import finish, reserve
from chip_nebula.taskgraph.domain import Artifact,ArtifactContent,ArtifactProducer,TaskBrief
from chip_nebula.taskgraph.static_cli import load_compiled_recipe,run_workflow
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from evaluate_study_physical import evaluate
from freeze_benchmark_study import verify as verify_freeze
from run_study_physical import run as run_physical
from study_budget import BudgetPool
from study_isolation import prepare_credentials
from study_portability import private_context
from study_protocol import MODEL,digest,ranking,score,write_json

CASE=Path(__file__).resolve().parents[1]
PROPOSER='''You are the PPA optimizer for a five-stage RV32I CPU plus INT8 dot4 accelerator.
Read context/baseline.json and context/protocol.json. Before each later proposal,
inspect the captured real EDA/measurement history and feedback. Choose one untried
candidate using the common physical parameter domain and proved RTL actions.
Optimize qualified area-times-workload-energy Q, not empty floorplan or a timing
estimate. Explain tradeoffs and report fields. All workflows have identical tools,
actions, budget, final acceptance and best-result retention. Only the protected
tool can execute EDA or apply the mechanical shared RTL actions. You may not edit
RTL, constraints, permissions, checkers or budget, run extra models/agents/EDA,
or inspect other sessions. All roles share 1200 seconds and at most three accepted
candidate evaluations. EDA wait is separate. Write only proposal/ and build/.
Write proposal/candidate.json with exactly configuration (four physical parameters),
rtl_actions (explicit boolean operand_isolation and reduce_width), rationale.
Validate with python3 tools/run_ppa.py validate. Repair rejected proposals yourself.
Return the matching NEBULA_OUTPUT: {"candidate":{"configuration":{...},
"rtl_actions":{"operand_isolation":false,"reduce_width":false},"rationale":"..."}}.
'''
REVIEWER='''Independently review the immutable candidate and captured report history
against context/baseline.json and context/protocol.json. Verify actual timing,
electrical and energy report interpretation, common action qualification, limits
and the candidate's rationale. Do not invent results or reject simply because a
valid experiment might fail; identify concrete errors or unsupported assumptions.
Do not change the candidate, run EDA/models, or read other trials. The optimizer
owns revisions. Your time and Tokens share the same 1200-second session budget.
Write reports/review.json with subject, verdict (passed or failed), repair_summary;
publish exactly those fields in NEBULA_OUTPUT: {"report":{...}}. Write only reports/
and build/. Inspect prior evaluation evidence under .nebula_inputs/ before judging.
'''


def git(project,*args):
    return subprocess.run(['git',*args],cwd=project,text=True,capture_output=True,check=True).stdout.strip()


def metadata():
    root=Path(os.environ['CHIP_BENCHMARK_PPA_SESSION']).resolve()
    return root,json.loads((root/'session.json').read_text())


def observations(root,meta):
    baseline=Path(meta['baseline'])
    if digest(baseline)!=meta['baseline_sha256']:raise ValueError('Common starting evidence changed')
    return [json.loads(baseline.read_text()),*[json.loads(p.read_text()) for p in sorted((root/'candidates').glob('*/evaluation.json'))]]


def review_required(meta,history):
    return meta['job']['workflow']=='F1' or meta['job']['workflow']=='F2' and (len(history)==1 or not history[-1]['rank_eligible'])


def capture(root,task):
    project=root/'project'
    with StaticTaskGraphStore(project/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        attempt=store.active_attempt('workflow-ppa:'+task)
        if attempt is None:raise ValueError('No active protected '+task+' attempt')
        candidate=store.get_artifact(attempt.input_deliveries['candidate']).document()
    document=json.loads(git(project,'show',candidate['content']['commit']+':proposal/candidate.json'))
    if document!={key:candidate['payload'][key] for key in ('configuration','rtl_actions','rationale')}:
        raise ValueError('Candidate file differs from captured Artifact')
    return candidate,document


def evaluate_candidate(root,meta,task):
    candidate,document=capture(root,task);history=observations(root,meta)
    for path in (root/'candidates').glob('*/launch.json'):
        if json.loads(path.read_text())['candidate_artifact']==candidate['id']:
            report=path.parent/'report.json'
            if report.exists():return json.loads(report.read_text())
            raise ValueError('Interrupted accepted candidate retained; no second execution')
    protocol=json.loads(Path(meta['protocol']).read_text())['ppa']
    validate(document,history,protocol['allowed_rtl_actions'])
    need=review_required(meta,history)
    if need!=(task=='reviewed'):raise ValueError('Execution branch violates frozen review policy')
    index=len(list((root/'candidates').glob('*/launch.json')))+1
    if index>3:raise ValueError('No fourth candidate is allowed')
    slot=root/'candidates'/f'{index:02d}';slot.mkdir()
    write_json(slot/'launch.json',dict(candidate_artifact=candidate['id'],candidate_index=index,
        candidate=document,review_required=need,accepted_at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    source=slot/'source';materialize(source,document['rtl_actions'])
    campaign=Path(meta['campaign']);identity=meta['job']['id']+'-candidate-'+str(index);physical=slot/'physical'
    reserve(campaign,'ppa',identity,physical)
    started=time.monotonic()
    try:
        run_physical(physical,source,document['configuration'],10526)
        # Legacy evaluator self-normalizes; cross-RTL normalization is guarded here.
        measured=evaluate(physical)
        reference=history[0]
        for field in ('period_ps','sdc_sha256','threads'):
            if measured['physical_manifest'][field]!=reference['physical_manifest'][field]:
                raise ValueError('Candidate differs from common constraints: '+field)
        delivery=json.loads((source/'selected-delivery.json').read_text())
        if measured['physical_manifest']['rtl_sha256']!=delivery['exported_source_sha256']:
            raise ValueError('Physical RTL differs from proved action materialization')
        if measured['rank_eligible']:
            measured.update(score(measured['cell_area_um2'],measured['energy_j'],reference['cell_area_um2'],reference['energy_j']))
    except Exception as error:
        import traceback
        (slot/'error.log').write_text(traceback.format_exc())
        measured=dict(rank_eligible=False,physical_qualified=False,failure_classes=['infrastructure_or_evaluation'],
            error_class=type(error).__name__,error=str(error),cell_area_um2=None,energy_j={},total_wall_seconds=time.monotonic()-started)
    measured.update(configuration=document['configuration'],rtl_actions=document['rtl_actions'],candidate_index=index,
        candidate_artifact=candidate['id'],proposal_rationale=document['rationale'],review_required=need,
        source_delivery_sha256=digest(source/'selected-delivery.json'),
        elapsed_search_seconds=time.monotonic()-meta['started_monotonic'],normalization_baseline_sha256=meta['baseline_sha256'])
    write_json(slot/'evaluation.json',measured)
    finish(campaign,identity,status='qualified' if measured['rank_eligible'] else 'failed',evidence=str((slot/'evaluation.json').relative_to(campaign)))
    budget=root/'results/budget.json';used=json.loads(budget.read_text())['used_agent_seconds'] if budget.exists() else 0
    report=dict(subject=candidate['id'],verdict='passed' if measured['rank_eligible'] else 'failed',
        continue_search=index<3 and used<1199,history=[*history,measured],candidate_index=index,
        repair_summary='Use the actual outcome and remaining common budget to choose the next untried candidate.')
    write_json(slot/'report.json',report)
    return report


def summarize(root,meta):
    history=observations(root,meta);new=history[1:];eligible=[r for r in new if r['rank_eligible']]
    budget=root/'results/budget.json'
    return dict(finished=True,job=meta['job'],baseline=history[0],candidates=new,
        best_new_qualified=min(eligible,key=ranking) if eligible else None,
        best_including_start=min([history[0],*eligible],key=ranking),
        accepted_candidates=len(list((root/'candidates').glob('*/launch.json'))),
        unused_candidate_slots=3-len(list((root/'candidates').glob('*/launch.json'))),
        budget=json.loads(budget.read_text()) if budget.exists() else {},
        elapsed_seconds=time.monotonic()-meta['started_monotonic'])


def native_counts(root):
    with StaticTaskGraphStore(root/'project/.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        optimizers=store.list_attempts('workflow-ppa:optimizer')
        reviews=store.list_attempts('workflow-ppa:reviewer')
        rework=sum(any(w.source_task_id=='workflow-ppa:reviewer' for w in store.work_items(a.work_item_ids)) for a in optimizers)
        return dict(optimizer_attempts=len(optimizers),review_attempts=len(reviews),
            review_rejections=sum(a.verdict in ('fail','failed') for a in reviews),
            review_feedback_optimizer_dispatches=rework,
            scope='Native attempt/verdict and captured reviewer-feedback work items; not an estimate of within-role edits')


def tool_action(action,workspace):
    root,meta=metadata()
    if action=='route':
        candidate,document=capture(root,'router');history=observations(root,meta)
        validate(document,history,json.loads(Path(meta['protocol']).read_text())['ppa']['allowed_rtl_actions'])
        report=dict(subject=candidate['id'],verdict='passed',review_required=review_required(meta,history),history=history,
            repair_summary='Route according to the frozen workflow policy; this is not an AI review.')
        write_json(workspace/'build/route/report.json',report)
    elif action in ('reviewed','direct'):
        report=evaluate_candidate(root,meta,action)
        write_json(workspace/'build/evaluation/report.json',report)
    elif action=='finalize':
        result=summarize(root,meta);write_json(root/'results/search-summary.json',result)
        report=dict(subject=meta['job']['id'],verdict='passed',search_finished=True,candidate_count=len(result['candidates']))
        write_json(workspace/'build/session/report.json',report)
    else:raise ValueError('Unknown protected workflow tool')
    print('NEBULA_OUTPUT: '+json.dumps({'report':report}))


def prepare(root,meta):
    project=root/'project'
    if project.exists():raise ValueError('Existing experiment preserved')
    for relative in ('context','proposal','reports','tools','.chip_nebula/roles','.chip_nebula/recipes','.chip_nebula/schemas'):
        (project/relative).mkdir(parents=True,exist_ok=True)
    baseline=json.loads(Path(meta['baseline']).read_text())
    if not baseline['rank_eligible']:raise ValueError('Starting point lacks qualified energy and area')
    write_json(project/'context/baseline.json',baseline)
    write_json(project/'context/protocol.json',json.loads(Path(meta['protocol']).read_text())['ppa'])
    for name,prompt,accepted,produced in (
        ('ppa-optimizer',PROPOSER,['specification.source','ppa.evaluation.report','verification.report'],['ppa.candidate']),
        ('ppa-verifier',REVIEWER,['specification.source','ppa.candidate','ppa.route.report'],['verification.report']),
        ('ppa-tool','Run only the protected deterministic experiment tool.',['ppa.candidate','verification.report','ppa.route.report'],['ppa.route.report','ppa.evaluation.report','ppa.session.report'])):
        (project/'.chip_nebula/roles'/(name+'.yaml')).write_text(yaml.safe_dump(dict(name=name,version=1,system_prompt=prompt,accepted_types=accepted,produced_types=produced,framework='codex',model=MODEL),sort_keys=False))
    fields={'ppa.candidate':dict(configuration='dict',rtl_actions='dict',rationale='str'),
        'ppa.route.report':dict(subject='str',verdict='str',review_required='bool',history='list',repair_summary='str'),
        'ppa.evaluation.report':dict(subject='str',verdict='str',continue_search='bool',history='list',repair_summary='str'),
        'ppa.session.report':dict(subject='str',verdict='str',search_finished='bool',candidate_count='int')}
    for name,required in fields.items():
        (project/'.chip_nebula/schemas'/(name+'.yaml')).write_text(yaml.safe_dump(dict(type=name,version=1,required_fields=required,carries_engineering_verdict=name.endswith('.report')),sort_keys=False))
    for name in ('study_protocol.py','benchmark_ppa_proposal.py'):
        shutil.copy2(CASE/'scripts'/name,project/'tools'/name)
    (project/'tools/run_ppa.py').write_text('''import os,sys
from pathlib import Path
python=os.environ['CHIP_STUDY_PYTHON']
if sys.executable!=python:os.execv(python,[python,__file__,*sys.argv[1:]])
if sys.argv[1]=='validate':
 from benchmark_ppa_proposal import local
 local(Path.cwd());print('PPA_CANDIDATE_VALID');raise SystemExit(0)
sys.path.insert(0,str(Path(os.environ['CHIP_STUDY_CASE'])/'scripts'))
from run_benchmark_ppa import tool_action
tool_action(sys.argv[1],Path.cwd())
''')
    source=dict(type='specification.source',**{'from':'$parameters.source'})
    candidate=dict(type='ppa.candidate',**{'from':'$tasks.optimizer.outputs.candidate'})
    route=dict(type='ppa.route.report',**{'from':'$tasks.router.outputs.report'})
    permission=lambda writes:dict(read=['context/**','proposal/**','reports/**','tools/**','build/**'],write=writes,tools=['python3','git'])
    agent_execution=dict(framework='codex',model=MODEL,reasoning_effort='high',timeout_seconds=1200)
    tool=lambda action,timeout:dict(executor='tool',command='python3 tools/run_ppa.py '+action,timeout_seconds=timeout)
    tasks=dict(optimizer=dict(role='ppa-optimizer',intent=PROPOSER,permission=permission(['proposal/**','build/**']),inputs=dict(source=source),
        outputs=dict(candidate=dict(type='ppa.candidate',paths=['proposal/**'])),execution=agent_execution,max_attempts=12,
        gates=[dict(name='common-valid-unseen-action',template='script-check',version=1,on_failure='retry',
          parameters=dict(script='python3',arguments=['tools/run_ppa.py','validate'],expected='PPA_CANDIDATE_VALID',timeout=30,level='L1',error_class='invalid_candidate'))]),
        router=dict(role='ppa-tool',intent='Route the candidate using frozen conditional review rules.',permission=permission(['build/route/**']),
          inputs=dict(candidate=candidate),outputs=dict(report=dict(type='ppa.route.report',paths=['build/route/**'])),execution=tool('route',30),max_attempts=12))
    tasks['reviewer']=dict(role='ppa-verifier',intent=REVIEWER,on_demand=True,permission=permission(['reports/**','build/**']),
        inputs=dict(source=source,candidate=candidate,route=dict(route,release=dict(field='review_required',equals=True))),
        outputs=dict(report=dict(type='verification.report',paths=['reports/**'])),execution=agent_execution,max_attempts=12)
    for name in ('reviewed','direct'):
        inputs=dict(candidate=candidate,route=dict(route,release=dict(field='review_required',equals=name=='reviewed')))
        if name=='reviewed':inputs['review']=dict(type='verification.report',**{'from':'$tasks.reviewer.outputs.report'},release=dict(field='verdict',equals='passed'))
        tasks[name]=dict(role='ppa-tool',intent='Evaluate one captured candidate with shared independent engineering gates.',on_demand=True,
            permission=permission(['build/evaluation/**']),inputs=inputs,outputs=dict(report=dict(type='ppa.evaluation.report',paths=['build/evaluation/**'])),execution=tool(name,16500),max_attempts=3)
    tasks['finalizer']=dict(role='ppa-tool',intent='Record terminal search state independently of chip qualification.',on_demand=True,
        permission=permission(['build/session/**']),inputs={},outputs=dict(report=dict(type='ppa.session.report',paths=['build/session/**'])),execution=tool('finalize',30),max_attempts=1)
    feedback=[dict(source='router',verdict='pass',target='reviewer' if needed else 'direct',kind='feedback',propagate=False,
                   when=dict(field='report.review_required',equals=needed),summary='Execute the frozen review branch.' if needed else 'Execute without an AI review.') for needed in (True,False)]
    feedback.extend([dict(source='reviewer',verdict='pass',target='reviewed',kind='feedback',propagate=False,summary='Evaluate the reviewed proposal.'),
        dict(source='reviewer',verdict='fail',target='optimizer',kind='feedback',propagate=True,summary='Repair concrete review findings.',summary_field='report.repair_summary')])
    for name in ('reviewed','direct'):
        for verdict in ('pass','fail'):
            for continuing in (True,False):
                feedback.append(dict(source=name,verdict=verdict,target='optimizer' if continuing else 'finalizer',kind='feedback',propagate=continuing,
                    when=dict(field='report.continue_search',equals=continuing),summary='Continue from real measurements.' if continuing else 'Record completed search.'))
    recipe=project/'.chip_nebula/recipes/workflow-ppa.yaml'
    recipe.write_text(yaml.safe_dump(dict(name='workflow-ppa',version=2,parameters=dict(source='specification.source'),tasks=tasks,feedback=feedback),sort_keys=False))
    (project/'.gitignore').write_text('.chip_nebula/\nbuild/\n__pycache__/\n*.pyc\n')
    for args in (('init','-q'),('config','user.name','ChipWave workflow study'),('config','user.email','automation@chipwave.invalid'),
                 ('add','.'),('add','-f','.chip_nebula/roles','.chip_nebula/recipes','.chip_nebula/schemas'),('commit','-qm','Freeze configurable workflow experiment')):git(project,*args)
    commit,tree=git(project,'rev-parse','HEAD'),git(project,'rev-parse','HEAD^{tree}')
    compiled=load_compiled_recipe(recipe,workflow_id='workflow-ppa',goal='Measure workflow organization with common chip actions and checks',parameters=dict(source='common-context'),baseline_commit=commit,workers=1)
    artifact=Artifact(id='common-context',type='specification.source',schema_version=1,
        producer=ArtifactProducer('external','workflow-protocol','frozen-input','experiment-author',1),content=ArtifactContent('git',commit,tree,('context',)),
        payload=dict(source_name='Frozen common workflow experiment',media_type='application/json',content=(project/'context/protocol.json').read_text(),content_digest='sha256:'+digest(project/'context/protocol.json'),received_at='2026-10-18T00:00:00+00:00'))
    briefs={task.id:TaskBrief(objective=task.intent,deliverables=tuple(o.name+': '+o.artifact_type for o in task.outputs),
        responsibilities=('Use captured reports and the common protocol.',),exclusions=('No hidden tools/models or modifications to frozen conditions.',),
        completion_criteria=('Publish genuine results; retain failures and costs.',),collaboration=tuple('task:'+other.id for other in compiled.tasks if other.id!=task.id)) for task in compiled.tasks}
    with StaticTaskGraphStore(project/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        store.create_workflow(compiled.workflow,compiled.roles,compiled.tasks,[artifact],compiled.joint_analysis_groups,compiled.feedback_routes);store.freeze_briefs('workflow-ppa',briefs)
    git(project,'update-ref','refs/chip-nebula/artifacts/common-context',commit)
    return compiled


def worker(root,private):
    root=root.resolve();meta=json.loads((root/'session.json').read_text());campaign=Path(meta['campaign'])
    verify_freeze(campaign,meta)
    prepare_credentials(private);wrappers=private/'wrapper';wrappers.mkdir()
    wrapper=wrappers/'codex';wrapper.write_text('#!'+sys.executable+'\nimport os,sys\nos.execv(sys.executable,[sys.executable,'+repr(str(CASE/'scripts/study_isolation.py'))+',*sys.argv[1:]])\n');wrapper.chmod(0o700)
    os.environ.update(CHIP_BENCHMARK_PPA_SESSION=str(root),CHIP_STUDY_CASE=str(CASE),CHIP_STUDY_PYTHON=sys.executable,
        CHIP_STUDY_PROJECT=str(root/'project'),CHIP_STUDY_PRIVATE_HOME=str(private),PATH=str(wrappers)+os.pathsep+os.environ['PATH'])
    status=run_workflow(root/'project',root/'project/.chip_nebula/shared/memory/taskgraph-v2.db','workflow-ppa',BudgetPool(root/'results/budget.json'),workers=1)
    from run_configuration_study import usage_and_repairs
    result=summarize(root,meta);result.update(workflow_state=status.value,usage=usage_and_repairs(private,root/'results',{}),
        coordination=native_counts(root),executed_worker_sha256=digest(Path(__file__)))
    write_json(root/'results/search-summary.json',result)


def run_session(campaign,baseline,job):
    campaign,baseline=Path(campaign).resolve(),Path(baseline).resolve();root=campaign/'ppa'/job['id']
    if root.exists():raise ValueError('Existing formal session cannot be retried')
    root.mkdir();(root/'results').mkdir();(root/'candidates').mkdir()
    meta=dict(job=job,campaign=str(campaign),baseline=str(baseline),baseline_sha256=digest(baseline),protocol=str(campaign/'protocol.json'),
        started_monotonic=time.monotonic(),started_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write_json(root/'session.json',meta);prepare(root,meta)
    private=private_context(campaign,'workflow-ppa',job['id'])
    if private.exists():raise ValueError('Private model context must be fresh')
    with (root/'results/runner.log').open('w') as log:
        result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',str(root),'--private',str(private)],stdout=log,stderr=subprocess.STDOUT)
    target=root/'results/search-summary.json'
    if not target.exists():
        record=summarize(root,meta);record.update(runner_exit_code=result.returncode,workflow_state='infrastructure_aborted')
        write_json(target,record)
    print(json.dumps(dict(session=job['id'],runner_exit_code=result.returncode,summary=str(target))),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path);parser.add_argument('--baseline',type=Path);parser.add_argument('--session')
    parser.add_argument('--worker',type=Path);parser.add_argument('--private',type=Path)
    args=parser.parse_args()
    if args.worker:worker(args.worker,args.private)
    else:
        if not args.campaign or not args.baseline:parser.error('--campaign and --baseline required')
        protocol=json.loads((args.campaign/'protocol.json').read_text())
        jobs=[job for job in protocol['ppa_jobs'] if not args.session or job['id']==args.session]
        if not jobs:parser.error('Unknown frozen workflow session')
        for job in jobs:run_session(args.campaign,args.baseline,job)

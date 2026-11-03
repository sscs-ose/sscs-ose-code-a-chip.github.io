"""Fixed TaskGraph PPA searches with protected three-candidate budgets."""
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

from chip_nebula.taskgraph.domain import Artifact, ArtifactContent, ArtifactProducer, TaskBrief
from chip_nebula.taskgraph.static_cli import load_compiled_recipe, run_workflow
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from evaluate_study_physical import evaluate as evaluate_measurement
from run_study_physical import run as run_physical
from study_budget import BudgetPool
from study_isolation import prepare_credentials
from study_protocol import BASELINE, MODEL, config_tuple, digest, ranking, rule_candidate, write_json

CASE = Path(__file__).resolve().parents[1]


def verify_sources(experiment):
    bindings = json.loads((experiment/'ppa/source-bindings.json').read_text())
    for name, expected in bindings.items():
        if Path(name).name != name or digest(CASE/'scripts'/name) != expected:
            raise ValueError('Frozen PPA helper changed: ' + name)


PROPOSER = '''You are the PPA implementation optimizer for one frozen CPU+NPU.
Read context/baseline.json and context/protocol.json. Inspect the immutable
feedback evaluation report/history before every subsequent proposal. Choose
one previously untried tuple in the frozen parameter domain. The circuit RTL,
clock, libraries and acceptance thresholds cannot change. No extra EDA calls,
screening searches, models or agents are allowed. Only the independent tool
evaluator executes hardware implementation. Explain the decision using the
actual available reports, and minimize the qualified area-times-energy score.
Write proposal/candidate.json containing exactly configuration (the four
parameter keys) and rationale (string). Write only proposal/ and optional
build/ notes. End with NEBULA_OUTPUT: {"candidate":{"configuration":{...},
"rationale":"your report-grounded explanation"}} with matching file/payload.
After review rejection, repair this proposal without changing permissions.
There are at most three new physical candidates and all AI roles together
have 1200 seconds; EDA waiting is outside that agent budget.
'''
REVIEWER = '''Independently review this PPA proposal against context/protocol.json,
the common baseline, and captured candidate/evaluation artifacts under
.nebula_inputs/. Check its exact parameter tuple, previous trials in this
session, interpretation of actual timing/electrical/power evidence, and that
it preserves frozen RTL, constraints and acceptance. Do not invent results
or run EDA/model calls. Reject an invalid or unsupported proposal with
actionable feedback; otherwise permit the experiment to measure it. The
optimizer alone owns proposal changes. Write only reports/review.json and
optional build/ notes. Return NEBULA_OUTPUT: {"report":{"subject":"candidate",
"verdict":"passed or failed","repair_summary":"concrete explanation"}}.
Select one real verdict, never the placeholder string. Your time and Tokens
are part of the same 1200-second budget as the optimizer.
'''


def git(root, *arguments):
    return subprocess.run(['git', *arguments], cwd=root, text=True, capture_output=True, check=True).stdout.strip()


def session_metadata():
    root = Path(os.environ['CHIP_PPA_SESSION']).resolve()
    document = json.loads((root/'session.json').read_text())
    return root, document


def history(root, metadata):
    baseline = Path(metadata['baseline'])
    if digest(baseline) != metadata['baseline_sha256']:
        raise ValueError('Common baseline evidence changed')
    return [json.loads(baseline.read_text()),
            *[json.loads(path.read_text()) for path in sorted((root/'candidates').glob('*/evaluation.json'))]]


def validate_configuration(configuration, observations):
    selected = config_tuple(configuration)
    if selected in {config_tuple(row['configuration']) for row in observations}:
        raise ValueError('Previously tried configuration; choose another frozen-domain tuple')


def proposal_file(workspace):
    path = workspace/'proposal/candidate.json'
    if path.is_symlink() or path.stat().st_size > 65536:
        raise ValueError('Invalid candidate file')
    document = json.loads(path.read_text())
    if set(document) != {'configuration', 'rationale'} or not isinstance(document['rationale'], str):
        raise ValueError('Candidate file needs configuration and a string rationale')
    return document


def captured_candidate(root):
    project = root/'project'
    with StaticTaskGraphStore(project/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        attempt = store.active_attempt('ppa-search:evaluator')
        if attempt is None:
            raise ValueError('No active evaluation Attempt owns this invocation')
        document = store.get_artifact(attempt.input_deliveries['candidate']).document()
    if document['type'] != 'ppa.candidate':
        raise ValueError('Captured formal input has the wrong type')
    blob = git(project,'show',document['content']['commit']+':proposal/candidate.json')
    content = json.loads(blob)
    if content != {key: document['payload'][key] for key in ('configuration','rationale')}:
        raise ValueError('Candidate file and final Artifact payload disagree')
    return document


def evaluate_candidate(workspace):
    root, metadata = session_metadata()
    observations = history(root, metadata)
    captured = captured_candidate(root)
    configuration = captured['payload']['configuration']
    config_tuple(configuration)
    # Replay a completed publication, never launch the same captured input twice.
    for path in sorted((root/'candidates').glob('*/launch.json')):
        launch = json.loads(path.read_text())
        if launch['candidate_artifact'] == captured['id']:
            report = path.parent/'report.json'
            if report.exists(): return json.loads(report.read_text())
            raise ValueError('Interrupted physical candidate retained; explicit recovery is required')
    validate_configuration(configuration, observations)
    index = len(list((root/'candidates').glob('*/launch.json'))) + 1
    if index > 3: raise ValueError('Frozen three-candidate physical budget exhausted')
    slot = root/'candidates'/f'{index:02d}'
    slot.mkdir(parents=True, exist_ok=False)
    write_json(slot/'launch.json', {'candidate_artifact': captured['id'], 'candidate_digest': captured.get('digest'),
               'configuration': configuration, 'candidate_index': index,
               'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    run = slot/'physical'
    run_physical(run, Path(metadata['rtl_source']), configuration, 10526)
    measured = evaluate_measurement(run, Path(metadata['baseline']))
    measured['candidate_index'] = index
    measured['candidate_artifact'] = captured['id']
    measured['proposal_rationale'] = captured['payload']['rationale']
    measured['elapsed_search_seconds'] = (time.monotonic()-metadata['started_monotonic']) if 'started_monotonic' in metadata else None
    write_json(slot/'evaluation.json', measured)
    budget_path = root/'results/budget.json'
    used = json.loads(budget_path.read_text())['used_agent_seconds'] if budget_path.exists() else 0
    continuing = index < 3 and (metadata['job']['workflow'] == 'W0' or used < 1199)
    report = {'subject': captured['id'], 'verdict': 'passed' if measured['rank_eligible'] else 'failed',
              'continue_search': continuing, 'repair_summary': 'Choose the next untried configuration using the actual session history.',
              'candidate_index': index, 'history': [*observations, measured]}
    write_json(slot/'report.json', report)
    return report


def summarize_session(root, metadata):
    observations = history(root, metadata)
    candidates = observations[1:]
    eligible = [row for row in candidates if row['rank_eligible']]
    best = min(eligible, key=ranking) if eligible else None
    budget_path = root/'results/budget.json'
    budget = json.loads(budget_path.read_text()) if budget_path.exists() else {'used_agent_seconds': 0, 'dispatches': []}
    launches={int(path.parent.name):json.loads(path.read_text()) for path in (root/'candidates').glob('*/launch.json')}
    evaluated={row['candidate_index'] for row in candidates}
    return {'finished': True, 'job': metadata['job'], 'baseline': observations[0],
            'candidates': candidates, 'best_qualified_candidate': best,
            'physical_launches': len(launches), 'unused_candidate_slots': 3-len(launches),
            'slots':[{'candidate_index':index,'status':'evaluated' if index in evaluated else
                      'launched_incomplete' if index in launches else 'unused',
                      'launch':launches.get(index)} for index in range(1,4)], 'budget': budget,
            'scope': 'Search completion is independent of candidate engineering qualification; all failures retained'}


def tool_action(action, workspace):
    root, metadata = session_metadata()
    if action == 'validate':
        document = proposal_file(workspace)
        validate_configuration(document['configuration'], history(root,metadata))
        print('PPA_CANDIDATE_VALID'); return
    if action == 'propose':
        configuration, reason = rule_candidate(history(root, metadata))
        document = {'configuration': configuration, 'rationale': json.dumps(reason)}
        write_json(workspace/'proposal/candidate.json', document)
        payload = {'candidate': document}
    elif action == 'evaluate':
        report = evaluate_candidate(workspace)
        write_json(workspace/'build/evaluation/report.json', report)
        payload = {'report': report}
    elif action == 'finalize':
        result = summarize_session(root, metadata)
        write_json(root/'results/search-summary.json', result)
        payload = {'report': {'subject': metadata['job']['id'], 'verdict': 'passed',
                             'search_finished': True, 'candidate_count': len(result['candidates'])}}
        write_json(workspace/'build/session/report.json',payload['report'])
    else:
        raise ValueError('Unknown protected study tool action')
    print('NEBULA_OUTPUT: '+json.dumps(payload))


def prepare(root, metadata):
    project = root/'project'
    if project.exists(): raise ValueError('Existing session preserved')
    for name in ('context','proposal','reports','tools','.chip_nebula/roles','.chip_nebula/recipes','.chip_nebula/schemas'):
        (project/name).mkdir(parents=True,exist_ok=True)
    baseline = json.loads(Path(metadata['baseline']).read_text())
    if not baseline['rank_eligible']:
        raise ValueError('Common baseline must qualify before scored PPA searches')
    write_json(project/'context/baseline.json',baseline)
    write_json(project/'context/protocol.json',json.loads(Path(metadata['protocol']).read_text())['ppa'])
    role_info = {'ppa-proposer': (PROPOSER,['specification.source','ppa.evaluation.report','verification.report'],['ppa.candidate']),
                 'ppa-verifier': (REVIEWER,['specification.source','ppa.candidate'],['verification.report']),
                 'ppa-evaluator': ('Execute exactly one protected candidate and report all engineering failures.', ['ppa.candidate','verification.report'],['ppa.evaluation.report']),
                 'ppa-finalizer': ('Record search completion separately from engineering acceptance.', ['ppa.evaluation.report'],['ppa.session.report'])}
    for name,(prompt,accepted,produced) in role_info.items():
        (project/'.chip_nebula/roles'/f'{name}.yaml').write_text(yaml.safe_dump(
            dict(name=name,version=1,system_prompt=prompt,accepted_types=accepted,produced_types=produced,framework='codex',model=MODEL),sort_keys=False))
    schemas = {'ppa.candidate': {'configuration':'dict','rationale':'str'},
               'ppa.evaluation.report': {'subject':'str','verdict':'str','continue_search':'bool','history':'list','repair_summary':'str'},
               'ppa.session.report': {'subject':'str','verdict':'str','search_finished':'bool','candidate_count':'int'}}
    for name,fields in schemas.items():
        (project/'.chip_nebula/schemas'/f'{name}.yaml').write_text(yaml.safe_dump(
            dict(type=name,version=1,required_fields=fields,carries_engineering_verdict=name.endswith('.report')),sort_keys=False))
    (project/'tools/run_ppa.py').write_text('import os,sys\nfrom pathlib import Path\n'
        'python=os.environ["CHIP_STUDY_PYTHON"]\n'
        'if sys.executable!=python:os.execv(python,[python,__file__,*sys.argv[1:]])\n'
        'sys.path.insert(0,str(Path(os.environ["CHIP_STUDY_CASE"])/"scripts"))\n'
        'from run_ppa_workflow_study import tool_action\ntool_action(sys.argv[1],Path.cwd())\n')
    source={'type':'specification.source','from':'$parameters.source'}
    candidate={'type':'ppa.candidate','from':'$tasks.proposer.outputs.candidate'}
    tools=['python3','git']
    permission=lambda read,write:dict(read=read,write=write,tools=tools)
    proposer_execution=dict(executor='tool',command='python3 tools/run_ppa.py propose',timeout_seconds=30) if metadata['job']['workflow']=='W0' else dict(framework='codex',model=MODEL,reasoning_effort='high',timeout_seconds=1200)
    tasks={'proposer':dict(role='ppa-proposer',intent=PROPOSER,
        permission=permission(['context/**','proposal/**','reports/**','tools/**','build/**'],['proposal/**','build/**']),
        inputs={'source':source},outputs={'candidate':dict(type='ppa.candidate',paths=['proposal/**'])},
        execution=proposer_execution,max_attempts=12,
        gates=[dict(name='bounded-unseen-candidate',template='script-check',version=1,on_failure='retry',
                    parameters=dict(script='python3',arguments=['tools/run_ppa.py','validate'],expected='PPA_CANDIDATE_VALID',timeout=30,level='L1',error_class='invalid_ppa_candidate'))])}
    evaluation_inputs={'candidate':candidate}
    feedback=[]
    if metadata['job']['workflow']=='W2':
        tasks['reviewer']=dict(role='ppa-verifier',intent=REVIEWER,
            permission=permission(['context/**','proposal/**','reports/**','build/**'],['reports/**','build/**']),
            inputs={'source':source,'candidate':candidate},outputs={'report':dict(type='verification.report',paths=['reports/**'])},
            execution=dict(framework='codex',model=MODEL,reasoning_effort='high',timeout_seconds=1200),max_attempts=12)
        evaluation_inputs['review']={'type':'verification.report','from':'$tasks.reviewer.outputs.report','release':{'field':'verdict','equals':'passed'}}
        feedback.append(dict(source='reviewer',verdict='fail',target='proposer',kind='feedback',
                             summary='Repair the rejected PPA proposal.',summary_field='report.repair_summary',propagate=True))
    tasks['evaluator']=dict(role='ppa-evaluator',intent='Execute the captured immutable candidate under the protected physical budget.',
        permission=permission(['context/**','proposal/**','reports/**','tools/**','build/**'],['build/**']),inputs=evaluation_inputs,
        outputs={'report':dict(type='ppa.evaluation.report',paths=['build/evaluation/**'])},
        execution=dict(executor='tool',command='python3 tools/run_ppa.py evaluate',timeout_seconds=16500),max_attempts=3)
    tasks['finalizer']=dict(role='ppa-finalizer',intent='Record search completion and retain the best qualified result, if any.',on_demand=True,
        permission=permission(['tools/**','build/**'],['build/session/**']),
        inputs={'evaluation':{'type':'ppa.evaluation.report','from':'$tasks.evaluator.outputs.report'}},
        outputs={'report':dict(type='ppa.session.report',paths=['build/session/**'])},
        execution=dict(executor='tool',command='python3 tools/run_ppa.py finalize',timeout_seconds=30),max_attempts=1)
    for verdict in ('pass','fail'):
        for continuing,target in ((True,'proposer'),(False,'finalizer')):
            feedback.append(dict(source='evaluator',verdict=verdict,target=target,kind='feedback',
                summary='Continue bounded search.' if continuing else 'Record terminal search observations.',
                propagate=continuing,when={'field':'report.continue_search','equals':continuing}))
    recipe=project/'.chip_nebula/recipes/ppa-search.yaml'
    recipe.write_text(yaml.safe_dump(dict(name='bounded-ppa-search',version=2,parameters={'source':'specification.source'},tasks=tasks,feedback=feedback),sort_keys=False))
    (project/'.gitignore').write_text('.chip_nebula/\nbuild/\n__pycache__/\n*.pyc\n')
    for command in (('init','-q'),('config','user.name','ChipNebula study automation'),('config','user.email','automation@chipnebula.invalid'),
                    ('add','.'),('add','-f','.chip_nebula/roles','.chip_nebula/recipes','.chip_nebula/schemas'),('commit','-qm','Freeze bounded PPA session')):
        git(project,*command)
    commit,tree=git(project,'rev-parse','HEAD'),git(project,'rev-parse','HEAD^{tree}')
    compiled=load_compiled_recipe(recipe,workflow_id='ppa-search',goal='Compare bounded PPA decision workflows on one fixed circuit',
                                  parameters={'source':'ppa-context'},baseline_commit=commit,workers=1)
    content=(project/'context/protocol.json').read_text()
    artifact=Artifact(id='ppa-context',type='specification.source',schema_version=1,
        producer=ArtifactProducer('external','common-ppa-input','frozen-input','study-author',1),
        content=ArtifactContent('git',commit,tree,('context',)),
        payload=dict(source_name='Frozen physical optimization domain',media_type='application/json',content_digest='sha256:'+digest(project/'context/protocol.json'),
                     content=content,received_at='2026-10-16T00:00:00+00:00'))
    briefs={task.id:TaskBrief(objective=task.intent,deliverables=tuple(out.name+': '+out.artifact_type for out in task.outputs),
        responsibilities=('Use captured inputs and preserve actual reports, frozen targets and shared budgets.',),
        exclusions=('No RTL/checker/library edits, hidden EDA, external model calls or work from another session.',),
        completion_criteria=('Publish declared outputs with honest engineering verdicts.',),
        collaboration=tuple('task:'+other.id for other in compiled.tasks if other.id!=task.id)) for task in compiled.tasks}
    with StaticTaskGraphStore(project/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        store.create_workflow(compiled.workflow,compiled.roles,compiled.tasks,[artifact],compiled.joint_analysis_groups,compiled.feedback_routes)
        store.freeze_briefs('ppa-search',briefs)
    git(project,'update-ref','refs/chip-nebula/artifacts/ppa-context',commit)
    return compiled


def worker(root,private):
    root=root.resolve();metadata=json.loads((root/'session.json').read_text());project=root/'project'
    verify_sources(root.parents[1])
    os.environ.update(CHIP_PPA_SESSION=str(root),CHIP_STUDY_CASE=str(CASE),CHIP_STUDY_PYTHON=sys.executable)
    if metadata['job']['workflow'] != 'W0':
        prepare_credentials(private)
        wrappers=private/'wrapper';wrappers.mkdir(exist_ok=True)
        wrapper=wrappers/'codex'
        wrapper.write_text('#!'+sys.executable+'\nimport os,sys\nos.execv(sys.executable,[sys.executable,'+repr(str(CASE/'scripts/study_isolation.py'))+',*sys.argv[1:]])\n')
        wrapper.chmod(0o700)
        os.environ.update(CHIP_STUDY_PROJECT=str(project),CHIP_STUDY_PRIVATE_HOME=str(private),PATH=str(wrappers)+os.pathsep+os.environ['PATH'])
    pool=BudgetPool(root/'results/budget.json')
    status=run_workflow(project,project/'.chip_nebula/shared/memory/taskgraph-v2.db','ppa-search',pool,workers=1)
    result=summarize_session(root,metadata);result['workflow_state']=status.value
    from run_configuration_study import usage_and_repairs
    result['usage']=usage_and_repairs(private,root/'results',{}) if metadata['job']['workflow']!='W0' else {
        'tokens':dict.fromkeys(('input_tokens','cached_input_tokens','output_tokens','reasoning_output_tokens'),0),'model_sessions':0}
    write_json(root/'results/search-summary.json',result)


def run_session(experiment,baseline,job):
    root=experiment/'ppa'/job['id']
    if root.exists():raise ValueError('Existing session retained; inspect before recovery')
    root.mkdir(parents=True);(root/'results').mkdir();(root/'candidates').mkdir()
    metadata={'job':job,'baseline':str(baseline),'baseline_sha256':digest(baseline),
              'source_bindings_sha256':digest(experiment/'ppa/source-bindings.json'),
              'protocol':str(experiment/'protocol.json'),'rtl_source':str(CASE/'released_design'),
              'started_monotonic':time.monotonic(),'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    write_json(root/'session.json',metadata);prepare(root,metadata)
    private=Path('/tmp/chipnebula-ppa-study-user37-20261016')/job['id']
    if private.exists():raise ValueError('Prior private context retained; do not reuse a session')
    command=[sys.executable,str(Path(__file__).resolve()),'--worker',str(root),'--private',str(private)]
    with (root/'results/runner.log').open('w') as log:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        # Each Role and deterministic stage already owns its bounded timeout.
        process.wait()
    result=root/'results/search-summary.json'
    if not result.exists():
        failed=summarize_session(root,metadata);failed.update(runner_exit_code=process.returncode,workflow_state='inspect-preserved-runner-failure')
        write_json(result,failed)
    print(json.dumps({'session':job['id'],'runner_exit_code':process.returncode,'summary':str(result)}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--experiment',type=Path);p.add_argument('--baseline',type=Path)
    p.add_argument('--session');p.add_argument('--worker',type=Path);p.add_argument('--private',type=Path)
    args=p.parse_args()
    if args.worker:worker(args.worker,args.private)
    else:
        if not args.experiment or not args.baseline:p.error('--experiment and --baseline are required')
        experiment=args.experiment.resolve();baseline=args.baseline.resolve()
        verify_sources(experiment)
        plan=json.loads((experiment/'protocol.json').read_text())
        jobs=[job for job in plan['ppa']['sessions'] if not args.session or job['id']==args.session]
        if not jobs:p.error('Unknown preregistered session')
        for job in jobs:
            previous=experiment/'ppa'/job['id']/'results/search-summary.json'
            if previous.exists():continue
            run_session(experiment,baseline,job)

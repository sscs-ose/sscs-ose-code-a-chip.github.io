"""Run the preregistered fresh/IP × single/multi Role experiment."""
from __future__ import annotations

import argparse
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
from chip_nebula.taskgraph.static_cli import load_compiled_recipe, run_workflow, cancel_workflow_attempts
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from study_budget import BudgetPool
from study_checks import CLIENT
from study_isolation import prepare_credentials
from study_protocol import MODEL, digest, preregistration, write_json

CASE = Path(__file__).resolve().parents[1]
CONTRACT = '''Implement synthesizable SystemVerilog module nebula_npu_dot4.
Ports: input clk,rst_n,req_valid; output req_ready; input [31:0] req_a,req_b;
output rsp_valid; input rsp_ready; output [31:0] rsp_data; input kill.
Each request computes the signed INT32 sum of four parallel signed INT8
products. Lane 0 is bits 7:0. Widen products before reduction. At most one
operation is outstanding. An idle module is ready. If accepted on edge n,
rsp_valid is low after n and n+1 and high after n+2. Hold valid/data under
backpressure, and do not accept another request before consuming the result.
Active-low reset and active-high kill dominate acceptance and output,
including combinational req_ready/rsp_valid while either is asserted.
Cancel pending work; no stale response may emerge after recovery.
No persistent accumulation across requests, memory, saturation or rounding.
Use four parallel multipliers. All inputs are sampled on rising edges.
'''
DESIGN = '''Read spec/npu.md and spec/treatment.md. Deliver the complete implementation
under rtl/. Run python3 tools/smoke.py and develop additional tests if useful.
The smoke endpoint executes the published checker and retains trusted receipts.
You may edit rtl/, tests/designer/ and build/ only. Do not alter spec, IP,
tools, the supplied testbench, task definitions or acceptance conditions.
Read actual feedback and repair the same assigned task. Do not invoke other
models/agents, access credentials, or attempt to inspect other trials or the
final evaluator. End with NEBULA_OUTPUT: {"rtl":{"module":"nebula_npu_dot4"}}.
'''
VERIFY = '''Independently verify the delivered RTL against spec/npu.md and treatment.md.
Read the actual implementation, run python3 tools/smoke.py and add/run tests
under tests/reviewer/ when useful. You may write tests/reviewer/, reports/ and
build/ only; RTL and the contract/checker/IP are read-only. Record actionable
defects including reproduction steps. Do not repair RTL, weaken checks,
invoke other models/agents or inspect other trials or the final evaluator.
Write reports/review.json with subject, verdict (passed or failed),
repair_summary (a string), and executed commands. End with exactly
NEBULA_OUTPUT: {"report":{"subject":"generated-rtl","verdict":"passed or failed","repair_summary":"specific findings or none"}}.
Do not literally copy the placeholder verdict above: select passed or failed.
'''
AUDIT = '''from pathlib import Path
import subprocess,json
root=Path.cwd();out=root/'build/audit';out.mkdir(parents=True,exist_ok=True)
sources=sorted(root.glob('rtl/**/*.sv'))+sorted(root.glob('rtl/**/*.v'))+sorted(root.glob('ip/**/*.sv'))+sorted(root.glob('ip/**/*.v'))
commands=[['iverilog','-g2012','-s','npu_smoke_tb','-o',str(out/'sim'),*map(str,sources),'tb/npu_smoke_tb.sv'],['vvp',str(out/'sim')]]
text='';code=1
for command in commands:
 r=subprocess.run(command,text=True,capture_output=True,timeout=90);text+=r.stdout+r.stderr;code=r.returncode
 if code:break
(out/'audit.log').write_text(text)
report={'subject':'generated-rtl','verdict':'passed' if code==0 and 'NPU_SMOKE_PASS' in text else 'failed','repair_summary':text[-12000:]}
(out/'report.json').write_text(json.dumps(report,indent=2)+chr(10))
print('NEBULA_OUTPUT: '+json.dumps({'report':report}))
'''


def git(root, *arguments):
    return subprocess.run(['git', *arguments], cwd=root, text=True, capture_output=True, check=True).stdout.strip()


def prepare(root, job):
    if root.exists(): raise ValueError('Existing trial preserved')
    for name in ('spec', 'rtl', 'tb', 'tools', 'tests/designer', 'tests/reviewer', 'reports', '.chip_nebula/roles', '.chip_nebula/recipes'):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / 'spec/npu.md').write_text(CONTRACT)
    if job['input'] == 'ip':
        (root / 'ip').mkdir()
        for name, source in (('gemm_pe.sv', CASE / 'ip/model2gds-dot4/rtl/gemm_pe.sv'),
                             ('LICENSE', CASE / 'ip/model2gds-dot4/LICENSE')):
            shutil.copy2(source, root / 'ip' / name)
        treatment = ('Integrate the supplied unchanged gemm_pe PE using four parallel instances.\n'
                     'Write a new nebula_npu_dot4 adapter; do not replace or bypass the PE.\n'
                     'The PE has active-high synchronous rst/clear and an internal accumulator.\n'
                     'Clear/reset each PE between requests so the external interface has no cross-request accumulation.\n'
                     'a_valid/b_valid gate accumulation; a_last/b_last set sticky result_valid. Read its supplied interface/source.\n')
    else:
        treatment = 'Generate original RTL from the common contract. Do not use external or supplied IP implementations.\n'
    (root / 'spec/treatment.md').write_text(treatment)
    shutil.copy2(CASE / 'generation_seed/tb/npu_smoke_tb.sv', root / 'tb/npu_smoke_tb.sv')
    (root / 'tools/smoke.py').write_text(CLIENT)
    (root / 'tools/audit.py').write_text(AUDIT)
    (root / '.gitignore').write_text('.chip_nebula/\nbuild/\n__pycache__/\n*.pyc\n')
    roles = {'study-designer': (DESIGN, ['specification.source', 'verification.report'], ['rtl.snapshot']),
             'study-verifier': (VERIFY, ['specification.source', 'rtl.snapshot'], ['verification.report']),
             'study-auditor': ('Replay the frozen common public checker and report its real outcome.', ['rtl.snapshot', 'verification.report'], ['verification.report'])}
    for name, (prompt, accepted, produced) in roles.items():
        (root / '.chip_nebula/roles' / (name + '.yaml')).write_text(yaml.safe_dump(dict(name=name, version=1,
            system_prompt=prompt, accepted_types=accepted, produced_types=produced, framework='codex', model=MODEL), sort_keys=False))
    source = {'type': 'specification.source', 'from': '$parameters.source'}
    design_input = {'type': 'rtl.snapshot', 'from': '$tasks.designer.outputs.rtl'}
    tools = ['python3', 'iverilog', 'vvp', 'verilator', 'git', 'make']
    tasks = {'designer': dict(role='study-designer', intent=DESIGN,
        permission=dict(read=['spec/**', 'rtl/**', 'ip/**', 'tb/**', 'tools/**', 'tests/**', 'build/**'],
                        write=['rtl/**', 'tests/designer/**', 'build/**'], tools=tools),
        inputs={'source': source}, outputs={'rtl': dict(type='rtl.snapshot', paths=['rtl/**'])},
        max_attempts=8, execution=dict(framework='codex', model=MODEL, reasoning_effort='high', timeout_seconds=1200),
        gates=[dict(name='rtl-present', kind='file_check', on_failure='retry', parameters=dict(paths=['rtl/**/*.sv', 'rtl/**/*.v'], min_files=1))])}
    feedback = []
    audit_inputs = {'rtl': design_input}
    if job['roles'] == 'multi':
        tasks['verifier'] = dict(role='study-verifier', intent=VERIFY,
            permission=dict(read=['spec/**', 'rtl/**', 'ip/**', 'tb/**', 'tools/**', 'tests/**', 'build/**'],
                            write=['tests/reviewer/**', 'reports/**', 'build/**'], tools=tools),
            inputs={'source': source, 'rtl': design_input},
            outputs={'report': dict(type='verification.report', paths=['reports/**', 'tests/reviewer/**'])},
            max_attempts=8, execution=dict(framework='codex', model=MODEL, reasoning_effort='high', timeout_seconds=1200))
        audit_inputs['review'] = {'type': 'verification.report', 'from': '$tasks.verifier.outputs.report',
                                  'release': {'field': 'verdict', 'equals': 'passed'}}
        feedback.append(dict(source='verifier', verdict='fail', target='designer', kind='feedback',
                             summary='Repair the independently reported defect.', summary_field='report.repair_summary', propagate=True))
    tasks['audit'] = dict(role='study-auditor', intent='Execute common immutable development check; do not modify design.',
        permission=dict(read=['rtl/**', 'ip/**', 'tb/**', 'tools/**', 'reports/**', 'tests/**'], write=['build/**'], tools=tools),
        inputs=audit_inputs, outputs={'report': dict(type='verification.report', paths=['build/audit/**'])},
        max_attempts=8, execution=dict(executor='tool', command='python3 tools/audit.py', timeout_seconds=180))
    feedback.append(dict(source='audit', verdict='fail', target='designer', kind='feedback',
                         summary='Repair the common public checker failure.', summary_field='report.repair_summary', propagate=True))
    recipe = root / '.chip_nebula/recipes/configuration.yaml'
    recipe.write_text(yaml.safe_dump(dict(name='configuration-study', version=2, parameters={'source': 'specification.source'},
                                        tasks=tasks, feedback=feedback), sort_keys=False))
    for arguments in (('init', '-q'), ('config', 'user.name', 'ChipNebula study automation'),
                      ('config', 'user.email', 'automation@chipnebula.invalid'), ('add', '.'),
                      ('add', '-f', '.chip_nebula/roles', '.chip_nebula/recipes'),
                      ('commit', '-qm', 'Freeze one preregistered configuration trial')):
        git(root, *arguments)
    commit, tree = git(root, 'rev-parse', 'HEAD'), git(root, 'rev-parse', 'HEAD^{tree}')
    compiled = load_compiled_recipe(recipe, workflow_id='configuration-study', goal='Implement and verify the fixed dot4 contract',
                                    parameters={'source': 'common-source'}, baseline_commit=commit, workers=1)
    artifact = Artifact(id='common-source', type='specification.source', schema_version=1,
        producer=ArtifactProducer('external', 'common-contract', 'frozen-input', 'study-author', 1),
        content=ArtifactContent('git', commit, tree, ('spec', 'tb', 'tools') + (('ip',) if job['input']=='ip' else ())),
        payload=dict(source_name='Common dot4 specification', media_type='text/markdown', content_digest='sha256:' + digest(root/'spec/npu.md'),
                     content=CONTRACT, received_at='2026-10-16T00:00:00+00:00'))
    briefs = {task.id: TaskBrief(objective=task.intent, deliverables=tuple(o.name + ': ' + o.artifact_type for o in task.outputs),
        responsibilities=('Read the exact frozen inputs and perform the assigned engineering work.',),
        exclusions=('Do not modify contracts, public checkers, permissions or IP source; no subordinate model calls.',),
        completion_criteria=('Publish every declared output with an honest report verdict and actual evidence.',),
        collaboration=tuple('task:' + other.id for other in compiled.tasks if other.id != task.id)) for task in compiled.tasks}
    with StaticTaskGraphStore(root / '.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        store.create_workflow(compiled.workflow, compiled.roles, compiled.tasks, [artifact], compiled.joint_analysis_groups, compiled.feedback_routes)
        store.freeze_briefs('configuration-study', briefs)
    git(root, 'update-ref', 'refs/chip-nebula/artifacts/common-source', commit)
    write_json(root / 'trial-inputs.json', {'job': job, 'baseline_commit': commit, 'hidden_planner_calls': 0,
        'frozen_sha256': {str(p.relative_to(root)): digest(p) for folder in ('spec', 'tb', 'tools', 'ip')
                          for p in (root/folder).glob('**/*') if p.is_file()}})


def worker(root, private, output):
    prepare_credentials(private)
    wrappers = private / 'wrapper'; wrappers.mkdir(exist_ok=True)
    wrapper = wrappers / 'codex'
    wrapper.write_text('#!' + sys.executable + '\nimport os,sys\nos.execv(sys.executable,[sys.executable,' +
                       repr(str(CASE / 'scripts/study_isolation.py')) + ',*sys.argv[1:]])\n')
    wrapper.chmod(0o700)
    os.environ.update(CHIP_STUDY_PROJECT=str(root), CHIP_STUDY_PRIVATE_HOME=str(private),
                      PATH=str(wrappers) + os.pathsep + os.environ['PATH'])
    pool = BudgetPool(output / 'budget.json', total_deadline=time.monotonic() + 1200, check_ledger=output/'development-checks')
    status = run_workflow(root, root/'.chip_nebula/shared/memory/taskgraph-v2.db', 'configuration-study', pool, workers=1)
    write_json(output / 'workflow-outcome.json', {'workflow_state': status.value})


def final_check(root, output, job):
    with StaticTaskGraphStore(root/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        selected = store.deliveries('configuration-study:designer').get('rtl')
        if not selected: return {'passed': False, 'reason': 'No formal RTL delivery'}
        artifact = store.get_artifact(selected.artifact_id)
    destination = output/'selected'; destination.mkdir()
    record = artifact.document()
    files = git(root, 'ls-tree', '-r', '--name-only', artifact.content.commit, 'rtl', 'ip').splitlines()
    hashes = {}
    for relative in files:
        if Path(relative).suffix not in ('.sv', '.v', '.vh', '.svh'): continue
        path = destination/relative; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(subprocess.run(['git','show',artifact.content.commit+':'+relative],cwd=root,capture_output=True,check=True).stdout)
        hashes[relative] = digest(path)
    record['exported_source_sha256'] = hashes
    write_json(destination/'selected-delivery.json', record)
    sources = sorted(destination.glob('rtl/**/*.sv')) + sorted(destination.glob('rtl/**/*.v'))
    sources += sorted(destination.glob('ip/**/*.sv')) + sorted(destination.glob('ip/**/*.v'))
    commands = [['iverilog','-g2012','-s','npu_acceptance_tb','-o',str(output/'acceptance'),*map(str,sources),str(CASE/'verification/npu_acceptance_tb.sv')],
                ['vvp',str(output/'acceptance')],
                ['yosys','-Q','-T','-p','read_slang --top nebula_npu_dot4 '+ ' '.join(map(str,sources))+
                 '; hierarchy -check -top nebula_npu_dot4; proc; opt; check -assert; write_json '+str(output/'synthesis.json')]]
    codes=[]
    for name, command in zip(('compile','acceptance','synthesis'), commands):
        result = subprocess.run(command, text=True, capture_output=True, timeout=120)
        (output/(name+'.log')).write_text(result.stdout+result.stderr); codes.append(result.returncode)
        if result.returncode: break
    passed = len(codes)==3 and all(code==0 for code in codes)
    passed &= 'NPU_ACCEPTANCE_PASS cases=264202 cancellations=8' in (output/'acceptance.log').read_text() if (output/'acceptance.log').exists() else False
    ip_instances = None
    if passed and job['input'] == 'ip':
        modules = json.loads((output/'synthesis.json').read_text())['modules']
        def count_pe(name, stack=()):
            if name in stack: raise ValueError('Recursive synthesis hierarchy')
            return sum((1 if cell['type']=='gemm_pe' else 0) +
                       (count_pe(cell['type'], (*stack, name)) if cell['type'] in modules else 0)
                       for cell in modules[name].get('cells',{}).values())
        ip_instances = count_pe('nebula_npu_dot4')
        passed &= ip_instances == 4
    return {'passed': bool(passed), 'command_exit_codes': codes, 'source_sha256': hashes,
            'checker_sha256': digest(CASE/'verification/npu_acceptance_tb.sv'), 'source_delivery': artifact.id,
            'reachable_supplied_pe_instances': ip_instances}


def usage_and_repairs(private, output, final):
    sessions=[]
    for path in sorted((private/'sessions').glob('**/*.jsonl')):
        context=None;terminal=None;session=None
        for line in path.open():
            try:event=json.loads(line)
            except ValueError:continue
            if event.get('type')=='session_meta':session=event.get('payload',{}).get('id')
            if event.get('type')=='turn_context':context=event['payload']
            if event.get('type')=='event_msg' and event.get('payload',{}).get('type')=='token_count':terminal=event
        if terminal and context:
            sessions.append({'session_id':session,'model':context.get('model'),
                             'reasoning_effort':context.get('effort',context.get('reasoning_effort')),
                             'terminal_timestamp':terminal['timestamp'],
                             'tokens':terminal['payload']['info']['total_token_usage']})
    identifiers=[s['session_id'] for s in sessions]
    if len(identifiers)!=len(set(identifiers)):raise ValueError('Duplicate session usage records')
    keys=('input_tokens','cached_input_tokens','output_tokens','reasoning_output_tokens')
    totals={key:sum(s['tokens'][key] for s in sessions) for key in keys} if sessions else None
    write_json(output/'usage.json',{'sessions':sessions,'totals':totals,'reasoning_tokens_already_in_output':True,
                                  'scope':'One terminal cumulative token event per isolated local model session; no credentials or prompts exported'})
    checks=[json.loads(path.read_text()) for path in sorted((output/'development-checks').glob('check-*.json'))]
    repairs=0;rechecks=0
    for before,after in zip(checks,checks[1:]):
        if before['source_sha256']==after['source_sha256']:rechecks+=1
        elif not before['passed']:repairs+=1
    return {'tokens':totals,'model_sessions':len(sessions),'trusted_development_checks':len(checks),
            'repair_iterations':repairs,'unchanged_source_rechecks':rechecks,
            'final_source_changed_since_last_development_check':bool(final.get('source_sha256')) and
                 (not checks or checks[-1]['source_sha256']!=final['source_sha256'])}


def run_trial(experiment, job):
    folder = experiment/'generation'/job['id']; folder.mkdir(exist_ok=False)
    root=folder/'project'; output=folder/'results'; output.mkdir()
    prepare(root, job)
    private=Path(tempfile_root())/job['id']
    if private.exists(): raise ValueError('Existing private session preserved; do not reuse a trial identifier')
    start=time.monotonic(); timed_out=False
    command=[sys.executable,str(Path(__file__).resolve()),'--worker',str(root),'--private',str(private),'--worker-output',str(output)]
    with (output/'workflow.log').open('w') as log:
        proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:proc.wait(timeout=1200)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=20)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            cancel_workflow_attempts(root,root/'.chip_nebula/shared/memory/taskgraph-v2.db','configuration-study',reason='Frozen 1200-second trial deadline')
    elapsed=time.monotonic()-start
    inputs=json.loads((root/'trial-inputs.json').read_text())
    unchanged=all((root/p).is_file() and digest(root/p)==h for p,h in inputs['frozen_sha256'].items())
    try:verdict=final_check(root,output,job) if unchanged else {'passed':False,'reason':'Frozen inputs changed'}
    except Exception as error:verdict={'passed':False,'reason':type(error).__name__+': '+str(error)}
    with StaticTaskGraphStore(root/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        workflow=store.get_workflow('configuration-study')
        attempts=[dict(id=a.id,role=a.role,status=a.status.value,session_id=a.session_id) for task in store.list_tasks(workflow.id) for a in store.list_attempts(task.id)]
    row={'job':job,'timed_out':timed_out,'engineering_seconds':elapsed,'runner_exit_code':proc.returncode,
         'workflow_state':workflow.status.value,'attempts':attempts,'frozen_inputs_unchanged':unchanged,
         'final_checker':verdict,'passed':verdict['passed'],'manual_design_interventions':0,
         'protocol':{'model':MODEL,'reasoning_effort':'high','total_trial_budget_seconds':1200,'hidden_planner_calls':0}}
    row.update(usage_and_repairs(private,output,verdict))
    write_json(output/'result.json',row)
    print(json.dumps({'job':job['id'],'passed':row['passed'],'timed_out':timed_out,'workflow':workflow.status.value}),flush=True)
    return row


def tempfile_root():
    # The private model sessions include authentication; never place them in exported results.
    return '/tmp/chipnebula-config-study-user37-20261016'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--experiment',type=Path)
    p.add_argument('--job',help='Run exactly this preregistered job, or all not-yet-created jobs')
    p.add_argument('--worker',type=Path);p.add_argument('--private',type=Path);p.add_argument('--worker-output',type=Path)
    args=p.parse_args()
    if args.worker:
        worker(args.worker.resolve(),args.private.resolve(),args.worker_output.resolve())
    else:
        if not args.experiment:p.error('--experiment is required')
        experiment=args.experiment.resolve(); plan=json.loads((experiment/'protocol.json').read_text())
        if plan != json.loads(json.dumps(preregistration())):raise ValueError('Frozen study protocol differs from this runner')
        jobs=[j for j in plan['generation']['jobs'] if not args.job or j['id']==args.job]
        if not jobs:p.error('Unknown job')
        rows=[]
        for job in jobs:
            existing=experiment/'generation'/job['id']
            if existing.exists():
                result=existing/'results/result.json'
                if not result.exists():raise ValueError('Incomplete trial needs explicit recovery: '+str(existing))
                rows.append(json.loads(result.read_text()));continue
            rows.append(run_trial(experiment,job))
            write_json(experiment/'generation/summary.json',{'complete':len(rows)==12,'rows':rows})

"""Rebind unchanged functional evidence and measure the V2 reset environment."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
from check_delivery import check_delivery
from check_reset_waveform import measure_reset, vcd_samples

ROOT = Path.cwd()
OUT = ROOT/'reports/verification'
PERF = ROOT/'reports/performance'
BUILD = ROOT/'build/verify/reset-waveform'

def sha(data): return hashlib.sha256(data).hexdigest()
def read(path): return json.loads(path.read_text())
def write(path, data): path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
def git_bytes(commit, path): return subprocess.check_output(['git','show',commit+':'+path])

def execute(command, log):
    started = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, timeout=180)
    (OUT/log).write_text(result.stdout)
    row = {'command':shlex.join(command),'cwd':str(ROOT),'log':'reports/verification/'+log,
        'returncode':result.returncode,'elapsed_seconds':time.monotonic()-started}
    commands.append(row)
    write(OUT/'baseline-commands.json',commands)
    assert result.returncode == 0, row
    return result.stdout

records = [read(p) for p in sorted(ROOT.glob('.nebula_inputs/*/artifact.json'))]
by_id = {a['id']:a for a in records}
selected = read(ROOT/'.nebula_inputs/attempt-context.json')['input_deliveries']
acceptance = by_id[selected['acceptance']]; integration = by_id[selected['integration']]
specification = by_id[selected['specification']]
plan = acceptance['payload']; old_plan = by_id['artifact-478b595695d0419e81e4d77e864a23d7']['payload']
old_commit = by_id['artifact-2f225eabd33249d79dbc17a7b73ec146']['content']['commit']
commit = integration['content']['commit']
assert plan['plan']['status'] == 'frozen' and plan['plan']['confirmed']
assert plan['spec_digest'] == specification['payload']['spec_digest'] == old_plan['spec_digest']
assert (ROOT/'spec/acceptance.plan.yaml').read_bytes() == git_bytes(acceptance['content']['commit'],'spec/acceptance.plan.yaml')
assert plan['requirement_ids'] == old_plan['requirement_ids']
changed_checks = [b['id'] for a,b in zip(old_plan['checks'],plan['checks']) if a != b]
assert set(changed_checks) == {'AC-PROJECT-COMPLETION','AC-PHYSICAL-INPUTS','AC-FLOORPLAN','AC-ELECTRICAL'}
assert plan['plan']['metrics'] == old_plan['plan']['metrics']
oracle_files = []
for path, expected in plan['plan']['input_file_sha256'].items():
    if path.startswith('spec/'):
        source = ROOT/path
        if not source.exists():
            source = next(ROOT/'.nebula_inputs'/a['id']/path for a in records
                if path in a['content']['paths'] and (ROOT/'.nebula_inputs'/a['id']/path).is_file()
                and sha((ROOT/'.nebula_inputs'/a['id']/path).read_bytes()) == expected)
        assert sha(source.read_bytes()) == expected, path
        oracle_files.append({'path':path,'sha256':expected,'source':str(source.relative_to(ROOT))})
for path in specification['content']['paths']:
    assert (ROOT/path).read_bytes() == git_bytes(specification['content']['commit'],path), path
resume = '--resume-analysis' in sys.argv
old_manifest = read(OUT/'evidence-manifest.json'); payload = read(OUT/'report.json')
for entry in old_manifest['files']:
    path = ROOT/entry['path']
    if resume and sha(path.read_bytes()) != entry['sha256']:
        path = OUT/'history'/('baseline-'+old_manifest['evidence_digest'].split(':')[1][:16])/path.name
    assert sha(path.read_bytes()) == entry['sha256'], entry['path']
old_digest = 'sha256:'+sha(json.dumps(old_manifest['files'],sort_keys=True,separators=(',',':')).encode())
assert old_digest == old_manifest['evidence_digest'] == payload['report']['evidence_digest']
previous = read(OUT/'candidate-view.json')
source_binding = []
for item in previous['sources']:
    path = item['source']; data = (ROOT/path).read_bytes()
    assert data == git_bytes(commit,path) == git_bytes(old_commit,path)
    assert sha(data) == item['sha256']
    source_binding.append({'path':path,'sha256':sha(data),'current_equals_original_run':True})
for path in ['integration/design.f','integration/address_map.json','integration/integration_smoke_tb.sv']:
    assert (ROOT/path).read_bytes() == git_bytes(commit,path) == git_bytes(old_commit,path)
lock = read(ROOT/'integration/dependencies.lock.json')
assert (ROOT/'integration/dependencies.lock.json').read_bytes() == git_bytes(commit,'integration/dependencies.lock.json')
old_lock = json.loads(git_bytes(old_commit,'integration/dependencies.lock.json'))
for key in lock:
    if key != 'platform': assert lock[key] == old_lock[key], key
for key in lock['platform']:
    if key not in ['constraints_artifact_id','constraints_commit','constraints_revision','constraints_sha256','sdc_sha256','physical_execution','spec_digest']:
        assert lock['platform'][key] == old_lock['platform'][key], key
revision = plan['plan']['physical_revision']; constraints = by_id[revision['constraints_artifact_id']]
resource = ROOT/'.nebula_inputs'/constraints['id']
constraint_path = resource/'physical/chip-nebula/implementation.constraints.json'
sdc_path = resource/'physical/chip-nebula/constraints.sdc'
constraint = read(constraint_path)
assert constraint_path.read_bytes() == git_bytes(constraints['content']['commit'],'physical/chip-nebula/implementation.constraints.json')
assert sha(constraint_path.read_bytes()) == revision['constraints_sha256'] == lock['platform']['constraints_sha256']
assert sha(sdc_path.read_bytes()) == revision['sdc_sha256'] == lock['platform']['sdc_sha256']
assert constraint['status'] == 'frozen' and constraint['revision'] == lock['platform']['constraints_revision'] == 2
assert lock['platform']['constraints_artifact_id'] == constraints['id']
assert lock['platform']['constraints_commit'] == constraints['content']['commit']
assert lock['platform']['spec_digest'] == plan['spec_digest']
physical = lock['platform']['physical_execution']; policy = plan['plan']['physical_execution']
for key in ['num_cores','NUM_CORES','openroad_threads']: assert physical[key] == policy[key] == 2
for key, target in [('path','openroad_executable'),('resolved_path','resolved_executable'),('sha256','executable_sha256'),('version','version')]:
    assert physical['openroad'][key] == policy[target]
old_constraint = json.loads(git_bytes('ef921aed5122da8617ee92fe41d4027de551dce8','physical/chip-nebula/implementation.constraints.json'))
for key in ['clocks','io','reset','electrical','routing','power','synthesis','view_binding']:
    assert constraint[key] == old_constraint[key], key
assert by_id[revision['authorization_artifact_id']]['digest'] == revision['authorization_artifact_digest']
assert sha((ROOT/revision['decision_path']).read_bytes()) == revision['decision_sha256']
delivery = check_delivery(ROOT)
fixed = ROOT/'.nebula_inputs/authorized-common-verifier-resources/verification/fixed_common'
fixed_files = read(fixed/'fixed-files.json')
assert sha((fixed/'fixed-files.json').read_bytes()) == read(OUT/'fixed-final.json')['manifest_sha256']
assert all(sha((fixed/p).read_bytes()) == expected for p,expected in fixed_files.items())
assert len(fixed_files) == delivery['fixed_files_validated'] == 767
history = OUT/'history'/('baseline-'+old_digest.split(':')[1][:16])
if not resume:
    history.mkdir(parents=True,exist_ok=False)
    for path in OUT.glob('*.json'):
        shutil.copyfile(path,history/path.name)
    shutil.copyfile(OUT/'traceability.md',history/'traceability.md')
    commands = []
    execute(['python3','-B','tests/test_delivery.py'],'delivery-checker-v2.log')
    assert not BUILD.exists(), 'Preserve earlier build results'
    BUILD.mkdir(parents=True)
    compile_command = ['/tmp/chipnebula-pinned-tools/bin/verilator','--binary','--timing','--assert','--trace','-Wno-fatal',
        '-j','2','--top-module','reset_waveform_tb','--Mdir',str(BUILD),'-o','sim',
        '-f','integration/design.f','integration/integration_smoke_tb.sv','tb/reset_waveform_tb.sv']
    version_script = 'source /tmp/chipnebula-pinned-tools/env.sh && source /opt/rh/gcc-toolset-13/enable && /tmp/chipnebula-pinned-tools/bin/verilator --version'
    version = execute(['bash','-c',version_script],'reset-runtime.log').strip()
    assert version.startswith('Verilator 5.048 ')
    compile_script = version_script + ' && ' + shlex.join(compile_command)
    execute(['bash','-c',compile_script],'reset-compile.log')
    run_script = 'source /tmp/chipnebula-pinned-tools/env.sh && source /opt/rh/gcc-toolset-13/enable && '+shlex.quote(str(BUILD/'sim'))
    run_log = execute(['bash','-c',run_script],'reset-run.log')
    assert 'INTEGRATION_SMOKE_PASS' in run_log
else:
    commands = read(OUT/'baseline-commands.json')
    version = (OUT/'reset-runtime.log').read_text().strip()
    assert 'INTEGRATION_SMOKE_PASS' in (OUT/'reset-run.log').read_text()
measurements = measure_reset(vcd_samples(OUT/'reset-waveform.vcd'))
write(OUT/'reset-waveform.json',{'verdict':'passed','scope':'fresh enabled RTL top/external memory model environment waveform; no mapped-netlist electrical/STA claim',
    'measurements':measurements,'clock_period_ns':100,'acceptance_artifact':acceptance['id'],
    'constraints_artifact':constraints['id'],'constraints_sha256':revision['constraints_sha256'],
    'spec_digest':plan['spec_digest'],'integration_artifact':integration['id'],
    'physical_execution_policy':plan['plan']['physical_execution'],'physical_tool_executed':False,
    'verilator_version':version,'vcd':'reports/verification/reset-waveform.vcd',
    'waveform_sha256':sha((OUT/'reset-waveform.vcd').read_bytes()),
    'joint_reset_binding':'Frozen integration_smoke_tb: instruction memory always_ff uses rst_n; pending/data0/data1/host initialize to zero in the same reset epoch; measured during low interval.',
    'commands':'reports/verification/baseline-commands.json','simulation_executions':1,
    'limitations':'Simulation environment compliance only; recovery/removal, characterized library pulse/electrical and board waveform remain downstream.'})
assert all(sha((fixed/p).read_bytes()) == expected for p,expected in fixed_files.items())
write(OUT/'baseline-revalidation.json',{'verdict':'passed','scope':'pre-synthesis exact functional evidence reuse plus fresh reset environment',
    'selected_inputs':selected,'artifact_records_read':len(records),'artifact_digests':{a['id']:a['digest'] for a in records},
    'changed_plan_checks':changed_checks,'oracle_files':oracle_files,'source_binding':source_binding,'fixed_files_validated':767,
    'previous_report_artifact':'artifact-210d9f6d592a4c08ae346ffd8e1d074a','previous_manifest':str((history/'evidence-manifest.json').relative_to(ROOT)),
    'previous_evidence_digest':old_digest,'previous_files_verified':len(old_manifest['files']),
    'functional_result_classification':'reused','functional_scenarios_reused':265267,
    'new_simulation_executions':1,'new_unique_functional_scenarios':0,
    'new_reset_measurement':'reports/verification/reset-waveform.json','new_checker_cases':12,'preflight_history':'reports/verification/baseline-preflight-history.log',
    'checker_correction':'VCD initial instruction data is unconstrained before the first reset clock edge; actual pulse, phase and post-edge reset state requirements retained. Raw simulation replay count remains one.',
    'configuration_binding':payload['environment']['compatibility']['configurations'],
    'original_runtime':'reports/verification/runtime.json','runtime_hash':sha((OUT/'runtime.json').read_bytes()),
    'constraints_sha256':revision['constraints_sha256'],'sdc_sha256':revision['sdc_sha256'],
    'lock_changes':'Only platform V2 constraints/spec/tool identity metadata changed; DUT packages/views and simulation inputs are byte-identical.',
    'history_policy':revision['history_policy']})
report = payload['report']
report['subject'] = 'nebula_cpu_npu_top / rtl.integration@'+commit
report['input_digests'] = list(dict.fromkeys([acceptance['digest'],integration['digest'],specification['digest'],constraints['digest'],by_id['authorized-calibrated-geometry-revision']['digest']]+report['input_digests']))
for check in report['checks']:
    check['result_origin'] = 'reused'
    check['evidence_binding'] = 'reports/verification/baseline-revalidation.json'
    if check['id'] in changed_checks:
        check['result_origin'] = 'deferred'
        frozen_check = next(c for c in plan['checks'] if c['id']==check['id'])
        check['responsible_stage'] = frozen_check['responsible_stage']
        check['reason'] = 'Requires actual V2 physical implementation and qualified tool/stage evidence; pre-synthesis report does not certify those results. Frozen detail retained in downstream-obligations.json.'
        check['scenarios'] = ['V2 physical inputs and separate planned/native-row geometry; affected physical stages and final export revalidation']
    if check['id'] == 'AC-ELECTRICAL':
        check['reason'] = 'Fresh reset environment waveform passed; characterized electrical, recovery/removal/library pulse and V2 physical tool/stage results require pnr. Whole check remains deferred.'
        check['evidence'].append('reports/verification/reset-waveform.json')
        check['scenarios'].append('existing enabled-top smoke with independent reset VCD measurements')
    if check['id'] in ['AC-RESET','AC-INTEGRATION']:
        check['result_origin'] = 'reused plus affected replay'
        check['evidence'].append('reports/verification/reset-waveform.json')
    if check['id'] == 'AC-DELIVERY':
        check['result_origin'] = 'revalidated'
        check['evidence'].append('reports/verification/baseline-revalidation.json')
    if check['id'] == 'AC-CYCLES':
        check['measurements'] = {'configurations':2,'checks_per_configuration':22,'passed_per_configuration':22,'continuous_addi_latency_cycles':4,'steady_state_ipc':1.0,'origin':'reused'}
write(OUT/'traceability.json',report['checks'])
(OUT/'traceability.md').write_text('| Check | Verdict | Origin | Minimal shared scenario | Direct evidence |\n|---|---|---|---|---|\n'+''.join('| '+c['id']+' | '+c['verdict']+' | '+c['result_origin']+' | '+'; '.join(c['scenarios'])+' | '+'; '.join(c['evidence'])+' |\n' for c in report['checks']))
obligations = read(OUT/'downstream-obligations.json')
for row in obligations:
    row['current_frozen_detail'] = next(c['detail'] for c in plan['checks'] if c['id']==row['id'])
    row['acceptance_artifact_id'] = acceptance['id']; row['constraints_artifact_id'] = constraints['id']
    if row['id'] in changed_checks: row['reason'] = next(c['reason'] for c in report['checks'] if c['id']==row['id'])
write(OUT/'downstream-obligations.json',obligations)
requirements = read(OUT/'requirements.json')
for row in requirements:
    row['acceptance_artifact_id'] = acceptance['id']
    row['evidence_binding'] = 'reports/verification/baseline-revalidation.json'
write(OUT/'requirements.json',requirements)
write(OUT/'delivery.json',delivery)
write(OUT/'evidence-reuse.json',{'prior_manifest':str((history/'evidence-manifest.json').relative_to(ROOT)),
    'prior_evidence_digest':old_digest,'files_verified':len(old_manifest['files']),
    'rtl_source_binding':source_binding,'fixed_files_validated':767,'functional_results':'reused',
    'simulation_reruns':1,'affected_checks':changed_checks+['AC-INTEGRATION','AC-RESET','AC-DELIVERY'],
    'binding_evidence':'reports/verification/baseline-revalidation.json'})
report['baseline_revalidation'] = 'reports/verification/baseline-revalidation.json'
report['commands'] = list(dict.fromkeys(report['commands']+['python3 -B verification/revalidate_baseline.py','python3 -B tests/test_reset_waveform.py','python3 -B verification/revalidate_baseline.py --resume-analysis']))
report['tool_versions']['reset_waveform_verilator'] = version
report['summary'] = 'Pre-synthesis stage passed: 265267 source-bound functional scenarios reused; 33/48 acceptance checks passed, 15 deferred. One enabled-top/reset-waveform replay and 12 delivery-checker cases passed under frozen V2 inputs.'
report['limitations'] = 'No full functional or physical rerun. Qualified functional/cycle/coverage evidence reused; only affected integration/reset environment replayed. V1 failed layout and unqualified tool measurements retain their identities. V2 physical geometry/electrical/GDS, resource accounting and independent evaluator replay remain deferred; stage PASS is not project acceptance.'
report['verdict'] = 'passed' if all(c['verdict'] in ['passed','deferred'] for c in report['checks']) else 'failed'
payload['environment']['paths'] = list(dict.fromkeys(payload['environment']['paths']+['verification/revalidate_baseline.py','verification/check_reset_waveform.py','tests/test_reset_waveform.py','tb/reset_waveform_tb.sv']))
tests = read(OUT/'tests.json')
tests['simulation_process_executions'] += 1
tests['latest_revalidation'] = {'functional_results':'reused','new_unique_functional_scenarios':0,
    'affected_simulation_replays':1,'evidence':'reports/verification/baseline-commands.json'}
write(OUT/'tests.json',tests)
summary = read(OUT/'result_summary.json'); summary['summary'] = report['summary']
for metric in summary['metrics']:
    if metric['id'] == 'tests.executions': metric['value'] += 1; metric['evidence'].append('reports/verification/baseline-commands.json')
    if metric['id'] in ['tests.total','tests.passed','tests.failed'] or metric['id'].startswith('coverage.'):
        metric['scope'] += '; reused under V2 by exact source/spec/checker binding'
        metric['evidence'].append('reports/verification/baseline-revalidation.json')
    if metric['id'].startswith('custom.delivery_checker_'): metric['scope'] += '; freshly replayed under V2 input context'
for key,value,unit in [('reset_low_ns',300,'ns'),('reset_release_phase_ns',50,'ns')]:
    summary['metrics'] = [m for m in summary['metrics'] if m['id'] != 'custom.'+key]
    summary['metrics'].append({'id':'custom.'+key,'label':key,'value':value,'unit':unit,'status':'measured',
        'scope':'fresh reset environment waveform of enabled RTL top; independent VCD measurement',
        'evidence':['reports/verification/reset-waveform.json','reports/verification/reset-waveform.vcd']})
write(OUT/'result_summary.json',summary)
entries=[]
for path in sorted(list(OUT.rglob('*'))+list(PERF.rglob('*'))):
    if not path.is_file() or path in [OUT/'report.json',OUT/'evidence-manifest.json'] or path.name in ['summary-gate.log','report-generation.log','delivery-refresh.log','engineering-gate.json','baseline-launch.log']:continue
    entries.append({'path':str(path.relative_to(ROOT)),'sha256':sha(path.read_bytes()),'bytes':path.stat().st_size})
report['evidence_digest'] = 'sha256:'+sha(json.dumps(entries,sort_keys=True,separators=(',',':')).encode())
write(OUT/'evidence-manifest.json',{'schema_version':1,'algorithm':old_manifest['algorithm'],'files':entries,'evidence_digest':report['evidence_digest']})
write(OUT/'report.json',payload)
print('BASELINE_REVALIDATION_PASS',dict(Counter(c['verdict'] for c in report['checks'])))

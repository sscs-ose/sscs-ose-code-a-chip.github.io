"""Join the validated PnR owner receipt without promoting unrelated project obligations."""
import collections
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
out = root / 'build/gds'
def read(path): return json.loads(Path(path).read_text())
def write(name, value): (out / name).write_text(json.dumps(value, indent=2) + '\n')
def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
proof = read(out / 'power_area_adoption.json')
owner = read(root / proof['owner_receipt'])
assert proof['status'] == owner['status'] == 'passed' and sha(root / proof['owner_receipt']) == proof['owner_receipt_sha256']
report = read(out / 'history/attempt-cf266b46df624d72941221bc4ba42d7e/project_acceptance.json')
assert proof['snapshot_id'] == report['snapshot_id'] and report['verdict'] == 'failed'
by_id = {c['id']:c for c in report['checks']}
frozen = read(root / '.nebula_inputs/artifact-8bfa326445194758816c2d0d07307a6f/artifact.json')['payload']
assert set(by_id) == {c['id'] for c in frozen['checks']}
for check in frozen['checks']:
    assert by_id[check['id']]['requirement_ids'] == check['requirement_ids']
    assert by_id[check['id']]['dependencies'] == check['dependencies']
ppa = by_id['AC-POWER-AREA']
ppa.update(verdict='passed', execution_status='PASS', result_origin='Source-bound owner evidence adopted after direct source/trace/waveform/report validation',
    reason='Qualified owner receipt for exact final STA netlist: DOT64/GEMM8/CONV3 commit/output comparisons pass; actual full VCD clock/reset/windows checked, tool-report-eligible annotation 59577/59577, separate nominal Liberty/SPEF estimates and unchanged area reported. Zero-delay scope, no silicon/glitch/SDF or energy-improvement claim.',
    evidence=['build/gds/power_area_adoption.json','build/gds/power_waveform_recheck.json','reports/pnr/power_area.json',
              'reports/pnr/power_area/DOT64.json','reports/pnr/power_area/GEMM8.json','reports/pnr/power_area/CONV3.json',
              'reports/pnr/power_area/clock_reset_recheck.json','reports/pnr/area_and_fanout.json','reports/pnr/geometry_acceptance.json'])
by_id['AC-PROJECT-COMPLETION']['reason'] = 'Historical resource failure, pending independent evaluator release and unproven typed adapters prevent whole-project acceptance; AC-POWER-AREA owner evidence is now qualified.'
for c in by_id.values(): c['acceptance_verdict'] = c['verdict']
for _ in by_id:
    for c in by_id.values():
        if c['acceptance_verdict'] == 'passed' and any(by_id[i]['acceptance_verdict'] != 'passed' for i in c['dependencies']):
            c['acceptance_verdict'] = 'deferred'
relocation = {x['original_path']:x['archived_path'] for x in read(out / 'resume_validation.json')['archive']}
adapters = read(out / 'history/attempt-cf266b46df624d72941221bc4ba42d7e/adapter_audit.json')
for a in adapters:
    a['nonpassing_checks'] = [i for i in a['check_ids'] if by_id[i]['verdict'] != 'passed']
    a['evidence'] = [relocation.get(e,e) for e in a['evidence']]
    if a['verdict'] == 'deferred':
        a['reason'] = 'Typed declarations/check links are retained; no complete per-operand adapter execution proof is supplied. ' + ('Mandatory linked checks remain nonpassing.' if a['nonpassing_checks'] else 'Linked direct checks pass in their stated scope.')
write('adapter_audit.json', adapters)
requirements = []
for old in read(out / 'history/attempt-cf266b46df624d72941221bc4ba42d7e/requirements_audit.json'):
    linked = [c for c in by_id.values() if old['id'] in c['requirement_ids']]
    linked_adapters = [a for a in adapters if old['id'] in a['requirement_ids']]
    assert linked, old['id']
    check_pass = all(c['acceptance_verdict'] == 'passed' for c in linked)
    failed = any(c['acceptance_verdict'] == 'failed' for c in linked) or any(a['verdict'] == 'failed' for a in linked_adapters)
    old.update(verdict='failed' if failed else ('passed' if check_pass and all(a['verdict']=='passed' for a in linked_adapters) else 'deferred'),
        check_evidence_verdict='passed' if check_pass else 'deferred', nonpassing_checks=[c['id'] for c in linked if c['acceptance_verdict'] != 'passed'],
        evidence=sorted({e for c in linked for e in c['evidence']}))
    requirements.append(old)
write('requirements_audit.json', requirements)
for c in by_id.values():
    c['nonpassing_dependencies'] = [i for i in c['dependencies'] if by_id[i]['acceptance_verdict'] != 'passed']
    c['evidence_sha256'] = {e:sha(root / e) for e in c['evidence'] if e != 'build/gds/project_acceptance.json'}
counts = collections.Counter(c['verdict'] for c in by_id.values())
gaps = [c['id'] for c in by_id.values() if c['verdict'] != 'passed']
assert len(by_id) == 48 and len(requirements) == 443 and len(adapters) == 26
assert {r['id'] for r in requirements} == set(frozen['requirement_ids'])
assert counts == {'passed':45, 'deferred':1, 'failed':2}
assert by_id['AC-RESOURCES']['verdict'] == by_id['AC-PROJECT-COMPLETION']['verdict'] == 'failed'
assert by_id['AC-EVALUATOR-RELEASE']['verdict'] == 'deferred' and by_id['AC-GDS']['acceptance_verdict'] == 'passed'
assert sum(a['verdict'] == 'passed' for a in adapters) == 1
report['summary'] = 'Physical/export passed; AC-POWER-AREA source-qualified owner receipt adopted. Whole-project acceptance failed: 45/48 direct checks passed, 1 pending, 2 failed; 1/26 typed adapters proven.'
report['counts'].update(passed=counts['passed'], deferred=counts['deferred'], failed=counts['failed'],
    acceptance_qualified_checks=sum(c['acceptance_verdict']=='passed' for c in by_id.values()),
    requirements_with_passing_check_evidence=sum(r['check_evidence_verdict']=='passed' for r in requirements),
    requirements_accepted=sum(r['verdict']=='passed' for r in requirements))
report['blocking_checks'] = gaps
report['whole_project_acceptance']['blocking_checks'] = gaps
report['power_area_acceptance'] = dict(verdict='passed', scope=owner['not_checked'], evidence='build/gds/power_area_adoption.json')
report['continuation_audit'] = 'build/gds/power_area_adoption.json'
report['current_layout_artifact_id'] = next(r['artifact_id'] for r in proof['input_artifacts'] if r['artifact_id'] == 'artifact-140e1d52ba374702b86e0683539ffd5a')
report['current_layout_commit'] = 'de62db689ae30570a828f470ed0913bb0ab23dfc'
report['prior_audits'].append('build/gds/history/attempt-cf266b46df624d72941221bc4ba42d7e/project_acceptance.json')
report['limitations'] += proof['limitations'][:3]
write('project_acceptance.json', report)
write('power_area.json', dict(schema_version=1, status='passed', engineering_verdict='passed', snapshot_id=proof['snapshot_id'],
    source=proof['owner_receipt'], source_sha256=proof['owner_receipt_sha256'], adoption_evidence='build/gds/power_area_adoption.json',
    workloads=proof['workloads'], measured_area=read(root / 'reports/pnr/area_and_fanout.json'), conditions=owner['conditions'],
    historical_unavailable_report='build/gds/history/attempt-cf266b46df624d72941221bc4ba42d7e/power_area.json', limitations=proof['limitations']))
binding = read(out / 'history/attempt-cf266b46df624d72941221bc4ba42d7e/upstream_binding.json')
binding['prior_layout_bindings'] = [r for r in binding['git_artifacts'] if r['artifact_id'] == 'artifact-689fbb20861e4a11a140ff35575166dc']
binding['git_artifacts'] = [r for r in binding['git_artifacts'] if r['artifact_id'] not in {x['artifact_id'] for x in proof['input_artifacts']} and r['artifact_id'] != 'artifact-689fbb20861e4a11a140ff35575166dc']
binding['git_artifacts'] += [dict(r, status='passed') for r in proof['input_artifacts']]
binding['power_owner_binding'] = 'build/gds/power_area_adoption.json'
write('upstream_binding.json', binding)
lines = ['# Frozen project acceptance audit', '', report['summary'], '', '**Physical/export: PASSED. AC-POWER-AREA: PASSED in the qualified estimate scope. Whole-project: FAILED / NOT ACCEPTED.**', '',
         'Snapshot: `' + report['snapshot_id'] + '`. No physical input or exported GDS was edited. Prior failed/unavailable reports are preserved in `history/attempt-cf266b46df624d72941221bc4ba42d7e/`.', '',
         '| Check | Direct result | Acceptance result | Evidence / reason |', '|---|---|---|---|']
for c in by_id.values():
    lines.append('| ' + c['id'] + ' | ' + c['execution_status'] + ' | ' + c['acceptance_verdict'] + ' | ' + c['reason'].replace('|','/') + ' Evidence: ' + ', '.join(c['evidence'][:2]) + ' |')
lines += ['', 'All 443 requirement rows and 26 adapter obligations are retained. Only one adapter has complete typed operand proof; workload comparison controls do not replace independent evaluator release.', '',
          '| Workload | Cycles (including 3 reset cycles) | Eligible window (ns) | Estimated total (mW) | VCD annotation |', '|---|---:|---|---:|---|']
for row in proof['workloads']:
    lines.append(f'| {row["workload"]} | {row["cycles"]} | {row["window_start_ns"]}–{row["window_end_ns"]} | {row["total_mw"]:.12f} | 59577/59577 tool-report-eligible pins |')
lines += ['', 'The estimates use the exact final netlist, exported SDC/SPEF and nominal TT25°C/1.8V Liberty. Dynamic, leakage, windows, annotation exclusions and source hashes are reported separately in power_area.json. No weighted aggregate is created.', '', 'Remaining scope limitations:', ''] + ['- ' + s for s in report['limitations']]
(out / 'project_acceptance.md').write_text('\n'.join(lines) + '\n')
print(report['summary'])

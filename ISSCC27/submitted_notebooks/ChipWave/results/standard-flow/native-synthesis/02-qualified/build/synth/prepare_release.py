import hashlib, json, subprocess
from pathlib import Path
from chip_nebula.taskgraph.artifacts import ArtifactValidationError, default_schema_registry

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/synthesis'
failure = json.loads((ROOT / '.nebula_inputs/attempt-148657862513458dba28e71a66de4c52/failure.json').read_text())
for name in failure['readable_wip_paths']:
    saved = subprocess.check_output(['git', 'show', failure['workspace_commit'] + ':' + name], cwd=ROOT)
    assert (ROOT / name).read_bytes() == saved, name
verification = json.loads((ROOT / '.nebula_inputs/artifact-210d9f6d592a4c08ae346ffd8e1d074a/artifact.json').read_text())
assert verification['payload']['verdict'] == 'passed'
assert json.loads((ROOT / 'reports/verification/report.json').read_text())['report']['verdict'] == 'passed'
summary = json.loads((OUT / 'result_summary.json').read_text())
assert isinstance(summary, dict)
metrics = {m['id']: m for m in summary['metrics']}
setup = metrics['timing.setup_slack']
assert setup['status'] == 'measured' and setup['value'] >= 0
report = json.loads((OUT / 'report.json').read_text())
netlist_sha = hashlib.sha256((ROOT / report['netlist']).read_bytes()).hexdigest()
assert netlist_sha == report['netlist_sha256']
command = ['/tmp/chipnebula-public-repro-user37/bin/python', '-m', 'chip_nebula.taskgraph.result_summary', 'reports/synthesis/result_summary.json', '--profile', 'synthesis', '--required', 'design.cell_area', '--required', 'design.macro_count', '--required', 'design.standard_cell_count', '--required', 'timing.hold_slack', '--required', 'timing.setup_slack', '--measured', 'design.standard_cell_count', '--measured', 'design.cell_area', '--measured', 'design.macro_count']
with (OUT / 'release_summary_gate.log').open('w') as log:
    gate = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=30)
assert gate.returncode == 0
previous = json.loads(failure['execution_log'].split('NEBULA_OUTPUT: ', 1)[1].split('\nTASK COMPLETED.', 1)[0])
payload = previous['netlist']
registry = default_schema_registry()
# Test types using the real saved WIP identity; the platform injects the final identity.
identity = dict(commit=failure['workspace_commit'], paths=failure['readable_wip_paths'])
try:
    registry.validate('netlist', 1, dict(payload, **identity))
except ArtifactValidationError as error:
    assert str(error) == 'result_summary must be an object', str(error)
else:
    raise AssertionError('Regression: original malformed payload was accepted')
payload['result_summary'] = summary
registry.validate('netlist', 1, dict(payload, **identity))
assert 'commit' not in payload and 'paths' not in payload
output = json.loads(json.dumps(dict(netlist=payload)))
assert output['netlist']['result_summary'] == summary
(OUT / 'release_payload.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
(OUT / 'release_revalidation.json').write_text(json.dumps(dict(verdict='passed', repair='Only output construction: embed complete parsed result_summary object instead of a path string.', preserved_wip_files=len(failure['readable_wip_paths']), saved_wip_commit=failure['workspace_commit'], netlist_sha256=netlist_sha, synthesis_rerun=False, sta_rerun=False, gates=[dict(name='synthesis-result-summary', exit_code=gate.returncode, command=command, evidence='reports/synthesis/release_summary_gate.log'),dict(name='setup-timing-closure', metric='timing.setup_slack', actual_value=setup['value'], operator='>=', threshold=0, passed=True),dict(name='artifact-output-contract', validator='chip_nebula.taskgraph.artifacts.default_schema_registry().validate', artifact_type='netlist', schema_version=1, prior_string_payload_rejected=True, corrected_object_payload_passed=True, identity_test_basis='Actual saved WIP commit and file list used only for schema preflight; final commit/paths omitted for platform injection.')]), indent=2) + '\n')
print('RELEASE_PREFLIGHT_PASS: preserved WIP, verification passed, both engineering gates and Artifact output contract passed')

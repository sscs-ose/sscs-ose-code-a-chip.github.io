import hashlib, json, subprocess
from pathlib import Path
from chip_nebula.taskgraph.artifacts import ArtifactValidationError, default_schema_registry

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/synthesis'
def sha(path): return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
prior = json.loads((ROOT / '.nebula_inputs/artifact-eb1f96aad0b1499fa7ca53fe2826eb90/artifact.json').read_text())
verification = json.loads((ROOT / '.nebula_inputs/artifact-7295759bd83c446780157c3cdc2d72ae/artifact.json').read_text())
assert verification['payload']['verdict'] == 'passed'
assert json.loads((ROOT / 'reports/verification/report.json').read_text())['report']['verdict'] == 'passed'
assert json.loads((OUT / 'execution_status.json').read_text())['status'] == 'completed'
summary = json.loads((OUT / 'result_summary.json').read_text())
metrics = {m['id']: m for m in summary['metrics']}
setup = metrics['timing.setup_slack']
assert setup['status'] == 'measured' and setup['value'] >= 0
report = json.loads((OUT / 'report.json').read_text())
assert report['verdict'] == 'passed' and sha(report['netlist']) == report['netlist_sha256']
checks = []
for path in ['build/synth/nebula_cpu_npu_top.v', 'build/synth/mapped.json', 'reports/synthesis/stat.json', 'reports/synthesis/setup_paths.rpt', 'reports/synthesis/hold_paths.rpt']:
    p = Path(path)
    archived = Path(*p.parts[:2]) / 'history/v1' / Path(*p.parts[2:])
    equal = (ROOT / path).read_bytes() == (ROOT / archived).read_bytes()
    assert equal, path
    checks.append(dict(path=path, sha256=sha(path), byte_identical=True, compared_to=str(archived)))
(OUT / 'reproducibility.json').write_text(json.dumps(dict(verdict='passed', command='python3 -B build/synth/run.py', basis='Fresh V2 synthesis and STA reproduce published V1 mapping/paths after protected input equality checks.', checks=checks), indent=2) + '\n')
command = ['/tmp/chipnebula-public-repro-user37/bin/python', '-m', 'chip_nebula.taskgraph.result_summary', 'reports/synthesis/result_summary.json', '--profile', 'synthesis', '--required', 'design.cell_area', '--required', 'design.macro_count', '--required', 'design.standard_cell_count', '--required', 'timing.hold_slack', '--required', 'timing.setup_slack', '--measured', 'design.standard_cell_count', '--measured', 'design.cell_area', '--measured', 'design.macro_count']
with (OUT / 'release_summary_gate.log').open('w') as log:
    gate = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=30)
assert gate.returncode == 0
payload = {key: value for key, value in prior['payload'].items() if key not in ['commit', 'paths']}
payload['summary'] = f"V2 冻结输入上重跑综合及 STA，通过两项门禁；{metrics['design.standard_cell_count']['value']:,} 个标准单元，0 macro、0 latch。Liberty 面积和独立 LEF 占地面积各为 {metrics['design.cell_area']['value']:.3f} um2。tt_025C_1v80、100 ns 理想时钟、pre-layout Liberty Small wire-load 下，setup {setup['value']:+.9f} ns、hold {metrics['timing.hold_slack']['value']:+.9f} ns。网表与原已发布网表字节一致，V1 证据保留。"
payload['result_summary'] = summary
payload['baseline_revalidation'] = 'reports/synthesis/baseline_revalidation.json'
payload['not_checked'] = '未运行完整 RTL 到综合网表形式等价及 V2 PnR、提取 RC、DRC/LVS。ORFS 导出安装目录没有 Git 元数据，revision 仅由冻结约束与 lock 绑定；20 份视图已逐个实测摘要。'
payload['risk'] = 'Pre-layout 收敛不代表 post-route 收敛；V1 PnR 几何失败仍保留。V2 物理阶段须使用已冻结的指定 OpenROAD/2核策略并完成独立资格检查。'
registry = default_schema_registry()
# Only the actual prior published identity is used for type preflight; final identity is platform-owned.
identity = dict(commit=prior['content']['commit'], paths=prior['content']['paths'])
try:
    registry.validate('netlist', 1, dict(payload, result_summary='reports/synthesis/result_summary.json', **identity))
except ArtifactValidationError as error:
    assert str(error) == 'result_summary must be an object', str(error)
else:
    raise AssertionError('Malformed path-string summary accepted')
registry.validate('netlist', 1, dict(payload, **identity))
assert 'commit' not in payload and 'paths' not in payload
output = json.loads(json.dumps(dict(netlist=payload)))
assert output['netlist']['result_summary'] == summary
(OUT / 'release_payload.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
(OUT / 'release_revalidation.json').write_text(json.dumps(dict(verdict='passed', current_baseline='reports/synthesis/baseline_revalidation.json', prior_published_netlist_artifact_id=prior['id'] if 'id' in prior else 'artifact-eb1f96aad0b1499fa7ca53fe2826eb90', netlist_sha256=sha(report['netlist']), synthesis_rerun=True, sta_rerun=True, gates=[dict(name='synthesis-result-summary', exit_code=gate.returncode, command=command, evidence='reports/synthesis/release_summary_gate.log'), dict(name='setup-timing-closure', metric='timing.setup_slack', actual_value=setup['value'], operator='>=', threshold=0, passed=True), dict(name='artifact-output-contract', validator='chip_nebula.taskgraph.artifacts.default_schema_registry().validate', artifact_type='netlist', schema_version=1, path_string_payload_rejected=True, object_payload_passed=True, identity_test_basis='Prior published identity used only for schema preflight; final commit/paths omitted for platform injection.')]), indent=2) + '\n')
print('RELEASE_PREFLIGHT_PASS: current verification, fresh synthesis/STA, both gates, reproducibility and artifact output contract passed')

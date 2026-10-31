"""Read-only adoption audit of source-bound owner workload evidence; writes only GDS receipts."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tarfile

root = Path(__file__).resolve().parents[2]
out = root / 'build/gds'
package = root / '.nebula_inputs/authorized-postroute-workload-experiment-20261014/operator-audits/postroute-workloads-20261014'
def read(path): return json.loads(Path(path).read_text())
def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def write(name, value): (out / name).write_text(json.dumps(value, indent=2) + '\n')

records = []
for path in sorted((root / '.nebula_inputs').glob('*/artifact.json')):
    record = read(path)
    content = record['content']
    base = path.parent if record['type'] == 'specification.source' else root
    tree = subprocess.check_output(['git', 'ls-tree', '-rz', content['commit'], '--', *content['paths']], cwd=root)
    count = 0
    for entry in tree.split(b'\0'):
        if not entry: continue
        metadata, name = entry.split(b'\t', 1)
        mode, kind, oid = metadata.split()
        name = name.decode()
        assert kind == b'blob' and mode in (b'100644', b'100755'), name
        data = (base / name).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest().encode() == oid, name
        count += 1
    records.append(dict(artifact_id=record['id'], commit=content['commit'], files_checked=count, record_sha256=sha(path), base_path=str(base.relative_to(root))))
assert len(records) == 5
snapshot = read(root / 'reports/pnr/delivery_snapshot.json')
owner = read(root / 'reports/pnr/power_area.json')
summary = read(package / 'summary.json')
manifest = read(package / 'experiment-manifest.json')
assert owner['status'] == owner['engineering_verdict'] == 'passed'
assert owner['snapshot_id'] == summary['snapshot_id'] == snapshot['snapshot_id'] == read(out / 'input_snapshot.json')['snapshot_id']
assert owner['source_commit'] == next(r['commit'] for r in records if r['artifact_id'] == owner['source_artifact_id'])
assert owner['source_record_sha256'] == sha(root / owner['source_record_path']) == sha(package.parents[1] / 'artifact.json')
assert owner['manifest_sha256'] == sha(package / 'experiment-manifest.json') == sha(root / owner['experiment_manifest_path'])
assert owner['source_summary_sha256'] == manifest['source_summary_sha256'] == sha(package / 'summary.json')
record = read(package.parents[1] / 'artifact.json')
assert hashlib.sha256(record['payload']['content'].encode()).hexdigest() == record['payload']['content_digest'].removeprefix('sha256:')
for item in manifest['files']:
    path = package / item['path']
    assert path.resolve().is_relative_to(package.resolve()) and not path.is_symlink()
    assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], path
    assert sha(root / owner['operator_evidence_path'] / item['path']) == item['sha256']
assert summary['complete'] and summary['passed'] and summary['power_complete']
assert all(c['exit_code'] == 0 for c in read(package / 'commands.json'))
assert all(c['exit_code'] == 0 for c in read(root / 'reports/pnr/power_area/adoption_commands.json'))
for group in ('files', 'evidence_sha256'):
    for path, expected in snapshot[group].items(): assert sha(root / path) == expected, path
assert sha(package / 'postroute.v') == summary['netlist_sha256'] == snapshot['files']['build/pnr/results/6_final.sta.v']
assert sha(package / 'cell_models.v') == summary['cell_models_sha256'] == sha(root / 'build/pnr/power_area/model_binding/cell_models.v')
assert owner['sdc_sha256'] == snapshot['files']['build/pnr/results/6_final.sdc']
assert owner['model_binding']['spef_sha256'] == snapshot['files']['build/pnr/results/6_final.spef']
models = read(root / 'reports/pnr/power_area/model_inventory.json')
assert sha(models['liberty_path']) == models['liberty_sha256'] == summary['liberty_sha256'] == snapshot['liberty_sha256']
assert all(m['leakage_power_present'] for m in models['masters'].values())
constant_only = [name for name, model in models['masters'].items() if not model['internal_power_present']]
assert constant_only == ['sky130_fd_sc_hd__conb_1']
text = (package / 'cell_models.v').read_text()
start = text.index('module sky130_fd_sc_hd__conb_1(')
constant_model = text[start:text.index('endmodule', start)]
assert "assign HI = 1'h1;" in constant_model and "assign LO = 1'h0;" in constant_model
assert sha(root / 'reports/verification/raw-run-evidence.tar.gz') == summary['source_archive_sha256']
for tool in summary['tool_executables'].values(): assert sha(tool['resolved']) == tool['sha256']
assert sha(root / owner['auditor_path']) == owner['auditor_sha256']
assert all(g['passed'] for g in read(root / 'reports/pnr/power_area/gate_preflight.json')['gates'])
assert read(root / 'reports/pnr/power_area/gate_preflight.json')['owner_verdict'] == 'passed'

# Pure captured checkers evaluate actual traces/VCDs; no simulator or PnR rerun.
sys.path.insert(0, str(package / 'used-comparator/scripts'))
sys.path.insert(0, str(package / 'used-comparator/verification'))
from kernel_programs import build_kernel, interpret, signed, OUTPUT, TOHOST
from sail_commit import compare_commits
spec = importlib.util.spec_from_file_location('captured_waveforms', package / 'used-comparator/scripts/check_postroute_waveforms.py')
waveform = importlib.util.module_from_spec(spec)
spec.loader.exec_module(waveform)
measured = waveform.check(package)
assert measured == read(package / 'clock-reset-waveform.json') == read(root / 'reports/pnr/power_area/clock_reset_recheck.json')
write('power_waveform_recheck.json', measured)
qualified = []
with tarfile.open(root / 'reports/verification/raw-run-evidence.tar.gz', 'r:gz') as archive:
    for row in summary['rows']:
        name = row['workload']
        case = package / name
        receipt = read(root / ('reports/pnr/power_area/' + name + '.json'))
        for filename in ('memory.hex', 'program.elf', 'reference.jsonl', 'expected_outputs.json'):
            data = archive.extractfile('kernels/' + name + '-xdot4/' + filename).read()
            assert data == (case / filename).read_bytes(), (name, filename)
        image = bytes(int(x, 16) for x in (case / 'memory.hex').read_text().splitlines())
        _, regenerated, expected, _ = build_kernel(name, True)
        assert image == bytes(regenerated) and expected == receipt['outputs'] == row['expected_outputs'] == read(case / 'expected_outputs.json')
        reference, _ = interpret(image)
        assert reference == [json.loads(x) for x in (case / 'reference.jsonl').read_text().splitlines()]
        observed = [json.loads(x) for x in (case / 'trace.jsonl').read_text().splitlines()]
        comparison = compare_commits(reference, observed)
        assert comparison['passed'] and comparison == row['comparison'] and comparison['matched'] == receipt['matched_commits']
        damaged = [dict(x) for x in observed]; damaged[0]['insn'] ^= 1
        assert not compare_commits(reference, damaged)['passed']
        stores = {x['mem_addr']: signed(x['mem_wdata']) for x in observed if x['mem_wstrb'] == 15}
        assert [stores[OUTPUT + 4 * i] for i in range(len(expected))] == expected
        assert observed[-1]['mem_addr'] == TOHOST and observed[-1]['mem_wdata'] == 1 and observed[-1]['mem_wstrb'] == 15
        assert row['activity_end_ps'] == observed[-1]['cycle'] * 100000 + 51000
        assert row['activity_start_ps'] == 300000 and row['activity_duration_ps'] == row['activity_end_ps'] - 300000
        runtime = (package / (name + '.log')).read_text()
        match = re.search(r'CPU_ELF_PASS cycles=(\d+) commits=(\d+) traps=(\d+) tohost=00000001', runtime)
        assert match and int(match[1]) == row['cycles'] == receipt['cycles'] and int(match[2]) == len(observed) and int(match[3]) == 0
        assert 'Verilator 5.048' in runtime
        stored = manifest['vcd_storage'][row['vcd']]
        decoded = root / ('build/pnr/power_area/validated-vcd/' + name + '.vcd')
        assert decoded.stat().st_size == stored['decoded_bytes'] and sha(decoded) == stored['decoded_sha256'] == row['vcd_sha256'] == receipt['vcd_sha256']
        power = read(root / receipt['power_evidence'])['Total']
        assert all(math.isfinite(v) and v >= 0 for v in power.values())
        assert all(math.isclose(power[k], v, rel_tol=1e-9, abs_tol=1e-12) for k, v in row['estimated_power_w'].items())
        assert math.isclose(power['total'] * 1000, receipt['total_mw'], rel_tol=1e-12)
        assert math.isclose((power['internal'] + power['switching']) * 1000, receipt['dynamic_mw'], rel_tol=1e-12)
        assert math.isclose(power['leakage'] * 1000, receipt['leakage_mw'], rel_tol=1e-12)
        activity = (root / ('reports/pnr/power_area/recomputed/' + name + '/activity.rpt')).read_text()
        assert int(re.search(r'^vcd\s+(\d+)', activity, re.M)[1]) == 59577
        assert int(re.search(r'^unannotated\s+(\d+)', activity, re.M)[1]) == 0
        assert receipt['window_start_ns'] * 1000 == row['activity_start_ps'] and receipt['window_end_ns'] * 1000 == row['activity_end_ps']
        qualified.append(receipt)
assert {r['workload'] for r in qualified} == {'DOT64', 'GEMM8', 'CONV3'}
old = read(out / 'history/attempt-cf266b46df624d72941221bc4ba42d7e/current_input_snapshot.json')
allowed_changes = {'build/pnr/README.txt', 'build/pnr/check_power_area.py', 'reports/pnr/delivery_snapshot.json', 'reports/pnr/power_area.json',
                   'reports/pnr/report.json', 'reports/pnr/power_area/CONV3.json', 'reports/pnr/power_area/DOT64.json',
                   'reports/pnr/power_area/GEMM8.json', 'reports/pnr/power_area/gate_preflight.json'}
changed = []
for path, expected in old['files'].items():
    if sha(root / path) != expected:
        assert path in allowed_changes, path
        changed.append(path)
assert sha(out / 'nebula_cpu_npu_top.gds') == read(out / 'readability.json')['sha256']
area = read(root / 'reports/pnr/area_and_fanout.json')
assert area['database_sha256'] == snapshot['files']['build/pnr/results/6_final.odb']
assert sum(v['count'] for v in area['master_type_groups'].values()) == area['placed_instance_count'] == 52908
assert math.isclose(sum(v['footprint_um2'] for v in area['master_type_groups'].values()), area['total_footprint_um2'], rel_tol=1e-12)
write('power_area_adoption.json', dict(schema_version=1, status='passed', engineering_verdict='passed', acceptance_id='AC-POWER-AREA',
    snapshot_id=snapshot['snapshot_id'], input_artifacts=records, owner_receipt='reports/pnr/power_area.json', owner_receipt_sha256=sha(root / 'reports/pnr/power_area.json'),
    owner_qualified=True, manifest_files_checked=len(manifest['files']), manifest_sha256=sha(package / 'experiment-manifest.json'),
    waveform_check='build/gds/power_waveform_recheck.json', workloads=qualified, changed_owner_files=changed,
    prior_audit='build/gds/history/attempt-cf266b46df624d72941221bc4ba42d7e/project_acceptance.json',
    comparator_controls='Damaged first instruction rejected for every workload; does not satisfy independent evaluator-release obligation.',
    execution_scope='Read-only source/trace/waveform/report validation; no Yosys, Verilator, PnR, GDS or design-check rerun.',
    limitations=[owner['not_checked'], owner['risk'], 'The 64 conb_1 static tie cells have characterized leakage and constant Boolean outputs but no internal_power table; no missing table is fabricated.', 'Historical resource failure, independent evaluator release and unresolved typed adapters still block whole-project acceptance.']))
write('current_input_snapshot.json', dict(snapshot_id=snapshot['snapshot_id'], files={str(p.relative_to(root)):sha(p) for base in ('build/pnr','reports/pnr') for p in (root / base).rglob('*') if p.is_file()}))
print('OWNER_POWER_AREA_SOURCE_TRACE_WAVEFORM_AND_REPORT_ADOPTION_PASS')

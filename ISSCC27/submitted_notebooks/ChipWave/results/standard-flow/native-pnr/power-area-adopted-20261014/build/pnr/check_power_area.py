"""Bind supplied gate activity and recompute power; preserve accepted physical outputs."""
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / 'build/pnr/power_area'
REPORT = ROOT / 'reports/pnr/power_area'
PACKAGE = BUILD / 'operator-evidence'
ARTIFACT = ROOT / '.nebula_inputs/authorized-postroute-workload-experiment-20261014/artifact.json'
for path in (BUILD / 'model_binding', BUILD / 'validated-vcd', REPORT / 'recomputed'):
    path.mkdir(parents=True, exist_ok=True)


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(path)


def q(path):
    value = str(path)
    assert not any(x in value for x in ('\\', '{', '}', '\r', '\n'))
    return '{' + value + '}'


commands = []


def execute(argv, log):
    with log.open('w') as handle:
        result = subprocess.run(argv, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, timeout=300)
    commands.append(dict(argv=argv, exit_code=result.returncode, log=str(log.relative_to(ROOT))))
    write(REPORT / 'adoption_commands.json', commands)
    assert result.returncode == 0, log


snapshot = read(ROOT / 'reports/pnr/delivery_snapshot.json')
assert all(sha(ROOT / p) == h for k in ('files', 'evidence_sha256') for p, h in snapshot[k].items())
protected = {p: sha(ROOT / p) for p in [*snapshot['files'], 'reports/pnr/execution_status.json',
             'reports/pnr/exit_gates.json', 'reports/pnr/result_summary.json',
             'build/pnr/checkpoints/latest.json', 'build/pnr/checkpoints/slot-a.odb', 'build/pnr/checkpoints/slot-b.odb']}
record = read(ARTIFACT)
assert hashlib.sha256(record['payload']['content'].encode()).hexdigest() == record['payload']['content_digest'].removeprefix('sha256:')
manifest = read(PACKAGE / 'experiment-manifest.json')
frozen = subprocess.check_output(['git', 'show', record['content']['commit'] + ':operator-audits/postroute-workloads-20261014/experiment-manifest.json'], cwd=ROOT)
assert hashlib.sha256(frozen).hexdigest() == sha(PACKAGE / 'experiment-manifest.json')
for item in manifest['files']:
    path = PACKAGE / item['path']
    assert path.resolve().is_relative_to(PACKAGE.resolve()) and not path.is_symlink()
    assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], item['path']
summary = read(PACKAGE / 'summary.json')
assert summary['complete'] and summary['passed'] and summary['power_complete']
assert summary['snapshot_id'] == snapshot['snapshot_id']
assert summary['netlist_sha256'] == sha(PACKAGE / 'postroute.v') == snapshot['files']['build/pnr/results/6_final.sta.v']
assert sha(PACKAGE / 'summary.json') == manifest['source_summary_sha256']
assert all(x['exit_code'] == 0 for x in read(PACKAGE / 'commands.json'))
constraints = read(ROOT / 'physical/chip-nebula/implementation.constraints.json')
assert all(sha(ROOT / f['path']) == f['sha256'] for i in snapshot['inputs'] for f in i['files'])
library = constraints['view_binding']['views'][constraints['view_binding']['liberty']]
assert sha(library['installed_path']) == library['sha256'] == snapshot['liberty_sha256'] == summary['liberty_sha256']
assert sha(PACKAGE / 'cell_models.v') == summary['cell_models_sha256']
assert sha(PACKAGE / 'used-comparator/verification/tb_cpu_npu.sv') == summary['original_bench_sha256']
assert sha(PACKAGE / 'gate_tb.sv') == summary['adapted_bench_sha256']
assert 'nebula_cpu_npu_top dut (.*);' in (PACKAGE / 'gate_tb.sv').read_text()
archive = ROOT / '.nebula_inputs/artifact-0b514721fd8641408ffcec0d7f4350ec/reports/verification/raw-run-evidence.tar.gz'
assert sha(archive) == summary['source_archive_sha256']
model = BUILD / 'model_binding/cell_models.v'
execute(['/tmp/chipnebula-pinned-tools/bin/yosys', '-Q', '-T', '-p', 'read_liberty -ignore_miss_func ' + json.dumps(library['installed_path']) +
         '; write_verilog -noattr ' + json.dumps(str(model))], REPORT / 'model_reimport.log')
assert sha(model) == summary['cell_models_sha256'], 'Imported frozen models differ'
execute(['/tmp/chipnebula-pinned-tools/bin/yosys', '-Q', '-T', '-p', 'read_verilog ' + json.dumps(str(model)) + ' ' + json.dumps(str(ROOT / 'build/pnr/results/6_final.sta.v')) +
         '; hierarchy -check -top nebula_cpu_npu_top'], REPORT / 'model_hierarchy_recheck.log')
sys.path.insert(0, str(PACKAGE / 'used-comparator/scripts'))
sys.path.insert(0, str(PACKAGE / 'used-comparator/verification'))
from kernel_programs import build_kernel, interpret, signed, OUTPUT, TOHOST
from sail_commit import compare_commits
spec = importlib.util.spec_from_file_location('waveform_checker', PACKAGE / 'used-comparator/scripts/check_postroute_waveforms.py')
waveform = importlib.util.module_from_spec(spec)
spec.loader.exec_module(waveform)
actual_waveforms = waveform.check(PACKAGE)
assert actual_waveforms == read(PACKAGE / 'clock-reset-waveform.json')
write(REPORT / 'clock_reset_recheck.json', actual_waveforms)
assert constraints['power']['activity']['period_ns'] == summary['clock_period_ns'] == 100
openroad = constraints['physical_execution']['openroad_executable']
assert sha(Path(openroad).resolve()) == constraints['physical_execution']['executable_sha256'] == summary['tool_executables']['openroad']['sha256']
rows = []
for row in summary['rows']:
    name = row['workload']
    assert name in ('DOT64', 'GEMM8', 'CONV3')
    case = PACKAGE / name
    for filename in ('memory.hex', 'program.elf', 'expected_outputs.json'):
        assert sha(case / filename) == sha(BUILD / name / filename), filename
    image = bytes(int(x, 16) for x in (case / 'memory.hex').read_text().splitlines())
    _, regenerated, expected, _ = build_kernel(name, True)
    assert image == bytes(regenerated) and expected == row['expected_outputs'] == read(case / 'expected_outputs.json')
    reference, _ = interpret(image)
    assert reference == [json.loads(x) for x in (case / 'reference.jsonl').read_text().splitlines()]
    observed = [json.loads(x) for x in (case / 'trace.jsonl').read_text().splitlines()]
    comparison = compare_commits(reference, observed)
    assert comparison['passed'] and comparison == row['comparison']
    damaged = [dict(x) for x in observed]
    damaged[0]['insn'] ^= 1
    assert not compare_commits(reference, damaged)['passed'], 'Comparator must reject damaged instructions'
    stores = {x['mem_addr']: signed(x['mem_wdata']) for x in observed if x['mem_wstrb'] == 15}
    assert [stores[OUTPUT + 4 * i] for i in range(len(expected))] == expected
    assert observed[-1]['mem_addr'] == TOHOST and observed[-1]['mem_wstrb'] == 15 and observed[-1]['mem_wdata'] == 1
    assert row['activity_end_ps'] == observed[-1]['cycle'] * 100000 + 51000
    assert row['activity_start_ps'] == 300000 and row['activity_duration_ps'] == row['activity_end_ps'] - 300000
    runtime = (PACKAGE / (name + '.log')).read_text()
    result = re.search(r'CPU_ELF_PASS cycles=(\d+) commits=(\d+) traps=(\d+) tohost=00000001', runtime)
    assert result and int(result[1]) == row['cycles'] and int(result[2]) == len(observed) and int(result[3]) == 0
    assert 'Verilator 5.048' in runtime
    stored = manifest['vcd_storage'][row['vcd']]
    decoded = BUILD / 'validated-vcd' / (name + '.vcd')
    with gzip.open(PACKAGE / stored['path'], 'rb') as source, decoded.open('wb') as destination:
        shutil.copyfileobj(source, destination)
    assert decoded.stat().st_size == stored['decoded_bytes'] and sha(decoded) == stored['decoded_sha256'] == row['vcd_sha256']
    out = REPORT / 'recomputed' / name
    out.mkdir(exist_ok=True)
    script = BUILD / (name + '_power.tcl')
    views = constraints['view_binding']['views']
    lines = ['read_liberty ' + q(library['installed_path'])]
    for lef in ('lef/sky130_fd_sc_hd.tlef', 'lef/sky130_fd_sc_hd_merged.lef'):
        assert sha(views[lef]['installed_path']) == views[lef]['sha256']
        lines.append('read_lef ' + q(views[lef]['installed_path']))
    lines += ['read_verilog ' + q(ROOT / 'build/pnr/results/6_final.sta.v'), 'link_design nebula_cpu_npu_top',
              'read_sdc ' + q(ROOT / 'build/pnr/results/6_final.sdc'), 'set_propagated_clock [all_clocks]',
              'read_spef ' + q(ROOT / 'build/pnr/results/6_final.spef'),
              f'read_vcd -scope tb_cpu_elf/dut -begin_time {row["activity_start_ps"]} -end_time {row["activity_end_ps"]} ' + q(decoded),
              'report_activity_annotation -report_unannotated > ' + q(out / 'activity.rpt'),
              'report_power -digits 12 -format json > ' + q(out / 'power.json')]
    script.write_text('if {[catch {\n' + '\n'.join(lines) + '\n} message options]} {puts stderr $message; exit 1}\nexit\n')
    execute([openroad, '-no_init', '-exit', '-threads', '2', str(script)], out / 'power.log')
    power = read(out / 'power.json')['Total']
    assert all(math.isfinite(x) and x >= 0 for x in power.values())
    assert all(math.isclose(power[k], v, rel_tol=1e-9, abs_tol=1e-12) for k, v in row['estimated_power_w'].items())
    # Match the supplied postprocessor's check of tool floating-point accumulation.
    assert math.isclose(power['total'], power['internal'] + power['switching'] + power['leakage'], rel_tol=1e-6, abs_tol=1e-12)
    annotation = (out / 'activity.rpt').read_text()
    assert int(re.search(r'^vcd\s+(\d+)', annotation, re.M)[1]) == 59577
    assert int(re.search(r'^unannotated\s+(\d+)', annotation, re.M)[1]) == 0
    qualified = dict(workload=name, status='passed', engineering_verdict='passed', cycles=row['cycles'],
        cycle_scope='Total harness cycles include three reset cycles; power uses only the measured eligible interval.',
        window_start_ns=row['activity_start_ps'] / 1000, window_end_ns=row['activity_end_ps'] / 1000,
        duration_ns=row['activity_duration_ps'] / 1000, matched_commits=comparison['matched'], outputs=expected,
        functional_model='Exact final STA netlist with frozen Liberty Boolean/sequential models; zero delay.',
        internal_mw=power['internal'] * 1000, switching_mw=power['switching'] * 1000,
        dynamic_mw=(power['internal'] + power['switching']) * 1000, leakage_mw=power['leakage'] * 1000,
        total_mw=power['total'] * 1000, annotation=row['activity_annotation'], snapshot_id=snapshot['snapshot_id'],
        vcd_sha256=row['vcd_sha256'], evidence_origin='Operator gate replay; PnR comparator/waveform/model binding and OpenROAD power rechecked.',
        power_evidence=str((out / 'power.json').relative_to(ROOT)), waveform_evidence='reports/pnr/power_area/clock_reset_recheck.json')
    write(REPORT / (name + '.json'), qualified)
    rows.append(qualified)
assert {x['workload'] for x in rows} == {'DOT64', 'GEMM8', 'CONV3'}
assert all(sha(ROOT / p) == digest for p, digest in protected.items())
write(ROOT / 'reports/pnr/power_area.json', dict(schema_version=1, status='passed', engineering_verdict='passed',
    acceptance_id='AC-POWER-AREA', checked_at=datetime.now(timezone.utc).isoformat(), snapshot_id=snapshot['snapshot_id'],
    source_artifact_id=record['id'], source_commit=record['content']['commit'], source_record_sha256=sha(ARTIFACT),
    manifest_sha256=sha(PACKAGE / 'experiment-manifest.json'), source_summary_sha256=sha(PACKAGE / 'summary.json'),
    conditions=constraints['power'], workloads=rows, aggregation='none; each workload reported separately',
    model_binding=dict(netlist_sha256=summary['netlist_sha256'], liberty_sha256=summary['liberty_sha256'],
                       cell_models_sha256=summary['cell_models_sha256'], spef_sha256=snapshot['files']['build/pnr/results/6_final.spef']),
    area_evidence='reports/pnr/area_and_fanout.json', geometry_evidence='reports/pnr/geometry_acceptance.json',
    historical_unavailable_report='reports/pnr/history/power-area-unavailable/power_area.json',
    evidence=['reports/pnr/power_area/clock_reset_recheck.json','reports/pnr/power_area/adoption_commands.json',
              'reports/pnr/power_area/model_reimport.log','reports/pnr/power_area/model_hierarchy_recheck.log'],
    self_check='Damaged instruction rejected by unchanged comparator for all three workloads.',
    remaining_project_dependencies='GDS and whole-project development/resource/evaluator/typed-adapter receipts remain separate; not awarded by this owner check.',
    not_checked='No new Verilator execution by PnR. No SDF-delay/glitch/silicon-power, energy-improvement or multi-corner signoff claim.',
    risk='100% annotation covers tool-report-eligible pins; sequential internal/hierarchical pins are excluded by the tool.'))
for path in [ROOT / 'reports/pnr/power_area.json', *REPORT.rglob('*'), *(ROOT / 'reports/pnr/history/power-area-unavailable').rglob('*')]:
    if path.is_file():
        snapshot['evidence_sha256'][str(path.relative_to(ROOT))] = sha(path)
write(ROOT / 'reports/pnr/delivery_snapshot.json', snapshot)
print('AC-POWER-AREA qualified; exact physical exports and existing physical gate evidence unchanged.')

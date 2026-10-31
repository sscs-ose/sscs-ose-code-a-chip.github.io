"""Replay frozen kernels on the accepted post-route netlist with zero-delay cell models."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import tarfile
import time

from run_kernels import compare_commits, OUTPUT, signed

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def summarize_power(output):
    summary = json.loads((output / 'summary.json').read_text())
    assert summary['complete'] and summary['passed']
    for row in summary['rows']:
        case = output / 'power' / row['workload']
        values = json.loads((case / 'power.json').read_text())['Total']
        assert all(math.isfinite(v) and v >= 0 for v in values.values())
        assert math.isclose(values['total'], sum(values[k] for k in ('internal', 'switching', 'leakage')),
                            rel_tol=1e-6, abs_tol=1e-12)
        annotation = (case / 'activity-annotation.rpt').read_text()
        annotated = int(re.search(r'^vcd\s+(\d+)', annotation, re.M)[1])
        missing = int(re.search(r'^unannotated\s+(\d+)', annotation, re.M)[1])
        assert annotated + missing > 0
        row['estimated_power_w'] = values
        row['activity_annotation'] = dict(vcd_pins=annotated, unannotated_pins=missing,
            reported_pins=annotated + missing, percent=100 * annotated / (annotated + missing),
            scope='OpenSTA report_activity_annotation pin classes; sequential internal and hierarchical pins excluded')
        row['power_reports_sha256'] = {name: digest(case / name) for name in
            ('power.tcl', 'power.log', 'power.json', 'power.rpt', 'activity-annotation.rpt', 'parasitic-annotation.rpt')}
    summary['power_complete'] = True
    summary['power_scope'] = 'Liberty-model estimates from zero-delay post-route gate activity and extracted SPEF. No SDF-delay/glitch, silicon-power, or energy-improvement claim. Windows start at reset deassertion and end at settled committed tohost completion.'
    summary['postprocessor_sha256'] = digest(Path(__file__))
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('POSTROUTE_POWER_SUMMARY_PASS')


def power(output):
    summary = json.loads((output / 'summary.json').read_text())
    assert summary['complete'] and summary['passed']
    source = ROOT / 'results/standard-flow/native-pnr/accepted-20261014'
    snapshot = json.loads((source / 'reports/pnr/delivery_snapshot.json').read_text())
    assert snapshot['snapshot_id'] == summary['snapshot_id']
    library = ROOT / 'toolchain/orfs/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
    assert digest(library) == summary['liberty_sha256']
    audit = json.loads((source / 'reports/pnr/input_audit.json').read_text())
    lef_paths = []
    for name in ('lef/sky130_fd_sc_hd.tlef', 'lef/sky130_fd_sc_hd_merged.lef'):
        view = next(v for v in audit['views'] if v['name'] == name)
        path = ROOT / 'toolchain/orfs/flow/platforms/sky130hd' / name
        assert digest(path) == view['sha256']
        lef_paths.append(path)
    for name in ('6_final.sta.v', '6_final.spef', '6_final.sdc'):
        assert digest(source / 'build/pnr/results' / name) == snapshot['files']['build/pnr/results/' + name]

    def q(path):
        value = str(path)
        if any(c in value for c in ('\\', '{', '}', '\r', '\n')):
            raise ValueError('Unsupported Tcl path characters')
        return '{' + value + '}'

    reports = output / 'power'
    reports.mkdir()
    for row in summary['rows']:
        case = reports / row['workload']; case.mkdir(); vcd = output / row['vcd']
        assert digest(vcd) == row['vcd_sha256'] and row['activity_start_ps'] == 300000
        script = case / 'power.tcl'
        if script.exists():
            raise ValueError('Previous power experiment preserved')
        script.write_text('if {[catch {\n' + '\n'.join([
            'read_liberty ' + q(library),
            *['read_lef ' + q(path) for path in lef_paths],
            'read_verilog ' + q(source / 'build/pnr/results/6_final.sta.v'),
            'link_design nebula_cpu_npu_top',
            'read_sdc ' + q(source / 'build/pnr/results/6_final.sdc'),
            'set_propagated_clock [all_clocks]',
            'read_spef ' + q(source / 'build/pnr/results/6_final.spef'),
            'report_units',
            'report_parasitic_annotation > ' + q(case / 'parasitic-annotation.rpt'),
            f'read_vcd -scope tb_cpu_elf/dut -begin_time {row["activity_start_ps"]} -end_time {row["activity_end_ps"]} ' + q(vcd),
            'report_activity_annotation -report_unannotated > ' + q(case / 'activity-annotation.rpt'),
            'report_power -digits 12 -format json > ' + q(case / 'power.json'),
            'report_power -digits 12 > ' + q(case / 'power.rpt'),
        ]) + '\n} message options]} {puts stderr $message; puts stderr [dict get $options -errorinfo]; exit 1}\nexit\n')
        argv = ['openroad', '-no_init', '-exit', '-threads', '2', str(script)]
        with (case / 'power.log').open('w') as log:
            result = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, timeout=300)
        assert result.returncode == 0, case / 'power.log'
        assert (case / 'power.json').is_file() and (case / 'activity-annotation.rpt').is_file()
        print('POSTROUTE_POWER_REPORT', row['workload'], flush=True)
    summarize_power(output)


def run(output):
    if output.exists() and set(p.name for p in output.iterdir()) != {'cell_models.v', 'models.log'}:
        raise ValueError('Use a new directory; previous runs are preserved')
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__), output / 'used-runner.py')
    source = ROOT / 'results/standard-flow/native-pnr/accepted-20261014'
    snapshot = json.loads((source / 'reports/pnr/delivery_snapshot.json').read_text())
    netlist = source / 'build/pnr/results/6_final.sta.v'
    assert digest(netlist) == snapshot['files']['build/pnr/results/6_final.sta.v']
    library = ROOT / 'toolchain/orfs/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
    assert digest(library) == snapshot['liberty_sha256']
    commands = []

    def execute(name, argv, timeout):
        start = time.monotonic()
        with (output / (name + '.log')).open('w') as log:
            result = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
        commands.append(dict(name=name, argv=argv, exit_code=result.returncode,
                             elapsed_seconds=time.monotonic() - start, log=name + '.log'))
        (output / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        if result.returncode:
            raise RuntimeError(f'{name} failed; see {output / (name + ".log")}')

    models = output / 'cell_models.v'
    execute('models', ['yosys', '-Q', '-T', '-p',
        f'read_liberty -ignore_miss_func {json.dumps(str(library))}; write_verilog -noattr {json.dumps(str(models))}'], 120)
    shutil.copy2(netlist, output / 'postroute.v')
    execute('model_hierarchy', ['yosys', '-Q', '-T', '-p',
        f'read_verilog {json.dumps(str(models))} {json.dumps(str(output / "postroute.v"))}; hierarchy -check -top nebula_cpu_npu_top'], 120)
    bench = (ROOT / 'verification/tb_cpu_npu.sv').read_text()
    assert bench.count('    #2;') == 3
    bench = bench.replace('    #2;', '    #50;', 1).replace('    #2;', '    #1;', 1)
    assert bench.count('    clk = 0;\n    #2;') == 1
    bench = bench.replace('    clk = 0;\n    #2;', '    #49;\n    clk = 0;')
    assert bench.count('    step(); step();\n    rst_n = 1;') == 1
    bench = bench.replace('    step(); step();\n    rst_n = 1;',
        '    step(); step(); step();\n    rst_n = 1;\n'
        '    $display("ACTIVITY_START_NS=%0t", $time);')
    assert bench.count('          host_committed = 1;') == 1
    bench = bench.replace('          host_committed = 1;',
        '          host_committed = 1;\n          $display("ACTIVITY_END_NS=%0t", $time);')
    bench = bench.replace('    trace_fd = 0;',
        '    if (!$value$plusargs("VCD=%s", vcd_file)) $fatal(1, "VCD required");\n'
        '    $dumpfile(vcd_file);\n    $dumpvars(0, dut);\n    trace_fd = 0;')
    bench = bench.replace('  string image_file;', '  string vcd_file;\n  string image_file;')
    bench_path = output / 'gate_tb.sv'; bench_path.write_text(bench)
    obj = output / 'obj'
    execute('compile', ['verilator', '--binary', '--timing', '--assert', '--trace', '--trace-underscore',
        '--trace-depth', '3', '-Wno-fatal', '-j', '2', '--top-module', 'tb_cpu_elf',
        '--Mdir', str(obj), str(models), str(output / 'postroute.v'), str(bench_path)], 900)
    archive = ROOT / 'results/standard-flow/native-verification/04-calibrated-baseline/reports/verification/raw-run-evidence.tar.gz'
    inputs = {}
    with tarfile.open(archive) as bundle:
        for name in ('DOT64', 'GEMM8', 'CONV3'):
            case = output / name; case.mkdir()
            for filename in ('memory.hex', 'program.elf', 'reference.jsonl', 'expected_outputs.json'):
                member = bundle.getmember(f'kernels/{name}-xdot4/{filename}')
                assert member.isfile() and not member.issym() and not member.islnk()
                with bundle.extractfile(member) as src, (case / filename).open('wb') as dst:
                    shutil.copyfileobj(src, dst)
                inputs[f'{name}/{filename}'] = digest(case / filename)
    rows = []
    for name in ('DOT64', 'GEMM8', 'CONV3'):
        case = output / name; trace = case / 'trace.jsonl'; vcd = case / 'activity-full.vcd'
        execute(name, [str(obj / 'Vtb_cpu_elf'), f'+IMAGE={case / "memory.hex"}',
            f'+TRACE={trace}', f'+VCD={vcd}', '+SEED=20260925', '+MAX_CYCLES=2000000'], 600)
        observed = [json.loads(line) for line in trace.read_text().splitlines()]
        reference = [json.loads(line) for line in (case / 'reference.jsonl').read_text().splitlines()]
        comparison = compare_commits(reference, observed)
        expected = json.loads((case / 'expected_outputs.json').read_text())
        stores = {e['mem_addr']: signed(e['mem_wdata']) for e in observed
                  if e.get('kind') == 'commit' and e.get('mem_wstrb') == 15
                  and OUTPUT <= e['mem_addr'] < OUTPUT + 4 * len(expected)}
        outputs = [stores.get(OUTPUT + 4 * i) for i in range(len(expected))]
        log = (output / (name + '.log')).read_text()
        result = re.search(r'CPU_ELF_PASS cycles=(\d+) commits=(\d+) traps=(\d+)', log)
        assert result and int(result[3]) == 0 and comparison['passed'] and outputs == expected
        start = int(re.search(r'ACTIVITY_START_NS=(\d+)', log)[1])
        end = int(re.search(r'ACTIVITY_END_NS=(\d+)', log)[1])
        assert end > start and vcd.is_file() and vcd.stat().st_size > 0
        rows.append(dict(workload=name, passed=True, cycles=int(result[1]),
            activity_start_ps=start, activity_end_ps=end, activity_duration_ps=end-start,
            vcd=str(vcd.relative_to(output)), vcd_sha256=digest(vcd),
            outputs=outputs, expected_outputs=expected, comparison=comparison))
        summary = dict(schema_version=1, complete=len(rows) == 3, passed=all(r['passed'] for r in rows),
            snapshot_id=snapshot['snapshot_id'], netlist_sha256=digest(netlist), liberty_sha256=digest(library),
            cell_models_sha256=digest(models), original_bench_sha256=digest(ROOT / 'verification/tb_cpu_npu.sv'),
            adapted_bench_sha256=digest(bench_path), clock_period_ns=100, clock_duty_percent=50,
            reset_low_ns=300, reset_release_phase_ns=50, source_archive_sha256=digest(archive),
            frozen_programs_sha256=inputs, rows=rows,
            tool_executables={name: {'requested': name, 'resolved': str(Path(shutil.which(name)).resolve()),
                'sha256': digest(Path(shutil.which(name)).resolve())} for name in ('yosys', 'verilator', 'openroad')},
            scope='Functional post-route netlist replay using Yosys-imported zero-delay Liberty Boolean/sequential models; no SDF delay simulation or timing-signoff claim. Raw VCD may include reset/end context; power must use only the declared eligible interval and report actual annotation coverage.')
        (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print('POSTROUTE_WORKLOAD_PASS', name, rows[-1]['cycles'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    destination = parser.parse_args().output.resolve()
    run(destination)
    power(destination)

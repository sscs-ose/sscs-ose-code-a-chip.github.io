#!/usr/bin/env python3
"""Recheck frozen dependencies and run the bounded integration smoke."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/integration'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(args, log):
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=180)
    output = result.stdout + result.stderr
    (OUT / log).write_text(output)
    assert result.returncode == 0, f'{args}:\n{output[-5000:]}'
    return output


def ports(path):
    header = Path(path).read_text().split(');', 1)[0]
    return [dict(direction=direction, name=name,
                 width=int(msb) + 1 if msb else 1)
            for direction, msb, name in re.findall(
                r'\b(input|output)\s+logic\s+(?:\[(\d+):0\]\s+)?(\w+)', header)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # Leave a failed verdict if any dependency or tool check aborts this run.
    report = dict(schema_version=1, verdict='FAIL', scope='integration only',
                  common_coverage_eligible=False)
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    lock = json.loads((ROOT / 'integration/dependencies.lock.json').read_text())
    assert set(lock) == {'schema_version', 'status', 'top_module', 'platform',
                         'components', 'packages', 'memory_macros'}
    assert lock['schema_version'] == 1 and lock['status'] == 'locked'
    assert lock['top_module'] == 'nebula_cpu_npu_top'
    assert lock['components'] == ['artifact-f978147dc8244ed0b8867cbe299baac9']
    inputs = []
    for path in sorted((ROOT / '.nebula_inputs').glob('*/artifact.json')):
        artifact = json.loads(path.read_text())
        assert artifact['content']['kind'] == 'git'
        for name in artifact['content']['paths']:
            frozen = subprocess.check_output(
                ['git', 'show', artifact['content']['commit'] + ':' + name], cwd=ROOT)
            assert (ROOT / name).read_bytes() == frozen, f'frozen input changed: {name}'
        inputs.append(dict(artifact_id=artifact['id'],
                           commit=artifact['content']['commit'],
                           files_checked=len(artifact['content']['paths'])))
    assert len(inputs) == 4
    platform = lock['platform']
    constraints = json.loads((ROOT / platform['constraints_path']).read_text())
    assert digest(ROOT / platform['constraints_path']) == platform['constraints_sha256']
    assert digest(ROOT / platform['sdc_path']) == platform['sdc_sha256']
    assert constraints['status'] == 'frozen'
    assert platform['id'] == constraints['platform'] == 'sky130hd'
    assert platform['corner'] == constraints['corner'] == 'tt_025C_1v80'
    assert platform['installation_directory'] == constraints['view_binding']['installed_root']
    assert platform['orfs_revision'] == constraints['view_binding']['orfs_revision']
    assert set(platform['views']) == set(constraints['view_binding']['views'])
    for name, view in platform['views'].items():
        frozen = constraints['view_binding']['views'][name]
        assert view['path'] == frozen['installed_path']
        assert Path(view['path']).stat().st_size == view['size']
        assert digest(view['path']) == view['sha256'] == frozen['sha256']
    assert lock['memory_macros'] == constraints['memory']['memory_macros'] == []
    assert constraints['memory']['required_views'] == []
    assert constraints['memory']['external_memories']['inside_physical_top'] is False
    sources = (ROOT / 'integration/design.f').read_text().splitlines()
    assert sources == [p['rtl_path'] for p in lock['packages']] == [
        'rtl/nebula_npu_dot4.sv', 'rtl/rv32i_five_stage_cpu.sv',
        'rtl/integration/nebula_cpu_npu_top.sv']
    for package in lock['packages']:
        assert package['content_digest'] == 'sha256:' + digest(ROOT / package['rtl_path'])
        assert package['version'] == next(i['commit'] for i in inputs
                                         if i['artifact_id'] == lock['components'][0])
        assert package['source_artifact_id'] == lock['components'][0]
    assert lock['packages'][1]['parameters'] == {'ENABLE_XNEBULA': 1}
    assert ports(ROOT / sources[1]) == ports(ROOT / sources[2]) == constraints['ports']
    assert 'rv32i_five_stage_cpu #(.ENABLE_XNEBULA(1)) core (.*);' in (ROOT / sources[2]).read_text()
    address = json.loads((ROOT / 'integration/address_map.json').read_text())
    assert address['top_module'] == lock['top_module'] and address['memory_macros'] == []
    for target, key in zip(address['targets'][:2], ['instruction_bytes', 'data_bytes']):
        assert target['placement'] == 'external'
        assert target['size_bytes'] == constraints['memory']['external_memories'][key]
        assert int(target['end_inclusive'], 16) - int(target['base'], 16) + 1 == target['size_bytes']
    tools = dict(verilator=command(['verilator', '--version'], 'verilator_version.log').strip(),
                 python=command(['python3', '--version'], 'python_version.log').strip())
    assert tools['verilator'].startswith('Verilator 5.048 '), tools['verilator']
    lint = ['verilator', '-Wall', '-Wno-UNUSEDSIGNAL', '--top-module', lock['top_module'],
            '-f', 'integration/design.f']
    command(lint + ['--lint-only'], 'lint.log')
    command(lint + ['--json-only', '--json-only-output', 'build/integration/elaboration.tree.json',
                    '--json-only-meta-output', 'build/integration/elaboration.meta.json',
                    '--Mdir', 'build/integration/elaboration'], 'elaboration.log')
    tree = json.loads((OUT / 'elaboration.tree.json').read_text())
    names = [m['origName'] for m in tree['modulesp']]
    assert sorted(names) == sorted(['nebula_cpu_npu_top', 'rv32i_five_stage_cpu', 'nebula_npu_dot4'])
    libs = OUT / 'tool-libs'
    libs.mkdir(exist_ok=True)
    link = libs / 'libatomic.so'
    if not link.exists():
        link.symlink_to('/usr/lib64/libatomic.so.1')
    command(['verilator', '--binary', '--timing', '-j', '2', '-Wall',
             '-Wno-UNUSEDSIGNAL', '-Wno-TIMESCALEMOD', '-CFLAGS', '-std=c++20',
             '-LDFLAGS', '-L../tool-libs', '--top-module', 'integration_smoke_tb',
             '--Mdir', 'build/integration/smoke', '-o', 'sim', '-f', 'integration/design.f',
             'integration/integration_smoke_tb.sv'], 'smoke_build.log')
    smoke = command([str(OUT / 'smoke/sim')], 'smoke.log')
    assert 'INTEGRATION_SMOKE_PASS directed_transactions=10' in smoke
    report.update(verdict='PASS', top_module=lock['top_module'], components=lock['components'],
                  configuration={'core.ENABLE_XNEBULA': 1}, inputs=inputs, tools=tools,
                  ordered_files=sources, platform=platform['id'], corner=platform['corner'],
                  checks={'frozen_inputs': 'PASS', 'dependencies': 'PASS', 'address_map': 'PASS',
                          'public_ports': 'PASS', 'lint': 'PASS', 'elaboration': 'PASS', 'smoke': 'PASS'},
                  technology_views_checked=len(platform['views']), memory_macro_count=0,
                  lint_waivers={'UNUSEDSIGNAL': 'Existing shared decode/payload fields; upstream waiver retained.',
                               'TIMESCALEMOD': 'Simulation build only: testbench time unit versus untimed frozen RTL.'},
                  smoke={'directed_transactions': 10, 'transaction_limit': 20,
                         'dmem_requests': 9, 'dmem_responses': 9, 'npu_operations': 1,
                         'program_instructions': 16, 'normal_retirements': 15, 'traps': 1,
                         'reset_low_ns': 300, 'coverage': ['reset release at reset PC',
                         'external instruction read', 'external data read/write',
                         'NPU operand write/result read and normal writeback',
                         'tohost read/write', 'lane-1 byte mask preserves other bytes',
                         'invalid-address error response and precise load trap']},
                  evidence=['build/integration/lint.log', 'build/integration/elaboration.log',
                            'build/integration/elaboration.tree.json', 'build/integration/elaboration.meta.json',
                            'build/integration/smoke_build.log',
                            'build/integration/smoke.log'],
                  not_checked=['Full functional/performance acceptance', 'formal equivalence',
                               'synthesis', 'STA', 'PnR', 'DRC/LVS'],
                  risk='Local integration PASS contributes no formal common acceptance coverage; physical closure remains downstream.')
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('INTEGRATION_PASS: frozen inputs, dependencies, ports, lint, elaboration, smoke; 10 transactions')


if __name__ == '__main__':
    main()

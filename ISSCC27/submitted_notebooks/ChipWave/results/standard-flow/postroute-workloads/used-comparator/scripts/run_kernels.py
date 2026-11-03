#!/usr/bin/env python3
"""Compile one frozen CPU/NPU snapshot and compare every retired instruction."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from kernel_programs import BASE, OUTPUT, build_extension, build_kernel, interpret, self_check, signed, write_elf

ENTRY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENTRY / 'verification'))
from sail_commit import compare_commits


def execute(command, log, timeout):
    result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    log.write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f'command failed ({result.returncode}); see {log}: {command[0]}')
    return result.stdout


def run(project, output, seeds):
    self_check()
    output.mkdir(parents=True, exist_ok=True)
    sources = sorted(project.glob('rtl/**/*.sv')) + sorted(project.glob('rtl/**/*.v'))
    if not sources:
        raise ValueError('no RTL sources in the selected delivery')
    tb = ENTRY / 'verification/tb_cpu_npu.sv'
    inputs = {str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    inputs['tb_cpu_npu.sv'] = hashlib.sha256(tb.read_bytes()).hexdigest()
    obj = output / 'obj'
    execute(['verilator', '--binary', '--timing', '--assert', '-Wno-fatal', '-j', '4',
             '--top-module', 'tb_cpu_elf', '--Mdir', str(obj), *map(str, sources), str(tb)],
            output / 'compile.log', 600)
    rows = []
    for name in ('XNEBULA', 'DOT64', 'GEMM8', 'CONV3'):
        for accelerated in ((True,) if name == 'XNEBULA' else (False, True)):
            mode = 'xdot4' if accelerated else 'scalar'
            case = output / f'{name}-{mode}'
            case.mkdir(exist_ok=True)
            p, image, expected_values, data = build_extension() if name == 'XNEBULA' else build_kernel(name, accelerated)
            reference, final_memory = interpret(image)
            (case / 'memory.hex').write_text(''.join(f'{x:02x}\n' for x in image))
            (case / 'program.S').write_text('\n'.join(p.assembly) + '\n')
            write_elf(case / 'program.elf', p.finish(), data)
            (case / 'reference.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in reference))
            (case / 'expected_outputs.json').write_text(json.dumps(expected_values) + '\n')
            for seed in seeds:
                trace = case / f'trace-{seed}.jsonl'
                stdout = execute([str(obj / 'Vtb_cpu_elf'), f'+IMAGE={case / "memory.hex"}',
                                  f'+TRACE={trace}', f'+SEED={seed}', '+MAX_CYCLES=2000000'],
                                 case / f'run-{seed}.log', 180)
                observed = [json.loads(line) for line in trace.read_text().splitlines()]
                verdict = compare_commits(reference, observed)
                stores = {e['mem_addr']: signed(e['mem_wdata']) for e in observed
                          if e.get('kind') == 'commit' and e.get('mem_wstrb') == 15
                          and OUTPUT <= e['mem_addr'] < OUTPUT + 4 * len(expected_values)}
                observed_outputs = [stores.get(OUTPUT + 4 * i) for i in range(len(expected_values))]
                match = re.search(r'CPU_ELF_PASS cycles=(\d+) commits=(\d+) traps=(\d+)', stdout)
                passed = bool(match) and verdict['passed'] and int(match[3]) == 0 and observed_outputs == expected_values
                row = dict(workload=name, mode=mode, seed=seed, passed=passed,
                           cycles=int(match[1]) if match else None,
                           commits=int(match[2]) if match else None,
                           outputs=observed_outputs, expected_outputs=expected_values,
                           output_observation='retired output stores, cross-checked against accepted bus writes by the testbench', comparison=verdict,
                           trace=str(trace.relative_to(output)),
                           firmware_sha256=hashlib.sha256((case / 'program.elf').read_bytes()).hexdigest())
                rows.append(row)
                summary = dict(schema_version=1, passed=all(r['passed'] for r in rows),
                               boundary='total testbench cycles, including two reset cycles through committed completion store; setup, loads, packing and output stores included',
                               input_sha256=inputs, rows=rows)
                (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
                print(json.dumps({k: row[k] for k in ('workload', 'mode', 'seed', 'passed', 'cycles', 'commits')}), flush=True)
                if not passed:
                    raise RuntimeError(f'kernel differential failed: {row}')
    speedups = [{"workload": name, "seed": seed,
                 "scalar_cycles": next(r['cycles'] for r in rows if r['workload'] == name and r['seed'] == seed and r['mode'] == 'scalar'),
                 "xdot4_cycles": next(r['cycles'] for r in rows if r['workload'] == name and r['seed'] == seed and r['mode'] == 'xdot4')}
                for name in ('DOT64', 'GEMM8', 'CONV3') for seed in seeds]
    for row in speedups: row['speedup'] = row['scalar_cycles'] / row['xdot4_cycles']
    summary['speedups'] = speedups
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('OPERATOR_ACCEPTANCE_PASS', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seeds', type=int, nargs='+', default=[20260925, 17, 37])
    args = parser.parse_args()
    run(args.project.resolve(), args.output.resolve(), args.seeds)

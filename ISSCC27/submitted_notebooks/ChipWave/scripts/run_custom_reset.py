#!/usr/bin/env python3
"""Inject integrated reset at six ages relative to a real NPU handshake."""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from kernel_programs import build_extension, interpret
from run_kernels import execute

ENTRY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENTRY / 'verification'))
from sail_commit import compare_commits


def run(project, output):
    output.mkdir(parents=True, exist_ok=True)
    source = (ENTRY / 'verification/tb_cpu_npu.sv').read_text()
    replacements = {
        'int trace_fd;': 'int trace_fd;\n  int npu_age=-1, reset_age=0;',
        'clk = 1;': '''if(rst_n && reset_when=="custom" && !reset_done && npu_age<0 &&
        dut.core.npu_req_valid && dut.core.npu_req_ready) npu_age=0;
    clk = 1;''',
        'void\'($value$plusargs("RESET_WHEN=%s", reset_when));': '''void'($value$plusargs("RESET_WHEN=%s", reset_when));
    void'($value$plusargs("RESET_AGE=%d", reset_age));''',
        '((reset_when == "alu"': '((reset_when == "custom" && npu_age==reset_age) || (reset_when == "alu"',
        'if (host_written && host_committed) begin': '''if(npu_age>=0 && !reset_done)npu_age++;
      if (host_written && host_committed) begin''',
    }
    for before, after in replacements.items():
        assert source.count(before) == 1, before
        source = source.replace(before, after)
    tb = output / 'tb_custom_reset.sv'
    tb.write_text('// Modified: add handshake-relative custom execution reset injection.\n' + source)
    obj = output / 'obj'
    sources = sorted(project.glob('rtl/**/*.sv')) + sorted(project.glob('rtl/**/*.v'))
    execute(['verilator', '--binary', '--timing', '--assert', '-Wno-fatal', '-j', '4',
             '--top-module', 'tb_cpu_elf', '--Mdir', str(obj), *map(str, sources), str(tb)], output / 'compile.log', 600)
    _, image, _, _ = build_extension()
    expected, _ = interpret(image)
    memory = output / 'memory.hex'
    memory.write_text(''.join(f'{value:02x}\n' for value in image))
    rows = []
    for age in range(6):
        trace = output / f'trace-{age}.jsonl'
        stdout = execute([str(obj / 'Vtb_cpu_elf'), f'+IMAGE={memory}', f'+TRACE={trace}',
                          '+SEED=20260925', '+RESET_WHEN=custom', f'+RESET_AGE={age}',
                          '+MAX_CYCLES=200000'], output / f'run-{age}.log', 180)
        actual = [json.loads(line) for line in trace.read_text().splitlines()]
        result = compare_commits(expected, actual)
        assert result['passed'] and 'CPU_RESET_INJECT phase=custom' in stdout and 'CPU_ELF_PASS' in stdout, result
        rows.append({'age_after_real_acceptance': age, 'passed': True, 'matched_retirements': result['matched']})
        print(f'CUSTOM_RESET_PASS age={age} matched={result["matched"]}', flush=True)
    (output / 'summary.json').write_text(json.dumps({'passed': True, 'rows': rows,
         'checker_sha256': hashlib.sha256(tb.read_bytes()).hexdigest(),
         'observation': 'test-only internal NPU valid/ready handshake; DUT unchanged'}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.project.resolve(), args.output.resolve())

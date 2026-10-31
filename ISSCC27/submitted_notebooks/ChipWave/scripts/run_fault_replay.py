#!/usr/bin/env python3
"""Replay three declared NPU mutations and preset repairs with the fixed checker.

This educational test measures checker sensitivity, not AI repair performance.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'results/standard-flow/design/rtl/nebula_npu_dot4.sv'
CHECKER = ROOT / 'verification/npu_acceptance_tb.sv'
FAULTS = (
    ('signedness', 'Signed INT8 lane multiplication',
     'p0 <= $signed(req_a[7:0]) * $signed(req_b[7:0]);',
     'p0 <= $unsigned(req_a[7:0]) * $unsigned(req_b[7:0]);',
     'NPU arithmetic/latency'),
    ('reduction-width', 'Widen products before reduction',
     'pair0 <= $signed({p0[15], p0}) + $signed({p1[15], p1});',
     "pair0 <= $signed(16'($signed({p0[15], p0}) + $signed({p1[15], p1})));",
     'NPU arithmetic/latency'),
    ('kill-priority', 'Kill suppresses the response immediately',
     'assign rsp_valid = rst_n && !kill && phase == RSP;',
     'assign rsp_valid = rst_n && phase == RSP;',
     'cancellation does not dominate interface'),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def mutate(source, old, new):
    if source.count(old) != 1 or new in source:
        raise ValueError('Mutation anchor must occur exactly once; source changed.')
    faulty = source.replace(old, new)
    repaired = faulty.replace(new, old)
    assert repaired == source and faulty != source
    return faulty, repaired


def run(output):
    source_bytes, checker_bytes = SOURCE.read_bytes(), CHECKER.read_bytes()
    source = source_bytes.decode()
    variants = [('control', 'accepted', source, None)]
    for name, _, old, new, expected in FAULTS:
        faulty, repaired = mutate(source, old, new)
        variants.extend([(name, 'faulty', faulty, expected),
                         (name, 'preset-repair', repaired, None)])
    # Existing experiment evidence is immutable; use a new output directory.
    output.mkdir(parents=True, exist_ok=False)
    tools = {name: shutil.which(name) for name in ('iverilog', 'vvp')}
    if not all(tools.values()):
        raise RuntimeError('Source the pinned tool environment first.')
    for name, path in tools.items():
        r = subprocess.run([path, '-V'], text=True, capture_output=True, timeout=20)
        (output / (name + '-version.log')).write_text(r.stdout + r.stderr)
        tools[name] = {'path': path, 'resolved_path': str(Path(path).resolve()),
                       'version_exit_code': r.returncode}
    rows = []
    for name, treatment, rtl, expected in variants:
        directory = output / (name + '-' + treatment)
        directory.mkdir()
        (directory / 'nebula_npu_dot4.sv').write_text(rtl)
        (directory / 'npu_acceptance_tb.sv').write_bytes(checker_bytes)
        commands = []
        started = time.monotonic()
        compile_cmd = [tools['iverilog']['path'], '-g2012', '-s', 'npu_acceptance_tb',
                       '-o', 'sim', 'nebula_npu_dot4.sv', 'npu_acceptance_tb.sv']
        c = subprocess.run(compile_cmd, cwd=directory, text=True,
                           capture_output=True, timeout=60)
        (directory / 'compile.log').write_text(c.stdout + c.stderr)
        commands.append({'argv': compile_cmd, 'exit_code': c.returncode})
        if c.returncode:
            raise RuntimeError('Compilation failure is not a detected functional fault.')
        sim_cmd = [tools['vvp']['path'], 'sim']
        r = subprocess.run(sim_cmd, cwd=directory, text=True,
                           capture_output=True, timeout=180)
        log = r.stdout + r.stderr
        (directory / 'simulation.log').write_text(log)
        commands.append({'argv': sim_cmd, 'exit_code': r.returncode})
        passed = r.returncode == 0 and 'NPU_ACCEPTANCE_PASS cases=264202 cancellations=8' in log
        detected = expected is not None and r.returncode != 0 and expected in log
        row = {'fault': name, 'treatment': treatment, 'compiled': True,
               'checker_passed': passed, 'declared_fault_detected': detected,
               'expected_failure': expected, 'elapsed_seconds': time.monotonic() - started,
               'rtl_sha256': sha(rtl.encode()), 'checker_sha256': sha(checker_bytes),
               'evidence_directory': directory.name, 'commands': commands}
        (directory / 'receipt.json').write_text(json.dumps(row, indent=2) + '\n')
        rows.append(row)
        assert detected if expected else passed, row
        print(name, treatment, 'DETECTED' if detected else 'PASS', flush=True)
    assert SOURCE.read_bytes() == source_bytes and CHECKER.read_bytes() == checker_bytes
    summary = {'complete': True, 'scope': 'Educational, deliberately injected faults; fixed-checker sensitivity and preset repair replay',
               'repair_origin': 'Operator-defined inverse edits returning byte-identical accepted RTL; no model repair trial',
               'ai_repair_comparison_measured': False, 'held_out_transfer_measured': False,
               'source': str(SOURCE.relative_to(ROOT)), 'source_sha256': sha(source_bytes),
               'checker': str(CHECKER.relative_to(ROOT)), 'checker_sha256': sha(checker_bytes),
               'tool_identities': tools, 'rows': rows,
               'contracts': [{'fault': n, 'requirement': req} for n, req, *_ in FAULTS]}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('FAULT_REPLAY_PASS: control, three detected faults, three preset repairs')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    run(args.output.resolve())

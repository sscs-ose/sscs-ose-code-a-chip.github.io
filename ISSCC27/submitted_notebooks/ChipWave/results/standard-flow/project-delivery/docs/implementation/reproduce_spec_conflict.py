#!/usr/bin/env python3
"""Replay the historical counterexample against the corrected signed baseline."""
import hashlib
import json
import sys
from check_rtl import ROOT, OUT, RTL, BASE, build, command, ins_i, ins_j, check_inputs


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inputs = check_inputs()
    libs = OUT / 'tool-libs'
    libs.mkdir(exist_ok=True)
    link = libs / 'libatomic.so'
    if not link.exists():
        link.symlink_to('/usr/lib64/libatomic.so.1')
    image = OUT / 'conflict.hex'
    image.write_text(''.join(f'{word:08x}\n' for word in
                             [ins_j(1, 8), ins_i(0, 0, 0), ins_i(2, 0, 2), ins_j(0, 0)]))
    runs = []
    for enable in (0, 1):
        binary = build('selfcheck_cpu_tb', RTL + ['docs/implementation/selfcheck_cpu_tb.sv'], 'cpu'+str(enable), enable)
        for invalid_word in ['deadbeef', '34002073', '30200073', '00000000']:
            trace = command([str(binary), f'+PROGRAM={image}', '+EVENTS=2',
                             f'+INVALID_WORD={invalid_word}'], f'redirect_{enable}_{invalid_word}.log')
            fetches = [(int(fields[1]), int(fields[2], 16))
                       for line in trace.splitlines() if (fields := line.split()) and fields[0] == 'F']
            commits = [line.split() for line in trace.splitlines() if line.startswith('C ')]
            assert len(commits) == 2 and not any(line.startswith(('T ', 'Q ')) for line in trace.splitlines())
            assert [int(c[2], 16) for c in commits] == [BASE, BASE + 8]
            assert [int(c[5], 16) for c in commits] == [BASE + 4, 2]
            first = next(cycle for cycle, pc in fetches if pc == BASE)
            target = next(cycle for cycle, pc in fetches if pc == BASE + 8)
            runs.append({'enable': enable, 'invalid_word': invalid_word, 'first_fetch_edge': first,
                         'expected_target_fetch_edge': first + 3,
                         'actual_target_fetch_edge': target,
                         'design_rule_pass': target == first + 3})
    blocked = any(not run['design_rule_pass'] for run in runs)
    result = {'engineering_verdict': 'fail_redirect_regression' if blocked else 'pass_redirect_regression',
              'historical_conflict_id': 'IF-UNOWNED-CSR-SERIALIZATION', 'runs': runs, 'inputs': inputs,
              'run_scope': 'local_selfcheck', 'common_coverage_eligible': False, 'local_common_contribution': 0,
              'verilator_version': command(['verilator', '--version']).strip(),
              'rtl_sha256': {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in RTL}}
    (OUT / 'spec_conflict_resolution.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 1 if blocked else 0


if __name__ == '__main__':
    sys.exit(main())

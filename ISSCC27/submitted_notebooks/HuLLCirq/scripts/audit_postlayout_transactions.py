"""Check the timed test's pre-edge samples against the external receiving edge.

This reads observed VCD values only. It does not cure VCD delta coalescing or
qualify a timing model. Original data/config/expected values stay in the plan.
"""
from pathlib import Path
from bisect import bisect_left, bisect_right
import argparse
import hashlib
import json

SIGNALS = ('clk', 'rst', 'config_data', 'config_data_valid', 'config_data_ready',
           'load_data', 'load_data_valid', 'load_data_ready', 'output_data',
           'output_data_valid', 'output_data_ready', 'busy', 'job_done')


def audit(path):
    scopes, paths, traces, widths = [], {}, {}, {}
    header, now = True, 0
    with Path(path).open('r', encoding='ascii') as stream:
        for raw in stream:
            line = raw.strip()
            if header:
                if not line.startswith('$'):
                    continue
                while '$end' not in line:
                    line += ' ' + next(stream).strip()
                items = line.split()
                if items[0] == '$scope': scopes.append(items[2])
                elif items[0] == '$upscope': scopes.pop()
                elif items[0] == '$timescale':
                    assert ''.join(items[1:-1]) == '1ps'
                elif items[0] == '$var' and scopes == ['hullcirq_global_tb'] and items[4] in SIGNALS:
                    name, code, width = items[4], items[3], int(items[2])
                    assert name not in paths
                    paths[name] = code; traces.setdefault(code, []); widths[code] = width
                elif items[0] == '$enddefinitions': header = False
                continue
            if not line or line.startswith('$'): continue
            if line.startswith('#'): now = int(line[1:]); continue
            if line[0] in '01xXzZ': value, code = line[0].lower(), line[1:]
            elif line[0] in 'bB':
                value, code = line[1:].split(); value = value.lower()
            else: continue
            if code not in traces: continue
            pad = value[0] if value[0] in 'xz' else '0'
            value = value.rjust(widths[code], pad)
            if not traces[code] or traces[code][-1][1] != value: traces[code].append((now, value))
    assert set(paths) == set(SIGNALS) and not header
    clock = traces[paths['clk']]
    assert clock[0] == (0, '0')
    edges = [time for i, (time, value) in enumerate(clock) if i and value == '1']
    assert edges and edges == [25000 + 50000*i for i in range(len(edges))]
    observations, changes, failures = 0, 0, []
    for name in SIGNALS[1:]:
        trace = traces[paths[name]]; times = [time for time, _ in trace]
        for edge in edges:
            lower = edge - 1000
            a, b = bisect_right(times, lower)-1, bisect_right(times, edge)-1
            between = [(time, value) for i, (time, value) in
                       enumerate(trace[bisect_left(times,lower):bisect_right(times,edge)], bisect_left(times,lower)) if i]
            observations += 1
            if a < 0 or b < 0 or trace[a][1] != trace[b][1] or between:
                changes += len(between)
                failures.append({'signal':name, 'sample_ps':lower, 'receiving_edge_ps':edge,
                                 'changes':between, 'sample_value':trace[a][1] if a>=0 else None,
                                 'receiving_value':trace[b][1] if b>=0 else None})
    with Path(path).open('rb') as raw:
        digest = hashlib.file_digest(raw,'sha256').hexdigest()
    return {'kind':'hullcirq-observed-external-sample-correspondence-v1',
            'status':'Passed' if not failures else 'Unsupported',
            'scope':'recorded VCD only; same-timestamp delta events may be omitted by native writer',
            'clock_period_ps':50000, 'first_receiving_edge_ps':25000, 'sample_margin_ps':1000,
            'receiving_edges':len(edges), 'signal_edge_observations':observations,
            'recorded_changes_in_sample_windows':changes, 'diagnostics':failures,
            'vcd_sha256':digest,
            'S14_adopted':False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('vcd'); parser.add_argument('new_report')
    args = parser.parse_args(); result = audit(args.vcd)
    with Path(args.new_report).open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='diagnostics'}))

"""Reuse the published waveform audit for the three capacity-task workloads."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json


def check(root):
    summary = json.loads((root / 'summary.json').read_text())
    manifest_path = root / 'experiment-manifest.json'
    storage = json.loads(manifest_path.read_text())['vcd_storage'] if manifest_path.exists() else {}
    rows = []
    period_ps = round(summary['clock_period_ns'] * 1000)
    assert period_ps > 0 and period_ps % 2 == 0
    assert summary['clock_duty_percent'] == 50
    reset_ps = round(summary['reset_low_ns'] * 1000)
    assert reset_ps == 3 * period_ps
    for row in summary['rows']:
        path = root / row['vcd']
        compressed = False
        if not path.exists():
            stored = storage[row['vcd']]
            assert stored['encoding'] == 'gzip' and stored['decoded_sha256'] == row['vcd_sha256']
            path = root / stored['path']; compressed = True
        assert path.resolve().is_relative_to(root.resolve()) and path.is_file() and not path.is_symlink()
        scope = []; ids = {}; header = True; stamp = 0; states = {}
        rises = []; falls = []; releases = []; initial_reset = None; ps = False
        digest = hashlib.sha256()
        with (gzip.open(path, 'rb') if compressed else path.open('rb')) as handle:
            for raw in handle:
                digest.update(raw); line = raw.decode('ascii').strip()
                if header:
                    if line.startswith('$timescale '):
                        ps = line == '$timescale 1ps $end'
                    elif line.startswith('$scope '):
                        scope.append(line.split()[2])
                    elif line.startswith('$upscope'):
                        scope.pop()
                    elif line.startswith('$var ') and scope == ['tb_cpu_elf']:
                        parts = line.split()
                        if parts[4] in ('clk', 'rst_n'):
                            assert parts[2] == '1'
                            ids[parts[3]] = parts[4]
                    elif line.startswith('$enddefinitions'):
                        assert ps and set(ids.values()) == {'clk', 'rst_n'}
                        header = False
                elif line.startswith('#'):
                    new = int(line[1:]); assert new >= stamp; stamp = new
                elif line and line[0] in '01xz' and line[1:] in ids:
                    name = ids[line[1:]]; value = line[0]; previous = states.get(name)
                    assert value in '01', 'Unknown primary clock/reset state'
                    states[name] = value
                    if name == 'rst_n' and previous is None:
                        initial_reset = (stamp, value)
                    if name == 'clk' and previous == '0' and value == '1':
                        rises.append(stamp)
                    if name == 'clk' and previous == '1' and value == '0':
                        falls.append(stamp)
                    if name == 'rst_n' and previous == '0' and value == '1':
                        releases.append(stamp)
        assert digest.hexdigest() == row['vcd_sha256']
        assert initial_reset == (0, '0'), 'VCD does not capture the actual reset assertion'
        assert len(rises) > 10 and len(rises) == len(falls)
        periods = {b - a for a, b in zip(rises, rises[1:])}
        highs = {b - a for a, b in zip(rises, falls)}
        assert periods == {period_ps} and highs == {period_ps // 2}
        assert releases == [reset_ps]
        phase = releases[0] - max(t for t in rises if t < releases[0])
        assert phase == period_ps // 2 and row['activity_start_ps'] == releases[0]
        assert row['activity_start_ps'] < row['activity_end_ps'] <= stamp
        rows.append(dict(workload=row['workload'], measured_clock_period_ps=periods.pop(),
            measured_clock_high_ps=highs.pop(), rising_edges_checked=len(rises),
            measured_reset_assertion_ps=initial_reset[0], measured_reset_release_ps=releases[0],
            measured_reset_release_phase_ps=phase, vcd_sha256=row['vcd_sha256'],
            activity_start_ps=row['activity_start_ps'], activity_end_ps=row['activity_end_ps']))
    assert len(rows) == 3 and {r['workload'] for r in rows} == {'short', 'mixed', 'long'}
    return dict(status='passed', scope='Actual primary clock/reset events from each full VCD; no clock-tree/SDF timing-signoff claim', rows=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Previous measurement preserved')
    result = check(args.directory.resolve())
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print('POSTROUTE_CLOCK_RESET_MEASUREMENT_PASS')

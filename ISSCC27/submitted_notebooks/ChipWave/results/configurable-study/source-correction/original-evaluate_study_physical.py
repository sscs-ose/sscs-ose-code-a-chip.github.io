"""Bind functional gate activity, extracted parasitics and energy to one physical run."""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

from study_protocol import WORKLOADS, score, write_json

CASE = Path(__file__).resolve().parents[1]


def checked(command, log, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return {'exit_code': 124, 'timed_out': True, 'command': command}
    with log.open('w') as handle:
        process = subprocess.Popen(command, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            process.wait(timeout=remaining)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    return {'exit_code': process.returncode, 'timed_out': timed_out, 'command': command}


def evaluate(run, baseline=None, revision=None):
    run = Path(run).resolve()
    if revision is not None and not re.fullmatch(r'[a-z0-9_-]+', revision):
        raise ValueError('Invalid evaluation revision label')
    suffix = '-'+revision if revision else ''
    target = run / ('evaluation'+suffix+'.json')
    if target.exists():
        raise ValueError('Existing evaluation preserved: ' + str(target))
    physical = json.loads((run / 'summary.json').read_text())
    reference = None if baseline is None else json.loads(Path(baseline).read_text())
    if reference is not None:
        for key in ('rtl_sha256', 'period_ps', 'sdc_sha256', 'threads'):
            if physical['manifest'][key] != reference['physical_manifest'][key]:
                raise ValueError('Candidate differs from the frozen baseline: ' + key)
    raw_files = list((run / 'evidence').glob('orfs-work/logs/**/6_report.json'))
    raw = json.loads(raw_files[0].read_text()) if len(raw_files) == 1 else {}
    result = {'schema_version': 1, 'physical_qualified': physical['physical_qualified'],
              'rank_eligible': False, 'configuration': physical['configuration'],
              'period_ps': physical['manifest']['period_ps'],
              'physical_wall_seconds': physical['physical_wall_seconds'],
              'failure_classes': list(physical.get('failure_classes', [])),
              'candidate_index': 0, 'cell_area_um2': raw.get('finish__design__instance__area__stdcell'),
              'die_area_um2': raw.get('finish__design__die__area'),
              'setup_slack_ns': raw.get('finish__timing__setup__ws'),
              'hold_slack_ns': raw.get('finish__timing__hold__ws'),
              'electrical_violations': {key: raw.get('finish__timing__drv__' + key)
                                        for key in ('max_slew', 'max_cap', 'max_fanout')},
              'energy_j': {}, 'estimated_power_w': {}, 'postprocessing_commands': [],
              'physical_manifest': physical['manifest']}
    if raw:
        if any(raw.get('finish__timing__' + kind + '__ws', -1) < 0 for kind in ('setup', 'hold')):
            result['failure_classes'].append('timing')
        if any(value != 0 for value in result['electrical_violations'].values()):
            result['failure_classes'].append('electrical')
    started = time.monotonic()
    if physical['physical_qualified']:
        output = run / ('workloads'+suffix)
        if output.exists():
            raise ValueError('Partial workload evidence preserved; use an explicitly versioned evaluation recovery')
        deadline = started + 1800
        if not (run/'evidence/measurement-source.json').exists():
            command = [sys.executable, str(CASE/'scripts/export_study_sta_views.py'), '--run', str(run)]
            exported = checked(command, run/('measurement-export'+suffix+'-driver.log'), deadline)
            result['postprocessing_commands'].append(exported)
            if exported['exit_code'] != 0:
                result['failure_classes'].append('measurement_export_failed')
                result['postprocess_wall_seconds'] = time.monotonic() - started
                result['total_wall_seconds'] = result['physical_wall_seconds'] + result['postprocess_wall_seconds']
                write_json(target, result)
                return result
        command = [sys.executable, str(CASE/'scripts/run_postroute_workloads.py'),
                   '--output', str(output), '--source', str(run/'evidence'),
                   '--period-ps', str(result['period_ps'])]
        first = checked(command, run/('workload'+suffix+'-driver.log'), deadline)
        result['postprocessing_commands'].append(first)
        if first['exit_code'] == 0:
            command = [sys.executable, str(CASE/'scripts/check_postroute_waveforms.py'),
                       str(output), '--output', str(output/'waveform-audit.json')]
            second = checked(command, run/('waveform-audit'+suffix+'-driver.log'), deadline)
            result['postprocessing_commands'].append(second)
            if second['exit_code'] == 0:
                summary = json.loads((output/'summary.json').read_text())
                rows = summary['rows']
                if {row['workload'] for row in rows} != set(WORKLOADS) or len(rows) != 3:
                    raise ValueError('Incomplete workload population')
                result['energy_j'] = {row['workload']: row['estimated_energy_j'] for row in rows}
                result['estimated_power_w'] = {row['workload']: row['estimated_power_w']['total'] for row in rows}
                result['measurement_qualified'] = bool(summary.get('measurement_qualified'))
                result['rank_eligible'] = result['measurement_qualified']
                result['power_scope'] = summary['power_scope']
                result['activity_and_parasitic_annotation'] = [
                    {'workload': row['workload'], 'activity': row['activity_annotation'],
                     'parasitics': row['parasitic_annotation']} for row in rows]
        if not result['rank_eligible']:
            result['failure_classes'].append('measurement_incomplete')
    result['postprocess_wall_seconds'] = time.monotonic() - started
    result['total_wall_seconds'] = result['physical_wall_seconds'] + result['postprocess_wall_seconds']
    result['failure_classes'] = sorted(set(result['failure_classes']))
    if result['rank_eligible']:
        reference = result if reference is None else reference
        if not reference['rank_eligible']:
            raise ValueError('Baseline lacks qualified normalization measurements')
        result.update(score(result['cell_area_um2'], result['energy_j'],
                            reference['cell_area_um2'], reference['energy_j']))
    write_json(target, result)
    print(json.dumps({'evaluation_finished': True, 'rank_eligible': result['rank_eligible'],
                      'score': result.get('score'), 'run': str(run)}), flush=True)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--baseline', type=Path, help='Common baseline evaluation.json; omit only for baseline measurement')
    p.add_argument('--revision', help='Explicit new measurement revision; retains all previous evidence')
    args = p.parse_args()
    evaluate(args.run, args.baseline, args.revision)

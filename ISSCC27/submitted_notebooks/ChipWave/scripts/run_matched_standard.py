#!/usr/bin/env python3
"""Rebuild regenerated RTL under the original 95 MHz experiment settings."""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from run_frequency_search import CASE, prepare, digest, collect_failed
from collect_physical import collect
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore


def run(output):
    if output.exists():
        raise ValueError('Existing experiment preserved; choose a new output directory.')
    source = CASE / 'results/standard-flow/design'
    selected = json.loads((source / 'selected-delivery.json').read_text())
    baseline = next(r for r in json.loads((CASE / 'results/frequency/summary.json').read_text())['rows']
                    if r['target_mhz'] == 95)
    assert baseline['qualified'] and baseline['source_unchanged']
    os.environ.update(ORFS_ROOT=str(CASE / 'toolchain/orfs'), NUM_CORES='2')
    flow = json.loads((CASE / 'toolchain/orfs/source-manifest.json').read_text())['files']
    for f in flow:
        assert digest(CASE / 'toolchain/orfs' / f['path']) == f['sha256']
    output.mkdir(parents=True)
    plan = {'complete': False, 'target_mhz': 95, 'period_ns': 10.5263,
            'corner': 'Sky130HD TT25C1.8V', 'utilization_percent': 40,
            'place_density': 0.55, 'abc_area': 0, 'threads': 2,
            'model_calls': 0, 'baseline_evidence': 'results/frequency/mhz95',
            'standard_source': str(source.relative_to(CASE)),
            'source_artifact': selected['id'], 'rtl_sha256': selected['exported_source_sha256'],
            'scope': 'One physical attempt on regenerated RTL with the same SDK, mapping mode, clock, IO, library and initial utilization; no RTL optimization or causal CSIR claim'}
    (output / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    project = output / 'project'
    prepare(project, 95, rtl_source=source)
    assert (project / 'physical/chip-nebula/constraints.sdc').read_bytes() == (
        CASE / 'results/frequency/mhz95/frozen-inputs/constraints.sdc').read_bytes()
    recipe = project / '.chip_nebula/recipes/cpu-npu-physical.yaml'
    started = time.monotonic()
    cmd = [sys.executable, '-m', 'chip_nebula.cli.commands', '--project-root', str(project),
           'run', str(recipe), '--workflow', 'independent-replay', '--param',
           'rtl=imported-main-rtl', '--workers', '1', '--resume']
    with (output / 'workflow.log').open('w') as log:
        result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    row = {'complete': True, 'exit_code': result.returncode,
           'wall_seconds': time.monotonic() - started, 'qualified': False,
           'source_unchanged': all(digest(project / p) == h for p, h in plan['rtl_sha256'].items()),
           'plan': plan, 'command': cmd}
    with StaticTaskGraphStore(project / '.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        row['task_state'] = store.task_state('independent-replay:physical').value
        delivery = store.deliveries('independent-replay:physical').get('report')
        attempts = store.list_attempts('independent-replay:physical')
        row['attempts'] = [{'id': a.id, 'status': a.status.value,
                            'failure': a.diagnostics.get('failure_reason', '')} for a in attempts]
        if delivery:
            collect(project, 'independent-replay', output / 'evidence', include_operators=True)
            evidence = output / 'evidence'
            raw = json.loads(next(evidence.glob('orfs-work/logs/**/6_report.json')).read_text())
            summary = json.loads((evidence / 'summary.json').read_text())
            counts = {k: raw['finish__timing__drv__' + k] for k in ('max_slew', 'max_cap', 'max_fanout')}
            row.update(metrics=summary['metrics'], electrical_violations=counts,
                       qualified=result.returncode == 0 and row['source_unchanged'] and all(v == 0 for v in counts.values()))
        elif attempts:
            row['failed_evidence'] = collect_failed(project, attempts[-1], output / 'evidence')
    for f in flow:
        assert digest(CASE / 'toolchain/orfs' / f['path']) == f['sha256']
    (output / 'summary.json').write_text(json.dumps(row, indent=2) + '\n')
    print('MATCHED_STANDARD_COMPLETE qualified=', row['qualified'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    run(parser.parse_args().output.resolve())

"""Recheck an exported reference without a model account or new physical attempt."""
import argparse
import json
import math
import shutil
import time
from pathlib import Path

from capacity_grade import function
from capacity_integration_physical import ROOT
from capacity_physical_evidence import audit
from capacity_physical_export import export, restore
from capacity_protocol import TASKS, score
from measure_capacity_integration import measure
from study_protocol import digest, write_json


def compare_measurements(recorded, reproduced):
    """Same pinned tools: allow only small floating-point reporting differences."""
    rows = []
    for key in ('cell_area', 'die_area'):
        rows.append(dict(metric=key, recorded=recorded[key], reproduced=reproduced[key]))
    if recorded['workloads'].keys() != reproduced['workloads'].keys():
        raise ValueError('Reproduction changed the workload population')
    for name, values in recorded['workloads'].items():
        for key in ('throughput', 'latency', 'power', 'energy'):
            rows.append(dict(metric=name+'/'+key, recorded=values[key],
                             reproduced=reproduced['workloads'][name][key]))
    for row in rows:
        row['matched'] = all(math.isfinite(row[key]) and row[key] > 0
                             for key in ('recorded', 'reproduced')) and math.isclose(
            row['recorded'], row['reproduced'], rel_tol=1e-6, abs_tol=0)
    return dict(passed=all(row['matched'] for row in rows), relative_tolerance=1e-6,
                absolute_tolerance=0, rows=rows)


def replay(task, output, *, remeasure=False):
    if task not in TASKS:
        raise ValueError('Unknown reference task')
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Reference replay requires a fresh output directory')
    if ROOT == output or ROOT.is_relative_to(output):
        raise ValueError('Output must not contain the source study')
    if any(output.is_relative_to(ROOT/name) for name in
           ('physical', 'trials', 'tasks', 'task-packages', 'integration', 'scripts')):
        raise ValueError('Replay output must be separate from original experiment inputs and evidence')
    attempts = json.loads((ROOT/'physical-ledger.json').read_text())['attempts']
    names = {'reference-integration-'+task, 'calibration-integration-'+task}
    selected = [row for row in attempts if row['identity'] in names and row['status'] == 'passed']
    if len(selected) != 1:
        raise ValueError('Exactly one qualified reference integration is required')
    run = ROOT/'physical'/selected[0]['identity']
    package = ROOT/'task-packages/formal'/task
    reference = package/'grader/reference.sv'
    receipt = json.loads((package/'package.json').read_text())
    if digest(reference) != receipt['source_sha256']['grader/reference.sv']:
        raise ValueError('Reference changed after task qualification')
    output.mkdir(parents=True)
    start = time.monotonic()
    result = dict(passed=False, task=task, model_calls=0, physical_runs=0,
        source_reference=str(run.relative_to(ROOT)), source_reference_sha256=digest(reference),
        fresh_measurement_requested=remeasure,
        scope='Reference replay with public sources and pinned EDA tools. No new model call, synthesis-to-GDS run, or experiment sample.',
        errors=[])
    try:
        source = output/'source/rtl'; source.mkdir(parents=True)
        shutil.copy2(reference, source/'design.sv')
        functional = function(source.parent, task, output/'function', task_package=package)
        recorded = audit(run, output/'recorded-physical-audit')
        measured = recorded
        if remeasure:
            exported, restored = output/'physical-export', output/'remeasured-physical'
            export(run, exported)
            restore(exported, restored)
            # Only derived measurements in our new copy are replaced; original evidence stays intact.
            for name in ('workloads', 'postroute', 'evidence/measurement'):
                if (restored/name).exists():
                    shutil.rmtree(restored/name)
            (restored/'evidence/measurement-source.json').unlink(missing_ok=True)
            fresh = measure(restored, task)
            if not fresh['passed']:
                raise ValueError('Fresh post-route workload or power checks failed')
            measured = audit(restored, output/'remeasured-physical-audit')
            result['measurement_comparison'] = compare_measurements(
                recorded['measurements'], measured['measurements'])
        result['score'] = score(functional, measured['gds'], measured['constraints'],
                                measured['measurements'], recorded['measurements'])
        result['evaluation_valid'] = functional['evaluation_valid']
        result['passed'] = (functional['evaluation_valid'] and result['score']['constraint_pass']
            and result.get('measurement_comparison', {'passed': True})['passed'])
    except Exception as error:
        result['errors'].append(type(error).__name__+': '+str(error))
    result['elapsed_seconds'] = time.monotonic()-start
    write_json(output/'replay.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', required=True, choices=TASKS)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--remeasure', action='store_true',
                        help='Regenerate gate activity and estimate power with the saved netlist and SPEF')
    args = parser.parse_args()
    result = replay(args.task, args.output, remeasure=args.remeasure)
    print(json.dumps(result))
    raise SystemExit(0 if result['passed'] else 1)

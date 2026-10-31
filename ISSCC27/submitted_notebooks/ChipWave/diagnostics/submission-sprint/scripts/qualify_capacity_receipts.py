"""Regenerate local prerequisite summaries from checked evidence, never archived passes."""
import argparse
import json
import shutil
from pathlib import Path

from capacity_protocol import MODELS
from study_portability import private_context
from study_protocol import digest, write_json

ROOT = Path(__file__).resolve().parents[1]
NAMES = {'properties': 'bounded-properties-status',
         'usage': 'live-usage-recorded-probes', 'integration': 'public-integration-backend'}


def properties(root):
    methods = {}
    for task in ('A1', 'A2', 'B1', 'B2'):
        folder = 'inductive-queue-invariants-v2' if task == 'B2' else 'properties-depth12'
        path = root / 'tasks' / task / 'qualification' / folder / 'qualification.json'
        row = json.loads(path.read_text())
        if row.get('passed') is not True or row.get('source_sha256') != digest(
                root / 'tasks' / task / 'grader/reference.sv'):
            raise ValueError('Reference safety evidence is failed or stale: ' + task)
        if task == 'B2':
            if row.get('original_reference_unchanged') is not True or not all(
                    row['results'][k]['passed'] is True for k in ('base', 'induction')):
                raise ValueError('Both induction and base evidence are required')
        elif row.get('bounded_depth') != 12 or not all(
                row.get(k) is True for k in ('safety_passed', 'result_reachable')):
            raise ValueError('Bounded safety/reachability evidence is incomplete')
        methods[task] = dict(evidence=str(path.relative_to(root)), sha256=digest(path),
                             method='reference induction' if task == 'B2' else 'bounded safety at depth 12')
    return dict(passed=True, methods=methods, model_calls=0, physical_runs=0,
                scope='Selected interface safety; finite progress/fairness is checked separately.')


def usage(root, output):
    from capacity_live_usage import LiveUsage
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for model in MODELS.values():
        private = private_context(root, 'capacity-connectivity', model.replace('.', '-'))
        observer = LiveUsage(private, output / (model + '.json'), model, limit=50000)
        row = observer.finish()
        if row.get('measurement_valid') is not True or row['actual_tokens'] <= 0:
            raise ValueError('Native connectivity evidence is not valid: ' + model)
        rows.append(dict(model=model, **row))
    return dict(passed=True, rows=rows, additional_model_calls=0, physical_attempts=0,
                scope='Replayed this installation\'s private native records; no transcript content exported.')


def integration(root, output):
    from capacity_backends import Backends
    output.mkdir(parents=True, exist_ok=False)
    source = output / 'input/rtl'
    source.mkdir(parents=True)
    shutil.copy2(root / 'tasks/A1/grader/reference.sv', source / 'design.sv')
    reply = Backends(output / 'backend', 'A1').integration(source.parent, 1)
    row = json.loads(Path(reply['evidence']).read_text())
    if row['status'] != 'passed' or len(row.get('checks', [])) != 3 or not all(
            r['passed'] and r['memory_response_seed'] == 17 for r in row['checks']):
        raise ValueError('Public integration callback did not pass all three workloads')
    return dict(passed=True, model_calls=0, physical_runs=0,
                evidence=str(Path(reply['evidence']).relative_to(root)),
                evidence_sha256=digest(reply['evidence']),
                scope='Actual public CPU integration callback; three workloads at development seed17.')


def run(kind):
    target = ROOT / 'checks' / (NAMES[kind] + '.json')
    if target.exists():
        raise ValueError('Retain the existing prerequisite receipt; use a new campaign for requalification')
    output = ROOT / 'checks/qualification-details' / kind
    row = (properties(ROOT) if kind == 'properties' else
           usage(ROOT, output) if kind == 'usage' else integration(ROOT, output))
    write_json(target, row)
    return row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', choices=tuple(NAMES), required=True)
    print(json.dumps(run(parser.parse_args().check)))

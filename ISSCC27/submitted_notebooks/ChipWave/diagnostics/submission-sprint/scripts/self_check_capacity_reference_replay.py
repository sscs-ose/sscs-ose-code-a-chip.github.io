"""Reference replay preserves originals and rejects changed measurements and inputs."""
import copy
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import replay_capacity_reference as replay
from capacity_protocol import GDS_GATES, CONSTRAINT_GATES
from study_protocol import digest, write_json


def check():
    values = dict(cell_area=100, die_area=200,
        workloads={name: dict(throughput=10, latency=2, power=3, energy=.3)
                   for name in ('short', 'mixed', 'long')})
    assert replay.compare_measurements(values, values)['passed']
    changed = copy.deepcopy(values); changed['workloads']['long']['power'] *= 1.001
    assert not replay.compare_measurements(values, changed)['passed']
    changed['workloads']['long']['power'] = float('nan')
    assert not replay.compare_measurements(values, changed)['passed']
    with tempfile.TemporaryDirectory(prefix='reference-replay-check-') as temp:
        root = Path(temp)
        reference = root/'task-packages/formal/A1/grader/reference.sv'
        reference.parent.mkdir(parents=True); reference.write_text('module fixture; endmodule\n')
        write_json(reference.parent.parent/'package.json',
            dict(source_sha256={'grader/reference.sv': digest(reference)}))
        write_json(root/'physical-ledger.json', dict(attempts=[
            dict(identity='reference-integration-A1', status='passed')]))
        evidence = dict(gds=dict.fromkeys(GDS_GATES, True),
            constraints=dict.fromkeys(CONSTRAINT_GATES, True), measurements=values)
        run = root/'physical/reference-integration-A1'
        for name in ('workloads/saved.json', 'postroute/qualification.json',
                     'evidence/measurement/saved.json', 'evidence/measurement-source.json'):
            write_json(run/name, dict(original=True))
        hashes = {str(path.relative_to(run)): digest(path) for path in run.rglob('*') if path.is_file()}
        def restore_fixture(source, target):
            import shutil
            shutil.copytree(run, target)
        def fresh_measurement(target, task):
            assert task == 'A1'
            assert not any((target/name).exists() for name in
                ('workloads', 'postroute', 'evidence/measurement', 'evidence/measurement-source.json'))
            return dict(passed=True)
        with patch.object(replay, 'ROOT', root), \
             patch.object(replay, 'function', return_value=dict(function=True, integration=True, evaluation_valid=True)), \
             patch.object(replay, 'audit', return_value=evidence), \
             patch.object(replay, 'export'), patch.object(replay, 'restore', side_effect=restore_fixture), \
             patch.object(replay, 'measure', side_effect=fresh_measurement):
            output = root/'replay'
            result = replay.replay('A1', output, remeasure=True)
            assert result['passed'] and result['score']['final_score'] == 50
            assert result['measurement_comparison']['passed']
            assert all(digest(run/name) == sha for name, sha in hashes.items())
            try: replay.replay('A1', run/'new-check')
            except ValueError: pass
            else: raise AssertionError('Replay may not add files to the original physical evidence')
            try: replay.replay('A1', output)
            except ValueError: pass
            else: raise AssertionError('Existing replay overwritten')
            reference.write_text('changed\n')
            try: replay.replay('A1', root/'changed')
            except ValueError: pass
            else: raise AssertionError('Changed reference accepted')
            assert not (root/'changed').exists()
    result = dict(passed=True, model_calls=0, physical_runs=0, synthetic=True,
        checks=['measurement differences and nonfinite data rejected',
                'original measurements preserved during fresh remeasurement',
                'existing destination and changed reference rejected'],
        scope='Replay mechanics; actual EDA reproduction is separately recorded')
    write_json(Path(__file__).resolve().parents[1]/'checks/reference-replay.json', result)
    return result


if __name__ == '__main__':
    print(json.dumps(check()))

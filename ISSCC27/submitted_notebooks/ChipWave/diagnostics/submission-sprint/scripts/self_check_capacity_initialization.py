"""A fresh campaign cannot inherit passes, spent attempts or private model contexts."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from init_capacity_study import budget, initialize
from study_protocol import write_json


def check():
    with tempfile.TemporaryDirectory(prefix='capacity-init-check-') as temporary:
        root = Path(temporary)
        source = root / 'original' / 'scripts'
        source.mkdir(parents=True)
        for name in ('init_capacity_study.py', 'capacity_protocol.py', 'study_protocol.py'):
            (source / name).write_bytes((Path(__file__).parent / name).read_bytes())
        (source.parent / 'campaign-freeze.json').write_text('{"qualified":true}')
        (source / 'private.txt').write_text('fixture credential, must not copy')
        target = root / 'new-study'
        receipt = initialize(target, source)
        assert receipt['qualified'] is False and receipt['model_calls'] == receipt['physical_runs'] == 0
        assert not (target / 'campaign-freeze.json').exists()
        assert not (target / 'scripts/private.txt').exists()
        assert json.loads((target / 'physical-ledger.json').read_text())['attempts'] == []
        rules = json.loads((target / 'protocol.json').read_text())
        assert not rules['pilot_launch_allowed'] and not rules['formal_launch_allowed']
        actual = json.loads(subprocess.check_output(
            [sys.executable, str(target / 'scripts/init_capacity_study.py')], text=True))
        assert actual == budget() and actual['physical_wait_hours_max'] == 873
        for invalid in (target, source.parent / 'nested'):
            try:
                initialize(invalid, source)
            except ValueError:
                pass
            else:
                raise AssertionError('Existing/nested workspace accepted')
        (source / 'linked.py').symlink_to(source / 'study_protocol.py')
        try:
            initialize(root / 'unsafe', source)
        except ValueError:
            pass
        else:
            raise AssertionError('Linked source accepted')
        assert not (root / 'unsafe').exists()
    result = dict(passed=True, model_calls=0, physical_runs=0,
                  checks=['fresh protocol', 'no copied credentials or qualification',
                          'portable budget preview', 'no reset or nested destination', 'no linked source'])
    write_json(Path(__file__).resolve().parents[1] / 'checks/new-workspace.json', result)
    return result


if __name__ == '__main__':
    print(json.dumps(check()))

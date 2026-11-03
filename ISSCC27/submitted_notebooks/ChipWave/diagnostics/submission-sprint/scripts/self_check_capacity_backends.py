"""Exercise actual admitted integration synthesis, preparation and allocation boundaries."""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from capacity_backends import Backends
from capacity_candidate import admit
from capacity_integration_physical import ROOT, CASE, prepare, verified_integration
from study_protocol import digest, write_json


def check():
    os.environ.update(ORFS_ROOT=str(CASE/'toolchain/orfs'), NUM_CORES='2')
    sys.path.append(str(CASE/'scripts'))
    rows = []
    with tempfile.TemporaryDirectory(prefix='capacity-backends-') as temp:
        root = Path(temp)
        for task in ('A1', 'B2'):
            snapshot = root/task
            (snapshot/'rtl').mkdir(parents=True)
            (snapshot/'configuration').mkdir()
            shutil.copy2(ROOT/'tasks'/task/'grader/reference.sv', snapshot/'rtl/design.sv')
            write_json(snapshot/'configuration/implementation.json', dict(
                utilization=30, density=.65, area_synthesis=True, repair_margin=10))
            backend = Backends(root/(task+'-backend'), task)
            result = backend.synthesis(snapshot, 1)
            assert result['status'] == 'passed', result
            evidence = Path(result['evidence']).parent
            manifest = prepare(root/(task+'-project'), task, candidate=evidence/'admitted')
            assert manifest['configuration'] == dict(CORE_UTILIZATION=30, PLACE_DENSITY=.65,
                ABC_AREA=1, CAP_MARGIN=10, SLEW_MARGIN=10)
            project = root/(task+'-project')
            source, _ = verified_integration(task)
            for path in source.glob('rtl/**/*.sv'):
                if 'candidate' not in path.parts:
                    assert digest(project/path.relative_to(source)) == digest(path)
            assert len(list((project/'rtl/candidate').iterdir())) == 1
            assert '10.526' in (project/'physical/chip-nebula/constraints.sdc').read_text()
            try:
                backend.physical(snapshot, 2)
            except ValueError:
                pass
            else:
                raise AssertionError('Preflight spent a physical attempt')
            # The actual physical executor is tested by the registered reference driver.
            # This negative fixture checks global allocation occurs before source admission.
            guarded = Backends(root/(task+'-guarded'), task, trial='not-registered', category='pilot')
            with patch('capacity_backends.reserve', side_effect=ValueError('prerequisite denied')) as reserve:
                try:
                    guarded.physical(snapshot, 1)
                except ValueError:
                    pass
                else:
                    raise AssertionError('Allocation denial ignored')
                reserve.assert_called_once()
                assert not list((root/(task+'-guarded')).iterdir())
            rows.append(dict(task=task, synthesis_passed=True,
                             frozen_neighbors_preserved=True, actual_physical_attempts=0))
    report = dict(passed=True, rows=rows, model_calls=0, physical_attempts=0,
                  scope='Actual full-integration generic synthesis and SDK preparation; physical dispatch negative checks')
    write_json(ROOT/'checks/controlled-backends.json', report)
    return report


if __name__ == '__main__':
    print(json.dumps(check()))

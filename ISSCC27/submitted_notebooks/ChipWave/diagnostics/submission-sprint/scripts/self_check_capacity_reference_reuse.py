"""Recheck functional/config separation and an actual reference export locally."""
import json
import shutil
import tempfile
from pathlib import Path

from capacity_candidate import admit, DEFAULT_CONFIG
from capacity_grade import function
from capacity_integration_physical import ROOT, prepare
from capacity_physical_evidence import audit
from capacity_physical_export import export, restore
from capacity_protocol import score
from study_protocol import write_json


def check():
    with tempfile.TemporaryDirectory(prefix='capacity-reference-reuse-') as directory:
        temp = Path(directory)
        snapshot = temp/'input'
        (snapshot/'rtl').mkdir(parents=True)
        shutil.copy2(ROOT/'tasks/A1/grader/reference.sv', snapshot/'rtl/design.sv')
        write_json(snapshot/'configuration/implementation.json', dict(DEFAULT_CONFIG, utilization=99))
        result = function(snapshot, 'A1', temp/'functional')
        assert result['function'] and result['integration'] and result['synthesis'], result
        admit(snapshot, 'A1', temp/'functional-admission', functional_only=True)
        for operation in (lambda: admit(snapshot, 'A1', temp/'physical-admission'),
                          lambda: prepare(temp/'project', 'A1', candidate=temp/'functional-admission')):
            try:
                operation()
            except ValueError:
                pass
            else:
                raise AssertionError('Invalid physical configuration reached physical preparation')
        write_json(ROOT/'checks/functional-config-separation.json', dict(passed=True,
            model_calls=0, physical_runs=0,
            scope='Actual reference functional/synthesis/CPU checks survive invalid physical configuration; physical admission rejects it'))
        manifest = export(ROOT/'physical/calibration-integration-A1', temp/'export')
        restore(temp/'export', temp/'restore')
        evidence = audit(temp/'restore', temp/'audit')
        result = score(dict(function=True, integration=True), evidence['gds'], evidence['constraints'],
                       evidence['measurements'], evidence['measurements'])
        assert result['constraint_pass'] and result['final_score'] == 50, result
        report = dict(passed=True, model_calls=0, physical_runs=0,
            exported_files=len(manifest['files']), self_reference_score=result['final_score'],
            scope='Actual A1 physical evidence export/restore and independent audit; final archive reproduction remains separate')
        write_json(ROOT/'checks/physical-export.json', report)
        return report


if __name__ == '__main__':
    print(json.dumps(check()))

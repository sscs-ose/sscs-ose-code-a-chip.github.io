"""Preserve protected reports while handing complete EDA diagnostics to later roles."""
import json
import tempfile
from pathlib import Path

from capacity_backends import Backends
from capacity_integration_physical import ROOT
from study_protocol import digest, write_json


def check():
    with tempfile.TemporaryDirectory(prefix='capacity-feedback-') as temp:
        root=Path(temp)
        backend=Backends(root/'protected','A1',feedback=root/'work/reports/integration/eda')
        output=root/'protected/synthesis-0001';output.mkdir()
        row=dict(status='passed',source_sha256={'rtl/design.sv':'fixture'})
        write_json(output/'result.json',row)
        (output/'evidence/reports').mkdir(parents=True)
        raw=output/'evidence/reports/timing.rpt';raw.write_text('Retained diagnostic fixture\n')
        result=backend.result(output,row)
        target=Path(json.loads(result['output'])['full_reports'])
        assert (target/'evidence/reports/timing.rpt').read_text()==raw.read_text()
        original=digest(raw)
        (target/'evidence/reports/timing.rpt').write_text('agent changed its own report copy')
        assert digest(raw)==original
        other=root/'work/reports/review';other.symlink_to(root/'protected',target_is_directory=True)
        backend.feedback=other/'eda'
        try:backend.result(output,row)
        except ValueError:pass
        else:raise AssertionError('Feedback symlink escaped workspace')
    report=dict(passed=True,model_calls=0,physical_runs=0,
                checks=['full raw EDA report handoff','protected evidence independent of agent copies','symlink rejection'])
    write_json(ROOT/'checks/backend-feedback.json',report)
    return report


if __name__=='__main__':
    print(json.dumps(check()))

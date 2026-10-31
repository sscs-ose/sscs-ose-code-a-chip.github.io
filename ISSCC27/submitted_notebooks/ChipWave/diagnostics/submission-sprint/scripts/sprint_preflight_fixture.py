"""Explicit deterministic physical substitute, restricted to the one live C3 preflight."""
import json
from pathlib import Path
from study_protocol import write_json


def handlers(config):
    root=Path(config['record']).resolve()
    allowed=Path(__file__).resolve().parents[1]/'checks/live-c3-sprint/runtime'
    if config.get('preflight_fixture')!='submission-sprint-c3' or root!=allowed:
        raise ValueError('Unknown fixture or unexpected fixture workspace')
    project=Path(config['project']).resolve()
    def physical(source, identity):
        ledger=json.loads((root/'tools/tool-ledger.json').read_text())
        count=sum(x['kind']=='physical' for x in ledger['attempts'])
        text=(source/'rtl/fixture.sv').read_text()
        passed=count==2 and '// repaired' in text
        evidence=root/f'fixture-physical-{count}.json'
        report=dict(status='passed' if passed else 'failed',fixture=True,
            actual_physical_runs=0,source_snapshot=str(source),attempt=count,
            diagnosis='Fixture marker repaired' if passed else 'Add // repaired to rtl/fixture.sv; preserve y=a',
            scope='Deterministic test substitute; no chip or PPA measurement')
        write_json(evidence,report)
        write_json(project/'reports/integration_ppa'/f'fixture-{count}.json',report)
        return dict(status=report['status'],evidence=str(evidence),
            exit_code=0 if passed else 1,output='DETERMINISTIC_FIXTURE_NOT_EDA '+json.dumps(report)+'\n')
    return dict(physical=physical)

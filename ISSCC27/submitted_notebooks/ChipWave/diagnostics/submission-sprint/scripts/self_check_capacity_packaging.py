"""Reject unfinished or altered capacity evidence before creating a submission ZIP."""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from capacity_integration_physical import ROOT,CASE
from capacity_protocol import PHYSICAL_LIMITS,TASKS
from study_protocol import write_json,digest

sys.path.append(str(CASE/'scripts'))
import package_submission as packaging


def reject(call):
    try:call()
    except ValueError:return
    raise AssertionError('Invalid submission accepted')


def check():
    current=json.loads((CASE/'results/capacity-study/export-manifest.json').read_text())
    if current['complete']:
        packaging.validate_capacity_study()
    else:
        reject(packaging.validate_capacity_study)
    assert 'experiments' in packaging.FOLDERS
    selected=set(packaging.files())
    for name in ('experiments/capacity/scripts/replay_capacity_reference.py',
                 'ChipNebula_CPU.source.json','requirements-formal.lock.txt'):
        assert CASE/name in selected
    with tempfile.TemporaryDirectory(prefix='capacity-package-gates-') as temp:
        case=Path(temp);source=case/'results/capacity-study';source.mkdir(parents=True)
        payload=source/'evidence.txt';payload.write_text('Synthetic packaging fixture\n')
        exported=dict(complete=True,files=[dict(path='evidence.txt',bytes=payload.stat().st_size,sha256=digest(payload))])
        write_json(source/'export-manifest.json',exported)
        write_json(source/'export-status.json',dict(complete=True))
        write_json(source/'checks/reference-calibration.json',dict(passed=True,references={task:{} for task in TASKS}))
        write_json(source/'campaign-freeze.json',dict(synthetic=True))
        decision=dict(formal_launch_allowed=True,stop_rule_triggered=False,campaign_sha256=digest(source/'campaign-freeze.json'))
        write_json(source/'pilot-decision.json',decision)
        ledger=dict(limits=PHYSICAL_LIMITS,absolute_total=194,attempts=[])
        write_json(source/'physical-ledger.json',ledger)
        def cohort(root,category):return dict(complete=True,terminal=8 if category=='pilot' else 84)
        with patch.object(packaging,'ROOT',case),patch('capacity_results.analyze',side_effect=cohort),\
             patch('capacity_results.read_trials',return_value=[]) as trials:
            packaging.validate_capacity_study()
            payload.write_text('Changed evidence\n');reject(packaging.validate_capacity_study)
            payload.write_text('Synthetic packaging fixture\n')
            broken=dict(decision,stop_rule_triggered=True);write_json(source/'pilot-decision.json',broken)
            reject(packaging.validate_capacity_study);write_json(source/'pilot-decision.json',decision)
            with patch('capacity_results.analyze',return_value=dict(complete=False,terminal=83)):
                reject(packaging.validate_capacity_study)
            ledger['attempts']=[dict(identity=str(i),trial='pilot-fixture',category='pilot',status='failed') for i in range(3)]
            write_json(source/'physical-ledger.json',ledger)
            trials.return_value=[dict(job=dict(id='pilot-fixture'),physical_attempts=[dict(identity=str(i)) for i in range(3)])]
            reject(packaging.validate_capacity_study)
            ledger['attempts']=[];write_json(source/'physical-ledger.json',ledger);trials.return_value=[]
            exported['files'][0]['path']='../outside';write_json(source/'export-manifest.json',exported)
            reject(packaging.validate_capacity_study)
    result=dict(passed=True,model_calls=0,physical_runs=0,actual_export_complete=current['complete'],
        checks=['actual working-copy readiness checked before packaging','used experiment scripts included in archive selection',
                'changed evidence, incomplete cohort and pilot stop rejected','third physical attempt and unsafe export path rejected'],
        scope='Actual working-copy readiness plus synthetic completed-cohort admission mechanics; not final archive reproduction or an independent judge verdict')
    write_json(ROOT/'checks/submission-packaging.json',result)
    return result


if __name__=='__main__':print(json.dumps(check()))

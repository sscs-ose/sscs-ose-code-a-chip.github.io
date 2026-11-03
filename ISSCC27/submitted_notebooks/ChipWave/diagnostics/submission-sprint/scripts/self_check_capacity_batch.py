"""A serial batch resumes between trials, never by replacing a failed/partial trial."""
import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import run_capacity_study as study
from capacity_protocol import protocol
from study_protocol import write_json


def check():
    with tempfile.TemporaryDirectory(prefix='capacity-batch-check-') as temp:
        root=Path(temp);rules=protocol();rules['pilot_jobs']=rules['pilot_jobs'][:2]
        write_json(root/'protocol.json',rules);calls=[]
        def child(command,**kwargs):
            identity=command[-1];calls.append(identity)
            job=next(j for j in rules['pilot_jobs'] if j['id']==identity)
            write_json(root/'trials/pilot'/identity/'result.json',dict(job=job,terminal=True,
                status='infrastructure_error' if len(calls)==1 else 'evaluated',final_score=0))
            return subprocess.CompletedProcess(command,1 if len(calls)==1 else 0)
        with patch.object(study,'ROOT',root),patch.object(study,'admit_trial'),\
             patch.object(study.subprocess,'run',side_effect=child):
            first=study.batch('pilot');assert len(calls)==2 and first['status']=='terminal'
            assert first['completed'][0]['status']=='infrastructure_error'
            repeated=study.batch('pilot');assert len(calls)==2 and repeated['completed']==first['completed']
            pending=protocol()['pilot_jobs'][2];rules['pilot_jobs'].append(pending)
            write_json(root/'protocol.json',rules);(root/'trials/pilot'/pending['id']).mkdir()
            try:study.batch('pilot')
            except ValueError:pass
            else:raise AssertionError('Partial trial was silently restarted')
            assert len(calls)==2
        write_json(root/'pilot-decision.json',dict(formal_launch_allowed=False,reason='all_luna_functional_fail'))
        with patch.object(study,'ROOT',root),patch.object(study,'batch') as launch:
            study.run();launch.assert_not_called()
    result=dict(passed=True,model_calls=0,physical_runs=0,
        scope='Synthetic child processes; no model design samples',checks=[
            'failed terminal runs retained','controller resume does not rerun completed trials',
            'partial trials stop the batch without replacement','pilot stop prevents formal launch'])
    write_json(Path(__file__).resolve().parents[1]/'checks/serial-batch.json',result)
    return result


if __name__=='__main__':print(json.dumps(check()))

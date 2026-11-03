"""Run the generated proposal validator with the protected backend hidden."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import run_ppa_workflow_study as study
from study_portability import sandbox_command
from study_protocol import BASELINE, preregistration, write_json


def run():
    with tempfile.TemporaryDirectory(prefix='chip-local-ppa-') as temporary:
        root=Path(temporary);private=root/'private';private.mkdir()
        baseline=dict(configuration=BASELINE,rank_eligible=True,candidate_index=0,
                      score=1.,energy_ratio=1.,cell_area_um2=100.)
        write_json(root/'baseline.json',baseline);write_json(root/'protocol.json',preregistration())
        study.prepare(root,{'job':{'id':'W1-local-check','workflow':'W1','repetition':0},
            'baseline':str(root/'baseline.json'),'protocol':str(root/'protocol.json')})
        project=root/'project';workspace=project/'isolated-attempt';workspace.mkdir()
        for name in ('context','tools'):shutil.copytree(project/name,workspace/name)
        candidate=workspace/'proposal/candidate.json'
        valid=dict(BASELINE,abc_area=1,repair_margin=20)
        probe=('import subprocess,sys; from pathlib import Path; '
               f'assert not Path({str(study.CASE)!r}).exists(); '
               'p=subprocess.run([sys.executable,"tools/run_ppa.py","validate"],capture_output=True,text=True); '
               'print(p.stdout); print(p.stderr,file=sys.stderr); sys.exit(p.returncode)')
        def check(document,passed):
            write_json(candidate,document)
            command=sandbox_command(project,workspace,private,[sys.executable,'-c',probe])
            result=subprocess.run(command,capture_output=True,text=True,timeout=30)
            assert (result.returncode==0)==passed,result.stdout+result.stderr
            assert ('PPA_CANDIDATE_VALID' in result.stdout)==passed
        with patch.dict(os.environ,{'CHIP_STUDY_PYTHON':sys.executable,
                                    'CHIP_STUDY_CASE':str(study.CASE),
                                    'CHIP_PPA_SESSION':str(root)}):
            check({'configuration':valid,'rationale':'fixture'},True)
            check({'configuration':dict(valid,utilization=99),'rationale':'fixture'},False)
            check({'configuration':BASELINE,'rationale':'already tried'},False)
            check({'configuration':valid,'rationale':'fixture','unexpected':True},False)
            check({'configuration':valid,'rationale':'x'*65536},False)
            write_json(workspace/'.nebula_inputs/feedback/evidence/artifact.json',{
                'type':'ppa.evaluation.report','payload':{'history':[baseline,{'configuration':valid}]}})
            check({'configuration':valid,'rationale':'captured prior candidate'},False)
    print(json.dumps({'passed':True,'checks':6,'protected_backend_hidden':True,
        'captured_history_duplicate_rejected':True,'model_calls':0,'physical_calls':0}))


if __name__=='__main__':run()

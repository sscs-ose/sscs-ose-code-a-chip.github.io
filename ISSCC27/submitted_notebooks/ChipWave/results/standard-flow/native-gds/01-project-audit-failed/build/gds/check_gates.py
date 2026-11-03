from dataclasses import asdict
import json
from pathlib import Path
import subprocess
from chip_nebula.gates import ReportVerdictGate
from chip_nebula.models.task_manifest import ExitCriterion

root=Path(__file__).resolve().parents[2]
out=root/'build/gds'
command=['/tmp/chipnebula-public-repro-user37/bin/python','-m','chip_nebula.taskgraph.result_summary','build/gds/result_summary.json',
         '--profile','gds','--required','gds.bytes','--required','gds.readable','--required','gds.top_cell',
         '--measured','gds.bytes','--measured','gds.top_cell','--measured','gds.readable']
with (out/'summary_gate.log').open('w') as log:
    rc=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT).returncode
criterion=ExitCriterion(type='report_verdict',source='build/gds/project_acceptance.json',error_class='project_acceptance_failed',on_failure='retry')
verdict=asdict(ReportVerdictGate().check(criterion,root))
result=dict(schema_version=1,passed=rc==0 and verdict['passed'],gates=[
    dict(name='gds-result-summary',passed=rc==0,exit_code=rc,command=command,evidence='build/gds/summary_gate.log'),
    dict(name='project-acceptance-verdict',report=verdict)])
(out/'exit_gates.json').write_text(json.dumps(result,indent=2)+'\n')
assert rc==0,'GDS result-summary Gate failed'
assert verdict['passed'] is False,'Incomplete mandatory acceptance evidence was incorrectly accepted'
print('GDS_RESULT_SUMMARY_PASS; PROJECT_ACCEPTANCE_BLOCKED_AS_REPORTED')

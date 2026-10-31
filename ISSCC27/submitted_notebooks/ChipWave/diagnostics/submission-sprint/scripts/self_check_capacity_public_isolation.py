"""Publicly distributed reference materials must still be invisible to evaluated agents."""
import json
import subprocess
import tempfile
from pathlib import Path

from capacity_integration_physical import ROOT,CASE
from capacity_protocol import TASKS
from capacity_toolbox import sandbox_command as tool_sandbox
from study_portability import sandbox_command as native_sandbox
from study_protocol import digest,write_json


def check():
    protected=[]
    for task in TASKS:
        for root in (ROOT/'task-packages/formal',CASE/'results/capacity-study/task-packages/formal'):
            for name in ('reference.sv','final_tb.sv'):
                path=root/task/'grader'/name
                assert path.is_file(),path
                protected.append(path)
    with tempfile.TemporaryDirectory(prefix='capacity-public-isolation-') as temporary:
        base=Path(temporary);project=base/'project';workspace=project/'workspace'
        workspace.mkdir(parents=True);private=base/'native-home';private.mkdir()
        canary=base/'another-trial';canary.write_text('Do not expose another session\n')
        paths=[*protected,canary]
        code='''import json, pathlib, sys
results=[]
for name in json.loads(sys.argv[1]):
    try:
        pathlib.Path(name).read_bytes()
    except (OSError, PermissionError):
        results.append(False)
    else:
        results.append(True)
print(json.dumps(results))
assert not any(results), 'Reference material escaped isolation'
'''
        command=['/usr/bin/python3','-c',code,json.dumps(list(map(str,paths)))]
        results={}
        for name,args in (('native',native_sandbox(project,workspace,private,command)),
                          ('tool',tool_sandbox(workspace,command))):
            done=subprocess.run(args,capture_output=True,text=True,timeout=60)
            assert done.returncode==0,(name,done.stderr)
            values=json.loads(done.stdout)
            assert values==[False]*len(paths)
            results[name]=dict(passed=True,denied=len(values))
    report=dict(passed=True,model_calls=0,physical_runs=0,sandboxes=results,
        protected_sources={str(p):digest(p) for p in protected},
        scope='Real native/tool namespaces deny every task reference/final checker in both experiment and public distribution, plus another-trial canary. No model invocation.')
    write_json(ROOT/'checks/public-reference-isolation.json',report)
    return report


if __name__=='__main__':
    result=check();print(json.dumps({k:v for k,v in result.items() if k!='protected_sources'}))

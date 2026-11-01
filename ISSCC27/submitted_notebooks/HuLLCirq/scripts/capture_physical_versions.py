"""Collect actual bundled tool versions inside the selected AppImage."""
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys

output=Path(sys.argv[1])
tools={}
for name,args in [('yosys',['-V']),('openroad',['-version']),('klayout',['-v']),('magic',['--version']),('ciel',['--version'])]:
    executable=shutil.which(name)
    if executable is None:raise RuntimeError('Missing bundled '+name)
    result=subprocess.run([executable,*args],capture_output=True,text=True,timeout=30,shell=False)
    if result.returncode!=0:raise RuntimeError(name+' version query failed: '+result.stderr)
    tools[name]={'executable':executable,'command':[executable,*args],'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
output.write_text(json.dumps({'librelane':importlib.metadata.version('librelane'),'python':sys.version,'tools':tools},indent=2)+'\n',encoding='utf-8')

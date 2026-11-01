"""Query bundled S13 tools; no circuit input or model is executed."""
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys

tools = {}
for name, arguments in (('magic', ['--version']), ('netgen', ['-batch'])):
    executable = shutil.which(name)
    if executable is None:
        raise RuntimeError('Missing bundled ' + name)
    result = subprocess.run([executable, *arguments], capture_output=True, text=True, timeout=30, shell=False)
    if result.returncode != 0 or not (result.stdout + result.stderr).strip():
        raise RuntimeError(name + ' version query failed: ' + result.stderr)
    tools[name] = {'executable': executable, 'command': [executable, *arguments], 'exit_code': result.returncode,
                   'stdout': result.stdout, 'stderr': result.stderr}
Path(sys.argv[1]).write_text(json.dumps({'librelane': importlib.metadata.version('librelane'), 'python': sys.version,
                                       'tools': tools}, indent=2) + '\n', encoding='utf-8')

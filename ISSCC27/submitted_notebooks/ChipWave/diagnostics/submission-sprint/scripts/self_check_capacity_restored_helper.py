"""A restored public command helper must remain executable inside the tool sandbox."""
import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import capacity_toolbox
from capacity_physical_export import restore_file
from study_protocol import digest, write_json

ROOT=Path(__file__).resolve().parents[1]


def check():
    with tempfile.TemporaryDirectory(prefix='capacity-restored-helper-') as temporary:
        restored=Path(temporary)
        source=ROOT/'scripts'
        name='capacity_check_help.py'
        original=source/name
        restore_file(source,restored,dict(stored=name,path='scripts/'+name,
            encoding='raw',bytes=original.stat().st_size,sha256=digest(original)))
        target=restored/'scripts'/name
        assert target.stat().st_mode & 0o111
        work=restored/'project';work.mkdir()
        with patch.object(capacity_toolbox,'__file__',str(restored/'scripts/capacity_toolbox.py')):
            command=capacity_toolbox.sandbox_command(work,['/bin/bash','-c','pwd && capacity-check status'])
            result=subprocess.run(command,text=True,capture_output=True,timeout=20)
        assert result.returncode==2 and 'standalone command' in result.stdout+result.stderr, result
    receipt=dict(passed=True,model_calls=0,physical_runs=0,
        scope='Raw-file archive restoration preserves executable bits; restored helper works in the actual isolated shell')
    write_json(ROOT/'checks/restored-helper.json',receipt)
    return receipt


if __name__=='__main__':print(json.dumps(check()))

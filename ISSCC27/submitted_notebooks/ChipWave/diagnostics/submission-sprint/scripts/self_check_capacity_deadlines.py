"""Expired tool budgets and descendant cleanup without model or physical calls."""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from capacity_backends import Backends
from capacity_process import remaining,run_group
from capacity_integration_physical import ROOT
from study_protocol import write_json
from build_capacity_dot_integration import qualify


def check():
    with tempfile.TemporaryDirectory(prefix='capacity-deadlines-') as temp:
        root=Path(temp);marker=root/'escaped.txt'
        child='import time;from pathlib import Path;time.sleep(1);Path('+repr(str(marker))+').write_text("escaped")'
        parent='import subprocess,sys,time;subprocess.Popen([sys.executable,"-c",'+repr(child)+']);time.sleep(30)'
        started=time.monotonic()
        try:run_group([sys.executable,'-c',parent],capture_output=True,text=True,timeout=.1)
        except subprocess.TimeoutExpired:pass
        else:raise AssertionError('Expired process was not terminated')
        assert time.monotonic()-started<3
        time.sleep(1.1)
        assert not marker.exists(),'Compiler descendant survived its deadline'
        try:remaining(time.monotonic()-1,60)
        except subprocess.TimeoutExpired:pass
        else:raise AssertionError('Expired tool budget accepted')
        source=root/'source';(source/'rtl').mkdir(parents=True)
        (source/'rtl/design.sv').write_text((ROOT/'tasks/A1/grader/reference.sv').read_text())
        backend=Backends(root/'record','A1')
        for index,method in enumerate((backend.synthesis,backend.integration),1):
            result=method(source,index,deadline=time.monotonic()-1)
            assert result['status']=='timeout',result
        compile_root=root/'bad-integration';compile_root.mkdir()
        with patch('capacity_process.run_group',return_value=subprocess.CompletedProcess([],1,'','syntax error')):
            invalid=qualify(compile_root)
        assert not invalid['passed'] and invalid['failure_class']=='candidate_integration_compile'
    report=dict(passed=True,model_calls=0,physical_runs=0,
                checks=['shared active deadline reaches synthesis and integration','compiler descendants terminated',
                        'candidate integration compile failure is not classified as infrastructure'])
    write_json(ROOT/'checks/tool-active-deadlines.json',report)
    return report


if __name__=='__main__':
    print(json.dumps(check()))

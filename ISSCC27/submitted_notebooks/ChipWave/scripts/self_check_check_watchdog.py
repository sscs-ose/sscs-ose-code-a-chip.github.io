"""Kill a check owner during a real zero-time RTL hang and verify child cleanup."""
from pathlib import Path
import os
import signal
import subprocess
import sys
import tempfile
import time

import psutil
from study_checks import DevelopmentChecks

CASE=Path(__file__).resolve().parents[1]


def run():
    with tempfile.TemporaryDirectory(prefix='chip-check-watchdog-') as temporary:
        root=Path(temporary);workspace=root/'workspace';(workspace/'rtl').mkdir(parents=True)
        source=(CASE/'released_design/rtl/npu/nebula_npu_dot4.sv').read_text()
        assert source.count('endmodule')==1
        (workspace/'rtl/hung.sv').write_text(source)
        with DevelopmentChecks(workspace,root/'positive-ledger','positive-control') as checks:
            assert checks.execute()['exit_code']==0
        (workspace/'rtl/hung.sv').write_text(source.replace('endmodule','initial forever begin end\nendmodule'))
        code='import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from study_checks import DevelopmentChecks;DevelopmentChecks(Path(sys.argv[2]),Path(sys.argv[3]),"watchdog-negative-control").execute()'
        with (root/'owner.log').open('w') as log:
            owner=subprocess.Popen([sys.executable,'-c',code,str(CASE/'scripts'),str(workspace),str(root/'ledger')],
                stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            children=[];deadline=time.monotonic()+15
            while time.monotonic()<deadline and owner.poll() is None:
                children=[child for child in psutil.Process(owner.pid).children(recursive=True) if child.name()=='vvp']
                if children:break
                time.sleep(.05)
            if not children:
                owner.kill();owner.wait()
                raise AssertionError('Real hung simulation did not start: '+(root/'owner.log').read_text())
            child=children[0]
            owner.kill();owner.wait()
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                try:alive=child.is_running() and child.status()!=psutil.STATUS_ZOMBIE
                except psutil.NoSuchProcess:alive=False
                if not alive:break
                time.sleep(.05)
            if alive:
                os.killpg(os.getpgid(child.pid),signal.SIGKILL)
                raise AssertionError('Parent cancellation left the trusted check simulator running; negative-control child cleaned up')
    print('CHECK_WATCHDOG_PASS: real hung VVP dies after owner SIGKILL; no model or full physical calls')


if __name__=='__main__':run()

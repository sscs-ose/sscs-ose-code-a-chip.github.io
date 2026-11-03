"""Reproduce the real namespace/session escape, then test a 75-second tree pause."""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from capacity_process import stop_tree,resume_tree

ROOT=Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT/'scripts'))
from study_portability import sandbox_command
from study_protocol import write_json

HEARTBEAT='''import os,sys,time,subprocess
from pathlib import Path
if len(sys.argv)==1:
 subprocess.Popen([sys.executable,__file__,'child'],start_new_session=True)
name='child' if len(sys.argv)>1 else 'issuer'
with Path(name+'.ticks').open('a',buffering=1) as out:
 while True:
  out.write(str(time.monotonic())+'\\n');time.sleep(.03)
'''


def counts(work):
    return {name:len((work/(name+'.ticks')).read_bytes())
            for name in ('issuer','child')}


def check():
    rows=[]
    with tempfile.TemporaryDirectory(prefix='capacity-pause-tree-') as temporary:
        base=Path(temporary)
        for fixed in (False,True):
            project=base/str(fixed)/'project';work=project/'workspace'
            work.mkdir(parents=True);private=base/str(fixed)/'private';private.mkdir()
            (work/'heartbeat.py').write_text(HEARTBEAT)
            command=sandbox_command(project,work,private,['/usr/bin/python3','heartbeat.py'])
            stopped={};fd_before=len(list(Path('/proc/self/fd').iterdir()))
            with (work/'process.log').open('w') as log:
                process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                try:
                    end=time.monotonic()+15
                    while not all((work/(n+'.ticks')).exists() for n in ('issuer','child')):
                        if process.poll() is not None:raise AssertionError((work/'process.log').read_text())
                        if time.monotonic()>end:raise TimeoutError('Fixture did not start')
                        time.sleep(.05)
                    if fixed:stopped=stop_tree(process.pid)
                    else:os.killpg(process.pid,signal.SIGSTOP)
                    time.sleep(.15);before=counts(work)
                    duration=75 if fixed else 1
                    for _ in range(duration):
                        time.sleep(1)
                        if fixed:assert counts(work)==before,'A stopped namespace descendant advanced'
                    after=counts(work)
                    if not fixed:assert all(after[n]>before[n] for n in before),'Original escape not reproduced'
                    frozen_pids=list(stopped)
                    if fixed:resume_tree(stopped)
                    else:os.killpg(process.pid,signal.SIGCONT)
                    time.sleep(.3);resumed=counts(work)
                    assert all(resumed[n]>after[n] for n in after)
                    rows.append(dict(revision='proposed tree pause' if fixed else 'original process-group pause',
                        before=before,after=after,resumed=resumed,paused_seconds=duration,stopped_pids=frozen_pids))
                finally:
                    resume_tree(stopped)
                    if process.poll() is None:
                        os.kill(process.pid,signal.SIGKILL);process.wait(timeout=10)
            assert len(list(Path('/proc/self/fd').iterdir()))==fd_before,'PID descriptor leaked'
    result=dict(passed=True,model_calls=0,physical_runs=0,rows=rows,
                scope='Real bubblewrap and nested setsid processes; sustained synthetic request-issuer/child heartbeats. Native and full campaign checks are separate prerequisites.')
    write_json(ROOT/'checks/pause-tree.json',result)
    return result


if __name__=='__main__':print(json.dumps(check()))

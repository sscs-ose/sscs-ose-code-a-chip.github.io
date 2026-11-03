"""Exercise pause rollback and termination using the actual sandbox, without models."""
import json, os, signal, subprocess, tempfile, time
from pathlib import Path
from unittest.mock import patch
import capacity_process as cp
from check_pause_tree import ROOT, HEARTBEAT, counts, sandbox_command, write_json


def check():
    with tempfile.TemporaryDirectory(prefix='capacity-pause-edges-') as temporary:
        base=Path(temporary);project=base/'project';work=project/'workspace';work.mkdir(parents=True)
        private=base/'private';private.mkdir();(work/'heartbeat.py').write_text(HEARTBEAT)
        command=sandbox_command(project,work,private,['/usr/bin/python3','heartbeat.py'])
        fd_before=len(list(Path('/proc/self/fd').iterdir()))
        process=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        held={}
        try:
            deadline=time.monotonic()+15
            while not all((work/(n+'.ticks')).exists() for n in ('issuer','child')):
                assert process.poll() is None
                if time.monotonic()>deadline:raise TimeoutError('Fixture startup')
                time.sleep(.03)
            real=cp._processes;calls=0
            def fail_second_scan():
                nonlocal calls
                calls+=1
                if calls==2:raise OSError('injected process scan failure')
                return real()
            try:
                with patch.object(cp,'_processes',side_effect=fail_second_scan):cp.stop_tree(process.pid)
            except OSError as error:assert 'injected' in str(error)
            else:raise AssertionError('Pause failure swallowed')
            before=counts(work);time.sleep(.3);after=counts(work)
            assert all(after[n]>before[n] for n in before),'Partial pause did not roll back'
            assert len(list(Path('/proc/self/fd').iterdir()))==fd_before,'Rollback leaked descriptors'
            held=cp.stop_tree(process.pid);pids=list(held)
            # Mirrors the existing budget observer: stopped wrapper needs the kill fallback.
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=.2)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
            cp.resume_tree(held)
            deadline=time.monotonic()+5
            while any(cp._processes().get(p,{}).get('state') not in (None,'Z') for p in pids):
                if time.monotonic()>deadline:raise AssertionError('Native descendant survived launcher termination')
                time.sleep(.05)
            assert len(list(Path('/proc/self/fd').iterdir()))==fd_before,'Termination leaked descriptors'
            try:cp.stop_tree(process.pid)
            except ProcessLookupError:pass
            else:raise AssertionError('Exited launcher accepted')
        finally:
            cp.resume_tree(held)
            if process.poll() is None:
                os.kill(process.pid,signal.SIGKILL);process.wait(timeout=5)
    result=dict(passed=True,model_calls=0,physical_runs=0,
        checks=['partial_pause_failure_resumes_descendants','no_descriptor_leak',
                'termination_while_paused_removes_native_namespace','exited_launcher_rejected'],
        scope='Actual sandbox process-control edges, not full repaired campaign qualification')
    write_json(ROOT/'checks/pause-edges.json',result)
    return result

if __name__=='__main__':print(json.dumps(check()))

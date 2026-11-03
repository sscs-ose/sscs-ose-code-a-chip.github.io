"""Bound tool waiting and terminate compiler descendants with their launcher."""
import os
import signal
import subprocess
import time
from contextlib import suppress
from pathlib import Path


def _processes():
    rows={}
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:
            text=(entry/'stat').read_text();fields=text[text.rindex(')')+2:].split()
            rows[int(entry.name)]=dict(parent=int(fields[1]),state=fields[0],start=fields[19])
        except (FileNotFoundError,ProcessLookupError):pass
    return rows


def resume_tree(stopped):
    for pid,(fd,start) in reversed(list(stopped.items())):
        try:
            with suppress(ProcessLookupError):signal.pidfd_send_signal(fd,signal.SIGCONT)
        finally:os.close(fd)
    stopped.clear()


def stop_tree(pid):
    """Freeze the native PID-namespace tree, including descendants that called setsid."""
    if os.getpgid(pid)!=pid:raise ValueError('Expected a dedicated invocation launcher')
    stopped={};deadline=time.monotonic()+10
    try:
        while True:
            rows=_processes()
            if pid not in rows:raise ProcessLookupError(pid)
            owned={pid}
            while True:
                expanded=owned|{p for p,r in rows.items() if r['parent'] in owned}
                if expanded==owned:break
                owned=expanded
            pending=[p for p in owned if rows[p]['state'] not in ('T','t','Z')]
            for p in [pid,*sorted(owned-{pid})]:
                row=rows[p]
                if row['state']=='Z':continue
                if p in stopped and stopped[p][1]!=row['start']:
                    raise ValueError('Native process identity changed during pause')
                if p not in stopped:
                    try:fd=os.pidfd_open(p)
                    except ProcessLookupError:continue
                    try:
                        text=Path(f'/proc/{p}/stat').read_text();fields=text[text.rindex(')')+2:].split()
                        if fields[19]!=row['start']:raise ValueError('PID changed before pause admission')
                    except (FileNotFoundError,ProcessLookupError):
                        os.close(fd)
                        continue
                    except BaseException:
                        os.close(fd)
                        raise
                    stopped[p]=(fd,row['start'])
                with suppress(ProcessLookupError):signal.pidfd_send_signal(stopped[p][0],signal.SIGSTOP)
            # A second scan catches children forked before their parent stopped.
            if not pending:return stopped
            if time.monotonic()>=deadline:raise TimeoutError('Native process tree did not quiesce')
            time.sleep(.02)
    except BaseException:
        resume_tree(stopped)
        raise


def remaining(deadline, maximum):
    value=maximum if deadline is None else min(maximum,deadline-time.monotonic())
    if value<=0:raise subprocess.TimeoutExpired('shared active-time budget',0)
    return value


def run_group(command, *, timeout, **kwargs):
    if kwargs.pop('capture_output',False):
        kwargs.update(stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    with subprocess.Popen(command,start_new_session=True,**kwargs) as process:
        try:
            stdout,stderr=process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            with suppress(ProcessLookupError):
                os.killpg(process.pid,signal.SIGTERM)
            try:stdout,stderr=process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                with suppress(ProcessLookupError):
                    os.killpg(process.pid,signal.SIGKILL)
                stdout,stderr=process.communicate()
            raise subprocess.TimeoutExpired(command,timeout,output=stdout,stderr=stderr)
        except BaseException:
            if process.poll() is None:
                with suppress(ProcessLookupError):
                    os.killpg(process.pid,signal.SIGKILL)
                process.communicate()
            raise
        return subprocess.CompletedProcess(command,process.returncode,stdout,stderr)

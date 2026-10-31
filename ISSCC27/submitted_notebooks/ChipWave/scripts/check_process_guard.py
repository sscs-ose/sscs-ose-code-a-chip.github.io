"""Keep trusted compiler/simulator children inside an owner-bound process group."""
import argparse
import ctypes
import os
import signal
import subprocess


def run(owner,command):
    if os.getpgrp()!=os.getpid() or not command:
        raise ValueError('The check guard requires its own process group and a command')
    def stop(*_):
        os.killpg(os.getpid(),signal.SIGKILL)
    signal.signal(signal.SIGTERM,stop)
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(1,signal.SIGTERM,0,0,0)!=0:
        raise OSError(ctypes.get_errno(),'Unable to bind trusted check lifetime to its owner')
    if os.getppid()!=owner:stop()
    result=subprocess.Popen(command).wait()
    return result if result>=0 else 128-result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--owner',type=int,required=True)
    parser.add_argument('command',nargs=argparse.REMAINDER);args=parser.parse_args()
    command=args.command[1:] if args.command[:1]==['--'] else args.command
    raise SystemExit(run(args.owner,command))

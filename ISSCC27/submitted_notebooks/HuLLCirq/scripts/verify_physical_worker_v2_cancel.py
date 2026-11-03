"""Harmless Linux cancellation QA; fake AppImage, no EDA/model/live project.

Run in WSL with --output pointing to a fresh retained .work directory. Both
cases intentionally leave a TERM-ignoring child after its leader exits.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

SOURCE = Path(__file__).resolve().with_name("physical_worker_v2.py")
SPEC = importlib.util.spec_from_file_location("physical_worker_v2_QA", SOURCE)
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)

FAKE_IMAGE = '''#!/usr/bin/python3
import json,os,signal,subprocess,sys,time
from pathlib import Path
root=Path(sys.argv[2])
code="""import json,os,signal,sys,time
from pathlib import Path
signal.signal(signal.SIGTERM,signal.SIG_IGN)
Path(sys.argv[1]).write_text(json.dumps({'pid':os.getpid(),'cwd':os.getcwd()}))
while True:time.sleep(.1)
"""
child=subprocess.Popen([sys.executable,'-c',code,str(root/'child-ready.json')])
deadline=time.monotonic()+5
while not (root/'child-ready.json').exists():
    if time.monotonic()>deadline:raise RuntimeError('child readiness timeout')
    time.sleep(.02)
(root/'leader-ready.json').write_text(json.dumps({'pid':os.getpid(),'child_pid':child.pid,'cwd':os.getcwd()}))
while True:time.sleep(.1)
'''


def wait_for(predicate, seconds=10):
    deadline = time.monotonic() + seconds
    while not predicate():
        if time.monotonic() >= deadline:
            raise RuntimeError("Harmless process readiness deadline expired.")
        time.sleep(.05)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run_case(folder, recovery):
    folder.mkdir()
    cwd = folder / "actual-cwd"
    cwd.mkdir()
    snapshot = folder / "worker.py"
    shutil.copyfile(SOURCE, snapshot)
    image = folder / "librelane-devshell-x86_64.AppImage"
    image.write_text(FAKE_IMAGE, encoding="utf-8")
    image.chmod(0o700)
    worker_sha = worker.digest(snapshot.read_bytes())
    request = {"version": worker.VERSION, "argv": [str(image), "python3", str(folder)],
               "cwd": str(cwd), "timeout_seconds": 60, "worker_sha256": worker_sha}
    request_path = folder / "request.json"
    request_path.write_bytes(worker.canonical(request) + b"\n")
    request_sha = worker.digest(request_path.read_bytes())
    argv = [sys.executable, str(snapshot), str(request_path), "--request-sha256", request_sha,
            "--worker-sha256", worker_sha]
    process = None
    success = False
    try:
        with (folder / "supervisor-stdout.log").open("xb") as out, (folder / "supervisor-stderr.log").open("xb") as err:
            process = subprocess.Popen(argv, stdout=out, stderr=err, start_new_session=True, shell=False)
            wait_for(lambda: (folder / "leader-ready.json").exists() and (folder / "process-group.json").exists())
            ready = read(folder / "leader-ready.json")
            wait_for(lambda: any(member["pid"] == ready["child_pid"] for member in read(folder / "process-group.json")["members"]))
            assert ready["cwd"] == str(cwd)
            assert read(folder / "child-ready.json")["cwd"] == str(cwd)
            start = read(folder / "process-start.json")
            assert start["request_sha256"] == request_sha and start["worker_sha256"] == worker_sha
            assert start["cwd"] == str(cwd) and start["observed_child_cwd"] == str(cwd)
            if recovery:
                process.kill()  # Simulate an unresponsive/dead supervisor only.
                process.wait(timeout=2)
                os.killpg(start["process_group"], signal.SIGTERM)
                wait_for(lambda: (worker.read_process(start["process_group"]) or {"state": "Z"})["state"] == "Z")
                with (folder / "cleanup-stdout.log").open("xb") as cleanup_out, (folder / "cleanup-stderr.log").open("xb") as cleanup_err:
                    cleanup = subprocess.run([*argv, "--cleanup"], stdout=cleanup_out, stderr=cleanup_err, timeout=15, shell=False)
                result = read(folder / "cleanup-result.json")
                assert cleanup.returncode == 0 and result["status"] == "Cancelled"
            else:
                (folder / "cancel.request").write_bytes(b"explicit harmless software QA cancel\n")
                process.wait(timeout=15)
                result = read(folder / "process-result.json")
                assert process.returncode == 0 and result["status"] == "Cancelled"
                assert result["request_unchanged_at_completion"] and result["worker_unchanged_at_completion"]
            assert result["whole_process_group_terminated_on_cancel"] is True
            assert result["termination"]["verified_terminated"] is True
            assert result["termination"]["signals"] == ["SIGTERM", "SIGKILL"]
            assert worker.live_group_members(start["process_group"]) == []
            assert worker.digest(snapshot.read_bytes()) == worker_sha
            assert worker.digest(request_path.read_bytes()) == request_sha
            success = True
            return {"case": "independent_cleanup_after_supervisor_and_leader_exit" if recovery else "cancel_leader_exit_TERM_ignoring_child",
                    "status": "Passed", "worker_sha256": worker_sha, "request_sha256": request_sha,
                    "process_group": start["process_group"], "leader_starttime": start["leader_starttime"],
                    "termination": result["termination"], "actual_cwd": str(cwd),
                    "model_calls": 0, "EDA_calls": 0, "evidence_kind": "harmless_process_supervision_software_QA"}
    finally:
        if not success:
            (folder / "cancel.request").write_bytes(b"cleanup after failed harmless QA\n")
            if process is not None and process.poll() is None:
                try: process.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=2)
            if (folder / "process-start.json").exists():
                with (folder / "fallback-cleanup-stdout.log").open("wb") as out, (folder / "fallback-cleanup-stderr.log").open("wb") as err:
                    subprocess.run([*argv, "--cleanup"], stdout=out, stderr=err, timeout=15, shell=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("This harmless integration check requires Linux /proc (WSL is supported).")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    summary = {"version": "hullcirq-worker-v2-cancellation-QA-v1", "status": "Failed", "cases": [],
               "evidence_kind": "harmless_process_supervision_software_QA", "model_calls": 0, "EDA_calls": 0}
    try:
        summary["cases"].append(run_case(output / "cancel", recovery=False))
        summary["cases"].append(run_case(output / "recovery", recovery=True))
        summary["status"] = "Passed"
        return 0
    except Exception as error:
        summary["error"] = str(error)
        raise
    finally:
        (output / "summary.json").write_bytes(worker.canonical(summary) + b"\n")
        print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())

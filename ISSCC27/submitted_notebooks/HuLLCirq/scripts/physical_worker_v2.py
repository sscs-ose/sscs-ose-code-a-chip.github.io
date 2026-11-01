"""Fixed Linux process-group supervisor; v1 stays immutable as prior provenance.

The adapter freezes this file and request bytes before execution. This module
never interprets model output or invokes a shell. Cleanup is independently
bounded and refuses an ambiguous/reused process identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import time

VERSION = "hullcirq-physical-worker-v2"
TERM_SECONDS = 5.0
KILL_SECONDS = 5.0
POLL_SECONDS = 0.1
# Fixed Linux signal numbers also let Windows run the isolated fake-/proc QA.
TERM_SIGNAL = 15
KILL_SIGNAL = 9


class WorkerError(RuntimeError):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def load_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise WorkerError("Duplicate JSON key: " + key)
            result[key] = value
        return result

    def invalid(value):
        raise WorkerError("Nonfinite JSON number: " + value)

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def atomic_json(path, value):
    pending = path.with_name(path.name + ".pending")
    pending.write_bytes(canonical(value) + b"\n")
    os.replace(pending, path)


def read_process(pid, proc_root=Path("/proc")):
    """Read Linux identity correctly even when comm contains spaces/parentheses."""
    try:
        # Linux comm is arbitrary bytes. It is discarded before numeric parsing.
        raw = (proc_root / str(pid) / "stat").read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None
    except OSError as error:
        raise WorkerError("Cannot inspect Linux process identity: " + str(error)) from error
    try:
        number, rest = raw.split(" (", 1)
        fields = rest.rsplit(")", 1)[1].split()
        if int(number) != pid or len(fields) < 20:
            raise ValueError("Truncated/mismatched process stat")
        return {"pid": pid, "state": fields[0], "ppid": int(fields[1]),
                "process_group": int(fields[2]), "session": int(fields[3]),
                "starttime": int(fields[19])}
    except (ValueError, IndexError) as error:
        raise WorkerError("Invalid Linux process identity: " + str(pid)) from error


def live_group_members(pgid, proc_root=Path("/proc")):
    try:
        entries = list(proc_root.iterdir())
    except OSError as error:
        raise WorkerError("Cannot enumerate Linux process groups: " + str(error)) from error
    members = []
    for entry in entries:
        if not entry.name.isascii() or not entry.name.isdecimal():
            continue
        process = read_process(int(entry.name), proc_root)
        if process is not None and process["process_group"] == pgid and process["state"] not in ("Z", "X", "x"):
            members.append(process)
    return sorted(members, key=lambda item: item["pid"])


def signal_group(pgid, sig):
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        pass  # The subsequent /proc scan establishes whether it actually ended.
    except OSError as error:
        raise WorkerError("Cannot signal Linux process group: " + str(error)) from error


def terminate_group(pgid, *, proc_root=Path("/proc"), clock=time.monotonic,
                    sleeper=time.sleep, sender=signal_group):
    """Never equate leader exit or killpg success with group termination."""
    proof = {"process_group": pgid, "signals": [], "before": [], "after": [],
             "verified_terminated": False, "inspection_error": None}
    try:
        proof["before"] = live_group_members(pgid, proc_root)
        members = proof["before"]
        for sig, name, duration in ((TERM_SIGNAL, "SIGTERM", TERM_SECONDS), (KILL_SIGNAL, "SIGKILL", KILL_SECONDS)):
            if not members:
                break
            sender(pgid, sig)
            proof["signals"].append(name)
            deadline = clock() + duration
            while True:
                members = live_group_members(pgid, proc_root)
                if not members or clock() >= deadline:
                    break
                sleeper(min(POLL_SECONDS, max(0.0, deadline - clock())))
        proof["after"] = members
        proof["verified_terminated"] = not members
    except (WorkerError, OSError) as error:
        proof["inspection_error"] = str(error)
    return proof


def frozen_request(request_path, expected_request_sha256, expected_worker_sha256, worker_source_path):
    for value in (expected_request_sha256, expected_worker_sha256):
        if type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise WorkerError("Require explicit frozen request and worker SHA256 identities.")
    request_raw = request_path.read_bytes()
    worker_raw = worker_source_path.read_bytes()
    if digest(request_raw) != expected_request_sha256 or digest(worker_raw) != expected_worker_sha256:
        raise WorkerError("Frozen request/worker bytes do not match their launch identities.")
    request = load_json(request_raw)
    if type(request) is not dict or set(request) != {"version", "argv", "cwd", "timeout_seconds", "worker_sha256"}:
        raise WorkerError("Require the exact fixed v2 request schema.")
    argv = request["argv"]
    if (request["version"] != VERSION or request["worker_sha256"] != expected_worker_sha256
            or type(argv) is not list or len(argv) < 2
            or any(type(value) is not str or any(ord(c) < 32 for c in value) for value in argv)
            or not argv[0].startswith("/") or PurePosixPath(argv[0]).name != "librelane-devshell-x86_64.AppImage"
            or argv[1] not in ("librelane", "python3")):
        raise WorkerError("Only the fixed AppImage invocation is supported.")
    cwd, timeout = request["cwd"], request["timeout_seconds"]
    if (type(cwd) is not str or not cwd.startswith("/") or any(ord(c) < 32 for c in cwd)
            or ".." in PurePosixPath(cwd).parts
            or type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 7200):
        raise WorkerError("Require an absolute execution cwd and a finite bounded timeout.")
    return request


def boot_identity(proc_root):
    try:
        value = (proc_root / "sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
    except OSError as error:
        raise WorkerError("Cannot establish Linux boot identity.") from error
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", value):
        raise WorkerError("Invalid Linux boot identity.")
    return value


def identity_fields(request, request_sha256, worker_sha256):
    return {"version": VERSION, "argv": request["argv"], "cwd": request["cwd"],
            "request_sha256": request_sha256, "worker_sha256": worker_sha256}


def cleanup_saved_group(root, binding, *, proc_root=Path("/proc"), clock=time.monotonic,
                        sleeper=time.sleep, sender=signal_group):
    """A separate host recovery invocation must prove identity before signalling."""
    proof = {**binding, "status": "Failed", "executed": False,
             "whole_process_group_terminated_on_cancel": False, "diagnostics": []}
    try:
        start_raw = (root / "process-start.json").read_bytes()
        start = load_json(start_raw)
        if any(canonical(start.get(key)) != canonical(value) for key, value in binding.items()):
            raise WorkerError("Process-start request/source identity differs from the frozen launch.")
        pgid, birth = start["process_group"], start["leader_starttime"]
        if type(pgid) is not int or pgid <= 1 or type(birth) is not int or birth <= 0:
            raise WorkerError("Invalid process-group birth identity.")
        if start["boot_id"] != boot_identity(proc_root):
            raise WorkerError("Linux restarted; the recorded process-group identity is stale.")
        members = live_group_members(pgid, proc_root)
        leader = read_process(pgid, proc_root)
        if leader is not None and (leader["starttime"] != birth or leader["process_group"] != pgid or leader["session"] != pgid):
            raise WorkerError("The recorded group leader PID was reused or changed identity.")
        if any(member["session"] != pgid or member["starttime"] < birth for member in members):
            raise WorkerError("A live group member has an incompatible session/birth identity.")
        if leader is None and members:
            checkpoint = load_json((root / "process-group.json").read_bytes())
            if checkpoint["process_start_sha256"] != digest(start_raw):
                raise WorkerError("The membership checkpoint belongs to another process start.")
            def member_identity(member):
                values = [member["pid"], member["starttime"], member["session"]]
                if any(type(value) is not int or value <= 0 for value in values):
                    raise WorkerError("A membership checkpoint has an invalid typed identity.")
                return canonical(values)
            observed = {member_identity(member) for member in checkpoint["members"]}
            if not any(member_identity(member) in observed for member in members):
                raise WorkerError("Leader exited and no previously observed live member anchors this group.")
        proof["process_start_sha256"] = digest(start_raw)
        proof["process_group"] = pgid
        proof["termination"] = terminate_group(pgid, proc_root=proc_root, clock=clock, sleeper=sleeper, sender=sender)
        proof["executed"] = True
        proof["whole_process_group_terminated_on_cancel"] = proof["termination"]["verified_terminated"]
        proof["status"] = "Cancelled" if proof["whole_process_group_terminated_on_cancel"] else "Failed"
    except (WorkerError, OSError, ValueError, KeyError, TypeError) as error:
        proof["diagnostics"].append(str(error))
    atomic_json(root / "cleanup-result.json", proof)
    return proof


def run_request(request_path, expected_request_sha256, expected_worker_sha256, *,
                worker_source_path=None, proc_root=Path("/proc"), clock=time.monotonic,
                sleeper=time.sleep, popen_factory=subprocess.Popen, sender=signal_group):
    request_path = Path(request_path).resolve()
    worker_source_path = Path(worker_source_path or __file__).resolve()
    request = frozen_request(request_path, expected_request_sha256, expected_worker_sha256, worker_source_path)
    root = request_path.parent
    if any((root / name).exists() for name in ("process-start.json", "process-result.json", "stdout.log", "stderr.log")):
        raise WorkerError("A worker launch requires a fresh directory; prior evidence is immutable.")
    binding = identity_fields(request, expected_request_sha256, expected_worker_sha256)
    result = {**binding, "status": "Failed", "executed": False, "exit_code": None,
              "process_group": None, "leader_starttime": None, "elapsed_seconds": 0.0,
              "whole_process_group_terminated_on_cancel": False, "whole_process_group_terminated": False, "termination": None,
              "supervisor_cwd": os.getcwd(), "observed_child_cwd": None, "diagnostics": []}
    started = clock()
    process = None
    try:
        boot_id = boot_identity(proc_root)
        with (root / "stdout.log").open("xb") as stdout, (root / "stderr.log").open("xb") as stderr:
            process = popen_factory(request["argv"], cwd=request["cwd"], stdout=stdout, stderr=stderr,
                                    start_new_session=True, shell=False)
            result["executed"], result["process_group"] = True, process.pid
            leader = read_process(process.pid, proc_root)
            if leader is None or leader["process_group"] != process.pid or leader["session"] != process.pid:
                raise WorkerError("Could not verify the newly isolated Linux process group.")
            result["leader_starttime"] = leader["starttime"]
            try:
                result["observed_child_cwd"] = os.readlink(proc_root / str(process.pid) / "cwd")
            except OSError:
                pass  # Popen's exact cwd remains recorded even for a fast exit.
            if result["observed_child_cwd"] not in (None, request["cwd"]):
                raise WorkerError("Actual child cwd differs from the frozen execution cwd.")
            start = {**binding, "process_group": process.pid, "leader_starttime": leader["starttime"],
                     "boot_id": boot_id, "observed_child_cwd": result["observed_child_cwd"]}
            atomic_json(root / "process-start.json", start)
            start_hash = digest((root / "process-start.json").read_bytes())
            result["process_start_sha256"] = start_hash
            previous_members = None
            while True:
                members = live_group_members(process.pid, proc_root)
                if members != previous_members:
                    atomic_json(root / "process-group.json", {"version": VERSION, "process_start_sha256": start_hash, "members": members})
                    previous_members = members
                cancelled = (root / "cancel.request").exists()
                timed_out = clock() - started >= request["timeout_seconds"]
                if cancelled or timed_out:
                    result["status"] = "Cancelled" if cancelled else "Timeout"
                    result["termination"] = terminate_group(process.pid, proc_root=proc_root, clock=clock, sleeper=sleeper, sender=sender)
                    result["whole_process_group_terminated_on_cancel"] = result["termination"]["verified_terminated"]
                    result["whole_process_group_terminated"] = result["termination"]["verified_terminated"]
                    if not result["whole_process_group_terminated_on_cancel"]:
                        result["status"] = "Failed"
                        result["diagnostics"].append("Process-group termination could not be verified.")
                    break
                if process.poll() is not None:
                    # poll may reap a leader that was live at the earlier scan.
                    # Only a fresh scan can establish remaining descendants.
                    if live_group_members(process.pid, proc_root):
                        result["termination"] = terminate_group(process.pid, proc_root=proc_root, clock=clock, sleeper=sleeper, sender=sender)
                        result["whole_process_group_terminated"] = result["termination"]["verified_terminated"]
                        result["diagnostics"].append("Leader exited with live process-group descendants; cleaned up instead of accepting completion.")
                    else:
                        result["status"] = "Completed"
                        result["whole_process_group_terminated"] = True
                    break
                sleeper(POLL_SECONDS)
            try:
                process.wait(timeout=POLL_SECONDS)
            except subprocess.TimeoutExpired:
                result["status"] = "Failed"
                result["diagnostics"].append("The group leader did not become waitable after bounded cleanup.")
            result["exit_code"] = process.returncode
    except (WorkerError, OSError, ValueError, KeyError, TypeError) as error:
        result["status"] = "Failed"
        result["diagnostics"].append(str(error))
        if process is not None:
            result["termination"] = terminate_group(process.pid, proc_root=proc_root, clock=clock, sleeper=sleeper, sender=sender)
            result["whole_process_group_terminated"] = result["termination"]["verified_terminated"]
            try:
                process.wait(timeout=POLL_SECONDS)
            except subprocess.TimeoutExpired:
                pass
            result["exit_code"] = process.returncode
    result["elapsed_seconds"] = clock() - started
    for name, path, expected in (("request", request_path, expected_request_sha256), ("worker", worker_source_path, expected_worker_sha256)):
        try:
            unchanged = digest(path.read_bytes()) == expected
        except OSError:
            unchanged = False
        result[name + "_unchanged_at_completion"] = unchanged
        if not unchanged:
            result["status"] = "Failed"
            result["diagnostics"].append("Frozen " + name + " bytes changed or disappeared during execution.")
    atomic_json(root / "process-result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("--request-sha256", required=True)
    parser.add_argument("--worker-sha256", required=True)
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    request_path, source_path = args.request.resolve(), Path(__file__).resolve()
    try:
        if args.cleanup:
            request = frozen_request(request_path, args.request_sha256, args.worker_sha256, source_path)
            result = cleanup_saved_group(request_path.parent, identity_fields(request, args.request_sha256, args.worker_sha256))
            return 0 if result["whole_process_group_terminated_on_cancel"] else 1
        run_request(request_path, args.request_sha256, args.worker_sha256, worker_source_path=source_path)
        return 0  # The retained actual tool/group result determines acceptance.
    except (WorkerError, OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, "physical worker rejected launch: " + str(error) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())

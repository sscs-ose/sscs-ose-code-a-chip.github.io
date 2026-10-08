"""Independent local Job Object supervisor. All execution work is inside its owned job."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time

from clockguard import clock_sample, clock_state
from winjob import OwnedJob, OwnedProcess, current_identity


def save(path: Path, value: object):
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def supervise(arguments: list[str], cwd: Path, output: Path, seconds: float, *,
              extra_env: dict | None = None, crash_after_seconds: float | None = None) -> dict:
    if output.exists():
        raise RuntimeError("A supervisor window path is single-use; it cannot be restarted")
    if not 0 < seconds <= 1800:
        raise RuntimeError("Invalid local whole-window limit")
    output.mkdir(parents=True)
    job = OwnedJob()
    worker = None
    stop = threading.Event()
    expired = threading.Event()
    monitor_fault = []
    monitor_samples = []
    decisions = []
    start = clock_sample()
    context = {
        "schema": 1, "supervisor": current_identity(), "start": start, "limit_seconds": seconds,
        "job_object_kill_on_close": True, "worker_assigned_while_suspended": True,
        "scope": "only this worker and its inherited descendants", "new_window_not_a_budget_reset": True,
    }

    def monitor():
        try:
            while not stop.is_set():
                sample = clock_sample()
                state = clock_state(start, sample, seconds)
                monitor_samples.append({"clock": sample, "state": state})
                if not state["allowed"]:
                    decisions.append({"clock": sample, "reason": state["reason"]})
                    expired.set()
                    job.terminate(124)
                    return
                stop.wait(0.025)
        except BaseException as error:
            monitor_fault.append({"type": type(error).__name__, "error": str(error)})
            expired.set()
            try:
                job.terminate(125)
            except OSError as termination_error:
                monitor_fault.append({"type": "owned_job_termination_error",
                                      "error": str(termination_error)})

    watcher = threading.Thread(target=monitor, name="owned-job-deadline", daemon=True)
    watcher.start()
    status = "supervisor_error"
    exit_code = None
    root_assigned = False
    active_before_cleanup = None
    cleanup_transition = "not_started"
    fault = None
    try:
        # The monitor never performs file I/O or waits for worker telemetry.
        # It is already active if launch preparation or the controller's own I/O stalls.
        save(output / "supervisor-start.json", context)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="1",
                   OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                   PVT45_SUPERVISION_CONTEXT=json.dumps(context, separators=(",", ":")),
                   **(extra_env or {}))
        with (output / "worker-console.log").open("wb") as log:
            worker = OwnedProcess.suspended(arguments, str(cwd), env, log)
            job.assign(worker)
            root_assigned = True
            if expired.is_set() or not clock_state(start, clock_sample(), seconds)["allowed"]:
                job.terminate(124)
                status = "deadline_before_worker_resume"
            else:
                worker.resume()
                launch = {"clock": clock_sample(), "worker": worker.identity,
                          "assigned_before_resume": True}
                save(output / "worker-launch.json", launch)
                status = "running"
            while worker.poll() is None:
                if crash_after_seconds is not None and time.monotonic_ns() - start["monotonic_ns"] >= \
                        int(crash_after_seconds * 1e9):
                    os._exit(93)  # synthetic ownership test: OS closes the sole non-inherited job handle
                if expired.is_set():
                    worker.wait(0.05)
                else:
                    worker.wait(0.025)
            exit_code = worker.poll()
            active_before_cleanup = job.accounting()
            cleanup_transition = "job_already_empty"
            if exit_code == 0 and not expired.is_set() and active_before_cleanup["active_processes"]:
                # Venv launchers may signal before their nested process/job
                # accounting drains. This bounded wait remains under the watchdog.
                cleanup_transition = "bounded_own_job_drain_0.25s_under_original_deadline"
                job.wait_empty(0.25)
            if active_before_cleanup["active_processes"]:
                if job.accounting()["active_processes"]:
                    cleanup_transition = "terminate_only_owned_remainder"
                    job.terminate(126)
                    status = "worker_exited_with_owned_descendants"
                else:
                    status = "expired_or_unverifiable_timing" if expired.is_set() else (
                        "worker_complete" if exit_code == 0 else "worker_failed")
            elif expired.is_set():
                status = "expired_or_unverifiable_timing"
            else:
                status = "worker_complete" if exit_code == 0 else "worker_failed"
            if not job.wait_empty(5):
                raise RuntimeError("Owned job did not become empty after termination")
    except BaseException as error:
        fault = {"type": type(error).__name__, "message": str(error)}
        try:
            job.terminate(125)
            job.wait_empty(5)
        finally:
            if worker is not None and not root_assigned:
                worker.terminate(125)
                worker.wait(5)
    finally:
        stop.set()
        watcher.join(timeout=2)
        final_clock = clock_sample()
        final_state = clock_state(start, final_clock, seconds)
        accounting = job.accounting()
        if accounting["active_processes"]:
            job.terminate(127)
            job.wait_empty(5)
            accounting = job.accounting()
        if worker is not None:
            worker.close()
        job.close()
    result = {
        "status": status, "worker_exit_code": exit_code, "start": start, "stop": final_clock,
        "limit_seconds": seconds, "final_clock_state": final_state,
        "new_window_time_conformance": final_state["allowed"] and not expired.is_set()
        and not monitor_fault and fault is None,
        "supervisor_independent_of_worker_reporting": True,
        "monitor_does_not_perform_file_io": True, "deadline_decisions": decisions,
        "monitor_faults": monitor_fault, "supervisor_fault": fault,
        "worker_was_assigned_to_owned_job_before_resume": root_assigned,
        "job_accounting_before_cleanup": active_before_cleanup,
        "cleanup_transition": cleanup_transition,
        "job_accounting_after_cleanup": accounting,
        "all_owned_processes_stopped": accounting["active_processes"] == 0,
        "termination_used_only_owned_job_or_original_suspended_process_handle": True,
        "no_process_name_or_unrelated_pid_termination": True,
        "no_hard_realtime_claim_while_host_suspended": True,
        "host_gap_not_subtracted_or_excused": True,
    }
    save(output / "supervisor-result.json", result)
    save(output / "supervisor-clock-observations.json", monitor_samples)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=1800)
    parser.add_argument("worker_command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.worker_command[1:] if args.worker_command[:1] == ["--"] else args.worker_command
    if not command:
        parser.error("An explicit owned worker command is required")
    report = supervise(command, args.cwd.resolve(), args.output.resolve(), args.seconds)
    print(json.dumps({key: report[key] for key in (
        "status", "new_window_time_conformance", "all_owned_processes_stopped", "worker_exit_code")}))
    sys.exit(0 if report["new_window_time_conformance"] and report["worker_exit_code"] == 0 else 1)

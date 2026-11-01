"""Read-only recovery of saved S14 process-termination evidence.

This module starts no process, signals no PID and never changes a tool record.
Only complete, hash-bound terminal proofs from the fixed supervisor qualify.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re

from .domain import DomainError
from .global_generation import require
from . import physical_tools as physical
from .postroute_sta import CORNERS
from .store import strict_loads
from .verification import object_hash, trusted_command, _wsl_path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "hullcirq-postlayout-cleanup-resolution-v1"


def _extended(path):
    """Use Windows long-path reads without changing recorded ordinary paths."""
    value = str(path)
    if os.name == "nt" and not value.startswith("\\\\?\\"):
        value = "\\\\?\\UNC\\" + value[2:] if value.startswith("\\\\") else "\\\\?\\" + value
    return Path(value)


def _read(path):
    try:
        return _extended(path).read_bytes()
    except OSError as error:
        raise DomainError("postlayout_cleanup_evidence_missing",
                          "The original process-termination evidence is missing or unreadable; execution stays blocked.", 409) from error


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def execution_hash(run):
    return object_hash({k: v for k, v in run.items() if k not in ("record_hash", "review_status", "acceptance_epoch")})


def termination_evidence(run):
    """Reproduce the proof from frozen bytes, independent of current runtimes."""
    require(type(run) is dict and run.get("execution_status") not in ("Queued", "Running")
            and run.get("evidence_kind") == "trusted_fixed_postlayout_execution"
            and run.get("execution_scope") == "post_route_functional_plus_sta"
            and run.get("checks", {}).get("cleanup_unresolved") is True
            and run.get("record_hash") == object_hash({k: v for k, v in run.items() if k != "record_hash"}),
            "postlayout_cleanup_not_applicable", "Select an unchanged, finished S14 attempt with unresolved cleanup.", 409)
    checks, configuration = run["checks"], run["runtime_configuration"]
    require(type(configuration) is dict and type(configuration.get("physical_runtime")) is dict
            and type(checks.get("artifacts_directory")) is str
            and type(configuration.get("working_directory")) is str,
            "postlayout_cleanup_evidence_invalid", "Retain the original fixed S14 execution directories and runtime binding.")
    root = Path(checks["artifacts_directory"]).resolve()
    working = Path(configuration["working_directory"]).resolve()
    work_root = (ROOT / ".work").resolve()
    require(root.is_absolute() and root.parent == working and root.name.startswith("postroute-")
            and working != work_root and working.is_relative_to(work_root),
            "postlayout_cleanup_path_invalid", "The saved process proof must remain in its original isolated S14 run directory.")
    runtime = configuration["physical_runtime"]
    require(runtime.get("kind") == "wsl" and type(runtime.get("executable")) is str,
            "postlayout_cleanup_evidence_invalid", "Only the frozen fixed WSL supervisor binding can be recovered.")
    records = checks.get("commands")
    require(type(records) is list and 0 < len(records) <= 11 and all(type(record) is dict for record in records),
            "postlayout_cleanup_evidence_invalid", "Retain every recorded fixed S14 command before verifying termination.")
    operation_names = ("compile", "simulate", *("sta-" + corner for corner in CORNERS))
    expected_request_paths, commands = set(), []
    for index, record in enumerate(records):
        operation = operation_names[index]
        folder = root if index < 2 else root / "sta"
        logs = folder / operation
        relative = logs.relative_to(root).as_posix()
        expected_request_paths.add(relative + "/request.json")
        raw = {name: _read(logs / name) for name in ("worker.py", "request.json", "process-start.json", "process-result.json")}
        request = strict_loads(raw["request.json"].decode("utf-8"))
        start = strict_loads(raw["process-start.json"].decode("utf-8"))
        terminal = strict_loads(raw["process-result.json"].decode("utf-8"))
        hashes = {name: _hash(value) for name, value in raw.items()}
        worker_hash, request_hash = hashes["worker.py"], hashes["request.json"]
        require(worker_hash == physical.WORKER_V2_SHA and record.get("worker_sha256") == worker_hash
                and record.get("request_sha256") == request_hash,
                "postlayout_cleanup_evidence_invalid", "The original supervisor or request differs from its saved launch identity.")
        if index < 2:
            arguments = ["python3", _wsl_path(root / "run_functional.py"), operation,
                         _hash(_read(root / "functional-inputs.json"))]
            if index == 1:
                arguments.append(_hash(_read(root / "functional-program.json")))
            timeout = 300
        else:
            arguments = ["python3", _wsl_path(folder / "run_sta.py"), CORNERS[index - 2],
                         _hash(_read(folder / "sta-inputs.json"))]
            timeout = 300
        command = trusted_command(runtime, runtime["executable"], arguments, folder)
        supervisor = trusted_command(runtime, "/usr/bin/python3",
            [_wsl_path(logs / "worker.py"), _wsl_path(logs / "request.json"),
             "--request-sha256", request_hash, "--worker-sha256", worker_hash], folder)
        expected_request = {"version": "hullcirq-physical-worker-v2", "argv": command[command.index("--exec") + 1:],
                            "cwd": _wsl_path(folder), "timeout_seconds": timeout, "worker_sha256": worker_hash}
        require(request == expected_request and record.get("command") == command
                and record.get("supervisor_command") == supervisor,
                "postlayout_cleanup_evidence_invalid", "The saved request and supervisor must match the exact recorded S14 command and paths.")
        require(type(terminal) is dict and type(start) is dict
                and terminal.get("executed") is True
                and terminal.get("status") in ("Completed", "Failed", "Cancelled", "Timeout")
                and type(terminal.get("exit_code")) is int
                and terminal.get("whole_process_group_terminated") is True
                and terminal.get("request_unchanged_at_completion") is True
                and terminal.get("worker_unchanged_at_completion") is True
                and terminal.get("process_start_sha256") == hashes["process-start.json"]
                and all(record[key] == terminal.get(key) for key in
                        ("process_start_sha256", "request_unchanged_at_completion", "worker_unchanged_at_completion") if key in record),
                "postlayout_cleanup_evidence_invalid", "The original terminal record must prove the unchanged launch and whole process-group termination.")
        physical.validate_worker_binding(request, {**terminal, "cleanup_unresolved": False}, start, folder, worker_hash)
        commands.append({"operation": operation, "relative_directory": relative,
                         "command_sha256": object_hash(command), "supervisor_command_sha256": object_hash(supervisor),
                         "raw_sha256": hashes, "terminal_status": terminal["status"], "exit_code": terminal["exit_code"],
                         "whole_process_group_terminated": True})
    actual_request_paths = {path.relative_to(_extended(root)).as_posix() for path in _extended(root).rglob("request.json")}
    require(actual_request_paths == expected_request_paths,
            "postlayout_cleanup_evidence_invalid", "Unrecorded or missing supervisor requests prevent termination recovery.")
    return {"schema": SCHEMA, "run_id": run["id"], "execution_sha256": execution_hash(run),
            "commands": commands, "scope": "saved_whole_process_group_termination_only_no_execution_or_verification_pass"}


def validate_resolution(run, resolution):
    require(type(resolution) is dict and type(resolution.get("id")) is str
            and type(resolution.get("created_at")) is str and resolution.get("actor") == "gui_operator"
            and resolution.get("provenance") == {"interface": "GUI", "action": "verify_saved_process_termination"}
            and resolution.get("run_id") == run["id"]
            and type(resolution.get("original_run_record_sha256")) is str
            and re.fullmatch(r"[0-9a-f]{64}", resolution["original_run_record_sha256"]) is not None
            and resolution.get("execution_sha256") == execution_hash(run)
            and resolution.get("record_hash") == object_hash({k: v for k, v in resolution.items() if k != "record_hash"}),
            "postlayout_cleanup_resolution_invalid", "The termination audit must bind the unchanged original failed run and its own checksum.")
    require(object_hash(resolution.get("evidence")) == object_hash(termination_evidence(run)),
            "postlayout_cleanup_resolution_invalid", "The original saved process-termination evidence changed after its audit.")

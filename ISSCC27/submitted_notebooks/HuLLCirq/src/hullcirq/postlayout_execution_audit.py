"""Read-only cross-binding of completed original-job Linux executions.

This establishes frozen request/input/process cleanup provenance. It neither
evaluates circuit outputs nor accepts a post-layout result.
"""
from __future__ import annotations
import hashlib
import math
from pathlib import Path
import re

from .physical_tools import require
from .postlayout_execution import fixed_worker_definition
from .store import strict_loads
from .verification import _wsl_path, object_hash


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_completed_execution(folder, operation, *, worker_version="v1"):
    """Check raw request, worker snapshot, birth and completed terminal proof."""
    folder = Path(folder).resolve()
    require(operation in ("compile", "simulate"), "postlayout_execution_operation", "Require a fixed operation.")
    definition = fixed_worker_definition(worker_version)
    logs = folder / operation
    raw = {name: (logs / name).read_bytes() for name in ("worker.py", "request.json", "process-start.json", "process-result.json")}
    documents = {name: strict_loads(raw[name].decode("utf-8")) for name in ("request.json", "process-start.json", "process-result.json")}
    request, start, result = (documents[name] for name in ("request.json", "process-start.json", "process-result.json"))
    require(_sha(raw["worker.py"]) == definition["_worker_sha256"], "postlayout_execution_worker", "Frozen worker bytes differ from the pinned version.")
    require(type(request) is dict and set(request) == {"version", "argv", "cwd", "timeout_seconds", "worker_sha256", "input_files", "configuration_sha256"},
            "postlayout_execution_request", "Require the complete exact frozen request.")
    require(request["version"] == definition["VERSION"] and request["worker_sha256"] == definition["_worker_sha256"]
            and request["configuration_sha256"] == object_hash(definition["CONFIGURATION"]) and request["cwd"] == _wsl_path(folder),
            "postlayout_execution_request", "Request runtime/worker/cwd identity differs.")
    expected_argv = definition["COMPILE_ARGV"] if operation == "compile" else (definition["simulation_argv"](_wsl_path(folder)) if worker_version in ("v2", "v3") else definition["SIMULATION_ARGV"])
    require(request["argv"] == list(expected_argv), "postlayout_execution_argv", "Request used a different fixed operation.")
    input_names = definition["validate_operation"](request["argv"], request["cwd"])
    require(type(request["input_files"]) is dict and set(request["input_files"]) == set(input_names),
            "postlayout_execution_inputs", "Request omits fixed source/program/plugin inputs.")
    for name in input_names:
        observed = _sha((folder / name).read_bytes())
        require(observed == request["input_files"][name], "postlayout_execution_inputs", "Retained source/program input bytes changed: " + name)
        if name in definition.get("PLUGIN_SHA256", {}):
            require(observed == definition["PLUGIN_SHA256"][name], "postlayout_execution_plugin", "Readback plugin/manifest is not the pinned implementation.")
    binding = definition["identity_fields"](request, _sha(raw["request.json"]), _sha(raw["worker.py"]))
    require(type(start) is dict and type(result) is dict and all(object_hash(document.get(key)) == object_hash(value) for document in (start, result) for key, value in binding.items()),
            "postlayout_execution_binding", "Request, process birth and terminal record do not describe one execution.")
    for key in ("process_group", "leader_starttime"):
        require(type(start.get(key)) is int and start[key] > 1 and type(result.get(key)) is int and result[key] == start[key],
                "postlayout_execution_birth", "Process-group birth identity differs.")
    require(type(start.get("boot_id")) is str and re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", start["boot_id"])
            and start.get("observed_child_cwd") in (None, request["cwd"]) and result.get("observed_child_cwd") == start.get("observed_child_cwd")
            and result.get("process_start_sha256") == _sha(raw["process-start.json"]),
            "postlayout_execution_birth", "Boot/cwd/birth snapshot binding differs.")
    require(type(result.get("exit_code")) is int and result["exit_code"] == 0 and result.get("status") == "Completed"
            and result.get("executed") is True and result.get("whole_process_group_terminated") is True
            and all(result.get(key) is True for key in ("request_unchanged_at_completion", "worker_unchanged_at_completion", "inputs_unchanged_at_completion", "runtime_unchanged_at_completion"))
            and type(result.get("elapsed_seconds")) in (int, float) and math.isfinite(result["elapsed_seconds"]) and result["elapsed_seconds"] >= 0,
            "postlayout_execution_terminal", "A completed zero-exit, unchanged-input and verified-group-cleanup proof is required.")
    return {"kind": "hullcirq-postlayout-completed-execution-audit-v1", "operation": operation, "worker_version": definition["VERSION"],
            "request_sha256": _sha(raw["request.json"]), "worker_sha256": _sha(raw["worker.py"]), "process_start_sha256": _sha(raw["process-start.json"]),
            "process_result_sha256": _sha(raw["process-result.json"]), "configuration_sha256": request["configuration_sha256"],
            "input_files_sha256": request["input_files"], "execution_binding_verified": True, "process_group_cleanup_verified": True,
            "circuit_validation_status": "Not evaluated", "adoption_permitted": False}

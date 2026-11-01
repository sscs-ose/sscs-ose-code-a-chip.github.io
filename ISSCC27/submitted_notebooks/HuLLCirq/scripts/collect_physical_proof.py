"""Collect current adopted S11 evidence without models, EDA or live writes.

The six original NPU histories and all preexisting result payloads remain
byte exact. Strict product inspection uses disposable copies. Physical files
are copied as bytes; their original paths remain in the saved tool report.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile

from collect_all_nodes_proof import HISTORIES, MAX_HISTORY_BYTES, ROOT, require
from collect_global_netlist_proof import (GLOBAL_HISTORY, WORKFLOW_HISTORY,
    decode_workflow_history, inspect_workflow_history, original_source_histories)
from collect_global_proof import history_descriptor
from node_spec_evidence import load, sha, write_json
from replay_all_nodes_proof import verify_manifest_files
from replay_global_proof import inspect_global_evidence
from hullcirq.physical_workflow import validate_artifact_manifest, validate_physical_proof
from hullcirq.server import make_server
from hullcirq.store import ProjectStore, strict_loads
from hullcirq.verification import content_hash, object_hash

PHYSICAL_HISTORY = "physical_workflow.json"
SOURCE_HISTORIES = (*HISTORIES, GLOBAL_HISTORY, WORKFLOW_HISTORY)
RECORD_KIND = "actual_original_GUI_job_S11_SKY130_routed_layout_proof"
SCOPE = "same_adopted_original_GUI_design_pinned_physical_mapping_placement_routing"
ATTEMPT_FILE_BYTES = 128 * 1024 * 1024
ATTEMPT_TOTAL_BYTES = 512 * 1024 * 1024
ATTEMPT_FILE_COUNT = 16384
ATTEMPT_TEXT_SUFFIXES = {".log", ".rpt", ".json", ".sdc", ".py", ".v", ".txt"}
ATTEMPT_LAYOUT_SUFFIXES = {".def", ".gds", ".png"}
LEGACY_EXECUTION_SOURCES = {
    "physical_worker.py": "955341ebe17cbf9457dddada8814c5a6588ef06fab19e7e207b7a72b006a09ff",
    "capture_physical_versions.py": "d1aa8290668ec384c2c556a5eec60d491f74696c83aa9cacdc3319dc93173ce1"}


def digest(value):
    return hashlib.sha256(value).hexdigest()


def valid_sha(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def read_sources(directory):
    return {name: (Path(directory) / name).read_bytes() for name in SOURCE_HISTORIES}


def require_source_bytes(current, original):
    require(type(current) is dict and type(original) is dict
            and set(current) == set(original) == set(SOURCE_HISTORIES)
            and all(type(value) is bytes and value == original[name] for name, value in current.items()),
            "The six original GUI/model/node/S08/S09/S10 histories must remain byte exact.")


def load_baseline(path, original_directory):
    raw = Path(path).read_bytes(); baseline = strict_loads(raw.decode("utf-8"))
    require(type(baseline) is dict and type(baseline.get("original_NPU_histories")) is dict
            and set(baseline["original_NPU_histories"]) == set(SOURCE_HISTORIES)
            and all(valid_sha(value) for value in baseline["original_NPU_histories"].values())
            and type(baseline.get("preexisting_files")) is dict
            and type(baseline.get("revision_id")) is str and type(baseline.get("original_settings")) is dict,
            "An exact pre-S11 baseline with all six original NPU histories is required.")
    original = read_sources(original_directory)
    require(all(digest(value) == baseline["original_NPU_histories"][name] for name, value in original.items()),
            "Original runtime copies differ from the pre-S11 baseline.")
    return baseline, raw, original


def verify_prior_payloads(baseline, root=ROOT):
    """Protect prior results; implementation/docs are intentionally evolving."""
    selected = {}
    for relative, expected in baseline["preexisting_files"].items():
        require(type(relative) is str and valid_sha(expected), "Invalid prior-file baseline entry.")
        if not relative.startswith("results/"):
            continue
        path = (Path(root) / relative).resolve()
        require(path.is_relative_to(Path(root).resolve()) and path.is_file()
                and path.relative_to(Path(root).resolve()).as_posix() == relative and sha(path) == expected,
                "A preexisting result payload was modified or removed: " + relative)
        selected[relative] = expected
    require(selected, "The baseline must bind the immutable earlier result payloads.")
    return selected


def terminal_history(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_HISTORY_BYTES, "Physical history is empty or oversized.")
    history = strict_loads(raw.decode("utf-8"))
    require(type(history) is dict and history.get("physical_workflow_store_version") == "0.1"
            and type(history.get("runs")) is list and history["runs"] and type(history.get("reviews")) is list
            and all(type(run) is dict and run.get("execution_status") not in ("Queued", "Running") for run in history["runs"]),
            "Wait for every physical attempt to terminate; all attempts and reviews must be retained.")
    return history


def latest_adopted(runs):
    require(type(runs) is list and runs, "No saved S11 execution is available.")
    run = runs[-1]
    require(type(run) is dict and run.get("stage_id") == "layout"
            and all(run.get(key) == value for key, value in (("execution_status", "Completed"),
                ("validation_status", "Passed"), ("review_status", "Accepted"), ("freshness", "Current"))),
            "The latest S11 result must be Completed, Passed, Accepted and Current.")
    return run


def require_real_origin(run):
    require(run.get("evidence_kind") in ("trusted_fixed_tool_execution", "trusted_saved_tool_revalidation")
            and run.get("checks", {}).get("software_qa_fixture") is not True
            and type(run.get("runtime_configuration")) is dict
            and type(run["runtime_configuration"].get("origin")) is str
            and bool(run["runtime_configuration"]["origin"].strip()),
            "Actual S11 evidence requires the trusted adapter and a recorded physical-profile origin; software QA is separate.")


def validate_revalidation_binding(run, runs):
    """A saved-output check never becomes another original tool execution."""
    if run.get("evidence_kind") == "trusted_fixed_tool_execution":
        require(run["checks"].get("execution_reused") is not True,
                "A new physical execution cannot be relabeled as a saved-output revalidation.")
        return None
    require(run.get("evidence_kind") == "trusted_saved_tool_revalidation"
            and run.get("execution_kind") == "saved_outputs_no_new_tool_start",
            "Unknown physical execution/revalidation provenance.")
    matches = [(index, value) for index, value in enumerate(runs) if value.get("id") == run.get("prior_run_id")]
    current = [index for index, value in enumerate(runs) if value.get("id") == run.get("id")]
    require(len(matches) == len(current) == 1 and matches[0][0] < current[0], "Saved-output revalidation must bind an earlier original run.")
    prior = matches[0][1]; old = prior["checks"]; result = run["checks"]
    require(prior.get("evidence_kind") == "trusted_fixed_tool_execution"
            and prior.get("execution_status") in ("Completed", "Failed")
            and old.get("software_qa_fixture") is not True and old.get("cleanup_unresolved") is not True
            and old.get("executed") is True and type(old.get("exit_code")) is int and old["exit_code"] == 0
            and type(old.get("commands")) is list and len(old["commands"]) == 2
            and all(c.get("executed") is True and c.get("status") == "Completed"
                    and type(c.get("exit_code")) is int and c["exit_code"] == 0 for c in old["commands"]),
            "Revalidation requires original actual completed tool executions, without unresolved cleanup or software fixtures.")
    require(run.get("previous_result_sha256") == result.get("previous_result_sha256") == object_hash(old)
            and run.get("prior_record_sha256") == object_hash(prior)
            and result.get("execution_reused") is True and result.get("revalidated_from_run_id") == prior["id"]
            and all(type(result.get(key)) is int and result[key] == 0 for key in ("revalidation_tool_starts", "revalidation_model_calls"))
            and all(object_hash(run.get(key)) == object_hash(prior.get(key)) for key in (
                "revision_id", "global_job_id", "synthesis_run_id", "netlist_run_id", "global_context_id", "global_rtl", "global_rtl_sha256",
                "source_manifest", "source_manifest_sha256", "verification_plan", "verification_plan_sha256", "vector_hash",
                "testbench_sha256", "public_boundary_vector_hash", "settings", "settings_sha256", "runtime_configuration",
                "runtime_configuration_sha256", "source_identity", "source_key", "source_epoch_at_start"))
            and object_hash(result.get("commands")) == object_hash(old["commands"])
            and all(type(result.get(key)) is str and result[key] == old.get(key) for key in ("stdout", "stderr", "artifacts_directory")),
            "Saved-output revalidation changed its original record/report, sources, command logs or typed zero-start provenance.")
    return prior


def validate_lineage(run, synthesis, simulation, global_job, baseline):
    manifest = global_job["context"]["source_manifest"]; plan = global_job["context"]["verification_plan"]
    require(run["revision_id"] == global_job["revision_id"] == baseline["revision_id"]
            and run["global_job_id"] == global_job["id"] == synthesis["global_job_id"] == simulation["global_job_id"]
            and run["synthesis_run_id"] == synthesis["id"] == simulation["prior_run_id"]
            and run["netlist_run_id"] == simulation["id"] and run["global_context_id"] == global_job["context_id"]
            and run["global_rtl"] == global_job["rtl"] and run["global_rtl_sha256"] == global_job["rtl_sha256"] == content_hash(global_job["rtl"])
            and object_hash(run["source_manifest"]) == object_hash(manifest) == run["source_manifest_sha256"]
            and object_hash(run["verification_plan"]) == object_hash(plan) == run["verification_plan_sha256"]
            and all(run[key] == plan[key] for key in ("vector_hash", "testbench_sha256", "public_boundary_vector_hash"))
            and object_hash(run["settings"]) == object_hash(baseline["original_settings"]) == run["settings_sha256"]
            and object_hash(run["runtime_configuration"]) == run["runtime_configuration_sha256"],
            "Physical sources, settings or original S08 plan differ from the adopted continuous design.")
    return manifest, plan


def inspect_physical_history(raw, original):
    """The live store is never opened by a manager or a server."""
    history = terminal_history(raw)
    configuration = history["runs"][-1].get("runtime_configuration")
    require(type(configuration) is dict, "The selected physical runtime must be frozen in its run.")
    scratch = ROOT / ".work/m2g/evidence-checks"; scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="physical-check-", dir=scratch) as name:
        folder = Path(name)
        for filename, value in original.items():
            (folder / filename).write_bytes(value)
        (folder / PHYSICAL_HISTORY).write_bytes(raw)
        server = make_server("127.0.0.1", 0, ProjectStore(folder), ROOT, physical_configuration=configuration)
        try:
            manager = server.physical_workflow
            effective = latest_adopted(manager.envelope()["physical_workflow"]["runs"])
            matches = [run for run in history["runs"] if run["id"] == effective["id"]]
            require(len(matches) == 1, "Selected S11 execution ID is missing or ambiguous.")
            selected = copy.deepcopy(matches[0]); require_real_origin(selected)
            validate_revalidation_binding(selected, history["runs"])
            from hullcirq.physical_tools import validate_layout_result
            validate_physical_proof(selected, validate_layout_result)
            require_source_bytes(read_sources(folder), original)
            require((folder / PHYSICAL_HISTORY).read_bytes() == raw,
                    "Strict inspection changed a copied terminal physical history.")
            return history, selected, effective
        finally:
            server.physical_workflow.close(); server.global_workflow.close(); server.global_generation.close()
            server.workflow.close(); server.generation.close(); server.server_close()


def decode_physical_history(directory, metadata):
    fields = {"archive", "compression", "archive_sha256", "archive_bytes", "decompressed_sha256", "decompressed_bytes"}
    require(type(metadata) is dict and set(metadata) == fields and metadata["archive"] == PHYSICAL_HISTORY + ".gz"
            and metadata["compression"] == "gzip" and valid_sha(metadata["archive_sha256"]) and valid_sha(metadata["decompressed_sha256"]),
            "Invalid fixed physical-history descriptor.")
    path = Path(directory) / metadata["archive"]; length = metadata["decompressed_bytes"]
    require(type(metadata["archive_bytes"]) is int and path.stat().st_size == metadata["archive_bytes"]
            and sha(path) == metadata["archive_sha256"] and type(length) is int and 0 < length <= MAX_HISTORY_BYTES,
            "Compressed physical history hash/length differs or expansion exceeds the limit.")
    with gzip.open(path, "rb") as stream:
        raw = stream.read(length + 1)
    require(len(raw) == length and digest(raw) == metadata["decompressed_sha256"], "Decompressed original physical history bytes differ.")
    strict_loads(raw.decode("utf-8"))
    return raw


def copy_artifacts(result, output):
    validate_artifact_manifest(result, True)
    source = Path(result["artifacts_directory"]).resolve(); exported = {}; paths = set()
    for entry in result["artifacts"]:
        relative = entry["relative_path"]
        require(PurePosixPath(relative).as_posix() == relative and relative not in paths,
                "Each declared physical artifact must have its own canonical retained path.")
        paths.add(relative); path = (source / relative).resolve(); payload = path.read_bytes()
        require(len(payload) == entry["bytes"] and digest(payload) == entry["sha256"], "Physical bytes changed while being collected.")
        destination = Path(output) / "artifacts" / Path(*PurePosixPath(relative).parts)
        destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(payload)
        exported[entry["id"]] = {**copy.deepcopy(entry), "source_path": str(path), "export_path": destination.relative_to(output).as_posix()}
    return exported


def retained_files(result):
    """Inspect raw adapter logs/reports without interpreting them as successes."""
    entries = result.get("retained_files")
    require(type(entries) is list and entries, "Retain original physical worker and per-step logs/reports.")
    root = Path(result["artifacts_directory"]).resolve(); seen = set(); selected = []
    for entry in entries:
        require(type(entry) is dict and set(entry) == {"relative_path", "sha256", "bytes"}
                and type(entry["relative_path"]) is str and valid_sha(entry["sha256"])
                and type(entry["bytes"]) is int and entry["bytes"] >= 0,
                "Invalid retained raw physical-file descriptor.")
        relative = PurePosixPath(entry["relative_path"])
        require(not relative.is_absolute() and relative.parts and relative.as_posix() == entry["relative_path"]
                and not any(part in (".", "..") for part in relative.parts)
                and "\\" not in entry["relative_path"] and ":" not in entry["relative_path"]
                and not any(ord(c) < 32 for c in entry["relative_path"]) and entry["relative_path"] not in seen,
                "Retained physical files must be unique safe paths below their original directory.")
        seen.add(entry["relative_path"]); path = (root / Path(*relative.parts)).resolve()
        require(path.is_relative_to(root) and path != root and path.is_file()
                and path.stat().st_size == entry["bytes"] and sha(path) == entry["sha256"],
                "Retained raw physical bytes changed or escaped their original directory.")
        selected.append((entry, path))
    return selected


def copy_retained_files(result, output):
    exported = []
    for entry, source in retained_files(result):
        payload = source.read_bytes()
        require(len(payload) == entry["bytes"] and digest(payload) == entry["sha256"], "Retained raw physical file changed during collection.")
        destination = Path(output) / "artifacts" / Path(*PurePosixPath(entry["relative_path"]).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        require(not destination.exists() or destination.read_bytes() == payload,
                "Main and retained physical artifacts disagree at the same path.")
        destination.write_bytes(payload)
        exported.append({**copy.deepcopy(entry), "source_path": str(source), "export_path": destination.relative_to(output).as_posix()})
    return exported


def export_logs(result, output):
    folder = Path(output) / "logs"; folder.mkdir(parents=True, exist_ok=True)
    for field in ("stdout", "stderr"):
        value = result.get(field)
        require(type(value) is str, "Retain the original adapter stdout/stderr strings.")
        (folder / ("adapter_" + field + ".txt")).write_bytes(value.encode("utf-8"))
    commands = result["commands"]
    write_json(folder / "commands.json", commands)
    for index, command in enumerate(commands):
        for field in ("stdout", "stderr"):
            value = command.get(field)
            require(type(value) is str, "Every recorded command must retain complete stdout/stderr strings.")
            (folder / f"command_{index:02d}_{field}.txt").write_bytes(value.encode("utf-8"))


def attempt_directory(run):
    """A historical diagnostic directory is not a new successful result."""
    require(type(run.get("id")) is str and re.fullmatch(r"[A-Za-z0-9_-]+", run["id"])
            and run.get("stage_id") == "layout"
            and run.get("execution_status") in ("Completed", "Failed", "Cancelled", "Interrupted"),
            "Only a terminal saved physical attempt with a safe original ID can be retained.")
    result = run["checks"]; configuration = run["runtime_configuration"]
    commands = result.get("commands", [])
    require(type(commands) is list and len(commands) <= 2 and all(type(c) is dict for c in commands),
            "Historical physical command records must remain the bounded original sequence.")
    value = result.get("artifacts_directory")
    if value is None:
        require(not commands and result.get("executed") is not True,
                "An attempted tool execution cannot lose its original artifact directory.")
        return None
    require(type(value) is str and Path(value).is_absolute()
            and type(configuration.get("working_directory")) is str and Path(configuration["working_directory"]).is_absolute(),
            "Historical physical paths must be absolute and frozen in their own runtime configuration.")
    folder = Path(value).resolve(); parent = Path(configuration["working_directory"]).resolve()
    require(folder.parent == parent and folder.name.startswith("hullcirq-layout-") and folder.is_dir(),
            "An original physical attempt directory is missing or outside its configured result root.")
    return folder


def validate_attempt_inputs(run, folder):
    """Check old inputs against their own snapshot, never today's profile.

    Tool JSON containing Infinity is copied without parsing. Only source,
    configuration and worker records use the project's strict JSON reader.
    """
    from hullcirq.global_workflow import source_bundle
    from hullcirq.physical_tools import fixed_commands
    from hullcirq.verification import _wsl_path, trusted_command
    result = run["checks"]; configuration = run["runtime_configuration"]
    require(object_hash(configuration) == run["runtime_configuration_sha256"], "Historical runtime configuration changed.")
    bundle = source_bundle(run["global_rtl"], run["source_manifest"])
    for key in ("global_rtl_sha256", "source_manifest_sha256", "settings_sha256", "runtime_configuration_sha256"):
        require(result.get(key) == run[key], "Historical adapter source/profile identity changed: " + key)
    require(object_hash(result.get("source_bundle")) == object_hash(bundle), "Historical source bundle changed.")
    expected = copy.deepcopy(configuration["profile"]["config"])
    expected.update(DESIGN_NAME=run["settings"]["top_module"], VERILOG_FILES=["dir::" + item["file"] for item in bundle],
        CLOCK_PORT=run["settings"]["clock_name"], CLOCK_PERIOD=run["settings"]["clock_period_ns"],
        PNR_SDC_FILE="dir::physical.sdc", SIGNOFF_SDC_FILE="dir::physical.sdc")
    input_manifest = {"settings": run["settings"], "runtime_configuration": configuration, "source_bundle": bundle,
        "source_manifest_sha256": run["source_manifest_sha256"], "global_rtl_sha256": run["global_rtl_sha256"]}
    staged = {"candidate_top.v": run["global_rtl"].encode("utf-8"),
              **{n["node_id"] + ".v": n["rtl"].encode("utf-8") for n in run["source_manifest"]["nodes"]}}
    commands = result.get("commands", []); executed = any(c.get("executed") is True for c in commands)
    missing = []; recorded = {}
    for name in (*staged, "config.json", "input-manifest.json", "physical.sdc", "pdk-input-manifest.json"):
        path = folder / name
        if not path.is_file():
            require(not executed, "Executed historical tools are missing a staged input: " + name)
            missing.append(name); continue
        require(path.resolve().is_relative_to(folder), "Historical staged source escaped its original directory.")
        if name in staged:
            require(path.read_bytes() == staged[name], "Historical RTL source bytes changed: " + name)
        elif name in ("config.json", "input-manifest.json"):
            value = strict_loads(path.read_bytes().decode("utf-8"))
            require(object_hash(value) == object_hash(expected if name == "config.json" else input_manifest),
                    "Historical configuration/input snapshot changed: " + name)
        else:
            expected_hash = configuration["base_sdc_sha256" if name == "physical.sdc" else "pdk_manifest_sha256"]
            require(valid_sha(expected_hash) and sha(path) == expected_hash, "Historical SDC/PDK manifest raw hash changed.")
            recorded[name] = expected_hash
    recipe = result.get("adapter_recipe", "v1")
    require(recipe in ("v1", "v2"), "Unknown historical physical command recipe.")
    fixed = fixed_commands(configuration, folder, recipe); external = []
    for index, record in enumerate(commands):
        operation = ("version", "layout")[index]; logs = folder / operation
        require(record.get("command") == fixed[index] and type(record.get("executed")) is bool,
                "Historical execution differs from its fixed command recipe.")
        for field in ("stdout", "stderr"):
            require(type(record.get(field)) is str, "Historical command output strings must remain complete.")
        request_path = logs / "request.json"
        if not request_path.is_file():
            require(record["executed"] is False, "An executed historical command lost its original request.")
            continue
        request = strict_loads(request_path.read_bytes().decode("utf-8"))
        argv = fixed[index][fixed[index].index("--exec") + 1:]
        expected_request = {"version": "hullcirq-physical-worker-" + recipe, "argv": argv,
                            "timeout_seconds": 120 if index == 0 else 7200}
        worker = logs / "worker.py" if recipe == "v2" else ROOT / "scripts/physical_worker.py"
        require(worker.is_file(), "Retain the exact original physical supervisor source.")
        worker_hash = sha(worker)
        if recipe == "v2": expected_request.update(cwd=_wsl_path(folder), worker_sha256=worker_hash)
        require(object_hash(request) == object_hash(expected_request), "Historical worker request changed.")
        request_hash = sha(request_path)
        if record["executed"] or record.get("request_sha256") is not None:
            require(record.get("request_sha256") == request_hash and record.get("worker_sha256") == worker_hash,
                    "Historical worker/request raw hash changed.")
            recorded[operation + "/request.json"] = request_hash
            if recipe == "v2": recorded[operation + "/worker.py"] = worker_hash
            elif not external:
                external.append({"relative_path": "external_sources/physical_worker_v1.py", "source_path": str(worker),
                    "sha256": worker_hash, "bytes": worker.stat().st_size,
                    "origin": "fixed_v1_supervisor_source_bound_by_original_execution_hash"})
        supervisor_args = [_wsl_path(worker), _wsl_path(request_path)]
        if recipe == "v2": supervisor_args += ["--request-sha256", request_hash, "--worker-sha256", worker_hash]
        require(record.get("supervisor_command") == trusted_command(configuration, "/usr/bin/python3", supervisor_args, folder),
                "Historical supervisor command changed.")
        exit_path = logs / "process-result.json"
        if exit_path.is_file():
            exit_record = strict_loads(exit_path.read_bytes().decode("utf-8"))
            require(type(exit_record) is dict and all(k in record and
                (k == "status" and record.get("recovery") is not None or object_hash(record[k]) == object_hash(v))
                for k, v in exit_record.items()), "Historical worker exit record differs from the saved execution.")
        else:
            require(record.get("status") != "Completed", "A completed historical command lost its actual exit record.")
        for field in ("stdout", "stderr"):
            path = logs / (field + ".log")
            require(not record["executed"] or path.is_file(), "An executed historical command lost its raw output log.")
            if path.is_file():
                require(record[field] == path.read_text(encoding="utf-8", errors="replace"),
                        "Historical raw log differs from its original decoded command output.")
        if recipe == "v2" and record.get("process_start_sha256") is not None:
            path = logs / "process-start.json"
            require(path.is_file() and sha(path) == record["process_start_sha256"], "Historical child process-start proof changed.")
            recorded[operation + "/process-start.json"] = record["process_start_sha256"]
    validate_artifact_manifest(result, False)
    for entry in result.get("artifacts", []): recorded[entry["relative_path"]] = entry["sha256"]
    if result.get("retained_files"):
        for entry, _ in retained_files(result): recorded[entry["relative_path"]] = entry["sha256"]
    return missing, recorded, external


def inspect_attempt_files(run):
    """Bounded read-only inventory, also usable with isolated SOFTWARE QA."""
    folder = attempt_directory(run)
    if folder is None:
        return {"directory": None, "files": [], "external_sources": [], "omitted_files": [],
            "missing_staged_inputs": [], "unavailable_reason": "No worker/artifact directory was created before this terminal attempt."}
    missing, recorded, external = validate_attempt_inputs(run, folder)
    candidates = []; omitted = []; layout = {}
    for directory, subdirs, filenames in os.walk(folder, followlinks=False):
        for name in sorted(subdirs):
            path = Path(directory) / name
            require(path.resolve().is_relative_to(folder), "Historical diagnostic directory escaped its original run.")
            require(not path.is_symlink() and path.resolve() == path.absolute(), "Historical diagnostic directory aliases are not traversed.")
        subdirs.sort()
        for name in sorted(filenames):
            path = Path(directory) / name; relative = path.relative_to(folder).as_posix()
            require(path.resolve().is_relative_to(folder) and path.is_file(), "Historical diagnostic file escaped its original run.")
            size = path.stat().st_size; suffix = path.suffix.lower()
            if relative in recorded:
                candidates.append((relative, path, size))
            elif suffix in ATTEMPT_LAYOUT_SUFFIXES:
                previous = layout.get(suffix)
                if previous is None or relative > previous[0]:
                    if previous is not None: omitted.append({"relative_path": previous[0], "bytes": previous[2], "reason": "Only the last path per partial-layout format is retained."})
                    layout[suffix] = (relative, path, size)
                else: omitted.append({"relative_path": relative, "bytes": size, "reason": "Only the last path per partial-layout format is retained."})
            elif suffix in ATTEMPT_TEXT_SUFFIXES or name == "cancel.request":
                candidates.append((relative, path, size))
            else:
                omitted.append({"relative_path": relative, "bytes": size, "reason": "Excluded heavy/intermediate format; no proof is inferred from it."})
    candidates += list(layout.values()); selected = []; total = 0
    require(len(candidates) <= ATTEMPT_FILE_COUNT, "Historical diagnostic file count exceeds its explicit retention bound.")
    for relative, path, size in sorted(candidates):
        if size > ATTEMPT_FILE_BYTES and path.suffix.lower() in ATTEMPT_LAYOUT_SUFFIXES and relative not in recorded:
            omitted.append({"relative_path": relative, "bytes": size, "reason": "Optional partial-layout binary exceeds the per-file bound."}); continue
        require(size <= ATTEMPT_FILE_BYTES and total + size <= ATTEMPT_TOTAL_BYTES,
                "Required historical diagnostics exceed their explicit byte bound; no truncated proof is written.")
        total += size; checksum = sha(path)
        require(relative not in recorded or checksum == recorded[relative], "A historical original file hash changed during inventory.")
        selected.append({"relative_path": relative, "source_path": str(path), "sha256": checksum, "bytes": size,
            "original_recorded_raw_sha256": recorded.get(relative), "origin_run_id": run["id"]})
    return {"directory": str(folder), "files": selected, "external_sources": external,
            "omitted_files": sorted(omitted, key=lambda e: e["relative_path"]), "missing_staged_inputs": missing,
            "unavailable_reason": None}


def copy_attempt(run, output, reviews=(), shared_files=()):
    """Preserve diagnostic bytes; do not re-run, re-review or adopt anything."""
    inventory = inspect_attempt_files(run); folder = Path(output) / "attempts" / run["id"]
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / "run_record.json", run)
    write_json(folder / "reviews.json", [r for r in reviews if r.get("run_id") == run["id"]])
    result = run["checks"]
    export_logs({"commands": result.get("commands", []), "stdout": result.get("stdout", ""), "stderr": result.get("stderr", "")}, folder)
    shared = {(str(Path(entry["source_path"]).resolve()), entry["sha256"], entry["bytes"]): entry for entry in shared_files}
    for group, prefix in (("files", "working_files"), ("external_sources", "")):
        for entry in inventory[group]:
            source = Path(entry["source_path"]); payload = source.read_bytes()
            require(len(payload) == entry["bytes"] and digest(payload) == entry["sha256"], "Historical diagnostic bytes changed during collection.")
            alias = shared.get((str(source.resolve()), entry["sha256"], entry["bytes"]))
            if alias is not None:
                require((Path(output) / alias["export_path"]).read_bytes() == payload, "Shared historical/selected bytes disagree.")
                entry.update(export_path=alias["export_path"], origin_run_id=run["id"],
                             storage="shared_exact_raw_file_with_selected_result")
                continue
            destination = folder / prefix / Path(*PurePosixPath(entry["relative_path"]).parts)
            destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(payload)
            entry["export_path"] = destination.relative_to(output).as_posix()
            entry["origin_run_id"] = run["id"]
    return {"original_run_id": run["id"], "execution_status": run["execution_status"],
        "validation_status": run["validation_status"], "review_status": run["review_status"],
        "record_object_sha256": object_hash(run), "original_record_hash": run.get("record_hash"),
        "runtime_configuration_sha256": run["runtime_configuration_sha256"],
        "source_revision_id": run["revision_id"], "source_global_job_id": run["global_job_id"],
        "synthesis_run_id": run["synthesis_run_id"], "netlist_run_id": run["netlist_run_id"],
        "scope": "diagnostic_preservation_only_no_rerun_or_new_adoption",
        "record_encoding": "Unchanged JSON object export; exact original history bytes are retained in physical_workflow.json.gz.",
        "raw_hash_scope": "Collection-time raw hashes; original preexisting raw hashes are identified separately.",
        "decoded_log_check": "Original command strings are UTF-8 replacement-decoded with universal newline translation; copied files keep raw bytes.",
        "bounds": {"file_bytes": ATTEMPT_FILE_BYTES, "total_working_file_bytes": ATTEMPT_TOTAL_BYTES, "file_count": ATTEMPT_FILE_COUNT},
        "partial_layout_selection": "Last lexicographic path per DEF/GDS/PNG format; no final-layout claim.", **inventory}


def copy_legacy_execution_sources(run, output):
    """Current byte copies of immutable sources, not pre-execution snapshots."""
    if run["checks"].get("adapter_recipe", "v1") != "v1": return []
    exported = []
    for name, expected in LEGACY_EXECUTION_SOURCES.items():
        path = ROOT / "scripts" / name; payload = path.read_bytes()
        require(digest(payload) == expected, "The immutable original v1 execution source changed: " + name)
        if name == "physical_worker.py":
            require(all(c.get("worker_sha256") == expected for c in run["checks"]["commands"] if c.get("executed") is True),
                    "The original executed v1 supervisor hash differs.")
        destination = Path(output) / "execution_sources" / name
        destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(payload)
        exported.append({"source_path": str(path), "export_path": destination.relative_to(output).as_posix(),
            "sha256": expected, "bytes": len(payload), "copy_origin": "collection_time_copy_of_immutable_legacy_source",
            "pre_execution_snapshot": False, "original_execution_record_contains_source_hash": name == "physical_worker.py"})
    return exported


def verify_attempt_copies(attempts):
    for attempt in attempts:
        for entry in (*attempt["files"], *attempt["external_sources"]):
            path = Path(entry["source_path"])
            if entry in attempt["files"]:
                require(path.resolve().is_relative_to(Path(attempt["directory"]).resolve()), "A historical diagnostic path escaped during collection.")
            require(path.is_file() and path.stat().st_size == entry["bytes"] and sha(path) == entry["sha256"],
                    "Historical raw diagnostics changed before the collection manifest was completed.")


def verify_prior_archives(global_evidence, nodes_evidence, netlist_evidence, original):
    global_manifest, nodes_manifest, global_job = inspect_global_evidence(global_evidence, nodes_evidence)
    prior = original_source_histories(global_evidence, nodes_evidence, global_manifest, nodes_manifest)
    require(all(original[name] == value for name, value in prior.items()), "The original six-node/S08 archives differ from the runtime baseline.")
    netlist_manifest = load(Path(netlist_evidence) / "manifest.json")
    require(netlist_manifest.get("record_kind") == "actual_original_GUI_job_S09_S10_generic_whole_netlist_proof",
            "The original actual S09/S10 archive is required.")
    verify_manifest_files(netlist_evidence, netlist_manifest["files"])
    raw = decode_workflow_history(netlist_evidence, netlist_manifest["global_workflow_history"])
    require(raw == original[WORKFLOW_HISTORY], "S09/S10 history differs from its immutable actual proof.")
    _, synthesis, simulation, _, _ = inspect_workflow_history(raw, prior)
    return global_job, synthesis, simulation, {
        "S04_S07": {"directory": str(Path(nodes_evidence).resolve()), "manifest_sha256": sha(Path(nodes_evidence) / "manifest.json")},
        "S08": {"directory": str(Path(global_evidence).resolve()), "manifest_sha256": sha(Path(global_evidence) / "manifest.json")},
        "S09_S10": {"directory": str(Path(netlist_evidence).resolve()), "manifest_sha256": sha(Path(netlist_evidence) / "manifest.json")}}


def collect(data_directory, baseline_path, original_directory, output, *, global_evidence=None, nodes_evidence=None, netlist_evidence=None):
    output = Path(output)
    require(not output.exists() or output.is_dir() and not any(output.iterdir()), "Use a new empty result directory; earlier proof is preserved.")
    data_directory = Path(data_directory)
    require(not output.resolve().is_relative_to(data_directory.resolve()), "Evidence output must be separate from the live project store.")
    baseline, baseline_raw, original = load_baseline(baseline_path, original_directory)
    prior_files = verify_prior_payloads(baseline); require_source_bytes(read_sources(data_directory), original)
    global_evidence = Path(global_evidence or ROOT / "results/npu_global_continuous_flow")
    nodes_evidence = Path(nodes_evidence or ROOT / "results/npu_all_nodes_continuous_flow")
    netlist_evidence = Path(netlist_evidence or ROOT / "results/npu_global_netlist_continuous_flow")
    global_job, synthesis, simulation, archives = verify_prior_archives(global_evidence, nodes_evidence, netlist_evidence, original)
    path = data_directory / PHYSICAL_HISTORY; raw = path.read_bytes()
    history, selected, effective = inspect_physical_history(raw, original)
    reused_prior = validate_revalidation_binding(selected, history["runs"])
    manifest, plan = validate_lineage(selected, synthesis, simulation, global_job, baseline)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / (PHYSICAL_HISTORY + ".gz"); archive.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    (output / "source_baseline.json").write_bytes(baseline_raw)
    documents = {"layout_record.json": selected, "layout_effective_record.json": effective,
        "layout_checks.json": selected["checks"], "reviews.json": history["reviews"], "source_manifest.json": manifest,
        "source_identity.json": selected["source_identity"], "verification_plan.json": plan,
        "original_GUI_settings.json": selected["settings"], "physical_runtime_configuration.json": selected["runtime_configuration"],
        "artifact_manifest.json": selected["checks"]["artifacts"], "retained_files.json": selected["checks"]["retained_files"]}
    for filename, value in documents.items(): write_json(output / filename, value)
    artifacts = copy_artifacts(selected["checks"], output)
    retained = copy_retained_files(selected["checks"], output); export_logs(selected["checks"], output)
    execution_sources = copy_legacy_execution_sources(selected, output)
    prior_attempts = []
    for run in history["runs"]:
        if run["id"] == selected["id"]: continue
        require_real_origin(run)
        validate_lineage(run, synthesis, simulation, global_job, baseline)
        prior_attempts.append(copy_attempt(run, output, history["reviews"], [*artifacts.values(), *retained, *execution_sources]))
    files = {p.relative_to(output).as_posix(): {"sha256": sha(p), "bytes": p.stat().st_size}
             for p in sorted(output.rglob("*")) if p.is_file()}
    result = {"record_kind": RECORD_KIND, "scope": SCOPE, "validation_status": "Passed",
        "layout_run_id": selected["id"], "source_revision_id": selected["revision_id"], "source_global_job_id": selected["global_job_id"],
        "synthesis_run_id": selected["synthesis_run_id"], "netlist_run_id": selected["netlist_run_id"],
        "global_rtl_sha256": selected["global_rtl_sha256"], "source_manifest_sha256": selected["source_manifest_sha256"],
        "verification_plan_sha256": selected["verification_plan_sha256"], "vector_hash": selected["vector_hash"],
        "testbench_sha256": selected["testbench_sha256"], "public_boundary_vector_hash": selected["public_boundary_vector_hash"],
        "original_GUI_settings_sha256": selected["settings_sha256"], "physical_runtime_configuration_sha256": selected["runtime_configuration_sha256"],
        "physical_profile_origin": selected["runtime_configuration"]["origin"], "source_identity": selected["source_identity"],
        "source_baseline_sha256": digest(baseline_raw), "prior_actual_archives": archives,
        "unchanged_original_source_histories": {name: {"sha256": digest(value), "bytes": len(value)} for name, value in original.items()},
        "unchanged_preexisting_result_files": prior_files, "physical_workflow_history": history_descriptor(archive, raw),
        "attempt_count": len(history["runs"]), "attempts": [{key: run.get(key) for key in ("id", "stage_id", "revision_id", "execution_status", "validation_status", "review_status")} for run in history["runs"]],
        "prior_attempt_diagnostics": prior_attempts,
        "legacy_execution_source_copies": execution_sources,
        "selected_execution_kind": selected.get("execution_kind", "new_fixed_tool_execution"),
        "selected_execution_reused": reused_prior is not None,
        "selected_new_tool_starts": 0 if reused_prior is not None else sum(c.get("executed") is True for c in selected["checks"]["commands"]),
        "revalidated_from_run_id": None if reused_prior is None else reused_prior["id"],
        "previous_result_sha256": selected.get("previous_result_sha256"), "prior_record_sha256": selected.get("prior_record_sha256"),
        "original_fixed_execution_record_count": sum(r.get("evidence_kind") == "trusted_fixed_tool_execution" for r in history["runs"]),
        "saved_output_revalidation_record_count": sum(r.get("evidence_kind") == "trusted_saved_tool_revalidation" for r in history["runs"]),
        "manual_human_reviews": sum(review.get("actor") == "human" for review in history["reviews"]),
        "artifacts": artifacts, "retained_files": retained, "metrics": selected["checks"]["metrics"], "model_calls": 0,
        "manual_RTL_modifications": [], "canonical_job_replaced": False, "original_source_histories_rewritten": False,
        "source_paths_rewritten": False, "logs_exported_from_retained_command_strings": True,
        "PDK_mapping": True, "layout": True, "routing_checks": copy.deepcopy(selected["checks"]["checks"]["routing"]),
        "timing_checks": copy.deepcopy(selected["checks"]["checks"]["timing"]),
        "signoff_DRC": False, "LVS": False, "formal_equivalence": False, "SDF_dynamic_simulation": False,
        "software_QA_fixtures_are_actual_evidence": False, "files": files}
    verify_prior_payloads(baseline); require_source_bytes(read_sources(data_directory), original)
    validate_artifact_manifest(selected["checks"], True)
    retained_files(selected["checks"])
    verify_attempt_copies(prior_attempts)
    validate_revalidation_binding(selected, history["runs"])
    for entry in execution_sources:
        require(sha(entry["source_path"]) == entry["sha256"], "An immutable execution-source copy changed during collection.")
    from hullcirq.physical_tools import validate_layout_result
    validate_physical_proof(selected, validate_layout_result)
    require(path.read_bytes() == raw and Path(baseline_path).read_bytes() == baseline_raw,
            "Physical history or baseline changed during collection; no completed manifest was written.")
    for label, directory in (("S04_S07", nodes_evidence), ("S08", global_evidence), ("S09_S10", netlist_evidence)):
        require(sha(directory / "manifest.json") == archives[label]["manifest_sha256"], "Prior archive manifest changed during collection.")
    require(decode_physical_history(output, result["physical_workflow_history"]) == raw, "Physical history compression was not lossless.")
    verify_manifest_files(output, files); write_json(output / "manifest.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".work/projects/npu")
    parser.add_argument("--baseline", type=Path, default=ROOT / ".work/m2g/baseline.json")
    parser.add_argument("--original-runtime", type=Path, default=ROOT / ".work/m2g/original_runtime")
    parser.add_argument("--global-evidence", type=Path, default=ROOT / "results/npu_global_continuous_flow")
    parser.add_argument("--nodes-evidence", type=Path, default=ROOT / "results/npu_all_nodes_continuous_flow")
    parser.add_argument("--netlist-evidence", type=Path, default=ROOT / "results/npu_global_netlist_continuous_flow")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = collect(args.data_dir, args.baseline, args.original_runtime, args.output,
        global_evidence=args.global_evidence, nodes_evidence=args.nodes_evidence, netlist_evidence=args.netlist_evidence)
    print(json.dumps({"validation_status": "Passed", "output": str(args.output), "layout_run_id": manifest["layout_run_id"]}))
    return 0


if __name__ == "__main__": raise SystemExit(main())

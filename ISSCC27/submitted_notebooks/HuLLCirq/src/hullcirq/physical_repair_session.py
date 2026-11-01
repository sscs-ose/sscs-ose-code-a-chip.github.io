"""Explicit, host-local preparation of the fixed NPU2 correction chain.

Preparation reproduces complete failed S14 evidence and a source-bound runtime
bundle. It launches no tool, writes no RTL and creates no workflow attempt.
The bundle is deliberately outside project backups and is revalidated before
its runtime configurations are restored on this host.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile

from .domain import DomainError
from .presentation_revision import same_source_design
from .store import _replace_with_windows_retry, strict_loads, utc_now
from .verification import object_hash
from .physical_tools import ROOT

SCHEMA = "hullcirq-gui-physical-repair-session-v1"
BUNDLE_NAME = "physical_repair_runtime.json"
RETRY_SCHEMA = "hullcirq-gui-physical-repair-session-v2"
RETRY_BUNDLE_NAME = "physical_repair_runtime_v2.json"
FINAL_SCHEMA = "hullcirq-gui-physical-repair-session-v3"
FINAL_BUNDLE_NAME = "physical_repair_runtime_v3.json"
GENERIC_SCHEMA = "hullcirq-gui-generic-physical-repair-session-v1"
CONFIG_NAMES = ("compiler", "synthesizer", "physical", "drc", "lvs", "postlayout")
CHECKS = ("source_identity", "configuration", "functional", "parasitics", "constraints", "setup_hold", "electrical")
MANAGERS = ("generation", "generation_batches", "repair_analysis", "workflow", "implementation_specs",
            "global_generation", "global_workflow", "physical_workflow", "drc_workflow", "lvs_workflow", "postlayout_workflow")


def _require(condition, code, message):
    if not condition:
        raise DomainError(code, message, 409)


def _checksum(record):
    _require(type(record) is dict and record.get("record_hash") == object_hash(
        {key: value for key, value in record.items() if key != "record_hash"}),
        "physical_repair_record_changed", "Retain the original durable source and failed S14 record checksums.")


class _RestorationReads:
    """One restoration's parsed inputs, guarded by their exact current bytes.

    Never retain this object on a store or manager. Repeated ancestor checks
    may reuse parsing, but a changed input must abort rather
    than combine a cached ancestor with a different durable history.
    """
    def __init__(self):
        self.inputs = {}
        self.histories = {}

    def _identity(self, path):
        return path.resolve(), hashlib.sha256(path.read_bytes()).hexdigest()

    def verify(self):
        for path, identity in self.inputs.items():
            _require(self._identity(path) == identity, "physical_repair_history_changed",
                     "Saved physical history changed during profile restoration; refresh and reopen the system.")

    def bytes(self, path):
        raw = path.read_bytes()
        identity = (path.resolve(), hashlib.sha256(raw).hexdigest())
        _require(path not in self.inputs or self.inputs[path] == identity, "physical_repair_history_changed",
                 "Saved physical history changed during profile restoration; refresh and reopen the system.")
        self.inputs[path] = identity
        return raw

    def saved(self, path):
        raw = self.bytes(path)
        if path in self.histories:
            return copy.deepcopy(self.histories[path])
        value = strict_loads(raw.decode("utf-8"))
        self.histories[path] = value
        return copy.deepcopy(value)


def _saved(store, name, read_cache=None):
    path = store.state_path.parent / (name + ".json")
    value = (read_cache.saved(path) if read_cache is not None
             else strict_loads(path.read_text(encoding="utf-8")))
    _require(type(value) is dict and type(value.get("runs")) is list and type(value.get("reviews")) is list,
             "physical_repair_history_invalid", "The original physical verification history is unavailable.")
    return value


def _failure(store, identifier, revision_id, read_cache=None):
    from .postlayout_workflow import POST_ROUTE_SCOPE, validate_source_snapshot, validate_artifact_manifest
    from .postroute_tools import validate_failed_postlayout_result
    state = _saved(store, "postlayout_workflow", read_cache)
    matches = [record for record in state["runs"] if record.get("id") == identifier]
    _require(len(matches) == 1, "physical_repair_failure_missing", "Select the saved complete electrical-only S14 failure.")
    run = matches[0]
    _checksum(run)
    same_source_design(store, revision_id)
    result = run.get("checks")
    _require(run.get("revision_id") == revision_id and run.get("stage_id") == "post_layout_verification"
             and run.get("execution_status") == "Completed" and run.get("validation_status") == "Failed"
             and run.get("execution_scope") == POST_ROUTE_SCOPE and run.get("verification_supported") is True
             and run.get("evidence_kind") == "trusted_fixed_postlayout_execution" and run.get("error") is None
             and type(result) is dict and result.get("origin") == "trusted_fixed_postlayout_adapter"
             and result.get("execution_scope") == POST_ROUTE_SCOPE and result.get("status") == "Completed"
             and result.get("validation_status") == "Failed" and result.get("executed") is True
             and type(result.get("exit_code")) is int and result["exit_code"] == 0
             and result.get("cleanup_unresolved") is not True and result.get("software_qa_fixture") is not True
             and type(result.get("commands")) is list and len(result["commands"]) == 11
             and all(type(command) is dict and command.get("executed") is True
                     and command.get("status") == "Completed" and type(command.get("exit_code")) is int
                     and command["exit_code"] == 0 and command.get("cleanup_unresolved") is not True
                     for command in result["commands"])
             and type(result.get("checks")) is dict and set(result["checks"]) == set(CHECKS)
             and all(type(result["checks"][name]) is dict
                     and result["checks"][name].get("validation_status") == ("Failed" if name == "electrical" else "Passed")
                     for name in CHECKS),
             "physical_repair_failure_ineligible",
             "Fixed physical repair requires a completed actual S14 run with eleven successful commands; only electrical checks may fail.")
    validate_source_snapshot(run)
    validate_artifact_manifest(result, True)
    records = {}
    for name, filename in (("layout", "physical_workflow"), ("drc", "drc_workflow"), ("lvs", "lvs_workflow")):
        snapshot = run[name + "_snapshot"]
        _checksum(snapshot)
        source_state = _saved(store, filename, read_cache)
        matches = [record for record in source_state["runs"] if record.get("id") == snapshot["id"]]
        _require(len(matches) == 1 and object_hash(matches[0]) == object_hash(snapshot)
                 and any(object_hash(review) == object_hash(run[name + "_adoption"]) for review in source_state["reviews"]),
                 "physical_repair_source_changed", "The exact original S11/S12/S13 records and authoritative adoptions must remain saved.")
        records[name] = snapshot
    validate_failed_postlayout_result(result, records["lvs"], records["drc"], records["layout"], run["runtime_configuration"])
    # Proof validators also inspect external frozen artifacts, reports and
    # runtime inputs. They must execute afresh even when the JSON is unchanged.
    return run, records


def _base_hashes(configurations):
    _require(type(configurations) in (tuple, list) and len(configurations) == len(CONFIG_NAMES),
             "physical_repair_base_unavailable", "Retain the complete server runtime configuration set.")
    return {name: object_hash(configuration) for name, configuration in zip(CONFIG_NAMES, configurations)}


def _generic_layout(layout):
    return layout.get("verification_plan", {}).get("kind") == "generic_cycle_vectors"


def _build(layout, configurations, failed_s14=None):
    from .physical_repair import prepare_npu2_configuration
    from .drc_tools import configuration_projection as drc_projection
    from .lvs_tools import configuration_projection as lvs_projection
    _base_hashes(configurations)
    _require(all(type(configurations[index]) is dict for index in (2, 3, 4))
             and object_hash(configurations[2]) == object_hash(layout["runtime_configuration"])
             and all(object_hash(configurations[index].get("physical_runtime")) == object_hash(configurations[2]) for index in (3, 4)),
             "physical_repair_base_conflict", "Prepare correction only with the original explicitly configured S11/S12/S13 runtimes.")
    generic = _generic_layout(layout)
    work_name = "generic_repair_v1" if generic else "n2r"
    root = (ROOT / ".work" / work_name).resolve()
    _require(root.is_relative_to((ROOT / ".work").resolve())
             and not (ROOT / ".work" / work_name).is_symlink() and not (ROOT / ".work" / work_name).is_junction(),
             "physical_repair_path_invalid", "The fixed correction work directory must stay inside HuLLCirq/.work.")
    destinations = {name: root / child for name, child in (("physical", "p"), ("drc", "d"), ("lvs", "l"))}
    _require(all(not path.is_symlink() and not path.is_junction() and path.resolve().parent == root for path in destinations.values()),
             "physical_repair_path_invalid", "Fixed correction directories cannot be linked outside their host scope.")
    if generic:
        from .physical_repair_generic import prepare_configuration
        physical = prepare_configuration(layout, destinations["physical"], failed_s14)
    else:
        physical = prepare_npu2_configuration(layout, destinations["physical"])
    derived = {"physical": physical}
    for name, index in (("drc", 3), ("lvs", 4)):
        value = copy.deepcopy(configurations[index])
        value.update(physical_runtime=copy.deepcopy(physical), working_directory=str(destinations[name]))
        derived[name] = value
    # Check the derived settings/profiles without inventing a completed layout.
    preview = copy.deepcopy(layout)
    preview["runtime_configuration"] = physical
    drc_projection(preview, derived["drc"])
    lvs_projection({"layout_snapshot": preview, "layout_record_sha256": object_hash(preview)}, preview, derived["lvs"])
    return derived


def _identity(run, records):
    from .postlayout_cleanup import execution_hash
    return {"failed_s14_id": run["id"], "failed_s14_execution_sha256": execution_hash(run),
            **{name + "_run_id": record["id"] for name, record in records.items()},
            **{name + "_record_sha256": object_hash(record) for name, record in records.items()}}


def _bundle_path(profile_directory, name=BUNDLE_NAME):
    _require(name in (BUNDLE_NAME, RETRY_BUNDLE_NAME, FINAL_BUNDLE_NAME), "physical_repair_profile_path", "Use only a fixed correction bundle name.")
    directory = Path(profile_directory).absolute()
    _require(not directory.is_symlink() and not directory.is_junction()
             and directory.resolve().parent.name == "runtime_profiles",
             "physical_repair_profile_path", "Use the compact host-managed system profile directory.")
    path = directory / name
    _require(not path.is_symlink() and not path.is_junction(),
             "physical_repair_profile_path", "The saved physical correction bundle cannot be a link.")
    return path


def _validate_bundle(bundle, store, configurations, project_id, system_id, read_cache=None):
    _checksum(bundle)
    _require(set(bundle) == {"schema", "project_id", "system_id", "revision_id", "base_configuration_sha256",
                            "source_identity", "configurations", "actor", "created_at", "record_hash"}
             and bundle.get("schema") in (SCHEMA, GENERIC_SCHEMA) and bundle.get("project_id") == project_id
             and bundle.get("system_id") == system_id and bundle.get("actor") == "explicit_GUI_action"
             and type(bundle.get("created_at")) is str and type(bundle.get("revision_id")) is str
             and bundle.get("base_configuration_sha256") == _base_hashes(configurations)
             and type(bundle.get("source_identity")) is dict,
             "physical_repair_profile_incompatible", "The saved correction profile does not match this exact host runtime, system or saved revision; its bytes were preserved.")
    run, records = _failure(store, bundle["source_identity"].get("failed_s14_id"), bundle["revision_id"], read_cache)
    _require(bundle["schema"] == (GENERIC_SCHEMA if _generic_layout(records["layout"]) else SCHEMA),
             "physical_repair_profile_incompatible", "Keep generic fresh correction separate from fixed original NPU checkpoint recipes.")
    _require(bundle["source_identity"] == _identity(run, records), "physical_repair_profile_incompatible",
             "The source or failed S14 execution changed after correction preparation; the saved bundle was preserved.")
    derived = _build(records["layout"], configurations, run) if _generic_layout(records["layout"]) else _build(records["layout"], configurations)
    _require(object_hash(bundle.get("configurations")) == object_hash(derived), "physical_repair_profile_incompatible",
             "The saved correction runtime differs from the fixed source-bound builder; its bytes were preserved.")
    return derived


def _load_legacy_repair_configurations(store, configurations, profile_directory, project_id, system_id):
    """Read-only restoration before manager construction; invalid bundles stay saved."""
    original = tuple(copy.deepcopy(configurations))
    status = {"configured": False, "bundle_present": False, "error": None}
    try:
        path = _bundle_path(profile_directory)
        retry_path = _bundle_path(profile_directory, RETRY_BUNDLE_NAME)
        final_path = _bundle_path(profile_directory, FINAL_BUNDLE_NAME)
        bundle_presence = tuple(item.exists() for item in (path, retry_path, final_path))
        if not path.exists():
            status["bundle_present"] = retry_path.exists() or final_path.exists()
            _require(not status["bundle_present"], "physical_repair_profile_incompatible",
                     "Later corrections require their original first correction bundle; existing bytes were preserved.")
            return original, status
        status["bundle_present"] = True
        _require(path.is_file(), "physical_repair_profile_incompatible", "The saved correction bundle is not an ordinary file.")
        read_cache = _RestorationReads()
        raw = read_cache.bytes(path)
        bundle = strict_loads(raw.decode("utf-8"))
        derived = _validate_bundle(bundle, store, original, project_id, system_id, read_cache)
        generation = 1
        identity = bundle["source_identity"]
        generic = bundle["schema"] == GENERIC_SCHEMA
        _require(not generic or not (retry_path.exists() or final_path.exists()),
                 "physical_repair_profile_incompatible", "Generic fresh correction cannot inherit fixed NPU checkpoint retries; existing bundles were preserved.")
        _require(not final_path.exists() or retry_path.exists(), "physical_repair_profile_incompatible",
                 "The third correction requires its unchanged second correction bundle; existing bytes were preserved.")
        if retry_path.exists():
            _require(retry_path.is_file(), "physical_repair_profile_incompatible", "The second correction bundle must be an ordinary file.")
            retry_raw = read_cache.bytes(retry_path)
            retry = strict_loads(retry_raw.decode("utf-8"))
            derived = _validate_retry_bundle(retry, raw, bundle, derived, store, original, project_id, system_id, read_cache)
            generation, identity = 2, retry["source_identity"]
        if final_path.exists():
            _require(final_path.is_file(), "physical_repair_profile_incompatible", "The third correction bundle must be an ordinary file.")
            final = strict_loads(read_cache.bytes(final_path).decode("utf-8"))
            derived = _validate_final_bundle(final, raw, bundle, retry_raw, retry, derived,
                                             store, original, project_id, system_id, read_cache)
            generation, identity = 3, final["source_identity"]
        result = list(original)
        for name, index in (("physical", 2), ("drc", 3), ("lvs", 4)):
            result[index] = copy.deepcopy(derived[name])
        _require(tuple(item.exists() for item in (path, retry_path, final_path)) == bundle_presence,
                 "physical_repair_history_changed",
                 "Saved correction bundles changed during profile restoration; refresh and reopen the system.")
        read_cache.verify()
        status.update(configured=True, source_identity=copy.deepcopy(identity), repair_generation=generation,
                      profile_version=derived["physical"]["profile"]["profile_version"])
        if generic:
            status.update(session_schema=GENERIC_SCHEMA, implementation_kind="fresh_generic_standard_electrical_closure",
                          technology_mapping_reused=False)
        return tuple(result), status
    except (DomainError, OSError, ValueError, KeyError, TypeError, UnicodeError) as error:
        status["error"] = {"code": getattr(error, "code", "physical_repair_profile_unavailable"),
                           "message": getattr(error, "message", "The saved correction profile could not be restored; its bytes were preserved.")}
        return original, status


def _write(path, bundle):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".physical-repair-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(bundle, ensure_ascii=False, allow_nan=False, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        _replace_with_windows_retry(temporary, path)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()


def load_repair_configurations(store, configurations, profile_directory, project_id, system_id):
    prior, status = _load_legacy_repair_configurations(store, configurations, profile_directory, project_id, system_id)
    from .generic_physical_retry_session import restore
    return restore(store, configurations, profile_directory, project_id, system_id, prior, status)


def prepare_repair(server, failed_s14_id, revision_id):
    """Validate and persist one explicit GUI correction setup; execute nothing."""
    from .physical_repair_generic import is_generic
    if is_generic(getattr(server.physical_workflow, 'tool_configuration', None)):
        from .generic_physical_retry_session import prepare
        return prepare(server, failed_s14_id, revision_id, 'post_layout_verification')
    from .workspace_server import _postlayout_profile_directory
    _require(type(failed_s14_id) is str and type(revision_id) is str,
             "physical_repair_request_invalid", "Provide only the saved failed S14 ID and current revision ID.")
    with server.execution_lock:
        workspace = getattr(server, "workspace", None)
        _require(workspace is not None and workspace.context is not None and not workspace.identity["read_only"],
                 "physical_repair_session_unavailable", "Open the editable original system before preparing its fixed physical correction.")
        for name in MANAGERS:
            manager = getattr(server, name, None)
            _require(manager is not None and not getattr(manager, "_storage_error", None)
                     and not (getattr(manager, "_worker", None) and manager._worker.is_alive())
                     and not (hasattr(manager, "is_active") and manager.is_active()),
                     "physical_repair_busy", "Finish active work, resolve process cleanup and saved-history errors before preparing physical correction.")
        postlayout = server.postlayout_workflow
        with postlayout._source_locks(), postlayout.lock:
            postlayout.observe_design()
            runs = postlayout._state["runs"]
            _require(runs and runs[-1]["id"] == failed_s14_id and postlayout._decorate(runs[-1])["freshness"] == "Current"
                     and server.store.envelope()["revision"]["id"] == revision_id,
                     "physical_repair_source_not_current", "Prepare correction only from the latest current S14 failure and current saved revision.")
            run, records = _failure(server.store, failed_s14_id, runs[-1]["revision_id"])
            _require(object_hash(runs[-1]) == object_hash(run), "physical_repair_record_changed", "Refresh the latest durable failed S14 record.")
            _, _, current_records, _ = postlayout._adopted_sources_locked()
            _require(all(object_hash(current_records[name]) == object_hash(record) for name, record in records.items()),
                     "physical_repair_source_not_current", "The failed S14 must bind the exact currently adopted S11/S12/S13 chain.")
            postlayout._validate_sources(records["lvs"], records["drc"], records["layout"])
            configurations = workspace.configurations
            _require(all(object_hash(getattr(server, name + "_workflow").tool_configuration) == object_hash(configurations[index])
                         for name, index in (("physical", 2), ("drc", 3), ("lvs", 4))),
                     "physical_repair_already_configured", "The physical runtimes already differ from this service's original setup. Refresh their saved correction state.")
            generic = _generic_layout(records["layout"])
            derived = _build(records["layout"], configurations, run) if generic else _build(records["layout"], configurations)
            identity = workspace.identity
            directory = _postlayout_profile_directory(workspace.registry.root, identity["project_id"], identity["system_id"])
            path = _bundle_path(directory)
            _require(not any(_bundle_path(directory, name).exists() for name in (BUNDLE_NAME, RETRY_BUNDLE_NAME, FINAL_BUNDLE_NAME)),
                     "physical_repair_profile_exists", "A saved correction bundle already exists. Its bytes were preserved; refresh the saved correction state.")
            bundle = {"schema": GENERIC_SCHEMA if generic else SCHEMA, "project_id": identity["project_id"], "system_id": identity["system_id"],
                      "revision_id": run["revision_id"], "base_configuration_sha256": _base_hashes(configurations),
                      "source_identity": _identity(run, records), "configurations": derived,
                      "actor": "explicit_GUI_action", "created_at": utc_now()}
            bundle["record_hash"] = object_hash(bundle)
            _write(path, bundle)
            status = {"configured": True, "bundle_present": True, "error": None,
                      "repair_generation": 1,
                      "source_identity": copy.deepcopy(bundle["source_identity"]),
                      "profile_version": derived["physical"]["profile"]["profile_version"]}
            if generic:
                status.update(session_schema=GENERIC_SCHEMA, implementation_kind="fresh_generic_standard_electrical_closure",
                              technology_mapping_reused=False)
            workspace.context.physical_repair_session = copy.deepcopy(status)
            server.physical_repair_session = copy.deepcopy(status)
            for name in ("physical", "drc", "lvs"):
                getattr(server, name + "_workflow").tool_configuration = copy.deepcopy(derived[name])
        # New runtime identities make the earlier results stale while preserving
        # every original attempt and adoption record. No execution is started.
        for name in ("physical_workflow", "drc_workflow", "lvs_workflow", "postlayout_workflow"):
            getattr(server, name).observe_design()
        return copy.deepcopy(status)


def _retry_failure(store, identifier, revision_id, original_layout, first_configurations, *, final=False, read_cache=None):
    """Require a complete unadopted electrical-only failure of correction one."""
    from .physical_workflow import validate_failed_physical_proof
    from .physical_tools import validate_failed_layout_result
    state = _saved(store, "physical_workflow", read_cache)
    matches = [record for record in state["runs"] if record.get("id") == identifier]
    _require(len(matches) == 1, "physical_repair_retry_source_missing",
             "Select the saved complete second-correction layout failure." if final else "Select the saved complete first-correction layout failure.")
    run = matches[0]
    _checksum(run)
    result = run.get("checks")
    required = ("source_identity", "configuration", "routing", "timing", "electrical")
    _require(run.get("revision_id") == revision_id and run.get("stage_id") == "layout"
             and run.get("execution_status") == "Completed" and run.get("validation_status") == "Failed"
             and run.get("review_status") != "Accepted" and run.get("error") is None
             and run.get("evidence_kind") == "trusted_fixed_tool_execution"
             and object_hash(run.get("runtime_configuration")) == object_hash(first_configurations["physical"])
             and run.get("runtime_configuration_sha256") == object_hash(first_configurations["physical"])
             and type(result) is dict and result.get("origin") == "trusted_fixed_tool_adapter"
             and result.get("validation_status") == "Failed" and result.get("executed") is True
             and type(result.get("exit_code")) is int and result["exit_code"] == 0
             and result.get("cleanup_unresolved") is not True and result.get("software_qa_fixture") is not True
             and result.get("technology_mapping_executed") is False and result.get("upstream_technology_mapping_reused") is True
             and type(result.get("commands")) is list and len(result["commands"]) == 2
             and all(type(command) is dict and command.get("executed") is True and command.get("status") == "Completed"
                     and type(command.get("exit_code")) is int and command["exit_code"] == 0
                     and command.get("cleanup_unresolved") is not True for command in result["commands"])
             and type(result.get("checks")) is dict and set(result["checks"]) == set(required)
             and all(type(result["checks"][name]) is dict
                     and result["checks"][name].get("validation_status") == ("Failed" if name == "electrical" else "Passed")
                     for name in required)
             and type(result.get("diagnostics")) is list
             and object_hash(run.get("diagnostics")) == object_hash(result["diagnostics"])
             and [item.get("code") for item in result["diagnostics"] if type(item) is dict and item.get("severity") == "error"] == ["physical_checks_failed"],
             "physical_repair_retry_ineligible",
             ("Third correction requires the complete actual second-correction S11 failure; only electrical checks may fail and process cleanup must be resolved."
              if final else "Second correction requires the complete actual first-correction S11 failure; only electrical checks may fail and process cleanup must be resolved."))
    source_fields = ("global_job_id", "global_rtl", "global_rtl_sha256", "source_manifest", "source_manifest_sha256",
                     "settings", "settings_sha256", "verification_plan", "verification_plan_sha256", "vector_hash",
                     "testbench_sha256", "public_boundary_vector_hash")
    _require(all(field in original_layout and field in run and object_hash(run[field]) == object_hash(original_layout[field])
                 for field in source_fields), "physical_repair_retry_source_changed",
             ("Third correction must retain the exact original job, RTL, node source manifest, settings and verification plan."
              if final else "Second correction must retain the exact original job, RTL, node source manifest, settings and verification plan."))
    validate_failed_physical_proof(run, validate_failed_layout_result)
    return run


def _build_retry(failed_layout, configurations):
    from .physical_repair import prepare_npu2_retry_configuration
    from .drc_tools import configuration_projection as drc_projection
    from .lvs_tools import configuration_projection as lvs_projection
    root = (ROOT / ".work" / "n2s").resolve()
    _require(root.is_relative_to((ROOT / ".work").resolve())
             and not (ROOT / ".work" / "n2s").is_symlink() and not (ROOT / ".work" / "n2s").is_junction(),
             "physical_repair_path_invalid", "Keep the fixed second correction inside HuLLCirq/.work.")
    destinations = {name: root / child for name, child in (("physical", "p"), ("drc", "d"), ("lvs", "l"))}
    _require(all(not path.is_symlink() and not path.is_junction() and path.resolve().parent == root for path in destinations.values()),
             "physical_repair_path_invalid", "Second correction directories cannot be linked outside their host scope.")
    physical = prepare_npu2_retry_configuration(failed_layout, destinations["physical"])
    derived = {"physical": physical}
    for name, index in (("drc", 3), ("lvs", 4)):
        value = copy.deepcopy(configurations[index])
        value.update(physical_runtime=copy.deepcopy(physical), working_directory=str(destinations[name]))
        derived[name] = value
    preview = copy.deepcopy(failed_layout)
    preview["runtime_configuration"] = physical
    drc_projection(preview, derived["drc"])
    lvs_projection({"layout_snapshot": preview, "layout_record_sha256": object_hash(preview)}, preview, derived["lvs"])
    return derived


def _retry_identity(first_bundle, failed_layout):
    from .postlayout_cleanup import execution_hash
    return {**copy.deepcopy(first_bundle["source_identity"]), "failed_layout_run_id": failed_layout["id"],
            "failed_layout_execution_sha256": execution_hash(failed_layout)}


def _validate_retry_bundle(bundle, first_raw, first_bundle, first_configurations, store, configurations, project_id, system_id, read_cache=None):
    _checksum(bundle)
    _require(set(bundle) == {"schema", "project_id", "system_id", "revision_id", "base_configuration_sha256",
                            "previous_bundle_sha256", "source_identity", "configurations", "actor", "created_at", "record_hash"}
             and bundle.get("schema") == RETRY_SCHEMA and bundle.get("project_id") == project_id and bundle.get("system_id") == system_id
             and bundle.get("revision_id") == first_bundle["revision_id"]
             and bundle.get("actor") == "explicit_GUI_action" and type(bundle.get("created_at")) is str
             and bundle.get("base_configuration_sha256") == _base_hashes(configurations)
             and bundle.get("previous_bundle_sha256") == hashlib.sha256(first_raw).hexdigest()
             and type(bundle.get("source_identity")) is dict,
             "physical_repair_profile_incompatible", "The second correction bundle must retain its exact original host bundle, runtime, system and revision; saved bytes were preserved.")
    _, records = _failure(store, first_bundle["source_identity"]["failed_s14_id"], first_bundle["revision_id"], read_cache)
    run = _retry_failure(store, bundle["source_identity"].get("failed_layout_run_id"), bundle["revision_id"], records["layout"], first_configurations, read_cache=read_cache)
    _require(bundle["source_identity"] == _retry_identity(first_bundle, run), "physical_repair_profile_incompatible",
             "The original S14 source or first-correction S11 execution changed; the second correction bundle was preserved.")
    derived = _build_retry(run, configurations)
    _require(object_hash(bundle.get("configurations")) == object_hash(derived), "physical_repair_profile_incompatible",
             "The second correction configuration differs from its fixed source-bound builder; saved bytes were preserved.")
    return derived


def _prepare_second(server, failed_layout_id, revision_id):
    """Advance explicitly to the fixed second profile; preserve the first bundle."""
    from .workspace_server import _postlayout_profile_directory
    _require(type(failed_layout_id) is str and type(revision_id) is str,
             "physical_repair_request_invalid", "Provide only the saved failed layout ID and current revision ID.")
    with server.execution_lock:
        workspace = getattr(server, "workspace", None)
        _require(workspace is not None and workspace.context is not None and not workspace.identity["read_only"],
                 "physical_repair_session_unavailable", "Open the editable original system before preparing the second correction.")
        for name in MANAGERS:
            manager = getattr(server, name, None)
            _require(manager is not None and not getattr(manager, "_storage_error", None)
                     and not (getattr(manager, "_worker", None) and manager._worker.is_alive())
                     and not (hasattr(manager, "is_active") and manager.is_active()),
                     "physical_repair_busy", "Finish active work, resolve cleanup and saved-history errors before preparing the second correction.")
        physical = server.physical_workflow
        with physical._source_locks(), physical.lock:
            physical.observe_design()
            runs = physical._state["runs"]
            _require(runs and runs[-1]["id"] == failed_layout_id and physical._decorate(runs[-1])["freshness"] == "Current"
                     and server.store.envelope()["revision"]["id"] == revision_id,
                     "physical_repair_source_not_current", "Prepare the second correction only from the latest current failed layout and saved revision.")
            identity = workspace.identity
            directory = _postlayout_profile_directory(workspace.registry.root, identity["project_id"], identity["system_id"])
            path = _bundle_path(directory)
            retry_path = _bundle_path(directory, RETRY_BUNDLE_NAME)
            _require(path.is_file() and not retry_path.exists() and not _bundle_path(directory, FINAL_BUNDLE_NAME).exists(), "physical_repair_profile_exists",
                     "Retain the original first correction bundle; an existing second bundle cannot be overwritten.")
            first_raw = path.read_bytes()
            first_bundle = strict_loads(first_raw.decode("utf-8"))
            configurations = workspace.configurations
            first = _validate_bundle(first_bundle, server.store, configurations, identity["project_id"], identity["system_id"])
            _require(all(object_hash(getattr(server, name + "_workflow").tool_configuration) == object_hash(first[name])
                         for name in ("physical", "drc", "lvs")),
                     "physical_repair_retry_configuration_conflict", "The active physical runtimes must match the saved first correction bundle exactly.")
            source_revision_id = first_bundle["revision_id"]
            _, records = _failure(server.store, first_bundle["source_identity"]["failed_s14_id"], source_revision_id)
            run = _retry_failure(server.store, failed_layout_id, source_revision_id, records["layout"], first)
            _require(object_hash(run) == object_hash(runs[-1]), "physical_repair_record_changed", "Refresh the latest durable failed layout record.")
            derived = _build_retry(run, configurations)
            bundle = {"schema": RETRY_SCHEMA, "project_id": identity["project_id"], "system_id": identity["system_id"],
                      "revision_id": source_revision_id, "base_configuration_sha256": _base_hashes(configurations),
                      "previous_bundle_sha256": hashlib.sha256(first_raw).hexdigest(),
                      "source_identity": _retry_identity(first_bundle, run), "configurations": derived,
                      "actor": "explicit_GUI_action", "created_at": utc_now()}
            bundle["record_hash"] = object_hash(bundle)
            _require(path.read_bytes() == first_raw, "physical_repair_record_changed", "The original correction bundle changed during preparation.")
            _write(retry_path, bundle)
            status = {"configured": True, "bundle_present": True, "error": None, "repair_generation": 2,
                      "source_identity": copy.deepcopy(bundle["source_identity"]),
                      "profile_version": derived["physical"]["profile"]["profile_version"]}
            workspace.context.physical_repair_session = copy.deepcopy(status)
            server.physical_repair_session = copy.deepcopy(status)
            for name in ("physical", "drc", "lvs"):
                getattr(server, name + "_workflow").tool_configuration = copy.deepcopy(derived[name])
        for name in ("physical_workflow", "drc_workflow", "lvs_workflow", "postlayout_workflow"):
            getattr(server, name).observe_design()
        return copy.deepcopy(status)


def _build_final(failed_layout, configurations):
    from .physical_repair import prepare_npu2_final_configuration
    from .drc_tools import configuration_projection as drc_projection
    from .lvs_tools import configuration_projection as lvs_projection
    root = (ROOT / ".work" / "n2t").resolve()
    _require(root.is_relative_to((ROOT / ".work").resolve())
             and not (ROOT / ".work" / "n2t").is_symlink() and not (ROOT / ".work" / "n2t").is_junction(),
             "physical_repair_path_invalid", "Keep the fixed third correction inside HuLLCirq/.work.")
    destinations = {name: root / child for name, child in (("physical", "p"), ("drc", "d"), ("lvs", "l"))}
    _require(all(not path.is_symlink() and not path.is_junction() and path.resolve().parent == root for path in destinations.values()),
             "physical_repair_path_invalid", "Third correction directories cannot be linked outside their host scope.")
    physical = prepare_npu2_final_configuration(failed_layout, destinations["physical"])
    derived = {"physical": physical}
    for name, index in (("drc", 3), ("lvs", 4)):
        value = copy.deepcopy(configurations[index])
        value.update(physical_runtime=copy.deepcopy(physical), working_directory=str(destinations[name]))
        derived[name] = value
    preview = copy.deepcopy(failed_layout)
    preview["runtime_configuration"] = physical
    drc_projection(preview, derived["drc"])
    lvs_projection({"layout_snapshot": preview, "layout_record_sha256": object_hash(preview)}, preview, derived["lvs"])
    return derived


def _final_identity(second_bundle, failed_layout):
    from .postlayout_cleanup import execution_hash
    return {**copy.deepcopy(second_bundle["source_identity"]),
            "failed_second_layout_run_id": failed_layout["id"],
            "failed_second_layout_execution_sha256": execution_hash(failed_layout)}


def _validate_final_bundle(bundle, first_raw, first_bundle, second_raw, second_bundle, second_configurations,
                           store, configurations, project_id, system_id, read_cache=None):
    _checksum(bundle)
    _require(set(bundle) == {"schema", "project_id", "system_id", "revision_id", "base_configuration_sha256",
                            "original_bundle_sha256", "previous_bundle_sha256", "source_identity",
                            "configurations", "actor", "created_at", "record_hash"}
             and bundle.get("schema") == FINAL_SCHEMA and bundle.get("project_id") == project_id
             and bundle.get("system_id") == system_id and bundle.get("actor") == "explicit_GUI_action"
             and type(bundle.get("created_at")) is str
             and bundle.get("revision_id") == first_bundle["revision_id"] == second_bundle["revision_id"]
             and bundle.get("base_configuration_sha256") == _base_hashes(configurations)
             and bundle.get("original_bundle_sha256") == hashlib.sha256(first_raw).hexdigest()
             and bundle.get("previous_bundle_sha256") == hashlib.sha256(second_raw).hexdigest()
             and type(bundle.get("source_identity")) is dict,
             "physical_repair_profile_incompatible", "The third correction must retain both exact ancestor bundles, host runtimes, system and revision; saved bytes were preserved.")
    _, records = _failure(store, first_bundle["source_identity"]["failed_s14_id"], first_bundle["revision_id"], read_cache)
    run = _retry_failure(store, bundle["source_identity"].get("failed_second_layout_run_id"), bundle["revision_id"],
                         records["layout"], second_configurations, final=True, read_cache=read_cache)
    _require(bundle["source_identity"] == _final_identity(second_bundle, run), "physical_repair_profile_incompatible",
             "The original S14 or either correction execution changed; the third correction bundle was preserved.")
    derived = _build_final(run, configurations)
    _require(object_hash(bundle.get("configurations")) == object_hash(derived), "physical_repair_profile_incompatible",
             "The third correction differs from its fixed source-bound builder; saved bytes were preserved.")
    return derived


def _prepare_final(server, failed_layout_id, revision_id):
    """Append the fixed third profile without changing either ancestor bundle."""
    from .workspace_server import _postlayout_profile_directory
    from .physical_repair import PROFILE_NPU2_RETRY
    with server.execution_lock:
        workspace = getattr(server, "workspace", None)
        _require(workspace is not None and workspace.context is not None and not workspace.identity["read_only"],
                 "physical_repair_session_unavailable", "Open the editable original system before preparing the third correction.")
        for name in MANAGERS:
            manager = getattr(server, name, None)
            _require(manager is not None and not getattr(manager, "_storage_error", None)
                     and not (getattr(manager, "_worker", None) and manager._worker.is_alive())
                     and not (hasattr(manager, "is_active") and manager.is_active()),
                     "physical_repair_busy", "Finish active work, resolve cleanup and saved-history errors before preparing the third correction.")
        physical = server.physical_workflow
        with physical._source_locks(), physical.lock:
            physical.observe_design()
            runs = physical._state["runs"]
            _require(runs and runs[-1]["id"] == failed_layout_id and physical._decorate(runs[-1])["freshness"] == "Current"
                     and server.store.envelope()["revision"]["id"] == revision_id,
                     "physical_repair_source_not_current", "Prepare the third correction only from the latest current failed layout and saved revision.")
            identity = workspace.identity
            directory = _postlayout_profile_directory(workspace.registry.root, identity["project_id"], identity["system_id"])
            first_path = _bundle_path(directory)
            second_path = _bundle_path(directory, RETRY_BUNDLE_NAME)
            final_path = _bundle_path(directory, FINAL_BUNDLE_NAME)
            _require(first_path.is_file() and second_path.is_file() and not final_path.exists(),
                     "physical_repair_profile_exists", "Retain both original correction bundles; an existing third bundle cannot be overwritten.")
            first_raw, second_raw = first_path.read_bytes(), second_path.read_bytes()
            first_bundle = strict_loads(first_raw.decode("utf-8"))
            second_bundle = strict_loads(second_raw.decode("utf-8"))
            configurations = workspace.configurations
            first = _validate_bundle(first_bundle, server.store, configurations, identity["project_id"], identity["system_id"])
            second = _validate_retry_bundle(second_bundle, first_raw, first_bundle, first, server.store,
                                            configurations, identity["project_id"], identity["system_id"])
            _require(second["physical"].get("profile", {}).get("profile_version") == PROFILE_NPU2_RETRY
                     and all(object_hash(getattr(server, name + "_workflow").tool_configuration) == object_hash(second[name])
                             for name in ("physical", "drc", "lvs")),
                     "physical_repair_retry_configuration_conflict", "The active physical runtimes must match the saved second correction bundle exactly.")
            source_revision_id = first_bundle["revision_id"]
            _, records = _failure(server.store, first_bundle["source_identity"]["failed_s14_id"], source_revision_id)
            run = _retry_failure(server.store, failed_layout_id, source_revision_id, records["layout"], second, final=True)
            _require(object_hash(run) == object_hash(runs[-1]), "physical_repair_record_changed", "Refresh the latest durable failed layout record.")
            derived = _build_final(run, configurations)
            bundle = {"schema": FINAL_SCHEMA, "project_id": identity["project_id"], "system_id": identity["system_id"],
                      "revision_id": source_revision_id, "base_configuration_sha256": _base_hashes(configurations),
                      "original_bundle_sha256": hashlib.sha256(first_raw).hexdigest(),
                      "previous_bundle_sha256": hashlib.sha256(second_raw).hexdigest(),
                      "source_identity": _final_identity(second_bundle, run), "configurations": derived,
                      "actor": "explicit_GUI_action", "created_at": utc_now()}
            bundle["record_hash"] = object_hash(bundle)
            _require(first_path.read_bytes() == first_raw and second_path.read_bytes() == second_raw,
                     "physical_repair_record_changed", "An ancestor correction bundle changed during preparation.")
            _write(final_path, bundle)
            status = {"configured": True, "bundle_present": True, "error": None, "repair_generation": 3,
                      "source_identity": copy.deepcopy(bundle["source_identity"]),
                      "profile_version": derived["physical"]["profile"]["profile_version"]}
            workspace.context.physical_repair_session = copy.deepcopy(status)
            server.physical_repair_session = copy.deepcopy(status)
            for name in ("physical", "drc", "lvs"):
                getattr(server, name + "_workflow").tool_configuration = copy.deepcopy(derived[name])
        for name in ("physical_workflow", "drc_workflow", "lvs_workflow", "postlayout_workflow"):
            getattr(server, name).observe_design()
        return copy.deepcopy(status)


def prepare_retry(server, failed_layout_id, revision_id):
    """Select only the fixed next generation from the active verified profile."""
    from .physical_repair_generic import is_generic
    if is_generic(getattr(server.physical_workflow, 'tool_configuration', None)):
        from .generic_physical_retry_session import prepare
        return prepare(server, failed_layout_id, revision_id, 'layout')
    from .physical_repair import PROFILE_NPU2, PROFILE_NPU2_RETRY
    _require(type(failed_layout_id) is str and type(revision_id) is str,
             "physical_repair_request_invalid", "Provide only the saved failed layout ID and current revision ID.")
    with server.execution_lock:
        configuration = server.physical_workflow.tool_configuration
        profile = configuration.get("profile") if type(configuration) is dict else None
        version = profile.get("profile_version") if type(profile) is dict else None
        _require(version in (PROFILE_NPU2, PROFILE_NPU2_RETRY), "physical_repair_profile_incompatible",
                 "Only the fixed next correction of the active first or second profile can be prepared.")
        return (_prepare_final if version == PROFILE_NPU2_RETRY else _prepare_second)(server, failed_layout_id, revision_id)

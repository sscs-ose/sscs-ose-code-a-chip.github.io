"""S13 history bound to both the exact adopted S12 DRC and S11 layout.

This manager never modifies RTL, regenerates a layout or calls a model.
Software doubles are explicitly marked and cannot become actual evidence.
"""
from __future__ import annotations

import copy
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import threading

from .domain import DomainError
from .envelope_cache import memoized_envelope
from .observation import ObservedState, persist_observation, require_durable_write
from .execution_submissions import PROTOCOL_VERSION, submission_view, validate_submissions
from .presentation_revision import same_source_design, same_revision_design
from .global_generation import require
from .drc_workflow import (EARLIER as DRC_EARLIER, validate_drc_proof,
                           validate_source_snapshot as validate_drc_source_snapshot)
from .store import new_id, strict_loads, utc_now, validate_policy_history, validate_policy_review, _replace_with_windows_retry
from .store import _io_path
from .review_actor import REVIEW_ACTORS, manual_review_fields
from .verification import object_hash

STAGE = "lvs"
ACTIVE = {"Queued", "Running"}
EARLIER = (*DRC_EARLIER, "drc")
CLEANUP_BLOCKED = "A previous LVS run has unresolved process cleanup. New execution is blocked until its termination is verified."
JSON_ARTIFACTS = {"drc-record", "layout-record", "source-identity", "runtime-configuration", "artifact-manifest"}
FILE_IDS = {"input-gds", "input-def", "input-netlist", "input-powered-netlist", "config", "initial-state",
            "final-state", "metrics", "tool-versions", "lvs-summary", "extracted-spice", "lvs-report", "lvs-json",
            "extraction-feedback", "extraction-markers", "lvs-script"}
REQUIRED_FILES = set(FILE_IDS)
# The new recipe's adapter independently requires its recognition proof.
# Keep the historical v1/v2 mandatory set unchanged while allowing its fixed-ID
# evidence download through the same guarded artifact path.
FILE_IDS.update({"extraction-model-proof", "extraction-raw-spice", "extraction-models", "extraction-deck"})
FILE_IDS.update({"extraction-inventory-pre-gds", "extraction-inventory-post-gds", "extraction-inventory-post-annotation"})
LIMITS = ["S13 extracts the exact S12-adopted S11 GDS and compares it with its bound powered mapped circuit.",
          "The powered circuit is newly observed at S13 from the unchanged S11 final-state pointer, not a previously retained S11 artifact.",
          "LVS does not establish dynamic SDF correctness, functional equivalence for every job or fabrication readiness."]


def _raw_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _artifact_path(result, entry):
    require(type(entry) is dict and entry.get("id") in FILE_IDS and type(entry.get("relative_path")) is str
            and type(entry.get("sha256")) is str and re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
            and type(entry.get("bytes")) is int and entry["bytes"] >= (0 if entry["id"] == "extraction-feedback" else 1) and type(entry.get("content_type")) is str
            and re.fullmatch(r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+(?:; charset=utf-8)?", entry["content_type"]),
            "lvs_artifact_invalid", "LVS artifacts require fixed IDs, raw hashes and media types; only the extraction feedback may be empty.")
    relative = PurePosixPath(entry["relative_path"])
    require(not relative.is_absolute() and relative.parts and not any(p in (".", "..") for p in relative.parts)
            and "\\" not in entry["relative_path"] and ":" not in entry["relative_path"]
            and not any(ord(c) < 32 for c in entry["relative_path"])
            and type(result.get("artifacts_directory")) is str and Path(result["artifacts_directory"]).is_absolute(),
            "lvs_artifact_path_invalid", "LVS files must stay below their recorded absolute result directory.")
    root = Path(result["artifacts_directory"]).resolve(); path = (root / Path(*relative.parts)).resolve()
    require(path.is_relative_to(root) and path != root and path.is_file(), "lvs_artifact_missing", "The original LVS file is missing or outside its directory.")
    return path


def validate_artifact_manifest(result, passed=False):
    artifacts = result.get("artifacts", [])
    require(type(artifacts) is list, "lvs_artifact_invalid", "LVS artifacts must be a fixed-ID manifest.")
    ids = set(); paths = set()
    for entry in artifacts:
        path = _artifact_path(result, entry)
        require(entry["id"] not in ids and path not in paths and path.stat().st_size == entry["bytes"] and _raw_hash(path) == entry["sha256"],
                "lvs_artifact_hash_conflict", "Saved LVS bytes must match their unique raw manifest.")
        ids.add(entry["id"]); paths.add(path)
    require(not passed or REQUIRED_FILES <= ids, "lvs_artifact_missing", "Passed LVS requires all fixed reports, inputs, summary and tool versions.")


def validate_lvs_proof(run, validator):
    validate_source_snapshot(run)
    result = run["checks"]
    require(type(result) is dict and result.get("cleanup_unresolved") is not True, "lvs_cleanup_unresolved", CLEANUP_BLOCKED)
    require(result.get("validation_status") == "Passed" and result.get("executed") is True
            and type(result.get("exit_code")) is int and result["exit_code"] == 0
            and result.get("layout_run_id") == run["layout_run_id"] and result.get("layout_record_sha256") == run["layout_record_sha256"]
            and result.get("drc_run_id") == run["drc_run_id"] and result.get("drc_record_sha256") == run["drc_record_sha256"]
            and result.get("input_gds_sha256") == run["input_gds_sha256"] and result.get("configuration_sha256") == run["configuration_sha256"]
            and result.get("input_netlist_sha256") == run["input_netlist_sha256"]
            and result.get("input_powered_netlist_sha256") == run["input_powered_netlist_sha256"]
            and type(result.get("commands")) is list and result["commands"]
            and all(type(c) is dict and c.get("executed") is True and c.get("status") == "Completed"
                    and type(c.get("exit_code")) is int and c["exit_code"] == 0 for c in result["commands"])
            and type(result.get("metrics")) is dict and type(result.get("diagnostics")) is list
            and all(result.get("checks", {}).get(name, {}).get("validation_status") == "Passed" for name in ("source_identity", "configuration", "extraction", "lvs"))
            and result["checks"]["extraction"].get("executed") is True and result["checks"]["extraction"].get("completed") is True
            and result["checks"]["lvs"].get("executed") is True and result["checks"]["lvs"].get("completed") is True,
            "lvs_proof_conflict", "Passed LVS requires executed extraction/comparison and unchanged S11, S12, mapped circuit and configuration.")
    require(run["evidence_kind"] == "software_qa_fixture" and result.get("software_qa_fixture") is True
            or run["evidence_kind"] == "trusted_fixed_lvs_execution" and result.get("origin") == "trusted_fixed_lvs_adapter" and result.get("software_qa_fixture") is not True,
            "lvs_proof_conflict", "Actual LVS and explicit software doubles must retain their distinct origins.")
    validate_artifact_manifest(result, True)
    require(validator(result, run["drc_snapshot"], run["layout_snapshot"], run["runtime_configuration"]) is None,
            "lvs_proof_conflict", "The fixed LVS validator must explicitly finish without a mismatch.")


def _immutable_source(record):
    return {k: v for k, v in record.items() if k not in ("record_hash", "review_status", "acceptance_epoch", "diagnostics")}


def validate_source_snapshot(run):
    """Pure frozen dual-source/configuration bindings, also usable in archives."""
    layout = run["layout_snapshot"]; drc = run["drc_snapshot"]; identity = run["source_identity"]
    adoption = run["layout_adoption"]; drc_adoption = run["drc_adoption"]; inputs = run["source_inputs"]
    validate_drc_source_snapshot(drc)
    require(type(inputs) is dict and set(inputs) == {"gds", "def", "netlist", "powered_netlist"}
            and all(type(e) is dict and type(e.get("sha256")) is str and re.fullmatch(r"[0-9a-f]{64}", e["sha256"])
                    and type(e.get("bytes")) is int and e["bytes"] > 0 for e in inputs.values())
            and all(inputs[k].get("id") == k and any(object_hash(inputs[k]) == object_hash(e) for e in layout["checks"]["artifacts"] if e["id"] == k)
                    for k in ("gds", "def", "netlist"))
            and inputs["powered_netlist"].get("id") == "powered-netlist"
            and inputs["powered_netlist"].get("origin") == "original_S11_state_pointer_observed_at_S13_start"
            and type(inputs["powered_netlist"].get("binding")) is dict
            and object_hash(identity.get("source_inputs")) == object_hash(inputs)
            and inputs["gds"]["sha256"] == run["input_gds_sha256"] == drc["input_gds_sha256"]
            and inputs["netlist"]["sha256"] == run["input_netlist_sha256"]
            and inputs["powered_netlist"]["sha256"] == run["input_powered_netlist_sha256"],
            "lvs_source_conflict", "LVS inputs must retain exact adopted GDS/DEF/netlist and the explicit newly observed powered-circuit binding.")
    require(object_hash(layout) == run["layout_record_sha256"]
            and layout.get("record_hash") == object_hash({k: v for k, v in layout.items() if k != "record_hash"})
            and layout["id"] == run["layout_run_id"] and layout["revision_id"] == run["revision_id"]
            and layout["execution_status"] == "Completed" and layout["validation_status"] == "Passed" and layout["review_status"] == "Accepted"
            and object_hash(drc) == run["drc_record_sha256"]
            and drc.get("record_hash") == object_hash({k: v for k, v in drc.items() if k != "record_hash"})
            and drc["id"] == run["drc_run_id"] and drc["revision_id"] == run["revision_id"]
            and drc["execution_status"] == "Completed" and drc["validation_status"] == "Passed" and drc["review_status"] == "Accepted"
            and drc["layout_run_id"] == layout["id"] and drc["layout_record_sha256"] == run["layout_record_sha256"]
            and object_hash(drc["layout_snapshot"]) == object_hash(layout)
            and object_hash(run["runtime_configuration"]) == run["configuration_sha256"] and run["source_key"] == object_hash(identity)
            and identity.get("revision_id") == run["revision_id"] and identity.get("layout_run_id") == run["layout_run_id"]
            and identity.get("layout_record_sha256") == run["layout_record_sha256"] and identity.get("physical_source_key") == layout["source_key"]
            and type(identity.get("physical_source_epoch")) is int and identity["physical_source_epoch"] == layout["source_epoch_at_start"] == layout["acceptance_epoch"]
            and identity.get("configuration_sha256") == run["configuration_sha256"]
            and object_hash(identity.get("layout_adoption")) == object_hash(adoption) and adoption.get("run_id") == layout["id"] and adoption.get("decision") == "accepted"
            and adoption.get("source_key") == layout["source_key"] and type(adoption.get("acceptance_epoch")) is int and adoption["acceptance_epoch"] == layout["acceptance_epoch"]
            and identity.get("drc_run_id") == run["drc_run_id"] and identity.get("drc_record_sha256") == run["drc_record_sha256"]
            and identity.get("drc_source_key") == drc["source_key"] and type(identity.get("drc_source_epoch")) is int
            and identity["drc_source_epoch"] == drc["source_epoch_at_start"] == drc["acceptance_epoch"]
            and object_hash(identity.get("drc_adoption")) == object_hash(drc_adoption) and drc_adoption.get("run_id") == drc["id"]
            and drc_adoption.get("decision") == "accepted" and drc_adoption.get("source_key") == drc["source_key"]
            and type(drc_adoption.get("acceptance_epoch")) is int and drc_adoption["acceptance_epoch"] == drc["acceptance_epoch"],
            "lvs_source_conflict", "Frozen LVS identity must bind both exact adopted S11/S12 records, adoptions and source epochs.")


def _source_inputs(layout):
    from .lvs_tools import source_inputs
    return source_inputs(layout)


class LvsWorkflowManager(ObservedState):
    def __init__(self, store, drc_workflow, tool_configuration=None, lvs_runner=None, lvs_validator=None):
        require((lvs_runner is None) == (lvs_validator is None), "lvs_adapter_invalid", "An injected runner needs its explicit proof validator.")
        self.store, self.drc_workflow = store, drc_workflow
        self.physical_workflow = drc_workflow.physical_workflow
        self.tool_configuration = copy.deepcopy(tool_configuration)
        self._injected = lvs_runner is not None; self._runner, self._validator = lvs_runner, lvs_validator
        self.path = store.state_path.parent / "lvs_workflow.json"; self.lock = threading.RLock()
        self._worker = None; self._cancel = threading.Event(); self._closed = False; self._storage_error = None
        self._state = {"lvs_workflow_store_version": "0.1", "runs": [], "reviews": [], "source_key": None, "source_epoch": 0, "source_transitions": []}
        if _io_path(self.path).exists():
            try: self._state = strict_loads(_io_path(self.path).read_text(encoding="utf-8")); self._validate_saved()
            except (DomainError, OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                raise DomainError("invalid_lvs_workflow_store", "LVS history is inconsistent; its original bytes are preserved.", 500) from error
        self._committed = copy.deepcopy(self._state)
        interrupted = False
        for run in self._state["runs"]:
            if run["execution_status"] in ACTIVE:
                run.update(execution_status="Interrupted", validation_status="Not Checked", finished_at=utc_now(),
                    error={"code": "service_restarted", "message": "Interrupted LVS retained; no tool was resent. Process termination requires verification."})
                run["checks"]["cleanup_unresolved"] = True; interrupted = True
        if interrupted: self._persist()

    def _adapter(self):
        if self._runner is None:
            from .lvs_tools import run_lvs, validate_lvs_result
            return run_lvs, validate_lvs_result
        return self._runner, self._validator

    def _capability(self):
        if self._injected:
            return {"available": type(self.tool_configuration) is dict, "reason": "Explicit software QA adapter; no actual EDA evidence."}
        from .lvs_tools import lvs_capability
        return lvs_capability(self.tool_configuration)

    @contextmanager
    def _source_locks(self):
        with self.drc_workflow._source_locks():
            with self.drc_workflow.lock: yield

    def _source_state(self):
        physical = self.physical_workflow; drc_manager = self.drc_workflow
        with self._source_locks():
            current = self.store.envelope()
            drc_manager.observe_design()
            try:
                require(physical._state["runs"] and drc_manager._state["runs"], "lvs_sources_not_adopted", "Adopt the latest current S11 layout and S12 DRC before LVS.")
                layout = physical._state["runs"][-1]; drc = drc_manager._state["runs"][-1]
                require(not physical.is_active() and not drc_manager.is_active()
                        and all(all(decorated[k] == v for k, v in (("execution_status", "Completed"), ("validation_status", "Passed"),
                             ("review_status", "Accepted"), ("freshness", "Current")))
                                for decorated in (physical._decorate(layout), drc_manager._decorate(drc))),
                        "lvs_sources_not_adopted", "The latest S11 and S12 must remain Completed, Passed, Accepted and Current with resolved cleanup.")
                require(self._injected or layout.get("evidence_kind") in ("trusted_fixed_tool_execution", "trusted_saved_tool_revalidation")
                        and drc.get("evidence_kind") == "trusted_fixed_drc_execution",
                        "lvs_fixture_rejected", "Actual LVS requires actual trusted S11 and S12 evidence.")
                require(layout["revision_id"] == drc["revision_id"]
                        and drc["layout_run_id"] == layout["id"] and drc["layout_record_sha256"] == object_hash(layout)
                        and object_hash(drc["layout_snapshot"]) == object_hash(layout),
                        "lvs_source_conflict", "S12 must refer to this exact unchanged adopted S11 record and original GUI revision.")
                same_source_design(self.store, layout["revision_id"], current)
                adoptions = [r for r in physical._state["reviews"] if r["run_id"] == layout["id"]]
                drc_adoptions = [r for r in drc_manager._state["reviews"] if r["run_id"] == drc["id"]]
                require(adoptions and adoptions[-1]["decision"] == "accepted" and drc_adoptions and drc_adoptions[-1]["decision"] == "accepted",
                        "lvs_adoption_conflict", "Retain the authoritative current S11 and S12 adoptions.")
                # Includes the explicit newly observed original-S11 state pointer.
                # The fixed helper verifies bytes/structure without writing S11/S12.
                inputs = _source_inputs(layout)
                identity = {"revision_id": layout["revision_id"], "layout_run_id": layout["id"], "layout_record_sha256": object_hash(layout),
                    "physical_source_key": physical._state["source_key"], "physical_source_epoch": physical._state["source_epoch"],
                    "layout_adoption": copy.deepcopy(adoptions[-1]), "source_inputs": copy.deepcopy(inputs),
                    "drc_run_id": drc["id"], "drc_record_sha256": object_hash(drc), "drc_source_key": drc_manager._state["source_key"],
                    "drc_source_epoch": drc_manager._state["source_epoch"], "drc_adoption": copy.deepcopy(drc_adoptions[-1]),
                    "configuration_sha256": object_hash(self.tool_configuration)}
                return object_hash(identity), {"identity": identity, "layout": copy.deepcopy(layout), "layout_adoption": copy.deepcopy(adoptions[-1]),
                    "drc": copy.deepcopy(drc), "drc_adoption": copy.deepcopy(drc_adoptions[-1]), "inputs": copy.deepcopy(inputs)}, None
            except DomainError as error:
                key = object_hash({"revision_id": current["revision"]["id"], "physical_source_key": physical._state["source_key"],
                    "physical_source_epoch": physical._state["source_epoch"], "physical_runs": [[r["id"], r["record_hash"]] for r in physical._state["runs"]],
                    "physical_reviews": physical._state["reviews"], "drc_source_key": drc_manager._state["source_key"], "drc_source_epoch": drc_manager._state["source_epoch"],
                    "drc_runs": [[r["id"], r["record_hash"]] for r in drc_manager._state["runs"]], "drc_reviews": drc_manager._state["reviews"],
                    "configuration_sha256": object_hash(self.tool_configuration), "blocked": error.code})
                return key, None, {"code": error.code, "message": error.message}

    def observe_design(self):
        key, source, error = self._source_state()
        with self.lock:
            if key != self._state["source_key"]:
                self._state["source_key"] = key; self._state["source_epoch"] += 1
                self._state["source_transitions"].append({"epoch": self._state["source_epoch"], "source_key": key, "created_at": utc_now()}); persist_observation(self)
        return key, source, error

    def _run(self, identifier):
        run = next((r for r in self._state["runs"] if r["id"] == identifier), None)
        require(run is not None, "lvs_run_not_found", "LVS execution does not exist.", 404)
        return run

    def _decorate(self, run):
        value = copy.deepcopy(run); current = run["source_key"] == self._state["source_key"] and run["source_epoch_at_start"] == self._state["source_epoch"]
        value["freshness"] = "Current" if current else "Stale"
        if value["review_status"] == "Accepted" and (not current or run.get("acceptance_epoch") != self._state["source_epoch"]): value["review_status"] = "Awaiting Review"
        value["artifacts"] = [{**entry, "url": "/api/artifacts/lvs-workflow/" + run["id"] + "/" + entry["id"]} for entry in run["checks"].get("artifacts", [])]
        return value

    @memoized_envelope
    def envelope(self):
        _, source, error = self.observe_design(); capability = self._capability()
        with self.lock:
            runs = [self._decorate(r) for r in self._state["runs"]]; latest = runs[-1] if runs else None
            unresolved = self._cleanup_unresolved(); tool_ready = capability.get("available") is True
            return {"lvs_workflow": {"implemented": True, "stage_id": STAGE, "runs": runs, "reviews": copy.deepcopy(self._state["reviews"]),
                "execution_submissions": submission_view(self), "submission_protocol_version": PROTOCOL_VERSION,
                "latest_run_id": latest["id"] if latest else None, "accepted_run_id": latest["id"] if latest and latest["review_status"] == "Accepted" and latest["freshness"] == "Current" else None,
                "ready": source is not None and tool_ready and not unresolved, "blocked_reason": CLEANUP_BLOCKED if unresolved else error["message"] if error else None if tool_ready else capability.get("reason"),
                "tool_ready": tool_ready, "tool_blocked_reason": None if tool_ready else capability.get("reason"),
                "configuration_sha256": object_hash(self.tool_configuration), "runtime_configuration": copy.deepcopy(self.tool_configuration),
                "layout_run_id": source["layout"]["id"] if source else None, "drc_run_id": source["drc"]["id"] if source else None,
                "source_inputs": copy.deepcopy(source["inputs"]) if source else None,
                "input_gds_sha256": source["inputs"]["gds"]["sha256"] if source else None,
                "input_netlist_sha256": source["inputs"]["netlist"]["sha256"] if source else None,
                "input_powered_netlist_sha256": source["inputs"]["powered_netlist"]["sha256"] if source else None,
                "storage_error": copy.deepcopy(self._storage_error), "limits": list(LIMITS)}}

    def run(self, identifier):
        self.observe_design()
        with self.lock: return self._decorate(self._run(identifier))

    def _cleanup_unresolved(self): return any(r["checks"].get("cleanup_unresolved") is True for r in self._state["runs"])

    def is_active(self):
        with self.lock: return self._cleanup_unresolved() or any(r["execution_status"] in ACTIVE for r in self._state["runs"])

    def _validate_sources(self, drc, layout):
        self.drc_workflow._validate_layout(layout)
        validate_drc_source_snapshot(drc)
        validate_drc_proof(drc, self.drc_workflow._adapter()[1])

    def start(self, stage_id, layout_run_id, drc_run_id, revision_id=None, *, _submission=None):
        require(stage_id == STAGE and type(layout_run_id) is str and type(drc_run_id) is str and (revision_id is None or type(revision_id) is str),
                "lvs_request_invalid", "S13 requires the exact saved adopted S11 and S12 IDs.")
        capability = self._capability()
        require(capability.get("available") is True, "lvs_runtime_unavailable", capability.get("reason") or "Configure the pinned LVS runtime.")
        with self._source_locks():
            key, source, error = self.observe_design()
            require(source is not None, "lvs_sources_not_current", error["message"] if error else "Adopt current S11 and S12 first.")
            layout = source["layout"]; drc = source["drc"]
            require(layout_run_id == layout["id"] and drc_run_id == drc["id"] and (revision_id is None or revision_id == self.store.envelope()["revision"]["id"]),
                    "lvs_source_conflict", "Continue from the exact latest adopted layout, DRC and GUI revision.")
            physical = self.physical_workflow
            require(not any(r["execution_status"] in ACTIVE for manager, field in
                    ((physical.global_generation, "jobs"), (physical.global_generation.generation, "jobs"),
                     (physical.global_generation.workflow, "runs"), (physical.global_workflow, "runs")) for r in manager._state[field]),
                    "lvs_peer_busy", "Wait for model or earlier tool execution before LVS.")
            self._validate_sources(drc, layout)
            with self.lock:
                require(not self._cleanup_unresolved(), "lvs_cleanup_unresolved", CLEANUP_BLOCKED)
                require(not self._closed and not self.is_active() and not (self._worker and self._worker.is_alive()), "lvs_busy", "Only one LVS execution may run at a time.")
                run = {"id": new_id("lvs-workflow"), "stage_id": STAGE, "revision_id": layout["revision_id"], "layout_run_id": layout["id"],
                    "layout_snapshot": layout, "layout_record_sha256": object_hash(layout), "layout_adoption": source["layout_adoption"],
                    "drc_run_id": drc["id"], "drc_snapshot": drc, "drc_record_sha256": object_hash(drc), "drc_adoption": source["drc_adoption"],
                    "source_inputs": source["inputs"], "input_gds_sha256": source["inputs"]["gds"]["sha256"],
                    "input_netlist_sha256": source["inputs"]["netlist"]["sha256"], "input_powered_netlist_sha256": source["inputs"]["powered_netlist"]["sha256"],
                    "runtime_configuration": copy.deepcopy(self.tool_configuration), "configuration_sha256": object_hash(self.tool_configuration),
                    "source_identity": source["identity"], "source_key": key, "source_epoch_at_start": self._state["source_epoch"],
                    "execution_status": "Queued", "validation_status": "Not Checked", "review_status": "Awaiting Review", "checks": {}, "diagnostics": [],
                    "created_at": utc_now(), "finished_at": None, "error": None, "evidence_kind": "software_qa_fixture" if self._injected else "trusted_fixed_lvs_execution", "limits": list(LIMITS)}
                validate_source_snapshot(run)
                if _submission is not None:
                    run["submission_id"] = _submission.submission_id
                    _submission.bind(run["id"])
                self._state["runs"].append(run); self._persist(); self._cancel = threading.Event()
                self._worker = threading.Thread(target=self._execute, args=(run["id"], self._cancel), daemon=True, name="HuLLCirq-LVS"); self._worker.start()
        return self.envelope()

    def _execute(self, identifier, cancel):
        try:
            with self.lock:
                run = self._run(identifier); run["execution_status"] = "Running"; self._persist(); frozen = copy.deepcopy(run)
            result = self._adapter()[0](frozen["drc_snapshot"], frozen["layout_snapshot"], frozen["runtime_configuration"], cancel_event=cancel)
            require(type(result) is dict and result.get("validation_status") in ("Passed", "Failed", "Unsupported", "Not Checked") and type(result.get("diagnostics")) is list,
                    "lvs_result_invalid", "The fixed LVS adapter must return structured evidence.")
            with self.lock:
                run = self._run(identifier); run.update(checks=copy.deepcopy(result), diagnostics=copy.deepcopy(result["diagnostics"])); self._persist()
            require(self._injected or result.get("software_qa_fixture") is not True, "lvs_fixture_rejected", "Software doubles cannot become actual LVS evidence.")
            require(result.get("cleanup_unresolved") is not True, "lvs_cleanup_unresolved", CLEANUP_BLOCKED)
            if result["validation_status"] == "Passed": validate_lvs_proof({**frozen, "checks": result}, self._adapter()[1])
            else: validate_artifact_manifest(result)
            status = result.get("status") if result.get("status") in ("Completed", "Failed", "Cancelled") else "Completed"
            with self.lock:
                run = self._run(identifier); run.update(execution_status="Cancelled" if cancel.is_set() else status,
                    validation_status="Not Checked" if cancel.is_set() else result["validation_status"], finished_at=utc_now()); self._persist()
            self.observe_design(); policy = self.store.review_policy()
            if not cancel.is_set() and status == "Completed" and result["validation_status"] == "Passed" and policy["mode"] == "accept_on_pass" and policy["user_authorized"] is True:
                try: self._review(identifier, "accepted", "Adopted under the user's configured Passed policy.", None, "automation_policy", self.store.policy_provenance(policy["id"]))
                except DomainError as error:
                    with self.lock:
                        self._run(identifier)["diagnostics"].append({"code": "automatic_adoption_blocked", "severity": "info", "message": error.message}); self._persist()
        except Exception as error:
            with self.lock:
                run = self._run(identifier); run.update(execution_status="Cancelled" if cancel.is_set() else "Failed", validation_status="Not Checked", finished_at=utc_now(),
                    error={"code": getattr(error, "code", "lvs_workflow_error"), "message": getattr(error, "message", "LVS execution or durable evidence recording failed.")})
                try: self._persist()
                except (OSError, ValueError, TypeError): pass

    def _review(self, identifier, decision, note, target_stage, actor, provenance=None):
        require(decision in ("accepted", "changes_requested", "return_to_stage") and type(note) is str and (decision == "accepted" or note.strip()), "lvs_review_invalid", "Provide a valid decision and correction/return reason.")
        require(target_stage in EARLIER if decision == "return_to_stage" else target_stage is None, "invalid_target_stage", "Return only to implemented S01–S12.")
        with self._source_locks():
            self.observe_design()
            with self.lock:
                run = self._run(identifier); decorated = self._decorate(run)
                require(run["execution_status"] not in ACTIVE and self._state["runs"][-1]["id"] == identifier, "lvs_superseded", "Review the latest completed LVS result.")
                if decision == "accepted":
                    require(not self._cleanup_unresolved(), "lvs_cleanup_unresolved", CLEANUP_BLOCKED)
                    require(decorated["freshness"] == "Current" and run["execution_status"] == "Completed" and run["validation_status"] == "Passed", "lvs_not_passed", "Only exact current executed Passed LVS may be adopted.")
                    self._validate_sources(run["drc_snapshot"], run["layout_snapshot"]); validate_lvs_proof(run, self._adapter()[1])
                    if actor == "automation_policy":
                        policy = self.store.review_policy()
                        require(policy["mode"] == "accept_on_pass" and policy["user_authorized"] is True and provenance is not None and provenance.get("policy_id") == policy["id"], "review_policy_changed", "The automatic adoption policy changed while LVS ran.")
                    run.update(review_status="Accepted", acceptance_epoch=self._state["source_epoch"])
                else: run["review_status"] = "Changes Requested"
                review = {"id": new_id("lvs-review"), "run_id": identifier, "decision": decision, "note": note, "target_stage": target_stage, "actor": actor,
                    "source_key": run["source_key"], "acceptance_epoch": run.get("acceptance_epoch"), "reviewed_revision_id": self.store.envelope()["revision"]["id"], "created_at": utc_now()}
                if provenance: review["provenance"] = copy.deepcopy(provenance)
                self._state["reviews"].append(review); self._persist()
        return self.envelope()

    def review(self, identifier, decision, note, target_stage=None, *, operator=None):
        fields = manual_review_fields(operator)
        return self._review(identifier, decision, note, target_stage, fields["actor"], fields["provenance"])

    def cancel(self, identifier):
        with self.lock:
            require(self._run(identifier)["execution_status"] in ACTIVE, "lvs_not_active", "Only active LVS can be cancelled."); self._cancel.set()
        return self.envelope()

    def artifact_file(self, identifier, artifact_id):
        with self.lock: result = copy.deepcopy(self._run(identifier)["checks"])
        entry = next((e for e in result.get("artifacts", []) if e["id"] == artifact_id), None)
        require(entry is not None and artifact_id in FILE_IDS, "lvs_artifact_not_found", "Only retained fixed-ID LVS files are available.", 404)
        path = _artifact_path(result, entry)
        require(path.stat().st_size == entry["bytes"] and _raw_hash(path) == entry["sha256"], "lvs_artifact_hash_conflict", "The original saved LVS bytes changed.")
        return {**entry, "path": path}

    def artifact_bytes(self, identifier, artifact_id):
        entry = self.artifact_file(identifier, artifact_id); payload = entry["path"].read_bytes()
        require(len(payload) == entry["bytes"] and hashlib.sha256(payload).hexdigest() == entry["sha256"], "lvs_artifact_hash_conflict", "LVS bytes changed during download.")
        return payload, entry["content_type"]

    def artifact(self, identifier, field):
        with self.lock: run = copy.deepcopy(self._run(identifier))
        fields = {"drc-record": "drc_snapshot", "layout-record": "layout_snapshot", "source-identity": "source_identity", "runtime-configuration": "runtime_configuration"}
        if field in fields: return run[fields[field]]
        if field == "artifact-manifest": return copy.deepcopy(run["checks"].get("artifacts", []))
        raise DomainError("lvs_artifact_not_found", "Only fixed LVS documents and raw files are available.", 404)

    def _validate_saved(self):
        state = self._state
        require(type(state) is dict and state.get("lvs_workflow_store_version") == "0.1" and type(state.get("runs")) is list and type(state.get("reviews")) is list
                and type(state.get("source_epoch")) is int and state["source_epoch"] >= 0 and type(state.get("source_transitions")) is list, "lvs_history_invalid", "Invalid LVS history containers.")
        transitions = state["source_transitions"]
        require([t["epoch"] for t in transitions] == list(range(1, state["source_epoch"] + 1)) and (transitions[-1]["source_key"] if transitions else None) == state["source_key"]
                and all(type(t["epoch"]) is int and type(t["source_key"]) is str for t in transitions), "lvs_history_invalid", "LVS source epochs are inconsistent.")
        policies = validate_policy_history(self.store.envelope()); ids = set()
        for run in state["runs"]:
            require(type(run) is dict and all(type(run.get(k)) is str for k in ("id", "stage_id", "revision_id", "layout_run_id", "layout_record_sha256",
                    "drc_run_id", "drc_record_sha256", "input_gds_sha256", "input_netlist_sha256", "input_powered_netlist_sha256", "configuration_sha256", "source_key", "created_at"))
                    and all(type(run.get(k)) is dict for k in ("layout_snapshot", "layout_adoption", "drc_snapshot", "drc_adoption", "source_inputs", "runtime_configuration", "source_identity", "checks")) and type(run.get("diagnostics")) is list
                    and run["stage_id"] == STAGE and run["id"] not in ids and type(run.get("source_epoch_at_start")) is int
                    and run["execution_status"] in ACTIVE | {"Completed", "Failed", "Cancelled", "Interrupted"} and run["validation_status"] in ("Not Checked", "Passed", "Failed", "Unsupported")
                    and run["review_status"] in ("Awaiting Review", "Accepted", "Changes Requested") and run.get("record_hash") == object_hash({k: v for k, v in run.items() if k != "record_hash"})
                    and run.get("evidence_kind") == ("software_qa_fixture" if self._injected else "trusted_fixed_lvs_execution"), "lvs_record_invalid", "LVS record types, origin, statuses or checksum differ.")
            layout = run["layout_snapshot"]; current_layout = self.physical_workflow._run(run["layout_run_id"])
            drc = run["drc_snapshot"]; current_drc = self.drc_workflow._run(run["drc_run_id"])
            validate_source_snapshot(run)
            require(object_hash(_immutable_source(layout)) == object_hash(_immutable_source(current_layout))
                    and object_hash(_immutable_source(drc)) == object_hash(_immutable_source(current_drc))
                    and any(object_hash(run["layout_adoption"]) == object_hash(r) for r in self.physical_workflow._state["reviews"])
                    and any(object_hash(run["drc_adoption"]) == object_hash(r) for r in self.drc_workflow._state["reviews"])
                    and any(t["epoch"] == run["source_epoch_at_start"] and t["source_key"] == run["source_key"] for t in transitions),
                    "lvs_source_conflict", "LVS history must retain both exact immutable source records and authoritative adoption records.")
            self.store.snapshot(run["revision_id"]); self._validate_sources(drc, layout)
            if run["validation_status"] == "Passed": validate_lvs_proof(run, self._adapter()[1])
            elif run["checks"].get("artifacts"): validate_artifact_manifest(run["checks"])
            reviews = [r for r in state["reviews"] if r["run_id"] == run["id"]]
            expected = "Awaiting Review" if not reviews else "Accepted" if reviews[-1]["decision"] == "accepted" else "Changes Requested"
            require(run["review_status"] == expected and (expected != "Accepted" or run["execution_status"] == "Completed" and run["validation_status"] == "Passed"
                    and type(run.get("acceptance_epoch")) is int and run["acceptance_epoch"] == reviews[-1]["acceptance_epoch"]), "lvs_review_conflict", "LVS adoption differs from recorded decisions.")
            ids.add(run["id"])
        for review in state["reviews"]:
            require(type(review) is dict and review.get("run_id") in ids and review.get("actor") in REVIEW_ACTORS and review.get("decision") in ("accepted", "changes_requested", "return_to_stage")
                    and type(review.get("note")) is str, "lvs_review_conflict", "Invalid LVS decision record.")
            run = self._run(review["run_id"])
            require(review["source_key"] == run["source_key"] and (review.get("target_stage") in EARLIER if review["decision"] == "return_to_stage" else review.get("target_stage") is None), "lvs_review_conflict", "LVS review source or return destination differs.")
            self.store.snapshot(review["reviewed_revision_id"]); validate_policy_review(review, policies)
            if review["decision"] == "accepted":
                require(type(review.get("acceptance_epoch")) is int and review["acceptance_epoch"] == run["source_epoch_at_start"] and same_revision_design(self.store, review["reviewed_revision_id"], run["revision_id"]), "lvs_review_conflict", "LVS acceptance must bind its original source epoch and semantic GUI revision.")
        validate_submissions(state)

    def _persist(self):
        require_durable_write()
        name = None
        try:
            for run in self._state["runs"]: run["record_hash"] = object_hash({k: v for k, v in run.items() if k != "record_hash"})
            _io_path(self.path.parent).mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(prefix=".lvs-workflow-", suffix=".tmp", dir=_io_path(self.path.parent))
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(self._state, ensure_ascii=False, allow_nan=False, indent=2) + "\n"); handle.flush(); os.fsync(handle.fileno())
            _replace_with_windows_retry(name, _io_path(self.path)); self._committed = copy.deepcopy(self._state); self._storage_error = None
        except (OSError, ValueError, TypeError):
            self._state = copy.deepcopy(self._committed); self._storage_error = {"code": "storage_error", "message": "LVS save failed; last durable state retained."}; raise
        finally:
            if name and _io_path(name).exists(): _io_path(name).unlink()

    def close(self):
        with self.lock:
            self._closed = True
            if self._worker and self._worker.is_alive(): self._cancel.set()
        if self._worker and self._worker.is_alive(): self._worker.join(timeout=3)

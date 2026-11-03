"""S12 history for fixed DRC tools and an exact adopted S11 layout.

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
from .presentation_revision import same_revision_design
from .global_generation import require
from .physical_workflow import EARLIER as PHYSICAL_EARLIER, validate_physical_proof, validate_revalidation_link
from .store import new_id, strict_loads, utc_now, validate_policy_history, validate_policy_review, _replace_with_windows_retry
from .store import _io_path
from .review_actor import REVIEW_ACTORS, manual_review_fields
from .verification import object_hash

STAGE = "drc"
ACTIVE = {"Queued", "Running"}
EARLIER = (*PHYSICAL_EARLIER, "layout")
CLEANUP_BLOCKED = "A previous DRC run has unresolved process cleanup. New execution is blocked until its termination is verified."
JSON_ARTIFACTS = {"layout-record", "source-identity", "runtime-configuration", "artifact-manifest"}
FILE_IDS = {"input-gds", "config", "initial-state", "final-state", "metrics", "tool-versions", "drc-summary", "klayout-violations", "magic-report", "magic-markers", "klayout-report"}
REQUIRED_FILES = set(FILE_IDS)
LIMITS = ["S12 checks the exact adopted S11 GDS with the configured fixed DRC decks.",
          "DRC does not establish LVS, dynamic SDF correctness, formal equivalence or fabrication readiness."]


def _raw_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _artifact_path(result, entry):
    require(type(entry) is dict and entry.get("id") in FILE_IDS and type(entry.get("relative_path")) is str
            and type(entry.get("sha256")) is str and re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
            and type(entry.get("bytes")) is int and entry["bytes"] > 0 and type(entry.get("content_type")) is str
            and re.fullmatch(r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+(?:; charset=utf-8)?", entry["content_type"]),
            "drc_artifact_invalid", "DRC artifacts require fixed IDs, raw hashes, positive lengths and media types.")
    relative = PurePosixPath(entry["relative_path"])
    require(not relative.is_absolute() and relative.parts and not any(p in (".", "..") for p in relative.parts)
            and "\\" not in entry["relative_path"] and ":" not in entry["relative_path"]
            and not any(ord(c) < 32 for c in entry["relative_path"])
            and type(result.get("artifacts_directory")) is str and Path(result["artifacts_directory"]).is_absolute(),
            "drc_artifact_path_invalid", "DRC files must stay below their recorded absolute result directory.")
    root = Path(result["artifacts_directory"]).resolve(); path = (root / Path(*relative.parts)).resolve()
    require(path.is_relative_to(root) and path != root and path.is_file(), "drc_artifact_missing", "The original DRC file is missing or outside its directory.")
    return path


def validate_artifact_manifest(result, passed=False):
    artifacts = result.get("artifacts", [])
    require(type(artifacts) is list, "drc_artifact_invalid", "DRC artifacts must be a fixed-ID manifest.")
    ids = set(); paths = set()
    for entry in artifacts:
        path = _artifact_path(result, entry)
        require(entry["id"] not in ids and path not in paths and path.stat().st_size == entry["bytes"] and _raw_hash(path) == entry["sha256"],
                "drc_artifact_hash_conflict", "Saved DRC bytes must match their unique raw manifest.")
        ids.add(entry["id"]); paths.add(path)
    require(not passed or REQUIRED_FILES <= ids, "drc_artifact_missing", "Passed DRC requires all fixed reports, inputs, summary and tool versions.")


def validate_drc_proof(run, validator):
    result = run["checks"]
    require(type(result) is dict and result.get("cleanup_unresolved") is not True, "drc_cleanup_unresolved", CLEANUP_BLOCKED)
    require(result.get("validation_status") == "Passed" and result.get("executed") is True
            and type(result.get("exit_code")) is int and result["exit_code"] == 0
            and result.get("layout_run_id") == run["layout_run_id"] and result.get("layout_record_sha256") == run["layout_record_sha256"]
            and result.get("input_gds_sha256") == run["input_gds_sha256"] and result.get("configuration_sha256") == run["configuration_sha256"]
            and type(result.get("commands")) is list and result["commands"]
            and all(type(c) is dict and c.get("executed") is True and c.get("status") == "Completed"
                    and type(c.get("exit_code")) is int and c["exit_code"] == 0 for c in result["commands"])
            and type(result.get("metrics")) is dict and type(result.get("diagnostics")) is list
            and all(result.get("checks", {}).get(name, {}).get("validation_status") == "Passed" for name in ("source_identity", "configuration", "drc"))
            and result["checks"]["drc"].get("executed") is True and result["checks"]["drc"].get("completed") is True,
            "drc_proof_conflict", "Passed DRC requires executed fixed tools, unchanged layout/configuration and complete rule checks.")
    require(run["evidence_kind"] == "software_qa_fixture" and result.get("software_qa_fixture") is True
            or run["evidence_kind"] == "trusted_fixed_drc_execution" and result.get("origin") == "trusted_fixed_drc_adapter" and result.get("software_qa_fixture") is not True,
            "drc_proof_conflict", "Actual DRC and explicit software doubles must retain their distinct origins.")
    validate_artifact_manifest(result, True)
    require(validator(result, run["layout_snapshot"], run["runtime_configuration"]) is None,
            "drc_proof_conflict", "The fixed DRC validator must explicitly finish without a mismatch.")


def _immutable_layout(record):
    return {k: v for k, v in record.items() if k not in ("record_hash", "review_status", "acceptance_epoch", "diagnostics")}


def validate_source_snapshot(run):
    """Pure frozen source/configuration bindings, also usable in portable archives."""
    layout = run["layout_snapshot"]; identity = run["source_identity"]; adoption = run["layout_adoption"]
    require(object_hash(layout) == run["layout_record_sha256"]
            and layout.get("record_hash") == object_hash({k: v for k, v in layout.items() if k != "record_hash"})
            and layout["id"] == run["layout_run_id"] and layout["revision_id"] == run["revision_id"]
            and layout["execution_status"] == "Completed" and layout["validation_status"] == "Passed" and layout["review_status"] == "Accepted"
            and object_hash(run["runtime_configuration"]) == run["configuration_sha256"] and run["source_key"] == object_hash(identity)
            and identity.get("revision_id") == run["revision_id"] and identity.get("layout_run_id") == run["layout_run_id"]
            and identity.get("layout_record_sha256") == run["layout_record_sha256"] and identity.get("physical_source_key") == layout["source_key"]
            and type(identity.get("physical_source_epoch")) is int and identity["physical_source_epoch"] == layout["source_epoch_at_start"] == layout["acceptance_epoch"]
            and identity.get("configuration_sha256") == run["configuration_sha256"] and identity.get("input_gds", {}).get("sha256") == run["input_gds_sha256"]
            and identity["input_gds"].get("id") == "gds" and any(object_hash(identity["input_gds"]) == object_hash(e) for e in layout["checks"]["artifacts"] if e["id"] == "gds")
            and object_hash(identity.get("layout_adoption")) == object_hash(adoption) and adoption.get("run_id") == layout["id"] and adoption.get("decision") == "accepted"
            and adoption.get("source_key") == layout["source_key"] and type(adoption.get("acceptance_epoch")) is int and adoption["acceptance_epoch"] == layout["acceptance_epoch"],
            "drc_source_conflict", "Frozen DRC identity must bind the exact adopted S11 record, GDS, configuration and source epoch.")


class DrcWorkflowManager(ObservedState):
    def __init__(self, store, physical_workflow, tool_configuration=None, drc_runner=None, drc_validator=None):
        require((drc_runner is None) == (drc_validator is None), "drc_adapter_invalid", "An injected runner needs its explicit proof validator.")
        self.store, self.physical_workflow = store, physical_workflow
        self.tool_configuration = copy.deepcopy(tool_configuration)
        self._injected = drc_runner is not None; self._runner, self._validator = drc_runner, drc_validator
        self.path = store.state_path.parent / "drc_workflow.json"; self.lock = threading.RLock()
        self._worker = None; self._cancel = threading.Event(); self._closed = False; self._storage_error = None
        self._state = {"drc_workflow_store_version": "0.1", "runs": [], "reviews": [], "source_key": None, "source_epoch": 0, "source_transitions": []}
        if _io_path(self.path).exists():
            try: self._state = strict_loads(_io_path(self.path).read_text(encoding="utf-8")); self._validate_saved()
            except (DomainError, OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                raise DomainError("invalid_drc_workflow_store", "DRC history is inconsistent; its original bytes are preserved.", 500) from error
        self._committed = copy.deepcopy(self._state)
        interrupted = False
        for run in self._state["runs"]:
            if run["execution_status"] in ACTIVE:
                run.update(execution_status="Interrupted", validation_status="Not Checked", finished_at=utc_now(),
                    error={"code": "service_restarted", "message": "Interrupted DRC retained; no tool was resent. Process termination requires verification."})
                run["checks"]["cleanup_unresolved"] = True; interrupted = True
        if interrupted: self._persist()

    def _adapter(self):
        if self._runner is None:
            from .drc_tools import run_drc, validate_drc_result
            return run_drc, validate_drc_result
        return self._runner, self._validator

    def _capability(self):
        if self._injected:
            return {"available": type(self.tool_configuration) is dict, "reason": "Explicit software QA adapter; no actual EDA evidence."}
        from .drc_tools import drc_capability
        return drc_capability(self.tool_configuration)

    @contextmanager
    def _source_locks(self):
        with self.physical_workflow._source_locks():
            with self.physical_workflow.lock: yield

    def _source_state(self):
        physical = self.physical_workflow
        with self._source_locks():
            current = self.store.envelope()
            physical.observe_design()
            try:
                require(physical._state["runs"], "drc_layout_not_adopted", "Adopt the latest current S11 layout before DRC.")
                layout = physical._state["runs"][-1]; decorated = physical._decorate(layout)
                require(not physical.is_active() and all(decorated[k] == v for k, v in
                        (("execution_status", "Completed"), ("validation_status", "Passed"), ("review_status", "Accepted"), ("freshness", "Current"))),
                        "drc_layout_not_adopted", "The latest S11 must remain Completed, Passed, Accepted and Current with resolved cleanup.")
                require(self._injected or layout.get("evidence_kind") in ("trusted_fixed_tool_execution", "trusted_saved_tool_revalidation"),
                        "drc_fixture_rejected", "Actual DRC requires an actual trusted S11 layout.")
                adoptions = [r for r in physical._state["reviews"] if r["run_id"] == layout["id"]]
                require(adoptions and adoptions[-1]["decision"] == "accepted", "drc_layout_adoption_conflict", "Retain the authoritative current S11 adoption.")
                gds = next((e for e in layout["checks"].get("artifacts", []) if e["id"] == "gds"), None)
                require(gds is not None, "drc_gds_missing", "S12 requires the original adopted GDS.")
                # This fixed-file read checks the exact GDS bytes, without copying or writing S11.
                physical.artifact_file(layout["id"], "gds")
                identity = {"revision_id": layout["revision_id"], "layout_run_id": layout["id"], "layout_record_sha256": object_hash(layout),
                    "physical_source_key": physical._state["source_key"], "physical_source_epoch": physical._state["source_epoch"],
                    "layout_adoption": copy.deepcopy(adoptions[-1]), "input_gds": copy.deepcopy(gds), "configuration_sha256": object_hash(self.tool_configuration)}
                return object_hash(identity), {"identity": identity, "layout": copy.deepcopy(layout), "adoption": copy.deepcopy(adoptions[-1]), "gds": copy.deepcopy(gds)}, None
            except DomainError as error:
                key = object_hash({"revision_id": current["revision"]["id"], "physical_source_key": physical._state["source_key"],
                    "physical_source_epoch": physical._state["source_epoch"], "physical_runs": [[r["id"], r["record_hash"]] for r in physical._state["runs"]],
                    "physical_reviews": physical._state["reviews"], "configuration_sha256": object_hash(self.tool_configuration), "blocked": error.code})
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
        require(run is not None, "drc_run_not_found", "DRC execution does not exist.", 404)
        return run

    def _decorate(self, run):
        value = copy.deepcopy(run); current = run["source_key"] == self._state["source_key"] and run["source_epoch_at_start"] == self._state["source_epoch"]
        value["freshness"] = "Current" if current else "Stale"
        if value["review_status"] == "Accepted" and (not current or run.get("acceptance_epoch") != self._state["source_epoch"]): value["review_status"] = "Awaiting Review"
        value["artifacts"] = [{**entry, "url": "/api/artifacts/drc-workflow/" + run["id"] + "/" + entry["id"]} for entry in run["checks"].get("artifacts", [])]
        return value

    @memoized_envelope
    def envelope(self):
        _, source, error = self.observe_design(); capability = self._capability()
        with self.lock:
            runs = [self._decorate(r) for r in self._state["runs"]]; latest = runs[-1] if runs else None
            unresolved = self._cleanup_unresolved(); tool_ready = capability.get("available") is True
            return {"drc_workflow": {"implemented": True, "stage_id": STAGE, "runs": runs, "reviews": copy.deepcopy(self._state["reviews"]),
                "execution_submissions": submission_view(self), "submission_protocol_version": PROTOCOL_VERSION,
                "latest_run_id": latest["id"] if latest else None, "accepted_run_id": latest["id"] if latest and latest["review_status"] == "Accepted" and latest["freshness"] == "Current" else None,
                "ready": source is not None and tool_ready and not unresolved, "blocked_reason": CLEANUP_BLOCKED if unresolved else error["message"] if error else None if tool_ready else capability.get("reason"),
                "tool_ready": tool_ready, "tool_blocked_reason": None if tool_ready else capability.get("reason"),
                "configuration_sha256": object_hash(self.tool_configuration), "runtime_configuration": copy.deepcopy(self.tool_configuration),
                "layout_run_id": source["layout"]["id"] if source else None, "storage_error": copy.deepcopy(self._storage_error), "limits": list(LIMITS)}}

    def run(self, identifier):
        self.observe_design()
        with self.lock: return self._decorate(self._run(identifier))

    def _cleanup_unresolved(self): return any(r["checks"].get("cleanup_unresolved") is True for r in self._state["runs"])

    def is_active(self):
        with self.lock: return self._cleanup_unresolved() or any(r["execution_status"] in ACTIVE for r in self._state["runs"])

    def _validate_layout(self, layout):
        if layout.get("evidence_kind") == "trusted_saved_tool_revalidation":
            validate_revalidation_link(layout, self.physical_workflow._run(layout["prior_run_id"]))
        validate_physical_proof(layout, self.physical_workflow._adapter()[1])

    def start(self, stage_id, layout_run_id, revision_id=None, *, _submission=None):
        require(stage_id == STAGE and type(layout_run_id) is str and (revision_id is None or type(revision_id) is str), "drc_request_invalid", "S12 requires the exact saved adopted S11 ID.")
        capability = self._capability()
        require(capability.get("available") is True, "drc_runtime_unavailable", capability.get("reason") or "Configure the pinned DRC runtime.")
        with self._source_locks():
            key, source, error = self.observe_design()
            require(source is not None, "drc_layout_not_current", error["message"] if error else "Adopt current S11 first.")
            layout = source["layout"]
            require(layout_run_id == layout["id"] and (revision_id is None or revision_id == self.store.envelope()["revision"]["id"]), "drc_source_conflict", "Continue from the exact latest adopted layout and current saved GUI revision.")
            physical = self.physical_workflow
            require(not any(r["execution_status"] in ACTIVE for manager, field in
                    ((physical.global_generation, "jobs"), (physical.global_generation.generation, "jobs"),
                     (physical.global_generation.workflow, "runs"), (physical.global_workflow, "runs")) for r in manager._state[field]),
                    "drc_peer_busy", "Wait for model or earlier tool execution before DRC.")
            self._validate_layout(layout)
            with self.lock:
                require(not self._cleanup_unresolved(), "drc_cleanup_unresolved", CLEANUP_BLOCKED)
                require(not self._closed and not self.is_active() and not (self._worker and self._worker.is_alive()), "drc_busy", "Only one DRC execution may run at a time.")
                run = {"id": new_id("drc-workflow"), "stage_id": STAGE, "revision_id": layout["revision_id"], "layout_run_id": layout["id"],
                    "layout_snapshot": layout, "layout_record_sha256": object_hash(layout), "layout_adoption": source["adoption"], "input_gds_sha256": source["gds"]["sha256"],
                    "runtime_configuration": copy.deepcopy(self.tool_configuration), "configuration_sha256": object_hash(self.tool_configuration),
                    "source_identity": source["identity"], "source_key": key, "source_epoch_at_start": self._state["source_epoch"],
                    "execution_status": "Queued", "validation_status": "Not Checked", "review_status": "Awaiting Review", "checks": {}, "diagnostics": [],
                    "created_at": utc_now(), "finished_at": None, "error": None, "evidence_kind": "software_qa_fixture" if self._injected else "trusted_fixed_drc_execution", "limits": list(LIMITS)}
                if _submission is not None:
                    run["submission_id"] = _submission.submission_id
                    _submission.bind(run["id"])
                self._state["runs"].append(run); self._persist(); self._cancel = threading.Event()
                self._worker = threading.Thread(target=self._execute, args=(run["id"], self._cancel), daemon=True, name="HuLLCirq-DRC"); self._worker.start()
        return self.envelope()

    def _execute(self, identifier, cancel):
        try:
            with self.lock:
                run = self._run(identifier); run["execution_status"] = "Running"; self._persist(); frozen = copy.deepcopy(run)
            result = self._adapter()[0](frozen["layout_snapshot"], frozen["runtime_configuration"], cancel_event=cancel)
            require(type(result) is dict and result.get("validation_status") in ("Passed", "Failed", "Unsupported", "Not Checked") and type(result.get("diagnostics")) is list,
                    "drc_result_invalid", "The fixed DRC adapter must return structured evidence.")
            with self.lock:
                run = self._run(identifier); run.update(checks=copy.deepcopy(result), diagnostics=copy.deepcopy(result["diagnostics"])); self._persist()
            require(self._injected or result.get("software_qa_fixture") is not True, "drc_fixture_rejected", "Software doubles cannot become actual DRC evidence.")
            require(result.get("cleanup_unresolved") is not True, "drc_cleanup_unresolved", CLEANUP_BLOCKED)
            if result["validation_status"] == "Passed": validate_drc_proof({**frozen, "checks": result}, self._adapter()[1])
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
                    error={"code": getattr(error, "code", "drc_workflow_error"), "message": getattr(error, "message", "DRC execution or durable evidence recording failed.")})
                try: self._persist()
                except (OSError, ValueError, TypeError): pass

    def _review(self, identifier, decision, note, target_stage, actor, provenance=None):
        require(decision in ("accepted", "changes_requested", "return_to_stage") and type(note) is str and (decision == "accepted" or note.strip()), "drc_review_invalid", "Provide a valid decision and correction/return reason.")
        require(target_stage in EARLIER if decision == "return_to_stage" else target_stage is None, "invalid_target_stage", "Return only to implemented S01–S11.")
        with self._source_locks():
            self.observe_design()
            with self.lock:
                run = self._run(identifier); decorated = self._decorate(run)
                require(run["execution_status"] not in ACTIVE and self._state["runs"][-1]["id"] == identifier, "drc_superseded", "Review the latest completed DRC result.")
                if decision == "accepted":
                    require(not self._cleanup_unresolved(), "drc_cleanup_unresolved", CLEANUP_BLOCKED)
                    require(decorated["freshness"] == "Current" and run["execution_status"] == "Completed" and run["validation_status"] == "Passed", "drc_not_passed", "Only exact current executed Passed DRC may be adopted.")
                    self._validate_layout(run["layout_snapshot"]); validate_drc_proof(run, self._adapter()[1])
                    if actor == "automation_policy":
                        policy = self.store.review_policy()
                        require(policy["mode"] == "accept_on_pass" and policy["user_authorized"] is True and provenance is not None and provenance.get("policy_id") == policy["id"], "review_policy_changed", "The automatic adoption policy changed while DRC ran.")
                    run.update(review_status="Accepted", acceptance_epoch=self._state["source_epoch"])
                else: run["review_status"] = "Changes Requested"
                review = {"id": new_id("drc-review"), "run_id": identifier, "decision": decision, "note": note, "target_stage": target_stage, "actor": actor,
                    "source_key": run["source_key"], "acceptance_epoch": run.get("acceptance_epoch"), "reviewed_revision_id": self.store.envelope()["revision"]["id"], "created_at": utc_now()}
                if provenance: review["provenance"] = copy.deepcopy(provenance)
                self._state["reviews"].append(review); self._persist()
        return self.envelope()

    def review(self, identifier, decision, note, target_stage=None, *, operator=None):
        fields = manual_review_fields(operator)
        return self._review(identifier, decision, note, target_stage, fields["actor"], fields["provenance"])

    def cancel(self, identifier):
        with self.lock:
            require(self._run(identifier)["execution_status"] in ACTIVE, "drc_not_active", "Only active DRC can be cancelled."); self._cancel.set()
        return self.envelope()

    def artifact_file(self, identifier, artifact_id):
        with self.lock: result = copy.deepcopy(self._run(identifier)["checks"])
        entry = next((e for e in result.get("artifacts", []) if e["id"] == artifact_id), None)
        require(entry is not None and artifact_id in FILE_IDS, "drc_artifact_not_found", "Only retained fixed-ID DRC files are available.", 404)
        path = _artifact_path(result, entry)
        require(path.stat().st_size == entry["bytes"] and _raw_hash(path) == entry["sha256"], "drc_artifact_hash_conflict", "The original saved DRC bytes changed.")
        return {**entry, "path": path}

    def artifact_bytes(self, identifier, artifact_id):
        entry = self.artifact_file(identifier, artifact_id); payload = entry["path"].read_bytes()
        require(len(payload) == entry["bytes"] and hashlib.sha256(payload).hexdigest() == entry["sha256"], "drc_artifact_hash_conflict", "DRC bytes changed during download.")
        return payload, entry["content_type"]

    def artifact(self, identifier, field):
        with self.lock: run = copy.deepcopy(self._run(identifier))
        fields = {"layout-record": "layout_snapshot", "source-identity": "source_identity", "runtime-configuration": "runtime_configuration"}
        if field in fields: return run[fields[field]]
        if field == "artifact-manifest": return copy.deepcopy(run["checks"].get("artifacts", []))
        raise DomainError("drc_artifact_not_found", "Only fixed DRC documents and raw files are available.", 404)

    def _validate_saved(self):
        state = self._state
        require(type(state) is dict and state.get("drc_workflow_store_version") == "0.1" and type(state.get("runs")) is list and type(state.get("reviews")) is list
                and type(state.get("source_epoch")) is int and state["source_epoch"] >= 0 and type(state.get("source_transitions")) is list, "drc_history_invalid", "Invalid DRC history containers.")
        transitions = state["source_transitions"]
        require([t["epoch"] for t in transitions] == list(range(1, state["source_epoch"] + 1)) and (transitions[-1]["source_key"] if transitions else None) == state["source_key"]
                and all(type(t["epoch"]) is int and type(t["source_key"]) is str for t in transitions), "drc_history_invalid", "DRC source epochs are inconsistent.")
        policies = validate_policy_history(self.store.envelope()); ids = set()
        for run in state["runs"]:
            require(type(run) is dict and all(type(run.get(k)) is str for k in ("id", "stage_id", "revision_id", "layout_run_id", "layout_record_sha256", "input_gds_sha256", "configuration_sha256", "source_key", "created_at"))
                    and all(type(run.get(k)) is dict for k in ("layout_snapshot", "layout_adoption", "runtime_configuration", "source_identity", "checks")) and type(run.get("diagnostics")) is list
                    and run["stage_id"] == STAGE and run["id"] not in ids and type(run.get("source_epoch_at_start")) is int
                    and run["execution_status"] in ACTIVE | {"Completed", "Failed", "Cancelled", "Interrupted"} and run["validation_status"] in ("Not Checked", "Passed", "Failed", "Unsupported")
                    and run["review_status"] in ("Awaiting Review", "Accepted", "Changes Requested") and run.get("record_hash") == object_hash({k: v for k, v in run.items() if k != "record_hash"})
                    and run.get("evidence_kind") == ("software_qa_fixture" if self._injected else "trusted_fixed_drc_execution"), "drc_record_invalid", "DRC record types, origin, statuses or checksum differ.")
            layout = run["layout_snapshot"]; current_layout = self.physical_workflow._run(run["layout_run_id"]); identity = run["source_identity"]
            validate_source_snapshot(run)
            require(object_hash(_immutable_layout(layout)) == object_hash(_immutable_layout(current_layout)) and object_hash(layout) == run["layout_record_sha256"]
                    and layout.get("record_hash") == object_hash({k: v for k, v in layout.items() if k != "record_hash"}) and layout["id"] == run["layout_run_id"] and layout["revision_id"] == run["revision_id"]
                    and layout["execution_status"] == "Completed" and layout["validation_status"] == "Passed" and layout["review_status"] == "Accepted"
                    and object_hash(run["runtime_configuration"]) == run["configuration_sha256"] and run["source_key"] == object_hash(identity)
                    and identity.get("revision_id") == run["revision_id"] and identity.get("layout_run_id") == run["layout_run_id"] and identity.get("layout_record_sha256") == run["layout_record_sha256"]
                    and identity.get("physical_source_key") == layout["source_key"] and type(identity.get("physical_source_epoch")) is int
                    and identity["physical_source_epoch"] == layout["source_epoch_at_start"] == layout["acceptance_epoch"]
                    and identity.get("configuration_sha256") == run["configuration_sha256"] and identity.get("input_gds", {}).get("sha256") == run["input_gds_sha256"]
                    and any(object_hash(identity["input_gds"]) == object_hash(e) for e in layout["checks"]["artifacts"] if e["id"] == "gds")
                    and object_hash(identity.get("layout_adoption")) == object_hash(run["layout_adoption"])
                    and run["layout_adoption"].get("run_id") == layout["id"] and run["layout_adoption"].get("decision") == "accepted"
                    and any(object_hash(run["layout_adoption"]) == object_hash(r) for r in self.physical_workflow._state["reviews"])
                    and any(t["epoch"] == run["source_epoch_at_start"] and t["source_key"] == run["source_key"] for t in transitions),
                    "drc_source_conflict", "DRC history must retain its exact S11 layout, adoption, GDS, runtime and source epoch.")
            self.store.snapshot(run["revision_id"]); self._validate_layout(layout)
            if run["validation_status"] == "Passed": validate_drc_proof(run, self._adapter()[1])
            elif run["checks"].get("artifacts"): validate_artifact_manifest(run["checks"])
            reviews = [r for r in state["reviews"] if r["run_id"] == run["id"]]
            expected = "Awaiting Review" if not reviews else "Accepted" if reviews[-1]["decision"] == "accepted" else "Changes Requested"
            require(run["review_status"] == expected and (expected != "Accepted" or run["execution_status"] == "Completed" and run["validation_status"] == "Passed"
                    and type(run.get("acceptance_epoch")) is int and run["acceptance_epoch"] == reviews[-1]["acceptance_epoch"]), "drc_review_conflict", "DRC adoption differs from recorded decisions.")
            ids.add(run["id"])
        for review in state["reviews"]:
            require(type(review) is dict and review.get("run_id") in ids and review.get("actor") in REVIEW_ACTORS and review.get("decision") in ("accepted", "changes_requested", "return_to_stage")
                    and type(review.get("note")) is str, "drc_review_conflict", "Invalid DRC decision record.")
            run = self._run(review["run_id"])
            require(review["source_key"] == run["source_key"] and (review.get("target_stage") in EARLIER if review["decision"] == "return_to_stage" else review.get("target_stage") is None), "drc_review_conflict", "DRC review source or return destination differs.")
            self.store.snapshot(review["reviewed_revision_id"]); validate_policy_review(review, policies)
            if review["decision"] == "accepted":
                require(type(review.get("acceptance_epoch")) is int and review["acceptance_epoch"] == run["source_epoch_at_start"] and same_revision_design(self.store, review["reviewed_revision_id"], run["revision_id"]), "drc_review_conflict", "DRC acceptance must bind its original source epoch and semantic GUI revision.")
        validate_submissions(state)

    def _persist(self):
        require_durable_write()
        name = None
        try:
            for run in self._state["runs"]: run["record_hash"] = object_hash({k: v for k, v in run.items() if k != "record_hash"})
            _io_path(self.path.parent).mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(prefix=".drc-workflow-", suffix=".tmp", dir=_io_path(self.path.parent))
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(self._state, ensure_ascii=False, allow_nan=False, indent=2) + "\n"); handle.flush(); os.fsync(handle.fileno())
            _replace_with_windows_retry(name, _io_path(self.path)); self._committed = copy.deepcopy(self._state); self._storage_error = None
        except (OSError, ValueError, TypeError):
            self._state = copy.deepcopy(self._committed); self._storage_error = {"code": "storage_error", "message": "DRC save failed; last durable state retained."}; raise
        finally:
            if name and _io_path(name).exists(): _io_path(name).unlink()

    def close(self):
        with self.lock:
            self._closed = True
            if self._worker and self._worker.is_alive(): self._cancel.set()
        if self._worker and self._worker.is_alive(): self._worker.join(timeout=3)

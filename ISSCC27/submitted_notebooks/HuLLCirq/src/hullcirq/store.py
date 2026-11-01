"""Atomic local project snapshots, validation runs, and human decisions."""

from __future__ import annotations

import copy
import json
import os
import re
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .domain import DomainError, IMPLEMENTED_STAGES, STAGES, fingerprint, revision_hashes, validate_shape, validate_stage
from .review_actor import manual_review_fields, validate_review_actor


def _io_path(path):
    """Extend local Windows paths only for file I/O, not saved identities."""
    value = os.path.abspath(os.fspath(path))
    if os.name == "nt" and not value.startswith("\\\\?\\"):
        if re.match(r"^[A-Za-z]:\\", value) is None:
            raise DomainError("project_io_path", "Use a local Windows drive for project I/O.")
        value = "\\\\?\\" + value
    return Path(value)

DEFAULT_REVIEW_POLICY = {"id": None, "mode": "manual", "user_authorized": False, "note": "",
                         "created_at": None, "authorization_source": None}


def validate_policy_history(state: dict) -> dict:
    policies = state.get("policy_history", [])
    if type(policies) is not list:
        raise DomainError("invalid_store", "Policy history must be an array.")
    indexed = {}
    for policy in policies:
        if (type(policy) is not dict or set(policy) != set(DEFAULT_REVIEW_POLICY)
                or type(policy["id"]) is not str or not policy["id"] or policy["id"] in indexed
                or policy["mode"] not in ("manual", "accept_on_pass") or type(policy["user_authorized"]) is not bool
                or policy["user_authorized"] != (policy["mode"] == "accept_on_pass")
                or type(policy["note"]) is not str or type(policy["created_at"]) is not str
                or policy["authorization_source"] != "explicit_api_configuration"):
            raise DomainError("invalid_store", "Invalid authorization policy record.")
        indexed[policy["id"]] = policy
    active = state.get("review_policy", DEFAULT_REVIEW_POLICY)
    if active != DEFAULT_REVIEW_POLICY and (type(active) is not dict or active.get("id") not in indexed
                                            or active != policies[-1]):
        raise DomainError("invalid_store", "Active authorization policy does not match its history.")
    return indexed


def validate_policy_review(record: dict, policies: dict) -> None:
    validate_review_actor(record)
    if record.get("actor") != "automation_policy":
        return
    provenance = record.get("provenance")
    if (record.get("actor") != "automation_policy" or record.get("decision") != "accepted"
            or type(provenance) is not dict or provenance.get("authorization") != "user_preapproved"
            or provenance.get("policy_id") not in policies
            or provenance.get("policy") != policies[provenance["policy_id"]]
            or provenance["policy"]["mode"] != "accept_on_pass" or provenance["policy"]["user_authorized"] is not True):
        raise DomainError("invalid_store", "Automatic adoption has no matching user authorization policy.")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def strict_loads(raw: str) -> dict:
    def invalid_constant(value: str) -> None:
        raise DomainError("invalid_json", f"Non-finite JSON number {value} is not allowed.")

    def unique_keys(pairs: list[tuple]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise DomainError("invalid_json", f"Duplicate JSON key: {key}.")
            result[key] = value
        return result

    try:
        return json.loads(raw, parse_constant=invalid_constant, object_pairs_hook=unique_keys)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise DomainError("invalid_json", "Request must contain valid UTF-8 JSON.") from error


def _validate_saved_state(state: dict) -> None:
    """Check persisted evidence before making any of it available to the GUI.

    Source snapshots and recorded stage fingerprints must agree. A malformed
    file is rejected in place; startup never rewrites or repairs its contents.
    """
    def require(condition: bool, message: str) -> None:
        if not condition:
            raise DomainError("invalid_store", message)

    def text(value, label: str, nonempty: bool = False) -> None:
        require(type(value) is str and (not nonempty or bool(value.strip())), f"Invalid {label}.")

    def fields(record, required: tuple[str, ...], label: str) -> None:
        require(type(record) is dict and all(key in record for key in required), f"Malformed {label} record.")

    require(type(state) is dict and state.get("store_version") == "0.1", "Unsupported or malformed local store.")
    fields(state, ("design", "revision", "snapshots", "runs", "reviews"), "local store")
    policies = validate_policy_history(state)
    validate_shape(state["design"])
    revision = state["revision"]
    fields(revision, ("id", "semantic_hash", "layout_hash", "created_at"), "current revision")
    for key in ("id", "semantic_hash", "layout_hash", "created_at"):
        text(revision[key], f"revision {key}", True)
    hashes = revision_hashes(state["design"])
    require(all(revision[key] == value for key, value in hashes.items()), "Current revision hashes do not match the design.")
    snapshots = state["snapshots"]
    require(type(snapshots) is dict, "Snapshots must be an object.")
    for snapshot_id, design in snapshots.items():
        text(snapshot_id, "snapshot ID", True)
        validate_shape(design)
    require(revision["id"] in snapshots and snapshots[revision["id"]] == state["design"],
            "Current revision snapshot does not match the current design.")
    epochs = state.get("acceptance_epochs", {stage: 0 for stage in IMPLEMENTED_STAGES})
    require(type(epochs) is dict and all(stage in epochs for stage in IMPLEMENTED_STAGES), "Malformed acceptance epochs.")
    require(all(type(value) is int and value >= 0 for value in epochs.values()), "Acceptance epochs must be nonnegative integers.")
    require(type(state["runs"]) is list and type(state["reviews"]) is list, "Runs and reviews must be arrays.")
    runs = {}
    for run in state["runs"]:
        fields(run, ("id", "stage_id", "revision_id", "input_hash", "execution_status", "validation_status",
                     "review_status", "freshness", "summary", "diagnostics", "created_at", "source_snapshot_id",
                     "validator_version", "artifacts"), "run")
        for key in ("id", "stage_id", "revision_id", "input_hash", "created_at", "source_snapshot_id", "validator_version"):
            text(run[key], f"run {key}", True)
        text(run["summary"], "run summary")
        require(run["id"] not in runs, "Run IDs must be unique.")
        require(run["stage_id"] in IMPLEMENTED_STAGES, "A saved run refers to an unsupported stage.")
        require(run["execution_status"] == "Completed" and run["validation_status"] in ("Passed", "Failed"), "Invalid saved run execution status.")
        require(run["review_status"] in ("Awaiting Review", "Accepted", "Changes Requested") and run["freshness"] in ("Current", "Stale"), "Invalid saved run review status.")
        require(run["source_snapshot_id"] == run["revision_id"] and run["revision_id"] in snapshots,
                "Saved run source snapshot is missing or inconsistent.")
        require(run["input_hash"] == fingerprint(snapshots[run["revision_id"]], run["stage_id"]),
                "Saved run input hash does not match its source snapshot.")
        require(type(run["diagnostics"]) is list and type(run["artifacts"]) is list, "Malformed run diagnostics or artifacts.")
        for diagnostic in run["diagnostics"]:
            fields(diagnostic, ("code", "severity", "message"), "diagnostic")
            for key in ("code", "severity", "message"):
                text(diagnostic[key], f"diagnostic {key}")
            require(diagnostic["severity"] in ("error", "warning", "info"), "Invalid diagnostic severity.")
            for key in ("node_id", "port_id", "edge_id"):
                if key in diagnostic:
                    text(diagnostic[key], f"diagnostic {key}")
        failed = any(item["severity"] == "error" for item in run["diagnostics"])
        require(run["validation_status"] == ("Failed" if failed else "Passed"), "Saved run status contradicts its diagnostics.")
        for artifact in run["artifacts"]:
            fields(artifact, ("kind", "revision_id", "url"), "artifact")
            require(artifact["kind"] == "design_input_snapshot" and artifact["revision_id"] == run["revision_id"]
                    and artifact["url"] == f"/api/snapshots/{run['revision_id']}", "Saved artifact does not refer to the run's source snapshot.")
        require(bool(run["artifacts"]), "Saved run has no source snapshot artifact.")
        if "accepted_epoch" in run:
            require(type(run["accepted_epoch"]) is int and 0 <= run["accepted_epoch"] <= epochs[run["stage_id"]], "Invalid run acceptance epoch.")
        if "reviewed_revision_id" in run:
            require(run["reviewed_revision_id"] in snapshots
                    and fingerprint(snapshots[run["reviewed_revision_id"]], run["stage_id"]) == run["input_hash"],
                    "Accepted run refers to a different reviewed input.")
        runs[run["id"]] = run
    reviews = {}
    latest_reviews = {}
    stage_order = [stage[0] for stage in STAGES]
    for review in state["reviews"]:
        fields(review, ("id", "run_id", "stage_id", "revision_id", "input_hash", "decision", "note", "target_stage", "actor", "created_at"), "review")
        for key in ("id", "run_id", "stage_id", "revision_id", "input_hash", "decision", "note", "actor", "created_at"):
            text(review[key], f"review {key}", key != "note")
        require(review["id"] not in reviews and review["run_id"] in runs, "Review ID or source run is invalid.")
        run = runs[review["run_id"]]
        require(all(review[key] == run[key] for key in ("stage_id", "revision_id", "input_hash")), "Review does not match its source run.")
        require(review["decision"] in ("accepted", "changes_requested", "return_to_stage"), "Invalid review decision.")
        validate_policy_review(review, policies)
        if review["decision"] == "accepted":
            require(run["validation_status"] == "Passed", "A failed run has an accepted review.")
            epoch = review.get("acceptance_epoch", 0)
            require(type(epoch) is int and 0 <= epoch <= epochs[run["stage_id"]], "Invalid review acceptance epoch.")
            reviewed_revision = review.get("reviewed_revision_id", review["revision_id"])
            require(type(reviewed_revision) is str and reviewed_revision in snapshots
                    and fingerprint(snapshots[reviewed_revision], run["stage_id"]) == run["input_hash"],
                    "Accepted review does not match the reviewed revision.")
        else:
            require(bool(review["note"].strip()), "Change requests require feedback.")
        if review["decision"] == "return_to_stage":
            require(review["target_stage"] in stage_order
                    and stage_order.index(review["target_stage"]) < stage_order.index(review["stage_id"]), "Invalid return-stage review.")
        else:
            require(review["target_stage"] is None, "Unexpected review return target.")
        reviews[review["id"]] = review
        latest_reviews[run["id"]] = review
    for run in runs.values():
        review = latest_reviews.get(run["id"])
        expected_status = "Awaiting Review" if review is None else "Accepted" if review["decision"] == "accepted" else "Changes Requested"
        require(run["review_status"] == expected_status, "Run review status does not match its latest adoption decision.")
        if expected_status == "Accepted":
            require(run.get("accepted_epoch", 0) == review.get("acceptance_epoch", 0), "Run and review acceptance epochs differ.")


def _replace_with_windows_retry(source: str, destination: Path) -> None:
    """Keep atomic replacement, with at most 250 ms of Windows retry waits."""
    source, destination = _io_path(source), _io_path(destination)
    deadline = time.monotonic() + 0.3
    for delay in (0.01, 0.02, 0.04, 0.08, 0.1, None):
        try:
            os.replace(source, destination)
            return
        except PermissionError as error:
            # Windows access/sharing denials can be transient; their cause is unknown.
            code = getattr(error, "winerror", None)
            if sys.platform != "win32" or type(code) is not int or code not in (5, 32, 33) or delay is None:
                raise
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise
            time.sleep(min(delay, remaining))
            if time.monotonic() >= deadline:
                raise


class ProjectStore:
    """A single local user's project; all mutations serialize under one lock.

    ``path`` is the directory containing state.json. Revision source snapshots,
    full diagnostic records, and review history are saved there. HTTP exports
    contain design data only and do not replace local history backups.
    """

    def __init__(self, path: str | Path, fixture_path: str | Path | None = None):
        self.path = Path(path).resolve()
        self.state_path = self.path / "state.json"
        self.lock = threading.RLock()
        if _io_path(self.state_path).exists():
            try:
                self._state = strict_loads(_io_path(self.state_path).read_text(encoding="utf-8"))
                _validate_saved_state(self._state)
                self._state.setdefault("acceptance_epochs", {stage: 0 for stage in IMPLEMENTED_STAGES})
            except (DomainError, OSError, KeyError, TypeError, ValueError, OverflowError) as error:
                raise DomainError("invalid_store", "Cannot read the existing local project; it was not overwritten.") from error
        else:
            project_root = Path(__file__).resolve().parents[2]
            fixture = Path(fixture_path) if fixture_path else project_root / "examples" / "m1_two_nodes.json"
            design = strict_loads(fixture.read_text(encoding="utf-8"))
            validate_shape(design)
            revision = {"id": new_id("revision"), **revision_hashes(design), "created_at": utc_now()}
            self._state = {"store_version": "0.1", "design": design, "revision": revision,
                           "snapshots": {revision["id"]: copy.deepcopy(design)}, "runs": [], "reviews": [],
                           "acceptance_epochs": {stage: 0 for stage in IMPLEMENTED_STAGES}}
            self._persist(self._state)

    def _persist(self, state: dict) -> None:
        directory = _io_path(self.path)
        directory.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(state, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        descriptor, temporary = tempfile.mkstemp(prefix=".state-", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            _replace_with_windows_retry(temporary, self.state_path)
        finally:
            temporary_path = _io_path(temporary)
            if temporary_path.exists():
                temporary_path.unlink()

    def _commit(self, state: dict) -> None:
        self._persist(state)
        self._state = state

    def _current_run(self, stage_id: str) -> dict | None:
        current_hash = fingerprint(self._state["design"], stage_id)
        return next((run for run in reversed(self._state["runs"])
                     if run["stage_id"] == stage_id and run["input_hash"] == current_hash), None)

    def _effective_review_status(self, run: dict) -> str:
        if run["review_status"] == "Accepted" and run.get("accepted_epoch", 0) != self._state["acceptance_epochs"][run["stage_id"]]:
            return "Awaiting Review"
        return run["review_status"]

    def review_policy(self) -> dict:
        with self.lock:
            return copy.deepcopy(self._state.get("review_policy", DEFAULT_REVIEW_POLICY))

    def policy_provenance(self, policy_id: str | None = None) -> dict:
        with self.lock:
            policy = self.review_policy() if policy_id is None else next(
                (entry for entry in self._state.get("policy_history", []) if entry["id"] == policy_id), None)
            if not policy or policy["mode"] != "accept_on_pass" or policy["user_authorized"] is not True:
                raise DomainError("policy_authorization_required", "An explicit user-authorized accept_on_pass policy is required.", 409)
            return {"authorization": "user_preapproved", "policy_id": policy["id"], "policy": copy.deepcopy(policy)}

    def set_review_policy(self, mode: str, user_authorized: bool, note: str = "", expected_policy_id=None) -> dict:
        if (mode not in ("manual", "accept_on_pass") or type(user_authorized) is not bool
                or type(note) is not str or len(note.encode("utf-8")) > 32768
                or expected_policy_id is not None and type(expected_policy_id) is not str):
            raise DomainError("invalid_policy", "Use manual or accept_on_pass with a boolean authorization and text note.")
        if user_authorized != (mode == "accept_on_pass"):
            raise DomainError("policy_authorization_required", "Accept on pass requires explicit user_authorized=true; manual uses false.", 409)
        with self.lock:
            if expected_policy_id != self.review_policy()["id"]:
                raise DomainError("policy_conflict", "Review policy changed since it was loaded.", 409)
            state = copy.deepcopy(self._state)
            policy = {"id": new_id("policy"), "mode": mode, "user_authorized": user_authorized,
                      "note": note.strip(), "created_at": utc_now(), "authorization_source": "explicit_api_configuration"}
            state.setdefault("policy_history", []).append(policy)
            state["review_policy"] = policy
            self._apply_accept_on_pass(state)
            self._commit(state)
            return self.envelope()

    @staticmethod
    def _apply_accept_on_pass(state: dict) -> bool:
        policy = state.get("review_policy", DEFAULT_REVIEW_POLICY)
        if policy["mode"] != "accept_on_pass" or policy["user_authorized"] is not True:
            return False
        previous_accepted = True
        changed = False
        for stage in IMPLEMENTED_STAGES:
            current_hash = fingerprint(state["design"], stage)
            run = next((item for item in reversed(state["runs"]) if item["stage_id"] == stage and item["input_hash"] == current_hash), None)
            if not run or run["validation_status"] != "Passed" or not previous_accepted:
                previous_accepted = False
                continue
            epoch = state["acceptance_epochs"][stage]
            if run["review_status"] == "Accepted" and run.get("accepted_epoch", 0) == epoch:
                continue
            run.update(review_status="Accepted", accepted_epoch=epoch, reviewed_revision_id=state["revision"]["id"])
            state["reviews"].append({"id": new_id("review"), "run_id": run["id"], "stage_id": stage,
                                     "revision_id": run["revision_id"], "input_hash": run["input_hash"],
                                     "decision": "accepted", "note": "Accepted after current input validation passed under the user's saved policy.",
                                     "target_stage": None, "actor": "automation_policy", "created_at": utc_now(),
                                     "acceptance_epoch": epoch, "reviewed_revision_id": state["revision"]["id"],
                                     "provenance": {"authorization": "user_preapproved", "policy_id": policy["id"], "policy": copy.deepcopy(policy)}})
            changed = True
        return changed

    def envelope(self) -> dict:
        with self.lock:
            result = copy.deepcopy({key: self._state[key] for key in ("design", "revision", "runs", "reviews")})
            result["review_policy"] = self.review_policy()
            result["policy_history"] = copy.deepcopy(self._state.get("policy_history", []))
            for run in result["runs"]:
                run["freshness"] = "Current" if run["input_hash"] == fingerprint(self._state["design"], run["stage_id"]) else "Stale"
                run["review_status"] = self._effective_review_status(run)
            workflow = []
            for index, (stage_id, label) in enumerate(STAGES, 1):
                current = self._current_run(stage_id)
                latest = next((run for run in reversed(result["runs"]) if run["stage_id"] == stage_id), None)
                selected = current or latest
                entry = {"id": stage_id, "index": index, "label": label,
                         "implemented": stage_id in IMPLEMENTED_STAGES,
                         "execution_status": "Not Run", "validation_status": "Not Checked" if stage_id in IMPLEMENTED_STAGES else "Unsupported",
                         "review_status": "Awaiting Review", "freshness": "Current", "latest_run_id": None}
                if selected:
                    for key in ("execution_status", "validation_status", "review_status"):
                        entry[key] = selected[key]
                    entry["review_status"] = self._effective_review_status(selected)
                    entry["freshness"] = "Current" if current else "Stale"
                    entry["latest_run_id"] = selected["id"]
                workflow.append(entry)
            result["workflow"] = workflow
            result["implementation"] = {"milestone": "M1", "scope": "design_input_checks_and_human_review",
                                        "llm_connected": False, "eda_executed": False,
                                        "fixture_is_circuit_evidence": False}
            return result

    def save(self, design: dict, expected_revision_id: str) -> dict:
        validate_shape(design)
        if type(expected_revision_id) is not str:
            raise DomainError("invalid_request", "expected_revision_id must be a string.")
        with self.lock:
            if expected_revision_id != self._state["revision"]["id"]:
                raise DomainError("revision_conflict", "Project changed since it was loaded. Reload before saving.", 409)
            if design == self._state["design"]:
                return self.envelope()
            state = copy.deepcopy(self._state)
            for stage_id in IMPLEMENTED_STAGES:
                if fingerprint(design, stage_id) != fingerprint(self._state["design"], stage_id):
                    state["acceptance_epochs"][stage_id] += 1
            state["design"] = copy.deepcopy(design)
            state["revision"] = {"id": new_id("revision"), **revision_hashes(design), "created_at": utc_now()}
            state["snapshots"][state["revision"]["id"]] = copy.deepcopy(design)
            self._commit(state)
            return self.envelope()

    def validate(self, stage_id: str, revision_id: str) -> dict:
        if type(stage_id) is not str or type(revision_id) is not str:
            raise DomainError("invalid_request", "stage_id and revision_id must be strings.")
        with self.lock:
            if revision_id != self._state["revision"]["id"]:
                raise DomainError("revision_conflict", "Verification must use the current saved revision.", 409)
            diagnostics = validate_stage(self._state["design"], stage_id)
            failed = any(item["severity"] == "error" for item in diagnostics)
            error_count = sum(item["severity"] == "error" for item in diagnostics)
            warning_count = sum(item["severity"] == "warning" for item in diagnostics)
            run = {"id": new_id("run"), "stage_id": stage_id, "revision_id": revision_id,
                   "input_hash": fingerprint(self._state["design"], stage_id),
                   "execution_status": "Completed", "validation_status": "Failed" if failed else "Passed",
                   "review_status": "Awaiting Review", "freshness": "Current",
                   "summary": f"Deterministic M1 input checks: {error_count} error(s), {warning_count} warning(s). No LLM or EDA execution.",
                   "diagnostics": diagnostics, "created_at": utc_now(),
                   "source_snapshot_id": revision_id, "validator_version": "0.1.0",
                   "artifacts": [{"kind": "design_input_snapshot", "revision_id": revision_id,
                                  "url": f"/api/snapshots/{revision_id}"}]}
            state = copy.deepcopy(self._state)
            state["runs"].append(run)
            self._apply_accept_on_pass(state)
            self._commit(state)
            return self.envelope()

    def review(self, run_id: str, decision: str, note: str, target_stage: str | None = None, *, operator=None) -> dict:
        operator_fields = manual_review_fields(operator)
        if any(type(value) is not str for value in (run_id, decision, note)):
            raise DomainError("invalid_request", "run_id, decision, and note must be strings.")
        if decision not in ("accepted", "changes_requested", "return_to_stage"):
            raise DomainError("invalid_decision", "Unknown human review decision.")
        with self.lock:
            run = next((item for item in self._state["runs"] if item["id"] == run_id), None)
            if not run:
                raise DomainError("run_not_found", "Validation run does not exist.", 404)
            if decision == "accepted":
                if run["validation_status"] != "Passed":
                    raise DomainError("verification_failed", "A failed verification cannot be accepted.", 409)
                if run["input_hash"] != fingerprint(self._state["design"], run["stage_id"]):
                    raise DomainError("stale_run", "This result belongs to older inputs; verify the current revision.", 409)
                current = self._current_run(run["stage_id"])
                if current is None or current["id"] != run_id:
                    raise DomainError("run_superseded", "Review the latest result for this stage and input.", 409)
                for previous in IMPLEMENTED_STAGES[:IMPLEMENTED_STAGES.index(run["stage_id"])]:
                    previous_run = self._current_run(previous)
                    if not previous_run or self._effective_review_status(previous_run) != "Accepted":
                        raise DomainError("review_prerequisite", f"Accept the current {dict(STAGES)[previous]} result first.", 409)
            else:
                if not note.strip():
                    raise DomainError("feedback_required", "Describe the requested change or return reason.")
                if decision == "return_to_stage":
                    available = [stage[0] for stage in STAGES]
                    if target_stage not in available or available.index(target_stage) >= available.index(run["stage_id"]):
                        raise DomainError("invalid_return_stage", "Return target must be an earlier design stage.")
            state = copy.deepcopy(self._state)
            edited = next(item for item in state["runs"] if item["id"] == run_id)
            edited["review_status"] = "Accepted" if decision == "accepted" else "Changes Requested"
            if decision == "accepted":
                edited["accepted_epoch"] = state["acceptance_epochs"][run["stage_id"]]
                edited["reviewed_revision_id"] = state["revision"]["id"]
            record = {"id": new_id("review"), "run_id": run_id, "stage_id": run["stage_id"],
                      "revision_id": run["revision_id"], "input_hash": run["input_hash"],
                      "decision": decision, "note": note, "target_stage": target_stage if decision == "return_to_stage" else None,
                      **operator_fields, "created_at": utc_now()}
            if decision == "accepted":
                record["acceptance_epoch"] = state["acceptance_epochs"][run["stage_id"]]
                record["reviewed_revision_id"] = state["revision"]["id"]
            state["reviews"].append(record)
            self._commit(state)
            return self.envelope()

    def snapshot(self, revision_id: str) -> dict:
        with self.lock:
            try:
                return copy.deepcopy(self._state["snapshots"][revision_id])
            except KeyError as error:
                raise DomainError("snapshot_not_found", "Input snapshot does not exist.", 404) from error

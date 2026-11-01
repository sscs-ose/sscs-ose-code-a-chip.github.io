"""Durable S04 node RTL generation and external-interface checks.

New generation never compiles or simulates RTL. Historical behavioral evidence
and the explicit legacy verification operation remain readable and reproducible.
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import re
import tempfile
import threading
import time
import traceback
from pathlib import Path

from .context import PROJECTED_CONTRACT_KINDS, build_node_context, node_fingerprint
from .domain import DomainError, IMPLEMENTED_STAGES
from .review_actor import REVIEW_ACTORS, manual_review_fields, validate_review_actor
from .envelope_cache import memoized_envelope
from .observation import ObservedState, persist_observation, require_durable_write
from .provider import ChatCompletionsClient, validate_profile, estimate_message_input
from .rtl_checks import check_rtl, compare_rtl, extract_rtl
from .store import new_id, strict_loads, utc_now, _replace_with_windows_retry, _io_path
from .verification import build_verification_plan, object_hash, verification_template_version, verify_behavior

ACTIVE = {"Queued", "Running"}
TERMINAL = {"Completed", "Failed", "Cancelled", "Interrupted"}
DECISIONS = {"accepted", "changes_requested", "return_to_stage"}
LIVE_PLAN_KINDS = PROJECTED_CONTRACT_KINDS | {"npu2_buffer_original_job", "npu2_control_original_job", "npu2_array_node_original_job"}
LOCAL_RTL_VALIDATION_SCOPE = "local_rtl_interface_v1"


SUBMISSION_VERSION = "node-submission-v1"
SUBMISSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SUBMISSION_FIELDS = ("node_id", "revision_id", "context_id", "profile_revision_id", "operation", "base_job_id", "instruction", "retry_of_job_id")


def _validate_submission_id(value):
    if type(value) is not str or not SUBMISSION_ID.fullmatch(value):
        raise DomainError("invalid_submission_id", "Submission identity must be 1 to 128 identifier characters.")


def _submission_request(node_id, revision_id, context_id, profile_revision_id, operation="generate", base_job_id=None, instruction="", retry_of_job_id=None):
    return dict(zip(SUBMISSION_FIELDS, (node_id, revision_id, context_id, profile_revision_id, operation, base_job_id, instruction, retry_of_job_id)))


def _submission_hash(request):
    return hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _exception_diagnostic(error, phase):
    """Retain failure location/codes without exception text, prompts or secrets."""
    name = type(error).__name__
    details = {"diagnostic_version": "generation-exception-v1", "execution_phase": phase,
               "exception_class": name if name.isidentifier() and len(name) <= 80 else "Exception"}
    for field in ("errno", "winerror"):
        value = getattr(error, field, None)
        if type(value) is int:
            details[field] = value
    return details


def _log_execution_exception(job_id, error, details):
    # A normal traceback renders str(error), which can contain provider data or
    # credentials. Log only code locations and the same sanitized saved codes.
    frames = [{"file": Path(frame.filename).name, "line": frame.lineno, "function": frame.name}
              for frame in traceback.extract_tb(error.__traceback__)[-20:]]
    logging.getLogger(__name__).error("Generation worker failure: job=%s diagnostic=%s frames=%s",
                                    job_id, json.dumps(details, sort_keys=True), json.dumps(frames))


def text_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest() if value is not None else None


def request_hash(context: dict, profile_revision_id: str, parameters: dict, operation: str, base_job_id) -> str:
    payload = {"messages": context["messages"], "node_input_hash": context["node_input_hash"],
               "profile_revision_id": profile_revision_id, "parameters": parameters,
               "operation": operation, "base_job_id": base_job_id}
    if context.get("retry_of_job_id") is not None:
        payload["retry_of_job_id"] = context["retry_of_job_id"]
    if context.get("validation_scope") is not None:
        payload["validation_scope"] = context["validation_scope"]
    if context.get("batch_context") is not None:
        payload["batch_context"] = context["batch_context"]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def saved_verification_hash(parent: dict, plan: dict) -> str:
    """Bind a tool-only run to the exact saved candidate and original inputs."""
    return object_hash({"operation": "verify", "verification_of_job_id": parent["id"],
                        "revision_id": parent["revision_id"], "node_id": parent["node_id"],
                        "input_hash": parent["input_hash"], "source_context_id": parent["context_id"],
                        "rtl_sha256": text_hash(parent["rtl"]), "verification_plan": plan})


def scheduler_live_source_error(design: dict, job: dict, verification_plans=None):
    """Recheck current scheduler input without changing frozen prompt hashes.

    Generic fingerprints normalize equivalent JSON numbers. The scheduler's
    integer-only matrix contract must nevertheless reject an invalid live type
    even when its normalized fingerprint matches the saved original source.
    Historical PE candidates retain their existing freshness behavior.
    """
    plan = job.get("verification_plan")
    if type(plan) is not dict or plan.get("kind") not in LIVE_PLAN_KINDS:
        return None
    key = ("frozen", job["node_id"], verification_template_version(plan))
    if verification_plans is not None and key in verification_plans:
        rebuilt, error = verification_plans[key]
    else:
        try:
            rebuilt, error = build_verification_plan(design, job["node_id"], verification_template_version(plan)), None
        except DomainError as caught:
            rebuilt, error = None, {"code": caught.code, "message": caught.message}
        if verification_plans is not None:
            verification_plans[key] = (rebuilt, error)
    if error:
        return error
    if object_hash(rebuilt) != object_hash(plan):
        return {"code": "scheduler_live_source_conflict", "message": "Current scheduler source must rebuild the same frozen original verification plan."}
    return None


class GenerationManager(ObservedState):
    def __init__(self, project_store, compiler: dict | None = None):
        self.store = project_store
        self.compiler = copy.deepcopy(compiler)
        self.path = project_store.state_path.parent / "generation.json"
        self.lock = threading.RLock()
        self._worker = None
        self._batch_reservation = None
        self._cancel = threading.Event()
        self._closed = False
        self._committed = None
        self._storage_error = None
        self._stream_checkpoint_at = time.monotonic()
        self._stream_pending_bytes = 0
        if _io_path(self.path).exists():
            try:
                self._state = strict_loads(_io_path(self.path).read_text(encoding="utf-8"))
                self._validate_saved()
                self._committed = copy.deepcopy(self._state)
            except (DomainError, OSError, KeyError, TypeError, ValueError, AttributeError) as error:
                raise DomainError("invalid_generation_store", "Generation history is inconsistent; original file preserved.") from error
            interrupted = False
            for job in self._state["jobs"]:
                if job["execution_status"] in ACTIVE:
                    job.update(execution_status="Interrupted", validation_status="Not Checked",
                               finished_at=utc_now(), error={"code": "interrupted", "message": "Service restarted; request was not resent."})
                    interrupted = True
            if interrupted:
                self._persist()
        else:
            self._state = {"generation_store_version": "0.1", "profiles": [], "active_profile_revision_id": None,
                           "probe": None, "jobs": [], "reviews": [], "node_inputs": {}, "node_epochs": {}}
            self._persist()
        self.observe_design()

    def _validate_saved(self):
        state = self._state
        if type(state) is not dict or state.get("generation_store_version") != "0.1":
            raise ValueError("Unsupported generation store")
        for key in ("profiles", "jobs", "reviews"):
            if type(state.get(key)) is not list:
                raise ValueError("Invalid history container")
        for key in ("node_inputs", "node_epochs"):
            if type(state.get(key)) is not dict:
                raise ValueError("Invalid node state")
        if any(type(v) is not int or v < 0 for v in state["node_epochs"].values()):
            raise ValueError("Invalid node epoch")
        profiles = {}
        for record in state["profiles"]:
            if type(record) is not dict or type(record.get("revision_id")) is not str or record["revision_id"] in profiles:
                raise ValueError("Invalid profile version")
            validate_profile(record["profile"])
            profiles[record["revision_id"]] = record["profile"]
        if state["active_profile_revision_id"] is not None and state["active_profile_revision_id"] not in profiles:
            raise ValueError("Missing active profile")
        ids = set()
        earlier_jobs = {}
        for job in state["jobs"]:
            required = ("id", "node_id", "revision_id", "input_hash", "profile_revision_id", "profile", "context_id",
                        "context", "operation", "base_job_id", "instruction", "parameters", "origin", "execution_status",
                        "validation_status", "review_status", "raw_content", "rtl", "diff", "diagnostics", "checks",
                        "events", "created_at", "finished_at", "error", "usage", "finish_reason")
            if type(job) is not dict or any(key not in job for key in required) or job["id"] in ids:
                raise ValueError("Malformed generation job")
            for key in ("id", "node_id", "revision_id", "input_hash", "profile_revision_id", "context_id", "instruction", "diff", "created_at"):
                if type(job[key]) is not str:
                    raise ValueError("Invalid job field type")
            for key in ("profile", "context", "parameters", "checks"):
                if type(job[key]) is not dict:
                    raise ValueError("Invalid job evidence type")
            ids.add(job["id"])
            if job["execution_status"] not in ACTIVE | TERMINAL or job["operation"] not in ("generate", "repair", "verify"):
                raise ValueError("Invalid job state")
            if "validation_scope" in job and (job["validation_scope"] != LOCAL_RTL_VALIDATION_SCOPE
                    or job["operation"] == "verify" or job["context"].get("validation_scope") != job["validation_scope"]):
                raise ValueError("Invalid generation validation scope")
            if job["validation_status"] not in ("Not Checked", "Passed", "Failed", "Unsupported"):
                raise ValueError("Invalid validation state")
            if job["review_status"] not in ("Awaiting Review", "Accepted", "Changes Requested"):
                raise ValueError("Invalid review state")
            if profiles.get(job["profile_revision_id"]) != job["profile"]:
                raise ValueError("Profile provenance mismatch")
            if job["origin"] != ("local_llm" if job["profile"]["execution_location"] == "Local" else "remote_llm"):
                raise ValueError("Provider origin mismatch")
            snapshot = self.store.snapshot(job["revision_id"])
            if node_fingerprint(snapshot, job["node_id"]) != job["input_hash"]:
                raise ValueError("Input provenance mismatch")
            verification_parent = earlier_jobs.get(job.get("verification_of_job_id")) if job["operation"] == "verify" else None
            if job["operation"] == "verify":
                self._validate_verification_parent(job, verification_parent)
            elif "verification_of_job_id" in job or job.get("provider_request_executed") is False:
                raise ValueError("Invalid saved verification provenance")
            elif job["context"].get("node_input_hash") != job["input_hash"] or request_hash(
                    job["context"], job["profile_revision_id"], job["parameters"], job["operation"], job["base_job_id"]) != job["context_id"]:
                raise ValueError("Request provenance mismatch")
            retry_of_job_id = job.get("retry_of_job_id")
            if job["operation"] != "verify" and (("retry_of_job_id" in job) != ("retry_of_job_id" in job["context"]) or job["context"].get("retry_of_job_id") != retry_of_job_id):
                raise ValueError("Retry context provenance mismatch")
            if "retry_of_job_id" in job:
                if type(retry_of_job_id) is not str or not retry_of_job_id:
                    raise ValueError("Invalid retry provenance")
                self._validate_retry_parent(earlier_jobs.get(retry_of_job_id), job["node_id"], job["revision_id"],
                                            job["input_hash"], job["operation"], job["base_job_id"], job["instruction"], job["context"])
            if type(job["raw_content"]) is not str or job["rtl"] is not None and type(job["rtl"]) is not str:
                raise ValueError("Invalid candidate text")
            if job.get("raw_content_sha256") != text_hash(job["raw_content"]) or job.get("rtl_sha256") != text_hash(job["rtl"]):
                raise ValueError("Candidate evidence mismatch")
            base = next((item for item in state["jobs"] if item["id"] == job["base_job_id"]), None) if job["base_job_id"] else None
            if job["operation"] == "repair" and (base is None or base["node_id"] != job["node_id"] or not base["rtl"]):
                raise ValueError("Invalid repair provenance")
            # A saved verification retains the originating prompt as evidence,
            # rather than pretending that another model request was submitted.
            # Its parent has already passed full prompt reconstruction above.
            expected = verification_parent["context"] if verification_parent else build_node_context(
                snapshot, job["revision_id"], job["node_id"], job["instruction"],
                base["rtl"] if base else None, base["diagnostics"] if base else None,
                template_version=job["context"].get("prompt_template_version"),
                reasoning_effort=(earlier_jobs[retry_of_job_id]["context"].get("thinking_control", {}).get("reasoning_effort")
                                  if retry_of_job_id else job["profile"].get("reasoning_effort")))
            if job["context"].get("batch_context") is not None:
                from .generation_batches import pack_batch_context, same_provider
                metadata = job["context"]["batch_context"]
                required = ("batch_id", "index", "prior_job_ids", "source_workflow_run_id", "seed_job_ids", "retry_of_batch_id")
                if (job["operation"] == "verify" or any(key not in metadata for key in required)
                        or job.get("batch_id") != metadata["batch_id"] or job.get("batch_index") != metadata["index"]
                        or type(metadata["prior_job_ids"]) is not list or len(set(metadata["prior_job_ids"])) != len(metadata["prior_job_ids"])):
                    raise ValueError("Invalid sequential context provenance")
                prior = [earlier_jobs[value] for value in metadata["prior_job_ids"]]
                seeds = metadata["seed_job_ids"]
                if (type(seeds) is not list or metadata["prior_job_ids"][:len(seeds)] != seeds
                        or bool(seeds) and not metadata["retry_of_batch_id"]
                        or any((value.get("batch_id") != job["batch_id"] and value["id"] not in seeds) or value["revision_id"] != job["revision_id"] or (not same_provider(value["profile"], job["profile"]) if value["id"] in seeds else value["profile_revision_id"] != job["profile_revision_id"]) for value in prior)):
                    raise ValueError("Invalid sequential conversation chain")
                batch_metadata = {key: metadata[key] for key in required}
                if metadata.get("repair_guidance") is not None:
                    batch_metadata["repair_guidance"] = metadata["repair_guidance"]
                if metadata.get("netlist_repair_evidence") is not None:
                    batch_metadata["netlist_repair_evidence"] = metadata["netlist_repair_evidence"]
                if metadata.get("packing_policy_version") is not None:
                    batch_metadata["packing_policy_version"] = metadata["packing_policy_version"]
                expected = pack_batch_context(expected, prior, job["profile"], batch_metadata)
            elif "batch_id" in job or "batch_index" in job:
                raise ValueError("Missing sequential context provenance")
            if any(job["context"].get(key) != value for key, value in expected.items()):
                raise ValueError("Context does not match saved source inputs")
            if job["rtl"] is not None and extract_rtl(job["raw_content"]).get("rtl") != job["rtl"]:
                raise ValueError("Candidate does not match provider answer")
            plan = job.get("verification_plan")
            if plan is not None:
                expected_plan, plan_error = self._verification_plan(
                    snapshot, job["node_id"], template_version=verification_template_version(plan))
                if type(plan) is not dict or plan_error is not None or plan != expected_plan:
                    raise ValueError("Behavioral plan does not match the original design input")
                if job.get("verification_plan_sha256") != text_hash(json.dumps(plan, sort_keys=True, ensure_ascii=False, allow_nan=False)):
                    raise ValueError("Behavioral plan hash mismatch")
            behavior = job["checks"].get("behavioral")
            if behavior is not None:
                if (type(behavior) is not dict or behavior.get("validation_status") not in ("Not Run", "Passed", "Failed", "Unsupported")
                        or type(behavior.get("executed")) is not bool or type(behavior.get("diagnostics")) is not list):
                    raise ValueError("Invalid behavioral check evidence")
                if behavior["validation_status"] == "Passed" and not self._passed_checks(job, require_behavioral=True):
                    raise ValueError("Behavioral pass lacks matching executed proof")
                if behavior["validation_status"] == "Failed" and job["validation_status"] == "Passed":
                    raise ValueError("Candidate pass contradicts failed behavioral verification")
            if type(job["events"]) is not list or type(job["diagnostics"]) is not list:
                raise ValueError("Invalid evidence list")
            for index, event in enumerate(job["events"], 1):
                if type(event) is not dict or event.get("sequence") != index or type(event.get("type")) is not str:
                    raise ValueError("Invalid event order")
            scoped_reviews = [r for r in state["reviews"] if r.get("job_id") == job["id"]]
            scoped_acceptance = bool(scoped_reviews and scoped_reviews[-1].get("validation_scope") == LOCAL_RTL_VALIDATION_SCOPE)
            if job["review_status"] == "Accepted" and (job["execution_status"] != "Completed" or
                    not (self._s04_passed_checks(job) if scoped_acceptance else job["validation_status"] == "Passed")):
                raise ValueError("Unverified accepted candidate")
            if job["review_status"] == "Accepted" and not (self._s04_passed_checks(job) if scoped_acceptance else self._passed_checks(job)):
                raise ValueError("Missing candidate check evidence")
            earlier_jobs[job["id"]] = job
        submissions = state.get("submissions", {})
        if type(submissions) is not dict:
            raise ValueError("Invalid submission ledger")
        bound_jobs = set()
        for submission_id, receipt in submissions.items():
            _validate_submission_id(submission_id)
            if (type(receipt) is not dict or set(receipt) != {"request", "binding_hash", "job_id", "rejection"}
                    or type(receipt["request"]) is not dict or set(receipt["request"]) != set(SUBMISSION_FIELDS)
                    or receipt["binding_hash"] != _submission_hash(receipt["request"])):
                raise ValueError("Invalid submission request binding")
            job_id, rejection = receipt["job_id"], receipt["rejection"]
            if job_id is None:
                if (type(rejection) is not dict or set(rejection) != {"code", "message", "status"}
                        or type(rejection["code"]) is not str or type(rejection["message"]) is not str
                        or type(rejection["status"]) is not int or not 400 <= rejection["status"] < 500):
                    raise ValueError("Invalid rejected submission receipt")
            else:
                job = earlier_jobs.get(job_id) if type(job_id) is str else None
                if (job is None or rejection is not None or job_id in bound_jobs
                        or job.get("submission_id") != submission_id or job["operation"] == "verify"
                        or _submission_request(*(job.get(key) for key in SUBMISSION_FIELDS)) != receipt["request"]):
                    raise ValueError("Submission receipt does not bind its exact job")
                bound_jobs.add(job_id)
        for job in state["jobs"]:
            if "submission_id" in job and (job["id"] not in bound_jobs or job["submission_id"] not in submissions):
                raise ValueError("Keyed generation job lacks its durable submission receipt")
        for record in state["reviews"]:
            if type(record) is not dict or record.get("job_id") not in ids or record.get("decision") not in DECISIONS or record.get("actor") not in REVIEW_ACTORS:
                raise ValueError("Invalid adoption review")
            validate_review_actor(record)
            reviewed_job = next(job for job in state["jobs"] if job["id"] == record["job_id"])
            if any(record.get(key) != reviewed_job[key] for key in ("node_id", "revision_id", "input_hash")):
                raise ValueError("Review input provenance mismatch")
            reviewed_snapshot = self.store.snapshot(record["reviewed_revision_id"])
            if record["decision"] == "accepted" and node_fingerprint(reviewed_snapshot, reviewed_job["node_id"]) != reviewed_job["input_hash"]:
                raise ValueError("Acceptance does not match the reviewed source inputs")
            if record["actor"] == "automation_policy":
                provenance = record.get("provenance")
                if (record["decision"] != "accepted" or type(provenance) is not dict
                        or provenance != self.store.policy_provenance(provenance.get("policy_id"))
                        or not (self._s04_passed_checks(reviewed_job) if record.get("validation_scope") == LOCAL_RTL_VALIDATION_SCOPE
                                else self._passed_checks(reviewed_job, require_behavioral=True))):
                    raise ValueError("Automatic candidate adoption lacks authorized behavioral proof")
            if "validation_scope" in record and (record["validation_scope"] != LOCAL_RTL_VALIDATION_SCOPE
                    or record["decision"] != "accepted" or reviewed_job["operation"] == "verify"
                    or not self._s04_passed_checks(reviewed_job)):
                raise ValueError("Invalid S04 interface adoption proof")
        for job in state["jobs"]:
            reviews = [record for record in state["reviews"] if record["job_id"] == job["id"]]
            if job["review_status"] != "Awaiting Review":
                if not reviews or (reviews[-1]["decision"] == "accepted") != (job["review_status"] == "Accepted"):
                    raise ValueError("Missing latest adoption decision")
            if job["review_status"] == "Accepted" and (reviews[-1].get("acceptance_epoch") != job.get("acceptance_epoch") or
                    reviews[-1]["reviewed_revision_id"] != job.get("reviewed_revision_id")):
                raise ValueError("Adoption epoch mismatch")

    @staticmethod
    def _s04_passed_checks(job):
        """Current S04 scope without reinterpreting historical simulation results."""
        return (job.get("execution_status") == "Completed"
                and type(job.get("rtl")) is str and bool(job["rtl"].strip())
                and job.get("checks", {}).get("interface", {}).get("validation_status") == "Passed"
                and extract_rtl(job.get("raw_content", "")).get("rtl") == job["rtl"]
                and not any(item.get("severity") == "error" for item in extract_rtl(job.get("raw_content", "")).get("diagnostics", [])))

    @staticmethod
    def _passed_checks(job, require_behavioral=False):
        checks = job.get("checks", {})
        if type(checks) is not dict or any(type(checks.get(key, {})) is not dict for key in ("interface", "syntax", "behavioral")):
            return False
        syntax = checks.get("syntax", {})
        basic = (checks.get("interface", {}).get("validation_status") == "Passed" and
                syntax.get("validation_status") == "Passed" and syntax.get("executed") is True
                and type(syntax.get("exit_code")) is int and syntax["exit_code"] == 0)
        if not require_behavioral:
            return basic
        behavior = checks.get("behavioral", {})
        plan = job.get("verification_plan")
        return (basic and type(plan) is dict and type(job.get("rtl")) is str and bool(job["rtl"])
                and all(type(plan.get(key)) is str and len(plan[key]) == 64 for key in ("vector_hash", "testbench_sha256"))
                and behavior.get("validation_status") == "Passed"
                and behavior.get("executed") is True and type(behavior.get("exit_code")) is int and behavior["exit_code"] == 0
                and behavior.get("vector_hash") == plan.get("vector_hash")
                and behavior.get("testbench_sha256") == plan.get("testbench_sha256")
                and behavior.get("rtl_sha256") == text_hash(job.get("rtl")))

    @staticmethod
    def _validate_verification_parent(job, parent):
        if (parent is None or parent["execution_status"] != "Completed" or not parent["rtl"]
                or type(parent.get("finished_at")) is not str or not parent["finished_at"].strip()):
            raise ValueError("Saved verification needs an earlier completed candidate")
        unchanged = ("node_id", "revision_id", "input_hash", "profile_revision_id", "profile", "context",
                     "instruction", "parameters", "origin", "raw_content", "rtl")
        if any(job.get(key) != parent.get(key) for key in unchanged):
            raise ValueError("Saved verification changed original RTL or generation provenance")
        if job.get("raw_reasoning", "") != parent.get("raw_reasoning", ""):
            raise ValueError("Saved verification changed original reasoning evidence")
        if (job.get("provider_request_executed") is not False or job["base_job_id"] is not None
                or "retry_of_job_id" in job or job["usage"] is not None or job["finish_reason"] is not None
                or job.get("provider_request_id") is not None or type(job.get("verification_plan")) is not dict
                or job["context_id"] != saved_verification_hash(parent, job["verification_plan"])):
            raise ValueError("Invalid tool-only verification provenance")

    @staticmethod
    def _verification_plan(design, node_id, template_version=None):
        try:
            return build_verification_plan(design, node_id, template_version=template_version), None
        except DomainError as error:
            return None, {"code": error.code, "message": error.message}

    def _record_acceptance(self, job, actor, note, provenance=None, validation_scope=None):
        revision_id = self.store.envelope()["revision"]["id"]
        job.update(review_status="Accepted", acceptance_epoch=self._state["node_epochs"][job["node_id"]],
                   reviewed_revision_id=revision_id)
        record = {"id": new_id("candidate-review"), "job_id": job["id"], "node_id": job["node_id"],
                  "revision_id": job["revision_id"], "input_hash": job["input_hash"], "reviewed_revision_id": revision_id,
                  "decision": "accepted", "note": note, "target_stage": None,
                  "acceptance_epoch": job["acceptance_epoch"], "actor": actor, "created_at": utc_now()}
        if provenance is not None:
            record["provenance"] = copy.deepcopy(provenance)
        if validation_scope is not None:
            record["validation_scope"] = validation_scope
        self._state["reviews"].append(record)

    def _accept_on_pass(self, job):
        with self.store.lock:
            design = self.store.envelope()["design"]
            if node_fingerprint(design, job["node_id"]) != job["input_hash"] or scheduler_live_source_error(design, job):
                return False
            return self._accept_on_pass_current(job)

    def _accept_on_pass_current(self, job):
        policy = self.store.review_policy()
        if policy["mode"] != "accept_on_pass" or policy["user_authorized"] is not True:
            return False
        scoped = job["operation"] != "verify"
        passed = self._s04_passed_checks(job) if scoped else (job["validation_status"] == "Passed" and self._passed_checks(job, require_behavioral=True))
        if (job["review_status"] == "Changes Requested" or not passed
                or self._state["node_inputs"].get(job["node_id"]) != job["input_hash"]):
            return False
        relevant = [item for item in self._state["jobs"] if item["node_id"] == job["node_id"] and item["input_hash"] == job["input_hash"]]
        if relevant[-1]["id"] != job["id"]:
            return False
        try:
            self._prerequisites()
        except DomainError:
            return False
        if job["review_status"] == "Accepted" and job.get("acceptance_epoch") == self._state["node_epochs"].get(job["node_id"]):
            return False
        self._record_acceptance(job, "automation_policy",
            "Accepted after current S04 external-interface checks passed under the user's saved policy. Syntax/synthesis and behavioral verification belong to S05/S06." if scoped else
            "Accepted after current interface, syntax, and behavioral verification passed under the user's saved policy.", self.store.policy_provenance(),
            LOCAL_RTL_VALIDATION_SCOPE if scoped else None)
        return True

    def apply_review_policy(self):
        self.observe_design()
        with self.lock, self.store.lock:
            changed = False
            for job in self._state["jobs"]:
                changed = self._accept_on_pass(job) or changed
            if changed:
                self._persist()
        return self.envelope()

    def _persist(self):
        require_durable_write()
        name = None
        try:
            for job in self._state["jobs"]:
                job["raw_content_sha256"] = text_hash(job["raw_content"])
                job["rtl_sha256"] = text_hash(job["rtl"])
                if "verification_plan" in job:
                    job["verification_plan_sha256"] = text_hash(json.dumps(job["verification_plan"], sort_keys=True, ensure_ascii=False, allow_nan=False)) if job["verification_plan"] is not None else None
            raw = json.dumps(self._state, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
            _io_path(self.path.parent).mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(prefix=".generation-", suffix=".tmp", dir=_io_path(self.path.parent))
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(raw); handle.flush(); os.fsync(handle.fileno())
            _replace_with_windows_retry(name, _io_path(self.path))
            self._committed = copy.deepcopy(self._state)
            self._storage_error = None
            self._stream_checkpoint_at = time.monotonic()
            self._stream_pending_bytes = 0
        except (OSError, ValueError, TypeError):
            if self._committed is not None:
                self._state = copy.deepcopy(self._committed)
            self._storage_error = {"code": "storage_error", "message": "Generation history could not be saved. Last durable state retained; stop and repair storage before retrying."}
            raise
        finally:
            if name is not None and os.path.exists(_io_path(name)):
                os.unlink(_io_path(name))

    def observe_design(self):
        design = self.store.envelope()["design"]
        with self.lock:
            current = {node["id"]: node_fingerprint(design, node["id"]) for node in design["nodes"]}
            # Rebuild each node/template once for this observation only. The
            # helper still compares every frozen plan with the rebuilt source.
            verification_plans = {}
            # Withdraw each current scheduler approval once if strict live
            # validation fails despite a numerically normalized hash match.
            # The epoch prevents a later restoration from reviving approval.
            invalid_live = {job["node_id"] for job in self._state["jobs"]
                            if job["review_status"] == "Accepted"
                            and current.get(job["node_id"]) == job["input_hash"]
                            and job.get("acceptance_epoch") == self._state["node_epochs"].get(job["node_id"])
                            and scheduler_live_source_error(design, job, verification_plans)}
            if current == self._state["node_inputs"] and not invalid_live:
                return
            for node_id in set(current) | set(self._state["node_inputs"]):
                if current.get(node_id) != self._state["node_inputs"].get(node_id) or node_id in invalid_live:
                    self._state["node_epochs"][node_id] = self._state["node_epochs"].get(node_id, 0) + 1
            self._state["node_inputs"] = current
            persist_observation(self)

    def _profile(self):
        return next((record for record in self._state["profiles"] if record["revision_id"] == self._state["active_profile_revision_id"]), None)

    def _require_profile(self, revision_id=None):
        record = self._profile()
        if record is None:
            raise DomainError("profile_required", "Save a connection profile first.", 409)
        if revision_id is not None and revision_id != record["revision_id"]:
            raise DomainError("profile_conflict", "Connection profile changed; preview the request again.", 409)
        return record

    def _stored_job(self, job_id):
        result = next((job for job in self._state["jobs"] if job["id"] == job_id), None)
        if result is None:
            raise DomainError("job_not_found", "Generation job does not exist.", 404)
        return result

    @staticmethod
    def _validate_retry_parent(parent, node_id, revision_id, input_hash, operation, base_job_id, instruction, context):
        if (parent is None or parent["execution_status"] not in {"Failed", "Cancelled", "Interrupted"}
                or type(parent.get("finished_at")) is not str or not parent["finished_at"].strip()):
            raise DomainError("invalid_retry_parent", "Retry needs a finished failed, cancelled, or interrupted generation job.", 409)
        if (parent["node_id"] != node_id or parent["revision_id"] != revision_id or parent["input_hash"] != input_hash):
            raise DomainError("retry_source_conflict", "Retry must use the same node and saved design revision as the failed request. Generate a new request for changed inputs.", 409)
        if (parent["operation"] != operation or parent["base_job_id"] != base_job_id or parent["instruction"] != instruction):
            raise DomainError("retry_request_conflict", "Retry must preserve the failed request's operation, repair base, and instruction.", 409)
        if (parent["context"]["messages"] != context["messages"]
                or parent["context"].get("prompt_template_version") != context.get("prompt_template_version")):
            raise DomainError("retry_request_conflict", "Retry must preserve the failed request's exact messages and prompt template.", 409)

    def _decorate(self, job, verification_plans=None):
        verification_plans = verification_plans if verification_plans is not None else {}
        source = self.store.envelope()
        result = copy.deepcopy(job)
        result["provider_input_estimated_tokens"] = estimate_message_input(job["context"]["messages"])
        current = self._state["node_inputs"].get(job["node_id"]) == job["input_hash"]
        live_error = scheduler_live_source_error(source["design"], job, verification_plans)
        if live_error:
            current = False
            result["current_source_validation"] = {"validation_status": "Failed", **live_error}
            result["blocked_reason"] = live_error["message"]
        result["freshness"] = "Current" if current else "Stale"
        s04_passed = self._s04_passed_checks(job)
        stage_status = "Passed" if s04_passed else ("Failed" if job["checks"].get("interface", {}).get("validation_status") == "Failed" else "Not Checked")
        result["stage_validation"] = {"stage_id": "local_rtl_generation", "scope": "external_interface",
            "validation_status": stage_status, "available": s04_passed, "syntax_stage_id": "local_synthesis",
            "behavioral_stage_id": "local_netlist_simulation"}
        # Tool-only legacy verification keeps its own result, independent of
        # the S04 scope shown for normal generate/repair records.
        result["effective_validation_status"] = job["validation_status"] if job["operation"] == "verify" else stage_status
        result["behavioral_verification"] = self._behavioral_verification_readiness(source, job["node_id"], verification_plans)
        try:
            self._saved_verification_inputs(job, source["revision"]["id"], verification_plans)
            result["saved_rtl_verification"] = {"available": True, "code": None,
                "message": "Run interface, syntax, and original-input behavioral checks on this saved RTL without an LLM request."}
        except DomainError as error:
            result["saved_rtl_verification"] = {"available": False, "code": error.code, "message": error.message}
        if result["review_status"] == "Accepted" and (not current or job.get("acceptance_epoch") != self._state["node_epochs"].get(job["node_id"])):
            result["review_status"] = "Awaiting Review"
        result["artifacts"] = [{"kind": "generation_job", "url": f'/api/generation/jobs/{job["id"]}'},
                               {"kind": "design_input_snapshot", "revision_id": job["revision_id"], "url": f'/api/snapshots/{job["revision_id"]}'}]
        return result

    def current_candidate_selection(self):
        """Return only the exact current latest adopted S04 identity per node.

        Worker source guards need these scalar identities, not copied prompts,
        raw answers, token estimates or behavioral-readiness GUI decorations.
        This is recomputed on every call, including live contract and adoption
        epoch checks; it is never a cached mutation/adoption decision.
        """
        self.observe_design()
        source = self.store.envelope()
        with self.lock:
            latest = {}
            for job in self._state["jobs"]:
                latest[job["node_id"]] = job
            plans = {}
            selected = {}
            for node_id, fingerprint in self._state["node_inputs"].items():
                job = latest.get(node_id)
                current = (job is not None and job["input_hash"] == fingerprint
                           and job["review_status"] == "Accepted"
                           and job.get("acceptance_epoch") == self._state["node_epochs"].get(node_id)
                           and not scheduler_live_source_error(source["design"], job, plans))
                selected[node_id] = job["id"] if current else None
            return selected

    @memoized_envelope
    def envelope(self):
        self.observe_design()
        with self.lock:
            profile = self._profile()
            source = self.store.envelope()
            verification_plans = {}
            jobs = [self._decorate(job, verification_plans) for job in self._state["jobs"]]
            nodes = []
            for node_id in self._state["node_inputs"]:
                relevant = [job for job in jobs if job["node_id"] == node_id]
                accepted = next((job for job in reversed(relevant) if job["freshness"] == "Current" and job["review_status"] == "Accepted"), None)
                latest = relevant[-1] if relevant else None
                nodes.append({"node_id": node_id, "latest_job_id": latest["id"] if latest else None,
                              "accepted_job_id": accepted["id"] if accepted else None,
                              "freshness": latest["freshness"] if latest else "Current",
                              "review_status": "Accepted" if accepted and latest and accepted["id"] == latest["id"] else "Awaiting Review",
                              "behavioral_verification": self._behavioral_verification_readiness(source, node_id, verification_plans)})
            probe = copy.deepcopy(self._state["probe"])
            return {"llm": {"profile": copy.deepcopy(profile["profile"]) if profile else None,
                            "profile_revision_id": profile["revision_id"] if profile else None, "probe": probe,
                            "capabilities": probe.get("capabilities", {}) if probe else {}},
                    "generation": {"implemented": True, "submission_protocol_version": SUBMISSION_VERSION, "jobs": jobs, "reviews": copy.deepcopy(self._state["reviews"]),
                                   "submissions": copy.deepcopy(self._state.get("submissions", {})),
                                   "validation_scope": LOCAL_RTL_VALIDATION_SCOPE,
                                   "syntax_stage_id": "local_synthesis", "behavioral_stage_id": "local_netlist_simulation",
                                   "storage_error": copy.deepcopy(self._storage_error),
                                   "nodes": nodes, "latest_job_id": jobs[-1]["id"] if jobs else None,
                                   "all_nodes_accepted": bool(nodes) and all(node["accepted_job_id"] and node["accepted_job_id"] == node["latest_job_id"] for node in nodes),
                                   "compiler": {"available": bool(self.compiler), "status": "Configured" if self.compiler else "Unsupported",
                                                "configuration": copy.deepcopy(self.compiler)}}}

    def save_profile(self, profile, expected_revision=None):
        normalized = validate_profile(profile)
        with self.lock:
            if self._batch_reservation is not None:
                raise DomainError("generation_batch_busy", "Finish or cancel sequential generation before changing its frozen provider profile.", 409)
            if expected_revision != self._state["active_profile_revision_id"]:
                raise DomainError("profile_conflict", "Profile changed since it was loaded.", 409)
            self._state["profiles"].append({"revision_id": new_id("profile"), "profile": normalized, "created_at": utc_now()})
            self._state["active_profile_revision_id"] = self._state["profiles"][-1]["revision_id"]
            self._state["probe"] = None
            self._persist()
        return self.envelope()

    def probe(self, profile_revision_id):
        with self.lock:
            if self._batch_reservation is not None:
                raise DomainError("generation_batch_busy", "Finish or cancel sequential generation before a provider probe.", 409)
            record = copy.deepcopy(self._require_profile(profile_revision_id))
        try:
            result = ChatCompletionsClient(record["profile"]).probe()
        except DomainError as error:
            result = {"status": "Failed", "models": [], "error": {"code": error.code, "message": error.message}}
        with self.lock:
            self._require_profile(profile_revision_id)
            self._state["probe"] = {**result, "profile_revision_id": profile_revision_id, "created_at": utc_now(), "generation_tested": False}
            self._persist()
        return self.envelope()

    def _prerequisites(self):
        envelope = self.store.envelope()
        missing = [stage["label"] for stage in envelope["workflow"] if stage["id"] in IMPLEMENTED_STAGES and
                   (stage["review_status"] != "Accepted" or stage["freshness"] == "Stale")]
        if missing:
            raise DomainError("review_prerequisite", "Accept current input checks first: " + ", ".join(missing) + ".", 409)

    def _current_verification_plan(self, envelope, node_id, verification_plans=None):
        """Share source recognition per node for one read, never cache across edits."""
        key = (envelope["revision"]["id"], node_id)
        if verification_plans is not None and key in verification_plans:
            return verification_plans[key]
        result = self._verification_plan(envelope["design"], node_id)
        if verification_plans is not None:
            verification_plans[key] = result
        return result

    def _behavioral_verification_readiness(self, envelope, node_id, verification_plans=None):
        """Explain current capability even before a candidate exists.

        This is a derived read view. In particular, legacy missing-contract
        diagnostics remain untouched in saved generation evidence.
        """
        key = ("readiness", envelope["revision"]["id"], node_id)
        if verification_plans is not None and key in verification_plans:
            return copy.deepcopy(verification_plans[key])
        node = next((item for item in envelope["design"]["nodes"] if item["id"] == node_id), None)
        missing = [] if node is None else [name for name in ("behavior", "test_expectations")
                                          if not isinstance(node.get(name), str) or not node[name].strip()]
        plan, error = self._current_verification_plan(envelope, node_id, verification_plans)
        if node is None or missing:
            result = {"status": "input_required", "available": False,
                      "code": "verification_input_required", "next_action": "review_specification",
                      "needed_user_action": True, "required_fields": missing,
                      "message": ("This node is absent from the current design." if node is None else
                                  "Complete the saved node specification: " + ", ".join(missing) +
                                  ". A matching behavioral checker is also required; entering text does not create one.")}
        elif error:
            # A complete natural-language specification is not itself an
            # executable checker. Do not send users back to enter it again.
            input_error = error["code"].startswith(("invalid_", "missing_"))
            result = {"status": "input_required" if input_error else "implementation_required", "available": False,
                      "code": error["code"] if input_error else "verification_implementation_required",
                      "next_action": "review_specification" if input_error else "implementation_required",
                      "needed_user_action": input_error,
                      "message": ("Review the saved verification inputs. " + error["message"] if input_error else
                                  "The saved specification exists, but HuLLCirq has no supported behavioral checker for this node's current specification. "
                                  "A developer must implement the checker before behavioral verification can proceed. "
                                  "Regenerating RTL or re-entering the same specification will not resolve this."),
                      "source_diagnostic": copy.deepcopy(error)}
        elif not self.compiler:
            result = {"status": "configuration_required", "available": False, "code": "compiler_unavailable",
                      "next_action": "configure_tools", "needed_user_action": True,
                      "message": "A behavioral checker supports this saved specification. Configure the fixed Verilog compiler and simulator before running it."}
        else:
            result = {"status": "ready", "available": True, "code": None, "next_action": "run_verification",
                      "needed_user_action": False,
                      "message": "Behavioral verification is supported for this saved specification. Checks use its frozen inputs; passing applies only to that verification plan."}
        if plan is not None:
            result.update(plan_kind=plan["kind"], template_version=verification_template_version(plan))
        result["stage_id"] = "local_netlist_simulation"
        if verification_plans is not None:
            verification_plans[key] = copy.deepcopy(result)
        return result

    def _saved_verification_inputs(self, parent, revision_id, verification_plans=None):
        """Check eligibility without mutating history or requiring an LLM."""
        verification_plans = verification_plans if verification_plans is not None else {}
        envelope = self.store.envelope()
        if revision_id != envelope["revision"]["id"]:
            raise DomainError("revision_conflict", "Verification must use the current saved input.", 409)
        if (parent["execution_status"] != "Completed" or not parent["rtl"]
                or type(parent.get("finished_at")) is not str):
            raise DomainError("saved_rtl_required", "Finish generation of a complete saved RTL candidate first.", 409)
        if (parent["revision_id"] != revision_id
                or node_fingerprint(envelope["design"], parent["node_id"]) != parent["input_hash"]
                or scheduler_live_source_error(envelope["design"], parent, verification_plans)):
            raise DomainError("stale_job", "This candidate belongs to older saved inputs. Generate a candidate from the current specification first.", 409)
        if (parent.get("rtl_sha256") != text_hash(parent["rtl"])
                or parent.get("raw_content_sha256") != text_hash(parent["raw_content"])
                or extract_rtl(parent["raw_content"]).get("rtl") != parent["rtl"]):
            raise DomainError("candidate_evidence_invalid", "Saved RTL does not match its original generation evidence.", 409)
        self._prerequisites()
        # Envelope rendering shares one plan build per node, even when many
        # historical attempts exist. The cache lives only for that envelope.
        plan, error = self._current_verification_plan(envelope, parent["node_id"], verification_plans)
        if error:
            readiness = self._behavioral_verification_readiness(envelope, parent["node_id"], verification_plans)
            raise DomainError("verification_unavailable", readiness["message"], 409)
        if not self.compiler:
            raise DomainError("compiler_unavailable", "Configure the fixed Verilog compiler and simulator before running saved RTL verification.", 409)
        return plan

    def verify_saved(self, job_id, revision_id):
        """Append an explicit tool run; never edit or resend the saved parent."""
        if any(type(value) is not str or not value for value in (job_id, revision_id)):
            raise DomainError("invalid_request", "Saved RTL verification needs a job and saved revision identifier.")
        self.observe_design()
        with self.lock, self.store.lock:
            if self._batch_reservation is not None:
                raise DomainError("generation_batch_busy", "Finish or cancel sequential generation first.", 409)
            if self._closed:
                raise DomainError("service_stopping", "Generation service is stopping.", 409)
            if self._worker and self._worker.is_alive() or any(job["execution_status"] in ACTIVE for job in self._state["jobs"]):
                raise DomainError("generation_busy", "Finish or cancel the current node generation or verification first.", 409)
            if len(self._state["jobs"]) >= 1000:
                raise DomainError("history_limit", "Archive reviewed evidence before creating more than 1000 jobs.", 409)
            parent = self._stored_job(job_id)
            plan = self._saved_verification_inputs(parent, revision_id)
            fields = ("node_id", "revision_id", "input_hash", "profile_revision_id", "profile", "context", "instruction",
                      "parameters", "origin", "raw_content", "rtl")
            job = {key: copy.deepcopy(parent[key]) for key in fields}
            new_job_id = new_id("generation")
            job.update(id=new_job_id, context_id=saved_verification_hash(parent, plan), operation="verify", base_job_id=None,
                       verification_of_job_id=job_id, provider_request_executed=False,
                       execution_status="Queued", validation_status="Not Checked", review_status="Awaiting Review",
                       raw_reasoning=parent.get("raw_reasoning", ""), diff="", diagnostics=[], checks={}, error=None,
                       events=[], usage=None, finish_reason=None, provider_request_id=None,
                       created_at=utc_now(), finished_at=None, verification_plan=plan, verification_plan_error=None)
            self._state["jobs"].append(job)
            self._event(job, {"type": "saved_rtl_verification_requested", "verification_of_job_id": job_id,
                              "provider_request_executed": False, "rtl_sha256": text_hash(parent["rtl"])})
            self._persist()
            self._cancel = threading.Event()
            self._worker = threading.Thread(target=self._execute, args=(new_job_id, self._cancel), daemon=True,
                                            name="HuLLCirq-saved-RTL-verification")
            self._worker.start()
        return self.envelope()

    def preview(self, node_id, revision_id, operation="generate", base_job_id=None, instruction="", retry_of_job_id=None, *, _allow_budget_overflow=False, _prompt_template_version=None):
        if any(type(value) is not str for value in (node_id, revision_id, operation, instruction)) or len(instruction.encode("utf-8")) > 32768:
            raise DomainError("invalid_request", "Invalid node generation request.")
        if retry_of_job_id is not None and (type(retry_of_job_id) is not str or not retry_of_job_id):
            raise DomainError("invalid_request", "Invalid retry job identifier.")
        if operation not in ("generate", "repair"):
            raise DomainError("unsupported_operation", "Only node generation and repair are available.")
        envelope = self.store.envelope()
        if revision_id != envelope["revision"]["id"]:
            raise DomainError("revision_conflict", "Preview must use the current saved input.", 409)
        previous_rtl, diagnostics, retry_parent = None, None, None
        with self.lock:
            record = copy.deepcopy(self._require_profile())
            if retry_of_job_id is not None:
                retry_parent = copy.deepcopy(self._stored_job(retry_of_job_id))
            if operation == "repair":
                if not instruction.strip():
                    raise DomainError("feedback_required", "Describe the requested RTL repair.")
                base = self._stored_job(base_job_id)
                if base["node_id"] != node_id or not base["rtl"]:
                    raise DomainError("invalid_repair_base", "Repair needs a candidate from this node.")
                previous_rtl, diagnostics = base["rtl"], base["diagnostics"]
            elif base_job_id is not None:
                raise DomainError("invalid_request", "Base job applies to repair only.")
        context_options = {"template_version": retry_parent["context"].get("prompt_template_version") if retry_parent else _prompt_template_version,
                           "reasoning_effort": (retry_parent["context"].get("thinking_control", {}).get("reasoning_effort")
                                                if retry_parent else record["profile"].get("reasoning_effort"))}
        context = build_node_context(envelope["design"], revision_id, node_id, instruction, previous_rtl, diagnostics,
                                     **context_options)
        context["validation_scope"] = LOCAL_RTL_VALIDATION_SCOPE
        if retry_of_job_id is not None:
            with self.lock:
                self._validate_retry_parent(self._stored_job(retry_of_job_id), node_id, revision_id,
                                            context["node_input_hash"], operation, base_job_id, instruction, context)
            context["retry_of_job_id"] = retry_of_job_id
        profile = record["profile"]
        parameters = {"temperature": profile["temperature"], "seed": profile["seed"], "max_tokens": profile["max_output_tokens"]}
        if profile.get("reasoning_effort") is not None:
            parameters["reasoning_effort"] = profile["reasoning_effort"]
        provider_estimate = estimate_message_input(context["messages"])
        result = {**context, "provider_input_estimated_tokens": provider_estimate,
                  "profile_revision_id": record["revision_id"], "parameters": parameters,
                  "operation": operation, "base_job_id": base_job_id,
                  "context_id": request_hash(context, record["revision_id"], parameters, operation, base_job_id)}
        if provider_estimate + profile["max_output_tokens"] > profile["context_window"] and not _allow_budget_overflow:
            raise DomainError("context_budget", "Estimated input plus output exceeds the configured context window; reduce the scope/output or adjust a verified runtime setting.", 422)
        try:
            self._prerequisites(); result["ready_to_generate"] = True; result["gate_reason"] = None
        except DomainError as error:
            result["ready_to_generate"] = False; result["gate_reason"] = error.message
        return result

    @staticmethod
    def _raise_submission_rejection(submission_id, rejection):
        error = DomainError(rejection["code"], rejection["message"], rejection["status"])
        error.generation_start_rejected_before_creation = True
        error.submission_id = submission_id
        raise error

    def submission_receipt(self, submission_id):
        """Read an immutable logical submission without starting or retrying it."""
        _validate_submission_id(submission_id)
        with self.lock:
            record = self._state.get("submissions", {}).get(submission_id)
            return {"version": SUBMISSION_VERSION, "submission_id": submission_id,
                    "status": "not_found" if record is None else "rejected" if record["rejection"] else "started",
                    **(copy.deepcopy(record) if record else {"job_id": None, "rejection": None})}

    def _existing_submission(self, submission_id, request, binding_hash):
        existing = self._state.get("submissions", {}).get(submission_id) if submission_id is not None else None
        if existing is None:
            return None
        if existing["binding_hash"] != binding_hash or existing["request"] != request:
            raise DomainError("submission_conflict", "This submission identity already binds a different frozen request.", 409)
        if existing["rejection"]:
            self._raise_submission_rejection(submission_id, existing["rejection"])
        return existing["job_id"]

    def _reject_submission(self, submission_id, request, binding_hash, error):
        if submission_id is not None and 400 <= error.status < 500:
            rejection = {"code": error.code, "message": error.message, "status": error.status}
            self._state.setdefault("submissions", {})[submission_id] = {"request": request, "binding_hash": binding_hash,
                "job_id": None, "rejection": rejection}
            self._persist()
            self._raise_submission_rejection(submission_id, rejection)
        raise error

    def _submitted_envelope(self, job_id, submission_id, replayed):
        result = self.envelope()
        result["generation_submission"] = {"version": SUBMISSION_VERSION, "submission_id": submission_id,
                                           "job_id": job_id, "replayed": replayed}
        return result

    def start(self, node_id, revision_id, context_id, profile_revision_id, operation="generate", base_job_id=None, instruction="", retry_of_job_id=None, *, _batch_id=None, _batch_context=None, _prompt_template_version=None, submission_id=None, _preflight=None):
        request = _submission_request(node_id, revision_id, context_id, profile_revision_id, operation, base_job_id, instruction, retry_of_job_id)
        if submission_id is not None:
            _validate_submission_id(submission_id)
        binding_hash = _submission_hash(request) if submission_id is not None else None
        # Upstream workers may hold their own lock while reading generation.
        # Never call their preflight checks while holding generation.lock.
        with self.lock:
            existing_id = self._existing_submission(submission_id, request, binding_hash)
            if existing_id is not None:
                return self._submitted_envelope(existing_id, submission_id, True)
        try:
            if _preflight is not None:
                _preflight()
        except DomainError as error:
            with self.lock:
                existing_id = self._existing_submission(submission_id, request, binding_hash)
                if existing_id is not None:
                    return self._submitted_envelope(existing_id, submission_id, True)
                self._reject_submission(submission_id, request, binding_hash, error)
        # Reordered copies must recheck after preflight, before any job commit.
        with self.lock:
            existing_id = self._existing_submission(submission_id, request, binding_hash)
            if existing_id is not None:
                return self._submitted_envelope(existing_id, submission_id, True)
            try:
                self.observe_design()
                self._prerequisites()
                context = self.preview(node_id, revision_id, operation, base_job_id, instruction, retry_of_job_id, _prompt_template_version=_prompt_template_version)
                if self._batch_reservation is not None and self._batch_reservation != _batch_id:
                    raise DomainError("generation_batch_busy", "Finish or cancel sequential generation before a separate model request.", 409)
                if _batch_id is not None:
                    from .generation_batches import pack_batch_context
                    if self._batch_reservation != _batch_id or type(_batch_context) is not dict or _batch_context.get("batch_id") != _batch_id:
                        raise DomainError("invalid_generation_batch", "Sequential context needs its active generation reservation.", 409)
                    context = pack_batch_context(context, [copy.deepcopy(self._stored_job(value)) for value in _batch_context["prior_job_ids"]], self._require_profile(profile_revision_id)["profile"], _batch_context)
                    context["context_id"] = request_hash(context, profile_revision_id, context["parameters"], operation, base_job_id)
                if self._closed:
                    raise DomainError("service_stopping", "Generation service is stopping.", 409)
                record = self._require_profile(profile_revision_id)
                if context["context_id"] != context_id:
                    raise DomainError("context_conflict", "Request context changed; preview it again.", 409)
                if self._worker and self._worker.is_alive() or any(job["execution_status"] in ACTIVE for job in self._state["jobs"]):
                    raise DomainError("generation_busy", "One local generation worker is already active.", 409)
                if len(self._state["jobs"]) >= 1000:
                    raise DomainError("history_limit", "Archive reviewed evidence before creating more than 1000 jobs.", 409)
            except DomainError as error:
                self._reject_submission(submission_id, request, binding_hash, error)
            job_id = new_id("generation")
            job = {"id": job_id, "node_id": node_id, "revision_id": revision_id, "input_hash": context["node_input_hash"],
                   "profile_revision_id": profile_revision_id, "profile": copy.deepcopy(record["profile"]),
                   "context_id": context_id, "context": context, "operation": operation, "base_job_id": base_job_id,
                   "instruction": instruction, "parameters": context["parameters"],
                   "origin": "local_llm" if record["profile"]["execution_location"] == "Local" else "remote_llm",
                   "execution_status": "Queued", "validation_status": "Not Checked", "review_status": "Awaiting Review",
                   "raw_content": "", "raw_reasoning": "", "rtl": None, "diff": "", "diagnostics": [], "checks": {}, "error": None,
                   "events": [], "usage": None, "finish_reason": None, "provider_request_id": None,
                   "created_at": utc_now(), "finished_at": None,
                   "validation_scope": LOCAL_RTL_VALIDATION_SCOPE,
                   "verification_plan": None, "verification_plan_error": None}
            if retry_of_job_id is not None:
                job["retry_of_job_id"] = retry_of_job_id
            if _batch_id is not None:
                job.update(batch_id=_batch_id, batch_index=_batch_context["index"])
            if submission_id is not None:
                job["submission_id"] = submission_id
                self._state.setdefault("submissions", {})[submission_id] = {"request": request, "binding_hash": binding_hash,
                    "job_id": job_id, "rejection": None}
            self._state["jobs"].append(job); self._persist()
            self._cancel = threading.Event()
            self._worker = threading.Thread(target=self._execute, args=(job_id, self._cancel), daemon=True, name="HuLLCirq-node-generation")
            self._worker.start()
            # Failures here follow persistence and never become pre-start proof.
            return self._submitted_envelope(job_id, submission_id, False)

    def _event(self, job, event):
        record = {**event, "sequence": len(job["events"]) + 1, "created_at": utc_now()}
        job["events"].append(record)
        if event.get("type") in ("delta", "content", "partial_answer") and type(event.get("content")) is str:
            job["raw_content"] += event["content"]
        if event.get("type") == "reasoning" and type(event.get("content")) is str:
            job["raw_reasoning"] = job.get("raw_reasoning", "") + event["content"]

    def _execute(self, job_id, cancelled):
        phase = "worker_start"
        def on_event(event):
            nonlocal phase
            previous_phase, phase = phase, "provider_event"
            with self.lock:
                job = self._stored_job(job_id)
                self._event(job, event)
                if event.get("type") in ("delta", "content", "partial_answer", "reasoning") and type(event.get("content")) is str:
                    # Keep every chunk/event in memory, but avoid serializing
                    # all frozen plans and fsyncing the history per token.
                    self._stream_pending_bytes += len(event["content"].encode("utf-8"))
                    if self._stream_pending_bytes >= 8192 or time.monotonic() - self._stream_checkpoint_at >= 0.5:
                        phase = "provider_event_save"
                        self._persist()
                else:
                    # Status, usage, terminal, warning and error events remain
                    # durable immediately. The finished/error path below also
                    # saves the complete exact response and event sequence.
                    phase = "provider_event_save"
                    self._persist()
            phase = previous_phase
        try:
            with self.lock:
                job = self._stored_job(job_id)
                job["execution_status"] = "Running"; self._event(job, {"type": "started"})
                phase = "start_save"
                self._persist()
                phase = "freeze_request"
                frozen = copy.deepcopy(job)
            phase = "provider_request" if frozen["operation"] != "verify" else "saved_verification_source"
            result = ({"execution_status": "Completed", "raw_content": frozen["raw_content"], "error": None}
                      if frozen["operation"] == "verify" else
                      ChatCompletionsClient(frozen["profile"]).generate(frozen["context"]["messages"], frozen["parameters"], cancelled, on_event))
            with self.lock:
                phase = "record_provider_result"
                job = self._stored_job(job_id)
                for field in ("raw_content", "raw_reasoning", "finish_reason", "usage", "provider_request_id", "error"):
                    if field in result:
                        job[field] = result[field]
                status = result.get("execution_status", "Failed")
                if status not in TERMINAL:
                    status = "Failed"
            if status == "Completed" and not cancelled.is_set():
                phase = "extract_rtl"
                extracted = extract_rtl(result["raw_content"])
                rtl = extracted.get("rtl")
                local_interface_only = frozen.get("validation_scope") == LOCAL_RTL_VALIDATION_SCOPE
                check_options = {"interface_only": True} if local_interface_only else {}
                phase = "interface_check" if local_interface_only else "candidate_checks"
                check = check_rtl(rtl, frozen["context"]["interface"], frozen["context"]["interface"]["module_name"], self.compiler, **check_options) if rtl else {
                    "validation_status": "Failed", "diagnostics": [], "checks": {}}
                if local_interface_only:
                    check["checks"]["behavioral"] = {"validation_status": "Not Run", "executed": False,
                        "deferred_to_stage": "local_netlist_simulation", "exit_code": None, "diagnostics": []}
                    check["checks"]["functional_verification"] = {"validation_status": "Not Run", "executed": False,
                        "deferred_to_stage": "local_netlist_simulation"}
                elif check["validation_status"] == "Passed" and frozen.get("verification_plan") is not None:
                    phase = "legacy_behavioral_check"
                    behavior = verify_behavior(rtl, frozen["verification_plan"], self.compiler, cancel_event=cancelled)
                    check["checks"]["behavioral"] = behavior
                    check["checks"]["functional_verification"] = {"validation_status": behavior["validation_status"],
                                                                    "executed": behavior["executed"], "plan": copy.deepcopy(frozen["verification_plan"])}
                    check["diagnostics"].extend(behavior.get("diagnostics", []))
                    check["validation_status"] = behavior["validation_status"]
                else:
                    check["checks"]["behavioral"] = {"validation_status": "Not Run", "executed": False, "exit_code": None,
                        "diagnostics": [{"code": "behavioral_not_run", "severity": "info", "message": "Behavioral verification requires a valid original design contract and passing interface/syntax checks."}]}
                with self.lock:
                    phase = "record_candidate_checks"
                    job = self._stored_job(job_id)
                    job["rtl"] = rtl
                    job["diagnostics"] = extracted.get("diagnostics", []) + check.get("diagnostics", [])
                    job["checks"] = check.get("checks", {})
                    job["validation_status"] = "Failed" if any(d.get("severity") == "error" for d in extracted.get("diagnostics", [])) else check["validation_status"]
                    previous = (frozen["rtl"] if frozen["operation"] == "verify" else
                                self._stored_job(frozen["base_job_id"])["rtl"] if frozen["base_job_id"] else "")
                    phase = "candidate_diff"
                    job["diff"] = compare_rtl(previous or "", rtl or "")
            with self.lock, self.store.lock:
                phase = "finalize"
                job = self._stored_job(job_id)
                job["execution_status"] = "Cancelled" if cancelled.is_set() else status
                if cancelled.is_set():
                    job["validation_status"] = "Not Checked"
                job["finished_at"] = utc_now()
                phase = "observe_design"
                self.observe_design()
                phase = "review_policy"
                self._accept_on_pass(job)
                phase = "finished_event"
                self._event(job, {"type": "finished", "execution_status": job["execution_status"], "validation_status": job["validation_status"]})
                phase = "final_save"
                self._persist()
        except Exception as error:
            details = _exception_diagnostic(error, phase)
            _log_execution_exception(job_id, error, details)
            with self.lock:
                job = self._stored_job(job_id)
                job.update(execution_status="Cancelled" if cancelled.is_set() else "Failed", validation_status="Not Checked",
                           finished_at=utc_now(), error={"code": getattr(error, "code", "generation_error"),
                                                      "message": getattr(error, "message", "Generation or candidate checks failed; partial evidence retained."),
                                                      **details})
                self._event(job, {"type": "error", "code": job["error"]["code"], **details})
                try:
                    self._persist()
                except OSError:
                    # The envelope reports the storage error. Never claim that
                    # an undurable terminal status was successfully recorded.
                    pass

    def job(self, job_id):
        self.observe_design()
        with self.lock:
            return self._decorate(self._stored_job(job_id))

    def cancel(self, job_id):
        with self.lock:
            job = self._stored_job(job_id)
            if job["execution_status"] not in ACTIVE:
                raise DomainError("job_not_active", "Only an active job can be cancelled.", 409)
            self._cancel.set()
            self._event(job, {"type": "cancel_requested", **(
                {"provider_request_executed": False} if job["operation"] == "verify" else
                {"server_inference_stop": "Not guaranteed; client connection will close"})})
            self._persist()
        return self.envelope()

    def review(self, job_id, decision, note, target_stage=None, *, operator=None):
        operator_fields = manual_review_fields(operator)
        if type(note) is not str or decision not in DECISIONS:
            raise DomainError("invalid_decision", "Invalid candidate review decision.")
        self.observe_design()
        with self.lock, self.store.lock:
            self.observe_design()
            job = self._stored_job(job_id)
            if job["execution_status"] in ACTIVE:
                raise DomainError("job_active", "Wait for generation to finish before review.", 409)
            if self._state["node_inputs"].get(job["node_id"]) != job["input_hash"]:
                raise DomainError("stale_job", "Candidate belongs to older node inputs.", 409)
            relevant = [j for j in self._state["jobs"] if j["node_id"] == job["node_id"] and j["input_hash"] == job["input_hash"]]
            if relevant[-1]["id"] != job_id:
                raise DomainError("job_superseded", "Review the latest candidate for this node input.", 409)
            if decision == "accepted":
                self._prerequisites()
                live_error = scheduler_live_source_error(self.store.envelope()["design"], job)
                if live_error:
                    raise DomainError("scheduler_live_source_invalid", live_error["message"], 409)
                scoped_acceptance = job["operation"] != "verify"
                required_behavioral = self.store.review_policy()["mode"] == "accept_on_pass"
                passed = self._s04_passed_checks(job) if scoped_acceptance else (job["execution_status"] == "Completed" and job["validation_status"] == "Passed" and bool(job["rtl"]) and self._passed_checks(job, require_behavioral=required_behavioral))
                if not passed:
                    required = "S04 external-interface" if scoped_acceptance else "interface, syntax, and original-input behavioral" if required_behavioral else "format, interface, and syntax"
                    raise DomainError("verification_failed", f"Completed {required} checks must pass before candidate acceptance.", 409)
                job["review_status"] = "Accepted"
                job["acceptance_epoch"] = self._state["node_epochs"][job["node_id"]]
                job["reviewed_revision_id"] = self.store.envelope()["revision"]["id"]
            else:
                if not note.strip():
                    raise DomainError("feedback_required", "Record the requested correction or return reason.")
                if decision == "return_to_stage" and target_stage not in IMPLEMENTED_STAGES:
                    raise DomainError("invalid_return_stage", "Return to Global Settings, Graph Editor, or Specifications.")
                job["review_status"] = "Changes Requested"
            self._state["reviews"].append({"id": new_id("candidate-review"), "job_id": job_id, "node_id": job["node_id"],
                                           "revision_id": job["revision_id"], "input_hash": job["input_hash"],
                                           "reviewed_revision_id": self.store.envelope()["revision"]["id"],
                                           "decision": decision, "note": note.strip(), "target_stage": target_stage,
                                           "acceptance_epoch": job.get("acceptance_epoch") if decision == "accepted" else None,
                                           **operator_fields, "created_at": utc_now(),
                                           **({"validation_scope": LOCAL_RTL_VALIDATION_SCOPE} if decision == "accepted" and scoped_acceptance else {})})
            self._persist()
        return self.envelope()

    def close(self):
        with self.lock:
            self._closed = True
            self._cancel.set()

    def is_active(self):
        with self.lock:
            return bool(self._batch_reservation is not None or (self._worker and self._worker.is_alive())
                        or any(job["execution_status"] in ACTIVE for job in self._state["jobs"]))

    def node_sources(self):
        """Small authoritative identity view for scheduler guards, no tool plans."""
        self.observe_design()
        with self.lock:
            result = {}
            for node_id, fingerprint in self._state["node_inputs"].items():
                relevant = [job for job in self._state["jobs"] if job["node_id"] == node_id]
                accepted = next((job for job in reversed(relevant) if job["input_hash"] == fingerprint
                                 and job["review_status"] == "Accepted"
                                 and job.get("acceptance_epoch") == self._state["node_epochs"].get(node_id)), None)
                result[node_id] = {"node_id": node_id, "latest_job_id": relevant[-1]["id"] if relevant else None,
                                   "accepted_job_id": accepted["id"] if accepted else None}
            return result

    def reserve_batch(self, identifier):
        with self.lock:
            if self._closed or self.is_active():
                raise DomainError("generation_busy", "Finish or cancel the active generation before starting a sequential batch.", 409)
            self._batch_reservation = identifier

    def release_batch(self, identifier):
        with self.lock:
            if self._batch_reservation == identifier:
                self._batch_reservation = None

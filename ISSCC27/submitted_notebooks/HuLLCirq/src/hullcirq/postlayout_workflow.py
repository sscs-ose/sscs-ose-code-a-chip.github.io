"""S14 history bound to the exact adopted S11/S12/S13 chain.

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
from .lvs_workflow import (EARLIER as LVS_EARLIER, validate_lvs_proof,
                           validate_source_snapshot as validate_lvs_source_snapshot)
from .store import new_id, strict_loads, utc_now, validate_policy_history, validate_policy_review, _replace_with_windows_retry
from .store import _io_path
from .review_actor import REVIEW_ACTORS, manual_review_fields
from .verification import object_hash

STAGE = "post_layout_verification"
POST_ROUTE_SCOPE = "post_route_functional_plus_sta"
ACTIVE = {"Queued", "Running"}
EARLIER = (*LVS_EARLIER, "lvs")
CLEANUP_BLOCKED = "A previous post-layout verification run has unresolved process cleanup. New execution is blocked until its termination is verified."
JSON_ARTIFACTS = {"lvs-record", "drc-record", "layout-record", "source-identity", "runtime-configuration", "verification-plan", "artifact-manifest"}
FILE_IDS = {"input-gds", "input-def", "input-netlist", "input-powered-netlist", "input-sdf", "cell-models", "timed-testbench",
            "public-vectors", "configuration", "source-binding", "tool-versions", "annotation-report", "timing-check-report",
            "simulation-report", "simulation-waveform", "worker-request", "worker-report", "compile-stdout", "compile-stderr",
            "simulation-stdout", "simulation-stderr", "frozen-verification-plan", "source-layout-state", "simulation-plot",
            "event-transcript", "event-manifest", "event-summary", "event-audit-report", "conditional-path-report",
            "native-delay-readback", "native-delay-manifest", "functional-provenance",
            "sta-report", "sta-log", "sta-input-manifest", "sta-constraints", "sta-parasitics", "sta-liberty",
            "completion-report", "functional-testbench", "functional-models", "functional-report"}
REQUIRED_FILES = {"input-netlist", "input-sdf", "cell-models", "timed-testbench", "frozen-verification-plan", "public-vectors",
                  "configuration", "source-binding", "tool-versions", "annotation-report", "timing-check-report", "simulation-report",
                  "worker-request", "worker-report", "simulation-stdout"}
POST_ROUTE_REQUIRED_FILES = {"input-netlist", "functional-models", "functional-testbench", "functional-report",
                            "frozen-verification-plan", "public-vectors", "configuration", "source-binding", "tool-versions",
                            "simulation-stdout", "simulation-waveform", "sta-report", "sta-log", "sta-input-manifest",
                            "sta-constraints", "sta-parasitics", "sta-liberty", "completion-report", "worker-request", "worker-report"}
POST_ROUTE_REQUIRED_CHECKS = ("source_identity", "configuration", "functional", "parasitics", "constraints", "setup_hold", "electrical")
EMPTY_FILES = {"compile-stdout", "compile-stderr", "simulation-stdout", "simulation-stderr"}
LIMITS = ["S14 retains the exact adopted S11 layout, S12 DRC and S13 LVS records and the original GUI verification job.",
          "Each run records its verification method and the timing inputs observed and frozen for that method.",
          "Finite functional checks and extracted static timing do not establish every job, formal equivalence or fabrication readiness.",
          "Routed-netlist functional simulation plus extracted STA is separate from SDF delay simulation; historical Unsupported diagnostics retain their limits.",
          "All mandatory checks for the recorded method must pass before adoption; missing or unsupported checks cannot be accepted."]


def _raw_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _artifact_path(result, entry):
    require(type(entry) is dict and entry.get("id") in FILE_IDS and type(entry.get("relative_path")) is str
            and type(entry.get("sha256")) is str and re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
            and type(entry.get("bytes")) is int and entry["bytes"] >= (0 if entry["id"] in EMPTY_FILES else 1) and type(entry.get("content_type")) is str
            and re.fullmatch(r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+(?:; charset=utf-8)?", entry["content_type"]),
            "postlayout_artifact_invalid", "Post-layout artifacts require fixed IDs, raw hashes and media types; only tool text streams may be empty.")
    relative = PurePosixPath(entry["relative_path"])
    require(not relative.is_absolute() and relative.parts and not any(p in (".", "..") for p in relative.parts)
            and "\\" not in entry["relative_path"] and ":" not in entry["relative_path"]
            and not any(ord(c) < 32 for c in entry["relative_path"])
            and type(result.get("artifacts_directory")) is str and Path(result["artifacts_directory"]).is_absolute(),
            "postlayout_artifact_path_invalid", "post-layout verification files must stay below their recorded absolute result directory.")
    root = Path(result["artifacts_directory"]).resolve(); path = (root / Path(*relative.parts)).resolve()
    require(path.is_relative_to(root) and path != root and path.is_file(), "postlayout_artifact_missing", "The original post-layout verification file is missing or outside its directory.")
    return path


def validate_artifact_manifest(result, passed=False):
    artifacts = result.get("artifacts", [])
    require(type(artifacts) is list, "postlayout_artifact_invalid", "post-layout verification artifacts must be a fixed-ID manifest.")
    ids = set(); paths = set()
    for entry in artifacts:
        path = _artifact_path(result, entry)
        require(entry["id"] not in ids and path not in paths and path.stat().st_size == entry["bytes"] and _raw_hash(path) == entry["sha256"],
                "postlayout_artifact_hash_conflict", "Saved post-layout verification bytes must match their unique raw manifest.")
        ids.add(entry["id"]); paths.add(path)
    required_files = POST_ROUTE_REQUIRED_FILES if result.get("execution_scope") == POST_ROUTE_SCOPE else REQUIRED_FILES
    require(not passed or required_files <= ids, "postlayout_artifact_missing", "Passed post-layout verification requires all fixed reports, inputs, summary and tool versions for its recorded method.")


def validate_postlayout_proof(run, validator):
    validate_source_snapshot(run)
    require(run["evidence_kind"] == "software_qa_fixture" or run.get("verification_supported") is True,
            "postlayout_unsupported", "An unsupported profile cannot be adopted as completed post-layout verification.")
    result = run["checks"]
    require(type(result) is dict and result.get("cleanup_unresolved") is not True, "postlayout_cleanup_unresolved", CLEANUP_BLOCKED)
    post_route = run.get("execution_scope") == POST_ROUTE_SCOPE
    require(post_route == (result.get("execution_scope") == POST_ROUTE_SCOPE)
            and post_route == (run["runtime_configuration"].get("execution_scope") == POST_ROUTE_SCOPE),
            "postlayout_method_conflict", "The run, configuration and executed evidence must retain the same verification method.")
    required_checks = POST_ROUTE_REQUIRED_CHECKS if post_route else ("source_identity", "configuration", "annotation", "functional", "timing_checks")
    fields = ("layout_run_id", "layout_record_sha256", "drc_run_id", "drc_record_sha256", "lvs_run_id", "lvs_record_sha256",
              "input_gds_sha256", "input_netlist_sha256", "configuration_sha256", "verification_plan_sha256", "vector_hash",
              "testbench_sha256", "public_boundary_vector_hash")
    require(result.get("validation_status") == "Passed" and result.get("executed") is True
            and type(result.get("exit_code")) is int and result["exit_code"] == 0 and all(result.get(k) == run[k] for k in fields)
            and type(result.get("commands")) is list and result["commands"]
            and all(type(c) is dict and c.get("executed") is True and c.get("status") == "Completed"
                    and type(c.get("exit_code")) is int and c["exit_code"] == 0 for c in result["commands"])
            and type(result.get("metrics")) is dict and type(result.get("diagnostics")) is list
            and all(result.get("checks", {}).get(name, {}).get("validation_status") == "Passed"
                    for name in required_checks),
            "postlayout_proof_conflict", "Passed post-layout verification requires all mandatory executed checks for its recorded method and unchanged complete source bindings.")
    require(run["evidence_kind"] == "software_qa_fixture" and result.get("software_qa_fixture") is True
            or run["evidence_kind"] == "trusted_fixed_postlayout_execution" and result.get("origin") == "trusted_fixed_postlayout_adapter" and result.get("software_qa_fixture") is not True,
            "postlayout_proof_conflict", "Actual post-layout verification and explicit software doubles must retain distinct origins.")
    validate_artifact_manifest(result, True)
    require(validator(result, run["lvs_snapshot"], run["drc_snapshot"], run["layout_snapshot"], run["runtime_configuration"]) is None,
            "postlayout_proof_conflict", "The fixed post-layout validator must explicitly finish without a mismatch.")


def _immutable_source(record):
    return {k: v for k, v in record.items() if k not in ("record_hash", "review_status", "acceptance_epoch", "diagnostics")}


def validate_source_snapshot(run):
    """Pure frozen triple-source/configuration/job bindings, usable in archives."""
    layout, drc, lvs, identity = (run[k] for k in ("layout_snapshot", "drc_snapshot", "lvs_snapshot", "source_identity"))
    validate_lvs_source_snapshot(lvs)
    inputs = run["source_inputs"]
    require(type(inputs) is dict and {"gds", "def", "netlist", "powered_netlist"} <= set(inputs)
            and all(type(e) is dict and type(e.get("sha256")) is str and re.fullmatch(r"[0-9a-f]{64}", e["sha256"])
                    and type(e.get("bytes")) is int and e["bytes"] > 0 for e in inputs.values())
            and all(object_hash(inputs[k]) == object_hash(lvs["source_inputs"][k]) for k in ("gds", "def", "netlist", "powered_netlist"))
            and object_hash(identity.get("source_inputs")) == object_hash(inputs)
            and inputs["gds"]["sha256"] == run["input_gds_sha256"] == drc["input_gds_sha256"] == lvs["input_gds_sha256"]
            and inputs["netlist"]["sha256"] == run["input_netlist_sha256"] == lvs["input_netlist_sha256"],
            "postlayout_source_conflict", "Post-layout inputs must retain exact S13-bound GDS/DEF/mapped/powered circuit and separately observed timing inputs.")
    for name, record in (("layout", layout), ("drc", drc), ("lvs", lvs)):
        adoption = run[name + "_adoption"]
        prefix = "physical" if name == "layout" else name
        require(object_hash(record) == run[name + "_record_sha256"]
                and record.get("record_hash") == object_hash({k: v for k, v in record.items() if k != "record_hash"})
                and record["id"] == run[name + "_run_id"] and record["revision_id"] == run["revision_id"]
                and record["execution_status"] == "Completed" and record["validation_status"] == "Passed" and record["review_status"] == "Accepted"
                and identity.get(name + "_run_id") == record["id"] and identity.get(name + "_record_sha256") == object_hash(record)
                and identity.get(prefix + "_source_key") == record["source_key"]
                and type(identity.get(prefix + "_source_epoch")) is int
                and identity[prefix + "_source_epoch"] == record["source_epoch_at_start"] == record["acceptance_epoch"]
                and object_hash(identity.get(name + "_adoption")) == object_hash(adoption)
                and adoption.get("run_id") == record["id"] and adoption.get("decision") == "accepted"
                and adoption.get("source_key") == record["source_key"] and type(adoption.get("acceptance_epoch")) is int
                and adoption["acceptance_epoch"] == record["acceptance_epoch"],
                "postlayout_source_conflict", "Frozen post-layout identity must bind each exact adopted record, authoritative adoption and source epoch.")
    require(lvs["layout_record_sha256"] == drc["layout_record_sha256"] == object_hash(layout)
            and lvs["drc_record_sha256"] == object_hash(drc)
            and object_hash(lvs["layout_snapshot"]) == object_hash(drc["layout_snapshot"]) == object_hash(layout)
            and object_hash(lvs["drc_snapshot"]) == object_hash(drc)
            and object_hash(run["runtime_configuration"]) == run["configuration_sha256"] == identity.get("configuration_sha256")
            and run["source_key"] == object_hash(identity) and identity.get("revision_id") == run["revision_id"],
            "postlayout_source_conflict", "S11/S12/S13 must retain one exact unchanged adopted chain, configuration and GUI revision.")
    plan = run["verification_plan"]
    require(type(plan) is dict and object_hash(plan) == run["verification_plan_sha256"] == layout["verification_plan_sha256"]
            and object_hash(plan) == object_hash(layout["verification_plan"])
            and identity.get("verification_plan_sha256") == run["verification_plan_sha256"]
            and all(run[k] == plan[k] == layout[k] and identity.get(k) == run[k]
                    for k in ("vector_hash", "testbench_sha256", "public_boundary_vector_hash")),
            "postlayout_source_conflict", "Post-layout verification must preserve the original GUI job, finite frozen plan, base testbench and public vector hashes.")


def _source_inputs(layout, configuration):
    from .postlayout_tools import source_inputs
    return source_inputs(layout, configuration)


class PostLayoutWorkflowManager(ObservedState):
    def __init__(self, store, lvs_workflow, tool_configuration=None, postlayout_runner=None, postlayout_validator=None,
                 compiler_configuration=None, configuration_path=None, profile_working_directory=None):
        require((postlayout_runner is None) == (postlayout_validator is None), "postlayout_adapter_invalid", "An injected runner needs its explicit proof validator.")
        self.store, self.lvs_workflow = store, lvs_workflow
        self.drc_workflow = lvs_workflow.drc_workflow
        self.physical_workflow = lvs_workflow.physical_workflow
        self._explicit_configuration = tool_configuration is not None
        self._compiler_configuration = copy.deepcopy(compiler_configuration)
        self._configuration_path = Path(configuration_path).absolute() if configuration_path is not None else None
        self._profile_working_directory = Path(profile_working_directory).absolute() if profile_working_directory is not None else None
        self._profile_directory = self._configuration_path.parent.resolve() if self._configuration_path is not None else None
        require(self._configuration_path is None or self._profile_working_directory is not None
                and self._profile_working_directory.parent.resolve() == self._profile_directory,
                "postlayout_profile_path_invalid", "The host-managed S14 profile and run directory must share one fixed system scope.")
        self._configuration_error = None
        if not self._explicit_configuration and self._configuration_path is not None and _io_path(self._configuration_path).exists():
            try:
                require(_io_path(self._configuration_path).is_file() and not _io_path(self._configuration_path).is_symlink()
                        and self._configuration_path.parent.resolve() == self._profile_directory,
                        "postlayout_profile_path_invalid", "The saved fixed S14 profile must be an ordinary file in its host-managed system scope.")
                loaded = strict_loads(_io_path(self._configuration_path).read_text(encoding="utf-8"))
                require(type(loaded) is dict, "postlayout_configuration_invalid", "The saved fixed S14 profile must be a JSON object.")
                from . import postroute_tools
                require(loaded.get("execution_scope") == POST_ROUTE_SCOPE
                        and loaded.get("profile_version") in (postroute_tools.PROFILE_V2, postroute_tools.PROFILE_V3, postroute_tools.PROFILE_V4)
                        and object_hash(loaded.get("compiler")) == object_hash(self._compiler_configuration)
                        and type(loaded.get("working_directory")) is str
                        and Path(loaded["working_directory"]).resolve() == self._profile_working_directory.resolve(),
                        "postlayout_profile_scope_conflict",
                        "The saved S14 profile does not match this system's fixed run directory and current server compiler. Prepare it again for this system.")
                capability = postroute_tools.runtime_descriptor(loaded)
                require(capability.get("available") is True and capability.get("verification_supported") is True
                        and capability.get("execution_scope") == POST_ROUTE_SCOPE,
                        "postlayout_configuration_invalid",
                        "The saved fixed S14 profile or its runtime inputs are unavailable. Prepare it again after checking the public environment setup.")
                tool_configuration = loaded
            except (DomainError, OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
                self._configuration_error = {"code": getattr(error, "code", "postlayout_configuration_invalid"),
                                             "message": getattr(error, "message", "The saved fixed S14 profile is unreadable or malformed; its bytes were preserved.")}
        self.tool_configuration = copy.deepcopy(tool_configuration)
        self._injected = postlayout_runner is not None; self._runner, self._validator = postlayout_runner, postlayout_validator
        self.path = store.state_path.parent / "postlayout_workflow.json"; self.lock = threading.RLock()
        self._worker = None; self._cancel = threading.Event(); self._closed = False; self._storage_error = None
        self._state = {"postlayout_workflow_store_version": "0.1", "runs": [], "reviews": [], "source_key": None, "source_epoch": 0, "source_transitions": []}
        if _io_path(self.path).exists():
            try: self._state = strict_loads(_io_path(self.path).read_text(encoding="utf-8")); self._validate_saved()
            except (DomainError, OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                raise DomainError("invalid_postlayout_workflow_store", "post-layout verification history is inconsistent; its original bytes are preserved.", 500) from error
        self._committed = copy.deepcopy(self._state)
        interrupted = False
        for run in self._state["runs"]:
            if run["execution_status"] in ACTIVE:
                run.update(execution_status="Interrupted", validation_status="Not Checked", finished_at=utc_now(),
                    error={"code": "service_restarted", "message": "Interrupted post-layout verification retained; no tool was resent. Process termination requires verification."})
                run["checks"]["cleanup_unresolved"] = True; interrupted = True
        if interrupted: self._persist()

    def _adapter(self):
        if self._runner is None:
            from .postlayout_tools import run_postlayout, validate_postlayout_result
            return run_postlayout, validate_postlayout_result
        return self._runner, self._validator

    def _capability(self):
        if self._injected:
            return {"available": type(self.tool_configuration) is dict, "reason": "Explicit software QA adapter; no actual EDA evidence.",
                    "verification_supported": False, "execution_scope": "software_qa_fixture"}
        from .postlayout_tools import runtime_descriptor
        return runtime_descriptor(self.tool_configuration)

    def _profile_prepare_available(self):
        return (not self._injected and not self._explicit_configuration
                and type(self._compiler_configuration) is dict
                and self._configuration_path is not None and self._profile_working_directory is not None)

    def _profile_update_available(self):
        from .postroute_tools import PROFILE_V2
        return (self._profile_prepare_available() and type(self.tool_configuration) is dict
                and self.tool_configuration.get("execution_scope") == POST_ROUTE_SCOPE
                and self.tool_configuration.get("profile_version") == PROFILE_V2)

    def _profile_prepare_needed(self):
        return (self._profile_prepare_available() and type(self.tool_configuration) is dict
                and object_hash(self.tool_configuration.get("physical_runtime"))
                    != object_hash(self.physical_workflow.tool_configuration))

    def _profile_preparation_sources(self):
        """Read-only candidate chain for explicit preparation, not execution.

        An installed profile can be available yet bound to an older physical
        runtime. Its execution-source rejection must not hide the independent
        current adopted chain needed to explicitly prepare its replacement.
        Actual preparation still revalidates every source proof and artifact.
        """
        if not self._profile_prepare_available():
            return {"available": False, "blocked_reason": "GUI-managed S14 profile preparation is unavailable."}
        try:
            with self._source_locks():
                current, _, records, _ = self._adopted_sources_locked()
                layout = records["layout"]
                return {"available": True,
                        "scope": "adopted_source_chain_for_explicit_profile_preparation_only",
                        "revision_id": current["revision"]["id"], "source_revision_id": layout["revision_id"],
                        **{name + "_run_id": record["id"] for name, record in records.items()},
                        **{name + "_record_hash": record["record_hash"] for name, record in records.items()},
                        "physical_runtime_sha256": object_hash(layout["runtime_configuration"]),
                        "verification_plan_sha256": layout["verification_plan_sha256"],
                        "settings_sha256": layout["settings_sha256"], "blocked_reason": None}
        except (DomainError, OSError, ValueError, KeyError, TypeError) as error:
            return {"available": False,
                    "blocked_reason": getattr(error, "message", "The current adopted source chain is unavailable for profile preparation.")}

    def _adapter_contract_for(self, layout):
        from . import postroute_generic
        plan, settings = layout["verification_plan"], layout["settings"]
        with self.lock:
            saved = next((copy.deepcopy(record) for record in reversed(self._state.get("adapter_contracts", []))
                          if record["verification_plan_sha256"] == object_hash(plan)
                          and record["settings_sha256"] == object_hash(settings)), None)
        if saved is not None:
            return postroute_generic.validate_contract(plan, settings, saved["contract"]), "saved_gui_contract"
        return postroute_generic.derive_contract(plan, settings), "derived_saved_testbench"

    def _adapter_metadata(self):
        """Read-only GUI metadata; never hold our result lock before S11."""
        from . import postroute_generic
        with self.physical_workflow.lock:
            runs = self.physical_workflow._state["runs"]
            layout = ({key: copy.deepcopy(runs[-1][key]) for key in
                       ("id", "verification_plan", "verification_plan_sha256", "settings")} if runs else None)
        result = {"adapter_contract": None, "adapter_contract_sha256": None,
                  "adapter_contract_editable": self._profile_prepare_available(),
                  "adapter_contract_required": False, "adapter_contract_reason": None,
                  "adapter_contract_fields": list(postroute_generic.FIELDS), "adapter_contract_source": None,
                  "adapter_contract_original": None}
        if layout is None:
            result.update(adapter_contract_required=True, adapter_contract_reason="Adopt an S11 layout with its saved external-port verification plan first.")
            return result
        plan, settings = layout["verification_plan"], layout["settings"]
        if plan.get('kind') == 'generic_cycle_vectors':
            result.update(adapter_contract_fields=['version'], adapter_contract_editable=False)
        result["adapter_contract_original"] = {"testbench": plan.get("testbench"),
            "expected_outputs": copy.deepcopy(plan.get('reference_trace') if plan.get('kind') == 'generic_cycle_vectors'
                                               else (plan.get("recipe") or {}).get("expected_outputs")),
            "clock_period_ns": settings.get("clock_period_ns"), "top_module": settings.get("top_module"),
            "verification_plan_sha256": layout["verification_plan_sha256"],
            "verification_profile": plan.get('kind'), "settings_sha256": object_hash(settings)}
        try:
            contract, origin = self._adapter_contract_for(layout)
            result.update(adapter_contract=contract, adapter_contract_sha256=object_hash(contract), adapter_contract_source=origin)
        except DomainError as error:
            result.update(adapter_contract_required=True, adapter_contract_reason=error.message)
        return result

    def save_adapter_contract(self, layout_run_id, drc_run_id, lvs_run_id, revision_id, contract):
        require(self._profile_prepare_available(), "postlayout_adapter_contract_unavailable",
                "Adapter metadata is editable only for a host-managed S14 profile.", 409)
        require(all(type(value) is str for value in (layout_run_id, drc_run_id, lvs_run_id, revision_id)),
                "postlayout_adapter_contract", "Select the exact current saved source chain.")
        with self._source_locks():
            current, _, records, _ = self._adopted_sources_locked()
            require((layout_run_id, drc_run_id, lvs_run_id, revision_id) ==
                    (records["layout"]["id"], records["drc"]["id"], records["lvs"]["id"], current["revision"]["id"]),
                    "postlayout_source_conflict", "Save adapter metadata only for the exact current adopted S11/S12/S13 chain.")
            from . import postroute_generic
            layout = records["layout"]
            validated = postroute_generic.validate_contract(layout["verification_plan"], layout["settings"], contract)
            with self.lock:
                require(not self._closed and not self.is_active() and not (self._worker and self._worker.is_alive()),
                        "postlayout_busy", "Wait for S14 execution and process cleanup before saving adapter metadata.", 409)
                record = {"id": new_id("postlayout-adapter"), "layout_run_id": layout_run_id,
                          "drc_run_id": drc_run_id, "lvs_run_id": lvs_run_id, "revision_id": revision_id,
                          "verification_plan_sha256": object_hash(layout["verification_plan"]),
                          "settings_sha256": object_hash(layout["settings"]), "contract": validated,
                          "contract_sha256": object_hash(validated), "created_at": utc_now(), "actor": "gui_operator"}
                self._state.setdefault("adapter_contracts", []).append(record)
                self._persist()
        return self.envelope()

    def _write_profile(self, configuration):
        path = self._configuration_path
        require(path is not None and not _io_path(path).is_symlink() and path.parent.resolve() == self._profile_directory,
                "postlayout_profile_path_invalid",
                "The host-managed S14 profile path is unavailable or linked.")
        _io_path(path.parent).mkdir(parents=True, exist_ok=True)
        name = None
        try:
            descriptor, name = tempfile.mkstemp(prefix=".postlayout-profile-", suffix=".tmp", dir=_io_path(path.parent))
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(configuration, ensure_ascii=False, allow_nan=False, indent=2) + "\n")
                handle.flush(); os.fsync(handle.fileno())
            _replace_with_windows_retry(name, _io_path(path))
        finally:
            if name and _io_path(name).exists(): _io_path(name).unlink()

    @contextmanager
    def _source_locks(self):
        with self.lvs_workflow._source_locks():
            with self.lvs_workflow.lock: yield

    def _adopted_sources_locked(self):
        managers = {"layout": self.physical_workflow, "drc": self.drc_workflow, "lvs": self.lvs_workflow}
        current = self.store.envelope()
        self.lvs_workflow.observe_design()
        require(all(m._state["runs"] for m in managers.values()), "postlayout_sources_not_adopted", "Adopt the latest current S11, S12 and S13 before post-layout verification.")
        records = {name: m._state["runs"][-1] for name, m in managers.items()}
        require(all(not m.is_active() and all(m._decorate(records[name])[k] == v for k, v in
                (("execution_status", "Completed"), ("validation_status", "Passed"), ("review_status", "Accepted"), ("freshness", "Current")))
                for name, m in managers.items()),
                "postlayout_sources_not_adopted", "Latest S11, S12 and S13 must remain Completed, Passed, Accepted and Current with resolved cleanup.")
        layout, drc, lvs = (records[k] for k in ("layout", "drc", "lvs"))
        require(self._injected or layout.get("evidence_kind") in ("trusted_fixed_tool_execution", "trusted_saved_tool_revalidation")
                and drc.get("evidence_kind") == "trusted_fixed_drc_execution" and lvs.get("evidence_kind") == "trusted_fixed_lvs_execution",
                "postlayout_fixture_rejected", "Actual post-layout verification requires actual trusted S11/S12/S13 evidence.")
        require(all(r["revision_id"] == layout["revision_id"] for r in records.values())
                and lvs["layout_record_sha256"] == drc["layout_record_sha256"] == object_hash(layout)
                and lvs["drc_record_sha256"] == object_hash(drc),
                "postlayout_source_conflict", "S11/S12/S13 must refer to this exact unchanged adopted chain and original GUI revision.")
        same_source_design(self.store, layout["revision_id"], current)
        adoptions = {}
        for name, manager in managers.items():
            reviews = [r for r in manager._state["reviews"] if r["run_id"] == records[name]["id"]]
            require(reviews and reviews[-1]["decision"] == "accepted", "postlayout_adoption_conflict", "Retain all authoritative current S11/S12/S13 adoptions.")
            adoptions[name] = copy.deepcopy(reviews[-1])
        return current, managers, records, adoptions

    def _source_state(self):
        managers = {"layout": self.physical_workflow, "drc": self.drc_workflow, "lvs": self.lvs_workflow}
        with self._source_locks():
            current = self.store.envelope()
            try:
                current, managers, records, adoptions = self._adopted_sources_locked()
                layout = records["layout"]
                from . import postroute_tools
                if (self.tool_configuration or {}).get("profile_version") != postroute_tools.PROFILE_V4:
                    with self.lock:
                        explicit_contract = any(record["verification_plan_sha256"] == object_hash(layout["verification_plan"])
                            and record["settings_sha256"] == object_hash(layout["settings"]) for record in self._state.get("adapter_contracts", []))
                    require(not explicit_contract, "postlayout_adapter_profile_stale",
                            "Saved adapter metadata requires explicit preparation of the generic S14 profile before execution.")
                if (self.tool_configuration or {}).get("profile_version") == postroute_tools.PROFILE_V4:
                    contract, _ = self._adapter_contract_for(layout)
                    require(object_hash(contract) == self.tool_configuration.get("functional_adapter", {}).get("contract_sha256"),
                            "postlayout_adapter_profile_stale", "Adapter metadata changed. Explicitly prepare the fixed S14 profile again before execution.")
                inputs = _source_inputs(layout, self.tool_configuration)
                identity = {"revision_id": layout["revision_id"], "source_inputs": copy.deepcopy(inputs),
                            "configuration_sha256": object_hash(self.tool_configuration),
                            "verification_plan_sha256": layout["verification_plan_sha256"],
                            **{k: layout[k] for k in ("vector_hash", "testbench_sha256", "public_boundary_vector_hash")}}
                source = {"identity": identity, "inputs": copy.deepcopy(inputs)}
                for name, record in records.items():
                    manager = managers[name]; prefix = "physical" if name == "layout" else name
                    identity.update({name + "_run_id": record["id"], name + "_record_sha256": object_hash(record),
                                     prefix + "_source_key": manager._state["source_key"], prefix + "_source_epoch": manager._state["source_epoch"],
                                     name + "_adoption": copy.deepcopy(adoptions[name])})
                    source[name] = copy.deepcopy(record); source[name + "_adoption"] = copy.deepcopy(adoptions[name])
                return object_hash(identity), source, None
            except (DomainError, OSError, ValueError, KeyError, TypeError) as error:
                code = getattr(error, "code", "postlayout_source_unavailable")
                message = getattr(error, "message", "The saved S14 source or runtime inputs are missing, unreadable or inconsistent. Refresh the saved source chain and prepare its fixed profile again.")
                state = {name: {"source_key": m._state["source_key"], "source_epoch": m._state["source_epoch"],
                                 "runs": [[r["id"], r["record_hash"]] for r in m._state["runs"]], "reviews": m._state["reviews"]}
                         for name, m in managers.items()}
                key = object_hash({"revision_id": current["revision"]["id"], "sources": state,
                                   "configuration_sha256": object_hash(self.tool_configuration), "blocked": code})
                return key, None, {"code": code, "message": message}

    def prepare_profile(self, layout_run_id, drc_run_id, lvs_run_id, revision_id):
        require(all(type(value) is str for value in (layout_run_id, drc_run_id, lvs_run_id, revision_id)),
                "postlayout_profile_request_invalid", "S14 profile preparation requires the current saved revision and exact S11/S12/S13 IDs.")
        require(self._profile_prepare_available(), "postlayout_profile_prepare_unavailable",
                "This service cannot build a GUI-managed S14 profile. Preserve an explicit command-line profile or restart with the pinned compiler configuration.", 409)
        with self._source_locks():
            current, _, records, _ = self._adopted_sources_locked()
            layout, drc, lvs = (records[name] for name in ("layout", "drc", "lvs"))
            require((layout_run_id, drc_run_id, lvs_run_id, revision_id) ==
                    (layout["id"], drc["id"], lvs["id"], current["revision"]["id"]),
                    "postlayout_source_conflict", "Prepare S14 only for the exact latest adopted layout, DRC, LVS and saved GUI revision.", 409)
            self._validate_sources(lvs, drc, layout)
            physical = self.physical_workflow
            require(not any(r["execution_status"] in ACTIVE for manager, field in
                    ((physical.global_generation, "jobs"), (physical.global_generation.generation, "jobs"),
                     (physical.global_generation.workflow, "runs"), (physical.global_workflow, "runs")) for r in manager._state[field]),
                    "postlayout_peer_busy", "Wait for model or earlier tool execution before preparing S14.", 409)
            with self.lock:
                require(not self._closed and not self.is_active() and not (self._worker and self._worker.is_alive()),
                        "postlayout_busy", "Finish or cancel post-layout verification before preparing its fixed profile.", 409)
            require(not self._profile_working_directory.is_symlink()
                    and self._profile_working_directory.parent.resolve() == self._profile_directory,
                    "postlayout_profile_path_invalid", "The host-managed S14 run directory is linked or outside this system scope.")
            self._profile_working_directory.mkdir(parents=True, exist_ok=True)
            require(self._profile_working_directory.resolve() == (self._profile_directory / "runs").resolve(),
                    "postlayout_profile_path_invalid", "The host-managed S14 run directory changed while preparing the profile.")
            from . import postroute_tools
            # Old standard plans retain their historical default v3 recipe.
            # New plan kinds and explicitly saved metadata use the independently
            # source-bound generic v4 adapter, without a circuit-name allowlist.
            with self.lock:
                explicit_contract = any(record["verification_plan_sha256"] == object_hash(layout["verification_plan"])
                    and record["settings_sha256"] == object_hash(layout["settings"]) for record in self._state.get("adapter_contracts", []))
            generic = layout["verification_plan"].get("kind") not in postroute_tools.SUPPORTED_PLAN_KINDS or explicit_contract
            contract = self._adapter_contract_for(layout)[0] if generic else None
            candidate = postroute_tools.prepare_configuration(layout, self._compiler_configuration,
                self._profile_working_directory, **({"adapter_contract": contract} if generic else {}))
            require(type(candidate) is dict, "postlayout_configuration_invalid", "Fixed S14 profile preparation did not return a configuration object.")
            capability = postroute_tools.runtime_descriptor(candidate)
            require(capability.get("available") is True and capability.get("verification_supported") is True
                    and capability.get("execution_scope") == POST_ROUTE_SCOPE,
                    "postlayout_runtime_unavailable", capability.get("reason") or "The fixed S14 profile did not pass its read-only runtime checks.")
            _source_inputs(layout, candidate)
            self._write_profile(candidate)
            with self.lock:
                self.tool_configuration = copy.deepcopy(candidate)
                self._configuration_error = None
        self.observe_design()
        return self.envelope()

    def observe_design(self):
        key, source, error = self._source_state()
        with self.lock:
            if key != self._state["source_key"]:
                self._state["source_key"] = key; self._state["source_epoch"] += 1
                self._state["source_transitions"].append({"epoch": self._state["source_epoch"], "source_key": key, "created_at": utc_now()}); persist_observation(self)
        return key, source, error

    def _run(self, identifier):
        run = next((r for r in self._state["runs"] if r["id"] == identifier), None)
        require(run is not None, "postlayout_run_not_found", "post-layout verification execution does not exist.", 404)
        return run

    def _decorate(self, run):
        value = copy.deepcopy(run); current = run["source_key"] == self._state["source_key"] and run["source_epoch_at_start"] == self._state["source_epoch"]
        value["freshness"] = "Current" if current else "Stale"
        if value["review_status"] == "Accepted" and (not current or run.get("acceptance_epoch") != self._state["source_epoch"]): value["review_status"] = "Awaiting Review"
        value["artifacts"] = [{**entry, "url": "/api/artifacts/postlayout-workflow/" + run["id"] + "/" + entry["id"]} for entry in run["checks"].get("artifacts", [])]
        resolution = self._valid_cleanup_resolution(run)
        value["cleanup_resolution"] = copy.deepcopy(resolution)
        value["cleanup_resolution_available"] = (run["checks"].get("cleanup_unresolved") is True
            and run["execution_status"] not in ACTIVE and resolution is None
            and run.get("evidence_kind") == "trusted_fixed_postlayout_execution"
            and run.get("execution_scope") == POST_ROUTE_SCOPE
            and not (self._worker and self._worker.is_alive()))
        return value

    @memoized_envelope
    def envelope(self):
        _, source, error = self.observe_design(); capability = self._capability()
        adapter_metadata = self._adapter_metadata()
        preparation_sources = self._profile_preparation_sources() if source is None else None
        with self.lock:
            runs = [self._decorate(r) for r in self._state["runs"]]; latest = runs[-1] if runs else None
            unresolved = self._cleanup_unresolved(); tool_ready = capability.get("available") is True
            return {"postlayout_workflow": {"implemented": True, "stage_id": STAGE, "runs": runs, "reviews": copy.deepcopy(self._state["reviews"]),
                "execution_submissions": submission_view(self), "submission_protocol_version": PROTOCOL_VERSION,
                "latest_run_id": latest["id"] if latest else None, "accepted_run_id": latest["id"] if latest and latest["review_status"] == "Accepted" and latest["freshness"] == "Current" else None,
                "ready": source is not None and tool_ready and not unresolved, "blocked_reason": CLEANUP_BLOCKED if unresolved else error["message"] if error else None if tool_ready else capability.get("reason"),
                "tool_ready": tool_ready, "tool_blocked_reason": None if tool_ready else capability.get("reason"),
                "verification_supported": capability.get("verification_supported") is True,
                "verification_blocked_reason": capability.get("verification_blocked_reason"),
                "execution_scope": capability.get("execution_scope", "compatibility_preflight_only"),
                "profile_prepare_available": self._profile_prepare_available(),
                "profile_preparation_sources": preparation_sources,
                "profile_update_available": self._profile_update_available(),
                "profile_prepare_needed": self._profile_prepare_needed() or self._adapter_profile_prepare_needed(adapter_metadata),
                "profile_configuration_source": "command_line" if self._explicit_configuration else "workspace_profile" if self.tool_configuration is not None else None,
                "profile_configuration_error": copy.deepcopy(self._configuration_error),
                "configuration_sha256": object_hash(self.tool_configuration), "runtime_configuration": copy.deepcopy(self.tool_configuration),
                "layout_run_id": source["layout"]["id"] if source else None, "drc_run_id": source["drc"]["id"] if source else None,
                "lvs_run_id": source["lvs"]["id"] if source else None,
                "verification_plan_sha256": source["layout"]["verification_plan_sha256"] if source else None,
                "source_inputs": copy.deepcopy(source["inputs"]) if source else None,
                "input_gds_sha256": source["inputs"]["gds"]["sha256"] if source else None,
                "input_netlist_sha256": source["inputs"]["netlist"]["sha256"] if source else None,
                "input_powered_netlist_sha256": source["inputs"]["powered_netlist"]["sha256"] if source else None,
                "cleanup_resolutions": copy.deepcopy(self._state.get("cleanup_resolutions", [])),
                "storage_error": copy.deepcopy(self._storage_error), "limits": list(LIMITS), **adapter_metadata}}

    def _adapter_profile_prepare_needed(self, metadata):
        configuration = self.tool_configuration
        if type(configuration) is not dict or not self._profile_prepare_available():
            return False
        original = metadata.get('adapter_contract_original') or {}
        if configuration.get('profile_version') != 'hullcirq-postroute-functional-sta-v4':
            return metadata.get('adapter_contract_source') == 'saved_gui_contract' or original.get('verification_profile') == 'generic_cycle_vectors'
        descriptor = configuration.get('functional_adapter') or {}
        return (metadata.get('adapter_contract_sha256') != descriptor.get('contract_sha256')
                or original.get('verification_plan_sha256') != descriptor.get('verification_plan_sha256')
                or original.get('settings_sha256') != descriptor.get('settings_sha256'))

    def run(self, identifier):
        self.observe_design()
        with self.lock: return self._decorate(self._run(identifier))

    def _valid_cleanup_resolution(self, run):
        from .postlayout_cleanup import validate_resolution
        for resolution in reversed(self._state.get("cleanup_resolutions", [])):
            if resolution.get("run_id") != run["id"]:
                continue
            try:
                validate_resolution(run, resolution)
                return resolution
            except (DomainError, OSError, ValueError, KeyError, TypeError):
                return None
        return None

    def _cleanup_unresolved(self):
        return any(r["checks"].get("cleanup_unresolved") is True and self._valid_cleanup_resolution(r) is None
                   for r in self._state["runs"])

    def verify_saved_termination(self, identifier):
        from .postlayout_cleanup import termination_evidence, execution_hash
        with self.lock:
            require(not self._closed and not (self._worker and self._worker.is_alive())
                    and not any(r["execution_status"] in ACTIVE for r in self._state["runs"]),
                    "postlayout_busy", "Wait for the actual S14 worker to finish before verifying saved termination.", 409)
            run = self._run(identifier)
            require(not any(r["id"] != identifier and r["checks"].get("cleanup_unresolved") is True
                            and self._valid_cleanup_resolution(r) is None for r in self._state["runs"]),
                    "postlayout_cleanup_unresolved", "Another S14 attempt still has unresolved process cleanup.", 409)
            require(self._valid_cleanup_resolution(run) is None,
                    "postlayout_cleanup_already_verified", "This saved process termination has already been verified.", 409)
            evidence = termination_evidence(copy.deepcopy(run))
            resolution = {"id": new_id("postlayout-cleanup-resolution"), "run_id": identifier,
                "original_run_record_sha256": run["record_hash"], "execution_sha256": execution_hash(run),
                "actor": "gui_operator", "provenance": {"interface": "GUI", "action": "verify_saved_process_termination"},
                "created_at": utc_now(), "evidence": evidence}
            resolution["record_hash"] = object_hash(resolution)
            self._state.setdefault("cleanup_resolutions", []).append(resolution)
            self._persist()
        return self.envelope()

    def is_active(self):
        with self.lock: return self._cleanup_unresolved() or any(r["execution_status"] in ACTIVE for r in self._state["runs"])

    def _validate_sources(self, lvs, drc, layout):
        self.lvs_workflow._validate_sources(drc, layout)
        validate_lvs_source_snapshot(lvs)
        validate_lvs_proof(lvs, self.lvs_workflow._adapter()[1])

    def start(self, stage_id, layout_run_id, drc_run_id, lvs_run_id, revision_id=None, *, _submission=None):
        require(stage_id == STAGE and type(layout_run_id) is str and type(drc_run_id) is str and type(lvs_run_id) is str and (revision_id is None or type(revision_id) is str),
                "postlayout_request_invalid", "S14 requires the exact saved adopted S11, S12 and S13 IDs.")
        capability = self._capability()
        require(capability.get("available") is True, "postlayout_runtime_unavailable", capability.get("reason") or "Configure the pinned post-layout verification runtime.")
        with self._source_locks():
            key, source, error = self.observe_design()
            require(source is not None, "postlayout_sources_not_current", error["message"] if error else "Adopt current S11, S12 and S13 first.")
            layout = source["layout"]; drc = source["drc"]; lvs = source["lvs"]
            require(layout_run_id == layout["id"] and drc_run_id == drc["id"] and lvs_run_id == lvs["id"] and (revision_id is None or revision_id == self.store.envelope()["revision"]["id"]),
                    "postlayout_source_conflict", "Continue from the exact latest adopted layout, DRC, LVS and GUI revision.")
            physical = self.physical_workflow
            require(not any(r["execution_status"] in ACTIVE for manager, field in
                    ((physical.global_generation, "jobs"), (physical.global_generation.generation, "jobs"),
                     (physical.global_generation.workflow, "runs"), (physical.global_workflow, "runs")) for r in manager._state[field]),
                    "postlayout_peer_busy", "Wait for model or earlier tool execution before post-layout verification.")
            self._validate_sources(lvs, drc, layout)
            with self.lock:
                require(not self._cleanup_unresolved(), "postlayout_cleanup_unresolved", CLEANUP_BLOCKED)
                require(not self._closed and not self.is_active() and not (self._worker and self._worker.is_alive()), "postlayout_busy", "Only one post-layout verification execution may run at a time.")
                run = {"id": new_id("postlayout-workflow"), "stage_id": STAGE, "revision_id": layout["revision_id"], "layout_run_id": layout["id"],
                    "layout_snapshot": layout, "layout_record_sha256": object_hash(layout), "layout_adoption": source["layout_adoption"],
                    "drc_run_id": drc["id"], "drc_snapshot": drc, "drc_record_sha256": object_hash(drc), "drc_adoption": source["drc_adoption"],
                    "lvs_run_id": lvs["id"], "lvs_snapshot": lvs, "lvs_record_sha256": object_hash(lvs), "lvs_adoption": source["lvs_adoption"],
                    "verification_plan": copy.deepcopy(layout["verification_plan"]), "verification_plan_sha256": layout["verification_plan_sha256"],
                    **{k: layout[k] for k in ("vector_hash", "testbench_sha256", "public_boundary_vector_hash")},
                    "source_inputs": source["inputs"], "input_gds_sha256": source["inputs"]["gds"]["sha256"],
                    "input_netlist_sha256": source["inputs"]["netlist"]["sha256"], "input_powered_netlist_sha256": source["inputs"]["powered_netlist"]["sha256"],
                    "runtime_configuration": copy.deepcopy(self.tool_configuration), "configuration_sha256": object_hash(self.tool_configuration),
                    "source_identity": source["identity"], "source_key": key, "source_epoch_at_start": self._state["source_epoch"],
                    "execution_scope": capability.get("execution_scope", "compatibility_preflight_only"),
                    "verification_supported": capability.get("verification_supported") is True,
                    "execution_status": "Queued", "validation_status": "Not Checked", "review_status": "Awaiting Review", "checks": {}, "diagnostics": [],
                    "created_at": utc_now(), "finished_at": None, "error": None, "evidence_kind": "software_qa_fixture" if self._injected else "trusted_fixed_postlayout_execution", "limits": list(LIMITS)}
                validate_source_snapshot(run)
                if _submission is not None:
                    run["submission_id"] = _submission.submission_id
                    _submission.bind(run["id"])
                self._state["runs"].append(run); self._persist(); self._cancel = threading.Event()
                self._worker = threading.Thread(target=self._execute, args=(run["id"], self._cancel), daemon=True, name="HuLLCirq-PostLayout"); self._worker.start()
        return self.envelope()

    def _execute(self, identifier, cancel):
        try:
            with self.lock:
                run = self._run(identifier); run["execution_status"] = "Running"; self._persist(); frozen = copy.deepcopy(run)
            result = self._adapter()[0](frozen["lvs_snapshot"], frozen["drc_snapshot"], frozen["layout_snapshot"], frozen["runtime_configuration"], cancel_event=cancel)
            require(type(result) is dict and result.get("validation_status") in ("Passed", "Failed", "Unsupported", "Not Checked") and type(result.get("diagnostics")) is list,
                    "postlayout_result_invalid", "The fixed post-layout verification adapter must return structured evidence.")
            with self.lock:
                run = self._run(identifier); run.update(checks=copy.deepcopy(result), diagnostics=copy.deepcopy(result["diagnostics"])); self._persist()
            require(self._injected or result.get("software_qa_fixture") is not True, "postlayout_fixture_rejected", "Software doubles cannot become actual post-layout verification evidence.")
            require(result.get("cleanup_unresolved") is not True, "postlayout_cleanup_unresolved", CLEANUP_BLOCKED)
            if result["validation_status"] == "Passed": validate_postlayout_proof({**frozen, "checks": result}, self._adapter()[1])
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
                    error={"code": getattr(error, "code", "postlayout_workflow_error"), "message": getattr(error, "message", "post-layout verification execution or durable evidence recording failed.")})
                try: self._persist()
                except (OSError, ValueError, TypeError): pass

    def _review(self, identifier, decision, note, target_stage, actor, provenance=None):
        require(decision in ("accepted", "changes_requested", "return_to_stage") and type(note) is str and (decision == "accepted" or note.strip()), "postlayout_review_invalid", "Provide a valid decision and correction/return reason.")
        require(target_stage in EARLIER if decision == "return_to_stage" else target_stage is None, "invalid_target_stage", "Return only to implemented S01–S13.")
        with self._source_locks():
            self.observe_design()
            with self.lock:
                run = self._run(identifier); decorated = self._decorate(run)
                require(run["execution_status"] not in ACTIVE and self._state["runs"][-1]["id"] == identifier, "postlayout_superseded", "Review the latest completed post-layout verification result.")
                if decision == "accepted":
                    require(not self._cleanup_unresolved(), "postlayout_cleanup_unresolved", CLEANUP_BLOCKED)
                    require(decorated["freshness"] == "Current" and run["execution_status"] == "Completed" and run["validation_status"] == "Passed", "postlayout_not_passed", "Only exact current executed Passed post-layout verification may be adopted.")
                    self._validate_sources(run["lvs_snapshot"], run["drc_snapshot"], run["layout_snapshot"]); validate_postlayout_proof(run, self._adapter()[1])
                    if actor == "automation_policy":
                        policy = self.store.review_policy()
                        require(policy["mode"] == "accept_on_pass" and policy["user_authorized"] is True and provenance is not None and provenance.get("policy_id") == policy["id"], "review_policy_changed", "The automatic adoption policy changed while post-layout verification ran.")
                    run.update(review_status="Accepted", acceptance_epoch=self._state["source_epoch"])
                else: run["review_status"] = "Changes Requested"
                review = {"id": new_id("postlayout-review"), "run_id": identifier, "decision": decision, "note": note, "target_stage": target_stage, "actor": actor,
                    "source_key": run["source_key"], "acceptance_epoch": run.get("acceptance_epoch"), "reviewed_revision_id": self.store.envelope()["revision"]["id"], "created_at": utc_now()}
                if provenance: review["provenance"] = copy.deepcopy(provenance)
                self._state["reviews"].append(review); self._persist()
        return self.envelope()

    def review(self, identifier, decision, note, target_stage=None, *, operator=None):
        fields = manual_review_fields(operator)
        return self._review(identifier, decision, note, target_stage, fields["actor"], fields["provenance"])

    def cancel(self, identifier):
        with self.lock:
            require(self._run(identifier)["execution_status"] in ACTIVE, "postlayout_not_active", "Only active post-layout verification can be cancelled."); self._cancel.set()
        return self.envelope()

    def artifact_file(self, identifier, artifact_id):
        with self.lock: result = copy.deepcopy(self._run(identifier)["checks"])
        entry = next((e for e in result.get("artifacts", []) if e["id"] == artifact_id), None)
        require(entry is not None and artifact_id in FILE_IDS, "postlayout_artifact_not_found", "Only retained fixed-ID post-layout verification files are available.", 404)
        path = _artifact_path(result, entry)
        require(path.stat().st_size == entry["bytes"] and _raw_hash(path) == entry["sha256"], "postlayout_artifact_hash_conflict", "The original saved post-layout verification bytes changed.")
        return {**entry, "path": path}

    def artifact_bytes(self, identifier, artifact_id):
        entry = self.artifact_file(identifier, artifact_id); payload = entry["path"].read_bytes()
        require(len(payload) == entry["bytes"] and hashlib.sha256(payload).hexdigest() == entry["sha256"], "postlayout_artifact_hash_conflict", "post-layout verification bytes changed during download.")
        return payload, entry["content_type"]

    def artifact(self, identifier, field):
        with self.lock: run = copy.deepcopy(self._run(identifier))
        fields = {"lvs-record": "lvs_snapshot", "drc-record": "drc_snapshot", "layout-record": "layout_snapshot", "source-identity": "source_identity", "runtime-configuration": "runtime_configuration", "verification-plan": "verification_plan"}
        if field in fields: return run[fields[field]]
        if field == "artifact-manifest": return copy.deepcopy(run["checks"].get("artifacts", []))
        raise DomainError("postlayout_artifact_not_found", "Only fixed post-layout verification documents and raw files are available.", 404)

    def _validate_saved(self):
        state = self._state
        require(type(state) is dict and state.get("postlayout_workflow_store_version") == "0.1" and type(state.get("runs")) is list and type(state.get("reviews")) is list
                and type(state.get("source_epoch")) is int and state["source_epoch"] >= 0 and type(state.get("source_transitions")) is list, "postlayout_history_invalid", "Invalid post-layout verification history containers.")
        transitions = state["source_transitions"]
        require([t["epoch"] for t in transitions] == list(range(1, state["source_epoch"] + 1)) and (transitions[-1]["source_key"] if transitions else None) == state["source_key"]
                and all(type(t["epoch"]) is int and type(t["source_key"]) is str for t in transitions), "postlayout_history_invalid", "post-layout verification source epochs are inconsistent.")
        policies = validate_policy_history(self.store.envelope()); ids = set()
        for run in state["runs"]:
            require(type(run) is dict and all(type(run.get(k)) is str for k in ("id", "stage_id", "revision_id", "layout_run_id", "layout_record_sha256",
                    "drc_run_id", "drc_record_sha256", "lvs_run_id", "lvs_record_sha256", "verification_plan_sha256", "vector_hash", "testbench_sha256", "public_boundary_vector_hash", "input_gds_sha256", "input_netlist_sha256", "input_powered_netlist_sha256", "configuration_sha256", "source_key", "created_at", "execution_scope"))
                    and all(type(run.get(k)) is dict for k in ("layout_snapshot", "layout_adoption", "drc_snapshot", "drc_adoption", "lvs_snapshot", "lvs_adoption", "verification_plan", "source_inputs", "runtime_configuration", "source_identity", "checks")) and type(run.get("diagnostics")) is list
                    and run["stage_id"] == STAGE and run["id"] not in ids and type(run.get("source_epoch_at_start")) is int and type(run.get("verification_supported")) is bool
                    and run["execution_status"] in ACTIVE | {"Completed", "Failed", "Cancelled", "Interrupted"} and run["validation_status"] in ("Not Checked", "Passed", "Failed", "Unsupported")
                    and run["review_status"] in ("Awaiting Review", "Accepted", "Changes Requested") and run.get("record_hash") == object_hash({k: v for k, v in run.items() if k != "record_hash"})
                    and run.get("evidence_kind") == ("software_qa_fixture" if self._injected else "trusted_fixed_postlayout_execution"), "postlayout_record_invalid", "post-layout verification record types, origin, statuses or checksum differ.")
            layout = run["layout_snapshot"]; current_layout = self.physical_workflow._run(run["layout_run_id"])
            drc = run["drc_snapshot"]; current_drc = self.drc_workflow._run(run["drc_run_id"])
            lvs = run["lvs_snapshot"]; current_lvs = self.lvs_workflow._run(run["lvs_run_id"])
            validate_source_snapshot(run)
            require(object_hash(_immutable_source(layout)) == object_hash(_immutable_source(current_layout))
                    and object_hash(_immutable_source(drc)) == object_hash(_immutable_source(current_drc))
                    and object_hash(_immutable_source(lvs)) == object_hash(_immutable_source(current_lvs))
                    and any(object_hash(run["layout_adoption"]) == object_hash(r) for r in self.physical_workflow._state["reviews"])
                    and any(object_hash(run["drc_adoption"]) == object_hash(r) for r in self.drc_workflow._state["reviews"])
                    and any(object_hash(run["lvs_adoption"]) == object_hash(r) for r in self.lvs_workflow._state["reviews"])
                    and any(t["epoch"] == run["source_epoch_at_start"] and t["source_key"] == run["source_key"] for t in transitions),
                    "postlayout_source_conflict", "post-layout verification history must retain all three exact immutable source records and authoritative adoption records.")
            self.store.snapshot(run["revision_id"]); self._validate_sources(lvs, drc, layout)
            if run["validation_status"] == "Passed": validate_postlayout_proof(run, self._adapter()[1])
            elif run["checks"].get("artifacts"): validate_artifact_manifest(run["checks"])
            reviews = [r for r in state["reviews"] if r["run_id"] == run["id"]]
            expected = "Awaiting Review" if not reviews else "Accepted" if reviews[-1]["decision"] == "accepted" else "Changes Requested"
            require(run["review_status"] == expected and (expected != "Accepted" or run["execution_status"] == "Completed" and run["validation_status"] == "Passed"
                    and type(run.get("acceptance_epoch")) is int and run["acceptance_epoch"] == reviews[-1]["acceptance_epoch"]), "postlayout_review_conflict", "post-layout verification adoption differs from recorded decisions.")
            ids.add(run["id"])
        for review in state["reviews"]:
            require(type(review) is dict and review.get("run_id") in ids and review.get("actor") in REVIEW_ACTORS and review.get("decision") in ("accepted", "changes_requested", "return_to_stage")
                    and type(review.get("note")) is str, "postlayout_review_conflict", "Invalid post-layout verification decision record.")
            run = self._run(review["run_id"])
            require(review["source_key"] == run["source_key"] and (review.get("target_stage") in EARLIER if review["decision"] == "return_to_stage" else review.get("target_stage") is None), "postlayout_review_conflict", "post-layout verification review source or return destination differs.")
            self.store.snapshot(review["reviewed_revision_id"]); validate_policy_review(review, policies)
            if review["decision"] == "accepted":
                require(type(review.get("acceptance_epoch")) is int and review["acceptance_epoch"] == run["source_epoch_at_start"] and same_revision_design(self.store, review["reviewed_revision_id"], run["revision_id"]), "postlayout_review_conflict", "post-layout verification acceptance must bind its original source epoch and semantic GUI revision.")
        contracts = state.get("adapter_contracts", [])
        require(type(contracts) is list, "postlayout_adapter_history_invalid", "Saved adapter metadata must be a list.")
        from . import postroute_generic
        contract_ids = set()
        for record in contracts:
            require(type(record) is dict and all(type(record.get(key)) is str for key in
                    ("id", "layout_run_id", "drc_run_id", "lvs_run_id", "revision_id", "verification_plan_sha256",
                     "settings_sha256", "contract_sha256", "created_at")) and record["id"] not in contract_ids
                    and record.get("actor") == "gui_operator" and type(record.get("contract")) is dict,
                    "postlayout_adapter_history_invalid", "Saved adapter metadata requires an explicit source-bound GUI record.")
            layout = self.physical_workflow._run(record["layout_run_id"])
            drc = self.drc_workflow._run(record["drc_run_id"]); lvs = self.lvs_workflow._run(record["lvs_run_id"])
            self.store.snapshot(record["revision_id"])
            require(record["verification_plan_sha256"] == object_hash(layout["verification_plan"])
                    and record["settings_sha256"] == object_hash(layout["settings"])
                    and record["contract_sha256"] == object_hash(record["contract"])
                    and drc["layout_run_id"] == lvs["layout_run_id"] == layout["id"] and lvs["drc_run_id"] == drc["id"]
                    and same_revision_design(self.store, record["revision_id"], layout["revision_id"]),
                    "postlayout_adapter_history_invalid", "Adapter metadata must retain its exact original plan, settings and source chain.")
            postroute_generic.validate_contract(layout["verification_plan"], layout["settings"], record["contract"])
            contract_ids.add(record["id"])
        resolutions = state.get("cleanup_resolutions", [])
        require(type(resolutions) is list, "postlayout_cleanup_resolution_invalid", "Saved termination audits must be a list.")
        from .postlayout_cleanup import validate_resolution
        resolution_ids = set()
        for resolution in resolutions:
            require(type(resolution) is dict and resolution.get("run_id") in ids
                    and resolution.get("id") not in resolution_ids,
                    "postlayout_cleanup_resolution_invalid", "Saved termination audits require unique IDs and original S14 runs.")
            validate_resolution(self._run(resolution["run_id"]), resolution)
            resolution_ids.add(resolution["id"])
        validate_submissions(state)

    def _persist(self):
        require_durable_write()
        name = None
        try:
            for run in self._state["runs"]: run["record_hash"] = object_hash({k: v for k, v in run.items() if k != "record_hash"})
            _io_path(self.path.parent).mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(prefix=".postlayout-workflow-", suffix=".tmp", dir=_io_path(self.path.parent))
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(self._state, ensure_ascii=False, allow_nan=False, indent=2) + "\n"); handle.flush(); os.fsync(handle.fileno())
            _replace_with_windows_retry(name, _io_path(self.path)); self._committed = copy.deepcopy(self._state); self._storage_error = None
        except (OSError, ValueError, TypeError):
            self._state = copy.deepcopy(self._committed); self._storage_error = {"code": "storage_error", "message": "post-layout verification save failed; last durable state retained."}; raise
        finally:
            if name and _io_path(name).exists(): _io_path(name).unlink()

    def close(self):
        with self.lock:
            self._closed = True
            if self._worker and self._worker.is_alive(): self._cancel.set()
        if self._worker and self._worker.is_alive(): self._worker.join(timeout=3)

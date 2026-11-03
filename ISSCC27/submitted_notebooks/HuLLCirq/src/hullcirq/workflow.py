"""One frozen node input through generic synthesis and netlist simulation.

No technology mapping, PDK, timing, or full-system verification is performed.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import re
import tempfile
import threading

from .context import node_fingerprint, physical_interface
from .domain import DomainError, IMPLEMENTED_STAGES, revision_hashes
from .review_actor import REVIEW_ACTORS, manual_review_fields
from .envelope_cache import memoized_envelope, read_scope
from .observation import ObservedState, persist_observation, require_durable_write
from .execution_submissions import PROTOCOL_VERSION, run_submission, submission_view, validate_submissions
from .store import _io_path, new_id, strict_loads, utc_now, validate_policy_history, validate_policy_review, _replace_with_windows_retry
from .verification import (build_verification_plan, content_hash, execute_fixed,
                           object_hash, trusted_command, validate_plan, verify_behavior, _wsl_path)
from .verification import verification_template_version
from .repair_guidance import compare_attempt

STAGES = ("local_synthesis", "local_netlist_simulation")
ACTIVE = {"Queued", "Running"}
SCOPE_VERSION = "stage-boundary-v2"
DERIVED_JOB_KINDS = {
    "generic_cycle_vectors",
    "npu2_array_node_original_job",
    "fifo_original_job", "npu2_control_original_job", "npu2_buffer_original_job",
    "npu2_scheduler_original_job", "npu2_dispatcher_original_job", "npu2_pe_original_job",
    "npu2_collector_original_job", "npu2_post_original_job",
}
BATCH_ITEM_STATUSES = ACTIVE | {"Skipped", "Passed", "Failed", "Unsupported", "Blocked", "Cancelled", "Interrupted"}


def workflow_exception_diagnostic(error, phase):
    """Preserve actionable exception identity, never paths or exception text."""
    name = type(error).__name__
    value = {"diagnostic_version": "workflow-exception-v1", "execution_phase": phase,
             "exception_class": name if name.isidentifier() and len(name) <= 80 else "Exception"}
    for field in ("errno", "winerror"):
        number = getattr(error, field, None)
        if type(number) is int:
            value[field] = number
    return value


def _environment_error(error, phase):
    failure = DomainError("workflow_environment_error",
                          "Tool input storage could not be prepared. Fix the trusted tool working directory and retry this stage using the same saved RTL.", 409)
    failure.execution_diagnostic = workflow_exception_diagnostic(error, phase)
    failure.next_action = "retry_same_RTL"
    return failure


def node_artifact_parent(configuration):
    """Use the trusted tool workspace, not deeply nested project/run IDs.

    The fallback belongs to HuLLCirq and does not use the user's global TEMP.
    Returning a parent for S06 avoids nesting a run UUID above its own unique
    ``hullcirq-functional-*`` directory. Historical artifact paths are untouched.
    """
    configured = configuration.get("working_directory") if type(configuration) is dict else None
    parent = Path(configured) if configured else Path(__file__).resolve().parents[2] / ".work" / "node_runs"
    if not parent.is_absolute():
        raise _environment_error(ValueError(), "validate_artifact_parent")
    parent = parent.resolve()
    # Windows CreateDirectory and later file writes can fail at different
    # legacy limits. Reserve room for the longest fixed unique child + file.
    if os.name == "nt" and len(str(parent / ("hullcirq-functional-" + "x" * 8) / "simulation.vvp")) >= 248:
        raise _environment_error(ValueError(), "validate_artifact_parent_length")
    return parent


def allocate_synthesis_directory(configuration):
    parent = node_artifact_parent(configuration)
    try:
        parent.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix="hullcirq-s05-", dir=parent))
    except OSError as error:
        raise _environment_error(error, "prepare_synthesis_artifact_directory") from error


def _candidate_interface(snapshot, job):
    """Freeze synthesis's public module without requiring a behavioral plan."""
    node = next((node for node in snapshot["nodes"] if node["id"] == job["node_id"]), None)
    if node is None:
        raise DomainError("node_not_found", "The candidate's original source node is missing.", 409)
    interface = physical_interface(snapshot, node)
    saved = job.get("context", {}).get("interface")
    if saved is not None and saved != interface:
        raise DomainError("candidate_interface_conflict", "The candidate interface differs from its original saved input.", 409)
    return interface


def _netlist_plan(snapshot, job):
    """S06 creates its own plan from the original input; old templates stay readable."""
    previous = job.get("verification_plan")
    template = verification_template_version(previous) if previous is not None else None
    plan = build_verification_plan(snapshot, job["node_id"], template)
    if previous is not None and plan != previous:
        raise DomainError("verification_input_conflict", "The historical verification plan no longer rebuilds from the original GUI input.", 409)
    validate_plan(plan)
    return plan


def ensure_current_verification_plan(design, node_id, plan, *, rebuilt_plans=None):
    """New derived contracts bind job data that S04's node hash does not cover.

    Keep historical node hashes and plans unchanged. Rebuild the exact frozen
    contract against current saved requirements before using or adopting S06.
    """
    if (plan or {}).get("kind") not in DERIVED_JOB_KINDS:
        return
    key = (node_id, verification_template_version(plan))
    if rebuilt_plans is None:
        current = build_verification_plan(design, *key)
    else:
        # A presentation pass uses one captured design. Rebuild that pure
        # reference once, but compare every individual saved plan below.
        if key not in rebuilt_plans:
            rebuilt_plans[key] = build_verification_plan(design, *key)
        current = rebuilt_plans[key]
    if object_hash(current) != object_hash(plan):
        raise DomainError("verification_source_changed", "The saved verification requirements or original job changed; use a candidate from that saved source before S06.", 409)


def validate_generic_simulation_proof(run):
    """Recheck generic S06 saved samples before restore or adoption, without tools."""
    plan = run.get("verification_plan")
    if (run.get('checks') or {}).get('waveform_recording') is not None:
        from . import simulation_waveforms_v1 as waveform
        tb_module = plan['testbench_module'] if plan.get('kind') == 'generic_cycle_vectors' else 'hullcirq_contract_tb'
        waveform.validate(run['checks'], plan, plan['testbench'], tb_module)
    if type(plan) is not dict or plan.get("kind") != "generic_cycle_vectors":
        return
    from .generic_verification import parse_cycle_runtime
    validate_plan(plan)
    check = run.get("checks")
    valid = type(check) is dict and type(run.get("netlist")) is str
    if valid:
        expected = {"rtl_sha256": content_hash(run["netlist"]), "vector_hash": plan["vector_hash"],
                    "testbench_sha256": plan["testbench_sha256"], "reference_trace_hash": plan["reference_trace_hash"],
                    "vector_count": plan["vector_count"], "coverage": plan["coverage"]}
        commands = check.get("commands")
        valid = (run.get("netlist_sha256") == expected["rtl_sha256"]
                 and all(check.get(key) == value for key, value in expected.items())
                 and check.get("validation_status") == "Passed" and check.get("executed") is True
                 and type(check.get("exit_code")) is int and check["exit_code"] == 0
                 and type(commands) is list and len(commands) == 3
                 and all(type(c) is dict and c.get("executed") is True and c.get("status") == "Completed"
                         and type(c.get("exit_code")) is int and c["exit_code"] == 0 for c in commands))
        if valid:
            valid = (parse_cycle_runtime(commands[-1].get("stdout"), plan, commands[-1].get("stderr", ""))["validation_status"] == "Passed"
                     and parse_cycle_runtime(check.get("stdout"), plan, check.get("stderr", ""))["validation_status"] == "Passed")
    if not valid:
        raise DomainError("generic_simulation_proof_invalid",
                          "The saved S06 proof must retain all exact cycle samples, original plan/netlist hashes and three successful fixed-tool records.", 409)


def synthesize_generic(rtl, module_name, synthesizer, directory, cancel_event=None):
    result = {"validation_status": "Unsupported", "executed": False, "exit_code": None, "diagnostics": [],
              "commands": [], "stdout": "", "stderr": "", "netlist": None,
              "scope": "generic_technology_independent_no_pdk_no_delay", "rtl_sha256": content_hash(rtl)}
    if synthesizer is None:
        result["diagnostics"].append({"code": "synthesizer_unavailable", "severity": "warning", "message": "Configure trusted Yosys before generic synthesis."})
        return result
    executable = synthesizer.get("executable")
    if type(executable) is not str or executable.replace("\\", "/").split("/")[-1].lower() not in ("yosys", "yosys.exe") or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", module_name):
        raise DomainError("invalid_synthesizer", "Only fixed Yosys synthesis of a saved plain module is supported.")
    environment = synthesizer.get("environment", {})
    if type(environment) is not dict or set(environment) - {"LD_LIBRARY_PATH", "YOSYS_DATDIR"} or any(type(value) is not str or not value.startswith("/") or any(ord(char) < 32 for char in value) for value in environment.values()):
        raise DomainError("invalid_synthesizer", "Only trusted Yosys data/library environment paths are supported.")
    directory = Path(directory).resolve()
    script = f"read_verilog candidate.v; synth -top {module_name} -noabc; check -assert; write_verilog -noattr netlist.v"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "candidate.v").write_text(rtl, encoding="utf-8")
        (directory / "synthesis.ys").write_text(script + "\n", encoding="utf-8")
    except OSError as error:
        raise _environment_error(error, "prepare_synthesis_inputs") from error
    result["artifacts_directory"] = str(directory)
    if environment and synthesizer["kind"] != "wsl":
        raise DomainError("unsupported_synthesizer", "Environment overrides are supported only for the isolated WSL Yosys runtime.")
    def command(arguments):
        if environment:
            return trusted_command(synthesizer, "/usr/bin/env", [*(f"{key}={value}" for key, value in sorted(environment.items())), executable, *arguments], directory)
        return trusted_command(synthesizer, executable, arguments, directory)
    version = execute_fixed(command(["-V"]), directory, cancel_event, timeout=10)
    result["tool_version"] = version["stdout"].strip()
    result["commands"].append(version)
    outcome = execute_fixed(command(["-Q", "-p", script]), directory, cancel_event, timeout=90)
    result["commands"].append(outcome)
    for key in ("executed", "exit_code", "stdout", "stderr"):
        result[key] = outcome[key]
    netlist_path = directory / "netlist.v"
    if outcome["status"] == "Completed" and outcome["exit_code"] == 0 and netlist_path.exists():
        netlist = netlist_path.read_text(encoding="utf-8")
        if re.search(r"\bmodule\s+" + re.escape(module_name) + r"\b", netlist):
            result.update(validation_status="Passed", netlist=netlist, netlist_sha256=content_hash(netlist))
    if result["validation_status"] != "Passed":
        result["validation_status"] = "Failed" if outcome["executed"] else "Unsupported"
        result["diagnostics"].append({"code": "synthesis_failed", "severity": "error", "message": "Generic synthesis did not produce the requested netlist; inspect the tool log."})
    return result


class WorkflowManager(ObservedState):
    def __init__(self, project_store, generation_manager, compiler=None, synthesizer=None):
        self.store, self.generation = project_store, generation_manager
        self.compiler, self.synthesizer = copy.deepcopy(compiler), copy.deepcopy(synthesizer)
        self.path = project_store.state_path.parent / "workflow.json"
        self.lock = threading.RLock()
        self._worker, self._cancel, self._closed = None, threading.Event(), False
        self._batch_worker, self._batch_cancel = None, threading.Event()
        self._committed, self._storage_error = None, None
        if _io_path(self.path).exists():
            try:
                self._state = strict_loads(_io_path(self.path).read_text(encoding="utf-8"))
                self._validate_saved()
            except (DomainError, OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                raise DomainError("invalid_workflow_store", "Workflow history is inconsistent; original file preserved.") from error
            self._committed = copy.deepcopy(self._state)
            interrupted = False
            for run in self._state["runs"]:
                if run["execution_status"] in ACTIVE:
                    run.update(execution_status="Interrupted", validation_status="Not Checked", finished_at=utc_now())
                    interrupted = True
            for batch in self._state.get("batches", []):
                if batch["execution_status"] in ACTIVE:
                    batch.update(execution_status="Interrupted", validation_status="Not Checked", finished_at=utc_now(),
                                 error={"code": "batch_interrupted", "message": "The service stopped. Start a new batch to continue; current accepted results are reused."})
                    for item in batch["items"]:
                        if item["status"] in ACTIVE:
                            run = next((run for run in self._state["runs"] if run["id"] == item.get("run_id")), None)
                            item["status"] = run["validation_status"] if run and run["execution_status"] == "Completed" else "Interrupted"
                            if item["status"] == "Not Checked":
                                item["status"] = "Interrupted"
                            item["reason"] = "Service interrupted; inspect saved runs before explicitly continuing."
                    interrupted = True
            if interrupted:
                self._persist()
        else:
            self._state = {"workflow_store_version": "0.1", "runs": [], "reviews": [], "node_inputs": {}, "node_epochs": {}}
            self._persist()
        self.observe_design()

    def _validate_saved(self):
        state = self._state
        def saved_job(identifier):
            # This constructor validates immutable persisted provenance. The
            # generation store has already been validated; API decoration
            # would rebuild current behavioral plans for every old run/item.
            getter = getattr(self.generation, "_stored_job", None)
            if getter is None:
                return self.generation.job(identifier)
            with self.generation.lock:
                return getter(identifier)
        policies = validate_policy_history(self.store.envelope())
        if type(state) is not dict or state.get("workflow_store_version") != "0.1" or any(type(state.get(key)) is not list for key in ("runs", "reviews")) or any(type(state.get(key)) is not dict for key in ("node_inputs", "node_epochs")):
            raise ValueError("Invalid workflow containers")
        if any(type(epoch) is not int or epoch < 0 for epoch in state["node_epochs"].values()):
            raise ValueError("Invalid workflow epochs")
        ids = set()
        for run in state["runs"]:
            if type(run) is not dict or type(run.get("id")) is not str or run["id"] in ids or run.get("stage_id") not in STAGES:
                raise ValueError("Invalid workflow run")
            ids.add(run["id"])
            if run.get("record_hash") != object_hash({key: value for key, value in run.items() if key != "record_hash"}):
                raise ValueError("Workflow evidence checksum mismatch")
            job = saved_job(run["candidate_id"])
            snapshot = self.store.snapshot(run["revision_id"])
            if run["revision_id"] != job["revision_id"] or run["node_id"] != job["node_id"] or run["design_hash"] != revision_hashes(snapshot)["semantic_hash"] or run["input_hash"] != node_fingerprint(snapshot, run["node_id"]) or run["rtl_sha256"] != content_hash(job["rtl"]):
                raise ValueError("Candidate input mismatch")
            scope = run.get("workflow_scope_version")
            if scope is None:
                # Historical S05/S06 records carried the S04 behavioral plan.
                validate_plan(run["verification_plan"])
                if run["verification_plan"] != job.get("verification_plan") or run["vector_hash"] != run["verification_plan"]["vector_hash"] or run["testbench_sha256"] != run["verification_plan"]["testbench_sha256"]:
                    raise ValueError("Changed original verification evidence")
            elif scope != SCOPE_VERSION or run.get("module_name") != _candidate_interface(snapshot, job)["module_name"]:
                raise ValueError("Invalid stage verification scope")
            elif run["stage_id"] == STAGES[0]:
                if any(run.get(key) is not None for key in ("verification_plan", "vector_hash", "testbench_sha256")):
                    raise ValueError("S05 must not imply behavioral verification")
            else:
                plan = run.get("verification_plan")
                validate_plan(plan)
                if (plan != build_verification_plan(snapshot, run["node_id"], verification_template_version(plan))
                        or run.get("vector_hash") != plan["vector_hash"] or run.get("testbench_sha256") != plan["testbench_sha256"]
                        or plan["module_name"] != run["module_name"]
                        or job.get("verification_plan") is not None and plan != job["verification_plan"]):
                    raise ValueError("Changed S06 original-input verification evidence")
            if run.get("netlist") is not None and run.get("netlist_sha256") != content_hash(run["netlist"]):
                raise ValueError("Netlist evidence mismatch")
            if type(run.get("checks")) is not dict or type(run.get("diagnostics")) is not list:
                raise ValueError("Invalid workflow evidence types")
            if run["execution_status"] not in ACTIVE | {"Completed", "Failed", "Cancelled", "Interrupted"} or run["validation_status"] not in {"Not Checked", "Passed", "Failed", "Unsupported"} or run["review_status"] not in {"Awaiting Review", "Accepted", "Changes Requested"}:
                raise ValueError("Invalid workflow status")
            reviews = [item for item in state["reviews"] if item.get("run_id") == run["id"]]
            if run["review_status"] != "Awaiting Review" and (not reviews or (reviews[-1]["decision"] == "accepted") != (run["review_status"] == "Accepted")):
                raise ValueError("Missing latest workflow adoption decision")
            if run["review_status"] == "Accepted" and (run["validation_status"] != "Passed" or run["execution_status"] != "Completed" or run["checks"].get("validation_status") != "Passed" or run["checks"].get("executed") is not True or run["checks"].get("exit_code") != 0 or not reviews or reviews[-1]["decision"] != "accepted" or reviews[-1].get("acceptance_epoch") != run.get("acceptance_epoch")):
                raise ValueError("Unverified workflow adoption")
            if run["stage_id"] == STAGES[1] and run["execution_status"] == "Completed" and run["validation_status"] == "Passed":
                validate_generic_simulation_proof(run)
            if run["stage_id"] == STAGES[1]:
                prior = next((item for item in state["runs"] if item["id"] == run["prior_run_id"]), None)
                if not prior or prior["stage_id"] != STAGES[0] or prior["candidate_id"] != run["candidate_id"] or prior["netlist_sha256"] != run["netlist_sha256"] or prior["netlist"] != run["netlist"]:
                    raise ValueError("Netlist source synthesis mismatch")
        for review in state["reviews"]:
            if type(review) is not dict or review.get("run_id") not in ids or review.get("actor") not in REVIEW_ACTORS or review.get("decision") not in ("accepted", "changes_requested", "return_to_stage"):
                raise ValueError("Invalid workflow decision")
            validate_policy_review(review, policies)
            self.store.snapshot(review["reviewed_revision_id"])
        batches = state.get("batches", [])
        if type(batches) is not list:
            raise ValueError("Invalid node workflow batches")
        batch_ids, request_ids = set(), set()
        for batch in batches:
            if (type(batch) is not dict or type(batch.get("id")) is not str or batch["id"] in batch_ids
                    or type(batch.get("request_id")) is not str or batch["request_id"] in request_ids
                    or batch.get("stage_id", STAGES[0]) not in STAGES or type(batch.get("items")) is not list
                    or batch.get("execution_status") not in ACTIVE | {"Completed", "Failed", "Cancelled", "Interrupted"}
                    or batch.get("validation_status") not in {"Not Checked", "Passed", "Failed", "Unsupported"}
                    or batch.get("record_hash") != object_hash({key: value for key, value in batch.items() if key != "record_hash"})):
                raise ValueError("Invalid node workflow batch evidence")
            stage_id = batch.get("stage_id", STAGES[0])
            batch_ids.add(batch["id"]); request_ids.add(batch["request_id"])
            snapshot = self.store.snapshot(batch["revision_id"])
            if (batch.get("design_hash") != revision_hashes(snapshot)["semantic_hash"]
                    or [item.get("node_id") for item in batch["items"]] != [node["id"] for node in snapshot["nodes"]]
                    or batch.get("tool_configuration_sha256") != object_hash(batch.get("tool_configuration"))):
                raise ValueError("Changed synthesis batch sources")
            for item in batch["items"]:
                if item.get("status") not in BATCH_ITEM_STATUSES:
                    raise ValueError("Invalid batch item status")
                candidate_id = item.get("candidate_id")
                if candidate_id is not None:
                    job = saved_job(candidate_id)
                    if job["node_id"] != item["node_id"] or content_hash(job["rtl"]) != item.get("rtl_sha256") or job["input_hash"] != item.get("input_hash"):
                        raise ValueError("Changed synthesis batch candidate")
                if item.get("run_id") is not None:
                    run = self._run(item["run_id"])
                    if run["stage_id"] != stage_id or run["candidate_id"] != candidate_id or run["node_id"] != item["node_id"]:
                        raise ValueError("Changed synthesis batch run")
                    if item["status"] != "Skipped" and (run.get("batch_id") != batch["id"] or run["tool_configuration"] != batch["tool_configuration"]):
                        raise ValueError("Changed synthesis batch tool configuration")
                    if stage_id == STAGES[1] and item["status"] != "Skipped" and run.get("requested_revision_id") != batch["revision_id"]:
                        raise ValueError("Changed netlist batch requested source")
                if stage_id == STAGES[1]:
                    prior = self._run(item["prior_run_id"]) if item.get("prior_run_id") else None
                    plan = item.get("verification_plan")
                    if prior and (prior["stage_id"] != STAGES[0] or prior["candidate_id"] != candidate_id
                                  or prior["node_id"] != item["node_id"] or not prior.get("netlist")
                                  or prior["netlist_sha256"] != item.get("netlist_sha256")):
                        raise ValueError("Changed netlist batch synthesis source")
                    if plan is not None:
                        validate_plan(plan)
                        if (not prior or item.get("verification_plan_sha256") != object_hash(plan)
                                or plan != _netlist_plan(self.store.snapshot(job["revision_id"]), job)):
                            raise ValueError("Changed netlist batch verification plan")
                    if item.get("status") in ACTIVE | {"Passed", "Failed", "Skipped"} and (not prior or plan is None):
                        raise ValueError("Missing netlist batch frozen sources")
                    if item.get("run_id") and (run["prior_run_id"] != item.get("prior_run_id")
                                              or run["netlist_sha256"] != item.get("netlist_sha256")
                                              or run["verification_plan"] != plan):
                        raise ValueError("Changed netlist batch executed source")

        validate_submissions(self._state)

    def _persist(self):
        require_durable_write()
        name = None
        try:
            for run in self._state["runs"]:
                run["record_hash"] = object_hash({key: value for key, value in run.items() if key != "record_hash"})
            for batch in self._state.get("batches", []):
                batch["record_hash"] = object_hash({key: value for key, value in batch.items() if key != "record_hash"})
            descriptor, name = tempfile.mkstemp(prefix=".workflow-", suffix=".tmp", dir=_io_path(self.path.parent))
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(self._state, ensure_ascii=False, allow_nan=False, indent=2) + "\n")
                handle.flush(); os.fsync(handle.fileno())
            _replace_with_windows_retry(name, self.path)
            self._committed, self._storage_error = copy.deepcopy(self._state), None
        except (OSError, ValueError, TypeError):
            if self._committed is not None:
                self._state = copy.deepcopy(self._committed)
            self._storage_error = {"code": "storage_error", "message": "Workflow evidence could not be saved; last durable state retained."}
            raise
        finally:
            if name and _io_path(name).exists():
                _io_path(name).unlink()

    def observe_design(self):
        design = self.store.envelope()["design"]
        current = {node["id"]: node_fingerprint(design, node["id"]) for node in design["nodes"]}
        with self.lock:
            if current == self._state["node_inputs"]:
                return
            for node_id in set(current) | set(self._state["node_inputs"]):
                if current.get(node_id) != self._state["node_inputs"].get(node_id):
                    self._state["node_epochs"][node_id] = self._state["node_epochs"].get(node_id, 0) + 1
            self._state["node_inputs"] = current
            persist_observation(self)

    def _run(self, run_id):
        run = next((run for run in self._state["runs"] if run["id"] == run_id), None)
        if run is None:
            raise DomainError("workflow_run_not_found", "Workflow run does not exist.", 404)
        return run

    def _decorate(self, run, _view=None):
        if _view is not None and run["id"] in _view["runs"]:
            return _view["runs"][run["id"]]
        result = copy.deepcopy(run)
        current = self._state["node_inputs"].get(run["node_id"]) == run["input_hash"]
        if run["stage_id"] == STAGES[1]:
            matches = [source for source in self._state["runs"] if source["stage_id"] == STAGES[0]
                       and source["node_id"] == run["node_id"]]
            prior = self._decorate(matches[-1], _view) if matches else None
            if (not prior or prior["id"] != run.get("prior_run_id") or prior["candidate_id"] != run["candidate_id"]
                    or prior["execution_status"] != "Completed" or prior["validation_status"] != "Passed"
                    or prior["review_status"] != "Accepted" or prior["freshness"] != "Current"
                    or prior.get("netlist_sha256") != run.get("netlist_sha256")):
                current = False
                result["blocked_reason"] = "The latest current adopted S05 netlist differs from this S06 source."
        if (run.get("verification_plan") or {}).get("kind") == "npu_scheduler_stream":
            candidate = self.generation.job(run["candidate_id"])
            if candidate["freshness"] != "Current" or candidate["review_status"] != "Accepted":
                current = False
                result["blocked_reason"] = candidate.get("blocked_reason", "The source scheduler candidate adoption is no longer current.")
        if (run.get("verification_plan") or {}).get("kind") in DERIVED_JOB_KINDS:
            try:
                self._fifo_source_current(run["candidate_id"], run["node_id"], run["prior_run_id"], run["verification_plan"], _view)
            except DomainError as error:
                current = False
                result["blocked_reason"] = error.message
        result["freshness"] = "Current" if current else "Stale"
        if result["review_status"] == "Accepted" and (not current or run.get("acceptance_epoch") != self._state["node_epochs"].get(run["node_id"])):
            result["review_status"] = "Awaiting Review"
        result["artifacts"] = [{"kind": "workflow_run", "url": f"/api/workflow/runs/{run['id']}"},
                               {"kind": "design_input_snapshot", "url": f"/api/snapshots/{run['revision_id']}"}]
        if _view is not None:
            _view["runs"][run["id"]] = result
        return result

    def _fifo_source_current(self, candidate_id, node_id, prior_run_id, plan, _view=None):
        # Preserve the historical helper name; all saved-job-derived node
        # contracts require the same current candidate / S05 / global-job guard.
        if (plan or {}).get("kind") not in DERIVED_JOB_KINDS:
            return
        selected = self._selected_candidates() if _view is None else _view["selected_candidates"]
        if selected.get(node_id) != candidate_id:
            raise DomainError("candidate_not_adopted", "Use the latest current adopted RTL candidate for this verification source.", 409)
        matches = [item for item in self._state["runs"] if item["stage_id"] == STAGES[0] and item["candidate_id"] == candidate_id]
        prior = self._decorate(matches[-1], _view) if matches else None
        if not prior or prior["id"] != prior_run_id or prior["validation_status"] != "Passed" or prior["review_status"] != "Accepted" or prior["freshness"] != "Current" or not prior.get("netlist"):
            raise DomainError("synthesis_not_adopted", "Use the latest current adopted synthesis of this exact candidate.", 409)
        if _view is None:
            ensure_current_verification_plan(self.store.envelope()["design"], node_id, plan)
        else:
            ensure_current_verification_plan(_view["project"]["design"], node_id, plan,
                                             rebuilt_plans=_view["plans"])

    @memoized_envelope
    def envelope(self):
        # Capture/decorate one coherent read view in the existing upstream
        # lock order; worker source guards outside this method remain live.
        with self.lock, self.generation.lock, self.store.lock:
            self.observe_design()
            selected_candidates = self._selected_candidates()
            # Only this final read view shares captured presentation inputs.
            # Workers, execution/adoption guards and individual record reads
            # keep their uncached default paths and recheck current sources.
            view = {"selected_candidates": selected_candidates, "project": self.store.envelope(),
                    "plans": {}, "runs": {}}
            runs = [self._decorate(run, view) for run in self._state["runs"]]
            nodes = []
            # Repair comparison needs four immutable scalar fields only.
            # generation.job() also rebuilds behavioral readiness and deep
            # copies the complete prompt/history for every lookup, which is
            # unnecessary for these already-selected source identities.
            with self.generation.lock:
                repair_sources = {job["id"]: {key: job.get(key) for key in ("rtl", "operation", "base_job_id")}
                                  for job in self.generation._state["jobs"]}
            for node_id in self._state["node_inputs"]:
                for stage_id in STAGES:
                    relevant = [run for run in runs if run["node_id"] == node_id and run["stage_id"] == stage_id]
                    latest = relevant[-1] if relevant else None
                    repair_status = None
                    if latest and latest["freshness"] == "Current" and stage_id == STAGES[0] and selected_candidates.get(node_id) == latest["candidate_id"]:
                        candidate = repair_sources.get(latest["candidate_id"], {})
                        parent_id = candidate.get("base_job_id") if candidate.get("operation") == "repair" else None
                        parent = repair_sources.get(parent_id) if parent_id else None
                        baselines = [entry for entry in runs if parent and entry["stage_id"] == stage_id and entry["candidate_id"] == parent_id]
                        repair_status = compare_attempt(latest, candidate.get("rtl"), baselines[-1] if baselines else None, (parent or {}).get("rtl"))
                    nodes.append({"node_id": node_id, "stage_id": stage_id, "latest_run_id": latest["id"] if latest else None,
                                  "repair_status": repair_status,
                                  "accepted_run_id": latest["id"] if latest and latest["review_status"] == "Accepted"
                                  and latest["freshness"] == "Current" and latest["execution_status"] == "Completed"
                                  and latest["validation_status"] == "Passed" and latest.get("netlist")
                                  and selected_candidates.get(node_id) == latest["candidate_id"] else None})
            batches = [self._decorate_batch(batch, view) for batch in self._state.get("batches", [])]
            active = next((batch for batch in reversed(batches) if batch["execution_status"] in ACTIVE), None)
            return {"workflow_runs": runs, "workflow_nodes": nodes, "workflow_reviews": copy.deepcopy(self._state["reviews"]),
                    "workflow_storage_error": copy.deepcopy(self._storage_error), "workflow_batches": batches,
                    "workflow_batch_stages": list(STAGES),
                    "workflow_active_batch_id": active["id"] if active else None,
                    "workflow_latest_batch_id": batches[-1]["id"] if batches else None,
                    "workflow_execution_submissions": submission_view(self),
                    "workflow_submission_protocol_version": PROTOCOL_VERSION}

    def is_active(self):
        with self.lock:
            return bool((self._worker and self._worker.is_alive()) or
                        (self._batch_worker and self._batch_worker.is_alive()) or
                        any(run["execution_status"] in ACTIVE for run in self._state["runs"]) or
                        any(batch["execution_status"] in ACTIVE for batch in self._state.get("batches", [])))

    def _result_envelope(self):
        # Only the final read view is cached. No mutation, worker execution,
        # source guard or adoption decision may run inside this scope.
        with read_scope():
            return self.envelope()

    def _batch(self, batch_id):
        batch = next((batch for batch in self._state.get("batches", []) if batch["id"] == batch_id), None)
        if batch is None:
            raise DomainError("workflow_batch_not_found", "Node workflow batch does not exist.", 404)
        return batch

    def _selected_candidates(self):
        # Recompute the same current/adopted identities without decorating the
        # entire generation history on every 50ms batch worker source check.
        selection = getattr(self.generation, "current_candidate_selection", None)
        if selection is not None:
            return selection()
        generation = self.generation.envelope()["generation"]
        return {node["node_id"]: node.get("accepted_job_id") if node.get("accepted_job_id") == node.get("latest_job_id") else None
                for node in generation["nodes"]}

    def _selected_synthesis(self, selected, _view=None):
        """Latest S05 adoption per node, bound to the currently selected RTL."""
        sources = {}
        for node_id, candidate_id in selected.items():
            matches = [run for run in self._state["runs"] if run["stage_id"] == STAGES[0] and run["node_id"] == node_id]
            latest = self._decorate(matches[-1], _view) if matches else None
            sources[node_id] = latest if (candidate_id and latest and latest["candidate_id"] == candidate_id
                and latest["execution_status"] == "Completed" and latest["validation_status"] == "Passed"
                and latest["review_status"] == "Accepted" and latest["freshness"] == "Current" and latest.get("netlist")) else None
        return sources

    def _batch_source_current(self, batch, _view=None):
        current = self.store.envelope() if _view is None else _view["project"]
        if current["revision"]["id"] != batch["revision_id"]:
            return False
        selected = self._selected_candidates() if _view is None else _view["selected_candidates"]
        if selected != {item["node_id"]: item["candidate_id"] for item in batch["items"]}:
            return False
        if batch.get("stage_id", STAGES[0]) == STAGES[1]:
            sources = self._selected_synthesis(selected, _view)
            return {node_id: source["id"] if source else None for node_id, source in sources.items()} == {
                item["node_id"]: item.get("prior_run_id") for item in batch["items"]}
        return True

    def _decorate_batch(self, batch, _view=None):
        result = copy.deepcopy(batch)
        result.setdefault("stage_id", STAGES[0])
        result["source_current"] = self._batch_source_current(batch, _view)
        result["freshness"] = "Current" if result["source_current"] else "Stale"
        result["counts"] = {status: sum(item["status"] == status for item in batch["items"]) for status in sorted(BATCH_ITEM_STATUSES)}
        result["completed_count"] = sum(item["status"] not in ACTIVE for item in batch["items"])
        result["required_node_count"] = len(batch["items"])
        accepted = 0
        for item in batch["items"]:
            run = self._decorate(self._run(item["run_id"]), _view) if item.get("run_id") else None
            matches = [entry for entry in self._state["runs"] if entry["node_id"] == item["node_id"]
                       and entry["stage_id"] == STAGES[1]] if result["stage_id"] == STAGES[1] else None
            latest_result = matches is None or bool(matches and run and matches[-1]["id"] == run["id"])
            if (result["source_current"] and run and run["review_status"] == "Accepted" and run["freshness"] == "Current"
                    and latest_result and run["execution_status"] == "Completed" and run["validation_status"] == "Passed" and run.get("netlist")):
                accepted += 1
        result["accepted_node_count"] = accepted
        return result

    def batch(self, batch_id):
        self.observe_design()
        with self.lock:
            return self._decorate_batch(self._batch(batch_id))

    def start_batch(self, revision_id, request_id, stage_id=STAGES[0], *, _submission=None):
        """One explicit request, one saved source and tool execution per node."""
        if (type(revision_id) is not str or type(request_id) is not str
                or not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", request_id) or stage_id not in STAGES):
            raise DomainError("invalid_batch_request", "Provide the saved revision, S05/S06 stage and a unique request ID.")
        self.observe_design()
        self._prerequisites()
        with self.lock:
            previous = next((batch for batch in self._state.get("batches", []) if batch["request_id"] == request_id), None)
            if previous is not None:
                if _submission is not None:
                    raise DomainError("submission_conflict", "This batch request ID already belongs to an earlier execution; use its original receipt.", 409)
                if previous["revision_id"] != revision_id or previous.get("stage_id", STAGES[0]) != stage_id:
                    raise DomainError("batch_request_conflict", "This request ID belongs to another revision or stage.", 409)
                return self._result_envelope()
            if self._closed or self.is_active():
                raise DomainError("workflow_busy", "Finish or cancel the active node tool run or batch first.", 409)
            current = self.store.envelope()
            if revision_id != current["revision"]["id"]:
                raise DomainError("revision_conflict", "Start the node batch from the current saved GUI input.", 409)
            if stage_id == STAGES[0] and self.synthesizer is None:
                raise DomainError("synthesizer_unavailable", "Configure trusted Yosys before starting all-node synthesis.", 409)
            if stage_id == STAGES[1] and self.compiler is None:
                raise DomainError("compiler_unavailable", "Configure trusted Icarus before starting all-node netlist verification.", 409)
            selected = self._selected_candidates()
            synthesis = self._selected_synthesis(selected) if stage_id == STAGES[1] else {}
            items = []
            for node in current["design"]["nodes"]:
                candidate_id = selected.get(node["id"])
                item = {"node_id": node["id"], "candidate_id": candidate_id, "run_id": None, "status": "Queued", "reason": None, "error": None}
                if stage_id == STAGES[1]:
                    item.update(prior_run_id=None, netlist_sha256=None, verification_plan=None, verification_plan_sha256=None)
                if candidate_id is None:
                    item.update(status="Blocked", reason="Generate and adopt this node RTL in S04 first.")
                else:
                    job = self.generation.job(candidate_id)
                    validation = job.get("stage_validation", {}).get("validation_status", job["validation_status"])
                    if (job["node_id"] != node["id"] or job["freshness"] != "Current" or job["review_status"] != "Accepted"
                            or job["execution_status"] != "Completed" or validation != "Passed"):
                        raise DomainError("candidate_not_adopted", "Use current Passed and adopted S04 candidates for node batches.", 409)
                    item.update(input_hash=job["input_hash"], rtl_sha256=content_hash(job["rtl"]))
                    prior = synthesis.get(node["id"])
                    if stage_id == STAGES[1]:
                        if prior is None:
                            item.update(status="Blocked", reason="Run and adopt S05 synthesis of this exact current RTL first.",
                                        error={"code": "synthesis_not_adopted", "message": "Current accepted S05 netlist is required."})
                        else:
                            item.update(prior_run_id=prior["id"], netlist_sha256=prior["netlist_sha256"])
                            try:
                                plan = _netlist_plan(self.store.snapshot(job["revision_id"]), job)
                                self._fifo_source_current(candidate_id, node["id"], prior["id"], plan)
                                item.update(verification_plan=plan, verification_plan_sha256=object_hash(plan))
                            except DomainError as error:
                                unsupported = error.code.startswith("unsupported_") or error.code == "verification_contract_missing"
                                item.update(status="Unsupported" if unsupported else "Blocked", reason=error.message,
                                            error={"code": error.code, "message": error.message})
                    matches = [run for run in self._state["runs"] if run["stage_id"] == stage_id and run["node_id"] == node["id"]]
                    latest = self._decorate(matches[-1]) if matches else None
                    if (item["status"] == "Queued" and latest and latest["candidate_id"] == candidate_id and latest["execution_status"] == "Completed"
                            and latest["validation_status"] == "Passed" and latest["review_status"] == "Accepted"
                            and latest["freshness"] == "Current" and latest.get("netlist")
                            and (stage_id == STAGES[0] or latest.get("prior_run_id") == item["prior_run_id"]
                                 and latest.get("netlist_sha256") == item["netlist_sha256"]
                                 and latest.get("verification_plan") == item["verification_plan"])):
                        item.update(status="Skipped", run_id=latest["id"], reason="Current accepted S05 of this exact RTL is reused." if stage_id == STAGES[0]
                                    else "Current accepted S06 of this exact S05 netlist and original verification plan is reused.")
                items.append(item)
            configuration = self.synthesizer if stage_id == STAGES[0] else self.compiler
            batch = {"id": new_id("synthesis-batch" if stage_id == STAGES[0] else "netlist-batch"), "request_id": request_id, "stage_id": stage_id,
                     "revision_id": revision_id, "design_hash": current["revision"]["semantic_hash"],
                     "tool_configuration": copy.deepcopy(configuration), "tool_configuration_sha256": object_hash(configuration),
                     "items": items, "execution_status": "Queued", "validation_status": "Not Checked", "error": None,
                     "created_at": utc_now(), "finished_at": None,
                     "scope": "sequential_generic_node_synthesis_no_llm_no_behavioral_simulation" if stage_id == STAGES[0]
                     else "sequential_exact_accepted_node_netlists_original_specification_no_llm_no_physical_timing"}
            if _submission is not None:
                batch["submission_id"] = _submission.submission_id
                _submission.bind(batch["id"])
            self._state.setdefault("batches", []).append(batch)
            self._persist()
            self._batch_cancel = threading.Event()
            self._batch_worker = threading.Thread(target=self._execute_batch, args=(batch["id"], self._batch_cancel), daemon=True, name="HuLLCirq-all-node-" + stage_id)
            self._batch_worker.start()
        return self._result_envelope()

    def _execute_batch(self, batch_id, cancelled):
        source_changed = False
        try:
            with self.lock:
                batch = self._batch(batch_id)
                batch["execution_status"] = "Running"
                self._persist()
            for index in range(len(batch["items"])):
                with self.lock:
                    batch = self._batch(batch_id)
                    source_changed = not self._batch_source_current(batch)
                    if cancelled.is_set() or source_changed:
                        break
                    item = batch["items"][index]
                    if item["status"] != "Queued":
                        continue
                    try:
                        self.start(batch.get("stage_id", STAGES[0]), item["node_id"], item["candidate_id"], batch["revision_id"], _batch_id=batch_id)
                    except DomainError as error:
                        # A node's unsupported contract is an item result. It must
                        # never prevent another eligible node from being checked.
                        if error.code in {"batch_source_changed", "workflow_busy", "revision_conflict"}:
                            raise
                        item.update(status="Unsupported" if error.code.startswith("unsupported_") or error.code == "verification_contract_missing" else "Blocked",
                                    reason=error.message, error={"code": error.code, "message": error.message})
                        self._persist()
                        continue
                    worker, run_id = self._worker, item["run_id"]
                while worker.is_alive():
                    worker.join(0.05)
                    with self.lock:
                        source_changed = not self._batch_source_current(self._batch(batch_id))
                        if cancelled.is_set() or source_changed:
                            self._cancel.set()
                with self.lock:
                    batch = self._batch(batch_id)
                    item = batch["items"][index]
                    run = self._run(run_id)
                    item["status"] = (run["validation_status"] if run["execution_status"] == "Completed" else
                                      "Cancelled" if run["execution_status"] == "Cancelled" else "Failed")
                    if item["status"] == "Not Checked":
                        item["status"] = "Failed"
                    item["error"] = copy.deepcopy(run.get("error"))
                    item["reason"] = (run.get("error") or {}).get("message") or (None if item["status"] == "Passed" else "Inspect this node tool log; successful nodes are retained.")
                    self._persist()
            with self.lock:
                batch = self._batch(batch_id)
                source_changed = source_changed or not self._batch_source_current(batch)
                for item in batch["items"]:
                    if item["status"] in ACTIVE:
                        item.update(status="Blocked" if source_changed else "Cancelled", reason="Saved design, adopted RTL or source synthesis changed; start a new batch." if source_changed else "Batch cancelled before this node started.")
                status = "Interrupted" if source_changed else "Cancelled" if cancelled.is_set() else "Completed"
                validation = ("Not Checked" if status != "Completed" else "Passed" if all(item["status"] in {"Passed", "Skipped"} for item in batch["items"]) else "Failed")
                batch.update(execution_status=status, validation_status=validation, finished_at=utc_now())
                if source_changed:
                    batch["error"] = {"code": "batch_source_changed", "message": "Saved design, adopted RTL or source synthesis changed. Historical results are retained; start from the current input."}
                self._persist()
        except Exception as error:
            with self.lock:
                batch = self._batch(batch_id)
                batch.update(execution_status="Cancelled" if cancelled.is_set() else "Failed", validation_status="Not Checked", finished_at=utc_now(),
                             error={"code": getattr(error, "code", "batch_error"), "message": getattr(error, "message", "Node tool scheduling or durable recording failed. Inspect saved runs before continuing."),
                                    **workflow_exception_diagnostic(error, "batch_scheduling")})
                for item in batch["items"]:
                    if item["status"] in ACTIVE:
                        item.update(status="Interrupted", reason=batch["error"]["message"])
                try:
                    self._persist()
                except OSError:
                    pass

    def cancel_batch(self, batch_id):
        with self.lock:
            if self._batch(batch_id)["execution_status"] not in ACTIVE:
                raise DomainError("workflow_batch_not_active", "Only an active node workflow batch can be cancelled.", 409)
            self._batch_cancel.set()
            self._cancel.set()
        return self._result_envelope()

    def run(self, run_id):
        self.observe_design()
        with self.lock:
            return self._decorate(self._run(run_id))

    def _prerequisites(self):
        if any(stage["review_status"] != "Accepted" or stage["freshness"] == "Stale" for stage in self.store.envelope()["workflow"] if stage["id"] in IMPLEMENTED_STAGES):
            raise DomainError("review_prerequisite", "Current design input checks must be adopted before continuing.", 409)

    def start(self, stage_id, node_id, candidate_id, revision_id, *, _batch_id=None, _submission=None):
        if stage_id not in STAGES or any(type(value) is not str for value in (node_id, candidate_id, revision_id)):
            raise DomainError("unsupported_workflow_stage", "Only node generic synthesis and netlist simulation are implemented.")
        self.observe_design()
        self._prerequisites()
        current = self.store.envelope()
        if revision_id != current["revision"]["id"]:
            raise DomainError("revision_conflict", "Continue from the current saved GUI input.", 409)
        job = self.generation.job(candidate_id)
        candidate_validation = job.get("stage_validation", {}).get("validation_status", job["validation_status"])
        if job["node_id"] != node_id or job["freshness"] != "Current" or job["review_status"] != "Accepted" or job["execution_status"] != "Completed" or candidate_validation != "Passed":
            raise DomainError("candidate_not_adopted", "Use a current Passed and adopted node candidate.", 409)
        snapshot = self.store.snapshot(job["revision_id"])
        interface = _candidate_interface(snapshot, job)
        with self.lock:
            active_batch = next((batch for batch in self._state.get("batches", []) if batch["execution_status"] in ACTIVE), None)
            if active_batch is not None and active_batch["id"] != _batch_id:
                raise DomainError("workflow_busy", "Finish or cancel the all-node workflow batch before a separate tool run.", 409)
            if self._closed or self._worker and self._worker.is_alive() or any(run["execution_status"] in ACTIVE for run in self._state["runs"]):
                raise DomainError("workflow_busy", "Only one continuous workflow tool operation can run at a time.", 409)
            prior = None
            plan = None
            if stage_id == STAGES[1]:
                matches = [run for run in self._state["runs"] if run["stage_id"] == STAGES[0] and run["candidate_id"] == candidate_id]
                prior = self._decorate(matches[-1]) if matches else None
                if not prior or prior["validation_status"] != "Passed" or prior["review_status"] != "Accepted" or prior["freshness"] != "Current" or not prior.get("netlist"):
                    raise DomainError("synthesis_not_adopted", "Adopt Passed synthesis of this exact candidate before netlist verification.", 409)
                try:
                    plan = _netlist_plan(snapshot, job)
                    self._fifo_source_current(candidate_id, node_id, prior["id"], plan)
                except DomainError as error:
                    raise DomainError(error.code, "S06 netlist verification cannot start: " + error.message, 409) from error
            run_id = new_id("workflow")
            run = {"id": run_id, "stage_id": stage_id, "node_id": node_id, "candidate_id": candidate_id,
                   "revision_id": job["revision_id"], "requested_revision_id": revision_id, "input_hash": job["input_hash"],
                   "design_hash": revision_hashes(self.store.snapshot(job["revision_id"]))["semantic_hash"],
                   "requested_design_hash": current["revision"]["semantic_hash"], "rtl_sha256": content_hash(job["rtl"]),
                   "workflow_scope_version": SCOPE_VERSION, "module_name": interface["module_name"],
                   "verification_plan": copy.deepcopy(plan), "vector_hash": plan["vector_hash"] if plan else None,
                   "testbench_sha256": plan["testbench_sha256"] if plan else None,
                   "prior_run_id": prior["id"] if prior else None, "netlist": prior["netlist"] if prior else None,
                   "netlist_sha256": prior["netlist_sha256"] if prior else None, "execution_status": "Queued",
                   "validation_status": "Not Checked", "review_status": "Awaiting Review", "checks": {}, "diagnostics": [],
                   "created_at": utc_now(), "finished_at": None, "error": None, "tool_configuration": copy.deepcopy(self.synthesizer if stage_id == STAGES[0] else self.compiler)}
            if _submission is not None:
                run["submission_id"] = _submission.submission_id
                _submission.bind(run["id"])
            self._state["runs"].append(run)
            if _batch_id is not None:
                batch = self._batch(_batch_id)
                if stage_id != batch.get("stage_id", STAGES[0]) or batch["id"] != (active_batch or {}).get("id") or not self._batch_source_current(batch) or self._batch_cancel.is_set():
                    self._state["runs"].pop()
                    raise DomainError("batch_source_changed", "The node workflow batch source changed or was cancelled.", 409)
                item = next(item for item in batch["items"] if item["node_id"] == node_id)
                if stage_id == STAGES[1] and (prior["id"] != item.get("prior_run_id")
                        or prior["netlist_sha256"] != item.get("netlist_sha256") or plan != item.get("verification_plan")):
                    self._state["runs"].pop()
                    raise DomainError("batch_source_changed", "The frozen S05 netlist or original verification plan changed.", 409)
                run.update(batch_id=_batch_id, tool_configuration=copy.deepcopy(batch["tool_configuration"]))
                item.update(run_id=run_id, status="Running")
            self._persist()
            self._cancel = threading.Event()
            self._worker = threading.Thread(target=self._execute, args=(run_id, job["rtl"], self._cancel), daemon=True, name="HuLLCirq-continuous-node-flow")
            self._worker.start()
        return {"workflow_run_id": run_id} if _batch_id is not None else self._result_envelope()

    def _execute(self, run_id, rtl, cancelled):
        phase = "record_running"
        try:
            with self.lock:
                run = self._run(run_id)
                run["execution_status"] = "Running"
                self._persist()
                frozen = copy.deepcopy(run)
            phase = "prepare_artifact_directory"
            if frozen["stage_id"] == STAGES[0]:
                directory = allocate_synthesis_directory(frozen["tool_configuration"])
                module_name = frozen.get("module_name") or frozen["verification_plan"]["module_name"]
                phase = "execute_synthesis"
                result = synthesize_generic(rtl, module_name, frozen["tool_configuration"], directory, cancelled)
            else:
                parent = node_artifact_parent(frozen["tool_configuration"])
                phase = "execute_netlist_simulation"
                result = verify_behavior(frozen["netlist"], frozen["verification_plan"], frozen["tool_configuration"], parent, cancelled, record_waveform=True)
            phase = "record_result"
            with self.lock:
                run = self._run(run_id)
                run.update(execution_status="Cancelled" if cancelled.is_set() else "Completed",
                           validation_status="Not Checked" if cancelled.is_set() else result["validation_status"],
                           checks=result, diagnostics=result.get("diagnostics", []), finished_at=utc_now())
                if frozen["stage_id"] == STAGES[0] and result.get("netlist"):
                    run.update(netlist=result["netlist"], netlist_sha256=result["netlist_sha256"])
                self._persist()
            phase = "observe_completed_source"
            self.observe_design()
            policy = self.store.review_policy()
            if result["validation_status"] == "Passed" and not cancelled.is_set() and policy["mode"] == "accept_on_pass" and policy["user_authorized"] is True:
                try:
                    self._review(run_id, "accepted", "Adopted under the user's configured Passed policy.", None,
                                 "automation_policy", self.store.policy_provenance(policy["id"]), _return_envelope=False)
                except DomainError as error:
                    # Input or predecessor adoption can change while a tool is
                    # running. Keep its historical Passed proof; do not adopt it.
                    with self.lock:
                        self._run(run_id)["diagnostics"].append({"code": "automatic_adoption_blocked", "severity": "info", "message": error.message})
                        self._persist()
        except Exception as error:
            diagnostic = getattr(error, "execution_diagnostic", workflow_exception_diagnostic(error, phase))
            environment = (getattr(error, "code", None) == "workflow_environment_error"
                           or isinstance(error, OSError) and phase in {"prepare_artifact_directory", "execute_synthesis", "execute_netlist_simulation"})
            details = {"code": "workflow_environment_error" if environment else getattr(error, "code", "workflow_error"),
                       "message": ("Tool input storage could not be prepared. Fix the trusted tool working directory and retry this stage using the same saved RTL."
                                   if getattr(error, "code", None) == "workflow_environment_error" else
                                   "The tool execution environment failed. Inspect the fixed tool setup and retry this stage using the same saved RTL."
                                   if environment else getattr(error, "message", "Tool execution or durable workflow recording failed.")),
                       **diagnostic}
            if environment:
                details["next_action"] = "retry_same_RTL"
            with self.lock:
                run = self._run(run_id)
                run.update(execution_status="Cancelled" if cancelled.is_set() else "Failed", validation_status="Not Checked",
                           finished_at=utc_now(), error=details)
                try:
                    self._persist()
                except OSError:
                    pass

    def _review(self, run_id, decision, note, target_stage, actor, provenance=None, *, _return_envelope=True):
        self.observe_design()
        if decision not in ("accepted", "changes_requested", "return_to_stage") or type(note) is not str or decision != "accepted" and not note.strip():
            raise DomainError("invalid_workflow_review", "Provide a valid decision and correction/return reason.")
        with self.lock:
            run = self._run(run_id)
            decorated = self._decorate(run)
            if run["execution_status"] in ACTIVE or decorated["freshness"] != "Current":
                raise DomainError("workflow_not_reviewable", "Wait for a current completed workflow result.", 409)
            relevant = [item for item in self._state["runs"] if item["stage_id"] == run["stage_id"] and item["node_id"] == run["node_id"]]
            if relevant[-1]["id"] != run_id:
                raise DomainError("workflow_superseded", "Review the latest stage result for this node.", 409)
            if decision == "accepted":
                self._prerequisites()
                if actor == "automation_policy":
                    active_policy = self.store.review_policy()
                    if active_policy["mode"] != "accept_on_pass" or active_policy["user_authorized"] is not True or active_policy["id"] != provenance.get("policy_id"):
                        raise DomainError("review_policy_changed", "Automatic adoption policy changed while the tool was running.", 409)
                if run["validation_status"] != "Passed" or run["execution_status"] != "Completed" or run["checks"].get("validation_status") != "Passed" or run["checks"].get("executed") is not True or run["checks"].get("exit_code") != 0:
                    raise DomainError("workflow_not_passed", "Only current Passed results can be adopted.", 409)
                if run["stage_id"] == STAGES[1]:
                    validate_generic_simulation_proof(run)
                candidate = self.generation.job(run["candidate_id"])
                if candidate["review_status"] != "Accepted" or candidate["freshness"] != "Current":
                    raise DomainError("candidate_not_adopted", "The source candidate adoption is no longer current.", 409)
                if run["stage_id"] == STAGES[1]:
                    prior = self._decorate(self._run(run["prior_run_id"]))
                    if prior["review_status"] != "Accepted" or prior["freshness"] != "Current":
                        raise DomainError("synthesis_not_adopted", "The source netlist synthesis adoption is no longer current.", 409)
                run.update(review_status="Accepted", acceptance_epoch=self._state["node_epochs"][run["node_id"]])
            else:
                if decision == "return_to_stage" and target_stage not in (*IMPLEMENTED_STAGES, "local_rtl_generation", *STAGES):
                    raise DomainError("invalid_target_stage", "Choose an implemented earlier stage.")
                run["review_status"] = "Changes Requested"
            record = {"id": new_id("workflow-review"), "run_id": run_id, "decision": decision, "note": note,
                      "actor": actor, "target_stage": target_stage, "created_at": utc_now(),
                      "acceptance_epoch": run.get("acceptance_epoch"), "reviewed_revision_id": self.store.envelope()["revision"]["id"]}
            if provenance:
                record["provenance"] = copy.deepcopy(provenance)
            self._state["reviews"].append(record)
            self._persist()
        # Internal worker adoption needs the durable decision, not a complete
        # decorated history. Building that unused read view delays worker exit
        # and leaves its parent batch visibly Running after the tool finished.
        return self._result_envelope() if _return_envelope else None

    def review(self, run_id, decision, note, target_stage=None, *, operator=None):
        fields = manual_review_fields(operator)
        return self._review(run_id, decision, note, target_stage, fields["actor"], fields["provenance"])

    def cancel(self, run_id):
        with self.lock:
            if self._run(run_id)["execution_status"] not in ACTIVE:
                raise DomainError("workflow_not_active", "Only an active tool operation can be cancelled.", 409)
            self._cancel.set()
        return self._result_envelope()

    def close(self):
        self._closed = True
        self._batch_cancel.set()
        self._cancel.set()

"""S11 routed-layout history with exact adopted S08/S09/S10 lineage.

No model calls, source edits, signoff DRC/LVS or dynamic SDF verification.
Large physical artifacts remain files, identified by fixed IDs and raw hashes.
"""
from __future__ import annotations

import copy
from contextlib import ExitStack, contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import threading

from .domain import DomainError, IMPLEMENTED_STAGES
from .envelope_cache import memoized_envelope
from .observation import ObservedState, persist_observation, require_durable_write
from .execution_submissions import PROTOCOL_VERSION, submission_view, validate_submissions
from .global_generation import NODE_IDS, require, validate_global_plan
from .global_workflow import source_bundle, validate_synthesis_proof, validate_netlist_proof
from .implementation_specs import execution_evidence_hash
from .presentation_revision import same_revision_design
from .store import new_id, strict_loads, utc_now, validate_policy_history, validate_policy_review, _replace_with_windows_retry
from .store import _io_path
from .review_actor import REVIEW_ACTORS, manual_review_fields
from .verification import content_hash, object_hash
from .physical_tools import effective_configuration
from .block_layout import validate_block_plan
from .block_recipe import (is_block_configuration, source_input as block_source_input,
                           BLOCK_ARTIFACTS, VERSION as BLOCK_VERSION)

STAGE = "layout"
ACTIVE = {"Queued", "Running"}
CLEANUP_BLOCKED = "A previous physical run has unresolved process cleanup. New execution is blocked until its termination is verified."
EARLIER = (*IMPLEMENTED_STAGES, "local_rtl_generation", "local_synthesis", "local_netlist_simulation",
           "node_implementation_specs", "global_rtl_generation", "global_synthesis", "global_netlist_simulation")
JSON_ARTIFACTS = {"source-manifest", "verification-plan", "settings", "runtime-configuration", "artifact-manifest"}
BASE_FILE_IDS = {"config", "sdc", "metrics", "def", "gds", "png", "netlist", "final-state", "tool-versions", "input-manifest", "rtl-top"}
BASE_REQUIRED_FILES = {"config", "sdc", "metrics", "def", "gds", "png", "netlist", "final-state", "tool-versions", "rtl-top"}
# Public constants retain the historical six-node set for callers/tests that
# inspect the old record format. New records derive their node artifacts from
# the immutable source bundle rather than changing the saved schema.
FILE_IDS = BASE_FILE_IDS | {"rtl-" + n for n in NODE_IDS}
REQUIRED_FILES = BASE_REQUIRED_FILES | {"rtl-" + n for n in NODE_IDS}
NODE_FILE_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
LIMITS = ["S11 confirms the pinned physical adapter's routing/timing checks and saved artifact correspondence.",
          "S09/S10 are prerequisite generic finite evidence; their netlist is not substituted for fresh PDK mapping.",
          "No signoff DRC, LVS, formal equivalence or SDF dynamic simulation is implied."]


def _raw_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _node_artifact_ids(result):
    bundle=result.get("source_bundle")
    if bundle is None:
        # Compatibility for historical helper callers that predate a supplied
        # bundle. Actual S11 results have always retained source_bundle.
        return tuple("rtl-" + node_id for node_id in NODE_IDS)
    require(type(bundle) is list and len(bundle)>1 and type(bundle[0]) is dict
            and bundle[0].get("file")=="candidate_top.v",
            "physical_source_manifest_invalid", "Physical artifacts require the retained top and node source bundle.")
    artifact_ids=[];seen_files={"candidate_top.v"};seen_artifact_ids={"rtl-top"}
    for entry in bundle[1:]:
        filename=entry.get("file") if type(entry) is dict else None
        match=re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*)\.v",filename or "")
        artifact_id="rtl-"+match[1] if match is not None else ""
        require(match is not None and NODE_FILE_IDENTIFIER.fullmatch(match[1]) is not None
                and filename.casefold() not in seen_files and artifact_id.casefold() not in seen_artifact_ids,
                "physical_source_identifier_invalid", "Physical source filenames must use unique safe, nonreserved node identifiers.")
        seen_files.add(filename.casefold());seen_artifact_ids.add(artifact_id.casefold());artifact_ids.append(artifact_id)
    return tuple(artifact_ids)


def _file_ids(result):
    return BASE_FILE_IDS | set(_node_artifact_ids(result)) | (BLOCK_ARTIFACTS if result.get("placement_mode")==BLOCK_VERSION else set())


def _required_files(result):
    return BASE_REQUIRED_FILES | set(_node_artifact_ids(result)) | (BLOCK_ARTIFACTS if result.get("placement_mode")==BLOCK_VERSION else set())


def _artifact_path(result, entry):
    require(type(entry) is dict and entry.get("id") in _file_ids(result) and type(entry.get("relative_path")) is str
            and type(entry.get("sha256")) is str and len(entry["sha256"]) == 64
            and all(c in "0123456789abcdef" for c in entry["sha256"])
            and type(entry.get("bytes")) is int and entry["bytes"] > 0
            and type(entry.get("content_type")) is str
            and re.fullmatch(r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+(?:; charset=utf-8)?",entry["content_type"]),
            "physical_artifact_invalid", "Physical files require fixed IDs, raw hashes, positive integer lengths and media types.")
    relative=PurePosixPath(entry["relative_path"])
    require(not relative.is_absolute() and relative.parts and not any(p in (".","..") for p in relative.parts)
            and "\\" not in entry["relative_path"] and ":" not in entry["relative_path"]
            and not any(ord(c) < 32 for c in entry["relative_path"]),
            "physical_artifact_path_invalid", "Physical artifacts must stay below their recorded result directory.")
    require(type(result.get("artifacts_directory")) is str and Path(result["artifacts_directory"]).is_absolute(),
            "physical_artifact_path_invalid", "Use the retained absolute adapter result directory.")
    root=Path(result["artifacts_directory"]).resolve(); path=(root/Path(*relative.parts)).resolve()
    require(path.is_relative_to(root) and path!=root and path.is_file(),
            "physical_artifact_missing", "The saved physical artifact is missing or outside its result directory.")
    return path


def validate_artifact_manifest(result, passed=False):
    artifacts=result.get("artifacts",[])
    require(type(artifacts) is list,"physical_artifact_invalid","Physical artifacts must be a fixed-ID manifest.")
    ids=set(); paths=set()
    for entry in artifacts:
        path=_artifact_path(result,entry)
        require(entry["id"] not in ids and path not in paths and path.stat().st_size==entry["bytes"] and _raw_hash(path)==entry["sha256"],
                "physical_artifact_hash_conflict","Saved physical bytes must match the original manifest, without duplicate IDs.")
        ids.add(entry["id"])
        paths.add(path)
    require(not passed or _required_files(result)<=ids,"physical_artifact_missing","A Passed routed result requires RTL inputs, constraints, metrics, DEF/GDS/PNG, mapped netlist, state and tool versions.")


def _command_pass(command):
    return type(command) is dict and command.get("executed") is True and command.get("status")=="Completed" and type(command.get("exit_code")) is int and command["exit_code"]==0


REVALIDATION_FIELDS=("revision_id","global_job_id","synthesis_run_id","netlist_run_id","global_context_id",
    "global_rtl","global_rtl_sha256","source_manifest","source_manifest_sha256","verification_plan","verification_plan_sha256",
    "vector_hash","testbench_sha256","public_boundary_vector_hash","settings","settings_sha256","runtime_configuration",
    "runtime_configuration_sha256","source_identity","source_key","source_epoch_at_start")


def validate_revalidation_candidate(prior):
    result=prior["checks"]
    require(prior.get("evidence_kind")=="trusted_fixed_tool_execution" and prior.get("execution_status") in ("Completed","Failed")
            and result.get("origin")=="trusted_fixed_tool_adapter" and result.get("software_qa_fixture") is not True
            and result.get("cleanup_unresolved") is not True and result.get("executed") is True
            and type(result.get("exit_code")) is int and result["exit_code"]==0
            and type(result.get("commands")) is list and len(result["commands"])==2 and all(_command_pass(c) for c in result["commands"])
            and all(result.get(field)==prior[field] for field in ("global_rtl_sha256","source_manifest_sha256","settings_sha256","runtime_configuration_sha256"))
            and object_hash(result.get("source_bundle"))==object_hash(source_bundle(prior["global_rtl"],prior["source_manifest"]))
            and all(type(result.get(field)) is str for field in ("stdout","stderr","artifacts_directory")),
            "physical_revalidation_unavailable","Recheck only the unchanged saved outputs of a completed actual tool execution with resolved cleanup.")


def validate_revalidation_link(run,prior,require_result=True):
    """Public pure linkage check; successful tool proof is validated separately."""
    validate_revalidation_candidate(prior)
    require(run.get("evidence_kind")=="trusted_saved_tool_revalidation" and run.get("execution_kind")=="saved_outputs_no_new_tool_start"
            and run.get("prior_run_id")==prior["id"] and run.get("prior_record_sha256")==object_hash(prior)
            and run.get("previous_result_sha256")==object_hash(prior["checks"])
            and object_hash({field:run[field] for field in REVALIDATION_FIELDS})==object_hash({field:prior[field] for field in REVALIDATION_FIELDS}),
            "physical_revalidation_conflict","Saved-output revalidation must bind its unchanged prior record, source epoch, settings and runtime.")
    if require_result:
        result=run["checks"]
        require(result.get("execution_reused") is True and result.get("revalidated_from_run_id")==prior["id"]
                and result.get("previous_result_sha256")==run["previous_result_sha256"]
                and type(result.get("revalidation_tool_starts")) is int and result["revalidation_tool_starts"]==0
                and type(result.get("revalidation_model_calls")) is int and result["revalidation_model_calls"]==0
                and object_hash(result.get("commands"))==object_hash(prior["checks"]["commands"])
                and all(result.get(field)==prior["checks"][field] for field in ("stdout","stderr","artifacts_directory"))
                and result.get("origin")=="trusted_fixed_tool_adapter" and result.get("software_qa_fixture") is not True
                and result.get("cleanup_unresolved") is not True,
                "physical_revalidation_conflict","Revalidation must reuse the original executed commands/logs and start zero tools or models.")


def _validate_physical_proof(run, validator, expected_status):
    result=run["checks"]
    require(type(result) is dict and result.get("cleanup_unresolved") is not True,"physical_cleanup_unresolved",CLEANUP_BLOCKED)
    require(type(result) is dict and result.get("validation_status")==expected_status and result.get("executed") is True
            and type(result.get("exit_code")) is int and result["exit_code"]==0
            and result.get("global_rtl_sha256")==run["global_rtl_sha256"]
            and result.get("source_manifest_sha256")==run["source_manifest_sha256"]
            and result.get("settings_sha256")==run["settings_sha256"]
            and result.get("runtime_configuration_sha256")==run["runtime_configuration_sha256"]
            and object_hash(result.get("source_bundle"))==object_hash(source_bundle(run["global_rtl"],run["source_manifest"]))
            and type(result.get("commands")) is list and result["commands"] and all(_command_pass(c) for c in result["commands"])
            and type(result.get("metrics")) is dict and type(result.get("diagnostics")) is list
            and all(result.get("checks",{}).get(name,{}).get("validation_status")=="Passed" for name in ("source_identity","configuration","routing","timing"))
            and result["checks"]["routing"].get("executed") is True and result["checks"]["routing"].get("completed") is True
            and result["checks"]["timing"].get("executed") is True,
            "physical_proof_conflict","A complete layout proof requires executed fixed tools, unchanged sources/settings/profile and actual routing/timing checks.")
    validate_artifact_manifest(result,True)
    require(validator(result,run["global_rtl"],run["source_manifest"],run["settings"],run["runtime_configuration"]) is None,
            "physical_proof_conflict","The trusted adapter validator must explicitly complete without a mismatch.")


def validate_physical_proof(run, validator):
    _validate_physical_proof(run, validator, "Passed")


def validate_failed_physical_proof(run, validator):
    require(run.get("execution_status") == "Completed" and run.get("validation_status") == "Failed",
            "physical_proof_conflict", "Only a complete actual failed layout can be inspected for fixed correction.")
    _validate_physical_proof(run, validator, "Failed")


class PhysicalWorkflowManager(ObservedState):
    def __init__(self,store,global_generation,global_workflow,tool_configuration=None,layout_runner=None,layout_validator=None):
        require((layout_runner is None)==(layout_validator is None),"physical_adapter_invalid","An isolated injected runner requires its matching explicit proof validator.")
        self.store,self.global_generation,self.global_workflow=store,global_generation,global_workflow
        self.tool_configuration=copy.deepcopy(tool_configuration)
        self._injected=layout_runner is not None; self._runner,self._validator=layout_runner,layout_validator
        self.path=store.state_path.parent/"physical_workflow.json"; self.lock=threading.RLock()
        self._worker=None; self._cancel=threading.Event(); self._closed=False; self._storage_error=None
        self._state={"physical_workflow_store_version":"0.1","runs":[],"reviews":[],"source_key":None,"source_epoch":0,"source_transitions":[]}
        if _io_path(self.path).exists():
            try: self._state=strict_loads(_io_path(self.path).read_text(encoding="utf-8")); self._validate_saved()
            except (DomainError,OSError,ValueError,KeyError,TypeError,AttributeError) as error:
                raise DomainError("invalid_physical_workflow_store","Physical history is inconsistent; the original file is preserved.",500) from error
        self._committed=copy.deepcopy(self._state)
        interrupted=False
        for run in self._state["runs"]:
            if run["execution_status"] in ACTIVE:
                run.update(execution_status="Interrupted",validation_status="Not Checked",finished_at=utc_now(),error={"code":"service_restarted","message":"Interrupted physical execution retained; no tool operation was resent. Process termination requires verification."})
                run["checks"]["cleanup_unresolved"]=True; interrupted=True
        if interrupted: self._persist()

    def _adapter(self):
        if self._runner is None:
            from .physical_tools import run_layout, validate_layout_result
            return run_layout,validate_layout_result
        return self._runner,self._validator

    @contextmanager
    def _source_locks(self):
        global_manager=self.global_generation
        with ExitStack() as stack:
            for manager in (global_manager,global_manager.specifications,global_manager.workflow,global_manager.generation,self.store,self.global_workflow):
                stack.enter_context(manager.lock)
            yield

    def _source_state(self):
        with self._source_locks():
            current=self.store.envelope(); settings=current["design"]["settings"]
            try:
                configuration=effective_configuration(self.tool_configuration,current["design"])
                key,source,error=self.global_workflow.observe_design()
                require(source is not None and error is None,"physical_sources_not_current","Adopt current S08 and every required node source before physical design.")
                synthesis=self.global_workflow._latest("global_synthesis"); simulation=self.global_workflow._latest("global_netlist_simulation")
                require(synthesis is not None and simulation is not None,"physical_netlist_not_adopted","Adopt S09 and S10 of this exact whole-system candidate first.")
                synthesis_effective=self.global_workflow._decorate(synthesis); simulation_effective=self.global_workflow._decorate(simulation)
                require(all(r["execution_status"]=="Completed" and r["validation_status"]=="Passed" and r["review_status"]=="Accepted" and r["freshness"]=="Current" for r in (synthesis_effective,simulation_effective)),
                        "physical_netlist_not_adopted","The latest exact S09/S10 results must remain Passed, Accepted and Current.")
                job=source["job"]; manifest=source["manifest"]; plan=job["context"]["verification_plan"]
                if is_block_configuration(configuration):
                    block_source_input(configuration,manifest,settings["top_module"])
                require(synthesis["global_job_id"]==simulation["global_job_id"]==job["id"] and simulation["prior_run_id"]==synthesis["id"]
                        and synthesis["netlist_sha256"]==simulation["netlist_sha256"] and synthesis["netlist"]==simulation["netlist"]
                        and synthesis["source_key"]==simulation["source_key"]==key
                        and all(object_hash(r["source_manifest"])==object_hash(manifest) and object_hash(r["verification_plan"])==object_hash(plan) for r in (synthesis,simulation)),
                        "physical_lineage_conflict","Keep the identical adopted S08, S09 netlist, S10 proof and original plan.")
                validate_synthesis_proof(synthesis); validate_netlist_proof(simulation)
                adoptions={stage:[r for r in self.global_workflow._state["reviews"] if r["run_id"]==record["id"]][-1]
                           for stage,record in (("synthesis",synthesis),("netlist",simulation))}
                require(all(r["decision"]=="accepted" for r in adoptions.values())
                        and object_hash(simulation["synthesis_adoption"])==object_hash(adoptions["synthesis"]),
                        "physical_adoption_conflict","Retain the latest authoritative S09/S10 adoption chain.")
                identity={"revision_id":job["revision_id"],"global_job_id":job["id"],"global_context_id":job["context_id"],
                    "global_rtl_sha256":job["rtl_sha256"],"global_source_identity":source["identity"],"global_workflow_source_key":key,
                    "global_workflow_source_epoch":self.global_workflow._state["source_epoch"],"synthesis_run_id":synthesis["id"],"netlist_run_id":simulation["id"],
                    "synthesis_execution_hash":execution_evidence_hash(synthesis),"netlist_execution_hash":execution_evidence_hash(simulation),
                    "generic_netlist_sha256":synthesis["netlist_sha256"],"source_manifest_sha256":object_hash(manifest),"verification_plan_sha256":object_hash(plan),
                    "synthesis_adoption":adoptions["synthesis"],"netlist_adoption":adoptions["netlist"],
                    "settings_sha256":object_hash(settings),"runtime_configuration_sha256":object_hash(configuration)}
                physical_plan=validate_block_plan(current["design"].get("physical_design"),current["design"])
                if physical_plan is not None:
                    identity.update(physical_design_sha256=object_hash(physical_plan))
                return object_hash(identity),{"identity":identity,"job":job,"manifest":manifest,"plan":plan,"settings":copy.deepcopy(settings),"configuration":configuration,
                                             "physical_design_revision_id":current["revision"]["id"] if physical_plan is not None else None},None
            except DomainError as error:
                key=object_hash({"revision_id":current["revision"]["id"],"settings":settings,"blocked":error.code,
                    "upstream_key":self.global_workflow._state["source_key"],"upstream_epoch":self.global_workflow._state["source_epoch"],
                    "latest_tools":[[r["id"],r["review_status"],r.get("acceptance_epoch")] for r in self.global_workflow._state["runs"]],
                    "tool_reviews":self.global_workflow._state["reviews"],"runtime_configuration_sha256":object_hash(self.tool_configuration),
                    **({"physical_design":current["design"]["physical_design"]} if "physical_design" in current["design"] else {})})
                return key,None,{"code":error.code,"message":error.message}

    def observe_design(self):
        key,source,error=self._source_state()
        with self.lock:
            if key!=self._state["source_key"]:
                self._state["source_key"]=key; self._state["source_epoch"]+=1
                self._state["source_transitions"].append({"epoch":self._state["source_epoch"],"source_key":key,"created_at":utc_now()}); persist_observation(self)
        return key,source,error

    def _run(self,identifier):
        run=next((r for r in self._state["runs"] if r["id"]==identifier),None)
        require(run is not None,"physical_run_not_found","Physical execution does not exist.",404)
        return run

    def _decorate(self,run):
        value=copy.deepcopy(run); current=run["source_key"]==self._state["source_key"] and run["source_epoch_at_start"]==self._state["source_epoch"]
        value["freshness"]="Current" if current else "Stale"
        if value["review_status"]=="Accepted" and (not current or run.get("acceptance_epoch")!=self._state["source_epoch"]): value["review_status"]="Awaiting Review"
        value["artifacts"]=[{**entry,"url":"/api/artifacts/physical-workflow/"+run["id"]+"/"+entry["id"]} for entry in run["checks"].get("artifacts",[])]
        return value

    @memoized_envelope
    def envelope(self):
        _,source,error=self.observe_design()
        # Source/adoption guards acquire the project store before this result
        # lock. Capture display inputs in that same order: a terminal DRC
        # worker can hold the store while waiting for our result lock.
        current_design=self.store.envelope()["design"]; settings=current_design["settings"]
        with self.lock:
            runs=[self._decorate(r) for r in self._state["runs"]]; latest=runs[-1] if runs else None
            tool_ready=type(self.tool_configuration) is dict
            cleanup_unresolved=self._cleanup_unresolved()
            try:configuration=source["configuration"] if source is not None else effective_configuration(self.tool_configuration,current_design)
            except DomainError:configuration=self.tool_configuration
            physical_design=current_design.get("physical_design")
            return {"physical_workflow":{"implemented":True,"stage_id":STAGE,"runs":runs,"reviews":copy.deepcopy(self._state["reviews"]),
                "execution_submissions":submission_view(self),"submission_protocol_version":PROTOCOL_VERSION,
                "latest_run_id":latest["id"] if latest else None,"accepted_run_id":latest["id"] if latest and latest["review_status"]=="Accepted" and latest["freshness"]=="Current" else None,
                "ready":source is not None and tool_ready and not cleanup_unresolved,"blocked_reason":CLEANUP_BLOCKED if cleanup_unresolved else error["message"] if error else None if tool_ready else "Configure the pinned trusted physical runtime before S11.",
                "tool_ready":tool_ready,"tool_blocked_reason":None if tool_ready else "No trusted physical runtime is configured.","settings_projection":copy.deepcopy(settings),
                "runtime_configuration_sha256":object_hash(configuration),"runtime_configuration":copy.deepcopy(configuration),
                "placement_mode":"block_regions" if is_block_configuration(configuration) else "mixed",
                "physical_design":copy.deepcopy(physical_design),"placement_plan_sha256":source["identity"].get("physical_design_sha256") if source else None,
                "storage_error":copy.deepcopy(self._storage_error),"limits":list(LIMITS)}}

    def run(self,identifier):
        self.observe_design()
        with self.lock: return self._decorate(self._run(identifier))

    def _cleanup_unresolved(self):
        return any(r["checks"].get("cleanup_unresolved") is True for r in self._state["runs"])

    def is_active(self):
        # Admission also remains closed after a terminal report if termination
        # is unverified. Keep the actual terminal execution status unchanged.
        with self.lock: return self._cleanup_unresolved() or any(r["execution_status"] in ACTIVE for r in self._state["runs"])

    def start(self,stage_id,global_job_id,synthesis_run_id,netlist_run_id,revision_id=None,*,_submission=None):
        require(stage_id==STAGE and all(type(x) is str for x in (global_job_id,synthesis_run_id,netlist_run_id)) and (revision_id is None or type(revision_id) is str),
                "physical_request_invalid","S11 requires exact saved S08, S09 and S10 IDs.")
        with self.lock:
            require(not self._cleanup_unresolved(),"physical_cleanup_unresolved",CLEANUP_BLOCKED)
        require(type(self.tool_configuration) is dict,"physical_runtime_unavailable","Configure the pinned physical runtime before S11.",409)
        with self._source_locks():
            key,source,error=self.observe_design()
            require(source is not None,"physical_sources_not_current",error["message"] if error else "Adopt current source results first.")
            identity=source["identity"]; job=source["job"]; plan=source["plan"]
            require((global_job_id,synthesis_run_id,netlist_run_id)==(identity["global_job_id"],identity["synthesis_run_id"],identity["netlist_run_id"])
                    and (revision_id is None or revision_id==self.store.envelope()["revision"]["id"]),"physical_source_conflict","Continue from the exact latest adopted sources and current saved GUI revision.")
            require(not any(r["execution_status"] in ACTIVE for manager,field in ((self.global_generation,"jobs"),(self.global_generation.generation,"jobs"),
                    (self.global_generation.workflow,"runs"),(self.global_workflow,"runs")) for r in manager._state[field]),
                    "physical_peer_busy","Wait for model or earlier tool execution before physical design.")
            with self.lock:
                require(not self._cleanup_unresolved(),"physical_cleanup_unresolved",CLEANUP_BLOCKED)
                require(not self._closed and not self.is_active() and not (self._worker and self._worker.is_alive()),"physical_busy","Only one physical execution can run at a time.")
                run={"id":new_id("physical-workflow"),"stage_id":STAGE,"revision_id":job["revision_id"],"global_job_id":global_job_id,"synthesis_run_id":synthesis_run_id,"netlist_run_id":netlist_run_id,
                    "global_context_id":job["context_id"],"global_rtl":job["rtl"],"global_rtl_sha256":job["rtl_sha256"],"source_manifest":copy.deepcopy(source["manifest"]),"source_manifest_sha256":object_hash(source["manifest"]),
                    "verification_plan":copy.deepcopy(plan),"verification_plan_sha256":object_hash(plan),"vector_hash":plan["vector_hash"],"testbench_sha256":plan["testbench_sha256"],"public_boundary_vector_hash":plan["public_boundary_vector_hash"],
                    "settings":copy.deepcopy(source["settings"]),"settings_sha256":object_hash(source["settings"]),"runtime_configuration":copy.deepcopy(source["configuration"]),"runtime_configuration_sha256":object_hash(source["configuration"]),
                    "source_identity":copy.deepcopy(identity),"source_key":key,"source_epoch_at_start":self._state["source_epoch"],"execution_status":"Queued","validation_status":"Not Checked","review_status":"Awaiting Review",
                    "checks":{},"diagnostics":[],"created_at":utc_now(),"finished_at":None,"error":None,"evidence_kind":"software_qa_fixture" if self._injected else "trusted_fixed_tool_execution","limits":list(LIMITS)}
                if source.get("physical_design_revision_id") is not None:
                    run["physical_design_revision_id"]=source["physical_design_revision_id"]
                if _submission is not None:
                    run["submission_id"]=_submission.submission_id
                    _submission.bind(run["id"])
                self._state["runs"].append(run); self._persist(); self._cancel=threading.Event()
                self._worker=threading.Thread(target=self._execute,args=(run["id"],self._cancel),daemon=True,name="HuLLCirq-physical-layout"); self._worker.start()
        return self.envelope()

    def revalidate(self,identifier):
        require(type(identifier) is str,"physical_request_invalid","Select the exact saved physical execution to recheck.")
        require(not self._injected,"physical_fixture_rejected","Injected software fixtures cannot be promoted into actual saved-tool evidence.")
        require(type(self.tool_configuration) is dict,"physical_runtime_unavailable","Configure the same pinned physical runtime before rechecking saved outputs.",409)
        with self._source_locks():
            key,source,error=self.observe_design()
            require(source is not None,"physical_sources_not_current",error["message"] if error else "Keep the original adopted sources current.")
            require(not any(r["execution_status"] in ACTIVE for manager,field in ((self.global_generation,"jobs"),(self.global_generation.generation,"jobs"),
                    (self.global_generation.workflow,"runs"),(self.global_workflow,"runs")) for r in manager._state[field]),
                    "physical_peer_busy","Wait for model or earlier tool execution before rechecking saved physical outputs.")
            with self.lock:
                require(not self._cleanup_unresolved(),"physical_cleanup_unresolved",CLEANUP_BLOCKED)
                require(not self._closed and not self.is_active() and not (self._worker and self._worker.is_alive()),"physical_busy","Only one physical operation can run at a time.")
                prior=self._run(identifier)
                require(self._state["runs"][-1]["id"]==identifier,"physical_superseded","Recheck only the latest original actual tool execution.")
                require(self._decorate(prior)["freshness"]=="Current" and prior["source_key"]==key
                        and object_hash(prior["source_identity"])==object_hash(source["identity"])
                        and prior["runtime_configuration_sha256"]==object_hash(source["configuration"]),
                        "physical_source_conflict","Recheck only the exact current source, settings, runtime and adoption epoch.")
                validate_revalidation_candidate(prior)
                run=copy.deepcopy(prior)
                for field in ("record_hash","acceptance_epoch","submission_id"):
                    run.pop(field,None)
                run.update(id=new_id("physical-workflow"),execution_status="Queued",validation_status="Not Checked",review_status="Awaiting Review",
                    checks={},diagnostics=[],created_at=utc_now(),finished_at=None,error=None,evidence_kind="trusted_saved_tool_revalidation",
                    execution_kind="saved_outputs_no_new_tool_start",prior_run_id=identifier,prior_record_sha256=object_hash(prior),
                    previous_result_sha256=object_hash(prior["checks"]))
                validate_revalidation_link(run,prior,False)
                self._state["runs"].append(run); self._cancel=threading.Event(); self._persist()
                self._worker=threading.Thread(target=self._execute,args=(run["id"],self._cancel),daemon=True,name="HuLLCirq-physical-revalidation"); self._worker.start()
        return self.envelope()

    def _execute(self,identifier,cancel):
        try:
            with self.lock:
                run=self._run(identifier); run["execution_status"]="Running"; self._persist(); frozen=copy.deepcopy(run)
            runner,validator=self._adapter()
            revalidation=frozen["evidence_kind"]=="trusted_saved_tool_revalidation"
            if revalidation:
                from .physical_tools import revalidate_layout
                with self.lock:
                    prior=copy.deepcopy(self._run(frozen["prior_run_id"]))
                validate_revalidation_link(frozen,prior,False)
                result=revalidate_layout(frozen["global_rtl"],frozen["source_manifest"],frozen["settings"],frozen["runtime_configuration"],
                    copy.deepcopy(prior["checks"]),prior["id"],cancel_event=cancel)
            else:
                result=runner(frozen["global_rtl"],frozen["source_manifest"],frozen["settings"],frozen["runtime_configuration"],cancel_event=cancel)
            require(type(result) is dict and result.get("validation_status") in ("Passed","Failed","Unsupported","Not Checked")
                    and type(result.get("diagnostics")) is list,"physical_result_invalid","The fixed physical adapter must return structured executed evidence.")
            if revalidation:
                try: validate_revalidation_link({**frozen,"checks":result},prior)
                except DomainError:
                    with self.lock:
                        self._run(identifier)["revalidation_rejected_report"]=copy.deepcopy(result); self._persist()
                    raise
            # Preserve a returned adapter report even when proof validation
            # refuses it. A rejected pass flag must not erase real tool logs.
            with self.lock:
                run=self._run(identifier); run.update(checks=copy.deepcopy(result),diagnostics=copy.deepcopy(result["diagnostics"])); self._persist()
            require(self._injected or result.get("software_qa_fixture") is not True,"physical_fixture_rejected","Software fixtures cannot become actual physical execution evidence.")
            if result["validation_status"]=="Passed":
                proof={**frozen,"checks":result}; validate_physical_proof(proof,validator)
            else: validate_artifact_manifest(result)
            with self.lock:
                run=self._run(identifier); run.update(execution_status="Cancelled" if cancel.is_set() else "Completed",validation_status="Not Checked" if cancel.is_set() else result["validation_status"],
                    checks=copy.deepcopy(result),diagnostics=copy.deepcopy(result["diagnostics"]),finished_at=utc_now()); self._persist()
            self.observe_design(); policy=self.store.review_policy()
            if not cancel.is_set() and result["validation_status"]=="Passed" and policy["mode"]=="accept_on_pass" and policy["user_authorized"] is True:
                try: self._review(identifier,"accepted","Adopted under the user's configured Passed policy.",None,"automation_policy",self.store.policy_provenance(policy["id"]))
                except DomainError as error:
                    with self.lock:
                        self._run(identifier)["diagnostics"].append({"code":"automatic_adoption_blocked","severity":"info","message":error.message}); self._persist()
        except Exception as error:
            with self.lock:
                run=self._run(identifier); run.update(execution_status="Cancelled" if cancel.is_set() else "Failed",validation_status="Not Checked",finished_at=utc_now(),
                    error={"code":getattr(error,"code","physical_workflow_error"),"message":getattr(error,"message","Physical execution or durable evidence recording failed.")})
                try: self._persist()
                except (OSError,ValueError,TypeError): pass

    def _review(self,identifier,decision,note,target_stage,actor,provenance=None):
        require(decision in ("accepted","changes_requested","return_to_stage") and type(note) is str and (decision=="accepted" or note.strip()),
                "physical_review_invalid","Provide a valid decision and correction/return reason.")
        require(target_stage in EARLIER if decision=="return_to_stage" else target_stage is None,"invalid_target_stage","Return only to implemented S01-S10.")
        with self._source_locks():
            self.observe_design()
            with self.lock:
                run=self._run(identifier); decorated=self._decorate(run)
                require(run["execution_status"] not in ACTIVE and self._state["runs"][-1]["id"]==identifier,"physical_superseded","Review the latest completed physical result.")
                if decision=="accepted":
                    require(not self._cleanup_unresolved(),"physical_cleanup_unresolved",CLEANUP_BLOCKED)
                    require(decorated["freshness"]=="Current" and run["execution_status"]=="Completed" and run["validation_status"]=="Passed",
                            "physical_not_passed","Only the exact current executed Passed layout may be adopted.")
                    if run["evidence_kind"]=="trusted_saved_tool_revalidation": validate_revalidation_link(run,self._run(run["prior_run_id"]))
                    validate_physical_proof(run,self._adapter()[1])
                    if actor=="automation_policy":
                        policy=self.store.review_policy()
                        require(policy["mode"]=="accept_on_pass" and policy["user_authorized"] is True and provenance is not None and provenance.get("policy_id")==policy["id"],
                                "review_policy_changed","The automatic adoption policy changed while physical tools ran.")
                    run.update(review_status="Accepted",acceptance_epoch=self._state["source_epoch"])
                else: run["review_status"]="Changes Requested"
                review={"id":new_id("physical-review"),"run_id":identifier,"decision":decision,"note":note,"target_stage":target_stage,"actor":actor,
                    "source_key":run["source_key"],"acceptance_epoch":run.get("acceptance_epoch"),"reviewed_revision_id":self.store.envelope()["revision"]["id"],"created_at":utc_now()}
                if provenance: review["provenance"]=copy.deepcopy(provenance)
                self._state["reviews"].append(review); self._persist()
        return self.envelope()

    def review(self,identifier,decision,note,target_stage=None, *, operator=None):
        fields = manual_review_fields(operator)
        return self._review(identifier, decision, note, target_stage, fields["actor"], fields["provenance"])

    def cancel(self,identifier):
        with self.lock:
            require(self._run(identifier)["execution_status"] in ACTIVE,"physical_not_active","Only active physical execution can be cancelled."); self._cancel.set()
        return self.envelope()

    def block_placement(self,identifier):
        """Inspect one immutable saved proof without observing or saving state."""
        require(type(identifier) is str and identifier and not any(c in identifier for c in ("/","\\","\x00")),
                "physical_run_not_found","Select one exact saved physical execution.",404)
        with self.lock:
            selected=copy.deepcopy(self._run(identifier)); display=self._decorate(selected)
            historical=bool(self._state["runs"] and self._state["runs"][-1]["id"]!=identifier or display["freshness"]!="Current")
        from .block_placement_view import block_placement_projection
        value=block_placement_projection(selected,lambda run:validate_physical_proof(run,self._adapter()[1]))
        value["status"]={key:display[key] for key in ("execution_status","validation_status","review_status","freshness")}
        value["historical"]=historical
        return value

    def artifact_file(self,identifier,artifact_id):
        with self.lock:
            result=copy.deepcopy(self._run(identifier)["checks"])
        entry=next((e for e in result.get("artifacts",[]) if e["id"]==artifact_id),None)
        require(entry is not None and artifact_id in _file_ids(result),"physical_artifact_not_found","Only retained source-bound physical artifacts are available.",404)
        path=_artifact_path(result,entry)
        require(path.stat().st_size==entry["bytes"] and _raw_hash(path)==entry["sha256"],"physical_artifact_hash_conflict","The original saved artifact bytes changed.")
        return {**entry,"path":path}

    def artifact_bytes(self,identifier,artifact_id):
        entry=self.artifact_file(identifier,artifact_id); payload=entry["path"].read_bytes()
        require(len(payload)==entry["bytes"] and hashlib.sha256(payload).hexdigest()==entry["sha256"],"physical_artifact_hash_conflict","Physical bytes changed during download.")
        return payload,entry["content_type"]

    def artifact(self,identifier,field):
        with self.lock: run=copy.deepcopy(self._run(identifier))
        fields={"source-manifest":"source_manifest","verification-plan":"verification_plan","settings":"settings","runtime-configuration":"runtime_configuration"}
        if field in fields: return run[fields[field]]
        if field=="artifact-manifest": return copy.deepcopy(run["checks"].get("artifacts",[]))
        if field in _file_ids(run["checks"])-{"gds","png"}:
            data,_=self.artifact_bytes(identifier,field)
            try: return data.decode("utf-8")
            except UnicodeError as error: raise DomainError("physical_artifact_not_text","Use the binary artifact endpoint for this file.") from error
        raise DomainError("physical_artifact_not_found","Only fixed physical documents and retained artifacts are available.",404)

    def _validate_saved(self):
        state=self._state
        require(type(state) is dict and state.get("physical_workflow_store_version")=="0.1" and type(state.get("runs")) is list and type(state.get("reviews")) is list
                and type(state.get("source_epoch")) is int and state["source_epoch"]>=0 and type(state.get("source_transitions")) is list,
                "physical_history_invalid","Invalid physical history containers.")
        transitions=state["source_transitions"]
        require([t["epoch"] for t in transitions]==list(range(1,state["source_epoch"]+1)) and (transitions[-1]["source_key"] if transitions else None)==state["source_key"]
                and all(type(t["epoch"]) is int and type(t["source_key"]) is str for t in transitions),"physical_history_invalid","Physical source epochs are inconsistent.")
        policies=validate_policy_history(self.store.envelope()); ids=set()
        for index,run in enumerate(state["runs"]):
            require(type(run) is dict and all(type(run.get(k)) is str for k in ("id","stage_id","revision_id","global_job_id","synthesis_run_id","netlist_run_id","global_context_id","global_rtl","source_key","created_at"))
                    and all(type(run.get(k)) is dict for k in ("source_identity","source_manifest","verification_plan","settings","runtime_configuration","checks")) and type(run.get("diagnostics")) is list
                    and run["stage_id"]==STAGE and run["id"] not in ids and type(run.get("source_epoch_at_start")) is int
                    and run["execution_status"] in ACTIVE|{"Completed","Failed","Cancelled","Interrupted"} and run["validation_status"] in ("Not Checked","Passed","Failed","Unsupported")
                    and run["review_status"] in ("Awaiting Review","Accepted","Changes Requested") and run.get("record_hash")==object_hash({k:v for k,v in run.items() if k!="record_hash"})
                    and run.get("evidence_kind") in ({"software_qa_fixture"} if self._injected else {"trusted_fixed_tool_execution","trusted_saved_tool_revalidation"}),
                    "physical_record_invalid","Physical record types, origin, statuses or checksum differ.")
            job=self.global_generation._job(run["global_job_id"]); manifest=job["context"]["source_manifest"]; plan=job["context"]["verification_plan"]
            synthesis=self.global_workflow._run(run["synthesis_run_id"]); simulation=self.global_workflow._run(run["netlist_run_id"]); identity=run["source_identity"]
            snapshot=self.store.snapshot(run["revision_id"])
            if "physical_design_sha256" in identity:
                physical_snapshot=self.store.snapshot(run.get("physical_design_revision_id"))
                physical_plan=validate_block_plan(physical_snapshot.get("physical_design"),physical_snapshot)
                require(same_revision_design(self.store,run["revision_id"],run.get("physical_design_revision_id"))
                        and physical_plan is not None and object_hash(physical_plan)==identity["physical_design_sha256"]
                        and (not is_block_configuration(run["runtime_configuration"]) or object_hash(run["runtime_configuration"].get("block_plan"))==identity["physical_design_sha256"]),
                        "block_region_source","Preserve the exact saved physical plan independently of the older logical source revision.")
            require(run["revision_id"]==job["revision_id"] and run["global_context_id"]==job["context_id"] and run["global_rtl"]==job["rtl"] and run["global_rtl_sha256"]==content_hash(job["rtl"])
                    and object_hash(run["source_manifest"])==object_hash(manifest)==run["source_manifest_sha256"]
                    and object_hash(run["verification_plan"])==object_hash(plan)==run["verification_plan_sha256"] and all(run[k]==plan[k] for k in ("vector_hash","testbench_sha256","public_boundary_vector_hash"))
                    and object_hash(run["settings"])==object_hash(snapshot["settings"])==run["settings_sha256"] and object_hash(run["runtime_configuration"])==run["runtime_configuration_sha256"]
                    and synthesis["stage_id"]=="global_synthesis" and simulation["stage_id"]=="global_netlist_simulation" and simulation["prior_run_id"]==synthesis["id"]
                    and synthesis["global_job_id"]==simulation["global_job_id"]==job["id"] and synthesis["netlist_sha256"]==simulation["netlist_sha256"]
                    and identity.get("global_job_id")==job["id"] and identity.get("global_context_id")==job["context_id"] and identity.get("revision_id")==run["revision_id"]
                    and identity.get("global_rtl_sha256")==run["global_rtl_sha256"] and object_hash(identity.get("global_source_identity"))==object_hash(synthesis["source_identity"])
                    and identity.get("global_workflow_source_key")==synthesis["source_key"]==simulation["source_key"] and type(identity.get("global_workflow_source_epoch")) is int
                    and identity["global_workflow_source_epoch"]==synthesis["source_epoch_at_start"]==simulation["source_epoch_at_start"]
                    and identity.get("synthesis_run_id")==synthesis["id"] and identity.get("netlist_run_id")==simulation["id"]
                    and identity.get("synthesis_execution_hash")==execution_evidence_hash(synthesis) and identity.get("netlist_execution_hash")==execution_evidence_hash(simulation)
                    and identity.get("generic_netlist_sha256")==synthesis["netlist_sha256"] and identity.get("source_manifest_sha256")==run["source_manifest_sha256"]
                    and identity.get("verification_plan_sha256")==run["verification_plan_sha256"] and identity.get("settings_sha256")==run["settings_sha256"]
                    and identity.get("runtime_configuration_sha256")==run["runtime_configuration_sha256"] and run["source_key"]==object_hash(identity)
                    and any(t["epoch"]==run["source_epoch_at_start"] and t["source_key"]==run["source_key"] for t in transitions),
                    "physical_source_conflict","Physical history must retain its exact original adopted S08/S09/S10, GUI settings, profile and source epoch.")
            for field,record in (("synthesis_adoption",synthesis),("netlist_adoption",simulation)):
                adoption=identity.get(field)
                require(type(adoption) is dict and adoption.get("run_id")==record["id"] and adoption.get("decision")=="accepted"
                        and any(object_hash(adoption)==object_hash(r) for r in self.global_workflow._state["reviews"]),"physical_adoption_conflict","Retain the original authoritative upstream adoption records.")
            require(object_hash(identity["synthesis_adoption"])==object_hash(simulation["synthesis_adoption"]),"physical_adoption_conflict","S10's adopted S09 must equal the physical source adoption.")
            validate_global_plan(snapshot,run["verification_plan"]); validate_synthesis_proof(synthesis); validate_netlist_proof(simulation)
            if run["evidence_kind"]=="trusted_saved_tool_revalidation":
                require(index>0 and run.get("prior_run_id")==state["runs"][index-1]["id"],"physical_revalidation_conflict","Revalidation must immediately follow its original actual tool execution.")
                validate_revalidation_link(run,state["runs"][index-1],bool(run["checks"]))
                if "revalidation_rejected_report" in run:
                    require(type(run["revalidation_rejected_report"]) is dict and not run["checks"] and run["execution_status"]!="Completed",
                            "physical_revalidation_conflict","A rejected adapter report is retained only as failed debug evidence.")
            else:
                require(not any(field in run for field in ("prior_run_id","prior_record_sha256","previous_result_sha256","execution_kind","revalidation_rejected_report")),
                        "physical_revalidation_conflict","Original tool executions cannot be relabeled as saved-output revalidation.")
            if run["validation_status"]=="Passed": validate_physical_proof(run,self._adapter()[1])
            elif run["checks"].get("artifacts"): validate_artifact_manifest(run["checks"])
            reviews=[r for r in state["reviews"] if r["run_id"]==run["id"]]
            expected="Awaiting Review" if not reviews else "Accepted" if reviews[-1]["decision"]=="accepted" else "Changes Requested"
            require(run["review_status"]==expected and (expected!="Accepted" or run["execution_status"]=="Completed" and run["validation_status"]=="Passed"
                    and type(run.get("acceptance_epoch")) is int and run["acceptance_epoch"]==reviews[-1]["acceptance_epoch"]),"physical_review_conflict","Physical adoption differs from recorded decisions.")
            ids.add(run["id"])
        for review in state["reviews"]:
            require(type(review) is dict and review.get("run_id") in ids and review.get("actor") in REVIEW_ACTORS and review.get("decision") in ("accepted","changes_requested","return_to_stage")
                    and type(review.get("note")) is str,"physical_review_conflict","Invalid physical decision record.")
            run=self._run(review["run_id"])
            require(review["source_key"]==run["source_key"] and (review.get("target_stage") in EARLIER if review["decision"]=="return_to_stage" else review.get("target_stage") is None),
                    "physical_review_conflict","Physical decision source or return destination differs.")
            self.store.snapshot(review["reviewed_revision_id"]); validate_policy_review(review,policies)
            if review["decision"]=="accepted":
                require(type(review.get("acceptance_epoch")) is int and review["acceptance_epoch"]==run["source_epoch_at_start"] and same_revision_design(self.store, review["reviewed_revision_id"], run["revision_id"]),
                        "physical_review_conflict","Acceptance binds the actual original source epoch and revision.")
        validate_submissions(state)

    def _persist(self):
        require_durable_write()
        name=None
        try:
            for run in self._state["runs"]: run["record_hash"]=object_hash({k:v for k,v in run.items() if k!="record_hash"})
            _io_path(self.path.parent).mkdir(parents=True,exist_ok=True)
            descriptor,name=tempfile.mkstemp(prefix=".physical-workflow-",suffix=".tmp",dir=_io_path(self.path.parent))
            with os.fdopen(descriptor,"w",encoding="utf-8",newline="\n") as handle:
                handle.write(json.dumps(self._state,ensure_ascii=False,allow_nan=False,indent=2)+"\n"); handle.flush(); os.fsync(handle.fileno())
            _replace_with_windows_retry(name,_io_path(self.path)); self._committed=copy.deepcopy(self._state); self._storage_error=None
        except (OSError,ValueError,TypeError):
            self._state=copy.deepcopy(self._committed); self._storage_error={"code":"storage_error","message":"Physical save failed; last durable state retained."}; raise
        finally:
            if name and _io_path(name).exists(): _io_path(name).unlink()

    def close(self):
        with self.lock:
            self._closed=True
            if self._worker and self._worker.is_alive(): self._cancel.set()
        if self._worker and self._worker.is_alive(): self._worker.join(timeout=3)

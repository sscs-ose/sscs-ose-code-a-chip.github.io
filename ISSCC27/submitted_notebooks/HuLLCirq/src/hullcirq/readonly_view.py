"""Fast, execution-disabled views of a pinned saved project.

Opening a historical project verifies its JSON bytes, not every external EDA
artifact and proof again. Results describe the recorded snapshot. Full records
and existing strict artifact downloads remain available on explicit request.
"""
from __future__ import annotations

import copy
import hashlib
import threading
from pathlib import Path
from types import SimpleNamespace

from .domain import DomainError
from .store import ProjectStore, strict_loads

NOTE = "Recorded snapshot only. Tool availability and external evidence have not been requalified by opening this project."
BLOCKED = "Preserved read-only snapshot. Duplicate the design to start new work."
SCOPE = "recorded_snapshot_no_runtime_requalification"
MANAGER_STAGES = {
    "generation": ("local_rtl_generation",),
    "workflow": ("local_synthesis", "local_netlist_simulation"),
    "implementation_specs": ("node_implementation_specs",),
    "global_generation": ("global_rtl_generation",),
    "global_workflow": ("global_synthesis", "global_netlist_simulation"),
    "physical_workflow": ("layout",), "drc_workflow": ("drc",),
    "lvs_workflow": ("lvs",), "postlayout_workflow": ("post_layout_verification",),
}
RECORD_KEYS = {"generation": "jobs", "global_generation": "jobs", "implementation_specs": "specs"}
SUMMARY_FIELDS = frozenset((
    "id", "stage_id", "node_id", "candidate_id", "global_job_id", "source_run_id",
    "revision_id", "input_hash", "design_hash", "source_key", "source_epoch_at_start",
    "execution_status", "validation_status", "review_status", "freshness", "created_at",
    "finished_at", "acceptance_epoch", "record_hash", "rtl_sha256", "netlist_sha256",
    "global_rtl_sha256", "verification_plan_sha256", "vector_hash", "testbench_sha256",
    "configuration_sha256", "runtime_configuration_sha256", "layout_run_id", "drc_run_id",
    "lvs_run_id", "synthesis_run_id", "netlist_run_id", "prior_run_id", "operation",
    "summary", "error", "profile_revision_id", "evidence_kind", "execution_kind",
    "public_boundary_vector_hash", "source_manifest_sha256", "input_gds_sha256",
    "input_netlist_sha256", "source_current", "blocked_reason", "artifacts", "execution_scope",
    "verification_supported"))


def _fail(message, code="invalid_readonly_snapshot", status=500):
    raise DomainError(code, message, status)


def _hash_file(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


class SavedFiles:
    """Pin source JSON once; lazily decode and verify those same bytes on use."""
    def __init__(self, path, expected_files=None):
        self.path, self.lock = Path(path).resolve(), threading.RLock()
        self.records, self.loaded = {}, {}
        expected = {}
        if expected_files is not None:
            entries = expected_files.values() if isinstance(expected_files, dict) else expected_files
            for entry in entries:
                if not isinstance(entry, dict):
                    _fail("Malformed saved snapshot hash manifest.")
                name = entry.get("path", entry.get("name"))
                if (type(name) is not str or Path(name).name != name or not name.endswith(".json")
                        or name in expected or type(entry.get("sha256")) is not str
                        or type(entry.get("size", entry.get("bytes"))) is not int):
                    _fail("Malformed saved snapshot hash manifest.")
                expected[name] = (entry.get("size", entry.get("bytes")), entry["sha256"])
        paths = sorted(self.path.glob("*.json"))
        names = {item.name for item in paths}
        if expected and names != set(expected):
            _fail("The preserved snapshot file list differs from its captured manifest.")
        if "state.json" not in names:
            _fail("The saved snapshot has no state.json.")
        for file in paths:
            if file.is_symlink() or not file.is_file() or not file.resolve().is_relative_to(self.path):
                _fail("Linked saved snapshot files are not supported.")
            record = _hash_file(file)
            if expected and expected[file.name] != record:
                _fail("The preserved snapshot bytes differ from their captured hash manifest.")
            self.records[file.name] = record
        self.manifest_verified = bool(expected)

    def load(self, name):
        with self.lock:
            if name in self.loaded:
                return self.loaded[name]
            if name not in self.records:
                return {}
            path = self.path / name
            if path.is_symlink() or not path.resolve().is_relative_to(self.path):
                _fail("The saved snapshot path changed after opening.")
            raw = path.read_bytes()
            if (len(raw), hashlib.sha256(raw).hexdigest()) != self.records[name]:
                _fail("The saved snapshot changed while it was opening.")
            value = strict_loads(raw.decode("utf-8-sig"))
            if type(value) is not dict:
                _fail("Saved snapshot stores must be JSON objects.")
            self.loaded[name] = value
            return value


class SavedManager:
    """The read methods needed by the GUI; no execution manager is initialized."""
    def __init__(self, files, name, store, configuration=None):
        self.files, self.name, self.store = files, name, store
        self.tool_configuration = configuration
        self.path = files.path / (name + ".json")
        self.lock, self._worker = threading.RLock(), None

    @property
    def _state(self):
        return self.files.load(self.name + ".json")

    def close(self):
        pass

    def is_active(self):
        return False

    def _records(self):
        records = self._state.get(RECORD_KEYS.get(self.name, "runs"), [])
        if type(records) is not list or any(type(item) is not dict or type(item.get("id")) is not str for item in records):
            _fail("Malformed saved history records.")
        return records

    def _run(self, identifier):
        value = next((record for record in self._records() if record["id"] == identifier), None)
        if value is None:
            _fail("Saved record does not exist.", "saved_record_not_found", 404)
        return value

    _job = _stored_job = _spec = _run

    def _freshness(self, record):
        state = self._state
        if self.name in ("generation", "workflow", "implementation_specs"):
            current = state.get("node_inputs", {}).get(record.get("node_id")) == record.get("input_hash")
            if self.name == "implementation_specs":
                current = current and state.get("current_design_hash") == record.get("design_hash")
            epoch = state.get("node_epochs", {}).get(record.get("node_id"))
        else:
            current = record.get("source_key") == state.get("source_key")
            if "source_epoch_at_start" in record:
                current = current and record["source_epoch_at_start"] == state.get("source_epoch")
            epoch = state.get("source_epoch")
        review = record.get("review_status", "Awaiting Review")
        if review == "Accepted" and (not current or record.get("acceptance_epoch") != epoch):
            review = "Awaiting Review"
        return "Current" if current else "Stale", review

    def _decorate(self, record, compact=False):
        value = ({key: copy.deepcopy(item) for key, item in record.items() if key in SUMMARY_FIELDS}
                 if compact else copy.deepcopy(record))
        value["freshness"], value["review_status"] = self._freshness(record)
        value["status_origin"] = "recorded_snapshot"
        value["summary_only"] = compact
        configuration = record.get("runtime_configuration") or {}
        if configuration.get("execution_scope"):
            value["execution_scope"] = configuration["execution_scope"]
            value["verification_supported"] = configuration["execution_scope"] == "post_route_functional_plus_sta"
        if compact:
            value["checks"] = {key: record.get("checks", {})[key] for key in
                               ("executed", "scope", "execution_scope", "validation_status", "cleanup_unresolved")
                               if key in record.get("checks", {})}
            if self.name == "physical_workflow":
                # Downstream stage headers identify the original finite GUI job
                # through this small frozen plan even before opening S11.
                value["verification_plan"] = copy.deepcopy(record.get("verification_plan"))
        if self.name in ("physical_workflow", "drc_workflow", "lvs_workflow", "postlayout_workflow"):
            kind = self.name.replace("_", "-")
            value["artifacts"] = [{**copy.deepcopy(entry), "url": f"/api/artifacts/{kind}/{record['id']}/{entry['id']}"}
                                  for entry in record.get("checks", {}).get("artifacts", [])]
        elif not value.get("artifacts"):
            route = {"generation": "generation/jobs", "workflow": "workflow/runs",
                     "implementation_specs": "implementation-specs", "global_generation": "global-generation/jobs",
                     "global_workflow": "global-workflow/runs"}[self.name]
            value["artifacts"] = [{"kind": self.name, "url": f"/api/{route}/{record['id']}"}]
        return value

    def run(self, identifier):
        return self._decorate(self._run(identifier))

    job = spec = run

    def batch(self, identifier):
        batches = self._state.get("batches", []) if self.name == "workflow" else []
        if type(batches) is not list:
            _fail("Malformed saved node workflow batches.")
        record = next((record for record in batches if record.get("id") == identifier), None)
        if record is None:
            _fail("Saved node workflow batch does not exist.", "workflow_batch_not_found", 404)
        value = copy.deepcopy(record)
        value.setdefault("stage_id", "local_synthesis")
        value.update(status_origin="recorded_snapshot", source_current=False, freshness="Recorded snapshot")
        value["required_node_count"] = len(value.get("items", []))
        value["completed_count"] = sum(item.get("status") not in {"Queued", "Running"} for item in value.get("items", []))
        value["accepted_node_count"] = sum(item.get("run_id") is not None and
            self._decorate(self._run(item["run_id"]))["review_status"] == "Accepted" for item in value.get("items", []))
        return value

    def _nodes(self, records, stages=None):
        nodes = []
        for node_id in self._state.get("node_inputs", {}):
            for stage in stages or (None,):
                relevant = [record for record in records if record.get("node_id") == node_id
                            and (stage is None or record.get("stage_id") == stage)]
                latest = relevant[-1] if relevant else None
                # Generation may retain an earlier accepted candidate. Synthesis
                # and implementation specs require the latest relevant record.
                candidates = reversed(relevant) if self.name == "generation" else ([latest] if latest else [])
                accepted = next((item for item in candidates if item["freshness"] == "Current"
                                 and item["review_status"] == "Accepted"), None)
                key = "job" if self.name == "generation" else "spec" if self.name == "implementation_specs" else "run"
                node = {"node_id": node_id, f"latest_{key}_id": latest["id"] if latest else None,
                        f"accepted_{key}_id": accepted["id"] if accepted else None,
                        "freshness": latest["freshness"] if latest else "Current",
                        "review_status": "Accepted" if accepted else "Awaiting Review",
                        "ready": False, "blocked_reason": BLOCKED}
                if stage:
                    node["stage_id"] = stage
                if self.name == "implementation_specs":
                    node["source_run_id"] = latest.get("source_run_id") if latest else None
                nodes.append(node)
        return nodes

    def stage_view(self, selected_ids=None, stage_id=None):
        records = self._records()
        if selected_ids is None:
            groups = {}
            for record in records:
                if stage_id is None or record.get("stage_id", MANAGER_STAGES[self.name][0]) == stage_id:
                    groups[(record.get("node_id"), record.get("stage_id"))] = record["id"]
            selected_ids = set(groups.values())
        else:
            selected_ids = {selected_ids} if type(selected_ids) is str else set(selected_ids)
            if not selected_ids.issubset({record["id"] for record in records}):
                _fail("Selected saved record does not exist.", "saved_record_not_found", 404)
        return self._envelope(selected_ids)

    def envelope(self):
        return self._envelope(set())

    def _envelope(self, expanded):
        raw = self._records()
        records = [self._decorate(record, compact=record["id"] not in expanded) for record in raw]
        latest = records[-1] if records else None
        reviews = copy.deepcopy(self._state.get("reviews", []))
        if self.name == "generation":
            nodes = self._nodes(records)
            profile = next((item for item in self._state.get("profiles", [])
                            if item.get("revision_id") == self._state.get("active_profile_revision_id")), None)
            probe = copy.deepcopy(self._state.get("probe"))
            return {"llm": {"profile": copy.deepcopy(profile.get("profile")) if profile else None,
                            "profile_revision_id": profile.get("revision_id") if profile else None,
                            "probe": probe, "capabilities": (probe or {}).get("capabilities", {})},
                    "generation": {"implemented": True, "jobs": records, "reviews": reviews, "nodes": nodes,
                                   "latest_job_id": latest["id"] if latest else None, "storage_error": None,
                                   "all_nodes_accepted": bool(nodes) and all(node["accepted_job_id"] for node in nodes),
                                   "compiler": {"available": False, "status": "Read-only snapshot", "configuration": None}}}
        if self.name == "workflow":
            batches = [self.batch(record["id"]) for record in self._state.get("batches", [])]
            return {"workflow_runs": records, "workflow_nodes": self._nodes(records, MANAGER_STAGES[self.name]),
                    "workflow_reviews": reviews, "workflow_storage_error": None, "workflow_batches": batches,
                    "workflow_batch_stages": list(MANAGER_STAGES[self.name]),
                    "workflow_active_batch_id": None, "workflow_latest_batch_id": batches[-1]["id"] if batches else None}
        if self.name == "implementation_specs":
            return {"implementation_specs": records, "implementation_spec_nodes": self._nodes(records),
                    "implementation_spec_reviews": reviews, "implementation_specs_storage_error": None}
        result = {"implemented": True, "jobs" if self.name == "global_generation" else "runs": records,
                  "reviews": reviews, "ready": False, "tool_ready": False, "blocked_reason": BLOCKED,
                  "tool_blocked_reason": BLOCKED, "storage_error": None, "limits": [NOTE],
                  "status_origin": "recorded_snapshot", "runtime_configuration": None}
        if self.name == "global_generation":
            result.update(latest_job_id=latest["id"] if latest else None,
                          required_node_count=6)  # Existing NPU adapter contract.
        elif self.name == "global_workflow":
            stages = []
            for stage in MANAGER_STAGES[self.name]:
                matches = [record for record in records if record.get("stage_id") == stage]
                last = matches[-1] if matches else None
                stages.append({"stage_id": stage, "latest_run_id": last["id"] if last else None,
                               "accepted_run_id": last["id"] if last and last["review_status"] == "Accepted"
                               and last["freshness"] == "Current" else None})
            result["stages"] = stages
        else:
            result.update(stage_id=MANAGER_STAGES[self.name][0], latest_run_id=latest["id"] if latest else None,
                          accepted_run_id=latest["id"] if latest and latest["review_status"] == "Accepted"
                          and latest["freshness"] == "Current" else None)
            if latest:
                for key in ("layout_run_id", "drc_run_id", "lvs_run_id", "input_gds_sha256", "input_netlist_sha256",
                            "verification_plan_sha256", "configuration_sha256", "runtime_configuration_sha256"):
                    if key in latest:
                        result[key] = latest[key]
                configuration = raw[-1].get("runtime_configuration") or {}
                result["runtime_configuration"] = copy.deepcopy(configuration)
                if latest["id"] in expanded:
                    result["source_inputs"] = copy.deepcopy(raw[-1].get("source_inputs"))
                    result["verification_plan"] = copy.deepcopy(raw[-1].get("verification_plan"))
                if self.name == "physical_workflow":
                    result["settings_projection"] = copy.deepcopy(raw[-1].get("settings"))
                result["execution_scope"] = configuration.get("execution_scope", "compatibility_preflight_only")
                result["verification_supported"] = configuration.get("execution_scope") in (
                    "post_route_functional_plus_sta", "post_route_functional_simulation_plus_extracted_sta")
                result["verification_blocked_reason"] = NOTE
        return {self.name: result}

    def artifact_file(self, identifier, artifact_id):
        return self._artifact_class().artifact_file(self, identifier, artifact_id)

    def artifact_bytes(self, identifier, artifact_id):
        return self._artifact_class().artifact_bytes(self, identifier, artifact_id)

    def artifact(self, identifier, artifact_id):
        return self._artifact_class().artifact(self, identifier, artifact_id)

    def _artifact_class(self):
        if self.name == "global_workflow":
            from .global_workflow import GlobalWorkflowManager
            return GlobalWorkflowManager
        if self.name == "physical_workflow":
            from .physical_workflow import PhysicalWorkflowManager
            return PhysicalWorkflowManager
        if self.name == "drc_workflow":
            from .drc_workflow import DrcWorkflowManager
            return DrcWorkflowManager
        if self.name == "lvs_workflow":
            from .lvs_workflow import LvsWorkflowManager
            return LvsWorkflowManager
        if self.name == "postlayout_workflow":
            from .postlayout_workflow import PostLayoutWorkflowManager
            return PostLayoutWorkflowManager
        _fail("No artifact exists for this manager.", "artifact_not_found", 404)


def _saved_envelope(context, stage_id=None, selected_ids=None):
    if stage_id is not None and not any(stage_id in stages for stages in MANAGER_STAGES.values()):
        _fail("Saved evidence stage does not exist.", "stage_not_found", 404)
    result = context.store.envelope()
    result.update(context.generation_batches.envelope())
    result.update(context.repair_analysis.envelope())
    for name, stages in MANAGER_STAGES.items():
        manager = getattr(context, name)
        extension = manager.stage_view(selected_ids, stage_id) if stage_id in stages else manager.envelope()
        result.update(extension)
        records = (extension["generation"]["jobs"] if name == "generation" else extension["workflow_runs"] if name == "workflow"
                   else extension["implementation_specs"] if name == "implementation_specs"
                   else extension[name]["jobs" if name == "global_generation" else "runs"])
        for stage in stages:
            target = next((item for item in result["workflow"] if item["id"] == stage), None)
            if target is None:
                continue
            relevant = [record for record in records if record.get("stage_id", stages[0]) == stage]
            latest = relevant[-1] if relevant else None
            node_states = (extension["generation"]["nodes"] if name == "generation" else extension["workflow_nodes"] if name == "workflow"
                           else extension["implementation_spec_nodes"] if name == "implementation_specs" else None)
            accepted = latest is not None and latest["review_status"] == "Accepted" and latest["freshness"] == "Current"
            target.update(implemented=True, execution_status=latest["execution_status"] if latest else "Not Run",
                          validation_status=latest["validation_status"] if latest else "Not Checked",
                          review_status="Accepted" if accepted else "Awaiting Review",
                          freshness=latest["freshness"] if latest else "Current", ready=False,
                          blocked_reason=BLOCKED, status_origin="recorded_snapshot")
            if name in ("generation", "global_generation"):
                target["latest_job_id"] = latest["id"] if latest else None
            else:
                target["latest_run_id" if name != "implementation_specs" else "latest_spec_id"] = latest["id"] if latest else None
            if node_states is not None:
                nodes = [node for node in node_states if node.get("stage_id", stage) == stage]
                field = "accepted_job_id" if name == "generation" else "accepted_spec_id" if name == "implementation_specs" else "accepted_run_id"
                count = sum(bool(node.get(field)) for node in nodes)
                target.update(node_scope=True, accepted_node_count=count, required_node_count=len(nodes),
                              all_nodes_accepted=bool(nodes) and count == len(nodes),
                              review_status="Accepted" if nodes and count == len(nodes) else "Awaiting Review")
            elif name != "global_generation":
                target["accepted_run_id"] = latest["id"] if accepted else None
    # This remains a lazy snapshot after one stage has loaded. Other stages and
    # historical records are still compact and must never trigger live polling.
    result["readonly_snapshot"] = {"compact": True, "scope": SCOPE, "note": NOTE,
                                   "source_manifest_verified": context.files.manifest_verified,
                                   "loaded_stage": stage_id, "execution_disabled": True}
    result["implementation"].update(read_only_snapshot=True, execution_disabled=True)
    return result


class SavedGenerationBatches:
    """Inspect retained batch records without initializing a model worker."""
    def __init__(self, files):
        self.files = files
        self.lock, self._worker = threading.RLock(), None

    @property
    def _state(self):
        return self.files.load("generation_batches.json")

    def close(self):
        pass

    def is_active(self):
        return False

    def batch(self, identifier):
        batches = self._state.get("batches", [])
        if not isinstance(batches, list):
            _fail("Malformed saved RTL generation batches.")
        record = next((item for item in batches if item.get("id") == identifier), None)
        if record is None:
            _fail("Saved RTL generation batch does not exist.", "generation_batch_not_found", 404)
        result = copy.deepcopy(record)
        result.update(read_only=True, status_origin="recorded_snapshot", source_current=False)
        if result.get("execution_status") in {"Queued", "Running"}:
            result.update(recorded_execution_status=result["execution_status"], execution_status="Interrupted")
        return result

    def plan(self, identifier):
        plans = self._state.get("plans", [])
        if not isinstance(plans, list):
            _fail("Malformed saved RTL generation plans.")
        record = next((item for item in plans if item.get("plan_id", item.get("id")) == identifier), None)
        if record is None:
            _fail("Saved RTL generation plan does not exist.", "generation_batch_plan_not_found", 404)
        return {**copy.deepcopy(record), "ready_to_start": False, "read_only": True}

    def envelope(self):
        batches = [self.batch(item["id"]) for item in self._state.get("batches", [])]
        return {"generation_batches": {"batches": batches, "active_batch_id": None,
                "latest_batch_id": batches[-1]["id"] if batches else None, "storage_error": None, "read_only": True}}


class SavedRepairAnalysis:
    """Inspect saved advice without creating a worker or migrating the snapshot."""
    def __init__(self, files):
        self.files, self.path = files, files.path / "repair_analysis.json"
        self.lock, self._worker = threading.RLock(), None

    @property
    def _state(self):
        return self.files.load("repair_analysis.json")

    def close(self):
        pass

    def is_active(self):
        return False

    def job(self, identifier):
        jobs = self._state.get("jobs", [])
        if type(jobs) is not list or any(type(item) is not dict or type(item.get("id")) is not str for item in jobs):
            _fail("Malformed saved repair analysis records.")
        record = next((item for item in jobs if item["id"] == identifier), None)
        if record is None:
            _fail("Saved repair analysis does not exist.", "repair_analysis_not_found", 404)
        result = copy.deepcopy(record)
        result.update(read_only=True, status_origin="recorded_snapshot", source_current=False)
        if result.get("execution_status") in {"Queued", "Running"}:
            result.update(recorded_execution_status=result["execution_status"], execution_status="Interrupted")
        return result

    def envelope(self):
        jobs = self._state.get("jobs", [])
        if type(jobs) is not list or any(type(item) is not dict or type(item.get("id")) is not str for item in jobs):
            _fail("Malformed saved repair analysis records.")
        return {"repair_analysis": {"jobs": [self.job(item["id"]) for item in jobs],
                "active_job_id": None, "storage_error": None, "read_only": True}}


def build_readonly_context(path, configurations=None, expected_files=None):
    files = SavedFiles(path, expected_files)
    # Validate the small design store normally; it never writes when present.
    files.load("state.json")
    store = ProjectStore(files.path)
    context = SimpleNamespace(store=store, files=files, read_only_snapshot=True)
    for name in MANAGER_STAGES:
        setattr(context, name, SavedManager(files, name, store))
    context.generation_batches = SavedGenerationBatches(files)
    context.repair_analysis = SavedRepairAnalysis(files)
    context.saved_envelope = lambda: _saved_envelope(context)
    context.stage_envelope = lambda stage_id, selected_ids=None: _saved_envelope(context, stage_id, selected_ids)
    return context

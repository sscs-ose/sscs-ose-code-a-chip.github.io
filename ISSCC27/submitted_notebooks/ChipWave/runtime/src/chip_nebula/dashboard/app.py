from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

import chip_nebula
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
import yaml

from chip_nebula.dashboard.process import RunManager
from chip_nebula.dashboard.design_delivery import (
    DesignDeliveryError,
    DesignDeliveryService,
)
from chip_nebula.dashboard.workbench import (
    WorkbenchConflict,
    WorkbenchError,
    WorkbenchProject,
    WorkbenchRunManager,
)
from chip_nebula.taskgraph.assembly import AssemblyError
from chip_nebula.taskgraph.memory_generator import MemoryGenerationError
from chip_nebula.taskgraph.product_flow import ProductFlowError, ProductFlowRunner
from chip_nebula.taskgraph.generic_bootstrap import GenericBootstrapError, GenericBootstrapRunner
from chip_nebula.taskgraph.ip_library import IPLibraryError
from chip_nebula.taskgraph.specs import SpecificationError, default_apb_gpio_spec
from chip_nebula.dashboard.state import (
    _PrettyYamlDumper,
    ansi_to_html,
    inject_intervention,
    list_agents,
    list_pipelines,
    list_workspaces,
    load_stage_agent_config,
    read_pipeline_definition,
    read_pipeline_state,
    read_desktop_operation_transcript,
    read_run_workspace_transcript,
    read_stage_log,
    read_stage_session_transcript,
    read_session_transcript_by_id,
    read_yaml_file,
    resolve_pipeline_file,
    resolve_project_root,
    update_stage_agent_config,
)
from chip_nebula.pipeline.parser import PipelineParser
from chip_nebula.project import (
    get_chip_nebula_dir,
    get_pipelines_dir,
    get_worktrees_dir,
)
from chip_nebula.workspace.manager import WorkspaceManager


class GdsPreviewRequest(BaseModel):
    path: str
    cell: str = ""
    layers: list[str] | None = None
    bounds: list[float] | None = None
    width: int = Field(default=1200, ge=100, le=1600)
    height: int = Field(default=700, ge=100, le=1200)


class StartRunRequest(BaseModel):
    pipeline: str
    feature: str
    framework: Optional[str] = None
    workers: int = 4
    resume: bool = False
    from_stage: Optional[str] = None


class InterveneRequest(BaseModel):
    stage: str
    text: str
    kind: str = "user_feedback"
    from_stage: Optional[str] = None


class UpdateAgentConfigRequest(BaseModel):
    system_prompt_template: Optional[str] = None
    write_paths: Optional[str | list[str]] = None


class CreatePipelineRequest(BaseModel):
    module: str
    name: str
    content: str


class UpdateYamlRequest(BaseModel):
    content: Optional[str] = None
    structured: Optional[dict[str, Any]] = None


class ApplyToColleaguesRequest(BaseModel):
    path: str
    framework: Optional[str] = None
    model: Optional[str] = None
    model_provider: Optional[str] = None


class HumanTaskAnswerRequest(BaseModel):
    issue_id: str
    selected: str
    actor: str = "human"
    evidence_artifact_ids: list[str] = Field(default_factory=list)


class ContinueTaskGraphRunRequest(BaseModel):
    instruction: str


class ExtendTaskGraphRunTimeoutRequest(BaseModel):
    seconds: int = Field(default=7200, gt=0, le=28800)


class SaveTaskGraphRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    system_prompt: str = ""
    framework: str = ""
    model: str = ""
    accepted_types: list[str] = Field(default_factory=list)
    produced_types: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class SaveTaskGraphSchemaRequest(BaseModel):
    version: int = 1
    # field -> 类型(str 或 list[str])，或 {type: ..., description: ...}
    required_fields: dict[str, Any] = Field(default_factory=dict)


class StartTaskGraphRequest(BaseModel):
    recipe: str
    workflow: str
    framework: Optional[str] = None
    model: Optional[str] = None
    workers: int = 4
    baseline: str = "HEAD"
    resume: bool = False
    rebase_from: str = ""
    parameters: dict[str, str] = Field(default_factory=dict)


class AutogenPlanRequest(BaseModel):
    prompt: str
    framework: str = "opencode"
    model: str = ""
    feedback: list[dict[str, str]] = Field(default_factory=list)
    previous_plan: Optional[dict[str, Any]] = None
    session_id: str = ""
    job_id: str = ""


class AutogenWorkflowRequest(BaseModel):
    prompt: str
    framework: str = "opencode"
    model: str = ""
    plan: Optional[dict[str, Any]] = None
    session_id: str = ""
    job_id: str = ""


class SaveTaskGraphRecipeRequest(BaseModel):
    filename: str
    recipe: dict[str, Any]
    overwrite: bool = False


class CreateTaskGraphArtifactRequest(BaseModel):
    artifact_id: str = ""
    artifact_type: str
    schema_version: int = 1
    payload: dict[str, Any]
    content_kind: str = "inline"
    git_ref: str = "HEAD"
    uri: str = ""
    paths: list[str] = Field(default_factory=list)
    workflow_id: str = "external"
    # interface.contract 专用：契约文件在仓库内的相对路径，
    # 平台用该文件最后一次被修改的 commit 作为 contract_version，无需人肉维护版本号
    contract_path: str = ""


class CreateRoundtableRequest(BaseModel):
    topic: str
    chairman: str
    participants: list[dict[str, Any]]  # [{name, kind, role_prompt?, framework?, model?, ...}]
    max_rounds: int = 10
    created_by: str = ""
    doc_writer: str = ""
    start: bool = True


class UpdateRoundtableRequest(BaseModel):
    topic: str
    chairman: str
    participants: list[dict[str, Any]]
    max_rounds: int = 10
    doc_writer: str = ""


class RoundtableMessageRequest(BaseModel):
    text: str
    author_name: str = ""


class RoundtableDecisionRequest(BaseModel):
    action: str                          # "approve" | "continue" | "rewrite"
    text: str = ""
    output_path: str = ""
    doc_mode: str = "direct"             # "direct" = save summary; "polish" = agent rewrite
    author_name: str = ""


class GenerateRoundtablePromptsRequest(BaseModel):
    generator_framework: str = "opencode"
    generator_model: str = ""
    generator_model_provider: str = ""


class SaveRoundtablePromptsRequest(BaseModel):
    topic: str
    chairman: str
    max_rounds: int = 10
    participants: list[dict[str, Any]]  # includes role_prompt for agents
    doc_writer: str = ""


class WorkbenchConfigRequest(BaseModel):
    top_module: str = ""
    top_parameters: dict[str, int] = Field(default_factory=dict)
    source_globs: list[str] = Field(
        default_factory=lambda: ["**/*.sv", "**/*.v", "**/*.svh", "**/*.vh"]
    )
    validation_mode: str = "commands"
    design_files: list[str] = Field(default_factory=list)
    testbench_files: list[str] = Field(default_factory=list)
    simulation_assets: list[str] = Field(default_factory=list)
    include_dirs: list[str] = Field(default_factory=list)
    defines: list[str] = Field(default_factory=list)
    filelists: list[str] = Field(default_factory=list)
    simulation_top: str = ""
    write_paths: list[str] = Field(default_factory=lambda: ["rtl/**", "src/**"])
    lint_command: str = ""
    simulation_command: str = ""
    workdir: str = "."
    timeout: int = 900
    agent_timeout: int = 3600
    success_pattern: str = ""
    success_evidence: dict[str, Any] = Field(default_factory=dict)
    report_globs: list[str] = Field(default_factory=list)
    waveform_globs: list[str] = Field(default_factory=lambda: ["**/*.vcd", "**/*.fst"])
    physical: dict[str, Any] = Field(default_factory=dict)


class WorkbenchFileRequest(BaseModel):
    content: str
    version: str


class WorkbenchFileCreateRequest(BaseModel):
    path: str
    content: str = ""


class WorkbenchFileImportItem(BaseModel):
    path: str
    content: str


class WorkbenchFileImportRequest(BaseModel):
    files: list[WorkbenchFileImportItem] = Field(default_factory=list)


class WorkbenchValidationRequest(BaseModel):
    kind: str = "all"


class WorkbenchPhysicalRequest(BaseModel):
    mode: str = "all"


class WorkbenchPhysicalConfigureRequest(BaseModel):
    top_module: str
    top_parameters: dict[str, int] = Field(default_factory=dict)
    clock_port: str
    clock_period_ns: float = 10.0
    platform: str = "sky130hd"
    simulation_command: str
    confirmed: bool = False


class WorkbenchEquivalenceRequest(BaseModel):
    operation_id: str
    timeout_seconds: int = 600
    clock_port: str = ""
    reset_port: str = ""
    reset_active: str = ""


class WorkbenchAgentRequest(BaseModel):
    instruction: str
    framework: str = "codex"
    write_paths: list[str] = Field(default_factory=list)
    stage: str = "rtl"


class WorkbenchAssistantRequest(BaseModel):
    instruction: str
    workspace: str
    mode: str = "ask"
    framework: str = "codex"


class WorkbenchExecutionPlanRequest(BaseModel):
    instruction: str
    workspace: str
    framework: str = "codex"
    write_paths: list[str] = Field(default_factory=list)
    clarifications: dict[str, str] = Field(default_factory=dict)


class PrepareSpecirGenerateRequest(BaseModel):
    document_text: str = ""
    framework: str = "codex"
    model: str = ""
    action_kind: Literal["spec_generate", "spec_repair"] = "spec_generate"


class PrepareSpecirRevisionRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=20000)


class PrepareAcceptanceSaveRequest(BaseModel):
    document: dict[str, Any]


class ProjectConstraintsSaveRequest(BaseModel):
    document: dict[str, Any]


def _specir_trace_catalog(provenance_file: Path) -> dict[str, set[str]]:
    if not provenance_file.is_file():
        return {"requirements": set(), "required_requirements": set(), "design_groups": set()}
    try:
        document = json.loads(provenance_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"requirements": set(), "required_requirements": set(), "design_groups": set()}
    if not isinstance(document, dict):
        return {"requirements": set(), "required_requirements": set(), "design_groups": set()}
    requirements = {
        str(item.get("id", "")).strip()
        for item in document.get("requirements", [])
        if isinstance(item, dict) and str(item.get("id", "")).startswith("REQ-")
    }
    required = {
        str(item.get("id", "")).strip()
        for item in document.get("requirements", [])
        if isinstance(item, dict)
        and str(item.get("id", "")).startswith("REQ-")
        and str(item.get("classification", "normative")) == "normative"
    }
    design_groups = {
        str(item.get("design_group", "")).strip()
        for item in document.get("nodes", [])
        if isinstance(item, dict) and item.get("design_group")
    }
    return {
        "requirements": requirements,
        "required_requirements": required,
        "design_groups": design_groups,
    }


class WorkbenchInputRemediationRequest(BaseModel):
    path: str
    framework: str = "codex"


class GenericAcceptanceFreezeRequest(BaseModel):
    operation_id: str
    confirmed: bool = False


class ExistingCheckerReviewRequest(BaseModel):
    plan_digest: str


class ExistingCheckerReviewFreezeRequest(BaseModel):
    confirmed: bool = False


class WorkbenchGitInitRequest(BaseModel):
    confirmed: bool = False


class WorkbenchProjectDefinitionRequest(BaseModel):
    confirmed: bool = False
    name: str = ""


class WorkbenchResetStateRequest(BaseModel):
    confirmed: bool = False


class DesignSpecRequest(BaseModel):
    document: dict[str, Any]


class IPImportRequest(BaseModel):
    path: str = ""
    repository: str = ""
    ref: str = ""
    subdirectory: str = ""


class IPValidateRequest(BaseModel):
    package_id: str
    version: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ProductPreparationRequest(BaseModel):
    plan_digest: str


class ProductFlowStartRequest(BaseModel):
    plan_digest: str
    run_physical: bool = False
    physical_timeout_seconds: int = 14400
    auto_repair_framework: str = ""


class GenericBootstrapStartRequest(BaseModel):
    plan_digest: str
    framework: str = "codex"


class DeliveryExportRequest(BaseModel):
    confirmed: bool = False
    include_physical: bool = False


class IPPublishRequest(BaseModel):
    version: str = "1.0.0"
    confirmed: bool = False


def _normalize_integration_dependencies(
    document: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return one UI shape for legacy and integration-authored locks."""
    components: list[dict[str, Any]] = []
    identities: set[tuple[str, str, str]] = set()

    def append_component(raw: object, *, package_entry: bool = False) -> None:
        if not isinstance(raw, dict):
            return
        package = str(raw.get("package") or raw.get("package_id") or "")
        version = str(raw.get("version") or "")
        module = str(
            raw.get("module") or raw.get("top_module")
            or raw.get("name") or package
        )
        identity = (package, version, module)
        if not module or identity in identities:
            return
        identities.add(identity)
        item = dict(raw)
        item.update({
            "module": module,
            "kind": str(raw.get("kind") or (
                "external_ip" if package or package_entry else "project_rtl"
            )),
        })
        if package:
            item["package"] = package
        digest = (
            raw.get("package_digest") or raw.get("content_digest")
            or raw.get("declared_content_digest") or raw.get("sha256")
        )
        if digest:
            item["package_digest"] = str(digest)
        parameters = raw.get("parameters")
        if isinstance(parameters, dict):
            item["parameters"] = parameters
        elif parameters:
            item["parameters"] = {"configuration": str(parameters)}
        else:
            item["parameters"] = {}
        components.append(item)

    raw_components = document.get("components", [])
    if isinstance(raw_components, list):
        for component in raw_components:
            append_component(component)

    packages = document.get("packages", [])
    if isinstance(packages, list):
        for package in packages:
            append_component(package, package_entry=True)

    external_ip = document.get("external_ip", [])
    if isinstance(external_ip, list):
        for package in external_ip:
            if isinstance(package, dict) and not any(
                package.get(key) for key in ("module", "top_module", "name")
            ):
                rtl = package.get("rtl")
                if isinstance(rtl, dict) and rtl.get("path"):
                    package = {
                        **package,
                        "module": Path(str(rtl["path"])).stem,
                    }
            append_component(package, package_entry=True)

    component_set = document.get("component_set", [])
    if isinstance(component_set, list):
        known_modules = {str(item.get("module") or "") for item in components}
        for module in component_set:
            if isinstance(module, str) and module and module not in known_modules:
                append_component({"module": module, "kind": "project_rtl"})
                known_modules.add(module)

    rtl_sources = document.get("rtl_sources", [])
    if isinstance(rtl_sources, list):
        for source in rtl_sources:
            if isinstance(source, str):
                append_component({
                    "module": Path(source).stem, "path": source,
                    "kind": "project_rtl",
                })
            elif isinstance(source, dict):
                append_component({
                    **source,
                    "module": source.get("module") or Path(str(source.get("path", ""))).stem,
                    "kind": source.get("kind") or "project_rtl",
                })

    memory_macro = document.get("memory_macro")
    if isinstance(memory_macro, dict):
        append_component({
            **memory_macro,
            "module": memory_macro.get("module") or memory_macro.get("name"),
            "kind": memory_macro.get("kind") or "hard_macro",
        })
    memory_macros = document.get("memory_macros", [])
    if isinstance(memory_macros, list):
        for macro in memory_macros:
            if isinstance(macro, dict):
                append_component({
                    **macro,
                    "module": macro.get("module") or macro.get("name"),
                    "kind": macro.get("kind") or "hard_macro",
                })

    external = [
        item for item in components
        if item.get("package") or item.get("kind") in {
            "existing_project_ip", "external_ip", "hard_macro",
        }
    ]
    return components, external


def _apply_from_stage_reset(saved: dict, stages: dict, from_stage: str) -> None:
    """State surgery for Inject / from-stage resume.

    - from_stage + its transitive downstream → pending (they will re-run).
    - Every non-passed transitive UPSTREAM stage → "skipped": never
      scheduled, but counts as dependency-satisfied and as complete for the
      final verdict. This lets the pipeline start exactly at from_stage
      instead of re-running unfinished upstream work (e.g. a stopped
      rtl_coding) that the user has taken manual responsibility for.
    """
    dependents: dict[str, set[str]] = {name: set() for name in stages}
    for name, cfg in stages.items():
        for dep in cfg.get("depends_on", []):
            if dep in dependents:
                dependents[dep].add(name)

    to_reset = {from_stage}
    queue = [from_stage]
    while queue:
        current = queue.pop(0)
        for nxt in dependents.get(current, set()):
            if nxt not in to_reset:
                to_reset.add(nxt)
                queue.append(nxt)

    upstream: set[str] = set()
    queue = list(stages.get(from_stage, {}).get("depends_on", []))
    while queue:
        current = queue.pop(0)
        if current in upstream or current not in stages:
            continue
        upstream.add(current)
        queue.extend(stages.get(current, {}).get("depends_on", []))

    stage_status = saved.setdefault("stage_status", {})
    iteration_counters = saved.setdefault("iteration_counters", {})
    session_ids = saved.setdefault("session_ids", {})
    for name in to_reset:
        stage_status[name] = "pending"
        iteration_counters.pop(name, None)
        session_ids.pop(name, None)
    for name in upstream:
        if stage_status.get(name) != "passed":
            stage_status[name] = "skipped"
            iteration_counters.pop(name, None)
    saved["rollbacks_executed"] = 0
    saved["last_updated"] = datetime.now().isoformat()


def create_app(project_root: Optional[Path] = None) -> FastAPI:
    requested = Path(project_root).expanduser() if project_root is not None else None
    explicit_project_file = (
        requested.resolve()
        if requested is not None and requested.suffix.lower() == ".cnprj"
        else None
    )
    root = resolve_project_root(project_root)
    workbench = WorkbenchProject(root, project_file=explicit_project_file)
    # Validate versioned project metadata before any manager creates mutable
    # ``.chip_nebula`` state.  A malformed entry therefore cannot modify the
    # project merely because the desktop tried to open it.
    workbench.project_definition()
    workbench.config()
    run_manager = RunManager(root)
    workbench_runs = WorkbenchRunManager(workbench)
    design = DesignDeliveryService(
        root, runs_provider=workbench_runs.list_runs,
        physical_fingerprint_provider=workbench.physical_fingerprint,
    )
    product_flows = ProductFlowRunner(workbench, design, workbench_runs)
    generic_bootstrap = GenericBootstrapRunner(
        workbench, workbench_runs,
        other_active=lambda: any(
            item.get("status") in ProductFlowRunner.ACTIVE
            for item in product_flows.list()
        ),
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            _recover_static_taskgraph_orphans(root)
            yield
        finally:
            gds_preview.close()
            # A normal window close stops active work through the API first.
            # This is the final owner boundary for Electron crashes, SIGTERM
            # and project-switch backend replacement.
            generic_bootstrap.stop_active()
            product_flows.stop_active()
            workbench_runs.stop_all()
            run_manager.stop_owned()

    app = FastAPI(title="Chip Nebula Dashboard", lifespan=lifespan)
    app.state.run_manager = run_manager
    app.state.workbench_runs = workbench_runs
    app.state.product_flows = product_flows
    app.state.generic_bootstrap = generic_bootstrap

    desktop_token = os.environ.get("CHIP_NEBULA_DESKTOP_TOKEN", "")

    @app.middleware("http")
    async def desktop_session_guard(request: Request, call_next):
        if (
            desktop_token
            and request.url.path.startswith("/api/")
            and request.headers.get("x-chip-nebula-token", "") != desktop_token
            and request.query_params.get("desktop_token", "") != desktop_token
        ):
            return JSONResponse(status_code=401, content={"detail": "Invalid desktop session"})
        return await call_next(request)

    static_dir = Path(chip_nebula.__file__).parent / "dashboard" / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def serve_index():
        index = static_dir / "index.html"
        if index.exists():
            # no-cache: the HTML points at content-hashed assets, but only if
            # the browser actually re-fetches it after each frontend rebuild.
            return HTMLResponse(index.read_text(), headers={"Cache-Control": "no-cache"})
        return "<h1>Chip Nebula Dashboard</h1><p>Frontend build not found.</p>"

    @app.get("/api/status")
    async def api_status():
        return {
            "version": chip_nebula.__version__,
            "project_root": str(root),
            "desktop": bool(desktop_token),
        }

    # --- RTL desktop workbench -------------------------------------------

    def _workbench_error(exc: Exception) -> HTTPException:
        if isinstance(exc, WorkbenchConflict):
            return HTTPException(
                status_code=409,
                detail={"message": str(exc), "paths": exc.paths},
            )
        return HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/workbench/project")
    async def api_workbench_project():
        try:
            return workbench.inspect()
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/git/init")
    async def api_initialize_workbench_git(req: WorkbenchGitInitRequest):
        try:
            if not req.confirmed:
                raise WorkbenchError("必须确认后才能初始化 Git 和创建基线提交")
            return workbench.initialize_git()
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/project-definition")
    async def api_create_workbench_project_definition(
        req: WorkbenchProjectDefinitionRequest,
    ):
        try:
            if not req.confirmed:
                raise WorkbenchError("必须确认后才能创建 .cnprj 工程文件")
            return workbench.create_project_definition(req.name)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/reset-state")
    async def api_reset_workbench_state(req: WorkbenchResetStateRequest):
        """Stop owned work and clear reproducible project runtime state."""
        try:
            if not req.confirmed:
                raise WorkbenchError("必须确认后才能清理工程状态")
            # Stop every owner before deleting locks, operation records and
            # taskgraph databases.  This endpoint is intentionally explicit so
            # a normal dashboard refresh can never erase state accidentally.
            generic_bootstrap.stop_active()
            product_flows.stop_active()
            workbench_runs.stop_all()
            run_manager.stop_all()
            return workbench.reset_state()
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.put("/api/workbench/config")
    async def api_workbench_config(req: WorkbenchConfigRequest):
        try:
            document = req.model_dump() if hasattr(req, "model_dump") else req.dict()
            return asdict(workbench.save_config(document))
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/fileset/detect")
    async def api_detect_workbench_fileset():
        try:
            return workbench.suggest_fileset()
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/files")
    async def api_workbench_files():
        return workbench.file_tree()

    @app.get("/api/workbench/sources")
    async def api_workbench_sources():
        try:
            return workbench.source_model()
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    def _artifact_workflow_id(artifact) -> str:
        producer = getattr(artifact, "producer", None)
        return str(
            getattr(producer, "workflow_id", "")
            or artifact.metadata.get("workflow_id", "")
        )

    def _artifact_input_ids(artifact) -> tuple[str, ...]:
        return tuple(
            getattr(artifact, "input_artifact_ids", ())
            or getattr(artifact, "inputs", ())
        )

    def _latest_initial_artifacts(items: list[dict]) -> list[dict]:
        latest: dict[str, dict] = {}
        for item in items:
            artifact_type = str(item.get("type") or "")
            if not artifact_type:
                continue
            previous = latest.get(artifact_type)
            if previous is None or (
                str(item.get("created_at") or ""), str(item.get("id") or "")
            ) > (
                str(previous.get("created_at") or ""), str(previous.get("id") or "")
            ):
                latest[artifact_type] = item
        return [latest[key] for key in sorted(latest)]

    def _taskgraph_artifact(artifact_id: str):
        static_database = (
            get_chip_nebula_dir(root) / "shared" / "memory" / "taskgraph-v2.db"
        )
        if static_database.is_file():
            from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
            with StaticTaskGraphStore(static_database) as store:
                return store.get_artifact(artifact_id)
        return None

    def _current_workflow_rtl_artifact(workflow_id: str = ""):
        candidates = []
        static_database = (
            get_chip_nebula_dir(root) / "shared" / "memory" / "taskgraph-v2.db"
        )
        if static_database.is_file():
            from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
            with StaticTaskGraphStore(static_database) as store:
                for workflow in store.list_workflows():
                    if workflow_id and workflow.id != workflow_id:
                        continue
                    for task in store.list_tasks(workflow.id):
                        for delivery in store.deliveries(task.id).values():
                            artifact = store.get_artifact(delivery.artifact_id)
                            if artifact is not None and artifact.type in {
                                "rtl.integration", "rtl.snapshot",
                            }:
                                candidates.append(artifact)
        if workflow_id:
            candidates = [
                artifact for artifact in candidates
                if _artifact_workflow_id(artifact) == workflow_id
            ]
        candidates = [
            artifact for artifact in candidates
            if artifact.content.kind == "git" and artifact.content.commit
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda artifact: (
            artifact.type == "rtl.integration", artifact.created_at, artifact.id,
        ))

    def _workflow_hierarchy_snapshots(artifact, workflow_id: str = ""):
        """Resolve the immutable design chain and its matching verification sources."""
        design_artifacts = [artifact]
        verification_artifacts = []
        for artifact_id in _artifact_input_ids(artifact):
            upstream = _taskgraph_artifact(artifact_id)
            if (
                upstream is not None and upstream.type == "rtl.snapshot"
                and upstream.content.kind == "git" and upstream.content.commit
            ):
                design_artifacts.append(upstream)
        candidates = []
        static_database = (
            get_chip_nebula_dir(root) / "shared" / "memory" / "taskgraph-v2.db"
        )
        if static_database.is_file():
            from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
            with StaticTaskGraphStore(static_database) as store:
                for workflow in store.list_workflows():
                    if workflow_id and workflow.id != workflow_id:
                        continue
                    for task in store.list_tasks(workflow.id):
                        for delivery in store.deliveries(task.id).values():
                            candidate = store.get_artifact(delivery.artifact_id)
                            if (
                                candidate is not None
                                and candidate.type == "verification.environment"
                                and candidate.content.kind == "git"
                                and candidate.content.commit
                            ):
                                candidates.append(candidate)
        if workflow_id:
            candidates = [
                item for item in candidates
                if _artifact_workflow_id(item) == workflow_id
            ]
        if candidates:
            verification_artifacts.append(max(candidates, key=lambda item: (
                artifact.id in _artifact_input_ids(item), item.created_at, item.id,
            )))

        def snapshot(item):
            return {
                "artifact_id": item.id, "commit": item.content.commit,
                "paths": list(item.content.paths),
            }

        return (
            [snapshot(item) for item in design_artifacts],
            [snapshot(item) for item in verification_artifacts],
        )

    def _artifact_text(artifact, relative: str) -> str:
        if relative not in artifact.content.paths:
            raise WorkbenchError("文件不属于该不可变 Artifact")
        result = subprocess.run(
            ["git", "show", f"{artifact.content.commit}:{relative}"],
            cwd=root, capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise WorkbenchError(result.stderr.strip() or "无法读取 Artifact 文件")
        return result.stdout

    from chip_nebula.taskgraph.gds_viewer import (
        GdsPreviewService, GdsPreviewError, GdsPreviewUnavailable, gds_paths,
    )
    gds_preview = GdsPreviewService(root)

    def _gds_artifact(artifact_id: str):
        artifact = _taskgraph_artifact(artifact_id)
        if artifact is None:
            raise HTTPException(status_code=404, detail="Artifact not found")
        if artifact.type != "gds":
            raise HTTPException(status_code=400, detail="请选择 GDS Artifact")
        return artifact

    @app.get("/api/taskgraph/artifacts/{artifact_id}/gds")
    async def api_gds_info(artifact_id: str, path: str = ""):
        artifact = _gds_artifact(artifact_id)
        candidates = gds_paths(artifact)
        if not candidates:
            raise HTTPException(status_code=400, detail="Artifact 未归档 GDS/OASIS 文件")
        try:
            return await asyncio.to_thread(gds_preview.info, artifact, path or candidates[0])
        except GdsPreviewError as exc:
            raise HTTPException(status_code=503 if isinstance(exc, GdsPreviewUnavailable) else 400,
                                detail=str(exc)) from exc

    @app.post("/api/taskgraph/artifacts/{artifact_id}/gds/preview")
    async def api_gds_preview(artifact_id: str, req: GdsPreviewRequest):
        from fastapi.responses import Response
        artifact = _gds_artifact(artifact_id)
        try:
            image = await asyncio.to_thread(gds_preview.render, artifact, req.path,
                                           cell=req.cell, layers=req.layers, bounds=req.bounds,
                                           width=req.width, height=req.height)
        except GdsPreviewError as exc:
            raise HTTPException(status_code=503 if isinstance(exc, GdsPreviewUnavailable) else 400,
                                detail=str(exc)) from exc
        return Response(image, media_type="image/png", headers={"Cache-Control": "private, no-store"})

    @app.get("/api/workbench/hierarchy")
    async def api_workbench_hierarchy(workflow_id: str = ""):
        """Hierarchy of the latest immutable workflow RTL, or live fileset."""
        artifact = _current_workflow_rtl_artifact(workflow_id)
        try:
            if artifact is None:
                return workbench.source_model()
            design_snapshots, testbench_snapshots = _workflow_hierarchy_snapshots(
                artifact, workflow_id,
            )
            return await asyncio.to_thread(
                workbench.source_model_from_git_snapshots,
                design_snapshots=design_snapshots,
                testbench_snapshots=testbench_snapshots,
            )
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/project-dependencies")
    async def api_workbench_project_dependencies(workflow_id: str = ""):
        artifact = _current_workflow_rtl_artifact(workflow_id)
        if artifact is None:
            return {"source": None, "components": [], "external_components": []}
        candidates = [
            path for path in artifact.content.paths
            if Path(path).name in {"dependencies.lock.json", "dependency.lock.json"}
        ]
        candidates.sort(key=lambda path: (
            not path.endswith("/dependencies.lock.json"), path,
        ))
        if not candidates:
            return {
                "source": {
                    "artifact_id": artifact.id, "commit": artifact.content.commit,
                },
                "components": [], "external_components": [],
            }
        try:
            document = json.loads(await asyncio.to_thread(
                _artifact_text, artifact, candidates[0],
            ))
        except (WorkbenchError, json.JSONDecodeError) as exc:
            raise _workbench_error(WorkbenchError(str(exc))) from exc
        components, external = _normalize_integration_dependencies(document)
        return {
            "source": {
                "artifact_id": artifact.id, "commit": artifact.content.commit,
                "path": candidates[0],
            },
            "top_module": document.get("top_module") or document.get("top", ""),
            "policy": document.get("discovery_policy", ""),
            "components": components,
            "external_components": external,
        }

    @app.get("/api/taskgraph/artifacts/{artifact_id}/dependency-file")
    async def api_taskgraph_dependency_file(artifact_id: str, path: str):
        from chip_nebula.taskgraph.hierarchy_dependencies import (
            HierarchyDependencyError, read_dependency_file,
        )
        artifact = _taskgraph_artifact(artifact_id)
        if artifact is None:
            raise HTTPException(status_code=404, detail="Artifact not found")
        if artifact.type not in {"rtl.integration", "rtl.snapshot"}:
            raise HTTPException(status_code=400, detail="Artifact is not a design source")
        try:
            return await asyncio.to_thread(read_dependency_file, root, {
                "artifact_id": artifact.id, "commit": artifact.content.commit,
                "paths": list(artifact.content.paths),
            }, path)
        except HierarchyDependencyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/taskgraph/artifacts/{artifact_id}/file")
    async def api_taskgraph_artifact_file(artifact_id: str, path: str):
        artifact = _taskgraph_artifact(artifact_id)
        if artifact is None:
            raise HTTPException(status_code=404, detail="Artifact not found")
        if not artifact.content.commit:
            raise HTTPException(status_code=400, detail="Artifact has no readable Git commit")
        try:
            content = await asyncio.to_thread(_artifact_text, artifact, path)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc
        return {
            "path": path, "content": content, "read_only": True,
            "version": f"{artifact.digest}:{path}", "artifact_id": artifact.id,
            "commit": artifact.content.commit,
        }

    @app.post("/api/workbench/files")
    async def api_create_workbench_file(req: WorkbenchFileCreateRequest):
        try:
            if workbench_runs.file_locked(req.path):
                raise WorkbenchConflict(
                    "AI 正在修改该授权范围，文件暂时锁定", [req.path]
                )
            return workbench.create_file(req.path, req.content)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/files/import")
    async def api_import_workbench_files(req: WorkbenchFileImportRequest):
        try:
            documents = [
                item.model_dump() if hasattr(item, "model_dump") else item.dict()
                for item in req.files
            ]
            for item in documents:
                if workbench_runs.file_locked(item["path"]):
                    raise WorkbenchConflict(
                        "AI 正在修改该授权范围，文件暂时锁定", [item["path"]]
                    )
            return workbench.import_files(documents)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/file")
    async def api_workbench_file(path: str):
        try:
            return workbench.read_file(path)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.put("/api/workbench/file")
    async def api_save_workbench_file(path: str, req: WorkbenchFileRequest):
        try:
            if workbench_runs.file_locked(path):
                raise WorkbenchConflict(
                    "AI 正在修改该授权范围，文件暂时锁定", [path]
                )
            return workbench.save_file(path, req.content, req.version)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/operations")
    async def api_workbench_operations():
        return workbench.list_operations()

    @app.get("/api/workbench/operations/{operation_id}")
    async def api_workbench_operation(operation_id: str):
        try:
            return workbench.operation_diff(operation_id)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/operations/{operation_id}/undo")
    async def api_undo_workbench_operation(operation_id: str):
        try:
            return workbench.undo_operation(operation_id)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/operations/{operation_id}/stop")
    async def api_stop_workbench_agent(operation_id: str):
        return {"stopped": workbench_runs.stop_agent(operation_id)}

    @app.post("/api/workbench/agent-runs")
    async def api_start_workbench_agent(req: WorkbenchAgentRequest):
        try:
            if req.stage not in {"rtl", "rtl_generation", "acceptance_generation", "specification", "advisory"}:
                raise WorkbenchError(
                    "AI stage must be rtl, rtl_generation, acceptance_generation, specification or advisory"
                )
            write_paths = (
                ["spec/design.csir.yaml"]
                if req.stage == "specification"
                else [workbench_runs.generic_acceptance_state()["checker"]]
                if req.stage == "acceptance_generation"
                else [] if req.stage == "advisory"
                else (req.write_paths or workbench.config().write_paths)
            )
            if not req.instruction.strip():
                raise WorkbenchError("AI instruction is required")
            return workbench_runs.start_agent(
                req.instruction.strip(), req.framework, write_paths,
                stage=req.stage,
            )
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/assistant/stage-skill/{workspace}")
    async def api_workbench_stage_skill(workspace: str):
        try:
            return workbench_runs.stage_skill(workspace)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/assistant/sessions")
    async def api_workbench_assistant_sessions(workspace: str = ""):
        try:
            return workbench_runs.list_assistant_sessions(workspace)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/assistant/sessions/{assistant_id}")
    async def api_workbench_assistant_session(assistant_id: str):
        try:
            return workbench_runs.assistant_session(assistant_id)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/assistant/sessions")
    async def api_start_workbench_assistant(req: WorkbenchAssistantRequest):
        try:
            return workbench_runs.start_assistant(
                req.instruction, req.framework,
                workspace=req.workspace, mode=req.mode,
            )
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/assistant/sessions/{assistant_id}/stop")
    async def api_stop_workbench_assistant(assistant_id: str):
        try:
            return {"stopped": workbench_runs.stop_assistant(assistant_id)}
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    _implementation_inventory_cache: dict[str, Any] = {}

    def _implementation_platform_inventory() -> dict[str, Any]:
        """Describe only platform assets that are actually installed locally."""
        from chip_nebula.taskgraph.platform_inventory import (
            installed_platform_inventory,
        )

        cached_at = float(_implementation_inventory_cache.get("cached_at", 0.0))
        if time.monotonic() - cached_at < 60.0:
            return dict(_implementation_inventory_cache["value"])
        result = installed_platform_inventory()
        _implementation_inventory_cache.update({
            "cached_at": time.monotonic(), "value": result,
        })
        return dict(result)

    def _delivery_file(delivery: dict[str, Any] | None, relative: str):
        """Read one file only from the immutable Artifact that declares it."""
        if not delivery:
            return None
        content = delivery.get("content") or {}
        paths = [str(item) for item in content.get("paths", [])]
        if relative not in paths:
            return None
        text = ""
        if content.get("kind") == "git" and content.get("commit"):
            result = subprocess.run(
                ["git", "show", f"{content['commit']}:{relative}"],
                cwd=root, capture_output=True, text=True, check=False,
            )
            if result.returncode == 0:
                text = result.stdout
        if not text:
            path = root / relative
            if not path.is_file():
                return None
            text = path.read_text(encoding="utf-8", errors="replace")
        try:
            return yaml.safe_load(text) if relative.endswith((".yaml", ".yml")) else json.loads(text)
        except (yaml.YAMLError, json.JSONDecodeError):
            return None

    def _prepare_phase(flow: dict[str, Any] | None, task_key: str) -> str:
        task = next((
            item for item in (flow or {}).get("tasks", [])
            if item.get("step") == task_key
        ), None)
        status = str((task or {}).get("status", ""))
        return {
            "succeeded": "complete",
            "running": "running",
            "ready": "ready",
            "awaiting_human": "awaiting_human",
            "failed": "failed",
            "paused": "failed",
            "waiting": "not_started",
            "": "not_started",
        }.get(status, "not_started")

    def _implementation_constraints_state(
        spec_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Project the fixed PREPARE Tasks; never infer state from old operations."""
        from chip_nebula.taskgraph.implementation_constraints import (
            ImplementationConstraintsError,
            missing_implementation_parameters,
            validate_constraint_questions,
            validate_implementation_constraints,
        )
        from chip_nebula.taskgraph.platform_inventory import constraint_inventory
        from chip_nebula.taskgraph.specification_flow import flow_state

        flow = flow_state(root)
        deliveries = (flow or {}).get("deliveries", {})
        baseline = deliveries.get("baseline") or {}
        bundle = deliveries.get("bundle") or {}
        revision_id = str(
            (baseline.get("payload") or {}).get("spec_revision_id")
            or (bundle.get("payload") or {}).get("revision_digest")
            or (spec_state or {}).get("revision_id", "")
        )
        inventory = _implementation_platform_inventory()
        usable = constraint_inventory(inventory)
        frozen = deliveries.get("constraints")
        draft = deliveries.get("constraints_draft")
        selected = frozen or draft
        document = _delivery_file(
            selected, "physical/chip-nebula/implementation.constraints.json",
        )
        document_error = ""
        missing: list[dict[str, Any]] = []
        if selected and document is None:
            document_error = "实现约束 Artifact 未包含可解析的约束 JSON"
        elif document is not None:
            try:
                document = validate_implementation_constraints(
                    document,
                    spec_revision_id=revision_id,
                    **usable,
                    require_frozen=bool(frozen),
                    allow_incomplete=not bool(frozen),
                )
                missing = missing_implementation_parameters(document)
                if missing:
                    document_error = "待补充参数：" + ", ".join(
                        field for item in missing for field in item["fields"]
                    )
            except ImplementationConstraintsError as exc:
                document_error = str(exc)

        candidates = deliveries.get("constraint_candidates")
        raw_questions = _delivery_file(
            candidates, "spec/project_constraints.questions.json",
        )
        questions: list[dict[str, Any]] = []
        question_error = ""
        if raw_questions is not None:
            try:
                questions = validate_constraint_questions(
                    raw_questions, spec_revision_id=revision_id, allow_empty=True,
                )
            except ImplementationConstraintsError as exc:
                question_error = str(exc)

        pending = int((flow or {}).get(
            "pending_project_decisions", (flow or {}).get("pending_decisions", 0),
        ))
        finalization = _prepare_phase(flow, "generate-project-constraints")
        if draft and not frozen:
            finalization = "awaiting_human"
        if frozen:
            finalization = "complete"
        consolidation = _prepare_phase(flow, "consolidate-project-decisions")
        human = (
            "awaiting_human" if pending
            else "complete" if consolidation == "complete"
            else "not_started"
        )
        return {
            "spec_revision_id": revision_id,
            "current": bool(frozen),
            "artifact_id": str((frozen or {}).get("id", "")),
            "document": document,
            "draft_ready": bool(draft and not frozen),
            "document_error": document_error,
            "missing_parameters": missing,
            "inventory": inventory,
            "questions": questions,
            "question_error": question_error,
            "inheritance": {
                "active": False, "source_artifact_id": "",
                "source_spec_revision_id": "", "document": None,
                "obsolete_request_ids": [],
            },
            "decisions": {
                "pending": pending,
                "resolved": 0,
                "items": [],
            },
            "phases": {
                "questions": _prepare_phase(
                    flow, "propose-project-constraint-decisions",
                ),
                "consolidation": consolidation,
                "human": human,
                "finalization": finalization,
            },
        }

    def _specir_state() -> dict[str, Any]:
        """Project PREPARE exclusively from current v2 Deliveries and WorkItems."""
        from chip_nebula.taskgraph.acceptance_plan import validate_acceptance_plan
        from chip_nebula.taskgraph.specification_flow import flow_state
        from chip_nebula.taskgraph.specir import (
            blocking_diagnostics,
            csir_available,
            is_clarification,
        )

        flow = flow_state(root)
        deliveries = (flow or {}).get("deliveries", {})
        bundle = deliveries.get("bundle")
        review = deliveries.get("review")
        compiler = deliveries.get("compiler")
        baseline = deliveries.get("baseline")
        frozen_acceptance = deliveries.get("acceptance")
        draft_acceptance = deliveries.get("acceptance_draft")
        acceptance_artifact = frozen_acceptance or draft_acceptance

        bundle_paths = set((bundle or {}).get("content", {}).get("paths", []))
        required_paths = {
            "spec/design_doc.md", "spec/draft.specir",
            "spec/provenance.json", "spec/questions.json",
        }
        missing_generation_outputs = sorted(required_paths - bundle_paths)
        bundle_payload = (bundle or {}).get("payload") or {}
        compiler_payload = (compiler or {}).get("payload") or {}
        review_payload = (review or {}).get("payload") or {}
        baseline_payload = (baseline or {}).get("payload") or {}
        revision_id = str(
            baseline_payload.get("spec_revision_id")
            or bundle_payload.get("revision_digest")
            or ""
        )
        diagnostics = [
            item for item in compiler_payload.get("diagnostics", [])
            if isinstance(item, dict)
        ]
        blocking = blocking_diagnostics(diagnostics)
        pending_clarifications = [
            item for item in diagnostics if is_clarification(item)
        ]
        valid = bool(
            compiler and compiler_payload.get("verdict") in {"pass", "passed"}
        )
        signoff = compiler_payload.get("signoff")
        if not isinstance(signoff, dict):
            signoff = None

        raw_questions = _delivery_file(bundle, "spec/questions.json")
        if isinstance(raw_questions, dict):
            raw_questions = raw_questions.get("questions", [])
        structured_questions = [
            item for item in (raw_questions or [])
            if isinstance(item, dict) and item.get("status", "open") == "open"
        ] if isinstance(raw_questions, list) else []

        acceptance_document = _delivery_file(
            acceptance_artifact, "spec/acceptance.plan.yaml",
        )
        acceptance_error = ""
        acceptance_current = False
        if isinstance(acceptance_document, dict):
            try:
                acceptance_document = validate_acceptance_plan(
                    acceptance_document, require_complete=True,
                )
                acceptance_current = True
            except ValueError as exc:
                acceptance_error = str(exc)
        elif acceptance_artifact:
            acceptance_error = "验收计划 Artifact 未包含可解析的 YAML"

        pending = int((flow or {}).get(
            "pending_spec_decisions", (flow or {}).get("pending_decisions", 0),
        ))
        consolidation = _prepare_phase(flow, "consolidate-spec-decisions")
        if pending:
            decision_status = "awaiting_human"
        elif baseline:
            decision_status = "complete"
        elif consolidation in {"running", "ready"}:
            decision_status = "running"
        elif consolidation == "failed":
            decision_status = "failed"
        elif compiler_payload.get("failure_kind") != "needs_decision":
            decision_status = "not_required" if valid else "not_started"
        else:
            decision_status = "not_started"

        readiness_blockers: list[str] = []
        if bundle and missing_generation_outputs:
            readiness_blockers.append(
                "规格 Artifact 缺少：" + "、".join(missing_generation_outputs)
            )
        if review and review_payload.get("verdict") not in {"pass", "passed"}:
            readiness_blockers.append("需求闭合审查未通过")
        if compiler and not valid:
            readiness_blockers.append("Spec Compiler/签署检查未通过")
        if pending:
            readiness_blockers.append(f"{pending} 项人类决策待完成")
        if baseline:
            readiness_status = "ready"
        elif not bundle:
            readiness_status = "not_started"
        elif not review:
            readiness_status = "review_required"
        elif not compiler:
            readiness_status = "check_required"
        elif pending:
            readiness_status = "alignment_required"
        else:
            readiness_status = "blocked"

        capability_gaps: list[str] = []
        if signoff and signoff.get("signoff_passed"):
            if not signoff.get("rtl_lowering_ready"):
                capability_gaps.append(
                    "CSIR 不能直接确定性 lowering；RTL Agent 必须同时读取已签署详细设计"
                )
            if not signoff.get("verification_contracts_ready"):
                capability_gaps.append("验证契约需要下游验证 Role 实现 adapter")

        decision_candidates = [
            item for item in compiler_payload.get("candidates", [])
            if isinstance(item, dict)
        ]
        counts = compiler_payload.get("counts", {})
        if not isinstance(counts, dict):
            counts = {}
        result = {
            "compiler_available": csir_available(),
            "file_exists": "spec/draft.specir" in bundle_paths,
            "path": "spec/draft.specir",
            "generation": {
                "status": (
                    "complete" if bundle and not missing_generation_outputs
                    else "incomplete" if bundle else "not_started"
                ),
                "complete": bool(bundle and not missing_generation_outputs),
                "missing_outputs": missing_generation_outputs,
            },
            "revision_id": revision_id,
            "input_digests": compiler_payload.get("input_digests", []),
            "valid": valid,
            "check_completed": bool(compiler),
            "check_stale": False,
            "diagnostics": diagnostics,
            "blocking_diagnostics": blocking,
            "pending_clarifications": pending_clarifications,
            "unresolved_questions": len(structured_questions),
            "structured_questions": structured_questions,
            "counts": {
                **counts,
                "errors": sum(
                    item.get("severity") == "error" for item in diagnostics
                ),
                "warnings": sum(
                    item.get("severity") == "warning" for item in diagnostics
                ),
                "notes": sum(
                    item.get("severity") == "note" for item in diagnostics
                ),
                "blocking": len(blocking),
                "pending": len(pending_clarifications),
            },
            "checked_at": str((compiler or {}).get("created_at", "")),
            "signoff": signoff,
            "readiness": {
                "name": "规格文档签署门禁",
                "status": readiness_status,
                "passed": bool(baseline),
                "blockers": readiness_blockers,
                "capability_gaps": capability_gaps,
            },
            "acceptance": {
                "exists": bool(acceptance_artifact),
                "confirmed": bool(frozen_acceptance),
                "document": acceptance_document,
                "current": acceptance_current,
                "stale": False,
                "trace_error": acceptance_error,
                "artifact_id": str((frozen_acceptance or {}).get("id", "")),
            },
            "decision_alignment": {
                "status": decision_status,
                "required_diagnostics": len([
                    item for item in diagnostics
                    if item.get("severity") in {"error", "warning"}
                ]),
                "required_candidates": len(decision_candidates) + len(
                    structured_questions
                ),
                "diagnostic_digest": "",
                "candidate_digest": "",
                "operation_id": "",
                "pending": pending,
                "resolved": 0,
                "ready_for_acceptance": bool(baseline),
            },
            "prepare_complete": bool(
                (flow or {}).get("prepare_complete")
                and frozen_acceptance
                and (flow or {}).get("constraints_ready")
            ),
            "flow": flow,
        }
        return result
    @app.get("/api/prepare/specir")
    async def api_prepare_specir_state():
        return _specir_state()

    @app.get("/api/prepare/implementation-constraints")
    async def api_prepare_implementation_constraints_state():
        return _implementation_constraints_state()

    def _wake_prepare_workflow(instance: dict[str, Any] | None) -> str:
        if not instance:
            raise ValueError("规格 flow 缺少冻结的启动契约")
        feature = f"taskgraph:{instance['workflow_id']}"
        active = run_manager.active_run_for(feature)
        if active:
            return active
        return run_manager.start_taskgraph(
            instance["recipe_path"], instance["workflow_id"],
            instance["framework"] or None, instance["model"] or None,
            int(instance["workers"]), baseline=instance["baseline"],
            resume=True, parameters=dict(instance["parameters"]),
        )

    def _normalize_project_constraints(
        document: dict[str, Any], state: dict[str, Any], *, status: str,
        persist: bool = True,
    ) -> dict[str, Any]:
        from chip_nebula.taskgraph.implementation_constraints import (
            ImplementationConstraintsError,
            missing_implementation_parameters,
            render_sdc,
            validate_implementation_constraints,
        )
        from chip_nebula.taskgraph.platform_inventory import constraint_inventory

        inventory = state["inventory"]
        resolved_ids = {
            str(item["decision_artifact_id"])
            for item in state["decisions"]["items"]
            if item.get("decision_artifact_id")
        }
        prepared = {
            **document,
            "schema_version": 1,
            "status": status,
            "spec_revision_id": state["spec_revision_id"],
            "decision_ids": sorted(resolved_ids) if resolved_ids else list(
                document.get("decision_ids", [])
            ),
        }
        try:
            options = dict(
                spec_revision_id=state["spec_revision_id"],
                **constraint_inventory(inventory),
                required_decision_ids=(resolved_ids or None),
                require_frozen=status == "frozen",
            )
            normalized = validate_implementation_constraints(prepared, **options, allow_incomplete=status == "draft")
            valid_sdc = True
            if status == "draft":
                try:
                    normalized = validate_implementation_constraints(normalized, **options)
                    valid_sdc = not missing_implementation_parameters(normalized)
                except ImplementationConstraintsError:
                    valid_sdc = False
        except ImplementationConstraintsError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if persist:
            constraint_path = root / "physical/chip-nebula/implementation.constraints.json"
            sdc_path = constraint_path.with_name("constraints.sdc")
            if not valid_sdc and (
                "sdc_sha256" in normalized or "sdc_sha256" in (state.get("document") or {})
            ):
                raise HTTPException(status_code=422, detail="Author constraints require a regenerated, verified author SDC")
            sdc = None
            if valid_sdc:
                try:
                    original = validate_implementation_constraints(
                        state["document"], **{**options, "require_frozen": False},
                    ) if state.get("document") else None
                    sdc = render_sdc(
                        normalized, authored_document=original,
                        authored_sdc=sdc_path.read_bytes() if original and "sdc_sha256" in original else None,
                    )
                except (ImplementationConstraintsError, OSError, UnicodeError) as exc:
                    raise HTTPException(status_code=422, detail=str(exc)) from exc
            constraint_path.parent.mkdir(parents=True, exist_ok=True)
            constraint_path.write_text(
                json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            if valid_sdc:
                sdc_path.write_text(sdc, encoding="utf-8")
            else:
                sdc_path.unlink(missing_ok=True)
        return normalized

    @app.put("/api/prepare/implementation-constraints")
    async def api_save_project_constraints(req: ProjectConstraintsSaveRequest):
        state = _implementation_constraints_state()
        if not state["spec_revision_id"]:
            raise HTTPException(status_code=409, detail="当前没有签署规格修订")
        _normalize_project_constraints(req.document, state, status="draft")
        return _implementation_constraints_state()

    @app.post("/api/prepare/implementation-constraints/confirm")
    async def api_confirm_project_constraints():
        state = _implementation_constraints_state()
        if state["current"]:
            raise HTTPException(status_code=409, detail="当前项目约束已经冻结")
        if state.get("phases", {}).get("finalization") == "running":
            raise HTTPException(
                status_code=409,
                detail="Project Constraints Agent 尚未完成输出校验，暂不能确认冻结",
            )
        if state["document"] is None:
            raise HTTPException(status_code=409, detail="尚无可确认的项目约束草稿")
        if state["decisions"]["pending"]:
            raise HTTPException(status_code=409, detail="项目约束决策尚未全部完成")
        normalized = _normalize_project_constraints(
            state["document"], state, status="frozen", persist=False,
        )
        from chip_nebula.taskgraph.specification_flow import confirm_prepare_page
        try:
            confirmation = confirm_prepare_page(
                root, "project_constraints_confirmation",
                answer=json.dumps({
                    "action": "confirm",
                    "document": normalized,
                }, ensure_ascii=False),
            )
            wake_run_id = _wake_prepare_workflow(confirmation.pop("instance"))
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {
            "state": _implementation_constraints_state(),
            "confirmation": confirmation,
            "wake_run_id": wake_run_id,
        }

    _SPECIR_CONTENT_CAP = 100_000

    def _specir_artifact_listing() -> list[dict[str, Any]]:
        """spec/ 目录顶层由 Agent 生成的产出文件清单（不含 build/ 等子目录）。"""
        import datetime as _dt

        spec_dir = root / "spec"
        result: list[dict[str, Any]] = []
        if not spec_dir.is_dir():
            return result
        entries = [
            item for item in spec_dir.iterdir()
            if item.is_file() and item.name in {
                "requirements.ledger.json", "design_doc.md", "draft.specir", "provenance.json",
                "contracts.json", "questions.json", "requirements.review.json", "acceptance.plan.yaml",
            }
        ]
        from chip_nebula.taskgraph.specification_flow import flow_state
        flow = flow_state(root)
        if flow:
            entries = [item for item in entries if f"spec/{item.name}" in flow["published_paths"] or item.name == "acceptance.plan.yaml"]
        # 按修改时间升序（生成顺序）：设计文档 → CSIR → 验收计划，与时间线一致
        for item in sorted(entries, key=lambda p: (p.stat().st_mtime, p.name)):
            stat = item.stat()
            result.append({
                "name": item.name,
                "path": f"spec/{item.name}",
                "size": stat.st_size,
                "modified_at": _dt.datetime.fromtimestamp(
                    stat.st_mtime, _dt.timezone.utc,
                ).isoformat(),
            })
        return result

    @app.get("/api/prepare/specir/files")
    async def api_prepare_specir_files():
        return {"files": _specir_artifact_listing()}

    @app.get("/api/prepare/specir/files/{name}")
    async def api_prepare_specir_file_content(name: str):
        known = {entry["name"] for entry in _specir_artifact_listing()}
        spec_dir = (root / "spec").resolve()
        target = (spec_dir / name).resolve()
        if name not in known or target.parent != spec_dir or not target.is_file():
            raise HTTPException(status_code=404, detail="文件不存在")
        content = target.read_text(encoding="utf-8", errors="replace")
        truncated = len(content) > _SPECIR_CONTENT_CAP
        return {
            "name": name,
            "path": f"spec/{name}",
            "content": content[:_SPECIR_CONTENT_CAP],
            "truncated": truncated,
        }

    @app.post("/api/prepare/specir/acceptance/save")
    async def api_prepare_acceptance_save(req: PrepareAcceptanceSaveRequest):
        """用户在验收计划页的每次编辑即时写回 acceptance.plan.yaml。"""
        from chip_nebula.taskgraph.acceptance_plan import validate_acceptance_plan
        try:
            document = validate_acceptance_plan(req.document)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        state = _specir_state()
        document["scope"] = "project"
        acceptance_file = root / "spec" / "acceptance.plan.yaml"
        acceptance_file.parent.mkdir(parents=True, exist_ok=True)
        acceptance_file.write_text(
            yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8",
        )
        return _specir_state()

    @app.post("/api/prepare/specir/acceptance/confirm")
    async def api_prepare_acceptance_confirm():
        """Resolve the static freeze Task's attached page confirmation."""
        acceptance_file = root / "spec" / "acceptance.plan.yaml"
        if not acceptance_file.is_file():
            raise HTTPException(status_code=400, detail="尚无验收计划可确认")
        try:
            document = yaml.safe_load(acceptance_file.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise HTTPException(status_code=400, detail=f"验收计划无法解析：{exc}") from exc
        if not isinstance(document, dict):
            raise HTTPException(status_code=400, detail="验收计划必须是映射结构")
        from chip_nebula.taskgraph.acceptance_plan import validate_acceptance_plan
        state = _specir_state()
        if not state["acceptance"]["current"]:
            raise HTTPException(
                status_code=409,
                detail="验收计划的需求/设计分组追踪尚未闭合，不能确认",
            )
        if not state["readiness"]["passed"]:
            blockers = "；".join(str(item) for item in state["readiness"].get("blockers", []) if item)
            raise HTTPException(
                status_code=409,
                detail="规格就绪门禁尚未通过，不能确认验收计划"
                + (f"：{blockers}" if blockers else ""),
            )
        constraints = _implementation_constraints_state(state)
        if not constraints["current"]:
            raise HTTPException(status_code=409, detail="实现约束尚未冻结，不能确认验收计划")
        trace_catalog = _specir_trace_catalog(root / "spec" / "provenance.json")
        try:
            document = validate_acceptance_plan(
                document,
                known_requirement_ids=trace_catalog["requirements"],
                known_design_groups=trace_catalog["design_groups"],
                required_requirement_ids=trace_catalog["required_requirements"],
                require_complete=True,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        document["scope"] = "project"
        document["confirmed"] = False
        from chip_nebula.taskgraph.specification_flow import confirm_prepare_page
        try:
            confirmation = confirm_prepare_page(
                root, "acceptance_plan_confirmation",
                answer=json.dumps({
                    "action": "confirm",
                    "document": document,
                }, ensure_ascii=False),
            )
            wake_run_id = _wake_prepare_workflow(confirmation.pop("instance"))
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {
            "state": _specir_state(),
            "confirmation": confirmation,
            "wake_run_id": wake_run_id,
        }

    @app.post("/api/prepare/specir/generate")
    async def api_prepare_specir_generate(req: PrepareSpecirGenerateRequest):
        """Launch the built-in scoped Recipe, never a single spec/** Agent."""
        from chip_nebula.taskgraph.specification_flow import start_specification_flow, flow_state

        document_text = req.document_text.strip()
        if not document_text:
            raise HTTPException(status_code=400, detail="需求文档内容不能为空")
        if req.action_kind not in {"", "spec_generate"}:
            raise HTTPException(status_code=409, detail="规格返工由内置 recipe 的 Handler 调度，不能启动单 Agent 快捷任务")
        current = flow_state(root)
        if current and (current["running"] or current["status"] == "awaiting_human"):
            raise HTTPException(status_code=409, detail="内置规格 flow 正在运行或等待人类决策")
        try:
            snapshot = workbench.capture_snapshot("specification source input")
            flow = start_specification_flow(root, document_text, req.framework, req.model.strip(), snapshot, run_manager)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc
        return {"flow": flow}

    @app.post("/api/prepare/specir/revise")
    async def api_prepare_specir_revise(req: PrepareSpecirRevisionRequest):
        """Record a direct human amendment and resume the current spec Author."""
        from chip_nebula.taskgraph.specification_flow import (
            flow_state, submit_specification_change,
        )

        instruction = req.instruction.strip()
        if not instruction:
            raise HTTPException(status_code=400, detail="规格变更内容不能为空")
        current = flow_state(root)
        if current is None:
            raise HTTPException(status_code=409, detail="当前项目没有内置规格 flow")
        feature = f"taskgraph:{current['workflow_id']}"
        if run_manager.active_run_for(feature) is not None:
            raise HTTPException(status_code=409, detail="内置规格 flow 正在运行")
        try:
            result = submit_specification_change(root, instruction)
            instance = result.pop("instance")
            if not instance:
                raise ValueError("规格 flow 缺少可恢复的启动契约")
            wake_run_id = _wake_prepare_workflow(instance)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {**result, "wake_run_id": wake_run_id}

    @app.post("/api/prepare/specir/flow/stop")
    async def api_prepare_specification_flow_stop():
        from chip_nebula.taskgraph.specification_flow import flow_state
        from chip_nebula.taskgraph.static_cli import (
            _recover_orphaned_attempts, database_path,
        )
        from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
        flow = flow_state(root)
        if not flow:
            raise HTTPException(status_code=409, detail="当前没有内置规格 flow")
        workflow = flow["workflow_id"]
        runner = run_manager.active_run_for(f"taskgraph:{workflow}")
        if runner:
            run_manager.stop(runner)
        database = database_path(root)
        with StaticTaskGraphStore(database) as store:
            _recover_orphaned_attempts(store, workflow, root)
            store.pause_workflow(workflow, "operator stopped PREPARE")
        return {"stopped": True, "workflow_id": workflow}

    @app.get("/api/workbench/execution-plans")
    async def api_workbench_execution_plans():
        return workbench_runs.list_execution_plans()

    @app.get("/api/workbench/execution-plans/{plan_id}")
    async def api_workbench_execution_plan(plan_id: str):
        try:
            return workbench_runs.execution_plan(plan_id)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/execution-plans")
    async def api_create_workbench_execution_plan(
        req: WorkbenchExecutionPlanRequest,
    ):
        try:
            return workbench_runs.create_execution_plan(
                req.instruction, req.framework,
                workspace=req.workspace, write_paths=req.write_paths,
                clarifications=req.clarifications,
            )
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/physical/input-remediation-plans")
    async def api_create_workbench_input_remediation_plan(
        req: WorkbenchInputRemediationRequest,
    ):
        try:
            return workbench_runs.create_input_remediation_plan(
                req.path, req.framework,
            )
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/execution-plans/{plan_id}/start")
    async def api_start_workbench_execution_plan(plan_id: str):
        try:
            return workbench_runs.start_execution_plan(plan_id)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/execution-plans/{plan_id}/pause")
    async def api_pause_workbench_execution_plan(plan_id: str):
        try:
            return workbench_runs.pause_execution_plan(plan_id)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/execution-plans/{plan_id}/resume")
    async def api_resume_workbench_execution_plan(plan_id: str):
        try:
            return workbench_runs.resume_execution_plan(plan_id)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/generic-acceptance")
    async def api_generic_acceptance_state():
        try:
            return workbench_runs.generic_acceptance_state()
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/generic-acceptance/existing/preview")
    async def api_preview_existing_checker_review():
        try:
            return workbench_runs.preview_existing_checker_review()
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/generic-acceptance/existing")
    async def api_start_existing_checker_review(req: ExistingCheckerReviewRequest):
        try:
            return workbench_runs.start_existing_checker_review(req.plan_digest)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/generic-acceptance/existing/{run_id}/evidence")
    async def api_existing_checker_review_evidence(run_id: str):
        try:
            return workbench_runs.existing_checker_review_evidence(run_id)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/generic-acceptance/existing/{run_id}/freeze")
    async def api_freeze_existing_checker_review(
        run_id: str, req: ExistingCheckerReviewFreezeRequest,
    ):
        try:
            return workbench_runs.freeze_existing_checker_review(
                run_id, confirmed=req.confirmed,
            )
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/operations/{operation_id}/acceptance-evidence")
    async def api_acceptance_candidate_evidence(operation_id: str):
        try:
            return workbench_runs.acceptance_candidate_evidence(operation_id)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/generic-acceptance/freeze")
    async def api_freeze_generic_acceptance(req: GenericAcceptanceFreezeRequest):
        try:
            return workbench_runs.freeze_generic_acceptance(
                req.operation_id, confirmed=req.confirmed,
            )
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/validation-runs")
    async def api_start_workbench_validation(req: WorkbenchValidationRequest):
        try:
            if req.kind not in {"all", "lint", "simulation"}:
                raise WorkbenchError("validation kind must be all, lint or simulation")
            return workbench_runs.start_validation(req.kind)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/physical/environment")
    async def api_workbench_physical_environment(platform: str = ""):
        try:
            return workbench_runs.physical_environment(platform=platform)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/physical/detect")
    async def api_detect_workbench_physical_project():
        try:
            return workbench.detect_physical_project()
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/physical/configure")
    async def api_configure_workbench_physical_project(
        req: WorkbenchPhysicalConfigureRequest,
    ):
        try:
            if not req.confirmed:
                raise WorkbenchError("必须确认顶层、时钟、周期和平台后才能生成物理流程")
            return workbench.configure_physical_project(
                top_module=req.top_module,
                top_parameters=req.top_parameters,
                clock_port=req.clock_port,
                clock_period_ns=req.clock_period_ns,
                platform=req.platform,
                simulation_command=req.simulation_command,
            )
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/physical-runs")
    async def api_start_workbench_physical(req: WorkbenchPhysicalRequest):
        try:
            return workbench_runs.start_physical(req.mode)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/formal/environment")
    async def api_workbench_formal_environment():
        try:
            return workbench_runs.formal_environment()
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/formal-runs")
    async def api_start_workbench_equivalence(req: WorkbenchEquivalenceRequest):
        try:
            return workbench_runs.start_equivalence(
                req.operation_id, timeout_seconds=req.timeout_seconds,
                clock_port=req.clock_port, reset_port=req.reset_port,
                reset_active=req.reset_active,
            )
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/runs")
    async def api_workbench_runs():
        return workbench_runs.list_runs()

    @app.get("/api/workbench/runs/{run_id}")
    async def api_workbench_run(run_id: str):
        try:
            return workbench_runs.get_run(run_id)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/runs/{run_id}/log")
    async def api_workbench_run_log(run_id: str):
        try:
            return {"run_id": run_id, "log": workbench_runs.run_log(run_id)}
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/runs/{run_id}/artifact-text")
    async def api_workbench_artifact_text(run_id: str, path: str):
        try:
            return workbench_runs.read_artifact(run_id, path)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/runs/{run_id}/evidence-bundle")
    async def api_workbench_evidence_bundle(run_id: str):
        try:
            path = workbench_runs.evidence_bundle(run_id)
            return FileResponse(
                path, media_type="application/zip", filename=path.name,
            )
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/runs/{run_id}/stop")
    async def api_stop_workbench_run(run_id: str):
        return {"stopped": workbench_runs.stop(run_id)}

    @app.get("/api/workbench/runs/{run_id}/artifacts/{artifact_path:path}")
    async def api_workbench_artifact(run_id: str, artifact_path: str):
        try:
            run = workbench_runs.get_run(run_id)
            if not any(item.get("path") == artifact_path for item in run.get("artifacts", [])):
                raise WorkbenchError("artifact is not registered for this run")
            path = (workbench.runs_dir / run_id / "artifacts" / artifact_path).resolve()
            base = (workbench.runs_dir / run_id / "artifacts").resolve()
            if base not in path.parents or not path.is_file():
                raise WorkbenchError("artifact not found")
            media_type = (
                "application/octet-stream"
                if path.suffix.lower() in {".gds", ".gdsii", ".odb"}
                else None
            )
            return FileResponse(
                path, media_type=media_type, filename=path.name,
            )
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/runs/{run_id}/waveform")
    async def api_launch_workbench_waveform(run_id: str, path: str):
        try:
            workbench_runs.launch_waveform(run_id, path)
            return {"launched": True}
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.post("/api/workbench/runs/{run_id}/layout")
    async def api_launch_workbench_layout(run_id: str, path: str):
        try:
            launch = workbench_runs.launch_layout(run_id, path)
            return {"launched": True, **launch}
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/workbench/viewers/{viewer_id}")
    async def api_workbench_viewer_status(viewer_id: int):
        try:
            return workbench_runs.viewer_status(viewer_id)
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    # --- Specification-driven design delivery ---------------------------

    def _design_error(exc: Exception) -> HTTPException:
        status = 409 if isinstance(exc, (IPLibraryError, AssemblyError)) else 400
        return HTTPException(status_code=status, detail=str(exc))

    @app.get("/api/design")
    async def api_design_summary():
        try:
            return design.summary()
        except (DesignDeliveryError, SpecificationError, IPLibraryError, AssemblyError) as exc:
            raise _design_error(exc) from exc

    @app.post("/api/design/bootstrap")
    async def api_design_bootstrap():
        try:
            return design.bootstrap()
        except (DesignDeliveryError, SpecificationError, IPLibraryError, AssemblyError) as exc:
            raise _design_error(exc) from exc

    @app.get("/api/design/architecture")
    async def api_design_architecture():
        try:
            return design.architecture_plan()
        except (DesignDeliveryError, SpecificationError, IPLibraryError) as exc:
            raise _design_error(exc) from exc

    @app.get("/api/design/spec")
    async def api_design_spec():
        try:
            return design.compile_spec()
        except (DesignDeliveryError, SpecificationError) as exc:
            raise _design_error(exc) from exc

    @app.put("/api/design/spec")
    async def api_save_design_spec(req: DesignSpecRequest):
        try:
            return design.save_spec(req.document)
        except (DesignDeliveryError, SpecificationError) as exc:
            raise _design_error(exc) from exc

    @app.get("/api/design/spec/examples/apb-gpio")
    def api_apb_gpio_spec_example():
        return default_apb_gpio_spec()

    @app.post("/api/design/spec/compile")
    async def api_compile_design_spec():
        try:
            return design.compile_spec()
        except (DesignDeliveryError, SpecificationError) as exc:
            raise _design_error(exc) from exc

    @app.post("/api/design/spec/freeze")
    async def api_freeze_design_spec():
        try:
            return design.freeze_spec()
        except (DesignDeliveryError, SpecificationError) as exc:
            raise _design_error(exc) from exc

    @app.get("/api/design/prepare/preview")
    async def api_preview_product_preparation():
        try:
            return design.preview_preparation()
        except (DesignDeliveryError, SpecificationError, IPLibraryError, AssemblyError, MemoryGenerationError) as exc:
            raise _design_error(exc) from exc

    @app.post("/api/design/prepare")
    async def api_prepare_product(req: ProductPreparationRequest):
        try:
            return design.prepare_assembly(req.plan_digest)
        except (DesignDeliveryError, SpecificationError, IPLibraryError, AssemblyError, MemoryGenerationError) as exc:
            raise _design_error(exc) from exc

    @app.get("/api/design/generic-bootstrap/preview")
    def api_preview_generic_bootstrap():
        return generic_bootstrap.preview()

    @app.get("/api/design/generic-bootstrap")
    def api_list_generic_bootstrap():
        return generic_bootstrap.list()

    @app.get("/api/design/generic-bootstrap/{bootstrap_id}")
    def api_get_generic_bootstrap(bootstrap_id: str):
        try:
            return generic_bootstrap.get(bootstrap_id)
        except GenericBootstrapError as exc:
            raise _design_error(exc) from exc

    @app.post("/api/design/generic-bootstrap")
    def api_start_generic_bootstrap(req: GenericBootstrapStartRequest):
        try:
            return generic_bootstrap.start(
                req.plan_digest, framework=req.framework,
            )
        except GenericBootstrapError as exc:
            raise _design_error(exc) from exc

    @app.post("/api/design/generic-bootstrap/{bootstrap_id}/stop")
    def api_stop_generic_bootstrap(bootstrap_id: str):
        try:
            return generic_bootstrap.stop(bootstrap_id)
        except GenericBootstrapError as exc:
            raise _design_error(exc) from exc

    @app.get("/api/design/product-flows")
    def api_product_flows():
        return product_flows.list()

    @app.get("/api/design/product-flows/{flow_id}")
    def api_product_flow(flow_id: str):
        try:
            return product_flows.inspect(flow_id)
        except ProductFlowError as exc:
            raise _design_error(exc) from exc

    @app.post("/api/design/product-flows")
    def api_start_product_flow(req: ProductFlowStartRequest):
        try:
            return product_flows.start(
                req.plan_digest, run_physical=req.run_physical,
                physical_timeout_seconds=req.physical_timeout_seconds,
                auto_repair_framework=req.auto_repair_framework,
            )
        except (ProductFlowError, DesignDeliveryError, SpecificationError,
                IPLibraryError, AssemblyError, MemoryGenerationError) as exc:
            raise _design_error(exc) from exc

    @app.post("/api/design/product-flows/{flow_id}/stop")
    def api_stop_product_flow(flow_id: str):
        try:
            return product_flows.stop(flow_id)
        except ProductFlowError as exc:
            raise _design_error(exc) from exc

    @app.get("/api/design/ip/catalog")
    async def api_ip_catalog():
        return design.library.catalog()

    @app.post("/api/design/ip/import")
    async def api_import_ip(req: IPImportRequest):
        try:
            if req.repository:
                return design.import_git_ip(
                    req.repository, req.ref, subdirectory=req.subdirectory,
                )
            if not req.path:
                raise DesignDeliveryError("本地路径或 Git 仓库必须填写一项")
            return design.import_ip(Path(req.path))
        except (DesignDeliveryError, IPLibraryError) as exc:
            raise _design_error(exc) from exc

    @app.post("/api/design/ip/validate")
    async def api_validate_ip(req: IPValidateRequest):
        try:
            return design.validate_ip(req.package_id, req.version, req.parameters or None)
        except (DesignDeliveryError, IPLibraryError) as exc:
            raise _design_error(exc) from exc

    @app.post("/api/design/ip/resolve")
    async def api_resolve_ip():
        try:
            return design.resolve()
        except (DesignDeliveryError, SpecificationError, IPLibraryError) as exc:
            raise _design_error(exc) from exc

    @app.post("/api/design/ip/upgrade")
    async def api_upgrade_ip():
        try:
            return design.resolve(upgrade=True)
        except (DesignDeliveryError, SpecificationError, IPLibraryError) as exc:
            raise _design_error(exc) from exc

    @app.post("/api/design/memory/generate")
    async def api_generate_design_memories():
        try:
            return design.generate_memories()
        except (DesignDeliveryError, SpecificationError, MemoryGenerationError) as exc:
            raise _design_error(exc) from exc

    @app.post("/api/design/assembly")
    async def api_assemble_design():
        try:
            return design.assemble()
        except (DesignDeliveryError, SpecificationError, IPLibraryError, AssemblyError) as exc:
            raise _design_error(exc) from exc

    @app.post("/api/design/assembly/validate")
    async def api_validate_design_assembly():
        try:
            config = design.assembly_validation_config()
            return workbench_runs.start_validation("all", config_override=config)
        except (DesignDeliveryError, SpecificationError, IPLibraryError, AssemblyError) as exc:
            raise _design_error(exc) from exc
        except WorkbenchError as exc:
            raise _workbench_error(exc) from exc

    @app.get("/api/design/coverage")
    async def api_design_coverage():
        return design.coverage()

    @app.get("/api/design/delivery/check")
    async def api_check_delivery():
        return design.check_delivery()

    @app.post("/api/design/delivery/export")
    async def api_export_delivery(req: DeliveryExportRequest):
        try:
            return design.export_delivery(
                confirmed=req.confirmed, include_physical=req.include_physical,
            )
        except (DesignDeliveryError, SpecificationError, IPLibraryError, AssemblyError) as exc:
            raise _design_error(exc) from exc

    @app.post("/api/design/ip/publish")
    async def api_publish_ip(req: IPPublishRequest):
        try:
            return design.publish_ip(req.version, confirmed=req.confirmed)
        except (DesignDeliveryError, SpecificationError, IPLibraryError, AssemblyError) as exc:
            raise _design_error(exc) from exc

    @app.get("/api/workspaces")
    async def api_workspaces():
        return list_workspaces(root)

    @app.delete("/api/workspaces/{feature_id}")
    async def api_delete_workspace(feature_id: str, force: bool = False):
        worktree_path = get_worktrees_dir(root) / feature_id
        if not worktree_path.exists():
            raise HTTPException(status_code=404, detail="Workspace not found")

        branch_name = f"feat-{feature_id.replace('__', '-')}"
        from chip_nebula.project import _run_git
        branch_check = _run_git(["rev-parse", "--verify", branch_name], cwd=root)
        branch_exists = branch_check.returncode == 0

        if branch_exists and not force:
            ancestor = _run_git(
                ["merge-base", "--is-ancestor", branch_name, "HEAD"], cwd=root
            )
            if ancestor.returncode != 0:
                raise HTTPException(
                    status_code=409,
                    detail="Workspace branch has commits not merged into the main checkout; use force=true to delete anyway",
                )

        try:
            WorkspaceManager(project_root=root).delete_workspace(feature_id)
        except Exception:
            import shutil
            shutil.rmtree(worktree_path, ignore_errors=True)

        if branch_exists:
            _run_git(["branch", "-D", branch_name], cwd=root)

        return {"deleted": True}

    @app.get("/api/pipelines")
    async def api_pipelines():
        return list_pipelines(root)

    @app.get("/api/agents")
    async def api_agents():
        return list_agents(root)

    @app.get("/api/taskgraph/active-runs")
    async def api_active_taskgraph_runs():
        return run_manager.active_taskgraph_runs()

    @app.get("/api/taskgraph")
    async def api_taskgraph(workflow_id: str = "", recipe: str = ""):
        from chip_nebula.taskgraph.static_store import StaticTaskGraphStore

        static_database = (
            get_chip_nebula_dir(root) / "shared" / "memory" / "taskgraph-v2.db"
        )
        scoped_workflow_id = workflow_id.strip()
        if static_database.is_file():
            with StaticTaskGraphStore(static_database) as store:
                if not scoped_workflow_id and recipe.strip():
                    recipe_name = recipe.strip().split("@", 1)[0]
                    candidates = [
                        item for item in store.list_workflows()
                        if item.recipe.split("@", 1)[0] == recipe_name
                    ]
                    if candidates:
                        scoped_workflow_id = max(
                            candidates,
                            key=lambda item: (item.created_at, item.id),
                        ).id
                snapshot = store.dashboard_snapshot(scoped_workflow_id)
        else:
            snapshot = {
                "tasks": [], "runs": [],
                "artifacts": [], "edges": [],
                "available_initial_artifacts": [], "workflows": [],
            }
        # Each Run executes in its own ephemeral worktree; surface the path so
        # the UI can point users at it. Attempts are the only execution unit in
        # the static kernel, so legacy Run workspaces are deliberately ignored.
        workspaces_root = get_chip_nebula_dir(root) / "taskgraph-v2" / "workspaces"
        for run in snapshot.get("runs", []):
            workspace = workspaces_root / str(run.get("id", ""))
            run["workspace"] = str(workspace)
            run["workspace_exists"] = workspace.is_dir()
        return snapshot

    def _builtin_recipes_dir() -> Path:
        return Path(chip_nebula.__file__).parent / "configs" / "recipes"

    def _resolve_recipe_path(recipe_path: str) -> Path | None:
        """@builtin/ 前缀解析到包内置 recipe；其余按工程 recipes 目录解析。"""
        from chip_nebula.project import get_recipes_dir
        if recipe_path.startswith("@builtin/"):
            base = _builtin_recipes_dir().resolve()
        else:
            base = get_recipes_dir(root).resolve()
        target = (base / recipe_path.removeprefix("@builtin/")).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            return None
        return target if target.is_file() else None

    @app.get("/api/taskgraph/recipes")
    async def api_taskgraph_recipes():
        from chip_nebula.project import get_recipes_dir
        base = get_recipes_dir(root)
        items = [str(path.relative_to(base)) for path in sorted(base.rglob("*.yaml"))]
        builtin = _builtin_recipes_dir()
        if builtin.is_dir():
            # 工程内同名 recipe 覆盖内置模板（与 Role 的项目覆盖语义一致）
            items += [
                f"@builtin/{path.relative_to(builtin)}"
                for path in sorted(builtin.rglob("*.yaml"))
                if str(path.relative_to(builtin)) not in set(items)
            ]
        return items

    @app.get("/api/taskgraph/recipes/{recipe_path:path}")
    async def api_taskgraph_recipe(recipe_path: str):
        target = _resolve_recipe_path(recipe_path)
        if target is None:
            raise HTTPException(status_code=404, detail="Recipe not found")
        document = yaml.safe_load(target.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise HTTPException(status_code=400, detail="Recipe root must be a mapping")
        return document

    @app.get("/api/taskgraph/catalog")
    async def api_taskgraph_catalog():
        from chip_nebula.taskgraph import default_gate_template_registry, load_schema_registry
        from chip_nebula.taskgraph.static_recipe import load_project_static_roles
        roles = load_project_static_roles(root)
        return {
            "roles": [
                {
                    "name": role.name, "version": role.version,
                    "stage": "",
                    "accepted_types": list(role.accepted_types),
                    "produced_types": list(role.produced_types),
                    "skills": list(role.skills),
                    "framework": role.framework, "model": role.model,
                    "description": " ".join(role.instruction.strip().split())[:180],
                }
                for role in sorted(roles.values(), key=lambda item: item.name)
            ],
            "schemas": load_schema_registry(root).describe(),
            "gate_templates": default_gate_template_registry().describe(),
            "frameworks": ["codex", "claude-code", "opencode", "qodercli", "mock"],
            "models": sorted({role.model for role in roles.values() if role.model}),
        }

    _ROLE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

    def _roles_dirs() -> tuple[Path, Path]:
        from chip_nebula.project import get_roles_dir
        builtin = Path(chip_nebula.__file__).parent / "configs" / "roles"
        return builtin, get_roles_dir(root)

    def _role_file_index() -> dict[str, Path]:
        """role 名字 → 实际定义它的 YAML 文件。

        与 load_project_roles 相同的来源和优先级（后面的覆盖前面的）：
        内置 configs/roles → 旧版 agents/ → agents/common → roles/ → roles/common。
        名字取自文件内容的 name/type 字段而不是文件名——旧版 Agent 配置文件
        的文件名（如 agents/common/sn_ifu_bside_design_reviewer.yaml）经常和
        里面的 type: design-reviewer 不一样。
        """
        from chip_nebula.taskgraph.static_recipe import load_static_role
        builtin_dir, project_dir = _roles_dirs()
        index: dict[str, Path] = {}
        for directory in (builtin_dir, project_dir):
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.yaml")):
                if path.name.startswith(("_", ".")):
                    continue
                try:
                    role = load_static_role(path.read_text(encoding="utf-8"))
                    index[role.name] = path
                except Exception:
                    continue
        return index

    def _role_source(name: str) -> str:
        builtin_dir, _ = _roles_dirs()
        path = _role_file_index().get(name)
        if path is None:
            return ""
        try:
            if path.is_relative_to(builtin_dir):
                return "builtin"
        except OSError:
            pass
        builtin_file = builtin_dir / f"{name}.yaml"
        if builtin_file.exists():
            # init_project 会把内置模板原样播种进项目；内容一致时仍视为内置
            try:
                if path.read_text(encoding="utf-8") == builtin_file.read_text(encoding="utf-8"):
                    return "builtin"
            except OSError:
                pass
            return "override"
        return "project"

    @app.get("/api/taskgraph/roles")
    async def api_taskgraph_roles():
        from chip_nebula.taskgraph.static_recipe import load_project_static_roles
        roles = load_project_static_roles(root)
        return [
            {
                "name": role.name, "version": role.version,
                "source": _role_source(role.name),
                "framework": role.framework, "model": role.model,
                "accepted_types": list(role.accepted_types),
                "produced_types": list(role.produced_types),
                "skills": list(role.skills),
                "description": " ".join(role.instruction.strip().split())[:120],
            }
            for role in sorted(roles.values(), key=lambda item: item.name)
        ]

    @app.get("/api/taskgraph/roles/{name}")
    async def api_taskgraph_role(name: str):
        if not _ROLE_NAME_PATTERN.match(name):
            raise HTTPException(status_code=400, detail="Invalid role name")
        path = _role_file_index().get(name)
        if path is None:
            raise HTTPException(status_code=404, detail="Role not found")
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        return {
            "name": name,
            "source": _role_source(name),
            "path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
            "document": document if isinstance(document, dict) else {},
        }

    @app.put("/api/taskgraph/roles/{name}")
    async def api_save_taskgraph_role(name: str, req: SaveTaskGraphRoleRequest):
        if not _ROLE_NAME_PATTERN.match(name):
            raise HTTPException(status_code=400, detail="Invalid role name")
        from chip_nebula.taskgraph.static_recipe import StaticRecipeError, load_static_role
        _, project_dir = _roles_dirs()
        project_dir.mkdir(parents=True, exist_ok=True)
        document: dict[str, Any] = {
            "name": name,
            "version": req.version,
        }
        if req.system_prompt.strip():
            document["system_prompt"] = req.system_prompt
        if req.framework.strip():
            document["framework"] = req.framework.strip()
        if req.model.strip():
            document["model"] = req.model.strip()
        if req.accepted_types:
            document["accepted_types"] = req.accepted_types
        if req.produced_types:
            document["produced_types"] = req.produced_types
        if req.skills:
            document["skills"] = req.skills
        text = yaml.safe_dump(document, allow_unicode=True, sort_keys=False)
        # Validate by round-tripping through the real loader before replacing
        # any existing file.
        probe = project_dir / f".{name}.probe.yaml"
        probe.write_text(text, encoding="utf-8")
        try:
            load_static_role(probe.read_text(encoding="utf-8"))
        except (StaticRecipeError, ValueError) as exc:
            probe.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        probe.replace(project_dir / f"{name}.yaml")
        return {"saved": True, "name": name, "source": _role_source(name)}

    @app.delete("/api/taskgraph/roles/{name}")
    async def api_delete_taskgraph_role(name: str):
        if not _ROLE_NAME_PATTERN.match(name):
            raise HTTPException(status_code=400, detail="Invalid role name")
        builtin_dir, _ = _roles_dirs()
        path = _role_file_index().get(name)
        if path is None:
            raise HTTPException(status_code=404, detail="Role not found")
        if path.is_relative_to(builtin_dir):
            raise HTTPException(
                status_code=400,
                detail="内置 Role 不能删除（它是平台模板，所有项目共享）",
            )
        path.unlink()
        # 删掉项目文件后可能回落到内置或更低优先级的同名定义
        return {"deleted": True, "reverted_to_builtin": name in _role_file_index()}

    # --- Artifact schema (input/output 类型) CRUD ---------------------------

    def _schemas_dir() -> Path:
        return get_chip_nebula_dir(root) / "schemas"

    def _builtin_schema_keys() -> set[tuple[str, int]]:
        from chip_nebula.taskgraph import default_schema_registry
        return {
            (item["type"], item["schema_version"])
            for item in default_schema_registry().describe()
        }

    def _schema_source(schema_type: str) -> str:
        if (_schemas_dir() / f"{schema_type}.yaml").exists():
            return "project"
        return "builtin" if any(k[0] == schema_type for k in _builtin_schema_keys()) else ""

    @app.get("/api/taskgraph/schemas")
    async def api_taskgraph_schemas():
        from chip_nebula.taskgraph import load_schema_registry
        return [
            {**item, "source": _schema_source(item["type"])}
            for item in load_schema_registry(root).describe()
        ]

    @app.get("/api/taskgraph/schemas/{schema_type}")
    async def api_taskgraph_schema(schema_type: str):
        from chip_nebula.taskgraph import default_schema_registry, load_schema_file
        project_file = _schemas_dir() / f"{schema_type}.yaml"
        if project_file.exists():
            try:
                schema = load_schema_file(project_file)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            fields = {
                name: [t.__name__ for t in (expected if isinstance(expected, tuple) else (expected,))]
                for name, expected in schema.required_fields.items()
            }
            return {
                "type": schema.artifact_type, "version": schema.version,
                "source": "project", "required_fields": fields,
                "field_descriptions": dict(schema.field_descriptions),
            }
        for item in default_schema_registry().describe():
            if item["type"] == schema_type:
                return {
                    "type": item["type"], "version": item["schema_version"],
                    "source": "builtin", "required_fields": item["required_fields"],
                    "field_descriptions": item.get("field_descriptions", {}),
                }
        raise HTTPException(status_code=404, detail="Schema not found")

    @app.put("/api/taskgraph/schemas/{schema_type}")
    async def api_save_taskgraph_schema(schema_type: str, req: SaveTaskGraphSchemaRequest):
        from chip_nebula.taskgraph import ArtifactValidationError, schema_from_document
        if (schema_type, req.version) in _builtin_schema_keys():
            raise HTTPException(
                status_code=400,
                detail=f"{schema_type}@{req.version} 是内置类型，不能直接覆盖；请把 version 提高一档再保存",
            )
        document = {
            "type": schema_type,
            "version": req.version,
            "required_fields": req.required_fields,
        }
        try:
            schema_from_document(document)
        except ArtifactValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        directory = _schemas_dir()
        directory.mkdir(parents=True, exist_ok=True)
        text = yaml.safe_dump(document, allow_unicode=True, sort_keys=False)
        probe = directory / f".{schema_type}.probe.yaml"
        probe.write_text(text, encoding="utf-8")
        probe.replace(directory / f"{schema_type}.yaml")
        return {"saved": True, "type": schema_type, "version": req.version}

    @app.delete("/api/taskgraph/schemas/{schema_type}")
    async def api_delete_taskgraph_schema(schema_type: str):
        project_file = _schemas_dir() / f"{schema_type}.yaml"
        if project_file.exists():
            project_file.unlink()
            return {"deleted": True}
        if any(k[0] == schema_type for k in _builtin_schema_keys()):
            raise HTTPException(
                status_code=400,
                detail="内置类型不能删除（平台模板，所有项目共享）",
            )
        raise HTTPException(status_code=404, detail="Schema not found")

    @app.get("/api/taskgraph/autogen/progress/{job_id}")
    def api_autogen_progress(job_id: str):
        from chip_nebula.workflowgen.progress import default_reporter
        snapshot = default_reporter().snapshot(job_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="unknown or expired job")
        return snapshot

    # 同步长任务：def（而非 async def）让 FastAPI 放入 threadpool，
    # 避免 LLM 生成期间阻塞事件循环。
    @app.post("/api/taskgraph/autogen/plan")
    def api_autogen_plan(req: AutogenPlanRequest):
        from chip_nebula.workflowgen import generate_plan
        if not req.prompt.strip():
            raise HTTPException(status_code=400, detail="prompt is required")
        try:
            draft = generate_plan(
                req.prompt, root,
                framework=req.framework or "opencode", model=req.model,
                feedback=req.feedback, previous_plan=req.previous_plan,
                session_id=req.session_id,
                job_id=req.job_id,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {
            **draft.plan.document(),
            "ok": draft.ok,
            "errors": list(draft.errors),
            "attempts": draft.attempts,
            "session_id": draft.session_id,
        }

    @app.post("/api/taskgraph/autogen")
    def api_autogen_taskgraph(req: AutogenWorkflowRequest):
        from chip_nebula.workflowgen import generate_workflow
        if not req.prompt.strip():
            raise HTTPException(status_code=400, detail="prompt is required")
        try:
            plan = None
            if req.plan:
                from chip_nebula.workflowgen.plan import WorkflowPlan, RolePlan
                plan = WorkflowPlan(
                    roles=tuple(
                        RolePlan(
                            name=str(item.get("name") or ""),
                            toolchain=tuple(map(str, item.get("toolchain") or ())),
                            purpose=str(item.get("purpose") or ""),
                            reuse=bool(item.get("reuse")),
                        )
                        for item in req.plan.get("roles") or ()
                    ),
                    detected_tools=tuple(map(str, req.plan.get("detected_tools") or ())),
                    notes=str(req.plan.get("notes") or ""),
                )
            draft = generate_workflow(
                req.prompt, root,
                framework=req.framework or "opencode", model=req.model,
                plan=plan, session_id=req.session_id,
                job_id=req.job_id,
                max_attempts=4,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {
            "recipe": draft.recipe,
            "roles": [{"name": name, "document": doc} for name, doc in draft.roles.items()],
            "schemas": [{"type": t, "document": doc} for t, doc in draft.schemas.items()],
            "validation": {
                "ok": draft.validation.ok,
                "errors": list(draft.validation.errors),
                "warnings": list(draft.validation.warnings),
            },
            "attempts": draft.attempts,
            "session_id": draft.session_id,
        }

    @app.post("/api/taskgraph/recipes")
    async def api_save_taskgraph_recipe(req: SaveTaskGraphRecipeRequest):
        from chip_nebula.project import get_recipes_dir
        from chip_nebula.taskgraph.static_recipe import (
            StaticRecipeCompiler, load_project_static_roles, load_static_recipe,
        )
        filename = req.filename.strip()
        if not filename.endswith((".yaml", ".yml")):
            filename += ".yaml"
        base = get_recipes_dir(root).resolve()
        target = (base / filename).resolve()
        try:
            target.relative_to(base)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Recipe path") from exc
        if target.exists() and not req.overwrite:
            raise HTTPException(status_code=409, detail="Recipe already exists")
        try:
            parameter_specs = req.recipe.get("parameters", {})
            parameters = {
                name: f"validate-{name}" for name in parameter_specs
            } if isinstance(parameter_specs, dict) else {}
            roles = load_project_static_roles(root)
            compiled = StaticRecipeCompiler(roles).compile(
                load_static_recipe(yaml.safe_dump(req.recipe)),
                workflow_id="builder-validation", goal="Validate Workflow Builder recipe",
                parameters=parameters,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(req.recipe, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return {"recipe": str(target.relative_to(base)), "tasks": len(compiled.tasks)}

    @app.delete("/api/taskgraph/recipes/{recipe_path:path}")
    async def api_delete_taskgraph_recipe(recipe_path: str):
        from chip_nebula.project import get_recipes_dir
        base = get_recipes_dir(root).resolve()
        target = (base / recipe_path).resolve()
        try:
            target.relative_to(base)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Recipe path") from exc
        if not target.is_file():
            raise HTTPException(status_code=404, detail="Recipe not found")
        target.unlink()
        return {"deleted": True, "recipe": recipe_path}

    @app.post("/api/taskgraph/artifacts")
    async def api_create_taskgraph_artifact(req: CreateTaskGraphArtifactRequest):
        import subprocess
        import uuid
        from chip_nebula.taskgraph.domain import (
            Artifact, ArtifactContent, ArtifactProducer,
        )
        from chip_nebula.taskgraph.static_store import (
            StateConflict, StaticTaskGraphStore,
        )
        artifact_id = req.artifact_id.strip() or f"external-{uuid.uuid4().hex}"
        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", artifact_id):
            raise HTTPException(status_code=400, detail="Artifact ID contains invalid characters")
        try:
            if req.content_kind == "git":
                commit = subprocess.run(
                    ["git", "rev-parse", req.git_ref], cwd=root, check=True,
                    capture_output=True, text=True,
                ).stdout.strip()
                tree = subprocess.run(
                    ["git", "rev-parse", f"{commit}^{{tree}}"], cwd=root, check=True,
                    capture_output=True, text=True,
                ).stdout.strip()
                content = ArtifactContent(
                    kind="git", commit=commit, tree=tree,
                    paths=tuple(req.paths),
                )
                payload = {**req.payload, "commit": commit, "paths": req.paths}
            else:
                content = ArtifactContent(
                    kind=req.content_kind, paths=tuple(req.paths),
                )
                payload = req.payload
            metadata = {"workflow_id": req.workflow_id or "external"}
            if req.uri.strip():
                metadata["uri"] = req.uri.strip()
            if req.artifact_type == "interface.contract" and req.contract_path.strip():
                # 以契约文件的最后修改 commit 作为版本标识：文件不变则版本不变，
                # 避免用 HEAD SHA 导致无关提交引发假冲突
                contract_file = req.contract_path.strip()
                revision = subprocess.run(
                    ["git", "log", "-1", "--format=%H", "--", contract_file],
                    cwd=root, check=True, capture_output=True, text=True,
                ).stdout.strip()
                if not revision:
                    raise HTTPException(
                        status_code=400,
                        detail=f"契约文件没有 Git 提交记录: {contract_file}",
                    )
                payload = {**payload, "contract_version": revision}
                metadata["contract_path"] = contract_file
            artifact = Artifact(
                id=artifact_id, type=req.artifact_type, schema_version=req.schema_version,
                producer=ArtifactProducer(
                    req.workflow_id or "external", f"human-{artifact_id}",
                    f"external:{artifact_id}", "human", 1,
                ),
                content=content, payload=payload,
                metadata=metadata,
            )
            database = (
                get_chip_nebula_dir(root) / "shared" / "memory" / "taskgraph-v2.db"
            )
            with StaticTaskGraphStore(database) as store:
                store.register_evidence_artifacts((artifact,))
            if req.content_kind == "git":
                subprocess.run(
                    ["git", "update-ref", f"refs/chip-nebula/artifacts/{artifact.id}", content.commit],
                    cwd=root, check=True, capture_output=True, text=True,
                )
            return {"artifact_id": artifact.id, "digest": artifact.digest}
        except StateConflict as exc:
            raise HTTPException(status_code=409, detail="Artifact ID already exists") from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/taskgraph/runs")
    async def api_start_taskgraph(req: StartTaskGraphRequest):
        recipe = _resolve_recipe_path(req.recipe)
        if recipe is None:
            raise HTTPException(status_code=404, detail="Recipe not found")
        if not req.workflow.strip():
            raise HTTPException(status_code=400, detail="workflow is required")
        existing_run = run_manager.active_run_for(f"taskgraph:{req.workflow.strip()}")
        if existing_run:
            raise HTTPException(
                status_code=409,
                detail=f"workflow is already running as {existing_run}",
            )
        launch_framework = req.framework or ""
        launch_model = req.model or ""
        launch_workers = req.workers
        launch_baseline = req.baseline
        launch_parameters = dict(req.parameters)
        try:
            from chip_nebula.taskgraph.static_recipe import load_static_recipe
            from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
            from chip_nebula.taskgraph.static_cli import (
                import_initial_artifact, prepare_workflow_resume,
            )
            document = load_static_recipe(recipe.read_text(encoding="utf-8"))
            specs = document.get("parameters", {})
            expected = {
                name: spec if isinstance(spec, str) else spec.get("type")
                for name, spec in specs.items()
            }
            static_database = (
                get_chip_nebula_dir(root) / "shared" / "memory" / "taskgraph-v2.db"
            )
            with StaticTaskGraphStore(static_database) as store:
                instance = store.get_workflow(req.workflow.strip())
            if req.resume:
                if instance is None:
                    raise ValueError("workflow has no frozen static Task plan to resume")
                if req.rebase_from:
                    raise ValueError(
                        "changing the frozen objective or initial inputs requires a new Workflow"
                    )
                metadata = dict(instance.metadata)
                if Path(str(metadata.get("recipe_path", ""))).resolve() != recipe.resolve():
                    raise ValueError("workflow resume recipe does not match its frozen definition")
                launch_framework = str(metadata.get("framework_override", ""))
                launch_model = str(metadata.get("model_override", ""))
                launch_parameters = dict(metadata.get("parameters", {}))
                launch_baseline = str(metadata.get("baseline_commit", launch_baseline))
            elif instance is not None:
                raise ValueError(f"workflow {req.workflow.strip()} already exists; use Resume")
            supplied = set(launch_parameters)
            missing = sorted(set(expected) - supplied)
            unknown = sorted(supplied - set(expected))
            if missing:
                raise ValueError(f"missing initial Artifacts: {', '.join(missing)}")
            if unknown:
                raise ValueError(f"unknown Recipe parameters: {', '.join(unknown)}")
            for name, artifact_id in launch_parameters.items():
                artifact = import_initial_artifact(root, artifact_id)
                if artifact.type != expected[name]:
                    raise ValueError(
                        f"parameter {name} requires {expected[name]}, got {artifact.type}"
                    )
            if req.resume:
                # Resume is an explicit operator action. Release workflow/task
                # pauses and replenish exhausted Task attempt budgets after
                # first preserving any workspace owned by a dead runner.
                # Artifact ids play no role here.
                prepare_workflow_resume(
                    root, static_database, req.workflow.strip(),
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        run_id = run_manager.start_taskgraph(
            str(recipe), req.workflow.strip(), launch_framework or None,
            launch_model or None, launch_workers,
            baseline=launch_baseline, resume=req.resume, parameters=launch_parameters,
        )
        return {"run_id": run_id, "workflow": req.workflow}

    _RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")

    def _taskgraph_log_file(run_id: str) -> Path:
        if not _RUN_ID_PATTERN.match(run_id):
            raise HTTPException(status_code=400, detail="Invalid run id")
        return (
            get_chip_nebula_dir(root) / "shared" / "memory" / "dashboard" / f"{run_id}.log"
        )

    @app.get("/api/taskgraph/runs/{run_id}")
    async def api_taskgraph_run_status(run_id: str):
        log_file = _taskgraph_log_file(run_id)
        return {
            "run_id": run_id,
            "active": run_manager.is_active(run_id),
            "returncode": run_manager.returncode_for(run_id),
            "has_log": log_file.is_file(),
        }

    @app.get("/api/taskgraph/runs/{run_id}/log")
    async def api_taskgraph_run_log(run_id: str, tail: int = 20000):
        log_file = _taskgraph_log_file(run_id)
        if not log_file.is_file():
            raise HTTPException(status_code=404, detail="Run log not found")
        tail = max(1, min(tail, 200_000))
        data = log_file.read_bytes()[-tail:]
        return {"run_id": run_id, "log": data.decode("utf-8", errors="replace")}

    @app.post("/api/taskgraph/task-runs/{run_id}/extend-timeout")
    async def api_extend_taskgraph_run_timeout(
        run_id: str, req: ExtendTaskGraphRunTimeoutRequest,
    ):
        """Extend the deadline of one currently running static Attempt."""
        from chip_nebula.taskgraph.domain import AttemptStatus
        from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
        from chip_nebula.taskgraph_run_controls import (
            extend_timeout_control, timeout_control_path,
        )

        static_database = (
            get_chip_nebula_dir(root) / "shared" / "memory" / "taskgraph-v2.db"
        )
        if not static_database.is_file():
            raise HTTPException(status_code=404, detail="Attempt not found")
        with StaticTaskGraphStore(static_database) as store:
            attempt = store.get_attempt(run_id)
            if attempt is None:
                raise HTTPException(status_code=404, detail="Attempt not found")
            if attempt.status != AttemptStatus.RUNNING:
                raise HTTPException(
                    status_code=409,
                    detail="Only a running Attempt can be extended",
                )
            path = timeout_control_path(get_chip_nebula_dir(root), run_id)
            try:
                control = extend_timeout_control(path, req.seconds)
            except FileNotFoundError as exc:
                raise HTTPException(
                    status_code=409, detail="Attempt has no live timeout control",
                ) from exc
            total = int(control["base_timeout_seconds"]) + int(control["extension_seconds"])
            deadline = float(control["started_at_epoch"]) + total
            store.record_attempt_diagnostics(run_id, {
                "base_timeout_seconds": int(control["base_timeout_seconds"]),
                "timeout_extension_seconds": int(control["extension_seconds"]),
                "timeout_deadline_epoch": deadline,
            })
        return {
            "run_id": run_id,
            "added_seconds": req.seconds,
            "extension_seconds": int(control["extension_seconds"]),
            "effective_timeout_seconds": total,
            "deadline_epoch": deadline,
        }

    @app.get("/api/taskgraph/sessions/{session_id}")
    async def api_taskgraph_session(session_id: str):
        return read_session_transcript_by_id(session_id)

    def _resolve_taskgraph_run_session(run_id: str) -> dict[str, Any]:
        """Resolve a Run transcript without occupying the API event loop.

        Session discovery may scan framework transcript stores and parse a
        large, actively growing JSONL file.  Keep that synchronous filesystem
        work in a helper so the HTTP endpoint can dispatch it to a worker
        thread instead of freezing unrelated dashboard polling requests.
        """
        static_database = (
            get_chip_nebula_dir(root) / "shared" / "memory" / "taskgraph-v2.db"
        )
        if not static_database.is_file():
            raise HTTPException(status_code=404, detail="Attempt not found")
        from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
        with StaticTaskGraphStore(static_database) as store:
            attempt = store.get_attempt(run_id)
            task = store.get_task(attempt.task_id) if attempt else None
        if attempt is None or task is None:
            raise HTTPException(status_code=404, detail="Attempt not found")
        if attempt.session_id:
            return read_session_transcript_by_id(attempt.session_id)

        fallback = {"session_id": "", "messages": [], "started_at": ""}
        per_attempt = (
            get_chip_nebula_dir(root) / "shared" / "memory" / "session_ids"
            / task.workflow_id / f"{task.key}.{run_id}.txt"
        )
        if per_attempt.is_file():
            result = read_session_transcript_by_id(per_attempt.read_text().strip())
            if result["messages"]:
                return result
            fallback = result

        # A workspace-derived transcript is keyed to this exact Attempt and
        # therefore outranks the stage sidecar, which tracks only the newest
        # session for a fixed Task.
        recovered = read_run_workspace_transcript(run_id)
        if recovered["messages"]:
            return recovered
        result = read_stage_session_transcript(root, task.workflow_id, task.key)
        if result["messages"]:
            return result
        fallback = fallback if fallback["session_id"] else result
        return fallback if fallback["session_id"] else recovered

    @app.get("/api/taskgraph/task-runs/{run_id}/session")
    async def api_taskgraph_run_session(run_id: str):
        return await asyncio.to_thread(_resolve_taskgraph_run_session, run_id)

    @app.post("/api/taskgraph/task-runs/{run_id}/continue")
    async def api_continue_taskgraph_run(
        run_id: str, req: ContinueTaskGraphRunRequest,
    ):
        """Attach human feedback to the same fixed Task.

        Static Task/Attempt workflows never clone a Task for a conversation.
        Feedback that arrives during an Attempt remains pending for the next
        Attempt; feedback to an idle Task wakes that Task and resumes its runner.
        """
        static_database = (
            get_chip_nebula_dir(root) / "shared" / "memory" / "taskgraph-v2.db"
        )
        if not static_database.is_file():
            raise HTTPException(status_code=404, detail="Attempt not found")
        import uuid
        from chip_nebula.taskgraph.domain import TaskState, WorkItemKind
        from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
        with StaticTaskGraphStore(static_database) as store:
            attempt = store.get_attempt(run_id)
            if attempt is None:
                raise HTTPException(status_code=404, detail="Attempt not found")
            task = store.get_task(attempt.task_id)
            workflow = store.get_workflow(task.workflow_id) if task else None
            if task is None or workflow is None:
                raise HTTPException(status_code=404, detail="Task or Workflow not found")
            instruction = req.instruction.strip()
            if not instruction:
                raise HTTPException(status_code=400, detail="Agent feedback is required")
            item = store.add_work(
                task.id, kind=WorkItemKind.CLARIFICATION,
                request_key=f"human-feedback:{uuid.uuid4().hex}",
                summary=instruction, source_task_id=task.id,
                propagate_to_dependents=True,
            )
            if store.task_state(task.id) == TaskState.PAUSED:
                store.resume_task(
                    task.id, additional_attempts=task.max_attempts,
                    reason="explicit human feedback",
                )
            metadata = dict(workflow.metadata)
            workflow_id = workflow.id
            runner_id = run_manager.active_run_for(f"taskgraph:{workflow_id}")
            if not runner_id:
                recipe = str(metadata.get("recipe_path", ""))
                if recipe and Path(recipe).is_file():
                    runner_id = run_manager.start_taskgraph(
                        recipe, workflow_id,
                        str(metadata.get("framework_override", "")) or None,
                        str(metadata.get("model_override", "")) or None,
                        int(metadata.get("workers", 4) or 4),
                        baseline=str(metadata.get("baseline_commit", "HEAD")),
                        resume=True,
                        parameters=dict(metadata.get("parameters", {})),
                    )
        return {
            "operation": None,
            "session_mode": "queued",
            "work_item_id": item.id,
            "task_id": task.id,
            "runner_id": runner_id or "",
        }

    @app.get("/api/taskgraph/events")
    async def api_taskgraph_events():
        static_database = (
            get_chip_nebula_dir(root) / "shared" / "memory" / "taskgraph-v2.db"
        )
        if not static_database.is_file():
            return []
        from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
        with StaticTaskGraphStore(static_database) as store:
            return store.events()

    @app.get("/api/taskgraph/human-tasks/{task_id}")
    async def api_taskgraph_human_task(task_id: str):
        from chip_nebula.taskgraph.static_store import (
            StateConflict as StaticStateConflict,
            StaticTaskGraphStore,
        )

        static_database = (
            get_chip_nebula_dir(root) / "shared" / "memory" / "taskgraph-v2.db"
        )
        if not static_database.is_file():
            raise HTTPException(status_code=404, detail="Task not found")
        try:
            with StaticTaskGraphStore(static_database) as static_store:
                if static_store.get_task(task_id) is None:
                    raise KeyError(task_id)
                return static_store.human_question_state(task_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except StaticStateConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/taskgraph/human-tasks/{task_id}/answers")
    async def api_taskgraph_human_task_answer(
        task_id: str, req: HumanTaskAnswerRequest,
    ):
        """Persist one Human Task selection and wake the workflow on completion."""
        import uuid
        from chip_nebula.taskgraph.static_store import (
            StateConflict as StaticStateConflict,
            StaticTaskGraphStore,
        )

        static_database = (
            get_chip_nebula_dir(root) / "shared" / "memory" / "taskgraph-v2.db"
        )
        if not static_database.is_file():
            raise HTTPException(status_code=404, detail="Task not found")
        try:
            with StaticTaskGraphStore(static_database) as static_store:
                static_task = static_store.get_task(task_id)
                if static_task is None:
                    raise KeyError(task_id)
                workflow = static_store.get_workflow(static_task.workflow_id)
                if workflow is None:
                    raise KeyError(static_task.workflow_id)
                question_id = req.issue_id.strip()
                static_store.answer_human_questions(
                    f"human-answer:{uuid.uuid4().hex}",
                    {question_id: req.selected.strip()},
                    evidence_artifact_ids={
                        question_id: tuple(req.evidence_artifact_ids),
                    },
                )
                try:
                    state = static_store.human_question_state(task_id)
                except StaticStateConflict:
                    state = {
                        "task_id": task_id,
                        "status": "answered",
                        "request_artifact_id": "",
                        "items": [], "answers": {}, "remaining": [],
                    }
                metadata = dict(workflow.metadata)
                workflow_id = workflow.id
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ValueError, StaticStateConflict) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        wake_run_id = ""
        if not state["remaining"]:
            feature = f"taskgraph:{workflow_id}"
            wake_run_id = run_manager.active_run_for(feature) or ""
            recipe = str(metadata.get("recipe_path", ""))
            if not wake_run_id and recipe and Path(recipe).is_file():
                wake_run_id = run_manager.start_taskgraph(
                    recipe, workflow_id,
                    str(metadata.get("framework_override", "")) or None,
                    str(metadata.get("model_override", "")) or None,
                    int(metadata.get("workers", 4) or 4),
                    baseline=str(metadata.get("baseline_commit", "HEAD")),
                    resume=True, parameters=dict(metadata.get("parameters", {})),
                )
        return {
            "state": state,
            "decision_artifact_id": "",
            "created_tasks": [],
            "wake_run_id": wake_run_id,
        }

    @app.get("/api/decisions")
    async def api_decisions():
        """Project attached human questions from the static WorkItem ledger."""
        from chip_nebula.taskgraph.domain import WorkItemKind, WorkItemStatus
        from chip_nebula.taskgraph.static_store import StaticTaskGraphStore

        database = (
            get_chip_nebula_dir(root) / "shared" / "memory" / "taskgraph-v2.db"
        )
        if not database.is_file():
            return {"pending": [], "log": []}

        pending: list[dict[str, Any]] = []
        log: list[dict[str, Any]] = []

        def detail(item) -> dict[str, Any]:
            try:
                value = json.loads(item.summary)
            except (TypeError, json.JSONDecodeError):
                value = {}
            return value if isinstance(value, dict) else {}

        with StaticTaskGraphStore(database) as store:
            for workflow in store.list_workflows():
                for task in store.list_tasks(workflow.id):
                    items = store.task_work_items(task.id)
                    answers = {
                        item.correlation_key: item
                        for item in items
                        if item.kind == WorkItemKind.HUMAN_ANSWER
                    }
                    for question in items:
                        if question.kind != WorkItemKind.HUMAN_QUESTION:
                            continue
                        fields = detail(question)
                        card = {
                            "id": question.id,
                            "human_task_id": task.id,
                            # The answer endpoint consumes the WorkItem id. A
                            # source diagnostic id remains presentation only.
                            "issue_id": question.id,
                            "source_issue_id": str(
                                fields.get("issue_id", question.id)
                            ),
                            "title": str(fields.get("title", "需要人工澄清")),
                            "context": str(fields.get("context", question.summary)),
                            "options": (
                                fields.get("options", [])
                                if isinstance(fields.get("options", []), list) else []
                            ),
                            "recommendation": fields.get("recommendation"),
                            "blocking": bool(fields.get("required", True)),
                            "presentation": str(
                                fields.get("presentation", "clarification")
                            ),
                            "workflow_id": workflow.id,
                            "stage": (
                                "specir"
                                if workflow.recipe.split("@", 1)[0]
                                == "specification-baseline-preparation"
                                else task.display_group
                            ),
                            "created_at": question.created_at,
                        }
                        answer = answers.get(question.correlation_key)
                        if question.status == WorkItemStatus.PENDING:
                            pending.append(card)
                        elif answer is not None:
                            log.append({
                                **card,
                                "id": answer.id,
                                "request_id": question.id,
                                "decision": answer.summary,
                                "decided_by": "human",
                                "created_at": answer.created_at,
                            })
        pending.sort(key=lambda item: item["created_at"])
        log.sort(key=lambda item: item["created_at"], reverse=True)
        return {"pending": pending, "log": log}

    @app.post("/api/pipelines")
    async def api_create_pipeline(req: CreatePipelineRequest):
        module = req.module.strip()
        name = req.name.strip()
        if not module or not name:
            raise HTTPException(status_code=400, detail="module and name are required")
        if not name.endswith((".yaml", ".yml")):
            name += ".yaml"

        pipelines_dir = get_pipelines_dir(root).resolve()
        target = (pipelines_dir / module / name).resolve()
        try:
            target.relative_to(pipelines_dir)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid pipeline path") from exc

        if target.exists():
            raise HTTPException(status_code=409, detail="Pipeline already exists")

        parser = PipelineParser()
        try:
            config = parser.parse_string(req.content)
            issues = parser.validate(config)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if issues:
            raise HTTPException(status_code=400, detail={"issues": issues})

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(req.content)
        return {
            "module": module,
            "name": name,
            "path": str(target.relative_to(root)),
        }

    @app.put("/api/yaml/batch/apply-colleagues")
    async def api_apply_to_colleagues(req: ApplyToColleaguesRequest):
        chip_dir = get_chip_nebula_dir(root).resolve()
        target = (chip_dir / req.path).resolve()
        try:
            rel = target.relative_to(chip_dir)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid YAML path") from exc

        if rel.parts[0:1] != ("agents",):
            raise HTTPException(status_code=400, detail="Only agent YAMLs are supported")

        if not target.exists():
            raise HTTPException(status_code=404, detail="File not found")

        directory = target.parent
        updated: list[str] = []
        unchanged: list[str] = []
        skipped: list[str] = []
        candidates = sorted(
            f for f in directory.iterdir()
            if f.is_file() and f.suffix in (".yaml", ".yml")
        )
        for candidate in candidates:
            if candidate.name.startswith("_"):
                continue
            if candidate.name == target.name:
                continue
            try:
                data = yaml.safe_load(candidate.read_text()) or {}
            except yaml.YAMLError:
                skipped.append(candidate.name)
                continue
            if not isinstance(data, dict):
                skipped.append(candidate.name)
                continue

            changed = False
            if req.model is not None and data.get("model") != req.model:
                data["model"] = req.model
                changed = True
            if req.model_provider is not None and data.get("model_provider") != req.model_provider:
                data["model_provider"] = req.model_provider
                changed = True
            if req.framework is not None and data.get("framework") != req.framework:
                data["framework"] = req.framework
                changed = True

            if changed:
                candidate.write_text(
                    yaml.dump(
                        data,
                        allow_unicode=True,
                        sort_keys=False,
                        default_flow_style=False,
                        Dumper=_PrettyYamlDumper,
                    )
                )
                updated.append(candidate.name)
            else:
                unchanged.append(candidate.name)

        return {"updated": updated, "unchanged": unchanged, "skipped": skipped}

    @app.put("/api/yaml/{path:path}")
    async def api_update_yaml(path: str, req: UpdateYamlRequest):
        chip_dir = get_chip_nebula_dir(root).resolve()
        target = (chip_dir / path).resolve()
        try:
            rel = target.relative_to(chip_dir)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid YAML path") from exc

        if not target.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if req.structured is not None and req.content is None:
            content_to_write = yaml.dump(
                req.structured,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
                Dumper=_PrettyYamlDumper,
            )
            content_for_validation = content_to_write
        elif req.content is not None:
            content_to_write = req.content
            content_for_validation = req.content
        else:
            raise HTTPException(status_code=400, detail="content or structured is required")

        if rel.parts[0:1] == ("pipelines",):
            parser = PipelineParser()
            try:
                config = parser.parse_string(content_for_validation)
                issues = parser.validate(config)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            if issues:
                raise HTTPException(status_code=400, detail={"issues": issues})

        try:
            yaml.safe_load(content_for_validation)
        except yaml.YAMLError as exc:
            raise HTTPException(status_code=400, detail=f"YAML syntax error: {exc}") from exc

        target.write_text(content_to_write)
        return {"ok": True}

    @app.get("/api/runs/{feature_id}")
    async def api_run(feature_id: str):
        state = read_pipeline_state(root, feature_id)
        state["stages"] = read_pipeline_definition(root, feature_id)
        return state

    @app.get("/api/runs/{feature_id}/raw_state")
    async def api_run_raw_state(feature_id: str):
        return read_pipeline_state(root, feature_id)

    @app.get("/api/runs/{feature_id}/pipeline_yaml")
    async def api_run_pipeline_yaml(feature_id: str):
        path = resolve_pipeline_file(root, feature_id)
        if path is None:
            raise HTTPException(status_code=404, detail="Pipeline file not found")
        try:
            return PlainTextResponse(path.read_text())
        except OSError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/runs/{feature_id}/active")
    async def api_active_run(feature_id: str):
        run_id = run_manager.active_run_for(feature_id)
        return {"active": bool(run_id), "run_id": run_id or ""}

    @app.get("/api/active-run")
    async def api_active_run_query(feature_id: str):
        """Return the active runner for identifiers that may contain slashes."""
        run_id = run_manager.active_run_for(feature_id)
        return {"active": bool(run_id), "run_id": run_id or ""}

    @app.get("/api/runs/{feature_id}/{run_id}/stages/{stage_name}/log")
    async def api_stage_log(feature_id: str, run_id: str, stage_name: str):
        return read_stage_log(root, feature_id, run_id, stage_name)

    @app.get("/api/runs/{feature_id}/stages/{stage_name}/session")
    async def api_stage_session(feature_id: str, stage_name: str):
        return read_stage_session_transcript(root, feature_id, stage_name)

    @app.get("/api/runs/{feature_id}/stages/{stage_name}/agent_config")
    async def api_stage_agent_config(feature_id: str, stage_name: str):
        return load_stage_agent_config(root, feature_id, stage_name)

    @app.put("/api/runs/{feature_id}/stages/{stage_name}/agent_config")
    async def api_update_stage_agent_config(
        feature_id: str, stage_name: str, req: UpdateAgentConfigRequest
    ):
        try:
            updates: dict[str, Any] = {}
            if req.system_prompt_template is not None:
                updates["system_prompt_template"] = req.system_prompt_template
            if req.write_paths is not None:
                updates["write_paths"] = req.write_paths
            return update_stage_agent_config(
                root, feature_id, stage_name, updates
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ValueError, OSError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/runs/{feature_id}/events")
    async def api_run_events(feature_id: str, request: Request):
        async def event_stream():
            last_state: str = ""
            while True:
                if await request.is_disconnected():
                    break
                state = read_pipeline_state(root, feature_id)
                state["stages"] = read_pipeline_definition(root, feature_id)
                payload = json.dumps(state, default=str)
                if payload != last_state:
                    yield f"data: {payload}\n\n"
                    last_state = payload
                await asyncio.sleep(1)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    @app.post("/api/runs")
    async def api_start_run(req: StartRunRequest):
        pipeline_path = Path(req.pipeline)
        if not pipeline_path.is_absolute():
            pipeline_path = (get_pipelines_dir(root) / req.pipeline).resolve()
        if not pipeline_path.exists():
            raise HTTPException(status_code=404, detail="Pipeline not found")

        log_dir = get_chip_nebula_dir(root) / "shared" / "memory" / "dashboard"
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / "start_run.log", "a") as f:
            f.write(
                f"{datetime.now().isoformat()} feature={req.feature} "
                f"pipeline={req.pipeline} resolved={pipeline_path} resume={req.resume}\n"
            )

        run_manager.prune_finished()

        worktree = get_worktrees_dir(root) / req.feature
        state_file = worktree / ".pipeline_state.json"

        if req.resume or req.from_stage:
            if not state_file.exists():
                raise HTTPException(
                    status_code=400, detail="No saved state to resume from"
                )
            saved = read_pipeline_state(root, req.feature)
            if req.from_stage:
                stages = read_pipeline_definition(root, req.feature)
                if req.from_stage not in stages:
                    raise HTTPException(
                        status_code=400, detail=f"Stage '{req.from_stage}' not found"
                    )
                _apply_from_stage_reset(saved, stages, req.from_stage)
                state_file.write_text(json.dumps(saved, indent=2, default=str))
            else:
                terminal = {"passed", "failed", "blocked"}
                statuses = saved.get("stage_status", {})
                if statuses and all(s in terminal for s in statuses.values()):
                    raise HTTPException(
                        status_code=400,
                        detail="Pipeline is already finished; use Start Fresh to retry",
                    )
                saved["rollbacks_executed"] = 0
                saved["last_updated"] = datetime.now().isoformat()
                state_file.write_text(json.dumps(saved, indent=2, default=str))
        elif state_file.exists():
            try:
                state = json.loads(state_file.read_text())
            except (json.JSONDecodeError, OSError):
                state = {}
            try:
                config = PipelineParser().parse_file(pipeline_path)
                pipeline_name = config.name
            except Exception:
                pipeline_name = ""
            state.update({
                "feature_id": req.feature,
                "pipeline": pipeline_name,
                "pipeline_path": str(pipeline_path),
                "run_id": "",
                "stage_status": {},
                "iteration_counters": {},
                "rollbacks_executed": 0,
                "pending_failure_contexts": {},
                "session_ids": {},
                "last_updated": datetime.now().isoformat(),
            })
            state_file.write_text(json.dumps(state, indent=2, default=str))

        run_id = run_manager.start(
            pipeline=str(pipeline_path),
            feature=req.feature,
            framework=req.framework,
            workers=req.workers,
            resume=req.resume or bool(req.from_stage),
            preserve_stopped=bool(req.from_stage),
        )
        return {"run_id": run_id, "feature": req.feature}

    @app.post("/api/runs/{run_id}/stop")
    async def api_stop_run(run_id: str):
        feature = run_manager.feature_for(run_id)
        if feature and feature.startswith("taskgraph:") and run_manager.is_active(run_id):
            from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
            database = get_chip_nebula_dir(root) / "shared" / "memory" / "taskgraph-v2.db"
            if database.is_file():
                with StaticTaskGraphStore(database) as store:
                    workflow_id = feature.removeprefix("taskgraph:")
                    if store.get_workflow(workflow_id) is not None:
                        store.request_workflow_stop(
                            workflow_id, "workflow runner stopped by operator",
                        )
        stopped = run_manager.stop(run_id)

        if stopped and feature:
            if feature.startswith("taskgraph:"):
                # Persist cancellation as a terminal Attempt while releasing
                # its pending WorkItems on the same fixed Task.  Resume is an
                # explicit operator action; stopping never rewrites history
                # back to a synthetic "ready" state.
                from chip_nebula.taskgraph.static_cli import cancel_workflow_attempts
                database = (
                    get_chip_nebula_dir(root)
                    / "shared" / "memory" / "taskgraph-v2.db"
                )
                cancel_workflow_attempts(
                    root, database, feature.removeprefix("taskgraph:"),
                )
            state_file = get_worktrees_dir(root) / feature / ".pipeline_state.json"
            if state_file.exists():
                try:
                    saved = json.loads(state_file.read_text())
                except (json.JSONDecodeError, OSError):
                    saved = {}
                statuses = saved.get("stage_status", {})
                changed = False
                for name, status in list(statuses.items()):
                    if status == "running":
                        statuses[name] = "stopped"
                        changed = True
                if changed:
                    saved["last_updated"] = datetime.now().isoformat()
                    state_file.write_text(json.dumps(saved, indent=2, default=str))

        return {"stopped": stopped}

    @app.post("/api/runs/{feature_id}/intervene")
    async def api_intervene(feature_id: str, req: InterveneRequest):
        state = read_pipeline_state(root, feature_id)
        pipeline_path = state.get("pipeline_path", "")
        if not pipeline_path:
            raise HTTPException(
                status_code=400, detail="Cannot resume: pipeline path not recorded in state"
            )

        # Stop the active run FIRST and wait for the process to die.
        # Otherwise its in-flight save_state can clobber the state surgery
        # below and silently drop the inject.
        active_run_id = run_manager.active_run_for(feature_id)
        if active_run_id:
            run_manager.stop(active_run_id)

        state_file = get_worktrees_dir(root) / feature_id / ".pipeline_state.json"
        if req.from_stage:
            stages = read_pipeline_definition(root, feature_id)
            if req.from_stage not in stages:
                raise HTTPException(
                    status_code=400, detail=f"Stage '{req.from_stage}' not found"
                )
            saved = json.loads(state_file.read_text()) if state_file.exists() else state
            _apply_from_stage_reset(saved, stages, req.from_stage)
            state_file.write_text(json.dumps(saved, indent=2, default=str))
        else:
            if state_file.exists():
                saved = json.loads(state_file.read_text())
                saved["rollbacks_executed"] = 0
                saved["last_updated"] = datetime.now().isoformat()
                state_file.write_text(json.dumps(saved, indent=2, default=str))

        # Framework is a runtime/run-level choice, not part of pipeline state.
        # The inject UI has no framework selector, so always default to auto
        # and let stage/agent YAML decide.
        framework = None
        inject_intervention(
            project_root=root,
            feature_id=feature_id,
            stage=req.stage,
            text=req.text,
            kind=req.kind,
        )
        new_run_id = run_manager.start(
            pipeline=pipeline_path,
            feature=feature_id,
            framework=framework,
            workers=4,
            run_id=active_run_id,
            resume=True,
            preserve_stopped=True,
        )
        return {"run_id": new_run_id, "feature": feature_id}

    @app.get("/api/yaml/{path:path}")
    async def api_yaml(path: str):
        content = read_yaml_file(root, path)
        if content is None:
            raise HTTPException(status_code=404, detail="File not found")
        return PlainTextResponse(content)

    # ------------------------------------------------------------------
    #  Roundtables (docs/design/roundtable-design.md §8.2)
    # ------------------------------------------------------------------
    from chip_nebula.roundtable import runner as rt_runner
    from chip_nebula.roundtable import store as rt_store
    from chip_nebula.roundtable import prompt_generator as rt_prompt_generator
    from chip_nebula.roundtable.models import (
        STATUS_AWAITING_DECISION,
        STATUS_DESTROYED,
        STATUS_DONE,
        STATUS_PAUSED,
        STATUS_RUNNING,
        RoundtableConfig,
    )

    def _rt_dir(table_id: str) -> Path:
        tdir = rt_store.table_dir(root, table_id)
        if not tdir.exists():
            raise HTTPException(status_code=404, detail="Roundtable not found")
        return tdir

    def _rt_detail(tdir: Path) -> dict:
        cfg = rt_store.load_config(tdir)
        state = rt_store.load_state(tdir)
        transcript = [e.to_dict() for e in rt_store.read_transcript(tdir)]
        # Pending human messages are shown immediately in the chat window;
        # the orchestrator drains them into the transcript at the next
        # speaking boundary.
        for m in rt_store.read_pending_messages(tdir):
            transcript.append({
                "seq": None, "round": state.current_round,
                "author_type": "human", "author_name": m.get("author_name", ""),
                "kind": "human_note", "text": m.get("text", ""),
                "ts": m.get("ts", ""), "pending": True,
            })
        summary_path = tdir / "output" / "summary.md"
        return {
            "config": cfg.to_dict(),
            "state": state.to_dict(),
            "transcript": transcript,
            "alive": rt_store.is_orchestrator_alive(tdir),
            "summary": summary_path.read_text() if summary_path.exists() else "",
            "final_document": (
                (tdir / "output" / "final_document.md").read_text()
                if (tdir / "output" / "final_document.md").exists() else ""
            ),
        }

    @app.get("/api/roundtables")
    async def api_rt_list():
        return rt_store.list_tables(root)

    @app.post("/api/roundtables")
    async def api_rt_create(req: CreateRoundtableRequest):
        data = {
            "table_id": rt_store.new_table_id(req.topic),
            "topic": req.topic,
            "created_by": req.created_by or "human",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "max_rounds": req.max_rounds,
            "chairman": req.chairman,
            "participants": req.participants,
        }
        if req.doc_writer:
            data["doc_writer"] = req.doc_writer
        cfg = RoundtableConfig.from_dict(data)
        issues = cfg.validate()
        if issues:
            raise HTTPException(status_code=400, detail={"issues": issues})
        try:
            tdir = rt_store.create_table(root, cfg)
        except FileExistsError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if req.start:
            rt_runner.start_orchestrator(root, cfg.table_id)
        return {"table_id": cfg.table_id, "path": str(tdir.relative_to(root))}

    @app.get("/api/roundtables/{table_id}")
    async def api_rt_detail(table_id: str):
        return _rt_detail(_rt_dir(table_id))

    @app.put("/api/roundtables/{table_id}")
    async def api_rt_update(table_id: str, req: UpdateRoundtableRequest):
        tdir = _rt_dir(table_id)
        state = rt_store.load_state(tdir)
        if state.status == STATUS_RUNNING:
            raise HTTPException(
                status_code=400,
                detail="圆桌正在运行，请先 Pause 再编辑配置",
            )
        old_cfg = rt_store.load_config(tdir)
        data = old_cfg.to_dict()
        data.update({
            "topic": req.topic,
            "chairman": req.chairman,
            "participants": req.participants,
            "max_rounds": req.max_rounds,
        })
        if req.doc_writer:
            data["doc_writer"] = req.doc_writer
        cfg = RoundtableConfig.from_dict(data)
        issues = cfg.validate()
        if issues:
            raise HTTPException(status_code=400, detail={"issues": issues})
        cfg.save(tdir / "config.yaml")
        return {"table_id": cfg.table_id}

    def _rt_save_prompts(tdir: Path, cfg: RoundtableConfig) -> None:
        """Persist agent role prompts to <tdir>/prompts/<role>.md and update config."""
        prompts_dir = tdir / "prompts"
        prompts_dir.mkdir(exist_ok=True)
        for p in cfg.participants:
            if p.kind != "agent":
                continue
            safe = re.sub(r"[^a-zA-Z0-9_\-一-鿿]+", "_", p.name).strip("_")[:64]
            if not safe:
                safe = "agent"
            (prompts_dir / f"{safe}.md").write_text(
                p.role_prompt, encoding="utf-8"
            )
        cfg.save(tdir / "config.yaml")

    @app.post("/api/roundtables/{table_id}/generate-prompts")
    async def api_rt_generate_prompts(
        table_id: str, req: GenerateRoundtablePromptsRequest
    ):
        tdir = _rt_dir(table_id)
        cfg = rt_store.load_config(tdir)
        agents = cfg.speaking_agents()
        if not agents:
            raise HTTPException(status_code=400, detail="No agent participants")
        roles = [{"name": a.name, "is_chairman": a.name == cfg.chairman} for a in agents]
        try:
            prompts = rt_prompt_generator.generate_role_prompts(
                topic=cfg.topic,
                roles=roles,
                framework=req.generator_framework,
                model=req.generator_model,
                model_provider=req.generator_model_provider,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"prompts": prompts}

    @app.put("/api/roundtables/{table_id}/prompts")
    async def api_rt_save_prompts(table_id: str, req: SaveRoundtablePromptsRequest):
        tdir = _rt_dir(table_id)
        state = rt_store.load_state(tdir)
        if state.status == STATUS_RUNNING:
            raise HTTPException(
                status_code=400,
                detail="圆桌正在运行，请先 Pause 再保存",
            )
        cfg = RoundtableConfig.from_dict({
            "table_id": table_id,
            "topic": req.topic,
            "chairman": req.chairman,
            "participants": req.participants,
            "max_rounds": req.max_rounds,
            "created_by": "human",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            **({"doc_writer": req.doc_writer} if req.doc_writer else {}),
        })
        issues = cfg.validate()
        if issues:
            raise HTTPException(status_code=400, detail={"issues": issues})
        _rt_save_prompts(tdir, cfg)
        return {"table_id": cfg.table_id, "saved": True}

    def _rt_spawn(table_id: str) -> dict:
        pid = rt_runner.start_orchestrator(root, table_id)
        return {"started": True, "pid": pid}

    @app.post("/api/roundtables/{table_id}/start")
    async def api_rt_start(table_id: str):
        tdir = _rt_dir(table_id)
        state = rt_store.load_state(tdir)
        if state.status in (STATUS_DONE, STATUS_DESTROYED):
            raise HTTPException(status_code=400, detail=f"Table is {state.status}")
        if rt_store.is_orchestrator_alive(tdir):
            raise HTTPException(status_code=409, detail="Orchestrator already running")
        return _rt_spawn(table_id)

    @app.post("/api/roundtables/{table_id}/pause")
    async def api_rt_pause(table_id: str):
        tdir = _rt_dir(table_id)
        stopped = rt_runner.stop_orchestrator(root, table_id)
        state = rt_store.load_state(tdir)
        # SIGKILL backstop path: orchestrator could not checkpoint itself.
        if state.status == STATUS_RUNNING and not rt_store.is_orchestrator_alive(tdir):
            state.status = STATUS_PAUSED
            state.run_pid = 0
            rt_store.save_state(tdir, state)
        return {"stopped": stopped, "status": rt_store.load_state(tdir).status}

    @app.post("/api/roundtables/{table_id}/resume")
    async def api_rt_resume(table_id: str):
        tdir = _rt_dir(table_id)
        state = rt_store.load_state(tdir)
        if state.status != STATUS_PAUSED:
            raise HTTPException(status_code=400, detail=f"Table is {state.status}, not paused")
        if rt_store.is_orchestrator_alive(tdir):
            raise HTTPException(status_code=409, detail="Orchestrator already running")
        return _rt_spawn(table_id)

    @app.post("/api/roundtables/{table_id}/destroy")
    async def api_rt_destroy(table_id: str, purge: bool = False):
        tdir = _rt_dir(table_id)
        rt_runner.stop_orchestrator(root, table_id)
        if purge:
            import shutil
            shutil.rmtree(tdir, ignore_errors=True)
            return {"destroyed": True, "purged": True}
        state = rt_store.load_state(tdir)
        state.status = STATUS_DESTROYED
        state.run_pid = 0
        rt_store.save_state(tdir, state)
        rt_store.append_system_event(tdir, "圆桌已销毁（保留只读存档）")
        return {"destroyed": True, "purged": False}

    @app.post("/api/roundtables/{table_id}/messages")
    async def api_rt_message(table_id: str, req: RoundtableMessageRequest):
        tdir = _rt_dir(table_id)
        if not req.text.strip():
            raise HTTPException(status_code=400, detail="text is required")
        cfg = rt_store.load_config(tdir)
        humans = [p.name for p in cfg.participants if p.kind == "human"]
        author = req.author_name or (humans[0] if humans else "human")
        return rt_store.append_pending_message(tdir, author, req.text)

    @app.post("/api/roundtables/{table_id}/request-summary")
    async def api_rt_request_summary(table_id: str):
        tdir = _rt_dir(table_id)
        state = rt_store.load_state(tdir)
        if state.status != STATUS_RUNNING:
            raise HTTPException(status_code=400, detail=f"Table is {state.status}, not running")
        state.force_summary = True
        rt_store.save_state(tdir, state)
        rt_store.append_system_event(tdir, "人类已要求主席尽快收束讨论")
        return {"force_summary": True}

    @app.post("/api/roundtables/{table_id}/decide")
    async def api_rt_decide(table_id: str, req: RoundtableDecisionRequest):
        tdir = _rt_dir(table_id)
        state = rt_store.load_state(tdir)
        if state.status != STATUS_AWAITING_DECISION:
            raise HTTPException(
                status_code=400,
                detail=f"Table is {state.status}, not awaiting_decision",
            )
        if req.action not in ("approve", "continue", "rewrite"):
            raise HTTPException(status_code=400, detail="action must be approve|continue|rewrite")
        if req.action == "continue":
            # The opinion joins the discussion as a human note before resume.
            rt_store.append_transcript(
                tdir, round_no=state.current_round, author_type="human",
                author_name=req.author_name or "human",
                kind="human_note", text=req.text,
            )
        state.decision = {
            "action": req.action,
            "text": req.text,
            "output_path": req.output_path or "",
            "doc_mode": req.doc_mode or "direct",
            "author_name": req.author_name or "human",
            "ts": datetime.now().isoformat(timespec="seconds"),
        }
        rt_store.save_state(tdir, state)
        return _rt_spawn(table_id)

    @app.get("/api/roundtables/{table_id}/events")
    async def api_rt_events(table_id: str, request: Request):
        tdir = _rt_dir(table_id)

        async def event_stream():
            last_payload: str = ""
            while True:
                if await request.is_disconnected():
                    break
                payload = json.dumps(_rt_detail(tdir), default=str, ensure_ascii=False)
                if payload != last_payload:
                    yield f"data: {payload}\n\n"
                    last_payload = payload
                await asyncio.sleep(1)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    @app.get("/api/roundtables/{table_id}/participants/{name}/session")
    async def api_rt_participant_session(table_id: str, name: str):
        tdir = _rt_dir(table_id)
        # Prefer the adapter sidecar: it is written at dispatch start, so an
        # in-flight turn is visible live; state.json lags until the turn ends.
        sidecar = (
            get_chip_nebula_dir(root)
            / "shared" / "memory" / "session_ids"
            / f"roundtable-{table_id}" / f"{name}.txt"
        )
        session_id = ""
        if sidecar.is_file():
            try:
                session_id = sidecar.read_text().strip()
            except OSError:
                session_id = ""
        if not session_id:
            session_id = rt_store.load_state(tdir).session_ids.get(name, "")
        return read_session_transcript_by_id(session_id)

    return app


def _recover_static_taskgraph_orphans(project_root: Path) -> tuple[str, ...]:
    """Close dead v2 Attempts so the desktop never presents phantom workers.

    The runner performs the same recovery before resuming one Workflow.  The
    desktop owns the project-wide projection, so it must also reconcile every
    stored Workflow after an Electron/backend crash rather than displaying a
    dead PID as a live Agent indefinitely.
    """
    from chip_nebula.taskgraph.domain import WorkflowStatus
    from chip_nebula.taskgraph.static_cli import _recover_orphaned_attempts
    from chip_nebula.taskgraph.static_store import StaticTaskGraphStore

    database = (
        get_chip_nebula_dir(project_root) / "shared" / "memory" / "taskgraph-v2.db"
    )
    if not database.is_file():
        return ()
    recovered: list[str] = []
    with StaticTaskGraphStore(database) as store:
        for workflow in store.list_workflows():
            attempts = _recover_orphaned_attempts(
                store, workflow.id, project_root,
            )
            if not attempts:
                continue
            recovered.extend(attempts)
            current = store.get_workflow(workflow.id)
            active = any(
                store.active_attempt(task.id) is not None
                for task in store.list_tasks(workflow.id)
            )
            if (
                current is not None
                and current.status in {WorkflowStatus.ACTIVE, WorkflowStatus.READY}
                and not active
            ):
                store.pause_workflow(
                    workflow.id,
                    "runner process ended; recover the saved Task work with Resume",
                )
    return tuple(recovered)

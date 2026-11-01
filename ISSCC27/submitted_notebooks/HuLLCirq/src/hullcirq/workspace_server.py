"""Project/system sessions around the existing single-design execution service.

Switching is explicit, serialized with API requests and denied while a worker or
unresolved cleanup is active. The original single-store API remains available to
scripts/tests which do not enable a workspace.
"""
from __future__ import annotations

import threading
import uuid
import shutil
import tempfile
import hashlib
import json
import copy
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from .domain import DomainError
from .store import ProjectStore, strict_loads

MANAGERS = ("postlayout_workflow", "lvs_workflow", "drc_workflow", "physical_workflow",
            "global_workflow", "global_generation", "implementation_specs", "repair_analysis", "generation_batches", "workflow", "generation")


def _postlayout_profile_directory(registry_root, project_id, system_id):
    # Keep fixed S14 operation paths below the Windows path limit at the public
    # checkout location. The exact ID pair remains the deterministic scope;
    # no project/system ID is expanded into nested runtime directory names.
    identity = json.dumps([project_id, system_id], ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    scope = hashlib.sha256(identity).hexdigest()[:32]
    profile_root = (registry_root / "runtime_profiles").resolve()
    directory = (profile_root / scope).resolve()
    if directory.parent != profile_root:
        raise DomainError("postlayout_profile_path_invalid", "The host-managed S14 profile identity is invalid.", 409)
    return directory


def close_context(context):
    if context is None:
        return
    for name in MANAGERS:
        manager = getattr(context, name, None)
        if manager is not None and hasattr(manager, "close"):
            manager.close()
    view = getattr(context, "workspace_view_dir", None)
    view_root = getattr(context, "workspace_view_root", None)
    if view is not None and view_root is not None:
        # Only disposable views created beneath this runtime's managed view root.
        if view.resolve().is_relative_to(view_root.resolve()) and view.name.startswith("view-"):
            shutil.rmtree(view)


def build_context(store, configurations, postlayout_profile_path=None, postlayout_working_directory=None):
    from .server import (GenerationManager, GenerationBatchManager, WorkflowManager, ImplementationSpecManager,
                         GlobalGenerationManager, GlobalWorkflowManager, PhysicalWorkflowManager,
                         DrcWorkflowManager, LvsWorkflowManager, PostLayoutWorkflowManager)
    from .repair_analysis import RepairAnalysisManager
    compiler, synthesizer, physical, drc, lvs, postlayout = configurations
    context = SimpleNamespace(store=store)
    try:
        context.generation = GenerationManager(store, compiler)
        context.workflow = WorkflowManager(store, context.generation, compiler, synthesizer)
        context.generation_batches = GenerationBatchManager(store, context.generation, context.workflow)
        context.repair_analysis = RepairAnalysisManager(store, context.generation, context.workflow, context.generation_batches)
        context.generation_batches.repair_analysis = context.repair_analysis
        context.implementation_specs = ImplementationSpecManager(store, context.generation, context.workflow)
        context.global_generation = GlobalGenerationManager(store, context.generation, context.workflow,
                                                            context.implementation_specs, compiler)
        context.global_workflow = GlobalWorkflowManager(store, context.generation, context.implementation_specs,
                                                        context.global_generation, compiler, synthesizer)
        context.physical_workflow = PhysicalWorkflowManager(store, context.global_generation,
                                                            context.global_workflow, physical)
        context.drc_workflow = DrcWorkflowManager(store, context.physical_workflow, drc)
        context.lvs_workflow = LvsWorkflowManager(store, context.drc_workflow, lvs)
        context.postlayout_workflow = PostLayoutWorkflowManager(
            store, context.lvs_workflow, postlayout,
            compiler_configuration=compiler,
            configuration_path=postlayout_profile_path,
            profile_working_directory=postlayout_working_directory)
    except Exception:
        close_context(context)
        raise
    return context


class WorkspaceRuntime:
    def __init__(self, server, registry, configurations):
        from .folder_picker import FolderPickerManager
        self.server, self.registry, self.configurations = server, registry, configurations
        self.folder_picker = FolderPickerManager(server.project_root)
        self.context = None
        self.identity = {"session_id": uuid.uuid4().hex, "project_id": None,
                         "system_id": None, "read_only": False}

    def catalog(self):
        result = self.registry.catalog()
        result["library"] = result.get("components", [])
        result["active"] = dict(self.identity)
        result["default_project_directory"] = str(self.registry.root / "projects")
        return result

    def require_session(self, handler, mutation=False):
        token = handler.headers.get("X-HuLLCirq-Session")
        if token is None:
            token = parse_qs(urlsplit(handler.path).query).get("session_id", [None])[0]
        if token != self.identity["session_id"]:
            raise DomainError("workspace_session_changed", "The active project or system changed. Your draft was preserved; reopen the intended system.", 409)
        if self.context is None:
            raise DomainError("no_system_open", "Open or create a project and system first.", 409)
        if mutation and self.identity["read_only"]:
            raise DomainError("read_only_system", "This preserved system is read-only. Duplicate its design to make an editable system.", 409)

    def require_management_session(self, handler):
        token = handler.headers.get("X-HuLLCirq-Session")
        if token is None:
            token = parse_qs(urlsplit(handler.path).query).get("session_id", [None])[0]
        if token != self.identity["session_id"]:
            raise DomainError("workspace_session_changed", "The workspace changed. Refresh the project list before continuing.", 409)

    def require_idle(self, handler):
        if self.context is not None:
            if self.identity["read_only"]:
                # Historical unresolved cleanup is evidence, not a live worker
                # in this execution-disabled saved viewing context.
                for name in MANAGERS:
                    worker = getattr(getattr(self.context, name, None), "_worker", None)
                    if worker is not None and worker.is_alive():
                        raise DomainError("workspace_busy", "Wait for the active worker before switching systems.", 409)
                return
            if self.context.repair_analysis.is_active():
                raise DomainError("repair_analysis_busy", "Finish or cancel repair guidance analysis before switching systems.", 409)
            handler._require_global_workflow_idle()
            handler._require_other_execution_idle()

    def open(self, project_id, system_id):
        resolved = self.registry.resolve_system(project_id, system_id)
        path = resolved["path"]
        if resolved["read_only"]:
            from .readonly_view import build_readonly_context
            expected_files = resolved["system"].get("origin", {}).get("files")
            candidate = build_readonly_context(path, self.configurations, expected_files)
            candidate.physical_repair_session = {"configured": False, "bundle_present": False, "error": None,
                                                 "read_only": True}
            candidate.lvs_repair_session = {"configured": False, "bundle_present": False, "error": None,
                                            "read_only": True}
        else:
            profile_directory = _postlayout_profile_directory(self.registry.root, project_id, system_id)
            from .physical_repair_session import load_repair_configurations
            store = ProjectStore(path)
            configurations, repair_status = load_repair_configurations(
                store, self.configurations, profile_directory, project_id, system_id)
            from .lvs_repair_session import load_repair_configuration
            configurations, lvs_repair_status = load_repair_configuration(
                store, configurations, profile_directory, project_id, system_id)
            candidate = build_context(
                store, configurations,
                postlayout_profile_path=profile_directory / "postlayout_runtime.json",
                postlayout_working_directory=profile_directory / "runs")
            candidate.physical_repair_session = repair_status
            candidate.lvs_repair_session = lvs_repair_status
        try:
            if hasattr(self.registry, "mark_recent"):
                self.registry.mark_recent(project_id, system_id)
        except Exception:
            close_context(candidate)
            raise
        # Prepare first: a corrupt requested store must not discard the old context.
        previous = self.context
        self.folder_picker.cancel_session(self.identity["session_id"])
        self.context = candidate
        for name in ("store", *MANAGERS):
            setattr(self.server, name, getattr(candidate, name))
        self.server.physical_repair_session = copy.deepcopy(candidate.physical_repair_session)
        self.server.lvs_repair_session = copy.deepcopy(candidate.lvs_repair_session)
        self.identity = {"session_id": uuid.uuid4().hex, "project_id": project_id,
                         "system_id": system_id, "read_only": bool(resolved["read_only"])}
        self.server.generation_previews.clear()
        close_context(previous)

    def close(self):
        self.folder_picker.cancel_session(self.identity["session_id"])
        previous, self.context = self.context, None
        for name in ("store", *MANAGERS):
            if hasattr(self.server, name):
                delattr(self.server, name)
        if hasattr(self.server, "physical_repair_session"):
            del self.server.physical_repair_session
        if hasattr(self.server, "lvs_repair_session"):
            del self.server.lvs_repair_session
        self.identity = {"session_id": uuid.uuid4().hex, "project_id": None,
                         "system_id": None, "read_only": False}
        self.server.generation_previews.clear()
        close_context(previous)

    def response(self):
        from .server import project_envelope
        return {"workspace": self.catalog(),
                "project": project_envelope(self.server) if self.context else None}

    def activate_result(self, result):
        project, system = result["project"], result.get("system")
        if system is None:
            system = project["systems"][0]
        self.open(project["id"], system["id"])


def make_workspace_server(host, port, registry, project_root=None, configurations=None,
                          local_runtime=None, ollama_path=None):
    from .server import HuLLCirqServer, RequestHandler
    if host not in ("127.0.0.1", "localhost"):
        raise DomainError("unsupported_bind", "HuLLCirq serves only the loopback interface.")
    server = HuLLCirqServer((host, port), RequestHandler)
    server.project_root = Path(project_root).resolve() if project_root else Path(__file__).resolve().parents[2]
    server.generation_previews = {}
    server.preview_lock = threading.RLock()
    server.execution_lock = threading.RLock()
    server.context_lock = threading.RLock()
    server.workspace = WorkspaceRuntime(server, registry, configurations or (None,) * 6)
    if local_runtime is None:
        from .local_runtime import LocalRuntimeController
        local_runtime = LocalRuntimeController(server.project_root, ollama_path=ollama_path)
    server.local_runtime = local_runtime
    return server


def workspace_get(handler, path):
    runtime = handler.server.workspace
    if path == "/api/workspace":
        handler._json(runtime.catalog())
        return True
    if not path.startswith("/api/workspace/"):
        return False
    runtime.require_management_session(handler)
    parts = path[len("/api/workspace/"):].split("/")
    if parts == ["local-runtime"]:
        runtime.require_session(handler)
        handler._json({"runtime": handler.server.local_runtime.status()})
    elif len(parts) == 2 and parts[0] == "backup":
        runtime.require_idle(handler)
        handler._json(runtime.registry.backup_project(parts[1]), extra={"Content-Disposition": 'attachment; filename="hullcirq-project-backup.json"'})
    elif len(parts) == 2 and parts[0] == "evidence-export":
        runtime.require_idle(handler)
        from .portable_projects import export_project
        handler._json(export_project(runtime.registry, parts[1], handler.server.project_root),
                      extra={"Content-Disposition": 'attachment; filename="hullcirq-evidence.json"'})
    elif len(parts) == 2 and parts[0] == "evidence":
        from .portable_projects import inspect_project
        handler._json(inspect_project(runtime.registry, parts[1]))
    elif len(parts) == 3 and parts[0] == "evidence-file":
        from .portable_projects import artifact_bytes
        raw, entry = artifact_bytes(runtime.registry, parts[1], parts[2])
        policy = "default-src 'none'; sandbox; frame-ancestors 'self'; base-uri 'none'; form-action 'none'"
        handler._headers(200, "application/octet-stream", len(raw), {"Content-Disposition": f'attachment; filename="evidence-{parts[2]}.bin"'},
                         content_security_policy=policy)
        handler.wfile.write(raw)
    elif len(parts) == 3 and parts[0] == "evidence-map":
        from .portable_projects import map_view_bytes
        from .layout_role_view import functional_map_csp
        raw = map_view_bytes(runtime.registry, parts[1], parts[2])
        policy = functional_map_csp(raw) + "; sandbox allow-scripts"
        handler._headers(200, "text/html; charset=utf-8", len(raw),
                         {"Content-Disposition": 'inline; filename="archived-functional-map.html"'}, content_security_policy=policy)
        handler.wfile.write(raw)
    elif len(parts) == 2 and parts[0] == "folder-picker":
        handler._json({"picker": runtime.folder_picker.status(parts[1], runtime.identity["session_id"])})
    elif len(parts) == 2 and parts[0] == "stage":
        runtime.require_session(handler)
        if not hasattr(runtime.context, "stage_envelope"):
            raise DomainError("stage_view_unavailable", "Stage loading is available for saved read-only snapshots.", 409)
        result = runtime.context.stage_envelope(parts[1])
        result["workspace_identity"] = dict(runtime.identity)
        handler._json(result)
    elif len(parts) == 3 and parts[0] == "component":
        version = int(parts[2]) if parts[2].isdigit() else parts[2]
        handler._json(runtime.registry.component_package(parts[1], version), extra={"Content-Disposition": 'attachment; filename="hullcirq-component.json"'})
    else:
        raise DomainError("route_not_found", "Workspace route does not exist.", 404)
    return True


def workspace_post(handler, path, body):
    runtime, required = handler.server.workspace, handler._required
    runtime.require_management_session(handler)
    runtime.require_idle(handler)
    registry = runtime.registry
    active = runtime.identity
    if path in ("/api/workspace/local-runtime/start", "/api/workspace/local-runtime/stop"):
        runtime.require_session(handler, mutation=True)
        if body:
            raise DomainError("local_runtime_request_invalid", "Local server controls do not accept executable paths or commands.")
        from .local_runtime import LocalRuntimeController
        manager = handler.server.generation
        with manager.lock:
            profile = manager._require_profile()["profile"]
            if not LocalRuntimeController.supports_profile(profile):
                raise DomainError("local_runtime_profile_unsupported", "These controls manage prepared qwen3:8b or qwen2.5-coder:7b at localhost:11435/v1. Save a matching Local profile first.", 409)
        controller = handler.server.local_runtime
        operation = controller.start if path.endswith("/start") else controller.stop
        return {"runtime": operation(profile) if path.endswith("/start") else operation()}
    elif path == "/api/workspace/create-project":
        result = registry.create_project(required(body, "name"), body.get("system_name", "Main"), body.get("top_module", "top"),
                                         project_directory=body.get("project_directory") or None)
        runtime.activate_result(result)
    elif path == "/api/workspace/folder-picker":
        return {"picker": runtime.folder_picker.start(active["session_id"], body.get("initial_directory"))}
    elif path == "/api/workspace/cancel-folder-picker":
        return {"picker": runtime.folder_picker.cancel(required(body, "picker_id"), active["session_id"])}
    elif path == "/api/workspace/open-directory":
        runtime.activate_result(registry.register_project_directory(required(body, "directory")))
    elif path == "/api/workspace/open":
        defer_project_view = body.get("defer_project_view", False)
        if type(defer_project_view) is not bool:
            raise DomainError("invalid_defer_project_view", "defer_project_view must be a boolean.")
        runtime.open(required(body, "project_id"), required(body, "system_id"))
        if defer_project_view:
            # The browser reloads to tear down all old editors and pollers, then
            # obtains the full view through its newly scoped bootstrap request.
            return {"workspace": runtime.catalog(), "project_view_deferred": True}
    elif path == "/api/workspace/close":
        runtime.close()
    elif path == "/api/workspace/delete-project":
        project_id = required(body, "project_id")
        expected = required(body, "expected_project_revision")
        registry.validate_delete_project(project_id, expected)
        if active["project_id"] == project_id:
            # Workers were checked above. Release every manager before removing
            # its project from the active catalog; retained bytes never move.
            runtime.close()
        registry.delete_project(project_id, expected)
    elif path == "/api/workspace/restore-project":
        registry.restore_deleted_project(required(body, "trash_id"), required(body, "expected_project_revision"))
    elif path == "/api/workspace/create-system":
        result = registry.create_system(required(body, "project_id"), required(body, "name"), body.get("top_module", "top"))
        runtime.activate_result(result)
    elif path == "/api/workspace/rename-project":
        registry.rename_project(required(body, "project_id"), required(body, "name"))
    elif path == "/api/workspace/rename-system":
        registry.rename_system(required(body, "project_id"), required(body, "system_id"), required(body, "name"))
    elif path == "/api/workspace/duplicate-project":
        runtime.activate_result(registry.duplicate_project(required(body, "project_id"), required(body, "name")))
    elif path == "/api/workspace/duplicate-system":
        runtime.activate_result(registry.duplicate_system(required(body, "project_id"), required(body, "system_id"), required(body, "name")))
    elif path == "/api/workspace/array-variant":
        runtime.activate_result(registry.create_array_variant(required(body, "project_id"), required(body, "system_id"), required(body, "name")))
    elif path == "/api/workspace/restore":
        if "bundle_text" in body:
            source = body["bundle_text"]
            if type(source) is not str:
                raise DomainError("invalid_backup", "Backup source must be UTF-8 JSON text.")
            try:
                bundle = strict_loads(source)
            except (ValueError, RecursionError) as error:
                raise DomainError("invalid_backup", "Backup source is not valid JSON.") from error
        else:
            bundle = required(body, "bundle")
        runtime.activate_result(registry.restore_project(bundle, body.get("name")))
    elif path == "/api/workspace/restore-evidence":
        from .portable_projects import restore_project
        source = required(body, "bundle_text")
        if type(source) is not str:
            raise DomainError("portable_evidence_invalid", "Evidence package source must be UTF-8 JSON text.")
        try:
            bundle = strict_loads(source)
        except (ValueError, RecursionError) as error:
            raise DomainError("portable_evidence_invalid", "Evidence package source is not valid JSON.") from error
        runtime.activate_result(restore_project(registry, bundle, body.get("name")))
    elif path == "/api/workspace/publish-component":
        runtime.require_session(handler)
        registry.publish_component(active["project_id"], active["system_id"], body.get("node_ids"),
                                   body.get("name"), body.get("public_ports"), component_id=body.get("component_id"))
    elif path == "/api/workspace/import-component":
        if "package_text" in body:
            source = body["package_text"]
            if type(source) is not str:
                raise DomainError("invalid_component", "Component source must be UTF-8 JSON text.")
            try:
                package = strict_loads(source)
            except (ValueError, RecursionError) as error:
                raise DomainError("invalid_component", "Component source is not valid JSON.") from error
        else:
            package = required(body, "package")
        registry.import_component_package(package)
    elif path == "/api/workspace/instantiate":
        runtime.require_session(handler, mutation=True)
        version = required(body, "version")
        if type(version) is str and version.isdigit():
            version = int(version)
        registry.instantiate_component(active["project_id"], active["system_id"], required(body, "component_id"),
                                       version, required(body, "expected_revision_id"),
                                       body.get("instance_name", "Component"))
        registry.refresh_project_manifest(active["project_id"])
        # A data-layer save was made through a separate ProjectStore instance.
        runtime.open(active["project_id"], active["system_id"])
    else:
        raise DomainError("route_not_found", "Workspace route does not exist.", 404)
    return runtime.response()

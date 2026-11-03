"""Loopback design/generation API and narrowly scoped GUI/branding file serving."""

from __future__ import annotations

import copy
import gzip
import hashlib
import json
import mimetypes
import re
import socket
import sys
import threading
from contextlib import nullcontext
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from .execution_submissions import PROTOCOL_VERSION as EXECUTION_SUBMISSION_VERSION, run_submission, submission_view, validate_submission_id
from .domain import DomainError, validate_shape
from .store import ProjectStore, strict_loads
from .review_actor import VERSION as REVIEW_ACTOR_VERSION
from .generation import GenerationManager
from .generation_batches import GenerationBatchManager
from .repair_analysis import RepairAnalysisManager
from .workflow import WorkflowManager
from .implementation_specs import ImplementationSpecManager
from .global_generation import GlobalGenerationManager
from .global_workflow import GlobalWorkflowManager
from .physical_workflow import PhysicalWorkflowManager
from .drc_workflow import DrcWorkflowManager, FILE_IDS as DRC_FILE_IDS
from .lvs_workflow import LvsWorkflowManager, FILE_IDS as LVS_FILE_IDS
from .postlayout_workflow import PostLayoutWorkflowManager, FILE_IDS as POSTLAYOUT_FILE_IDS
from .envelope_cache import envelope_read_scope, read_scope
from .layout_role_view import (FILE_IDS as FUNCTIONAL_MAP_FILE_IDS, functional_map_bytes, functional_map_csp,
                               functional_map_metadata, snapshot_selected_run, verify_registration)

MAX_BODY_BYTES = 2 * 1024 * 1024
JSON_GZIP_MIN_BYTES = 64 * 1024


def _accepts_gzip(values) -> bool:
    """Negotiate gzip conservatively, retaining explicit exclusions over '*'."""
    qualities = {"gzip": [], "*": []}
    for value in values:
        for item in value.split(","):
            coding, *parameters = [part.strip() for part in item.split(";")]
            coding = coding.lower()
            if coding not in qualities:
                continue
            quality = 1.0
            if parameters:
                name, separator, raw = parameters[0].partition("=")
                if (len(parameters) != 1 or name.strip().lower() != "q" or not separator
                        or not re.fullmatch(r"(?:0(?:\.[0-9]{0,3})?|1(?:\.0{0,3})?)", raw.strip())):
                    quality = 0.0
                else:
                    quality = float(raw.strip())
            qualities[coding].append(quality)
    selected = qualities["gzip"] or qualities["*"]
    # Conflicting duplicate entries must not override an explicit q=0.
    return bool(selected) and min(selected) > 0


class HuLLCirqServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = sys.platform != "win32"

    def server_bind(self):
        # Windows SO_REUSEADDR can let an older GUI keep serving the same port.
        # Exclusivity makes a duplicate start fail instead of mixing versions.
        if sys.platform == "win32":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def server_close(self):
        maps = getattr(self, "functional_map_generation", None)
        if maps is not None:
            maps.close()
        if getattr(self, "workspace", None) is not None:
            self.workspace.folder_picker.close()
            self.workspace.close()
        if hasattr(self, "postlayout_workflow"):
            self.postlayout_workflow.close()
        if hasattr(self, "lvs_workflow"):
            self.lvs_workflow.close()
        if hasattr(self, "drc_workflow"):
            self.drc_workflow.close()
        if hasattr(self, "physical_workflow"):
            self.physical_workflow.close()
        if hasattr(self, "global_workflow"):
            self.global_workflow.close()
        if hasattr(self, "global_generation"):
            self.global_generation.close()
        if hasattr(self, "repair_analysis"):
            self.repair_analysis.close()
        if hasattr(self, "generation_batches"):
            self.generation_batches.close()
        if hasattr(self, "workflow"):
            self.workflow.close()
        if hasattr(self, "generation"):
            self.generation.close()
        runtime = getattr(self, "local_runtime", None)
        if runtime is not None:
            self.local_runtime = None
            runtime.close()
        super().server_close()


def make_server(host: str, port: int, store: ProjectStore, project_root: str | Path | None = None, compiler: dict | None = None, synthesizer: dict | None = None, physical_configuration: dict | None = None, drc_configuration: dict | None = None, lvs_configuration: dict | None = None, postlayout_configuration: dict | None = None) -> HuLLCirqServer:
    """Construct without starting, allowing isolated tests with port=0."""
    if host not in ("127.0.0.1", "localhost"):
        raise DomainError("unsupported_bind", "M1 serves only the loopback interface.")
    root = Path(project_root).resolve() if project_root else Path(__file__).resolve().parents[2]
    server = HuLLCirqServer((host, port), RequestHandler)
    server.store = store
    server.project_root = root
    # Only successful request previews are cached, in memory, for lossless downloads.
    # These are not durable generation records and never start a model request.
    server.generation_previews = {}
    server.preview_lock = threading.RLock()
    server.execution_lock = threading.RLock()
    # Derived presentation jobs are not circuit stages or project-store records.
    # Construct lazily; ordinary map GETs remain read-only and legacy-compatible.
    server.functional_map_generation = None
    try:
        server.generation = GenerationManager(store, compiler)
        server.workflow = WorkflowManager(store, server.generation, compiler, synthesizer)
        server.generation_batches = GenerationBatchManager(store, server.generation, server.workflow)
        server.repair_analysis = RepairAnalysisManager(store, server.generation, server.workflow, server.generation_batches)
        server.generation_batches.repair_analysis = server.repair_analysis
        server.implementation_specs = ImplementationSpecManager(store, server.generation, server.workflow)
        server.global_generation = GlobalGenerationManager(store, server.generation, server.workflow, server.implementation_specs, compiler)
        server.global_workflow = GlobalWorkflowManager(store, server.generation, server.implementation_specs,
                                                       server.global_generation, compiler, synthesizer)
        server.physical_workflow = PhysicalWorkflowManager(store, server.global_generation,
                                                           server.global_workflow, physical_configuration)
        server.drc_workflow = DrcWorkflowManager(store, server.physical_workflow, drc_configuration)
        server.lvs_workflow = LvsWorkflowManager(store, server.drc_workflow, lvs_configuration)
        server.postlayout_workflow = PostLayoutWorkflowManager(
            store, server.lvs_workflow, postlayout_configuration,
            compiler_configuration=compiler)
    except Exception:
        if hasattr(server, "generation"):
            server.generation.close()
        server.server_close()
        raise
    return server


def _functional_map_scope(server):
    workspace = getattr(server, "workspace", None)
    if workspace is not None:
        return {key: workspace.identity.get(key) for key in ("project_id", "system_id")}
    identity = hashlib.sha256(str(server.store.path.resolve()).encode("utf-8")).hexdigest()
    return {"project_id": "standalone-" + identity, "system_id": "standalone"}


def _functional_map_service(server):
    with server.execution_lock:
        if getattr(server, "functional_map_generation", None) is None:
            from .layout_map_generation import FunctionalMapGeneration
            from .verification import object_hash
            from .layout_role_view import _raw_record_projection

            def recheck(record, scope):
                with getattr(server, "context_lock", server.execution_lock):
                    if _functional_map_scope(server) != scope:
                        return False
                    with server.physical_workflow.lock:
                        current, display = snapshot_selected_run(server.physical_workflow, record["id"])
                        return (not display["historical"] and
                                object_hash(_raw_record_projection(current)) == object_hash(_raw_record_projection(record)))

            server.functional_map_generation = FunctionalMapGeneration(
                server.project_root, verify=verify_registration, recheck=recheck)
        return server.functional_map_generation


def _functional_map_generation_state(server, record, display):
    from .layout_map_source import eligibility
    result = _functional_map_service(server).status(record, _functional_map_scope(server))
    supported = eligibility(record)
    workspace = getattr(server, "workspace", None)
    reason = None
    if workspace is not None and workspace.identity.get("read_only"):
        reason = "This preserved system is read-only. Existing maps remain inspectable."
    elif display["historical"]:
        reason = "Select the latest Current, Passed and Accepted S11 result before generating a map."
    elif not supported["supported"]:
        detail = supported.get("reason")
        reason = detail.get("message") if type(detail) is dict else detail
        reason = reason or "This saved source format is not supported for map generation."
    elif _functional_map_service(server).is_active():
        reason = "A Functional Map generation is active. Refresh its saved status; do not resend."
    if reason is None:
        for name in ("postlayout_workflow", "lvs_workflow", "drc_workflow", "physical_workflow",
                     "global_workflow", "global_generation", "workflow", "generation", "repair_analysis", "generation_batches"):
            manager = getattr(server, name, None)
            worker = getattr(manager, "_worker", None)
            if manager is not None and ((hasattr(manager, "is_active") and manager.is_active()) or
                                        (worker is not None and worker.is_alive())):
                reason = "Wait for active project, model and tool work to finish."
                break
    return {**result, "run_id": record["id"], "can_generate": reason is None,
            "registered": result.get("registration") is not None,
            "blocked_reason": reason, "scope": "derived_read_only_presentation_not_circuit_execution"}


def execution_routes(server):
    return {"generation/start": server.generation, "generation/batches/start": server.generation_batches,
            "repair-analysis/start": server.repair_analysis, "workflow/start": server.workflow,
            "workflow/batches/start": server.workflow, "global-generation/start": server.global_generation,
            "global-workflow/runs": server.global_workflow, "physical-workflow/runs": server.physical_workflow,
            "drc-workflow/runs": server.drc_workflow, "lvs-workflow/runs": server.lvs_workflow,
            "postlayout-workflow/runs": server.postlayout_workflow}


def execution_configuration_fingerprint(owner):
    configuration = {name: getattr(owner, name, None) for name in ("compiler", "synthesizer", "tool_configuration")}
    return hashlib.sha256(json.dumps(configuration, sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def execution_submission_metadata(server):
    receipts, configurations = {}, {}
    for route, owner in execution_routes(server).items():
        configurations[route] = execution_configuration_fingerprint(owner)
        if route == "generation/start":
            receipts[route] = {}  # S04 retains its separately versioned I16 ledger.
        elif type(getattr(owner, "_committed", None)) is dict:
            receipts[route] = {key: value for key, value in submission_view(owner).items() if value["route"] == route}
        else:
            receipts[route] = {}
    return {"execution_submission_protocol_version": EXECUTION_SUBMISSION_VERSION,
            "execution_submission_receipts": receipts, "execution_configuration_fingerprints": configurations}


@envelope_read_scope
def project_envelope(server) -> dict:
    workspace = getattr(server, "workspace", None)
    context = workspace.context if workspace is not None else None
    if context is not None and hasattr(context, "saved_envelope"):
        result = context.saved_envelope()
        result["workspace_identity"] = dict(workspace.identity)
        result["physical_repair_session"] = copy.deepcopy(getattr(context, "physical_repair_session",
            {"configured": False, "bundle_present": False, "error": None}))
        result["lvs_repair_session"] = copy.deepcopy(getattr(context, "lvs_repair_session",
            {"configured": False, "bundle_present": False, "error": None}))
        result["lvs_repair_preparation"] = {"available": False, "eligible": False, "source": None,
            "blocked_reason": "This preserved system is read-only.", "profile_version": "hullcirq-sky130-lvs-v3"}
        return result
    result = server.store.envelope()
    result["review_operator_version"] = REVIEW_ACTOR_VERSION
    result.update(execution_submission_metadata(server))
    extension = server.generation.envelope()
    result.update(extension)
    if hasattr(server, "generation_batches"):
        result.update(server.generation_batches.envelope())
    if getattr(server, "repair_analysis", None) is not None:
        result.update(server.repair_analysis.envelope())
    generation = extension["generation"]
    latest = generation["jobs"][-1] if generation["jobs"] else None
    local_stage = next(stage for stage in result["workflow"] if stage["id"] == "local_rtl_generation")
    local_stage.update(implemented=True, execution_status=latest["execution_status"] if latest else "Not Run",
                       validation_status=latest.get("effective_validation_status", latest["validation_status"]) if latest else "Not Checked",
                       review_status="Accepted" if generation["all_nodes_accepted"] else "Awaiting Review",
                       freshness=latest["freshness"] if latest else "Current", latest_job_id=latest["id"] if latest else None,
                       accepted_node_count=sum(bool(node["accepted_job_id"]) and node["accepted_job_id"] == node["latest_job_id"] for node in generation["nodes"]),
                       required_node_count=len(generation["nodes"]))
    tools = server.workflow.envelope()
    result.update(tools)
    for stage_id in ("local_synthesis", "local_netlist_simulation"):
        records = [run for run in tools["workflow_runs"] if run["stage_id"] == stage_id]
        latest_run = records[-1] if records else None
        node_states = [node for node in tools["workflow_nodes"] if node["stage_id"] == stage_id]
        accepted_count = sum(bool(node["accepted_run_id"]) for node in node_states)
        stage = next(entry for entry in result["workflow"] if entry["id"] == stage_id)
        stage.update(implemented=True, node_scope=True, execution_status=latest_run["execution_status"] if latest_run else "Not Run",
                     validation_status=latest_run["validation_status"] if latest_run else "Not Checked",
                     review_status="Accepted" if node_states and accepted_count == len(node_states) else "Awaiting Review",
                     freshness=latest_run["freshness"] if latest_run else "Current", latest_run_id=latest_run["id"] if latest_run else None,
                     accepted_node_count=accepted_count, required_node_count=len(node_states),
                     all_nodes_accepted=bool(node_states) and accepted_count == len(node_states))
    specifications = server.implementation_specs.envelope()
    result.update(specifications)
    records, node_states = specifications["implementation_specs"], specifications["implementation_spec_nodes"]
    latest_spec = records[-1] if records else None
    accepted_count = sum(bool(node["accepted_spec_id"]) for node in node_states)
    spec_stage = next(entry for entry in result["workflow"] if entry["id"] == "node_implementation_specs")
    spec_stage.update(implemented=True, node_scope=True, execution_status=latest_spec["execution_status"] if latest_spec else "Not Run",
                      validation_status=latest_spec["validation_status"] if latest_spec else "Not Checked",
                      review_status="Accepted" if node_states and accepted_count == len(node_states) else "Awaiting Review",
                      freshness=latest_spec["freshness"] if latest_spec else "Current", latest_spec_id=latest_spec["id"] if latest_spec else None,
                      accepted_node_count=accepted_count, required_node_count=len(node_states),
                      all_nodes_accepted=bool(node_states) and accepted_count == len(node_states))
    probe = extension["llm"]["probe"]
    global_data = server.global_generation.envelope()
    result.update(global_data)
    global_jobs = global_data["global_generation"]["jobs"]
    global_latest = global_jobs[-1] if global_jobs else None
    global_stage = next(stage for stage in result["workflow"] if stage["id"] == "global_rtl_generation")
    global_stage.update(implemented=True, execution_status=global_latest["execution_status"] if global_latest else "Not Run",
                        validation_status=global_latest["validation_status"] if global_latest else "Not Checked",
                        review_status=global_latest["review_status"] if global_latest else "Awaiting Review",
                        freshness=global_latest["freshness"] if global_latest else "Current",
                        latest_job_id=global_latest["id"] if global_latest else None,
                        ready=global_data["global_generation"]["ready"],
                        blocked_reason=global_data["global_generation"]["blocked_reason"])
    global_tools = server.global_workflow.envelope()
    result.update(global_tools)
    for stage_id in ("global_synthesis", "global_netlist_simulation"):
        records = [run for run in global_tools["global_workflow"]["runs"] if run["stage_id"] == stage_id]
        latest_run = records[-1] if records else None
        status = next(entry for entry in global_tools["global_workflow"]["stages"] if entry["stage_id"] == stage_id)
        stage = next(entry for entry in result["workflow"] if entry["id"] == stage_id)
        stage.update(implemented=True, execution_status=latest_run["execution_status"] if latest_run else "Not Run",
                     validation_status=latest_run["validation_status"] if latest_run else "Not Checked",
                     review_status="Accepted" if status["accepted_run_id"] else "Awaiting Review",
                     freshness=latest_run["freshness"] if latest_run else "Current",
                     latest_run_id=status["latest_run_id"], accepted_run_id=status["accepted_run_id"])
    physical_data = server.physical_workflow.envelope()
    result.update(physical_data)
    physical = physical_data["physical_workflow"]
    layout_latest = next((run for run in reversed(physical["runs"]) if run["stage_id"] == "layout"), None)
    layout_stage = next(stage for stage in result["workflow"] if stage["id"] == "layout")
    layout_stage.update(implemented=True, execution_status=layout_latest["execution_status"] if layout_latest else "Not Run",
                        validation_status=layout_latest["validation_status"] if layout_latest else "Not Checked",
                        review_status="Accepted" if physical["accepted_run_id"] else "Awaiting Review",
                        freshness=layout_latest["freshness"] if layout_latest else "Current",
                        latest_run_id=physical["latest_run_id"], accepted_run_id=physical["accepted_run_id"])
    drc_data = server.drc_workflow.envelope()
    result.update(drc_data)
    drc = drc_data["drc_workflow"]
    drc_latest = drc["runs"][-1] if drc["runs"] else None
    drc_stage = next(stage for stage in result["workflow"] if stage["id"] == "drc")
    drc_stage.update(implemented=True, execution_status=drc_latest["execution_status"] if drc_latest else "Not Run",
                     validation_status=drc_latest["validation_status"] if drc_latest else "Not Checked",
                     review_status="Accepted" if drc["accepted_run_id"] else "Awaiting Review",
                     freshness=drc_latest["freshness"] if drc_latest else "Current",
                     latest_run_id=drc["latest_run_id"], accepted_run_id=drc["accepted_run_id"])
    lvs_data = server.lvs_workflow.envelope()
    result.update(lvs_data)
    lvs = lvs_data["lvs_workflow"]
    lvs_latest = lvs["runs"][-1] if lvs["runs"] else None
    lvs_stage = next(stage for stage in result["workflow"] if stage["id"] == "lvs")
    lvs_stage.update(implemented=True, execution_status=lvs_latest["execution_status"] if lvs_latest else "Not Run",
                     validation_status=lvs_latest["validation_status"] if lvs_latest else "Not Checked",
                     review_status="Accepted" if lvs["accepted_run_id"] else "Awaiting Review",
                     freshness=lvs_latest["freshness"] if lvs_latest else "Current",
                     latest_run_id=lvs["latest_run_id"], accepted_run_id=lvs["accepted_run_id"])
    postlayout_data = server.postlayout_workflow.envelope()
    result.update(postlayout_data)
    postlayout = postlayout_data["postlayout_workflow"]
    postlayout_latest = postlayout["runs"][-1] if postlayout["runs"] else None
    postlayout_stage = next(stage for stage in result["workflow"] if stage["id"] == "post_layout_verification")
    postlayout_stage.update(implemented=True, execution_status=postlayout_latest["execution_status"] if postlayout_latest else "Not Run",
                     validation_status=postlayout_latest["validation_status"] if postlayout_latest else "Not Checked",
                     review_status="Accepted" if postlayout["accepted_run_id"] else "Awaiting Review",
                     freshness=postlayout_latest["freshness"] if postlayout_latest else "Current",
                     latest_run_id=postlayout["latest_run_id"], accepted_run_id=postlayout["accepted_run_id"])
    result["implementation"].update(milestone="M2-J", scope="node_global_functional_verification_routed_layout_drc_lvs_and_postlayout_preflight",
                                     llm_connected=bool(probe and probe.get("status") in ("Connected", "connected")),
                                     rtl_generated=any(job["execution_status"] == "Completed" and job["rtl"] for job in generation["jobs"]),
                                     eda_executed=any(run.get("checks", {}).get("executed") is True for run in
                                                      tools["workflow_runs"] + global_tools["global_workflow"]["runs"] + physical["runs"] + drc["runs"] + lvs["runs"] + postlayout["runs"]),
                                     postlayout_executed=any(run.get("checks", {}).get("executed") is True for run in postlayout["runs"]),
                                     dynamic_postlayout_supported=postlayout.get("verification_supported") is True
                                         and postlayout.get("execution_scope") != "post_route_functional_plus_sta",
                                     postlayout_verification_supported=postlayout.get("verification_supported") is True,
                                     postlayout_execution_scope=postlayout.get("execution_scope"),
                                     lvs_executed=any(run.get("checks", {}).get("checks", {}).get("lvs", {}).get("executed") is True for run in lvs["runs"]),
                                     drc_executed=any(run.get("checks", {}).get("checks", {}).get("drc", {}).get("executed") is True for run in drc["runs"]),
                                     layout_executed=any(run.get("checks", {}).get("checks", {}).get("routing", {}).get("executed") is True for run in physical["runs"]),
                                     pdk_used=any(run.get("checks", {}).get("technology_mapping_executed") is True for run in physical["runs"]))
    if getattr(server, "workspace", None) is not None:
        result["workspace_identity"] = dict(server.workspace.identity)
    result["physical_repair_session"] = copy.deepcopy(getattr(server, "physical_repair_session",
        {"configured": False, "bundle_present": False, "error": None}))
    result["lvs_repair_session"] = copy.deepcopy(getattr(server, "lvs_repair_session",
        {"configured": False, "bundle_present": False, "error": None}))
    from .lvs_repair_session import eligibility
    result["lvs_repair_preparation"] = eligibility(server)
    return result


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "HuLLCirq/0.1"

    def _headers(self, status: int, content_type: str, length: int, extra: dict | None = None, content_security_policy: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", content_security_policy or "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        if extra:
            for name, value in extra.items():
                self.send_header(name, value)
        self.end_headers()

    def _json(self, value: dict, status: int = 200, extra: dict | None = None) -> None:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        response_headers = dict(extra or {})
        vary_keys = [key for key in response_headers if key.lower() == "vary"]
        vary = [token.strip() for key in vary_keys for token in response_headers.pop(key).split(",") if token.strip()]
        if not any(token.lower() in ("accept-encoding", "*") for token in vary):
            vary.append("Accept-Encoding")
        response_headers["Vary"] = ", ".join(vary)
        # Download bytes and raw file routes retain their original contracts.
        # Only negotiated large API JSON uses transparent transport compression.
        download = any(key.lower() == "content-disposition" for key in response_headers)
        encoded_already = any(key.lower() == "content-encoding" for key in response_headers)
        if (not download and not encoded_already and len(encoded) >= JSON_GZIP_MIN_BYTES
                and _accepts_gzip(self.headers.get_all("Accept-Encoding", []))):
            encoded = gzip.compress(encoded, compresslevel=1, mtime=0)
            response_headers["Content-Encoding"] = "gzip"
        self._headers(status, "application/json; charset=utf-8", len(encoded), response_headers)
        self.wfile.write(encoded)

    def _error(self, error: DomainError) -> None:
        details = {"code": error.code, "message": error.message}
        if getattr(error, "generation_start_rejected_before_creation", False) is True:
            details.update(generation_start_rejected_before_creation=True, submission_id=error.submission_id)
        if getattr(error, "execution_start_rejected_before_creation", False) is True:
            details.update(execution_start_rejected_before_creation=True, submission_id=error.submission_id)
        self._json({"error": details}, error.status)

    def _check_host(self) -> str:
        port = self.server.server_address[1]
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if port == 80:
            allowed |= {"127.0.0.1", "localhost"}
        host = self.headers.get("Host", "").lower()
        if host not in allowed:
            raise DomainError("invalid_host", "Use this server's localhost address.", 403)
        return host

    def _read_body(self) -> dict:
        host = self._check_host()
        origin = self.headers.get("Origin")
        if origin is not None and origin.lower() != f"http://{host}":
            raise DomainError("invalid_origin", "Cross-origin project mutations are not allowed.", 403)
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            raise DomainError("invalid_origin", "Cross-site project mutations are not allowed.", 403)
        if self.headers.get("Transfer-Encoding") is not None:
            raise DomainError("invalid_request", "Chunked request bodies are not supported.")
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise DomainError("invalid_content_type", "Use application/json for project mutations.", 415)
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise DomainError("invalid_request", "Invalid request body length.") from error
        limit = 128 * 1024 * 1024 if urlsplit(self.path).path.startswith("/api/workspace/") else MAX_BODY_BYTES
        if not 0 < length <= limit:
            raise DomainError("body_limit", f"Request body must be between 1 byte and {limit // (1024 * 1024)} MiB.", 413)
        self.connection.settimeout(10)
        raw = self.rfile.read(length)
        self._body_consumed = True
        if len(raw) != length:
            raise DomainError("invalid_request", "Request body ended prematurely.")
        try:
            value = strict_loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError, RecursionError) as error:
            raise DomainError("invalid_json", "Request must contain valid UTF-8 JSON.") from error
        if type(value) is not dict:
            raise DomainError("invalid_request", "Request body must be a JSON object.")
        return value

    def _discard_rejected_body(self) -> None:
        """Drain a small denied request so Windows can deliver its error reply.

        Closing a TCP socket with unread inbound bytes can reset the connection
        before a client receives the 403. This does not parse denied input or
        permit chunked/oversized uploads, and waits only briefly for missing data.
        """
        if self._body_consumed or self.headers.get("Transfer-Encoding") is not None:
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return
        if not 0 < length <= MAX_BODY_BYTES:
            return
        previous_timeout = self.connection.gettimeout()
        try:
            self.connection.settimeout(0.5)
            self.rfile.read(length)
            self._body_consumed = True
        except (OSError, TimeoutError):
            pass
        finally:
            self.connection.settimeout(previous_timeout)

    @staticmethod
    def _required(body: dict, name: str):
        if name not in body:
            raise DomainError("invalid_request", f"{name} is required.")
        return body[name]

    def _require_global_workflow_idle(self):
        maps = getattr(self.server, "functional_map_generation", None)
        if maps is not None and maps.is_active():
            raise DomainError("functional_map_generation_busy", "Wait for Functional Map generation to finish; it starts no EDA.", 409)
        if self.server.postlayout_workflow.is_active():
            raise DomainError("postlayout_workflow_busy", "Finish or cancel post-layout verification before starting another execution.", 409)
        if self.server.lvs_workflow.is_active():
            raise DomainError("lvs_workflow_busy", "Finish or cancel LVS execution before starting another execution.", 409)
        if self.server.drc_workflow.is_active():
            raise DomainError("drc_workflow_busy", "Finish or cancel DRC execution before starting another execution.", 409)
        if self.server.physical_workflow.is_active():
            raise DomainError("physical_workflow_busy", "Finish or cancel layout execution before starting another execution.", 409)
        if self.server.global_workflow.is_active():
            raise DomainError("global_workflow_busy", "Finish or cancel the whole-system tool run before starting another execution.", 409)

    def _require_other_execution_idle(self):
        active = {"Queued", "Running"}
        self._require_generation_batch_idle()
        if self.server.global_generation.is_active():
            raise DomainError("competing_execution_busy", "Finish or cancel global generation before whole-system tool execution.", 409)
        if self.server.workflow.is_active():
            raise DomainError("competing_execution_busy", "Finish or cancel node execution or the synthesis batch before another execution.", 409)
        for manager, key in ((self.server.generation, "jobs"), (self.server.workflow, "runs")):
            with manager.lock:
                worker = manager._worker
                if (worker and worker.is_alive()) or any(record["execution_status"] in active for record in manager._state[key]):
                    raise DomainError("competing_execution_busy", "Finish or cancel node execution before whole-system tool execution.", 409)

    def _execution_start(self, manager, route, body, create, preflight=None, project=True):
        def checked_preflight():
            if body.get("submission_id") is not None and body.get("submission_configuration_fingerprint") != execution_configuration_fingerprint(manager):
                raise DomainError("submission_configuration_conflict", "Execution configuration changed; prepare a new request from the current profile.", 409)
            if preflight is not None:
                preflight()
        started = run_submission(manager, route, body, create, checked_preflight)
        if not project:
            return started
        result = project_envelope(self.server)
        if "execution_submission" in started:
            result["execution_submission"] = started["execution_submission"]
        return result

    def _require_generation_batch_idle(self):
        if getattr(self.server, "repair_analysis", None) is not None and self.server.repair_analysis.is_active():
            raise DomainError("repair_analysis_busy", "Finish or cancel repair analysis before another execution or project operation.", 409)
        if getattr(self.server, "generation_batches", None) is not None and self.server.generation_batches.is_active():
            raise DomainError("generation_batch_busy", "Finish or cancel sequential node generation before another execution or project operation.", 409)

    def do_POST(self) -> None:
        with getattr(self.server, "context_lock", self.server.execution_lock):
            self._do_POST()

    def _do_POST(self) -> None:
        self._body_consumed = False
        try:
            path = urlsplit(self.path).path
            body = self._read_body()
            maps = getattr(self.server, "functional_map_generation", None)
            if maps is not None and maps.is_active():
                raise DomainError("functional_map_generation_busy", "Functional Map generation is active. Refresh saved status without resending; project data is unchanged.", 409)
            if getattr(self.server, "workspace", None) is not None:
                from .workspace_server import workspace_post
                if path.startswith("/api/workspace/"):
                    self._json(workspace_post(self, path, body))
                    return
                self.server.workspace.require_session(self, mutation=True)
            store = self.server.store
            if path in ("/api/save", "/api/import"):
                design = self._required(body, "design")
                if getattr(self.server, "workspace", None) is not None:
                    active = self.server.workspace.identity
                    if type(design) is not dict:
                        raise DomainError("invalid_shape", "Design must be a JSON object.")
                    validate_shape(design)
                    if path == "/api/import":
                        import copy
                        design = copy.deepcopy(design)
                        design["imported_design_identity"] = {"project": design.get("project"), "system": design.get("system"),
                                                               "scope": "Imported design input only; no results or adoption transferred."}
                        design["project"] = copy.deepcopy(store.envelope()["design"]["project"])
                        design["system"] = copy.deepcopy(store.envelope()["design"]["system"])
                    elif (design.get("project", {}).get("id") != active["project_id"]
                          or design.get("system", {}).get("id") != active["system_id"]):
                        raise DomainError("workspace_identity_mismatch", "Save belongs to another project or system. Reopen the intended system first.", 409)
                result = store.save(design, self._required(body, "expected_revision_id"))
                if getattr(self.server, "workspace", None) is not None:
                    self.server.workspace.registry.refresh_project_manifest(active["project_id"])
                self.server.generation.observe_design()
                result = project_envelope(self.server)
            elif path == "/api/validate":
                store.validate(self._required(body, "stage_id"), self._required(body, "revision_id"))
                self.server.generation.apply_review_policy()
                result = project_envelope(self.server)
            elif path == "/api/review-policy":
                store.set_review_policy(self._required(body, "mode"), self._required(body, "user_authorized"),
                                        body.get("note", ""), body.get("expected_policy_id"))
                self.server.generation.apply_review_policy()
                result = project_envelope(self.server)
            elif path == "/api/review":
                result = store.review(self._required(body, "run_id"), self._required(body, "decision"),
                                      self._required(body, "note"), body.get("target_stage"), operator=body.get("review_operator"))
                result = project_envelope(self.server)
            elif path == "/api/llm/profile":
                self.server.generation.save_profile(self._required(body, "profile"), self._required(body, "expected_profile_revision_id"))
                result = project_envelope(self.server)
            elif path == "/api/llm/probe":
                with self.server.execution_lock, self.server.global_generation.lock:
                    self._require_generation_batch_idle()
                    self._require_global_workflow_idle()
                    if self.server.workflow.is_active():
                        raise DomainError("workflow_busy", "Finish or cancel node synthesis before a provider probe.", 409)
                    if self.server.global_generation.is_active():
                        raise DomainError("global_generation_busy", "Finish or cancel global generation before a provider probe.", 409)
                    self.server.generation.probe(self._required(body, "profile_revision_id"))
                result = project_envelope(self.server)
            elif path == "/api/global-generation/context":
                from .physical_recovery import validate_instruction
                validate_instruction(self.server, body, 'global_rtl')
                result = self.server.global_generation.preview(self._required(body, "revision_id"),
                    body.get("operation", "generate"), body.get("base_job_id"), body.get("instruction", ""))
            elif path == "/api/global-generation/start":
                with self.server.execution_lock:
                    def preflight():
                        from .physical_recovery import validate_instruction
                        validate_instruction(self.server, body, 'global_rtl')
                        self._require_generation_batch_idle()
                        self._require_global_workflow_idle()
                        if self.server.workflow.is_active():
                            raise DomainError("workflow_busy", "Finish or cancel node synthesis before global generation.", 409)
                    result = self._execution_start(self.server.global_generation, 'global-generation/start', body,
                        lambda ticket: self.server.global_generation.start(self._required(body, "revision_id"), self._required(body, "context_id"),
                            self._required(body, "profile_revision_id"), body.get("operation", "generate"), body.get("base_job_id"), body.get("instruction", ""),
                            **({"_submission": ticket} if ticket else {})), preflight)
            elif path == "/api/global-generation/cancel":
                self.server.global_generation.cancel(self._required(body, "job_id"))
                result = project_envelope(self.server)
            elif path == "/api/global-generation/review":
                self.server.global_generation.review(self._required(body, "job_id"), self._required(body, "decision"),
                    self._required(body, "note"), body.get("target_stage"), operator=body.get("review_operator"))
                result = project_envelope(self.server)
            elif path == "/api/repair-analysis/preview":
                result = self.server.repair_analysis.preview(self._required(body, "run_id"))
            elif path == "/api/repair-analysis/start":
                with self.server.execution_lock:
                    def preflight():
                        known = any(job["request_id"] == body.get("request_id") for job in self.server.repair_analysis._state["jobs"])
                        if not known:
                            self._require_global_workflow_idle()
                            self._require_other_execution_idle()
                    result = self._execution_start(self.server.repair_analysis, 'repair-analysis/start', body,
                        lambda ticket: self.server.repair_analysis.start(self._required(body, "context_id"), self._required(body, "request_id"),
                            **({"_submission": ticket} if ticket else {})), preflight, project=False)
                self._json(result, 202)
                return
            elif path == "/api/repair-analysis/cancel":
                result = self.server.repair_analysis.cancel(self._required(body, "job_id"))
            elif path == "/api/generation/batches/preview":
                args = (self._required(body, "revision_id"), body.get("mode", "generate"), body.get("node_ids"), body.get("instruction", ""), body.get("retry_batch_id"))
                options = {key: body[key] for key in ("analysis_job_ids", "node_instructions") if key in body}
                result = self.server.generation_batches.preview(*args, **options)
            elif path == "/api/generation/batches/start":
                with self.server.execution_lock:
                    def preflight():
                        known = any(batch["request_id"] == body.get("request_id") for batch in self.server.generation_batches._state["batches"])
                        if not known:
                            self._require_global_workflow_idle()
                            self._require_other_execution_idle()
                    result = self._execution_start(self.server.generation_batches, 'generation/batches/start', body,
                        lambda ticket: self.server.generation_batches.start(self._required(body, "plan_id"), self._required(body, "request_id"),
                            **({"_submission": ticket} if ticket else {})), preflight)
                self._json(result, 202)
                return
            elif path.startswith("/api/generation/batches/"):
                parts = path[len("/api/generation/batches/"):].split("/")
                if len(parts) != 2 or not parts[0] or parts[1] != "cancel":
                    raise DomainError("route_not_found", "API route does not exist.", 404)
                self.server.generation_batches.cancel(parts[0])
                result = project_envelope(self.server)
            elif path == "/api/generation/context":
                from .physical_recovery import validate_instruction
                validate_instruction(self.server, body, 'node_rtl')
                result = self.server.generation.preview(self._required(body, "node_id"), self._required(body, "revision_id"),
                                                        body.get("operation", "generate"), body.get("base_job_id"), body.get("instruction", ""),
                                                        body.get("retry_of_job_id"))
                with self.server.preview_lock:
                    self.server.generation_previews.pop(result["context_id"], None)
                    self.server.generation_previews[result["context_id"]] = result
                    while len(self.server.generation_previews) > 16:
                        del self.server.generation_previews[next(iter(self.server.generation_previews))]
            elif path == "/api/generation/start":
                with self.server.execution_lock, self.server.global_generation.lock:
                    def preflight():
                        from .physical_recovery import validate_instruction
                        validate_instruction(self.server, body, 'node_rtl')
                        self._require_generation_batch_idle()
                        self._require_global_workflow_idle()
                        if self.server.workflow.is_active():
                            raise DomainError("workflow_busy", "Finish or cancel node synthesis before RTL generation.", 409)
                        if self.server.global_generation.is_active():
                            raise DomainError("global_generation_busy", "Finish or cancel the global model request before node generation.", 409)
                    # Preserve legacy unkeyed admission/error priority. Keyed
                    # submissions resolve their durable receipt before preflight.
                    legacy_start = body.get("submission_id") is None
                    if legacy_start:
                        preflight()
                    started = self.server.generation.start(self._required(body, "node_id"), self._required(body, "revision_id"),
                                              self._required(body, "context_id"), self._required(body, "profile_revision_id"),
                                              body.get("operation", "generate"), body.get("base_job_id"), body.get("instruction", ""),
                                              body.get("retry_of_job_id"), submission_id=body.get("submission_id"), _preflight=None if legacy_start else preflight)
                result = project_envelope(self.server)
                result["generation_submission"] = started["generation_submission"]
                receipt = started["generation_submission"]
                if receipt["submission_id"] is not None:
                    result["execution_submission"] = {"version": EXECUTION_SUBMISSION_VERSION, "submission_id": receipt["submission_id"],
                        "record_id": receipt["job_id"], "replayed": receipt["replayed"], "route": 'generation/start'}
                self._json(result, 202)
                return
            elif path == "/api/generation/cancel":
                self.server.generation.cancel(self._required(body, "job_id"))
                result = project_envelope(self.server)
            elif path == "/api/generation/verify":
                with self.server.execution_lock:
                    self._require_global_workflow_idle()
                    self._require_other_execution_idle()
                    self.server.generation.verify_saved(self._required(body, "job_id"), self._required(body, "revision_id"))
                self._json(project_envelope(self.server), 202)
                return
            elif path == "/api/generation/review":
                self.server.generation.review(self._required(body, "job_id"), self._required(body, "decision"),
                                             self._required(body, "note"), body.get("target_stage"), operator=body.get("review_operator"))
                result = project_envelope(self.server)
            elif path == "/api/workflow/start":
                with self.server.execution_lock:
                    def preflight():
                        self._require_global_workflow_idle()
                        self._require_other_execution_idle()
                    result = self._execution_start(self.server.workflow, 'workflow/start', body,
                        lambda ticket: self.server.workflow.start(self._required(body, "stage_id"), self._required(body, "node_id"),
                            self._required(body, "candidate_id"), self._required(body, "revision_id"), **({"_submission": ticket} if ticket else {})), preflight)
                self._json(result, 202)
                return
            elif path == "/api/workflow/batches/start":
                with self.server.execution_lock:
                    def preflight():
                        self._require_generation_batch_idle()
                        self._require_global_workflow_idle()
                        if self.server.global_generation.is_active():
                            raise DomainError("competing_execution_busy", "Finish or cancel global generation before an all-node workflow batch.", 409)
                        with self.server.generation.lock:
                            worker = self.server.generation._worker
                            if (worker and worker.is_alive()) or any(job["execution_status"] in {"Queued", "Running"} for job in self.server.generation._state["jobs"]):
                                raise DomainError("competing_execution_busy", "Finish or cancel RTL generation before an all-node workflow batch.", 409)
                    def create(ticket):
                        options = {"stage_id": body["stage_id"]} if "stage_id" in body else {}
                        if ticket is not None:
                            options["_submission"] = ticket
                        return self.server.workflow.start_batch(self._required(body, "revision_id"), self._required(body, "request_id"), **options)
                    result = self._execution_start(self.server.workflow, 'workflow/batches/start', body, create, preflight)
                self._json(result, 202)
                return
            elif path.startswith("/api/workflow/batches/"):
                parts = path[len("/api/workflow/batches/"):].split("/")
                if len(parts) != 2 or not parts[0] or parts[1] != "cancel":
                    raise DomainError("route_not_found", "API route does not exist.", 404)
                self.server.workflow.cancel_batch(parts[0])
                result = project_envelope(self.server)
            elif path == "/api/global-workflow/runs":
                with self.server.execution_lock:
                    def preflight():
                        self._require_global_workflow_idle()
                        self._require_other_execution_idle()
                    result = self._execution_start(self.server.global_workflow, 'global-workflow/runs', body,
                        lambda ticket: self.server.global_workflow.start(self._required(body, "stage"), self._required(body, "global_job_id"), body.get("synthesis_run_id"), body.get("revision_id"), **({"_submission": ticket} if ticket else {})), preflight)
                self._json(result, 202)
                return
            elif path.startswith("/api/global-workflow/runs/"):
                parts = path[len("/api/global-workflow/runs/"):].split("/")
                if len(parts) != 2 or not parts[0]:
                    raise DomainError("route_not_found", "API route does not exist.", 404)
                identifier, action = parts
                if action == "cancel":
                    self.server.global_workflow.cancel(identifier)
                elif action == "review":
                    self.server.global_workflow.review(identifier, self._required(body, "decision"),
                        self._required(body, "note"), body.get("target_stage"), operator=body.get("review_operator"))
                else:
                    raise DomainError("route_not_found", "API route does not exist.", 404)
                result = project_envelope(self.server)
            elif path == "/api/physical-workflow/repair-profile":
                if type(body) is not dict or set(body) != {"failed_layout_id", "revision_id"}:
                    raise DomainError("physical_repair_request_invalid",
                                      "The next fixed physical correction accepts only the failed S11 ID and current saved revision ID.", 400)
                with self.server.execution_lock:
                    self._require_global_workflow_idle()
                    self._require_other_execution_idle()
                    from .physical_repair_session import prepare_retry
                    prepare_retry(self.server, body["failed_layout_id"], body["revision_id"])
                result = project_envelope(self.server)
            elif path == "/api/physical-workflow/runs":
                with self.server.execution_lock:
                    def preflight():
                        self._require_global_workflow_idle()
                        self._require_other_execution_idle()
                    result = self._execution_start(self.server.physical_workflow, 'physical-workflow/runs', body,
                        lambda ticket: self.server.physical_workflow.start(self._required(body, "stage"), self._required(body, "global_job_id"), self._required(body, "synthesis_run_id"), self._required(body, "netlist_run_id"), body.get("revision_id"), **({"_submission": ticket} if ticket else {})), preflight)
                self._json(result, 202)
                return
            elif path == "/api/drc-workflow/runs":
                with self.server.execution_lock:
                    def preflight():
                        self._require_global_workflow_idle()
                        self._require_other_execution_idle()
                    result = self._execution_start(self.server.drc_workflow, 'drc-workflow/runs', body,
                        lambda ticket: self.server.drc_workflow.start(self._required(body, "stage"), self._required(body, "layout_run_id"), body.get("revision_id"), **({"_submission": ticket} if ticket else {})), preflight)
                self._json(result, 202)
                return
            elif path == "/api/physical-recovery/history":
                from .physical_recovery import history
                if type(body) is not dict or set(body) != {'stage'}:
                    raise DomainError('physical_recovery_invalid', 'Select an S11–S14 stage.', 400)
                result = history(self.server, body['stage'])
            elif path == "/api/physical-recovery/prepare":
                from .physical_recovery import prepare
                required = {'stage', 'run_id', 'revision_id', 'target', 'node_id', 'feedback'}
                if type(body) is not dict or set(body) != required:
                    raise DomainError('physical_recovery_invalid', 'Provide the exact diagnostic source and explicit repair target.', 400)
                with self.server.execution_lock:
                    self._require_global_workflow_idle()
                    self._require_other_execution_idle()
                    result = prepare(self.server, **body)
            elif path == "/api/physical-recovery/open":
                from .physical_recovery import validate
                if type(body) is not dict or set(body) != {'id'}:
                    raise DomainError('physical_recovery_invalid', 'Select the saved handoff identifier.', 400)
                with self.server.execution_lock:
                    self._require_global_workflow_idle()
                    self._require_other_execution_idle()
                    result = validate(self.server, body['id'])
            elif path == "/api/lvs-workflow/repair-profile":
                required = {"layout_run_id", "drc_run_id", "source_lvs_run_id", "revision_id"}
                if type(body) is not dict or set(body) != required:
                    raise DomainError("lvs_repair_request_invalid",
                                      "Corrected extraction preparation accepts only exact saved source IDs and the current revision.", 400)
                with self.server.execution_lock:
                    self._require_global_workflow_idle()
                    self._require_other_execution_idle()
                    from .lvs_repair_session import prepare_repair
                    prepare_repair(self.server, body["layout_run_id"], body["drc_run_id"], body["source_lvs_run_id"], body["revision_id"])
                result = project_envelope(self.server)
            elif path == "/api/postlayout-workflow/physical-repair-profile":
                if type(body) is not dict or set(body) != {"failed_s14_id", "revision_id"}:
                    raise DomainError("physical_repair_request_invalid",
                                      "Fixed physical correction accepts only the failed S14 ID and current saved revision ID.", 400)
                with self.server.execution_lock:
                    self._require_global_workflow_idle()
                    self._require_other_execution_idle()
                    from .physical_repair_session import prepare_repair
                    prepare_repair(self.server, body["failed_s14_id"], body["revision_id"])
                result = project_envelope(self.server)
            elif path == "/api/postlayout-workflow/adapter-contract":
                required = {"layout_run_id", "drc_run_id", "lvs_run_id", "revision_id", "contract"}
                if type(body) is not dict or set(body) != required:
                    raise DomainError("postlayout_adapter_request_invalid",
                                      "S14 adapter metadata accepts only the exact saved source IDs, revision and verification contract.", 400)
                with self.server.execution_lock:
                    self._require_global_workflow_idle()
                    self._require_other_execution_idle()
                    self.server.postlayout_workflow.save_adapter_contract(
                        body["layout_run_id"], body["drc_run_id"], body["lvs_run_id"], body["revision_id"], body["contract"])
                result = project_envelope(self.server)
            elif path == "/api/postlayout-workflow/profile":
                required = {"layout_run_id", "drc_run_id", "lvs_run_id", "revision_id"}
                if type(body) is not dict or set(body) != required:
                    raise DomainError("postlayout_profile_request_invalid",
                                      "S14 profile preparation accepts only the current saved revision and exact S11/S12/S13 IDs.", 400)
                with self.server.execution_lock:
                    self._require_global_workflow_idle()
                    self._require_other_execution_idle()
                    self.server.postlayout_workflow.prepare_profile(
                        body["layout_run_id"], body["drc_run_id"], body["lvs_run_id"], body["revision_id"])
                result = project_envelope(self.server)
            elif path == "/api/postlayout-workflow/runs":
                with self.server.execution_lock:
                    def preflight():
                        self._require_global_workflow_idle()
                        self._require_other_execution_idle()
                    result = self._execution_start(self.server.postlayout_workflow, 'postlayout-workflow/runs', body,
                        lambda ticket: self.server.postlayout_workflow.start(self._required(body, "stage"), self._required(body, "layout_run_id"), self._required(body, "drc_run_id"), self._required(body, "lvs_run_id"), body.get("revision_id"), **({"_submission": ticket} if ticket else {})), preflight)
                self._json(result, 202)
                return
            elif path.startswith("/api/postlayout-workflow/runs/"):
                parts = path[len("/api/postlayout-workflow/runs/"):].split("/")
                if len(parts) != 2 or not parts[0]:
                    raise DomainError("route_not_found", "API route does not exist.", 404)
                identifier, action = parts
                if action == "cancel":
                    self.server.postlayout_workflow.cancel(identifier)
                elif action == "verify-termination":
                    if type(body) is not dict or body:
                        raise DomainError("postlayout_cleanup_request_invalid", "Saved termination verification accepts no paths, commands or parameters.", 400)
                    with self.server.execution_lock:
                        self._require_generation_batch_idle()
                        for name in ("lvs_workflow", "drc_workflow", "physical_workflow", "global_workflow", "global_generation", "workflow", "repair_analysis"):
                            if getattr(self.server, name).is_active():
                                raise DomainError("competing_execution_busy", "Wait for other model and tool execution before inspecting saved S14 termination.", 409)
                        for manager, field in ((self.server.generation, "jobs"), (self.server.workflow, "runs")):
                            with manager.lock:
                                if (manager._worker and manager._worker.is_alive()) or any(r["execution_status"] in ("Queued", "Running") for r in manager._state[field]):
                                    raise DomainError("competing_execution_busy", "Wait for actual model and tool workers before inspecting saved S14 termination.", 409)
                        self.server.postlayout_workflow.verify_saved_termination(identifier)
                elif action == "review":
                    self.server.postlayout_workflow.review(identifier, self._required(body, "decision"), self._required(body, "note"), body.get("target_stage"), operator=body.get("review_operator"))
                else:
                    raise DomainError("route_not_found", "API route does not exist.", 404)
                result = project_envelope(self.server)
            elif path == "/api/lvs-workflow/runs":
                with self.server.execution_lock:
                    def preflight():
                        self._require_global_workflow_idle()
                        self._require_other_execution_idle()
                    result = self._execution_start(self.server.lvs_workflow, 'lvs-workflow/runs', body,
                        lambda ticket: self.server.lvs_workflow.start(self._required(body, "stage"), self._required(body, "layout_run_id"), self._required(body, "drc_run_id"), body.get("revision_id"), **({"_submission": ticket} if ticket else {})), preflight)
                self._json(result, 202)
                return
            elif path.startswith("/api/lvs-workflow/runs/"):
                parts = path[len("/api/lvs-workflow/runs/"):].split("/")
                if len(parts) != 2 or not parts[0]:
                    raise DomainError("route_not_found", "API route does not exist.", 404)
                identifier, action = parts
                if action == "cancel":
                    self.server.lvs_workflow.cancel(identifier)
                elif action == "review":
                    self.server.lvs_workflow.review(identifier, self._required(body, "decision"), self._required(body, "note"), body.get("target_stage"), operator=body.get("review_operator"))
                else:
                    raise DomainError("route_not_found", "API route does not exist.", 404)
                result = project_envelope(self.server)
            elif path.startswith("/api/drc-workflow/runs/"):
                parts = path[len("/api/drc-workflow/runs/"):].split("/")
                if len(parts) != 2 or not parts[0]:
                    raise DomainError("route_not_found", "API route does not exist.", 404)
                identifier, action = parts
                if action == "cancel":
                    self.server.drc_workflow.cancel(identifier)
                elif action == "review":
                    self.server.drc_workflow.review(identifier, self._required(body, "decision"), self._required(body, "note"), body.get("target_stage"), operator=body.get("review_operator"))
                else:
                    raise DomainError("route_not_found", "API route does not exist.", 404)
                result = project_envelope(self.server)
            elif path.startswith("/api/physical-workflow/runs/"):
                parts = path[len("/api/physical-workflow/runs/"):].split("/")
                if len(parts) != 2 or not parts[0]:
                    raise DomainError("route_not_found", "API route does not exist.", 404)
                identifier, action = parts
                if action == "functional-map-generation":
                    if type(body) is not dict or set(body) != {"revision_id", "record_hash"}:
                        raise DomainError("functional_map_request_invalid", "Require only the selected revision and physical record hash.", 400)
                    with self.server.execution_lock:
                        with self.server.physical_workflow.lock:
                            selected, display = snapshot_selected_run(self.server.physical_workflow, identifier)
                        state = _functional_map_generation_state(self.server, selected, display)
                        if body["revision_id"] != selected["revision_id"]:
                            raise DomainError("functional_map_source_changed", "The selected physical revision changed. Refresh saved status.", 409)
                        if not state["can_generate"]:
                            raise DomainError("functional_map_generation_blocked", state["blocked_reason"], 409)
                        self._require_global_workflow_idle()
                        self._require_other_execution_idle()
                        _functional_map_service(self.server).start(selected, body["record_hash"], _functional_map_scope(self.server))
                        result = _functional_map_generation_state(self.server, selected, display)
                    self._json(result, 202)
                    return
                elif action == "cancel":
                    self.server.physical_workflow.cancel(identifier)
                elif action == "revalidate":
                    with self.server.execution_lock:
                        self._require_global_workflow_idle()
                        self._require_other_execution_idle()
                        self.server.physical_workflow.revalidate(identifier)
                    self._json(project_envelope(self.server), 202)
                    return
                elif action == "review":
                    self.server.physical_workflow.review(identifier, self._required(body, "decision"),
                        self._required(body, "note"), body.get("target_stage"), operator=body.get("review_operator"))
                else:
                    raise DomainError("route_not_found", "API route does not exist.", 404)
                result = project_envelope(self.server)
            elif path == "/api/workflow/cancel":
                self.server.workflow.cancel(self._required(body, "run_id"))
                result = project_envelope(self.server)
            elif path == "/api/workflow/review":
                self.server.workflow.review(self._required(body, "run_id"), self._required(body, "decision"),
                                            self._required(body, "note"), body.get("target_stage"), operator=body.get("review_operator"))
                result = project_envelope(self.server)
            elif path == "/api/implementation-specs/start":
                self.server.implementation_specs.start(self._required(body, "node_id"), self._required(body, "revision_id"), body.get("source_run_id"))
                result = project_envelope(self.server)
            elif path == "/api/implementation-specs/review":
                self.server.implementation_specs.review(self._required(body, "spec_id"), self._required(body, "decision"),
                                                        self._required(body, "note"), body.get("target_stage"), operator=body.get("review_operator"))
                result = project_envelope(self.server)
            else:
                raise DomainError("route_not_found", "API route does not exist.", 404)
            self._json(result)
        except DomainError as error:
            self._discard_rejected_body()
            self._error(error)
        except (ConnectionError, TimeoutError):
            self.close_connection = True
        except OSError:
            self._error(DomainError("storage_error", "Cannot persist project state; no success was recorded.", 500))
        except Exception as error:
            self.log_error("Unhandled API error: %s", type(error).__name__)
            self._error(DomainError("internal_error", "The request could not be completed.", 500))

    def do_GET(self) -> None:
        # Cache repeated manager views only during this read response. Starting
        # or cancelling a job never shares this cache with a mutation request.
        from .observation import readonly_observation_scope
        # Static startup HTML/assets do not inspect an active project. Keep
        # them responsive while a project API is waiting for source locks.
        # Decode exactly as _do_GET does so encoded API paths retain all guards.
        if unquote(urlsplit(self.path).path).startswith("/api/"):
            with getattr(self.server, "context_lock", nullcontext()), read_scope(), readonly_observation_scope():
                self._do_GET()
        else:
            self._do_GET()

    def _do_GET(self) -> None:
        try:
            self._check_host()
            path = unquote(urlsplit(self.path).path)
            if getattr(self.server, "workspace", None) is not None and path.startswith("/api/"):
                from .workspace_server import workspace_get
                if workspace_get(self, path):
                    return
                self.server.workspace.require_session(self)
            if path.startswith('/api/inspection/waveform/'):
                from .inspection import waveform
                parts = path[len('/api/inspection/waveform/'):].split('/')
                if len(parts) != 2:
                    raise DomainError('inspection_unavailable', 'Select one saved execution.', 400)
                self._json(waveform(self.server, *parts))
                return
            if path == '/api/inspection/files':
                from .inspection import catalog
                self._json(catalog(self.server)[0])
                return
            if path.startswith('/api/inspection/files/'):
                from .inspection import file_content
                query = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
                if set(query)-{'session_id', 'page', 'sha256'} or any(len(values) != 1 for values in query.values()):
                    raise DomainError('inspection_unavailable', 'Choose one saved file page and whole-file checksum.', 400)
                page = query.get('page', ['0'])[0]
                if not page.isascii() or not page.isdecimal() or len(page) > 9:
                    raise DomainError('inspection_unavailable', 'Page must be a non-negative integer.', 400)
                self._json(file_content(self.server, path[len('/api/inspection/files/'):],
                                        page=int(page), sha256=query.get('sha256', [None])[0]))
                return
            if path.startswith("/api/artifacts/"):
                parts = path[len("/api/artifacts/"):].split("/")
                if len(parts) != 3 or not parts[1] or any(character in parts[1] for character in ("\\", "\x00")):
                    raise DomainError("artifact_not_found", "The requested JSON artifact does not exist.", 404)
                kind, identifier, artifact = parts
                if (kind, artifact) == ("generation", "context"):
                    value = self.server.generation.job(identifier).get("context")
                elif (kind, artifact) == ("workflow", "verification-plan"):
                    value = self.server.workflow.run(identifier).get("verification_plan")
                elif (kind, artifact) == ("implementation-specs", "specification"):
                    value = self.server.implementation_specs.spec(identifier).get("specification")
                elif (kind, artifact) == ("generation-preview", "context"):
                    with self.server.preview_lock:
                        value = self.server.generation_previews.get(identifier)
                    if value is None:
                        raise DomainError("preview_not_found", "This preview is no longer available. Use Context Preview again.", 404)
                elif kind == "global-generation" and artifact in ("context", "source-manifest", "verification-plan"):
                    job = self.server.global_generation.job(identifier)
                    value = job["context"] if artifact == "context" else job["context"][
                        "source_manifest" if artifact == "source-manifest" else "verification_plan"]
                elif (kind, artifact) == ("global-preview", "context"):
                    value = self.server.global_generation.preview_artifact(identifier)
                elif kind == "global-workflow":
                    value = self.server.global_workflow.artifact(identifier, artifact)
                elif kind == "physical-workflow":
                    if artifact in FUNCTIONAL_MAP_FILE_IDS:
                        versions = parse_qs(urlsplit(self.path).query, keep_blank_values=True).get("map_generation", [])
                        if len(versions) > 1 or (versions and not versions[0]):
                            raise DomainError("functional_map_generation_integrity_error", "Select one immutable Functional Map publication.", 409)
                        with self.server.physical_workflow.lock:
                            selected, _ = snapshot_selected_run(self.server.physical_workflow, identifier)
                            encoded, mime, disposition, filename = functional_map_bytes(
                                self.server.project_root, selected, artifact, generation_id=versions[0] if versions else None)
                        policy = functional_map_csp(encoded) if artifact == "functional-map-html" else None
                        self._headers(200, mime, len(encoded), {"Content-Disposition": f'{disposition}; filename="{filename}"'}, content_security_policy=policy)
                        self.wfile.write(encoded)
                        return
                    if artifact in ("def", "gds", "png"):
                        encoded, mime = self.server.physical_workflow.artifact_bytes(identifier, artifact)
                        disposition = "inline" if artifact == "png" else "attachment"
                        self._headers(200, mime, len(encoded), {"Content-Disposition": f'{disposition}; filename="layout.{artifact}"'})
                        self.wfile.write(encoded)
                        return
                    value = self.server.physical_workflow.artifact(identifier, artifact)
                elif kind == "drc-workflow":
                    if artifact in DRC_FILE_IDS:
                        encoded, mime = self.server.drc_workflow.artifact_bytes(identifier, artifact)
                        self._headers(200, mime, len(encoded), {"Content-Disposition": f'attachment; filename="drc-{artifact}"'})
                        self.wfile.write(encoded)
                        return
                    value = self.server.drc_workflow.artifact(identifier, artifact)
                elif kind == "postlayout-workflow":
                    if artifact in POSTLAYOUT_FILE_IDS:
                        encoded, mime = self.server.postlayout_workflow.artifact_bytes(identifier, artifact)
                        self._headers(200, mime, len(encoded), {"Content-Disposition": f'attachment; filename="postlayout-{artifact}"'})
                        self.wfile.write(encoded)
                        return
                    value = self.server.postlayout_workflow.artifact(identifier, artifact)
                elif kind == "lvs-workflow":
                    if artifact in LVS_FILE_IDS:
                        encoded, mime = self.server.lvs_workflow.artifact_bytes(identifier, artifact)
                        self._headers(200, mime, len(encoded), {"Content-Disposition": f'attachment; filename="lvs-{artifact}"'})
                        self.wfile.write(encoded)
                        return
                    value = self.server.lvs_workflow.artifact(identifier, artifact)
                else:
                    raise DomainError("artifact_not_found", "The requested JSON artifact does not exist.", 404)
                if value is None:
                    raise DomainError("artifact_not_found", "No saved JSON artifact was produced for this record.", 404)
                self._json(value, extra={"Content-Disposition": f'attachment; filename="{artifact}.json"'})
                return
            if path in ("/api/project", "/api/bootstrap"):
                self._json(project_envelope(self.server))
                return
            if path == "/api/global-generation":
                self._json(self.server.global_generation.envelope())
                return
            if path == "/api/global-workflow":
                self._json(self.server.global_workflow.envelope())
                return
            if path == "/api/physical-workflow":
                self._json(self.server.physical_workflow.envelope())
                return
            if path == "/api/drc-workflow":
                self._json(self.server.drc_workflow.envelope())
                return
            if path == "/api/postlayout-workflow":
                self._json(self.server.postlayout_workflow.envelope())
                return
            if path.startswith("/api/postlayout-workflow/runs/"):
                self._json(self.server.postlayout_workflow.run(path[len("/api/postlayout-workflow/runs/") :]))
                return
            if path == "/api/lvs-workflow":
                self._json(self.server.lvs_workflow.envelope())
                return
            if path.startswith("/api/lvs-workflow/runs/"):
                self._json(self.server.lvs_workflow.run(path[len("/api/lvs-workflow/runs/") :]))
                return
            if path.startswith("/api/drc-workflow/runs/"):
                self._json(self.server.drc_workflow.run(path[len("/api/drc-workflow/runs/"):]))
                return
            if path.startswith("/api/physical-workflow/runs/"):
                parts = path[len("/api/physical-workflow/runs/"):].split("/")
                if len(parts) == 2 and parts[1] == "block-placement" and parts[0] and not any(c in parts[0] for c in ("\\", "\x00")):
                    self._json(self.server.physical_workflow.block_placement(parts[0]))
                    return
                if len(parts) == 2 and parts[1] == "functional-map-generation" and parts[0] and not any(c in parts[0] for c in ("\\", "\x00")):
                    with self.server.execution_lock:
                        with self.server.physical_workflow.lock:
                            selected, display = snapshot_selected_run(self.server.physical_workflow, parts[0])
                        value = _functional_map_generation_state(self.server, selected, display)
                    self._json(value)
                    return
                if len(parts) == 2 and parts[1] == "functional-map" and parts[0] and not any(c in parts[0] for c in ("\\", "\x00")):
                    versions = parse_qs(urlsplit(self.path).query, keep_blank_values=True).get("map_generation", [])
                    if len(versions) > 1 or (versions and not versions[0]):
                        raise DomainError("functional_map_generation_integrity_error", "Select one immutable Functional Map publication.", 409)
                    with self.server.physical_workflow.lock:
                        selected, display = snapshot_selected_run(self.server.physical_workflow, parts[0])
                        value = functional_map_metadata(self.server.project_root, selected, display,
                                                        generation_id=versions[0] if versions else None)
                    self._json(value)
                    return
                self._json(self.server.physical_workflow.run(path[len("/api/physical-workflow/runs/"):]))
                return
            if path.startswith("/api/global-workflow/runs/"):
                identifier = path[len("/api/global-workflow/runs/"):]
                if not identifier or any(c in identifier for c in ("/", "\\", "\x00")):
                    raise DomainError("route_not_found", "API route does not exist.", 404)
                self._json(self.server.global_workflow.run(identifier))
                return
            if path.startswith("/api/global-generation/jobs/"):
                self._json(self.server.global_generation.job(path[len("/api/global-generation/jobs/"):]))
                return
            if path == "/api/llm":
                self._json(self.server.generation.envelope()["llm"])
                return
            if path == "/api/execution-submissions":
                query = parse_qs(urlsplit(self.path).query)
                route, key = query.get("route", [None])[0], query.get("submission_id", [None])[0]
                validate_submission_id(key)
                owner = execution_routes(self.server).get(route)
                if owner is None:
                    raise DomainError("invalid_submission_route", "This route does not start a supported model/native execution.")
                if getattr(getattr(self.server, "workspace", None), "identity", {}).get("read_only"):
                    self._json({"version": EXECUTION_SUBMISSION_VERSION, "submission_id": key, "route": route, "status": "read_only"})
                elif route == "generation/start":
                    self._json(owner.submission_receipt(key))
                else:
                    receipt = submission_view(owner).get(key)
                    self._json({"version": EXECUTION_SUBMISSION_VERSION, "submission_id": key, "route": route,
                        "status": "not_found" if receipt is None else "rejected" if receipt["rejection"] else "started",
                        **(receipt if receipt is not None else {"record_id": None, "rejection": None})})
                return
            if path.startswith("/api/generation/submissions/"):
                self._json(self.server.generation.submission_receipt(path[len("/api/generation/submissions/"):]))
                return
            if path.startswith("/api/generation/jobs/"):
                self._json(self.server.generation.job(path[len("/api/generation/jobs/"):]))
                return
            if path == "/api/repair-analysis":
                self._json(self.server.repair_analysis.envelope())
                return
            if path.startswith("/api/repair-analysis/jobs/"):
                self._json(self.server.repair_analysis.job(path[len("/api/repair-analysis/jobs/"):]))
                return
            if path == "/api/generation/batches":
                self._json(self.server.generation_batches.envelope())
                return
            if path.startswith("/api/generation/batches/plans/"):
                self._json(self.server.generation_batches.plan(path[len("/api/generation/batches/plans/"):]))
                return
            if path.startswith("/api/generation/batches/"):
                self._json(self.server.generation_batches.batch(path[len("/api/generation/batches/"):]))
                return
            if path == "/api/workflow":
                self._json(self.server.workflow.envelope())
                return
            if path.startswith("/api/workflow/batches/"):
                self._json(self.server.workflow.batch(path[len("/api/workflow/batches/"):]))
                return
            if path.startswith("/api/workflow/runs/"):
                self._json(self.server.workflow.run(path[len("/api/workflow/runs/"):]))
                return
            if path == "/api/implementation-specs":
                self._json(self.server.implementation_specs.envelope())
                return
            if path.startswith("/api/implementation-specs/"):
                self._json(self.server.implementation_specs.spec(path[len("/api/implementation-specs/"):]))
                return
            if path == "/api/export":
                self._json(self.server.store.envelope()["design"], extra={"Content-Disposition": 'attachment; filename="hullcirq-design.json"'})
                return
            if path.startswith("/api/snapshots/"):
                self._json(self.server.store.snapshot(path[len("/api/snapshots/"):]))
                return
            if path.startswith("/api/"):
                raise DomainError("route_not_found", "API route does not exist.", 404)
            if "\\" in path or "\x00" in path:
                raise DomainError("file_not_found", "File does not exist.", 404)
            if path.startswith("/assets/branding/"):
                allowed_root = self.server.project_root / "assets" / "branding"
                relative = path[len("/assets/branding/"):]
            else:
                allowed_root = self.server.project_root / "src" / "gui"
                relative = "index.html" if path in ("/", "/index.html") else path.lstrip("/")
                if relative.startswith("src/gui/"):
                    relative = relative[len("src/gui/"):]
            candidate = (allowed_root / relative).resolve()
            if not candidate.is_relative_to(allowed_root.resolve()) or not candidate.is_file():
                raise DomainError("file_not_found", "File does not exist.", 404)
            encoded = candidate.read_bytes()
            mime = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
            if candidate.suffix in (".html", ".css", ".js", ".json", ".svg"):
                mime += "; charset=utf-8"
            self._headers(200, mime, len(encoded))
            self.wfile.write(encoded)
        except DomainError as error:
            self._error(error)
        except (ConnectionError, TimeoutError):
            self.close_connection = True
        except OSError:
            self._error(DomainError("file_error", "The requested file could not be read.", 500))

    def do_OPTIONS(self) -> None:
        self._error(DomainError("cross_origin_not_supported", "Cross-origin API access is not supported.", 403))

    def log_message(self, format: str, *args) -> None:
        sys.stderr.write(f"[HuLLCirq] {format % args}\n")

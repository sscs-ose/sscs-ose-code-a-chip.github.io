"""CLI orchestration for the static Task / continuing Attempt kernel."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import tempfile
import threading
from contextlib import contextmanager
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import asdict, replace
from pathlib import Path
from typing import Mapping

from chip_nebula.adapters.pool_manager import AgentPoolManager
from chip_nebula.models.task_manifest import TaskContext, TaskManifest
from chip_nebula.project import get_chip_nebula_dir
from chip_nebula.taskgraph_run_controls import (
    terminate_recorded_run_process,
    timeout_control_path,
)

from .attempt_runtime import AttemptRuntime
from .attempt_workspace import AttemptWorkspaceFactory
from .attempt_scheduler import AttemptScheduler
from .domain import Artifact, WorkflowStatus
from .planner import TaskBriefPlanner
from .static_recipe import (
    CompiledStaticRecipe,
    StaticRecipeCompiler,
    load_static_recipe,
    load_static_role,
)
from .static_store import StateConflict, StaticTaskGraphStore
from .workspaces import capture_leaked_wip_state


def database_path(project_root: Path, explicit: str = "") -> Path:
    return (
        Path(explicit).expanduser().resolve()
        if explicit else
        get_chip_nebula_dir(project_root) / "shared" / "memory" / "taskgraph-v2.db"
    )


def load_compiled_recipe(
    recipe_path: Path, *, workflow_id: str, goal: str,
    parameters: Mapping[str, str], framework: str = "", model: str = "",
    reasoning_effort: str = "", baseline_commit: str = "", workers: int = 4,
) -> CompiledStaticRecipe:
    document = load_static_recipe(recipe_path.read_text(encoding="utf-8"))
    role_names = {
        str(raw["role"])
        for raw in document.get("tasks", {}).values()
        if isinstance(raw, Mapping) and raw.get("role")
    }
    config_root = Path(__file__).resolve().parent.parent / "configs"
    roles = {}
    for name in sorted(role_names):
        candidates = [
            recipe_path.parent.parent / "roles" / f"{name}.yaml",
            config_root / "roles" / f"{name}.yaml",
        ]
        role_path = next((path for path in candidates if path.is_file()), None)
        if role_path is None:
            raise FileNotFoundError(f"Role configuration not found: {name}")
        role = load_static_role(role_path.read_text(encoding="utf-8"))
        if framework or model:
            role = replace(
                role, framework=framework or role.framework,
                model=model or role.model,
            )
        roles[role.name] = role
    compiled = StaticRecipeCompiler(roles).compile(
        document, workflow_id=workflow_id, goal=goal, parameters=parameters,
    )
    if framework or model or reasoning_effort:
        compiled = replace(
            compiled,
            tasks=tuple(replace(
                task, framework=framework or task.framework,
                model=model or task.model,
                reasoning_effort=reasoning_effort or task.reasoning_effort,
            ) for task in compiled.tasks),
            planner=replace(
                compiled.planner,
                framework=framework or compiled.planner.framework,
                model=model or compiled.planner.model,
            ),
        )
    return replace(
        compiled,
        workflow=replace(compiled.workflow, metadata={
            "recipe_path": str(recipe_path.resolve()),
            "parameters": dict(parameters),
            "framework_override": framework,
            "model_override": model,
            "reasoning_effort_override": reasoning_effort,
            "baseline_commit": baseline_commit,
            "workers": workers,
        }),
    )


def create_workflow(
    project_root: Path, database: Path, compiled: CompiledStaticRecipe,
    pool: AgentPoolManager,
) -> None:
    initial = [
        import_initial_artifact(project_root, artifact_id)
        for artifact_id in compiled.parameter_artifacts.values()
    ]
    with StaticTaskGraphStore(database) as store:
        existing = store.get_workflow(compiled.workflow.id)
        if existing is None:
            store.create_workflow(
                compiled.workflow, compiled.roles, compiled.tasks, initial,
                compiled.joint_analysis_groups, compiled.feedback_routes,
            )
        elif (
            existing.status != WorkflowStatus.PLANNING
            or existing.definition_digest != compiled.workflow.definition_digest
            or json.dumps({task.id: asdict(task) for task in store.list_tasks(existing.id)}, sort_keys=True)
            != json.dumps({task.id: asdict(task) for task in compiled.tasks}, sort_keys=True)
            or any(store.get_role(role.name, role.version) != role for role in compiled.roles)
        ):
            raise StateConflict("planning resume must retain the exact original Tasks, Roles and Recipe")
        planner = TaskBriefPlanner(AdapterPlannerBackend(
            pool, project_root, workflow_id=compiled.workflow.id,
            inputs=tuple(initial),
        ))
        planner.plan_and_freeze(store, compiled)


def run_workflow(
    project_root: Path, database: Path, workflow_id: str,
    pool: AgentPoolManager, *, workers: int, framework: str = "", model: str = "",
    reasoning_effort: str = "",
) -> WorkflowStatus:
    with _runner_shutdown_signals():
        return _run_workflow_loop(
            project_root, database, workflow_id, pool, workers=workers,
            framework=framework, model=model, reasoning_effort=reasoning_effort,
        )


def prepare_workflow_resume(
    project_root: Path, database: Path, workflow_id: str,
    *, additional_attempts: int | None = None,
) -> tuple[str, ...]:
    """Recover dead owners before applying an explicit operator Resume.

    A runner can disappear while its Attempt is still recorded as running.
    Resume must first close that orphan and preserve its WIP; only then can the
    store see the exhausted/paused Task and replenish its attempt budget.
    Doing these operations in the opposite order can make the first Resume a
    no-op and force the operator to click Resume twice.
    """
    with StaticTaskGraphStore(database) as store:
        recovered = _recover_orphaned_attempts(store, workflow_id, project_root)
        store.resume_workflow(
            workflow_id, additional_attempts=additional_attempts,
        )
    return recovered


def cancel_workflow_attempts(
    project_root: Path, database: Path, workflow_id: str,
    *, reason: str = "workflow runner stopped by operator",
) -> tuple[str, ...]:
    """Close any Attempts left active after an explicit runner stop.

    The dashboard first terminates the owning runner process group, then calls
    this function to persist a truthful terminal Attempt and preserve its WIP.
    WorkItems are released by ``finish_attempt_failure`` and remain pending on
    the same fixed Task for a later explicit Resume.
    """
    cancelled: list[str] = []
    with StaticTaskGraphStore(database) as store:
        workflow = store.get_workflow(workflow_id)
        if workflow is None:
            return ()
        for task in store.list_tasks(workflow_id):
            attempt = store.active_attempt(task.id)
            if attempt is None:
                continue
            control = timeout_control_path(
                get_chip_nebula_dir(project_root), attempt.id,
            )
            terminate_recorded_run_process(control)
            workspace_commit, changed_paths = capture_leaked_wip_state(
                project_root,
                get_chip_nebula_dir(project_root) / "taskgraph-v2" / "workspaces",
                attempt.id, attempt.permission.write_paths,
                base_commit=str(attempt.diagnostics.get("workspace_base_commit", "")),
            )
            try:
                store.finish_attempt_failure(
                    attempt.id, reason=reason, cancelled=True,
                    workspace_commit=workspace_commit,
                    diagnostics={
                        "operator_cancelled": True,
                        "changed_paths": list(changed_paths),
                    },
                )
            except StateConflict:
                # The runner may have persisted its own terminal result while
                # the dashboard was waiting for the process group to exit.
                continue
            cancelled.append(attempt.id)
        if cancelled:
            store.pause_workflow(workflow_id, reason)
    return tuple(cancelled)


def _run_workflow_loop(
    project_root: Path, database: Path, workflow_id: str,
    pool: AgentPoolManager, *, workers: int, framework: str = "", model: str = "",
    reasoning_effort: str = "",
) -> WorkflowStatus:
    workspaces = AttemptWorkspaceFactory(
        project_root,
        get_chip_nebula_dir(project_root) / "taskgraph-v2" / "workspaces",
    )
    with StaticTaskGraphStore(database) as store:
        _recover_orphaned_attempts(store, workflow_id, project_root)
    with StaticTaskGraphStore(database) as store:
        routes = store.feedback_routes(workflow_id)

    def execute_one(attempt):
        with StaticTaskGraphStore(database) as worker_store:
            return AttemptRuntime(
                worker_store, pool, workspaces,
                project_root=project_root,
                feedback_routes=routes,
            ).execute(attempt)

    executor = ThreadPoolExecutor(max_workers=workers)
    running: dict[Future, object] = {}
    try:
        while True:
            with StaticTaskGraphStore(database) as store:
                workflow = store.get_workflow(workflow_id)
                if workflow is None:
                    raise KeyError(workflow_id)
                if workflow.status == WorkflowStatus.COMPLETE and not running:
                    return workflow.status
                scheduler = AttemptScheduler(
                    store, workflow_id, max_parallel_tasks=workers,
                    framework=framework, model=model,
                    reasoning_effort=reasoning_effort,
                )
                attempts = scheduler.claim(limit=max(0, workers - len(running)))
            for attempt in attempts:
                running[executor.submit(execute_one, attempt)] = attempt

            if running:
                # There is deliberately no batch/wave barrier. As soon as one
                # Attempt finishes, revisit the fixed graph and use the newly
                # available worker slot, even while unrelated siblings run.
                completed, _ = wait(tuple(running), timeout=1, return_when=FIRST_COMPLETED)
                for future in completed:
                    running.pop(future)
                    future.result()
                continue

            # No owned Attempt is running and no new Task was claimable. Only
            # now may this runner declare the Workflow quiescent.
            with StaticTaskGraphStore(database) as store:
                workflow = store.get_workflow(workflow_id)
                if workflow.status in {WorkflowStatus.ACTIVE, WorkflowStatus.READY}:
                    tasks = store.list_tasks(workflow_id)
                    if not any(store.active_attempt(task.id) for task in tasks):
                        paused = [
                            task.key for task in tasks
                            if store.task_state(task.id).value == "paused"
                        ]
                        human = [
                            task.key for task in tasks
                            if any(
                                item.kind.value == "human_question"
                                for item in store.pending_work(task.id)
                            )
                        ]
                        reason = (
                            "attempt budget or operator pause: " + ", ".join(paused)
                            if paused else
                            "awaiting human input: " + ", ".join(human)
                            if human else
                            "no Task is runnable; inspect failed engineering verdicts and unmet release conditions"
                        )
                        store.pause_workflow(workflow_id, reason)
                        workflow = store.get_workflow(workflow_id)
                return workflow.status
    except BaseException:
        # New Agent sessions do not have a framework session UUID until their
        # first protocol event. Attempt ids are stable from claim time, so
        # adapters also register this handle and shutdown can terminate every
        # process tree owned by this runner.
        for attempt in running.values():
            pool.terminate(attempt.id)
            if attempt.session_id:
                pool.terminate(attempt.session_id)
        raise
    finally:
        executor.shutdown(wait=True, cancel_futures=True)


@contextmanager
def _runner_shutdown_signals():
    """Turn terminal shutdown into normal adapter cleanup.

    Python's default SIGTERM/SIGHUP handling exits immediately and skips the
    ThreadPool cleanup path, leaving long-lived EDA/Agent subprocesses under
    PID 1.  Raising in the main thread lets ``run_workflow`` terminate every
    process registered to the active Attempts before it exits.
    """
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    handled = tuple(
        item for item in (signal.SIGTERM, getattr(signal, "SIGHUP", None))
        if item is not None
    )
    previous = {item: signal.getsignal(item) for item in handled}

    def interrupt(signum, _frame):
        raise KeyboardInterrupt(f"TaskGraph runner received signal {signum}")

    for item in handled:
        signal.signal(item, interrupt)
    try:
        yield
    finally:
        for item, handler in previous.items():
            signal.signal(item, handler)


def _recover_orphaned_attempts(
    store: StaticTaskGraphStore, workflow_id: str, project_root: Path,
) -> tuple[str, ...]:
    """Release claims whose owning runner process is definitely gone.

    Artifact ids and input versions are deliberately irrelevant. A live owner
    remains attached; a dead owner becomes a failed Attempt and the exact same
    pending WorkItems become claimable again on the same Task.
    """
    recovered: list[str] = []
    for task in store.list_tasks(workflow_id):
        attempt = store.active_attempt(task.id)
        if attempt is None:
            continue
        raw_pid = attempt.diagnostics.get("runner_pid")
        try:
            pid = int(raw_pid)
        except (TypeError, ValueError):
            pid = 0
        if pid and _process_alive(pid):
            continue
        control = timeout_control_path(
            get_chip_nebula_dir(project_root), attempt.id,
        )
        terminate_recorded_run_process(control)
        workspace_commit, changed_paths = capture_leaked_wip_state(
            project_root,
            get_chip_nebula_dir(project_root) / "taskgraph-v2" / "workspaces",
            attempt.id,
            attempt.permission.write_paths,
            base_commit=str(attempt.diagnostics.get("workspace_base_commit", "")),
        )
        store.finish_attempt_failure(
            attempt.id,
            reason="runner process ended before the Attempt reached a terminal state",
            workspace_commit=workspace_commit,
            diagnostics={
                "orphan_recovered": True,
                "changed_paths": list(changed_paths),
            },
        )
        recovered.append(attempt.id)
    return tuple(recovered)


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        status = subprocess.run(
            ["ps", "-o", "stat=", "-p", str(pid)],
            capture_output=True, text=True, check=False, timeout=2,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return True
    if status.startswith("Z"):
        return False
    return True


def import_initial_artifact(project_root: Path, artifact_id: str) -> Artifact:
    """Resolve one immutable Workflow-start fact from the canonical store.

    A static Workflow may consume only evidence registered in the same
    Task/Attempt store. Falling back to the retired dynamic database would
    silently mix two execution models and make the Workflow's real inputs
    depend on hidden legacy state.
    """
    static_database = database_path(project_root)
    if not static_database.is_file():
        raise FileNotFoundError(
            f"static TaskGraph database does not exist: {static_database}"
        )
    with StaticTaskGraphStore(static_database) as static:
        source = static.get_artifact(artifact_id)
    if source is None:
        raise FileNotFoundError(f"initial Artifact not found: {artifact_id}")
    return source


class AdapterPlannerBackend:
    def __init__(
        self, pool: AgentPoolManager, project_root: Path, *, workflow_id: str,
        inputs: tuple[Artifact, ...] = (),
    ) -> None:
        self.pool = pool
        self.project_root = project_root
        self.workflow_id = workflow_id
        self.inputs = inputs

    def generate(self, prompt: str, *, framework: str, model: str) -> str:
        with tempfile.TemporaryDirectory(prefix="chip-nebula-planner-") as directory:
            workspace = Path(directory)
            input_root = workspace / ".nebula_inputs"
            input_root.mkdir()
            for artifact in self.inputs:
                AttemptWorkspaceFactory._write_manifest(artifact, input_root)
            manifest = TaskManifest(
                task_id=f"{self.workflow_id}:planner",
                feature_id=self.workflow_id,
                stage="workflow-planning",
                assigned_agent="workflow-planner",
                context=TaskContext(
                    description="Create all fixed Task briefs before execution",
                ),
                description="Create all fixed Task briefs before execution",
                framework=framework,
                model=model,
                pipeline="taskgraph-v2-planning",
                timeout=1800,
                max_iterations=1,
                write_paths=["__planner_no_write__/**"],
                read_paths=[".nebula_inputs/**"],
                reuse_session=False,
                prompt_override=prompt,
            )
            result = self.pool.dispatch(
                manifest, workspace, project_root=self.project_root,
            )
            if not result.success:
                raise RuntimeError(result.error or "workflow planner failed")
            for artifact in self.inputs:
                record = json.loads((workspace / artifact.input_manifest_path).read_text(encoding="utf-8"))
                if record != {**artifact.document(), "digest": artifact.digest}:
                    raise RuntimeError(f"planning input record changed: {artifact.id}")
            return result.execution_log


def snapshot_text(database: Path, workflow_id: str, *, as_json: bool) -> str:
    with StaticTaskGraphStore(database) as store:
        snapshot = store.graph_snapshot(workflow_id)
    if as_json:
        return json.dumps(snapshot, ensure_ascii=False, indent=2)
    lines = [
        f"Workflow {workflow_id}: {snapshot['workflow']['status']}",
    ]
    for task in snapshot["tasks"]:
        lines.append(
            f"{task['state']:10} {task['key']} [{task['role']}@{task['role_version']}] "
            f"attempts={len(task['attempts'])} pending={len(task['pending_work'])}"
        )
    return "\n".join(lines)

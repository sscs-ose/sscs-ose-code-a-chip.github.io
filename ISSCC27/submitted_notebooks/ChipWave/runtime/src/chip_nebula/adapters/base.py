from abc import ABC, abstractmethod
import asyncio
import os
import random
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Awaitable, Callable, Iterable
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import psutil
from chip_nebula.models.task_manifest import TaskManifest, AgentResult
from chip_nebula.taskgraph_run_controls import effective_timeout_seconds

_NL = chr(10)


def wait_for_process_with_extendable_timeout(
    proc: subprocess.Popen[Any], task: TaskManifest,
) -> None:
    """Wait for ``proc`` while honoring live extensions to this Run's deadline.

    Extensions can only move the deadline later, so there is no polling: block
    until the currently known deadline, then re-read once at that boundary.
    """
    started = time.monotonic()
    base_timeout = int(task.timeout or 10800)
    while True:
        timeout = effective_timeout_seconds(task.timeout_control_path, base_timeout)
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            raise subprocess.TimeoutExpired(proc.args, timeout)
        try:
            proc.wait(timeout=remaining)
            return
        except subprocess.TimeoutExpired:
            extended_timeout = effective_timeout_seconds(
                task.timeout_control_path, base_timeout
            )
            if time.monotonic() - started >= extended_timeout:
                raise


async def await_with_extendable_timeout(awaitable: Awaitable[Any], task: TaskManifest) -> Any:
    """Await an SDK operation, re-reading extensions only at a deadline."""
    future = asyncio.ensure_future(awaitable)
    started = time.monotonic()
    base_timeout = int(task.timeout or 10800)
    try:
        while True:
            timeout = effective_timeout_seconds(task.timeout_control_path, base_timeout)
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0:
                raise asyncio.TimeoutError
            done, _ = await asyncio.wait({future}, timeout=remaining)
            if future in done:
                return future.result()
            if time.monotonic() - started >= effective_timeout_seconds(
                task.timeout_control_path, base_timeout
            ):
                raise asyncio.TimeoutError
    except BaseException:
        if not future.done():
            future.cancel()
            try:
                await future
            except BaseException:
                pass
        raise


def terminate_process_tree(
    proc: subprocess.Popen[Any], *, timeout: float = 5.0, process_group: bool = True,
) -> bool:
    """Terminate a subprocess and every descendant, returning whether all exited.

    Descendants are captured *before* the parent receives a signal.  The old
    implementation did this afterwards; once the CLI parent exited, OpenROAD
    was re-parented to PID 1 and escaped cleanup.
    """
    descendants: list[psutil.Process] = []
    try:
        descendants = psutil.Process(proc.pid).children(recursive=True)
    except (psutil.NoSuchProcess, ProcessLookupError):
        pass
    pgid: int | None = None
    if process_group and os.name == "posix":
        try:
            pgid = os.getpgid(proc.pid)
        except (ProcessLookupError, PermissionError):
            pass

    def _signal_group(sig: int) -> None:
        if pgid is not None:
            try:
                os.killpg(pgid, sig)
                return
            except (ProcessLookupError, PermissionError):
                pass
        for child in reversed(descendants):
            try:
                child.send_signal(sig)
            except (psutil.NoSuchProcess, PermissionError):
                pass
        try:
            proc.send_signal(sig)
        except (ProcessLookupError, PermissionError):
            pass

    _signal_group(signal.SIGTERM)
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        pass
    _, alive = psutil.wait_procs(descendants, timeout=timeout)
    if proc.poll() is None or alive:
        _signal_group(signal.SIGKILL)
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass
        _, alive = psutil.wait_procs(descendants, timeout=timeout)
    return proc.poll() is not None and not alive


# Bash commands that agents must never execute.  These mutate git state or
# destroy workspace files outside the adapter's post-run scope enforcement.
_FORBIDDEN_GIT_COMMANDS = frozenset(
    ("git reset", "git restore", "git checkout", "git clean", "git stash", "git rm --cached")
)


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a shell-style glob to a regex.

    Supported syntax:
        `**`   — any number of path segments (matches across `/`)
        `*`    — any chars except `/`
        `?`    — single char except `/`

    Matching is anchored (full-path, not substring).
    """
    out: list[str] = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if i + 1 < len(pattern) and pattern[i + 1] == "*":
                out.append(".*")
                i += 2
                if i < len(pattern) and pattern[i] == "/":
                    i += 1
            else:
                out.append("[^/]*")
                i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c in r".^$+(){}[]|\\":
            out.append(re.escape(c))
            i += 1
        else:
            out.append(c)
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _normalize_agent_path(path: str, workspace: Path | None = None) -> str:
    """Return ``path`` relative to the worktree root.

    Agent tool inputs usually pass relative paths, but if an absolute path is
    provided we try to make it relative to ``workspace``.  Any path that falls
    outside ``workspace`` is returned unchanged so the caller can deny it.
    """
    normalized = path.strip().lstrip("./")
    if workspace and Path(path).is_absolute():
        try:
            normalized = str(Path(path).relative_to(workspace))
        except ValueError:
            pass
    return normalized


def is_path_in_write_scope(
    path: str,
    write_paths: Iterable[str],
    workspace: Path | None = None,
) -> bool:
    """Return True when ``path`` is covered by one of ``write_paths``.

    Patterns are glob-like and relative to the worktree root.  A trailing
    slash means "this directory and everything underneath it".
    """
    patterns = [p for p in (write_paths or []) if p]
    if not patterns:
        return False

    normalized = _normalize_agent_path(path, workspace)
    for pattern in patterns:
        stripped = pattern.strip().lstrip("./")
        # Git Artifacts may compact a subtree to its directory root while
        # Role scopes normally spell the same boundary as ``directory/**``.
        # The root is part of that scope too; otherwise retry materialization
        # can overlay an older checkpoint on top of newer preserved WIP.
        if stripped.endswith("/**") and normalized == stripped[:-3].rstrip("/"):
            return True
        if stripped.endswith("/"):
            prefix = stripped
            root = stripped.rstrip("/")
            if normalized == root or normalized.startswith(prefix):
                return True
        if _glob_to_regex(stripped).match(normalized):
            return True
    return False


def contains_forbidden_git_command(command: str) -> Optional[str]:
    """Return the matched forbidden substring if ``command`` contains one."""
    normalized = command.lower().strip()
    for token in _FORBIDDEN_GIT_COMMANDS:
        if token in normalized:
            return token
    return None


def build_git_discipline(*, allow_git_add: bool = False) -> str:
    """Return the Git Discipline paragraph injected into every agent prompt.

    ``allow_git_add=True`` is used only by the post-gate staging assistant,
    which must be able to ``git add`` deliverables while still being forbidden
    from all other mutating git commands.
    """
    allowed = "`git status`, `git diff`, and `git log`"
    if allow_git_add:
        allowed += ", plus `git add` for staging deliverables"
    return (
        "\n- Git Discipline: You may only use " + allowed +
        " to READ repository state" +
        (" or stage deliverables" if allow_git_add else "") +
        ". You MUST NOT run `git reset`, `git restore`, `git checkout`, "
        "`git clean`, `git stash`, `git rm`, or any other command that "
        "modifies the git index, working tree, or HEAD. You MUST NOT modify "
        "`.gitignore`. The pipeline framework manages staging automatically "
        "after each stage passes its gates."
    )


def build_forbidden_git_refusal(command: str, forbidden: str) -> str:
    """Return a refusal message that can be sent back to the agent as a tool result.

    Keeping the refusal in the conversation gives the agent explicit feedback so
    it can correct course, instead of crashing the iteration silently.
    """
    return (
        f"Refused to execute Bash command: {command!r}. "
        f"The substring {forbidden!r} is forbidden because it can mutate git "
        "state (index, working tree, or HEAD). Git Discipline allows only "
        "`git status`, `git diff`, `git log`. Do not use `git reset`, "
        "`git restore`, `git checkout`, `git clean`, `git stash`, or `git rm`."
    )


def build_scope_refusal(path: str, write_paths: list[str]) -> str:
    """Return a refusal message for an Edit/Write outside ``write_paths``."""
    return (
        f"Refused to write {path!r}: it is outside the allowed write scope "
        f"{write_paths!r}. You may only create or modify files under the "
        "configured paths. Do not write to the project root or other "
        "directories outside your assigned scope."
    )


def build_can_use_tool(
    allow_cls: type[Any],
    deny_cls: type[Any],
    write_paths: list[str],
    workspace: Path | None = None,
) -> Callable[..., Awaitable[Any]]:
    """Return an SDK ``can_use_tool`` callback that enforces ``write_paths``.

    The callback denies ``Edit`` and ``Write`` tools whose target path is not
    covered by ``write_paths``, and denies ``Bash`` commands that contain
    forbidden git mutations.  Everything else is allowed.

    ``workspace`` must be the Agent's worktree root: SDKs typically pass
    absolute ``file_path`` values, which can only be matched against the
    relative ``write_paths`` patterns after relativizing against it.
    """
    async def _can_use_tool(
        tool_name: str, inp: dict[str, Any], ctx: Any
    ) -> Any:
        if tool_name in ("Edit", "Write"):
            path = str(inp.get("file_path") or inp.get("path") or "").strip()
            if path and not is_path_in_write_scope(path, write_paths, workspace):
                print(
                    f"[adapter can_use_tool] DENY {tool_name} {path!r} "
                    f"outside write_paths={write_paths}",
                    file=sys.stderr, flush=True,
                )
                return deny_cls(
                    behavior="deny",
                    message=build_scope_refusal(path, write_paths),
                    interrupt=False,
                )
        if tool_name == "Bash":
            cmd = str(inp.get("command", "")).strip()
            forbidden = contains_forbidden_git_command(cmd)
            if forbidden:
                print(
                    f"[adapter can_use_tool] DENY Bash {cmd!r} "
                    f"(forbidden {forbidden!r})",
                    file=sys.stderr, flush=True,
                )
                return deny_cls(
                    behavior="deny",
                    message=build_forbidden_git_refusal(cmd, forbidden),
                    interrupt=False,
                )
            print(
                f"[adapter can_use_tool] ALLOW Bash {cmd!r}",
                file=sys.stderr, flush=True,
            )
        return allow_cls(behavior="allow")

    return _can_use_tool


_FINAL_INSTRUCTION = (
    "FINAL INSTRUCTION: Your last message MUST report status explicitly.\n"
    "- If all verification gates pass: output 'ALL GATES PASSED'.\n"
    "- If any gate fails: output 'Error-Class: <name>' with Error-Class-Reason.\n"
    "Text without one of these two formats is ignored."
)

_TASKGRAPH_FINAL_INSTRUCTION = (
    "## Task Graph completion protocol (supersedes earlier session instructions)\n"
    "The platform runs the bound gates AFTER you finish. Do not claim or wait for "
    "their results, and do not declare an execution error because they have not run.\n"
    "When you have completed the assigned work and written the required outputs, "
    "end with 'TASK COMPLETED'. Put the engineering verdict (passed or failed) in "
    "the required report; a failed review/report is a valid completed output, not "
    "an Agent execution failure. The platform evaluates the report and gates and "
    "routes any required rework.\n"
    "Use 'Error-Class: <name>' with Error-Class-Reason only if you cannot complete "
    "the assigned work (execution/tool/environment failure), not for an engineering "
    "finding recorded in a completed report. Do not output 'ALL GATES PASSED'."
)


def automatic_error_inference_enabled(task: TaskManifest) -> bool:
    """Whether an adapter may infer execution failure from free-form prose.

    Task Graph owns the distinction between execution success, typed report
    verdicts and deterministic gate results.  Its adapters therefore preserve
    output verbatim; only an explicit Error-Class line may signal execution
    failure.  Legacy pipelines keep their historical heuristic behaviour.
    """
    return task.prompt_override is None and task.pipeline != "taskgraph"


def append_predecessor_info(parts: list[str], task: TaskManifest) -> None:
    pi = task.predecessor_info
    if not pi:
        return
    has_any = bool(
        pi.files or pi.metrics or pi.decisions or pi.failures
        or getattr(pi, "logs", None)
    )
    if not has_any:
        return
    parts.append("")
    parts.append("## Latest Stage Artifacts")
    if pi.files:
        parts.append("Files produced or modified by upstream stages:")
        for f in pi.files[:20]:
            parts.append(f"- {f}")
    if pi.metrics:
        parts.append("Metrics:")
        for k, v in list(pi.metrics.items())[:20]:
            parts.append(f"- {k}: {v}")
    if pi.decisions:
        parts.append("Design decisions:")
        for d in pi.decisions[:10]:
            parts.append(f"- {d}")
    if pi.failures:
        parts.append("Upstream failures:")
        for f in pi.failures[:5]:
            stage = f.get("stage", "?") if isinstance(f, dict) else getattr(f, "stage", "?")
            parts.append(f"- {stage}")
    if getattr(pi, "logs", None):
        parts.append("")
        parts.append("## Upstream Stage Execution Logs")
        parts.append(
            "Understand these logs from upstream stages before you start working. "
            "They contain the reasoning, changes, and results you should build on."
        )
        for stage_name, log in pi.logs.items():
            parts.append("")
            parts.append(f"### Execution log from `{stage_name}`")
            parts.append("```")
            parts.append(log)
            parts.append("```")


def append_failure_context(parts: list[str], pfc: Optional[Any]) -> None:
    if not pfc:
        return
    if getattr(pfc, "source_stage", None) == "user" and getattr(
        pfc, "error_class", None
    ) == "user_prompt":
        parts.append("")
        parts.append("## User Directive")
        reason = getattr(pfc, "error_class_reason", "") or ""
        if reason:
            parts.append(reason)
        return

    parts.append("")
    parts.append("## Upstream Failure Context")
    parts.append(
        f"Stage `{pfc.source_stage}` classified its failure as "
        f"`{pfc.error_class}` after {pfc.iteration_count} iteration(s)."
    )
    if getattr(pfc, "error_class_reason", None):
        parts.append(f"Reason: {pfc.error_class_reason}")
    if getattr(pfc, "execution_log", None):
        parts.append("")
        parts.append("Downstream agent's full analysis:")
        truncated = pfc.execution_log[:4000]
        if len(pfc.execution_log) > 4000:
            truncated += f"\n... (truncated {len(pfc.execution_log) - 4000} chars)"
        parts.append(truncated)
    if getattr(pfc, "errors", None):
        parts.append("Structured errors observed downstream:")
        for e in pfc.errors[:10]:
            parts.append(f"- [{e.code}] {e.file}:{e.line} — {e.message}")
    if getattr(pfc, "modified_files", None):
        parts.append(
            "Files the downstream stage touched: "
            + ", ".join(pfc.modified_files[:8])
        )


def append_classification_protocol(
    parts: list[str], task: TaskManifest, *, summary: bool = False
) -> None:
    specs = getattr(task, "_error_class_specs", None) or {}
    if not specs:
        return
    parts.append("")
    if summary:
        parts.append("## Error Classification")
        by_priority = sorted(specs.items(), key=lambda kv: -kv[1].priority)
        for name, spec in by_priority:
            parts.append(
                f"- `{name}` (priority={spec.priority}): {spec.description or ''}"
            )
        return
    if task.pipeline == "taskgraph":
        parts.append("## Execution Error Classification (only if unable to complete the Task)")
        parts.append(
            "The platform evaluates gates and engineering reports after completion. "
            "Record engineering findings in the report, not in execution error tags. "
            "Only if you cannot produce the required outputs, classify the execution failure:"
        )
    else:
        parts.append("## Error Classification (REQUIRED if gates do not pass)")
        parts.append(
            "If the verification gates do not pass, classify the failure by emitting:"
        )
    parts.append("```")
    parts.append("Error-Class: <one of the classes listed below>")
    parts.append("Error-Class-Reason: <one-sentence explanation>")
    parts.append("```")
    parts.append("Valid classes:")
    by_priority = sorted(specs.items(), key=lambda kv: -kv[1].priority)
    for name, spec in by_priority:
        parts.append(
            f"- `{name}` (priority={spec.priority}): {spec.description or ''}"
        )


def build_agent_prompt(task: TaskManifest) -> str:
    parts = ["## Role", task.assigned_agent, ""]
    parts.append("## Task")
    parts.append(task.context.description if task.context else task.description)

    append_failure_context(parts, task.predecessor_failure_context)
    append_predecessor_info(parts, task)

    if task.target:
        parts.append("")
        parts.append("## Target Files (informational — may already exist)")
        for f in task.target:
            parts.append(f"- {f.path}: {f.reason}")
    if task.errors:
        parts.append("")
        parts.append("## Errors to Fix")
        for err in task.errors:
            parts.append(f"- [{err.code}] {err.file}:{err.line} - {err.message}")
    if task.previous_attempt:
        parts.append("")
        parts.append("## Previous Attempt")
        if task.previous_attempt.error_class:
            parts.append(
                f"Last classification: `{task.previous_attempt.error_class}`"
            )
        parts.append(task.previous_attempt.agent_notes)
    if task.completion_criteria:
        parts.append("")
        parts.append(
            "## Verification Gates (checked AFTER you finish — do NOT try to satisfy them)"
        )
        for c in task.completion_criteria:
            parts.append(f"- {c}")

    if task.artifact_output_contracts:
        parts.append("")
        parts.append("## Artifact Output Contract (REQUIRED before completion)")
        parts.append(
            "These path selectors and JSON invariants are part of this Task's "
            "declared output. Create or update every listed file before reporting completion."
        )
        for contract in task.artifact_output_contracts:
            parts.append(f"- {contract}")

    if task.write_paths:
        parts.append("")
        parts.append("## Write Scope (DO NOT write outside these paths)")
        for wp in task.write_paths:
            parts.append(f"- {wp}")
        parts.append("")
        parts.append(
            "All Bash commands that may run for more than a few seconds "
            "(simulations, regression, debug builds) MUST specify a timeout "
            "so they cannot hang the pipeline. Do not run open-ended debug "
            "simulations without a bounded timeout."
        )

    append_classification_protocol(parts, task)

    parts.append(build_git_discipline())
    final_instruction = (
        _TASKGRAPH_FINAL_INSTRUCTION if task.pipeline == "taskgraph" else _FINAL_INSTRUCTION
    )
    return _NL.join(parts) + _NL + _NL + final_instruction


def build_continuation_prompt(task: TaskManifest) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if task.pipeline == "taskgraph":
        # A resumed session can contain obsolete completion instructions and
        # paths from a removed worktree. Resend the complete current contract,
        # including authoritative inputs, write scope and platform-owned gates.
        return (
            f"## [{now}] Continuing session `{task.session_id}` for stage `{task.stage}`\n"
            "Resume your previous work, but follow the CURRENT Task contract below. "
            "It supersedes earlier task paths, scope and completion instructions.\n\n"
            + build_agent_prompt(task)
        )
    parts = [
        f"## [{now}] Continuing session `{task.session_id}` for stage `{task.stage}`",
        "",
        "Resume the previous conversation. The prompt below contains NEW feedback from a downstream stage. You MUST address this feedback before reporting completion status.",
    ]
    append_failure_context(parts, task.predecessor_failure_context)
    append_predecessor_info(parts, task)

    if task.errors:
        parts.append("")
        parts.append("## New Errors to Fix")
        for err in task.errors:
            parts.append(f"- [{err.code}] {err.file}:{err.line} - {err.message}")
    if task.previous_attempt:
        parts.append("")
        parts.append("## Previous Attempt")
        if task.previous_attempt.error_class:
            parts.append(
                f"Last classification: `{task.previous_attempt.error_class}`"
            )
        parts.append(task.previous_attempt.agent_notes)
    if task.completion_criteria:
        parts.append("")
        parts.append("## Verification Gates")
        for c in task.completion_criteria:
            parts.append(f"- {c}")

    if task.artifact_output_contracts:
        parts.append("")
        parts.append("## Current Artifact Output Contract (REQUIRED)")
        parts.append(
            "The current Task contract supersedes any older filenames or formats in this session."
        )
        for contract in task.artifact_output_contracts:
            parts.append(f"- {contract}")

    append_classification_protocol(parts, task, summary=True)

    parts.append(build_git_discipline())
    return _NL.join(parts)


def detect_changed_files(workspace: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, cwd=workspace,
        )
        if result.returncode == 0:
            return [line for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        pass
    return []


def revert_out_of_scope(
    workspace: Path,
    project_root: Optional[Path],
    paths: list[str],
    label: str,
) -> None:
    for p in paths:
        try:
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", p],
                capture_output=True, text=True, cwd=workspace,
            )
            if tracked.returncode == 0:
                subprocess.run(
                    ["git", "checkout", "--", p],
                    capture_output=True, text=True, cwd=workspace,
                )
                print(
                    f"  [{label} adapter] Reverted out-of-scope path: {p}",
                    file=sys.stderr, flush=True,
                )
        except Exception as exc:
            print(
                f"  [{label} adapter] Failed to revert out-of-scope path {p}: {exc}",
                file=sys.stderr, flush=True,
            )


def record_session_id(
    project_root: Optional[Path],
    feature_id: str,
    stage: str,
    session_id: str,
    run_id: str = "",
) -> None:
    """Persist the chosen agent session id so the dashboard can display the
    session transcript while a stage is still running.

    With ``run_id`` set, additionally records a per-Run sidecar
    (``<stage>.<run_id>.txt``) so every attempt of a taskgraph task keeps its
    own session mapping instead of all pointing at the latest one.
    """
    if not project_root or not feature_id or not stage or not session_id:
        return
    directory = (
        Path(project_root)
        / ".chip_nebula"
        / "shared"
        / "memory"
        / "session_ids"
        / feature_id
    )
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{stage}.txt").write_text(session_id)
    if run_id:
        (directory / f"{stage}.{run_id}.txt").write_text(session_id)


class _SessionRegistry:
    """In-memory registry mapping (feature_id, stage) -> the actual session ID
    the adapter is currently using.

    The adapter finalizes its session ID *after* the pipeline interpreter has
    already submitted the stage, so the interpreter cannot know the ID in
    advance. This registry lets the interpreter stop/terminate a running
    session even when the adapter generated the ID itself.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._sessions: dict[tuple[str, str], str] = {}

    def register(self, feature_id: str, stage: str, session_id: str) -> None:
        if feature_id and stage and session_id:
            with self._lock:
                self._sessions[(feature_id, stage)] = session_id

    def get(self, feature_id: str, stage: str) -> str | None:
        with self._lock:
            return self._sessions.get((feature_id, stage))

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()


session_registry = _SessionRegistry()


class AgentFrameworkAdapter(ABC):
    @abstractmethod
    def execute(
        self, task: TaskManifest, workspace: Path,
        project_root: Optional[Path] = None,
    ) -> AgentResult:
        pass

    def terminate(self, session_id: str) -> None:
        """Best-effort terminate the running session identified by ``session_id``.

        Concrete adapters that manage long-running subprocesses or async SDK
        sessions should override this. The default implementation is a no-op so
        that tests and mock adapters are not broken.
        """
        return None


def unavailable_agent_result(framework: str, reason: str) -> AgentResult:
    """Return an explicit environment failure for an unavailable real agent.

    Mock execution is a separate, user-selected framework. A missing binary,
    SDK, or credential for a real framework must never manufacture a successful
    result through :class:`MockAgentFrameworkAdapter`.
    """
    message = f"Agent framework '{framework}' is unavailable: {reason}"
    return AgentResult(
        success=False,
        execution_log=(
            f"{message}\n"
            "Error-Class: env\n"
            f"Error-Class-Reason: {reason}"
        ),
        error=message,
    )

class MockAgentFrameworkAdapter(AgentFrameworkAdapter):
    def __init__(self, success_rate: float = 1.0, mock_duration: float = 1.0):
        self.success_rate = success_rate
        self.mock_duration = mock_duration

    def execute(
        self, task: TaskManifest, workspace: Path,
        project_root: Optional[Path] = None,
    ) -> AgentResult:
        start_time = time.time()

        sleep_time = random.uniform(0.5, 2.0) * self.mock_duration
        time.sleep(sleep_time)

        success = random.random() < self.success_rate
        files_modified = []

        session_id = task.session_id or ""
        if task.reuse_session and not session_id:
            session_id = f"mock-{task.stage}-{uuid.uuid4().hex[:8]}"
        elif task.reuse_session and session_id:
            pass

        record_session_id(project_root, task.feature_id, task.stage, session_id, run_id=getattr(task, "run_id", ""))

        if success:
            dummy_file = workspace / f"mock_output_{task.task_id}.txt"
            dummy_file.write_text(f"Mock output for {task.task_id}\n")
            self._stub_file_check_targets(task, workspace)

        duration = time.time() - start_time

        log = f"Mock execution for task {task.task_id}"
        if task.reuse_session:
            log += f" (session reused: {session_id})" if task.session_id else f" (new session: {session_id})"

        return AgentResult(
            success=success,
            files_modified=files_modified,
            execution_log=log,
            tool_calls=[{"tool": "mock_tool"}],
            duration_seconds=duration,
            error=None if success else "Mock failure",
            session_id=session_id,
        )

    @staticmethod
    def _stub_file_check_targets(task: TaskManifest, workspace: Path) -> None:
        """Create placeholder files for every file_check criterion so the
        real ExitGate passes in mock mode."""
        exit_criteria = getattr(task, "_exit_criteria", None)
        if not exit_criteria:
            return
        for raw in exit_criteria:
            if not isinstance(raw, dict):
                continue
            if raw.get("type") != "file_check":
                continue
            for pattern in raw.get("paths", []):
                # Resolve the glob pattern to at least one concrete file.
                # If the pattern has wildcards, create a concrete stub;
                # otherwise, create the exact path.
                if any(ch in pattern for ch in "*?[]"):
                    stub = workspace / pattern.replace("*", "stub").replace("?", "x")
                else:
                    stub = workspace / pattern
                stub.parent.mkdir(parents=True, exist_ok=True)
                if not stub.exists():
                    stub.write_text(f"# Mock stub for {pattern}\n")

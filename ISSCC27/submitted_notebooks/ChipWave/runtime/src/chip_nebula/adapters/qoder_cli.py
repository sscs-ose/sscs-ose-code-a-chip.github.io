import asyncio
import json
import os
import threading
import time
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any, Optional

import psutil

from chip_nebula.models.task_manifest import (
    DEFAULT_SESSION_TOKEN_THRESHOLD,
    TaskManifest,
    AgentResult,
)
from chip_nebula.adapters.base import (
    AgentFrameworkAdapter,
    await_with_extendable_timeout,
    automatic_error_inference_enabled,
    build_agent_prompt,
    build_can_use_tool,
    build_continuation_prompt,
    build_forbidden_git_refusal,
    contains_forbidden_git_command,
    detect_changed_files,
    record_session_id,
    revert_out_of_scope,
    session_registry,
    unavailable_agent_result,
)
from chip_nebula.adapters.scope_check import (
    detect_changed_paths,
    format_scope_violation_log,
    violations,
)

from chip_nebula.adapters.error_class_inference import infer_error_class
from chip_nebula.taskgraph_run_controls import effective_timeout_seconds

_NL = chr(10)

_QODER_MODEL_MAP: dict[str, str] = {
    "deepseek-v4-pro": "DeepSeek-V4-Pro",
    "deepseek-v4-flash": "DeepSeek-V4-Flash",
    "deepseek-v4": "DeepSeek-V4-Pro",
    "deepseek-v3": "Auto",
    "deepseek": "Auto",
    # Qoder currently exposes the production name "Qwen3.8-Max" for this account.
    # The "-Preview" suffix resolves internally but then receives a FORBIDDEN
    # entitlement error (code 112), so all aliases route to the canonical name.
    "qwen3.8-max": "Qwen3.8-Max",
    "qwen-3.8-max": "Qwen3.8-Max",
    "qwen3.8-max-preview": "Qwen3.8-Max",
    "Qwen3.8-Max-Preview": "Qwen3.8-Max",
    "Qwen3.8-Max": "Qwen3.8-Max",
    "qwen3.7-max": "Qwen3.7-Max",
    "qwen-3.7-max": "Qwen3.7-Max",
    "qwen3.7-plus": "Qwen3.7-Plus",
    "kimi-k3": "Kimi-K3",
    "kimi-k2.7-code": "Kimi-K2.7-Code",
    "glm-5.2": "GLM-5.2",
    "minimax-m3": "MiniMax-M3",
}


def _build_model_resolver(desired: str):
    """Return a pull-mode model selector for the Qoder SDK.

    The selector receives the live ``availableModels`` catalog from qodercli and
    returns the internal model value (e.g. ``qmodel_38max``) that best matches
    the user-facing ``desired`` name.  This avoids hard-coding Qoder's internal
    IDs while still honoring the user's model choice.
    """
    desired_lower = desired.lower()

    def _resolver(context: dict[str, Any]) -> dict[str, Any]:
        available = context.get("availableModels") or []
        candidates = [
            m for m in available
            if m.get("isEnabled", True) and m.get("value")
        ]

        # 1) exact internal value match
        for m in candidates:
            if m["value"].lower() == desired_lower:
                return {"model": m["value"]}

        # 2) exact display-name match (case-insensitive)
        for m in candidates:
            if (m.get("displayName") or "").lower() == desired_lower:
                return {"model": m["value"]}

        # 3) substring display-name match (e.g. "qwen3.8-max" -> "Qwen3.8-Max")
        for m in candidates:
            if desired_lower in (m.get("displayName") or "").lower():
                return {"model": m["value"]}

        # 4) fallback to auto, then the first enabled model
        for m in candidates:
            if m["value"].lower() == "auto":
                print(
                    f"  [qoder_cli adapter] Model '{desired}' not in catalog; "
                    "falling back to auto.",
                    file=sys.stderr, flush=True,
                )
                return {"model": "auto"}
        if candidates:
            fallback = candidates[0]["value"]
            print(
                f"  [qoder_cli adapter] Model '{desired}' not in catalog; "
                f"falling back to '{fallback}'.",
                file=sys.stderr, flush=True,
            )
            return {"model": fallback}

        # Should not happen, but keep the session alive.
        return {"model": "lite"}

    return _resolver


_ALLOWED_TOOLS = [
    "Bash",
    "Edit",
    "Write",
    "Read",
    "Glob",
    "Grep",
    "TodoWrite",
]

# ---------------------------------------------------------------------------
#  Optional Qoder SDK import — reported as unavailable when not installed.
# ---------------------------------------------------------------------------
try:
    import qoder_agent_sdk as sdk
    from qoder_agent_sdk import (
        AssistantMessage,
        QoderAgentOptions,
        ResultMessage,
        TextBlock,
        ToolUseBlock,
    )

    HAS_QODER_SDK = True
except ImportError:
    HAS_QODER_SDK = False
    sdk = None  # type: ignore[assignment]
    QoderAgentOptions = None  # type: ignore[assignment]
    AssistantMessage = None  # type: ignore[assignment]
    TextBlock = None  # type: ignore[assignment]
    ToolUseBlock = None  # type: ignore[assignment]
    ResultMessage = None  # type: ignore[assignment]


class QoderCLIAdapter(AgentFrameworkAdapter):
    """Adapter that drives the Qoder Agent SDK (qoder_agent_sdk).

    Uses the same async streaming pattern as ClaudeCodeAdapter. Missing SDK or
    authentication is an explicit environment failure; mock execution must be
    selected separately.
    """

    def __init__(self, model_provider: str = "deepseek"):
        self.model_provider = model_provider
        self._lock = threading.Lock()
        self._active_tasks: dict[str, tuple[asyncio.Task, asyncio.AbstractEventLoop]] = {}

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def execute(
        self,
        task: TaskManifest,
        workspace: Path,
        project_root: Optional[Path] = None,
    ) -> AgentResult:
        if not HAS_QODER_SDK:
            return unavailable_agent_result(
                "qodercli", "the qoder_agent_sdk package is not installed"
            )

        # -- Session tracking --
        session_id = task.session_id or ""
        is_new_session = False
        if task.reuse_session and not session_id:
            session_id = str(uuid.uuid4())
            is_new_session = True

        # -- Session length fuse (same heuristic as ClaudeCodeAdapter) --
        _SESSION_TOKEN_THRESHOLD = (
            task.session_token_threshold
            if hasattr(task, "session_token_threshold") and task.session_token_threshold
            else DEFAULT_SESSION_TOKEN_THRESHOLD
        )
        if task.reuse_session and session_id and not is_new_session:
            if not self._session_exists(session_id):
                print(
                    f"  [qoder_cli adapter] Session {session_id} transcript not found; "
                    "forcing new session.",
                    file=sys.stderr,
                    flush=True,
                )
                session_id = str(uuid.uuid4())
                is_new_session = True
            else:
                estimated = self._estimate_session_tokens(session_id)
                if estimated >= _SESSION_TOKEN_THRESHOLD:
                    print(
                        f"  [qoder_cli adapter] Session {session_id} estimated "
                        f"{estimated} tokens >= {_SESSION_TOKEN_THRESHOLD}; "
                        "forcing new session.",
                        file=sys.stderr,
                        flush=True,
                    )
                    session_id = str(uuid.uuid4())
                    is_new_session = True

        record_session_id(project_root, task.feature_id, task.stage, session_id, run_id=getattr(task, "run_id", ""))
        session_registry.register(task.feature_id, task.stage, session_id)

        prompt = self._build_qoder_prompt(task)
        start = time.time()
        pre_snapshot = set(detect_changed_paths(workspace, working_tree_only=True))

        max_turns = getattr(task, "max_turns_per_session", None) or 30

        # Qoder exposes models as internal values (e.g. ``qmodel_38max``) in SDK
        # mode, while users configure friendly names like ``qwen-3.8-max``.  We
        # use pull-mode model selection (``resolve_model``) so we can pick the
        # right value from the live catalog instead of guessing internal IDs.
        raw_model = task.model or ""
        desired_model = _QODER_MODEL_MAP.get(raw_model.lower()) or raw_model
        system_prompt = task.context.system_prompt if task.context else ""

        # -- Build QoderAgentOptions --
        can_use_tool = build_can_use_tool(
            sdk.PermissionResultAllow,
            sdk.PermissionResultDeny,
            task.write_paths or [],
            workspace,
        )
        options_kwargs: dict[str, Any] = {
            "cwd": str(workspace),
            "max_turns": max_turns,
            "allowed_tools": _ALLOWED_TOOLS,
            "can_use_tool": can_use_tool,
        }
        if desired_model:
            options_kwargs["resolve_model"] = _build_model_resolver(desired_model)
        if system_prompt:
            options_kwargs["system_prompt"] = system_prompt
        if session_id:
            if is_new_session:
                options_kwargs["session_id"] = session_id
            else:
                options_kwargs["resume"] = session_id

        # Auth: try PAT env var first, then local CLI login.
        # access_token_from_env() does NOT raise when var is missing —
        # it returns an auth object that fails later inside query().
        # We check os.environ proactively so we can give a clear message.
        try:
            from qoder_agent_sdk import access_token, access_token_from_env, qodercli_auth

            token = os.environ.get("QODER_PERSONAL_ACCESS_TOKEN", "")
            if token:
                options_kwargs["auth"] = access_token(token)
            else:
                options_kwargs["auth"] = qodercli_auth()
        except Exception as exc:
            return unavailable_agent_result(
                "qodercli",
                "authentication is unavailable; set "
                "QODER_PERSONAL_ACCESS_TOKEN or run 'qodercli login' first "
                f"({exc})",
            )

        options = QoderAgentOptions(**options_kwargs)

        tailer = _SDKSessionTailer(stage=task.stage, agent=task.assigned_agent)
        tailer.start()

        cache_read_tokens = 0
        try:
            effective_timeout = task.timeout if task.timeout else 10800
            result_text, tool_count, cache_read_tokens = asyncio.run(
                await_with_extendable_timeout(
                    self._run_query(prompt, options, tailer, session_id), task
                )
            )
        except asyncio.TimeoutError:
            tailer.stop()
            duration = time.time() - start
            # If a brand-new session never finished initializing, do not persist
            # its ID — subsequent iterations would try to resume a ghost session.
            returned_session_id = "" if is_new_session else session_id
            return AgentResult(
                success=False,
                files_modified=detect_changed_files(workspace),
                execution_log="",
                tool_calls=[],
                duration_seconds=duration,
                error=f"Timeout after {effective_timeout_seconds(task.timeout_control_path, effective_timeout)}s",
                session_id=returned_session_id,
                cache_read_input_tokens=cache_read_tokens,
            )
        except Exception as exc:
            tailer.stop()
            duration = time.time() - start
            returned_session_id = "" if is_new_session else session_id
            return AgentResult(
                success=False,
                files_modified=detect_changed_files(workspace),
                execution_log=f"SDK error: {exc}",
                tool_calls=[],
                duration_seconds=duration,
                error=str(exc),
                session_id=returned_session_id,
                cache_read_input_tokens=cache_read_tokens,
            )
        finally:
            tailer.stop()

        duration = time.time() - start
        changed = detect_changed_files(workspace)
        execution_log = f"[qoder rc=0 dur={duration:.0f}s]\n"
        execution_log += (result_text or "") + _NL

        # Auto-classify failures when agent output signals test failures
        # but forgot to emit Error-Class tags. Skipped entirely for
        # prompt_override (roundtable) runs: conclusions stay verbatim.
        output_text = result_text or ""
        class_specs = getattr(task, "_error_class_specs", None) or {}
        infer_errors = automatic_error_inference_enabled(task)
        inferred = infer_error_class(output_text, class_specs) if infer_errors else None
        if inferred:
            inferred_class, inferred_reason = inferred
            execution_log += _NL + f"Error-Class: {inferred_class}" + _NL
            execution_log += (
                f"Error-Class-Reason: {inferred_reason} (auto-detected)" + _NL
            )
        elif (
            infer_errors
            and ("FAILED" in output_text or "SOME TESTS PASSED" not in output_text)
            and "Error-Class:" not in output_text
            and "ALL GATES PASSED" not in output_text
            and "PASSED" not in output_text
            and any(kw in output_text for kw in ("FAIL", "ERROR", "error:", "Error:"))
        ):
            execution_log += _NL + "Error-Class: dut_error" + _NL
            execution_log += (
                "Error-Class-Reason: agent reported failures (auto-detected)" + _NL
            )

        success = True
        error = None
        post_paths = set(detect_changed_paths(workspace, working_tree_only=True))
        new_paths = post_paths - pre_snapshot
        bad = violations(new_paths, task.write_paths)
        if bad:
            if not task.live_workspace:
                revert_out_of_scope(workspace, project_root, bad, "qoder_cli")
            success = False
            execution_log += format_scope_violation_log(bad, task.write_paths)
            error = f"Scope violation: {len(bad)} path(s) outside write_paths"

        return AgentResult(
            success=success,
            files_modified=changed,
            execution_log=execution_log,
            tool_calls=[],
            duration_seconds=duration,
            error=error,
            session_id=session_id,
            cache_read_input_tokens=cache_read_tokens,
        )

    # ------------------------------------------------------------------
    #  Async query loop
    # ------------------------------------------------------------------

    @staticmethod
    async def _prompt_stream(prompt: str):
        yield {
            "type": "user",
            "session_id": "",
            "message": {"role": "user", "content": prompt},
            "parent_tool_use_id": None,
        }

    async def _run_query(
        self,
        prompt: str,
        options: "QoderAgentOptions",
        tailer: "_SDKSessionTailer",
        session_id: str = "",
    ) -> tuple[str, int, int]:
        chunks: list[str] = []
        result_text: str | None = None
        tool_count = 0
        msg_types: dict[str, int] = {}
        last_cache_read = 0

        # Query unit tests and callers without a resumable session may run on
        # an AnyIO Trio backend.  Cancellation tracking is only useful when a
        # concrete session id exists; real SDK dispatch runs inside asyncio.run.
        if session_id:
            current_task = asyncio.current_task()
            loop = asyncio.get_running_loop()
            if current_task is not None:
                with self._lock:
                    self._active_tasks[session_id] = (current_task, loop)

        stream = sdk.query(prompt=self._prompt_stream(prompt), options=options)
        try:
            async for message in stream:
                mtype = type(message).__name__
                msg_types[mtype] = msg_types.get(mtype, 0) + 1
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            chunks.append(block.text)
                        elif isinstance(block, sdk.ToolUseBlock):
                            tool_count += 1
                            name = getattr(block, "name", "?")
                            inp = getattr(block, "input", {}) or {}
                            if name == "Bash":
                                cmd = str(inp.get("command", "")).strip()
                                forbidden = contains_forbidden_git_command(cmd)
                                if forbidden:
                                    chunks.append(
                                        "\n[Adapter refused Bash command: "
                                        + build_forbidden_git_refusal(cmd, forbidden)
                                        + "]\n"
                                    )
                                    tailer.on_tool(name, inp)
                                    continue
                            tailer.on_tool(name, inp)
                    usage = getattr(message, "usage", None) or {}
                    if isinstance(usage, dict):
                        last_cache_read = usage.get(
                            "cache_read_input_tokens", last_cache_read
                        )
                    elif hasattr(usage, "cache_read_input_tokens"):
                        last_cache_read = getattr(
                            usage, "cache_read_input_tokens", last_cache_read
                        )
                elif isinstance(message, ResultMessage):
                    result_text = getattr(message, "result", None)
        except Exception:
            import traceback
            traceback.print_exc(file=sys.stderr)
            raise
        finally:
            if session_id:
                with self._lock:
                    self._active_tasks.pop(session_id, None)

        if msg_types:
            import pprint
            pprint.pprint(msg_types, stream=sys.stderr)

        final = result_text if result_text is not None else "".join(chunks)
        return final, tool_count, last_cache_read

    def terminate(self, session_id: str) -> None:
        """Cancel the active asyncio task and clean up SDK child processes."""
        if not session_id:
            return None
        with self._lock:
            entry = self._active_tasks.pop(session_id, None)
        if entry is None:
            return None
        task, loop = entry
        try:
            loop.call_soon_threadsafe(task.cancel)
        except RuntimeError:
            pass
        self._kill_sdk_children(session_id)
        return None

    def _kill_sdk_children(self, session_id: str, timeout: float = 5) -> None:
        """Kill any child qoder CLI processes whose command line contains the session ID."""
        try:
            current = psutil.Process()
            children = current.children(recursive=True)
            targets = [
                child for child in children
                if session_id in " ".join(child.cmdline() or [])
            ]
            for child in targets:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            _, alive = psutil.wait_procs(targets, timeout=timeout)
            for child in alive:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
        except (psutil.NoSuchProcess, ProcessLookupError):
            pass
        except PermissionError as exc:
            print(
                f"  [qoder_cli adapter] Permission denied cleaning up children: {exc}",
                file=sys.stderr, flush=True,
            )

    # ------------------------------------------------------------------
    #  Session existence / size helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _session_file_path(session_id: str) -> Path | None:
        """Return the path to a Qoder session JSONL if it exists, else None."""
        if not session_id:
            return None
        try:
            matches = list(Path.home().glob(f".qoder/projects/*/{session_id}.jsonl"))
            return matches[0] if matches else None
        except Exception:
            return None

    def _session_exists(self, session_id: str) -> bool:
        """True if Qoder has a transcript file for this session_id."""
        path = self._session_file_path(session_id)
        return path is not None and path.is_file()

    def _estimate_session_tokens(self, session_id: str) -> int:
        """Estimate session size from the JSONL log.

        Qoder stores sessions in ``~/.qoder/projects/<slug>/<id>.jsonl``
        and does NOT include per-message ``usage`` fields (unlike Claude
        Code).  We count assistant messages and multiply by a conservative
        per-turn average (4 KiB) to decide whether the session is too large
        to safely resume.
        """
        if not session_id:
            return 0
        try:
            matches = list(
                Path.home().glob(f".qoder/projects/*/{session_id}.jsonl")
            )
            for log_path in matches:
                assistant_count = 0
                with open(log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        d = json.loads(line)
                        if d.get("type") == "assistant":
                            assistant_count += 1
                return assistant_count * 4000
        except Exception:
            pass
        return 0

    # ------------------------------------------------------------------
    #  Scope enforcement
    # ------------------------------------------------------------------

    def _build_qoder_prompt(self, task: TaskManifest) -> str:
        if task.prompt_override is not None:
            return task.prompt_override
        if task.reuse_session and task.session_id:
            return build_continuation_prompt(task)
        return build_agent_prompt(task)


# ---------------------------------------------------------------------------
#  Real-time progress display (mirrors _SDKSessionTailer in claude_code.py)
# ---------------------------------------------------------------------------


class _SDKSessionTailer:
    """Real-time progress display for Qoder SDK agent sessions."""

    _TOOL_LABELS = {
        "Read": "Reading",
        "Write": "Writing",
        "Edit": "Editing",
        "Bash": "Running",
        "Glob": "Searching",
        "Grep": "Searching",
        "Task": "Planning",
        "TodoWrite": "Planning",
    }

    def __init__(self, stage: str = "", agent: str = ""):
        import threading

        self._prefix = f"  [{stage}/{agent}]" if stage else "  [agent]"
        self._tool_count = 0
        self._last_action = "starting..."
        self._start_time = time.time()
        self._stop = threading.Event()
        self._pulse_thread: Optional[threading.Thread] = None

    def start(self):
        import threading

        self._pulse_thread = threading.Thread(target=self._pulse, daemon=True)
        self._pulse_thread.start()

    def stop(self):
        self._stop.set()

    def on_tool(self, name: str, inp: dict):
        self._tool_count += 1
        label = self._TOOL_LABELS.get(name, name)
        detail = ""
        if name == "Read":
            detail = str(inp.get("file_path", "")).split("/")[-1]
        elif name in ("Write", "Edit"):
            detail = str(inp.get("file_path", "")).split("/")[-1]
        elif name == "Bash":
            detail = str(inp.get("command", ""))[:60]
        elif name == "Glob":
            detail = inp.get("pattern", "")
        self._last_action = f"{label} {detail}" if detail else label
        print(f"{self._prefix} {self._last_action}", file=sys.stderr, flush=True)

    def _pulse(self):
        while not self._stop.is_set():
            self._stop.wait(60)
            if self._stop.is_set():
                return
            elapsed = int(time.time() - self._start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            print(
                f"{self._prefix} [{mins}m{secs:02d}s, {self._tool_count} actions] {self._last_action}",
                file=sys.stderr,
                flush=True,
            )

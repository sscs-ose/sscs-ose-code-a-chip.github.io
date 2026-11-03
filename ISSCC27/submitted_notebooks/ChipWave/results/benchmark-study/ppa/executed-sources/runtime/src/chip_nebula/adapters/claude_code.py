from __future__ import annotations

import asyncio
import time
import shutil
import sys
import json
import threading
import uuid
from pathlib import Path
from typing import Any, Optional

import psutil

try:
    import claude_agent_sdk as sdk
    HAS_CLAUDE_SDK = True
except ImportError:  # Optional until the Claude Code adapter is selected.
    sdk = None  # type: ignore[assignment]
    HAS_CLAUDE_SDK = False

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

_ALLOWED_TOOLS = [
    "Bash",
    "Edit",
    "Write",
    "Read",
    "Glob",
    "Grep",
    "TodoWrite",
]


class ClaudeCodeAdapter(AgentFrameworkAdapter):
    def __init__(self, model_provider: str = "anthropic"):
        self.model_provider = model_provider
        self._lock = threading.Lock()
        self._active_tasks: dict[str, tuple[asyncio.Task, asyncio.AbstractEventLoop]] = {}

    def execute(
        self, task: TaskManifest, workspace: Path,
        project_root: Optional[Path] = None,
    ) -> AgentResult:
        if not shutil.which("claude"):
            return unavailable_agent_result(
                "claude-code", "the 'claude' executable was not found on PATH"
            )
        if not HAS_CLAUDE_SDK:
            return unavailable_agent_result(
                "claude-code", "the claude_agent_sdk package is not installed"
            )

        import uuid

        session_id = task.session_id or ""
        # When reuse_session is enabled but no session ID is provided, generate
        # a real UUID so the CLI can create a valid session we can later resume.
        is_new_session = False
        if task.reuse_session and not session_id:
            session_id = str(uuid.uuid4())
            is_new_session = True

        # ---- Session length fuse ----
        _SESSION_TOKEN_THRESHOLD = task.session_token_threshold if hasattr(task, 'session_token_threshold') and task.session_token_threshold else DEFAULT_SESSION_TOKEN_THRESHOLD
        if task.reuse_session and session_id and not is_new_session:
            if not self._session_exists(session_id):
                print(
                    f"  [claude_code adapter] Session {session_id} transcript not found; "
                    "forcing new session.",
                    file=sys.stderr, flush=True,
                )
                session_id = str(uuid.uuid4())
                is_new_session = True
            else:
                estimated = self._estimate_session_tokens(session_id)
                if estimated >= _SESSION_TOKEN_THRESHOLD:
                    print(
                        f"  [claude_code adapter] Session {session_id} estimated "
                        f"{estimated} tokens >= {_SESSION_TOKEN_THRESHOLD}; "
                        "forcing new session.",
                        file=sys.stderr, flush=True,
                    )
                    session_id = str(uuid.uuid4())
                    is_new_session = True

        prompt = self._build_claude_prompt(task)
        start = time.time()
        pre_snapshot = set(detect_changed_paths(workspace, working_tree_only=True))

        max_turns = getattr(task, "max_turns_per_session", None) or 30
        # Claude Code only supports Anthropic models.  If the task leaves the
        # model blank, let the CLI pick its own default; otherwise pass through
        # exactly what the user configured.
        model = task.model or ""
        system_prompt = task.context.system_prompt if task.context else ""

        can_use_tool = build_can_use_tool(
            sdk.PermissionResultAllow,
            sdk.PermissionResultDeny,
            task.write_paths or [],
            workspace,
        )

        base_options = {
            "cwd": str(workspace),
            "max_turns": max_turns,
            "allowed_tools": _ALLOWED_TOOLS,
            "system_prompt": system_prompt if system_prompt else None,
            "can_use_tool": can_use_tool,
        }
        if model:
            base_options["model"] = model

        def _attempt(current_sid: str, current_new: bool):
            """Run one Claude Code dispatch. Returns a tuple describing the outcome."""
            record_session_id(project_root, task.feature_id, task.stage, current_sid, run_id=getattr(task, "run_id", ""))
            session_registry.register(task.feature_id, task.stage, current_sid)

            tailer = _SDKSessionTailer(stage=task.stage, agent=task.assigned_agent)
            tailer.start()
            try:
                options = sdk.ClaudeAgentOptions(
                    **base_options,
                    resume=current_sid if not current_new else None,
                    session_id=current_sid if current_new else None,
                )
                effective_timeout = task.timeout if task.timeout else 10800
                result_text, tool_count, cache_read_tokens = asyncio.run(
                    await_with_extendable_timeout(
                        self._run_query(prompt, options, tailer, current_sid), task
                    )
                )
                return ("ok", result_text, tool_count, cache_read_tokens, current_sid)
            except asyncio.TimeoutError:
                return (
                    "timeout", "", 0, 0,
                    "" if current_new else current_sid,
                )
            except Exception as exc:
                err = str(exc)
                # The CLI may lose a session even though its transcript file
                # still exists (aborted/killed sessions). Detect this and give
                # the caller a chance to start a fresh one.
                if "No conversation found" in err and not current_new:
                    return ("session_not_found", err, 0, 0, "")
                return (
                    "error", f"SDK error: {err}", 0, 0,
                    "" if current_new else current_sid,
                )
            finally:
                tailer.stop()

        status, result_text, tool_count, cache_read_tokens, returned_sid = _attempt(
            session_id, is_new_session
        )

        if status == "session_not_found":
            print(
                f"  [claude_code adapter] Session {session_id} not recognized by CLI; "
                "starting a fresh session and retrying.",
                file=sys.stderr, flush=True,
            )
            session_id = str(uuid.uuid4())
            is_new_session = True
            status, result_text, tool_count, cache_read_tokens, returned_sid = _attempt(
                session_id, is_new_session
            )

        if status == "timeout":
            duration = time.time() - start
            return AgentResult(
                success=False,
                files_modified=detect_changed_files(workspace),
                execution_log="",
                tool_calls=[],
                duration_seconds=duration,
                error=f"Timeout after {effective_timeout_seconds(task.timeout_control_path, task.timeout or 10800)}s",
                session_id=returned_sid,
                cache_read_input_tokens=cache_read_tokens,
            )

        if status == "error":
            duration = time.time() - start
            return AgentResult(
                success=False,
                files_modified=detect_changed_files(workspace),
                execution_log=result_text,
                tool_calls=[],
                duration_seconds=duration,
                error=result_text.replace("SDK error: ", ""),
                session_id=returned_sid,
                cache_read_input_tokens=cache_read_tokens,
            )

        # status == "ok": fall through to the normal post-processing below.
        session_id = returned_sid

        duration = time.time() - start
        changed = detect_changed_files(workspace)
        execution_log = f"[claude rc=0 dur={duration:.0f}s]\n"
        execution_log += (result_text or "") + _NL

        output_text = result_text or ""
        class_specs = getattr(task, "_error_class_specs", None) or {}
        # prompt_override (roundtable) runs carry no pipeline error classes;
        # skip inference AND the FAILED fallback so conclusions stay verbatim.
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
            and ("FAILED" in output_text or "SOME TESTS FAILED" in output_text)
            and "Error-Class:" not in output_text
            and "ALL GATES PASSED" not in output_text
        ):
            execution_log += _NL + "Error-Class: dut_error" + _NL
            execution_log += "Error-Class-Reason: agent reported test failures (auto-detected)" + _NL

        success = True
        error = None
        post_paths = set(detect_changed_paths(workspace, working_tree_only=True))
        new_paths = post_paths - pre_snapshot
        bad = violations(new_paths, task.write_paths)
        if bad:
            # Roll back out-of-scope changes so the next retry starts clean
            # and cannot inherit illegal files from this failed run.
            if not task.live_workspace:
                revert_out_of_scope(workspace, project_root, bad, "claude_code")
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

    @staticmethod
    async def _prompt_stream(prompt: str):
        yield {
            "type": "user",
            "session_id": "",
            "message": {"role": "user", "content": prompt},
            "parent_tool_use_id": None,
        }

    async def _run_query(self, prompt: str, options: sdk.ClaudeAgentOptions,
                         tailer: "_SDKSessionTailer", session_id: str = "") -> tuple[str, int, int]:
        chunks: list[str] = []
        result_text: str | None = None
        result_is_error: bool | None = None
        result_stop_reason: str | None = None
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
                if isinstance(message, sdk.AssistantMessage):
                    for block in message.content:
                        if isinstance(block, sdk.TextBlock):
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
                        last_cache_read = usage.get("cache_read_input_tokens", last_cache_read)
                    elif hasattr(usage, "cache_read_input_tokens"):
                        last_cache_read = getattr(usage, "cache_read_input_tokens", last_cache_read)
                elif isinstance(message, sdk.ResultMessage):
                    result_text = getattr(message, "result", None)
        except Exception as exc:
            # The SDK may raise a misleading "Claude Code returned an error
            # result: success" exception when the underlying agent session
            # terminates abnormally.  Do NOT treat this as a successful run:
            # the agent was interrupted mid-task and its output is incomplete.
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
        """Kill any child ``claude`` CLI processes whose command line contains the session ID."""
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
                f"  [claude_code adapter] Permission denied cleaning up children: {exc}",
                file=sys.stderr, flush=True,
            )

    def _estimate_session_tokens(self, session_id: str) -> int:
        """Read the session JSONL log and return the latest
        cache_read_input_tokens seen in any assistant message.
        """
        if not session_id:
            return 0
        try:
            matches = list(Path.home().glob(f".claude/projects/*/{session_id}.jsonl"))
            for log_path in matches:
                last_cache = 0
                with open(log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        d = json.loads(line)
                        if d.get("type") == "assistant":
                            msg = d.get("message", {})
                            usage = msg.get("usage", {}) or {}
                            cr = usage.get("cache_read_input_tokens", 0)
                            if cr:
                                last_cache = cr
                return last_cache
        except Exception:
            pass
        return 0

    @staticmethod
    def _session_file_path(session_id: str) -> Path | None:
        """Return the path to a Claude session JSONL if it exists, else None."""
        if not session_id:
            return None
        try:
            matches = list(Path.home().glob(f".claude/projects/*/{session_id}.jsonl"))
            return matches[0] if matches else None
        except Exception:
            return None

    def _session_exists(self, session_id: str) -> bool:
        """True if Claude has a transcript file for this session_id."""
        path = self._session_file_path(session_id)
        return path is not None and path.is_file()

    def _build_claude_prompt(self, task: TaskManifest) -> str:
        if task.prompt_override is not None:
            return task.prompt_override
        if task.reuse_session and task.session_id:
            return build_continuation_prompt(task)
        return build_agent_prompt(task)


class _SDKSessionTailer:
    """Real-time progress display for SDK-based agent sessions.

    Unlike _SessionTailer (which polled JSONL files), this receives tool
    use events directly from the SDK's message stream — no filesystem I/O,
    no race conditions with session log writes.
    """

    _TOOL_LABELS = {
        "Read": "Reading",
        "Write": "Writing",
        "Edit": "Editing",
        "Bash": "Running",
        "Glob": "Searching",
        "Grep": "Searching",
        "Task": "Planning",
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
                file=sys.stderr, flush=True,
            )

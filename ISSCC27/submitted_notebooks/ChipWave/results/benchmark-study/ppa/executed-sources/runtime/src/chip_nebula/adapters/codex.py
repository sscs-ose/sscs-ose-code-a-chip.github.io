import json
import os
import shutil
import subprocess
import sys
import threading
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from chip_nebula.models.task_manifest import TaskManifest, AgentResult
from chip_nebula.adapters.base import (
    AgentFrameworkAdapter,
    automatic_error_inference_enabled,
    build_agent_prompt,
    build_continuation_prompt,
    detect_changed_files,
    record_session_id,
    revert_out_of_scope,
    session_registry,
    terminate_process_tree,
    unavailable_agent_result,
    wait_for_process_with_extendable_timeout,
)
from chip_nebula.adapters.scope_check import (
    detect_changed_paths,
    format_scope_violation_log,
    violations,
)
from chip_nebula.adapters.error_class_inference import infer_error_class
from chip_nebula.taskgraph_run_controls import (
    clear_run_process,
    effective_timeout_seconds,
    record_run_process,
)

_NL = chr(10)


class CodexAdapter(AgentFrameworkAdapter):
    """Adapter that drives the OpenAI Codex CLI.

    Codex is invoked as a subprocess (``codex exec``) with structured JSONL
    output (``--json``).  It supports non-interactive agent execution, session
    resume, and model selection, mirroring the OpenCode adapter's shape so that
    pipeline/roundtable code needs no special casing.

    A missing binary, authentication failure, or network failure is returned as
    a real execution failure. Mock execution is only available when callers
    explicitly select the mock framework.
    """

    def __init__(self, model_provider: str = "openai"):
        self.model_provider = model_provider
        self._lock = threading.Lock()
        self._active: dict[str, subprocess.Popen] = {}

    def execute(
        self, task: TaskManifest, workspace: Path,
        project_root: Optional[Path] = None,
    ) -> AgentResult:
        if not shutil.which("codex"):
            return unavailable_agent_result(
                "codex", "the 'codex' executable was not found on PATH"
            )

        session_id = task.session_id or ""
        is_new_session = False
        # Codex's ``resume`` subcommand only resumes an existing session.  If the
        # requested id does not exist on disk, drop it and start fresh.
        if task.reuse_session and session_id and not self._session_exists(session_id):
            print(
                f"  [codex adapter] Session {session_id} not found in codex store; "
                "starting a new session.",
                file=sys.stderr, flush=True,
            )
            session_id = ""
            is_new_session = True
        elif task.reuse_session and not session_id:
            is_new_session = True

        # New Codex sessions reveal their real UUID only after the process emits
        # the first JSON event, so track the in-flight subprocess with a
        # placeholder key and swap it for the real id once parsed.
        # ``run_id`` is known before the subprocess starts and is therefore the
        # only reliable cancellation handle while a new Codex session has not
        # emitted its UUID yet.  Keep it registered for the whole execution;
        # the session UUID is an additional alias, not a replacement.
        tracking_key = session_id or task.run_id or f"codex-{task.stage}-{uuid.uuid4().hex[:8]}"
        session_registry.register(task.feature_id, task.stage, tracking_key)
        if session_id:
            record_session_id(project_root, task.feature_id, task.stage, session_id, run_id=getattr(task, "run_id", ""))

        # _build_prompt decides continuation vs fresh based on task.session_id.
        task.session_id = session_id
        prompt = self._build_prompt(task)
        start = time.time()
        pre_snapshot = set(detect_changed_paths(workspace, working_tree_only=True))

        timeout = task.timeout if task.timeout else 10800

        # Codex has no native system-prompt flag.  We inject the project-level
        # system prompt as a leading developer message by prepending it to the
        # user prompt, wrapped so Codex still treats the task body as the primary
        # instruction.
        system_prompt = (task.context.system_prompt if task.context else "") or ""
        effective_prompt = prompt
        if system_prompt.strip():
            effective_prompt = (
                f"[Project system instructions]\n{system_prompt.strip()}\n\n"
                f"[Task]\n{prompt}"
            )

        # Base command.  ``--dangerously-bypass-approvals-and-sandbox`` is
        # required for non-interactive use; the pipeline worktree is already an
        # isolated git worktree so this matches how OpenCode/Claude Code are
        # used by the platform.
        cmd = [
            "codex",
            "exec",
            "--json",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "--cd", str(workspace),
        ]
        model = task.model or ""
        if model:
            cmd.extend(["--model", model])
        reasoning_effort = (task.reasoning_effort or "").strip().lower()
        if reasoning_effort:
            if reasoning_effort not in {"low", "medium", "high", "xhigh", "max", "ultra"}:
                return AgentResult(
                    success=False,
                    error=f"Unsupported Codex reasoning effort: {reasoning_effort}",
                    execution_log=(
                        "Error-Class: configuration\n"
                        f"Error-Class-Reason: unsupported Codex reasoning effort {reasoning_effort}"
                    ),
                )
            cmd.extend([
                "--config", f'model_reasoning_effort="{reasoning_effort}"',
            ])

        if session_id and not is_new_session:
            cmd.extend(["resume", session_id])

        cmd.append("-")

        # Codex inherits ``PWD`` from the parent shell, which is the project root
        # when ``chip-nebula run`` is launched from there.  ``--cd`` above tells
        # the agent its workspace root; also set cwd defensively.
        # A corrected whole-workflow brief can exceed the OS limit for one argv entry.
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as prompt_input:
            prompt_input.write(effective_prompt)
            prompt_input.seek(0)
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=prompt_input,
                text=True,
                cwd=workspace,
                env=os.environ,
                start_new_session=(os.name == "posix"),
            )
        record_run_process(task.timeout_control_path, proc.pid)
        with self._lock:
            self._active[tracking_key] = proc

        lines: list[str] = []
        real_id: list[str] = [""]

        def _drain() -> None:
            for line in proc.stdout:
                lines.append(line.rstrip("\n"))
                if not real_id[0]:
                    sid = self._extract_session_id(line)
                    if sid:
                        real_id[0] = sid
                        with self._lock:
                            self._active[sid] = proc
                        session_registry.register(task.feature_id, task.stage, sid)
                        record_session_id(project_root, task.feature_id, task.stage, sid, run_id=getattr(task, "run_id", ""))

        reader = threading.Thread(target=_drain, daemon=True)
        reader.start()

        try:
            wait_for_process_with_extendable_timeout(proc, task)
            reader.join(timeout=10)
            duration = time.time() - start
            success = proc.returncode == 0
            changed = detect_changed_files(workspace)

            real_session_id, execution_log = self._parse_codex_json("\n".join(lines))
            if real_session_id and real_session_id != session_id:
                session_id = real_session_id
                record_session_id(project_root, task.feature_id, task.stage, session_id, run_id=getattr(task, "run_id", ""))
                session_registry.register(task.feature_id, task.stage, session_id)
            if not execution_log:
                execution_log = "\n".join(lines) or ""

            # Codex session JSONL only records the initial user prompt.  Write a
            # synthetic assistant entry with the final conclusion so the dashboard
            # session panel can show the full turn, like Claude Code / Qoder.
            if session_id and execution_log:
                self._append_session_message(session_id, execution_log)

            error = None if success else execution_log

            class_specs = getattr(task, "_error_class_specs", None) or {}
            inferred = (
                infer_error_class(execution_log, class_specs)
                if automatic_error_inference_enabled(task) else None
            )
            if inferred:
                inferred_class, inferred_reason = inferred
                execution_log += _NL + f"Error-Class: {inferred_class}" + _NL
                execution_log += (
                    f"Error-Class-Reason: {inferred_reason} (auto-detected)" + _NL
                )

            if success:
                post_paths = set(detect_changed_paths(workspace, working_tree_only=True))
                new_paths = post_paths - pre_snapshot
                bad = violations(new_paths, task.write_paths)
                if bad:
                    if not task.live_workspace:
                        revert_out_of_scope(workspace, project_root, bad, "codex")
                    success = False
                    execution_log += format_scope_violation_log(bad, task.write_paths)
                    error = (
                        f"Scope violation: {len(bad)} path(s) outside write_paths"
                    )

            return AgentResult(
                success=success,
                files_modified=changed,
                execution_log=execution_log,
                tool_calls=self._parse_tool_calls(execution_log),
                duration_seconds=duration,
                error=error,
                session_id=session_id,
            )
        except subprocess.TimeoutExpired:
            cleanup_complete = self._terminate_popen(proc)
            reader.join(timeout=10)
            duration = time.time() - start
            collected = "\n".join(lines)
            real_session_id, execution_log = self._parse_codex_json(collected)
            returned_session_id = real_session_id or ("" if is_new_session else session_id)
            # The CLI can emit its authoritative completion event at the exact
            # timeout boundary before the wrapper process exits.  Preserve that
            # completed turn instead of reporting a false timeout after the RTL
            # and its self-checks have already finished.
            if self._turn_completed(collected):
                execution_log = execution_log or collected
                if returned_session_id and execution_log:
                    self._append_session_message(returned_session_id, execution_log)
                post_paths = set(detect_changed_paths(workspace, working_tree_only=True))
                bad = violations(post_paths - pre_snapshot, task.write_paths)
                error = None
                success = True
                if bad:
                    if not task.live_workspace:
                        revert_out_of_scope(workspace, project_root, bad, "codex")
                    success = False
                    execution_log += format_scope_violation_log(bad, task.write_paths)
                    error = f"Scope violation: {len(bad)} path(s) outside write_paths"
                return AgentResult(
                    success=success,
                    files_modified=detect_changed_files(workspace),
                    execution_log=execution_log,
                    tool_calls=self._parse_tool_calls(execution_log),
                    duration_seconds=duration,
                    error=error,
                    session_id=returned_session_id,
                )
            return AgentResult(
                success=False,
                files_modified=detect_changed_files(workspace),
                execution_log=collected,
                tool_calls=[],
                duration_seconds=duration,
                error=(
                    f"Timeout after {effective_timeout_seconds(task.timeout_control_path, timeout)}s"
                    + ("" if cleanup_complete else "; process tree cleanup incomplete")
                ),
                session_id=returned_session_id,
            )
        except BaseException:
            # KeyboardInterrupt, process-owner shutdown and cancellation must
            # not orphan a long-running Codex/OpenROAD child under PID 1.
            self._terminate_popen(proc)
            reader.join(timeout=10)
            raise
        finally:
            clear_run_process(task.timeout_control_path, proc.pid)
            with self._lock:
                self._active.pop(tracking_key, None)
                self._active.pop(session_id, None)

    def terminate(self, session_id: str) -> None:
        """Best-effort terminate the Codex subprocess for ``session_id``."""
        if not session_id:
            return None
        with self._lock:
            proc = self._active.pop(session_id, None)
        if proc is None:
            return None
        self._terminate_popen(proc)
        return None

    @staticmethod
    def _session_exists(session_id: str) -> bool:
        """True if Codex has persisted a session with this id."""
        return CodexAdapter._session_file_path(session_id) is not None

    @staticmethod
    def _session_file_path(session_id: str) -> Optional[Path]:
        """Return the path to a Codex session JSONL if it exists, else None.

        Codex stores sessions under ``~/.codex/sessions/YYYY/MM/DD/`` with a
        filename like ``<name>-<uuid>.jsonl``.  The session id is the trailing
        UUID.
        """
        if not session_id:
            return None
        try:
            matches = list(
                Path.home().glob(f".codex/sessions/*/*/*/*-{session_id}.jsonl")
            )
            return matches[0] if matches else None
        except Exception:
            return None

    def _estimate_session_tokens(self, session_id: str) -> int:
        """Estimate session size from the Codex JSONL log.

        Codex session files do not currently expose per-message token usage, so
        we approximate from file size (bytes / 4 chars per token), matching the
        generic fallback used elsewhere.
        """
        path = self._session_file_path(session_id)
        if path is None:
            return 0
        try:
            return path.stat().st_size // 4
        except OSError:
            return 0

    @staticmethod
    def _append_session_message(session_id: str, text: str) -> None:
        """Append a synthetic assistant entry to the Codex session JSONL.

        Codex transcripts persist the user prompt but not the agent's final
        conclusion.  Writing it back lets the dashboard display the full private
        turn.  The entry format mirrors Codex's native event envelope
        (``timestamp``, ``type``, ``payload``) so ``_parse_session_transcript``
        can render it.
        """
        if not session_id or not text:
            return
        path = CodexAdapter._session_file_path(session_id)
        if path is None:
            return
        try:
            has_assistant = False
            if path.is_file():
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            d = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        # Codex uses ``response_item`` events with role=assistant
                        # inside the payload for assistant turns.
                        if d.get("type") == "response_item":
                            payload = d.get("payload", {})
                            if payload.get("role") == "assistant":
                                has_assistant = True
                                break
            if has_assistant:
                return
            entry = {
                "timestamp": datetime.now().isoformat(timespec="seconds") + "Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "input_text", "text": text.strip()}],
                },
            }
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    @staticmethod
    def _extract_session_id(line: str) -> str:
        """Return the session id from a single Codex JSON event line."""
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            return ""
        # Current Codex emits ``thread.started`` with a top-level
        # ``thread_id``.  Older releases used a ``session_meta`` payload.
        thread_id = evt.get("thread_id") or ""
        if thread_id:
            return thread_id
        payload = evt.get("payload") or {}
        sid = payload.get("session_id") or payload.get("id") or ""
        if sid:
            return sid
        return evt.get("session_id") or ""

    @staticmethod
    def _parse_codex_json(stdout: str) -> tuple[str, str]:
        """Return (session_id, final_conclusion) from ``codex exec --json`` NDJSON.

        Codex structured output is a stream of events.  We are interested in:
          - ``session_meta`` / ``event_msg`` for the session id.
          - ``response_item`` payload messages carrying assistant text.

        Because the exact public schema is still stabilizing, the parser is
        defensive: it collects any text it can find and falls back to the raw
        concatenated output when no structured text is present.
        """
        session_id = ""
        final_text = ""
        last_tool_summary = ""
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue

            payload = evt.get("payload") or {}
            typ = evt.get("type") or payload.get("type") or ""

            sid = (
                evt.get("thread_id")
                or payload.get("thread_id")
                or payload.get("session_id")
                or payload.get("id")
                or evt.get("session_id")
                or ""
            )
            if sid and not session_id:
                session_id = sid

            item = evt.get("item") or {}
            if typ == "item.completed" and item.get("type") == "agent_message":
                text = item.get("text") or ""
                if isinstance(text, str) and text.strip():
                    final_text = text.strip()
            elif typ == "item.completed" and item.get("type") == "command_execution":
                command = item.get("command") or ""
                if isinstance(command, str) and command.strip():
                    last_tool_summary = f"[tool] command: {command[:120]}"
            elif typ in ("text", "message"):
                content = payload.get("content") or evt.get("content") or []
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            txt = (
                                block.get("text")
                                or block.get("thinking")
                                or block.get("value")
                                or ""
                            )
                            if isinstance(txt, str) and txt.strip():
                                final_text = txt.strip()
                elif isinstance(content, str) and content.strip():
                    final_text = content.strip()
            elif typ in ("tool_use", "tool_call"):
                tool = payload.get("tool") or payload.get("name") or "?"
                inp = payload.get("input") or payload.get("arguments") or {}
                detail = CodexAdapter._tool_input_summary(tool, inp)
                last_tool_summary = f"[tool] {tool}" + (f": {detail}" if detail else "")

        return session_id, final_text or last_tool_summary

    @staticmethod
    def _turn_completed(stdout: str) -> bool:
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = event.get("payload") or {}
            if (event.get("type") or payload.get("type")) == "turn.completed":
                return True
        return False

    @staticmethod
    def _tool_input_summary(tool: str, inp: dict) -> str:
        if tool == "bash":
            return str(inp.get("command", ""))[:120]
        if tool in ("write", "edit"):
            return str(inp.get("file_path") or inp.get("filePath") or "")
        if tool == "read":
            return str(inp.get("file_path") or "")
        return ""

    @staticmethod
    def _terminate_popen(proc: subprocess.Popen, timeout: float = 5) -> bool:
        return terminate_process_tree(proc, timeout=timeout)

    def _build_prompt(self, task: TaskManifest) -> str:
        if task.prompt_override is not None:
            return task.prompt_override
        if task.reuse_session and task.session_id:
            return build_continuation_prompt(task)
        return build_agent_prompt(task)

    def _parse_tool_calls(self, log: str) -> list[dict]:
        return []

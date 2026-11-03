import json
import os
import subprocess
import sys
import threading
import time
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from chip_nebula.models.task_manifest import TaskManifest, AgentResult, FileTarget
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


class OpenCodeAdapter(AgentFrameworkAdapter):
    def __init__(self, model_provider: str = "deepseek"):
        self.model_provider = model_provider
        self._lock = threading.Lock()
        self._active: dict[str, subprocess.Popen] = {}

    def execute(
        self, task: TaskManifest, workspace: Path,
        project_root: Optional[Path] = None,
    ) -> AgentResult:
        if not shutil.which("opencode"):
            return unavailable_agent_result(
                "opencode", "the 'opencode' executable was not found on PATH"
            )

        session_id = task.session_id or ""
        is_new_session = False
        # opencode's `--session` only RESUMES an existing session; it can never
        # create one. So never fabricate an id: if we have a prior id, verify it
        # actually exists in opencode's store; otherwise start fresh.
        if task.reuse_session and session_id and not self._session_exists(session_id):
            print(
                f"  [opencode adapter] Session {session_id} not found in opencode; "
                "starting a new session.",
                file=sys.stderr, flush=True,
            )
            session_id = ""
            is_new_session = True
        elif task.reuse_session and not session_id:
            is_new_session = True

        # ``tracking_key`` is used only for terminate() bookkeeping while the
        # subprocess runs. A brand-new session does not reveal its real id until
        # opencode emits it, so use a placeholder key for new sessions and swap
        # in the real id once we parse it from the JSON output.
        tracking_key = session_id or f"opencode-{task.stage}-{uuid.uuid4().hex[:8]}"
        session_registry.register(task.feature_id, task.stage, tracking_key)
        if session_id:
            record_session_id(project_root, task.feature_id, task.stage, session_id, run_id=getattr(task, "run_id", ""))

        # _build_prompt selects the continuation prompt based on task.session_id,
        # so align it with the effective session state (empty = fresh prompt).
        task.session_id = session_id
        prompt = self._build_prompt(task)
        start = time.time()
        pre_snapshot = set(detect_changed_paths(workspace, working_tree_only=True))

        timeout = task.timeout if task.timeout else 10800
        # opencode has no --system-prompt flag; the native mechanism is an
        # agent whose markdown body becomes the system prompt. Inject one
        # per-invocation via OPENCODE_CONFIG_CONTENT and select it with --agent.
        system_prompt = (task.context.system_prompt if task.context else "") or ""
        agent_name = ""
        extra_env: dict[str, str] = {}
        if system_prompt.strip():
            agent_name = "chip-nebula"
            config = {
                "agent": {agent_name: {"mode": "primary", "prompt": system_prompt.strip()}}
            }
            extra_env["OPENCODE_CONFIG_CONTENT"] = json.dumps(config)

        # --format json emits the real session id plus structured events we parse
        # below, so new sessions can be captured for a later resume.
        # `--dir` is REQUIRED: opencode's run command resolves its working
        # directory from `process.env.PWD ?? process.cwd()`, and `PWD` is
        # inherited from the shell that launched `chip-nebula run` (the project
        # root), NOT our subprocess `cwd` (the worktree). Without `--dir` the
        # agent operates on the project root and does meaningless work there.
        cmd = ["opencode", "run", "--auto", "--format", "json", "--dir", str(workspace)]
        if agent_name:
            cmd.extend(["--agent", agent_name])
        if session_id:
            cmd.extend(["--session", session_id])
        model = task.model or ""
        provider = task.model_provider or self.model_provider
        if model:
            model_spec = f"{provider}/{model}" if provider else model
            cmd.extend(["--model", model_spec])
        cmd.append(prompt)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=workspace,
            env={**os.environ, **extra_env},
            start_new_session=(os.name == "posix"),
        )
        record_run_process(task.timeout_control_path, proc.pid)
        with self._lock:
            self._active[tracking_key] = proc

        # Drain stdout on a background thread so we can capture the real session
        # id the moment opencode emits its first event, and publish it to the
        # sidecar/registry. Otherwise the dashboard transcript stays empty for
        # the whole run (the id would only be known after the process exits).
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
                            if self._active.pop(tracking_key, None) is not None:
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

            real_session_id, execution_log = self._parse_opencode_json("\n".join(lines))
            if real_session_id and real_session_id != session_id:
                session_id = real_session_id
                record_session_id(project_root, task.feature_id, task.stage, session_id, run_id=getattr(task, "run_id", ""))
                session_registry.register(task.feature_id, task.stage, session_id)
            if not execution_log:
                execution_log = "\n".join(lines) or ""
            # The OpenCode CLI only writes the user prompt to its session JSONL;
            # append the assistant's final reply so the dashboard's right-hand
            # session panel can display the full turn.
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
                        revert_out_of_scope(workspace, project_root, bad, "opencode")
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
            real_session_id, _ = self._parse_opencode_json(collected)
            returned_session_id = real_session_id or ("" if is_new_session else session_id)
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
        finally:
            clear_run_process(task.timeout_control_path, proc.pid)
            with self._lock:
                self._active.pop(tracking_key, None)
                self._active.pop(session_id, None)

    def terminate(self, session_id: str) -> None:
        """Best-effort terminate the OpenCode subprocess for ``session_id``."""
        if not session_id:
            return None
        with self._lock:
            proc = self._active.pop(session_id, None)
        if proc is None:
            return None
        self._terminate_popen(proc)
        return None

    def _session_exists(self, session_id: str) -> bool:
        """True if opencode's store has a session with this exact id."""
        if not session_id:
            return False
        try:
            out = subprocess.run(
                ["opencode", "session", "list"],
                capture_output=True, text=True, timeout=15,
            )
            for line in out.stdout.splitlines():
                if line.split() and line.split()[0] == session_id:
                    return True
        except Exception:
            return False
        return False

    @staticmethod
    def _append_session_message(session_id: str, text: str) -> None:
        """Append an assistant message to the OpenCode session JSONL.

        OpenCode's native transcript only records the initial user prompt.
        Writing the assistant reply back to the same JSONL lets the dashboard
        session viewer show the full private turn alongside Claude Code/Qoder.
        The append is skipped if the transcript already contains an assistant
        entry (e.g. newer OpenCode versions or an earlier adapter run).
        """
        if not session_id or not text:
            return
        for base in (".claude/transcripts",):
            for path in Path.home().glob(f"{base}/{session_id}.jsonl"):
                try:
                    has_assistant = False
                    if path.is_file():
                        with open(path, "r") as f:
                            for line in f:
                                if not line.strip():
                                    continue
                                try:
                                    if json.loads(line).get("type") == "assistant":
                                        has_assistant = True
                                        break
                                except json.JSONDecodeError:
                                    continue
                    if has_assistant:
                        return
                    entry = {
                        "type": "assistant",
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                        "message": {
                            "role": "assistant",
                            "content": [{"type": "text", "text": text.strip()}],
                        },
                    }
                    with open(path, "a") as f:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    return
                except OSError:
                    pass

    @staticmethod
    def _extract_session_id(line: str) -> str:
        """Return the ``sessionID`` from a single opencode JSON event line."""
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            return ""
        return evt.get("sessionID") or ""

    @staticmethod
    def _parse_opencode_json(stdout: str) -> tuple[str, str]:
        """Return (session_id, final_conclusion) from opencode `--format json` NDJSON.

        A run is a sequence of steps: ``step_start`` → (``text`` | ``tool_use``)…
        → ``step_finish``. A ``text`` event carries a WHOLE assistant message
        (not streamed chunks), so the last ``text`` event is the agent's final
        conclusion — the same thing Claude Code's SDK surfaces as
        ``ResultMessage.result``. We keep only that and drop the intermediate
        tool chatter, so the execution log stays as clean as Claude Code's.
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
            sid = evt.get("sessionID") or ""
            if sid and not session_id:
                session_id = sid
            typ = evt.get("type")
            part = evt.get("part") or {}
            if typ == "text" or part.get("type") == "text":
                txt = part.get("text") or ""
                if txt.strip():
                    final_text = txt
            elif typ == "tool_use" or part.get("type") == "tool":
                tool = part.get("tool") or "?"
                state = part.get("state") or {}
                inp = state.get("input") or {}
                # ``title`` lives on ``state``, not ``part`` (verified on 1.18.15).
                title = state.get("title") or ""
                detail = title or OpenCodeAdapter._tool_input_summary(tool, inp)
                last_tool_summary = f"[tool] {tool}" + (f": {detail}" if detail else "")
        return session_id, final_text or last_tool_summary

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

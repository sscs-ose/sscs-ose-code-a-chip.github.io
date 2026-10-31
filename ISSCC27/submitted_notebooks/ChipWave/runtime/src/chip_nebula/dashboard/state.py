from __future__ import annotations

import json
import subprocess
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml
from ansi2html import Ansi2HTMLConverter

from chip_nebula.project import (
    find_project_root,
    get_agents_dir,
    get_chip_nebula_dir,
    get_pipelines_dir,
    get_worktrees_dir,
    infer_module_from_pipeline_path,
    load_agent_config,
    normalize_project_root,
    worktree_has_uncommitted_changes,
)
from chip_nebula.workspace.manager import WorkspaceManager


_ansi_converter = Ansi2HTMLConverter(inline=True)


def resolve_project_root(project_root: Optional[str | Path] = None) -> Path:
    if project_root is not None:
        return normalize_project_root(project_root)
    root = find_project_root()
    if root is None:
        raise FileNotFoundError("Not inside a Chip Nebula project")
    return root


def ansi_to_html(text: str) -> str:
    return _ansi_converter.convert(text, full=False)


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def list_workspaces(project_root: Path) -> list[dict[str, Any]]:
    wm = WorkspaceManager(project_root=project_root)
    worktree_root = get_worktrees_dir(project_root)
    result: list[dict[str, Any]] = []

    for feature_id in wm.list_workspaces():
        ws_path = worktree_root / feature_id
        branch = ""
        branch_res = _run_git(["symbolic-ref", "--short", "HEAD"], cwd=ws_path)
        if branch_res.returncode == 0:
            branch = branch_res.stdout.strip()

        state = read_pipeline_state(project_root, feature_id)
        stage_status = state.get("stage_status", {})
        if not stage_status:
            run_status = "idle"
        elif any(s == "failed" for s in stage_status.values()):
            run_status = "failed"
        elif any(s == "running" for s in stage_status.values()):
            run_status = "running"
        elif all(s == "passed" for s in stage_status.values()):
            run_status = "passed"
        else:
            run_status = "pending"

        result.append(
            {
                "id": feature_id,
                "branch": branch,
                "dirty": worktree_has_uncommitted_changes(ws_path),
                "current_stage": state.get("current_stage", ""),
                "run_status": run_status,
                "last_updated": state.get("last_updated", ""),
                "pipeline": state.get("pipeline", ""),
                "run_id": state.get("run_id", ""),
            }
        )

    return result


def _list_config_tree(base_dir: Path) -> dict[str, list[str]]:
    if not base_dir.exists():
        return {}
    result: dict[str, list[str]] = {}
    for child in sorted(base_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("_"):
            continue
        files = sorted(
            f.name for f in child.iterdir()
            if f.is_file() and f.suffix in (".yaml", ".yml") and not f.name.startswith("_")
        )
        if files:
            result[child.name] = files
    return result


def list_pipelines(project_root: Path) -> dict[str, list[str]]:
    return _list_config_tree(get_pipelines_dir(project_root))


def list_agents(project_root: Path) -> dict[str, list[str]]:
    return _list_config_tree(get_agents_dir(project_root))


def read_pipeline_state(project_root: Path, feature_id: str) -> dict[str, Any]:
    state_file = get_worktrees_dir(project_root) / feature_id / ".pipeline_state.json"
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _load_stages_from_file(path: Path) -> dict[str, Any]:
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return {}
    return data.get("stages", {})


def _find_pipeline_file_by_name(project_root: Path, name: str) -> Optional[Path]:
    pipelines_dir = get_pipelines_dir(project_root)
    if not pipelines_dir.exists():
        return None
    for path in pipelines_dir.rglob("*.yaml"):
        if any(part.startswith("_") for part in path.relative_to(pipelines_dir).parts):
            continue
        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            continue
        if data.get("name") == name:
            return path
    return None


def resolve_pipeline_file(project_root: Path, feature_id: str) -> Optional[Path]:
    """Locate the pipeline YAML file backing a feature run: prefer the
    recorded pipeline_path, fall back to searching by pipeline name."""
    state = read_pipeline_state(project_root, feature_id)
    pipeline_path = state.get("pipeline_path", "")
    if pipeline_path:
        path = Path(pipeline_path)
        if not path.is_absolute():
            path = project_root / path
        if path.exists():
            return path

    pipeline_name = state.get("pipeline", "")
    if pipeline_name:
        path = _find_pipeline_file_by_name(project_root, pipeline_name)
        if path and path.exists():
            return path

    return None


def read_pipeline_definition(project_root: Path, feature_id: str) -> dict[str, Any]:
    path = resolve_pipeline_file(project_root, feature_id)
    if path is None:
        return {}
    return _load_stages_from_file(path)


def read_stage_log(
    project_root: Path, feature_id: str, run_id: str, stage_name: str
) -> dict[str, Any]:
    artifact_dir = _artifact_dir(project_root, feature_id, run_id)
    if artifact_dir is None:
        return {"execution_log": "", "gate_reports": [], "files_modified": []}

    candidates = [
        artifact_dir / f"{stage_name}.iter-{n}.json"
        for n in range(1, 100)
    ]
    candidates.append(artifact_dir / f"{stage_name}.json")

    # Return the LATEST artifact (highest iteration), not the earliest.
    for candidate in reversed(candidates):
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            return {
                "execution_log": ansi_to_html(data.get("execution_log", "")),
                "gate_reports": data.get("gate_reports", []),
                "files_modified": data.get("files_modified", []),
                "iteration": data.get("iteration", 0),
                "passed": data.get("passed", False),
                "timestamp": data.get("timestamp", ""),
            }

    return {"execution_log": "", "gate_reports": [], "files_modified": []}


def _artifact_dir(
    project_root: Path, feature_id: str, run_id: str
) -> Optional[Path]:
    state = read_pipeline_state(project_root, feature_id)
    pipeline = state.get("pipeline", "")
    if not pipeline:
        return None
    memory_dir = get_chip_nebula_dir(project_root) / "shared" / "memory"
    candidate = memory_dir / "artifacts" / pipeline / run_id
    if candidate.exists():
        return candidate
    return None


def inject_intervention(
    project_root: Path,
    feature_id: str,
    stage: str,
    text: str,
    kind: str = "user_feedback",
) -> None:
    state_file = get_worktrees_dir(project_root) / feature_id / ".pipeline_state.json"
    state: dict[str, Any] = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
        except (json.JSONDecodeError, OSError):
            state = {}

    pending = state.setdefault("pending_failure_contexts", {})
    pending[stage] = {
        "source_stage": "user",
        "error_class": kind,
        "error_class_reason": text,
        "execution_log": "",
        "errors": [],
        "previous_attempts": [],
        "modified_files": [],
        "iteration_count": 0,
    }
    state["last_updated"] = datetime.now().isoformat()
    state_file.write_text(json.dumps(state, indent=2, default=str))


def read_yaml_file(project_root: Path, relative_path: str) -> Optional[str]:
    target = get_chip_nebula_dir(project_root) / relative_path
    try:
        target.relative_to(get_chip_nebula_dir(project_root))
    except ValueError:
        return None
    if not target.exists() or not target.is_file():
        return None
    return target.read_text()


def _resolve_stage_agent_path(
    project_root: Path, feature_id: str, stage_name: str
) -> Optional[Path]:
    state = read_pipeline_state(project_root, feature_id)
    stages = read_pipeline_definition(project_root, feature_id)
    stage = stages.get(stage_name, {})
    agent_type = stage.get("agent", "")
    if not agent_type:
        return None

    pipeline_path = state.get("pipeline_path", "")
    module = None
    if pipeline_path:
        module = infer_module_from_pipeline_path(pipeline_path, project_root)
    if module is None:
        pipeline_name = state.get("pipeline", "")
        path = _find_pipeline_file_by_name(project_root, pipeline_name)
        if path:
            module = infer_module_from_pipeline_path(path, project_root)

    agents_dir = get_agents_dir(project_root)
    candidates: list[Path] = []
    if module:
        candidates.append(agents_dir / module / f"{agent_type}.yaml")
    candidates.append(agents_dir / "common" / f"{agent_type}.yaml")
    candidates.append(agents_dir / f"{agent_type}.yaml")

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_stage_agent_config(
    project_root: Path, feature_id: str, stage_name: str
) -> dict[str, Any]:
    path = _resolve_stage_agent_path(project_root, feature_id, stage_name)
    if path is None:
        return {}
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _pretty_str_representer(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


class _PrettyYamlDumper(yaml.SafeDumper):
    pass


_PrettyYamlDumper.add_representer(str, _pretty_str_representer)


def update_stage_agent_config(
    project_root: Path,
    feature_id: str,
    stage_name: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    path = _resolve_stage_agent_path(project_root, feature_id, stage_name)
    if path is None:
        raise FileNotFoundError("Agent config not found for this stage")

    agents_dir = get_agents_dir(project_root)
    try:
        path.relative_to(agents_dir)
    except ValueError as exc:
        raise ValueError("Invalid agent config path") from exc

    with open(path) as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        data = {}

    if "system_prompt_template" in updates:
        data["system_prompt_template"] = updates["system_prompt_template"]

    write_value = updates.get("write_paths")
    if write_value is not None:
        if isinstance(write_value, list):
            if "write_path" in data:
                del data["write_path"]
            data["write_paths"] = write_value
        else:
            data["write_path"] = write_value
            if "write_paths" in data:
                del data["write_paths"]

    with open(path, "w") as f:
        yaml.dump(
            data,
            f,
            Dumper=_PrettyYamlDumper,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )

    return data


def _find_session_file(session_id: str) -> Optional[Path]:
    """Locate the JSONL transcript for a session across all frameworks.

    Claude Code  → ~/.claude/projects/<slug>/<id>.jsonl
    Qoder CLI    → ~/.qoder/projects/<slug>/<id>.jsonl
    OpenCode     → ~/.claude/transcripts/<id>.jsonl  (flat, no project subdir)
    """
    if not session_id:
        return None
    # Project-based storage (Claude Code, Qoder): one directory per project
    for base in (".claude/projects", ".qoder/projects"):
        for path in Path.home().glob(f"{base}/*/{session_id}.jsonl"):
            if path.is_file():
                return path
    # Flat storage (OpenCode): transcripts sit directly under the directory
    for base in (".claude/transcripts",):
        for path in Path.home().glob(f"{base}/{session_id}.jsonl"):
            if path.is_file():
                return path
    # Codex date-based storage
    for path in Path.home().glob(f".codex/sessions/*/*/*/*-{session_id}.jsonl"):
        if path.is_file():
            return path
    return None


def _parse_session_transcript(path: Path, max_chars: int = 1_000_000) -> list[dict[str, str]]:
    """Parse a session JSONL transcript into UI-displayable messages.

    Handles three transcript formats:
      - Claude Code / Qoder: ``type=user`` with ``message.content`` (str),
        ``type=assistant`` with ``message.content`` (list of blocks).
      - OpenCode: ``type=user`` with flat ``content`` (str),
        ``type=tool_use`` / ``tool_result`` (no assistant blocks).
        Tool calls are rendered as synthetic assistant messages.
      - Codex: ``type=response_item`` with ``payload.role`` and
        ``payload.content`` (list of blocks).  Tool calls are rendered as
        synthetic assistant messages.
    """
    if max_chars <= 0:
        return []
    messages: deque[dict[str, str]] = deque()
    total = 0
    event_timestamp = ""

    def append(role: str, content: str, *, kind: str = "message", title: str = "") -> None:
        nonlocal total
        content = content.strip()[-max_chars:]
        if not content:
            return
        item: dict[str, str] = {"role": role, "content": content}
        if event_timestamp:
            item["timestamp"] = event_timestamp
        if kind != "message":
            item["kind"] = kind
        if title:
            item["title"] = title
        messages.append(item)
        total += len(content)
        while total > max_chars:
            total -= len(messages.popleft()["content"])
    try:
        # Read a bounded tail so long resumed sessions expose current progress.
        with path.open("r", encoding="utf-8", errors="replace") as stream:
            end = stream.seek(0, 2)
            start = max(0, end - max_chars * 4)
            stream.seek(start)
            if start:
                stream.readline()  # discard a partial JSONL record
            for line in stream:
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                event_timestamp = str(d.get("timestamp") or "")
                typ = d.get("type")
                if typ == "user":
                    content = _extract_user_content(d)
                    if content:
                        append("user", content, kind="input")
                elif typ == "assistant":
                    for block in d.get("message", {}).get("content", []):
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") == "text":
                            content = str(block.get("text", ""))
                            append("assistant", content, kind="final")
                        elif block.get("type") == "thinking":
                            content = str(block.get("thinking") or block.get("text") or "")
                            append("assistant", content, kind="reasoning", title="思考摘要")
                elif typ == "tool_use":
                    tool_name = d.get("tool_name", "?")
                    tool_input = d.get("tool_input", {}) or {}
                    detail = _format_tool_input(tool_name, tool_input)
                    content = f"[tool] {tool_name}" + (f": {detail}" if detail else "")
                    append("tool", content, kind="tool_call", title=f"工具调用 · {tool_name}")
                elif typ == "tool_result":
                    tool_name = (d.get("tool_name") or "").lower()
                    if tool_name in ("read", "write", "edit"):
                        continue
                    output = d.get("tool_output", {}) or {}
                    text = output.get("output", "") if isinstance(output, dict) else str(output)
                    if text and text.strip():
                        append("tool", text, kind="tool_result", title="工具结果")
                elif typ == "response_item":
                    # Codex native event envelope.
                    payload = d.get("payload", {}) or {}
                    payload_type = payload.get("type", "")
                    role = payload.get("role", "")
                    if role == "user":
                        content = _extract_codex_text(payload)
                        if content:
                            append("user", content, kind="input")
                    elif role == "assistant":
                        content = _extract_codex_text(payload)
                        if content:
                            append("assistant", content, kind="final")
                    elif payload_type == "reasoning":
                        content = _extract_codex_reasoning(payload)
                        if content:
                            append("assistant", content, kind="reasoning", title="思考摘要")
                    elif payload_type == "custom_tool_call":
                        name = str(payload.get("name", "tool"))
                        content = str(payload.get("input", ""))
                        append("tool", content, kind="tool_call", title=f"工具调用 · {name}")
                    elif payload_type == "custom_tool_call_output":
                        content = _extract_codex_text({"content": payload.get("output", [])})
                        if content:
                            append("tool", content, kind="tool_result", title="工具结果")
    except OSError:
        return []
    return list(messages)


def _extract_user_content(d: dict) -> str:
    msg = d.get("message")
    if isinstance(msg, dict):
        content = msg.get("content", "")
    else:
        content = d.get("content", "")
    if isinstance(content, str):
        content = content.strip()
        # OpenCode's transcript stores the raw prompt wrapped in a pair of
        # literal double quotes; strip them so the UI doesn't show leading/
        # trailing quotation marks.
        if len(content) >= 2 and content[0] == '"' and content[-1] == '"':
            content = content[1:-1].strip()
        return content
    return ""


def _extract_assistant_content(d: dict) -> str:
    parts: list[str] = []
    for block in d.get("message", {}).get("content", []):
        if block.get("type") in ("text", "thinking"):
            txt = block.get("text") or block.get("thinking", "")
            if isinstance(txt, str) and txt.strip():
                parts.append(txt.strip())
    return "\n\n".join(parts)


def _extract_codex_text(payload: dict) -> str:
    """Extract readable text from a Codex response_item payload."""
    content = payload.get("content", "")
    if isinstance(content, str) and content.strip():
        return content.strip()
    parts: list[str] = []
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            txt = (
                block.get("text")
                or block.get("thinking")
                or block.get("value")
                or ""
            )
            if isinstance(txt, str) and txt.strip():
                parts.append(txt.strip())
    return "\n\n".join(parts)


def _extract_codex_reasoning(payload: dict) -> str:
    """Return only Codex's exposed reasoning summary, never encrypted CoT."""
    summary = payload.get("summary", [])
    if isinstance(summary, str):
        return summary.strip()
    parts: list[str] = []
    if isinstance(summary, list):
        for item in summary:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("text") or item.get("summary") or ""
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
    return "\n\n".join(parts)


def _format_tool_input(tool_name: str, inp: dict) -> str:
    name = (tool_name or "").lower()
    if name == "read":
        path = inp.get("file_path") or inp.get("filePath") or ""
        return str(path).split("/")[-1]
    if name in ("write", "edit"):
        path = inp.get("file_path") or inp.get("filePath") or ""
        return str(path).split("/")[-1]
    if name == "bash":
        return str(inp.get("command", ""))[:120]
    return ""


# Backward-compatible alias
_parse_claude_session = _parse_session_transcript


def _read_session_id_sidecar(
    project_root: Path, feature_id: str, stage_name: str
) -> Optional[str]:
    path = (
        get_chip_nebula_dir(project_root)
        / "shared"
        / "memory"
        / "session_ids"
        / feature_id
        / f"{stage_name}.txt"
    )
    if not path.is_file():
        return None
    try:
        return path.read_text().strip()
    except OSError:
        return None


def _read_session_started_at(path: Path) -> str:
    """Extract the timestamp from the first JSONL line that carries one.

    Qoder sessions begin with a ``workspace-directories`` entry that lacks
    a ``timestamp`` field, so we scan until we hit a line that has it.
    """
    try:
        with open(path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = d.get("timestamp", "")
                if ts:
                    return ts
        return ""
    except OSError:
        return ""


def read_stage_session_transcript(
    project_root: Path, feature_id: str, stage_name: str
) -> dict[str, Any]:
    state = read_pipeline_state(project_root, feature_id)
    session_ids = state.get("session_ids", {})
    raw = session_ids.get(stage_name, "")

    # Normalize: old format is str, new format is list[str]
    if isinstance(raw, str):
        candidates = [raw] if raw else []
    elif isinstance(raw, list):
        candidates = list(raw)
    else:
        candidates = []

    # Sidecar is written in real-time by the adapter on session start,
    # while pipeline state lags (saved only after iteration completes).
    # Always append sidecar as newest candidate if not already present.
    sidecar = _read_session_id_sidecar(project_root, feature_id, stage_name)
    if sidecar and (not candidates or candidates[-1] != sidecar):
        candidates.append(sidecar)

    if not candidates:
        return {"session_id": "", "messages": [], "started_at": ""}

    # Walk newest-first; pick the first session with substantive content
    for sid in reversed(candidates):
        if not sid:
            continue
        path = _find_session_file(sid)
        if path is None:
            continue
        messages = _parse_claude_session(path)
        if any(m.get("role") == "assistant" for m in messages):
            return {
                "session_id": sid,
                "messages": messages,
                "started_at": _read_session_started_at(path),
            }

    # No session has assistant content; return newest ID with empty messages
    newest = candidates[-1]
    path = _find_session_file(newest)
    if path is None:
        return {"session_id": newest, "messages": [], "started_at": ""}
    return {
        "session_id": newest,
        "messages": _parse_claude_session(path),
        "started_at": _read_session_started_at(path),
    }


def read_run_workspace_transcript(run_id: str) -> dict[str, Any]:
    """Recover a taskgraph Run's transcript via its workspace identity.

    Runs that predate session-id recording (no DB session_id, no adapter
    sidecar) may still have a transcript on disk. The runner gives every Run
    its own git worktree at ``.chip_nebula/taskgraph/workspaces/<run_id>``,
    and each framework's store is searchable by that cwd:

    - Claude Code / Qoder: one project dir per cwd, named after its path slug
      → match by directory name.
    - Codex: date-based store, but every rollout file opens with a
      ``session_meta`` line carrying ``cwd`` and ``session_id`` → match by
      first-line content.
    - OpenCode: flat transcripts carry no cwd → not recoverable this way;
      its adapter captures the real session id mid-run, so sidecars cover it.

    Stores that can hold several transcripts for one workspace (Qoder, Codex)
    are only trusted when exactly one matches — with multiple files the
    run↔session mapping is ambiguous (e.g. a later manual resume dropped
    another session into the dir) and the stage-level sidecar is safer.
    """
    empty = {"session_id": "", "messages": [], "started_at": ""}
    if not run_id:
        return empty
    projects = Path.home() / ".claude" / "projects"
    for project_dir in sorted(projects.glob(f"*{run_id}*")):
        files = sorted(
            project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if files:
            return _workspace_transcript_result(files[0])
    qoder_projects = Path.home() / ".qoder" / "projects"
    for project_dir in sorted(qoder_projects.glob(f"*{run_id}*")):
        files = list(project_dir.glob("*.jsonl"))
        if len(files) == 1:
            return _workspace_transcript_result(files[0])
    codex = _find_codex_workspace_session(run_id)
    if codex is not None:
        path, session_id = codex
        return _workspace_transcript_result(path, session_id=session_id)
    return empty


def read_desktop_operation_transcript(
    project_root: Path, operation: dict[str, Any], *, timestamp_slack_seconds: int = 90,
) -> dict[str, Any]:
    """Recover a legacy desktop Agent transcript without a recorded ID.

    Older Claude/Qoder desktop dispatches ran in the live project checkout and
    did not persist the session ID.  A project directory alone is ambiguous,
    so recovery requires both the exact operation instruction in the JSONL and
    a first transcript timestamp close to the durable operation creation time.
    """
    empty = {"session_id": "", "messages": [], "started_at": ""}
    instruction = str(operation.get("instruction", "")).strip()
    created_at = str(operation.get("created_at", "")).strip()
    if not instruction or not created_at:
        return empty
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
    except ValueError:
        return empty
    matches: list[Path] = []
    root_marker = project_root.name.replace("_", "-")
    for base in (Path.home() / ".claude" / "projects", Path.home() / ".qoder" / "projects"):
        if not base.is_dir():
            continue
        for project_dir in base.glob(f"*{root_marker}*"):
            for path in project_dir.glob("*.jsonl"):
                try:
                    messages = _parse_session_transcript(path)
                except OSError:
                    continue
                # Parse JSONL rather than searching its serialized bytes:
                # Claude may encode non-ASCII user text as ``\\uXXXX``.
                if not any(instruction in str(message.get("content", "")) for message in messages):
                    continue
                started_at = _read_session_started_at(path)
                try:
                    started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    if started.tzinfo is None:
                        started = started.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
                if abs((started - created).total_seconds()) <= timestamp_slack_seconds:
                    matches.append(path)
    if len(matches) != 1:
        return empty
    return _workspace_transcript_result(matches[0])


def _workspace_transcript_result(path: Path, session_id: str = "") -> dict[str, Any]:
    return {
        "session_id": session_id or path.stem,
        "messages": _parse_session_transcript(path),
        "started_at": _read_session_started_at(path),
    }


def _find_codex_workspace_session(run_id: str) -> tuple[Path, str] | None:
    """Match a Codex rollout file whose session ran in this Run's worktree.

    Codex names files by date, not cwd, so read each rollout's first line
    (``session_meta``) and compare its recorded cwd. Returns ``(path,
    session_id)`` only when exactly one rollout matches.
    """
    matches: list[tuple[Path, str]] = []
    sessions = Path.home() / ".codex" / "sessions"
    for path in sessions.glob("*/*/*/rollout-*.jsonl"):
        try:
            with path.open("r", encoding="utf-8", errors="replace") as stream:
                meta = json.loads(stream.readline())
        except (OSError, json.JSONDecodeError):
            continue
        if meta.get("type") != "session_meta":
            continue
        payload = meta.get("payload") or {}
        cwd = str(payload.get("cwd", "")).rstrip("/")
        if cwd.endswith(f"/workspaces/{run_id}"):
            matches.append((path, str(payload.get("session_id", ""))))
    return matches[0] if len(matches) == 1 else None


def read_session_transcript_by_id(session_id: str) -> dict[str, Any]:
    """Locate and parse a session transcript by bare session_id.

    Thin public wrapper over ``_find_session_file`` + ``_parse_session_transcript``
    for consumers whose session ids do not live in pipeline state/sidecars
    (currently: the roundtable feature, which tracks ids in its own state.json).
    """
    if not session_id:
        return {"session_id": "", "messages": [], "started_at": ""}
    path = _find_session_file(session_id)
    if path is None:
        return {"session_id": session_id, "messages": [], "started_at": ""}
    return {
        "session_id": session_id,
        "messages": _parse_session_transcript(path),
        "started_at": _read_session_started_at(path),
    }

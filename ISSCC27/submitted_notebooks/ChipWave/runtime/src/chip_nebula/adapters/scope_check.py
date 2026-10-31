"""Post-run write-scope enforcement for agent adapters.

An agent YAML declares a flat `write_paths` list of glob patterns — the only
places in the worktree it's permitted to modify. After the adapter's
subprocess returns, we compare the actual filesystem changes against this
allow-list. Any out-of-scope change demotes the run to failure and injects
a synthetic `Error-Class: scope_violation` into the execution log so the
stage loop routes it through the normal classification machinery.

Why enforce at the output side instead of constraining the framework's
tool permissions:

* Claude Code / OpenCode permission models are per-process (settings.json),
  not per-TaskManifest — regenerating them on every dispatch would race.
* Interactive permission prompts kill throughput.
* The git worktree already captures *what actually changed*, which is the
  only thing that matters for safety.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable

from chip_nebula.adapters.base import is_path_in_write_scope


_NL = "\n"


def detect_changed_paths(
    workspace: Path, working_tree_only: bool = False, *,
    ignored_write_paths: Iterable[str] = (),
) -> list[str]:
    """Return every path relative to `workspace` that ``git status`` reports.

    Uses ``git status --porcelain=v1`` so we catch modified, added, deleted,
    renamed AND untracked files — ``git diff`` alone misses untracked.

    Explicit ``ignored_write_paths`` also includes ignored generated deliverables
    inside the Task grant; adapter scope checks keep their existing default.

    When ``working_tree_only=True``, only paths where the working tree is
    dirty (second porcelain column non-space) are returned.  This excludes
    files that are *only* staged (e.g. ``A `` after ``git add`` by a
    previous stage's ``_stage_deliverables``), so that scope enforcement
    doesn't get a false-negative when a downstream agent silently appends
    its own modifications on top of an already-staged file.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            capture_output=True, text=True, cwd=workspace,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []

    paths: list[str] = []
    for line in result.stdout.split(_NL):
        if not line.strip():
            continue
        status = line[:2] if len(line) >= 2 else ""
        wt_status = status[1] if len(status) >= 2 else " "
        if working_tree_only and wt_status.strip() == "":
            # Second-column is space → working tree is clean for this file.
            # Skip files that are only index-staged (e.g. "A ", "M ").
            continue
        # Porcelain v1: two-char status, space, path.  Rename: "R  old -> new".
        body = line[3:] if len(line) >= 3 else line
        if " -> " in body:
            _, body = body.split(" -> ", 1)
        # Dequote paths porcelain quotes when they contain special chars.
        body = body.strip()
        if body.startswith('"') and body.endswith('"'):
            body = body[1:-1]
        if body:
            paths.append(body)
    grants = tuple(ignored_write_paths)
    if grants:
        ignored = subprocess.run(
            ["git", "ls-files", "--others", "--ignored", "--exclude-standard", "-z", "--", *grants],
            capture_output=True, text=True, cwd=workspace, check=True,
        )
        paths.extend(path for path in ignored.stdout.split("\0")
                     if path and is_path_in_write_scope(path, grants))
    return list(dict.fromkeys(paths))


# Framework-owned state dirs: written by the agent framework or its plugins
# (skill symlinks, session-continuation state, project config), never by the
# agent, so they must not count as out-of-scope agent writes.
_FRAMEWORK_STATE_DIRS = (
    ".claude/", ".omo/", ".opencode/", ".codex/", ".nebula_inputs/",
    ".chip_nebula/",
)


def violations(
    changed_paths: Iterable[str],
    write_paths: Iterable[str],
) -> list[str]:
    """Return changed paths that fall outside ``write_paths``.

    If ``write_paths`` is empty, every changed path is treated as a violation
    (except framework state dirs like ``.claude/`` and ``.omo/``).
    """
    patterns = [p for p in (write_paths or []) if p]
    bad: list[str] = []
    for path in changed_paths:
        if path.startswith(_FRAMEWORK_STATE_DIRS):
            continue
        if not is_path_in_write_scope(path, patterns):
            bad.append(path)
    return bad


def format_scope_violation_log(
    violating_paths: list[str],
    write_paths: list[str],
) -> str:
    """Render the synthetic trailer the adapter appends to execution_log when
    an out-of-scope write is detected. The two Error-Class lines use the
    existing parse_error_classes_from_log convention so the interpreter
    picks this up without any special casing.
    """
    reason = (
        f"agent modified {len(violating_paths)} path(s) outside write_paths="
        f"{list(write_paths)}: {violating_paths}"
    )
    return (
        _NL
        + "Error-Class: scope_violation" + _NL
        + f"Error-Class-Reason: {reason}" + _NL
    )

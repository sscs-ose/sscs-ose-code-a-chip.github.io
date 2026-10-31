"""Ephemeral Git worktrees materialized from immutable Artifact commits."""

from __future__ import annotations

import shutil
import subprocess
import io
import tarfile
from dataclasses import dataclass
from pathlib import Path

from chip_nebula.adapters.base import is_path_in_write_scope
from chip_nebula.adapters.scope_check import detect_changed_paths
from chip_nebula.taskgraph.domain import Artifact


ATTEMPT_WIP_REF_PREFIX = "refs/chip-nebula/attempts"
_GIT_PATH_BATCH_SIZE = 128


def is_publishable_path(path: str) -> bool:
    """Exclude host/runtime caches from WIP and immutable Deliveries."""
    parts = Path(path).parts
    return (
        "__pycache__" not in parts
        and not path.endswith((".pyc", ".pyo"))
        and Path(path).name not in {".DS_Store"}
    )


def preserve_attempt_wip(
    workspace: ExecutionWorkspace, write_paths: tuple[str, ...],
) -> str:
    """Commit a terminal Attempt's in-scope work and pin its WIP ref.

    Without this, a Run that never reaches the success path loses everything
    the Agent changed: the worktree is deleted without a commit. Only the
    declared write paths are staged (same scope and exclusions as a success
    commit). Returns the WIP commit, or "" when there is nothing new.
    """
    before = _git(workspace.root, "rev-parse", "HEAD").stdout.strip()
    commit, _ = workspace.commit(
        write_paths, f"[nebula] WIP checkpoint {workspace.attempt_id}"
    )
    # Output publication may already have committed direct evidence before a
    # later schema validation rejects the payload. Compare with the workspace
    # materialization base, not only with HEAD immediately before this helper,
    # so that commit is still pinned as recoverable WIP.
    unchanged = (
        commit == workspace.base_commit
        if workspace.base_commit else commit == before
    )
    if unchanged:
        return ""
    _git(
        workspace.repository, "update-ref",
        f"{ATTEMPT_WIP_REF_PREFIX}/{workspace.attempt_id}", commit,
    )
    return commit


def capture_leaked_wip_state(
    repository: Path, workspace_root: Path, attempt_id: str,
    write_paths: tuple[str, ...], *, base_commit: str = "",
) -> tuple[str, tuple[str, ...]]:
    """Checkpoint a dead Attempt worktree and report its in-scope paths.

    ``base_commit`` is the materialized Attempt workspace before the Agent ran.
    It lets recovery preserve Agent-created commits as well as dirty files,
    without treating platform input-overlay commits as Task WIP.
    """
    root = workspace_root / attempt_id
    if not root.is_dir():
        return "", ()
    workspace = ExecutionWorkspace(
        repository, root, attempt_id, base_commit=base_commit,
    )
    try:
        committed: set[str] = set()
        if base_commit:
            result = _git(
                root, "diff", "--name-only", "-z",
                f"{base_commit}..HEAD", check=False,
            )
            if result.returncode != 0:
                raise WorkspaceError(
                    "leaked Attempt workspace is not comparable with its materialized base"
                )
            committed = {path for path in result.stdout.split("\0") if path}
        dirty = set(detect_changed_paths(root, ignored_write_paths=write_paths))
        paths = tuple(sorted(
            path for path in committed | dirty
            if is_publishable_path(path)
            and is_path_in_write_scope(path, write_paths)
        ))
        if not paths:
            commit = ""
        else:
            commit = preserve_attempt_wip(workspace, write_paths)
            if not commit:
                # ``preserve_attempt_wip`` returns empty only when HEAD equals the
                # materialized base.  Paths above prove there was work, so keep a
                # defensive explicit failure instead of deleting the only copy.
                raise WorkspaceError("leaked Attempt WIP could not be checkpointed")
    except Exception:
        workspace.retain_on_close()
        raise
    workspace.close()
    return commit, paths


class WorkspaceError(RuntimeError):
    pass


def _git(repository: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args], cwd=repository, capture_output=True, text=True
    )
    if check and result.returncode != 0:
        raise WorkspaceError(result.stderr.strip() or result.stdout.strip())
    return result


@dataclass
class ExecutionWorkspace:
    repository: Path
    root: Path
    attempt_id: str
    base_commit: str
    overlay_paths: tuple[str, ...] = ()
    _closed: bool = False
    _retain_on_close: bool = False
    _preserve_on_error_paths: tuple[str, ...] = ()
    preserved_wip_commit: str = ""
    preserved_wip_paths: tuple[str, ...] = ()

    def commit(self, paths: tuple[str, ...], message: str) -> tuple[str, str]:
        if paths:
            # Stage exact changed files that fall inside the grant.  Passing
            # every declared glob directly to ``git add`` makes Git reject an
            # otherwise valid run whenever one authorized directory does not
            # exist yet (for example ``rtl/**`` in a fresh project while the
            # Agent only writes a diagnostic under ``docs/**``).
            framework_roots = (
                ".nebula_inputs/", ".claude/", ".omo/", ".opencode/", ".codex/",
                ".chip_nebula/", ".qoder/",
            )
            changed = detect_changed_paths(self.root, ignored_write_paths=paths)
            stageable = [
                path for path in changed
                if not path.startswith(framework_roots)
                and is_publishable_path(path)
                and is_path_in_write_scope(path, paths)
            ]
            if stageable:
                # Large verification runs can touch thousands of files.  Keep
                # path lists out of one giant argv so retries never hit the
                # operating system's ARG_MAX limit.
                for start in range(0, len(stageable), _GIT_PATH_BATCH_SIZE):
                    _git(
                        self.root, "add", "-A", "-f", "--",
                        *stageable[start:start + _GIT_PATH_BATCH_SIZE],
                    )
        staged = _git(self.root, "diff", "--cached", "--quiet", check=False)
        if staged.returncode == 1:
            _git(
                self.root, "-c", "user.name=Chip Nebula", "-c",
                "user.email=nebula@localhost", "commit", "-m", message,
            )
        elif staged.returncode != 0:
            raise WorkspaceError(staged.stderr.strip())
        commit = _git(self.root, "rev-parse", "HEAD").stdout.strip()
        tree = _git(self.root, "rev-parse", "HEAD^{tree}").stdout.strip()
        return commit, tree

    def tracked_paths(self, paths: tuple[str, ...] = ()) -> list[str]:
        """Return pinned files, optionally narrowed to declared write scopes."""
        result = (
            _git(self.root, "ls-files", "-z", "--", *paths)
            if paths else _git(self.root, "ls-files", "-z")
        )
        return [
            path for path in result.stdout.split("\0")
            if path and is_publishable_path(path)
            and (not paths or is_path_in_write_scope(path, paths))
        ]

    def preserve(self, artifact_id: str, commit: str) -> None:
        safe = artifact_id.replace("/", "-")
        _git(self.repository, "update-ref", f"refs/chip-nebula/artifacts/{safe}", commit)

    def close(self) -> None:
        if self._closed:
            return
        if self._retain_on_close:
            return
        _git(self.repository, "worktree", "remove", "--force", str(self.root), check=False)
        if self.root.exists():
            shutil.rmtree(self.root)
        _git(self.repository, "worktree", "prune", check=False)
        self._closed = True

    def retain_on_close(self) -> None:
        """Keep this worktree when process cleanup could not be verified."""
        self._retain_on_close = True

    def preserve_on_error(self, paths: tuple[str, ...]) -> None:
        """Checkpoint authorized work before an exception removes the worktree."""
        self._preserve_on_error_paths = paths

    def __enter__(self) -> "ExecutionWorkspace":
        return self

    def __exit__(self, exc_type: object, *_args: object) -> None:
        if exc_type is not None and self._preserve_on_error_paths:
            try:
                committed = _git(
                    self.root, "diff", "--name-only", "-z",
                    f"{self.base_commit}..HEAD", check=False,
                )
                dirty = detect_changed_paths(
                    self.root,
                    ignored_write_paths=self._preserve_on_error_paths,
                )
                candidates = set(committed.stdout.split("\0")) | set(dirty)
                self.preserved_wip_paths = tuple(sorted(
                    path for path in candidates
                    if path and is_publishable_path(path)
                    and is_path_in_write_scope(
                        path, self._preserve_on_error_paths,
                    )
                ))
                self.preserved_wip_commit = preserve_attempt_wip(
                    self, self._preserve_on_error_paths,
                )
            except Exception:
                # Never delete the only recoverable copy when checkpointing
                # itself fails.  Surface the checkpoint error to the caller.
                self.retain_on_close()
                raise
        self.close()

def _extract_repo_archive(archive: tarfile.TarFile, destination: Path) -> None:
    """Extract trusted `git archive` output, tolerating absolute symlinks.

    The `data` filter rejects symlinks whose target is an absolute path, but
    project repos legitimately contain such links (e.g. prebuilt test binaries
    under verification/ pointing into a toolchain install). The archive here
    is the user's own repository content, so keep those links — they stay
    valid on this machine — while retaining every other `data` protection.
    """

    def _filter(member: tarfile.TarInfo, dest: str) -> tarfile.TarInfo | None:
        try:
            return tarfile.data_filter(member, dest)
        except tarfile.AbsoluteLinkError:
            return member

    archive.extractall(destination, filter=_filter)


def _export_commit(repository: Path, artifact: Artifact, destination: Path) -> None:
    safe = "".join(char if char.isalnum() or char in "-_" else "-" for char in artifact.id)
    target = destination / safe
    target.mkdir()
    if not _git(repository, "ls-tree", "-r", "--name-only", artifact.content.commit).stdout.strip():
        # A fresh specification source may legitimately have an empty tree.
        # Its inline input text is still exported in artifact.json below.
        return
    result = subprocess.run(
        ["git", "archive", "--format=tar", artifact.content.commit],
        cwd=repository, capture_output=True,
    )
    if result.returncode != 0:
        raise WorkspaceError(result.stderr.decode(errors="replace").strip())
    with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
        _extract_repo_archive(archive, target)


def _overlay_commit_paths(repository: Path, artifact: Artifact, destination: Path) -> None:
    """Overlay only the Artifact-owned files, never merge its whole history."""
    if not artifact.content.paths:
        return
    for start in range(0, len(artifact.content.paths), _GIT_PATH_BATCH_SIZE):
        paths = artifact.content.paths[start:start + _GIT_PATH_BATCH_SIZE]
        result = subprocess.run(
            ["git", "archive", "--format=tar", artifact.content.commit, "--", *paths],
            cwd=repository, capture_output=True,
        )
        if result.returncode != 0:
            raise WorkspaceError(result.stderr.decode(errors="replace").strip())
        with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
            _extract_repo_archive(archive, destination)
    deleted = artifact.metadata.get("deleted_paths", ())
    if isinstance(deleted, (list, tuple)):
        for path in deleted:
            target = destination / str(path)
            if target.is_file() or target.is_symlink():
                target.unlink()

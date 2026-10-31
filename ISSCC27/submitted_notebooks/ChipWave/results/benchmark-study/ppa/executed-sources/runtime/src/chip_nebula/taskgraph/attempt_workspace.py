"""Conflict-aware worktree materialization for static Task Attempts."""

from __future__ import annotations

import json
import io
import shutil
import subprocess
import tarfile
from pathlib import Path

from chip_nebula.project import ensure_framework_skills

from chip_nebula.adapters.base import is_path_in_write_scope
from .domain import Artifact, Attempt
from .prepare_contracts import REQUIREMENT_STATUSES, ledger_without_status
from .workspaces import ExecutionWorkspace, WorkspaceError, _export_commit, _git, _overlay_commit_paths, _extract_repo_archive


class AttemptWorkspaceFactory:
    def __init__(self, repository: Path, workspace_root: Path) -> None:
        self.repository = repository.resolve()
        self.workspace_root = workspace_root.resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def create(
        self, attempt_id: str, inputs: list[Artifact], *,
        workflow_baseline: str, resume_commit: str = "",
        resume_base_commit: str = "",
        resume_modified_paths: tuple[str, ...] | None = None,
        context_only_artifact_ids: frozenset[str] = frozenset(),
        failure_attempts: tuple[Attempt, ...] = (),
        evidence_read_paths: tuple[str, ...] = (),
    ) -> ExecutionWorkspace:
        if not workflow_baseline:
            raise WorkspaceError("Workflow has no frozen Git baseline")
        root = self.workspace_root / attempt_id
        if root.exists():
            raise WorkspaceError(f"workspace already exists: {root}")
        # A failed Attempt's checkpoint is recoverable content, not published
        # Artifact ancestry.  Starting HEAD at the WIP commit would make every
        # abandoned download, diagnostic binary, or other later-removed file a
        # permanent ancestor of a successful Delivery.  Rehydrate the selected
        # WIP paths as dirty files on the frozen baseline instead.  The next
        # successful commit then contains exactly the retained result while the
        # immutable failed checkpoint remains independently auditable.
        _git(
            self.repository, "worktree", "add", "--detach", str(root),
            workflow_baseline,
        )
        try:
            changed_in_wip = (
                set(resume_modified_paths)
                if resume_modified_paths is not None
                else self._changed_paths(workflow_baseline, resume_commit)
            )
            ensure_framework_skills(root)
            input_root = root / ".nebula_inputs"
            input_root.mkdir()
            platform_paths: set[str] = set()
            input_owners: dict[str, Artifact] = {}
            for artifact in inputs:
                if artifact.content.kind == "git":
                    _export_commit(self.repository, artifact, input_root)
                self._write_manifest(artifact, input_root)
                # Feedback evidence is immutable context, not a replacement
                # for a Task's formal Delivery. Keep its complete Git snapshot
                # under .nebula_inputs without overlaying same-named project
                # files. An explicit repair Attempt may then reconcile the
                # content while preserving its existing WIP.
                if (
                    artifact.content.kind != "git"
                    or artifact.id in context_only_artifact_ids
                ):
                    continue
                overlay_paths: list[str] = []
                for path in artifact.content.paths:
                    previous = input_owners.get(path)
                    if previous is not None:
                        if self._blob(previous.content.commit, path) == self._blob(
                            artifact.content.commit, path,
                        ):
                            continue
                        reviewed = self._reviewed_ledger(path, previous, artifact)
                        if reviewed is None:
                            raise WorkspaceError(
                                "real content conflict between Attempt inputs: "
                                f"{path} differs in {previous.id} and {artifact.id}"
                            )
                        if reviewed.id == previous.id:
                            continue
                    input_owners[path] = artifact
                    platform_paths.add(path)
                    overlay_paths.append(path)
                if overlay_paths:
                    from dataclasses import replace
                    view = replace(
                        artifact,
                        content=replace(
                            artifact.content, paths=tuple(overlay_paths),
                        ),
                        digest="",
                    )
                    _overlay_commit_paths(self.repository, view, root)
            for failure in failure_attempts:
                destination = input_root / failure.id
                destination.mkdir()
                paths = [str(path) for path in failure.diagnostics.get("changed_paths", ())
                         if is_path_in_write_scope(str(path), evidence_read_paths)
                         and is_path_in_write_scope(str(path), failure.permission.write_paths)]
                # A WIP snapshot is diagnostic evidence, never a formal input overlay.
                if failure.workspace_commit and paths:
                    existing = set(_git(self.repository, "ls-tree", "-r", "--name-only",
                                        failure.workspace_commit).stdout.splitlines())
                    paths = [path for path in paths if path in existing]
                    for start in range(0, len(paths), 128):
                        archive = subprocess.run(
                            ["git", "archive", "--format=tar", failure.workspace_commit,
                             "--", *paths[start:start + 128]], cwd=self.repository, capture_output=True,
                        )
                        if archive.returncode:
                            raise WorkspaceError(archive.stderr.decode(errors="replace").strip())
                        with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as stream:
                            _extract_repo_archive(stream, destination)
                (destination / "failure.json").write_text(json.dumps({
                    "attempt_id": failure.id, "task_id": failure.task_id,
                    "workspace_commit": failure.workspace_commit,
                    "failure_reason": failure.diagnostics.get("failure_reason", ""),
                    "gate_reports": failure.diagnostics.get("gate_reports", []),
                    "execution_log": failure.diagnostics.get("execution_log", ""),
                    "readable_wip_paths": paths,
                }, ensure_ascii=False, indent=2), encoding="utf-8")
            self._commit_platform_inputs(root, platform_paths)
            materialized = _git(root, "rev-parse", "HEAD").stdout.strip()
            if resume_commit and changed_in_wip:
                self._restore_wip(
                    root, resume_base_commit or workflow_baseline, resume_commit, changed_in_wip,
                )
            return ExecutionWorkspace(
                self.repository, root, attempt_id, materialized,
            )
        except Exception:
            _git(self.repository, "worktree", "remove", "--force", str(root), check=False)
            if root.exists():
                shutil.rmtree(root)
            raise

    def _reviewed_ledger(self, path: str, first: Artifact, second: Artifact) -> Artifact | None:
        # A linked review owns only ledger statuses; input order cannot select a revision.
        if path != "spec/requirements.ledger.json":
            return None
        review, bundle = (first, second) if first.type == "requirements.review.report" else (second, first)
        if (review.type != "requirements.review.report" or bundle.type != "specification.bundle"
                or review.payload.get("subject") != bundle.id
                or bundle.id not in review.input_artifact_ids):
            return None
        try:
            before = json.loads(self._blob(bundle.content.commit, path))
            after = json.loads(self._blob(review.content.commit, path))
            if ledger_without_status(before) != ledger_without_status(after):
                return None
            if not after["requirements"] or any(
                item.get("status") not in REQUIREMENT_STATUSES for item in after["requirements"]
            ):
                return None
        except (TypeError, ValueError, KeyError):
            return None
        return review

    def _restore_wip(
        self, root: Path, baseline: str, resume_commit: str,
        paths: set[str],
    ) -> None:
        """Restore checkpoint content without importing its Git ancestry."""
        selected = sorted(paths)
        for start in range(0, len(selected), 128):
            batch = selected[start:start + 128]
            patch = subprocess.run(
                [
                    "git", "diff", "--binary", "--full-index", "--no-ext-diff",
                    baseline, resume_commit, "--", *batch,
                ],
                cwd=self.repository, capture_output=True,
            )
            if patch.returncode != 0:
                raise WorkspaceError(
                    patch.stderr.decode(errors="replace").strip()
                    or "cannot read recoverable WIP diff"
                )
            if not patch.stdout:
                continue
            applied = subprocess.run(
                ["git", "apply", "--3way", "--binary", "--whitespace=nowarn"],
                cwd=root, input=patch.stdout, capture_output=True,
            )
            if applied.returncode != 0:
                raise WorkspaceError(
                    "real content conflict while restoring WIP: "
                    + (applied.stderr.decode(errors="replace").strip()
                       or "cannot apply saved changes to captured inputs")
                )
        _git(root, "reset", "--mixed", "HEAD")

    def _changed_paths(self, baseline: str, resume_commit: str) -> set[str]:
        if not resume_commit:
            return set()
        result = _git(
            self.repository, "diff", "--name-only", "-z",
            f"{baseline}..{resume_commit}", check=False,
        )
        if result.returncode != 0:
            raise WorkspaceError(
                "recoverable WIP is not comparable with the frozen Workflow baseline"
            )
        return {path for path in result.stdout.split("\0") if path}

    def _blob(self, commit: str, path: str) -> bytes | None:
        incoming = subprocess.run(
            ["git", "show", f"{commit}:{path}"],
            cwd=self.repository, capture_output=True,
        )
        return incoming.stdout if incoming.returncode == 0 else None

    @staticmethod
    def _commit_platform_inputs(root: Path, paths: set[str]) -> None:
        selected = sorted(paths)
        if selected:
            _git(root, "add", "-A", "-f", "--", *selected)
        staged = _git(root, "diff", "--cached", "--quiet", check=False)
        if staged.returncode == 1:
            _git(
                root, "-c", "user.name=Chip Nebula", "-c",
                "user.email=nebula@localhost", "commit", "-m",
                "[nebula] materialize Attempt inputs",
            )
        elif staged.returncode != 0:
            raise WorkspaceError(staged.stderr.strip())

    @staticmethod
    def _write_manifest(artifact: Artifact, input_root: Path) -> None:
        target = input_root.parent / Path(artifact.input_manifest_path).parent
        target.mkdir(exist_ok=True)
        (target / "artifact.json").write_text(
            json.dumps(
                {**artifact.document(), "digest": artifact.digest},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )

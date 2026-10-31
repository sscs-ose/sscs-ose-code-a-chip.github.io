import json
import shutil
from pathlib import Path
from typing import List, Optional

from chip_nebula.models.task_manifest import PipelineState, Workspace
from chip_nebula.project import (
    find_project_root,
    get_sparse_patterns,
    get_worktrees_dir,
    create_worktree,
    remove_worktree,
)


# Maps each Workspace dataclass field to the sparse-checkout dir it needs. If
# the user's chip_nebula.yaml `sparse_checkout` list omits the dir, we skip
# the mkdir and leave the Workspace field set to None, so downstream code
# can detect "this dir was excluded from the worktree" rather than quietly
# operating on an empty directory.
_WS_DIR_MAP = {
    "spec_dir": "docs",
    "rtl_dir": "rtl",
    "tb_dir": "tb",
    "constraints_dir": "constraints",
}


class WorkspaceManager:
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or find_project_root()
        if not self.project_root:
            raise FileNotFoundError("Project root not found")

    def _included_dirs(self) -> set[str]:
        patterns = get_sparse_patterns(self.project_root)
        if patterns is None:
            return set(_WS_DIR_MAP.values())
        return set(patterns)

    def create(self, feature_id: str) -> Workspace:
        root = create_worktree(feature_id, self.project_root)

        included = self._included_dirs()
        # Always point Workspace fields at `root/<subdir>`; only the mkdir is
        # skipped when the subdir is excluded from sparse_checkout. This keeps
        # downstream `ws.rtl_dir.exists()` checks honest: False when excluded,
        # True when included and actually present.
        for subdir in _WS_DIR_MAP.values():
            if subdir in included:
                (root / subdir).mkdir(parents=True, exist_ok=True)

        results_dir = root / "results"
        for d in ("lint", "sim", "sta"):
            (results_dir / d).mkdir(parents=True, exist_ok=True)

        pipeline_state = PipelineState(feature_id=feature_id)

        ws = Workspace(
            id=feature_id,
            root=root,
            spec_dir=root / _WS_DIR_MAP["spec_dir"],
            rtl_dir=root / _WS_DIR_MAP["rtl_dir"],
            tb_dir=root / _WS_DIR_MAP["tb_dir"],
            constraints_dir=root / _WS_DIR_MAP["constraints_dir"],
            results_dir=results_dir,
            pipeline_state=pipeline_state,
        )

        self.save_pipeline_state(feature_id, pipeline_state)

        with open(root / ".memory.json", "w") as f:
            json.dump({"iterations": [], "decisions": []}, f, indent=2)

        return ws

    def get_workspace(self, feature_id: str) -> Workspace:
        if not self.exists(feature_id):
            raise FileNotFoundError(f"Workspace {feature_id} not found")

        root = get_worktrees_dir(self.project_root) / feature_id
        pipeline_state = self.get_pipeline_state(feature_id)

        return Workspace(
            id=feature_id,
            root=root,
            spec_dir=root / _WS_DIR_MAP["spec_dir"],
            rtl_dir=root / _WS_DIR_MAP["rtl_dir"],
            tb_dir=root / _WS_DIR_MAP["tb_dir"],
            constraints_dir=root / _WS_DIR_MAP["constraints_dir"],
            results_dir=root / "results",
            pipeline_state=pipeline_state,
        )

    def exists(self, feature_id: str) -> bool:
        worktrees_dir = get_worktrees_dir(self.project_root)
        return (worktrees_dir / feature_id).is_dir()

    def get_pipeline_state(self, feature_id: str) -> PipelineState:
        state_file = get_worktrees_dir(self.project_root) / feature_id / ".pipeline_state.json"
        if not state_file.exists():
            return PipelineState(feature_id=feature_id)
            
        try:
            with open(state_file) as f:
                data = json.load(f)
                return PipelineState(
                    feature_id=data.get("feature_id", feature_id),
                    current_stage=data.get("current_stage", ""),
                    stage_status=data.get("stage_status", {}),
                    iteration_counts=data.get("iteration_counts", {}),
                    last_updated=data.get("last_updated", "")
                )
        except json.JSONDecodeError:
            return PipelineState(feature_id=feature_id)

    def save_pipeline_state(self, feature_id: str, state: PipelineState) -> None:
        state_file = get_worktrees_dir(self.project_root) / feature_id / ".pipeline_state.json"
        with open(state_file, "w") as f:
            json.dump({
                "feature_id": state.feature_id,
                "current_stage": state.current_stage,
                "stage_status": state.stage_status,
                "iteration_counts": state.iteration_counts,
                "last_updated": state.last_updated
            }, f, indent=2)

    def merge_to_integration(self, feature_ids: List[str], sprint: str) -> Workspace:
        integration_id = f"integration__{sprint}"
        ws = self.create(integration_id)

        merged_dir = ws.root / "merged"
        merged_dir.mkdir(exist_ok=True)

        # Copy source files so the integration workspace is independent of the
        # feature workspaces; otherwise edits on either side would bleed
        # through and destroy isolation.
        for fid in feature_ids:
            if not self.exists(fid):
                continue

            f_ws = self.get_workspace(fid)

            for src_dir in (f_ws.rtl_dir, f_ws.tb_dir):
                if not src_dir.exists():
                    continue
                for f in src_dir.glob("*"):
                    if f.is_file():
                        target = merged_dir / f.name
                        if not target.exists():
                            shutil.copy2(f, target)

        return ws

    def list_workspaces(self) -> List[str]:
        worktrees_dir = get_worktrees_dir(self.project_root)
        if not worktrees_dir.exists():
            return []
        return [d.name for d in worktrees_dir.iterdir() if d.is_dir()]

    def delete_workspace(self, feature_id: str) -> None:
        remove_worktree(feature_id, self.project_root)

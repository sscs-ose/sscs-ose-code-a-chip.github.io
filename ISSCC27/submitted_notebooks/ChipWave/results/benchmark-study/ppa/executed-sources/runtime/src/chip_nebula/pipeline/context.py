from typing import Any, Dict, List, Optional
import copy

from chip_nebula.models.task_manifest import AggregatedArtifact


class PipelineContext:
    """
    A mutable container carrying shared state during a pipeline run.
    Acts as a conduit between the pipeline interpreter and the artifact store.
    """

    def __init__(self) -> None:
        self.data: Dict[str, Any] = {}
        self.errors: Dict[str, List[Dict[str, Any]]] = {}
        self.predecessor_info: Optional[AggregatedArtifact] = None
        
        # Internal state tracking
        self._files_modified: set[str] = set()
        self._files_created: set[str] = set()
        self._interface_changes: list[Dict[str, Any]] = []

    def clone(self) -> "PipelineContext":
        """Returns a deep copy of the context."""
        new_ctx = PipelineContext()
        new_ctx.data = copy.deepcopy(self.data)
        new_ctx.errors = copy.deepcopy(self.errors)
        new_ctx.predecessor_info = copy.deepcopy(self.predecessor_info)
        new_ctx._files_modified = set(self._files_modified)
        new_ctx._files_created = set(self._files_created)
        new_ctx._interface_changes = copy.deepcopy(self._interface_changes)
        return new_ctx

    def carry_errors(self, gate_results: List[Any], carry_keys: List[str]) -> None:
        """Stores errors from gate results for the specified carry keys."""
        # This assumes gate_results has a specific structure not fully defined here
        # but typical for gate_reports containing errors dict/list
        for key in carry_keys:
            errors_for_key = []
            for result in gate_results:
                if hasattr(result, 'errors') and result.errors:
                     errors_for_key.extend(result.errors)
            if errors_for_key:
                self.errors[key] = self.errors.get(key, []) + errors_for_key

    def extract_metrics_from_reports(self, gate_reports: List[Any]) -> Dict[str, float]:
        """Parses metric values from gate reports."""
        metrics: Dict[str, float] = {}
        for report in gate_reports:
             if hasattr(report, 'metrics') and isinstance(report.metrics, dict):
                 for k, v in report.metrics.items():
                     if isinstance(v, (int, float)):
                         metrics[k] = float(v)
        return metrics

    def extract_decisions_from_log(self, execution_log: str) -> List[str]:
        """Finds decision lines in the execution log."""
        decisions: List[str] = []
        if not execution_log:
            return decisions
            
        for line in execution_log.splitlines():
            line_stripped = line.strip()
            if line_stripped.startswith("Decision:"):
                decisions.append(line_stripped[len("Decision:"):].strip())
            elif line_stripped.startswith("设计决策:"):
                decisions.append(line_stripped[len("设计决策:"):].strip())
        return decisions

    def detect_changed_files(self) -> List[str]:
        """Returns files tracked as changed."""
        return list(self._files_modified)

    def detect_interface_changes(self) -> List[Dict[str, Any]]:
        """Returns interface change records."""
        return self._interface_changes

    def detect_new_files(self) -> List[str]:
        """Returns files tracked as new."""
        return list(self._files_created)

    def set_predecessor_info(self, aggregated: AggregatedArtifact) -> None:
        """Stores predecessor aggregated artifact info."""
        self.predecessor_info = aggregated
        
    def track_modified_file(self, file_path: str) -> None:
        self._files_modified.add(file_path)
        
    def track_created_file(self, file_path: str) -> None:
        self._files_created.add(file_path)
        
    def track_interface_change(self, change: Dict[str, Any]) -> None:
        self._interface_changes.append(change)

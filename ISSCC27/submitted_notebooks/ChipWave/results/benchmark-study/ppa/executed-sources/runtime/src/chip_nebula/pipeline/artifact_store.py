import json
import re
import threading
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from chip_nebula.models.gate_report import GateReport
from chip_nebula.models.task_manifest import (
    AggregatedArtifact,
    FailedStageInfo,
    StageArtifact,
    StageResult,
)
from chip_nebula.pipeline.context import PipelineContext


class PipelineArtifactStore:
    """In-memory artifact store with optional on-disk persistence.

    When `persist_dir` is provided, every `record()` call writes the stage's
    artifact as JSON at `{persist_dir}/{stage_name}.json`, and a fresh
    instance can be restored via `load_from_disk(persist_dir)`.

    On-disk layout is intentionally one-file-per-stage (not a single bundle)
    so that:
      * partial writes from a crash leave the rest of the run intact
      * downstream tools can tail a specific stage's artifact without
        deserializing the whole pipeline
    """

    def __init__(self, persist_dir: Optional[Path] = None) -> None:
        self.records: Dict[str, StageArtifact] = {}
        self.persist_dir: Optional[Path] = Path(persist_dir) if persist_dir else None
        self._disk_lock = threading.Lock()
        if self.persist_dir is not None:
            self.persist_dir.mkdir(parents=True, exist_ok=True)

    def record(self, stage_name: str, result: StageResult, context: PipelineContext) -> StageArtifact:
        """
        Creates StageArtifact from result + context data.
        Extracts metrics, decisions, and interface changes.
        Overwrites previous record for the same stage_name (latest state semantics).
        """
        metrics = context.extract_metrics_from_reports(result.gate_reports)

        # Fallback: scan GateReport.details and GateReport.evidence for metric
        # values. `details` is the canonical place gates write numeric results
        # (e.g. MetricCheckGate writes {"actual_value": ..., "threshold": ...}),
        # so prefer it over evidence-text regex.
        metric_patterns = {
            'code_coverage': r'code[_\s-]?coverage\s*[:=]\s*(-?\d+\.?\d*)',
            'worst_slack': r'worst[_\s-]?slack\s*[:=]\s*(-?\d+\.?\d*)',
            'total_power': r'total[_\s-]?power\s*[:=]\s*(-?\d+\.?\d*)',
            'area': r'\barea\s*[:=]\s*(-?\d+\.?\d*)',
        }
        for report in result.gate_reports:
            details = getattr(report, 'details', None) or {}
            if isinstance(details, dict):
                for key, value in details.items():
                    if isinstance(value, (int, float)) and key not in metrics:
                        metrics[key] = float(value)

            evidence = getattr(report, 'evidence', '') or ''
            for metric_name, pattern in metric_patterns.items():
                if metric_name in metrics:
                    continue
                match = re.search(pattern, evidence, re.IGNORECASE)
                if match:
                    try:
                        metrics[metric_name] = float(match.group(1))
                    except ValueError:
                        pass

        decisions = context.extract_decisions_from_log(result.execution_log)

        # Merge modified files from result and context
        modified_files = set(result.files_modified)
        modified_files.update(context.detect_changed_files())

        created_files = context.detect_new_files()

        interface_changes = context.detect_interface_changes()

        current_status = "PASSED" if result.passed else "FAILED"

        artifact = StageArtifact(
            stage_name=stage_name,
            iteration=result.iteration,
            passed=result.passed,
            timestamp=datetime.now(),
            files_modified=list(modified_files),
            files_created=created_files,
            gate_reports=result.gate_reports,
            metrics=metrics,
            decisions=decisions,
            interface_changes=interface_changes,
            current_status=current_status,
            previous_attempt=result.previous_attempt,
            pending_failure_context=_failure_context_to_dict(result.failure_context) if result.failure_context else None,
            session_id=getattr(result, "session_id", "") or "",
            execution_log=getattr(result, "execution_log", "") or "",
        )

        self.records[stage_name] = artifact
        if self.persist_dir is not None:
            self._persist(stage_name, artifact)
        return artifact

    # ------------------------------------------------------------------ disk

    def _persist(self, stage_name: str, artifact: StageArtifact) -> None:
        """Atomically write one stage's artifact as JSON."""
        assert self.persist_dir is not None
        payload = _artifact_to_json(artifact)
        target = self.persist_dir / f"{_safe_name(stage_name)}.json"
        tmp = target.with_suffix(".json.tmp")
        with self._disk_lock:
            tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
            tmp.replace(target)

    @classmethod
    def load_from_disk(cls, persist_dir: Path) -> "PipelineArtifactStore":
        """Rehydrate a store from a directory previously written by record()."""
        store = cls(persist_dir=persist_dir)
        if not persist_dir.is_dir():
            return store
        for json_file in sorted(persist_dir.glob("*.json")):
            if json_file.name.endswith(".tmp"):
                continue
            try:
                data = json.loads(json_file.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            artifact = _artifact_from_json(data)
            if artifact is not None:
                store.records[artifact.stage_name] = artifact
        return store

    def get_aggregated(self, stage_names: List[str]) -> AggregatedArtifact:
        """
        Reads ALL specified stages' artifacts and merges their contents.
        """
        if not stage_names or not any(name in self.records for name in stage_names):
            return AggregatedArtifact(all_passed=True)

        agg = AggregatedArtifact(
            all_passed=True,
            all_files_modified=set(),
            all_files_created=set(),
            metrics={},
            decisions=[],
            interface_changes={},
            failures=[]
        )

        for name in stage_names:
            if name not in self.records:
                continue

            artifact = self.records[name]

            if not artifact.passed:
                agg.all_passed = False
                errors = self._extract_errors(artifact.gate_reports)
                agg.failures.append(FailedStageInfo(
                    stage=artifact.stage_name,
                    iteration=artifact.iteration,
                    errors=errors
                ))

            agg.all_files_modified.update(artifact.files_modified)
            agg.all_files_created.update(artifact.files_created)

            # Merge metrics with namespace prefix: {stage_name}.{metric_name}
            for metric_name, value in artifact.metrics.items():
                agg.metrics[f"{artifact.stage_name}.{metric_name}"] = value

            agg.decisions.extend(artifact.decisions)

            if artifact.interface_changes:
                agg.interface_changes[artifact.stage_name] = artifact.interface_changes

        return agg

    def _extract_errors(self, gate_reports: List[Any]) -> List[Dict[str, Any]]:
        """Extract error info from failed gate reports.

        Reads fields actually present on GateReport (evidence, suggestion,
        check_type, level).
        """
        errors: List[Dict[str, Any]] = []
        for report in gate_reports:
            is_passed = getattr(report, 'passed', False)
            if is_passed:
                continue
            errors.append({
                "source": getattr(report, 'check_type', 'unknown'),
                "level": getattr(report, 'level', ''),
                "evidence": getattr(report, 'evidence', ''),
                "suggestion": getattr(report, 'suggestion', ''),
            })
        return errors

    def get_stage_artifact(self, stage_name: str) -> Optional[StageArtifact]:
        """Returns the artifact for the given stage name, if it exists."""
        return self.records.get(stage_name)

    def clear(self) -> None:
        """Reset all records (in-memory only; on-disk files are kept)."""
        self.records.clear()


# ---------------------------------------------------------------- serdes


_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def _safe_name(name: str) -> str:
    """Make a stage name safe as a filesystem path component."""
    return _SAFE_NAME_RE.sub("_", name) or "unnamed"


def _failure_context_to_dict(pfc) -> Optional[dict]:
    if pfc is None:
        return None
    return {
        "source_stage": pfc.source_stage,
        "error_class": pfc.error_class,
        "error_class_reason": pfc.error_class_reason,
        "execution_log": pfc.execution_log,
        "errors": [
            {"file": e.file, "line": e.line, "code": e.code,
             "severity": e.severity, "message": e.message}
            for e in (pfc.errors or [])
        ],
        "previous_attempts": [
            {"iteration": pa.iteration, "result": pa.result,
             "agent_notes": pa.agent_notes, "error_class": pa.error_class}
            for pa in (pfc.previous_attempts or [])
        ],
        "modified_files": pfc.modified_files,
        "iteration_count": pfc.iteration_count,
    }


def _report_to_dict(r: Any) -> dict:
    if isinstance(r, GateReport):
        return asdict(r)
    if isinstance(r, dict):
        return r
    return {
        "level": getattr(r, "level", ""),
        "check_type": getattr(r, "check_type", ""),
        "passed": bool(getattr(r, "passed", False)),
        "evidence": getattr(r, "evidence", ""),
        "details": getattr(r, "details", {}) or {},
        "suggestion": getattr(r, "suggestion", ""),
    }


def _artifact_to_json(artifact: StageArtifact) -> dict:
    ts = artifact.timestamp
    ts_iso = ts.isoformat() if isinstance(ts, datetime) else str(ts)
    payload = {
        "stage_name": artifact.stage_name,
        "iteration": artifact.iteration,
        "passed": artifact.passed,
        "timestamp": ts_iso,
        "files_modified": list(artifact.files_modified),
        "files_created": list(artifact.files_created),
        "gate_reports": [_report_to_dict(r) for r in artifact.gate_reports],
        "metrics": dict(artifact.metrics),
        "decisions": list(artifact.decisions),
        "interface_changes": artifact.interface_changes,
        "current_status": artifact.current_status,
        "session_id": artifact.session_id or "",
        "execution_log": artifact.execution_log or "",
    }
    if artifact.previous_attempt is not None:
        payload["previous_attempt"] = artifact.previous_attempt
    if artifact.pending_failure_context is not None:
        payload["pending_failure_context"] = artifact.pending_failure_context
    return payload


def _artifact_from_json(data: dict) -> Optional[StageArtifact]:
    try:
        ts_raw = data.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_raw) if ts_raw else datetime.now()
        except ValueError:
            ts = datetime.now()
        reports = [GateReport(**r) for r in data.get("gate_reports", [])
                   if isinstance(r, dict)]
        return StageArtifact(
            stage_name=data["stage_name"],
            iteration=int(data.get("iteration", 0)),
            passed=bool(data.get("passed", False)),
            timestamp=ts,
            files_modified=list(data.get("files_modified", [])),
            files_created=list(data.get("files_created", [])),
            gate_reports=reports,
            metrics=dict(data.get("metrics", {})),
            decisions=list(data.get("decisions", [])),
            interface_changes=data.get("interface_changes", []),
            current_status=data.get("current_status", "PENDING"),
            previous_attempt=data.get("previous_attempt"),
            pending_failure_context=data.get("pending_failure_context"),
            session_id=data.get("session_id", ""),
            execution_log=data.get("execution_log", ""),
        )
    except (KeyError, TypeError, ValueError):
        return None

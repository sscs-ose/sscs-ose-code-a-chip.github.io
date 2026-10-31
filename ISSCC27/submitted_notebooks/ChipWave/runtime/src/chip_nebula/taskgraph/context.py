"""Attempt context assembly from fixed definition plus actual current work."""

from __future__ import annotations

import json

from .domain import Artifact, Attempt, WorkItem
from .static_store import StaticTaskGraphStore


class AttemptContextAssembler:
    def __init__(self, store: StaticTaskGraphStore) -> None:
        self.store = store

    def build(self, attempt: Attempt) -> str:
        work = self.store.work_items(attempt.work_item_ids)

        def failed_gate_reports(artifact: Artifact) -> list[dict]:
            producer = self.store.get_attempt(artifact.producer.attempt_id)
            return [dict(report) for report in producer.diagnostics.get("gate_reports", [])
                    if report.get("passed") is False] if producer else []

        inputs = []
        for name, artifact_id in attempt.input_deliveries.items():
            artifact = self.store.get_artifact(artifact_id)
            if artifact is None:
                raise FileNotFoundError(f"Attempt input Artifact is unavailable: {artifact_id}")
            inputs.append({
                "name": name,
                "artifact_id": artifact.id,
                "type": artifact.type,
                "content": artifact.content.__dict__,
                "complete_record_path": artifact.input_manifest_path,
                "summary": _payload_summary(artifact.payload),
                "failed_gate_reports": failed_gate_reports(artifact),
            })
        evidence = []
        evidence_ids = dict.fromkeys(
            artifact_id
            for item in work
            for artifact_id in item.evidence_artifact_ids
        )
        for artifact_id in evidence_ids:
            artifact = self.store.get_artifact(artifact_id)
            if artifact is None:
                raise FileNotFoundError(
                    f"Attempt feedback evidence is unavailable: {artifact_id}"
                )
            evidence.append({
                "artifact_id": artifact.id,
                "type": artifact.type,
                "content": artifact.content.__dict__,
                "complete_record_path": artifact.input_manifest_path,
                "summary": _payload_summary(artifact.payload),
                "failed_gate_reports": failed_gate_reports(artifact),
            })
        site = self.store.recoverable_site(attempt.task_id)
        task = self.store.get_task(attempt.task_id)
        failures = [self.store.get_attempt(item_id) for item_id in dict.fromkeys(
            item_id for item in work for item_id in item.evidence_attempt_ids
        )]
        previous = next((item for item in reversed(self.store.list_attempts(task.id))
                         if item.id != attempt.id and item.status.value == "failed"), None)
        dynamic = {
            "work_items": [_work_context(item) for item in work],
            "workflow_tasks": [{
                "id": task.id, "key": task.key, "role": task.role,
                "outputs": {output.name: output.artifact_type for output in task.outputs},
                "permission": task.permission.__dict__,
                "gates": [gate.__dict__ for gate in task.hard_gates],
            } for task in self.store.list_tasks(task.workflow_id)],
            "current_inputs": inputs,
            "feedback_evidence": evidence,
            "resume_site": _resume_context(site) if site else None,
            "previous_failure": self.failure_context(previous) if previous else None,
            "failure_evidence": [self.failure_context(item) for item in failures if item],
        }
        permission = attempt.permission
        return (
            "# Role\n"
            f"{attempt.role_instruction.strip()}\n\n"
            "# Frozen task brief\n"
            f"Objective: {attempt.brief.objective}\n"
            f"Deliverables: {json.dumps(attempt.brief.deliverables, ensure_ascii=False)}\n"
            f"Responsibilities: {json.dumps(attempt.brief.responsibilities, ensure_ascii=False)}\n"
            f"Exclusions: {json.dumps(attempt.brief.exclusions, ensure_ascii=False)}\n"
            f"Completion criteria: {json.dumps(attempt.brief.completion_criteria, ensure_ascii=False)}\n"
            f"Collaboration: {json.dumps(attempt.brief.collaboration, ensure_ascii=False)}\n\n"
            "# Enforced permission\n"
            f"Read: {json.dumps(permission.read_paths)}\n"
            f"Write: {json.dumps(permission.write_paths)}\n"
            f"Tools: {json.dumps(permission.tools)}\n\n"
            "# This attempt's actual context\n"
            f"{json.dumps(dynamic, ensure_ascii=False, indent=2)}\n\n"
            "Complete the frozen brief while handling only the captured work above. "
            "Artifact summaries may be truncated. Read each complete_record_path for the "
            "full immutable payload, including inline source content. These captured input "
            "records and failure evidence directories are read-only platform context. "
            "The workflow task catalog is read-only context, not additional authorization. "
            "Do not expand the objective or permissions. Preserve valid existing work."
        )

    def failure_context(self, attempt: Attempt) -> dict:
        task = self.store.get_task(attempt.task_id)
        return {
            "attempt_id": attempt.id, "task_id": task.id, "task_key": task.key,
            "status": attempt.status.value, "engineering_verdict": attempt.verdict,
            "failure_reason": str(attempt.diagnostics.get("failure_reason", ""))[:6000],
            "execution_log_tail": str(attempt.diagnostics.get("execution_log", ""))[-6000:],
            "gate_reports": [dict(report) for report in attempt.diagnostics.get("gate_reports", [])],
            "input_deliveries": dict(attempt.input_deliveries),
            "workspace_commit": attempt.workspace_commit,
            "captured_resume_site": attempt.diagnostics.get("resume_site"),
            "modified_path_count": len(attempt.diagnostics.get("changed_paths", [])),
            "modified_paths_sample": list(attempt.diagnostics.get("changed_paths", []))[:32],
            "evidence_directory": f".nebula_inputs/{attempt.id}",
            "frozen_brief": attempt.brief.__dict__,
            "permission": attempt.permission.__dict__,
            "attempts_used": len(self.store.list_attempts(task.id)),
            "configured_max_attempts": task.max_attempts,
            "recent_failures": [{
                "attempt_id": item.id,
                "reason": str(item.diagnostics.get("failure_reason", ""))[:1500],
                "workspace_commit": item.workspace_commit,
                "modified_path_count": len(item.diagnostics.get("changed_paths", [])),
            } for item in self.store.list_attempts(task.id)[-4:] if item.status.value == "failed"],
        }


def _work_context(item: WorkItem) -> dict:
    return {
        "id": item.id,
        "kind": item.kind.value,
        "status": item.status.value,
        "summary": item.summary,
        "source_task_id": item.source_task_id,
        "causal_correlation_keys": list(item.causal_correlation_keys),
        "evidence_artifact_ids": list(item.evidence_artifact_ids),
        "evidence_attempt_ids": list(item.evidence_attempt_ids),
    }


def _resume_context(site) -> dict:
    """Describe a restored site without dumping thousands of paths to the LLM."""
    paths = tuple(site.modified_paths)
    groups: dict[str, int] = {}
    for path in paths:
        components = str(path).split("/")
        group = "/".join(components[:2]) if len(components) > 1 else components[0]
        groups[group] = groups.get(group, 0) + 1
    common = sorted(groups.items(), key=lambda item: (-item[1], item[0]))[:24]
    return {
        "task_id": site.task_id,
        "attempt_id": site.attempt_id,
        "session_id": site.session_id,
        "workspace_commit": site.workspace_commit,
        "base_commit": site.base_commit,
        "modified_path_count": len(paths),
        "modified_paths_sample": list(paths[:32]),
        "modified_path_groups": dict(common),
        "failure_reason": site.failure_reason,
    }


def _payload_summary(value, *, depth: int = 0):
    """Bound prompt metadata while keeping exact evidence in the workspace."""
    if depth >= 2:
        if isinstance(value, dict):
            return {"kind": "object", "keys": sorted(map(str, value))[:24]}
        if isinstance(value, (list, tuple)):
            return {"kind": "array", "items": len(value)}
        text = str(value)
        return text if len(text) <= 240 else text[:237] + "..."
    if isinstance(value, dict):
        result = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 24:
                result["__omitted_fields__"] = len(value) - index
                break
            result[str(key)] = _payload_summary(item, depth=depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        return [_payload_summary(item, depth=depth + 1) for item in value[:12]] + (
            [{"__omitted_items__": len(value) - 12}] if len(value) > 12 else []
        )
    text = value if isinstance(value, (str, int, float, bool)) or value is None else str(value)
    if isinstance(text, str) and len(text) > 600:
        return text[:597] + "..."
    return text

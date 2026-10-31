"""Deterministic application of feedback to predefined Tasks."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .domain import Attempt, WorkItemKind, WorkRequest
from .static_recipe import FeedbackRoute
from .static_store import StaticTaskGraphStore


class StaticWorkHandler:
    def __init__(
        self, store: StaticTaskGraphStore, workflow_id: str,
        routes: tuple[FeedbackRoute, ...],
    ) -> None:
        self.store = store
        self.workflow_id = workflow_id
        self.routes = routes

    def requests_for_attempt_failure(self, attempt: Attempt) -> tuple[WorkRequest, ...]:
        work = self.store.work_items(attempt.work_item_ids)
        return self.requests_for_verdict(
            event_id=f"execution-failure:{attempt.id}",
            source_task_id=attempt.task_id, verdict="execution_fail", payloads={},
            evidence_artifact_ids=tuple(artifact_id for artifact_id in attempt.input_deliveries.values()
                                        if self.store.get_artifact(artifact_id) is not None),
            evidence_attempt_ids=(attempt.id,),
            causal_correlation_keys=tuple(dict.fromkeys(
                key for item in work
                for key in (item.correlation_key, *item.causal_correlation_keys)
                if key and key != "initial"
            )),
        )

    def handle_verdict(
        self, *, event_id: str, source_task_id: str, verdict: str,
        payloads: Mapping[str, Mapping[str, Any]] | None = None,
        evidence_artifact_ids: tuple[str, ...] = (),
        evidence_attempt_ids: tuple[str, ...] = (),
        causal_correlation_keys: tuple[str, ...] = (),
    ) -> list:
        requests = self.requests_for_verdict(
            event_id=event_id, source_task_id=source_task_id, verdict=verdict,
            payloads=payloads or {},
            evidence_artifact_ids=evidence_artifact_ids,
            evidence_attempt_ids=evidence_attempt_ids,
            causal_correlation_keys=causal_correlation_keys,
        )
        if not requests:
            return []
        return self.store.apply_work_event(event_id, self.workflow_id, requests)

    def requests_for_verdict(
        self, *, event_id: str, source_task_id: str, verdict: str,
        payloads: Mapping[str, Mapping[str, Any]],
        evidence_artifact_ids: tuple[str, ...] = (),
        evidence_attempt_ids: tuple[str, ...] = (),
        causal_correlation_keys: tuple[str, ...] = (),
    ) -> tuple[WorkRequest, ...]:
        """Resolve declared automatic routes without applying a DB transaction.

        Attempt publication uses this pure step and commits the resulting Work
        requests atomically with Deliveries. Explicit Handler calls can use
        ``handle_verdict`` to apply the same route semantics independently.
        """
        applicable = [
            route for route in self.routes
            if route.source_task_id == source_task_id and route.verdict == verdict
        ]
        requests: list[WorkRequest] = []
        for route in applicable:
            if route.payload_field:
                supplied = _payload_value(payloads, route.payload_field)
                if supplied != route.payload_equals:
                    if route.payload_field.rsplit(".", 1)[-1] != "target_task":
                        continue
                    target = self.store.get_task(route.target_task_id)
                    if (
                        target is None or target.workflow_id != self.workflow_id
                        or route.payload_equals != target.key
                        or supplied not in (target.id, f"task:{target.id}")
                    ):
                        continue
            evidence = evidence_artifact_ids
            attempt_evidence = evidence_attempt_ids
            target = (self.store.get_task(route.target_task_id)
                      if verdict in {"fail", "execution_fail"} and (evidence or attempt_evidence) else None)
            if target and any(
                output.artifact_type == "failure.report" for output in target.outputs
            ):
                source_attempt = self.store.get_attempt(event_id)
                if source_attempt:
                    attempt_evidence = tuple(dict.fromkeys((*attempt_evidence, source_attempt.id)))
                    evidence = tuple(dict.fromkeys((*evidence, *source_attempt.input_deliveries.values())))
            # Follow captured lineage for every feedback owner, never a newer Delivery.
            lineage = list(evidence)
            for artifact_id in lineage:
                artifact = self.store.get_artifact(artifact_id)
                if artifact:
                    for parent_id in artifact.input_artifact_ids:
                        if parent_id not in lineage:
                            lineage.append(parent_id)
            evidence = tuple(lineage)
            if route.kind == WorkItemKind.HUMAN_QUESTION.value:
                items = _decision_items(payloads)
                if items is not None:
                    for item in items:
                        issue_id = str(item.get("id", "")).strip()
                        if not issue_id:
                            raise ValueError(
                                "decision request item requires a stable id"
                            )
                        requests.append(WorkRequest(
                            target_task_id=route.target_task_id,
                            kind=WorkItemKind.HUMAN_QUESTION,
                            request_key=(
                                f"{event_id}:{route.target_task_id}:"
                                f"{route.verdict}:{issue_id}"
                            ),
                            correlation_key=f"decision:{event_id}:{issue_id}",
                            summary=json.dumps(
                                {
                                    "presentation": "decision_card",
                                    "issue_id": issue_id,
                                    "title": str(item.get("title", "需要人工决策")),
                                    "context": str(item.get("context", route.summary)),
                                    "required": bool(item.get("required", True)),
                                    "options": item.get("options", []),
                                    "candidate_ids": item.get("candidate_ids", []),
                                    "compiler_backed": bool(
                                        item.get("compiler_backed", False)
                                    ),
                                },
                                ensure_ascii=False,
                                sort_keys=True,
                            ),
                            causal_correlation_keys=causal_correlation_keys,
                            source_task_id=source_task_id,
                            evidence_artifact_ids=evidence,
                            evidence_attempt_ids=attempt_evidence,
                            propagate_to_dependents=route.propagate_to_dependents,
                        ))
                    continue
            summary = route.summary
            if route.summary_field:
                supplied = _payload_value(payloads, route.summary_field)
                if isinstance(supplied, str) and supplied.strip():
                    summary = supplied.strip()
            requests.append(WorkRequest(
                target_task_id=route.target_task_id,
                kind=WorkItemKind(route.kind),
                request_key=f"{event_id}:{route.target_task_id}:{route.verdict}",
                summary=summary,
                causal_correlation_keys=causal_correlation_keys,
                source_task_id=source_task_id,
                evidence_artifact_ids=evidence,
                evidence_attempt_ids=attempt_evidence,
                propagate_to_dependents=route.propagate_to_dependents,
            ))
        if applicable and not requests and _decision_items(payloads) is None:
            raise ValueError(
                f"no declared feedback route accepted {source_task_id} "
                f"verdict={verdict}; the structured routing decision is "
                "missing or invalid"
            )
        return tuple(requests)


def _payload_value(payloads: Mapping[str, Mapping[str, Any]], field: str) -> Any:
    value: Any = payloads
    for component in field.split("."):
        if not isinstance(value, Mapping) or component not in value:
            return None
        value = value[component]
    return value


def _decision_items(
    payloads: Mapping[str, Mapping[str, Any]],
) -> list[Mapping[str, Any]] | None:
    """Return an explicit decision batch, including an intentional empty one.

    A decision.request is a normal Delivery.  Turning its items into attached
    HUMAN_QUESTION WorkItems is deterministic Handler work, not Task creation
    and not a generic policy DSL.  Empty ``items`` means there is nothing for a
    person to answer and the already-predeclared target Task may proceed.
    """
    batches = [
        value.get("items")
        for value in payloads.values()
        if isinstance(value, Mapping) and "items" in value
    ]
    if not batches:
        return None
    if len(batches) != 1 or not isinstance(batches[0], list):
        raise ValueError("human decision routing requires one items list")
    if any(not isinstance(item, Mapping) for item in batches[0]):
        raise ValueError("decision request items must be objects")
    return list(batches[0])

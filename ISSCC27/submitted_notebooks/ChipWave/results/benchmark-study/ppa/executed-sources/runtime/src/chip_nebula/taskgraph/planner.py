"""One-shot planning of concrete, immutable Task briefs."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Mapping, Protocol

from .domain import DomainError, TaskBrief
from .static_recipe import CompiledStaticRecipe
from .static_store import StaticTaskGraphStore


class PlannerBackend(Protocol):
    def generate(self, prompt: str, *, framework: str, model: str) -> str: ...


class PlanningError(ValueError):
    pass


class TaskBriefPlanner:
    """Ask one planner for all predefined briefs, validate, then freeze once."""

    def __init__(self, backend: PlannerBackend, *, max_corrections: int = 2) -> None:
        self.backend = backend
        self.max_corrections = max_corrections

    def plan_and_freeze(
        self, store: StaticTaskGraphStore, recipe: CompiledStaticRecipe,
    ) -> list:
        prompt = build_planning_prompt(
            recipe,
            {
                name: {
                    "artifact_id": artifact_id,
                    "type": store.get_artifact(artifact_id).type,
                    "complete_record_path": store.get_artifact(artifact_id).input_manifest_path,
                    "payload_summary": summarize_planner_value(
                        store.get_artifact(artifact_id).payload,
                    ),
                }
                for name, artifact_id in recipe.parameter_artifacts.items()
                if store.get_artifact(artifact_id) is not None
            },
        )
        previous = ""
        error = ""
        for correction in range(self.max_corrections + 1):
            request = prompt
            if correction:
                request += (
                    "\n\nYour previous response was rejected before any Task was frozen. "
                    "Correct the complete response; do not return a patch or omit unchanged Tasks.\n"
                    f"Validation error:\n{error}\n\nPrevious response:\n{previous}"
                )
            previous = self.backend.generate(
                request,
                framework=recipe.planner.framework,
                model=recipe.planner.model,
            )
            try:
                briefs = parse_briefs(previous, recipe)
                return store.freeze_briefs(recipe.workflow.id, briefs)
            except (PlanningError, DomainError) as exc:
                error = str(exc)
        raise PlanningError(
            f"planner could not produce a valid complete Task plan after "
            f"{self.max_corrections + 1} attempts: {error}"
        )


def build_planning_prompt(
    recipe: CompiledStaticRecipe,
    workflow_inputs: Mapping[str, object] | None = None,
) -> str:
    roles = {(role.name, role.version): role for role in recipe.roles}
    tasks = []
    for task in recipe.tasks:
        role = roles[(task.role, task.role_version)]
        consumers = [
            candidate.id
            for candidate in recipe.tasks
            if any(
                dependency.upstream_task_id == task.id
                for dependency in candidate.dependencies
            )
        ]
        tasks.append({
            "task_id": task.id,
            "task_key": task.key,
            "role": f"{task.role}@{task.role_version}",
            "role_capability": {
                "instruction": role.instruction,
                "skills": list(role.skills),
                "accepted_types": list(role.accepted_types),
                "produced_types": list(role.produced_types),
            },
            "intent": task.intent,
            "permission": asdict(task.permission),
            "inputs": [
                {"name": item.name, "type": item.required_type, "source": "workflow-input"}
                for item in task.initial_inputs
            ] + [
                {
                    "name": item.input_name, "type": item.required_type,
                    "source_task_id": item.upstream_task_id,
                    "source_output": item.output_name,
                    "release": asdict(item.condition),
                }
                for item in task.dependencies
            ],
            "outputs": [asdict(item) for item in task.outputs],
            "consumers": consumers,
            "required_collaborators": sorted(
                {dependency.upstream_task_id for dependency in task.dependencies}
                | set(consumers)
                | {route.target_task_id for route in recipe.feedback_routes if route.source_task_id == task.id}
            ),
            "hard_gates": [asdict(item) for item in task.hard_gates],
            "executor": task.executor.value,
            "command": task.command,
            "on_demand": task.on_demand,
        })
    schema = {
        "tasks": [{
            "task_id": "exact predefined id",
            "objective": "specific contribution to the workflow goal",
            "deliverables": ["concrete accepted results"],
            "responsibilities": ["what this Task owns"],
            "exclusions": ["what this Task must not do"],
            "completion_criteria": ["concrete criteria including hard gates"],
            "collaboration": ["use task:<exact id or key> references where applicable"],
        }],
    }
    return (
        "You are the one-shot workflow planning agent. Produce one concrete, stable task "
        "brief for every predefined Task. Do not add, remove, merge, split or reorder Tasks; "
        "do not change dependencies, permissions, outputs, or hard gates. The brief freezes "
        "the objective, delivery boundary, and completion standard, but must leave technical "
        "implementation methods to the executing Agent. Do not include runtime failures or "
        "attempt-specific steps. Input summaries may be truncated; read every complete_record_path "
        "for the full immutable payload before planning. These input records are read-only. "
        "Include every required_collaborator as a literal "
        "task:<exact id> token in collaboration[]. Keep briefs concise. Return JSON only.\n\n"
        f"Workflow goal:\n{recipe.workflow.goal}\n\n"
        f"Workflow inputs:\n{json.dumps(workflow_inputs or {}, ensure_ascii=False, indent=2)}\n\n"
        f"Fixed tasks:\n{json.dumps(tasks, ensure_ascii=False, indent=2)}\n\n"
        f"Predeclared feedback routes:\n{json.dumps([asdict(route) for route in recipe.feedback_routes], ensure_ascii=False, indent=2)}\n\n"
        f"Required response shape:\n{json.dumps(schema, ensure_ascii=False, indent=2)}"
    )


def parse_briefs(text: str, recipe: CompiledStaticRecipe) -> dict[str, TaskBrief]:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise PlanningError("planner returned no JSON object")
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise PlanningError(f"planner returned invalid JSON: {exc}") from exc
    rows = raw.get("tasks") if isinstance(raw, Mapping) else None
    if not isinstance(rows, list):
        raise PlanningError("planner response must contain tasks[]")
    expected = {task.id: task for task in recipe.tasks}
    result: dict[str, TaskBrief] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise PlanningError(f"planner task #{index + 1} must be an object")
        allowed = {
            "task_id", "objective", "deliverables", "responsibilities",
            "exclusions", "completion_criteria", "collaboration",
        }
        unknown = sorted(set(row) - allowed)
        if unknown:
            raise PlanningError(f"planner task #{index + 1} has unknown fields: {unknown}")
        task_id = row.get("task_id")
        if task_id not in expected or task_id in result:
            raise PlanningError(f"planner returned unknown or duplicate Task: {task_id}")
        try:
            candidate = TaskBrief(
                objective=_text(row.get("objective"), "objective"),
                deliverables=_list(row.get("deliverables"), "deliverables"),
                responsibilities=_list(row.get("responsibilities"), "responsibilities"),
                exclusions=_list(row.get("exclusions", ()), "exclusions", empty=True),
                completion_criteria=_list(row.get("completion_criteria"), "completion_criteria"),
                collaboration=_list(row.get("collaboration"), "collaboration"),
            )
        except DomainError as exc:
            raise PlanningError(str(exc)) from exc
        task = expected[task_id]
        for gate in task.hard_gates:
            if not any(gate.name in criterion for criterion in candidate.completion_criteria):
                raise PlanningError(
                    f"Task {task.key} brief omits hard gate {gate.name} from completion criteria"
                )
        raw_references = _collaboration_refs(candidate.collaboration)
        ids_by_key = {item.key: item.id for item in recipe.tasks}
        references = {ids_by_key.get(reference, reference) for reference in raw_references}
        required_collaborators = {
            dependency.upstream_task_id for dependency in task.dependencies
        } | {
            consumer.id
            for consumer in recipe.tasks
            if any(
                dependency.upstream_task_id == task.id
                for dependency in consumer.dependencies
            )
        } | {
            route.target_task_id
            for route in recipe.feedback_routes
            if route.source_task_id == task.id
        }
        missing_collaborators = sorted(required_collaborators - references)
        if missing_collaborators:
            raise PlanningError(
                f"Task {task.key} brief omits required collaborators: {missing_collaborators}"
            )
        result[task_id] = candidate
    missing = sorted(set(expected) - set(result))
    if missing:
        raise PlanningError(f"planner omitted predefined Tasks: {missing}")
    return result


def _text(value: object, owner: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlanningError(f"planner {owner} must be a non-empty string")
    return value.strip()


def _list(value: object, owner: str, *, empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (not empty and not value) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise PlanningError(f"planner {owner} must be a string list")
    return tuple(item.strip() for item in value)


def _collaboration_refs(lines: tuple[str, ...]) -> set[str]:
    return {
        match.group(1).rstrip(".,;)")
        for line in lines
        for match in re.finditer(r"task:([A-Za-z0-9_.:-]+)", line)
    }


def summarize_planner_value(value: object, *, depth: int = 0) -> object:
    """Bound Workflow inputs without hiding their engineering shape.

    Planning assigns fixed responsibilities; it does not need every acceptance
    sentence, compiler diagnostic or log line. Full inputs remain available to
    the eventual Task Attempts through Artifact materialization.
    """
    if depth >= 3:
        if isinstance(value, Mapping):
            return {"keys": list(map(str, value.keys()))[:16], "field_count": len(value)}
        if isinstance(value, (list, tuple)):
            return {"item_count": len(value)}
    if isinstance(value, Mapping):
        items = list(value.items())
        result = {
            str(key): summarize_planner_value(item, depth=depth + 1)
            for key, item in items[:24]
        }
        if len(items) > 24:
            result["_omitted_field_count"] = len(items) - 24
        return result
    if isinstance(value, (list, tuple)):
        sample = [summarize_planner_value(item, depth=depth + 1) for item in value[:8]]
        return sample if len(value) <= 8 else {
            "item_count": len(value), "sample": sample,
        }
    if isinstance(value, str) and len(value) > 240:
        return value[:237] + "..."
    return value

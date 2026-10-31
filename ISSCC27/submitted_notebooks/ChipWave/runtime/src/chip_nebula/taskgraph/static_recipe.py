"""Strict Recipe v2 compiler for a fixed Task topology.

Recipe v2 deliberately has no runtime instructions, Task replacement fields,
stage jumps, rework groups, or Role-owned project permissions.  It describes
the finite collaboration that is planned once before execution.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from .domain import (
    Dependency,
    DomainError,
    GateSpec,
    InitialInput,
    JointAnalysisGroup,
    OutputSpec,
    PermissionGrant,
    ReleaseCondition,
    Role,
    Task,
    TaskExecutor,
    Workflow,
    path_scope_covers,
)
from .gate_templates import GateTemplateRegistry, default_gate_template_registry


class StaticRecipeError(ValueError):
    pass


@dataclass(frozen=True)
class FeedbackRoute:
    """A deterministic failed-delivery route between predefined Tasks."""

    source_task_id: str
    verdict: str
    target_task_id: str
    kind: str
    summary: str
    propagate_to_dependents: bool = True
    payload_field: str = ""
    payload_equals: Any = None
    summary_field: str = ""


@dataclass(frozen=True)
class PlannerConfig:
    framework: str = "codex"
    model: str = "gpt-6.1-sol"


@dataclass(frozen=True)
class CompiledStaticRecipe:
    workflow: Workflow
    roles: tuple[Role, ...]
    tasks: tuple[Task, ...]
    parameter_types: Mapping[str, str]
    parameter_artifacts: Mapping[str, str]
    feedback_routes: tuple[FeedbackRoute, ...]
    joint_analysis_groups: tuple[JointAnalysisGroup, ...]
    planner: PlannerConfig


def load_static_recipe(text: str) -> dict[str, Any]:
    try:
        result = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise StaticRecipeError(f"invalid Recipe YAML: {exc}") from exc
    if not isinstance(result, dict):
        raise StaticRecipeError("Recipe root must be a mapping")
    return result


def load_static_role(text: str) -> Role:
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise StaticRecipeError(f"invalid Role YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise StaticRecipeError("Role root must be a mapping")
    allowed = {
        "name", "version", "description", "system_prompt", "accepted_types",
        "produced_types", "skills", "framework", "model",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise StaticRecipeError(
            "Role contains Task/runtime policy fields: " + ", ".join(unknown)
        )
    return Role(
        name=_string(raw, "name", "Role"),
        version=_positive_int(raw.get("version", 1), "Role.version"),
        instruction=_string(raw, "system_prompt", "Role"),
        accepted_types=_strings(raw.get("accepted_types", ()), "Role.accepted_types"),
        produced_types=_strings(raw.get("produced_types", ()), "Role.produced_types"),
        skills=_strings(raw.get("skills", ()), "Role.skills"),
        framework=str(raw.get("framework", "")),
        model=str(raw.get("model", "")),
    )


def load_project_static_roles(project_root: Path) -> dict[str, Role]:
    """Load built-in Role capabilities with project Role overrides.

    Legacy ``agents/`` profiles are intentionally excluded: they mix Task
    authorization and runtime routing into the Role object. New TaskGraph
    workflows may override a capability only through ``.chip_nebula/roles``.
    """
    from chip_nebula.project import get_roles_dir

    builtin = Path(__file__).parents[1] / "configs" / "roles"
    result: dict[str, Role] = {}
    for directory in (builtin, get_roles_dir(project_root)):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.yaml")):
            if path.name.startswith(("_", ".")):
                continue
            role = load_static_role(path.read_text(encoding="utf-8"))
            result[role.name] = role
    return result


class StaticRecipeCompiler:
    """Compile the entire fixed graph without creating execution Attempts."""

    _TOP_LEVEL = {
        "name", "version", "parameters", "planner", "tasks", "feedback",
        "joint_analysis",
    }
    _TASK_KEYS = {
        "role", "intent", "permission", "inputs", "outputs", "gates",
        "execution", "required", "on_demand", "max_attempts", "display_group",
    }

    def __init__(
        self, roles: Mapping[str, Role],
        gate_templates: GateTemplateRegistry | None = None,
    ) -> None:
        self.roles = roles
        self.gate_templates = gate_templates or default_gate_template_registry()

    def compile(
        self,
        document: Mapping[str, Any],
        *,
        workflow_id: str,
        goal: str,
        parameters: Mapping[str, str],
    ) -> CompiledStaticRecipe:
        self._unknown(document, self._TOP_LEVEL, "Recipe")
        name = _string(document, "name", "Recipe")
        version = _positive_int(document.get("version", 2), "Recipe.version")
        if version != 2:
            raise StaticRecipeError(
                f"fixed Task/Attempt workflows require Recipe.version=2, got {version}"
            )
        parameter_types = self._parameters(document.get("parameters", {}))
        if set(parameters) != set(parameter_types):
            raise StaticRecipeError(
                f"parameter mismatch; missing={sorted(set(parameter_types) - set(parameters))}, "
                f"extra={sorted(set(parameters) - set(parameter_types))}"
            )
        if any(not isinstance(value, str) or not value for value in parameters.values()):
            raise StaticRecipeError("every parameter must reference a real Artifact id")
        raw_tasks = document.get("tasks")
        if not isinstance(raw_tasks, Mapping) or not raw_tasks:
            raise StaticRecipeError("Recipe.tasks must be a non-empty mapping")
        task_ids = {key: f"{workflow_id}:{key}" for key in raw_tasks}
        declared_outputs = self._outputs(raw_tasks)
        tasks = tuple(
            self._task(
                workflow_id, key, raw, task_ids, declared_outputs,
                parameter_types, parameters,
            )
            for key, raw in raw_tasks.items()
        )
        self._acyclic(tasks)
        routes = self._feedback(
            document.get("feedback", ()), task_ids,
        )
        by_id = {task.id: task for task in tasks}
        for route in routes:
            if route.verdict == "execution_fail":
                target = by_id[route.target_task_id]
                if (
                    route.source_task_id == route.target_task_id or not target.on_demand
                    or target.dependencies or target.executor != TaskExecutor.AGENT
                    or target.permission.write_paths
                    or not any(output.artifact_type == "failure.report" for output in target.outputs)
                    or route.kind != "feedback" or route.propagate_to_dependents
                    or route.payload_field
                ):
                    raise StaticRecipeError(
                        "execution_fail requires an independent on-demand Agent diagnostic "
                        "Task, feedback without propagation or payload conditions"
                    )
        groups = self._joint_analysis(
            document.get("joint_analysis", ()), workflow_id, task_ids, tasks,
        )
        used_roles: list[Role] = []
        for task in tasks:
            value = self.roles.get(task.role)
            if value is None or value.version != task.role_version:
                raise StaticRecipeError(f"Task {task.key} references unavailable Role {task.role}")
            if value not in used_roles:
                used_roles.append(value)
        digest = "sha256:" + hashlib.sha256(json.dumps(
            document, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest()
        workflow = Workflow(
            id=workflow_id, recipe=f"{name}@{version}", goal=goal,
            definition_digest=digest,
        )
        planner_raw = document.get("planner", {})
        if not isinstance(planner_raw, Mapping):
            raise StaticRecipeError("Recipe.planner must be a mapping")
        self._unknown(planner_raw, {"framework", "model"}, "Recipe.planner")
        planner = PlannerConfig(
            framework=str(planner_raw.get("framework", "codex")),
            model=str(planner_raw.get("model", "gpt-6.1-sol")),
        )
        return CompiledStaticRecipe(
            workflow=workflow, roles=tuple(used_roles), tasks=tasks,
            parameter_types=parameter_types,
            parameter_artifacts=dict(parameters),
            feedback_routes=routes, joint_analysis_groups=groups,
            planner=planner,
        )

    @staticmethod
    def _parameters(raw: Any) -> dict[str, str]:
        if not isinstance(raw, Mapping):
            raise StaticRecipeError("Recipe.parameters must be a mapping")
        result: dict[str, str] = {}
        for key, value in raw.items():
            if isinstance(value, str):
                result[str(key)] = value
            elif isinstance(value, Mapping) and set(value) == {"type"}:
                result[str(key)] = _string(value, "type", f"parameter {key}")
            else:
                raise StaticRecipeError(f"parameter {key} must only declare type")
        return result

    @staticmethod
    def _outputs(raw_tasks: Mapping[str, Any]) -> dict[tuple[str, str], OutputSpec]:
        result: dict[tuple[str, str], OutputSpec] = {}
        for task_key, raw in raw_tasks.items():
            if not isinstance(raw, Mapping):
                raise StaticRecipeError(f"Task {task_key} must be a mapping")
            outputs = raw.get("outputs", {})
            if not isinstance(outputs, Mapping):
                raise StaticRecipeError(f"Task {task_key}.outputs must be a mapping")
            for output_name, value in outputs.items():
                if isinstance(value, str):
                    spec = OutputSpec(str(output_name), value)
                elif isinstance(value, Mapping):
                    unknown = set(value) - {"type", "schema_version", "paths"}
                    if unknown:
                        raise StaticRecipeError(
                            f"Task {task_key} output {output_name} has unsupported keys: {sorted(unknown)}"
                        )
                    spec = OutputSpec(
                        str(output_name), _string(value, "type", f"output {output_name}"),
                        _positive_int(value.get("schema_version", 1), "output.schema_version"),
                        _strings(value.get("paths", ()), f"output {output_name}.paths"),
                    )
                else:
                    raise StaticRecipeError(f"Task {task_key} output {output_name} is invalid")
                result[(str(task_key), str(output_name))] = spec
        return result

    def _task(
        self, workflow_id: str, key: str, raw: Any,
        task_ids: Mapping[str, str], outputs: Mapping[tuple[str, str], OutputSpec],
        parameter_types: Mapping[str, str], parameters: Mapping[str, str],
    ) -> Task:
        if not isinstance(raw, Mapping):
            raise StaticRecipeError(f"Task {key} must be a mapping")
        self._unknown(raw, self._TASK_KEYS, f"Task {key}")
        if "instruction" in raw:
            raise StaticRecipeError(f"Task {key} must use intent, not an execution prompt")
        role_name = _string(raw, "role", f"Task {key}")
        role = self.roles.get(role_name)
        if role is None:
            raise StaticRecipeError(f"Task {key} references unknown Role {role_name}")
        permission = self._permission(raw.get("permission", {}), key)
        initial: list[InitialInput] = []
        dependencies: list[Dependency] = []
        inputs = raw.get("inputs", {})
        if not isinstance(inputs, Mapping):
            raise StaticRecipeError(f"Task {key}.inputs must be a mapping")
        for input_name, spec in inputs.items():
            if not isinstance(spec, Mapping):
                raise StaticRecipeError(f"Task {key} input {input_name} must be a mapping")
            self._unknown(spec, {"type", "from", "optional", "release"}, f"Task {key} input {input_name}")
            required_type = _string(spec, "type", f"Task {key} input {input_name}")
            source = _string(spec, "from", f"Task {key} input {input_name}")
            optional = bool(spec.get("optional", False))
            if source.startswith("$parameters."):
                parameter = source.removeprefix("$parameters.")
                if parameter_types.get(parameter) != required_type:
                    raise StaticRecipeError(f"Task {key} input {input_name} parameter type mismatch")
                initial.append(InitialInput(
                    name=str(input_name), required_type=required_type,
                    artifact_id=parameters[parameter], optional=optional,
                ))
                continue
            prefix = "$tasks."
            marker = ".outputs."
            if not source.startswith(prefix) or marker not in source:
                raise StaticRecipeError(f"Task {key} input {input_name} has invalid source {source}")
            owner, output_name = source[len(prefix):].split(marker, 1)
            output = outputs.get((owner, output_name))
            if owner not in task_ids or output is None or output.artifact_type != required_type:
                raise StaticRecipeError(f"Task {key} input {input_name} source/type mismatch")
            unreadable = [
                path for path in output.paths
                if not any(path_scope_covers(grant, path) for grant in permission.read_paths)
            ]
            if unreadable:
                raise StaticRecipeError(
                    f"Task {key} input {input_name} exposes upstream paths outside its "
                    f"read grant: {unreadable}"
                )
            release = spec.get("release", {})
            if not isinstance(release, Mapping) or set(release) - {"field", "equals"}:
                raise StaticRecipeError(f"Task {key} input {input_name}.release is invalid")
            dependencies.append(Dependency(
                input_name=str(input_name), upstream_task_id=task_ids[owner],
                output_name=output_name, required_type=required_type,
                condition=ReleaseCondition(
                    field=str(release.get("field", "")), equals=release.get("equals"),
                ), optional=optional,
            ))
        execution = raw.get("execution", {})
        if not isinstance(execution, Mapping):
            raise StaticRecipeError(f"Task {key}.execution must be a mapping")
        self._unknown(
            execution, {
                "executor", "command", "framework", "model",
                "reasoning_effort", "timeout_seconds",
            },
            f"Task {key}.execution",
        )
        try:
            executor = TaskExecutor(str(execution.get("executor", "agent")))
        except ValueError as exc:
            raise StaticRecipeError(
                f"Task {key}.execution.executor is invalid"
            ) from exc
        command = str(execution.get("command", "")).strip()
        if executor == TaskExecutor.TOOL and not command:
            raise StaticRecipeError(f"Task {key} tool executor requires command")
        if executor != TaskExecutor.TOOL and command:
            raise StaticRecipeError(f"Task {key} non-tool executor cannot declare command")
        gates = raw.get("gates", ())
        if not isinstance(gates, Sequence) or isinstance(gates, (str, bytes)):
            raise StaticRecipeError(f"Task {key}.gates must be a list")
        gate_specs: list[GateSpec] = []
        for gate in gates:
            if not isinstance(gate, Mapping):
                raise StaticRecipeError(f"Task {key} has an invalid hard gate")
            self._unknown(
                gate,
                {"name", "kind", "template", "version", "parameters", "on_failure"},
                f"Task {key} gate",
            )
            parameters_raw = gate.get("parameters", {})
            if not isinstance(parameters_raw, Mapping):
                raise StaticRecipeError(f"Task {key} gate parameters must be a mapping")
            name = _string(gate, "name", f"Task {key} gate")
            on_failure = str(gate.get("on_failure", "retry"))
            template_id = str(gate.get("template", ""))
            if template_id:
                if gate.get("kind"):
                    raise StaticRecipeError(
                        f"Task {key} gate {name} cannot declare both template and kind"
                    )
                try:
                    binding = self.gate_templates.get(
                        template_id, _positive_int(gate.get("version", 1), "Gate.version"),
                    ).instantiate(
                        name=name, parameters=dict(parameters_raw), on_failure=(
                            "retry" if on_failure == "retry" else "report"
                        ),
                    )
                except Exception as exc:
                    raise StaticRecipeError(
                        f"Task {key} gate {name} cannot be instantiated: {exc}"
                    ) from exc
                resolved = dict(binding.resolved)
                kind = str(resolved.pop("type"))
                resolved.pop("on_failure", None)
                gate_specs.append(GateSpec(
                    name=name, kind=kind, parameters=resolved,
                    on_failure=on_failure,
                ))
            else:
                if "version" in gate:
                    raise StaticRecipeError(
                        f"Task {key} gate {name} version is only valid with template"
                    )
                gate_specs.append(GateSpec(
                    name=name,
                    kind=_string(gate, "kind", f"Task {key} gate"),
                    parameters=dict(parameters_raw), on_failure=on_failure,
                ))
        task_outputs = tuple(
            spec for (owner, _), spec in outputs.items() if owner == key
        )
        if executor == TaskExecutor.HUMAN:
            if (
                len(task_outputs) != 1
                or task_outputs[0].artifact_type != "human.decision"
                or task_outputs[0].schema_version != 1
                or task_outputs[0].paths
            ):
                raise StaticRecipeError(
                    f"Task {key} human executor must declare exactly one inline "
                    "human.decision@1 output"
                )
            if permission.write_paths or permission.tools or gate_specs:
                raise StaticRecipeError(
                    f"Task {key} human executor cannot declare write paths, tools, or gates"
                )
        granted_paths = permission.read_paths + permission.write_paths
        for output in task_outputs:
            unauthorized = [
                path for path in output.paths
                if not any(path_scope_covers(grant, path) for grant in granted_paths)
            ]
            if unauthorized:
                raise StaticRecipeError(
                    f"Task {key} output {output.name} exposes paths outside its read/write "
                    f"grant: {unauthorized}"
                )
        input_types = {
            item.required_type for item in initial
        } | {
            item.required_type for item in dependencies
        }
        if role.accepted_types and not input_types <= set(role.accepted_types):
            raise StaticRecipeError(
                f"Task {key} gives Role {role.name} unsupported inputs: "
                f"{sorted(input_types - set(role.accepted_types))}"
            )
        output_types = {item.artifact_type for item in task_outputs}
        if role.produced_types and not output_types <= set(role.produced_types):
            raise StaticRecipeError(
                f"Task {key} asks Role {role.name} for unsupported outputs: "
                f"{sorted(output_types - set(role.produced_types))}"
            )
        return Task(
            id=task_ids[key], workflow_id=workflow_id, key=key,
            role=role.name, role_version=role.version,
            intent=_string(raw, "intent", f"Task {key}"), permission=permission,
            initial_inputs=tuple(initial), dependencies=tuple(dependencies),
            outputs=task_outputs,
            hard_gates=tuple(gate_specs),
            executor=executor, command=command,
            framework=str(execution.get("framework", role.framework)),
            model=str(execution.get("model", role.model)),
            reasoning_effort=str(execution.get("reasoning_effort", "")),
            required=bool(raw.get("required", True)),
            on_demand=bool(raw.get("on_demand", False)),
            display_group=str(raw.get("display_group", "")),
            max_attempts=_positive_int(raw.get("max_attempts", 8), f"Task {key}.max_attempts"),
            timeout_seconds=_positive_int(
                execution.get("timeout_seconds", 5400),
                f"Task {key}.execution.timeout_seconds",
            ),
        )

    @staticmethod
    def _permission(raw: Any, key: str) -> PermissionGrant:
        if not isinstance(raw, Mapping):
            raise StaticRecipeError(f"Task {key}.permission must be a mapping")
        unknown = set(raw) - {"read", "write", "tools"}
        if unknown:
            raise StaticRecipeError(f"Task {key}.permission has unknown keys: {sorted(unknown)}")
        return PermissionGrant(
            read_paths=_strings(raw.get("read", ()), f"Task {key}.permission.read"),
            write_paths=_strings(raw.get("write", ()), f"Task {key}.permission.write"),
            tools=_strings(raw.get("tools", ()), f"Task {key}.permission.tools"),
        )

    @staticmethod
    def _feedback(raw: Any, task_ids: Mapping[str, str]) -> tuple[FeedbackRoute, ...]:
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            raise StaticRecipeError("Recipe.feedback must be a list")
        result: list[FeedbackRoute] = []
        for index, item in enumerate(raw):
            if not isinstance(item, Mapping):
                raise StaticRecipeError(f"feedback #{index + 1} must be a mapping")
            unknown = set(item) - {
                "source", "verdict", "target", "kind", "summary", "propagate",
                "when", "summary_field",
            }
            if unknown:
                raise StaticRecipeError(f"feedback #{index + 1} has unknown keys: {sorted(unknown)}")
            source = _string(item, "source", f"feedback #{index + 1}")
            target = _string(item, "target", f"feedback #{index + 1}")
            if source not in task_ids or target not in task_ids:
                raise StaticRecipeError(f"feedback #{index + 1} targets an unknown Task")
            kind = str(item.get("kind", "feedback"))
            try:
                from .domain import WorkItemKind
                WorkItemKind(kind)
            except ValueError as exc:
                raise StaticRecipeError(
                    f"feedback #{index + 1} has unsupported work kind {kind}"
                ) from exc
            condition = item.get("when", {})
            if not isinstance(condition, Mapping) or set(condition) - {"field", "equals"}:
                raise StaticRecipeError(f"feedback #{index + 1}.when is invalid")
            field = str(condition.get("field", ""))
            if condition and not field:
                raise StaticRecipeError(f"feedback #{index + 1}.when.field is required")
            result.append(FeedbackRoute(
                source_task_id=task_ids[source],
                verdict=str(item.get("verdict", "fail")),
                target_task_id=task_ids[target],
                kind=kind,
                summary=_string(item, "summary", f"feedback #{index + 1}"),
                propagate_to_dependents=bool(item.get("propagate", True)),
                payload_field=field,
                payload_equals=condition.get("equals"),
                summary_field=str(item.get("summary_field", "")),
            ))
        return tuple(result)

    @staticmethod
    def _joint_analysis(
        raw: Any, workflow_id: str, task_ids: Mapping[str, str], tasks: Sequence[Task],
    ) -> tuple[JointAnalysisGroup, ...]:
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            raise StaticRecipeError("Recipe.joint_analysis must be a list")
        by_id = {task.id: task for task in tasks}
        result: list[JointAnalysisGroup] = []
        for index, item in enumerate(raw):
            if not isinstance(item, Mapping):
                raise StaticRecipeError(f"joint_analysis #{index + 1} must be a mapping")
            unknown = set(item) - {"name", "members", "analyzer"}
            if unknown:
                raise StaticRecipeError(
                    f"joint_analysis #{index + 1} has unknown keys: {sorted(unknown)}"
                )
            name = _string(item, "name", f"joint_analysis #{index + 1}")
            members = _strings(item.get("members"), f"joint_analysis {name}.members")
            analyzer = _string(item, "analyzer", f"joint_analysis {name}")
            if any(member not in task_ids for member in members) or analyzer not in task_ids:
                raise StaticRecipeError(f"joint_analysis {name} references an unknown Task")
            if not by_id[task_ids[analyzer]].on_demand:
                raise StaticRecipeError(f"joint_analysis {name} analyzer must be on-demand")
            result.append(JointAnalysisGroup(
                id=f"{workflow_id}:joint:{name}", workflow_id=workflow_id,
                member_task_ids=tuple(task_ids[member] for member in members),
                analyzer_task_id=task_ids[analyzer],
            ))
        return tuple(result)

    @staticmethod
    def _unknown(raw: Mapping, allowed: set[str], owner: str) -> None:
        unknown = sorted(set(raw) - allowed)
        if unknown:
            raise StaticRecipeError(f"{owner} has unknown fields: {', '.join(unknown)}")

    @staticmethod
    def _acyclic(tasks: Sequence[Task]) -> None:
        try:
            from .static_store import StaticTaskGraphStore
            StaticTaskGraphStore._assert_acyclic(tasks)
        except DomainError as exc:
            raise StaticRecipeError(str(exc)) from exc


def _string(raw: Mapping[str, Any], key: str, owner: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise StaticRecipeError(f"{owner}.{key} must be a non-empty string")
    return value.strip()


def _strings(raw: Any, owner: str) -> tuple[str, ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or any(
        not isinstance(item, str) or not item for item in raw
    ):
        raise StaticRecipeError(f"{owner} must be a string list")
    return tuple(raw)


def _positive_int(value: Any, owner: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise StaticRecipeError(f"{owner} must be a positive integer")
    return value

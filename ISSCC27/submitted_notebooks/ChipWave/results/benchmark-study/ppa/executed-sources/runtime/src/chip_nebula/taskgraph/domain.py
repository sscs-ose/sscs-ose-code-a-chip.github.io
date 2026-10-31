"""Domain objects for static Task workflows and append-only Attempts.

The execution graph is frozen before the first Attempt.  Runtime change is
represented by WorkItems, Attempts and Deliveries, never by cloning Tasks or
rewriting dependencies.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def path_scope_covers(outer: str, inner: str) -> bool:
    """Conservatively prove that a configured project path scope contains another."""
    if outer == inner:
        return True
    wildcard = min(
        (outer.find(character) for character in "*?[" if character in outer),
        default=-1,
    )
    if wildcard < 0:
        return False
    outer_prefix = outer[:wildcard].rstrip("/")
    inner_prefix = inner
    for character in "*?[":
        inner_prefix = inner_prefix.split(character, 1)[0]
    inner_prefix = inner_prefix.rstrip("/")
    return not outer_prefix or (
        inner_prefix == outer_prefix
        or inner_prefix.startswith(outer_prefix + "/")
    )


class DomainError(ValueError):
    """A static workflow invariant was violated."""


class WorkflowStatus(str, Enum):
    PLANNING = "planning"
    READY = "ready"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETE = "complete"


class TaskState(str, Enum):
    IDLE = "idle"
    WAITING = "waiting"
    READY = "ready"
    RUNNING = "running"
    SATISFIED = "satisfied"
    PAUSED = "paused"


class AttemptStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkItemKind(str, Enum):
    INITIAL = "initial"
    FEEDBACK = "feedback"
    REVERIFY = "reverify"
    CLARIFICATION = "clarification"
    HUMAN_QUESTION = "human_question"
    HUMAN_ANSWER = "human_answer"


class WorkItemStatus(str, Enum):
    PENDING = "pending"
    RESOLVED = "resolved"


class TaskExecutor(str, Enum):
    AGENT = "agent"
    TOOL = "tool"
    HUMAN = "human"


@dataclass(frozen=True)
class Role:
    """Reusable capability identity; project authorization belongs to Tasks."""

    name: str
    version: int
    instruction: str
    accepted_types: tuple[str, ...] = ()
    produced_types: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    framework: str = ""
    model: str = ""

    def __post_init__(self) -> None:
        if not self.name or self.version < 1 or not self.instruction.strip():
            raise DomainError("Role requires name, positive version and instruction")


@dataclass(frozen=True)
class PermissionGrant:
    read_paths: tuple[str, ...] = ()
    write_paths: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class OutputSpec:
    name: str
    artifact_type: str
    schema_version: int = 1
    paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name or not self.artifact_type or self.schema_version < 1:
            raise DomainError("OutputSpec requires name, type and positive schema version")
        if any(not path.strip() for path in self.paths):
            raise DomainError("OutputSpec paths must be non-empty patterns")


@dataclass(frozen=True)
class GateSpec:
    """A fully instantiated deterministic acceptance condition."""

    name: str
    kind: str
    parameters: Mapping[str, Any]
    on_failure: str = "retry"

    def __post_init__(self) -> None:
        if not self.name or not self.kind:
            raise DomainError("GateSpec requires name and kind")
        if self.on_failure not in {"retry", "feedback", "pause", "report"}:
            raise DomainError(f"unsupported Gate failure action: {self.on_failure}")


@dataclass(frozen=True)
class ReleaseCondition:
    """Deterministic condition applied to an upstream Delivery payload."""

    field: str = ""
    equals: Any = None

    def accepts(self, payload: Mapping[str, Any]) -> bool:
        if not self.field:
            return True
        value: Any = payload
        for component in self.field.split("."):
            if not isinstance(value, Mapping) or component not in value:
                return False
            value = value[component]
        return value == self.equals


@dataclass(frozen=True)
class Dependency:
    input_name: str
    upstream_task_id: str
    output_name: str
    required_type: str
    condition: ReleaseCondition = ReleaseCondition()
    optional: bool = False

    def __post_init__(self) -> None:
        if not all((self.input_name, self.upstream_task_id, self.output_name, self.required_type)):
            raise DomainError("Dependency requires input, upstream Task, output and type")


@dataclass(frozen=True)
class InitialInput:
    """A Workflow-start input; its id is a retrieval reference only."""

    name: str
    required_type: str
    artifact_id: str
    optional: bool = False

    def __post_init__(self) -> None:
        if not self.name or not self.required_type or (not self.optional and not self.artifact_id):
            raise DomainError("InitialInput requires a name, type and Artifact reference")


@dataclass(frozen=True)
class TaskBrief:
    objective: str
    deliverables: tuple[str, ...]
    responsibilities: tuple[str, ...]
    exclusions: tuple[str, ...]
    completion_criteria: tuple[str, ...]
    collaboration: tuple[str, ...]

    def __post_init__(self) -> None:
        collections = (
            self.deliverables, self.responsibilities, self.completion_criteria,
            self.collaboration,
        )
        if not self.objective.strip() or any(not values for values in collections):
            raise DomainError(
                "TaskBrief requires an objective, deliverables, responsibilities, "
                "completion criteria and collaboration rules"
            )

    @property
    def digest(self) -> str:
        encoded = json.dumps(
            {
                "objective": self.objective,
                "deliverables": self.deliverables,
                "responsibilities": self.responsibilities,
                "exclusions": self.exclusions,
                "completion_criteria": self.completion_criteria,
                "collaboration": self.collaboration,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return "sha256:" + hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class Task:
    id: str
    workflow_id: str
    key: str
    role: str
    role_version: int
    intent: str
    permission: PermissionGrant
    initial_inputs: tuple[InitialInput, ...] = ()
    dependencies: tuple[Dependency, ...] = ()
    outputs: tuple[OutputSpec, ...] = ()
    hard_gates: tuple[GateSpec, ...] = ()
    executor: TaskExecutor = TaskExecutor.AGENT
    command: str = ""
    framework: str = ""
    model: str = ""
    reasoning_effort: str = ""
    required: bool = True
    on_demand: bool = False
    display_group: str = ""
    max_attempts: int = 8
    timeout_seconds: int = 5400
    brief: TaskBrief | None = None
    frozen: bool = False

    def __post_init__(self) -> None:
        if self.executor == TaskExecutor.TOOL and not self.command.strip():
            raise DomainError("tool Task requires a deterministic command")
        if self.executor != TaskExecutor.TOOL and self.command.strip():
            raise DomainError("only a tool Task may declare a command")
        if self.executor == TaskExecutor.HUMAN:
            if (
                len(self.outputs) != 1
                or self.outputs[0].artifact_type != "human.decision"
                or self.outputs[0].schema_version != 1
                or self.outputs[0].paths
            ):
                raise DomainError(
                    "human Task requires exactly one inline human.decision@1 output"
                )
            if self.permission.write_paths or self.permission.tools or self.hard_gates:
                raise DomainError(
                    "human Task cannot declare write paths, tools, or hard gates"
                )
        if not all((self.id, self.workflow_id, self.key, self.role, self.intent.strip())):
            raise DomainError("Task requires stable identity, Role and intent")
        if self.role_version < 1 or self.max_attempts < 1 or self.timeout_seconds < 1:
            raise DomainError("Task Role version and attempt budget must be positive")
        if self.reasoning_effort and self.reasoning_effort not in {
            "low", "medium", "high", "xhigh", "max", "ultra",
        }:
            raise DomainError(
                f"Task {self.id} has unsupported reasoning effort: {self.reasoning_effort}"
            )
        if len({output.name for output in self.outputs}) != len(self.outputs):
            raise DomainError(f"Task {self.id} has duplicate output names")
        input_names = [item.name for item in self.initial_inputs] + [
            item.input_name for item in self.dependencies
        ]
        if len(set(input_names)) != len(input_names):
            raise DomainError(f"Task {self.id} has duplicate input names")
        if self.frozen and self.brief is None:
            raise DomainError(f"frozen Task {self.id} requires a TaskBrief")


@dataclass(frozen=True)
class Workflow:
    id: str
    recipe: str
    goal: str
    status: WorkflowStatus = WorkflowStatus.PLANNING
    paused_reason: str = ""
    definition_digest: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class WorkItem:
    id: str
    task_id: str
    kind: WorkItemKind
    request_key: str
    correlation_key: str
    summary: str
    # Correlations that causally led to this work request.  The request keeps
    # its own identity in ``correlation_key``; these parent keys only make
    # already-resolved answers and clarifications available to later
    # Attempts.  They are not scheduling generations or Artifact lineage.
    causal_correlation_keys: tuple[str, ...] = ()
    source_task_id: str = ""
    evidence_artifact_ids: tuple[str, ...] = ()
    evidence_attempt_ids: tuple[str, ...] = ()
    wait_for_work_item_ids: tuple[str, ...] = ()
    status: WorkItemStatus = WorkItemStatus.PENDING
    created_sequence: int = 0
    claimed_attempt_id: str = ""
    resolved_attempt_id: str = ""
    created_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class Attempt:
    id: str
    task_id: str
    ordinal: int
    status: AttemptStatus
    work_item_ids: tuple[str, ...]
    input_deliveries: Mapping[str, str]
    role: str
    role_version: int
    role_instruction: str
    role_skills: tuple[str, ...]
    role_accepted_types: tuple[str, ...]
    brief: TaskBrief
    brief_digest: str
    permission: PermissionGrant
    framework: str
    model: str = ""
    reasoning_effort: str = ""
    executor: TaskExecutor = TaskExecutor.AGENT
    command: str = ""
    timeout_seconds: int = 5400
    session_id: str = ""
    workspace_commit: str = ""
    verdict: str = ""
    diagnostics: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    finished_at: str = ""


@dataclass(frozen=True)
class RecoverableSite:
    """Latest engineering site that may be resumed for the same Task.

    Selection is deliberately Task-local and does not compare Artifact ids or
    input fingerprints.  Content conflicts are reported by the workspace
    restorer, not guessed here.
    """

    task_id: str
    attempt_id: str
    session_id: str = ""
    workspace_commit: str = ""
    modified_paths: tuple[str, ...] = ()
    failure_reason: str = ""
    base_commit: str = ""


@dataclass(frozen=True)
class ArtifactProducer:
    workflow_id: str
    task_id: str
    attempt_id: str
    role: str
    role_version: int


@dataclass(frozen=True)
class ArtifactContent:
    kind: str
    commit: str = ""
    tree: str = ""
    paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class Artifact:
    """Immutable result/evidence record with no scheduling semantics."""

    id: str
    type: str
    schema_version: int
    producer: ArtifactProducer
    content: ArtifactContent
    payload: Mapping[str, Any]
    input_artifact_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    digest: str = ""

    def __post_init__(self) -> None:
        if not self.id or not self.type or self.schema_version < 1:
            raise DomainError("Artifact requires id, type and schema version")
        calculated = self.calculate_digest()
        if self.digest and self.digest != calculated:
            raise DomainError("Artifact digest does not match its immutable record")
        object.__setattr__(self, "digest", calculated)

    @property
    def input_manifest_path(self) -> str:
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in self.id)
        return f".nebula_inputs/{safe}/artifact.json"

    def document(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "schema_version": self.schema_version,
            "producer": self.producer.__dict__,
            "content": {**self.content.__dict__, "paths": list(self.content.paths)},
            "payload": dict(self.payload),
            "input_artifact_ids": list(self.input_artifact_ids),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }

    def digest_document(self) -> dict[str, Any]:
        return self.document()

    def calculate_digest(self) -> str:
        encoded = json.dumps(
            self.document(), ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return "sha256:" + hashlib.sha256(encoded).hexdigest()

    def validate(self, registry) -> None:
        """Validate content using the schema catalog without scheduling meaning."""
        registry.validate(self.type, self.schema_version, self.payload)
        if "result_summary" in self.payload:
            from .result_summary import ResultSummaryError, validate_result_summary

            try:
                summary = validate_result_summary(
                    self.payload["result_summary"],
                    archived_paths=self.content.paths,
                )
                if (
                    any(item["status"] == "measured" for item in summary["metrics"])
                    and not self.content.commit
                ):
                    raise ResultSummaryError(
                        "measured result summary requires immutable Git evidence"
                    )
            except ResultSummaryError as exc:
                from .artifacts import ArtifactValidationError

                raise ArtifactValidationError(str(exc)) from exc
        if self.content.kind == "git":
            payload_commit = self.payload.get("commit")
            if payload_commit and payload_commit != self.content.commit:
                from .artifacts import ArtifactValidationError

                raise ArtifactValidationError(
                    "payload.commit does not match content.commit"
                )


@dataclass(frozen=True)
class Delivery:
    task_id: str
    output_name: str
    artifact_id: str
    attempt_id: str
    accepted_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class WorkRequest:
    """One idempotent event action targeting an existing Task."""

    target_task_id: str
    kind: WorkItemKind
    request_key: str
    summary: str
    correlation_key: str = ""
    causal_correlation_keys: tuple[str, ...] = ()
    source_task_id: str = ""
    evidence_artifact_ids: tuple[str, ...] = ()
    evidence_attempt_ids: tuple[str, ...] = ()
    # Upstream changes conservatively require the affected delivery branch to
    # revalidate.  Callers must opt out explicitly when a request is purely
    # diagnostic and cannot change the Task's delivery.
    propagate_to_dependents: bool = True


@dataclass(frozen=True)
class JointAnalysisGroup:
    """Predeclared barrier that wakes one existing on-demand analysis Task."""

    id: str
    workflow_id: str
    member_task_ids: tuple[str, ...]
    analyzer_task_id: str

    def __post_init__(self) -> None:
        if (
            not self.id or not self.workflow_id or len(self.member_task_ids) < 2
            or len(set(self.member_task_ids)) != len(self.member_task_ids)
            or not self.analyzer_task_id
            or self.analyzer_task_id in self.member_task_ids
        ):
            raise DomainError("JointAnalysisGroup requires distinct members and analyzer")

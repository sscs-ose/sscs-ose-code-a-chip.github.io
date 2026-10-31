"""SQLite state for static Task workflows and continuing Attempts."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import asdict, replace
from pathlib import Path
from typing import Iterator, Mapping, Sequence

from .domain import (
    Artifact,
    ArtifactContent,
    ArtifactProducer,
    Attempt,
    AttemptStatus,
    Delivery,
    Dependency,
    DomainError,
    GateSpec,
    InitialInput,
    JointAnalysisGroup,
    OutputSpec,
    PermissionGrant,
    ReleaseCondition,
    RecoverableSite,
    Role,
    Task,
    TaskBrief,
    TaskExecutor,
    TaskState,
    WorkItem,
    WorkItemKind,
    WorkItemStatus,
    Workflow,
    WorkflowStatus,
    WorkRequest,
    path_scope_covers,
    utc_now,
)
from .static_recipe import FeedbackRoute


class StateConflict(RuntimeError):
    """A concurrent or invalid state transition was rejected."""


class StaticTaskGraphStore:
    """Authoritative persistence; no method can add Tasks after freeze."""

    SCHEMA_VERSION = 1

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, timeout=30)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._migrate()

    def __enter__(self) -> "StaticTaskGraphStore":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            yield self._connection
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

    def _migrate(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS taskgraph_schema(version INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS workflows(
                id TEXT PRIMARY KEY, status TEXT NOT NULL, document TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS roles(
                name TEXT NOT NULL, version INTEGER NOT NULL, document TEXT NOT NULL,
                PRIMARY KEY(name, version)
            );
            CREATE TABLE IF NOT EXISTS tasks(
                id TEXT PRIMARY KEY, workflow_id TEXT NOT NULL REFERENCES workflows(id),
                task_key TEXT NOT NULL, document TEXT NOT NULL,
                paused_reason TEXT NOT NULL DEFAULT '',
                UNIQUE(workflow_id, task_key)
            );
            CREATE TABLE IF NOT EXISTS attempt_budget_extensions(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL, additional_attempts INTEGER NOT NULL,
                reason TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS work_items(
                id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id),
                request_key TEXT NOT NULL, status TEXT NOT NULL,
                created_sequence INTEGER NOT NULL, document TEXT NOT NULL,
                UNIQUE(task_id, request_key)
            );
            CREATE TABLE IF NOT EXISTS attempts(
                id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id),
                ordinal INTEGER NOT NULL, status TEXT NOT NULL, document TEXT NOT NULL,
                UNIQUE(task_id, ordinal)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_attempt_per_task
                ON attempts(task_id) WHERE status = 'running';
            CREATE TABLE IF NOT EXISTS artifacts(
                id TEXT PRIMARY KEY, type TEXT NOT NULL, attempt_id TEXT NOT NULL,
                digest TEXT NOT NULL, document TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS attempt_outputs(
                attempt_id TEXT NOT NULL REFERENCES attempts(id), output_name TEXT NOT NULL,
                artifact_id TEXT NOT NULL UNIQUE REFERENCES artifacts(id),
                PRIMARY KEY(attempt_id, output_name)
            );
            CREATE TABLE IF NOT EXISTS deliveries(
                task_id TEXT NOT NULL REFERENCES tasks(id), output_name TEXT NOT NULL,
                artifact_id TEXT NOT NULL REFERENCES artifacts(id),
                attempt_id TEXT NOT NULL REFERENCES attempts(id), accepted_at TEXT NOT NULL,
                PRIMARY KEY(task_id, output_name)
            );
            CREATE TABLE IF NOT EXISTS delivery_history(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL, output_name TEXT NOT NULL,
                artifact_id TEXT NOT NULL, attempt_id TEXT NOT NULL, accepted_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS work_events(
                event_id TEXT PRIMARY KEY, workflow_id TEXT NOT NULL,
                document TEXT NOT NULL, processed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS joint_analysis_groups(
                id TEXT PRIMARY KEY, workflow_id TEXT NOT NULL,
                document TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS feedback_routes(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL, document TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS joint_analysis_arrivals(
                group_id TEXT NOT NULL, correlation_key TEXT NOT NULL,
                member_task_id TEXT NOT NULL, attempt_id TEXT NOT NULL,
                outcome TEXT NOT NULL, summary TEXT NOT NULL,
                PRIMARY KEY(group_id, correlation_key, member_task_id)
            );
            CREATE TABLE IF NOT EXISTS joint_analysis_dispatches(
                group_id TEXT NOT NULL, correlation_key TEXT NOT NULL,
                work_item_id TEXT NOT NULL,
                PRIMARY KEY(group_id, correlation_key)
            );
            CREATE TABLE IF NOT EXISTS events(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL, subject_id TEXT NOT NULL,
                document TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        row = self._connection.execute("SELECT version FROM taskgraph_schema").fetchone()
        if row is None:
            self._connection.execute(
                "INSERT INTO taskgraph_schema(version) VALUES (?)", (self.SCHEMA_VERSION,),
            )
        elif row["version"] != self.SCHEMA_VERSION:
            raise StateConflict(
                f"unsupported static TaskGraph schema {row['version']}"
            )
        self._connection.commit()

    def get_role(self, name: str, version: int) -> Role:
        return self._role(self._connection, name, version)

    def create_workflow(
        self, workflow: Workflow, roles: Sequence[Role], tasks: Sequence[Task],
        initial_artifacts: Sequence[Artifact] = (),
        joint_analysis_groups: Sequence[JointAnalysisGroup] = (),
        feedback_routes: Sequence[FeedbackRoute] = (),
    ) -> None:
        if workflow.status != WorkflowStatus.PLANNING:
            raise DomainError("new Workflow must begin in planning")
        if not tasks or any(task.workflow_id != workflow.id for task in tasks):
            raise DomainError("Workflow requires a non-empty, owned Task set")
        task_ids = {task.id for task in tasks}
        if len(task_ids) != len(tasks):
            raise DomainError("Workflow Task ids must be unique")
        role_keys = {(role.name, role.version) for role in roles}
        for task in tasks:
            if task.frozen or task.brief is not None:
                raise DomainError("Task briefs are created by the planning step")
            if (task.role, task.role_version) not in role_keys:
                raise DomainError(f"Task {task.id} references an unavailable Role")
            for dependency in task.dependencies:
                if dependency.upstream_task_id not in task_ids:
                    raise DomainError(
                        f"Task {task.id} depends on unknown Task {dependency.upstream_task_id}"
                    )
        self._assert_acyclic(tasks)
        tasks_by_id = {task.id: task for task in tasks}
        for group in joint_analysis_groups:
            if group.workflow_id != workflow.id:
                raise DomainError(f"joint analysis group {group.id} belongs to another Workflow")
            if any(member not in tasks_by_id for member in group.member_task_ids):
                raise DomainError(f"joint analysis group {group.id} has an unknown member")
            analyzer = tasks_by_id.get(group.analyzer_task_id)
            if analyzer is None or not analyzer.on_demand:
                raise DomainError(f"joint analysis group {group.id} analyzer must be on-demand")
        artifact_types = {artifact.id: artifact.type for artifact in initial_artifacts}
        artifacts_by_id = {artifact.id: artifact for artifact in initial_artifacts}
        for task in tasks:
            for item in task.initial_inputs:
                if item.optional and not item.artifact_id:
                    continue
                if artifact_types.get(item.artifact_id) != item.required_type:
                    raise DomainError(
                        f"Task {task.id} initial input {item.name} is missing or has wrong type"
                    )
                artifact = artifacts_by_id[item.artifact_id]
                unreadable = [
                    path for path in artifact.content.paths
                    if not any(
                        path_scope_covers(grant, path)
                        for grant in task.permission.read_paths
                    )
                ]
                if unreadable:
                    raise DomainError(
                        f"Task {task.id} initial input {item.name} contains paths outside "
                        f"its read grant: {unreadable}"
                    )
        with self.transaction() as tx:
            tx.execute(
                "INSERT INTO workflows(id, status, document) VALUES (?, ?, ?)",
                (workflow.id, workflow.status.value, _json(_workflow_doc(workflow))),
            )
            for role in roles:
                role_document = _json(_role_doc(role))
                existing_role = tx.execute(
                    "SELECT document FROM roles WHERE name = ? AND version = ?",
                    (role.name, role.version),
                ).fetchone()
                if existing_role is not None:
                    if existing_role["document"] != role_document:
                        raise StateConflict(
                            f"Role {role.name}@{role.version} already exists with "
                            "different immutable capability content; bump its version"
                        )
                else:
                    tx.execute(
                        "INSERT INTO roles(name, version, document) VALUES (?, ?, ?)",
                        (role.name, role.version, role_document),
                    )
            for artifact in initial_artifacts:
                existing = tx.execute(
                    "SELECT type, digest FROM artifacts WHERE id = ?",
                    (artifact.id,),
                ).fetchone()
                if existing is not None:
                    if (
                        existing["type"] != artifact.type
                        or existing["digest"] != artifact.digest
                    ):
                        raise StateConflict(
                            f"initial Artifact {artifact.id} already exists with "
                            "different immutable content"
                        )
                    continue
                tx.execute(
                    "INSERT INTO artifacts(id, type, attempt_id, digest, document) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (artifact.id, artifact.type, artifact.producer.attempt_id,
                     artifact.digest, _json(artifact.document())),
                )
            for task in tasks:
                tx.execute(
                    "INSERT INTO tasks(id, workflow_id, task_key, document) VALUES (?, ?, ?, ?)",
                    (task.id, task.workflow_id, task.key, _json(_task_doc(task))),
                )
            for group in joint_analysis_groups:
                tx.execute(
                    "INSERT INTO joint_analysis_groups(id, workflow_id, document) VALUES (?, ?, ?)",
                    (group.id, group.workflow_id, _json(asdict(group))),
                )
            for route in feedback_routes:
                if route.source_task_id not in task_ids or route.target_task_id not in task_ids:
                    raise DomainError("feedback route must target predefined Workflow Tasks")
                tx.execute(
                    "INSERT INTO feedback_routes(workflow_id, document) VALUES (?, ?)",
                    (workflow.id, _json(asdict(route))),
                )
            self._event(tx, "WorkflowCreated", workflow.id, {
                "task_ids": sorted(task_ids), "recipe": workflow.recipe,
            })

    def freeze_briefs(
        self, workflow_id: str, briefs: Mapping[str, TaskBrief],
    ) -> list[Task]:
        """Freeze exactly one concrete brief for every predefined Task."""
        with self.transaction() as tx:
            workflow = self._workflow(tx, workflow_id)
            if workflow.status != WorkflowStatus.PLANNING:
                existing = self.list_tasks(workflow_id)
                if {task.id: task.brief for task in existing} == dict(briefs):
                    return existing
                raise StateConflict("Workflow Task briefs are already frozen")
            tasks = self._tasks(tx, workflow_id)
            routes = tuple(
                FeedbackRoute(**json.loads(row["document"]))
                for row in tx.execute(
                    "SELECT document FROM feedback_routes WHERE workflow_id = ? "
                    "ORDER BY sequence",
                    (workflow_id,),
                ).fetchall()
            )
            if set(briefs) != {task.id for task in tasks}:
                missing = sorted({task.id for task in tasks} - set(briefs))
                extra = sorted(set(briefs) - {task.id for task in tasks})
                raise DomainError(f"planner brief coverage mismatch; missing={missing}, extra={extra}")
            result: list[Task] = []
            for task in tasks:
                brief = briefs[task.id]
                self._validate_collaboration(task, brief, tasks, routes)
                frozen = replace(task, brief=brief, frozen=True)
                tx.execute(
                    "UPDATE tasks SET document = ? WHERE id = ?",
                    (_json(_task_doc(frozen)), task.id),
                )
                result.append(frozen)
                if task.required and not task.on_demand:
                    self._append_work_item(
                        tx, task.id, (
                            WorkItemKind.HUMAN_QUESTION
                            if task.executor == TaskExecutor.HUMAN
                            else WorkItemKind.INITIAL
                        ),
                        request_key=f"initial:{task.id}",
                        correlation_key="initial",
                        summary=brief.objective,
                    )
            ready = replace(workflow, status=WorkflowStatus.READY)
            self._write_workflow(tx, ready)
            self._event(tx, "TaskBriefsFrozen", workflow_id, {
                "brief_digests": {task.id: task.brief.digest for task in result},
            })
            return result

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        row = self._connection.execute(
            "SELECT document FROM workflows WHERE id = ?", (workflow_id,),
        ).fetchone()
        return _workflow_from(json.loads(row["document"])) if row else None

    def list_workflows(self) -> list[Workflow]:
        return [
            _workflow_from(json.loads(row["document"]))
            for row in self._connection.execute(
                "SELECT document FROM workflows ORDER BY rowid"
            ).fetchall()
        ]

    def feedback_routes(self, workflow_id: str) -> tuple[FeedbackRoute, ...]:
        return tuple(
            FeedbackRoute(**json.loads(row["document"]))
            for row in self._connection.execute(
                "SELECT document FROM feedback_routes WHERE workflow_id = ? ORDER BY sequence",
                (workflow_id,),
            ).fetchall()
        )

    def get_task(self, task_id: str) -> Task | None:
        row = self._connection.execute(
            "SELECT document FROM tasks WHERE id = ?", (task_id,),
        ).fetchone()
        return _task_from(json.loads(row["document"])) if row else None

    def list_tasks(self, workflow_id: str) -> list[Task]:
        rows = self._connection.execute(
            "SELECT document FROM tasks WHERE workflow_id = ? ORDER BY rowid", (workflow_id,),
        ).fetchall()
        return [_task_from(json.loads(row["document"])) for row in rows]

    def task_ids(self, workflow_id: str) -> tuple[str, ...]:
        return tuple(task.id for task in self.list_tasks(workflow_id))

    def add_work(
        self, task_id: str, *, kind: WorkItemKind, request_key: str, summary: str,
        source_task_id: str = "", evidence_artifact_ids: Sequence[str] = (),
        propagate_to_dependents: bool = True,
    ) -> WorkItem:
        with self.transaction() as tx:
            task = self._task(tx, task_id)
            self._validate_work_requests(tx, task.workflow_id, (WorkRequest(
                target_task_id=task_id, kind=kind, request_key=request_key,
                summary=summary, source_task_id=source_task_id,
                evidence_artifact_ids=tuple(evidence_artifact_ids),
                propagate_to_dependents=propagate_to_dependents,
            ),))
            item = self._append_work_item(
                tx, task_id, kind, request_key, summary,
                correlation_key=request_key,
                source_task_id=source_task_id,
                evidence_artifact_ids=evidence_artifact_ids,
            )
            if propagate_to_dependents:
                self._propagate_reverification(tx, task_id, request_key, summary)
            self._mark_workflow_active(tx, task.workflow_id)
            return item

    def apply_work_event(
        self, event_id: str, workflow_id: str, requests: Sequence[WorkRequest],
    ) -> list[WorkItem]:
        """Atomically deliver idempotent feedback to existing Tasks only."""
        if not event_id or not requests:
            raise DomainError("work event requires an id and at least one request")
        with self.transaction() as tx:
            existing = tx.execute(
                "SELECT 1 FROM work_events WHERE event_id = ?", (event_id,),
            ).fetchone()
            if existing:
                return []
            workflow = self._workflow(tx, workflow_id)
            if workflow.status == WorkflowStatus.PLANNING:
                raise StateConflict("cannot deliver runtime work before planning is frozen")
            self._validate_work_requests(tx, workflow_id, requests)
            created: list[WorkItem] = []
            for request in requests:
                item = self._append_work_item(
                    tx, request.target_task_id, request.kind,
                    request.request_key, request.summary,
                    correlation_key=request.correlation_key or request.request_key,
                    causal_correlation_keys=request.causal_correlation_keys,
                    source_task_id=request.source_task_id,
                    evidence_artifact_ids=request.evidence_artifact_ids,
                    evidence_attempt_ids=request.evidence_attempt_ids,
                )
                created.append(item)
                if request.propagate_to_dependents:
                    created.extend(self._propagate_reverification(
                        tx, request.target_task_id, request.request_key, request.summary,
                        correlation_key=request.correlation_key or request.request_key,
                        causal_correlation_keys=request.causal_correlation_keys,
                    ))
            tx.execute(
                "INSERT INTO work_events(event_id, workflow_id, document, processed_at) "
                "VALUES (?, ?, ?, ?)",
                (event_id, workflow_id, _json({"requests": [asdict(r) for r in requests]}), utc_now()),
            )
            self._mark_workflow_active(tx, workflow_id)
            self._event(tx, "WorkEventApplied", event_id, {
                "workflow_id": workflow_id,
                "work_item_ids": [item.id for item in created],
            })
            return created

    def pending_work(self, task_id: str) -> list[WorkItem]:
        rows = self._connection.execute(
            "SELECT document FROM work_items WHERE task_id = ? AND status = ? "
            "ORDER BY created_sequence",
            (task_id, WorkItemStatus.PENDING.value),
        ).fetchall()
        return [_work_item_from(json.loads(row["document"])) for row in rows]

    def task_work_items(self, task_id: str) -> list[WorkItem]:
        """Return the immutable work ledger for one fixed Task."""
        if self.get_task(task_id) is None:
            raise KeyError(task_id)
        rows = self._connection.execute(
            "SELECT document FROM work_items WHERE task_id = ? "
            "ORDER BY created_sequence",
            (task_id,),
        ).fetchall()
        return [_work_item_from(json.loads(row["document"])) for row in rows]

    def human_question_state(self, task_id: str) -> dict:
        """Expose pending attached questions without inventing a Human Task.

        Attached questions are intentionally plain WorkItems.  This projection
        gives the dashboard the same small interaction shape used by an
        explicit human executor while keeping the fixed Task topology intact.
        """
        task = self.get_task(task_id)
        if task is None:
            raise KeyError(task_id)
        questions = [
            item for item in self.pending_work(task_id)
            if item.kind == WorkItemKind.HUMAN_QUESTION
        ]
        if not questions:
            raise StateConflict(f"Task {task_id} has no pending human questions")
        def card(item: WorkItem) -> dict:
            try:
                detail = json.loads(item.summary)
            except (TypeError, json.JSONDecodeError):
                detail = {}
            if not isinstance(detail, dict):
                detail = {}
            return {
                "id": item.id,
                "issue_id": str(detail.get("issue_id", item.id)),
                "title": str(detail.get("title", "需要人工澄清")),
                "context": str(detail.get("context", item.summary)),
                "required": bool(detail.get("required", True)),
                "options": (
                    detail.get("options", [])
                    if isinstance(detail.get("options", []), list) else []
                ),
                "candidate_ids": (
                    detail.get("candidate_ids", [])
                    if isinstance(detail.get("candidate_ids", []), list) else []
                ),
                "compiler_backed": bool(detail.get("compiler_backed", False)),
                "presentation": str(detail.get("presentation", "clarification")),
            }

        return {
            "task_id": task.id,
            "status": "awaiting_human",
            "request_artifact_id": "",
            "items": [card(item) for item in questions],
            "answers": {},
            "remaining": [item.id for item in questions],
        }

    def answer_human_questions(
        self, event_id: str, answers: Mapping[str, str], *,
        evidence_artifact_ids: Mapping[str, Sequence[str]] | None = None,
    ) -> list[WorkItem]:
        """Resolve attached human questions and append answers as Task work.

        Questions and answers never become hidden Tasks.  One event may answer
        multiple Tasks atomically and replaying it is a no-op.
        """
        if not event_id or not answers:
            raise DomainError("human answer event requires answers")
        if any(not isinstance(answer, str) or not answer.strip() for answer in answers.values()):
            raise DomainError("every human answer must be non-empty")
        answer_evidence = evidence_artifact_ids or {}
        if set(answer_evidence) - set(answers):
            raise DomainError("human answer evidence names an unanswered question")
        with self.transaction() as tx:
            if tx.execute(
                "SELECT 1 FROM work_events WHERE event_id = ?", (event_id,),
            ).fetchone():
                return []
            questions = [self._work_item(tx, question_id) for question_id in answers]
            workflow_ids = {self._task(tx, item.task_id).workflow_id for item in questions}
            if len(workflow_ids) != 1:
                raise DomainError("one human answer event must belong to one Workflow")
            missing_evidence = sorted({
                artifact_id
                for question_id in answers
                for artifact_id in answer_evidence.get(question_id, ())
                if tx.execute(
                    "SELECT 1 FROM artifacts WHERE id = ?", (artifact_id,),
                ).fetchone() is None
            })
            if missing_evidence:
                raise DomainError(
                    f"human answer references unavailable evidence: {missing_evidence}"
                )
            created: list[WorkItem] = []
            human_answers: dict[str, list[tuple[WorkItem, WorkItem, str]]] = {}
            for question in questions:
                if question.kind != WorkItemKind.HUMAN_QUESTION:
                    raise DomainError(f"Work item {question.id} is not a human question")
                if question.status != WorkItemStatus.PENDING:
                    raise StateConflict(f"human question {question.id} is already resolved")
                self._write_work_item(tx, replace(
                    question, status=WorkItemStatus.RESOLVED,
                    resolved_attempt_id=f"human:{event_id}",
                ))
                answer = self._append_work_item(
                    tx, question.task_id, WorkItemKind.HUMAN_ANSWER,
                    request_key=f"answer:{question.request_key}",
                    correlation_key=question.correlation_key,
                    causal_correlation_keys=question.causal_correlation_keys,
                    summary=answers[question.id].strip(),
                    source_task_id=question.task_id,
                    # The answer resolves the question; it does not replace
                    # the evidence that caused the question to be asked.
                    # Keep those immutable references on the follow-up work
                    # so the next Attempt receives the decision and its
                    # factual basis together.
                    evidence_artifact_ids=tuple(dict.fromkeys((
                        *question.evidence_artifact_ids,
                        *answer_evidence.get(question.id, ()),
                    ))),
                    evidence_attempt_ids=question.evidence_attempt_ids,
                )
                task = self._task(tx, question.task_id)
                if task.executor == TaskExecutor.HUMAN:
                    human_answers.setdefault(task.id, []).append(
                        (question, answer, answers[question.id].strip())
                    )
                else:
                    created.append(answer)
            for task_id, rows in human_answers.items():
                task = self._task(tx, task_id)
                unanswered = [
                    item.id for item in self._pending_work(tx, task_id)
                    if item.kind == WorkItemKind.HUMAN_QUESTION
                ]
                if unanswered:
                    raise StateConflict(
                        f"human Task {task_id} requires one complete answer batch; "
                        f"unanswered={unanswered}"
                    )
                created.extend(self._complete_human_task_tx(
                    tx, task, rows, event_id,
                ))
            workflow_id = next(iter(workflow_ids))
            tx.execute(
                "INSERT INTO work_events(event_id, workflow_id, document, processed_at) "
                "VALUES (?, ?, ?, ?)",
                (event_id, workflow_id, _json({"question_ids": list(answers)}), utc_now()),
            )
            workflow = self._workflow(tx, workflow_id)
            remaining_questions = any(
                item.kind == WorkItemKind.HUMAN_QUESTION
                for task in self._tasks(tx, workflow_id)
                for item in self._pending_work(tx, task.id)
            )
            if not remaining_questions:
                if (
                    workflow.status == WorkflowStatus.PAUSED
                    and workflow.paused_reason.startswith("awaiting human input")
                ):
                    self._write_workflow(tx, replace(
                        workflow, status=WorkflowStatus.ACTIVE, paused_reason="",
                    ))
                else:
                    self._mark_workflow_active(tx, workflow_id)
            self._refresh_workflow_completion(tx, workflow_id)
            self._event(tx, "HumanAnswersApplied", event_id, {
                "workflow_id": workflow_id,
                "question_ids": list(answers),
                "answer_work_item_ids": [item.id for item in created],
            })
            return created

    def register_evidence_artifacts(self, artifacts: Sequence[Artifact]) -> None:
        """Import immutable external evidence without changing Task topology.

        This is the explicit bridge used when an attached human clarification
        is resolved by another workflow, such as PREPARE publishing a newly
        signed specification.  Imported records are context only: registering
        them never creates work, selects a Delivery, or changes scheduling.
        """
        with self.transaction() as tx:
            imported: list[str] = []
            for artifact in artifacts:
                existing = tx.execute(
                    "SELECT type, digest FROM artifacts WHERE id = ?",
                    (artifact.id,),
                ).fetchone()
                if existing is not None:
                    if (
                        existing["type"] != artifact.type
                        or existing["digest"] != artifact.digest
                    ):
                        raise StateConflict(
                            f"evidence Artifact {artifact.id} already exists with "
                            "different immutable content"
                        )
                    continue
                tx.execute(
                    "INSERT INTO artifacts(id, type, attempt_id, digest, document) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        artifact.id, artifact.type,
                        artifact.producer.attempt_id, artifact.digest,
                        _json(artifact.document()),
                    ),
                )
                imported.append(artifact.id)
            if imported:
                self._event(tx, "EvidenceArtifactsRegistered", imported[0], {
                    "artifact_ids": imported,
                })

    def record_resolved_context(
        self, event_id: str, task_id: str, *, correlation_key: str,
        summary: str, evidence_artifact_ids: Sequence[str],
    ) -> WorkItem | None:
        """Append late immutable evidence to an already-resolved correlation.

        The record is resolved immediately and therefore cannot wake or claim
        a Task by itself.  Future Attempts that already have correlated work
        capture it through ``_resolved_correlation_context``.
        """
        if not event_id or not correlation_key or not summary.strip():
            raise DomainError("resolved context requires event, correlation and summary")
        with self.transaction() as tx:
            if tx.execute(
                "SELECT 1 FROM work_events WHERE event_id = ?", (event_id,),
            ).fetchone():
                return None
            task = self._task(tx, task_id)
            missing = sorted({
                artifact_id for artifact_id in evidence_artifact_ids
                if tx.execute(
                    "SELECT 1 FROM artifacts WHERE id = ?", (artifact_id,),
                ).fetchone() is None
            })
            if missing:
                raise DomainError(f"resolved context references unavailable evidence: {missing}")
            item = self._append_work_item(
                tx, task_id, WorkItemKind.CLARIFICATION,
                request_key=f"resolved-context:{event_id}",
                correlation_key=correlation_key,
                summary=summary,
                source_task_id=task_id,
                evidence_artifact_ids=evidence_artifact_ids,
            )
            resolved = replace(
                item, status=WorkItemStatus.RESOLVED,
                resolved_attempt_id=f"context:{event_id}",
            )
            self._write_work_item(tx, resolved)
            tx.execute(
                "INSERT INTO work_events(event_id, workflow_id, document, processed_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    event_id, task.workflow_id,
                    _json({"resolved_context_work_item_id": resolved.id}), utc_now(),
                ),
            )
            self._event(tx, "ResolvedContextRecorded", resolved.id, {
                "workflow_id": task.workflow_id,
                "correlation_key": correlation_key,
                "evidence_artifact_ids": list(evidence_artifact_ids),
            })
            return resolved

    def work_items(self, ids: Sequence[str]) -> list[WorkItem]:
        return [
            _work_item_from(json.loads(row["document"]))
            for item_id in ids
            for row in [self._connection.execute(
                "SELECT document FROM work_items WHERE id = ?", (item_id,),
            ).fetchone()]
            if row is not None
        ]

    def task_state(self, task_id: str) -> TaskState:
        task = self.get_task(task_id)
        if task is None:
            raise KeyError(task_id)
        if not task.frozen:
            return TaskState.WAITING
        paused = self._connection.execute(
            "SELECT paused_reason FROM tasks WHERE id = ?", (task_id,),
        ).fetchone()["paused_reason"]
        if paused:
            return TaskState.PAUSED
        if self.active_attempt(task_id):
            return TaskState.RUNNING
        pending = self.pending_work(task_id)
        if not pending:
            return TaskState.IDLE if task.on_demand and not self.deliveries(task_id) else TaskState.SATISFIED
        if task.executor == TaskExecutor.HUMAN:
            return TaskState.WAITING
        # A Task may accumulate ordinary feedback and one or more attached
        # questions together.  It must not consume the feedback using only a
        # partial answer batch.
        if any(item.kind == WorkItemKind.HUMAN_QUESTION for item in pending):
            return TaskState.WAITING
        if not self._claimable_work(self._connection, task_id):
            return TaskState.WAITING
        return TaskState.READY if self._dependencies_satisfied(task) else TaskState.WAITING

    def claim_attempt(
        self, task_id: str, *, framework: str = "", model: str = "",
        reasoning_effort: str = "",
    ) -> Attempt:
        """Atomically snapshot pending work and current upstream Deliveries."""
        budget_error = ""
        created: Attempt | None = None
        with self.transaction() as tx:
            task = self._task(tx, task_id)
            if task.executor == TaskExecutor.HUMAN:
                raise StateConflict(
                    f"human Task {task_id} is completed only by an explicit answer event"
                )
            workflow = self._workflow(tx, task.workflow_id)
            if workflow.status in {WorkflowStatus.PLANNING, WorkflowStatus.PAUSED, WorkflowStatus.COMPLETE}:
                raise StateConflict(f"Workflow {workflow.id} is {workflow.status.value}")
            paused = tx.execute(
                "SELECT paused_reason FROM tasks WHERE id = ?", (task_id,),
            ).fetchone()["paused_reason"]
            if paused:
                raise StateConflict(f"Task {task_id} is paused: {paused}")
            if self._active_attempt(tx, task_id):
                raise StateConflict(f"Task {task_id} already has an active Attempt")
            work = self._claimable_work(tx, task_id)
            if not work:
                if self._pending_work(tx, task_id):
                    raise StateConflict(f"Task {task_id} work is waiting for prerequisite work")
                raise StateConflict(f"Task {task_id} has no pending work")
            if task.on_demand and any(output.artifact_type == "failure.report" for output in task.outputs):
                failures = [item for item in work if item.evidence_attempt_ids
                            and item.kind != WorkItemKind.HUMAN_ANSWER]
                if failures:
                    # One diagnosis names one owner; concurrent failures keep separate cursors.
                    selected = failures[:1]
                    related = self._resolved_correlation_context(tx, task.workflow_id, selected)
                    correlations = {key for item in (*selected, *related)
                                    for key in (item.correlation_key, *item.causal_correlation_keys)
                                    if key and key != "initial"}
                    work = [*selected, *(item for item in work if item.kind == WorkItemKind.HUMAN_ANSWER
                            and correlations.intersection((item.correlation_key, *item.causal_correlation_keys)))]
            context_work = self._resolved_correlation_context(
                tx, task.workflow_id, work,
            )
            inputs = self._resolved_deliveries(tx, task)
            if inputs is None:
                raise StateConflict(f"Task {task_id} dependencies are not released")
            ordinal = int(tx.execute(
                "SELECT COUNT(*) FROM attempts WHERE task_id = ?", (task_id,),
            ).fetchone()[0]) + 1
            extensions = int(tx.execute(
                "SELECT COALESCE(SUM(additional_attempts), 0) FROM attempt_budget_extensions "
                "WHERE task_id = ?", (task.id,),
            ).fetchone()[0])
            budget = task.max_attempts + extensions
            if ordinal > budget:
                budget_error = f"attempt budget exhausted ({budget})"
                tx.execute(
                    "UPDATE tasks SET paused_reason = ? WHERE id = ?",
                    (budget_error, task.id),
                )
                self._event(tx, "TaskPaused", task.id, {"reason": budget_error})
            else:
                assert task.brief is not None and task.frozen
                role = self._role(tx, task.role, task.role_version)
                created = Attempt(
                    id=f"attempt-{uuid.uuid4().hex}",
                    task_id=task.id,
                    ordinal=ordinal,
                    status=AttemptStatus.RUNNING,
                    # Snapshot both the work being claimed and the resolved
                    # causal records behind it.  In particular, a downstream
                    # revalidation request created for a human question must
                    # carry the later human answer instead of repeating the
                    # already-resolved question as though it were still open.
                    # Resolved context is immutable evidence; only ``work`` is
                    # claimed and can be completed by this Attempt.
                    work_item_ids=tuple(
                        item.id for item in (*work, *context_work)
                    ),
                    input_deliveries=inputs,
                    role=task.role,
                    role_version=task.role_version,
                    role_instruction=role.instruction,
                    role_skills=role.skills,
                    role_accepted_types=role.accepted_types,
                    brief=task.brief,
                    brief_digest=task.brief.digest,
                    permission=task.permission,
                    framework=framework or task.framework,
                    model=model or task.model,
                    reasoning_effort=reasoning_effort or task.reasoning_effort,
                    executor=task.executor,
                    command=task.command,
                    timeout_seconds=task.timeout_seconds,
                )
                tx.execute(
                    "INSERT INTO attempts(id, task_id, ordinal, status, document) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (created.id, task.id, ordinal, created.status.value, _json(_attempt_doc(created))),
                )
                for item in work:
                    claimed = replace(item, claimed_attempt_id=created.id)
                    self._write_work_item(tx, claimed)
                self._mark_workflow_active(tx, task.workflow_id)
                self._event(tx, "AttemptStarted", created.id, {
                    "task_id": task.id,
                    "ordinal": ordinal,
                    "work_item_ids": list(created.work_item_ids),
                    "input_deliveries": dict(inputs),
                })
        if budget_error:
            raise StateConflict(budget_error)
        assert created is not None
        return created

    def _resolved_correlation_context(
        self, tx: sqlite3.Connection, workflow_id: str,
        work: Sequence[WorkItem],
    ) -> list[WorkItem]:
        """Return resolved causal records for the work captured by an Attempt.

        Correlation keys identify one work request across its question,
        answer, repair and revalidation records.  They are not Artifact
        lineage or scheduling identities.  Including resolved records here
        gives a downstream Attempt the decision that released its waiting
        work while leaving Task topology and pending-work accounting intact.
        """
        correlations = set(
            key
            for item in work
            for key in (item.correlation_key, *item.causal_correlation_keys)
            if key and key != "initial"
        )
        if not correlations:
            return []
        rows = tx.execute(
            "SELECT wi.document FROM work_items wi "
            "JOIN tasks t ON t.id = wi.task_id "
            "WHERE t.workflow_id = ? AND wi.status = ? "
            "ORDER BY wi.rowid",
            (workflow_id, WorkItemStatus.RESOLVED.value),
        ).fetchall()
        claimed_ids = {item.id for item in work}
        candidates = [
            _work_item_from(json.loads(row["document"])) for row in rows
        ]
        selected: list[WorkItem] = []
        selected_ids = set(claimed_ids)
        # Walk the small resolved-work set to retain the complete causal
        # context even when a failure is routed through an analysis Task.
        changed = True
        while changed:
            changed = False
            for item in candidates:
                if item.id in selected_ids:
                    continue
                item_keys = {
                    key for key in (
                        item.correlation_key, *item.causal_correlation_keys,
                    ) if key and key != "initial"
                }
                if not (item_keys & correlations):
                    continue
                selected.append(item)
                selected_ids.add(item.id)
                before = len(correlations)
                correlations.update(item_keys)
                changed = changed or len(correlations) != before
                changed = True
        return selected

    def active_attempt(self, task_id: str) -> Attempt | None:
        row = self._connection.execute(
            "SELECT document FROM attempts WHERE task_id = ? AND status = ?",
            (task_id, AttemptStatus.RUNNING.value),
        ).fetchone()
        return _attempt_from(json.loads(row["document"])) if row else None

    def list_attempts(self, task_id: str) -> list[Attempt]:
        rows = self._connection.execute(
            "SELECT document FROM attempts WHERE task_id = ? ORDER BY ordinal", (task_id,),
        ).fetchall()
        return [_attempt_from(json.loads(row["document"])) for row in rows]

    def get_attempt(self, attempt_id: str) -> Attempt | None:
        row = self._connection.execute(
            "SELECT document FROM attempts WHERE id = ?", (attempt_id,),
        ).fetchone()
        return _attempt_from(json.loads(row["document"])) if row else None

    def record_attempt_diagnostics(self, attempt_id: str, values: Mapping) -> Attempt:
        with self.transaction() as tx:
            attempt = self._attempt(tx, attempt_id)
            updated = replace(
                attempt, diagnostics={**attempt.diagnostics, **dict(values)},
            )
            self._write_attempt(tx, updated)
            self._event(tx, "AttemptDiagnosticsUpdated", attempt_id, dict(values))
            return updated

    def recoverable_site(self, task_id: str) -> RecoverableSite | None:
        """Return the newest Task-local site, honoring an explicit WIP reset."""
        self.get_task(task_id) or (_ for _ in ()).throw(KeyError(task_id))
        rows = self._connection.execute(
            "SELECT document FROM attempts WHERE task_id = ? ORDER BY ordinal DESC",
            (task_id,),
        ).fetchall()
        restore_saved_wip = True
        for row in rows:
            attempt = _attempt_from(json.loads(row["document"]))
            # An operator can retain history/session while resolving a reported merge conflict.
            if attempt.diagnostics.get("restore_saved_wip") is False:
                restore_saved_wip = False
            session_reusable = (
                attempt.status == AttemptStatus.SUCCEEDED
                or attempt.diagnostics.get("session_reusable") is True
            )
            session_id = attempt.session_id if session_reusable else ""
            if session_id or attempt.workspace_commit:
                return RecoverableSite(
                    task_id=task_id, attempt_id=attempt.id,
                    session_id=session_id,
                    workspace_commit=attempt.workspace_commit if restore_saved_wip else "",
                    base_commit=(str(attempt.diagnostics.get("workspace_base_commit", ""))
                                 if restore_saved_wip else ""),
                    modified_paths=tuple(
                        str(path)
                        for path in attempt.diagnostics.get("changed_paths", ())
                    ) if restore_saved_wip else (),
                    failure_reason=str(
                        attempt.diagnostics.get("failure_reason", "")
                    ),
                )
        return None

    def finish_attempt_failure(
        self, attempt_id: str, *, reason: str, session_id: str = "",
        workspace_commit: str = "", cancelled: bool = False,
        diagnostics: Mapping | None = None, pause_reason: str = "",
    ) -> Attempt:
        with self.transaction() as tx:
            attempt = self._attempt(tx, attempt_id)
            if attempt.status != AttemptStatus.RUNNING:
                raise StateConflict("only a running Attempt can finish")
            if attempt.diagnostics.get("operator_cancelled"):
                cancelled = True
                reason = str(attempt.diagnostics.get("operator_cancel_reason") or reason)
            status = AttemptStatus.CANCELLED if cancelled else AttemptStatus.FAILED
            finished = replace(
                attempt, status=status, session_id=session_id or attempt.session_id,
                workspace_commit=workspace_commit or attempt.workspace_commit,
                diagnostics={
                    **attempt.diagnostics, **dict(diagnostics or {}),
                    "failure_reason": reason,
                },
                finished_at=utc_now(),
            )
            self._write_attempt(tx, finished)
            for item in self._work_items(tx, attempt.work_item_ids):
                if item.status == WorkItemStatus.PENDING and item.claimed_attempt_id == attempt.id:
                    self._write_work_item(tx, replace(item, claimed_attempt_id=""))
            self._event(tx, "AttemptFinished", attempt.id, {
                "status": status.value, "reason": reason,
            })
            if pause_reason:
                tx.execute(
                    "UPDATE tasks SET paused_reason = ? WHERE id = ?",
                    (pause_reason, attempt.task_id),
                )
                self._event(tx, "TaskPaused", attempt.task_id, {
                    "reason": pause_reason,
                    "attempt_id": attempt.id,
                })
            self._record_joint_arrivals(tx, finished, status.value, reason)
            if not cancelled and not pause_reason:
                from .work_handler import StaticWorkHandler
                task = self._task(tx, attempt.task_id)
                requests = StaticWorkHandler(
                    self, task.workflow_id, self.feedback_routes(task.workflow_id),
                ).requests_for_attempt_failure(finished)
                if requests:
                    diagnostic_work = self._apply_work_event_tx(
                        tx, f"execution-failure:{attempt.id}", task.workflow_id, requests,
                    )
                    wait_for = tuple(item.id for item in diagnostic_work)
                    for item in self._work_items(tx, attempt.work_item_ids):
                        if item.status == WorkItemStatus.PENDING:
                            self._write_work_item(tx, replace(
                                item, wait_for_work_item_ids=tuple(dict.fromkeys(
                                    (*item.wait_for_work_item_ids, *wait_for),
                                )),
                            ))
                    finished = replace(finished, diagnostics={
                        **finished.diagnostics,
                        "recovery": {
                            "work_item_ids": list(wait_for),
                            "target_task_ids": [request.target_task_id for request in requests],
                        },
                    })
                    self._write_attempt(tx, finished)
                    self._event(tx, "AttemptRecoveryRequested", attempt.id, finished.diagnostics["recovery"])
            return finished

    def _complete_human_task_tx(
        self, tx: sqlite3.Connection, task: Task,
        rows: Sequence[tuple[WorkItem, WorkItem, str]], event_id: str,
    ) -> list[WorkItem]:
        """Record one explicit human response as an immutable Task delivery."""
        if task.executor != TaskExecutor.HUMAN or task.brief is None or not task.frozen:
            raise StateConflict(f"Task {task.id} is not a frozen human Task")
        inputs = self._resolved_deliveries(tx, task)
        if inputs is None:
            raise StateConflict(f"human Task {task.id} dependencies are not released")
        if self._active_attempt(tx, task.id):
            raise StateConflict(f"human Task {task.id} already has an active Attempt")
        declaration = task.outputs[0]
        ordinal = int(tx.execute(
            "SELECT COUNT(*) FROM attempts WHERE task_id = ?", (task.id,),
        ).fetchone()[0]) + 1
        role = self._role(tx, task.role, task.role_version)
        question_ids = tuple(question.id for question, _, _ in rows)
        answer_items = tuple(answer for _, answer, _ in rows)
        decision = (
            rows[0][2] if len(rows) == 1 else
            json.dumps(
                {question.id: answer for question, _, answer in rows},
                ensure_ascii=False, sort_keys=True,
            )
        )
        attempt = Attempt(
            id=f"attempt-{uuid.uuid4().hex}", task_id=task.id,
            ordinal=ordinal, status=AttemptStatus.SUCCEEDED,
            work_item_ids=question_ids + tuple(item.id for item in answer_items),
            input_deliveries=inputs,
            role=task.role, role_version=task.role_version,
            role_instruction=role.instruction, role_skills=role.skills,
            role_accepted_types=role.accepted_types,
            brief=task.brief, brief_digest=task.brief.digest,
            permission=task.permission, framework="human", executor=TaskExecutor.HUMAN,
            verdict="pass", session_id=f"human:{event_id}",
            diagnostics={"answer_event_id": event_id},
            finished_at=utc_now(),
        )
        tx.execute(
            "INSERT INTO attempts(id, task_id, ordinal, status, document) "
            "VALUES (?, ?, ?, ?, ?)",
            (attempt.id, task.id, ordinal, attempt.status.value, _json(_attempt_doc(attempt))),
        )
        artifact = Artifact(
            id=f"artifact-{uuid.uuid4().hex}",
            type=declaration.artifact_type,
            schema_version=declaration.schema_version,
            producer=ArtifactProducer(
                workflow_id=task.workflow_id, task_id=task.id,
                attempt_id=attempt.id, role=task.role,
                role_version=task.role_version,
            ),
            content=ArtifactContent(kind="inline"),
            payload={"subject": task.id, "decision": decision},
            input_artifact_ids=tuple(inputs.values()),
            metadata={"workflow_id": task.workflow_id, "task_key": task.key},
        )
        tx.execute(
            "INSERT INTO artifacts(id, type, attempt_id, digest, document) "
            "VALUES (?, ?, ?, ?, ?)",
            (artifact.id, artifact.type, attempt.id, artifact.digest, _json(artifact.document())),
        )
        tx.execute(
            "INSERT INTO attempt_outputs(attempt_id, output_name, artifact_id) "
            "VALUES (?, ?, ?)",
            (attempt.id, declaration.name, artifact.id),
        )
        accepted_at = utc_now()
        tx.execute(
            "INSERT INTO deliveries(task_id, output_name, artifact_id, attempt_id, accepted_at) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(task_id, output_name) DO UPDATE SET "
            "artifact_id=excluded.artifact_id, attempt_id=excluded.attempt_id, "
            "accepted_at=excluded.accepted_at",
            (task.id, declaration.name, artifact.id, attempt.id, accepted_at),
        )
        tx.execute(
            "INSERT INTO delivery_history(task_id, output_name, artifact_id, attempt_id, accepted_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (task.id, declaration.name, artifact.id, attempt.id, accepted_at),
        )
        resolved: list[WorkItem] = []
        for item in answer_items:
            completed = replace(
                item, status=WorkItemStatus.RESOLVED,
                claimed_attempt_id=attempt.id, resolved_attempt_id=attempt.id,
            )
            self._write_work_item(tx, completed)
            resolved.append(completed)
        self._event(tx, "AttemptFinished", attempt.id, {
            "status": AttemptStatus.SUCCEEDED.value,
            "artifact_ids": {declaration.name: artifact.id},
            "verdict": "pass", "executor": "human",
        })
        self._record_joint_arrivals(
            tx, attempt, "pass", f"Human answer event {event_id}",
        )
        return resolved

    def finish_attempt_success(
        self, attempt_id: str, outputs: Mapping[str, Artifact], *,
        verdict: str = "", session_id: str = "", workspace_commit: str = "",
        work_event_id: str = "", work_requests: Sequence[WorkRequest] = (),
        diagnostics: Mapping | None = None,
    ) -> Attempt:
        """Publish outputs, resolve only claimed work, and apply feedback atomically."""
        with self.transaction() as tx:
            attempt = self._attempt(tx, attempt_id)
            if attempt.status != AttemptStatus.RUNNING:
                raise StateConflict("only a running Attempt can publish a Delivery")
            task = self._task(tx, attempt.task_id)
            declarations = {output.name: output for output in task.outputs}
            if set(outputs) != set(declarations):
                raise DomainError(
                    f"Attempt output mismatch; expected={sorted(declarations)}, "
                    f"received={sorted(outputs)}"
                )
            for name, artifact in outputs.items():
                declaration = declarations[name]
                if artifact.producer.attempt_id != attempt.id or artifact.producer.task_id != task.id:
                    raise DomainError("Artifact producer does not own this Attempt")
                if (artifact.type, artifact.schema_version) != (
                    declaration.artifact_type, declaration.schema_version,
                ):
                    raise DomainError(f"output {name} violates its Artifact contract")
                tx.execute(
                    "INSERT INTO artifacts(id, type, attempt_id, digest, document) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (artifact.id, artifact.type, attempt.id, artifact.digest, _json(artifact.document())),
                )
                tx.execute(
                    "INSERT INTO attempt_outputs(attempt_id, output_name, artifact_id) "
                    "VALUES (?, ?, ?)", (attempt.id, name, artifact.id),
                )
                accepted_at = utc_now()
                tx.execute(
                    "INSERT INTO deliveries(task_id, output_name, artifact_id, attempt_id, accepted_at) "
                    "VALUES (?, ?, ?, ?, ?) ON CONFLICT(task_id, output_name) DO UPDATE SET "
                    "artifact_id=excluded.artifact_id, attempt_id=excluded.attempt_id, "
                    "accepted_at=excluded.accepted_at",
                    (task.id, name, artifact.id, attempt.id, accepted_at),
                )
                tx.execute(
                    "INSERT INTO delivery_history(task_id, output_name, artifact_id, attempt_id, accepted_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (task.id, name, artifact.id, attempt.id, accepted_at),
                )
            for item in self._work_items(tx, attempt.work_item_ids):
                if item.status == WorkItemStatus.PENDING:
                    self._write_work_item(tx, replace(
                        item, status=WorkItemStatus.RESOLVED,
                        resolved_attempt_id=attempt.id,
                    ))
            finished = replace(
                attempt, status=AttemptStatus.SUCCEEDED,
                verdict=verdict, session_id=session_id or attempt.session_id,
                workspace_commit=workspace_commit or attempt.workspace_commit,
                diagnostics={**attempt.diagnostics, **dict(diagnostics or {})},
                finished_at=utc_now(),
            )
            self._write_attempt(tx, finished)
            if work_requests:
                if not work_event_id:
                    raise DomainError("feedback published with a Delivery requires an event id")
                self._apply_work_event_tx(
                    tx, work_event_id, task.workflow_id, work_requests,
                )
            self._event(tx, "AttemptFinished", attempt.id, {
                "status": AttemptStatus.SUCCEEDED.value,
                "artifact_ids": {name: artifact.id for name, artifact in outputs.items()},
                "verdict": verdict,
            })
            self._record_joint_arrivals(
                tx, finished, verdict or AttemptStatus.SUCCEEDED.value,
                f"Attempt {attempt.id} delivered {', '.join(outputs)}",
            )
            self._refresh_workflow_completion(tx, task.workflow_id)
            return finished

    def get_artifact(self, artifact_id: str) -> Artifact | None:
        row = self._connection.execute(
            "SELECT document FROM artifacts WHERE id = ?", (artifact_id,),
        ).fetchone()
        return _artifact_from(json.loads(row["document"])) if row else None

    def list_artifacts(self) -> list[Artifact]:
        return [
            _artifact_from(json.loads(row["document"]))
            for row in self._connection.execute(
                "SELECT document FROM artifacts ORDER BY rowid"
            ).fetchall()
        ]

    def deliveries(self, task_id: str) -> dict[str, Delivery]:
        rows = self._connection.execute(
            "SELECT task_id, output_name, artifact_id, attempt_id, accepted_at "
            "FROM deliveries WHERE task_id = ?", (task_id,),
        ).fetchall()
        return {
            row["output_name"]: Delivery(**dict(row)) for row in rows
        }

    def delivery_history(self, task_id: str, output_name: str) -> list[Delivery]:
        rows = self._connection.execute(
            "SELECT task_id, output_name, artifact_id, attempt_id, accepted_at "
            "FROM delivery_history WHERE task_id = ? AND output_name = ? ORDER BY sequence",
            (task_id, output_name),
        ).fetchall()
        return [Delivery(**dict(row)) for row in rows]

    def pause_task(self, task_id: str, reason: str) -> None:
        if not reason.strip():
            raise DomainError("pause requires a reason")
        with self.transaction() as tx:
            self._task(tx, task_id)
            tx.execute("UPDATE tasks SET paused_reason = ? WHERE id = ?", (reason, task_id))
            self._event(tx, "TaskPaused", task_id, {"reason": reason})

    def request_workflow_stop(self, workflow_id: str, reason: str) -> None:
        """Persist operator intent before process termination can finish an Attempt."""
        if not reason.strip():
            raise DomainError("Workflow stop requires a reason")
        with self.transaction() as tx:
            workflow = self._workflow(tx, workflow_id)
            if workflow.status == WorkflowStatus.COMPLETE:
                return
            for task in self._tasks(tx, workflow_id):
                attempt = self._active_attempt(tx, task.id)
                if attempt is not None:
                    self._write_attempt(tx, replace(attempt, diagnostics={
                        **attempt.diagnostics, "operator_cancelled": True,
                        "operator_cancel_reason": reason.strip(),
                    }))
            self._write_workflow(tx, replace(
                workflow, status=WorkflowStatus.PAUSED, paused_reason=reason.strip(),
            ))
            self._event(tx, "WorkflowStopRequested", workflow_id, {"reason": reason.strip()})

    def pause_workflow(self, workflow_id: str, reason: str) -> None:
        """Pause a quiescent Workflow with an explicit, visible reason."""
        if not reason.strip():
            raise DomainError("Workflow pause requires a reason")
        with self.transaction() as tx:
            workflow = self._workflow(tx, workflow_id)
            if any(self._active_attempt(tx, task.id) for task in self._tasks(tx, workflow_id)):
                raise StateConflict("cannot pause a Workflow with active Attempts")
            paused = replace(
                workflow, status=WorkflowStatus.PAUSED,
                paused_reason=reason.strip(),
            )
            self._write_workflow(tx, paused)
            self._event(tx, "WorkflowPaused", workflow_id, {"reason": paused.paused_reason})

    def resume_task(
        self, task_id: str, *, additional_attempts: int = 0,
        reason: str = "operator resume",
    ) -> None:
        if additional_attempts < 0:
            raise DomainError("additional_attempts cannot be negative")
        with self.transaction() as tx:
            task = self._task(tx, task_id)
            if additional_attempts:
                tx.execute(
                    "INSERT INTO attempt_budget_extensions("
                    "task_id, additional_attempts, reason, created_at) VALUES (?, ?, ?, ?)",
                    (task_id, additional_attempts, reason, utc_now()),
                )
            tx.execute("UPDATE tasks SET paused_reason = '' WHERE id = ?", (task_id,))
            workflow = self._workflow(tx, task.workflow_id)
            if workflow.status == WorkflowStatus.PAUSED:
                self._write_workflow(tx, replace(
                    workflow, status=WorkflowStatus.ACTIVE, paused_reason="",
                ))
            self._event(tx, "TaskResumed", task_id, {
                "additional_attempts": additional_attempts, "reason": reason,
            })

    def resume_workflow(
        self, workflow_id: str, *, additional_attempts: int | None = None,
    ) -> None:
        with self.transaction() as tx:
            workflow = self._workflow(tx, workflow_id)
            for task in self._tasks(tx, workflow_id):
                paused = tx.execute(
                    "SELECT paused_reason FROM tasks WHERE id = ?", (task.id,),
                ).fetchone()["paused_reason"]
                attempts = int(tx.execute(
                    "SELECT COUNT(*) FROM attempts WHERE task_id = ?", (task.id,),
                ).fetchone()[0])
                extensions = int(tx.execute(
                    "SELECT COALESCE(SUM(additional_attempts), 0) "
                    "FROM attempt_budget_extensions WHERE task_id = ?", (task.id,),
                ).fetchone()[0])
                exhausted_with_work = (
                    bool(self._pending_work(tx, task.id))
                    and attempts >= task.max_attempts + extensions
                )
                if paused or exhausted_with_work:
                    grant = task.max_attempts if additional_attempts is None else additional_attempts
                    if grant:
                        tx.execute(
                            "INSERT INTO attempt_budget_extensions("
                            "task_id, additional_attempts, reason, created_at) VALUES (?, ?, ?, ?)",
                            (task.id, grant, "workflow resume", utc_now()),
                        )
                    tx.execute("UPDATE tasks SET paused_reason = '' WHERE id = ?", (task.id,))
            if workflow.status == WorkflowStatus.PAUSED:
                self._write_workflow(tx, replace(
                    workflow, status=WorkflowStatus.ACTIVE, paused_reason="",
                ))
            self._event(tx, "WorkflowResumed", workflow_id, {
                "additional_attempts_per_paused_task": (
                    "task_default_budget" if additional_attempts is None else additional_attempts
                ),
            })

    def graph_snapshot(self, workflow_id: str) -> dict:
        workflow = self.get_workflow(workflow_id)
        if workflow is None:
            raise KeyError(workflow_id)
        tasks = self.list_tasks(workflow_id)
        return {
            "workflow": _workflow_doc(workflow),
            "tasks": [
                {
                    **_task_doc(task),
                    "state": self.task_state(task.id).value,
                    "attempts": [_attempt_doc(item) for item in self.list_attempts(task.id)],
                    "pending_work": [_work_item_doc(item) for item in self.pending_work(task.id)],
                    "deliveries": {
                        name: asdict(delivery)
                        for name, delivery in self.deliveries(task.id).items()
                    },
                }
                for task in tasks
            ],
            "edges": [
                {
                    "source_task_id": dependency.upstream_task_id,
                    "target_task_id": task.id,
                    "input_name": dependency.input_name,
                    "output_name": dependency.output_name,
                    "required_type": dependency.required_type,
                    "release": asdict(dependency.condition),
                }
                for task in tasks for dependency in task.dependencies
            ],
        }

    def dashboard_snapshot(self, workflow_id: str = "") -> dict:
        """Return the dashboard projection, optionally scoped to one workflow.

        The unscoped projection remains available to the Task Graph inspector.
        Product workflow pages should always pass ``workflow_id``: otherwise a
        long-lived project repeatedly serializes every historical Task, Attempt
        and Artifact merely to paint one seven-node graph.
        """
        tasks: list[dict] = []
        runs: list[dict] = []
        edges: list[dict] = []
        workflows = self.list_workflows()
        selected_workflows = (
            [item for item in workflows if item.id == workflow_id]
            if workflow_id else workflows
        )
        selected_task_ids: set[str] = set()
        referenced_artifact_ids: set[str] = set()
        for workflow in selected_workflows:
            for task in self.list_tasks(workflow.id):
                selected_task_ids.add(task.id)
                state = self.task_state(task.id)
                attempts = self.list_attempts(task.id)
                latest_attempt = attempts[-1] if attempts else None
                status = {
                    TaskState.IDLE: "waiting",
                    TaskState.WAITING: "waiting",
                    TaskState.READY: "ready",
                    TaskState.RUNNING: "running",
                    TaskState.SATISFIED: "succeeded",
                    TaskState.PAUSED: "paused",
                }[state]
                pending_work = self.pending_work(task.id)
                if any(item.kind == WorkItemKind.HUMAN_QUESTION for item in pending_work):
                    status = "awaiting_human"
                elif (
                    workflow.status == WorkflowStatus.PAUSED
                    and state != TaskState.SATISFIED
                ):
                    # A workflow-level operator/awaiting-condition pause owns
                    # execution even when the Task's pending work would
                    # otherwise be claimable. Do not advertise it as ready.
                    status = "paused"
                if (
                    state == TaskState.SATISFIED
                    and latest_attempt is not None
                    and latest_attempt.verdict == "fail"
                ):
                    # Execution succeeded in delivering a credible failed
                    # engineering report. Keep Run execution truth separate,
                    # but project the Task node as failed/blocked for users.
                    status = "failed"
                deliveries = self.deliveries(task.id)
                input_rows = [
                    {
                        "name": item.name, "required_type": item.required_type,
                        "artifact_id": item.artifact_id,
                        "source_task_id": "", "source_output": "",
                        "optional": item.optional,
                    }
                    for item in task.initial_inputs
                ] + [
                    {
                        "name": item.input_name, "required_type": item.required_type,
                        "artifact_id": "",
                        "source_task_id": item.upstream_task_id,
                        "source_output": item.output_name,
                        "optional": item.optional,
                    }
                    for item in task.dependencies
                ]
                referenced_artifact_ids.update(
                    item.artifact_id for item in task.initial_inputs
                    if item.artifact_id
                )
                for attempt in attempts:
                    referenced_artifact_ids.update(attempt.input_deliveries.values())
                tasks.append({
                    "id": task.id, "role": task.role,
                    "role_version": task.role_version,
                    "instruction": task.brief.objective if task.brief else task.intent,
                    "brief": asdict(task.brief) if task.brief else None,
                    "inputs": input_rows,
                    "outputs": [asdict(item) for item in task.outputs],
                    "write_paths": list(task.permission.write_paths),
                    "permission": asdict(task.permission),
                    "executor": task.executor.value,
                    "framework": task.framework, "model": task.model,
                    "gates": [asdict(item) for item in task.hard_gates],
                    "status": status,
                    "metadata": {
                        "workflow_id": workflow.id,
                        "recipe_task": task.key,
                        "recipe": workflow.recipe.split("@", 1)[0],
                        "static_task_attempt": True,
                        "stage": task.display_group,
                        "on_demand": task.on_demand,
                        "pending_work": len(pending_work),
                        "pending_human_questions": sum(
                            item.kind == WorkItemKind.HUMAN_QUESTION
                            for item in pending_work
                        ),
                    },
                    "pending_work_items": [
                        _work_item_doc(item) for item in pending_work
                    ],
                })
                for initial in task.initial_inputs:
                    if initial.artifact_id:
                        edges.append({
                            "from": initial.artifact_id, "to": task.id,
                            "kind": "consumes", "name": initial.name,
                        })
                for dependency in task.dependencies:
                    delivery = self.deliveries(dependency.upstream_task_id).get(
                        dependency.output_name
                    )
                    if delivery:
                        edges.append({
                            "from": delivery.artifact_id, "to": task.id,
                            "kind": "consumes", "name": dependency.input_name,
                        })
                    edges.append({
                        "from": dependency.upstream_task_id, "to": task.id,
                        "kind": "depends", "name": dependency.input_name,
                    })
                for output_name, delivery in deliveries.items():
                    edges.append({
                        "from": task.id, "to": delivery.artifact_id,
                        "kind": "produces", "name": output_name,
                    })
                for attempt in attempts:
                    runs.append({
                        "id": attempt.id, "task_id": attempt.task_id,
                        "attempt": attempt.ordinal, "role": attempt.role,
                        "role_version": attempt.role_version,
                        "input_artifacts": list(attempt.input_deliveries.values()),
                        "framework": attempt.framework, "model": attempt.model,
                        "session_id": attempt.session_id,
                        "status": attempt.status.value,
                        "engineering_verdict": attempt.verdict,
                        "diagnostics": dict(attempt.diagnostics),
                        "created_at": attempt.created_at,
                        "finished_at": attempt.finished_at,
                    })
        all_artifacts = self.list_artifacts()
        # Input selection is a different concern from the selected
        # Workflow's immutable history. Keep only formally published PREPARE
        # deliveries in this side channel. A draft with the same Artifact
        # type is not an implementation baseline merely because it is newer.
        available_initial_by_type: dict[str, Artifact] = {}

        def consider_prepare_input(artifact: Artifact) -> None:
            previous = available_initial_by_type.get(artifact.type)
            if previous is None or (
                artifact.created_at, artifact.id
            ) > (
                previous.created_at, previous.id
            ):
                available_initial_by_type[artifact.type] = artifact

        # Stable imports created by the pre-v2 PREPARE UI remain legitimate
        # immutable inputs; they are data, not retired scheduling state.
        for artifact in all_artifacts:
            if (
                artifact.producer.workflow_id == "prepare"
                or artifact.metadata.get("workflow_id") == "prepare"
            ):
                consider_prepare_input(artifact)

        # Recipe v2 publishes the four implementation inputs through named
        # Delivery slots. Select those slots only after the entire PREPARE
        # Workflow is complete; do not infer authority from Artifact ids,
        # timestamps, metadata ancestry, or a same-typed draft.
        prepare_slots = {
            "design.specification": ("generate-design-document", "design"),
            "specification.csir": (
                "freeze-specification-baseline", "specification",
            ),
            "implementation.constraints": (
                "freeze-project-constraints", "constraints",
            ),
            "acceptance.plan": ("freeze-acceptance-plan", "acceptance"),
        }
        for workflow in workflows:
            if (
                workflow.recipe.split("@", 1)[0]
                != "specification-baseline-preparation"
                or workflow.status != WorkflowStatus.COMPLETE
            ):
                continue
            by_key = {task.key: task for task in self.list_tasks(workflow.id)}
            for artifact_type, (task_key, output_name) in prepare_slots.items():
                task = by_key.get(task_key)
                delivery = (
                    self.deliveries(task.id).get(output_name)
                    if task is not None else None
                )
                artifact = (
                    self.get_artifact(delivery.artifact_id)
                    if delivery is not None else None
                )
                if artifact is not None and artifact.type == artifact_type:
                    consider_prepare_input(artifact)
        if workflow_id:
            all_artifacts = [
                artifact for artifact in all_artifacts
                if artifact.id in referenced_artifact_ids
                or artifact.producer.task_id in selected_task_ids
            ]
        artifacts = [_dashboard_artifact_doc(artifact) for artifact in all_artifacts]
        return {
            "tasks": tasks, "runs": runs,
            "artifacts": artifacts, "edges": edges,
            "available_initial_artifacts": [
                _dashboard_artifact_doc(artifact)
                for artifact in sorted(
                    available_initial_by_type.values(),
                    key=lambda item: (item.type, item.created_at, item.id),
                )
            ],
            # Keep the inexpensive workflow directory unscoped so the client
            # can select the newest instance without another full snapshot.
            "workflows": [_workflow_doc(item) for item in workflows],
        }

    def events(self) -> list[dict]:
        return [
            {
                "sequence": row["sequence"], "kind": row["kind"],
                "subject_id": row["subject_id"],
                "document": json.loads(row["document"]),
                "created_at": row["created_at"],
            }
            for row in self._connection.execute(
                "SELECT * FROM events ORDER BY sequence"
            ).fetchall()
        ]

    def _apply_work_event_tx(
        self, tx: sqlite3.Connection, event_id: str, workflow_id: str,
        requests: Sequence[WorkRequest],
    ) -> list[WorkItem]:
        if tx.execute("SELECT 1 FROM work_events WHERE event_id = ?", (event_id,)).fetchone():
            return []
        self._validate_work_requests(tx, workflow_id, requests)
        created: list[WorkItem] = []
        for request in requests:
            created.append(self._append_work_item(
                tx, request.target_task_id, request.kind, request.request_key,
                request.summary, source_task_id=request.source_task_id,
                correlation_key=request.correlation_key or request.request_key,
                causal_correlation_keys=request.causal_correlation_keys,
                evidence_artifact_ids=request.evidence_artifact_ids,
                evidence_attempt_ids=request.evidence_attempt_ids,
            ))
            if request.propagate_to_dependents:
                created.extend(self._propagate_reverification(
                    tx, request.target_task_id, request.request_key, request.summary,
                    correlation_key=request.correlation_key or request.request_key,
                    causal_correlation_keys=request.causal_correlation_keys,
                ))
        tx.execute(
            "INSERT INTO work_events(event_id, workflow_id, document, processed_at) "
            "VALUES (?, ?, ?, ?)",
            (event_id, workflow_id, _json({"requests": [asdict(r) for r in requests]}), utc_now()),
        )
        self._mark_workflow_active(tx, workflow_id)
        return created

    def _validate_work_requests(
        self, tx: sqlite3.Connection, workflow_id: str,
        requests: Sequence[WorkRequest],
    ) -> None:
        task_ids = {task.id for task in self._tasks(tx, workflow_id)}
        if any(request.target_task_id not in task_ids for request in requests):
            raise DomainError("work event targets a Task outside this Workflow")
        invalid_sources = sorted({
            request.source_task_id
            for request in requests
            if request.source_task_id and request.source_task_id not in task_ids
        })
        if invalid_sources:
            raise DomainError(
                f"work event names sources outside this Workflow: {invalid_sources}"
            )
        missing_evidence = sorted({
            artifact_id
            for request in requests
            for artifact_id in request.evidence_artifact_ids
            if tx.execute(
                "SELECT 1 FROM artifacts WHERE id = ?", (artifact_id,),
            ).fetchone() is None
        })
        if missing_evidence:
            raise DomainError(
                f"work event references unavailable evidence: {missing_evidence}"
            )
        for request in requests:
            for attempt_id in request.evidence_attempt_ids:
                attempt = self.get_attempt(attempt_id)
                if (
                    attempt is None or attempt.task_id not in task_ids
                    or not (attempt.status == AttemptStatus.FAILED or (
                        attempt.status == AttemptStatus.SUCCEEDED and attempt.verdict == "fail"
                    ))
                ):
                    raise DomainError(f"work event references invalid failure Attempt: {attempt_id}")

    def _append_work_item(
        self, tx: sqlite3.Connection, task_id: str, kind: WorkItemKind,
        request_key: str, summary: str, *, source_task_id: str = "",
        evidence_artifact_ids: Sequence[str] = (),
        wait_for_work_item_ids: Sequence[str] = (),
        evidence_attempt_ids: Sequence[str] = (),
        correlation_key: str = "",
        causal_correlation_keys: Sequence[str] = (),
    ) -> WorkItem:
        self._task(tx, task_id)
        if not request_key or not summary.strip():
            raise DomainError("work item requires idempotency key and summary")
        row = tx.execute(
            "SELECT document FROM work_items WHERE task_id = ? AND request_key = ?",
            (task_id, request_key),
        ).fetchone()
        if row:
            return _work_item_from(json.loads(row["document"]))
        sequence = int(tx.execute(
            "SELECT COALESCE(MAX(created_sequence), 0) + 1 FROM work_items WHERE task_id = ?",
            (task_id,),
        ).fetchone()[0])
        item = WorkItem(
            id=f"work-{uuid.uuid4().hex}", task_id=task_id, kind=kind,
            request_key=request_key, correlation_key=correlation_key or request_key,
            causal_correlation_keys=tuple(dict.fromkeys(
                key for key in causal_correlation_keys
                if key and key != (correlation_key or request_key)
            )),
            summary=summary,
            source_task_id=source_task_id,
            evidence_artifact_ids=tuple(evidence_artifact_ids),
            wait_for_work_item_ids=tuple(wait_for_work_item_ids),
            evidence_attempt_ids=tuple(evidence_attempt_ids),
            created_sequence=sequence,
        )
        tx.execute(
            "INSERT INTO work_items(id, task_id, request_key, status, created_sequence, document) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (item.id, task_id, request_key, item.status.value, sequence, _json(_work_item_doc(item))),
        )
        self._event(tx, "WorkAdded", item.id, {
            "task_id": task_id, "kind": kind.value, "request_key": request_key,
        })
        return item

    def _propagate_reverification(
        self, tx: sqlite3.Connection, upstream_task_id: str,
        request_key: str, summary: str, *, correlation_key: str = "",
        causal_correlation_keys: Sequence[str] = (),
    ) -> list[WorkItem]:
        tasks = self._tasks(tx, self._task(tx, upstream_task_id).workflow_id)
        by_upstream: dict[str, list[Task]] = {}
        for task in tasks:
            for dependency in task.dependencies:
                by_upstream.setdefault(dependency.upstream_task_id, []).append(task)
        result: list[WorkItem] = []
        upstream_items = [
            item for item in self._pending_work(tx, upstream_task_id)
            if item.request_key == request_key
        ]
        wait_for = tuple(item.id for item in upstream_items)
        pending = [(task, wait_for) for task in by_upstream.get(upstream_task_id, ())]
        visited: set[str] = set()
        while pending:
            task, prerequisites = pending.pop(0)
            if task.id in visited:
                continue
            visited.add(task.id)
            # A never-started downstream Task already owns its initial work.
            # A delivered Task, or one whose active Attempt captured the old
            # upstream state, needs an explicit later revalidation request.
            # The active Attempt remains immutable and continues; this new
            # WorkItem stays outside its captured work-item cursor.
            if self._deliveries(tx, task.id) or self._active_attempt(tx, task.id):
                reverify = self._append_work_item(
                    tx, task.id, WorkItemKind.REVERIFY,
                    request_key=f"reverify:{request_key}:{task.id}",
                    summary=f"Revalidate after upstream change: {summary}",
                    source_task_id=upstream_task_id,
                    wait_for_work_item_ids=prerequisites,
                    correlation_key=correlation_key or request_key,
                    causal_correlation_keys=causal_correlation_keys,
                )
                result.append(reverify)
                downstream_wait = (reverify.id,)
            else:
                downstream_wait = prerequisites
            pending.extend(
                (dependent, downstream_wait)
                for dependent in by_upstream.get(task.id, ())
            )
        return result

    def _record_joint_arrivals(
        self, tx: sqlite3.Connection, attempt: Attempt,
        outcome: str, summary: str,
    ) -> None:
        groups = [
            json.loads(row["document"])
            for row in tx.execute(
                "SELECT document FROM joint_analysis_groups WHERE workflow_id = "
                "(SELECT workflow_id FROM tasks WHERE id = ?)",
                (attempt.task_id,),
            ).fetchall()
        ]
        work_items = self._work_items(tx, attempt.work_item_ids)
        correlations = {item.correlation_key for item in work_items}
        for raw in groups:
            members = tuple(raw["member_task_ids"])
            if attempt.task_id not in members:
                continue
            for correlation in correlations:
                tx.execute(
                    "INSERT OR IGNORE INTO joint_analysis_arrivals("
                    "group_id, correlation_key, member_task_id, attempt_id, outcome, summary"
                    ") VALUES (?, ?, ?, ?, ?, ?)",
                    (raw["id"], correlation, attempt.task_id, attempt.id, outcome, summary),
                )
                arrived = {
                    row["member_task_id"]
                    for row in tx.execute(
                        "SELECT member_task_id FROM joint_analysis_arrivals "
                        "WHERE group_id = ? AND correlation_key = ?",
                        (raw["id"], correlation),
                    ).fetchall()
                }
                if arrived != set(members):
                    continue
                if tx.execute(
                    "SELECT 1 FROM joint_analysis_dispatches WHERE group_id = ? AND correlation_key = ?",
                    (raw["id"], correlation),
                ).fetchone():
                    continue
                rows = tx.execute(
                    "SELECT member_task_id, outcome, summary FROM joint_analysis_arrivals "
                    "WHERE group_id = ? AND correlation_key = ? ORDER BY member_task_id",
                    (raw["id"], correlation),
                ).fetchall()
                analysis_work = self._append_work_item(
                    tx, raw["analyzer_task_id"], WorkItemKind.FEEDBACK,
                    request_key=f"joint:{raw['id']}:{correlation}",
                    correlation_key=correlation,
                    summary="Joint results ready: " + json.dumps(
                        [dict(row) for row in rows], ensure_ascii=False,
                    ),
                )
                tx.execute(
                    "INSERT INTO joint_analysis_dispatches(group_id, correlation_key, work_item_id) "
                    "VALUES (?, ?, ?)",
                    (raw["id"], correlation, analysis_work.id),
                )

    def _dependencies_satisfied(self, task: Task) -> bool:
        with self.transaction() as tx:
            return self._resolved_deliveries(tx, task) is not None

    def _resolved_deliveries(
        self, tx: sqlite3.Connection, task: Task,
    ) -> dict[str, str] | None:
        result: dict[str, str] = {}
        for item in task.initial_inputs:
            if item.optional and not item.artifact_id:
                continue
            try:
                artifact = self._artifact(tx, item.artifact_id)
            except KeyError:
                return None
            if artifact.type != item.required_type:
                return None
            result[item.name] = artifact.id
        for dependency in task.dependencies:
            # A previous Delivery remains historical evidence, but it is not
            # released for a new downstream Attempt while its owner has work.
            if self._pending_work(tx, dependency.upstream_task_id) or self._active_attempt(
                tx, dependency.upstream_task_id
            ):
                return None
            row = tx.execute(
                "SELECT artifact_id, attempt_id FROM deliveries WHERE task_id = ? AND output_name = ?",
                (dependency.upstream_task_id, dependency.output_name),
            ).fetchone()
            if row is None:
                if dependency.optional:
                    continue
                return None
            artifact = self._artifact(tx, row["artifact_id"])
            if artifact.type != dependency.required_type:
                return None
            if (
                dependency.condition.field == "verdict"
                and dependency.condition.equals in ("pass", "passed")
                and self._attempt(tx, row["attempt_id"]).verdict in ("fail", "failed")
            ):
                return None
            if not dependency.condition.accepts(artifact.payload):
                return None
            result[dependency.input_name] = artifact.id
        return result

    def _refresh_workflow_completion(self, tx: sqlite3.Connection, workflow_id: str) -> None:
        workflow = self._workflow(tx, workflow_id)
        tasks = self._tasks(tx, workflow_id)
        unfinished = False
        for task in tasks:
            if self._active_attempt(tx, task.id) or self._pending_work(tx, task.id):
                unfinished = True
                break
            if task.required and not task.on_demand:
                delivered = self._deliveries(tx, task.id)
                if set(delivered) != {output.name for output in task.outputs}:
                    unfinished = True
                    break
                delivery_attempts = {
                    delivery.attempt_id for delivery in delivered.values()
                }
                if any(
                    self._attempt(tx, attempt_id).verdict == "fail"
                    for attempt_id in delivery_attempts
                ):
                    # A credible failed report is a valid execution result and
                    # remains the current Delivery, but it cannot satisfy the
                    # Workflow's engineering completion condition.
                    unfinished = True
                    break
        status = (
            workflow.status
            if unfinished and workflow.status == WorkflowStatus.PAUSED
            else WorkflowStatus.ACTIVE if unfinished
            else WorkflowStatus.COMPLETE
        )
        if workflow.status != status:
            self._write_workflow(tx, replace(workflow, status=status))
            self._event(tx, "WorkflowStatusChanged", workflow_id, {"status": status.value})

    def _mark_workflow_active(self, tx: sqlite3.Connection, workflow_id: str) -> None:
        workflow = self._workflow(tx, workflow_id)
        if workflow.status in {WorkflowStatus.READY, WorkflowStatus.COMPLETE}:
            self._write_workflow(tx, replace(workflow, status=WorkflowStatus.ACTIVE))

    @staticmethod
    def _assert_acyclic(tasks: Sequence[Task]) -> None:
        dependencies = {
            task.id: {dep.upstream_task_id for dep in task.dependencies}
            for task in tasks
        }
        remaining = set(dependencies)
        while remaining:
            ready = {task_id for task_id in remaining if not (dependencies[task_id] & remaining)}
            if not ready:
                raise DomainError("static Task dependencies must be acyclic")
            remaining -= ready

    @staticmethod
    def _validate_collaboration(
        task: Task, brief: TaskBrief, tasks: Sequence[Task],
        routes: Sequence[FeedbackRoute] = (),
    ) -> None:
        by_key = {candidate.key: candidate.id for candidate in tasks}
        valid = set(by_key) | {candidate.id for candidate in tasks}
        references: set[str] = set()
        for line in brief.collaboration:
            line_references = [
                match.group(1).rstrip(".,;)")
                for match in re.finditer(r"task:([A-Za-z0-9_.:-]+)", line)
            ]
            unknown = sorted(set(line_references) - valid)
            if unknown:
                raise DomainError(f"Task {task.id} brief references unknown collaborators: {unknown}")
            references.update(by_key.get(reference, reference) for reference in line_references)
        required = {
            dependency.upstream_task_id for dependency in task.dependencies
        } | {
            candidate.id
            for candidate in tasks
            if any(
                dependency.upstream_task_id == task.id
                for dependency in candidate.dependencies
            )
        } | {
            route.target_task_id
            for route in routes
            if route.source_task_id == task.id
        }
        missing = sorted(required - references)
        if missing:
            raise DomainError(
                f"Task {task.id} brief omits required collaborators: {missing}"
            )

    def _workflow(self, tx: sqlite3.Connection, workflow_id: str) -> Workflow:
        row = tx.execute("SELECT document FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        if row is None:
            raise KeyError(workflow_id)
        return _workflow_from(json.loads(row["document"]))

    def _write_workflow(self, tx: sqlite3.Connection, workflow: Workflow) -> None:
        tx.execute(
            "UPDATE workflows SET status = ?, document = ? WHERE id = ?",
            (workflow.status.value, _json(_workflow_doc(workflow)), workflow.id),
        )

    def _tasks(self, tx: sqlite3.Connection, workflow_id: str) -> list[Task]:
        return [
            _task_from(json.loads(row["document"]))
            for row in tx.execute(
                "SELECT document FROM tasks WHERE workflow_id = ? ORDER BY rowid", (workflow_id,),
            ).fetchall()
        ]

    def _task(self, tx: sqlite3.Connection, task_id: str) -> Task:
        row = tx.execute("SELECT document FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)
        return _task_from(json.loads(row["document"]))

    @staticmethod
    def _role(tx: sqlite3.Connection, name: str, version: int) -> Role:
        row = tx.execute(
            "SELECT document FROM roles WHERE name = ? AND version = ?", (name, version),
        ).fetchone()
        if row is None:
            raise KeyError(f"{name}@{version}")
        value = json.loads(row["document"])
        return Role(
            name=value["name"], version=int(value["version"]),
            instruction=value["instruction"],
            accepted_types=tuple(value.get("accepted_types", ())),
            produced_types=tuple(value.get("produced_types", ())),
            skills=tuple(value.get("skills", ())),
            framework=value.get("framework", ""), model=value.get("model", ""),
        )

    def _pending_work(self, tx: sqlite3.Connection, task_id: str) -> list[WorkItem]:
        return [
            _work_item_from(json.loads(row["document"]))
            for row in tx.execute(
                "SELECT document FROM work_items WHERE task_id = ? AND status = ? "
                "ORDER BY created_sequence",
                (task_id, WorkItemStatus.PENDING.value),
            ).fetchall()
        ]

    def _claimable_work(self, tx: sqlite3.Connection, task_id: str) -> list[WorkItem]:
        pending = self._pending_work(tx, task_id)
        if any(item.kind == WorkItemKind.HUMAN_QUESTION for item in pending):
            return []
        result: list[WorkItem] = []
        for item in pending:
            if all(
                self._work_item(tx, prerequisite).status == WorkItemStatus.RESOLVED
                for prerequisite in item.wait_for_work_item_ids
            ):
                result.append(item)
        return result

    def _work_items(self, tx: sqlite3.Connection, ids: Sequence[str]) -> list[WorkItem]:
        return [self._work_item(tx, item_id) for item_id in ids]

    def _work_item(self, tx: sqlite3.Connection, item_id: str) -> WorkItem:
        row = tx.execute("SELECT document FROM work_items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise KeyError(item_id)
        return _work_item_from(json.loads(row["document"]))

    @staticmethod
    def _write_work_item(tx: sqlite3.Connection, item: WorkItem) -> None:
        tx.execute(
            "UPDATE work_items SET status = ?, document = ? WHERE id = ?",
            (item.status.value, _json(_work_item_doc(item)), item.id),
        )

    def _attempt(self, tx: sqlite3.Connection, attempt_id: str) -> Attempt:
        row = tx.execute("SELECT document FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
        if row is None:
            raise KeyError(attempt_id)
        return _attempt_from(json.loads(row["document"]))

    def _active_attempt(self, tx: sqlite3.Connection, task_id: str) -> Attempt | None:
        row = tx.execute(
            "SELECT document FROM attempts WHERE task_id = ? AND status = ?",
            (task_id, AttemptStatus.RUNNING.value),
        ).fetchone()
        return _attempt_from(json.loads(row["document"])) if row else None

    @staticmethod
    def _write_attempt(tx: sqlite3.Connection, attempt: Attempt) -> None:
        tx.execute(
            "UPDATE attempts SET status = ?, document = ? WHERE id = ?",
            (attempt.status.value, _json(_attempt_doc(attempt)), attempt.id),
        )

    def _artifact(self, tx: sqlite3.Connection, artifact_id: str) -> Artifact:
        row = tx.execute("SELECT document FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
        if row is None:
            raise KeyError(artifact_id)
        return _artifact_from(json.loads(row["document"]))

    def _deliveries(self, tx: sqlite3.Connection, task_id: str) -> dict[str, Delivery]:
        rows = tx.execute(
            "SELECT task_id, output_name, artifact_id, attempt_id, accepted_at "
            "FROM deliveries WHERE task_id = ?", (task_id,),
        ).fetchall()
        return {row["output_name"]: Delivery(**dict(row)) for row in rows}

    @staticmethod
    def _event(tx: sqlite3.Connection, kind: str, subject_id: str, document: Mapping) -> None:
        tx.execute(
            "INSERT INTO events(kind, subject_id, document) VALUES (?, ?, ?)",
            (kind, subject_id, _json(document)),
        )


def _json(value: Mapping | Sequence) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _dashboard_artifact_doc(artifact: Artifact) -> dict:
    return {
        **artifact.document(), "digest": artifact.digest,
        "producer": {
            "task_id": artifact.producer.task_id,
            "run_id": artifact.producer.attempt_id,
            "role": artifact.producer.role,
            "role_version": artifact.producer.role_version,
        },
        "inputs": list(artifact.input_artifact_ids),
    }


def _role_doc(role: Role) -> dict:
    return asdict(role)


def _workflow_doc(workflow: Workflow) -> dict:
    return {**asdict(workflow), "status": workflow.status.value}


def _workflow_from(value: Mapping) -> Workflow:
    return Workflow(**{**value, "status": WorkflowStatus(value["status"])})


def _permission_from(value: Mapping) -> PermissionGrant:
    return PermissionGrant(
        read_paths=tuple(value.get("read_paths", ())),
        write_paths=tuple(value.get("write_paths", ())),
        tools=tuple(value.get("tools", ())),
    )


def _brief_from(value: Mapping | None) -> TaskBrief | None:
    if value is None:
        return None
    return TaskBrief(
        objective=value["objective"],
        deliverables=tuple(value["deliverables"]),
        responsibilities=tuple(value["responsibilities"]),
        exclusions=tuple(value["exclusions"]),
        completion_criteria=tuple(value["completion_criteria"]),
        collaboration=tuple(value["collaboration"]),
    )


def _dependency_from(value: Mapping) -> Dependency:
    condition = value.get("condition") or {}
    return Dependency(
        input_name=value["input_name"], upstream_task_id=value["upstream_task_id"],
        output_name=value["output_name"], required_type=value["required_type"],
        condition=ReleaseCondition(**condition), optional=bool(value.get("optional", False)),
    )


def _task_doc(task: Task) -> dict:
    return {
        **asdict(task),
        "permission": asdict(task.permission),
        "initial_inputs": [asdict(item) for item in task.initial_inputs],
        "dependencies": [asdict(dependency) for dependency in task.dependencies],
        "outputs": [asdict(output) for output in task.outputs],
        "executor": task.executor.value,
        "brief": asdict(task.brief) if task.brief else None,
    }


def _task_from(value: Mapping) -> Task:
    return Task(
        id=value["id"], workflow_id=value["workflow_id"], key=value["key"],
        role=value["role"], role_version=value["role_version"], intent=value["intent"],
        permission=_permission_from(value["permission"]),
        initial_inputs=tuple(InitialInput(**item) for item in value.get("initial_inputs", ())),
        dependencies=tuple(_dependency_from(item) for item in value.get("dependencies", ())),
        outputs=tuple(OutputSpec(**item) for item in value.get("outputs", ())),
        hard_gates=tuple(GateSpec(**item) for item in value.get("hard_gates", ())),
        executor=TaskExecutor(value.get("executor", "agent")),
        command=str(value.get("command", "")),
        framework=value.get("framework", ""), model=value.get("model", ""),
        reasoning_effort=value.get("reasoning_effort", ""),
        required=bool(value.get("required", True)),
        on_demand=bool(value.get("on_demand", False)),
        display_group=str(value.get("display_group", "")),
        max_attempts=int(value.get("max_attempts", 8)),
        timeout_seconds=int(value.get("timeout_seconds", 5400)),
        brief=_brief_from(value.get("brief")), frozen=bool(value.get("frozen", False)),
    )


def _work_item_doc(item: WorkItem) -> dict:
    return {
        **asdict(item), "kind": item.kind.value, "status": item.status.value,
        "evidence_artifact_ids": list(item.evidence_artifact_ids),
        "evidence_attempt_ids": list(item.evidence_attempt_ids),
        "causal_correlation_keys": list(item.causal_correlation_keys),
        "wait_for_work_item_ids": list(item.wait_for_work_item_ids),
    }


def _work_item_from(value: Mapping) -> WorkItem:
    return WorkItem(
        **{
            **value,
            "kind": WorkItemKind(value["kind"]),
            "status": WorkItemStatus(value["status"]),
            "evidence_artifact_ids": tuple(value.get("evidence_artifact_ids", ())),
            "evidence_attempt_ids": tuple(value.get("evidence_attempt_ids", ())),
            "causal_correlation_keys": tuple(value.get("causal_correlation_keys", ())),
            "wait_for_work_item_ids": tuple(value.get("wait_for_work_item_ids", ())),
        }
    )


def _attempt_doc(attempt: Attempt) -> dict:
    return {
        **asdict(attempt), "status": attempt.status.value,
        "executor": attempt.executor.value,
        "work_item_ids": list(attempt.work_item_ids),
        "role_skills": list(attempt.role_skills),
        "role_accepted_types": list(attempt.role_accepted_types),
        "input_deliveries": dict(attempt.input_deliveries),
        "permission": asdict(attempt.permission),
        "brief": asdict(attempt.brief),
    }


def _attempt_from(value: Mapping) -> Attempt:
    return Attempt(
        **{
            **value,
            "status": AttemptStatus(value["status"]),
            "work_item_ids": tuple(value.get("work_item_ids", ())),
            "role_skills": tuple(value.get("role_skills", ())),
            "role_accepted_types": tuple(value.get("role_accepted_types", ())),
            "input_deliveries": dict(value.get("input_deliveries", {})),
            "permission": _permission_from(value["permission"]),
            "brief": _brief_from(value["brief"]),
            "executor": TaskExecutor(value.get("executor", "agent")),
        }
    )


def _artifact_from(value: Mapping) -> Artifact:
    return Artifact(
        id=value["id"], type=value["type"], schema_version=value["schema_version"],
        producer=ArtifactProducer(**value["producer"]),
        content=ArtifactContent(
            **{**value["content"], "paths": tuple(value["content"].get("paths", ()))},
        ),
        payload=dict(value["payload"]),
        input_artifact_ids=tuple(value.get("input_artifact_ids", ())),
        metadata=dict(value.get("metadata", {})),
        created_at=value["created_at"], digest=value.get("digest", ""),
    )

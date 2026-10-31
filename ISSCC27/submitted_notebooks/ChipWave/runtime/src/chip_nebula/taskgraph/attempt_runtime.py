"""Execution of one claimed Attempt from the static TaskGraph kernel."""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Protocol

from chip_nebula.adapters.base import is_path_in_write_scope
from chip_nebula.adapters.scope_check import detect_changed_paths, violations
from chip_nebula.gates.exit_gate import ExitGate
from chip_nebula.models.task_manifest import AgentResult, ExitCriterion, TaskContext, TaskManifest
from chip_nebula.taskgraph_run_controls import initialize_timeout_control, timeout_control_path
from chip_nebula.taskgraph.artifacts import ArtifactSchemaRegistry, load_schema_registry
from chip_nebula.taskgraph.tool_executor import DeterministicToolExecutor, ToolCommand

from .context import AttemptContextAssembler
from .domain import (
    Artifact,
    ArtifactContent,
    ArtifactProducer,
    Attempt,
    GateSpec,
    OutputSpec,
    Task,
    TaskExecutor,
)
from .static_recipe import FeedbackRoute
from .static_store import StaticTaskGraphStore
from .work_handler import StaticWorkHandler
from .attempt_workspace import AttemptWorkspaceFactory
from .workspaces import is_publishable_path, preserve_attempt_wip
from .prepare_contracts import enrich_prepare_payload
from .platform_inventory import installed_platform_inventory
from .result_summary import summary_contract


class Dispatcher(Protocol):
    def dispatch(
        self, task: TaskManifest, workspace: Path,
        blocking: bool = True, project_root: Path | None = None,
    ) -> AgentResult: ...


@dataclass(frozen=True)
class AttemptRuntimeResult:
    attempt: Attempt
    artifacts: tuple[Artifact, ...] = ()


_OUTPUT = re.compile(r"NEBULA_OUTPUT\s*:\s*", re.IGNORECASE)
_ERROR_CLASS = re.compile(r"^\s*Error-Class\s*:\s*(\S+)", re.MULTILINE | re.IGNORECASE)
_GIT_TYPES = frozenset({
    "design.specification", "specification.csir", "implementation.constraints", "rtl.snapshot",
    "rtl.integration", "verification.environment", "netlist", "layout", "gds",
})


class AttemptRuntime:
    def __init__(
        self, store: StaticTaskGraphStore, dispatcher: Dispatcher,
        workspaces: AttemptWorkspaceFactory, *, project_root: Path,
        feedback_routes: tuple[FeedbackRoute, ...] = (),
        schema_registry: ArtifactSchemaRegistry | None = None,
    ) -> None:
        self.store = store
        self.dispatcher = dispatcher
        self.workspaces = workspaces
        self.project_root = project_root
        self.feedback_routes = feedback_routes
        self.schema_registry = schema_registry or load_schema_registry(project_root)

    def execute(self, attempt: Attempt) -> AttemptRuntimeResult:
        try:
            return self._execute(attempt)
        except Exception as exc:
            active = self.store.active_attempt(attempt.task_id)
            if active is None or active.id != attempt.id:
                raise
            finished = self.store.finish_attempt_failure(
                attempt.id, reason=f"runtime error: {exc}",
            )
            return AttemptRuntimeResult(finished)

    def _execute(self, attempt: Attempt) -> AttemptRuntimeResult:
        current = self.store.active_attempt(attempt.task_id)
        if current is None or current.id != attempt.id:
            raise ValueError(f"Attempt {attempt.id} is not the active claim")
        task = self.store.get_task(attempt.task_id)
        if task is None:
            raise KeyError(attempt.task_id)
        if task.executor == TaskExecutor.HUMAN:
            raise ValueError("human Tasks are completed by an explicit answer event")
        workflow = self.store.get_workflow(task.workflow_id)
        if workflow is None:
            raise KeyError(task.workflow_id)
        workflow_baseline = str(workflow.metadata.get("baseline_commit", ""))
        attempt = self.store.record_attempt_diagnostics(attempt.id, {
            "runner_pid": os.getpid(),
            "runner_state": "dispatching",
        })
        formal_inputs = [
            self._artifact(artifact_id)
            for artifact_id in attempt.input_deliveries.values()
        ]
        rejected = (
            sorted({item.type for item in formal_inputs} - set(attempt.role_accepted_types))
            if attempt.role_accepted_types else []
        )
        if rejected:
            finished = self.store.finish_attempt_failure(
                attempt.id,
                reason=f"Role {attempt.role} cannot consume: {', '.join(rejected)}",
            )
            return AttemptRuntimeResult(finished)
        captured_work = self.store.work_items(attempt.work_item_ids)
        evidence_ids = dict.fromkeys(
            artifact_id
            for item in captured_work
            for artifact_id in item.evidence_artifact_ids
        )
        evidence = [self._artifact(artifact_id) for artifact_id in evidence_ids]
        failure_attempts = tuple(
            self.store.get_attempt(attempt_id) for attempt_id in dict.fromkeys(
                attempt_id for item in captured_work for attempt_id in item.evidence_attempt_ids
            )
        )
        inputs = list(dict.fromkeys(
            artifact.id for artifact in [*formal_inputs, *evidence]
        ))
        materialized_inputs = [self._artifact(artifact_id) for artifact_id in inputs]
        site = self.store.recoverable_site(task.id)
        resume_commit = (
            site.workspace_commit
            if site and site.attempt_id != attempt.id else ""
        )
        resume_session = (
            site.session_id if site and site.attempt_id != attempt.id else ""
        )
        workspace = None
        result = None
        try:
            if resume_commit and site:
                attempt = self.store.record_attempt_diagnostics(attempt.id, {
                    "resume_site": {
                        "attempt_id": site.attempt_id, "workspace_commit": resume_commit,
                        "base_commit": site.base_commit,
                        "modified_path_count": len(site.modified_paths),
                        "modified_paths_sample": list(site.modified_paths[:32]),
                    },
                })
            workspace = self.workspaces.create(
                attempt.id, materialized_inputs, workflow_baseline=workflow_baseline,
                resume_commit=resume_commit,
                resume_base_commit=site.base_commit if resume_commit and site else "",
                resume_modified_paths=(site.modified_paths if resume_commit and site else None),
                context_only_artifact_ids=frozenset(evidence_ids).difference(
                    artifact.id for artifact in formal_inputs
                ),
                failure_attempts=failure_attempts,
                evidence_read_paths=attempt.permission.read_paths,
            )
            attempt = self.store.record_attempt_diagnostics(attempt.id, {
                "workspace_base_commit": workspace.base_commit,
                "runner_state": "executing",
            })
            workspace.preserve_on_error(attempt.permission.write_paths)
            with workspace:
                if attempt.role in {"project-constraints-author", "failure-triager"}:
                    resource_context = {"inventory": installed_platform_inventory()}
                    for artifact in formal_inputs:
                        if artifact.type != "specification.bundle":
                            continue
                        source_id = str(artifact.payload.get("source_artifact_id", ""))
                        if source_id:
                            if source_id not in artifact.input_artifact_ids:
                                raise ValueError("bundle source context has no captured input lineage")
                            source = self._artifact(source_id)
                            if source.type != "specification.source":
                                raise ValueError("bundle source context is not specification.source")
                            resource_context["source"] = {
                                "artifact_id": source.id, "digest": source.digest,
                                "payload": dict(source.payload),
                            }
                    attempt = self.store.record_attempt_diagnostics(
                        attempt.id, {"resource_context": resource_context},
                    )
                prompt = self._prompt(attempt, task)
                self._write_attempt_context(
                    workspace.root, attempt, captured_work,
                )
                manifest = TaskManifest(
                    task_id=task.id,
                    feature_id=task.workflow_id,
                    stage=task.key,
                    assigned_agent=attempt.role,
                    context=TaskContext(description=attempt.brief.objective),
                    completion_criteria=list(attempt.brief.completion_criteria),
                    iteration=attempt.ordinal,
                    max_iterations=task.max_attempts,
                    pipeline="taskgraph-v2",
                    description=attempt.brief.objective,
                    framework=attempt.framework,
                    relevant_skills=list(attempt.role_skills),
                    timeout=attempt.timeout_seconds,
                    run_id=attempt.id,
                    model=attempt.model,
                    reasoning_effort=attempt.reasoning_effort,
                    write_paths=list(attempt.permission.write_paths),
                    read_paths=list(attempt.permission.read_paths),
                    allowed_tools=list(attempt.permission.tools),
                    reuse_session=True,
                    session_id=resume_session,
                    prompt_override=prompt,
                )
                control = timeout_control_path(
                    self.project_root / ".chip_nebula", attempt.id,
                )
                initialize_timeout_control(
                    control, run_id=attempt.id, base_timeout=manifest.timeout,
                )
                manifest.timeout_control_path = str(control)
                if attempt.executor == TaskExecutor.TOOL:
                    execution = DeterministicToolExecutor().execute(
                        workspace.root,
                        [ToolCommand(
                            name=task.key, command=attempt.command,
                            timeout=attempt.timeout_seconds,
                        )],
                    )
                    result = AgentResult(
                        success=(execution.status == "succeeded"),
                        execution_log=execution.log,
                        error="" if execution.status == "succeeded" else (
                            execution.commands[-1].reason if execution.commands else execution.status
                        ),
                    )
                else:
                    result = self.dispatcher.dispatch(
                        manifest, workspace.root, project_root=self.project_root,
                    )
                session_reusable = _session_reached_terminal_response(
                    result.execution_log,
                )
                if not result.success or _ERROR_CLASS.search(result.execution_log or ""):
                    reason = result.error or "Agent reported an execution failure"
                    return self._fail(
                        attempt, workspace, reason=reason,
                        session_id=result.session_id,
                        diagnostics={
                            "execution_log": result.execution_log,
                            "session_reusable": session_reusable,
                        },
                    )
                changed = [
                    path for path in detect_changed_paths(
                        workspace.root,
                        ignored_write_paths=attempt.permission.write_paths,
                    )
                    if not path.startswith((".chip_nebula/", ".nebula_inputs/", ".codex/", ".claude/"))
                    and is_publishable_path(path)
                ]
                invalid = violations(changed, attempt.permission.write_paths)
                if invalid:
                    return self._fail(
                        attempt, workspace,
                        reason=f"scope violation: {', '.join(invalid)}",
                        session_id=result.session_id,
                        diagnostics={
                            "changed_paths": changed,
                            "session_reusable": session_reusable,
                        },
                    )
                (
                    gate_reports,
                    retry_failures,
                    pause_failures,
                    report_failures,
                ) = self._run_gates(
                    task.hard_gates, workspace.root,
                )
                if pause_failures:
                    reason = "; ".join(item["evidence"] for item in pause_failures)
                    return self._fail(
                        attempt, workspace,
                        reason=reason,
                        session_id=result.session_id,
                        diagnostics={
                            "gate_reports": gate_reports,
                            "session_reusable": session_reusable,
                        },
                        pause_reason=f"Gate requested operator review: {reason}",
                    )
                if retry_failures:
                    return self._fail(
                        attempt, workspace,
                        reason="; ".join(item["evidence"] for item in retry_failures),
                        session_id=result.session_id,
                        diagnostics={
                            "gate_reports": gate_reports,
                            "session_reusable": session_reusable,
                        },
                    )
                payloads, output_contract_report = self._run_output_contract_gate(
                    task, attempt, materialized_inputs, workspace, changed,
                    result.execution_log,
                )
                gate_reports.append(output_contract_report)
                if not output_contract_report["passed"]:
                    return self._fail(
                        attempt, workspace,
                        reason=output_contract_report["evidence"],
                        session_id=result.session_id,
                        diagnostics={
                            "execution_log": result.execution_log,
                            "gate_reports": gate_reports,
                            "session_reusable": session_reusable,
                        },
                    )
                verdict = _delivery_verdict(
                    payloads, task.outputs, self.schema_registry,
                    bool(report_failures),
                )
                failed_deliverables = [
                    declaration.name
                    for declaration in task.outputs
                    if not declaration.artifact_type.endswith(".report")
                    and _payload_declares_nonpassing_verdict(
                        payloads[declaration.name]
                    )
                ]
                if failed_deliverables:
                    return self._fail(
                        attempt, workspace,
                        reason=(
                            "non-report deliverable declared a non-passing engineering "
                            f"verdict: {', '.join(failed_deliverables)}"
                        ),
                        session_id=result.session_id,
                        diagnostics={
                            "execution_log": result.execution_log,
                            "gate_reports": gate_reports,
                            "session_reusable": session_reusable,
                        },
                    )
                artifacts, commit = self._publish_candidates(
                    task, attempt, materialized_inputs, payloads, workspace,
                )
                requests = StaticWorkHandler(
                    self.store, task.workflow_id, self.feedback_routes,
                ).requests_for_verdict(
                    event_id=attempt.id,
                    source_task_id=task.id,
                    verdict=verdict,
                    payloads=payloads,
                    evidence_artifact_ids=tuple(item.id for item in artifacts),
                    evidence_attempt_ids=tuple(dict.fromkeys(
                        item_id for item in captured_work for item_id in item.evidence_attempt_ids
                    )),
                    causal_correlation_keys=tuple(dict.fromkeys(
                        key
                        for item in captured_work
                        for key in (
                            item.correlation_key, *item.causal_correlation_keys,
                        )
                        if key and key != "initial"
                    )),
                )
                # Pin every Git-backed candidate before it becomes an
                # authoritative Delivery.  A failed DB transaction may leave
                # an unreferenced candidate ref, which is harmless; the
                # inverse ordering could publish an Artifact whose commit is
                # immediately eligible for Git GC.
                for artifact in artifacts:
                    if artifact.content.commit:
                        workspace.preserve(artifact.id, artifact.content.commit)
                finished = self.store.finish_attempt_success(
                    attempt.id,
                    {declaration.name: artifact for declaration, artifact in zip(task.outputs, artifacts)},
                    verdict=verdict,
                    session_id=result.session_id,
                    workspace_commit=commit,
                    work_event_id=f"delivery:{attempt.id}" if requests else "",
                    work_requests=requests,
                    diagnostics={
                        "execution_log": result.execution_log,
                        "gate_reports": gate_reports,
                        "changed_paths": changed,
                        "session_reusable": session_reusable,
                    },
                )
                projection_errors: list[str] = []
                if any(
                    artifact.type in {
                        "design.specification", "specification.bundle",
                        "requirements.review.report", "specification.csir",
                        "implementation.constraints", "acceptance.plan",
                    }
                    for artifact in artifacts
                ):
                    # Immutable Artifacts are authoritative.  This projection
                    # keeps the existing desktop editors in sync without
                    # staging the user's branch or creating compatibility
                    # Artifacts in the legacy store.
                    from .specification_flow import project_output

                    for artifact in artifacts:
                        try:
                            project_output(self.project_root, artifact)
                        except Exception as exc:  # projection is a UI cache
                            projection_errors.append(f"{artifact.id}: {exc}")
                if projection_errors:
                    finished = self.store.record_attempt_diagnostics(
                        attempt.id,
                        {"projection_errors": projection_errors},
                    )
                return AttemptRuntimeResult(finished, tuple(artifacts))
        except Exception as exc:
            active = self.store.active_attempt(attempt.task_id)
            if active and active.id == attempt.id:
                finished = self.store.finish_attempt_failure(
                    attempt.id, reason=f"runtime error: {exc}",
                    session_id=(result.session_id if result is not None else ""),
                    workspace_commit=(
                        workspace.preserved_wip_commit if workspace is not None else ""
                    ),
                    diagnostics={
                        "changed_paths": list(
                            workspace.preserved_wip_paths
                            if workspace is not None else ()
                        ),
                        "session_reusable": bool(
                            result is not None
                            and _session_reached_terminal_response(
                                result.execution_log,
                            )
                        ),
                    },
                )
                return AttemptRuntimeResult(finished)
            raise

    def _prompt(self, attempt: Attempt, task: Task) -> str:
        output_contract = {}
        for item in task.outputs:
            schema = self.schema_registry.get(item.artifact_type, item.schema_version)
            output_contract[item.name] = {
                "type": item.artifact_type,
                "schema_version": item.schema_version,
                "required_payload_fields": sorted(schema.required_fields) if schema else [],
                "required_payload_types": {
                    name: [
                        choice.__name__
                        for choice in (
                            expected if isinstance(expected, tuple) else (expected,)
                        )
                    ]
                    for name, expected in (schema.required_fields.items() if schema else ())
                },
                "field_descriptions": dict(schema.field_descriptions) if schema else {},
                "validation_notes": list(schema.validation_notes) if schema else [],
            }
        return (
            AttemptContextAssembler(self.store).build(attempt)
            + (
                "\n\n# Platform-provided resource facts\n"
                "The following captured inventory and original source are read-only facts, "
                "not new user decisions. Unavailable resources remain unavailable; "
                "do not substitute defaults or relax the frozen specification.\n"
                + json.dumps(attempt.diagnostics["resource_context"], ensure_ascii=False, indent=2)
                if "resource_context" in attempt.diagnostics else ""
            )
            + "\n\n# Frozen exit gates\n"
            + json.dumps([gate.__dict__ for gate in task.hard_gates], ensure_ascii=False, indent=2)
            + (
                "\n\n# EDA result summary v1 contract\n"
                "Use exactly this schema and metric catalog; preflight with the frozen Gate command. "
                "Extra details belong in separate evidence files. Extensions use custom.* IDs.\n"
                + json.dumps(summary_contract(), ensure_ascii=False, indent=2)
                if any(
                    gate.kind == "tool_check" and any(marker in str(gate.parameters.get("command", ""))
                                                     for marker in ("--result-summary-check", "chip_nebula.taskgraph.result_summary"))
                    for gate in task.hard_gates
                ) else ""
            )
            + "\n\n# Output protocol\n"
            + "Return exactly one final `NEBULA_OUTPUT: {...}` object mapping every declared "
              "output name to its structured payload. For Git-backed outputs, the platform "
              "injects `commit` and `paths` after committing the authorized write scope; "
              "provide every other required field. Reports must include their honest "
              "engineering verdict. Every payload field must use exactly the listed JSON "
              "type; for example a field typed `str` must be a JSON string, never an "
              "object carrying extra details.\n"
            + json.dumps(output_contract, ensure_ascii=False, indent=2)
            + "\nEnd with TASK COMPLETED. Use Error-Class only when execution itself cannot complete."
        )

    @staticmethod
    def _write_attempt_context(workspace: Path, attempt: Attempt, work_items) -> None:
        """Expose captured work to deterministic Tool Tasks as immutable JSON.

        Agent Tasks receive the same facts through their assembled prompt.
        Tool Tasks cannot read a prompt, so they get a platform-owned file
        under the already-ignored ``.nebula_inputs`` namespace.  It is context,
        never a publishable project output.
        """
        target = workspace / ".nebula_inputs/attempt-context.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({
            "attempt_id": attempt.id,
            "task_id": attempt.task_id,
            "input_deliveries": dict(attempt.input_deliveries),
            "work_items": [
                {
                    "id": item.id,
                    "kind": item.kind.value,
                    "status": item.status.value,
                    "request_key": item.request_key,
                    "correlation_key": item.correlation_key,
                    "summary": item.summary,
                    "source_task_id": item.source_task_id,
                    "evidence_artifact_ids": list(item.evidence_artifact_ids),
                    "evidence_attempt_ids": list(item.evidence_attempt_ids),
                }
                for item in work_items
            ],
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    def _run_gates(
        self, gates: tuple[GateSpec, ...], workspace: Path,
    ) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
        reports: list[dict] = []
        retry_failures: list[dict] = []
        pause_failures: list[dict] = []
        report_failures: list[dict] = []
        fields = set(ExitCriterion.__dataclass_fields__)
        for gate in gates:
            values = {"type": gate.kind, "on_failure": gate.on_failure, **dict(gate.parameters)}
            unknown = sorted(set(values) - fields)
            if unknown:
                raise ValueError(f"Gate {gate.name} has unsupported parameters: {unknown}")
            result = ExitGate.check([ExitCriterion(**values)], workspace)
            report = result.reports[0]
            document = {
                "name": gate.name, "kind": gate.kind, "passed": report.passed,
                "evidence": report.evidence, "suggestion": report.suggestion,
                "details": report.details, "checked_at": report.checked_at,
                "on_failure": gate.on_failure,
            }
            reports.append(document)
            if not report.passed:
                if gate.on_failure in {"feedback", "report"}:
                    report_failures.append(document)
                elif gate.on_failure == "pause":
                    pause_failures.append(document)
                else:
                    retry_failures.append(document)
        return reports, retry_failures, pause_failures, report_failures

    def _run_output_contract_gate(
        self, task: Task, attempt: Attempt, inputs: list[Artifact], workspace,
        changed_paths: list[str], execution_log: str,
    ) -> tuple[dict[str, dict], dict]:
        """Validate Agent-declared Artifact payloads before publishing files.

        Git ``commit`` and ``paths`` are platform-owned facts, so the Gate
        derives prospective values for schema validation.  Publication still
        recomputes both values after the authorized commit.  Keeping this
        check ahead of ``workspace.commit`` turns malformed NEBULA_OUTPUT into
        ordinary Gate feedback that the same Agent session can repair instead
        of a late runtime exception after a large EDA snapshot is committed.
        """
        report = {
            "name": "artifact-output-contract",
            "kind": "artifact_schema",
            "passed": False,
            "evidence": "",
            "suggestion": (
                "Rewrite the final NEBULA_OUTPUT payload to match the declared "
                "Artifact schema; preserve valid workspace results."
            ),
            "details": {},
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "on_failure": "retry",
        }
        try:
            payloads = parse_output_payloads(execution_log)
            expected = {item.name for item in task.outputs}
            if set(payloads) != expected:
                raise ValueError(
                    "NEBULA_OUTPUT mismatch; "
                    f"expected={sorted(expected)}, received={sorted(payloads)}"
                )
            validated: list[str] = []
            for declaration in task.outputs:
                declared = enrich_prepare_payload(
                    declaration.artifact_type,
                    payloads[declaration.name],
                    inputs,
                    workspace.root,
                )
                git_backed = (
                    declaration.artifact_type in _GIT_TYPES
                    or bool(declaration.paths)
                )
                if git_backed:
                    scopes = declaration.paths or attempt.permission.write_paths
                    prospective_paths = set(workspace.tracked_paths(scopes))
                    prospective_paths.update(
                        path for path in changed_paths
                        if is_path_in_write_scope(path, scopes)
                        and (workspace.root / path).is_file()
                    )
                    declared["commit"] = workspace.base_commit or "pending-platform-commit"
                    declared["paths"] = sorted(prospective_paths)
                if declaration.artifact_type == "rtl.snapshot" and not any(
                    path.lower().endswith((".v", ".sv", ".vhd", ".vhdl"))
                    for path in declared.get("paths", ())
                ):
                    raise ValueError("rtl.snapshot contains no synthesizable HDL source")
                self.schema_registry.validate(
                    declaration.artifact_type,
                    declaration.schema_version,
                    declared,
                )
                validated.append(
                    f"{declaration.name}:{declaration.artifact_type}"
                    f"@{declaration.schema_version}"
                )
            report.update(
                passed=True,
                evidence="Artifact output contract passed",
                suggestion="",
                details={"validated_outputs": validated},
            )
            return payloads, report
        except Exception as exc:
            report.update(
                evidence=f"Artifact output contract Gate failed: {exc}",
                details={"error": str(exc)},
            )
            return {}, report

    def _publish_candidates(
        self, task: Task, attempt: Attempt, inputs: list[Artifact],
        payloads: Mapping[str, dict], workspace,
    ) -> tuple[list[Artifact], str]:
        expected = {item.name for item in task.outputs}
        if set(payloads) != expected:
            raise ValueError(
                f"NEBULA_OUTPUT mismatch; expected={sorted(expected)}, received={sorted(payloads)}"
            )
        changed = detect_changed_paths(
            workspace.root, ignored_write_paths=attempt.permission.write_paths,
        )
        publish_scopes = tuple(dict.fromkeys(
            scope
            for declaration in task.outputs
            for scope in (
                declaration.paths
                or (
                    attempt.permission.write_paths
                    if declaration.artifact_type in _GIT_TYPES else ()
                )
            )
        ))
        commit = ""
        tree = ""
        if changed:
            commit, tree = workspace.commit(
                publish_scopes,
                f"[nebula] {task.key} attempt {attempt.ordinal}",
            )
        elif workspace.base_commit:
            commit = workspace.base_commit
        result: list[Artifact] = []
        for declaration in task.outputs:
            declared = enrich_prepare_payload(
                declaration.artifact_type,
                payloads[declaration.name],
                inputs,
                workspace.root,
            )
            git_backed = (
                declaration.artifact_type in _GIT_TYPES
                or bool(declaration.paths)
            )
            # A delivery may intentionally package immutable read-side inputs
            # together with newly authored files (an integrated RTL snapshot
            # is the common case). Output membership is therefore its own
            # explicit contract, not an alias for the Task's write grant.
            artifact_paths = tuple(sorted(
                workspace.tracked_paths(
                    declaration.paths or attempt.permission.write_paths,
                )
            ))
            content = ArtifactContent(
                kind="git" if git_backed else "inline",
                commit=commit if git_backed else "",
                tree=tree if git_backed else "",
                paths=artifact_paths if git_backed and commit else (),
            )
            if git_backed:
                # Commit and path membership are platform facts. Never accept
                # an Agent-supplied stale commit or a selectively omitted path
                # list as the immutable Artifact envelope.
                declared["commit"] = commit
                declared["paths"] = list(artifact_paths)
            if declaration.artifact_type == "rtl.snapshot" and not any(
                path.lower().endswith((".v", ".sv", ".vhd", ".vhdl"))
                for path in artifact_paths
            ):
                raise ValueError("rtl.snapshot contains no synthesizable HDL source")
            self.schema_registry.validate(
                declaration.artifact_type, declaration.schema_version, declared,
            )
            result.append(Artifact(
                id=f"artifact-{uuid.uuid4().hex}",
                type=declaration.artifact_type,
                schema_version=declaration.schema_version,
                producer=ArtifactProducer(
                    workflow_id=task.workflow_id, task_id=task.id,
                    attempt_id=attempt.id, role=attempt.role,
                    role_version=attempt.role_version,
                ),
                content=content,
                payload=declared,
                input_artifact_ids=tuple(item.id for item in inputs),
                metadata={
                    "workflow_id": task.workflow_id,
                    "task_key": task.key,
                },
            ))
        return result, commit

    def _fail(
        self, attempt: Attempt, workspace, *, reason: str,
        session_id: str, diagnostics: Mapping, pause_reason: str = "",
    ) -> AttemptRuntimeResult:
        changed = [
            path for path in detect_changed_paths(
                workspace.root,
                ignored_write_paths=attempt.permission.write_paths,
            )
            if not path.startswith(
                (".chip_nebula/", ".nebula_inputs/", ".codex/", ".claude/")
            )
            and is_path_in_write_scope(path, attempt.permission.write_paths)
            and is_publishable_path(path)
        ]
        wip = preserve_attempt_wip(workspace, attempt.permission.write_paths)
        finished = self.store.finish_attempt_failure(
            attempt.id, reason=reason, session_id=session_id,
            workspace_commit=wip,
            diagnostics={**dict(diagnostics), "changed_paths": changed},
            pause_reason=pause_reason,
        )
        return AttemptRuntimeResult(finished)

    def _artifact(self, artifact_id: str) -> Artifact:
        artifact = self.store.get_artifact(artifact_id)
        if artifact is None:
            raise FileNotFoundError(f"missing input Artifact: {artifact_id}")
        return artifact


def _session_reached_terminal_response(execution_log: str) -> bool:
    """Only resume sessions whose previous turn produced the output protocol.

    A process can expose a session id before its first turn has completed.  If
    that process is interrupted or hangs, resuming the half-open turn can hang
    every later Attempt as well.  Git WIP remains recoverable independently;
    the conversation is reusable only after the Agent reached its terminal
    output boundary.
    """
    return bool(_OUTPUT.search(execution_log or ""))


def parse_output_payloads(execution_log: str) -> dict[str, dict]:
    matches = list(_OUTPUT.finditer(execution_log or ""))
    if not matches:
        raise ValueError("Agent returned no NEBULA_OUTPUT object")
    remainder = (execution_log or "")[matches[-1].end():].lstrip()
    fence = re.match(r"```(?:json)?\s*", remainder, re.IGNORECASE)
    if fence:
        remainder = remainder[fence.end():]
    try:
        value, _ = json.JSONDecoder().raw_decode(remainder)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid NEBULA_OUTPUT: {exc}") from exc
    if not isinstance(value, dict) or any(not isinstance(item, dict) for item in value.values()):
        raise ValueError("NEBULA_OUTPUT must map output names to objects")
    return value


def _delivery_verdict(
    payloads: Mapping[str, dict], outputs: tuple[OutputSpec, ...],
    schema_registry: ArtifactSchemaRegistry,
    gate_failed: bool,
) -> str:
    verdict_outputs = {
        output.name
        for output in outputs
        if (
            (schema := schema_registry.get(output.artifact_type, output.schema_version))
            is not None and schema.carries_engineering_verdict
        )
    }
    values = {
        str(payload.get("verdict", "")).strip().lower()
        for name, payload in payloads.items()
        if name in verdict_outputs
        if payload.get("verdict") is not None
    }
    if gate_failed:
        return "fail"
    if not values:
        return "pass"
    passing = {"pass", "passed", "success", "succeeded", "ready"}
    # A verdict is an explicit engineering claim. Unknown or mixed verdicts
    # are never silently upgraded to pass.
    return "pass" if values <= passing else "fail"


def _payload_declares_nonpassing_verdict(payload: Mapping[str, object]) -> bool:
    # Report schemas use ``verdict``.  Git-backed engineering deliverables may
    # also refuse publication explicitly when an Agent discovers that the
    # requested repair conflicts with frozen inputs.  Treat those explicit
    # aliases identically: execution success must never upgrade an engineering
    # failure into an authoritative Delivery.
    declared = [
        payload[name]
        for name in ("verdict", "engineering_verdict", "delivery_verdict")
        if payload.get(name) is not None
    ]
    if not declared:
        return False
    passing = {
        "pass", "passed", "success", "succeeded", "ready",
    }
    return any(str(raw).strip().lower() not in passing for raw in declared)

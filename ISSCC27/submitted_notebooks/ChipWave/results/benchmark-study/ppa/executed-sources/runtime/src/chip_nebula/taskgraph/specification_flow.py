"""Static PREPARE workflow and deterministic specification tools.

The Recipe owns a finite Task set.  Review failures, Compiler diagnostics,
human answers and direct amendments become WorkItems on those Tasks; this
module contains no runtime Task construction or replacement logic.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml

from .domain import (
    Artifact,
    ArtifactContent,
    ArtifactProducer,
    TaskState,
    WorkItemKind,
)
from .specir import (
    run_check,
    run_signoff,
    specir_revision_id,
)
from .prepare_contracts import REQUIREMENT_STATUSES as STATUSES, ledger_without_status
from .static_cli import database_path
from .static_recipe import (
    StaticRecipeCompiler,
    load_project_static_roles,
    load_static_recipe,
)
from .static_store import StaticTaskGraphStore


RECIPE_NAME = "specification-baseline-preparation"
RECIPE_PATH = (
    Path(__file__).parents[1] / "configs" / "recipes" / f"{RECIPE_NAME}.yaml"
)
AUTHOR_PATHS = (
    "spec/requirements.ledger.json",
    "spec/design_doc.md",
    "spec/draft.specir",
    "spec/provenance.json",
    "spec/contracts.json",
    "spec/questions.json",
)


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def input_documents(root: Path) -> dict[str, dict]:
    result: dict[str, dict] = {}
    context_path = root / ".nebula_inputs/attempt-context.json"
    context = read_json(context_path) if context_path.is_file() else {}
    captured = context.get("input_deliveries")
    if captured is not None:
        if not isinstance(captured, dict) or any(
            not isinstance(value, str) or not value for value in captured.values()
        ):
            raise ValueError("Attempt input_deliveries must bind Artifact IDs")
        paths = [(value, input_file(root, {"id": value}, "artifact.json"))
                 for value in captured.values()]
    else:
        paths = [(None, path) for path in (root / ".nebula_inputs").glob("*/artifact.json")]
    for expected_id, path in paths:
        document = read_json(path)
        if expected_id is not None and (
            not isinstance(document, dict) or document.get("id") != expected_id
        ):
            raise ValueError("Input manifest does not match captured Artifact ID")
        if isinstance(document, dict) and isinstance(document.get("type"), str):
            result[document["type"]] = document
    return result


def input_file(root: Path, artifact: Mapping[str, Any], name: str) -> Path:
    safe = "".join(
        character if character.isalnum() or character in "-_" else "-"
        for character in str(artifact["id"])
    )
    return root / ".nebula_inputs" / safe / name


def ledger_items(root: Path) -> list[dict]:
    path = root / "spec/requirements.ledger.json"
    if not path.is_file():
        return []
    document = read_json(path)
    items = document.get("requirements") if isinstance(document, dict) else None
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise ValueError("ledger must contain a requirements list")
    return items


def questions(root: Path) -> list[dict]:
    path = root / "spec/questions.json"
    if not path.is_file():
        return []
    document = read_json(path)
    if isinstance(document, dict):
        document = document.get("questions", [])
    if not isinstance(document, list) or any(
        not isinstance(item, dict) for item in document
    ):
        raise ValueError("questions.json must contain a question list")
    return [
        item for item in document if str(item.get("status", "open")) == "open"
    ]


def original_ledger(root: Path, inputs: Mapping[str, dict]):
    for artifact_type in (
        "requirements.review.report",
        "specification.bundle",
        "specification.source-analysis",
    ):
        artifact = inputs.get(artifact_type)
        if artifact is None:
            continue
        path = input_file(root, artifact, "spec/requirements.ledger.json")
        if path.is_file():
            return read_json(path)
    return None


def check_gate(root: Path, action: str) -> None:
    inputs = input_documents(root)
    if action == "ledger-shape-gate":
        source = inputs["specification.source"]
        path = root / "spec/requirements.ledger.json"
        if not path.is_file():
            return
        document = read_json(path)
        if (
            document.get("source_artifact_id") != source["id"]
            or document.get("source_digest")
            != source["payload"]["content_digest"]
        ):
            raise ValueError(
                "ledger source identity/digest does not match the immutable source"
            )
        items = ledger_items(root)
        if not items or len({item.get("id") for item in items}) != len(items):
            raise ValueError("ledger needs nonempty, unique requirement IDs")
        for item in items:
            if not all(
                isinstance(item.get(key), str) and item[key]
                for key in ("id", "kind", "text")
            ):
                raise ValueError("ledger entries need id, kind and text")
            if "status" not in item or item["status"] is not None:
                raise ValueError("Author must leave every initial status null")
            evidence = item.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                raise ValueError("ledger entry has no source evidence")
            if any(
                not isinstance(entry, dict)
                or not entry.get("locator")
                or not entry.get("quote")
                for entry in evidence
            ):
                raise ValueError("ledger evidence needs locator and original quote")
        return

    analysis = inputs.get("specification.source-analysis", {}).get("payload", {})
    bundle = inputs.get("specification.bundle", {}).get("payload", {})
    document_kind = bundle.get("document_kind", analysis.get("document_kind"))
    path = root / "spec/requirements.ledger.json"
    if document_kind == "detailed_design" and path.exists():
        raise ValueError("detailed_design must not create a requirements ledger")
    before = original_ledger(root, inputs)
    after = read_json(path) if path.is_file() else None
    if document_kind == "requirements" and (before is None or after is None):
        raise ValueError("requirements ledger is missing")

    if action == "ledger-status-protection":
        old = {
            item["id"]: item.get("status")
            for item in (before or {}).get("requirements", [])
        }
        for item in (after or {}).get("requirements", []):
            if "status" not in item or item["status"] != old.get(item["id"]):
                raise ValueError(
                    f"Author changed reviewer-owned status: {item['id']}"
                )
        return

    report = read_json(root / "spec/requirements.review.json")
    if action == "review-integrity-gate":
        if ledger_without_status(before) != ledger_without_status(after):
            raise ValueError(
                "Reviewer changed fields other than existing ledger statuses"
            )
        verdict = str(report.get("verdict", ""))
        if verdict not in {"passed", "failed", "pass", "fail"}:
            raise ValueError("Reviewer must declare pass/fail")
        if not all(
            isinstance(report.get(key), list)
            for key in ("requirements", "discovered_requirements", "issues")
        ):
            raise ValueError(
                "Review needs requirements, discovered_requirements and issues lists"
            )
        if any(
            item.get("status") not in STATUSES
            for item in (after or {}).get("requirements", [])
        ):
            raise ValueError("Reviewer must fill each ledger status")
        target = str(report.get("repair_target", ""))
        summary = str(report.get("repair_summary", ""))
        if verdict in {"failed", "fail"}:
            if target not in {
                "analyze-source",
                "generate-design-document",
                "generate-csir-draft",
            } or not summary.strip():
                raise ValueError(
                    "failed review needs a valid repair_target and repair_summary"
                )
        elif target or summary:
            raise ValueError("passed review must not request repair work")
        return

    if action == "ledger-closure-gate":
        claims = (after or {}).get("requirements", report.get("requirements", []))
        if not claims or any(
            item.get("status") not in STATUSES - {"unsupported"}
            for item in claims
        ):
            raise ValueError("Unsupported or unreviewed requirements remain")
        if (
            report.get("verdict") not in {"pass", "passed"}
            or report.get("discovered_requirements")
        ):
            raise ValueError("Reviewer failed or found omitted requirements")
        if any(item.get("blocking", True) for item in report.get("issues", [])):
            raise ValueError("Blocking review issues remain")
        return
    raise ValueError(f"unknown specification gate: {action}")


def tool_payload(root: Path, action: str) -> dict:
    inputs = input_documents(root)
    if action == "compiler-check":
        bundle = inputs["specification.bundle"]
        review = inputs["requirements.review.report"]
        if (
            review["payload"]["verdict"] not in {"passed", "pass"}
            or review["payload"]["subject"] != bundle["id"]
        ):
            raise ValueError(
                "Compiler requires a passed review of this exact bundle"
            )
        source = root / "spec/draft.specir"
        if specir_revision_id(source) != bundle["payload"]["revision_digest"]:
            raise ValueError(
                "materialized bundle revision differs from reviewed revision"
            )
        checked = run_check(source)
        if not checked.get("ok"):
            diagnostics = checked.get("diagnostics", [])
            detail = str(checked.get("error") or "").strip()
            if not detail:
                detail = next(
                    (
                        str(item.get("message") or item.get("code") or "").strip()
                        for item in diagnostics
                        if isinstance(item, dict)
                    ),
                    "",
                )
            if checked.get("failure_class") != "source_compile":
                raise ValueError(
                    "Spec Compiler tool execution failed: "
                    + (detail or "unknown compiler failure")
                )
            return {
                "subject": bundle["id"],
                "verdict": "failed",
                "failure_kind": "needs_repair",
                "repair_summary": detail or "CSIR source could not be compiled",
                "spec_revision_id": bundle["payload"]["revision_digest"],
                "diagnostics": diagnostics,
                "questions": questions(root),
                "candidates": [],
                "counts": checked.get("counts", {}),
                "signoff": {},
                "input_digests": [bundle["digest"], review["digest"]],
                "check": checked,
            }
        diagnostics = list(checked.get("diagnostics", []))
        pending = questions(root)
        failure_kind = (
            "needs_decision" if pending or any(
                item.get("severity") in {"error", "warning"}
                for item in diagnostics
            )
            else ""
        )
        signoff: dict[str, Any] = {}
        if not failure_kind:
            signoff = run_signoff(source)
            if not signoff.get("signoff_passed"):
                detail = str(signoff.get("detail") or signoff.get("error") or "").strip()
                raise ValueError(
                    "Spec Compiler signoff tool execution failed after a clean check: "
                    + (detail or "unknown signoff failure")
                )
        candidates = [
            {
                "id": f"compiler:{index}:{item.get('code', 'unknown')}",
                "diagnostic": item,
            }
            for index, item in enumerate(diagnostics)
            if item.get("severity") in {"error", "warning"}
        ]
        candidates.extend(
            {"id": f"question:{item['id']}", "question": item}
            for item in pending
        )
        return {
            "subject": bundle["id"],
            # A completed compiler run is successful even when it truthfully
            # reports semantic diagnostics.  failure_kind gates baseline
            # release and wakes decision consolidation; it is not a failed
            # CSIR delivery verdict.
            "verdict": "passed",
            "failure_kind": failure_kind,
            "repair_summary": "",
            "spec_revision_id": bundle["payload"]["revision_digest"],
            "diagnostics": diagnostics,
            "questions": pending,
            "candidates": candidates,
            "counts": checked.get("counts", {}),
            "signoff": signoff,
            "input_digests": [bundle["digest"], review["digest"]],
            "check": checked,
        }

    if action == "freeze-baseline":
        bundle = inputs["specification.bundle"]
        review = inputs["requirements.review.report"]
        compiler = inputs["spec.compiler.report"]
        result = compiler["payload"]
        if (
            review["payload"]["subject"] != bundle["id"]
            or result["subject"] != bundle["id"]
            or review["payload"]["verdict"] not in {"pass", "passed"}
            or result["verdict"] not in {"pass", "passed"}
            or not result.get("signoff", {}).get("signoff_passed")
            or questions(root)
        ):
            raise ValueError(
                "cannot freeze a mismatched or nonpassing specification revision"
            )
        revision_id = str(bundle["payload"]["revision_digest"])
        return {
            "source_artifact_id": bundle["payload"]["source_artifact_id"],
            "bundle_artifact_id": bundle["id"],
            "review_artifact_id": review["id"],
            "compiler_report_artifact_id": compiler["id"],
            "spec_revision_id": revision_id,
            "spec_digest": _spec_digest(revision_id),
            "status": "ready",
            "input_digests": [
                bundle["digest"], review["digest"], compiler["digest"]
            ],
        }

    if action == "freeze-project-constraints":
        return _freeze_project_constraints(root, inputs)
    if action == "freeze-acceptance-plan":
        return _freeze_acceptance_plan(root, inputs)
    raise ValueError(f"unknown specification tool: {action}")


def _spec_digest(revision_id: str) -> str:
    if not revision_id.startswith("specir:"):
        raise ValueError("invalid signed Compact SpecIR revision id")
    return "sha256:" + revision_id.removeprefix("specir:")


def _frozen_specification_payload(
    root: Path, inputs: Mapping[str, dict], baseline: Mapping[str, Any],
) -> dict[str, Any]:
    bundle = inputs["specification.bundle"]
    revision_id = str(baseline["spec_revision_id"])
    signoff = inputs["spec.compiler.report"]["payload"].get("signoff", {})
    if not isinstance(signoff, dict) or not signoff.get("signoff_passed"):
        raise ValueError("signed specification payload requires passing signoff evidence")
    required = ("draft.specir", "provenance.json", "questions.json")
    if any(not (root / "spec" / name).is_file() for name in required):
        raise ValueError("signed specification bundle is incomplete")
    return {
        "spec_id": "prepared:" + revision_id.removeprefix("specir:")[:20],
        "revision": 1,
        "status": "frozen",
        "spec_digest": _spec_digest(revision_id),
        "document": {
            "format": "compact-specir",
            "source_path": "spec/draft.specir",
            "provenance_path": "spec/provenance.json",
            "contracts_path": (
                "spec/contracts.json"
                if (root / "spec/contracts.json").is_file() else ""
            ),
            "questions_path": "spec/questions.json",
            "revision_id": revision_id,
            "bundle_artifact_id": bundle["id"],
            "signoff": signoff,
        },
    }


def _freeze_project_constraints(
    root: Path, inputs: Mapping[str, dict],
) -> dict:
    from .implementation_constraints import (
        render_sdc,
        validate_implementation_constraints,
    )
    from .platform_inventory import (
        constraint_inventory,
        installed_platform_inventory,
    )

    confirmation = _require_confirmation(root, "project_constraints_confirmation")
    path = root / "physical/chip-nebula/implementation.constraints.json"
    draft = read_json(path)
    document = _confirmed_document(confirmation) or draft
    document = {**document, "status": "frozen"}
    inventory = constraint_inventory(installed_platform_inventory())
    normalized = validate_implementation_constraints(
        document,
        spec_revision_id=str(document.get("spec_revision_id", "")),
        **inventory,
        require_frozen=True,
    )
    if "sdc_sha256" in draft:
        original = validate_implementation_constraints(
            draft, spec_revision_id=str(document.get("spec_revision_id", "")),
            **inventory, require_frozen=False,
        )
        # The immutable draft includes the author's complete, hash-bound SDC.
        sdc = render_sdc(normalized, authored_document=original,
                         authored_sdc=path.with_name("constraints.sdc").read_bytes())
    else:
        sdc = render_sdc(normalized)
    normalized["sdc_path"] = "physical/chip-nebula/constraints.sdc"
    normalized["sdc_digest"] = "sha256:" + hashlib.sha256(sdc.encode("utf-8")).hexdigest()
    path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / normalized["sdc_path"]).write_text(sdc, encoding="utf-8")
    return {
        "spec_digest": str(
            normalized.get("spec_digest")
            or normalized.get("spec_revision_id")
        ),
        "platform": normalized["platform"],
        "corner": normalized["corner"],
        "clocks": normalized["clocks"],
        "io": normalized["io"],
        "power": normalized["power"],
        "status": "frozen",
        "decision_ids": normalized["decision_ids"],
    }


def _freeze_acceptance_plan(root: Path, inputs: Mapping[str, dict]) -> dict:
    from .acceptance_plan import provenance_design_groups, validate_acceptance_plan

    confirmation = _require_confirmation(root, "acceptance_plan_confirmation")
    path = root / "spec/acceptance.plan.yaml"
    document = _confirmed_document(confirmation) or yaml.safe_load(
        path.read_text(encoding="utf-8")
    )
    provenance = read_json(root / "spec/provenance.json")
    normalized = validate_acceptance_plan(
        document,
        known_design_groups=provenance_design_groups(provenance),
        require_complete=True,
    )
    normalized["confirmed"] = True
    if "status" in normalized:
        normalized["status"] = "frozen"
    path.write_text(
        yaml.safe_dump(normalized, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    checks: list[dict] = []
    requirement_ids: list[str] = []
    for category in normalized.get("categories", []):
        for card in category.get("cards", []):
            for item in card.get("items", []):
                checks.append(dict(item))
                for requirement_id in item.get("requirement_ids", []):
                    if requirement_id not in requirement_ids:
                        requirement_ids.append(requirement_id)
    constraints = inputs["implementation.constraints"]["payload"]
    return {
        "spec_digest": str(constraints["spec_digest"]),
        "checks": checks,
        "requirement_ids": requirement_ids,
        "plan": normalized,
    }


def _confirmed_document(answer: str) -> dict[str, Any] | None:
    try:
        value = json.loads(answer)
    except (TypeError, json.JSONDecodeError):
        return None
    document = value.get("document") if isinstance(value, dict) else None
    return dict(document) if isinstance(document, dict) else None


def _require_confirmation(root: Path, presentation: str) -> str:
    path = root / ".nebula_inputs/attempt-context.json"
    if not path.is_file():
        raise ValueError("confirmation context is missing")
    context = read_json(path)
    answers = [
        item for item in context.get("work_items", [])
        if item.get("kind") == "human_answer"
    ]
    if not answers:
        raise ValueError("explicit human confirmation is missing")
    # Page confirmation questions encode their presentation in the resolved
    # question record.  The answer itself may simply be "confirm" or carry a
    # JSON edit envelope; in either case its presence is explicit authority.
    questions_by_correlation = {
        item.get("correlation_key"): item
        for item in context.get("work_items", [])
        if item.get("kind") == "human_question"
    }
    matched_answer = ""
    for answer in answers:
        question = questions_by_correlation.get(answer.get("correlation_key"), {})
        try:
            detail = json.loads(str(question.get("summary", "")))
        except json.JSONDecodeError:
            detail = {}
        if isinstance(detail, dict) and detail.get("presentation") == presentation:
            matched_answer = str(answer.get("summary", ""))
            break
    if not matched_answer:
        raise ValueError(f"human confirmation does not match {presentation}")
    return matched_answer


def internal_command(action: str) -> int:
    try:
        root = Path.cwd()
        if action in {
            "compiler-check",
            "freeze-baseline",
            "freeze-project-constraints",
            "freeze-acceptance-plan",
        }:
            payload = tool_payload(root, action)
            if action == "freeze-baseline":
                outputs = {
                    "baseline": payload,
                    "specification": _frozen_specification_payload(
                        root, input_documents(root), payload,
                    ),
                }
            else:
                output = {
                    "compiler-check": "result",
                    "freeze-project-constraints": "constraints",
                    "freeze-acceptance-plan": "acceptance",
                }[action]
                outputs = {output: payload}
            print(
                "NEBULA_OUTPUT: "
                + json.dumps(outputs, ensure_ascii=False)
            )
        else:
            check_gate(root, action)
            print({
                "ledger-shape-gate": "REQUIREMENTS_LEDGER_SHAPE_PASS",
                "review-integrity-gate": "REQUIREMENTS_REVIEW_INTEGRITY_PASS",
                "ledger-closure-gate": "REQUIREMENTS_LEDGER_CLOSURE_PASS",
                "ledger-status-protection": "LEDGER_STATUS_PROTECTION_PASS",
            }[action])
        return 0
    except Exception as exc:
        print(f"Specification {action} rejected: {exc}")
        return 1


def template_tasks(roles, workflow_id: str, source_id: str):
    """Compile the complete fixed PREPARE Task set for inspection/tests."""
    document = load_static_recipe(RECIPE_PATH.read_text(encoding="utf-8"))
    return StaticRecipeCompiler(roles).compile(
        document,
        workflow_id=workflow_id,
        goal="Prepare a signed project specification and implementation baseline",
        parameters={"source": source_id},
    ).tasks


def start_specification_flow(
    root: Path,
    document_text: str,
    framework: str,
    model: str,
    snapshot: Mapping[str, str],
    run_manager,
) -> dict:
    workflow_id = f"prepare-spec-{uuid.uuid4().hex[:12]}"
    source_id = f"source-{workflow_id}"
    baseline = _clean_spec_baseline(root, str(snapshot["commit"]), source_id)
    source = Artifact(
        id=source_id,
        type="specification.source",
        schema_version=1,
        producer=ArtifactProducer(
            workflow_id=workflow_id,
            task_id=f"{workflow_id}:__input__",
            attempt_id=f"input-{workflow_id}",
            role="human",
            role_version=1,
        ),
        content=ArtifactContent(kind="git", commit=baseline["commit"], tree=baseline["tree"]),
        payload={
            "source_name": "Design Specification input",
            "media_type": "text/plain",
            "content_digest": "sha256:"
            + hashlib.sha256(document_text.encode("utf-8")).hexdigest(),
            "content": document_text,
            "received_at": datetime.now(timezone.utc).isoformat(),
        },
        metadata={"workflow_id": workflow_id, "recipe": RECIPE_NAME},
    )
    database = database_path(root)
    with StaticTaskGraphStore(database) as store:
        store.register_evidence_artifacts((source,))
    memory = root / ".chip_nebula/shared/memory"
    memory.mkdir(parents=True, exist_ok=True)
    pointer = {
        "workflow_id": workflow_id,
        "source_artifact_id": source.id,
        "framework": framework,
        "model": model,
        "baseline": baseline["commit"],
    }
    (memory / "specification_flow.json").write_text(
        json.dumps(pointer, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    run_id = run_manager.start_taskgraph(
        str(RECIPE_PATH), workflow_id, framework, model or None, 1,
        baseline=baseline["commit"], resume=False,
        parameters={"source": source.id},
    )
    pointer["run_id"] = run_id
    (memory / "specification_flow.json").write_text(
        json.dumps(pointer, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"workflow_id": workflow_id, "run_id": run_id, "recipe": RECIPE_NAME}


def _clean_spec_baseline(root: Path, parent: str, source_id: str) -> dict[str, str]:
    descriptor, index_name = tempfile.mkstemp(prefix="chip-nebula-spec-source-")
    os.close(descriptor)
    index = Path(index_name)
    index.unlink()
    environment = {**os.environ, "GIT_INDEX_FILE": str(index)}

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments], cwd=root, env=environment,
            check=True, capture_output=True, text=True,
        ).stdout.strip()

    try:
        git("read-tree", parent)
        paths = git("ls-files", "--", "spec", "physical/chip-nebula").splitlines()
        for offset in range(0, len(paths), 100):
            git("update-index", "--force-remove", "--", *paths[offset:offset + 100])
        tree = git("write-tree")
        environment.update(
            GIT_AUTHOR_NAME="Chip Nebula",
            GIT_AUTHOR_EMAIL="nebula@localhost",
            GIT_COMMITTER_NAME="Chip Nebula",
            GIT_COMMITTER_EMAIL="nebula@localhost",
        )
        commit = git(
            "commit-tree", tree, "-p", parent, "-m",
            f"[nebula] clean PREPARE baseline {source_id}",
        )
        git("update-ref", f"refs/chip-nebula/artifacts/{source_id}", commit)
        return {"commit": commit, "tree": tree}
    finally:
        index.unlink(missing_ok=True)


def _restored_prepare_state(
    store: StaticTaskGraphStore,
    *,
    workflow_id: str,
    pointer: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Project retained PREPARE evidence when its retired Workflow is absent.

    This is intentionally a read-only recovery path.  It follows the IDs in a
    published ``specification.baseline`` to recover one coherent bundle,
    review and compiler result; it does not infer scheduling state from
    Artifact identity and does not recreate Tasks.
    """
    artifacts = store.list_artifacts()
    by_id = {artifact.id: artifact for artifact in artifacts}

    def newest(artifact_type: str, *, preferred_workflow: str = ""):
        candidates = [
            artifact for artifact in artifacts if artifact.type == artifact_type
        ]
        if preferred_workflow:
            preferred = [
                artifact for artifact in candidates
                if artifact.producer.workflow_id == preferred_workflow
                or artifact.metadata.get("workflow_id") == preferred_workflow
            ]
            if preferred:
                candidates = preferred
        return max(
            candidates,
            key=lambda artifact: (artifact.created_at, artifact.id),
            default=None,
        )

    baseline = newest(
        "specification.baseline", preferred_workflow=workflow_id,
    ) or newest("specification.baseline")
    if baseline is None:
        return None

    def referenced(name: str, artifact_type: str):
        artifact_id = str(baseline.payload.get(name, ""))
        artifact = by_id.get(artifact_id)
        if artifact is not None and artifact.type == artifact_type:
            return artifact
        return newest(artifact_type, preferred_workflow=workflow_id)

    bundle = referenced("bundle_artifact_id", "specification.bundle")
    review = referenced("review_artifact_id", "requirements.review.report")
    compiler = referenced("compiler_report_artifact_id", "spec.compiler.report")
    if bundle is None:
        return None

    # Constraints and acceptance are independently human-frozen PREPARE
    # products.  They may have been imported under the stable ``prepare``
    # producer during migration, so select their latest canonical record
    # rather than pretending they belonged to the missing legacy Workflow.
    constraints = newest("implementation.constraints")
    acceptance = newest("acceptance.plan")

    deliveries = {
        "bundle": bundle,
        "review": review,
        "compiler": compiler,
        "baseline": baseline,
        "spec_request": None,
        "constraint_candidates": None,
        "project_request": None,
        "constraints_draft": None,
        "constraints": constraints,
        "acceptance_draft": None,
        "acceptance": acceptance,
    }
    spec_complete = all((bundle, review, compiler, baseline))
    constraint_complete = constraints is not None
    acceptance_complete = acceptance is not None
    completed_steps = {
        "analyze-source": bundle is not None,
        "generate-design-document": bundle is not None,
        "generate-csir-draft": bundle is not None,
        "review-requirements-closure": review is not None,
        "spec-compiler": compiler is not None,
        "consolidate-spec-decisions": spec_complete,
        "freeze-specification-baseline": baseline is not None,
        "propose-project-constraint-decisions": constraint_complete,
        "consolidate-project-decisions": constraint_complete,
        "generate-project-constraints": constraint_complete,
        "freeze-project-constraints": constraint_complete,
        "generate-acceptance-plan": acceptance_complete,
        "freeze-acceptance-plan": acceptance_complete,
    }
    selected = [artifact for artifact in deliveries.values() if artifact]
    return {
        "workflow_id": workflow_id,
        "recipe": RECIPE_NAME,
        "status": "completed" if all((
            spec_complete, constraint_complete, acceptance_complete,
        )) else "paused",
        "framework": str(pointer.get("framework", "")),
        "model": str(pointer.get("model", "")),
        "running": False,
        "tasks": [
            {
                "id": f"{workflow_id}:{step}",
                "role": "",
                "step": step,
                "status": "succeeded" if complete else "waiting",
            }
            for step, complete in completed_steps.items()
        ],
        "baseline_ready": baseline is not None,
        "has_bundle": bundle is not None,
        "compiler_current": compiler is not None,
        "constraints_ready": constraint_complete,
        "constraints_draft_ready": False,
        "acceptance_ready": acceptance_complete,
        "acceptance_draft_ready": False,
        "prepare_complete": all((
            spec_complete, constraint_complete, acceptance_complete,
        )),
        "published_paths": sorted({
            path for artifact in selected for path in artifact.content.paths
        }),
        "consolidation_status": "complete" if spec_complete else "waiting",
        "review_verdict": (
            str(review.payload.get("verdict", "")) if review else ""
        ),
        "pending_decisions": 0,
        "restored_from_artifacts": True,
        "deliveries": {
            name: artifact.document() if artifact is not None else None
            for name, artifact in deliveries.items()
        },
    }


def flow_state(root: Path):
    pointer_path = root / ".chip_nebula/shared/memory/specification_flow.json"
    pointer = read_json(pointer_path) if pointer_path.is_file() else {}
    if not pointer and not database_path(root).is_file():
        return None
    with StaticTaskGraphStore(database_path(root)) as store:
        if not pointer:
            workflow = max(
                (item for item in store.list_workflows()
                 if item.recipe.split("@", 1)[0] in {RECIPE_NAME, "specification-to-gds"}),
                key=lambda item: (item.created_at, item.id), default=None,
            )
            if workflow is None:
                return None
            workflow_id = workflow.id
        else:
            workflow_id = str(pointer["workflow_id"])
        workflow = store.get_workflow(workflow_id)
        if workflow is None:
            # A project upgraded from the retired dynamic executor can retain
            # immutable PREPARE evidence without retaining that executor's
            # mutable Workflow/Task rows.  The pointer is only a launcher hint;
            # it must never hide an already published specification baseline.
            # Recover the read-only page projection from the canonical v2
            # Artifact records.  Starting or amending PREPARE still requires a
            # real static Workflow and therefore remains deliberately separate.
            restored = _restored_prepare_state(
                store, workflow_id=workflow_id, pointer=pointer,
            )
            if restored is not None:
                return restored
            return {
                "workflow_id": workflow_id,
                "recipe": RECIPE_NAME,
                "status": "planning",
                "framework": pointer.get("framework", ""),
                "model": pointer.get("model", ""),
                "running": False,
                "tasks": [],
                "baseline_ready": False,
                "has_bundle": False,
                "compiler_current": False,
                "published_paths": [],
                "consolidation_status": "waiting",
                "review_verdict": "",
                "pending_decisions": 0,
                "constraints_ready": False,
                "constraints_draft_ready": False,
                "acceptance_ready": False,
                "acceptance_draft_ready": False,
                "prepare_complete": False,
                "deliveries": {},
            }
        tasks = store.list_tasks(workflow_id)
        artifacts = [
            item for item in store.list_artifacts()
            if item.producer.workflow_id == workflow_id
            or item.metadata.get("workflow_id") == workflow_id
        ]
        by_key = {task.key: task for task in tasks}

        def delivery(task_key: str, output: str):
            task = by_key.get(task_key)
            if task is None:
                return None
            # Historical evidence is not released while its owner has new work.
            if store.pending_work(task.id) or store.active_attempt(task.id):
                return None
            current = store.deliveries(task.id).get(output)
            return store.get_artifact(current.artifact_id) if current else None

        review = delivery("review-requirements-closure", "review")
        compiler = delivery("spec-compiler", "result")
        baseline = delivery("freeze-specification-baseline", "baseline")
        bundle = delivery("generate-csir-draft", "bundle")
        spec_request = delivery("consolidate-spec-decisions", "request")
        constraint_candidates = delivery(
            "propose-project-constraint-decisions", "candidates",
        )
        project_request = delivery("consolidate-project-decisions", "request")
        constraints = delivery("freeze-project-constraints", "constraints")
        constraints_draft = delivery("generate-project-constraints", "draft")
        acceptance = delivery("freeze-acceptance-plan", "acceptance")
        acceptance_draft = delivery("generate-acceptance-plan", "draft")
        delivered = {
            "bundle": bundle,
            "review": review,
            "compiler": compiler,
            "baseline": baseline,
            "spec_request": spec_request,
            "constraint_candidates": constraint_candidates,
            "project_request": project_request,
            "constraints_draft": constraints_draft,
            "constraints": constraints,
            "acceptance_draft": acceptance_draft,
            "acceptance": acceptance,
        }
        pending_questions = [
            item
            for task in tasks
            for item in store.pending_work(task.id)
            if item.kind == WorkItemKind.HUMAN_QUESTION
        ]
        active = any(store.active_attempt(task.id) for task in tasks)
        ready = any(store.task_state(task.id) == TaskState.READY for task in tasks)
        consolidator = by_key.get("consolidate-spec-decisions")

        def task_status(task) -> str:
            state = store.task_state(task.id)
            status = {
                TaskState.IDLE: "waiting",
                TaskState.WAITING: "waiting",
                TaskState.READY: "ready",
                TaskState.RUNNING: "running",
                TaskState.SATISFIED: "succeeded",
                TaskState.PAUSED: "paused",
            }[state]
            pending = store.pending_work(task.id)
            if any(item.kind == WorkItemKind.HUMAN_QUESTION for item in pending):
                return "awaiting_human"
            attempts = store.list_attempts(task.id)
            if (
                state == TaskState.SATISFIED
                and attempts and attempts[-1].verdict == "fail"
            ):
                return "failed"
            return status

        return {
            "workflow_id": workflow_id,
            "recipe": workflow.recipe.split("@", 1)[0],
            "status": workflow.status.value,
            "framework": str(workflow.metadata.get("framework_override", "")),
            "model": str(workflow.metadata.get("model_override", "")),
            "running": active or ready,
            "tasks": [
                {
                    "id": task.id,
                    "role": task.role,
                    "step": task.key,
                    "status": task_status(task),
                }
                for task in tasks
            ],
            "baseline_ready": baseline is not None,
            "has_bundle": bundle is not None,
            "compiler_current": compiler is not None,
            "constraints_ready": constraints is not None,
            "constraints_draft_ready": constraints_draft is not None,
            "acceptance_ready": acceptance is not None,
            "acceptance_draft_ready": acceptance_draft is not None,
            "prepare_complete": acceptance is not None,
            "published_paths": sorted({
                path for artifact in artifacts for path in artifact.content.paths
            }),
            "consolidation_status": (
                task_status(consolidator)
                if consolidator is not None else "waiting"
            ),
            "review_verdict": str(review.payload.get("verdict", "")) if review else "",
            "pending_decisions": sum(
                item.task_id in {
                    f"{workflow_id}:generate-design-document",
                    f"{workflow_id}:generate-project-constraints",
                } for item in pending_questions
            ),
            "pending_spec_decisions": sum(
                item.task_id == f"{workflow_id}:generate-design-document"
                for item in pending_questions
            ),
            "pending_project_decisions": sum(
                item.task_id == f"{workflow_id}:generate-project-constraints"
                for item in pending_questions
            ),
            "deliveries": {
                name: artifact.document() if artifact is not None else None
                for name, artifact in delivered.items()
            },
        }


def submit_specification_change(root: Path, instruction: str) -> dict:
    instruction = instruction.strip()
    if not instruction:
        raise ValueError("规格变更内容不能为空")
    state = flow_state(root)
    if state is None:
        raise ValueError("当前项目没有内置规格 flow")
    workflow_id = state["workflow_id"]
    with StaticTaskGraphStore(database_path(root)) as store:
        workflow = store.get_workflow(workflow_id)
        if workflow is None:
            raise ValueError("规格 flow 仍在规划，暂不能提交变更")
        task_id = f"{workflow_id}:analyze-source"
        before = store.task_ids(workflow_id)
        item = store.add_work(
            task_id,
            kind=WorkItemKind.CLARIFICATION,
            request_key=f"human-spec-change:{uuid.uuid4().hex}",
            summary=(
                "用户对原规格提交有范围的增量变更。只修改受影响内容，保留其余已验证设计："
                + instruction
            ),
            source_task_id=task_id,
            propagate_to_dependents=True,
        )
        after = store.task_ids(workflow_id)
        if before != after:
            raise RuntimeError("specification amendment changed the frozen Task set")
    return {
        "workflow_id": workflow_id,
        "work_item_id": item.id,
        "created_tasks": [],
        "instance": workflow_resume_contract(root, workflow_id),
    }


def workflow_resume_contract(
    root: Path, workflow_id: str = "",
) -> dict[str, Any] | None:
    """Return the frozen launcher contract for one existing Workflow.

    Resume reloads this contract verbatim; it never replans Tasks or derives
    execution inputs from newer Artifact IDs.
    """
    if not workflow_id:
        state = flow_state(root)
        if state is None:
            return None
        workflow_id = str(state["workflow_id"])
    with StaticTaskGraphStore(database_path(root)) as store:
        workflow = store.get_workflow(workflow_id)
    if workflow is None:
        return None
    metadata = dict(workflow.metadata)
    return {
        "recipe_path": str(metadata.get("recipe_path") or RECIPE_PATH),
        "workflow_id": workflow.id,
        "framework": str(metadata.get("framework_override", "")),
        "model": str(metadata.get("model_override", "")),
        "workers": int(metadata.get("workers", 1) or 1),
        "baseline": str(metadata.get("baseline_commit", "HEAD")),
        "parameters": dict(metadata.get("parameters", {})),
    }


def confirm_prepare_page(
    root: Path, presentation: str, *, answer: str = "confirm",
) -> dict[str, Any]:
    """Resolve the attached page confirmation without creating a Human Task."""
    task_keys = {
        "project_constraints_confirmation": "freeze-project-constraints",
        "acceptance_plan_confirmation": "freeze-acceptance-plan",
    }
    try:
        task_key = task_keys[presentation]
    except KeyError as exc:
        raise ValueError(f"unknown PREPARE confirmation: {presentation}") from exc
    state = flow_state(root)
    if state is None:
        raise ValueError("current project has no static PREPARE Workflow")
    workflow_id = str(state["workflow_id"])
    task_id = f"{workflow_id}:{task_key}"
    with StaticTaskGraphStore(database_path(root)) as store:
        question_state = store.human_question_state(task_id)
        matching = [
            item for item in question_state["items"]
            if item.get("presentation") == presentation
        ]
        if not matching:
            raise ValueError(f"no pending {presentation} confirmation")
        created = store.answer_human_questions(
            f"page-confirm:{presentation}:{uuid.uuid4().hex}",
            {str(item["id"]): answer for item in matching},
        )
        after = store.task_ids(workflow_id)
    return {
        "workflow_id": workflow_id,
        "task_id": task_id,
        "answer_work_item_ids": [item.id for item in created],
        "created_tasks": [],
        "task_ids": list(after),
        "instance": workflow_resume_contract(root, workflow_id),
    }


def project_output(root: Path, artifact: Artifact) -> None:
    """Project generated PREPARE files for the existing desktop editors.

    The immutable Git Artifact remains authoritative.  Projection updates only
    declared PREPARE product paths and never stages or commits the user's branch.
    """
    allowed = {
        *AUTHOR_PATHS,
        "spec/requirements.review.json",
        "spec/project_constraints.questions.json",
        "spec/acceptance.plan.yaml",
        "physical/chip-nebula/implementation.constraints.json",
        "physical/chip-nebula/constraints.sdc",
    }
    if artifact.content.kind != "git" or not artifact.content.commit:
        return
    for relative in artifact.content.paths:
        if relative not in allowed:
            continue
        target = root / relative
        if target.is_symlink() or target.parent.is_symlink():
            raise ValueError(f"refusing to project through symlink: {relative}")
        result = subprocess.run(
            ["git", "show", f"{artifact.content.commit}:{relative}"],
            cwd=root, check=True, capture_output=True,
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or target.read_bytes() != result.stdout:
            target.write_bytes(result.stdout)

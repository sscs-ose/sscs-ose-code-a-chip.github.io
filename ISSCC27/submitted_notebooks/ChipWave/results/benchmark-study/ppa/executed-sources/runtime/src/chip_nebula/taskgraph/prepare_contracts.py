"""Deterministic PREPARE Artifact envelope enrichment.

Agents author semantic content.  The platform owns input identity, file
membership and content digests, so those facts are derived from the captured
Attempt workspace immediately before schema validation and publication.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

import yaml

from .acceptance_plan import provenance_design_groups, validate_acceptance_plan
from .domain import Artifact
from .specir import specir_revision_id


REQUIREMENT_STATUSES = {"represented", "contracted", "question", "unsupported"}

def ledger_without_status(document):
    result = copy.deepcopy(document)
    if result is None:
        return None
    if not isinstance(result, dict) or not isinstance(result.get("requirements"), list):
        raise ValueError("ledger must contain a requirements list")
    for item in result["requirements"]:
        if not isinstance(item, dict):
            raise ValueError("ledger requirements must be objects")
        item.pop("status", None)
    return result

def enrich_prepare_payload(
    artifact_type: str,
    declared: Mapping[str, object],
    inputs: Sequence[Artifact],
    workspace: Path,
) -> dict:
    payload = dict(declared)
    by_type: dict[str, Artifact] = {}
    for item in inputs:
        # Runtime supplies captured formal inputs before read-only feedback ancestry.
        by_type.setdefault(item.type, item)

    if artifact_type == "specification.source-analysis":
        source = _required(by_type, "specification.source")
        kind = str(payload.get("document_kind", ""))
        if kind not in {"requirements", "detailed_design"}:
            raise ValueError(
                "source analysis document_kind must be requirements or detailed_design"
            )
        ledger = workspace / "spec/requirements.ledger.json"
        if kind == "requirements" and not ledger.is_file():
            raise ValueError("requirements input must publish requirements.ledger.json")
        if kind == "detailed_design" and ledger.exists():
            raise ValueError("detailed-design input must not publish a requirements ledger")
        requirements = _ledger_requirements(ledger) if ledger.is_file() else []
        payload.update(
            source_artifact_id=source.id,
            source_digest=str(source.payload["content_digest"]),
            requirements_ledger_path=(
                "spec/requirements.ledger.json" if ledger.is_file() else ""
            ),
            requirements_ledger_digest=_digest(ledger) if ledger.is_file() else "",
            requirement_count=len(requirements),
        )
        return payload

    if artifact_type == "design.specification":
        source = _required(by_type, "specification.source")
        analysis = _required(by_type, "specification.source-analysis")
        path = workspace / "spec/design_doc.md"
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            raise ValueError("detailed design document is missing or empty")
        ledger = workspace / "spec/requirements.ledger.json"
        payload.update(
            source_artifact_id=source.id,
            source_analysis_artifact_id=analysis.id,
            document_kind=str(analysis.payload["document_kind"]),
            design_document_path="spec/design_doc.md",
            design_digest=_digest(path),
            requirement_ids=[
                str(item["id"]) for item in _ledger_requirements(ledger)
            ] if ledger.is_file() else [],
        )
        payload.setdefault("unresolved_items", [])
        return payload

    if artifact_type == "specification.bundle":
        source = _required(by_type, "specification.source")
        analysis = _required(by_type, "specification.source-analysis")
        design = _required(by_type, "design.specification")
        required = (
            "spec/design_doc.md", "spec/draft.specir",
            "spec/provenance.json", "spec/questions.json",
        )
        for relative in required:
            path = workspace / relative
            if not path.is_file() or not path.read_text(encoding="utf-8").strip():
                raise ValueError(f"specification bundle is missing {relative}")
        for relative in ("spec/provenance.json", "spec/questions.json"):
            json.loads((workspace / relative).read_text(encoding="utf-8"))
        provenance_design_groups(json.loads(
            (workspace / "spec/provenance.json").read_text(encoding="utf-8")
        ))
        optional = (
            "spec/contracts.json", "spec/requirements.ledger.json",
        )
        present = [
            relative for relative in (*required, *optional)
            if (workspace / relative).is_file()
        ]
        payload.update(
            source_artifact_id=source.id,
            source_analysis_artifact_id=analysis.id,
            design_artifact_id=design.id,
            document_kind=str(analysis.payload["document_kind"]),
            revision_digest=specir_revision_id(workspace / "spec/draft.specir"),
            design_document_path="spec/design_doc.md",
            draft_path="spec/draft.specir",
            provenance_path="spec/provenance.json",
            questions_path="spec/questions.json",
            contracts_path=(
                "spec/contracts.json"
                if (workspace / "spec/contracts.json").is_file() else ""
            ),
            requirements_ledger_path=(
                "spec/requirements.ledger.json"
                if (workspace / "spec/requirements.ledger.json").is_file() else ""
            ),
            file_digests={
                relative: _digest(workspace / relative) for relative in present
            },
        )
        return payload

    if artifact_type == "requirements.review.report":
        bundle = _required(by_type, "specification.bundle")
        report_path = workspace / "spec/requirements.review.json"
        if not report_path.is_file():
            raise ValueError("requirements review report file is missing")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if not isinstance(report, dict):
            raise ValueError("requirements review report must be an object")
        report.update(payload)
        report.update(
            subject=bundle.id,
            input_digests=[item.digest for item in inputs],
        )
        return report

    if artifact_type == "implementation.constraints":
        specification = by_type.get("specification.csir")
        baseline = by_type.get("specification.baseline")
        authoritative_digest = ""
        if specification is not None:
            authoritative_digest = str(specification.payload["spec_digest"])
        elif baseline is not None:
            authoritative_digest = str(baseline.payload.get("spec_digest", ""))
        elif "implementation.constraints" in by_type:
            authoritative_digest = str(
                by_type["implementation.constraints"].payload.get("spec_digest", "")
            )
        if not authoritative_digest:
            raise ValueError("implementation constraints have no signed specification digest")
        payload["spec_digest"] = authoritative_digest
        return payload

    if artifact_type == "acceptance.plan":
        specification = by_type.get("specification.csir")
        constraints = by_type.get("implementation.constraints")
        authoritative_digest = (
            str(specification.payload.get("spec_digest", ""))
            if specification is not None else ""
        ) or (
            str(constraints.payload.get("spec_digest", ""))
            if constraints is not None else ""
        )
        if not authoritative_digest:
            raise ValueError("acceptance plan has no signed specification digest")
        path = workspace / "spec/acceptance.plan.yaml"
        if path.is_file():
            provenance = json.loads((workspace / "spec/provenance.json").read_text(encoding="utf-8"))
            requirements = provenance.get("requirements", [])
            validate_acceptance_plan(
                yaml.safe_load(path.read_text(encoding="utf-8")),
                known_requirement_ids={str(item["id"]) for item in requirements},
                required_requirement_ids={str(item["id"]) for item in requirements
                                          if item.get("classification", "normative") == "normative"},
                known_design_groups=provenance_design_groups(provenance),
                require_complete=True,
            )
        payload["spec_digest"] = authoritative_digest
        return payload

    return payload


def _required(by_type: Mapping[str, Artifact], artifact_type: str) -> Artifact:
    try:
        return by_type[artifact_type]
    except KeyError as exc:
        raise ValueError(f"missing {artifact_type} input") from exc


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _ledger_requirements(path: Path) -> list[dict]:
    document = json.loads(path.read_text(encoding="utf-8"))
    requirements = document.get("requirements") if isinstance(document, dict) else None
    if not isinstance(requirements, list) or any(
        not isinstance(item, dict) for item in requirements
    ):
        raise ValueError("requirements ledger must contain an object list")
    return requirements

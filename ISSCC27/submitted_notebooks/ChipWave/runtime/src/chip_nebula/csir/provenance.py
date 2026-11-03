from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .ast import Diagnostic, Program, Severity, Span, iter_nodes

SIDECAR_VERSION = "0.1"
_REQUIREMENT_CLASSIFICATIONS = {
    "normative",
    "objective",
    "assumption",
    "definition",
    "out_of_scope",
}
_REQUIREMENT_STATUSES = {"pending", "mapped", "question", "out_of_scope"}
_MAPPING_KINDS = {"core", "contract", "both", "none"}


@dataclass(frozen=True, slots=True)
class ProvenanceResult:
    data: dict[str, Any]
    diagnostics: tuple[Diagnostic, ...]


def empty_sidecar(program: Program) -> dict[str, Any]:
    statement_nodes: list[dict[str, Any]] = []
    for module in program.modules:
        for item in module.items:
            statement_nodes.append(
                {
                    "node_id": item.node_id,
                    "module": module.name,
                    "requirements": [],
                    "evidence": [],
                    "extraction": None,
                }
            )
    return {
        "schema_version": SIDECAR_VERSION,
        "nodes": statement_nodes,
        "conflicts": [],
    }


def load_sidecar(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("provenance sidecar root must be a JSON object")
    return value


def validate_sidecar(program: Program, data: dict[str, Any]) -> ProvenanceResult:
    diagnostics: list[Diagnostic] = []
    node_by_id = {node.node_id: node for node in iter_nodes(program) if node.node_id}
    fallback_span = program.span
    requirement_entries: dict[str, dict[str, Any]] = {}

    if data.get("schema_version") != SIDECAR_VERSION:
        diagnostics.append(
            Diagnostic(
                code="E-PROV-SCHEMA",
                severity=Severity.ERROR,
                message=(
                    f"provenance schema_version must be {SIDECAR_VERSION!r}, "
                    f"found {data.get('schema_version')!r}"
                ),
                span=fallback_span,
            )
        )

    raw_requirements = data.get("requirements")
    ledger_present = "requirements" in data
    if ledger_present and not isinstance(raw_requirements, list):
        diagnostics.append(
            Diagnostic(
                code="E-PROV-SCHEMA",
                severity=Severity.ERROR,
                message="provenance 'requirements' must be an array",
                span=fallback_span,
            )
        )
        raw_requirements = []
    if isinstance(raw_requirements, list):
        for requirement in raw_requirements:
            if not isinstance(requirement, dict) or not isinstance(
                requirement.get("id"), str
            ) or not requirement["id"]:
                diagnostics.append(
                    Diagnostic(
                        code="E-PROV-SCHEMA",
                        severity=Severity.ERROR,
                        message="each provenance requirement requires a non-empty string id",
                        span=fallback_span,
                    )
                )
                continue
            requirement_id = requirement["id"]
            if requirement_id in requirement_entries:
                diagnostics.append(
                    Diagnostic(
                        code="E-PROV-DUPLICATE-REQUIREMENT",
                        severity=Severity.ERROR,
                        message=f"duplicate provenance requirement {requirement_id!r}",
                        span=fallback_span,
                    )
                )
            requirement_entries[requirement_id] = requirement
            classification = requirement.get("classification")
            status = requirement.get("status")
            mapping_kind = requirement.get("mapping_kind")
            for field, field_value, allowed in (
                ("classification", classification, _REQUIREMENT_CLASSIFICATIONS),
                ("status", status, _REQUIREMENT_STATUSES),
                ("mapping_kind", mapping_kind, _MAPPING_KINDS),
            ):
                if not isinstance(field_value, str) or field_value not in allowed:
                    diagnostics.append(
                        Diagnostic(
                            code="E-PROV-SCHEMA",
                            severity=Severity.ERROR,
                            message=(
                                f"provenance requirement {requirement_id!r} field {field!r} "
                                f"must be one of {sorted(allowed)}, found {field_value!r}"
                            ),
                            span=fallback_span,
                        )
                    )
            for list_field in ("evidence", "mapped_nodes", "mapped_contracts"):
                if list_field in requirement and not isinstance(requirement[list_field], list):
                    diagnostics.append(
                        Diagnostic(
                            code="E-PROV-SCHEMA",
                            severity=Severity.ERROR,
                            message=(
                                f"provenance requirement {requirement_id!r} field "
                                f"{list_field!r} must be an array"
                            ),
                            span=fallback_span,
                        )
                    )
            mapped_nodes = requirement.get("mapped_nodes", [])
            mapped_contracts = requirement.get("mapped_contracts", [])
            if (
                status == "mapped"
                and isinstance(mapped_nodes, list)
                and isinstance(mapped_contracts, list)
            ):
                mapping_is_incomplete = (
                    mapping_kind == "none"
                    or not (mapped_nodes or mapped_contracts)
                    or (mapping_kind in {"core", "both"} and not mapped_nodes)
                    or (mapping_kind in {"contract", "both"} and not mapped_contracts)
                )
                if mapping_is_incomplete:
                    diagnostics.append(
                        Diagnostic(
                            code="E-PROV-MAPPING-INCOMPLETE",
                            severity=Severity.ERROR,
                            message=(
                                f"mapped requirement {requirement_id!r} is inconsistent with "
                                f"mapping_kind {mapping_kind!r} and its node/contract mappings"
                            ),
                            span=fallback_span,
                        )
                    )
            if status == "out_of_scope" and (
                mapping_kind != "none"
                or (isinstance(mapped_nodes, list) and mapped_nodes)
                or (isinstance(mapped_contracts, list) and mapped_contracts)
            ):
                diagnostics.append(
                    Diagnostic(
                        code="E-PROV-MAPPING-INCOMPLETE",
                        severity=Severity.ERROR,
                        message=(
                            f"out-of-scope requirement {requirement_id!r} must use "
                            "mapping_kind 'none' and have no semantic mappings"
                        ),
                        span=fallback_span,
                    )
                )
            if isinstance(mapped_nodes, list):
                for node_id in mapped_nodes:
                    if not isinstance(node_id, str) or node_id not in node_by_id:
                        diagnostics.append(
                            Diagnostic(
                                code="E-PROV-STALE-NODE",
                                severity=Severity.ERROR,
                                message=(
                                    f"requirement {requirement_id!r} references unknown or "
                                    f"stale semantic node {node_id!r}"
                                ),
                                span=fallback_span,
                                node_id=node_id if isinstance(node_id, str) else None,
                            )
                        )

    nodes = data.get("nodes", [])
    if not isinstance(nodes, list):
        diagnostics.append(
            Diagnostic(
                code="E-PROV-SCHEMA",
                severity=Severity.ERROR,
                message="provenance 'nodes' must be an array",
                span=fallback_span,
            )
        )
        nodes = []

    seen: set[str] = set()
    node_entries: dict[str, dict[str, Any]] = {}
    for entry in nodes:
        if not isinstance(entry, dict) or not isinstance(entry.get("node_id"), str):
            diagnostics.append(
                Diagnostic(
                    code="E-PROV-SCHEMA",
                    severity=Severity.ERROR,
                    message="each provenance node entry requires a string node_id",
                    span=fallback_span,
                )
            )
            continue
        node_id = entry["node_id"]
        if node_id in seen:
            diagnostics.append(
                Diagnostic(
                    code="E-PROV-DUPLICATE",
                    severity=Severity.ERROR,
                    message=f"duplicate provenance entry for node {node_id}",
                    span=node_by_id.get(node_id, program).span,
                    node_id=node_id,
                )
            )
        seen.add(node_id)
        node_entries[node_id] = entry
        if node_id not in node_by_id:
            diagnostics.append(
                Diagnostic(
                    code="E-PROV-STALE-NODE",
                    severity=Severity.ERROR,
                    message=f"provenance references unknown or stale semantic node {node_id}",
                    span=fallback_span,
                    node_id=node_id,
                )
            )
        for list_field in ("requirements", "evidence"):
            if not isinstance(entry.get(list_field, []), list):
                diagnostics.append(
                    Diagnostic(
                        code="E-PROV-SCHEMA",
                        severity=Severity.ERROR,
                        message=f"provenance node {node_id} field '{list_field}' must be an array",
                        span=node_by_id.get(node_id, program).span,
                        node_id=node_id,
                    )
                )
        entry_requirements = entry.get("requirements", [])
        if ledger_present and isinstance(entry_requirements, list):
            for requirement_id in entry_requirements:
                if requirement_id not in requirement_entries:
                    diagnostics.append(
                        Diagnostic(
                            code="E-PROV-REQUIREMENT-UNKNOWN",
                            severity=Severity.ERROR,
                            message=(
                                f"provenance node {node_id} references unknown requirement "
                                f"{requirement_id!r}"
                            ),
                            span=node_by_id.get(node_id, program).span,
                            node_id=node_id,
                        )
                    )

    if ledger_present:
        for requirement_id, requirement in requirement_entries.items():
            mapped_nodes = requirement.get("mapped_nodes", [])
            if not isinstance(mapped_nodes, list):
                continue
            for node_id in mapped_nodes:
                if not isinstance(node_id, str) or node_id not in node_by_id:
                    continue
                entry = node_entries.get(node_id)
                if entry is None or requirement_id not in entry.get("requirements", []):
                    diagnostics.append(
                        Diagnostic(
                            code="E-PROV-BACKLINK-MISSING",
                            severity=Severity.ERROR,
                            message=(
                                f"requirement {requirement_id!r} maps node {node_id}, but the "
                                "node entry does not map back"
                            ),
                            span=node_by_id[node_id].span,
                            node_id=node_id,
                        )
                    )
        for node_id, entry in node_entries.items():
            entry_requirements = entry.get("requirements", [])
            if not isinstance(entry_requirements, list):
                continue
            for requirement_id in entry_requirements:
                requirement = requirement_entries.get(requirement_id)
                if requirement is None:
                    continue
                if node_id not in requirement.get("mapped_nodes", []):
                    diagnostics.append(
                        Diagnostic(
                            code="E-PROV-BACKLINK-MISSING",
                            severity=Severity.ERROR,
                            message=(
                                f"node {node_id} maps requirement {requirement_id!r}, but the "
                                "requirement entry does not map back"
                            ),
                            span=node_by_id.get(node_id, program).span,
                            node_id=node_id,
                        )
                    )

    conflicts = data.get("conflicts", [])
    if not isinstance(conflicts, list):
        diagnostics.append(
            Diagnostic(
                code="E-PROV-SCHEMA",
                severity=Severity.ERROR,
                message="provenance 'conflicts' must be an array",
                span=fallback_span,
            )
        )
        conflicts = []
    for conflict in conflicts:
        if not isinstance(conflict, dict):
            diagnostics.append(
                Diagnostic(
                    code="E-PROV-SCHEMA",
                    severity=Severity.ERROR,
                    message="each conflict must be an object",
                    span=fallback_span,
                )
            )
            continue
        if conflict.get("status", "open") != "resolved":
            conflict_id = conflict.get("id", "<unnamed>")
            raw_node_id = conflict.get("node_id")
            node_id = raw_node_id if isinstance(raw_node_id, str) else None
            span: Span = node_by_id.get(node_id, program).span if node_id else program.span
            candidates = conflict.get("candidates", [])
            notes = tuple(
                f"candidate: {candidate.get('value')!r} <- {candidate.get('requirements', [])}"
                for candidate in candidates
                if isinstance(candidate, dict)
            )
            diagnostics.append(
                Diagnostic(
                    code="E-CONFLICT-UNRESOLVED",
                    severity=Severity.ERROR,
                    message=f"unresolved extraction conflict {conflict_id}",
                    span=span,
                    node_id=node_id,
                    notes=notes,
                )
            )
    return ProvenanceResult(data=data, diagnostics=tuple(diagnostics))


def dump_sidecar(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

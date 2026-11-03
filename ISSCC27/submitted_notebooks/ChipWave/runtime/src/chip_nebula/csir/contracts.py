from __future__ import annotations

import json
import math
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .ast import (
    ContractApply,
    ContractBinding,
    Diagnostic,
    NameExpr,
    Node,
    Program,
    Severity,
    Span,
)
from .semantics import CheckResult, TypeInfo

CONTRACT_SCHEMA_VERSION = "0.1"
_VERIFICATION_STATUSES = {"adapter_required", "executable", "manual"}
_ROLE_MODES = {"observe", "constrain"}
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


@dataclass(frozen=True, slots=True)
class ContractResult:
    data: dict[str, Any]
    diagnostics: tuple[Diagnostic, ...]


def load_contracts(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("contract sidecar root must be a JSON object")
    return value


def dump_contracts(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _parse_contract_type(
    value: Any,
    *,
    contract_id: str,
    role: str,
    emit: Callable[[str, Severity, str, Node | None], None],
) -> TypeInfo | None:
    prefix = f"contract {contract_id!r} interface role {role!r}"
    if not isinstance(value, dict):
        emit(
            "E-CONTRACT-SCHEMA",
            Severity.ERROR,
            f"{prefix} requires a structured type object",
            None,
        )
        return None
    kind = value.get("kind")
    if kind == "bit":
        return TypeInfo("bit", 1)
    if kind in {"bits", "uint", "sint"}:
        width = value.get("width")
        if not isinstance(width, int) or isinstance(width, bool) or width <= 0:
            emit(
                "E-CONTRACT-SCHEMA",
                Severity.ERROR,
                f"{prefix} requires a positive integer width",
                None,
            )
            return None
        return TypeInfo(kind, width)
    if kind == "enum":
        members = value.get("members")
        if (
            not isinstance(members, list)
            or not members
            or not all(isinstance(member, str) and member for member in members)
            or len(set(members)) != len(members)
        ):
            emit(
                "E-CONTRACT-SCHEMA",
                Severity.ERROR,
                f"{prefix} requires unique, non-empty enum members",
                None,
            )
            return None
        return TypeInfo(
            "enum",
            max(1, math.ceil(math.log2(max(2, len(members))))),
            tuple(members),
        )
    emit(
        "E-CONTRACT-SCHEMA",
        Severity.ERROR,
        f"{prefix} has unsupported runtime type kind {kind!r}",
        None,
    )
    return None


def validate_contracts(
    program: Program,
    result: CheckResult,
    data: dict[str, Any] | None,
    *,
    requirement_ids: set[str] | None = None,
    requirement_contracts: dict[str, set[str]] | None = None,
    adapter_base: Path | None = None,
    source_name: str | None = None,
) -> ContractResult:
    value = (
        data
        if data is not None
        else {"schema_version": CONTRACT_SCHEMA_VERSION, "contracts": []}
    )
    diagnostics: list[Diagnostic] = []
    covered_abstracts: set[str] = set()
    interfaces: dict[str, dict[str, tuple[str, TypeInfo | None]]] = {}
    definition_ids: set[str] = set()
    definition_requirements: dict[str, set[str]] = {}

    def emit(
        code: str,
        severity: Severity,
        message: str,
        node: Node | None = None,
    ) -> None:
        diagnostics.append(
            Diagnostic(
                code=code,
                severity=severity,
                message=message,
                span=(
                    node.span
                    if node is not None
                    else Span(line=1, column=1, end_line=1, end_column=2)
                ),
                node_id=node.node_id or None if node is not None else None,
                source_name=None if node is not None else source_name,
            )
        )

    if value.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        emit(
            "E-CONTRACT-SCHEMA",
            Severity.ERROR,
            "contract schema_version must be "
            f"{CONTRACT_SCHEMA_VERSION!r}, found {value.get('schema_version')!r}",
        )

    contracts = value.get("contracts", [])
    if not isinstance(contracts, list):
        emit("E-CONTRACT-SCHEMA", Severity.ERROR, "contract 'contracts' must be an array")
        contracts = []

    if contracts and requirement_ids is None:
        emit(
            "E-CONTRACT-REQUIREMENT-UNCHECKED",
            Severity.ERROR,
            "contracts require a provenance sidecar with a requirement ledger",
        )

    for contract in contracts:
        if not isinstance(contract, dict):
            emit("E-CONTRACT-SCHEMA", Severity.ERROR, "each contract must be an object")
            continue

        contract_id = contract.get("id")
        if not isinstance(contract_id, str) or not contract_id:
            emit("E-CONTRACT-SCHEMA", Severity.ERROR, "each contract requires a non-empty id")
            contract_id = "<unnamed>"
        elif _IDENTIFIER.fullmatch(contract_id) is None:
            emit(
                "E-CONTRACT-SCHEMA",
                Severity.ERROR,
                f"contract id {contract_id!r} must be a Compact SpecIR identifier",
            )
        elif contract_id in definition_ids:
            emit(
                "E-CONTRACT-DUPLICATE",
                Severity.ERROR,
                f"duplicate contract id {contract_id!r}",
            )
        definition_ids.add(contract_id)

        requirements = contract.get("requirements")
        if not isinstance(requirements, list) or not requirements or not all(
            isinstance(item, str) and item for item in requirements
        ):
            emit(
                "E-CONTRACT-SCHEMA",
                Severity.ERROR,
                f"contract {contract_id!r} requires a non-empty string requirements array",
            )
        elif requirement_ids is not None:
            for requirement_id in requirements:
                if requirement_id not in requirement_ids:
                    emit(
                        "E-CONTRACT-REQUIREMENT-UNKNOWN",
                        Severity.ERROR,
                        f"contract {contract_id!r} references unknown requirement "
                        f"{requirement_id!r}",
                    )
        definition_requirements[contract_id] = (
            {item for item in requirements if isinstance(item, str)}
            if isinstance(requirements, list)
            else set()
        )

        evidence = contract.get("evidence")
        if not isinstance(evidence, list) or not evidence or not all(
            isinstance(item, str) and item for item in evidence
        ):
            emit(
                "E-CONTRACT-SCHEMA",
                Severity.ERROR,
                f"contract {contract_id!r} requires a non-empty string evidence array",
            )

        semantics = contract.get("semantics")
        if not isinstance(semantics, dict):
            emit(
                "E-CONTRACT-SCHEMA",
                Severity.ERROR,
                f"contract {contract_id!r} requires a semantics object",
            )
        else:
            language = semantics.get("language")
            body = semantics.get("body")
            if not isinstance(language, str) or not language:
                emit(
                    "E-CONTRACT-SCHEMA",
                    Severity.ERROR,
                    f"contract {contract_id!r} semantics requires a language",
                )
            if not isinstance(body, str | list | dict) or not body:
                emit(
                    "E-CONTRACT-SCHEMA",
                    Severity.ERROR,
                    f"contract {contract_id!r} semantics requires a non-empty body",
                )

        raw_interface = contract.get("interface")
        parsed_interface: dict[str, tuple[str, TypeInfo | None]] = {}
        if not isinstance(raw_interface, dict):
            emit(
                "E-CONTRACT-SCHEMA",
                Severity.ERROR,
                f"contract {contract_id!r} requires an interface object; "
                "legacy untyped targets are not sufficient",
            )
        else:
            for role, role_spec in raw_interface.items():
                if not isinstance(role, str) or _IDENTIFIER.fullmatch(role) is None:
                    emit(
                        "E-CONTRACT-SCHEMA",
                        Severity.ERROR,
                        f"contract {contract_id!r} interface role {role!r} must be an identifier",
                    )
                    continue
                if not isinstance(role_spec, dict):
                    emit(
                        "E-CONTRACT-SCHEMA",
                        Severity.ERROR,
                        f"contract {contract_id!r} interface role {role!r} must be an object",
                    )
                    continue
                mode = role_spec.get("mode")
                if mode not in _ROLE_MODES:
                    emit(
                        "E-CONTRACT-SCHEMA",
                        Severity.ERROR,
                        f"contract {contract_id!r} interface role {role!r} mode must be "
                        f"one of {sorted(_ROLE_MODES)}",
                    )
                    mode = "observe"
                parsed_interface[role] = (
                    mode,
                    _parse_contract_type(
                        role_spec.get("type"),
                        contract_id=contract_id,
                        role=role,
                        emit=emit,
                    ),
                )
        interfaces[contract_id] = parsed_interface

        verification = contract.get("verification")
        if not isinstance(verification, dict):
            emit(
                "E-CONTRACT-SCHEMA",
                Severity.ERROR,
                f"contract {contract_id!r} requires a verification object",
            )
            continue
        status = verification.get("status")
        backend = verification.get("backend")
        adapter = verification.get("adapter")
        if status not in _VERIFICATION_STATUSES:
            emit(
                "E-CONTRACT-SCHEMA",
                Severity.ERROR,
                f"contract {contract_id!r} verification status must be one of "
                f"{sorted(_VERIFICATION_STATUSES)}",
            )
        if not isinstance(backend, str) or not backend:
            emit(
                "E-CONTRACT-SCHEMA",
                Severity.ERROR,
                f"contract {contract_id!r} verification requires a backend",
            )
        if status == "executable":
            if not isinstance(adapter, str) or not adapter:
                emit(
                    "E-CONTRACT-ADAPTER-MISSING",
                    Severity.ERROR,
                    f"executable contract {contract_id!r} requires an adapter path",
                )
            else:
                declared_adapter_path = Path(adapter)
                adapter_path: Path | None = declared_adapter_path
                if not declared_adapter_path.is_absolute():
                    if adapter_base is None:
                        emit(
                            "E-CONTRACT-ADAPTER-UNRESOLVED",
                            Severity.ERROR,
                            f"cannot resolve relative adapter {adapter!r} for executable "
                            f"contract {contract_id!r} without the contract sidecar directory",
                        )
                        adapter_path = None
                    else:
                        adapter_path = adapter_base / declared_adapter_path
                if adapter_path is not None and (
                    not adapter_path.is_file() or not os.access(adapter_path, os.R_OK)
                ):
                    emit(
                        "E-CONTRACT-ADAPTER-UNRESOLVED",
                        Severity.ERROR,
                        f"adapter {adapter!r} for executable contract {contract_id!r} "
                        "is not a readable file",
                    )
        elif status == "adapter_required":
            emit(
                "N-CONTRACT-ADAPTER-REQUIRED",
                Severity.NOTE,
                f"contract {contract_id!r} is specified but needs a verification adapter",
            )
        elif status == "manual":
            emit(
                "N-CONTRACT-MANUAL",
                Severity.NOTE,
                f"contract {contract_id!r} is specified for manual/external verification",
            )

    applied_ids: set[str] = set()
    for module in program.modules:
        module_symbols = result.symbols.get(module.name, {})
        for application in (
            item for item in module.items if isinstance(item, ContractApply)
        ):
            contract_id = application.contract_id
            interface = interfaces.get(contract_id)
            if interface is None:
                emit(
                    "E-CONTRACT-APPLICATION-UNKNOWN",
                    Severity.ERROR,
                    f"application references undefined contract {contract_id!r}",
                    application,
                )
                continue
            applied_ids.add(contract_id)
            bindings: dict[str, ContractBinding] = {}
            for binding in application.bindings:
                if binding.role in bindings:
                    emit(
                        "E-CONTRACT-BINDING-DUPLICATE",
                        Severity.ERROR,
                        f"contract {contract_id!r} role {binding.role!r} is bound more than once",
                        binding,
                    )
                else:
                    bindings[binding.role] = binding
            for role in sorted(interface.keys() - bindings.keys()):
                emit(
                    "E-CONTRACT-BINDING-MISSING",
                    Severity.ERROR,
                    f"contract {contract_id!r} application is missing role {role!r}",
                    application,
                )
            for role in sorted(bindings.keys() - interface.keys()):
                emit(
                    "E-CONTRACT-BINDING-UNKNOWN",
                    Severity.ERROR,
                    f"contract {contract_id!r} application binds unknown role {role!r}",
                    bindings[role],
                )
            for role in sorted(interface.keys() & bindings.keys()):
                binding = bindings[role]
                mode, expected_type = interface[role]
                actual_type = result.expression_types.get(id(binding.value))
                if (
                    expected_type is not None
                    and actual_type is not None
                    and actual_type != expected_type
                ):
                    emit(
                        "E-CONTRACT-BINDING-TYPE",
                        Severity.ERROR,
                        f"contract {contract_id!r} role {role!r} has type "
                        f"{actual_type.describe()}, expected {expected_type.describe()}",
                        binding,
                    )
                if mode == "constrain" and isinstance(binding.value, NameExpr):
                    # Coverage is deliberately syntactic in v0.1.  Merely mentioning
                    # an abstract inside a derived expression does not prove that the
                    # contract limits that abstract (for example, y ^ y is constant).
                    # A constrain role must bind the abstract symbol itself; operands
                    # and context belong in separate observe roles.
                    symbol = module_symbols.get(binding.value.name)
                    if symbol is not None and symbol.is_abstract:
                        covered_abstracts.add(f"{module.name}.{binding.value.name}")

    for contract_id in sorted(definition_ids - applied_ids):
        emit(
            "E-CONTRACT-UNAPPLIED",
            Severity.ERROR,
            f"contract {contract_id!r} has no application in Compact SpecIR",
        )

    if requirement_contracts is not None:
        for requirement_id, mapped_contracts in requirement_contracts.items():
            for contract_id in mapped_contracts:
                if contract_id not in definition_ids:
                    emit(
                        "E-CONTRACT-PROVENANCE-MISMATCH",
                        Severity.ERROR,
                        f"requirement {requirement_id!r} maps undefined contract "
                        f"{contract_id!r}",
                    )
                elif requirement_id not in definition_requirements.get(contract_id, set()):
                    emit(
                        "E-CONTRACT-PROVENANCE-MISMATCH",
                        Severity.ERROR,
                        f"requirement {requirement_id!r} maps contract {contract_id!r}, "
                        "but the contract does not map back",
                    )
        for contract_id, requirements in definition_requirements.items():
            for requirement_id in requirements:
                if contract_id not in requirement_contracts.get(requirement_id, set()):
                    emit(
                        "E-CONTRACT-PROVENANCE-MISMATCH",
                        Severity.ERROR,
                        f"contract {contract_id!r} maps requirement {requirement_id!r}, "
                        "but the requirement does not map back",
                    )

    for abstract_name in result.abstract_symbols:
        if abstract_name in covered_abstracts:
            continue
        module_name, symbol_name = abstract_name.split(".", 1)
        symbol = result.symbols[module_name][symbol_name]
        emit(
            "E-ABSTRACT-UNCONSTRAINED",
            Severity.ERROR,
            f"abstract symbol {abstract_name!r} is not bound to a constrain contract role",
            symbol.node,
        )

    diagnostics.sort(
        key=lambda item: (
            item.source_name or program.source_name,
            item.span.line,
            item.span.column,
            item.code,
            item.message,
        )
    )
    return ContractResult(value, tuple(diagnostics))

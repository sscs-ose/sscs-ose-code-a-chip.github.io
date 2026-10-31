from __future__ import annotations

from typing import Any

from .ast import (
    AbstractDecl,
    ContractApply,
    Equation,
    Expr,
    HoleExpr,
    Program,
    iter_nodes,
    semantic_dict,
)
from .semantics import CheckResult, TypeInfo, semantics_fingerprint


def type_to_dict(type_info: TypeInfo) -> dict[str, Any]:
    value: dict[str, Any] = {"kind": type_info.kind}
    if type_info.width is not None:
        value["width"] = type_info.width
    if type_info.members:
        value["members"] = list(type_info.members)
    return value


def elaborate(program: Program, result: CheckResult) -> dict[str, Any]:
    """Build a deterministic semantic projection separate from the source AST."""
    modules: list[dict[str, Any]] = []
    node_types: dict[str, dict[str, Any]] = {}
    holes: list[dict[str, Any]] = []
    abstracts: list[dict[str, Any]] = []

    for node in iter_nodes(program):
        if isinstance(node, Expr):
            type_info = result.expression_types.get(id(node))
            if type_info is not None:
                node_types[node.node_id] = type_to_dict(type_info)
        if isinstance(node, HoleExpr):
            holes.append({"node_id": node.node_id, "name": node.name})

    for module in program.modules:
        symbols = result.symbols.get(module.name, {})
        equations: list[dict[str, Any]] = []
        contract_applications: list[dict[str, Any]] = []
        for item in module.items:
            if not isinstance(item, AbstractDecl):
                continue
            for name in item.names:
                symbol = symbols.get(name)
                abstracts.append(
                    {
                        "node_id": item.node_id,
                        "module": module.name,
                        "name": name,
                        "type": type_to_dict(symbol.type_info) if symbol else None,
                        "domain": item.domain,
                        "direction": item.direction,
                    }
                )
        for item in module.items:
            if isinstance(item, ContractApply):
                contract_applications.append(
                    {
                        "node_id": item.node_id,
                        "contract_id": item.contract_id,
                        "bindings": [
                            {
                                "node_id": binding.node_id,
                                "role": binding.role,
                                "value_node_id": binding.value.node_id,
                                "type": (
                                    type_to_dict(result.expression_types[id(binding.value)])
                                    if id(binding.value) in result.expression_types
                                    else None
                                ),
                            }
                            for binding in item.bindings
                        ],
                    }
                )
            if not isinstance(item, Equation):
                continue
            symbol = symbols.get(item.target)
            equations.append(
                {
                    "node_id": item.node_id,
                    "target": item.target,
                    "role": "next" if item.is_next else "comb",
                    "target_type": type_to_dict(symbol.type_info) if symbol else None,
                    "domain": symbol.domain if symbol else None,
                    "value_node_id": item.value.node_id,
                }
            )
        modules.append(
            {
                "node_id": module.node_id,
                "name": module.name,
                "fragment": module.fragment,
                "symbols": [
                    {
                        "name": symbol.name,
                        "type": type_to_dict(symbol.type_info),
                        "domain": symbol.domain,
                        "state": symbol.is_state,
                        "direction": symbol.direction,
                        "abstract": symbol.is_abstract,
                        "enum_value": symbol.enum_value,
                        "declaration_node_id": symbol.node.node_id,
                    }
                    for symbol in symbols.values()
                ],
                "equations": equations,
                "contract_applications": contract_applications,
            }
        )

    return {
        "kind": "ElaboratedProgram",
        "schema_version": "0.1",
        "semantic_sha256": semantics_fingerprint(program),
        "source_semantics": semantic_dict(program),
        "modules": modules,
        "node_types": node_types,
        "holes": holes,
        "abstracts": abstracts,
    }

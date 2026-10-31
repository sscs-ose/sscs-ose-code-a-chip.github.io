from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


@dataclass(frozen=True, slots=True)
class Span:
    line: int
    column: int
    end_line: int
    end_column: int


@dataclass(slots=True, kw_only=True)
class Node:
    span: Span
    node_id: str = ""


@dataclass(slots=True, kw_only=True)
class Expr(Node):
    pass


@dataclass(slots=True, kw_only=True)
class NameExpr(Expr):
    name: str


@dataclass(slots=True, kw_only=True)
class IntExpr(Expr):
    value: int
    raw: str
    width: int | None = None
    base: int = 10


@dataclass(slots=True, kw_only=True)
class HoleExpr(Expr):
    name: str | None


@dataclass(slots=True, kw_only=True)
class NoneExpr(Expr):
    pass


@dataclass(slots=True, kw_only=True)
class HoldExpr(Expr):
    pass


@dataclass(slots=True, kw_only=True)
class UnboundedExpr(Expr):
    pass


@dataclass(slots=True, kw_only=True)
class UnaryExpr(Expr):
    op: str
    operand: Expr


@dataclass(slots=True, kw_only=True)
class BinaryExpr(Expr):
    op: str
    left: Expr
    right: Expr


@dataclass(slots=True, kw_only=True)
class TernaryExpr(Expr):
    condition: Expr
    then_expr: Expr
    else_expr: Expr


@dataclass(slots=True, kw_only=True)
class CallExpr(Expr):
    function: str
    args: list[Expr]


@dataclass(slots=True, kw_only=True)
class IndexExpr(Expr):
    value: Expr
    index: Expr


@dataclass(slots=True, kw_only=True)
class SliceExpr(Expr):
    value: Expr
    msb: Expr
    lsb: Expr


@dataclass(slots=True, kw_only=True)
class ConcatExpr(Expr):
    values: list[Expr]


@dataclass(slots=True, kw_only=True)
class Branch(Node):
    guard: Expr
    value: Expr


@dataclass(slots=True, kw_only=True)
class ChoiceExpr(Expr):
    kind: str
    branches: list[Branch]
    else_expr: Expr | None


@dataclass(slots=True, kw_only=True)
class TemporalUnaryExpr(Expr):
    op: str
    operand: Expr


@dataclass(slots=True, kw_only=True)
class TemporalBinaryExpr(Expr):
    op: str
    left: Expr
    right: Expr


@dataclass(slots=True, kw_only=True)
class DelayExpr(Expr):
    lower: Expr
    upper: Expr
    operand: Expr


@dataclass(slots=True, kw_only=True)
class TypeRef(Node):
    kind: str
    width: Expr | None = None
    members: list[str] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class ResetClause(Node):
    value: Expr


@dataclass(slots=True, kw_only=True)
class ContractBinding(Node):
    role: str
    value: Expr


@dataclass(slots=True, kw_only=True)
class Item(Node):
    pass


@dataclass(slots=True, kw_only=True)
class DomainDecl(Item):
    name: str
    edge: str
    clock: str
    reset_mode: str | None
    reset: Expr | None


@dataclass(slots=True, kw_only=True)
class PortDecl(Item):
    direction: str
    is_state: bool
    names: list[str]
    type_ref: TypeRef
    domain: str | None
    reset: ResetClause | None
    value: Expr | None


@dataclass(slots=True, kw_only=True)
class AbstractDecl(Item):
    names: list[str]
    type_ref: TypeRef
    direction: str | None
    domain: str | None


@dataclass(slots=True, kw_only=True)
class ContractApply(Item):
    contract_id: str
    bindings: list[ContractBinding]


@dataclass(slots=True, kw_only=True)
class StateDecl(Item):
    names: list[str]
    type_ref: TypeRef
    domain: str
    reset: ResetClause | None


@dataclass(slots=True, kw_only=True)
class ConstDecl(Item):
    name: str
    type_ref: TypeRef
    value: Expr


@dataclass(slots=True, kw_only=True)
class ParamDecl(Item):
    name: str
    value: Expr


@dataclass(slots=True, kw_only=True)
class LetDecl(Item):
    name: str
    type_ref: TypeRef | None
    value: Expr


@dataclass(slots=True, kw_only=True)
class Equation(Item):
    target: str
    is_next: bool
    value: Expr


@dataclass(slots=True, kw_only=True)
class PropertyStmt(Item):
    kind: str
    domain: str
    property: Expr
    unless: Expr | None


@dataclass(slots=True, kw_only=True)
class Module(Node):
    name: str
    parameters: list[ParamDecl]
    items: list[Item]
    fragment: bool = False


@dataclass(slots=True, kw_only=True)
class Program(Node):
    modules: list[Module]
    source_name: str = "<input>"


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    span: Span
    node_id: str | None = None
    source_name: str | None = None
    notes: tuple[str, ...] = ()
    witness: dict[str, str] | None = None


def _plain(value: Any, *, include_source: bool = True) -> Any:
    if dataclasses.is_dataclass(value):
        data: dict[str, Any] = {"kind": type(value).__name__}
        for definition in dataclasses.fields(value):
            if not include_source and definition.name in {"span", "node_id", "source_name"}:
                continue
            data[definition.name] = _plain(
                getattr(value, definition.name), include_source=include_source
            )
        return data
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, list):
        return [_plain(item, include_source=include_source) for item in value]
    if isinstance(value, tuple):
        return [_plain(item, include_source=include_source) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _plain(item, include_source=include_source) for key, item in value.items()
        }
    return value


def to_dict(value: Any) -> Any:
    return _plain(value)


def semantic_dict(value: Any) -> Any:
    return _plain(value, include_source=False)


def iter_nodes(value: Any) -> list[Node]:
    nodes: list[Node] = []

    def visit(current: Any) -> None:
        if isinstance(current, Node):
            nodes.append(current)
            for definition in dataclasses.fields(current):
                if definition.name not in {"span", "node_id"}:
                    visit(getattr(current, definition.name))
        elif isinstance(current, list):
            for item in current:
                visit(item)

    visit(value)
    return nodes


def assign_node_ids(program: Program) -> None:
    program_payload = json.dumps(semantic_dict(program), sort_keys=True, separators=(",", ":"))
    program.node_id = "N" + hashlib.sha256(program_payload.encode()).hexdigest()[:16]
    occurrences: dict[str, int] = {}
    for module in program.modules:
        for node in iter_nodes(module):
            payload = json.dumps(semantic_dict(node), sort_keys=True, separators=(",", ":"))
            digest = hashlib.sha256(f"{module.name}\x1f{payload}".encode()).hexdigest()[:16]
            count = occurrences.get(digest, 0)
            occurrences[digest] = count + 1
            suffix = f"-{count + 1}" if count else ""
            node.node_id = f"N{digest}{suffix}"

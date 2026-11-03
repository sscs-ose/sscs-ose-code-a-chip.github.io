from __future__ import annotations

import importlib
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .ast import (
    AbstractDecl,
    BinaryExpr,
    CallExpr,
    ChoiceExpr,
    ConcatExpr,
    ConstDecl,
    ContractApply,
    DelayExpr,
    Diagnostic,
    DomainDecl,
    Equation,
    Expr,
    HoldExpr,
    HoleExpr,
    IndexExpr,
    IntExpr,
    LetDecl,
    Module,
    NameExpr,
    Node,
    NoneExpr,
    ParamDecl,
    PortDecl,
    Program,
    PropertyStmt,
    Severity,
    SliceExpr,
    StateDecl,
    TemporalBinaryExpr,
    TemporalUnaryExpr,
    TernaryExpr,
    TypeRef,
    UnaryExpr,
    UnboundedExpr,
    iter_nodes,
    semantic_dict,
)


@dataclass(frozen=True, slots=True)
class TypeInfo:
    kind: str
    width: int | None = None
    members: tuple[str, ...] = ()

    @property
    def is_hardware(self) -> bool:
        return self.kind in {"bit", "bits", "uint", "sint", "enum"}

    @property
    def is_vector(self) -> bool:
        return self.kind in {"bits", "uint", "sint"}

    def describe(self) -> str:
        if self.kind == "bit":
            return "bit"
        if self.kind == "int":
            return "int"
        if self.kind == "property":
            return "temporal property"
        if self.kind == "enum":
            return "{" + ",".join(self.members) + "}"
        prefix = {"bits": "bits", "uint": "u", "sint": "s"}.get(self.kind, self.kind)
        return f"{prefix}[{self.width}]"


BIT = TypeInfo("bit", 1)
INT = TypeInfo("int")
PROPERTY = TypeInfo("property")


@dataclass(slots=True)
class Symbol:
    name: str
    type_info: TypeInfo
    domain: str | None
    is_state: bool
    direction: str | None
    node: Node
    enum_value: int | None = None
    is_abstract: bool = False


@dataclass(frozen=True, slots=True)
class CheckResult:
    diagnostics: tuple[Diagnostic, ...]
    symbols: dict[str, dict[str, Symbol]]
    expression_types: dict[int, TypeInfo]

    @property
    def has_errors(self) -> bool:
        return any(item.severity == Severity.ERROR for item in self.diagnostics)

    @property
    def has_blocking_diagnostics(self) -> bool:
        return self.has_errors or any(
            item.code == "W-CHOICE-NOT-PROVEN" for item in self.diagnostics
        )

    @property
    def abstract_symbols(self) -> tuple[str, ...]:
        return tuple(
            f"{module_name}.{symbol.name}"
            for module_name, symbols in sorted(self.symbols.items())
            for symbol in symbols.values()
            if symbol.is_abstract
        )


class Checker:
    def __init__(self, program: Program, *, solver: bool = True):
        self.program = program
        self.use_solver = solver
        self.diagnostics: list[Diagnostic] = []
        self._diagnostic_keys: set[tuple[str, int, int, str]] = set()
        self.symbols_by_module: dict[str, dict[str, Symbol]] = {}
        self.expression_types: dict[int, TypeInfo] = {}
        self.params: dict[str, int] = {}
        self.domains: dict[str, DomainDecl] = {}
        self.current_symbols: dict[str, Symbol] = {}
        self.current_module: Module | None = None
        self._single_domain: str | None = None

    def emit(
        self,
        code: str,
        severity: Severity,
        message: str,
        node: Node,
        *,
        notes: tuple[str, ...] = (),
        witness: dict[str, str] | None = None,
    ) -> None:
        key = (code, node.span.line, node.span.column, message)
        if key in self._diagnostic_keys:
            return
        self._diagnostic_keys.add(key)
        self.diagnostics.append(
            Diagnostic(
                code=code,
                severity=severity,
                message=message,
                span=node.span,
                node_id=node.node_id or None,
                notes=notes,
                witness=witness,
            )
        )

    def run(self) -> CheckResult:
        module_names: set[str] = set()
        for module in self.program.modules:
            if module.name in module_names:
                self.emit(
                    "E-NAME-DUPLICATE-MODULE",
                    Severity.ERROR,
                    f"duplicate module declaration '{module.name}'",
                    module,
                )
            module_names.add(module.name)
            self.check_module(module)
        ordered = tuple(
            sorted(
                self.diagnostics,
                key=lambda item: (
                    item.span.line,
                    item.span.column,
                    item.code,
                    item.message,
                ),
            )
        )
        return CheckResult(ordered, self.symbols_by_module, self.expression_types)

    def check_module(self, module: Module) -> None:
        self.current_module = module
        self.current_symbols = {}
        self.params = {}
        self.domains = {}

        for parameter in module.parameters:
            self.declare_param(parameter)
        for item in module.items:
            if isinstance(item, ParamDecl):
                self.declare_param(item)
            elif isinstance(item, DomainDecl):
                if item.name in self.domains:
                    self.emit(
                        "E-NAME-DUPLICATE",
                        Severity.ERROR,
                        f"duplicate domain declaration '{item.name}'",
                        item,
                    )
                else:
                    self.domains[item.name] = item

        self._single_domain = next(iter(self.domains)) if len(self.domains) == 1 else None

        for item in module.items:
            if isinstance(item, AbstractDecl):
                type_info = self.resolve_type(item.type_ref)
                if not type_info.is_hardware:
                    self.emit(
                        "E-TYPE-ABSTRACT-RUNTIME",
                        Severity.ERROR,
                        "abstract runtime values require a hardware type, "
                        f"found {type_info.describe()}",
                        item,
                    )
                for name in item.names:
                    self.declare_symbol(
                        Symbol(
                            name,
                            type_info,
                            item.domain,
                            False,
                            item.direction,
                            item,
                            is_abstract=True,
                        )
                    )
                self.declare_enum_members(type_info, item)
            elif isinstance(item, PortDecl):
                type_info = self.resolve_type(item.type_ref)
                for name in item.names:
                    self.declare_symbol(
                        Symbol(name, type_info, item.domain, item.is_state, item.direction, item)
                    )
                self.declare_enum_members(type_info, item)
            elif isinstance(item, StateDecl):
                type_info = self.resolve_type(item.type_ref)
                for name in item.names:
                    self.declare_symbol(Symbol(name, type_info, item.domain, True, None, item))
                self.declare_enum_members(type_info, item)
            elif isinstance(item, ConstDecl):
                type_info = self.resolve_type(item.type_ref)
                self.declare_symbol(Symbol(item.name, type_info, None, False, None, item))
                self.declare_enum_members(type_info, item)
            elif isinstance(item, LetDecl) and item.type_ref is not None:
                type_info = self.resolve_type(item.type_ref)
                self.declare_symbol(Symbol(item.name, type_info, None, False, None, item))

        for item in module.items:
            if isinstance(item, LetDecl) and item.type_ref is None:
                inferred = self.infer_expr(item.value)
                if inferred is not None:
                    self.declare_symbol(Symbol(item.name, inferred, None, False, None, item))

        self.symbols_by_module[module.name] = self.current_symbols.copy()
        self.check_domains(module)
        self.check_values(module)
        self.check_expression_contexts(module)
        self.check_drivers(module)
        self.check_unused_lets(module)
        self.check_comb_cycles(module)
        self.check_holes(module)
        self.check_temporal_bounds(module)
        self.check_choice_semantics(module)

    def declare_param(self, item: ParamDecl) -> None:
        if item.name in self.params:
            self.emit(
                "E-NAME-DUPLICATE",
                Severity.ERROR,
                f"duplicate parameter declaration '{item.name}'",
                item,
            )
            return
        value = self.eval_const(item.value)
        if value is None:
            self.emit(
                "E-TYPE-CONST",
                Severity.ERROR,
                f"parameter '{item.name}' must have a compile-time integer value",
                item,
            )
            return
        self.params[item.name] = value
        self.declare_symbol(Symbol(item.name, INT, None, False, None, item))

    def declare_symbol(self, symbol: Symbol) -> None:
        previous = self.current_symbols.get(symbol.name)
        if previous is not None:
            self.emit(
                "E-NAME-DUPLICATE",
                Severity.ERROR,
                f"duplicate symbol declaration '{symbol.name}'",
                symbol.node,
                notes=(
                    "previous declaration at "
                    f"{previous.node.span.line}:{previous.node.span.column}",
                ),
            )
            return
        self.current_symbols[symbol.name] = symbol

    def declare_enum_members(self, type_info: TypeInfo, node: Node) -> None:
        if type_info.kind != "enum":
            return
        for index, member in enumerate(type_info.members):
            previous = self.current_symbols.get(member)
            if previous is not None:
                if previous.type_info != type_info or previous.enum_value != index:
                    self.emit(
                        "E-NAME-ENUM-AMBIGUOUS",
                        Severity.ERROR,
                        f"enum member '{member}' is ambiguous in module scope",
                        node,
                    )
                continue
            self.current_symbols[member] = Symbol(
                member,
                type_info,
                None,
                False,
                None,
                node,
                enum_value=index,
            )

    def resolve_type(self, type_ref: TypeRef) -> TypeInfo:
        if type_ref.kind == "bit":
            return BIT
        if type_ref.kind == "int":
            return INT
        if type_ref.kind == "enum":
            if len(set(type_ref.members)) != len(type_ref.members):
                self.emit(
                    "E-TYPE-ENUM-DUPLICATE",
                    Severity.ERROR,
                    "enum type contains duplicate members",
                    type_ref,
                )
            return TypeInfo(
                "enum",
                max(1, math.ceil(math.log2(max(2, len(type_ref.members))))),
                tuple(type_ref.members),
            )
        width = self.eval_const(type_ref.width) if type_ref.width else None
        if width is None:
            self.emit(
                "E-TYPE-WIDTH",
                Severity.ERROR,
                "type width must be a compile-time integer",
                type_ref,
            )
            width = 1
        elif width <= 0:
            self.emit(
                "E-TYPE-WIDTH",
                Severity.ERROR,
                f"type width must be positive, found {width}",
                type_ref,
            )
            width = 1
        return TypeInfo(type_ref.kind, width)

    def eval_const(self, expr: Expr | None) -> int | None:
        if expr is None:
            return None
        if isinstance(expr, IntExpr):
            return expr.value
        if isinstance(expr, NameExpr):
            return self.params.get(expr.name)
        if isinstance(expr, UnaryExpr):
            value = self.eval_const(expr.operand)
            if value is None:
                return None
            if expr.op == "+":
                return value
            if expr.op == "-":
                return -value
            if expr.op == "~":
                return ~value
            return None
        if isinstance(expr, BinaryExpr):
            left = self.eval_const(expr.left)
            right = self.eval_const(expr.right)
            if left is None or right is None:
                return None
            if expr.op == "+":
                return left + right
            if expr.op == "-":
                return left - right
            if expr.op == "*":
                return left * right
            if expr.op == "/":
                return left // right if right else None
            if expr.op == "%":
                return left % right if right else None
            if expr.op == "<<":
                return left << right
            if expr.op == ">>":
                return left >> right
            if expr.op == "&":
                return left & right
            if expr.op == "|":
                return left | right
            if expr.op == "^":
                return left ^ right
            return None
        return None

    def check_domains(self, module: Module) -> None:
        for domain in self.domains.values():
            clock = self.current_symbols.get(domain.clock)
            if clock is None:
                self.emit(
                    "E-NAME-UNDECLARED",
                    Severity.ERROR,
                    f"domain '{domain.name}' references undeclared clock '{domain.clock}'",
                    domain,
                )
            elif clock.type_info != BIT:
                self.emit(
                    "E-DOMAIN-CLOCK-TYPE",
                    Severity.ERROR,
                    f"clock '{domain.clock}' must have type bit",
                    domain,
                )
            if domain.reset is not None:
                reset_type = self.infer_expr(domain.reset, expected=BIT, context_domain=domain.name)
                self.require_type(reset_type, BIT, domain.reset, "domain reset condition")

        for item in module.items:
            if isinstance(item, StateDecl | PropertyStmt) or (
                isinstance(item, PortDecl) and item.domain is not None
            ) or (
                isinstance(item, AbstractDecl) and item.domain is not None
            ):
                assert item.domain is not None
                self.require_domain(item.domain, item)

    def require_domain(self, domain: str, node: Node) -> None:
        if domain not in self.domains:
            self.emit(
                "E-DOMAIN-UNDECLARED",
                Severity.ERROR,
                f"undefined clock/reset domain '{domain}'",
                node,
            )

    def check_values(self, module: Module) -> None:
        for item in module.items:
            if isinstance(item, AbstractDecl):
                continue
            if isinstance(item, PortDecl):
                type_info = self.resolve_type(item.type_ref)
                if item.is_state and item.domain is None:
                    self.emit(
                        "E-DOMAIN-MISSING",
                        Severity.ERROR,
                        f"state output '{item.names[0]}' requires a clock domain",
                        item,
                    )
                self.check_reset(item.reset, type_info, item.domain, item)
                if item.value is not None:
                    if item.direction == "in":
                        self.emit(
                            "E-COMB-INPUT-DRIVER",
                            Severity.ERROR,
                            f"input '{item.names[0]}' cannot have a defining expression",
                            item,
                        )
                    value_type = self.infer_expr(
                        item.value, expected=type_info, context_domain=item.domain
                    )
                    self.require_type(value_type, type_info, item.value, "port definition")
                    self.check_cdc(item.value, item.domain, item)
            elif isinstance(item, StateDecl):
                type_info = self.resolve_type(item.type_ref)
                self.check_reset(item.reset, type_info, item.domain, item)
            elif isinstance(item, ConstDecl):
                type_info = self.current_symbols[item.name].type_info
                value_type = self.infer_expr(item.value, expected=type_info)
                self.require_type(value_type, type_info, item.value, "constant initializer")
            elif isinstance(item, LetDecl):
                expected = self.current_symbols.get(item.name)
                value_type = self.infer_expr(
                    item.value, expected=expected.type_info if expected else None
                )
                if expected:
                    self.require_type(value_type, expected.type_info, item.value, "let expression")
            elif isinstance(item, ContractApply):
                for binding in item.bindings:
                    self.infer_expr(binding.value)
            elif isinstance(item, Equation):
                self.check_equation(item)
            elif isinstance(item, PropertyStmt):
                property_type = self.infer_expr(
                    item.property, context_domain=item.domain, temporal=True
                )
                if property_type not in {BIT, PROPERTY, None}:
                    self.emit(
                        "E-TEMP-TYPE",
                        Severity.ERROR,
                        "property expression must be boolean or temporal",
                        item.property,
                    )
                if item.unless is not None:
                    unless_type = self.infer_expr(
                        item.unless,
                        expected=BIT,
                        context_domain=item.domain,
                    )
                    self.require_type(unless_type, BIT, item.unless, "unless condition")
                self.check_cdc(item.property, item.domain, item)

    def check_reset(
        self,
        reset_clause: Any,
        type_info: TypeInfo,
        domain: str | None,
        owner: Node,
    ) -> None:
        if reset_clause is None:
            if isinstance(owner, StateDecl) or (isinstance(owner, PortDecl) and owner.is_state):
                self.emit(
                    "E-STATE-RESET-OMITTED",
                    Severity.ERROR,
                    "state reset intent is omitted; use 'reset none' or an explicit value/hole",
                    owner,
                )
            return
        value = reset_clause.value
        if isinstance(value, NoneExpr | HoleExpr):
            return
        if domain in self.domains and self.domains[domain].reset is None:
            self.emit(
                "E-DOMAIN-RESET-MISSING",
                Severity.ERROR,
                f"state has a reset value but domain '{domain}' has no reset condition",
                owner,
            )
        value_type = self.infer_expr(value, expected=type_info, context_domain=domain)
        self.require_type(value_type, type_info, value, "state reset value")
        self.check_cdc(value, domain, owner)

    def check_equation(self, equation: Equation) -> None:
        symbol = self.current_symbols.get(equation.target)
        if symbol is None:
            self.emit(
                "E-NAME-UNDECLARED",
                Severity.ERROR,
                f"equation targets undeclared symbol '{equation.target}'",
                equation,
            )
            self.infer_expr(equation.value)
            return
        if equation.is_next and not symbol.is_state:
            self.emit(
                "E-STATE-NEXT-NONSTATE",
                Severity.ERROR,
                f"next-state equation target '{equation.target}' is not state",
                equation,
            )
        if symbol.is_abstract:
            self.emit(
                "E-ABSTRACT-DRIVER",
                Severity.ERROR,
                f"abstract symbol '{equation.target}' cannot also have a defining equation",
                equation,
            )
        if not equation.is_next and symbol.is_state:
            self.emit(
                "E-STATE-COMB-DRIVER",
                Severity.ERROR,
                f"state '{equation.target}' must be driven by a next-state equation",
                equation,
            )
        if symbol.direction == "in":
            self.emit(
                "E-COMB-INPUT-DRIVER",
                Severity.ERROR,
                f"input '{equation.target}' cannot be driven",
                equation,
            )
        value_type = self.infer_expr(
            equation.value,
            expected=symbol.type_info,
            allow_hold=equation.is_next,
            context_domain=self.effective_domain(symbol),
        )
        self.require_type(value_type, symbol.type_info, equation.value, "equation result")
        self.check_cdc(equation.value, self.effective_domain(symbol), equation)

    def infer_expr(
        self,
        expr: Expr,
        *,
        expected: TypeInfo | None = None,
        allow_hold: bool = False,
        context_domain: str | None = None,
        temporal: bool = False,
    ) -> TypeInfo | None:
        result: TypeInfo | None
        if isinstance(expr, NameExpr):
            if expr.name == "reset" and context_domain in self.domains:
                domain = self.domains[context_domain]
                if domain.reset is None:
                    self.emit(
                        "E-DOMAIN-RESET-MISSING",
                        Severity.ERROR,
                        f"domain '{context_domain}' has no declared reset condition",
                        expr,
                    )
                result = BIT
            else:
                symbol = self.current_symbols.get(expr.name)
                if symbol is None:
                    self.emit(
                        "E-NAME-UNDECLARED",
                        Severity.ERROR,
                        f"undeclared symbol '{expr.name}'",
                        expr,
                    )
                    result = None
                else:
                    if symbol.type_info == INT and expected and expected.is_hardware:
                        value = self.eval_const(expr)
                        if (
                            value is not None
                            and expected.width is not None
                            and value >= (1 << expected.width)
                        ):
                            self.emit(
                                "E-TYPE-LITERAL-RANGE",
                                Severity.ERROR,
                                f"constant '{expr.name}' does not fit {expected.describe()}",
                                expr,
                            )
                        result = expected
                    else:
                        result = symbol.type_info
        elif isinstance(expr, IntExpr):
            if expr.width is not None and (expr.width <= 0 or expr.value >= (1 << expr.width)):
                self.emit(
                    "E-TYPE-LITERAL-RANGE",
                    Severity.ERROR,
                    f"literal {expr.raw} does not fit its declared width {expr.width}",
                    expr,
                )
            if expected and expected.is_hardware:
                if expected.kind == "bit" and expr.value not in {0, 1}:
                    self.emit(
                        "E-TYPE-LITERAL-RANGE",
                        Severity.ERROR,
                        f"literal {expr.raw} does not fit type bit",
                        expr,
                    )
                elif expected.width is not None and expr.value >= (1 << expected.width):
                    self.emit(
                        "E-TYPE-LITERAL-RANGE",
                        Severity.ERROR,
                        f"literal {expr.raw} does not fit {expected.describe()}",
                        expr,
                    )
                if (
                    expr.width is not None
                    and expected.width is not None
                    and expr.width != expected.width
                ):
                    self.emit(
                        "E-TYPE-WIDTH-MISMATCH",
                        Severity.ERROR,
                        f"literal width {expr.width} does not match {expected.describe()}",
                        expr,
                    )
                result = expected
            elif expr.width is not None:
                result = TypeInfo("bits", expr.width)
            else:
                result = INT
        elif isinstance(expr, HoleExpr | NoneExpr | HoldExpr):
            result = expected
        elif isinstance(expr, UnboundedExpr):
            result = INT
        elif isinstance(expr, UnaryExpr):
            if expr.op == "!":
                operand = self.infer_expr(
                    expr.operand,
                    expected=BIT,
                    allow_hold=allow_hold,
                    context_domain=context_domain,
                    temporal=temporal,
                )
                self.require_type(operand, BIT, expr.operand, "logical-not operand")
                result = BIT
            else:
                operand = self.infer_expr(
                    expr.operand,
                    expected=expected,
                    allow_hold=allow_hold,
                    context_domain=context_domain,
                    temporal=temporal,
                )
                if operand and expr.op == "~" and operand.kind not in {"bits", "uint", "sint"}:
                    self.emit(
                        "E-TYPE-OPERATOR",
                        Severity.ERROR,
                        "bitwise-not requires a bitvector operand",
                        expr,
                    )
                if (
                    operand
                    and expr.op in {"+", "-"}
                    and operand.kind
                    not in {
                        "uint",
                        "sint",
                        "int",
                    }
                ):
                    self.emit(
                        "E-TYPE-OPERATOR",
                        Severity.ERROR,
                        f"unary {expr.op} requires a numeric operand",
                        expr,
                    )
                result = operand
        elif isinstance(expr, BinaryExpr):
            result = self.infer_binary(
                expr,
                expected=expected,
                allow_hold=allow_hold,
                context_domain=context_domain,
                temporal=temporal,
            )
        elif isinstance(expr, TernaryExpr):
            condition_type = self.infer_expr(
                expr.condition,
                expected=BIT,
                context_domain=context_domain,
                temporal=temporal,
            )
            self.require_type(condition_type, BIT, expr.condition, "conditional guard")
            then_type = self.infer_expr(
                expr.then_expr,
                expected=expected,
                allow_hold=allow_hold,
                context_domain=context_domain,
                temporal=temporal,
            )
            else_type = self.infer_expr(
                expr.else_expr,
                expected=then_type or expected,
                allow_hold=allow_hold,
                context_domain=context_domain,
                temporal=temporal,
            )
            if then_type is None and else_type is not None:
                then_type = self.infer_expr(
                    expr.then_expr,
                    expected=else_type,
                    allow_hold=allow_hold,
                    context_domain=context_domain,
                    temporal=temporal,
                )
            self.require_same(then_type, else_type, expr, "conditional branches")
            result = then_type or else_type or expected
        elif isinstance(expr, CallExpr):
            result = self.infer_call(expr, context_domain=context_domain, temporal=temporal)
        elif isinstance(expr, IndexExpr):
            value_type = self.infer_expr(
                expr.value, context_domain=context_domain, temporal=temporal
            )
            index_type = self.infer_expr(expr.index, temporal=temporal)
            if value_type and not value_type.is_vector:
                self.emit(
                    "E-TYPE-INDEX",
                    Severity.ERROR,
                    "indexing requires a bitvector value",
                    expr.value,
                )
            if index_type not in {INT, None} and not (index_type and index_type.kind == "uint"):
                self.emit(
                    "E-TYPE-INDEX",
                    Severity.ERROR,
                    "index must be an integer or unsigned value",
                    expr.index,
                )
            index_value = self.eval_const(expr.index)
            if (
                index_value is not None
                and value_type is not None
                and value_type.width is not None
                and (index_value < 0 or index_value >= value_type.width)
            ):
                self.emit(
                    "E-TYPE-INDEX",
                    Severity.ERROR,
                    f"index {index_value} is outside width {value_type.width}",
                    expr.index,
                )
            result = BIT
        elif isinstance(expr, SliceExpr):
            value_type = self.infer_expr(
                expr.value, context_domain=context_domain, temporal=temporal
            )
            msb = self.eval_const(expr.msb)
            lsb = self.eval_const(expr.lsb)
            if value_type and not value_type.is_vector:
                self.emit(
                    "E-TYPE-SLICE",
                    Severity.ERROR,
                    "slice requires a bitvector value",
                    expr.value,
                )
            if msb is None or lsb is None or msb < lsb or lsb < 0:
                self.emit(
                    "E-TYPE-SLICE",
                    Severity.ERROR,
                    "slice bounds must be constant and satisfy msb >= lsb >= 0",
                    expr,
                )
                result = None
            else:
                if value_type and value_type.width is not None and msb >= value_type.width:
                    self.emit(
                        "E-TYPE-SLICE",
                        Severity.ERROR,
                        f"slice [{msb}:{lsb}] exceeds width {value_type.width}",
                        expr,
                    )
                result = TypeInfo("bits", msb - lsb + 1)
        elif isinstance(expr, ConcatExpr):
            width = 0
            valid = True
            for concat_item in expr.values:
                item_type = self.infer_expr(
                    concat_item, context_domain=context_domain, temporal=temporal
                )
                if item_type == BIT:
                    width += 1
                elif item_type and item_type.is_vector and item_type.width is not None:
                    width += item_type.width
                else:
                    valid = False
                    self.emit(
                        "E-TYPE-CONCAT",
                        Severity.ERROR,
                        "concatenation operands must have fixed hardware width",
                        concat_item,
                    )
            result = TypeInfo("bits", width) if valid else None
        elif isinstance(expr, ChoiceExpr):
            branch_type = expected
            for branch in expr.branches:
                guard_type = self.infer_expr(
                    branch.guard,
                    expected=BIT,
                    context_domain=context_domain,
                )
                self.require_type(guard_type, BIT, branch.guard, "choice guard")
                value_type = self.infer_expr(
                    branch.value,
                    expected=branch_type,
                    allow_hold=allow_hold,
                    context_domain=context_domain,
                )
                if branch_type is None and value_type is not None:
                    branch_type = value_type
                self.require_same(branch_type, value_type, branch.value, "choice branch")
            if expr.else_expr is not None:
                else_type = self.infer_expr(
                    expr.else_expr,
                    expected=branch_type,
                    allow_hold=allow_hold,
                    context_domain=context_domain,
                )
                self.require_same(branch_type, else_type, expr.else_expr, "choice else branch")
            result = branch_type
        elif isinstance(expr, TemporalUnaryExpr):
            operand = self.infer_expr(
                expr.operand,
                context_domain=context_domain,
                temporal=True,
            )
            if operand not in {BIT, PROPERTY, None}:
                self.emit(
                    "E-TEMP-TYPE",
                    Severity.ERROR,
                    f"{expr.op} requires a boolean or temporal operand",
                    expr.operand,
                )
            result = PROPERTY
        elif isinstance(expr, TemporalBinaryExpr):
            left = self.infer_expr(expr.left, context_domain=context_domain, temporal=True)
            right = self.infer_expr(expr.right, context_domain=context_domain, temporal=True)
            for temporal_operand, operand_type in ((expr.left, left), (expr.right, right)):
                if operand_type not in {BIT, PROPERTY, None}:
                    self.emit(
                        "E-TEMP-TYPE",
                        Severity.ERROR,
                        f"{expr.op} operands must be boolean or temporal",
                        temporal_operand,
                    )
            result = PROPERTY
        elif isinstance(expr, DelayExpr):
            operand = self.infer_expr(
                expr.operand,
                context_domain=context_domain,
                temporal=True,
            )
            if operand not in {BIT, PROPERTY, None}:
                self.emit(
                    "E-TEMP-TYPE",
                    Severity.ERROR,
                    "delay operand must be boolean or temporal",
                    expr.operand,
                )
            result = PROPERTY
        else:
            raise TypeError(f"unhandled expression type {type(expr).__name__}")

        if result is not None:
            self.expression_types[id(expr)] = result
        return result

    def check_expression_contexts(self, module: Module) -> None:
        allowed_none: set[int] = set()
        allowed_hold: set[int] = set()
        allowed_choices: set[int] = set()
        allowed_unbounded: set[int] = set()
        temporal_nodes: set[int] = set()

        def collect_branch_holds(expr: Expr) -> None:
            if isinstance(expr, HoldExpr):
                allowed_hold.add(id(expr))
            elif isinstance(expr, TernaryExpr):
                collect_branch_holds(expr.then_expr)
                collect_branch_holds(expr.else_expr)

        for item in module.items:
            if (
                isinstance(item, PortDecl | StateDecl)
                and item.reset is not None
                and isinstance(item.reset.value, NoneExpr)
            ):
                allowed_none.add(id(item.reset.value))
            if isinstance(item, Equation) and item.is_next:
                if isinstance(item.value, ChoiceExpr):
                    allowed_choices.add(id(item.value))
                    for branch in item.value.branches:
                        collect_branch_holds(branch.value)
                    if item.value.else_expr is not None:
                        collect_branch_holds(item.value.else_expr)
                elif isinstance(item.value, TernaryExpr):
                    collect_branch_holds(item.value)
            if isinstance(item, PropertyStmt):
                temporal_nodes.update(id(node) for node in iter_nodes(item.property))

        for node in iter_nodes(module):
            if isinstance(node, DelayExpr) and isinstance(node.upper, UnboundedExpr):
                allowed_unbounded.add(id(node.upper))
            if isinstance(node, NoneExpr) and id(node) not in allowed_none:
                self.emit(
                    "E-TYPE-NONE-CONTEXT",
                    Severity.ERROR,
                    "none is only legal as explicit state reset intent",
                    node,
                )
            elif isinstance(node, HoldExpr) and id(node) not in allowed_hold:
                self.emit(
                    "E-STATE-HOLD-CONTEXT",
                    Severity.ERROR,
                    "hold is only legal as a next-state choice/ternary branch value",
                    node,
                )
            elif isinstance(node, ChoiceExpr) and id(node) not in allowed_choices:
                self.emit(
                    "E-CHOICE-CONTEXT",
                    Severity.ERROR,
                    "case/priority is only legal as a complete next-state RHS",
                    node,
                )
            elif (
                isinstance(node, TemporalUnaryExpr | TemporalBinaryExpr | DelayExpr)
                and id(node) not in temporal_nodes
            ):
                self.emit(
                    "E-TEMP-CONTEXT",
                    Severity.ERROR,
                    "temporal operators are only legal in property statements",
                    node,
                )
            elif isinstance(node, UnboundedExpr) and id(node) not in allowed_unbounded:
                self.emit(
                    "E-TEMP-BOUND",
                    Severity.ERROR,
                    "$ is only legal as an upper temporal delay bound",
                    node,
                )

    def infer_binary(
        self,
        expr: BinaryExpr,
        *,
        expected: TypeInfo | None,
        allow_hold: bool,
        context_domain: str | None,
        temporal: bool,
    ) -> TypeInfo | None:
        if expr.op in {"&&", "||"}:
            left = self.infer_expr(
                expr.left, expected=BIT, context_domain=context_domain, temporal=temporal
            )
            right = self.infer_expr(
                expr.right, expected=BIT, context_domain=context_domain, temporal=temporal
            )
            self.require_type(left, BIT, expr.left, "logical operand")
            self.require_type(right, BIT, expr.right, "logical operand")
            return BIT

        if expr.op in {"==", "!=", "<", "<=", ">", ">="}:
            left = self.infer_expr(expr.left, context_domain=context_domain, temporal=temporal)
            right = self.infer_expr(
                expr.right,
                expected=left,
                context_domain=context_domain,
                temporal=temporal,
            )
            if left == INT and right and right.is_hardware:
                left = self.infer_expr(
                    expr.left,
                    expected=right,
                    context_domain=context_domain,
                    temporal=temporal,
                )
            if right == INT and left and left.is_hardware:
                right = self.infer_expr(
                    expr.right,
                    expected=left,
                    context_domain=context_domain,
                    temporal=temporal,
                )
            self.require_same(left, right, expr, "comparison operands")
            if expr.op in {"<", "<=", ">", ">="} and left and left.kind == "enum":
                self.emit(
                    "E-TYPE-ENUM-ORDER",
                    Severity.ERROR,
                    "enum values only support == and != comparisons",
                    expr,
                )
            return BIT

        if expr.op in {"<<", ">>"}:
            left = self.infer_expr(
                expr.left,
                expected=expected,
                context_domain=context_domain,
                temporal=temporal,
            )
            right = self.infer_expr(
                expr.right,
                context_domain=context_domain,
                temporal=temporal,
            )
            if left and left.kind not in {"bits", "uint", "sint", "int"}:
                self.emit(
                    "E-TYPE-OPERATOR",
                    Severity.ERROR,
                    "shift requires a bitvector or integer left operand",
                    expr.left,
                )
            if right == INT and left and left.is_hardware and left.width is not None:
                right = self.infer_expr(
                    expr.right,
                    expected=TypeInfo("uint", left.width),
                    context_domain=context_domain,
                    temporal=temporal,
                )
            if right and right.kind not in {"uint", "int"}:
                self.emit(
                    "E-TYPE-OPERATOR",
                    Severity.ERROR,
                    "shift amount must be unsigned or compile-time int",
                    expr.right,
                )
            if (
                left
                and right
                and left.is_hardware
                and right.is_hardware
                and left.width != right.width
            ):
                self.emit(
                    "E-TYPE-WIDTH-MISMATCH",
                    Severity.ERROR,
                    "shift value and amount must have equal widths; use an explicit conversion",
                    expr,
                )
            return left

        left = self.infer_expr(
            expr.left,
            expected=expected,
            context_domain=context_domain,
            temporal=temporal,
        )
        right = self.infer_expr(
            expr.right,
            expected=left or expected,
            context_domain=context_domain,
            temporal=temporal,
        )
        if left == INT and right and right.is_hardware:
            left = self.infer_expr(
                expr.left,
                expected=right,
                context_domain=context_domain,
                temporal=temporal,
            )
        if right == INT and left and left.is_hardware:
            right = self.infer_expr(
                expr.right,
                expected=left,
                context_domain=context_domain,
                temporal=temporal,
            )

        if expr.op in {"&", "|", "^"}:
            allowed = {"bits", "uint", "sint"}
            if left and left.kind not in allowed:
                self.emit(
                    "E-TYPE-OPERATOR",
                    Severity.ERROR,
                    f"bitwise {expr.op} requires bitvector operands; use logical operators for bit",
                    expr,
                )
            self.require_same(left, right, expr, "bitwise operands")
            return left or right
        if expr.op in {"+", "-", "*", "/", "%"}:
            allowed = {"uint", "sint", "int"}
            if left and left.kind not in allowed:
                self.emit(
                    "E-TYPE-OPERATOR",
                    Severity.ERROR,
                    f"arithmetic {expr.op} requires uN, sN, or compile-time int operands",
                    expr,
                )
            self.require_same(left, right, expr, "arithmetic operands")
            return left or right
        return None

    def infer_call(
        self,
        expr: CallExpr,
        *,
        context_domain: str | None,
        temporal: bool,
    ) -> TypeInfo | None:
        sampled = {"rose", "fell", "stable", "changed"}
        if expr.function in sampled:
            if not temporal:
                self.emit(
                    "E-TEMP-CONTEXT",
                    Severity.ERROR,
                    f"{expr.function} is only legal in a temporal property",
                    expr,
                )
            if len(expr.args) != 1:
                self.emit(
                    "E-TEMP-ARITY",
                    Severity.ERROR,
                    f"{expr.function} requires one argument",
                    expr,
                )
            for arg in expr.args:
                arg_type = self.infer_expr(arg, context_domain=context_domain)
                if arg_type is not None and not arg_type.is_hardware:
                    self.emit(
                        "E-TEMP-TYPE",
                        Severity.ERROR,
                        f"{expr.function} argument must be a sampled hardware value",
                        arg,
                    )
                if expr.function in {"rose", "fell"} and arg_type not in {BIT, None}:
                    self.emit(
                        "E-TEMP-TYPE",
                        Severity.ERROR,
                        f"{expr.function} requires a bit operand in v0.1",
                        arg,
                    )
            return BIT
        if expr.function == "past":
            if not temporal:
                self.emit(
                    "E-TEMP-CONTEXT",
                    Severity.ERROR,
                    "past is only legal in a temporal property",
                    expr,
                )
            if len(expr.args) != 2:
                self.emit("E-TEMP-ARITY", Severity.ERROR, "past requires two arguments", expr)
                return None
            value_type = self.infer_expr(expr.args[0], context_domain=context_domain)
            bound = self.eval_const(expr.args[1])
            if bound is None or bound < 0:
                self.emit(
                    "E-TEMP-BOUND",
                    Severity.ERROR,
                    "past sample count must be a non-negative compile-time integer",
                    expr.args[1],
                )
            return value_type
        if expr.function in {"zext", "sext", "trunc"}:
            if len(expr.args) != 2:
                self.emit(
                    "E-TYPE-ARITY",
                    Severity.ERROR,
                    f"{expr.function} requires value and target width",
                    expr,
                )
                return None
            source_type = self.infer_expr(expr.args[0], context_domain=context_domain)
            width = self.eval_const(expr.args[1])
            if source_type and not source_type.is_vector:
                self.emit(
                    "E-TYPE-CONVERSION",
                    Severity.ERROR,
                    f"{expr.function} requires a bitvector source",
                    expr.args[0],
                )
            if width is None or width <= 0:
                self.emit(
                    "E-TYPE-WIDTH",
                    Severity.ERROR,
                    f"{expr.function} target width must be a positive compile-time integer",
                    expr.args[1],
                )
                return None
            if source_type and source_type.width is not None:
                if expr.function in {"zext", "sext"} and width < source_type.width:
                    self.emit(
                        "E-TYPE-CONVERSION",
                        Severity.ERROR,
                        f"{expr.function} cannot reduce width from {source_type.width} to {width}",
                        expr,
                    )
                if expr.function == "trunc" and width > source_type.width:
                    self.emit(
                        "E-TYPE-CONVERSION",
                        Severity.ERROR,
                        f"trunc cannot increase width from {source_type.width} to {width}",
                        expr,
                    )
            kind = (
                "sint" if expr.function == "sext" else (source_type.kind if source_type else "bits")
            )
            return TypeInfo(kind, width)
        if expr.function in {"as_u", "as_s"}:
            if len(expr.args) != 1:
                self.emit(
                    "E-TYPE-ARITY",
                    Severity.ERROR,
                    f"{expr.function} requires one argument",
                    expr,
                )
                return None
            source_type = self.infer_expr(expr.args[0], context_domain=context_domain)
            if source_type and not source_type.is_vector:
                self.emit(
                    "E-TYPE-CONVERSION",
                    Severity.ERROR,
                    f"{expr.function} requires a bitvector source",
                    expr.args[0],
                )
            return TypeInfo(
                "uint" if expr.function == "as_u" else "sint",
                source_type.width if source_type else None,
            )

        self.emit(
            "E-NAME-BUILTIN",
            Severity.ERROR,
            f"unknown builtin function '{expr.function}'",
            expr,
        )
        for arg in expr.args:
            self.infer_expr(arg, context_domain=context_domain, temporal=temporal)
        return None

    def require_type(
        self,
        actual: TypeInfo | None,
        expected: TypeInfo,
        node: Node,
        context: str,
    ) -> None:
        if actual is not None and actual != expected:
            self.emit(
                "E-TYPE-MISMATCH",
                Severity.ERROR,
                f"{context} has type {actual.describe()}, expected {expected.describe()}",
                node,
            )

    def require_same(
        self,
        left: TypeInfo | None,
        right: TypeInfo | None,
        node: Node,
        context: str,
    ) -> None:
        if left is not None and right is not None and left != right:
            code = (
                "E-TYPE-WIDTH-MISMATCH"
                if left.width != right.width and left.is_hardware and right.is_hardware
                else "E-TYPE-MISMATCH"
            )
            self.emit(
                code,
                Severity.ERROR,
                f"{context} have incompatible types {left.describe()} and {right.describe()}; "
                "use an explicit conversion",
                node,
            )

    def check_drivers(self, module: Module) -> None:
        next_drivers: dict[str, list[Equation]] = defaultdict(list)
        comb_drivers: dict[str, list[Node]] = defaultdict(list)
        for item in module.items:
            if isinstance(item, Equation):
                (next_drivers if item.is_next else comb_drivers)[item.target].append(item)
            elif isinstance(item, PortDecl) and item.value is not None:
                for name in item.names:
                    comb_drivers[name].append(item)
            elif isinstance(item, LetDecl):
                comb_drivers[item.name].append(item)

        for symbol in self.current_symbols.values():
            if symbol.enum_value is not None or isinstance(symbol.node, ParamDecl | ConstDecl):
                continue
            if symbol.is_abstract:
                continue
            if symbol.is_state:
                state_drivers = next_drivers.get(symbol.name, [])
                if not state_drivers:
                    self.emit(
                        "E-STATE-MISSING-NEXT",
                        Severity.ERROR,
                        f"state '{symbol.name}' has no next-state equation; omitted behavior "
                        "is a semantic hole, not hold",
                        symbol.node,
                    )
                elif len(state_drivers) > 1:
                    self.emit(
                        "E-STATE-MULTIPLE-NEXT",
                        Severity.ERROR,
                        f"state '{symbol.name}' has {len(state_drivers)} next-state equations",
                        state_drivers[1],
                    )
            elif symbol.direction == "out" and not comb_drivers.get(symbol.name):
                self.emit(
                    "E-COMB-UNDRIVEN",
                    Severity.ERROR,
                    f"output '{symbol.name}' has no defining combinational equation",
                    symbol.node,
                )

        for target, definition_drivers in comb_drivers.items():
            if len(definition_drivers) > 1:
                self.emit(
                    "E-COMB-MULTIPLE-DRIVERS",
                    Severity.ERROR,
                    f"symbol '{target}' has multiple combinational definitions",
                    definition_drivers[1],
                )

    def expression_names(self, expr: Expr) -> set[str]:
        return {
            node.name
            for node in iter_nodes(expr)
            if isinstance(node, NameExpr) and node.name in self.current_symbols
        }

    def check_unused_lets(self, module: Module) -> None:
        lets = {item.name: item for item in module.items if isinstance(item, LetDecl)}
        dependencies = {
            name: self.expression_names(item.value) & lets.keys()
            for name, item in lets.items()
        }
        live = {
            node.name
            for item in module.items
            if not isinstance(item, LetDecl)
            for node in iter_nodes(item)
            if isinstance(node, NameExpr) and node.name in lets
        }
        pending = list(live)
        while pending:
            name = pending.pop()
            for dependency in dependencies.get(name, set()):
                if dependency not in live:
                    live.add(dependency)
                    pending.append(dependency)
        for item in module.items:
            if isinstance(item, LetDecl) and item.name not in live:
                self.emit(
                    "W-UNUSED-LET",
                    Severity.WARNING,
                    f"let '{item.name}' is not used by behavior, property, or contract binding",
                    item,
                )

    def check_comb_cycles(self, module: Module) -> None:
        definitions: dict[str, tuple[Expr, Node]] = {}
        for item in module.items:
            if isinstance(item, LetDecl):
                definitions[item.name] = (item.value, item)
            elif isinstance(item, Equation) and not item.is_next:
                definitions[item.target] = (item.value, item)
            elif isinstance(item, PortDecl) and item.value is not None:
                for name in item.names:
                    definitions[name] = (item.value, item)
        graph = {
            target: self.expression_names(value) & definitions.keys()
            for target, (value, _node) in definitions.items()
        }
        visiting: list[str] = []
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visiting:
                cycle = visiting[visiting.index(name) :] + [name]
                self.emit(
                    "E-COMB-CYCLE",
                    Severity.ERROR,
                    "combinational dependency cycle: " + " -> ".join(cycle),
                    definitions[name][1],
                )
                return
            if name in visited:
                return
            visiting.append(name)
            for dependency in graph.get(name, set()):
                visit(dependency)
            visiting.pop()
            visited.add(name)

        for name in graph:
            visit(name)

    def check_holes(self, module: Module) -> None:
        for node in iter_nodes(module):
            if isinstance(node, HoleExpr):
                label = f"?{node.name}" if node.name else "anonymous ?"
                self.emit(
                    "E-HOLE-UNRESOLVED",
                    Severity.ERROR,
                    f"unresolved semantic hole '{label}' affects executable or "
                    "verification meaning",
                    node,
                )

    def check_temporal_bounds(self, module: Module) -> None:
        for node in iter_nodes(module):
            if not isinstance(node, DelayExpr):
                continue
            lower = self.eval_const(node.lower)
            upper = self.eval_const(node.upper)
            if isinstance(node.lower, UnboundedExpr):
                self.emit(
                    "E-TEMP-BOUND",
                    Severity.ERROR,
                    "unbounded marker $ is only legal as the upper delay bound",
                    node.lower,
                )
            if not isinstance(node.lower, HoleExpr) and lower is None:
                self.emit(
                    "E-TEMP-BOUND",
                    Severity.ERROR,
                    "delay lower bound must be a non-negative compile-time integer",
                    node.lower,
                )
            if not isinstance(node.upper, HoleExpr | UnboundedExpr) and upper is None:
                self.emit(
                    "E-TEMP-BOUND",
                    Severity.ERROR,
                    "delay upper bound must be an integer, $, or semantic hole",
                    node.upper,
                )
            if lower is not None and lower < 0:
                self.emit(
                    "E-TEMP-BOUND",
                    Severity.ERROR,
                    "delay lower bound cannot be negative",
                    node.lower,
                )
            if lower is not None and upper is not None and upper < lower:
                self.emit(
                    "E-TEMP-BOUND",
                    Severity.ERROR,
                    f"delay range [{lower}:{upper}] has upper bound below lower bound",
                    node,
                )

    def effective_domain(self, symbol: Symbol) -> str | None:
        return symbol.domain or self._single_domain

    def check_cdc(self, expr: Expr, target_domain: str | None, owner: Node) -> None:
        if target_domain is None:
            return
        for name in sorted(self.expression_names(expr)):
            symbol = self.current_symbols[name]
            if symbol.enum_value is not None or symbol.type_info == INT:
                continue
            source_domain = self.effective_domain(symbol)
            if source_domain is not None and source_domain != target_domain:
                self.emit(
                    "E-CDC-UNQUALIFIED",
                    Severity.ERROR,
                    f"'{name}' from domain '{source_domain}' is sampled in domain "
                    f"'{target_domain}' without synchronization intent",
                    owner,
                    notes=("CDC patterns belong in a library/annotation, not a new core keyword.",),
                )
            elif source_domain is None and len(self.domains) > 1:
                self.emit(
                    "E-DOMAIN-AMBIGUOUS",
                    Severity.ERROR,
                    f"domain of referenced signal '{name}' cannot be inferred in a "
                    "multi-domain module",
                    owner,
                )

    def check_choice_semantics(self, module: Module) -> None:
        for item in module.items:
            expressions: list[tuple[Expr, str | None]] = []
            if isinstance(item, Equation):
                symbol = self.current_symbols.get(item.target)
                expressions.append((item.value, self.effective_domain(symbol) if symbol else None))
            elif isinstance(item, PortDecl) and item.value is not None:
                expressions.append((item.value, item.domain or self._single_domain))
            elif isinstance(item, LetDecl | ConstDecl):
                expressions.append((item.value, None))
            for expression, domain in expressions:
                for node in iter_nodes(expression):
                    if isinstance(node, ChoiceExpr):
                        self.analyze_choice(node, domain)

    def analyze_choice(self, choice: ChoiceExpr, domain: str | None) -> None:
        if not self.use_solver:
            if choice.kind == "priority" and choice.else_expr is not None:
                return
            self.emit(
                "W-CHOICE-NOT-PROVEN",
                Severity.WARNING,
                f"{choice.kind} overlap/coverage was not solver-checked",
                choice,
            )
            return
        try:
            z3 = importlib.import_module("z3")
            translator = _Z3Translator(z3, self.current_symbols, self.expression_types)
            guards = [
                translator.translate(branch.guard, expected=BIT) for branch in choice.branches
            ]
            assumptions = self.solver_assumptions(domain, translator)
            if any(guard is None for guard in guards):
                raise ValueError("unsupported guard expression")
            concrete_guards = [guard for guard in guards if guard is not None]
            if choice.kind == "case":
                for first in range(len(concrete_guards)):
                    for second in range(first + 1, len(concrete_guards)):
                        solver = z3.Solver()
                        solver.add(*translator.constraints, *assumptions)
                        solver.add(concrete_guards[first], concrete_guards[second])
                        if solver.check() == z3.sat:
                            self.emit(
                                "E-CHOICE-OVERLAP",
                                Severity.ERROR,
                                f"overlapping guards {first + 1} and {second + 1} in "
                                "unordered case",
                                choice,
                                notes=(
                                    "specify priority, add an exclusivity assumption, or "
                                    "refine guards",
                                ),
                                witness=translator.witness(
                                    solver.model(), self.choice_relevant_names(choice, domain)
                                ),
                            )
            else:
                previous: list[Any] = []
                for index, guard in enumerate(concrete_guards):
                    solver = z3.Solver()
                    solver.add(*translator.constraints, *assumptions)
                    if previous:
                        solver.add(z3.Not(z3.Or(*previous)))
                    solver.add(guard)
                    if solver.check() == z3.unsat:
                        self.emit(
                            "E-CHOICE-UNREACHABLE",
                            Severity.WARNING,
                            f"priority branch {index + 1} is unreachable after earlier branches",
                            choice.branches[index],
                        )
                    previous.append(guard)

            if choice.else_expr is None:
                solver = z3.Solver()
                solver.add(*translator.constraints, *assumptions)
                solver.add(z3.Not(z3.Or(*concrete_guards)))
                if solver.check() == z3.sat:
                    self.emit(
                        "E-CHOICE-COVERAGE",
                        Severity.ERROR,
                        f"{choice.kind} does not cover all input/state combinations; "
                        "missing space is a semantic hole",
                        choice,
                        witness=translator.witness(
                            solver.model(), self.choice_relevant_names(choice, domain)
                        ),
                    )
        except (ImportError, ValueError, TypeError, AttributeError) as exc:
            if choice.kind == "priority" and choice.else_expr is not None:
                return
            self.emit(
                "W-CHOICE-NOT-PROVEN",
                Severity.WARNING,
                f"could not prove {choice.kind} guards with the available solver: {exc}",
                choice,
            )

    def choice_relevant_names(self, choice: ChoiceExpr, domain: str | None) -> set[str]:
        names: set[str] = set()
        for branch in choice.branches:
            names.update(self.expression_names(branch.guard))
        assert self.current_module is not None
        for item in self.current_module.items:
            if isinstance(item, PropertyStmt) and item.kind == "assume" and item.domain == domain:
                names.update(self.expression_names(item.property))
        return names

    def solver_assumptions(self, domain: str | None, translator: _Z3Translator) -> list[Any]:
        assumptions: list[Any] = []
        assert self.current_module is not None
        for item in self.current_module.items:
            if not isinstance(item, PropertyStmt) or item.kind != "assume" or item.domain != domain:
                continue
            if item.unless is not None:
                continue
            expression = item.property
            if isinstance(expression, TemporalUnaryExpr) and expression.op == "always":
                expression = expression.operand
            if any(
                isinstance(node, TemporalBinaryExpr | DelayExpr | TemporalUnaryExpr)
                for node in iter_nodes(expression)
            ):
                continue
            translated = translator.translate(expression, expected=BIT)
            if translated is not None:
                assumptions.append(translated)
        return assumptions


class _Z3Translator:
    def __init__(
        self,
        z3: Any,
        symbols: dict[str, Symbol],
        expression_types: dict[int, TypeInfo],
    ):
        self.z3 = z3
        self.symbols = symbols
        self.expression_types = expression_types
        self.variables: dict[str, Any] = {}
        self.constraints: list[Any] = []
        for name, symbol in symbols.items():
            if symbol.enum_value is not None or symbol.type_info == INT:
                continue
            type_info = symbol.type_info
            if type_info.kind == "bit":
                self.variables[name] = z3.Bool(name)
            elif type_info.kind == "enum":
                variable = z3.Int(name)
                self.variables[name] = variable
                self.constraints.extend((variable >= 0, variable < len(type_info.members)))
            elif type_info.width is not None:
                self.variables[name] = z3.BitVec(name, type_info.width)

    def translate(self, expr: Expr, expected: TypeInfo | None = None) -> Any | None:
        z3 = self.z3
        inferred = self.expression_types.get(id(expr), expected)
        if isinstance(expr, NameExpr):
            symbol = self.symbols.get(expr.name)
            if symbol and symbol.enum_value is not None:
                return z3.IntVal(symbol.enum_value)
            return self.variables.get(expr.name)
        if isinstance(expr, IntExpr):
            target = expected or inferred
            if target and target.kind == "bit":
                return z3.BoolVal(bool(expr.value))
            if target and target.kind == "enum":
                return z3.IntVal(expr.value)
            if target and target.width is not None:
                return z3.BitVecVal(expr.value, target.width)
            return z3.IntVal(expr.value)
        if isinstance(expr, IndexExpr):
            value = self.translate(expr.value)
            # shortcut: literal indices only; extend when symbolic guard indices are needed.
            if not isinstance(expr.index, IntExpr) or not z3.is_bv(value):
                return None
            index = expr.index.value
            if not 0 <= index < value.size():
                return None
            return z3.Extract(index, index, value) == 1
        if isinstance(expr, UnaryExpr):
            operand = self.translate(expr.operand, self.expression_types.get(id(expr.operand)))
            if operand is None:
                return None
            return {
                "!": lambda: z3.Not(operand),
                "~": lambda: ~operand,
                "-": lambda: -operand,
                "+": lambda: operand,
            }[expr.op]()
        if isinstance(expr, BinaryExpr):
            left_type = self.expression_types.get(id(expr.left))
            right_type = self.expression_types.get(id(expr.right))
            common = left_type if left_type and left_type != INT else right_type
            left = self.translate(expr.left, common)
            right = self.translate(expr.right, common)
            if left is None or right is None:
                return None
            operations = {
                "&&": lambda: z3.And(left, right),
                "||": lambda: z3.Or(left, right),
                "&": lambda: left & right,
                "|": lambda: left | right,
                "^": lambda: left ^ right,
                "+": lambda: left + right,
                "-": lambda: left - right,
                "*": lambda: left * right,
                "/": lambda: (
                    z3.UDiv(left, right)
                    if common and common.kind in {"uint", "bits"}
                    else left / right
                ),
                "%": lambda: (
                    z3.URem(left, right)
                    if common and common.kind in {"uint", "bits"}
                    else left % right
                ),
                "<<": lambda: left << right,
                ">>": lambda: (
                    z3.LShR(left, right)
                    if common and common.kind in {"uint", "bits"}
                    else left >> right
                ),
                "==": lambda: left == right,
                "!=": lambda: left != right,
                "<": lambda: (
                    z3.ULT(left, right)
                    if common and common.kind in {"uint", "bits"}
                    else left < right
                ),
                "<=": lambda: (
                    z3.ULE(left, right)
                    if common and common.kind in {"uint", "bits"}
                    else left <= right
                ),
                ">": lambda: (
                    z3.UGT(left, right)
                    if common and common.kind in {"uint", "bits"}
                    else left > right
                ),
                ">=": lambda: (
                    z3.UGE(left, right)
                    if common and common.kind in {"uint", "bits"}
                    else left >= right
                ),
            }
            return operations[expr.op]()
        if isinstance(expr, TernaryExpr):
            condition = self.translate(expr.condition, BIT)
            then_expr = self.translate(expr.then_expr, expected or inferred)
            else_expr = self.translate(expr.else_expr, expected or inferred)
            if any(value is None for value in (condition, then_expr, else_expr)):
                return None
            return z3.If(condition, then_expr, else_expr)
        if isinstance(expr, CallExpr):
            return None
        return None

    def witness(self, model: Any, relevant: set[str] | None = None) -> dict[str, str]:
        result: dict[str, str] = {}
        for name, variable in sorted(self.variables.items()):
            if relevant is not None and name not in relevant:
                continue
            value = model.eval(variable, model_completion=True)
            symbol = self.symbols[name]
            if symbol.type_info.kind == "bit":
                result[name] = "1" if self.z3.is_true(value) else "0"
            elif symbol.type_info.kind == "enum":
                index = value.as_long()
                members = symbol.type_info.members
                result[name] = members[index] if 0 <= index < len(members) else str(index)
            else:
                result[name] = str(value.as_long())
        return result


def check(program: Program, *, solver: bool = True) -> CheckResult:
    return Checker(program, solver=solver).run()


def diagnostic_to_dict(diagnostic: Diagnostic, source_name: str) -> dict[str, Any]:
    return {
        "code": diagnostic.code,
        "severity": diagnostic.severity.value,
        "message": diagnostic.message,
        "source": {
            "file": diagnostic.source_name or source_name,
            "line": diagnostic.span.line,
            "column": diagnostic.span.column,
            "end_line": diagnostic.span.end_line,
            "end_column": diagnostic.span.end_column,
        },
        "node_id": diagnostic.node_id,
        "notes": list(diagnostic.notes),
        "witness": diagnostic.witness,
    }


def semantics_fingerprint(program: Program) -> str:
    import hashlib
    import json

    payload = json.dumps(semantic_dict(program), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()

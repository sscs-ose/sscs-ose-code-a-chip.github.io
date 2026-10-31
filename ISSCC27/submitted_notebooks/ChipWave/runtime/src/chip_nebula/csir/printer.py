from __future__ import annotations

from .ast import (
    AbstractDecl,
    BinaryExpr,
    CallExpr,
    ChoiceExpr,
    ConcatExpr,
    ConstDecl,
    ContractApply,
    DelayExpr,
    DomainDecl,
    Equation,
    Expr,
    HoldExpr,
    HoleExpr,
    IndexExpr,
    IntExpr,
    Item,
    LetDecl,
    Module,
    NameExpr,
    NoneExpr,
    ParamDecl,
    PortDecl,
    Program,
    PropertyStmt,
    SliceExpr,
    StateDecl,
    TemporalBinaryExpr,
    TemporalUnaryExpr,
    TernaryExpr,
    TypeRef,
    UnaryExpr,
    UnboundedExpr,
)

_PRECEDENCE = {
    "|->": 1,
    "|=>": 1,
    "until": 2,
    "?:": 3,
    "||": 4,
    "&&": 6,
    "|": 8,
    "^": 10,
    "&": 12,
    "==": 14,
    "!=": 14,
    "<": 16,
    "<=": 16,
    ">": 16,
    ">=": 16,
    "<<": 18,
    ">>": 18,
    "+": 20,
    "-": 20,
    "*": 22,
    "/": 22,
    "%": 22,
    "unary": 24,
    "postfix": 26,
    "atom": 28,
}


def format_type(type_ref: TypeRef) -> str:
    if type_ref.kind == "bit":
        return "bit"
    if type_ref.kind == "int":
        return "int"
    if type_ref.kind == "bits":
        assert type_ref.width is not None
        return f"bits[{format_expr(type_ref.width)}]"
    if type_ref.kind in {"uint", "sint"}:
        assert type_ref.width is not None
        prefix = "u" if type_ref.kind == "uint" else "s"
        if isinstance(type_ref.width, IntExpr):
            return f"{prefix}{type_ref.width.value}"
        return f"{prefix}[{format_expr(type_ref.width)}]"
    if type_ref.kind == "enum":
        return "{" + ",".join(type_ref.members) + "}"
    raise ValueError(f"unknown type kind {type_ref.kind!r}")


def _with_parentheses(text: str, own_precedence: int, parent_precedence: int) -> str:
    return f"({text})" if own_precedence < parent_precedence else text


def format_expr(expr: Expr, parent_precedence: int = 0, *, indent: int = 0) -> str:
    if isinstance(expr, NameExpr):
        return expr.name
    if isinstance(expr, IntExpr):
        return expr.raw
    if isinstance(expr, HoleExpr):
        return "?" + (expr.name or "")
    if isinstance(expr, NoneExpr):
        return "none"
    if isinstance(expr, HoldExpr):
        return "hold"
    if isinstance(expr, UnboundedExpr):
        return "$"
    if isinstance(expr, UnaryExpr):
        text = expr.op + format_expr(expr.operand, _PRECEDENCE["unary"], indent=indent)
        return _with_parentheses(text, _PRECEDENCE["unary"], parent_precedence)
    if isinstance(expr, BinaryExpr | TemporalBinaryExpr):
        precedence = _PRECEDENCE[expr.op]
        left = format_expr(expr.left, precedence, indent=indent)
        right = format_expr(expr.right, precedence + 1, indent=indent)
        return _with_parentheses(f"{left} {expr.op} {right}", precedence, parent_precedence)
    if isinstance(expr, TernaryExpr):
        precedence = _PRECEDENCE["?:"]
        condition = format_expr(expr.condition, precedence, indent=indent)
        then_expr = format_expr(expr.then_expr, 0, indent=indent)
        else_expr = format_expr(expr.else_expr, precedence, indent=indent)
        return _with_parentheses(
            f"{condition} ? {then_expr} : {else_expr}", precedence, parent_precedence
        )
    if isinstance(expr, CallExpr):
        args = ", ".join(format_expr(arg, indent=indent) for arg in expr.args)
        return f"{expr.function}({args})"
    if isinstance(expr, IndexExpr):
        return f"{format_expr(expr.value, _PRECEDENCE['postfix'])}[{format_expr(expr.index)}]"
    if isinstance(expr, SliceExpr):
        return (
            f"{format_expr(expr.value, _PRECEDENCE['postfix'])}"
            f"[{format_expr(expr.msb)}:{format_expr(expr.lsb)}]"
        )
    if isinstance(expr, ConcatExpr):
        return "{" + ", ".join(format_expr(value) for value in expr.values) + "}"
    if isinstance(expr, ChoiceExpr):
        pad = "  " * indent
        branch_pad = "  " * (indent + 1)
        lines = [f"{expr.kind} {{"]
        for branch in expr.branches:
            lines.append(
                f"{branch_pad}{format_expr(branch.guard, indent=indent + 1)} -> "
                f"{format_expr(branch.value, indent=indent + 1)}"
            )
        if expr.else_expr is not None:
            lines.append(f"{branch_pad}else -> {format_expr(expr.else_expr, indent=indent + 1)}")
        lines.append(f"{pad}}}")
        return "\n".join(lines)
    if isinstance(expr, TemporalUnaryExpr):
        text = f"{expr.op} {format_expr(expr.operand, 3, indent=indent)}"
        return _with_parentheses(text, 3, parent_precedence)
    if isinstance(expr, DelayExpr):
        if (
            isinstance(expr.lower, IntExpr)
            and isinstance(expr.upper, IntExpr)
            and expr.lower.value == expr.upper.value
        ):
            bound = str(expr.lower.value)
        else:
            bound = f"[{format_expr(expr.lower)}:{format_expr(expr.upper)}]"
        text = f"##{bound} {format_expr(expr.operand, 3, indent=indent)}"
        return _with_parentheses(text, 3, parent_precedence)
    raise TypeError(f"unsupported expression {type(expr).__name__}")


def _format_reset(item: PortDecl | StateDecl) -> str:
    if item.reset is None:
        return ""
    return f" reset {format_expr(item.reset.value)}"


def format_item(item: Item, *, indent: int = 1) -> str:
    pad = "  " * indent
    if isinstance(item, AbstractDecl):
        direction = " out" if item.direction == "out" else ""
        domain = f" @{item.domain}" if item.domain else ""
        return (
            f"{pad}abstract{direction} {', '.join(item.names)}: "
            f"{format_type(item.type_ref)}{domain}"
        )
    if isinstance(item, ContractApply):
        lines = [f"{pad}apply {item.contract_id} {{"]
        binding_pad = "  " * (indent + 1)
        lines.extend(
            f"{binding_pad}{binding.role}: "
            f"{format_expr(binding.value, indent=indent + 1)}"
            for binding in item.bindings
        )
        lines.append(f"{pad}}}")
        return "\n".join(lines)
    if isinstance(item, DomainDecl):
        text = f"domain {item.name} = {item.edge} {item.clock}"
        if item.reset is not None:
            mode = item.reset_mode or "sync"
            text += f", {mode} reset {format_expr(item.reset)}"
        return pad + text
    if isinstance(item, PortDecl):
        state = " state" if item.is_state else ""
        domain = f" @{item.domain}" if item.domain else ""
        value = f" = {format_expr(item.value, indent=indent)}" if item.value else ""
        return (
            f"{pad}{item.direction}{state} {', '.join(item.names)}: "
            f"{format_type(item.type_ref)}{domain}{_format_reset(item)}{value}"
        )
    if isinstance(item, StateDecl):
        return (
            f"{pad}state {', '.join(item.names)}: {format_type(item.type_ref)} "
            f"@{item.domain}{_format_reset(item)}"
        )
    if isinstance(item, ConstDecl):
        return f"{pad}const {item.name}: {format_type(item.type_ref)} = {format_expr(item.value)}"
    if isinstance(item, ParamDecl):
        return f"{pad}param {item.name}: int = {format_expr(item.value)}"
    if isinstance(item, LetDecl):
        annotation = f": {format_type(item.type_ref)}" if item.type_ref else ""
        return f"{pad}let {item.name}{annotation} = {format_expr(item.value, indent=indent)}"
    if isinstance(item, Equation):
        prime = "'" if item.is_next else ""
        value = format_expr(item.value, indent=indent)
        return f"{pad}{item.target}{prime} = {value}"
    if isinstance(item, PropertyStmt):
        text = f"{pad}{item.kind} @{item.domain} {format_expr(item.property, indent=indent)}"
        if item.unless is not None:
            text += f" unless {format_expr(item.unless)}"
        return text
    raise TypeError(f"unsupported item {type(item).__name__}")


def format_module(module: Module) -> str:
    if module.fragment:
        return "\n".join(format_item(item, indent=0) for item in module.items) + "\n"
    if module.parameters:
        parameters = ", ".join(
            f"{parameter.name}: int = {format_expr(parameter.value)}"
            for parameter in module.parameters
        )
        header = f"module {module.name}({parameters}) {{"
    else:
        header = f"module {module.name} {{"
    lines = [header]
    lines.extend(format_item(item) for item in module.items)
    lines.append("}")
    return "\n".join(lines)


def format_program(program: Program) -> str:
    return "\n\n".join(format_module(module).rstrip() for module in program.modules) + "\n"

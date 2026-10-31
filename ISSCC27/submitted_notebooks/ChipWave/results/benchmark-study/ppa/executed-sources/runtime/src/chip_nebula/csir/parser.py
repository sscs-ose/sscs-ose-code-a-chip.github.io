from __future__ import annotations

import re
from pathlib import Path

from .ast import (
    AbstractDecl,
    BinaryExpr,
    Branch,
    CallExpr,
    ChoiceExpr,
    ConcatExpr,
    ConstDecl,
    ContractApply,
    ContractBinding,
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
    ResetClause,
    SliceExpr,
    Span,
    StateDecl,
    TemporalBinaryExpr,
    TemporalUnaryExpr,
    TernaryExpr,
    TypeRef,
    UnaryExpr,
    UnboundedExpr,
    assign_node_ids,
)
from .lexer import LexError, Token, lex


class ParseError(ValueError):
    def __init__(self, message: str, span: Span):
        super().__init__(message)
        self.message = message
        self.span = span


_STATEMENT_KEYWORDS = {
    "abstract",
    "apply",
    "module",
    "domain",
    "in",
    "out",
    "state",
    "const",
    "param",
    "let",
    "assume",
    "assert",
    "cover",
    "else",
    "unless",
}

_BINARY_BINDING_POWER: dict[str, tuple[int, int]] = {
    "|->": (1, 1),
    "|=>": (1, 1),
    "until": (2, 3),
    "||": (4, 5),
    "&&": (6, 7),
    "|": (8, 9),
    "^": (10, 11),
    "&": (12, 13),
    "==": (14, 15),
    "!=": (14, 15),
    "<": (16, 17),
    "<=": (16, 17),
    ">": (16, 17),
    ">=": (16, 17),
    "<<": (18, 19),
    ">>": (18, 19),
    "+": (20, 21),
    "-": (20, 21),
    "*": (22, 23),
    "/": (22, 23),
    "%": (22, 23),
}


def _merge(first: Span, second: Span) -> Span:
    return Span(first.line, first.column, second.end_line, second.end_column)


class Parser:
    def __init__(self, tokens: list[Token], source_name: str, *, fragment: bool = False):
        self.tokens = tokens
        self.source_name = source_name
        self.index = 0
        self.fragment = fragment

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def peek(self, offset: int = 1) -> Token:
        return self.tokens[min(self.index + offset, len(self.tokens) - 1)]

    def advance(self) -> Token:
        token = self.current
        self.index += 1
        return token

    def at(self, value: str) -> bool:
        return self.current.kind == value or self.current.value == value

    def at_ident(self, value: str | None = None) -> bool:
        if self.current.kind != "IDENT":
            return False
        return value is None or self.current.value == value

    def accept(self, value: str) -> Token | None:
        if self.at(value):
            return self.advance()
        return None

    def accept_ident(self, value: str) -> Token | None:
        if self.at_ident(value):
            return self.advance()
        return None

    def expect(self, value: str, message: str | None = None) -> Token:
        if not self.at(value):
            raise ParseError(
                message or f"expected {value!r}, found {self.current.value!r}", self.current.span
            )
        return self.advance()

    def expect_ident(self, message: str = "expected identifier") -> Token:
        if self.current.kind != "IDENT":
            raise ParseError(message, self.current.span)
        return self.advance()

    def at_separator(self) -> bool:
        return self.at(";") or self.at("NEWLINE")

    def separators(self) -> None:
        while self.at_separator():
            self.advance()

    def require_item_boundary(self, *terminators: str) -> None:
        if not self.at_separator() and not any(self.at(value) for value in terminators):
            raise ParseError(
                "statements on the same line must be separated by ';'",
                self.current.span,
            )

    def parse_program(self) -> Program:
        start = self.current.span
        if self.fragment:
            items: list[Item] = []
            while not self.at("EOF"):
                self.separators()
                if self.at("EOF"):
                    break
                items.append(self.parse_item())
                self.require_item_boundary("EOF")
            module = Module(
                span=_merge(start, self.current.span),
                name="__fragment__",
                parameters=[],
                items=items,
                fragment=True,
            )
            program = Program(
                span=module.span,
                modules=[module],
                source_name=self.source_name,
            )
            assign_node_ids(program)
            return program

        modules: list[Module] = []
        while not self.at("EOF"):
            self.separators()
            if self.at("EOF"):
                break
            modules.append(self.parse_module())
            self.require_item_boundary("EOF")
        if not modules:
            raise ParseError("program must contain at least one module", start)
        program = Program(
            span=_merge(start, self.current.span),
            modules=modules,
            source_name=self.source_name,
        )
        assign_node_ids(program)
        return program

    def parse_module(self) -> Module:
        start = self.expect("module", "expected 'module'").span
        name = self.expect_ident("expected module name").value
        parameters: list[ParamDecl] = []
        if self.accept("(") is not None:
            while not self.at(")"):
                param_start = self.current.span
                self.accept_ident("param")
                param_name = self.expect_ident("expected parameter name").value
                self.expect(":")
                self.expect("int", "module parameters must have type int in v0.1")
                self.expect("=")
                value = self.parse_expression()
                parameters.append(
                    ParamDecl(span=_merge(param_start, value.span), name=param_name, value=value)
                )
                if self.accept(",") is None:
                    break
            self.expect(")")
        self.expect("{")
        items: list[Item] = []
        while not self.at("}"):
            self.separators()
            if self.at("EOF"):
                raise ParseError(f"unterminated module {name!r}", start)
            if self.at("}"):
                break
            items.append(self.parse_item())
            self.require_item_boundary("}", "EOF")
        end = self.expect("}").span
        return Module(
            span=_merge(start, end),
            name=name,
            parameters=parameters,
            items=items,
        )

    def parse_item(self) -> Item:
        if self.at_ident("abstract"):
            return self.parse_abstract()
        if self.at_ident("apply"):
            return self.parse_contract_apply()
        if self.at_ident("domain"):
            return self.parse_domain()
        if self.at_ident("in") or self.at_ident("out"):
            return self.parse_port()
        if self.at_ident("state"):
            return self.parse_state()
        if self.at_ident("const"):
            return self.parse_const()
        if self.at_ident("param"):
            return self.parse_param()
        if self.at_ident("let"):
            return self.parse_let()
        if any(self.at_ident(value) for value in ("assume", "assert", "cover")):
            return self.parse_property()
        if self.current.kind == "IDENT":
            return self.parse_equation()
        raise ParseError(
            f"expected declaration or equation, found {self.current.value!r}", self.current.span
        )

    def parse_abstract(self) -> AbstractDecl:
        start = self.expect("abstract").span
        direction = "out" if self.accept_ident("out") is not None else None
        if self.at_ident("in") or self.at_ident("state"):
            raise ParseError(
                "abstract declarations support internal values or outputs, not inputs/state",
                self.current.span,
            )
        names = self.parse_names()
        self.expect(":")
        type_ref = self.parse_type()
        domain = self.parse_optional_domain()
        end = self.tokens[self.index - 1].span if domain is not None else type_ref.span
        return AbstractDecl(
            span=_merge(start, end),
            names=names,
            type_ref=type_ref,
            direction=direction,
            domain=domain,
        )

    def parse_contract_apply(self) -> ContractApply:
        start = self.expect("apply").span
        contract_id = self.expect_ident("expected contract ID after 'apply'").value
        self.expect("{")
        bindings: list[ContractBinding] = []
        self.separators()
        while not self.at("}"):
            role = self.expect_ident("expected contract role name")
            self.expect(":", "expected ':' after contract role")
            value = self.parse_expression()
            bindings.append(
                ContractBinding(
                    span=_merge(role.span, value.span),
                    role=role.value,
                    value=value,
                )
            )
            self.require_item_boundary("}")
            self.separators()
        end = self.expect("}").span
        return ContractApply(
            span=_merge(start, end),
            contract_id=contract_id,
            bindings=bindings,
        )

    def parse_domain(self) -> DomainDecl:
        start = self.expect("domain").span
        name = self.expect_ident("expected domain name").value
        self.expect("=")
        edge = self.expect_ident("expected posedge or negedge")
        if edge.value not in {"posedge", "negedge"}:
            raise ParseError("domain edge must be posedge or negedge", edge.span)
        clock_token = self.expect_ident("expected domain clock symbol")
        clock = clock_token.value
        reset_mode: str | None = None
        reset: Expr | None = None
        if self.accept(",") is not None:
            if self.at_ident("async") or self.at_ident("sync"):
                reset_mode = self.advance().value
            else:
                reset_mode = "sync"
            self.expect("reset", "expected reset after domain comma")
            reset = self.parse_expression()
        end = reset.span if reset else clock_token.span
        return DomainDecl(
            span=_merge(start, end),
            name=name,
            edge=edge.value,
            clock=clock,
            reset_mode=reset_mode,
            reset=reset,
        )

    def parse_port(self) -> PortDecl:
        start_token = self.advance()
        direction = start_token.value
        is_state = self.accept_ident("state") is not None
        names = self.parse_names()
        self.expect(":")
        type_ref = self.parse_type()
        domain = self.parse_optional_domain()
        reset = self.parse_optional_reset()
        value = self.parse_expression() if self.accept("=") is not None else None
        end = value.span if value else reset.span if reset else type_ref.span
        return PortDecl(
            span=_merge(start_token.span, end),
            direction=direction,
            is_state=is_state,
            names=names,
            type_ref=type_ref,
            domain=domain,
            reset=reset,
            value=value,
        )

    def parse_state(self) -> StateDecl:
        start = self.expect("state").span
        names = self.parse_names()
        self.expect(":")
        type_ref = self.parse_type()
        self.expect("@", "state declaration requires a clock domain")
        domain_token = self.expect_ident("expected state clock domain")
        domain = domain_token.value
        reset = self.parse_optional_reset()
        end = reset.span if reset else domain_token.span
        return StateDecl(
            span=_merge(start, end),
            names=names,
            type_ref=type_ref,
            domain=domain,
            reset=reset,
        )

    def parse_const(self) -> ConstDecl:
        start = self.expect("const").span
        name = self.expect_ident("expected constant name").value
        self.expect(":")
        type_ref = self.parse_type()
        self.expect("=")
        value = self.parse_expression()
        return ConstDecl(
            span=_merge(start, value.span),
            name=name,
            type_ref=type_ref,
            value=value,
        )

    def parse_param(self) -> ParamDecl:
        start = self.expect("param").span
        name = self.expect_ident("expected parameter name").value
        self.expect(":")
        self.expect("int", "parameter type must be int")
        self.expect("=")
        value = self.parse_expression()
        return ParamDecl(span=_merge(start, value.span), name=name, value=value)

    def parse_let(self) -> LetDecl:
        start = self.expect("let").span
        name = self.expect_ident("expected let name").value
        type_ref = None
        if self.accept(":") is not None:
            type_ref = self.parse_type()
        self.expect("=")
        value = self.parse_expression()
        return LetDecl(
            span=_merge(start, value.span),
            name=name,
            type_ref=type_ref,
            value=value,
        )

    def parse_property(self) -> PropertyStmt:
        start_token = self.advance()
        self.expect("@", "property requires an explicit domain")
        domain = self.expect_ident("expected property domain").value
        property_expr = self.parse_expression()
        unless = None
        if self.accept_ident("unless") is not None:
            unless = self.parse_expression()
        end = unless.span if unless else property_expr.span
        return PropertyStmt(
            span=_merge(start_token.span, end),
            kind=start_token.value,
            domain=domain,
            property=property_expr,
            unless=unless,
        )

    def parse_equation(self) -> Equation:
        target_token = self.expect_ident()
        is_next = self.accept("'") is not None
        self.expect("=", "expected '=' in equation")
        value = self.parse_expression()
        return Equation(
            span=_merge(target_token.span, value.span),
            target=target_token.value,
            is_next=is_next,
            value=value,
        )

    def parse_names(self) -> list[str]:
        names = [self.expect_ident().value]
        while self.accept(",") is not None:
            names.append(self.expect_ident().value)
        return names

    def parse_optional_domain(self) -> str | None:
        if self.accept("@") is None:
            return None
        return self.expect_ident("expected clock domain after @").value

    def parse_optional_reset(self) -> ResetClause | None:
        reset_token = self.accept_ident("reset")
        if reset_token is None:
            return None
        value = self.parse_expression(24)
        return ResetClause(span=_merge(reset_token.span, value.span), value=value)

    def parse_type(self) -> TypeRef:
        start = self.current.span
        if self.accept_ident("bit") is not None:
            return TypeRef(span=start, kind="bit")
        if self.accept_ident("int") is not None:
            return TypeRef(span=start, kind="int")
        if self.accept_ident("bits") is not None:
            self.expect("[")
            width = self.parse_expression()
            end = self.expect("]").span
            return TypeRef(span=_merge(start, end), kind="bits", width=width)
        if self.current.kind == "IDENT" and re.fullmatch(r"[us]\d+", self.current.value):
            token = self.advance()
            kind = "uint" if token.value.startswith("u") else "sint"
            raw_width = token.value[1:]
            width = IntExpr(span=token.span, value=int(raw_width), raw=raw_width)
            return TypeRef(span=token.span, kind=kind, width=width)
        if self.at_ident("u") or self.at_ident("s"):
            token = self.advance()
            kind = "uint" if token.value == "u" else "sint"
            self.expect("[")
            width = self.parse_expression()
            end = self.expect("]").span
            return TypeRef(span=_merge(start, end), kind=kind, width=width)
        if self.accept("{") is not None:
            members = [self.expect_ident("expected enum member").value]
            while self.accept(",") is not None:
                members.append(self.expect_ident("expected enum member").value)
            end = self.expect("}").span
            return TypeRef(span=_merge(start, end), kind="enum", members=members)
        raise ParseError("expected Compact SpecIR type", self.current.span)

    def parse_expression(self, minimum_bp: int = 0) -> Expr:
        token = self.advance()
        left = self.parse_prefix(token)
        left = self.parse_postfix(left)

        while True:
            token = self.current
            operator = token.value
            if operator == "?":
                if minimum_bp > 3:
                    break
                self.advance()
                then_expr = self.parse_expression()
                self.expect(":", "expected ':' in conditional expression")
                else_expr = self.parse_expression(3)
                left = TernaryExpr(
                    span=_merge(left.span, else_expr.span),
                    condition=left,
                    then_expr=then_expr,
                    else_expr=else_expr,
                )
                continue
            binding = _BINARY_BINDING_POWER.get(operator)
            if binding is None or binding[0] < minimum_bp:
                break
            self.advance()
            right = self.parse_expression(binding[1])
            expression_type = (
                TemporalBinaryExpr if operator in {"|->", "|=>", "until"} else BinaryExpr
            )
            left = expression_type(
                span=_merge(left.span, right.span), op=operator, left=left, right=right
            )
        return left

    def parse_prefix(self, token: Token) -> Expr:
        if token.kind == "INT":
            return IntExpr(
                span=token.span, value=int(token.value.replace("_", "")), raw=token.value
            )
        if token.kind == "BASED_INT":
            width_text, value_text = token.value.split("'", 1)
            base_code = value_text[0].lower()
            base = {"b": 2, "o": 8, "d": 10, "h": 16}[base_code]
            integer_value = int(value_text[1:].replace("_", ""), base)
            return IntExpr(
                span=token.span,
                value=integer_value,
                raw=token.value,
                width=int(width_text.replace("_", "")),
                base=base,
            )
        if token.value == "?":
            name = None
            if self.current.kind == "IDENT" and self.current.value not in _STATEMENT_KEYWORDS:
                name = self.advance().value
            end = self.tokens[self.index - 1].span
            return HoleExpr(span=_merge(token.span, end), name=name)
        if token.value == "$":
            return UnboundedExpr(span=token.span)
        if token.value in {"!", "~", "-", "+"}:
            operand = self.parse_expression(24)
            return UnaryExpr(span=_merge(token.span, operand.span), op=token.value, operand=operand)
        if token.value in {"always", "eventually"}:
            operand = self.parse_expression(3)
            return TemporalUnaryExpr(
                span=_merge(token.span, operand.span), op=token.value, operand=operand
            )
        if token.value == "##":
            return self.parse_delay(token)
        if token.value == "(":
            grouped = self.parse_expression()
            end = self.expect(")").span
            grouped.span = _merge(token.span, end)
            return grouped
        if token.value == "{":
            values = [self.parse_expression()]
            while self.accept(",") is not None:
                values.append(self.parse_expression())
            end = self.expect("}").span
            return ConcatExpr(span=_merge(token.span, end), values=values)
        if token.kind == "IDENT":
            if token.value in {"case", "priority"} and self.at("{"):
                return self.parse_choice(token)
            if token.value == "hold":
                return HoldExpr(span=token.span)
            if token.value == "none":
                return NoneExpr(span=token.span)
            return NameExpr(span=token.span, name=token.value)
        raise ParseError(f"expected expression, found {token.value!r}", token.span)

    def parse_postfix(self, value: Expr) -> Expr:
        while True:
            if self.accept("(") is not None:
                if not isinstance(value, NameExpr):
                    raise ParseError("only named builtins may be called", value.span)
                args: list[Expr] = []
                if not self.at(")"):
                    args.append(self.parse_expression())
                    while self.accept(",") is not None:
                        args.append(self.parse_expression())
                end = self.expect(")").span
                value = CallExpr(
                    span=_merge(value.span, end),
                    function=value.name,
                    args=args,
                )
                continue
            if self.accept("[") is not None:
                first = self.parse_expression()
                if self.accept(":") is not None:
                    second = self.parse_expression()
                    end = self.expect("]").span
                    value = SliceExpr(
                        span=_merge(value.span, end), value=value, msb=first, lsb=second
                    )
                else:
                    end = self.expect("]").span
                    value = IndexExpr(span=_merge(value.span, end), value=value, index=first)
                continue
            break
        return value

    def parse_choice(self, token: Token) -> ChoiceExpr:
        self.expect("{")
        branches: list[Branch] = []
        else_expr: Expr | None = None
        self.separators()
        while not self.at("}"):
            if self.accept_ident("else") is not None:
                self.expect("->")
                else_expr = self.parse_expression()
                self.require_item_boundary("}")
                self.separators()
                break
            branch_start = self.current.span
            guard = self.parse_expression()
            self.expect("->", "expected '->' after choice guard")
            branch_value = self.parse_expression()
            branches.append(
                Branch(
                    span=_merge(branch_start, branch_value.span),
                    guard=guard,
                    value=branch_value,
                )
            )
            self.require_item_boundary("}")
            self.separators()
        end = self.expect("}").span
        if not branches:
            raise ParseError(f"{token.value} requires at least one branch", token.span)
        return ChoiceExpr(
            span=_merge(token.span, end),
            kind=token.value,
            branches=branches,
            else_expr=else_expr,
        )

    def parse_delay(self, token: Token) -> DelayExpr:
        if self.accept("[") is not None:
            lower = self.parse_expression()
            self.expect(":")
            upper = self.parse_expression()
            self.expect("]")
        else:
            bound = self.expect("INT", "expected delay integer or [lower:upper]")
            lower = IntExpr(span=bound.span, value=int(bound.value), raw=bound.value)
            upper = IntExpr(span=bound.span, value=int(bound.value), raw=bound.value)
        operand = self.parse_expression(3)
        return DelayExpr(
            span=_merge(token.span, operand.span),
            lower=lower,
            upper=upper,
            operand=operand,
        )


def parse(text: str, *, source_name: str = "<input>", fragment: bool = False) -> Program:
    try:
        tokens = lex(text)
    except LexError as exc:
        raise ParseError(exc.message, exc.span) from exc
    return Parser(tokens, source_name, fragment=fragment).parse_program()


def parse_file(path: Path, *, fragment: bool = False) -> Program:
    return parse(path.read_text(encoding="utf-8"), source_name=str(path), fragment=fragment)

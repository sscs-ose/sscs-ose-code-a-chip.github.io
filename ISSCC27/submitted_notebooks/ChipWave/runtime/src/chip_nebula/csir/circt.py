from __future__ import annotations

from dataclasses import dataclass

from .ast import (
    BinaryExpr,
    CallExpr,
    ChoiceExpr,
    ConcatExpr,
    ConstDecl,
    DelayExpr,
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
    UnaryExpr,
    UnboundedExpr,
)
from .semantics import BIT, INT, PROPERTY, CheckResult, Symbol, TypeInfo


class LoweringError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Value:
    name: str
    type_info: TypeInfo
    mlir_type: str


class ModuleEmitter:
    def __init__(self, module: Module, result: CheckResult):
        self.module = module
        self.result = result
        self.symbols = result.symbols[module.name]
        self.lines: list[str] = []
        self.values: dict[str, Value] = {}
        self.definitions: dict[str, Expr] = {}
        self.resolving: set[str] = set()
        self.counter = 0
        self.clock_values: dict[str, Value] = {}
        self.domain_decls = {
            item.name: item for item in module.items if isinstance(item, DomainDecl)
        }
        self.next_equations = {
            item.target: item
            for item in module.items
            if isinstance(item, Equation) and item.is_next
        }

    def fresh(self, hint: str = "v") -> str:
        self.counter += 1
        safe = "".join(char if char.isalnum() or char == "_" else "_" for char in hint)
        return f"%{safe}_{self.counter}"

    def mlir_type(self, type_info: TypeInfo) -> str:
        if type_info.kind == "bit":
            return "i1"
        if type_info.kind in {"bits", "uint", "sint", "enum"} and type_info.width:
            return f"i{type_info.width}"
        raise LoweringError(f"type {type_info.describe()} is not a runtime CIRCT value")

    def emit(self) -> str:
        input_ports: list[str] = []
        output_ports: list[str] = []
        output_names: list[str] = []
        for item in self.module.items:
            if not isinstance(item, PortDecl):
                continue
            for name in item.names:
                symbol = self.symbols[name]
                mlir_type = self.mlir_type(symbol.type_info)
                if item.direction == "in":
                    input_ports.append(f"%{name}: {mlir_type}")
                    self.values[name] = Value(f"%{name}", symbol.type_info, mlir_type)
                elif item.direction == "out":
                    output_ports.append(f"{name}: {mlir_type}")
                    output_names.append(name)
                else:
                    raise LoweringError("inout ports are parsed but not lowerable in v0.1")

        inputs = ", ".join(input_ports)
        output_signature = ", ".join(output_ports)
        header = f"  hw.module @{self.module.name}({inputs}) -> ({output_signature}) {{"

        for name, symbol in self.symbols.items():
            if symbol.is_state:
                self.values[name] = Value(
                    f"%{name}", symbol.type_info, self.mlir_type(symbol.type_info)
                )

        for item in self.module.items:
            if isinstance(item, LetDecl | ConstDecl):
                self.definitions[item.name] = item.value
            elif isinstance(item, Equation) and not item.is_next:
                self.definitions[item.target] = item.value
            elif isinstance(item, PortDecl) and item.value is not None:
                for name in item.names:
                    self.definitions[name] = item.value

        self.emit_domain_clocks()
        self.emit_states()
        for name in self.definitions:
            self.resolve_name(name)
        self.emit_properties()

        output_values = [self.resolve_name(name) for name in output_names]
        if output_values:
            operands = ", ".join(value.name for value in output_values)
            types = ", ".join(value.mlir_type for value in output_values)
            self.lines.append(f"    hw.output {operands} : {types}")
        else:
            self.lines.append("    hw.output")
        return "\n".join([header, *self.lines, "  }"])

    def emit_domain_clocks(self) -> None:
        for domain in self.domain_decls.values():
            clock = self.resolve_name(domain.clock)
            clock_wire = clock
            if domain.edge == "negedge":
                one = self.constant(1, BIT)
                inverted = Value(self.fresh(f"{domain.name}_nclk"), BIT, "i1")
                self.lines.append(f"    {inverted.name} = comb.xor {clock.name}, {one.name} : i1")
                clock_wire = inverted
            result = Value(self.fresh(f"{domain.name}_clk"), TypeInfo("clock"), "!seq.clock")
            self.lines.append(f"    {result.name} = seq.to_clock {clock_wire.name}")
            self.clock_values[domain.name] = result

    def emit_states(self) -> None:
        register_lines: list[str] = []
        for name, symbol in self.symbols.items():
            if not symbol.is_state:
                continue
            equation = self.next_equations.get(name)
            if equation is None:
                raise LoweringError(f"state {name!r} has no next equation")
            domain_name = symbol.domain or self.infer_single_domain()
            if domain_name is None or domain_name not in self.domain_decls:
                raise LoweringError(f"state {name!r} has no lowerable domain")
            next_value = self.lower_expr(
                equation.value,
                expected=symbol.type_info,
                hold=self.values[name],
                domain=domain_name,
            )
            domain = self.domain_decls[domain_name]
            clock = self.clock_values[domain_name]
            reset_clause = self.state_reset(symbol)
            reset_operands = ""
            attributes = ""
            if reset_clause is not None and not isinstance(reset_clause, NoneExpr):
                if isinstance(reset_clause, HoleExpr):
                    raise LoweringError(f"state {name!r} reset contains a semantic hole")
                if domain.reset is None:
                    raise LoweringError(
                        f"state {name!r} has a reset value but domain {domain_name!r} has no reset"
                    )
                reset_condition = self.lower_expr(domain.reset, expected=BIT, domain=domain_name)
                reset_value = self.lower_expr(
                    reset_clause,
                    expected=symbol.type_info,
                    domain=domain_name,
                )
                reset_operands = f" reset {reset_condition.name}, {reset_value.name}"
                style = domain.reset_mode or "sync"
                attributes = f' {{specir.resetStyle = "{style}"}}'
            register_lines.append(
                f"    %{name} = seq.compreg {next_value.name}, {clock.name}"
                f"{reset_operands}{attributes} : {self.mlir_type(symbol.type_info)}"
            )
        self.lines.extend(register_lines)

    def state_reset(self, symbol: Symbol) -> Expr | None:
        node = symbol.node
        if isinstance(node, PortDecl | StateDecl) and node.reset is not None:
            return node.reset.value
        return None

    def emit_properties(self) -> None:
        for item in self.module.items:
            if not isinstance(item, PropertyStmt):
                continue
            domain = self.domain_decls[item.domain]
            property_value = self.lower_property(item.property, item.domain)
            clocked_name = self.fresh(f"{item.kind}_clocked")
            if property_value.mlir_type == "i1":
                self.lines.append(
                    f"    {clocked_name} = ltl.clocked_atom {property_value.name}, "
                    f"{domain.edge} %{domain.clock} : i1"
                )
                property_value = Value(clocked_name, TypeInfo("sequence"), "!ltl.sequence")
            else:
                self.lines.append(
                    f"    {clocked_name} = ltl.clock {property_value.name}, "
                    f"{domain.edge} %{domain.clock} : {property_value.mlir_type}"
                )
                property_value = Value(clocked_name, PROPERTY, property_value.mlir_type)

            enable = ""
            if item.unless is not None:
                unless = self.lower_expr(
                    self.expand_reset_pseudo(item.unless, item.domain),
                    expected=BIT,
                    domain=item.domain,
                )
                enabled = Value(self.fresh("property_enable"), BIT, "i1")
                one = self.constant(1, BIT)
                self.lines.append(f"    {enabled.name} = comb.xor {unless.name}, {one.name} : i1")
                enable = f" if {enabled.name}"
            operation = {
                "assert": "verif.assert",
                "assume": "verif.assume",
                "cover": "verif.cover",
            }[item.kind]
            self.lines.append(
                f"    {operation} {property_value.name}{enable} "
                f'label "{item.node_id}" : {property_value.mlir_type}'
            )

    def expand_reset_pseudo(self, expr: Expr, domain_name: str) -> Expr:
        if isinstance(expr, NameExpr) and expr.name == "reset":
            domain = self.domain_decls[domain_name]
            if domain.reset is None:
                raise LoweringError(f"domain {domain_name!r} has no reset expression")
            return domain.reset
        return expr

    def infer_single_domain(self) -> str | None:
        return next(iter(self.domain_decls)) if len(self.domain_decls) == 1 else None

    def resolve_name(self, name: str) -> Value:
        existing = self.values.get(name)
        if existing is not None:
            return existing
        symbol = self.symbols.get(name)
        if symbol is None:
            raise LoweringError(f"undefined value {name!r}")
        if symbol.enum_value is not None:
            value = self.constant(symbol.enum_value, symbol.type_info)
            self.values[name] = value
            return value
        if symbol.type_info == INT:
            node = symbol.node
            if not isinstance(node, ParamDecl):
                raise LoweringError(f"compile-time symbol {name!r} has no constant expression")
            constant = self.eval_const(node.value)
            if constant is None:
                raise LoweringError(f"compile-time symbol {name!r} is not constant")
            raise LoweringError(
                f"compile-time parameter {name!r} requires a contextual hardware type"
            )
        expression = self.definitions.get(name)
        if expression is None:
            raise LoweringError(f"symbol {name!r} has no runtime value")
        if name in self.resolving:
            raise LoweringError(f"combinational cycle while lowering {name!r}")
        self.resolving.add(name)
        value = self.lower_expr(expression, expected=symbol.type_info, domain=symbol.domain)
        self.resolving.remove(name)
        self.values[name] = value
        return value

    def eval_const(self, expr: Expr) -> int | None:
        if isinstance(expr, IntExpr):
            return expr.value
        if isinstance(expr, NameExpr):
            symbol = self.symbols.get(expr.name)
            if symbol and isinstance(symbol.node, ParamDecl):
                return self.eval_const(symbol.node.value)
            return None
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
            functions = {
                "+": lambda: left + right,
                "-": lambda: left - right,
                "*": lambda: left * right,
                "/": lambda: left // right,
                "%": lambda: left % right,
                "<<": lambda: left << right,
                ">>": lambda: left >> right,
            }
            return functions[expr.op]() if expr.op in functions else None
        return None

    def constant(self, value: int, type_info: TypeInfo) -> Value:
        mlir_type = self.mlir_type(type_info)
        result = Value(self.fresh("c"), type_info, mlir_type)
        self.lines.append(f"    {result.name} = hw.constant {value} : {mlir_type}")
        return result

    def lower_name(self, expr: NameExpr, expected: TypeInfo | None) -> Value:
        symbol = self.symbols.get(expr.name)
        if symbol and symbol.type_info == INT:
            value = self.eval_const(expr)
            if value is None or expected is None or not expected.is_hardware:
                raise LoweringError(
                    f"compile-time constant {expr.name!r} lacks a hardware type context"
                )
            return self.constant(value, expected)
        return self.resolve_name(expr.name)

    def lower_expr(
        self,
        expr: Expr,
        *,
        expected: TypeInfo | None = None,
        hold: Value | None = None,
        domain: str | None = None,
    ) -> Value:
        inferred = self.result.expression_types.get(id(expr), expected)
        if isinstance(expr, NameExpr):
            return self.lower_name(expr, expected or inferred)
        if isinstance(expr, IntExpr):
            type_info = expected or inferred
            if type_info is None or type_info == INT:
                if expr.width is None:
                    raise LoweringError(f"literal {expr.raw} lacks a hardware type context")
                type_info = TypeInfo("bits", expr.width)
            return self.constant(expr.value, type_info)
        if isinstance(expr, HoldExpr):
            if hold is None:
                raise LoweringError("hold has no next-state context")
            return hold
        if isinstance(expr, HoleExpr):
            raise LoweringError("cannot lower a semantic hole")
        if isinstance(expr, NoneExpr | UnboundedExpr):
            raise LoweringError(f"cannot lower {type(expr).__name__} as a runtime value")
        if isinstance(expr, UnaryExpr):
            operand = self.lower_expr(expr.operand, expected=inferred, hold=hold, domain=domain)
            if expr.op == "+":
                return operand
            if expr.op in {"!", "~"}:
                mask = 1 if operand.mlir_type == "i1" else (1 << (operand.type_info.width or 1)) - 1
                constant = self.constant(mask, operand.type_info)
                result = Value(self.fresh("not"), operand.type_info, operand.mlir_type)
                self.lines.append(
                    f"    {result.name} = comb.xor {operand.name}, {constant.name} "
                    f": {operand.mlir_type}"
                )
                return result
            zero = self.constant(0, operand.type_info)
            result = Value(self.fresh("neg"), operand.type_info, operand.mlir_type)
            self.lines.append(
                f"    {result.name} = comb.sub {zero.name}, {operand.name} : {operand.mlir_type}"
            )
            return result
        if isinstance(expr, BinaryExpr):
            return self.lower_binary(expr, expected=inferred, hold=hold, domain=domain)
        if isinstance(expr, TernaryExpr):
            condition = self.lower_expr(expr.condition, expected=BIT, domain=domain)
            result_type = inferred or expected
            then_value = self.lower_expr(
                expr.then_expr, expected=result_type, hold=hold, domain=domain
            )
            else_value = self.lower_expr(
                expr.else_expr, expected=result_type, hold=hold, domain=domain
            )
            result = Value(self.fresh("mux"), then_value.type_info, then_value.mlir_type)
            self.lines.append(
                f"    {result.name} = comb.mux {condition.name}, {then_value.name}, "
                f"{else_value.name} : {then_value.mlir_type}"
            )
            return result
        if isinstance(expr, ChoiceExpr):
            if expr.else_expr is None:
                # Static semantics proved coverage. The final branch is a legal
                # deterministic fallback outside the constrained environment.
                current = self.lower_expr(
                    expr.branches[-1].value,
                    expected=expected or inferred,
                    hold=hold,
                    domain=domain,
                )
                remaining_branches = expr.branches[:-1]
            else:
                current = self.lower_expr(
                    expr.else_expr, expected=expected or inferred, hold=hold, domain=domain
                )
                remaining_branches = expr.branches
            for branch in reversed(remaining_branches):
                guard = self.lower_expr(branch.guard, expected=BIT, domain=domain)
                branch_value = self.lower_expr(
                    branch.value,
                    expected=expected or inferred,
                    hold=hold,
                    domain=domain,
                )
                result = Value(self.fresh(expr.kind), current.type_info, current.mlir_type)
                self.lines.append(
                    f"    {result.name} = comb.mux {guard.name}, {branch_value.name}, "
                    f"{current.name} : {current.mlir_type}"
                )
                current = result
            return current
        if isinstance(expr, CallExpr):
            return self.lower_call(expr, domain=domain)
        if isinstance(expr, IndexExpr):
            index = self.eval_const(expr.index)
            value = self.lower_expr(expr.value, domain=domain)
            if index is None:
                dynamic_index = self.lower_expr(expr.index, domain=domain)
                value_width = value.type_info.width or 1
                index_width = dynamic_index.type_info.width or 1
                if index_width < value_width:
                    high = self.constant(0, TypeInfo("bits", value_width - index_width))
                    resized = Value(
                        self.fresh("index_zext"), TypeInfo("bits", value_width), f"i{value_width}"
                    )
                    self.lines.append(
                        f"    {resized.name} = comb.concat {high.name}, {dynamic_index.name} "
                        f": {high.mlir_type}, {dynamic_index.mlir_type}"
                    )
                    dynamic_index = resized
                elif index_width > value_width:
                    resized = Value(
                        self.fresh("index_trunc"),
                        TypeInfo("bits", value_width),
                        f"i{value_width}",
                    )
                    self.lines.append(
                        f"    {resized.name} = comb.extract {dynamic_index.name} from 0 : "
                        f"({dynamic_index.mlir_type}) -> {resized.mlir_type}"
                    )
                    dynamic_index = resized
                shifted = Value(self.fresh("index_shift"), value.type_info, value.mlir_type)
                self.lines.append(
                    f"    {shifted.name} = comb.shru {value.name}, {dynamic_index.name} "
                    f": {value.mlir_type}"
                )
                value = shifted
                index = 0
            result = Value(self.fresh("bit"), BIT, "i1")
            self.lines.append(
                f"    {result.name} = comb.extract {value.name} from {index} : "
                f"({value.mlir_type}) -> i1"
            )
            return result
        if isinstance(expr, SliceExpr):
            msb = self.eval_const(expr.msb)
            lsb = self.eval_const(expr.lsb)
            if msb is None or lsb is None:
                raise LoweringError("dynamic slice lowering is not supported")
            value = self.lower_expr(expr.value, domain=domain)
            result_type = TypeInfo("bits", msb - lsb + 1)
            result = Value(self.fresh("slice"), result_type, self.mlir_type(result_type))
            self.lines.append(
                f"    {result.name} = comb.extract {value.name} from {lsb} : "
                f"({value.mlir_type}) -> {result.mlir_type}"
            )
            return result
        if isinstance(expr, ConcatExpr):
            values = [self.lower_expr(value, domain=domain) for value in expr.values]
            width = sum(value.type_info.width or 0 for value in values)
            result_type = TypeInfo("bits", width)
            result = Value(self.fresh("concat"), result_type, self.mlir_type(result_type))
            self.lines.append(
                f"    {result.name} = comb.concat {', '.join(value.name for value in values)} "
                f": {', '.join(value.mlir_type for value in values)}"
            )
            return result
        raise LoweringError(f"expression {type(expr).__name__} requires temporal lowering")

    def lower_binary(
        self,
        expr: BinaryExpr,
        *,
        expected: TypeInfo | None,
        hold: Value | None,
        domain: str | None,
    ) -> Value:
        common = self.result.expression_types.get(id(expr.left))
        if common == INT:
            common = self.result.expression_types.get(id(expr.right))
        common = common or expected
        left = self.lower_expr(expr.left, expected=common, hold=hold, domain=domain)
        right = self.lower_expr(expr.right, expected=common, hold=hold, domain=domain)
        if expr.op in {"==", "!=", "<", "<=", ">", ">="}:
            signed = left.type_info.kind == "sint"
            predicates = {
                "==": "eq",
                "!=": "ne",
                "<": "slt" if signed else "ult",
                "<=": "sle" if signed else "ule",
                ">": "sgt" if signed else "ugt",
                ">=": "sge" if signed else "uge",
            }
            result = Value(self.fresh("cmp"), BIT, "i1")
            self.lines.append(
                f"    {result.name} = comb.icmp {predicates[expr.op]} {left.name}, "
                f"{right.name} : {left.mlir_type}"
            )
            return result
        operations = {
            "&&": "and",
            "||": "or",
            "&": "and",
            "|": "or",
            "^": "xor",
            "+": "add",
            "-": "sub",
            "*": "mul",
            "/": "divs" if left.type_info.kind == "sint" else "divu",
            "%": "mods" if left.type_info.kind == "sint" else "modu",
            "<<": "shl",
            ">>": "shrs" if left.type_info.kind == "sint" else "shru",
        }
        result_type = BIT if expr.op in {"&&", "||"} else left.type_info
        result = Value(self.fresh(operations[expr.op]), result_type, self.mlir_type(result_type))
        self.lines.append(
            f"    {result.name} = comb.{operations[expr.op]} {left.name}, {right.name} "
            f": {left.mlir_type}"
        )
        return result

    def lower_call(self, expr: CallExpr, *, domain: str | None) -> Value:
        if expr.function in {"zext", "sext", "trunc"}:
            value = self.lower_expr(expr.args[0], domain=domain)
            width = self.eval_const(expr.args[1])
            if width is None:
                raise LoweringError("conversion width is not constant")
            result_type = self.result.expression_types[id(expr)]
            if expr.function == "trunc":
                result = Value(self.fresh("trunc"), result_type, self.mlir_type(result_type))
                self.lines.append(
                    f"    {result.name} = comb.extract {value.name} from 0 : "
                    f"({value.mlir_type}) -> {result.mlir_type}"
                )
                return result
            extension = width - (value.type_info.width or 0)
            if extension == 0:
                return Value(value.name, result_type, value.mlir_type)
            if expr.function == "zext":
                high = self.constant(0, TypeInfo("bits", extension))
            else:
                sign = Value(self.fresh("sign"), BIT, "i1")
                self.lines.append(
                    f"    {sign.name} = comb.extract {value.name} from "
                    f"{(value.type_info.width or 1) - 1} : ({value.mlir_type}) -> i1"
                )
                high = sign
                if extension > 1:
                    high = Value(
                        self.fresh("sign_fill"),
                        TypeInfo("bits", extension),
                        f"i{extension}",
                    )
                    self.lines.append(
                        f"    {high.name} = comb.replicate {sign.name} : (i1) -> {high.mlir_type}"
                    )
                result = Value(self.fresh("sext"), result_type, self.mlir_type(result_type))
                self.lines.append(
                    f"    {result.name} = comb.concat {high.name}, {value.name} : "
                    f"{high.mlir_type}, {value.mlir_type}"
                )
                return result
            result = Value(self.fresh("zext"), result_type, self.mlir_type(result_type))
            self.lines.append(
                f"    {result.name} = comb.concat {high.name}, {value.name} : "
                f"{high.mlir_type}, {value.mlir_type}"
            )
            return result
        if expr.function in {"as_u", "as_s"}:
            value = self.lower_expr(expr.args[0], domain=domain)
            return Value(value.name, self.result.expression_types[id(expr)], value.mlir_type)
        if expr.function in {"rose", "fell", "stable", "changed"}:
            if domain is None:
                raise LoweringError(f"sampled builtin {expr.function} requires a domain")
            value = self.lower_expr(expr.args[0], domain=domain)
            previous = Value(self.fresh(f"past_{expr.function}"), value.type_info, value.mlir_type)
            clock = self.clock_values[domain]
            self.lines.append(
                f"    {previous.name} = seq.compreg {value.name}, {clock.name} : {value.mlir_type}"
            )
            if expr.function in {"stable", "changed"}:
                comparison = "eq" if expr.function == "stable" else "ne"
                result = Value(self.fresh(expr.function), BIT, "i1")
                self.lines.append(
                    f"    {result.name} = comb.icmp {comparison} {value.name}, "
                    f"{previous.name} : {value.mlir_type}"
                )
                return result
            if value.type_info != BIT:
                raise LoweringError(f"{expr.function} currently requires a bit operand")
            one = self.constant(1, BIT)
            inverted = Value(self.fresh("not_sample"), BIT, "i1")
            invert_operand = previous if expr.function == "rose" else value
            other = value if expr.function == "rose" else previous
            self.lines.append(
                f"    {inverted.name} = comb.xor {invert_operand.name}, {one.name} : i1"
            )
            result = Value(self.fresh(expr.function), BIT, "i1")
            self.lines.append(f"    {result.name} = comb.and {other.name}, {inverted.name} : i1")
            return result
        if expr.function == "past":
            if domain is None:
                raise LoweringError("past requires a domain")
            value = self.lower_expr(expr.args[0], domain=domain)
            count = self.eval_const(expr.args[1])
            if count is None:
                raise LoweringError("past count is not constant")
            current = value
            for _ in range(count):
                previous = Value(self.fresh("past"), value.type_info, value.mlir_type)
                self.lines.append(
                    f"    {previous.name} = seq.compreg {current.name}, "
                    f"{self.clock_values[domain].name} : {value.mlir_type}"
                )
                current = previous
            return current
        raise LoweringError(f"unsupported call {expr.function!r}")

    def lower_property(self, expr: Expr, domain: str) -> Value:
        if isinstance(expr, TemporalUnaryExpr):
            operand = self.lower_property(expr.operand, domain)
            if expr.op == "eventually":
                result = Value(self.fresh(expr.op), PROPERTY, "!ltl.property")
                operation = "ltl.eventually"
                suffix = ""
            else:
                result = Value(self.fresh(expr.op), TypeInfo("sequence"), "!ltl.sequence")
                operation = "ltl.repeat"
                suffix = ", 0"
            self.lines.append(
                f"    {result.name} = {operation} {operand.name}{suffix} : {operand.mlir_type}"
            )
            return result
        if isinstance(expr, TemporalBinaryExpr):
            left = self.lower_property(expr.left, domain)
            right = self.lower_property(expr.right, domain)
            if expr.op == "until":
                if left.mlir_type != right.mlir_type:
                    raise LoweringError("until operands must lower to the same CIRCT type")
                result = Value(self.fresh("until"), PROPERTY, "!ltl.property")
                self.lines.append(
                    f"    {result.name} = ltl.until {left.name}, {right.name} : {left.mlir_type}"
                )
                return result
            if expr.op == "|=>":
                true_value = self.constant(1, BIT)
                delayed = Value(
                    self.fresh("nonoverlap_delay"),
                    TypeInfo("sequence"),
                    "!ltl.sequence",
                )
                self.lines.append(f"    {delayed.name} = ltl.delay {true_value.name}, 1, 0 : i1")
                antecedent = Value(
                    self.fresh("nonoverlap_antecedent"),
                    TypeInfo("sequence"),
                    "!ltl.sequence",
                )
                self.lines.append(
                    f"    {antecedent.name} = ltl.concat {left.name}, {delayed.name} "
                    f": !ltl.sequence"
                )
                left = antecedent
            result = Value(self.fresh("implication"), PROPERTY, "!ltl.property")
            self.lines.append(
                f"    {result.name} = ltl.implication {left.name}, {right.name} : !ltl.property"
            )
            return result
        if isinstance(expr, DelayExpr):
            lower = self.eval_const(expr.lower)
            if lower is None:
                raise LoweringError("delay lower bound is unresolved")
            operand = self.lower_property(expr.operand, domain)
            if isinstance(expr.upper, UnboundedExpr):
                bounds = f", {lower}"
            else:
                upper = self.eval_const(expr.upper)
                if upper is None:
                    raise LoweringError("delay upper bound is unresolved")
                bounds = f", {lower}, {upper - lower}"
            result = Value(self.fresh("delay"), TypeInfo("sequence"), "!ltl.sequence")
            self.lines.append(
                f"    {result.name} = ltl.delay {operand.name}{bounds} : {operand.mlir_type}"
            )
            return result
        return self.lower_expr(expr, expected=BIT, domain=domain)


def emit_circt(program: Program, result: CheckResult) -> str:
    if result.has_blocking_diagnostics:
        raise LoweringError("cannot lower a program with unresolved or invalid semantics")
    if result.abstract_symbols:
        raise LoweringError(
            "cannot lower abstract semantics before refinement: "
            + ", ".join(result.abstract_symbols)
        )
    modules = [ModuleEmitter(module, result).emit() for module in program.modules]
    return "module {\n" + "\n\n".join(modules) + "\n}\n"

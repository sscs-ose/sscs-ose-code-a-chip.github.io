from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import textwrap
from pathlib import Path
from typing import Any

from . import __version__
from .ast import ContractApply, Diagnostic, Severity, iter_nodes, to_dict
from .circt import LoweringError, emit_circt
from .contracts import dump_contracts, load_contracts, validate_contracts
from .elaboration import elaborate
from .parser import ParseError, parse_file
from .printer import format_program
from .provenance import dump_sidecar, empty_sidecar, load_sidecar, validate_sidecar
from .semantics import CheckResult, check, diagnostic_to_dict, semantics_fingerprint

_NOTE_GROUP_LABELS = {
    "N-CONTRACT-ADAPTER-REQUIRED": "verification adapters required",
    "N-CONTRACT-MANUAL": "manual/external verification required",
}
_CONTRACT_NOTE_SUBJECT = re.compile(r"^contract '([^']+)'")


def _common_input(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source", type=Path, help="Compact SpecIR source file")
    parser.add_argument(
        "--fragment",
        action="store_true",
        help="parse declarations/statements without a module wrapper",
    )


def _common_check(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provenance", type=Path, help="provenance sidecar JSON")
    parser.add_argument("--contracts", type=Path, help="external contract sidecar JSON")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="show individual note diagnostics instead of only their final count",
    )
    parser.add_argument(
        "--no-solver",
        action="store_true",
        help="skip SMT checks and emit conservative choice warnings",
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="specir",
        description="Compact SpecIR v0.1 parser, checker, and CIRCT lowering PoC.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_parser = subparsers.add_parser("parse", help="parse source and print source AST JSON")
    _common_input(parse_parser)
    parse_parser.add_argument("-o", "--output", type=Path)

    check_parser = subparsers.add_parser("check", help="run deterministic static semantics")
    _common_input(check_parser)
    _common_check(check_parser)
    check_parser.add_argument("--format", choices=("text", "json"), default="text")

    elaborate_parser = subparsers.add_parser(
        "elaborate", help="print the checked, resolved semantic projection as JSON"
    )
    _common_input(elaborate_parser)
    _common_check(elaborate_parser)
    elaborate_parser.add_argument("-o", "--output", type=Path)

    fmt_parser = subparsers.add_parser("fmt", help="print or write canonical textual form")
    _common_input(fmt_parser)
    fmt_group = fmt_parser.add_mutually_exclusive_group()
    fmt_group.add_argument("-w", "--write", action="store_true", help="rewrite source in place")
    fmt_group.add_argument("--check", action="store_true", help="fail if source is not canonical")

    build_parser = subparsers.add_parser("build", help="build replayable compiler artifacts")
    _common_input(build_parser)
    _common_check(build_parser)
    build_parser.add_argument("--out", type=Path, required=True, help="artifact directory")
    build_parser.add_argument(
        "--signoff",
        action="store_true",
        help="fail unless specification semantics and contract declarations are complete",
    )

    emit_parser = subparsers.add_parser("emit-circt", help="lower checked SpecIR to CIRCT MLIR")
    _common_input(emit_parser)
    _common_check(emit_parser)
    emit_parser.add_argument("-o", "--output", type=Path)

    nodes_parser = subparsers.add_parser("nodes", help="list stable semantic node IDs")
    _common_input(nodes_parser)
    nodes_parser.add_argument("--format", choices=("text", "json"), default="text")

    provenance_parser = subparsers.add_parser(
        "init-provenance", help="create an empty provenance sidecar keyed by stable node IDs"
    )
    _common_input(provenance_parser)
    provenance_parser.add_argument("-o", "--output", type=Path, required=True)
    return parser


def _write_or_print(text: str, output: Path | None) -> None:
    if output is None:
        print(text, end="")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _load_and_check(args: argparse.Namespace) -> tuple[Any, CheckResult, list[Diagnostic]]:
    program = parse_file(args.source, fragment=args.fragment)
    result = check(program, solver=not getattr(args, "no_solver", False))
    diagnostics = list(result.diagnostics)
    provenance_data: dict[str, Any] | None = None
    provenance_path: Path | None = getattr(args, "provenance", None)
    if provenance_path is not None:
        provenance_data = load_sidecar(provenance_path)
        provenance = validate_sidecar(program, provenance_data)
        diagnostics.extend(provenance.diagnostics)
    requirement_ids: set[str] | None = None
    requirement_contracts: dict[str, set[str]] | None = None
    if provenance_data is not None and isinstance(provenance_data.get("requirements"), list):
        requirement_ids = {
            item["id"]
            for item in provenance_data["requirements"]
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        requirement_contracts = {
            item["id"]: {
                contract_id
                for contract_id in item.get("mapped_contracts", [])
                if isinstance(contract_id, str)
            }
            for item in provenance_data["requirements"]
            if isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and isinstance(item.get("mapped_contracts", []), list)
        }
    contracts_path: Path | None = getattr(args, "contracts", None)
    contracts_data = load_contracts(contracts_path) if contracts_path is not None else None
    contracts = validate_contracts(
        program,
        result,
        contracts_data,
        requirement_ids=requirement_ids,
        requirement_contracts=requirement_contracts,
        adapter_base=contracts_path.parent if contracts_path is not None else None,
        source_name=str(contracts_path) if contracts_path is not None else None,
    )
    diagnostics.extend(contracts.diagnostics)
    diagnostics.sort(key=lambda item: (item.span.line, item.span.column, item.code))
    return program, result, diagnostics


def _diagnostics_json(diagnostics: list[Diagnostic], source: Path) -> list[dict[str, Any]]:
    return [diagnostic_to_dict(item, str(source)) for item in diagnostics]


def _render_diagnostic(diagnostic: Diagnostic, source: Path) -> str:
    diagnostic_source = Path(diagnostic.source_name) if diagnostic.source_name else source
    location = f"{diagnostic_source}:{diagnostic.span.line}:{diagnostic.span.column}"
    heading = diagnostic.severity.value.capitalize()
    rendered = [
        f"{heading}-[{diagnostic.code}]",
        f"  Message: {diagnostic.message}",
        f"  Location: {location}",
    ]
    try:
        lines = diagnostic_source.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    if 1 <= diagnostic.span.line <= len(lines):
        source_line = lines[diagnostic.span.line - 1]
        rendered.append(f"  {source_line}")
        width = max(1, diagnostic.span.end_column - diagnostic.span.column)
        rendered.append("  " + " " * (diagnostic.span.column - 1) + "^" * width)
    for note in diagnostic.notes:
        rendered.append(f"  Note: {note}")
    if diagnostic.witness:
        witness = ", ".join(f"{name}={value}" for name, value in diagnostic.witness.items())
        rendered.append(f"  Witness: {witness}")
    return "\n".join(rendered)


def _print_diagnostics(
    diagnostics: list[Diagnostic], source: Path, *, verbose: bool = False
) -> None:
    detailed_count = 0
    for diagnostic in diagnostics:
        if diagnostic.severity == Severity.NOTE and not verbose:
            continue
        print()
        print(_render_diagnostic(diagnostic, source))
        detailed_count += 1
    notes = [item for item in diagnostics if item.severity == Severity.NOTE]
    if notes and not verbose:
        if detailed_count:
            print()
        grouped: dict[str, list[str]] = {}
        for diagnostic in notes:
            match = _CONTRACT_NOTE_SUBJECT.match(diagnostic.message)
            subject = match.group(1) if match is not None else diagnostic.message
            grouped.setdefault(diagnostic.code, []).append(subject)
        print("Note summary:")
        for code in sorted(grouped):
            subjects = sorted(dict.fromkeys(grouped[code]))
            label = _NOTE_GROUP_LABELS.get(code, "additional information")
            print(f"  {label} ({len(grouped[code])}) [{code}]:")
            print(
                textwrap.fill(
                    ", ".join(subjects),
                    width=100,
                    initial_indent="    ",
                    subsequent_indent="    ",
                )
            )
    error_count = sum(item.severity == Severity.ERROR for item in diagnostics)
    warning_count = sum(item.severity == Severity.WARNING for item in diagnostics)
    note_count = sum(item.severity == Severity.NOTE for item in diagnostics)
    if detailed_count or notes:
        print()
    print(f"{error_count} Error(s), {warning_count} Warning(s), {note_count} Note(s)")


def command_parse(args: argparse.Namespace) -> int:
    program = parse_file(args.source, fragment=args.fragment)
    _write_or_print(_json(to_dict(program)), args.output)
    return 0


def command_check(args: argparse.Namespace) -> int:
    _program, _result, diagnostics = _load_and_check(args)
    if args.format == "json":
        print(_json(_diagnostics_json(diagnostics, args.source)), end="")
    else:
        _print_diagnostics(diagnostics, args.source, verbose=args.verbose)
    return 1 if any(item.severity == Severity.ERROR for item in diagnostics) else 0


def command_elaborate(args: argparse.Namespace) -> int:
    program, result, diagnostics = _load_and_check(args)
    if any(item.severity == Severity.ERROR for item in diagnostics):
        _print_diagnostics(diagnostics, args.source, verbose=args.verbose)
        return 1
    _write_or_print(_json(elaborate(program, result)), args.output)
    return 0


def command_fmt(args: argparse.Namespace) -> int:
    program = parse_file(args.source, fragment=args.fragment)
    formatted = format_program(program)
    original = args.source.read_text(encoding="utf-8")
    if args.check:
        if original != formatted:
            print(f"{args.source}: not in canonical Compact SpecIR format", file=sys.stderr)
            return 1
        return 0
    if args.write:
        args.source.write_text(formatted, encoding="utf-8")
    else:
        print(formatted, end="")
    return 0


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_build(args: argparse.Namespace) -> int:
    program, result, diagnostics = _load_and_check(args)
    output: Path = args.out
    output.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, Path] = {
        "canonical": output / "canonical.specir",
        "ast": output / "ast.json",
        "diagnostics": output / "diagnostics.json",
        "nodes": output / "nodes.json",
        "provenance_template": output / "provenance.template.json",
        "elaborated": output / "elaborated.json",
    }
    artifacts["canonical"].write_text(format_program(program), encoding="utf-8")
    artifacts["ast"].write_text(_json(to_dict(program)), encoding="utf-8")
    artifacts["diagnostics"].write_text(
        _json(_diagnostics_json(diagnostics, args.source)), encoding="utf-8"
    )
    artifacts["nodes"].write_text(_json(_node_records(program)), encoding="utf-8")
    artifacts["provenance_template"].write_text(
        dump_sidecar(empty_sidecar(program)), encoding="utf-8"
    )
    artifacts["elaborated"].write_text(_json(elaborate(program, result)), encoding="utf-8")
    provenance_path: Path | None = getattr(args, "provenance", None)
    if provenance_path is not None:
        artifacts["provenance"] = output / "provenance.json"
        artifacts["provenance"].write_text(
            dump_sidecar(load_sidecar(provenance_path)), encoding="utf-8"
        )
    else:
        stale_provenance = output / "provenance.json"
        if stale_provenance.exists():
            stale_provenance.unlink()
    contracts_path: Path | None = getattr(args, "contracts", None)
    if contracts_path is not None:
        artifacts["contracts"] = output / "contracts.json"
        artifacts["contracts"].write_text(
            dump_contracts(load_contracts(contracts_path)), encoding="utf-8"
        )
    else:
        stale_contracts = output / "contracts.json"
        if stale_contracts.exists():
            stale_contracts.unlink()

    has_errors = any(item.severity == Severity.ERROR for item in diagnostics)
    has_blocking = has_errors or any(item.code == "W-CHOICE-NOT-PROVEN" for item in diagnostics)
    has_abstracts = bool(result.abstract_symbols)
    lowering_ready = not has_blocking and not has_abstracts and not args.fragment
    circt_path = output / "design.mlir"
    if lowering_ready:
        artifacts["circt"] = output / "design.mlir"
        artifacts["circt"].write_text(emit_circt(program, result), encoding="utf-8")
    elif circt_path.exists():
        circt_path.unlink()

    manifest = {
        "schema_version": "0.1",
        "tool_version": __version__,
        "source": str(args.source),
        "source_sha256": _hash_file(args.source),
        "semantic_sha256": semantics_fingerprint(program),
        "solver_enabled": not args.no_solver,
        "signoff_requested": args.signoff,
        "signoff_passed": not has_blocking,
        "spec_signoff_passed": not has_blocking,
        "rtl_lowering_ready": lowering_ready,
        "verification_contracts_ready": not any(
            item.code in {"N-CONTRACT-ADAPTER-REQUIRED", "N-CONTRACT-MANUAL"}
            or item.code.startswith("E-CONTRACT-")
            or item.code == "E-ABSTRACT-UNCONSTRAINED"
            for item in diagnostics
        ),
        "abstract_symbols": list(result.abstract_symbols),
        "contract_applications": [
            {
                "module": module.name,
                "contract_id": item.contract_id,
                "node_id": item.node_id,
            }
            for module in program.modules
            for item in module.items
            if isinstance(item, ContractApply)
        ],
        "artifacts": {name: _hash_file(path) for name, path in artifacts.items()},
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(_json(manifest), encoding="utf-8")
    print(f"built {len(artifacts)} artifacts in {output}")
    _print_diagnostics(diagnostics, args.source, verbose=args.verbose)
    if args.signoff and has_blocking:
        print("signoff failed: unresolved or invalid semantics remain", file=sys.stderr)
        return 1
    return 0


def command_emit_circt(args: argparse.Namespace) -> int:
    program, result, diagnostics = _load_and_check(args)
    if any(item.severity == Severity.ERROR for item in diagnostics) or (
        result.has_blocking_diagnostics
    ):
        _print_diagnostics(diagnostics, args.source, verbose=args.verbose)
        return 1
    if args.fragment:
        print(
            "\nError-[E-LOWERING-FRAGMENT]\n"
            "  Message: CIRCT lowering requires module-complete form",
            file=sys.stderr,
        )
        return 1
    if result.abstract_symbols:
        print(
            "\nError-[E-LOWERING-ABSTRACT]\n"
            "  Message: CIRCT lowering requires refinement of "
            + ", ".join(result.abstract_symbols),
            file=sys.stderr,
        )
        return 1
    _write_or_print(emit_circt(program, result), args.output)
    return 0


def _node_records(program: Any) -> list[dict[str, Any]]:
    return [
        {
            "node_id": node.node_id,
            "kind": type(node).__name__,
            "span": to_dict(node.span),
        }
        for node in iter_nodes(program)
    ]


def command_nodes(args: argparse.Namespace) -> int:
    program = parse_file(args.source, fragment=args.fragment)
    records = _node_records(program)
    if args.format == "json":
        print(_json(records), end="")
    else:
        for record in records:
            span = record["span"]
            print(
                f"{record['node_id']} {record['kind']} "
                f"{args.source}:{span['line']}:{span['column']}"
            )
    return 0


def command_init_provenance(args: argparse.Namespace) -> int:
    program = parse_file(args.source, fragment=args.fragment)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(dump_sidecar(empty_sidecar(program)), encoding="utf-8")
    print(f"wrote provenance template to {args.output}")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    commands = {
        "parse": command_parse,
        "check": command_check,
        "elaborate": command_elaborate,
        "fmt": command_fmt,
        "build": command_build,
        "emit-circt": command_emit_circt,
        "nodes": command_nodes,
        "init-provenance": command_init_provenance,
    }
    try:
        code = commands[args.command](args)
    except ParseError as exc:
        diagnostic = Diagnostic(
            code="E-PARSE",
            severity=Severity.ERROR,
            message=exc.message,
            span=exc.span,
        )
        print("\n" + _render_diagnostic(diagnostic, args.source), file=sys.stderr)
        code = 2
    except (OSError, ValueError, json.JSONDecodeError, LoweringError) as exc:
        print(f"\nError-[E-TOOL]\n  Message: {exc}", file=sys.stderr)
        code = 2
    raise SystemExit(code)

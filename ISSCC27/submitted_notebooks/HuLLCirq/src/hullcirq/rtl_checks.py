"""Candidate extraction and constrained interface/syntax checks, not proofs."""

from __future__ import annotations

import difflib
import os
import re
import subprocess
import tempfile
from pathlib import Path

from .domain import DomainError, VERILOG_IDENTIFIER, VERILOG_KEYWORDS

MAX_RTL_CHARS = 512 * 1024
INTERFACE_CHECK_VERSION = "verilog2005-interface-guard-v2-pure-casts"
PURE_CAST_FUNCTIONS = frozenset({"$signed", "$unsigned"})
CAST_ARGUMENT_START = re.compile(r'\s*\(')


def _diagnostic(code: str, message: str, severity: str = "error") -> dict:
    return {"code": code, "severity": severity, "message": message}


def _strip_comments(text: str) -> str:
    return re.sub(r'//[^\n]*|/\*[\s\S]*?\*/', lambda match: "\n" * match[0].count("\n") + " ", text)


def extract_rtl(raw_content: str) -> dict:
    if type(raw_content) is not str:
        raise DomainError("invalid_response", "Raw generation content must be text.")
    if len(raw_content) > MAX_RTL_CHARS:
        return {"rtl": None, "diagnostics": [_diagnostic("rtl_size_limit", "Candidate text exceeds the RTL size limit.")]}
    content = re.sub(r'<think>[\s\S]*?</think>', '', raw_content, flags=re.IGNORECASE).strip()
    fences = re.findall(r'```([^\n`]*)\n([\s\S]*?)```', content)
    candidate_blocks = [body.strip() for language, body in fences
                        if language.strip().lower() in ("verilog", "v", "") and re.search(r'\bmodule\b', _strip_comments(body))]
    if len(candidate_blocks) > 1:
        return {"rtl": None, "diagnostics": [_diagnostic("ambiguous_rtl", "Response contains more than one possible Verilog block.")]}
    if len(candidate_blocks) == 1:
        candidate = candidate_blocks[0]
    elif not fences and re.match(r'^module\b', _strip_comments(content).strip()) and re.search(r'\bendmodule\s*$', _strip_comments(content)):
        candidate = content
    else:
        return {"rtl": None, "diagnostics": [_diagnostic("rtl_not_found", "Reply must contain one fenced Verilog block or one complete raw module.")]}
    if "<think>" in candidate.lower() or "</think>" in candidate.lower():
        return {"rtl": None, "diagnostics": [_diagnostic("incomplete_reasoning", "Response did not cleanly separate reasoning from candidate RTL.")]}
    return {"rtl": candidate + "\n", "diagnostics": []}


def compare_rtl(previous: str | None, candidate: str | None) -> str:
    return "".join(difflib.unified_diff((previous or "").splitlines(keepends=True), (candidate or "").splitlines(keepends=True),
                                        fromfile="previous.v", tofile="candidate.v"))


def _parse_port_declarations(parts: list[str]) -> tuple[list[dict], list[dict]]:
    ports, diagnostics = [], []
    inherited = None
    declaration = re.compile(r'^(input|output|inout)\s+(?:(?:wire|reg)\s+)?(?:(signed)\s+)?(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?([A-Za-z_][A-Za-z0-9_$]*)$')
    for part in parts:
        part = re.sub(r'\s+', ' ', part.strip())
        match = declaration.fullmatch(part)
        if match:
            direction, signed, msb, lsb, name = match.groups()
            inherited = {"direction": direction, "signed": bool(signed), "width": abs(int(msb) - int(lsb)) + 1 if msb is not None else 1}
        elif inherited is not None and VERILOG_IDENTIFIER.fullmatch(part):
            name = part
        else:
            diagnostics.append(_diagnostic("unsupported_port_declaration", "Port declarations require input/output, literal fixed-width ranges, and plain Verilog identifiers."))
            continue
        ports.append({"name": name, **inherited})
    return ports, diagnostics


def _parse_interface(source: str) -> tuple[str | None, list[dict], list[dict]]:
    diagnostics = []
    modules = re.findall(r'\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)\b', source)
    if len(modules) != 1 or len(re.findall(r'\bmodule\b', source)) != 1 or len(re.findall(r'\bendmodule\b', source)) != 1:
        return None, [], [_diagnostic("module_count", "Candidate must contain exactly one module and one endmodule.")]
    module_name = modules[0]
    header = re.search(r'\bmodule\s+' + re.escape(module_name) + r'\s*\(([^()]*)\)\s*;', source)
    if header is None:
        return module_name, [], [_diagnostic("unsupported_module_header", "M2-A requires a fixed, unparameterized module with an explicit port list.")]
    pieces = header[1].split(",") if header[1].strip() else []
    if re.search(r'\b(input|output|inout)\b', header[1]):
        ports, diagnostics = _parse_port_declarations(pieces)
    else:
        names = [piece.strip() for piece in pieces]
        if any(not VERILOG_IDENTIFIER.fullmatch(name) for name in names) or len(names) != len(set(names)):
            diagnostics.append(_diagnostic("invalid_header_ports", "Non-ANSI module header must list unique plain port names."))
        body = source[header.end():]
        body = re.sub(r'\bfunction\b[\s\S]*?\bendfunction\b|\btask\b[\s\S]*?\bendtask\b', '', body)
        ports = []
        for match in re.finditer(r'\b(input|output|inout)\s+([^;]+);', body):
            parsed, findings = _parse_port_declarations((match[1] + " " + match[2]).split(","))
            ports.extend(parsed)
            diagnostics.extend(findings)
        if set(names) != {port["name"] for port in ports}:
            diagnostics.append(_diagnostic("header_declaration_mismatch", "Header ports and body port declarations differ."))
    if len({port["name"] for port in ports}) != len(ports):
        diagnostics.append(_diagnostic("duplicate_rtl_port", "Candidate declares a physical port more than once."))
    return module_name, ports, diagnostics


def _wsl_path(path: Path) -> str:
    absolute = str(path.resolve())
    if not re.match(r'^[A-Za-z]:[\\/]', absolute):
        raise DomainError("unsupported_compiler", "WSL compilation requires a local Windows drive path.")
    return "/mnt/" + absolute[0].lower() + "/" + absolute[3:].replace("\\", "/")


def _syntax_check(rtl: str, module_name: str, compiler: dict | None) -> dict:
    unsupported = {"validation_status": "Unsupported", "scope": "Verilog-2005 compilation_only", "executed": False,
                   "diagnostics": [_diagnostic("syntax_compiler_unavailable", "A trusted Icarus compiler must be configured before this candidate can be accepted.", "warning")]}
    if compiler is None:
        return unsupported
    if type(compiler) is not dict or compiler.get("kind") not in ("native", "wsl"):
        raise DomainError("invalid_compiler", "Compiler must be a trusted native or WSL configuration.")
    executable = compiler.get("executable")
    if type(executable) is not str or not executable or any(ord(char) < 32 for char in executable):
        raise DomainError("invalid_compiler", "Trusted compiler executable path is required.")
    basename = executable.replace("\\", "/").rsplit("/", 1)[-1].lower()
    if basename not in ("iverilog", "iverilog.exe"):
        raise DomainError("invalid_compiler", "Only the fixed Icarus compiler operation is supported.")
    extra = []
    base_directory = compiler.get("base_directory")
    if base_directory is not None:
        if type(base_directory) is not str or any(ord(char) < 32 for char in base_directory):
            raise DomainError("invalid_compiler", "Compiler base directory must be a trusted absolute path.")
        if compiler["kind"] == "wsl" and not base_directory.startswith("/") or compiler["kind"] == "native" and not Path(base_directory).is_absolute():
            raise DomainError("invalid_compiler", "Compiler base directory must be absolute.")
        extra = ["-B", base_directory]
    workspace = compiler.get("working_directory")
    if workspace is not None:
        if type(workspace) is not str or not Path(workspace).is_absolute():
            raise DomainError("invalid_compiler", "Compiler working directory must be a trusted absolute local path.")
        Path(workspace).mkdir(parents=True, exist_ok=True)
    # WSL can retain a Windows cwd handle briefly after the compiler exits.
    # Keep its cwd outside the disposable candidate directory, and tolerate
    # delayed cleanup without replacing the actual compiler result.
    with tempfile.TemporaryDirectory(prefix="hullcirq-rtl-", dir=workspace, ignore_cleanup_errors=True) as directory:
        candidate = Path(directory) / "candidate.v"
        candidate.write_text(rtl, encoding="utf-8")
        compile_directory = directory
        if compiler["kind"] == "native":
            if not Path(executable).is_absolute():
                raise DomainError("invalid_compiler", "Native compiler executable must be an absolute trusted path.")
            command = [executable, *extra, "-g2005", "-tnull", "-s", module_name, str(candidate)]
        else:
            distribution = compiler.get("distribution")
            if type(distribution) is not str or not re.fullmatch(r'[A-Za-z0-9_.-]+', distribution) or not executable.startswith("/"):
                raise DomainError("invalid_compiler", "WSL compiler requires a trusted distribution and absolute Linux executable.")
            wsl = Path(os.environ.get("SystemRoot", "C:\\Windows")) / "System32" / "wsl.exe"
            try:
                source_path = _wsl_path(candidate)
                compile_directory = workspace or tempfile.gettempdir()
                persistent_cwd = _wsl_path(Path(compile_directory))
            except DomainError:
                return unsupported
            command = [str(wsl), "-d", distribution, "--cd", persistent_cwd, "--exec", executable,
                       *extra, "-g2005", "-tnull", "-s", module_name, source_path]
        try:
            outcome = subprocess.run(command, cwd=compile_directory, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20, shell=False)
        except FileNotFoundError:
            result = unsupported
        except subprocess.TimeoutExpired:
            result = {"validation_status": "Failed", "scope": "Verilog-2005 compilation_only", "executed": True,
                      "command": command, "diagnostics": [_diagnostic("syntax_timeout", "The fixed syntax check exceeded its time limit.")]}
        except OSError:
            result = {"validation_status": "Unsupported", "scope": "Verilog-2005 compilation_only", "executed": False,
                      "diagnostics": [_diagnostic("syntax_compiler_unavailable", "The configured compiler could not be started.", "warning")]}
        else:
            passed = outcome.returncode == 0
            result = {"validation_status": "Passed" if passed else "Failed", "scope": "Verilog-2005 compilation_only", "executed": True,
                      "command": command, "exit_code": outcome.returncode, "stdout": outcome.stdout, "stderr": outcome.stderr,
                      "diagnostics": [] if passed else [_diagnostic("syntax_failed", "The trusted compiler rejected this candidate; inspect its actual output.")]}
    try:
        incomplete_cleanup = Path(directory).exists()
    except OSError:
        incomplete_cleanup = True
    result["cleanup_status"] = "Incomplete" if incomplete_cleanup else "Completed"
    if incomplete_cleanup:
        result["cleanup_directory"] = directory
        result["diagnostics"].append(_diagnostic("syntax_cleanup_incomplete", "Compiler result retained; temporary candidate cleanup is delayed or incomplete.", "warning"))
    return result


def check_rtl(rtl: str, expected_interface, module_name: str, compiler: dict | None = None, *, interface_only=False) -> dict:
    if type(rtl) is not str or type(module_name) is not str or not VERILOG_IDENTIFIER.fullmatch(module_name) or module_name in VERILOG_KEYWORDS:
        raise DomainError("invalid_rtl_check", "Candidate text and a plain non-keyword module name are required.")
    expected_ports = expected_interface.get("ports") if type(expected_interface) is dict else expected_interface
    if type(expected_ports) is not list:
        raise DomainError("invalid_interface", "Expected interface must contain a physical ports array.")
    expected = {}
    for port in expected_ports:
        if (type(port) is not dict or type(port.get("name")) is not str or not VERILOG_IDENTIFIER.fullmatch(port["name"])
                or port.get("direction") not in ("input", "output") or type(port.get("width")) is not int or port["width"] < 1
                or type(port.get("signed")) is not bool or port["name"] in expected):
            raise DomainError("invalid_interface", "Expected physical ports have invalid or duplicate contract fields.")
        expected[port["name"]] = port
    diagnostics = []
    source = _strip_comments(rtl)
    if len(rtl) > MAX_RTL_CHARS:
        diagnostics.append(_diagnostic("rtl_size_limit", "Candidate exceeds the supported RTL size."))
    if "`" in source:
        diagnostics.append(_diagnostic("unsafe_directive", "Preprocessor directives, includes, and macros are not permitted in this fixed candidate check."))
    system_tokens = re.finditer(r'\$(?:[A-Za-z_][A-Za-z0-9_$]*)', source)
    if any(match[0] not in PURE_CAST_FUNCTIONS or not CAST_ARGUMENT_START.match(source, match.end()) for match in system_tokens):
        diagnostics.append(_diagnostic("unsafe_system_task", "Only pure $signed(...) and $unsigned(...) casts are permitted; other system tasks/functions and file access are not allowed."))
    if re.search(r'\b(?:logic|always_ff|always_comb|interface|package|typedef|struct|enum|initial)\b', source):
        diagnostics.append(_diagnostic("unsupported_language", "Candidate must use synthesizable Verilog-2005 without testbench/SystemVerilog constructs."))
    actual_module, ports, interface_diagnostics = _parse_interface(source)
    diagnostics.extend(interface_diagnostics)
    if actual_module != module_name:
        diagnostics.append(_diagnostic("module_name_mismatch", "Candidate module name does not match the requested node module."))
    actual = {port["name"]: port for port in ports}
    for name in sorted(set(expected) - set(actual)):
        diagnostics.append(_diagnostic("missing_rtl_port", f"Requested physical port {name} is missing."))
    for name in sorted(set(actual) - set(expected)):
        diagnostics.append(_diagnostic("unexpected_rtl_port", f"Candidate added unrequested physical port {name}."))
    for name in sorted(set(actual) & set(expected)):
        for field in ("direction", "width", "signed"):
            if actual[name][field] != expected[name][field]:
                diagnostics.append(_diagnostic(f"rtl_{field}_mismatch", f"Physical port {name} has a different {field} from the requested contract."))
    interface_status = "Failed" if any(item["severity"] == "error" for item in diagnostics) else "Passed"
    if interface_only:
        # S04 checks the generated module boundary. Compilation belongs to S05;
        # behavioral simulation belongs to S06 after the candidate is synthesized.
        syntax = {"validation_status": "Not Run", "executed": False,
                  "deferred_to_stage": "local_synthesis", "diagnostics": []}
    elif interface_status == "Failed":
        syntax = {"validation_status": "Not Checked", "executed": False,
                  "diagnostics": [_diagnostic("syntax_blocked", "Syntax execution was blocked by candidate safety/interface errors.", "info")]}
    else:
        syntax = _syntax_check(rtl, module_name, compiler)
    diagnostics.extend(syntax["diagnostics"])
    diagnostics.append(_diagnostic("rtl_check_limits", "Interface checks do not prove syntax, function, handshake timing, synthesis, or netlist behavior." if interface_only else "Interface and compilation checks do not prove function, handshake timing, synthesis, or netlist behavior.", "info"))
    status = (interface_status if interface_only else
              "Failed" if interface_status == "Failed" or syntax["validation_status"] == "Failed" else "Passed" if syntax["validation_status"] == "Passed" else "Unsupported")
    return {"validation_status": status, "diagnostics": diagnostics, "checks": {
        "interface": {"validation_status": interface_status, "expected_ports": expected_ports, "actual_ports": ports,
                      "checker_version": INTERFACE_CHECK_VERSION},
        "syntax": syntax, "functional_verification": {"validation_status": "Not Run", "executed": False}}}

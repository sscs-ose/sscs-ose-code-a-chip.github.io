"""Parse tool stdout/stderr into structured TaskError records.

Used by the pipeline interpreter to carry precise, line-level errors from a
failed gate into the next retry's TaskManifest, so agents don't have to
rediscover them by re-running the tool.
"""
import re
from typing import Iterable

from chip_nebula.models.task_manifest import TaskError


# Verilator: "%Error-WIDTHTRUNC: path/to/file.sv:42:17: message..."
# Also matches %Warning-XXXX.
_VERILATOR_RE = re.compile(
    r"%(?P<severity>Error|Warning)(?:-(?P<code>[A-Z0-9_]+))?:\s*"
    r"(?P<file>[^:\s][^:]*):(?P<line>\d+)(?::\d+)?:\s*(?P<msg>.+)"
)

# Yosys: "ERROR: path/file.v:123: message" or "Warning: ..."
_YOSYS_RE = re.compile(
    r"^(?P<severity>ERROR|Warning):\s*"
    r"(?P<file>[^:\s\r\n][^:\r\n]*):(?P<line>\d+):\s*(?P<msg>.+)",
    re.MULTILINE,
)

# Icarus/VVP SystemVerilog ``$fatal`` output:
# "FATAL: tb/top_tb.sv:19: count changed while disabled"
_VVP_FATAL_RE = re.compile(
    r"^FATAL:\s*(?P<file>[^:\s][^:]*):(?P<line>\d+)(?::\d+)?:\s*(?P<msg>.+)",
    re.MULTILINE,
)

# Python traceback final line: "File "x.py", line 42, in <module>"
_PY_TB_FILE_RE = re.compile(
    r'File "(?P<file>[^"]+)", line (?P<line>\d+)'
)
_PY_TB_MSG_RE = re.compile(r"^(?P<type>\w+Error|\w+Exception):\s*(?P<msg>.+)$", re.MULTILINE)

# Generic "file:line: message" fallback
_GENERIC_RE = re.compile(
    r"^\s*(?P<file>[A-Za-z0-9_.$/\\-]+\.(?:sv|v|vh|svh|py|sdc)):"
    r"(?P<line>\d+)(?::\d+)?:\s*(?P<msg>.+)",
    re.MULTILINE,
)


def parse_errors(text: str, *, tool_hint: str = "") -> list[TaskError]:
    """Parse tool output into TaskError records.

    Best-effort: multiple parsers are tried; duplicate (file, line, code) are
    deduped. Returns empty list if no patterns match — callers should fall
    back to a generic 'see execution log' entry.
    """
    if not text:
        return []

    errors: list[TaskError] = []
    seen: set[tuple[str, int, str]] = set()

    def add(file: str, line: int, code: str, severity: str, msg: str) -> None:
        key = (file, line, code)
        if key in seen:
            return
        seen.add(key)
        errors.append(TaskError(
            file=file, line=line, code=code,
            severity=severity.upper(), message=msg.strip(),
        ))

    hint = tool_hint.lower()

    if not hint or "verilator" in hint:
        for m in _VERILATOR_RE.finditer(text):
            add(
                m.group("file"), int(m.group("line")),
                m.group("code") or "VERILATOR",
                m.group("severity"),
                m.group("msg"),
            )

    if not hint or "yosys" in hint:
        for m in _YOSYS_RE.finditer(text):
            sev = m.group("severity")
            sev_norm = "ERROR" if sev.upper() == "ERROR" else "WARNING"
            add(
                m.group("file"), int(m.group("line")),
                "YOSYS", sev_norm, m.group("msg"),
            )

    # VVP failures can follow successful Verilator lint warnings in a single
    # archived run log.  Always inspect them instead of gating on tool_hint.
    for m in _VVP_FATAL_RE.finditer(text):
        add(
            m.group("file"), int(m.group("line")),
            "VVP_FATAL", "FATAL", m.group("msg"),
        )

    if not hint or "python" in hint or "pytest" in hint or "sim" in hint:
        tb_files = list(_PY_TB_FILE_RE.finditer(text))
        tb_msgs = list(_PY_TB_MSG_RE.finditer(text))
        if tb_files and tb_msgs:
            last_file = tb_files[-1]
            last_msg = tb_msgs[-1]
            add(
                last_file.group("file"),
                int(last_file.group("line")),
                last_msg.group("type"),
                "ERROR",
                last_msg.group("msg"),
            )

    # A combined lint/compile log can contain Verilator warnings followed by
    # the actual Icarus failure.  Generic diagnostics must therefore be parsed
    # even when a tool-specific parser already found another record.
    for m in _GENERIC_RE.finditer(text):
        message = m.group("msg")
        lowered = message.lower()
        if lowered.startswith(("$finish called at", "$stop called at")):
            # VVP reports normal SystemVerilog ``$finish`` and non-interactive
            # ``$stop`` with source locations even when simulation succeeds.
            # It belongs in the complete log, not in the problem list.
            continue
        if lowered.startswith("example path:"):
            # Verilator emits one or more source-located cycle traces after an
            # UNOPTFLAT warning. They explain the primary warning and are not
            # independent diagnostics. Keeping them would create red generic
            # errors in an otherwise successful lint run.
            continue
        if lowered.startswith("warning:"):
            code, severity = "GENERIC_WARNING", "WARNING"
        elif (
            lowered.startswith(("note:", "...", ":"))
            or re.match(r"^\d+\s*\|", message)
        ):
            # Icarus emits source-location continuation records such as
            # ``...: The inherited timescale is here.`` or
            # ``: Padding 1 high bits ...`` after a warning.
            # Verilator may also prefix a numbered source excerpt with a
            # second ``file:line:column`` location. These records add context
            # but do not turn a successful compile into an error.
            code, severity = "GENERIC_NOTE", "WARNING"
        elif " sorry:" in f" {lowered}" or lowered.startswith("sorry:"):
            # Icarus uses "sorry:" for accepted constructs whose simulation
            # semantics are reduced. It commonly returns 0.
            code, severity = "IVERILOG_SORRY", "WARNING"
        else:
            code, severity = "GENERIC", "ERROR"
        add(
            m.group("file"), int(m.group("line")),
            code, severity, message,
        )

    return errors


def parse_errors_from_reports(reports: Iterable, *, tool_hint: str = "") -> list[TaskError]:
    """Aggregate TaskError from an iterable of failed GateReport objects."""
    errs: list[TaskError] = []
    for r in reports:
        if getattr(r, "passed", True):
            continue
        evidence = getattr(r, "evidence", "") or ""
        suggestion = getattr(r, "suggestion", "") or ""
        combined = evidence + "\n" + suggestion
        errs.extend(parse_errors(combined, tool_hint=tool_hint))
    return errs

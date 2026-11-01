"""Independent, read-only SDF INTERCONNECT inventory for a flat netlist.

An inventory is not successful annotation or simulation. Every scalar arc is
bound to exact original source/destination pins, directions and a unique raw
driver net. Original netlist, models and SDF are never written. Delays are
retained as signed-checked integer picoseconds without rounding. No custom
delay transformation is used: native simulator qualification is separate.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re

from .layout_roles import LayoutRoleError, _ID, _name, parse_structural_verilog


class InterconnectError(ValueError):
    """The input falls outside the deliberately narrow supported subset."""


def _require(value, message):
    if not value:
        raise InterconnectError(message)


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _without_comments(text):
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)


def parse_sdf(text):
    """Parse complete S-expressions, retaining every atom and quoted string.

    This tokenizer does not implement escaped whitespace in unquoted names;
    such names are rejected by endpoint validation rather than guessed.
    """
    scanner = re.compile(r'\s+|/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|[()]|[^\s()"]+', re.S)
    tokens, position = [], 0
    for match in scanner.finditer(text):
        _require(match.start() == position, "Unrecognized SDF token")
        token, position = match[0], match.end()
        _require(not token.startswith("/*") or token.endswith("*/"), "Unterminated SDF comment")
        if not token.isspace() and not token.startswith(("//", "/*")):
            tokens.append(token)
    _require(position == len(text), "Truncated or unrecognized SDF token")
    stack, roots = [], []
    for token in tokens:
        if token == "(":
            item = []
            (stack[-1] if stack else roots).append(item)
            stack.append(item)
        elif token == ")":
            _require(stack, "Unbalanced SDF close parenthesis")
            stack.pop()
        else:
            _require(stack, "SDF atom outside a list")
            stack[-1].append(token)
    _require(not stack and len(roots) == 1, "Require one complete SDF root")
    _require(roots[0] and roots[0][0] == "DELAYFILE", "Require DELAYFILE")
    return roots[0]


def _children(node, name):
    return [item for item in node[1:] if isinstance(item, list) and item and item[0] == name]


def _one(node, name):
    matches = _children(node, name)
    _require(len(matches) == 1, f"Require exactly one SDF {name}")
    return matches[0]


def _endpoint(value):
    _require(isinstance(value, str) and not value.startswith('"'), "Quoted endpoint unsupported")
    parts, current, escaped = [], [], False
    for char in value:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ".":
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    _require(not escaped, "Unterminated escaped SDF endpoint")
    parts.append("".join(current))
    _require(len(parts) in (1, 2) and all(parts), "Only flat top ports or instance.pin endpoints supported")
    return tuple(parts)


def _delay_ps(node, selection):
    _require(isinstance(node, list) and len(node) == 1 and isinstance(node[0], str), "Require scalar SDF delay")
    values = node[0].split(":")
    _require(len(values) in (1, 3) and all(values), "Require complete scalar or min:typ:max delay")
    _require(all(re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value) for value in values),
             "Invalid numeric SDF delay syntax")
    try:
        parsed = [Decimal(value) for value in values]
    except InvalidOperation as error:
        raise InterconnectError("Invalid numeric SDF delay") from error
    _require(all(value.is_finite() and value >= 0 for value in parsed), "INTERCONNECT must have finite nonnegative delays")
    value = parsed[0] if len(parsed) == 1 else parsed[{"min": 0, "typ": 1, "max": 2}[selection]]
    ps = value * 1000
    _require(ps == ps.to_integral_value(), "Sub-picosecond INTERCONNECT delay unsupported; no rounding permitted")
    return int(ps)


def interconnect_records(sdf_text, *, selection="typ"):
    """Return strict flat absolute 1 ns, two-transition scalar arc records."""
    _require(selection in ("min", "typ", "max"), "Unknown delay selection")
    root = parse_sdf(sdf_text)
    _require(_one(root, "SDFVERSION")[1:] == ['"3.0"'], "Require SDF 3.0")
    _require(_one(root, "DIVIDER")[1:] == ["."], "Require dot SDF divider")
    _require(_one(root, "TIMESCALE")[1:] == ["1ns"], "Require 1ns SDF timescale")
    design = _one(root, "DESIGN")
    _require(len(design) == 2 and re.fullmatch(r'"[A-Za-z_$][\w$]*"', design[1]), "Unsupported SDF design")
    top = design[1][1:-1]
    cells = _children(root, "CELL")
    tops = [cell for cell in cells if _one(cell, "INSTANCE")[1:] == []]
    _require(len(tops) == 1 and _one(tops[0], "CELLTYPE")[1:] == [json.dumps(top)], "Require exact top CELL")
    delay = _one(tops[0], "DELAY")
    absolute = _one(delay, "ABSOLUTE")
    _require(len(delay) == 2 and all(isinstance(child, list) and child and child[0] == "INTERCONNECT" for child in absolute[1:]),
             "Top delay must contain only ABSOLUTE INTERCONNECT records")
    arcs, seen = [], set()
    for index, item in enumerate(absolute[1:]):
        _require(len(item) == 5, "Require exactly two scalar INTERCONNECT delay values")
        source, destination = _endpoint(item[1]), _endpoint(item[2])
        _require(destination not in seen, "Duplicate INTERCONNECT destination unsupported")
        seen.add(destination)
        arcs.append({"index": index, "source": item[1], "destination": item[2],
                     "source_endpoint": source, "destination_endpoint": destination,
                     "rise_ps": _delay_ps(item[3], selection), "fall_ps": _delay_ps(item[4], selection),
                     "original_record": item})
    # An arc outside the selected top ABSOLUTE block must never be dropped.
    def count(node):
        return (int(bool(node) and node[0] == "INTERCONNECT") +
                sum(count(child) for child in node if isinstance(child, list)))
    _require(arcs and count(root) == len(arcs), "Uncovered INTERCONNECT record")
    for token in ("PATHPULSE", "PATHPULSEPERCENT", "GLOBALPATHPULSE", "GLOBALPATHPULSEPERCENT"):
        _require(not re.search(r"\(\s*" + token + r"\b", sdf_text), "Explicit pulse rejection unsupported")
    return top, arcs


def cell_port_directions(models_text):
    """Read scalar module port directions across matching preprocessor variants.

    This is declaration inspection, not Verilog preprocessing or compilation.
    A direction must agree in all matching variants. Optional power pins can be
    present in only the powered variants.
    """
    text = _without_comments(models_text)
    result = {}
    for match in re.finditer(r"\bmodule\s+(" + _ID + r")\s*\([^;]*\)\s*;(.*?)\bendmodule\b", text, re.S):
        name, body = _name(match[1]), match[2]
        ports = result.setdefault(name, {})
        for declaration in re.finditer(r"\b(input|output|inout)\s+([^;]+);", body):
            direction, names = declaration.groups()
            _require(not any(char in names for char in "[]="), "Only scalar model port declarations supported")
            for port in names.split(","):
                port = port.strip()
                _require(re.fullmatch(_ID, port), "Unsupported model port declaration")
                port = _name(port)
                _require(port not in ports or ports[port] == direction, "Conflicting model pin directions")
                ports[port] = direction
    _require(result, "No cell module declarations found")
    return result


def interconnect_inventory(netlist_text, sdf_text, cell_models_text, *, selection="typ"):
    """Return every original scalar arc's binding and read-only provenance.

    Supported structural input has one non-ANSI module, scalar named-port cells,
    named nets or individual vector bits, and no aliases/behavioral statements.
    Inout pins, multiple drivers, cross-net SDF arcs and missing pin directions
    fail closed. A complete inventory does not prove that a simulator applies
    these arcs; successful native annotation must be established separately.
    """
    top, arcs = interconnect_records(sdf_text, selection=selection)
    try:
        graph = parse_structural_verilog(netlist_text)
    except LayoutRoleError as error:
        raise InterconnectError(str(error)) from error
    _require(top == graph["top"], "SDF/netlist top mismatch")
    clean = _without_comments(netlist_text)
    _require(not re.search(r"\bassign\b", clean), "Structural alias assignments unsupported")
    directions = cell_port_directions(cell_models_text)
    top_ports, drivers = {}, defaultdict(list)
    for match in re.finditer(r"\b(input|output|inout|wire)\s*(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*(" + _ID + r")\s*;", clean):
        direction, high, low, name = match.groups()
        if direction == "wire":
            continue
        _require(direction != "inout", "Top inout ports unsupported")
        bits = [_name(name)] if high is None else [f"{_name(name)}[{bit}]" for bit in range(min(int(high), int(low)), max(int(high), int(low)) + 1)]
        for bit in bits:
            _require(bit not in top_ports, "Duplicate top port declaration")
            top_ports[bit] = direction
            if direction == "input":
                drivers[bit].append((bit,))
    cells = graph["cells"]
    for name, cell in cells.items():
        _require(cell["master"] in directions, f"Missing model for {cell['master']}")
        for pin, net in cell["pins"].items():
            direction = directions[cell["master"]].get(pin)
            _require(direction in ("input", "output"), f"Missing or inout model pin {name}.{pin}")
            _require(net in graph["declarations"] or net.startswith("const:"), "Undeclared structural pin net")
            if direction == "output":
                drivers[net].append((name, pin))
    for net, endpoints in drivers.items():
        _require(len(endpoints) == 1, f"Multiple drivers unsupported: {net}")

    def resolve(endpoint, source):
        if len(endpoint) == 1:
            net = endpoint[0]
            expected = "input" if source else "output"
            _require(top_ports.get(net) == expected, "SDF top endpoint direction mismatch")
        else:
            name, pin = endpoint
            _require(name in cells and pin in cells[name]["pins"], "Unknown SDF cell pin")
            cell = cells[name]
            expected = "output" if source else "input"
            _require(directions[cell["master"]][pin] == expected, "SDF cell endpoint direction mismatch")
            net = cell["pins"][pin]
        _require(not net.startswith("const:"), "Constant SDF endpoint unsupported")
        return net

    bindings = []
    for arc in arcs:
        source_net = resolve(arc["source_endpoint"], True)
        destination_net = resolve(arc["destination_endpoint"], False)
        _require(source_net == destination_net, "SDF endpoints connect different original nets")
        _require(drivers.get(source_net) == [arc["source_endpoint"]], "SDF source is not the unique original driver")
        bindings.append({**arc, "source_endpoint": list(arc["source_endpoint"]), "destination_endpoint": list(arc["destination_endpoint"]),
                         "original_net": source_net,
                         "source_cell_type": cells[arc["source_endpoint"][0]]["master"] if len(arc["source_endpoint"]) == 2 else None,
                         "destination_cell_type": cells[arc["destination_endpoint"][0]]["master"] if len(arc["destination_endpoint"]) == 2 else None})
    fanout = Counter(arc["source"] for arc in arcs)
    report = {"kind": "hullcirq-scalar-interconnect-inventory-v1", "origin": "development_assistant",
              "top_module": top, "delay_selection": selection, "timescale": "1ns/1ps",
              "input_netlist_text_sha256": _sha(netlist_text), "input_sdf_text_sha256": _sha(sdf_text),
              "input_cell_models_text_sha256": _sha(cell_models_text),
              "text_hash_scope": "UTF-8 supplied text, not a claim of original file byte hashes",
              "arc_count": len(arcs), "unique_source_count": len(fanout), "maximum_fanout": max(fanout.values()),
              "top_output_arc_count": sum(len(arc["destination_endpoint"]) == 1 for arc in arcs), "cell_instance_count": len(cells),
              "zero_rise_arc_count": sum(arc["rise_ps"] == 0 for arc in arcs),
              "zero_fall_arc_count": sum(arc["fall_ps"] == 0 for arc in arcs),
              "source_bytes_modified": False, "full_sdf_equivalence": False, "dynamic_validation_executed": False,
              "qualification_status": "Inventory only; native annotation unestablished",
              "limitations": ["An arc count is not successful native annotation coverage.",
                              "No netlist rewriting or custom delay implementation is performed.",
                              "No cell IOPATH, SETUP/HOLD/WIDTH, delayed reference/data or notifier implementation in this inventory.",
                              "No claim of complete IEEE SDF or electrical/signoff equivalence.",
                              "The native simulator's pulse and X/Z behavior must be qualified separately."],
              "bindings": bindings}
    return report


def audit_native_interconnect_log(inventory, log_text):
    """Bind Icarus 13 ``-sdf-verbose`` records to every inventory arc.

    Require each source/destination name and bus index, one native path handle
    and both selected delay values in original order. This audits the emitted
    pre-write log, not VPI readback, transition semantics or timing-check
    success. The exact TIMINGCHECK-not-supported warning is retained separately
    and never treated as successful timing verification.
    """
    _require(type(inventory) is dict and inventory.get("kind") == "hullcirq-scalar-interconnect-inventory-v1",
             "Require the exact independent interconnect inventory")
    expected = inventory.get("bindings")
    _require(type(expected) is list and len(expected) == inventory.get("arc_count") and expected,
             "Incomplete inventory bindings")
    marker = re.compile(r"^SDF INFO: (.+):(\d+): INTERCONNECT with port1 = (.+) index = (-?\d+), port2 = (.+) index = (-?\d+)$")
    created = re.compile(r"^SDF INFO: (.+):(\d+): Created a vpiInterModPath$")
    putting = re.compile(r"^SDF INFO: (.+):(\d+): Putting delay: (\S+) for index (\d+)$")
    ignored_timing = re.compile(r"^SDF WARNING: (.+):(\d+): TIMINGCHECK not supported\.$")
    groups, current, warnings = [], None, []
    for line in log_text.splitlines():
        if "SDF ERROR:" in line:
            raise InterconnectError("Native annotation error: " + line)
        if "SDF WARNING:" in line:
            _require(ignored_timing.fullmatch(line), "Unqualified native annotation warning: " + line)
            warnings.append(line)
            continue
        match = marker.fullmatch(line)
        if match:
            current = {"file": match[1], "line": int(match[2]), "source_name": match[3], "source_index": int(match[4]),
                       "destination_name": match[5], "destination_index": int(match[6]), "created": 0, "delays": []}
            groups.append(current)
            continue
        match = created.fullmatch(line)
        if match:
            _require(current is not None and (match[1], int(match[2])) == (current["file"], current["line"]),
                     "Native path-handle record is unbound or has a different SDF location")
            current["created"] += 1
            continue
        match = putting.fullmatch(line)
        if match:
            _require(current is not None and (match[1], int(match[2])) == (current["file"], current["line"]),
                     "Native delay record is unbound or has a different SDF location")
            try:
                value = Decimal(match[3]) * 1000
            except InvalidOperation as error:
                raise InterconnectError("Invalid native logged delay") from error
            _require(value.is_finite() and value >= 0 and value == value.to_integral_value(),
                     "Native logged delay is nonfinite, negative or sub-picosecond")
            current["delays"].append((int(match[4]), int(value)))
    _require(len(groups) == len(expected), "Native INTERCONNECT log count differs from the complete inventory")

    def endpoint_log_fields(endpoint):
        name = ".".join(endpoint)
        match = re.fullmatch(r"(.+)\[(\d+)\]", name)
        return (match[1], int(match[2])) if match else (name, 0)

    for arc, observed in zip(expected, groups):
        _require(endpoint_log_fields(arc["source_endpoint"]) == (observed["source_name"], observed["source_index"])
                 and endpoint_log_fields(arc["destination_endpoint"]) == (observed["destination_name"], observed["destination_index"]),
                 f"Native endpoints differ at original arc {arc['index']}")
        _require(observed["created"] == 1, f"Native path-handle count differs at original arc {arc['index']}")
        _require(observed["delays"] == [(0, arc["rise_ps"]), (1, arc["fall_ps"])],
                 f"Native selected delay values/order differ at original arc {arc['index']}")
    return {"kind": "hullcirq-icarus13-interconnect-log-audit-v1", "input_inventory_sha256": _sha(json.dumps(inventory, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)),
            "simulation_log_text_sha256": _sha(log_text), "inventory_arc_count": len(expected), "bound_native_log_arc_count": len(groups),
            "bound_path_handle_log_count": sum(group["created"] for group in groups), "bound_delay_value_log_count": 2 * len(groups),
            "binding_complete": True, "unknown_annotation_warning_count": 0, "annotation_error_count": 0,
            "ignored_timingcheck_warning_count": len(warnings), "ignored_timingcheck_warnings": warnings,
            "native_delay_readback_executed": False, "full_sdf_equivalence": False,
            "timing_checks_supported_by_native_simulator": False,
            "scope": "Exact native pre-write interconnect log binding only; not delay readback, dynamic semantics or timing-check acceptance"}


ORIGINAL_SDF_SHA256 = "477b34cf25b9be2b0312ae34e1a4632590eecd31fe63d02518d7663d4b3f3702"


def original_metadata_diagnostics(sdf_text, log_text):
    """Classify the two exact metadata errors of the unmodified original SDF.

    This does not fill missing typical values, alter SDF, or establish native
    voltage/temperature annotation. The immutable source hash and exact source
    lines prevent this exception being applied to delays or arbitrary errors.
    """
    _require(_sha(sdf_text) == ORIGINAL_SDF_SHA256, "Metadata classification requires the exact original retained SDF")
    source_lines = sdf_text.splitlines()
    expected = [(9, "VOLTAGE", " (VOLTAGE 1.800::1.800)"), (11, "TEMPERATURE", " (TEMPERATURE 25.000::25.000)")]
    diagnostics = []
    observed = [line for line in log_text.splitlines() if "SDF ERROR:" in line]
    exact_errors = [f"SDF ERROR: input.sdf:{line}: Chosen value not defined." for line, _, _ in expected]
    _require(observed == exact_errors, "Native errors differ from the two exact original metadata empty-typ errors")
    for (line, field, raw), error in zip(expected, observed):
        _require(source_lines[line - 1] == raw, "Original SDF metadata line mismatch")
        diagnostics.append({"kind": "original_metadata_empty_typ", "field": field, "sdf_line": line, "original_source_line": raw,
                            "raw_native_error": error, "selected_metadata_value_established": False, "original_bytes_modified": False})
    return diagnostics


def audit_native_interconnect_log_v2(inventory, log_text, sdf_text):
    """Audit arcs while separately retaining exact original metadata errors.

    The previous all-errors-rejecting auditor and its failed attempts remain
    valid historical evidence. This narrowly pinned profile reports complete
    arc log binding alongside two unresolved metadata errors; it never returns
    a complete-SDF or timing-check success result.
    """
    _require(inventory.get("input_sdf_text_sha256") == ORIGINAL_SDF_SHA256, "Inventory must bind the exact original SDF")
    diagnostics = original_metadata_diagnostics(sdf_text, log_text)
    errors = {item["raw_native_error"] for item in diagnostics}
    arc_only_text = "\n".join(line for line in log_text.splitlines() if line not in errors)
    result = audit_native_interconnect_log(inventory, arc_only_text)
    result.update(kind="hullcirq-icarus13-original-sdf-interconnect-log-audit-v2",
                  profile="exact-original-metadata-empty-typ-v1", simulation_log_text_sha256=_sha(log_text),
                  classified_arc_only_log_text_sha256=_sha(arc_only_text), annotation_error_count=len(diagnostics),
                  interconnect_annotation_error_count=0, metadata_annotation_error_count=len(diagnostics),
                  metadata_diagnostics=diagnostics, original_sdf_text_sha256=_sha(sdf_text),
                  original_sdf_modified=False,
                  scope="Exact native interconnect pre-write log binding with two separately retained unresolved original metadata errors; not full SDF, readback, dynamic semantics or timing-check acceptance")
    return result

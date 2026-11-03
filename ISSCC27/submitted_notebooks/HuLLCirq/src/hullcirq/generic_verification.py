"""Finite, declarative cycle vectors for fixed-width synchronous digital RTL.

Expected values are supplied independently in the saved specification. No DUT,
model, Python expression, shell command or generated RTL computes the oracle.
All builders/validators here are pure; execution uses the existing fixed tools.
"""
from __future__ import annotations

import copy
from decimal import Decimal, InvalidOperation
import re

from .domain import DomainError, VERILOG_IDENTIFIER, VERILOG_KEYWORDS
from .verification import content_hash, object_hash

KIND = "generic_cycle_vectors"
TEMPLATE = "generic-cycle-vectors-v1"
TESTBENCH_MODULE = "__hullcirq_contract_tb"
MAX_CYCLES = 10000


def _require(condition, message, code="invalid_generic_cycle_contract"):
    if not condition:
        raise DomainError(code, message, 409)


def _identifier(value):
    return type(value) is str and bool(VERILOG_IDENTIFIER.fullmatch(value)) and value not in VERILOG_KEYWORDS


def _interface(value):
    _require(type(value) is dict and _identifier(value.get("module_name")) and type(value.get("ports")) is list,
             "Cycle verification needs a fixed public module interface.")
    ports = []
    for port in value["ports"]:
        _require(type(port) is dict and _identifier(port.get("name")) and port.get("direction") in ("input", "output")
                 and type(port.get("width")) is int and 1 <= port["width"] <= 4096 and type(port.get("signed")) is bool,
                 "Use plain named input/output ports, fixed widths from 1 to 4096, and explicit signedness.")
        ports.append({key: port[key] for key in ("name", "direction", "width", "signed")})
    _require(len({p["name"] for p in ports}) == len(ports), "Public physical port names must be unique.")
    clock, reset = value.get("clock"), value.get("reset")
    if type(clock) is str:
        clock = {"port": clock, "period_ns": value.get("clock_period_ns")}
    if type(reset) is str:
        reset = {"port": reset, "active": value.get("reset_active"), "kind": value.get("reset_kind")}
    _require(type(clock) is dict and set(clock) == {"port", "period_ns"} and _identifier(clock["port"])
             and type(reset) is dict and set(reset) == {"port", "active", "kind"}
             and _identifier(reset["port"]) and reset["port"] != clock["port"]
             and reset["kind"] == "synchronous" and reset["active"] in ("high", "low"),
             "Use one clock and one synchronous active-high or active-low reset.")
    _require(type(clock["period_ns"]) in (int, float), "Clock period must be a finite JSON number.")
    try:
        ticks = Decimal(str(clock["period_ns"])) * 1000
        _require(ticks.is_finite() and 4 <= ticks <= 1000000000 and ticks == ticks.to_integral_value() and int(ticks) % 2 == 0,
                 "Clock period must be from 0.004 to 1000000 ns on an even 1 ps grid (0.002 ns increments).")
    except InvalidOperation as error:
        raise DomainError("invalid_generic_cycle_contract", "Clock period must be finite.", 409) from error
    by_name = {p["name"]: p for p in ports}
    for name in (clock["port"], reset["port"]):
        _require(name in by_name and by_name[name] == {"name": name, "direction": "input", "width": 1, "signed": False},
                 "Clock and reset must be explicit unsigned one-bit input ports.")
    _require(any(p["direction"] == "output" for p in ports), "At least one observable output is required.")
    return {"module_name": value["module_name"], "ports": ports, "clock": copy.deepcopy(clock), "reset": copy.deepcopy(reset)}


def exact_integer(value):
    """Lossless JSON integer or canonical decimal text, never float/Boolean."""
    if type(value) is int:
        return value
    _require(type(value) is str and len(value) <= 1235 and re.fullmatch(r"(?:0|[1-9][0-9]*|-[1-9][0-9]*)", value) is not None,
             "Use an exact integer or canonical decimal string (no plus, leading zero, spaces, X/Z, fractions or don't-care).")
    return int(value)


def _value(number, port):
    width = port["width"]
    low = -(1 << (width - 1)) if port["signed"] else 0
    high = (1 << (width - (1 if port["signed"] else 0))) - 1
    integer = exact_integer(number)
    _require(low <= integer <= high,
             "Every drive/expected value must be an exact known integer in the declared signed/unsigned width: " + port["name"])
    return integer


def _contract(value, interface):
    _require(type(value) is dict and set(value) == {"kind", "version", "cycles"}
             and value["kind"] == KIND and type(value["version"]) is int and value["version"] == 1,
             "Use generic_cycle_vectors version 1 with only kind, version and cycles.")
    clock, reset = interface["clock"]["port"], interface["reset"]["port"]
    inputs = {p["name"]: p for p in interface["ports"] if p["direction"] == "input" and p["name"] not in (clock, reset)}
    outputs = {p["name"]: p for p in interface["ports"] if p["direction"] == "output"}
    cycles = value["cycles"]
    _require(type(cycles) is list and 2 <= len(cycles) <= MAX_CYCLES,
             "Save 2 to 10000 complete cycle vectors, including reset and non-reset operation.")
    for cycle in cycles:
        _require(type(cycle) is dict and set(cycle) == {"reset", "drive", "expect"}
                 and type(cycle["reset"]) is int and cycle["reset"] in (0, 1)
                 and type(cycle["drive"]) is dict and set(cycle["drive"]) == set(inputs)
                 and type(cycle["expect"]) is dict and set(cycle["expect"]) == set(outputs),
                 "Each cycle needs logical reset 0/1, every non-clock/reset input, and every output expectation; no omissions or don't-care values.")
        for key, ports in (("drive", inputs), ("expect", outputs)):
            for name, port in ports.items():
                _value(cycle[key][name], port)
    _require(cycles[0]["reset"] == 1 and any(c["reset"] == 0 for c in cycles),
             "The first cycle must assert synchronous reset and at least one saved cycle must exercise non-reset operation.")
    if inputs:
        initial_drive = {name: exact_integer(value) for name, value in cycles[0]["drive"].items()}
        _require(any({name: exact_integer(value) for name, value in c["drive"].items()} != initial_drive for c in cycles[1:]),
                 "Saved vectors must change at least one non-clock/reset input; reset-only or constant-input checks are insufficient.")
    return {"kind": KIND, "version": 1, "cycles": [
        {"reset": cycle["reset"], "drive": {name: cycle["drive"][name] for name in inputs},
         "expect": {name: cycle["expect"][name] for name in outputs}} for cycle in cycles]}


def _literal(value, width):
    return str(width) + "'h" + format(exact_integer(value) & ((1 << width) - 1), "x")


def _testbench(interface, contract, vector_hash, timing, testbench_module):
    clock, reset = interface["clock"]["port"], interface["reset"]["port"]
    names = {p["name"]: "hc_p" + str(i) for i, p in enumerate(interface["ports"])}
    ports = {p["name"]: p for p in interface["ports"]}
    lines = ["`timescale 1ps/1ps", "module " + testbench_module + ";",
             "// Saved independent vectors; no DUT-derived golden output."]
    for port in interface["ports"]:
        lines.append(("reg" if port["direction"] == "input" else "wire") + (" signed" if port["signed"] else "") +
                     (" [" + str(port["width"] - 1) + ":0]" if port["width"] > 1 else "") + " " + names[port["name"]] + ";")
    lines += [interface["module_name"] + " dut (" + ",".join("." + p["name"] + "(" + names[p["name"]] + ")" for p in interface["ports"]) + ");",
              "initial begin", names[clock] + "=0;"]
    for index, cycle in enumerate(contract["cycles"]):
        physical_reset = cycle["reset"] if interface["reset"]["active"] == "high" else 1 - cycle["reset"]
        lines += ["// Saved cycle " + str(index), names[reset] + "=1'b" + str(physical_reset) + ";"]
        lines += [names[name] + "=" + _literal(value, ports[name]["width"]) + ";" for name, value in cycle["drive"].items()]
        lines += ["#" + str(timing["half_period_ps"]) + "; " + names[clock] + "=1; #" + str(timing["sample_after_rising_ps"]) + ";"]
        for name, expected in cycle["expect"].items():
            observed = names[name]
            literal = _literal(expected, ports[name]["width"])
            lines += [f'$display("HULLCIRQ_CYCLE cycle={index} signal={name} value=%h", {observed});',
                      f'if ({observed} !== {literal}) begin $display("HULLCIRQ_FAIL cycle={index} phase=after signal={name} expected=%h actual=%h", {literal}, {observed}); $finish; end']
        lines.append("#" + str(timing["half_period_ps"] - timing["sample_after_rising_ps"]) + "; " + names[clock] + "=0;")
    lines += [f'$display("HULLCIRQ_PASS vectors={len(contract["cycles"])} vector_hash={vector_hash}");', "$finish;", "end", "endmodule", ""]
    return "\n".join(lines)


def build_cycle_plan(interface, contract, source_node_id=None, template_version=None, reserved_module_names=None):
    """Build exactly the saved expectations; never execute or inspect a DUT."""
    _require(template_version in (None, TEMPLATE), "Unsupported generic cycle testbench template.", "unsupported_verification_template")
    interface = _interface(interface)
    contract = _contract(contract, interface)
    _require(reserved_module_names is None or type(reserved_module_names) in (list, tuple)
             and all(_identifier(name) for name in reserved_module_names),
             "Reserved source module names must be plain Verilog identifiers.")
    reserved = sorted({interface["module_name"], *(reserved_module_names or [])})
    testbench_module = TESTBENCH_MODULE
    suffix = 0
    while testbench_module in reserved:
        suffix += 1
        testbench_module = TESTBENCH_MODULE + "_" + str(suffix)
    ticks = int(Decimal(str(interface["clock"]["period_ns"])) * 1000)
    timing = {"unit": "ps", "period_ps": ticks, "half_period_ps": ticks // 2,
              "sample_after_rising_ps": min(1000, ticks // 4), "drive_phase": "clock_low_before_next_rising_edge",
              "check_phase": "after_each_saved_rising_edge_including_first_reset"}
    vectors = copy.deepcopy(contract["cycles"])
    vector_hash = object_hash(vectors)
    trace = [{"cycle": i, "stimulus": {"reset": row["reset"], **copy.deepcopy(row["drive"])},
              "before": {}, "after": copy.deepcopy(row["expect"])} for i, row in enumerate(vectors)]
    testbench = _testbench(interface, contract, vector_hash, timing, testbench_module)
    return {"kind": KIND, "version": 1, "source_node_id": source_node_id, "module_name": interface["module_name"],
            "interface": interface, "contract": contract, "contract_hash": object_hash(contract),
            "vector_hash": vector_hash, "vector_count": len(vectors), "reference_trace": trace,
            "reference_trace_hash": object_hash(trace), "public_boundary_vectors": vectors,
            "public_boundary_vector_hash": vector_hash, "testbench": testbench,
            "testbench_sha256": content_hash(testbench), "testbench_module": testbench_module, "dut_instance": "dut",
            "reserved_module_names": reserved,
            "testbench_template_version": TEMPLATE, "stimulus_timing": timing,
            "signal_checks": [p["name"] for p in interface["ports"] if p["direction"] == "output"],
            "initialization_origin": "first_saved_cycle_asserting_synchronous_reset",
            "stimulus_origin": "saved_declarative_cycle_contract",
            "reference_origin": "independent_expected_values_in_saved_specification_not_DUT_output",
            "testbench_origin": "ordinary_program_from_complete_saved_drive_expect_cycles",
            "coverage": {"reset_cycles": sum(row["reset"] for row in vectors),
                         "non_reset_cycles": sum(not row["reset"] for row in vectors),
                         "output_assertions": sum(len(row["expect"]) for row in vectors),
                         "distinct_input_vectors": len({object_hash({name: exact_integer(value) for name, value in row["drive"].items()}) for row in vectors})},
            "limits": ["Finite saved cycle vectors only; not exhaustive or formal verification.",
                       "All expected outputs are independent saved requirements, not DUT-derived golden data.",
                       "One clock and synchronous reset, fixed-width Verilog-2005 ports, exact integers or canonical decimal strings only.",
                       "No propagation delay, CDC, analog behavior, general hierarchy recovery or physical qualification is established by this node test."]}


def build_node_plan(design, node_id, template_version=None):
    from .context import physical_interface
    nodes = [n for n in design.get("nodes", []) if n.get("id") == node_id]
    _require(len(nodes) == 1, "Verification requires one exact saved node.")
    interface = {**physical_interface(design, nodes[0]), "clock_period_ns": design["settings"]["clock_period_ns"]}
    return build_cycle_plan(interface, nodes[0].get("verification"), node_id, template_version)


def validate_cycle_plan(plan):
    _require(type(plan) is dict and plan.get("kind") == KIND, "A generic cycle plan is required.", "invalid_verification_plan")
    try:
        rebuilt = build_cycle_plan(plan["interface"], plan["contract"], plan["source_node_id"], plan["testbench_template_version"], plan["reserved_module_names"])
    except (KeyError, TypeError, ValueError) as error:
        raise DomainError("invalid_verification_plan", "The saved generic cycle plan cannot be rebuilt.", 409) from error
    _require(plan == rebuilt, "The saved generic plan, expected values, interface, timing or testbench changed.", "invalid_verification_plan")


def cycle_asserted_trace(plan):
    validate_cycle_plan(plan)
    return [{"cycle": row["cycle"], "stimulus": copy.deepcopy(row["stimulus"]), "asserted_before": {},
             "asserted_after": copy.deepcopy(row["after"]), "after_condition": "saved_rising_edge_plus_fixed_sample_offset",
             "predicate_assertions": [], "temporal_assertions": [], "conditional_assertions": []}
            for row in plan["reference_trace"]]


def parse_cycle_runtime(stdout, plan, stderr=""):
    """Require every actual sample, exact expected bits and one final pass marker."""
    validate_cycle_plan(plan)
    marker = f"HULLCIRQ_PASS vectors={plan['vector_count']} vector_hash={plan['vector_hash']}"
    errors, observed, order = [], {}, []
    if type(stdout) is not str:
        stdout = ""
    _require(type(stderr) is str, "Runtime stderr must remain the original text.", "invalid_generic_cycle_runtime")
    lines = stdout.splitlines()
    diagnostic_pattern = re.compile(r"^\s*(?:\*\*\s*)?(?:(?:ERROR|FATAL)(?=\s*[:\[]|\s*$)|UVM_(?:ERROR|FATAL)\b|(?:vvp|iverilog|Icarus Verilog)\s*:\s*(?:error|fatal)\b)", re.I)
    if any(diagnostic_pattern.match(line) for line in lines + stderr.splitlines()):
        errors.append("The simulator/model reported an ERROR or FATAL diagnostic.")
    if lines.count(marker) != 1 or "HULLCIRQ_FAIL" in stdout:
        errors.append("Missing exact pass marker, duplicate marker, or explicit failed assertion.")
    expected = {(i, name): value for i, row in enumerate(plan["contract"]["cycles"]) for name, value in row["expect"].items()}
    ports = {p["name"]: p for p in plan["interface"]["ports"]}
    for line in lines:
        if not line.startswith("HULLCIRQ_CYCLE"):
            continue
        match = re.fullmatch(r"HULLCIRQ_CYCLE cycle=(\d+) signal=([A-Za-z_][A-Za-z0-9_$]*) value=([0-9a-fA-FxXzZ]+)", line)
        if match is None:
            errors.append("Malformed cycle sample.")
            continue
        key = (int(match[1]), match[2])
        if key not in expected or key in observed or re.search("[xz]", match[3], re.I):
            errors.append("Unexpected, duplicate or unknown cycle sample.")
            continue
        value = int(match[3], 16)
        observed[key] = value
        order.append(key)
        if value != exact_integer(expected[key]) & ((1 << ports[key[1]]["width"]) - 1):
            errors.append("Actual cycle sample differs from the independent saved expectation.")
    if set(observed) != set(expected):
        errors.append("At least one required output sample is missing.")
    if order != list(expected):
        errors.append("Cycle output samples are not in the exact saved cycle/port order.")
    protocol_lines = [line for line in lines if line.startswith(("HULLCIRQ_CYCLE", "HULLCIRQ_PASS", "HULLCIRQ_FAIL"))]
    if not protocol_lines or protocol_lines[-1] != marker:
        errors.append("The exact pass marker must follow every required sample.")
    return {"validation_status": "Failed" if errors else "Passed", "scope": "all_saved_cycle_output_assertions_only",
            "vector_count": plan["vector_count"], "vector_hash": plan["vector_hash"],
            "checked_output_samples": len(observed), "required_output_samples": len(expected),
            "records": [{"cycle": cycle, "signal": name, "value": value} for (cycle, name), value in sorted(observed.items())],
            "diagnostics": [{"code": "generic_cycle_runtime_mismatch", "severity": "error", "message": message} for message in errors]}

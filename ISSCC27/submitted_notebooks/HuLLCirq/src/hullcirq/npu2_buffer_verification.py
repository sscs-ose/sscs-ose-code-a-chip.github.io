"""Finite buffer checks derived from the saved 2x2 graph and matrix job.

This adapter recognizes one explicit graph contract. It does not add a
verification field to the saved GUI design or substitute a different matrix.
"""
from __future__ import annotations

import copy
import re

from .context import build_node_context
from .domain import DomainError
from .verification import content_hash, object_hash

TEMPLATE = "npu2-original-job-buffer-v1"
KIND = "npu2_buffer_original_job"
NODE_ID = "npu2-buffer"
BEHAVIOR = "Two banks of sixteen stored unsigned byte bit patterns. External load_data[7:0]=byte, [11:8]=address, [12]=bank (0=A,1=B). A[r,k] is at r*8+k; B[k,c] is at k*2+c. Read index k returns operands[7:0]=A[k], [15:8]=A[8+k], [23:16]=B[2*k], [31:24]=B[2*k+1]. One registered response slot; a read transfer produces a response on the following cycle. Load takes priority over a read; neither accepts while a response is pending. Hold operands and valid under response backpressure; do not replace a just-consumed response with a new read in that same cycle. Synchronous reset cancels pending response but retains bank bytes; no initial byte contents are assumed. Top-level environment must load every address for the chosen K before accepting a configuration and must not offer loads during busy. No SRAM macro or retention after power loss is claimed."
CONSTRAINTS = {"latency_cycles": 1, "protocol": "valid_ready", "bank_depth": 16,
               "storage": "register_banks", "uninitialized_reads": "forbidden"}
EDGE_BEHAVIORS = {
    "read_index": "k=0..K-1 requests one row/column operand bundle; no read before source-job addressed bytes are loaded.",
    "operands": "Response contains A0k,A1k,Bk0,Bk1 in declared low-to-high byte order, held until accepted.",
}


def _require(value, message, code="unsupported_npu2_buffer_contract"):
    if not value:
        raise DomainError(code, message)


def physical_ports():
    ports = {"clk": ("input", 1, False), "rst": ("input", 1, False)}
    for name, direction, width in (("load_data", "input", 13), ("read_index", "input", 3), ("operands", "output", 32)):
        ports[name] = direction, width, False
        ports[name + "_valid"] = direction, 1, False
        ports[name + "_ready"] = ("output" if direction == "input" else "input"), 1, False
    return ports


def _recognize(contract):
    _require(type(contract) is dict and set(contract) == {"kind", "version", "source_node", "source_job", "source_edges", "settings", "global_integration", "design_intent"},
             "A complete saved graph/job contract is required.")
    _require(contract["kind"] == KIND and type(contract["version"]) is int and contract["version"] == 1,
             "Unsupported saved graph/job contract version.")
    node = contract["source_node"]
    _require(type(node) is dict and node.get("id") == NODE_ID and node.get("parent_id") is None
             and node.get("behavior") == BEHAVIOR and object_hash(node.get("constraints")) == object_hash(CONSTRAINTS)
             and node.get("verification") is None,
             "This adapter supports only the unchanged explicit 2x2 operand-buffer behavior and constraints.")
    _require(type(node.get("module_name")) is str and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", node["module_name"]),
             "A valid saved Verilog module name is required.")
    expected = {"load_data": ("input", 13), "read_index": ("input", 3), "operands": ("output", 32)}
    ports = node.get("ports")
    _require(type(ports) is list and len(ports) == 3 and {p.get("name") for p in ports if type(p) is dict} == set(expected),
             "The original three graph streams are required.")
    for port in ports:
        direction, width = expected[port["name"]]
        _require(port.get("direction") == direction and type(port.get("width")) is int and port["width"] == width
                 and port.get("signed") is False and port.get("protocol") == "valid_ready"
                 and port.get("clock") == "clk" and port.get("reset") == "rst", "Unsupported saved graph port.")
    _require(all(type(p.get("id")) is str for p in ports) and len({p["id"] for p in ports}) == 3,
             "The original graph streams require distinct textual port IDs.")
    settings = contract["settings"]
    _require(type(settings) is dict and all(settings.get(k) == v for k, v in {
        "clock_name": "clk", "reset_name": "rst", "reset_active": "high", "reset_kind": "synchronous", "rtl_language": "verilog_2005"}.items()),
        "The saved shared clock and synchronous high reset are required.")
    intent = contract["design_intent"]
    _require(type(intent) is dict and all(type(intent.get(k)) is int and intent[k] == v for k, v in {
        "matrix_rows": 2, "matrix_columns": 2, "operand_bits": 8, "accumulator_bits": 32, "k_min": 1, "k_max": 8}.items()),
        "The saved 2x2 INT8 design dimensions are required.")
    integration = contract["global_integration"]
    _require(type(integration) is dict
             and type(integration.get("public_streams")) is list
             and integration.get("external_load_rule") == "Load the addresses used by the saved job before configuration; gate load handshake off while busy."
             and integration.get("reset_contract") == "Synchronous high reset cancels all in-flight transfers and clears arithmetic/control/output state; operand register bank bytes are retained. No power-loss retention claim."
             and sum(p == {"node_id": NODE_ID, "port": "load_data", "direction": "input", "width": 13} for p in integration.get("public_streams", [])) == 1,
             "The saved public load and retained-bank reset contracts are required.")
    by_id = {port["id"]: port["name"] for port in ports}
    found = set()
    edges = contract["source_edges"]
    _require(type(edges) is list and len(edges) == 2, "Exactly the saved request/response edges are supported.")
    for edge in edges:
        _require(type(edge) is dict and edge.get("protocol") == "valid_ready", "Unsupported incident edge protocol.")
        source, target = edge.get("source", {}), edge.get("target", {})
        _require(type(source) is dict and type(target) is dict, "Structured incident edge endpoints are required.")
        if target.get("node_id") == NODE_ID:
            name = by_id.get(target.get("port_id"))
            _require(name == "read_index" and source == {"node_id": "npu2-scheduler", "port_id": "npu2-scheduler-read_index"}, "Unsupported request edge endpoints.")
        else:
            name = by_id.get(source.get("port_id"))
            _require(source.get("node_id") == NODE_ID and name == "operands"
                     and target == {"node_id": "npu2-scheduler", "port_id": "npu2-scheduler-operands"}, "Unsupported response edge endpoints.")
        _require(name not in found and edge.get("behavior") == EDGE_BEHAVIORS[name], "Modified or duplicate edge behavior is unsupported.")
        found.add(name)
    _require(found == set(EDGE_BEHAVIORS), "Both saved buffer edges are required.")
    job = contract["source_job"]
    _require(type(job) is dict and set(job) == {"id", "k", "A", "B", "bias", "relu", "scope"}
             and type(job["id"]) is str and bool(job["id"]) and type(job["scope"]) is str
             and type(job["k"]) is int and 1 <= job["k"] <= 8 and type(job["relu"]) is bool,
             "One supported saved matrix job is required.")
    k = job["k"]
    _require(type(job["A"]) is list and len(job["A"]) == 2 and all(type(row) is list and len(row) == k for row in job["A"])
             and type(job["B"]) is list and len(job["B"]) == k and all(type(row) is list and len(row) == 2 for row in job["B"])
             and all(type(v) is int and -128 <= v <= 127 for matrix in (job["A"], job["B"]) for row in matrix for v in row)
             and type(job["bias"]) is list and len(job["bias"]) == 2 and all(type(v) is int and -(1 << 31) <= v < (1 << 31) for v in job["bias"]),
             "Saved matrix dimensions, signed bytes and bias values must match the 2x2 job.")
    return contract


def load_packets(job):
    return [((row * 8 + k) << 8) | (job["A"][row][k] & 255) for row in range(2) for k in range(job["k"])] + [
        (1 << 12) | ((k * 2 + column) << 8) | (job["B"][k][column] & 255) for k in range(job["k"]) for column in range(2)]


def expand_vectors(contract):
    _recognize(contract)
    packets = load_packets(contract["source_job"])
    def vector(**changes):
        value = {"reset": 0, "load_data": packets[-1], "load_data_valid": 0,
                 "read_index": 0, "read_index_valid": 0, "operands_ready": 0}
        value.update(changes)
        return value
    vectors = [vector(reset=1)]
    vectors += [vector(load_data=packet, load_data_valid=1) for packet in packets]
    vectors += [vector(load_data_valid=1, read_index_valid=1),  # Repeat one original byte: load wins.
                vector(read_index_valid=1), vector(load_data_valid=1, read_index_valid=1),
                vector(load_data_valid=1, read_index_valid=1),
                vector(reset=1, load_data_valid=1, read_index_valid=1), vector()]
    for k in range(contract["source_job"]["k"]):
        next_k = min(k + 1, contract["source_job"]["k"] - 1)
        next_valid = int(k + 1 < contract["source_job"]["k"])
        # Offered inputs remain stable through response consumption and the
        # following load transfer. The next iteration then accepts that held
        # original-job read. Only synchronous reset cancels the prelude offers.
        vectors += [vector(read_index=k, read_index_valid=1),
                    vector(read_index=next_k, load_data_valid=1, read_index_valid=next_valid),
                    vector(read_index=next_k, load_data_valid=1, read_index_valid=next_valid),
                    vector(read_index=next_k, load_data_valid=1, read_index_valid=next_valid, operands_ready=1),
                    vector(read_index=next_k, load_data_valid=1, read_index_valid=next_valid)]
    vectors += [vector() for _ in range(3)]
    return vectors


def reference_trace(vectors):
    memory, pending, data = {}, 0, 0
    trace = []
    def outputs(vector):
        return {"load_data_ready": int(not pending), "read_index_ready": int(not pending and not vector["load_data_valid"]),
                "operands_valid": pending, "operands": data}
    for cycle, vector in enumerate(vectors):
        before = outputs(vector)
        load = int(not vector["reset"] and vector["load_data_valid"] and before["load_data_ready"])
        read = int(not vector["reset"] and vector["read_index_valid"] and before["read_index_ready"])
        response = int(not vector["reset"] and before["operands_valid"] and vector["operands_ready"])
        if vector["reset"]:
            pending = 0
        else:
            if load:
                memory[(vector["load_data"] >> 8) & 31] = vector["load_data"] & 255
            if read:
                k = vector["read_index"]
                addresses = [k, 8 + k, 16 + 2 * k, 16 + 2 * k + 1]
                _require(all(address in memory for address in addresses), "The original job projection must never read uninitialized bytes.")
                data = sum(memory[address] << (8 * byte) for byte, address in enumerate(addresses))
                pending = 1
            elif response:
                pending = 0
        trace.append({"cycle": cycle, "stimulus": copy.deepcopy(vector), "before": before, "after": outputs(vector),
                      "load_transfer": load, "read_transfer": read, "response_transfer": response})
    return trace


def asserted(values, vector):
    # Synchronous cancellation specifies the state after reset, not whether
    # ready/valid are additionally gated combinationally during asserted rst.
    if vector["reset"]:
        return {"operands_valid": 0}
    result = {key: values[key] for key in ("load_data_ready", "read_index_ready", "operands_valid")}
    if values["operands_valid"]:
        result["operands"] = values["operands"]
    return result


def testbench(module_name, trace, vector_hash):
    ports = physical_ports()
    lines = ["`timescale 1ns/1ps", "module hullcirq_contract_tb;", "reg clk;"]
    for name, (direction, width, _) in ports.items():
        if name != "clk":
            lines.append(f"{'reg' if direction == 'input' else 'wire'} {'' if width == 1 else f'[{width-1}:0] '}{name};")
    lines += [f"{module_name} dut (" + ", ".join(f".{name}({name})" for name in ports) + ");",
              "reg expected_valid; reg [31:0] expected_data;",
              "// Hold each offered original-job transaction until its actual handshake.",
              "// The 64-cycle wait is a finite test-harness progress bound, not a hardware timeout.",
              "task apply_step;", "input integer wait_kind; input target_valid; input [31:0] target_data; input integer step_number;",
              "integer attempt; reg taken;", "begin: step_body", "for(attempt=0;attempt<64;attempt=attempt+1) begin",
              "clk=0; #4; taken=0;",
              'if (!rst) begin',
              'if (operands_valid !== expected_valid) begin $display("HULLCIRQ_FAIL step=%0d before signal=operands_valid",step_number); $finish; end',
              'if (expected_valid && operands !== expected_data) begin $display("HULLCIRQ_FAIL step=%0d before signal=operands",step_number); $finish; end',
              'if (load_data_valid && load_data_ready !== 0 && load_data_ready !== 1) begin $display("HULLCIRQ_FAIL unknown load ready"); $finish; end',
              'if (read_index_valid && read_index_ready !== 0 && read_index_ready !== 1) begin $display("HULLCIRQ_FAIL unknown read ready"); $finish; end',
              'if (expected_valid && load_data_valid && load_data_ready !== 0) begin $display("HULLCIRQ_FAIL load accepted while response pending"); $finish; end',
              'if (expected_valid && read_index_valid && read_index_ready !== 0) begin $display("HULLCIRQ_FAIL read accepted while response pending"); $finish; end',
              'if (load_data_valid && read_index_valid && read_index_ready !== 0) begin $display("HULLCIRQ_FAIL load priority violated"); $finish; end',
              'if (wait_kind != 1 && load_data_valid && load_data_ready === 1) begin $display("HULLCIRQ_FAIL unexpected load transfer"); $finish; end',
              'if (wait_kind != 2 && read_index_valid && read_index_ready === 1) begin $display("HULLCIRQ_FAIL unexpected read transfer"); $finish; end',
              'if (wait_kind == 1) taken = load_data_valid && load_data_ready === 1;',
              'if (wait_kind == 2) taken = read_index_valid && read_index_ready === 1;',
              'end',
              'if (rst) expected_valid=0;',
              'else if (wait_kind == 0 || taken) begin expected_valid=target_valid; expected_data=target_data; end',
              '#1; clk=1; #1;',
              'if (operands_valid !== expected_valid) begin $display("HULLCIRQ_FAIL step=%0d after signal=operands_valid",step_number); $finish; end',
              'if (expected_valid && operands !== expected_data) begin $display("HULLCIRQ_FAIL step=%0d after signal=operands expected=%h actual=%h",step_number,expected_data,operands); $finish; end',
              '#4; clk=0;', 'if (wait_kind == 0 || taken) disable step_body;', 'end',
              '$display("HULLCIRQ_FAIL step=%0d finite harness progress bound reached",step_number); $finish;',
              'end', 'endtask', "initial begin", "clk=0; expected_valid=0; expected_data=0;"]
    for item in trace:
        cycle, vector = item["cycle"], item["stimulus"]
        lines += [f"// Saved GUI job projection cycle {cycle}", "clk=0;"]
        for name, (direction, width, _) in ports.items():
            if direction == "input" and name != "clk":
                lines.append(f"{name}={width}'h{vector['reset' if name == 'rst' else name]:x};")
        wait_kind = 1 if item["load_transfer"] else 2 if item["read_transfer"] else 0
        lines.append(f"apply_step({wait_kind},1'b{item['after']['operands_valid']},32'h{item['after']['operands']:08x},{cycle});")
    lines += [f'$display("HULLCIRQ_PASS vectors={len(trace)} vector_hash={vector_hash}");', "$finish;", "end", "endmodule", ""]
    return "\n".join(lines)


def _coverage(trace, contract):
    return {"load_transfers": sum(v["load_transfer"] for v in trace), "read_transfers": sum(v["read_transfer"] for v in trace),
            "response_transfers": sum(v["response_transfer"] for v in trace),
            "source_job_k": contract["source_job"]["k"], "unique_loaded_job_bytes": len(load_packets(contract["source_job"])),
            "reset_cycles": sum(v["stimulus"]["reset"] for v in trace),
            "reset_with_pending_response": sum(bool(v["stimulus"]["reset"] and v["before"]["operands_valid"]) for v in trace),
            "response_stall_cycles": sum(bool(not v["stimulus"]["reset"] and v["before"]["operands_valid"] and not v["stimulus"]["operands_ready"]) for v in trace),
            "load_priority_cycles": sum(bool(v["load_transfer"] and v["stimulus"]["read_index_valid"]) for v in trace),
            "consume_without_read_replacement_cycles": sum(bool(v["response_transfer"] and v["stimulus"]["read_index_valid"] and not v["read_transfer"]) for v in trace)}


def _plan(contract, node_input_hash):
    vectors = expand_vectors(contract)
    trace = reference_trace(vectors)
    vector_hash = object_hash(vectors)
    module_name = contract["source_node"]["module_name"]
    tb = testbench(module_name, trace, vector_hash)
    return {"kind": KIND, "version": 1, "source_node_id": NODE_ID, "module_name": module_name, "node_input_hash": node_input_hash,
            "contract": copy.deepcopy(contract), "contract_hash": object_hash(contract), "expanded_vectors": vectors, "vector_hash": vector_hash,
            "reference_trace": trace, "reference_trace_hash": object_hash(trace), "testbench": tb, "testbench_sha256": content_hash(tb), "vector_count": len(vectors),
            "testbench_template_version": TEMPLATE, "initialization_origin": "first_saved_job_projection_vector_asserting_synchronous_reset",
            "stimulus_origin": "original_design.verification_jobs[0]_and_exact_saved_buffer_node_edges_contract",
            "reference_origin": "ordinary_program_independent_two_bank_byte_state_machine",
            "testbench_origin": "ordinary_program_from_saved_job_projection_and_independent_reference",
            "stimulus_timing": "original_job_recipe_steps_with_actual_input_handshake_waits",
            "coverage": _coverage(trace, contract), "signal_checks": [name for name, (direction, _, _) in physical_ports().items() if direction == "output"],
            "limits": ["Finite projection of the one saved 2x2 matrix job; not exhaustive or formal verification.",
                       "Only job-addressed bytes are loaded and read; other bank addresses and K values are not verified.",
                       "Inactive output payload and ready gating during synchronous reset are unspecified and not asserted.",
                       "Reference trace is the earliest-acceptance recipe projection, not an assertion of eager input readiness or an observed DUT cycle trace.",
                       "Testbench holds each offered original-job payload until actual acceptance; each offer has a 64-cycle finite harness progress bound, not a circuit timeout requirement.",
                       "Reset retention is functional register behavior, not power-loss memory retention.",
                       "Load/read overlap exercises the local priority contract; no busy top-level system is simulated.",
                       "No cross-node integration, full-NPU behavior, synthesis, timing, layout, DRC, LVS or post-layout check is claimed."]}


def build_buffer_plan(design, node_id, template_version=None):
    _require(template_version in (None, TEMPLATE), "Unsupported 2x2 buffer testbench template.", "unsupported_verification_template")
    nodes = [node for node in design.get("nodes", []) if node.get("id") == node_id]
    _require(node_id == NODE_ID and len(nodes) == 1, "Select the saved explicit 2x2 operand buffer.")
    jobs = design.get("verification_jobs")
    _require(type(jobs) is list and len(jobs) == 1, "Exactly one saved original matrix job is required.")
    contract = {"kind": KIND, "version": 1, "source_node": copy.deepcopy(nodes[0]), "source_job": copy.deepcopy(jobs[0]),
                "source_edges": copy.deepcopy([edge for edge in design.get("edges", []) if any(edge.get(side, {}).get("node_id") == node_id for side in ("source", "target"))]),
                **{key: copy.deepcopy(design.get(key)) for key in ("settings", "global_integration", "design_intent")}}
    _recognize(contract)
    context = build_node_context(design, "verification-source", node_id)
    ports = {p["name"]: (p["direction"], p["width"], p["signed"]) for p in context["interface"]["ports"]}
    _require(ports == physical_ports(), "The expanded public interface must match the saved buffer streams.", "invalid_verification_interface")
    return _plan(contract, context["node_input_hash"])


def validate_buffer_plan(plan):
    try:
        valid = object_hash(plan) == object_hash(_plan(plan["contract"], plan["node_input_hash"]))
    except (KeyError, TypeError, ValueError, AttributeError, DomainError):
        valid = False
    _require(valid, "Frozen 2x2 original-job buffer evidence is inconsistent.", "invalid_verification_plan")

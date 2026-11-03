"""Compile a finite FIFO check from a recognized saved specification and job.

The profile is depth-two signed32, registered, ordered valid/ready storage.
Recognition is deliberately fail-closed; this is not an arbitrary natural
language-to-testbench compiler. No node ID or module name selects this profile.
"""
from __future__ import annotations

import copy
import re

from .context import build_node_context
from .domain import DomainError
from .verification import content_hash, object_hash

KIND = "fifo_original_job"
TEMPLATE = "fifo-saved-spec-original-job-v1"
BEHAVIOR = "Depth-two signed32 FIFO. Preserve accepted input order; output valid whenever nonempty and not in reset. Input ready when not full, or when a valid current head is being popped in that cycle. Support full simultaneous pop+push and pointer wrap. An empty push becomes a registered output on a later cycle, with no combinational bypass. Hold head and output valid under external stall. Raw output_transfer is exactly external output_data_valid && output_data_ready, including consecutive transfers; Job control counts this pulse. Reset empties queue and resets pointers/count but need not clear storage bits."
CONSTRAINTS = {"latency_cycles": 1, "protocol": "valid_ready", "depth": 2}
NUMERICAL_CONTRACT = "C[r,c] = signed32(sum_k(signed8(A[r,k])*signed8(B[k,c])) + signed32(bias[c])); ReLU, if configured, applies after the signed32 wrap."
RESET_CONTRACT = "Synchronous high reset cancels all in-flight transfers and clears arithmetic/control/output state; operand register bank bytes are retained. No power-loss retention claim."
QUANTITIES = ("", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen")
ORDINALS = ("", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth", "sixteenth")


def _require(value, message, code="unsupported_fifo_specification"):
    if not value:
        raise DomainError(code, message)


def recognizes_fifo_spec(node):
    """Candidate recognition only; build_fifo_plan validates every dependency."""
    return (type(node) is dict and node.get("verification") is None
            and (node.get("behavior") == BEHAVIOR
                 or type(node.get("constraints")) is dict and "depth" in node["constraints"]
                 and {p.get("name") for p in node.get("ports", []) if type(p) is dict}
                 == {"result_data", "output_data", "output_transfer"}))


def physical_ports(clock="clk", reset="rst"):
    return {clock: ("input", 1, False), reset: ("input", 1, False),
            "result_data": ("input", 32, True), "result_data_valid": ("input", 1, False),
            "result_data_ready": ("output", 1, False), "output_data": ("output", 32, True),
            "output_data_valid": ("output", 1, False), "output_data_ready": ("input", 1, False),
            "output_transfer": ("output", 1, False)}


def _job_projection(job, intent):
    _require(type(intent) is dict, "Saved matrix dimensions are required.")
    dimensions = (intent.get("matrix_rows"), intent.get("matrix_columns"), intent.get("k_min"), intent.get("k_max"))
    _require(all(type(v) is int and 1 <= v <= 16 for v in dimensions), "Supported saved matrix dimensions and K bounds are integers from 1 to 16.")
    rows, columns, k_min, k_max = dimensions
    _require(rows * columns <= 16 and k_min <= k_max
             and type(intent.get("operand_bits")) is int and intent["operand_bits"] == 8
             and type(intent.get("accumulator_bits")) is int and intent["accumulator_bits"] == 32,
             "This profile supports at most sixteen signed32 results from signed8 operands.")
    _require(type(job) is dict and set(job) == {"id", "k", "A", "B", "bias", "relu", "scope"}
             and type(job["id"]) is str and bool(job["id"]) and type(job["scope"]) is str
             and type(job["k"]) is int and k_min <= job["k"] <= k_max and type(job["relu"]) is bool,
             "One original typed matrix job is required.", "invalid_fifo_source_job")
    k = job["k"]
    _require(type(job["A"]) is list and len(job["A"]) == rows
             and all(type(row) is list and len(row) == k for row in job["A"])
             and type(job["B"]) is list and len(job["B"]) == k
             and all(type(row) is list and len(row) == columns for row in job["B"])
             and all(type(v) is int and -128 <= v <= 127 for matrix in (job["A"], job["B"]) for row in matrix for v in row)
             and type(job["bias"]) is list and len(job["bias"]) == columns
             and all(type(v) is int and -(1 << 31) <= v < (1 << 31) for v in job["bias"]),
             "The saved job matrices and signed values must match the saved dimensions.", "invalid_fifo_source_job")
    values = []
    for row in range(rows):
        for column in range(columns):
            value = (sum(job["A"][row][index] * job["B"][index][column] for index in range(k)) + job["bias"][column]) & 0xFFFFFFFF
            values.append(0 if job["relu"] and value & 0x80000000 else value)
    return values


def _recognize(contract):
    _require(type(contract) is dict and set(contract) == {"kind", "version", "source_node", "source_job", "source_edges", "settings", "design_intent", "global_integration"}
             and contract.get("kind") == KIND and type(contract.get("version")) is int and contract["version"] == 1,
             "A complete versioned saved FIFO specification and source job are required.")
    node, settings = contract["source_node"], contract["settings"]
    _require(type(node) is dict and type(node.get("id")) is str and bool(node["id"])
             and node.get("verification") is None and node.get("behavior") == BEHAVIOR
             and object_hash(node.get("constraints")) == object_hash(CONSTRAINTS)
             and type(node.get("test_expectations")) is str and bool(node["test_expectations"].strip()),
             "Only the recognized saved depth-two signed32 FIFO behavior and constraints are supported.")
    _require(type(node.get("module_name")) is str and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", node["module_name"]), "The saved module must be a plain Verilog identifier.")
    _require(type(settings) is dict and settings.get("reset_kind") == "synchronous" and settings.get("reset_active") == "high"
             and settings.get("rtl_language") == "verilog_2005"
             and all(type(settings.get(k)) is str and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", settings[k]) for k in ("clock_name", "reset_name")),
             "This profile needs the saved synchronous high reset and Verilog-2005 domain.")
    clock, reset = settings["clock_name"], settings["reset_name"]
    ports = node.get("ports")
    _require(type(ports) is list and len(ports) == 3 and all(type(p) is dict for p in ports)
             and {p.get("name") for p in ports} == {"result_data", "output_data", "output_transfer"}
             and all(type(p.get("id")) is str for p in ports) and len({p["id"] for p in ports}) == 3, "Three distinct saved FIFO graph ports are required.")
    by_name = {p["name"]: p for p in ports}
    for name, direction in (("result_data", "input"), ("output_data", "output"), ("output_transfer", "output")):
        port = by_name[name]; raw = name == "output_transfer"
        _require(port.get("direction") == direction and type(port.get("width")) is int and port["width"] == (1 if raw else 32)
                 and port.get("signed") is (not raw) and port.get("protocol") == ("raw" if raw else "valid_ready")
                 and port.get("clock") == clock and port.get("reset") == reset, "Saved FIFO port type, protocol and domain must match the profile.")
    _require(by_name["output_transfer"].get("sideband") == {"kind": "pulse", "associated_port_id": by_name["output_data"]["id"],
             "meaning": "output_data_valid && output_data_ready; consecutive transfer cycles produce consecutive high cycles."}, "The saved raw transfer pulse must count actual external handshakes.")
    values = _job_projection(contract["source_job"], contract["design_intent"])
    integration = contract["global_integration"]
    _require(type(integration) is dict and integration.get("numerical_contract") == NUMERICAL_CONTRACT
             and integration.get("reset_contract") == RESET_CONTRACT
             and type(integration.get("public_streams")) is list
             and sum(item == {"node_id": node["id"], "port": "output_data", "direction": "output", "width": 32, "signed": True}
                     for item in integration["public_streams"]) == 1, "The saved numerical projection, reset and external output boundary must match.")
    edges = contract["source_edges"]
    _require(type(edges) is list and len(edges) == 2 and all(type(edge) is dict for edge in edges), "This profile requires the saved result input and transfer-count edges.")
    expected = {
        "result_data": ("valid_ready", f"{QUANTITIES[len(values)]} bias-adjusted and optionally ReLU-clamped signed32 values in the same row-major order."),
        "output_transfer": ("raw", f"Count actual external transfers only; {ORDINALS[len(values)]} pulse completes current job, independent of scheduler dispatch.")}
    seen = set()
    for edge in edges:
        source, target = edge.get("source"), edge.get("target")
        _require(type(source) is dict and type(target) is dict, "Saved FIFO edge endpoints must be structured.")
        if target.get("node_id") == node["id"]:
            name = "result_data"
            _require(target.get("port_id") == by_name[name]["id"] and source.get("node_id") != node["id"], "The FIFO input edge must target its declared input.")
        else:
            name = "output_transfer"
            _require(source.get("node_id") == node["id"] and source.get("port_id") == by_name[name]["id"] and target.get("node_id") != node["id"], "The FIFO completion edge must source its declared pulse.")
        _require(name not in seen and (edge.get("protocol"), edge.get("behavior")) == expected[name], "Modified or duplicate saved FIFO edge behavior is unsupported.")
        seen.add(name)
    _require(seen == set(expected), "Both original FIFO edges are required.")
    return values


def _outputs(queue, vector):
    valid = int(not vector["reset"] and bool(queue))
    return {"result_data_ready": int(not vector["reset"] and (len(queue) < 2 or valid and vector["output_data_ready"])),
            "output_data_valid": valid, "output_data": queue[0] if queue else 0,
            "output_transfer": int(valid and vector["output_data_ready"])}


def fifo_reference_trace(vectors):
    """Independent Python queue and pointer bookkeeping; never reads a DUT."""
    queue, read_pointer, write_pointer = [], 0, 0
    trace = []
    for cycle, vector in enumerate(vectors):
        _require(type(vector) is dict and set(vector) == {"reset", "result_data", "result_data_valid", "output_data_ready", "reset_pulse_without_clock"}
                 and all(type(vector[k]) is int and vector[k] in (0, 1) for k in ("reset", "result_data_valid", "output_data_ready", "reset_pulse_without_clock"))
                 and not (vector["reset"] and vector["reset_pulse_without_clock"])
                 and type(vector["result_data"]) is int and 0 <= vector["result_data"] <= 0xFFFFFFFF, "FIFO vectors require exact typed bit patterns.", "invalid_fifo_vectors")
        before = _outputs(queue, vector)
        push, pop = vector["result_data_valid"] * before["result_data_ready"], before["output_transfer"]
        bookkeeping = {"queue_depth": len(queue), "read_pointer": read_pointer, "write_pointer": write_pointer}
        write_wrap, read_wrap = int(bool(push and write_pointer == 1)), int(bool(pop and read_pointer == 1))
        if vector["reset"]:
            queue, read_pointer, write_pointer = [], 0, 0
        else:
            if pop:
                queue.pop(0); read_pointer = (read_pointer + 1) % 2
            if push:
                queue.append(vector["result_data"]); write_pointer = (write_pointer + 1) % 2
        _require(len(queue) <= 2, "Independent FIFO reference overflowed.", "invalid_fifo_vectors")
        temporal = ([{"phase": "reset_asserted_without_clock", "asserted": {"output_data_valid": 0, "output_transfer": 0}},
                     {"phase": "reset_deasserted_before_clock", "asserted": _asserted(before, vector)}]
                    if vector["reset_pulse_without_clock"] else [])
        trace.append({"cycle": cycle, "stimulus": copy.deepcopy(vector), "before": before, "after": _outputs(queue, vector),
                      "input_transfer": push, "output_transfer": pop, "reference_bookkeeping": bookkeeping,
                      "write_pointer_wrap": write_wrap, "read_pointer_wrap": read_wrap, "temporal_assertions": temporal})
    return trace


def expand_fifo_vectors(contract):
    values = _recognize(contract)
    vectors = []
    def append(reset=0, value=0, valid=0, ready=0, pulse=0):
        vectors.append({"reset": reset, "result_data": value, "result_data_valid": valid, "output_data_ready": ready,
                        "reset_pulse_without_clock": pulse})
    append(reset=1); append(reset=1)
    # Boundary exercises repeat only payloads projected from the original job.
    append(value=values[0], valid=1)
    append(value=values[1 % len(values)], valid=1)
    for index in range(3):
        append(value=values[2 % len(values)], valid=1, pulse=int(index == 0))
    append(reset=1, value=values[2 % len(values)], valid=1, ready=1)
    append(reset=1)
    # Repeat the same complete job to exercise pointer wrap even for one result.
    # All decisions use this independent queue, never DUT readiness or output.
    for repetition in range(4):
        pending = []; index = consumed = cycle = 0
        while consumed < len(values):
            _require(cycle < 256, "Original-job FIFO recipe exceeded its finite bound.", "invalid_fifo_vectors")
            ready = (0, 0, 0, 1, 1, 0, 1)[cycle % 7] if repetition == 0 else 1
            value, valid = (values[index], 1) if index < len(values) else (0, 0)
            vector = {"reset": 0, "result_data": value, "result_data_valid": valid, "output_data_ready": ready,
                      "reset_pulse_without_clock": 0}
            before = _outputs(pending, vector)
            pop, push = before["output_transfer"], valid * before["result_data_ready"]
            if pop:
                pending.pop(0); consumed += 1
            if push:
                pending.append(value); index += 1
            vectors.append(vector); cycle += 1
        _require(index == len(values) and not pending, "Every original-job FIFO sequence must drain once in order.", "invalid_fifo_vectors")
        append(ready=1)
    append(); append()
    return vectors


def _asserted(values, vector):
    # Input-ready behavior during reset was not explicitly specified. Do not
    # turn one implementation's reset gating choice into an acceptance rule.
    result = {"output_data_valid": values["output_data_valid"], "output_transfer": values["output_transfer"]}
    if not vector["reset"]:
        result["result_data_ready"] = values["result_data_ready"]
    if values["output_data_valid"]:
        result["output_data"] = values["output_data"]
    return result


def fifo_asserted_trace(plan):
    return [{"cycle": item["cycle"], "stimulus": copy.deepcopy(item["stimulus"]),
             "input_transfer": item["input_transfer"], "output_transfer": item["output_transfer"],
             "asserted_before": _asserted(item["before"], item["stimulus"]) if item["cycle"] else None,
             "asserted_after": _asserted(item["after"], item["stimulus"]),
             "temporal_assertions": copy.deepcopy(item["temporal_assertions"])} for item in plan["reference_trace"]]


def _testbench(contract, trace, vector_hash):
    node, settings = contract["source_node"], contract["settings"]
    clock, reset = settings["clock_name"], settings["reset_name"]
    ports = physical_ports(clock, reset)
    lines = ["`timescale 1ns/1ps", "module hullcirq_contract_tb;"]
    lines += [f"{'reg' if direction == 'input' else 'wire'} {'' if width == 1 else f'[{width-1}:0] '}{name};"
              for name, (direction, width, _) in ports.items()]
    lines += [f"{node['module_name']} dut (" + ", ".join(f".{name}({name})" for name in ports) + ");", "initial begin", f"{clock}=0;"]
    for item in trace:
        cycle, vector = item["cycle"], item["stimulus"]
        lines += [f"// Saved specification / original job projection cycle {cycle}", f"{clock}=0;"]
        for name, (direction, width, _) in ports.items():
            if direction == "input" and name != clock:
                lines.append(f"{name}={width}'h{vector['reset' if name == reset else name]:x};")
        lines.append("#4;")
        for phase in ("before", "after"):
            if phase == "before" and cycle == 0:
                continue
            if phase == "after":
                lines.append(f"#1; {clock}=1; #1;")
            for name, value in _asserted(item[phase], vector).items():
                expected = f"{ports[name][1]}'h{value:x}"
                lines.append(f'if ({name} !== {expected}) begin $display("HULLCIRQ_FAIL cycle={cycle} phase={phase} signal={name} expected=%h actual=%h", {expected}, {name}); $finish; end')
            if phase == "before" and vector["reset_pulse_without_clock"]:
                # Pulse and restore reset with no intervening clock edge.
                # A synchronous FIFO must preserve its queued head/count.
                for index, temporal in enumerate(item["temporal_assertions"]):
                    lines.append(f"{reset}=1'b{int(index == 0)}; #1;")
                    for name, value in temporal["asserted"].items():
                        expected = f"{ports[name][1]}'h{value:x}"
                        lines.append(f'if ({name} !== {expected}) begin $display("HULLCIRQ_FAIL cycle={cycle} phase={temporal["phase"]} signal={name} expected=%h actual=%h", {expected}, {name}); $finish; end')
        lines.append(f"#4; {clock}=0;")
    lines += [f'$display("HULLCIRQ_PASS vectors={len(trace)} vector_hash={vector_hash}");', "$finish;", "end", "endmodule", ""]
    return "\n".join(lines)


def _coverage(trace, values):
    return {"input_transfers": sum(v["input_transfer"] for v in trace), "output_transfers": sum(v["output_transfer"] for v in trace),
            "source_job_result_count": len(values), "complete_original_job_repetitions": 4,
            "reset_cycles": sum(v["stimulus"]["reset"] for v in trace),
            "reset_pulses_without_clock": sum(v["stimulus"]["reset_pulse_without_clock"] for v in trace),
            "no_clock_reset_pulses_with_full_queue": sum(v["stimulus"]["reset_pulse_without_clock"] and v["reference_bookkeeping"]["queue_depth"] == 2 for v in trace),
            "reset_with_pending_output": sum(bool(v["stimulus"]["reset"] and v["reference_bookkeeping"]["queue_depth"]) for v in trace),
            "full_stall_cycles": sum(not v["stimulus"]["reset"] and v["reference_bookkeeping"]["queue_depth"] == 2 and not v["stimulus"]["output_data_ready"] for v in trace),
            "output_stall_cycles": sum(v["before"]["output_data_valid"] and not v["stimulus"]["output_data_ready"] for v in trace),
            "full_simultaneous_cycles": sum(v["reference_bookkeeping"]["queue_depth"] == 2 and v["input_transfer"] and v["output_transfer"] for v in trace),
            "simultaneous_cycles": sum(v["input_transfer"] and v["output_transfer"] for v in trace),
            "empty_registered_pushes": sum(not v["reference_bookkeeping"]["queue_depth"] and v["input_transfer"] for v in trace),
            "consecutive_output_transfers": sum(a["output_transfer"] and b["output_transfer"] for a, b in zip(trace, trace[1:])),
            "reference_write_pointer_wraps": sum(v["write_pointer_wrap"] for v in trace),
            "reference_read_pointer_wraps": sum(v["read_pointer_wrap"] for v in trace)}


def _plan(contract, node_input_hash):
    values = _recognize(contract); vectors = expand_fifo_vectors(contract); trace = fifo_reference_trace(vectors)
    vector_hash = object_hash(vectors); tb = _testbench(contract, trace, vector_hash)
    return {"kind": KIND, "version": 1, "source_node_id": contract["source_node"]["id"], "module_name": contract["source_node"]["module_name"],
            "node_input_hash": node_input_hash, "contract": copy.deepcopy(contract), "contract_hash": object_hash(contract),
            "source_job_hash": object_hash(contract["source_job"]), "projected_original_results": values,
            "compiled_requirements": {"kind": "registered_ordered_fifo", "depth": 2, "payload_bits": 32, "payload_signed": True,
                                      "input_stream": "result_data", "output_stream": "output_data", "transfer_pulse": "output_transfer",
                                      "full_simultaneous_pop_push": True, "empty_bypass": False, "synchronous_high_reset": True,
                                      "recognition": "finite_saved_specification_profile_v1"},
            "expanded_vectors": vectors, "vector_hash": vector_hash, "reference_trace": trace, "reference_trace_hash": object_hash(trace),
            "testbench": tb, "testbench_sha256": content_hash(tb), "vector_count": len(vectors), "testbench_template_version": TEMPLATE,
            "initialization_origin": "first_saved_job_projection_vector_asserting_synchronous_reset",
            "stimulus_origin": "original_design.verification_jobs[0]_projected_by_saved_numerical_contract_and_fifo_requirements",
            "reference_origin": "ordinary_program_independent_ordered_queue_and_signed_integer_job_projection",
            "testbench_origin": "ordinary_program_versioned_fifo_specification_compiler",
            "coverage": _coverage(trace, values), "signal_checks": [name for name, (direction, _, _) in physical_ports().items() if direction == "output"],
            "limits": ["Only the recognized saved depth-two signed32 registered FIFO profile is supported; arbitrary natural-language requirements are not compiled.",
                       "Finite protocol exercises repeat payloads from the one original GUI matrix job; no new numerical test job or payload is substituted.",
                       "Four complete repetitions test ordering and wrapping; reference pointer/count bookkeeping is not observed DUT internal state.",
                       "All ready/valid/pulse controls outside reset and valid output payloads are asserted before and after clock edges; inactive payload values and input ready during reset are unspecified.",
                       "Synchronous reset cancels a full queue; storage-bit clearing and power-up state before the first reset edge are not asserted.",
                       "One recorded no-clock reset pulse while full checks synchronous state retention and combinational output masking; it is a finite sampled temporal check, not an exhaustive reset proof.",
                       "The matrix projection supplies expected FIFO input values; this does not verify upstream arithmetic, cross-node integration, other job values, or all FIFO states.",
                       "No exhaustive/formal proof, PDK mapping, propagation delay, timing, layout, DRC, LVS or post-layout correctness is established."]}


def build_fifo_plan(design, node_id, template_version=None):
    _require(template_version in (None, TEMPLATE), "Unsupported FIFO saved-specification template.", "unsupported_verification_template")
    nodes = [node for node in design.get("nodes", []) if node.get("id") == node_id]
    _require(len(nodes) == 1, "Select exactly one saved FIFO source node.")
    jobs = design.get("verification_jobs")
    _require(type(jobs) is list and len(jobs) == 1, "Exactly one original saved matrix job must select the FIFO stimulus.", "invalid_fifo_source_job")
    contract = {"kind": KIND, "version": 1, "source_node": copy.deepcopy(nodes[0]), "source_job": copy.deepcopy(jobs[0]),
                "source_edges": copy.deepcopy([edge for edge in design.get("edges", []) if any(edge.get(side, {}).get("node_id") == node_id for side in ("source", "target"))]),
                **{key: copy.deepcopy(design.get(key)) for key in ("settings", "design_intent", "global_integration")}}
    _recognize(contract)
    context = build_node_context(design, "verification-source", node_id)
    ports = {p["name"]: (p["direction"], p["width"], p["signed"]) for p in context["interface"]["ports"]}
    _require(ports == physical_ports(context["interface"]["clock"], context["interface"]["reset"]), "Expanded saved FIFO interface must match the recognized profile.", "invalid_verification_interface")
    return _plan(contract, context["node_input_hash"])


def validate_fifo_plan(plan):
    try:
        valid = object_hash(plan) == object_hash(_plan(plan["contract"], plan["node_input_hash"]))
    except (KeyError, TypeError, ValueError, AttributeError, DomainError):
        valid = False
    _require(valid, "Frozen FIFO requirements, original job, vectors, reference or testbench are inconsistent.", "invalid_verification_plan")

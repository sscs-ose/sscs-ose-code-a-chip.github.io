"""Independent finite buffer/post/FIFO checks projected from the original job.

All environment vectors are expanded from the saved recipe and reference only,
then frozen for RTL/netlist reuse. No DUT response controls future stimulus.
"""
from __future__ import annotations

import copy

from .context import build_node_context
from .domain import DomainError
from .scheduler_verification import _job
from .verification import content_hash, object_hash

TEMPLATE = "npu-original-job-nodes-v1"
KINDS = {"npu_buffer_stream": "node-buffer", "npu_post_stream": "node-post", "npu_fifo_stream": "node-fifo"}
STREAMS = {
    "npu_buffer_stream": {"load_data": ("input", 16, False), "read_request": ("input", 16, False), "read_response": ("output", 16, False)},
    "npu_post_stream": {"acc_data": ("input", 32, True), "post_config": ("input", 129, False), "result_data": ("output", 32, True)},
    "npu_fifo_stream": {"result_data": ("input", 32, True), "output_data": ("output", 32, True)},
}


def _require(value, message, code="invalid_npu_node_contract"):
    if not value:
        raise DomainError(code, message)


def projected_job(job):
    """Independent signed integer arithmetic; no generated RTL is consulted."""
    _job(job)
    sums = [sum(job["A"][row][index] * job["B"][index][column] for index in range(job["k"])) & 0xFFFFFFFF
            for row in range(4) for column in range(4)]
    results = []
    for lane, value in enumerate(sums):
        value = (value + job["bias"][lane % 4]) & 0xFFFFFFFF
        if job["relu"] and value & 0x80000000:
            value = 0
        results.append(value)
    return {"accumulators": sums, "results": results,
            "post_config": int(job["relu"]) | sum((value & 0xFFFFFFFF) << (1 + 32 * index) for index, value in enumerate(job["bias"]))}


def _contract(contract):
    _require(type(contract) is dict and set(contract) == {"kind", "version", "source_job", "exercise"}
             and contract.get("kind") in KINDS and type(contract.get("version")) is int and contract["version"] == 1,
             "Use one supported original-job node contract version 1 with exact fields.")
    _job(contract["source_job"])
    _require(type(contract["exercise"]) is dict and contract["exercise"] == {"kind": "original_job_projection_v1"},
             "Unsupported or modified original-job exercise recipe.")
    return contract


def _physical(kind):
    ports = {"clk": ("input", 1, False), "rst": ("input", 1, False)}
    for name, (direction, width, signed) in STREAMS[kind].items():
        ports[name] = direction, width, signed
        ports[name + "_valid"] = direction, 1, False
        ports[name + "_ready"] = "output" if direction == "input" else "input", 1, False
    if kind == "npu_fifo_stream":
        ports["output_transfer"] = "output", 1, False
    return ports


def _initial(kind):
    if kind == "npu_buffer_stream":
        return {"memory": {}, "valid": 0, "data": 0}
    if kind == "npu_post_stream":
        return {"configured": 0, "column": 0, "config": 0, "valid": 0, "data": 0}
    return {"queue": []}


def _outputs(kind, state, vector):
    enabled = not vector["reset"]
    if kind == "npu_buffer_stream":
        return {"load_data_ready": int(enabled and not state["valid"] and not (vector["load_data"] & 0x8000)),
                "read_request_ready": int(enabled and not state["valid"] and not vector["load_data_valid"] and not (vector["read_request"] & 0xC0C0)),
                "read_response_valid": int(enabled and state["valid"]), "read_response": state["data"]}
    if kind == "npu_post_stream":
        return {"post_config_ready": int(enabled and not state["valid"] and state["column"] == 0),
                "acc_data_ready": int(enabled and state["configured"] and (not state["valid"] or vector["result_data_ready"]) and not vector["post_config_valid"]),
                "result_data_valid": int(enabled and state["valid"]), "result_data": state["data"]}
    valid = int(enabled and bool(state["queue"]))
    return {"result_data_ready": int(enabled and (len(state["queue"]) < 2 or vector["output_data_ready"] and valid)),
            "output_data_valid": valid, "output_data": state["queue"][0] if state["queue"] else 0,
            "output_transfer": int(valid and vector["output_data_ready"])}


def _step(kind, state, vector):
    before = _outputs(kind, state, vector)
    transfers = {}
    for name, (direction, _, _) in STREAMS[kind].items():
        transfers[name + "_transfer"] = int((vector[name + "_valid"] if direction == "input" else before[name + "_valid"])
                                            and (before[name + "_ready"] if direction == "input" else vector[name + "_ready"]))
    after = copy.deepcopy(state)
    if vector["reset"]:
        if kind == "npu_buffer_stream":
            after.update(valid=0)  # Stored operand bytes deliberately survive reset.
        else:
            after = _initial(kind)
    elif kind == "npu_buffer_stream":
        if transfers["load_data_transfer"]:
            packet = vector["load_data"]
            after["memory"][(packet >> 8) & 127] = packet & 255
        if transfers["read_request_transfer"]:
            packet = vector["read_request"]
            a, b = packet & 63, 64 | ((packet >> 8) & 63)
            _require(a in state["memory"] and b in state["memory"], "The saved projection must not read uninitialized operand bytes.")
            after.update(valid=1, data=state["memory"][a] | state["memory"][b] << 8)
        elif transfers["read_response_transfer"]:
            after["valid"] = 0
    elif kind == "npu_post_stream":
        if transfers["post_config_transfer"]:
            after.update(configured=1, config=vector["post_config"], column=0)
        if transfers["acc_data_transfer"]:
            bias = (state["config"] >> (1 + 32 * state["column"])) & 0xFFFFFFFF
            data = (vector["acc_data"] + bias) & 0xFFFFFFFF
            if state["config"] & 1 and data & 0x80000000:
                data = 0
            after.update(valid=1, data=data, column=(state["column"] + 1) % 4)
        elif transfers["result_data_transfer"]:
            after["valid"] = 0
    else:
        if transfers["output_data_transfer"]:
            after["queue"].pop(0)
        if transfers["result_data_transfer"]:
            after["queue"].append(vector["result_data"])
        _require(len(after["queue"]) <= 2, "Independent depth-two queue overflowed.")
    return after, before, _outputs(kind, after, vector), transfers


def nodes_reference_trace(kind, vectors):
    _require(kind in KINDS, "Unsupported node reference kind.")
    state, trace = _initial(kind), []
    for cycle, vector in enumerate(vectors):
        after_state, before, after, transfers = _step(kind, state, vector)
        # This reference bookkeeping is not exported as an observed DUT state.
        bookkeeping = {"queue_depth": len(state["queue"])} if kind == "npu_fifo_stream" else {
            "response_pending": state["valid"], **({"column": state["column"], "configured": state["configured"]} if kind == "npu_post_stream" else {})}
        trace.append({"cycle": cycle, "stimulus": copy.deepcopy(vector), "before": before, "after": after, **transfers,
                      "reference_bookkeeping": bookkeeping})
        state = after_state
    return trace


def expand_nodes_vectors(contract):
    _contract(contract)
    kind, job = contract["kind"], contract["source_job"]
    projection = projected_job(job)
    state, vectors = _initial(kind), []
    def base(**updates):
        result = {"reset": 0}
        for name, (direction, _, _) in STREAMS[kind].items():
            if direction == "input":
                result.update({name: 0, name + "_valid": 0})
            else:
                result[name + "_ready"] = 0
        result.update(updates)
        return result
    def append(vector):
        nonlocal state
        _require(len(vectors) < 2000, "Original-job recipe exceeded the finite cycle bound.")
        state, before, after, transfers = _step(kind, state, vector)
        vectors.append(vector)
        return before, after, transfers
    append(base(reset=1)); append(base(reset=1))
    if kind == "npu_buffer_stream":
        loads = [(row * 16 + index, job["A"][row][index]) for row in range(4) for index in range(job["k"])]
        loads += [(64 | (index * 4 + column), job["B"][index][column]) for index in range(job["k"]) for column in range(4)]
        # A read offer is held throughout all loads to verify load priority.
        for address, value in loads:
            append(base(load_data=(address << 8) | (value & 255), load_data_valid=1, read_request_valid=1))
        _, _, transfer = append(base(read_request_valid=1))
        _require(transfer["read_request_transfer"], "The held first read must follow the completed loads.")
        for _ in range(3):
            append(base())
        append(base(reset=1)); append(base(reset=1))
        for stream, invalid in (("load_data", 0x8000), ("read_request", 0xC0C0)):
            for _ in range(2):
                append(base(**{stream: invalid, stream + "_valid": 1}))
            append(base(reset=1, **{stream: invalid, stream + "_valid": 1}))
        requests = [row * 16 + index | (index * 4 + column) << 8 for row in range(4) for column in range(4) for index in range(job["k"])]
        index = consumed = cycle = 0
        while consumed < len(requests):
            vector = base(read_request=requests[index] if index < len(requests) else 0,
                          read_request_valid=int(index < len(requests)), read_response_ready=[0, 0, 1, 1, 1][cycle % 5])
            _, _, transfers = append(vector)
            index += transfers["read_request_transfer"]; consumed += transfers["read_response_transfer"]; cycle += 1
        _require(index == len(requests), "Every source-derived read must be accepted once.")
    elif kind == "npu_post_stream":
        config = projection["post_config"]
        append(base(post_config=config, post_config_valid=1))
        # Isolate the row-boundary rule from output-slot backpressure: drain
        # one original product-sum result, then hold a config at empty col1.
        append(base(acc_data=projection["accumulators"][0], acc_data_valid=1, result_data_ready=1))
        append(base(result_data_ready=1))
        append(base(post_config=config, post_config_valid=1))
        append(base(post_config=config, post_config_valid=1))
        append(base(reset=1, post_config=config, post_config_valid=1)); append(base(reset=1))
        append(base(post_config=config, post_config_valid=1))
        index = cycle = 0
        while index < 5:
            _, _, transfers = append(base(acc_data=projection["accumulators"][index], acc_data_valid=1,
                                          result_data_ready=[0, 0, 1, 1, 1][cycle % 5]))
            index += transfers["acc_data_transfer"]; cycle += 1
        # Mid-row overlapping configuration cannot be accepted; the saved
        # reset cancels its stable held offer and the pending fifth output.
        append(base(post_config=config, post_config_valid=1))
        append(base(reset=1, post_config=config, post_config_valid=1)); append(base(reset=1))
        append(base(post_config=config, post_config_valid=1))
        index = consumed = cycle = 0
        while consumed < 16:
            _, _, transfers = append(base(acc_data=projection["accumulators"][index] if index < 16 else 0,
                                          acc_data_valid=int(index < 16), result_data_ready=[0, 0, 1, 1, 1][cycle % 5]))
            index += transfers["acc_data_transfer"]; consumed += transfers["result_data_transfer"]; cycle += 1
        _require(index == 16 and state["column"] == 0, "The complete original row-major job must end on a row boundary.")
        append(base(post_config=config, post_config_valid=1))  # Allowed between rows, after output drain.
    else:
        values = projection["results"]
        append(base(result_data=values[0], result_data_valid=1))
        append(base(result_data=values[1], result_data_valid=1))
        for _ in range(3):
            append(base(result_data=values[2], result_data_valid=1))
        append(base(reset=1, result_data=values[2], result_data_valid=1)); append(base(reset=1))
        index = consumed = cycle = 0
        while consumed < 16:
            _, _, transfers = append(base(result_data=values[index] if index < 16 else 0,
                                          result_data_valid=int(index < 16), output_data_ready=[0, 0, 0, 1, 1, 0, 1][cycle % 7]))
            index += transfers["result_data_transfer"]; consumed += transfers["output_data_transfer"]; cycle += 1
        _require(index == 16 and not state["queue"], "The final complete FIFO sequence must drain exactly once in order.")
    for _ in range(4):
        append(base())
    return vectors


def _asserted(kind, values):
    result = {}
    for name, (direction, _, _) in STREAMS[kind].items():
        if direction == "input":
            result[name + "_ready"] = values[name + "_ready"]
        else:
            result[name + "_valid"] = values[name + "_valid"]
            if values[name + "_valid"]:
                result[name] = values[name]
    if kind == "npu_fifo_stream":
        result["output_transfer"] = values["output_transfer"]
    return result


def nodes_asserted_trace(plan):
    return [{"cycle": item["cycle"], "stimulus": copy.deepcopy(item["stimulus"]),
             **{key: value for key, value in item.items() if key.endswith("_transfer")},
             "asserted_before": _asserted(plan["kind"], item["before"]) if item["cycle"] else None,
             "asserted_after": _asserted(plan["kind"], item["after"])} for item in plan["reference_trace"]]


def _testbench(kind, module, trace, vector_hash):
    ports = _physical(kind)
    inputs = {name: width for name, (direction, width, _) in ports.items() if direction == "input" and name != "clk"}
    outputs = {name: width for name, (direction, width, _) in ports.items() if direction == "output"}
    lines = ["`timescale 1ns/1ps", "module hullcirq_contract_tb;", "reg clk;"]
    lines += [f"reg {'' if width == 1 else f'[{width-1}:0] '}{name};" for name, width in inputs.items()]
    lines += [f"wire {'' if width == 1 else f'[{width-1}:0] '}{name};" for name, width in outputs.items()]
    lines += [f"{module} dut (" + ", ".join(f".{name}({name})" for name in ports) + ");", "initial begin", "clk=0;"]
    for item in trace:
        cycle = item["cycle"]
        lines += [f"// Original GUI job projection cycle {cycle}", "clk=0;"]
        for name, width in inputs.items():
            value = item["stimulus"]["reset" if name == "rst" else name]
            lines.append(f"{name}={width}'h{value:x};")
        lines.append("#4;")
        for phase in ("before", "after"):
            if phase == "before" and cycle == 0:
                continue
            if phase == "after":
                lines.append("#1; clk=1; #1;")
            for name, value in _asserted(kind, item[phase]).items():
                expected = f"{outputs[name]}'h{value:x}"
                lines.append(f'if ({name} !== {expected}) begin $display("HULLCIRQ_FAIL cycle={cycle} phase={phase} signal={name} expected=%h actual=%h", {expected}, {name}); $finish; end')
        lines.append("#4; clk=0;")
    lines += [f'$display("HULLCIRQ_PASS vectors={len(trace)} vector_hash={vector_hash}");', "$finish;", "end", "endmodule", ""]
    return "\n".join(lines)


def _coverage(kind, trace):
    transfer_names = [name + "_transfer" for name in STREAMS[kind]]
    result = {name + "s": sum(item[name] for item in trace) for name in transfer_names}
    output = next(name for name, (direction, _, _) in STREAMS[kind].items() if direction == "output")
    result.update(reset_cycles=sum(item["stimulus"]["reset"] for item in trace),
                  output_stall_cycles=sum(item["before"][output + "_valid"] and not item["stimulus"][output + "_ready"] for item in trace),
                  reset_with_pending_output=sum(item["stimulus"]["reset"] and bool(item["reference_bookkeeping"].get("queue_depth", item["reference_bookkeeping"].get("response_pending", 0))) for item in trace))
    if kind == "npu_buffer_stream":
        result.update(load_priority_cycles=sum(not item["stimulus"]["reset"] and item["stimulus"]["load_data_valid"] and item["stimulus"]["read_request_valid"] for item in trace),
                      invalid_load_cycles=sum(not item["stimulus"]["reset"] and item["stimulus"]["load_data_valid"] and bool(item["stimulus"]["load_data"] & 0x8000) for item in trace),
                      invalid_read_cycles=sum(not item["stimulus"]["reset"] and item["stimulus"]["read_request_valid"] and bool(item["stimulus"]["read_request"] & 0xC0C0) for item in trace))
        # This is a count of completed source-derived response assertions, not
        # an observation of physical memory contents or retention technology.
        result["retained_memory_response_transfers"] = result["read_response_transfers"]
    elif kind == "npu_post_stream":
        result.update(simultaneous_replace_cycles=sum(item["acc_data_transfer"] and item["result_data_transfer"] for item in trace),
                      rejected_midrow_config_cycles=sum(not item["stimulus"]["reset"] and item["stimulus"]["post_config_valid"] and item["reference_bookkeeping"]["column"] != 0 for item in trace),
                      complete_original_results=16)
    else:
        result.update(full_stall_cycles=sum(not item["stimulus"]["reset"] and item["reference_bookkeeping"]["queue_depth"] == 2 and not item["stimulus"]["output_data_ready"] for item in trace),
                      full_simultaneous_cycles=sum(item["reference_bookkeeping"]["queue_depth"] == 2 and item["result_data_transfer"] and item["output_data_transfer"] for item in trace),
                      simultaneous_cycles=sum(item["result_data_transfer"] and item["output_data_transfer"] for item in trace),
                      complete_original_results=16)
    return result


def build_nodes_plan(design, node_id, template_version=None):
    _require(template_version in (None, TEMPLATE), "Unsupported node testbench template.", "unsupported_verification_template")
    nodes = [node for node in design.get("nodes", []) if node.get("id") == node_id]
    _require(len(nodes) == 1, "Select exactly one original source node.")
    contract = _contract(nodes[0].get("verification"))
    kind = contract["kind"]
    _require(KINDS[kind] == node_id, "Contract kind does not match this supported node ID.")
    jobs = design.get("verification_jobs", [])
    _require(type(jobs) is list and all(type(job) is dict for job in jobs), "Canonical jobs must be a list of structured objects.")
    matches = [job for job in jobs if job.get("id") == contract["source_job"]["id"]]
    _require(len(matches) == 1, "The canonical original job must exist exactly once.")
    _job(matches[0]); _require(object_hash(matches[0]) == object_hash(contract["source_job"]), "Copied source job and canonical original job must match exactly, including types.")
    context = build_node_context(design, "verification-source", node_id)
    expected = _physical(kind)
    ports = {port["name"]: port for port in context["interface"]["ports"]}
    _require(set(ports) == set(expected) and all((ports[name]["direction"], ports[name]["width"], ports[name]["signed"]) == value for name, value in expected.items()),
             "The contract requires its exact existing public streams, widths, signedness and clock/reset.", "invalid_verification_interface")
    vectors = expand_nodes_vectors(contract)
    vector_hash = object_hash(vectors)
    trace = nodes_reference_trace(kind, vectors)
    tb = _testbench(kind, context["interface"]["module_name"], trace, vector_hash)
    return {"kind": kind, "version": 1, "source_node_id": node_id, "module_name": context["interface"]["module_name"], "node_input_hash": context["node_input_hash"],
            "contract": copy.deepcopy(contract), "contract_hash": object_hash(contract), "expanded_vectors": vectors, "vector_hash": vector_hash,
            "reference_trace": trace, "reference_trace_hash": object_hash(trace), "testbench": tb, "testbench_sha256": content_hash(tb), "vector_count": len(trace),
            "testbench_template_version": TEMPLATE, "initialization_origin": "first_original_gui_projection_vector_asserting_synchronous_reset",
            "stimulus_origin": "original_design_node.verification.source_job_and_saved_exercise",
            "reference_origin": "ordinary_program_independent_node_state_machine_and_signed_integer_projection",
            "testbench_origin": "ordinary_program_from_original_job_expanded_vectors_and_independent_reference",
            "coverage": _coverage(kind, trace), "signal_checks": [name for name, (direction, _, _) in expected.items() if direction == "output"],
            "limits": ["Finite projection of one original GUI matrix job only; not exhaustive or formal verification.",
                       "Reference bookkeeping is an expectation, not observed DUT internal state or an independently captured waveform.",
                       "Only valid public output payloads and all handshake controls are asserted; inactive payload values are unspecified.",
                       "Source job ReLU mode is preserved; an unexercised mode is not verified by this projection.",
                       "These node checks do not establish real cross-node integration, full NPU completion or global RTL correctness.",
                       "Buffer reset retention is finite functional register behavior, not a physical memory-retention result.",
                       "No propagation delay, PDK mapping, timing, layout, DRC, LVS or post-layout verification is checked.",
                       "Power-up state before the first original synchronous reset edge is not observed or assumed."]}


def validate_nodes_plan(plan):
    try:
        contract = _contract(plan["contract"])
        kind = contract["kind"]
        vectors = expand_nodes_vectors(contract); trace = nodes_reference_trace(kind, vectors)
        vector_hash = object_hash(vectors); tb = _testbench(kind, plan["module_name"], trace, vector_hash)
        valid = (plan["kind"] == kind and type(plan["version"]) is int and plan["version"] == 1 and plan["testbench_template_version"] == TEMPLATE
                 and plan["contract_hash"] == object_hash(contract) and plan["expanded_vectors"] == vectors and plan["vector_hash"] == vector_hash
                 and plan["reference_trace"] == trace and plan["reference_trace_hash"] == object_hash(trace)
                 and plan["testbench"] == tb and plan["testbench_sha256"] == content_hash(tb) and plan["vector_count"] == len(vectors)
                 and plan["coverage"] == _coverage(kind, trace)
                 and plan["signal_checks"] == [name for name, (direction, _, _) in _physical(kind).items() if direction == "output"])
    except (KeyError, TypeError, ValueError, DomainError):
        valid = False
    _require(valid, "Frozen original-job node vectors, reference, coverage or testbench are inconsistent.", "invalid_verification_plan")

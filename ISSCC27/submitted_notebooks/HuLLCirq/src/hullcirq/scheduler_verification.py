"""Finite scheduler verification from one original GUI-saved matrix job.

The exercise recipe is part of the GUI specification. An ordinary program
expands it once using an independent state machine, never DUT observations.
The exact expanded vectors/reference/TB are frozen for RTL and netlist checks.
"""
from __future__ import annotations

import copy

from .context import build_node_context
from .domain import DomainError
from .verification import content_hash, object_hash

TEMPLATE = "scheduler-original-job-v1"
CONTROL_SIGNALS = ("schedule_config_ready", "read_request_valid", "read_response_ready",
                   "pair_data_valid", "pe_clear", "schedule_done")
SIGNAL_WIDTHS = {**{name: 1 for name in CONTROL_SIGNALS}, "read_request": 16, "pair_data": 16, "pair_meta": 6}
VECTOR_KEYS = {"reset", "config_valid", "config_data", "request_ready", "response_valid", "response_data", "pair_ready"}


def _require(condition, message, code="invalid_scheduler_contract"):
    if not condition:
        raise DomainError(code, message)


def _job(job):
    _require(type(job) is dict and type(job.get("id")) is str and job["id"], "Copy one named original verification job.")
    k = job.get("k")
    _require(type(k) is int and 1 <= k <= 16, "Original scheduler job K must be an integer in 1..16.")
    for key, rows, columns in (("A", 4, k), ("B", k, 4)):
        matrix = job.get(key)
        _require(type(matrix) is list and len(matrix) == rows and all(type(row) is list and len(row) == columns for row in matrix)
                 and all(type(value) is int and -128 <= value <= 127 for row in matrix for value in row),
                 f"Original {key} must have its declared dimensions and signed INT8 values.")
    _require(type(job.get("bias")) is list and len(job["bias"]) == 4
             and all(type(value) is int and -(1 << 31) <= value < (1 << 31) for value in job["bias"])
             and type(job.get("relu")) is bool, "Copy the original four INT32 biases and Boolean ReLU setting.")
    return job


def pack_configuration(job):
    """K[4:0], ReLU[5], four signed bias bit-vectors at [6+32*i+:32]."""
    _job(job)
    return job["k"] | int(job["relu"]) << 5 | sum((value & 0xFFFFFFFF) << (6 + 32 * index) for index, value in enumerate(job["bias"]))


def validate_contract(contract):
    _require(type(contract) is dict and set(contract) == {"kind", "version", "source_job", "exercise"}
             and contract["kind"] == "npu_scheduler_stream" and type(contract["version"]) is int and contract["version"] == 1,
             "Scheduler verification requires npu_scheduler_stream version 1 and exact contract fields.")
    job = _job(contract["source_job"])
    exercise = contract["exercise"]
    fields = {"kind", "request_ready_pattern", "pair_ready_pattern", "response_delays", "cancel_after_pair_transfers", "cancel_states", "invalid_k"}
    _require(type(exercise) is dict and set(exercise) == fields and exercise["kind"] == "complete_cancel_restart_v1", "Unsupported saved scheduler exercise recipe.")
    for key in ("request_ready_pattern", "pair_ready_pattern"):
        values = exercise[key]
        _require(type(values) is list and 1 <= len(values) <= 16
                 and all(type(value) is int and value in (0, 1) for value in values) and 0 in values and 1 in values,
                 "Saved sink ready patterns require both stalls and transfers.")
    delays = exercise["response_delays"]
    _require(type(delays) is list and 1 <= len(delays) <= 16 and all(type(value) is int and 0 <= value <= 8 for value in delays)
             and any(value > 0 for value in delays), "Saved response delays must be bounded nonnegative integers including a delay.")
    _require(type(exercise["cancel_after_pair_transfers"]) is int and 0 < exercise["cancel_after_pair_transfers"] < 16 * job["k"],
             "Cancellation must occur after a nonempty prefix of the same original job.")
    _require(type(exercise["cancel_states"]) is list and exercise["cancel_states"] == ["response_pending", "pair_held"]
             and type(exercise["invalid_k"]) is list and exercise["invalid_k"] == [0, 17]
             and all(type(value) is int for value in exercise["invalid_k"]),
             "This finite recipe checks two saved invalid K values and both shared-reset cancellation states.")
    return contract


def _new_state():
    return {"state": "IDLE", "k": 0, "lane": 0, "index": 0, "data": 0}


def _outputs(state, vector):
    enabled = not vector["reset"]
    mode, lane, index = state["state"], state["lane"], state["index"]
    return {"schedule_config_ready": int(enabled and mode == "IDLE" and 1 <= (vector["config_data"] & 31) <= 16),
            "read_request_valid": int(enabled and mode == "ISSUE"), "read_response_ready": int(enabled and mode == "WAIT"),
            "pair_data_valid": int(enabled and mode == "EMIT"), "pe_clear": int(enabled and mode == "CLEAR"),
            "schedule_done": int(enabled and mode == "DONE"),
            "read_request": (lane // 4 * 16 + index) | (index * 4 + lane % 4) << 8,
            "pair_data": state["data"], "pair_meta": lane | int(index == 0) << 4 | int(index == state["k"] - 1) << 5}


def _step(state, vector):
    before = _outputs(state, vector)
    transfers = {"config_transfer": int(vector["config_valid"] and before["schedule_config_ready"]),
                 "request_transfer": int(vector["request_ready"] and before["read_request_valid"]),
                 "response_transfer": int(vector["response_valid"] and before["read_response_ready"]),
                 "pair_transfer": int(vector["pair_ready"] and before["pair_data_valid"])}
    after = copy.deepcopy(state)
    if vector["reset"]:
        after = _new_state()
    elif state["state"] == "IDLE" and transfers["config_transfer"]:
        after.update(state="CLEAR", k=vector["config_data"] & 31, lane=0, index=0, data=0)
    elif state["state"] == "CLEAR":
        after["state"] = "ISSUE"
    elif transfers["request_transfer"]:
        after["state"] = "WAIT"
    elif transfers["response_transfer"]:
        after.update(state="EMIT", data=vector["response_data"])
    elif transfers["pair_transfer"]:
        if state["index"] + 1 < state["k"]:
            after.update(state="ISSUE", index=state["index"] + 1)
        elif state["lane"] < 15:
            after.update(state="ISSUE", index=0, lane=state["lane"] + 1)
        else:
            after["state"] = "DONE"
    elif state["state"] == "DONE":
        after["state"] = "IDLE"
    return after, before, _outputs(after, vector), transfers


def scheduler_reference_trace(vectors):
    state, trace = _new_state(), []
    for cycle, vector in enumerate(vectors):
        state_after, before, after, transfers = _step(state, vector)
        trace.append({"cycle": cycle, "stimulus": copy.deepcopy(vector), "state_before": state["state"], "state_after": state_after["state"],
                      "lane": state["lane"], "k_index": state["index"], **transfers, "before": before, "after": after})
        state = state_after
    return trace


def expand_vectors(contract):
    """Replay a saved deterministic environment against reference state only."""
    validate_contract(contract)
    job, exercise = contract["source_job"], contract["exercise"]
    config = pack_configuration(job)
    state, vectors = _new_state(), []
    def append(vector):
        nonlocal state
        _require(len(vectors) < 2000, "Saved exercise exceeded the finite cycle bound.")
        state, before, after, transfers = _step(state, vector)
        vectors.append(vector)
        return before, after, transfers
    def base(reset=0, config_valid=0, config_data=config):
        return {"reset": reset, "config_valid": config_valid, "config_data": config_data,
                "request_ready": 0, "response_valid": 0, "response_data": 0, "pair_ready": 0}
    append(base(reset=1)); append(base(reset=1))
    for invalid in exercise["invalid_k"]:
        value = (config & ~31) | invalid
        append(base(config_valid=1, config_data=value)); append(base(config_valid=1, config_data=value))
        # The saved reset cancels the invalid source offer; never withdraw a
        # stalled valid/data pair without a handshake or shared reset.
        append(base(reset=1, config_valid=1, config_data=value))
    for cancel_state in [*exercise["cancel_states"], None]:
        pending, request_count, pair_count, started, overlap = None, 0, 0, False, False
        local_cycle = 0
        while True:
            vector = base(config_valid=int(not started or overlap))
            vector["request_ready"] = exercise["request_ready_pattern"][local_cycle % len(exercise["request_ready_pattern"])]
            vector["pair_ready"] = exercise["pair_ready_pattern"][local_cycle % len(exercise["pair_ready_pattern"])]
            if cancel_state == "pair_held" and pair_count >= exercise["cancel_after_pair_transfers"]:
                # This saved recipe's pair_held phase deliberately stalls its
                # sink after the prefix until a full EMIT cycle is observed.
                vector["pair_ready"] = 0
            if pending is not None:
                vector["response_valid"] = int(pending["delay"] == 0)
                vector["response_data"] = pending["data"]
            before, after, transfers = append(vector)
            if transfers["config_transfer"]:
                started = True
            if pending is not None:
                if transfers["response_transfer"]:
                    pending = None
                elif pending["delay"]:
                    pending["delay"] -= 1
            if transfers["request_transfer"]:
                _require(pending is None, "Reference environment cannot accept a second outstanding request.")
                lane, index = request_count // job["k"], request_count % job["k"]
                expected = lane // 4 * 16 + index | (index * 4 + lane % 4) << 8
                _require(before["read_request"] == expected, "Independent reference request order is inconsistent.")
                data = (job["A"][lane // 4][index] & 255) | (job["B"][index][lane % 4] & 255) << 8
                pending = {"delay": exercise["response_delays"][request_count % len(exercise["response_delays"])], "data": data}
                request_count += 1
            pair_count += transfers["pair_transfer"]
            if cancel_state and pair_count:
                overlap = True  # Hold an overlapping source offer until reset.
            cancel = cancel_state and pair_count >= exercise["cancel_after_pair_transfers"] and (
                cancel_state == "response_pending" and state["state"] == "WAIT" and pending is not None or
                cancel_state == "pair_held" and before["pair_data_valid"] and not vector["pair_ready"])
            if cancel:
                reset = dict(vector, reset=1, config_valid=int(overlap))
                if pending is not None:
                    reset.update(response_valid=int(pending["delay"] == 0), response_data=pending["data"])
                append(reset); append(base(reset=1))
                # The buffer-side model shares reset and discards its pending
                # response before the next job. A real buffer is not integrated.
                pending = None
                break
            if before["schedule_done"]:
                _require(cancel_state is None and request_count == pair_count == 16 * job["k"] and pending is None,
                         "The complete original job must dispatch all operands once.")
                break
            local_cycle += 1
        if cancel_state is None:
            for _ in range(6):
                append(base())
    return vectors


def _asserted(values):
    result = {name: values[name] for name in CONTROL_SIGNALS}
    if values["read_request_valid"]:
        result["read_request"] = values["read_request"]
    if values["pair_data_valid"]:
        result.update(pair_data=values["pair_data"], pair_meta=values["pair_meta"])
    return result


def scheduler_asserted_trace(plan):
    return [{"cycle": item["cycle"], "stimulus": copy.deepcopy(item["stimulus"]),
             **{key: item[key] for key in ("config_transfer", "request_transfer", "response_transfer", "pair_transfer")},
             "asserted_before": _asserted(item["before"]) if item["cycle"] else None,
             "asserted_after": _asserted(item["after"])} for item in plan["reference_trace"]]


def _testbench(module, trace, vector_hash):
    inputs = {"rst": 1, "schedule_config": 134, "schedule_config_valid": 1, "read_request_ready": 1,
              "read_response": 16, "read_response_valid": 1, "pair_data_ready": 1}
    lines = ["`timescale 1ns/1ps", "module hullcirq_contract_tb;", "reg clk;"]
    lines += [f"reg {'' if width == 1 else f'[{width-1}:0] '}{name};" for name, width in inputs.items()]
    lines += [f"wire {'' if width == 1 else f'[{width-1}:0] '}{name};" for name, width in SIGNAL_WIDTHS.items()]
    names = ["clk", *inputs, *SIGNAL_WIDTHS]
    lines += [f"{module} dut (" + ", ".join(f".{name}({name})" for name in names) + ");", "initial begin", "clk=0;"]
    mapping = {"reset": "rst", "config_data": "schedule_config", "config_valid": "schedule_config_valid", "request_ready": "read_request_ready",
               "response_data": "read_response", "response_valid": "read_response_valid", "pair_ready": "pair_data_ready"}
    for item in trace:
        index = item["cycle"]
        lines += [f"// Original GUI job exercise cycle {index}", "clk=0;"]
        for field, signal in mapping.items():
            width = inputs[signal]
            lines.append(f"{signal}={width}'h{item['stimulus'][field]:x};")
        lines.append("#4;")
        for phase in ("before", "after"):
            if phase == "before" and index == 0:
                continue
            if phase == "after":
                lines.append("#1; clk=1; #1;")
            for signal, value in _asserted(item[phase]).items():
                literal = f"{SIGNAL_WIDTHS[signal]}'h{value:x}"
                lines.append(f'if ({signal} !== {literal}) begin $display("HULLCIRQ_FAIL cycle={index} phase={phase} signal={signal} expected=%h actual=%h", {literal}, {signal}); $finish; end')
        lines.append("#4; clk=0;")
    lines += [f'$display("HULLCIRQ_PASS vectors={len(trace)} vector_hash={vector_hash}");', "$finish;", "end", "endmodule", ""]
    return "\n".join(lines)


def _coverage(trace):
    result = {key + "s": sum(item[key] for item in trace) for key in ("config_transfer", "request_transfer", "response_transfer", "pair_transfer")}
    result.update(reset_cycles=sum(item["stimulus"]["reset"] for item in trace),
                  request_stall_cycles=sum(item["before"]["read_request_valid"] and not item["stimulus"]["request_ready"] for item in trace),
                  pair_stall_cycles=sum(item["before"]["pair_data_valid"] and not item["stimulus"]["pair_ready"] for item in trace),
                  clear_pulses=sum(item["before"]["pe_clear"] for item in trace), done_pulses=sum(item["before"]["schedule_done"] for item in trace),
                  invalid_config_cycles=sum(not item["stimulus"]["reset"] and item["state_before"] == "IDLE" and item["stimulus"]["config_valid"] and not 1 <= (item["stimulus"]["config_data"] & 31) <= 16 for item in trace),
                  busy_config_cycles=sum(not item["stimulus"]["reset"] and item["state_before"] != "IDLE" and item["stimulus"]["config_valid"] for item in trace),
                  reset_with_response_pending=sum(item["stimulus"]["reset"] and item["state_before"] == "WAIT" for item in trace),
                  reset_with_pair_held=sum(item["stimulus"]["reset"] and item["state_before"] == "EMIT" for item in trace),
                  completed_jobs=sum(item["before"]["schedule_done"] for item in trace))
    return result


def build_scheduler_plan(design, node_id, template_version=None):
    _require(template_version in (None, TEMPLATE), "Unsupported scheduler testbench template.", "unsupported_verification_template")
    nodes = [node for node in design.get("nodes", []) if node.get("id") == node_id]
    _require(len(nodes) == 1, "Scheduler verification needs one source node.")
    contract = validate_contract(nodes[0].get("verification"))
    source_job = contract["source_job"]
    jobs = design.get("verification_jobs", [])
    _require(type(jobs) is list and all(type(job) is dict for job in jobs), "Original verification_jobs must be a list of structured jobs.")
    matches = [job for job in jobs if job.get("id") == source_job["id"]]
    _require(len(matches) == 1, "The selected original GUI verification job must exist exactly once.")
    _job(matches[0])
    _require(object_hash(matches[0]) == object_hash(source_job), "The copied scheduler job must exactly match its selected original GUI verification job, including data types.")
    context = build_node_context(design, "verification-source", node_id)
    interface = context["interface"]
    expected = {"clk": ("input", 1, False), "rst": ("input", 1, False),
                "schedule_config": ("input", 134, False), "schedule_config_valid": ("input", 1, False), "schedule_config_ready": ("output", 1, False),
                "read_request": ("output", 16, False), "read_request_valid": ("output", 1, False), "read_request_ready": ("input", 1, False),
                "read_response": ("input", 16, False), "read_response_valid": ("input", 1, False), "read_response_ready": ("output", 1, False),
                "pair_data": ("output", 16, False), "pair_data_valid": ("output", 1, False), "pair_data_ready": ("input", 1, False),
                "pair_meta": ("output", 6, False), "pe_clear": ("output", 1, False), "schedule_done": ("output", 1, False)}
    ports = {port["name"]: port for port in interface["ports"]}
    _require(set(ports) == set(expected) and all((ports[name]["direction"], ports[name]["width"], ports[name]["signed"]) == value for name, value in expected.items()),
             "Scheduler verification requires the exact declared streams and three raw sideband signals.", "invalid_verification_interface")
    logical = {port["name"]: port for port in nodes[0]["ports"]}
    _require(logical["pair_meta"].get("protocol") == "raw" and logical["pair_meta"].get("sideband", {}).get("kind") == "metadata"
             and logical["pair_meta"]["sideband"].get("associated_port_id") == logical["pair_data"]["id"]
             and all(logical[name].get("protocol") == "raw" and logical[name].get("sideband", {}).get("kind") == "pulse" for name in ("pe_clear", "schedule_done")),
             "Scheduler pair metadata must belong to pair_data, and clear/done must be raw pulse signals.", "invalid_verification_interface")
    vectors = expand_vectors(contract)
    vector_hash = object_hash(vectors)
    trace = scheduler_reference_trace(vectors)
    tb = _testbench(interface["module_name"], trace, vector_hash)
    return {"kind": "npu_scheduler_stream", "version": 1, "source_node_id": node_id, "module_name": interface["module_name"], "node_input_hash": context["node_input_hash"],
            "contract": copy.deepcopy(contract), "contract_hash": object_hash(contract), "expanded_vectors": vectors, "vector_hash": vector_hash,
            "reference_trace": trace, "reference_trace_hash": object_hash(trace), "testbench": tb, "testbench_sha256": content_hash(tb), "vector_count": len(trace),
            "testbench_template_version": TEMPLATE, "initialization_origin": "first_original_gui_exercise_vector_asserting_synchronous_reset",
            "stimulus_origin": "original_design_node.verification.source_job_and_saved_exercise",
            "reference_origin": "ordinary_program_independent_scheduler_state_machine_from_structured_contract",
            "testbench_origin": "ordinary_program_from_original_job_recipe_expanded_vectors_and_independent_reference",
            "coverage": _coverage(trace), "signal_checks": list(SIGNAL_WIDTHS),
            "limits": ["Finite original matrix job and saved exercise recipe only; not exhaustive or formal verification.",
                       "Assertions check independent reference values; they are not an independently captured measured waveform.",
                       "One source job is restarted after two aborted prefixes; this is not three different matrix datasets.",
                       "The modeled external response queue shares reset; a real buffer and control are not yet integrated.",
                       "schedule_done means operand dispatch completed, not PE accumulation or final FIFO result completion.",
                       "Bias/ReLU configuration bits are packed from the original job but ignored by this scheduler.",
                       "No propagation delay, PDK cell timing, layout, PPA, or full-NPU behavior is checked.",
                       "Power-up state before the first original synchronous reset edge is not observed or assumed."]}


def validate_scheduler_plan(plan):
    try:
        validate_contract(plan["contract"])
        vectors = expand_vectors(plan["contract"])
        trace = scheduler_reference_trace(vectors)
        vector_hash = object_hash(vectors)
        tb = _testbench(plan["module_name"], trace, vector_hash)
        valid = (plan.get("kind") == "npu_scheduler_stream" and type(plan.get("version")) is int and plan["version"] == 1
                 and plan.get("testbench_template_version") == TEMPLATE and plan["contract_hash"] == object_hash(plan["contract"])
                 and plan["expanded_vectors"] == vectors and plan["vector_count"] == len(vectors) and plan["vector_hash"] == vector_hash
                 and plan["reference_trace"] == trace and plan["reference_trace_hash"] == object_hash(trace)
                 and plan["coverage"] == _coverage(trace) and plan["signal_checks"] == list(SIGNAL_WIDTHS)
                 and plan["testbench"] == tb and plan["testbench_sha256"] == content_hash(tb))
    except (KeyError, TypeError, ValueError, DomainError):
        valid = False
    _require(valid, "Frozen scheduler job, exercise, expanded stimulus, reference or testbench is inconsistent.", "invalid_verification_plan")

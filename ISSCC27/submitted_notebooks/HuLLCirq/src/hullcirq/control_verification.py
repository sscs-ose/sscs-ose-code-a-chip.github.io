"""Finite job-control verification from the unchanged original GUI matrix job.

An independent ordinary-program model expands a fixed environment recipe.
Its transfer pulses exercise the control boundary only. S08 must obtain these
pulses from real FIFO output valid && ready, not an invented completion signal.
"""
from __future__ import annotations

import copy

from .context import build_node_context
from .domain import DomainError
from .scheduler_verification import pack_configuration
from .verification import content_hash, object_hash

TEMPLATE = "control-original-job-v1"
CONTROL_SIGNALS = ("config_data_ready", "schedule_config_valid", "post_config_valid", "busy", "job_done")
SIGNAL_WIDTHS = {**{name: 1 for name in CONTROL_SIGNALS}, "schedule_config": 134, "post_config": 129}
VECTOR_KEYS = {"reset", "config_valid", "config_data", "schedule_ready", "post_ready", "output_transfer"}


def _require(condition, message, code="invalid_control_contract"):
    if not condition:
        raise DomainError(code, message)


def validate_contract(contract):
    _require(type(contract) is dict and set(contract) == {"kind", "version", "source_job", "exercise"}
             and contract["kind"] == "npu_control_stream" and type(contract["version"]) is int and contract["version"] == 1,
             "Control verification requires npu_control_stream version 1 and exact contract fields.")
    pack_configuration(contract["source_job"])
    _require(type(contract["exercise"]) is dict and contract["exercise"] == {"kind": "original_job_projection_v1"},
             "Use the fixed original-job control exercise recipe.")
    return contract


def _new_state():
    return {"state": "IDLE", "configuration": 0, "schedule_sent": 0, "post_sent": 0, "completed_outputs": 0}


def _outputs(state, vector):
    enabled, mode = not vector["reset"], state["state"]
    configuration = state["configuration"]
    return {"config_data_ready": int(enabled and mode == "IDLE" and 1 <= (vector["config_data"] & 31) <= 16),
            "schedule_config_valid": int(enabled and mode == "SEND_CONFIG" and not state["schedule_sent"]),
            "post_config_valid": int(enabled and mode == "SEND_CONFIG" and not state["post_sent"]),
            "busy": int(enabled and mode != "IDLE"), "job_done": int(enabled and mode == "DONE"),
            "schedule_config": configuration, "post_config": (configuration >> 6) << 1 | ((configuration >> 5) & 1)}


def _step(state, vector):
    before = _outputs(state, vector)
    transfers = {"config_transfer": int(vector["config_valid"] and before["config_data_ready"]),
                 "schedule_transfer": int(vector["schedule_ready"] and before["schedule_config_valid"]),
                 "post_transfer": int(vector["post_ready"] and before["post_config_valid"]),
                 "output_transfer": int(not vector["reset"] and state["state"] == "RUN" and vector["output_transfer"])}
    after = copy.deepcopy(state)
    if vector["reset"]:
        after = _new_state()
    elif transfers["config_transfer"]:
        after.update(state="SEND_CONFIG", configuration=vector["config_data"], schedule_sent=0, post_sent=0, completed_outputs=0)
    elif state["state"] == "SEND_CONFIG":
        after["schedule_sent"] |= transfers["schedule_transfer"]
        after["post_sent"] |= transfers["post_transfer"]
        if after["schedule_sent"] and after["post_sent"]:
            after["state"] = "RUN"
    elif transfers["output_transfer"]:
        after["completed_outputs"] += 1
        if after["completed_outputs"] == 16:
            after["state"] = "DONE"
    elif state["state"] == "DONE":
        after["state"] = "IDLE"
    return after, before, _outputs(after, vector), transfers


def control_reference_trace(vectors):
    _require(type(vectors) is list and vectors, "Control reference requires finite structured cycle vectors.")
    state, trace = _new_state(), []
    for cycle, vector in enumerate(vectors):
        _require(type(vector) is dict and set(vector) == VECTOR_KEYS
                 and all(type(vector[key]) is int and vector[key] in (0, 1) for key in VECTOR_KEYS - {"config_data"})
                 and type(vector["config_data"]) is int and 0 <= vector["config_data"] < (1 << 134),
                 "Control stimuli require exact integer controls and an unsigned 134-bit configuration.")
        next_state, before, after, transfers = _step(state, vector)
        trace.append({"cycle": cycle, "stimulus": copy.deepcopy(vector), "state_before": state["state"], "state_after": next_state["state"],
                      "completed_outputs_before": state["completed_outputs"], "completed_outputs_after": next_state["completed_outputs"],
                      **transfers, "before": before, "after": after})
        state = next_state
    return trace


def expand_vectors(contract):
    """Fixed stalls/cancellation/restart from reference state; no DUT feedback."""
    validate_contract(contract)
    configuration = pack_configuration(contract["source_job"])
    state, vectors = _new_state(), []

    def append(vector):
        nonlocal state
        _require(len(vectors) < 256, "The finite control exercise exceeded its cycle bound.")
        state, before, after, transfers = _step(state, vector)
        vectors.append(vector)
        return before, after, transfers

    def base(**changes):
        return {"reset": 0, "config_valid": 0, "config_data": configuration,
                "schedule_ready": 0, "post_ready": 0, "output_transfer": 0, **changes}

    append(base(reset=1, output_transfer=1)); append(base(reset=1))
    for invalid in (0, 17):
        invalid_configuration = (configuration & ~31) | invalid
        append(base(config_valid=1, config_data=invalid_configuration, output_transfer=1))
        append(base(config_valid=1, config_data=invalid_configuration))
        append(base(reset=1, config_valid=1, config_data=invalid_configuration, output_transfer=1))
    schedule_pattern, post_pattern, output_pattern = (0, 0, 1, 1, 0, 1), (0, 1, 0, 0, 1), (0, 1, 1, 0, 1)
    for cancelled in (True, False):
        started, local_cycle, output_count = False, 0, 0
        while True:
            # Keep the overlapping valid/data offer until a shared reset, even
            # while DONE. It is never silently withdrawn under backpressure.
            phase = local_cycle + (0 if cancelled else 2)
            vector = base(config_valid=1,
                          schedule_ready=schedule_pattern[phase % len(schedule_pattern)],
                          post_ready=post_pattern[phase % len(post_pattern)],
                          output_transfer=output_pattern[phase % len(output_pattern)])
            before, _, transfers = append(vector)
            started |= bool(transfers["config_transfer"])
            output_count += transfers["output_transfer"]
            if cancelled and output_count == 5:
                # A simultaneous transfer pulse at reset must not survive into
                # the restarted job's final-output count.
                append(base(reset=1, config_valid=1, schedule_ready=1, post_ready=1, output_transfer=1))
                append(base(reset=1))
                break
            if before["job_done"]:
                _require(started and not cancelled and output_count == 16, "Completion requires all 16 final output transfers.")
                append(base(reset=1, config_valid=1, output_transfer=1))
                break
            local_cycle += 1
        if not cancelled:
            for _ in range(5):
                append(base(output_transfer=1))
    return vectors


def _asserted(values):
    result = {name: values[name] for name in CONTROL_SIGNALS}
    if values["schedule_config_valid"]:
        result["schedule_config"] = values["schedule_config"]
    if values["post_config_valid"]:
        result["post_config"] = values["post_config"]
    return result


def control_asserted_trace(plan):
    return [{"cycle": item["cycle"], "stimulus": copy.deepcopy(item["stimulus"]),
             **{key: item[key] for key in ("config_transfer", "schedule_transfer", "post_transfer", "output_transfer")},
             "asserted_before": _asserted(item["before"]) if item["cycle"] else None,
             "asserted_after": _asserted(item["after"])} for item in plan["reference_trace"]]


def _testbench(module, trace, vector_hash):
    inputs = {"rst": 1, "config_data": 134, "config_data_valid": 1, "schedule_config_ready": 1,
              "post_config_ready": 1, "output_transfer": 1}
    mapping = {"reset": "rst", "config_data": "config_data", "config_valid": "config_data_valid",
               "schedule_ready": "schedule_config_ready", "post_ready": "post_config_ready", "output_transfer": "output_transfer"}
    lines = ["`timescale 1ns/1ps", "module hullcirq_contract_tb;", "reg clk;"]
    lines += [f"reg {'' if width == 1 else f'[{width-1}:0] '}{name};" for name, width in inputs.items()]
    lines += [f"wire {'' if width == 1 else f'[{width-1}:0] '}{name};" for name, width in SIGNAL_WIDTHS.items()]
    lines += [f"{module} dut (" + ", ".join(f".{name}({name})" for name in ("clk", *inputs, *SIGNAL_WIDTHS)) + ");", "initial begin", "clk=0;"]
    for item in trace:
        index = item["cycle"]
        lines += [f"// Original GUI job control exercise cycle {index}", "clk=0;"]
        lines += [f"{signal}={inputs[signal]}'h{item['stimulus'][field]:x};" for field, signal in mapping.items()]
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
    result = {key + "s": sum(item[key] for item in trace) for key in ("config_transfer", "schedule_transfer", "post_transfer", "output_transfer")}
    result.update(reset_cycles=sum(item["stimulus"]["reset"] for item in trace),
                  schedule_stall_cycles=sum(item["before"]["schedule_config_valid"] and not item["stimulus"]["schedule_ready"] for item in trace),
                  post_stall_cycles=sum(item["before"]["post_config_valid"] and not item["stimulus"]["post_ready"] for item in trace),
                  invalid_config_cycles=sum(not item["stimulus"]["reset"] and item["state_before"] == "IDLE" and item["stimulus"]["config_valid"] and not 1 <= (item["stimulus"]["config_data"] & 31) <= 16 for item in trace),
                  busy_config_cycles=sum(item["before"]["busy"] and item["stimulus"]["config_valid"] for item in trace),
                  ignored_output_pulses=sum(not item["stimulus"]["reset"] and item["state_before"] != "RUN" and item["stimulus"]["output_transfer"] for item in trace),
                  reset_with_partial_outputs=sum(item["stimulus"]["reset"] and item["state_before"] == "RUN" and item["completed_outputs_before"] > 0 for item in trace),
                  done_pulses=sum(item["before"]["job_done"] for item in trace),
                  completed_jobs=sum(item["before"]["job_done"] for item in trace))
    return result


def build_control_plan(design, node_id, template_version=None):
    _require(template_version in (None, TEMPLATE), "Unsupported control testbench template.", "unsupported_verification_template")
    nodes = [node for node in design.get("nodes", []) if node.get("id") == node_id]
    _require(len(nodes) == 1, "Control verification requires one source node.")
    node = nodes[0]
    contract = validate_contract(node.get("verification"))
    jobs = design.get("verification_jobs")
    _require(type(jobs) is list and all(type(job) is dict for job in jobs), "Original verification_jobs must be structured jobs.")
    source_job = contract["source_job"]
    matches = [job for job in jobs if job.get("id") == source_job["id"]]
    _require(len(matches) == 1, "The selected original GUI matrix job must exist exactly once.")
    pack_configuration(matches[0])
    _require(object_hash(matches[0]) == object_hash(source_job), "The control source job must exactly match the current canonical GUI job, including numeric types.")
    context = build_node_context(design, "verification-source", node_id)
    interface = context["interface"]
    _require(interface["clock"] == "clk" and interface["reset"] == "rst"
             and interface["reset_active"] == "high" and interface["reset_kind"] == "synchronous",
             "Control verification requires clk and synchronous active-high rst.", "invalid_verification_interface")
    expected = {"clk": ("input", 1, False), "rst": ("input", 1, False),
                "config_data": ("input", 134, False), "config_data_valid": ("input", 1, False), "config_data_ready": ("output", 1, False),
                "schedule_config": ("output", 134, False), "schedule_config_valid": ("output", 1, False), "schedule_config_ready": ("input", 1, False),
                "post_config": ("output", 129, False), "post_config_valid": ("output", 1, False), "post_config_ready": ("input", 1, False),
                "output_transfer": ("input", 1, False), "busy": ("output", 1, False), "job_done": ("output", 1, False)}
    ports = {port["name"]: port for port in interface["ports"]}
    _require(len(interface["ports"]) == len(expected) and set(ports) == set(expected)
             and all((ports[name]["direction"], ports[name]["width"], ports[name]["signed"]) == value for name, value in expected.items()),
             "Control verification needs exactly the three configuration streams and three raw control signals.", "invalid_verification_interface")
    logical = {port["name"]: port for port in node["ports"]}
    _require(len(node["ports"]) == 6 and all(port.get("clock") == "clk" and port.get("reset") == "rst" for port in node["ports"])
             and all(logical[name].get("protocol") == "valid_ready" for name in ("config_data", "schedule_config", "post_config"))
             and all(logical[name].get("protocol") == "raw" and logical[name].get("sideband", {}).get("kind") == kind
                     and logical[name]["sideband"].get("associated_port_id", "missing") is None
                     for name, kind in (("output_transfer", "pulse"), ("busy", "level"), ("job_done", "pulse"))),
             "Declare independent output_transfer/job_done pulses and a busy level signal.", "invalid_verification_interface")
    vectors = expand_vectors(contract)
    vector_hash = object_hash(vectors)
    trace = control_reference_trace(vectors)
    tb = _testbench(interface["module_name"], trace, vector_hash)
    return {"kind": "npu_control_stream", "version": 1, "source_node_id": node_id, "module_name": interface["module_name"], "node_input_hash": context["node_input_hash"],
            "contract": copy.deepcopy(contract), "contract_hash": object_hash(contract), "expanded_vectors": vectors, "vector_hash": vector_hash,
            "reference_trace": trace, "reference_trace_hash": object_hash(trace), "testbench": tb, "testbench_sha256": content_hash(tb), "vector_count": len(trace),
            "testbench_template_version": TEMPLATE, "initialization_origin": "first_original_gui_exercise_vector_asserting_synchronous_reset",
            "stimulus_origin": "original_design_node.verification.source_job_and_saved_exercise",
            "reference_origin": "ordinary_program_independent_control_state_machine_from_structured_contract",
            "testbench_origin": "ordinary_program_from_original_job_recipe_expanded_vectors_and_independent_reference",
            "coverage": _coverage(trace), "signal_checks": list(SIGNAL_WIDTHS),
            "limits": ["Finite unchanged original matrix job and fixed exercise only; not exhaustive or formal verification.",
                       "Assertions check independent reference values; they are not a captured measured waveform.",
                       "One original configuration is restarted after five cancelled final-output transfers; no replacement matrix dataset is used.",
                       "Output-transfer pulses are a finite control-boundary environment projection, not an integrated FIFO measurement.",
                       "S08 must wire output_transfer to actual final FIFO output valid AND ready; scheduler_done is not job completion.",
                       "Control completion follows 16 final output transfers; their numerical values and 16-PE/global datapath are not verified here.",
                       "Data is asserted only while its corresponding configuration valid is high; inactive data is unspecified.",
                       "No PDK mapping, propagation delay, SDF, layout, PPA or full-NPU correctness is checked.",
                       "Power-up state before the first original synchronous reset edge is not observed or assumed."]}


def validate_control_plan(plan):
    try:
        validate_contract(plan["contract"])
        vectors = expand_vectors(plan["contract"])
        trace = control_reference_trace(vectors)
        vector_hash = object_hash(vectors)
        tb = _testbench(plan["module_name"], trace, vector_hash)
        valid = (plan.get("kind") == "npu_control_stream" and type(plan.get("version")) is int and plan["version"] == 1
                 and plan.get("testbench_template_version") == TEMPLATE and plan["contract_hash"] == object_hash(plan["contract"])
                 and object_hash(plan["expanded_vectors"]) == object_hash(vectors) and type(plan["vector_count"]) is int and plan["vector_count"] == len(vectors)
                 and plan["vector_hash"] == vector_hash and object_hash(plan["reference_trace"]) == object_hash(trace)
                 and plan["reference_trace_hash"] == object_hash(trace) and object_hash(plan["coverage"]) == object_hash(_coverage(trace))
                 and plan["signal_checks"] == list(SIGNAL_WIDTHS) and plan["testbench"] == tb and plan["testbench_sha256"] == content_hash(tb))
    except (KeyError, TypeError, ValueError, DomainError):
        valid = False
    _require(valid, "Frozen control job, recipe, vectors, reference or testbench is inconsistent.", "invalid_verification_plan")

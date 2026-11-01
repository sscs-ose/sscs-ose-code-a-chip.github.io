"""Finite control checks projected from the original explicit 2x2 GUI job.

The saved design is never edited. Repeating its one configuration under
different handshakes is not an additional arithmetic workload or matrix job.
"""
from __future__ import annotations

import copy
import re

from .context import build_node_context
from .domain import DomainError
from .verification import content_hash, object_hash

TEMPLATE = "npu2-original-job-control-v1"
KIND = "npu2_control_original_job"
NODE_ID = "npu2-control"
BEHAVIOR = "One matrix job in flight. config_data[3:0]=unsigned K in 1..8, [4]=ReLU, [36:5]=signed bias0, [68:37]=signed bias1. IDLE accepts a valid legal configuration and latches all 69 bits; invalid K is not accepted. SEND_CONFIG presents schedule_config=saved[3:0] and post_config=saved[68:4], with independent valid/ready handshakes and independent sent flags. Hold each channel stable until its own transfer; do not treat one ready as acceptance of both. Enter RUN only after both transfers. Count exactly four actual final external output_transfer pulses in RUN; ignore pulses before RUN. After fourth transfer assert job_done for one cycle, then return IDLE. busy is high from configuration acceptance through DONE and blocks new configuration. Synchronous high reset cancels the job, flags and output count; gate ready/valid/busy/done during reset. No arbitrary timeout completion."
CONSTRAINTS = {"latency_cycles": 1, "protocol": "valid_ready", "jobs_in_flight": 1, "final_outputs_per_job": 4}
EDGE_BEHAVIORS = {
    "schedule_config": "One stable K1..8 configuration transfer per job; independent of post configuration acceptance.",
    "post_config": "Exactly the saved ReLU and two signed column biases; independent handshake before RUN.",
    "output_transfer": "Count actual external transfers only; fourth pulse completes current job, independent of scheduler dispatch.",
}


def _require(value, message, code="unsupported_npu2_control_contract"):
    if not value:
        raise DomainError(code, message)


def physical_ports():
    ports = {"clk": ("input", 1, False), "rst": ("input", 1, False)}
    for name, direction, width in (("config_data", "input", 69), ("schedule_config", "output", 4), ("post_config", "output", 65)):
        ports[name] = direction, width, False
        ports[name + "_valid"] = direction, 1, False
        ports[name + "_ready"] = ("output" if direction == "input" else "input"), 1, False
    for name, direction in (("output_transfer", "input"), ("busy", "output"), ("job_done", "output")):
        ports[name] = direction, 1, False
    return ports


def _recognize(contract):
    _require(type(contract) is dict and set(contract) == {"kind", "version", "source_node", "source_job", "source_edges", "settings", "global_integration", "design_intent"},
             "A complete saved control graph/job contract is required.")
    _require(contract["kind"] == KIND and type(contract["version"]) is int and contract["version"] == 1, "Unsupported saved control contract version.")
    node = contract["source_node"]
    _require(type(node) is dict and node.get("id") == NODE_ID and node.get("parent_id") is None and node.get("behavior") == BEHAVIOR
             and object_hash(node.get("constraints")) == object_hash(CONSTRAINTS) and node.get("verification") is None,
             "Only the unchanged explicit 2x2 job-control behavior and constraints are supported.")
    _require(type(node.get("module_name")) is str and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", node["module_name"]), "A valid saved module name is required.")
    expected = {"config_data": ("input", 69, "valid_ready"), "schedule_config": ("output", 4, "valid_ready"),
                "post_config": ("output", 65, "valid_ready"), "output_transfer": ("input", 1, "raw"), "busy": ("output", 1, "raw"), "job_done": ("output", 1, "raw")}
    ports = node.get("ports")
    _require(type(ports) is list and len(ports) == len(expected) and {p.get("name") for p in ports if type(p) is dict} == set(expected), "The six saved control streams/status ports are required.")
    for port in ports:
        direction, width, protocol = expected[port["name"]]
        _require(port.get("id") == NODE_ID + "-" + port["name"] and port.get("direction") == direction and type(port.get("width")) is int
                 and port["width"] == width and port.get("signed") is False and port.get("protocol") == protocol
                 and port.get("clock") == "clk" and port.get("reset") == "rst", "Unsupported saved control port.")
        if protocol == "raw":
            sideband = {"kind": "level" if port["name"] == "busy" else "pulse", "associated_port_id": None}
            if port["name"] == "output_transfer":
                sideband["meaning"] = "Exactly one pulse for each external FIFO output valid && ready."
            _require(object_hash(port.get("sideband")) == object_hash(sideband), "The original control status/transfer meaning is required.")
    settings = contract["settings"]
    _require(type(settings) is dict and all(settings.get(k) == v for k, v in {"clock_name": "clk", "reset_name": "rst", "reset_active": "high", "reset_kind": "synchronous", "rtl_language": "verilog_2005"}.items()), "The saved synchronous high reset and Verilog-2005 settings are required.")
    intent = contract["design_intent"]
    _require(type(intent) is dict and all(type(intent.get(k)) is int and intent[k] == v for k, v in {"matrix_rows": 2, "matrix_columns": 2, "operand_bits": 8, "accumulator_bits": 32, "k_min": 1, "k_max": 8, "pe_instances": 4}.items()), "The saved explicit four-PE 2x2 dimensions are required.")
    integration = contract["global_integration"]
    _require(type(integration) is dict and type(integration.get("public_streams")) is list and type(integration.get("public_status")) is list
             and sum(p == {"node_id": NODE_ID, "port": "config_data", "direction": "input", "width": 69} for p in integration["public_streams"]) == 1
             and all(sum(p == {"node_id": NODE_ID, "port": name} for p in integration["public_status"]) == 1 for name in ("busy", "job_done"))
             and integration.get("external_load_rule") == "Load the addresses used by the saved job before configuration; gate load handshake off while busy."
             and integration.get("reset_contract") == "Synchronous high reset cancels all in-flight transfers and clears arithmetic/control/output state; operand register bank bytes are retained. No power-loss retention claim.", "The saved public configuration/status and reset contracts are required.")
    edges = contract["source_edges"]
    _require(type(edges) is list and len(edges) == 3, "Exactly the original three control edges are supported.")
    found = set()
    for edge in edges:
        _require(type(edge) is dict and type(edge.get("source")) is dict and type(edge.get("target")) is dict, "Structured control edge endpoints are required.")
        source, target = edge["source"], edge["target"]
        if source.get("node_id") == NODE_ID:
            name = source.get("port_id", "").removeprefix(NODE_ID + "-")
            other = "npu2-scheduler" if name == "schedule_config" else "npu2-post"
            _require(name in ("schedule_config", "post_config") and source == {"node_id": NODE_ID, "port_id": NODE_ID + "-" + name}
                     and target == {"node_id": other, "port_id": other + "-" + name} and edge.get("protocol") == "valid_ready", "Unsupported configuration edge.")
        else:
            name = "output_transfer"
            _require(source == {"node_id": "npu2-fifo", "port_id": "npu2-fifo-output_transfer"}
                     and target == {"node_id": NODE_ID, "port_id": NODE_ID + "-output_transfer"} and edge.get("protocol") == "raw", "Unsupported final transfer edge.")
        _require(name not in found and edge.get("behavior") == EDGE_BEHAVIORS[name], "Modified or duplicate control edge behavior is unsupported.")
        found.add(name)
    _require(found == set(EDGE_BEHAVIORS), "All original control edges are required.")
    job = contract["source_job"]
    _require(type(job) is dict and set(job) == {"id", "k", "A", "B", "bias", "relu", "scope"} and type(job["id"]) is str and bool(job["id"])
             and type(job["scope"]) is str and type(job["k"]) is int and 1 <= job["k"] <= 8 and type(job["relu"]) is bool, "One supported original matrix job is required.")
    k = job["k"]
    _require(type(job["A"]) is list and len(job["A"]) == 2 and all(type(row) is list and len(row) == k for row in job["A"])
             and type(job["B"]) is list and len(job["B"]) == k and all(type(row) is list and len(row) == 2 for row in job["B"])
             and all(type(value) is int and -128 <= value <= 127 for matrix in (job["A"], job["B"]) for row in matrix for value in row)
             and type(job["bias"]) is list and len(job["bias"]) == 2 and all(type(value) is int and -(1 << 31) <= value < (1 << 31) for value in job["bias"]), "The saved matrix dimensions, signed operands and two biases must match the job.")
    return contract


def config_packet(job):
    return job["k"] | (int(job["relu"]) << 4) | ((job["bias"][0] & 0xffffffff) << 5) | ((job["bias"][1] & 0xffffffff) << 37)


def expand_vectors(contract):
    _recognize(contract)
    packet = config_packet(contract["source_job"])
    vectors = []
    def add(label, repeat=1, **changes):
        for _ in range(repeat):
            value = {"label": label, "reset": 0, "reset_pulse_before_edge": 0, "config_data": packet, "config_data_valid": 0,
                     "schedule_config_ready": 0, "post_config_ready": 0, "output_transfer": 0}
            value.update(changes); vectors.append(value)
    def offer(label):
        add(label, config_data_valid=1, output_transfer=1)
    def finish(label, consecutive=False):
        add(label + "_run_gap", repeat=3)
        for index in range(4):
            add(label + f"_output_{index}", output_transfer=1)
            if label == "schedule_first" and index == 1:
                add("run_nonclocked_reset_pulse", reset_pulse_before_edge=1)
            if index < 3 and not consecutive:
                add(label + "_output_gap", repeat=2)
        add(label + "_done_return", output_transfer=1)
        add(label + "_idle_ignore", output_transfer=1)
    add("initial_reset", reset=1, config_data_valid=1, schedule_config_ready=1, post_config_ready=1, output_transfer=1)
    add("idle_ignore", output_transfer=1)
    offer("schedule_first_accept")
    add("both_stall", repeat=2, output_transfer=1)
    add("send_nonclocked_reset_pulse", reset_pulse_before_edge=1)
    add("schedule_only", schedule_config_ready=1, output_transfer=1)
    add("post_stall_after_schedule", repeat=3, schedule_config_ready=1, output_transfer=1)
    add("post_transfer", schedule_config_ready=1, post_config_ready=1, output_transfer=1)
    finish("schedule_first")
    offer("cancel_send_accept")
    add("post_only_before_cancel", post_config_ready=1, output_transfer=1)
    add("cancel_send_stall", repeat=2, config_data_valid=1, post_config_ready=1, output_transfer=1)
    add("cancel_send_reset", reset=1, config_data_valid=1, schedule_config_ready=1, post_config_ready=1, output_transfer=1)
    add("after_send_reset", output_transfer=1)
    offer("post_first_accept")
    add("post_only", post_config_ready=1, output_transfer=1)
    add("schedule_stall_after_post", repeat=3, post_config_ready=1, output_transfer=1)
    add("schedule_transfer", schedule_config_ready=1, post_config_ready=1, output_transfer=1)
    finish("post_first")
    offer("cancel_run_accept")
    add("cancel_run_both_transfer", schedule_config_ready=1, post_config_ready=1, output_transfer=1)
    add("cancel_run_two_outputs", repeat=2, config_data_valid=1, output_transfer=1)
    add("cancel_run_reset", reset=1, config_data_valid=1, schedule_config_ready=1, post_config_ready=1, output_transfer=1)
    add("after_run_reset", repeat=2, output_transfer=1)
    offer("simultaneous_accept")
    add("simultaneous_stall", repeat=2, output_transfer=1)
    add("simultaneous_transfer", schedule_config_ready=1, post_config_ready=1, output_transfer=1)
    finish("simultaneous", consecutive=True)
    add("final_idle", repeat=3)
    return vectors


def reference_trace(vectors):
    phase, saved, schedule_sent, post_sent, count = "IDLE", 0, False, False, 0
    trace = []
    def outputs(vector):
        enabled = not vector["reset"]
        return {"config_data_ready": int(enabled and phase == "IDLE"), "schedule_config": saved & 15,
                "schedule_config_valid": int(enabled and phase == "SEND" and not schedule_sent),
                "post_config": saved >> 4, "post_config_valid": int(enabled and phase == "SEND" and not post_sent),
                "busy": int(enabled and phase != "IDLE"), "job_done": int(enabled and phase == "DONE")}
    for step, vector in enumerate(vectors):
        before = outputs(vector); phase_before = phase
        accepted = int(not vector["reset"] and vector["config_data_valid"] and before["config_data_ready"])
        schedule = int(before["schedule_config_valid"] and vector["schedule_config_ready"])
        post = int(before["post_config_valid"] and vector["post_config_ready"])
        output = int(not vector["reset"] and phase == "RUN" and vector["output_transfer"])
        if vector["reset"]:
            phase, saved, schedule_sent, post_sent, count = "IDLE", 0, False, False, 0
        elif phase == "IDLE" and accepted:
            saved, schedule_sent, post_sent, count, phase = vector["config_data"], False, False, 0, "SEND"
        elif phase == "SEND":
            schedule_sent = schedule_sent or bool(schedule)
            post_sent = post_sent or bool(post)
            if schedule_sent and post_sent:
                phase = "RUN"
        elif phase == "RUN" and output:
            count += 1
            if count == 4:
                phase = "DONE"
        elif phase == "DONE":
            phase = "IDLE"
        trace.append({"step": step, "stimulus": copy.deepcopy(vector), "phase_before": phase_before, "phase_after": phase,
                      "before": before, "after": outputs(vector), "config_transfer": accepted, "schedule_transfer": schedule,
                      "post_transfer": post, "counted_output_transfer": output, "output_count_after": count})
    return trace


def testbench(module_name, trace, vector_hash):
    ports = physical_ports()
    lines = ["`timescale 1ns/1ps", "module hullcirq_contract_tb;", "reg clk;"]
    for name, (direction, width, _) in ports.items():
        if name != "clk":
            lines.append(f"{'reg' if direction == 'input' else 'wire'} {'' if width == 1 else f'[{width-1}:0] '}{name};")
    lines += [f"{module_name} dut (" + ", ".join(f".{name}({name})" for name in ports) + ");",
              "integer attempt; reg accepted;", "initial begin", "clk=0;"]
    def checks(values, where, step, idle=False):
        result = []
        for name in ("config_data_ready", "schedule_config_valid", "post_config_valid", "busy", "job_done"):
            # Source does not promise eager combinational readiness in IDLE.
            if name == "config_data_ready" and idle and values[name] == 1:
                result.append(f'if ({name} !== 0 && {name} !== 1) begin $display("HULLCIRQ_FAIL step={step} {where} unknown config ready"); $finish; end')
            else:
                result.append(f'if ({name} !== 1\'b{values[name]}) begin $display("HULLCIRQ_FAIL step={step} {where} signal={name} expected={values[name]} actual=%b",{name}); $finish; end')
        for name, width in (("schedule_config", 4), ("post_config", 65)):
            if values[name + "_valid"]:
                result.append(f'if ({name} !== {width}\'h{values[name]:x}) begin $display("HULLCIRQ_FAIL step={step} {where} signal={name} payload mismatch"); $finish; end')
        return result
    for item in trace:
        step, vector = item["step"], item["stimulus"]
        lines += [f"// Original GUI configuration recipe step {step}: {vector['label']}", "clk=0;"]
        for name, (direction, width, _) in ports.items():
            if direction == "input" and name != "clk":
                lines.append(f"{name}={width}'h{vector['reset' if name == 'rst' else name]:x};")
        if vector["reset_pulse_before_edge"]:
            lines += ["// Pulse reset without a clock edge: gate outputs, but retain synchronous state.", "#1;"]
            lines += checks(item["before"], "before nonclocked reset", step)
            gated = dict(item["before"])
            gated.update({name: 0 for name in ("config_data_ready", "schedule_config_valid", "post_config_valid", "busy", "job_done")})
            lines += ["rst=1; #1;"] + checks(gated, "during nonclocked reset", step)
            lines += ["rst=0; #1;"] + checks(item["before"], "after nonclocked reset", step)
        if item["config_transfer"]:
            lines += ["// Hold this original configuration until actual acceptance; 64 is a harness bound, not a hardware timeout.",
                      "accepted=0; begin: wait_config_" + str(step), "for(attempt=0;attempt<64;attempt=attempt+1) begin", "#4;"]
            lines += checks(item["before"], "before", step, idle=True)
            lines += ["accepted=(config_data_ready === 1'b1); #1; clk=1; #1;", "if (accepted) begin"]
            lines += checks(item["after"], "after", step)
            lines += ["#4; clk=0; disable wait_config_" + str(step) + "; end"]
            lines += checks(item["before"], "waiting", step, idle=True)
            lines += ["#4; clk=0; end", f'$display("HULLCIRQ_FAIL step={step} finite harness configuration acceptance bound reached"); $finish;', "end"]
        else:
            lines += ["#4;"]
            # During rst, combinationally gated status is required even before the clock.
            lines += checks(item["before"], "before", step, idle=item["phase_before"] == "IDLE")
            lines += ["#1; clk=1; #1;"]
            lines += checks(item["after"], "after", step, idle=item["phase_after"] == "IDLE")
            lines += ["#4; clk=0;"]
    lines += [f'$display("HULLCIRQ_PASS vectors={len(trace)} vector_hash={vector_hash}");', "$finish;", "end", "endmodule", ""]
    return "\n".join(lines)


def _coverage(trace):
    return {"original_configuration_acceptances": sum(v["config_transfer"] for v in trace),
            "schedule_config_transfers": sum(v["schedule_transfer"] for v in trace), "post_config_transfers": sum(v["post_transfer"] for v in trace),
            "counted_external_output_pulses": sum(v["counted_output_transfer"] for v in trace),
            "ignored_pulses_before_run": sum(bool(v["stimulus"]["output_transfer"] and not v["stimulus"]["reset"] and v["phase_before"] in ("IDLE", "SEND")) for v in trace),
            "completed_job_done_pulses": sum(v["after"]["job_done"] for v in trace),
            "reset_cycles": sum(v["stimulus"]["reset"] for v in trace),
            "reset_during_send": sum(bool(v["stimulus"]["reset"] and v["phase_before"] == "SEND") for v in trace),
            "reset_during_run": sum(bool(v["stimulus"]["reset"] and v["phase_before"] == "RUN") for v in trace),
            "nonclocked_reset_pulses": sum(v["stimulus"]["reset_pulse_before_edge"] for v in trace),
            "schedule_stall_cycles": sum(bool(v["before"]["schedule_config_valid"] and not v["stimulus"]["schedule_config_ready"]) for v in trace),
            "post_stall_cycles": sum(bool(v["before"]["post_config_valid"] and not v["stimulus"]["post_config_ready"]) for v in trace)}


def _plan(contract, node_input_hash):
    vectors = expand_vectors(contract); trace = reference_trace(vectors); vector_hash = object_hash(vectors)
    module_name = contract["source_node"]["module_name"]; tb = testbench(module_name, trace, vector_hash)
    return {"kind": KIND, "version": 1, "source_node_id": NODE_ID, "module_name": module_name, "node_input_hash": node_input_hash,
            "contract": copy.deepcopy(contract), "contract_hash": object_hash(contract), "source_job_hash": object_hash(contract["source_job"]),
            "expanded_vectors": vectors, "vector_hash": vector_hash, "reference_trace": trace, "reference_trace_hash": object_hash(trace),
            "testbench": tb, "testbench_sha256": content_hash(tb), "vector_count": len(vectors), "testbench_template_version": TEMPLATE,
            "initialization_origin": "first_saved_job_projection_vector_asserting_synchronous_reset",
            "stimulus_origin": "original_design.verification_jobs[0]_and_exact_saved_control_node_edges_contract",
            "reference_origin": "ordinary_program_independent_configuration_fork_and_four_output_control_state_machine",
            "testbench_origin": "ordinary_program_from_saved_configuration_recipe_and_independent_reference",
            "stimulus_timing": "original_job_recipe_steps_with_actual_config_handshake_waits",
            "coverage": _coverage(trace), "signal_checks": [name for name, (direction, _, _) in physical_ports().items() if direction == "output"],
            "limits": ["Finite local projection of the one original 2x2 job; not exhaustive or formal verification.",
                       "Only the original legal K, ReLU and signed biases are offered; invalid-K rejection, other K/bias/ReLU values and changed configuration payloads are not verified.",
                       "Matrix operands are preserved in the frozen source job but not sent to control; no arithmetic or full-NPU result is simulated here.",
                       "The same original configuration is repeated under finite schedule-first, post-first and simultaneous fork handshakes, output gaps, clocked reset cancellation and two non-clocked reset pulses checking synchronous-state retention.",
                       "Reference trace is an earliest-acceptance recipe, not an observed DUT cycle trace; config offers wait for actual acceptance up to 64 cycles, a harness progress bound rather than a hardware timeout.",
                       "Inactive output payload is unspecified and not asserted. Only specified reset-gated handshake/status outputs are checked during reset.",
                       "Finite RUN gaps check premature completion only over those gaps, not arbitrary-duration timeout absence.",
                       "No cross-node integration, synthesis, netlist, timing, layout, DRC, LVS or post-layout check is claimed."]}


def build_control_plan(design, node_id, template_version=None):
    _require(template_version in (None, TEMPLATE), "Unsupported 2x2 control testbench template.", "unsupported_verification_template")
    nodes = [node for node in design.get("nodes", []) if node.get("id") == node_id]
    _require(node_id == NODE_ID and len(nodes) == 1, "Select the saved explicit 2x2 job control.")
    jobs = design.get("verification_jobs")
    _require(type(jobs) is list and len(jobs) == 1, "Exactly one original saved matrix job is required.")
    contract = {"kind": KIND, "version": 1, "source_node": copy.deepcopy(nodes[0]), "source_job": copy.deepcopy(jobs[0]),
                "source_edges": copy.deepcopy([edge for edge in design.get("edges", []) if any(edge.get(side, {}).get("node_id") == node_id for side in ("source", "target"))]),
                **{key: copy.deepcopy(design.get(key)) for key in ("settings", "global_integration", "design_intent")}}
    _recognize(contract)
    context = build_node_context(design, "verification-source", node_id)
    ports = {p["name"]: (p["direction"], p["width"], p["signed"]) for p in context["interface"]["ports"]}
    _require(ports == physical_ports(), "The expanded public interface must match saved control streams.", "invalid_verification_interface")
    return _plan(contract, context["node_input_hash"])


def validate_control_plan(plan):
    try:
        valid = object_hash(plan) == object_hash(_plan(plan["contract"], plan["node_input_hash"]))
    except (KeyError, TypeError, ValueError, AttributeError, DomainError):
        valid = False
    _require(valid, "Frozen 2x2 original-job control evidence is inconsistent.", "invalid_verification_plan")

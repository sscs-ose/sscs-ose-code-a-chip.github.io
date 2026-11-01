"""Finite scheduler/dispatcher checks from the saved explicit 2x2 graph/job.

The recipes use only the original GUI matrix job. Progress waits are finite
harness bounds, not extra hardware latency requirements. Reference recipes are
expected transactions, never measured DUT waveforms. New template versions are
required if these frozen semantics change.
"""
from __future__ import annotations

import copy
import re

from .context import build_node_context
from .domain import DomainError
from .verification import content_hash, object_hash

SCHEDULER_KIND = "npu2_scheduler_original_job"
DISPATCHER_KIND = "npu2_dispatcher_original_job"
SCHEDULER_TEMPLATE = "npu2-original-job-scheduler-v1"
DISPATCHER_TEMPLATE = "npu2-original-job-dispatcher-v1"
SCHEDULER_BEHAVIOR = "Accept schedule_config K1..8 only when idle. For k=0..K-1: transfer one read_index=k request, capture exactly one operands response, then transfer exactly one batch_data. batch_data[31:0]=captured operands, bit32=(k==0), bit33=(k==K-1). Hold request and batch data stable under stalls. Do not start a new k until the current batch transfers; at the last batch transfer return idle. Each job generates exactly K operand batches. Shared synchronous high reset cancels all pending transfers and iteration state. Dispatch completion is not final NPU completion; Job control counts actual external FIFO transfers."
DISPATCHER_BEHAVIOR = "One captured operand batch with four independent output transfers. Let a0=batch[7:0], a1=[15:8], b0=[23:16], b1=[31:24], first=batch[32], last=batch[33]. pair00={last,first,b0,a0}, pair01={last,first,b1,a0}, pair10={last,first,b0,a1}, pair11={last,first,b1,a1}. Each pair is 18 bits: a[7:0], b[15:8], first[16], last[17]. Keep a separate delivered flag for every lane. Assert each output valid until that lane alone accepts it, hold its payload stable, and never duplicate a delivered pair. Accept no new batch until all four lanes have transferred the current batch; no same-cycle batch replacement. No combinational broadcast of one ready signal. Reset clears pending batch and all lane flags."
BATCH_EDGE = "One operand bundle and first/last markers per k; stable under stall; all four lane transfers must complete before next batch."
RESET_CONTRACT = "Synchronous high reset cancels all in-flight transfers and clears arithmetic/control/output state; operand register bank bytes are retained. No power-loss retention claim."
LANES = ("00", "01", "10", "11")


def _require(condition, message, code="unsupported_npu2_schedule_contract"):
    if not condition:
        raise DomainError(code, message)


def physical_ports(kind):
    ports = {"clk": ("input", 1, False), "rst": ("input", 1, False)}
    streams = (("schedule_config", "input", 4), ("read_index", "output", 3), ("operands", "input", 32), ("batch_data", "output", 34)) if kind == SCHEDULER_KIND else (("batch_data", "input", 34), *(("pair" + lane, "output", 18) for lane in LANES))
    for name, direction, width in streams:
        ports[name] = direction, width, False
        ports[name + "_valid"] = direction, 1, False
        ports[name + "_ready"] = ("output" if direction == "input" else "input"), 1, False
    return ports


def _recognized_job(job):
    _require(type(job) is dict and set(job) == {"id", "k", "A", "B", "bias", "relu", "scope"}
             and type(job["id"]) is str and bool(job["id"]) and type(job["scope"]) is str
             and type(job["k"]) is int and 1 <= job["k"] <= 8 and type(job["relu"]) is bool, "Exactly one supported saved matrix job is required.")
    k = job["k"]
    _require(type(job["A"]) is list and len(job["A"]) == 2 and all(type(row) is list and len(row) == k for row in job["A"])
             and type(job["B"]) is list and len(job["B"]) == k and all(type(row) is list and len(row) == 2 for row in job["B"])
             and all(type(value) is int and -128 <= value <= 127 for matrix in (job["A"], job["B"]) for row in matrix for value in row)
             and type(job["bias"]) is list and len(job["bias"]) == 2 and all(type(value) is int and -(1 << 31) <= value < (1 << 31) for value in job["bias"]), "Saved matrix shapes and exact signed integer types are required.")


def _expected_edges(kind):
    def edge(source, sp, target, tp, behavior):
        return {"source": {"node_id": source, "port_id": source + "-" + sp}, "target": {"node_id": target, "port_id": target + "-" + tp}, "protocol": "valid_ready", "behavior": behavior}
    shared = edge("npu2-scheduler", "batch_data", "npu2-dispatcher", "batch_data", BATCH_EDGE)
    if kind == SCHEDULER_KIND:
        return [edge("npu2-control", "schedule_config", "npu2-scheduler", "schedule_config", "One stable K1..8 configuration transfer per job; independent of post configuration acceptance."),
                edge("npu2-scheduler", "read_index", "npu2-buffer", "read_index", "k=0..K-1 requests one row/column operand bundle; no read before source-job addressed bytes are loaded."),
                edge("npu2-buffer", "operands", "npu2-scheduler", "operands", "Response contains A0k,A1k,Bk0,Bk1 in declared low-to-high byte order, held until accepted."), shared]
    return [shared] + [edge("npu2-dispatcher", "pair" + lane, "npu2-pe" + lane, "pair_data", f"Dedicated lane{lane} stream; signed A(row{lane[0]},k) and B(k,col{lane[1]}) with first/last bits, independent handshake.") for lane in LANES]


def _recognize(contract):
    _require(type(contract) is dict and set(contract) == {"kind", "version", "source_node", "source_job", "source_edges", "settings", "global_integration", "design_intent"}, "The complete saved node, incident edges, settings and original job are required.")
    kind = contract["kind"]
    _require(kind in (SCHEDULER_KIND, DISPATCHER_KIND) and type(contract["version"]) is int and contract["version"] == 1, "Unsupported saved schedule contract version.")
    scheduler = kind == SCHEDULER_KIND
    node_id = "npu2-scheduler" if scheduler else "npu2-dispatcher"
    node = contract["source_node"]
    constraints = {"latency_cycles": 1, "protocol": "valid_ready", **({} if scheduler else {"lane_count": 4})}
    _require(type(node) is dict and node.get("id") == node_id and node.get("parent_id") is None and node.get("behavior") == (SCHEDULER_BEHAVIOR if scheduler else DISPATCHER_BEHAVIOR)
             and object_hash(node.get("constraints")) == object_hash(constraints) and node.get("verification") is None, "This adapter supports only the unchanged saved 2x2 scheduler/dispatcher behavior and constraints.")
    _require(type(node.get("module_name")) is str and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", node["module_name"]), "A valid saved Verilog module name is required.")
    expected = {name: (direction, width) for name, (direction, width, _) in physical_ports(kind).items() if name not in ("clk", "rst") and not name.endswith(("_valid", "_ready"))}
    ports = node.get("ports")
    _require(type(ports) is list and len(ports) == len(expected) and all(type(p) is dict for p in ports) and {p.get("name") for p in ports} == set(expected), "Exactly the saved graph streams are required.")
    for port in ports:
        direction, width = expected[port["name"]]
        _require(port.get("id") == node_id + "-" + port["name"] and port.get("direction") == direction and type(port.get("width")) is int and port["width"] == width
                 and port.get("signed") is False and port.get("protocol") == "valid_ready" and port.get("clock") == "clk" and port.get("reset") == "rst", "Modified stream names, widths, protocol or clock/reset are unsupported.")
    settings = contract["settings"]
    _require(type(settings) is dict and all(settings.get(key) == value for key, value in {"clock_name": "clk", "reset_name": "rst", "reset_active": "high", "reset_kind": "synchronous", "rtl_language": "verilog_2005"}.items()), "Saved synchronous high reset and Verilog-2005 settings are required.")
    intent = contract["design_intent"]
    _require(type(intent) is dict and all(type(intent.get(key)) is int and intent[key] == value for key, value in {"matrix_rows": 2, "matrix_columns": 2, "operand_bits": 8, "accumulator_bits": 32, "k_min": 1, "k_max": 8, "pe_instances": 4}.items()), "The saved explicit four-PE 2x2 dimensions are required.")
    integration = contract["global_integration"]
    _require(type(integration) is dict and integration.get("one_instance_per_graph_node") is True and integration.get("reset_contract") == RESET_CONTRACT
             and integration.get("handshake_expansion") == "For each valid_ready graph port use the same base name for payload plus <base>_valid and <base>_ready. Clock/reset are the shared settings, not additional graph edges.", "The saved handshake expansion and reset contract are required.")
    edges = contract["source_edges"]
    _require(type(edges) is list and all(type(edge) is dict for edge in edges), "Structured incident edges are required.")
    projected = [{key: edge.get(key) for key in ("source", "target", "protocol", "behavior")} for edge in edges]
    _require(sorted(map(object_hash, projected)) == sorted(map(object_hash, _expected_edges(kind))), "Exactly the original incident edge endpoints, protocols and behavior are supported.")
    _recognized_job(contract["source_job"])
    return contract


def operand_bundles(job):
    return [(job["A"][0][k] & 255) | ((job["A"][1][k] & 255) << 8) | ((job["B"][k][0] & 255) << 16) | ((job["B"][k][1] & 255) << 24) for k in range(job["k"])]


def batch_packets(job):
    return [value | (int(k == 0) << 32) | (int(k == job["k"] - 1) << 33) for k, value in enumerate(operand_bundles(job))]


def lane_packets(batch):
    a = (batch & 255, (batch >> 8) & 255)
    b = ((batch >> 16) & 255, (batch >> 24) & 255)
    markers = ((batch >> 32) & 3) << 16
    return {lane: a[int(lane[0])] | (b[int(lane[1])] << 8) | markers for lane in LANES}


def expand_vectors(contract):
    _recognize(contract)
    job = contract["source_job"]; batches = batch_packets(job)
    recipe = [{"action": "reset", "label": "initial_saved_reset"}]
    def add(action, label, **values):
        recipe.append({"action": action, "label": label, **values})
    if contract["kind"] == SCHEDULER_KIND:
        for cancel in ("read", "response", "batch"):
            add("configure", "cancel_" + cancel + "_configure", data=job["k"])
            if cancel == "read":
                add("stall_read", "cancel_pending_read", cycles=3)
            else:
                add("read", "cancel_" + cancel + "_read", data=0, stalls=2)
                if cancel == "response":
                    add("idle", "cancel_waiting_response", cycles=3)
                else:
                    add("response", "cancel_batch_response", data=batches[0] & 0xffffffff, delay=2)
                    add("stall_batch", "cancel_pending_batch", cycles=3)
            add("pulse", "nonclocked_reset_preserves_" + cancel)
            add("reset", "cancel_" + cancel + "_reset")
        for repeat in range(2):
            add("configure", f"complete_{repeat}_configure", data=job["k"])
            for k, batch in enumerate(batches):
                add("read", f"complete_{repeat}_read_{k}", data=k, stalls=1 + (k + repeat) % 3)
                add("response", f"complete_{repeat}_response_{k}", data=batch & 0xffffffff, delay=1 + (k + repeat) % 3)
                add("batch", f"complete_{repeat}_batch_{k}", data=batch, stalls=1 + (2 * k + repeat) % 4)
            add("idle", f"complete_{repeat}_no_extra_transfers", cycles=4)
    else:
        add("offer", "cancel_partial_capture", data=batches[0])
        add("lanes", "cancel_partial_lane00", mask=1, cycles=1)
        add("lanes", "cancel_partial_stall", mask=0, cycles=3)
        add("pulse", "nonclocked_reset_preserves_pending_lanes")
        add("reset", "cancel_partial_reset")
        for repeat in range(2):
            for k, batch in enumerate(batches):
                add("offer", f"complete_{repeat}_capture_{k}", data=batch)
                # Offer the next ORIGINAL batch while the current batch is pending.
                if k + 1 < len(batches):
                    add("hold_next", f"complete_{repeat}_hold_next_{k}", data=batches[k + 1])
                add("lanes", f"complete_{repeat}_all_stalled_{k}", mask=0, cycles=2)
                order = (1, 4, 2, 8) if (k + repeat) % 2 == 0 else (8, 2, 4, 1)
                for lane, mask in enumerate(order):
                    add("lanes", f"complete_{repeat}_independent_{k}_{lane}", mask=mask, cycles=1)
                    if lane < 3:
                        add("lanes", f"complete_{repeat}_gap_{k}_{lane}", mask=0, cycles=1)
            add("idle", f"complete_{repeat}_no_extra_transfers", cycles=4)
    return recipe


def reference_trace(contract, recipe):
    """Ordinary integer projection of expected transactions, independent of RTL."""
    batches = batch_packets(contract["source_job"]); captured = None; delivered = set(); result = []
    for step, action in enumerate(recipe):
        item = {"step": step, "stimulus": copy.deepcopy(action), "before": {}, "after": {}}
        kind = action["action"]
        if kind == "reset":
            captured, delivered = None, set(); item["reset_cancels_pending"] = True
        if contract["kind"] == SCHEDULER_KIND:
            if kind == "read": item["expected_read_index"] = action["data"]
            if kind == "response": item["expected_operand_response"] = action["data"]
            if kind == "batch": item["expected_batch"] = action["data"]
        else:
            if kind == "offer": captured, delivered = action["data"], set()
            if captured is not None:
                item["before"] = {"pair" + lane: value for lane, value in lane_packets(captured).items() if lane not in delivered}
                if kind == "lanes":
                    transferred = [lane for index, lane in enumerate(LANES) if action["mask"] & (1 << index) and lane not in delivered]
                    item["expected_lane_transfers"] = transferred; delivered.update(transferred)
                item["after"] = {"pair" + lane: value for lane, value in lane_packets(captured).items() if lane not in delivered}
                if len(delivered) == 4: captured = None
        result.append(item)
    return result


def _header(module_name, kind):
    ports = physical_ports(kind)
    lines = ["\x60timescale 1ns/1ps", "module hullcirq_contract_tb;"]
    for name, (direction, width, _) in ports.items():
        lines.append(f"{'reg' if direction == 'input' else 'wire'} {'' if width == 1 else f'[{width - 1}:0] '}{name};")
    lines += [f"{module_name} dut (" + ", ".join(f".{name}({name})" for name in ports) + ");",
              "integer cycles; integer recipe_step;",
              '// The finite 64-cycle progress bound is a harness limit, not a hardware timeout.',
              'task fail; input [1023:0] reason; begin $display("HULLCIRQ_FAIL step=%0d cycle=%0d %0s",recipe_step,cycles,reason); $finish; end endtask']
    return lines


def _scheduler_tb(contract, recipe, vector_hash):
    batches = batch_packets(contract["source_job"])
    lines = _header(contract["source_node"]["module_name"], SCHEDULER_KIND)
    lines += ["reg active; integer reads; integer responses; integer batches; integer completed; integer attempt; reg took;",
              "reg read_stalled; reg batch_stalled; reg [2:0] held_read; reg [33:0] held_batch;",
              f"reg [33:0] expected_batch [0:{len(batches)-1}];",
              "task tick; reg config_take; reg read_take; reg response_take; reg batch_take; begin",
              "clk=0; #4;",
              "if (!rst) begin",
              "if ((schedule_config_ready !== 0 && schedule_config_ready !== 1) || (read_index_valid !== 0 && read_index_valid !== 1) || (operands_ready !== 0 && operands_ready !== 1) || (batch_data_valid !== 0 && batch_data_valid !== 1)) fail(\"unknown handshake\");",
              "if (read_stalled && (read_index_valid !== 1 || read_index !== held_read)) fail(\"read request changed while stalled\");",
              "if (batch_stalled && (batch_data_valid !== 1 || batch_data !== held_batch)) fail(\"batch changed while stalled\");",
              "if (active && schedule_config_ready !== 0) fail(\"configuration ready while active\");",
              "if (read_index_valid) begin if (!active || reads != batches || reads != responses) fail(\"extra or reordered read request\"); if (read_index !== batches) fail(\"wrong read index\"); end",
              "if (batch_data_valid) begin if (!active || responses != batches+1) fail(\"batch without captured response\"); if (batch_data !== expected_batch[batches]) fail(\"batch payload or first/last marker mismatch\"); end",
              "config_take=schedule_config_valid && schedule_config_ready; read_take=read_index_valid && read_index_ready; response_take=operands_valid && operands_ready; batch_take=batch_data_valid && batch_data_ready;",
              "if (response_take && (!active || reads != responses+1)) fail(\"unexpected or duplicate operand response\");",
              "if (config_take) begin if (active) fail(\"new configuration while active\"); active=1; reads=0; responses=0; batches=0; end",
              "if (read_take) reads=reads+1; if (response_take) responses=responses+1;",
              f"if (batch_take) begin batches=batches+1; if (batches == {len(batches)}) begin active=0; completed=completed+1; end end",
              "read_stalled=read_index_valid && !read_index_ready; held_read=read_index; batch_stalled=batch_data_valid && !batch_data_ready; held_batch=batch_data;",
              "end else begin active=0; reads=0; responses=0; batches=0; read_stalled=0; batch_stalled=0; end",
              "#1; clk=1; #1; cycles=cycles+1;",
              "if (rst && (read_index_valid !== 0 || batch_data_valid !== 0)) fail(\"reset did not cancel pending transfers\"); #4; clk=0; end endtask",
              "task wait_config; begin: config_wait for(attempt=0;attempt<64;attempt=attempt+1) begin #1; took=(schedule_config_ready === 1'b1); tick; if(took) disable config_wait; end fail(\"configuration acceptance bound\"); end endtask",
              "task wait_read; begin: read_wait for(attempt=0;attempt<64;attempt=attempt+1) begin #1; if(read_index_valid === 1'b1) disable read_wait; tick; end fail(\"read request progress bound\"); end endtask",
              "task wait_response; begin: response_wait for(attempt=0;attempt<64;attempt=attempt+1) begin #1; took=(operands_ready === 1'b1); tick; if(took) disable response_wait; end fail(\"operand response acceptance bound\"); end endtask",
              "task wait_batch; begin: batch_wait for(attempt=0;attempt<64;attempt=attempt+1) begin #1; if(batch_data_valid === 1'b1) disable batch_wait; tick; end fail(\"batch progress bound\"); end endtask",
              "reg saved_read_valid; reg [2:0] saved_read; reg saved_batch_valid; reg [33:0] saved_batch;",
              "task reset_pulse; begin #1; saved_read_valid=read_index_valid; saved_read=read_index; saved_batch_valid=batch_data_valid; saved_batch=batch_data; rst=1; #1; rst=0; #1; if(read_index_valid !== saved_read_valid || batch_data_valid !== saved_batch_valid || (saved_read_valid && read_index !== saved_read) || (saved_batch_valid && batch_data !== saved_batch)) fail(\"nonclocked reset changed synchronous state\"); end endtask",
              "initial begin clk=0; rst=1; schedule_config=0; schedule_config_valid=0; read_index_ready=0; operands=0; operands_valid=0; batch_data_ready=0; cycles=0; recipe_step=0; active=0; reads=0; responses=0; batches=0; completed=0; read_stalled=0; batch_stalled=0;"]
    lines += [f"expected_batch[{k}]=34'h{batch:x};" for k, batch in enumerate(batches)]
    for step, action in enumerate(recipe):
        kind = action["action"]; lines += [f"// Original-job recipe {step}: {action['label']}", f"recipe_step={step};"]
        if kind == "reset": lines += ["rst=1; tick; rst=0; schedule_config_valid=0; operands_valid=0; read_index_ready=0; batch_data_ready=0;"]
        elif kind == "configure": lines += [f"schedule_config=4'd{action['data']}; schedule_config_valid=1; wait_config; schedule_config_valid=0;"]
        elif kind in ("read", "stall_read"):
            lines += ["read_index_ready=0; wait_read;", f"repeat({action.get('stalls', action.get('cycles', 0))}) tick;"]
            if kind == "read": lines += ["read_index_ready=1; tick; read_index_ready=0;"]
        elif kind == "response": lines += [f"repeat({action['delay']}) tick; operands=32'h{action['data']:x}; operands_valid=1; wait_response; operands_valid=0;"]
        elif kind in ("batch", "stall_batch"):
            lines += ["batch_data_ready=0; wait_batch;", f"repeat({action.get('stalls', action.get('cycles', 0))}) tick;"]
            if kind == "batch": lines += ["batch_data_ready=1; tick; batch_data_ready=0;"]
        elif kind == "idle": lines += [f"repeat({action['cycles']}) tick;"]
        elif kind == "pulse": lines += ["reset_pulse;"]
    lines += ['if (completed != 2) fail("complete original-job transfer count");', f'$display("HULLCIRQ_PASS vectors={len(recipe)} vector_hash={vector_hash}");', "$finish; end endmodule", ""]
    return "\n".join(lines)


def _dispatcher_tb(contract, recipe, vector_hash):
    lines = _header(contract["source_node"]["module_name"], DISPATCHER_KIND)
    lines += ["reg pending; reg [3:0] delivered; reg [33:0] captured; integer accepted_batches; integer completed_batches; integer total_lane_transfers; integer attempt; reg took;",
              "task tick; reg [3:0] transfers; reg batch_take; begin clk=0; #4; transfers=0;",
              "if (!rst) begin",
              "if (batch_data_ready !== 0 && batch_data_ready !== 1) fail(\"unknown batch ready\");",
              "if (pending && batch_data_ready !== 0) fail(\"new or same-cycle replacement batch accepted while pending\");"]
    for index, lane in enumerate(LANES):
        name = "pair" + lane; ai = 0 if lane[0] == "0" else 8; bi = 16 if lane[1] == "0" else 24
        expected = "{captured[33:32],captured[" + str(bi + 7) + ":" + str(bi) + "],captured[" + str(ai + 7) + ":" + str(ai) + "]}"
        lines += [f'if ({name}_valid !== (pending && !delivered[{index}])) fail("{name} valid or duplicate delivery mismatch");',
                  f'if (pending && !delivered[{index}] && {name} !== {expected}) fail("{name} payload or marker mismatch");',
                  f"transfers[{index}]={name}_valid && {name}_ready;"]
    lines += ["batch_take=batch_data_valid && batch_data_ready;",
              "if (batch_take) begin if(pending) fail(\"batch overwrite\"); captured=batch_data; pending=1; delivered=0; accepted_batches=accepted_batches+1; end",
              "else if(pending) begin delivered=delivered | transfers; total_lane_transfers=total_lane_transfers+transfers[0]+transfers[1]+transfers[2]+transfers[3]; if(delivered==4'b1111) begin pending=0; completed_batches=completed_batches+1; end end",
              "end else begin pending=0; delivered=0; captured=0; end",
              "#1; clk=1; #1; cycles=cycles+1;"]
    for lane in LANES: lines += [f'if(rst && pair{lane}_valid !== 0) fail("reset did not cancel pair{lane}");']
    lines += ["#4; clk=0; end endtask",
              "task offer; input [33:0] value; begin: offer_wait if(batch_data_valid && batch_data !== value) fail(\"harness changed stalled original batch\"); batch_data=value; batch_data_valid=1; for(attempt=0;attempt<64;attempt=attempt+1) begin #1; took=(batch_data_ready === 1'b1); tick; if(took) begin batch_data_valid=0; disable offer_wait; end end fail(\"batch acceptance progress bound\"); end endtask",
              "reg [3:0] saved_valid; reg [17:0] saved_pair [0:3];",
              "task reset_pulse; begin #1;"]
    for index, lane in enumerate(LANES): lines += [f"saved_valid[{index}]=pair{lane}_valid; saved_pair[{index}]=pair{lane};"]
    lines += ["rst=1; #1; rst=0; #1;"]
    for index, lane in enumerate(LANES): lines += [f'if(pair{lane}_valid !== saved_valid[{index}] || (saved_valid[{index}] && pair{lane} !== saved_pair[{index}])) fail("nonclocked reset changed synchronous pair{lane} state");']
    lines += ["end endtask", "initial begin clk=0; rst=1; batch_data=0; batch_data_valid=0; cycles=0; recipe_step=0; pending=0; delivered=0; captured=0; accepted_batches=0; completed_batches=0; total_lane_transfers=0;"]
    for lane in LANES: lines += [f"pair{lane}_ready=0;"]
    for step, action in enumerate(recipe):
        kind = action["action"]; lines += [f"// Original-job recipe {step}: {action['label']}", f"recipe_step={step};"]
        if kind == "reset": lines += ["rst=1; tick; rst=0; batch_data_valid=0;"] + [f"pair{lane}_ready=0;" for lane in LANES]
        elif kind == "offer": lines += [f"offer(34'h{action['data']:x});"]
        elif kind == "hold_next": lines += [f"batch_data=34'h{action['data']:x}; batch_data_valid=1;"]
        elif kind == "lanes": lines += [f"pair{lane}_ready=1'b{int(bool(action['mask'] & (1 << index)))};" for index, lane in enumerate(LANES)] + [f"repeat({action['cycles']}) tick;"]
        elif kind == "idle": lines += ["batch_data_valid=0;"] + [f"pair{lane}_ready=1;" for lane in LANES] + [f"repeat({action['cycles']}) tick;"]
        elif kind == "pulse": lines += ["reset_pulse;"]
    expected = contract["source_job"]["k"] * 2
    lines += [f'if(accepted_batches != {expected+1} || completed_batches != {expected} || total_lane_transfers != {expected*4+1}) fail("original-job batch or independent lane transfer count");',
              f'$display("HULLCIRQ_PASS vectors={len(recipe)} vector_hash={vector_hash}");', "$finish; end endmodule", ""]
    return "\n".join(lines)


def _plan(contract, node_input_hash):
    _recognize(contract)
    recipe = expand_vectors(contract); trace = reference_trace(contract, recipe); vector_hash = object_hash(recipe)
    scheduler = contract["kind"] == SCHEDULER_KIND
    tb = (_scheduler_tb if scheduler else _dispatcher_tb)(contract, recipe, vector_hash)
    coverage = {"original_job_repetitions_completed": 2, "reset_cycles": sum(v["action"] == "reset" for v in recipe),
                "nonclocked_reset_pulses": sum(v["action"] == "pulse" for v in recipe), "recipe_steps": len(recipe)}
    if scheduler:
        coverage.update({"complete_job_read_requests": 2 * contract["source_job"]["k"], "complete_job_batch_transfers": 2 * contract["source_job"]["k"],
                         "reset_cancel_points": ["pending_read", "waiting_operand_response", "pending_batch"],
                         "read_stall_recipe_cycles": sum(v.get("stalls", v.get("cycles", 0)) for v in recipe if v["action"] in ("read", "stall_read")),
                         "batch_stall_recipe_cycles": sum(v.get("stalls", v.get("cycles", 0)) for v in recipe if v["action"] in ("batch", "stall_batch"))})
    else:
        coverage.update({"complete_job_batch_transfers": 2 * contract["source_job"]["k"], "complete_job_lane_transfers": 8 * contract["source_job"]["k"],
                         "reset_cancel_points": ["partial_lane_delivery"], "independent_lane_ready_masks": sorted({v["mask"] for v in recipe if v["action"] == "lanes"}),
                         "next_original_batch_offered_while_pending": sum(v["action"] == "hold_next" for v in recipe)})
    return {"kind": contract["kind"], "version": 1, "source_node_id": contract["source_node"]["id"], "module_name": contract["source_node"]["module_name"],
            "node_input_hash": node_input_hash, "contract": copy.deepcopy(contract), "contract_hash": object_hash(contract), "source_job_hash": object_hash(contract["source_job"]),
            "expanded_vectors": recipe, "vector_hash": vector_hash, "reference_trace": trace, "reference_trace_hash": object_hash(trace),
            "testbench": tb, "testbench_sha256": content_hash(tb), "vector_count": len(recipe), "testbench_template_version": SCHEDULER_TEMPLATE if scheduler else DISPATCHER_TEMPLATE,
            "initialization_origin": "first_saved_job_projection_recipe_asserting_synchronous_reset",
            "stimulus_origin": "original_design.verification_jobs[0]_and_exact_saved_scheduler_dispatcher_node_edges_contract",
            "reference_origin": "ordinary_program_independent_original_operand_byte_projection_and_transaction_scoreboard",
            "testbench_origin": "ordinary_program_from_versioned_original_job_recipe_and_independent_transaction_scoreboard",
            "stimulus_timing": "event_driven_actual_handshakes_with_64_cycle_finite_progress_bounds",
            "coverage": coverage, "signal_checks": [name for name, (direction, _, _) in physical_ports(contract["kind"]).items() if direction == "output"],
            "limits": ["Finite local projection of the one saved original 2x2 job, repeated without changing data; not exhaustive or formal verification.",
                       "Reference trace is an expected transaction recipe, not an observed DUT waveform or exact execution cycle count.",
                       "Configuration and operand/batch payloads come only from the saved GUI job; no unrelated stage-specific test data is substituted.",
                       "Initial synchronous reset establishes state before observation; finite clocked cancellation and nonclocked reset retention are checked.",
                       "The 64-cycle waits are finite harness progress bounds, not promised hardware latency or arbitrary-duration liveness proofs.",
                       "Inactive payload is unspecified and not asserted. Reset-cleared valid state is checked after the reset clock edge.",
                       "Invalid K, other data/jobs, full-NPU integration, arithmetic outside this node, timing, PDK mapping and physical signoff are not verified by this local plan."]}


def _build(design, node_id, kind, template_version):
    template = SCHEDULER_TEMPLATE if kind == SCHEDULER_KIND else DISPATCHER_TEMPLATE
    _require(template_version in (None, template), "Unsupported explicit 2x2 schedule testbench template.", "unsupported_verification_template")
    expected_node = "npu2-scheduler" if kind == SCHEDULER_KIND else "npu2-dispatcher"
    nodes = [node for node in design.get("nodes", []) if node.get("id") == node_id]
    _require(node_id == expected_node and len(nodes) == 1, "Select the original explicit 2x2 scheduler or dispatcher.")
    jobs = design.get("verification_jobs")
    _require(type(jobs) is list and len(jobs) == 1, "Exactly one original saved matrix job is required.")
    contract = {"kind": kind, "version": 1, "source_node": copy.deepcopy(nodes[0]), "source_job": copy.deepcopy(jobs[0]),
                "source_edges": copy.deepcopy([edge for edge in design.get("edges", []) if any(edge.get(side, {}).get("node_id") == node_id for side in ("source", "target"))]),
                **{key: copy.deepcopy(design.get(key)) for key in ("settings", "global_integration", "design_intent")}}
    _recognize(contract)
    context = build_node_context(design, "verification-source", node_id)
    ports = {port["name"]: (port["direction"], port["width"], port["signed"]) for port in context["interface"]["ports"]}
    _require(ports == physical_ports(kind), "The expanded external interface must match the saved stream ports.", "invalid_verification_interface")
    return _plan(contract, context["node_input_hash"])


def build_scheduler_plan(design, node_id, template_version=None):
    return _build(design, node_id, SCHEDULER_KIND, template_version)


def build_dispatcher_plan(design, node_id, template_version=None):
    return _build(design, node_id, DISPATCHER_KIND, template_version)


def validate_schedule_plan(plan):
    try:
        valid = object_hash(plan) == object_hash(_plan(plan["contract"], plan["node_input_hash"]))
    except (KeyError, TypeError, ValueError, AttributeError, DomainError):
        valid = False
    _require(valid, "Frozen original-job scheduler/dispatcher plan is inconsistent.", "invalid_verification_plan")


def template_for_kind(kind):
    _require(kind in (SCHEDULER_KIND, DISPATCHER_KIND), "Unsupported explicit 2x2 schedule plan kind.", "unsupported_verification_template")
    return SCHEDULER_TEMPLATE if kind == SCHEDULER_KIND else DISPATCHER_TEMPLATE


def schedule_asserted_trace(plan):
    """Describe actual scoreboard assertions without inventing DUT cycles.

    The values below are guarded by actual handshakes/pending state in the TB;
    before/after refer to recipe actions rather than measured execution edges.
    """
    validate_schedule_plan(plan)
    rows = []
    scheduler = plan["kind"] == SCHEDULER_KIND
    for item in plan["reference_trace"]:
        action = item["stimulus"]; kind = action["action"]
        row = {"recipe_step": item["step"], "stimulus": copy.deepcopy(action),
               "reference_transfers": {key: copy.deepcopy(value) for key, value in item.items() if key.startswith("expected_")},
               "asserted_before": None, "asserted_after": {}, "conditional_assertions": [], "predicate_assertions": [],
               "after_condition": "versioned_event_recipe_not_measured_DUT_cycle"}
        if kind == "reset":
            row["asserted_after"] = {name: 0 for name in (("read_index_valid", "batch_data_valid") if scheduler else tuple("pair" + lane + "_valid" for lane in LANES))}
            row["after_condition"] = "after_original_recipe_reset_clock_edge"
        elif scheduler and kind in ("read", "batch"):
            name = "read_index" if kind == "read" else "batch_data"
            row["conditional_assertions"].append({"phase": "before_clock_when_actual_output_valid", "asserted": {name + "_valid": 1, name: action["data"]}, "condition": "actual_output_offer_before_acceptance_or_during_stall"})
        elif not scheduler and kind == "lanes":
            checked = {**copy.deepcopy(item["before"]), **{name + "_valid": 1 for name in item["before"]}}
            absent = {"pair" + lane + "_valid": 0 for lane in LANES if "pair" + lane not in item["before"]}
            row["conditional_assertions"].append({"phase": "before_clock_when_pending_original_batch", "asserted": {**checked, **absent, "batch_data_ready": 0}, "condition": "current_captured_batch_and_independent_delivered_lane_flags"})
        if kind not in ("reset", "pulse"):
            row["predicate_assertions"].append({"phase": "each_executed_tick_before_clock", "operator": "saved_contract_scoreboard", "checks": "known_handshakes_order_payload_stability_no_extra_transfers_and_finite_progress"})
        if kind == "pulse":
            row["predicate_assertions"].append({"phase": "after_nonclocked_reset_pulse", "operator": "equals_observed_before_pulse", "checks": "active_valid_and_active_payload_preserved_without_clock_edge"})
        rows.append(row)
    return rows

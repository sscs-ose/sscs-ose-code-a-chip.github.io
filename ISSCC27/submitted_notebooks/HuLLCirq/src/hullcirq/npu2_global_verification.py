"""Pure S08 verification helpers for the explicit two-by-two NPU.

This module recognizes the saved public ``npu_2x2_explicit`` contract and
derives a whole-system test without importing the legacy six-node S08 manager.
It performs no file I/O, model request, subprocess execution or persistence.
"""
from __future__ import annotations

import copy
import re

from .domain import DomainError
from .npu2_buffer_verification import load_packets
from .npu2_control_verification import config_packet
from .npu2_datapath_verification import projected_job
from .npu2_schedule_verification import batch_packets, lane_packets, operand_bundles
from .verification import build_verification_plan, content_hash, object_hash


PROFILE = "npu2-explicit-four-pe-v1"
PLAN_KIND = "npu2-global-original-matrix-v1"
# ``global_generation`` historically calls its plan discriminator TEMPLATE.
# Keep that small compatibility surface without importing the legacy module.
TEMPLATE = PLAN_KIND
MONITOR_TEMPLATE = "npu2-compiler-hierarchy-public-boundary-original-job-v1"
NODE_IDS = (
    "npu2-control",
    "npu2-buffer",
    "npu2-scheduler",
    "npu2-dispatcher",
    "npu2-pe00",
    "npu2-pe01",
    "npu2-pe10",
    "npu2-pe11",
    "npu2-collector",
    "npu2-post",
    "npu2-fifo",
)
MODULE_NAMES = {
    "npu2-control": "hullcirq_npu2_control",
    "npu2-buffer": "hullcirq_npu2_buffer",
    "npu2-scheduler": "hullcirq_npu2_scheduler",
    "npu2-dispatcher": "hullcirq_npu2_dispatcher",
    "npu2-pe00": "hullcirq_npu2_pe00",
    "npu2-pe01": "hullcirq_npu2_pe01",
    "npu2-pe10": "hullcirq_npu2_pe10",
    "npu2-pe11": "hullcirq_npu2_pe11",
    "npu2-collector": "hullcirq_npu2_collector",
    "npu2-post": "hullcirq_npu2_post",
    "npu2-fifo": "hullcirq_npu2_fifo",
}
LANES = ("00", "01", "10", "11")


def _require(condition, code, message, status=409):
    if not condition:
        raise DomainError(code, message, status)


def _validate_job(job):
    _require(type(job) is dict and set(job) == {"id", "k", "A", "B", "bias", "relu", "scope"}
             and type(job["id"]) is str and bool(job["id"]) and type(job["scope"]) is str
             and type(job["k"]) is int and 1 <= job["k"] <= 8 and type(job["relu"]) is bool,
             "npu2_global_job_unsupported", "Use the one exact typed 2x2 matrix job saved in the GUI design.")
    k = job["k"]
    _require(type(job["A"]) is list and len(job["A"]) == 2
             and all(type(row) is list and len(row) == k for row in job["A"])
             and type(job["B"]) is list and len(job["B"]) == k
             and all(type(row) is list and len(row) == 2 for row in job["B"])
             and all(type(value) is int and -128 <= value <= 127
                     for matrix in (job["A"], job["B"]) for row in matrix for value in row)
             and type(job["bias"]) is list and len(job["bias"]) == 2
             and all(type(value) is int and -(1 << 31) <= value < (1 << 31) for value in job["bias"]),
             "npu2_global_job_unsupported", "The saved job must retain its 2xK and Kx2 signed-INT8 matrices and two signed biases.")
    return job


def _recognize_structure(design):
    _require(type(design) is dict, "npu2_global_design_unsupported", "A complete saved 2x2 design is required.")
    nodes = design.get("nodes")
    _require(type(nodes) is list and tuple(node.get("id") for node in nodes if type(node) is dict) == NODE_IDS,
             "npu2_global_nodes_unsupported", "Use the eleven declared explicit 2x2 graph nodes in their saved order.")
    _require(all(node.get("module_name") == MODULE_NAMES[node["id"]] for node in nodes),
             "npu2_global_modules_unsupported", "Use the exact saved public module identities for all eleven nodes.")
    settings = design.get("settings")
    _require(type(settings) is dict and all(settings.get(key) == value for key, value in {
        "top_module": "hullcirq_npu2_top", "clock_name": "clk", "reset_name": "rst",
        "reset_active": "high", "reset_kind": "synchronous", "rtl_language": "verilog_2005",
    }.items()), "npu2_global_settings_unsupported",
             "This integration supports the saved hullcirq_npu2_top, clk and synchronous active-high rst contract.")
    intent = design.get("design_intent")
    _require(type(intent) is dict and all(type(intent.get(key)) is int and intent[key] == value for key, value in {
        "matrix_rows": 2, "matrix_columns": 2, "operand_bits": 8, "accumulator_bits": 32,
        "k_min": 1, "k_max": 8, "pe_instances": 4,
    }.items()) and intent.get("architecture") == "four_explicit_parallel_output_stationary_MACs",
             "npu2_global_intent_unsupported", "Use the saved explicit four-PE 2x2 design intent.")
    integration = design.get("global_integration")
    _require(type(integration) is dict and integration.get("top_module") == settings["top_module"]
             and integration.get("one_instance_per_graph_node") is True
             and integration.get("handshake_expansion") == "For each valid_ready graph port use the same base name for payload plus <base>_valid and <base>_ready. Clock/reset are the shared settings, not additional graph edges."
             and integration.get("external_load_rule") == "Load the addresses used by the saved job before configuration; gate load handshake off while busy."
             and integration.get("numerical_contract") == "C[r,c] = signed32(sum_k(signed8(A[r,k])*signed8(B[k,c])) + signed32(bias[c])); ReLU, if configured, applies after the signed32 wrap."
             and integration.get("reset_contract") == "Synchronous high reset cancels all in-flight transfers and clears arithmetic/control/output state; operand register bank bytes are retained. No power-loss retention claim.",
             "npu2_global_integration_unsupported", "The saved public integration, handshake, load, numerical and reset contracts are required.")
    streams = integration.get("public_streams")
    status = integration.get("public_status")
    _require(type(streams) is list and streams == [
        {"node_id": "npu2-control", "port": "config_data", "direction": "input", "width": 69},
        {"node_id": "npu2-buffer", "port": "load_data", "direction": "input", "width": 13},
        {"node_id": "npu2-fifo", "port": "output_data", "direction": "output", "width": 32, "signed": True},
    ] and status == [{"node_id": "npu2-control", "port": "busy"},
                     {"node_id": "npu2-control", "port": "job_done"}],
             "npu2_global_public_interface_unsupported", "The exact saved public streams and status outputs are required.")
    jobs = design.get("verification_jobs")
    _require(type(jobs) is list and len(jobs) == 1, "npu2_global_job_unsupported",
             "Exactly one original saved matrix job is required.")
    _validate_job(jobs[0])
    return nodes


def recognize_design(design):
    """Recognize the exact public/current explicit 2x2 graph.

    The existing node verification builders are intentionally reused so node
    behavior, constraints, ports, all incident edge language and the FIFO
    contract remain one source of truth.
    """
    _recognize_structure(design)
    plans = [build_verification_plan(design, node_id) for node_id in NODE_IDS]
    return {"profile": PROFILE, "node_ids": list(NODE_IDS),
            "module_names": copy.deepcopy(MODULE_NAMES),
            "node_verification_kinds": [plan["kind"] for plan in plans]}


def original_job(design):
    """Return the validated saved job without exposing mutable design state."""
    recognize_design(design)
    return copy.deepcopy(design["verification_jobs"][0])


def _top_interface(design):
    return {"module_name": design["settings"]["top_module"], "ports": [
        {"name": "clk", "direction": "input", "width": 1, "signed": False},
        {"name": "rst", "direction": "input", "width": 1, "signed": False},
        {"name": "config_data", "direction": "input", "width": 69, "signed": False},
        {"name": "config_data_valid", "direction": "input", "width": 1, "signed": False},
        {"name": "config_data_ready", "direction": "output", "width": 1, "signed": False},
        {"name": "load_data", "direction": "input", "width": 13, "signed": False},
        {"name": "load_data_valid", "direction": "input", "width": 1, "signed": False},
        {"name": "load_data_ready", "direction": "output", "width": 1, "signed": False},
        {"name": "output_data", "direction": "output", "width": 32, "signed": True},
        {"name": "output_data_valid", "direction": "output", "width": 1, "signed": False},
        {"name": "output_data_ready", "direction": "input", "width": 1, "signed": False},
        {"name": "busy", "direction": "output", "width": 1, "signed": False},
        {"name": "job_done", "direction": "output", "width": 1, "signed": False},
    ]}


def top_interface(design):
    recognize_design(design)
    return _top_interface(design)


def _signed32(bits):
    bits &= 0xFFFFFFFF
    return bits - (1 << 32) if bits & (1 << 31) else bits


def matrix_results(job):
    _validate_job(job)
    values = []
    for row in range(2):
        for column in range(2):
            total = sum(job["A"][row][k] * job["B"][k][column] for k in range(job["k"]))
            wrapped = (total + job["bias"][column]) & 0xFFFFFFFF
            signed = _signed32(wrapped)
            values.append(0 if job["relu"] and signed < 0 else signed)
    projection = projected_job(job)
    _require([value & 0xFFFFFFFF for value in values] == projection["results"],
             "npu2_global_reference_conflict", "The shared node and global arithmetic projections must agree exactly.")
    return values


def public_vectors(job):
    _validate_job(job)
    projection = projected_job(job)
    batches = batch_packets(job)
    lanes = {lane: [lane_packets(batch)[lane] for batch in batches] for lane in LANES}
    return {"template": MONITOR_TEMPLATE, "configuration": [config_packet(job)],
            "post_configuration": [projection["post_config"]], "load_words": load_packets(job),
            "read_indices": list(range(job["k"])), "operands": operand_bundles(job), "batches": batches,
            "lane_pairs": lanes,
            "lane_sums": {lane: [projection["sums"][index]] for index, lane in enumerate(LANES)},
            "collected_sums": projection["sums"], "results": projection["results"]}


def _connections(design):
    nodes = {node["id"]: node for node in design["nodes"]}
    result = []
    for edge in design["edges"]:
        source_node = nodes[edge["source"]["node_id"]]
        target_node = nodes[edge["target"]["node_id"]]
        source = next(port for port in source_node["ports"] if port["id"] == edge["source"]["port_id"])
        target = next(port for port in target_node["ports"] if port["id"] == edge["target"]["port_id"])
        _require(source["direction"] == "output" and target["direction"] == "input"
                 and source["protocol"] == target["protocol"] == edge["protocol"],
                 "npu2_global_edge_unsupported", "Every global edge must retain its declared output-to-input protocol.")
        result.append({"source_node": source_node["id"], "source_port": source["name"],
                       "target_node": target_node["id"], "target_port": target["name"],
                       "protocol": edge["protocol"]})
    return result


def _global_tb(module, recipe, vector_hash):
    expected = "\n".join(f"    expected[{index}] = 32'h{value & 0xFFFFFFFF:08x};"
                         for index, value in enumerate(recipe["expected_outputs"]))
    loads = "\n".join(f"    send_load(13'h{word:04x});" for word in recipe["load_words"])
    config = recipe["configuration_word"]
    return f"""module hullcirq_global_tb;
  reg clk=0, rst=1;
  reg [68:0] config_data=0; reg config_data_valid=0;
  wire config_data_ready; reg [12:0] load_data=0; reg load_data_valid=0;
  wire load_data_ready; wire signed [31:0] output_data;
  wire output_data_valid; reg output_data_ready=0; wire busy,job_done;
  {module} dut(.clk(clk),.rst(rst),.config_data(config_data),
    .config_data_valid(config_data_valid),.config_data_ready(config_data_ready),
    .load_data(load_data),.load_data_valid(load_data_valid),.load_data_ready(load_data_ready),
    .output_data(output_data),.output_data_valid(output_data_valid),
    .output_data_ready(output_data_ready),.busy(busy),.job_done(job_done));
  always #5 clk=~clk;
  reg signed [31:0] expected [0:3];
  integer cycles=0, outputs=0, done_count=0, started=0, after_start=0, i;
  reg stalled=0; reg [31:0] held_data=0; reg previous_done=0;
  task fail; input [511:0] message; begin
    $display("HULLCIRQ_FAIL cycle=%0d outputs=%0d %0s",cycles,outputs,message); $finish;
  end endtask
  task send_load; input [12:0] word; integer wait_cycle;
    begin
      @(negedge clk); load_data=word; load_data_valid=1;
      begin : waiting
        for(wait_cycle=0;wait_cycle<2000;wait_cycle=wait_cycle+1) begin
          @(posedge clk);
          if(load_data_ready===1'b1) begin
            @(negedge clk); load_data_valid=0; disable waiting;
          end
        end
        fail("load timeout");
      end
    end
  endtask
  always @(negedge clk) begin
    if(rst) output_data_ready=0;
    else output_data_ready=(cycles%5==1 || cycles%5==3 || cycles%5==4);
  end
  always @(posedge clk) begin
    cycles=cycles+1;
    if(rst) begin outputs=0; done_count=0; started=0; after_start=0;
      stalled=0; previous_done=0;
    end else begin
      if(stalled && (output_data_valid!==1'b1 || output_data!==held_data)) fail("output changed under backpressure");
      if(output_data_valid!==1'b0 && output_data_valid!==1'b1) fail("unknown output valid");
      if(busy!==1'b0 && busy!==1'b1) fail("unknown busy");
      if(job_done!==1'b0 && job_done!==1'b1) fail("unknown job_done");
      if(busy===1'b1 && load_data_ready!==1'b0) fail("loading enabled during job");
      if(config_data_valid===1'b1 && config_data_ready===1'b1) started=1;
      if(started) after_start=after_start+1;
      if(started && after_start>2 && outputs<4 && busy!==1'b1) fail("busy dropped before four outputs");
      if(output_data_valid===1'b1 && output_data_ready===1'b1) begin
        if(!started || outputs>=4) fail("unexpected extra output");
        if(output_data!==expected[outputs]) fail("matrix output mismatch");
        $display("HULLCIRQ_OUTPUT index=%0d value=%0d cycle=%0d",outputs,output_data,cycles);
        outputs=outputs+1;
      end
      if(job_done===1'b1) begin
        if(outputs!=4 || previous_done) fail("premature or repeated completion");
        done_count=done_count+1;
      end
      stalled=(output_data_valid===1'b1 && output_data_ready!==1'b1);
      held_data=output_data; previous_done=job_done;
    end
  end
  initial begin
{expected}
    repeat(3) @(negedge clk); rst=0;
{loads}
    @(negedge clk); config_data=69'h{config:018x}; config_data_valid=1;
    begin : config_wait
      for(i=0;i<2000;i=i+1) begin
        @(posedge clk);
        if(config_data_ready===1'b1) begin
          @(negedge clk); config_data_valid=0; disable config_wait;
        end
      end
      fail("configuration timeout");
    end
    begin : finish_wait
      for(i=0;i<12000;i=i+1) begin
        @(negedge clk);
        if(done_count==1) begin
          repeat(12) @(negedge clk);
          if(outputs!=4 || done_count!=1 || busy!==1'b0 || output_data_valid!==1'b0)
            fail("completion did not return to idle");
          // PUBLIC_COMPLETION_CHECK
          $display("HULLCIRQ_GLOBAL_PASS outputs=4 vector_hash={vector_hash}"); $finish;
        end
      end
      fail("job timeout");
    end
  end
  initial begin #200000; fail("watchdog timeout"); end
endmodule
"""


def build_plan(design):
    recognize_design(design)
    job = copy.deepcopy(design["verification_jobs"][0])
    recipe = {"kind": PLAN_KIND, "source_job": job, "load_words": load_packets(job),
              "configuration_word": config_packet(job), "expected_outputs": matrix_results(job),
              "output_ready_pattern": [0, 1, 0, 1, 1], "reset_cycles": 3,
              "load_timeout_cycles": 2000, "job_timeout_cycles": 12000}
    vector_hash = object_hash(recipe)
    tb = _global_tb(_top_interface(design)["module_name"], recipe, vector_hash)
    vectors = public_vectors(job)
    connections = _connections(design)
    return {"kind": PLAN_KIND, "version": 1, "profile": PROFILE, "recipe": recipe,
            "vector_hash": vector_hash, "public_boundary_vectors": vectors,
            "public_boundary_vector_hash": object_hash(vectors), "connections": connections,
            "connections_sha256": object_hash(connections), "testbench": tb,
            "testbench_sha256": content_hash(tb), "output_count": 4,
            "reference_origin": "ordinary_program_independent_signed_integer_2x2_matrix_dot_products_wrap32_bias_relu",
            "stimulus_origin": "same_original_GUI_matrix_job_projected_to_external_load_and_configuration_transactions",
            "scope": "one_saved_job_full_system_external_transactions_zero_delay",
            "limits": ["Only the single saved job and deterministic backpressure recipe are checked.",
                       "No synthesis, PDK mapping, timing, layout, DRC, LVS or SDF execution is implied."]}


def validate_plan(design, plan):
    _require(object_hash(plan) == object_hash(build_plan(design)), "npu2_global_plan_conflict",
             "Global stimuli and expectations must rebuild exactly from the original saved 2x2 job.")


def _require_plan(plan):
    _require(type(plan) is dict and plan.get("kind") == PLAN_KIND and plan.get("version") == 1
             and plan.get("profile") == PROFILE and plan.get("output_count") == 4,
             "npu2_global_plan_unsupported", "Use the exact explicit-2x2 global verification plan.")
    return plan


def _require_manifest(manifest):
    _require(type(manifest) is dict and type(manifest.get("design")) is dict and type(manifest.get("nodes")) is list,
             "npu2_global_manifest_unsupported", "A complete adopted source manifest is required.")
    recognize_design(manifest["design"])
    _require([entry.get("node_id") for entry in manifest["nodes"]] == list(NODE_IDS),
             "npu2_global_manifest_unsupported", "The manifest must retain all eleven sources in saved graph order.")
    _require(all(entry.get("module_name") == MODULE_NAMES[entry["node_id"]] for entry in manifest["nodes"]),
             "npu2_global_manifest_unsupported", "Manifest module identities must match the saved graph.")
    return manifest


def expected_instance_counts(manifest):
    _require_manifest(manifest)
    return {node_id: 1 for node_id in NODE_IDS}


def expected_output_count(plan=None):
    if plan is not None:
        _require_plan(plan)
    return 4


def expected_pe_records(plan):
    _require_plan(plan)
    k = plan["recipe"]["source_job"]["k"]
    return [{"node_id": "npu2-pe" + lane, "lane": lane, "inputs": k, "outputs": 1} for lane in LANES]


def compiler_public_hierarchy(scope_lines, manifest):
    """Return public instance paths derived from actual Icarus scope records."""
    expected_instance_counts(manifest)
    _require(type(scope_lines) is list and all(type(line) is str for line in scope_lines),
             "npu2_global_hierarchy_unsupported", "Compiler scope lines must be retained as text.")
    scopes = {}
    for line in scope_lines:
        match = re.fullmatch(r'(S_[A-Za-z0-9_]+)\s+\.scope (\w+),\s*"([^"]+)"(?:\s+"([^"]+)")?(.*);', line)
        _require(match is not None, "npu2_global_hierarchy_unsupported", "Compiler scope output is unsupported.")
        identifier, kind, name, module, rest = match.groups()
        _require(identifier not in scopes, "npu2_global_hierarchy_unsupported", "Compiler scope identifiers must be unique.")
        parents = re.findall(r'\bS_[A-Za-z0-9_]+\b', rest)
        scopes[identifier] = {"kind": kind, "name": name, "module": module,
                              "parent": parents[-1] if parents else None}

    def path(identifier, seen=None):
        seen = set() if seen is None else seen
        _require(identifier in scopes and identifier not in seen, "npu2_global_hierarchy_unsupported",
                 "Compiler hierarchy is incomplete or cyclic.")
        seen.add(identifier)
        record = scopes[identifier]
        _require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?', record["name"]) is not None,
                 "npu2_global_hierarchy_unsupported", "Observable instances require safe ordinary names.")
        return (path(record["parent"], seen) + "." if record["parent"] else "") + record["name"]

    result = {}
    for entry in manifest["nodes"]:
        locations = []
        for identifier, record in scopes.items():
            if record["kind"] == "module" and record["module"] == entry["module_name"]:
                absolute = path(identifier)
                _require(absolute.startswith("hullcirq_global_tb.dut."), "npu2_global_hierarchy_unsupported",
                         "Every adopted module must elaborate below the candidate top.")
                locations.append(absolute.removeprefix("hullcirq_global_tb."))
        _require(len(locations) == 1, "npu2_global_instance_count",
                 "Elaborate exactly one instance of every explicit graph node.")
        result[entry["node_id"]] = locations
    return result


def public_transfer_counts(plan):
    _require_plan(plan)
    vectors = plan["public_boundary_vectors"]
    counts = {"control_config": 1, "control_schedule": 1, "scheduler_config": 1,
              "control_post": 1, "post_config": 1, "buffer_load": len(vectors["load_words"]),
              "scheduler_read": len(vectors["read_indices"]), "buffer_read": len(vectors["read_indices"]),
              "buffer_operands": len(vectors["operands"]), "scheduler_operands": len(vectors["operands"]),
              "scheduler_batch": len(vectors["batches"]), "dispatcher_batch": len(vectors["batches"])}
    for lane in LANES:
        counts["dispatcher_pair" + lane] = len(vectors["lane_pairs"][lane])
        counts["pe" + lane + "_pair"] = len(vectors["lane_pairs"][lane])
        counts["pe" + lane + "_sum"] = 1
        counts["collector_sum" + lane] = 1
    counts.update(collector_acc=4, post_acc=4, post_result=4, fifo_input=4, fifo_output=4)
    return counts


def _validated_hierarchy(hierarchy):
    _require(type(hierarchy) is dict and list(hierarchy) == list(NODE_IDS)
             and all(type(hierarchy[node_id]) is list and len(hierarchy[node_id]) == 1
                     and type(hierarchy[node_id][0]) is str for node_id in NODE_IDS),
             "npu2_global_hierarchy_unsupported", "Use one compiler-derived public path for every explicit graph node.")
    return hierarchy


def instrument_public_testbench(plan, hierarchy):
    """Insert public-boundary checks using only frozen vectors and hierarchy."""
    _require_plan(plan)
    hierarchy = _validated_hierarchy(hierarchy)
    vectors = plan["public_boundary_vectors"]
    declarations, initial, resets, checks, completion, observations = [], [], [], [], [], []
    counters = {}

    def stream(label, node_id, name, width, expected):
        path = hierarchy[node_id][0]
        prefix = "pb_" + label
        counter = prefix + "_count"
        memory = prefix + "_expected"
        _require(expected, "npu2_global_monitor_conflict", "Every monitored stream requires at least one expected transfer.")
        declarations.extend([f"integer {counter}=0;", f"reg [{width-1}:0] {memory} [0:{len(expected)-1}];",
                             f"reg {prefix}_stalled=0;"])
        initial.extend(f"{memory}[{index}]={width}'h{value & ((1 << width)-1):x};"
                       for index, value in enumerate(expected))
        resets.append(f"{counter}=0; {prefix}_stalled=0;")
        valid, ready, data = f"{path}.{name}_valid", f"{path}.{name}_ready", f"{path}.{name}"
        checks.append(f'''if({prefix}_stalled && {valid}!==1'b1) fail("{label} valid withdrawn under backpressure");
if(({valid}!==1'b0 && {valid}!==1'b1) || ({ready}!==1'b0 && {ready}!==1'b1)) fail("unknown {label} handshake");
if({valid}===1'b1) begin
  if({counter}>={len(expected)}) fail("extra {label} valid");
  else if({data}!=={memory}[{counter}]) fail("{label} public data mismatch");
  if({ready}===1'b1) {counter}={counter}+1;
end
{prefix}_stalled=({valid}===1'b1 && {ready}!==1'b1);''')
        completion.append(f'if({counter}!={len(expected)}) fail("{label} transfer count");')
        observations.append(f'$display("HULLCIRQ_PUBLIC stream={label} transfers=%0d",{counter});')
        counters[(node_id, name)] = counter

    stream("control_config", "npu2-control", "config_data", 69, vectors["configuration"])
    stream("control_schedule", "npu2-control", "schedule_config", 4,
           [plan["recipe"]["source_job"]["k"]])
    stream("scheduler_config", "npu2-scheduler", "schedule_config", 4,
           [plan["recipe"]["source_job"]["k"]])
    stream("control_post", "npu2-control", "post_config", 65, vectors["post_configuration"])
    stream("post_config", "npu2-post", "post_config", 65, vectors["post_configuration"])
    stream("buffer_load", "npu2-buffer", "load_data", 13, vectors["load_words"])
    stream("scheduler_read", "npu2-scheduler", "read_index", 3, vectors["read_indices"])
    stream("buffer_read", "npu2-buffer", "read_index", 3, vectors["read_indices"])
    stream("buffer_operands", "npu2-buffer", "operands", 32, vectors["operands"])
    stream("scheduler_operands", "npu2-scheduler", "operands", 32, vectors["operands"])
    stream("scheduler_batch", "npu2-scheduler", "batch_data", 34, vectors["batches"])
    stream("dispatcher_batch", "npu2-dispatcher", "batch_data", 34, vectors["batches"])
    for lane in LANES:
        stream("dispatcher_pair" + lane, "npu2-dispatcher", "pair" + lane, 18, vectors["lane_pairs"][lane])
        stream("pe" + lane + "_pair", "npu2-pe" + lane, "pair_data", 18, vectors["lane_pairs"][lane])
        stream("pe" + lane + "_sum", "npu2-pe" + lane, "sum_data", 32, vectors["lane_sums"][lane])
        stream("collector_sum" + lane, "npu2-collector", "sum" + lane, 32, vectors["lane_sums"][lane])
    stream("collector_acc", "npu2-collector", "acc_data", 32, vectors["collected_sums"])
    stream("post_acc", "npu2-post", "acc_data", 32, vectors["collected_sums"])
    stream("post_result", "npu2-post", "result_data", 32, vectors["results"])
    stream("fifo_input", "npu2-fifo", "result_data", 32, vectors["results"])
    stream("fifo_output", "npu2-fifo", "output_data", 32, vectors["results"])

    path = lambda node_id: hierarchy[node_id][0]
    for connection in plan["connections"]:
        source = path(connection["source_node"])
        target = path(connection["target_node"])
        source_port, target_port = connection["source_port"], connection["target_port"]
        if connection["protocol"] == "valid_ready":
            checks.append(f'''if({source}.{source_port}_valid!=={target}.{target_port}_valid ||
 {source}.{source_port}_ready!=={target}.{target_port}_ready ||
 ({source}.{source_port}_valid===1'b1 && {source}.{source_port}!=={target}.{target_port})) fail("public stream connection mismatch");''')
        else:
            checks.append(f'if({source}.{source_port}!=={target}.{target_port}) fail("public raw connection mismatch");')
    control, buffer, fifo = path("npu2-control"), path("npu2-buffer"), path("npu2-fifo")
    checks.extend([f'''if({control}.config_data!==config_data || {control}.config_data_valid!==config_data_valid ||
 {control}.config_data_ready!==config_data_ready) fail("external config bypassed control");''',
        f'''if({buffer}.load_data!==load_data || {buffer}.load_data_valid!==(load_data_valid&&!busy) ||
 load_data_ready!==({buffer}.load_data_ready&&!busy)) fail("external load gate mismatch");''',
        f'''if({fifo}.output_data_valid!==output_data_valid || {fifo}.output_data_ready!==output_data_ready ||
 (output_data_valid===1'b1 && {fifo}.output_data!==output_data)) fail("external output bypassed FIFO");''',
        f'if({control}.busy!==busy || {control}.job_done!==job_done) fail("external control status mismatch");',
        f'if({fifo}.output_transfer!==(output_data_valid&&output_data_ready)) fail("FIFO transfer pulse mismatch");'])
    for node_id in NODE_IDS:
        checks.append(f'if({path(node_id)}.clk!==clk || {path(node_id)}.rst!==rst) fail("shared clock/reset mismatch");')
    declarations.extend(["integer pb_fifo_transfer_count=0;", "integer pb_control_done_count=0;"])
    resets.append("pb_fifo_transfer_count=0; pb_control_done_count=0;")
    checks.extend([f"if({fifo}.output_transfer===1'b1) pb_fifo_transfer_count=pb_fifo_transfer_count+1;",
                   f"if({control}.job_done===1'b1) pb_control_done_count=pb_control_done_count+1;"])
    completion.append('if(pb_fifo_transfer_count!=4 || pb_control_done_count!=1) fail("completion pulse count mismatch");')
    for record in expected_pe_records(plan):
        inc = counters[(record["node_id"], "pair_data")]
        out = counters[(record["node_id"], "sum_data")]
        observations.append(f'$display("HULLCIRQ_PE node={record["node_id"]} lane={record["lane"]} inputs=%0d outputs=%0d",{inc},{out});')
    observations.append(f'$display("HULLCIRQ_PUBLIC_PASS vector_hash={plan["public_boundary_vector_hash"]}");')
    monitor = "\n".join(declarations) + "\ninitial begin\n" + "\n".join(initial) + "\nend\n"
    monitor += "always @(posedge clk) begin\nif(rst) begin\n" + "\n".join(resets)
    monitor += "\nend else begin\n" + "\n".join(checks) + "\nend\nend\n"
    monitor += "task verify_public_completion; begin\n" + "\n".join(completion + observations) + "\nend endtask\n"
    tb = plan["testbench"]
    _require(tb.count("// PUBLIC_COMPLETION_CHECK") == 1 and tb.endswith("endmodule\n"),
             "npu2_global_monitor_conflict", "The frozen base testbench completion insertion point is missing.")
    return (tb.replace("// PUBLIC_COMPLETION_CHECK", "verify_public_completion;")
            .removesuffix("endmodule\n") + monitor + "endmodule\n", monitor)


def proof_expectations(manifest, plan):
    _require_plan(plan)
    return {"output_marker": f"HULLCIRQ_GLOBAL_PASS outputs=4 vector_hash={plan['vector_hash']}",
            "public_marker": f"HULLCIRQ_PUBLIC_PASS vector_hash={plan['public_boundary_vector_hash']}",
            "output_count": 4, "instance_counts": expected_instance_counts(manifest),
            "public_stream_transfers": [{"stream": name, "transfers": count}
                                        for name, count in public_transfer_counts(plan).items()],
            "pe_records": expected_pe_records(plan)}


def runtime_records_pass(stdout, plan):
    """Parse a retained runtime and return ``(passed, outputs, streams, pes)``."""
    _require_plan(plan)
    _require(type(stdout) is str, "npu2_global_runtime_unsupported", "Retained simulator stdout must be text.")
    outputs = [{"index": int(index), "value": int(value), "cycle": int(cycle)}
               for index, value, cycle in re.findall(
                   r'^HULLCIRQ_OUTPUT index=(\d+) value=(-?\d+) cycle=(\d+)$', stdout, re.M)]
    streams = [{"stream": name, "transfers": int(count)} for name, count in re.findall(
        r'^HULLCIRQ_PUBLIC stream=([a-z0-9_]+) transfers=(\d+)$', stdout, re.M)]
    pes = [{"node_id": node_id, "lane": lane, "inputs": int(inputs), "outputs": int(outputs_count)}
           for node_id, lane, inputs, outputs_count in re.findall(
               r'^HULLCIRQ_PE node=(npu2-pe(?:00|01|10|11)) lane=(00|01|10|11) inputs=(\d+) outputs=(\d+)$',
               stdout, re.M)]
    expected_streams = [{"stream": name, "transfers": count} for name, count in public_transfer_counts(plan).items()]
    output_marker = f"HULLCIRQ_GLOBAL_PASS outputs=4 vector_hash={plan['vector_hash']}"
    public_marker = f"HULLCIRQ_PUBLIC_PASS vector_hash={plan['public_boundary_vector_hash']}"
    passed = (stdout.splitlines().count(output_marker) == 1 and stdout.splitlines().count(public_marker) == 1
              and "HULLCIRQ_FAIL" not in stdout
              and [record["index"] for record in outputs] == list(range(4))
              and [record["value"] for record in outputs] == plan["recipe"]["expected_outputs"]
              and all(record["cycle"] > 0 and (index == 0 or record["cycle"] > outputs[index - 1]["cycle"])
                      for index, record in enumerate(outputs))
              and object_hash(streams) == object_hash(expected_streams)
              and object_hash(pes) == object_hash(expected_pe_records(plan)))
    return passed, outputs, streams, pes


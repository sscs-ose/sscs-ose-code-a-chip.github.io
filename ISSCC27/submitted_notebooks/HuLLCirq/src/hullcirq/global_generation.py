"""S08: local-model integration of supported adopted public node contracts.

The program freezes sources, builds an independent external transaction test,
and executes fixed tools. It does not implement or silently replace the top RTL.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import time

from .context import physical_interface, node_fingerprint
from .domain import DomainError, IMPLEMENTED_STAGES
from .review_actor import REVIEW_ACTORS, manual_review_fields
from .observation import ObservedState, persist_observation, require_durable_write
from .execution_submissions import PROTOCOL_VERSION, submission_view, validate_submissions
from .implementation_specs import execution_evidence_hash
from .presentation_revision import same_source_design, same_revision_design
from . import npu2_global_verification as npu2_global
from . import npu2_array_verification as npu2_array
from . import generic_global_verification as generic_global
from .provider import ChatCompletionsClient, validate_profile
from .rtl_checks import check_rtl, compare_rtl, extract_rtl, _strip_comments
from .scheduler_verification import _job, pack_configuration
from .store import new_id, strict_loads, utc_now, validate_policy_history, validate_policy_review, _replace_with_windows_retry
from .store import _io_path
from .verification import content_hash, object_hash, trusted_command, execute_fixed, _wsl_path

STAGE = "global_rtl_generation"
LEGACY_NODE_IDS = ("node-control", "node-buffer", "node-scheduler", "node-pe", "node-post", "node-fifo")
# Public compatibility alias. Historical six-node records and software fixtures
# import this name, so it must not be repurposed for the explicit 2x2 design.
NODE_IDS = LEGACY_NODE_IDS
NPU2_NODE_IDS = npu2_global.NODE_IDS
ACTIVE = {"Queued", "Running"}
TERMINAL = {"Completed", "Failed", "Cancelled", "Interrupted"}
TEMPLATE = "global-original-matrix-v1"
PROMPT_TEMPLATE_V1 = TEMPLATE
PROMPT_TEMPLATE_V2 = "global-public-contract-projection-v2"
PROMPT_TEMPLATE_V3 = "global-public-contract-projection-explicit-2x2-v3"
PROMPT_TEMPLATE_V4 = "global-public-contract-projection-explicit-2x2-v4"
PROMPT_TEMPLATE_V5 = "global-public-contract-projection-shared-array-2x2-v5"
PROMPT_TEMPLATE_V6 = generic_global.PROMPT
PROMPT_TEMPLATE_V7 = generic_global.EXTERNAL_PROMPT
PROMPT_TEMPLATE_V8 = generic_global.EXTERNAL_PROMPT_V8
PROMPT_TEMPLATE = PROMPT_TEMPLATE_V2
PROMPT_PROJECTIONS = {
    PROMPT_TEMPLATE_V1: "public_interfaces_and_integration_algorithm_excluding_numeric_verification_inputs",
    PROMPT_TEMPLATE_V2: "public_interfaces_and_lossless_compact_edge_language_v2_excluding_numeric_verification_inputs",
    PROMPT_TEMPLATE_V3: "explicit_2x2_public_interfaces_design_intent_and_lossless_edge_language_v3_excluding_numeric_verification_inputs",
    PROMPT_TEMPLATE_V4: "explicit_2x2_public_interfaces_design_intent_lossless_edges_and_final_repair_correction_v4_excluding_numeric_verification_inputs",
    PROMPT_TEMPLATE_V5: "shared_array_2x2_scalar_definition_indexed_edges_and_final_repair_v5_excluding_numeric_verification_inputs",
    PROMPT_TEMPLATE_V6: "generic_saved_graph_public_interfaces_behavior_and_exact_instance_arrays_excluding_independent_numeric_vectors",
    PROMPT_TEMPLATE_V7: "generic_explicit_external_io_typed_bindings_direct_named_instances_v7_excluding_independent_numeric_vectors",
    PROMPT_TEMPLATE_V8: "generic_explicit_external_io_typed_bindings_direct_named_instances_no_preprocessor_v8_excluding_independent_numeric_vectors",
}
MONITOR_TEMPLATE = "compiler_hierarchy_public_boundary_original_job_v1"


def require(condition, code, message, status=409):
    if not condition:
        raise DomainError(code, message, status)


def _is_npu2_design(design):
    return {n.get("id") for n in design.get("nodes", []) if type(n) is dict} == set(NPU2_NODE_IDS)


def required_node_ids(design):
    """Return the immutable source order for a supported design family."""
    if generic_global.handles(design):
        return generic_global.required_node_ids(design)
    ids = {n.get("id") for n in design.get("nodes", []) if type(n) is dict}
    if "npu2-pe" in ids:
        npu2_array.recognize_design(design)
        return npu2_array.NODE_IDS
    if ids == set(LEGACY_NODE_IDS):
        return LEGACY_NODE_IDS
    if ids == set(NPU2_NODE_IDS):
        npu2_global.recognize_design(design)
        return NPU2_NODE_IDS
    raise DomainError("global_nodes_unsupported",
                      "Configure a generic cycle-vector system contract in Specifications to integrate this design. Historical NPU profiles remain available for their exact saved designs.")


def top_interface(design):
    if generic_global.handles(design):
        return generic_global.top_interface(design)
    if npu2_array.is_array_design(design):
        return npu2_array.top_interface(design)
    if _is_npu2_design(design):
        return npu2_global.top_interface(design)
    settings = design["settings"]
    require(settings.get("clock_name") == "clk" and settings.get("reset_name") == "rst"
            and settings.get("reset_active") == "high" and settings.get("reset_kind") == "synchronous"
            and settings.get("rtl_language") == "verilog_2005",
            "unsupported_global_settings", "S08 currently supports clk and synchronous active-high rst with Verilog-2005.")
    ports = [{"name": name, "direction": direction, "width": width, "signed": signed}
             for name, direction, width, signed in (
                 ("clk", "input", 1, False), ("rst", "input", 1, False),
                 ("config_data", "input", 134, False), ("config_data_valid", "input", 1, False),
                 ("config_data_ready", "output", 1, False), ("load_data", "input", 16, False),
                 ("load_data_valid", "input", 1, False), ("load_data_ready", "output", 1, False),
                 ("output_data", "output", 32, True), ("output_data_valid", "output", 1, False),
                 ("output_data_ready", "input", 1, False), ("busy", "output", 1, False),
                 ("job_done", "output", 1, False))]
    return {"module_name": settings["top_module"], "ports": ports}


def original_job(design):
    if generic_global.handles(design):
        generic_global.build_plan(design)
        return copy.deepcopy(design['global_verification'])
    if npu2_array.is_array_design(design):
        return npu2_array.original_job(design)
    if _is_npu2_design(design):
        return npu2_global.original_job(design)
    jobs = design.get("verification_jobs")
    require(type(jobs) is list and len(jobs) == 1, "global_job_ambiguous",
            "S08 currently requires exactly one original saved matrix job.")
    return copy.deepcopy(_job(jobs[0]))


def canonical_job_hash(design):
    # A generic system's original workload is its explicitly saved cycle
    # contract, not an absent or unrelated legacy matrix-job collection.
    return object_hash(design['global_verification'] if generic_global.handles(design) else design['verification_jobs'])


def matrix_results(job):
    """Independent signed-integer dot products, then wrap32 bias and ReLU."""
    _job(job)
    values = []
    for row in range(4):
        for column in range(4):
            total = sum(job["A"][row][k] * job["B"][k][column] for k in range(job["k"]))
            total = (total + job["bias"][column]) & 0xFFFFFFFF
            total = total - (1 << 32) if total & (1 << 31) else total
            values.append(max(0, total) if job["relu"] else total)
    return values


def load_words(job):
    _job(job)
    return ([((row * 16 + k) << 8) | (job["A"][row][k] & 255)
             for row in range(4) for k in range(job["k"])]
            + [(1 << 14) | ((k * 4 + column) << 8) | (job["B"][k][column] & 255)
               for k in range(job["k"]) for column in range(4)])


def _global_tb(module, recipe, vector_hash):
    expected = "\n".join(f"    expected[{i}] = 32'h{value & 0xFFFFFFFF:08x};"
                         for i, value in enumerate(recipe["expected_outputs"]))
    loads = "\n".join(f"    send_load(16'h{word:04x});" for word in recipe["load_words"])
    config = recipe["configuration_word"]
    return f"""module hullcirq_global_tb;
  reg clk=0, rst=1;
  reg [133:0] config_data=0; reg config_data_valid=0;
  wire config_data_ready; reg [15:0] load_data=0; reg load_data_valid=0;
  wire load_data_ready; wire signed [31:0] output_data;
  wire output_data_valid; reg output_data_ready=0; wire busy,job_done;
  {module} dut(.clk(clk),.rst(rst),.config_data(config_data),
    .config_data_valid(config_data_valid),.config_data_ready(config_data_ready),
    .load_data(load_data),.load_data_valid(load_data_valid),.load_data_ready(load_data_ready),
    .output_data(output_data),.output_data_valid(output_data_valid),
    .output_data_ready(output_data_ready),.busy(busy),.job_done(job_done));
  always #5 clk=~clk;
  reg signed [31:0] expected [0:15];
  integer cycles=0, outputs=0, done_count=0, started=0, after_start=0, i;
  reg stalled=0; reg [31:0] held_data=0; reg previous_done=0;
  task fail; input [511:0] message; begin
    $display("HULLCIRQ_FAIL cycle=%0d outputs=%0d %0s",cycles,outputs,message); $finish;
  end endtask
  task send_load; input [15:0] word; integer wait_cycle;
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
      if(stalled && (output_data_valid!==1'b1 || output_data!==held_data))
        fail("output changed under backpressure");
      if(output_data_valid!==1'b0 && output_data_valid!==1'b1) fail("unknown output valid");
      if(busy!==1'b0 && busy!==1'b1) fail("unknown busy");
      if(job_done!==1'b0 && job_done!==1'b1) fail("unknown job_done");
      if(busy===1'b1 && load_data_ready!==1'b0) fail("loading enabled during job");
      if(config_data_valid===1'b1 && config_data_ready===1'b1) started=1;
      if(started) after_start=after_start+1;
      if(started && after_start>2 && outputs<16 && busy!==1'b1) fail("busy dropped before 16 outputs");
      if(output_data_valid===1'b1 && output_data_ready===1'b1) begin
        if(!started || outputs>=16) fail("unexpected extra output");
        if(output_data!==expected[outputs]) fail("matrix output mismatch");
        $display("HULLCIRQ_OUTPUT index=%0d value=%0d cycle=%0d",outputs,output_data,cycles);
        outputs=outputs+1;
      end
      if(job_done===1'b1) begin
        if(outputs!=16 || previous_done) fail("premature or repeated completion");
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
    @(negedge clk); config_data=134'h{config:034x}; config_data_valid=1;
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
          if(outputs!=16 || done_count!=1 || busy!==1'b0 || output_data_valid!==1'b0)
            fail("completion did not return to idle");
          // PUBLIC_COMPLETION_CHECK
          $display("HULLCIRQ_GLOBAL_PASS outputs=16 vector_hash={vector_hash}"); $finish;
        end
      end
      fail("job timeout");
    end
  end
  initial begin #200000; fail("watchdog timeout"); end
endmodule
"""


def public_vectors(job):
    """Original-job projection for actual module boundary assertions."""
    requests=[]; pairs=[]; metadata=[]; partials=[]; sums=[]
    for row in range(4):
        for column in range(4):
            total=0; lane_partials=[]; lane_pairs=[]
            for k in range(job["k"]):
                requests.append(((k*4+column)<<8)|(row*16+k))
                pair=((job["B"][k][column]&255)<<8)|(job["A"][row][k]&255)
                pairs.append(pair); lane_pairs.append(pair)
                metadata.append(row*4+column | (16 if k==0 else 0) | (32 if k==job["k"]-1 else 0))
                total+=job["A"][row][k]*job["B"][k][column]
                lane_partials.append(total & 0xffffffff)
            partials.append({"pairs":lane_pairs,"partial_sums":lane_partials}); sums.append(total & 0xffffffff)
    return {"template":MONITOR_TEMPLATE,"load_words":load_words(job),"configuration":[pack_configuration(job)],
            "post_configuration":[pack_configuration(job)>>5],"requests":requests,"pairs":pairs,"metadata":metadata,
            "pe_lanes":partials,"final_sums":sums,"results":[v&0xffffffff for v in matrix_results(job)]}


def compiler_public_hierarchy(scope_lines, manifest):
    """Derive paths from compiler scopes, exposing only adopted public ports.

    Compiler-derived instance paths are per-candidate measurement locations,
    not stable internal-net names supplied to the global generation model.
    """
    if generic_global.handles(manifest["design"]):
        return generic_global.hierarchy(scope_lines, manifest)
    if npu2_array.is_array_design(manifest["design"]):
        return npu2_array.compiler_public_hierarchy(scope_lines, manifest)
    if _is_npu2_design(manifest["design"]):
        return npu2_global.compiler_public_hierarchy(scope_lines, manifest)
    scopes={}
    for line in scope_lines:
        match=re.fullmatch(r'(S_[A-Za-z0-9_]+)\s+\.scope (\w+),\s*"([^"]+)"(?:\s+"([^"]+)")?(.*);',line)
        require(match is not None,"global_hierarchy_unsupported","Compiler scope output is unsupported.")
        identifier,kind,name,module,rest=match.groups()
        parents=re.findall(r'\bS_[A-Za-z0-9_]+\b',rest)
        scopes[identifier]={"kind":kind,"name":name,"module":module,"parent":parents[-1] if parents else None}
    def path(identifier,seen=None):
        seen=set() if seen is None else seen
        require(identifier not in seen and identifier in scopes,"global_hierarchy_unsupported","Compiler hierarchy is incomplete or cyclic.")
        seen.add(identifier); record=scopes[identifier]
        require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?',record["name"]) is not None,
                "global_hierarchy_unsupported","Use ordinary identifiers or constant generate indices for observable instances.")
        return (path(record["parent"],seen)+"." if record["parent"] else "")+record["name"]
    result={}
    for entry in manifest["nodes"]:
        locations=[]
        for identifier,record in scopes.items():
            if record["kind"]=="module" and record["module"]==entry["module_name"]:
                absolute=path(identifier)
                require(absolute.startswith("hullcirq_global_tb.dut."),"global_hierarchy_unsupported","Adopted modules must be below the candidate top.")
                locations.append(absolute.removeprefix("hullcirq_global_tb."))
        require(len(locations)==(16 if entry["node_id"]=="node-pe" else 1),"global_instance_count","All adopted module instances must elaborate exactly.")
        result[entry["node_id"]]=sorted(locations)
    return result


def instrument_public_testbench(plan, hierarchy):
    """Generate ordinary-program monitors from the frozen job and public ports."""
    if plan.get("kind") == generic_global.KIND:
        return generic_global.instrument(plan, hierarchy)
    if plan.get("kind") == npu2_array.TEMPLATE:
        return npu2_array.instrument_public_testbench(plan, hierarchy)
    if plan.get("kind") == npu2_global.TEMPLATE:
        return npu2_global.instrument_public_testbench(plan, hierarchy)
    vectors=plan["public_boundary_vectors"]
    streams=[]; checks=[]; declarations=[]; initial=[]; resets=[]; completion=[]; observations=[]
    counter_by_path={}
    def stream(label,path,name,width,expected):
        prefix="pb_"+label; counter=prefix+"_count"; memory=prefix+"_expected"
        declarations.extend([f"integer {counter}=0;",f"reg [{width-1}:0] {memory} [0:{len(expected)-1}];"])
        declarations.append(f"reg {prefix}_stalled=0;")
        initial.extend(f"{memory}[{i}]={width}'h{value & ((1<<width)-1):x};" for i,value in enumerate(expected))
        resets.append(counter+"=0; "+prefix+"_stalled=0;")
        valid=f"{path}.{name}_valid"; ready=f"{path}.{name}_ready"; data=f"{path}.{name}"
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
        counter_by_path[(path,name)]=counter
        return counter
    control=hierarchy["node-control"][0]; buffer=hierarchy["node-buffer"][0]
    scheduler=hierarchy["node-scheduler"][0]; post=hierarchy["node-post"][0]; fifo=hierarchy["node-fifo"][0]
    stream("control_config",control,"config_data",134,vectors["configuration"])
    stream("control_schedule",control,"schedule_config",134,vectors["configuration"])
    stream("scheduler_config",scheduler,"schedule_config",134,vectors["configuration"])
    stream("control_post",control,"post_config",129,vectors["post_configuration"])
    stream("post_config",post,"post_config",129,vectors["post_configuration"])
    stream("buffer_load",buffer,"load_data",16,vectors["load_words"])
    stream("scheduler_request",scheduler,"read_request",16,vectors["requests"])
    stream("buffer_request",buffer,"read_request",16,vectors["requests"])
    stream("buffer_response",buffer,"read_response",16,vectors["pairs"])
    stream("scheduler_response",scheduler,"read_response",16,vectors["pairs"])
    pair_counter=stream("scheduler_pair",scheduler,"pair_data",16,vectors["pairs"])
    # Check metadata before incrementing the associated stream counter.
    declarations.append(f'reg [5:0] pb_metadata [0:{len(vectors["metadata"])-1}];')
    initial.extend(f'pb_metadata[{i}]=6\'h{value:x};' for i,value in enumerate(vectors["metadata"]))
    checks.insert(len(checks)-1,f'''if({scheduler}.pair_data_valid===1'b1 && {pair_counter}<{len(vectors["pairs"])} &&
 {scheduler}.pair_meta!==pb_metadata[{pair_counter}]) fail("scheduler pair metadata mismatch");''')
    stream("post_acc",post,"acc_data",32,vectors["final_sums"])
    stream("post_result",post,"result_data",32,vectors["results"])
    stream("fifo_input",fifo,"result_data",32,vectors["results"])
    stream("fifo_output",fifo,"output_data",32,vectors["results"])
    # Lanes are discovered from actual transfers, not guessed from instance
    # names or lexical ordering of a generate loop. Each lane must be served
    # by exactly one PE and its own K original operands and partial sums.
    declarations.extend(["integer pb_pair_lane=-1, pb_final_transfers=0, pb_pe_pair_transfers=0;",
        "integer pb_clear_count=0, pb_schedule_done_count=0, pb_control_done_count=0;",
        "integer pb_lane_owner [0:15];"])
    initial.extend(f"pb_lane_owner[{i}]=-1;" for i in range(16))
    resets.extend(["pb_clear_count=0; pb_schedule_done_count=0; pb_control_done_count=0;",
                   *[f"pb_lane_owner[{i}]=-1;" for i in range(16)]])
    early=["pb_pair_lane=-1; pb_final_transfers=0; pb_pe_pair_transfers=0;",
           f"if({scheduler}.pair_data_valid===1'b1 && {scheduler}.pair_data_ready===1'b1) pb_pair_lane={scheduler}.pair_meta[3:0];"]
    expected_pairs=vectors["pe_lanes"]
    for index,path in enumerate(hierarchy["node-pe"]):
        prefix=f"pb_pe{index}"; inc=prefix+"_input_count"; out=prefix+"_output_count"; lane=prefix+"_lane"
        declarations.extend([f"integer {inc}=0,{out}=0,{lane}=-1;",f"reg [15:0] {prefix}_pairs [0:{16*len(expected_pairs[0]['pairs'])-1}];",
                             f"reg [31:0] {prefix}_partials [0:{16*len(expected_pairs[0]['pairs'])-1}];"])
        k=len(expected_pairs[0]["pairs"])
        for lane_index,values in enumerate(expected_pairs):
            initial.extend(f"{prefix}_pairs[{lane_index*k+i}]=16'h{value:x};" for i,value in enumerate(values["pairs"]))
            initial.extend(f"{prefix}_partials[{lane_index*k+i}]=32'h{value:x};" for i,value in enumerate(values["partial_sums"]))
        resets.append(f"{inc}=0; {out}=0; {lane}=-1;")
        early.append(f'''if({path}.rst!==(rst|{scheduler}.pe_clear)) fail("PE reset broadcast mismatch");
if(({path}.pair_data_valid!==1'b0 && {path}.pair_data_valid!==1'b1) || ({path}.pair_data_ready!==1'b0 && {path}.pair_data_ready!==1'b1) ||
   ({path}.acc_data_valid!==1'b0 && {path}.acc_data_valid!==1'b1) || ({path}.acc_data_ready!==1'b0 && {path}.acc_data_ready!==1'b1)) fail("unknown PE public handshake");
if({path}.pair_data_valid===1'b1 && {path}.pair_data_ready===1'b1) begin
  pb_pe_pair_transfers=pb_pe_pair_transfers+1;
  if(pb_pair_lane<0 || {path}.pair_data!=={scheduler}.pair_data || {inc}>={k}) fail("PE dispatch mismatch");
  if({lane}<0) begin
    {lane}=pb_pair_lane;
    if(pb_pair_lane>=0) begin
      if(pb_lane_owner[pb_pair_lane]!=-1) fail("two PEs own one lane");
      pb_lane_owner[pb_pair_lane]={index};
    end
  end
  if(pb_pair_lane!={lane}) fail("PE lane changed");
  if({lane}>=0 && {inc}<{k} && {path}.pair_data!=={prefix}_pairs[{lane}*{k}+{inc}]) fail("PE original operand mismatch");
  {inc}={inc}+1;
end
if({path}.acc_data_valid===1'b1) begin
  if({lane}<0 || {out}>={k} || {out}>={inc}) fail("unexpected PE partial sum");
  else if({path}.acc_data!=={prefix}_partials[{lane}*{k}+{out}]) fail("PE public partial sum mismatch");
  if({path}.acc_data_ready===1'b1) begin
    if({out}=={k-1}) begin
      pb_final_transfers=pb_final_transfers+1;
      if({post}.acc_data_valid!==1'b1 || {post}.acc_data_ready!==1'b1 || {post}.acc_data!=={path}.acc_data) fail("final PE result not transferred to post");
    end
    {out}={out}+1;
  end
end''')
        completion.append(f'if({inc}!={k} || {out}!={k} || {lane}<0) fail("PE lane participation count");')
        observations.append(f'$display("HULLCIRQ_PE instance={index} lane=%0d inputs=%0d outputs=%0d",{lane},{inc},{out});')
    early.append(f'''if(pb_pe_pair_transfers!=(pb_pair_lane>=0 ? 1 : 0)) fail("scheduler/PE transfer mismatch");
if(pb_final_transfers!=(({post}.acc_data_valid===1'b1 && {post}.acc_data_ready===1'b1) ? 1 : 0)) fail("post input bypassed final PE output");''')
    def connect(a,name,b,target=None):
        target=target or name
        return f'''if({a}.{name}_valid!=={b}.{target}_valid || {a}.{name}_ready!=={b}.{target}_ready ||
 ({a}.{name}_valid===1'b1 && {a}.{name}!=={b}.{target})) fail("public stream connection mismatch");'''
    early.extend([connect(control,"schedule_config",scheduler),connect(control,"post_config",post),
        connect(scheduler,"read_request",buffer),connect(buffer,"read_response",scheduler),connect(post,"result_data",fifo),
        f'''if({fifo}.output_data_valid!==output_data_valid || {fifo}.output_data_ready!==output_data_ready ||
 (output_data_valid===1'b1 && {fifo}.output_data!==output_data)) fail("external output bypassed FIFO");
if({control}.config_data_valid!==config_data_valid || {control}.config_data_ready!==config_data_ready ||
 (config_data_valid===1'b1 && {control}.config_data!==config_data)) fail("external config bypassed control");
if({control}.busy!==busy || {control}.job_done!==job_done) fail("external control output mismatch");
if({fifo}.output_transfer!==(output_data_valid&&output_data_ready) || {control}.output_transfer!=={fifo}.output_transfer) fail("completion feedback mismatch");
if({scheduler}.pe_clear===1'b1) begin
 if({pair_counter}!=0) fail("PE clear after pair dispatch"); pb_clear_count=pb_clear_count+1;
end
if({scheduler}.schedule_done===1'b1) begin
 if({pair_counter}!={len(vectors['pairs'])}) fail("premature dispatch completion"); pb_schedule_done_count=pb_schedule_done_count+1;
end
if({control}.job_done===1'b1) pb_control_done_count=pb_control_done_count+1;'''])
    for node_id,paths in hierarchy.items():
        for path in paths:
            early.append(f'if({path}.clk!==clk) fail("module clock connection mismatch");')
            if node_id!="node-pe": early.append(f'if({path}.rst!==rst) fail("module reset connection mismatch");')
    completion.extend(['if(pb_clear_count!=1 || pb_schedule_done_count!=1 || pb_control_done_count!=1) fail("public pulse count mismatch");',
                       *[f'if(pb_lane_owner[{i}]<0) fail("missing PE lane");' for i in range(16)]])
    observations.append(f'$display("HULLCIRQ_PUBLIC_PASS vector_hash={plan["public_boundary_vector_hash"]}");')
    monitor="\n".join(declarations)+"\ninitial begin\n"+"\n".join(initial)+"\nend\n"
    monitor+="always @(posedge clk) begin\nif(rst) begin\n"+"\n".join(resets)+"\nend else begin\n"+"\n".join(early+checks)+"\nend\nend\n"
    monitor+="task verify_public_completion; begin\n"+"\n".join(completion+observations)+"\nend endtask\n"
    tb=plan["testbench"].replace("// PUBLIC_COMPLETION_CHECK","verify_public_completion;")
    tb=tb.removesuffix("endmodule\n")+monitor+"endmodule\n"
    return tb,monitor


def public_transfer_counts(plan):
    if plan.get("kind") == generic_global.KIND:
        return {}
    if plan.get("kind") == npu2_array.TEMPLATE:
        return npu2_array.public_transfer_counts(plan)
    if plan.get("kind") == npu2_global.TEMPLATE:
        return npu2_global.public_transfer_counts(plan)
    v=plan["public_boundary_vectors"]
    return {"control_config":1,"control_schedule":1,"scheduler_config":1,"control_post":1,"post_config":1,
            "buffer_load":len(v["load_words"]),"scheduler_request":len(v["requests"]),"buffer_request":len(v["requests"]),
            "buffer_response":len(v["pairs"]),"scheduler_response":len(v["pairs"]),"scheduler_pair":len(v["pairs"]),
            "post_acc":16,"post_result":16,"fifo_input":16,"fifo_output":16}


def build_global_plan(design):
    if generic_global.handles(design):
        return generic_global.build_plan(design)
    if npu2_array.is_array_design(design):
        return npu2_array.build_plan(design)
    if _is_npu2_design(design):
        return npu2_global.build_plan(design)
    job = original_job(design)
    recipe = {"kind": TEMPLATE, "source_job": job, "load_words": load_words(job),
              "configuration_word": pack_configuration(job), "expected_outputs": matrix_results(job),
              "output_ready_pattern": [0, 1, 0, 1, 1], "reset_cycles": 3,
              "load_timeout_cycles": 2000, "job_timeout_cycles": 12000}
    vector_hash = object_hash(recipe)
    tb = _global_tb(top_interface(design)["module_name"], recipe, vector_hash)
    boundary=public_vectors(job)
    return {"kind": TEMPLATE, "version": 1, "recipe": recipe, "vector_hash": vector_hash,
            "public_boundary_vectors":boundary,"public_boundary_vector_hash":object_hash(boundary),
            "testbench": tb, "testbench_sha256": content_hash(tb), "output_count": 16,
            "reference_origin": "ordinary_program_independent_signed_integer_matrix_dot_products_wrap32_bias_relu",
            "stimulus_origin": "same_original_GUI_matrix_job_projected_to_external_load_and_configuration_transactions",
            "scope": "one_saved_job_full_system_external_transactions_zero_delay",
            "limits": ["Only the single saved job and deterministic backpressure recipe are checked.",
                       "No synthesis, PDK mapping, timing, layout, DRC, LVS or SDF execution is implied."]}


def validate_global_plan(design, plan):
    require(object_hash(plan) == object_hash(build_global_plan(design)), "global_plan_conflict",
            "Global stimuli and expectations must rebuild exactly from the original GUI job, including JSON numeric types.")


def expected_instance_counts(manifest):
    if generic_global.handles(manifest["design"]):
        return generic_global.instance_counts(manifest)
    if npu2_array.is_array_design(manifest["design"]):
        return npu2_array.expected_instance_counts(manifest)
    if _is_npu2_design(manifest["design"]):
        return npu2_global.expected_instance_counts(manifest)
    return {node_id: 16 if node_id == "node-pe" else 1 for node_id in LEGACY_NODE_IDS}


def expected_output_count(plan):
    if plan.get("kind") == generic_global.KIND:
        return sum(len(cycle['expect']) for cycle in plan['contract']['cycles'])
    if plan.get("kind") == npu2_array.TEMPLATE:
        return 4
    if plan.get("kind") == npu2_global.TEMPLATE:
        return npu2_global.expected_output_count(plan)
    return 16


def expected_pe_records(plan):
    if plan.get("kind") == generic_global.KIND:
        return []
    if plan.get("kind") == npu2_array.TEMPLATE:
        return npu2_array.expected_pe_records(plan)
    if plan.get("kind") == npu2_global.TEMPLATE:
        return npu2_global.expected_pe_records(plan)
    k = plan["recipe"]["source_job"]["k"]
    return [{"instance": index, "lane": index, "inputs": k, "outputs": k} for index in range(16)]


def pe_records_match_plan(plan, records):
    """Keep monitor ordinals distinct from the logical lanes they discover.

    The historical six-definition monitor discovers each PE's lane from actual
    transfers. Its lexical compiler-instance order need not equal lane order.
    Explicit and shared-array profiles retain their exact existing bindings.
    """
    if plan.get("kind") in {generic_global.KIND, npu2_array.TEMPLATE, npu2_global.TEMPLATE}:
        return object_hash(records) == object_hash(expected_pe_records(plan))
    k = plan["recipe"]["source_job"]["k"]
    fields = {"instance", "lane", "inputs", "outputs"}
    return (type(records) is list and len(records) == 16
            and all(type(record) is dict and set(record) == fields
                    and all(type(record[field]) is int for field in fields) for record in records)
            and [record["instance"] for record in records] == list(range(16))
            and sorted(record["lane"] for record in records) == list(range(16))
            and all(record["inputs"] == k and record["outputs"] == k for record in records))


def parse_runtime_records(stdout, plan, stderr=''):
    """Parse and validate the retained simulator record language for a plan."""
    if plan.get("kind") == generic_global.KIND:
        return generic_global.runtime_records(stdout, plan, stderr)
    if plan.get("kind") == npu2_array.TEMPLATE:
        return npu2_array.runtime_records_pass(stdout, plan)
    if plan.get("kind") == npu2_global.TEMPLATE:
        return npu2_global.runtime_records_pass(stdout, plan)
    outputs = [{"index": int(index), "value": int(value), "cycle": int(cycle)}
               for index, value, cycle in re.findall(
                   r"^HULLCIRQ_OUTPUT index=(\d+) value=(-?\d+) cycle=(\d+)$", stdout, re.M)]
    streams = [{"stream": name, "transfers": int(count)} for name, count in re.findall(
        r"^HULLCIRQ_PUBLIC stream=([a-z0-9_]+) transfers=(\d+)$", stdout, re.M)]
    pes = [{"instance": int(instance), "lane": int(lane), "inputs": int(inputs), "outputs": int(outputs_count)}
           for instance, lane, inputs, outputs_count in re.findall(
               r"^HULLCIRQ_PE instance=(\d+) lane=(\d+) inputs=(\d+) outputs=(\d+)$", stdout, re.M)]
    output_count = expected_output_count(plan)
    expected_streams = [{"stream": name, "transfers": count}
                        for name, count in public_transfer_counts(plan).items()]
    passed = (stdout.splitlines().count(
                  f"HULLCIRQ_GLOBAL_PASS outputs={output_count} vector_hash={plan['vector_hash']}") == 1
              and stdout.splitlines().count(
                  f"HULLCIRQ_PUBLIC_PASS vector_hash={plan['public_boundary_vector_hash']}") == 1
              and "HULLCIRQ_FAIL" not in stdout
              and [record["index"] for record in outputs] == list(range(output_count))
              and [record["value"] for record in outputs] == plan["recipe"]["expected_outputs"]
              and all(record["cycle"] > 0
                      and (index == 0 or record["cycle"] > outputs[index - 1]["cycle"])
                      for index, record in enumerate(outputs))
              and object_hash(streams) == object_hash(expected_streams)
              and pe_records_match_plan(plan, pes))
    return passed, outputs, streams, pes


def fixed_global_commands(compiler, manifest, folder):
    """Pure reconstruction of the three trusted operations, including sources."""
    folder = Path(folder).resolve()
    parent = Path(compiler.get("working_directory") or tempfile.gettempdir()).resolve()
    require(folder.parent == parent and folder.name.startswith("hullcirq-global-"),
            "global_tool_path_conflict", "Global artifacts must retain the configured fixed-tool working directory.")
    executable = compiler["executable"]
    require(executable.replace("\\", "/").split("/")[-1].lower() in ("iverilog", "iverilog.exe"),
            "invalid_compiler", "Global verification uses Icarus only.")
    path = lambda p: _wsl_path(p) if compiler["kind"] == "wsl" else str(p)
    base = ["-B", compiler["base_directory"]] if compiler.get("base_directory") else []
    runtime = executable.rsplit("/", 1)[0] + "/vvp" if compiler["kind"] == "wsl" else str(Path(executable).with_name(
        "vvp.exe" if executable.lower().endswith(".exe") else "vvp"))
    sources = [folder / "candidate_top.v", *(folder / (n["node_id"] + ".v") for n in manifest["nodes"])]
    tb_module = (generic_global.testbench_module(build_global_plan(manifest['design']))
                 if generic_global.handles(manifest['design']) else "hullcirq_global_tb")
    return [trusted_command(compiler, executable, [*base, "-V"], parent),
            trusted_command(compiler, executable, [*base, "-g2005", "-s", tb_module, "-o", path(folder / "hierarchy.vvp"), *map(path, sources), path(folder / "original_job_tb.v")], parent),
            trusted_command(compiler, executable, [*base, "-g2005", "-s", tb_module, "-o", path(folder / "global.vvp"), *map(path, sources), path(folder / "instrumented_job_tb.v")], parent),
            trusted_command(compiler, runtime, [*(["-M", compiler["base_directory"]] if compiler.get("base_directory") else []), path(folder / "global.vvp")], parent)]


def check_global_rtl(rtl, manifest, plan, compiler, cancel_event=None):
    """Compile the model TOP with immutable adopted sources and simulate externally."""
    validate_global_plan(manifest["design"], plan)
    interface = top_interface(manifest["design"])
    checked = check_rtl(rtl, interface, interface["module_name"], None)
    result = {"validation_status": "Failed", "executed": False, "exit_code": None,
              "checks": {"interface": checked["checks"]["interface"]}, "diagnostics": [
                  d for d in checked["diagnostics"] if d["code"] not in ("syntax_compiler_unavailable", "rtl_check_limits")],
              "commands": [], "rtl_sha256": content_hash(rtl), "source_manifest_sha256": object_hash(manifest),
              "vector_hash": plan["vector_hash"], "testbench_sha256": plan["testbench_sha256"],
              "scope": plan.get("scope", "saved_generic_external_cycle_vectors") if plan.get('kind') == generic_global.KIND else plan["scope"],
              "stdout": "", "stderr": "", "tool_configuration": copy.deepcopy(compiler)}
    if checked["checks"]["interface"]["validation_status"] != "Passed":
        return result
    if 'external_io' in manifest['design']:
        wiring = generic_global.check_external_wiring(rtl, manifest)
        result['external_io_wiring_proof'] = wiring
        result['checks']['external_io_wiring'] = {'validation_status': wiring['validation_status'],
                                                 'version': wiring['version'], 'scope': wiring['scope']}
        result['diagnostics'].extend(wiring['diagnostics'])
        if wiring['validation_status'] != 'Passed':
            return result
    if compiler is None:
        result.update(validation_status="Unsupported")
        result["diagnostics"].append({"code": "global_compiler_unavailable", "severity": "warning",
                                      "message": "Configure trusted Icarus and sibling vvp before global acceptance."})
        return result
    executable = compiler.get("executable")
    require(type(executable) is str and executable.replace("\\", "/").split("/")[-1].lower() in ("iverilog", "iverilog.exe"),
            "invalid_compiler", "Global verification uses only configured Icarus and sibling vvp.")
    parent = Path(compiler.get("working_directory") or tempfile.gettempdir()).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix="hullcirq-global-", dir=parent))
    top = folder / "candidate_top.v"; top.write_text(rtl, encoding="utf-8")
    tb = folder / "original_job_tb.v"; tb.write_text(plan["testbench"], encoding="utf-8")
    sources = [top]
    for entry in manifest["nodes"]:
        path = folder / (entry["node_id"] + ".v"); path.write_text(entry["rtl"], encoding="utf-8"); sources.append(path)
    output = folder / "hierarchy.vvp"
    fixed=fixed_global_commands(compiler,manifest,folder)
    commands = result["commands"]
    version = execute_fixed(fixed[0], parent, cancel_event, 10)
    commands.append(version); result["tool_version"] = version["stdout"] + version["stderr"]
    if version["status"] != "Completed" or version["exit_code"] != 0:
        return result
    compiled = execute_fixed(fixed[1], parent, cancel_event, 30)
    commands.append(compiled); result.update(executed=compiled["executed"], exit_code=compiled["exit_code"],
                                            stdout=compiled["stdout"], stderr=compiled["stderr"], artifacts_directory=str(folder))
    if compiled["status"] != "Completed" or compiled["exit_code"] != 0:
        result["diagnostics"].append({"code":"global_compile_failed","severity":"error",
            "message":compiled["stderr"] or compiled["stdout"] or "Fixed adopted-module compilation did not complete."})
        return result
    elaboration = output.read_text(encoding="utf-8", errors="replace")
    counts = {entry["node_id"]: len(re.findall(r'\.scope module,\s*"[^"]*"\s+"' +
              re.escape(entry["module_name"]) + r'"', elaboration)) for entry in manifest["nodes"]}
    result["elaborated_instance_counts"] = counts
    expected_counts = expected_instance_counts(manifest)
    result["checks"]["elaboration"] = {"validation_status": "Passed" if counts == expected_counts else "Failed", "instance_counts": counts,
        "scope": "actual_compiler_elaboration_module_counts_not_physical_instances"}
    if result["checks"]["elaboration"]["validation_status"] != "Passed":
        result["diagnostics"].append({"code": "global_instance_count", "severity": "error",
                                      "message": "Elaborate exactly the adopted module instances required by the saved design."})
        return result
    scope_lines=[line for line in elaboration.splitlines() if re.match(r'^S_\S+\s+\.scope ',line)]
    hierarchy=compiler_public_hierarchy(scope_lines,manifest)
    instrumented,monitor=instrument_public_testbench(plan,hierarchy)
    (folder/"instrumented_job_tb.v").write_text(instrumented,encoding="utf-8")
    result.update(public_port_hierarchy=hierarchy,hierarchy_scope_lines=scope_lines,
        hierarchy_scope_sha256=object_hash(scope_lines),public_monitor_source=monitor,
        public_monitor_sha256=content_hash(monitor),instrumented_testbench_sha256=content_hash(instrumented),
        public_boundary_vector_hash=plan["public_boundary_vector_hash"],
        instrumentation_origin="ordinary_program_from_frozen_original_job_and_actual_compiler_hierarchy_public_ports_only")
    instrumented_compile=execute_fixed(fixed[2],parent,cancel_event,30)
    commands.append(instrumented_compile)
    result.update(exit_code=instrumented_compile["exit_code"],stdout=result["stdout"]+instrumented_compile["stdout"],
                  stderr=result["stderr"]+instrumented_compile["stderr"])
    if instrumented_compile["status"]!="Completed" or instrumented_compile["exit_code"]!=0:
        result["diagnostics"].append({"code":"global_monitor_compile_failed","severity":"error",
            "message":instrumented_compile["stderr"] or instrumented_compile["stdout"] or "Trusted public-monitor compilation did not complete."})
        return result
    simulated = execute_fixed(fixed[3], parent, cancel_event, 30)
    commands.append(simulated)
    result.update(exit_code=simulated["exit_code"], executed=simulated["executed"],
                  stdout=result["stdout"] + simulated["stdout"], stderr=result["stderr"] + simulated["stderr"])
    runtime_pass, records, stream_records, pe_records = parse_runtime_records(simulated["stdout"], plan, simulated.get('stderr', ''))
    result["actual_output_transfers"] = records
    if plan.get('kind') == generic_global.KIND:
        result.update(verification_profile=generic_global.KIND, signal_sample_count=len(records),
                      expected_signal_samples=expected_output_count(plan))
    output_count = expected_output_count(plan)
    marker = f"HULLCIRQ_GLOBAL_PASS outputs={output_count} vector_hash={plan['vector_hash']}"
    public_marker=f"HULLCIRQ_PUBLIC_PASS vector_hash={plan['public_boundary_vector_hash']}"
    result["actual_public_stream_transfers"] = stream_records
    result["actual_pe_lane_transfers"] = pe_records
    passed = (simulated["status"] == "Completed" and simulated["exit_code"] == 0
              and runtime_pass)
    result["validation_status"] = "Passed" if passed else "Failed"
    result["checks"]["functional"] = {"validation_status": result["validation_status"], "executed": simulated["executed"],
                                     "expected_output_count": output_count, "actual_output_count": len(records)}
    result["checks"]["public_boundary"]={"validation_status":result["validation_status"],"executed":simulated["executed"],
        "scope":"exact_saved_external_cycle_output_samples_no_internal_coverage_claim" if plan.get('kind') == generic_global.KIND
                else "finite_original_job_public_transfer_values_routing_and_per_PE_participation_not_formal_equivalence"}
    if not passed:
        result["diagnostics"].extend({"code":"global_public_assertion","severity":"error","message":line}
            for line in simulated["stdout"].splitlines() if "HULLCIRQ_FAIL" in line)
        result["diagnostics"].append({"code": "global_behavior_mismatch", "severity": "error",
                                      "message": "The integrated RTL did not match every independently saved external cycle output assertion."
                                        if plan.get('kind') == generic_global.KIND else "The actual integrated RTL did not complete the original matrix job under saved backpressure."})
    return result


ALGORITHM = """Generate only the requested synthesizable Verilog-2005 top module.
Instantiate the six adopted modules using EXACT public port names. Use 16 instances of the PE module, one instance of each other type. clk/rst are shared synchronous active-high.
Wire external config_data/valid/ready to control. Expose control busy/job_done. Wire control schedule_config stream to scheduler and control post_config stream to post. Config K=[4:0], ReLU=[5], bias[i]=[6+32*i+:32]; post_config=config[133:5] (ReLU bit0, bias[i] bits[1+32*i+:32]).
Wire external load_data to buffer, gating BOTH load_data_valid and load_data_ready by !busy. load_data low8 byte, bits[13:8] address, bit14 bank A=0/B=1, bit15 reserved0.
Connect scheduler read_request to buffer and buffer read_response to scheduler with their valid/ready wires.
Scheduler pair_meta[3:0] is lane row*4+column, bit4 first, bit5 last. Route each accepted pair ONLY to that PE. Broadcast rst OR scheduler pe_clear to all PE rst; pe_clear occurs BEFORE first pair. Do not reset a PE on first metadata (that would discard its first product).
Serialize pair/result transactions: allow one PE pair handshake only while no prior PE output is pending. On pair handshake latch lane and last bit, then prevent another pair until that selected PE output transfers. Keep each PE input_valid zero unless selected and transaction allowed. Scheduler pair_data_ready must reflect selected PE ready and no pending output. Each PE emits a partial sum after EACH pair; intermediate sums must be consumed and discarded. For a latched last pair route that selected signed acc_data/valid to post acc_data, with PE ready driven by post ready. For non-last drive selected PE output ready=1 and discard its sum. Keep metadata until the matching PE output handshake completes. Nonselected PE output_ready=0.
Wire post result_data to FIFO and FIFO output_data to external output stream. Wire FIFO output_transfer public pulse to control output_transfer (the actual external output valid&&ready). Scheduler schedule_done is dispatch completion only; control waits for 16 FIFO final output transfers before pulsing job_done and clearing busy. Do not use schedule_done as top job_done.
No numerical matrix/bias constants: receive all values through external loading/configuration. No alternate behavioral implementation of adopted modules. No system tasks/functions, initial blocks, includes, macros or extra modules. Literal fixed-width ports. Named connections; Verilog-2005 genvar/generate or direct PE instances are allowed."""

NPU2_ALGORITHM = """Generate only the requested synthesizable Verilog-2005 top module.
Instantiate exactly one instance of every adopted graph module: control, buffer, scheduler, dispatcher, the four distinct PE modules, collector, post and FIFO. Use the exact public port names and shared clk/rst. Do not add modules or reimplement any adopted behavior.
Wire external config_data/valid/ready directly to control and expose control busy/job_done. Wire control schedule_config to scheduler and post_config to post, preserving each data/valid/ready handshake.
Wire external load_data to buffer. Gate both the buffer load_data_valid input and the external load_data_ready output with !busy, so no load transfer can occur during a job.
Wire every saved valid_ready graph edge directly, including data, valid and reverse ready: scheduler read_index to buffer, buffer operands to scheduler, scheduler batch_data to dispatcher, dispatcher pair00/pair01/pair10/pair11 to the matching explicit PE, the four PE sum_data streams to matching collector inputs, collector acc_data to post, and post result_data to FIFO.
Wire FIFO output_data/valid/ready directly to the external output stream. Wire FIFO output_transfer directly to control output_transfer. Every graph node receives the same synchronous active-high rst; there is no hidden PE array or pe_clear signal in this design.
No numerical matrix, operand, bias or expected-result constants. No alternate datapath, bypass or constant-output implementation. No system tasks/functions, initial blocks, includes, macros, parameters or extra modules. Use named connections and literal fixed-width Verilog-2005 declarations."""


NPU2_ARRAY_ALGORITHM = NPU2_ALGORITHM.replace(
    "Instantiate exactly one instance of every adopted graph module: control, buffer, scheduler, dispatcher, the four distinct PE modules, collector, post and FIFO.",
    "Instantiate control, buffer, scheduler, dispatcher, collector, post and FIFO once each. The ONE adopted scalar module hullcirq_npu2_pe must be instantiated exactly four times as pe00, pe01, pe10, pe11 for array indices [0,0], [0,1], [1,0], [1,1]. Do not duplicate its definition or implement a wrapper datapath."
).replace("matching explicit PE", "matching indexed scalar PE instance").replace(
    "there is no hidden PE array or pe_clear signal in this design.",
    "the declared 2x2 array is four named instances of the SAME adopted scalar PE definition. There is no pe_clear signal."
)


def prompt_template(design):
    if generic_global.handles(design):
        return PROMPT_TEMPLATE_V8 if 'external_io' in design else PROMPT_TEMPLATE_V6
    if npu2_array.is_array_design(design):
        return PROMPT_TEMPLATE_V5
    return PROMPT_TEMPLATE_V4 if _is_npu2_design(design) else PROMPT_TEMPLATE


def integration_projection(manifest, template_version=None):
    """Project exact public contracts; full source evidence remains in manifest.

    v1 retains the original editor-ID projection byte for byte. v2 resolves
    endpoints to module.port and factors repeated, verbatim language segments.
    Concatenating the indexed segments reconstructs every complete edge text.
    Unknown edge fields are retained because they may carry design semantics.
    """
    version = template_version or prompt_template(manifest["design"])
    require(version in PROMPT_PROJECTIONS, "global_prompt_version", "Unsupported global prompt projection version.")
    if version in (PROMPT_TEMPLATE_V6, PROMPT_TEMPLATE_V7, PROMPT_TEMPLATE_V8):
        design = manifest['design']
        generic_global.top_interface(design)
        projected = {'top': top_interface(design), 'settings': copy.deepcopy(design['settings']),
                'global_integration': copy.deepcopy(design['global_integration']),
                'design_intent': copy.deepcopy(design.get('design_intent')),
                'adopted_modules': [{'node_id': n['node_id'], 'interface': copy.deepcopy(n['public_interface']),
                    'instance_array': copy.deepcopy(next(node.get('instance_array') for node in design['nodes'] if node['id'] == n['node_id']))}
                    for n in manifest['nodes']], 'edges': copy.deepcopy(design['edges']),
                'required_instance_counts': generic_global.instance_counts(manifest),
                'verification_scope': 'Independent saved finite cycle vectors are withheld from generation; implement the saved behavior.'}
        if version in (PROMPT_TEMPLATE_V7, PROMPT_TEMPLATE_V8):
            from .external_io import bindings
            require('external_io' in design, 'external_io_required', 'The external-I/O prompt requires an explicit saved boundary.')
            projected['external_connections'] = bindings(design)
            projected['required_direct_instances'] = generic_global.external_instances(design)
        return projected
    def declaration(interface):
        ports = [p["direction"] + (" signed" if p["signed"] else "") +
                 (f" [{p['width']-1}:0]" if p["width"] > 1 else "") + " " + p["name"] for p in interface["ports"]]
        return "module " + interface["module_name"] + "(" + ",".join(ports) + ");"
    modules = [declaration(n["public_interface"]) for n in manifest["nodes"]]
    projected = {"top": declaration(top_interface(manifest["design"])), "adopted_modules": modules}
    if version == PROMPT_TEMPLATE_V1:
        projected["edges"] = copy.deepcopy(manifest["design"]["edges"])
        return projected
    nodes = {n["id"]: n for n in manifest["design"]["nodes"]}
    language, indices, edges = [], {}, []
    def endpoint(reference):
        node = nodes[reference["node_id"]]
        port = next(p for p in node["ports"] if p["id"] == reference["port_id"])
        member = reference.get("instance_index") if version == PROMPT_TEMPLATE_V5 else None
        suffix = f"[{member[0]},{member[1]}]" if member is not None else ""
        return node["module_name"] + suffix + "." + port["name"]
    for edge in manifest["design"]["edges"]:
        parts = []
        for text in re.split(r"(?<=[.!?])(?=\s|$)", edge["behavior"]):
            if not text:
                continue
            if text not in indices:
                indices[text] = len(language); language.append(text)
            parts.append(indices[text])
        fields = {k: copy.deepcopy(v) for k, v in edge.items()
                  if k not in ("id", "source", "target", "protocol", "behavior")}
        for side in ("source", "target"):
            extra = {k: copy.deepcopy(v) for k, v in edge[side].items() if k not in ("node_id", "port_id")}
            if extra:
                fields[side] = extra
        row = [endpoint(edge["source"]), endpoint(edge["target"]), edge["protocol"], parts]
        if fields:
            row.append(fields)
        edges.append(row)
    projected.update(edge_columns=["source", "target", "protocol", "language_parts", "optional_fields"],
                     edge_language=language, edges=edges)
    if version in (PROMPT_TEMPLATE_V3, PROMPT_TEMPLATE_V4, PROMPT_TEMPLATE_V5):
        projected.update(settings=copy.deepcopy(manifest["design"].get("settings")),
                         global_integration=copy.deepcopy(manifest["design"].get("global_integration")),
                         design_intent=copy.deepcopy(manifest["design"].get("design_intent")))
    if version == PROMPT_TEMPLATE_V5:
        npu2_array.recognize_design(manifest["design"])
        projected["instance_arrays"] = [{"node_id": node["id"], "module_name": node["module_name"],
            **copy.deepcopy(node["instance_array"]), "instance_names": ["pe00", "pe01", "pe10", "pe11"]}
            for node in manifest["design"]["nodes"] if "instance_array" in node]
    return projected


def integration_messages(manifest, instruction, base=None, template_version=None):
    version = template_version or prompt_template(manifest["design"])
    user = json.dumps(integration_projection(manifest, version), separators=(",", ":"), ensure_ascii=False)
    if version in (PROMPT_TEMPLATE_V6, PROMPT_TEMPLATE_V7, PROMPT_TEMPLATE_V8):
        user += ('\nGenerate only the declared synthesizable Verilog-2005 top. Instantiate exactly the saved adopted scalar '
                 'module definitions and graph-declared counts/array elements. Wire exact public ports using the saved '
                 'edges and complete integration behavior. Respect the declared clock/reset names, polarity and period. '
                 'Do not reproduce module bodies, invent expected outputs, or substitute a built-in circuit algorithm.')
        if version in (PROMPT_TEMPLATE_V7, PROMPT_TEMPLATE_V8):
            user += ('\nUse exactly the instance_name and module_name in required_direct_instances for each node/member. '
                     'Use direct named pin connections for EVERY adopted physical pin, including matching clock/reset. '
                     'external_connections is the authoritative physical top-to-node mapping; direction is the top pin direction. '
                     'Connect each listed node_pin to its exact external_name on that member, including reverse ready. '
                     'Only direct scalar named instances, plain literal-width wire declarations and assign identifier = identifier aliases '
                     'are supported in this top. Use each listed array member as its own direct named instance, no generate blocks. '
                     'No parameters, behavioral logic, constants, expressions, casts, slicing, concatenation, extra fanout or protocol conversion. '
                     'Declare all intermediate nets with the exact width and signedness of their connected pins.')
        if version == PROMPT_TEMPLATE_V8:
            user += ('\nInside the Verilog fence the first non-whitespace token must be module and the last token must be endmodule. '
                     'Do not emit any Verilog preprocessor directive, backtick directive, macro invocation or include. '
                     'In particular, do not emit `timescale, `include, `define or any other backtick construct. '
                     'The trusted testbench owns simulation timing; preserve the saved design clock period without adding a timescale directive.')
        if base:
            user += '\nPrevious top:\n' + base['rtl'] + '\nRecorded diagnostics:\n' + json.dumps(base['diagnostics'], ensure_ascii=False)
        if instruction:
            user += '\nDevelopment-assistant/user correction (final instruction): ' + instruction
        system = 'Return one synthesizable Verilog-2005 top in a verilog fence. Only instantiate/wire the adopted saved modules; preserve their exact interfaces and behavior.'
        if version == PROMPT_TEMPLATE_V8:
            system += (' The fenced code must start with module and end with endmodule. '
                       'Do not emit Verilog preprocessor directives, backtick directives, macros or includes, including `timescale, `include and `define.')
        return [{'role': 'system', 'content': system},
                {'role': 'user', 'content': user}]
    if version in (PROMPT_TEMPLATE_V2, PROMPT_TEMPLATE_V3, PROMPT_TEMPLATE_V4, PROMPT_TEMPLATE_V5):
        user += "\nEdge endpoints are module.port. Concatenate indexed edge_language parts verbatim; retain optional_fields."
    user += "\n" + (NPU2_ARRAY_ALGORITHM if version == PROMPT_TEMPLATE_V5 else NPU2_ALGORITHM if version in (PROMPT_TEMPLATE_V3, PROMPT_TEMPLATE_V4) else ALGORITHM)
    # V3 must remain byte-for-byte reconstructable for retained jobs. V4 puts
    # the exact repair correction after the complete prior candidate/evidence,
    # where it is the highest-recency content seen by the model.
    if version not in (PROMPT_TEMPLATE_V4, PROMPT_TEMPLATE_V5) and instruction:
        user += "\nDevelopment-assistant/user correction: " + instruction
    if base:
        user += "\nPrevious top:\n" + base["rtl"] + "\nRecorded diagnostics:\n" + json.dumps(base["diagnostics"], ensure_ascii=False)
    if version in (PROMPT_TEMPLATE_V4, PROMPT_TEMPLATE_V5) and instruction:
        user += "\nDevelopment-assistant/user correction (final instruction): " + instruction
    system = "Return exactly one synthesizable Verilog-2005 top module in a verilog code fence. Instantiation and wiring only; retain the adopted module interfaces and behavior."
    if version in (PROMPT_TEMPLATE_V2, PROMPT_TEMPLATE_V3, PROMPT_TEMPLATE_V4, PROMPT_TEMPLATE_V5):
        system = "Return one synthesizable Verilog-2005 top in a verilog fence. Only instantiate/wire adopted modules; preserve interfaces and behavior."
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]


class GlobalGenerationManager(ObservedState):
    """Separate atomic S08 history, frozen source lineage and revocable adoption."""
    def __init__(self, store, generation, workflow, specifications, compiler=None):
        self.store, self.generation, self.workflow, self.specifications = store, generation, workflow, specifications
        self.compiler = compiler; self.path = store.state_path.parent / "global_generation.json"
        self.lock = threading.RLock(); self._worker = None; self._cancel = threading.Event(); self._closed = False
        self._storage_error = None; self._checkpoint = time.monotonic(); self._pending = 0
        self._previews = {}
        self._manifest_cache = None
        self._manifest_stamp = None
        self._state = {"global_generation_store_version": "0.1", "jobs": [], "reviews": [],
                       "source_key": None, "source_epoch": 0, "source_transitions": []}
        if _io_path(self.path).exists():
            try:
                self._state = strict_loads(_io_path(self.path).read_text(encoding="utf-8")); self._validate_saved()
            except (DomainError, OSError, ValueError, KeyError, TypeError) as error:
                raise DomainError("global_history_invalid", "Global generation history is inconsistent; original file preserved.", 500) from error
        self._committed = copy.deepcopy(self._state)
        for job in self._state["jobs"]:
            if job["execution_status"] in ACTIVE:
                job.update(execution_status="Interrupted", validation_status="Not Checked", finished_at=utc_now(),
                           error={"code": "service_restarted", "message": "Interrupted global generation is retained; no request was resent."})
                self._persist()

    def source_manifest(self):
        current = self.store.envelope(); design = current["design"]
        node_ids = required_node_ids(design)
        original_job(design); top_interface(design)
        require(all(s["validation_status"] == "Passed" and s["review_status"] == "Accepted" and s["freshness"] == "Current"
                    for s in current["workflow"] if s["id"] in IMPLEMENTED_STAGES),
                "global_input_prerequisite", "Adopt all current saved GUI input checks first.")
        # Avoid repeatedly decorating large histories while most nodes are
        # still missing. This is only an early refusal; final eligibility below
        # remains authoritative and includes each source manager's live guards.
        latest_raw = {spec["node_id"]: spec for spec in self.specifications._state["specs"]}
        require(set(latest_raw) == set(node_ids) and all(s["review_status"] == "Accepted" for s in latest_raw.values()),
                "global_spec_prerequisite", "All latest required node specifications must be Passed, Accepted and Current before S08.")
        # Inspect selected raw records under the existing source-manager lock
        # order. Their full histories can be tens of megabytes; copying all of
        # them once per node/poll would stall the model receiver.
        with self.specifications.lock, self.workflow.lock, self.generation.lock, self.store.lock:
            self.generation.observe_design()
            self.workflow.observe_design()
            self.specifications.observe_design()
            # A source edit can occur between the cheap early refusal and
            # acquiring these locks. Capture all authoritative inputs again.
            current = self.store.envelope(); design = current["design"]
            node_ids = required_node_ids(design)
            original_job(design); top_interface(design)
            require(all(s["validation_status"] == "Passed" and s["review_status"] == "Accepted"
                            and s["freshness"] == "Current" for s in current["workflow"] if s["id"] in IMPLEMENTED_STAGES),
                    "global_input_prerequisite", "Adopt all current saved GUI input checks first.")
            latest_raw = {spec["node_id"]: spec for spec in self.specifications._state["specs"]}
            require(set(latest_raw) == set(node_ids) and all(s["review_status"] == "Accepted" for s in latest_raw.values()),
                    "global_spec_prerequisite", "All latest required node specifications must remain adopted.")
            return self._source_manifest_locked(current, design, latest_raw, node_ids)

    def _source_manifest_locked(self, current, design, latest_raw, node_ids):
        latest_jobs = {j["node_id"]: j for j in self.generation._state["jobs"]}
        latest_runs = {(r["node_id"], r["stage_id"]): r for r in self.workflow._state["runs"]}
        source_revisions = set()
        for node_id in node_ids:
            spec = latest_raw[node_id]
            source_records = (spec, self.generation._stored_job(spec["candidate_id"]),
                self.workflow._run(spec["specification"]["lineage"]["synthesis_run_id"]),
                self.workflow._run(spec["source_run_id"]))
            source_revisions.update(r["revision_id"] for r in source_records)
        require(len(source_revisions) == 1, "global_revision_conflict",
                "All required sources must retain one exact original GUI revision; inspect mixed source revisions.")
        source_revision_id = next(iter(source_revisions))
        # Always resolve and compare the retained snapshot, including on the
        # display-plan cache path. Never relabel old evidence as a new revision.
        source_design = same_source_design(self.store, source_revision_id, current)
        def stamp_record(record):
            return [record.get(k) for k in ("id", "execution_status", "validation_status", "review_status",
                "acceptance_epoch", "record_hash", "rtl_sha256", "verification_plan_sha256", "revision_id", "input_hash",
                "design_hash", "candidate_id", "source_run_id", "prior_run_id")]
        stamp = object_hash({"revision": current["revision"]["id"], "design": design,
            "source_revision": source_revision_id, "source_design": source_design,
            "specs": {k:stamp_record(v) for k,v in latest_raw.items()},
            "jobs": {k:stamp_record(v) for k,v in latest_jobs.items()},
            "runs": {str(k):stamp_record(v) for k,v in latest_runs.items()},
            "generation_epochs": self.generation._state["node_epochs"], "workflow_epochs": self.workflow._state["node_epochs"],
            "spec_epochs": self.specifications._state["node_epochs"],
            "reviews": [manager._state["reviews"] for manager in
                        (self.generation, self.workflow, self.specifications)]})
        if stamp == self._manifest_stamp:
            return copy.deepcopy(self._manifest_cache)
        entries = []
        for node_id in node_ids:
            node = next(n for n in design["nodes"] if n["id"] == node_id)
            spec = latest_raw[node_id]
            candidate = self.generation._stored_job(spec["candidate_id"])
            lineage = spec["specification"]["lineage"]
            synthesis = self.workflow._run(lineage["synthesis_run_id"]); netlist = self.workflow._run(spec["source_run_id"])
            require(all(r["execution_status"] == "Completed" and r["validation_status"] == "Passed"
                        and r["review_status"] == "Accepted"
                        for r in (spec, candidate, synthesis, netlist)), "global_source_not_adopted",
                    "Every source candidate, synthesis, netlist result and specification must remain current and adopted.")
            require(latest_jobs.get(node_id, {}).get("id") == candidate["id"]
                    and latest_runs.get((node_id, "local_synthesis"), {}).get("id") == synthesis["id"]
                    and latest_runs.get((node_id, "local_netlist_simulation"), {}).get("id") == netlist["id"]
                    and all(r["input_hash"] == node_fingerprint(design, node_id) for r in (spec, candidate, synthesis, netlist))
                    and candidate.get("acceptance_epoch") == self.generation._state["node_epochs"].get(node_id)
                    and all(r.get("acceptance_epoch") == self.workflow._state["node_epochs"].get(node_id) for r in (synthesis, netlist))
                    and spec.get("acceptance_epoch") == self.specifications._state["node_epochs"].get(node_id)
                    and spec["design_hash"] == current["revision"]["semantic_hash"]
                    and synthesis["candidate_id"] == netlist["candidate_id"] == candidate["id"]
                    and netlist["prior_run_id"] == synthesis["id"],
                    "global_source_stale", "Use the latest source records at their current authoritative input/adoption epochs.")
            adoptions = []
            for kind, record, manager, field in (("candidate", candidate, self.generation, "job_id"),
                    ("synthesis", synthesis, self.workflow, "run_id"), ("netlist_simulation", netlist, self.workflow, "run_id")):
                source_reviews = [r for r in manager._state["reviews"] if r[field] == record["id"]]
                require(source_reviews and source_reviews[-1]["decision"] == "accepted", "global_adoption_missing",
                        "All source results need their latest authoritative adoption.")
                adoptions.append({"kind": kind, "review": source_reviews[-1]})
            require(object_hash(spec["source_adoptions"]) == object_hash(adoptions),
                    "global_source_adoption_changed", "S07 source adoption changed; derive it again before global generation.")
            revisions = {r["revision_id"] for r in (spec, candidate, synthesis, netlist)}
            require(revisions == {source_revision_id},
                    "global_revision_conflict", "All required sources must retain one exact original GUI revision; inspect mixed source revisions.")
            require(object_hash(spec["specification"]["original_requirements"]["verification_jobs"]) == object_hash(
                        design.get("verification_jobs", []) if generic_global.handles(design) else design["verification_jobs"]),
                    "global_job_conflict", "Every adopted specification must preserve the same original canonical matrix job, including numeric types.")
            reviews = [r for r in self.specifications._state["reviews"] if r["spec_id"] == spec["id"]]
            require(reviews and reviews[-1]["decision"] == "accepted", "global_adoption_missing", "Keep the authoritative S07 adoption.")
            entries.append({"node_id": node_id, "module_name": node["module_name"], "revision_id": candidate["revision_id"],
                "candidate_id": candidate["id"], "synthesis_run_id": synthesis["id"], "netlist_run_id": netlist["id"], "spec_id": spec["id"],
                "rtl": candidate["rtl"], "rtl_sha256": candidate["rtl_sha256"], "specification": spec["specification"],
                "specification_sha256": spec["specification_sha256"], "public_interface": physical_interface(design, node),
                "candidate_execution_hash": execution_evidence_hash(self.generation._stored_job(candidate["id"])),
                "netlist_execution_hash": execution_evidence_hash(self.workflow._run(netlist["id"])),
                "S07_adoption": copy.deepcopy(reviews[-1])})
        manifest = {"version": 1, "revision_id": source_revision_id, "design": copy.deepcopy(source_design),
                "design_sha256": object_hash(source_design), "canonical_job_hash": canonical_job_hash(source_design),
                "nodes": entries, "integration_artifacts": "adopted_source_rtl_and_exact_public_boundary_ports",
                "internal_nets_used_as_API": False}
        self._manifest_stamp = stamp
        self._manifest_cache = copy.deepcopy(manifest)
        return copy.deepcopy(manifest)

    def _source_state(self):
        try:
            manifest = self.source_manifest()
            return object_hash(manifest), manifest, None
        except DomainError as error:
            current = self.store.envelope()
            key = object_hash({"revision_id": current["revision"]["id"], "design": current["design"], "blocked": error.code})
            return key, None, {"code": error.code, "message": error.message}

    def observe_design(self):
        key, manifest, error = self._source_state()
        with self.lock:
            if key != self._state["source_key"]:
                self._state["source_key"] = key; self._state["source_epoch"] += 1
                self._state["source_transitions"].append({"epoch": self._state["source_epoch"], "source_key": key, "created_at": utc_now()})
                if _io_path(self.path).exists(): persist_observation(self)
        return key, manifest, error

    def _job(self, identifier):
        job = next((j for j in self._state["jobs"] if j["id"] == identifier), None)
        require(job is not None, "global_job_not_found", "Global generation job does not exist.", 404)
        return job

    def _decorate(self, job):
        value = copy.deepcopy(job); current = job["source_key"] == self._state["source_key"]
        value["freshness"] = "Current" if current else "Stale"
        if value["review_status"] == "Accepted" and (not current or job.get("acceptance_epoch") != self._state["source_epoch"]):
            value["review_status"] = "Awaiting Review"
        value["artifacts"] = [{"kind": "global_generation_job", "url": "/api/global-generation/jobs/" + job["id"]}]
        return value

    def envelope(self):
        _, manifest, error = self.observe_design()
        try:
            required_count = len(required_node_ids(self.store.envelope()["design"]))
        except DomainError:
            required_count = len(self.store.envelope()["design"].get("nodes", []))
        with self.lock:
            jobs = [self._decorate(j) for j in self._state["jobs"]]
            return {"global_generation": {"implemented": True, "jobs": jobs, "reviews": copy.deepcopy(self._state["reviews"]),
                    "execution_submissions": submission_view(self), "submission_protocol_version": PROTOCOL_VERSION,
                    "ready": manifest is not None, "blocked_reason": error["message"] if error else None,
                    "blocked_code": error["code"] if error else None,
                    "required_node_count": required_count, "latest_job_id": jobs[-1]["id"] if jobs else None,
                    "storage_error": copy.deepcopy(self._storage_error)}}

    def job(self, identifier):
        self.observe_design()
        with self.lock: return self._decorate(self._job(identifier))

    def preview(self, revision_id, operation="generate", base_job_id=None, instruction=""):
        require(all(type(x) is str for x in (revision_id, operation, instruction)) and len(instruction.encode("utf-8")) <= 32768,
                "invalid_global_request", "Provide current revision and text instructions.")
        require(operation in ("generate", "repair"), "invalid_global_operation", "Use generate or repair.")
        key, manifest, error = self.observe_design()
        require(manifest is not None, error["code"] if error else "global_source_missing", error["message"] if error else "No adopted sources.")
        require(revision_id == self.store.envelope()["revision"]["id"], "revision_conflict", "Preview the current saved revision.")
        with self.generation.lock:
            profile = copy.deepcopy(self.generation._require_profile())
        require(profile["profile"]["execution_location"] == "Local", "global_local_required",
                "This first global demonstration uses the saved Local provider profile; no network fallback occurs.")
        base = None
        if operation == "repair":
            base = self._job(base_job_id)
            require(base["rtl"] and instruction.strip(), "global_repair_required", "Repair needs an existing global RTL and explicit feedback.")
        else:
            require(base_job_id is None, "invalid_global_request", "A base job applies only to repair.")
        template_version = prompt_template(manifest["design"])
        messages = integration_messages(manifest, instruction, base, template_version)
        p = profile["profile"]
        parameters = {"temperature": p["temperature"], "seed": p["seed"], "max_tokens": p["max_output_tokens"]}
        if p.get("reasoning_effort") is not None: parameters["reasoning_effort"] = p["reasoning_effort"]
        estimate = len(json.dumps(messages, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        require(estimate + p["max_output_tokens"] <= p["context_window"], "global_context_budget",
                "The complete compact integration prompt plus output budget exceeds the profile context; nothing was truncated.", 422)
        context = {"template_version": template_version, "revision_id": manifest["revision_id"],
                   "requested_revision_id": revision_id, "source_key": key, "source_manifest": manifest,
                   "interface": top_interface(manifest["design"]), "messages": messages, "parameters": parameters,
                   "profile_revision_id": profile["revision_id"], "operation": operation, "base_job_id": base_job_id,
                   "instruction": instruction, "estimated_input_tokens": estimate, "token_estimate_method": "conservative_one_UTF8_byte_per_token",
                   "prompt_projection": PROMPT_PROJECTIONS[template_version],
                   "tool_configuration": copy.deepcopy(self.compiler),
                   "verification_plan": build_global_plan(manifest["design"])}
        if template_version in (PROMPT_TEMPLATE_V2, PROMPT_TEMPLATE_V3, PROMPT_TEMPLATE_V4, PROMPT_TEMPLATE_V5, PROMPT_TEMPLATE_V6, PROMPT_TEMPLATE_V7, PROMPT_TEMPLATE_V8):
            context["prompt_projection_sha256"] = object_hash(integration_projection(manifest, template_version))
        context["context_id"] = object_hash(context)
        with self.lock:
            self._previews[context["context_id"]] = copy.deepcopy(context)
            while len(self._previews) > 8: del self._previews[next(iter(self._previews))]
        return context

    def preview_artifact(self, identifier):
        with self.lock:
            require(identifier in self._previews, "global_preview_not_found", "Preview again; this in-memory global context is unavailable.", 404)
            return copy.deepcopy(self._previews[identifier])

    def start(self, revision_id, context_id, profile_revision_id, operation="generate", base_job_id=None, instruction="", *, _submission=None):
        context = self.preview(revision_id, operation, base_job_id, instruction)
        with self.lock, self.specifications.lock, self.workflow.lock, self.generation.lock, self.store.lock:
            self.observe_design()
            require(revision_id == self.store.envelope()["revision"]["id"]
                    and context.get("requested_revision_id") == revision_id,
                    "revision_conflict", "The saved revision changed; preview the current request again.")
            require(not self._closed and not self.is_active(), "global_generation_busy", "One global worker is already active or stopping.")
            require(not any(j["execution_status"] in ACTIVE for j in self.generation._state["jobs"]),
                    "generation_busy", "Finish or cancel the local node model request before global generation.")
            require(context["context_id"] == context_id and context["source_key"] == self._state["source_key"],
                    "global_context_conflict", "Sources changed; preview the global context again.")
            profile = self.generation._require_profile(profile_revision_id)
            require(context["profile_revision_id"] == profile_revision_id, "profile_conflict", "Preview the current provider profile.")
            require(len(self._state["jobs"]) < 64, "history_limit", "Archive reviewed global evidence before adding more than 64 attempts.")
            job = {"id": new_id("global-generation"), "stage_id": STAGE, "revision_id": context["revision_id"],
                   "requested_revision_id": revision_id,
                   "source_key": context["source_key"], "context": context, "context_id": context_id,
                   "profile": copy.deepcopy(profile["profile"]), "profile_revision_id": profile_revision_id,
                   "parameters": context["parameters"], "operation": operation, "base_job_id": base_job_id, "instruction": instruction,
                   "origin": "local_llm", "execution_status": "Queued", "validation_status": "Not Checked",
                   "review_status": "Awaiting Review", "raw_content": "", "raw_reasoning": "", "rtl": None,
                   "events": [], "checks": {}, "diagnostics": [], "error": None, "diff": "", "usage": None,
                   "finish_reason": None, "provider_request_id": None, "created_at": utc_now(), "finished_at": None}
            if _submission is not None:
                job["submission_id"] = _submission.submission_id
                _submission.bind(job["id"])
            self._state["jobs"].append(job); self._persist(); self._cancel = threading.Event()
            self._worker = threading.Thread(target=self._execute, args=(job["id"], self._cancel), daemon=True, name="HuLLCirq-global-generation")
            self._worker.start()
        return self.envelope()

    def is_active(self):
        return any(j["execution_status"] in ACTIVE for j in self._state["jobs"]) or bool(self._worker and self._worker.is_alive())

    def _event(self, job, event):
        job["events"].append({**copy.deepcopy(event), "sequence": len(job["events"]) + 1, "created_at": utc_now()})
        if event.get("type") in ("delta", "content", "partial_answer", "reasoning") and type(event.get("content")) is str:
            field = "raw_reasoning" if event["type"] == "reasoning" else "raw_content"
            job[field] += event["content"]; self._pending += len(event["content"].encode("utf-8"))
            if self._pending >= 8192 or time.monotonic() - self._checkpoint >= 0.5: self._persist()
        else: self._persist()

    def _execute(self, identifier, cancel):
        try:
            with self.lock:
                job = self._job(identifier); job["execution_status"] = "Running"; self._event(job, {"type": "started"})
                frozen = copy.deepcopy(job)
            def on_event(event):
                with self.lock: self._event(self._job(identifier), event)
            answer = ChatCompletionsClient(frozen["profile"]).generate(frozen["context"]["messages"], frozen["parameters"], cancel, on_event)
            with self.lock:
                job = self._job(identifier)
                for key in ("raw_content", "raw_reasoning", "usage", "finish_reason", "provider_request_id", "error"):
                    if key in answer: job[key] = answer[key]
                status = answer.get("execution_status", "Failed")
                if status not in TERMINAL: status = "Failed"
                raw = job["raw_content"]
            if status == "Completed" and not cancel.is_set():
                extracted = extract_rtl(raw); rtl = extracted.get("rtl")
                check = check_global_rtl(rtl, frozen["context"]["source_manifest"], frozen["context"]["verification_plan"], frozen["context"]["tool_configuration"], cancel) if rtl else {
                    "validation_status": "Failed", "checks": {}, "diagnostics": extracted.get("diagnostics", [])}
                with self.lock:
                    job = self._job(identifier); job.update(rtl=rtl, checks=check, diagnostics=extracted.get("diagnostics", []) + check.get("diagnostics", []),
                        validation_status=check["validation_status"])
                    previous = self._job(frozen["base_job_id"])["rtl"] if frozen["base_job_id"] else ""
                    job["diff"] = compare_rtl(previous or "", rtl or "")
            with self.lock, self.specifications.lock, self.workflow.lock, self.generation.lock, self.store.lock:
                self.observe_design(); job = self._job(identifier)
                job.update(execution_status="Cancelled" if cancel.is_set() else status, finished_at=utc_now())
                if cancel.is_set(): job["validation_status"] = "Not Checked"
                policy = self.store.review_policy()
                if (job["execution_status"] == "Completed" and job["validation_status"] == "Passed" and self._passed(job)
                        and job["source_key"] == self._state["source_key"] and policy["mode"] == "accept_on_pass" and policy["user_authorized"]):
                    self._record_review(job, "accepted", "Accepted after the original whole-matrix job and adopted-module compilation passed under the saved user policy.",
                                        None, "automation_policy", self.store.policy_provenance())
                self._event(job, {"type": "finished", "execution_status": job["execution_status"], "validation_status": job["validation_status"]})
        except Exception as error:
            with self.lock:
                job = self._job(identifier); job.update(execution_status="Cancelled" if cancel.is_set() else "Failed",
                    validation_status="Not Checked", finished_at=utc_now(),
                    error={"code": getattr(error, "code", "global_generation_error"), "message": getattr(error, "message", "Global generation/check failed; partial evidence retained.")})
                try: self._event(job, {"type": "error", "code": job["error"]["code"]})
                except OSError: pass

    def cancel(self, identifier):
        with self.lock:
            require(self._job(identifier)["execution_status"] in ACTIVE, "global_job_not_active", "Only an active global job can be cancelled.")
            self._cancel.set(); self._event(self._job(identifier), {"type": "cancel_requested", "server_inference_stop": "Not guaranteed"})
        return self.envelope()

    def _record_review(self, job, decision, note, target, actor, provenance=None):
        job["review_status"] = "Accepted" if decision == "accepted" else "Changes Requested"
        if decision == "accepted": job["acceptance_epoch"] = self._state["source_epoch"]
        record = {"id": new_id("global-review"), "job_id": job["id"], "decision": decision, "note": note,
                  "target_stage": target, "actor": actor, "created_at": utc_now(), "source_key": job["source_key"],
                  "acceptance_epoch": job.get("acceptance_epoch"), "reviewed_revision_id": self.store.envelope()["revision"]["id"]}
        if provenance: record["provenance"] = provenance
        self._state["reviews"].append(record)

    def review(self, identifier, decision, note, target_stage=None, *, operator=None):
        fields = manual_review_fields(operator)
        require(decision in ("accepted", "changes_requested", "return_to_stage") and type(note) is str,
                "invalid_global_review", "Provide a supported decision and feedback text.")
        require(decision == "accepted" or note.strip(), "feedback_required", "Record the requested correction or return.")
        require(target_stage in (*IMPLEMENTED_STAGES, "local_rtl_generation", "local_synthesis", "local_netlist_simulation", "node_implementation_specs")
                if decision == "return_to_stage" else target_stage is None, "invalid_return_stage", "Return only to an implemented earlier stage.")
        with self.lock, self.specifications.lock, self.workflow.lock, self.generation.lock, self.store.lock:
            self.observe_design(); job = self._job(identifier)
            require(job["execution_status"] not in ACTIVE and self._state["jobs"][-1]["id"] == identifier,
                    "global_job_superseded", "Review the latest completed global candidate.")
            if decision == "accepted":
                require(job["source_key"] == self._state["source_key"], "stale_global_job", "Use current adopted node sources.")
                require(job["execution_status"] == "Completed" and job["validation_status"] == "Passed" and self._passed(job),
                        "global_unverified", "The exact adopted modules and full original matrix job must pass before acceptance.")
            self._record_review(job, decision, note, target_stage, fields["actor"], fields["provenance"]); self._persist()
        return self.envelope()

    @staticmethod
    def _passed(job):
        proof = job.get("checks", {}); plan = job["context"]["verification_plan"]
        if plan.get('kind') == generic_global.KIND:
            return generic_global.passed_s08(job)
        output_count = expected_output_count(plan)
        marker = f"HULLCIRQ_GLOBAL_PASS outputs={output_count} vector_hash={plan['vector_hash']}"
        commands = proof.get("commands", [])
        runtime = commands[-1].get("stdout", "") if type(commands) is list and commands else ""
        try:
            runtime_pass, observed, stream_records, pe_records = parse_runtime_records(runtime, plan)
            expected_commands = fixed_global_commands(job["context"]["tool_configuration"], job["context"]["source_manifest"], proof["artifacts_directory"])
            hierarchy=compiler_public_hierarchy(proof["hierarchy_scope_lines"],job["context"]["source_manifest"])
            instrumented,monitor=instrument_public_testbench(plan,hierarchy)
        except (DomainError, KeyError, TypeError, ValueError):
            return False
        public_marker=f"HULLCIRQ_PUBLIC_PASS vector_hash={plan['public_boundary_vector_hash']}"
        return (proof.get("validation_status") == "Passed" and proof.get("executed") is True
                and runtime_pass
                and object_hash(proof.get("tool_configuration")) == object_hash(job["context"]["tool_configuration"])
                and object_hash([c.get("command") for c in commands]) == object_hash(expected_commands)
                and type(proof.get("exit_code")) is int and proof["exit_code"] == 0
                and proof.get("rtl_sha256") == content_hash(job["rtl"])
                and proof.get("source_manifest_sha256") == object_hash(job["context"]["source_manifest"])
                and proof.get("vector_hash") == plan["vector_hash"] and proof.get("testbench_sha256") == plan["testbench_sha256"]
                and proof.get("checks", {}).get("interface", {}).get("validation_status") == "Passed"
                and proof.get("checks", {}).get("elaboration", {}).get("validation_status") == "Passed"
                and proof.get("checks", {}).get("functional", {}).get("validation_status") == "Passed"
                and proof.get("checks", {}).get("public_boundary", {}).get("validation_status") == "Passed"
                and proof.get("hierarchy_scope_sha256")==object_hash(proof["hierarchy_scope_lines"])
                and object_hash(proof.get("public_port_hierarchy"))==object_hash(hierarchy)
                and proof.get("public_monitor_source")==monitor and proof.get("public_monitor_sha256")==content_hash(monitor)
                and proof.get("instrumented_testbench_sha256")==content_hash(instrumented)
                and proof.get("public_boundary_vector_hash")==plan["public_boundary_vector_hash"]
                and runtime.splitlines().count(public_marker)==1
                and object_hash(stream_records)==object_hash(proof.get("actual_public_stream_transfers"))
                and object_hash(stream_records)==object_hash([{"stream":name,"transfers":count} for name,count in public_transfer_counts(plan).items()])
                and object_hash(pe_records)==object_hash(proof.get("actual_pe_lane_transfers"))
                and pe_records_match_plan(plan, pe_records)
                and object_hash(proof.get("elaborated_instance_counts")) == object_hash(expected_instance_counts(job["context"]["source_manifest"]))
                and [x.get("index") for x in proof.get("actual_output_transfers", [])] == list(range(output_count))
                and [x.get("value") for x in proof.get("actual_output_transfers", [])] == plan["recipe"]["expected_outputs"]
                and all(type(x.get(k)) is int for x in proof.get("actual_output_transfers", []) for k in ("index", "value", "cycle"))
                and proof.get("stdout", "").splitlines().count(marker) == 1 and "HULLCIRQ_FAIL" not in proof.get("stdout", "")
                and runtime.splitlines().count(marker) == 1 and "HULLCIRQ_FAIL" not in runtime
                and object_hash(observed) == object_hash(proof.get("actual_output_transfers"))
                and all(x["cycle"] > 0 and (i == 0 or x["cycle"] > observed[i-1]["cycle"]) for i,x in enumerate(observed))
                and len(proof.get("commands", [])) == 4 and all(c.get("executed") is True and c.get("status") == "Completed"
                    and type(c.get("exit_code")) is int and c["exit_code"] == 0 for c in proof["commands"]))

    def _validate_saved(self):
        s = self._state
        require(type(s) is dict and s.get("global_generation_store_version") == "0.1" and type(s.get("jobs")) is list
                and type(s.get("reviews")) is list and type(s.get("source_epoch")) is int and s["source_epoch"] >= 0
                and type(s.get("source_transitions")) is list, "invalid_global_history", "Invalid global history containers.")
        require([t["epoch"] for t in s["source_transitions"]] == list(range(1, s["source_epoch"] + 1))
                and (s["source_transitions"][-1]["source_key"] if s["source_transitions"] else None) == s["source_key"],
                "invalid_global_epochs", "Global adoption epoch transitions are inconsistent.")
        policies = validate_policy_history(self.store.envelope()); ids = set()
        for job in s["jobs"]:
            require(type(job) is dict and all(type(job.get(k)) is str for k in
                ("id","stage_id","revision_id","source_key","context_id","profile_revision_id","operation","instruction",
                 "origin","execution_status","validation_status","review_status","created_at","raw_content","raw_reasoning","diff"))
                and all(type(job.get(k)) is dict for k in ("context","profile","parameters","checks"))
                and all(type(job.get(k)) is list for k in ("events","diagnostics")),
                "invalid_global_record","Global record fields have invalid types.")
            require(job["id"] not in ids and job["stage_id"] == STAGE and job["origin"] == "local_llm"
                    and job["execution_status"] in ACTIVE | TERMINAL and job["validation_status"] in ("Not Checked", "Passed", "Failed", "Unsupported")
                    and job["record_hash"] == object_hash({k:v for k,v in job.items() if k != "record_hash"}),
                    "invalid_global_record", "Global job checksum or status is inconsistent.")
            validate_profile(job["profile"])
            profile = next((p for p in self.generation._state["profiles"] if p["revision_id"] == job["profile_revision_id"]), None)
            require(job["profile"]["execution_location"] == "Local" and profile is not None
                    and object_hash(profile["profile"]) == object_hash(job["profile"]),
                    "invalid_global_origin", "Original global model must retain its saved Local profile version.")
            context = job["context"]; manifest = context["source_manifest"]
            snapshot = self.store.snapshot(job["revision_id"])
            if "requested_revision_id" in job or "requested_revision_id" in context:
                require(type(job.get("requested_revision_id")) is str
                        and job["requested_revision_id"] == context.get("requested_revision_id")
                        and same_revision_design(self.store, job["revision_id"], job["requested_revision_id"]),
                        "global_source_conflict", "The requested revision must preserve the exact original semantic source design.")
            require(object_hash(manifest["design"]) == object_hash(snapshot) == manifest["design_sha256"]
                    and manifest["canonical_job_hash"] == canonical_job_hash(snapshot)
                    and job["source_key"] == context["source_key"] == object_hash(manifest)
                    and context["context_id"] == job["context_id"] == object_hash({k:v for k,v in context.items() if k != "context_id"}),
                    "global_source_conflict", "Global context must retain its exact original source snapshot and manifest.")
            validate_global_plan(snapshot, context["verification_plan"])
            base = self._job(job["base_job_id"]) if job["base_job_id"] else None
            require(job["operation"] in ("generate", "repair") and type(job["instruction"]) is str
                    and ((job["operation"] == "repair" and base is not None and base["id"] in ids and base["rtl"]
                          and job["instruction"].strip()) or (job["operation"] == "generate" and base is None)),
                    "global_repair_conflict", "A repair must refer to earlier saved RTL and explicit feedback.")
            ids.add(job["id"])
            p = job["profile"]
            parameters = {"temperature": p["temperature"], "seed": p["seed"], "max_tokens": p["max_output_tokens"]}
            if p.get("reasoning_effort") is not None: parameters["reasoning_effort"] = p["reasoning_effort"]
            require(job["operation"] == context["operation"] and job["base_job_id"] == context["base_job_id"]
                    and job["instruction"] == context["instruction"]
                    and object_hash(job["parameters"]) == object_hash(context["parameters"]) == object_hash(parameters)
                    and job["profile_revision_id"] == context["profile_revision_id"]
                    and context["template_version"] in PROMPT_PROJECTIONS and context["revision_id"] == job["revision_id"]
                    and object_hash(context["interface"]) == object_hash(top_interface(snapshot))
                    and context["messages"] == integration_messages(manifest, job["instruction"], base, context["template_version"])
                    and context["prompt_projection"] == PROMPT_PROJECTIONS[context["template_version"]]
                    and (context.get("prompt_projection_sha256") == object_hash(integration_projection(manifest, context["template_version"]))
                         if context["template_version"] in (PROMPT_TEMPLATE_V2, PROMPT_TEMPLATE_V3, PROMPT_TEMPLATE_V4, PROMPT_TEMPLATE_V5, PROMPT_TEMPLATE_V6, PROMPT_TEMPLATE_V7, PROMPT_TEMPLATE_V8) else "prompt_projection_sha256" not in context)
                    and context["estimated_input_tokens"] == len(json.dumps(context["messages"], ensure_ascii=False, allow_nan=False).encode("utf-8"))
                    and context["token_estimate_method"] == "conservative_one_UTF8_byte_per_token",
                    "global_prompt_conflict", "The complete prompt must rebuild from exact saved public contracts, edges and explicit repair feedback.")
            require([n["node_id"] for n in manifest["nodes"]] == list(required_node_ids(manifest["design"])),
                    "global_source_conflict", "All required adopted source nodes are required in immutable design order.")
            for entry in manifest["nodes"]:
                candidate = self.generation._stored_job(entry["candidate_id"]); spec = self.specifications._spec(entry["spec_id"])
                source_netlist = self.workflow._run(entry["netlist_run_id"])
                node = next(n for n in snapshot["nodes"] if n["id"] == entry["node_id"])
                require(entry["rtl"] == candidate["rtl"] and entry["rtl_sha256"] == content_hash(entry["rtl"])
                        and entry["candidate_execution_hash"] == execution_evidence_hash(candidate)
                        and entry["netlist_execution_hash"] == execution_evidence_hash(source_netlist)
                        and object_hash(entry["specification"]) == object_hash(spec["specification"]) == entry["specification_sha256"]
                        and entry["revision_id"] == candidate["revision_id"] == job["revision_id"]
                        and entry["module_name"] == node["module_name"] and candidate["node_id"] == spec["node_id"] == entry["node_id"]
                        and spec["candidate_id"] == candidate["id"] and spec["source_run_id"] == entry["netlist_run_id"]
                        and spec["specification"]["lineage"]["synthesis_run_id"] == entry["synthesis_run_id"]
                        and object_hash(entry["public_interface"]) == object_hash(physical_interface(snapshot, node))
                        and any(object_hash(entry["S07_adoption"])==object_hash(r) for r in self.specifications._state["reviews"])
                        and entry["S07_adoption"]["spec_id"] == spec["id"] and entry["S07_adoption"]["decision"] == "accepted",
                        "global_source_conflict", "Historical global sources must retain the exact original adopted RTL and S07 evidence.")
            require(type(job["raw_content"]) is str and type(job["raw_reasoning"]) is str
                    and job["raw_content_sha256"] == content_hash(job["raw_content"])
                    and (job["rtl_sha256"] == content_hash(job["rtl"]) if type(job["rtl"]) is str else job["rtl"] is None and job["rtl_sha256"] is None),
                    "global_text_conflict", "Saved model content hashes differ.")
            require([e["sequence"] for e in job["events"]] == list(range(1, len(job["events"]) + 1)),
                    "global_event_conflict", "Global event sequence is inconsistent.")
            for field,kinds in (("raw_content",("delta","content","partial_answer")),("raw_reasoning",("reasoning",))):
                chunks=[e["content"] for e in job["events"] if e.get("type") in kinds]
                require(all(type(c) is str for c in chunks) and "".join(chunks)==job[field],
                        "global_event_conflict","Saved stream events must reconstruct the complete original provider text.")
            if job["rtl"] is not None:
                require(extract_rtl(job["raw_content"]).get("rtl") == job["rtl"], "global_answer_conflict", "RTL must be extracted from the saved provider answer.")
            if job["validation_status"] == "Passed":
                require(self._passed(job), "global_proof_conflict", "Global pass must preserve exact executed compilation and original-job evidence.")
            reviews = [v for v in s["reviews"] if v["job_id"] == job["id"]]
            expected = "Awaiting Review" if not reviews else "Accepted" if reviews[-1]["decision"] == "accepted" else "Changes Requested"
            require(job["review_status"] == expected and (expected != "Accepted" or job["validation_status"] == "Passed"
                    and job.get("acceptance_epoch") == reviews[-1]["acceptance_epoch"]), "global_review_conflict", "Global adoption differs from its reviews.")
        for review in s["reviews"]:
            require(review["job_id"] in ids and review["decision"] in ("accepted", "changes_requested", "return_to_stage"),
                    "global_review_conflict", "Global review target is invalid.")
            job = self._job(review["job_id"])
            require(type(review["note"]) is str and review["actor"] in REVIEW_ACTORS
                    and review["source_key"] == job["source_key"]
                    and type(review["reviewed_revision_id"]) is str
                    and (review["target_stage"] in (*IMPLEMENTED_STAGES, "local_rtl_generation", "local_synthesis",
                         "local_netlist_simulation", "node_implementation_specs") if review["decision"] == "return_to_stage"
                         else review["target_stage"] is None),
                    "global_review_conflict", "Global review must preserve its source, actor and implemented destination.")
            self.store.snapshot(review["reviewed_revision_id"])
            validate_policy_review(review, policies)
            if review["decision"] == "accepted":
                require(same_revision_design(self.store, review["reviewed_revision_id"], job["revision_id"]) and type(review["acceptance_epoch"]) is int
                        and any(t["epoch"] == review["acceptance_epoch"] and t["source_key"] == review["source_key"] for t in s["source_transitions"]),
                        "global_review_conflict", "Global acceptance must bind its original observed source epoch.")
        validate_submissions(self._state)

    def _persist(self):
        require_durable_write()
        name = None
        try:
            for job in self._state["jobs"]:
                job["raw_content_sha256"] = content_hash(job["raw_content"])
                job["rtl_sha256"] = content_hash(job["rtl"]) if job["rtl"] is not None else None
                job["record_hash"] = object_hash({k:v for k,v in job.items() if k != "record_hash"})
            _io_path(self.path.parent).mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(prefix=".global-generation-", suffix=".tmp", dir=_io_path(self.path.parent))
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(self._state, ensure_ascii=False, allow_nan=False, indent=2) + "\n"); handle.flush(); os.fsync(handle.fileno())
            _replace_with_windows_retry(name, _io_path(self.path)); self._committed = copy.deepcopy(self._state)
            self._storage_error = None; self._checkpoint = time.monotonic(); self._pending = 0
        except (OSError, ValueError, TypeError):
            self._state = copy.deepcopy(self._committed); self._storage_error = {"code": "storage_error", "message": "Global history save failed; last durable state retained."}
            raise
        finally:
            if name and _io_path(name).exists(): _io_path(name).unlink()

    def close(self):
        with self.lock:
            self._closed = True
            if self._worker and self._worker.is_alive(): self._cancel.set()
        if self._worker and self._worker.is_alive(): self._worker.join(timeout=3)

"""Independent software QA; fixture RTL is never local-model evidence."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src")); sys.path.insert(0, str(PROJECT / "scripts"))
from hullcirq.domain import DomainError
from hullcirq.npu_nodes_verification import (KINDS, build_nodes_plan, nodes_asserted_trace,
                                            projected_job, validate_nodes_plan)
from hullcirq.verification import content_hash, object_hash, verify_behavior
from prepare_npu_nodes_project import build_proposal


def design():
    return build_proposal(json.loads((PROJECT / "examples/npu_scheduler_project.json").read_text(encoding="utf-8")))


BUFFER_FIXTURE = """module hullcirq_buffer(input wire clk,input wire rst,
input wire [15:0] load_data,input wire load_data_valid,output wire load_data_ready,
input wire [15:0] read_request,input wire read_request_valid,output wire read_request_ready,
output wire [15:0] read_response,output wire read_response_valid,input wire read_response_ready);
reg [7:0] a[0:63];reg [7:0] b[0:63];reg v;reg [15:0] d;
assign load_data_ready=!rst&&!v&&!load_data[15];
assign read_request_ready=!rst&&!v&&!load_data_valid&&((read_request&16'hc0c0)==0);
assign read_response=d;assign read_response_valid=!rst&&v;
always @(posedge clk)begin
if(rst)v<=0;
else begin
 if(load_data_valid&&load_data_ready)begin if(load_data[14])b[load_data[13:8]]<=load_data[7:0];else a[load_data[13:8]]<=load_data[7:0];end
 if(read_request_valid&&read_request_ready)begin d<={b[read_request[13:8]],a[read_request[5:0]]};v<=1;end
 else if(read_response_valid&&read_response_ready)v<=0;
end end endmodule
"""
POST_FIXTURE = """module hullcirq_post(input wire clk,input wire rst,
input wire signed [31:0] acc_data,input wire acc_data_valid,output wire acc_data_ready,
input wire [128:0] post_config,input wire post_config_valid,output wire post_config_ready,
output wire signed [31:0] result_data,output wire result_data_valid,input wire result_data_ready);
reg configured,v;reg [1:0] col;reg [128:0] cfg;reg signed [31:0] data;
wire [31:0] bias=(cfg>>(1+32*col));wire [31:0] added=acc_data+bias;
assign post_config_ready=!rst&&!v&&(col==0);
assign acc_data_ready=!rst&&configured&&(!v||result_data_ready)&&!post_config_valid;
assign result_data=data;assign result_data_valid=!rst&&v;
always @(posedge clk)begin
if(rst)begin configured<=0;v<=0;col<=0;cfg<=0;data<=0;end
else begin
 if(post_config_valid&&post_config_ready)begin configured<=1;cfg<=post_config;col<=0;end
 if(acc_data_valid&&acc_data_ready)begin data<=(cfg[0]&&added[31])?32'b0:added;v<=1;col<=col+1'b1;end
 else if(result_data_valid&&result_data_ready)v<=0;
end end endmodule
"""
FIFO_FIXTURE = """module hullcirq_fifo(input wire clk,input wire rst,
input wire signed [31:0] result_data,input wire result_data_valid,output wire result_data_ready,
output wire signed [31:0] output_data,output wire output_data_valid,input wire output_data_ready,
output wire output_transfer);
reg [31:0] mem[0:1];reg rp,wp;reg [1:0] count;
wire push=result_data_valid&&result_data_ready;wire pop=output_data_valid&&output_data_ready;
assign output_data_valid=!rst&&(count!=0);assign output_data=mem[rp];
assign result_data_ready=!rst&&((count<2)||pop);assign output_transfer=pop;
always @(posedge clk)begin
 if(rst)begin count<=0;rp<=0;wp<=0;end
 else begin
 if(push)begin mem[wp]<=result_data;wp<=!wp;end
 if(pop)rp<=!rp;
 case({push,pop})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:count<=count;endcase
 end end endmodule
"""
FIXTURES = {"node-buffer": BUFFER_FIXTURE, "node-post": POST_FIXTURE, "node-fifo": FIFO_FIXTURE}


class NpuNodeReferenceTests(unittest.TestCase):
    def test_proposal_preserves_source_job_pe_plan_and_all_existing_ports(self):
        original = json.loads((PROJECT / "examples/npu_scheduler_project.json").read_text(encoding="utf-8"))
        proposed = build_proposal(original)
        self.assertEqual(proposed["verification_jobs"], original["verification_jobs"])
        self.assertEqual(proposed["edges"], original["edges"])
        self.assertEqual(next(n for n in proposed["nodes"] if n["id"] == "node-pe"), next(n for n in original["nodes"] if n["id"] == "node-pe"))
        for node in original["nodes"]:
            updated = next(n for n in proposed["nodes"] if n["id"] == node["id"])
            self.assertEqual(updated["ports"][:len(node["ports"])], node["ports"])
        self.assertEqual(build_proposal(proposed), proposed)

    def test_independent_original_matrix_projection_wraps_bias_and_preserves_disabled_relu(self):
        job = design()["verification_jobs"][0]
        projection = projected_job(job)
        self.assertEqual(projection["accumulators"][:4], [113, (-122)&0xFFFFFFFF, (-127)&0xFFFFFFFF, (-1041)&0xFFFFFFFF])
        self.assertEqual(projection["results"][:4], [113, (-112)&0xFFFFFFFF, (-135)&0xFFFFFFFF, 2147482606])
        self.assertEqual(projection["results"][7], 2147483652)
        self.assertFalse(job["relu"])
        self.assertEqual(projection["post_config"] & 1, 0)
        self.assertEqual([(projection["post_config"] >> (1+32*i)) & 0xFFFFFFFF for i in range(4)], [v&0xFFFFFFFF for v in job["bias"]])

    def test_buffer_exact_load_bytes_priority_retention_and_all_scheduler_address_responses(self):
        original = design();job = original["verification_jobs"][0]
        plan = build_nodes_plan(original, "node-buffer")
        loaded = [item["stimulus"]["load_data"] for item in plan["reference_trace"] if item["load_data_transfer"]]
        expected = [(r*16+k)<<8 | (job["A"][r][k]&255) for r in range(4) for k in range(4)]
        expected += [(64|k*4+c)<<8 | (job["B"][k][c]&255) for k in range(4) for c in range(4)]
        self.assertEqual(loaded, expected)
        responses = [item["before"]["read_response"] for item in plan["reference_trace"] if item["read_response_transfer"]]
        self.assertEqual(responses, [(job["A"][r][k]&255)|(job["B"][k][c]&255)<<8 for r in range(4) for c in range(4) for k in range(4)])
        self.assertEqual(plan["coverage"]["retained_memory_response_transfers"],64)
        self.assertEqual(plan["coverage"]["invalid_load_cycles"],2)
        self.assertEqual(plan["coverage"]["invalid_read_cycles"],2)
        self.assertEqual(plan["coverage"]["load_priority_cycles"],32)
        self.assertEqual(plan["coverage"]["reset_with_pending_output"],1)
        validate_nodes_plan(plan)

    def test_post_final_complete_original_results_and_midrow_config_reset(self):
        original=design();plan=build_nodes_plan(original,"node-post")
        starts=[i["cycle"] for i in plan["reference_trace"] if i["post_config_transfer"]]
        self.assertEqual(len(starts),4)
        results=[i["before"]["result_data"] for i in plan["reference_trace"] if starts[2]<=i["cycle"]<starts[3] and i["result_data_transfer"]]
        self.assertEqual(results,projected_job(original["verification_jobs"][0])["results"])
        self.assertGreater(plan["coverage"]["simultaneous_replace_cycles"],0)
        self.assertEqual(plan["coverage"]["reset_with_pending_output"],1)
        self.assertGreater(plan["coverage"]["rejected_midrow_config_cycles"],0)
        validate_nodes_plan(plan)

    def test_fifo_full_stall_full_simultaneous_ring_wrap_and_reset_order(self):
        original=design();plan=build_nodes_plan(original,"node-fifo")
        results=[i["before"]["output_data"] for i in plan["reference_trace"] if i["output_data_transfer"]]
        self.assertEqual(results,projected_job(original["verification_jobs"][0])["results"])
        self.assertGreater(plan["coverage"]["full_stall_cycles"],0)
        self.assertGreater(plan["coverage"]["full_simultaneous_cycles"],0)
        self.assertEqual(plan["coverage"]["reset_with_pending_output"],1)
        for item in plan["reference_trace"]:
            self.assertEqual(item["before"]["output_transfer"],item["output_data_transfer"])
        validate_nodes_plan(plan)

    def test_all_source_valid_data_stability_until_handshake_or_shared_reset(self):
        from hullcirq.npu_nodes_verification import STREAMS
        for kind,node in KINDS.items():
            plan=build_nodes_plan(design(),node)
            for left,right in zip(plan["reference_trace"],plan["reference_trace"][1:]):
                for name,(direction,_,_) in STREAMS[kind].items():
                    if direction=="input" and not left["stimulus"]["reset"] and left["stimulus"][name+"_valid"] and not left["before"][name+"_ready"]:
                        self.assertEqual(right["stimulus"][name+"_valid"],1,(node,name,left["cycle"]))
                        self.assertEqual(right["stimulus"][name],left["stimulus"][name],(node,name,left["cycle"]))

    def test_canonical_job_changes_duplicates_types_and_unsupported_recipe_fail_closed(self):
        for node in KINDS.values():
            for change in (lambda d:d["verification_jobs"][0].update(k=4.0),
                           lambda d:d["verification_jobs"].append(copy.deepcopy(d["verification_jobs"][0])),
                           lambda d:d["verification_jobs"][0]["bias"].__setitem__(0,False),
                           lambda d:d["verification_jobs"][0]["A"][0].__setitem__(0,-127),
                           lambda d:next(n for n in d["nodes"] if n["id"]==node)["verification"]["exercise"].update(extra=True)):
                changed=design();change(changed)
                with self.subTest(node=node,change=change),self.assertRaises(DomainError):
                    build_nodes_plan(changed,node)

    def test_checksum_updated_vectors_reference_testbench_coverage_cannot_replace_plan(self):
        for node in KINDS.values():
            original=build_nodes_plan(design(),node)
            for field in ("expanded_vectors","reference_trace","testbench","coverage"):
                plan=copy.deepcopy(original)
                if field=="expanded_vectors":plan[field][5]["reset"]^=1;plan["vector_hash"]=object_hash(plan[field])
                elif field=="reference_trace":plan[field][5]["cycle"]=999;plan["reference_trace_hash"]=object_hash(plan[field])
                elif field=="testbench":plan[field]+="//stage replacement\n";plan["testbench_sha256"]=content_hash(plan[field])
                else:plan[field]["reset_cycles"]=999
                with self.subTest(node=node,field=field),self.assertRaises(DomainError):validate_nodes_plan(plan)

    def test_s07_facts_omit_inactive_payloads_and_reference_internal_state(self):
        from hullcirq.npu_nodes_verification import STREAMS
        for kind,node in KINDS.items():
            plan=build_nodes_plan(design(),node)
            trace=nodes_asserted_trace(plan)
            self.assertIsNone(trace[0]["asserted_before"])
            for item in trace:
                self.assertNotIn("reference_bookkeeping",item)
                for values in (item["asserted_before"],item["asserted_after"]):
                    if values is None:continue
                    for name,(direction,_,_) in STREAMS[kind].items():
                        if direction=="output":self.assertEqual(name in values,bool(values[name+"_valid"]))
            self.assertLess(plan["vector_count"],600)


class NpuNodeActualToolQaTests(unittest.TestCase):
    def setUp(self):
        path=PROJECT/".work/m2/compiler.json"
        if not path.exists():self.skipTest("Existing isolated trusted Icarus runtime unavailable.")
        self.compiler=json.loads(path.read_text(encoding="utf-8-sig"))

    def test_three_positive_fixtures_with_actual_icarus(self):
        for node,rtl in FIXTURES.items():
            with self.subTest(node=node):
                result=verify_behavior(rtl,build_nodes_plan(design(),node),self.compiler,PROJECT/".work/npu-nodes-software-qa")
                self.assertEqual(result["validation_status"],"Passed",result["stdout"]+result["stderr"])

    def test_corrupt_operand_bias_and_fifo_completion_fail_actual_assertions(self):
        changes={"node-buffer":("a[read_request[5:0]]","a[read_request[5:0]]^8'h01"),
                 "node-post":("acc_data+bias","acc_data+bias+1'b1"),
                 "node-fifo":("assign output_transfer=pop","assign output_transfer=output_data_valid")}
        for node,(old,new) in changes.items():
            with self.subTest(node=node):
                result=verify_behavior(FIXTURES[node].replace(old,new),build_nodes_plan(design(),node),self.compiler,PROJECT/".work/npu-nodes-software-qa")
                self.assertEqual(result["validation_status"],"Failed",result["stdout"]+result["stderr"])
                self.assertIn("HULLCIRQ_FAIL",result["stdout"])

    def test_post_config_ready_row_boundary_fault_fails_even_with_empty_output(self):
        rtl=POST_FIXTURE.replace("!rst&&!v&&(col==0)","!rst&&!v")
        result=verify_behavior(rtl,build_nodes_plan(design(),"node-post"),self.compiler,PROJECT/".work/npu-nodes-software-qa")
        self.assertEqual(result["validation_status"],"Failed",result["stdout"]+result["stderr"])
        self.assertIn("signal=post_config_ready",result["stdout"])

    def test_s07_three_node_payloads_use_actual_fixture_syntax_synthesis_and_netlist_proof(self):
        """Actual tools on explicit QA source; no real project/model jobs exist."""
        from hullcirq.context import node_fingerprint, physical_interface
        from hullcirq.domain import revision_hashes
        from hullcirq.implementation_specs import build_node_implementation_spec
        from hullcirq.rtl_checks import check_rtl
        from hullcirq.workflow import synthesize_generic
        path=PROJECT/".work/m2b/synthesizer.json"
        if not path.exists():self.skipTest("Existing isolated trusted Yosys unavailable.")
        synthesizer=json.loads(path.read_text(encoding="utf-8-sig"))
        original=design()
        qa_root=PROJECT/".work/npu-nodes-software-qa";qa_root.mkdir(parents=True,exist_ok=True)
        for node_id,rtl in FIXTURES.items():
            with self.subTest(node=node_id):
                node=next(n for n in original["nodes"] if n["id"]==node_id)
                plan=build_nodes_plan(original,node_id)
                compiled=check_rtl(rtl,physical_interface(original,node),node["module_name"],self.compiler)
                self.assertEqual(compiled["validation_status"],"Passed",compiled["diagnostics"])
                behavioral=verify_behavior(rtl,plan,self.compiler,qa_root)
                self.assertEqual(behavioral["validation_status"],"Passed",behavioral["stdout"]+behavioral["stderr"])
                candidate={"id":"qa-fixture-candidate-"+node_id,"node_id":node_id,"revision_id":"qa-only-source-revision",
                           "execution_status":"Completed","validation_status":"Passed","input_hash":node_fingerprint(original,node_id),
                           "rtl":rtl,"rtl_sha256":content_hash(rtl),"verification_plan":plan,
                           "checks":{**compiled["checks"],"behavioral":behavioral},"origin":"software_qa_fixture_never_actual_model_evidence"}
                synth=synthesize_generic(rtl,node["module_name"],synthesizer,tempfile.mkdtemp(prefix="s07-fixture-",dir=qa_root))
                self.assertEqual(synth["validation_status"],"Passed",synth["stdout"]+synth["stderr"])
                simulated=verify_behavior(synth["netlist"],plan,self.compiler,qa_root)
                self.assertEqual(simulated["validation_status"],"Passed",simulated["stdout"]+simulated["stderr"])
                common={"candidate_id":candidate["id"],"node_id":node_id,"revision_id":candidate["revision_id"],"input_hash":candidate["input_hash"],
                        "design_hash":revision_hashes(original)["semantic_hash"],"rtl_sha256":candidate["rtl_sha256"],"verification_plan":plan,
                        "vector_hash":plan["vector_hash"],"testbench_sha256":plan["testbench_sha256"],"netlist":synth["netlist"],"netlist_sha256":synth["netlist_sha256"],
                        "execution_status":"Completed","validation_status":"Passed","origin":"software_qa_fixture_never_actual_project_history"}
                source={**common,"id":"qa-synthesis-"+node_id,"stage_id":"local_synthesis","checks":synth}
                source["record_hash"]=object_hash(source)
                simulation={**common,"id":"qa-netlist-"+node_id,"prior_run_id":source["id"],"stage_id":"local_netlist_simulation","checks":simulated}
                simulation["record_hash"]=object_hash(simulation)
                spec=build_node_implementation_spec(original,candidate,source,simulation)
                self.assertEqual(spec["checks"]["validation_status"],"Passed")
                self.assertEqual(spec["observed_facts"]["trace"],nodes_asserted_trace(plan))
                self.assertEqual(spec["observed_facts"]["checked_assertion_count"],sum(len(i["asserted_before"] or {})+len(i["asserted_after"]) for i in nodes_asserted_trace(plan)))
                self.assertEqual(len(spec["public_interface"]["ports"]),9 if node_id=="node-fifo" else 11)
                self.assertEqual(len(spec["public_interface"]["streams"]),2 if node_id=="node-fifo" else 3)
                if node_id=="node-fifo":self.assertEqual(spec["public_interface"]["raw_signals"][0]["name"],"output_transfer")
                mixed=copy.deepcopy(simulation);mixed["vector_hash"]="0"*64
                mixed["record_hash"]=object_hash({k:v for k,v in mixed.items() if k!="record_hash"})
                with self.assertRaises(DomainError):build_node_implementation_spec(original,candidate,source,mixed)


if __name__=="__main__":unittest.main()

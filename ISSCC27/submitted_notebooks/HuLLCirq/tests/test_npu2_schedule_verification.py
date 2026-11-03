"""Qualify source-derived scheduler/dispatcher checkers; fixtures are NOT project RTL.

No model request, GUI input mutation, candidate adoption, or actual NPU run is
performed here. Intentional fixture faults must fail by an assertion, rather
than merely fail to compile.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.domain import DomainError
from hullcirq.npu2_schedule_verification import (SCHEDULER_KIND, DISPATCHER_KIND, SCHEDULER_TEMPLATE, DISPATCHER_TEMPLATE,
    build_scheduler_plan, build_dispatcher_plan, validate_schedule_plan, operand_bundles, batch_packets, lane_packets, schedule_asserted_trace, template_for_kind)
from hullcirq.verification import content_hash, object_hash, verify_behavior


def design():
    return json.loads((PROJECT / "examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))


SCHEDULER_FIXTURE = """// Independent software qualification fixture, not an adopted candidate.
module hullcirq_npu2_scheduler(input clk,input rst,
 input [3:0] schedule_config,input schedule_config_valid,output schedule_config_ready,
 output [2:0] read_index,output read_index_valid,input read_index_ready,
 input [31:0] operands,input operands_valid,output operands_ready,
 output [33:0] batch_data,output batch_data_valid,input batch_data_ready);
 reg [1:0] phase; reg [3:0] limit; reg [2:0] index; reg [31:0] saved;
 assign schedule_config_ready=(phase==0);
 assign read_index=index;
 assign read_index_valid=(phase==1);
 assign operands_ready=(phase==2);
 assign batch_data={index==limit-1,index==0,saved};
 assign batch_data_valid=(phase==3);
 always @(posedge clk) begin
  if(rst) begin phase<=0; limit<=0; index<=0; saved<=0; end
  else case(phase)
   0: if(schedule_config_valid && schedule_config_ready) begin limit<=schedule_config; index<=0; phase<=1; end
   1: if(read_index_valid && read_index_ready) phase<=2;
   2: if(operands_valid && operands_ready) begin saved<=operands; phase<=3; end
   3: if(batch_data_valid && batch_data_ready) begin if(index==limit-1) phase<=0; else begin index<=index+1'b1; phase<=1; end end
  endcase
 end
endmodule
"""
DISPATCHER_FIXTURE = """// Independent software qualification fixture, not an adopted candidate.
module hullcirq_npu2_dispatcher(input clk,input rst,
 input [33:0] batch_data,input batch_data_valid,output batch_data_ready,
 output [17:0] pair00,output pair00_valid,input pair00_ready,
 output [17:0] pair01,output pair01_valid,input pair01_ready,
 output [17:0] pair10,output pair10_valid,input pair10_ready,
 output [17:0] pair11,output pair11_valid,input pair11_ready);
 reg pending; reg [3:0] delivered; reg [33:0] saved;
 wire [3:0] transfer={pair11_valid && pair11_ready,pair10_valid && pair10_ready,pair01_valid && pair01_ready,pair00_valid && pair00_ready};
 assign batch_data_ready=!pending;
 assign pair00={saved[33:32],saved[23:16],saved[7:0]};
 assign pair01={saved[33:32],saved[31:24],saved[7:0]};
 assign pair10={saved[33:32],saved[23:16],saved[15:8]};
 assign pair11={saved[33:32],saved[31:24],saved[15:8]};
 assign pair00_valid=pending && !delivered[0];
 assign pair01_valid=pending && !delivered[1];
 assign pair10_valid=pending && !delivered[2];
 assign pair11_valid=pending && !delivered[3];
 always @(posedge clk) begin
  if(rst) begin pending<=0; delivered<=0; saved<=0; end
  else if(batch_data_valid && batch_data_ready) begin pending<=1; delivered<=0; saved<=batch_data; end
  else if(pending) begin delivered<=delivered | transfer; if((delivered | transfer)==4'b1111) pending<=0; end
 end
endmodule
"""


def fixture_cases():
    return {
        "scheduler_correct": ("npu2-scheduler", SCHEDULER_FIXTURE, "Passed"),
        "scheduler_wrong_index": ("npu2-scheduler", SCHEDULER_FIXTURE.replace("assign read_index=index;", "assign read_index=index+1'b1;"), "Failed"),
        "scheduler_wrong_last": ("npu2-scheduler", SCHEDULER_FIXTURE.replace("assign batch_data={index==limit-1,index==0,saved};", "assign batch_data={1'b0,index==0,saved};"), "Failed"),
        "scheduler_wrong_operand_order": ("npu2-scheduler", SCHEDULER_FIXTURE.replace("saved<=operands;", "saved<={operands[15:0],operands[31:16]};"), "Failed"),
        "scheduler_drops_stalled_read": ("npu2-scheduler", SCHEDULER_FIXTURE.replace("assign read_index_valid=(phase==1);", "assign read_index_valid=(phase==1) && read_index_ready;"), "Failed"),
        "scheduler_read_before_batch_consumed": ("npu2-scheduler", SCHEDULER_FIXTURE.replace("assign read_index_valid=(phase==1);", "assign read_index_valid=(phase==1 || phase==3);"), "Failed"),
        "scheduler_async_reset": ("npu2-scheduler", SCHEDULER_FIXTURE.replace("always @(posedge clk)", "always @(posedge clk or posedge rst)"), "Failed"),
        "dispatcher_correct": ("npu2-dispatcher", DISPATCHER_FIXTURE, "Passed"),
        "dispatcher_wrong_lane": ("npu2-dispatcher", DISPATCHER_FIXTURE.replace("assign pair01={saved[33:32],saved[31:24],saved[7:0]};", "assign pair01={saved[33:32],saved[23:16],saved[7:0]};"), "Failed"),
        "dispatcher_duplicate_lane": ("npu2-dispatcher", DISPATCHER_FIXTURE.replace("assign pair00_valid=pending && !delivered[0];", "assign pair00_valid=pending;"), "Failed"),
        "dispatcher_shared_ready": ("npu2-dispatcher", DISPATCHER_FIXTURE.replace("pair01_valid && pair01_ready", "pair01_valid && pair00_ready"), "Failed"),
        "dispatcher_same_cycle_replace": ("npu2-dispatcher", DISPATCHER_FIXTURE.replace("assign batch_data_ready=!pending;", "assign batch_data_ready=!pending || ((delivered | transfer)==4'b1111);"), "Failed"),
        "dispatcher_stalled_data_changes": ("npu2-dispatcher", DISPATCHER_FIXTURE.replace("assign pair11={saved[33:32],saved[31:24],saved[15:8]};", "assign pair11={saved[33:32],saved[31:24],saved[15:8]} ^ (pair11_ready ? 18'd0 : 18'd1);"), "Failed"),
        "dispatcher_async_reset": ("npu2-dispatcher", DISPATCHER_FIXTURE.replace("always @(posedge clk)", "always @(posedge clk or posedge rst)"), "Failed"),
    }


def run_qualification(archive_directory=None):
    source = design()
    compiler = json.loads((PROJECT / ".work/m2/compiler.json").read_text(encoding="utf-8-sig"))
    plans = {"npu2-scheduler": build_scheduler_plan(source, "npu2-scheduler"), "npu2-dispatcher": build_dispatcher_plan(source, "npu2-dispatcher")}
    report = {"scope": "software_checker_qualification_only_not_actual_project_evidence", "source_job": copy.deepcopy(source["verification_jobs"][0]), "source_design_sha256": object_hash(source),
              "fixture_origin": "development_assistant_independent_positive_and_intentional_fault_fixtures", "project_mutation": False, "cases": []}
    archive = Path(archive_directory) if archive_directory else None
    if archive:
        archive.mkdir(parents=True, exist_ok=True)
        for node_id, plan in plans.items():
            (archive / (node_id + "_plan.json")).write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, (node_id, rtl, expected) in fixture_cases().items():
        result = verify_behavior(rtl, plans[node_id], compiler, PROJECT / ".work/npu2-schedule-checker-qualification")
        correct_marker = "HULLCIRQ_PASS" if expected == "Passed" else "HULLCIRQ_FAIL"
        qualified = result["validation_status"] == expected and correct_marker in result["stdout"] and len(result["commands"]) == 3 and result["commands"][1]["exit_code"] == 0
        report["cases"].append({"name": name, "node_id": node_id, "expected": expected, "qualified": qualified, "rtl_sha256": content_hash(rtl), "result": result})
        if archive:
            (archive / (name + ".v")).write_text(rtl, encoding="utf-8")
            (archive / (name + ".json")).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report["qualified"] = all(case["qualified"] for case in report["cases"])
    if archive:
        (archive / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


class ScheduleVerificationTests(unittest.TestCase):
    def test_build_freezes_full_source_and_preserves_input(self):
        for builder, node, kind, template in ((build_scheduler_plan,"npu2-scheduler",SCHEDULER_KIND,SCHEDULER_TEMPLATE), (build_dispatcher_plan,"npu2-dispatcher",DISPATCHER_KIND,DISPATCHER_TEMPLATE)):
            source=design(); before=copy.deepcopy(source); plan=builder(source,node)
            self.assertEqual(before,source); self.assertEqual(plan["kind"],kind); self.assertEqual(template_for_kind(kind),template)
            self.assertEqual(plan["contract"]["source_job"],source["verification_jobs"][0]); validate_schedule_plan(plan)
            self.assertEqual(plan["testbench_template_version"],template)

    def test_independent_original_operand_byte_projection_and_markers(self):
        job=design()["verification_jobs"][0]
        self.assertEqual(operand_bundles(job),[0xff0607f8,0x05fdfe03,0x07020405])
        batches=batch_packets(job)
        self.assertEqual(batches,[0x1ff0607f8,0x005fdfe03,0x207020405])
        self.assertEqual(lane_packets(batches[0]),{"00":0x106f8,"01":0x1fff8,"10":0x10607,"11":0x1ff07})
        for builder,node in ((build_scheduler_plan,"npu2-scheduler"),(build_dispatcher_plan,"npu2-dispatcher")):
            plan=builder(design(),node)
            self.assertEqual(plan["coverage"]["original_job_repetitions_completed"],2)
            self.assertGreater(plan["coverage"]["nonclocked_reset_pulses"],0)
            for vector in plan["expanded_vectors"]:
                if vector["action"] in ("offer","hold_next","batch"):
                    self.assertIn(vector["data"],batches)
                if vector["action"]=="response": self.assertIn(vector["data"],operand_bundles(job))

    def test_scheduler_cancel_and_stall_cases_are_finite_and_not_exact_cycle_claims(self):
        plan=build_scheduler_plan(design(),"npu2-scheduler")
        self.assertEqual(plan["coverage"]["reset_cancel_points"],["pending_read","waiting_operand_response","pending_batch"])
        self.assertEqual(plan["coverage"]["complete_job_read_requests"],6)
        self.assertGreater(plan["coverage"]["read_stall_recipe_cycles"],6)
        self.assertGreater(plan["coverage"]["batch_stall_recipe_cycles"],6)
        self.assertIn("attempt<64",plan["testbench"]); self.assertIn("event_driven",plan["stimulus_timing"])

    def test_dispatcher_independent_lane_masks_and_backpressure_are_present(self):
        plan=build_dispatcher_plan(design(),"npu2-dispatcher")
        self.assertEqual(plan["coverage"]["independent_lane_ready_masks"],[0,1,2,4,8])
        self.assertEqual(plan["coverage"]["next_original_batch_offered_while_pending"],4)
        self.assertEqual(plan["coverage"]["complete_job_lane_transfers"],24)
        self.assertIn("same-cycle replacement",plan["testbench"])
        for row in schedule_asserted_trace(plan):
            self.assertNotIn("cycle",row)
            if row["stimulus"]["action"]=="reset": self.assertTrue(all(value==0 for value in row["asserted_after"].values()))

    def test_altered_job_invalidates_hash_and_stimulus_and_bad_types_fail_closed(self):
        for builder,node in ((build_scheduler_plan,"npu2-scheduler"),(build_dispatcher_plan,"npu2-dispatcher")):
            source=design(); first=builder(source,node); source["verification_jobs"][0]["A"][0][0]=-7; second=builder(source,node)
            self.assertNotEqual(first["vector_hash"],second["vector_hash"]); self.assertNotEqual(first["testbench_sha256"],second["testbench_sha256"])
            for key,value in (("k",True),("relu",0)):
                bad=design(); bad["verification_jobs"][0][key]=value
                with self.assertRaises(DomainError): builder(bad,node)
            bad=design(); bad["verification_jobs"][0]["A"][0][0]=False
            with self.assertRaises(DomainError): builder(bad,node)

    def test_contract_edits_and_malformed_ports_edges_fail_closed(self):
        for builder,node in ((build_scheduler_plan,"npu2-scheduler"),(build_dispatcher_plan,"npu2-dispatcher")):
            for field,value in (("behavior","changed"),("constraints",{"latency_cycles":2}),("module_name","unsafe;name")):
                bad=design(); next(n for n in bad["nodes"] if n["id"]==node)[field]=value
                with self.assertRaises(DomainError): builder(bad,node)
            for mutate in (lambda d:d["settings"].update(reset_kind="asynchronous"),lambda d:d["design_intent"].update(matrix_rows=4),lambda d:d["global_integration"].update(reset_contract="optional")):
                bad=design(); mutate(bad)
                with self.assertRaises(DomainError): builder(bad,node)
            bad=design(); next(n for n in bad["nodes"] if n["id"]==node)["ports"][0]["width"]=True
            with self.assertRaises(DomainError): builder(bad,node)
            bad=design(); next(e for e in bad["edges"] if e["source"]["node_id"]==node)["behavior"]="changed"
            with self.assertRaises(DomainError): builder(bad,node)
            with self.assertRaises(DomainError): builder(design(),node,"future")

    def test_tampering_rejected_and_old_source_hash_preserved(self):
        for builder,node in ((build_scheduler_plan,"npu2-scheduler"),(build_dispatcher_plan,"npu2-dispatcher")):
            original=builder(design(),node)
            for mutate in (lambda p:p.update(testbench=p["testbench"]+"changed"),lambda p:p.update(vector_hash="bad"),lambda p:p["reference_trace"][0].update(reset_cancels_pending=False),lambda p:p["coverage"].update(original_job_repetitions_completed=99),lambda p:p["expanded_vectors"][0].update(label="changed")):
                bad=copy.deepcopy(original); mutate(bad)
                with self.assertRaises(DomainError): validate_schedule_plan(bad)

    def test_positive_and_fault_mutants_execute_actual_existing_icarus(self):
        if not (PROJECT / ".work/m2/compiler.json").exists(): self.skipTest("Trusted existing Icarus not configured")
        report=run_qualification()
        for case in report["cases"]:
            with self.subTest(case=case["name"]):
                self.assertTrue(case["qualified"],case["result"]["stdout"]+case["result"]["stderr"])


if __name__=="__main__": unittest.main()

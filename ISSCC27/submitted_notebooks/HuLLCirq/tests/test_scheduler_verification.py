"""Software QA fixtures; none are local-model or actual-NPU evidence."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.domain import DomainError
from hullcirq.scheduler_verification import (expand_vectors, pack_configuration,
                                            scheduler_asserted_trace, scheduler_reference_trace)
from hullcirq.verification import build_verification_plan, content_hash, object_hash, validate_plan, verify_behavior


def scheduler_design():
    design = json.loads((PROJECT / "examples" / "npu_project.json").read_text(encoding="utf-8"))
    node = next(node for node in design["nodes"] if node["id"] == "node-scheduler")
    for name, width, kind in (("pair_meta", 6, "metadata"), ("pe_clear", 1, "pulse"), ("schedule_done", 1, "pulse")):
        node["ports"].append({"id": "port-scheduler-" + name, "name": name, "direction": "output", "width": width,
                              "signed": False, "protocol": "raw", "clock": "clk", "reset": "rst",
                              "sideband": {"kind": kind, "associated_port_id": "port-scheduler-pair_data" if kind == "metadata" else None}})
    node["verification"] = {"kind": "npu_scheduler_stream", "version": 1, "source_job": copy.deepcopy(design["verification_jobs"][0]),
                            "exercise": {"kind": "complete_cancel_restart_v1", "request_ready_pattern": [0, 0, 1, 1],
                                         "pair_ready_pattern": [0, 1, 0, 1, 1], "response_delays": [0, 2, 1, 3],
                                         "cancel_after_pair_transfers": 5, "cancel_states": ["response_pending", "pair_held"], "invalid_k": [0, 17]}}
    return design


SOFTWARE_FIXTURE_RTL = """module hullcirq_scheduler (
 input wire clk, input wire rst,
 input wire [133:0] schedule_config, input wire schedule_config_valid, output wire schedule_config_ready,
 output wire [15:0] read_request, output wire read_request_valid, input wire read_request_ready,
 input wire [15:0] read_response, input wire read_response_valid, output wire read_response_ready,
 output wire [15:0] pair_data, output wire pair_data_valid, input wire pair_data_ready,
 output wire [5:0] pair_meta, output wire pe_clear, output wire schedule_done
);
 localparam IDLE=0, CLEAR=1, ISSUE=2, WAIT=3, EMIT=4, DONE=5;
 reg [2:0] state; reg [4:0] count_k, index_k; reg [3:0] lane; reg [15:0] data;
 wire [5:0] address_a = {lane[3:2],4'b0} + index_k;
 wire [5:0] address_b = {index_k[3:0],2'b0} + lane[1:0];
 assign schedule_config_ready = !rst && state==IDLE && schedule_config[4:0]>=1 && schedule_config[4:0]<=16;
 assign read_request = {2'b0,address_b,2'b0,address_a};
 assign read_request_valid = !rst && state==ISSUE;
 assign read_response_ready = !rst && state==WAIT;
 assign pair_data = data; assign pair_data_valid = !rst && state==EMIT;
 assign pair_meta = {(index_k==count_k-1'b1),(index_k==0),lane};
 assign pe_clear = !rst && state==CLEAR; assign schedule_done = !rst && state==DONE;
 always @(posedge clk) begin
   if (rst) begin state<=IDLE; count_k<=0; index_k<=0; lane<=0; data<=0; end
   else case(state)
    IDLE: if(schedule_config_valid && schedule_config_ready) begin state<=CLEAR; count_k<=schedule_config[4:0]; index_k<=0;lane<=0;data<=0;end
    CLEAR: state<=ISSUE;
    ISSUE: if(read_request_ready) state<=WAIT;
    WAIT: if(read_response_valid) begin data<=read_response;state<=EMIT;end
    EMIT: if(pair_data_ready) begin
      if(index_k+1'b1<count_k) begin index_k<=index_k+1'b1;state<=ISSUE;end
      else if(lane<15) begin lane<=lane+1'b1; index_k<=0;state<=ISSUE;end
      else state<=DONE;
    end
    DONE: state<=IDLE;
    default: state<=IDLE;
   endcase
 end
endmodule
"""


class SchedulerReferenceTests(unittest.TestCase):
    def test_original_job_packing_order_and_metadata(self):
        design = scheduler_design()
        plan = build_verification_plan(design, "node-scheduler")
        job = design["verification_jobs"][0]
        config = pack_configuration(job)
        self.assertEqual(config & 31, 4)
        self.assertEqual((config >> 5) & 1, int(job["relu"]))
        self.assertEqual([(config >> (6 + 32 * index)) & 0xFFFFFFFF for index in range(4)], [v & 0xFFFFFFFF for v in job["bias"]])
        complete_start = max(item["cycle"] for item in plan["reference_trace"] if item["config_transfer"])
        completed = [item for item in plan["reference_trace"] if item["cycle"] >= complete_start]
        requests = [item["before"]["read_request"] for item in completed if item["request_transfer"]]
        pairs = [item for item in completed if item["pair_transfer"]]
        self.assertEqual(len(requests), 64)
        self.assertEqual(requests[:8], [0, 0x401, 0x802, 0xC03, 0x100, 0x501, 0x902, 0xD03])
        self.assertEqual(requests[-4:], [0x330, 0x731, 0xB32, 0xF33])
        self.assertEqual([item["before"]["pair_meta"] for item in pairs[:8]], [16, 0, 0, 32, 17, 1, 1, 33])
        self.assertEqual([item["before"]["pair_data"] for item in pairs[:4]], [0x8080, 0x05FD, 0x0300, 0x807F])
        for lane in range(16):
            for index in range(4):
                pair = pairs[lane * 4 + index]
                self.assertEqual(pair["before"]["pair_data"], (job["A"][lane // 4][index] & 255) | (job["B"][index][lane % 4] & 255) << 8)
        validate_plan(plan)

    def test_saved_recipe_checks_stalls_two_reset_cancellations_and_only_one_completion(self):
        plan = build_verification_plan(scheduler_design(), "node-scheduler")
        self.assertLess(plan["vector_count"], 600)
        coverage = plan["coverage"]
        self.assertEqual(coverage["config_transfers"], 3)
        self.assertEqual(coverage["clear_pulses"], 3)
        self.assertEqual(coverage["done_pulses"], 1)
        self.assertEqual(coverage["reset_with_response_pending"], 1)
        self.assertEqual(coverage["reset_with_pair_held"], 1)
        self.assertEqual(coverage["invalid_config_cycles"], 4)
        self.assertGreater(coverage["busy_config_cycles"], 0)
        self.assertGreater(coverage["request_stall_cycles"], 0)
        self.assertGreater(coverage["pair_stall_cycles"], 0)
        for item in plan["reference_trace"]:
            if item["stimulus"]["reset"]:
                self.assertFalse(any(item[key] for key in ("config_transfer", "request_transfer", "response_transfer", "pair_transfer")))
            if item["before"]["pair_data_valid"] and not item["stimulus"]["pair_ready"]:
                self.assertEqual((item["before"]["pair_data"], item["before"]["pair_meta"]), (item["after"]["pair_data"], item["after"]["pair_meta"]))

    def test_external_valid_data_never_changes_while_stalled_except_shared_reset(self):
        plan = build_verification_plan(scheduler_design(), "node-scheduler")
        for left, right in zip(plan["reference_trace"], plan["reference_trace"][1:]):
            for valid, data, ready in (("config_valid", "config_data", "schedule_config_ready"), ("response_valid", "response_data", "read_response_ready")):
                if left["stimulus"][valid] and not left["before"][ready] and not left["stimulus"]["reset"]:
                    self.assertEqual(right["stimulus"][data], left["stimulus"][data])
                    self.assertEqual(right["stimulus"][valid], 1)

    def test_inactive_data_omitted_from_s07_asserted_facts(self):
        plan = build_verification_plan(scheduler_design(), "node-scheduler")
        trace = scheduler_asserted_trace(plan)
        self.assertIsNone(trace[0]["asserted_before"])
        for item in trace:
            self.assertNotIn("state_before", item)
            for values in (item["asserted_before"], item["asserted_after"]):
                if values is None:
                    continue
                self.assertEqual("read_request" in values, bool(values["read_request_valid"]))
                self.assertEqual("pair_data" in values, bool(values["pair_data_valid"]))
                self.assertEqual("pair_meta" in values, bool(values["pair_data_valid"]))

    def test_duplicate_source_id_mismatch_and_unsupported_recipe_rejected(self):
        for change in (lambda d: d["verification_jobs"].append(copy.deepcopy(d["verification_jobs"][0])),
                       lambda d: d["verification_jobs"][0]["A"][0].__setitem__(0, -127),
                       lambda d: d["nodes"][2]["verification"]["exercise"].update(response_delays=[0]),
                       lambda d: d["nodes"][2]["verification"]["exercise"].update(cancel_after_pair_transfers=64),
                       lambda d: d["nodes"][2]["verification"]["source_job"]["A"][0].__setitem__(0, True)):
            design = scheduler_design(); change(design)
            with self.subTest(change=change), self.assertRaises(DomainError):
                build_verification_plan(design, "node-scheduler")

    def test_checksum_updated_vector_reference_and_testbench_tampering_rejected(self):
        original = build_verification_plan(scheduler_design(), "node-scheduler")
        for field in ("expanded_vectors", "reference_trace", "testbench", "coverage"):
            plan = copy.deepcopy(original)
            if field == "expanded_vectors":
                plan[field][10]["pair_ready"] ^= 1; plan["vector_hash"] = object_hash(plan[field])
            elif field == "reference_trace":
                plan[field][10]["after"]["pair_meta"] ^= 1; plan["reference_trace_hash"] = object_hash(plan[field])
            elif field == "testbench":
                plan[field] += "// stage-only replacement\n"; plan["testbench_sha256"] = content_hash(plan[field])
            else:
                plan[field]["done_pulses"] = 2
            with self.subTest(field=field), self.assertRaises(DomainError):
                validate_plan(plan)

    def test_metadata_association_and_pulse_kind_cannot_be_substituted(self):
        for name, update in (("pair_meta", {"associated_port_id": "port-scheduler-read_request"}),
                             ("pe_clear", {"kind": "metadata", "associated_port_id": "port-scheduler-pair_data"})):
            design = scheduler_design()
            node = next(node for node in design["nodes"] if node["id"] == "node-scheduler")
            next(port for port in node["ports"] if port["name"] == name)["sideband"].update(update)
            with self.subTest(name=name), self.assertRaises(DomainError):
                build_verification_plan(design, "node-scheduler")

    def test_historical_pe_plan_preserved_exactly(self):
        source = PROJECT / "results" / "npu_pe_continuous_flow"
        plan = json.loads((source / "verification_plan.json").read_text(encoding="utf-8"))
        design = json.loads((source / "design.json").read_text(encoding="utf-8"))
        from hullcirq.verification import verification_template_version
        self.assertEqual(build_verification_plan(design, "node-pe", verification_template_version(plan)), plan)
        validate_plan(plan)


class SchedulerActualToolQaTests(unittest.TestCase):
    def setUp(self):
        config = PROJECT / ".work" / "m2" / "compiler.json"
        if not config.exists():
            self.skipTest("Existing isolated trusted Icarus runtime is unavailable.")
        self.compiler = json.loads(config.read_text(encoding="utf-8-sig"))
        self.plan = build_verification_plan(scheduler_design(), "node-scheduler")

    def test_positive_fixture_runs_actual_icarus(self):
        result = verify_behavior(SOFTWARE_FIXTURE_RTL, self.plan, self.compiler, PROJECT / ".work" / "scheduler-software-qa")
        self.assertEqual(result["validation_status"], "Passed", result["stdout"] + result["stderr"])
        self.assertTrue(result["executed"])

    def test_address_metadata_extra_completion_and_reset_faults_fail_actual_assertions(self):
        changes = (("{2'b0,address_b,2'b0,address_a}", "{2'b0,address_b,2'b0,address_a}+1'b1", "read_request"),
                   ("(index_k==0),lane", "(index_k==0),4'b0", "pair_meta"),
                   ("!rst && state==DONE", "!rst && (state==DONE || state==EMIT)", "schedule_done"),
                   ("!rst && state==EMIT", "state==EMIT", "pair_data_valid"))
        for old, new, signal in changes:
            with self.subTest(signal=signal):
                result = verify_behavior(SOFTWARE_FIXTURE_RTL.replace(old, new), self.plan, self.compiler, PROJECT / ".work" / "scheduler-software-qa")
                self.assertEqual(result["validation_status"], "Failed", result["stdout"])
                self.assertIn("signal=" + signal, result["stdout"])
                self.assertEqual(result["exit_code"], 0)  # Assertions, not exit code alone, determine adoption.


if __name__ == "__main__":
    unittest.main()

"""Software QA only; handwritten fault fixtures are never actual model RTL."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from prepare_control_contract import build_control_node
from hullcirq.control_verification import (TEMPLATE, build_control_plan, control_asserted_trace,
                                           control_reference_trace, expand_vectors, validate_control_plan)
from hullcirq.domain import DomainError
from hullcirq.scheduler_verification import pack_configuration
from hullcirq.verification import content_hash, object_hash, verify_behavior


def control_design():
    design = json.loads((ROOT / "examples/npu_project.json").read_text(encoding="utf-8"))
    node = build_control_node(design)
    design["nodes"] = [node if original["id"] == node["id"] else original for original in design["nodes"]]
    return design


SOFTWARE_FIXTURE_RTL = """module hullcirq_control (
 input wire clk, input wire rst,
 input wire [133:0] config_data, input wire config_data_valid, output wire config_data_ready,
 output wire [133:0] schedule_config, output wire schedule_config_valid, input wire schedule_config_ready,
 output wire [128:0] post_config, output wire post_config_valid, input wire post_config_ready,
 input wire output_transfer, output wire busy, output wire job_done
);
 localparam IDLE=0,SEND_CONFIG=1,RUN=2,DONE=3;
 reg [1:0] state; reg [133:0] saved; reg schedule_sent,post_sent; reg [4:0] count;
 wire schedule_take = schedule_config_valid && schedule_config_ready;
 wire post_take = post_config_valid && post_config_ready;
 assign config_data_ready = !rst && state==IDLE && config_data[4:0]>=1 && config_data[4:0]<=16;
 assign schedule_config=saved; assign post_config={saved[133:6],saved[5]};
 assign schedule_config_valid=!rst && state==SEND_CONFIG && !schedule_sent;
 assign post_config_valid=!rst && state==SEND_CONFIG && !post_sent;
 assign busy=!rst && state!=IDLE; assign job_done=!rst && state==DONE;
 always @(posedge clk) begin
  if(rst) begin state<=IDLE;saved<=0;schedule_sent<=0;post_sent<=0;count<=0;end
  else case(state)
   IDLE: if(config_data_valid && config_data_ready) begin
    state<=SEND_CONFIG;saved<=config_data;schedule_sent<=0;post_sent<=0;count<=0;
   end
   SEND_CONFIG: begin
    if(schedule_take) schedule_sent<=1;
    if(post_take) post_sent<=1;
    if((schedule_sent || schedule_take) && (post_sent || post_take)) state<=RUN;
   end
   RUN: if(output_transfer) begin count<=count+1'b1; if(count==15) state<=DONE; end
   DONE: state<=IDLE;
   default: state<=IDLE;
  endcase
 end
endmodule
"""


class ControlReferenceTests(unittest.TestCase):
    def setUp(self):
        self.design = control_design()
        self.plan = build_control_plan(self.design, "node-control")

    def test_proposal_preserves_original_job_other_nodes_and_three_streams(self):
        source = json.loads((ROOT / "examples/npu_project.json").read_text(encoding="utf-8"))
        before = object_hash(source)
        node = build_control_node(source)
        self.assertEqual(object_hash(source), before)
        self.assertEqual(object_hash(node["verification"]["source_job"]), object_hash(source["verification_jobs"][0]))
        self.assertEqual(node["ports"][:3], source["nodes"][0]["ports"])
        self.assertEqual([(p["name"], p["direction"], p["sideband"]["kind"], p["sideband"]["associated_port_id"])
                          for p in node["ports"][3:]], [("output_transfer", "input", "pulse", None), ("busy", "output", "level", None), ("job_done", "output", "pulse", None)])
        self.assertIn("actual final FIFO output valid&&ready", node["behavior"])

    def test_configuration_packing_and_each_independent_sink_handshake(self):
        config = pack_configuration(self.design["verification_jobs"][0])
        post = (config >> 6) << 1 | ((config >> 5) & 1)
        self.assertGreater(config.bit_length(), 130)
        trace = self.plan["reference_trace"]
        for item in trace:
            if item["schedule_transfer"]:
                self.assertEqual(item["before"]["schedule_config"], config)
            if item["post_transfer"]:
                self.assertEqual(item["before"]["post_config"], post)
        config_cycles = [item["cycle"] for item in trace if item["config_transfer"]]
        self.assertEqual(len(config_cycles), 2)
        orders = []
        for index, first in enumerate(config_cycles):
            end = config_cycles[index + 1] if index + 1 < len(config_cycles) else len(trace)
            schedule = [item["cycle"] for item in trace[first:end] if item["schedule_transfer"]]
            downstream = [item["cycle"] for item in trace[first:end] if item["post_transfer"]]
            self.assertEqual((len(schedule), len(downstream)), (1, 1))
            orders.append(schedule[0] < downstream[0])
        self.assertEqual(orders, [False, True])

    def test_cancellation_and_exact_16_output_completion_use_same_original_job(self):
        coverage = self.plan["coverage"]
        self.assertLess(self.plan["vector_count"], 100)
        self.assertEqual((coverage["config_transfers"], coverage["schedule_transfers"], coverage["post_transfers"]), (2, 2, 2))
        self.assertEqual(coverage["output_transfers"], 21)
        self.assertEqual(coverage["reset_with_partial_outputs"], 1)
        self.assertEqual(coverage["done_pulses"], 1)
        self.assertEqual(coverage["invalid_config_cycles"], 4)
        self.assertGreater(coverage["busy_config_cycles"], 0)
        self.assertGreater(coverage["schedule_stall_cycles"], 0)
        self.assertGreater(coverage["post_stall_cycles"], 0)
        self.assertGreater(coverage["ignored_output_pulses"], 0)
        config = pack_configuration(self.design["verification_jobs"][0])
        for item in self.plan["reference_trace"]:
            vector = item["stimulus"]
            if vector["config_valid"] and (vector["config_data"] & 31) in (0, 17):
                self.assertEqual(vector["config_data"] & ~31, config & ~31)
            if item["state_before"] == "SEND_CONFIG" and item["state_after"] == "RUN":
                self.assertEqual(item["completed_outputs_after"], 0)
                self.assertEqual(item["output_transfer"], 0)
            if item["after"]["job_done"]:
                self.assertEqual(item["completed_outputs_after"], 16)
            if vector["reset"]:
                self.assertFalse(any(item["before"][key] or item["after"][key] for key in ("config_data_ready", "schedule_config_valid", "post_config_valid", "busy", "job_done")))
                self.assertEqual(item["completed_outputs_after"], 0)

    def test_config_sources_and_sink_data_hold_during_stalls_until_handshake_or_reset(self):
        trace = self.plan["reference_trace"]
        for left, right in zip(trace, trace[1:]):
            if left["stimulus"]["config_valid"] and not left["before"]["config_data_ready"] and not left["stimulus"]["reset"]:
                self.assertEqual(right["stimulus"]["config_data"], left["stimulus"]["config_data"])
                self.assertEqual(right["stimulus"]["config_valid"], 1)
            for stream, ready in (("schedule_config", "schedule_ready"), ("post_config", "post_ready")):
                if left["before"][stream + "_valid"] and not left["stimulus"][ready]:
                    self.assertEqual(left["before"][stream], left["after"][stream])
                    self.assertEqual(left["after"][stream + "_valid"], 1)

    def test_s07_asserted_facts_omit_inactive_data_and_internal_state(self):
        trace = control_asserted_trace(self.plan)
        self.assertIsNone(trace[0]["asserted_before"])
        for item in trace:
            self.assertNotIn("state_before", item)
            self.assertNotIn("completed_outputs_before", item)
            for phase in ("asserted_before", "asserted_after"):
                values = item[phase]
                if values is not None:
                    self.assertEqual("schedule_config" in values, bool(values["schedule_config_valid"]))
                    self.assertEqual("post_config" in values, bool(values["post_config_valid"]))
        self.assertIn("actual final FIFO", " ".join(self.plan["limits"]))

    def test_duplicate_mismatched_and_wrong_type_source_jobs_are_rejected(self):
        changes = (lambda d: d["verification_jobs"].append(copy.deepcopy(d["verification_jobs"][0])),
                   lambda d: d["verification_jobs"][0]["bias"].__setitem__(0, 1),
                   lambda d: d["verification_jobs"][0].update(k=4.0),
                   lambda d: d["nodes"][0]["verification"]["source_job"]["bias"].__setitem__(0, False),
                   lambda d: d["nodes"][0]["verification"]["exercise"].update(replacement_vectors=[]))
        for change in changes:
            design = copy.deepcopy(self.design); change(design)
            with self.subTest(change=change), self.assertRaises(DomainError):
                build_control_plan(design, "node-control")

    def test_interface_width_kind_association_and_protocol_changes_are_rejected(self):
        changes = (("busy", {"kind": "pulse"}), ("output_transfer", {"associated_port_id": "port-control-config_data"}))
        for name, update in changes:
            design = copy.deepcopy(self.design)
            next(p for p in design["nodes"][0]["ports"] if p["name"] == name)["sideband"].update(update)
            with self.subTest(name=name), self.assertRaises(DomainError):
                build_control_plan(design, "node-control")
        design = copy.deepcopy(self.design); design["nodes"][0]["ports"][2]["width"] = 128
        with self.assertRaises(DomainError):
            build_control_plan(design, "node-control")

    def test_reset_mode_and_logical_clock_domains_cannot_disagree_with_frozen_contract(self):
        for setting, value in (("reset_active", "low"), ("reset_kind", "asynchronous"), ("clock_name", "other_clock")):
            design = copy.deepcopy(self.design); design["settings"][setting] = value
            with self.subTest(setting=setting), self.assertRaises(DomainError):
                build_control_plan(design, "node-control")
        design = copy.deepcopy(self.design)
        next(port for port in design["nodes"][0]["ports"] if port["name"] == "busy")["clock"] = "other_clock"
        with self.assertRaises(DomainError):
            build_control_plan(design, "node-control")

    def test_frozen_plan_rejects_checksum_updated_vectors_trace_and_numeric_type_changes(self):
        validate_control_plan(self.plan)
        for field in ("expanded_vectors", "reference_trace", "testbench", "coverage", "version", "vector_count"):
            plan = copy.deepcopy(self.plan)
            if field == "expanded_vectors":
                plan[field][0]["reset"] = 1.0; plan["vector_hash"] = object_hash(plan[field])
            elif field == "reference_trace":
                plan[field][0]["after"]["job_done"] = False; plan["reference_trace_hash"] = object_hash(plan[field])
            elif field == "testbench":
                plan[field] += "// stage-only replacement\n"; plan["testbench_sha256"] = content_hash(plan[field])
            elif field == "coverage":
                plan[field]["done_pulses"] = 1.0
            elif field == "version":
                plan[field] = True
            else:
                plan[field] = float(plan[field])
            with self.subTest(field=field), self.assertRaises(DomainError):
                validate_control_plan(plan)

    def test_raw_pulse_projection_requires_exact_integer_types(self):
        vectors = expand_vectors(self.plan["contract"])
        for field, value in (("reset", True), ("output_transfer", 1.0), ("config_data", 1 << 134)):
            altered = copy.deepcopy(vectors); altered[0][field] = value
            with self.subTest(field=field), self.assertRaises(DomainError):
                control_reference_trace(altered)


class ControlActualToolQATests(unittest.TestCase):
    def setUp(self):
        configuration = ROOT / ".work/m2/compiler.json"
        if not configuration.is_file():
            self.skipTest("Existing isolated trusted Icarus runtime is unavailable.")
        self.compiler = json.loads(configuration.read_text(encoding="utf-8-sig"))
        self.plan = build_control_plan(control_design(), "node-control")

    def check(self, rtl):
        return verify_behavior(rtl, self.plan, self.compiler, ROOT / ".work/control-software-qa")

    def test_positive_software_fixture_runs_the_actual_trusted_icarus(self):
        result = self.check(SOFTWARE_FIXTURE_RTL)
        self.assertTrue(result["executed"])
        self.assertEqual(result["validation_status"], "Passed", result["stdout"] + result["stderr"])

    def test_premature_done_duplicate_config_bad_post_packing_and_reset_faults_fail(self):
        changes = (("if(count==15)", "if(count==14)", "job_done"),
                   ("&& !post_sent", "", "post_config_valid"),
                   ("{saved[133:6],saved[5]}", "{saved[133:6],~saved[5]}", "post_config"),
                   ("!rst && state!=IDLE", "state!=IDLE", "busy"),
                   ("count<=0;", "count<=5;", "job_done"))
        for old, new, signal in changes:
            with self.subTest(signal=signal, change=old):
                self.assertIn(old, SOFTWARE_FIXTURE_RTL)
                result = self.check(SOFTWARE_FIXTURE_RTL.replace(old, new))
                self.assertEqual(result["validation_status"], "Failed", result["stdout"])
                self.assertIn("signal=" + signal, result["stdout"])
                self.assertEqual(result["exit_code"], 0)


if __name__ == "__main__":
    unittest.main()

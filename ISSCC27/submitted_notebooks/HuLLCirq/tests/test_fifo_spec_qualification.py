"""Qualify the saved-spec FIFO checker with software fixtures, not project RTL.

The stimulus stays derived from the original saved matrix job.  The independent
FIFO implementation below and its intentional faults are test equipment only;
none is a candidate, acceptance record, or evidence for the actual NPU.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import time
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from hullcirq.verification import build_verification_plan, content_hash, object_hash, verify_behavior

SYSTEM = PROJECT / ".work/projects/npu_2x2_explicit/systems/system-7df07952c6b64696813d14ab19837af8"


def source_design():
    """Use saved input if available; the tracked canonical example is portable."""
    saved = SYSTEM / "state.json"
    if saved.exists():
        return json.loads(saved.read_text(encoding="utf-8"))["design"]
    return json.loads((PROJECT / "examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))


FIFO_FIXTURE = """// Software qualification fixture; not generated or adopted project RTL.
module hullcirq_npu2_fifo (
 input wire clk, input wire rst,
 input wire signed [31:0] result_data,
 input wire result_data_valid, output wire result_data_ready,
 output wire signed [31:0] output_data,
 output wire output_data_valid, input wire output_data_ready,
 output wire output_transfer
);
 reg signed [31:0] memory [0:1];
 reg read_pointer, write_pointer;
 reg [1:0] count;
 wire pop = output_data_valid && output_data_ready;
 wire push = result_data_valid && result_data_ready;
 assign result_data_ready = !rst && ((count < 2) || pop);
 assign output_data_valid = !rst && (count != 0);
 assign output_data = memory[read_pointer];
 assign output_transfer = pop;
 always @(posedge clk) begin
  if (rst) begin
   read_pointer <= 0; write_pointer <= 0; count <= 0;
  end else begin
   if (push) begin memory[write_pointer] <= result_data; write_pointer <= !write_pointer; end
   if (pop) read_pointer <= !read_pointer;
   case ({push,pop})
    2'b10: count <= count + 1'b1;
    2'b01: count <= count - 1'b1;
    default: count <= count;
   endcase
  end
 end
endmodule
"""


def fixture_cases():
    """Single faults with distinct externally observable contract violations."""
    reset_fault = FIFO_FIXTURE.replace(
        "reg [1:0] count;", "reg [1:0] count; reg reset_seen; initial reset_seen = 0;"
    ).replace("count <= 0;", "count <= reset_seen ? count : 0; reset_seen <= 1;")
    consecutive_fault = FIFO_FIXTURE.replace(
        "reg [1:0] count;", "reg [1:0] count; reg last_pop;"
    ).replace("assign output_transfer = pop;", "assign output_transfer = pop && !last_pop;"
    ).replace("count <= 0;", "count <= 0; last_pop <= 0;"
    ).replace("end else begin\n", "end else begin\n   last_pop <= pop;\n", 1)
    return {
        "correct_fifo": (FIFO_FIXTURE, "Passed", "Independent two-entry circular queue"),
        "undriven_output_data": (FIFO_FIXTURE.replace("assign output_data = memory[read_pointer];", ""), "Failed", "No driver on the externally visible payload"),
        "wrong_output_order": (FIFO_FIXTURE.replace("memory[read_pointer];", "memory[!write_pointer];"), "Failed", "Reads the most recently written payload instead of the oldest accepted head"),
        "full_pop_push_refused": (FIFO_FIXTURE.replace("((count < 2) || pop)", "(count < 2)"), "Failed", "Refuses an input when a full queue is popped in the same cycle"),
        "stalled_head_corrupted": (FIFO_FIXTURE.replace("assign output_data = memory[read_pointer];", "assign output_data = (output_data_valid && !output_data_ready) ? memory[read_pointer] ^ 32'h1 : memory[read_pointer];"), "Failed", "Changes the visible head under output backpressure"),
        "reset_keeps_pending_queue": (reset_fault, "Failed", "Initial reset works; later reset leaves the pending count nonzero"),
        "asynchronous_reset_clears_early": (FIFO_FIXTURE.replace("always @(posedge clk)", "always @(posedge clk or posedge rst)"), "Failed", "An off-clock reset pulse wrongly clears the queue before a synchronous reset edge"),
        "consecutive_transfer_suppressed": (consecutive_fault, "Failed", "Suppresses the second of consecutive real output transfers"),
        "empty_combinational_bypass": (FIFO_FIXTURE.replace("!rst && (count != 0)", "!rst && ((count != 0) || result_data_valid)"), "Failed", "Asserts output valid on an empty input offer before the clock edge"),
        "write_pointer_never_wraps": (FIFO_FIXTURE.replace("write_pointer <= !write_pointer;", "write_pointer <= 0;"), "Failed", "Always writes slot zero, corrupting order and wrap behavior"),
    }


def run_qualification(archive_directory=None):
    """Run the bounded fixture matrix with the already configured compiler."""
    compiler = json.loads((PROJECT / ".work/m2/compiler.json").read_text(encoding="utf-8-sig"))
    design = source_design()
    plan = build_verification_plan(design, "npu2-fifo")
    archive = Path(archive_directory) if archive_directory else None
    if archive:
        archive.mkdir(parents=True, exist_ok=True)
        (archive / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (archive / "contract_tb.v").write_text(plan["testbench"], encoding="utf-8")
    report = {
        "scope": "software_checker_qualification_only_not_actual_project_verification",
        "source_design_sha256": object_hash(design),
        "source_job": copy.deepcopy(design["verification_jobs"][0]),
        "fixture_origin": "development_assistant_authored_independent_fifo_and_single_fault_mutants",
        "stimulus_origin": plan["stimulus_origin"],
        "vector_hash": plan["vector_hash"],
        "testbench_sha256": plan["testbench_sha256"],
        "vector_count": plan["vector_count"],
        "compiler_config": compiler,
        "project_mutation": False,
        "cases": [],
    }
    started = time.monotonic()
    for name, (rtl, expected, fault) in fixture_cases().items():
        result = verify_behavior(rtl, plan, compiler, PROJECT / ".work/fifo-spec-qualification")
        actual = result["validation_status"]
        assertion_seen = "HULLCIRQ_FAIL" in result["stdout"] if expected == "Failed" else "HULLCIRQ_PASS" in result["stdout"]
        report["cases"].append({"case": name, "expected": expected, "actual": actual, "fault": fault,
                                "qualified": actual == expected and assertion_seen,
                                "rtl_sha256": content_hash(rtl), "result": result})
        if archive:
            (archive / (name + ".v")).write_text(rtl, encoding="utf-8")
            (archive / (name + ".json")).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report["elapsed_seconds"] = time.monotonic() - started
    report["qualified"] = all(case["qualified"] for case in report["cases"])
    if archive:
        (archive / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


class FifoSpecQualificationTests(unittest.TestCase):
    def test_original_saved_payloads_and_boundary_conditions_are_present(self):
        design = source_design()
        before = copy.deepcopy(design)
        plan = build_verification_plan(design, "npu2-fifo")
        self.assertEqual(design, before)
        vectors = plan["expanded_vectors"]
        offered = [item["result_data"] for item in vectors if item["result_data_valid"]]
        # Independently evaluated from the exact original A/B/bias job, not DUT.
        self.assertEqual(set(value & 0xffffffff for value in offered), {(-44) & 0xffffffff, 56, 59, 9})
        self.assertLess(len(vectors), 128)
        self.assertGreater(sum(bool(v["reset"]) for v in vectors), 1)
        self.assertEqual(sum(v["reset_pulse_without_clock"] for v in vectors), 1)
        self.assertTrue(any(v["result_data_valid"] and not v["output_data_ready"] for v in vectors))
        trace = plan["reference_trace"]
        serialized = json.dumps(trace)
        self.assertNotIn("dut", serialized.lower())
        self.assertIn("output_transfer", plan["testbench"])
        self.assertIn("!==", plan["testbench"])

    def test_fixture_positive_and_mutants_with_actual_existing_icarus(self):
        if not (PROJECT / ".work/m2/compiler.json").exists():
            self.skipTest("Existing trusted Icarus runtime is not configured.")
        report = run_qualification()
        for case in report["cases"]:
            with self.subTest(case=case["case"]):
                self.assertTrue(case["qualified"], case["result"]["stdout"] + case["result"]["stderr"])


if __name__ == "__main__":
    unittest.main()

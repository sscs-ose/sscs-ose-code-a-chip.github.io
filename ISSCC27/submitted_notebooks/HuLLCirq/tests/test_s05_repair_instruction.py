"""Source-derived repair guidance QA; no model, EDA or live store writes."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hullcirq.generation_batches import synthesis_repair_evidence, synthesis_repair_instruction
from hullcirq.repair_guidance import actionable_diagnostics, build_repair_guidance, compare_attempt, render_repair_instruction, with_prompt_projection
from hullcirq.verification import object_hash


def failed_run(stdout="Warning: multiple conflicting drivers for module.\\busy:\n port Q of cell A\n port Y of cell B\n"):
    return {"id": "software-run", "stage_id": "local_synthesis", "candidate_id": "software-candidate",
            "input_hash": "source", "tool_configuration": {}, "diagnostics": [],
            "checks": {"executed": True, "exit_code": 1, "stdout": stdout,
                       "stderr": "ERROR: Found 1 problems in 'check -assert'.\n"}}


class RepairInstructionTests(unittest.TestCase):
    def test_actual_assignment_lines_and_single_owner_guidance_are_included(self):
        rtl = "module module(output wire busy);\nassign busy = active;\nalways @(posedge clk) begin\n busy <= 1'b0;\nend\nendmodule\n"
        run = failed_run()
        original = copy.deepcopy(run)
        instruction = synthesis_repair_instruction(run, rtl)
        self.assertIn("S05 repair instruction v4", instruction)
        self.assertIn("busy <= at lines 4; assign busy at lines 2", instruction)
        self.assertIn("exactly one output driver", instruction)
        self.assertIn("Keep output wire", instruction)
        self.assertIn("only if allowed by the required header", instruction)
        self.assertIn("lexical evidence; confirm in RTL", instruction)
        self.assertLess(instruction.index("Driver correction"), instruction.index("S05 source evidence:"))
        self.assertIn("check -assert", instruction)
        self.assertIn(synthesis_repair_evidence(run)["full_record_sha256"], instruction)
        self.assertEqual(run, original)

    def test_comments_strings_and_comparisons_do_not_supply_assignment_evidence(self):
        rtl = '''module module(output wire busy);
// busy <= 1'b0;
/*
busy <= 1'b1;
*/
localparam TEXT = "busy <= something";
assign busy = active;
always @(posedge clk) if (busy <= value) active <= 0;
endmodule
'''
        instruction = synthesis_repair_instruction(failed_run(), rtl)
        self.assertNotIn("Driver correction", instruction)

    def test_source_overlap_without_tool_diagnosis_is_not_inferred_as_the_failure(self):
        rtl = "assign busy = active;\nbusy <= 1'b0;\n"
        instruction = synthesis_repair_instruction(failed_run("ERROR: syntax error at candidate.v:8\n"), rtl)
        self.assertNotIn("Driver correction", instruction)
        self.assertIn("syntax error", instruction)

    def test_final_check_signal_takes_precedence_over_preliminary_conflicts(self):
        output = ("2.1. Executing CHECK pass (checking for obvious problems).\n"
                  "Warning: multiple conflicting drivers for module.\\job_done:\n old drivers\n"
                  "3. Executing CHECK pass (checking for obvious problems).\n"
                  "Warning: multiple conflicting drivers for module.\\busy:\n final drivers\n")
        rtl = "assign job_done = done;\njob_done <= 0;\nassign busy = active;\nbusy <= 0;\n"
        instruction = synthesis_repair_instruction(failed_run(output), rtl)
        guidance = instruction.split("Driver correction", 1)[1].split("S05 source evidence:", 1)[0]
        self.assertIn("busy <= at lines 4; assign busy at lines 3", guidance)
        self.assertNotIn("job_done", guidance)

    def test_full_human_instruction_is_appended_exactly_and_original_evidence_unchanged(self):
        note = "  Keep these precise instructions.\nInspect both output drivers.  "
        run = failed_run()
        v2 = synthesis_repair_evidence(run, "s05-repair-diagnostics-v2")
        v3 = synthesis_repair_evidence(run)
        instruction = synthesis_repair_instruction(run, "assign busy = active;\nbusy <= 0;\n", note)
        self.assertTrue(instruction.endswith("Additional requested correction:\n" + note))
        self.assertEqual(synthesis_repair_evidence(run, "s05-repair-diagnostics-v2"), v2)
        self.assertEqual(synthesis_repair_evidence(run), v3)
        self.assertIn('"projection_version":"s05-repair-diagnostics-v3"', instruction)

    def test_missing_rtl_and_unsupported_identifier_forms_do_not_invent_guidance(self):
        for rtl in (None, "assign busy[0] = active;\nbusy[0] <= 0;\n", "assign \\busy = active;\n\\busy <= 0;\n"):
            with self.subTest(rtl=rtl):
                self.assertNotIn("Driver correction", synthesis_repair_instruction(failed_run(), rtl))


class GeneralizedRepairTests(unittest.TestCase):
    def source(self, rtl, error, specification="Saved reset behavior", name="arbitrary"):
        design = {"nodes": [{"id": name, "behavior": specification}], "edges": [], "settings": {"reset_kind": "synchronous"}}
        job = {"id": "candidate", "node_id": name, "revision_id": "revision", "rtl": rtl, "operation": "generate"}
        run = failed_run("")
        run.update(node_id=name, candidate_id="candidate", execution_status="Completed", validation_status="Failed")
        run["checks"]["stderr"] = error
        return design, job, run

    def test_retained_storage_rule_is_spec_derived_and_never_clears_bank(self):
        rtl = "module a;\nreg [7:0] memory [0:15];\nalways @(posedge clk) if (rst) begin\n memory <= 0;\nend\nendmodule\n"
        design, job, run = self.source(rtl, "candidate.v:4: ERROR: Invalid array access.\n", "Synchronous reset cancels response but retains memory bytes.")
        original = copy.deepcopy((design, job, run))
        guidance = build_repair_guidance(design, run, job)
        self.assertFalse(guidance["analysis_required"])
        self.assertEqual(guidance["changes"][0]["rule_id"], "unpacked_array_assignment")
        instruction = render_repair_instruction(guidance)
        self.assertIn("do not replace them with a loop clearing storage", instruction)
        self.assertIn("memory", instruction)
        self.assertEqual((design, job, run), original)

    def test_array_pattern_uses_same_contract_aware_rule(self):
        rtl = "module a;\nreg [31:0] queue [0:1];\nalways @(posedge clk) if (rst) begin\n queue <= '{default:32'b0};\nend\nendmodule\n"
        design, job, run = self.source(rtl, "candidate.v:4: ERROR: syntax error, unexpected OP_CAST\n", "Reset empties the queue; need not clear storage bits.")
        guidance = build_repair_guidance(design, run, job)
        self.assertFalse(guidance["analysis_required"])
        self.assertEqual(guidance["changes"][0]["confidence"], "confirmed")

    def test_same_reset_branch_sibling_arrays_are_included_without_hardcoded_names(self):
        rtl = "module a;\nreg [7:0] left [0:15];\nreg [7:0] right [0:15];\nalways @(posedge clk) if (rst) begin\n left <= 0;\n right <= 0;\nend\nendmodule\n"
        design, job, run = self.source(rtl, "candidate.v:5: ERROR: Invalid array access\n", "Synchronous reset retains all stored bank bytes.")
        design["settings"]["reset_name"] = "rst"
        guidance = build_repair_guidance(design, run, job)
        self.assertEqual([item["line"] for item in guidance["changes"][0]["locations"]], [5, 6])
        self.assertIn("left, right", render_repair_instruction(guidance))

    def test_retaining_unrelated_state_does_not_imply_retaining_array_bytes(self):
        rtl = "reg [7:0] bank [0:3];\nbank <= 0;\n"
        design, job, run = self.source(rtl, "candidate.v:2: ERROR: Invalid array access\n", "Reset retains valid flags but clears bank bytes.")
        guidance = build_repair_guidance(design, run, job)
        self.assertTrue(guidance["analysis_required"])
        self.assertEqual(guidance["changes"][0]["confidence"], "hypothesis")

    def test_typed_unnamed_block_declaration_has_source_bound_guidance(self):
        rtl = "module a;\nalways @(posedge clk) begin\nreg signed [31:0] temporary;\nend\nendmodule\n"
        design, job, run = self.source(rtl, "candidate.v:3: ERROR: Local declaration in unnamed block is only supported in SystemVerilog mode!\n")
        guidance = build_repair_guidance(design, run, job)
        self.assertFalse(guidance["analysis_required"])
        self.assertEqual(guidance["changes"][0]["rule_id"], "block_local_typed_declaration")

    def test_uncertain_array_reset_never_invents_retention_fact(self):
        rtl = "reg [31:0] array [0:1];\narray <= 0;\n"
        design, job, run = self.source(rtl, "candidate.v:2: ERROR: Invalid array access\n", "Reset must initialize entries to seven.")
        guidance = build_repair_guidance(design, run, job)
        self.assertEqual(guidance["changes"][0]["confidence"], "hypothesis")
        self.assertTrue(guidance["changes"][0]["assumptions"])
        self.assertNotIn("retains storage", " ".join(guidance["changes"][0]["facts"]))

    def test_signed_rule_has_actual_anchor_and_preserves_semantics(self):
        rtl = "module a;\nalways @(posedge clk) begin\n signed [31:0] result;\nend\nendmodule\n"
        design, job, run = self.source(rtl, "candidate.v:3: ERROR: syntax error, unexpected TOK_SIGNED\n", "Apply signed32 wrap before signed ReLU.")
        guidance = build_repair_guidance(design, run, job)
        self.assertFalse(guidance["analysis_required"])
        self.assertEqual(guidance["changes"][0]["locations"][0]["line"], 3)
        self.assertIn("module scope", render_repair_instruction(guidance))
        self.assertIn("signed ReLU", guidance["original_requirements"]["node"]["behavior"])

    def test_commented_declaration_is_not_supported_evidence(self):
        design, job, run = self.source("// signed [31:0] result;\n", "candidate.v:1: ERROR: unexpected TOK_SIGNED\n")
        guidance = build_repair_guidance(design, run, job)
        self.assertTrue(guidance["analysis_required"])
        self.assertEqual(guidance["changes"], [])

    def test_unknown_analysis_contains_exact_contract_rtl_and_tool_diagnostic(self):
        design, job, run = self.source("module x;\nweird source;\nendmodule\n", "candidate.v:2: ERROR: unsupported unknown construct\n")
        guidance = build_repair_guidance(design, run, job)
        self.assertTrue(guidance["analysis_required"])
        self.assertEqual(guidance["changes"], [])
        self.assertIn("weird source", guidance["analysis_messages"][1]["content"])
        self.assertIn("unsupported unknown construct", guidance["analysis_messages"][1]["content"])
        self.assertEqual(guidance["guidance_sha256"], object_hash({key: value for key, value in guidance.items() if key != "guidance_sha256"}))

    def test_line_path_and_whitespace_changes_do_not_hide_same_issue(self):
        _, _, old = self.source("module x;\nsigned [31:0] result;\n", "C:/one/candidate.v:2: ERROR: unexpected TOK_SIGNED\n")
        _, _, new = self.source("module x;\n// shifted\n signed  [31:0] result;\n", "D:/two/candidate.v:3: ERROR: unexpected TOK_SIGNED\n")
        new["candidate_id"] = "repaired"
        status = compare_attempt(new, "module x;\n// shifted\n signed  [31:0] result;\n", old, "module x;\nsigned [31:0] result;\n")
        self.assertEqual(status["outcome"], "same_diagnostic")
        self.assertTrue(status["reconsideration_required"])

    def test_different_source_targets_are_not_conflated(self):
        rtl = "signed [31:0] first;\nsigned [31:0] second;\n"
        _, _, old = self.source(rtl, "candidate.v:1: ERROR: unexpected TOK_SIGNED\n")
        _, _, new = self.source(rtl + "// repair\n", "candidate.v:2: ERROR: unexpected TOK_SIGNED\n")
        self.assertEqual(compare_attempt(new, rtl + "// repair\n", old, rtl)["outcome"], "new_diagnostic")

    def test_changing_signed_range_does_not_fix_missing_declaration_type(self):
        old_rtl, new_rtl = "signed [31:0] result;\n", "signed [63:0] result;\n"
        _, _, old = self.source(old_rtl, "candidate.v:1: ERROR: unexpected TOK_SIGNED\n")
        _, _, new = self.source(new_rtl, "other.v:1: ERROR: unexpected TOK_SIGNED\n")
        self.assertEqual(compare_attempt(new, new_rtl, old, old_rtl)["outcome"], "same_diagnostic")

    def test_unchanged_source_result_and_config_scope(self):
        _, _, old = self.source("same RTL", "ERROR: bad token\n")
        new = copy.deepcopy(old); new["candidate_id"] = "repair"
        self.assertEqual(compare_attempt(new, "same RTL", old, "same RTL")["outcome"], "unchanged")
        new["tool_configuration"] = {"other": True}
        self.assertEqual(compare_attempt(new, "same RTL", old, "same RTL")["outcome"], "not_comparable")
        new["tool_configuration"] = old["tool_configuration"]; new["node_id"] = "different"
        self.assertEqual(compare_attempt(new, "same RTL", old, "same RTL")["outcome"], "not_comparable")

    def test_passed_notrun_and_no_baseline_are_distinct(self):
        _, _, run = self.source("RTL", "ERROR: bad token\n")
        self.assertEqual(compare_attempt(run, "RTL")["outcome"], "no_baseline")
        run["execution_status"] = "Cancelled"
        self.assertEqual(compare_attempt(run, "RTL")["outcome"], "not_comparable")
        run.update(execution_status="Completed", validation_status="Passed")
        self.assertEqual(compare_attempt(run, "RTL")["outcome"], "passed")

    def test_recent_attempts_keep_full_diff_but_do_not_nest_old_history(self):
        rtl = "signed [31:0] result;\n"
        design, job, run = self.source(rtl, "candidate.v:1: ERROR: unexpected TOK_SIGNED\n")
        old_job = copy.deepcopy(job); old_job["id"] = "base"
        old_run = copy.deepcopy(run); old_run.update(id="base-run", candidate_id="base")
        job.update(operation="repair", base_job_id="base", instruction="Previous precise correction")
        first = build_repair_guidance(design, run, job, [old_job, job], [old_run, run])
        job["context"] = {"batch_context": {"repair_guidance": first}}
        second = build_repair_guidance(design, run, job, [old_job, job], [old_run, run])
        self.assertTrue(second["same_plan_repeated"])
        self.assertEqual(second["recent_attempts"][0]["diff"], "")
        self.assertNotIn("recent_attempts", second["recent_attempts"][0]["previous_guidance"])
        self.assertEqual(second["repeat_status"]["outcome"], "unchanged")

    def test_diff_hunks_are_sent_and_history_is_bounded_with_explicit_hashes(self):
        rtl = "signed [31:0] result;\n"
        design, job, run = self.source(rtl, "candidate.v:1: ERROR: unexpected TOK_SIGNED\n")
        base = copy.deepcopy(job); base.update(id="base", rtl=rtl + "// old source\n")
        job.update(operation="repair", base_job_id="base", instruction="x" * 30000)
        old_run = copy.deepcopy(run); old_run.update(id="old-run", candidate_id="base")
        guidance = build_repair_guidance(design, run, job, [base, job], [old_run, run])
        self.assertEqual(len(guidance["recent_attempts"][0]["instruction"]), 30000)
        self.assertIn("-// old source", render_repair_instruction(guidance))
        self.assertLess(len(guidance["analysis_messages"][1]["content"]), 7000)
        self.assertIn('"omitted_characters":29700', guidance["analysis_messages"][1]["content"])
        compact = with_prompt_projection(guidance, compact=True)
        self.assertEqual(compact["prompt_projection"]["mode"], "compact_history_v1")
        self.assertEqual(compact["recent_attempts"], guidance["recent_attempts"])
        self.assertEqual(compact["original_requirements"], guidance["original_requirements"])
        self.assertLess(len(render_repair_instruction(compact)), len(render_repair_instruction(guidance)))
        self.assertEqual(compact["guidance_sha256"], object_hash({key: value for key, value in compact.items() if key != "guidance_sha256"}))


if __name__ == "__main__":
    unittest.main()

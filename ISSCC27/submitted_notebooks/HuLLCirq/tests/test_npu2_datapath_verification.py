"""QA only: finite saved-contract references and qualified checker fault rejection.

Unit fixtures never replace the original GUI job or become active-flow evidence.
Run qualification explicitly via this module's --qualify flag using trusted tools.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.domain import DomainError
from hullcirq.npu2_datapath_verification import (
    KINDS, TEMPLATE, EXPECTED_NODES, STREAMS, build_datapath_plan, datapath_asserted_trace,
    pair_packets, projected_job, validate_datapath_plan,
)
from hullcirq.verification import object_hash, execute_fixed, trusted_command, _wsl_path


def design():
    return json.loads((PROJECT / "examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))


def node(source, node_id):
    return next(n for n in source["nodes"] if n["id"] == node_id)


class Npu2DatapathTests(unittest.TestCase):
    def test_all_six_plans_freeze_original_job_and_do_not_change_input(self):
        source = design(); original = copy.deepcopy(source)
        for node_id in EXPECTED_NODES:
            plan = build_datapath_plan(source, node_id)
            validate_datapath_plan(plan)
            self.assertEqual(plan["testbench_template_version"], TEMPLATE)
            self.assertEqual(plan["contract"]["source_node"], node(source, node_id))
            self.assertEqual(plan["contract"]["source_job"], source["verification_jobs"][0])
            self.assertEqual(plan["coverage"]["complete_original_jobs"], 2)
        self.assertEqual(source, original)

    def test_independent_original_matrix_numbers(self):
        projection = projected_job(design()["verification_jobs"][0])
        self.assertEqual(projection["sums"], [(-47) & 0xffffffff, 58, 56, 11])
        self.assertEqual(projection["results"], [(-44) & 0xffffffff, 56, 59, 9])
        self.assertEqual(projection["post_config"] & 1, 0)

    def test_pe_pairs_are_exact_saved_row_and_column_with_first_last(self):
        source = design(); job = source["verification_jobs"][0]
        for row in range(2):
            for column in range(2):
                plan = build_datapath_plan(source, f"npu2-pe{row}{column}")
                pairs = pair_packets(plan["contract"])
                self.assertEqual(len(pairs), job["k"])
                self.assertEqual([v & 255 for v in pairs], [v & 255 for v in job["A"][row]])
                self.assertEqual([(v >> 8) & 255 for v in pairs], [v[column] & 255 for v in job["B"]])
                self.assertEqual([v >> 16 for v in pairs], [1, 0, 2])
                self.assertEqual({v["pair_data"] for v in plan["expanded_vectors"] if v["pair_data_valid"]}, set(pairs))

    def test_pe_only_final_sum_emits_and_both_same_jobs_finish_in_order(self):
        for node_id in KINDS["npu2_pe_original_job"]:
            plan = build_datapath_plan(design(), node_id)
            index = int(node_id[-2]) * 2 + int(node_id[-1])
            expected = plan["coverage"]["source_job_sums"][index]
            results = [v["before"]["sum_data"] for v in plan["reference_trace"] if v["sum_data_transfer"]]
            self.assertEqual(results, [expected, expected])
            self.assertEqual(plan["coverage"]["pair_data_transfers"], 7)
            self.assertGreaterEqual(plan["coverage"]["output_stall_cycles"], 5)
            self.assertEqual(plan["coverage"]["no_same_cycle_replacement_checks"], 1)
            for item in plan["reference_trace"]:
                if item["pair_data_transfer"] and not item["stimulus"]["pair_data"] & 0x20000:
                    self.assertEqual(item["after"]["sum_data_valid"], 0)

    def test_collector_does_not_bypass_missing_lane_and_resets_order(self):
        plan = build_datapath_plan(design(), "npu2-collector")
        transfers = [v["before"]["acc_data"] for v in plan["reference_trace"] if v["acc_data_transfer"]]
        expected = plan["coverage"]["source_job_sums"]
        self.assertEqual(transfers[:8], expected * 2)
        self.assertEqual(transfers[8:], [expected[0], expected[0], expected[1]])
        for item in plan["reference_trace"]:
            if item["stimulus"]["label"] == "other_lanes_cannot_pass_missing_00":
                self.assertEqual(item["acc_data_transfer"], 0)
                self.assertEqual(item["before"]["sum01_ready"], 0)
            if item["stimulus"]["reset"]:
                self.assertTrue(all(v == 0 for k, v in item["after"].items() if k.endswith(("_valid", "_ready"))))

    def test_post_four_outputs_config_boundaries_stalls_and_replacement(self):
        plan = build_datapath_plan(design(), "npu2-post")
        results = [v["before"]["result_data"] for v in plan["reference_trace"] if v["result_data_transfer"]]
        self.assertEqual(results, plan["coverage"]["source_job_results"] * 2)
        self.assertEqual(plan["coverage"]["post_config_transfers"], 3)
        self.assertEqual(plan["coverage"]["result_data_transfers"], 8)
        self.assertEqual(plan["coverage"]["same_cycle_replacement_transfers"], 6)
        self.assertEqual(plan["coverage"]["signed_overflow_transfers"], 0)
        for item in plan["reference_trace"]:
            if item["stimulus"]["label"] in ("fifth_acc_rejected_without_fresh_config", "no_stale_configuration"):
                self.assertEqual(item["acc_data_transfer"], 0)
            if item["stimulus"]["post_config_valid"]:
                self.assertEqual(item["acc_data_transfer"], 0)

    def test_payload_and_valid_are_held_until_actual_transfer_or_reset(self):
        for node_id in EXPECTED_NODES:
            plan = build_datapath_plan(design(), node_id)
            for previous, current in zip(plan["reference_trace"], plan["reference_trace"][1:]):
                if previous["stimulus"]["reset"] or current["stimulus"]["reset"]:
                    continue
                for stream, (direction, _, _) in STREAMS[plan["kind"]].items():
                    if direction == "input" and previous["stimulus"][stream + "_valid"] and not previous[stream + "_transfer"]:
                        self.assertEqual(current["stimulus"][stream + "_valid"], 1, (node_id, stream, previous["cycle"]))
                        self.assertEqual(current["stimulus"][stream], previous["stimulus"][stream])
                output = next(name for name, (direction, _, _) in STREAMS[plan["kind"]].items() if direction == "output")
                if previous["before"][output + "_valid"] and not previous["stimulus"][output + "_ready"]:
                    self.assertEqual(previous["after"][output + "_valid"], 1)
                    self.assertEqual(previous["after"][output], previous["before"][output])

    def test_recipes_and_asserted_trace_are_explicit_not_observed_dut_cycles(self):
        for node_id in EXPECTED_NODES:
            plan = build_datapath_plan(design(), node_id)
            trace = datapath_asserted_trace(plan)
            self.assertEqual(len(trace), plan["vector_count"])
            self.assertIsNone(trace[0]["asserted_before"])
            self.assertIn("earliest-acceptance", " ".join(plan["limits"]))
            self.assertIn("harness", plan["testbench"] if plan["kind"] != "npu2_collector_original_job" else "harness")

    def test_modified_contracts_fail_closed(self):
        for node_id in EXPECTED_NODES:
            changes = [lambda d: node(d, node_id).update(behavior="Different arithmetic"),
                       lambda d: node(d, node_id)["ports"][0].update(width=17),
                       lambda d: node(d, node_id)["constraints"].update(latency_cycles=9),
                       lambda d: d["settings"].update(reset_kind="asynchronous"),
                       lambda d: d["design_intent"].update(pe_instances=True),
                       lambda d: d["global_integration"].update(numerical_contract="Changed arithmetic"),
                       lambda d: d["verification_jobs"][0].update(k=True),
                       lambda d: d["verification_jobs"][0]["A"][0].__setitem__(0, False),
                       lambda d: d["verification_jobs"].append(copy.deepcopy(d["verification_jobs"][0]))]
            for change in changes:
                source = design(); change(source)
                with self.subTest(node=node_id, change=change), self.assertRaises(DomainError):
                    build_datapath_plan(source, node_id)
            source = design()
            edge = next(e for e in source["edges"] if node_id in (e["source"]["node_id"], e["target"]["node_id"]))
            edge["behavior"] += " Changed protocol."
            with self.assertRaises(DomainError):
                build_datapath_plan(source, node_id)

    def test_plan_tampering_is_rejected_including_boolean_numeric_substitution(self):
        for node_id in ("npu2-pe00", "npu2-collector", "npu2-post"):
            original = build_datapath_plan(design(), node_id)
            changes = [lambda p: p["expanded_vectors"][0].update(reset=True),
                       lambda p: p["reference_trace"][0]["after"].update(new_value=0),
                       lambda p: p["coverage"].update(complete_original_jobs=3),
                       lambda p: p.update(testbench=p["testbench"] + "// tampered"),
                       lambda p: p.update(testbench_template_version="not-supported")]
            for change in changes:
                plan = copy.deepcopy(original); change(plan)
                with self.assertRaises(DomainError):
                    validate_datapath_plan(plan)

    def test_new_saved_job_values_change_stimulus_reference_and_hash(self):
        source = design()
        before = build_datapath_plan(source, "npu2-pe00")
        source["verification_jobs"][0]["A"][0][0] = -7
        after = build_datapath_plan(source, "npu2-pe00")
        self.assertNotEqual(before["vector_hash"], after["vector_hash"])
        self.assertNotEqual(before["reference_trace_hash"], after["reference_trace_hash"])
        validate_datapath_plan(after)

    def test_qa_only_k1_and_signed_overflow_relu_projection(self):
        source = design(); job = source["verification_jobs"][0]
        job.update(k=1, A=[[-128], [127]], B=[[-128, 127]], bias=[2147483647, -2147483648], relu=True)
        for node_id in EXPECTED_NODES:
            plan = build_datapath_plan(source, node_id)
            validate_datapath_plan(plan)
        post = build_datapath_plan(source, "npu2-post")
        self.assertGreater(post["coverage"]["signed_overflow_transfers"], 0)
        self.assertGreater(post["coverage"]["relu_clamped_transfers"], 0)
        self.assertEqual(pair_packets(build_datapath_plan(source, "npu2-pe00")["contract"])[0] >> 16, 3)

    def test_extracted_ready_facts_match_actual_checker_predicates(self):
        for node_id in EXPECTED_NODES:
            plan = build_datapath_plan(design(), node_id)
            asserted_trace = datapath_asserted_trace(plan)
            for recipe, facts in zip(plan["reference_trace"], asserted_trace):
                for phase in ("before", "after"):
                    exact = facts["asserted_" + phase] or {}
                    known = facts["known_bit_" + phase]
                    self.assertFalse(set(exact) & set(known))
                    for name, value in exact.items():
                        if name.endswith("_ready") and value == 1 and plan["kind"] != "npu2_collector_original_job":
                            self.assertEqual(plan["kind"], "npu2_post_original_job")
                            self.assertEqual((name, phase), ("acc_data_ready", "before"))
                            self.assertTrue(recipe["result_data_transfer"] and recipe["acc_data_transfer"])
        pe = datapath_asserted_trace(build_datapath_plan(design(), "npu2-pe00"))
        self.assertIn("pair_data_ready", pe[1]["known_bit_before"])
        self.assertNotIn("pair_data_ready", pe[1]["asserted_before"])

    def test_nonclocked_reset_pulses_preserve_synchronous_state(self):
        for node_id in EXPECTED_NODES:
            plan = build_datapath_plan(design(), node_id)
            self.assertGreater(plan["coverage"]["nonclocked_reset_pulse_checks"], 0)
            self.assertIn("rst=0; #1;", plan["testbench"])
            self.assertIn("after nonclocked reset", plan["testbench"])

    def test_unknown_kind_node_and_template_fail_closed(self):
        with self.assertRaises(DomainError):
            build_datapath_plan(design(), "npu2-control")
        with self.assertRaises(DomainError):
            build_datapath_plan(design(), "npu2-post", "future-v2")


def qualify(compiler, output_directory):
    """Compile dev-only good RTL and known-fault mutants with each real TB.

    These are tests of the checker, never active project runs or accepted RTL.
    """
    output_directory = Path(output_directory).resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    good = (PROJECT / "tests/fixtures/npu2_datapath_good.v").read_text(encoding="utf-8")
    records = []
    def simulate(label, source, node_id, rtl, expected_pass):
        plan = build_datapath_plan(source, node_id)
        directory = output_directory / label
        directory.mkdir(parents=True, exist_ok=True)
        candidate, tb, result = directory / "qa_fixture.v", directory / "frozen_tb.v", directory / "simulation.vvp"
        candidate.write_text(rtl, encoding="utf-8"); tb.write_text(plan["testbench"], encoding="utf-8")
        paths = [_wsl_path(p) if compiler["kind"] == "wsl" else str(p) for p in (candidate, tb, result)]
        base = ["-B", compiler["base_directory"]] if compiler.get("base_directory") else []
        compiled = execute_fixed(trusted_command(compiler, compiler["executable"], [*base, "-g2005", "-s", "hullcirq_contract_tb", "-o", paths[2], paths[0], paths[1]], directory), directory)
        if compiled["status"] != "Completed" or compiled["exit_code"] != 0:
            raise RuntimeError(label + " fixture/TB compilation failed: " + compiled["stderr"])
        runtime = compiler["executable"].rsplit("/", 1)[0] + "/vvp"
        args = ["-M", compiler["base_directory"]] if compiler.get("base_directory") else []
        simulated = execute_fixed(trusted_command(compiler, runtime, [*args, paths[2]], directory), directory)
        marker = f"HULLCIRQ_PASS vectors={plan['vector_count']} vector_hash={plan['vector_hash']}"
        actual_pass = simulated["status"] == "Completed" and simulated["exit_code"] == 0 and simulated["stdout"].splitlines().count(marker) == 1 and "HULLCIRQ_FAIL" not in simulated["stdout"]
        record = {"label": label, "scope": "development_checker_qualification_not_active_NPU", "node_id": node_id, "expected_pass": expected_pass, "actual_pass": actual_pass, "qualified": actual_pass == expected_pass, "plan": plan, "compile": compiled, "simulation": simulated}
        (directory / "record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        records.append(record)
        if not record["qualified"]:
            raise AssertionError(label + " unexpected checker outcome: " + simulated["stdout"])
    for node_id in EXPECTED_NODES:
        simulate("good_" + node_id, design(), node_id, good.replace("hullcirq_npu2_pe00", node(design(), node_id)["module_name"]) if node_id.startswith("npu2-pe") else good, True)
    mutants = {
        "pe_asynchronous_reset": ("npu2-pe00", "always @(posedge clk) begin\n if (rst) begin accumulator", "always @(posedge clk or posedge rst) begin\n if (rst) begin accumulator"),
        "collector_asynchronous_reset": ("npu2-collector", "always @(posedge clk) begin\n if (rst) selected", "always @(posedge clk or posedge rst) begin\n if (rst) selected"),
        "post_asynchronous_reset": ("npu2-post", "always @(posedge clk) begin\n if (rst) begin configured", "always @(posedge clk or posedge rst) begin\n if (rst) begin configured"),
        "pe_unsigned_product": ("npu2-pe00", "wire signed [7:0] a", "wire [7:0] a"),
        "pe_first_ignored": ("npu2-pe00", "pair_data[16] ? extended_product : accumulator + extended_product", "accumulator + extended_product"),
        "pe_last_ignored": ("npu2-pe00", "if (pair_data[17])", "if (1'b1)"),
        "pe_replacement_allowed": ("npu2-pe00", "assign pair_data_ready = !out_valid;", "assign pair_data_ready = !out_valid || sum_data_ready;"),
        "pe_stalled_data_corruption": ("npu2-pe00", "assign sum_data = out_data;", "assign sum_data = sum_data_ready ? out_data : 32'b0;"),
        "collector_wrong_lane": ("npu2-collector", "selected==0 ? sum00 : selected==1 ? sum01", "selected==0 ? sum01 : selected==1 ? sum00"),
        "collector_ignores_backpressure": ("npu2-collector", "else if (acc_data_valid && acc_data_ready)", "else if (acc_data_valid)"),
        "collector_drains_other_lane": ("npu2-collector", "assign sum01_ready = !rst && selected==1 && acc_data_ready;", "assign sum01_ready = !rst && acc_data_ready;"),
        "collector_wrong_reset_lane": ("npu2-collector", "if (rst) selected<=0;", "if (rst) selected<=1;"),
        "post_wrong_column_bias": ("npu2-post", "result_index[0] ? saved_config[64:33] : saved_config[32:1]", "saved_config[32:1]"),
        "post_always_relu": ("npu2-post", "saved_config[0] && wrapped[31]", "wrapped[31]"),
        "post_no_fresh_config": ("npu2-post", "if (result_index==3) configured<=0;", "if (result_index==3) configured<=1;"),
        "post_no_replacement": ("npu2-post", "(!out_valid || result_data_ready)", "(!out_valid)"),
        "post_config_priority_missing": ("npu2-post", " && !post_config_valid;", ";"),
        "post_stalled_data_corruption": ("npu2-post", "assign result_data = out_data;", "assign result_data = result_data_ready ? out_data : 32'b0;"),
    }
    for label, (node_id, old, new) in mutants.items():
        if old not in good:
            raise AssertionError("Bad mutation site: " + label)
        simulate(label, design(), node_id, good.replace(old, new, 1), False)
    source = design(); source["verification_jobs"][0].update(k=1, A=[[-128], [127]], B=[[-128,127]], bias=[2147483647,-2147483648], relu=True)
    for node_id in ("npu2-pe00", "npu2-post"):
        simulate("qa_numeric_" + node_id, source, node_id, good, True)
    simulate("qa_post_relu_disabled", source, "npu2-post", good.replace("saved_config[0] && wrapped[31]", "1'b0"), False)
    report = {"scope": "development_checker_qualification_not_active_NPU", "completed": len(records), "qualified": sum(r["qualified"] for r in records), "records": [{k: v for k, v in r.items() if k not in ("plan", "compile", "simulation")} for r in records]}
    (output_directory / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--qualify":
        compiler = json.loads((PROJECT / ".work/m2/compiler.json").read_text(encoding="utf-8-sig"))
        print(json.dumps(qualify(compiler, PROJECT / ".work/npu2_datapath_checker_qualification"), ensure_ascii=False, indent=2))
    else:
        unittest.main()

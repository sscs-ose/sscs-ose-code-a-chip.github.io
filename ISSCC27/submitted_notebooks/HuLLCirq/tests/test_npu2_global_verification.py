"""Pure software QA for the explicit 2x2 S08 helper.

No model, compiler, simulator or live project store is used by this module.
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
from hullcirq.npu2_control_verification import config_packet
from hullcirq.npu2_global_verification import (
    NODE_IDS, PLAN_KIND, TEMPLATE, build_plan, compiler_public_hierarchy, expected_instance_counts,
    expected_output_count, expected_pe_records, instrument_public_testbench, matrix_results,
    original_job, proof_expectations, public_transfer_counts, public_vectors, recognize_design,
    runtime_records_pass, top_interface, validate_plan,
)


class ExplicitNpu2GlobalTests(unittest.TestCase):
    def setUp(self):
        self.design = json.loads((PROJECT / "examples" / "npu_2x2_explicit_project.json").read_text(encoding="utf-8"))

    def manifest(self):
        return {"version": 1, "design": copy.deepcopy(self.design),
                "nodes": [{"node_id": node["id"], "module_name": node["module_name"]}
                          for node in self.design["nodes"]]}

    def test_exact_public_design_recognition_and_top(self):
        recognized = recognize_design(self.design)
        self.assertEqual(TEMPLATE, PLAN_KIND)
        self.assertEqual(original_job(self.design), self.design["verification_jobs"][0])
        self.assertIsNot(original_job(self.design), self.design["verification_jobs"][0])
        self.assertEqual(recognized["node_ids"], list(NODE_IDS))
        self.assertEqual(len(recognized["node_verification_kinds"]), 11)
        interface = top_interface(self.design)
        self.assertEqual(interface["module_name"], "hullcirq_npu2_top")
        self.assertEqual([(port["name"], port["width"], port["signed"]) for port in interface["ports"]], [
            ("clk", 1, False), ("rst", 1, False), ("config_data", 69, False),
            ("config_data_valid", 1, False), ("config_data_ready", 1, False),
            ("load_data", 13, False), ("load_data_valid", 1, False), ("load_data_ready", 1, False),
            ("output_data", 32, True), ("output_data_valid", 1, False),
            ("output_data_ready", 1, False), ("busy", 1, False), ("job_done", 1, False)])

    def test_recognizer_rejects_every_fixed_identity_class(self):
        mutations = [
            lambda design: design["nodes"].pop(),
            lambda design: design["nodes"][4].update(module_name="substituted_pe"),
            lambda design: design["settings"].update(reset_kind="asynchronous"),
            lambda design: design["design_intent"].update(pe_instances=16),
            lambda design: design["global_integration"].update(one_instance_per_graph_node=False),
            lambda design: design["global_integration"]["public_streams"][0].update(width=68),
            lambda design: design["verification_jobs"][0].update(k=3.0),
            lambda design: design["edges"][0].update(behavior="changed edge language"),
        ]
        for mutation in mutations:
            changed = copy.deepcopy(self.design)
            mutation(changed)
            with self.subTest(mutation=mutation), self.assertRaises(DomainError):
                recognize_design(changed)

    def test_original_job_projection_is_exact_and_typed(self):
        job = self.design["verification_jobs"][0]
        self.assertEqual(matrix_results(job), [-44, 56, 59, 9])
        vectors = public_vectors(job)
        self.assertEqual(len(vectors["load_words"]), 12)
        self.assertEqual(vectors["load_words"], [0x0F8, 0x103, 0x205, 0x807, 0x9FE, 0xA04,
                                                  0x1006, 0x11FF, 0x12FD, 0x1305, 0x1402, 0x1507])
        self.assertEqual(vectors["configuration"], [config_packet(job)])
        self.assertEqual(vectors["read_indices"], [0, 1, 2])
        self.assertEqual(set(vectors["lane_pairs"]), {"00", "01", "10", "11"})
        self.assertTrue(all(len(values) == 3 for values in vectors["lane_pairs"].values()))
        self.assertEqual(vectors["results"], [value & 0xFFFFFFFF for value in (-44, 56, 59, 9)])

    def test_plan_rebuild_counts_and_tamper_rejection(self):
        plan = build_plan(self.design)
        self.assertEqual(plan["kind"], PLAN_KIND)
        self.assertEqual(plan["recipe"]["source_job"], self.design["verification_jobs"][0])
        self.assertEqual(plan["recipe"]["expected_outputs"], [-44, 56, 59, 9])
        self.assertEqual(expected_output_count(plan), 4)
        self.assertEqual(expected_instance_counts(self.manifest()), {node_id: 1 for node_id in NODE_IDS})
        counts = public_transfer_counts(plan)
        self.assertEqual((counts["buffer_load"], counts["scheduler_batch"], counts["dispatcher_pair00"]), (12, 3, 3))
        self.assertEqual((counts["pe00_sum"], counts["collector_acc"], counts["fifo_output"]), (1, 4, 4))
        self.assertEqual(expected_pe_records(plan), [
            {"node_id": "npu2-pe00", "lane": "00", "inputs": 3, "outputs": 1},
            {"node_id": "npu2-pe01", "lane": "01", "inputs": 3, "outputs": 1},
            {"node_id": "npu2-pe10", "lane": "10", "inputs": 3, "outputs": 1},
            {"node_id": "npu2-pe11", "lane": "11", "inputs": 3, "outputs": 1},
        ])
        validate_plan(self.design, plan)
        changed = copy.deepcopy(plan)
        changed["recipe"]["expected_outputs"][0] += 1
        with self.assertRaises(DomainError):
            validate_plan(self.design, changed)

    def test_compiler_hierarchy_requires_one_of_each_explicit_node(self):
        manifest = self.manifest()
        lines = ['S_tb .scope module, "hullcirq_global_tb" "hullcirq_global_tb" 1 1;',
                 'S_dut .scope module, "dut" "hullcirq_npu2_top" 1 1, 2 1 0, S_tb;']
        for index, entry in enumerate(manifest["nodes"]):
            lines.append(f'S_n{index} .scope module, "u_{index}" "{entry["module_name"]}" 1 1, 2 1 0, S_dut;')
        hierarchy = compiler_public_hierarchy(lines, manifest)
        self.assertEqual(list(hierarchy), list(NODE_IDS))
        self.assertEqual(hierarchy["npu2-pe11"], ["dut.u_7"])
        for changed in (lines[:-1], [*lines, lines[-1].replace("S_n10", "S_extra")]):
            with self.subTest(changed=len(changed)), self.assertRaises(DomainError):
                compiler_public_hierarchy(changed, manifest)

    def test_instrumented_monitor_covers_edges_explicit_pes_and_external_gates(self):
        plan = build_plan(self.design)
        hierarchy = {node_id: ["dut.u_" + node_id.replace("-", "_")] for node_id in NODE_IDS}
        testbench, monitor = instrument_public_testbench(plan, hierarchy)
        self.assertEqual(testbench.count("          verify_public_completion;\n"), 1)
        self.assertEqual(testbench.count("HULLCIRQ_GLOBAL_PASS outputs=4"), 1)
        self.assertNotIn("pe_clear", monitor)
        self.assertIn("external load gate mismatch", monitor)
        self.assertIn("public stream connection mismatch", monitor)
        for node_id in NODE_IDS:
            self.assertIn(hierarchy[node_id][0] + ".clk", monitor)
        for lane in ("00", "01", "10", "11"):
            self.assertIn("HULLCIRQ_PE node=npu2-pe" + lane, monitor)
            self.assertIn("pb_dispatcher_pair" + lane + "_count", monitor)

    def test_runtime_records_and_proof_expectations_fail_closed(self):
        plan = build_plan(self.design)
        expectations = proof_expectations(self.manifest(), plan)
        lines = [f'HULLCIRQ_OUTPUT index={index} value={value} cycle={100 + index * 2}'
                 for index, value in enumerate(plan["recipe"]["expected_outputs"])]
        lines += [f'HULLCIRQ_PUBLIC stream={record["stream"]} transfers={record["transfers"]}'
                  for record in expectations["public_stream_transfers"]]
        lines += [f'HULLCIRQ_PE node={record["node_id"]} lane={record["lane"]} inputs={record["inputs"]} outputs={record["outputs"]}'
                  for record in expectations["pe_records"]]
        lines += [expectations["public_marker"], expectations["output_marker"]]
        stdout = "\n".join(lines) + "\n"
        passed, outputs, streams, pes = runtime_records_pass(stdout, plan)
        self.assertTrue(passed)
        self.assertEqual(len(outputs), 4)
        self.assertEqual(streams, expectations["public_stream_transfers"])
        self.assertEqual(pes, expectations["pe_records"])
        for changed in (stdout.replace("value=-44", "value=-43", 1),
                        stdout.replace(lines[4] + "\n", "", 1),
                        stdout + "HULLCIRQ_FAIL injected\n"):
            with self.subTest(changed=len(changed)):
                self.assertFalse(runtime_records_pass(changed, plan)[0])


if __name__ == "__main__":
    unittest.main()

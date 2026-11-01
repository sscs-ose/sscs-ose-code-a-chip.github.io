"""Software QA of source-derived stimulus; no model or simulator is run."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.domain import DomainError
from hullcirq.npu2_buffer_verification import KIND, TEMPLATE, build_buffer_plan, load_packets
from hullcirq.verification import build_verification_plan, object_hash, validate_plan, verification_template_version


def design():
    return json.loads((PROJECT / "examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))


class Npu2BufferVerificationTests(unittest.TestCase):
    def test_plan_derives_from_saved_graph_job_without_editing_design(self):
        source = design(); original = copy.deepcopy(source)
        plan = build_verification_plan(source, "npu2-buffer")
        self.assertEqual(source, original)
        self.assertNotIn("verification", next(n for n in source["nodes"] if n["id"] == "npu2-buffer"))
        self.assertEqual(plan["kind"], KIND)
        self.assertEqual(plan["contract"]["source_job"], source["verification_jobs"][0])
        self.assertEqual(verification_template_version(plan), TEMPLATE)
        validate_plan(plan)

    def test_every_load_byte_is_from_original_matrix_at_declared_bank_address(self):
        source = design(); job = source["verification_jobs"][0]
        packets = load_packets(job)
        expected = {((r * 8 + k) << 8) | (job["A"][r][k] & 255) for r in range(2) for k in range(job["k"])}
        expected |= {(1 << 12) | ((k * 2 + c) << 8) | (job["B"][k][c] & 255) for k in range(job["k"]) for c in range(2)}
        self.assertEqual(set(packets), expected)
        plan = build_buffer_plan(source, "npu2-buffer")
        offered = {v["load_data"] for v in plan["expanded_vectors"] if v["load_data_valid"]}
        self.assertEqual(offered, expected)
        self.assertEqual(plan["coverage"]["unique_loaded_job_bytes"], 12)
        self.assertEqual(plan["coverage"]["load_transfers"], 16)

    def test_all_original_bundles_are_checked_in_order_after_reset_retention(self):
        source = design(); job = source["verification_jobs"][0]
        plan = build_buffer_plan(source, "npu2-buffer")
        responses = [item["before"]["operands"] for item in plan["reference_trace"] if item["response_transfer"]]
        expected = [(job["A"][0][k] & 255) | (job["A"][1][k] & 255) << 8
                    | (job["B"][k][0] & 255) << 16 | (job["B"][k][1] & 255) << 24 for k in range(job["k"])]
        self.assertEqual(responses, expected)
        self.assertEqual(plan["coverage"]["reset_with_pending_response"], 1)
        self.assertEqual(plan["coverage"]["response_transfers"], 3)
        reset_cycle = next(item["cycle"] for item in plan["reference_trace"] if item["stimulus"]["reset"] and item["before"]["operands_valid"])
        self.assertEqual({item["stimulus"]["load_data"] for item in plan["reference_trace"][reset_cycle + 1:] if item["load_transfer"]}, {load_packets(job)[-1]})

    def test_priority_stalls_and_no_same_cycle_replacement_are_exercised(self):
        plan = build_buffer_plan(design(), "npu2-buffer")
        self.assertEqual(plan["coverage"]["load_priority_cycles"], 3)
        self.assertEqual(plan["coverage"]["consume_without_read_replacement_cycles"], 2)
        self.assertGreaterEqual(plan["coverage"]["response_stall_cycles"], 8)
        for item in plan["reference_trace"]:
            if not item["stimulus"]["reset"] and item["before"]["operands_valid"] and not item["stimulus"]["operands_ready"]:
                self.assertEqual(item["after"]["operands"], item["before"]["operands"])
                self.assertEqual(item["after"]["operands_valid"], 1)
                self.assertEqual(item["read_transfer"], 0)
                self.assertEqual(item["load_transfer"], 0)

    def test_offered_input_valid_and_payload_hold_until_transfer_or_reset(self):
        plan = build_buffer_plan(design(), "npu2-buffer")
        trace = plan["reference_trace"]
        for previous, current in zip(trace, trace[1:]):
            if current["stimulus"]["reset"] or previous["stimulus"]["reset"]:
                continue
            for stream, transfer in (("load_data", "load_transfer"), ("read_index", "read_transfer")):
                if previous["stimulus"][stream + "_valid"] and not previous[transfer]:
                    self.assertEqual(current["stimulus"][stream + "_valid"], 1)
                    self.assertEqual(current["stimulus"][stream], previous["stimulus"][stream])
        self.assertIn("attempt<64", plan["testbench"])
        self.assertIn("until its actual handshake", plan["testbench"])
        self.assertNotIn("load_data_ready !== 1", plan["testbench"].split('if (load_data_valid && load_data_ready !== 0 && load_data_ready !== 1)')[0])

    def test_changed_original_job_changes_frozen_stimulus_and_hash(self):
        source = design(); before = build_buffer_plan(source, "npu2-buffer")
        source["verification_jobs"][0]["A"][0][0] = -7
        after = build_buffer_plan(source, "npu2-buffer")
        self.assertNotEqual(before["vector_hash"], after["vector_hash"])
        self.assertNotEqual(before["contract_hash"], after["contract_hash"])
        self.assertNotEqual(before["testbench_sha256"], after["testbench_sha256"])
        validate_plan(after)

    def test_modified_behavior_ports_edges_reset_or_dimensions_fail_closed(self):
        mutations = [
            lambda d: d["nodes"][1].update(behavior=d["nodes"][1]["behavior"] + " Different latency."),
            lambda d: d["nodes"][1]["constraints"].update(bank_depth=32),
            lambda d: d["nodes"][1]["ports"][0].update(width=16),
            lambda d: d["edges"][2].update(behavior="Changed request contract"),
            lambda d: d["settings"].update(reset_kind="asynchronous"),
            lambda d: d["design_intent"].update(matrix_rows=4),
            lambda d: d["global_integration"].update(reset_contract="Clear operand bytes"),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                source = design(); mutate(source)
                with self.assertRaises(DomainError):
                    build_buffer_plan(source, "npu2-buffer")

    def test_duplicate_or_malformed_original_jobs_fail_closed(self):
        mutations = [lambda d: d["verification_jobs"].append(copy.deepcopy(d["verification_jobs"][0])),
                     lambda d: d["verification_jobs"][0].update(k=True),
                     lambda d: d["verification_jobs"][0]["A"][0].__setitem__(0, False),
                     lambda d: d["verification_jobs"][0]["B"].pop(),
                     lambda d: d["verification_jobs"][0].update(relu=0)]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                source = design(); mutate(source)
                with self.assertRaises(DomainError):
                    build_buffer_plan(source, "npu2-buffer")

    def test_frozen_plan_tampering_including_boolean_type_is_rejected(self):
        original = build_buffer_plan(design(), "npu2-buffer")
        changes = [lambda p: p["expanded_vectors"][1].update(load_data=0),
                   lambda p: p["reference_trace"][1].update(load_transfer=True),
                   lambda p: p["coverage"].update(response_transfers=4),
                   lambda p: p.update(testbench=p["testbench"] + "// changed"),
                   lambda p: p.update(testbench_template_version="npu-original-job-nodes-v1"),
                   lambda p: p["contract"]["source_job"]["A"][0].__setitem__(0, 1)]
        for change in changes:
            with self.subTest(mutation=change):
                plan = copy.deepcopy(original); change(plan)
                with self.assertRaises(DomainError):
                    validate_plan(plan)

    def test_saved_legacy_plans_keep_their_template(self):
        sys.path.insert(0, str(PROJECT / "scripts"))
        from prepare_npu_nodes_project import build_proposal
        old = build_proposal(json.loads((PROJECT / "examples/npu_scheduler_project.json").read_text(encoding="utf-8")))
        plan = build_verification_plan(old, "node-buffer")
        self.assertEqual(plan["testbench_template_version"], "npu-original-job-nodes-v1")
        validate_plan(plan)


if __name__ == "__main__":
    unittest.main()

"""Software QA of the finite saved-spec FIFO compiler; no circuit run here."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.domain import DomainError
from hullcirq.fifo_spec_verification import (KIND, TEMPLATE, _job_projection,
                                           build_fifo_plan, fifo_asserted_trace)
from hullcirq.verification import build_verification_plan, object_hash, validate_plan, verification_template_version


def design():
    return json.loads((PROJECT / "examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))


def node(source):
    return next(n for n in source["nodes"] if n["id"] == "npu2-fifo")


class FifoSpecVerificationTests(unittest.TestCase):
    def test_saved_input_is_frozen_without_editing_or_adding_verification_field(self):
        source = design(); before = copy.deepcopy(source)
        plan = build_verification_plan(source, "npu2-fifo")
        self.assertEqual(source, before)
        self.assertNotIn("verification", node(source))
        self.assertEqual(plan["kind"], KIND)
        self.assertEqual(verification_template_version(plan), TEMPLATE)
        self.assertEqual(plan["contract"]["source_node"], node(source))
        self.assertEqual(plan["contract"]["source_job"], source["verification_jobs"][0])
        self.assertEqual(plan["source_job_hash"], object_hash(source["verification_jobs"][0]))
        validate_plan(plan)

    def test_no_fixed_node_or_module_identity_is_required(self):
        source = design(); selected = node(source)
        selected["id"], selected["module_name"] = "arbitrary-storage", "custom_storage"
        ids = {p["id"]: "custom-" + p["name"] for p in selected["ports"]}
        for p in selected["ports"]:
            p["id"] = ids[p["id"]]
            if "sideband" in p:
                p["sideband"]["associated_port_id"] = ids[p["sideband"]["associated_port_id"]]
        for edge in source["edges"]:
            for side in ("source", "target"):
                if edge[side]["node_id"] == "npu2-fifo":
                    edge[side]["node_id"] = selected["id"]
                    edge[side]["port_id"] = ids[edge[side]["port_id"]]
        for stream in source["global_integration"]["public_streams"]:
            if stream["node_id"] == "npu2-fifo":
                stream["node_id"] = selected["id"]
        source["layout"]["nodes"][selected["id"]] = source["layout"]["nodes"].pop("npu2-fifo")
        plan = build_verification_plan(source, selected["id"])
        self.assertEqual(plan["source_node_id"], "arbitrary-storage")
        self.assertIn("custom_storage dut", plan["testbench"])
        validate_plan(plan)

    def test_payloads_are_original_row_major_signed_results_only(self):
        plan = build_fifo_plan(design(), "npu2-fifo")
        values = [0xFFFFFFD4, 56, 59, 9]
        self.assertEqual(plan["projected_original_results"], values)
        offered = {v["result_data"] for v in plan["expanded_vectors"] if v["result_data_valid"]}
        self.assertEqual(offered, set(values))
        received = [v["before"]["output_data"] for v in plan["reference_trace"] if v["output_transfer"]]
        self.assertEqual(received, values * 4)
        self.assertEqual(plan["coverage"]["input_transfers"] - plan["coverage"]["output_transfers"], 2)

    def test_matrix_projection_uses_dimensions_and_relu_of_saved_job(self):
        source = design(); job = source["verification_jobs"][0]; intent = source["design_intent"]
        job["relu"] = True
        self.assertEqual(_job_projection(job, intent), [0, 56, 59, 9])
        intent.update(matrix_rows=1, matrix_columns=4)
        job["A"] = job["A"][:1]
        job["B"] = [row * 2 for row in job["B"]]
        job["bias"] *= 2
        self.assertEqual(_job_projection(job, intent), [0, 56, 0, 56])

    def test_saved_spec_boundary_requirements_are_exercised(self):
        plan = build_fifo_plan(design(), "npu2-fifo"); coverage = plan["coverage"]
        for key in ("full_stall_cycles", "output_stall_cycles", "full_simultaneous_cycles", "simultaneous_cycles",
                    "empty_registered_pushes", "consecutive_output_transfers", "reference_write_pointer_wraps", "reference_read_pointer_wraps"):
            self.assertGreater(coverage[key], 0, key)
        self.assertEqual(coverage["reset_with_pending_output"], 1)
        self.assertEqual(coverage["complete_original_job_repetitions"], 4)
        for v in plan["reference_trace"]:
            if v["reference_bookkeeping"]["queue_depth"] == 0 and v["input_transfer"]:
                self.assertEqual(v["before"]["output_data_valid"], 0)
                self.assertEqual(v["after"]["output_data_valid"], 1)
            if v["before"]["output_data_valid"] and not v["stimulus"]["output_data_ready"]:
                self.assertEqual(v["after"]["output_data"], v["before"]["output_data"])
                self.assertEqual(v["after"]["output_data_valid"], 1)

    def test_offered_input_is_held_until_reference_acceptance_or_reset(self):
        plan = build_fifo_plan(design(), "npu2-fifo")
        for previous, current in zip(plan["reference_trace"], plan["reference_trace"][1:]):
            if previous["stimulus"]["reset"] or current["stimulus"]["reset"]:
                continue
            if previous["stimulus"]["result_data_valid"] and not previous["input_transfer"]:
                self.assertEqual(current["stimulus"]["result_data_valid"], 1)
                self.assertEqual(current["stimulus"]["result_data"], previous["stimulus"]["result_data"])

    def test_assertions_respect_unspecified_payload_and_reset_ready(self):
        plan = build_fifo_plan(design(), "npu2-fifo")
        assertions = fifo_asserted_trace(plan)
        self.assertIsNone(assertions[0]["asserted_before"])
        for row, reference in zip(assertions, plan["reference_trace"]):
            for phase in ("before", "after"):
                checked = row["asserted_" + phase]
                if checked is None:
                    continue
                if row["stimulus"]["reset"]:
                    self.assertNotIn("result_data_ready", checked)
                self.assertEqual("output_data" in checked, bool(reference[phase]["output_data_valid"]))
                self.assertEqual(checked["output_transfer"], int(reference[phase]["output_data_valid"] and row["stimulus"]["output_data_ready"]))

    def test_recorded_no_clock_reset_pulse_preserves_full_queue(self):
        plan = build_fifo_plan(design(), "npu2-fifo")
        pulses = [v for v in plan["reference_trace"] if v["stimulus"]["reset_pulse_without_clock"]]
        self.assertEqual(len(pulses), 1)
        pulse = pulses[0]
        self.assertEqual(pulse["stimulus"]["reset"], 0)
        self.assertEqual(pulse["reference_bookkeeping"]["queue_depth"], 2)
        self.assertEqual(pulse["before"]["output_data"], pulse["after"]["output_data"])
        self.assertEqual(pulse["temporal_assertions"][0]["asserted"], {"output_data_valid": 0, "output_transfer": 0})
        self.assertEqual(pulse["temporal_assertions"][1]["asserted"]["output_data"], pulse["before"]["output_data"])
        self.assertIn("reset_asserted_without_clock", plan["testbench"])
        self.assertIn("reset_deasserted_before_clock", plan["testbench"])
        self.assertEqual(plan["coverage"]["reset_pulses_without_clock"], 1)
        self.assertEqual(plan["coverage"]["no_clock_reset_pulses_with_full_queue"], 1)

    def test_changed_original_job_rebuilds_all_numerical_proof(self):
        source = design(); original = build_fifo_plan(source, "npu2-fifo")
        source["verification_jobs"][0]["A"][0][0] = -7
        changed = build_fifo_plan(source, "npu2-fifo")
        for key in ("contract_hash", "source_job_hash", "vector_hash", "reference_trace_hash", "testbench_sha256"):
            self.assertNotEqual(original[key], changed[key], key)
        validate_plan(changed)

    def test_changed_semantics_ports_edges_numerics_or_reset_fail_closed(self):
        changes = [lambda d: node(d).update(behavior=node(d)["behavior"] + " Different bypass."),
                   lambda d: node(d)["constraints"].update(depth=3),
                   lambda d: node(d)["ports"][0].update(width=16),
                   lambda d: node(d)["ports"][2]["sideband"].update(meaning="one pulse per job"),
                   lambda d: d["edges"][-2].update(behavior="Reverse result order"),
                   lambda d: d["settings"].update(reset_kind="asynchronous"),
                   lambda d: d["global_integration"].update(numerical_contract="unsigned sums"),
                   lambda d: d["global_integration"].update(reset_contract="retain FIFO queue")]
        for change in changes:
            with self.subTest(change=change):
                source = design(); change(source)
                with self.assertRaises(DomainError):
                    build_verification_plan(source, "npu2-fifo")

    def test_ambiguous_or_invalid_typed_original_jobs_fail_closed(self):
        changes = [lambda d: d["verification_jobs"].append(copy.deepcopy(d["verification_jobs"][0])),
                   lambda d: d["verification_jobs"][0].update(k=True),
                   lambda d: d["verification_jobs"][0]["A"][0].__setitem__(0, False),
                   lambda d: d["verification_jobs"][0]["B"].pop(),
                   lambda d: d["verification_jobs"][0].update(relu=0),
                   lambda d: d["design_intent"].update(matrix_rows=2.0)]
        for change in changes:
            with self.subTest(change=change):
                source = design(); change(source)
                with self.assertRaises(DomainError):
                    build_fifo_plan(source, "npu2-fifo")

    def test_tampered_frozen_plan_or_boolean_type_is_rejected(self):
        original = build_fifo_plan(design(), "npu2-fifo")
        changes = [lambda p: p["expanded_vectors"][2].update(result_data=0),
                   lambda p: p["reference_trace"][2].update(input_transfer=True),
                   lambda p: p["coverage"].update(input_transfers=100),
                   lambda p: p["compiled_requirements"].update(empty_bypass=True),
                   lambda p: p.update(testbench=p["testbench"] + "// changed"),
                   lambda p: p["projected_original_results"].__setitem__(0, 0),
                   lambda p: p.update(testbench_template_version="future-v2")]
        for change in changes:
            with self.subTest(change=change):
                plan = copy.deepcopy(original); change(plan)
                with self.assertRaises(DomainError):
                    validate_plan(plan)

    def test_template_and_legacy_fifo_compatibility(self):
        with self.assertRaises(DomainError):
            build_fifo_plan(design(), "npu2-fifo", "unknown-template")
        sys.path.insert(0, str(PROJECT / "scripts"))
        from prepare_npu_nodes_project import build_proposal
        old = build_proposal(json.loads((PROJECT / "examples/npu_scheduler_project.json").read_text(encoding="utf-8")))
        plan = build_verification_plan(old, "node-fifo")
        self.assertEqual(plan["kind"], "npu_fifo_stream")
        self.assertEqual(verification_template_version(plan), "npu-original-job-nodes-v1")
        validate_plan(plan)


if __name__ == "__main__":
    unittest.main()

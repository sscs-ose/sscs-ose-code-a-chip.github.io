"""Software checks of the original-job control recipe, not live model proof."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.domain import DomainError
from hullcirq.npu2_control_verification import KIND, TEMPLATE, build_control_plan, config_packet, validate_control_plan
from hullcirq.verification import build_verification_plan, object_hash, validate_plan, verification_template_version


def design():
    return json.loads((PROJECT / "examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))


class Npu2ControlVerificationTests(unittest.TestCase):
    def test_dispatch_preserves_original_design_and_freezes_exact_source(self):
        source = design(); original = copy.deepcopy(source)
        plan = build_verification_plan(source, "npu2-control")
        self.assertEqual(source, original)
        self.assertEqual(plan["kind"], KIND)
        self.assertEqual(plan["contract"]["source_job"], source["verification_jobs"][0])
        self.assertEqual(plan["source_job_hash"], object_hash(source["verification_jobs"][0]))
        self.assertEqual(verification_template_version(plan), TEMPLATE)
        validate_plan(plan)

    def test_every_offered_payload_is_exact_original_configuration(self):
        source = design(); job = source["verification_jobs"][0]
        packet = config_packet(job)
        self.assertEqual(packet & 15, 3)
        self.assertEqual((packet >> 4) & 1, 0)
        self.assertEqual((packet >> 5) & 0xffffffff, 3)
        self.assertEqual((packet >> 37) & 0xffffffff, 0xfffffffe)
        plan = build_control_plan(source, "npu2-control")
        self.assertEqual({v["config_data"] for v in plan["expanded_vectors"]}, {packet})
        self.assertEqual(plan["coverage"]["original_configuration_acceptances"], 5)
        self.assertEqual(plan["coverage"]["completed_job_done_pulses"], 3)
        self.assertTrue(any("invalid-K rejection" in limit for limit in plan["limits"]))

    def test_independent_config_channels_keep_stable_payload_until_own_transfer(self):
        plan = build_control_plan(design(), "npu2-control")
        trace = plan["reference_trace"]
        self.assertGreater(plan["coverage"]["schedule_stall_cycles"], 2)
        self.assertGreater(plan["coverage"]["post_stall_cycles"], 2)
        saw_schedule_first = saw_post_first = saw_together = False
        for item in trace:
            if item["stimulus"]["reset"]:
                continue
            for name in ("schedule_config", "post_config"):
                if item["before"][name + "_valid"] and not item["stimulus"][name + "_ready"]:
                    self.assertEqual(item["after"][name + "_valid"], 1)
                    self.assertEqual(item["after"][name], item["before"][name])
            saw_schedule_first |= bool(item["schedule_transfer"] and not item["post_transfer"] and item["after"]["post_config_valid"])
            saw_post_first |= bool(item["post_transfer"] and not item["schedule_transfer"] and item["after"]["schedule_config_valid"])
            saw_together |= bool(item["schedule_transfer"] and item["post_transfer"])
        self.assertTrue(saw_schedule_first and saw_post_first and saw_together)

    def test_exact_four_run_transfers_and_one_done_cycle(self):
        trace = build_control_plan(design(), "npu2-control")["reference_trace"]
        completed = []
        for index, item in enumerate(trace):
            if item["after"]["job_done"]:
                self.assertEqual(item["phase_before"], "RUN")
                self.assertEqual(item["counted_output_transfer"], 1)
                self.assertEqual(item["output_count_after"], 4)
                self.assertEqual(item["after"]["busy"], 1)
                self.assertEqual(trace[index + 1]["after"]["job_done"], 0)
                self.assertEqual(trace[index + 1]["phase_after"], "IDLE")
                completed.append(index)
            if item["phase_before"] != "RUN":
                self.assertEqual(item["counted_output_transfer"], 0)
            if item["phase_after"] != "IDLE" and not item["stimulus"]["reset"]:
                self.assertEqual(item["after"]["config_data_ready"], 0)
        self.assertEqual(len(completed), 3)

    def test_reset_cancels_send_and_run_and_gates_status_before_edge(self):
        plan = build_control_plan(design(), "npu2-control")
        self.assertEqual(plan["coverage"]["reset_during_send"], 1)
        self.assertEqual(plan["coverage"]["reset_during_run"], 1)
        self.assertEqual(plan["coverage"]["counted_external_output_pulses"], 14)
        self.assertEqual(plan["coverage"]["nonclocked_reset_pulses"], 2)
        self.assertIn("after nonclocked reset", plan["testbench"])
        for item in plan["reference_trace"]:
            if item["stimulus"]["reset"]:
                for side in ("before", "after"):
                    for name in ("config_data_ready", "schedule_config_valid", "post_config_valid", "busy", "job_done"):
                        self.assertEqual(item[side][name], 0)
                self.assertEqual(item["output_count_after"], 0)

    def test_actual_handshake_wait_is_finite_and_input_is_held(self):
        plan = build_control_plan(design(), "npu2-control")
        self.assertEqual(plan["testbench"].count("attempt<64"), 5)
        self.assertIn("harness bound, not a hardware timeout", plan["testbench"])
        self.assertIn("finite harness configuration acceptance bound reached", plan["testbench"])
        self.assertEqual(len(plan["expanded_vectors"]), plan["vector_count"])
        for previous, current in zip(plan["reference_trace"], plan["reference_trace"][1:]):
            if previous["stimulus"]["config_data_valid"] and not previous["config_transfer"] and not previous["stimulus"]["reset"]:
                self.assertEqual(current["stimulus"]["config_data"], previous["stimulus"]["config_data"])

    def test_changed_original_job_rebuilds_source_and_payload_hash(self):
        source = design(); before = build_control_plan(source, "npu2-control")
        source["verification_jobs"][0]["bias"][1] = -3
        after = build_control_plan(source, "npu2-control")
        self.assertNotEqual(before["source_job_hash"], after["source_job_hash"])
        self.assertNotEqual(before["vector_hash"], after["vector_hash"])
        self.assertNotEqual(before["testbench_sha256"], after["testbench_sha256"])
        validate_control_plan(after)

    def test_matrix_only_change_invalidates_source_even_with_same_control_payload(self):
        source = design(); before = build_control_plan(source, "npu2-control")
        source["verification_jobs"][0]["A"][0][0] = -7
        after = build_control_plan(source, "npu2-control")
        self.assertEqual(before["vector_hash"], after["vector_hash"])
        self.assertNotEqual(before["source_job_hash"], after["source_job_hash"])
        self.assertNotEqual(before["contract_hash"], after["contract_hash"])

    def test_modified_source_contract_fails_closed(self):
        mutations = [lambda d: d["nodes"][0].update(behavior=d["nodes"][0]["behavior"] + " changed"),
                     lambda d: d["nodes"][0]["constraints"].update(final_outputs_per_job=16),
                     lambda d: d["nodes"][0]["ports"][0].update(width=70),
                     lambda d: d["nodes"][0]["ports"][3]["sideband"].update(meaning="dispatch pulse"),
                     lambda d: d["edges"][0].update(behavior="accept both on either ready"),
                     lambda d: d["settings"].update(reset_kind="asynchronous"),
                     lambda d: d["design_intent"].update(matrix_rows=4),
                     lambda d: d["global_integration"].update(reset_contract="reset optional")]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                source = design(); mutate(source)
                with self.assertRaises(DomainError):
                    build_control_plan(source, "npu2-control")

    def test_malformed_job_types_shapes_or_unsupported_templates_fail_closed(self):
        mutations = [lambda d: d["verification_jobs"].append(copy.deepcopy(d["verification_jobs"][0])),
                     lambda d: d["verification_jobs"][0].update(k=True),
                     lambda d: d["verification_jobs"][0].update(relu=0),
                     lambda d: d["verification_jobs"][0]["bias"].__setitem__(0, False),
                     lambda d: d["verification_jobs"][0]["B"].pop()]
        for mutate in mutations:
            source = design(); mutate(source)
            with self.assertRaises(DomainError):
                build_control_plan(source, "npu2-control")
        with self.assertRaises(DomainError):
            build_control_plan(design(), "npu2-control", "future-version")

    def test_tampered_evidence_is_rejected(self):
        original = build_control_plan(design(), "npu2-control")
        changes = [lambda p: p["expanded_vectors"][2].update(config_data=0),
                   lambda p: p["reference_trace"][2].update(config_transfer=True),
                   lambda p: p["coverage"].update(completed_job_done_pulses=99),
                   lambda p: p.update(testbench=p["testbench"] + "// changed"),
                   lambda p: p.update(source_job_hash="invalid"),
                   lambda p: p["contract"]["source_job"]["A"][0].__setitem__(0, 1)]
        for change in changes:
            plan = copy.deepcopy(original); change(plan)
            with self.assertRaises(DomainError):
                validate_control_plan(plan)


if __name__ == "__main__":
    unittest.main()

"""Independent software QA of scheduler data lineage and finite assertions.

These tests read the immutable prior GUI input and use disposable copies only.
They do not run a model or EDA tool, and are not actual scheduler DUT evidence.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from hullcirq.context import node_fingerprint
from hullcirq.domain import DomainError
from hullcirq.scheduler_verification import (build_scheduler_plan, pack_configuration,
                                           scheduler_asserted_trace, validate_scheduler_plan)
from hullcirq.verification import build_verification_plan, content_hash, object_hash


def isolated_scheduler_design():
    """Disposable copy of the common scheduler proposal, with no second builder."""
    return json.loads((PROJECT / "examples/npu_scheduler_project.json").read_text(encoding="utf-8"))


def independently_expected_transactions(job):
    """Direct matrix traversal and specified wire encoding, without FSM reuse."""
    result = []
    for row in range(4):
        for column in range(4):
            for index in range(job["k"]):
                lane = row * 4 + column
                result.append({"request": row * 16 + index + 256 * (index * 4 + column),
                               "data": (job["A"][row][index] % 256) + 256 * (job["B"][index][column] % 256),
                               "meta": lane + (16 if index == 0 else 0) + (32 if index == job["k"] - 1 else 0)})
    return result


class SchedulerIndependentEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.design = isolated_scheduler_design()
        self.node = next(node for node in self.design["nodes"] if node["id"] == "node-scheduler")
        self.plan = build_scheduler_plan(self.design, "node-scheduler")

    def test_completed_original_job_matches_independent_matrix_addresses_pairs_and_metadata(self):
        trace = self.plan["reference_trace"]
        final_start = max(item["cycle"] for item in trace if item["config_transfer"])
        complete = trace[final_start:]
        expected = independently_expected_transactions(self.design["verification_jobs"][0])
        requests = [item["before"]["read_request"] for item in complete if item["request_transfer"]]
        pairs = [(item["before"]["pair_data"], item["before"]["pair_meta"]) for item in complete if item["pair_transfer"]]
        self.assertEqual(requests, [item["request"] for item in expected])
        self.assertEqual(pairs, [(item["data"], item["meta"]) for item in expected])
        self.assertEqual(len(requests), 64)
        self.assertEqual(requests[:4], [0x0000, 0x0401, 0x0802, 0x0C03])
        self.assertEqual(requests[-1], 0x0F33)
        self.assertEqual(pairs[0], (0x8080, 0x10))
        self.assertEqual(pairs[-1], (0xFF00, 0x2F))
        self.assertEqual({meta & 15 for _, meta in pairs}, set(range(16)))
        self.assertTrue(all(request & 0xC0C0 == 0 for request in requests))

    def test_aborted_prefixes_restart_the_same_job_without_changing_numerical_inputs(self):
        trace = self.plan["reference_trace"]
        starts = [item["cycle"] for item in trace if item["config_transfer"]]
        self.assertEqual(len(starts), 3)
        expected = independently_expected_transactions(self.design["verification_jobs"][0])
        for position, start in enumerate(starts):
            end = starts[position + 1] if position + 1 < len(starts) else len(trace)
            actual = [(item["before"]["pair_data"], item["before"]["pair_meta"])
                      for item in trace[start:end] if item["pair_transfer"]]
            self.assertEqual(actual, [(item["data"], item["meta"]) for item in expected[:len(actual)]])
            if position < 2:
                self.assertTrue(0 < len(actual) < len(expected))
        self.assertEqual(self.plan["contract"]["source_job"], self.design["verification_jobs"][0])

    def test_all_driving_sources_obey_valid_data_stability_until_transfer_or_reset(self):
        trace = self.plan["reference_trace"]
        stalls = {"config": 0, "response": 0, "request": 0, "pair": 0}
        for current, following in zip(trace, trace[1:]):
            if current["stimulus"]["reset"] or following["stimulus"]["reset"]:
                continue
            for label, valid, ready, data in (("config", "config_valid", "schedule_config_ready", "config_data"),
                                              ("response", "response_valid", "read_response_ready", "response_data")):
                if current["stimulus"][valid] and not current["before"][ready]:
                    self.assertEqual(following["stimulus"][valid], 1, (label, current["cycle"]))
                    self.assertEqual(following["stimulus"][data], current["stimulus"][data], (label, current["cycle"]))
                    stalls[label] += 1
            for label, valid, ready, payload in (("request", "read_request_valid", "request_ready", ("read_request",)),
                                                ("pair", "pair_data_valid", "pair_ready", ("pair_data", "pair_meta"))):
                if current["before"][valid] and not current["stimulus"][ready]:
                    self.assertEqual(following["before"][valid], 1, (label, current["cycle"]))
                    for key in payload:
                        self.assertEqual(following["before"][key], current["before"][key], (label, key, current["cycle"]))
                    stalls[label] += 1
        self.assertGreater(stalls["config"], 0)
        self.assertGreater(stalls["request"], 0)
        self.assertGreater(stalls["pair"], 0)
        # A response-ready stall may be absent for this single-outstanding FSM;
        # the check is still applied whenever the frozen environment offers one.

    def test_reset_cancels_both_pending_response_and_held_pair_without_false_done(self):
        trace = self.plan["reference_trace"]
        modes = {item["state_before"] for item in trace if item["stimulus"]["reset"]}
        self.assertTrue({"WAIT", "EMIT"}.issubset(modes))
        for item in trace:
            if item["stimulus"]["reset"]:
                self.assertEqual(item["state_after"], "IDLE")
                self.assertEqual(sum(item[key] for key in ("config_transfer", "request_transfer", "response_transfer", "pair_transfer")), 0)
                self.assertEqual(item["after"]["schedule_done"], 0)
        self.assertEqual(self.plan["coverage"]["completed_jobs"], 1)
        self.assertEqual(self.plan["coverage"]["done_pulses"], 1)
        self.assertEqual(self.plan["coverage"]["clear_pulses"], 3)

    def test_done_is_only_operand_dispatch_completion_and_clear_has_no_stream_transfer(self):
        trace = self.plan["reference_trace"]
        final_start = max(item["cycle"] for item in trace if item["config_transfer"])
        done = next(item["cycle"] for item in trace if item["before"]["schedule_done"])
        self.assertEqual(sum(item["pair_transfer"] for item in trace[final_start:done]), 64)
        for item in trace:
            if item["before"]["pe_clear"]:
                self.assertEqual(item["before"]["pair_data_valid"], 0)
                self.assertEqual(item["before"]["read_request_valid"], 0)
        self.assertTrue(any("not PE accumulation" in limit for limit in self.plan["limits"]))

    def test_configuration_preserves_original_bias_relu_and_rejects_undefined_k(self):
        job = self.design["verification_jobs"][0]
        config = pack_configuration(job)
        self.assertEqual(config & 31, 4)
        self.assertEqual((config >> 5) & 1, int(job["relu"]))
        self.assertEqual([(config >> (6 + 32 * column)) & 0xFFFFFFFF for column in range(4)],
                         [value & 0xFFFFFFFF for value in job["bias"]])
        invalid = [item for item in self.plan["reference_trace"] if not item["stimulus"]["reset"]
                   and item["stimulus"]["config_valid"] and (item["stimulus"]["config_data"] & 31) in (0, 17)]
        self.assertEqual(len(invalid), 4)
        self.assertTrue(all(not item["config_transfer"] and not item["before"]["pe_clear"] for item in invalid))

    def test_implementation_facts_omit_inactive_payloads_and_internal_fsm_observations(self):
        for raw, facts in zip(self.plan["reference_trace"], scheduler_asserted_trace(self.plan)):
            self.assertNotIn("state_before", facts)
            self.assertNotIn("state_after", facts)
            for phase in ("before", "after"):
                values = facts["asserted_" + phase]
                if values is None:
                    self.assertEqual(raw["cycle"], 0)
                    continue
                self.assertEqual("read_request" in values, bool(raw[phase]["read_request_valid"]))
                self.assertEqual("pair_data" in values, bool(raw[phase]["pair_data_valid"]))
                self.assertEqual("pair_meta" in values, bool(raw[phase]["pair_data_valid"]))

    def test_source_job_change_invalidates_fingerprint_and_cannot_reuse_copied_job(self):
        original = node_fingerprint(self.design, "node-scheduler")
        self.design["verification_jobs"][0]["A"][3][3] = 1
        self.assertNotEqual(node_fingerprint(self.design, "node-scheduler"), original)
        with self.assertRaises(DomainError):
            build_scheduler_plan(self.design, "node-scheduler")

    def test_changed_canonical_bias_relu_and_duplicate_source_job_are_rejected(self):
        for change in (lambda design: design["verification_jobs"][0]["bias"].__setitem__(0, 1),
                       lambda design: design["verification_jobs"][0].update(relu=True),
                       lambda design: design["verification_jobs"].append(copy.deepcopy(design["verification_jobs"][0]))):
            changed = copy.deepcopy(self.design)
            change(changed)
            with self.subTest(change=change), self.assertRaises(DomainError):
                build_scheduler_plan(changed, "node-scheduler")

    def test_canonical_job_types_are_checked_even_when_python_equality_matches_copy(self):
        for change in (lambda job: job.update(k=4.0),
                       lambda job: job.update(relu=0),
                       lambda job: job["A"][0].__setitem__(0, -128.0),
                       lambda job: job["bias"].__setitem__(0, False)):
            changed = copy.deepcopy(self.design)
            change(changed["verification_jobs"][0])
            with self.subTest(change=change), self.assertRaises(DomainError):
                build_scheduler_plan(changed, "node-scheduler")

    def test_changed_vectors_are_rejected_even_when_checksum_is_updated(self):
        changed = copy.deepcopy(self.plan)
        changed["expanded_vectors"][-1]["response_data"] = 1
        changed["vector_hash"] = object_hash(changed["expanded_vectors"])
        with self.assertRaises(DomainError):
            validate_scheduler_plan(changed)

    def test_changed_reference_is_rejected_even_when_checksum_is_updated(self):
        changed = copy.deepcopy(self.plan)
        first = next(item for item in changed["reference_trace"] if item["pair_transfer"])
        first["before"]["pair_meta"] ^= 1
        changed["reference_trace_hash"] = object_hash(changed["reference_trace"])
        with self.assertRaises(DomainError):
            validate_scheduler_plan(changed)

    def test_changed_testbench_and_coverage_are_rejected_with_consistent_own_checksums(self):
        changed = copy.deepcopy(self.plan)
        changed["testbench"] += "// Stage-specific altered testbench.\n"
        changed["testbench_sha256"] = content_hash(changed["testbench"])
        with self.assertRaises(DomainError):
            validate_scheduler_plan(changed)
        changed = copy.deepcopy(self.plan)
        changed["coverage"]["completed_jobs"] = 16
        with self.assertRaises(DomainError):
            validate_scheduler_plan(changed)

    def test_recipe_and_numeric_types_fail_closed(self):
        for change in (lambda contract: contract["source_job"].update(k=True),
                       lambda contract: contract["source_job"]["A"][0].__setitem__(0, -129),
                       lambda contract: contract["source_job"]["bias"].__setitem__(0, 1 << 31),
                       lambda contract: contract["exercise"].update(request_ready_pattern=[1, 1]),
                       lambda contract: contract["exercise"].update(pair_ready_pattern=[False, True]),
                       lambda contract: contract["exercise"].update(response_delays=[9]),
                       lambda contract: contract["exercise"].update(invalid_k=[False, 17]),
                       lambda contract: contract["exercise"].update(cancel_after_pair_transfers=64)):
            changed = copy.deepcopy(self.plan)
            change(changed["contract"])
            changed["contract_hash"] = object_hash(changed["contract"])
            with self.subTest(change=change), self.assertRaises(DomainError):
                validate_scheduler_plan(changed)

    def test_wrong_metadata_width_cannot_generate_verification_or_invent_signal_names(self):
        next(port for port in self.node["ports"] if port["name"] == "pair_meta")["width"] = 5
        with self.assertRaises(DomainError):
            build_scheduler_plan(self.design, "node-scheduler")

    def test_original_frozen_pe_evidence_remains_identical_without_migration(self):
        source = PROJECT / "results/npu_pe_continuous_flow"
        original_design = json.loads((source / "design.json").read_text(encoding="utf-8"))
        original_plan = json.loads((source / "verification_plan.json").read_text(encoding="utf-8"))
        self.assertEqual(build_verification_plan(original_design, "node-pe"), original_plan)


if __name__ == "__main__":
    unittest.main()

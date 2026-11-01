"""S07 recipe extraction QA from retained actual proof; no model or EDA.

The control files are immutable copies of executed S04/S05/S06 evidence.
Buffer extraction uses its historical frozen RTL-verification plan only and
does not claim a buffer netlist run or a newly executed circuit test.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.domain import DomainError
from hullcirq.implementation_specs import (ImplementationSpecManager,
    _assertion_site_count, _npu2_buffer_asserted_trace,
    _npu2_control_asserted_trace, build_node_implementation_spec)
from hullcirq.verification import object_hash, validate_plan

SOURCE = PROJECT / "results/s07_node_trace_fix/sources"
BUFFER = PROJECT / "results/npu2_buffer_debug/evidence_final/jobs/generation-307613ad790a4743a45fac9eadc3e043/verification_plan.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rehash(run):
    run["record_hash"] = object_hash({key: value for key, value in run.items()
                                    if key not in ("record_hash", "freshness", "artifacts")})


class Npu2RecipeSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = read(SOURCE / "manifest.json")
        cls.original_bytes = {name: (SOURCE / name).read_bytes() for name in cls.manifest["files"]}
        for name, raw in cls.original_bytes.items():
            if hashlib.sha256(raw).hexdigest() != cls.manifest["files"][name]["sha256"]:
                raise AssertionError("Retained actual evidence changed: " + name)
        cls.buffer_bytes = BUFFER.read_bytes()

    @classmethod
    def tearDownClass(cls):
        for name, raw in cls.original_bytes.items():
            if (SOURCE / name).read_bytes() != raw:
                raise AssertionError("Software QA rewrote original proof: " + name)
        if BUFFER.read_bytes() != cls.buffer_bytes:
            raise AssertionError("Software QA rewrote original buffer plan.")

    def sources(self):
        return tuple(read(SOURCE / name) for name in
                     ("control_design.json", "control_candidate.json", "control_synthesis.json", "control_simulation.json"))

    def test_actual_current_control_derives_from_exact_passed_netlist(self):
        data = self.sources(); original = copy.deepcopy(data)
        payload = build_node_implementation_spec(*data)
        self.assertEqual(data, original)
        self.assertEqual(payload["checks"]["validation_status"], "Passed")
        self.assertEqual(payload["lineage"]["netlist_run_id"], self.manifest["netlist_run_id"])
        self.assertEqual(payload["lineage"]["verification_plan_sha256"], object_hash(data[3]["verification_plan"]))
        self.assertEqual(payload["observed_facts"]["vector_unit"], "recipe_step")
        self.assertEqual(payload["observed_facts"]["vector_count"], 77)
        self.assertEqual(payload["observed_facts"]["signal_checks"], data[3]["verification_plan"]["signal_checks"])
        self.assertFalse(any("16-PE" in text or "K=1/16" in text for text in payload["unverified_limits"]))
        self.assertEqual(payload["original_requirements"]["verification_plan_limits"], data[3]["verification_plan"]["limits"])
        self.assertNotIn("No cross-node integration, synthesis, netlist, timing, layout, DRC, LVS or post-layout check is claimed.", payload["unverified_limits"])
        self.assertEqual({p["name"] for p in payload["public_interface"]["raw_signals"]}, {"output_transfer", "busy", "job_done"})

    def test_control_summary_matches_literal_frozen_testbench_signal_check_sites(self):
        plan = self.sources()[3]["verification_plan"]
        trace = _npu2_control_asserted_trace(plan)
        # Every HULLCIRQ_FAIL site in this expanded control TB is either a
        # represented signal assertion or the one progress-bound guard per offer.
        offers = sum(row["config_transfer"] for row in plan["reference_trace"])
        self.assertEqual(_assertion_site_count(trace), plan["testbench"].count("HULLCIRQ_FAIL") - offers)
        self.assertEqual(_assertion_site_count(trace), 890)
        facts = build_node_implementation_spec(*self.sources())["observed_facts"]
        self.assertEqual(facts["checked_assertion_count"], 890)
        self.assertEqual(facts["assertion_count_scope"], "static_recipe_assertion_sites_not_measured_runtime_samples")
        self.assertEqual(facts["trace_timing"], "earliest_acceptance_reference_recipe_not_observed_dut_cycles")

    def test_idle_ready_is_known_not_eager_and_payloads_are_valid_only(self):
        plan = self.sources()[3]["verification_plan"]
        for item, row in zip(plan["reference_trace"], _npu2_control_asserted_trace(plan)):
            self.assertNotIn("cycle", row)
            for phase in ("before", "after"):
                checked = row["asserted_" + phase]
                idle = item["phase_" + phase] == "IDLE"
                if idle and item[phase]["config_data_ready"] == 1:
                    self.assertNotIn("config_data_ready", checked)
                    self.assertTrue(any(p["phase"] == phase and p["signal"] == "config_data_ready" and p["allowed"] == [0, 1]
                                        for p in row["predicate_assertions"]))
                for name in ("schedule_config", "post_config"):
                    self.assertEqual(name in checked, bool(item[phase][name + "_valid"]))
                    if name in checked:
                        self.assertEqual(checked[name], item[phase][name])
            if item["config_transfer"]:
                self.assertEqual(row["after_condition"], "after_actual_configuration_acceptance")
                self.assertEqual(row["conditional_assertions"][0]["maximum_attempts"], 64)

    def test_control_nonclocked_reset_assertions_are_retained(self):
        rows = [row for row in _npu2_control_asserted_trace(self.sources()[3]["verification_plan"])
                if row["temporal_assertions"]]
        self.assertEqual([row["recipe_step"] for row in rows], [5, 18])
        for row in rows:
            temporal = row["temporal_assertions"]
            self.assertEqual(len(temporal), 3)
            self.assertEqual(temporal[0]["asserted"], temporal[2]["asserted"])
            self.assertEqual(temporal[1]["asserted"], dict.fromkeys(
                ("config_data_ready", "schedule_config_valid", "post_config_valid", "busy", "job_done"), 0))

    def test_original_control_plan_and_checks_remain_required(self):
        for field in ("reference_trace_hash", "testbench_sha256"):
            data = self.sources()
            data[3]["checks"][field] = "0" * 64
            rehash(data[3])
            with self.subTest(field=field), self.assertRaises(DomainError) as caught:
                build_node_implementation_spec(*data)
            self.assertEqual(caught.exception.code, "simulation_provenance_conflict")

    def test_buffer_extracts_historical_actual_frozen_recipe_without_eager_readiness(self):
        plan = json.loads(self.buffer_bytes); before = copy.deepcopy(plan)
        validate_plan(plan)
        trace = _npu2_buffer_asserted_trace(plan)
        self.assertEqual(plan, before)
        self.assertEqual(len(trace), 37)
        for item, row in zip(plan["reference_trace"], trace):
            self.assertNotIn("cycle", row)
            self.assertEqual(row["recipe_step"], item["cycle"])
            if row["stimulus"]["reset"]:
                self.assertIsNone(row["asserted_before"])
                self.assertEqual(row["asserted_after"], {"operands_valid": 0})
                self.assertEqual(row["predicate_assertions"], [])
            for phase in ("before", "after"):
                checked = row["asserted_" + phase]
                if checked is not None:
                    self.assertNotIn("load_data_ready", checked)
                    self.assertNotIn("read_index_ready", checked)
                    self.assertEqual("operands" in checked, bool(item[phase]["operands_valid"]))
            self.assertFalse(any(p["operator"] == "equals" and p["expected"] == 1 for p in row["predicate_assertions"]))
            if item["load_transfer"] or item["read_transfer"]:
                self.assertEqual(row["conditional_assertions"][0]["maximum_attempts"], 64)
                self.assertTrue(row["after_condition"].startswith("after_actual_"))

    def test_buffer_backpressure_priority_and_unexpected_transfers_match_harness(self):
        plan = json.loads(self.buffer_bytes)
        for row in _npu2_buffer_asserted_trace(plan):
            vector = row["stimulus"]
            ready = row["predicate_assertions"]
            if not vector["reset"]:
                for name in ("load_data", "read_index"):
                    self.assertEqual(any(p["signal"] == name + "_ready" and p["operator"] == "known_bit" for p in ready), bool(vector[name + "_valid"]))
                if vector["load_data_valid"] and vector["read_index_valid"]:
                    self.assertTrue(any(p.get("reason") == "load_priority" and p["signal"] == "read_index_ready" and p["expected"] == 0 for p in ready))
                if row["asserted_before"]["operands_valid"]:
                    for name in ("load_data", "read_index"):
                        self.assertEqual(any(p["signal"] == name + "_ready" and p.get("reason") == "no_input_acceptance_while_response_pending" for p in ready), bool(vector[name + "_valid"]))

    def test_future_unknown_trace_kind_records_clear_unsupported_result(self):
        data = self.sources()
        data[3]["verification_plan"]["kind"] = "future_supported_verification_kind"
        rehash(data[3])
        # Simulate a future verification adapter added without an S07 extractor.
        # All actual artifact/provenance checks still run; no circuit is executed.
        with patch("hullcirq.implementation_specs.validate_plan"), patch(
                "hullcirq.implementation_specs.build_verification_plan", return_value=data[3]["verification_plan"]), patch(
                "hullcirq.implementation_specs.verification_template_version", return_value="future-supported-template-v1"):
            payload, status, checks, error = ImplementationSpecManager._derive(data)
        self.assertIsNone(payload)
        self.assertEqual(status, "Unsupported")
        self.assertEqual(error["code"], "unsupported_implementation_trace")
        self.assertEqual(checks["validation_status"], "Unsupported")


if __name__ == "__main__":
    unittest.main()

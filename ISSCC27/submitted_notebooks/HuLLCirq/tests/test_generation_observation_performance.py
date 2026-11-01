"""Isolated observation reuse; no project, provider, simulator or EDA action.

The in-memory jobs and plan builder below are software fixtures. Template names
use the real resolver, but the fixtures do not claim valid circuit behavior.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.domain import DomainError
from hullcirq.context import node_fingerprint
from hullcirq.generation import GenerationManager
from hullcirq.npu2_buffer_verification import TEMPLATE as BUFFER_TEMPLATE
from hullcirq.npu2_control_verification import TEMPLATE as CONTROL_TEMPLATE
from hullcirq.verification import build_verification_plan


class GenerationObservationPerformanceTests(unittest.TestCase):
    def setUp(self):
        self.design = {"nodes": [{"id": "node-a"}, {"id": "node-b"}], "source_value": 1}
        self.manager = GenerationManager.__new__(GenerationManager)
        self.manager.store = SimpleNamespace(envelope=lambda: {"design": self.design})
        self.manager.lock = threading.RLock()
        self.manager._state = {"jobs": [], "node_inputs": {"node-a": "hash-node-a", "node-b": "hash-node-b"},
                               "node_epochs": {"node-a": 0, "node-b": 0}}
        self.manager._persist = Mock()
        self.fingerprints = patch("hullcirq.generation.node_fingerprint", side_effect=lambda design, node: "hash-" + node)
        self.fingerprints.start()
        self.addCleanup(self.fingerprints.stop)

    @staticmethod
    def plan(node_id="node-a", template=CONTROL_TEMPLATE, value=1):
        return {"kind": "npu2_control_original_job" if template == CONTROL_TEMPLATE else "npu2_buffer_original_job",
                "testbench_template_version": template, "node_id": node_id, "fixture_source_value": value}

    def job(self, identifier, node_id="node-a", template=CONTROL_TEMPLATE):
        job = {"id": identifier, "node_id": node_id, "input_hash": "hash-" + node_id,
               "review_status": "Accepted", "acceptance_epoch": 0,
               "verification_plan": self.plan(node_id, template)}
        self.manager._state["jobs"].append(job)
        return job

    def build_plan(self, design, node_id, template):
        return self.plan(node_id, template, design["source_value"])

    def test_same_node_and_template_rebuild_once_without_state_changes(self):
        self.job("first")
        self.job("second")
        before = copy.deepcopy(self.manager._state)
        with patch("hullcirq.generation.build_verification_plan", side_effect=self.build_plan) as builder:
            self.manager.observe_design()
        builder.assert_called_once_with(self.design, "node-a", CONTROL_TEMPLATE)
        self.assertEqual(self.manager._state, before)
        self.manager._persist.assert_not_called()

    def test_node_and_template_keys_do_not_share_rebuilds(self):
        self.job("control-first")
        self.job("control-second")
        self.job("buffer", template=BUFFER_TEMPLATE)
        self.job("other-node", node_id="node-b")
        with patch("hullcirq.generation.build_verification_plan", side_effect=self.build_plan) as builder:
            self.manager.observe_design()
        self.assertEqual(builder.call_count, 3)
        self.assertEqual([(call.args[1], call.args[2]) for call in builder.call_args_list],
                         [("node-a", CONTROL_TEMPLATE), ("node-a", BUFFER_TEMPLATE), ("node-b", CONTROL_TEMPLATE)])
        self.manager._persist.assert_not_called()

    def test_each_raw_frozen_plan_is_checked_even_when_rebuild_is_shared(self):
        self.job("matching")
        changed = self.job("changed")
        changed["verification_plan"]["fixture_source_value"] = 99
        frozen_jobs = copy.deepcopy(self.manager._state["jobs"])
        with patch("hullcirq.generation.build_verification_plan", side_effect=self.build_plan) as builder:
            self.manager.observe_design()
        self.assertEqual(builder.call_count, 1)
        self.assertEqual(self.manager._state["node_epochs"], {"node-a": 1, "node-b": 0})
        self.assertEqual(self.manager._state["jobs"], frozen_jobs)
        self.manager._persist.assert_called_once_with()

    def test_next_observation_rebuilds_and_observes_same_fingerprint_source_change(self):
        self.job("first")
        self.job("second")
        with patch("hullcirq.generation.build_verification_plan", side_effect=self.build_plan) as builder:
            self.manager.observe_design()
            self.manager._persist.assert_not_called()
            self.design["source_value"] = 2
            self.manager.observe_design()
            self.assertEqual(builder.call_count, 2)
            self.assertEqual(self.manager._state["node_epochs"]["node-a"], 1)
            self.manager._persist.assert_called_once_with()
            # Approval withdrawal must still happen once, not on every read.
            self.manager.observe_design()
            self.assertEqual(builder.call_count, 2)
            self.manager._persist.assert_called_once_with()

    def test_build_error_is_shared_only_within_observation_and_withdraws_once(self):
        self.job("first")
        self.job("second")
        error = DomainError("software_fixture_invalid_source", "Isolated source failure.")
        with patch("hullcirq.generation.build_verification_plan", side_effect=error) as builder:
            self.manager.observe_design()
            self.manager.observe_design()
        self.assertEqual(builder.call_count, 1)
        self.assertEqual(self.manager._state["node_epochs"]["node-a"], 1)
        self.manager._persist.assert_called_once_with()

    def test_real_saved_plan_retains_strict_live_type_guard_with_normalized_hash(self):
        # This is plan reconstruction only, not RTL generation or simulation.
        self.design = json.loads((PROJECT / "examples/npu_scheduler_project.json").read_text(encoding="utf-8"))
        node_id = "node-scheduler"
        fingerprints = {node["id"]: node_fingerprint(self.design, node["id"]) for node in self.design["nodes"]}
        frozen_plan = build_verification_plan(self.design, node_id)
        jobs = [{"id": identifier, "node_id": node_id, "input_hash": fingerprints[node_id],
                 "review_status": "Accepted", "acceptance_epoch": 0,
                 "verification_plan": copy.deepcopy(frozen_plan)} for identifier in ("first", "second")]
        self.manager._state = {"jobs": jobs, "node_inputs": fingerprints,
                               "node_epochs": {identifier: 0 for identifier in fingerprints}}
        original_jobs = copy.deepcopy(jobs)
        with patch("hullcirq.generation.node_fingerprint", wraps=node_fingerprint), \
                patch("hullcirq.generation.build_verification_plan", wraps=build_verification_plan) as builder:
            self.manager.observe_design()
            self.assertEqual(builder.call_count, 1)
            self.manager._persist.assert_not_called()
            self.design["verification_jobs"][0]["k"] = float(self.design["verification_jobs"][0]["k"])
            self.assertEqual(node_fingerprint(self.design, node_id), fingerprints[node_id])
            self.manager.observe_design()
            self.assertEqual(builder.call_count, 2)
            self.assertEqual(self.manager._state["node_epochs"][node_id], 1)
            self.manager._persist.assert_called_once_with()
        self.assertEqual(jobs, original_jobs)


if __name__ == "__main__":
    unittest.main()

"""Capability guidance QA. No model, compiler, simulator, or live store runs."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.domain import IMPLEMENTED_STAGES, DomainError
from hullcirq.generation import GenerationManager
from hullcirq.store import ProjectStore
from test_adoption_policy import design_fixture, format_fixture, software_profile


class VerificationReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".work")
        self.addCleanup(self.temp.cleanup)
        self.store = ProjectStore(self.temp.name)

    def manager(self, design=None, compiler=True):
        self.store.save(design or design_fixture(), self.store.envelope()["revision"]["id"])
        manager = GenerationManager(self.store, compiler={"software_fixture": True} if compiler else None)
        self.addCleanup(manager.close)
        return manager

    def readiness(self, manager, node_id="node-producer"):
        return next(node for node in manager.envelope()["generation"]["nodes"]
                    if node["node_id"] == node_id)["behavioral_verification"]

    def test_supported_node_exposes_ready_before_any_rtl_without_running_tools(self):
        manager = self.manager()
        before = manager.path.read_bytes()
        with patch("hullcirq.generation.ChatCompletionsClient") as client, \
                patch("hullcirq.generation.verify_behavior") as behavior, \
                patch("hullcirq.generation.check_rtl") as checks:
            value = self.readiness(manager)
            client.assert_not_called()
            behavior.assert_not_called()
            checks.assert_not_called()
        self.assertEqual(value["status"], "ready")
        self.assertTrue(value["available"])
        self.assertEqual(value["plan_kind"], "int8_mac_stream")
        self.assertEqual(manager.envelope()["generation"]["jobs"], [])
        self.assertEqual(manager.path.read_bytes(), before)

    def test_original_explicit_npu_all_nodes_expose_ready_without_running_tools(self):
        design = json.loads((ROOT / "examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))
        manager = self.manager(design)
        before = (self.store.state_path.read_bytes(), manager.path.read_bytes())
        with patch("hullcirq.generation.ChatCompletionsClient") as client, \
                patch("hullcirq.generation.verify_behavior") as behavior:
            for node in design["nodes"]:
                value = self.readiness(manager, node["id"])
                self.assertEqual(value["status"], "ready", node["id"])
                self.assertTrue(value["available"], node["id"])
            client.assert_not_called()
            behavior.assert_not_called()
        self.assertEqual((self.store.state_path.read_bytes(), manager.path.read_bytes()), before)

    def test_blank_behavior_is_missing_input_without_promising_text_creates_checker(self):
        design = design_fixture(with_contract=False)
        design["nodes"][0]["behavior"] = " "
        manager = self.manager(design)
        value = self.readiness(manager)
        self.assertEqual(value["status"], "input_required")
        self.assertTrue(value["needed_user_action"])
        self.assertEqual(value["required_fields"], ["behavior"])
        self.assertIn("entering text does not create one", value["message"])

    def test_invalid_supported_contract_points_to_review_and_keeps_diagnostic(self):
        design = design_fixture()
        design["nodes"][0]["verification"]["vectors"] = []
        value = self.readiness(self.manager(design))
        self.assertEqual(value["status"], "input_required")
        self.assertEqual(value["next_action"], "review_specification")
        self.assertEqual(value["source_diagnostic"]["code"], "invalid_verification_vectors")

    def test_unsupported_contract_does_not_suggest_tool_setup_or_spec_reentry(self):
        design = design_fixture()
        design["nodes"][0]["verification"]["kind"] = "unimplemented_contract"
        value = self.readiness(self.manager(design, compiler=False))
        self.assertEqual(value["status"], "implementation_required")
        self.assertFalse(value["needed_user_action"])
        self.assertEqual(value["next_action"], "implementation_required")

    def test_supported_contract_without_compiler_reports_configuration(self):
        value = self.readiness(self.manager(compiler=False))
        self.assertEqual(value["status"], "configuration_required")
        self.assertEqual(value["code"], "compiler_unavailable")
        self.assertEqual(value["plan_kind"], "int8_mac_stream")

    def test_current_plan_is_built_once_per_node_and_recomputed_after_saved_edit(self):
        manager = self.manager()
        with patch.object(manager, "_verification_plan", wraps=manager._verification_plan) as build:
            manager.envelope()
            self.assertEqual(build.call_count, len(self.store.envelope()["design"]["nodes"]))
        value = self.store.envelope()
        design = copy.deepcopy(value["design"])
        design["nodes"][0].pop("verification")
        self.store.save(design, value["revision"]["id"])
        self.assertEqual(self.readiness(manager)["status"], "implementation_required")

    def test_s04_generation_does_not_require_s06_capability(self):
        manager = self.manager(design_fixture(with_contract=False))
        revision = self.store.envelope()["revision"]["id"]
        self.store.set_review_policy("accept_on_pass", True, "Software fixture authorization", self.store.review_policy()["id"])
        for stage in IMPLEMENTED_STAGES:
            self.store.validate(stage, revision)
        manager.save_profile(software_profile())
        preview = manager.preview("node-producer", revision)
        with patch("hullcirq.generation.ChatCompletionsClient") as client, \
                patch("hullcirq.generation.check_rtl", side_effect=format_fixture):
            client.return_value.generate.return_value = {
                "execution_status": "Completed", "raw_content": "```verilog\n" + preview["requested_module_header"] + "endmodule\n```",
                "raw_reasoning": "", "finish_reason": "stop", "usage": None, "provider_request_id": None, "error": None}
            result = manager.start("node-producer", revision, preview["context_id"], preview["profile_revision_id"])
            manager._worker.join(10)
            self.assertFalse(manager._worker.is_alive())
        before = manager.path.read_bytes()
        job_id = result["generation"]["latest_job_id"]
        job = manager.job(job_id)
        self.assertIsNone(job["verification_plan_error"])
        self.assertEqual(job["effective_validation_status"], "Passed")
        self.assertEqual(job["review_status"], "Accepted")
        self.assertEqual(job["behavioral_verification"]["status"], "implementation_required")
        self.assertEqual(job["behavioral_verification"]["stage_id"], "local_netlist_simulation")
        self.assertIn("no supported behavioral checker", job["saved_rtl_verification"]["message"])
        with patch("hullcirq.generation.verify_behavior") as behavior:
            with self.assertRaises(DomainError) as rejected:
                manager.verify_saved(job_id, revision)
            self.assertIn("developer must implement", rejected.exception.message)
            behavior.assert_not_called()
        self.assertEqual(manager.path.read_bytes(), before)
        manager.close()
        reloaded = GenerationManager(ProjectStore(self.temp.name), compiler={"software_fixture": True})
        self.addCleanup(reloaded.close)
        self.assertEqual(reloaded.path.read_bytes(), before)
        self.assertEqual(reloaded.job(job_id)["behavioral_verification"]["status"], "implementation_required")


if __name__ == "__main__":
    unittest.main()

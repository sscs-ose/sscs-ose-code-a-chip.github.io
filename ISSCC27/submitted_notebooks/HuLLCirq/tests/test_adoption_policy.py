"""User authorization and durable adoption policy tests.

Provider/compiler/behavior results below are explicit software fixtures. They
verify policy control and provenance, never model quality or circuit behavior.
"""
from __future__ import annotations

import copy
import hashlib
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.domain import DomainError, IMPLEMENTED_STAGES
from hullcirq.generation import GenerationManager
from hullcirq.server import make_server
from hullcirq.store import ProjectStore


def design_fixture(with_contract=True):
    design = json.loads((PROJECT / "examples/m1_two_nodes.json").read_text(encoding="utf-8"))
    node = design["nodes"][0]
    output = node["ports"][0]
    output["name"] = "acc_data"
    incoming = copy.deepcopy(output)
    incoming.update(id="fixture-input", name="pair_data", direction="input", width=16, signed=False)
    node["ports"] = [incoming, output]
    if with_contract:
        node["verification"] = {"kind": "int8_mac_stream", "version": 1, "input_port": "pair_data", "output_port": "acc_data",
                                "accumulator_width": 32, "initial_accumulator": 0,
                                "vectors": [{"reset": 1, "input_valid": 0, "output_ready": 0, "input_data": 0},
                                            {"reset": 0, "input_valid": 1, "output_ready": 0, "input_data": 0x0201},
                                            {"reset": 0, "input_valid": 0, "output_ready": 1, "input_data": 0}]}
    return design


def software_profile():
    return {"id": "fixture", "name": "Software fixture only", "execution_location": "Local",
            "base_url": "http://127.0.0.1:9/v1", "model": "fixture-no-model", "context_window": 32768}


def format_fixture(*args, **kwargs):
    return {"validation_status": "Passed", "diagnostics": [], "checks": {
        "interface": {"validation_status": "Passed"},
        "syntax": ({"validation_status": "Not Run", "executed": False, "deferred_to_stage": "local_synthesis"}
                   if kwargs.get("interface_only") else {"validation_status": "Passed", "executed": True, "exit_code": 0}),
        "functional_verification": {"validation_status": "Not Run", "executed": False}}}


def behavior_fixture(rtl, plan, compiler, **kwargs):
    return {"validation_status": "Passed", "executed": True, "exit_code": 0, "diagnostics": [],
            "vector_hash": plan["vector_hash"], "testbench_sha256": plan["testbench_sha256"],
            "rtl_sha256": hashlib.sha256(rtl.encode("utf-8")).hexdigest()}


class AdoptionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.store = ProjectStore(self.directory)

    def tearDown(self):
        self.temporary.cleanup()

    def authorize(self):
        self.store.set_review_policy("accept_on_pass", True, "Explicit unit-test authorization", self.store.review_policy()["id"])

    def validate_inputs(self):
        revision = self.store.envelope()["revision"]["id"]
        for stage in IMPLEMENTED_STAGES:
            self.store.validate(stage, revision)

    def manager(self, with_contract=True):
        current = self.store.envelope()
        self.store.save(design_fixture(with_contract), current["revision"]["id"])
        self.authorize()
        self.validate_inputs()
        manager = GenerationManager(self.store)
        manager.save_profile(software_profile())
        return manager

    def generate(self, manager, behavior=behavior_fixture, mutate=None):
        current = self.store.envelope()
        preview = manager.preview("node-producer", current["revision"]["id"])
        rtl = preview["requested_module_header"] + "endmodule\n"
        def response(*args, **kwargs):
            if mutate:
                mutate()
            return {"raw_content": "```verilog\n" + rtl + "```", "execution_status": "Completed", "finish_reason": "stop", "usage": None, "error": None}
        with patch("hullcirq.generation.ChatCompletionsClient") as client, patch("hullcirq.generation.check_rtl", side_effect=format_fixture), patch("hullcirq.generation.verify_behavior", side_effect=behavior):
            client.return_value.generate.side_effect = response
            manager.start("node-producer", current["revision"]["id"], preview["context_id"], preview["profile_revision_id"])
            deadline = time.monotonic() + 3
            while manager._worker.is_alive() and time.monotonic() < deadline:
                manager._worker.join(0.01)
            self.assertFalse(manager._worker.is_alive())
        return manager.envelope()["generation"]["jobs"][-1]

    def test_old_store_defaults_manual_without_startup_rewrite(self):
        before = self.store.state_path.read_bytes()
        loaded = ProjectStore(self.directory)
        self.assertEqual(loaded.review_policy()["mode"], "manual")
        self.assertFalse(loaded.review_policy()["user_authorized"])
        self.assertEqual(loaded.state_path.read_bytes(), before)
        loaded.validate("global_settings", loaded.envelope()["revision"]["id"])
        self.assertEqual(loaded.envelope()["runs"][-1]["review_status"], "Awaiting Review")

    def test_automatic_policy_requires_explicit_authorization(self):
        before = self.store.state_path.read_bytes()
        with self.assertRaises(DomainError) as raised:
            self.store.set_review_policy("accept_on_pass", False)
        self.assertEqual(raised.exception.code, "policy_authorization_required")
        self.assertEqual(self.store.state_path.read_bytes(), before)

    def test_passed_input_checks_adopt_with_policy_actor_and_reload(self):
        self.authorize()
        self.validate_inputs()
        result = self.store.envelope()
        self.assertTrue(all(stage["review_status"] == "Accepted" for stage in result["workflow"][:3]))
        self.assertTrue(all(review["actor"] == "automation_policy" for review in result["reviews"]))
        self.assertTrue(all(review["provenance"]["authorization"] == "user_preapproved" for review in result["reviews"]))
        self.assertEqual(ProjectStore(self.directory).envelope()["reviews"], result["reviews"])

    def test_failed_and_stale_input_evidence_is_not_adopted(self):
        self.authorize()
        self.validate_inputs()
        current = self.store.envelope()
        altered = current["design"]
        altered["nodes"][1]["ports"][0]["width"] = 16
        saved = self.store.save(altered, current["revision"]["id"])
        graph = self.store.validate("graph_editor", saved["revision"]["id"])["runs"][-1]
        self.assertEqual(graph["validation_status"], "Failed")
        self.assertEqual(graph["review_status"], "Awaiting Review")
        self.assertFalse(any(review["run_id"] == graph["id"] for review in self.store.envelope()["reviews"]))
        self.assertEqual(self.store.envelope()["workflow"][2]["review_status"], "Awaiting Review")

    def test_manual_switch_and_policy_conflict_preserve_history(self):
        self.authorize()
        policy_id = self.store.review_policy()["id"]
        self.store.set_review_policy("manual", False, expected_policy_id=policy_id)
        before = self.store.state_path.read_bytes()
        with self.assertRaises(DomainError) as raised:
            self.store.set_review_policy("accept_on_pass", True, expected_policy_id=policy_id)
        self.assertEqual(raised.exception.code, "policy_conflict")
        self.assertEqual(self.store.state_path.read_bytes(), before)
        self.assertEqual(len(self.store.envelope()["policy_history"]), 2)

    def test_corrupt_authorization_is_rejected_without_rewriting(self):
        self.authorize()
        saved = json.loads(self.store.state_path.read_text(encoding="utf-8"))
        saved["policy_history"][0]["user_authorized"] = False
        self.store.state_path.write_text(json.dumps(saved), encoding="utf-8")
        before = self.store.state_path.read_bytes()
        with self.assertRaises(DomainError) as raised:
            ProjectStore(self.directory)
        self.assertEqual(raised.exception.code, "invalid_store")
        self.assertEqual(self.store.state_path.read_bytes(), before)

    def test_generation_adopts_interface_pass_and_records_stage_scope(self):
        manager = self.manager()
        job = self.generate(manager)
        self.assertEqual(job["review_status"], "Accepted")
        self.assertEqual(job["checks"]["behavioral"]["validation_status"], "Not Run")
        self.assertEqual(job["checks"]["syntax"]["validation_status"], "Not Run")
        self.assertIsNone(job["verification_plan"])
        review = manager.envelope()["generation"]["reviews"][-1]
        self.assertEqual(review["actor"], "automation_policy")
        self.assertEqual(review["provenance"], self.store.policy_provenance())
        self.assertEqual(review["validation_scope"], "local_rtl_interface_v1")
        manager.close()
        loaded = GenerationManager(ProjectStore(self.directory))
        self.assertEqual(loaded.job(job["id"])["review_status"], "Accepted")
        loaded.close()

    def test_interface_pass_without_behavioral_contract_can_auto_adopt_at_s04(self):
        manager = self.manager(with_contract=False)
        job = self.generate(manager)
        self.assertEqual(job["review_status"], "Accepted")
        self.assertIsNone(job["verification_plan"])
        manager.review(job["id"], "accepted", "S04 accepts the external interface only.")
        manager.close()

    def test_behavioral_checker_is_not_called_during_s04(self):
        manager = self.manager()
        def failure(*args, **kwargs):
            result = behavior_fixture(*args, **kwargs)
            result.update(validation_status="Failed", exit_code=1, diagnostics=[{"code": "fixture_fail", "severity": "error", "message": "Software fixture failure."}])
            return result
        job = self.generate(manager, behavior=failure)
        self.assertEqual(job["validation_status"], "Passed")
        self.assertEqual(job["review_status"], "Accepted")
        self.assertEqual(job["checks"]["behavioral"]["validation_status"], "Not Run")
        manager.close()

    def test_input_change_during_generation_keeps_result_stale_unadopted(self):
        manager = self.manager()
        def mutate():
            current = self.store.envelope()
            changed = current["design"]
            changed["nodes"][0]["behavior"] += " A different source specification."
            self.store.save(changed, current["revision"]["id"])
        job = self.generate(manager, mutate=mutate)
        self.assertEqual(job["freshness"], "Stale")
        self.assertEqual(job["review_status"], "Awaiting Review")
        self.assertFalse(manager.envelope()["generation"]["reviews"])
        manager.close()

    def test_policy_revocation_during_generation_keeps_pass_unadopted(self):
        manager = self.manager()
        def revoke():
            self.store.set_review_policy("manual", False, "User revoked preauthorization", self.store.review_policy()["id"])
        job = self.generate(manager, mutate=revoke)
        self.assertEqual(job["validation_status"], "Passed")
        self.assertEqual(job["freshness"], "Current")
        self.assertEqual(job["review_status"], "Awaiting Review")
        self.assertFalse(manager.envelope()["generation"]["reviews"])
        manager.close()

    def test_boolean_exit_code_is_not_an_executed_success(self):
        manager = self.manager()
        job = self.generate(manager)
        for check in ("syntax", "behavioral"):
            with self.subTest(check=check):
                altered = copy.deepcopy(job)
                altered["checks"][check]["exit_code"] = False
                self.assertFalse(GenerationManager._passed_checks(altered, require_behavioral=True))
        manager.close()

    def test_tampered_behavioral_plan_is_rejected_without_rewriting(self):
        manager = self.manager()
        self.generate(manager)
        manager.close()
        path = self.directory / "generation.json"
        saved = json.loads(path.read_text(encoding="utf-8"))
        saved["jobs"][0]["verification_plan"] = {"kind": "forged_s04_behavioral_plan"}
        path.write_text(json.dumps(saved), encoding="utf-8")
        before = path.read_bytes()
        with self.assertRaises(DomainError) as raised:
            GenerationManager(ProjectStore(self.directory))
        self.assertEqual(raised.exception.code, "invalid_generation_store")
        self.assertEqual(path.read_bytes(), before)

    def test_http_policy_api_records_authorization_and_first_pass(self):
        server = make_server("127.0.0.1", 0, self.store)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        def post(path, body):
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            connection.request("POST", path, json.dumps(body), {"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{port}"})
            response = connection.getresponse()
            result = json.loads(response.read())
            connection.close()
            self.assertEqual(response.status, 200, result)
            return result
        try:
            policy = post("/api/review-policy", {"mode": "accept_on_pass", "user_authorized": True, "expected_policy_id": None})
            self.assertEqual(policy["review_policy"]["mode"], "accept_on_pass")
            result = post("/api/validate", {"stage_id": "global_settings", "revision_id": policy["revision"]["id"]})
            self.assertEqual(result["runs"][-1]["review_status"], "Accepted")
            self.assertEqual(result["reviews"][-1]["actor"], "automation_policy")
        finally:
            server.workflow.close()
            server.generation.close()
            server.shutdown()
            server.server_close()
            thread.join(2)


if __name__ == "__main__":
    unittest.main()

"""Tool-only verification lifecycle QA; all tool/provider outputs are fixtures.

These tests exercise provenance and admission without calling a model, compiler,
or simulator. They do not establish circuit correctness.
"""
from __future__ import annotations

import copy
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.domain import DomainError, IMPLEMENTED_STAGES
from hullcirq.generation import GenerationManager, saved_verification_hash, text_hash
from hullcirq.server import make_server, project_envelope
from hullcirq.store import ProjectStore
from test_adoption_policy import behavior_fixture, design_fixture, format_fixture, software_profile


class SavedRTLVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".work")
        self.addCleanup(self.temp.cleanup)
        self.store = ProjectStore(self.temp.name)
        self.store.save(design_fixture(), self.store.envelope()["revision"]["id"])
        self.store.set_review_policy("accept_on_pass", True, "Software QA policy", self.store.review_policy()["id"])
        self.revision = self.store.envelope()["revision"]["id"]
        for stage in IMPLEMENTED_STAGES:
            self.store.validate(stage, self.revision)
        self.manager = GenerationManager(self.store, compiler={"software_fixture": True})
        self.addCleanup(lambda: self.manager.close())
        self.manager.save_profile(software_profile())
        self.parent = self.generate_parent()
        self.original = copy.deepcopy(self.manager._state["jobs"])

    def generate_parent(self, **kwargs):
        preview = self.manager.preview("node-producer", self.revision, **kwargs)
        # Complete text is a fixture. No actual tool is run against this DUT.
        rtl = preview["requested_module_header"] + "endmodule\n"
        with patch("hullcirq.generation.ChatCompletionsClient") as client, \
                patch("hullcirq.generation.check_rtl", side_effect=format_fixture), \
                patch.object(self.manager, "_verification_plan", return_value=(None, {"code": "fixture_missing_adapter", "message": "Historical adapter missing."})):
            client.return_value.generate.return_value = {"execution_status": "Completed", "raw_content": "```verilog\n" + rtl + "```",
                "raw_reasoning": "Original fixture reasoning.", "finish_reason": "stop", "usage": {"completion_tokens": 5},
                "provider_request_id": "original-fixture-request", "error": None}
            envelope = self.manager.start("node-producer", self.revision, preview["context_id"], preview["profile_revision_id"], **kwargs)
            self.manager._worker.join(10)
            self.assertFalse(self.manager._worker.is_alive())
        return self.manager.job(envelope["generation"]["latest_job_id"])

    def verify(self, parent=None, behavior=behavior_fixture):
        with patch("hullcirq.generation.ChatCompletionsClient") as client, \
                patch("hullcirq.generation.check_rtl", side_effect=format_fixture), \
                patch("hullcirq.generation.verify_behavior", side_effect=behavior):
            envelope = self.manager.verify_saved((parent or self.parent)["id"], self.revision)
            self.manager._worker.join(10)
            self.assertFalse(self.manager._worker.is_alive())
            client.assert_not_called()
        return self.manager.job(envelope["generation"]["latest_job_id"])

    def error(self, code, action):
        with self.assertRaises(DomainError) as error:
            action()
        self.assertEqual(error.exception.code, code)

    def test_saved_rtl_appends_exact_candidate_and_auto_adopts_without_model_or_profile_requirement(self):
        design_bytes = self.store.state_path.read_bytes()
        self.manager._state["active_profile_revision_id"] = None
        self.manager._persist()
        result = self.verify()
        self.assertEqual(self.manager._state["jobs"][:-1], self.original)
        self.assertEqual(self.store.state_path.read_bytes(), design_bytes)
        self.assertEqual(result["operation"], "verify")
        self.assertEqual(result["verification_of_job_id"], self.parent["id"])
        for key in ("rtl", "raw_content", "raw_reasoning", "context", "profile", "origin", "input_hash", "revision_id"):
            self.assertEqual(result[key], self.parent[key])
        self.assertFalse(result["provider_request_executed"])
        self.assertIsNone(result["usage"])
        self.assertIsNone(result["provider_request_id"])
        self.assertIsNone(result["finish_reason"])
        self.assertEqual(result["diff"], "")
        self.assertEqual((result["execution_status"], result["validation_status"], result["review_status"]), ("Completed", "Passed", "Accepted"))
        self.assertEqual(self.manager.envelope()["generation"]["nodes"][0]["accepted_job_id"], result["id"])
        self.assertEqual(self.manager._state["reviews"][-1]["actor"], "automation_policy")

    def test_s04_pass_and_legacy_verification_capability_are_separate_without_rewrite(self):
        before = self.manager.path.read_bytes()
        value = self.manager.job(self.parent["id"])
        self.assertEqual(value["validation_status"], "Passed")
        self.assertEqual(value["effective_validation_status"], "Passed")
        self.assertTrue(value["saved_rtl_verification"]["available"])
        self.assertEqual(self.manager.path.read_bytes(), before)

    def test_new_failure_preserves_parent_and_cannot_adopt(self):
        def fail(*args, **kwargs):
            return {**behavior_fixture(*args, **kwargs), "validation_status": "Failed", "exit_code": 1,
                    "diagnostics": [{"severity": "error", "code": "fixture_behavior", "message": "Fixture detected incorrect behavior."}]}
        job = self.verify(behavior=fail)
        self.assertEqual(job["validation_status"], "Failed")
        self.assertEqual(job["review_status"], "Awaiting Review")
        self.assertEqual(self.manager._state["jobs"][:-1], self.original)
        self.error("verification_failed", lambda: self.manager.review(job["id"], "accepted", "Invalid override"))

    def test_changed_source_and_wrong_revision_reject_before_tool_run(self):
        self.error("revision_conflict", lambda: self.manager.verify_saved(self.parent["id"], "older-revision"))
        current = self.store.envelope()
        design = copy.deepcopy(current["design"])
        design["nodes"][0]["behavior"] += " Changed specification."
        new = self.store.save(design, current["revision"]["id"])
        with patch("hullcirq.generation.check_rtl") as checks:
            self.error("stale_job", lambda: self.manager.verify_saved(self.parent["id"], new["revision"]["id"]))
            checks.assert_not_called()
        self.assertEqual(self.manager._state["jobs"], self.original)

    def test_missing_adapter_and_compiler_report_actionable_unavailability(self):
        with patch.object(self.manager, "_verification_plan", return_value=(None, {"code": "missing", "message": "Adapter is unavailable for this node."})):
            value = self.manager.job(self.parent["id"])["saved_rtl_verification"]
            self.assertFalse(value["available"])
            self.error("verification_unavailable", lambda: self.manager.verify_saved(self.parent["id"], self.revision))
        self.manager.compiler = None
        self.error("compiler_unavailable", lambda: self.manager.verify_saved(self.parent["id"], self.revision))

    def test_busy_and_cancel_use_same_single_worker_and_never_adopt_cancelled_proof(self):
        started = threading.Event()
        release = threading.Event()
        self.addCleanup(release.set)
        def waiting(rtl, plan, compiler, cancel_event=None):
            started.set()
            release.wait(10)
            return behavior_fixture(rtl, plan, compiler)
        with patch("hullcirq.generation.ChatCompletionsClient") as client, \
                patch("hullcirq.generation.check_rtl", side_effect=format_fixture), \
                patch("hullcirq.generation.verify_behavior", side_effect=waiting):
            envelope = self.manager.verify_saved(self.parent["id"], self.revision)
            self.assertTrue(started.wait(5))
            job_id = envelope["generation"]["latest_job_id"]
            self.error("generation_busy", lambda: self.manager.verify_saved(self.parent["id"], self.revision))
            self.manager.cancel(job_id)
            release.set()
            self.manager._worker.join(10)
            client.assert_not_called()
        job = self.manager.job(job_id)
        self.assertEqual((job["execution_status"], job["validation_status"], job["review_status"]), ("Cancelled", "Not Checked", "Awaiting Review"))
        self.assertNotIn("server_inference_stop", next(e for e in job["events"] if e["type"] == "cancel_requested"))

    def test_saved_verification_reload_preserves_exact_records(self):
        job = self.verify()
        saved = self.manager.path.read_bytes()
        self.manager.close()
        self.manager = GenerationManager(ProjectStore(self.temp.name), compiler={"software_fixture": True})
        self.assertEqual(self.manager.path.read_bytes(), saved)
        self.assertEqual(self.manager.job(job["id"])["review_status"], "Accepted")

    def test_repair_parent_context_is_copied_and_loads_without_fabricated_generate_prompt(self):
        parent = self.generate_parent(operation="repair", base_job_id=self.parent["id"], instruction="Software fixture repair request.")
        job = self.verify(parent)
        self.assertEqual(job["context"], parent["context"])
        self.manager.close()
        self.manager = GenerationManager(ProjectStore(self.temp.name), compiler={"software_fixture": True})
        self.assertEqual(self.manager.job(job["id"])["rtl"], parent["rtl"])

    def test_tampered_lineage_rtl_plan_or_provider_metadata_fails_load_without_overwrite(self):
        self.verify()
        original = copy.deepcopy(self.manager._state)
        self.manager.close()
        mutations = {
            "self_parent": lambda j: j.update(verification_of_job_id=j["id"]),
            "changed_rtl": lambda j: j.update(rtl=j["rtl"] + "// changed\n", rtl_sha256=text_hash(j["rtl"] + "// changed\n")),
            "changed_plan": lambda j: j["verification_plan"].update(vector_count=0),
            "model_call": lambda j: j.update(provider_request_executed=True),
            "invented_usage": lambda j: j.update(usage={"completion_tokens": 1}),
            "changed_prompt": lambda j: j["context"]["messages"][0].update(content="Changed prompt"),
            "changed_raw_reasoning": lambda j: j.update(raw_reasoning="Changed reasoning"),
        }
        for label, change in mutations.items():
            with self.subTest(label=label):
                state = copy.deepcopy(original)
                change(state["jobs"][-1])
                self.manager.path.write_text(json.dumps(state), encoding="utf-8")
                before = self.manager.path.read_bytes()
                self.error("invalid_generation_store", lambda: GenerationManager(ProjectStore(self.temp.name)))
                self.assertEqual(self.manager.path.read_bytes(), before)

    def test_request_changes_is_not_undone_by_policy_refresh(self):
        job = self.verify()
        self.manager.review(job["id"], "changes_requested", "Review found an untested concern.")
        reviews = copy.deepcopy(self.manager._state["reviews"])
        self.manager.apply_review_policy()
        self.assertEqual(self.manager.job(job["id"])["review_status"], "Changes Requested")
        self.assertEqual(self.manager._state["reviews"], reviews)

    def test_capability_plan_build_is_shared_per_node_in_one_envelope_only(self):
        self.generate_parent()
        with patch.object(self.manager, "_verification_plan", wraps=self.manager._verification_plan) as build:
            self.manager.envelope()
            # Readiness also covers nodes with no candidate yet. Each node is
            # recognized once, regardless of how many saved attempts it has.
            node_ids = {node["id"] for node in self.store.envelope()["design"]["nodes"]}
            self.assertCountEqual([call.args[1] for call in build.call_args_list], node_ids)
            self.manager.envelope()
            self.assertEqual(build.call_count, 2 * len(node_ids))

    def test_incomplete_parent_and_tampered_text_are_rejected(self):
        parent = self.manager._state["jobs"][0]
        parent["execution_status"] = "Failed"
        self.error("saved_rtl_required", lambda: self.manager.verify_saved(parent["id"], self.revision))
        parent["execution_status"] = "Completed"
        parent["rtl"] += "// altered after saved extraction\n"
        self.error("candidate_evidence_invalid", lambda: self.manager.verify_saved(parent["id"], self.revision))

    def test_workspace_session_and_readonly_checks_cover_verify_endpoint(self):
        # Reuse only this fixture's setup/helpers, not its other test cases.
        from test_workspace_http import WorkspaceHttpTests
        fixture = WorkspaceHttpTests("test_new_project_has_no_circuit_evidence")
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        first = fixture.create("Verification admission")
        old_session = fixture.session
        second = fixture.create("Different active project")
        payload = {"job_id": self.parent["id"], "revision_id": self.revision}
        status, result = fixture.request("POST", "/api/generation/verify", payload, session=old_session)
        self.assertEqual((status, result["error"]["code"]), (409, "workspace_session_changed"))
        status, backup = fixture.request("GET", f'/api/workspace/backup/{second["workspace"]["active"]["project_id"]}?session_id={fixture.session}', authenticated=False)
        self.assertEqual(status, 200)
        fixture.mutation("restore", {"bundle_text": json.dumps(backup), "name": "Read only verification admission"})
        status, result = fixture.request("POST", "/api/generation/verify", payload)
        self.assertEqual((status, result["error"]["code"]), (409, "read_only_system"))

    def test_http_endpoint_reuses_worker_admission_and_effective_stage_status(self):
        server = make_server("127.0.0.1", 0, self.store, compiler={"software_fixture": True})
        self.addCleanup(server.server_close)
        thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=.01), daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), thread.join(3)))
        port = server.server_address[1]
        def request(body):
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            try:
                connection.request("POST", "/api/generation/verify", json.dumps(body), {"Content-Type": "application/json"})
                response = connection.getresponse()
                return response.status, json.loads(response.read())
            finally:
                connection.close()
        stage = next(s for s in project_envelope(server)["workflow"] if s["id"] == "local_rtl_generation")
        self.assertEqual(stage["validation_status"], "Passed")
        with patch.object(server.global_generation, "is_active", return_value=True):
            status, response = request({"job_id": self.parent["id"], "revision_id": self.revision})
            self.assertEqual(status, 409)
            self.assertEqual(response["error"]["code"], "competing_execution_busy")
        with patch("hullcirq.generation.ChatCompletionsClient") as provider, \
                patch("hullcirq.generation.check_rtl", side_effect=format_fixture), \
                patch("hullcirq.generation.verify_behavior", side_effect=behavior_fixture):
            status, response = request({"job_id": self.parent["id"], "revision_id": self.revision})
            self.assertEqual(status, 202, response)
            server.generation._worker.join(10)
            provider.assert_not_called()
        self.assertEqual(server.generation._state["jobs"][-1]["verification_of_job_id"], self.parent["id"])


if __name__ == "__main__":
    unittest.main()

"""Isolated worker diagnostics: fake provider, no model or EDA execution."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.domain import IMPLEMENTED_STAGES
from hullcirq.generation import GenerationManager
from hullcirq.store import ProjectStore, _replace_with_windows_retry
from test_adoption_policy import design_fixture, software_profile


class GenerationExceptionDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".work")
        self.addCleanup(self.temp.cleanup)
        self.store = ProjectStore(self.temp.name)
        self.store.save(design_fixture(False), self.store.envelope()["revision"]["id"])
        self.store.set_review_policy("accept_on_pass", True, "Isolated exception QA", self.store.review_policy()["id"])
        self.revision = self.store.envelope()["revision"]["id"]
        for stage in IMPLEMENTED_STAGES:
            self.store.validate(stage, self.revision)
        self.manager = GenerationManager(self.store)
        self.manager.save_profile(software_profile())
        self.addCleanup(self.manager.close)
        preview = self.manager.preview("node-producer", self.revision)
        self.raw = "```verilog\n" + preview["requested_module_header"] + "endmodule\n```"
        with patch("threading.Thread.start"):
            self.manager.start("node-producer", self.revision, preview["context_id"], preview["profile_revision_id"])
        self.identifier = self.manager._state["jobs"][-1]["id"]

    def result(self, *args):
        return {"execution_status": "Completed", "raw_content": self.raw,
                "finish_reason": "stop", "usage": {"prompt_tokens": 1, "completion_tokens": 1}, "error": None}

    def execute(self, response=None):
        with patch("hullcirq.generation.ChatCompletionsClient") as provider, \
                patch("hullcirq.generation.verify_behavior", side_effect=AssertionError("No behavior in S04")):
            provider.return_value.generate.side_effect = response or self.result
            self.manager._execute(self.identifier, threading.Event())
            self.assertEqual(provider.return_value.generate.call_count, 1)
        return copy.deepcopy(self.manager._stored_job(self.identifier))

    def assert_saved_diagnostic(self, job, phase, exception_class):
        self.assertEqual(job["execution_status"], "Failed")
        self.assertEqual(job["validation_status"], "Not Checked")
        self.assertEqual(job["error"]["execution_phase"], phase)
        self.assertEqual(job["error"]["exception_class"], exception_class)
        self.assertEqual(job["error"]["diagnostic_version"], "generation-exception-v1")
        event = job["events"][-1]
        self.assertEqual(event["type"], "error")
        for field in ("execution_phase", "exception_class", "diagnostic_version", "errno", "winerror"):
            self.assertEqual(event.get(field), job["error"].get(field))
        self.assertEqual(self.manager._state["reviews"], [])

    def test_interface_exception_retains_phase_without_exception_message_or_secret(self):
        with self.assertLogs("hullcirq.generation", level="ERROR") as logs, \
                patch("hullcirq.generation.check_rtl", side_effect=ValueError("private-provider-value")):
            job = self.execute()
        self.assert_saved_diagnostic(job, "interface_check", "ValueError")
        self.assertEqual(job["raw_content"], self.raw)
        self.assertNotIn("private-provider-value", str(job["error"]) + str(job["events"]) + str(logs.output))
        self.assertIn("frames=", logs.output[0])
        before = self.manager.path.read_bytes()
        loaded = GenerationManager(self.store)
        self.addCleanup(loaded.close)
        self.assertEqual(loaded.path.read_bytes(), before)
        self.assertEqual(loaded._stored_job(self.identifier), job)

    def test_extraction_exception_is_distinct_from_interface_or_storage(self):
        with self.assertLogs("hullcirq.generation", level="ERROR"), \
                patch("hullcirq.generation.extract_rtl", side_effect=RuntimeError("private-raw-answer")):
            job = self.execute()
        self.assert_saved_diagnostic(job, "extract_rtl", "RuntimeError")
        self.assertEqual(job["checks"], {})

    def test_final_atomic_save_error_retains_codes_and_rolls_back_adoption(self):
        calls = []
        def replace(source, destination):
            calls.append(str(destination))
            if len(calls) == 2:
                error = PermissionError(13, "private-path-or-data")
                error.winerror = 32
                raise error
            return _replace_with_windows_retry(source, destination)
        with self.assertLogs("hullcirq.generation", level="ERROR") as logs, \
                patch("hullcirq.generation._replace_with_windows_retry", side_effect=replace):
            job = self.execute()
        self.assert_saved_diagnostic(job, "final_save", "PermissionError")
        self.assertEqual(job["error"]["errno"], 13)
        self.assertEqual(job["error"]["winerror"], 32)
        self.assertEqual(job["review_status"], "Awaiting Review")
        self.assertNotIn("private-path-or-data", str(job["error"]) + str(logs.output))
        self.assertEqual(len(calls), 3)

    def test_stream_event_save_failure_is_distinct_from_provider_request(self):
        calls = []
        def replace(source, destination):
            calls.append(str(destination))
            if len(calls) == 2:
                raise OSError(28, "private-storage-details")
            return _replace_with_windows_retry(source, destination)
        def response(messages, parameters, cancelled, event):
            event({"type": "usage", "usage": {"completion_tokens": 1}})
            return self.result()
        with self.assertLogs("hullcirq.generation", level="ERROR"), \
                patch("hullcirq.generation._replace_with_windows_retry", side_effect=replace):
            job = self.execute(response)
        self.assert_saved_diagnostic(job, "provider_event_save", "OSError")
        self.assertEqual(job["error"]["errno"], 28)
        self.assertNotIn("winerror", job["error"])

    def test_provider_exception_keeps_raw_error_text_out_of_diagnostics(self):
        with self.assertLogs("hullcirq.generation", level="ERROR") as logs:
            job = self.execute(lambda *args: (_ for _ in ()).throw(ValueError("private-token")))
        self.assert_saved_diagnostic(job, "provider_request", "ValueError")
        self.assertNotIn("private-token", str(job["error"]) + str(logs.output))

    def test_successful_s04_scope_and_legacy_error_reload_remain_unchanged(self):
        job = self.execute()
        self.assertEqual(job["execution_status"], "Completed")
        self.assertEqual(job["validation_status"], "Passed")
        self.assertIsNone(job["error"])
        self.assertEqual(job["checks"]["syntax"]["deferred_to_stage"], "local_synthesis")
        self.assertEqual(job["checks"]["behavioral"]["deferred_to_stage"], "local_netlist_simulation")
        stored = self.manager._stored_job(self.identifier)
        stored.update(execution_status="Failed", validation_status="Not Checked", review_status="Awaiting Review",
                      error={"code": "generation_error", "message": "Historical generic error."})
        self.manager._state["reviews"] = []
        self.manager._persist()
        before = self.manager.path.read_bytes()
        loaded = GenerationManager(self.store)
        self.addCleanup(loaded.close)
        self.assertEqual(loaded.path.read_bytes(), before)
        self.assertEqual(loaded._stored_job(self.identifier)["error"], stored["error"])
        self.assertNotIn("execution_phase", loaded._stored_job(self.identifier)["error"])


if __name__ == "__main__":
    unittest.main()

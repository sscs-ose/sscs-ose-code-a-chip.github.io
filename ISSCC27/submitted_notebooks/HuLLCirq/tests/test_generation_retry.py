"""Explicit retry bookkeeping with fake model responses; no inference or EDA."""
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

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from hullcirq.context import build_node_context
from hullcirq.domain import DomainError
from hullcirq.generation import GenerationManager, request_hash
from hullcirq.server import make_server
from hullcirq.store import ProjectStore
from test_m2_provider import FIXTURE_RTL, profile


class GenerationRetryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "project"
        self.store = ProjectStore(self.directory, PROJECT / "examples" / "m1_two_nodes.json")
        self.manager = GenerationManager(self.store)
        self.addCleanup(lambda: self.manager.close())
        for stage in ("global_settings", "graph_editor", "specifications"):
            run = self.store.validate(stage, self.store.envelope()["revision"]["id"])["runs"][-1]
            self.store.review(run["id"], "accepted", "Reviewed software fixture inputs.")
        self.manager.save_profile(profile(context_window=16384), None)

    @staticmethod
    def answer(status="Failed", code="output_truncated"):
        # Even a seemingly complete raw module must not become a candidate
        # when the provider declares a failed/truncated answer.
        return {"execution_status": status, "raw_content": "```verilog\n" + FIXTURE_RTL + "```",
                "raw_reasoning": "Preserved incomplete fixture reasoning.", "finish_reason": "length" if code else "stop",
                "usage": {"completion_tokens": 256}, "error": {"code": code, "message": "Fixture failure."} if code else None}

    def preview(self, **overrides):
        arguments = {"node_id": "node-producer", "revision_id": self.store.envelope()["revision"]["id"],
                     "operation": "generate", "base_job_id": None, "instruction": ""}
        arguments.update(overrides)
        return self.manager.preview(**arguments), arguments

    def start_fixture(self, *, answer=None, **overrides):
        preview, arguments = self.preview(**overrides)
        arguments.update(context_id=preview["context_id"], profile_revision_id=preview["profile_revision_id"])
        with patch("hullcirq.generation.ChatCompletionsClient") as provider, \
                patch("hullcirq.generation.check_rtl", return_value={"validation_status": "Unsupported", "diagnostics": [], "checks": {}}) as checks:
            provider.return_value.generate.return_value = answer or self.answer()
            envelope = self.manager.start(**arguments)
            self.manager._worker.join(timeout=5)
            self.assertFalse(self.manager._worker.is_alive())
            job = self.manager.job(envelope["generation"]["latest_job_id"])
            self.assertEqual(provider.return_value.generate.call_count, 1)
            if job["execution_status"] != "Completed":
                checks.assert_not_called()
        return job

    def update_profile(self, **overrides):
        llm = self.manager.envelope()["llm"]
        value = copy.deepcopy(llm["profile"])
        value.update(overrides)
        self.manager.save_profile(value, llm["profile_revision_id"])

    def assert_error(self, code, action):
        with self.assertRaises(DomainError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)

    def test_truncation_can_explicitly_retry_with_new_profile_and_preserves_original(self):
        original = self.start_fixture()
        original_saved = copy.deepcopy(self.manager._state["jobs"][0])
        design_bytes = self.store.state_path.read_bytes()
        self.assertIsNone(original["rtl"])
        self.assertEqual(original["validation_status"], "Not Checked")
        self.update_profile(max_output_tokens=1024, reasoning_effort="none")
        with patch("hullcirq.generation.ChatCompletionsClient") as provider:
            prepared, _ = self.preview(retry_of_job_id=original["id"])
            provider.assert_not_called()
        self.assertEqual(len(self.manager._state["jobs"]), 1)
        self.assertEqual(prepared["messages"], original["context"]["messages"])
        retried = self.start_fixture(answer=self.answer("Completed", None), retry_of_job_id=original["id"])
        self.assertNotEqual(retried["id"], original["id"])
        self.assertNotEqual(retried["context_id"], original["context_id"])
        self.assertNotEqual(retried["profile_revision_id"], original["profile_revision_id"])
        self.assertEqual(retried["retry_of_job_id"], original["id"])
        self.assertEqual(retried["context"]["retry_of_job_id"], original["id"])
        self.assertEqual(retried["context"]["messages"], original["context"]["messages"])
        self.assertEqual(retried["input_hash"], original["input_hash"])
        self.assertEqual(retried["revision_id"], original["revision_id"])
        self.assertEqual(retried["parameters"]["max_tokens"], 1024)
        self.assertEqual(retried["parameters"]["reasoning_effort"], "none")
        self.assertEqual(self.manager._state["jobs"][0], original_saved)
        self.assertEqual(self.store.state_path.read_bytes(), design_bytes)
        self.assertEqual(retried["execution_status"], "Completed")
        self.assertEqual(retried["validation_status"], "Unsupported")
        self.assertEqual(retried["review_status"], "Awaiting Review")

    def test_failed_retry_retains_both_failures_without_automatic_resubmission(self):
        original = self.start_fixture()
        retry = self.start_fixture(retry_of_job_id=original["id"])
        self.assertEqual([job["execution_status"] for job in self.manager._state["jobs"]], ["Failed", "Failed"])
        self.assertEqual(retry["raw_content"], original["raw_content"])
        self.assertEqual(retry["raw_reasoning"], original["raw_reasoning"])
        self.assertIsNone(retry["rtl"])
        with patch("hullcirq.generation.ChatCompletionsClient") as provider:
            self.manager.envelope()
            provider.assert_not_called()
        self.assertEqual(len(self.manager._state["jobs"]), 2)

    def test_retry_lineage_survives_restart_without_mutation(self):
        original = self.start_fixture()
        retry = self.start_fixture(retry_of_job_id=original["id"])
        saved = self.manager.path.read_bytes()
        self.manager.close()
        self.manager = GenerationManager(ProjectStore(self.directory))
        self.assertEqual(self.manager.path.read_bytes(), saved)
        self.assertEqual(self.manager.job(retry["id"])["retry_of_job_id"], original["id"])

    def test_cancelled_and_interrupted_terminal_jobs_can_be_retried(self):
        for status in ("Cancelled", "Interrupted"):
            with self.subTest(status=status):
                original = self.start_fixture(answer=self.answer(status))
                prepared, _ = self.preview(retry_of_job_id=original["id"])
                self.assertEqual(prepared["retry_of_job_id"], original["id"])

    def test_completed_active_and_unfinished_parents_are_rejected(self):
        original = self.start_fixture()
        parent = self.manager._state["jobs"][0]
        for status, finished in (("Completed", original["finished_at"]), ("Running", None), ("Queued", None), ("Failed", None)):
            with self.subTest(status=status, finished=finished):
                parent.update(execution_status=status, finished_at=finished)
                self.assert_error("invalid_retry_parent", lambda: self.preview(retry_of_job_id=original["id"]))
        parent.update(execution_status="Failed", finished_at=original["finished_at"])

    def test_wrong_node_and_missing_parent_are_rejected(self):
        original = self.start_fixture()
        self.assert_error("retry_source_conflict", lambda: self.preview(node_id="node-consumer", retry_of_job_id=original["id"]))
        self.assert_error("job_not_found", lambda: self.preview(retry_of_job_id="missing-generation"))

    def test_changed_design_revision_is_rejected_even_for_layout_only_change(self):
        original = self.start_fixture()
        envelope = self.store.envelope()
        changed = copy.deepcopy(envelope["design"])
        changed["layout"]["nodes"]["node-producer"]["x"] += 1
        self.store.save(changed, envelope["revision"]["id"])
        self.assert_error("retry_source_conflict", lambda: self.preview(retry_of_job_id=original["id"]))

    def test_changed_instruction_or_input_fingerprint_is_rejected(self):
        original = self.start_fixture(instruction="Original fixture request.")
        self.assert_error("retry_request_conflict", lambda: self.preview(retry_of_job_id=original["id"]))
        parent = self.manager._state["jobs"][0]
        parent["input_hash"] = "0" * 64
        self.assert_error("retry_source_conflict", lambda: self.preview(instruction=original["instruction"], retry_of_job_id=original["id"]))

    def test_retry_hash_cannot_be_replaced_with_normal_preview_hash(self):
        original = self.start_fixture()
        normal, arguments = self.preview()
        retry, _ = self.preview(retry_of_job_id=original["id"])
        self.assertNotEqual(normal["context_id"], retry["context_id"])
        with patch("hullcirq.generation.ChatCompletionsClient") as provider:
            self.assert_error("context_conflict", lambda: self.manager.start(**arguments, context_id=normal["context_id"],
                profile_revision_id=normal["profile_revision_id"], retry_of_job_id=original["id"]))
            provider.assert_not_called()
        self.assertEqual(len(self.manager._state["jobs"]), 1)

    def test_omitted_or_null_retry_keeps_legacy_hash_and_schema(self):
        omitted, _ = self.preview()
        null, _ = self.preview(retry_of_job_id=None)
        self.assertEqual(omitted, null)
        self.assertNotIn("retry_of_job_id", omitted)
        job = self.start_fixture()
        self.assertNotIn("retry_of_job_id", job)
        self.assertNotIn("retry_of_job_id", job["context"])

    def test_invalid_retry_identifier_types_are_rejected(self):
        for value in ("", 1, True, [], {}):
            with self.subTest(value=value):
                self.assert_error("invalid_request", lambda: self.preview(retry_of_job_id=value))

    def test_retry_preserves_older_prompt_template_and_exact_messages(self):
        def historical_context(*args, **kwargs):
            kwargs["template_version"] = kwargs.get("template_version") or "node-verilog-2005-v7"
            return build_node_context(*args, **kwargs)

        with patch("hullcirq.generation.build_node_context", side_effect=historical_context):
            original = self.start_fixture()
        self.assertEqual(original["context"]["prompt_template_version"], "node-verilog-2005-v7")
        retried = self.start_fixture(retry_of_job_id=original["id"])
        self.assertEqual(retried["context"]["messages"], original["context"]["messages"])
        self.assertEqual(retried["context"]["prompt_template_version"], "node-verilog-2005-v7")
        self.manager.close()
        self.manager = GenerationManager(ProjectStore(self.directory))
        self.assertEqual(self.manager.job(retried["id"])["context"]["messages"], original["context"]["messages"])

    def test_failed_repair_retry_preserves_valid_base_candidate_without_using_failed_partial(self):
        base = self.start_fixture(answer=self.answer("Completed", None))
        failed = self.start_fixture(operation="repair", base_job_id=base["id"], instruction="Fixture correction.")
        retry = self.start_fixture(operation="repair", base_job_id=base["id"], instruction="Fixture correction.", retry_of_job_id=failed["id"])
        self.assertEqual(retry["base_job_id"], base["id"])
        self.assertEqual(retry["context"]["messages"], failed["context"]["messages"])
        self.assertIsNone(failed["rtl"])
        self.manager.close()
        self.manager = GenerationManager(ProjectStore(self.directory))
        self.assertEqual(self.manager.job(retry["id"])["retry_of_job_id"], failed["id"])

    def test_saved_forged_lineage_or_hash_is_rejected_without_overwriting(self):
        original = self.start_fixture()
        self.start_fixture(retry_of_job_id=original["id"])
        clean = copy.deepcopy(self.manager._state)
        self.manager.close()
        for forgery in ("hash", "context_only", "job_only", "self_parent", "forward_parent", "changed_messages"):
            with self.subTest(forgery=forgery):
                state = copy.deepcopy(clean)
                retry = state["jobs"][1]
                if forgery == "hash":
                    retry["context_id"] = "0" * 64
                elif forgery == "context_only":
                    del retry["retry_of_job_id"]
                elif forgery == "job_only":
                    del retry["context"]["retry_of_job_id"]
                elif forgery == "self_parent":
                    retry["retry_of_job_id"] = retry["context"]["retry_of_job_id"] = retry["id"]
                elif forgery == "forward_parent":
                    state["jobs"].reverse()
                elif forgery == "changed_messages":
                    retry["context"]["messages"][0]["content"] += " Altered retry."
                if forgery != "hash":
                    retry["context_id"] = request_hash(retry["context"], retry["profile_revision_id"], retry["parameters"], retry["operation"], retry["base_job_id"])
                self.manager.path.write_text(json.dumps(state), encoding="utf-8")
                corrupted = self.manager.path.read_bytes()
                self.assert_error("invalid_generation_store", lambda: GenerationManager(ProjectStore(self.directory)))
                self.assertEqual(self.manager.path.read_bytes(), corrupted)

    def test_http_preview_and_start_forward_retry_link_and_bind_hash(self):
        original = self.start_fixture()
        self.manager.close()
        server = make_server("127.0.0.1", 0, self.store, PROJECT)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def request(path, value):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
            try:
                connection.request("POST", path, json.dumps(value), {"Content-Type": "application/json"})
                response = connection.getresponse()
                return response.status, json.loads(response.read())
            finally:
                connection.close()

        try:
            arguments = {"node_id": original["node_id"], "revision_id": original["revision_id"], "retry_of_job_id": original["id"]}
            status, preview = request("/api/generation/context", arguments)
            self.assertEqual(status, 200, preview)
            self.assertEqual(preview["retry_of_job_id"], original["id"])
            arguments.update(context_id=preview["context_id"], profile_revision_id=preview["profile_revision_id"])
            with patch("hullcirq.generation.ChatCompletionsClient") as provider:
                provider.return_value.generate.return_value = self.answer()
                status, result = request("/api/generation/start", arguments)
                self.assertEqual(status, 202, result)
                server.generation._worker.join(timeout=5)
                self.assertFalse(server.generation._worker.is_alive())
                provider.return_value.generate.assert_called_once()
            retried = server.generation.envelope()["generation"]["jobs"][-1]
            self.assertEqual(retried["retry_of_job_id"], original["id"])
        finally:
            server.generation.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()

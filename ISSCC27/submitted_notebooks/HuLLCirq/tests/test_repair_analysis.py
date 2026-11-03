"""Isolated repair-advice lifecycle checks; no model, RTL edits, or EDA execution."""
import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from hullcirq.domain import DomainError
from hullcirq.repair_analysis import RepairAnalysisManager
from hullcirq.repair_guidance import build_repair_guidance, render_repair_instruction


class FakeGeneration:
    def __init__(self, job):
        self.saved_job = copy.deepcopy(job)
        self.profile = {"revision_id": "profile-one", "profile": {
            "id": "local", "name": "Isolated local model", "execution_location": "Local",
            "api_type": "chat_completions", "base_url": "http://127.0.0.1:11435/v1", "model": "isolated",
            "credential_env": "", "context_window": 16384, "max_output_tokens": 2000,
            "temperature": 0.2, "seed": 1, "timeout_seconds": 10, "reasoning_effort": "none"}}
        self.reservation, self.busy = None, False
        self.reservations, self.releases = [], []

    def _require_profile(self, identifier=None):
        if identifier is not None and identifier != self.profile["revision_id"]:
            raise DomainError("profile_conflict", "Provider changed.", 409)
        return copy.deepcopy(self.profile)

    def job(self, identifier):
        if identifier != self.saved_job["id"]:
            raise DomainError("job_not_found", "Missing fixture job.", 404)
        return copy.deepcopy(self.saved_job)

    def is_active(self):
        return self.busy or self.reservation is not None

    def reserve_batch(self, identifier):
        if self.is_active():
            raise DomainError("generation_busy", "Busy.", 409)
        self.reservation = identifier
        self.reservations.append(identifier)

    def release_batch(self, identifier):
        self.releases.append(identifier)
        if self.reservation == identifier:
            self.reservation = None


class FakeWorkflow:
    busy = False

    def is_active(self):
        return self.busy


class FakeBatches:
    def __init__(self, guidance):
        self.guidance = copy.deepcopy(guidance)

    def repair_guidance_for_run(self, run_id):
        if run_id != self.guidance["source"]["run_id"]:
            raise DomainError("repair_source_changed", "The synthesis source changed.", 409)
        return copy.deepcopy(self.guidance)


class RepairAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / ".work")
        self.root = Path(self.temp.name)
        self.store = type("IsolatedStore", (), {"state_path": self.root / "state.json"})()
        self.job = {"id": "candidate-one", "node_id": "node-one", "revision_id": "revision-one",
                    "operation": "generate", "rtl": "module node_one(input clk, output result);\n  unsupported_construct result;\nendmodule\n"}
        self.run = {"id": "synthesis-one", "candidate_id": self.job["id"], "node_id": self.job["node_id"],
                    "stage_id": "local_synthesis", "input_hash": "input-one", "execution_status": "Completed",
                    "validation_status": "Failed", "checks": {"executed": True, "stderr": "candidate.v:2: ERROR: unknown construct unsupported_construct", "stdout": ""},
                    "tool_configuration": {"mode": "generic"}, "diagnostics": []}
        design = {"nodes": [{"id": "node-one", "module_name": "node_one", "behavior": "Preserve the required behavior.",
                             "test_expectations": "Use original inputs.", "ports": []}],
                  "edges": [], "settings": {"reset_kind": "synchronous", "reset_active": "high"}}
        self.guidance = build_repair_guidance(design, self.run, self.job, [self.job], [self.run])
        self.assertTrue(self.guidance["analysis_required"])
        self.generation, self.workflow = FakeGeneration(self.job), FakeWorkflow()
        self.batches = FakeBatches(self.guidance)
        self.manager = RepairAnalysisManager(self.store, self.generation, self.workflow, self.batches)

    def tearDown(self):
        self.manager.close()
        self.temp.cleanup()

    @staticmethod
    def proposal():
        return {"changes": [{"cause": "The diagnosed construct is unsupported.", "locations": [2],
                             "actions": ["Replace the diagnosed construct with a typed Verilog-2005 signal."],
                             "preserve": ["Keep the required external ports and original behavior."],
                             "expected_result": "The unknown construct diagnostic should disappear.",
                             "uncertainty": "A new synthesis run is still required."}]}

    def result(self, **overrides):
        result = {"execution_status": "Completed", "raw_content": json.dumps(self.proposal()), "raw_reasoning": "",
                  "usage": {"completion_tokens": 99}, "finish_reason": "stop", "provider_request_id": "provider-one", "error": None, "events": []}
        return result | overrides

    def wait(self):
        self.manager._worker.join(timeout=3)
        self.assertFalse(self.manager._worker.is_alive(), "Isolated analysis worker did not finish")

    def complete(self, result=None):
        plan = self.manager.preview(self.run["id"])
        with patch("hullcirq.repair_analysis.ChatCompletionsClient.generate", return_value=result or self.result()) as provider:
            created = self.manager.start(plan["context_id"], "isolated-analysis-request")
            self.wait()
        return plan, self.manager.job(created["id"]), provider

    def test_preview_saves_exact_request_without_provider_or_candidate_mutation(self):
        with patch("hullcirq.repair_analysis.ChatCompletionsClient.generate") as provider:
            plan = self.manager.preview(self.run["id"])
            same = self.manager.preview(self.run["id"])
        provider.assert_not_called()
        self.assertEqual(plan["context_id"], same["context_id"])
        self.assertEqual(len(self.manager._state["plans"]), 1)
        self.assertEqual(self.manager.envelope()["repair_analysis"]["jobs"], [])
        self.assertIn("unsupported_construct", plan["messages"][1]["content"])
        self.assertIn("original_requirements", plan["messages"][1]["content"])
        self.assertEqual(self.generation.saved_job, self.job)
        self.assertIsNone(self.generation.reservation)

    def test_completed_advice_is_separate_saved_evidence_and_explicitly_reviewable(self):
        plan, job, provider = self.complete()
        provider.assert_called_once()
        self.assertEqual(job["execution_status"], "Completed")
        self.assertEqual(job["scope"], "unverified_repair_advice_no_rtl_edit")
        self.assertEqual(job["messages"], plan["messages"])
        self.assertEqual(job["profile"], plan["profile"])
        self.assertEqual(job["usage"], {"completion_tokens": 99})
        self.assertNotIn("rtl", job)
        self.assertNotIn("review_status", job)
        self.assertEqual(self.generation.saved_job, self.job)
        self.assertIsNone(self.generation.reservation)
        reviewed = self.manager.reviewed_guidance(job["id"], self.run["id"], self.guidance)
        self.assertTrue(reviewed["analysis_reviewed"])
        self.assertFalse(reviewed["analysis_required"])
        self.assertEqual(reviewed["changes"][-1]["locations"], [{"line": 2, "source": self.job["rtl"].splitlines()[1]}])
        self.assertEqual(reviewed["changes"][-1]["confidence"], "hypothesis")
        self.assertTrue(self.guidance["analysis_required"], "Explicit review must not mutate original guidance")
        self.assertIn("model_assisted_analysis_v1", render_repair_instruction(reviewed))
        self.assertEqual(reviewed["analysis_provenance"]["job_id"], job["id"])
        reopened = RepairAnalysisManager(self.store, self.generation, self.workflow, self.batches)
        try:
            self.assertEqual(reopened.job(job["id"])["raw_content"], job["raw_content"])
            self.assertEqual(reopened.job(job["id"])["proposal"], self.proposal())
        finally:
            reopened.close()

    def test_duplicate_request_reconnects_and_conflicting_id_never_resends(self):
        plan, job, provider = self.complete()
        with patch("hullcirq.repair_analysis.ChatCompletionsClient.generate") as repeated:
            self.assertEqual(self.manager.start(plan["context_id"], job["request_id"])["id"], job["id"])
            with self.assertRaises(DomainError) as error:
                self.manager.start("another-context", job["request_id"])
            self.assertEqual(error.exception.code, "request_conflict")
        repeated.assert_not_called()
        self.assertEqual(len(self.manager._state["jobs"]), 1)
        self.assertEqual(len(self.generation.reservations), 1)

    def test_source_or_profile_drift_rejects_before_provider(self):
        plan = self.manager.preview(self.run["id"])
        original = copy.deepcopy(self.batches.guidance)
        with patch("hullcirq.repair_analysis.ChatCompletionsClient.generate") as provider:
            self.batches.guidance["source"]["rtl_sha256"] = "changed"
            with self.assertRaises(DomainError) as error:
                self.manager.start(plan["context_id"], "source-drift-request")
            self.assertEqual(error.exception.code, "repair_analysis_source_changed")
            self.batches.guidance = original
            self.generation.profile["revision_id"] = "profile-new"
            with self.assertRaises(DomainError) as error:
                self.manager.start(plan["context_id"], "profile-drift-request")
            self.assertEqual(error.exception.code, "profile_conflict")
        provider.assert_not_called()
        self.assertFalse(self.manager._state["jobs"])

    def test_context_budget_preview_explains_recovery_and_start_rejects_without_provider(self):
        self.generation.profile["profile"]["context_window"] = 64
        plan = self.manager.preview(self.run["id"])
        self.assertFalse(plan["ready_to_start"])
        self.assertFalse(plan["context_budget"]["fits"])
        self.assertEqual(plan["context_budget"]["maximum_output_tokens"], 0)
        self.assertIn("lowering output alone cannot resolve", plan["gate_reason"])
        with self.assertRaises(DomainError) as error, patch("hullcirq.repair_analysis.ChatCompletionsClient.generate") as provider:
            self.manager.start(plan["context_id"], "oversized-analysis-request")
        self.assertEqual(error.exception.code, "context_budget")
        provider.assert_not_called()
        self.assertFalse(self.generation.reservations)
        self.generation.profile["profile"]["context_window"] = 16384
        plan = self.manager.preview(self.run["id"])
        for manager in (self.generation, self.workflow):
            manager.busy = True
            with self.assertRaises(DomainError) as error:
                self.manager.start(plan["context_id"], "competing-work-request")
            self.assertEqual(error.exception.code, "repair_analysis_busy")
            manager.busy = False
        self.assertFalse(self.manager._state["jobs"])

    def test_projection_keeps_current_source_whole_and_preserves_full_old_history(self):
        from hullcirq.provider import estimate_message_input
        from hullcirq.repair_analysis import ANALYSIS_PROJECTION, ANALYSIS_SYSTEM
        from hullcirq.verification import content_hash
        old_history = []
        for index in range(4):
            old_history.append({"job_id": f"previous-{index}", "base_job_id": "original", "run_id": f"run-{index}",
                                "rtl_sha256": "old-rtl", "base_rtl_sha256": "base-rtl", "outcome": {"outcome": "same_diagnostic"},
                                "instruction": "OLD INSTRUCTION " * 1000, "diff": "DIFF " * 1000})
        self.batches.guidance["recent_attempts"] = old_history
        self.batches.guidance["analysis_messages"][1]["content"] += "DUPLICATE OLD PROMPT " * 2000
        before = copy.deepcopy(self.batches.guidance)
        plan = self.manager.preview(self.run["id"])
        payload = json.loads(plan["messages"][1]["content"])
        self.assertEqual(plan["prompt_projection"], ANALYSIS_PROJECTION)
        self.assertEqual(payload["original_requirements"], self.guidance["original_requirements"])
        self.assertEqual(payload["rtl"], self.job["rtl"])
        self.assertEqual(payload["actual_diagnostics"], self.guidance["evidence"]["actionable_diagnostics"])
        self.assertEqual(plan["source_evidence"]["guidance"], before)
        self.assertEqual(self.batches.guidance, before)
        self.assertEqual(len(payload["recent_attempts"]), 1)
        self.assertEqual(payload["recent_attempts"][0]["diff"]["sha256"], content_hash(old_history[0]["diff"]))
        self.assertEqual(payload["recent_attempts"][0]["diff"]["omitted_characters"], len(old_history[0]["diff"]) - 200)
        self.assertEqual(payload["recent_attempts"][0]["outcome"], "same_diagnostic")
        self.assertEqual(plan["context_budget"]["provider_input_estimated_tokens"], estimate_message_input(plan["messages"]))
        self.assertTrue(plan["ready_to_start"])
        self.assertGreater(estimate_message_input([{"role": "system", "content": ANALYSIS_SYSTEM}, self.batches.guidance["analysis_messages"][1]]), 16384)
        reopened = RepairAnalysisManager(self.store, self.generation, self.workflow, self.batches)
        try:
            self.assertEqual(reopened._state["plans"], self.manager._state["plans"])
        finally:
            reopened.close()

    def test_output_only_recovery_uses_exact_saved_budget_and_never_changes_profile(self):
        original_profile = copy.deepcopy(self.generation.profile)
        initial = self.manager.preview(self.run["id"])
        input_size = initial["estimated_input_tokens"]
        self.generation.profile["profile"]["context_window"] = input_size + 1000
        plan = self.manager.preview(self.run["id"])
        self.assertFalse(plan["ready_to_start"])
        self.assertEqual(plan["context_budget"]["maximum_output_tokens"], 1000)
        self.assertIn("Lower the saved provider output limit", plan["gate_reason"])
        self.assertEqual(self.generation.profile["profile"]["max_output_tokens"], original_profile["profile"]["max_output_tokens"])
        self.generation.profile["profile"]["max_output_tokens"] = 1000
        self.generation.profile["revision_id"] = "profile-explicit-output-change"
        fresh = self.manager.preview(self.run["id"])
        self.assertTrue(fresh["ready_to_start"])
        self.assertEqual(fresh["context_budget"]["total_estimated_tokens"], fresh["context_budget"]["context_window"])
        self.assertEqual(fresh["messages"], plan["messages"])
        self.assertNotEqual(fresh["context_id"], plan["context_id"])

    def test_legacy_frozen_plan_identity_and_reopen_are_unchanged(self):
        from hullcirq.repair_analysis import ANALYSIS_SYSTEM
        from hullcirq.provider import estimate_message_input
        plan = self.manager.preview(self.run["id"])
        for key in ("prompt_projection", "source_evidence", "source_evidence_sha256", "context_budget"):
            plan.pop(key)
        plan["messages"] = [{"role": "system", "content": ANALYSIS_SYSTEM}, copy.deepcopy(self.guidance["analysis_messages"][1])]
        plan["estimated_input_tokens"] = estimate_message_input(plan["messages"])
        plan["context_id"] = self.manager._context_id(plan)
        self.manager._state["plans"] = [plan]
        self.manager._persist()
        original = self.manager.path.read_bytes()
        reopened = RepairAnalysisManager(self.store, self.generation, self.workflow, self.batches)
        try:
            self.assertEqual(reopened._state["plans"], [plan])
            self.assertEqual(reopened.path.read_bytes(), original)
        finally:
            reopened.close()

    def test_v2_projection_reopens_unchanged_after_v3_history_limit(self):
        from hullcirq.repair_analysis import LEGACY_ANALYSIS_PROJECTION, analysis_messages, analysis_budget, analysis_budget_reason
        from hullcirq.verification import object_hash
        plan = self.manager.preview(self.run["id"])
        plan["prompt_projection"] = LEGACY_ANALYSIS_PROJECTION
        plan["messages"] = analysis_messages(plan["source_evidence"]["guidance"], plan["source_evidence"]["rtl"], LEGACY_ANALYSIS_PROJECTION)
        plan["context_budget"] = analysis_budget(plan["messages"], plan["parameters"], plan["profile"])
        plan["estimated_input_tokens"] = plan["context_budget"]["provider_input_estimated_tokens"]
        plan["ready_to_start"] = plan["context_budget"]["fits"]
        plan["gate_reason"] = analysis_budget_reason(plan["context_budget"])
        plan["context_id"] = self.manager._context_id(plan)
        self.manager._state["plans"] = [plan]
        self.manager._persist()
        before = self.manager.path.read_bytes()
        reopened = RepairAnalysisManager(self.store, self.generation, self.workflow, self.batches)
        try:
            self.assertEqual(reopened.path.read_bytes(), before)
            self.assertEqual(reopened._state["plans"], [plan])
        finally:
            reopened.close()

    def test_changed_saved_projection_evidence_is_rejected_without_rewrite(self):
        self.manager.preview(self.run["id"])
        self.manager._state["plans"][0]["source_evidence"]["rtl"] += "// altered"
        self.manager._persist()
        before = self.manager.path.read_bytes()
        with self.assertRaises(DomainError) as error:
            RepairAnalysisManager(self.store, self.generation, self.workflow, self.batches)
        self.assertEqual(error.exception.code, "invalid_repair_analysis_store")
        self.assertEqual(self.manager.path.read_bytes(), before)

    def test_malformed_or_unanchored_advice_is_retained_but_cannot_be_applied(self):
        cases = ["not JSON", json.dumps({"changes": []}),
                 json.dumps({"changes": [self.proposal()["changes"][0] | {"locations": [999]}]}),
                 json.dumps({"changes": [self.proposal()["changes"][0] | {"locations": [True]}]})]
        plan = self.manager.preview(self.run["id"])
        for index, raw in enumerate(cases):
            with self.subTest(raw=raw), patch("hullcirq.repair_analysis.ChatCompletionsClient.generate", return_value=self.result(raw_content=raw)):
                job = self.manager.start(plan["context_id"], f"malformed-request-{index}")
                self.wait()
                job = self.manager.job(job["id"])
                self.assertEqual(job["execution_status"], "Failed")
                self.assertEqual(job["error"]["code"], "invalid_analysis_proposal")
                self.assertEqual(job["raw_content"], raw)
                self.assertIsNone(job["proposal"])
                with self.assertRaises(DomainError):
                    self.manager.reviewed_guidance(job["id"], self.run["id"], self.guidance)
        self.assertEqual(self.generation.saved_job, self.job)

    def test_timeout_partial_output_and_stream_failure_remain_non_applicable(self):
        plan = self.manager.preview(self.run["id"])
        for index, code in enumerate(("timeout", "stream_incomplete", "output_truncated")):
            partial = "{partial answer"
            with self.subTest(code=code), patch("hullcirq.repair_analysis.ChatCompletionsClient.generate", return_value=self.result(execution_status="Failed", raw_content=partial, error={"code": code, "message": "fixture"}, finish_reason=None)):
                job = self.manager.start(plan["context_id"], f"failed-transport-{index}")
                self.wait()
                job = self.manager.job(job["id"])
                self.assertEqual(job["error"]["code"], code)
                self.assertEqual(job["raw_content"], partial)
                self.assertIsNone(job["proposal"])
        self.assertIsNone(self.generation.reservation)

    def test_stream_partial_survives_adapter_exception(self):
        def failing_provider(client, messages, parameters, cancelled, on_event):
            on_event({"type": "content", "content": "retained partial"})
            on_event({"type": "reasoning", "content": "retained reasoning"})
            raise RuntimeError("isolated adapter failure")
        plan = self.manager.preview(self.run["id"])
        with patch("hullcirq.repair_analysis.ChatCompletionsClient.generate", new=failing_provider):
            created = self.manager.start(plan["context_id"], "partial-exception-request")
            self.wait()
        observed = self.manager.job(created["id"])
        self.assertEqual(observed["raw_content"], "retained partial")
        self.assertEqual(observed["raw_reasoning"], "retained reasoning")
        self.assertEqual(observed["execution_status"], "Failed")
        self.assertEqual(len(observed["events"]), 2)
        self.assertIsNone(self.generation.reservation)

    def test_cancel_blocks_other_analysis_and_retains_partial_without_proposal(self):
        entered = threading.Event()
        def cancelled_provider(client, messages, parameters, cancelled, on_event):
            on_event({"type": "content", "content": "partial before cancellation"})
            entered.set()
            self.assertTrue(cancelled.wait(2))
            return self.result(execution_status="Cancelled", raw_content="partial before cancellation", error={"code": "cancelled", "message": "fixture"}, finish_reason=None)
        plan = self.manager.preview(self.run["id"])
        with patch("hullcirq.repair_analysis.ChatCompletionsClient.generate", new=cancelled_provider):
            created = self.manager.start(plan["context_id"], "cancel-analysis-request")
            self.assertTrue(entered.wait(2))
            self.assertTrue(self.manager.is_active())
            self.assertTrue(self.generation.is_active())
            with self.assertRaises(DomainError):
                self.manager.preview(self.run["id"])
            self.assertEqual(self.manager.start(plan["context_id"], "cancel-analysis-request")["id"], created["id"])
            self.manager.cancel(created["id"])
            self.wait()
        observed = self.manager.job(created["id"])
        self.assertEqual(observed["execution_status"], "Cancelled")
        self.assertEqual(observed["raw_content"], "partial before cancellation")
        self.assertIsNone(observed["proposal"])
        self.assertIsNone(self.generation.reservation)
        with self.assertRaises(DomainError):
            self.manager.cancel(created["id"])

    def test_source_change_during_request_keeps_raw_advice_but_rejects_application(self):
        def changed_provider(client, messages, parameters, cancelled, on_event):
            self.batches.guidance["source"]["run_sha256"] = "new-result"
            return self.result()
        plan = self.manager.preview(self.run["id"])
        with patch("hullcirq.repair_analysis.ChatCompletionsClient.generate", new=changed_provider):
            created = self.manager.start(plan["context_id"], "source-changes-during-request")
            self.wait()
        observed = self.manager.job(created["id"])
        self.assertEqual(observed["execution_status"], "Failed")
        self.assertEqual(observed["error"]["code"], "repair_analysis_source_changed")
        self.assertEqual(observed["raw_content"], json.dumps(self.proposal()))
        self.assertIsNone(observed["proposal"])

    def test_restart_marks_saved_active_analysis_interrupted_without_resending(self):
        plan, job, _ = self.complete()
        self.manager._state["jobs"][0].update(execution_status="Running", proposal=None)
        self.manager._persist()
        with patch("hullcirq.repair_analysis.ChatCompletionsClient.generate") as provider:
            reopened = RepairAnalysisManager(self.store, self.generation, self.workflow, self.batches)
        try:
            observed = reopened.job(job["id"])
            self.assertEqual(observed["execution_status"], "Interrupted")
            self.assertEqual(observed["raw_content"], job["raw_content"])
            self.assertFalse(reopened.is_active())
            self.assertEqual(reopened.start(plan["context_id"], job["request_id"])["id"], job["id"])
            provider.assert_not_called()
        finally:
            reopened.close()

    def test_corrupted_completed_advice_rejected_without_rewriting_store(self):
        _, job, _ = self.complete()
        self.manager._state["jobs"][0]["raw_content"] = "corrupted answer"
        self.manager._persist()
        before = self.manager.path.read_bytes()
        with self.assertRaises(DomainError) as error:
            RepairAnalysisManager(self.store, self.generation, self.workflow, self.batches)
        self.assertEqual(error.exception.code, "invalid_repair_analysis_store")
        self.assertEqual(self.manager.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()

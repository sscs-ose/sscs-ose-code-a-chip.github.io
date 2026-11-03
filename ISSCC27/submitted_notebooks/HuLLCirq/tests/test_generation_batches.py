"""Isolated queue/provenance QA: fake provider and synthesis, no model or EDA."""
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
from hullcirq.domain import DomainError, IMPLEMENTED_STAGES
from hullcirq.generation import GenerationManager
from hullcirq.generation_batches import GenerationBatchManager, POLICY_V2, pack_batch_context, synthesis_repair_evidence
from hullcirq.provider import estimate_message_input
from hullcirq.store import ProjectStore
from hullcirq.workflow import WorkflowManager
from hullcirq.verification import object_hash, content_hash
from test_adoption_policy import design_fixture, software_profile


class GenerationBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".work")
        self.addCleanup(self.temp.cleanup)
        self.store = ProjectStore(self.temp.name)
        self.store.save(design_fixture(False), self.store.envelope()["revision"]["id"])
        self.store.set_review_policy("accept_on_pass", True, "Software queue QA only", self.store.review_policy()["id"])
        self.revision = self.store.envelope()["revision"]["id"]
        for stage in IMPLEMENTED_STAGES:
            self.store.validate(stage, self.revision)
        self.generation = GenerationManager(self.store)
        profile = software_profile(); profile.update(context_window=32768, max_output_tokens=2048)
        self.generation.save_profile(profile)
        self.workflow = WorkflowManager(self.store, self.generation, synthesizer={"kind": "native", "executable": "yosys"})
        self.manager = GenerationBatchManager(self.store, self.generation, self.workflow)
        self.addCleanup(self.close)
        self.calls = []

    def close(self):
        self.manager.close(); self.generation.close(); self.workflow.close()
        for manager in (self.manager, self.generation):
            if manager._worker:
                manager._worker.join(5)

    def response(self, messages, parameters, cancelled, event):
        self.calls.append(copy.deepcopy(messages))
        with self.generation.lock:
            job = self.generation._state["jobs"][-1]
            rtl = job["context"]["requested_module_header"] + "endmodule\n"
        return {"execution_status": "Completed", "raw_content": "```verilog\n" + rtl + "```", "error": None, "finish_reason": "stop"}

    def run_batch(self, plan=None, request_id="software-batch-request", response=None):
        plan = plan or self.manager.preview(self.revision)
        with patch("hullcirq.generation.ChatCompletionsClient") as provider, patch("hullcirq.generation.verify_behavior", side_effect=AssertionError("S04 does not run behavior")):
            provider.return_value.generate.side_effect = response or self.response
            batch = self.manager.start(plan["plan_id"], request_id)["generation_batches"]["batches"][-1]
            self.manager._worker.join(10)
            self.assertFalse(self.manager._worker.is_alive())
        return self.manager.batch(batch["id"])

    def test_two_distinct_calls_retain_actual_conversation_and_reload_exactly(self):
        plan = self.manager.preview(self.revision)
        before = self.store.state_path.read_bytes()
        self.assertTrue(plan["ready_to_start"])
        self.assertEqual(len(self.calls), 0)
        batch = self.run_batch(plan)
        self.assertEqual([item["status"] for item in batch["items"]], ["Passed", "Passed"])
        self.assertEqual(batch["validation_status"], "Passed")
        self.assertEqual(len(self.calls), 2)
        jobs = self.generation._state["jobs"]
        self.assertEqual(jobs[0]["context"]["batch_context"]["prior_job_ids"], [])
        self.assertEqual(jobs[1]["context"]["batch_context"]["prior_job_ids"], [jobs[0]["id"]])
        self.assertIn({"role": "assistant", "content": jobs[0]["raw_content"]}, self.calls[1])
        self.assertEqual(jobs[1]["context"]["batch_context"]["packing"][0]["representation"], "exact_user_and_assistant")
        self.assertEqual(self.calls[1][-1], plan["items"][1]["context"]["messages"][-1])
        self.assertEqual(self.store.state_path.read_bytes(), before)
        self.assertEqual(len(self.generation._state["reviews"]), 2)
        raw_generation, raw_batch = self.generation.path.read_bytes(), self.manager.path.read_bytes()
        loaded = GenerationManager(self.store)
        loaded_batch = GenerationBatchManager(self.store, loaded, self.workflow)
        self.addCleanup(loaded.close); self.addCleanup(loaded_batch.close)
        self.assertEqual(loaded.path.read_bytes(), raw_generation)
        self.assertEqual(loaded_batch.path.read_bytes(), raw_batch)
        self.assertEqual(loaded_batch.batch(batch["id"])["validation_status"], "Passed")
        self.assertEqual(self.manager.preview(self.revision)["items"], [])

    def test_request_idempotency_and_live_reservation(self):
        entered, release = threading.Event(), threading.Event()
        def hold(*args):
            entered.set(); release.wait(3)
            return self.response(*args)
        plan = self.manager.preview(self.revision)
        with patch("hullcirq.generation.ChatCompletionsClient") as provider:
            provider.return_value.generate.side_effect = hold
            first = self.manager.start(plan["plan_id"], "software-same-request")["generation_batches"]["batches"][-1]
            self.assertTrue(entered.wait(2))
            self.assertTrue(self.generation.is_active())
            self.assertEqual(self.manager.start(plan["plan_id"], "software-same-request")["generation_batches"]["batches"][-1]["id"], first["id"])
            preview = self.generation.preview("node-producer", self.revision)
            with self.assertRaises(DomainError) as caught:
                self.generation.start("node-producer", self.revision, preview["context_id"], preview["profile_revision_id"])
            self.assertEqual(caught.exception.code, "generation_batch_busy")
            with self.assertRaises(DomainError):
                self.generation.save_profile(self.generation._profile()["profile"], self.generation._profile()["revision_id"])
            release.set(); self.manager._worker.join(10)
        self.assertEqual(len(self.calls), 2)
        self.assertFalse(self.generation.is_active())
        self.assertEqual(len(self.manager._state["batches"]), 1)

    def test_saved_validation_uses_raw_candidate_provenance_and_rejects_changed_source(self):
        self.run_batch()
        def synthesize(rtl, module, configuration, directory, cancelled):
            return {"validation_status": "Passed", "executed": True, "exit_code": 0,
                    "diagnostics": [], "netlist": rtl, "netlist_sha256": content_hash(rtl)}
        with patch("hullcirq.workflow.synthesize_generic", synthesize):
            self.workflow.start_batch(self.revision, "software-startup-validation")
            self.workflow._batch_worker.join(10)
            self.assertFalse(self.workflow.is_active())
        before = {manager.path: manager.path.read_bytes() for manager in (self.generation, self.workflow, self.manager)}
        with patch.object(self.generation, "job", side_effect=AssertionError("Startup validation must not decorate saved jobs")), \
                patch.object(self.generation, "_stored_job", wraps=self.generation._stored_job) as raw:
            restored_workflow = WorkflowManager(self.store, self.generation)
            self.addCleanup(restored_workflow.close)
            restored_batch = GenerationBatchManager(self.store, self.generation, restored_workflow)
            self.addCleanup(restored_batch.close)
            self.assertGreater(raw.call_count, len(self.generation._state["jobs"]))
            original = self.generation._state["jobs"][0]["node_id"]
            try:
                self.generation._state["jobs"][0]["node_id"] = "changed-saved-node"
                for constructor, code in ((lambda: WorkflowManager(self.store, self.generation), "invalid_workflow_store"),
                                          (lambda: GenerationBatchManager(self.store, self.generation, restored_workflow), "invalid_generation_batch_store")):
                    with self.subTest(code=code), self.assertRaises(DomainError) as caught:
                        constructor()
                    self.assertEqual(caught.exception.code, code)
            finally:
                self.generation._state["jobs"][0]["node_id"] = original
        for path, contents in before.items():
            self.assertEqual(path.read_bytes(), contents)

    def test_individual_provider_failure_is_retained_and_next_call_continues(self):
        def answer(*args):
            result = self.response(*args)
            if len(self.calls) == 1:
                result.update(execution_status="Failed", error={"code": "output_truncated", "message": "Software output limit"})
            return result
        batch = self.run_batch(response=answer)
        self.assertEqual([item["status"] for item in batch["items"]], ["Failed", "Passed"])
        self.assertEqual(batch["execution_status"], "Completed")
        self.assertEqual(batch["validation_status"], "Failed")
        self.assertEqual(len(self.calls), 2)
        self.assertIn({"role": "assistant", "content": self.generation._state["jobs"][0]["raw_content"]}, self.calls[1])

    def test_cancel_prevents_next_model_request(self):
        entered = threading.Event()
        def hold(messages, parameters, cancelled, event):
            entered.set(); cancelled.wait(3)
            return self.response(messages, parameters, cancelled, event)
        plan = self.manager.preview(self.revision)
        with patch("hullcirq.generation.ChatCompletionsClient") as provider:
            provider.return_value.generate.side_effect = hold
            batch = self.manager.start(plan["plan_id"], "software-cancel-request")["generation_batches"]["batches"][-1]
            self.assertTrue(entered.wait(2))
            self.manager.cancel(batch["id"]); self.manager._worker.join(10)
        self.assertEqual(self.manager.batch(batch["id"])["execution_status"], "Cancelled")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(self.generation._state["reviews"]), 0)

    def test_saved_design_change_stops_sequence(self):
        entered = threading.Event()
        def hold(messages, parameters, cancelled, event):
            entered.set(); cancelled.wait(3)
            return self.response(messages, parameters, cancelled, event)
        plan = self.manager.preview(self.revision)
        with patch("hullcirq.generation.ChatCompletionsClient") as provider:
            provider.return_value.generate.side_effect = hold
            batch = self.manager.start(plan["plan_id"], "software-change-request")["generation_batches"]["batches"][-1]
            self.assertTrue(entered.wait(2))
            design = self.store.envelope()["design"]; design["nodes"][0]["description"] = "Changed saved specification"
            self.store.save(design, self.revision)
            self.manager._worker.join(10)
        after = self.manager.batch(batch["id"])
        self.assertEqual(after["execution_status"], "Failed")
        self.assertEqual(after["error"]["code"], "batch_source_changed")
        self.assertLessEqual(len(self.calls), 1)
        self.assertFalse(after["source_current"])

    def test_restart_marks_active_history_interrupted_without_resend(self):
        batch = self.run_batch()
        self.manager._state["batches"][0]["execution_status"] = "Running"
        self.manager._persist()
        loaded = GenerationBatchManager(self.store, self.generation, self.workflow)
        self.addCleanup(loaded.close)
        self.assertEqual(loaded.batch(batch["id"])["execution_status"], "Interrupted")
        self.assertFalse(loaded.is_active())
        self.assertEqual(len(self.calls), 2)

    def test_tampered_conversation_metadata_fails_saved_generation_validation(self):
        self.run_batch()
        self.generation._state["jobs"][-1]["context"]["batch_context"]["packing"][0]["representation"] = "forged"
        self.generation._persist()
        with self.assertRaises(DomainError) as caught:
            GenerationManager(self.store)
        self.assertEqual(caught.exception.code, "invalid_generation_store")

    def test_context_packing_explicitly_records_omissions_and_never_drops_contract(self):
        self.run_batch()
        prior = copy.deepcopy(self.generation._state["jobs"][0])
        prior["context"]["messages"][-1]["content"] = "Long original request" * 3000
        base = self.generation.preview("node-consumer", self.revision)
        profile = copy.deepcopy(self.generation._profile()["profile"])
        profile["context_window"] = estimate_message_input(base["messages"]) + 5000
        packed = pack_batch_context(base, [prior], profile, {"batch_id": "software", "index": 1, "prior_job_ids": [prior["id"]], "source_workflow_run_id": None})
        self.assertEqual(packed["messages"][-1], base["messages"][-1])
        self.assertEqual(packed["batch_context"]["packing"][0]["representation"], "compact_user_exact_assistant")
        self.assertIn({"role": "assistant", "content": prior["raw_content"]}, packed["messages"])
        self.assertEqual(packed["batch_context"]["ledger"][0]["request_messages_sha256"], object_hash(prior["context"]["messages"]))
        self.assertLessEqual(estimate_message_input(packed["messages"]) + profile["max_output_tokens"], profile["context_window"])

    def test_v2_empty_transport_failures_never_duplicate_full_repair_prompts(self):
        self.run_batch()
        prior = copy.deepcopy(self.generation._state["jobs"][0])
        prior.update(raw_content="", rtl=None, execution_status="Failed", error={"code": "connection_error"})
        prior["context"]["messages"][-1]["content"] = "Saved failed request " * 10000
        base = self.generation.preview("node-consumer", self.revision)
        profile = copy.deepcopy(self.generation._profile()["profile"])
        # Only 100 bytes of optional overhead fit: the complete source fits,
        # but the ledger does not. Durable references must suffice.
        profile["context_window"] = estimate_message_input(base["messages"]) + profile["max_output_tokens"] + 100
        packed = pack_batch_context(base, [prior], profile, {"packing_policy_version": POLICY_V2["kind"]})
        self.assertEqual(packed["messages"], base["messages"])
        self.assertEqual(packed["batch_context"]["packing"][0]["representation"], "saved_reference_only")
        self.assertEqual(packed["batch_context"]["ledger"][0]["request_messages_sha256"], object_hash(prior["context"]["messages"]))
        self.assertFalse(packed["batch_context"]["ledger_projection"]["sent"])
        budget = packed["context_budget"]
        self.assertTrue(budget["fits"])
        self.assertEqual(budget["provider_input_estimated_tokens"], estimate_message_input(packed["messages"]))
        self.assertEqual(budget["maximum_output_tokens"], profile["max_output_tokens"] + 100)

    def test_v2_blocked_budget_reports_actual_complete_source_without_dropping_it(self):
        base = self.generation.preview("node-consumer", self.revision)
        profile = copy.deepcopy(self.generation._profile()["profile"])
        profile["context_window"] = estimate_message_input(base["messages"]) + profile["max_output_tokens"] - 1
        with self.assertRaises(DomainError) as caught:
            pack_batch_context(base, [], profile, {"packing_policy_version": POLICY_V2["kind"]})
        budget = caught.exception.context_budget
        self.assertFalse(budget["fits"])
        self.assertEqual(budget["maximum_output_tokens"], profile["max_output_tokens"] - 1)
        self.assertEqual(budget["provider_input_estimated_tokens"], estimate_message_input(base["messages"]))

    def test_synthesis_repair_binds_exact_failure_and_excludes_tool_unavailable(self):
        self.run_batch()
        def fail(rtl, module, configuration, directory, cancelled):
            return {"validation_status": "Failed", "executed": True, "exit_code": 1, "diagnostics": [{"code": "software_parse_error", "message": "Exact saved fixture line 9 error"}], "netlist": None}
        with patch("hullcirq.workflow.synthesize_generic", fail):
            self.workflow.start_batch(self.revision, "software-failed-synthesis")
            self.workflow._batch_worker.join(10)
        before_read = [manager.path.read_bytes() for manager in (self.generation, self.workflow, self.manager)]
        with patch.object(self.generation, "job", side_effect=AssertionError("Read-only error display must not decorate or requalify old generation jobs")):
            sources = self.manager.repair_sources()
        self.assertEqual(len(sources), 2)
        self.assertTrue(all(source["repair_explanation"]["issues"] for source in sources))
        self.assertEqual([manager.path.read_bytes() for manager in (self.generation, self.workflow, self.manager)], before_read)
        plan = self.manager.preview(self.revision, "synthesis_repair")
        self.assertEqual(len(plan["items"]), 2)
        self.assertTrue(all(item["operation"] == "repair" for item in plan["items"]))
        self.assertIn("Exact saved fixture line 9 error", plan["items"][0]["instruction"])
        self.assertFalse(plan["ready_to_start"])
        self.assertTrue(all(item["repair_guidance"]["analysis_required"] for item in plan["items"]))
        for item in plan["items"]:
            explanation = item["repair_explanation"]
            self.assertEqual(explanation["source"]["candidate_id"], item["base_job_id"])
            self.assertEqual(explanation["source"]["run_id"], item["source_workflow_run_id"])
            self.assertNotIn("repair_explanation", item["repair_guidance"])
            self.assertEqual(explanation["issues"][0]["confidence"], "unknown")
        self.assertEqual(len(self.calls), 2)
        plan = self.manager.preview(self.revision, "synthesis_repair", instruction="Explicit software fixture correction: preserve the frozen interface.")
        batch = self.run_batch(plan, "software-repair-request")
        self.assertEqual([item["status"] for item in batch["items"]], ["Passed", "Passed"])
        self.assertEqual(len(self.calls), 4)
        for item in batch["items"]:
            job = self.generation.job(item["job_id"])
            self.assertEqual(job["context"]["batch_context"]["source_workflow_run_id"], item["source_workflow_run_id"])
            self.assertEqual(job["base_job_id"], item["base_job_id"])
            self.assertEqual(job["context"]["batch_context"]["repair_guidance"], item["repair_guidance"])
            self.assertNotIn("repair_explanation", job["context"]["batch_context"])
        raw_generation, raw_batch = self.generation.path.read_bytes(), self.manager.path.read_bytes()
        loaded = GenerationManager(self.store)
        loaded_batch = GenerationBatchManager(self.store, loaded, self.workflow)
        self.addCleanup(loaded.close); self.addCleanup(loaded_batch.close)
        self.assertEqual(loaded.path.read_bytes(), raw_generation)
        self.assertEqual(loaded_batch.path.read_bytes(), raw_batch)
        self.assertEqual(loaded_batch.batch(batch["id"])["validation_status"], "Passed")
        self.assertEqual(self.manager.preview(self.revision, "synthesis_repair")["items"], [])

    def test_explicit_remaining_retry_retains_failed_answer_and_allows_same_provider_settings(self):
        def answer(*args):
            result = self.response(*args)
            if len(self.calls) == 1:
                result.update(execution_status="Failed", error={"code": "output_truncated", "message": "Software output limit"})
            return result
        old = self.run_batch(response=answer)
        profile = copy.deepcopy(self.generation._profile()["profile"])
        profile["max_output_tokens"] = 4096
        self.generation.save_profile(profile, self.generation._profile()["revision_id"])
        plan = self.manager.preview(self.revision, retry_batch_id=old["id"])
        self.assertEqual(len(plan["items"]), 1)
        self.assertEqual(plan["items"][0]["node_id"], old["items"][0]["node_id"])
        new = self.run_batch(plan, "software-explicit-conversation-retry")
        self.assertEqual(new["validation_status"], "Passed")
        job = self.generation.job(new["items"][0]["job_id"])
        self.assertEqual(job["context"]["batch_context"]["seed_job_ids"], [item["job_id"] for item in old["items"]])
        self.assertNotEqual(job["profile_revision_id"], self.generation.job(old["items"][0]["job_id"])["profile_revision_id"])
        loaded = GenerationManager(self.store)
        loaded_batch = GenerationBatchManager(self.store, loaded, self.workflow)
        self.addCleanup(loaded.close); self.addCleanup(loaded_batch.close)
        self.assertEqual(loaded_batch.batch(new["id"])["validation_status"], "Passed")

    def test_fresh_repair_after_empty_transport_failure_executes_exact_source_and_reloads(self):
        self.run_batch()
        def fail(rtl, module, configuration, directory, cancelled):
            return {"validation_status": "Failed", "executed": True, "exit_code": 1,
                    "diagnostics": [{"code": "software_parse_error", "message": "Saved fixture line 9 error"}], "netlist": None}
        with patch("hullcirq.workflow.synthesize_generic", fail):
            self.workflow.start_batch(self.revision, "software-recovery-failed-synthesis")
            self.workflow._batch_worker.join(10)
        original = self.manager.preview(self.revision, "synthesis_repair", instruction="Explicit fixture correction.")
        def disconnected(*args):
            return {"execution_status": "Failed", "raw_content": "", "error": {"code": "connection_error", "message": "Isolated provider unavailable"}, "finish_reason": None}
        failed = self.run_batch(original, "software-recovery-connection-failure", response=disconnected)
        self.assertEqual(failed["items"][0]["status"], "Failed")
        recovery = self.manager.preview(self.revision, "synthesis_repair", instruction="Explicit fixture correction.")
        self.assertTrue(recovery["ready_to_start"])
        item = recovery["items"][0]
        self.assertEqual(item["base_job_id"], original["items"][0]["base_job_id"])
        self.assertEqual(item["expected_latest_job_id"], failed["items"][0]["job_id"])
        self.assertEqual(item["source_recovery"]["failed_job_ids"], [failed["items"][0]["job_id"]])
        completed = self.run_batch(recovery, "software-recovery-fresh-success")
        self.assertEqual(completed["validation_status"], "Passed")
        latest = self.generation.job(completed["items"][0]["job_id"])
        self.assertEqual(latest["base_job_id"], original["items"][0]["base_job_id"])
        loaded = GenerationManager(self.store)
        loaded_batches = GenerationBatchManager(self.store, loaded, self.workflow)
        self.addCleanup(loaded.close); self.addCleanup(loaded_batches.close)
        self.assertEqual(loaded_batches.batch(completed["id"])["validation_status"], "Passed")

    def test_repair_status_read_view_does_not_decorate_each_source_job_again(self):
        self.run_batch()
        def fail(rtl, module, configuration, directory, cancelled):
            return {"validation_status": "Failed", "executed": True, "exit_code": 1,
                    "diagnostics": [{"code": "software_parse_error", "message": "Exact saved fixture error"}], "netlist": None}
        with patch("hullcirq.workflow.synthesize_generic", fail):
            self.workflow.start_batch(self.revision, "software-repair-summary-perf")
            self.workflow._batch_worker.join(10)
        with patch.object(self.generation, "job", side_effect=AssertionError("Comparison must use immutable source fields, not decorate full jobs")):
            result = self.workflow.envelope()
        summaries = [node["repair_status"] for node in result["workflow_nodes"] if node["stage_id"] == "local_synthesis"]
        self.assertEqual([item["outcome"] for item in summaries], ["no_baseline", "no_baseline"])

    def test_repair_retry_reuses_frozen_instruction_without_new_projection(self):
        self.run_batch()
        def fail(rtl, module, configuration, directory, cancelled):
            return {"validation_status": "Failed", "executed": True, "exit_code": 1,
                    "diagnostics": [{"code": "software_parse_error", "message": "Exact saved fixture error"}], "netlist": None}
        with patch("hullcirq.workflow.synthesize_generic", fail):
            self.workflow.start_batch(self.revision, "software-frozen-repair-source")
            self.workflow._batch_worker.join(10)
        plan = self.manager.preview(self.revision, "synthesis_repair", instruction="Explicit software fixture correction for frozen retry QA.")
        def partial(*args):
            result = self.response(*args)
            result.update(execution_status="Failed", error={"code": "output_truncated", "message": "Software incomplete output"})
            return result
        batch = self.run_batch(plan, "software-frozen-repair", response=partial)
        frozen = copy.deepcopy(plan)
        with patch("hullcirq.generation_batches.synthesis_repair_instruction", side_effect=AssertionError("Frozen retries must not be reprojected")):
            retry = self.manager.preview(self.revision, "synthesis_repair", retry_batch_id=batch["id"])
        self.assertEqual([item["instruction"] for item in retry["items"]], [item["instruction"] for item in frozen["items"]])
        self.assertEqual(self.manager._plan(plan["plan_id"]), frozen)

    def test_retry_rejects_new_unrelated_request_or_changed_provider(self):
        def failed(*args):
            result = self.response(*args); result.update(execution_status="Failed", error={"code": "timeout", "message": "Software timeout"})
            return result
        old = self.run_batch(response=failed)
        profile = copy.deepcopy(self.generation._profile()["profile"]); profile["model"] = "different-model"
        self.generation.save_profile(profile, self.generation._profile()["revision_id"])
        with self.assertRaises(DomainError) as caught:
            self.manager.preview(self.revision, retry_batch_id=old["id"])
        self.assertEqual(caught.exception.code, "generation_retry_profile_conflict")

    def test_large_synthesis_log_is_bounded_with_actual_error_and_full_hash(self):
        run = {"id": "software-run", "stage_id": "local_synthesis", "candidate_id": "software-candidate",
               "input_hash": "original", "tool_configuration": {"executable": "yosys"}, "diagnostics": [{"code": "synthesis_failed", "message": "Saved actual fixture error"}],
               "checks": {"executed": True, "exit_code": 1, "stdout": "verbose tool output\n" * 100000 + "ERROR: syntax error in candidate.v:42\n", "stderr": ""}}
        evidence = synthesis_repair_evidence(run)
        self.assertIn("ERROR: syntax error in candidate.v:42", evidence["focused_tool_error"])
        self.assertGreater(evidence["full_tool_output_characters"], 100000)
        self.assertLess(len(str(evidence)), 3000)
        self.assertEqual(evidence["full_record_sha256"], object_hash(run))

    def test_synthesis_projection_includes_driver_warnings_before_check_assert_failure(self):
        run = {"id": "software-driver-run", "stage_id": "local_synthesis", "candidate_id": "software-candidate",
               "input_hash": "original", "tool_configuration": {}, "diagnostics": [],
               "checks": {"executed": True, "exit_code": 1,
                          "stderr": "ERROR: Found 2 problems in check -assert.\n",
                          "stdout": "Warning: multiple conflicting drivers for module.acc_data_ready:\n port Q of cell A\n port Y of cell B\nWarning: multiple conflicting drivers for module.result_data_valid:\n port Q of cell C\n port Y of cell D\n"}}
        evidence = synthesis_repair_evidence(run)
        text = evidence["focused_tool_error"]
        self.assertIn("acc_data_ready", text)
        self.assertIn("result_data_valid", text)
        self.assertIn("port Q of cell A", text)
        self.assertIn("check -assert", text)
        self.assertEqual(evidence["projection_version"], "s05-repair-diagnostics-v3")

    def test_primary_driver_errors_survive_a_preliminary_warning_flood(self):
        run = {"id": "software-driver-run", "stage_id": "local_synthesis", "candidate_id": "software-candidate",
               "input_hash": "original", "tool_configuration": {},
               "diagnostics": [{"code": "synthesis_failed", "severity": "error", "message": "Inspect tool output"}],
               "checks": {"executed": True, "exit_code": 1,
                          "stderr": "ERROR: Found 1 problems in check -assert.\n",
                          "stdout": "Warning: wire output is assigned in a block at candidate.v:43.\n" * 1000
                          + "Warning: multiple conflicting drivers for module.job_done:\n port Q of cell old_A\n port Q of cell old_B\n"
                          + "Warning: multiple conflicting drivers for module.busy:\n port Q of cell final_A\n port Q of cell final_B\n"}}
        original = copy.deepcopy(run)
        evidence = synthesis_repair_evidence(run)
        self.assertIn("module.busy", evidence["focused_tool_error"])
        self.assertIn("module.job_done", evidence["focused_tool_error"])
        self.assertIn("final_A", evidence["focused_tool_error"])
        self.assertIn("check -assert", evidence["focused_tool_error"])
        self.assertNotIn("assigned in a block", evidence["focused_tool_error"])
        self.assertEqual(evidence["full_record_sha256"], object_hash(original))
        self.assertEqual(evidence["full_record_url"], "/api/workflow/runs/software-driver-run")
        self.assertLess(len(str(evidence)), 1050)
        self.assertEqual(run, original)

    def test_v2_projection_remains_available_without_rewriting_saved_instructions(self):
        run = {"id": "software-legacy-run", "stage_id": "local_synthesis", "candidate_id": "software-candidate",
               "input_hash": "original", "tool_configuration": {}, "diagnostics": [],
               "checks": {"executed": True, "exit_code": 1, "stderr": "ERROR: syntax error", "stdout": ""}}
        old = synthesis_repair_evidence(run, "s05-repair-diagnostics-v2")
        self.assertEqual(old["projection_version"], "s05-repair-diagnostics-v2")
        self.assertEqual(old["focused_tool_error"], {"text": "ERROR: syntax error", "full_sha256": content_hash("ERROR: syntax error"), "original_characters": 19, "omitted_characters": 0})
        self.assertEqual(old["full_record_sha256"], object_hash(run))

    def test_provider_configuration_failure_stops_before_second_request(self):
        def fail(*args):
            result = self.response(*args)
            result.update(execution_status="Failed", error={"code": "authentication", "message": "Software rejected credentials"})
            return result
        batch = self.run_batch(response=fail)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(batch["execution_status"], "Failed")
        self.assertEqual(batch["error"]["code"], "generation_batch_provider_blocked")
        self.assertEqual([item["status"] for item in batch["items"]], ["Failed", "Blocked"])

    def test_restart_reconnects_child_committed_before_scheduler_id(self):
        batch = self.run_batch()
        record = self.manager._state["batches"][0]
        record["execution_status"] = "Running"
        original_id = record["items"][-1]["job_id"]
        record["items"][-1].update(job_id=None, status="Running")
        self.manager._persist()
        loaded = GenerationBatchManager(self.store, self.generation, self.workflow)
        self.addCleanup(loaded.close)
        restored = loaded.batch(batch["id"])
        self.assertEqual(restored["execution_status"], "Interrupted")
        self.assertEqual(restored["items"][-1]["job_id"], original_id)
        self.assertEqual(len(self.calls), 2)

    def test_eleven_prior_nodes_keep_full_contract_and_bounded_semantic_context(self):
        self.run_batch()
        original = self.generation._state["jobs"][0]
        prior = []
        for index in range(11):
            job = copy.deepcopy(original); job["id"] = "software-prior-" + str(index)
            job["node_id"] = "software-node-" + str(index)
            job["instruction"] = "Prior correction " * 60
            prior.append(job)
        base = self.generation.preview("node-consumer", self.revision)
        profile = copy.deepcopy(self.generation._profile()["profile"]); profile["context_window"] = 16384
        packed = pack_batch_context(base, prior, profile, {"batch_id": "software", "index": 11, "prior_job_ids": [job["id"] for job in prior], "seed_job_ids": [], "retry_of_batch_id": None, "source_workflow_run_id": None})
        self.assertEqual(packed["messages"][-1], base["messages"][-1])
        self.assertEqual(len(packed["batch_context"]["ledger"]), 11)
        self.assertEqual(packed["batch_context"]["ledger_projection"]["kind"], "older_hashed_segment_and_recent_semantics")
        self.assertLessEqual(estimate_message_input(packed["messages"]) + profile["max_output_tokens"], 16384)


if __name__ == "__main__":
    unittest.main()

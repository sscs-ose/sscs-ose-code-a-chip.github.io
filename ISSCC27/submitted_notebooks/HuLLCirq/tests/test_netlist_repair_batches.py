"""Sequential S06 repair provenance with an isolated provider/source fixture.

These are scheduler/recovery software tests, not real circuit verification.
"""
import copy
import json
import re
import threading
import unittest
from unittest.mock import patch

from hullcirq.domain import DomainError
from hullcirq.generation import GenerationManager
from hullcirq.generation_batches import GenerationBatchManager, netlist_repair_evidence
from hullcirq.verification import content_hash, object_hash
import test_generation_batches as generation_batch_tests


class SavedWorkflowFixture:
    def __init__(self, jobs):
        self.lock = threading.RLock()
        self._state = {"runs": []}
        for job in jobs:
            synth = {"id": "s05-" + job["node_id"], "node_id": job["node_id"], "candidate_id": job["id"],
                     "stage_id": "local_synthesis", "execution_status": "Completed", "validation_status": "Passed",
                     "review_status": "Accepted", "rtl_sha256": job["rtl_sha256"], "netlist": job["rtl"],
                     "netlist_sha256": content_hash(job["rtl"]), "checks": {"executed": True}}
            sim = {**copy.deepcopy(synth), "id": "s06-" + job["node_id"], "stage_id": "local_netlist_simulation",
                   "validation_status": "Failed", "review_status": "Awaiting Review", "prior_run_id": synth["id"],
                   "verification_plan": {"kind": "isolated_finite_plan", "contract_hash": "original-contract", "vector_hash": "original-vectors",
                                         "testbench": "FULL_TESTBENCH_NOT_SENT " * 10000, "reference_trace": ["FULL_TRACE_NOT_SENT"] * 1000},
                   "diagnostics": [{"code": "behavior_mismatch", "message": "Actual isolated saved mismatch"}],
                   "checks": {"executed": True, "stdout": "setup\nFAIL cycle 2 signal result_valid expected 0 actual 1\n", "stderr": "", "scope": "finite_zero_delay"}}
            self._state["runs"].extend([synth, sim])

    def _run(self, identifier):
        return next(run for run in self._state["runs"] if run["id"] == identifier)

    def run(self, identifier):
        return copy.deepcopy(self._run(identifier)) | {"freshness": "Current"}

    def is_active(self):
        return False

    def close(self):
        pass


class NetlistRepairBatchTests(unittest.TestCase):
    close = generation_batch_tests.GenerationBatchTests.close
    response = generation_batch_tests.GenerationBatchTests.response
    run_batch = generation_batch_tests.GenerationBatchTests.run_batch

    def setUp(self):
        generation_batch_tests.GenerationBatchTests.setUp(self)
        self.run_batch()
        self.addCleanup(self.workflow.close)
        self.workflow = SavedWorkflowFixture(self.generation._state["jobs"])
        self.manager.workflow = self.workflow
        self.original_sources = copy.deepcopy(self.workflow._state)

    def test_preview_keeps_complete_source_and_compact_actual_first_failure(self):
        before_jobs = copy.deepcopy(self.generation._state)
        sources = self.manager.netlist_repair_sources()
        self.assertEqual(len(sources), 2)
        plan = self.manager.preview(self.revision, "netlist_repair")
        self.assertTrue(plan["ready_to_start"])
        self.assertEqual(len(plan["items"]), 2)
        for item in plan["items"]:
            evidence = item["netlist_repair_evidence"]
            run = self.workflow.run(item["source_workflow_run_id"])
            self.assertEqual(evidence["frozen_plan"]["sha256"], object_hash(run["verification_plan"]))
            self.assertIn("FAIL cycle 2 signal result_valid expected 0 actual 1", item["instruction"])
            self.assertNotIn("FULL_TESTBENCH_NOT_SENT", item["instruction"])
            self.assertNotIn("FULL_TRACE_NOT_SENT", item["instruction"])
            job = self.generation.job(item["base_job_id"])
            payload = json.loads(item["context"]["messages"][-1]["content"].split("\nRequired interface header", 1)[0])
            previous = payload["previous_rtl"].replace("\\n", "\n")
            self.assertEqual(re.sub(r"\s+", "", previous), re.sub(r"\s+", "", job["rtl"]))
            self.assertEqual(evidence["source"]["netlist_sha256"], run["netlist_sha256"])
        self.assertEqual(self.generation._state, before_jobs)
        self.assertEqual(self.workflow._state, self.original_sources)
        self.assertEqual(len(self.calls), 2)

    def test_distinct_requests_keep_context_evidence_and_reopen_without_rewriting_old_plans(self):
        legacy = copy.deepcopy(self.manager._state["plans"])
        plan = self.manager.preview(self.revision, "netlist_repair")
        batch = self.run_batch(plan, "isolated-netlist-repair")
        self.assertEqual(batch["validation_status"], "Passed")
        self.assertEqual(len(self.calls), 4)
        for item in batch["items"]:
            job = self.generation.job(item["job_id"])
            self.assertEqual(job["base_job_id"], item["base_job_id"])
            self.assertEqual(job["context"]["batch_context"]["netlist_repair_evidence"], item["netlist_repair_evidence"])
        self.assertEqual(self.manager._state["plans"][:len(legacy)], legacy)
        before = [self.generation.path.read_bytes(), self.manager.path.read_bytes()]
        generation = GenerationManager(self.store)
        manager = GenerationBatchManager(self.store, generation, self.workflow)
        self.addCleanup(generation.close); self.addCleanup(manager.close)
        self.assertEqual([generation.path.read_bytes(), manager.path.read_bytes()], before)
        self.assertEqual(self.workflow._state, self.original_sources)

    def test_changed_plan_netlist_or_diagnostic_rejects_before_model(self):
        plan = self.manager.preview(self.revision, "netlist_repair")
        source = self.workflow._run(plan["items"][0]["source_workflow_run_id"])
        for change in (lambda: source["verification_plan"].update(vector_hash="different"),
                       lambda: source["checks"].update(stdout="FAIL cycle 4 another failure"),
                       lambda: source.update(netlist_sha256="different-netlist")):
            original = copy.deepcopy(source)
            change()
            with self.assertRaises(DomainError) as error:
                self.manager.start(plan["plan_id"], "changed-netlist-source")
            self.assertEqual(error.exception.code, "batch_source_changed")
            source.clear(); source.update(original)
        self.assertEqual(len(self.calls), 2)

    def test_actual_hullcirq_failure_prefix_is_verbatim_and_v1_remains_reconstructible(self):
        run, synthesis = self.workflow._state["runs"][1], self.workflow._state["runs"][0]
        for failure in ("HULLCIRQ_FAIL step=2 signal=config_data_ready expected=0 actual=x",
                        "HULLCIRQ_FAIL step=7 phase=before signal=operands_valid"):
            run["checks"]["stdout"] = "setup\n" + failure + "\n"
            current = netlist_repair_evidence(run, synthesis)
            old = netlist_repair_evidence(run, synthesis, "s06-netlist-repair-evidence-v1")
            self.assertEqual(current["first_failure"], failure)
            self.assertEqual(current["first_failure_sha256"], content_hash(failure))
            self.assertIsNone(old["first_failure"])
            preview = self.manager.preview(self.revision, "netlist_repair", [run["node_id"]])
            self.assertIn(failure, preview["items"][0]["instruction"])

    def test_old_s06_analysis_guard_uses_frozen_v1_failure_projection(self):
        from hullcirq.repair_analysis import RepairAnalysisManager, LEGACY_ANALYSIS_PROJECTION, analysis_messages, analysis_budget, analysis_budget_reason
        run = self.workflow._state["runs"][1]
        run["checks"]["stdout"] = "HULLCIRQ_FAIL step=2 signal=result_valid expected=0 actual=1\n"
        analysis = RepairAnalysisManager(self.store, self.generation, self.workflow, self.manager)
        self.addCleanup(analysis.close)
        plan = analysis.preview(run["id"])
        guidance = self.manager.netlist_repair_guidance_for_run(run["id"], "s06-netlist-repair-evidence-v1")
        self.assertIsNone(guidance["evidence"]["netlist_repair_evidence"]["first_failure"])
        plan.update(prompt_projection=LEGACY_ANALYSIS_PROJECTION, source_evidence={"guidance": guidance, "rtl": plan["source_evidence"]["rtl"]}, guidance_sha256=guidance["guidance_sha256"])
        plan["source_evidence_sha256"] = object_hash(plan["source_evidence"])
        plan["messages"] = analysis_messages(guidance, plan["source_evidence"]["rtl"], LEGACY_ANALYSIS_PROJECTION)
        plan["context_budget"] = analysis_budget(plan["messages"], plan["parameters"], plan["profile"])
        plan["estimated_input_tokens"] = plan["context_budget"]["provider_input_estimated_tokens"]
        plan["ready_to_start"] = plan["context_budget"]["fits"]
        plan["gate_reason"] = analysis_budget_reason(plan["context_budget"])
        plan["context_id"] = analysis._context_id(plan)
        analysis._state["plans"] = [plan]; analysis._persist()
        analysis._guard(plan)
        before = analysis.path.read_bytes()
        reopened = RepairAnalysisManager(self.store, self.generation, self.workflow, self.manager)
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.path.read_bytes(), before)

    def test_unexecuted_or_unadopted_source_is_not_a_repair_candidate(self):
        sim = self.workflow._state["runs"][1]
        sim["checks"]["executed"] = False
        self.assertEqual(len(self.manager.netlist_repair_sources()), 1)
        plan = self.manager.preview(self.revision, "netlist_repair", [sim["node_id"]])
        self.assertFalse(plan["ready_to_start"])
        self.assertEqual(plan["items"][0]["error"]["code"], "netlist_repair_source_unavailable")
        sim["checks"]["executed"] = True
        self.workflow._state["runs"][0]["review_status"] = "Awaiting Review"
        self.assertEqual(len(self.manager.netlist_repair_sources()), 1)

    def test_transport_retry_reuses_frozen_s06_instruction_and_saved_originals(self):
        plan = self.manager.preview(self.revision, "netlist_repair")
        def disconnected(*args):
            return {"execution_status": "Failed", "raw_content": "", "finish_reason": None,
                    "error": {"code": "connection_error", "message": "isolated connection failure"}}
        batch = self.run_batch(plan, "isolated-netlist-disconnected", response=disconnected)
        self.assertEqual(batch["execution_status"], "Failed")
        with patch("hullcirq.generation_batches.netlist_repair_instruction", side_effect=AssertionError("Frozen retry is not reprojected")):
            retry = self.manager.preview(self.revision, "netlist_repair", retry_batch_id=batch["id"])
        self.assertTrue(retry["ready_to_start"])
        self.assertEqual(retry["items"][0]["instruction"], plan["items"][0]["instruction"])
        self.assertEqual(retry["items"][0]["netlist_repair_evidence"], plan["items"][0]["netlist_repair_evidence"])
        self.assertEqual(self.workflow._state, self.original_sources)

    def test_partial_answer_retry_is_explicit_and_never_used_as_repair_rtl(self):
        plan = self.manager.preview(self.revision, "netlist_repair")
        def truncated(*args):
            return {"execution_status": "Failed", "raw_content": "```verilog\nmodule partial", "finish_reason": "length",
                    "error": {"code": "output_truncated", "message": "isolated incomplete answer"}}
        batch = self.run_batch(plan, "isolated-netlist-partial", response=truncated)
        retry = self.manager.preview(self.revision, "netlist_repair", retry_batch_id=batch["id"])
        self.assertTrue(retry["ready_to_start"])
        self.assertNotIn("module partial", retry["items"][0]["context"]["messages"][-1]["content"])
        self.assertEqual(retry["items"][0]["base_job_id"], plan["items"][0]["base_job_id"])
        self.manager._guard(retry)
        self.assertEqual(self.workflow._state, self.original_sources)

    def test_own_replacement_can_make_old_s06_view_stale_without_cancelling_its_batch(self):
        original_run = self.workflow.run
        def derived_freshness(identifier):
            run = original_run(identifier)
            current = self.generation.node_sources()[run["node_id"]]
            if run["stage_id"] == "local_netlist_simulation" and current["latest_job_id"] != run["candidate_id"]:
                run.update(freshness="Stale", blocked_reason="The source candidate was superseded.")
            return run
        self.workflow.run = derived_freshness
        plan = self.manager.preview(self.revision, "netlist_repair")
        batch = self.run_batch(plan, "isolated-netlist-own-child")
        self.assertEqual(batch["validation_status"], "Passed")
        self.assertEqual([item["status"] for item in batch["items"]], ["Passed", "Passed"])

    def test_s06_analysis_is_separate_preview_start_review_apply_and_saved_v2_repair(self):
        from hullcirq.repair_analysis import RepairAnalysisManager
        analysis = RepairAnalysisManager(self.store, self.generation, self.workflow, self.manager)
        self.addCleanup(analysis.close)
        self.manager.repair_analysis = analysis
        run_id = self.workflow._state["runs"][1]["id"]
        before = copy.deepcopy(self.workflow._state)
        preview = analysis.preview(run_id)
        self.assertEqual(preview["source"]["stage_id"], "local_netlist_simulation")
        self.assertTrue(preview["ready_to_start"])
        self.assertIn("netlist-simulation failure", preview["messages"][0]["content"])
        self.assertIn("FAIL cycle 2 signal result_valid expected 0 actual 1", preview["messages"][1]["content"])
        self.assertNotIn("FULL_TESTBENCH_NOT_SENT", preview["messages"][1]["content"])
        proposal = {"changes": [{"cause": "Isolated source hypothesis", "locations": [2], "actions": ["Change only the diagnosed valid-state assignment."],
                    "preserve": ["Original reset and handshake rules"], "expected_result": "The saved first failure should disappear.", "uncertainty": "Must rerun S05 and S06."}]}
        with patch("hullcirq.repair_analysis.ChatCompletionsClient.generate", return_value={"execution_status": "Completed", "raw_content": json.dumps(proposal), "error": None}):
            job = analysis.start(preview["context_id"], "isolated-s06-guidance-analysis")
            analysis._worker.join(5)
        job = analysis.job(job["id"])
        self.assertEqual(job["execution_status"], "Completed")
        plan = self.manager.preview(self.revision, "netlist_repair", [job["source"]["node_id"]], analysis_job_ids={job["source"]["node_id"]: job["id"]})
        self.assertIn("S06 RTL repair instruction v4", plan["items"][0]["instruction"])
        self.assertIn("Change only the diagnosed valid-state assignment", plan["items"][0]["instruction"])
        self.assertEqual(plan["items"][0]["repair_guidance"]["version"], "s06-repair-guidance-v1")
        self.assertTrue(plan["items"][0]["repair_guidance"]["analysis_reviewed"])
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.workflow._state, before)


if __name__ == "__main__":
    unittest.main()

"""Independent adversarial software checks; no model, browser, or EDA calls."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.domain import DomainError
from hullcirq.generation_batches import GenerationBatchManager, POLICY_V2, pack_batch_context
from hullcirq.provider import estimate_message_input
from hullcirq.verification import object_hash


def empty_prior():
    return {"id": "failed-transport", "node_id": "node-fifo", "context_id": "context-failed",
            "profile_revision_id": "profile-original", "operation": "repair", "instruction": "Preserve the FIFO contract.",
            "context": {"messages": [{"role": "system", "content": "Saved original system"},
                                     {"role": "user", "content": "Saved original full source"}],
                        "interface": {"module_name": "fifo", "ports": []}},
            "raw_content": "", "rtl": None, "execution_status": "Failed", "validation_status": "Not Checked",
            "error": {"code": "connection_error", "message": "Connection failed"}}


class PackingAdversarialTests(unittest.TestCase):
    def base_with_exact_size(self, size=13097):
        messages = [{"role": "system", "content": "Preserve every saved requirement."}, {"role": "user", "content": ""}]
        messages[-1]["content"] = "X" * (size - estimate_message_input(messages))
        self.assertEqual(estimate_message_input(messages), size)
        return {"messages": messages}

    def test_empty_failed_request_cannot_make_a_fitting_current_contract_overflow_v2(self):
        base, prior = self.base_with_exact_size(), empty_prior()
        before = copy.deepcopy((base, prior))
        profile = {"context_window": 16384, "max_output_tokens": 3000}
        with self.assertRaises(DomainError) as caught:
            pack_batch_context(base, [prior], profile, {})
        self.assertEqual(caught.exception.code, "context_budget")
        packed = pack_batch_context(base, [prior], profile, {"packing_policy_version": POLICY_V2["kind"]})
        self.assertEqual(packed["messages"], base["messages"])
        self.assertEqual(packed["provider_input_estimated_tokens"], 13097)
        self.assertEqual(packed["context_budget"]["maximum_output_tokens"], 3287)
        self.assertTrue(packed["context_budget"]["fits"])
        self.assertFalse(packed["batch_context"]["ledger_projection"]["sent"])
        self.assertEqual(packed["batch_context"]["packing"][0]["representation"], "saved_reference_only")
        self.assertEqual(packed["batch_context"]["ledger"][0]["request_messages_sha256"], object_hash(prior["context"]["messages"]))
        self.assertEqual((base, prior), before)

    def test_legacy_dispatch_and_explicit_v1_preserve_the_exact_messages(self):
        base, prior = self.base_with_exact_size(1000), empty_prior()
        profile = {"context_window": 16384, "max_output_tokens": 3000}
        implicit = pack_batch_context(base, [prior], profile, {})
        explicit = pack_batch_context(base, [prior], profile, {"packing_policy_version": "exact_turns_with_ledger_v1"})
        self.assertEqual(implicit["messages"], explicit["messages"])
        self.assertEqual(implicit["batch_context"]["policy"]["kind"], "exact_turns_with_ledger_v1")
        self.assertIn({"role": "assistant", "content": ""}, implicit["messages"])
        self.assertNotIn("context_budget", implicit)

    def test_unknown_policy_does_not_silently_repack_historical_messages(self):
        with self.assertRaises(DomainError) as caught:
            pack_batch_context(self.base_with_exact_size(1000), [], {"context_window": 16384, "max_output_tokens": 3000},
                               {"packing_policy_version": "unrecognized-future-policy"})
        self.assertEqual(caught.exception.code, "unsupported_context_policy")

    def test_current_contract_overflow_is_measured_without_removing_a_requirement(self):
        base = self.base_with_exact_size(14000)
        with self.assertRaises(DomainError) as caught:
            pack_batch_context(base, [], {"context_window": 16384, "max_output_tokens": 3000},
                               {"packing_policy_version": POLICY_V2["kind"]})
        budget = caught.exception.context_budget
        self.assertEqual(budget["provider_input_estimated_tokens"], 14000)
        self.assertEqual(budget["maximum_output_tokens"], 2384)
        self.assertFalse(budget["fits"])

    def test_useful_prior_answer_stays_exact_when_it_fits(self):
        base, prior = self.base_with_exact_size(1000), empty_prior()
        prior.update(raw_content="Actual earlier answer", execution_status="Completed", error=None)
        packed = pack_batch_context(base, [prior], {"context_window": 16384, "max_output_tokens": 3000},
                                    {"packing_policy_version": POLICY_V2["kind"]})
        self.assertIn({"role": "assistant", "content": prior["raw_content"]}, packed["messages"])
        self.assertEqual(packed["messages"][-1], base["messages"][-1])
        budget = packed["context_budget"]
        self.assertEqual(budget["provider_input_estimated_tokens"], estimate_message_input(packed["messages"]))
        self.assertEqual(budget["base_input_estimated_tokens"] + budget["ledger_input_estimated_tokens"] +
                         budget["retained_history_input_estimated_tokens"], budget["provider_input_estimated_tokens"])


class RepairIdentityAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.revision = "revision-original"
        self.base = {"id": "base-rtl", "node_id": "node-fifo", "revision_id": self.revision, "input_hash": "saved-input",
                     "rtl": "module fifo; endmodule", "execution_status": "Completed", "operation": "generate"}
        self.failed = {"id": "failed-child", "node_id": "node-fifo", "revision_id": self.revision, "input_hash": "saved-input",
                       "rtl": None, "raw_content": "", "raw_content_sha256": "empty", "rtl_sha256": None,
                       "context_id": "context-failed", "base_job_id": "base-rtl", "execution_status": "Failed",
                       "operation": "repair", "error": {"code": "connection_error", "message": "Connection failed"},
                       "context": {"batch_context": {"source_workflow_run_id": "s05-failed"}}}
        self.run = {"id": "s05-failed", "node_id": "node-fifo", "stage_id": "local_synthesis", "candidate_id": "base-rtl",
                    "freshness": "Current", "execution_status": "Completed", "validation_status": "Failed", "checks": {"executed": True}}
        self.manager = GenerationBatchManager.__new__(GenerationBatchManager)
        self.manager.store = SimpleNamespace(envelope=lambda: {"revision": {"id": self.revision}})
        self.manager.generation = SimpleNamespace(lock=threading.RLock(), _state={"jobs": [self.base, self.failed]})
        self.manager.workflow = SimpleNamespace(lock=threading.RLock(), _state={"runs": [self.run]}, run=lambda identifier: copy.deepcopy(self.run))

    def identity(self):
        return self.manager._repair_identity("node-fifo", self.manager.generation._state["jobs"][-1]["id"])

    def test_exact_empty_transport_child_has_explicit_recovery_identity(self):
        value = self.identity()
        self.assertEqual(value["latest_job_id"], "failed-child")
        self.assertEqual(value["base_job_id"], "base-rtl")
        self.assertEqual(value["recovery"]["failed_job_ids"], ["failed-child"])

    def test_new_failed_interface_candidate_is_never_hidden_by_older_rtl(self):
        self.failed.update(rtl="module wrong_interface; endmodule", raw_content="module wrong_interface; endmodule",
                           validation_status="Failed", error=None, execution_status="Completed")
        self.assertIsNone(self.identity())

    def test_source_and_transport_tampering_never_fall_back_to_older_candidate(self):
        mutations = [
            {"base_job_id": "another-base"}, {"input_hash": "different-input"}, {"revision_id": "another-revision"},
            {"raw_content": "partial model answer"}, {"operation": "generate"}, {"execution_status": "Completed"},
            {"error": {"code": "output_truncated"}},
            {"context": {"batch_context": {"source_workflow_run_id": "another-run"}}},
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                modified = copy.deepcopy(self.failed); modified.update(mutation)
                self.manager.generation._state["jobs"] = [self.base, modified]
                self.assertIsNone(self.identity())

    def test_intervening_unusable_request_prevents_recovery_through_a_good_tail(self):
        middle = copy.deepcopy(self.failed)
        middle.update(id="intervening-new-request", operation="generate", base_job_id=None)
        self.manager.generation._state["jobs"] = [self.base, middle, self.failed]
        self.assertIsNone(self.identity())

    def test_newer_synthesis_failure_for_another_candidate_does_not_match(self):
        self.run["candidate_id"] = "different-rtl"
        self.assertIsNone(self.identity())

    def test_stale_or_unexecuted_synthesis_result_cannot_supply_repair_evidence(self):
        for field, value in (("freshness", "Stale"), ("checks", {"executed": False}), ("validation_status", "Passed")):
            with self.subTest(field=field):
                original = copy.deepcopy(self.run)
                self.run[field] = value
                self.assertIsNone(self.identity())
                self.run.clear(); self.run.update(original)

    def recovery_plan(self):
        identity = self.identity()
        self.manager.generation.node_sources = lambda: {"node-fifo": {"latest_job_id": self.manager.generation._state["jobs"][-1]["id"]}}
        self.manager.generation._require_profile = lambda revision: None
        return {"mode": "repair", "revision_id": self.revision, "profile_revision_id": "profile-saved", "items": [{
            "node_id": "node-fifo", "expected_latest_job_id": identity["latest_job_id"],
            "base_job_id": identity["base_job_id"], "source_workflow_run_id": self.run["id"],
            "source_workflow_sha256": object_hash({key: value for key, value in self.run.items() if key not in {"freshness", "artifacts"}}),
            "source_recovery": copy.deepcopy(identity["recovery"])}]}

    def test_recovery_start_guard_rejects_transport_evidence_changed_after_preview(self):
        plan = self.recovery_plan()
        self.manager._guard(plan)
        self.failed["error"]["message"] = "Different saved failure evidence"
        with self.assertRaises(DomainError) as caught:
            self.manager._guard(plan)
        self.assertEqual(caught.exception.code, "batch_source_changed")

    def test_recovery_start_guard_rejects_new_rtl_after_preview(self):
        plan = self.recovery_plan()
        self.manager.generation._state["jobs"].append(dict(self.base, id="newest-candidate"))
        with self.assertRaises(DomainError) as caught:
            self.manager._guard(plan)
        self.assertEqual(caught.exception.code, "batch_source_changed")

    def test_recovery_start_guard_rejects_synthesis_evidence_changed_after_preview(self):
        plan = self.recovery_plan()
        self.run["checks"]["new_evidence"] = "Changed tool evidence"
        with self.assertRaises(DomainError) as caught:
            self.manager._guard(plan)
        self.assertEqual(caught.exception.code, "batch_source_changed")

    def test_recovery_start_guard_keeps_profile_revision_guard(self):
        plan = self.recovery_plan()
        def changed_profile(revision):
            raise DomainError("profile_conflict", "Profile changed after preview.", 409)
        self.manager.generation._require_profile = changed_profile
        with self.assertRaises(DomainError) as caught:
            self.manager._guard(plan)
        self.assertEqual(caught.exception.code, "profile_conflict")


if __name__ == "__main__":
    unittest.main()

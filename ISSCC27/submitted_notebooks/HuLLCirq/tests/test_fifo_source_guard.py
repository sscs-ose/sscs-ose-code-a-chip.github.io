"""Source-change checks on isolated software data; no project/tool mutations."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.context import node_fingerprint
from hullcirq.domain import DomainError
from hullcirq.verification import build_verification_plan, object_hash
from hullcirq.workflow import WorkflowManager, ensure_current_verification_plan


class FifoSourceGuardTests(unittest.TestCase):
    def setUp(self):
        self.design = json.loads((PROJECT / "examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))
        self.node_id = "npu2-fifo"
        self.plan = build_verification_plan(self.design, self.node_id)
        self.manager = WorkflowManager.__new__(WorkflowManager)
        self.manager.store = SimpleNamespace(envelope=lambda: {"design": self.design})
        self.nodes = [{"node_id": self.node_id, "latest_job_id": "candidate", "accepted_job_id": "candidate"}]
        self.manager.generation = SimpleNamespace(envelope=lambda: {"generation": {"nodes": self.nodes}})
        self.prior = {"id": "s05", "node_id": self.node_id, "candidate_id": "candidate", "stage_id": "local_synthesis",
                      "execution_status": "Completed", "validation_status": "Passed", "review_status": "Accepted",
                      "revision_id": "original", "netlist": "saved original netlist", "verification_plan": None,
                      "input_hash": node_fingerprint(self.design, self.node_id), "acceptance_epoch": 0}
        self.run = {**self.prior, "id": "s06", "stage_id": "local_netlist_simulation", "prior_run_id": "s05", "verification_plan": self.plan}
        self.manager._state = {"node_inputs": {self.node_id: self.prior["input_hash"]},
                               "node_epochs": {self.node_id: 0}, "runs": [self.prior, self.run]}

    def test_current_saved_job_is_usable_and_plan_remains_immutable(self):
        before = object_hash(self.plan)
        ensure_current_verification_plan(self.design, self.node_id, self.plan)
        self.manager._fifo_source_current("candidate", self.node_id, "s05", self.plan)
        self.assertEqual(self.manager._decorate(self.run)["freshness"], "Current")
        self.assertEqual(object_hash(self.plan), before)

    def test_job_only_edit_invalidates_s06_even_when_s04_hash_is_unchanged(self):
        before = object_hash(self.plan)
        self.design["verification_jobs"][0]["A"][0][0] += 1
        self.assertEqual(node_fingerprint(self.design, self.node_id), self.prior["input_hash"])
        with self.assertRaises(DomainError):
            ensure_current_verification_plan(self.design, self.node_id, self.plan)
        view = self.manager._decorate(self.run)
        self.assertEqual(view["freshness"], "Stale")
        self.assertEqual(view["review_status"], "Awaiting Review")
        self.assertEqual(self.run["review_status"], "Accepted")
        self.assertEqual(object_hash(self.plan), before)

    def test_noncanonical_job_type_cannot_reuse_old_frozen_evidence(self):
        self.design["verification_jobs"][0]["k"] = 3.0
        with self.assertRaises(DomainError):
            ensure_current_verification_plan(self.design, self.node_id, self.plan)
        self.assertEqual(self.manager._decorate(self.run)["freshness"], "Stale")

    def test_new_candidate_or_new_s05_prevents_old_s06_adoption(self):
        for change in ("candidate", "synthesis"):
            with self.subTest(change=change):
                if change == "candidate":
                    self.nodes[0]["latest_job_id"] = "new-candidate"
                else:
                    self.nodes[0]["latest_job_id"] = "candidate"
                    self.manager._state["runs"].append({**self.prior, "id": "new-s05", "validation_status": "Failed", "review_status": "Awaiting Review"})
                self.assertEqual(self.manager._decorate(self.run)["freshness"], "Stale")
                with self.assertRaises(DomainError):
                    self.manager._fifo_source_current("candidate", self.node_id, "s05", self.plan)

    def test_existing_plan_kinds_keep_historical_semantics(self):
        ensure_current_verification_plan({}, "old-node", {"kind": "npu_fifo_stream"})


if __name__ == "__main__":
    unittest.main()

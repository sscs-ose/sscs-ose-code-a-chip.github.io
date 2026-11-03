"""Latest-candidate aggregate truthfulness; isolated fake provider only."""
from __future__ import annotations
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
import test_generation_batches as batch_fixtures

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.server import make_server, project_envelope


class S04CurrentAggregateTests(unittest.TestCase):
    def setUp(self):
        self.fixture = batch_fixtures.GenerationBatchTests(methodName="test_two_distinct_calls_retain_actual_conversation_and_reload_exactly")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.run_batch()

    def test_new_failed_candidate_withdraws_aggregate_without_rewriting_old_adoption(self):
        fixture = self.fixture
        original = fixture.generation.envelope()["generation"]
        node = next(node for node in original["nodes"] if node["node_id"] == "node-producer")
        old_id = node["accepted_job_id"]
        old_record = fixture.generation.job(old_id)
        old_review = fixture.generation._state["reviews"][0].copy()
        self.assertTrue(original["all_nodes_accepted"])
        preview = fixture.generation.preview("node-producer", fixture.revision)
        with patch("hullcirq.generation.ChatCompletionsClient") as provider:
            provider.return_value.generate.return_value = {"execution_status": "Failed", "raw_content": "incomplete software fixture", "error": {"code": "output_truncated", "message": "Software output limit"}}
            fixture.generation.start("node-producer", fixture.revision, preview["context_id"], preview["profile_revision_id"])
            fixture.generation._worker.join(5)
        current = fixture.generation.envelope()["generation"]
        node = next(node for node in current["nodes"] if node["node_id"] == "node-producer")
        self.assertFalse(current["all_nodes_accepted"])
        self.assertEqual(node["accepted_job_id"], old_id)
        self.assertNotEqual(node["latest_job_id"], old_id)
        self.assertEqual(node["review_status"], "Awaiting Review")
        self.assertEqual(fixture.generation.job(old_id), old_record)
        self.assertEqual(fixture.generation._state["reviews"][0], old_review)
        server = make_server("127.0.0.1", 0, fixture.store, ROOT)
        try:
            envelope = project_envelope(server)
            stage = next(stage for stage in envelope["workflow"] if stage["id"] == "local_rtl_generation")
            self.assertEqual(stage["accepted_node_count"], 1)
            self.assertEqual(stage["required_node_count"], 2)
            self.assertEqual(stage["review_status"], "Awaiting Review")
        finally:
            server.server_close()

    def test_new_running_candidate_does_not_inherit_old_node_review_status(self):
        fixture = self.fixture
        preview = fixture.generation.preview("node-producer", fixture.revision)
        entered, release = threading.Event(), threading.Event()
        def hold(*args):
            entered.set(); release.wait(3)
            return fixture.response(*args)
        with patch("hullcirq.generation.ChatCompletionsClient") as provider:
            provider.return_value.generate.side_effect = hold
            fixture.generation.start("node-producer", fixture.revision, preview["context_id"], preview["profile_revision_id"])
            self.assertTrue(entered.wait(2))
            current = fixture.generation.envelope()["generation"]
            self.assertFalse(current["all_nodes_accepted"])
            node = next(node for node in current["nodes"] if node["node_id"] == "node-producer")
            self.assertEqual(node["review_status"], "Awaiting Review")
            release.set(); fixture.generation._worker.join(5)
        self.assertTrue(fixture.generation.envelope()["generation"]["all_nodes_accepted"])


if __name__ == "__main__":
    unittest.main()

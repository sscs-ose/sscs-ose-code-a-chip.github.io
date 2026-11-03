"""Isolated HTTP queue dispatch and session guards; no model or EDA calls."""
from pathlib import Path
from unittest.mock import patch
import unittest

import test_s05_batch_http as s05_http
from hullcirq.store import ProjectStore


class GenerationBatchHttpTests(unittest.TestCase):
    setUp = s05_http.S05BatchHttpTests.setUp
    tearDown = s05_http.S05BatchHttpTests.tearDown
    request = s05_http.S05BatchHttpTests.request
    mutation = s05_http.S05BatchHttpTests.mutation
    create = s05_http.S05BatchHttpTests.create

    def test_preview_start_cancel_and_saved_evidence_dispatch_without_model(self):
        self.create()
        revision = self.server.store.envelope()["revision"]["id"]
        body = {"revision_id": revision, "mode": "synthesis_repair", "node_ids": ["qa-a", "qa-b"], "instruction": "Saved diagnostic correction", "retry_batch_id": "qa-prior-batch"}
        with patch.object(self.server.generation_batches, "preview", return_value={"plan_id": "qa-plan"}) as preview:
            status, value = self.request("POST", "/api/generation/batches/preview", body)
        self.assertEqual((status, value["plan_id"]), (200, "qa-plan"))
        preview.assert_called_once_with(revision, "synthesis_repair", ["qa-a", "qa-b"], body["instruction"], "qa-prior-batch")
        with patch.object(self.server.generation_batches, "start", return_value={}) as start:
            status, _ = self.request("POST", "/api/generation/batches/start", {"plan_id": "qa-plan", "request_id": "qa-http-request"})
        self.assertEqual(status, 202)
        start.assert_called_once_with("qa-plan", "qa-http-request")
        with patch.object(self.server.generation_batches, "cancel", return_value={}) as cancel:
            status, _ = self.request("POST", "/api/generation/batches/qa-batch/cancel", {})
        self.assertEqual(status, 200)
        cancel.assert_called_once_with("qa-batch")
        with patch.object(self.server.generation_batches, "batch", return_value={"id": "qa-batch"}) as read:
            status, value = self.request("GET", "/api/generation/batches/qa-batch")
        self.assertEqual((status, value["id"]), (200, "qa-batch"))
        read.assert_called_once_with("qa-batch")
        with patch.object(self.server.generation_batches, "plan", return_value={"plan_id": "qa-plan"}) as read:
            status, value = self.request("GET", "/api/generation/batches/plans/qa-plan")
        self.assertEqual((status, value["plan_id"]), (200, "qa-plan"))
        read.assert_called_once_with("qa-plan")

    def test_stale_missing_session_and_foreign_origin_cannot_submit_queue(self):
        self.create()
        paths = ("/api/generation/batches/preview", "/api/generation/batches/start", "/api/generation/batches/qa-batch/cancel")
        for path in paths:
            for options, expected in (({"authenticated": False}, 409), ({"session": "stale-session"}, 409),
                                      ({"extra_headers": {"Origin": "https://other.example"}}, 403),
                                      ({"extra_headers": {"Sec-Fetch-Site": "cross-site"}}, 403)):
                with self.subTest(path=path, options=options), patch.object(self.server.generation_batches, "preview") as preview, patch.object(self.server.generation_batches, "start") as start, patch.object(self.server.generation_batches, "cancel") as cancel:
                    status, _ = self.request("POST", path, {}, **options)
                    self.assertEqual(status, expected)
                    preview.assert_not_called(); start.assert_not_called(); cancel.assert_not_called()
        for path in ("/api/generation/batches/qa-batch", "/api/generation/batches/plans/qa-plan"):
            status, _ = self.request("GET", path, authenticated=False)
            self.assertEqual(status, 409)

    def test_readonly_system_denies_mutations_and_preserves_original_stores(self):
        source = ProjectStore(Path(self.temp.name) / "legacy")
        saved = self.registry.register_legacy(source.path)
        self.mutation("open", {"project_id": saved["project_id"], "system_id": saved["system_id"]})
        before = {path.name: path.read_bytes() for path in source.path.glob("*.json")}
        for path in ("/api/generation/batches/preview", "/api/generation/batches/start", "/api/generation/batches/qa-batch/cancel"):
            status, response = self.request("POST", path, {})
            self.assertEqual(status, 409)
            self.assertEqual(response["error"]["code"], "read_only_system")
        self.assertEqual(before, {path.name: path.read_bytes() for path in source.path.glob("*.json")})

    def test_active_batch_guards_execution_probe_and_workspace_between_child_jobs(self):
        self.create()
        with patch.object(self.server.generation_batches, "is_active", return_value=True):
            for path in ("/api/generation/start", "/api/workflow/batches/start", "/api/workflow/start", "/api/global-generation/start", "/api/llm/probe"):
                with self.subTest(path=path):
                    status, response = self.request("POST", path, {})
                    self.assertEqual(status, 409)
                    self.assertEqual(response["error"]["code"], "generation_batch_busy")
            status, _ = self.request("POST", "/api/workspace/close", {})
            self.assertEqual(status, 409)
            self.assertEqual(self.server.workspace.identity["session_id"], self.session)


if __name__ == "__main__":
    unittest.main()

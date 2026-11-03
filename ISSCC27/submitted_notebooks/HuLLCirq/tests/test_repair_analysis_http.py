"""Repair-analysis HTTP dispatch/session guards with no real model or tools."""
import json
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

import test_s05_batch_http as s05_http
from hullcirq.store import ProjectStore


class RepairAnalysisHttpTests(unittest.TestCase):
    setUp = s05_http.S05BatchHttpTests.setUp
    tearDown = s05_http.S05BatchHttpTests.tearDown
    request = s05_http.S05BatchHttpTests.request
    mutation = s05_http.S05BatchHttpTests.mutation
    create = s05_http.S05BatchHttpTests.create

    def test_preview_start_cancel_and_saved_get_dispatch_to_analysis_only(self):
        self.create()
        manager = self.server.repair_analysis
        with patch.object(manager, "preview", return_value={"context_id": "analysis-context"}) as preview:
            status, value = self.request("POST", "/api/repair-analysis/preview", {"run_id": "failed-s05"})
        self.assertEqual((status, value["context_id"]), (200, "analysis-context"))
        preview.assert_called_once_with("failed-s05")
        with patch.object(manager, "start", return_value={"id": "analysis-one"}) as start, patch.object(self.server.generation, "start") as generate, patch.object(self.server.workflow, "start") as execute:
            status, value = self.request("POST", "/api/repair-analysis/start", {"context_id": "analysis-context", "request_id": "analysis-http-request"})
        self.assertEqual((status, value["id"]), (202, "analysis-one"))
        start.assert_called_once_with("analysis-context", "analysis-http-request")
        generate.assert_not_called()
        execute.assert_not_called()
        with patch.object(manager, "cancel", return_value={"id": "analysis-one"}) as cancel:
            status, _ = self.request("POST", "/api/repair-analysis/cancel", {"job_id": "analysis-one"})
        self.assertEqual(status, 200)
        cancel.assert_called_once_with("analysis-one")
        with patch.object(manager, "job", return_value={"id": "analysis-one", "raw_content": "exact saved advice"}) as read:
            status, value = self.request("GET", "/api/repair-analysis/jobs/analysis-one")
        self.assertEqual((status, value["raw_content"]), (200, "exact saved advice"))
        read.assert_called_once_with("analysis-one")
        status, value = self.request("GET", "/api/repair-analysis")
        self.assertEqual(status, 200)
        self.assertEqual(value["repair_analysis"]["jobs"], [])

    def test_missing_stale_or_cross_origin_requests_never_dispatch(self):
        self.create()
        manager = self.server.repair_analysis
        for path in ("/api/repair-analysis/preview", "/api/repair-analysis/start", "/api/repair-analysis/cancel"):
            for options, expected in (({"authenticated": False}, 409), ({"session": "stale"}, 409),
                                      ({"extra_headers": {"Origin": "https://other.example"}}, 403),
                                      ({"extra_headers": {"Sec-Fetch-Site": "cross-site"}}, 403)):
                with self.subTest(path=path, options=options), patch.object(manager, "preview") as preview, patch.object(manager, "start") as start, patch.object(manager, "cancel") as cancel:
                    status, _ = self.request("POST", path, {}, **options)
                    self.assertEqual(status, expected)
                    preview.assert_not_called()
                    start.assert_not_called()
                    cancel.assert_not_called()
        for path in ("/api/repair-analysis", "/api/repair-analysis/jobs/analysis-one"):
            status, _ = self.request("GET", path, authenticated=False)
            self.assertEqual(status, 409)

    def test_preserved_snapshot_shows_exact_advice_and_denies_all_analysis_mutations(self):
        source = ProjectStore(Path(self.temp.name) / "legacy-analysis")
        analysis_path = source.path / "repair_analysis.json"
        analysis_path.write_text(json.dumps({"version": "0.1", "plans": [], "jobs": [{
            "id": "preserved-analysis", "execution_status": "Completed", "raw_content": "Saved unverified advice\n",
            "messages": [{"role": "user", "content": "Exact saved RTL and diagnostic"}], "proposal": {"changes": []}}]}), encoding="utf-8")
        saved = self.registry.register_legacy(source.path)
        self.mutation("open", {"project_id": saved["project_id"], "system_id": saved["system_id"]})
        before = {path.name: path.read_bytes() for path in source.path.glob("*.json")}
        for path in ("/api/repair-analysis/preview", "/api/repair-analysis/start", "/api/repair-analysis/cancel"):
            status, value = self.request("POST", path, {})
            self.assertEqual(status, 409)
            self.assertEqual(value["error"]["code"], "read_only_system")
        status, value = self.request("GET", "/api/repair-analysis/jobs/preserved-analysis")
        self.assertEqual(status, 200)
        self.assertEqual(value["raw_content"], "Saved unverified advice\n")
        self.assertTrue(value["read_only"])
        self.assertEqual(before, {path.name: path.read_bytes() for path in source.path.glob("*.json")})

    def test_active_analysis_blocks_competing_execution_and_workspace_switch(self):
        self.create()
        with patch.object(self.server.repair_analysis, "is_active", return_value=True):
            for path in ("/api/generation/start", "/api/workflow/batches/start", "/api/workflow/start",
                         "/api/global-generation/start", "/api/llm/probe", "/api/workspace/close"):
                with self.subTest(path=path):
                    status, value = self.request("POST", path, {})
                    self.assertEqual(status, 409)
                    self.assertEqual(value["error"]["code"], "repair_analysis_busy")
            self.assertEqual(self.server.workspace.identity["session_id"], self.session)

    def test_competing_execution_blocks_new_analysis_before_dispatch(self):
        self.create()
        body = {"context_id": "analysis-context", "request_id": "new-analysis-request"}
        for name, expected in (("global_generation", "competing_execution_busy"),
                               ("workflow", "competing_execution_busy"),
                               ("physical_workflow", "physical_workflow_busy"),
                               ("postlayout_workflow", "postlayout_workflow_busy"),
                               ("generation_batches", "generation_batch_busy")):
            with self.subTest(manager=name), patch.object(getattr(self.server, name), "is_active", return_value=True), patch.object(self.server.repair_analysis, "start") as start:
                status, value = self.request("POST", "/api/repair-analysis/start", body)
                self.assertEqual(status, 409)
                self.assertEqual(value["error"]["code"], expected)
                start.assert_not_called()
        with patch.object(self.server.generation, "_worker", Mock(is_alive=Mock(return_value=True))), patch.object(self.server.repair_analysis, "start") as start:
            status, value = self.request("POST", "/api/repair-analysis/start", body)
            self.assertEqual(status, 409)
            self.assertEqual(value["error"]["code"], "competing_execution_busy")
            start.assert_not_called()

    def test_duplicate_analysis_request_can_reconnect_while_worker_is_active(self):
        self.create()
        manager = self.server.repair_analysis
        manager._state["jobs"].append({"id": "existing-analysis", "request_id": "existing-request-id"})
        try:
            with patch.object(manager, "is_active", return_value=True), patch.object(manager, "start", return_value={"id": "existing-analysis"}) as start:
                status, value = self.request("POST", "/api/repair-analysis/start", {"context_id": "existing-context", "request_id": "existing-request-id"})
            self.assertEqual((status, value["id"]), (202, "existing-analysis"))
            start.assert_called_once_with("existing-context", "existing-request-id")
        finally:
            manager._state["jobs"].clear()


if __name__ == "__main__":
    unittest.main()

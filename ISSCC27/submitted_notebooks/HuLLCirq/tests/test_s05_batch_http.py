"""Isolated HTTP authorization/dispatch QA; no model, real EDA, or live project."""
import http.client
import json
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

import test_workspace_http as workspace_http
from hullcirq.store import ProjectStore


class S05BatchHttpTests(unittest.TestCase):
    setUp = workspace_http.WorkspaceHttpTests.setUp
    tearDown = workspace_http.WorkspaceHttpTests.tearDown
    mutation = workspace_http.WorkspaceHttpTests.mutation
    create = workspace_http.WorkspaceHttpTests.create

    def request(self, method, path, body=None, authenticated=True, session=None, extra_headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"X-HuLLCirq-Session": session or getattr(self, "session", "")} if authenticated else {}
        headers.update(extra_headers or {})
        if body is not None:
            body = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def body(self):
        return {"revision_id": self.server.store.envelope()["revision"]["id"], "request_id": "isolated-http-batch"}

    def test_start_and_cancel_dispatch_to_exact_manager_without_executing_tools(self):
        self.create()
        body = self.body()
        with patch.object(self.server.workflow, "start_batch", return_value={}) as start:
            status, _ = self.request("POST", "/api/workflow/batches/start", body)
        self.assertEqual(status, 202)
        start.assert_called_once_with(body["revision_id"], body["request_id"])
        with patch.object(self.server.workflow, "cancel_batch", return_value={}) as cancel:
            status, _ = self.request("POST", "/api/workflow/batches/batch-fixture/cancel", {})
        self.assertEqual(status, 200)
        cancel.assert_called_once_with("batch-fixture")
        with patch.object(self.server.workflow, "batch", return_value={"id": "batch-fixture"}) as read:
            status, value = self.request("GET", "/api/workflow/batches/batch-fixture")
        self.assertEqual((status, value["id"]), (200, "batch-fixture"))
        read.assert_called_once_with("batch-fixture")

    def test_stale_missing_session_and_foreign_origin_cannot_start_or_cancel(self):
        self.create()
        for path in ("/api/workflow/batches/start", "/api/workflow/batches/batch-fixture/cancel"):
            for options, expected in (({"authenticated": False}, 409), ({"session": "stale-session"}, 409),
                                      ({"extra_headers": {"Origin": "https://other.example"}}, 403),
                                      ({"extra_headers": {"Sec-Fetch-Site": "cross-site"}}, 403)):
                with self.subTest(path=path, options=options), patch.object(self.server.workflow, "start_batch") as start, patch.object(self.server.workflow, "cancel_batch") as cancel:
                    status, _ = self.request("POST", path, self.body(), **options)
                    self.assertEqual(status, expected)
                    start.assert_not_called()
                    cancel.assert_not_called()

    def test_readonly_system_denies_batch_mutations_without_original_writes(self):
        source = ProjectStore(Path(self.temp.name) / "legacy")
        saved = self.registry.register_legacy(source.path)
        self.mutation("open", {"project_id": saved["project_id"], "system_id": saved["system_id"]})
        before = {p.name: p.read_bytes() for p in source.path.glob("*.json")}
        for path in ("/api/workflow/batches/start", "/api/workflow/batches/batch-fixture/cancel"):
            with self.subTest(path=path):
                status, response = self.request("POST", path, self.body())
                self.assertEqual(status, 409)
                self.assertEqual(response["error"]["code"], "read_only_system")
        self.assertEqual(before, {p.name: p.read_bytes() for p in source.path.glob("*.json")})

    def test_competing_model_and_physical_execution_blocks_batch_dispatch(self):
        self.create()
        cases = [(self.server.global_generation, "competing_execution_busy"),
                 (self.server.physical_workflow, "physical_workflow_busy"),
                 (self.server.postlayout_workflow, "postlayout_workflow_busy")]
        for manager, code in cases:
            with self.subTest(code=code), patch.object(manager, "is_active", return_value=True), patch.object(self.server.workflow, "start_batch") as start:
                status, response = self.request("POST", "/api/workflow/batches/start", self.body())
                self.assertEqual(status, 409)
                self.assertEqual(response["error"]["code"], code)
                start.assert_not_called()
        with patch.object(self.server.generation, "_worker", Mock(is_alive=Mock(return_value=True))), patch.object(self.server.workflow, "start_batch") as start:
            status, response = self.request("POST", "/api/workflow/batches/start", self.body())
            self.assertEqual(status, 409)
            self.assertEqual(response["error"]["code"], "competing_execution_busy")
            start.assert_not_called()

    def test_active_batch_prevents_other_execution_and_workspace_switch(self):
        self.create()
        with patch.object(self.server.workflow, "is_active", return_value=True):
            with patch.object(self.server.generation, "start") as generate:
                status, response = self.request("POST", "/api/generation/start", {})
                self.assertEqual(status, 409)
                self.assertEqual(response["error"]["code"], "workflow_busy")
                generate.assert_not_called()
            status, response = self.request("POST", "/api/workspace/close", {})
            self.assertEqual(status, 409)
            self.assertEqual(self.server.workspace.identity["session_id"], self.session)


if __name__ == "__main__":
    unittest.main()

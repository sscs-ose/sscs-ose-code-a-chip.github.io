"""Ephemeral HTTP dispatch QA only; no LLM, EDA, or user project writes."""
import http.client
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import test_workspace_http as workspace_http
from hullcirq.store import ProjectStore


class S06BatchHttpTests(unittest.TestCase):
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
        return {"revision_id": self.server.store.envelope()["revision"]["id"],
                "request_id": "s06-isolated-http-batch", "stage_id": "local_netlist_simulation"}

    def test_explicit_s06_dispatch_is_exact_stage_and_default_s05_stays_compatible(self):
        self.create()
        body = self.body()
        with patch.object(self.server.workflow, "start_batch", return_value={}) as start:
            status, _ = self.request("POST", "/api/workflow/batches/start", body)
        self.assertEqual(status, 202)
        start.assert_called_once_with(body["revision_id"], body["request_id"], stage_id="local_netlist_simulation")
        body.pop("stage_id")
        with patch.object(self.server.workflow, "start_batch", return_value={}) as start:
            status, _ = self.request("POST", "/api/workflow/batches/start", body)
        self.assertEqual(status, 202)
        start.assert_called_once_with(body["revision_id"], body["request_id"])

    def test_capability_advertises_s06_before_client_can_start_it(self):
        self.create()
        status, response = self.request("GET", "/api/workflow")
        self.assertEqual(status, 200)
        self.assertEqual(response["workflow_batch_stages"], ["local_synthesis", "local_netlist_simulation"])

    def test_invalid_stage_rejects_before_scheduling_any_operation(self):
        self.create()
        before = self.server.workflow.path.read_bytes()
        body = dict(self.body(), stage_id="global_synthesis")
        status, response = self.request("POST", "/api/workflow/batches/start", body)
        self.assertEqual(status, 400)
        self.assertEqual(response["error"]["code"], "invalid_batch_request")
        self.assertEqual(self.server.workflow.path.read_bytes(), before)

    def test_missing_stale_session_or_foreign_origin_cannot_send_s06(self):
        self.create()
        for options, expected in (({"authenticated": False}, 409), ({"session": "stale"}, 409),
                ({"extra_headers": {"Origin": "https://other.example"}}, 403),
                ({"extra_headers": {"Sec-Fetch-Site": "cross-site"}}, 403)):
            with self.subTest(options=options), patch.object(self.server.workflow, "start_batch") as start:
                status, _ = self.request("POST", "/api/workflow/batches/start", self.body(), **options)
                self.assertEqual(status, expected)
                start.assert_not_called()

    def test_readonly_s06_rejected_without_original_writes(self):
        source = ProjectStore(Path(self.temp.name) / "legacy")
        saved = self.registry.register_legacy(source.path)
        self.mutation("open", {"project_id": saved["project_id"], "system_id": saved["system_id"]})
        before = {path.name: path.read_bytes() for path in source.path.glob("*.json")}
        status, response = self.request("POST", "/api/workflow/batches/start", self.body())
        self.assertEqual(status, 409)
        self.assertEqual(response["error"]["code"], "read_only_system")
        self.assertEqual(before, {path.name: path.read_bytes() for path in source.path.glob("*.json")})

    def test_active_model_or_physical_execution_blocks_s06_dispatch(self):
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
            self.assertEqual((status, response["error"]["code"]), (409, "competing_execution_busy"))
            start.assert_not_called()


if __name__ == "__main__":
    unittest.main()

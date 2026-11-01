"""Isolated S09/S10 routing QA; doubles below are not circuit proof.

No live history, model server or EDA executable is used by these tests.
"""
from __future__ import annotations

import http.client
import json
import threading
import unittest

import test_global_generation as fixtures
from hullcirq.domain import DomainError
from hullcirq.server import make_server
from hullcirq.store import strict_loads


class WorkflowDouble:
    def __init__(self):
        self.active = False
        self.calls = []
        self.record = {"id": "software-run", "stage_id": "global_synthesis",
                       "execution_status": "Completed", "validation_status": "Passed",
                       "review_status": "Accepted", "freshness": "Current"}

    def envelope(self):
        return {"global_workflow": {"implemented": True, "runs": [self.record], "reviews": [],
                "stages": [{"stage_id": stage, "latest_run_id": "software-run" if i == 0 else None,
                            "accepted_run_id": "software-run" if i == 0 else None}
                           for i, stage in enumerate(("global_synthesis", "global_netlist_simulation"))],
                "ready": True, "blocked_reason": None, "storage_error": None}}

    def start(self, *args):
        self.calls.append(("start", args))
        # Match the real manager return contract; no worker or receipt is created.
        return self.envelope()

    def run(self, identifier):
        if identifier != self.record["id"]:
            raise DomainError("run_not_found", "SOFTWARE QA missing run", 404)
        return self.record

    def cancel(self, identifier):
        self.calls.append(("cancel", identifier))

    def review(self, *args, operator=None):
        self.calls.append(("review", args))

    def artifact(self, identifier, field):
        self.run(identifier)
        if field == "verification-plan":
            return {"configuration_word": 2**133 + 123, "software_qa_fixture": True}
        if field == "netlist":
            return "// SOFTWARE QA netlist placeholder; never compiled\n"
        raise DomainError("artifact_not_found", "SOFTWARE QA missing artifact", 404)

    def is_active(self):
        return self.active

    def close(self):
        pass


class GlobalWorkflowHTTPTests(unittest.TestCase):
    def setUp(self):
        self.qa = fixtures.GlobalSoftwareTests("test_manifest_exact_sources_and_prompt_excludes_numeric_test_job")
        self.qa.setUp()
        self.addCleanup(self.qa.doCleanups)
        self.server = make_server("127.0.0.1", 0, self.qa.store, fixtures.PROJECT)
        self.server.global_workflow.close()
        self.double = self.server.global_workflow = WorkflowDouble()
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .02}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.server.workflow.close()
        self.server.generation.close()
        self.thread.join(2)

    def request(self, path, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=20)
        try:
            connection.request("GET" if body is None else "POST", path,
                               None if body is None else json.dumps(body),
                               {} if body is None else {"Content-Type": "application/json"})
            response = connection.getresponse()
            raw = response.read()
            return response.status, raw, strict_loads(raw.decode())
        finally:
            connection.close()

    def test_stage_projection_and_lossless_fixed_artifacts(self):
        status, _, project = self.request("/api/bootstrap")
        self.assertEqual(status, 200)
        synthesis = next(s for s in project["workflow"] if s["id"] == "global_synthesis")
        self.assertTrue(synthesis["implemented"])
        self.assertEqual(synthesis["accepted_run_id"], "software-run")
        layout = next(s for s in project["workflow"] if s["id"] == "layout")
        self.assertTrue(layout["implemented"])
        self.assertEqual(layout["execution_status"], "Not Run")
        self.assertFalse(project["implementation"]["layout_executed"])
        status, raw, value = self.request("/api/artifacts/global-workflow/software-run/verification-plan")
        self.assertEqual(status, 200)
        self.assertEqual(value["configuration_word"], 2**133 + 123)
        self.assertIn(str(2**133 + 123).encode(), raw)
        self.assertEqual(self.request("/api/artifacts/global-workflow/software-run/netlist")[2],
                         "// SOFTWARE QA netlist placeholder; never compiled\n")
        for path in ("/api/artifacts/global-workflow/software-run/arbitrary-expression",
                     "/api/artifacts/global-workflow/../verification-plan", "/api/global-workflow/runs/missing"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)
        self.assertEqual(self.double.calls, [])

    def test_start_cancel_review_and_invalid_routes(self):
        status, _, value = self.request("/api/global-workflow/runs", {"stage": "global_netlist_simulation",
            "global_job_id": "software-global", "synthesis_run_id": "software-synth", "revision_id": "software-revision"})
        self.assertEqual(status, 202)
        self.assertEqual(self.double.calls[-1], ("start", ("global_netlist_simulation", "software-global", "software-synth", "software-revision")))
        self.assertEqual(self.request("/api/global-workflow/runs/software-run/cancel", {})[0], 200)
        self.assertEqual(self.request("/api/global-workflow/runs/software-run/review", {
            "decision": "changes_requested", "note": "SOFTWARE QA feedback", "target_stage": "global_rtl_generation"})[0], 200)
        self.assertEqual(self.double.calls[-1], ("review", ("software-run", "changes_requested", "SOFTWARE QA feedback", "global_rtl_generation")))
        for path, body in (("/api/global-workflow/runs", {"stage": "global_synthesis"}),
                           ("/api/global-workflow/runs/software-run/unknown", {}),
                           ("/api/global-workflow/runs/software-run/review", {"decision": "accepted"})):
            with self.subTest(path=path):
                self.assertIn(self.request(path, body)[0], (400, 404))

    def test_active_whole_tool_run_blocks_competing_execution(self):
        self.double.active = True
        bodies = [("/api/global-workflow/runs", {"stage": "global_synthesis", "global_job_id": "qa"}),
                  ("/api/workflow/start", {"stage_id": "local_synthesis", "node_id": "node-pe", "candidate_id": "qa", "revision_id": "qa"}),
                  ("/api/llm/probe", {"profile_revision_id": "qa"}),
                  ("/api/global-generation/start", {"revision_id": "qa", "context_id": "qa", "profile_revision_id": "qa"}),
                  ("/api/generation/start", {"node_id": "node-pe", "revision_id": "qa", "context_id": "qa", "profile_revision_id": "qa"})]
        for path, body in bodies:
            with self.subTest(path=path):
                status, _, value = self.request(path, body)
                self.assertEqual(status, 409)
                self.assertEqual(value["error"]["code"], "global_workflow_busy")
        self.assertEqual(self.double.calls, [])

    def test_active_node_execution_blocks_whole_tool_admission(self):
        for manager, key in ((self.server.generation, "jobs"), (self.server.workflow, "runs")):
            with self.subTest(key=key):
                manager._state[key].append({"execution_status": "Running"})
                try:
                    status, _, value = self.request("/api/global-workflow/runs", {
                        "stage": "global_synthesis", "global_job_id": "qa"})
                    self.assertEqual(status, 409)
                    self.assertEqual(value["error"]["code"], "competing_execution_busy")
                finally:
                    manager._state[key].pop()
        self.assertEqual(self.double.calls, [])


if __name__ == "__main__":
    unittest.main()

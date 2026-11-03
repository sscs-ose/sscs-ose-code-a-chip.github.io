"""S12 loopback route/admission QA. All reported DRC states are explicit doubles."""
from __future__ import annotations

from contextlib import ExitStack
import http.client
import json
import threading
import unittest
from unittest.mock import patch

import test_global_generation as fixtures
from hullcirq.domain import DomainError
from hullcirq.drc_workflow import FILE_IDS
from hullcirq.server import make_server
from hullcirq.store import strict_loads


class DrcDouble:
    def __init__(self, revision_id):
        self.active = False; self.visible = False; self.calls = []; self.revision_id = revision_id
        self.record = {"id": "software-drc", "stage_id": "drc", "layout_run_id": "software-layout", "execution_status": "Completed", "validation_status": "Failed",
                       "review_status": "Awaiting Review", "freshness": "Current", "checks": {}, "software_qa_fixture": True}
        self.binary = {name: (b"SOFTWARE_QA_RAW\r\n\x00\xff", "application/octet-stream" if name == "input-gds" else "application/json" if name in
                       ("config", "initial-state", "final-state", "metrics", "tool-versions", "drc-summary", "klayout-violations") else "application/xml" if name in
                       ("magic-markers", "klayout-report") else "text/plain; charset=utf-8") for name in FILE_IDS}

    def envelope(self):
        return {"drc_workflow": {"implemented": True, "stage_id": "drc", "runs": [self.record] if self.visible else [], "reviews": [],
                "latest_run_id": self.record["id"] if self.visible else None, "accepted_run_id": None, "ready": False,
                "blocked_reason": "SOFTWARE QA double; no EDA execution", "tool_ready": False, "configuration_sha256": None}}

    def start(self, stage, layout_run_id, revision_id=None):
        if stage != "drc" or layout_run_id != "software-layout" or revision_id != self.revision_id:
            raise DomainError("drc_source_conflict", "SOFTWARE QA ID mismatch", 409)
        self.calls.append(("start", (stage, layout_run_id, revision_id))); self.active = True; self.visible = True
        self.record.update(execution_status="Queued", validation_status="Not Checked")
        # Match the real manager return contract; no worker or receipt is created.
        return self.envelope()

    def run(self, identifier):
        if identifier != self.record["id"]: raise DomainError("drc_run_not_found", "SOFTWARE QA missing run", 404)
        return self.record

    def cancel(self, identifier):
        self.run(identifier); self.calls.append(("cancel", identifier)); self.active = False; self.record["execution_status"] = "Cancelled"

    def review(self, *args, operator=None): self.run(args[0]); self.calls.append(("review", args))
    def is_active(self): return self.active
    def close(self): pass

    def artifact(self, identifier, field):
        self.run(identifier)
        if field in ("layout-record", "source-identity", "runtime-configuration"):
            return {"configuration_word": 2**133 + 123, "software_qa_fixture": True}
        if field == "artifact-manifest": return [{"id": name, "software_qa_fixture": True} for name in self.binary]
        raise DomainError("drc_artifact_not_found", "SOFTWARE QA missing artifact", 404)

    def artifact_bytes(self, identifier, field):
        self.run(identifier)
        if field not in self.binary: raise DomainError("drc_artifact_not_found", "SOFTWARE QA missing raw artifact", 404)
        return self.binary[field]


class DrcWorkflowHTTPTests(unittest.TestCase):
    def setUp(self):
        self.qa = fixtures.GlobalSoftwareTests("runTest"); self.qa.setUp(); self.addCleanup(self.qa.doCleanups)
        self.server = make_server("127.0.0.1", 0, self.qa.store, fixtures.PROJECT)
        self.original = self.server.drc_workflow
        self.double = DrcDouble(self.qa.store.envelope()["revision"]["id"]); self.server.drc_workflow = self.double
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .02}, daemon=True); self.thread.start(); self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown(); self.server.server_close(); self.original.close(); self.server.workflow.close(); self.server.generation.close(); self.thread.join(2)

    def request(self, path, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=20)
        try:
            connection.request("GET" if body is None else "POST", path, None if body is None else json.dumps(body), {} if body is None else {"Content-Type": "application/json"})
            response = connection.getresponse(); raw = response.read()
            return response.status, raw, dict(response.getheaders())
        finally: connection.close()

    def json_request(self, path, body=None):
        status, raw, headers = self.request(path, body)
        return status, raw, strict_loads(raw.decode("utf-8")), headers

    def start_body(self): return {"stage": "drc", "layout_run_id": "software-layout", "revision_id": self.double.revision_id}

    def test_implemented_without_sources_or_runtime_reports_not_run(self):
        self.server.drc_workflow = self.original
        status, _, project, _ = self.json_request("/api/bootstrap")
        self.assertEqual(status, 200); self.assertEqual(project["implementation"]["milestone"], "M2-J")
        drc = next(s for s in project["workflow"] if s["id"] == "drc")
        self.assertTrue(drc["implemented"]); self.assertEqual(drc["execution_status"], "Not Run"); self.assertIsNone(drc["accepted_run_id"])
        self.assertFalse(project["drc_workflow"]["tool_ready"]); self.assertFalse(project["implementation"]["drc_executed"])
        self.assertTrue(next(s for s in project["workflow"] if s["id"] == "lvs")["implemented"])
        self.assertTrue(next(s for s in project["workflow"] if s["id"] == "post_layout_verification")["implemented"])
        self.assertFalse(self.original._state["runs"])

    def test_exact_source_start_cancel_review_and_invalid_routes(self):
        status, _, project, _ = self.json_request("/api/drc-workflow/runs", self.start_body())
        self.assertEqual(status, 202); self.assertEqual(self.double.calls[-1], ("start", ("drc", "software-layout", self.double.revision_id)))
        self.assertEqual(next(s for s in project["workflow"] if s["id"] == "drc")["execution_status"], "Queued")
        self.assertEqual(self.json_request("/api/drc-workflow/runs/software-drc")[2]["id"], "software-drc")
        self.assertEqual(self.json_request("/api/drc-workflow/runs/software-drc/cancel", {})[0], 200)
        self.assertEqual(self.double.calls[-1], ("cancel", "software-drc"))
        body = {"decision": "return_to_stage", "note": "SOFTWARE QA feedback", "target_stage": "layout"}
        self.assertEqual(self.json_request("/api/drc-workflow/runs/software-drc/review", body)[0], 200)
        self.assertEqual(self.double.calls[-1], ("review", ("software-drc", "return_to_stage", "SOFTWARE QA feedback", "layout")))
        for key in ("stage", "layout_run_id"):
            body = self.start_body(); body.pop(key)
            with self.subTest(missing=key): self.assertEqual(self.json_request("/api/drc-workflow/runs", body)[0], 400)
        self.assertEqual(self.json_request("/api/drc-workflow/runs", dict(self.start_body(), layout_run_id="old"))[0], 409)
        self.assertEqual(self.json_request("/api/drc-workflow/runs/software-drc/unknown", {})[0], 404)
        self.assertEqual(self.json_request("/api/drc-workflow/runs/software-drc/review", {"decision": "accepted"})[0], 400)

    def test_all_fixed_raw_files_keep_original_bytes_mime_headers_and_no_mutation(self):
        for name, (expected, mime) in self.double.binary.items():
            with self.subTest(artifact=name):
                status, raw, headers = self.request("/api/artifacts/drc-workflow/software-drc/" + name)
                self.assertEqual(status, 200); self.assertEqual(raw, expected); self.assertEqual(headers["Content-Type"], mime)
                self.assertEqual(int(headers["Content-Length"]), len(expected)); self.assertEqual(headers["Content-Disposition"], f'attachment; filename="drc-{name}"')
                self.assertEqual(headers["Cache-Control"], "no-store"); self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertFalse(self.double.calls)

    def test_json_documents_keep_wide_integer_and_deny_unknown_path_expressions(self):
        for name in ("layout-record", "source-identity", "runtime-configuration"):
            status, raw, value, headers = self.json_request("/api/artifacts/drc-workflow/software-drc/" + name)
            self.assertEqual(status, 200); self.assertEqual(value["configuration_word"], 2**133 + 123); self.assertIn(str(2**133 + 123).encode(), raw)
            self.assertIn("attachment", headers["Content-Disposition"])
        for path in ("/api/artifacts/drc-workflow/software-drc/arbitrary-expression", "/api/artifacts/drc-workflow/../magic-report",
                     "/api/artifacts/drc-workflow/software-drc/%2e%2e%2fstate.json", "/api/artifacts/drc-workflow/software%5Cdrc/config",
                     "/api/artifacts/drc-workflow/software-drc/config/extra", "/api/drc-workflow/runs/missing", "/api/drc-workflow/runs/software-drc/extra"):
            with self.subTest(path=path): self.assertEqual(self.json_request(path)[0], 404)
        self.assertFalse(self.double.calls)

    def test_active_drc_blocks_all_execution_starts_revalidation_and_probe(self):
        self.double.active = True
        cases = [("/api/drc-workflow/runs", self.start_body()), ("/api/physical-workflow/runs", {"stage": "layout"}),
                 ("/api/physical-workflow/runs/software-layout/revalidate", {}), ("/api/global-workflow/runs", {"stage": "global_synthesis"}),
                 ("/api/workflow/start", {"stage_id": "local_synthesis"}), ("/api/llm/probe", {"profile_revision_id": "qa"}),
                 ("/api/global-generation/start", {"revision_id": "qa"}), ("/api/generation/start", {"node_id": "qa"})]
        with ExitStack() as stack:
            protected = [stack.enter_context(patch.object(manager, method)) for manager, method in
                         ((self.server.physical_workflow, "start"), (self.server.physical_workflow, "revalidate"), (self.server.global_workflow, "start"),
                          (self.server.workflow, "start"), (self.server.generation, "probe"), (self.server.global_generation, "start"), (self.server.generation, "start"))]
            for path, body in cases:
                with self.subTest(path=path):
                    status, _, value, _ = self.json_request(path, body); self.assertEqual(status, 409); self.assertEqual(value["error"]["code"], "drc_workflow_busy")
            for mocked in protected: mocked.assert_not_called()
        self.assertFalse(self.double.calls)

    def test_active_layout_earlier_tool_and_model_block_drc_admission(self):
        for manager in (self.server.physical_workflow, self.server.global_workflow, self.server.global_generation):
            with patch.object(manager, "is_active", return_value=True):
                status, _, value, _ = self.json_request("/api/drc-workflow/runs", self.start_body())
                self.assertEqual(status, 409); self.assertIn(value["error"]["code"], ("physical_workflow_busy", "global_workflow_busy", "competing_execution_busy"))
        self.assertFalse(self.double.calls)

    def test_inflight_probe_serializes_drc_start_without_overlap_or_retry(self):
        entered = threading.Event(); release = threading.Event(); done = threading.Event(); requested = threading.Event(); outcomes = {}
        def probe(*args): entered.set(); release.wait(5)
        def request_probe(): outcomes["probe"] = self.json_request("/api/llm/probe", {"profile_revision_id": "software-only"})[0]
        def request_drc(): requested.set(); outcomes["drc"] = self.json_request("/api/drc-workflow/runs", self.start_body())[0]; done.set()
        with patch.object(self.server.generation, "probe", side_effect=probe):
            a = threading.Thread(target=request_probe); b = threading.Thread(target=request_drc)
            a.start(); self.assertTrue(entered.wait(5)); b.start(); self.assertTrue(requested.wait(5))
            try: self.assertFalse(done.wait(.1)); self.assertFalse(self.double.calls)
            finally: release.set(); a.join(10); b.join(10)
        self.assertEqual(outcomes, {"probe": 200, "drc": 202}); self.assertEqual(len(self.double.calls), 1)


if __name__ == "__main__": unittest.main()

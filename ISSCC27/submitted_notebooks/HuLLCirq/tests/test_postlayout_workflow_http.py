"""S14 loopback route/admission QA. All reported dynamic states are explicit doubles."""
from __future__ import annotations

from contextlib import ExitStack
import http.client
import json
import threading
import unittest
from unittest.mock import patch

import test_global_generation as fixtures
from hullcirq.domain import DomainError
from hullcirq.postlayout_workflow import FILE_IDS
from hullcirq.server import make_server
from hullcirq.store import strict_loads


class PostLayoutDouble:
    def __init__(self, revision_id):
        self.active = False; self.visible = False; self.calls = []; self.revision_id = revision_id
        self.record = {"id": "software-postlayout", "stage_id": "post_layout_verification", "layout_run_id": "software-layout", "drc_run_id": "software-drc", "lvs_run_id": "software-lvs", "execution_status": "Completed", "validation_status": "Failed",
                       "review_status": "Awaiting Review", "freshness": "Current", "checks": {}, "software_qa_fixture": True}
        self.binary = {name: (b"SOFTWARE_QA_RAW\r\n\x00\xff", "application/octet-stream" if name == "input-gds" else "application/json" if name in
                       ("config", "initial-state", "final-state", "metrics", "tool-versions", "lvs-summary", "lvs-json") else "application/xml" if name in
                       ("extraction-markers",) else "text/plain; charset=utf-8") for name in FILE_IDS}

    def envelope(self):
        return {"postlayout_workflow": {"implemented": True, "stage_id": "post_layout_verification", "runs": [self.record] if self.visible else [], "reviews": [],
                "latest_run_id": self.record["id"] if self.visible else None, "accepted_run_id": None, "ready": False,
                "blocked_reason": "SOFTWARE QA double; no EDA execution", "tool_ready": False, "configuration_sha256": None}}

    def start(self, stage, layout_run_id, drc_run_id, lvs_run_id, revision_id=None):
        if stage != "post_layout_verification" or lvs_run_id != "software-lvs" or layout_run_id != "software-layout" or drc_run_id != "software-drc" or revision_id != self.revision_id:
            raise DomainError("lvs_source_conflict", "SOFTWARE QA ID mismatch", 409)
        self.calls.append(("start", (stage, layout_run_id, drc_run_id, lvs_run_id, revision_id))); self.active = True; self.visible = True
        self.record.update(execution_status="Queued", validation_status="Not Checked")
        # Match the real manager return contract; no worker or receipt is created.
        return self.envelope()

    def prepare_profile(self, layout_run_id, drc_run_id, lvs_run_id, revision_id):
        if (layout_run_id, drc_run_id, lvs_run_id, revision_id) != ("software-layout", "software-drc", "software-lvs", self.revision_id):
            raise DomainError("postlayout_source_conflict", "SOFTWARE QA ID mismatch", 409)
        self.calls.append(("prepare_profile", (layout_run_id, drc_run_id, lvs_run_id, revision_id)))

    def save_adapter_contract(self, layout_run_id, drc_run_id, lvs_run_id, revision_id, contract):
        if (layout_run_id, drc_run_id, lvs_run_id, revision_id) != ("software-layout", "software-drc", "software-lvs", self.revision_id):
            raise DomainError("postlayout_source_conflict", "SOFTWARE QA ID mismatch", 409)
        self.calls.append(("save_adapter_contract", (layout_run_id, drc_run_id, lvs_run_id, revision_id, contract)))

    def run(self, identifier):
        if identifier != self.record["id"]: raise DomainError("lvs_run_not_found", "SOFTWARE QA missing run", 404)
        return self.record

    def cancel(self, identifier):
        self.run(identifier); self.calls.append(("cancel", identifier)); self.active = False; self.record["execution_status"] = "Cancelled"

    def review(self, *args, operator=None): self.run(args[0]); self.calls.append(("review", args))
    def verify_saved_termination(self, identifier):
        self.run(identifier); self.calls.append(("verify_saved_termination", identifier)); self.active = False
    def is_active(self): return self.active
    def close(self): pass

    def artifact(self, identifier, field):
        self.run(identifier)
        if field in ("lvs-record", "drc-record", "layout-record", "source-identity", "runtime-configuration", "verification-plan"):
            return {"configuration_word": 2**133 + 123, "software_qa_fixture": True}
        if field == "artifact-manifest": return [{"id": name, "software_qa_fixture": True} for name in self.binary]
        raise DomainError("lvs_artifact_not_found", "SOFTWARE QA missing artifact", 404)

    def artifact_bytes(self, identifier, field):
        self.run(identifier)
        if field not in self.binary: raise DomainError("lvs_artifact_not_found", "SOFTWARE QA missing raw artifact", 404)
        return self.binary[field]


class PostLayoutWorkflowHTTPTests(unittest.TestCase):
    def setUp(self):
        self.qa = fixtures.GlobalSoftwareTests("runTest"); self.qa.setUp(); self.addCleanup(self.qa.doCleanups)
        self.server = make_server("127.0.0.1", 0, self.qa.store, fixtures.PROJECT)
        self.original = self.server.postlayout_workflow
        self.double = PostLayoutDouble(self.qa.store.envelope()["revision"]["id"]); self.server.postlayout_workflow = self.double
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

    def start_body(self): return {"stage": "post_layout_verification", "layout_run_id": "software-layout", "drc_run_id": "software-drc", "lvs_run_id": "software-lvs", "revision_id": self.double.revision_id}
    def profile_body(self): return {key: value for key, value in self.start_body().items() if key != "stage"}

    def test_implemented_without_sources_or_runtime_reports_not_run(self):
        self.server.postlayout_workflow = self.original
        status, _, project, _ = self.json_request("/api/bootstrap")
        self.assertEqual(status, 200); self.assertEqual(project["implementation"]["milestone"], "M2-J")
        lvs = next(s for s in project["workflow"] if s["id"] == "post_layout_verification")
        self.assertTrue(lvs["implemented"]); self.assertEqual(lvs["execution_status"], "Not Run"); self.assertIsNone(lvs["accepted_run_id"])
        self.assertFalse(project["postlayout_workflow"]["tool_ready"]); self.assertFalse(project["implementation"]["postlayout_executed"])
        self.assertTrue(next(s for s in project["workflow"] if s["id"] == "drc")["implemented"])
        self.assertTrue(next(s for s in project["workflow"] if s["id"] == "lvs")["implemented"])
        self.assertFalse(self.original._state["runs"])

    def test_exact_source_start_cancel_review_and_invalid_routes(self):
        status, _, project, _ = self.json_request("/api/postlayout-workflow/runs", self.start_body())
        self.assertEqual(status, 202); self.assertEqual(self.double.calls[-1], ("start", ("post_layout_verification", "software-layout", "software-drc", "software-lvs", self.double.revision_id)))
        self.assertEqual(next(s for s in project["workflow"] if s["id"] == "post_layout_verification")["execution_status"], "Queued")
        self.assertEqual(self.json_request("/api/postlayout-workflow/runs/software-postlayout")[2]["id"], "software-postlayout")
        self.assertEqual(self.json_request("/api/postlayout-workflow/runs/software-postlayout/cancel", {})[0], 200)
        self.assertEqual(self.double.calls[-1], ("cancel", "software-postlayout"))
        body = {"decision": "return_to_stage", "note": "SOFTWARE QA feedback", "target_stage": "layout"}
        self.assertEqual(self.json_request("/api/postlayout-workflow/runs/software-postlayout/review", body)[0], 200)
        self.assertEqual(self.double.calls[-1], ("review", ("software-postlayout", "return_to_stage", "SOFTWARE QA feedback", "layout")))
        for key in ("stage", "layout_run_id", "drc_run_id", "lvs_run_id"):
            body = self.start_body(); body.pop(key)
            with self.subTest(missing=key): self.assertEqual(self.json_request("/api/postlayout-workflow/runs", body)[0], 400)
        self.assertEqual(self.json_request("/api/postlayout-workflow/runs", dict(self.start_body(), layout_run_id="old"))[0], 409)
        self.assertEqual(self.json_request("/api/postlayout-workflow/runs/software-postlayout/unknown", {})[0], 404)
        self.assertEqual(self.json_request("/api/postlayout-workflow/runs/software-postlayout/review", {"decision": "accepted"})[0], 400)

    def test_profile_preparation_accepts_only_exact_ids_and_revision(self):
        status, _, _, _ = self.json_request("/api/postlayout-workflow/profile", self.profile_body())
        self.assertEqual(status, 200)
        self.assertEqual(self.double.calls[-1], ("prepare_profile", ("software-layout", "software-drc", "software-lvs", self.double.revision_id)))
        before = len(self.double.calls)
        for body in ({**self.profile_body(), "working_directory": "C:/arbitrary"},
                     {key: value for key, value in self.profile_body().items() if key != "revision_id"},
                     {**self.profile_body(), "layout_run_id": "old"}):
            with self.subTest(body=body): self.assertIn(self.json_request("/api/postlayout-workflow/profile", body)[0], (400, 409))
        self.assertEqual(len(self.double.calls), before)

    def test_all_fixed_raw_files_keep_original_bytes_mime_headers_and_no_mutation(self):
        for name, (expected, mime) in self.double.binary.items():
            with self.subTest(artifact=name):
                status, raw, headers = self.request("/api/artifacts/postlayout-workflow/software-postlayout/" + name)
                self.assertEqual(status, 200); self.assertEqual(raw, expected); self.assertEqual(headers["Content-Type"], mime)
                self.assertEqual(int(headers["Content-Length"]), len(expected)); self.assertEqual(headers["Content-Disposition"], f'attachment; filename="postlayout-{name}"')
                self.assertEqual(headers["Cache-Control"], "no-store"); self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertFalse(self.double.calls)

    def test_adapter_contract_is_metadata_only_exact_source_guarded_and_idle(self):
        path = "/api/postlayout-workflow/adapter-contract"
        contract = {"software_qa_fixture": True}
        body = dict(self.profile_body(), contract=contract)
        self.assertEqual(self.json_request(path, body)[0], 200)
        self.assertEqual(self.double.calls, [("save_adapter_contract", (
            "software-layout", "software-drc", "software-lvs", self.double.revision_id, contract))])
        self.double.calls.clear()
        for invalid in ({**body, "command": "not-allowed"},
                        {k: v for k, v in body.items() if k != "contract"}):
            self.assertEqual(self.json_request(path, invalid)[0], 400)
        self.assertEqual(self.json_request(path, {**body, "layout_run_id": "old"})[0], 409)
        with patch.object(self.server.physical_workflow, "is_active", return_value=True):
            self.assertEqual(self.json_request(path, body)[0], 409)
        self.assertFalse(self.double.calls)

    def test_saved_termination_route_allows_target_cleanup_lock_but_rejects_paths_and_other_workers(self):
        self.double.active = True
        path = "/api/postlayout-workflow/runs/software-postlayout/verify-termination"
        self.assertEqual(self.json_request(path, {"path": "C:/arbitrary"})[0], 400)
        with patch.object(self.server.physical_workflow, "is_active", return_value=True):
            self.assertEqual(self.json_request(path, {})[0], 409)
        with patch.object(self.server.repair_analysis, "is_active", return_value=True):
            self.assertEqual(self.json_request(path, {})[0], 409)
        self.assertFalse(self.double.calls)
        self.assertEqual(self.json_request(path, {})[0], 200)
        self.assertEqual(self.double.calls, [("verify_saved_termination", "software-postlayout")])
        self.assertFalse(self.double.active)

    def test_physical_repair_route_only_passes_fixed_ids_after_normal_idle_checks(self):
        path = "/api/postlayout-workflow/physical-repair-profile"
        body = {"failed_s14_id": "software-postlayout", "revision_id": self.double.revision_id}
        with patch("hullcirq.physical_repair_session.prepare_repair") as prepare:
            for invalid in ({**body, "configuration": {}}, {**body, "path": "C:/arbitrary"},
                            {"failed_s14_id": "software-postlayout"}, {"revision_id": self.double.revision_id}):
                with self.subTest(invalid=invalid): self.assertEqual(self.json_request(path, invalid)[0], 400)
            self.double.active = True
            self.assertEqual(self.json_request(path, body)[0], 409)
            self.double.active = False
            with patch.object(self.server.repair_analysis, "is_active", return_value=True):
                self.assertEqual(self.json_request(path, body)[0], 409)
            prepare.assert_not_called()
            status = {"configured": True, "bundle_present": True, "error": None,
                      "source_identity": {"failed_s14_id": "software-postlayout"}, "profile_version": "SOFTWARE_QA_FIXED_REPAIR"}
            def apply_profile(*args): self.server.physical_repair_session = status
            prepare.side_effect = apply_profile
            response_status, _, project, _ = self.json_request(path, body)
            self.assertEqual(response_status, 200)
            prepare.assert_called_once_with(self.server, "software-postlayout", self.double.revision_id)
            self.assertEqual(project["physical_repair_session"], status)
            self.assertFalse(self.double.calls)
        from hullcirq.server import project_envelope
        project = project_envelope(self.server)
        project["physical_repair_session"]["source_identity"]["failed_s14_id"] = "CHANGED_RESPONSE_COPY"
        self.assertEqual(status["source_identity"]["failed_s14_id"], "software-postlayout")

    def test_functional_plus_sta_metadata_does_not_claim_dynamic_sdf_support(self):
        original = self.double.envelope
        def supported():
            value = original()
            value["postlayout_workflow"].update(verification_supported=True, execution_scope="post_route_functional_plus_sta")
            return value
        with patch.object(self.double, "envelope", side_effect=supported):
            implementation = self.json_request("/api/project")[2]["implementation"]
        self.assertFalse(implementation["dynamic_postlayout_supported"])
        self.assertTrue(implementation["postlayout_verification_supported"])
        self.assertEqual(implementation["postlayout_execution_scope"], "post_route_functional_plus_sta")

    def test_json_documents_keep_wide_integer_and_deny_unknown_path_expressions(self):
        for name in ("lvs-record", "drc-record", "layout-record", "source-identity", "runtime-configuration", "verification-plan"):
            status, raw, value, headers = self.json_request("/api/artifacts/postlayout-workflow/software-postlayout/" + name)
            self.assertEqual(status, 200); self.assertEqual(value["configuration_word"], 2**133 + 123); self.assertIn(str(2**133 + 123).encode(), raw)
            self.assertIn("attachment", headers["Content-Disposition"])
        for path in ("/api/artifacts/postlayout-workflow/software-postlayout/arbitrary-expression", "/api/artifacts/postlayout-workflow/../lvs-report",
                     "/api/artifacts/postlayout-workflow/software-postlayout/%2e%2e%2fstate.json", "/api/artifacts/postlayout-workflow/software%5Clvs/config",
                     "/api/artifacts/postlayout-workflow/software-postlayout/config/extra", "/api/postlayout-workflow/runs/missing", "/api/postlayout-workflow/runs/software-postlayout/extra"):
            with self.subTest(path=path): self.assertEqual(self.json_request(path)[0], 404)
        self.assertFalse(self.double.calls)

    def test_active_postlayout_blocks_all_execution_starts_revalidation_and_probe(self):
        self.double.active = True
        cases = [("/api/postlayout-workflow/runs", self.start_body()), ("/api/lvs-workflow/runs", {"stage": "lvs"}), ("/api/drc-workflow/runs", {"stage": "drc"}), ("/api/physical-workflow/runs", {"stage": "layout"}),
                 ("/api/physical-workflow/runs/software-layout/revalidate", {}), ("/api/global-workflow/runs", {"stage": "global_synthesis"}),
                 ("/api/workflow/start", {"stage_id": "local_synthesis"}), ("/api/llm/probe", {"profile_revision_id": "qa"}),
                 ("/api/global-generation/start", {"revision_id": "qa"}), ("/api/generation/start", {"node_id": "qa"})]
        with ExitStack() as stack:
            protected = [stack.enter_context(patch.object(manager, method)) for manager, method in
                         ((self.server.lvs_workflow, "start"), (self.server.drc_workflow, "start"), (self.server.physical_workflow, "start"), (self.server.physical_workflow, "revalidate"), (self.server.global_workflow, "start"),
                          (self.server.workflow, "start"), (self.server.generation, "probe"), (self.server.global_generation, "start"), (self.server.generation, "start"))]
            for path, body in cases:
                with self.subTest(path=path):
                    status, _, value, _ = self.json_request(path, body); self.assertEqual(status, 409); self.assertEqual(value["error"]["code"], "postlayout_workflow_busy")
            for mocked in protected: mocked.assert_not_called()
        self.assertFalse(self.double.calls)

    def test_active_lvs_layout_earlier_tool_and_model_block_postlayout_admission(self):
        for manager in (self.server.lvs_workflow, self.server.drc_workflow, self.server.physical_workflow, self.server.global_workflow, self.server.global_generation):
            with patch.object(manager, "is_active", return_value=True):
                status, _, value, _ = self.json_request("/api/postlayout-workflow/runs", self.start_body())
                self.assertEqual(status, 409); self.assertIn(value["error"]["code"], ("lvs_workflow_busy", "drc_workflow_busy", "physical_workflow_busy", "global_workflow_busy", "competing_execution_busy"))
        self.assertFalse(self.double.calls)

    def test_inflight_probe_serializes_postlayout_start_without_overlap_or_retry(self):
        entered = threading.Event(); release = threading.Event(); done = threading.Event(); requested = threading.Event(); outcomes = {}
        def probe(*args): entered.set(); release.wait(5)
        def request_probe(): outcomes["probe"] = self.json_request("/api/llm/probe", {"profile_revision_id": "software-only"})[0]
        def request_lvs(): requested.set(); outcomes["lvs"] = self.json_request("/api/postlayout-workflow/runs", self.start_body())[0]; done.set()
        with patch.object(self.server.generation, "probe", side_effect=probe):
            a = threading.Thread(target=request_probe); b = threading.Thread(target=request_lvs)
            a.start(); self.assertTrue(entered.wait(5)); b.start(); self.assertTrue(requested.wait(5))
            try: self.assertFalse(done.wait(.1)); self.assertFalse(self.double.calls)
            finally: release.set(); a.join(10); b.join(10)
        self.assertEqual(outcomes, {"probe": 200, "lvs": 202}); self.assertEqual(len(self.double.calls), 1)


if __name__ == "__main__": unittest.main()

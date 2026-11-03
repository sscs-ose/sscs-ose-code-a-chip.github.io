"""Isolated derived-view HTTP routes; no live project, capture, render or EDA.

The saved source is a deliberately tiny software fixture. A controllable service
double replaces all generation work; no claimed circuit evidence is produced.
"""
from __future__ import annotations

import copy
import http.client
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from hullcirq.domain import DomainError
from hullcirq.server import make_server
from hullcirq.store import ProjectStore
from hullcirq.verification import object_hash
from hullcirq.workspace_server import WorkspaceRuntime
import test_layout_map_source as source_fixtures


class PhysicalSnapshotDouble:
    """Only immutable selection/status reads; never observes or persists."""
    def __init__(self, record):
        self.lock = threading.RLock()
        self._state = {"runs": [copy.deepcopy(record)]}
        self.freshness = "Current"
        self.observe_design = Mock(side_effect=AssertionError("No source-epoch mutation"))
        self._persist = Mock(side_effect=AssertionError("No saved-layout mutation"))
        self.start = Mock(side_effect=AssertionError("No EDA"))
        self.review = Mock(side_effect=AssertionError("No adoption"))

    def _run(self, identifier):
        value = next((record for record in self._state["runs"] if record["id"] == identifier), None)
        if value is None:
            raise DomainError("physical_run_not_found", "No selected software fixture.", 404)
        return value

    def _decorate(self, record):
        decorated = copy.deepcopy(record)
        decorated["freshness"] = self.freshness
        return decorated

    def run(self, identifier):
        return self._decorate(self._run(identifier))

    def is_active(self):
        return False

    def close(self):
        pass


class GenerationServiceDouble:
    """Metadata only: does not invoke source capture, renderer or any process."""
    def __init__(self):
        self.jobs = []
        self.calls = []
        self.status_calls = []
        self.active = False
        self.registration = None

    def is_active(self):
        return self.active

    def status(self, record, scope):
        self.status_calls.append((copy.deepcopy(record), copy.deepcopy(scope)))
        jobs = [copy.deepcopy(job) for job in self.jobs
                if job["layout_run_id"] == record["id"] and job["scope_identity"] == scope]
        return {"jobs": jobs, "latest_job": jobs[-1] if jobs else None,
                "registration": copy.deepcopy(self.registration),
                "additional_eda_model_or_simulation_runs": 0}

    def start(self, record, expected_record_hash, scope):
        if expected_record_hash != record["record_hash"]:
            raise DomainError("functional_map_source_changed", "Refresh the exact selected record hash.", 409)
        self.calls.append((copy.deepcopy(record), expected_record_hash, copy.deepcopy(scope)))
        self.jobs.append({"id": "functional-map-" + str(len(self.calls)) * 32,
            "layout_run_id": record["id"], "scope_identity": copy.deepcopy(scope),
            "status": "Queued", "phase": "Queued", "created_at": "2026-10-21T00:00:00+00:00",
            "finished_at": None, "error": None, "registration": None,
            "software_qa_fixture": True, "additional_eda_model_or_simulation_runs": 0})
        self.active = True
        return copy.deepcopy(self.jobs[-1])

    def close(self):
        pass


class SessionWorkspaceDouble:
    """Uses the production session/read-only guard with no actual registry."""
    require_session = WorkspaceRuntime.require_session

    def __init__(self, read_only=False):
        self.identity = {"project_id": "software-qa-project", "system_id": "software-qa-system",
                         "session_id": "software-qa-session", "read_only": read_only}
        self.context = object()
        self.folder_picker = SimpleNamespace(close=lambda: None)

    def close(self):
        pass


class FunctionalMapGenerationHTTPTests(unittest.TestCase):
    def setUp(self):
        self.source = source_fixtures.LayoutMapSourceTests("test_new_run_is_complete_read_only_and_renderer_compatible")
        self.source.setUp()
        self.addCleanup(self.source.doCleanups)
        self.root = self.source.root
        self.store = ProjectStore(self.root / ".work/store")
        self.source.run["revision_id"] = self.store.envelope()["revision"]["id"]
        self.source._hash()
        self.server = make_server("127.0.0.1", 0, self.store, self.root)
        self.original_physical = self.server.physical_workflow
        self.physical = PhysicalSnapshotDouble(self.source.run)
        self.server.physical_workflow = self.physical
        self.generation = GenerationServiceDouble()
        self.server.functional_map_generation = self.generation
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": .01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.path = "/api/physical-workflow/runs/" + self.source.run["id"] + "/functional-map-generation"
        self.body = {"revision_id": self.source.run["revision_id"], "record_hash": self.source.run["record_hash"]}
        self.original_files = self.snapshot()
        self.original_record = copy.deepcopy(self.physical._state)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.original_physical.close()
        self.thread.join(3)

    def snapshot(self):
        return {path.relative_to(self.root).as_posix(): path.read_bytes()
                for path in self.root.rglob("*") if path.is_file()}

    def request(self, method="GET", path=None, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        request_headers = dict(headers or {})
        payload = None
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        try:
            connection.request(method, self.path if path is None else path,
                               body=payload, headers=request_headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def assert_untouched(self):
        self.assertEqual(self.original_files, self.snapshot())
        self.assertEqual(self.original_record, self.physical._state)
        self.physical.observe_design.assert_not_called()
        self.physical._persist.assert_not_called()
        self.physical.start.assert_not_called()
        self.physical.review.assert_not_called()

    def test_empty_get_is_read_only_and_creates_no_generation_files(self):
        status, result = self.request()
        self.assertEqual(status, 200, result)
        self.assertEqual(result["run_id"], self.source.run["id"])
        self.assertEqual(result["jobs"], [])
        self.assertIsNone(result["latest_job"])
        self.assertTrue(result["can_generate"])
        self.assertFalse(result["registered"])
        self.assertEqual(result["scope"], "derived_read_only_presentation_not_circuit_execution")
        self.assertFalse(self.generation.calls)
        self.assert_untouched()

    def test_explicit_post_uses_exact_snapshot_hash_and_returns_separate_job_history(self):
        status, result = self.request("POST", body=self.body)
        self.assertEqual(status, 202, result)
        self.assertEqual(result["run_id"], self.source.run["id"])
        self.assertEqual(result["latest_job"]["status"], "Queued")
        self.assertEqual(result["latest_job"]["layout_run_id"], self.source.run["id"])
        self.assertEqual(len(self.generation.calls), 1)
        captured, digest, scope = self.generation.calls[0]
        self.assertEqual(captured, self.source.run)
        self.assertEqual(digest, self.body["record_hash"])
        self.assertEqual(scope["system_id"], "standalone")
        self.assertTrue(scope["project_id"].startswith("standalone-"))
        self.assertFalse(result["can_generate"])
        self.assertNotIn("physical_workflow", result)
        self.assertNotIn("workflow", result)
        self.assert_untouched()
        self.generation.jobs[-1].update(status="Completed", phase="Registered")
        self.generation.active = False
        self.generation.registration = {"software_qa_fixture": True}
        status, result = self.request()
        self.assertEqual(status, 200, result)
        self.assertTrue(result["registered"])
        self.assertTrue(result["can_generate"])
        self.assertEqual(result["latest_job"]["status"], "Completed")
        self.assertEqual(len(self.generation.calls), 1)
        self.assert_untouched()

    def test_post_rejects_extra_or_missing_request_arguments(self):
        for body in ({}, {"revision_id": self.body["revision_id"]},
                     {**self.body, "output": "results/arbitrary"},
                     {**self.body, "source_root": "results/foreign"},
                     {**self.body, "run_id": self.source.run["id"]}):
            with self.subTest(body=body):
                status, result = self.request("POST", body=body)
                self.assertEqual(status, 400, result)
                self.assertEqual(result["error"]["code"], "functional_map_request_invalid")
        self.assertFalse(self.generation.calls)
        self.assert_untouched()

    def test_revision_or_record_hash_change_is_rejected_without_start(self):
        for key, value in (("revision_id", "foreign-revision"), ("record_hash", "0" * 64)):
            with self.subTest(key=key):
                status, result = self.request("POST", body={**self.body, key: value})
                self.assertEqual(status, 409, result)
                self.assertEqual(result["error"]["code"], "functional_map_source_changed")
        self.assertFalse(self.generation.calls)
        self.assert_untouched()

    def test_stale_and_historical_selection_cannot_start(self):
        self.physical.freshness = "Stale"
        status, result = self.request()
        self.assertEqual(status, 200, result)
        self.assertFalse(result["can_generate"])
        self.assertIn("Current", result["blocked_reason"])
        status, result = self.request("POST", body=self.body)
        self.assertEqual(status, 409, result)
        self.assertEqual(result["error"]["code"], "functional_map_generation_blocked")
        self.physical.freshness = "Current"
        newer = copy.deepcopy(self.source.run)
        newer["id"] = "physical-workflow-" + "2" * 32
        newer["record_hash"] = object_hash({key: value for key, value in newer.items() if key != "record_hash"})
        self.physical._state["runs"].append(newer)
        status, result = self.request("POST", body=self.body)
        self.assertEqual(status, 409, result)
        self.assertEqual(result["error"]["code"], "functional_map_generation_blocked")
        self.physical._state["runs"].pop()
        self.assertFalse(self.generation.calls)
        self.assert_untouched()

    def test_unsupported_source_reports_reason_and_does_not_start(self):
        original = self.physical._state["runs"][0]
        changed = copy.deepcopy(original)
        changed["checks"]["source_bundle"].pop()
        changed["record_hash"] = object_hash({key: value for key, value in changed.items() if key != "record_hash"})
        self.physical._state["runs"][0] = changed
        status, result = self.request()
        self.assertEqual(status, 200, result)
        self.assertFalse(result["can_generate"])
        self.assertIn("source bundle no longer matches", result["blocked_reason"])
        status, result = self.request("POST", body={**self.body, "record_hash": changed["record_hash"]})
        self.assertEqual(status, 409, result)
        self.assertEqual(result["error"]["code"], "functional_map_generation_blocked")
        self.physical._state["runs"][0] = original
        self.assertFalse(self.generation.calls)
        self.assert_untouched()

    def test_global_workflow_lookalike_route_is_not_a_generation_endpoint(self):
        wrong = self.path.replace("/physical-workflow/", "/global-workflow/")
        for method in ("GET", "POST"):
            with self.subTest(method=method):
                status, result = self.request(method, wrong, self.body if method == "POST" else None)
                self.assertEqual(status, 404, result)
        self.assertFalse(self.generation.calls)
        self.assertFalse(self.generation.status_calls)
        self.assert_untouched()

    def test_active_generation_blocks_all_mutations_but_status_get_remains_available(self):
        self.generation.active = True
        for path in (self.path, "/api/save", "/api/llm/generation", "/api/generation/jobs",
                     "/api/workspace/open", "/api/workspace/create-project", "/api/review-policy"):
            with self.subTest(path=path):
                status, result = self.request("POST", path, self.body)
                self.assertEqual(status, 409, result)
                self.assertEqual(result["error"]["code"], "functional_map_generation_busy")
        status, result = self.request()
        self.assertEqual(status, 200, result)
        self.assertFalse(result["can_generate"])
        self.assertFalse(self.generation.calls)
        self.assert_untouched()

    def test_read_only_workspace_allows_status_but_rejects_generation(self):
        self.server.workspace = SessionWorkspaceDouble(read_only=True)
        headers = {"X-HuLLCirq-Session": "software-qa-session"}
        status, result = self.request(headers=headers)
        self.assertEqual(status, 200, result)
        self.assertFalse(result["can_generate"])
        self.assertIn("read-only", result["blocked_reason"])
        status, result = self.request("POST", body=self.body, headers=headers)
        self.assertEqual(status, 409, result)
        self.assertEqual(result["error"]["code"], "read_only_system")
        self.assertFalse(self.generation.calls)
        self.assert_untouched()

    def test_production_session_guard_and_origin_guard_precede_generation(self):
        self.server.workspace = SessionWorkspaceDouble()
        for method in ("GET", "POST"):
            status, result = self.request(method, body=self.body if method == "POST" else None,
                                          headers={"X-HuLLCirq-Session": "stale-session"})
            self.assertEqual(status, 409, result)
            self.assertEqual(result["error"]["code"], "workspace_session_changed")
        status, result = self.request("POST", body=self.body, headers={
            "X-HuLLCirq-Session": "software-qa-session", "Origin": "https://foreign.invalid"})
        self.assertEqual(status, 403, result)
        self.assertEqual(result["error"]["code"], "invalid_origin")
        self.assertFalse(self.generation.calls)
        self.assertFalse(self.generation.status_calls)
        self.assert_untouched()

    def test_missing_selected_run_cannot_borrow_another_runs_history(self):
        path = self.path.replace(self.source.run["id"], "physical-workflow-" + "f" * 32)
        for method in ("GET", "POST"):
            status, result = self.request(method, path, self.body if method == "POST" else None)
            self.assertEqual(status, 404, result)
            self.assertEqual(result["error"]["code"], "physical_run_not_found")
        self.assertFalse(self.generation.calls)
        self.assertFalse(self.generation.status_calls)
        self.assert_untouched()

    def test_generation_routes_release_physical_lock_before_cross_manager_checks(self):
        calls = []
        for name in ("postlayout_workflow", "lvs_workflow", "drc_workflow", "physical_workflow",
                     "global_workflow", "global_generation", "workflow", "generation", "repair_analysis", "generation_batches"):
            manager = getattr(self.server, name)
            original = manager.is_active

            def guarded(original=original, name=name):
                self.assertFalse(self.physical.lock._is_owned(),
                                 name + " must not acquire its lock under the physical manager lock")
                calls.append(name)
                return original()

            manager.is_active = guarded
        status, result = self.request()
        self.assertEqual(status, 200, result)
        self.assertTrue(result["can_generate"])
        self.assertEqual(set(calls), {"postlayout_workflow", "lvs_workflow", "drc_workflow", "physical_workflow",
                                     "global_workflow", "global_generation", "workflow", "generation", "repair_analysis", "generation_batches"})
        calls.clear()
        status, result = self.request("POST", body=self.body)
        self.assertEqual(status, 202, result)
        self.assertEqual(len(self.generation.calls), 1)
        self.assertTrue(calls)
        self.assert_untouched()

    def test_worker_alive_blocks_derived_generation_even_after_record_is_terminal(self):
        for name in ("generation", "workflow", "physical_workflow"):
            manager = getattr(self.server, name)
            missing = object()
            original = getattr(manager, "_worker", missing)
            manager._worker = SimpleNamespace(is_alive=lambda: True)
            try:
                with self.subTest(manager=name):
                    status, result = self.request()
                    self.assertEqual(status, 200, result)
                    self.assertFalse(result["can_generate"])
                    self.assertIn("active", result["blocked_reason"])
                    status, result = self.request("POST", body=self.body)
                    self.assertEqual(status, 409, result)
                    self.assertEqual(result["error"]["code"], "functional_map_generation_blocked")
            finally:
                if original is missing:
                    del manager._worker
                else:
                    manager._worker = original
        self.assertFalse(self.generation.calls)
        self.assert_untouched()


if __name__ == "__main__":
    unittest.main()

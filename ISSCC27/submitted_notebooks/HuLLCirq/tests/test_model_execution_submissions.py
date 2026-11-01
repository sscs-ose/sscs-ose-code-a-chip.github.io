"""Model-manager receipt integration; failed software providers only."""
from contextlib import contextmanager
import copy
import importlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT / "src"), str(PROJECT / "tests")]
import test_global_generation as global_fixtures
import test_generation_batches as batch_fixtures
import test_repair_analysis as analysis_fixtures
from hullcirq.domain import DomainError
from hullcirq.execution_submissions import run_submission, submission_view, validate_submissions
from hullcirq.store import _io_path
from hullcirq.global_generation import GlobalGenerationManager
from hullcirq.generation_batches import GenerationBatchManager
from hullcirq.repair_analysis import RepairAnalysisManager

CASES = ("global_generation", "generation_batches", "repair_analysis")


class ModelExecutionSubmissionTests(unittest.TestCase):
    def setUp(self):
        root = PROJECT / ".work" / "qa"
        root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="model-submission-", dir=root)
        self.directory = Path(self.temporary.name).resolve()
        self.assertEqual(self.directory.parent, root.resolve())
        self.addCleanup(self.cleanup_directory)
        self.providers = {}
        for target, options in [("tempfile.tempdir", {"new": str(self.directory)}),
                ("subprocess.Popen", {"side_effect": AssertionError("No native process in model receipt QA")}),
                ("socket.create_connection", {"side_effect": AssertionError("No live endpoint in model receipt QA")}),
                ("hullcirq.global_generation.check_global_rtl", {"side_effect": AssertionError("No global compiler")}),
                ("hullcirq.generation.check_rtl", {"side_effect": AssertionError("Failed answer cannot run checks")})]:
            started = patch(target, **options); started.start(); self.addCleanup(started.stop)
        for name in ("global_generation", "generation", "repair_analysis"):
            started = patch("hullcirq." + name + ".ChatCompletionsClient")
            provider = started.start(); self.addCleanup(started.stop)
            provider.return_value.generate.return_value = self.failed()
            self.providers[name] = provider

    def cleanup_directory(self):
        target = Path(self.temporary.name)
        self.assertFalse(target.is_symlink())
        self.assertTrue(target.resolve().is_relative_to((PROJECT / ".work" / "qa").resolve()))
        self.temporary.name = str(_io_path(target))
        self.temporary.cleanup()

    @staticmethod
    def failed():
        return {"execution_status": "Failed", "raw_content": "", "raw_reasoning": "",
                "finish_reason": "length", "error": {"code": "output_truncated", "message": "No real model."}, "events": []}

    @contextmanager
    def fixture(self, name):
        cls = {"global_generation": global_fixtures.GlobalSoftwareTests,
               "generation_batches": batch_fixtures.GenerationBatchTests,
               "repair_analysis": analysis_fixtures.RepairAnalysisTests}[name]
        fixture = cls("runTest")
        try:
            fixture.setUp()
            temp = Path(fixture.temp.name).resolve()
            self.assertTrue(temp.is_relative_to((PROJECT / ".work").resolve()))
            manager = fixture.manager
            if name == "global_generation":
                revision = fixture.store.envelope()["revision"]["id"]
                plan = manager.preview(revision)
                body = {"revision_id": revision, "context_id": plan["context_id"], "profile_revision_id": plan["profile_revision_id"]}
                route = "/api/global-generation/start"
            elif name == "generation_batches":
                plan = manager.preview(fixture.revision)
                body = {"plan_id": plan["plan_id"], "request_id": "software-model-request"}
                route = "/api/generation/batches/start"
            else:
                plan = manager.preview(fixture.run["id"])
                body = {"context_id": plan["context_id"], "request_id": "software-model-request"}
                route = "/api/repair-analysis/start"
            yield fixture, manager, body, route
        finally:
            if getattr(fixture, "manager", None) is not None:
                worker = fixture.manager._worker
                if worker is not None and worker.ident is None:
                    fixture.manager._worker = None
            fixture.tearDown()
            fixture.doCleanups()

    def submit(self, manager, body, route, key="software-model-nonce", preflight=None):
        return run_submission(manager, route, {**body, "submission_id": key},
            lambda ticket: manager.start(**body, _submission=ticket), preflight=preflight)

    def join(self, manager):
        manager._worker.join(8)
        self.assertFalse(manager._worker.is_alive())

    @staticmethod
    def durable(manager):
        p = _io_path(manager.path)
        return (p.read_bytes(), p.stat().st_mtime_ns) if p.exists() else (None, None)

    @staticmethod
    def records(manager):
        return manager._state.get("jobs", manager._state.get("batches", []))

    def reopen(self, fixture, name, store=None):
        store = fixture.store if store is None else store
        if name == "global_generation":
            return GlobalGenerationManager(store, fixture.sources.generation, fixture.sources.workflow, fixture.sources.specs, fixture.compiler)
        if name == "generation_batches":
            return GenerationBatchManager(store, fixture.generation, fixture.workflow)
        return RepairAnalysisManager(store, fixture.generation, fixture.workflow, fixture.batches)

    def test_all_three_replay_terminal_receipt_and_restart_without_a_second_worker(self):
        for name in CASES:
            with self.subTest(manager=name), self.fixture(name) as (fixture, manager, body, route):
                first = self.submit(manager, body, route)
                self.join(manager)
                record = copy.deepcopy(self.records(manager)[-1])
                self.assertEqual(record["submission_id"], "software-model-nonce")
                self.assertEqual(first["execution_submission"]["record_id"], record["id"])
                if name == "repair_analysis":
                    self.assertEqual(first["id"], record["id"], "Analysis retains its original raw-job return")
                    self.assertEqual(manager.envelope()[name]["jobs"][-1]["submission_id"], record["submission_id"])
                validate_submissions(manager._state)
                before = self.durable(manager)
                self.assertTrue(self.submit(manager, body, route)["execution_submission"]["replayed"])
                manager.close()
                loaded = self.reopen(fixture, name); self.addCleanup(loaded.close)
                self.assertEqual(self.durable(loaded), before)
                self.assertTrue(self.submit(loaded, body, route)["execution_submission"]["replayed"])
                self.assertIsNone(loaded._worker)
                self.assertEqual(self.records(loaded)[-1], record)
                self.assertEqual(self.durable(loaded), before)

    def test_all_payload_changes_conflict_and_legacy_records_remain_exact(self):
        for name in CASES:
            with self.subTest(manager=name), self.fixture(name) as (fixture, manager, body, route):
                manager.start(**body); self.join(manager)
                original = copy.deepcopy(self.records(manager)[0])
                self.assertNotIn("submission_id", original)
                if name == "repair_analysis":
                    self.assertNotIn("submission_id", manager.envelope()[name]["jobs"][0])
                next_body = {**body}
                if "request_id" in next_body:next_body["request_id"] = "software-model-request-next"
                if name == "generation_batches":
                    next_body["plan_id"] = manager.preview(fixture.revision)["plan_id"]
                self.submit(manager, next_body, route); self.join(manager)
                before = self.durable(manager)
                for field in next_body:
                    with self.subTest(field=field), self.assertRaises(DomainError) as error:
                        self.submit(manager, {**next_body, field: "different-frozen-input"}, route)
                    self.assertEqual((error.exception.code, error.exception.status), ("submission_conflict", 409))
                self.assertEqual(self.records(manager)[0], original)
                self.assertEqual(self.durable(manager), before)

    def test_batch_and_analysis_new_nonce_cannot_rebind_an_existing_request_id(self):
        for name in CASES[1:]:
            with self.subTest(manager=name), self.fixture(name) as (_fixture, manager, body, route):
                manager.start(**body); self.join(manager)
                original = copy.deepcopy(self.records(manager)[0])
                with self.assertRaises(DomainError) as error:
                    self.submit(manager, body, route)
                self.assertEqual(error.exception.status, 409)
                self.assertTrue(error.exception.execution_start_rejected_before_creation)
                self.assertEqual(self.records(manager), [original])

    def test_all_rejected_nonces_remain_terminal_and_restore_without_view_writes(self):
        for name in CASES:
            with self.subTest(manager=name), self.fixture(name) as (fixture, manager, body, route):
                def reject():raise DomainError("fixture_busy", "No fixture execution.", 409)
                with self.assertRaises(DomainError):self.submit(manager, body, route, preflight=reject)
                manager.close()
                loaded = self.reopen(fixture, name); self.addCleanup(loaded.close)
                before = self.durable(loaded)
                loaded.envelope(); submission_view(loaded)
                with self.assertRaises(DomainError) as error:self.submit(loaded, body, route)
                self.assertTrue(error.exception.execution_start_rejected_before_creation)
                self.assertEqual(self.durable(loaded), before)
                self.assertEqual(self.records(loaded), [])

    def test_all_postcommit_worker_start_errors_do_not_become_prestart_rejections(self):
        for name in CASES:
            with self.subTest(manager=name), self.fixture(name) as (_fixture, manager, body, route):
                with patch("threading.Thread.start", side_effect=DomainError("fixture_worker", "No fixture thread.", 409)):
                    with self.assertRaises(DomainError) as error:self.submit(manager, body, route)
                self.assertFalse(getattr(error.exception, "execution_start_rejected_before_creation", False))
                record = self.records(manager)[-1]
                before = self.durable(manager)
                replay = self.submit(manager, body, route)["execution_submission"]
                self.assertTrue(replay["replayed"]); self.assertEqual(replay["record_id"], record["id"])
                self.assertEqual(self.durable(manager), before)

    def test_real_global_stream_chunks_survive_a_busy_competing_submission(self):
        with self.fixture("global_generation") as (_fixture, manager, body, route):
            entered, release = threading.Event(), threading.Event()
            def generate(_messages, _parameters, _cancel, event):
                event({"type": "delta", "content": "pending-software-fragment"})
                entered.set()
                if not release.wait(3):raise AssertionError("Fixture release missing")
                return {**self.failed(), "raw_content": "pending-software-fragment"}
            self.providers["global_generation"].return_value.generate.side_effect = generate
            try:
                self.submit(manager, body, route)
                self.assertTrue(entered.wait(2))
                current = copy.deepcopy(manager._state["jobs"][0])
                self.assertNotEqual(current["raw_content"], manager._committed["jobs"][0]["raw_content"])
                def busy():raise DomainError("global_generation_busy", "Software busy.", 409)
                with self.assertRaises(DomainError):self.submit(manager, body, route, key="competing-software-nonce", preflight=busy)
                for field in ("raw_content", "raw_reasoning", "events"):
                    self.assertEqual(manager._state["jobs"][0][field], current[field])
                    self.assertEqual(manager._committed["jobs"][0][field], current[field])
            finally:
                release.set(); self.join(manager)

    def test_all_failed_saves_keep_committed_snapshot_and_allow_explicit_same_nonce_retry(self):
        for name in CASES:
            with self.subTest(manager=name), self.fixture(name) as (_fixture, manager, body, route):
                before, committed = self.durable(manager), copy.deepcopy(manager._committed)
                module = importlib.import_module("hullcirq." + name)
                with patch.object(module, "_replace_with_windows_retry", side_effect=OSError("Software disk failure")):
                    with self.assertRaises(OSError):self.submit(manager, body, route)
                self.assertEqual(self.durable(manager), before)
                self.assertEqual(manager._committed, committed)
                self.assertEqual(submission_view(manager), {})
                self.assertEqual(self.records(manager), [])
                self.submit(manager, body, route); self.join(manager)
                self.assertEqual(len(self.records(manager)), 1)

    def test_all_deep_empty_histories_commit_and_reopen_without_default_view_writes(self):
        for name in CASES:
            with self.subTest(manager=name), self.fixture(name) as (fixture, _manager, _body, _route):
                deep = self.directory
                while len(str(deep)) < 350:deep = deep / ("deep_model_" + "x" * 28)
                deep = deep / name
                _io_path(deep).mkdir(parents=True)
                store = copy.copy(fixture.store); store.state_path = deep / "software-state.json"
                cls = {"global_generation": GlobalGenerationManager, "generation_batches": GenerationBatchManager,
                       "repair_analysis": RepairAnalysisManager}[name]
                scope = patch.object(cls, "observe_design", return_value=(None, None, None)) if name == "global_generation" else patch.object(cls, "is_active", return_value=False)
                with scope:
                    first = self.reopen(fixture, name, store); self.addCleanup(first.close)
                    self.assertIsInstance(first._committed, dict)
                    self.assertFalse(_io_path(first.path).exists())
                    first.envelope(); submission_view(first)
                    self.assertFalse(_io_path(first.path).exists(), "An empty view cannot create a history file")
                    first._persist()
                    before = self.durable(first)
                    loaded = self.reopen(fixture, name, store); self.addCleanup(loaded.close)
                    submission_view(loaded)
                    self.assertEqual(self.durable(loaded), before)
                    self.assertEqual(loaded._state, first._state)
                    self.assertNotIn("execution_submissions", json.loads(before[0]))
                    self.assertFalse(str(loaded.path).startswith("\\\\?\\"))


if __name__ == "__main__":unittest.main()

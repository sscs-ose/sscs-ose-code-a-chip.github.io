"""S11-S14 receipt integration using explicit software adapters only.

All upstream model/synthesis/simulation and native results are existing marked
software fixtures. These checks prove request bookkeeping, never circuit proof.
"""
from __future__ import annotations

from contextlib import contextmanager
import copy
import importlib
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

import test_physical_workflow as physical_fixtures
import test_drc_workflow as drc_fixtures
import test_lvs_workflow as lvs_fixtures
import test_postlayout_workflow as postlayout_fixtures
from hullcirq.domain import DomainError
from hullcirq.execution_submissions import PROTOCOL_VERSION, run_submission, submission_view, validate_submissions
from hullcirq.verification import object_hash
from hullcirq.store import ProjectStore, _io_path


CASES = (
    ("physical_workflow", "layout", physical_fixtures.PhysicalWorkflowTests),
    ("drc_workflow", "drc", drc_fixtures.DrcWorkflowTests),
    ("lvs_workflow", "lvs", lvs_fixtures.LvsWorkflowTests),
    ("postlayout_workflow", "post_layout_verification", postlayout_fixtures.PostLayoutWorkflowTests),
)


class NativeExecutionSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.qa_root = PROJECT / ".work" / "qa"
        self.qa_root.mkdir(parents=True, exist_ok=True)
        self.assertTrue(self.qa_root.resolve().is_relative_to(PROJECT.resolve()))
        self.temporary = tempfile.TemporaryDirectory(prefix="native-submission-", dir=self.qa_root)
        self.directory = Path(self.temporary.name).resolve()
        self.assertEqual(self.directory.parent, self.qa_root.resolve())
        self.addCleanup(self.cleanup_directory)
        for target, options in (
            ("tempfile.tempdir", {"new": str(self.directory)}),
            ("subprocess.Popen", {"side_effect": AssertionError("No native subprocess in receipt QA")}),
            ("socket.create_connection", {"side_effect": AssertionError("No network in receipt QA")}),
        ):
            patcher = patch(target, **options)
            patcher.start()
            self.addCleanup(patcher.stop)

    def cleanup_directory(self):
        target = Path(self.temporary.name)
        self.assertFalse(target.is_symlink())
        self.assertEqual(target.resolve().parent, self.qa_root.resolve())
        self.assertTrue(target.resolve().is_relative_to(PROJECT.resolve()))
        # Extended I/O spelling is confined to cleanup of this checked fixture.
        self.temporary.name = str(_io_path(target))
        self.temporary.cleanup()

    @contextmanager
    def fixture(self, case):
        name, stage, cls = case
        fixture = cls("runTest")
        try:
            fixture.setUp()
            manager = fixture.manager
            body = {"stage_id": stage}
            if name == "physical_workflow":
                body.update(global_job_id=fixture.base.job["id"], synthesis_run_id=fixture.synthesis["id"],
                            netlist_run_id=fixture.simulation["id"], revision_id=fixture.base.job["revision_id"])
            else:
                body.update(layout_run_id=fixture.layout["id"], revision_id=fixture.layout["revision_id"])
                if name in ("lvs_workflow", "postlayout_workflow"):
                    body["drc_run_id"] = fixture.drc_run["id"]
                if name == "postlayout_workflow":
                    body["lvs_run_id"] = fixture.lvs_run["id"]
            yield fixture, manager, body, "/api/" + name.replace("_", "-") + "/start"
        finally:
            fixture.doCleanups()

    def submit(self, manager, route, body, *, key="native-fixture-001", preflight=None):
        wire = {**body, "submission_id": key}
        return run_submission(manager, route, wire,
            lambda ticket: manager.start(**body, _submission=ticket), preflight=preflight)

    def join(self, manager):
        worker = manager._worker
        self.assertIsNotNone(worker)
        worker.join(timeout=10)
        self.assertFalse(worker.is_alive())

    @staticmethod
    def durable(manager):
        # Fresh managers deliberately need no history file until an action.
        if not manager.path.exists():
            return None, None
        return manager.path.read_bytes(), manager.path.stat().st_mtime_ns

    @staticmethod
    def canonical(value):
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()

    def test_each_manager_stamps_before_hash_and_replays_after_terminal_restart(self):
        for case in CASES:
            with self.subTest(manager=case[0]), self.fixture(case) as (fixture, manager, body, route):
                runner = Mock(wraps=manager._runner)
                manager._runner = runner
                first = self.submit(manager, route, body)["execution_submission"]
                self.join(manager)
                run = manager._state["runs"][-1]
                self.assertEqual(first, {"version": PROTOCOL_VERSION, "submission_id": "native-fixture-001",
                    "record_id": run["id"], "replayed": False, "route": route})
                self.assertEqual(run["submission_id"], "native-fixture-001")
                self.assertEqual(run["record_hash"], object_hash({k: v for k, v in run.items() if k != "record_hash"}))
                validate_submissions(manager._state)
                before, original = self.durable(manager), self.canonical(run)
                replay = self.submit(manager, route, body)["execution_submission"]
                self.assertTrue(replay["replayed"])
                self.assertEqual(replay["record_id"], run["id"])
                self.assertEqual(runner.call_count, 1)
                self.assertEqual(self.durable(manager), before)
                manager.close()
                reopened = fixture.new_manager()
                fixture.addCleanup(reopened.close)
                self.assertEqual(self.durable(reopened), before)
                repeated = self.submit(reopened, route, body)["execution_submission"]
                self.assertEqual(repeated["record_id"], run["id"])
                self.assertTrue(repeated["replayed"])
                self.assertIsNone(reopened._worker)
                self.assertEqual(self.canonical(reopened._state["runs"][-1]), original)
                self.assertEqual(self.durable(reopened), before)

    def test_each_changed_frozen_body_field_or_route_conflicts_without_another_run(self):
        for case in CASES:
            with self.subTest(manager=case[0]), self.fixture(case) as (_fixture, manager, body, route):
                self.submit(manager, route, body)
                self.join(manager)
                before = self.durable(manager)
                for field in body:
                    with self.subTest(field=field):
                        changed = {**body, field: "different-frozen-value"}
                        with self.assertRaises(DomainError) as error:
                            self.submit(manager, route, changed)
                        self.assertEqual((error.exception.code, error.exception.status), ("submission_conflict", 409))
                        self.assertEqual(self.durable(manager), before)
                with self.assertRaises(DomainError) as error:
                    self.submit(manager, route + "-different", body)
                self.assertEqual(error.exception.code, "submission_conflict")
                self.assertEqual(len(manager._state["runs"]), 1)

    def test_each_active_request_has_one_worker_when_same_nonce_is_submitted_again(self):
        for case in CASES:
            with self.subTest(manager=case[0]), self.fixture(case) as (_fixture, manager, body, route):
                entered, release = threading.Event(), threading.Event()
                runner = manager._runner
                calls = []
                def slow(*args, **kwargs):
                    calls.append("software fixture only")
                    entered.set()
                    if not release.wait(3):
                        raise AssertionError("Fixture was not released")
                    return runner(*args, **kwargs)
                manager._runner = slow
                try:
                    first = self.submit(manager, route, body)["execution_submission"]
                    self.assertTrue(entered.wait(2))
                    second = self.submit(manager, route, body)["execution_submission"]
                    self.assertTrue(second["replayed"])
                    self.assertEqual(first["record_id"], second["record_id"])
                    self.assertEqual(len(manager._state["runs"]), 1)
                finally:
                    release.set()
                    self.join(manager)
                self.assertEqual(len(calls), 1)

    def test_each_rejection_is_durable_terminal_and_does_not_run_adapter(self):
        for case in CASES:
            with self.subTest(manager=case[0]), self.fixture(case) as (fixture, manager, body, route):
                runner = Mock(wraps=manager._runner)
                manager._runner = runner
                gate = Mock(side_effect=DomainError("fixture_gate", "Explicit software rejection.", 409))
                with self.assertRaises(DomainError) as first:
                    self.submit(manager, route, body, preflight=gate)
                self.assertTrue(first.exception.execution_start_rejected_before_creation)
                self.assertEqual(first.exception.submission_id, "native-fixture-001")
                self.assertEqual(manager._state["runs"], [])
                runner.assert_not_called()
                manager.close()
                reopened = fixture.new_manager()
                fixture.addCleanup(reopened.close)
                before = self.durable(reopened)
                allowed = Mock()
                with self.assertRaises(DomainError) as replay:
                    self.submit(reopened, route, body, preflight=allowed)
                self.assertEqual(replay.exception.code, first.exception.code)
                self.assertTrue(replay.exception.execution_start_rejected_before_creation)
                allowed.assert_not_called()
                self.assertEqual(self.durable(reopened), before)

    def test_each_failed_atomic_save_rolls_back_receipt_and_run_then_allows_same_nonce(self):
        for case in CASES:
            with self.subTest(manager=case[0]), self.fixture(case) as (_fixture, manager, body, route):
                before = self.durable(manager)
                runner = Mock(wraps=manager._runner)
                manager._runner = runner
                module = importlib.import_module("hullcirq." + case[0])
                with patch.object(module, "_replace_with_windows_retry", side_effect=OSError("Isolated fixture disk failure")):
                    with self.assertRaises(OSError) as error:
                        self.submit(manager, route, body)
                self.assertFalse(getattr(error.exception, "execution_start_rejected_before_creation", False))
                self.assertEqual(self.durable(manager), before)
                self.assertEqual(manager._state["runs"], [])
                self.assertEqual(submission_view(manager), {})
                runner.assert_not_called()
                self.submit(manager, route, body)
                self.join(manager)
                self.assertEqual(runner.call_count, 1)
                self.assertEqual(len(manager._state["runs"]), 1)

    def test_each_worker_start_failure_after_commit_is_never_proven_prestart_rejection(self):
        for case in CASES:
            with self.subTest(manager=case[0]), self.fixture(case) as (fixture, manager, body, route):
                with patch("threading.Thread.start", side_effect=DomainError("fixture_worker", "No fixture worker.", 409)):
                    with self.assertRaises(DomainError) as error:
                        self.submit(manager, route, body)
                self.assertFalse(getattr(error.exception, "execution_start_rejected_before_creation", False))
                original_id = manager._state["runs"][-1]["id"]
                self.assertEqual(submission_view(manager)["native-fixture-001"]["record_id"], original_id)
                before = self.durable(manager)
                with patch("threading.Thread.start", side_effect=AssertionError("Replay cannot create another worker")):
                    replay = self.submit(manager, route, body)["execution_submission"]
                self.assertEqual(replay["record_id"], original_id)
                self.assertTrue(replay["replayed"])
                self.assertEqual(self.durable(manager), before)
                manager.close()
                reopened = fixture.new_manager()
                fixture.addCleanup(reopened.close)
                self.assertEqual(reopened._state["runs"][-1]["execution_status"], "Interrupted")
                replay = self.submit(reopened, route, body)["execution_submission"]
                self.assertEqual(replay["record_id"], original_id)
                self.assertTrue(replay["replayed"])
                self.assertIsNone(reopened._worker)

    def test_each_legacy_reopen_view_has_no_ledger_write_and_old_record_hash_is_preserved(self):
        for case in CASES:
            with self.subTest(manager=case[0]), self.fixture(case) as (fixture, manager, body, route):
                manager.start(**body)
                self.join(manager)
                original = self.canonical(manager._state["runs"][0])
                self.assertNotIn("submission_id", manager._state["runs"][0])
                self.assertNotIn("execution_submissions", manager._state)
                before = self.durable(manager)
                manager.close()
                reopened = fixture.new_manager()
                fixture.addCleanup(reopened.close)
                envelope = reopened.envelope()[case[0]]
                self.assertEqual(envelope["submission_protocol_version"], PROTOCOL_VERSION)
                self.assertEqual(envelope["execution_submissions"], {})
                self.assertEqual(submission_view(reopened), {})
                self.assertEqual(self.durable(reopened), before)
                self.assertNotIn("execution_submissions", json.loads(reopened.path.read_text(encoding="utf-8")))
                self.submit(reopened, route, body)
                self.join(reopened)
                self.assertEqual(self.canonical(reopened._state["runs"][0]), original)

    def test_each_forged_nonce_record_link_fails_restore_without_rewriting_evidence(self):
        for case in CASES:
            with self.subTest(manager=case[0]), self.fixture(case) as (fixture, manager, body, route):
                self.submit(manager, route, body)
                self.join(manager)
                manager.close()
                state = json.loads(manager.path.read_text(encoding="utf-8"))
                state["execution_submissions"]["native-fixture-001"]["record_id"] = "missing-record"
                manager.path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                before = self.durable(manager)
                with self.assertRaises(DomainError):
                    fixture.new_manager()
                self.assertEqual(self.durable(manager), before)

    def test_keyed_s11_revalidation_has_new_unkeyed_identity_and_preserves_original_receipt(self):
        with self.fixture(CASES[0]) as (fixture, _manager, body, route):
            fixture.prepare_saved_actual_double()
            manager = fixture.manager
            first = self.submit(manager, route, body)["execution_submission"]
            self.join(manager)
            original = copy.deepcopy(manager._state["runs"][-1])
            receipt = submission_view(manager)
            self.assertEqual(original["submission_id"], "native-fixture-001")
            manager.revalidate(first["record_id"])
            self.join(manager)
            revalidated = manager._state["runs"][-1]
            self.assertNotEqual(revalidated["id"], original["id"])
            self.assertNotIn("submission_id", revalidated)
            self.assertEqual(revalidated["prior_run_id"], original["id"])
            self.assertEqual(revalidated["prior_record_sha256"], object_hash(original))
            self.assertEqual(submission_view(manager), receipt)
            self.assertEqual(manager._state["runs"][-2], original)
            self.assertEqual(fixture.calls["saved_recheck_double"], 1)
            validate_submissions(manager._state)
            manager._validate_saved()

    def test_each_deep_existing_store_is_loaded_and_explicit_write_reopens_without_view_writes(self):
        deep = self.directory
        while len(str(deep)) < 350:
            deep = deep / ("deep_fixture_" + "x" * 28)
        _io_path(deep).mkdir(parents=True)
        store = ProjectStore(deep / "project")
        project_before = _io_path(store.state_path).read_bytes(), _io_path(store.state_path).stat().st_mtime_ns
        upstream = SimpleNamespace(lock=threading.RLock(), _state={"jobs": [], "runs": []})
        physical = SimpleNamespace(lock=threading.RLock(), global_generation=upstream, global_workflow=upstream)
        drc = SimpleNamespace(lock=threading.RLock(), physical_workflow=physical)
        lvs = SimpleNamespace(lock=threading.RLock(), physical_workflow=physical, drc_workflow=drc)
        for case in CASES:
            with self.subTest(manager=case[0]):
                module = importlib.import_module("hullcirq." + case[0])
                class_name = {"physical_workflow": "PhysicalWorkflowManager", "drc_workflow": "DrcWorkflowManager",
                              "lvs_workflow": "LvsWorkflowManager", "postlayout_workflow": "PostLayoutWorkflowManager"}[case[0]]
                cls = getattr(module, class_name)
                arguments = {"physical_workflow": (store, upstream, upstream),
                             "drc_workflow": (store, physical), "lvs_workflow": (store, drc),
                             "postlayout_workflow": (store, lvs)}[case[0]]
                # No source or adapter is invented: this is an empty native
                # history I/O test. Existing full-chain fixtures cover sources.
                with patch.object(cls, "observe_design", return_value=(None, None, None)):
                    first = cls(*arguments)
                    self.addCleanup(first.close)
                    self.assertGreater(len(str(first.path)), 260)
                    self.assertFalse(str(first.path).startswith("\\\\?\\"))
                    first._persist()
                    initial = _io_path(first.path).read_bytes(), _io_path(first.path).stat().st_mtime_ns
                    reopened = cls(*arguments)
                    self.addCleanup(reopened.close)
                    self.assertEqual((_io_path(first.path).read_bytes(), _io_path(first.path).stat().st_mtime_ns), initial)
                    def reject():
                        raise DomainError("deep_fixture_rejection", "Explicit software I/O action.", 409)
                    with self.assertRaises(DomainError):
                        run_submission(reopened, "/api/" + case[0] + "/start",
                            {"submission_id": "deep-storage-fixture"}, Mock(), preflight=reject)
                    written = _io_path(first.path).read_bytes(), _io_path(first.path).stat().st_mtime_ns
                    self.assertNotEqual(written[0], initial[0])
                    last = cls(*arguments)
                    self.addCleanup(last.close)
                    self.assertEqual(submission_view(last)["deep-storage-fixture"]["rejection"]["code"], "deep_fixture_rejection")
                    self.assertEqual((_io_path(first.path).read_bytes(), _io_path(first.path).stat().st_mtime_ns), written)
                    self.assertEqual(last.path, first.path)
                    self.assertNotIn("\\\\?\\", written[0].decode("utf-8"))
        self.assertEqual((_io_path(store.state_path).read_bytes(), _io_path(store.state_path).stat().st_mtime_ns), project_before)

    def test_deep_profile_writer_preserves_bytes_fsync_atomicity_and_failure_cleanup(self):
        module = importlib.import_module("hullcirq.postlayout_workflow")
        deep = self.directory
        while len(str(deep)) < 350:
            deep = deep / ("profile_fixture_" + "x" * 24)
        _io_path(deep).mkdir(parents=True)
        manager = module.PostLayoutWorkflowManager.__new__(module.PostLayoutWorkflowManager)
        manager._configuration_path = deep / "software-profile.json"
        manager._profile_directory = deep.resolve()
        configuration = {"version": "SOFTWARE_QA_ONLY", "purpose": "I/O fixture, not an execution profile"}
        with patch.object(module.os, "fsync", wraps=module.os.fsync) as synced, \
                patch.object(module, "_replace_with_windows_retry", wraps=module._replace_with_windows_retry) as replaced:
            manager._write_profile(configuration)
        self.assertEqual(synced.call_count, 1)
        self.assertEqual(replaced.call_count, 1)
        path = manager._configuration_path
        self.assertFalse(str(path).startswith("\\\\?\\"))
        expected = (json.dumps(configuration, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
        self.assertEqual(_io_path(path).read_bytes(), expected)
        before = _io_path(path).read_bytes(), _io_path(path).stat().st_mtime_ns
        for failed_operation in ("replace", "fsync"):
            with self.subTest(failed_operation=failed_operation):
                target = "_replace_with_windows_retry" if failed_operation == "replace" else "fsync"
                owner = module if failed_operation == "replace" else module.os
                with patch.object(owner, target, side_effect=OSError("Isolated profile write failure")):
                    with self.assertRaises(OSError):
                        manager._write_profile({**configuration, "new_value": "Must not replace original"})
                self.assertEqual((_io_path(path).read_bytes(), _io_path(path).stat().st_mtime_ns), before)
                self.assertFalse(any(p.name.startswith(".postlayout-profile-") for p in _io_path(deep).iterdir()))


if __name__ == "__main__":
    unittest.main()

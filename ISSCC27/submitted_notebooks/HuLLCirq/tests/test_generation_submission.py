"""Durable S04 submission identities; software fixtures, never model evidence.

Every provider is a patched object returning an explicitly failed/truncated
answer. No HTTP server, native compiler, model, GUI or real project is used.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from hullcirq.domain import DomainError, IMPLEMENTED_STAGES
from hullcirq.generation import GenerationManager
from hullcirq.store import ProjectStore
from hullcirq.verification import object_hash


class GenerationSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.qa_root = PROJECT / ".work" / "qa"
        self.qa_root.mkdir(parents=True, exist_ok=True)
        self.assertTrue(self.qa_root.resolve().is_relative_to(PROJECT.resolve()))
        self.temporary = tempfile.TemporaryDirectory(
            prefix="generation-submission-", dir=self.qa_root)
        self.directory = Path(self.temporary.name).resolve()
        self.assertEqual(self.directory.parent, self.qa_root.resolve())
        self.addCleanup(self._cleanup_temporary)
        provider_patch = patch("hullcirq.generation.ChatCompletionsClient")
        self.provider = provider_patch.start()
        self.addCleanup(provider_patch.stop)
        self.provider.return_value.generate.return_value = self.failed_answer()
        checks_patch = patch("hullcirq.generation.check_rtl",
                             side_effect=AssertionError("No RTL tool in submission QA"))
        self.checks = checks_patch.start()
        self.addCleanup(checks_patch.stop)
        behavior_patch = patch("hullcirq.generation.verify_behavior",
                               side_effect=AssertionError("No simulation in submission QA"))
        self.behavior = behavior_patch.start()
        self.addCleanup(behavior_patch.stop)
        self.store = ProjectStore(self.directory / "project", PROJECT / "examples/m1_two_nodes.json")
        self.revision = self.store.envelope()["revision"]["id"]
        for stage in IMPLEMENTED_STAGES:
            run = self.store.validate(stage, self.revision)["runs"][-1]
            self.store.review(run["id"], "accepted", "Reviewed isolated submission fixture.")
        self.manager = self._manager(self.store)
        self.manager.save_profile({
            "id": "submission-fixture", "name": "No inference software fixture",
            "execution_location": "Local", "base_url": "http://localhost:9/v1",
            "model": "no-model-called", "context_window": 16384,
        })
        prepared = self.manager.preview("node-producer", self.revision)
        self.arguments = {
            "node_id": "node-producer", "revision_id": self.revision,
            "context_id": prepared["context_id"],
            "profile_revision_id": prepared["profile_revision_id"],
            "operation": "generate", "base_job_id": None,
            "instruction": "", "retry_of_job_id": None,
        }
        self.key = "submission-fixture-001"

    @staticmethod
    def failed_answer():
        return {
            "execution_status": "Failed", "raw_content": "",
            "raw_reasoning": "Explicitly truncated software response.",
            "finish_reason": "length", "usage": {"completion_tokens": 1},
            "error": {"code": "output_truncated", "message": "Software fixture only."},
        }

    def _cleanup_temporary(self):
        # Recheck the final absolute cleanup target; never recurse outside QA.
        target = Path(self.temporary.name)
        self.assertFalse(target.is_symlink())
        self.assertEqual(target.resolve().parent, self.qa_root.resolve())
        self.assertTrue(target.resolve().is_relative_to(PROJECT.resolve()))
        self.temporary.cleanup()

    def _manager(self, store):
        manager = GenerationManager(store)
        self.addCleanup(self._close_manager, manager)
        return manager

    @staticmethod
    def _close_manager(manager):
        manager.close()
        worker = manager._worker
        if worker is not None and worker.ident is not None:
            worker.join(timeout=5)
            if worker.is_alive():
                raise AssertionError("Isolated fixture worker did not terminate")

    def join(self):
        worker = self.manager._worker
        self.assertIsNotNone(worker)
        worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.checks.assert_not_called()
        self.behavior.assert_not_called()

    def start(self, key=None, **overrides):
        arguments = {**self.arguments, **overrides}
        return self.manager.start(**arguments, submission_id=self.key if key is None else key)

    def completed_start(self, key=None):
        envelope = self.start(key)
        self.join()
        receipt = envelope["generation_submission"]
        job = self.manager.job(receipt["job_id"])
        self.assertEqual(job["execution_status"], "Failed")
        self.assertEqual(job["error"]["code"], "output_truncated")
        self.assertEqual(job["validation_status"], "Not Checked")
        self.assertEqual(job["review_status"], "Awaiting Review")
        self.assertIsNone(job["rtl"])
        return envelope, job

    @staticmethod
    def canonical(value):
        return json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":")).encode("utf-8")

    def durable(self):
        return self.manager.path.read_bytes(), self.manager.path.stat().st_mtime_ns

    def assert_conflict(self, action):
        with self.assertRaises(DomainError) as caught:
            action()
        self.assertEqual(caught.exception.code, "submission_conflict")
        self.assertEqual(caught.exception.status, 409)
        self.assertFalse(getattr(caught.exception, "generation_start_rejected_before_creation", False))

    def test_terminal_replay_has_exact_receipt_and_never_creates_another_worker(self):
        first, job = self.completed_start()
        self.assertEqual(first["generation_submission"], {
            "version": "node-submission-v1", "submission_id": self.key,
            "job_id": job["id"], "replayed": False,
        })
        self.assertEqual(job["submission_id"], self.key)
        before, worker = self.durable(), self.manager._worker
        for _ in range(3):
            replay = self.start()["generation_submission"]
            self.assertEqual(replay, {**first["generation_submission"], "replayed": True})
        self.assertIs(self.manager._worker, worker)
        self.assertEqual(len(self.manager._state["jobs"]), 1)
        self.assertEqual(self.durable(), before)
        self.assertEqual(self.provider.return_value.generate.call_count, 1)

    def test_each_frozen_field_conflict_leaves_history_and_receipt_unchanged(self):
        self.completed_start()
        before = self.durable()
        changes = {
            "node_id": "another-node", "revision_id": "another-revision",
            "context_id": "another-context", "profile_revision_id": "another-profile",
            "operation": "repair", "base_job_id": "another-job",
            "instruction": "Different frozen instruction.", "retry_of_job_id": "another-parent",
        }
        for field, value in changes.items():
            with self.subTest(field=field):
                self.assert_conflict(lambda: self.start(**{field: value}))
                self.assertEqual(self.durable(), before)
        self.assertEqual(len(self.manager._state["jobs"]), 1)
        self.assertEqual(self.provider.return_value.generate.call_count, 1)

    def test_replay_survives_restart_and_changed_current_profile_and_source(self):
        _, job = self.completed_start()
        old_job = self.canonical(self.manager._state["jobs"][0])
        profile_state = self.manager.envelope()["llm"]
        changed_profile = copy.deepcopy(profile_state["profile"])
        changed_profile["max_output_tokens"] += 1
        self.manager.save_profile(changed_profile, profile_state["profile_revision_id"])
        current = self.store.envelope()
        changed = copy.deepcopy(current["design"])
        changed["nodes"][0]["behavior"] += " Changed current specification."
        self.store.save(changed, current["revision"]["id"])
        self.manager.close()
        self.manager = self._manager(ProjectStore(self.directory / "project"))
        before = self.durable()
        replay = self.start()["generation_submission"]
        self.assertEqual(replay["job_id"], job["id"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(self.canonical(self.manager._state["jobs"][0]), old_job)
        self.assertEqual(self.durable(), before)
        self.assertEqual(self.provider.return_value.generate.call_count, 1)

    def test_active_duplicate_and_concurrent_same_nonce_have_one_provider_request(self):
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)

        def blocked(*_args):
            entered.set()
            if not release.wait(5):
                raise AssertionError("Fixture release timed out")
            return self.failed_answer()

        self.provider.return_value.generate.side_effect = blocked
        barrier = threading.Barrier(6)
        results, errors = [], []

        def submit():
            try:
                barrier.wait(timeout=5)
                results.append(self.start()["generation_submission"])
            except Exception as error:
                errors.append(error)

        callers = [threading.Thread(target=submit, daemon=True) for _ in range(6)]
        try:
            for caller in callers:
                caller.start()
            for caller in callers:
                caller.join(timeout=5)
                self.assertFalse(caller.is_alive())
            self.assertEqual(errors, [])
            self.assertTrue(entered.wait(2))
            self.assertEqual(len(results), 6)
            self.assertEqual(len({value["job_id"] for value in results}), 1)
            self.assertEqual(sum(not value["replayed"] for value in results), 1)
            self.assertTrue(self.start()["generation_submission"]["replayed"])
            self.assertEqual(len(self.manager._state["jobs"]), 1)
            self.assertEqual(self.provider.return_value.generate.call_count, 1)
        finally:
            release.set()
            for caller in callers:
                caller.join(timeout=5)
            self.join()

    def test_preflight_releases_generation_lock_before_requesting_upstream_lock(self):
        upstream = threading.RLock()
        held, preflight_entered, generation_acquired = (threading.Event() for _ in range(3))
        errors = []

        def upstream_reader():
            with upstream:
                held.set()
                if not preflight_entered.wait(2):
                    errors.append("Preflight was not reached")
                    return
                # Model workflow/batch readers: upstream lock -> generation.
                if self.manager.lock.acquire(timeout=1):
                    generation_acquired.set()
                    self.manager.lock.release()
                else:
                    errors.append("Reverse lock order blocked generation reader")

        def preflight():
            preflight_entered.set()
            if not upstream.acquire(timeout=2):
                raise AssertionError("Preflight retained generation while waiting upstream")
            upstream.release()

        reader = threading.Thread(target=upstream_reader, daemon=True)
        reader.start()
        self.assertTrue(held.wait(2))
        try:
            self.start(_preflight=preflight)
            self.join()
        finally:
            reader.join(timeout=3)
        self.assertFalse(reader.is_alive())
        self.assertEqual(errors, [])
        self.assertTrue(generation_acquired.is_set())
        self.assertEqual(self.provider.return_value.generate.call_count, 1)

    def test_preflight_races_recheck_a_started_or_rejected_receipt_before_commit(self):
        for winning_outcome in ("started", "rejected"):
            with self.subTest(winning_outcome=winning_outcome):
                key = "racing-" + winning_outcome
                entered, release = threading.Event(), threading.Event()
                returned, errors = [], []

                def delayed_preflight():
                    entered.set()
                    if not release.wait(3):
                        raise AssertionError("Fixture preflight was not released")
                    if winning_outcome == "started":
                        raise DomainError("late_rejection", "Late fixture gate rejected.", 409)

                def delayed_request():
                    try:
                        returned.append(self.start(key, _preflight=delayed_preflight))
                    except Exception as error:
                        errors.append(error)

                caller = threading.Thread(target=delayed_request, daemon=True)
                caller.start()
                try:
                    self.assertTrue(entered.wait(2))
                    if winning_outcome == "started":
                        winner = self.start(key)["generation_submission"]
                        self.join()
                    else:
                        def reject():
                            raise DomainError("first_rejection", "First fixture gate rejected.", 409)
                        with self.assertRaises(DomainError):
                            self.start(key, _preflight=reject)
                    before = self.durable()
                finally:
                    release.set()
                    caller.join(timeout=4)
                self.assertFalse(caller.is_alive())
                self.assertEqual(self.durable(), before)
                if winning_outcome == "started":
                    self.assertEqual(errors, [])
                    self.assertEqual(returned[0]["generation_submission"]["job_id"], winner["job_id"])
                    self.assertTrue(returned[0]["generation_submission"]["replayed"])
                else:
                    self.assertEqual(returned, [])
                    self.assertEqual(len(errors), 1)
                    self.assertIsInstance(errors[0], DomainError)
                    self.assertEqual(errors[0].code, "first_rejection")
                    self.assertTrue(errors[0].generation_start_rejected_before_creation)
                self.assertEqual(self.manager.submission_receipt(key)["status"], winning_outcome)
        self.assertEqual(len(self.manager._state["jobs"]), 1)
        self.assertEqual(self.provider.return_value.generate.call_count, 1)

    def test_receipt_lookup_is_readonly_for_unknown_and_started_keys(self):
        before = self.durable()
        missing = self.manager.submission_receipt("unknown-key")
        self.assertEqual(missing["status"], "not_found")
        self.assertEqual(missing["submission_id"], "unknown-key")
        self.assertEqual(self.durable(), before)
        self.provider.assert_not_called()
        _, job = self.completed_start()
        before = self.durable()
        receipt = self.manager.submission_receipt(self.key)
        self.assertEqual(receipt["version"], "node-submission-v1")
        self.assertEqual(receipt["status"], "started")
        self.assertEqual(receipt["job_id"], job["id"])
        self.assertEqual(receipt["request"], self.arguments)
        self.assertEqual(receipt["binding_hash"], object_hash(receipt["request"]))
        self.assertEqual(self.durable(), before)

    def test_restart_of_queued_submission_retains_identity_without_resubmission(self):
        with patch("threading.Thread.start") as launch:
            first = self.start()["generation_submission"]
        self.assertEqual(launch.call_count, 1)
        self.assertEqual(self.manager._state["jobs"][0]["execution_status"], "Queued")
        self.manager.close()
        self.manager = self._manager(ProjectStore(self.directory / "project"))
        self.assertEqual(self.manager._state["jobs"][0]["execution_status"], "Interrupted")
        before = self.durable()
        with patch("threading.Thread.start", side_effect=AssertionError("A replay cannot launch a worker")):
            replay = self.start()["generation_submission"]
        self.assertEqual(replay["job_id"], first["job_id"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(len(self.manager._state["jobs"]), 1)
        self.assertEqual(self.durable(), before)
        self.provider.assert_not_called()

    def test_durable_rejection_remains_terminal_after_restart_and_gate_changes(self):
        preflight = Mock(side_effect=DomainError("fixture_gate", "Not authorized by fixture.", 409))
        with self.assertRaises(DomainError) as first:
            self.start(_preflight=preflight)
        self.assertTrue(first.exception.generation_start_rejected_before_creation)
        self.assertEqual(first.exception.submission_id, self.key)
        receipt = self.manager.submission_receipt(self.key)
        self.assertEqual(receipt["status"], "rejected")
        self.assertIsNone(receipt["job_id"])
        self.assertEqual(receipt["request"], self.arguments)
        self.manager.close()
        self.manager = self._manager(ProjectStore(self.directory / "project"))
        before = self.durable()
        now_allowed = Mock()
        with self.assertRaises(DomainError) as second:
            self.start(_preflight=now_allowed)
        self.assertEqual((second.exception.code, second.exception.message, second.exception.status),
                         (first.exception.code, first.exception.message, first.exception.status))
        self.assertTrue(second.exception.generation_start_rejected_before_creation)
        now_allowed.assert_not_called()
        self.assertEqual(preflight.call_count, 1)
        self.assertEqual(self.durable(), before)
        self.assertEqual(self.manager._state["jobs"], [])
        self.provider.assert_not_called()
        self.assert_conflict(lambda: self.start(instruction="A different request."))

    def test_source_precheck_rejection_has_proof_only_after_saved_tombstone(self):
        arguments = {**self.arguments, "context_id": "not-the-preview-context"}
        with self.assertRaises(DomainError) as error:
            self.manager.start(**arguments, submission_id=self.key)
        self.assertEqual(error.exception.code, "context_conflict")
        self.assertTrue(error.exception.generation_start_rejected_before_creation)
        self.assertEqual(self.manager.submission_receipt(self.key)["status"], "rejected")
        self.assertEqual(self.manager._state["jobs"], [])
        self.provider.assert_not_called()

    def test_job_persistence_failure_rolls_back_without_launch_then_nonce_can_retry(self):
        before = self.durable()
        with patch("hullcirq.generation._replace_with_windows_retry", side_effect=OSError("Fixture storage unavailable")):
            with self.assertRaises(OSError) as error:
                self.start()
        self.assertFalse(getattr(error.exception, "generation_start_rejected_before_creation", False))
        self.assertEqual(self.durable(), before)
        self.assertEqual(self.manager._state["jobs"], [])
        self.assertEqual(self.manager.submission_receipt(self.key)["status"], "not_found")
        self.provider.assert_not_called()
        self.completed_start()
        self.assertEqual(len(self.manager._state["jobs"]), 1)
        self.assertEqual(self.provider.return_value.generate.call_count, 1)

    def test_failed_rejection_save_never_claims_proven_prestart_rejection(self):
        before = self.durable()
        preflight = Mock(side_effect=DomainError("fixture_gate", "Rejected fixture.", 409))
        with patch("hullcirq.generation._replace_with_windows_retry", side_effect=OSError("Fixture storage unavailable")):
            with self.assertRaises(OSError) as error:
                self.start(_preflight=preflight)
        self.assertFalse(getattr(error.exception, "generation_start_rejected_before_creation", False))
        self.assertEqual(self.durable(), before)
        self.assertEqual(self.manager.submission_receipt(self.key)["status"], "not_found")
        self.provider.assert_not_called()
        self.completed_start()

    def test_worker_start_failure_after_commit_is_not_a_prestart_rejection(self):
        with patch("threading.Thread.start", side_effect=DomainError("fixture_after_commit", "Worker fixture refused.", 409)):
            with self.assertRaises(DomainError) as error:
                self.start()
        self.assertFalse(getattr(error.exception, "generation_start_rejected_before_creation", False))
        receipt = self.manager.submission_receipt(self.key)
        self.assertEqual(receipt["status"], "started")
        self.assertEqual(len(self.manager._state["jobs"]), 1)
        replay = self.start()["generation_submission"]
        self.assertEqual(replay["job_id"], receipt["job_id"])
        self.assertTrue(replay["replayed"])
        self.provider.assert_not_called()

    def test_envelope_failure_after_commit_preserves_started_receipt(self):
        original = self.manager.envelope

        def fail_only_after_commit():
            if self.manager._state["jobs"]:
                raise DomainError("fixture_envelope", "Lost fixture acknowledgement.", 409)
            return original()

        with patch.object(self.manager, "envelope", side_effect=fail_only_after_commit):
            with self.assertRaises(DomainError) as error:
                self.start()
        self.join()
        self.assertFalse(getattr(error.exception, "generation_start_rejected_before_creation", False))
        receipt = self.manager.submission_receipt(self.key)
        self.assertEqual(receipt["status"], "started")
        self.assertEqual(self.start()["generation_submission"]["job_id"], receipt["job_id"])
        self.assertEqual(self.provider.return_value.generate.call_count, 1)

    def test_invalid_nonce_formats_fail_without_receipts_or_workers(self):
        before = self.durable()
        for key in (0, True, [], {}, "", " ", "a b", "non-ascii-\u00e4", "a/b", "a\\b", "a\n", "x" * 129):
            with self.subTest(key=key):
                with self.assertRaises(DomainError) as error:
                    self.manager.start(**self.arguments, submission_id=key)
                self.assertEqual(error.exception.code, "invalid_submission_id")
                self.assertEqual(error.exception.status, 400)
                self.assertEqual(self.durable(), before)
        self.provider.assert_not_called()

    def test_nonce_boundary_formats_are_accepted_as_distinct_explicit_requests(self):
        ids = []
        for key in ("a", "A0._-", "z" * 128):
            with self.subTest(key=key):
                envelope, _job = self.completed_start(key)
                ids.append(envelope["generation_submission"]["job_id"])
        self.assertEqual(len(set(ids)), 3)
        self.assertEqual(self.provider.return_value.generate.call_count, 3)

    def test_malformed_and_forged_started_receipts_are_rejected_without_rewriting(self):
        self.completed_start()
        self.manager.close()
        path = self.manager.path
        original = json.loads(path.read_text(encoding="utf-8"))

        def receipt(state):
            return state["submissions"][self.key]

        def changed_request(state, rehash=False):
            value = receipt(state)
            value["request"]["instruction"] = "Forged frozen request."
            if rehash:
                value["binding_hash"] = object_hash(value["request"])

        mutations = {
            "wrong_container": lambda s: s.update(submissions=[]),
            "wrong_binding_hash": lambda s: receipt(s).update(binding_hash="0" * 64),
            "missing_job": lambda s: receipt(s).update(job_id="missing-job"),
            "empty_receipt": lambda s: receipt(s).update(job_id=None, rejection=None),
            "job_and_rejection": lambda s: receipt(s).update(rejection={"code": "fake", "message": "Fake", "status": 409}),
            "duplicate_job_receipt": lambda s: s["submissions"].update({"other-key": copy.deepcopy(receipt(s))}),
            "missing_reverse_receipt": lambda s: s["submissions"].pop(self.key),
            "wrong_job_key": lambda s: s["jobs"][0].update(submission_id="other-key"),
            "invalid_key": lambda s: s["submissions"].update({"bad key": s["submissions"].pop(self.key)}),
            "legacy_job_claimed_by_receipt": lambda s: s["jobs"][0].pop("submission_id"),
            "request_changed": changed_request,
            "rehashed_request_differs_from_job": lambda s: changed_request(s, True),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                state = copy.deepcopy(original)
                mutate(state)
                path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                before = path.read_bytes(), path.stat().st_mtime_ns
                with self.assertRaises(DomainError) as error:
                    self._manager(self.store)
                self.assertEqual(error.exception.code, "invalid_generation_store")
                self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)
        self.assertEqual(self.provider.return_value.generate.call_count, 1)

    def test_rejected_receipt_hash_and_error_shape_are_validated_on_restart(self):
        with self.assertRaises(DomainError):
            self.start(_preflight=lambda: (_ for _ in ()).throw(DomainError("fixture_gate", "Rejected.", 409)))
        self.manager.close()
        path = self.manager.path
        original = json.loads(path.read_text(encoding="utf-8"))
        mutations = {
            "request_hash": lambda r: r["request"].update(instruction="Changed."),
            "invalid_status": lambda r: r["rejection"].update(status=500),
            "bool_status": lambda r: r["rejection"].update(status=True),
            "non_string_code": lambda r: r["rejection"].update(code=[]),
            "non_string_message": lambda r: r["rejection"].update(message={}),
            "success_id_on_rejection": lambda r: r.update(job_id="fake-job"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                state = copy.deepcopy(original)
                mutate(state["submissions"][self.key])
                path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                before = path.read_bytes(), path.stat().st_mtime_ns
                with self.assertRaises(DomainError) as error:
                    self._manager(self.store)
                self.assertEqual(error.exception.code, "invalid_generation_store")
                self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)
        self.provider.assert_not_called()

    def test_legacy_unkeyed_requests_stay_distinct_and_old_job_bytes_are_unchanged(self):
        ids = []
        for _ in range(2):
            envelope = self.manager.start(**self.arguments)
            self.join()
            ids.append(envelope["generation"]["latest_job_id"])
        self.assertEqual(len(set(ids)), 2)
        self.assertTrue(all("submission_id" not in job for job in self.manager._state["jobs"]))
        saved_jobs = self.canonical(self.manager._state["jobs"])
        self.manager.close()
        # Exercise an actual legacy state with the optional ledger absent.
        state = json.loads(self.manager.path.read_text(encoding="utf-8"))
        state.pop("submissions", None)
        self.manager.path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        before = self.durable()
        self.manager = self._manager(ProjectStore(self.directory / "project"))
        self.assertEqual(self.durable(), before)
        self.assertEqual(self.canonical(self.manager._state["jobs"]), saved_jobs)
        self.completed_start()
        self.assertEqual(self.canonical(self.manager._state["jobs"][:2]), saved_jobs)
        self.assertEqual(self.provider.return_value.generate.call_count, 3)

    def test_legacy_reopen_envelope_and_missing_receipt_do_not_write_default_ledger(self):
        self.manager.start(**self.arguments)
        self.join()
        self.manager.close()
        state = json.loads(self.manager.path.read_text(encoding="utf-8"))
        state.pop("submissions", None)
        self.manager.path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        before = self.durable()
        self.manager = self._manager(ProjectStore(self.directory / "project"))
        self.assertEqual(self.durable(), before)
        for _ in range(2):
            envelope = self.manager.envelope()
            receipt = self.manager.submission_receipt("never-submitted-key")
            self.assertEqual(len(envelope["generation"]["jobs"]), 1)
            self.assertEqual(receipt["status"], "not_found")
            self.assertEqual(self.durable(), before)
            self.assertNotIn("submissions", json.loads(self.manager.path.read_text(encoding="utf-8")))
        self.assertEqual(self.provider.return_value.generate.call_count, 1)


if __name__ == "__main__":
    unittest.main()

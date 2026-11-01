"""Pure receipt tests with in-memory owners; no files, models or tools."""
import copy
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hullcirq.domain import DomainError
from hullcirq.execution_submissions import run_submission, submission_view, validate_submissions


class FakeOwner:
    def __init__(self):
        self.lock = threading.RLock()
        self._state = {"jobs": [{"id": "existing-software-job", "raw_content": "committed", "events": []}]}
        self._committed = copy.deepcopy(self._state)
        self.saves = 0
        self.fail_save = False

    def _persist(self):
        if self.fail_save:
            raise OSError("In-memory fixture save failure")
        self.saves += 1
        self._committed = copy.deepcopy(self._state)

    def envelope(self):
        return {"software_fixture": copy.deepcopy(self._state)}

    def dirty_chunk(self):
        self._state["jobs"][0]["raw_content"] += "+pending"
        self._state["jobs"][0]["events"].append({"type": "delta", "content": "+pending"})


class ExecutionSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.owner = FakeOwner()
        self.route = "/api/software-fixture/start"
        self.body = {"submission_id": "software-nonce", "revision_id": "software-revision", "instruction": "Frozen."}
        self.creates = 0

    def create(self, ticket):
        self.creates += 1
        record = {"id": "new-software-job", "software_fixture": True}
        if ticket is not None:
            record["submission_id"] = ticket.submission_id
            ticket.bind(record["id"])
        self.owner._state["jobs"].append(record)
        self.owner._persist()
        return self.owner.envelope()

    def submit(self, create=None, preflight=None, body=None, route=None):
        return run_submission(self.owner, route or self.route, self.body if body is None else body,
                              self.create if create is None else create, preflight=preflight)

    def test_busy_preflight_rejection_keeps_and_durably_saves_existing_pending_chunks(self):
        self.owner.dirty_chunk()
        existing = copy.deepcopy(self.owner._state["jobs"][0])
        create = Mock()
        def busy():
            raise DomainError("generation_busy", "Software fixture busy.", 409)
        with self.assertRaises(DomainError) as error:
            self.submit(create, busy)
        self.assertTrue(error.exception.execution_start_rejected_before_creation)
        create.assert_not_called()
        self.assertEqual(self.owner._state["jobs"], [existing])
        self.assertEqual(self.owner._committed["jobs"], [existing])
        self.assertIsNone(submission_view(self.owner)["software-nonce"]["record_id"])
        validate_submissions(self.owner._state)

    def test_bound_prepersist_failure_removes_only_this_ticket_not_unrelated_dirty_state(self):
        self.owner.dirty_chunk()
        existing = copy.deepcopy(self.owner._state["jobs"][0])
        committed = copy.deepcopy(self.owner._committed)
        def failed(ticket):
            record = {"id": "uncommitted-software-job", "submission_id": ticket.submission_id}
            ticket.bind(record["id"])
            self.owner._state["jobs"].append(record)
            raise RuntimeError("Software failure before persist")
        with self.assertRaises(RuntimeError):
            self.submit(failed)
        self.assertEqual(self.owner._state["jobs"], [existing])
        self.assertEqual(self.owner._committed, committed)
        self.assertEqual(submission_view(self.owner), {})
        self.assertNotIn("software-nonce", self.owner._state.get("execution_submissions", {}))
        self.assertEqual(self.owner.saves, 0)

    def test_bound_prepersist_domain_rejection_cleans_new_record_but_keeps_dirty_old_job(self):
        self.owner.dirty_chunk()
        existing = copy.deepcopy(self.owner._state["jobs"][0])
        def failed(ticket):
            ticket.bind("uncommitted-software-job")
            self.owner._state["jobs"].append({"id": "uncommitted-software-job", "submission_id": ticket.submission_id})
            raise DomainError("fixture_rejected", "Software rejection before persist.", 409)
        with self.assertRaises(DomainError) as error:
            self.submit(failed)
        self.assertTrue(error.exception.execution_start_rejected_before_creation)
        self.assertEqual(self.owner._state["jobs"], [existing])
        self.assertEqual(self.owner._committed["jobs"], [existing])
        self.assertIsNotNone(submission_view(self.owner)["software-nonce"]["rejection"])
        validate_submissions(self.owner._state)

    def test_failed_save_preserves_pending_old_data_and_nonce_can_be_explicitly_retried(self):
        self.owner.dirty_chunk()
        existing = copy.deepcopy(self.owner._state["jobs"][0])
        self.owner.fail_save = True
        with self.assertRaises(OSError):
            self.submit()
        self.assertEqual(self.owner._state["jobs"], [existing])
        self.assertEqual(submission_view(self.owner), {})
        self.owner.fail_save = False
        reply = self.submit()["execution_submission"]
        self.assertFalse(reply["replayed"])
        self.assertEqual(self.owner._committed["jobs"][0], existing)

    def test_postpersist_response_error_keeps_committed_record_and_never_claims_rejection(self):
        def failed(ticket):
            self.create(ticket)
            raise DomainError("fixture_response", "Acknowledgement fixture failed.", 409)
        with self.assertRaises(DomainError) as error:
            self.submit(failed)
        self.assertFalse(getattr(error.exception, "execution_start_rejected_before_creation", False))
        committed = copy.deepcopy(self.owner._committed)
        forbidden = Mock(side_effect=AssertionError("Replay cannot execute create"))
        reply = self.submit(forbidden)["execution_submission"]
        forbidden.assert_not_called()
        self.assertEqual(reply["record_id"], "new-software-job")
        self.assertTrue(reply["replayed"])
        self.assertEqual(self.owner._committed, committed)
        self.assertEqual(self.creates, 1)

    def test_exact_key_replay_and_changed_route_or_payload_never_execute_again(self):
        self.submit()
        before = copy.deepcopy(self.owner._committed)
        forbidden = Mock(side_effect=AssertionError("A receipt must resolve without create"))
        self.assertTrue(self.submit(forbidden)["execution_submission"]["replayed"])
        for body, route in (({**self.body, "instruction": "Changed."}, self.route),
                            (self.body, self.route + "-other")):
            with self.subTest(route=route, instruction=body["instruction"]), self.assertRaises(DomainError) as error:
                self.submit(forbidden, body=body, route=route)
            self.assertEqual((error.exception.code, error.exception.status), ("submission_conflict", 409))
        self.assertEqual(self.owner._committed, before)
        forbidden.assert_not_called()

    def test_legacy_view_does_not_add_a_ledger_and_unkeyed_create_receives_none(self):
        before = copy.deepcopy(self.owner._state)
        self.assertEqual(submission_view(self.owner), {})
        validate_submissions(self.owner._state)
        self.assertEqual(self.owner._state, before)
        body = {k: v for k, v in self.body.items() if k != "submission_id"}
        self.submit(body=body)
        self.assertNotIn("execution_submissions", self.owner._state)
        self.assertTrue(all("submission_id" not in row for row in self.owner._state["jobs"]))

    def test_nonclient_server_failure_does_not_create_rejection_or_drop_pending_chunks(self):
        self.owner.dirty_chunk()
        before = copy.deepcopy(self.owner._state)
        def unavailable():
            raise DomainError("fixture_internal", "Software failure.", 500)
        with self.assertRaises(DomainError) as error:
            self.submit(preflight=unavailable)
        self.assertFalse(getattr(error.exception, "execution_start_rejected_before_creation", False))
        self.assertEqual(self.owner._state, before)
        self.assertEqual(submission_view(self.owner), {})
        self.assertEqual(self.owner.saves, 0)


if __name__ == "__main__":
    unittest.main()

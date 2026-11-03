"""Atomic-save durability with injected OS faults, not circuit evidence."""
from __future__ import annotations

import copy
import errno
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq import store as store_module
from hullcirq.store import ProjectStore


def denied(code=None):
    error = PermissionError(errno.EACCES, "Injected atomic replace denial")
    if code is not None:
        error.winerror = code
    return error


class AtomicReplaceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name) / "project"
        self.store = ProjectStore(self.directory)
        self.previous = copy.deepcopy(self.store._state)
        self.previous_bytes = self.store.state_path.read_bytes()
        self.original = self.store.envelope()
        self.changed = copy.deepcopy(self.original["design"])
        self.changed["project"]["name"] = "Atomic save — 保存"

    def save(self):
        return self.store.save(self.changed, self.original["revision"]["id"])

    def assert_previous(self):
        self.assertEqual(self.store._state, self.previous)
        self.assertEqual(self.store.envelope(), self.original)
        self.assertEqual(self.store.state_path.read_bytes(), self.previous_bytes)

    def assert_failure_cleanup(self):
        self.assert_previous()
        self.assertEqual(list(self.directory.glob(".state-*.tmp")), [])
        self.assertEqual(ProjectStore(self.directory)._state, self.previous)

    def test_transient_access_denied_reuses_fsynced_bytes_and_commits_after_replace(self):
        actual_replace = store_module.os.replace
        actual_fsync = store_module.os.fsync
        staged = []
        fault = denied(5)

        def replace(source, destination):
            self.assert_previous()  # No new revision/history is visible before replacement succeeds.
            self.assertEqual(store_module._io_path(destination), store_module._io_path(self.store.state_path))
            staged.append((source, Path(source).read_bytes()))
            if len(staged) <= 2:
                raise fault
            actual_replace(source, destination)

        with patch.object(store_module, "sys", SimpleNamespace(platform="win32")), \
                patch.object(store_module.os, "replace", side_effect=replace) as replacement, \
                patch.object(store_module.os, "fsync", wraps=actual_fsync) as sync, \
                patch.object(store_module.time, "sleep") as sleep:
            saved = self.save()
        self.assertEqual(replacement.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(sync.call_count, 1)
        self.assertTrue(all(item == staged[0] for item in staged))
        self.assertEqual(self.store.state_path.read_bytes(), staged[0][1])
        self.assertEqual(json.loads(staged[0][1]), self.store._state)
        self.assertEqual(saved["design"], self.changed)
        self.assertNotEqual(saved["revision"]["id"], self.original["revision"]["id"])
        self.assertEqual(ProjectStore(self.directory)._state, self.store._state)
        self.assertEqual(list(self.directory.glob(".state-*.tmp")), [])

    def test_windows_sharing_and_lock_denials_can_recover(self):
        actual_replace = store_module.os.replace
        for code in (32, 33):
            with self.subTest(winerror=code):
                self.original = self.store.envelope()
                self.changed = copy.deepcopy(self.original["design"])
                self.changed["project"]["name"] = f"Recovered Windows error {code}"
                with patch.object(store_module, "sys", SimpleNamespace(platform="win32")), \
                        patch.object(store_module.os, "replace") as replacement, \
                        patch.object(store_module.time, "sleep") as sleep:
                    # The second attempt performs the real atomic replace, not a fake successful save.
                    def replace(source, destination):
                        if replacement.call_count == 1:
                            raise denied(code)
                        actual_replace(source, destination)
                    replacement.side_effect = replace
                    self.save()
                self.assertEqual(replacement.call_count, 2)
                self.assertEqual(sleep.call_count, 1)
                self.assertEqual(ProjectStore(self.directory).envelope(), self.store.envelope())
                self.assertEqual(list(self.directory.glob(".state-*.tmp")), [])

    def test_permanent_denial_exhausts_bounded_retries_without_changing_state(self):
        self.store.set_review_policy("accept_on_pass", True, "Isolated durability test")
        self.store.validate("global_settings", self.store.envelope()["revision"]["id"])
        self.previous = copy.deepcopy(self.store._state)
        self.previous_bytes = self.store.state_path.read_bytes()
        self.original = self.store.envelope()
        fault = denied(5)
        clock = [0.0]
        waits = []
        staged = []

        def replace(source, destination):
            self.assert_previous()
            staged.append((source, Path(source).read_bytes()))
            raise fault

        def sleep(delay):
            waits.append(delay)
            clock[0] += delay

        with patch.object(store_module, "sys", SimpleNamespace(platform="win32")), \
                patch.object(store_module.os, "replace", side_effect=replace), \
                patch.object(store_module.time, "monotonic", side_effect=lambda: clock[0]), \
                patch.object(store_module.time, "sleep", side_effect=sleep), \
                self.assertRaises(PermissionError) as raised:
            self.save()
        self.assertIs(raised.exception, fault)
        self.assertGreater(len(staged), 1)
        self.assertLessEqual(len(staged), 6)
        self.assertLessEqual(sum(waits), 0.3)
        self.assertTrue(all(item == staged[0] for item in staged))
        self.assert_failure_cleanup()

    def test_other_errors_fail_immediately_without_retry_or_state_change(self):
        non_permission = OSError(errno.EIO, "Injected non-permission I/O failure")
        non_permission.winerror = 32
        for error in (denied(), denied(2), denied(19), non_permission):
            with self.subTest(error=repr(error), winerror=getattr(error, "winerror", None)):
                with patch.object(store_module, "sys", SimpleNamespace(platform="win32")), \
                        patch.object(store_module.os, "replace", side_effect=error) as replacement, \
                        patch.object(store_module.time, "sleep") as sleep, \
                        self.assertRaises(type(error)) as raised:
                    self.save()
                self.assertIs(raised.exception, error)
                self.assertEqual(replacement.call_count, 1)
                sleep.assert_not_called()
                self.assert_failure_cleanup()

    def test_non_windows_denial_fails_immediately(self):
        with patch.object(store_module, "sys", SimpleNamespace(platform="linux")), \
                patch.object(store_module.os, "replace", side_effect=denied(5)) as replacement, \
                patch.object(store_module.time, "sleep") as sleep, self.assertRaises(PermissionError):
            self.save()
        self.assertEqual(replacement.call_count, 1)
        sleep.assert_not_called()
        self.assert_failure_cleanup()

    def test_expired_deadline_prevents_another_attempt_after_delayed_wakeup(self):
        clock = [0.0]

        def delayed_sleep(delay):
            clock[0] = 0.4  # Simulate a scheduler delay; no extra replacement may follow.

        with patch.object(store_module, "sys", SimpleNamespace(platform="win32")), \
                patch.object(store_module.os, "replace", side_effect=denied(5)) as replacement, \
                patch.object(store_module.time, "monotonic", side_effect=lambda: clock[0]), \
                patch.object(store_module.time, "sleep", side_effect=delayed_sleep) as sleep, \
                self.assertRaises(PermissionError):
            self.save()
        self.assertEqual(replacement.call_count, 1)
        self.assertEqual(sleep.call_count, 1)
        self.assert_failure_cleanup()


if __name__ == "__main__":
    unittest.main()

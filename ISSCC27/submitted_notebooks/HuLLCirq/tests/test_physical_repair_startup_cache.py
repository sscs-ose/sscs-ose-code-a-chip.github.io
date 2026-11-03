"""Restoration-only reuse; isolated software fixtures, no live project or EDA."""
import json
import os
import unittest
from unittest.mock import patch

import test_physical_repair_session as fixtures
from hullcirq import physical_repair_session as session


class PhysicalRepairStartupCacheTests(unittest.TestCase):
    def setUp(self):
        self.qa = fixtures.PhysicalRepairSessionTests(methodName="runTest")
        self.qa.setUp()
        self.addCleanup(self.qa.doCleanups)

    def third_profile(self):
        failed = self.qa.second_layout_failure()
        session.prepare_retry(self.qa.server, failed["id"], self.qa.revision)
        for mock in (self.qa.source_validator, self.qa.artifact_validator,
                     self.qa.failed_validator, self.qa.failed_physical_validator):
            mock.reset_mock()

    def restore(self):
        qa = self.qa
        return session.load_repair_configurations(qa.store, qa.base, qa.directory,
                                                 "software-qa-project", "software-qa-system")

    def saved_bytes(self):
        return {path: path.read_bytes() for directory in (self.qa.store_path, self.qa.directory)
                for path in directory.iterdir() if path.is_file()}

    def test_third_restore_parses_each_history_once_but_revalidates_every_failure_proof(self):
        self.third_profile()
        before = self.saved_bytes()
        with patch.object(session, "strict_loads", wraps=session.strict_loads) as loads:
            restored, status = self.restore()
        self.assertTrue(status["configured"])
        self.assertEqual(status["repair_generation"], 3)
        self.assertEqual(restored[2], self.qa.server.physical_workflow.tool_configuration)
        self.assertEqual(loads.call_count, 7)  # Three bundles and four distinct histories.
        self.assertEqual(self.qa.source_validator.call_count, 3)
        self.assertEqual(self.qa.artifact_validator.call_count, 3)
        self.assertEqual(self.qa.failed_validator.call_count, 3)
        self.assertEqual(self.qa.failed_physical_validator.call_count, 2)
        self.assertEqual(self.saved_bytes(), before)

    def test_reopening_does_not_reuse_a_previous_restoration_proof(self):
        self.third_profile()
        for _ in range(2):
            self.assertTrue(self.restore()[1]["configured"])
        self.assertEqual(self.qa.failed_validator.call_count, 6)
        self.assertEqual(self.qa.failed_physical_validator.call_count, 4)

    def test_changed_failure_after_first_validation_rejects_restoration(self):
        self.third_profile()
        path = self.qa.store_path / "postlayout_workflow.json"
        original_builder = self.qa.fixed_builder

        def change_after_validation(layout, work):
            result = original_builder(layout, work)
            path.write_bytes(path.read_bytes() + b"\n")
            return result

        self.qa.builder.side_effect = change_after_validation
        restored, status = self.restore()
        changed = path.read_bytes()
        self.assertFalse(status["configured"])
        self.assertEqual(status["error"]["code"], "physical_repair_history_changed")
        self.assertEqual(restored, self.qa.base)
        self.assertEqual(path.read_bytes(), changed)
        self.qa.failed_validator.assert_called_once()

    def test_final_boundary_rechecks_first_generation_and_bundle_bytes(self):
        self.qa.prepare()
        original_builder = self.qa.fixed_builder
        for path in (self.qa.store_path / "postlayout_workflow.json", self.qa.bundle_path):
            original = path.read_bytes()

            def change_after_validation(layout, work):
                result = original_builder(layout, work)
                path.write_bytes(path.read_bytes() + b"\n")
                return result

            self.qa.builder.side_effect = change_after_validation
            with self.subTest(file=path.name):
                restored, status = self.restore()
                self.assertFalse(status["configured"])
                self.assertEqual(status["error"]["code"], "physical_repair_history_changed")
                self.assertEqual(restored, self.qa.base)
                self.assertEqual(path.read_bytes(), original + b"\n")
            path.write_bytes(original)

    def test_same_size_same_timestamp_change_is_not_a_cache_hit(self):
        self.qa.prepare()
        path = self.qa.store_path / "postlayout_workflow.json"
        raw = path.read_bytes()
        old_stat = path.stat()
        cache = session._RestorationReads()
        saved = session._saved(self.qa.store, "postlayout_workflow", cache)
        changed = raw.replace(b"software-qa-s14", b"software-qa-s15", 1)
        self.assertNotEqual(raw, changed)
        self.assertEqual(len(raw), len(changed))
        path.write_bytes(changed)
        os.utime(path, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
        with self.assertRaises(session.DomainError) as error:
            session._saved(self.qa.store, "postlayout_workflow", cache)
        self.assertEqual(error.exception.code, "physical_repair_history_changed")
        self.assertEqual(saved["runs"][0]["id"], "software-qa-s14")

    def test_new_descendant_bundle_mid_restore_is_not_silently_ignored(self):
        self.qa.prepare()
        path = self.qa.directory / session.RETRY_BUNDLE_NAME
        original_builder = self.qa.fixed_builder

        def add_after_validation(layout, work):
            result = original_builder(layout, work)
            path.write_text('{"SOFTWARE_QA_NEW_BUNDLE":true}', encoding="utf-8")
            return result

        self.qa.builder.side_effect = add_after_validation
        restored, status = self.restore()
        self.assertFalse(status["configured"])
        self.assertEqual(restored, self.qa.base)
        self.assertTrue(path.exists())

    def test_cached_returns_are_independent_and_corruption_is_rechecked_next_open(self):
        self.qa.prepare()
        cache = session._RestorationReads()
        first = session._failure(self.qa.store, self.qa.failure["id"], self.qa.revision, cache)
        first[0]["checks"]["commands"].clear()
        again = session._failure(self.qa.store, self.qa.failure["id"], self.qa.revision, cache)
        self.assertEqual(len(again[0]["checks"]["commands"]), 11)
        self.assertTrue(self.restore()[1]["configured"])
        path = self.qa.store_path / "postlayout_workflow.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        state["runs"][0]["checks"]["commands"].clear()
        fixtures.checksum(state["runs"][0])
        path.write_text(json.dumps(state), encoding="utf-8")
        restored, status = self.restore()
        self.assertFalse(status["configured"])
        self.assertEqual(restored, self.qa.base)

    def test_external_proof_rejection_on_repeated_validation_is_not_cached_away(self):
        self.third_profile()
        before = self.saved_bytes()
        self.qa.failed_validator.side_effect = [None, session.DomainError(
            "software_qa_external_artifact_changed", "SOFTWARE QA external proof changed")]
        restored, status = self.restore()
        self.assertFalse(status["configured"])
        self.assertEqual(status["error"]["code"], "software_qa_external_artifact_changed")
        self.assertEqual(self.qa.failed_validator.call_count, 2)
        self.assertEqual(restored, self.qa.base)
        self.assertEqual(self.saved_bytes(), before)


if __name__ == "__main__":
    unittest.main()

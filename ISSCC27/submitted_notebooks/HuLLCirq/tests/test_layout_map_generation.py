"""Isolated derived-view job QA; no real project, EDA or model is invoked."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from hullcirq.domain import DomainError
from hullcirq import layout_map_generation as jobs
from hullcirq.verification import object_hash


def sealed_run(**changes):
    record = {"id": "physical-workflow-isolated", "revision_id": "revision-isolated",
              "source_manifest_sha256": "a" * 64, "execution_status": "Completed",
              "validation_status": "Passed", "review_status": "Accepted", "acceptance_epoch": 1,
              "checks": {"fixture_only": True}}
    record.update(changes)
    record["record_hash"] = object_hash(record)
    return record


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


class FunctionalMapGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.run = sealed_run()
        self.scope = {"project_id": "project-isolated", "system_id": "system-isolated"}
        self.calls = []
        self.services = []

    def tearDown(self):
        for service in self.services:
            if service._thread is not None:
                service._thread.join(3)
                self.assertFalse(service._thread.is_alive(), "Fixture worker did not terminate")
        self.temporary.cleanup()

    def capture(self, root, raw_run, output):
        self.calls.append(("capture", root, copy.deepcopy(raw_run), output))
        output.mkdir(parents=True)
        write_json(output / "manifest.json", {"fixture_only": "source"})
        return {"source_root": output.relative_to(root).as_posix()}

    def render(self, root, selected, output):
        self.calls.append(("render", root, copy.deepcopy(selected), output))
        output.mkdir(parents=True)
        write_json(output / "report.json", {"summary": {"final_cells": 7}})
        write_json(output / "manifest.json", {"fixture_only": "view"})
        return {"summary": {"final_cells": 7}}

    def verify(self, root, run, candidate):
        self.calls.append(("verify", root, copy.deepcopy(run), copy.deepcopy(candidate)))
        self.assertEqual(candidate["binding"], jobs._binding(run))
        for name in ("source", "view"):
            raw = (root / candidate[name + "_root"] / "manifest.json").read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), candidate[name + "_manifest_sha256"])

    def service(self, **overrides):
        options = {"capture": self.capture, "render": self.render, "verify": self.verify,
                   "recheck": lambda run, scope: True}
        options.update(overrides)
        service = jobs.FunctionalMapGeneration(self.root, **options)
        self.services.append(service)
        return service

    def finish(self, service):
        service._thread.join(3)
        self.assertFalse(service._thread.is_alive())
        self.assertFalse(service.is_active())
        return service.status(self.run, self.scope)["latest_job"]

    def start(self, service):
        return service.start(self.run, self.run["record_hash"], self.scope)

    def test_constructor_and_empty_status_are_read_only(self):
        service = self.service()
        self.assertFalse(service.is_active())
        self.assertEqual(service.status(self.run, self.scope)["jobs"], [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_absent_dynamic_registration_preserves_legacy_minimal_record_contract(self):
        self.assertIsNone(jobs.read_registration(self.root, {"id": "legacy-minimal"}))
        self.assertIsNone(jobs.read_registration(self.root, {**self.run, "source_manifest_sha256": "legacy-invalid"}))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_present_dynamic_registration_still_rejects_invalid_raw_checksum(self):
        service = self.service()
        self.start(service)
        self.finish(service)
        invalid = {**self.run, "record_hash": "f" * 64}
        with self.assertRaises(DomainError):
            jobs.read_registration(self.root, invalid)

    def test_source_recheck_is_mandatory(self):
        with self.assertRaises(ValueError):
            jobs.FunctionalMapGeneration(self.root)

    def test_success_publishes_exact_binding_and_immutable_event_history(self):
        service = self.service()
        first = self.start(service)
        self.assertEqual(first["status"], "Queued")
        self.assertEqual(first["layout_run_id"], self.run["id"])
        self.assertEqual(first["source_root"], "results/fm-source-" + first["id"].removeprefix("functional-map-"))
        self.assertEqual(first["view_root"], "results/fm-view-" + first["id"].removeprefix("functional-map-"))
        completed = self.finish(service)
        self.assertEqual(completed["status"], "Completed")
        self.assertEqual(completed["additional_eda_model_or_simulation_runs"], 0)
        registration = jobs.read_registration(self.root, self.run)
        self.assertEqual(registration["job_id"], first["id"])
        self.assertEqual(registration["scope_identity"], self.scope)
        self.assertEqual(registration["final_cells"], 7)
        directory = self.root / ".work/functional_maps/jobs"
        initial = jobs._validated_record((directory / (first["id"] + ".json")).read_bytes())
        self.assertEqual(initial, first)
        events = sorted((directory / first["id"]).glob("*.json"))
        self.assertEqual(len(events), 4)
        previous = initial
        for index, path in enumerate(events, 1):
            current = jobs._validated_record(path.read_bytes())
            jobs.FunctionalMapGeneration._validate_job(current, first["id"], index, previous)
            previous = current
        self.assertEqual([call[0] for call in self.calls], ["capture", "render", "verify"])
        # Reload/status validates saved evidence but does not write anything.
        before = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        reloaded = self.service()
        self.assertEqual(reloaded.status(self.run, self.scope)["latest_job"], completed)
        self.assertEqual(before, {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()})

    def test_active_job_rejects_duplicates_and_records_no_extra_attempt(self):
        entered = threading.Event()
        release = threading.Event()

        def waiting_capture(root, raw_run, output):
            entered.set()
            if not release.wait(3):
                raise AssertionError("Fixture release missing")
            return self.capture(root, raw_run, output)

        service = self.service(capture=waiting_capture)
        self.start(service)
        self.assertTrue(entered.wait(2))
        self.assertTrue(service.is_active())
        try:
            with self.assertRaises(DomainError) as raised:
                self.start(service)
            self.assertEqual(raised.exception.code, "functional_map_generation_active")
            self.assertEqual(len(service.status(self.run, self.scope)["jobs"]), 1)
        finally:
            release.set()
        self.assertEqual(self.finish(service)["status"], "Completed")

    def test_malformed_or_changed_record_is_rejected_before_any_write(self):
        service = self.service()
        changed = copy.deepcopy(self.run)
        changed["checks"] = {"tampered": True}
        for record, expected in ((changed, self.run["record_hash"]), (self.run, "b" * 64)):
            with self.assertRaises(DomainError):
                service.start(record, expected, self.scope)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_unaccepted_or_failed_source_is_not_eligible(self):
        service = self.service()
        for changes in ({"execution_status": "Running"}, {"validation_status": "Failed"}, {"review_status": "Awaiting Review"}):
            run = sealed_run(**changes)
            with self.assertRaises(DomainError) as raised:
                service.start(run, run["record_hash"], self.scope)
            self.assertEqual(raised.exception.code, "functional_map_source_not_eligible")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_recheck_before_start_rejects_stale_context(self):
        service = self.service(recheck=lambda run, scope: False)
        with self.assertRaises(DomainError) as raised:
            self.start(service)
        self.assertEqual(raised.exception.code, "functional_map_source_changed")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_recheck_before_publish_preserves_outputs_without_registering(self):
        checks = iter((True, False))
        service = self.service(recheck=lambda run, scope: next(checks))
        first = self.start(service)
        failed = self.finish(service)
        self.assertEqual(failed["status"], "Failed")
        self.assertEqual(failed["error"]["code"], "functional_map_source_changed")
        self.assertIsNone(jobs.read_registration(self.root, self.run))
        self.assertTrue((self.root / first["source_root"] / "manifest.json").is_file())
        self.assertTrue((self.root / first["view_root"] / "manifest.json").is_file())

    def test_capture_failure_preserved_and_explicit_retry_is_separate_job(self):
        def broken_capture(root, run, output):
            output.mkdir(parents=True)
            (output / "failure.txt").write_text("fixture capture failure", encoding="utf-8")
            raise ValueError("fixture capture failure")

        service = self.service(capture=broken_capture)
        first = self.start(service)
        failed = self.finish(service)
        self.assertEqual(failed["status"], "Failed")
        before = (self.root / ".work/functional_maps/jobs" / first["id"] / "000002.json").read_bytes()
        service._capture = self.capture
        second = self.start(service)
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(self.finish(service)["status"], "Completed")
        self.assertEqual((self.root / ".work/functional_maps/jobs" / first["id"] / "000002.json").read_bytes(), before)
        self.assertEqual((self.root / first["source_root"] / "failure.txt").read_text(encoding="utf-8"), "fixture capture failure")
        self.assertEqual(len(service.status(self.run, self.scope)["jobs"]), 2)

    def test_render_failure_keeps_capture_and_partial_view_unregistered(self):
        def broken_render(root, selected, output):
            output.mkdir(parents=True)
            (output / "partial.txt").write_text("fixture", encoding="utf-8")
            raise ValueError("fixture render failure")

        service = self.service(render=broken_render)
        first = self.start(service)
        self.assertEqual(self.finish(service)["status"], "Failed")
        self.assertIsNone(jobs.read_registration(self.root, self.run))
        self.assertTrue((self.root / first["source_root"] / "manifest.json").is_file())
        self.assertTrue((self.root / first["view_root"] / "partial.txt").is_file())

    def test_full_bundle_verification_failure_prevents_registration(self):
        def reject(root, run, registration):
            raise DomainError("fixture_bundle_invalid", "fixture invalid geometry", 409)

        service = self.service(verify=reject)
        self.start(service)
        failed = self.finish(service)
        self.assertEqual(failed["status"], "Failed")
        self.assertEqual(failed["error"]["code"], "fixture_bundle_invalid")
        self.assertIsNone(jobs.read_registration(self.root, self.run))

    def test_false_verification_result_is_not_treated_as_success(self):
        service = self.service(verify=lambda root, run, registration: False)
        self.start(service)
        self.assertEqual(self.finish(service)["status"], "Failed")
        self.assertIsNone(jobs.read_registration(self.root, self.run))

    def test_mutable_acceptance_fields_do_not_change_binding(self):
        service = self.service()
        self.start(service)
        self.assertEqual(self.finish(service)["status"], "Completed")
        changed = sealed_run(review_status="Awaiting Review", acceptance_epoch=5)
        self.assertEqual(jobs.projection_hash(changed), jobs.projection_hash(self.run))
        self.assertEqual(jobs.read_registration(self.root, changed), jobs.read_registration(self.root, self.run))
        changed_revision = sealed_run(revision_id="revision-other")
        self.assertIsNone(jobs.read_registration(self.root, changed_revision))

    def test_scope_does_not_leak_job_history_or_registration(self):
        service = self.service()
        self.start(service)
        self.finish(service)
        other = {**self.scope, "system_id": "another-system"}
        with self.assertRaises(DomainError) as raised:
            service.status(self.run, other)
        self.assertEqual(raised.exception.code, "functional_map_binding_mismatch")
        for malformed in ({}, {"project_id": "p"}, {**self.scope, "client_path": "elsewhere"}):
            with self.assertRaises(DomainError):
                service.start(self.run, self.run["record_hash"], malformed)

    def test_explicit_regeneration_versions_registration_without_rewriting_prior_jobs(self):
        service = self.service()
        first = self.start(service)
        completed = self.finish(service)
        before = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        second = self.start(service)
        self.assertEqual(self.finish(service)["status"], "Completed")
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(jobs.read_registration(self.root, self.run)["job_id"], second["id"])
        pointer = jobs._registration_path(self.root, self.run).relative_to(self.root)
        for relative, raw in before.items():
            if relative != pointer:
                self.assertEqual((self.root / relative).read_bytes(), raw)
        first_saved = service.status(self.run, self.scope)["jobs"][0]
        self.assertEqual(first_saved, completed)
        self.assertEqual(first_saved["registration"]["job_id"], first["id"])

    def test_immutable_publications_remain_readable_after_pointer_changes(self):
        service = self.service()
        first = self.start(service)
        first_completed = self.finish(service)
        second = self.start(service)
        second_completed = self.finish(service)
        before = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(jobs.read_registration_version(self.root, self.run, first["id"]), first_completed["registration"])
        self.assertEqual(jobs.read_registration_version(self.root, self.run, second["id"]), second_completed["registration"])
        self.assertEqual(jobs.read_registration(self.root, self.run)["job_id"], second["id"])
        self.assertEqual(before, {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()})
        # An already pinned version does not depend on even a corrupt pointer.
        jobs._registration_path(self.root, self.run).write_text("{}\n", encoding="utf-8")
        self.assertEqual(jobs.read_registration_version(self.root, self.run, first["id"]), first_completed["registration"])

    def test_unknown_or_cross_run_publication_never_falls_back(self):
        service = self.service()
        first = self.start(service)
        self.finish(service)
        for run, identifier in ((self.run, "functional-map-" + "f" * 32),
                                (sealed_run(revision_id="different-revision"), first["id"]),
                                (sealed_run(id="different-layout"), first["id"])):
            with self.assertRaises(DomainError) as raised:
                jobs.read_registration_version(self.root, run, identifier)
            self.assertEqual(raised.exception.code, "functional_map_not_available")
        self.assertEqual(jobs.read_registration(self.root, self.run)["job_id"], first["id"])

    def test_publication_identifier_rejects_traversal_and_foreign_paths(self):
        for identifier in (None, "", "../outside", "functional-map-../outside", "C:/outside", "functional-map-" + "A" * 32,
                           "functional-map-" + "a" * 32 + "/other"):
            with self.assertRaises(DomainError):
                jobs.read_registration_version(self.root, self.run, identifier)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_tampered_or_wrong_publication_version_is_rejected(self):
        service = self.service()
        first = self.start(service)
        first_completed = self.finish(service)
        second = self.start(service)
        second_completed = self.finish(service)
        version = jobs._registration_path(self.root, self.run).parent / jobs.projection_hash(self.run) / (first["id"] + ".json")
        write_json(version, second_completed["registration"])
        with self.assertRaises(DomainError) as raised:
            jobs.read_registration_version(self.root, self.run, first["id"])
        self.assertEqual(raised.exception.code, "functional_map_binding_mismatch")
        corrupted = copy.deepcopy(first_completed["registration"])
        corrupted["final_cells"] = 999
        write_json(version, corrupted)
        with self.assertRaises(DomainError):
            jobs.read_registration_version(self.root, self.run, first["id"])
        malformed_scope = {key: value for key, value in first_completed["registration"].items() if key != "record_hash"}
        malformed_scope["scope_identity"] = {"project_id": "missing-system"}
        write_json(version, jobs._sealed(malformed_scope))
        with self.assertRaises(DomainError):
            jobs.read_registration_version(self.root, self.run, first["id"])
        self.assertEqual(jobs.read_registration_version(self.root, self.run, second["id"]), second_completed["registration"])

    def test_corrupt_present_registration_fails_closed(self):
        service = self.service()
        self.start(service)
        self.finish(service)
        pointer = jobs._registration_path(self.root, self.run)
        pointer.write_text('{"bad":true}\n', encoding="utf-8")
        with self.assertRaises(DomainError):
            jobs.read_registration(self.root, self.run)
        with self.assertRaises(DomainError):
            service.status(self.run, self.scope)

    def test_checksum_valid_pointer_requires_exact_immutable_version(self):
        service = self.service()
        self.start(service)
        self.finish(service)
        registration = jobs.read_registration(self.root, self.run)
        del registration["record_hash"]
        registration["final_cells"] = 99
        write_json(jobs._registration_path(self.root, self.run), jobs._sealed(registration))
        with self.assertRaises(DomainError):
            jobs.read_registration(self.root, self.run)

    def test_constructor_and_get_project_interruption_without_writes(self):
        service = self.service()
        with patch.object(threading.Thread, "start", return_value=None):
            first = self.start(service)
        service._thread = None
        service._active_id = None
        initial_path = self.root / ".work/functional_maps/jobs" / (first["id"] + ".json")
        original = initial_path.read_bytes()
        before = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        reloaded = self.service()
        interrupted = reloaded.status(self.run, self.scope)["latest_job"]
        self.assertEqual(interrupted["status"], "Interrupted")
        self.assertEqual(interrupted["recorded_status"], "Queued")
        self.assertTrue(interrupted["recovery_required"])
        self.assertEqual(before, {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()})
        self.start(reloaded)
        self.assertEqual(self.finish(reloaded)["status"], "Completed")
        self.assertEqual(initial_path.read_bytes(), original)
        event = jobs._validated_record((initial_path.with_suffix("") / "000001.json").read_bytes())
        self.assertEqual(event["status"], "Interrupted")
        self.assertEqual(len(reloaded.status(self.run, self.scope)["jobs"]), 2)

    def test_job_event_corruption_and_gaps_are_not_repaired(self):
        service = self.service()
        first = self.start(service)
        self.finish(service)
        event = self.root / ".work/functional_maps/jobs" / first["id"] / "000001.json"
        event.write_text("{}\n", encoding="utf-8")
        original = event.read_bytes()
        with self.assertRaises(DomainError):
            self.service()
        self.assertEqual(event.read_bytes(), original)

    def test_no_overwrite_writer_preserves_existing_evidence(self):
        target = self.root / "fixture.json"
        jobs._write_new(self.root, target, {"first": True})
        original = target.read_bytes()
        with self.assertRaises(FileExistsError):
            jobs._write_new(self.root, target, {"second": True})
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_output_paths_reject_escape_or_foreign_absolute_targets(self):
        for relative in ("../escape", "C:/foreign", "results\\escape", "/absolute"):
            with self.assertRaises(DomainError):
                jobs._below(self.root, relative)

    def test_closed_service_rejects_new_jobs_without_writes(self):
        service = self.service()
        service.close()
        with self.assertRaises(DomainError) as raised:
            self.start(service)
        self.assertEqual(raised.exception.code, "functional_map_service_closed")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_close_during_capture_interrupts_before_render_or_registration(self):
        entered = threading.Event()
        release = threading.Event()

        def waiting_capture(root, run, output):
            entered.set()
            if not release.wait(3):
                raise AssertionError("Fixture release missing")
            return self.capture(root, run, output)

        service = self.service(capture=waiting_capture)
        self.start(service)
        self.assertTrue(entered.wait(2))
        service.close()
        release.set()
        interrupted = self.finish(service)
        self.assertEqual(interrupted["status"], "Interrupted")
        self.assertEqual(interrupted["error"]["code"], "functional_map_service_closed")
        self.assertEqual([call[0] for call in self.calls], ["capture"])
        self.assertIsNone(jobs.read_registration(self.root, self.run))


if __name__ == "__main__":
    unittest.main()

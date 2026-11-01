"""S12 isolated manager QA: all layout/DRC bytes below are software doubles."""
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

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
import test_physical_workflow as fixtures
from hullcirq.domain import DomainError
from hullcirq.drc_workflow import (DrcWorkflowManager, FILE_IDS, validate_artifact_manifest,
                                    validate_drc_proof, validate_source_snapshot)
from hullcirq.verification import object_hash


def fixture_validator(result, layout, configuration):
    if result.get("software_qa_fixture") is not True or result.get("fixture_marker") != "explicitly_simulated_not_DRC_evidence":
        raise DomainError("fixture_proof_invalid", "SOFTWARE QA fixture marker missing")


def fixture_runner(layout, configuration, cancel_event=None):
    folder = Path(tempfile.mkdtemp(prefix="drc-software-fixture-", dir=configuration["working_directory"]))
    artifacts = []
    for identifier in sorted(FILE_IDS):
        payload = ("SOFTWARE QA ONLY: " + identifier + "\r\n").encode()
        (folder / identifier).write_bytes(payload)
        artifacts.append({"id": identifier, "relative_path": identifier, "sha256": hashlib.sha256(payload).hexdigest(),
                          "bytes": len(payload), "content_type": "application/octet-stream" if identifier == "input-gds" else "text/plain; charset=utf-8"})
    gds = next(a for a in layout["checks"]["artifacts"] if a["id"] == "gds")
    return {"status": "Completed", "validation_status": "Passed", "origin": "SOFTWARE_QA_NO_EDA_EXECUTION", "software_qa_fixture": True,
            "fixture_marker": "explicitly_simulated_not_DRC_evidence", "executed": True, "exit_code": 0,
            "layout_run_id": layout["id"], "layout_record_sha256": object_hash(layout), "input_gds_sha256": gds["sha256"],
            "configuration_sha256": object_hash(configuration), "artifacts_directory": str(folder), "artifacts": artifacts,
            "commands": [{"executed": True, "status": "Completed", "exit_code": 0, "command": ["SOFTWARE_QA_NO_EXECUTION"], "stdout": "SOFTWARE QA\n", "stderr": ""}],
            "stdout": "SOFTWARE QA\n", "stderr": "", "diagnostics": [], "metrics": {"software_qa_fixture": True},
            "checks": {"source_identity": {"validation_status": "Passed"}, "configuration": {"validation_status": "Passed"},
                       "drc": {"validation_status": "Passed", "executed": True, "completed": True}}, "retained_files": []}


class DrcWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.PhysicalWorkflowTests("runTest"); self.base.setUp(); self.addCleanup(self.base.doCleanups)
        self.store, self.physical = self.base.store, self.base.manager
        self.layout = self.base.run_layout()
        directory = self.base.base.base.directory / "drc-artifacts"; directory.mkdir()
        self.configuration = {"version": "SOFTWARE_QA_ONLY", "working_directory": str(directory), "profile": {"kind": "SOFTWARE_QA_ONLY"}}
        self.manager = self.new_manager(); self.addCleanup(self.manager.close)

    def new_manager(self, runner=fixture_runner, validator=fixture_validator, configuration=None):
        return DrcWorkflowManager(self.store, self.physical, self.configuration if configuration is None else configuration, runner, validator)

    def run_drc(self, runner=None):
        if runner is not None: self.manager._runner = runner
        self.manager.start("drc", self.layout["id"], self.layout["revision_id"])
        self.manager._worker.join(20); self.assertFalse(self.manager._worker.is_alive())
        return self.manager.run(self.manager._state["runs"][-1]["id"])

    def test_exact_adopted_layout_gds_policy_and_restart_preserve_all_upstream(self):
        paths = [m.path for m in (self.physical, self.base.global_manager, self.base.global_workflow)] + [self.store.state_path]
        before = [p.read_bytes() for p in paths]
        run = self.run_drc()
        self.assertEqual((run["execution_status"], run["validation_status"], run["review_status"], run["freshness"]), ("Completed", "Passed", "Accepted", "Current"))
        self.assertEqual(run["layout_snapshot"], self.physical._run(self.layout["id"]))
        self.assertEqual(run["layout_record_sha256"], object_hash(run["layout_snapshot"]))
        self.assertEqual(run["evidence_kind"], "software_qa_fixture")
        validate_source_snapshot(run); validate_drc_proof(run, fixture_validator)
        self.assertEqual(before, [p.read_bytes() for p in paths]); self.assertEqual(self.manager.path.name, "drc_workflow.json")
        self.assertEqual(self.manager._state["reviews"][-1]["actor"], "automation_policy")
        reopened = self.new_manager(); self.addCleanup(reopened.close)
        self.assertEqual(reopened.envelope()["drc_workflow"]["accepted_run_id"], run["id"])

    def test_no_current_accepted_layout_wrong_source_and_revision_block_before_runner(self):
        with patch.object(self.manager, "_runner") as runner:
            for stage, identifier, revision in (("layout", self.layout["id"], None), ("drc", "old-layout", None), ("drc", self.layout["id"], "old-revision")):
                with self.subTest(stage=stage, identifier=identifier, revision=revision), self.assertRaises(DomainError): self.manager.start(stage, identifier, revision)
            self.physical.review(self.layout["id"], "changes_requested", "SOFTWARE QA withdraw")
            with self.assertRaises(DomainError): self.manager.start("drc", self.layout["id"])
            runner.assert_not_called()
        self.assertFalse(self.manager._state["runs"])

    def test_withdraw_restore_layout_never_revives_old_drc_acceptance_even_after_restart(self):
        run = self.run_drc()
        self.physical.review(self.layout["id"], "changes_requested", "SOFTWARE QA withdraw")
        self.assertEqual(self.manager.run(run["id"])["freshness"], "Stale")
        self.physical.review(self.layout["id"], "accepted", "SOFTWARE QA explicit reaccept")
        self.assertEqual(self.manager.run(run["id"])["review_status"], "Awaiting Review")
        with self.assertRaises(DomainError): self.manager.review(run["id"], "accepted", "")
        reopened = self.new_manager(); self.addCleanup(reopened.close)
        self.assertEqual(reopened.run(run["id"])["freshness"], "Stale")

    def test_profile_roundtrip_and_gds_tamper_never_revive_old_adoption(self):
        run = self.run_drc(); original = copy.deepcopy(self.manager.tool_configuration)
        self.manager.tool_configuration["profile"]["kind"] = "changed"
        self.assertEqual(self.manager.run(run["id"])["freshness"], "Stale")
        self.manager.tool_configuration = original
        self.assertEqual(self.manager.run(run["id"])["freshness"], "Stale")
        path = self.physical.artifact_file(self.layout["id"], "gds")["path"]; raw = path.read_bytes(); path.write_bytes(raw + b"changed")
        try:
            self.assertFalse(self.manager.envelope()["drc_workflow"]["ready"])
            with self.assertRaises(DomainError): self.manager.start("drc", self.layout["id"])
        finally: path.write_bytes(raw)
        self.assertEqual(self.manager.run(run["id"])["freshness"], "Stale")

    def test_latest_failed_layout_blocks_previously_adopted_gds(self):
        run = self.run_drc()
        def failed_layout(*args, **kwargs):
            report = fixtures.fixture_runner(*args, **kwargs); report["validation_status"] = "Failed"; return report
        latest = self.base.run_layout(failed_layout)
        self.assertEqual(latest["validation_status"], "Failed")
        self.assertFalse(self.manager.envelope()["drc_workflow"]["ready"])
        self.assertEqual(self.manager.run(run["id"])["freshness"], "Stale")

    def test_inflight_source_withdrawal_blocks_automatic_adoption(self):
        def changed(*args, **kwargs):
            result = fixture_runner(*args, **kwargs)
            self.physical.review(self.layout["id"], "changes_requested", "SOFTWARE QA inflight withdrawal")
            return result
        run = self.run_drc(changed)
        self.assertEqual(run["validation_status"], "Passed"); self.assertEqual(run["review_status"], "Awaiting Review")
        self.assertEqual(run["freshness"], "Stale"); self.assertTrue(any(d["code"] == "automatic_adoption_blocked" for d in run["diagnostics"]))

    def test_invalid_typed_pass_retains_raw_report_and_commands_without_adoption(self):
        def invalid(*args, **kwargs):
            result = fixture_runner(*args, **kwargs); result["exit_code"] = False; return result
        run = self.run_drc(invalid)
        self.assertEqual(run["execution_status"], "Failed"); self.assertEqual(run["validation_status"], "Not Checked")
        self.assertTrue(run["checks"]["commands"]); self.assertEqual(run["checks"]["stdout"], "SOFTWARE QA\n"); self.assertFalse(self.manager._state["reviews"])

    def test_every_proof_binding_command_and_complete_check_is_required(self):
        run = self.run_drc()
        mutations = (lambda r: r["checks"].update(exit_code=True), lambda r: r["checks"].update(layout_run_id="different"),
                     lambda r: r["checks"].update(layout_record_sha256="0" * 64), lambda r: r["checks"].update(configuration_sha256="0" * 64),
                     lambda r: r["checks"].update(input_gds_sha256="0" * 64), lambda r: r["checks"]["commands"][0].update(exit_code=False),
                     lambda r: r["checks"]["checks"]["drc"].update(completed=False), lambda r: r["checks"]["checks"]["drc"].update(executed=False),
                     lambda r: r["checks"]["artifacts"].pop(), lambda r: r["checks"].update(cleanup_unresolved=True),
                     lambda r: r["checks"].update(fixture_marker="fabricated"), lambda r: r.update(evidence_kind="trusted_fixed_drc_execution"))
        for mutate in mutations:
            bad = copy.deepcopy(run); mutate(bad)
            with self.subTest(mutation=mutate), self.assertRaises(DomainError): validate_drc_proof(bad, fixture_validator)

    def test_fixed_raw_download_hashes_and_portable_source_snapshot(self):
        run = self.run_drc()
        for identifier in FILE_IDS:
            raw, mime = self.manager.artifact_bytes(run["id"], identifier)
            self.assertIn(b"SOFTWARE QA ONLY", raw); self.assertIn("/", mime)
        self.assertEqual(self.manager.artifact(run["id"], "layout-record"), run["layout_snapshot"])
        for identifier in ("../../state.json", "arbitrary-expression"):
            with self.assertRaises(DomainError): self.manager.artifact_file(run["id"], identifier)
        path = self.manager.artifact_file(run["id"], "magic-report")["path"]; raw = path.read_bytes(); path.write_bytes(raw + b"changed")
        try:
            with self.assertRaises(DomainError): self.manager.artifact_bytes(run["id"], "magic-report")
            with self.assertRaises(DomainError): self.new_manager()
        finally: path.write_bytes(raw)

    def test_artifact_paths_duplicate_ids_boolean_lengths_and_header_injection_rejected(self):
        run = self.run_drc()
        mutations = (lambda r: r["artifacts"][0].update(relative_path="../state.json"), lambda r: r["artifacts"].append(copy.deepcopy(r["artifacts"][0])),
                     lambda r: r["artifacts"][0].update(bytes=True), lambda r: r["artifacts"][0].update(relative_path="C:/outside"),
                     lambda r: r["artifacts"][0].update(content_type="text/plain\r\nInjected: yes"))
        for mutate in mutations:
            result = copy.deepcopy(run["checks"]); mutate(result)
            with self.subTest(mutation=mutate), self.assertRaises(DomainError): validate_artifact_manifest(result)

    def test_rehashed_history_tamper_source_gds_epoch_configuration_and_policy_rejected(self):
        self.run_drc(); original = self.manager.path.read_bytes()
        mutations = (lambda r: r["layout_snapshot"].update(global_rtl="fabricated"), lambda r: r["source_identity"].update(physical_source_epoch=True),
                     lambda r: r["source_identity"]["input_gds"].update(sha256="0" * 64), lambda r: r["runtime_configuration"]["profile"].update(kind="other"),
                     lambda r: r.update(evidence_kind="trusted_fixed_drc_execution"), lambda r: r["layout_adoption"].update(actor="fabricated"))
        for mutate in mutations:
            state = json.loads(original); mutate(state["runs"][0]); run = state["runs"][0]; run["record_hash"] = object_hash({k: v for k, v in run.items() if k != "record_hash"})
            self.manager.path.write_text(json.dumps(state), encoding="utf-8")
            with self.subTest(mutation=mutate), self.assertRaises(DomainError): self.new_manager()
        self.manager.path.write_bytes(original)

    def test_cancel_busy_and_restart_never_resend_tools_and_unverified_restart_blocks(self):
        entered = threading.Event(); release = threading.Event(); calls = []
        def slow(*args, **kwargs):
            calls.append("SOFTWARE QA"); entered.set(); release.wait(5); return fixture_runner(*args, **kwargs)
        self.manager._runner = slow; self.manager.start("drc", self.layout["id"]); self.assertTrue(entered.wait(5))
        identifier = self.manager._state["runs"][-1]["id"]
        with self.assertRaises(DomainError): self.manager.start("drc", self.layout["id"])
        self.manager.cancel(identifier); release.set(); self.manager._worker.join(10)
        self.assertEqual(self.manager.run(identifier)["execution_status"], "Cancelled")
        state = json.loads(self.manager.path.read_text()); state["runs"][0]["execution_status"] = "Running"; state["runs"][0]["record_hash"] = object_hash({k: v for k, v in state["runs"][0].items() if k != "record_hash"})
        self.manager.path.write_text(json.dumps(state), encoding="utf-8")
        reopened = self.new_manager(runner=slow); self.addCleanup(reopened.close)
        self.assertEqual(reopened.run(identifier)["execution_status"], "Interrupted"); self.assertTrue(reopened.is_active())
        self.assertFalse(reopened.envelope()["drc_workflow"]["ready"]); self.assertEqual(len(calls), 1)
        with self.assertRaises(DomainError): reopened.start("drc", self.layout["id"])

    def test_terminal_unresolved_cleanup_remains_admission_blocked_after_restart(self):
        def unresolved(*args, **kwargs):
            result = fixture_runner(*args, **kwargs); result["cleanup_unresolved"] = True; return result
        run = self.run_drc(unresolved)
        self.assertEqual(run["execution_status"], "Failed"); self.assertTrue(run["checks"]["cleanup_unresolved"])
        reopened = self.new_manager(runner=unresolved); self.addCleanup(reopened.close)
        for manager in (self.manager, reopened):
            self.assertTrue(manager.is_active()); self.assertFalse(manager.envelope()["drc_workflow"]["ready"])
            with self.assertRaises(DomainError) as blocked: manager.start("drc", self.layout["id"])
            self.assertEqual(blocked.exception.code, "drc_cleanup_unresolved")
            self.assertFalse(manager._state["reviews"])

    def test_back_to_layout_durable_review_failure_and_superseded_run(self):
        run = self.run_drc()
        with self.assertRaises(DomainError): self.manager.review(run["id"], "return_to_stage", "future", "lvs")
        original = self.manager.path.read_bytes()
        with patch("hullcirq.drc_workflow.os.replace", side_effect=OSError("SOFTWARE QA disk failure")):
            with self.assertRaises(OSError): self.manager.review(run["id"], "changes_requested", "SOFTWARE QA save failure")
        self.assertEqual(self.manager.path.read_bytes(), original); self.assertEqual(self.manager.run(run["id"])["review_status"], "Accepted")
        self.manager.review(run["id"], "return_to_stage", "SOFTWARE QA return", "layout")
        self.assertEqual(self.manager.run(run["id"])["review_status"], "Changes Requested")
        self.run_drc()
        with self.assertRaises(DomainError): self.manager.review(run["id"], "accepted", "old")

    def test_other_tool_active_and_fixture_promotion_blocked_without_call(self):
        active_job = copy.deepcopy(self.base.global_manager._state["jobs"][-1]); active_job["execution_status"] = "Running"
        self.base.global_manager._state["jobs"].append(active_job)
        try:
            with self.assertRaises(DomainError): self.manager.start("drc", self.layout["id"])
        finally: self.base.global_manager._state["jobs"].pop()
        self.manager._injected = False
        with patch.object(self.manager, "_capability", return_value={"available": True}):
            with self.assertRaises(DomainError) as blocked: self.manager.start("drc", self.layout["id"])
            self.assertEqual(blocked.exception.code, "drc_layout_not_current")


if __name__ == "__main__": unittest.main()

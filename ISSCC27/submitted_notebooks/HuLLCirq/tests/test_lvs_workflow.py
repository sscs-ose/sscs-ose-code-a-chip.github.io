"""S13 isolated history/lineage QA; all circuit/tool outputs are explicit doubles."""
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
import test_drc_workflow as fixtures
from hullcirq.domain import DomainError
from hullcirq.lvs_workflow import (LvsWorkflowManager, FILE_IDS, validate_artifact_manifest,
                                   validate_lvs_proof, validate_source_snapshot)
from hullcirq.verification import object_hash


def fixture_inputs(layout):
    """SOFTWARE QA only. Actual S13 uses the strict original-S11 pointer binder."""
    root = Path(layout["checks"]["artifacts_directory"])
    inputs = {}
    for name in ("gds", "def", "netlist"):
        descriptor = copy.deepcopy(next(a for a in layout["checks"]["artifacts"] if a["id"] == name))
        raw = (root / descriptor["relative_path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != descriptor["sha256"]:
            raise DomainError("software_qa_source_changed", "SOFTWARE QA original artifact changed")
        inputs[name] = descriptor
    payload = b"SOFTWARE QA ONLY: powered circuit\r\n"
    path = root / "powered-netlist"
    if not path.exists(): path.write_bytes(payload)
    if path.read_bytes() != payload:
        raise DomainError("software_qa_source_changed", "SOFTWARE QA original powered circuit changed")
    inputs["powered_netlist"] = {"id": "powered-netlist", "relative_path": path.name, "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(), "content_type": "text/plain; charset=utf-8",
        "origin": "original_S11_state_pointer_observed_at_S13_start", "binding": {"software_qa_fixture": True}}
    return inputs


def fixture_validator(result, drc, layout, configuration):
    if result.get("software_qa_fixture") is not True or result.get("fixture_marker") != "explicitly_simulated_not_LVS_evidence":
        raise DomainError("fixture_proof_invalid", "SOFTWARE QA fixture marker missing")


def fixture_runner(drc, layout, configuration, cancel_event=None):
    folder = Path(tempfile.mkdtemp(prefix="lvs-software-fixture-", dir=configuration["working_directory"]))
    artifacts = []
    for identifier in sorted(FILE_IDS):
        payload = ("SOFTWARE QA ONLY: " + identifier + "\r\n").encode()
        (folder / identifier).write_bytes(payload)
        artifacts.append({"id": identifier, "relative_path": identifier, "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload), "content_type": "application/octet-stream" if identifier == "input-gds" else "text/plain; charset=utf-8"})
    inputs = fixture_inputs(layout)
    return {"status": "Completed", "validation_status": "Passed", "origin": "SOFTWARE_QA_NO_EDA_EXECUTION", "software_qa_fixture": True,
        "fixture_marker": "explicitly_simulated_not_LVS_evidence", "executed": True, "exit_code": 0,
        "drc_run_id": drc["id"], "drc_record_sha256": object_hash(drc),
        "layout_run_id": layout["id"], "layout_record_sha256": object_hash(layout), "input_gds_sha256": inputs["gds"]["sha256"],
        "input_netlist_sha256": inputs["netlist"]["sha256"], "input_powered_netlist_sha256": inputs["powered_netlist"]["sha256"],
        "configuration_sha256": object_hash(configuration), "artifacts_directory": str(folder), "artifacts": artifacts,
        "commands": [{"executed": True, "status": "Completed", "exit_code": 0, "command": ["SOFTWARE_QA_NO_EXECUTION"], "stdout": "SOFTWARE QA\n", "stderr": ""}],
        "stdout": "SOFTWARE QA\n", "stderr": "", "diagnostics": [], "metrics": {"software_qa_fixture": True},
        "checks": {"source_identity": {"validation_status": "Passed"}, "configuration": {"validation_status": "Passed"},
                   "extraction": {"validation_status": "Passed", "executed": True, "completed": True},
                   "lvs": {"validation_status": "Passed", "executed": True, "completed": True}}, "retained_files": []}


class LvsWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.DrcWorkflowTests("runTest"); self.base.setUp(); self.addCleanup(self.base.doCleanups)
        self.store, self.drc, self.physical = self.base.store, self.base.manager, self.base.physical
        self.layout = self.base.layout; self.drc_run = self.base.run_drc()
        directory = Path(self.base.configuration["working_directory"]).parent / "lvs-artifacts"; directory.mkdir()
        self.configuration = {"version": "SOFTWARE_QA_ONLY", "working_directory": str(directory), "profile": {"kind": "SOFTWARE_QA_ONLY"}}
        self.inputs_patch = patch("hullcirq.lvs_workflow._source_inputs", side_effect=fixture_inputs)
        self.inputs_patch.start(); self.addCleanup(self.inputs_patch.stop)
        self.manager = self.new_manager(); self.addCleanup(self.manager.close)

    def new_manager(self, runner=fixture_runner, validator=fixture_validator, configuration=None):
        return LvsWorkflowManager(self.store, self.drc, self.configuration if configuration is None else configuration, runner, validator)

    def run_lvs(self, runner=None):
        if runner is not None: self.manager._runner = runner
        self.manager.start("lvs", self.layout["id"], self.drc_run["id"], self.layout["revision_id"])
        self.manager._worker.join(20); self.assertFalse(self.manager._worker.is_alive())
        return self.manager.run(self.manager._state["runs"][-1]["id"])

    def test_exact_both_adopted_records_policy_and_restart_preserve_upstream(self):
        paths = [m.path for m in (self.drc, self.physical, self.base.base.global_manager, self.base.base.global_workflow)] + [self.store.state_path]
        before = [p.read_bytes() for p in paths]
        run = self.run_lvs()
        self.assertEqual((run["execution_status"], run["validation_status"], run["review_status"], run["freshness"]), ("Completed", "Passed", "Accepted", "Current"))
        self.assertEqual(run["layout_snapshot"], self.physical._run(self.layout["id"]))
        self.assertEqual(run["drc_snapshot"], self.drc._run(self.drc_run["id"]))
        self.assertEqual(run["layout_record_sha256"], run["drc_snapshot"]["layout_record_sha256"])
        validate_source_snapshot(run); validate_lvs_proof(run, fixture_validator)
        self.assertEqual(before, [p.read_bytes() for p in paths]); self.assertEqual(self.manager.path.name, "lvs_workflow.json")
        self.assertEqual(self.manager._state["reviews"][-1]["actor"], "automation_policy")
        self.assertEqual(self.manager.envelope()["lvs_workflow"]["source_inputs"], run["source_inputs"])
        reopened = self.new_manager(); self.addCleanup(reopened.close)
        self.assertEqual(reopened.envelope()["lvs_workflow"]["accepted_run_id"], run["id"])

    def test_wrong_stage_source_revision_or_unadopted_drc_never_calls_runner(self):
        with patch.object(self.manager, "_runner") as runner:
            cases = (("drc", self.layout["id"], self.drc_run["id"], None), ("lvs", "old-layout", self.drc_run["id"], None),
                     ("lvs", self.layout["id"], "old-drc", None), ("lvs", self.layout["id"], self.drc_run["id"], "old-revision"))
            for args in cases:
                with self.subTest(args=args), self.assertRaises(DomainError): self.manager.start(*args)
            self.drc.review(self.drc_run["id"], "changes_requested", "SOFTWARE QA withdraw")
            with self.assertRaises(DomainError): self.manager.start("lvs", self.layout["id"], self.drc_run["id"])
            runner.assert_not_called()
        self.assertFalse(self.manager._state["runs"])

    def test_invalid_newly_observed_powered_origin_rejected_before_history_or_tool(self):
        def invalid(layout):
            inputs = fixture_inputs(layout); inputs["powered_netlist"]["origin"] = "retrospectively_retained_at_S11"; return inputs
        with patch("hullcirq.lvs_workflow._source_inputs", side_effect=invalid), patch.object(self.manager, "_runner") as runner:
            with self.assertRaises(DomainError): self.manager.start("lvs", self.layout["id"], self.drc_run["id"])
            runner.assert_not_called()
        self.assertFalse(self.manager._state["runs"])

    def test_drc_withdraw_restore_never_revives_old_lvs_acceptance(self):
        run = self.run_lvs()
        self.drc.review(self.drc_run["id"], "changes_requested", "SOFTWARE QA withdraw")
        self.assertEqual(self.manager.run(run["id"])["freshness"], "Stale")
        self.drc.review(self.drc_run["id"], "accepted", "SOFTWARE QA explicit reaccept")
        self.assertEqual(self.manager.run(run["id"])["review_status"], "Awaiting Review")
        with self.assertRaises(DomainError): self.manager.review(run["id"], "accepted", "")
        reopened = self.new_manager(); self.addCleanup(reopened.close)
        self.assertEqual(reopened.run(run["id"])["freshness"], "Stale")

    def test_layout_withdraw_restore_stales_both_downstream_stages(self):
        run = self.run_lvs()
        self.physical.review(self.layout["id"], "changes_requested", "SOFTWARE QA withdraw")
        self.assertEqual(self.manager.run(run["id"])["freshness"], "Stale")
        self.physical.review(self.layout["id"], "accepted", "SOFTWARE QA explicit reaccept")
        self.assertFalse(self.manager.envelope()["lvs_workflow"]["ready"])
        self.assertEqual(self.manager.run(run["id"])["freshness"], "Stale")
        with self.assertRaises(DomainError): self.manager.review(run["id"], "accepted", "")

    def test_profile_roundtrip_and_original_gds_netlist_powered_tamper_never_revive(self):
        run = self.run_lvs(); original = copy.deepcopy(self.manager.tool_configuration)
        self.manager.tool_configuration["profile"]["kind"] = "changed"
        self.assertEqual(self.manager.run(run["id"])["freshness"], "Stale")
        self.manager.tool_configuration = original
        self.assertEqual(self.manager.run(run["id"])["freshness"], "Stale")
        root = Path(self.layout["checks"]["artifacts_directory"])
        for name in ("gds", "netlist", "powered_netlist"):
            path = root / run["source_inputs"][name]["relative_path"]; raw = path.read_bytes(); path.write_bytes(raw + b"changed")
            try:
                with self.subTest(name=name):
                    self.assertFalse(self.manager.envelope()["lvs_workflow"]["ready"])
                    with self.assertRaises(DomainError): self.manager.start("lvs", self.layout["id"], self.drc_run["id"])
            finally: path.write_bytes(raw)
        self.assertEqual(self.manager.run(run["id"])["freshness"], "Stale")

    def test_latest_failed_drc_blocks_previously_adopted_lvs(self):
        run = self.run_lvs()
        def failed(*args, **kwargs):
            result = fixtures.fixture_runner(*args, **kwargs); result["validation_status"] = "Failed"; return result
        latest = self.base.run_drc(failed)
        self.assertEqual(latest["validation_status"], "Failed")
        self.assertFalse(self.manager.envelope()["lvs_workflow"]["ready"])
        self.assertEqual(self.manager.run(run["id"])["freshness"], "Stale")

    def test_inflight_drc_withdrawal_blocks_automatic_adoption(self):
        def changed(*args, **kwargs):
            result = fixture_runner(*args, **kwargs)
            self.drc.review(self.drc_run["id"], "changes_requested", "SOFTWARE QA inflight withdrawal")
            return result
        run = self.run_lvs(changed)
        self.assertEqual(run["validation_status"], "Passed"); self.assertEqual(run["review_status"], "Awaiting Review")
        self.assertEqual(run["freshness"], "Stale"); self.assertTrue(any(d["code"] == "automatic_adoption_blocked" for d in run["diagnostics"]))

    def test_valid_failed_comparison_is_retained_without_adoption(self):
        def failed(*args, **kwargs):
            result = fixture_runner(*args, **kwargs); result["validation_status"] = "Failed"; result["checks"]["lvs"]["validation_status"] = "Failed"; return result
        run = self.run_lvs(failed)
        self.assertEqual((run["execution_status"], run["validation_status"], run["review_status"]), ("Completed", "Failed", "Awaiting Review"))
        self.assertTrue(run["checks"]["commands"]); self.assertFalse(self.manager._state["reviews"])
        reopened = self.new_manager(); self.addCleanup(reopened.close)
        self.assertEqual(reopened.run(run["id"])["validation_status"], "Failed")

    def test_typed_exit_or_missing_extraction_never_adopts_and_keeps_raw_commands(self):
        def invalid(*args, **kwargs):
            result = fixture_runner(*args, **kwargs); result["exit_code"] = False; return result
        run = self.run_lvs(invalid)
        self.assertEqual(run["execution_status"], "Failed"); self.assertEqual(run["validation_status"], "Not Checked")
        self.assertTrue(run["checks"]["commands"]); self.assertFalse(self.manager._state["reviews"])

    def test_every_dual_source_hash_circuit_and_extraction_proof_binding_is_required(self):
        run = self.run_lvs()
        mutations = (lambda r: r["checks"].update(exit_code=True), lambda r: r["checks"].update(layout_run_id="different"),
            lambda r: r["checks"].update(drc_run_id="different"), lambda r: r["checks"].update(layout_record_sha256="0" * 64),
            lambda r: r["checks"].update(drc_record_sha256="0" * 64), lambda r: r["checks"].update(configuration_sha256="0" * 64),
            lambda r: r["checks"].update(input_gds_sha256="0" * 64), lambda r: r["checks"].update(input_netlist_sha256="0" * 64),
            lambda r: r["checks"].update(input_powered_netlist_sha256="0" * 64), lambda r: r["checks"]["commands"][0].update(exit_code=False),
            lambda r: r["checks"]["checks"]["extraction"].update(completed=False), lambda r: r["checks"]["checks"]["extraction"].update(executed=False),
            lambda r: r["checks"]["checks"]["lvs"].update(completed=False), lambda r: r["checks"]["artifacts"].pop(),
            lambda r: r["checks"].update(cleanup_unresolved=True), lambda r: r["checks"].update(fixture_marker="fabricated"),
            lambda r: r.update(evidence_kind="trusted_fixed_lvs_execution"))
        for mutate in mutations:
            bad = copy.deepcopy(run); mutate(bad)
            with self.subTest(mutation=mutate), self.assertRaises(DomainError): validate_lvs_proof(bad, fixture_validator)

    def test_fixed_raw_downloads_source_docs_and_tampered_artifact_rejection(self):
        run = self.run_lvs()
        for identifier in FILE_IDS:
            raw, mime = self.manager.artifact_bytes(run["id"], identifier)
            self.assertIn(b"SOFTWARE QA ONLY", raw); self.assertIn("/", mime)
        self.assertEqual(self.manager.artifact(run["id"], "drc-record"), run["drc_snapshot"])
        self.assertEqual(self.manager.artifact(run["id"], "layout-record"), run["layout_snapshot"])
        for identifier in ("../../state.json", "arbitrary-expression"):
            with self.assertRaises(DomainError): self.manager.artifact_file(run["id"], identifier)
        path = self.manager.artifact_file(run["id"], "lvs-report")["path"]; raw = path.read_bytes(); path.write_bytes(raw + b"changed")
        try:
            with self.assertRaises(DomainError): self.manager.artifact_bytes(run["id"], "lvs-report")
            with self.assertRaises(DomainError): self.new_manager()
        finally: path.write_bytes(raw)

    def test_empty_extraction_feedback_is_retained_and_downloaded_without_fabricating_text(self):
        def empty_feedback(*args, **kwargs):
            result = fixture_runner(*args, **kwargs)
            entry = next(e for e in result["artifacts"] if e["id"] == "extraction-feedback")
            (Path(result["artifacts_directory"]) / entry["relative_path"]).write_bytes(b"")
            entry.update(bytes=0, sha256=hashlib.sha256(b"").hexdigest())
            return result
        run = self.run_lvs(empty_feedback)
        self.assertEqual(run["review_status"], "Accepted")
        raw, _ = self.manager.artifact_bytes(run["id"], "extraction-feedback")
        self.assertEqual(raw, b"")
        reopened = self.new_manager(); self.addCleanup(reopened.close)
        self.assertEqual(reopened.run(run["id"])["review_status"], "Accepted")

    def test_artifact_paths_duplicate_ids_boolean_lengths_and_header_injection_rejected(self):
        run = self.run_lvs()
        mutations = (lambda r: r["artifacts"][0].update(relative_path="../state.json"), lambda r: r["artifacts"].append(copy.deepcopy(r["artifacts"][0])),
            lambda r: r["artifacts"][0].update(bytes=True), lambda r: r["artifacts"][0].update(relative_path="C:/outside"),
            lambda r: r["artifacts"][0].update(content_type="text/plain\r\nInjected: yes"))
        for mutate in mutations:
            result = copy.deepcopy(run["checks"]); mutate(result)
            with self.subTest(mutation=mutate), self.assertRaises(DomainError): validate_artifact_manifest(result)

    def test_rehashed_history_source_drc_powered_origin_epoch_and_policy_tamper_rejected(self):
        self.run_lvs(); original = self.manager.path.read_bytes()
        mutations = (lambda r: r["layout_snapshot"].update(global_rtl="fabricated"), lambda r: r["drc_snapshot"].update(layout_record_sha256="0" * 64),
            lambda r: r["source_identity"].update(drc_source_epoch=True), lambda r: r["source_identity"].update(physical_source_epoch=True),
            lambda r: r["source_inputs"]["powered_netlist"].update(origin="retained_at_S11"),
            lambda r: r["source_inputs"]["netlist"].update(sha256="0" * 64), lambda r: r["runtime_configuration"]["profile"].update(kind="other"),
            lambda r: r.update(evidence_kind="trusted_fixed_lvs_execution"), lambda r: r["drc_adoption"].update(actor="fabricated"))
        for mutate in mutations:
            state = json.loads(original); mutate(state["runs"][0]); run = state["runs"][0]
            run["record_hash"] = object_hash({k: v for k, v in run.items() if k != "record_hash"})
            self.manager.path.write_text(json.dumps(state), encoding="utf-8")
            with self.subTest(mutation=mutate), self.assertRaises(DomainError): self.new_manager()
        self.manager.path.write_bytes(original)

    def test_cancel_busy_restart_never_resends_and_unverified_restart_blocks(self):
        entered = threading.Event(); release = threading.Event(); calls = []
        def slow(*args, **kwargs):
            calls.append("SOFTWARE QA"); entered.set(); release.wait(5); return fixture_runner(*args, **kwargs)
        self.manager._runner = slow; self.manager.start("lvs", self.layout["id"], self.drc_run["id"]); self.assertTrue(entered.wait(5))
        identifier = self.manager._state["runs"][-1]["id"]
        with self.assertRaises(DomainError): self.manager.start("lvs", self.layout["id"], self.drc_run["id"])
        self.manager.cancel(identifier); release.set(); self.manager._worker.join(10)
        self.assertEqual(self.manager.run(identifier)["execution_status"], "Cancelled")
        state = json.loads(self.manager.path.read_text()); state["runs"][0]["execution_status"] = "Running"
        state["runs"][0]["record_hash"] = object_hash({k: v for k, v in state["runs"][0].items() if k != "record_hash"})
        self.manager.path.write_text(json.dumps(state), encoding="utf-8")
        reopened = self.new_manager(runner=slow); self.addCleanup(reopened.close)
        self.assertEqual(reopened.run(identifier)["execution_status"], "Interrupted"); self.assertTrue(reopened.is_active())
        self.assertFalse(reopened.envelope()["lvs_workflow"]["ready"]); self.assertEqual(len(calls), 1)
        with self.assertRaises(DomainError): reopened.start("lvs", self.layout["id"], self.drc_run["id"])

    def test_terminal_unresolved_cleanup_blocks_execution_and_adoption_after_restart(self):
        def unresolved(*args, **kwargs):
            result = fixture_runner(*args, **kwargs); result["cleanup_unresolved"] = True; return result
        run = self.run_lvs(unresolved)
        self.assertEqual(run["execution_status"], "Failed"); self.assertTrue(run["checks"]["cleanup_unresolved"])
        reopened = self.new_manager(runner=unresolved); self.addCleanup(reopened.close)
        for manager in (self.manager, reopened):
            self.assertTrue(manager.is_active()); self.assertFalse(manager.envelope()["lvs_workflow"]["ready"])
            with self.assertRaises(DomainError) as blocked: manager.start("lvs", self.layout["id"], self.drc_run["id"])
            self.assertEqual(blocked.exception.code, "lvs_cleanup_unresolved"); self.assertFalse(manager._state["reviews"])

    def test_return_to_drc_and_save_failure_do_not_fake_a_review_or_revive_superseded(self):
        run = self.run_lvs()
        with self.assertRaises(DomainError): self.manager.review(run["id"], "return_to_stage", "future", "post_layout_verification")
        original = self.manager.path.read_bytes()
        with patch("hullcirq.lvs_workflow.os.replace", side_effect=OSError("SOFTWARE QA disk failure")):
            with self.assertRaises(OSError): self.manager.review(run["id"], "changes_requested", "SOFTWARE QA save failure")
        self.assertEqual(self.manager.path.read_bytes(), original); self.assertEqual(self.manager.run(run["id"])["review_status"], "Accepted")
        self.manager.review(run["id"], "return_to_stage", "SOFTWARE QA return", "drc")
        self.assertEqual(self.manager.run(run["id"])["review_status"], "Changes Requested")
        self.run_lvs()
        with self.assertRaises(DomainError): self.manager.review(run["id"], "accepted", "old")

    def test_earlier_active_tool_and_fixture_promotion_block_before_runner(self):
        active_job = copy.deepcopy(self.base.base.global_manager._state["jobs"][-1]); active_job["execution_status"] = "Running"
        self.base.base.global_manager._state["jobs"].append(active_job)
        try:
            with self.assertRaises(DomainError): self.manager.start("lvs", self.layout["id"], self.drc_run["id"])
        finally: self.base.base.global_manager._state["jobs"].pop()
        self.manager._injected = False
        with patch.object(self.manager, "_capability", return_value={"available": True}):
            with self.assertRaises(DomainError) as blocked: self.manager.start("lvs", self.layout["id"], self.drc_run["id"])
            self.assertEqual(blocked.exception.code, "lvs_sources_not_current")


if __name__ == "__main__": unittest.main()

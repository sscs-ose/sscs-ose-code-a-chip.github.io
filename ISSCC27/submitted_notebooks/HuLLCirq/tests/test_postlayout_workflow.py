"""S14 isolated workflow QA. Every tool result is an explicit software double."""
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
import test_lvs_workflow as fixtures
from hullcirq.domain import DomainError
from hullcirq.postlayout_workflow import (PostLayoutWorkflowManager, FILE_IDS, REQUIRED_FILES, STAGE,
    validate_artifact_manifest, validate_postlayout_proof, validate_source_snapshot)
from hullcirq.store import strict_loads
from hullcirq.verification import object_hash


def fixture_inputs(layout, configuration):
    values = fixtures.fixture_inputs(layout)
    for name in ("sdf", "cell_models", "timed_adapter"):
        raw = ("SOFTWARE QA INPUT: " + name).encode()
        values[name] = {"id": name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                        "origin": "SOFTWARE_QA_ONLY"}
    return values


def fixture_validator(result, lvs, drc, layout, configuration):
    if result.get("software_qa_fixture") is not True or result.get("fixture_marker") != "no_actual_dynamic_simulation":
        raise DomainError("fixture_proof_invalid", "SOFTWARE QA marker missing")


def fixture_runner(lvs, drc, layout, configuration, cancel_event=None):
    folder = Path(tempfile.mkdtemp(prefix="postlayout-software-fixture-", dir=configuration["working_directory"]))
    artifacts = []
    for identifier in sorted(FILE_IDS):
        raw = ("SOFTWARE QA ONLY: " + identifier + "\r\n").encode()
        (folder / identifier).write_bytes(raw)
        artifacts.append({"id": identifier, "relative_path": identifier, "sha256": hashlib.sha256(raw).hexdigest(),
                          "bytes": len(raw), "content_type": "text/plain; charset=utf-8"})
    inputs = fixture_inputs(layout, configuration)
    return {"status": "Completed", "validation_status": "Passed", "origin": "SOFTWARE_QA_NO_SIMULATION", "software_qa_fixture": True,
            "fixture_marker": "no_actual_dynamic_simulation", "executed": True, "exit_code": 0,
            "layout_run_id": layout["id"], "layout_record_sha256": object_hash(layout),
            "drc_run_id": drc["id"], "drc_record_sha256": object_hash(drc),
            "lvs_run_id": lvs["id"], "lvs_record_sha256": object_hash(lvs),
            "input_gds_sha256": inputs["gds"]["sha256"], "input_netlist_sha256": inputs["netlist"]["sha256"],
            "configuration_sha256": object_hash(configuration),
            **{k: layout[k] for k in ("verification_plan_sha256", "vector_hash", "testbench_sha256", "public_boundary_vector_hash")},
            "artifacts_directory": str(folder), "artifacts": artifacts,
            "commands": [{"executed": True, "status": "Completed", "exit_code": 0, "command": ["SOFTWARE_QA_NO_EXECUTION"], "stdout": "SOFTWARE QA", "stderr": ""}],
            "stdout": "SOFTWARE QA", "stderr": "", "metrics": {"software_qa_fixture": True}, "diagnostics": [],
            "checks": {name: {"validation_status": "Passed"} for name in ("source_identity", "configuration", "annotation", "functional", "timing_checks")}}


class PostLayoutWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.LvsWorkflowTests("runTest"); self.base.setUp(); self.addCleanup(self.base.doCleanups)
        self.store, self.lvs, self.drc, self.physical = self.base.store, self.base.manager, self.base.drc, self.base.physical
        self.lvs_run = self.base.run_lvs(); self.layout, self.drc_run = self.base.layout, self.base.drc_run
        directory = Path(self.base.configuration["working_directory"]).parent / "postlayout-artifacts"; directory.mkdir()
        self.configuration = {"version": "SOFTWARE_QA_ONLY", "working_directory": str(directory), "profile": {"kind": "SOFTWARE_QA_ONLY"}}
        self.patch_inputs = patch("hullcirq.postlayout_workflow._source_inputs", side_effect=fixture_inputs)
        self.patch_inputs.start(); self.addCleanup(self.patch_inputs.stop)
        self.manager = self.new_manager(); self.addCleanup(self.manager.close)

    def new_manager(self, runner=fixture_runner, validator=fixture_validator):
        return PostLayoutWorkflowManager(self.store, self.lvs, self.configuration, runner, validator)

    def run_postlayout(self, runner=None):
        if runner is not None: self.manager._runner = runner
        self.manager.start(STAGE, self.layout["id"], self.drc_run["id"], self.lvs_run["id"], self.layout["revision_id"])
        self.manager._worker.join(20); self.assertFalse(self.manager._worker.is_alive())
        return self.manager.run(self.manager._state["runs"][-1]["id"])

    def test_triple_adoption_exact_original_plan_policy_restart_and_upstream_bytes(self):
        paths = [m.path for m in (self.lvs, self.drc, self.physical)] + [self.store.state_path]
        before = [p.read_bytes() for p in paths]
        run = self.run_postlayout()
        self.assertEqual((run["execution_status"], run["validation_status"], run["review_status"], run["freshness"]), ("Completed", "Passed", "Accepted", "Current"))
        for name, manager in (("lvs", self.lvs), ("drc", self.drc), ("layout", self.physical)):
            self.assertEqual(run[name + "_snapshot"], manager._run(run[name + "_run_id"]))
        self.assertEqual(run["verification_plan"], self.layout["verification_plan"])
        validate_source_snapshot(run); validate_postlayout_proof(run, fixture_validator)
        self.assertEqual(before, [p.read_bytes() for p in paths]); self.assertEqual(self.manager.path.name, "postlayout_workflow.json")
        self.assertEqual(self.manager._state["reviews"][-1]["actor"], "automation_policy")
        reopened = self.new_manager(); self.addCleanup(reopened.close)
        self.assertEqual(reopened.envelope()["postlayout_workflow"]["accepted_run_id"], run["id"])

    def test_wrong_stage_each_source_and_revision_rejected_before_tool(self):
        args = [STAGE, self.layout["id"], self.drc_run["id"], self.lvs_run["id"], self.layout["revision_id"]]
        with patch.object(self.manager, "_runner") as runner:
            for i in range(5):
                invalid = args.copy(); invalid[i] = "SOFTWARE_QA_WRONG"
                with self.subTest(field=i), self.assertRaises(DomainError): self.manager.start(*invalid)
            runner.assert_not_called()
        self.assertFalse(self.manager._state["runs"])

    def test_lvs_withdraw_restore_stales_old_postlayout_and_prevents_readoption(self):
        run = self.run_postlayout()
        self.lvs.review(self.lvs_run["id"], "changes_requested", "SOFTWARE QA withdraw")
        self.assertEqual(self.manager.run(run["id"])["freshness"], "Stale")
        self.lvs.review(self.lvs_run["id"], "accepted", "SOFTWARE QA explicit reaccept")
        self.assertEqual(self.manager.run(run["id"])["review_status"], "Awaiting Review")
        with self.assertRaises(DomainError): self.manager.review(run["id"], "accepted", "")
        reopened = self.new_manager(); self.addCleanup(reopened.close)
        self.assertEqual(reopened.run(run["id"])["freshness"], "Stale")

    def test_profile_roundtrip_and_new_timing_input_hash_change_never_revive(self):
        run = self.run_postlayout(); original = copy.deepcopy(self.manager.tool_configuration)
        self.manager.tool_configuration["profile"]["kind"] = "SOFTWARE_QA_CHANGED"
        self.assertEqual(self.manager.run(run["id"])["freshness"], "Stale")
        self.manager.tool_configuration = original
        self.assertEqual(self.manager.run(run["id"])["freshness"], "Stale")
        def changed(layout, config):
            data = fixture_inputs(layout, config); data["sdf"]["sha256"] = "a" * 64; return data
        with patch("hullcirq.postlayout_workflow._source_inputs", side_effect=changed):
            self.assertEqual(self.manager.run(run["id"])["freshness"], "Stale")
        self.assertEqual(self.manager.run(run["id"])["freshness"], "Stale")

    def test_unsupported_is_retained_unadopted_with_all_raw_evidence(self):
        def unsupported(*args, **kwargs):
            result = fixture_runner(*args, **kwargs); result["validation_status"] = "Unsupported"
            result["checks"]["timing_checks"]["validation_status"] = "Unsupported"; return result
        run = self.run_postlayout(unsupported)
        self.assertEqual((run["execution_status"], run["validation_status"], run["review_status"]), ("Completed", "Unsupported", "Awaiting Review"))
        self.assertFalse(self.manager._state["reviews"]); self.assertEqual(set(FILE_IDS), {e["id"] for e in run["checks"]["artifacts"]})
        with self.assertRaises(DomainError): self.manager.review(run["id"], "accepted", "")

    def test_preflight_without_simulator_execution_is_unsupported_unadopted(self):
        def preflight(*args, **kwargs):
            result = fixture_runner(*args, **kwargs)
            result.update(validation_status="Unsupported", executed=False, commands=[], exit_code=None,
                          execution_scope="compatibility_preflight_only")
            for key in ("annotation", "functional", "timing_checks"):
                result["checks"][key] = {"validation_status": "Unsupported", "executed": False}
            return result
        run = self.run_postlayout(preflight)
        self.assertEqual((run["execution_status"], run["validation_status"], run["review_status"]), ("Completed", "Unsupported", "Awaiting Review"))
        self.assertIs(run["checks"]["executed"], False); self.assertFalse(run["checks"]["commands"])
        self.assertFalse(self.manager._state["reviews"])
        with self.assertRaises(DomainError): self.manager.review(run["id"], "accepted", "")

    def test_incomplete_passed_checks_or_wrong_original_hash_cannot_adopt(self):
        for name in ("timing_checks", "annotation", "functional", "vector_hash"):
            def invalid(*args, **kwargs):
                result = fixture_runner(*args, **kwargs)
                if name == "vector_hash": result[name] = "f" * 64
                else: result["checks"][name]["validation_status"] = "Unsupported"
                return result
            with self.subTest(field=name):
                run = self.run_postlayout(invalid)
                self.assertEqual((run["execution_status"], run["validation_status"], run["review_status"]), ("Failed", "Not Checked", "Awaiting Review"))
                self.assertEqual(run["error"]["code"], "postlayout_proof_conflict")
        self.assertFalse(self.manager._state["reviews"])

    def test_retained_artifact_bytes_traversal_missing_and_hash_tamper(self):
        run = self.run_postlayout()
        for entry in run["checks"]["artifacts"]:
            raw, mime = self.manager.artifact_bytes(run["id"], entry["id"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), entry["sha256"])
            self.assertEqual(mime, entry["content_type"])
        for name in ("../state.json", "arbitrary", "runtime_configuration.profile"):
            with self.assertRaises(DomainError): self.manager.artifact_bytes(run["id"], name)
        result = copy.deepcopy(run["checks"]); result["artifacts"][0]["relative_path"] = "../outside"
        with self.assertRaises(DomainError): validate_artifact_manifest(result)
        target = Path(run["checks"]["artifacts_directory"]) / "input-sdf"; target.write_bytes(b"SOFTWARE QA tamper")
        with self.assertRaises(DomainError): self.manager.artifact_bytes(run["id"], "input-sdf")
        with self.assertRaises(DomainError): self.manager.review(run["id"], "accepted", "")

    def test_missing_required_report_is_never_a_pass(self):
        def incomplete(*args, **kwargs):
            result = fixture_runner(*args, **kwargs)
            result["artifacts"] = [e for e in result["artifacts"] if e["id"] != "annotation-report"]; return result
        run = self.run_postlayout(incomplete)
        self.assertEqual(run["execution_status"], "Failed"); self.assertEqual(run["error"]["code"], "postlayout_artifact_missing")
        self.assertFalse(self.manager._state["reviews"])

    def test_cancel_unresolved_cleanup_still_blocks_after_restart(self):
        entered = threading.Event(); release = threading.Event()
        def cancellable(*args, cancel_event=None, **kwargs):
            entered.set(); release.wait(5)
            result = fixture_runner(*args, cancel_event=cancel_event, **kwargs)
            result.update(status="Cancelled", validation_status="Not Checked", cleanup_unresolved=True); return result
        self.manager._runner = cancellable
        self.manager.start(STAGE, self.layout["id"], self.drc_run["id"], self.lvs_run["id"])
        self.assertTrue(entered.wait(5)); identifier = self.manager._state["runs"][-1]["id"]
        self.manager.cancel(identifier); release.set(); self.manager._worker.join(10)
        self.assertTrue(self.manager.is_active()); self.assertEqual(self.manager.run(identifier)["execution_status"], "Cancelled")
        self.assertFalse(self.manager.envelope()["postlayout_workflow"]["ready"])
        with self.assertRaises(DomainError): self.manager.start(STAGE, self.layout["id"], self.drc_run["id"], self.lvs_run["id"])
        reopened = self.new_manager(); self.addCleanup(reopened.close); self.assertTrue(reopened.is_active())

    def test_foreign_upstream_input_descriptor_rejected_without_new_history(self):
        def invalid(layout, config):
            inputs = fixture_inputs(layout, config); inputs["netlist"]["sha256"] = "a" * 64; return inputs
        with patch("hullcirq.postlayout_workflow._source_inputs", side_effect=invalid), patch.object(self.manager, "_runner") as runner:
            with self.assertRaises(DomainError): self.manager.start(STAGE, self.layout["id"], self.drc_run["id"], self.lvs_run["id"])
            runner.assert_not_called()
        self.assertFalse(self.manager._state["runs"])

    def test_explicit_double_cannot_remove_its_fixture_origin(self):
        def forged(*args, **kwargs):
            result = fixture_runner(*args, **kwargs); result["software_qa_fixture"] = False
            result["origin"] = "trusted_fixed_postlayout_adapter"; return result
        run = self.run_postlayout(forged)
        self.assertEqual(run["execution_status"], "Failed")
        self.assertEqual(run["error"]["code"], "postlayout_proof_conflict")
        self.assertFalse(self.manager._state["reviews"])

    def test_invalid_policy_proof_and_failed_persistence_never_adopt(self):
        def validator(*args): raise DomainError("software_qa_proof_rejected", "SOFTWARE QA validator deliberately rejects")
        self.manager._validator = validator
        run = self.run_postlayout()
        self.assertEqual(run["execution_status"], "Failed"); self.assertFalse(self.manager._state["reviews"])
        before = self.manager.path.read_bytes()
        with patch("hullcirq.postlayout_workflow._replace_with_windows_retry", side_effect=OSError("SOFTWARE QA deliberate storage failure")):
            with self.assertRaises(OSError): self.manager.start(STAGE, self.layout["id"], self.drc_run["id"], self.lvs_run["id"])
        self.assertEqual(self.manager.path.read_bytes(), before)
        self.assertEqual(len(self.manager._state["runs"]), 1)

    def test_returns_s01_to_s13_and_fixed_json_preserve_original_plan(self):
        run = self.run_postlayout()
        self.assertEqual(self.manager.artifact(run["id"], "verification-plan"), self.layout["verification_plan"])
        self.assertEqual(self.manager.artifact(run["id"], "lvs-record"), self.lvs._run(self.lvs_run["id"]))
        for target in ("lvs", "layout", "global_rtl_generation"):
            self.manager.review(run["id"], "return_to_stage", "SOFTWARE QA correction", target)
        with self.assertRaises(DomainError): self.manager.review(run["id"], "return_to_stage", "SOFTWARE QA invalid", STAGE)
        with self.assertRaises(DomainError): self.manager.artifact(run["id"], "source_identity.any_expression")

    def test_gui_profile_preparation_is_read_only_preflight_and_persists_outside_store(self):
        profile_path = Path(self.base.configuration["working_directory"]).parent / "host-runtime" / "postlayout_runtime.json"
        work_path = profile_path.parent / "runs"
        manager = PostLayoutWorkflowManager(
            self.store, self.lvs, None,
            compiler_configuration={"kind": "SOFTWARE_QA_PINNED_COMPILER"},
            configuration_path=profile_path,
            profile_working_directory=work_path)
        self.addCleanup(manager.close)
        current, managers, records, adoptions = self.manager._adopted_sources_locked()
        adopted = (current, managers, records, adoptions)
        candidate = {"execution_scope": "post_route_functional_plus_sta", "verification_supported": True,
                     "working_directory": str(work_path), "software_qa_fixture": True}
        before = [len(manager._state["runs"]), len(manager._state["reviews"])]
        with (patch.object(manager, "_adopted_sources_locked", return_value=adopted),
              patch.object(manager, "_validate_sources"),
              patch("hullcirq.postroute_tools.prepare_configuration", return_value=candidate, create=True) as prepare,
              patch("hullcirq.postroute_tools.runtime_descriptor", return_value={"available": True, "verification_supported": True,
                    "execution_scope": "post_route_functional_plus_sta"})):
            result = manager.prepare_profile(self.layout["id"], self.drc_run["id"], self.lvs_run["id"], self.layout["revision_id"])
        self.assertEqual(strict_loads(profile_path.read_text(encoding="utf-8")), candidate)
        self.assertEqual(manager.tool_configuration, candidate)
        self.assertEqual([len(manager._state["runs"]), len(manager._state["reviews"])], before)
        self.assertTrue(result["postlayout_workflow"]["profile_prepare_available"])
        self.assertEqual(result["postlayout_workflow"]["profile_configuration_source"], "workspace_profile")
        prepare.assert_called_once()
        self.assertEqual(prepare.call_args.args[0]["id"], self.layout["id"])
        self.assertEqual(prepare.call_args.args[1:], ({"kind": "SOFTWARE_QA_PINNED_COMPILER"}, work_path))

    def test_explicit_and_injected_profiles_cannot_be_replaced_by_gui(self):
        self.assertFalse(self.manager.envelope()["postlayout_workflow"]["profile_prepare_available"])
        self.assertFalse(self.manager.envelope()["postlayout_workflow"]["profile_update_available"])
        self.assertFalse(self.manager.envelope()["postlayout_workflow"]["profile_prepare_needed"])
        with self.assertRaises(DomainError) as caught:
            self.manager.prepare_profile(self.layout["id"], self.drc_run["id"], self.lvs_run["id"], self.layout["revision_id"])
        self.assertEqual(caught.exception.code, "postlayout_profile_prepare_unavailable")

    def test_host_profile_v2_is_retained_until_explicit_preparation_updates_it_to_v3(self):
        from hullcirq.postroute_tools import PROFILE_V2, PROFILE_V3
        profile_path = Path(self.base.configuration["working_directory"]).parent / "host-upgrade" / "postlayout_runtime.json"
        work_path = profile_path.parent / "runs"
        compiler = {"kind": "SOFTWARE_QA_PINNED_COMPILER"}
        legacy = {"execution_scope": "post_route_functional_plus_sta", "profile_version": PROFILE_V2,
                  "verification_supported": True, "compiler": compiler, "working_directory": str(work_path),
                  "physical_runtime": copy.deepcopy(self.physical.tool_configuration)}
        profile_path.parent.mkdir()
        raw = json.dumps(legacy).encode(); profile_path.write_bytes(raw)
        capability = {"available": True, "verification_supported": True, "execution_scope": "post_route_functional_plus_sta"}
        paths = [manager.path for manager in (self.physical, self.drc, self.lvs)] + [self.store.state_path]
        preserved = [path.read_bytes() for path in paths]
        with patch("hullcirq.postroute_tools.runtime_descriptor", return_value=capability):
            manager = PostLayoutWorkflowManager(self.store, self.lvs, compiler_configuration=compiler,
                configuration_path=profile_path, profile_working_directory=work_path)
            self.addCleanup(manager.close)
            initial = manager.envelope()["postlayout_workflow"]
            self.assertTrue(initial["tool_ready"])
            self.assertTrue(initial["profile_update_available"])
            self.assertFalse(initial["profile_prepare_needed"])
            self.assertEqual(manager.tool_configuration, legacy)
            self.assertEqual(profile_path.read_bytes(), raw)
            self.assertFalse(manager._state["runs"])
            candidate = {**legacy, "profile_version": PROFILE_V3, "annotation_policy": "SOFTWARE_QA_NEW_POLICY"}
            adopted = self.manager._adopted_sources_locked()
            with patch.object(manager, "_adopted_sources_locked", return_value=adopted), \
                    patch.object(manager, "_validate_sources"), \
                    patch("hullcirq.postroute_tools.prepare_configuration", return_value=candidate):
                updated = manager.prepare_profile(self.layout["id"], self.drc_run["id"], self.lvs_run["id"], self.layout["revision_id"])["postlayout_workflow"]
            self.assertFalse(updated["profile_update_available"])
            self.assertEqual(strict_loads(profile_path.read_text(encoding="utf-8")), candidate)
            self.assertFalse(manager._state["runs"])
            reopened = PostLayoutWorkflowManager(self.store, self.lvs, compiler_configuration=compiler,
                configuration_path=profile_path, profile_working_directory=work_path)
            self.addCleanup(reopened.close)
            self.assertEqual(reopened.tool_configuration, candidate)
            self.assertFalse(reopened._profile_update_available())
            original_physical = copy.deepcopy(self.physical.tool_configuration)
            self.physical.tool_configuration = {**original_physical, "software_qa_new_physical_runtime": True}
            try:
                self.assertTrue(reopened._profile_prepare_needed())
                self.assertEqual(reopened.tool_configuration, candidate)
                explicit = PostLayoutWorkflowManager(self.store, self.lvs, legacy, compiler_configuration=compiler,
                    configuration_path=profile_path, profile_working_directory=work_path)
                self.addCleanup(explicit.close)
                self.assertFalse(explicit._profile_update_available())
                self.assertFalse(explicit._profile_prepare_needed())
                self.assertEqual(explicit.tool_configuration, legacy)
            finally: self.physical.tool_configuration = original_physical
        self.assertEqual(preserved, [path.read_bytes() for path in paths])

    def test_valid_json_but_incomplete_saved_profile_is_recoverable_without_rewriting_it(self):
        from hullcirq.postroute_tools import PROFILE_V2
        profile_path = Path(self.base.configuration["working_directory"]).parent / "host-incomplete" / "postlayout_runtime.json"
        work_path = profile_path.parent / "runs"
        compiler = {"kind": "SOFTWARE_QA_PINNED_COMPILER"}
        profile_path.parent.mkdir()
        # Pass the outer profile contract but omit required physical/runtime data.
        raw = json.dumps({"execution_scope": "post_route_functional_plus_sta", "profile_version": PROFILE_V2,
                          "verification_supported": True, "compiler": compiler, "working_directory": str(work_path)}).encode()
        profile_path.write_bytes(raw)
        manager = PostLayoutWorkflowManager(self.store, self.lvs, compiler_configuration=compiler,
            configuration_path=profile_path, profile_working_directory=work_path)
        self.addCleanup(manager.close)
        value = manager.envelope()["postlayout_workflow"]
        self.assertIsNone(manager.tool_configuration)
        self.assertFalse(value["tool_ready"])
        self.assertFalse(value["ready"])
        self.assertTrue(value["profile_prepare_available"])
        self.assertEqual(value["profile_configuration_error"]["code"], "postlayout_configuration_invalid")
        self.assertEqual(profile_path.read_bytes(), raw)
        self.assertFalse(manager._state["runs"])

    def test_copied_profile_cannot_reuse_another_system_run_directory_or_compiler(self):
        from hullcirq.postroute_tools import PROFILE_V2
        profile_path = Path(self.base.configuration["working_directory"]).parent / "host-scoped" / "postlayout_runtime.json"
        work_path = profile_path.parent / "runs"
        compiler = {"kind": "SOFTWARE_QA_PINNED_COMPILER"}
        profile_path.parent.mkdir()
        original = {"execution_scope": "post_route_functional_plus_sta", "profile_version": PROFILE_V2,
                    "verification_supported": True, "compiler": compiler, "working_directory": str(work_path)}
        for field, replacement in (("working_directory", str(profile_path.parent.parent / "another-system" / "runs")),
                                   ("compiler", {"kind": "SOFTWARE_QA_OTHER_COMPILER"})):
            raw = json.dumps({**original, field: replacement}).encode()
            profile_path.write_bytes(raw)
            with self.subTest(field=field):
                manager = PostLayoutWorkflowManager(self.store, self.lvs, compiler_configuration=compiler,
                    configuration_path=profile_path, profile_working_directory=work_path)
                self.addCleanup(manager.close)
                self.assertIsNone(manager.tool_configuration)
                self.assertEqual(manager._configuration_error["code"], "postlayout_profile_scope_conflict")
                self.assertTrue(manager.envelope()["postlayout_workflow"]["profile_prepare_available"])
                self.assertEqual(profile_path.read_bytes(), raw)

    def test_missing_runtime_inputs_block_source_without_hiding_unexpected_errors(self):
        for error in (FileNotFoundError("SOFTWARE QA removed runtime"), KeyError("SOFTWARE QA missing runtime field")):
            with self.subTest(error=type(error).__name__), \
                    patch("hullcirq.postlayout_workflow._source_inputs", side_effect=error):
                value = self.manager.envelope()["postlayout_workflow"]
                self.assertFalse(value["ready"])
                self.assertIn("missing, unreadable or inconsistent", value["blocked_reason"])
                self.assertFalse(self.manager._state["runs"])
        with patch("hullcirq.postlayout_workflow._source_inputs", side_effect=RuntimeError("SOFTWARE QA unexpected")), \
                self.assertRaises(RuntimeError):
            self.manager.envelope()

    def test_separate_termination_audit_preserves_failed_run_and_survives_restart_feedback(self):
        from hullcirq.postlayout_cleanup import execution_hash
        def unresolved(*args, **kwargs):
            value = fixture_runner(*args, **kwargs)
            value["cleanup_unresolved"] = True
            return value
        decorated = self.run_postlayout(unresolved)
        identifier = decorated["id"]
        original = copy.deepcopy(self.manager._run(identifier))
        def saved_proof(run):
            return {"software_qa_fixture": True, "execution_sha256": execution_hash(run), "raw_hash": "a"*64}
        with patch("hullcirq.postlayout_cleanup.termination_evidence", side_effect=saved_proof):
            self.assertTrue(self.manager.is_active())
            self.manager.verify_saved_termination(identifier)
            self.assertEqual(self.manager._run(identifier), original)
            self.assertFalse(self.manager.is_active())
            self.assertEqual(len(self.manager._state["cleanup_resolutions"]), 1)
            self.assertEqual(self.manager._state["cleanup_resolutions"][0]["original_run_record_sha256"], original["record_hash"])
            with self.assertRaises(DomainError): self.manager.verify_saved_termination(identifier)
            self.configuration["version"] = "SOFTWARE_QA_CURRENT_RUNTIME_CHANGED"
            reopened = self.new_manager(); self.addCleanup(reopened.close)
            self.assertFalse(reopened.is_active())
            self.assertEqual(reopened._run(identifier), original)
            reopened.review(identifier, "changes_requested", "SOFTWARE QA preserved failure; retry after runtime fix")
            self.assertFalse(reopened.is_active())
            self.assertEqual(reopened._run(identifier)["checks"], original["checks"])
            self.assertEqual(reopened._run(identifier)["execution_status"], "Failed")
            self.assertEqual(reopened._run(identifier)["validation_status"], "Not Checked")

    def test_saved_termination_evidence_is_revalidated_on_admission_and_restart(self):
        from hullcirq.postlayout_cleanup import execution_hash
        def unresolved(*args, **kwargs):
            value = fixture_runner(*args, **kwargs); value["cleanup_unresolved"] = True; return value
        identifier = self.run_postlayout(unresolved)["id"]
        token = {"raw_hash": "a"*64}
        with patch("hullcirq.postlayout_cleanup.termination_evidence", side_effect=lambda run:
                   {**token, "software_qa_fixture": True, "execution_sha256": execution_hash(run)}):
            self.manager.verify_saved_termination(identifier)
            self.assertFalse(self.manager.is_active())
            token["raw_hash"] = "b"*64
            self.assertTrue(self.manager.is_active())
            with self.assertRaises(DomainError) as caught: self.new_manager()
            self.assertEqual(caught.exception.code, "invalid_postlayout_workflow_store")


if __name__ == "__main__": unittest.main()

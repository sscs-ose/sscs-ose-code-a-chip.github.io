"""Isolated host-profile QA; no model, EDA, browser or live design is used."""
import copy
from contextlib import ExitStack, nullcontext
import hashlib
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from hullcirq.domain import DomainError
from hullcirq import physical_repair_session as session
from hullcirq.verification import object_hash
from hullcirq.workspace_server import _postlayout_profile_directory

ROOT = Path(__file__).resolve().parents[1]


def checksum(record):
    record["record_hash"] = object_hash({key: value for key, value in record.items() if key != "record_hash"})
    return record


class Manager:
    def __init__(self, configuration=None, runs=None):
        self.tool_configuration = copy.deepcopy(configuration)
        self._state = {"runs": runs or []}
        self._storage_error = None
        self._worker = None
        self.lock = threading.RLock()
        self.active = False
        self.current = True
        self.observations = 0

    def is_active(self):
        return self.active

    def observe_design(self):
        self.observations += 1

    def _source_locks(self):
        return nullcontext()

    def _decorate(self, run):
        return {**run, "freshness": "Current" if self.current else "Stale"}


class PhysicalRepairSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".work")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store_path = self.root / "system"
        self.store_path.mkdir()
        self.revision = "software-qa-revision"
        self.design = {"project": {"id": "software-qa-project", "name": "Software QA"},
                       "settings": {"clock_period_ns": 50}, "layout": {"viewport": {"x": 0}}}
        self.snapshots = {self.revision: copy.deepcopy(self.design)}
        self.store = SimpleNamespace(state_path=self.store_path / "state.json",
                                     envelope=lambda: {"revision": {"id": self.revision}, "design": copy.deepcopy(self.design)},
                                     snapshot=lambda identifier: copy.deepcopy(self.snapshots[identifier]))
        physical = {"origin": "SOFTWARE_QA_ONLY", "profile": {"profile_version": "SOFTWARE_QA_ORIGINAL"}}
        self.base = ({"kind": "SOFTWARE_QA_COMPILER"}, {"kind": "SOFTWARE_QA_SYNTHESIZER"}, physical,
                     {"physical_runtime": physical, "profile": {"kind": "SOFTWARE_QA_DRC"}, "working_directory": "old-drc"},
                     {"physical_runtime": physical, "profile": {"kind": "SOFTWARE_QA_LVS"}, "working_directory": "old-lvs"}, None)
        self.records = {name: checksum({"id": "software-qa-" + name, "revision_id": self.revision,
                                       "execution_status": "Completed", "validation_status": "Passed", "review_status": "Accepted",
                                       "runtime_configuration": copy.deepcopy(physical), "settings": {"clock_period_ns": 50}})
                        for name in ("layout", "drc", "lvs")}
        self.records["layout"].update(global_job_id="software-qa-original-job", global_rtl="SOFTWARE_QA_ORIGINAL_RTL",
            global_rtl_sha256="software-qa-rtl-hash", source_manifest={"SOFTWARE_QA_ONLY": True},
            source_manifest_sha256="software-qa-manifest-hash", settings_sha256="software-qa-settings-hash",
            verification_plan={"SOFTWARE_QA_ORIGINAL_JOB": True}, verification_plan_sha256="software-qa-plan-hash",
            vector_hash="software-qa-vector-hash", testbench_sha256="software-qa-testbench-hash",
            public_boundary_vector_hash="software-qa-public-boundary-hash")
        checksum(self.records["layout"])
        self.adoptions = {name: {"run_id": record["id"], "decision": "accepted", "software_qa_fixture": True}
                          for name, record in self.records.items()}
        commands = [{"executed": True, "status": "Completed", "exit_code": 0, "cleanup_unresolved": False} for _ in range(11)]
        checks = {name: {"validation_status": "Failed" if name == "electrical" else "Passed"} for name in session.CHECKS}
        self.failure = checksum({"id": "software-qa-s14", "revision_id": self.revision, "stage_id": "post_layout_verification",
            "execution_status": "Completed", "validation_status": "Failed", "execution_scope": "post_route_functional_plus_sta",
            "verification_supported": True, "evidence_kind": "trusted_fixed_postlayout_execution", "error": None,
            "runtime_configuration": {"SOFTWARE_QA_ONLY": True},
            "checks": {"origin": "trusted_fixed_postlayout_adapter", "execution_scope": "post_route_functional_plus_sta",
                "status": "Completed", "validation_status": "Failed", "executed": True, "exit_code": 0,
                "cleanup_unresolved": False, "commands": commands, "checks": checks},
            **{name + "_snapshot": copy.deepcopy(record) for name, record in self.records.items()},
            **{name + "_adoption": copy.deepcopy(review) for name, review in self.adoptions.items()}})
        self.save_histories()
        self.server = SimpleNamespace(execution_lock=threading.RLock(), store=self.store)
        for name in session.MANAGERS:
            setattr(self.server, name, Manager())
        for name, index in (("physical", 2), ("drc", 3), ("lvs", 4)):
            getattr(self.server, name + "_workflow").tool_configuration = copy.deepcopy(self.base[index])
        self.server.postlayout_workflow._state["runs"] = [copy.deepcopy(self.failure)]
        self.server.postlayout_workflow._adopted_sources_locked = lambda: (self.store.envelope(), {}, self.records, self.adoptions)
        self.server.postlayout_workflow._validate_sources = lambda *args: None
        self.server.workspace = SimpleNamespace(context=SimpleNamespace(), configurations=copy.deepcopy(self.base),
            registry=SimpleNamespace(root=self.root / "workspace"),
            identity={"project_id": "software-qa-project", "system_id": "software-qa-system", "read_only": False})
        self.directory = _postlayout_profile_directory(self.server.workspace.registry.root,
            "software-qa-project", "software-qa-system")
        self.bundle_path = self.directory / session.BUNDLE_NAME
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(session, "ROOT", self.root))
        self.source_validator = self.stack.enter_context(patch("hullcirq.postlayout_workflow.validate_source_snapshot"))
        self.artifact_validator = self.stack.enter_context(patch("hullcirq.postlayout_workflow.validate_artifact_manifest"))
        self.failed_validator = self.stack.enter_context(patch("hullcirq.postroute_tools.validate_failed_postlayout_result"))
        self.builder = self.stack.enter_context(patch("hullcirq.physical_repair.prepare_npu2_configuration", side_effect=self.fixed_builder))
        self.drc_validator = self.stack.enter_context(patch("hullcirq.drc_tools.configuration_projection"))
        self.lvs_validator = self.stack.enter_context(patch("hullcirq.lvs_tools.configuration_projection"))
        self.failed_physical_validator = self.stack.enter_context(patch("hullcirq.physical_workflow.validate_failed_physical_proof"))
        self.retry_builder = self.stack.enter_context(patch("hullcirq.physical_repair.prepare_npu2_retry_configuration",
                                                          side_effect=self.fixed_retry_builder, create=True))
        self.final_builder = self.stack.enter_context(patch("hullcirq.physical_repair.prepare_npu2_final_configuration",
                                                          side_effect=self.fixed_final_builder, create=True))

    def fixed_builder(self, layout, work):
        return {**copy.deepcopy(layout["runtime_configuration"]), "working_directory": str(work),
                "profile": {"profile_version": "hullcirq-sky130-route-repair-npu2v1"},
                "resume": {"SOFTWARE_QA_FIXED_CHECKPOINT": True}}

    def fixed_retry_builder(self, layout, work):
        return {**copy.deepcopy(layout["runtime_configuration"]), "working_directory": str(work),
                "profile": {"profile_version": "hullcirq-sky130-route-repair-npu2v2"},
                "resume": {"SOFTWARE_QA_SECOND_FIXED_CHECKPOINT": True}}

    def fixed_final_builder(self, layout, work):
        return {**copy.deepcopy(layout["runtime_configuration"]), "working_directory": str(work),
                "profile": {"profile_version": "hullcirq-sky130-route-repair-npu2v3"},
                "resume": {"SOFTWARE_QA_THIRD_FIXED_CHECKPOINT": True}}

    def first_layout_failure(self):
        self.prepare()
        run = copy.deepcopy(self.records["layout"])
        configuration = copy.deepcopy(self.server.physical_workflow.tool_configuration)
        run.update(id="software-qa-first-layout-failure", stage_id="layout", validation_status="Failed",
                   review_status="Awaiting Review", error=None, evidence_kind="trusted_fixed_tool_execution",
                   diagnostics=[{"severity": "error", "code": "physical_checks_failed"}],
                   runtime_configuration=configuration, runtime_configuration_sha256=object_hash(configuration),
                   checks={"origin": "trusted_fixed_tool_adapter", "validation_status": "Failed", "executed": True,
                           "exit_code": 0, "cleanup_unresolved": False, "technology_mapping_executed": False,
                           "upstream_technology_mapping_reused": True,
                           "commands": [{"executed": True, "status": "Completed", "exit_code": 0, "cleanup_unresolved": False} for _ in range(2)],
                           "checks": {name: {"validation_status": "Failed" if name == "electrical" else "Passed"}
                                      for name in ("source_identity", "configuration", "routing", "timing", "electrical")},
                           "diagnostics": [{"severity": "error", "code": "physical_checks_failed"}]})
        checksum(run)
        self.save_layout_failure(run)
        return run

    def save_layout_failure(self, run):
        path = self.store_path / "physical_workflow.json"
        records = json.loads(path.read_text(encoding="utf-8"))["runs"]
        records = [record for record in records if record["id"] != run["id"]] + [run]
        (self.store_path / "physical_workflow.json").write_text(json.dumps({"runs": records,
            "reviews": [self.adoptions["layout"]]}), encoding="utf-8")
        self.server.physical_workflow._state["runs"] = copy.deepcopy(records)

    def second_layout_failure(self):
        first = self.first_layout_failure()
        session.prepare_retry(self.server, first["id"], self.revision)
        second = copy.deepcopy(first)
        configuration = copy.deepcopy(self.server.physical_workflow.tool_configuration)
        second.update(id="software-qa-second-layout-failure", runtime_configuration=configuration,
                      runtime_configuration_sha256=object_hash(configuration))
        checksum(second); self.save_layout_failure(second)
        self.first_failure = first
        return second

    def save_histories(self):
        for name, filename in (("layout", "physical_workflow"), ("drc", "drc_workflow"), ("lvs", "lvs_workflow")):
            (self.store_path / (filename + ".json")).write_text(json.dumps({"runs": [self.records[name]], "reviews": [self.adoptions[name]]}), encoding="utf-8")
        (self.store_path / "postlayout_workflow.json").write_text(json.dumps({"runs": [self.failure], "reviews": []}), encoding="utf-8")

    def prepare(self):
        return session.prepare_repair(self.server, self.failure["id"], self.revision)

    def display_save(self):
        self.revision += "-view"
        self.design["layout"]["viewport"]["x"] += 10
        self.design["project"]["name"] += " view"
        self.snapshots[self.revision] = copy.deepcopy(self.design)

    def assert_display_restore_unchanged(self, generation):
        before = {path: path.read_bytes() for path in (*self.directory.iterdir(), *self.store_path.iterdir())}
        proof_calls = self.failed_validator.call_count
        self.display_save()
        restored, status = session.load_repair_configurations(self.store, self.base, self.directory,
                                                             "software-qa-project", "software-qa-system")
        self.assertTrue(status["configured"], status["error"])
        self.assertEqual(status["repair_generation"], generation)
        self.assertGreater(self.failed_validator.call_count, proof_calls)
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        self.assertEqual(restored[2], self.server.physical_workflow.tool_configuration)

    def test_all_three_original_bundles_restore_after_display_only_revisions(self):
        first = self.first_layout_failure()
        self.assert_display_restore_unchanged(1)
        session.prepare_retry(self.server, first["id"], self.revision)
        self.assert_display_restore_unchanged(2)
        second = copy.deepcopy(first)
        configuration = copy.deepcopy(self.server.physical_workflow.tool_configuration)
        second.update(id="software-qa-second-layout-after-view", runtime_configuration=configuration,
                      runtime_configuration_sha256=object_hash(configuration))
        checksum(second); self.save_layout_failure(second)
        session.prepare_retry(self.server, second["id"], self.revision)
        self.assert_display_restore_unchanged(3)
        for name in (session.BUNDLE_NAME, session.RETRY_BUNDLE_NAME, session.FINAL_BUNDLE_NAME):
            self.assertEqual(json.loads((self.directory / name).read_text(encoding="utf-8"))["revision_id"], self.failure["revision_id"])

    def test_initial_prepare_after_display_save_keeps_failure_original_revision(self):
        self.display_save()
        status = self.prepare()
        self.assertTrue(status["configured"])
        self.assertEqual(json.loads(self.bundle_path.read_text(encoding="utf-8"))["revision_id"], self.failure["revision_id"])

    def test_bundle_restore_rejects_semantic_types_missing_snapshot_and_mixed_ancestors(self):
        first = self.first_layout_failure()
        session.prepare_retry(self.server, first["id"], self.revision)
        before = {path: path.read_bytes() for path in self.directory.iterdir()}
        original_design = copy.deepcopy(self.design)
        for period in (51, 50.0):
            self.design["settings"]["clock_period_ns"] = period
            restored, status = session.load_repair_configurations(self.store, self.base, self.directory,
                                                                 "software-qa-project", "software-qa-system")
            self.assertFalse(status["configured"])
            self.assertEqual(restored, self.base)
            self.assertEqual({path: path.read_bytes() for path in before}, before)
        self.design = original_design
        original_snapshot = self.snapshots.pop(self.failure["revision_id"])
        _, status = session.load_repair_configurations(self.store, self.base, self.directory,
                                                      "software-qa-project", "software-qa-system")
        self.assertFalse(status["configured"])
        self.snapshots[self.failure["revision_id"]] = original_snapshot
        retry_path = self.directory / session.RETRY_BUNDLE_NAME
        bundle = json.loads(retry_path.read_text(encoding="utf-8"))
        self.display_save()
        bundle["revision_id"] = self.revision
        checksum(bundle)
        retry_path.write_text(json.dumps(bundle), encoding="utf-8")
        _, status = session.load_repair_configurations(self.store, self.base, self.directory,
                                                      "software-qa-project", "software-qa-system")
        self.assertFalse(status["configured"])

    def test_explicit_prepare_preserves_histories_and_restores_exact_fixed_configs(self):
        before = {path.name: path.read_bytes() for path in self.store_path.iterdir()}
        original_failure = copy.deepcopy(self.server.postlayout_workflow._state["runs"])
        status = self.prepare()
        self.assertTrue(status["configured"])
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.store_path.iterdir()})
        self.assertEqual(original_failure, self.server.postlayout_workflow._state["runs"])
        self.assertFalse(self.bundle_path.is_relative_to(self.store_path))
        self.failed_validator.assert_called_once_with(self.failure["checks"], self.records["lvs"], self.records["drc"],
                                                     self.records["layout"], self.failure["runtime_configuration"])
        self.artifact_validator.assert_called_once_with(self.failure["checks"], True)
        self.builder.assert_called_once_with(self.records["layout"], self.root / ".work/n2r/p")
        for name, child in (("physical", "p"), ("drc", "d"), ("lvs", "l")):
            config = getattr(self.server, name + "_workflow").tool_configuration
            self.assertEqual(config["working_directory"], str(self.root / ".work/n2r" / child))
        self.assertEqual(self.server.drc_workflow.tool_configuration["profile"], self.base[3]["profile"])
        self.assertEqual(self.server.lvs_workflow.tool_configuration["profile"], self.base[4]["profile"])
        restored, reopened_status = session.load_repair_configurations(self.store, self.base, self.directory,
                                                                     "software-qa-project", "software-qa-system")
        self.assertTrue(reopened_status["configured"])
        self.assertEqual(restored[:2], self.base[:2])
        self.assertEqual(restored[5], self.base[5])
        for name, index in (("physical", 2), ("drc", 3), ("lvs", 4)):
            self.assertEqual(restored[index], getattr(self.server, name + "_workflow").tool_configuration)

    def test_readonly_busy_stale_superseded_and_wrong_revision_are_rejected_without_bundle(self):
        cases = ((self.server.workspace.identity, "read_only", True),
                 (self.server.generation, "active", True),
                 (self.server.postlayout_workflow, "current", False),
                 (self.server.drc_workflow, "_storage_error", {"code": "storage_error"}))
        for obj, key, value in cases:
            old = obj[key] if isinstance(obj, dict) else getattr(obj, key)
            if isinstance(obj, dict): obj[key] = value
            else: setattr(obj, key, value)
            with self.subTest(key=key), self.assertRaises(DomainError): self.prepare()
            self.assertFalse(self.bundle_path.exists())
            if isinstance(obj, dict): obj[key] = old
            else: setattr(obj, key, old)
        with self.assertRaises(DomainError): session.prepare_repair(self.server, "earlier-qa-failure", self.revision)
        with self.assertRaises(DomainError): session.prepare_repair(self.server, self.failure["id"], "other-qa-revision")

    def test_partial_other_failure_and_unverified_termination_are_never_repair_sources(self):
        original = copy.deepcopy(self.failure)
        for mutation in (lambda r: r["checks"]["commands"].pop(),
                         lambda r: r["checks"]["checks"]["functional"].update(validation_status="Failed"),
                         lambda r: r["checks"].update(cleanup_unresolved=True),
                         lambda r: r.update(evidence_kind="software_qa_fixture"),
                         lambda r: r["checks"].update(exit_code=False)):
            self.failure = copy.deepcopy(original)
            mutation(self.failure)
            checksum(self.failure)
            self.save_histories()
            self.server.postlayout_workflow._state["runs"] = [copy.deepcopy(self.failure)]
            with self.assertRaises(DomainError): self.prepare()
            self.assertFalse(self.bundle_path.exists())
        self.failed_validator.assert_not_called()

    def test_failed_evidence_validator_rejection_cannot_prepare_or_mutate_runtimes(self):
        self.failed_validator.side_effect = DomainError("software_qa_proof_changed", "SOFTWARE QA deliberate proof failure")
        with self.assertRaises(DomainError): self.prepare()
        self.assertFalse(self.bundle_path.exists())
        self.assertEqual(self.server.physical_workflow.tool_configuration, self.base[2])
        self.builder.assert_not_called()

    def test_incompatible_or_changed_bundle_is_preserved_without_applying_overrides(self):
        self.prepare()
        original = self.bundle_path.read_bytes()
        changed = copy.deepcopy(self.base)
        changed[0]["kind"] = "SOFTWARE_QA_OTHER_COMPILER"
        restored, status = session.load_repair_configurations(self.store, changed, self.directory,
                                                             "software-qa-project", "software-qa-system")
        self.assertFalse(status["configured"])
        self.assertTrue(status["error"])
        self.assertEqual(restored, changed)
        self.assertEqual(self.bundle_path.read_bytes(), original)
        bundle = json.loads(original)
        bundle["configurations"]["physical"]["working_directory"] = str(self.root / "arbitrary")
        checksum(bundle)  # A recomputed checksum cannot authorize a changed runtime.
        self.bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
        raw = self.bundle_path.read_bytes()
        restored, status = session.load_repair_configurations(self.store, self.base, self.directory,
                                                             "software-qa-project", "software-qa-system")
        self.assertFalse(status["configured"])
        self.assertEqual(restored, self.base)
        self.assertEqual(self.bundle_path.read_bytes(), raw)

    def test_saved_source_or_failure_change_invalidates_restore(self):
        self.prepare()
        self.failure["checks"]["commands"][0]["exit_code"] = 1
        checksum(self.failure)
        self.save_histories()
        restored, status = session.load_repair_configurations(self.store, self.base, self.directory,
                                                             "software-qa-project", "software-qa-system")
        self.assertFalse(status["configured"])
        self.assertEqual(restored, self.base)
        self.assertIsNotNone(status["error"])

    def test_later_s14_review_metadata_does_not_revert_the_prepared_runtime(self):
        self.prepare()
        self.failure["review_status"] = "Changes Requested"
        checksum(self.failure)
        self.save_histories()
        restored, status = session.load_repair_configurations(self.store, self.base, self.directory,
                                                             "software-qa-project", "software-qa-system")
        self.assertTrue(status["configured"])
        self.assertNotEqual(restored[2], self.base[2])

    def test_host_bundle_cannot_be_replayed_for_another_project_or_system(self):
        self.prepare()
        original = self.bundle_path.read_bytes()
        for project_id, system_id in (("other-qa-project", "software-qa-system"),
                                      ("software-qa-project", "other-qa-system")):
            restored, status = session.load_repair_configurations(self.store, self.base, self.directory, project_id, system_id)
            self.assertFalse(status["configured"])
            self.assertEqual(restored, self.base)
            self.assertEqual(self.bundle_path.read_bytes(), original)

    def test_atomic_save_failure_changes_no_manager_runtime(self):
        with patch.object(session, "_replace_with_windows_retry", side_effect=OSError("SOFTWARE QA save failure")):
            with self.assertRaises(OSError): self.prepare()
        self.assertFalse(self.bundle_path.exists())
        self.assertEqual(self.server.physical_workflow.tool_configuration, self.base[2])
        self.assertEqual(self.server.drc_workflow.tool_configuration, self.base[3])
        self.assertEqual(self.server.lvs_workflow.tool_configuration, self.base[4])

    def test_second_prepare_preserves_first_bundle_and_reloads_both_fixed_derivations(self):
        failed = self.first_layout_failure()
        first_raw = self.bundle_path.read_bytes()
        histories = {path.name: path.read_bytes() for path in self.store_path.iterdir()}
        status = session.prepare_retry(self.server, failed["id"], self.revision)
        self.assertEqual(status["repair_generation"], 2)
        self.assertEqual(self.bundle_path.read_bytes(), first_raw)
        self.assertEqual(histories, {path.name: path.read_bytes() for path in self.store_path.iterdir()})
        self.failed_physical_validator.assert_called_once()
        self.assertEqual(self.failed_physical_validator.call_args.args[0], failed)
        self.retry_builder.assert_called_once_with(failed, self.root / ".work/n2s/p")
        for name, child in (("physical", "p"), ("drc", "d"), ("lvs", "l")):
            self.assertEqual(getattr(self.server, name + "_workflow").tool_configuration["working_directory"],
                             str(self.root / ".work/n2s" / child))
        restored, reopened = session.load_repair_configurations(self.store, self.base, self.directory,
                                                               "software-qa-project", "software-qa-system")
        self.assertEqual(reopened["repair_generation"], 2)
        self.assertTrue(reopened["configured"])
        self.assertEqual(restored[2], self.server.physical_workflow.tool_configuration)
        self.assertNotEqual(restored[2], self.base[2])

    def test_retry_partial_non_electrical_or_changed_source_failures_are_rejected(self):
        original = self.first_layout_failure()
        for mutation in (lambda r: r["checks"]["commands"].pop(),
                         lambda r: r["checks"]["checks"]["routing"].update(validation_status="Failed"),
                         lambda r: r["checks"].update(cleanup_unresolved=True),
                         lambda r: r["checks"]["diagnostics"][0].update(code="different_error"),
                         lambda r: r.update(global_rtl="SOFTWARE_QA_CHANGED_RTL"),
                         lambda r: r.update(review_status="Accepted")):
            failed = copy.deepcopy(original)
            mutation(failed)
            checksum(failed)
            self.save_layout_failure(failed)
            with self.assertRaises(DomainError): session.prepare_retry(self.server, failed["id"], self.revision)
            self.assertFalse((self.directory / session.RETRY_BUNDLE_NAME).exists())
        self.failed_physical_validator.assert_not_called()

    def test_retry_requires_latest_current_failure_and_exact_first_runtime(self):
        failed = self.first_layout_failure()
        self.server.physical_workflow.current = False
        with self.assertRaises(DomainError): session.prepare_retry(self.server, failed["id"], self.revision)
        self.server.physical_workflow.current = True
        self.server.drc_workflow.tool_configuration["profile"]["kind"] = "SOFTWARE_QA_OTHER_DRC"
        with self.assertRaises(DomainError): session.prepare_retry(self.server, failed["id"], self.revision)
        self.assertFalse((self.directory / session.RETRY_BUNDLE_NAME).exists())

    def test_second_bundle_pins_original_file_bytes_and_never_overwrites_either_bundle(self):
        failed = self.first_layout_failure()
        session.prepare_retry(self.server, failed["id"], self.revision)
        retry_path = self.directory / session.RETRY_BUNDLE_NAME
        retry_raw = retry_path.read_bytes()
        with self.assertRaises(DomainError): session.prepare_retry(self.server, failed["id"], self.revision)
        self.assertEqual(retry_path.read_bytes(), retry_raw)
        self.bundle_path.write_bytes(self.bundle_path.read_bytes() + b"\n")
        changed = self.bundle_path.read_bytes()
        restored, status = session.load_repair_configurations(self.store, self.base, self.directory,
                                                             "software-qa-project", "software-qa-system")
        self.assertFalse(status["configured"])
        self.assertEqual(restored, self.base)
        self.assertEqual(retry_path.read_bytes(), retry_raw)
        self.assertEqual(self.bundle_path.read_bytes(), changed)

    def test_retry_review_metadata_survives_reload_but_failed_proof_rejection_does_not(self):
        failed = self.first_layout_failure()
        session.prepare_retry(self.server, failed["id"], self.revision)
        failed["review_status"] = "Changes Requested"
        checksum(failed)
        self.save_layout_failure(failed)
        restored, status = session.load_repair_configurations(self.store, self.base, self.directory,
                                                             "software-qa-project", "software-qa-system")
        self.assertTrue(status["configured"])
        self.assertEqual(status["repair_generation"], 2)
        self.failed_physical_validator.side_effect = DomainError("software_qa_bad_proof", "SOFTWARE QA altered proof")
        restored, status = session.load_repair_configurations(self.store, self.base, self.directory,
                                                             "software-qa-project", "software-qa-system")
        self.assertFalse(status["configured"])
        self.assertEqual(restored, self.base)

    def test_retry_save_failure_retains_first_configuration_and_first_bundle_bytes(self):
        failed = self.first_layout_failure()
        first_raw = self.bundle_path.read_bytes()
        first_configuration = copy.deepcopy(self.server.physical_workflow.tool_configuration)
        with patch.object(session, "_replace_with_windows_retry", side_effect=OSError("SOFTWARE QA second save failure")):
            with self.assertRaises(OSError): session.prepare_retry(self.server, failed["id"], self.revision)
        self.assertFalse((self.directory / session.RETRY_BUNDLE_NAME).exists())
        self.assertEqual(self.bundle_path.read_bytes(), first_raw)
        self.assertEqual(self.server.physical_workflow.tool_configuration, first_configuration)

    def test_orphan_second_bundle_is_preserved_without_enabling_a_runtime(self):
        self.directory.mkdir(parents=True)
        path = self.directory / session.RETRY_BUNDLE_NAME
        raw = b'{"SOFTWARE_QA_ORPHAN_SECOND_PROFILE":true}\n'
        path.write_bytes(raw)
        restored, status = session.load_repair_configurations(self.store, self.base, self.directory,
                                                             "software-qa-project", "software-qa-system")
        self.assertFalse(status["configured"])
        self.assertTrue(status["bundle_present"])
        self.assertIsNotNone(status["error"])
        self.assertEqual(restored, self.base)
        self.assertEqual(path.read_bytes(), raw)

    def test_third_prepare_preserves_both_ancestors_histories_and_all_distinct_execution_identities(self):
        failed = self.second_layout_failure()
        second_path = self.directory / session.RETRY_BUNDLE_NAME
        first_raw, second_raw = self.bundle_path.read_bytes(), second_path.read_bytes()
        before = {path.name: path.read_bytes() for path in self.store_path.iterdir()}
        second_identity = json.loads(second_raw)["source_identity"]
        self.final_builder.reset_mock()
        status = session.prepare_retry(self.server, failed["id"], self.revision)
        self.assertEqual(status["repair_generation"], 3)
        self.assertEqual(status["profile_version"], "hullcirq-sky130-route-repair-npu2v3")
        self.final_builder.assert_called_once_with(failed, self.root / ".work/n2t/p")
        self.assertEqual(self.bundle_path.read_bytes(), first_raw)
        self.assertEqual(second_path.read_bytes(), second_raw)
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.store_path.iterdir()})
        final_path = self.directory / session.FINAL_BUNDLE_NAME
        bundle = json.loads(final_path.read_text(encoding="utf-8"))
        self.assertEqual(bundle["schema"], session.FINAL_SCHEMA)
        self.assertEqual(bundle["original_bundle_sha256"], hashlib.sha256(first_raw).hexdigest())
        self.assertEqual(bundle["previous_bundle_sha256"], hashlib.sha256(second_raw).hexdigest())
        self.assertTrue(all(bundle["source_identity"][key] == value for key, value in second_identity.items()))
        self.assertEqual(bundle["source_identity"]["failed_layout_run_id"], self.first_failure["id"])
        self.assertEqual(bundle["source_identity"]["failed_second_layout_run_id"], failed["id"])
        for name, child in (("physical", "p"), ("drc", "d"), ("lvs", "l")):
            configuration = getattr(self.server, name + "_workflow").tool_configuration
            self.assertEqual(configuration["working_directory"], str(self.root / ".work/n2t" / child))
            if name != "physical":
                self.assertEqual(configuration["physical_runtime"], self.server.physical_workflow.tool_configuration)
        self.server.physical_workflow.current = False  # Ancestors may be stale after the new configuration.
        restored, reopened = session.load_repair_configurations(self.store, self.base, self.directory,
                                                               "software-qa-project", "software-qa-system")
        self.assertTrue(reopened["configured"]); self.assertEqual(reopened["repair_generation"], 3)
        self.assertEqual(restored[2], self.server.physical_workflow.tool_configuration)
        self.assertEqual(reopened["source_identity"], bundle["source_identity"])
        final_raw = final_path.read_bytes()
        with self.assertRaises(DomainError): session.prepare_retry(self.server, failed["id"], self.revision)
        self.assertEqual(final_path.read_bytes(), final_raw)

    def test_third_prepare_requires_current_exact_second_runtime_and_complete_electrical_only_proof(self):
        failed = self.second_layout_failure()
        original = copy.deepcopy(failed)
        for mutation in (lambda r: r["checks"]["commands"].pop(),
                         lambda r: r["checks"]["commands"][0].update(cleanup_unresolved=True),
                         lambda r: r["checks"]["checks"]["timing"].update(validation_status="Failed"),
                         lambda r: r["checks"].update(cleanup_unresolved=True),
                         lambda r: r.update(review_status="Accepted"),
                         lambda r: r.update(global_rtl="SOFTWARE_QA_CHANGED_RTL"),
                         lambda r: r["checks"]["diagnostics"][0].update(code="other_error")):
            changed = copy.deepcopy(original); mutation(changed); checksum(changed); self.save_layout_failure(changed)
            with self.assertRaises(DomainError): session.prepare_retry(self.server, changed["id"], self.revision)
            self.assertFalse((self.directory / session.FINAL_BUNDLE_NAME).exists())
        self.save_layout_failure(original)
        self.server.physical_workflow.current = False
        with self.assertRaises(DomainError): session.prepare_retry(self.server, failed["id"], self.revision)
        self.server.physical_workflow.current = True
        with self.assertRaises(DomainError): session.prepare_retry(self.server, failed["id"], "other-revision")
        self.server.lvs_workflow.tool_configuration["working_directory"] = "SOFTWARE_QA_OTHER_LVS_RUNTIME"
        with self.assertRaises(DomainError): session.prepare_retry(self.server, failed["id"], self.revision)
        self.final_builder.assert_not_called()

    def test_third_prepare_busy_readonly_worker_and_storage_guards_change_no_bundle(self):
        failed = self.second_layout_failure()
        for name in ("repair_analysis", "postlayout_workflow", "physical_workflow"):
            manager = getattr(self.server, name); manager.active = True
            with self.subTest(manager=name), self.assertRaises(DomainError):
                session.prepare_retry(self.server, failed["id"], self.revision)
            manager.active = False
        self.server.workspace.identity["read_only"] = True
        with self.assertRaises(DomainError): session.prepare_retry(self.server, failed["id"], self.revision)
        self.server.workspace.identity["read_only"] = False
        self.server.generation._worker = SimpleNamespace(is_alive=lambda: True)
        with self.assertRaises(DomainError): session.prepare_retry(self.server, failed["id"], self.revision)
        self.server.generation._worker = None
        self.server.drc_workflow._storage_error = {"code": "SOFTWARE_QA_STORAGE_ERROR"}
        with self.assertRaises(DomainError): session.prepare_retry(self.server, failed["id"], self.revision)
        self.assertFalse((self.directory / session.FINAL_BUNDLE_NAME).exists())
        self.final_builder.assert_not_called()

    def test_dispatch_rejects_unknown_or_malformed_profile_without_preparation(self):
        for configuration in (None, {}, {"profile": None}, {"profile": []},
                              {"profile": {"profile_version": "hullcirq-sky130-route-repair-npu2v3"}},
                              {"profile": {"profile_version": "SOFTWARE_QA_ARBITRARY_PROFILE"}}):
            self.server.physical_workflow.tool_configuration = configuration
            with self.subTest(configuration=configuration), self.assertRaises(DomainError):
                session.prepare_retry(self.server, "software-qa-missing-layout", self.revision)
        self.assertFalse(self.directory.exists())
        self.builder.assert_not_called(); self.retry_builder.assert_not_called(); self.final_builder.assert_not_called()

    def test_third_restore_retains_feedback_only_updates_but_rejects_changed_execution_and_proof(self):
        failed = self.second_layout_failure()
        session.prepare_retry(self.server, failed["id"], self.revision)
        self.first_failure["review_status"] = "Changes Requested"; checksum(self.first_failure); self.save_layout_failure(self.first_failure)
        failed["review_status"] = "Changes Requested"; checksum(failed); self.save_layout_failure(failed)
        self.failure["review_status"] = "Changes Requested"; checksum(self.failure)
        (self.store_path / "postlayout_workflow.json").write_text(json.dumps({"runs": [self.failure], "reviews": []}), encoding="utf-8")
        restored, status = session.load_repair_configurations(self.store, self.base, self.directory,
                                                             "software-qa-project", "software-qa-system")
        self.assertTrue(status["configured"]); self.assertEqual(status["repair_generation"], 3)
        original = copy.deepcopy(failed)
        failed["checks"]["commands"][0]["stdout"] = "SOFTWARE_QA_CHANGED_EXECUTION"
        checksum(failed); self.save_layout_failure(failed)
        restored, status = session.load_repair_configurations(self.store, self.base, self.directory,
                                                             "software-qa-project", "software-qa-system")
        self.assertFalse(status["configured"]); self.assertEqual(restored, self.base)
        self.save_layout_failure(original)
        self.failed_physical_validator.side_effect = DomainError("software_qa_third_proof_rejected", "SOFTWARE QA invalid full saved proof")
        restored, status = session.load_repair_configurations(self.store, self.base, self.directory,
                                                             "software-qa-project", "software-qa-system")
        self.assertFalse(status["configured"]); self.assertEqual(restored, self.base)

    def test_third_bundle_and_both_ancestor_raw_bytes_are_fixed_on_reload(self):
        failed = self.second_layout_failure()
        session.prepare_retry(self.server, failed["id"], self.revision)
        paths = (self.bundle_path, self.directory / session.RETRY_BUNDLE_NAME, self.directory / session.FINAL_BUNDLE_NAME)
        originals = {path: path.read_bytes() for path in paths}
        for changed_path in paths:
            changed_path.write_bytes(originals[changed_path] + b"\n" if changed_path != paths[2] else b'{"SOFTWARE_QA_CHANGED_THIRD":true}')
            before = {path: path.read_bytes() for path in paths}
            restored, status = session.load_repair_configurations(self.store, self.base, self.directory,
                                                                 "software-qa-project", "software-qa-system")
            self.assertFalse(status["configured"]); self.assertEqual(restored, self.base)
            self.assertEqual({path: path.read_bytes() for path in paths}, before)
            changed_path.write_bytes(originals[changed_path])

    def test_third_save_failure_changes_no_runtime_or_ancestor_and_has_no_retry_side_effects(self):
        failed = self.second_layout_failure()
        paths = (self.bundle_path, self.directory / session.RETRY_BUNDLE_NAME)
        before = {path: path.read_bytes() for path in paths}
        configurations = {name: copy.deepcopy(getattr(self.server, name + "_workflow").tool_configuration)
                          for name in ("physical", "drc", "lvs")}
        with patch.object(session, "_replace_with_windows_retry", side_effect=OSError("SOFTWARE QA third save failure")):
            with self.assertRaises(OSError): session.prepare_retry(self.server, failed["id"], self.revision)
        self.assertEqual({path: path.read_bytes() for path in paths}, before)
        self.assertFalse((self.directory / session.FINAL_BUNDLE_NAME).exists())
        self.assertEqual({name: getattr(self.server, name + "_workflow").tool_configuration for name in configurations}, configurations)

    def test_orphan_third_bundle_requires_both_ancestors_and_is_never_ignored_or_overwritten(self):
        self.directory.mkdir(parents=True)
        path = self.directory / session.FINAL_BUNDLE_NAME
        raw = b'{"SOFTWARE_QA_ORPHAN_THIRD":true}\n'; path.write_bytes(raw)
        for with_first in (False, True):
            if with_first:
                path.unlink(); self.prepare(); path.write_bytes(raw)
            restored, status = session.load_repair_configurations(self.store, self.base, self.directory,
                                                                 "software-qa-project", "software-qa-system")
            self.assertFalse(status["configured"]); self.assertTrue(status["bundle_present"])
            self.assertEqual(restored, self.base); self.assertEqual(path.read_bytes(), raw)
        with self.assertRaises(DomainError): self.prepare()
        self.assertEqual(path.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()

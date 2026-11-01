"""Isolated source-archive capture QA; actual EDA proof is an explicit double."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_capture_layout_role_source as fixtures

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
import capture_layout_role_repaired_source as capture
from hullcirq.domain import DomainError


class RepairedSourceCaptureTests(unittest.TestCase):
    def test_isolated_cli_help_resolves_sibling_without_cwd_or_pythonpath(self):
        result = subprocess.run(
            [sys.executable, '-I', '-B', '-X', 'utf8',
             str(PROJECT / 'scripts/capture_layout_role_repaired_source.py'), '--help'],
            cwd=self.root, capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('usage:', result.stdout)

    def setUp(self):
        self.base = fixtures.CaptureLayoutRoleSourceTests("runTest")
        self.base.setUp(); self.addCleanup(self.base.doCleanups)
        self.root, self.store_path = self.base.root, self.base.store_path
        original = copy.deepcopy(self.base.run)
        settings = {"top_module": capture.TOP, "clock_name": "clk", "clock_period_ns": 50}
        plan = {"kind": "npu2-global-original-matrix-v1", "output_count": 4,
                "recipe": {"source_job": {"id": "SOFTWARE_QA_JOB", "k": 3}, "expected_outputs": [-44, 56, 59, 9]}}
        original.update(stage_id="layout", global_rtl=(self.base.artifact_root / "candidate_top.v").read_text(encoding="utf-8"),
            source_manifest={"nodes": [{"node_id": filename[:-2], "module_name": module}
                for filename, module, _ in capture.RTL_INPUTS[1:]]}, settings=settings, verification_plan=plan,
            settings_sha256=capture.object_hash(settings), verification_plan_sha256=capture.object_hash(plan))
        original["global_rtl_sha256"] = hashlib.sha256(original["global_rtl"].encode()).hexdigest()
        original["source_manifest_sha256"] = capture.object_hash(original["source_manifest"])
        self.rehash(original)
        binding = copy.deepcopy(capture.NPU2_SOURCE_BINDING)
        for key in ("revision_id", "global_job_id", "global_rtl_sha256", "source_manifest_sha256", "verification_plan_sha256", "settings_sha256"):
            binding[key] = original[key]
        binding["layout_record_sha256"] = original["record_hash"]
        original_archive = self.root / capture.ORIGINAL_SOURCE_ROOT
        original_archive.mkdir(parents=True)
        original_files = {
            "layout_record.json": capture._json_bytes(original),
            "source_binding.json": capture._json_bytes({"structural_checks": {"synthesis_cells": 1}}),
            "artifacts/synthesis.json": (self.base.artifact_root / fixtures.capture.SYNTHESIS_JSON).read_bytes(),
            "artifacts/synthesis.v": self.base.synthesis_verilog_path.read_bytes(),
            "README.md": b"SOFTWARE QA original bundle must remain unchanged\n",
        }
        original_files.update({"artifacts/" + filename: (self.base.artifact_root / filename).read_bytes()
                               for filename, _, _ in capture.RTL_INPUTS})
        for relative, raw in original_files.items():
            path = original_archive / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        manifest = {"validation_status": "Passed", "layout_run_id": original["id"],
                    "files": {name: capture._record(raw) for name, raw in original_files.items()}}
        manifest_raw = capture._json_bytes(manifest)
        (original_archive / "manifest.json").write_bytes(manifest_raw)
        first_runtime = {"profile": {"profile_version": capture.PROFILE_NPU2},
                         "repair_source_binding": binding, "working_directory": str(self.root / ".work/n2r/p")}
        self.first_repair = copy.deepcopy(original)
        self.first_repair.update(id=capture.NPU2_RETRY_SOURCE_BINDING["layout_run_id"], validation_status="Failed",
            review_status="Awaiting Review", runtime_configuration=first_runtime,
            runtime_configuration_sha256=capture.object_hash(first_runtime), error=None)
        self.first_repair["diagnostics"] = [{"severity": "error", "code": "physical_checks_failed",
                                             "message": "SOFTWARE QA isolated electrical-only failure"}]
        self.first_repair["checks"].update(validation_status="Failed", technology_mapping_executed=False,
            upstream_technology_mapping_reused=True, implementation_kind="resumed_pre_CTS_route_repair",
            diagnostics=copy.deepcopy(self.first_repair["diagnostics"]),
            commands=[{"executed": True, "status": "Completed", "exit_code": 0, "cleanup_unresolved": False} for _ in range(2)],
            checks={name: {"validation_status": "Failed" if name == "electrical" else "Passed"}
                    for name in ("configuration", "source_identity", "routing", "timing", "electrical")})
        self.rehash(self.first_repair)
        retry_binding = copy.deepcopy(capture.NPU2_RETRY_SOURCE_BINDING)
        for key in ("revision_id", "global_job_id", "global_rtl_sha256", "source_manifest_sha256", "verification_plan_sha256", "settings_sha256"):
            retry_binding[key] = original[key]
        retry_binding.update(layout_record_sha256=self.first_repair["record_hash"],
            layout_execution_sha256=capture.execution_hash(self.first_repair),
            original_runtime_configuration_sha256=capture.object_hash(first_runtime))
        second_runtime = {"profile": {"profile_version": capture.PROFILE_NPU2_RETRY},
            "repair_source_binding": retry_binding, "working_directory": str(self.root / ".work/n2s/p"),
            "resume": {"initial_state_path": "SOFTWARE_QA_FIRST_REPAIR_CHECKPOINT",
                       "source_input_manifest_path": "SOFTWARE_QA_FIRST_REPAIR_INPUTS",
                       "from_step": "OpenROAD.RepairDesignPostGRT"}}
        self.second_repair = copy.deepcopy(self.first_repair)
        self.second_repair.update(id=capture.NPU2_FINAL_SOURCE_BINDING["layout_run_id"],
            runtime_configuration=second_runtime, runtime_configuration_sha256=capture.object_hash(second_runtime))
        self.rehash(self.second_repair)
        final_binding = copy.deepcopy(capture.NPU2_FINAL_SOURCE_BINDING)
        for key in ("revision_id", "global_job_id", "global_rtl_sha256", "source_manifest_sha256", "verification_plan_sha256", "settings_sha256"):
            final_binding[key] = original[key]
        final_binding.update(layout_record_sha256=self.second_repair["record_hash"],
            layout_execution_sha256=capture.execution_hash(self.second_repair),
            original_runtime_configuration_sha256=capture.object_hash(second_runtime))
        self.artifact_root = self.root / ".work/n2t/p/hullcirq-layout-software-qa"
        shutil.copytree(self.base.artifact_root, self.artifact_root)
        checkpoint_raw = capture._json_bytes({"odb": "resume-files/resume-files/resume-files/SOFTWARE_QA_THIRD_LEVEL.odb"})
        input_raw = capture._json_bytes({"runtime_configuration": second_runtime,
            "global_rtl_sha256": original["global_rtl_sha256"], "source_manifest_sha256": original["source_manifest_sha256"],
            "settings": settings, "source_bundle": self.first_repair["checks"]["source_bundle"]})
        checkpoint_hash, input_hash = hashlib.sha256(checkpoint_raw).hexdigest(), hashlib.sha256(input_raw).hexdigest()
        inventory_raw = capture._json_bytes({"schema": "hullcirq-npu2-final-checkpoint-inventory-v1",
            "origin": capture.NPU2_FINAL_INVENTORY_ORIGIN,
            "source_run_id": self.second_repair["id"], "source_execution_sha256": capture.execution_hash(self.second_repair),
            "checkpoint_sha256": checkpoint_hash, "input_manifest_sha256": input_hash,
            "files": [{"relative_path": "resume-files/resume-files/resume-files/SOFTWARE_QA_THIRD_LEVEL.odb", "bytes": 19, "sha256": "a" * 64}]})
        inventory_hash = hashlib.sha256(inventory_raw).hexdigest()
        self.inventory_path = self.root / capture.INVENTORY_RELATIVE
        self.inventory_path.parent.mkdir(parents=True, exist_ok=True)
        self.inventory_path.write_bytes(inventory_raw)
        pre_retry_inventory_raw = capture._json_bytes({"schema": "hullcirq-npu2-retry-checkpoint-inventory-v1",
            "origin": capture.NPU2_RETRY_INVENTORY_ORIGIN,
            "source_run_id": self.first_repair["id"], "source_execution_sha256": capture.execution_hash(self.first_repair),
            "checkpoint_sha256": "b" * 64, "input_manifest_sha256": "c" * 64,
            "files": [{"relative_path": "resume-files/SOFTWARE_QA_PRE_RETRY.odb", "bytes": 19, "sha256": "d" * 64}]})
        self.pre_retry_inventory_path = self.root / capture.PRE_RETRY_INVENTORY_RELATIVE
        self.pre_retry_inventory_path.write_bytes(pre_retry_inventory_raw)
        resume_raw = capture._json_bytes({"software_qa_fixture": True,
            "from_step": capture.RETRY_START_STEP, "original_state_sha256": checkpoint_hash,
            "original_input_manifest_sha256": input_hash, "checkpoint_inventory_sha256": inventory_hash,
            "checkpoint_view_hash_origin": capture.NPU2_FINAL_INVENTORY_ORIGIN})
        for name, raw in (("resume-original-state.json", checkpoint_raw), ("resume-original-input-manifest.json", input_raw),
                          ("resume-manifest.json", resume_raw)):
            (self.artifact_root / name).write_bytes(raw)
        runtime = {"profile": {"profile_version": capture.PROFILE_NPU2_FINAL}, "repair_source_binding": final_binding,
                   "working_directory": str(self.artifact_root.parent),
                   "repair_checkpoint_inventory": {"relative_path": capture.INVENTORY_RELATIVE,
                       "sha256": inventory_hash, "origin": capture.NPU2_FINAL_INVENTORY_ORIGIN},
                   "resume": {"initial_state_sha256": checkpoint_hash, "source_input_manifest_sha256": input_hash,
                              "from_step": capture.RETRY_START_STEP}}
        self.record = copy.deepcopy(original)
        self.record.update(id=capture.RUN_ID, source_key="SOFTWARE_QA_NEW_SOURCE", source_epoch_at_start=8, acceptance_epoch=8,
                           runtime_configuration=runtime, runtime_configuration_sha256=capture.object_hash(runtime), error=None)
        self.record["checks"].update(artifacts_directory=str(self.artifact_root), technology_mapping_executed=False,
            upstream_technology_mapping_reused=True, implementation_kind="resumed_post_GRT_route_repair",
            commands=[{"executed": True, "status": "Completed", "exit_code": 0, "cleanup_unresolved": False} for _ in range(2)],
            checks={name: {"validation_status": "Passed"} for name in ("configuration", "source_identity", "routing", "timing", "electrical")},
            checkpoint_manifest_sha256=hashlib.sha256(resume_raw).hexdigest())
        # New final paths deliberately do not resemble the original step numbers.
        for artifact in self.record["checks"]["artifacts"]:
            if artifact["id"] in ("gds", "def", "netlist"):
                raw = (self.artifact_root / artifact["relative_path"]).read_bytes()
                relative = "runs/corrected/91-final/" + artifact["id"] + ".saved"
                path = self.artifact_root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
                artifact["relative_path"] = relative
        self.store = {"physical_workflow_store_version": "0.1", "source_key": self.record["source_key"], "source_epoch": 8,
                      "runs": [original, self.first_repair, self.second_repair, self.record], "reviews": [{"run_id": capture.RUN_ID, "decision": "accepted",
                      "source_key": self.record["source_key"], "acceptance_epoch": 8}]}
        self.write_store()
        patches = {"ROOT": self.root, "NPU2_SOURCE_BINDING": binding, "NPU2_RETRY_SOURCE_BINDING": retry_binding,
                   "NPU2_FINAL_SOURCE_BINDING": final_binding,
                   "NPU2_FINAL_STATE_SHA": checkpoint_hash, "NPU2_FINAL_INPUT_SHA": input_hash,
                   "NPU2_FINAL_INVENTORY_SHA": inventory_hash,
                   "NPU2_RETRY_INVENTORY_SHA": hashlib.sha256(pre_retry_inventory_raw).hexdigest(),
                   "RUNTIME_SHA256": capture.object_hash(runtime),
                   "ORIGINAL_MANIFEST_SHA256": hashlib.sha256(manifest_raw).hexdigest(),
                   "STORE_RELATIVE": self.store_path.relative_to(self.root).as_posix()}
        for name, value in patches.items():
            replacement = patch.object(capture, name, value); replacement.start(); self.addCleanup(replacement.stop)
        proof = patch.object(capture, "validate_physical_proof")
        self.proof = proof.start(); self.addCleanup(proof.stop)
        failed_proof = patch.object(capture, "validate_failed_physical_proof")
        self.failed_proof = failed_proof.start(); self.addCleanup(failed_proof.stop)
        self.output = self.root / capture.OUTPUT_RELATIVE
        self.profile = self.root / capture.PROFILE_RELATIVE

    @staticmethod
    def rehash(record): record["record_hash"] = capture.object_hash({key: value for key, value in record.items() if key != "record_hash"})
    def write_store(self):
        self.rehash(self.record)
        self.store_path.write_bytes(capture._json_bytes(self.store))
    @staticmethod
    def snapshot(root): return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}

    def test_new_archive_uses_new_geometry_same_rtl_and_explicitly_reused_synthesis(self):
        before_work = self.snapshot(self.root / ".work")
        old_archive = self.snapshot(self.root / capture.ORIGINAL_SOURCE_ROOT)
        result = capture.capture()
        self.proof.assert_called_once_with(self.record, capture.validate_layout_result)
        self.assertEqual(self.failed_proof.call_count, 2)
        self.failed_proof.assert_any_call(self.first_repair, capture.validate_failed_layout_result)
        self.failed_proof.assert_any_call(self.second_repair, capture.validate_failed_layout_result)
        self.assertEqual(self.snapshot(self.root / ".work"), before_work)
        self.assertEqual(self.snapshot(self.root / capture.ORIGINAL_SOURCE_ROOT), old_archive)
        manifest = json.loads((self.output / "manifest.json").read_text(encoding="utf-8"))
        for relative, expected in manifest["files"].items():
            self.assertEqual(capture._record((self.output / relative).read_bytes()), expected)
        binding = json.loads((self.output / "source_binding.json").read_text(encoding="utf-8"))
        self.assertEqual(binding["upstream_synthesis"]["scope"], "reused_original_technology_mapping_no_fresh_synthesis")
        self.assertTrue(binding["checkpoint_proof"]["full_saved_physical_proof_revalidated_read_only"])
        self.assertEqual(binding["checkpoint_proof"]["source_run_id"], self.second_repair["id"])
        self.assertEqual(binding["checkpoint_proof"]["source_validation_status"], "Failed")
        self.assertFalse(binding["checkpoint_proof"]["source_adopted"])
        self.assertEqual(binding["checkpoint_proof"]["resume_from_step"], capture.NPU2_FINAL_STEP)
        self.assertEqual(binding["checkpoint_proof"]["source_execution_sha256"], capture.execution_hash(self.second_repair))
        self.assertEqual(binding["checkpoint_proof"]["checkpoint_view_hash_origin"], capture.NPU2_FINAL_INVENTORY_ORIGIN)
        self.assertEqual((self.output / "checkpoint/pre_final_observation_inventory.json").read_bytes(), self.inventory_path.read_bytes())
        self.assertEqual((self.output / "checkpoint/pre_retry_observation_inventory.json").read_bytes(), self.pre_retry_inventory_path.read_bytes())
        prior = binding["prior_checkpoint_observation"]
        self.assertEqual(prior["source_run_id"], self.first_repair["id"])
        self.assertEqual(prior["source_execution_sha256"], capture.execution_hash(self.first_repair))
        self.assertEqual(prior["inventory_sha256"], capture.NPU2_RETRY_INVENTORY_SHA)
        self.assertEqual(prior["checkpoint_view_hash_origin"], capture.NPU2_RETRY_INVENTORY_ORIGIN)
        self.assertNotEqual(prior["inventory_sha256"], binding["checkpoint_proof"]["pre_final_inventory_sha256"])
        first_inputs = json.loads((self.output / "checkpoint/resume-original-input-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(first_inputs["runtime_configuration"]["profile"]["profile_version"], capture.PROFILE_NPU2_RETRY)
        self.assertEqual(first_inputs["runtime_configuration"]["repair_source_binding"], capture.NPU2_RETRY_SOURCE_BINDING)
        self.assertEqual(first_inputs["source_bundle"], self.first_repair["checks"]["source_bundle"])
        checkpoint = json.loads((self.output / "checkpoint/resume-original-state.json").read_text(encoding="utf-8"))
        self.assertEqual(checkpoint["odb"], "resume-files/resume-files/resume-files/SOFTWARE_QA_THIRD_LEVEL.odb")
        self.assertEqual(json.loads((self.output / "checkpoint/first_repair_failed_record.json").read_text(encoding="utf-8")), self.first_repair)
        self.assertEqual(json.loads((self.output / "checkpoint/second_repair_failed_record.json").read_text(encoding="utf-8")), self.second_repair)
        self.assertEqual([entry["run_id"] for entry in binding["failed_repair_ancestry"]], [self.first_repair["id"], self.second_repair["id"]])
        self.assertTrue(all(value == 0 for value in binding["derivation_activity"].values()))
        final_bindings = [item for item in binding["artifact_bindings"] if item["artifact_id"] in ("gds", "def", "netlist")]
        self.assertTrue(all(item["source_relative_path"].startswith("runs/corrected/91-final/") for item in final_bindings))
        profile = json.loads(self.profile.read_text(encoding="utf-8"))
        self.assertEqual(profile["layout_run_id"], capture.RUN_ID)
        self.assertEqual(profile["role_profile"], "npu2_explicit_2x2_v1")
        self.assertEqual(profile["expected_final_cells"], 1)
        self.assertEqual(profile["expected_synthesis_cells"], 1)
        self.assertEqual(profile["source_manifest_sha256"], result["source_manifest_sha256"])
        self.assertEqual(result["additional_eda_runs"], 0)

    def test_running_stale_or_changed_job_cannot_create_archive(self):
        original = copy.deepcopy(self.record)
        for field, value in (("execution_status", "Running"), ("validation_status", "Failed"),
                             ("review_status", "Awaiting Review"), ("acceptance_epoch", 7), ("global_job_id", "CHANGED_JOB")):
            self.record.clear(); self.record.update(copy.deepcopy(original)); self.record[field] = value; self.write_store()
            with self.subTest(field=field), self.assertRaises(capture.CaptureError): capture.capture()
            self.assertFalse(self.output.exists()); self.assertFalse(self.profile.exists())

    def test_new_rtl_or_checkpoint_byte_tamper_and_failed_saved_proof_are_rejected(self):
        path = self.artifact_root / "candidate_top.v"; original = path.read_bytes(); path.write_bytes(b"CHANGED RTL")
        with self.assertRaises(capture.CaptureError): capture.capture()
        path.write_bytes(original)
        path = self.artifact_root / "resume-original-state.json"; original = path.read_bytes(); path.write_bytes(b"CHANGED CHECKPOINT")
        with self.assertRaises(capture.CaptureError): capture.capture()
        path.write_bytes(original)
        self.proof.side_effect = DomainError("software_qa_invalid_saved_proof", "SOFTWARE QA failed frozen proof")
        with self.assertRaises(DomainError): capture.capture()
        self.assertFalse(self.output.exists()); self.assertFalse(self.profile.exists())

    def test_original_synthesis_archive_tamper_is_not_used(self):
        (self.root / capture.ORIGINAL_SOURCE_ROOT / "artifacts/synthesis.v").write_bytes(b"ALTERED ORIGINAL")
        with self.assertRaises(capture.CaptureError): capture.capture()
        self.assertFalse(self.output.exists()); self.assertFalse(self.profile.exists())

    def test_first_correction_execution_or_fixed_inventory_tamper_cannot_create_archive(self):
        original = copy.deepcopy(self.first_repair)
        self.first_repair["validation_status"] = "Passed"; self.rehash(self.first_repair); self.write_store()
        with self.assertRaises(capture.CaptureError): capture.capture()
        self.first_repair.clear(); self.first_repair.update(original); self.write_store()
        self.inventory_path.write_bytes(self.inventory_path.read_bytes() + b"\n")
        with self.assertRaises(capture.CaptureError): capture.capture()
        self.assertFalse(self.output.exists()); self.assertFalse(self.profile.exists())

    def test_previous_v1_layout_or_failed_ancestry_proof_is_not_substituted(self):
        runtime = self.record["runtime_configuration"]
        runtime["profile"]["profile_version"] = capture.PROFILE_NPU2
        self.record["runtime_configuration_sha256"] = capture.object_hash(runtime); self.write_store()
        with self.assertRaises(capture.CaptureError): capture.capture()
        runtime["profile"]["profile_version"] = capture.PROFILE_NPU2_FINAL
        self.record["runtime_configuration_sha256"] = capture.object_hash(runtime); self.write_store()
        self.failed_proof.side_effect = DomainError("software_qa_invalid_ancestry", "SOFTWARE QA rejected first-repair proof")
        with self.assertRaises(DomainError): capture.capture()
        self.assertFalse(self.output.exists()); self.assertFalse(self.profile.exists())

    def test_pre_retry_observation_inventory_tamper_cannot_create_archive(self):
        self.pre_retry_inventory_path.write_bytes(self.pre_retry_inventory_path.read_bytes() + b"\n")
        with self.assertRaisesRegex(capture.CaptureError, "pre-retry observation inventory changed"):
            capture.capture()
        self.assertFalse(self.output.exists()); self.assertFalse(self.profile.exists())

    def test_first_correction_ordinary_review_does_not_change_execution_ancestry(self):
        before = capture.execution_hash(self.first_repair)
        self.first_repair["review_status"] = "Changes Requested"
        self.first_repair["acceptance_epoch"] = None
        self.rehash(self.first_repair); self.write_store()
        self.assertEqual(capture.execution_hash(self.first_repair), before)
        result = capture.capture()
        self.assertEqual(result["layout_run_id"], capture.RUN_ID)
        self.assertEqual(self.first_repair["validation_status"], "Failed")

    def test_second_failure_tamper_or_previous_v2_candidate_is_rejected(self):
        original = copy.deepcopy(self.second_repair)
        self.second_repair["validation_status"] = "Passed"
        self.rehash(self.second_repair); self.write_store()
        with self.assertRaises(capture.CaptureError): capture.capture()
        self.second_repair.clear(); self.second_repair.update(original)
        runtime = self.record["runtime_configuration"]
        runtime["profile"]["profile_version"] = capture.PROFILE_NPU2_RETRY
        self.record["runtime_configuration_sha256"] = capture.object_hash(runtime); self.write_store()
        with self.assertRaises(capture.CaptureError): capture.capture()
        self.assertFalse(self.output.exists()); self.assertFalse(self.profile.exists())

    def test_second_failure_review_metadata_preserves_execution_provenance(self):
        before = capture.execution_hash(self.second_repair)
        self.second_repair.update(review_status="Changes Requested", acceptance_epoch=None)
        self.rehash(self.second_repair); self.write_store()
        self.assertEqual(capture.execution_hash(self.second_repair), before)
        self.assertEqual(capture.capture()["layout_run_id"], capture.RUN_ID)

    def test_existing_archive_or_profile_is_preserved(self):
        self.output.mkdir(); marker = self.output / "keep"; marker.write_bytes(b"KEEP")
        with self.assertRaises(capture.CaptureError): capture.capture()
        self.assertEqual(marker.read_bytes(), b"KEEP")
        marker.unlink(); self.output.rmdir()
        self.profile.parent.mkdir(exist_ok=True); self.profile.write_bytes(b"KEEP PROFILE")
        with self.assertRaises(capture.CaptureError): capture.capture()
        self.assertEqual(self.profile.read_bytes(), b"KEEP PROFILE")
        self.assertFalse(self.output.exists())


if __name__ == "__main__": unittest.main()

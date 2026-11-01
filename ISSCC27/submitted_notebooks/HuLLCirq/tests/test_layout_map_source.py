"""Isolated source-capture fixtures; no live stores, processes or EDA."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq import layout_map_source as source
from hullcirq.domain import DomainError
from hullcirq.layout_roles import collect_layout_roles
from hullcirq.verification import content_hash, object_hash


class LayoutMapSourceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "results").mkdir()
        self.artifacts = self.root / ".work/layout/hullcirq-layout-fixture"
        self.artifacts.mkdir(parents=True)
        self.output = self.root / "results" / ("fm-source-" + "e" * 32)
        self.registrations = {}
        self.addCleanup(patch.stopall)
        patch.object(source, "_registrations", lambda: self.registrations).start()
        self._build()

    @staticmethod
    def _record(raw):
        return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

    @staticmethod
    def _bytes(value):
        return (json.dumps(value, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")

    def _put(self, relative, raw):
        path = self.artifacts / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return {"relative_path": relative, **self._record(raw)}

    def _hash(self):
        self.run["record_hash"] = object_hash({key: value for key, value in self.run.items() if key != "record_hash"})

    def _build(self):
        design = json.loads((ROOT / "examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))
        self.rtl = {filename: "module " + module + "; endmodule\n" for filename, module, _ in source.RTL_INPUTS}
        manifest = {"design": design, "nodes": [{"node_id": filename[:-2], "module_name": module,
            "rtl": self.rtl[filename], "rtl_sha256": content_hash(self.rtl[filename])}
            for filename, module, _ in source.RTL_INPUTS[1:]]}
        artifacts = []
        for filename, _, identifier in source.RTL_INPUTS:
            artifacts.append({"id": identifier, "content_type": "text/plain; charset=utf-8", **self._put(filename, self.rtl[filename].encode())})
        self.structural = ("module hullcirq_npu2_top(a,z);\ninput a; output z;\n"
                           "sky130_fd_sc_hd__buf_1 c0 (.A(a),.X(z));\nendmodule\n").encode()
        self.synthesis = self._bytes({"modules": {source.TOP: {"cells": {"json0": {"type": "sky130_fd_sc_hd__buf_1",
            "connections": {"A": [2], "X": [3]}, "port_directions": {"A": "input", "X": "output"},
            "attributes": {"src": "/src/npu2-control.v:1.1-2.1"}}},
            "netnames": {"a": {"hide_name": 0, "bits": [2]}, "z": {"hide_name": 0, "bits": [3]}}}}})
        self.final_def = b"VERSION 5.8 ;\nCOMPONENTS 1 ;\n- c0 sky130_fd_sc_hd__buf_1 + PLACED ( 0 0 ) N ;\nEND COMPONENTS\n"
        for identifier, relative, raw in (("gds", "final.gds", b"fixture-gds-not-circuit-evidence"),
                                          ("def", "final.def", self.final_def), ("netlist", "final.nl.v", self.structural)):
            artifacts.append({"id": identifier, "content_type": "application/octet-stream", **self._put(relative, raw)})
        self.synthesis_relative = "runs/physical/06-yosys-synthesis/" + source.TOP + ".nl.v.json"
        retained = [self._put(self.synthesis_relative, self.synthesis)]
        self._put(self.synthesis_relative[:-5], self.structural)
        self.run = {"id": "physical-workflow-" + "1" * 32, "stage_id": "layout", "revision_id": "revision-fixture",
            "execution_status": "Completed", "validation_status": "Passed", "review_status": "Accepted", "error": None,
            "evidence_kind": "trusted_fixed_tool_execution", "global_rtl": self.rtl["candidate_top.v"],
            "global_rtl_sha256": content_hash(self.rtl["candidate_top.v"]), "source_manifest": manifest,
            "source_manifest_sha256": object_hash(manifest), "checks": {"origin": "trusted_fixed_tool_adapter",
                "validation_status": "Passed", "executed": True, "exit_code": 0, "cleanup_unresolved": False,
                "source_bundle": source.source_bundle(self.rtl["candidate_top.v"], manifest), "artifacts": artifacts,
                "artifacts_directory": str(self.artifacts), "retained_files": retained}}
        self._hash()

    def _capture(self):
        return source.capture_source(self.root, self.run, self.output)

    def _work_snapshot(self):
        return {p.relative_to(self.artifacts).as_posix(): p.read_bytes() for p in self.artifacts.rglob("*") if p.is_file()}

    def _archive(self, run=None, name="registered-fixture", *, add=True):
        run = copy.deepcopy(self.run if run is None else run)
        folder = self.root / "results" / name
        folder.mkdir()
        pending = {"layout_record.json": self._bytes(run), "artifacts/synthesis.json": self.synthesis,
            "artifacts/synthesis.v": self.structural, "artifacts/final.gds": b"fixture-gds-not-circuit-evidence",
            "artifacts/final.def": self.final_def, "artifacts/final.nl.v": self.structural,
            **{"artifacts/" + filename: raw.encode() for filename, raw in self.rtl.items()}}
        for relative, raw in pending.items():
            path = folder / relative
            path.parent.mkdir(exist_ok=True, parents=True)
            path.write_bytes(raw)
        manifest_raw = self._bytes({"validation_status": "Passed", "layout_run_id": run["id"],
            "files": {name: self._record(raw) for name, raw in pending.items()}})
        (folder / "manifest.json").write_bytes(manifest_raw)
        registered = {"source_root": folder.relative_to(self.root).as_posix(),
            "source_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(), "allow_registered_archive_artifact_fallback": True}
        if add:
            self.registrations[run["id"]] = registered
        return folder, registered

    def test_new_run_is_complete_read_only_and_renderer_compatible(self):
        before = self._work_snapshot()
        profile = self._capture()
        self.assertEqual(before, self._work_snapshot())
        self.assertEqual(profile["layout_run_id"], self.run["id"])
        self.assertEqual(profile["expected_synthesis_cells"], 1)
        self.assertEqual(profile["expected_final_cells"], 1)
        self.assertEqual(profile["annotation_policy"], "changed_family_unknown_v1")
        mapping = collect_layout_roles(self.root, profile)
        self.assertEqual(mapping["cells"][0]["status"], "source_confirmed")
        self.assertEqual(mapping["cells"][0]["role"], "control")
        self.assertEqual(len(mapping["provenance"]["source_rtl"]), 12)
        binding = json.loads((self.output / "source_binding.json").read_bytes())
        v = binding["synthesis_inputs"]["verilog"]
        self.assertFalse(v["declared_in_original_retained_files"])
        self.assertEqual(v["binding"], "new_read_only_observation_not_originally_retained")
        self.assertTrue(all(value == 0 for value in binding["derivation_activity"].values()))
        manifest_raw = (self.output / "manifest.json").read_bytes()
        self.assertEqual(hashlib.sha256(manifest_raw).hexdigest(), profile["source_manifest_sha256"])
        self.assertEqual(json.loads((self.output / "layout_record.json").read_bytes()), self.run)

    def test_declared_synthesis_verilog_keeps_retained_provenance(self):
        path = self.synthesis_relative[:-5]
        self.run["checks"]["retained_files"].append({"relative_path": path, **self._record(self.structural)})
        self._hash()
        self._capture()
        binding = json.loads((self.output / "source_binding.json").read_bytes())
        self.assertTrue(binding["synthesis_inputs"]["verilog"]["declared_in_original_retained_files"])

    def test_existing_destination_is_not_overwritten(self):
        self.output.mkdir()
        marker = self.output / "preserve"
        marker.write_bytes(b"prior-evidence")
        with self.assertRaises(DomainError):
            self._capture()
        self.assertEqual(marker.read_bytes(), b"prior-evidence")
        self.assertEqual(list(self.output.iterdir()), [marker])

    def test_output_path_and_identifier_are_server_confined(self):
        for output in (self.root / "results/other", self.root / "fm-source-" / ("e" * 32), self.root / "results/sub" / self.output.name):
            with self.subTest(output=output), self.assertRaises(DomainError):
                source.capture_source(self.root, self.run, output)

    def test_raw_checksum_failure_writes_no_output(self):
        self.run["revision_id"] = "substituted"
        with self.assertRaises(DomainError):
            self._capture()
        self.assertFalse(self.output.exists())

    def test_unaccepted_failed_fixture_and_unresolved_cleanup_are_rejected(self):
        original = copy.deepcopy(self.run)
        changes = [lambda r: r.update(review_status="Awaiting Review"), lambda r: r.update(validation_status="Failed"),
            lambda r: r.update(execution_status="Running"), lambda r: r["checks"].update(cleanup_unresolved=True),
            lambda r: r["checks"].update(software_qa_fixture=True), lambda r: r.update(evidence_kind="fixture"),
            lambda r: r["checks"].update(exit_code=False)]
        for change in changes:
            self.run = copy.deepcopy(original)
            change(self.run)
            self._hash()
            with self.subTest(change=change), self.assertRaises(DomainError):
                self._capture()
            self.assertFalse(self.output.exists())

    def test_changed_bundle_has_explicit_integrity_reason(self):
        self.run["checks"]["source_bundle"].pop()
        self._hash()
        result = source.eligibility(self.run)
        self.assertFalse(result["supported"])
        self.assertEqual(result["reason"]["code"], "functional_map_source_integrity_error")

    def test_rtl_manifest_content_and_artifact_substitution_fail_closed(self):
        original = copy.deepcopy(self.run)
        changes = [lambda r: r.update(global_rtl_sha256="0" * 64), lambda r: r.update(source_manifest_sha256="0" * 64),
            lambda r: r["checks"]["source_bundle"][1].update(sha256="0" * 64),
            lambda r: r["checks"]["artifacts"][0].update(sha256="0" * 64)]
        for change in changes:
            self.run = copy.deepcopy(original)
            change(self.run)
            self._hash()
            with self.subTest(change=change), self.assertRaises(DomainError):
                self._capture()
            self.assertFalse(self.output.exists())

    def test_readable_changed_final_geometry_does_not_fallback(self):
        self._archive()
        (self.artifacts / "final.gds").write_bytes(b"changed-layout")
        with self.assertRaisesRegex(DomainError, "Retained physical bytes changed"):
            self._capture()
        self.assertFalse(self.output.exists())

    def test_same_run_registered_archive_recovers_missing_original_inputs(self):
        self._archive()
        for path in self.artifacts.rglob("*"):
            if path.is_file():
                path.unlink()
        self._capture()
        binding = json.loads((self.output / "source_binding.json").read_bytes())
        self.assertTrue(all(entry["method"] == "registered_same_run_source_archive" for entry in binding["artifact_bindings"]))
        self.assertEqual(binding["synthesis_inputs"]["layout_run_id"], self.run["id"])

    def test_gui_published_same_run_archive_recovers_without_static_code_registration(self):
        _, registered = self._archive()
        self.registrations.clear()
        for path in self.artifacts.rglob("*"):
            if path.is_file():
                path.unlink()
        with patch('hullcirq.layout_map_generation.read_registration', return_value=registered):
            self._capture()
        binding = json.loads((self.output / 'source_binding.json').read_bytes())
        self.assertTrue(all(entry['method'] == 'registered_same_run_source_archive'
                            for entry in binding['artifact_bindings']))

    def test_outside_workspace_original_path_is_never_read(self):
        self.run["checks"]["artifacts_directory"] = str(self.root.parent / "foreign-result")
        self._hash()
        self._archive()
        with patch.object(source, "_artifact_path", side_effect=AssertionError("outside source read")):
            self._capture()

    def test_same_run_archive_must_match_immutable_raw_record_projection(self):
        self._archive()
        self.run["revision_id"] = "substituted"
        self._hash()
        with self.assertRaisesRegex(DomainError, "exact selected physical record"):
            self._capture()

    def test_archive_manifest_pin_and_file_hash_reject_tampering(self):
        folder, _ = self._archive()
        (folder / "manifest.json").write_bytes(b"{}")
        with self.assertRaisesRegex(DomainError, "manifest changed"):
            self._capture()
        self.assertFalse(self.output.exists())

    def test_archive_file_tampering_cannot_substitute_rtl(self):
        folder, _ = self._archive()
        (folder / "artifacts/candidate_top.v").write_bytes(b"changed-source")
        (self.artifacts / "candidate_top.v").unlink()
        with self.assertRaisesRegex(DomainError, "archive input changed"):
            self._capture()
        self.assertFalse(self.output.exists())

    def test_other_run_final_geometry_cannot_be_used_as_missing_current_layout(self):
        old = copy.deepcopy(self.run)
        old["id"] = "physical-workflow-" + "2" * 32
        old["record_hash"] = object_hash({k: v for k, v in old.items() if k != "record_hash"})
        self._archive(old)
        (self.artifacts / "final.gds").unlink()
        with self.assertRaisesRegex(DomainError, "no pinned same-run"):
            self._capture()

    def test_repaired_run_can_reuse_only_source_identical_registered_synthesis(self):
        original = copy.deepcopy(self.run)
        self._archive(original)
        self.run["id"] = "physical-workflow-" + "3" * 32
        self.run["checks"].update(retained_files=[], upstream_technology_mapping_reused=True, technology_mapping_executed=False)
        self._hash()
        self._capture()
        binding = json.loads((self.output / "source_binding.json").read_bytes())
        synth = binding["synthesis_inputs"]
        self.assertEqual(synth["layout_run_id"], original["id"])
        self.assertTrue(synth["all_twelve_source_rtl_bytes_equal"])
        self.assertTrue(all(entry["method"] == "retained_result_file" for entry in binding["artifact_bindings"]))

    def test_unrelated_run_synthesis_is_not_reused_without_explicit_repair_scope(self):
        self._archive()
        self.run["id"] = "physical-workflow-" + "4" * 32
        self.run["checks"]["retained_files"] = []
        self._hash()
        with self.assertRaisesRegex(DomainError, "No retained synthesis graph"):
            self._capture()

    def test_reused_synthesis_rejects_different_source_manifest(self):
        old = copy.deepcopy(self.run)
        old["source_manifest"]["metadata"] = "different-input"
        old["source_manifest_sha256"] = object_hash(old["source_manifest"])
        old["record_hash"] = object_hash({k: v for k, v in old.items() if k != "record_hash"})
        self._archive(old)
        self.run["id"] = "physical-workflow-" + "5" * 32
        self.run["checks"].update(retained_files=[], upstream_technology_mapping_reused=True, technology_mapping_executed=False)
        self._hash()
        with self.assertRaisesRegex(DomainError, "No retained synthesis graph"):
            self._capture()

    def test_reused_synthesis_requires_all_twelve_byte_hashes(self):
        folder, registration = self._archive()
        # A newly pinned archive may not truthfully assert the same global source
        # while providing another RTL.  Every source byte is checked separately.
        path = folder / "artifacts/npu2-pe11.v"
        path.write_bytes(b"different-but-checksum-declared-input")
        manifest = json.loads((folder / "manifest.json").read_bytes())
        manifest["files"]["artifacts/npu2-pe11.v"] = self._record(path.read_bytes())
        raw = self._bytes(manifest)
        (folder / "manifest.json").write_bytes(raw)
        registration["source_manifest_sha256"] = hashlib.sha256(raw).hexdigest()
        self.run["id"] = "physical-workflow-" + "6" * 32
        self.run["checks"].update(retained_files=[], upstream_technology_mapping_reused=True, technology_mapping_executed=False)
        self._hash()
        with self.assertRaisesRegex(DomainError, "No retained synthesis graph"):
            self._capture()

    def test_readable_retained_synthesis_mismatch_is_not_replaced_by_archive(self):
        self._archive()
        (self.artifacts / self.synthesis_relative).write_bytes(b"substituted-graph")
        with self.assertRaisesRegex(DomainError, "synthesis JSON bytes changed"):
            self._capture()

    def test_unsafe_relative_paths_and_duplicate_ids_are_rejected(self):
        original = copy.deepcopy(self.run)
        for relative in ("../escape", "/escape", "drive:escape", "nested\\escape"):
            self.run = copy.deepcopy(original)
            self.run["checks"]["artifacts"][-1]["relative_path"] = relative
            self._hash()
            with self.subTest(relative=relative), self.assertRaises(DomainError):
                self._capture()
        self.run = copy.deepcopy(original)
        self.run["checks"]["artifacts"].append(copy.deepcopy(self.run["checks"]["artifacts"][0]))
        self._hash()
        with self.assertRaises(DomainError):
            self._capture()

    def test_changed_synthesis_connectivity_and_final_def_inventory_are_rejected(self):
        self._put(self.synthesis_relative[:-5], self.structural.replace(b".A(a)", b".A(z)"))
        with self.assertRaisesRegex(DomainError, "structural source correspondence"):
            self._capture()
        self.assertFalse(self.output.exists())

    def test_declared_but_substituted_synthesis_verilog_is_rejected(self):
        relative = self.synthesis_relative[:-5]
        self.run["checks"]["retained_files"].append({"relative_path": relative, **self._record(self.structural)})
        self._hash()
        self._put(relative, self.structural + b"// newly changed bytes\n")
        with self.assertRaisesRegex(DomainError, "synthesis Verilog bytes changed"):
            self._capture()
        self.assertFalse(self.output.exists())

    def test_extra_unmapped_hierarchy_is_rejected_before_archive_creation(self):
        document = json.loads(self.synthesis)
        document["modules"]["unmapped_extra_module"] = {"cells": {}, "attributes": {}}
        raw = self._bytes(document)
        self.run["checks"]["retained_files"][0] = self._put(self.synthesis_relative, raw)
        self._hash()
        with self.assertRaisesRegex(DomainError, "only blackbox"):
            self._capture()
        self.assertFalse(self.output.exists())

    def test_declared_final_def_cannot_disagree_with_actual_netlist(self):
        changed = self.final_def.replace(b"sky130_fd_sc_hd__buf_1", b"sky130_fd_sc_hd__inv_1")
        entry = next(item for item in self.run["checks"]["artifacts"] if item["id"] == "def")
        entry.update(self._put("final.def", changed))
        self._hash()
        with self.assertRaisesRegex(DomainError, "instance/master inventories differ"):
            self._capture()
        self.assertFalse(self.output.exists())

    def test_duplicate_synthesis_retained_path_is_rejected(self):
        self.run["checks"]["retained_files"].append(copy.deepcopy(self.run["checks"]["retained_files"][0]))
        self._hash()
        with self.assertRaisesRegex(DomainError, "Duplicate retained"):
            self._capture()
        self.assertFalse(self.output.exists())

    def test_manifest_module_substitution_is_an_integrity_failure(self):
        entry = self.run["source_manifest"]["nodes"][1]
        entry["module_name"] = "unrecognized_buffer"
        # The physical bundle remains consistent with this changed manifest;
        # The unchanged graph/source must not be relabelled by a manifest edit.
        self.run["source_manifest_sha256"] = object_hash(self.run["source_manifest"])
        self.run["checks"]["source_bundle"] = source.source_bundle(self.run["global_rtl"], self.run["source_manifest"])
        self._hash()
        with self.assertRaises(DomainError) as caught:
            self._capture()
        self.assertEqual(caught.exception.code, "functional_map_source_integrity_error")

    def test_source_capture_rejects_linked_external_input_without_read(self):
        external = self.root / "outside-retained-artifact.v"
        external.write_bytes(self.structural)
        target = self.artifacts / "final.nl.v"
        target.unlink()
        try:
            target.symlink_to(external)
        except OSError:
            self.skipTest("Symbolic links are unavailable in this isolated Windows environment")
        with self.assertRaisesRegex(DomainError, "escapes its retained directory"):
            self._capture()
        self.assertFalse(self.output.exists())

    def test_input_changed_during_capture_leaves_no_output(self):
        original = source.source_profile_values
        def mutate(profile):
            result = original(profile)
            (self.artifacts / "final.gds").write_bytes(b"concurrent-change")
            return result
        with patch.object(source, "source_profile_values", mutate), self.assertRaisesRegex(DomainError, "changed during source capture"):
            self._capture()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()

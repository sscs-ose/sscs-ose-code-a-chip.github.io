import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import capture_layout_role_source as capture  # noqa: E402


class CaptureLayoutRoleSourceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.artifact_root = (
            self.root / ".work/n2f/layout/hullcirq-layout-fixture"
        )
        self.artifact_root.mkdir(parents=True)
        self.store_path = (
            self.root
            / ".work/projects/example/systems/system-fixture/physical_workflow.json"
        )
        self.store_path.parent.mkdir(parents=True)
        self.output = self.root / "results/captured"
        (self.root / "results").mkdir()
        self._build_fixture()

    @staticmethod
    def _record(raw):
        return {
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }

    def _put(self, relative, raw):
        path = self.artifact_root / Path(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return {"relative_path": relative, **self._record(raw)}

    def _build_fixture(self):
        artifacts = []
        source_bundle = []
        for filename, module_name, artifact_id in capture.RTL_INPUTS:
            raw = f"module {module_name}; endmodule\n".encode("ascii")
            entry = self._put(filename, raw)
            artifacts.append({"id": artifact_id, **entry})
            source_bundle.append(
                {
                    "file": filename,
                    "module_name": module_name,
                    "sha256": entry["sha256"],
                }
            )

        structural = (
            "module hullcirq_npu2_top(a, z);\n"
            "input a;\n"
            "output z;\n"
            "sky130_fd_sc_hd__buf_1 c0 (.A(a), .X(z));\n"
            "endmodule\n"
        ).encode("ascii")
        synthesis_json = json.dumps(
            {
                "modules": {
                    capture.TOP: {
                        "cells": {
                            "json_cell": {
                                "type": "sky130_fd_sc_hd__buf_1",
                                "connections": {"A": [2], "X": [3]},
                            }
                        },
                        "netnames": {
                            "a": {"bits": [2], "hide_name": 0},
                            "z": {"bits": [3], "hide_name": 0},
                        },
                    }
                }
            },
            sort_keys=True,
        ).encode("utf-8")
        def_raw = (
            "VERSION 5.8 ;\n"
            "DESIGN hullcirq_npu2_top ;\n"
            "COMPONENTS 1 ;\n"
            "- c0 sky130_fd_sc_hd__buf_1 + PLACED ( 0 0 ) N ;\n"
            "END COMPONENTS\n"
            "END DESIGN\n"
        ).encode("ascii")
        layout_raw = {
            "gds": b"fixture-gds-bytes\n",
            "def": def_raw,
            "netlist": structural,
        }
        for artifact_id, relative, _target in capture.LAYOUT_INPUTS:
            entry = self._put(relative, layout_raw[artifact_id])
            artifacts.append({"id": artifact_id, **entry})
        synthesis_json_entry = self._put(
            capture.SYNTHESIS_JSON, synthesis_json
        )
        self.synthesis_verilog_path = self.artifact_root / Path(
            *capture.SYNTHESIS_VERILOG.split("/")
        )
        self.synthesis_verilog_path.parent.mkdir(parents=True, exist_ok=True)
        self.synthesis_verilog_path.write_bytes(structural)

        self.run = {
            "id": capture.DEFAULT_RUN_ID,
            "execution_status": "Completed",
            "validation_status": "Passed",
            "review_status": "Accepted",
            "evidence_kind": "trusted_fixed_tool_execution",
            "acceptance_epoch": 7,
            "source_key": "source-fixture",
            "revision_id": "revision-fixture",
            "global_job_id": "global-fixture",
            "synthesis_run_id": "synthesis-fixture",
            "netlist_run_id": "netlist-fixture",
            "global_context_id": "context-fixture",
            "global_rtl_sha256": "1" * 64,
            "source_manifest_sha256": "2" * 64,
            "verification_plan_sha256": "3" * 64,
            "vector_hash": "4" * 64,
            "testbench_sha256": "5" * 64,
            "public_boundary_vector_hash": "6" * 64,
            "checks": {
                "validation_status": "Passed",
                "executed": True,
                "exit_code": 0,
                "cleanup_unresolved": False,
                "origin": "trusted_fixed_tool_adapter",
                "artifacts_directory": str(self.artifact_root),
                "artifacts": artifacts,
                "retained_files": [synthesis_json_entry],
                "source_bundle": source_bundle,
            },
        }
        self.store = {
            "physical_workflow_store_version": "0.1",
            "source_key": "source-fixture",
            "source_epoch": 7,
            "runs": [self.run],
            "reviews": [
                {
                    "run_id": capture.DEFAULT_RUN_ID,
                    "decision": "accepted",
                    "acceptance_epoch": 7,
                }
            ],
        }
        self._write_store(rehash=True)
        self.expected_record_hash = self.run["record_hash"]

    def _write_store(self, rehash=False):
        if rehash:
            self.run["record_hash"] = capture.object_hash(
                {
                    key: value
                    for key, value in self.run.items()
                    if key != "record_hash"
                }
            )
        self.store_path.write_text(
            json.dumps(self.store, ensure_ascii=False, allow_nan=False),
            encoding="utf-8",
        )

    def _capture(self, **kwargs):
        with patch.object(capture, "ROOT", self.root), patch.object(
            capture, "EXPECTED_RUN_RECORD_HASH", self.expected_record_hash
        ):
            return capture.capture(
                self.store_path,
                self.output,
                capture.DEFAULT_RUN_ID,
                **kwargs,
            )

    def _work_snapshot(self):
        work = self.root / ".work"
        return {
            path.relative_to(work).as_posix(): path.read_bytes()
            for path in work.rglob("*")
            if path.is_file()
        }

    def test_capture_is_complete_hash_bound_and_read_only(self):
        before = self._work_snapshot()
        result = self._capture(working_root=self.artifact_root)

        expected = {
            "manifest.json",
            "layout_record.json",
            "source_binding.json",
            "README.md",
            "artifacts/final.gds",
            "artifacts/final.def",
            "artifacts/final.nl.v",
            "artifacts/synthesis.json",
            "artifacts/synthesis.v",
        }
        expected.update(
            "artifacts/" + filename for filename, _module, _id in capture.RTL_INPUTS
        )
        actual = {
            path.relative_to(self.output).as_posix()
            for path in self.output.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual, expected)
        self.assertEqual(result["files"], 21)
        self.assertEqual(result["additional_eda_runs"], 0)
        self.assertEqual(result["saved_project_mutations"], 0)
        self.assertEqual(self._work_snapshot(), before)

        manifest = json.loads((self.output / "manifest.json").read_text("utf-8"))
        self.assertEqual(manifest["validation_status"], "Passed")
        self.assertEqual(set(manifest["files"]), expected - {"manifest.json"})
        for relative, declaration in manifest["files"].items():
            self.assertEqual(
                self._record((self.output / relative).read_bytes()), declaration
            )
        self.assertEqual(
            json.loads((self.output / "layout_record.json").read_text("utf-8")),
            self.run,
        )
        binding = json.loads(
            (self.output / "source_binding.json").read_text("utf-8")
        )
        observed = binding["synthesis_inputs"]["verilog"]
        self.assertFalse(observed["declared_in_original_retained_files"])
        self.assertEqual(
            observed["binding"],
            "new_read_only_observation_of_exact_adopted_result_sibling",
        )
        self.assertEqual(
            {key: observed[key] for key in ("bytes", "sha256")},
            self._record(self.synthesis_verilog_path.read_bytes()),
        )
        self.assertTrue(
            binding["structural_checks"][
                "final_netlist_def_exact_instance_master_match"
            ]
        )
        self.assertEqual(binding["structural_checks"]["final_cells"], 1)
        self.assertTrue(
            all(value == 0 for value in binding["derivation_activity"].values())
        )

    def test_existing_retained_synthesis_verilog_declaration_is_verified(self):
        raw = self.synthesis_verilog_path.read_bytes()
        self.run["checks"]["retained_files"].append(
            {"relative_path": capture.SYNTHESIS_VERILOG, **self._record(raw)}
        )
        self._write_store(rehash=True)
        self.expected_record_hash = self.run["record_hash"]

        self._capture()
        binding = json.loads(
            (self.output / "source_binding.json").read_text("utf-8")
        )
        observed = binding["synthesis_inputs"]["verilog"]
        self.assertTrue(observed["declared_in_original_retained_files"])
        self.assertEqual(
            observed["binding"], "original_checks.retained_files_declaration"
        )

    def test_rejects_source_byte_tamper_without_partial_archive(self):
        (self.artifact_root / "candidate_top.v").write_bytes(b"tampered\n")
        with self.assertRaisesRegex(capture.CaptureError, "do not match"):
            self._capture()
        self.assertFalse(self.output.exists())

    def test_rejects_run_record_hash_or_adoption_change(self):
        self.run["review_status"] = "Rejected"
        self._write_store(rehash=True)
        with self.assertRaisesRegex(capture.CaptureError, "Completed / Passed / Accepted"):
            self._capture()
        self.assertFalse(self.output.exists())

        self.run["review_status"] = "Accepted"
        self._write_store(rehash=True)
        self.run["source_key"] = "changed-after-hash"
        self._write_store(rehash=False)
        with self.assertRaisesRegex(capture.CaptureError, "record hash mismatch"):
            self._capture()
        self.assertFalse(self.output.exists())

    def test_rejects_nonlatest_run_and_wrong_working_root(self):
        self.store["runs"].append(
            {"id": "physical-workflow-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
        )
        self._write_store()
        with self.assertRaisesRegex(capture.CaptureError, "latest physical run"):
            self._capture()
        self.assertFalse(self.output.exists())

        self.store["runs"].pop()
        self._write_store()
        wrong = self.root / ".work/n2f/layout/hullcirq-layout-other"
        wrong.mkdir()
        with self.assertRaisesRegex(capture.CaptureError, "exact saved result"):
            self._capture(working_root=wrong)
        self.assertFalse(self.output.exists())

    def test_rejects_structural_graph_mismatch(self):
        self.synthesis_verilog_path.write_text(
            "module hullcirq_npu2_top(a, z);\n"
            "input a; output z;\n"
            "sky130_fd_sc_hd__inv_1 c0 (.A(a), .Y(z));\n"
            "endmodule\n",
            encoding="ascii",
        )
        with self.assertRaisesRegex(capture.CaptureError, "structural binding failed"):
            self._capture()
        self.assertFalse(self.output.exists())

    def test_existing_output_is_never_overwritten(self):
        self.output.mkdir()
        marker = self.output / "keep.txt"
        marker.write_bytes(b"keep")
        with self.assertRaisesRegex(capture.CaptureError, "never overwritten"):
            self._capture()
        self.assertEqual(marker.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()

"""Focused saved-view metadata checks; no circuit or EDA execution."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hullcirq.domain import DomainError
from hullcirq.readonly_view import build_readonly_context, SavedFiles
from hullcirq.store import ProjectStore


class ReadonlyViewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / ".work")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = ProjectStore(self.root)
        self.revision = self.store.envelope()["revision"]["id"]
        self.record = {"id": "layout-saved", "stage_id": "layout", "revision_id": self.revision,
                       "source_key": "source", "source_epoch_at_start": 1, "acceptance_epoch": 1,
                       "execution_status": "Completed", "validation_status": "Passed", "review_status": "Accepted",
                       "created_at": "saved-time", "checks": {"executed": True, "stdout": "x" * 50000},
                       "global_rtl": "module original; endmodule", "runtime_configuration": {"id": "original-profile"}}
        self.write("physical_workflow.json", {"runs": [self.record], "reviews": [], "source_key": "source", "source_epoch": 1})

    def write(self, name, value):
        (self.root / name).write_text(json.dumps(value), encoding="utf-8")

    def manifest(self):
        return [{"path": path.name, "size": len(raw := path.read_bytes()), "sha256": hashlib.sha256(raw).hexdigest()}
                for path in self.root.glob("*.json")]

    def test_pinned_compact_view_preserves_status_and_hydrates_original(self):
        original = {path.name: path.read_bytes() for path in self.root.glob("*.json")}
        with patch("hullcirq.physical_workflow.PhysicalWorkflowManager.__init__", side_effect=AssertionError("No manager startup")):
            context = build_readonly_context(self.root, expected_files=self.manifest())
            envelope = context.saved_envelope()
            record = envelope["physical_workflow"]["runs"][0]
            self.assertTrue(record["summary_only"])
            self.assertEqual(record["review_status"], "Accepted")
            self.assertNotIn("stdout", record["checks"])
            self.assertTrue(envelope["readonly_snapshot"]["source_manifest_verified"])
            self.assertFalse(envelope["physical_workflow"]["ready"])
            stage = context.stage_envelope("layout")
            self.assertTrue(stage["readonly_snapshot"]["compact"])
            self.assertEqual(stage["readonly_snapshot"]["loaded_stage"], "layout")
            full = stage["physical_workflow"]["runs"][0]
            self.assertFalse(full["summary_only"])
            self.assertEqual(full["checks"], self.record["checks"])
            self.assertEqual(context.physical_workflow.run("layout-saved")["global_rtl"], self.record["global_rtl"])
            self.assertEqual(context.physical_workflow.artifact("layout-saved", "runtime-configuration"), self.record["runtime_configuration"])
        self.assertEqual(original, {path.name: path.read_bytes() for path in self.root.glob("*.json")})

    def test_manifest_mismatch_is_rejected(self):
        manifest = self.manifest()
        self.write("physical_workflow.json", {"runs": []})
        with self.assertRaises(DomainError):
            build_readonly_context(self.root, expected_files=manifest)

    def test_unknown_evidence_stage_is_rejected(self):
        context = build_readonly_context(self.root, expected_files=self.manifest())
        with self.assertRaises(DomainError) as raised:
            context.stage_envelope("unknown-stage")
        self.assertEqual(raised.exception.status, 404)

    def test_latest_failed_local_run_does_not_inherit_older_adoption(self):
        first = dict(self.record, id="old-synthesis", stage_id="local_synthesis", node_id="node-a", input_hash="input")
        last = dict(first, id="new-synthesis", validation_status="Failed", review_status="Awaiting Review")
        self.write("workflow.json", {"runs": [first, last], "node_inputs": {"node-a": "input"}, "node_epochs": {"node-a": 1}})
        context = build_readonly_context(self.root, expected_files=self.manifest())
        synthesis = next(item for item in context.workflow.envelope()["workflow_nodes"] if item["stage_id"] == "local_synthesis")
        self.assertIsNone(synthesis["accepted_run_id"])
        self.assertEqual(synthesis["latest_run_id"], "new-synthesis")

    def test_file_changed_between_pin_and_lazy_read_is_rejected(self):
        files = SavedFiles(self.root, self.manifest())
        self.write("physical_workflow.json", {"runs": []})
        with self.assertRaises(DomainError):
            files.load("physical_workflow.json")

    def test_saved_synthesis_batch_is_inspectable_without_execution_or_original_writes(self):
        batch = {"id": "batch-saved", "request_id": "saved-request", "stage_id": "local_synthesis",
                 "revision_id": self.revision, "execution_status": "Interrupted", "validation_status": "Not Checked",
                 "items": [{"node_id": "node-a", "candidate_id": None, "run_id": None,
                            "status": "Interrupted", "reason": "Explicit continuation required."}]}
        self.write("workflow.json", {"runs": [], "reviews": [], "node_inputs": {}, "node_epochs": {}, "batches": [batch]})
        original = {path.name: path.read_bytes() for path in self.root.glob("*.json")}
        with patch("hullcirq.workflow.WorkflowManager.__init__", side_effect=AssertionError("No live manager startup")):
            context = build_readonly_context(self.root, expected_files=self.manifest())
            envelope = context.workflow.envelope()
            self.assertEqual(envelope["workflow_latest_batch_id"], batch["id"])
            self.assertIsNone(envelope["workflow_active_batch_id"])
            self.assertEqual(context.workflow.batch(batch["id"])["items"], batch["items"])
            self.assertEqual(envelope["workflow_batches"][0]["execution_status"], "Interrupted")
        self.assertEqual(original, {path.name: path.read_bytes() for path in self.root.glob("*.json")})

    def test_old_epoch_withdraws_effective_adoption_without_rewriting_record(self):
        self.write("physical_workflow.json", {"runs": [self.record], "reviews": [], "source_key": "source", "source_epoch": 2})
        context = build_readonly_context(self.root, expected_files=self.manifest())
        record = context.physical_workflow.run("layout-saved")
        self.assertEqual(record["freshness"], "Stale")
        self.assertEqual(record["review_status"], "Awaiting Review")
        self.assertEqual(context.physical_workflow._run("layout-saved")["review_status"], "Accepted")

    def test_selected_record_and_stage_keep_other_history_compact(self):
        previous = dict(self.record, id="layout-older", acceptance_epoch=0, source_epoch_at_start=0)
        self.write("physical_workflow.json", {"runs": [previous, self.record], "reviews": [], "source_key": "source", "source_epoch": 1})
        context = build_readonly_context(self.root, expected_files=self.manifest())
        records = context.stage_envelope("layout", ["layout-older"])["physical_workflow"]["runs"]
        self.assertFalse(records[0]["summary_only"])
        self.assertTrue(records[1]["summary_only"])
        with self.assertRaises(DomainError):
            context.stage_envelope("layout", ["missing"])

    def test_download_preserves_existing_artifact_hash_validation(self):
        payload = b"saved-layout"
        directory = self.root / "artifacts"
        directory.mkdir()
        (directory / "final.gds").write_bytes(payload)
        self.record["checks"].update(artifacts_directory=str(directory), artifacts=[{"id": "gds", "relative_path": "final.gds",
            "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(), "content_type": "application/octet-stream"}])
        self.write("physical_workflow.json", {"runs": [self.record], "reviews": [], "source_key": "source", "source_epoch": 1})
        context = build_readonly_context(self.root, expected_files=self.manifest())
        self.assertEqual(context.physical_workflow.artifact_bytes("layout-saved", "gds")[0], payload)
        (directory / "final.gds").write_bytes(b"changed")
        with self.assertRaises(DomainError):
            context.physical_workflow.artifact_bytes("layout-saved", "gds")


if __name__ == "__main__":
    unittest.main()

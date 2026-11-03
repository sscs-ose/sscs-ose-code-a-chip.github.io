"""Preserved repair advice is inspectable without model workers or migrations."""
import json
from pathlib import Path
import tempfile
import unittest

from hullcirq.domain import DomainError
from hullcirq.readonly_view import build_readonly_context
from hullcirq.store import ProjectStore


class SavedRepairAnalysisTests(unittest.TestCase):
    def directory(self):
        return tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / ".work")

    def test_absent_history_does_not_create_store(self):
        with self.directory() as directory:
            root = Path(directory)
            ProjectStore(root)
            before = {path.name: path.read_bytes() for path in root.glob("*.json")}
            context = build_readonly_context(root)
            self.assertEqual(context.repair_analysis.envelope()["repair_analysis"]["jobs"], [])
            self.assertFalse(context.repair_analysis.is_active())
            self.assertEqual(before, {path.name: path.read_bytes() for path in root.glob("*.json")})

    def test_exact_request_and_raw_answer_remain_saved_and_execution_disabled(self):
        with self.directory() as directory:
            root = Path(directory)
            ProjectStore(root)
            path = root / "repair_analysis.json"
            record = {"id": "analysis-one", "execution_status": "Running", "raw_content": "Advice only\n",
                      "raw_reasoning": "retained reasoning", "events": [{"type": "delta", "content": "Advice only\n"}],
                      "context": {"messages": [{"role": "user", "content": "Original requirement\nRTL\nError"}]}}
            path.write_text(json.dumps({"version": "0.1", "plans": [], "jobs": [record]}), encoding="utf-8")
            before = path.read_bytes()
            context = build_readonly_context(root)
            observed = context.repair_analysis.job("analysis-one")
            self.assertEqual(observed["execution_status"], "Interrupted")
            self.assertEqual(observed["recorded_execution_status"], "Running")
            self.assertEqual(observed["raw_content"], record["raw_content"])
            self.assertEqual(observed["context"], record["context"])
            self.assertIsNone(context.repair_analysis.envelope()["repair_analysis"]["active_job_id"])
            for action in ("preview", "start", "cancel"):
                self.assertFalse(hasattr(context.repair_analysis, action))
            observed["context"]["messages"][0]["content"] = "attempted view mutation"
            self.assertEqual(context.repair_analysis.job("analysis-one")["context"], record["context"])
            with self.assertRaises(DomainError):
                context.repair_analysis.job("missing")
            context.repair_analysis.close()
            self.assertEqual(path.read_bytes(), before)

    def test_malformed_history_is_not_silently_ignored(self):
        with self.directory() as directory:
            root = Path(directory)
            ProjectStore(root)
            path = root / "repair_analysis.json"
            path.write_text('{"jobs": {"wrong": "shape"}}', encoding="utf-8")
            before = path.read_bytes()
            context = build_readonly_context(root)
            with self.assertRaises(DomainError):
                context.repair_analysis.envelope()
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()

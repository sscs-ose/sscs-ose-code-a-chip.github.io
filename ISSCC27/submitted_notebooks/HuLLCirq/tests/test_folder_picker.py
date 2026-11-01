"""Native chooser management tests using software runners; no native UI opened."""
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.domain import DomainError
from hullcirq.folder_picker import FolderPickerManager


class FolderPickerTests(unittest.TestCase):
    def setUp(self):
        self.release = threading.Event()
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".work")
        self.manager = FolderPickerManager(ROOT, runner=self.run_picker)

    def run_picker(self, identifier, initial):
        self.release.wait(2)
        return {"status": "Completed", "directory": self.temp.name}

    def tearDown(self):
        self.release.set()
        self.manager.close()
        self.temp.cleanup()

    def completed(self, identifier):
        self.release.set()
        for _ in range(100):
            result = self.manager.status(identifier, "page-a")
            if result["status"] != "Pending":
                return result
            time.sleep(.001)
        self.fail("Software chooser runner did not finish")

    def test_start_returns_without_waiting_for_user_selection(self):
        picker = self.manager.start("page-a")
        self.assertEqual(picker["status"], "Pending")
        self.assertEqual(self.completed(picker["id"])["directory"], self.temp.name)

    def test_other_page_cannot_read_chosen_path(self):
        picker = self.manager.start("page-a")
        with self.assertRaises(DomainError):
            self.manager.status(picker["id"], "page-b")

    def test_cancel_cannot_be_overwritten_by_late_selection(self):
        picker = self.manager.start("page-a")
        self.manager.cancel(picker["id"], "page-a")
        self.assertEqual(self.completed(picker["id"])["status"], "Cancelled")

    def test_second_native_picker_is_rejected_while_one_is_open(self):
        self.manager.start("page-a")
        with self.assertRaises(DomainError):
            self.manager.start("page-a")

    def test_failed_native_runner_returns_manual_path_fallback(self):
        def failure(*args):
            raise RuntimeError("software fixture")
        self.manager.runner = failure
        picker = self.manager.start("page-a")
        result = self.completed(picker["id"])
        self.assertEqual(result["status"], "Failed")
        self.assertIn("absolute folder path", result["error"])


if __name__ == "__main__":
    unittest.main()

"""Recoverable catalog deletion; isolated stores only, no model or EDA work."""
import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.domain import DomainError
from hullcirq.store import ProjectStore
from hullcirq.workspace import PROJECT_MANIFEST, WorkspaceRegistry, digest


class ProjectTrashTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".work")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.registry = WorkspaceRegistry(self.base / "workspace")
        created = self.registry.create_project("Trash QA", "First", "first_top", self.base / "external")
        self.pid, self.sid = created["project_id"], created["system_id"]
        self.path = Path(created["project"]["directory"])
        self.registry.create_system(self.pid, "Second", "second_top")
        source = self.registry.resolve_system(self.pid, self.sid)["path"]
        (source / "generation_batches.json").write_bytes(b'{"batches":[{"id":"retained-batch"}],"wide":123456789012345678901234567890}\n')
        (source / "original.bin").write_bytes(b"original\x00output")
        self.registry.mark_recent(self.pid, self.sid)

    def project(self):
        return next(p for p in self.registry.catalog()["projects"] if p["id"] == self.pid)

    def delete(self):
        return self.registry.delete_project(self.pid, self.project()["management_revision"])

    def assert_code(self, code, action):
        with self.assertRaises(DomainError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)

    def bytes(self):
        return {str(p.relative_to(self.path)): p.read_bytes() for p in self.path.rglob("*") if p.is_file()}

    def test_delete_restart_restore_retains_every_byte_identity_and_path(self):
        before, project = self.bytes(), self.project()
        shared = self.registry.root / "components" / "keep.json"
        shared.parent.mkdir(parents=True, exist_ok=True)
        shared.write_bytes(b'{"shared":"retained"}')
        # Do not use catalog() while a deliberately opaque library sentinel is present.
        entry = self.delete_with_revision(project["management_revision"])
        self.assertEqual(self.bytes(), before)
        self.assertEqual(shared.read_bytes(), b'{"shared":"retained"}')
        self.assertEqual(self.registry._registry["projects"], [])
        self.assertEqual(self.registry._registry["recent"], [])
        self.assertEqual(entry["project"]["id"], self.pid)
        reloaded = WorkspaceRegistry(self.registry.root)
        restored = reloaded.restore_deleted_project(entry["id"], digest(entry["project"]))
        self.assertEqual(restored["project_id"], self.pid)
        self.assertEqual(restored["project"]["directory"], str(self.path))
        self.assertEqual([s["id"] for s in restored["project"]["systems"]], [s["id"] for s in project["systems"]])
        self.assertEqual(reloaded._registry["trash"], [])
        self.assertEqual(self.bytes(), before)
        self.assertEqual(shared.read_bytes(), b'{"shared":"retained"}')

    def delete_with_revision(self, revision):
        return self.registry.delete_project(self.pid, revision)

    def test_stale_missing_and_duplicate_deletion_are_rejected(self):
        old = self.project()["management_revision"]
        self.registry.rename_project(self.pid, "Changed")
        original = self.registry.registry_path.read_bytes()
        self.assert_code("project_management_changed", lambda: self.registry.delete_project(self.pid, old))
        self.assertEqual(self.registry.registry_path.read_bytes(), original)
        self.assert_code("project_management_changed", lambda: self.registry.delete_project(self.pid, None))
        self.delete()
        self.assert_code("project_not_found", lambda: self.registry.delete_project(self.pid, old))

    def test_trashed_folder_identity_copy_and_nested_create_cannot_bypass_restore(self):
        entry = self.delete()
        self.assert_code("project_in_trash", lambda: self.registry.register_project_directory(str(self.path)))
        duplicate = self.base / "copied-folder"
        duplicate.mkdir()
        (duplicate / PROJECT_MANIFEST).write_bytes((self.path / PROJECT_MANIFEST).read_bytes())
        self.assert_code("project_in_trash", lambda: self.registry.register_project_directory(str(duplicate)))
        self.assert_code("project_directory_in_use", lambda: self.registry.create_project("Nested", project_directory=self.path / "child"))
        self.assert_code("project_not_found", lambda: self.registry.resolve_system(self.pid, self.sid))
        self.registry.restore_deleted_project(entry["id"], digest(entry["project"]))
        self.assertEqual(self.registry.register_project_directory(str(self.path))["project_id"], self.pid)

    def test_restore_requires_current_trash_entry_and_does_not_overwrite_changed_marker(self):
        entry = self.delete()
        self.assert_code("project_management_changed", lambda: self.registry.restore_deleted_project(entry["id"], "stale"))
        marker = self.path / PROJECT_MANIFEST
        original = marker.read_bytes()
        marker.write_text('{"changed":true}', encoding="utf-8")
        catalog = self.registry.registry_path.read_bytes()
        self.assert_code("trash_project_unavailable", lambda: self.registry.restore_deleted_project(entry["id"], digest(entry["project"])))
        self.assertEqual(marker.read_bytes(), b'{"changed":true}')
        self.assertEqual(self.registry.registry_path.read_bytes(), catalog)
        marker.write_bytes(original)
        self.registry.restore_deleted_project(entry["id"], digest(entry["project"]))
        self.assert_code("trash_not_found", lambda: self.registry.restore_deleted_project(entry["id"], digest(entry["project"])))

    def test_failed_registry_write_leaves_catalog_and_all_files_unchanged(self):
        project, before = self.project(), self.bytes()
        index = self.registry.registry_path.read_bytes()
        with patch("hullcirq.workspace.write_json", side_effect=OSError("disk unavailable")):
            with self.assertRaises(OSError):
                self.registry.delete_project(self.pid, project["management_revision"])
        self.assertEqual(self.registry.registry_path.read_bytes(), index)
        self.assertEqual(self.project(), project)
        self.assertEqual(self.bytes(), before)
        entry = self.delete()
        catalog = copy.deepcopy(self.registry._registry)
        with patch("hullcirq.workspace.write_json", side_effect=OSError("disk unavailable")):
            with self.assertRaises(OSError):
                self.registry.restore_deleted_project(entry["id"], digest(entry["project"]))
        self.assertEqual(self.registry._registry, catalog)
        self.assertEqual(self.bytes(), before)

    def test_malformed_duplicate_trash_catalog_fails_closed(self):
        entry = self.delete()
        path = self.registry.registry_path
        valid = path.read_bytes()
        for trash in ({}, [entry, entry], [{"id": "bad"}], [entry | {"project": entry["project"] | {"systems": "bad"}}]):
            malformed = copy.deepcopy(self.registry._registry)
            malformed["trash"] = trash
            path.write_text(json.dumps(malformed), encoding="utf-8")
            with self.subTest(trash=trash), self.assertRaises(DomainError):
                WorkspaceRegistry(self.registry.root)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), malformed)
        path.write_bytes(valid)

    def test_backup_restores_generation_batch_history_exactly_with_existing_bounds(self):
        source = self.registry.resolve_system(self.pid, self.sid)["path"]
        original = (source / "generation_batches.json").read_bytes()
        backup = self.registry.backup_project(self.pid)
        self.assertIn(f"systems/{self.sid}/generation_batches.json", [item["path"] for item in backup["files"]])
        restored = self.registry.restore_project(backup)
        target = self.registry.resolve_system(restored["project_id"], restored["system_id"])["path"]
        self.assertEqual((target / "generation_batches.json").read_bytes(), original)
        with patch("hullcirq.workspace.MAX_BUNDLE_BYTES", 1):
            self.assert_code("backup_limit", lambda: self.registry.backup_project(self.pid))

    def test_deleted_legacy_snapshot_stays_in_trash_on_boot_without_source_changes(self):
        source = ProjectStore(self.base / "legacy")
        original = source.state_path.read_bytes()
        legacy = self.registry.register_legacy(source.path)
        entry = self.registry.delete_project(legacy["project_id"], legacy["project"]["management_revision"])
        self.assert_code("project_in_trash", lambda: self.registry.register_legacy(source.path))
        self.assertEqual(source.state_path.read_bytes(), original)
        spec = importlib.util.spec_from_file_location("trash_qa_run_workspace", ROOT / "scripts" / "run_workspace.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(sys, "argv", ["run_workspace.py", "--workspace-dir", str(self.registry.root), "--legacy-data-dir", str(source.path)]), patch.object(module, "make_workspace_server", side_effect=KeyboardInterrupt):
            self.assertEqual(module.main(), 0)
        self.assertEqual(WorkspaceRegistry(self.registry.root)._registry["trash"][-1]["id"], entry["id"])
        self.assertEqual(source.state_path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()

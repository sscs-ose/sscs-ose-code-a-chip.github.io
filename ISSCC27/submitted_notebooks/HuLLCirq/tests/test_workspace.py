"""Focused project persistence/isolation checks; no circuit flow is executed."""
import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hullcirq.domain import DomainError
from hullcirq.store import ProjectStore
from hullcirq.workspace import PROJECT_MANIFEST, WorkspaceRegistry, digest


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        qa = Path(__file__).resolve().parents[1] / ".work" / "wm"
        qa.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=qa)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = WorkspaceRegistry(self.root / "workspace")
        self.created = self.registry.create_project("Example", "Main", "example_top")
        self.pid, self.sid = self.created["project_id"], self.created["system_id"]

    def resolve(self, sid=None):
        return self.registry.resolve_system(self.pid, sid or self.sid)

    def test_new_blank_project_and_restart_preserve_identity_without_evidence(self):
        store = ProjectStore(self.resolve()["path"])
        env = store.envelope()
        self.assertEqual(env["design"]["nodes"], [])
        self.assertEqual(env["runs"], [])
        self.assertEqual(env["reviews"], [])
        self.assertEqual(env["review_policy"]["mode"], "manual")
        self.assertTrue(all(s["execution_status"] == "Not Run" for s in env["workflow"]))
        self.assertEqual(env["design"]["system"]["id"], self.sid)
        self.assertEqual(WorkspaceRegistry(self.root / "workspace").resolve_system(self.pid, self.sid)["path"], self.resolve()["path"])

    def test_system_isolation_and_distinct_top(self):
        second = self.registry.create_system(self.pid, "Other", "other_top")
        first_path = self.resolve()["path"] / "state.json"
        previous = first_path.read_bytes()
        store = ProjectStore(self.resolve(second["system_id"])["path"])
        env = store.envelope()
        design = env["design"]
        design["settings"]["clock_period_ns"] = 77
        design["settings"]["top_module"] = "updated_top"
        store.save(design, env["revision"]["id"])
        self.assertEqual(first_path.read_bytes(), previous)
        self.assertNotEqual(self.sid, second["system_id"])
        catalog = self.registry.catalog()
        self.assertEqual(next(s for s in catalog["projects"][0]["systems"] if s["id"] == second["system_id"])["top_module"], "updated_top")
        self.assertEqual(self.resolve(second["system_id"])["system"]["top_module"], "updated_top")
        with self.assertRaises(DomainError):
            self.registry.resolve_system("../../escape", self.sid)

    def test_metadata_renames_leave_evidence_bytes_unchanged_and_recent_persisted(self):
        path = self.resolve()["path"] / "state.json"
        original = path.read_bytes()
        self.registry.rename_project(self.pid, "Renamed")
        self.registry.rename_system(self.pid, self.sid, "A")
        self.registry.mark_recent(self.pid, self.sid)
        self.assertEqual(path.read_bytes(), original)
        cat = WorkspaceRegistry(self.root / "workspace").catalog()
        self.assertEqual(cat["projects"][0]["name"], "Renamed")
        self.assertEqual(cat["recent"][0]["system_id"], self.sid)

    def test_legacy_snapshot_original_untouched_and_duplicate_has_no_adoption(self):
        legacy = self.root / "legacy"
        old_store = ProjectStore(legacy)
        env = old_store.envelope()
        old_store.validate("global_settings", env["revision"]["id"])
        (legacy / "generation.json").write_text('{"source":"retained history"}', encoding="utf-8")
        old_bytes = {p.name: p.read_bytes() for p in legacy.glob("*.json")}
        registered = self.registry.register_legacy(legacy)
        self.assertTrue(registered["system"]["read_only"])
        mounted = self.registry.resolve_system(registered["project_id"], registered["system_id"])
        self.assertEqual({p.name: p.read_bytes() for p in mounted["path"].glob("*.json")}, old_bytes)
        again = self.registry.register_legacy(legacy)
        self.assertEqual(again["project_id"], registered["project_id"])
        clone = self.registry.duplicate_system(registered["project_id"], registered["system_id"])
        clone_path = self.registry.resolve_system(clone["project_id"], clone["system_id"])["path"]
        cloned = ProjectStore(clone_path).envelope()
        self.assertEqual(cloned["runs"], [])
        self.assertEqual(cloned["reviews"], [])
        self.assertNotEqual(cloned["revision"]["id"], old_store.envelope()["revision"]["id"])
        self.assertEqual((clone_path / "provenance_snapshot" / "state.json").read_bytes(), old_bytes["state.json"])
        self.assertEqual({p.name: p.read_bytes() for p in legacy.glob("*.json")}, old_bytes)

    def test_backup_restore_all_local_bytes_readonly_and_new_workspace_ids(self):
        path = self.resolve()["path"]
        (path / "history.bin").write_bytes(b"retained\x00bytes")
        backup = self.registry.backup_project(self.pid)
        restored = self.registry.restore_project(backup)
        resolved = self.registry.resolve_system(restored["project_id"], restored["system_id"])
        self.assertNotEqual(restored["project_id"], self.pid)
        self.assertNotEqual(restored["system_id"], self.sid)
        self.assertTrue(resolved["read_only"])
        self.assertEqual((resolved["path"] / "state.json").read_bytes(), (path / "state.json").read_bytes())
        self.assertEqual((resolved["path"] / "history.bin").read_bytes(), b"retained\x00bytes")
        self.assertIn("references", backup["external_references"][0]["scope"])

    def test_backup_corruption_and_path_traversal_do_not_create_project(self):
        backup = self.registry.backup_project(self.pid)
        original_catalog = self.registry.catalog()
        for mutation in ("checksum", "path", "gzip", "size", "duplicate"):
            value = copy.deepcopy(backup)
            entry = value["files"][0]
            if mutation == "checksum":
                entry["sha256"] = "0" * 64
            elif mutation == "path":
                entry["path"] = "../outside.json"
            elif mutation == "gzip":
                entry["data"] = "AA=="
            elif mutation == "size":
                entry["size"] = 1
            else:
                value["files"].append(copy.deepcopy(entry))
            value["checksum"] = digest({k: v for k, v in value.items() if k != "checksum"})
            with self.subTest(mutation=mutation), self.assertRaises(DomainError):
                self.registry.restore_project(value)
            self.assertEqual(self.registry.catalog(), original_catalog)
        self.assertFalse((self.root / "outside.json").exists())

    def test_duplicate_project_has_all_systems_and_original_files_unchanged(self):
        self.registry.create_system(self.pid, "Second", "second")
        before = {str(p.relative_to(self.registry.root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.registry._project_path(self.pid).rglob("*") if p.is_file()}
        clone = self.registry.duplicate_project(self.pid)
        self.assertEqual(len(clone["project"]["systems"]), 2)
        self.assertTrue(all(not s["read_only"] for s in clone["project"]["systems"]))
        after = {str(p.relative_to(self.registry.root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.registry._project_path(self.pid).rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_failed_catalog_commit_does_not_leave_new_project(self):
        before = list(self.registry._project_path(self.pid).parent.iterdir())
        with patch.object(self.registry, "_save", side_effect=OSError("simulated disk error")):
            with self.assertRaises(OSError):
                self.registry.create_project("Will fail")
        self.assertEqual(list(self.registry._project_path(self.pid).parent.iterdir()), before)

    def test_create_in_selected_folder_reopen_in_other_workspace_without_rewriting(self):
        directory = self.root / "selected" / "My Project"
        created = self.registry.create_project("Selected", project_directory=str(directory))
        pid, sid = created["project_id"], created["system_id"]
        self.assertEqual(created["project"]["directory"], str(directory.resolve()))
        resolved = self.registry.resolve_system(pid, sid)
        self.assertEqual(resolved["path"], directory / "systems" / sid)
        (resolved["path"] / "history.json").write_text('{"original":true}', encoding="utf-8")
        before = {str(p.relative_to(directory)): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
        other = WorkspaceRegistry(self.root / "different_workspace")
        opened = other.register_project_directory(str(directory))
        self.assertEqual(opened["project_id"], pid)
        self.assertEqual(other.resolve_system(pid, sid)["path"], resolved["path"])
        self.assertEqual(before, {str(p.relative_to(directory)): p.read_bytes() for p in directory.rglob("*") if p.is_file()})
        self.assertEqual(other.register_project_directory(str(directory))["project_id"], pid)
        self.assertEqual(len(other.catalog()["projects"]), 1)
        self.assertEqual(WorkspaceRegistry(other.root).resolve_system(pid, sid)["path"], resolved["path"])

    def test_selected_folder_metadata_tracks_rename_add_duplicate_and_saved_top(self):
        directory = self.root / "selected"
        created = self.registry.create_project("Selected", project_directory=str(directory))
        pid, sid = created["project_id"], created["system_id"]
        self.registry.rename_project(pid, "Renamed")
        self.registry.rename_system(pid, sid, "Renamed system")
        second = self.registry.create_system(pid, "Second", "second_top")
        self.registry.duplicate_system(pid, second["system_id"], "Second copy")
        store = ProjectStore(self.registry.resolve_system(pid, sid)["path"])
        env = store.envelope()
        design = env["design"]
        design["settings"]["top_module"] = "saved_top"
        store.save(design, env["revision"]["id"])
        saved_state = (self.registry.resolve_system(pid, sid)["path"] / "state.json").read_bytes()
        self.registry.refresh_project_manifest(pid)
        other = WorkspaceRegistry(self.root / "other")
        reopened = other.register_project_directory(str(directory))
        self.assertEqual(reopened["project"]["name"], "Renamed")
        self.assertEqual(len(reopened["project"]["systems"]), 3)
        current = other.resolve_system(pid, sid)
        self.assertEqual(current["system"]["name"], "Renamed system")
        self.assertEqual(current["system"]["top_module"], "saved_top")
        self.assertEqual((current["path"] / "state.json").read_bytes(), saved_state)

    def test_selected_folder_rejects_relative_root_nonempty_and_identity_conflict(self):
        nonempty = self.root / "nonempty"
        nonempty.mkdir()
        keep = nonempty / "keep.txt"
        keep.write_text("keep", encoding="utf-8")
        before = self.registry.catalog()
        for path in ("relative", str(Path(self.root.anchor)), str(nonempty)):
            with self.subTest(path=path), self.assertRaises(DomainError):
                self.registry.create_project("Rejected", project_directory=path)
        self.assertEqual(self.registry.catalog(), before)
        self.assertEqual(keep.read_text(encoding="utf-8"), "keep")
        with self.assertRaises(DomainError) as caught:
            self.registry.create_project("Nested", project_directory=str(self.registry._project_path(self.pid) / "nested"))
        self.assertEqual(caught.exception.code, "project_directory_in_use")
        copied = self.root / "identity_copy"
        import shutil
        shutil.copytree(self.registry._project_path(self.pid), copied)
        with self.assertRaises(DomainError) as caught:
            self.registry.register_project_directory(str(copied))
        self.assertEqual(caught.exception.code, "project_identity_conflict")

    def test_failed_external_create_preserves_preexisting_empty_folder(self):
        for existed in (False, True):
            directory = self.root / ("empty" if existed else "new")
            if existed:
                directory.mkdir()
            with self.subTest(existed=existed), patch.object(self.registry, "_save", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    self.registry.create_project("Fail", project_directory=str(directory))
            self.assertEqual(directory.exists(), existed)
            if existed:
                self.assertEqual(list(directory.iterdir()), [])

    def test_catalog_commit_failure_rolls_back_external_marker_and_new_system(self):
        created = self.registry.create_project("External", project_directory=str(self.root / "external"))
        pid = created["project_id"]
        marker = self.registry._project_path(pid) / PROJECT_MANIFEST
        before, catalog = marker.read_bytes(), self.registry.catalog()
        from hullcirq.workspace import write_json as original_write
        def fail_index(path, value):
            if path == self.registry.registry_path:
                raise OSError("catalog disk full")
            original_write(path, value)
        with patch("hullcirq.workspace.write_json", side_effect=fail_index):
            with self.assertRaises(OSError):
                self.registry.create_system(pid, "No commit")
        self.assertEqual(marker.read_bytes(), before)
        self.assertEqual(self.registry.catalog(), catalog)
        self.assertEqual(len(list((marker.parent / "systems").iterdir())), 1)

    def test_open_folder_rejects_missing_manifest_malformed_state_and_links(self):
        directory = self.root / "external"
        created = self.registry.create_project("External", project_directory=str(directory))
        other = WorkspaceRegistry(self.root / "other")
        state_path = self.registry.resolve_system(created["project_id"], created["system_id"])["path"] / "state.json"
        valid = state_path.read_bytes()
        state_path.write_text('{"store_version":"wrong"}', encoding="utf-8")
        with self.assertRaises(DomainError) as caught:
            other.register_project_directory(str(directory))
        self.assertEqual(caught.exception.code, "invalid_project_state")
        self.assertEqual(other.catalog()["projects"], [])
        state_path.write_bytes(valid)
        missing = self.root / "missing"
        missing.mkdir()
        with self.assertRaises(DomainError):
            other.register_project_directory(str(missing))
        link = self.root / "linked"
        try:
            link.symlink_to(directory, target_is_directory=True)
        except OSError:
            return
        with self.assertRaises(DomainError):
            other.register_project_directory(str(link))

    def test_external_backup_restore_and_duplicate_never_reuse_exported_directory(self):
        directory = self.root / "external"
        created = self.registry.create_project("External", project_directory=str(directory))
        pid = created["project_id"]
        backup = self.registry.backup_project(pid)
        self.assertEqual(backup["project"]["directory"], str(directory.resolve()))
        self.assertNotIn(PROJECT_MANIFEST, [entry["path"] for entry in backup["files"]])
        before = {str(p.relative_to(directory)): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
        backup["project"]["directory"] = str(self.root / "untrusted-export-directory")
        backup["checksum"] = digest({k: v for k, v in backup.items() if k != "checksum"})
        restored = self.registry.restore_project(backup)
        duplicated = self.registry.duplicate_project(pid)
        for result in (restored, duplicated):
            path = self.registry._project_path(result["project_id"])
            self.assertTrue(path.is_relative_to(self.registry.root / "projects"))
            self.assertTrue((path / PROJECT_MANIFEST).is_file())
        self.assertFalse((self.root / "untrusted-export-directory").exists())
        self.assertEqual(before, {str(p.relative_to(directory)): p.read_bytes() for p in directory.rglob("*") if p.is_file()})

    def test_backup_restores_pinned_components_and_rejects_missing_dependencies(self):
        legacy = self.root / "legacy"
        ProjectStore(legacy)
        source = self.registry.register_legacy(legacy)
        meta = self.registry.publish_component(source["project_id"], source["system_id"], name="Reusable")
        env = ProjectStore(self.resolve()["path"]).envelope()
        self.registry.instantiate_component(self.pid, self.sid, meta["id"], meta["version"], env["revision"]["id"], "First")
        backup = self.registry.backup_project(self.pid)
        self.assertEqual(len(backup["components"]), 1)
        other = WorkspaceRegistry(self.root / "other")
        restored = other.restore_project(backup)
        self.assertTrue(restored["system"]["read_only"])
        self.assertEqual(other.component_package(meta["id"], 1)["sha256"], meta["sha256"])
        bad = copy.deepcopy(backup)
        bad["components"] = []
        bad["checksum"] = digest({k: v for k, v in bad.items() if k != "checksum"})
        before = other.catalog()
        with self.assertRaises(DomainError) as caught:
            other.restore_project(bad)
        self.assertEqual(caught.exception.code, "backup_dependency_missing")
        self.assertEqual(other.catalog(), before)


if __name__ == "__main__":
    unittest.main()

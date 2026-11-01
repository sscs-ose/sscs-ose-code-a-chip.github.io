"""Bounded isolated evidence-transfer tests; no model or EDA starts."""
import copy
import gzip
import base64
import json
import os
import tempfile
import unittest
import subprocess
import sys
import shutil
from pathlib import Path
from unittest.mock import patch

from hullcirq.domain import DomainError
from hullcirq.workspace import WorkspaceRegistry, digest, write_json
from hullcirq.portable_projects import (export_project, validate_package, restore_project, inspect_project,
                                        artifact_bytes, sha, _pack, safe_file, io_path)
from hullcirq.verification import object_hash

ROOT = Path(__file__).resolve().parents[1]


class PortableProjectsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".work")
        self.root = Path(self.temp.name)
        self.registry = WorkspaceRegistry(self.root / "workspace")
        self.created = self.registry.create_project("Software QA raw evidence", "Pipeline", "pipe_top")
        self.pid, self.sid = self.created["project_id"], self.created["system_id"]
        self.system = self.registry._system_path(self.pid, self.sid)
        self.before = (self.system / "state.json").read_bytes()
        self.job = "physical-workflow-" + "1" * 32
        self.artifacts = self.root / ".work" / "results" / "run"
        self.artifacts.mkdir(parents=True)
        self.raw = b"SOFTWARE QA\r\nraw\x00layout"
        (self.artifacts / "layout.gds").write_bytes(self.raw)
        checks = {"artifacts_directory": str(self.artifacts), "artifacts": [
            {"id": "gds", "relative_path": "layout.gds", "bytes": len(self.raw), "sha256": sha(self.raw)}]}
        write_json(self.system / "physical_workflow.json", {"runs": [{"id": self.job, "checks": checks}]})

    def tearDown(self):
        # Long-path fixtures must be removed through the same OS I/O boundary.
        # Delete only this test's exact owned temporary directory.
        self.assertEqual(self.root.resolve().parent, (ROOT / ".work").resolve())
        self.assertTrue(self.root.name.startswith("tmp"))
        if io_path(self.root).exists():
            shutil.rmtree(io_path(self.root))
        self.temp.cleanup()

    def package(self):
        # Software fixture intentionally has no real source-bound Functional Map.
        with patch("hullcirq.portable_projects._export_maps"):
            return export_project(self.registry, self.pid, self.root)

    @staticmethod
    def seal(value):
        value["checksum"] = digest({key: item for key, item in value.items() if key != "checksum"})
        return value

    def test_raw_stores_and_external_artifact_restore_fresh_readonly_and_reexport(self):
        package = self.package()
        self.assertEqual(len(package["entries"]), 1)
        restored = restore_project(self.registry, package)
        self.assertNotEqual(restored["project_id"], self.pid)
        self.assertNotEqual(restored["system_id"], self.sid)
        self.assertTrue(restored["system"]["read_only"])
        path = self.registry._system_path(restored["project_id"], restored["system_id"])
        self.assertEqual((path / "state.json").read_bytes(), self.before)
        self.assertEqual((self.system / "state.json").read_bytes(), self.before)
        view = inspect_project(self.registry, restored["project_id"])
        self.assertFalse(view["host_execution_ready"])
        artifact = next(entry for entry in view["entries"] if entry.get("kind") == "eda_artifact")
        self.assertEqual(artifact_bytes(self.registry, restored["project_id"], artifact["file_id"])[0], self.raw)
        # No foreign paths are read when re-exporting an attachment.
        with patch("hullcirq.portable_projects._export_maps", side_effect=AssertionError("foreign map lookup")):
            again = export_project(self.registry, restored["project_id"], self.root)
        validate_package(again)
        self.assertEqual(again["entries"][0]["sha256"], sha(self.raw))
        restored_again = restore_project(self.registry, again)
        self.assertTrue(restored_again["system"]["read_only"])

    def test_duplicate_is_explicit_editable_design_with_no_imported_acceptance(self):
        restored = restore_project(self.registry, self.package())
        clone = self.registry.duplicate_system(restored["project_id"], restored["system_id"])
        self.assertFalse(clone["system"]["read_only"])
        state = json.loads((self.registry._system_path(clone["project_id"], clone["system_id"]) / "state.json").read_text())
        self.assertEqual(state["runs"], [])
        self.assertEqual(state["reviews"], [])
        self.assertNotIn("adoption_policy", state)

    def test_external_hash_mismatch_fails_without_catalog_mutation(self):
        (self.artifacts / "layout.gds").write_bytes(b"changed")
        before = copy.deepcopy(self.registry._registry)
        with self.assertRaises(DomainError):
            self.package()
        self.assertEqual(before, self.registry._registry)

    def test_missing_artifact_is_disclosed_not_faked(self):
        (self.artifacts / "layout.gds").unlink()
        value = self.package()
        self.assertEqual(value["entries"], [])
        self.assertEqual(value["unavailable"][0]["reason"], "original_artifact_unavailable")
        self.assertEqual(value["unavailable"][0]["relative_path"], "layout.gds")

    def test_long_retained_artifact_is_exported_verified_and_restored(self):
        relative = "/".join(["deep-" + "x" * 45] * 4 + ["extracted-cell.ext"])
        target = self.artifacts / relative
        self.assertGreater(len(str(target)), 300)
        io_path(target.parent).mkdir(parents=True)
        raw = b"SOFTWARE QA long-path extraction\r\n"
        io_path(target).write_bytes(raw)
        value = json.loads((self.system / "physical_workflow.json").read_text())
        item = {"relative_path": relative, "bytes": len(raw), "sha256": sha(raw)}
        value["runs"][0]["checks"]["retained_files"] = [item]
        write_json(self.system / "physical_workflow.json", value)
        package = self.package()
        self.assertEqual(package["unavailable"], [])
        found = next(e for e in package["entries"] if e.get("relative_path") == relative)
        self.assertEqual(found["artifact_id"], relative)
        restored = restore_project(self.registry, package)
        manifest = inspect_project(self.registry, restored["project_id"])
        archived = next(e for e in manifest["entries"] if e.get("relative_path") == relative)
        self.assertEqual(artifact_bytes(self.registry, restored["project_id"], archived["file_id"])[0], raw)
        io_path(target).write_bytes(b"SOFTWARE QA corrupted long extraction")
        with self.assertRaises(DomainError):
            self.package()

    def test_long_retained_path_still_rejects_reparse_ancestors(self):
        from types import SimpleNamespace
        relative = "/".join(["long-" + "x" * 45] * 4 + ["cell.ext"])
        target = self.artifacts / relative
        io_path(target.parent).mkdir(parents=True)
        io_path(target).write_bytes(self.raw)
        blocked = io_path(target.parent)
        original = Path.lstat
        def redirected(path):
            result = original(path)
            return SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400) if path == blocked else result
        with patch.object(Path, "lstat", redirected):
            with self.assertRaises(DomainError):
                safe_file(self.artifacts, relative)

    def prepared_directory(self):
        import hashlib
        identity = json.dumps([self.pid, self.sid], ensure_ascii=True, separators=(",", ":")).encode()
        return self.registry.root / "runtime_profiles" / hashlib.sha256(identity).hexdigest()[:32]

    def add_prepared_profiles(self):
        directory = self.prepared_directory()
        directory.mkdir(parents=True)
        config = {"profile_version": "SOFTWARE QA inert runtime", "working_directory": str(self.root / "never-executed")}
        raw = json.dumps(config, indent=3).encode() + b"\r\n"
        (directory / "postlayout_runtime.json").write_bytes(raw)
        run = {"id": "postlayout-workflow-" + "2" * 32, "runtime_configuration": config}
        write_json(self.system / "postlayout_workflow.json", {"runs": [run]})
        bundle = {"schema": "SOFTWARE QA inert preparation", "project_id": self.pid, "system_id": self.sid,
                  "configuration": {"profile": {"profile_version": "SOFTWARE QA terminal setup"}}}
        bundle["record_hash"] = object_hash(bundle)
        bundle_raw = json.dumps(bundle, indent=4).encode() + b"\r\n"
        (directory / "lvs_repair_direct_runtime_v7.json").write_bytes(bundle_raw)
        write_json(self.system / "lvs_workflow.json", {"runs": [{"id": "lvs-workflow-" + "3" * 32,
                   "runtime_configuration": bundle["configuration"]}]})
        return {"postlayout_runtime.json": raw, "lvs_repair_direct_runtime_v7.json": bundle_raw}

    def test_prepared_profiles_are_bound_inert_bytes_and_reexport_without_host_lookup(self):
        expected = self.add_prepared_profiles()
        (self.prepared_directory() / "unrelated.json").write_text("SOFTWARE QA not exported")
        package = self.package()
        profiles = [e for e in package["entries"] if e["kind"] == "prepared_profile"]
        self.assertEqual({e["path"].split("/")[-1] for e in profiles}, set(expected))
        self.assertTrue(all(e["source_run_ids"] and e["executable"] is False for e in profiles))
        validate_package(package)
        result = restore_project(self.registry, package)
        inspected = inspect_project(self.registry, result["project_id"])
        self.assertFalse(inspected["host_execution_ready"])
        for entry in inspected["entries"]:
            if entry["kind"] == "prepared_profile":
                self.assertEqual(artifact_bytes(self.registry, result["project_id"], entry["file_id"])[0],
                                 expected[entry["path"].split("/")[-1]])
        active_identity = json.dumps([result["project_id"], result["system_id"]], ensure_ascii=True, separators=(",", ":")).encode()
        import hashlib
        active = self.registry.root / "runtime_profiles" / hashlib.sha256(active_identity).hexdigest()[:32]
        self.assertFalse(active.exists())
        with patch("hullcirq.portable_projects._export_prepared_profiles", side_effect=AssertionError("foreign profile lookup")):
            again = export_project(self.registry, result["project_id"], self.root)
        validate_package(again)
        self.assertEqual(len([e for e in again["entries"] if e["kind"] == "prepared_profile"]), 2)

    def test_unexecuted_prepared_profile_is_explicitly_unavailable(self):
        self.add_prepared_profiles()
        (self.system / "postlayout_workflow.json").unlink()
        package = self.package()
        self.assertEqual(package["unavailable"], [{"system_id": self.sid, "store": "postlayout_workflow.json",
                         "kind": "prepared_profile", "relative_path": "postlayout_runtime.json",
                         "reason": "prepared_profile_without_saved_execution"}])

    def test_prepared_profile_checksum_or_foreign_source_is_rejected(self):
        self.add_prepared_profiles()
        path = self.prepared_directory() / "lvs_repair_direct_runtime_v7.json"
        for mutation in ("checksum", "source"):
            bundle = json.loads(path.read_text())
            if mutation == "checksum": bundle["record_hash"] = "0" * 64
            else:
                bundle["system_id"] = "system-" + "f" * 32
                bundle["record_hash"] = object_hash({k: v for k, v in bundle.items() if k != "record_hash"})
            write_json(path, bundle)
            with self.assertRaises(DomainError):
                self.package()

    def test_archive_cannot_install_or_rename_prepared_profiles(self):
        self.add_prepared_profiles()
        original = self.package()
        for mutation in ("active", "filename", "kind"):
            value = copy.deepcopy(original)
            entry = next(e for e in value["entries"] if e["kind"] == "prepared_profile")
            if mutation == "active": entry["executable"] = True
            if mutation == "filename": entry["path"] = f"profiles/{self.sid}/arbitrary-command.json"
            if mutation == "kind": entry["kind"] = "eda_artifact"
            with self.assertRaises(DomainError):
                validate_package(self.seal(value))

    def test_unrelated_project_files_and_runtime_are_not_exported(self):
        (self.system / "password.txt").write_text("SOFTWARE QA not exported")
        (self.system / "runtime.json").write_text("SOFTWARE QA not exported")
        value = self.package()
        self.assertEqual({entry["path"].split("/")[-1] for entry in value["design_backup"]["files"]},
                         {"state.json", "physical_workflow.json"})

    def test_retained_file_manifest_is_included_and_duplicate_declarations_are_checked(self):
        raw = b"SOFTWARE QA worker receipt\r\n"
        (self.artifacts / "receipt.json").write_bytes(raw)
        value = json.loads((self.system / "physical_workflow.json").read_text())
        value["runs"][0]["checks"]["retained_files"] = [
            {"relative_path": "receipt.json", "bytes": len(raw), "sha256": sha(raw)},
            copy.deepcopy(value["runs"][0]["checks"]["artifacts"][0])]
        write_json(self.system / "physical_workflow.json", value)
        package = self.package()
        self.assertEqual(len(package["entries"]), 2)
        value["runs"][0]["checks"]["retained_files"][-1]["sha256"] = "0" * 64
        write_json(self.system / "physical_workflow.json", value)
        with self.assertRaises(DomainError): self.package()

    def test_tool_or_model_directories_cannot_become_artifact_read_roots(self):
        for folder in ("runtime", "models", "pdks", "tools"):
            location = self.root / ".work" / folder
            location.mkdir()
            (location / "layout.gds").write_bytes(self.raw)
            value = json.loads((self.system / "physical_workflow.json").read_text())
            value["runs"][0]["checks"]["artifacts_directory"] = str(location)
            write_json(self.system / "physical_workflow.json", value)
            with self.assertRaises(DomainError):
                self.package()

    def test_path_traversal_windows_devices_and_case_collisions_rejected(self):
        for path in ("../escape", "/absolute", "artifacts/../escape", "C:/escape", "artifacts/x/CON", "artifacts/x/name. "):
            value = self.package()
            value["entries"][0]["path"] = path
            with self.assertRaises(DomainError, msg=path):
                validate_package(self.seal(value))
        value = self.package()
        duplicate = copy.deepcopy(value["entries"][0])
        duplicate["path"] = duplicate["path"].upper()
        value["entries"].append(duplicate)
        with self.assertRaises(DomainError):
            validate_package(self.seal(value))

    def test_zero_byte_hash_size_trailing_gzip_and_bomb_guards(self):
        for change in ("hash", "size", "trailing", "bomb"):
            value = self.package()
            item = value["entries"][0]
            if change == "hash": item["sha256"] = "0" * 64
            if change == "size": item["size"] += 1
            if change == "trailing": item["data"] = base64.b64encode(base64.b64decode(item["data"]) + gzip.compress(b"extra")).decode()
            if change == "bomb": item["size"] = 1; item["data"] = base64.b64encode(gzip.compress(b"x" * 100000)).decode()
            with self.assertRaises(DomainError, msg=change):
                validate_package(self.seal(value))

    def test_object_tampering_is_rejected_on_each_read(self):
        result = restore_project(self.registry, self.package())
        value = inspect_project(self.registry, result["project_id"])
        entry = value["entries"][-1]
        root = self.registry._project_path(result["project_id"]) / "evidence"
        (root / entry["object"]).write_bytes(b"corrupt")
        with self.assertRaises(DomainError):
            artifact_bytes(self.registry, result["project_id"], entry["file_id"])

    def test_original_absolute_provenance_and_large_integer_bytes_unchanged(self):
        value = json.loads((self.system / "state.json").read_text())
        value["transfer_provenance"] = {"foreign": "/foreign/host/retained", "wide": 2 ** 134 + 5}
        raw = json.dumps(value, ensure_ascii=False, indent=3).encode() + b"\r\n"
        (self.system / "state.json").write_bytes(raw)
        package = self.package()
        restored = restore_project(self.registry, package)
        path = self.registry._system_path(restored["project_id"], restored["system_id"])
        self.assertEqual((path / "state.json").read_bytes(), raw)

    def test_map_path_must_be_in_package(self):
        value = self.package()
        value["maps"] = [{"html_path": "https://external.invalid/script"}]
        with self.assertRaises(DomainError):
            validate_package(self.seal(value))

    def test_oversize_and_file_count_limits_before_restore(self):
        value = self.package()
        with patch("hullcirq.portable_projects.MAX_FILES", 1):
            with self.assertRaises(DomainError): validate_package(value)
        with patch("hullcirq.portable_projects.MAX_TOTAL_BYTES", 2):
            with self.assertRaises(DomainError): validate_package(value)

    def test_readonly_restore_rolls_back_catalog_on_attachment_disk_failure(self):
        value = self.package()
        before = copy.deepcopy(self.registry._registry)
        original = Path.open
        def broken(path, *args, **kwargs):
            if "evidence" in path.parts and args and args[0] == "xb":
                raise OSError("SOFTWARE QA injected attachment disk failure")
            return original(path, *args, **kwargs)
        with patch.object(Path, "open", broken):
            with self.assertRaises(OSError): restore_project(self.registry, value)
        self.assertEqual(before, self.registry._registry)

    def test_parent_symlink_is_rejected_where_supported(self):
        target = self.root / "safe-data"
        target.mkdir()
        (target / "data").write_bytes(b"SOFTWARE QA")
        linked = self.root / "linked"
        try:
            linked.symlink_to(target, target_is_directory=True)
        except OSError:
            # Exercise Windows reparse-point rejection without requiring the
            # test runner to enable Developer Mode or alter host privileges.
            from types import SimpleNamespace
            original = Path.lstat
            def simulated(path):
                if path == io_path(target): return SimpleNamespace(st_file_attributes=0x400, st_mode=original(path).st_mode)
                return original(path)
            with patch.object(Path, "lstat", simulated):
                with self.assertRaises(DomainError): safe_file(target, "data")
        else:
            with self.assertRaises(DomainError): safe_file(linked, "data")

    def test_combined_declared_size_preflight_happens_before_any_decode(self):
        value = self.package()
        with patch("hullcirq.portable_projects.MAX_TOTAL_BYTES", 2), patch("hullcirq.portable_projects._decode", side_effect=AssertionError("must not decode")):
            with self.assertRaises(DomainError): validate_package(value)

    def test_restore_validation_does_not_retain_duplicate_store_bytes(self):
        value = self.package()
        nonstores = validate_package(value, retain_store_bytes=False)
        self.assertTrue(nonstores)
        self.assertTrue(all(not entry["path"].startswith("systems/") for entry, _ in nonstores))

    def test_malformed_unhashable_metadata_is_bounded_domain_error(self):
        for mutation in ("system_id", "map_path", "backup_files", "entry"):
            value = self.package()
            if mutation == "system_id":
                value["design_backup"]["project"]["systems"][0]["id"] = []
                value["project"] = copy.deepcopy(value["design_backup"]["project"])
                value["design_backup"]["checksum"] = digest({k: v for k, v in value["design_backup"].items() if k != "checksum"})
            if mutation == "map_path": value["maps"] = [{"html_path": []}]
            if mutation == "backup_files": value["design_backup"]["files"] = {}
            if mutation == "entry": value["entries"][0] = []
            self.seal(value)
            with self.assertRaises(DomainError, msg=mutation): validate_package(value)

    def test_attachment_failure_removes_only_new_component_versions(self):
        from hullcirq.store import ProjectStore
        from hullcirq.components import ComponentLibrary
        source = self.root / "component-source"
        ProjectStore(source)
        resolved = self.registry.register_legacy(source, "Software QA component source")
        component = self.registry.publish_component(resolved["project_id"], resolved["system_id"], name="Software QA pinned unit")
        package = self.registry.component_package(component["id"], component["version"])
        value = self.package()
        value["design_backup"]["components"] = [package]
        value["design_backup"]["checksum"] = digest({k: v for k, v in value["design_backup"].items() if k != "checksum"})
        self.seal(value)
        destination = WorkspaceRegistry(self.root / "destination-workspace")
        original = Path.open
        def broken(path, *args, **kwargs):
            if "evidence" in path.parts and args and args[0] == "xb": raise OSError("SOFTWARE QA disk failure")
            return original(path, *args, **kwargs)
        with patch.object(Path, "open", broken):
            with self.assertRaises(OSError): restore_project(destination, value)
        self.assertEqual(destination.catalog()["projects"], [])
        self.assertEqual(ComponentLibrary(destination.root / "components").catalog(), [])
        self.assertEqual(self.registry.component_package(component["id"], component["version"]), package)

    def test_component_history_sizes_are_preflighted_before_any_decode(self):
        value = self.package()
        value["design_backup"]["components"] = [{"source_history": [{"size": 1000000}]}]
        value["design_backup"]["checksum"] = digest({k: v for k, v in value["design_backup"].items() if k != "checksum"})
        self.seal(value)
        with patch("hullcirq.portable_projects.MAX_TOTAL_BYTES", 500000), patch("hullcirq.portable_projects._decode", side_effect=AssertionError("must not decode")):
            with self.assertRaises(DomainError): validate_package(value)

    def test_cli_verify_has_no_workspace_side_effect_and_restore_is_readonly(self):
        value = self.package()
        archive = self.root / "software-qa-evidence.json"
        archive.write_text(json.dumps(value), encoding="utf-8")
        workspace = self.root / "cli-workspace"
        def run(operation, *args):
            result = subprocess.run([sys.executable, "-B", "-X", "utf8", "scripts/portable_project.py", operation,
                                     "--workspace", str(workspace), *args], cwd=ROOT, capture_output=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(result.stdout)
        verified = run("verify", "--package", str(archive))
        self.assertEqual(verified["status"], "Passed")
        self.assertFalse(verified["executed"])
        self.assertFalse(workspace.exists())
        restored = run("restore", "--package", str(archive))
        self.assertTrue(restored["read_only"])
        self.assertFalse(restored["host_execution_ready"])
        self.assertFalse(restored["executed"])

    def test_cli_export_refuses_to_overwrite_existing_file(self):
        blank = self.registry.create_project("Software QA blank CLI")
        archive = self.root / "keep.json"
        archive.write_bytes(b"SOFTWARE QA KEEP EXACT")
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", "scripts/portable_project.py", "export",
                                 "--workspace", str(self.registry.root), "--project-id", blank["project_id"],
                                 "--package", str(archive)], cwd=ROOT, capture_output=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(archive.read_bytes(), b"SOFTWARE QA KEEP EXACT")


if __name__ == "__main__":
    unittest.main()

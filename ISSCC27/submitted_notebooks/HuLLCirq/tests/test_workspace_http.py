"""Focused project/session isolation checks; no model or EDA execution."""
import copy
import hashlib
import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hullcirq.store import ProjectStore
from hullcirq.workspace import WorkspaceRegistry
from hullcirq.workspace_server import _postlayout_profile_directory, make_workspace_server


class WorkspaceHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".work")
        self.registry = WorkspaceRegistry(Path(self.temp.name) / "workspace")
        self.server = make_workspace_server("127.0.0.1", 0, self.registry)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.01), daemon=True)
        self.thread.start()
        self.session = self.request("GET", "/api/workspace", authenticated=False)[1]["active"]["session_id"]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.temp.cleanup()

    def request(self, method, path, body=None, authenticated=True, session=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"X-HuLLCirq-Session": session or getattr(self, "session", "")} if authenticated else {}
        if body is not None:
            body = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def mutation(self, operation, body):
        status, result = self.request("POST", "/api/workspace/" + operation, body)
        self.assertEqual(status, 200, result)
        self.session = result["workspace"]["active"]["session_id"]
        return result

    def create(self, name="A"):
        return self.mutation("create-project", {"name": name, "system_name": "Main", "top_module": "main_top"})

    def test_new_project_has_no_circuit_evidence(self):
        result = self.create()
        self.assertEqual(result["project"]["design"]["nodes"], [])
        self.assertFalse(result["project"]["runs"])
        self.assertTrue(all(item["review_status"] != "Accepted" for item in result["project"]["workflow"]))

    def test_s14_profile_location_is_host_scoped_by_project_and_system(self):
        result = self.create()
        active = result["workspace"]["active"]
        manager = self.server.postlayout_workflow
        scope = hashlib.sha256(json.dumps([active["project_id"], active["system_id"]], separators=(",", ":")).encode("utf-8")).hexdigest()[:32]
        expected = (self.registry.root / "runtime_profiles" / scope).resolve()
        system_path = self.registry.resolve_system(active["project_id"], active["system_id"])["path"].resolve()
        self.assertEqual(manager._configuration_path, expected / "postlayout_runtime.json")
        self.assertEqual(manager._profile_working_directory, expected / "runs")
        self.assertFalse(manager._configuration_path.is_relative_to(system_path))
        self.assertFalse(manager._configuration_path.exists())
        self.assertEqual(len(expected.name), 32)
        legacy_profile = self.registry.root / "runtime_profiles" / active["project_id"] / active["system_id"] / "postlayout_runtime.json"
        legacy_profile.parent.mkdir(parents=True)
        legacy_profile.write_bytes(b"SOFTWARE QA preserved legacy host profile\n")
        self.mutation("create-system", {"project_id": active["project_id"], "name": "Other", "top_module": "other_top"})
        other_path = self.server.postlayout_workflow._configuration_path
        self.assertNotEqual(other_path, manager._configuration_path)
        self.assertEqual(other_path.parent.parent, expected.parent)
        self.mutation("open", {"project_id": active["project_id"], "system_id": active["system_id"]})
        self.assertEqual(self.server.postlayout_workflow._configuration_path, expected / "postlayout_runtime.json")
        self.assertIsNone(self.server.postlayout_workflow.tool_configuration)
        self.assertEqual(legacy_profile.read_bytes(), b"SOFTWARE QA preserved legacy host profile\n")

    def test_s14_longest_process_record_fits_typical_windows_checkout_path(self):
        project_id, system_id = "project-" + "1" * 32, "system-" + "2" * 32
        scope = _postlayout_profile_directory(self.registry.root, project_id, system_id).name
        typical_root = PureWindowsPath("C:/Users/developer/codes/HuLLCirq-private/ISSCC27/submitted_notebooks/HuLLCirq/.work/workspace/runtime_profiles")
        # Current tempfile suffix length and longest fixed nine-corner operation.
        tail = PureWindowsPath("runs/postroute-12345678/sta/sta-max_ff_n40C_1v95/process-result.json")
        compact = str(typical_root / scope / tail)
        legacy = str(typical_root / project_id / system_id / tail)
        self.assertGreaterEqual(len(legacy), 260)  # Reproduce the failed layout.
        self.assertLess(len(compact), 240)  # Retain margin below MAX_PATH.
        self.assertNotIn(project_id, compact)
        self.assertNotIn(system_id, compact)
        self.assertNotEqual(scope, _postlayout_profile_directory(self.registry.root, system_id, project_id).name)

    def test_invalid_host_repair_bundle_is_preserved_and_does_not_block_open(self):
        result = self.create()
        active = result["workspace"]["active"]
        directory = _postlayout_profile_directory(self.registry.root, active["project_id"], active["system_id"])
        directory.mkdir(parents=True)
        bundle = directory / "physical_repair_runtime.json"
        raw = b"SOFTWARE QA deliberately malformed host correction profile\n"
        bundle.write_bytes(raw)
        reopened = self.mutation("open", {"project_id": active["project_id"], "system_id": active["system_id"]})
        self.assertEqual(reopened["project"]["revision"], result["project"]["revision"])
        self.assertFalse(self.server.physical_repair_session["configured"])
        self.assertTrue(self.server.physical_repair_session["bundle_present"])
        self.assertIsNotNone(self.server.physical_repair_session["error"])
        self.assertIsNone(self.server.physical_workflow.tool_configuration)
        self.assertEqual(bundle.read_bytes(), raw)

    def test_stale_tab_cannot_read_or_mutate_other_project(self):
        self.create("A")
        old_session = self.session
        current = self.create("B")["project"]
        for method, path, body in (("GET", "/api/project", None),
                                  ("POST", "/api/save", {"design": current["design"], "expected_revision_id": current["revision"]["id"]}),
                                  ("POST", "/api/workspace/close", {})):
            status, result = self.request(method, path, body, session=old_session)
            self.assertEqual(status, 409)
            self.assertEqual(result["error"]["code"], "workspace_session_changed")
        self.assertEqual(self.request("GET", "/api/project")[1]["revision"], current["revision"])

    def test_two_systems_retain_independent_saved_designs(self):
        first = self.create()
        active = first["workspace"]["active"]
        second = self.mutation("create-system", {"project_id": active["project_id"], "name": "Other", "top_module": "other_top"})
        self.assertNotEqual(second["workspace"]["active"]["system_id"], active["system_id"])
        self.assertEqual(second["project"]["design"]["settings"]["top_module"], "other_top")
        reopened = self.mutation("open", {"project_id": active["project_id"], "system_id": active["system_id"]})
        self.assertEqual(reopened["project"]["revision"], first["project"]["revision"])

    def test_close_removes_active_system_but_keeps_saved_project(self):
        self.create()
        closed = self.mutation("close", {})
        self.assertIsNone(closed["project"])
        self.assertIsNone(closed["workspace"]["active"]["project_id"])
        status, result = self.request("GET", "/api/project")
        self.assertEqual(status, 409)
        self.assertEqual(result["error"]["code"], "no_system_open")
        self.assertEqual(len(closed["workspace"]["projects"]), 1)

    def test_active_worker_prevents_context_switch(self):
        current = self.create()
        manager = self.server.global_generation
        original = manager.is_active
        manager.is_active = lambda: True
        try:
            status, _ = self.request("POST", "/api/workspace/close", {})
            self.assertEqual(status, 409)
            self.assertEqual(self.server.workspace.identity["session_id"], self.session)
        finally:
            manager.is_active = original
        self.assertEqual(self.request("GET", "/api/project")[1]["revision"], current["project"]["revision"])

    def test_backup_restore_preserves_history_as_readonly(self):
        original = self.create()
        design = copy.deepcopy(original["project"]["design"])
        design["wide_input_value"] = 2 ** 134 + 3
        status, saved = self.request("POST", "/api/save", {"design": design, "expected_revision_id": original["project"]["revision"]["id"]})
        self.assertEqual(status, 200, saved)
        pid = original["workspace"]["active"]["project_id"]
        status, backup = self.request("GET", f"/api/workspace/backup/{pid}?session_id={self.session}", authenticated=False)
        self.assertEqual(status, 200, backup)
        restored = self.mutation("restore", {"bundle_text": json.dumps(backup), "name": "Restored"})
        self.assertTrue(restored["workspace"]["active"]["read_only"])
        self.assertEqual(restored["project"]["revision"], saved["revision"])
        self.assertEqual(restored["project"]["design"]["wide_input_value"], 2 ** 134 + 3)
        status, result = self.request("POST", "/api/save", {"design": restored["project"]["design"], "expected_revision_id": restored["project"]["revision"]["id"]})
        self.assertEqual(status, 409)
        self.assertEqual(result["error"]["code"], "read_only_system")

    def test_duplicate_starts_fresh_without_adoption(self):
        original = self.create()
        active = original["workspace"]["active"]
        duplicate = self.mutation("duplicate-system", {"project_id": active["project_id"], "system_id": active["system_id"], "name": "Copy"})
        self.assertNotEqual(duplicate["project"]["revision"]["id"], original["project"]["revision"]["id"])
        self.assertFalse(duplicate["project"]["runs"])
        self.assertFalse(duplicate["project"]["reviews"])

    def test_bad_open_keeps_existing_context(self):
        current = self.create()
        status, _ = self.request("POST", "/api/workspace/open", {"project_id": "project-" + "0" * 32, "system_id": "system-" + "0" * 32})
        self.assertEqual(status, 404)
        self.assertEqual(self.request("GET", "/api/project")[1]["revision"], current["project"]["revision"])

    def test_legacy_registration_leaves_original_bytes_unchanged(self):
        source = ProjectStore(Path(self.temp.name) / "legacy")
        before = source.state_path.read_bytes()
        result = self.registry.register_legacy(source.path)
        opened = self.mutation("open", {"project_id": result["project"]["id"], "system_id": result["system"]["id"]})
        self.assertTrue(opened["workspace"]["active"]["read_only"])
        self.assertEqual(source.state_path.read_bytes(), before)

    def test_readonly_initialization_does_not_write_preserved_snapshot(self):
        source = ProjectStore(Path(self.temp.name) / "legacy")
        result = self.registry.register_legacy(source.path)
        preserved = self.registry.resolve_system(result["project_id"], result["system_id"])["path"]
        before = {p.name: p.read_bytes() for p in preserved.glob("*.json")}
        self.mutation("open", {"project_id": result["project_id"], "system_id": result["system_id"]})
        after = {p.name: p.read_bytes() for p in preserved.glob("*.json")}
        self.assertEqual(before, after)
        self.assertTrue(hasattr(self.server.workspace.context, "saved_envelope"))
        status, stage = self.request("GET", "/api/workspace/stage/layout")
        self.assertEqual(status, 200, stage)
        self.assertTrue(stage["readonly_snapshot"]["compact"])
        self.assertEqual(stage["readonly_snapshot"]["loaded_stage"], "layout")
        self.assertEqual(stage["workspace_identity"]["session_id"], self.session)
        self.assertEqual(self.request("GET", "/api/workspace/stage/layout", session="old-session")[0], 409)
        self.assertEqual(self.request("GET", "/api/workspace/stage/invalid-stage")[0], 404)
        self.assertEqual(self.request("POST", "/api/verify", {"stage_id": "global_settings"})[0], 409)
        self.assertEqual(before, {p.name: p.read_bytes() for p in preserved.glob("*.json")})

    def test_recent_write_failure_does_not_activate_candidate(self):
        original = self.create()
        other = self.registry.create_project("Other")
        before = self.server.workspace.context
        mark_recent = self.registry.mark_recent
        self.registry.mark_recent = lambda *args: (_ for _ in ()).throw(OSError("simulated catalog write failure"))
        try:
            status, _ = self.request("POST", "/api/workspace/open", {"project_id": other["project_id"], "system_id": other["system_id"]})
            self.assertEqual(status, 500)
            self.assertIs(self.server.workspace.context, before)
            self.assertEqual(self.server.workspace.identity["session_id"], self.session)
        finally:
            self.registry.mark_recent = mark_recent
        self.assertEqual(self.request("GET", "/api/project")[1]["revision"], original["project"]["revision"])

    def test_readonly_historical_cleanup_does_not_prevent_leaving(self):
        source = ProjectStore(Path(self.temp.name) / "legacy")
        result = self.registry.register_legacy(source.path)
        self.mutation("open", {"project_id": result["project_id"], "system_id": result["system_id"]})
        original = self.server.physical_workflow.is_active
        self.server.physical_workflow.is_active = lambda: True
        try:
            closed = self.mutation("close", {})
            self.assertIsNone(closed["project"])
        finally:
            # The disposed context has no live workers or authoritative writes.
            self.assertEqual(source.state_path.read_bytes(), ProjectStore(source.path).state_path.read_bytes())

    def test_save_cannot_change_workspace_identity(self):
        original = self.create()["project"]
        design = copy.deepcopy(original["design"])
        design["system"]["id"] = "system-" + "0" * 32
        status, result = self.request("POST", "/api/save", {"design": design, "expected_revision_id": original["revision"]["id"]})
        self.assertEqual(status, 409)
        self.assertEqual(result["error"]["code"], "workspace_identity_mismatch")

    def test_design_json_import_keeps_target_identity_without_adoption(self):
        original = self.create()["project"]
        design = json.loads((ROOT / "examples" / "m1_two_nodes.json").read_text(encoding="utf-8"))
        status, result = self.request("POST", "/api/import", {"design": design, "expected_revision_id": original["revision"]["id"]})
        self.assertEqual(status, 200, result)
        self.assertEqual(result["design"]["system"], original["design"]["system"])
        self.assertEqual(result["design"]["project"]["id"], original["design"]["project"]["id"])
        self.assertFalse(result["runs"])
        self.assertFalse(result["reviews"])

    def test_create_in_chosen_directory_then_open_that_folder(self):
        directory = Path(self.temp.name) / "chosen project"
        created = self.mutation("create-project", {"name": "Chosen folder", "project_directory": str(directory)})
        self.assertTrue((directory / "hullcirq.project.json").is_file())
        self.assertEqual(created["workspace"]["projects"][0]["directory"], str(directory.resolve()))
        revision = created["project"]["revision"]
        self.mutation("close", {})
        opened = self.mutation("open-directory", {"directory": str(directory)})
        self.assertEqual(opened["project"]["revision"], revision)

    def test_folder_picker_routes_use_nonblocking_software_runner(self):
        from hullcirq.folder_picker import FolderPickerManager
        self.server.workspace.folder_picker.close()
        self.server.workspace.folder_picker = FolderPickerManager(ROOT, runner=lambda *args: {"status": "Completed", "directory": self.temp.name})
        status, started = self.request("POST", "/api/workspace/folder-picker", {})
        self.assertEqual(status, 200)
        identifier = started["picker"]["id"]
        status, result = self.request("GET", "/api/workspace/folder-picker/" + identifier)
        self.assertEqual(status, 200)
        self.assertIn(result["picker"]["status"], ("Pending", "Completed"))


if __name__ == "__main__":
    unittest.main()

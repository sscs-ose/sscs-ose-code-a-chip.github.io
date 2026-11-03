"""Trash API/session/worker guards on a disposable local workspace only."""
import unittest
from unittest.mock import patch
import test_workspace_http as workspace_http


class ProjectTrashHttpTests(unittest.TestCase):
    setUp = workspace_http.WorkspaceHttpTests.setUp
    tearDown = workspace_http.WorkspaceHttpTests.tearDown
    request = workspace_http.WorkspaceHttpTests.request
    mutation = workspace_http.WorkspaceHttpTests.mutation
    create = workspace_http.WorkspaceHttpTests.create

    def project(self, result, pid=None):
        pid = pid or result["workspace"]["active"]["project_id"]
        return next(p for p in result["workspace"]["projects"] if p["id"] == pid)

    def test_active_deletion_closes_context_and_restore_reuses_ids_without_auto_open(self):
        created = self.create("Disposable QA")
        project = self.project(created)
        pid, sid = created["workspace"]["active"]["project_id"], created["workspace"]["active"]["system_id"]
        source = self.registry.resolve_system(pid, sid)["path"]
        before = {p.name: p.read_bytes() for p in source.glob("*.json")}
        old_session = self.session
        deleted = self.mutation("delete-project", {"project_id": pid, "expected_project_revision": project["management_revision"]})
        self.assertIsNone(deleted["project"])
        self.assertIsNone(deleted["workspace"]["active"]["project_id"])
        self.assertNotEqual(self.session, old_session)
        self.assertEqual(deleted["workspace"]["projects"], [])
        self.assertEqual({p.name: p.read_bytes() for p in source.glob("*.json")}, before)
        self.assertEqual(self.request("POST", "/api/workspace/delete-project", {"project_id": pid, "expected_project_revision": project["management_revision"]}, session=old_session)[0], 409)
        entry = deleted["workspace"]["trash"][0]
        restored = self.mutation("restore-project", {"trash_id": entry["id"], "expected_project_revision": entry["project"]["management_revision"]})
        self.assertIsNone(restored["workspace"]["active"]["project_id"])
        self.assertEqual(restored["workspace"]["projects"][0]["id"], pid)
        self.assertEqual(restored["workspace"]["projects"][0]["systems"][0]["id"], sid)
        self.assertEqual({p.name: p.read_bytes() for p in source.glob("*.json")}, before)
        opened = self.mutation("open", {"project_id": pid, "system_id": sid})
        self.assertEqual(opened["project"]["revision"], created["project"]["revision"])

    def test_busy_and_stale_delete_leave_context_and_catalog_unchanged(self):
        created = self.create()
        project, session = self.project(created), self.session
        body = {"project_id": project["id"], "expected_project_revision": project["management_revision"]}
        with patch.object(self.server.workflow, "is_active", return_value=True):
            status, result = self.request("POST", "/api/workspace/delete-project", body)
        self.assertEqual(status, 409, result)
        self.assertEqual(self.server.workspace.identity["session_id"], session)
        self.assertEqual(len(self.registry.catalog()["projects"]), 1)
        status, result = self.request("POST", "/api/workspace/delete-project", body | {"expected_project_revision": "stale"})
        self.assertEqual(status, 409, result)
        self.assertEqual(result["error"]["code"], "project_management_changed")
        self.assertEqual(self.server.workspace.identity["session_id"], session)
        self.assertIsNotNone(self.server.workspace.context)

    def test_delete_inactive_project_does_not_switch_other_project(self):
        first = self.create("First")
        project = self.project(first)
        second = self.create("Keep active")
        session = self.session
        deleted = self.mutation("delete-project", {"project_id": project["id"], "expected_project_revision": project["management_revision"]})
        self.assertEqual(self.session, session)
        self.assertEqual(deleted["workspace"]["active"], second["workspace"]["active"])
        self.assertEqual(deleted["project"]["revision"], second["project"]["revision"])

    def test_open_directory_of_deleted_project_returns_explicit_restore_action(self):
        created = self.create()
        project = self.project(created)
        self.mutation("delete-project", {"project_id": project["id"], "expected_project_revision": project["management_revision"]})
        status, result = self.request("POST", "/api/workspace/open-directory", {"directory": project["directory"]})
        self.assertEqual(status, 409, result)
        self.assertEqual(result["error"]["code"], "project_in_trash")
        self.assertIn("Restore", result["error"]["message"])
        self.assertEqual(self.registry.catalog()["projects"], [])


if __name__ == "__main__":
    unittest.main()

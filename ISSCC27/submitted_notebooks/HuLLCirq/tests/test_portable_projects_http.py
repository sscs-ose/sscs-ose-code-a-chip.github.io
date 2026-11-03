"""Isolated authenticated portable-evidence routes; never starts real tools."""
import copy
import hashlib
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from hullcirq.workspace import WorkspaceRegistry, digest
from hullcirq.workspace_server import make_workspace_server
from hullcirq.portable_projects import _pack

ROOT = Path(__file__).resolve().parents[1]


class PortableHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".work")
        self.registry = WorkspaceRegistry(Path(self.temp.name) / "workspace")
        self.server = make_workspace_server("127.0.0.1", 0, self.registry)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.01), daemon=True)
        self.thread.start()
        self.session = json.loads(self.request("GET", "/api/workspace", auth=False)[2])["active"]["session_id"]
        status, _, raw = self.request("POST", "/api/workspace/create-project", {"name": "Software QA transfer"})
        self.assertEqual(status, 200, raw)
        self.current = json.loads(raw)
        self.session = self.current["workspace"]["active"]["session_id"]
        self.pid = self.current["workspace"]["active"]["project_id"]

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(2); self.temp.cleanup()

    def request(self, method, path, body=None, auth=True, session=None, origin=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        headers = {"X-HuLLCirq-Session": session or self.session} if auth else {}
        if origin: headers["Origin"] = origin
        if body is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(body).encode("utf-8")
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def package(self):
        status, _, raw = self.request("GET", f"/api/workspace/evidence-export/{self.pid}")
        self.assertEqual(status, 200, raw)
        value = json.loads(raw)
        sid = value["project"]["systems"][0]["id"]
        html = b'<!doctype html><meta http-equiv="refresh" content="0;url=https://untrusted.invalid"><script id="layout-data" type="application/json">{"cells":[],"bad":"\\u003c/script>"}</script><script>location="https://untrusted.invalid";</script>'
        path = f"maps/{sid}/software-qa/static/view/layout_roles.html"
        value["entries"].append(_pack(path, html, kind="functional_map", system_id=sid, run_id="software-qa", map_id="static"))
        value["maps"] = [{"system_id": sid, "layout_run_id": "software-qa", "map_id": "static", "html_path": path}]
        value["checksum"] = digest({k: v for k, v in value.items() if k != "checksum"})
        return value, html

    def restore(self, value):
        status, _, raw = self.request("POST", "/api/workspace/restore-evidence", {"bundle_text": json.dumps(value), "name": "Software QA restored"})
        self.assertEqual(status, 200, raw)
        result = json.loads(raw)
        self.session = result["workspace"]["active"]["session_id"]
        return result

    def test_export_is_explicit_authenticated_and_does_not_modify_saved_stores(self):
        directory = self.registry._system_path(self.pid, self.current["workspace"]["active"]["system_id"])
        before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in directory.glob("*.json")}
        status, _, _ = self.request("GET", f"/api/workspace/evidence-export/{self.pid}", session="old-session")
        self.assertEqual(status, 409)
        self.package()
        after = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in directory.glob("*.json")}
        self.assertEqual(before, after)

    def test_restore_inspect_and_sandboxed_map_relocated_without_execution(self):
        value, html = self.package()
        with patch("hullcirq.workspace_server.WorkspaceRuntime.require_idle", wraps=self.server.workspace.require_idle) as idle:
            result = self.restore(value)
            self.assertTrue(idle.called)
        active = result["workspace"]["active"]
        self.assertTrue(active["read_only"])
        self.assertNotEqual(active["project_id"], self.pid)
        status, _, raw = self.request("GET", f"/api/workspace/evidence/{active['project_id']}")
        self.assertEqual(status, 200, raw)
        manifest = json.loads(raw)
        self.assertFalse(manifest["host_execution_ready"])
        entry = next(item for item in manifest["entries"] if item.get("kind") == "functional_map")
        status, headers, raw = self.request("GET", f"/api/workspace/evidence-map/{active['project_id']}/{entry['file_id']}?session_id={self.session}", auth=False)
        self.assertEqual(status, 200, raw)
        self.assertNotEqual(raw, html)
        self.assertNotIn(b"untrusted.invalid", raw)
        self.assertNotIn(b"http-equiv=", raw)
        self.assertIn(b"\\u003c/script>", raw)
        self.assertIn("sandbox allow-scripts", headers["Content-Security-Policy"])
        self.assertIn("connect-src 'none'", headers["Content-Security-Policy"])
        self.assertNotIn("allow-same-origin", headers["Content-Security-Policy"])
        status, download_headers, original = self.request("GET", f"/api/workspace/evidence-file/{active['project_id']}/{entry['file_id']}")
        self.assertEqual(original, html)
        self.assertEqual(download_headers["Content-Type"], "application/octet-stream")
        status, _, _ = self.request("POST", "/api/save", {"design": result["project"]["design"], "expected_revision_id": result["project"]["revision"]["id"]})
        self.assertEqual(status, 409)

    def test_stale_or_foreign_restore_requests_are_rejected_before_catalog_write(self):
        value, _ = self.package()
        count = len(self.registry.catalog()["projects"])
        for options in ({"session": "old-session"}, {"origin": "https://foreign.invalid"}):
            status, _, _ = self.request("POST", "/api/workspace/restore-evidence", {"bundle_text": json.dumps(value)}, **options)
            self.assertIn(status, (403, 409))
        self.assertEqual(len(self.registry.catalog()["projects"]), count)

    def test_checksum_failure_has_no_new_project(self):
        value, _ = self.package()
        value["entries"][0]["data"] = "AAAA"
        count = len(self.registry.catalog()["projects"])
        status, _, _ = self.request("POST", "/api/workspace/restore-evidence", {"bundle_text": json.dumps(value)})
        self.assertEqual(status, 409)
        self.assertEqual(len(self.registry.catalog()["projects"]), count)

    def test_active_worker_blocks_export_and_restore(self):
        value, _ = self.package()
        with patch.object(self.server.global_generation, "is_active", return_value=True):
            for method, path, body in (
                ("GET", f"/api/workspace/evidence-export/{self.pid}", None),
                ("POST", "/api/workspace/restore-evidence", {"bundle_text": json.dumps(value)})):
                self.assertEqual(self.request(method, path, body)[0], 409)

    def test_non_map_download_always_attachment_octet_stream(self):
        value, _ = self.package()
        result = self.restore(value)
        pid = result["workspace"]["active"]["project_id"]
        status, _, raw = self.request("GET", f"/api/workspace/evidence/{pid}")
        entry = next(item for item in json.loads(raw)["entries"] if item["kind"] == "system_store")
        status, headers, raw = self.request("GET", f"/api/workspace/evidence-file/{pid}/{entry['file_id']}")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/octet-stream")
        self.assertTrue(headers["Content-Disposition"].startswith("attachment"))
        self.assertIn("sandbox", headers["Content-Security-Policy"])


if __name__ == "__main__": unittest.main()

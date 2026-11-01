"""Exercise the real HTTP boundary and durable saved-input review path."""

import copy
import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hullcirq.server import make_server  # noqa: E402
from hullcirq.store import ProjectStore  # noqa: E402


class HttpWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.temporary.name) / "project")
        self.server = make_server("127.0.0.1", 0, self.store)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True
        )
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def request(self, method, path, body=None, headers=None):
        request_headers = dict(headers or {})
        if body is not None:
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            content = response.read()
            result_headers = dict(response.getheaders())
            parsed = (
                json.loads(content)
                if "application/json" in result_headers.get("Content-Type", "")
                else content
            )
            return response.status, parsed, result_headers
        finally:
            connection.close()

    def project(self):
        status, project, _ = self.request("GET", "/api/project")
        self.assertEqual(status, 200)
        return project

    def test_saved_input_validation_review_and_snapshot_are_linked(self):
        project = self.project()
        status, checked, _ = self.request(
            "POST", "/api/validate",
            {"stage_id": "global_settings", "revision_id": project["revision"]["id"]},
        )
        self.assertEqual(status, 200)
        run = checked["runs"][-1]
        self.assertEqual(run["validation_status"], "Passed")
        self.assertEqual(run["review_status"], "Awaiting Review")
        self.assertEqual(checked["reviews"], [])
        status, snapshot, _ = self.request(
            "GET", "/api/snapshots/" + run["source_snapshot_id"]
        )
        self.assertEqual(status, 200)
        self.assertEqual(snapshot, project["design"])
        status, reviewed, _ = self.request(
            "POST", "/api/review",
            {"run_id": run["id"], "decision": "accepted", "note": "Checked settings."},
        )
        self.assertEqual(status, 200)
        self.assertEqual(reviewed["workflow"][0]["review_status"], "Accepted")
        self.assertEqual(reviewed["reviews"][-1]["run_id"], run["id"])
        self.assertEqual(reviewed["workflow"][1]["execution_status"], "Not Run")

    def test_concurrent_save_and_late_validation_do_not_overwrite(self):
        initial = self.project()
        design = copy.deepcopy(initial["design"])
        design["project"]["name"] = "Saved in another window"
        status, saved, _ = self.request(
            "POST", "/api/save",
            {"design": design, "expected_revision_id": initial["revision"]["id"]},
        )
        self.assertEqual(status, 200)
        status, error, _ = self.request(
            "POST", "/api/save",
            {"design": initial["design"], "expected_revision_id": initial["revision"]["id"]},
        )
        self.assertEqual(status, 409)
        self.assertEqual(error["error"]["code"], "revision_conflict")
        status, _, _ = self.request(
            "POST", "/api/validate",
            {"stage_id": "graph_editor", "revision_id": initial["revision"]["id"]},
        )
        self.assertEqual(status, 409)
        self.assertEqual(self.project()["revision"], saved["revision"])

    def test_export_import_roundtrip_preserves_design_ids(self):
        initial = self.project()
        status, design, headers = self.request("GET", "/api/export")
        self.assertEqual(status, 200)
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertEqual(design, initial["design"])
        design["nodes"][0]["name"] = "Renamed producer"
        status, imported, _ = self.request(
            "POST", "/api/import",
            {"design": design, "expected_revision_id": initial["revision"]["id"]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(imported["design"]["edges"], initial["design"]["edges"])
        self.assertEqual(imported["design"]["nodes"][0]["id"], initial["design"]["nodes"][0]["id"])

    def test_bad_import_preserves_existing_saved_work(self):
        initial = self.project()
        bad = copy.deepcopy(initial["design"])
        bad["schema_version"] = "999"
        status, error, _ = self.request(
            "POST", "/api/import",
            {"design": bad, "expected_revision_id": initial["revision"]["id"]},
        )
        self.assertEqual(status, 400)
        self.assertEqual(error["error"]["code"], "unsupported_schema")
        self.assertEqual(self.project(), initial)

    def test_unimplemented_stage_does_not_create_success_run(self):
        initial = self.project()
        status, error, _ = self.request(
            "POST", "/api/validate",
            {"stage_id": "local_rtl_generation", "revision_id": initial["revision"]["id"]},
        )
        self.assertEqual(status, 422)
        self.assertEqual(error["error"]["code"], "unsupported_stage")
        self.assertEqual(self.project()["runs"], [])

    def test_malformed_json_duplicate_keys_and_nonfinite_numbers(self):
        initial = self.project()
        for body in (b'{"design":', b'{"x":1,"x":2}', b'{"x":NaN}', b'\xff'):
            with self.subTest(body=body):
                status, error, _ = self.request("POST", "/api/import", body)
                self.assertEqual(status, 400)
                self.assertEqual(error["error"]["code"], "invalid_json")
        self.assertEqual(self.project(), initial)

    def test_foreign_origin_and_host_cannot_mutate_project(self):
        initial = self.project()
        body = {"design": initial["design"], "expected_revision_id": initial["revision"]["id"]}
        for headers in (
            {"Origin": "https://example.invalid"},
            {"Host": "example.invalid:" + str(self.port)},
            {"Sec-Fetch-Site": "cross-site"},
        ):
            with self.subTest(headers=headers):
                status, _, _ = self.request("POST", "/api/save", body, headers)
                self.assertEqual(status, 403)
        self.assertEqual(self.project(), initial)

    def test_private_state_is_not_served_as_static_content(self):
        for path in (
            "/.work/projects/default/state.json",
            "/src/hullcirq/store.py",
            "/assets/branding/../../.work/projects/default/state.json",
            "/assets/branding/%2e%2e/%2e%2e/docs/project_context.md",
            "/%2e%2e/%2e%2e/.git/config",
        ):
            with self.subTest(path=path):
                status, _, _ = self.request("GET", path)
                self.assertEqual(status, 404)
        status, data, headers = self.request("GET", "/assets/branding/icon_hullcirq.png")
        # Standalone AI artwork is withheld from the curated distribution.
        self.assertEqual(status, 404)
        status, data, _ = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"HuLLCirq", data)
        self.assertNotIn(b"/assets/branding/", data)


if __name__ == "__main__":
    unittest.main()

"""Local service controls under workspace/session guards; no actual process.

These checks exercise only HTTP admission, controller ownership and preservation
of saved project data. They do not start a model, infer RTL or run EDA.
"""
import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hullcirq.store import ProjectStore
from hullcirq.workspace import WorkspaceRegistry
from hullcirq.workspace_server import make_workspace_server


class FakeLocalRuntime:
    """An in-memory service controller, without subprocesses or network clients."""

    def __init__(self):
        self.state = "Stopped"
        self.calls = []
        self.close_calls = 0
        self.start_profiles = []

    def status(self):
        self.calls.append("status")
        return {"state": self.state, "owned": self.state == "Running"}

    def start(self, profile=None):
        self.calls.append("start")
        self.start_profiles.append(dict(profile) if profile is not None else None)
        self.state = "Running"
        return self.status()

    def stop(self):
        self.calls.append("stop")
        self.state = "Stopped"
        return self.status()

    def close(self):
        self.close_calls += 1


class LocalRuntimeHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".work")
        self.registry = WorkspaceRegistry(Path(self.temp.name) / "workspace")
        self.controller = FakeLocalRuntime()
        self.server = make_workspace_server("127.0.0.1", 0, self.registry,
                                            local_runtime=self.controller)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=.01), daemon=True)
        self.thread.start()
        self.session = self.request("GET", "/api/workspace", authenticated=False)[1]["active"]["session_id"]
        self.closed = False

    def tearDown(self):
        if not self.closed:
            self.close_server()
        self.temp.cleanup()

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.closed = True

    def request(self, method, path, body=None, *, authenticated=True, session=None,
                extra_headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"X-HuLLCirq-Session": session or self.session} if authenticated else {}
        headers.update(extra_headers or {})
        if body is not None:
            body = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def mutation(self, path, body):
        status, result = self.request("POST", "/api/workspace/" + path, body)
        self.assertEqual(status, 200, result)
        if "workspace" in result:
            self.session = result["workspace"]["active"]["session_id"]
        return result

    def create(self, name="Local service software check"):
        return self.mutation("create-project", {"name": name, "system_name": "Main", "top_module": "main_top"})

    def save_profile(self, changes=None):
        profile = json.loads((ROOT / "configs" / "llm_profile_npu.json").read_text(encoding="utf-8"))
        profile.update(changes or {})
        current = self.server.generation.envelope()["llm"]["profile_revision_id"]
        self.server.generation.save_profile(profile, current)

    def saved_bytes(self):
        return {p.name: p.read_bytes() for p in self.server.store.path.glob("*.json")}

    def runtime_calls(self):
        return [call for call in self.controller.calls if call != "status"]

    def test_status_start_stop_preserve_design_and_evidence(self):
        self.create()
        self.save_profile()
        before = self.saved_bytes()
        for method, path, body, expected in (
                ("GET", "/api/workspace/local-runtime", None, "Stopped"),
                ("POST", "/api/workspace/local-runtime/start", {}, "Running"),
                ("GET", "/api/workspace/local-runtime", None, "Running"),
                ("POST", "/api/workspace/local-runtime/stop", {}, "Stopped")):
            with self.subTest(path=path, expected=expected):
                status, result = self.request(method, path, body)
                self.assertEqual(status, 200, result)
                self.assertEqual(result["runtime"]["state"], expected)
        self.assertEqual(self.runtime_calls(), ["start", "stop"])
        self.assertEqual(self.saved_bytes(), before)

    def test_runtime_requires_active_project(self):
        for method, path, body in (
                ("GET", "/api/workspace/local-runtime", None),
                ("POST", "/api/workspace/local-runtime/start", {}),
                ("POST", "/api/workspace/local-runtime/stop", {})):
            with self.subTest(path=path):
                status, result = self.request(method, path, body)
                self.assertEqual(status, 409, result)
                self.assertEqual(result["error"]["code"], "no_system_open")
        self.assertEqual(self.controller.calls, [])

    def test_missing_or_stale_session_cannot_observe_or_control_service(self):
        self.create()
        self.save_profile()
        for session in (None, "stale-session"):
            for method, path, body in (
                    ("GET", "/api/workspace/local-runtime", None),
                    ("POST", "/api/workspace/local-runtime/start", {}),
                    ("POST", "/api/workspace/local-runtime/stop", {})):
                with self.subTest(path=path, session=session):
                    status, result = self.request(method, path, body,
                                                  authenticated=session is not None, session=session)
                    self.assertEqual(status, 409, result)
                    self.assertEqual(result["error"]["code"], "workspace_session_changed")
        self.assertEqual(self.controller.calls, [])

    def test_cross_origin_and_cross_site_mutations_cannot_control_service(self):
        self.create()
        self.save_profile()
        before = self.saved_bytes()
        for headers in ({"Origin": "https://other.example"}, {"Sec-Fetch-Site": "cross-site"}):
            for action in ("start", "stop"):
                with self.subTest(headers=headers, action=action):
                    status, result = self.request("POST", "/api/workspace/local-runtime/" + action,
                                                  {}, extra_headers=headers)
                    self.assertEqual(status, 403, result)
                    self.assertEqual(result["error"]["code"], "invalid_origin")
        self.assertEqual(self.runtime_calls(), [])
        self.assertEqual(self.saved_bytes(), before)

    def test_runtime_control_requires_a_saved_profile(self):
        self.create()
        before = self.saved_bytes()
        for action in ("start", "stop"):
            with self.subTest(action=action):
                status, result = self.request("POST", "/api/workspace/local-runtime/" + action, {})
                self.assertEqual(status, 409, result)
                self.assertEqual(result["error"]["code"], "profile_required")
        self.assertEqual(self.runtime_calls(), [])
        self.assertEqual(self.saved_bytes(), before)

    def test_incompatible_profiles_cannot_start_or_stop_prepared_runtime(self):
        self.create()
        cases = (
            {"execution_location": "Network", "base_url": "https://network.example/v1"},
            {"base_url": "http://127.0.0.1:11434/v1"},
            {"base_url": "http://127.0.0.1:11435/other"},
            {"base_url": "http://127.0.0.2:11435/v1"},
            {"base_url": "https://127.0.0.1:11435/v1"},
            {"model": "another-local-model"},
        )
        for changes in cases:
            self.save_profile(changes)
            before = self.saved_bytes()
            for action in ("start", "stop"):
                with self.subTest(changes=changes, action=action):
                    status, result = self.request("POST", "/api/workspace/local-runtime/" + action, {})
                    self.assertEqual(status, 409, result)
                    self.assertEqual(result["error"]["code"], "local_runtime_profile_unsupported")
            self.assertEqual(self.saved_bytes(), before)
        self.assertEqual(self.runtime_calls(), [])

    def test_localhost_and_trailing_slash_use_same_prepared_runtime(self):
        self.create()
        self.save_profile({"base_url": "http://localhost:11435/v1/"})
        for action in ("start", "stop"):
            status, result = self.request("POST", "/api/workspace/local-runtime/" + action, {})
            self.assertEqual(status, 200, result)
        self.assertEqual(self.runtime_calls(), ["start", "stop"])

    def test_coder_start_receives_exact_saved_model_and_context_without_store_changes(self):
        self.create()
        self.save_profile({"model": "qwen2.5-coder:7b", "context_window": 32768})
        before = self.saved_bytes()
        status, result = self.request("POST", "/api/workspace/local-runtime/start", {})
        self.assertEqual(status, 200, result)
        self.assertEqual(self.controller.start_profiles[-1]["model"], "qwen2.5-coder:7b")
        self.assertEqual(self.controller.start_profiles[-1]["context_window"], 32768)
        self.assertEqual(self.runtime_calls(), ["start"])
        self.assertEqual(self.saved_bytes(), before)
        status, _ = self.request("POST", "/api/workspace/local-runtime/stop", {})
        self.assertEqual(status, 200)
        self.assertEqual(self.runtime_calls(), ["start", "stop"])

    def test_runtime_controls_do_not_accept_browser_command_overrides(self):
        self.create()
        self.save_profile()
        before = self.saved_bytes()
        for action in ("start", "stop"):
            status, result = self.request("POST", "/api/workspace/local-runtime/" + action,
                                          {"ollama_path": "browser supplied executable"})
            self.assertEqual(status, 400, result)
            self.assertEqual(result["error"]["code"], "local_runtime_request_invalid")
        self.assertEqual(self.runtime_calls(), [])
        self.assertEqual(self.saved_bytes(), before)

    def test_readonly_snapshot_can_inspect_status_but_cannot_control_service(self):
        source = ProjectStore(Path(self.temp.name) / "readonly source")
        registered = self.registry.register_legacy(source.path)
        self.mutation("open", {"project_id": registered["project_id"], "system_id": registered["system_id"]})
        before = self.saved_bytes()
        status, result = self.request("GET", "/api/workspace/local-runtime")
        self.assertEqual(status, 200, result)
        self.assertEqual(result["runtime"]["state"], "Stopped")
        for action in ("start", "stop"):
            with self.subTest(action=action):
                status, result = self.request("POST", "/api/workspace/local-runtime/" + action, {})
                self.assertEqual(status, 409, result)
                self.assertEqual(result["error"]["code"], "read_only_system")
        self.assertEqual(self.runtime_calls(), [])
        self.assertEqual(self.saved_bytes(), before)

    def test_active_generation_blocks_runtime_stop(self):
        self.create()
        self.save_profile()
        self.request("POST", "/api/workspace/local-runtime/start", {})
        before = self.saved_bytes()
        manager = self.server.global_generation
        is_active = manager.is_active
        manager.is_active = lambda: True
        try:
            status, result = self.request("POST", "/api/workspace/local-runtime/stop", {})
            self.assertEqual(status, 409, result)
            self.assertEqual(self.runtime_calls(), ["start"])
            self.assertEqual(self.saved_bytes(), before)
        finally:
            manager.is_active = is_active

    def test_active_node_worker_blocks_runtime_start_and_stop(self):
        self.create()
        self.save_profile()
        before = self.saved_bytes()

        class ActiveSoftwareWorker:
            def is_alive(self):
                return True

        manager = self.server.generation
        worker = manager._worker
        manager._worker = ActiveSoftwareWorker()
        try:
            for action in ("start", "stop"):
                with self.subTest(action=action):
                    status, result = self.request("POST", "/api/workspace/local-runtime/" + action, {})
                    self.assertEqual(status, 409, result)
            self.assertEqual(self.runtime_calls(), [])
            self.assertEqual(self.saved_bytes(), before)
        finally:
            manager._worker = worker

    def test_project_switch_keeps_service_owned_by_server_until_shutdown(self):
        self.create("First software check")
        self.save_profile()
        self.request("POST", "/api/workspace/local-runtime/start", {})
        self.create("Second software check")
        self.assertEqual(self.controller.close_calls, 0)
        self.assertEqual(self.runtime_calls(), ["start"])
        status, result = self.request("GET", "/api/workspace/local-runtime")
        self.assertEqual(status, 200, result)
        self.assertEqual(result["runtime"]["state"], "Running")
        self.mutation("close", {})
        self.assertEqual(self.controller.close_calls, 0)
        self.close_server()
        self.assertEqual(self.controller.close_calls, 1)


if __name__ == "__main__":
    unittest.main()

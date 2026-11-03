"""Scratch HTTP/client contracts; no live project, model or EDA execution."""
from __future__ import annotations

import copy
import http.client
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.server import project_envelope
from hullcirq.workspace import WorkspaceRegistry
from hullcirq.workspace_server import make_workspace_server


class DeferredOpenHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=PROJECT / ".work")
        self.addCleanup(self.temp.cleanup)
        self.registry = WorkspaceRegistry(Path(self.temp.name) / "workspace")
        self.server = make_workspace_server("127.0.0.1", 0, self.registry)
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.01), daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.session = self.request("GET", "/api/workspace")[1]["active"]["session_id"]
        status, result = self.request("POST", "/api/workspace/create-project", {"name": "Software fixture", "system_name": "Main", "top_module": "fixture_top"})
        self.assertEqual(status, 200, result)
        self.session = result["workspace"]["active"]["session_id"]
        self.saved = result["project"]
        self.target = {key: result["workspace"]["active"][key] for key in ("project_id", "system_id")}

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def request(self, method, path, body=None, session=None):
        headers = {"X-HuLLCirq-Session": session or getattr(self, "session", "")}
        if body is not None:
            body = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        try:
            connection.request(method, path, body, headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_default_and_false_preserve_legacy_full_project_response(self):
        for flag in ({}, {"defer_project_view": False}):
            with self.subTest(flag=flag), patch("hullcirq.server.project_envelope", wraps=project_envelope) as full_view:
                status, response = self.request("POST", "/api/workspace/open", {**self.target, **flag})
                self.assertEqual(status, 200, response)
                full_view.assert_called_once_with(self.server)
                self.assertNotIn("project_view_deferred", response)
                self.assertEqual(response["project"]["revision"], self.saved["revision"])
                self.assertEqual(response["project"]["design"], self.saved["design"])
                self.session = response["workspace"]["active"]["session_id"]

    def test_deferred_response_omits_full_view_and_new_session_bootstrap_has_it(self):
        previous_session = self.session
        with patch("hullcirq.server.project_envelope", side_effect=AssertionError("Deferred Open must not build a full project view")) as full_view:
            status, response = self.request("POST", "/api/workspace/open", {**self.target, "defer_project_view": True})
        self.assertEqual(status, 200, response)
        full_view.assert_not_called()
        self.assertTrue(response["project_view_deferred"])
        self.assertNotIn("project", response)
        self.assertTrue(response["workspace"]["projects"])
        active = response["workspace"]["active"]
        self.assertEqual({key: active[key] for key in self.target}, self.target)
        self.assertNotEqual(active["session_id"], previous_session)
        self.session = active["session_id"]
        with patch("hullcirq.server.project_envelope", wraps=project_envelope) as full_view:
            status, bootstrap = self.request("GET", "/api/bootstrap")
        self.assertEqual(status, 200, bootstrap)
        full_view.assert_called_once_with(self.server)
        self.assertEqual(bootstrap["workspace_identity"]["session_id"], self.session)
        self.assertEqual(bootstrap["design"], self.saved["design"])
        self.assertEqual(bootstrap["revision"], self.saved["revision"])
        for key in ("workflow", "generation", "workflow_runs", "physical_workflow", "postlayout_workflow"):
            self.assertIn(key, bootstrap)
        status, stale = self.request("GET", "/api/bootstrap", session=previous_session)
        self.assertEqual(status, 409)
        self.assertEqual(stale["error"]["code"], "workspace_session_changed")

    def test_invalid_flag_is_rejected_before_open_without_context_mutation(self):
        runtime = self.server.workspace
        previous_identity = copy.deepcopy(runtime.identity)
        previous_context = runtime.context
        for value in (None, 0, 1, "true", [], {}):
            with self.subTest(value=value), patch.object(runtime, "open", wraps=runtime.open) as opened:
                status, response = self.request("POST", "/api/workspace/open", {**self.target, "defer_project_view": value})
                self.assertEqual(status, 400, response)
                self.assertEqual(response["error"]["code"], "invalid_defer_project_view")
                opened.assert_not_called()
                self.assertEqual(runtime.identity, previous_identity)
                self.assertIs(runtime.context, previous_context)

    def test_stale_management_session_cannot_open_deferred_project(self):
        runtime = self.server.workspace
        previous_context = runtime.context
        with patch.object(runtime, "open", wraps=runtime.open) as opened:
            status, response = self.request("POST", "/api/workspace/open", {**self.target, "defer_project_view": True}, session="stale-software-fixture")
        self.assertEqual(status, 409, response)
        self.assertEqual(response["error"]["code"], "workspace_session_changed")
        opened.assert_not_called()
        self.assertIs(runtime.context, previous_context)

    def test_unknown_deferred_target_keeps_old_context(self):
        previous_identity = copy.deepcopy(self.server.workspace.identity)
        previous_context = self.server.workspace.context
        status, response = self.request("POST", "/api/workspace/open", {"project_id": "project-" + "0" * 32, "system_id": "system-" + "0" * 32, "defer_project_view": True})
        self.assertEqual(status, 404, response)
        self.assertEqual(self.server.workspace.identity, previous_identity)
        self.assertIs(self.server.workspace.context, previous_context)

    def test_other_workspace_actions_keep_original_response(self):
        status, response = self.request("POST", "/api/workspace/close", {"defer_project_view": True})
        self.assertEqual(status, 200, response)
        self.assertIsNone(response["project"])
        self.assertNotIn("project_view_deferred", response)


CLIENT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync('src/gui/workspace.js','utf8').replace(/^import[^\n]*\n/gm,'').replace('export class WorkspaceManager','class WorkspaceManager');
const sandbox={};vm.createContext(sandbox);vm.runInContext(source+'\nglobalThis.WorkspaceManager=WorkspaceManager;',sandbox);
const manager=Object.create(sandbox.WorkspaceManager.prototype);
const normalized=value=>JSON.parse(JSON.stringify(value));
"""


class DeferredOpenClientTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for the isolated client contract checks.")
        result = subprocess.run([node, "-e", CLIENT + "\n(async()=>{\n" + body + "\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});"],
                                cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_open_requests_deferred_view_for_both_default_and_explicit_system(self):
        self.run_client(r"""
const calls=[];manager.operate=async(...args)=>calls.push(normalized(args));
const project={id:'fixture-project',name:'Software fixture',systems:[{id:'default-system'}]};
await manager.open(project);await manager.open(project,{id:'other-system'});
assert.deepEqual(calls.map(call=>[call[0],call[1],call[2].context]),[
 ['open',{project_id:'fixture-project',system_id:'default-system',defer_project_view:true},true],
 ['open',{project_id:'fixture-project',system_id:'other-system',defer_project_view:true},true]]);
""")

    def test_deferred_and_old_full_response_both_keep_protected_context_activation(self):
        self.run_client(r"""
const events=[];manager.busy=false;manager.render=()=>{};manager.renderChrome=()=>{};
manager.receive=value=>events.push(['receive',value]);
const workspace={active:{session_id:'new-session',project_id:'fixture-project',system_id:'fixture-system'}};
for(const result of [{workspace,project_view_deferred:true},{workspace,project:{design:{id:'legacy-full'}}}]) {
 events.length=0;
 manager.callbacks={beforeLeave:async()=>{events.push(['protect']);return true;},
  request:async(route,body)=>{events.push(['request',route,body]);return result;},
  activate:value=>events.push(['activate',value]),updated:()=>assert.fail('Context Open must reload, not update in place'),
  toast:()=>assert.fail('Context activation returns before success toast'),notify:message=>assert.fail(message)};
 await manager.operate('open',{defer_project_view:true},{context:true});
 assert.deepEqual(events.map(event=>event[0]),['protect','request','receive','activate']);
 assert.equal(events.at(-1)[1],result);assert.equal(manager.busy,false);
}
events.length=0;manager.callbacks.beforeLeave=async()=>false;
await manager.operate('open',{defer_project_view:true},{context:true});assert.equal(events.length,0);
""")


if __name__ == "__main__":
    unittest.main()

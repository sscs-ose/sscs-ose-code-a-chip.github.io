"""S08 API/browser software QA on an ephemeral fixture-only project.

The manager doubles and mocked successful proof are explicitly software QA.
No live node histories, model servers or EDA tools are accessed by these tests.
"""
from __future__ import annotations
import http.client
import json
import os
from pathlib import Path
import subprocess
import threading
import unittest
from unittest.mock import patch
from browser_qa_runtime import browser_environment

import test_global_generation as qa_fixture
from test_global_generation import PROJECT, fixture_proof, header
from hullcirq.global_generation import top_interface
from hullcirq.domain import DomainError
from hullcirq.server import make_server
from hullcirq.store import strict_loads
from hullcirq.verification import object_hash


class GlobalHTTPTests(unittest.TestCase):
    def setUp(self):
        self.qa=qa_fixture.GlobalSoftwareTests("test_manifest_exact_sources_and_prompt_excludes_numeric_test_job")
        self.qa.setUp(); self.addCleanup(self.qa.doCleanups)
        self.server=make_server("127.0.0.1",0,self.qa.store,PROJECT)
        self.server.global_generation.close(); self.server.global_generation=self.qa.manager
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={"poll_interval":.02},daemon=True); self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown(); self.server.server_close(); self.server.workflow.close(); self.server.generation.close(); self.thread.join(2)

    def request(self,path,body=None):
        connection=http.client.HTTPConnection("127.0.0.1",self.server.server_address[1],timeout=20)
        try:
            connection.request("GET" if body is None else "POST",path,None if body is None else json.dumps(body),
                {} if body is None else {"Content-Type":"application/json"})
            response=connection.getresponse(); raw=response.read()
            return response.status,raw,strict_loads(raw.decode())
        finally: connection.close()

    def test_context_and_fixed_lossless_preview_download_no_model_or_history(self):
        state_bytes=self.qa.store.state_path.read_bytes()
        revision=self.qa.store.envelope()["revision"]["id"]
        with patch("hullcirq.global_generation.ChatCompletionsClient") as client:
            status,_,preview=self.request("/api/global-generation/context",{"revision_id":revision})
            self.assertEqual(status,200)
            status,raw,download=self.request("/api/artifacts/global-preview/"+preview["context_id"]+"/context")
        client.assert_not_called(); self.assertEqual(status,200); self.assertEqual(object_hash(download),object_hash(preview))
        self.assertGreater(download["verification_plan"]["recipe"]["configuration_word"],2**53)
        self.assertIn(str(preview["verification_plan"]["recipe"]["configuration_word"]).encode(),raw)
        self.assertFalse(self.qa.manager.path.exists()); self.assertEqual(self.qa.store.state_path.read_bytes(),state_bytes)

    def test_fixed_job_artifacts_preserve_wide_int_and_reject_other_paths(self):
        job=self.qa.run_job()
        for path,expected in (("/api/global-generation/jobs/"+job["id"],job),
            ("/api/artifacts/global-generation/"+job["id"]+"/context",job["context"]),
            ("/api/artifacts/global-generation/"+job["id"]+"/source-manifest",job["context"]["source_manifest"]),
            ("/api/artifacts/global-generation/"+job["id"]+"/verification-plan",job["context"]["verification_plan"])):
            status,_,value=self.request(path); self.assertEqual(status,200); self.assertEqual(object_hash(value),object_hash(expected))
        saved=self.qa.manager.path.read_bytes()
        for path in ("/api/artifacts/global-generation/"+job["id"]+"/raw_content", "/api/artifacts/global-generation/../context",
            "/api/artifacts/global-preview/missing/context", "/api/global-generation/jobs/missing"):
            with self.subTest(path=path): self.assertEqual(self.request(path)[0],404)
        self.assertEqual(self.qa.manager.path.read_bytes(),saved)

    def test_profile_probe_and_node_generation_refuse_while_global_active(self):
        self.qa.manager._state["jobs"].append({"id":"software-active","execution_status":"Running"})
        for route,body in (("/api/llm/probe",{"profile_revision_id":"software-profile"}),
            ("/api/generation/start",{"node_id":"node-pe","revision_id":"r","context_id":"c","profile_revision_id":"p"})):
            with self.subTest(route=route):
                status,_,result=self.request(route,body)
                self.assertEqual(status,409); self.assertEqual(result["error"]["code"],"global_generation_busy")
        self.qa.manager._state["jobs"]=[]

    def test_actual_browser_helper_generation_and_lossless_downloads(self):
        environ = browser_environment()
        playwright=environ.get("HULLCIRQ_PLAYWRIGHT_PATH")
        if not playwright or not Path(playwright).is_dir(): self.skipTest("Set HULLCIRQ_PLAYWRIGHT_PATH to an installed Playwright package.")
        outputs=PROJECT/".work/m2e/global-gui-software-qa"/self.qa.directory.name
        environ.update({"HULLCIRQ_NPU_URL":f"http://127.0.0.1:{self.server.server_address[1]}/",
            "HULLCIRQ_GUI_OUTPUT_ROOT":str(outputs),"HULLCIRQ_GLOBAL_WAIT_MS":"20000"})
        rtl=header(top_interface(self.qa.store.envelope()["design"]))+"// SOFTWARE QA ONLY\nendmodule\n"
        raw="```verilog\n"+rtl+"```"
        def generate(messages,parameters,cancel,on_event):
            on_event({"type":"delta","content":raw})
            return {"raw_content":raw,"raw_reasoning":"","execution_status":"Completed","usage":{"completion_tokens":1},"error":None,"finish_reason":"stop"}
        with patch("hullcirq.global_generation.ChatCompletionsClient") as client,patch("hullcirq.global_generation.check_global_rtl",side_effect=fixture_proof):
            client.return_value.generate.side_effect=generate
            executed=subprocess.run(["node",str(PROJECT/"scripts/run_global_project_gui.cjs"),"generate"],cwd=PROJECT,env=environ,text=True,
                capture_output=True,encoding="utf-8",timeout=75)
        self.assertEqual(executed.returncode,0,executed.stdout+executed.stderr)
        folders=list(outputs.iterdir()); self.assertEqual(len(folders),1); folder=folders[0]
        operation=strict_loads((folder/"gui-operation.json").read_text(encoding="utf-8"))
        self.assertEqual(operation["page_errors"],[]); self.assertEqual(len(operation["downloads"]),6)
        self.assertGreater(operation["checks_view"]["rendered_characters"],100000)
        self.assertEqual(operation["checks_view"]["white_space"],"pre")
        self.assertEqual(operation["checks_view"]["overflow_wrap"],"normal")
        self.assertTrue(operation["checks_view"]["complete_display_record_present"])
        job=self.qa.manager.job(self.qa.manager._state["jobs"][-1]["id"])
        expected={"preview.json":job["context"],"job.json":job,"job-api-original.json":job,"context.json":job["context"],
            "source-manifest.json":job["context"]["source_manifest"],"verification-plan.json":job["context"]["verification_plan"]}
        for name,value in expected.items():
            with self.subTest(name=name): self.assertEqual(object_hash(strict_loads((folder/name).read_text(encoding="utf-8"))),object_hash(value))
        self.assertEqual((folder/"top.v").read_text(encoding="utf-8"),rtl)
        self.assertTrue((folder/"global-executed-checks.png").is_file())
        self.assertEqual(client.return_value.generate.call_count,1)

    def test_simultaneous_node_and_global_requests_admit_only_one_model(self):
        revision=self.qa.store.envelope()["revision"]["id"]
        context=self.qa.manager.preview(revision)
        entered=threading.Event(); prepared=threading.Event(); release=threading.Event(); results={}
        real_preview=self.qa.manager.preview
        def node_start(*args, submission_id=None, _preflight=None):
            self.assertIsNone(submission_id)
            self.assertIsNone(_preflight)  # Legacy admission already ran in the handler.
            entered.set()
            if not release.wait(5): raise DomainError("qa_timeout","SOFTWARE QA coordination timeout",500)
            self.qa.sources.generation._state["jobs"][0]["execution_status"]="Running"
            return {"generation_submission": {"version": "node-submission-v1", "submission_id": None,
                "job_id": self.qa.sources.generation._state["jobs"][0]["id"], "replayed": False}}
        def global_preview(*args,**kwargs):
            prepared.set(); return real_preview(*args,**kwargs)
        def request(name,path,body): results[name]=self.request(path,body)
        with patch.object(self.server.generation,"start",side_effect=node_start),patch.object(self.qa.manager,"preview",side_effect=global_preview),patch("hullcirq.global_generation.ChatCompletionsClient") as client:
            local=threading.Thread(target=request,args=("node","/api/generation/start",{"node_id":"node-pe","revision_id":revision,"context_id":"qa","profile_revision_id":"software-profile"}))
            local.start(); self.assertTrue(entered.wait(3))
            global_thread=threading.Thread(target=request,args=("global","/api/global-generation/start",{"revision_id":revision,"context_id":context["context_id"],"profile_revision_id":context["profile_revision_id"]}))
            global_thread.start()
            try:
                # Shared execution admission now precedes global preparation.
                # The pending global request cannot start or prepare a model
                # call while the node request is still being admitted.
                global_thread.join(.1); self.assertTrue(global_thread.is_alive())
                self.assertFalse(prepared.is_set())
                self.assertEqual(self.qa.manager._state["jobs"],[]); client.assert_not_called()
            finally: release.set(); local.join(5); global_thread.join(5)
        self.assertFalse(local.is_alive()); self.assertFalse(global_thread.is_alive())
        self.assertEqual(results["node"][0],202); self.assertEqual(results["global"][0],409)
        self.assertEqual(self.qa.manager._state["jobs"],[]); client.assert_not_called()
        self.qa.sources.generation._state["jobs"][0]["execution_status"]="Completed"


if __name__=="__main__": unittest.main()

"""S11 loopback route QA with explicit doubles, never circuit/EDA evidence."""
from __future__ import annotations

from contextlib import ExitStack
import http.client
import json
import threading
import unittest
from unittest.mock import patch

import test_global_generation as fixtures
from hullcirq.domain import DomainError
from hullcirq.server import make_server
from hullcirq.store import strict_loads


class PhysicalDouble:
    """SOFTWARE QA route double; every byte and status below is simulated."""
    def __init__(self,revision_id):
        self.active=False; self.visible=False; self.calls=[]; self.revision_id=revision_id
        self.source_ids=("software-current-global","software-current-synthesis","software-current-netlist")
        self.record={"id":"software-layout","stage_id":"layout","execution_status":"Completed","validation_status":"Failed",
            "review_status":"Awaiting Review","freshness":"Current","checks":{},"software_qa_fixture":True,
            "global_job_id":self.source_ids[0],"synthesis_run_id":self.source_ids[1],"netlist_run_id":self.source_ids[2]}
        self.binary={"png":(b"\x89PNG\r\n\x1a\nSOFTWARE_QA\x00\xff","image/png"),
            "gds":(b"\x00\x06\x00\x02\x00\x03SOFTWARE_QA\x00\xff","application/octet-stream"),
            "def":(b"VERSION 5.8 ;\r\nDESIGN SOFTWARE_QA_ONLY ;\r\nEND DESIGN\r\n","text/plain; charset=utf-8")}

    def envelope(self):
        return {"physical_workflow":{"implemented":True,"stage_id":"layout","runs":[self.record] if self.visible else [],"reviews":[],
            "latest_run_id":self.record["id"] if self.visible else None,"accepted_run_id":None,"ready":False,"blocked_reason":"SOFTWARE QA double, no physical execution",
            "tool_ready":False,"tool_blocked_reason":"No actual tool is used","settings_projection":{},"runtime_configuration_sha256":None}}

    def start(self,stage,global_job_id,synthesis_run_id,netlist_run_id,revision_id=None):
        if stage!="layout" or (global_job_id,synthesis_run_id,netlist_run_id)!=self.source_ids or revision_id!=self.revision_id:
            raise DomainError("physical_source_conflict","SOFTWARE QA source ID mismatch",409)
        self.calls.append(("start",(stage,global_job_id,synthesis_run_id,netlist_run_id,revision_id)))
        self.active=True; self.visible=True; self.record.update(execution_status="Queued",validation_status="Not Checked")
        # Match the real manager return contract; no worker or receipt is created.
        return self.envelope()

    def run(self,identifier):
        if identifier!=self.record["id"]: raise DomainError("physical_run_not_found","SOFTWARE QA missing run",404)
        return self.record

    def cancel(self,identifier):
        self.run(identifier); self.calls.append(("cancel",identifier)); self.active=False; self.record["execution_status"]="Cancelled"

    def review(self,*args,operator=None):
        self.run(args[0]); self.calls.append(("review",args))

    def artifact(self,identifier,field):
        self.run(identifier)
        if field in ("verification-plan","source-manifest","settings","runtime-configuration"):
            return {"configuration_word":2**133+123,"software_qa_fixture":True}
        if field=="artifact-manifest": return [{"id":name,"software_qa_fixture":True} for name in self.binary]
        if field=="sdc": return "# SOFTWARE QA only\r\ncreate_clock -period 50 [get_ports clk]\r\n"
        raise DomainError("physical_artifact_not_found","SOFTWARE QA missing artifact",404)

    def artifact_bytes(self,identifier,field):
        self.run(identifier)
        if field not in self.binary: raise DomainError("physical_artifact_not_found","SOFTWARE QA missing binary",404)
        return self.binary[field]

    def is_active(self): return self.active
    def close(self): pass


class PhysicalWorkflowHTTPTests(unittest.TestCase):
    def setUp(self):
        self.qa=fixtures.GlobalSoftwareTests("test_manifest_exact_sources_and_prompt_excludes_numeric_test_job"); self.qa.setUp(); self.addCleanup(self.qa.doCleanups)
        self.server=make_server("127.0.0.1",0,self.qa.store,fixtures.PROJECT)
        self.original_physical=self.server.physical_workflow
        self.double=PhysicalDouble(self.qa.store.envelope()["revision"]["id"]); self.server.physical_workflow=self.double
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={"poll_interval":.02},daemon=True); self.thread.start(); self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown(); self.server.server_close(); self.original_physical.close(); self.server.workflow.close(); self.server.generation.close(); self.thread.join(2)

    def request(self,path,body=None):
        connection=http.client.HTTPConnection("127.0.0.1",self.server.server_address[1],timeout=20)
        try:
            connection.request("GET" if body is None else "POST",path,None if body is None else json.dumps(body),{} if body is None else {"Content-Type":"application/json"})
            response=connection.getresponse(); raw=response.read()
            return response.status,raw,dict(response.getheaders())
        finally: connection.close()

    def json_request(self,path,body=None):
        status,raw,headers=self.request(path,body)
        return status,raw,strict_loads(raw.decode("utf-8")),headers

    def start_body(self):
        return {"stage":"layout","global_job_id":self.double.source_ids[0],"synthesis_run_id":self.double.source_ids[1],
                "netlist_run_id":self.double.source_ids[2],"revision_id":self.double.revision_id}

    def test_implemented_stage_is_not_run_without_actual_sources_or_runtime(self):
        self.server.physical_workflow=self.original_physical
        status,_,project,_=self.json_request("/api/bootstrap")
        self.assertEqual(status,200)
        layout=next(s for s in project["workflow"] if s["id"]=="layout")
        self.assertTrue(layout["implemented"]); self.assertEqual(layout["execution_status"],"Not Run")
        self.assertEqual(layout["validation_status"],"Not Checked"); self.assertIsNone(layout["accepted_run_id"])
        self.assertFalse(project["physical_workflow"]["tool_ready"]); self.assertFalse(project["physical_workflow"]["ready"])
        self.assertFalse(project["implementation"]["layout_executed"]); self.assertFalse(project["implementation"]["pdk_used"])
        self.assertTrue(next(s for s in project["workflow"] if s["id"] == "drc")["implemented"])
        self.assertTrue(next(s for s in project["workflow"] if s["id"] == "lvs")["implemented"])
        self.assertTrue(next(s for s in project["workflow"] if s["id"] == "post_layout_verification")["implemented"])
        self.assertEqual(self.original_physical._state["runs"],[])

    def test_exact_source_start_cancel_review_and_invalid_requests(self):
        body=self.start_body()
        status,_,project,_=self.json_request("/api/physical-workflow/runs",body)
        self.assertEqual(status,202)
        self.assertEqual(self.double.calls[-1],("start",("layout",*self.double.source_ids,self.double.revision_id)))
        self.assertEqual(next(s for s in project["workflow"] if s["id"]=="layout")["execution_status"],"Queued")
        self.assertEqual(self.json_request("/api/physical-workflow/runs/software-layout")[2]["id"],"software-layout")
        self.assertEqual(self.json_request("/api/physical-workflow/runs/software-layout/cancel",{})[0],200)
        self.assertEqual(self.double.calls[-1],("cancel","software-layout"))
        feedback={"decision":"return_to_stage","note":"SOFTWARE QA feedback","target_stage":"global_netlist_simulation"}
        self.assertEqual(self.json_request("/api/physical-workflow/runs/software-layout/review",feedback)[0],200)
        self.assertEqual(self.double.calls[-1],("review",("software-layout","return_to_stage","SOFTWARE QA feedback","global_netlist_simulation")))
        for missing in ("stage","global_job_id","synthesis_run_id","netlist_run_id"):
            bad=dict(body); bad.pop(missing)
            with self.subTest(missing=missing): self.assertEqual(self.json_request("/api/physical-workflow/runs",bad)[0],400)
        bad=dict(body,netlist_run_id="old-source")
        self.assertEqual(self.json_request("/api/physical-workflow/runs",bad)[0],409)
        self.assertEqual(self.json_request("/api/physical-workflow/runs/software-layout/unknown",{})[0],404)
        self.assertEqual(self.json_request("/api/physical-workflow/runs/software-layout/review",{"decision":"accepted"})[0],400)

    def test_binary_bytes_mime_and_disposition_are_exact(self):
        for name,(expected,mime) in self.double.binary.items():
            with self.subTest(artifact=name):
                status,raw,headers=self.request("/api/artifacts/physical-workflow/software-layout/"+name)
                self.assertEqual(status,200); self.assertEqual(raw,expected)
                self.assertEqual(headers["Content-Type"],mime); self.assertEqual(int(headers["Content-Length"]),len(expected))
                disposition="inline" if name=="png" else "attachment"
                self.assertEqual(headers["Content-Disposition"],f'{disposition}; filename="layout.{name}"')
                self.assertEqual(headers["Cache-Control"],"no-store"); self.assertEqual(headers["X-Content-Type-Options"],"nosniff")
        self.assertEqual(self.double.calls,[])

    def test_json_download_keeps_wide_integer_and_denies_unknown_or_traversal(self):
        for artifact in ("verification-plan","source-manifest","settings","runtime-configuration"):
            status,raw,value,headers=self.json_request("/api/artifacts/physical-workflow/software-layout/"+artifact)
            self.assertEqual(status,200); self.assertEqual(value["configuration_word"],2**133+123)
            self.assertIn(str(2**133+123).encode(),raw); self.assertIn("attachment",headers["Content-Disposition"])
        status,_,text,_=self.json_request("/api/artifacts/physical-workflow/software-layout/sdc")
        self.assertEqual(status,200); self.assertEqual(text,self.double.artifact("software-layout","sdc"))
        for path in ("/api/artifacts/physical-workflow/software-layout/arbitrary-expression",
            "/api/artifacts/physical-workflow/../def","/api/artifacts/physical-workflow/%2e%2e/def",
            "/api/artifacts/physical-workflow/software-layout/%2e%2e%2fstate.json",
            "/api/artifacts/physical-workflow/software%5Clayout/png","/api/physical-workflow/runs/missing",
            "/api/physical-workflow/runs/software-layout/extra","/api/artifacts/physical-workflow/software-layout/png/extra"):
            with self.subTest(path=path): self.assertEqual(self.json_request(path)[0],404)
        self.assertEqual(self.double.calls,[])

    def test_active_physical_execution_blocks_all_other_start_and_probe_routes(self):
        self.double.active=True
        cases=[("/api/physical-workflow/runs",self.start_body()),("/api/global-workflow/runs",{"stage":"global_synthesis","global_job_id":"qa"}),
            ("/api/workflow/start",{"stage_id":"local_synthesis","node_id":"node-pe","candidate_id":"qa","revision_id":"qa"}),
            ("/api/llm/probe",{"profile_revision_id":"qa"}),
            ("/api/global-generation/start",{"revision_id":"qa","context_id":"qa","profile_revision_id":"qa"}),
            ("/api/generation/start",{"node_id":"node-pe","revision_id":"qa","context_id":"qa","profile_revision_id":"qa"})]
        with ExitStack() as stack:
            protected=[stack.enter_context(patch.object(manager,method)) for manager,method in
                ((self.server.global_workflow,"start"),(self.server.workflow,"start"),(self.server.generation,"probe"),(self.server.global_generation,"start"),(self.server.generation,"start"))]
            for path,body in cases:
                with self.subTest(path=path):
                    status,_,value,_=self.json_request(path,body); self.assertEqual(status,409); self.assertEqual(value["error"]["code"],"physical_workflow_busy")
            for guarded in protected: guarded.assert_not_called()
        self.assertEqual(self.double.calls,[])

    def test_active_earlier_tool_or_model_blocks_physical_admission(self):
        for manager in (self.server.global_generation,self.server.global_workflow):
            with patch.object(manager,"is_active",return_value=True):
                status,_,value,_=self.json_request("/api/physical-workflow/runs",self.start_body())
                self.assertEqual(status,409); self.assertIn(value["error"]["code"],("global_workflow_busy","competing_execution_busy"))
        for manager,key in ((self.server.generation,"jobs"),(self.server.workflow,"runs")):
            manager._state[key].append({"execution_status":"Running"})
            try:
                status,_,value,_=self.json_request("/api/physical-workflow/runs",self.start_body())
                self.assertEqual(status,409); self.assertEqual(value["error"]["code"],"competing_execution_busy")
            finally: manager._state[key].pop()
        self.assertEqual(self.double.calls,[])

    def test_fixed_retry_route_accepts_only_ids_and_never_starts_execution(self):
        """The full saved-proof checks belong to the fixed preparation module."""
        body={"failed_layout_id":"software-layout", "revision_id":self.double.revision_id}
        with patch("hullcirq.physical_repair_session.prepare_retry",create=True) as prepare:
            for bad in ({}, {"failed_layout_id":"software-layout"},
                        {**body,"command":"SOFTWARE QA forbidden"},
                        {**body,"configuration":{}}):
                with self.subTest(bad=bad):
                    status,_,value,_=self.json_request("/api/physical-workflow/repair-profile",bad)
                    self.assertEqual(status,400)
                    self.assertEqual(value["error"]["code"],"physical_repair_request_invalid")
            self.assertEqual(self.json_request("/api/physical-workflow/repair-profile",[])[0],400)
            prepare.assert_not_called()
            def prepared(server, failed, revision):
                self.assertIs(server,self.server)
                self.assertEqual((failed,revision),(body["failed_layout_id"],body["revision_id"]))
                self.server.physical_repair_session={"configured":True,"repair_generation":2,
                    "profile_version":"hullcirq-sky130-route-repair-npu2v2","actor":"explicit_GUI_action"}
            prepare.side_effect=prepared
            status,_,value,_=self.json_request("/api/physical-workflow/repair-profile",body)
            self.assertEqual(status,200)
            prepare.assert_called_once_with(self.server,"software-layout",self.double.revision_id)
            self.assertEqual(value["physical_repair_session"]["repair_generation"],2)
        self.assertEqual(self.double.calls,[])
        self.assertEqual(self.double.record["execution_status"],"Completed")

    def test_fixed_retry_route_can_return_third_generation_without_a_tool_start(self):
        body={"failed_layout_id":"software-second-layout", "revision_id":self.double.revision_id}
        def prepared(server, failed, revision):
            self.assertEqual((failed,revision),(body["failed_layout_id"],body["revision_id"]))
            server.physical_repair_session={"configured":True,"repair_generation":3,
                "profile_version":"hullcirq-sky130-route-repair-npu2v3","actor":"explicit_GUI_action"}
        with patch("hullcirq.physical_repair_session.prepare_retry",side_effect=prepared) as prepare:
            status,_,value,_=self.json_request("/api/physical-workflow/repair-profile",body)
            self.assertEqual(status,200)
            self.assertEqual(value["physical_repair_session"]["repair_generation"],3)
            prepare.assert_called_once_with(self.server,body["failed_layout_id"],self.double.revision_id)
        self.assertEqual(self.double.calls,[])
        self.assertEqual(self.double.record["execution_status"],"Completed")

    def test_fixed_retry_route_serializes_and_blocks_active_model_and_tools(self):
        body={"failed_layout_id":"software-layout","revision_id":self.double.revision_id}
        with patch("hullcirq.physical_repair_session.prepare_retry",create=True) as prepare:
            for manager,code in ((self.double,"physical_workflow_busy"),
                                 (self.server.postlayout_workflow,"postlayout_workflow_busy"),
                                 (self.server.repair_analysis,"repair_analysis_busy"),
                                 (self.server.global_generation,"competing_execution_busy")):
                with self.subTest(code=code), patch.object(manager,"is_active",return_value=True):
                    status,_,value,_=self.json_request("/api/physical-workflow/repair-profile",body)
                    self.assertEqual(status,409); self.assertEqual(value["error"]["code"],code)
            prepare.assert_not_called()
            # The request waits for the shared admission lock before preparing.
            completed=threading.Event(); started=threading.Event(); outcomes={}
            def request_retry():
                started.set()
                outcomes["status"]=self.json_request("/api/physical-workflow/repair-profile",body)[0]
                completed.set()
            with self.server.execution_lock:
                thread=threading.Thread(target=request_retry); thread.start()
                self.assertTrue(started.wait(5)); self.assertFalse(completed.wait(.1))
                prepare.assert_not_called()
            thread.join(10); self.assertFalse(thread.is_alive())
            self.assertEqual(outcomes,{"status":200}); prepare.assert_called_once()
        self.assertEqual(self.double.calls,[])

    def test_in_progress_probe_serializes_physical_start_without_overlap(self):
        entered=threading.Event(); release=threading.Event(); physical_done=threading.Event(); physical_requested=threading.Event(); outcomes={}
        def probe(*args): entered.set(); release.wait(5)
        def request_probe(): outcomes["probe"]=self.json_request("/api/llm/probe",{"profile_revision_id":"software-only"})[0]
        def request_physical():
            physical_requested.set(); outcomes["physical"]=self.json_request("/api/physical-workflow/runs",self.start_body())[0]; physical_done.set()
        with patch.object(self.server.generation,"probe",side_effect=probe):
            probe_thread=threading.Thread(target=request_probe); physical_thread=threading.Thread(target=request_physical)
            probe_thread.start(); self.assertTrue(entered.wait(5)); physical_thread.start(); self.assertTrue(physical_requested.wait(5))
            try:
                self.assertFalse(physical_done.wait(.1)); self.assertEqual(self.double.calls,[])
            finally: release.set(); probe_thread.join(10); physical_thread.join(10)
        self.assertFalse(probe_thread.is_alive()); self.assertFalse(physical_thread.is_alive())
        self.assertEqual(outcomes,{"probe":200,"physical":202}); self.assertEqual(len(self.double.calls),1)


if __name__=="__main__": unittest.main()

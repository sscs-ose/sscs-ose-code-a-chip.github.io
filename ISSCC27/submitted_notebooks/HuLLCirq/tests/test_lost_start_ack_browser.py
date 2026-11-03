"""True lost HTTP start acknowledgement on an isolated browser/software backend.

The backend doubles never run EDA/models or create qualifying/adopted proof.
The socket is dropped only after the fixture backend created exactly one job.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest

from browser_qa_runtime import browser_environment
from hullcirq.domain import DomainError
from hullcirq.server import make_server
from hullcirq.store import ProjectStore, utc_now
from test_physical_workflow_gui import (PROJECT, AcceptedBaselineDouble,
    GlobalGenerationDouble, PhysicalDouble, PhysicalControlHandler)


class LostAckHandler(PhysicalControlHandler):
    def do_GET(self):
        self.server.qa_requests.append(('GET', self.path))
        super().do_GET()

    def do_POST(self):
        self.server.qa_requests.append(('POST', self.path))
        if self.path == '/api/physical-workflow/runs' and self.server.qa_mode == 'reject':
            body = self._read_body()
            def reject_before_creation():
                raise DomainError('software_qa_rejected_source', 'SOFTWARE QA source rejected before creation.', 409)
            try:
                with self.server.execution_lock:
                    self._execution_start(self.server.physical_workflow, 'physical-workflow/runs', body,
                        lambda ticket: (_ for _ in ()).throw(AssertionError('Rejected fixture must never create a job')),
                        reject_before_creation)
            except DomainError as error:
                self._error(error)
            return
        super().do_POST()

    def _json(self, value, status=200, extra=None):
        if (self.command == 'POST' and self.path == '/api/physical-workflow/runs'
                and 200 <= status < 300 and not self.server.qa_drops):
            double = self.server.physical_workflow
            with double.lock:
                assert len(double.calls) == len(double.runs) == 1
                # A fast terminal job makes an accidental replay observable:
                # there is no active-worker lock hiding duplicate-start bugs.
                double.runs[0].update(execution_status='Completed', validation_status='Not Checked',
                    review_status='Awaiting Review', finished_at=utc_now(), error=None)
                double._persist()
                self.server.qa_created_id = double.runs[0]['id']
                # Retain a durable, explicitly software-only fixture ledger
                # before the acknowledgement is dropped. Never circuit proof.
                with self.server.qa_ledger.open('xb') as ledger:
                    ledger.write(json.dumps({'software_qa_fixture':True,'record':double.runs[0]}).encode())
                    ledger.flush();os.fsync(ledger.fileno())
            self.server.qa_drops += 1
            self.close_connection = True
            try:self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:pass
            self.connection.close()
            return
        super()._json(value, status, extra)


BROWSER = r"""
const assert=require('node:assert/strict');
const {chromium}=require(process.env.HULLCIRQ_PLAYWRIGHT_PATH||'playwright');
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});
try{const context=await browser.newContext(),page=await context.newPage();page.setDefaultTimeout(20000);
const url=process.env.HULLCIRQ_SOFTWARE_QA_URL,mode=process.env.HULLCIRQ_SOFTWARE_QA_MODE;
await context.route('**/*',route=>new URL(route.request().url()).origin===new URL(url).origin?route.continue():route.abort());
const starts=[],gets=[],errors=[];page.on('pageerror',e=>errors.push(e.message));
page.on('request',r=>{const p=new URL(r.url()).pathname;if(r.method()==='POST'&&p==='/api/physical-workflow/runs')starts.push(p);if(r.method()==='GET'&&p==='/api/project')gets.push(p);});
const test=id=>page.getByTestId(id);
await page.goto(url);await test('stage-global_netlist_simulation').click();await test('global-workflow-continue').click();
assert.equal(await test('physical-workflow-run').isEnabled(),true);
await test('physical-workflow-run').click();
if(mode==='reject'){
 // A durable precreation refusal is a known outcome, not a lost ACK. The new
 // protocol clears its marker immediately; the test never submits a new intent.
 await page.waitForFunction(()=>document.querySelector('#stage-status')?.getAttribute('data-status')==='Failed');
 assert.equal(await test('execution-submission-refresh').count(),0);assert.equal(starts.length,1);
 const saved=await(await context.request.get(url+'api/project')).json();assert.equal(saved.physical_workflow.runs.length,0);
 assert.deepEqual(errors,[]);console.log(JSON.stringify({scope:'isolated software browser/HTTP fixture, not GUI circuit qualification',mode,start_posts:starts.length,reconnect_gets:0,definite_precreation_refusal:true}));
 return;
}
await test('execution-submission-refresh').waitFor();
assert.equal(starts.length,1);assert.equal(await test('physical-workflow-run').isDisabled(),true);
// A disabled native button must not send a second start even if clicked again.
await test('physical-workflow-run').evaluate(el=>el.click());await page.waitForTimeout(150);assert.equal(starts.length,1);
const beforeReconnectGets=gets.length;
if(mode==='changed')await context.request.post(url+'software-qa/external-source',{data:{}});
await test('execution-submission-refresh').click();
await page.waitForFunction(()=>!document.querySelector('[data-testid="execution-submission-refresh"]'));
assert.ok(gets.length>beforeReconnectGets,'Reconnect must read the saved project');assert.equal(starts.length,1,'Reconnect cannot replay the POST');
if(mode==='reject'){const saved=await(await context.request.get(url+'api/project')).json();assert.equal(saved.physical_workflow.runs.length,0);}
else{assert.match(await test('physical-workflow-result').innerText(),/software-qa-layout/);}
if(mode==='changed')assert.equal(await test('physical-workflow-run').isDisabled(),true,'Changed sources still block a new execution');
assert.deepEqual(errors,[]);console.log(JSON.stringify({scope:'isolated software browser/HTTP fixture, not GUI circuit qualification',mode,start_posts:starts.length,reconnect_gets:gets.length-beforeReconnectGets}));
}finally{await browser.close();}})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
"""


class LostStartAcknowledgementBrowserTests(unittest.TestCase):
    def run_case(self, mode):
        node=shutil.which('node')
        if not node:self.skipTest('Node and installed Playwright required; no packages are installed.')
        qa=PROJECT/'.work/qa';qa.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='lost-ack-software-',dir=qa) as temporary:
            directory=Path(temporary);self.assertTrue(directory.resolve().is_relative_to(qa.resolve()))
            store=ProjectStore(directory/'project',PROJECT/'examples/npu_all_nodes_project.json')
            original=copy.deepcopy(store.envelope()['design']);revision=store.envelope()['revision']['id']
            server=make_server('127.0.0.1',0,store,PROJECT)
            server.physical_workflow.close();server.global_workflow.close();server.global_generation.close()
            server.global_workflow=AcceptedBaselineDouble(store)
            server.global_generation=GlobalGenerationDouble(revision)
            server.physical_workflow=double=PhysicalDouble(store)
            server.RequestHandlerClass=LostAckHandler
            server.qa_mode=mode;server.qa_requests=[];server.qa_drops=0;server.qa_created_id=None
            server.qa_ledger=directory/'software-qa-job-ledger.json'
            thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);thread.start()
            try:
                env=browser_environment();env['HULLCIRQ_SOFTWARE_QA_URL']=f'http://127.0.0.1:{server.server_address[1]}/';env['HULLCIRQ_SOFTWARE_QA_MODE']=mode
                result=subprocess.run([node,'-e',BROWSER],cwd=PROJECT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=55)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertEqual(sum(method=='POST' and path=='/api/physical-workflow/runs' for method,path in server.qa_requests),1)
                self.assertEqual(len(double.calls),0 if mode=='reject' else 1)
                self.assertEqual(len(double.runs),0 if mode=='reject' else 1)
                self.assertEqual(server.qa_drops,0 if mode=='reject' else 1)
                self.assertFalse(double.reviews,'No fixture job may be adopted.')
                if mode=='reject':self.assertFalse(server.qa_ledger.exists())
                else:
                    saved=json.loads(server.qa_ledger.read_bytes())
                    self.assertTrue(saved['software_qa_fixture']);self.assertEqual(saved['record']['id'],server.qa_created_id)
                    self.assertEqual(saved['record']['review_status'],'Awaiting Review')
                for run in double.runs:
                    self.assertTrue(run['software_qa_fixture']);self.assertNotEqual(run['review_status'],'Accepted');self.assertEqual(run['id'],server.qa_created_id)
                if mode!='changed':self.assertEqual(store.envelope()['design'],original)
            finally:
                server.shutdown();server.server_close();server.workflow.close();server.generation.close();thread.join(2)

    def test_ack_lost_after_one_persisted_fast_terminal_job_reconnects_without_replay(self):self.run_case('lost')
    def test_rejected_start_creates_no_job_and_is_not_replayed(self):self.run_case('reject')
    def test_changed_sources_after_lost_ack_remain_blocked_after_reconnect(self):self.run_case('changed')

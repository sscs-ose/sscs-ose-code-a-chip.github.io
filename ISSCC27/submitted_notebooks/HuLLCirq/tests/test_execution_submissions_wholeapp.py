"""Real WorkspaceRuntime/HTTP/browser recovery, SOFTWARE-only terminal jobs.

The physical controller double persists only Not Checked/unadopted fixture
records. It never invokes an EDA adapter, provider, native tool or real project.
"""
import copy
from contextlib import contextmanager
from http.server import HTTPServer
import json
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from browser_qa_runtime import browser_environment
from hullcirq.domain import DomainError
from hullcirq.server import HuLLCirqServer, RequestHandler
from hullcirq.store import ProjectStore, _io_path, utc_now
from hullcirq.workspace import WorkspaceRegistry
from hullcirq.workspace_server import make_workspace_server
from test_physical_workflow_gui import PhysicalDouble, AcceptedBaselineDouble, GlobalGenerationDouble

ROOT=Path(__file__).resolve().parents[1]


@contextmanager
def owned_directory(parent):
    directory=Path(tempfile.mkdtemp(prefix='execution-workspace-',dir=parent))
    try:yield directory
    finally:
        # Native Windows recursion needs the same extended-path boundary as the
        # product. Resolve and verify ownership before this isolated cleanup.
        assert directory.resolve().parent==parent.resolve()
        shutil.rmtree(_io_path(directory))


class ReceiptPhysicalDouble(PhysicalDouble):
    def __init__(self,store,mode,counter):
        super().__init__(store)
        self.mode,self.counter=mode,counter
        self.path=store.state_path.parent/'SOFTWARE_ONLY_transport_ledger.json'
        if _io_path(self.path).exists():
            self._state=json.loads(_io_path(self.path).read_bytes())
            self.runs,self.reviews=self._state['runs'],self._state['reviews']
        else:self._state={'runs':self.runs,'reviews':self.reviews}
        self._committed=copy.deepcopy(self._state)

    def _persist(self):
        raw=json.dumps(self._state,ensure_ascii=False,indent=2).encode()
        with _io_path(self.path).open('wb') as handle:
            handle.write(raw);handle.flush()
            import os
            os.fsync(handle.fileno())
        self._committed=copy.deepcopy(self._state)

    def start(self,stage,job,synthesis,netlist,revision,*,_submission=None):
        with self.lock:
            if self.mode=='reject':raise DomainError('software_fixture_rejected','SOFTWARE QA pre-start refusal.',409)
            self.counter.append(1)
            run={'id':f'software-transport-{len(self.counter)}','stage_id':stage,'global_job_id':job,
                 'synthesis_run_id':synthesis,'netlist_run_id':netlist,'revision_id':revision,
                 'execution_status':'Completed','validation_status':'Not Checked','review_status':'Awaiting Review',
                 'freshness':'Current','created_at':utc_now(),'finished_at':utc_now(),'error':None,
                 'checks':{},'diagnostics':[],'artifacts':[],'software_qa_fixture':True,
                 'source_manifest':{'software_qa_fixture':True},'verification_plan':{'software_qa_fixture':True},
                 'settings':copy.deepcopy(self.store.envelope()['design']['settings']),
                 'runtime_configuration':{'software_qa_fixture':True},'evidence_kind':'software_transport_fixture'}
            if _submission is not None:
                run['submission_id']=_submission.submission_id
                _submission.bind(run['id'])
            self.runs.append(run);self._persist()
        return self.envelope()


class Fixture:
    def __init__(self,directory,mode):
        self.mode=mode;self.counter=[];self.payloads=[];self.sessions=[];self.faults=0;self.restart_error=None
        self.registry=WorkspaceRegistry(directory/'workspace')
        self.target=self.registry.create_project('SOFTWARE transport fixture')
        path=self.registry.resolve_system(self.target['project_id'],self.target['system_id'])['path']
        store=ProjectStore(path);design=json.loads((ROOT/'examples/npu_all_nodes_project.json').read_text())
        design['project']=store.envelope()['design']['project'];design['system']=store.envelope()['design']['system']
        store.save(design,store.envelope()['revision']['id']);self.original=copy.deepcopy(design)
        self.server=None;self.thread=None;self.new_session=None;self.restarting=False
        self.start(0)

    def start(self,port):
        # The real default local-runtime status would probe the live model port.
        # This explicit stopped software fixture performs no connection/start.
        runtime=SimpleNamespace(status=lambda:{'state':'Stopped','can_start':False,'can_stop':False,'message':'SOFTWARE fixture: no model runtime'},close=lambda:None)
        server=make_workspace_server('127.0.0.1',port,self.registry,ROOT,local_runtime=runtime)
        server.workspace.open(self.target['project_id'],self.target['system_id'])
        context=server.workspace.context;revision=context.store.envelope()['revision']['id']
        for name,value in [('global_workflow',AcceptedBaselineDouble(context.store)),('global_generation',GlobalGenerationDouble(revision)),('physical_workflow',ReceiptPhysicalDouble(context.store,self.mode,self.counter))]:
            getattr(context,name).close();setattr(context,name,value);setattr(server,name,value)
        fixture=self
        class Handler(RequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                if self.path=='/software-qa/restart':
                    self._read_body();self._json({'accepted':True},202)
                    threading.Thread(target=fixture.restart,daemon=True).start();return
                if self.path=='/api/physical-workflow/runs' and fixture.mode=='before' and not fixture.faults:
                    body=self._read_body();fixture.payloads.append(body);fixture.sessions.append(self.headers.get('X-HuLLCirq-Session'));fixture.faults+=1;self.drop();return
                return super().do_POST()
            def _read_body(self):
                value=super()._read_body()
                if self.path=='/api/physical-workflow/runs' and not (fixture.mode=='before' and not fixture.faults):
                    fixture.payloads.append(copy.deepcopy(value));fixture.sessions.append(self.headers.get('X-HuLLCirq-Session'))
                return value
            def drop(self):
                self.close_connection=True
                try:self.connection.shutdown(socket.SHUT_RDWR)
                except OSError:pass
                self.connection.close()
            def _json(self,value,status=200,extra=None):
                if self.command=='POST' and self.path=='/api/physical-workflow/runs' and 200<=status<300 and fixture.mode=='restart' and not fixture.faults:
                    assert len(fixture.counter)==1
                    fixture.faults+=1;self.drop();return
                return super()._json(value,status,extra)
        server.RequestHandlerClass=Handler
        self.server=server;self.port=server.server_address[1];self.new_session=server.workspace.identity['session_id']
        self.thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);self.thread.start()

    def restart(self):
        self.restarting=True
        try:
            port=self.port;self.stop();self.start(port)
        except Exception as error:self.restart_error=repr(error)
        finally:self.restarting=False

    def stop(self):
        if self.server:
            self.server.shutdown();self.server.server_close();self.thread.join(2)
            self.server=None


BROWSER=r"""
const assert=require('node:assert/strict');const{chromium}=require(process.env.HULLCIRQ_PLAYWRIGHT_PATH||'playwright');
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});try{
 const context=await browser.newContext(),page=await context.newPage();page.setDefaultTimeout(20000);
 const url=process.env.HULLCIRQ_SOFTWARE_QA_URL,mode=process.env.HULLCIRQ_SOFTWARE_QA_MODE;
 await context.route('**/*',r=>new URL(r.request().url()).origin===new URL(url).origin?r.continue():r.abort());
 const test=id=>page.getByTestId(id);const posts=[];page.on('request',r=>{if(r.method()==='POST'&&new URL(r.url()).pathname==='/api/physical-workflow/runs')posts.push(JSON.parse(r.postData()));});
 await page.goto(url);await test('stage-global_netlist_simulation').click();await test('global-workflow-continue').click();
 assert.equal(await test('physical-workflow-run').isEnabled(),true);await test('physical-workflow-run').click();
 if(mode==='reject'){
  await page.waitForFunction(()=>!document.querySelector('[data-testid="execution-submission-retry"]'));
  await page.waitForFunction(()=>document.querySelector('[data-testid="physical-workflow-run"]')?.disabled===false);
  assert.equal(posts.length,1);
 }else{
  await test('execution-submission-retry').waitFor();await page.waitForFunction(()=>!document.querySelector('[data-testid="execution-submission-retry"]').disabled);
  assert.equal(await test('physical-workflow-run').isDisabled(),true);
  const retained=await page.evaluate(()=>sessionStorage.getItem('hullcirq.execution-start-recovery.v1'));
  assert.ok(retained);assert.equal(JSON.parse(retained)[0].body.submission_id,posts[0].submission_id);assert.ok(!retained.includes('session_id'));
  if(mode==='restart'){
   const old=(await(await context.request.get(url+'api/workspace')).json()).active.session_id;
   await context.request.post(url+'software-qa/restart',{data:{}});
   await page.waitForFunction(async({url,old})=>{try{return(await(await fetch(url+'api/workspace')).json()).active.session_id!==old;}catch{return false;}},{url,old},{timeout:20000});
  }
  await page.reload();await test('stage-layout').click();
  if(mode==='before'){
   await test('execution-submission-retry').waitFor();assert.equal(await test('execution-submission-retry').isEnabled(),true);await test('execution-submission-retry').click();
  }
  await page.waitForFunction(()=>!document.querySelector('[data-testid="execution-submission-retry"]'));
  await page.waitForFunction(()=>document.querySelector('[data-testid="physical-workflow-result"]')?.innerText.includes('software-transport-1'));
  assert.equal(posts.length,mode==='before'?2:1);
  if(posts.length===2)assert.deepEqual(posts[0],posts[1],'Frozen request and nonce must survive reload');
  assert.equal(await test('physical-workflow-run').isEnabled(),true,'Known result must clear legacy controller uncertainty');
 }
 console.log(JSON.stringify({scope:'isolated real workspace HTTP/browser; software-only physical jobs',mode,start_posts:posts.length}));
}finally{await browser.close();}})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
"""


class ExecutionSubmissionsWholeAppTests(unittest.TestCase):
    def run_case(self,mode):
        node=shutil.which('node')
        if not node:self.skipTest('Installed Node/Playwright required; no packages installed.')
        qa=ROOT/'.work/qa';qa.mkdir(parents=True,exist_ok=True)
        # Test-only owned ephemeral listener; Windows forbids combining the
        # product's exclusive socket flag with the reuse needed for this test.
        # The production listener settings are never changed outside this scope.
        with owned_directory(qa) as temporary,patch.object(HuLLCirqServer,'allow_reuse_address',True),patch.object(HuLLCirqServer,'server_bind',HTTPServer.server_bind):
            directory=Path(temporary);self.assertTrue(directory.resolve().is_relative_to(qa.resolve()))
            fixture=Fixture(directory,mode)
            try:
                env=browser_environment();env['HULLCIRQ_SOFTWARE_QA_URL']=f'http://127.0.0.1:{fixture.port}/';env['HULLCIRQ_SOFTWARE_QA_MODE']=mode
                result=subprocess.run([node,'-e',BROWSER],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=65)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr+str(fixture.restart_error))
                print(result.stdout.strip())
                self.assertIsNone(fixture.restart_error);self.assertEqual(len(fixture.counter),0 if mode=='reject' else 1)
                self.assertEqual(fixture.server.store.envelope()['design'],fixture.original)
                owner=fixture.server.physical_workflow;self.assertFalse(owner.reviews)
                self.assertEqual(len(owner.runs),0 if mode=='reject' else 1)
                if owner.runs:
                    self.assertEqual(owner.runs[0]['validation_status'],'Not Checked');self.assertEqual(owner.runs[0]['review_status'],'Awaiting Review')
                self.assertEqual(len(fixture.payloads),2 if mode=='before' else 1)
                if len(fixture.payloads)==2:self.assertEqual(fixture.payloads[0],fixture.payloads[1])
            finally:fixture.stop()

    def test_before_forward_loss_reload_and_explicit_retry_create_exactly_one_job(self):self.run_case('before')
    def test_persisted_ack_loss_server_restart_and_new_session_restore_exact_job(self):self.run_case('restart')
    def test_proven_prestart_rejection_releases_matching_controller_flags(self):self.run_case('reject')

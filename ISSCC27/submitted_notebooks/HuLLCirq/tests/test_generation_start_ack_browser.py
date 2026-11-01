"""Real S04 HTTP acknowledgement loss; isolated fake provider, no model/EDA proof."""
import copy
import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from browser_qa_runtime import browser_environment
from hullcirq.domain import DomainError
from hullcirq.server import RequestHandler, make_server
from hullcirq.store import ProjectStore
from test_m2_provider import profile

PROJECT = Path(__file__).resolve().parents[1]


class GenerationAckHandler(RequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.qa_requests.append(('GET', self.path))
        super().do_GET()

    def _read_body(self):
        value = super()._read_body()
        if self.path == '/api/generation/start':
            self.server.qa_payloads.append(copy.deepcopy(value))
        return value

    def do_POST(self):
        self.server.qa_requests.append(('POST', self.path))
        if self.path == '/api/generation/start':
            if self.server.qa_mode == 'before' and not self.server.qa_drops:
                self._read_body()
                self.server.qa_drops += 1
                self.drop_connection()
                return
            if self.server.qa_mode == 'reject':
                # The real manager durably records this preflight refusal.
                with patch.object(self.server.workflow, 'is_active', return_value=True):
                    return super().do_POST()
        super().do_POST()

    def drop_connection(self):
        self.close_connection = True
        try:
            self.connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.connection.close()

    def _json(self, value, status=200, extra=None):
        if self.command == 'POST' and self.path == '/api/generation/start' and 200 <= status < 300 and not self.server.qa_drops:
            identifier = value['generation_submission']['job_id']
            worker = self.server.generation._worker
            if worker:
                worker.join(5)
                assert not worker.is_alive()
            job = self.server.generation.job(identifier)
            assert job['execution_status'] == 'Failed'
            saved = json.loads(self.server.generation.path.read_bytes())
            assert len(saved['jobs']) == 1 and saved['jobs'][0]['id'] == identifier
            self.server.qa_created_id = identifier
            self.server.qa_drops += 1
            if self.server.qa_mode == 'posterror':
                raise DomainError('software_qa_after_persist', 'SOFTWARE QA response-view failure after persistence.', 400)
            self.drop_connection()
            return
        super()._json(value, status, extra)


BROWSER = r"""
const assert=require('node:assert/strict');
const {chromium}=require(process.env.HULLCIRQ_PLAYWRIGHT_PATH||'playwright');
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});
try{const context=await browser.newContext(),page=await context.newPage();page.setDefaultTimeout(20000);
const url=process.env.HULLCIRQ_SOFTWARE_QA_URL,mode=process.env.HULLCIRQ_SOFTWARE_QA_MODE;
await context.route('**/*',route=>new URL(route.request().url()).origin===new URL(url).origin?route.continue():route.abort());
const posts=[],gets=[],errors=[];page.on('pageerror',e=>errors.push(e.message));
page.on('request',r=>{const path=new URL(r.url()).pathname;if(r.method()==='POST'&&path==='/api/generation/start')posts.push(JSON.parse(r.postData()));if(r.method()==='GET'&&['/api/project','/api/bootstrap'].includes(path))gets.push(path);});
const test=id=>page.getByTestId(id);
await page.goto(url);await test('stage-local_rtl_generation').click();
await test('context-preview-button').click();await page.waitForFunction(()=>!document.querySelector('[data-testid="generate-node"]').disabled);
await test('generate-node').click();
if(mode==='reject'){
 await page.waitForFunction(()=>!document.querySelector('[data-testid="generation-start-uncertain"]')&&document.querySelector('[data-testid="context-preview-button"]').disabled===false&&document.querySelector('[data-testid="generate-node"]').disabled===true);
 assert.equal(await test('generation-start-uncertain').count(),0);
}else{
 await test('generation-start-uncertain').waitFor();assert.equal(await test('generate-node').isDisabled(),true);assert.equal(await test('context-preview-button').isDisabled(),true);
 await test('generate-node').evaluate(el=>el.click());assert.equal(posts.length,1,'A new request cannot be sent while uncertain');
 await test('stage-graph_editor').click();await test('stage-local_rtl_generation').click();assert.equal(await test('generate-node').isDisabled(),true);
 const before=gets.length;
 if(mode==='reload'){await page.reload();await test('stage-local_rtl_generation').click();}
 else if(['before','replay','posterror'].includes(mode))await test('generation-retry-same-start').click();
 else await test('reconnect-generation').click();
 await page.waitForFunction(()=>!document.querySelector('[data-testid="generation-start-uncertain"]'));
 if(['before','replay','posterror'].includes(mode)){assert.equal(posts.length,2);assert.deepEqual(posts[0],posts[1],'Exact same nonce and frozen payload must be replayed');}
 else assert.ok(gets.length>before,'Read-only recovery must fetch saved progress');
 assert.equal(await test('generate-node').isDisabled(),true,'Recovered attempt consumes preview');
 await page.waitForFunction(()=>document.querySelector('[data-testid="generation-job-status"]')?.innerText.includes('Failed'));
 assert.equal(await test('recovery-advice').count(),1);
}
assert.equal(posts.length,['before','replay','posterror'].includes(mode)?2:1);assert.ok(posts[0].submission_id);assert.deepEqual(errors,[]);
console.log(JSON.stringify({scope:'software HTTP/browser fixture only; fake provider, no EDA/model/adoption',mode,start_posts:posts.length,same_submission_identity:true}));
}finally{await browser.close();}})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});
"""


class GenerationStartAckBrowserTests(unittest.TestCase):
    def run_case(self, mode):
        node = shutil.which('node')
        if not node:
            self.skipTest('Installed Node and Playwright are required; no packages are installed.')
        qa = PROJECT / '.work/qa'
        qa.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='s04-lost-ack-', dir=qa) as temporary:
            self.assertTrue(Path(temporary).resolve().is_relative_to(qa.resolve()))
            store = ProjectStore(Path(temporary)/'project', PROJECT/'examples/m1_two_nodes.json')
            original = copy.deepcopy(store.envelope()['design'])
            for stage in ('global_settings', 'graph_editor', 'specifications'):
                run = store.validate(stage, store.envelope()['revision']['id'])['runs'][-1]
                store.review(run['id'], 'accepted', 'SOFTWARE QA validated fixture input only.')
            server = make_server('127.0.0.1', 0, store, PROJECT)
            server.generation.save_profile(profile(context_window=16384), None)
            server.RequestHandlerClass = GenerationAckHandler
            server.qa_requests = []
            server.qa_payloads = []
            server.qa_mode = mode
            server.qa_created_id = None
            server.qa_drops = 0
            thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval':.02}, daemon=True)
            thread.start()
            answer = dict(execution_status='Failed', raw_content='SOFTWARE QA truncated answer', raw_reasoning='', finish_reason='length', usage={'completion_tokens':64}, error={'code':'output_truncated','message':'SOFTWARE QA output limit.'})
            try:
                env = browser_environment()
                env['HULLCIRQ_SOFTWARE_QA_URL'] = f'http://127.0.0.1:{server.server_address[1]}/'
                env['HULLCIRQ_SOFTWARE_QA_MODE'] = mode
                with patch('hullcirq.generation.ChatCompletionsClient') as provider:
                    provider.return_value.generate.return_value = answer
                    result = subprocess.run([node,'-e',BROWSER], cwd=PROJECT, env=env, capture_output=True, text=True, encoding='utf-8', timeout=60)
                    self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                    self.assertEqual(provider.return_value.generate.call_count, 0 if mode == 'reject' else 1)
                self.assertEqual(sum(method=='POST' and path=='/api/generation/start' for method,path in server.qa_requests), 2 if mode in ('before','replay','posterror') else 1)
                if len(server.qa_payloads) == 2:
                    self.assertEqual(server.qa_payloads[0], server.qa_payloads[1])
                jobs = server.generation.envelope()['generation']['jobs']
                self.assertEqual(len(jobs), 0 if mode=='reject' else 1)
                self.assertEqual(server.qa_drops, 0 if mode=='reject' else 1)
                self.assertFalse(server.generation.envelope()['generation']['reviews'])
                if jobs:
                    self.assertEqual(jobs[0]['submission_id'], server.qa_payloads[0]['submission_id'])
                    if mode != 'before':
                        self.assertEqual(jobs[0]['id'], server.qa_created_id)
                    self.assertEqual(jobs[0]['execution_status'], 'Failed')
                    self.assertNotEqual(jobs[0]['review_status'], 'Accepted')
                receipts = server.generation.envelope()['generation']['submissions']
                self.assertEqual(len(receipts), 1)
                if mode == 'reject':
                    self.assertEqual(next(iter(receipts.values()))['job_id'], None)
                    self.assertIsNotNone(next(iter(receipts.values()))['rejection'])
                self.assertEqual(store.envelope()['design'], original)
            finally:
                server.shutdown(); server.server_close(); server.workflow.close(); server.generation.close(); thread.join(2)

    def test_s04_persisted_terminal_start_loses_ack_and_explicit_get_never_resends(self):
        self.run_case('lost')

    def test_s04_pending_marker_survives_reload_and_bootstrap_recovers_same_job(self):
        self.run_case('reload')

    def test_s04_typed_http_refusal_creates_no_job_or_provider_call(self):
        self.run_case('reject')

    def test_s04_pre_forward_loss_explicit_same_identity_retry_creates_only_one_job(self):
        self.run_case('before')

    def test_s04_persisted_ack_loss_explicit_same_identity_retry_reuses_existing_job(self):
        self.run_case('replay')

    def test_s04_postpersist_typed_4xx_is_not_misclassified_as_prestart_rejection(self):
        self.run_case('posterror')

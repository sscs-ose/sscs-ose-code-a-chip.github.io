"""Focused API error messages; an eligibility failure is not a workspace loss."""
from pathlib import Path
import shutil
import subprocess
import unittest

PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync('src/gui/app.js','utf8').split('async function api(path, body) {')[1].split('\nfunction notify(')[0];
let response,fetcher=async()=>response;const calls=[],deadlines=[],executionFailures=[];
const status={textContent:'Local service',classList:{add(){},remove(){}}};
// Explicit execution-tracker stubs match the production API's current contract;
// they never start a workflow, model, browser or network request.
const sandbox={sessionFetch:async(...args)=>{calls.push(args);return fetcher(...args);},byId:()=>status,
  AbortSignal:{timeout:milliseconds=>{deadlines.push(milliseconds);return {software_qa_deadline:milliseconds};}},JSON,
  generation:{observeSavedProgress(){}},state:{envelope:null,design:null},reviewOperator:{request:(_path,body)=>body},executionAction:()=>null,executionScope:()=> 'software-qa-scope',syncChrome(){},executionReadFailure(){},
  executionState:{scopeKey:'software-qa-scope',receive(){},setScope(){},begin(){return null;},success(){},observeFailure(){return false;},failure:(...args)=>executionFailures.push(args)}};
vm.createContext(sandbox);vm.runInContext('async function api(path,body) {'+source+'\nglobalThis.api=api;',sandbox);
const rejected=(code,message,status=409)=>{response={ok:false,status,json:async()=>({error:{code,message}})};return sandbox.api('generation/review',{decision:'accepted'}).then(()=>assert.fail('Expected rejection'),error=>error);};
"""


class GuiApiErrorTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for focused API-client checks.')
        result = subprocess.run(
            [node, '-e', CLIENT + '\n(async()=>{\n' + body +
             '\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});'],
            cwd=PROJECT, capture_output=True, text=True, encoding='utf-8', timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unmet_behavioral_checks_do_not_claim_a_workspace_conflict(self):
        self.run_client(r"""
const error=await rejected('verification_failed','Completed interface, syntax, and original-input behavioral checks must pass before candidate acceptance.');
assert.equal(error.status,409);assert.equal(error.code,'verification_failed');
assert.match(error.message,/original-input behavioral checks/);
assert.doesNotMatch(error.message,/Open Projects|draft was preserved|reconnect/);
assert.equal(calls.length,1);
""")

    def test_only_actual_workspace_and_revision_conflicts_offer_reconnect(self):
        self.run_client(r"""
for(const code of ['workspace_session_changed','revision_conflict']) {
  const error=await rejected(code,'Saved context changed.');
  assert.match(error.message,/Your draft was preserved\. Open Projects to reconnect explicitly or export your draft\./);
  assert.equal(error.code,code);
}
for(const code of ['profile_conflict','context_conflict','job_active','job_superseded']) {
  const error=await rejected(code,'Resolve the stated operation.');
  assert.equal(error.message,'Resolve the stated operation.');assert.equal(error.code,code);
}
""")

    def test_nonconflict_errors_and_success_keep_their_original_messages(self):
        self.run_client(r"""
let error=await rejected('context_budget','Input plus output exceeds context.',422);
assert.equal(error.message,'Input plus output exceeds context.');assert.equal(error.status,422);
response={ok:false,status:409,json:async()=>({error:'Plain eligibility failure'})};
error=await sandbox.api('generation/review',{}).catch(error=>error);
assert.equal(error.message,'Plain eligibility failure');assert.equal(error.code,null);
response={ok:true,status:200,json:async()=>({message:'Saved'})};
assert.equal((await sandbox.api('project')).message,'Saved');
""")

    def test_reads_are_bounded_and_only_explicit_open_post_has_a_longer_deadline(self):
        self.run_client(r"""
response={ok:true,status:200,json:async()=>({software_qa_fixture:true})};
await sandbox.api('workspace/open',{project_id:'software-qa-project',system_id:'software-qa-system'});
assert.equal(calls[0][1].method,'POST');assert.equal(calls[0][1].signal.software_qa_deadline,300000);
for(const [route,body] of [['workspace/open',undefined],['workspace/open-directory',{directory:'SOFTWARE_QA_ONLY'}],
  ['workspace/close',{}],['workspace/local-runtime/start',{}]]) {
  await sandbox.api(route,body);assert.equal(calls.at(-1)[1].signal.software_qa_deadline,60000);
}
await sandbox.api('physical-workflow/runs',{stage:'layout'});assert.equal(calls.at(-1)[1].signal,undefined);
await sandbox.api('workspace');assert.equal(calls.at(-1)[1].signal.software_qa_deadline,60000);
for(const route of ['bootstrap','project','drc-workflow','physical-workflow','lvs-workflow']){
 await sandbox.api(route);assert.equal(calls.at(-1)[1].signal.software_qa_deadline,60000);assert.equal(calls.at(-1)[1].method,undefined);
}
assert.deepEqual(deadlines,[300000,60000,60000,60000,60000,60000,60000,60000,60000,60000,60000]);assert.equal(calls.length,12);
""")

    def test_delayed_open_success_waits_once_and_timeout_never_resends(self):
        self.run_client(r"""
let resolve;fetcher=()=>new Promise(done=>resolve=done);
const opening=sandbox.api('workspace/open',{project_id:'software-qa-project',system_id:'software-qa-system'});
assert.equal(calls.length,1);assert.equal(calls[0][1].signal.software_qa_deadline,300000);
const completed={workspace:{active:{project_id:'software-qa-project',session_id:'software-qa-new-session'}}};
resolve({ok:true,status:200,json:async()=>completed});assert.equal(await opening,completed);assert.equal(calls.length,1);
fetcher=async()=>{throw Object.assign(new Error('SOFTWARE QA timeout'),{name:'TimeoutError'});};
const error=await sandbox.api('workspace/open',{project_id:'software-qa-project',system_id:'software-qa-system'}).catch(error=>error);
assert.match(error.message,/operation may already have completed/);assert.equal(calls.length,2);
fetcher=async()=>({ok:true,status:200,json:async()=>completed});
await sandbox.api('workspace');assert.equal(calls.length,3);assert.equal(calls.at(-1)[0],'/api/workspace');
assert.equal(calls.at(-1)[1].method,undefined);assert.equal(calls.filter(([path])=>path.includes('workflow')).length,0);
""")

    def test_aborted_or_malformed_success_body_is_not_an_empty_success(self):
        self.run_client(r"""
for(const failure of [Object.assign(new Error('SOFTWARE QA aborted body'),{name:'AbortError'}),new SyntaxError('SOFTWARE QA malformed JSON')]) {
  response={ok:true,status:200,json:async()=>{throw failure;}};
  const error=await sandbox.api('workspace/open',{project_id:'software-qa-project',system_id:'software-qa-system'}).catch(error=>error);
  assert.equal(typeof error.message,'string');assert.match(error.message,/operation may already have completed/);
}
assert.equal(calls.length,2);
response={ok:false,status:502,json:async()=>{throw new SyntaxError('SOFTWARE QA non-JSON error');}};
const error=await sandbox.api('workspace/close',{}).catch(error=>error);assert.equal(error.status,502);assert.equal(error.message,'Request failed (502).');
assert.equal(calls.length,3);
""")

    def test_context_change_response_is_ignored_without_retry_or_relabeling(self):
        self.run_client(r"""
const changed=new Error('The project context changed while this request was running. Its response was ignored.');
fetcher=async()=>{throw changed;};
const error=await sandbox.api('workspace/open',{project_id:'software-qa-project',system_id:'software-qa-system'}).catch(error=>error);
assert.equal(error,changed);assert.equal(calls.length,1);assert.equal(status.textContent,'Local service');
""")

    def test_fetch_and_body_read_timeouts_never_fail_circuit_or_resend(self):
        self.run_client(r"""
const reads=[],failures=[];sandbox.executionState.observeFailure=(...args)=>{failures.push(args);return false;};
sandbox.state.design={draft:'KEEP',settings:{period:50}};const original=JSON.stringify(sandbox.state.design);
for(const phase of ['fetch','body','error-body']){
 fetcher=async()=>{const timeout=Object.assign(Error('SOFTWARE QA read expired'),{name:'TimeoutError'});
  if(phase==='fetch')throw timeout;
  return {ok:phase==='body',status:phase==='body'?200:502,json:async()=>{throw timeout;}};
 };
 const before=calls.length,error=await sandbox.api(phase==='fetch'?'drc-workflow':'project').catch(error=>error);
 assert.equal(error.code,'read_timeout');assert.equal(error.read_only,true);assert.match(error.message,/not a circuit verification failure.*No tool or model request was repeated/);
 assert.equal(calls.length,before+1);assert.equal(calls.at(-1)[1].signal.software_qa_deadline,60000);
 assert.equal(JSON.stringify(sandbox.state.design),original);assert.equal(executionFailures.length,0);assert.equal(failures.length,0);assert.equal(status.textContent,'Local service');
}
fetcher=async()=>({ok:true,status:200,json:async()=>({message:'Recovered'})});
assert.equal((await sandbox.api('project')).message,'Recovered');assert.equal(calls.length,4);
""")


    def test_same_project_new_transport_session_cannot_publish_delayed_json(self):
        self.run_client(r"""
let session='session-before-reopen';sandbox.workspaceSession=()=>session;
let release;fetcher=async()=>({ok:true,status:200,json:()=>new Promise(done=>release=done)});
const before=executionFailures.length,pending=sandbox.api('project');
await new Promise(done=>setImmediate(done));assert.equal(typeof release,'function');
session='session-after-reopen';release({design:{id:'same-project'},revision:{id:'same-revision'}});
await assert.rejects(pending,/context changed.*response was being read/);
assert.equal(calls.length,1);assert.equal(executionFailures.length,before);
""")

if __name__ == '__main__':
    unittest.main()

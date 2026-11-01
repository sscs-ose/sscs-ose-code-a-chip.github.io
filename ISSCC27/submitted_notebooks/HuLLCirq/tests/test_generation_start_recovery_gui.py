"""Scope-bound S04 transport recovery. Pure client fixtures, never model proof."""
from test_generation_recovery_gui import CLIENT, PROJECT
import shutil
import subprocess
import unittest


SETUP = CLIENT.replace(
    "const sandbox={el,",
    "const savedSession=new Map(); const storage={getItem:k=>savedSession.get(k)||null,setItem:(k,v)=>savedSession.set(k,String(v)),removeItem:k=>savedSession.delete(k)};\nconst sandbox={sessionStorage:storage,el,",
) + r"""
function ready() {
 workspace.preview={revision_id:'revision-a',profile_revision_id:'profile-a',context_id:'context-lost',estimated_input_tokens:100,prompt_text:'QA only'};
 workspace.previewStale=false;workspace.operation='generate';workspace.baseJobId=null;workspace.retryOfJobId=null;
 workspace.refreshGenerationActions();assert.equal(workspace.previewGate(),'');
}
function created(overrides={}) {return {...structuredClone(failed),...workspace.pendingStart()?.request,id:'job-accepted-once',context_id:'context-lost',operation:'generate',base_job_id:null,retry_of_job_id:null,...overrides};}
function frozen(job){return Object.fromEntries(['node_id','revision_id','context_id','profile_revision_id','operation','base_job_id','instruction','retry_of_job_id'].map(key=>[key,job[key]??({instruction:'',operation:'generate',base_job_id:null,retry_of_job_id:null})[key]]));}
function envelope(jobs) {const submissions=Object.fromEntries(jobs.filter(job=>job.submission_id).map(job=>[job.submission_id,{request:frozen(job),binding_hash:'software-fixture-only',job_id:job.id,rejection:null}]));return {...structuredClone(project.envelope),llm:structuredClone(workspace.llm),generation:{...structuredClone(workspace.generation),submissions,jobs,nodes:[{node_id:'node-a',latest_job_id:jobs.at(-1)?.id||null}]}};}
function ack(jobs,body,replayed=false){const result=envelope(jobs);result.generation_submission={version:'node-submission-v1',submission_id:body.submission_id,job_id:jobs.find(job=>job.submission_id===body.submission_id).id,replayed};return result;}
async function lose() {ready();responder=async(route)=>{assert.equal(route,'generation/start');throw new Error('Acknowledgement lost');};await workspace.startGeneration();assert.ok(workspace.pendingStart());}
"""


class GenerationStartRecoveryGuiTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated generation-start client checks.')
        result = subprocess.run(
            [node, '-e', SETUP + '\n(async()=>{\n' + body + '\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});'],
            cwd=PROJECT, capture_output=True, text=True, encoding='utf-8', timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lost_ack_after_persist_blocks_every_model_path_and_reads_one_terminal_job(self):
        self.run_client(r"""
ready();const persisted=[];
responder=async(route,body)=>{assert.equal(route,'generation/start');assert.equal(savedSession.size,1,'Recovery marker must be durable before POST');persisted.push(created());throw new Error('socket closed after persist');};
await workspace.startGeneration();assert.equal(persisted.length,1);assert.equal(test('generate-node').disabled,true);assert.equal(test('context-preview-button').disabled,true);
await workspace.startGeneration();await workspace.previewContext();assert.equal(requests.length,1);assert.equal(persisted.length,1);
assert.match(workspace.providerRequestGate(),/previous generation start/);assert.match(text(test('generation-start-uncertain')),/Refresh saved jobs/);
project.envelope.llm=workspace.llm;
for(const [file,klass] of [['generation_batch.js','GenerationBatchWorkspace'],['global_generation.js','GlobalGeneration']]){
 vm.runInContext('{'+fs.readFileSync('src/gui/'+file,'utf8').replace(/^import[^\n]+\n/gm,'').replace(/export /g,'')+'\nglobalThis.'+klass+'='+klass+';}',sandbox);
 const module=new sandbox[klass]({project:()=>project,providerGate:()=>workspace.providerRequestGate(),providerDirty:()=>false,request:callbacks.request});
 assert.match(module.gate(),/previous generation start/);await module.start();
}
assert.equal(requests.length,1,'Single, batch and S08 must not resend');
responder=async(route,body)=>{assert.equal(route,'project');assert.equal(body,undefined);return envelope(persisted);};
await test('reconnect-generation').onclick();assert.equal(requests.length,2);assert.equal(workspace.pendingStart(),undefined);assert.equal(workspace.selectedJobId,persisted[0].id);
assert.equal(workspace.preview,null);assert.equal(workspace.previewStale,true);assert.equal(test('generate-node').disabled,true);assert.equal(persisted.length,1);assert.equal(savedSession.size,0);
assert.equal(workspace.selectedJob().execution_status,'Failed');assert.equal(workspace.selectedJob().review_status,'Awaiting Review');
""")

    def test_unknown_before_persist_zero_jobs_and_failed_reads_stay_blocked_until_one_appears(self):
        self.run_client(r"""
workspace.generation.jobs=[];workspace.generation.nodes=[];workspace.selectedJobId=null;workspace.render(host);await lose();
assert.ok(test('reconnect-generation'),'No known job ID is needed for the GET control');
responder=async(route,body)=>{assert.equal(route,'project');assert.equal(body,undefined);return envelope([]);};
await workspace.reconnectStart();assert.ok(workspace.pendingStart());assert.equal(workspace.pendingStart().matchCount,0);
responder=async()=>{throw new Error('GET failed');};await workspace.reconnectStart();assert.ok(workspace.pendingStart());assert.equal(test('generate-node').disabled,true);
await workspace.startGeneration();assert.equal(requests.filter(r=>r[0]==='generation/start').length,1);
responder=async()=>envelope([created({execution_status:'Running',finished_at:null,error:null})]);await workspace.reconnectStart();
assert.equal(workspace.pendingStart(),undefined);assert.equal(workspace.selectedJob().execution_status,'Running');assert.equal(requests.filter(r=>r[0]==='generation/start').length,1);
""")

    def test_multiple_matching_new_jobs_remain_ambiguous_without_history_edits(self):
        self.run_client(r"""
await lose();const jobs=[created(),created({id:'job-second'})];const before=JSON.stringify(jobs);
responder=async()=>envelope(jobs);await workspace.reconnectStart();assert.ok(workspace.pendingStart());assert.equal(workspace.pendingStart().matchCount,2);
assert.equal(test('generate-node').disabled,true);await workspace.startGeneration();assert.equal(requests.filter(r=>r[0]==='generation/start').length,1);assert.equal(JSON.stringify(jobs),before);
""")

    def test_existing_same_context_and_other_source_fields_cannot_resolve_the_start(self):
        self.run_client(r"""
failed.context_id='context-lost';await lose();
assert.equal(workspace.observeSavedProgress(envelope([failed])),false,'An old matching-context job is not the new attempt');
for(const changed of [{node_id:'node-b'},{revision_id:'other-revision'},{profile_revision_id:'other-profile'},{context_id:'other-context'},{operation:'repair'},{base_job_id:'other-base'},{retry_of_job_id:'other-retry'}]){
 assert.equal(workspace.observeSavedProgress(envelope([created(changed)])),false);assert.ok(workspace.pendingStart());
}
const foreign=envelope([created()]);foreign.workspace_identity.project_id='other-project';assert.equal(workspace.observeSavedProgress(foreign),false);assert.ok(workspace.pendingStart());
assert.equal(workspace.observeSavedProgress(envelope([created()])),true);assert.equal(workspace.preview,null);
""")

    def test_typed_http_validation_refusals_do_not_leave_an_uncertain_start(self):
        self.run_client(r"""
for(const status of [400,401,403,404,409,413,415,422,429]){
 ready();responder=async(route,body)=>{throw Object.assign(new Error('Definite validation refusal'),{status,code:'invalid_request',generationStartRejectedBeforeCreation:true,submissionId:body.submission_id});};await workspace.startGeneration();
 assert.equal(workspace.pendingStart(),undefined);assert.equal(savedSession.size,0);assert.equal(workspace.providerRequestGate(),'');
}
assert.equal(requests.length,9);
""")

    def test_server_error_timeout_and_untyped_http_error_keep_uncertainty(self):
        self.run_client(r"""
for(const error of [Object.assign(new Error('server error'),{status:500,code:'internal_error'}),Object.assign(new Error('gateway timeout'),{status:408,code:'timeout'}),Object.assign(new Error('untyped rejection'),{status:400}),Object.assign(new Error('read aborted'),{name:'AbortError'}),new Error('body unreadable')]){
 ready();responder=async()=>{throw error;};await workspace.startGeneration();assert.ok(workspace.pendingStart());assert.equal(test('generate-node').disabled,true);
 workspace.pendingStarts.clear();workspace.persistStartRecovery();
}
assert.equal(requests.length,5);
""")

    def test_reload_reconstructs_scoped_pending_marker_without_resending(self):
        self.run_client(r"""
await lose();const reloaded=new sandbox.qa.GenerationWorkspace({...callbacks,envelope:response=>reloaded.receive(response)});
reloaded.receive({llm:workspace.llm,generation:workspace.generation});assert.ok(reloaded.pendingStart());assert.match(reloaded.generationGate(),/previous generation start/);
assert.equal(reloaded.observeSavedProgress(envelope([])),false);assert.ok(reloaded.pendingStart());
assert.equal(reloaded.observeSavedProgress(envelope([created()])),true);reloaded.receive(envelope([created()]));
assert.equal(reloaded.pendingStart(),undefined);assert.equal(reloaded.selectedJobId,'job-accepted-once');assert.equal(requests.length,1);assert.equal(savedSession.size,0);
""")

    def test_node_revision_stage_and_project_navigation_cannot_erase_pending_marker(self):
        self.run_client(r"""
await lose();const originalIdentity=structuredClone(project.envelope.workspace_identity);
workspace.selectNode('node-b');assert.ok(workspace.pendingStart());project.stage='graph_editor';workspace.receive({generation:workspace.generation});assert.ok(workspace.pendingStart());
project.envelope.revision.id='revision-new';workspace.receive({generation:workspace.generation});assert.ok(workspace.pendingStart());
project.envelope.workspace_identity={...originalIdentity,project_id:'project-b',system_id:'system-b'};workspace.receive({generation:{implemented:true,jobs:[],nodes:[]}});assert.equal(workspace.pendingStart(),undefined);
project.envelope.workspace_identity=originalIdentity;workspace.receive({generation:{implemented:true,jobs:[],nodes:[]}});assert.ok(workspace.pendingStart());assert.match(workspace.providerRequestGate(),/previous generation start/);
assert.equal(requests.length,1);
""")

    def test_late_start_and_reconnect_replies_do_not_cross_project_or_revision(self):
        self.run_client(r"""
ready();const post=deferred();responder=()=>post.promise;const started=workspace.startGeneration();const original=structuredClone(project.envelope.workspace_identity);
project.envelope.workspace_identity={...original,system_id:'system-other'};workspace.receive({generation:{implemented:true,jobs:[],nodes:[]}});post.reject(new Error('late lost ACK'));await started;
assert.equal(adopted.length,0);project.envelope.workspace_identity=original;workspace.receive({generation:{implemented:true,jobs:[],nodes:[]}});assert.ok(workspace.pendingStart());
const get=deferred();const saved=envelope([created()]);responder=()=>get.promise;const reconnect=workspace.reconnectStart();project.envelope.revision.id='revision-new';get.resolve(saved);await reconnect;
assert.ok(workspace.pendingStart());assert.equal(adopted.length,0);assert.equal(workspace.generation.jobs.length,0);
""")

    def test_acknowledged_start_and_storage_failures_preserve_truthful_request_count(self):
        self.run_client(r"""
ready();responder=async(route,body)=>ack([failed,created()],body);await workspace.startGeneration();
assert.equal(workspace.pendingStart(),undefined);assert.equal(savedSession.size,0);assert.equal(workspace.selectedJobId,'job-accepted-once');assert.equal(requests.length,1);
ready();storage.setItem=()=>{throw new Error('Storage quota');};await workspace.startGeneration();assert.equal(requests.length,1,'No POST may be sent without durable recovery state');assert.match(workspace.providerRequestGate(),/could not retain/);
""")

    def test_batch_uncertain_start_also_blocks_single_and_integration_requests(self):
        self.run_client(r"""
for(const field of ['startUncertain','analysisStartUncertain']){
 workspace.callbacks.batch=()=>({[field]:true,activeBatch:()=>null,refresh:()=>{}});assert.match(workspace.providerRequestGate(),/batch|analysis/i);
 await workspace.startGeneration();await workspace.previewContext();assert.equal(requests.length,0);
}
""")

    def test_app_observes_only_successful_full_saved_gets(self):
        self.run_client(r"""
await lose();let received=0;const observe=workspace.observeSavedProgress.bind(workspace);workspace.observeSavedProgress=value=>{received++;return observe(value);};
Object.assign(sandbox,{generation:workspace,reviewOperator:{request:(path,body)=>body},executionAction:()=>null,executionScope:()=> 'qa-scope',
 state:{envelope:project.envelope,design:project.design},executionState:{scopeKey:'qa-scope',setScope:()=>{},receive:()=>{}},
 AbortSignal,sessionFetch:async()=>({ok:true,json:async()=>envelope([created()])}),byId:()=>({textContent:'',classList:{add:()=>{},remove:()=>{}}}),executionReadFailure:()=>{},syncChrome:()=>{}});
const app=fs.readFileSync('src/gui/app.js','utf8');vm.runInContext(app.slice(app.indexOf('async function api('),app.indexOf('function executionReadFailure('))+'\nglobalThis.readApi=api;',sandbox);
await sandbox.readApi('inspection/files');assert.equal(received,0);assert.ok(workspace.pendingStart());
await sandbox.readApi('llm/profile',{profile:savedProfile});assert.equal(received,0);assert.ok(workspace.pendingStart());
await sandbox.readApi('project');assert.equal(received,1);assert.equal(workspace.pendingStart(),undefined);assert.equal(requests.length,1);
""")


    def test_recovered_old_source_candidate_remains_unadoptable(self):
        self.run_client(r"""
await lose();project.envelope.revision.id='revision-new';
const old=created({execution_status:'Completed',freshness:'Stale',rtl:'module qa_control; endmodule',checks:{interface:{validation_status:'Passed'}},stage_validation:{validation_status:'Passed'}});
const saved=envelope([old]);assert.equal(workspace.observeSavedProgress(saved),true);workspace.receive(saved);
const review=new DOMDouble('div');workspace.renderReview(review);
assert.equal(review.querySelector('[data-testid="accept-candidate"]').disabled,true);
assert.match(review.querySelector('[data-testid="accept-candidate"]').title,/stale source/);
assert.equal(workspace.selectedJob().review_status,'Awaiting Review');assert.equal(workspace.preview,null);assert.equal(requests.length,1);
""")

    def test_malformed_or_old_job_acknowledgements_cannot_unlock_the_request(self):
        self.run_client(r"""
for(const response of [{},{generation:{latest_job_id:'unknown',jobs:[]}},{generation:{latest_job_id:failed.id,jobs:[failed]}}]){
 ready();responder=async()=>response;await workspace.startGeneration();assert.ok(workspace.pendingStart());assert.equal(test('generate-node').disabled,true);
 workspace.pendingStarts.clear();workspace.persistStartRecovery();
}
assert.equal(requests.length,3);
""")

    def test_bootstrap_read_resolves_reloaded_marker_but_late_source_read_does_not(self):
        self.run_client(r"""
await lose();let observed=0;const observe=workspace.observeSavedProgress.bind(workspace);workspace.observeSavedProgress=value=>{observed++;return observe(value);};
const pending=deferred();
Object.assign(sandbox,{generation:workspace,reviewOperator:{request:(path,body)=>body},executionAction:()=>null,executionScope:()=>project.envelope.revision.id,
 state:{envelope:project.envelope,design:project.design},executionState:{scopeKey:'revision-a',setScope:()=>{},receive:()=>{}},
 AbortSignal,sessionFetch:()=>pending.promise,byId:()=>({textContent:'',classList:{add:()=>{},remove:()=>{}}}),executionReadFailure:()=>{},syncChrome:()=>{}});
const app=fs.readFileSync('src/gui/app.js','utf8');vm.runInContext(app.slice(app.indexOf('async function api('),app.indexOf('function executionReadFailure('))+'\nglobalThis.readApi=api;',sandbox);
const old=envelope([created()]);const read=sandbox.readApi('project');project.envelope.revision.id='revision-new';pending.resolve({ok:true,json:async()=>old});await read;
assert.equal(observed,0);assert.ok(workspace.pendingStart());assert.equal(workspace.previewStale,false);
sandbox.sessionFetch=async()=>({ok:true,json:async()=>envelope([created()])});await sandbox.readApi('bootstrap');
assert.equal(observed,1);assert.equal(workspace.pendingStart(),undefined);assert.equal(workspace.preview,null);assert.equal(requests.length,1);
""")

if __name__ == '__main__':
    unittest.main()

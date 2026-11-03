"""Explicit S04 keyed replay; isolated client fixtures, no actual model or EDA."""
import shutil
import subprocess
import unittest
from test_generation_start_recovery_gui import SETUP, PROJECT


class GenerationSubmissionGuiTests(unittest.TestCase):
    def run_client(self, body):
        node=shutil.which('node')
        if not node:self.skipTest('Installed Node is required for isolated client checks.')
        result=subprocess.run([node,'-e',SETUP+'\n(async()=>{\n'+body+'\n})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});'],cwd=PROJECT,capture_output=True,text=True,encoding='utf-8',timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_zero_persist_loss_can_explicitly_retry_exact_frozen_request_once(self):
        self.run_client(r"""
await lose();const original=structuredClone(requests[0][1]);assert.ok(original.submission_id);responder=async()=>envelope([]);
await workspace.reconnectStart();assert.ok(workspace.pendingStart());assert.equal(test('generation-retry-same-start').disabled,false);
workspace.instruction='Unsent future instruction';let workers=0;
responder=async(route,body)=>{assert.equal(route,'generation/start');assert.deepEqual(body,original);workers++;return ack([created()],body);};
await test('generation-retry-same-start').onclick();assert.equal(workers,1);assert.equal(workspace.pendingStart(),undefined);assert.equal(workspace.preview,null);
assert.equal(workspace.instruction,'Unsent future instruction');assert.equal(requests.filter(row=>row[0]==='generation/start').length,2);
""")

    def test_persisted_ack_loss_reuses_nonce_and_returns_same_job(self):
        self.run_client(r"""
ready();const saved=new Map();let workers=0;
responder=async(route,body)=>{workers++;saved.set(body.submission_id,created());throw new Error('ACK dropped after persisted job');};await workspace.startGeneration();
const original=structuredClone(requests[0][1]);
responder=async(route,body)=>{assert.deepEqual(body,original);assert.ok(saved.has(body.submission_id));return ack([saved.get(body.submission_id)],body,true);};
await workspace.retrySameStart();assert.equal(workers,1);assert.equal(saved.size,1);assert.equal(workspace.selectedJobId,'job-accepted-once');assert.equal(workspace.pendingStart(),undefined);assert.match(notices.join(' '),/No second job/);
""")

    def test_postpersist_typed_http_error_without_server_proof_stays_uncertain(self):
        self.run_client(r"""
ready();let job;responder=async()=>{job=created();throw Object.assign(new Error('View failed after job persisted'),{status:400,code:'invalid_generation_batch_store'});};await workspace.startGeneration();
assert.ok(workspace.pendingStart());assert.equal(test('generate-node').disabled,true);
responder=async(route,body)=>ack([job],body,true);await workspace.retrySameStart();assert.equal(workspace.pendingStart(),undefined);assert.equal(workspace.generation.jobs.length,1);
""")

    def test_exact_submission_job_is_selected_even_when_global_latest_is_other(self):
        self.run_client(r"""
ready();responder=async(route,body)=>{const own=created({execution_status:'Queued',finished_at:null,error:null}),other=created({id:'job-other',node_id:'node-b',submission_id:'other-key',context_id:'other-context'});const result=ack([own,other],body);result.generation.latest_job_id=other.id;result.generation.nodes=[{node_id:'node-a',latest_job_id:own.id},{node_id:'node-b',latest_job_id:other.id}];return result;};
await workspace.startGeneration();assert.equal(workspace.selectedJobId,'job-accepted-once');assert.equal(workspace.submittedRequest.jobId,'job-accepted-once');assert.equal(workspace.pendingStart(),undefined);
""")

    def test_wrong_nonce_or_frozen_payload_receipt_cannot_release_pending(self):
        self.run_client(r"""
for(const mutation of ['nonce','context','job']){
 ready();responder=async(route,body)=>{const result=ack([created()],body);if(mutation==='nonce')result.generation_submission.submission_id='wrong';if(mutation==='context')result.generation.jobs[0].context_id='wrong';if(mutation==='job')result.generation_submission.job_id='wrong';return result;};
 await workspace.startGeneration();assert.ok(workspace.pendingStart());assert.equal(test('generate-node').disabled,true);workspace.pendingStarts.clear();workspace.persistStartRecovery();
}
""")

    def test_saved_rejection_receipt_is_bound_to_nonce_and_frozen_payload(self):
        self.run_client(r"""
await lose();const pending=workspace.pendingStart();const result=envelope([]);const request=frozen(pending.request);
result.generation.submissions[pending.submissionId]={request:{...request,instruction:'wrong'},binding_hash:'fixture',job_id:null,rejection:{code:'workflow_busy',message:'QA refusal',status:409}};
assert.equal(workspace.observeSavedProgress(result),false);assert.ok(workspace.pendingStart());
result.generation.submissions[pending.submissionId].request=request;assert.equal(workspace.observeSavedProgress(result),true);assert.equal(workspace.pendingStart(),undefined);assert.equal(workspace.preview,null);assert.equal(workspace.generation.jobs.length,1,'Existing old result was not mutated or adopted');
""")

    def test_wrong_identity_rejection_proof_cannot_clear_another_attempt(self):
        self.run_client(r"""
ready();responder=async()=>{throw Object.assign(new Error('Wrong proof identity'),{status:409,code:'invalid_request',generationStartRejectedBeforeCreation:true,submissionId:'wrong'});};await workspace.startGeneration();assert.ok(workspace.pendingStart());assert.equal(test('generate-node').disabled,true);
""")

    def test_reload_retains_exact_payload_for_safe_replay(self):
        self.run_client(r"""
await lose();const original=structuredClone(requests[0][1]);const reloaded=new sandbox.qa.GenerationWorkspace({...callbacks,envelope:response=>reloaded.receive(response)});
reloaded.receive({llm:workspace.llm,generation:workspace.generation});reloaded.instruction='different browser draft';
responder=async(route,body)=>{assert.deepEqual(body,original);return ack([created()],body);};await reloaded.retrySameStart();assert.equal(reloaded.pendingStart(),undefined);assert.equal(reloaded.selectedJobId,'job-accepted-once');assert.equal(reloaded.instruction,'different browser draft');
""")

    def test_old_loaded_backend_cannot_ignore_new_client_nonce(self):
        self.run_client(r"""
workspace.generation.submission_protocol_version=undefined;workspace.refreshGenerationActions();assert.match(workspace.providerRequestGate(),/Restart the local workspace service/);
await workspace.startGeneration();await workspace.previewContext();assert.equal(requests.length,0);assert.equal(test('generate-node').disabled,true);
""")

    def test_legacy_unkeyed_pending_attempt_is_inspectable_but_never_replayed(self):
        self.run_client(r"""
await lose();const pending=workspace.pendingStart();delete pending.submissionId;delete pending.request;workspace.persistStartRecovery();workspace.refreshStatus();
assert.match(workspace.retryStartGate(),/unkeyed/);assert.equal(test('generation-retry-same-start').disabled,true);await workspace.retrySameStart();assert.equal(requests.length,1);
""")

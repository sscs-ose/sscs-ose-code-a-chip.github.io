"""S05 batch-client orchestration with isolated software fixtures; no model/EDA calls."""
from pathlib import Path
import shutil
import subprocess
import unittest

from test_generation_recovery_gui import CLIENT

PROJECT = Path(__file__).resolve().parents[1]
SETUP = r"""
const localSource=fs.readFileSync('src/gui/workflow.js','utf8').replace(/^import[^\n]+\n/gm,'').replace('export class LocalWorkflow','class LocalWorkflow');
vm.runInContext('{'+localSource+'\nglobalThis.LocalWorkflow=LocalWorkflow;}',sandbox);
project.stage='local_synthesis';project.design.project={name:'Isolated S05 QA'};
project.envelope.workflow.push({id:'local_synthesis',implemented:true},{id:'local_netlist_simulation',implemented:true});
const candidates=project.design.nodes.map((node,i)=>({...failed,id:'candidate-'+i,node_id:node.id,execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',finished_at:'2026-10-14T00:00:00Z',rtl:'module qa; endmodule',rtl_sha256:'rtl-'+i,input_hash:'input-'+i,error:null}));
project.envelope.generation={jobs:candidates,nodes:candidates.map(job=>({node_id:job.node_id,accepted_job_id:job.id,latest_job_id:job.id}))};
const passed={id:'synthesis-a',node_id:'node-a',stage_id:'local_synthesis',candidate_id:candidates[0].id,execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',finished_at:'2026-10-14T01:00:00Z',netlist:'saved netlist',netlist_sha256:'netlist-a',checks:{},diagnostics:[]};
const failedRun={...passed,id:'synthesis-b',node_id:'node-b',candidate_id:candidates[1].id,validation_status:'Failed',review_status:'Awaiting Review',netlist:null,checks:{executed:true,exit_code:1,stdout:'',stderr:'ERROR: candidate.v:54: unsupported syntax'}};
const batch={id:'batch-a',request_id:'request-a',execution_status:'Completed',validation_status:'Failed',items:[{node_id:'node-a',candidate_id:candidates[0].id,run_id:passed.id,status:'Skipped',reason:'Current accepted result'},{node_id:'node-b',candidate_id:candidates[1].id,run_id:failedRun.id,status:'Failed',reason:'Synthesis failed'}]};
const envelopes=[];
const local=new sandbox.LocalWorkflow({project:()=>project,request:(...args)=>{requests.push(args);return responder(...args);},envelope:response=>{envelopes.push(response);project.envelope={...project.envelope,...response};local.receive(project.envelope);},toast:message=>notices.push(message),notify:message=>notices.push(message),navigate:(...args)=>notices.push(args)});
const makeEnvelope=(batches=[],runs=[passed])=>({...project.envelope,workflow_batches:batches,workflow_runs:runs,workflow_reviews:[],workflow_nodes:[]});
local.receive(makeEnvelope());const localHost=new DOMDouble('div');local.render(localHost);
const localTest=id=>localHost.querySelector(`[data-testid="${id}"]`);
"""


class S05BatchGuiTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for focused client checks.")
        result = subprocess.run([node, "-e", CLIENT + SETUP + "\n(async()=>{\n" + body +
                                 "\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});"],
                                cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_default_all_node_action_and_selected_node_debug_remain_distinct(self):
        self.client(r"""
assert.equal(localTest('workflow-batch-run').text,'Run synthesis for all nodes');
assert.equal(localTest('workflow-run').text,'Run synthesis for selected node');
assert.match(text(localTest('workflow-batch-status')),/1\/2 nodes adopted/);
assert.match(text(localTest('workflow-batch-gate')),/Accepted current results are skipped.*S06 is not run/);
project.envelope.generation.nodes[1].accepted_job_id=null;local.refresh();
assert.equal(localTest('workflow-batch-run').disabled,false);assert.match(text(localTest('workflow-batch-node-node-b')),/Not run.*Prerequisites missing.*S04 RTL/);
assert.equal(local.synthesisSummary().blocked,1);assert.equal(requests.length,0);
""")

    def test_batch_completed_with_node_failure_is_not_reported_as_all_pass(self):
        self.client(r"""
local.receive(makeEnvelope([batch],[passed,failedRun]));
assert.match(text(localTest('workflow-batch-status')),/Batch finished · inspect unresolved nodes.*1\/2 nodes adopted.*Failed/);
assert.match(text(localTest('workflow-batch-node-node-a')),/Complete.*Complete/);
assert.match(text(localTest('workflow-batch-node-node-b')),/Failed.*Synthesis failed/);
assert.equal(local.synthesisSummary().failed,1);assert.equal(local.synthesisSummary().firstFailed.id,'node-b');
assert.equal(localTest('workflow-batch-run').disabled,false);
""")

    def test_old_pass_and_stale_or_unaccepted_netlists_are_not_counted(self):
        self.client(r"""
for(const change of [{validation_status:'Failed'},{execution_status:'Failed'},{review_status:'Awaiting Review'},{freshness:'Stale'},{netlist:null},{candidate_id:'other-candidate'}]) {
 local.runs=[passed,{...passed,id:'newer',...change}];
 assert.equal(local.synthesisProgress().accepted,change.candidate_id?1:0);
}
project.envelope.generation.nodes[0].latest_job_id='newer-rtl';local.runs=[passed];assert.equal(local.synthesisProgress().accepted,0);
""")

    def test_per_node_inspect_selects_exact_run_and_updates_selected_node(self):
        self.client(r"""
local.receive(makeEnvelope([batch],[passed,failedRun]));
localTest('workflow-batch-inspect-node-b').onclick();
assert.equal(local.nodeId,'node-b');assert.equal(local.runId,failedRun.id);assert.equal(local.selected().id,failedRun.id);
assert.equal(localTest('workflow-node').value,'node-b');assert.match(text(localTest('workflow-result')),/synthesis-b/);
assert.equal(requests.length,0);
""")

    def test_explicit_start_sends_only_saved_revision_and_idempotency_key(self):
        self.client(r"""
const before=JSON.stringify([candidates,passed]);
responder=async(route,body)=>{assert.equal(route,'workflow/batches/start');assert.equal(body.revision_id,'revision-a');assert.equal(typeof body.request_id,'string');assert.ok(body.request_id.length>10);assert.deepEqual(Object.keys(body).sort(),['request_id','revision_id']);return makeEnvelope([{...batch,id:'batch-new',request_id:body.request_id,execution_status:'Running',validation_status:'Not Checked'}]);};
await local.startBatch();assert.equal(requests.length,1);assert.equal(local.batchId,'batch-new');assert.equal(local.activeBatch().id,'batch-new');assert.equal(localTest('workflow-batch-run').disabled,true);assert.equal(localTest('workflow-run').disabled,true);assert.ok(localTest('workflow-batch-cancel'));
assert.equal(JSON.stringify([candidates,passed]),before);await local.startBatch();assert.equal(requests.length,1);
""")

    def test_batch_poll_keeps_progress_alive_between_child_runs_and_refreshes_adoption(self):
        self.client(r"""
local.receive(makeEnvelope([{...batch,execution_status:'Running',validation_status:'Not Checked',items:[batch.items[0],{...batch.items[1],run_id:null,status:'Queued'}]}],[passed]));
assert.equal(local.runs.some(run=>run.execution_status==='Running'),false);assert.ok(local.pollTimer);
const adoptedB={...failedRun,validation_status:'Passed',review_status:'Accepted',netlist:'saved B netlist'};
responder=async route=>{if(route==='workflow/batches/batch-a')return {...batch,validation_status:'Passed',items:[batch.items[0],{...batch.items[1],status:'Passed'}]};assert.equal(route,'project');return makeEnvelope([{...batch,validation_status:'Passed'}],[passed,adoptedB]);};
await local.poll();assert.deepEqual(requests.map(item=>item[0]),['workflow/batches/batch-a','project']);
assert.equal(local.synthesisProgress().accepted,2);assert.equal(local.activeBatch(),undefined);assert.match(text(localTest('workflow-batch-status')),/2\/2 nodes adopted/);
""")

    def test_lost_start_response_reconnects_without_resending_or_losing_request_identity(self):
        self.client(r"""
let requestId;responder=async(route,body)=>{assert.equal(route,'workflow/batches/start');requestId=body.request_id;throw Error('Connection lost');};
await local.startBatch();assert.equal(local.batchStartUncertain,true);assert.equal(localTest('workflow-batch-run').disabled,true);assert.ok(localTest('workflow-batch-reconnect'));await local.startBatch();assert.equal(requests.length,1);
responder=async route=>{assert.equal(route,'project');return makeEnvelope([{...batch,request_id:requestId,execution_status:'Running'}]);};
await local.reconnectBatch();assert.deepEqual(requests.map(item=>item[0]),['workflow/batches/start','project']);assert.equal(local.batchStartUncertain,false);assert.equal(local.batchId,batch.id);assert.equal(local.batchPollError,null);assert.equal(local.batchRequestId,null);
""")

    def test_explicit_retry_after_no_saved_batch_reuses_same_idempotency_key(self):
        self.client(r"""
let requestId;responder=async(route,body)=>{requestId=body.request_id;throw Error('Connection lost');};await local.startBatch();
responder=async route=>{assert.equal(route,'project');return makeEnvelope([]);};await local.reconnectBatch();assert.equal(local.batchRequestId,requestId);assert.equal(local.batchGate(),'');
responder=async(route,body)=>{assert.equal(route,'workflow/batches/start');assert.equal(body.request_id,requestId);return makeEnvelope([{...batch,request_id:requestId}],[passed,failedRun]);};await local.startBatch();assert.equal(requests.length,3);
""")

    def test_poll_error_and_cancel_preserve_child_records_and_never_start_again(self):
        self.client(r"""
const running={...batch,execution_status:'Running'};local.receive(makeEnvelope([running],[passed,failedRun]));const before=JSON.stringify([passed,failedRun]);
responder=async route=>{assert.equal(route,'workflow/batches/batch-a');throw Error('offline');};await local.poll();assert.match(local.batchPollError,/not resent/);assert.ok(localTest('workflow-batch-reconnect'));
responder=async(route,body)=>{assert.equal(route,'workflow/batches/batch-a/cancel');assert.equal(Object.keys(body).length,0);return makeEnvelope([{...batch,execution_status:'Cancelled'}],[passed,failedRun]);};await local.cancelBatch();
assert.deepEqual(requests.map(item=>item[0]),['workflow/batches/batch-a','workflow/batches/batch-a/cancel']);assert.equal(JSON.stringify([passed,failedRun]),before);assert.equal(local.activeBatch(),undefined);
""")

    def test_reloaded_client_resumes_saved_batch_observation_without_start(self):
        self.client(r"""
const fresh=new sandbox.LocalWorkflow(local.callbacks);fresh.receive(makeEnvelope([{...batch,execution_status:'Running'}]));const freshHost=new DOMDouble('div');fresh.render(freshHost);
assert.equal(fresh.activeBatch().id,batch.id);assert.ok(fresh.pollTimer);assert.equal(requests.length,0);assert.equal(freshHost.querySelector('[data-testid="workflow-batch-run"]').disabled,true);
""")

    def test_late_batch_start_poll_and_project_responses_do_not_cross_sessions(self):
        self.client(r"""
let pending=deferred();responder=()=>pending.promise;const starting=local.startBatch();project.envelope.workspace_identity.session_id='session-b';pending.resolve(makeEnvelope([batch]));await starting;assert.equal(envelopes.length,0);assert.equal(local.batches.length,0);
local.receive(makeEnvelope([{...batch,execution_status:'Running'}]));pending=deferred();responder=()=>pending.promise;const polling=local.pollBatch();project.envelope.workspace_identity.session_id='session-c';pending.resolve(batch);await polling;assert.equal(envelopes.length,0);assert.equal(local.batches[0].execution_status,'Running');
local.receive(makeEnvelope([{...batch,execution_status:'Running'}]));pending=deferred();responder=route=>route==='project'?pending.promise:Promise.resolve(batch);const pollingProject=local.pollBatch();await tick();assert.equal(requests.at(-1)[0],'project');project.envelope.workspace_identity.session_id='session-d';pending.resolve(makeEnvelope([batch]));await pollingProject;assert.equal(envelopes.length,0);
""")

    def test_dirty_readonly_storage_and_active_operations_block_batch_without_requests(self):
        self.client(r"""
responder=()=>assert.fail('Blocked batch was sent');
const reset=()=>{Object.assign(project,{dirty:false,conflict:null,busy:false,readOnly:false,postlayoutRunning:false,lvsRunning:false});project.envelope.workspace_identity.read_only=false;local.busy=false;local.storageError=null;local.batches=[];local.runs=[passed];project.envelope.generation.jobs=candidates;delete project.envelope.physical_workflow;};
for(const change of [()=>project.dirty=true,()=>project.conflict='changed',()=>project.readOnly=true,()=>project.envelope.workspace_identity.read_only=true,()=>project.busy=true,()=>local.busy=true,()=>project.postlayoutRunning=true,()=>local.storageError={message:'disk'},()=>local.batches=[{...batch,execution_status:'Running'}],()=>local.runs=[{...passed,execution_status:'Queued'}],()=>project.envelope.generation.jobs=[...candidates,{execution_status:'Running'}],()=>project.envelope.physical_workflow={runs:[{execution_status:'Running'}]}]){reset();change();assert.ok(local.batchGate());await local.startBatch();}
assert.equal(requests.length,0);
""")


if __name__ == '__main__':
    unittest.main()

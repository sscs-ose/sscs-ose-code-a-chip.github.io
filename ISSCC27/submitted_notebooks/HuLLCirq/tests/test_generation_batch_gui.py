"""Sequential request UI with software fixtures only; no model or EDA execution."""
from pathlib import Path
import shutil
import subprocess
import unittest

from test_generation_recovery_gui import CLIENT

PROJECT = Path(__file__).resolve().parents[1]
SETUP = r"""
const batchSource=fs.readFileSync('src/gui/generation_batch.js','utf8').replace(/^import[^\n]+\n/gm,'').replace('export class GenerationBatchWorkspace','class GenerationBatchWorkspace');
sandbox.crypto={randomUUID:()=> 'request-software-fixture'};
vm.runInContext('{'+batchSource+'\nglobalThis.GenerationBatchWorkspace=GenerationBatchWorkspace;}',sandbox);
project.envelope.llm={profile_revision_id:'profile-a'};
const candidate={...failed,id:'candidate-a',execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',rtl:'module qa; endmodule',error:null};
project.envelope.generation={jobs:[candidate],nodes:[{node_id:'node-a',latest_job_id:candidate.id,accepted_job_id:candidate.id}]};
project.envelope.workflow_runs=[];
project.envelope.generation_batches={batches:[]};
const captured=[],navigations=[],inspected=[];
const batchUI=new sandbox.GenerationBatchWorkspace({project:()=>project,request:(...args)=>{requests.push(args);return responder(...args);},envelope:value=>{captured.push(value);project.envelope={...project.envelope,...value};batchUI.receive(project.envelope);},notify:message=>notices.push(message),toast:message=>notices.push(message),navigate:(...args)=>navigations.push(args),inspect:(...args)=>inspected.push(args)});
batchUI.receive(project.envelope);
const batchHost=new DOMDouble('div');batchUI.renderGeneration(batchHost);
const batchTest=id=>batchHost.querySelector(`[data-testid="${id}"]`);
const plan={plan_id:'plan-a',revision_id:'revision-a',profile_revision_id:'profile-a',mode:'generate',ready_to_start:true,items:[{node_id:'node-a',node_name:'Job control',operation:'generate',status:'Queued',context:{context_id:'context-a',messages:[{role:'user',content:'Original node A requirements'}]}},{node_id:'node-b',node_name:'Other node',operation:'generate',status:'Queued',context:{context_id:'context-b',messages:[{role:'user',content:'Original node B requirements'}]}}],first_request_context:{estimated_input_tokens:100, messages:[{role:'user',content:'Original node A requirements'}]},context_policy:{kind:'exact_turns_with_ledger_v1'}};
const batch={id:'batch-a',request_id:'request-software-fixture',mode:'generate',revision_id:'revision-a',profile_revision_id:'profile-a',execution_status:'Running',validation_status:'Not Checked',completed_count:0,required_node_count:2,source_current:true,items:plan.items};
const makeEnvelope=(batches=[])=>({...project.envelope,generation_batches:{batches,active_batch_id:batches.find(b=>['Queued','Running'].includes(b.execution_status))?.id,latest_batch_id:batches.at(-1)?.id}});
"""


class GenerationBatchGuiTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for focused client checks.")
        result = subprocess.run([node, "-e", CLIENT + SETUP + "\n(async()=>{\n" + body +
                                 "\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});"],
                                cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unsent_queue_names_input_reason_and_preserves_original_status(self):
        self.client(r"""
const item={...plan.items[0],status:'Blocked',reason:'Complete current request exceeds the configured context window: input 13097 + output 4096 > context 16384.',error:{code:'context_budget'}};
batchUI.plan={...plan,ready_to_start:false,items:[item]};batchUI.planSource=batchUI.sourceIdentity();
const before=JSON.stringify(batchUI.plan);batchUI.refresh();
assert.equal(batchUI.itemDisplayStatus(item),'Not run');
assert.match(text(batchTest('generation-batch-availability-node-a')),/Input required.*input 13097.*context 16384/);
assert.equal(batchUI.guidance().title,'Input required · request not sent');
assert.equal(batchTest('generation-batch-start').disabled,true);
assert.equal(JSON.stringify(batchUI.plan),before);assert.equal(item.status,'Blocked');assert.equal(requests.length,0);
""")

    def test_unimplemented_queue_has_no_retry_and_is_distinct_from_missing_prerequisite(self):
        self.client(r"""
const missing={...plan.items[0],status:'Blocked',reason:'Accepted synthesis is required.',error:{code:'accepted_synthesis_required'}};
const unsupported={...plan.items[1],status:'Blocked',reason:'The checker is not implemented for this saved specification.',error:{code:'checker_not_implemented'}};
assert.equal(batchUI.itemAvailability(missing).label,'Prerequisites missing');
assert.equal(batchUI.itemAvailability(unsupported).label,'Not implemented');
batchUI.plan={...plan,ready_to_start:false,items:[unsupported]};batchUI.planSource=batchUI.sourceIdentity();batchUI.refresh();
assert.equal(batchUI.guidance().title,'Not implemented · request not sent');
assert.equal(batchUI.guidance().primary.label,'Inspect saved requirements');
assert.equal(batchTest('generation-batch-rebuild'),null);assert.equal(batchTest('generation-batch-provider-settings'),null);
assert.match(text(batchTest('generation-batch-availability-node-b')),/Not implemented.*checker is not implemented/);
const saved={...batch,execution_status:'Completed',validation_status:'Failed',counts:{Blocked:1},items:[unsupported]};
const before=JSON.stringify(saved);batchUI.plan=null;batchUI.receive(makeEnvelope([saved]));
assert.match(text(batchTest('generation-batch-status')),/Not run: 1/);assert.doesNotMatch(text(batchTest('generation-batch-status')),/Blocked/);
assert.equal(batchTest('generation-batch-remaining'),null);assert.equal(batchUI.guidance().title,'Not implemented · requests not sent');
assert.equal(JSON.stringify(saved),before);assert.equal(requests.length,0);
""")

    def test_real_executed_failure_remains_failed_beside_unsent_item(self):
        self.client(r"""
const executed={...candidate,id:'executed-failure',execution_status:'Failed',validation_status:'Failed'};
project.envelope.generation.jobs.push(executed);
const item={...plan.items[0],status:'Blocked',job_id:executed.id,reason:'Source failed after the model request.'};
assert.equal(batchUI.itemDisplayStatus(item),'Failed');
assert.equal(batchUI.itemDisplayStatus({...item,job_id:null}),'Not run');assert.equal(item.status,'Blocked');assert.equal(requests.length,0);
""")

    def test_default_missing_selection_and_explicit_all_selection_send_nothing(self):
        self.client(r"""
assert.equal(batchUI.selected.size,1);assert.ok(batchUI.selected.has('node-b'));
assert.equal(batchTest('generation-batch-select-node-a').checked,false);
batchTest('generation-batch-select-all').onclick();assert.deepEqual([...batchUI.selected],['node-a','node-b']);
assert.equal(requests.length,0);assert.equal(batchUI.plan,null);
const ids=[];function walk(node){if(node instanceof DOMDouble){if(node['data-testid'])ids.push(node['data-testid']);for(const c of node.children)walk(c);}}walk(batchHost);
assert.equal(new Set(ids).size,ids.length,'Test IDs must be unique in the mounted S04 panel');
""")

    def test_batch_preview_retains_target_context_and_single_start_authorizes_whole_queue(self):
        self.client(r"""
batchUI.selected=new Set(['node-a','node-b']);const original=JSON.stringify(candidate);
responder=async(route,body)=>{assert.equal(route,'generation/batches/preview');assert.deepEqual(Array.from(body.node_ids),['node-a','node-b']);assert.equal(body.revision_id,'revision-a');assert.equal(body.mode,'generate');return plan;};
await batchUI.prepare();assert.equal(requests.length,1);assert.equal(batchUI.plan,plan);
assert.match(text(batchTest('generation-batch-context')),/exact_turns_with_ledger_v1/);
assert.match(text(batchTest('generation-batch-plan')),/Later exact requests.*retained conversation and ledger/);
assert.equal(batchTest('generation-batch-start').disabled,false);
responder=async(route,body)=>{assert.equal(route,'generation/batches/start');assert.deepEqual(Object.keys(body).sort(),['plan_id','request_id']);assert.equal(body.plan_id,'plan-a');return makeEnvelope([batch]);};
await batchUI.start();assert.equal(requests.length,2);assert.equal(batchUI.plan,null);assert.equal(batchUI.activeBatch().id,'batch-a');
assert.equal(batchTest('generation-batch-select-node-a').disabled,true);assert.ok(batchTest('generation-batch-cancel'));
await batchUI.start();assert.equal(requests.length,2);assert.equal(JSON.stringify(candidate),original);
""")

    def test_late_preview_start_poll_and_project_responses_cannot_cross_session(self):
        self.client(r"""
let pending=deferred();responder=()=>pending.promise;const previewing=batchUI.prepare();
project.envelope.workspace_identity.session_id='session-b';batchUI.receive(project.envelope);pending.resolve(plan);await previewing;
assert.equal(batchUI.plan,null);assert.equal(batchUI.busy,false);assert.equal(captured.length,0);
batchUI.plan=plan;batchUI.planSource=batchUI.sourceIdentity();pending=deferred();responder=()=>pending.promise;const starting=batchUI.start();
project.envelope.workspace_identity.session_id='session-c';batchUI.receive(project.envelope);pending.resolve(makeEnvelope([batch]));await starting;
assert.equal(captured.length,0);assert.equal(batchUI.batches.length,0);assert.equal(batchUI.busy,false);
batchUI.receive(makeEnvelope([batch]));pending=deferred();responder=route=>route==='project'?pending.promise:Promise.resolve({...batch,completed_count:1});const polling=batchUI.poll();await tick();
assert.equal(requests.at(-1)[0],'project');project.envelope.workspace_identity.session_id='session-d';batchUI.receive(project.envelope);pending.resolve(makeEnvelope([{...batch,execution_status:'Completed'}]));await polling;
assert.equal(captured.length,0);assert.equal(batchUI.polling,false);
""")

    def test_dirty_readonly_profile_changes_and_other_operations_block_requests(self):
        self.client(r"""
responder=()=>assert.fail('Blocked actions must not send requests');
for(const change of [()=>project.dirty=true,()=>project.conflict='changed',()=>project.envelope.workspace_identity.read_only=true,()=>project.busy=true,()=>project.envelope.workflow_runs=[{execution_status:'Running'}],()=>batchUI.callbacks.providerDirty=()=>true]) {
 project.dirty=false;project.conflict=null;project.busy=false;project.envelope.workspace_identity.read_only=false;project.envelope.workflow_runs=[];batchUI.callbacks.providerDirty=()=>false;
 change();assert.ok(batchUI.gate());await batchUI.prepare();assert.equal(requests.length,0);
}
project.envelope.workflow_runs=[];batchUI.callbacks.providerDirty=()=>false;batchUI.plan=plan;batchUI.planSource=batchUI.sourceIdentity();
project.envelope.llm.profile_revision_id='new-profile';assert.match(batchUI.startGate(),/Preview this batch/);await batchUI.start();assert.equal(requests.length,0);
""")

    def test_lost_start_response_reconnects_without_resend_and_reuses_identity(self):
        self.client(r"""
batchUI.plan=plan;batchUI.planSource=batchUI.sourceIdentity();let requestId;
responder=async(route,body)=>{requestId=body.request_id;throw Error('Response lost');};await batchUI.start();
assert.equal(batchUI.startUncertain,true);assert.ok(batchTest('generation-batch-reconnect'));await batchUI.start();assert.equal(requests.length,1);
responder=async route=>{assert.equal(route,'project');return makeEnvelope([]);};await batchUI.reconnect();assert.equal(batchUI.startUncertain,false);assert.equal(batchUI.requestId,requestId);
responder=async(route,body)=>{assert.equal(body.request_id,requestId);return makeEnvelope([batch]);};await batchUI.start();assert.equal(requests.length,3);
assert.equal(batchUI.batchId,'batch-a');assert.equal(batchUI.requestId,null);
""")

    def test_saved_batch_reconnect_consumes_preview_without_model_submission(self):
        self.client(r"""
batchUI.plan=plan;batchUI.planSource=batchUI.sourceIdentity();batchUI.startUncertain=true;batchUI.requestId=batch.request_id;
responder=async route=>{assert.equal(route,'project');return makeEnvelope([batch]);};await batchUI.reconnect();
assert.equal(requests.length,1);assert.equal(batchUI.plan,null);assert.equal(batchUI.activeBatch().id,batch.id);assert.equal(batchUI.startUncertain,false);
""")

    def test_bulk_s05_repairs_select_exact_current_failures_and_exclude_tool_setup(self):
        self.client(r"""
const candidateB={...candidate,id:'candidate-b',node_id:'node-b'};
project.envelope.generation.jobs.push(candidateB);project.envelope.generation.nodes.push({node_id:'node-b',latest_job_id:candidateB.id,accepted_job_id:candidateB.id});
const run=(id,node,candidate)=>({id,node_id:node,stage_id:'local_synthesis',candidate_id:candidate,execution_status:'Completed',validation_status:'Failed',freshness:'Current',finished_at:'saved',checks:{executed:true,stderr:'ERROR: unsupported language'}});
project.envelope.workflow_runs=[run('failed-a','node-a','candidate-a'),run('failed-b','node-b','candidate-b')];project.stage='local_synthesis';batchUI.receive(project.envelope);
const repairHost=new DOMDouble('div');batchUI.renderRepairs(repairHost);assert.equal(batchUI.repairSelected.size,2);
responder=async(route,body)=>{assert.equal(route,'generation/batches/preview');assert.equal(body.mode,'synthesis_repair');assert.deepEqual(Array.from(body.node_ids),['node-a','node-b']);return {...plan,mode:'synthesis_repair'};};
await batchUI.prepare('synthesis_repair');assert.equal(requests.length,1);assert.deepEqual(navigations,[['local_rtl_generation']]);
assert.match(batchUI.guidance().title,/prepared repair batch/);assert.equal(batchUI.guidance().primary.label,'Start repair batch');
project.envelope.workflow_runs[0].checks.executed=false;batchUI.receive(project.envelope);assert.equal(batchUI.repairSelected.has('node-a'),false);
project.envelope.generation.nodes[1].latest_job_id='newer-candidate';assert.equal(batchUI.failedSynthesis().length,1);
""")

    def test_interrupted_batch_requires_new_preview_and_never_auto_resumes(self):
        self.client(r"""
const interrupted={...batch,execution_status:'Interrupted',validation_status:'Not Checked',completed_count:1,items:[{...plan.items[0],status:'Passed',job_id:'saved-child-a'},{...plan.items[1],status:'Interrupted',reason:'Service restarted'}]};
batchUI.receive(makeEnvelope([interrupted]));assert.equal(requests.length,0);assert.equal(batchUI.activeBatch(),undefined);
assert.ok(batchTest('generation-batch-remaining'));assert.equal(batchUI.plan,null);
responder=async(route,body)=>{assert.equal(route,'generation/batches/preview');assert.equal(body.retry_batch_id,interrupted.id);assert.deepEqual(Array.from(body.node_ids),['node-b']);return {...plan,items:[plan.items[1]]};};
batchTest('generation-batch-remaining').onclick();await tick();assert.equal(requests.length,1);assert.equal(batchUI.plan.items.length,1);
batchTest('generation-batch-inspect-node-a').onclick();assert.deepEqual(inspected,[['saved-child-a','node-a']]);
""")

    def test_active_generation_batch_blocks_existing_single_generation_and_synthesis(self):
        self.client(r"""
workspace.callbacks.batch=()=>batchUI;batchUI.receive(makeEnvelope([batch]));assert.match(workspace.generationGate(),/sequential generation batch/);
const localSource=fs.readFileSync('src/gui/workflow.js','utf8').replace(/^import[^\n]+\n/gm,'').replace('export class LocalWorkflow','class LocalWorkflow');
vm.runInContext('{'+localSource+'\nglobalThis.LocalWorkflow=LocalWorkflow;}',sandbox);
project.stage='local_synthesis';project.envelope.workflow.push({id:'local_synthesis',implemented:true});
const local=new sandbox.LocalWorkflow({project:()=>project,batch:()=>batchUI});local.nodeId='node-a';
assert.match(local.batchGate(),/active operation/);assert.equal(local.blocker().kind,'active_operation');
assert.match(local.repairGate(),/active operation/);assert.equal(requests.length,0);
""")

    def test_completed_failed_batch_guides_remaining_repair_with_exact_batch_lineage(self):
        self.client(r"""
const completed={...batch,mode:'synthesis_repair',execution_status:'Completed',validation_status:'Failed',completed_count:2,counts:{Passed:1,Failed:1,Blocked:0},items:[{...plan.items[0],status:'Passed',job_id:'saved-pass'},{...plan.items[1],status:'Failed',job_id:'saved-failed-repair'}]};
batchUI.receive(makeEnvelope([completed]));assert.equal(batchUI.guidance().title,'Some RTL requests need attention');
assert.match(text(batchTest('generation-batch-status')),/2\/2 nodes processed.*Passed: 1.*Failed: 1/);
responder=async(route,body)=>{assert.equal(route,'generation/batches/preview');assert.equal(body.mode,'synthesis_repair');assert.equal(body.retry_batch_id,completed.id);assert.deepEqual(Array.from(body.node_ids),['node-b']);return {...plan,mode:'synthesis_repair',retry_of_batch_id:completed.id,items:[plan.items[1]]};};
await batchUI.guidance().primary.action();assert.equal(requests.length,1);assert.equal(batchUI.plan.retry_of_batch_id,completed.id);
assert.equal(batchUI.guidance().primary.label,'Start repair batch');
""")

    def test_completed_passed_batch_guides_synthesis_without_repair_or_auto_execution(self):
        self.client(r"""
const candidateB={...candidate,id:'candidate-b',node_id:'node-b'};
project.envelope.generation.jobs.push(candidateB);project.envelope.generation.nodes.push({node_id:'node-b',latest_job_id:candidateB.id,accepted_job_id:candidateB.id});
const completed={...batch,execution_status:'Completed',validation_status:'Passed',completed_count:2,items:plan.items.map(item=>({...item,status:'Passed'}))};
batchUI.receive(makeEnvelope([completed]));assert.equal(batchUI.guidance().primary.label,'Open Local Synthesis');
batchUI.guidance().primary.action();assert.deepEqual(navigations,[['local_synthesis']]);assert.equal(requests.length,0);
assert.match(batchUI.guidance().summary,/does not establish synthesis or circuit behavior/);
batchUI.batches[0].source_current=false;assert.equal(batchUI.guidance(),null,'Historical batch must not override current single-node guidance');
""")

    def test_s05_shared_repair_instruction_invalidates_preview_and_reaches_each_request(self):
        self.client(r"""
project.stage='local_synthesis';const repairHost=new DOMDouble('div');batchUI.plan=plan;const token=batchUI.token;batchUI.renderRepairs(repairHost);
const input=repairHost.querySelector('[data-testid="workflow-batch-repair-instruction"]');assert.equal(input.disabled,false);
input.change('Move local declarations to module scope.');assert.equal(batchUI.instruction,'Move local declarations to module scope.');assert.equal(batchUI.plan,null);assert.ok(batchUI.token>token);assert.equal(requests.length,0);
responder=async(route,body)=>{assert.equal(route,'generation/batches/preview');assert.equal(body.mode,'synthesis_repair');assert.equal(body.instruction,'Move local declarations to module scope.');return {...plan,mode:'synthesis_repair'};};
await batchUI.prepare('synthesis_repair',['node-a','node-b']);assert.equal(requests.length,1);
batchUI.receive(makeEnvelope([batch]));batchUI.renderRepairs(repairHost);assert.equal(repairHost.querySelector('[data-testid="workflow-batch-repair-instruction"]').disabled,true);
""")

    def test_unchanged_repair_warns_without_revoking_interface_pass_and_previews_fresh_generation(self):
        self.client(r"""
const base={...candidate,rtl_sha256:'same-rtl-hash'},repaired={...base,id:'repair-unchanged',operation:'repair',base_job_id:base.id};
project.envelope.generation.jobs=[base,repaired];project.envelope.generation.nodes=[{node_id:'node-a',latest_job_id:repaired.id,accepted_job_id:repaired.id}];
project.envelope.workflow_runs=[{id:'failed-s05-a',stage_id:'local_synthesis',candidate_id:base.id,validation_status:'Failed',checks:{executed:true}}];
const result={...batch,mode:'synthesis_repair',execution_status:'Completed',validation_status:'Passed',completed_count:1,required_node_count:1,items:[{node_id:'node-a',node_name:'Job control',operation:'repair',status:'Passed',job_id:repaired.id,base_job_id:base.id,source_workflow_run_id:'failed-s05-a'}]};
batchUI.receive(makeEnvelope([result]));const original=JSON.stringify(project.envelope.generation);
assert.match(text(batchTest('generation-batch-unchanged-node-a')),/RTL unchanged; prior synthesis failure not corrected/);
assert.equal(repaired.validation_status,'Passed');assert.equal(repaired.review_status,'Accepted');
assert.equal(batchUI.guidance().primary.label,'Preview fresh generation');assert.equal(batchUI.guidance().secondary.label,'Open Local Synthesis');
responder=async(route,body)=>{assert.equal(route,'generation/batches/preview');assert.equal(body.mode,'generate');assert.deepEqual(Array.from(body.node_ids),['node-a']);assert.equal('retry_batch_id' in body,false);return {...plan,mode:'generate',items:[plan.items[0]]};};
await batchUI.guidance().primary.action();assert.equal(requests.length,1);assert.equal(batchUI.plan.mode,'generate');
assert.equal(JSON.stringify(project.envelope.generation),original,'The warning does not change pass/adoption requirements or saved candidates');
""")

    def test_unchanged_repair_action_requires_current_latest_sources_and_respects_readonly_active_gates(self):
        self.client(r"""
const base={...candidate,rtl_sha256:'same-rtl-hash'},repaired={...base,id:'repair-unchanged',operation:'repair',base_job_id:base.id};
project.envelope.generation.jobs=[base,repaired];project.envelope.generation.nodes=[{node_id:'node-a',latest_job_id:repaired.id,accepted_job_id:repaired.id}];
project.envelope.workflow_runs=[{id:'failed-s05-a',stage_id:'local_synthesis',candidate_id:base.id,validation_status:'Failed',checks:{executed:true}}];
const item={node_id:'node-a',operation:'repair',status:'Passed',job_id:repaired.id,base_job_id:base.id,source_workflow_run_id:'failed-s05-a'},result={...batch,execution_status:'Completed',validation_status:'Passed',items:[item]};
batchUI.receive(makeEnvelope([result]));assert.ok(batchTest('generation-batch-fresh-unchanged'));
project.envelope.workspace_identity.read_only=true;batchUI.refresh();assert.equal(batchTest('generation-batch-fresh-unchanged').disabled,true);await batchUI.prepare('generate',['node-a'],false);assert.equal(requests.length,0);
project.envelope.workspace_identity.read_only=false;project.envelope.generation.nodes[0].latest_job_id='newer-candidate';batchUI.refresh();assert.equal(batchTest('generation-batch-fresh-unchanged'),null);assert.match(text(batchTest('generation-batch-unchanged-node-a')),/Historical unchanged RTL/);
project.envelope.generation.nodes[0].latest_job_id=repaired.id;batchUI.batches[0].source_current=false;batchUI.refresh();assert.equal(batchTest('generation-batch-fresh-unchanged'),null);assert.equal(batchUI.guidance(),null);
batchUI.batches[0].source_current=true;repaired.rtl_sha256='different';assert.equal(batchUI.unchangedRepairs(result).length,0);
repaired.rtl_sha256=base.rtl_sha256;repaired.execution_status='Running';assert.equal(batchUI.unchangedRepairs(result).length,0);
assert.equal(requests.length,0);
""")


    def test_unchecked_or_structured_environment_failures_are_not_rtl_repair_sources(self):
        self.client(r"""
for(const error of [{code:'workflow_environment_error',next_action:'retry_same_RTL'}, {code:'workflow_error'}]) {
 project.stage='local_synthesis';project.envelope.workflow_runs=[{id:'environment-failure',node_id:'node-a',stage_id:'local_synthesis',candidate_id:candidate.id,execution_status:'Failed',validation_status:'Not Checked',freshness:'Current',finished_at:'2026-10-22T00:00:00Z',error,checks:{}}];
 const before=JSON.stringify(project.envelope.workflow_runs),failures=batchUI.failedSynthesis();assert.equal(failures.length,1);assert.match(failures[0].blocked,/same saved RTL/);
 const host=new DOMDouble('div');batchUI.renderRepairs(host);assert.ok(host.querySelector('[data-testid="workflow-same-rtl-recovery"]'));
 assert.equal(host.querySelector('[data-testid="workflow-batch-repair-all"]'),null);assert.equal(host.querySelector('[data-testid="workflow-batch-repair-selected"]'),null);
 assert.equal(batchUI.guidance().title,'Retry S05 using the same saved RTL');assert.equal(requests.length,0);assert.equal(JSON.stringify(project.envelope.workflow_runs),before);
}
project.envelope.workflow_runs[0]={...project.envelope.workflow_runs[0],validation_status:'Failed',error:null,checks:{executed:true,stderr:'ERROR: real syntax failure'}};
assert.equal(batchUI.failedSynthesis()[0].blocked,'');
""")


if __name__ == "__main__":
    unittest.main()

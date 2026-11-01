"""S05 failures remain actionable after direct S04 navigation; software fixtures only."""
import unittest

from test_generation_batch_gui import GenerationBatchGuiTests
from test_s05_batch_gui import S05BatchGuiTests


CURRENT_FAILURES = r"""
const candidateB={...candidate,id:'candidate-b',node_id:'node-b'};
project.envelope.generation.jobs.push(candidateB);
project.envelope.generation.nodes.push({node_id:'node-b',latest_job_id:candidateB.id,accepted_job_id:candidateB.id});
const failRun=(id,node,candidate)=>({id,node_id:node,stage_id:'local_synthesis',candidate_id:candidate,execution_status:'Completed',validation_status:'Failed',review_status:'Awaiting Review',freshness:'Current',finished_at:'saved',checks:{executed:true,exit_code:1,stderr:'ERROR: candidate.v:54: unsupported syntax'}});
project.envelope.workflow_runs=[failRun('failed-a','node-a','candidate-a'),failRun('failed-b','node-b','candidate-b')];
const oldSuccess={...batch,execution_status:'Completed',validation_status:'Passed',completed_count:2,items:plan.items.map(item=>({...item,status:'Passed'}))};
project.envelope=makeEnvelope([oldSuccess]);batchUI.receive(project.envelope);
"""


class RepairReturnGuiTests(unittest.TestCase):
    client = GenerationBatchGuiTests.client

    def test_direct_s04_return_shows_repairs_before_old_completed_batch_and_keeps_history(self):
        self.client(CURRENT_FAILURES + r"""
const before=JSON.stringify(project.envelope);
const guide=batchUI.guidance();assert.match(guide.primary.label,/repair/i);assert.notEqual(guide.primary.label,'Open Local Synthesis');
assert.ok(batchTest('workflow-batch-repair-all'),'Direct S04 navigation must expose the S05 repair entry');
assert.equal(batchTest('workflow-batch-repair-all').disabled,false);
assert.match(text(batchTest('workflow-batch-repair-status')),/2.*failed/);
assert.ok(batchTest('generation-batch-result'),'Earlier batch evidence remains inspectable');
const ids=[];function walk(node){if(node instanceof DOMDouble){if(node['data-testid'])ids.push(node['data-testid']);for(const c of node.children)walk(c);}}walk(batchHost);
assert.equal(new Set(ids).size,ids.length,'S04 repair panel must not duplicate control IDs');
assert.equal(requests.length,0);assert.equal(JSON.stringify(project.envelope),before);
responder=async(route,body)=>{assert.equal(route,'generation/batches/preview');assert.equal(body.mode,'synthesis_repair');assert.deepEqual(Array.from(body.node_ids),['node-a','node-b']);return {...plan,mode:'synthesis_repair'};};
await guide.primary.action();assert.equal(requests.length,1);assert.equal(batchUI.guidance().primary.label,'Start repair batch');
assert.equal(batchTest('generation-batch-start').disabled,false);assert.equal(JSON.stringify(project.envelope),before);
""")

    def test_direct_repair_entry_uses_current_failures_only_and_excludes_setup_errors(self):
        self.client(CURRENT_FAILURES + r"""
project.envelope.workflow_runs[0].checks.executed=false;
batchUI.receive(project.envelope);assert.equal(batchUI.repairSelected.has('node-a'),false);
assert.equal(batchTest('workflow-batch-repair-select-node-a').disabled,true);
responder=async(route,body)=>{assert.equal(route,'generation/batches/preview');assert.equal(body.mode,'synthesis_repair');assert.deepEqual(Array.from(body.node_ids),['node-b']);return {...plan,mode:'synthesis_repair',items:[plan.items[1]]};};
await batchTest('workflow-batch-repair-all').onclick();assert.equal(requests.length,1);
batchUI.plan=null;project.envelope.generation.nodes[1].latest_job_id='newer-unaccepted-candidate';
batchUI.receive(project.envelope);assert.equal(batchUI.failedSynthesis().filter(item=>!item.blocked).length,0);
assert.notEqual(batchUI.guidance()?.primary.label,'Prepare repairs for all failed nodes');
assert.equal(requests.length,1);
""")

    def test_repair_card_reports_surviving_synthesis_problem_after_earlier_warnings(self):
        self.client(CURRENT_FAILURES + r"""
project.envelope.workflow_runs[0].checks.stderr='Warning: multiple conflicting drivers for job_done\nWarning: multiple conflicting drivers for busy\nERROR: Found 1 problems in check -assert.';
project.envelope.workflow_runs[1].checks.executed=false;batchUI.receive(project.envelope);
assert.match(batchUI.failureExcerpt(project.envelope.workflow_runs[0]),/busy/);assert.doesNotMatch(batchUI.failureExcerpt(project.envelope.workflow_runs[0]),/job_done/);
assert.match(text(batchTest('generation-synthesis-recovery')),/multiple conflicting drivers for busy/);assert.equal(requests.length,0);
""")

    def test_single_repair_draft_wins_without_losing_active_or_reconnect_precedence(self):
        self.client(CURRENT_FAILURES + r"""
assert.equal(batchUI.guidance({singleRequestPrepared:true}),null,'A visible single-node repair draft must remain the next action');
batchUI.plan={...plan,mode:'synthesis_repair'};batchUI.planSource=batchUI.sourceIdentity();
assert.equal(batchUI.guidance({singleRequestPrepared:true}).primary.label,'Start repair batch','An explicitly prepared batch remains actionable');
batchUI.plan=null;batchUI.receive(makeEnvelope([batch]));
assert.match(batchUI.guidance({singleRequestPrepared:true}).title,/running/);
batchUI.startUncertain=true;assert.match(batchUI.guidance({singleRequestPrepared:true}).primary.label,/Reconnect/);
assert.equal(requests.length,0);
""")

    def test_blocked_preview_has_budget_settings_and_rebuild_path_without_submission(self):
        self.client(r"""
const blockedPlan={...plan,mode:'synthesis_repair',ready_to_start:false,gate_reason:'Input plus output exceeds context',profile:{context_window:16384,max_output_tokens:8192},first_request_context:{estimated_input_tokens:11000},items:[{...plan.items[0],status:'Blocked',reason:'Input plus output exceeds context'}]};
responder=async route=>{assert.equal(route,'generation/batches/preview');return blockedPlan;};await batchUI.prepare('synthesis_repair',['node-a'],false);
assert.equal(requests.length,1);assert.match(notices.at(-1),/request|input|context/i);assert.match(notices.at(-1),/No model request was sent/);assert.doesNotMatch(notices.at(-1),/Batch preview ready|Preview blocked/);
assert.equal(batchTest('generation-batch-start').disabled,true);assert.equal(batchTest('generation-batch-rebuild').disabled,false);
assert.ok(batchTest('generation-batch-provider-settings'));const budget=text(batchTest('generation-batch-budget'));
assert.match(budget,/Saved base input 11,000.*8,192.*16,384/);
assert.match(budget,/Complete provider input including conversation was not recorded; rebuild the preview to calculate its limit/);
assert.doesNotMatch(budget,/maximum output|5,384/,'A base-only legacy context does not establish the complete request output ceiling');
assert.match(batchUI.guidance().primary.label,/Rebuild repair preview/);batchTest('generation-batch-provider-settings').onclick();assert.deepEqual(navigations,[['global_settings']]);
responder=async(route,body)=>{assert.equal(route,'generation/batches/preview');assert.equal(body.mode,'synthesis_repair');assert.deepEqual(Array.from(body.node_ids),['node-a']);return {...plan,mode:'synthesis_repair',items:[plan.items[0]]};};
await batchTest('generation-batch-rebuild').onclick();assert.equal(requests.length,2);assert.equal(batchTest('generation-batch-start').disabled,false);assert.equal(batchUI.guidance().primary.label,'Start repair batch');assert.match(notices.at(-1),/Batch preview ready/);
""")

    def test_direct_repair_panel_preserves_design_provider_and_active_operation_guards(self):
        self.client(CURRENT_FAILURES + r"""
responder=()=>assert.fail('Blocked recovery must not send a preview');
const reset=()=>{project.dirty=false;project.conflict=null;project.busy=false;project.envelope.workspace_identity.read_only=false;batchUI.callbacks.providerDirty=()=>false;};
for(const change of [()=>project.dirty=true,()=>project.conflict='other version',()=>project.busy=true,()=>project.envelope.workspace_identity.read_only=true,()=>batchUI.callbacks.providerDirty=()=>true]){
 reset();change();batchUI.refresh();assert.equal(batchTest('workflow-batch-repair-all').disabled,true);assert.equal(batchUI.guidance().primary.disabled,true);await batchUI.guidance().primary.action();assert.equal(requests.length,0);
}
reset();batchUI.refresh();assert.equal(batchTest('workflow-batch-repair-all').disabled,false);assert.equal(requests.length,0);
""")

    def test_new_latest_candidate_invalidates_ready_preview_before_any_start(self):
        self.client(r"""
batchUI.plan={...plan,mode:'synthesis_repair',items:[{...plan.items[0],expected_latest_job_id:candidate.id}]};batchUI.planSource=batchUI.sourceIdentity();batchUI.refresh();
assert.equal(batchTest('generation-batch-start').disabled,false);
const newer={...candidate,id:'accepted-newer'};project.envelope.generation.jobs.push(newer);project.envelope.generation.nodes[0].latest_job_id=newer.id;project.envelope.generation.nodes[0].accepted_job_id=newer.id;
batchUI.receive(project.envelope);assert.equal(batchTest('generation-batch-start').disabled,true);assert.match(batchUI.guidance().primary.label,/Rebuild/);
responder=()=>assert.fail('Stale preview must not submit a generation batch');await batchUI.start();assert.equal(requests.length,0);
""")

    def test_editing_shared_repair_instruction_disables_existing_start_immediately(self):
        self.client(CURRENT_FAILURES + r"""
batchUI.plan={...plan,mode:'synthesis_repair'};batchUI.planSource=batchUI.sourceIdentity();batchUI.refresh();
const start=batchTest('generation-batch-start');assert.equal(start.disabled,false);
batchTest('workflow-batch-repair-instruction').change('Use one driver per output register.');
assert.equal(batchUI.instruction,'Use one driver per output register.');assert.equal(batchUI.plan,null);assert.equal(start.disabled,true,'No stale enabled Start remains while the correction is being edited');
responder=()=>assert.fail('Edited instruction requires a fresh preview');await batchUI.start();assert.equal(requests.length,0);
""")

    def test_single_repair_cannot_replace_uncertain_batch_but_can_discard_unsent_preview(self):
        self.client(r"""
workspace.receive({generation:{submission_protocol_version:"node-submission-v1",implemented:true,jobs:[candidate],nodes:[{node_id:'node-a',latest_job_id:candidate.id,accepted_job_id:candidate.id}],reviews:[]}});
workspace.callbacks.batch=()=>batchUI;batchUI.plan=plan;batchUI.planSource=batchUI.sourceIdentity();batchUI.startUncertain=true;
const previous=JSON.stringify({operation:workspace.operation,base:workspace.baseJobId,instruction:workspace.instruction});
assert.equal(workspace.prepareRepair(candidate,'Keep one output driver.'),false);assert.equal(batchUI.plan,plan);
assert.equal(JSON.stringify({operation:workspace.operation,base:workspace.baseJobId,instruction:workspace.instruction}),previous);assert.match(notices.at(-1),/reconnect/);
batchUI.startUncertain=false;workspace.prepareRepair(candidate,'Keep one output driver.');
assert.equal(batchUI.plan,null);assert.equal(workspace.operation,'repair');assert.equal(workspace.baseJobId,candidate.id);assert.equal(workspace.instruction,'Keep one output driver.');assert.equal(requests.length,0);
""")

    def test_empty_manual_repair_guidance_focuses_correction_then_allows_preview(self):
        self.client(r"""
workspace.receive({generation:{submission_protocol_version:"node-submission-v1",implemented:true,jobs:[candidate],nodes:[{node_id:'node-a',latest_job_id:candidate.id,accepted_job_id:candidate.id}],reviews:[]}});
workspace.prepareRepair(candidate,'');const guide=workspace.guidance();assert.equal(guide.primary.label,'Edit required correction');assert.notEqual(guide.primary.disabled,true);
const input=host.querySelector('#generation-instruction');assert.ok(input);let focused=0,scrolled=0;input.focus=()=>focused++;input.scrollIntoView=()=>scrolled++;
guide.primary.action();assert.equal(focused,1);assert.equal(scrolled,1);assert.equal(requests.length,0);
input.change('Use one synchronous driver for busy.');assert.equal(workspace.guidance().primary.label,'Context Preview');assert.equal(workspace.guidance().primary.disabled,false);
responder=()=>assert.fail('Busy repair must not prepare or submit a request');project.busy=true;
assert.equal(workspace.guidance().primary.disabled,true);await workspace.guidance().primary.action();assert.equal(requests.length,0);
""")

    def test_current_later_accepted_candidate_resolves_older_batch_failure(self):
        self.client(r"""
const earlierFailed={...candidate,id:'older-failed',review_status:'Awaiting Review',validation_status:'Failed'};
project.envelope.generation.jobs.unshift(earlierFailed);
const completed={...batch,execution_status:'Completed',validation_status:'Failed',items:[{node_id:'node-a',status:'Failed',job_id:earlierFailed.id}]};
batchUI.receive(makeEnvelope([completed]));
assert.equal(batchUI.remaining(completed).length,0,'Accepted current RTL supersedes the earlier failed child result');
assert.equal(batchUI.guidance(),null,'Superseded history yields to the current node guide');assert.equal(requests.length,0);
assert.equal(completed.items[0].status,'Failed','The original failure record is preserved');
""")

    def test_older_failed_queue_keeps_unexecuted_nodes_but_cannot_mask_current_s05_repair(self):
        self.client(CURRENT_FAILURES + r"""
const failedChild={...candidate,id:'old-failed-child',execution_status:'Failed',validation_status:'Not Checked',review_status:'Awaiting Review',rtl:null};
project.envelope.generation.jobs.unshift(failedChild);
const failedQueue={...batch,execution_status:'Failed',validation_status:'Not Checked',items:[{node_id:'node-a',status:'Failed',job_id:failedChild.id},{node_id:'node-b',status:'Blocked',job_id:null}]};
project.envelope=makeEnvelope([failedQueue]);batchUI.receive(project.envelope);
assert.deepEqual(Array.from(batchUI.remaining(failedQueue),item=>item.node_id),['node-b'],'The never-executed node remains available to retry');
assert.match(batchUI.guidance().primary.label,/repair/i);assert.notEqual(batchUI.guidance().primary.label,'Preview remaining requests');
assert.equal(failedQueue.items[0].status,'Failed');assert.equal(failedQueue.items[1].status,'Blocked');assert.equal(requests.length,0);
""")

    def test_new_candidate_and_new_synthesis_pass_clear_old_repair_guidance(self):
        self.client(CURRENT_FAILURES + r"""
for(const state of project.envelope.generation.nodes){
 const old=project.envelope.generation.jobs.find(job=>job.id===state.latest_job_id);
 const newer={...old,id:old.id+'-repaired'};project.envelope.generation.jobs.push(newer);state.latest_job_id=newer.id;state.accepted_job_id=newer.id;
 project.envelope.workflow_runs.push({...failRun('passed-'+state.node_id,state.node_id,newer.id),validation_status:'Passed',review_status:'Accepted',netlist:'saved netlist'});
}
batchUI.receive(project.envelope);assert.equal(batchUI.failedSynthesis().length,0);
assert.equal(batchUI.guidance().primary.label,'Continue to Netlist Simulation');assert.match(batchUI.guidance().title,/S04 and S05 are complete/);assert.equal(requests.length,0);
""")


class S05RepairPreviewRouteTests(unittest.TestCase):
    client = S05BatchGuiTests.client

    def test_selected_s05_repair_routes_to_batch_preview_without_duplicate_log_instruction(self):
        self.client(r"""
const source=candidates[1];Object.assign(failedRun,{revision_id:source.revision_id,requested_revision_id:'revision-a',input_hash:source.input_hash,rtl_sha256:source.rtl_sha256});
failedRun.checks.stderr='ERROR: candidate.v:54: unsupported syntax\n'+'repeated saved tool log\n'.repeat(500);
local.receive(makeEnvelope([], [passed,failedRun]));local.nodeId='node-b';local.runId=failedRun.id;
const calls=[],queue={instruction:'',activeBatch:()=>null,prepare:async(...args)=>{calls.push(args);return true;}};
local.callbacks.batch=()=>queue;local.callbacks.prepareRepair=()=>assert.fail('S05 should prepare the bounded shared repair preview rather than duplicate the logs into a single-request instruction');
const before=JSON.stringify([source,failedRun]);assert.equal(local.repairGate(failedRun),'');
await local.prepareRepair(failedRun,'Move local declarations to module scope.');
assert.equal(calls.length,1);assert.equal(calls[0][0],'synthesis_repair');assert.deepEqual(Array.from(calls[0][1]),['node-b']);
assert.equal(queue.instruction,'Move local declarations to module scope.');assert.ok(queue.instruction.length<100);
assert.equal(requests.length,0,'Preparing this route must not invoke any real model or EDA API');assert.equal(JSON.stringify([source,failedRun]),before);
""")

    def test_selected_s05_route_keeps_read_only_guard_before_preview(self):
        self.client(r"""
const source=candidates[1];Object.assign(failedRun,{revision_id:source.revision_id,requested_revision_id:'revision-a',input_hash:source.input_hash,rtl_sha256:source.rtl_sha256});
local.receive(makeEnvelope([], [passed,failedRun]));local.nodeId='node-b';local.runId=failedRun.id;
const queue={instruction:'existing unsent note',activeBatch:()=>null,prepare:()=>assert.fail('Read-only repair must not create a preview')};
local.callbacks.batch=()=>queue;local.callbacks.prepareRepair=()=>assert.fail('Read-only repair must not create a single draft');
project.envelope.workspace_identity.read_only=true;assert.ok(local.repairGate(failedRun));await local.prepareRepair(failedRun,'new note');
assert.equal(queue.instruction,'existing unsent note');assert.equal(requests.length,0);
""")


# The imported class supplies the isolated harness only.
del GenerationBatchGuiTests
del S05BatchGuiTests


if __name__ == '__main__':
    unittest.main()

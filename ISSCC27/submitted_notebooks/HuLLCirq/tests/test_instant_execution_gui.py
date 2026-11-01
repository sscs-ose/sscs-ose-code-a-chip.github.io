"""Real API wrapper and DOM paint before deferred HTTP; no live model or EDA."""
import shutil
import subprocess
import unittest

from test_visual_navigation import CLIENT, PROJECT


HARNESS = CLIENT.replace(
    "setNavigate:callback=>{setStage=callback;}",
    "api,receiveExecution,stageVisual,guidanceContext,resolveStageGuidance,originalPaint:syncChrome,"
    "setPaint:callback=>{syncChrome=callback;},setNavigate:callback=>{setStage=callback;}")
assert HARNESS != CLIENT, "The isolated app fixture must expose the real paint/API helpers."


class InstantExecutionGuiTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node required')
        script = HARNESS + r"""
(async()=>{const qa=await initialize();
qa.state.envelope.design=structuredClone(qa.state.design);
qa.state.envelope.workflow=qa.STAGES.map(([id])=>({id,latest_run_id:`old-${id}`,
 execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',implemented:true}));
qa.generation.llm={profile:null};
qa.setPaint(()=>{qa.renderTabs();qa.renderStageStatus();});
qa.receiveExecution();
""" + body + r"""
})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});
"""
        result = subprocess.run([node, '--experimental-vm-modules', '-e', script],
                                cwd=PROJECT, capture_output=True, text=True,
                                encoding='utf-8', timeout=25)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_stage_paints_running_and_downstream_not_run_before_http(self):
        self.run_client(r"""
const routes=[['validate',{stage_id:'global_settings'}],['validate',{stage_id:'graph_editor'}],
 ['validate',{stage_id:'specifications'}],['generation/start',{node_id:'node-a'}],
 ['workflow/batches/start',{}],['workflow/batches/start',{stage_id:'local_netlist_simulation'}],
 ['implementation-specs/start',{node_id:'node-a'}],['global-generation/start',{}],
 ['global-workflow/runs',{stage:'global_synthesis'}],['global-workflow/runs',{stage:'global_netlist_simulation'}],
 ['physical-workflow/runs',{}],['drc-workflow/runs',{}],['lvs-workflow/runs',{}],['postlayout-workflow/runs',{}]];
for(let index=0;index<routes.length;index++){
 qa.executionState.reset();qa.receiveExecution();qa.state.stage=qa.STAGES[index][0];
 let resolve,wire;context.fetch=(_url,options)=>{wire=JSON.parse(options.body);
  assert.equal(elements.get('stage-status').getAttribute('data-status'),'Running','paint must precede HTTP');
  const tabs=elements.get('stage-tabs').querySelectorAll('[data-stage-id]');
  assert.match(tabs[index].textContent,/Running/);
  tabs.slice(index+1).forEach(tab=>assert.match(tab.textContent,/Not run/));
  return new Promise(done=>{resolve=done;});
 };
 const promise=qa.api(...routes[index]);
 assert.equal(elements.get('stage-status').getAttribute('data-status'),'Running');
 // Old poll/result must not replace the just-started operation.
 qa.receiveExecution();qa.renderStageStatus();
 assert.equal(elements.get('stage-status').getAttribute('data-status'),'Running');
 const current={id:`new-${index}`,stage_id:qa.state.stage,execution_status:'Completed',
  validation_status:'Failed',review_status:'Awaiting Review',freshness:'Current'};
 const route=routes[index][0],response={workflow_runs:[current]};
 if(wire.submission_id){const key=({'workflow/batches/start':'workflow_batches','global-generation/start':'global_generation','global-workflow/runs':'global_workflow','physical-workflow/runs':'physical_workflow','drc-workflow/runs':'drc_workflow','lvs-workflow/runs':'lvs_workflow','postlayout-workflow/runs':'postlayout_workflow'})[route];if(key)response[key]=key==='workflow_batches'?[current]:{[key==='global_generation'?'jobs':'runs']:[current]};}
 const reply=wire.submission_id?qa.fixtureExecutionReply(route,wire,response,{recordId:current.id}):response;
 resolve({ok:true,json:async()=>reply});await promise;
 assert.equal(elements.get('stage-status').getAttribute('data-status'),'Failed');
 const details=elements.get('stage-status').querySelector('[data-testid="stage-execution-details"]');
 assert.ok(details);assert.equal(details.tag,'details');
}
""")

    def test_failure_refresh_and_review_do_not_resend_or_hide_old_evidence(self):
        self.run_client(r"""
qa.state.stage='drc';let sent=0;
context.fetch=async()=>{sent++;throw new Error('connection lost');};
await assert.rejects(qa.api('drc-workflow/runs',{}));
assert.equal(elements.get('stage-status').getAttribute('data-status'),'Failed');
assert.equal(qa.executionState.overlay('drc').reconnectRequired,true);
assert.ok(elements.get('stage-status').textContent.includes('Completed'),'old evidence retained in details');
context.fetch=async()=>{sent++;return {ok:true,json:async()=>({drc_workflow:{runs:[{
 id:'new-drc',execution_status:'Completed',validation_status:'Passed',review_status:'Awaiting Review',freshness:'Current'}]}})};};
await qa.api('project');qa.renderStageStatus();
assert.equal(elements.get('stage-status').getAttribute('data-status'),'Review required');
assert.equal(sent,2);assert.equal(qa.executionState.overlay('lvs').status,'Not run');
""")

    def test_rejected_request_is_failed_without_claiming_an_unknown_execution(self):
        self.run_client(r"""
qa.state.stage='layout';context.fetch=async(_url,options)=>({ok:false,status:409,json:async()=>({error:{code:'source_changed',message:'Source changed',execution_start_rejected_before_creation:true,submission_id:JSON.parse(options.body).submission_id}})});
await assert.rejects(qa.api('physical-workflow/runs',{}),/Source changed/);
assert.equal(elements.get('stage-status').getAttribute('data-status'),'Failed');
assert.equal(qa.executionState.overlay('layout').reconnectRequired,false);
assert.equal(qa.executionState.overlay('drc').status,'Not run');
""")

    def test_poll_connection_loss_stays_failed_until_fresh_exact_saved_progress(self):
        self.run_client(r"""
qa.state.stage='drc';const run={id:'current-drc',execution_status:'Running',freshness:'Current'};
context.fetch=async(_url,options)=>({ok:true,json:async()=>qa.fixtureExecutionReply('drc-workflow/runs',JSON.parse(options.body),{drc_workflow:{runs:[run]}},{recordId:run.id})});
await qa.api('drc-workflow/runs',{});
qa.state.envelope.drc_workflow={runs:[run]};
assert.equal(elements.get('stage-status').getAttribute('data-status'),'Running');
context.fetch=async()=>{throw Error('status connection lost');};
await assert.rejects(qa.api('drc-workflow'));
assert.equal(elements.get('stage-status').getAttribute('data-status'),'Failed');
qa.renderStageStatus();assert.equal(elements.get('stage-status').getAttribute('data-status'),'Failed');
context.fetch=async()=>({ok:true,json:async()=>({drc_workflow:{runs:[{...run,
 execution_status:'Completed',validation_status:'Passed',review_status:'Accepted'}]}})});
await qa.api('project');qa.renderStageStatus();
assert.equal(elements.get('stage-status').getAttribute('data-status'),'Complete');
assert.equal(qa.executionState.overlay('lvs').status,'Not run');
""")

    def test_completed_single_node_does_not_complete_the_entire_stage(self):
        self.run_client(r"""
qa.state.stage='local_synthesis';Object.assign(qa.state.envelope.workflow.find(s=>s.id===qa.state.stage),{
 required_node_count:11,accepted_node_count:1});
context.fetch=async(_url,options)=>({ok:true,json:async()=>qa.fixtureExecutionReply('workflow/start',JSON.parse(options.body),{workflow_runs:[{id:'one-node',stage_id:'local_synthesis',
 node_id:'node-a',execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current'}]},{recordId:'one-node'})});
await qa.api('workflow/start',{stage_id:'local_synthesis',node_id:'node-a'});
assert.equal(elements.get('stage-status').getAttribute('data-status'),'Not run');
assert.match(elements.get('stage-status').textContent,/1\/11/);
""")

    def test_invalidated_stage_guidance_returns_to_the_actual_running_stage(self):
        self.run_client(r"""
qa.executionState.begin({kind:'execute',stageId:'local_synthesis'});
qa.state.stage='drc';const context=qa.guidanceContext();
assert.equal(context.executionUpstreamRunning.stage,'local_synthesis');
const guide=qa.resolveStageGuidance(context);
assert.equal(guide.decisionId,'execution_invalidated');
assert.equal(guide.primary.kind,'navigate');assert.equal(guide.primary.stage,'local_synthesis');
""")

    def test_unsaved_inputs_do_not_reuse_a_completed_action_overlay(self):
        self.run_client(r"""
qa.state.stage='drc';context.fetch=async(_url,options)=>({ok:true,json:async()=>qa.fixtureExecutionReply('drc-workflow/runs',JSON.parse(options.body),{drc_workflow:{runs:[{id:'saved-drc',
 execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current'}]}},{recordId:'saved-drc'})});
await qa.api('drc-workflow/runs',{});assert.equal(qa.stageVisual('drc').label,'Complete');
qa.state.design.project.name='Unsaved edit';qa.renderStageStatus();
assert.equal(elements.get('stage-status').getAttribute('data-status'),'Not run');
assert.match(elements.get('stage-status').textContent,/Unsaved/);
""")

    def test_real_chrome_paint_and_next_step_run_before_the_http_request(self):
        self.run_client(r"""
qa.connectionMonitor.receive=()=>{};qa.setPaint(qa.originalPaint);qa.state.stage='local_netlist_simulation';
context.fetch=async()=>{
 assert.equal(elements.get('stage-status').getAttribute('data-status'),'Running');
 assert.equal(elements.get('next-step').getAttribute('data-guidance-id'),'execution.submission-recovery');
 assert.match(elements.get('next-step').textContent,/Waiting for the start acknowledgement/);
 assert.equal(elements.get('next-step').querySelector('[data-testid="execution-submission-retry"]').disabled,true);
 assert.equal(elements.get('review-state').textContent,'Running');
 return {ok:false,status:400,json:async()=>({error:{message:'Isolated rejected execution'}})};
};
await assert.rejects(qa.api('workflow/batches/start',{stage_id:'local_netlist_simulation'}),/Isolated rejected execution/);
assert.equal(elements.get('stage-status').getAttribute('data-status'),'Failed');
assert.equal(elements.get('review-state').textContent,'Failed');
""")


if __name__ == '__main__':
    unittest.main()

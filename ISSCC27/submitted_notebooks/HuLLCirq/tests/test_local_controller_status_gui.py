"""I11 real shared DOM paint with isolated state; no model, network or EDA."""
import unittest

from test_visual_navigation import VisualNavigationTests
from test_s05_batch_gui import S05BatchGuiTests


SETUP = r"""
function setupLocal(id) {
 qa.state.stage=id;qa.executionState.reset();qa.executionState.setScope('isolated-i11-'+id);
 const oldBatch={id:'old-'+id,stage_id:id,request_id:'earlier-request',execution_status:'Completed',validation_status:'Passed',review_status:'Awaiting Review',freshness:'Current'};
 qa.state.envelope.workflow.find(s=>s.id===id).execution_status='Completed';
 Object.assign(qa.state.envelope.workflow.find(s=>s.id===id),{validation_status:'Passed',review_status:'Awaiting Review',accepted_node_count:9,required_node_count:11});
 qa.state.envelope.workflow_batches=[oldBatch];
 qa.localFlow.batches=[oldBatch];qa.localFlow.runs=[];qa.localFlow.busy=false;qa.localFlow.busyStage=null;qa.localFlow.polling=false;
 qa.localFlow.batchStartUncertain=false;qa.localFlow.batchPollError=null;qa.localFlow.pollError=null;
 const token=qa.executionState.begin({kind:'execute',stageId:id});
 qa.executionState.success(token,{workflow_batches:[oldBatch]});
 return token;
}
function painted(id,expected) {
 qa.state.stage=id;qa.renderTabs();qa.renderStageStatus();
 assert.equal(elements.get('stage-status').getAttribute('data-status'),expected);
 assert.equal(elements.get('stage-tabs').querySelector('[data-stage-id="'+id+'"]').querySelector('.stage-state-label').textContent,expected);
}
"""


class LocalControllerStatusGuiTests(unittest.TestCase):
    run_client = VisualNavigationTests.run_client
    batch_client = S05BatchGuiTests.client

    def test_pending_local_mutation_dominates_terminal_partial_envelope_then_releases(self):
        self.run_client(SETUP + r"""
for (const id of ['local_synthesis','local_netlist_simulation']) {
 setupLocal(id);painted(id,'Review required');
 const before=JSON.stringify(qa.state.envelope);
 qa.localFlow.busy=true;painted(id,'Running');
 assert.equal(JSON.stringify(qa.state.envelope),before);
 qa.localFlow.busy=false;painted(id,'Review required');
 qa.executionState.reset();
 Object.assign(qa.state.envelope.workflow.find(s=>s.id===id),{accepted_node_count:11,review_status:'Accepted'});
 painted(id,'Complete');
 Object.assign(qa.state.envelope.workflow.find(s=>s.id===id),{accepted_node_count:9,validation_status:'Failed',review_status:'Awaiting Review'});
 painted(id,'Failed');
}
""")

    def test_active_controller_run_or_batch_overrides_stale_terminal_snapshot_for_its_stage(self):
        self.run_client(SETUP + r"""
for (const id of ['local_synthesis','local_netlist_simulation']) {
 setupLocal(id);qa.localFlow.runs=[{id:'child',stage_id:id,execution_status:'Running'}];painted(id,'Running');
 qa.localFlow.runs=[];qa.localFlow.batches=[{id:'new-batch',stage_id:id,execution_status:'Running'}];painted(id,'Running');
 const other=id==='local_synthesis'?'local_netlist_simulation':'local_synthesis';
 qa.localFlow.busy=true;qa.localFlow.busyStage=id;
 qa.state.stage=other;qa.renderTabs();qa.renderStageStatus();
 assert.notEqual(elements.get('stage-status').getAttribute('data-status'),'Running');
 qa.localFlow.busy=false;qa.localFlow.busyStage=null;qa.localFlow.batches=[];painted(id,'Review required');
}
""")

    def test_ordinary_read_poll_does_not_start_running_or_complete_partial_results(self):
        self.run_client(SETUP + r"""
for (const id of ['local_synthesis','local_netlist_simulation']) {
 setupLocal(id);qa.localFlow.polling=true;painted(id,'Review required');
 qa.executionState.reset();qa.state.envelope.workflow.find(s=>s.id===id).review_status='Accepted';
 painted(id,'Not run');
}
""")

    def test_reconnect_uncertainty_is_not_hidden_by_controller_busy_or_old_active_run(self):
        self.run_client(SETUP + r"""
for (const id of ['local_synthesis','local_netlist_simulation']) {
 setupLocal(id);const token=qa.executionState.begin({kind:'execute',stageId:id});
 qa.executionState.failure(token,new Error('Unknown request outcome; refresh saved results.'));
 qa.localFlow.busy=true;qa.localFlow.runs=[{id:'old-child',stage_id:id,execution_status:'Running'}];
 painted(id,'Failed');
 assert.equal(qa.executionState.overlay(id).reconnectRequired,true);
}
""")

    def test_pending_new_batch_marks_old_panel_as_earlier_without_losing_record(self):
        self.batch_client(r"""
for (const id of ['local_synthesis','local_netlist_simulation']) {
 project.stage=id;const saved={...batch,stage_id:id};
 local.batches=[saved];local.batchId=saved.id;
 local.batchRequestStage=id;local.batchRequestId='new-request';local.busy=true;
 local.renderBatch();
 assert.match(text(localTest('workflow-batch-status')),/Starting.*earlier saved batch below.*Earlier · Failed/);
 assert.match(text(localTest('workflow-batch-record')),/request-a/);
 local.busy=false;local.batchRequestId=null;local.renderBatch();
 assert.match(text(localTest('workflow-batch-status')),/Batch finished · inspect unresolved nodes/);
 assert.doesNotMatch(text(localTest('workflow-batch-status')),/Earlier ·/);
}
assert.equal(requests.length,0);
""")


del VisualNavigationTests, S05BatchGuiTests


if __name__ == '__main__':
    unittest.main()

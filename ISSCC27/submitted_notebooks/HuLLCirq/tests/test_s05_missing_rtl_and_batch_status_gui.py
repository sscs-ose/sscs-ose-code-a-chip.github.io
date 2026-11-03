"""I9 finite client regressions; no real project, model, HTTP or EDA execution."""
import unittest

from test_local_workflow_scope_gui import LocalWorkflowScopeGuiTests
from test_stage_visuals import StageVisualsTests


SETUP = r"""
project.design={nodes:Array.from({length:11},(_,i)=>({id:'pe'+i,name:i===10?'PE 1,1':'Node '+i}))};
project.envelope.generation.jobs=project.design.nodes.map(n=>({...candidate,id:'candidate-'+n.id,node_id:n.id,finished_at:'saved'}));
project.envelope.generation.nodes=project.design.nodes.map(n=>({node_id:n.id,latest_job_id:'candidate-'+n.id,accepted_job_id:'candidate-'+n.id}));
flow.runs=project.design.nodes.map(n=>({...synthesis,id:'s05-'+n.id,node_id:n.id,candidate_id:'candidate-'+n.id}));
function replaceLatest(id,status='Failed',rtl=null) {
 const state=project.envelope.generation.nodes.find(n=>n.node_id===id);
 state.latest_job_id='latest-'+id;
 project.envelope.generation.jobs.push({...candidate,id:state.latest_job_id,node_id:id,execution_status:status,validation_status:'Not Checked',review_status:'Awaiting Review',finished_at:'saved',rtl,error:{code:'generation_error',message:'Actual saved generation failed.'}});
}
const guide=()=>sandbox.resolve({stage:'local_synthesis',implemented:true,nodeId:'pe0',nodeName:'Node 0',record:flow.runs[0],synthesisSummary:flow.synthesisSummary(),synthesisBatchGate:flow.batchGate()});
"""


class S05MissingRtlAndBatchStatusGuiTests(unittest.TestCase):
    client = LocalWorkflowScopeGuiTests.client
    visual_client = StageVisualsTests.run_client

    def test_ten_adopted_and_latest_pe11_generation_error_routes_to_exact_s04(self):
        self.client(SETUP + r"""
replaceLatest('pe10');
const summary=flow.synthesisSummary();
assert.equal(summary.total,11);assert.equal(summary.accepted,10);
assert.equal(summary.failed,0);assert.equal(summary.blocked,1);
assert.equal(summary.firstIncomplete.id,'pe10');
const before=JSON.stringify(project),r=guide();
assert.equal(r.decisionId,'s05_sources');assert.equal(r.primary.kind,'navigate');
assert.equal(r.primary.stage,'local_rtl_generation');assert.equal(r.primary.nodeId,'pe10');
assert.match(r.primary.label,/Open S04.*PE 1,1/);
assert.match(r.summary,/10\/11.*current accepted S04 RTL.*No remaining node is eligible/);
assert.match(r.detail,/Running synthesis again cannot create/);
assert.equal(r.secondary.kind,'inspect');assert.notEqual(r.tone,'success');
assert.doesNotMatch(r.title+' '+r.summary+' '+r.detail,/Blocked/);
assert.equal(JSON.stringify(project),before);
""")

    def test_missing_unaccepted_candidate_never_reuses_older_accepted_netlist(self):
        self.client(SETUP + r"""
for (const status of ['Failed','Interrupted','Completed']) {
 replaceLatest('pe10',status,status==='Completed'?'module incomplete;endmodule':null);
 assert.equal(flow.candidateFor('pe10'),undefined);
 assert.equal(flow.synthesisFor('pe10'),undefined);
 const r=guide();assert.equal(r.primary.stage,'local_rtl_generation');
 assert.equal(r.primary.nodeId,'pe10');assert.notEqual(r.primary.testId,'workflow-batch-run');
}
""")

    def test_mixed_eligible_and_missing_nodes_keep_useful_s05_batch(self):
        self.client(SETUP + r"""
replaceLatest('pe10');flow.runs=flow.runs.filter(r=>r.node_id!=='pe9');
const r=guide();assert.equal(flow.synthesisSummary().accepted,9);
assert.equal(r.decisionId,'s05_pending');assert.equal(r.primary.testId,'workflow-batch-run');
assert.match(r.summary,/remaining eligible nodes/);
assert.match(r.summary,/1 other node\(s\).*S04 RTL.*cannot generate/);
assert.notEqual(r.tone,'success');
""")

    def test_real_current_s05_failure_still_has_its_own_recovery(self):
        self.client(SETUP + r"""
replaceLatest('pe10');flow.runs[9].validation_status='Failed';
flow.runs[9].review_status='Awaiting Review';
const r=guide();assert.equal(r.decisionId,'s05_failed_node');
assert.equal(r.primary.stage,'local_synthesis');assert.equal(r.primary.nodeId,'pe9');
""")

    def test_s05_and_s06_active_partial_batches_dominate_old_failed_child_overlay(self):
        self.visual_client(r"""
for (const id of ['local_synthesis','local_netlist_simulation']) {
 const env={workflow:[{id,...accepted,execution_status:'Completed',validation_status:'Failed',review_status:'Awaiting Review',accepted_node_count:5,required_node_count:11}],
  workflow_batches:[{id:'active-'+id,stage_id:id,execution_status:'Running',validation_status:'Failed',freshness:'Current',items:[]}]};
 const before=JSON.stringify(env);
 for (const overlay of [{status:'Failed',detail:'An earlier child failed.'},{status:'Complete'},{status:'Not run',invalidated:true}]) {
  const r=presentation(env,id,{overlay});
  assert.equal(r.label,'Running');assert.equal(r.kind,'working');
  assert.match(r.detail,/5\/11 nodes adopted.*active operation/);
 }
 assert.equal(JSON.stringify(env),before);
}
""")

    def test_terminal_batch_restores_actual_complete_or_failed_status(self):
        self.visual_client(r"""
for (const id of ['local_synthesis','local_netlist_simulation']) {
 const env={workflow:[{id,...accepted,accepted_node_count:11,required_node_count:11}],
  workflow_batches:[{id:'done-'+id,stage_id:id,execution_status:'Completed',validation_status:'Passed',freshness:'Current'}]};
 assert.equal(presentation(env,id).label,'Complete');
 env.workflow[0].accepted_node_count=5;env.workflow[0].validation_status='Failed';
 env.workflow[0].review_status='Awaiting Review';env.workflow_batches[0].validation_status='Failed';
 const failed=presentation(env,id,{overlay:{status:'Failed',detail:'Real terminal batch failure.'}});
 assert.equal(failed.label,'Failed');assert.notEqual(failed.kind,'working');
}
""")

    def test_connection_uncertainty_and_other_stage_batches_do_not_hide_failure(self):
        self.visual_client(r"""
const env={workflow:[{id:'local_synthesis',...accepted,validation_status:'Failed',accepted_node_count:5,required_node_count:11}],
 workflow_batches:[{id:'active',stage_id:'local_synthesis',execution_status:'Running',freshness:'Current'}]};
const uncertain={status:'Failed',reconnectRequired:true,detail:'Refresh the saved execution before retrying.'};
assert.equal(presentation(env,'local_synthesis',{overlay:uncertain}).label,'Failed');
assert.match(presentation(env,'local_synthesis',{overlay:uncertain}).detail,/Refresh/);
env.workflow_batches[0].stage_id='local_netlist_simulation';
assert.equal(presentation(env,'local_synthesis',{overlay:{status:'Failed'}}).label,'Failed');
env.workflow_batches=[];
assert.equal(presentation(env,'local_synthesis',{overlay:{status:'Failed'}}).label,'Failed');
""")


# Imported only to reuse their isolated Node runners, not duplicate discovery.
del LocalWorkflowScopeGuiTests, StageVisualsTests


if __name__ == '__main__':
    unittest.main()

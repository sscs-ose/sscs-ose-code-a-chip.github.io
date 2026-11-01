"""S07 latest-adoption/navigation and mutation guards, isolated GUI fixtures only."""
import unittest

from test_s07_current_source_gui import S07CurrentSourceGuiTests


class S07NavigationGuardsGuiTests(unittest.TestCase):
    client = S07CurrentSourceGuiTests.client

    def test_new_failed_or_returned_spec_cannot_be_skipped_using_old_acceptance(self):
        self.client(r"""
for (const changes of [{validation_status:'Failed',review_status:'Awaiting Review'},{review_status:'Changes Requested'}]) {
 const latest={...spec,id:'s07-new',...changes};view.specs=[spec,latest];
 Object.assign(view.nodes[0],{latest_spec_id:latest.id,accepted_spec_id:null});
 assert.equal(view.currentRun().id,latest.id);assert.equal(view.accepted('node-a'),false);
 assert.equal(view.nextNode().id,'node-a');assert.equal(view.runCurrent(spec),false);
 view.specId=spec.id;view.renderReview(reviewHost);
 assert.equal(view.selected().id,spec.id,'Explicit history remains inspectable');
 assert.equal(reviewButton('implementation-continue').disabled,true);
 assert.equal(reviewButton('implementation-accept').disabled,true);
 assert.equal(reviewButton('implementation-request-changes').disabled,true);
}
assert.equal(requests.length,0);
""")

    def test_absent_backend_node_metadata_never_uses_local_history_as_current(self):
        self.client(r"""
delete project.envelope.implementation_spec_nodes;
assert.equal(view.currentRun(),undefined);assert.equal(view.accepted('node-a'),false);
assert.equal(view.nextNode().id,'node-a');
view.specId=spec.id;assert.equal(view.selected().id,spec.id);assert.equal(view.runCurrent(spec),false);
assert.equal(requests.length,0);
""")

    def test_backend_missing_latest_record_fails_closed_instead_of_falling_back(self):
        self.client(r"""
for (const latest_spec_id of ['missing-from-response',null]) {
 Object.assign(view.nodes[0],{latest_spec_id,accepted_spec_id:spec.id});
 assert.equal(view.currentRun(),undefined);assert.equal(view.accepted('node-a'),false);
 assert.equal(view.nextNode().id,'node-a');
}
assert.equal(requests.length,0);
""")

    def test_current_adoption_progress_uses_backend_latest_and_exact_source(self):
        self.client(r"""
assert.equal(view.accepted('node-a'),true);assert.equal(view.nextNode().id,'node-b');
project.design.nodes=project.design.nodes.filter(node=>node.id==='node-a');
assert.equal(view.nextNode(),undefined);
view.nodes[0].accepted_spec_id=null;assert.equal(view.accepted('node-a'),false);
assert.equal(view.nextNode().id,'node-a');
view.nodes[0].accepted_spec_id=spec.id;spec.source_run_id='older-s06';
assert.equal(view.accepted('node-a'),false);assert.equal(view.nextNode().id,'node-a');
assert.equal(requests.length,0);
""")

    def test_readonly_blocks_buttons_and_direct_start_or_review_without_post(self):
        self.client(r"""
(async()=>{
for (const key of ['project','workspace']) {
 project.readOnly=key==='project';project.envelope.workspace_identity.read_only=key==='workspace';
 assert.match(view.gate(),/read-only/);view.renderReview(reviewHost);
 assert.equal(reviewButton('implementation-continue').disabled,true);
 assert.equal(reviewButton('implementation-request-changes').disabled,true);
 await view.start();await view.review(spec,'changes_requested','Read-only must not mutate');
}
assert.equal(requests.length,0);
})().catch(e=>{console.error(e);process.exitCode=1});
""")

    def test_cross_operation_and_between_child_batch_gaps_block_s07_mutations(self):
        self.client(r"""
(async()=>{
const idle=structuredClone(project.envelope);
const cases=[['generation',{jobs:[{execution_status:'Running'}]}],['generation_batches',{batches:[{execution_status:'Running'}]}],
 ['workflow_runs',[{execution_status:'Queued'}]],['workflow_batches',[{execution_status:'Running'}]],
 ['repair_analysis',{active_job_id:'analysis-active'}],['repair_analysis',{jobs:[{execution_status:'Running'}]}],
 ...['global_generation','global_workflow','physical_workflow','drc_workflow','lvs_workflow','postlayout_workflow'].map(key=>[key,{runs:[{execution_status:'Running'}]}])];
for (const [key,value] of cases) {
 project.envelope=structuredClone(idle);project.envelope[key]=value;
 assert.match(view.gate(),/active|running/i,key);await view.start();
 await view.review(spec,'changes_requested','Wait for the actual operation');
}
assert.equal(requests.length,0);
})().catch(e=>{console.error(e);process.exitCode=1});
""")

    def test_readonly_refresh_still_reads_saved_evidence_without_extraction(self):
        self.client(r"""
(async()=>{
project.readOnly=true;view.refresh=()=>{};view.callbacks.envelope=()=>{};
responder=async()=>project.envelope;
await view.refreshSaved();
assert.deepEqual(requests.map(call=>call[0]),['implementation-specs/'+spec.id,'project']);
assert.ok(requests.every(call=>call[1]===undefined));
})().catch(e=>{console.error(e);process.exitCode=1});
""")

    def test_pending_request_keeps_started_node_identity_if_selection_changes(self):
        self.client(r"""
(async()=>{
let complete;responder=()=>new Promise(resolve=>{complete=resolve;});
view.refresh=()=>{};view.callbacks.envelope=value=>view.receive(value);view.callbacks.toast=message=>notices.push(message);
const pending=view.start();assert.equal(view.busy,true);assert.equal(requests[0][1].node_id,'node-a');
view.setNode('node-b');const created={...spec,id:'created-for-a'};
complete({implementation_specs:[created,{...spec,id:'failed-b',node_id:'node-b',validation_status:'Failed'}],implementation_spec_nodes:[]});
await pending;assert.equal(view.nodeId,'node-b');assert.equal(view.specId,null);
assert.match(notices.at(-1),/derived and verified/);assert.equal(requests.length,1);
})().catch(e=>{console.error(e);process.exitCode=1});
""")

    def test_direct_old_review_is_rejected_but_latest_stale_feedback_remains_available(self):
        self.client(r"""
(async()=>{
const latest={...spec,id:'latest-stale',freshness:'Stale'};view.specs.push(latest);
Object.assign(view.nodes[0],{latest_spec_id:latest.id,accepted_spec_id:null});
view.callbacks.envelope=()=>{};responder=async()=>({});
await view.review(spec,'changes_requested','Older history cannot be changed');assert.equal(requests.length,0);
await view.review(latest,'changes_requested','Record feedback without accepting stale evidence');
assert.equal(requests.length,1);assert.equal(requests[0][0],'implementation-specs/review');
assert.equal(requests[0][1].spec_id,latest.id);assert.equal(requests[0][1].decision,'changes_requested');
})().catch(e=>{console.error(e);process.exitCode=1});
""")


del S07CurrentSourceGuiTests


if __name__ == '__main__':
    unittest.main()

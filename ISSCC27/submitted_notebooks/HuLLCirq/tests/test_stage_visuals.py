"""Overview source/aggregate display regressions; fixtures never establish circuit proof."""
from pathlib import Path
import shutil
import subprocess
import unittest


PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');const sandbox={URL};vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('src/gui/visual_state.js','utf8').replace(/export /g,''),sandbox);
vm.runInContext('{'+fs.readFileSync('src/gui/stage_visuals.js','utf8').replace(/^import[^\n]+\n/gm,'').replace(/export /g,'')+'\nthis.presentation=stagePresentation;this.overview=stageOverviewFacts;}',sandbox);
const presentation=sandbox.presentation;
const accepted={execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',implemented:true};
const node={node_id:'node-a',latest_job_id:'candidate-a',accepted_job_id:'candidate-a'};
const run={id:'run-a',node_id:'node-a',candidate_id:'candidate-a',stage_id:'local_synthesis',...accepted};
const envelope={workflow:[{id:'local_rtl_generation',...accepted,accepted_node_count:2,required_node_count:2},{id:'local_synthesis',...accepted,accepted_node_count:1,required_node_count:2}],generation:{nodes:[node],jobs:[]},workflow_nodes:[{node_id:'node-a',stage_id:'local_synthesis',latest_run_id:'run-a',accepted_run_id:'run-a'}],workflow_runs:[run]};
"""


class StageVisualsTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for isolated overview checks.")
        result = subprocess.run([node, "-e", CLIENT + "\n" + body], cwd=PROJECT,
                                capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_current_failure_is_visible_even_when_last_other_node_passed(self):
        self.run_client(r"""
envelope.generation.nodes.push({node_id:'node-b',latest_job_id:'candidate-b',accepted_job_id:'candidate-b'});
envelope.workflow_nodes.push({node_id:'node-b',stage_id:'local_synthesis',latest_run_id:'run-b'});
envelope.workflow_runs.unshift({...run,id:'run-b',node_id:'node-b',candidate_id:'candidate-b',validation_status:'Failed',review_status:'Awaiting Review'});
const value=presentation(envelope,'local_synthesis');assert.equal(value.kind,'error');assert.match(value.detail,/1\/2 nodes adopted/);
""")

    def test_failure_from_previous_candidate_does_not_override_current_aggregate(self):
        self.run_client(r"""
envelope.workflow[1].accepted_node_count=2;
envelope.workflow_runs[0].candidate_id='previous-candidate';envelope.workflow_runs[0].validation_status='Failed';
assert.equal(presentation(envelope,'local_synthesis').kind,'complete');
""")

    def test_historical_s04_behavior_failure_does_not_reenter_interface_only_status(self):
        self.run_client(r"""
envelope.generation.jobs=[{id:'candidate-a',node_id:'node-a',...accepted,validation_status:'Failed',effective_validation_status:'Passed',stage_validation:{validation_status:'Passed'}}];
assert.equal(presentation(envelope,'local_rtl_generation').kind,'complete');
""")

    def test_partial_adoption_and_missing_sources_are_not_whole_stage_complete(self):
        self.run_client(r"""
assert.equal(presentation(envelope,'local_synthesis').label,'Not run');
assert.match(presentation(envelope,'local_synthesis').detail,/1\/2 nodes adopted/);
envelope.workflow[1].execution_status='Not Run';envelope.workflow[1].validation_status='Not Checked';envelope.workflow[1].review_status='Awaiting Review';envelope.workflow[1].accepted_node_count=0;
envelope.generation.nodes=[];assert.equal(presentation(envelope,'local_synthesis').label,'Not run');
""")

    def test_active_batch_overrides_old_complete_and_unsaved_inputs_do_not_complete(self):
        self.run_client(r"""
envelope.workflow[1].accepted_node_count=2;envelope.workflow_batches=[{execution_status:'Running'}];
assert.equal(presentation(envelope,'local_synthesis').kind,'working');
envelope.workflow_batches=[];assert.equal(presentation(envelope,'local_synthesis',{dirty:true}).label,'Not run');
""")

    def test_unsupported_integration_and_postlayout_are_not_shown_as_unrun_ready(self):
        self.run_client(r"""
envelope.workflow.push({id:'global_rtl_generation',execution_status:'Not Run',implemented:true},{id:'post_layout_verification',execution_status:'Not Run',implemented:true});
envelope.global_generation={ready:false,blocked_reason:'This integration checker does not support the design.'};
envelope.postlayout_workflow={verification_supported:false};
assert.equal(presentation(envelope,'global_rtl_generation').label,'Not run');
assert.equal(presentation(envelope,'post_layout_verification').label,'Not run');
""")

    def test_s07_current_failure_is_not_hidden_by_other_accepted_node(self):
        self.run_client(r"""
envelope.workflow.push({id:'node_implementation_specs',...accepted,accepted_node_count:1,required_node_count:2});
envelope.implementation_spec_nodes=[{node_id:'node-a',latest_spec_id:'spec-a',ready:true},{node_id:'node-b',latest_spec_id:'spec-b',ready:true}];
envelope.implementation_specs=[{id:'spec-a',node_id:'node-a',...accepted,validation_status:'Failed'},{id:'spec-b',node_id:'node-b',...accepted}];
assert.equal(presentation(envelope,'node_implementation_specs').kind,'error');
envelope.implementation_specs[0].freshness='Stale';assert.notEqual(presentation(envelope,'node_implementation_specs').kind,'error');
""")

    def test_s14_support_barrier_overrides_an_old_accepted_aggregate(self):
        self.run_client(r"""
envelope.workflow.push({id:'post_layout_verification',...accepted});
envelope.postlayout_workflow={verification_supported:false};
assert.equal(presentation(envelope,'post_layout_verification').label,'Failed');
""")

    def test_s06_batch_running_is_not_assigned_to_s05(self):
        self.run_client(r"""
envelope.workflow[1].accepted_node_count=2;
envelope.workflow.push({id:'local_netlist_simulation',execution_status:'Not Run',validation_status:'Not Checked',review_status:'Awaiting Review',freshness:'Current',implemented:true});
envelope.workflow_batches=[{stage_id:'local_netlist_simulation',execution_status:'Running',freshness:'Current'}];
assert.equal(presentation(envelope,'local_netlist_simulation').label,'Running');
assert.equal(presentation(envelope,'local_synthesis').label,'Complete');
envelope.workflow_batches[0].execution_status='Queued';
assert.equal(presentation(envelope,'local_netlist_simulation').label,'Running');
""")

    def test_all_fourteen_stages_use_the_same_five_states_and_click_overlay(self):
        self.run_client(r"""
const ids=['global_settings','graph_editor','specifications','local_rtl_generation','local_synthesis','local_netlist_simulation','node_implementation_specs','global_rtl_generation','global_synthesis','global_netlist_simulation','layout','drc','lvs','post_layout_verification'];
const untouched={workflow:ids.map(id=>({id,execution_status:'Not Run',validation_status:'Not Checked',review_status:'Awaiting Review',freshness:'Current',implemented:true}))};
const before=JSON.stringify(untouched);
for(const id of ids) {
 assert.equal(presentation(untouched,id).label,'Not run');
 for(const status of ['Not run','Running','Complete','Review required','Failed']) {
  assert.equal(presentation(untouched,id,{overlay:{status}}).label,status);
 }
 const old={workflow:[{id,...accepted}]};
 assert.equal(presentation(old,id,{overlay:{invalidated:true}}).label,'Not run');
 assert.match(presentation(old,id,{overlay:{invalidated:true}}).detail,/Earlier evidence/);
}
assert.equal(JSON.stringify(untouched),before);
""")

    def test_partial_stage_has_review_status_only_for_a_real_current_review(self):
        self.run_client(r"""
envelope.workflow_runs[0].review_status='Awaiting Review';
assert.equal(presentation(envelope,'local_synthesis').label,'Review required');
envelope.workflow_runs[0].review_status='Accepted';
assert.equal(presentation(envelope,'local_synthesis').label,'Not run');
""")

    def test_current_global_record_failure_or_active_operation_is_visible(self):
        self.run_client(r"""
for(const [id,key,collection] of [['global_rtl_generation','global_generation','jobs'],['global_synthesis','global_workflow','runs'],['global_netlist_simulation','global_workflow','runs'],['layout','physical_workflow','runs'],['drc','drc_workflow','runs'],['lvs','lvs_workflow','runs'],['post_layout_verification','postlayout_workflow','runs']]) {
 const isolated={workflow:[{id,...accepted}],[key]:{[collection]:[{id:'current',stage_id:id,...accepted,execution_status:'Failed'}]}};
 assert.equal(presentation(isolated,id).label,'Failed');
 isolated[key][collection][0].execution_status='Running';
 assert.equal(presentation(isolated,id).label,'Running');
 isolated[key][collection][0].freshness='Stale';
 isolated[key][collection][0].execution_status='Failed';
 assert.notEqual(presentation(isolated,id).label,'Failed');
}
""")

    def test_s06_old_synthesis_failure_cannot_replace_current_run_state(self):
        self.run_client(r"""
envelope.workflow.push({id:'local_netlist_simulation',execution_status:'Not Run',validation_status:'Not Checked',review_status:'Awaiting Review',freshness:'Current',implemented:true});
envelope.workflow_nodes.push({node_id:'node-a',stage_id:'local_netlist_simulation',latest_run_id:'sim-old'});
envelope.workflow_runs.push({...run,id:'sim-old',stage_id:'local_netlist_simulation',validation_status:'Failed',prior_run_id:'older-synthesis',netlist_sha256:'old-hash'});
assert.equal(presentation(envelope,'local_netlist_simulation').label,'Not run');
envelope.workflow_runs[0].netlist_sha256='new-hash';
envelope.workflow_runs.at(-1).prior_run_id='run-a';envelope.workflow_runs.at(-1).netlist_sha256='new-hash';
assert.equal(presentation(envelope,'local_netlist_simulation').label,'Failed');
""")


if __name__ == "__main__":
    unittest.main()

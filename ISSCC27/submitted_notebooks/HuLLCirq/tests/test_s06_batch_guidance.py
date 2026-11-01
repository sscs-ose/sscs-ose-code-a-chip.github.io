"""Aggregate S06 next actions never treat a selected-node pass as all-node completion."""
import unittest
from test_flow_guidance import FlowGuidanceTests


class S06BatchGuidanceTests(unittest.TestCase):
    run_client = FlowGuidanceTests.run_client

    def test_current_failed_source_offers_the_visible_s04_repair_draft(self):
        self.run_client(r"""
const r=resolve(context('local_netlist_simulation',{record:accepted,netlistSummary:{total:11,accepted:0,runnable:3,blocked:8,failed:3,repairable:3,firstFailed:{id:'control',name:'Job control'},firstRepairable:{id:'control',name:'Job control'}}}));
assert.equal(r.primary.testId,'workflow-netlist-repair-all');assert.match(r.primary.label,/failed node netlists/);
assert.match(r.summary,/3 node\(s\) failed.*8.*S04.*S05 and S06/);assert.notEqual(r.tone,'success');
""")

    def test_one_failed_node_retains_its_direct_repair_route(self):
        self.run_client(r"""
const r=resolve(context('local_netlist_simulation',{netlistSummary:{total:11,accepted:10,runnable:1,blocked:0,failed:1,repairable:1,firstRepairable:{id:'fifo',name:'Output FIFO'}}}));
assert.equal(r.primary.testId,'workflow-netlist-repair-first');assert.match(r.primary.label,/Output FIFO/);
""")

    def test_click_running_overrides_old_acceptance_and_prepared_repair_guidance(self):
        self.run_client(r"""
for(const stage of stages.map(row=>row[0])) {
 const r=resolve(context(stage,{record:accepted,executionOverlay:{status:'Running'},generationBatchGuidance:{title:'Old ready preview'},netlistSummary:{total:1,accepted:1}}));
 assert.equal(r.decisionId,'execution_running');assert.equal(r.title,'Running');assert.equal(r.primary.kind,'inspect');assert.notEqual(r.tone,'success');
}
""")

    def test_unknown_completion_offers_readonly_refresh_and_never_resubmits(self):
        self.run_client(r"""
let reads=0;const refresh=()=>reads++;
for(const stage of stages.map(row=>row[0])) {
 const r=resolve(context(stage,{record:accepted,executionOverlay:{status:'Failed',reconnectRequired:true,detail:'Saved result not confirmed'},executionReconnect:refresh}));
 assert.equal(r.decisionId,'execution_reconnect');assert.equal(r.primary.action,refresh);assert.equal(r.primary.label,'Refresh saved results');
 r.primary.action();
}
assert.equal(reads,14);
""")

    def test_restarted_upstream_never_advances_from_old_aggregate_passes(self):
        self.run_client(r"""
const overlay={status:'Not run',invalidated:true};
let r=resolve(context('local_netlist_simulation',{record:accepted,executionOverlay:overlay,netlistSummary:{total:11,accepted:11},executionUpstreamRunning:{stage:'local_synthesis'}}));
assert.equal(r.decisionId,'execution_invalidated');assert.equal(r.primary.stage,'local_synthesis');assert.equal(r.primary.label,'View running stage');
r=resolve(context('local_netlist_simulation',{record:accepted,executionOverlay:overlay,netlistSummary:{total:11,accepted:11}}));
assert.equal(r.primary.testId,'workflow-run');assert.notEqual(r.primary.stage,'node_implementation_specs');
r=resolve(context('local_netlist_simulation',{record:accepted,executionOverlay:overlay,gate:'Current S05 required',netlistSummary:{total:11,accepted:11}}));
assert.equal(r.primary.stage,'local_synthesis');assert.match(r.detail,/S05 required/);
""")

    def test_selected_accepted_node_still_offers_remaining_batch(self):
        self.run_client(r"""
const r=resolve(context('local_netlist_simulation',{record:accepted,netlistSummary:{total:11,accepted:2,runnable:8,blocked:1,failed:0},blocker:{kind:'implementation_required',message:'Selected checker unavailable'}}));
assert.equal(r.primary.testId,'workflow-batch-run');assert.equal(r.scope,'All nodes');assert.match(r.summary,/2\/11.*8 remaining.*1 node\(s\) need/);
assert.notEqual(r.primary.stage,'node_implementation_specs');assert.notEqual(r.primary.stage,'local_synthesis');
""")

    def test_only_all_current_adoptions_advance_to_implementation_specs(self):
        self.run_client(r"""
const r=resolve(context('local_netlist_simulation',{netlistSummary:{total:11,accepted:11,runnable:0,blocked:0,failed:0}}));
assert.equal(r.primary.stage,'node_implementation_specs');assert.equal(r.tone,'success');assert.equal(r.scope,'All nodes');
""")

    def test_failed_other_node_remains_visible_and_batch_retry_stays_available(self):
        self.run_client(r"""
const r=resolve(context('local_netlist_simulation',{record:accepted,netlistSummary:{total:11,accepted:10,runnable:1,blocked:0,failed:1,firstFailed:{id:'fifo',name:'Output FIFO'}}}));
assert.equal(r.primary.stage,'local_netlist_simulation');assert.equal(r.primary.nodeId,'fifo');assert.equal(r.secondary.testId,'workflow-batch-run');assert.notEqual(r.tone,'success');
""")

    def test_checker_requirement_does_not_incorrectly_repeat_s05(self):
        self.run_client(r"""
const r=resolve(context('local_netlist_simulation',{netlistSummary:{total:2,accepted:1,runnable:0,blocked:1,failed:0,firstBlocked:{id:'fifo'}},netlistBlocker:{kind:'implementation_required',message:'Original FIFO checker missing.'}}));
assert.equal(r.primary.stage,'specifications');assert.equal(r.primary.nodeId,'fifo');assert.match(r.summary,/Original FIFO checker missing/);
assert.equal(r.secondary.kind,'inspect');assert.notEqual(r.primary.stage,'local_synthesis');
""")

    def test_missing_current_s05_is_distinct_from_checker_configuration_and_review(self):
        self.run_client(r"""
for(const [kind,stage] of [['candidate_required','local_rtl_generation'],['synthesis_required','local_synthesis'],['configuration_required','global_settings'],['input_required','specifications']]) {
 const r=resolve(context('local_netlist_simulation',{netlistSummary:{total:1,accepted:0,runnable:0,blocked:1,failed:0,firstBlocked:{id:'node'}},netlistBlocker:{kind,message:'Explicit prerequisite'}}));
 assert.equal(r.primary.stage,stage);assert.match(r.summary,/Explicit prerequisite/);
}
const r=resolve(context('local_netlist_simulation',{netlistSummary:{total:2,accepted:1,runnable:1,blocked:0,failed:0,firstReview:{id:'review',name:'Control'}}}));
assert.equal(r.primary.nodeId,'review');assert.equal(r.secondary.testId,'workflow-batch-run');assert.match(r.summary,/awaits adoption/);
""")

    def test_global_gate_active_batch_reconnect_and_historical_source_take_precedence(self):
        self.run_client(r"""
const base={netlistSummary:{total:2,accepted:1,runnable:1,blocked:0,failed:0}};
let r=resolve(context('local_netlist_simulation',{...base,netlistBatchGate:'Update and restart service'}));assert.equal(r.primary.kind,'inspect');assert.match(r.summary,/restart/);
r=resolve(context('local_netlist_simulation',{...base,activeOperation:{stage:'local_netlist_simulation'}}));assert.equal(r.decisionId,'active_current');
r=resolve(context('local_synthesis',{activeOperation:{stage:'local_netlist_simulation'}}));assert.equal(r.primary.stage,'local_netlist_simulation');
r=resolve(context('local_netlist_simulation',{...base,reconnect:'workflow-batch-reconnect'}));assert.equal(r.primary.testId,'workflow-batch-reconnect');
r=resolve(context('local_netlist_simulation',{...base,record:accepted,recordCurrent:false}));assert.equal(r.primary.kind,'latest');assert.notEqual(r.primary.testId,'workflow-batch-run');
""")


del FlowGuidanceTests

if __name__ == '__main__':
    unittest.main()

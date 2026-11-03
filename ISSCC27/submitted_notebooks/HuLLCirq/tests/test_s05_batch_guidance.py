"""S05 next steps must reflect all-node synthesis and exact failure recovery."""
import unittest
from test_flow_guidance import FlowGuidanceTests


class S05BatchGuidanceTests(unittest.TestCase):
    run_client = FlowGuidanceTests.run_client
    def test_pending_nodes_keep_batch_as_primary_after_one_accepted_node(self):
        self.run_client(r"""
const r=resolve(context('local_synthesis',{record:accepted,synthesisSummary:{total:11,accepted:5,firstIncomplete:{id:'pending',name:'Pending'}}}));
assert.equal(r.primary.testId,'workflow-batch-run');assert.equal(r.scope,'All nodes');assert.match(r.summary,/5\/11/);
assert.notEqual(r.primary.stage,'local_netlist_simulation');
""")

    def test_failure_is_repaired_from_exact_selected_node(self):
        self.run_client("""
const r=resolve(context('local_synthesis',{record:{...accepted,validation_status:'Failed',review_status:'Awaiting Review'},repairAvailable:true,failureExcerpt:'candidate.v:54: ERROR: Static cast',synthesisSummary:{total:11,accepted:5}}));
assert.equal(r.secondary.testId,'workflow-prepare-repair');assert.match(r.summary,/candidate.v:54/);assert.match(r.summary,/synthesis/);
""")

    def test_other_failed_node_prevents_whole_stage_completion(self):
        self.run_client("""
const r=resolve(context('local_synthesis',{record:accepted,synthesisSummary:{total:11,accepted:5,firstFailed:{id:'failed',name:'PE 0,1'}}}));
assert.equal(r.primary.stage,'local_synthesis');assert.equal(r.primary.nodeId,'failed');assert.notEqual(r.tone,'success');
""")

    def test_only_all_current_adoptions_advance_to_s06(self):
        self.run_client("""
const r=resolve(context('local_synthesis',{synthesisSummary:{total:11,accepted:11}}));
assert.equal(r.primary.stage,'local_netlist_simulation');assert.equal(r.tone,'success');assert.match(r.summary,/Circuit behavior is checked in S06/);
""")

    def test_active_batch_blocks_other_stage_without_selected_child(self):
        self.run_client("""
const r=resolve(context('local_netlist_simulation',{activeOperation:{stage:'local_synthesis'}}));
assert.equal(r.primary.stage,'local_synthesis');assert.match(r.title,/progress/);assert.notEqual(r.primary.testId,'workflow-run');
""")


# The base class is imported for its runner only.
del FlowGuidanceTests

if __name__ == '__main__':
    unittest.main()

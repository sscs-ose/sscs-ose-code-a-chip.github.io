"""Specific S05/S06 availability reasons, with isolated UI fixtures only."""
import unittest
import test_s06_batch_gui as s06
import test_flow_guidance as guidance


class AvailabilityReasonsGuiTests(unittest.TestCase):
    client = s06.S06BatchGuiTests.client

    def test_checker_and_missing_s05_are_distinct_and_route_to_valid_sources(self):
        self.client(r"""
const raw={...verificationBatch,execution_status:'Completed',validation_status:'Failed',items:[{node_id:'node-b',status:'Blocked',reason:'Checker for original FIFO requirements is not implemented.'}]};
project.envelope.generation.nodes[1].behavioral_verification={available:false,status:'implementation_required',code:'verification_implementation_required',message:'Checker for original FIFO requirements is not implemented.'};
local.receive(makeEnvelope([raw],[passed,synthesisB,verifiedA]));const before=JSON.stringify(raw);
let row=localTest('workflow-batch-node-node-b');assert.match(text(row),/Not run.*Not implemented.*original FIFO/);assert.doesNotMatch(text(row),/Blocked/);
assert.match(text(localTest('workflow-netlist-unavailable')),/1 Not implemented/);
assert.equal(local.netlistSummary().availabilityCounts[0].label,'Not implemented');
localTest('workflow-batch-prerequisite-node-b').onclick();assert.deepEqual(notices.at(-1),['specifications','node-b']);
local.runs=[passed,verifiedA];local.refresh();row=localTest('workflow-batch-node-node-b');assert.match(text(row),/Prerequisites missing.*S05/);
localTest('workflow-batch-prerequisite-node-b').onclick();assert.deepEqual(notices.at(-1),['local_synthesis','node-b']);
assert.equal(JSON.stringify(raw),before);assert.equal(localTest('workflow-batch-record').text,JSON.stringify(raw,null,2));assert.equal(requests.length,0);
""")

    def test_tool_setup_and_missing_verification_input_are_not_implementation_claims(self):
        self.client(r"""
for(const [kind,label,message,target] of [
 ['configuration_required','Tool setup required','Configure the trusted simulator.','global_settings'],
 ['input_required','Input required','Saved original vectors need a reset sample.','specifications']]) {
 project.envelope.generation.nodes[1].behavioral_verification={available:false,status:kind,message};local.refresh();
 const row=text(localTest('workflow-batch-readiness-node-b'));assert.ok(row.includes(label),row);assert.ok(row.includes(message),row);assert.doesNotMatch(row,/Blocked|Not implemented|Needs attention/);
 localTest('workflow-batch-prerequisite-node-b').onclick();assert.deepEqual(notices.at(-1),[target,'node-b']);
 assert.equal(local.netlistSummary().availabilityCounts[0].label,label);
}
assert.equal(requests.length,0);
""")


class AvailabilityGuidanceTests(unittest.TestCase):
    run_client = guidance.FlowGuidanceTests.run_client

    def test_aggregate_counts_explain_implementation_and_prerequisites_without_blocked(self):
        self.run_client(r"""
const result=resolve(context('local_netlist_simulation',{netlistSummary:{total:11,accepted:0,runnable:3,blocked:8,failed:3,firstFailed:{id:'control',name:'Job control'},availabilityCounts:[{kind:'implementation',label:'Not implemented',count:6},{kind:'prerequisite',label:'Prerequisites missing',count:2}]}}));
assert.match(result.summary,/3 node\(s\) failed.*6 Not implemented; 2 Prerequisites missing/);assert.doesNotMatch(result.title+' '+result.summary,/blocked/i);
""")

    def test_implementation_next_action_explains_developer_work_instead_of_retry(self):
        self.run_client(r"""
const result=resolve(context('local_netlist_simulation',{netlistSummary:{total:1,accepted:0,runnable:0,blocked:1,failed:0,availabilityCounts:[{kind:'implementation',label:'Not implemented',count:1}],firstBlocked:{id:'fifo'}},netlistBlocker:{kind:'implementation_required',message:'The output FIFO checker has no implementation.'}}));
assert.match(result.title,/Not implemented/);assert.match(result.summary,/output FIFO checker/);assert.match(result.detail,/HuLLCirq must implement.*Repeating RTL generation or synthesis cannot add it/);
assert.equal(result.primary.stage,'specifications');assert.notEqual(result.primary.stage,'local_synthesis');assert.doesNotMatch(result.title+' '+result.summary,/blocked/i);
""")

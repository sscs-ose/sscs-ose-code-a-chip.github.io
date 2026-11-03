"""Stage-scoped S06 batch controls with isolated DOM fixtures; no real EDA calls."""
from pathlib import Path
import shutil
import subprocess
import unittest

from test_generation_recovery_gui import CLIENT
from test_s05_batch_gui import SETUP

PROJECT = Path(__file__).resolve().parents[1]


S06_SETUP = r"""
project.stage='local_netlist_simulation';
project.envelope.workflow_batch_stages=['local_synthesis','local_netlist_simulation'];
const synthesisB={...passed,id:'synthesis-b-ready',node_id:'node-b',candidate_id:candidates[1].id,netlist:'saved B netlist',netlist_sha256:'netlist-b'};
const verifiedA={...passed,id:'verification-a',stage_id:'local_netlist_simulation',prior_run_id:passed.id,netlist_sha256:passed.netlist_sha256,netlist:null,verification_plan:{plan_sha256:'plan-a'}};
const verifiedB={...synthesisB,id:'verification-b',stage_id:'local_netlist_simulation',prior_run_id:synthesisB.id,netlist:null,verification_plan:{plan_sha256:'plan-b'}};
const verificationBatch={...batch,id:'verification-batch',stage_id:'local_netlist_simulation',items:[{node_id:'node-a',run_id:verifiedA.id,status:'Skipped',reason:'Current accepted S06 result'},{node_id:'node-b',status:'Queued'}]};
local.receive(makeEnvelope([], [passed,synthesisB,verifiedA]));local.render(localHost);
"""

RECOVERY_SETUP = r"""
const synthesisSource={...synthesisB,revision_id:candidates[1].revision_id,requested_revision_id:'revision-a',input_hash:candidates[1].input_hash,rtl_sha256:candidates[1].rtl_sha256};
const failedVerification={...verifiedB,revision_id:candidates[1].revision_id,requested_revision_id:'revision-a',input_hash:candidates[1].input_hash,rtl_sha256:candidates[1].rtl_sha256,vector_hash:'original-vectors-b',testbench_sha256:'frozen-testbench-b',validation_status:'Failed',review_status:'Awaiting Review',checks:{executed:true,stdout:'HULLCIRQ_FAIL step=0 before signal=config_data_ready expected=0 actual=x',stderr:''},verification_plan:{plan_sha256:'original-plan-b',description:'Preserve original requirements'}};
const drafts=[];local.callbacks.prepareRepair=(candidate,instruction)=>{drafts.push({candidate,instruction});return true;};
local.receive(makeEnvelope([{...verificationBatch,execution_status:'Completed',validation_status:'Failed'}],[passed,synthesisSource,verifiedA,failedVerification]));
"""


class S06BatchGuiTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated GUI checks.')
        result = subprocess.run([node, '-e', CLIENT + SETUP + S06_SETUP + '\n(async()=>{\n' + body +
                                 '\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});'],
                                cwd=PROJECT, capture_output=True, text=True, encoding='utf-8', timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_failed_node_repair_is_visible_above_debug_form_and_carries_exact_sources(self):
        self.client(RECOVERY_SETUP + r"""
const before=JSON.stringify([candidates,local.runs]);
assert.equal(local.nodeId,'node-a');assert.equal(local.netlistSummary().firstRepairable.id,'node-b');
assert.match(text(localTest('workflow-netlist-failure-node-b')),/config_data_ready expected=0 actual=x.*S04.*S05 and S06/);
assert.equal(localTest('workflow-netlist-prepare-repair-node-b').disabled,false);
localTest('workflow-netlist-prepare-repair-node-b').onclick();
assert.equal(drafts.length,1);assert.equal(drafts[0].candidate.id,candidates[1].id);
for(const value of [failedVerification.id,synthesisSource.id,failedVerification.candidate_id,failedVerification.netlist_sha256,failedVerification.vector_hash,failedVerification.testbench_sha256,failedVerification.verification_plan.plan_sha256,'config_data_ready expected=0 actual=x']) assert.ok(drafts[0].instruction.includes(value),value);
assert.match(drafts[0].instruction,/do not weaken the test or change its expectations/);
assert.equal(JSON.stringify([candidates,local.runs]),before);assert.equal(requests.length,0);
""")

    def test_next_step_and_table_repair_work_without_manually_selecting_the_failed_node(self):
        self.client(RECOVERY_SETUP + r"""
localTest('workflow-netlist-repair-first').onclick();localTest('workflow-batch-repair-node-b').onclick();
assert.equal(drafts.length,2);assert.equal(drafts.every(draft=>draft.candidate.node_id==='node-b'),true);
assert.equal(local.nodeId,'node-a');assert.equal(requests.length,0);
localTest('workflow-netlist-inspect-node-b').onclick();assert.equal(local.selected().id,failedVerification.id);
""")

    def test_stale_source_setup_error_and_timeout_do_not_prepare_an_rtl_repair(self):
        self.client(RECOVERY_SETUP + r"""
for(const change of [{requested_revision_id:'older-revision'},{vector_hash:null},{testbench_sha256:null},{checks:{executed:false}},{checks:{executed:true,commands:[{status:'Timeout'}]}}]) {
 local.runs=[passed,synthesisSource,verifiedA,{...failedVerification,...change}];local.refresh();
 assert.equal(localTest('workflow-netlist-prepare-repair-node-b').disabled,true,JSON.stringify(change));
 assert.equal(local.prepareRepair(local.netlistFor('node-b')),false);
}
assert.equal(drafts.length,0);assert.equal(requests.length,0);
assert.ok(localTest('workflow-netlist-configure-node-b'));
""")

    def test_tool_timeout_retry_selects_exact_node_and_does_not_call_the_model(self):
        self.client(RECOVERY_SETUP + r"""
local.runs=[passed,synthesisSource,verifiedA,{...failedVerification,checks:{executed:true,commands:[{status:'Timeout'}]}}];local.refresh();
responder=async(route,body)=>{assert.equal(route,'workflow/start');assert.equal(body.node_id,'node-b');assert.equal(body.candidate_id,candidates[1].id);return makeEnvelope([],local.runs);};
await localTest('workflow-netlist-retry-node-b').onclick();assert.equal(requests.length,1);assert.equal(drafts.length,0);
assert.equal(local.nodeId,'node-b');
""")

    def test_missing_checker_is_separate_from_a_failed_rtl_and_has_no_repair_action(self):
        self.client(r"""
project.envelope.generation.nodes[1].behavioral_verification={available:false,status:'implementation_required',message:'Saved requirements need a checker.'};local.refresh();
assert.match(text(localTest('workflow-netlist-unavailable')),/test requirements exist.*executable checker is not implemented/);
assert.equal(localTest('workflow-netlist-prepare-repair-node-b'),null);
localTest('workflow-netlist-prerequisite-node-b').onclick();assert.deepEqual(notices.at(-1),['specifications','node-b']);
assert.equal(requests.length,0);
""")

    def test_ambiguous_disconnect_requires_reconnect_before_source_repair(self):
        self.client(RECOVERY_SETUP + r"""
local.batchPollError='Connection lost. Saved status unknown.';local.refresh();
assert.equal(localTest('workflow-netlist-prepare-repair-node-b').disabled,true);
assert.match(localTest('workflow-netlist-prepare-repair-node-b').title,/Reconnect/);
responder=async route=>{assert.equal(route,'project');return makeEnvelope([{...verificationBatch,execution_status:'Completed',validation_status:'Failed'}],[passed,synthesisSource,verifiedA,failedVerification]);};
await localTest('workflow-batch-reconnect').onclick();
assert.equal(localTest('workflow-netlist-prepare-repair-node-b').disabled,false);
assert.deepEqual(requests.map(row=>row[0]),['project']);assert.equal(drafts.length,0);
""")

    def test_confirmed_cancel_clears_stale_poll_failure_and_offers_remaining_retry(self):
        self.client(RECOVERY_SETUP + r"""
const running={...verificationBatch,execution_status:'Running'};
local.receive(makeEnvelope([running],[passed,synthesisSource,verifiedA,failedVerification]));
local.batchPollError='Offline';local.refresh();
responder=async route=>{assert.equal(route,'workflow/batches/verification-batch/cancel');return makeEnvelope([{...running,execution_status:'Cancelled'}],[passed,synthesisSource,verifiedA,failedVerification]);};
await localTest('workflow-batch-cancel').onclick();
assert.equal(local.batchPollError,null);assert.equal(localTest('workflow-netlist-prepare-repair-node-b').disabled,false);
assert.ok(localTest('workflow-netlist-retry-remaining'));assert.equal(localTest('workflow-netlist-retry-remaining').disabled,false);
assert.equal(requests.length,1);assert.equal(drafts.length,0);
""")

    def test_start_click_synchronously_announces_busy_chrome_before_request_resolves(self):
        self.client(r"""
const pending=deferred(), observations=[];
local.callbacks.chrome=()=>observations.push({busy:local.busy,disabled:localTest('workflow-batch-run').disabled});
responder=()=>pending.promise;const starting=localTest('workflow-batch-run').onclick();
assert.equal(local.busy,true);assert.equal(localTest('workflow-batch-run').disabled,true);
assert.equal(observations.some(item=>item.busy&&item.disabled),true);
pending.resolve(makeEnvelope([{...verificationBatch,execution_status:'Running'}],[passed,synthesisB,verifiedA]));await starting;
assert.equal(local.activeBatch().execution_status,'Running');assert.equal(requests.length,1);
""")

    def test_all_node_action_with_separate_node_debug_and_readiness(self):
        self.client(r"""
assert.equal(localTest('workflow-batch-run').text,'Verify all node netlists');
assert.equal(localTest('workflow-run').text,'Verify selected node netlist');
assert.match(text(localTest('workflow-batch-status')),/1\/2 nodes adopted/);
assert.match(text(localTest('workflow-batch-nodes')),/Current S06 result.*Readiness \/ S05 source/);
assert.match(text(localTest('workflow-batch-readiness-node-b')),/Ready.*synthesis-b-ready/);
assert.equal(requests.length,0);
""")

    def test_old_backend_cannot_silently_run_s05_when_s06_is_requested(self):
        self.client(r"""
delete project.envelope.workflow_batch_stages;local.refresh();assert.equal(localTest('workflow-batch-run').disabled,true);
assert.match(local.batchGate(),/Update and restart.*S06/);responder=()=>assert.fail('Legacy service must not receive stage_id');
await local.startBatch();assert.equal(requests.length,0);assert.equal(localTest('workflow-run').disabled,false);
""")

    def test_s06_sends_explicit_stage_without_changing_s05_contract(self):
        self.client(r"""
responder=async(route,body)=>{assert.equal(route,'workflow/batches/start');assert.equal(body.stage_id,'local_netlist_simulation');assert.equal(body.revision_id,'revision-a');assert.ok(body.request_id);return makeEnvelope([{...verificationBatch,request_id:body.request_id,execution_status:'Running'}],[passed,synthesisB,verifiedA]);};
await localTest('workflow-batch-run').onclick();
assert.equal(requests.length,1);assert.equal(local.batchId,'verification-batch');assert.equal(localTest('workflow-batch-run').disabled,true);
assert.equal(localTest('workflow-batch-cancel').text,'Cancel remaining verification');
""")

    def test_history_and_selection_are_stage_scoped_including_legacy_s05(self):
        self.client(r"""
const old={...verificationBatch,id:'older-verification'}, latest={...verificationBatch,id:'latest-verification'};
local.batchId=batch.id;local.receive(makeEnvelope([old,latest,batch],[passed,synthesisB,verifiedA]));
assert.equal(local.selectedBatch().id,latest.id);assert.match(text(localTest('workflow-batch-history')),/older-verification.*latest-verification|latest-verification.*older-verification/);
assert.doesNotMatch(text(localTest('workflow-batch-history')),/batch-a/);
project.stage='local_synthesis';local.render(localHost);assert.equal(local.selectedBatch().id,batch.id);
assert.equal(localTest('workflow-batch-history'),null);assert.match(text(localTest('workflow-batch-nodes')),/Current S05 result/);
""")

    def test_blocked_checker_is_explained_per_node_and_does_not_stop_batch(self):
        self.client(r"""
project.envelope.generation.nodes[1].behavioral_verification={available:false,status:'implementation_required',message:'Checker for original FIFO requirements is unavailable.'};local.refresh();
assert.match(text(localTest('workflow-batch-readiness-node-b')),/Not implemented.*Checker/);
assert.equal(localTest('workflow-batch-readiness-node-b').title,'Checker for original FIFO requirements is unavailable.');
assert.match(text(localTest('workflow-batch-readiness-node-b')),/Checker for original FIFO requirements/);
assert.equal(localTest('workflow-run').disabled,false);local.setNode('node-b');local.refresh();assert.equal(localTest('workflow-run').disabled,true);
assert.equal(localTest('workflow-batch-run').disabled,false);assert.equal(local.netlistSummary().blocked,1);
assert.equal(local.netlistSummary().accepted,1);assert.equal(requests.length,0);
project.envelope.generation.nodes[1].behavioral_verification={available:false,status:'future_checker_error',message:'Specific unknown checker failure at channel 3.'};local.refresh();
assert.match(text(localTest('workflow-batch-readiness-node-b')),/Specific unknown checker failure at channel 3/);
""")

    def test_current_s06_requires_exact_current_accepted_s05_netlist(self):
        self.client(r"""
assert.equal(local.netlistSummary().accepted,1);
for(const changed of [{prior_run_id:'another-s05'},{netlist_sha256:'another-netlist'},{candidate_id:'other-candidate'},{input_hash:'other-input'},{rtl_sha256:'other-rtl'},{freshness:'Stale'},{review_status:'Awaiting Review'}]) {
 local.runs=[passed,synthesisB,{...verifiedA,...changed}];assert.equal(local.netlistSummary().accepted,0,JSON.stringify(changed));
}
local.runs=[passed,synthesisB,verifiedA,{...passed,id:'newer-s05',netlist_sha256:'newer-netlist'}];
assert.equal(local.netlistSummary().accepted,0);assert.equal(local.netlistFor('node-a'),undefined);
local.refresh();localTest('workflow-batch-inspect-node-a').onclick();assert.equal(local.selected(),undefined);
""")

    def test_batch_child_failures_keep_other_accepted_results_and_exact_inspection(self):
        self.client(r"""
const failure={...verifiedB,execution_status:'Completed',validation_status:'Failed',review_status:'Awaiting Review',checks:{stdout:'HULLCIRQ_FAIL original vector 4',stderr:''}};
const complete={...verificationBatch,execution_status:'Completed',validation_status:'Failed',items:[verificationBatch.items[0],{node_id:'node-b',run_id:failure.id,status:'Failed',reason:'Original-vector behavior mismatch'}]};
local.receive(makeEnvelope([complete],[passed,synthesisB,verifiedA,failure]));
assert.match(text(localTest('workflow-batch-status')),/inspect unresolved nodes.*1\/2 nodes adopted/);
assert.equal(local.netlistSummary().failed,1);localTest('workflow-batch-inspect-node-b').onclick();
assert.equal(local.selected().id,failure.id);assert.match(text(localTest('workflow-result')),/original vector 4/);
assert.equal(requests.length,0);
""")

    def test_poll_cancel_and_reload_never_start_another_request(self):
        self.client(r"""
const running={...verificationBatch,execution_status:'Running',validation_status:'Not Checked'};
local.receive(makeEnvelope([running],[passed,synthesisB,verifiedA]));
responder=async route=>{if(route==='workflow/batches/verification-batch')return running;assert.equal(route,'project');return makeEnvelope([running],[passed,synthesisB,verifiedA]);};
await local.poll();assert.deepEqual(requests.map(row=>row[0]),['workflow/batches/verification-batch','project']);
const reloaded=new sandbox.LocalWorkflow(local.callbacks);reloaded.receive(project.envelope);assert.equal(reloaded.activeBatch().stage_id,'local_netlist_simulation');assert.ok(reloaded.pollTimer);
responder=async(route,body)=>{assert.equal(route,'workflow/batches/verification-batch/cancel');return makeEnvelope([{...running,execution_status:'Cancelled'}],[passed,synthesisB,verifiedA]);};
await localTest('workflow-batch-cancel').onclick();assert.equal(requests.length,3);assert.equal(local.netlistSummary().accepted,1);assert.equal(local.activeBatch(),undefined);
""")

    def test_lost_start_reconnect_is_stage_scoped_and_never_resends(self):
        self.client(r"""
let requestId;responder=async(route,body)=>{requestId=body.request_id;throw Error('Connection lost');};await local.startBatch();
assert.ok(local.batchStartUncertain);assert.ok(localTest('workflow-batch-reconnect'));assert.equal(localTest('workflow-batch-run').disabled,true);
responder=async route=>{assert.equal(route,'project');return makeEnvelope([{...batch,request_id:requestId},{...verificationBatch,request_id:requestId,execution_status:'Running'}],[passed,synthesisB,verifiedA]);};
await local.reconnectBatch();assert.equal(local.batchId,verificationBatch.id);assert.equal(local.batchRequestId,null);assert.equal(local.batchStartUncertain,false);
assert.deepEqual(requests.map(row=>row[0]),['workflow/batches/start','project']);
""")

    def test_other_stage_batch_still_blocks_execution_without_contaminating_s06_view(self):
        self.client(r"""
local.receive(makeEnvelope([{...batch,execution_status:'Running'}],[passed,synthesisB,verifiedA]));
assert.equal(local.selectedBatch(),undefined);assert.equal(localTest('workflow-batch-cancel'),null);assert.equal(localTest('workflow-batch-run').disabled,true);
assert.match(text(localTest('workflow-batch-status')),/Ready to verify all node netlists/);
assert.doesNotMatch(text(localTest('workflow-batch-record')),/batch-a/);
""")

    def test_main_header_handler_and_next_step_use_the_batch_action(self):
        self.client(r"""
const app=fs.readFileSync('src/gui/app.js','utf8');
const header=app.match(/byId\('run-verification'\)\.textContent = ([^\n]+);/)[1];
sandbox.state={stage:'local_netlist_simulation'};
Object.assign(sandbox,{postlayoutStage:false,lvsStage:false,drcStage:false,physicalStage:false,candidateStage:false,implementationStage:false});
assert.equal(vm.runInContext(header,sandbox),'Verify all node netlists');
const definitions=app.match(/const definitions = (\{[\s\S]*?\n  \});/)[1];
Object.assign(sandbox,{localFlow:local,implementationSpecs:{},globalGeneration:{},globalFlow:{},physicalFlow:{},drcFlow:{},lvsFlow:{},postlayoutFlow:{actionLabel:()=>''}});
assert.equal(vm.runInContext('('+definitions+').local_netlist_simulation[3]',sandbox),'workflow-batch-run');
const validate=app.match(/async function validate\(\) \{[\s\S]*?\n\}/)[0];
let batchCalls=0,singleCalls=0;const realBatch=local.startBatch;
local.startBatch=async()=>{batchCalls++};local.start=async()=>{singleCalls++};sandbox.flushActiveField=()=>{};
vm.runInContext(validate+'\nglobalThis.validateForQA=validate;',sandbox);await sandbox.validateForQA();
assert.equal(batchCalls,1);assert.equal(singleCalls,0);local.startBatch=realBatch;
""")


if __name__ == '__main__':
    unittest.main()

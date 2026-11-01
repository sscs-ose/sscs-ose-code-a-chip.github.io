"""Next-step decisions on isolated GUI state; no model, circuit or service calls."""
from pathlib import Path
import shutil
import subprocess
import unittest


PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const sandbox={};vm.createContext(sandbox);vm.runInContext('{'+fs.readFileSync('src/gui/availability.js','utf8').replace(/export /g,'')+'\nglobalThis.availabilityReason=availabilityReason;}',sandbox);
const source=fs.readFileSync('src/gui/flow_guidance.js','utf8');
vm.runInContext(source.replace(/^import[^\n]+\n/gm,'').replace(/export /g,'')+'\nthis.resolve=resolveStageGuidance;this.stages=FLOW_STAGES;',sandbox);
const resolve=sandbox.resolve,stages=sandbox.stages;
const accepted={id:'selected-result',execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current'};
const inputs=['global_settings','graph_editor','specifications'];
const tools=[
 ['local_synthesis','local_rtl_generation','workflow-run','Run generic synthesis'],
 ['local_netlist_simulation','local_synthesis','workflow-run','Run netlist verification'],
 ['node_implementation_specs','local_netlist_simulation','implementation-spec-run','Derive and verify node specification'],
 ['global_synthesis','global_rtl_generation','global-workflow-run','Run global generic synthesis'],
 ['global_netlist_simulation','global_synthesis','global-workflow-run','Run global netlist verification'],
 ['layout','global_netlist_simulation','physical-workflow-run','Run physical layout'],
 ['drc','layout','drc-workflow-run','Run DRC'],
 ['lvs','drc','lvs-workflow-run','Run LVS'],
 ['post_layout_verification','lvs','postlayout-workflow-run','Run post-layout verification']
];
function context(stage='local_synthesis',extra={}) {
 const item=tools.find(row=>row[0]===stage);
 return {stage,implemented:true,prerequisite:item?.[1]||'specifications',runTestId:item?.[2],runLabel:item?.[3],...extra};
}
function next(stage) {return stages[stages.findIndex(row=>row[0]===stage)+1]?.[0];}
function neverAdvance(result,stage) {
 assert.ok(!(result.primary?.kind==='navigate'&&result.primary.stage===next(stage)),JSON.stringify(result));
 assert.notEqual(result.tone,'success',JSON.stringify(result));
}
"""


class FlowGuidanceTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for isolated guidance checks.")
        result = subprocess.run(
            [node, "-e", CLIENT + "\n" + body], cwd=PROJECT,
            capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_all_fourteen_stages_have_an_action_using_the_existing_controls(self):
        self.run_client(r"""
assert.equal(stages.length,14);assert.equal(new Set(stages.map(row=>row[0])).size,14);
for(const stage of inputs) {
 const result=resolve(context(stage));
 assert.equal(result.primary.kind,'control');assert.equal(result.primary.testId,'run-verification');
}
const local={title:'Review the RTL for synthesis',summary:'S04 checks the external interface; S06 verifies circuit behavior.',primary:{label:'Open candidate review',kind:'inspect',target:'review-content'}};
assert.equal(resolve(context('local_rtl_generation',{localGuidance:local})).primary.label,'Open candidate review');
assert.equal(resolve(context('global_rtl_generation')).primary.testId,'global-context-preview');
for(const [stage,,testId,label] of tools) {
 const result=resolve(context(stage));assert.equal(result.primary.kind,'control');
 assert.equal(result.primary.testId,testId);assert.equal(result.primary.label,label);
 assert.equal(typeof result.summary,'string');assert.ok(result.summary.length>0);
}
""")

    def test_input_completion_diagnostics_and_earlier_steps(self):
        self.run_client(r"""
for(const stage of inputs) {
 const success=resolve(context(stage,{record:{...accepted}}));
 assert.equal(success.primary.stage,next(stage));assert.equal(success.tone,'success');
 const failed=resolve(context(stage,{record:{...accepted,validation_status:'Failed',review_status:'Awaiting Review'}}));
 assert.equal(failed.primary.kind,'inspect');assert.match(failed.primary.label,/issues/);
 assert.equal(failed.secondary.testId,'run-verification');neverAdvance(failed,stage);
 const awaiting=resolve(context(stage,{record:{...accepted,review_status:'Awaiting Review'}}));
 assert.equal(awaiting.primary.kind,'inspect');assert.match(awaiting.primary.label,/accept/);neverAdvance(awaiting,stage);
}
const missing=resolve(context('specifications',{missingInputStage:'graph_editor'}));
assert.equal(missing.primary.stage,'graph_editor');
const empty=resolve(context('specifications',{emptyGraph:true}));
assert.equal(empty.primary.stage,'graph_editor');assert.match(empty.detail,/Add node/);
""")

    def test_read_only_wins_over_ready_and_unsaved_and_does_not_execute(self):
        self.run_client(r"""
for(const [stage] of stages) {
 const result=resolve(context(stage,{record:{...accepted},readOnly:true,dirty:true}));
 assert.equal(result.primary.kind,'inspect');assert.equal(result.secondary.testId,'workspace-home');
 assert.match(result.summary,/read-only.*duplicate/i);assert.notEqual(result.tone,'success');
}
""")

    def test_conflict_invalid_input_and_unsaved_design_are_actionable_before_execution(self):
        self.run_client(r"""
for(const [stage] of stages) {
 const conflict=resolve(context(stage,{record:{...accepted},conflict:'new-revision',dirty:true}));
 assert.equal(conflict.primary.testId,'export-project');assert.equal(conflict.secondary.testId,'workspace-home');
 const dirty=resolve(context(stage,{record:{...accepted},dirty:true}));
 assert.equal(dirty.primary.testId,'save-project');assert.match(dirty.summary,/does not run a model or EDA/);
}
const invalid=resolve(context('local_synthesis',{invalidInput:'Verification JSON is invalid',nodeId:'scheduler'}));
assert.equal(invalid.primary.stage,'specifications');assert.equal(invalid.primary.nodeId,'scheduler');
assert.match(invalid.summary,/JSON is invalid/);
""")

    def test_running_operations_route_to_actual_stage_and_node_without_restarting(self):
        self.run_client(r"""
const other=resolve(context('layout',{activeOperation:{stage:'local_rtl_generation',nodeId:'scheduler'}}));
assert.equal(other.primary.kind,'navigate');assert.equal(other.primary.stage,'local_rtl_generation');
assert.equal(other.primary.nodeId,'scheduler');
for(const execution_status of ['Queued','Running']) {
 const current=resolve(context('layout',{record:{...accepted,execution_status}}));
 assert.equal(current.primary.kind,'inspect');assert.equal(current.primary.target,'stage-content');neverAdvance(current,'layout');
}
const busy=resolve(context('global_rtl_generation',{busy:true,previewReady:true}));
assert.equal(busy.primary.kind,'inspect');
""")

    def test_unknown_start_or_poll_outcome_requires_reconnect_without_resend(self):
        self.run_client(r"""
for(const [stage,,runTestId] of tools) {
 const reconnect=runTestId.replace(/-run$/,'-reconnect');
 const result=resolve(context(stage,{record:{...accepted,execution_status:'Running'},reconnect,gate:'The start outcome is unknown.'}));
 assert.equal(result.primary.kind,'control');assert.equal(result.primary.testId,reconnect);
 assert.notEqual(result.primary.testId,runTestId);assert.match(result.summary,/does not resend/);
 assert.notEqual(result.tone,'success');
}
""")

    def test_local_generation_guidance_uses_interface_scope_and_preserves_node(self):
        self.run_client(r"""
const localGuidance={tone:'neutral',title:'Review the RTL for synthesis',summary:'The S04 external-interface check passed. S06 checks circuit behavior.',
 primary:{kind:'inspect',target:'review-content',label:'Open candidate review'}};
const result=resolve(context('local_rtl_generation',{nodeId:'scheduler',nodeName:'2x2 scheduler',localGuidance}));
assert.equal(result.primary.target,'review-content');assert.equal(result.title,localGuidance.title);
assert.equal(result.scope,'Selected node: 2x2 scheduler');
assert.equal(result.phase,'Generate, synthesize & verify nodes · 04–07');
assert.notEqual(result.primary.testId,'verify-saved-rtl');assert.match(result.summary,/external-interface.*S06/);
""")

    def test_historical_pass_cannot_advance_current_sources(self):
        self.run_client(r"""
for(const stage of [...tools.map(row=>row[0]),'global_rtl_generation']) {
 const result=resolve(context(stage,{record:{...accepted},historical:true}));
 assert.equal(result.primary.kind,'latest');assert.equal(result.secondary.kind,'inspect');neverAdvance(result,stage);
}
""")

    def test_stale_results_require_current_inputs_not_old_pass_or_acceptance(self):
        self.run_client(r"""
for(const stage of inputs) {
 const result=resolve(context(stage,{record:{...accepted,freshness:'Stale'}}));
 assert.equal(result.primary.testId,'run-verification');neverAdvance(result,stage);
}
for(const [stage,prerequisite,testId] of tools) {
 const record={...accepted,freshness:'Stale'};
 const runnable=resolve(context(stage,{record}));assert.equal(runnable.primary.testId,testId);neverAdvance(runnable,stage);
 const blocked=resolve(context(stage,{record,gate:'A current accepted source is required.'}));
 assert.equal(blocked.primary.stage,prerequisite);neverAdvance(blocked,stage);
}
""")

    def test_review_changes_and_failed_results_route_to_evidence_and_source(self):
        self.run_client(r"""
for(const [stage,prerequisite] of tools) {
 for(const review_status of ['Changes Requested','Returned']) {
  const result=resolve(context(stage,{record:{...accepted,review_status}}));
  assert.equal(result.primary.kind,'inspect');assert.equal(result.secondary.stage,prerequisite);neverAdvance(result,stage);
 }
 for(const execution_status of ['Failed','Cancelled','Interrupted']) {
  const result=resolve(context(stage,{record:{...accepted,execution_status,error:{message:'Recorded source mismatch'}}}));
  assert.equal(result.primary.kind,'inspect');assert.equal(result.secondary.stage,prerequisite);
  assert.match(result.summary,/Recorded source mismatch/);neverAdvance(result,stage);
 }
 for(const validation_status of ['Failed','Unsupported']) {
  const result=resolve(context(stage,{record:{...accepted,validation_status}}));
  assert.equal(result.primary.kind,'inspect');neverAdvance(result,stage);
 }
}
""")

    def test_unimplemented_and_new_eleven_node_global_flow_report_capability_limit(self):
        self.run_client(r"""
const generic=resolve(context('layout',{implemented:false}));
assert.match(generic.title,/Not implemented/);assert.equal(generic.primary.stage,'specifications');
const blocked=resolve(context('global_rtl_generation',{gate:'S08 currently integrates the six declared NPU node types.'}));
assert.match(blocked.title,/Not implemented/);assert.match(blocked.summary,/six declared/);
assert.match(blocked.detail,/HuLLCirq development/);assert.equal(blocked.primary.stage,'specifications');
assert.notEqual(blocked.primary.testId,'global-context-preview');assert.notEqual(blocked.primary.testId,'global-generate');
assert.doesNotMatch(blocked.summary,/Complete all.*then run/i);
""")

    def test_generation_batch_progress_and_reconnect_override_generic_active_job_hint(self):
        self.run_client(r"""
const generationBatchGuidance={title:'Sequential RTL requests are running',summary:'1/3 nodes processed.',primary:{label:'View generation batch',action:()=>{}}};
const running=resolve(context('local_rtl_generation',{record:{...accepted,execution_status:'Running'},activeOperation:{stage:'local_rtl_generation'},generationBatchGuidance}));
assert.equal(running.title,generationBatchGuidance.title);assert.equal(running.primary.label,'View generation batch');assert.match(running.summary,/1\/3/);
const recovery={title:'Reconnect to the saved generation batch',summary:'No request was resent.',primary:{label:'Reconnect without resending',action:()=>{}}};
const failed=resolve(context('local_rtl_generation',{activeOperation:{stage:'local_rtl_generation'},generationBatchGuidance:recovery,reconnect:'generation-reconnect'}));
assert.equal(failed.title,recovery.title);assert.equal(failed.primary.label,recovery.primary.label);
const readonly=resolve(context('local_rtl_generation',{readOnly:true,generationBatchGuidance}));assert.equal(readonly.title,'Inspect preserved evidence');
const dirty=resolve(context('local_rtl_generation',{dirty:true,generationBatchGuidance}));assert.equal(dirty.primary.testId,'save-project');
""")

    def test_s05_bulk_repair_is_next_action_and_tool_configuration_keeps_inspection(self):
        self.run_client(r"""
const failed={...accepted,validation_status:'Failed',review_status:'Awaiting Review'};
const summary={total:11,accepted:8,firstFailed:{id:'pe00',name:'PE 0,0'}};
const bulk=resolve(context('local_synthesis',{record:failed,synthesisSummary:summary,synthesisRepairCount:3,synthesisRepairGate:''}));
assert.equal(bulk.primary.testId,'workflow-batch-repair-all');assert.equal(bulk.primary.disabled,false);assert.match(bulk.summary,/8\/11.*3 failed.*together/);
const blocked=resolve(context('local_synthesis',{record:failed,synthesisSummary:summary,synthesisRepairCount:3,synthesisRepairGate:'Save the provider settings first.'}));
assert.equal(blocked.primary.disabled,true);assert.equal(blocked.summary,'Save the provider settings first.');
const tool=resolve(context('local_synthesis',{record:failed,synthesisSummary:summary,synthesisRepairCount:0,repairAvailable:false}));
assert.equal(tool.primary.kind,'inspect');assert.notEqual(tool.primary.testId,'workflow-batch-repair-all');assert.equal(tool.secondary.stage,'local_rtl_generation');
const historical=resolve(context('local_synthesis',{record:failed,historical:true,synthesisSummary:summary,synthesisRepairCount:3}));assert.equal(historical.primary.kind,'latest');
""")

    def test_s06_structured_checker_blocker_reports_accepted_synthesis_and_preserves_node(self):
        self.run_client(r"""
for(const gate of ['Checker build support is absent.','S06 netlist verification is unavailable: The saved specification has no supported behavioral checker.']) {
 const result=resolve(context('local_netlist_simulation',{gate,nodeId:'fifo',nodeName:'Output FIFO',blocker:{kind:'implementation_required',message:gate}}));
 assert.equal(result.title,'Not implemented · S06 behavioral checker');
 assert.equal(result.summary,gate);assert.match(result.detail,/S05 synthesis is accepted/);
 assert.equal(result.primary.stage,'specifications');assert.equal(result.primary.nodeId,'fifo');
 assert.equal(result.primary.label,'Inspect saved requirements');assert.equal(result.secondary.label,'Inspect accepted S05 netlist');
 assert.notEqual(result.primary.kind,'control');assert.doesNotMatch(result.primary.label,/Run|Generate|synthesis/);
 assert.equal(result.secondary.nodeId,'fifo');neverAdvance(result,'local_netlist_simulation');
}
""")

    def test_s06_structured_input_tool_and_prerequisite_blockers_have_distinct_actions(self):
        self.run_client(r"""
const guide=kind=>resolve(context('local_netlist_simulation',{nodeId:'fifo',gate:'Specific blocker',blocker:{kind,message:'Specific blocker',readiness:{message:'Original readiness detail'}}}));
const input=guide('input_required');assert.equal(input.primary.stage,'specifications');assert.match(input.title,/verification inputs/);
assert.equal(input.primary.nodeId,'fifo');assert.equal(input.summary,'Original readiness detail');
const tool=guide('configuration_required');assert.equal(tool.primary.stage,'global_settings');assert.match(tool.title,/simulator/);
const candidate=guide('candidate_required');assert.equal(candidate.primary.stage,'local_rtl_generation');
const synthesis=guide('synthesis_required');assert.equal(synthesis.primary.stage,'local_synthesis');assert.match(synthesis.title,/Prerequisites missing/);
for(const result of [input,tool,candidate,synthesis]) {assert.notEqual(result.primary.kind,'control');neverAdvance(result,'local_netlist_simulation');}
const s05=resolve(context('local_synthesis',{blocker:{kind:'implementation_required'},nodeId:'fifo'}));
assert.equal(s05.primary.testId,'workflow-run'); // S06 readiness must not gate S05.
""")

    def test_s06_checker_blocker_does_not_override_read_only_dirty_or_active_guards(self):
        self.run_client(r"""
const base={nodeId:'fifo',gate:'Specific checker limit',blocker:{kind:'implementation_required'}};
const readonly=resolve(context('local_netlist_simulation',{...base,readOnly:true}));assert.equal(readonly.primary.kind,'inspect');
const dirty=resolve(context('local_netlist_simulation',{...base,dirty:true}));assert.equal(dirty.primary.testId,'save-project');
const active=resolve(context('local_netlist_simulation',{...base,activeOperation:{stage:'local_synthesis',nodeId:'fifo'}}));
assert.equal(active.primary.stage,'local_synthesis');assert.match(active.title,/progress/);
""")

    def test_node_success_preserves_selection_and_s07_routes_to_remaining_node(self):
        self.run_client(r"""
for(const stage of ['local_synthesis','local_netlist_simulation']) {
 const result=resolve(context(stage,{record:{...accepted},nodeId:'scheduler',nodeName:'2x2 scheduler'}));
 assert.equal(result.primary.stage,next(stage));assert.equal(result.primary.nodeId,'scheduler');
 assert.match(result.summary,/selected node.*Other nodes/);
}
const result=resolve(context('node_implementation_specs',{record:{...accepted},nodeId:'control',nodeName:'Job control',nextNode:{id:'scheduler',name:'2x2 scheduler'}}));
assert.equal(result.primary.stage,'node_implementation_specs');assert.equal(result.primary.nodeId,'scheduler');
assert.match(result.primary.label,/Derive specification/);assert.match(result.summary,/Continue in S07/);
assert.equal(result.secondary.stage,'global_rtl_generation');assert.match(result.title,/remaining specifications/);
""")

    def test_accepted_records_do_not_override_changed_required_sources_or_runtime_gate(self):
        self.run_client(r"""
for(const [stage,prerequisite] of tools) {
 const result=resolve(context(stage,{record:{...accepted},gate:'The required source is no longer accepted.'}));
 assert.equal(result.primary.stage,prerequisite,JSON.stringify(result));neverAdvance(result,stage);
 const runtime=resolve(context(stage,{record:{...accepted},gate:'The configured tool runtime is unavailable.',configurationBlocked:true}));
 assert.equal(runtime.primary.kind,'inspect');assert.equal(runtime.primary.target,'stage-content');neverAdvance(runtime,stage);
}
""")

    def test_global_generation_requires_preview_before_explicit_model_request(self):
        self.run_client(r"""
const fresh=resolve(context('global_rtl_generation'));assert.equal(fresh.primary.testId,'global-context-preview');
const previewed=resolve(context('global_rtl_generation',{previewReady:true}));assert.equal(previewed.primary.testId,'global-generate');
assert.match(previewed.summary,/explicitly send/);
const blocked=resolve(context('global_rtl_generation',{gate:'Current adopted specifications are missing.',prerequisite:'node_implementation_specs',previewReady:true}));
assert.equal(blocked.primary.stage,'node_implementation_specs');assert.notEqual(blocked.primary.testId,'global-generate');
""")

    def test_mixed_revision_blocker_does_not_bounce_back_to_completed_s07(self):
        self.run_client(r"""
for (const record of [undefined, {...accepted}, {...accepted,freshness:'Stale',review_status:'Awaiting Review'}]) {
 const result=resolve(context('global_rtl_generation',{record,sourceRevisionConflict:true,gate:'Saved sources use different revisions.',prerequisite:'node_implementation_specs'}));
 assert.equal(result.primary.kind,'inspect');assert.equal(result.primary.target,'review-content');
 assert.equal(result.secondary.testId,'global-refresh');assert.match(result.detail,/does not regenerate RTL/);
 assert.notEqual(result.tone,'success');
}
const guarded=resolve(context('global_rtl_generation',{sourceRevisionConflict:true,dirty:true}));
assert.equal(guarded.primary.testId,'save-project');
const ordinary=resolve(context('global_rtl_generation',{gate:'Adopt missing node specifications.',prerequisite:'node_implementation_specs'}));
assert.equal(ordinary.primary.stage,'node_implementation_specs');
""")

    def test_continuation_uses_existing_guarded_button_and_explains_next_stage_block(self):
        self.run_client(r"""
const current=resolve(context('global_synthesis',{record:{...accepted},continueTestId:'global-workflow-continue'}));
assert.equal(current.primary.kind,'control');assert.equal(current.primary.testId,'global-workflow-continue');
const blocked=resolve(context('node_implementation_specs',{record:{...accepted},continueBlocked:'S08 currently integrates the six declared NPU node types.',continueTestId:'implementation-continue'}));
assert.notEqual(blocked.tone,'success');assert.notEqual(blocked.primary.testId,'implementation-continue');
assert.equal(blocked.primary.stage,'global_rtl_generation');assert.match(blocked.primary.label,/Inspect/);
assert.match(blocked.summary,/six declared/);
""")

    def test_integration_support_limit_is_visible_in_every_dependent_stage(self):
        self.run_client(r"""
for (const [stage] of stages.slice(7)) {
 const result=resolve(context(stage,{integrationUnsupported:'S08 currently integrates the six declared NPU node types.'}));
 assert.equal(result.tone,'warning');
 assert.match(result.detail,/Completing node checks alone will not remove/);
 assert.equal(result.primary.stage,stage==='global_rtl_generation'?'specifications':'global_rtl_generation');
 assert.notEqual(result.primary.kind,'control');
}
""")

    def test_empty_editor_points_to_its_existing_add_control(self):
        self.run_client(r"""
const result=resolve(context('graph_editor',{emptyGraph:true}));
assert.equal(result.primary.testId,'add-node');
assert.equal(resolve(context('specifications',{emptyGraph:true})).primary.stage,'graph_editor');
""")

    def test_s14_final_evidence_is_not_tapeout_approval_and_unsupported_does_not_complete(self):
        self.run_client(r"""
const final=resolve(context('post_layout_verification',{record:{...accepted}}));
assert.equal(final.primary.kind,'inspect');assert.equal(final.secondary.testId,'workspace-home');
assert.match(final.summary,/scope, remaining limitations/);
assert.match(final.detail,/does not establish foundry qualification or tapeout approval/);
const unsupported=resolve(context('post_layout_verification',{record:{...accepted,validation_status:'Unsupported',review_status:'Awaiting Review'}}));
assert.equal(unsupported.primary.kind,'inspect');assert.notEqual(unsupported.tone,'success');
assert.doesNotMatch(unsupported.title,/completed|ready/i);
const diagnostic=resolve(context('post_layout_verification',{record:{...accepted},completionBlocked:'Saved diagnostic review has unsupported timing semantics and cannot establish final completion.'}));
assert.notEqual(diagnostic.tone,'success');assert.equal(diagnostic.primary.kind,'inspect');
assert.match(diagnostic.summary,/unsupported timing/);assert.doesNotMatch(diagnostic.title,/completed evidence/);
""")


    def test_environment_or_unchecked_s05_failure_retries_same_rtl_not_model_repair(self):
        self.run_client(r"""
for(const error of [{code:'workflow_environment_error',next_action:'retry_same_RTL'}, {code:'workflow_error'}]) {
 const record={id:'failed',stage_id:'local_synthesis',execution_status:'Failed',validation_status:'Not Checked',freshness:'Current',error,checks:{}};
 const before=JSON.stringify(record),result=resolve(context('local_synthesis',{record,synthesisRepairCount:0}));
 assert.equal(result.primary.testId,'workflow-batch-run');assert.match(result.primary.label,/same RTL/);
 assert.doesNotMatch(result.primary.label,/repair|generate/i);assert.match(result.detail,/does not regenerate RTL/);assert.equal(JSON.stringify(record),before);
 if(error.code==='workflow_error')assert.match(result.summary,/cause is not established/);
 const gated=resolve(context('local_synthesis',{record,synthesisBatchGate:'Wait for active work'}));assert.equal(gated.primary.disabled,true);
}
const actual=resolve(context('local_synthesis',{record:{stage_id:'local_synthesis',execution_status:'Completed',validation_status:'Failed',freshness:'Current',checks:{executed:true}},synthesisRepairCount:2}));
assert.equal(actual.decisionId,'s05_bulk_repair');assert.equal(actual.primary.testId,'workflow-batch-repair-all');
""")


if __name__ == "__main__":
    unittest.main()

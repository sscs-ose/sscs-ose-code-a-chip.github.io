"""Read-only S04 guidance and explicit navigation; synthetic software fixtures only."""
from pathlib import Path
import shutil
import subprocess
import unittest

from test_generation_recovery_gui import CLIENT
from test_saved_rtl_verification_gui import SAVED_CANDIDATE

PROJECT = Path(__file__).resolve().parents[1]
SETUP = r"""
const navigations=[];callbacks.navigate=(...args)=>navigations.push(args);
const ready={status:'ready',available:true,message:'Saved specification checks are available.',code:null,needed_user_action:false};
const unsupported={status:'implementation_required',available:false,code:'verification_implementation_required',message:'The saved specification exists, but its behavioral checker is not implemented. Development is required.',needed_user_action:false};
const readiness=value=>{workspace.generation.nodes[0].behavioral_verification=value;failed.behavioral_verification=value;workspace.render(host);};
responder=()=>assert.fail('Guidance and navigation must not send requests');
const queueRepair=async()=>{
 workspace.prepareRepair(failed,'Keep the ports and remove the initial block.');
 workspace.preview={revision_id:'revision-a',node_id:'node-a',profile_revision_id:'profile-a',context_id:'repair-context',estimated_input_tokens:100};workspace.previewStale=false;
 const queued={...structuredClone(failed),...workspace.requestPayload(),id:'job-repair-'+(requests.filter(row=>row[0]==='generation/start').length+1),context_id:'repair-context',execution_status:'Queued',finished_at:null,rtl:null,checks:{},review_status:'Awaiting Review'};
 responder=async(route,body)=>{assert.equal(route,'generation/start');queued.submission_id=body.submission_id;return{generation_submission:{version:'node-submission-v1',submission_id:body.submission_id,job_id:queued.id,replayed:false},generation:{...workspace.generation,jobs:[failed,queued],latest_job_id:queued.id,nodes:[{node_id:'node-a',latest_job_id:queued.id,review_status:'Awaiting Review',freshness:'Current'}]}};};
 await workspace.startGeneration();return queued;
};
const finishRepair=(queued,patch={})=>{
 const result={...queued,execution_status:'Completed',finished_at:'2026-10-14T00:00:00Z',rtl:'module qa_control; endmodule',checks:{interface:{validation_status:'Passed'}},review_status:'Accepted',...patch};
 workspace.receive({generation:{...workspace.generation,jobs:[failed,result],latest_job_id:result.id,nodes:[{node_id:'node-a',latest_job_id:result.id,review_status:result.review_status,freshness:'Current'}]}});return result;
};
"""


class GenerationGuidanceGuiTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for isolated client checks.")
        result = subprocess.run(
            [node, "-e", CLIENT + "\n" + SAVED_CANDIDATE + "\n" + SETUP +
             "\n(async()=>{\n" + body +
             "\nconsole.log('Passed: S04 next-action guidance');\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});"],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_behavior_checker_does_not_block_s04_or_prompt_implementation(self):
        self.run_client(r"""
const original=JSON.stringify(failed);readiness(unsupported);
failed.saved_rtl_verification={available:false,code:unsupported.code,message:unsupported.message};workspace.renderResult();
const guide=workspace.guidance();assert.equal(guide.title,'Review the RTL for synthesis');
assert.match(guide.summary,/S04 external-interface check passed.*S05.*S06/);
assert.equal(guide.primary.label,'Open candidate review');assert.equal(test('verify-saved-rtl'),null);
assert.equal(test('saved-rtl-verification'),null);assert.equal(test('generation-behavioral-not-run'),null);
assert.doesNotMatch(text(test('generation-readiness')),/Checker implementation|awaits checker/);
assert.doesNotMatch(text(test('generation-progress-node-a')),/Checker implementation/);
assert.match(text(test('generation-stage-scope')),/S05.*S06/);assert.equal(requests.length,0);
assert.equal(JSON.parse(original).rtl,failed.rtl);assert.equal(failed.verification_plan_error.code,'verification_contract_missing');
""")

    def test_behavior_support_does_not_gate_pre_generation_preview(self):
        self.run_client(r"""
workspace.generation.jobs=[];workspace.generation.nodes[0].latest_job_id=null;workspace.selectedJobId=null;
for(const value of [unsupported,{status:'input_required',available:false,message:'Missing behavioral contract'},{status:'configuration_required',available:false,message:'Compiler not configured'},ready]) {
 readiness(value);assert.equal(workspace.guidance().primary.label,'Context Preview');
 assert.equal(workspace.guidance().primary.disabled,false);assert.match(text(test('generation-readiness')),/external port names, directions and widths.*S05.*S06/);
 assert.equal(test('verify-saved-rtl'),null);
}
assert.equal(requests.length,0);
""")

    def test_saved_rtl_adoption_does_not_need_an_llm_or_behavior_adapter(self):
        self.run_client(r"""
readiness(unsupported);workspace.llm={profile:null,profile_revision_id:null,probe:null};
const guide=workspace.guidance();assert.equal(guide.primary.label,'Open candidate review');
const review=new DOMDouble('div');workspace.renderReview(review);
assert.equal(review.querySelector('[data-testid="accept-candidate"]').disabled,false);
assert.equal(requests.length,0);
""")

    def test_accepted_node_keeps_selected_node_synthesis_and_next_node_separate(self):
        self.run_client(r"""
readiness(unsupported);failed.review_status='Accepted';workspace.generation.nodes[0].review_status='Accepted';workspace.generation.nodes[0].freshness='Current';
const guide=workspace.guidance();
assert.equal(guide.primary.label,'Next unfinished node: Other node');assert.match(guide.summary,/S06/);
guide.secondary.action();assert.equal(JSON.stringify(navigations[0]),JSON.stringify(['local_synthesis','node-a']));
guide.primary.action();assert.equal(workspace.nodeId,'node-b');
assert.equal(requests.length,0);
""")

    def test_successful_repair_consumes_only_its_submitted_draft_and_targets_output_fifo(self):
        self.run_client(r"""
project.design.nodes[1].name='OutputFIFO';const original=JSON.stringify(failed);
const queued=await queueRepair();assert.equal(workspace.operation,'repair');assert.equal(workspace.previewStale,false);
finishRepair(queued);
assert.equal(workspace.operation,'generate');assert.equal(workspace.baseJobId,null);assert.equal(workspace.retryOfJobId,null);
assert.equal(workspace.instruction,'');assert.equal(workspace.preview,null);assert.equal(workspace.previewStale,true);
assert.equal(test('generate-node').disabled,true);assert.equal(test('generate-node').textContent,'Generate node RTL');
const guide=workspace.guidance();assert.equal(guide.primary.label,'Next unfinished node: OutputFIFO');
assert.equal(guide.secondary.label,'Continue this node to S05');assert.doesNotMatch(guide.title,/repair/i);
guide.primary.action();assert.equal(workspace.nodeId,'node-b');assert.equal(workspace.selectedJob(),undefined);
assert.equal(workspace.guidance().primary.label,'Context Preview');assert.equal(requests.length,1);
assert.equal(JSON.stringify(failed),original);assert.equal(workspace.generation.jobs.length,2);
""")

    def test_next_unfinished_node_immediately_refreshes_shared_guide_and_status(self):
        self.run_client(r"""
project.design.nodes[1].name='Output FIFO';failed.review_status='Accepted';workspace.generation.nodes[0].review_status='Accepted';workspace.generation.nodes[0].freshness='Current';
const observed=[];callbacks.chrome=()=>{assert.ok(observed.length<8,'Shared chrome refresh must not recurse');workspace.refreshGenerationActions();observed.push({node:workspace.nodeId,job:workspace.selectedJob()?.id||null,guide:workspace.guidance().primary.label});};
workspace.guidance().primary.action();
assert.equal(workspace.nodeId,'node-b');assert.equal(test('generation-node').value,'node-b');assert.equal(workspace.selectedJob(),undefined);
assert.match(text(host.querySelector('#generation-result-content')),/No generated candidate/);
assert.ok(observed.length>0);assert.deepEqual(observed.at(-1),{node:'node-b',job:null,guide:'Context Preview'});
assert.equal(requests.length,0);
""")

    def test_ungenerated_node_status_does_not_inherit_aggregate_or_previous_node_pass(self):
        self.run_client(r"""
failed.review_status='Accepted';workspace.generation.nodes[0].review_status='Accepted';workspace.generation.nodes[0].freshness='Current';
const stageHost=new DOMDouble('div');const aggregate={execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current'};
const stageText=()=>text(stageHost).replace(/\s+/g,' ').trim();
Object.assign(sandbox,{state:{stage:'local_rtl_generation'},generation:workspace,byId:()=>stageHost,dirty:()=>false,workflowStage:()=>aggregate,statusIcon:kind=>el('svg',{'data-icon':kind})});
const app=fs.readFileSync('src/gui/app.js','utf8');
installStatusPresentation(app);
vm.runInContext(app.slice(app.indexOf('function renderStageStatus()'),app.indexOf('\nfunction render()')),sandbox);
callbacks.chrome=()=>vm.runInContext('renderStageStatus();',sandbox);callbacks.chrome();
assert.match(stageText(),/EXECUTION Completed.*VALIDATION Passed.*ADOPTION Accepted/);
workspace.guidance().primary.action();
assert.equal(workspace.nodeId,'node-b');assert.match(stageText(),/EXECUTION Not Run.*VALIDATION Not Checked.*ADOPTION Not requested.*INPUT Current/);
assert.doesNotMatch(stageText(),/Completed|Passed|Accepted/);
workspace.selectedJobId=failed.id;callbacks.chrome();
assert.match(stageText(),/EXECUTION Not Run.*VALIDATION Not Checked/);assert.equal(requests.length,0);
""")

    def test_local_history_header_marks_earlier_source_without_rewriting_record(self):
        self.run_client(r"""
const app=fs.readFileSync('src/gui/app.js','utf8');
const record={id:'old-record',execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current'};
const original=JSON.stringify(record);const stageHost=new DOMDouble('div');let current=false;
const localSourceView={selected:()=>record,runCurrent:()=>current};
Object.assign(sandbox,{state:{stage:'local_synthesis'},generation:workspace,localFlow:localSourceView,implementationSpecs:localSourceView,byId:()=>stageHost,dirty:()=>false,workflowStage:()=>null,statusIcon:kind=>el('svg',{'data-icon':kind})});
installStatusPresentation(app);
vm.runInContext(app.slice(app.indexOf('function renderStageStatus()'),app.indexOf('\nfunction render()')),sandbox);
for(const stage of ['local_synthesis','local_netlist_simulation','node_implementation_specs']){
 sandbox.state.stage=stage;current=false;vm.runInContext('renderStageStatus();',sandbox);
 const shown=text(stageHost).replace(/\s+/g,' ').trim();
 assert.match(shown,/Completed.*Passed.*Accepted.*INPUT Earlier source/);
 const input=stageHost.querySelector('[data-testid="stage-execution-details"]').children[1].children.at(-1);assert.equal(input.children[1].class,'badge warning');
 current=true;vm.runInContext('renderStageStatus();',sandbox);assert.match(text(stageHost).replace(/\s+/g,' '),/INPUT Current/);
}
assert.equal(JSON.stringify(record),original);assert.equal(requests.length,0);
""")

    def test_all_nodes_accepted_routes_to_s05_without_another_model_request(self):
        self.run_client(r"""
const queued=await queueRepair();finishRepair(queued);
workspace.generation.nodes.push({node_id:'node-b',latest_job_id:'other-job',review_status:'Accepted',freshness:'Current'});
const guide=workspace.guidance();assert.equal(guide.primary.label,'Continue this node to S05');assert.equal(guide.secondary,undefined);
assert.match(guide.summary,/All node RTL is accepted/);guide.primary.action();
assert.equal(JSON.stringify(navigations.at(-1)),JSON.stringify(['local_synthesis','node-a']));assert.equal(requests.length,1);
""")

    def test_successful_repair_waits_for_terminal_checks_then_allows_manual_review(self):
        self.run_client(r"""
const queued=await queueRepair();finishRepair(queued,{finished_at:null,review_status:'Awaiting Review'});
assert.equal(workspace.operation,'repair');assert.equal(workspace.preview.context_id,'repair-context');
assert.equal(workspace.guidance().primary.label,'View active request');
finishRepair(queued,{review_status:'Awaiting Review'});
assert.equal(workspace.operation,'generate');assert.equal(workspace.preview,null);
assert.equal(workspace.guidance().primary.label,'Open candidate review');assert.equal(requests.length,1);
""")

    def test_unsent_future_correction_or_repreview_is_preserved_after_success(self):
        self.run_client(r"""
let queued=await queueRepair();test('generation-instruction').change('A new unsent correction');
finishRepair(queued);assert.equal(workspace.operation,'repair');assert.equal(workspace.instruction,'A new unsent correction');assert.equal(workspace.previewStale,true);
assert.equal(workspace.guidance().primary.label,'Context Preview');
workspace.selectNode('node-a');queued=await queueRepair();const futurePreview={...workspace.preview};workspace.preview=futurePreview;
finishRepair(queued);assert.equal(workspace.operation,'repair');assert.equal(workspace.preview,futurePreview);
assert.equal(workspace.guidance().primary.label,'Repair node RTL');assert.equal(requests.length,2);
""")

    def test_failed_repair_keeps_repair_context_and_failed_result(self):
        self.run_client(r"""
const queued=await queueRepair();finishRepair(queued,{checks:{interface:{validation_status:'Failed'}},review_status:'Awaiting Review'});
assert.equal(workspace.operation,'repair');assert.equal(workspace.baseJobId,failed.id);assert.equal(workspace.preview.context_id,'repair-context');
assert.equal(workspace.selectedJob().checks.interface.validation_status,'Failed');assert.equal(workspace.submittedRequest,null);
assert.match(workspace.guidance().title,/repair/i);assert.equal(requests.length,1);
""")

    def test_explicit_identical_repair_after_success_is_not_cleared_by_refresh(self):
        self.run_client(r"""
const queued=await queueRepair();finishRepair(queued);assert.equal(workspace.submittedRequest,null);
workspace.prepareRepair(failed,'Keep the ports and remove the initial block.');
workspace.preview={revision_id:'revision-a',node_id:'node-a',profile_revision_id:'profile-a',context_id:'repair-context',estimated_input_tokens:100};workspace.previewStale=false;
workspace.receive({generation:workspace.generation});
assert.equal(workspace.operation,'repair');assert.equal(workspace.preview.context_id,'repair-context');assert.equal(workspace.previewStale,false);
assert.equal(workspace.guidance().primary.label,'Repair node RTL');assert.equal(requests.length,1);
""")

    def test_successful_request_cannot_clear_a_different_profile_source_or_context(self):
        self.run_client(r"""
const queued=await queueRepair();const snapshot=workspace.submittedRequest;
for(const patch of [{context_id:'foreign-context'},{profile_revision_id:'foreign-profile'},{revision_id:'foreign-revision'},{instruction:'Foreign instruction'},{base_job_id:'different-base'}]){
 workspace.submittedRequest=snapshot;finishRepair(queued,patch);assert.equal(workspace.operation,'repair');assert.equal(workspace.preview.context_id,'repair-context');
}
workspace.submittedRequest=snapshot;workspace.profileDraft.name='Future provider edit';finishRepair(queued);
assert.equal(workspace.profileDraft.name,'Future provider edit');assert.equal(workspace.operation,'repair');assert.equal(requests.length,1);
""")

    def test_successful_retry_clears_its_lineage_and_consumed_preview(self):
        self.run_client(r"""
failed.execution_status='Failed';failed.rtl=null;failed.checks={};failed.error={category:'stream_incomplete'};
workspace.prepareRetry(failed);assert.equal(workspace.retryOfJobId,failed.id);
workspace.preview={revision_id:'revision-a',node_id:'node-a',profile_revision_id:'profile-a',context_id:'retry-context',estimated_input_tokens:100};workspace.previewStale=false;
const queued={...structuredClone(failed),...workspace.requestPayload(),id:'job-retry',context_id:'retry-context',execution_status:'Queued',finished_at:null};
responder=async(route,body)=>{queued.submission_id=body.submission_id;return{generation_submission:{version:'node-submission-v1',submission_id:body.submission_id,job_id:queued.id,replayed:false},generation:{...workspace.generation,jobs:[failed,queued],latest_job_id:queued.id,nodes:[{node_id:'node-a',latest_job_id:queued.id,freshness:'Current'}]}};};
await workspace.startGeneration();finishRepair(queued);
assert.equal(workspace.retryOfJobId,null);assert.equal(workspace.preview,null);assert.equal(workspace.operation,'generate');
assert.equal(workspace.guidance().primary.label,'Next unfinished node: Other node');assert.equal(requests.length,1);
""")

    def test_poll_success_consumes_repair_before_project_refresh_without_replay(self):
        self.run_client(r"""
const queued=await queueRepair();const result={...queued,execution_status:'Completed',finished_at:'2026-10-14T00:00:00Z',rtl:'module qa_control; endmodule',checks:{interface:{validation_status:'Passed'}},review_status:'Accepted'};
responder=async(route)=>{
 if(route===`generation/jobs/${queued.id}`)return result;
 assert.equal(route,'project');assert.equal(workspace.preview,null);assert.equal(workspace.operation,'generate');
 return{generation:{...workspace.generation,nodes:[{node_id:'node-a',latest_job_id:result.id,review_status:'Accepted',freshness:'Current'}]}};
};
await workspace.pollJob();assert.equal(workspace.selectedJobId,result.id);assert.equal(workspace.preview,null);
assert.equal(workspace.guidance().primary.label,'Next unfinished node: Other node');
assert.equal(requests.length,3);assert.equal(requests.filter(([route])=>route==='generation/start').length,1);
""")

    def test_workspace_switch_discards_submission_tracking_without_consuming_foreign_draft(self):
        self.run_client(r"""
const queued=await queueRepair();project.envelope.workspace_identity.session_id='session-b';
workspace.receive({generation:workspace.generation});assert.equal(workspace.submittedRequest,null);assert.equal(workspace.preview,null);
workspace.operation='repair';workspace.baseJobId='foreign-base';workspace.instruction='Foreign unsent correction';
workspace.preview={context_id:'foreign-preview'};finishRepair(queued);
assert.equal(workspace.baseJobId,'foreign-base');assert.equal(workspace.instruction,'Foreign unsent correction');
assert.equal(workspace.preview.context_id,'foreign-preview');assert.equal(requests.length,1);
""")

    def test_interface_failure_routes_to_diagnostics_and_explicit_repair(self):
        self.run_client(r"""
readiness(unsupported);failed.checks.interface={validation_status:'Failed',diagnostics:[{code:'missing_port',message:'The declared output port is absent.'}]};
const guide=workspace.guidance();assert.equal(guide.primary.label,'View failed checks');guide.primary.action();
assert.equal(workspace.artifactTab,'checks');guide.secondary.action();assert.equal(workspace.operation,'repair');
assert.equal(workspace.baseJobId,'job-failed');assert.match(workspace.instruction,/missing_port/);
assert.equal(workspace.guidance().primary.label,'Context Preview');assert.equal(requests.length,0);
""")

    def test_historical_behavior_failure_is_retained_but_not_required_in_s04(self):
        self.run_client(r"""
failed.validation_status='Failed';failed.checks.behavioral={validation_status:'Failed',executed:true,diagnostics:[{code:'old_behavior',message:'Saved old failure'}]};
readiness(unsupported);const original=JSON.stringify(failed);
assert.equal(workspace.validationLabel(failed),'Passed');assert.equal(workspace.guidance().primary.label,'Open candidate review');
workspace.artifactTab='checks';workspace.renderResult();assert.match(text(test('candidate-checks')),/old_behavior/);
assert.equal(JSON.stringify(failed),original);assert.equal(requests.length,0);
""")

    def test_stale_candidate_routes_to_current_source_request(self):
        self.run_client(r"""
readiness(unsupported);failed.freshness='Stale';failed.revision_id='old-revision';
const guide=workspace.guidance();assert.equal(guide.primary.label,'Prepare current-source request');guide.primary.action();
assert.equal(workspace.selectedJob(),undefined);assert.equal(workspace.preview,null);
assert.equal(workspace.guidance().primary.label,'Context Preview');assert.equal(requests.length,0);
""")

    def test_readonly_and_running_states_have_inspection_only_actions(self):
        self.run_client(r"""
readiness(unsupported);project.envelope.workspace_identity.read_only=true;
assert.equal(workspace.guidance().title,'Inspect preserved evidence');
project.envelope.workspace_identity.read_only=false;failed.execution_status='Running';failed.finished_at=null;
const guide=workspace.guidance();assert.equal(guide.primary.label,'View active request');guide.primary.action();
assert.equal(requests.length,0);assert.equal(workspace.selectedJobId,'job-failed');
""")

    def test_preview_and_send_remain_distinct_user_actions(self):
        self.run_client(r"""
readiness(unsupported);workspace.generation.jobs=[];workspace.selectedJobId=null;
let previewed=0,generated=0;workspace.previewContext=()=>previewed++;workspace.startGeneration=()=>generated++;
const guide=workspace.guidance();assert.equal(guide.primary.label,'Context Preview');guide.primary.action();
assert.equal(previewed,1);assert.equal(generated,0);
workspace.preview={profile_revision_id:'profile-a',estimated_input_tokens:100};workspace.previewStale=false;
const prepared=workspace.guidance();assert.equal(prepared.primary.label,'Generate node RTL');prepared.primary.action();
assert.equal(generated,1);assert.equal(requests.length,0);
""")

    def test_chrome_refresh_does_not_recurse(self):
        self.run_client(r"""
readiness(unsupported);let chromeCalls=0;callbacks.chrome=()=>{assert.ok(++chromeCalls<5,'Recursive chrome callback');workspace.refreshGenerationActions();workspace.guidance();};
workspace.refreshGenerationActions();assert.equal(chromeCalls,0);
test('generation-instruction').change('Explicit user edit');assert.equal(chromeCalls,1);
assert.equal(requests.length,0);
""")

    def test_earliest_input_prerequisite_still_gates_generation(self):
        self.run_client(r"""
readiness(unsupported);project.envelope.workflow.reverse();
for(const stage of project.envelope.workflow)stage.review_status='Awaiting Review';
let guide=workspace.guidance();assert.equal(guide.primary.label,'Open Global Settings');guide.primary.action();
assert.equal(navigations.at(-1)[0],'global_settings');
project.envelope.workflow.find(stage=>stage.id==='global_settings').review_status='Accepted';
guide=workspace.guidance();assert.equal(guide.primary.label,'Open Graph Editor');
project.envelope.workflow.find(stage=>stage.id==='graph_editor').review_status='Accepted';
guide=workspace.guidance();assert.equal(guide.primary.label,'Open Specifications');guide.primary.action();
assert.equal(navigations.at(-1)[1],'node-a');
project.envelope.workflow.find(stage=>stage.id==='specifications').review_status='Accepted';
assert.equal(workspace.guidance().primary.label,'Open candidate review');assert.equal(requests.length,0);
""")

    def test_provider_configuration_only_gates_new_generation_or_repair(self):
        self.run_client(r"""
readiness(unsupported);workspace.generation.jobs=[];workspace.selectedJobId=null;
workspace.llm.profile_revision_id=null;
let guide=workspace.guidance();assert.equal(guide.primary.label,'Open LLM provider settings');assert.ok(!guide.primary.disabled);
guide.primary.action();assert.equal(navigations.at(-1)[0],'global_settings');
workspace.llm.profile_revision_id='profile-a';workspace.profileDraft.name='Unsaved provider edit';
guide=workspace.guidance();assert.equal(guide.title,'Save the edited provider settings');
workspace.generation.jobs=[failed];workspace.selectedJobId=failed.id;workspace.llm.profile_revision_id=null;
assert.equal(workspace.guidance().primary.label,'Open candidate review');
workspace.operation='repair';workspace.baseJobId=failed.id;workspace.instruction='Explicit correction';
assert.equal(workspace.guidance().primary.label,'Open LLM provider settings');assert.equal(requests.length,0);
""")

    def test_backend_stage_validation_is_authoritative(self):
        self.run_client(r"""
readiness(unsupported);failed.stage_validation={stage_id:'local_rtl_generation',scope:'external_interface',validation_status:'Not Checked',available:false};
assert.equal(workspace.validationLabel(failed),'Not Checked');
const review=new DOMDouble('div');workspace.renderReview(review);
assert.equal(review.querySelector('[data-testid="accept-candidate"]').disabled,true);
assert.equal(requests.length,0);
""")

    def test_main_stage_header_does_not_dispatch_behavior_checks_from_s04(self):
        source = (PROJECT / "src/gui/app.js").read_text(encoding="utf-8")
        self.assertNotIn("generation.verifySavedRTL", source)
        self.assertNotIn("Run behavioral verification", source)
        self.assertIn("byId('run-verification').hidden = state.stage === 'local_rtl_generation'", source)



if __name__ == "__main__":
    unittest.main()

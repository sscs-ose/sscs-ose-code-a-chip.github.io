"""Isolated recovery-client checks; fixtures are software behavior, never circuit proof."""
from pathlib import Path
import shutil
import subprocess
import unittest

PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
class DOMDouble {
  constructor(tag,attributes={}) {this.tag=tag;this.children=[];this.isConnected=true;this.dataset={};Object.assign(this,attributes);}
  append(...children) {this.children.push(...children.flat(Infinity).filter(child=>child!==null&&child!==undefined&&child!==false));}
  prepend(...children) {this.children.unshift(...children);}
  replaceChildren(...children) {assert.equal(children.some(child=>child===null||child===undefined),false,'Native replaceChildren would turn optional null into visible text');this.children=[];this.append(...children);}
  contains(node) {return this.children.some(child=>child===node||child instanceof DOMDouble&&child.contains(node));}
  querySelector(selector) {
    const matches=node=>node instanceof DOMDouble && (selector.startsWith('#') ? node.id===selector.slice(1) : node['data-testid']===selector.match(/^\[data-testid="([^"]+)"\]$/)?.[1]);
    for(const child of this.children) {if(matches(child))return child;const found=child instanceof DOMDouble&&child.querySelector(selector);if(found)return found;}
    return null;
  }
}
const el=(tag,attributes={},...children)=>{const node=new DOMDouble(tag,attributes);node.append(...children);return node;};
const requests=[],notices=[],adopted=[];let responder;
const project={envelope:{workspace_identity:{session_id:'session-a',project_id:'project-a',system_id:'system-a',read_only:false},revision:{id:'revision-a'},workflow:['global_settings','graph_editor','specifications'].map(id=>({id,label:id,review_status:'Accepted',freshness:'Current'}))},design:{id:'design-a',nodes:[{id:'node-a',name:'Job control',module_name:'qa_control'},{id:'node-b',name:'Other node',module_name:'qa_other'}]},stage:'local_rtl_generation',dirty:false,conflict:null,busy:false};
const sandbox={el,field:(label,value,change,options)=>el('input',{...options,value,change}),badge:(text,tone)=>el('span',{text,tone}),downloadJsonResponse:()=>{},structuredClone,URL,document:{activeElement:null},setTimeout:()=>1,clearTimeout:()=>{}};
vm.createContext(sandbox);
const operatorSource=fs.readFileSync('src/gui/review_operator.js','utf8').replace(/^import[^\n]+\n/gm,'').replace(/export /g,'');
vm.runInContext('{'+operatorSource+'\nglobalThis.adoptionProvenance=adoptionProvenance;}',sandbox);
vm.runInContext('{'+fs.readFileSync('src/gui/availability.js','utf8').replace(/export /g,'')+'\nglobalThis.availabilityReason=availabilityReason;}',sandbox);
const availabilitySource=fs.readFileSync('src/gui/availability.js','utf8').replace(/export /g,'');
vm.runInContext('{'+availabilitySource+'\nglobalThis.availabilityReason=availabilityReason;}',sandbox);
const promptViewSource=fs.readFileSync('src/gui/prompt_view.js','utf8').replace(/^import[^\n]+\n/gm,'').replace(/export /g,'');
vm.runInContext(promptViewSource,sandbox);
const source=fs.readFileSync('src/gui/generation.js','utf8').replace(/^import[^\n]+\n/gm,'').replace('export class GenerationWorkspace','class GenerationWorkspace');
vm.runInContext(source+'\nglobalThis.qa={GenerationWorkspace,PROFILE_DEFAULTS,cleanProfile};',sandbox);
const callbacks={project:()=>project,request:(...args)=>{requests.push(args);return responder(...args);},envelope:response=>{adopted.push(response);workspace.receive(response);},toast:message=>notices.push(message),notify:message=>notices.push(message)};
const workspace=new sandbox.qa.GenerationWorkspace(callbacks);
const savedProfile={...sandbox.qa.PROFILE_DEFAULTS,context_window:16384,timeout_seconds:181,temperature:.1,seed:87,model_revision:'qa-manifest',extra_provider_metadata:'preserve every saved field'};
const failed={id:'job-failed',node_id:'node-a',revision_id:'revision-a',input_hash:'qa-input',profile_revision_id:'profile-a',profile:structuredClone(savedProfile),context:{estimated_input_tokens:8148,messages:[{role:'user',content:'QA original specification'}]},operation:'generate',base_job_id:null,instruction:'Original human instruction',parameters:{max_tokens:2048},origin:'local_llm',execution_status:'Failed',validation_status:'Not Checked',review_status:'Awaiting Review',freshness:'Current',finished_at:'2026-10-13T00:00:00Z',created_at:'2026-10-13T00:00:00Z',error:{category:'output_truncated',message:'Output limit reached'},raw_content:'',raw_reasoning:'QA reasoning only',finish_reason:'length',usage:{prompt_tokens:1807,completion_tokens:2048},events:[],rtl:null};
workspace.receive({llm:{profile:savedProfile,profile_revision_id:'profile-a',probe:null},generation:{implemented:true,submission_protocol_version:'node-submission-v1',jobs:[failed],nodes:[{node_id:'node-a',latest_job_id:failed.id}],reviews:[]}});
const host=new DOMDouble('div');workspace.render(host);
const test=id=>host.querySelector(`[data-testid="${id}"]`);
const text=node=>node instanceof DOMDouble?[node.text||node.textContent||'',...node.children.map(text)].join(' '):String(node||'');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const deferred=()=>{let resolve,reject;const promise=new Promise((r,j)=>{resolve=r;reject=j;});return{promise,resolve,reject};};
const saveResponder=async(route,body)=>{assert.equal(route,'llm/profile');return{llm:{profile:structuredClone(body.profile),profile_revision_id:'profile-recovery',probe:null}};};
function installStatusPresentation(app) {
 DOMDouble.prototype.setAttribute=function(name,value){this[name]=String(value);};
 Object.assign(sandbox,{stageInputDirty:()=>false,physicalDraftDirty:()=>false,executionState:{overlay:()=>null},
  localFlow:{busy:false,batches:[],runs:[],...sandbox.localFlow}});
 sandbox.state.design=project.design;
 Object.defineProperty(sandbox.state,'envelope',{get:()=>({...project.envelope,generation:workspace.generation})});
 for(const [file,exports] of [['visual_state.js','globalThis.stageVisualState=stageVisualState;'],['stage_visuals.js','globalThis.stagePresentation=stagePresentation;globalThis.stageOverviewFacts=stageOverviewFacts;']])
  vm.runInContext('{'+fs.readFileSync('src/gui/'+file,'utf8').replace(/^import[^\n]+\n/gm,'').replace(/export /g,'')+'\n'+exports+'}',sandbox);
 vm.runInContext(app.slice(app.indexOf('function stageVisual(id)'),app.indexOf('const byId =')),sandbox);
}
"""


class GenerationRecoveryGuiTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for focused recovery-client checks.")
        result = subprocess.run(
            [node, "-e", CLIENT + "\n(async()=>{\n" + body +
             "\nconsole.log('Passed: explicit generation recovery UI');\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});"],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_failure_explains_reasoning_only_and_preserves_actual_usage_without_network(self):
        self.run_client(r"""
assert.equal(requests.length,0);assert.equal(workspace.preview,null);
assert.match(text(test('recovery-advice')),/Output limit reached.*4,096.*thinking disabled/);
assert.match(text(test('recovery-stats')),/completion tokens: 2048.*output limit: 2048.*answer characters: 0.*reasoning characters: 17/);
assert.equal(test('recovery-max-output').value,2048);assert.equal(test('recovery-thinking-control').value,'');
assert.equal(test('save-recovery-settings').disabled,true);assert.equal(test('prepare-retry').disabled,false);
assert.equal(test('recovery-max-output').max,8236);assert.equal(test('recovery-details').tag,'details');assert.ok(!test('recovery-details').open);
test('apply-recovery-suggestion').onclick();
assert.equal(test('recovery-max-output').value,4096);assert.equal(test('recovery-thinking-control').value,'none');
assert.equal(test('save-recovery-settings').disabled,false);assert.equal(test('prepare-retry').disabled,true);assert.equal(requests.length,0);
assert.equal(failed.raw_reasoning,'QA reasoning only');assert.equal(failed.rtl,null);
""")

    def test_save_prepare_preview_and_start_are_separate_and_keep_failed_job(self):
        self.run_client(r"""
const original=JSON.stringify(failed);workspace.applyRecoveryRecommendation(failed);responder=saveResponder;
await workspace.saveRecoverySettings(failed);
assert.equal(requests.length,1);assert.equal(requests[0][0],'llm/profile');
const submitted=requests[0][1];assert.equal(submitted.expected_profile_revision_id,'profile-a');
for(const [key,value] of Object.entries(savedProfile)) if(!['max_output_tokens','reasoning_effort'].includes(key))assert.deepEqual(submitted.profile[key],value);
assert.equal(submitted.profile.max_output_tokens,4096);assert.equal(submitted.profile.reasoning_effort,'none');
assert.equal(workspace.llm.profile_revision_id,'profile-recovery');assert.equal(workspace.preview,null);assert.equal(workspace.previewStale,true);
assert.equal(test('prepare-retry').disabled,false);workspace.prepareRetry(failed);
assert.equal(requests.length,1);assert.equal(workspace.retryOfJobId,failed.id);assert.equal(workspace.instruction,failed.instruction);
assert.equal(test('generate-node').disabled,true);assert.equal(test('generate-node').textContent,'Retry node RTL');
responder=async(route,body)=>{assert.equal(route,'generation/context');assert.equal(body.retry_of_job_id,failed.id);assert.equal(body.instruction,'Original human instruction');assert.equal('raw_reasoning' in body,false);return{...body,profile_revision_id:'profile-recovery',context_id:'preview-retry',estimated_input_tokens:8148,token_estimate_method:'qa-only',prompt_text:'QA saved specification'};};
await workspace.previewContext();assert.equal(requests.length,2);assert.equal(test('generate-node').disabled,false);
responder=async(route,body)=>{assert.equal(route,'generation/start');assert.equal(body.retry_of_job_id,failed.id);assert.equal(body.context_id,'preview-retry');const retry={...structuredClone(failed),...body,profile:structuredClone(workspace.llm.profile),id:'job-retry',retry_of_job_id:failed.id,execution_status:'Completed',validation_status:'Unsupported',error:null,raw_reasoning:'',raw_content:'QA candidate only'};return{generation_submission:{version:'node-submission-v1',submission_id:body.submission_id,job_id:retry.id,replayed:false},generation:{...workspace.generation,jobs:[failed,retry],latest_job_id:retry.id}};};
await workspace.startGeneration();assert.equal(requests.length,3);assert.equal(JSON.stringify(failed),original);assert.equal(workspace.generation.jobs.length,2);
assert.match(text(test('generation-retry-lineage')),/Retry of job-failed/);assert.equal(workspace.selectedJob().validation_status,'Unsupported');
""")

    def test_recovery_gates_prevent_dirty_readonly_busy_stale_and_budget_overflow(self):
        self.run_client(r"""
responder=()=>assert.fail('No blocked action may contact the service');
const blocked=[
 ()=>project.dirty=true,()=>project.conflict='external revision',()=>project.busy=true,
 ()=>project.envelope.workspace_identity.read_only=true,()=>workspace.requestBusy=true,
 ()=>workspace.profileBusy=true,()=>workspace.generation.storage_error={message:'disk unavailable'},
 ()=>workspace.profileDraft.name='unsaved provider edit',()=>failed.freshness='Stale',
 ()=>failed.revision_id='older revision',()=>workspace.generation.jobs.push({...failed,id:'active',execution_status:'Running'}),
 ()=>workspace.recoveryDraft(failed).max_output_tokens=16000,
];
for(const change of blocked) {
  project.dirty=false;project.conflict=null;project.busy=false;project.envelope.workspace_identity.read_only=false;
  workspace.requestBusy=false;workspace.profileBusy=false;delete workspace.generation.storage_error;workspace.profileDraft=sandbox.qa.cleanProfile(workspace.llm.profile);
  failed.freshness='Current';failed.revision_id='revision-a';workspace.generation.jobs=[failed];workspace.recoveryDrafts.clear();
  change();assert.notEqual(workspace.recoveryGate(failed,true),'');await workspace.saveRecoverySettings(failed);workspace.prepareRetry(failed);assert.equal(workspace.retryOfJobId,null);
}
assert.equal(requests.length,0);
""")

    def test_unsaved_provider_draft_is_never_overwritten_by_recovery(self):
        self.run_client(r"""
workspace.profileDraft.base_url='http://localhost:9999/v1';const before=JSON.stringify(workspace.profileDraft);
responder=()=>assert.fail('Dirty provider draft must block recovery save');await workspace.saveRecoverySettings(failed);
assert.equal(requests.length,0);assert.equal(JSON.stringify(workspace.profileDraft),before);
workspace.profileDraft=sandbox.qa.cleanProfile(workspace.llm.profile);workspace.applyRecoveryRecommendation(failed);const pending=deferred();responder=()=>pending.promise;
const saving=workspace.saveRecoverySettings(failed);workspace.profileDraft.timeout_seconds=222;
pending.resolve({llm:{profile:{...savedProfile,max_output_tokens:4096,reasoning_effort:'none'},profile_revision_id:'profile-recovery',probe:null}});
await saving;assert.equal(workspace.profileDraft.timeout_seconds,222);assert.equal(workspace.profileDirty(),true);
""")

    def test_request_edits_cancel_retry_lineage_and_require_new_preview(self):
        self.run_client(r"""
workspace.applyRecoveryRecommendation(failed);responder=saveResponder;await workspace.saveRecoverySettings(failed);workspace.prepareRetry(failed);
workspace.preview={profile_revision_id:'profile-recovery',context_id:'old-preview',estimated_input_tokens:100};workspace.previewStale=false;
test('generation-instruction').change('A different instruction');assert.equal(workspace.retryOfJobId,null);assert.equal(workspace.previewStale,true);assert.equal('retry_of_job_id' in workspace.requestPayload(),false);
workspace.prepareRetry(failed);test('generation-operation').change('repair');assert.equal(workspace.retryOfJobId,null);
workspace.operation='generate';workspace.prepareRetry(failed);workspace.clearRetry();assert.equal(workspace.retryOfJobId,null);assert.equal(workspace.preview,null);
workspace.prepareRetry(failed);workspace.selectNode('node-b');assert.equal(workspace.retryOfJobId,null);assert.equal(workspace.preview,null);
""")

    def test_late_profile_and_preview_responses_cannot_cross_workspace_session(self):
        self.run_client(r"""
workspace.applyRecoveryRecommendation(failed);let pending=deferred();responder=()=>pending.promise;const saving=workspace.saveRecoverySettings(failed);
project.envelope.workspace_identity.session_id='session-b';
pending.resolve({llm:{profile:{...savedProfile,max_output_tokens:4096,reasoning_effort:'none'},profile_revision_id:'old-session-result'}});
await saving;assert.equal(adopted.length,0);assert.equal(workspace.llm.profile_revision_id,'profile-a');
workspace.profileBusy=false;pending=deferred();responder=()=>pending.promise;const previewing=workspace.previewContext();
project.envelope.workspace_identity.session_id='session-c';pending.resolve({revision_id:'revision-a',context_id:'old-session-preview'});
await previewing;assert.equal(workspace.preview,null);assert.equal(adopted.length,0);
""")

    def test_late_poll_job_and_project_envelopes_cannot_cross_workspace_session(self):
        self.run_client(r"""
let pending=deferred();responder=()=>pending.promise;
const polling=workspace.pollJob(true);project.envelope.workspace_identity.session_id='session-b';
pending.resolve({...structuredClone(failed),id:'old-session-job'});await polling;
assert.equal(workspace.generation.jobs.length,1);assert.equal(workspace.generation.jobs[0].id,'job-failed');assert.equal(adopted.length,0);
pending=deferred();responder=route=>route==='project'?pending.promise:Promise.resolve({...structuredClone(failed),raw_reasoning:'same-system refreshed output'});
const second=workspace.pollJob(true);await tick();assert.equal(requests.at(-1)[0],'project');
project.envelope.workspace_identity.session_id='session-c';pending.resolve({generation:{jobs:[{id:'foreign-job'}]}});await second;
assert.equal(adopted.length,0);assert.equal(workspace.generation.jobs.some(job=>job.id==='foreign-job'),false);
""")

    def test_retry_of_failed_repair_keeps_original_base_and_instruction(self):
        self.run_client(r"""
failed.operation='repair';failed.base_job_id='earlier-valid-candidate';failed.instruction='Fix the original reset mismatch';
workspace.generation.jobs.unshift({...structuredClone(failed),id:'earlier-valid-candidate',execution_status:'Completed',rtl:'QA prior candidate',base_job_id:null});
workspace.applyRecoveryRecommendation(failed);responder=saveResponder;await workspace.saveRecoverySettings(failed);workspace.prepareRetry(failed);
const payload=workspace.requestPayload();assert.equal(payload.operation,'repair');assert.equal(payload.base_job_id,'earlier-valid-candidate');
assert.equal(payload.instruction,'Fix the original reset mismatch');assert.equal(payload.retry_of_job_id,'job-failed');
assert.equal(JSON.stringify(payload).includes('QA reasoning only'),false);assert.equal(workspace.preview,null);assert.equal(requests.length,1);
""")

    def test_cancelled_interrupted_and_partial_answer_recover_without_reasoning_only_claim(self):
        self.run_client(r"""
for(const status of ['Cancelled','Interrupted']){failed.execution_status=status;failed.error=null;workspace.renderResult();assert.ok(test('generation-recovery'));assert.match(text(test('recovery-advice')),/request did not complete/);}
failed.execution_status='Failed';failed.error={category:'output_truncated'};failed.raw_content='module qa_control(';workspace.renderResult();
assert.match(text(test('recovery-advice')),/Output limit reached/);assert.doesNotMatch(text(test('recovery-advice')),/thinking disabled/);
failed.execution_status='Completed';workspace.renderResult();assert.equal(test('generation-recovery'),null);assert.equal(requests.length,0);
""")

    def test_profile_save_failure_is_visible_and_does_not_discard_preview_or_original_job(self):
        self.run_client(r"""
const original=JSON.stringify(failed);workspace.applyRecoveryRecommendation(failed);workspace.preview={context_id:'prior-preview'};
responder=async()=>{throw new Error('Profile version conflict');};await workspace.saveRecoverySettings(failed);
assert.match(notices.join(' '),/Profile version conflict/);assert.equal(workspace.profileBusy,false);assert.equal(workspace.preview.context_id,'prior-preview');
assert.equal(workspace.llm.profile_revision_id,'profile-a');assert.equal(JSON.stringify(failed),original);assert.equal(workspace.retryOfJobId,null);
""")

    def test_historical_missing_behavior_contract_is_saved_without_main_s04_gate(self):
        self.run_client(r"""
failed.execution_status='Completed';failed.validation_status='Passed';failed.error=null;failed.rtl='module qa_control; endmodule';
failed.verification_plan_error={code:'verification_contract_missing',message:'The original design has no structured behavioral verification contract.'};
failed.checks={interface:{validation_status:'Passed'},syntax:{validation_status:'Passed',executed:true},behavioral:{validation_status:'Not Run',executed:false,diagnostics:[{code:'behavioral_not_run',message:'Historical missing behavior checker'}]}};
const before=JSON.stringify(failed);workspace.renderResult();assert.equal(test('generation-behavioral-not-run'),null);
assert.equal(workspace.validationLabel(failed),'Passed');assert.match(text(test('generation-stage-scope')),/S05.*S06/);
workspace.artifactTab='events';workspace.renderResult();
assert.match(text(host.querySelector('#generation-result-content')),/verification_contract_missing/);
assert.equal(JSON.stringify(failed),before);assert.equal(requests.length,0);
""")

    def test_timeout_recovery_explains_deadline_and_saves_only_explicit_changes(self):
        self.run_client(r"""
failed.error={category:'timeout',message:'Provider request timed out'};failed.raw_content='module qa_control(';failed.finish_reason=null;failed.usage=null;
workspace.recoveryDrafts.clear();workspace.renderResult();
assert.equal(test('recovery-timeout').value,181);assert.equal(requests.length,0);
assert.match(text(test('recovery-timeout-explanation')),/timed out after 181 seconds/);
assert.match(text(test('recovery-timeout-explanation')),/does not establish that the output limit or the model's capacity was reached/);
assert.match(text(test('recovery-stats')),/completion tokens: Unknown/);
test('recovery-timeout').change(360);assert.equal(requests.length,0);assert.equal(test('prepare-retry').disabled,true);
responder=saveResponder;await workspace.saveRecoverySettings(failed);
assert.equal(requests.length,1);assert.equal(requests[0][0],'llm/profile');
for(const [key,value] of Object.entries(savedProfile)) if(key!=='timeout_seconds')assert.deepEqual(requests[0][1].profile[key],value);
assert.equal(requests[0][1].profile.timeout_seconds,360);assert.equal(workspace.retryOfJobId,null);
assert.equal(failed.profile.timeout_seconds,181);assert.equal(test('prepare-retry').disabled,false);
""")

    def test_timeout_bounds_and_serialized_budget_block_before_request(self):
        self.run_client(r"""
responder=()=>assert.fail('Blocked recovery must not contact the service');
for(const invalid of [0,.049,3601,Infinity,NaN]) {
  workspace.recoveryDraft(failed).timeout_seconds=invalid;
  assert.match(workspace.recoveryGate(failed,true),/Timeout must be a finite number/);
  await workspace.saveRecoverySettings(failed);
}
workspace.recoveryDraft(failed).timeout_seconds=.05;assert.equal(workspace.recoveryGate(failed,true),'');
workspace.recoveryDraft(failed).timeout_seconds=3600;assert.equal(workspace.recoveryGate(failed,true),'');
failed.provider_input_estimated_tokens=13000;workspace.recoveryDraft(failed).max_output_tokens=4096;workspace.renderResult();
assert.match(text(test('recovery-budget')),/input estimate 13,000.*max output 3,384/);assert.equal(test('recovery-max-output').max,3384);
assert.match(workspace.recoveryGate(failed,true),/exceeds the saved context window/);assert.equal(test('save-recovery-settings').disabled,true);
workspace.preview={profile_revision_id:'profile-a',estimated_input_tokens:100,provider_input_estimated_tokens:15000};workspace.previewStale=false;
assert.match(workspace.previewGate(),/exceeds the configured context window/);
delete workspace.preview.provider_input_estimated_tokens;assert.equal(workspace.previewGate(),'');assert.equal(requests.length,0);
""")

    def test_s04_policy_scope_requires_interface_but_defers_behavior_to_s06(self):
        self.run_client(r"""
failed.execution_status='Completed';failed.validation_status='Passed';failed.error=null;failed.rtl='QA complete candidate';
failed.checks={interface:{validation_status:'Passed'},syntax:{validation_status:'Not Run',executed:false},behavioral:{validation_status:'Not Run',executed:false}};
const review=new DOMDouble('div');workspace.renderReview(review);
const decision=id=>review.querySelector(`[data-testid="${id}"]`);
for(const mode of ['manual','accept_on_pass']) {
 project.envelope.review_policy={mode,user_authorized:true};workspace.renderReview(review);
 assert.equal(decision('accept-candidate').disabled,false);
}
for(const change of [()=>failed.checks.behavioral.executed=false,()=>failed.checks.behavioral.exit_code=1,()=>failed.checks.behavioral.vector_hash='c'.repeat(64),()=>failed.verification_plan_error={code:'verification_contract_missing'}]) {
  change();workspace.renderReview(review);assert.equal(decision('accept-candidate').disabled,false);
}
failed.checks.interface.validation_status='Failed';workspace.renderReview(review);
assert.equal(decision('accept-candidate').disabled,true);
assert.equal(requests.length,0);assert.equal(failed.review_status,'Awaiting Review');
""")

    def test_incomplete_stream_shows_actual_budget_and_same_settings_retry(self):
        self.run_client(r"""
failed.error={category:'stream_incomplete',message:'No normal finish received'};failed.provider_input_estimated_tokens=8829;
failed.raw_content='QA partial output';failed.raw_reasoning='';failed.usage=null;failed.finish_reason=null;
workspace.recoveryDrafts.clear();workspace.renderResult();
assert.equal(text(test('recovery-advice')).trim(),'No normal finish received. Retry with the same settings.');
assert.match(text(test('recovery-budget')),/Context 16,384.*input estimate 8,829.*max output 7,555/);
assert.equal(test('recovery-max-output').max,7555);assert.equal(test('apply-recovery-suggestion'),null);
assert.equal(test('prepare-retry').textContent,'Prepare retry with saved settings');assert.equal(test('prepare-retry').disabled,false);
assert.equal(text(test('recovery-gate')).trim(),'Next: Prepare retry with saved settings.');
assert.equal(test('reset-recovery-settings').disabled,true);assert.equal(test('recovery-timeout').min,.05);assert.equal(test('recovery-timeout').max,3600);
test('recovery-max-output').change(7555);assert.equal(test('save-recovery-settings').disabled,false);
test('recovery-max-output').change(7556);assert.equal(test('save-recovery-settings').disabled,true);assert.match(text(test('recovery-gate')),/1–7,555/);
test('reset-recovery-settings').onclick();assert.equal(test('recovery-max-output').value,2048);assert.equal(test('prepare-retry').disabled,false);
test('prepare-retry').onclick();assert.equal(workspace.retryOfJobId,failed.id);assert.equal(workspace.guidance().primary.label,'Context Preview');
assert.equal(text(test('recovery-gate')).trim(),'Next: Context Preview.');
workspace.preview={profile_revision_id:'profile-a',provider_input_estimated_tokens:8829};workspace.previewStale=false;workspace.refreshRecoveryActions();
assert.equal(text(test('recovery-gate')).trim(),'Next: Retry node RTL.');
assert.equal(requests.length,0);assert.equal(failed.parameters.max_tokens,2048);
""")

    def test_truncation_suggestion_fits_small_remaining_budget(self):
        self.run_client(r"""
failed.provider_input_estimated_tokens=13384;workspace.renderResult();
assert.equal(test('recovery-max-output').value,2048);assert.equal(test('recovery-max-output').max,3000);
assert.match(test('apply-recovery-suggestion').text,/3,000/);test('apply-recovery-suggestion').onclick();
assert.equal(test('recovery-max-output').value,3000);assert.equal(workspace.recoveryGate(failed,true),'');assert.equal(requests.length,0);
failed.provider_input_estimated_tokens=14336;workspace.llm.profile.reasoning_effort='none';workspace.profileDraft=sandbox.qa.cleanProfile(workspace.llm.profile);
workspace.recoveryDrafts.clear();workspace.renderResult();assert.equal(test('apply-recovery-suggestion'),null);
assert.match(text(test('recovery-advice')),/No larger output limit fits/);
assert.equal(test('recovery-max-output').value,2048);assert.equal(test('recovery-max-output').max,2048);
assert.equal(test('prepare-retry').disabled,false);assert.equal(requests.length,0);
""")

    def test_empty_fractional_and_configured_budget_boundaries(self):
        self.run_client(r"""
workspace.llm.profile.context_window=100000;workspace.profileDraft=sandbox.qa.cleanProfile(workspace.llm.profile);
failed.provider_input_estimated_tokens=0;assert.equal(workspace.recoveryBudget(failed).maxOutput,65536);
workspace.llm.profile.context_window=64;workspace.llm.profile.max_output_tokens=1;workspace.profileDraft=sandbox.qa.cleanProfile(workspace.llm.profile);
failed.provider_input_estimated_tokens=0;workspace.recoveryDrafts.clear();assert.equal(workspace.recoveryBudget(failed).maxOutput,63);
failed.provider_input_estimated_tokens=62.1;assert.equal(workspace.recoveryBudget(failed).maxOutput,1);
failed.provider_input_estimated_tokens=64;workspace.renderResult();assert.equal(test('recovery-max-output').max,0);
assert.equal(test('apply-recovery-suggestion'),null);assert.equal(test('prepare-retry').disabled,true);assert.match(text(test('recovery-gate')),/No output budget remains/);
assert.equal(requests.length,0);
""")

    def test_unknown_input_allows_saved_retry_preview_then_validated_settings(self):
        self.run_client(r"""
delete failed.context.estimated_input_tokens;failed.error={category:'stream_incomplete'};workspace.renderResult();
assert.match(text(test('recovery-budget')),/input estimate Unknown.*max output Unknown/);assert.equal(test('recovery-max-output').max,16383);
assert.equal(test('prepare-retry').disabled,false);assert.equal(test('apply-recovery-suggestion'),null);
test('recovery-max-output').change(4096);assert.equal(test('save-recovery-settings').disabled,true);
assert.match(text(test('recovery-gate')),/Input budget unknown/);test('reset-recovery-settings').onclick();workspace.prepareRetry(failed);
assert.equal(workspace.retryOfJobId,failed.id);assert.equal(workspace.guidance().primary.label,'Context Preview');
workspace.preview={profile_revision_id:'profile-a',provider_input_estimated_tokens:9000};workspace.previewStale=false;
workspace.renderResult();assert.equal(test('recovery-max-output').max,7384);assert.equal(workspace.guidance().primary.label,'Retry node RTL');
test('recovery-max-output').change(4096);assert.equal(test('save-recovery-settings').disabled,false);
workspace.previewStale=true;workspace.refreshRecoveryActions();assert.equal(test('save-recovery-settings').disabled,true);
assert.equal(requests.length,0);
""")

    def test_nonfinite_estimate_is_unknown_and_newer_request_blocks_retry(self):
        self.run_client(r"""
for(const value of [NaN,Infinity,-1,'8829']){failed.provider_input_estimated_tokens=value;assert.equal(workspace.recoveryBudget(failed).maxOutput,null);}
failed.provider_input_estimated_tokens=8829;workspace.generation.nodes[0].latest_job_id='newer-job';workspace.renderResult();
assert.equal(test('prepare-retry').disabled,true);assert.match(text(test('recovery-gate')),/newer request exists/);
workspace.prepareRetry(failed);assert.equal(workspace.retryOfJobId,null);assert.equal(requests.length,0);
""")


if __name__ == "__main__":
    unittest.main()

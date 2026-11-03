"""Real app S01-S03 review/validation handlers with isolated DOM and API doubles."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

PROJECT = Path(__file__).resolve().parents[1]
INSTANCES = []
CLIENT = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element {
 constructor(tag,attributes={}){this.tag=tag;this.children=[];Object.assign(this,attributes);}
 append(...children){this.children.push(...children.flat(Infinity).filter(x=>x!==null&&x!==undefined&&x!==false));}
 replaceChildren(...children){this.children=[];this.append(...children);}
 querySelector(selector){
  const matches=n=>n instanceof Element&&(selector.startsWith('#')?n.id===selector.slice(1):n['data-testid']===selector.match(/^\[data-testid="([^"]+)"\]$/)?.[1]);
  for(const n of this.children){if(matches(n))return n;const found=n instanceof Element&&n.querySelector(selector);if(found)return found;}return null;
 }
 focus(){focused=this;}
}
const el=(tag,attributes={},...children)=>{const n=new Element(tag,attributes);n.append(...children);return n;};
const hosts={'review-content':el('div'),'review-state':el('div')};
const calls=[],navigations=[],toasts=[],notices=[],instances=[],received=[],autosaves=[];
let focused,unsaved=false,flushes=0,protectedReadOnly=false,invalidDraft=false,apiSaveHook=null;
const state={stage:'global_settings',busy:false,feedback:{},returnTargets:{},externalRevision:null,envelope:null};
const inputs=['global_settings','graph_editor','specifications'];
const init=(stage,patch={})=>{
 state.stage=stage;state.busy=false;state.feedback={};state.returnTargets={};state.externalRevision=null;unsaved=false;focused=null;
 protectedReadOnly=false;invalidDraft=false;apiSaveHook=null;received.length=0;autosaves.length=0;
 state.design={id:'input-design',project:{name:'Saved design'},nodes:[]};state.saved=structuredClone(state.design);
 calls.length=0;navigations.length=0;toasts.length=0;notices.length=0;
 const run={id:'run-'+stage,stage_id:stage,execution_status:'Completed',validation_status:'Passed',review_status:'Awaiting Review',freshness:'Current',revision_id:'saved-revision',created_at:'2026-10-16T00:00:00Z',summary:'Isolated input checks',...patch};
 state.envelope={revision:{id:'saved-revision'},design:structuredClone(state.design),runs:[run],reviews:[],workflow:inputs.map(id=>({id,implemented:true,freshness:'Current',review_status:id===stage?run.review_status:'Accepted'}))};
 sandbox.renderReview();return run;
};
const test=id=>hosts['review-content'].querySelector(`[data-testid="${id}"]`);
const click=async id=>{const node=test(id);assert.ok(node,`Missing ${id}`);if(node.disabled)return false;await node.onclick();return true;};
const note=value=>{const field=test('review-note');field.value=value;field.oninput?.({target:field});};
const api=async(route,payload)=>{
 calls.push({route,payload:structuredClone(payload)});
 const response=structuredClone(state.envelope);
 if(route==='review'){
  const run=response.runs.find(r=>r.id===payload.run_id);assert.ok(run);
  const review={id:'review-'+calls.length,run_id:run.id,...payload,actor:'human'};response.reviews.push(review);
  run.review_status=({accepted:'Accepted',changes_requested:'Changes Requested',return_to_stage:'Returned'})[payload.decision];
  response.workflow.find(x=>x.id===run.stage_id).review_status=run.review_status;
 }else if(route==='validate'){
  assert.equal(payload.revision_id,response.revision.id);
  response.runs.push({id:'verified-'+calls.length,stage_id:payload.stage_id,execution_status:'Completed',validation_status:'Passed',review_status:'Awaiting Review',freshness:'Current',revision_id:payload.revision_id,summary:'Isolated API validation response'});
 }else if(route==='save'){
  if(apiSaveHook)return apiSaveHook(payload,response);
  assert.equal(payload.expected_revision_id,response.revision.id);
  response.revision={id:'saved-revision-next'};response.design=structuredClone(payload.design);
 }else assert.fail('Unexpected API route '+route);
 return response;
};
const sandbox={el,field:(label,value,change,options)=>el('select',{...options,value,change}),badge:(text,tone)=>el('span',{text,tone}),state,structuredClone,
 byId:id=>hosts[id]||hosts['review-content'].querySelector('#'+id),compactSnapshot:()=>false,
 dirty:()=>unsaved||JSON.stringify(state.design)!==JSON.stringify(state.saved),readOnly:()=>protectedReadOnly,invalidVerification:()=>invalidDraft,
 clone:structuredClone,equal:(a,b)=>JSON.stringify(a)===JSON.stringify(b),autosave:()=>autosaves.push(structuredClone(state.design)),
 workflowStage:id=>state.envelope.workflow.find(x=>x.id===id),stageRun:()=>state.envelope.runs.filter(x=>x.stage_id===state.stage).at(-1),
 formatDate:x=>x,renderHistory:()=>{},renderReviewState:()=>{},focusDiagnostic:()=>{},downloadJson:()=>{},flushActiveField:()=>flushes++,syncChrome:()=>{},
 executionInputDirty:()=>unsaved||JSON.stringify(state.design)!==JSON.stringify(state.saved),
 api,adopt:response=>{state.envelope=response;},setStage:stage=>{assert.ok(stage);navigations.push(stage);state.stage=stage;},
 toast:x=>toasts.push(x),notify:(...x)=>notices.push(x),generation:{selectedJob:()=>null,renderReview:()=>{},receive:r=>received.push({module:'generation',revision:r.revision.id})}};
for(const name of ['generationBatches','adoption','localFlow','implementationSpecs','globalGeneration','globalFlow','physicalFlow','drcFlow','lvsFlow','postlayoutFlow'])sandbox[name]={receive:r=>received.push({module:name,revision:r.revision.id})};
sandbox.physicalFlow.refreshDraftActions=()=>{};sandbox.blockFloorplan={host:null};
vm.createContext(sandbox);
// Review actions are exercised below; the independently tested status header is decorative here.
const operatorSource=fs.readFileSync('src/gui/review_operator.js','utf8').replace(/^import[^\n]+\n/gm,'').replace(/export /g,'');
vm.runInContext('{'+operatorSource+'\nglobalThis.adoptionProvenance=adoptionProvenance;}',sandbox);
const app=fs.readFileSync('src/gui/app.js','utf8');
const stageStart=app.indexOf('const STAGES = [');
vm.runInContext(app.slice(stageStart,app.indexOf('\n];',stageStart)+3),sandbox);
vm.runInContext(app.slice(app.indexOf('function renderReview()'),app.indexOf('\nfunction renderHistory(')),sandbox);
vm.runInContext(app.slice(app.indexOf('async function saveDesign()'),app.indexOf('\nasync function loadDesign()')),sandbox);
vm.runInContext(app.slice(app.indexOf('async function validate()'),app.indexOf('\nfunction attachCommands()')),sandbox);
"""


class InputTransitionActionsGuiTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node required for isolated DOM action checks.")
        tail = "\nconsole.log(JSON.stringify({scope:'Real app DOM onclick and handlers; isolated API responses, not circuit validation',instances}));\n})().catch(e=>{console.error(e.stack||e);process.exitCode=1});"
        result = subprocess.run([node, "-e", CLIENT + "\n(async()=>{\n" + body + tail],
                                cwd=PROJECT, capture_output=True, text=True, encoding="utf8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        INSTANCES.extend(report["instances"])
        return report

    def test_accept_and_continue_records_exact_review_and_advances_each_input_stage(self):
        self.client(r"""
for(const [i,stage] of inputs.entries()){
 const run=init(stage);note('  Checked saved input  ');assert.equal(test('accept-continue').disabled,false);
 await click('accept-continue');assert.equal(calls.length,1);assert.deepEqual(calls[0],{route:'review',payload:{run_id:run.id,decision:'accepted',note:'Checked saved input'}});
 assert.equal(navigations[0],[...inputs,'local_rtl_generation'][i+1]);assert.equal(state.busy,false);assert.equal(state.feedback[run.id],undefined);
 instances.push({id:`INPUT-accept-${i+1}`,from:stage,to:navigations[0],control:'accept-continue',api:'review',decision:'accepted',status:'Passed'});
}
""")

    def test_accepted_continue_does_not_create_another_adoption(self):
        self.client(r"""
for(const [i,stage] of inputs.entries()){
 init(stage,{review_status:'Accepted'});assert.equal(test('accept-continue').text,'Continue to next stage');
 await click('accept-continue');assert.equal(calls.length,0);assert.equal(navigations[0],[...inputs,'local_rtl_generation'][i+1]);
 instances.push({id:`INPUT-continue-${i+1}`,from:stage,to:navigations[0],control:'accept-continue',api_calls:0,status:'Passed'});
}
""")

    def test_request_changes_records_feedback_without_advancing(self):
        self.client(r"""
for(const [i,stage] of inputs.entries()){
 const run=init(stage);note('  Revise the saved constraint  ');await click('request-changes');
 assert.equal(calls.length,1);assert.deepEqual(calls[0].payload,{run_id:run.id,decision:'changes_requested',note:'Revise the saved constraint'});
 assert.equal(state.stage,stage);assert.equal(navigations.length,0);assert.equal(state.envelope.reviews[0].decision,'changes_requested');assert.equal(state.busy,false);
 instances.push({id:`INPUT-changes-${i+1}`,from:stage,to:stage,control:'request-changes',decision:'changes_requested',status:'Passed'});
}
""")

    def test_blank_change_or_return_reason_keeps_focus_and_sends_nothing(self):
        self.client(r"""
for(const [i,stage] of inputs.entries()){
 init(stage);note('   ');await click('request-changes');assert.equal(calls.length,0);assert.equal(focused.id,'review-note');assert.match(toasts.at(-1),/feedback note/);
 instances.push({id:`INPUT-blank-changes-${i+1}`,from:stage,to:stage,control:'request-changes',api_calls:0,status:'Passed'});
 if(i){focused=null;await click('return-to-stage');assert.equal(calls.length,0);assert.equal(focused.id,'review-note');assert.equal(navigations.length,0);
 instances.push({id:`INPUT-blank-return-${i+1}`,from:stage,to:stage,control:'return-to-stage',api_calls:0,status:'Passed'});}
}
""")

    def test_every_input_return_destination_is_selectable_and_recorded(self):
        self.client(r"""
for(const [from,targets] of [['graph_editor',['global_settings']],['specifications',['global_settings','graph_editor']]]){
 for(const target of targets){
  const run=init(from);const selector=test('return-stage');assert.deepEqual(Array.from(selector.choices,x=>x[0]),targets);
  selector.change(target);note('Return to correct the source');await click('return-to-stage');assert.equal(calls.length,1);
  assert.deepEqual(calls[0].payload,{run_id:run.id,decision:'return_to_stage',note:'Return to correct the source',target_stage:target});
  assert.equal(navigations[0],target);assert.equal(state.stage,target);assert.equal(state.busy,false);
  instances.push({id:`INPUT-return-${from}-${target}`,from,to:target,control:'return-to-stage',decision:'return_to_stage',status:'Passed'});
 }
}
init('global_settings');assert.equal(test('return-to-stage').disabled,true);assert.equal(test('return-stage').choices.length,0);
assert.equal(await click('return-to-stage'),false);assert.equal(calls.length,0);
instances.push({id:'INPUT-no-return-01',from:'global_settings',control:'return-to-stage',disabled:true,api_calls:0,status:'Passed'});
""")

    def test_rerun_uses_real_validate_handler_and_preserves_prior_input_history(self):
        self.client(r"""
for(const [i,stage] of inputs.entries()){
 const run=init(stage,{validation_status:'Failed'}),original=JSON.stringify(run);
 await click('rerun');assert.equal(calls.length,1);assert.deepEqual(calls[0],{route:'validate',payload:{stage_id:stage,revision_id:'saved-revision'}});
 assert.equal(state.envelope.runs.length,2);assert.equal(JSON.stringify(state.envelope.runs[0]),original);assert.equal(state.stage,stage);assert.equal(state.busy,false);
 assert.equal(test('accept-continue').disabled,false);assert.equal(state.envelope.reviews.length,0);
 instances.push({id:`INPUT-rerun-${i+1}`,from:stage,to:stage,control:'rerun',api:'validate',preserved_old_run:true,status:'Passed'});
}
""")

    def test_dirty_stale_failed_and_missing_prerequisite_disable_acceptance(self):
        self.client(r"""
for(const [id,patch,configure] of [
 ['dirty',{},()=>{unsaved=true;}],['stale',{freshness:'Stale'},()=>{}],['failed',{validation_status:'Failed'},()=>{}],
 ['conflict',{},()=>{state.externalRevision='other-revision';}],['previous',{},()=>{state.envelope.workflow[0].review_status='Awaiting Review';}]
]){
 init('specifications',patch);configure();sandbox.renderReview();assert.equal(test('accept-continue').disabled,true,id);
 await click('accept-continue');assert.equal(calls.length,0);assert.equal(navigations.length,0);
 instances.push({id:'INPUT-guard-'+id,from:'specifications',control:'accept-continue',disabled:true,api_calls:0,status:'Passed'});
}
""")

    def test_save_current_draft_records_revision_and_refreshes_all_views(self):
        self.client(r"""
init('global_settings');const original=structuredClone(state.saved);state.design.project.name='Edited draft';const submitted=structuredClone(state.design);
assert.equal(sandbox.dirty(),true);await sandbox.saveDesign();
assert.equal(calls.length,1);assert.deepEqual(calls[0],{route:'save',payload:{design:submitted,expected_revision_id:'saved-revision'}});
assert.equal(state.envelope.revision.id,'saved-revision-next');assert.deepEqual(state.saved,submitted);assert.deepEqual(state.design,submitted);
assert.equal(sandbox.dirty(),false);assert.equal(state.busy,false);assert.equal(state.externalRevision,null);
assert.equal(received.length,11);assert.ok(received.every(x=>x.revision==='saved-revision-next'));assert.equal(autosaves.length,1);
assert.equal(original.project.name,'Saved design');assert.match(toasts.at(-1),/Design saved/);
instances.push({id:'DRAFT-save-current',control:'save-project',handler:'saveDesign',api:'save',saved_revision:'saved-revision-next',dirty:false,receiver_count:11,status:'Passed'});
""")

    def test_save_keeps_newer_draft_edits_made_while_response_is_pending(self):
        self.client(r"""
init('global_settings');state.design.project.name='Submitted edit';let release;
apiSaveHook=async(payload,response)=>new Promise(resolve=>{release=()=>resolve({...response,revision:{id:'saved-revision-next'},design:structuredClone(payload.design)});});
const pending=sandbox.saveDesign();assert.equal(state.busy,true);assert.equal(calls.length,1);
state.design.project.name='Newer unsaved edit';release();await pending;
assert.equal(state.saved.project.name,'Submitted edit');assert.equal(state.envelope.design.project.name,'Submitted edit');
assert.equal(state.design.project.name,'Newer unsaved edit');assert.equal(sandbox.dirty(),true);assert.equal(state.busy,false);
assert.match(toasts.at(-1),/newer edits remain unsaved/);assert.equal(calls.length,1);
instances.push({id:'DRAFT-save-newer-edit',control:'save-project',handler:'saveDesign',api_calls:1,newer_draft_preserved:true,dirty:true,status:'Passed'});
""")

    def test_save_readonly_busy_invalid_or_clean_draft_sends_nothing(self):
        self.client(r"""
for(const [id,configure] of [['read_only',()=>{protectedReadOnly=true;}],['busy',()=>{state.busy=true;}],['invalid_json',()=>{invalidDraft=true;}],['clean',()=>{state.design=structuredClone(state.saved);} ]]){
 init('global_settings');state.design.project.name='Draft edit';configure();const original=JSON.stringify({envelope:state.envelope,design:state.design,saved:state.saved});
 await sandbox.saveDesign();assert.equal(calls.length,0,id);assert.equal(received.length,0);
 assert.equal(JSON.stringify({envelope:state.envelope,design:state.design,saved:state.saved}),original);
 instances.push({id:'DRAFT-save-guard-'+id,control:'save-project',handler:'saveDesign',api_calls:0,status:'Passed'});
}
""")

    def test_rejected_save_conflict_keeps_original_revision_and_current_draft(self):
        self.client(r"""
init('global_settings');state.design.project.name='Retained draft';state.externalRevision='newer-saved-revision';
const before=JSON.stringify({envelope:state.envelope,design:state.design,saved:state.saved});
apiSaveHook=async()=>{throw Object.assign(new Error('A newer saved revision exists; reopen or export this draft.'),{status:409});};
await sandbox.saveDesign();assert.equal(calls.length,1);assert.equal(calls[0].payload.expected_revision_id,'saved-revision');
assert.equal(JSON.stringify({envelope:state.envelope,design:state.design,saved:state.saved}),before);
assert.equal(state.externalRevision,'newer-saved-revision');assert.equal(state.busy,false);assert.equal(received.length,0);
assert.match(notices[0][0],/newer saved revision/);assert.equal(sandbox.dirty(),true);
instances.push({id:'DRAFT-save-conflict',control:'save-project',handler:'saveDesign',api_calls:1,http_status:409,original_revision_preserved:true,draft_preserved:true,status:'Passed'});
""")


if __name__ == "__main__":
    unittest.main()

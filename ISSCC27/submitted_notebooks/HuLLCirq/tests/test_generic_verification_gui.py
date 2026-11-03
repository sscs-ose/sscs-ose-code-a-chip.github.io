"""Generic-project presentation and explicit metadata saves; no live tools/API."""
import shutil
import subprocess
import unittest

from test_postlayout_workflow_gui import CLIENT, PROJECT
from test_flow_guidance import CLIENT as GUIDANCE_CLIENT
from test_functional_map_generation_gui import FIXTURE as MAP_CLIENT

ADAPTER = r"""
const adapter={version:'external-port-functional-v1',testbench_module:'custom_tb',dut_instance:'design_under_test',clock_signal:'clock_pin',clock_statement:'always #7 clock_pin = ~clock_pin;',timeout_statement:'initial begin #7000;',output_prefix:'MY_OUTPUT',pass_marker:'MY_PASS',failure_markers:['MY_FAIL']};
function adapterData(extra={}){return{...flow.data,adapter_contract:structuredClone(adapter),adapter_contract_sha256:'adapter-hash-a',adapter_contract_editable:true,adapter_contract_required:false,adapter_contract_reason:null,adapter_contract_fields:Object.keys(adapter),adapter_contract_source:'derived_saved_testbench',adapter_contract_original:{testbench:'SOFTWARE QA original custom testbench',expected_outputs:[17,23],clock_period_ns:14,top_module:'custom_design',verification_plan_sha256:'saved-plan-hash'},...extra};}
function installAdapter(extra={}){project.envelope.postlayout_workflow=adapterData(extra);flow.receive(project.envelope);}
function editAdapter(change){const value=JSON.parse(find('postlayout-adapter-contract').value);change(value);find('postlayout-adapter-contract').oninput({target:{value:JSON.stringify(value,null,2)}});return value;}
"""


class GenericVerificationClientTests(unittest.TestCase):
    def client(self, body, prefix=CLIENT + ADAPTER):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated generic verification checks.')
        completed = subprocess.run([node, '-e', prefix + '\n(async()=>{\n' + body +
                                   '\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});'],
                                  cwd=PROJECT, capture_output=True, text=True, encoding='utf-8', timeout=25)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_view_and_adapter_typing_do_not_save_or_modify_original_inputs(self):
        self.client(r"""
installAdapter();const original=JSON.stringify(flow.data.adapter_contract_original),design=JSON.stringify(project.design),saved=JSON.stringify(project.envelope);
assert.equal(requests.length,0);assert.equal(flow.adapterDirty(),false);assert.equal(find('postlayout-adapter-save').disabled,true);
editAdapter(value=>{value.pass_marker='SECOND_EXACT_MARKER';});assert.equal(requests.length,0);assert.equal(flow.adapterDirty(),true);
assert.equal(JSON.stringify(flow.data.adapter_contract_original),original);assert.equal(JSON.stringify(project.design),design);assert.equal(JSON.stringify(project.envelope),saved);
assert.match(text(find('postlayout-adapter-original')),/17[\s\S]*23/);assert.match(flow.gate(),/Save.*adapter/);
flow.refresh();assert.match(find('postlayout-adapter-contract').value,/SECOND_EXACT_MARKER/);assert.equal(requests.length,0);
""")

    def test_explicit_save_sends_exact_metadata_and_source_ids_not_testbench_or_goldens(self):
        self.client(r"""
installAdapter();const original=JSON.stringify(flow.data.adapter_contract_original),value=editAdapter(v=>{v.output_prefix='SECOND_OUTPUT';});
responder=async(route,body)=>{assert.equal(route,'postlayout-workflow/adapter-contract');return{...project.envelope,postlayout_workflow:adapterData({adapter_contract:body.contract,adapter_contract_sha256:'adapter-hash-b',adapter_contract_source:'saved_gui_contract'})};};
await flow.saveAdapterContract();assert.equal(requests.length,1);const body=requests[0].body;
assert.deepEqual(Object.keys(body).sort(),['contract','drc_run_id','layout_run_id','lvs_run_id','revision_id']);
assert.deepEqual(normalized(body.contract),value);assert.equal(body.layout_run_id,layout.id);assert.equal(body.drc_run_id,drc.id);assert.equal(body.lvs_run_id,lvs.id);assert.equal(body.revision_id,project.envelope.revision.id);
assert.equal(Object.hasOwn(body.contract,'expected_outputs'),false);assert.equal(Object.hasOwn(body.contract,'clock_period_ns'),false);assert.equal(Object.hasOwn(body.contract,'testbench'),false);
assert.equal(JSON.stringify(flow.data.adapter_contract_original),original);assert.equal(flow.adapterDirty(),false);assert.equal(flow.data.runs.length,0);
""")

    def test_invalid_or_forbidden_metadata_never_posts_and_draft_is_retained(self):
        self.client(r"""
installAdapter();for(const mutate of [v=>{v.expected_outputs=[0];},v=>{v.testbench='replacement';},v=>{v.clock_period_ns=1;},v=>{v.failure_markers=[];},v=>{v.clock_statement='';}]){
 const value=structuredClone(adapter);mutate(value);find('postlayout-adapter-contract').oninput({target:{value:JSON.stringify(value)}});
 const before=flow.adapterDraft().text;await flow.saveAdapterContract();assert.equal(requests.length,0);assert.equal(flow.adapterDraft().text,before);assert.equal(find('postlayout-adapter-save').disabled,true);
}
find('postlayout-adapter-contract').oninput({target:{value:'{broken'}});assert.equal(flow.adapterDirty(),true);await flow.saveAdapterContract();assert.equal(requests.length,0);
""")

    def test_failed_save_and_newer_edits_are_retained_without_automatic_resend(self):
        self.client(r"""
installAdapter();editAdapter(v=>{v.pass_marker='LOCAL_CHANGE';});responder=async()=>{throw Error('SOFTWARE QA interrupted metadata save');};
const before=flow.adapterDraft().text;await flow.saveAdapterContract();assert.equal(requests.length,1);assert.equal(flow.adapterDraft().text,before);assert.equal(flow.busy,false);assert.match(notices.at(-1)[0],/draft retained.*no save request is automatically resent/);
let resolve;responder=()=>new Promise(done=>{resolve=done;});const saving=flow.saveAdapterContract();const newer=flow.adapterDraft();newer.text=JSON.stringify({...adapter,pass_marker:'NEWER_BROWSER_EDIT'});
resolve({...project.envelope,postlayout_workflow:adapterData({adapter_contract:{...adapter,pass_marker:'LOCAL_CHANGE'},adapter_contract_sha256:'adapter-hash-b'})});await saving;
assert.equal(requests.length,2);assert.match(flow.adapterDraft().text,/NEWER_BROWSER_EDIT/);assert.equal(flow.adapterDirty(),true);assert.equal(flow.adapterDraft().baseHash,'adapter-hash-b');
""")

    def test_refreshed_saved_metadata_updates_clean_view_but_preserves_conflicting_draft(self):
        self.client(r"""
installAdapter();project.envelope.postlayout_workflow=adapterData({adapter_contract:{...adapter,output_prefix:'REMOTE_SAVED'},adapter_contract_sha256:'adapter-hash-b'});flow.receive(project.envelope);
assert.match(find('postlayout-adapter-contract').value,/REMOTE_SAVED/);assert.equal(flow.adapterDirty(),false);
editAdapter(v=>{v.pass_marker='LOCAL_KEEP';});const before=flow.adapterDraft().text;
project.envelope.postlayout_workflow=adapterData({adapter_contract:{...adapter,output_prefix:'REMOTE_NEWER'},adapter_contract_sha256:'adapter-hash-c'});flow.receive(project.envelope);
assert.equal(flow.adapterDraft().text,before);assert.match(flow.adapterSaveGate(),/saved adapter changed/);await flow.saveAdapterContract();assert.equal(requests.length,0);
""")

    def test_missing_contract_has_direct_settings_action_not_lvs_navigation(self):
        self.client(r"""
installAdapter({adapter_contract:null,adapter_contract_sha256:null,adapter_contract_required:true,adapter_contract_reason:'Declare the saved custom testbench markers.',profile_prepare_available:true,ready:false,tool_ready:false,layout_run_id:null,drc_run_id:null,lvs_run_id:null});
assert.equal(flow.adapterDirty(),false);assert.equal(flow.adapterBackupDirty(),false);
const blocker=flow.blocker();assert.equal(blocker.setup_action.testId,'postlayout-adapter-settings');assert.equal(flow.prepareGate(),'Declare the saved custom testbench markers.');
find('postlayout-adapter-settings').onclick();assert.equal(document.activeElement,find('postlayout-adapter-contract'));assert.equal(requests.length,0);
""")

    def test_self_describing_generic_cycle_adapter_needs_no_manual_metadata(self):
        self.client(r"""
installAdapter({adapter_contract:{version:'generic-cycle-functional-v1'},adapter_contract_editable:false,adapter_contract_fields:['version'],profile_prepare_available:true,profile_prepare_needed:true,tool_ready:false});
layout.verification_plan={kind:'generic_cycle_vectors',vector_count:12,coverage:{output_assertions:36},interface:{clock:{period_ns:30}}};flow.refresh();
assert.equal(find('postlayout-adapter-card').hidden,true);assert.equal(flow.adapterDirty(),false);assert.equal(flow.prepareGate(),'');assert.equal(flow.blocker().setup_action.testId,'postlayout-workflow-prepare');
assert.match(text(find('postlayout-workflow-lineage')),/12 saved cycles.*36 independent output-pin assertions.*30 ns saved clock/);assert.doesNotMatch(text(find('postlayout-workflow-lineage')),/K=|ReLU|PE|Not available.*Saved independent/);assert.equal(requests.length,0);
""")

    def test_metadata_browser_backup_is_exact_source_scoped_and_survives_session_reload(self):
        self.client(r"""
project.envelope.workspace_identity={project_id:'qa-project',system_id:'qa-system',session_id:'first'};installAdapter();editAdapter(v=>{v.pass_marker='LOCAL_RETAIN';});
const backup=JSON.parse(JSON.stringify(flow.adapterBackup()));assert.equal(backup.length,1);assert.equal(flow.adapterBackupDirty(),true);const original=JSON.stringify(flow.data.adapter_contract_original);
flow.adapterDrafts.clear();project.envelope.workspace_identity={project_id:'other-project',system_id:'qa-system',session_id:'other'};flow.restoreAdapterBackup(backup);assert.equal(flow.adapterDrafts.size,0);assert.equal(flow.adapterBackupDirty(),false);
project.envelope.workspace_identity={project_id:'qa-project',system_id:'other-system',session_id:'other'};flow.restoreAdapterBackup(backup);assert.equal(flow.adapterDrafts.size,0);
project.envelope.workspace_identity={project_id:'qa-project',system_id:'qa-system',session_id:'new'};flow.restoreAdapterBackup(backup);assert.equal(flow.adapterDrafts.size,1);assert.equal(flow.adapterDirty(),true);assert.match(flow.adapterDraft().text,/LOCAL_RETAIN/);
const parts=JSON.parse(flow.adapterKey()),old=JSON.parse(backup[0].key);assert.deepEqual(parts.slice(1),old.slice(1));assert.equal(parts[0].session_id,'new');assert.equal(JSON.stringify(flow.data.adapter_contract_original),original);assert.equal(requests.length,0);
""")

    def test_invalid_and_old_source_metadata_are_preserved_not_applied_to_new_sources(self):
        self.client(r"""
installAdapter();find('postlayout-adapter-contract').oninput({target:{value:'{unclosed exact text'}});const backup=flow.adapterBackup();assert.equal(backup[0].text,'{unclosed exact text');
const previous=flow.adapterKey();project.envelope.revision.id='new-saved-revision';flow.refresh();assert.notEqual(flow.adapterKey(),previous);assert.equal(flow.adapterDirty(),false);assert.equal(flow.adapterBackupDirty(),true);assert.equal(flow.adapterBackup()[0].text,'{unclosed exact text');
assert.equal(flow.data.adapter_contract.pass_marker,adapter.pass_marker);assert.equal(requests.length,0);
""")

    def test_adapter_only_edit_uses_browser_backup_and_context_export_guard_without_post(self):
        self.client(r"""
installAdapter();editAdapter(v=>{v.pass_marker='EXACT_BACKUP_ONLY';});
const storage=new Map(),exports=[],listeners={},body=new DOMDouble('body');
DOMDouble.prototype.addEventListener=function(name,callback){(this.listeners??={})[name]=callback;};
DOMDouble.prototype.showModal=function(){this.open=true;};DOMDouble.prototype.close=function(value){this.returnValue=value;this.listeners.close();};
const state={design:{schema_version:'0.1',project:{name:'QA'}},envelope:{revision:{id:project.envelope.revision.id}},verificationDrafts:{},busy:false};
const controller={busy:false},generation={profileDirty:()=>false,profileBusy:false,requestBusy:false,profileDraft:null},adoption={dirty:()=>false,busy:false,draft:null};
const s=vm.createContext({state,postlayoutFlow:flow,dirty:()=>false,generation,adoption,activeWorkspace:{project_id:'qa-project',system_id:'qa-system'},DRAFT_KEY:'qa-scoped-draft',
 localStorage:{setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)},flushActiveField(){},readOnly:()=>false,invalidVerification:()=>false,
 localFlow:controller,globalGeneration:controller,globalFlow:controller,physicalFlow:controller,drcFlow:controller,lvsFlow:controller,
 el,document:{body},downloadJson:value=>exports.push(value),notify(){throw Error('No warning expected');},saveDesign(){throw Error('Must not silently save metadata/design');},
 window:{addEventListener:(name,callback)=>listeners[name]=callback}});
const app=fs.readFileSync('src/gui/app.js','utf8'),helper=app.match(/^const adapterDraftDirty = .*;$/m)[0],save=app.slice(app.indexOf('function autosave() {'),app.indexOf('function loadRecoveredDrafts(')),leave=app.slice(app.indexOf('async function preserveBeforeContextChange() {'),app.indexOf('function configureBrowserScope(')),unload=app.match(/window.addEventListener\('beforeunload', event => \{[\s\S]*?\n  \}\);/)[0];
vm.runInContext(helper+'\n'+save+'\n'+leave+'\n'+unload+'\nglobalThis.qa={autosave,preserveBeforeContextChange};',s);
s.qa.autosave();assert.equal(JSON.parse(storage.get('qa-scoped-draft')).postlayout_adapter_drafts[0].text,flow.adapterDraft().text);
const event={preventDefault(){this.prevented=true;}};listeners.beforeunload(event);assert.equal(event.prevented,true);
const pending=s.qa.preserveBeforeContextChange();const controls=descend(body);assert.equal(controls.find(n=>n['data-testid']==='workspace-save-and-continue').disabled,true);
controls.find(n=>n['data-testid']==='workspace-export-and-continue').onclick();assert.equal(await pending,true);assert.equal(exports.length,1);assert.equal(exports[0].postlayout_adapter_drafts[0].text,flow.adapterDraft().text);assert.equal(requests.length,0);
""")

    def test_readonly_active_and_context_changes_guard_metadata_writes(self):
        self.client(r"""
installAdapter();editAdapter(v=>{v.pass_marker='LOCAL';});project.envelope.workspace_identity={project_id:'first',read_only:true};flow.refresh();await flow.saveAdapterContract();assert.equal(requests.length,0);
project.envelope.workspace_identity={project_id:'first',read_only:false};flow.refresh();editAdapter(v=>{v.pass_marker='LOCAL';});flow.data.runs=[record('active')];flow.data.runs[0].execution_status='Running';await flow.saveAdapterContract();assert.equal(requests.length,0);flow.data.runs=[];
let resolve;responder=()=>new Promise(done=>{resolve=done;});const pending=flow.saveAdapterContract();const old=project.envelope;
project.envelope={...old,workspace_identity:{project_id:'second'}};resolve({...old,postlayout_workflow:adapterData({adapter_contract_sha256:'old-response'})});await pending;
assert.equal(project.envelope.workspace_identity.project_id,'second');assert.equal(requests.length,1);
""")

    def test_prepare_blocker_and_non_npu_job_summary_use_actual_saved_fields(self):
        self.client(r"""
layout.verification_plan={output_count:2,recipe:{source_job:{id:'custom-job'}}};installAdapter({profile_prepare_available:true,profile_prepare_needed:true,tool_ready:false});
assert.equal(flow.blocker().setup_action.testId,'postlayout-workflow-prepare');assert.doesNotMatch(text(find('postlayout-workflow-lineage')),/K=undefined|ReLU not reported/);
assert.match(text(find('postlayout-workflow-lineage')),/custom-job.*2 expected outputs/);assert.equal(requests.length,0);
""")

    def test_guidance_targets_profile_or_adapter_controls_even_after_invalidation(self):
        self.client(r"""
for(const testId of ['postlayout-workflow-prepare','postlayout-adapter-settings','postlayout-adapter-save']){
 const answer=resolve(context('post_layout_verification',{gate:'Configure project verification metadata.',blocker:{kind:'configuration_required',message:'Configure project verification metadata.',setup_action:{label:'Configure here',testId}},executionOverlay:{invalidated:true,status:'Not run'}}));
 assert.equal(answer.primary.kind,'control');assert.equal(answer.primary.testId,testId);assert.notEqual(answer.primary.stage,'lvs');
}
const guarded=resolve(context('post_layout_verification',{readOnly:true,blocker:{setup_action:{label:'Configure',testId:'postlayout-workflow-prepare'}}}));assert.equal(guarded.decisionId,'read_only');
""", GUIDANCE_CLIENT)

    def test_functional_map_backend_capability_is_not_gated_by_node_count_or_project_name(self):
        self.client(r"""
for(const count of [1,3,8,11,17,100]){const f=setup();f.project().design={name:'Generic custom design',nodes:Array.from({length:count},(_,i)=>({id:'custom-'+i,module_name:'module_'+i}))};
await f.lookup({...result(f.record.id),capability:'generic_saved_source_v1'});assert.equal(f.flow.mapGenerationGate(f.record),'');
assert.ok(f.find('functional-map-generation-capability'));assert.equal(f.find('functional-map-generate').disabled,false);assert.ok(f.calls.every(call=>call.body===undefined));}
const rejected=setup();await rejected.lookup({...result(rejected.record.id,[],false),blocked_reason:'Saved source bindings are incomplete.'});
assert.equal(rejected.find('functional-map-generate').disabled,true);assert.match(rejected.flow.mapGenerationGate(rejected.record),/source bindings/);
""", MAP_CLIENT)


if __name__ == '__main__':
    unittest.main()

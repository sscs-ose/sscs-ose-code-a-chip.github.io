"""Isolated S14 client checks with a declared DOM/API double.

No live project, model or EDA process is accessed. These assertions validate UI
guards and evidence handling, not the correctness of any physical circuit.
"""
from pathlib import Path
import shutil
import subprocess
import unittest

PROJECT = Path(__file__).resolve().parents[1]

CLIENT = r"""
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const source = fs.readFileSync('src/gui/postlayout_workflow.js', 'utf8')
  .replace(/^import[^\n]*\n/gm, '').replace('export class PostlayoutWorkflow', 'class PostlayoutWorkflow');
class DOMDouble {
  constructor(tag = 'div', attrs = {}) { this.tag = tag; Object.assign(this, attrs); this.children = []; this.isConnected = true; }
  append(...children) { this.children.push(...children.map(child => child == null ? String(child) : child)); }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  querySelector(selector) { const id = selector.match(/^\[data-testid="([^"]+)"\]$/)?.[1]; return descend(this).find(node => node && typeof node === 'object' && node['data-testid'] === id) || null; }
  focus() { document.activeElement = this; }
  setSelectionRange(start, end) { this.selectionStart = start; this.selectionEnd = end; }
  click() { this.onclick?.(); }
  remove() { this.removed = true; }
}
const descend = host => host.children.flatMap(child => child && typeof child === 'object' ? [child, ...descend(child)] : [child]);
const text = host => [host.text, host.textContent, ...descend(host).map(node => typeof node === 'string' ? node : node.text ?? node.textContent ?? '')].filter(Boolean).join('\n');
const el = (tag, attrs = {}, ...children) => { const node = new DOMDouble(tag, attrs); node.append(...children.flat(Infinity).filter(x => x != null && x !== false)); return node; };
const document = {activeElement: null, body: new DOMDouble('body')}, requests = [], notices = [], toasts = [], navigations = [], fetches = [], revoked = [];
let responder = async () => project.envelope, responseBytes = new TextEncoder().encode('SOFTWARE QA ONLY: timing log\r\n'), responseStatus = 200, responseGate = null;
const sandbox = {el, badge: text => el('span', {text}), field: (label, value, change, options) => el('select', {value, ...options, onchange: change}), downloadJsonResponse() {},
  document, console, Blob, TextDecoder, TextEncoder, Uint8Array, crypto: require('crypto').webcrypto,
  URL: {createObjectURL: () => 'blob:software-qa', revokeObjectURL: url => revoked.push(url)},
  setTimeout: () => 1, clearTimeout() {},
  fetch: async (url, options) => { fetches.push({url, method: options.method || 'GET'}); if (responseGate) await responseGate.promise; return {ok: responseStatus === 200, status: responseStatus, arrayBuffer: async () => responseBytes.buffer.slice(responseBytes.byteOffset, responseBytes.byteOffset + responseBytes.byteLength)}; }
};
// Transport is a declared isolated double; production import count can change.
sandbox.sessionFetch = (...args) => sandbox.fetch(...args);
vm.createContext(sandbox); vm.runInContext(source + '\nglobalThis.PostlayoutWorkflow = PostlayoutWorkflow;', sandbox);
const hash = value => require('crypto').createHash('sha256').update(value).digest('hex');
const accepted = (id, extra = {}) => ({id, revision_id: 'software-qa-revision', execution_status: 'Completed', validation_status: 'Passed', review_status: 'Accepted', freshness: 'Current', ...extra});
const layout = accepted('software-qa-layout', {artifacts: [{id:'gds',sha256:'gds-software-qa'}, {id:'netlist',sha256:'netlist-software-qa'}]});
const drc = accepted('software-qa-drc', {layout_run_id:layout.id, input_gds_sha256:'gds-software-qa'});
const lvs = accepted('software-qa-lvs', {layout_run_id:layout.id, drc_run_id:drc.id, input_gds_sha256:'gds-software-qa', input_netlist_sha256:'netlist-software-qa'});
let project = {design:{id:'software-qa-project'}, stage:'post_layout_verification', dirty:false, conflict:null, busy:false, envelope:{revision:{id:'software-qa-revision'}, workflow:[{id:'post_layout_verification',implemented:true}], physical_workflow:{runs:[layout],accepted_run_id:layout.id}, drc_workflow:{runs:[drc],accepted_run_id:drc.id}, lvs_workflow:{runs:[lvs],accepted_run_id:lvs.id}}};
const flow = new sandbox.PostlayoutWorkflow({project: () => project, request: async (route, body) => {requests.push({route,body}); return responder(route,body);},
  envelope: envelope => {project.envelope = envelope; flow.receive(envelope);}, workflow: value => flow.receive({...project.envelope,postlayout_workflow:value}), notify: (...args) => notices.push(args), toast: value => toasts.push(value), navigate: stage => navigations.push(stage), chrome() {}});
flow.data = {implemented:true, ready:true, tool_ready:true, runs:[], reviews:[], source_inputs:{sdf:{sha256:'software-qa-sdf'}}, runtime_configuration:{software_qa_fixture:true}};
const host = new DOMDouble('main'); flow.render(host);
const find = id => host.querySelector(`[data-testid="${id}"]`);
const normalized = value => JSON.parse(JSON.stringify(value));
const record = (id = 'software-qa-postlayout') => ({id, revision_id:'software-qa-revision',layout_run_id:layout.id,drc_run_id:drc.id,lvs_run_id:lvs.id,execution_status:'Completed',validation_status:'Failed',review_status:'Awaiting Review',freshness:'Current',source_key:'software-qa-source',source_identity:{software_qa_fixture:true},checks:{executed:false,software_qa_fixture:true,checks:{annotation:{status:'Unsupported'}},summary:{timing_scope:'SOFTWARE QA unsupported construct'},stdout:'SOFTWARE QA ONLY: no simulator executed'},diagnostics:[{code:'software_qa_unsupported',severity:'warning',message:'SOFTWARE QA ONLY'}],artifacts:[]});
const install = run => {flow.data={...flow.data,runs:[run],latest_run_id:run.id,accepted_run_id:null}; flow.runId=run.id; project.envelope.postlayout_workflow=flow.data; flow.refresh();};
const deferred = () => {let resolve; const promise=new Promise(r=>resolve=r); return {promise,resolve};};
"""


class PostlayoutClientTests(unittest.TestCase):
    def test_drc_lvs_intros_do_not_mislabel_s14_as_dynamic_verification(self):
        drc = (PROJECT / 'src/gui/drc_workflow.js').read_text(encoding='utf-8')
        lvs = (PROJECT / 'src/gui/lvs_workflow.js').read_text(encoding='utf-8')
        self.assertIn('LVS and S14 post-layout verification require separate evidence.', drc)
        self.assertNotIn('LVS and dynamic post-layout verification require separate evidence.', drc)
        app = (PROJECT / 'src/gui/app.js').read_text(encoding='utf-8')
        self.assertNotIn('Inspect extracted timing and dynamic post-layout verification separately.', app)
        self.assertIn('Inspect recorded functional and timing evidence, scope and limitations.', app)
        self.assertIn('Post-layout functional/timing verification remains a separate stage;', lvs)
        self.assertIn('this view does not establish dynamic SDF qualification.', lvs)
        self.assertNotIn('Dynamic post-layout verification remains a separate stage.', lvs)

    def run_client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for the isolated S14 client checks.")
        result = subprocess.run([node, "-e", CLIENT + "\n(async () => {\n" + body +
                                 "\nconsole.log('Passed: isolated S14 software fixture');\n})().catch(error => {console.error(error.stack || error); process.exitCode = 1;});"],
                                cwd=PROJECT, capture_output=True, text=True,
                                encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_exact_source_chain_unsupported_runtime_and_active_guards(self):
        self.run_client(r"""
assert.equal(flow.gate(),''); assert.equal(find('postlayout-workflow-run').disabled,false);
for (const [object,key,value] of [[lvs,'drc_run_id','other-drc'],[lvs,'input_netlist_sha256','other-netlist'],[drc,'input_gds_sha256','other-gds'],[layout,'freshness','Stale'],[lvs,'revision_id','other-revision']]) {
  const old=object[key]; object[key]=value; flow.refresh(); assert.ok(flow.gate()); assert.equal(find('postlayout-workflow-run').disabled,true); object[key]=old;
}
flow.data.tool_ready=false; flow.data.tool_blocked_reason='SOFTWARE QA unsupported INTERCONNECT'; flow.refresh();
assert.match(find('postlayout-workflow-gate').textContent,/unsupported INTERCONNECT/); flow.data.tool_ready=true;
project.dirty=true; assert.match(flow.gate(),/Save/); project.dirty=false;
project.conflict='newer'; assert.match(flow.gate(),/newer saved/); project.conflict=null;
project.envelope.generation={jobs:[{execution_status:'Running'}]}; assert.match(flow.gate(),/active/); delete project.envelope.generation;
project.envelope.postlayout_workflow={runs:[{execution_status:'Running'}]}; flow.data.runs=project.envelope.postlayout_workflow.runs; assert.match(flow.gate(),/active/);
assert.equal(requests.length,0);
""")

    def test_unsupported_failed_evidence_full_log_segments_and_review(self):
        self.run_client(r"""
const run=record(); run.validation_status='Unsupported'; run.checks.stdout='SOFTWARE QA ONLY\n'+'x'.repeat(150000)+'\nSOFTWARE QA END'; install(run);
const review=new DOMDouble('aside'); flow.renderReview(review);
assert.equal(review.querySelector('[data-testid="postlayout-workflow-accept"]').disabled,true);
assert.match(text(find('postlayout-workflow-status')),/Unsupported/); assert.match(text(find('postlayout-workflow-checks')),/Unsupported/);
const logs=find('postlayout-workflow-logs'); assert.ok(logs); assert.match(text(logs),/Segment 1 of/);
logs.querySelector('[data-testid="postlayout-workflow-logs-last"]').click(); assert.match(text(logs),/SOFTWARE QA END/);
const prior=text(logs); flow.refresh(); assert.equal(text(find('postlayout-workflow-logs')),prior);
const note=review.querySelector('[data-testid="postlayout-workflow-feedback"]'); note.value='SOFTWARE QA correction'; note.oninput({target:note}); note.focus(); note.selectionStart=3; note.selectionEnd=7;
flow.renderReview(review); const next=review.querySelector('[data-testid="postlayout-workflow-feedback"]'); assert.equal(next.value,'SOFTWARE QA correction'); assert.equal(next.selectionStart,3); assert.equal(next.selectionEnd,7);
assert.equal(descend(find('postlayout-workflow-result')).includes('null'),false);
run.freshness='Stale'; run.validation_status='Passed'; flow.renderReview(review); assert.equal(review.querySelector('[data-testid="postlayout-workflow-accept"]').disabled,true);
""")

    def test_exact_start_uncertain_readonly_reconnect_cancel_and_feedback(self):
        self.run_client(r"""
responder=async()=>{throw new Error('SOFTWARE QA lost response');}; await flow.start();
assert.equal(requests.length,1); assert.deepEqual(normalized(requests[0]),{route:'postlayout-workflow/runs',body:{stage:'post_layout_verification',layout_run_id:layout.id,drc_run_id:drc.id,lvs_run_id:lvs.id,revision_id:'software-qa-revision'}});
assert.equal(flow.uncertainStart,true); await flow.start(); assert.equal(requests.length,1);
responder=async()=>project.envelope; await flow.refreshSaved(); assert.equal(requests.length,2); assert.equal(requests[1].route,'project'); assert.equal(requests[1].body,undefined); assert.equal(flow.uncertainStart,false);
const run=record(); install(run); await flow.cancel(run); assert.equal(requests.at(-1).route,`postlayout-workflow/runs/${run.id}/cancel`);
const before=requests.length; await flow.review(run,'changes_requested','   '); assert.equal(requests.length,before);
await flow.review(run,'return_to_stage',' SOFTWARE QA fix timing ','layout'); assert.deepEqual(normalized(requests.at(-1).body),{decision:'return_to_stage',note:'SOFTWARE QA fix timing',target_stage:'layout'}); assert.equal(navigations.at(-1),'layout');
""")

    def test_gui_prepares_fixed_profile_with_ids_only_and_no_run(self):
        self.run_client(r"""
flow.data={...flow.data,ready:false,tool_ready:false,profile_prepare_available:true,blocked_reason:'SOFTWARE QA profile missing',profile_configuration_error:{message:'SOFTWARE QA stale profile'}}; flow.refresh();
const prepare=find('postlayout-workflow-prepare'); assert.equal(prepare.hidden,false); assert.equal(prepare.disabled,false);
assert.equal(find('postlayout-workflow-run').disabled,true); assert.match(find('postlayout-workflow-gate').textContent,/starts no EDA or model process/);
const prepared={...flow.data,ready:true,tool_ready:true,execution_scope:'post_route_functional_plus_sta',profile_configuration_error:null};
responder=async()=>({...project.envelope,postlayout_workflow:prepared}); await flow.prepare();
assert.equal(requests.length,1); assert.deepEqual(normalized(requests[0]),{route:'postlayout-workflow/profile',body:{layout_run_id:layout.id,drc_run_id:drc.id,lvs_run_id:lvs.id,revision_id:'software-qa-revision'}});
assert.deepEqual(Object.keys(requests[0].body).sort(),['drc_run_id','layout_run_id','lvs_run_id','revision_id']);
assert.equal(flow.data.runs.length,0); assert.equal(find('postlayout-workflow-prepare').hidden,true); assert.equal(find('postlayout-workflow-run').disabled,false);
assert.match(toasts.at(-1),/No EDA, model or S14 verification attempt was started/);
""")

    def test_explicit_profile_update_is_visible_without_starting_or_replacing_old_attempts(self):
        self.run_client(r"""
const run=record(); install(run); const original=normalized(run);
flow.data={...flow.data,ready:true,tool_ready:true,profile_prepare_available:true,profile_update_available:true,runtime_configuration:{profile_version:'SOFTWARE_QA_V2'}}; flow.refresh();
const prepare=find('postlayout-workflow-prepare'); assert.equal(prepare.hidden,false); assert.equal(prepare.disabled,false); assert.equal(prepare.textContent,'Prepare updated S14 profile');
assert.match(find('postlayout-workflow-gate').textContent,/saved profile remains in use until you explicitly prepare/);
assert.match(find('postlayout-workflow-gate').textContent,/creates no S14 attempt/);
assert.deepEqual(normalized(run),original); assert.equal(requests.length,0);
run.checks.cleanup_unresolved=true; flow.refresh(); assert.equal(find('postlayout-workflow-prepare').disabled,true); await flow.prepare(); assert.equal(requests.length,0); delete run.checks.cleanup_unresolved;
for(const [key,value] of [['dirty',true],['busy',true],['conflict','SOFTWARE QA newer saved revision']]) { project[key]=value; flow.refresh(); assert.equal(find('postlayout-workflow-prepare').disabled,true); await flow.prepare(); project[key]=key==='conflict'?null:false; }
assert.equal(requests.length,0); flow.refresh();
const pending=deferred(); responder=async()=>{await pending.promise; return {...project.envelope,postlayout_workflow:{...flow.data,profile_update_available:false,runtime_configuration:{profile_version:'SOFTWARE_QA_V3'}}};};
const update=flow.prepare(); assert.equal(flow.data.runtime_configuration.profile_version,'SOFTWARE_QA_V2'); assert.equal(find('postlayout-workflow-prepare').disabled,true); await flow.prepare();
assert.equal(requests.length,1); assert.deepEqual(normalized(requests[0]),{route:'postlayout-workflow/profile',body:{layout_run_id:layout.id,drc_run_id:drc.id,lvs_run_id:lvs.id,revision_id:'software-qa-revision'}});
pending.resolve(); await update; assert.equal(flow.data.runtime_configuration.profile_version,'SOFTWARE_QA_V3'); assert.equal(find('postlayout-workflow-prepare').hidden,true);
assert.deepEqual(normalized(run),original); assert.equal(flow.data.runs.length,1); assert.match(toasts.at(-1),/Earlier attempts were preserved/); assert.match(toasts.at(-1),/No EDA, model or S14 verification attempt was started/);
""")

    def test_new_physical_runtime_keeps_gui_profile_preparation_visible_when_tools_are_ready(self):
        self.run_client(r"""
flow.data={...flow.data,ready:false,tool_ready:true,profile_prepare_available:true,profile_update_available:false,profile_prepare_needed:true}; flow.refresh();
assert.equal(find('postlayout-workflow-prepare').hidden,false); assert.equal(find('postlayout-workflow-prepare').disabled,false); assert.equal(find('postlayout-workflow-run').disabled,true);
assert.match(find('postlayout-workflow-gate').textContent,/earlier physical runtime/);
lvs.freshness='Stale'; flow.refresh(); assert.equal(find('postlayout-workflow-prepare').disabled,true); await flow.prepare(); assert.equal(requests.length,0); lvs.freshness='Current';
responder=async()=>({...project.envelope,postlayout_workflow:{...flow.data,ready:true,profile_prepare_needed:false}}); await flow.prepare(); assert.equal(requests.length,1); assert.equal(requests[0].route,'postlayout-workflow/profile'); assert.equal(find('postlayout-workflow-prepare').hidden,true);
flow.data.profile_prepare_available=false; flow.data.profile_prepare_needed=false; flow.data.profile_update_available=false; flow.refresh(); assert.equal(find('postlayout-workflow-prepare').hidden,true);
""")

    def test_fixed_artifact_hash_guard_and_late_source_view_rejection(self):
        self.run_client(r"""
const run=record(); const item={id:'simulation-stdout',content_type:'text/plain; charset=utf-8',bytes:responseBytes.length,sha256:hash(responseBytes),url:`/api/artifacts/postlayout-workflow/${run.id}/simulation-stdout`}; run.artifacts=[item]; install(run);
await flow.viewFile(run,item); assert.match(flow.fileView.text,/SOFTWARE QA ONLY/); assert.ok(find('postlayout-workflow-file-view'));
const previous=fetches.length; await flow.viewFile(run,{...item,url:'https://invalid.example/raw'}); assert.equal(fetches.length,previous); assert.match(notices.at(-1)[0],/fixed post-layout routes/);
await flow.viewFile(run,{...item,sha256:'wrong'}); assert.equal(flow.fileView,null); assert.match(notices.at(-1)[0],/hash and size/);
responseGate=deferred(); const pending=flow.viewFile(run,item); project.design={id:'other-software-qa-project'}; responseGate.resolve(); await pending; assert.equal(flow.fileView,null); responseGate=null;
project.design={id:'software-qa-project'}; responseGate=deferred(); const next=flow.viewFile(run,item); run.source_identity={software_qa_fixture:true,changed:true}; responseGate.resolve(); await next; assert.equal(flow.fileView,null); responseGate=null;
assert.ok(fetches.every(request=>request.method==='GET'));
""")

    def test_saved_termination_recovery_keeps_failure_and_does_not_run_tools(self):
        self.run_client(r"""
const run=record(); run.execution_status='Failed'; run.validation_status='Not Checked'; run.checks.cleanup_unresolved=true; run.cleanup_resolution_available=true; install(run);
flow.data.ready=false; flow.data.tool_ready=true; flow.data.profile_prepare_available=true; flow.data.blocked_reason='SOFTWARE QA unresolved cleanup'; flow.refresh();
assert.equal(find('postlayout-workflow-prepare').hidden,true);
const button=find('postlayout-workflow-verify-termination'); assert.ok(button); assert.equal(button.disabled,false);
const original=normalized(run.checks);
responder=async()=>({...project.envelope,postlayout_workflow:{...flow.data,runs:[{...run,cleanup_resolution_available:false,cleanup_resolution:{id:'SOFTWARE_QA_AUDIT'}}],ready:true}});
await flow.verifyTermination(run);
assert.equal(requests.length,1); assert.deepEqual(normalized(requests[0]),{route:`postlayout-workflow/runs/${run.id}/verify-termination`,body:{}});
assert.equal(flow.selected().execution_status,'Failed'); assert.equal(flow.selected().validation_status,'Not Checked'); assert.deepEqual(normalized(flow.selected().checks),original);
assert.equal(find('postlayout-workflow-verify-termination'),null); assert.match(text(find('postlayout-workflow-cleanup')),/retains its original failure/);
assert.match(toasts.at(-1),/no process or verification was started/);
""")

    def test_fixed_physical_correction_requires_electrical_only_complete_current_failure(self):
        self.run_client(r"""
const run=record(); run.evidence_kind='trusted_fixed_postlayout_execution'; run.execution_scope='post_route_functional_plus_sta'; run.verification_supported=true;
run.checks={origin:'trusted_fixed_postlayout_adapter',execution_scope:run.execution_scope,status:'Completed',validation_status:'Failed',executed:true,exit_code:0,cleanup_unresolved:false,
 commands:Array.from({length:11},()=>({executed:true,status:'Completed',exit_code:0,cleanup_unresolved:false})),
 checks:Object.fromEntries(['source_identity','configuration','functional','parasitics','constraints','setup_hold','electrical'].map(name=>[name,{validation_status:name==='electrical'?'Failed':'Passed'}]))};
install(run); assert.equal(find('postlayout-physical-repair-card').hidden,false); assert.equal(find('postlayout-physical-repair-prepare').disabled,false);
assert.match(text(find('postlayout-physical-repair-card')),/original 50 ns clock, SDC constraints, workload and expected values/);
assert.match(text(find('postlayout-physical-repair-card')),/starts no EDA/);
assert.equal(descend(find('postlayout-physical-repair-card')).includes('null'),false);
for(const [object,key,value] of [[run,'freshness','Stale'],[run,'evidence_kind','software_qa_fixture'],[run,'execution_status','Failed'],[run,'verification_supported',false],[run.checks,'cleanup_unresolved',true],[run.checks,'commands',run.checks.commands.slice(1)],[run.checks.checks.functional,'validation_status','Failed'],[run.checks.checks.electrical,'validation_status','Passed']]) {
 const previous=object[key]; object[key]=value; flow.refresh(); assert.equal(find('postlayout-physical-repair-card').hidden,true,key); object[key]=previous;
}
flow.refresh(); const initial=requests.length;
for(const [key,value] of [['dirty',true],['busy',true],['conflict','SOFTWARE QA newer saved revision']]) { project[key]=value; flow.refresh(); assert.equal(find('postlayout-physical-repair-prepare').disabled,true); await flow.preparePhysicalRepair(run); project[key]=key==='conflict'?null:false; }
assert.equal(requests.length,initial);
const pending=deferred(); responder=async()=>{await pending.promise; return {...project.envelope,physical_repair_session:{configured:true,bundle_present:true,error:null,source_identity:{failed_s14_id:run.id},profile_version:'SOFTWARE_QA_FIXED_REPAIR'},postlayout_workflow:{...flow.data,runs:[{...run,freshness:'Stale'}]}};};
const preparation=flow.preparePhysicalRepair(run); await flow.preparePhysicalRepair(run); assert.equal(requests.length,initial+1); assert.equal(flow.busy,true);
assert.deepEqual(normalized(requests.at(-1)),{route:'postlayout-workflow/physical-repair-profile',body:{failed_s14_id:run.id,revision_id:'software-qa-revision'}});
pending.resolve(); await preparation;
assert.equal(navigations.at(-1),'layout'); assert.equal(flow.selected().freshness,'Stale'); assert.equal(flow.selected().validation_status,'Failed');
assert.equal(find('postlayout-physical-repair-prepare'),null); assert.ok(find('postlayout-physical-repair-layout'));
assert.match(text(find('postlayout-physical-repair-card')),/explicit GUI action/); assert.match(text(find('postlayout-physical-repair-card')),/S11 → S12 → S13 → S14/);
find('postlayout-physical-repair-layout').click(); assert.equal(navigations.at(-1),'layout');
assert.match(toasts.at(-1),/No EDA was started/); assert.equal(requests.length,initial+1);
""")

    def test_preflight_only_runtime_never_implies_dynamic_execution_or_adoption(self):
        self.run_client(r"""
flow.data.verification_supported=false; flow.data.execution_scope='compatibility_preflight_only'; flow.refresh();
assert.equal(flow.gate(),''); assert.equal(find('postlayout-workflow-run').textContent,'Check S14 readiness');
assert.match(find('postlayout-workflow-intro').textContent,/does not start a simulator or permit adoption/);
assert.match(find('postlayout-workflow-gate').textContent,/compatibility check only/);
const run=record(); run.runtime_configuration={verification_supported:false,execution_scope:'compatibility_preflight_only'}; run.validation_status='Unsupported'; run.checks.executed=false; install(run);
const review=new DOMDouble('aside'); flow.renderReview(review); assert.equal(review.querySelector('[data-testid="postlayout-workflow-accept"]').disabled,true);
assert.match(find('postlayout-workflow-scope').text,/no dynamic simulator was started/);
// Even an inconsistent upstream status must not enable preflight adoption.
run.validation_status='Passed'; project.envelope.review_policy={mode:'accept_on_pass',user_authorized:true}; flow.renderReview(review);
assert.equal(review.querySelector('[data-testid="postlayout-workflow-accept"]').disabled,true); assert.equal(flow.pendingPolicy(),false);
await flow.review(run,'accepted',''); assert.equal(requests.length,0);
run.validation_status='Unsupported'; await flow.start(); assert.equal(requests.length,1); assert.match(toasts.at(-1),/Dynamic simulation remains unsupported/);
""")

    def test_static_stage_wiring_and_other_tool_exclusion(self):
        self.run_client(r"""
const app=fs.readFileSync('src/gui/app.js','utf8'); const stages=app.match(/const STAGES = \[([\s\S]*?)\n\];/)[1]; assert.equal((stages.match(/^  \['/gm)||[]).length,14);
assert.match(app,/id === 'post_layout_verification'.*postlayoutFlow\.render/); assert.match(app,/state\.stage === 'post_layout_verification'.*postlayoutFlow\.start/);
for(const [file,name] of [['physical_workflow.js','PhysicalWorkflow'],['drc_workflow.js','DRCWorkflow'],['lvs_workflow.js','LVSWorkflow'],['global_workflow.js','GlobalWorkflow']]) {
  const code=fs.readFileSync('src/gui/'+file,'utf8').replace(/^import[^\n]*\n/gm,'').replace('export class '+name,'class '+name);
  const separate={el,field(){},badge(){},downloadJsonResponse(){}}; vm.createContext(separate); vm.runInContext(code+'\nglobalThis.GuardClass = '+name+';',separate);
  const guard=new separate.GuardClass({project:()=>({envelope:{postlayout_workflow:{runs:[{execution_status:'Running'}]}}})});
  assert.equal(guard.anyActive(),true,file+' must block a concurrent S14 run');
}
""")

    def test_saved_timed_diagnostic_review_never_implies_a_new_tool_run_or_adoption(self):
        self.run_client(r"""
flow.data.verification_supported=false; flow.data.execution_scope='saved_dynamic_diagnostic_review'; flow.refresh();
assert.equal(flow.preflight(),false); assert.equal(flow.diagnostic(),true);
assert.equal(find('postlayout-workflow-run').textContent,'Validate saved timed diagnostic');
assert.match(find('postlayout-workflow-intro').textContent,/actual timed diagnostic/);
assert.match(find('postlayout-workflow-intro').textContent,/starts no new simulator process/);
assert.match(find('postlayout-workflow-gate').textContent,/retained tool run is not repeated/);
const run=record(); run.execution_scope='saved_dynamic_diagnostic_review'; run.runtime_configuration={verification_supported:false,execution_scope:run.execution_scope}; run.validation_status='Unsupported';
run.checks={...run.checks,executed:true,execution_started_by_this_review:false,review_mode:run.execution_scope,retained_execution:true}; install(run);
assert.match(text(find('postlayout-workflow-scope')),/Actual tool execution occurred in the retained original run/);
assert.match(text(find('postlayout-workflow-scope')),/this review starts no new simulator process/);
const execution=text(find('postlayout-workflow-diagnostic-execution'));
assert.match(execution,/"retained_actual_tool_execution": true/); assert.match(execution,/"execution_started_by_this_review": false/);
const review=new DOMDouble('aside'); flow.renderReview(review);
assert.equal(text(review.querySelector('[data-testid="postlayout-workflow-retry"]')),'Repeat saved diagnostic review');
assert.equal(review.querySelector('[data-testid="postlayout-workflow-accept"]').disabled,true);
run.validation_status='Passed'; project.envelope.review_policy={mode:'accept_on_pass',user_authorized:true}; flow.renderReview(review);
assert.equal(review.querySelector('[data-testid="postlayout-workflow-accept"]').disabled,true); assert.equal(flow.pendingPolicy(),false);
await flow.review(run,'accepted',''); assert.equal(requests.length,0); assert.match(toasts.at(-1),/remain Unsupported/);
run.validation_status='Unsupported'; await flow.start(); assert.equal(requests.length,1); assert.match(toasts.at(-1),/no new simulator process is launched/);
""")

    def test_historical_readiness_and_saved_diagnostic_keep_their_own_modes(self):
        self.run_client(r"""
flow.data.verification_supported=false; flow.data.execution_scope='saved_dynamic_diagnostic_review';
const prior=record('software-qa-prior-readiness'); prior.execution_scope='compatibility_preflight_only'; prior.validation_status='Unsupported'; prior.checks.executed=false;
const diagnostic=record('software-qa-retained-diagnostic'); diagnostic.execution_scope='saved_dynamic_diagnostic_review'; diagnostic.validation_status='Unsupported'; diagnostic.checks.executed=true;
flow.data.runs=[prior,diagnostic]; flow.data.latest_run_id=diagnostic.id; flow.runId=prior.id; flow.refresh();
assert.equal(find('postlayout-workflow-run').textContent,'Validate saved timed diagnostic');
assert.match(text(find('postlayout-workflow-scope')),/no dynamic simulator was started/);
assert.equal(find('postlayout-workflow-diagnostic-execution'),null);
flow.runId=diagnostic.id; flow.refresh(); assert.match(text(find('postlayout-workflow-scope')),/retained original run/);
assert.ok(find('postlayout-workflow-diagnostic-execution'));
diagnostic.execution_status='Running'; flow.refresh();
assert.match(text(find('postlayout-workflow-result')),/Rechecking saved timed diagnostic bytes and process proofs; no new tool run/);
assert.equal(text(find('postlayout-workflow-result')).includes('Actual dynamic post-layout verification in progress'),false);
""")

    def test_saved_diagnostic_json_model_bundle_and_native_warning_explanation(self):
        self.run_client(r"""
flow.data.verification_supported=false; flow.data.execution_scope='saved_dynamic_diagnostic_review';
const run=record(); run.execution_scope='saved_dynamic_diagnostic_review'; run.validation_status='Unsupported';
responseBytes=new TextEncoder().encode('{"software_qa_fixture":true}');
const item={id:'cell-models',content_type:'application/json',bytes:responseBytes.length,sha256:hash(responseBytes),url:`/api/artifacts/postlayout-workflow/${run.id}/cell-models`};
run.artifacts=[item]; install(run);
assert.equal(flow.fileExtension(run,item),'json');
await flow.downloadFile(run,item); assert.match(document.body.children.at(-1).download,/-cell-models\.json$/);
assert.equal(fetches.length,1); assert.equal(notices.length,0);
const explanation=text(find('postlayout-workflow-native-diagnostics'));
assert.match(explanation,/two empty-typ metadata errors for VOLTAGE and TEMPERATURE/);
assert.match(explanation,/missing values were not filled/); assert.match(explanation,/1,991 ignored TIMINGCHECK warnings/);
assert.match(explanation,/do not establish native timing-check support/); assert.match(explanation,/S14 remains Unsupported/);
const prior={...run,execution_scope:'compatibility_preflight_only'}; assert.equal(flow.fileExtension(prior,item),'v');
install(prior); assert.equal(find('postlayout-workflow-native-diagnostics'),null);
""")

    def test_global_settings_environment_distinguishes_preflight_from_dynamic_support(self):
        self.run_client(r"""
const app=fs.readFileSync('src/gui/app.js','utf8'), start=app.indexOf('function renderSettings(host) {'), end=app.indexOf('\nfunction conceptCard()',start);
assert.ok(start>0 && end>start);
const state={design:{settings:{},project:{name:'SOFTWARE QA ONLY'}},envelope:{postlayout_workflow:{implemented:true},lvs_workflow:{implemented:true}}};
let preflight=true, diagnostic=false;
const settingsContext={state,workspaceEnabled:false,el,field:()=>el('div'),badge:label=>el('span',{text:label}),section:(title,description,children)=>el('section',{},children),postlayoutFlow:{preflight:()=>preflight,diagnostic:()=>diagnostic,eventDiagnostic:()=>false},mutate(){},adoption:{render(){}},generation:{renderProvider(){}},conceptCard:()=>el('div')};
vm.createContext(settingsContext); vm.runInContext(app.slice(start,end)+'\nglobalThis.renderSettings=renderSettings;',settingsContext);
const settingsHost=new DOMDouble('main'); settingsContext.renderSettings(settingsHost);
let environment=text(settingsHost.querySelector('[data-testid="eda-settings-environment"]'));
assert.match(environment,/S14 readiness API/); assert.match(environment,/workflow and readiness checks are implemented/); assert.match(environment,/Qualified dynamic post-layout simulation remains unsupported/); assert.match(environment,/without starting a simulator or permitting S14 adoption/);
assert.equal(environment.includes('S14 dynamic post-layout verification remains unimplemented.'),false);
preflight=false; const futureHost=new DOMDouble('main'); settingsContext.renderSettings(futureHost);
environment=text(futureHost.querySelector('[data-testid="eda-settings-environment"]')); assert.match(environment,/post-layout workflow API/); assert.match(environment,/actual dynamic results are reported separately/);
diagnostic=true; const diagnosticHost=new DOMDouble('main'); settingsContext.renderSettings(diagnosticHost);
environment=text(diagnosticHost.querySelector('[data-testid="eda-settings-environment"]')); assert.match(environment,/saved S14 diagnostic API/); assert.match(environment,/starts no new simulator/); assert.match(environment,/cannot complete S14/);
""")


if __name__ == "__main__":
    unittest.main()

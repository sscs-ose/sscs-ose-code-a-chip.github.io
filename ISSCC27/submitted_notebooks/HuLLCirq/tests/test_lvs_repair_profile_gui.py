"""Pure DOM/API doubles for explicit LVS profile preparation; no live tools."""
from pathlib import Path
import shutil
import subprocess
import unittest

PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync('src/gui/lvs_workflow.js','utf8').replace(/^import[^\n]*\n/gm,'').replace('export class LVSWorkflow','class LVSWorkflow');
class DOMDouble{
 constructor(tag='div',attrs={}){this.tag=tag;Object.assign(this,attrs);this.children=[];this.isConnected=true;}
 append(...children){this.children.push(...children.flat(Infinity).filter(x=>x!=null&&x!==false));}
 replaceChildren(...children){this.children=[];this.append(...children);}
 querySelector(selector){const id=selector.match(/^\[data-testid="([^"]+)"\]$/)?.[1];return descend(this).find(x=>x&&typeof x==='object'&&x['data-testid']===id)||null;}
 focus(){document.activeElement=this;} setSelectionRange(){} click(){this.onclick?.();} remove(){}
}
const descend=host=>host.children.flatMap(x=>x&&typeof x==='object'?[x,...descend(x)]:[x]);
const text=host=>[host.text,host.textContent,...descend(host).map(x=>typeof x==='string'?x:x.text??x.textContent??'')].filter(Boolean).join('\n');
const el=(tag,attrs={},...children)=>{const result=new DOMDouble(tag,attrs);result.append(...children);return result;};
const document={activeElement:null,body:new DOMDouble('body')},requests=[],notices=[],toasts=[],navigations=[];let gets=0;
const sandbox={el,badge:value=>el('span',{text:value}),field:()=>el('select'),document,console,setTimeout:()=>1,clearTimeout(){},downloadJsonResponse(){},sessionFetch:async()=>{gets++;throw Error('Unexpected artifact read');}};
vm.createContext(sandbox);vm.runInContext(source+'\nglobalThis.LVSWorkflow=LVSWorkflow;',sandbox);
const accepted=(id,extra={})=>({id,revision_id:'original-source-revision',execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',...extra});
const gds='1'.repeat(64),netlist='2'.repeat(64);
const layout=accepted('qa-layout',{record_hash:'3'.repeat(64),artifacts:[{id:'gds',sha256:gds},{id:'netlist',sha256:netlist}]}),drc=accepted('qa-drc',{record_hash:'4'.repeat(64),layout_run_id:layout.id,input_gds_sha256:gds});
const run=accepted('qa-warning-lvs',{record_hash:'5'.repeat(64),layout_run_id:layout.id,drc_run_id:drc.id,input_gds_sha256:gds,input_netlist_sha256:netlist,evidence_kind:'trusted_fixed_lvs_execution',layout_snapshot:{...layout},drc_snapshot:{...drc},checks:{executed:true,summary:{extraction:{feedback_item_count:2,non_overlap_feedback_count:2,illegal_overlap_count:0},lvs:{match_status:'Unique match'}}},diagnostics:[{code:'retained-feedback',message:'SOFTWARE QA: two retained terminal warnings'}],artifacts:[]});
const preparation={available:true,eligible:true,blocked_reason:null,profile_version:'hullcirq-sky130-lvs-v3',source:{layout_run_id:layout.id,drc_run_id:drc.id,source_lvs_run_id:run.id,revision_id:'current-gui-revision',source_revision_id:layout.revision_id,layout_record_hash:layout.record_hash,drc_record_hash:drc.record_hash,source_lvs_record_hash:run.record_hash,source_lvs_record_sha256:'6'.repeat(64),input_gds_sha256:gds,input_netlist_sha256:netlist}};
const session={configured:true,bundle_present:true,error:null,profile_version:'hullcirq-sky130-lvs-v3',source_identity:{...preparation.source}};
let project={design:{id:'qa-project'},stage:'lvs',dirty:false,conflict:null,busy:false,readOnly:false,envelope:{workspace_identity:{project_id:'qa-project',system_id:'qa-system',session_id:'qa-session',read_only:false},revision:{id:'current-gui-revision'},workflow:[{id:'lvs',implemented:true},{id:'post_layout_verification',implemented:true}],review_policy:{mode:'manual'},physical_workflow:{runs:[layout],accepted_run_id:layout.id,latest_run_id:layout.id},drc_workflow:{runs:[drc],accepted_run_id:drc.id,latest_run_id:drc.id},lvs_repair_preparation:preparation}};
let responder=async()=>project.envelope;
const flow=new sandbox.LVSWorkflow({project:()=>project,request:async(route,body)=>{requests.push({route,body});return responder(route,body);},envelope:value=>{project.envelope=value;flow.receive(value);},workflow:value=>{flow.data=value;flow.refresh();},notify:(...args)=>notices.push(args),toast:value=>toasts.push(value),navigate:value=>navigations.push(value),chrome(){}});
flow.data={implemented:true,ready:true,tool_ready:true,layout_run_id:layout.id,drc_run_id:drc.id,configuration_sha256:'7'.repeat(64),runs:[run],reviews:[],latest_run_id:run.id,accepted_run_id:run.id,runtime_configuration:{profile:{profile_version:'hullcirq-sky130-lvs-v2'}}};project.envelope.lvs_workflow=flow.data;
const host=new DOMDouble('main');flow.render(host);const find=id=>host.querySelector(`[data-testid="${id}"]`),normalized=value=>JSON.parse(JSON.stringify(value)),deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return{promise,resolve};};
function installInitialV7(){
 run.runtime_configuration={profile:{profile_version:'hullcirq-sky130-lvs-v2'}};
 const initial={...preparation,mode:'initial_v7',profile_version:'hullcirq-sky130-lvs-v7'};
 project.envelope={...project.envelope,lvs_repair_preparation:initial};delete project.envelope.lvs_repair_session;flow.refresh();return initial;
}
function installUpgrade(){
 const failed={...run,id:'qa-failed-v3',record_hash:'8'.repeat(64),execution_status:'Failed',validation_status:'Failed',review_status:'Awaiting Review',runtime_configuration:{profile:{profile_version:'hullcirq-sky130-lvs-v3'}},checks:{...run.checks,executed:true,status:'Failed',exit_code:1}};
 const prior={...session,bundle_sha256:'a'.repeat(64),source_identity:{historical_lvs_run_id:run.id,historical_lvs_record_sha256:preparation.source.source_lvs_record_sha256}};
 const upgrade={...preparation,mode:'upgrade_v4',profile_version:'hullcirq-sky130-lvs-v4',source:{...preparation.source,source_lvs_run_id:failed.id,source_lvs_record_hash:failed.record_hash,source_lvs_record_sha256:'9'.repeat(64),previous_profile_version:'hullcirq-sky130-lvs-v3',previous_bundle_sha256:prior.bundle_sha256,historical_lvs_run_id:prior.source_identity.historical_lvs_run_id,historical_lvs_record_sha256:prior.source_identity.historical_lvs_record_sha256}};
 flow.data={...flow.data,runs:[{...run,freshness:'Stale',review_status:'Awaiting Review'},failed],latest_run_id:failed.id,accepted_run_id:null};flow.runId=failed.id;project.envelope={...project.envelope,lvs_workflow:flow.data,lvs_repair_session:prior,lvs_repair_preparation:upgrade};flow.refresh();return{failed,prior,upgrade};
}
function installV5Upgrade(){
 const base=installUpgrade(),failed={...base.failed,id:'qa-failed-v4',record_hash:'b'.repeat(64),runtime_configuration:{profile:{profile_version:'hullcirq-sky130-lvs-v4'}}};
 const prior={...base.prior,profile_version:'hullcirq-sky130-lvs-v4',bundle_sha256:'c'.repeat(64),previous_bundle_sha256:base.prior.bundle_sha256,upgrade_identity:{failed_v3_run_id:base.failed.id}};
 const upgrade={...base.upgrade,mode:'upgrade_v5',profile_version:'hullcirq-sky130-lvs-v5',source:{...base.upgrade.source,source_lvs_run_id:failed.id,source_lvs_record_hash:failed.record_hash,source_lvs_record_sha256:'d'.repeat(64),previous_profile_version:'hullcirq-sky130-lvs-v4',previous_bundle_sha256:prior.bundle_sha256}};
 flow.data={...flow.data,runs:[...flow.data.runs.map(item=>({...item,freshness:'Stale'})),failed],latest_run_id:failed.id};flow.runId=failed.id;project.envelope={...project.envelope,lvs_workflow:flow.data,lvs_repair_session:prior,lvs_repair_preparation:upgrade};flow.refresh();return{...base,failed,prior,upgrade};
}
function installV6Upgrade(){
 const base=installV5Upgrade(),failed={...base.failed,id:'qa-failed-v5',record_hash:'e'.repeat(64),runtime_configuration:{profile:{profile_version:'hullcirq-sky130-lvs-v5'}}};
 const prior={...base.prior,profile_version:'hullcirq-sky130-lvs-v5',bundle_sha256:'f'.repeat(64),previous_bundle_sha256:base.prior.bundle_sha256,upgrade_identity:{failed_v4_run_id:base.failed.id}};
 const upgrade={...base.upgrade,mode:'upgrade_v6',profile_version:'hullcirq-sky130-lvs-v6',source:{...base.upgrade.source,source_lvs_run_id:failed.id,source_lvs_record_hash:failed.record_hash,source_lvs_record_sha256:'a'.repeat(64),previous_profile_version:'hullcirq-sky130-lvs-v5',previous_bundle_sha256:prior.bundle_sha256}};
 flow.data={...flow.data,runs:[...flow.data.runs.map(item=>({...item,freshness:'Stale'})),failed],latest_run_id:failed.id};flow.runId=failed.id;project.envelope={...project.envelope,lvs_workflow:flow.data,lvs_repair_session:prior,lvs_repair_preparation:upgrade};flow.refresh();return{...base,failed,prior,upgrade};
}
function installV7Upgrade(){
 const base=installV6Upgrade(),failed={...base.failed,id:'qa-failed-v6',record_hash:'1'.repeat(64),execution_status:'Completed',runtime_configuration:{profile:{profile_version:'hullcirq-sky130-lvs-v6'}},checks:{...base.failed.checks,status:'Completed',exit_code:0,validation_status:'Failed'}};
 const prior={...base.prior,profile_version:'hullcirq-sky130-lvs-v6',bundle_sha256:'2'.repeat(64),previous_bundle_sha256:base.prior.bundle_sha256,upgrade_identity:{failed_v5_run_id:base.failed.id}};
 const upgrade={...base.upgrade,mode:'upgrade_v7',profile_version:'hullcirq-sky130-lvs-v7',source:{...base.upgrade.source,source_lvs_run_id:failed.id,source_lvs_record_hash:failed.record_hash,source_lvs_record_sha256:'3'.repeat(64),previous_profile_version:'hullcirq-sky130-lvs-v6',previous_bundle_sha256:prior.bundle_sha256}};
 flow.data={...flow.data,runs:[...flow.data.runs.map(item=>({...item,freshness:'Stale'})),failed],latest_run_id:failed.id};flow.runId=failed.id;project.envelope={...project.envelope,lvs_workflow:flow.data,lvs_repair_session:prior,lvs_repair_preparation:upgrade};flow.refresh();return{...base,failed,prior,upgrade};
}
"""


class LVSRepairProfileGuiTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated LVS correction fixtures.')
        result = subprocess.run([node, '-e', CLIENT + '\n(async()=>{\n' + body +
                                 '\n})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});'],
                                cwd=PROJECT, capture_output=True, text=True, encoding='utf-8', timeout=25)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_view_and_navigation_are_read_only_and_do_not_claim_warning_resolution(self):
        self.client(r"""
const before=JSON.stringify(project);assert.equal(flow.repairGate(),'');assert.equal(find('lvs-repair-profile-prepare').disabled,false);
assert.match(text(find('lvs-repair-profile-card')),/actual new tool feedback/i);assert.match(text(find('lvs-repair-profile-card')),/No warning is waived or declared resolved/);assert.match(text(find('lvs-workflow-result')),/two retained terminal warnings/);
for(const stage of ['layout','lvs','post_layout_verification','lvs']){project.stage=stage;flow.refresh();}flow.render(host);
assert.equal(JSON.stringify(project),before);assert.equal(requests.length,0);assert.equal(gets,0);
delete project.envelope.lvs_repair_preparation;flow.refresh();assert.equal(find('lvs-repair-profile-card').hidden,true);assert.equal(requests.length,0);
""")

    def test_explicit_prepare_sends_only_exact_ids_preserves_record_and_requires_separate_run(self):
        self.client(r"""
const original=JSON.stringify(run),source=JSON.stringify([layout,drc]),policy=JSON.stringify(project.envelope.review_policy);
responder=async(route,body)=>{assert.equal(route,'lvs-workflow/repair-profile');return{...project.envelope,lvs_repair_session:session,lvs_repair_preparation:{...preparation,eligible:false,blocked_reason:'Prepared'},lvs_workflow:{...flow.data,accepted_run_id:null,runs:[{...run,freshness:'Stale'}],runtime_configuration:{profile:{profile_version:'hullcirq-sky130-lvs-v3'}}}};};
await flow.prepareRepairProfile();assert.equal(requests.length,1);assert.deepEqual(normalized(requests[0]),{route:'lvs-workflow/repair-profile',body:{layout_run_id:layout.id,drc_run_id:drc.id,source_lvs_run_id:run.id,revision_id:'current-gui-revision'}});
assert.equal(JSON.stringify(run),original);assert.equal(JSON.stringify([layout,drc]),source);assert.equal(JSON.stringify(project.envelope.review_policy),policy);assert.equal(flow.selected().freshness,'Stale');assert.equal(flow.data.runs.length,1);assert.equal(find('lvs-repair-profile-prepare'),null);assert.ok(find('lvs-repair-profile-run'));assert.match(text(find('lvs-repair-profile-card')),/not a new LVS result/);assert.match(text(find('lvs-repair-profile-card')),/new source-bound S14 run/);assert.match(text(find('lvs-repair-profile-card')),/prepare its profile again only if requested/);
flow.refresh();await flow.prepareRepairProfile();assert.equal(requests.length,1);assert.equal(navigations.length,0);assert.match(toasts.at(-1),/No EDA, model, geometry change or adoption/);
responder=async()=>({...project.envelope,lvs_workflow:{...flow.data,latest_run_id:'qa-new-lvs',runs:[...flow.data.runs,{id:'qa-new-lvs',execution_status:'Queued'}]}});await flow.start();assert.equal(requests.length,2);assert.equal(requests[1].route,'lvs-workflow/runs');assert.equal(run.checks.summary.extraction.non_overlap_feedback_count,2);
""")

    def test_metadata_source_hashes_revision_alias_latest_and_actual_record_are_required(self):
        self.client(r"""
assert.notEqual(preparation.source.revision_id,run.revision_id);assert.equal(flow.repairSource().run.id,run.id);
for(const key of Object.keys(preparation.source)){const old=preparation.source[key];preparation.source[key]='wrong';assert.equal(flow.repairSource(),null,key);await flow.prepareRepairProfile();preparation.source[key]=old;}
for(const [object,key,value] of [[preparation,'available',false],[preparation,'eligible',false],[preparation,'profile_version','unrecognized'],[run,'freshness','Stale'],[run,'review_status','Awaiting Review'],[run,'validation_status','Failed'],[run,'evidence_kind','software_qa_fixture'],[run,'error',{code:'unknown'}],[run.checks,'executed',false],[run.checks,'cleanup_unresolved',true],[run.layout_snapshot,'record_hash','old'],[flow.data,'latest_run_id','other-run'],[flow.data,'accepted_run_id',null],[drc,'layout_run_id','other-layout']]){
 const old=object[key];object[key]=value;assert.ok(flow.repairGate(),key);await flow.prepareRepairProfile();object[key]=old;
}
assert.equal(requests.length,0);
""")

    def test_readonly_dirty_conflict_busy_active_and_existing_bundle_never_prepare(self):
        self.client(r"""
for(const key of ['readOnly','dirty','conflict','busy']){project[key]=key==='conflict'?'newer':true;assert.ok(flow.repairGate());await flow.prepareRepairProfile();project[key]=key==='conflict'?null:false;}
project.envelope.workspace_identity.read_only=true;assert.match(flow.repairGate(),/read-only/);assert.match(flow.gate(),/read-only/);await flow.prepareRepairProfile();project.envelope.workspace_identity.read_only=false;
for(const key of ['busy','polling','uncertainStart']){flow[key]=true;await flow.prepareRepairProfile();flow[key]=false;}
flow.pollError='read outcome unknown';await flow.prepareRepairProfile();flow.pollError=null;
flow.data.runs.push({id:'active-other',execution_status:'Running'});await flow.prepareRepairProfile();flow.data.runs.pop();
project.envelope.lvs_repair_session={bundle_present:true,configured:false,error:{message:'Saved profile must not be overwritten'}};flow.refresh();assert.match(text(find('lvs-repair-profile-card')),/must not be overwritten/);await flow.prepareRepairProfile();
assert.equal(requests.length,0);assert.equal(gets,0);
""")

    def test_restored_profile_requires_run_and_blocks_unknown_profile_from_prepared_claim(self):
        self.client(r"""
project.envelope.lvs_repair_session=session;flow.refresh();flow.render(host);assert.ok(find('lvs-repair-profile-run'));assert.equal(find('lvs-repair-profile-prepare'),null);assert.equal(requests.length,0);assert.match(text(find('lvs-repair-profile-status')),new RegExp(run.id));
project.readOnly=true;flow.refresh();assert.equal(find('lvs-repair-profile-run').disabled,true);project.readOnly=false;
project.envelope.lvs_repair_session={...session,profile_version:'unknown-profile'};flow.refresh();assert.equal(find('lvs-repair-profile-run'),null);assert.equal(find('lvs-repair-profile-prepare').disabled,true);assert.equal(requests.length,0);
""")

    def test_late_context_success_and_failure_are_dropped_and_unknown_outcome_is_not_resent(self):
        self.client(r"""
for(const rejected of [false,true]){const wait=deferred(),old=project.envelope,noticeCount=notices.length,toastCount=toasts.length;responder=async()=>{await wait.promise;if(rejected)throw Error('OLD_SCOPE');return{...old,lvs_repair_session:session};};
 const pending=flow.prepareRepairProfile();project.envelope={...old,workspace_identity:{...old.workspace_identity,session_id:'changed-session'}};wait.resolve();await pending;assert.equal(project.envelope.lvs_repair_session,undefined);assert.equal(notices.length,noticeCount);assert.equal(toasts.length,toastCount);assert.equal(flow.busy,false);project.envelope=old;
}
responder=async()=>{throw Error('uncertain transport');};await flow.prepareRepairProfile();const count=requests.length;assert.match(flow.pollError,/Refresh saved status without resending/);await flow.prepareRepairProfile();assert.equal(requests.length,count);assert.ok(find('lvs-workflow-reconnect'));assert.equal(gets,0);
""")

    def test_app_hook_exposes_readonly_without_changing_controller_requests(self):
        source = (PROJECT / 'src/gui/app.js').read_text(encoding='utf-8')
        line = next(line for line in source.splitlines() if line.startswith('const lvsFlow = new LVSWorkflow'))
        self.assertIn('readOnly: readOnly()', line)

    def test_explicit_v4_upgrade_uses_failed_v3_id_and_preserves_v2_v3_history(self):
        self.client(r"""
const {failed,prior,upgrade}=installUpgrade(),original=JSON.stringify([run,failed,prior]);assert.equal(flow.repairGate(),'');assert.equal(flow.repairSource().upgrade,true);assert.equal(find('lvs-repair-profile-prepare').text,'Prepare corrected LVS extraction profile v4');assert.match(text(find('lvs-repair-profile-card')),/loaded-definition inventory handling after a retained failed v3 execution/);assert.match(text(find('lvs-repair-profile-card')),/v3 bundle, failure and guard remain unchanged/);assert.equal(requests.length,0);
responder=async(route)=>{assert.equal(route,'lvs-workflow/repair-profile');return{...project.envelope,lvs_repair_session:{...prior,profile_version:'hullcirq-sky130-lvs-v4',bundle_sha256:'b'.repeat(64),upgrade_identity:{failed_v3_run_id:failed.id}},lvs_repair_preparation:{...upgrade,eligible:false},lvs_workflow:{...flow.data,runs:flow.data.runs.map(item=>({...item,freshness:'Stale'})),runtime_configuration:{profile:{profile_version:'hullcirq-sky130-lvs-v4'}}}};};
await flow.prepareRepairProfile();assert.equal(requests.length,1);assert.deepEqual(normalized(requests[0].body),{layout_run_id:layout.id,drc_run_id:drc.id,source_lvs_run_id:failed.id,revision_id:'current-gui-revision'});assert.equal(JSON.stringify([run,failed,prior]),original);assert.equal(flow.data.runs.length,2);assert.equal(find('lvs-repair-profile-prepare'),null);assert.equal(find('lvs-repair-profile-run').text,'Run LVS with prepared v4 profile');assert.match(text(find('lvs-repair-profile-status')),/failed_v3_run_id/);assert.equal(flow.selected().execution_status,'Failed');assert.equal(navigations.length,0);
await flow.prepareRepairProfile();flow.refresh();assert.equal(requests.length,1);responder=async()=>({...project.envelope,lvs_workflow:{...flow.data,runs:[...flow.data.runs,{id:'qa-new-v4',execution_status:'Queued'}],latest_run_id:'qa-new-v4'}});await flow.start();assert.equal(requests.length,2);assert.equal(requests[1].route,'lvs-workflow/runs');assert.equal(gets,0);
""")

    def test_v4_upgrade_requires_exact_failed_source_prior_bundle_and_historical_binding(self):
        self.client(r"""
const {failed,prior,upgrade}=installUpgrade();
for(const [object,key,value] of [[upgrade,'mode','unknown'],[upgrade,'profile_version','unknown'],[upgrade,'eligible',false],[prior,'configured',false],[prior,'bundle_present',false],[prior,'profile_version','unknown'],[prior,'bundle_sha256','mismatch'],[prior,'error',{message:'invalid priorbundle'}],[upgrade.source,'previous_profile_version','unknown'],[upgrade.source,'previous_bundle_sha256','c'.repeat(64)],[upgrade.source,'historical_lvs_run_id','other-seed'],[upgrade.source,'historical_lvs_record_sha256','d'.repeat(64)],[upgrade.source,'source_lvs_record_hash','e'.repeat(64)],[failed,'execution_status','Completed'],[failed,'validation_status','Not Checked'],[failed,'freshness','Stale'],[failed,'review_status','Accepted'],[failed.runtime_configuration.profile,'profile_version','unknown'],[flow.data,'latest_run_id','old-source']]){
 const saved=object[key];object[key]=value;assert.ok(flow.repairGate(),key);await flow.prepareRepairProfile();object[key]=saved;
}
project.dirty=true;await flow.prepareRepairProfile();project.dirty=false;project.readOnly=true;await flow.prepareRepairProfile();project.readOnly=false;flow.data.runs.push({id:'active',execution_status:'Running'});await flow.prepareRepairProfile();flow.data.runs.pop();assert.equal(requests.length,0);
""")

    def test_v4_upgrade_reply_is_dropped_if_prior_bundle_or_workspace_changes(self):
        self.client(r"""
const {prior}=installUpgrade();
for(const changed of ['bundle','workspace']){const wait=deferred(),old=project.envelope,noticeCount=notices.length,toastCount=toasts.length;responder=async()=>{await wait.promise;return{...old,marker:'OLD_UPGRADE'};};const pending=flow.prepareRepairProfile();
 if(changed==='bundle')project.envelope={...old,lvs_repair_session:{...prior,bundle_sha256:'f'.repeat(64)}};else project.envelope={...old,workspace_identity:{...old.workspace_identity,session_id:'changed'}};
 wait.resolve();await pending;assert.equal(project.envelope.marker,undefined);assert.equal(notices.length,noticeCount);assert.equal(toasts.length,toastCount);assert.equal(flow.busy,false);project.envelope=old;
}
assert.equal(requests.length,2);assert.ok(requests.every(item=>item.route==='lvs-workflow/repair-profile'));
""")

    def test_explicit_v5_upgrade_preserves_v3_v4_failures_and_requires_new_separate_run(self):
        self.client(r"""
const {failed,prior,upgrade}=installV5Upgrade(),before=JSON.stringify([flow.data.runs,prior]),original=JSON.stringify([run,layout,drc]);
assert.equal(flow.repairGate(),'');assert.equal(flow.repairSource().upgrade,true);assert.equal(find('lvs-repair-profile-prepare').text,'Prepare corrected LVS extraction profile v5');assert.match(text(find('lvs-repair-profile-card')),/explicit selected-cell extraction after a retained failed v4 execution/);assert.equal(requests.length,0);
responder=async(route)=>{assert.equal(route,'lvs-workflow/repair-profile');return{...project.envelope,lvs_repair_session:{...prior,profile_version:'hullcirq-sky130-lvs-v5',bundle_sha256:'e'.repeat(64),previous_bundle_sha256:prior.bundle_sha256,upgrade_identity:{failed_v4_run_id:failed.id}},lvs_repair_preparation:{...upgrade,eligible:false},lvs_workflow:{...flow.data,runs:flow.data.runs.map(item=>({...item,freshness:'Stale'})),runtime_configuration:{profile:{profile_version:'hullcirq-sky130-lvs-v5'}}}};};
await flow.prepareRepairProfile();assert.equal(requests.length,1);assert.deepEqual(normalized(requests[0].body),{layout_run_id:layout.id,drc_run_id:drc.id,source_lvs_run_id:failed.id,revision_id:'current-gui-revision'});assert.equal(JSON.stringify([run,layout,drc]),original);assert.equal(JSON.stringify(prior),JSON.parse(before)[1]&&JSON.stringify(JSON.parse(before)[1]));assert.equal(flow.data.runs.length,3);assert.equal(flow.selected().execution_status,'Failed');assert.equal(find('lvs-repair-profile-prepare'),null);assert.equal(find('lvs-repair-profile-run').text,'Run LVS with prepared v5 profile');assert.equal(navigations.length,0);assert.match(text(find('lvs-repair-profile-card')),/not a new LVS result/);
await flow.prepareRepairProfile();assert.equal(requests.length,1);responder=async()=>({...project.envelope,lvs_workflow:{...flow.data,latest_run_id:'qa-new-v5',runs:[...flow.data.runs,{id:'qa-new-v5',execution_status:'Queued'}]}});await flow.start();assert.equal(requests.length,2);assert.equal(requests[1].route,'lvs-workflow/runs');assert.equal(gets,0);
""")

    def test_v5_transition_rejects_skipped_unknown_or_wrong_source_versions_and_all_old_guards(self):
        self.client(r"""
const {failed,prior,upgrade}=installV5Upgrade();
for(const [object,key,value]of [[upgrade,'mode','upgrade_v6'],[upgrade,'profile_version','hullcirq-sky130-lvs-v6'],[upgrade,'mode','upgrade_v4'],[upgrade,'eligible',false],[prior,'profile_version','hullcirq-sky130-lvs-v3'],[prior,'bundle_sha256','f'.repeat(64)],[upgrade.source,'previous_profile_version','hullcirq-sky130-lvs-v3'],[upgrade.source,'source_lvs_run_id','qa-failed-v3'],[upgrade.source,'historical_lvs_run_id','wrong-original'],[upgrade.source,'historical_lvs_record_sha256','f'.repeat(64)],[failed.runtime_configuration.profile,'profile_version','hullcirq-sky130-lvs-v3'],[failed,'freshness','Stale'],[failed,'execution_status','Completed'],[failed,'record_hash','f'.repeat(64)]]){const saved=object[key];object[key]=value;assert.ok(flow.repairGate(),key);await flow.prepareRepairProfile();object[key]=saved;}
for(const keyofguard of ['readOnly','dirty','busy','conflict']){project[keyofguard]=keyofguard==='conflict'?'newer':true;await flow.prepareRepairProfile();project[keyofguard]=keyofguard==='conflict'?null:false;}
project.envelope.lvs_repair_session={...prior,profile_version:'hullcirq-sky130-lvs-v8'};flow.refresh();assert.equal(find('lvs-repair-profile-run'),null);assert.equal(find('lvs-repair-profile-prepare').disabled,true);assert.equal(requests.length,0);
""")

    def test_v5_delayed_upgrade_does_not_apply_after_v4_bundle_changes(self):
        self.client(r"""
const {prior}=installV5Upgrade(),wait=deferred(),old=project.envelope;responder=async()=>{await wait.promise;return{...old,marker:'OLD_V5'};};const pending=flow.prepareRepairProfile();project.envelope={...old,lvs_repair_session:{...prior,bundle_sha256:'f'.repeat(64)}};wait.resolve();await pending;assert.equal(project.envelope.marker,undefined);assert.equal(toasts.length,0);assert.equal(notices.length,0);assert.equal(flow.busy,false);assert.equal(requests.length,1);assert.equal(requests[0].body.source_lvs_run_id,'qa-failed-v4');
""")

    def test_v6_explicit_native_recognition_upgrade_retains_all_predecessor_records(self):
        self.client(r"""
const {failed,prior,upgrade}=installV6Upgrade(),oldRuns=flow.data.runs,before=JSON.stringify([oldRuns,prior,layout,drc,run]);assert.equal(flow.repairGate(),'');assert.equal(find('lvs-repair-profile-prepare').text,'Prepare corrected LVS extraction profile v6');assert.match(text(find('lvs-repair-profile-card')),/native MOS-capacitor parameter recognition/);assert.match(text(find('lvs-repair-profile-card')),/v5 bundle, failure and guard remain unchanged/);assert.equal(requests.length,0);
responder=async(route)=>{assert.equal(route,'lvs-workflow/repair-profile');return{...project.envelope,lvs_repair_session:{...prior,profile_version:'hullcirq-sky130-lvs-v6',bundle_sha256:'1'.repeat(64),previous_bundle_sha256:prior.bundle_sha256,upgrade_identity:{failed_v5_run_id:failed.id}},lvs_repair_preparation:{...upgrade,eligible:false},lvs_workflow:{...flow.data,runs:flow.data.runs.map(item=>({...item,freshness:'Stale'})),runtime_configuration:{profile:{profile_version:'hullcirq-sky130-lvs-v6'}}}};};
await flow.prepareRepairProfile();assert.equal(requests.length,1);assert.deepEqual(normalized(requests[0].body),{layout_run_id:layout.id,drc_run_id:drc.id,source_lvs_run_id:failed.id,revision_id:'current-gui-revision'});assert.equal(JSON.stringify([oldRuns,prior,layout,drc,run]),before);assert.equal(flow.data.runs.length,4);assert.equal(flow.selected().execution_status,'Failed');assert.equal(find('lvs-repair-profile-prepare'),null);assert.equal(find('lvs-repair-profile-run').text,'Run LVS with prepared v6 profile');assert.equal(navigations.length,0);flow.refresh();await flow.prepareRepairProfile();assert.equal(requests.length,1);
responder=async()=>({...project.envelope,lvs_workflow:{...flow.data,runs:[...flow.data.runs,{id:'qa-new-v6',execution_status:'Queued'}],latest_run_id:'qa-new-v6'}});await flow.start();assert.equal(requests.length,2);assert.equal(requests[1].route,'lvs-workflow/runs');assert.equal(gets,0);
""")

    def test_v6_fixed_transition_does_not_accept_old_bundle_skipped_version_or_stale_sources(self):
        self.client(r"""
const {failed,prior,upgrade}=installV6Upgrade();
for(const [object,key,value]of [[upgrade,'mode','upgrade_v7'],[upgrade,'profile_version','hullcirq-sky130-lvs-v7'],[upgrade,'mode','upgrade_v5'],[upgrade,'eligible',false],[prior,'profile_version','hullcirq-sky130-lvs-v4'],[prior,'bundle_sha256','0'.repeat(64)],[upgrade.source,'previous_profile_version','hullcirq-sky130-lvs-v4'],[upgrade.source,'previous_bundle_sha256','2'.repeat(64)],[upgrade.source,'historical_lvs_record_sha256','2'.repeat(64)],[upgrade.source,'source_lvs_run_id','qa-failed-v4'],[failed.runtime_configuration.profile,'profile_version','hullcirq-sky130-lvs-v4'],[failed,'freshness','Stale'],[failed,'review_status','Accepted'],[failed,'record_hash','0'.repeat(64)]]){const saved=object[key];object[key]=value;assert.ok(flow.repairGate(),key);await flow.prepareRepairProfile();object[key]=saved;}
for(const key of ['readOnly','dirty','busy','conflict']){project[key]=key==='conflict'?'newer':true;await flow.prepareRepairProfile();project[key]=key==='conflict'?null:false;}flow.data.runs.push({id:'active',execution_status:'Running'});await flow.prepareRepairProfile();flow.data.runs.pop();assert.equal(requests.length,0);
""")

    def test_v6_late_prepare_reply_after_predecessor_bundle_change_is_ignored(self):
        self.client(r"""
const {prior}=installV6Upgrade(),wait=deferred(),old=project.envelope;responder=async()=>{await wait.promise;return{...old,marker:'OLD_V6'};};const pending=flow.prepareRepairProfile();project.envelope={...old,lvs_repair_session:{...prior,bundle_sha256:'0'.repeat(64)}};wait.resolve();await pending;assert.equal(project.envelope.marker,undefined);assert.equal(toasts.length,0);assert.equal(notices.length,0);assert.equal(flow.busy,false);assert.equal(requests.length,1);assert.equal(requests[0].body.source_lvs_run_id,'qa-failed-v5');
""")

    def test_v7_completed_failed_comparison_prepares_only_then_requires_explicit_run(self):
        self.client(r"""
const {failed,prior,upgrade}=installV7Upgrade(),oldRuns=flow.data.runs,before=JSON.stringify([oldRuns,prior,layout,drc,run]);assert.equal(failed.execution_status,'Completed');assert.equal(failed.validation_status,'Failed');assert.equal(flow.repairGate(),'');assert.equal(find('lvs-repair-profile-prepare').text,'Prepare corrected LVS extraction profile v7');assert.match(text(find('lvs-repair-profile-card')),/raw extracted parameters in an explicit three-to-four-pin comparison mapping/);assert.equal(requests.length,0);
responder=async()=>({...project.envelope,lvs_repair_session:{...prior,profile_version:'hullcirq-sky130-lvs-v7',bundle_sha256:'4'.repeat(64),previous_bundle_sha256:prior.bundle_sha256,upgrade_identity:{failed_v6_run_id:failed.id}},lvs_repair_preparation:{...upgrade,eligible:false},lvs_workflow:{...flow.data,runs:flow.data.runs.map(item=>({...item,freshness:'Stale'})),runtime_configuration:{profile:{profile_version:'hullcirq-sky130-lvs-v7'}}}});
await flow.prepareRepairProfile();assert.equal(requests.length,1);assert.deepEqual(normalized(requests[0].body),{layout_run_id:layout.id,drc_run_id:drc.id,source_lvs_run_id:failed.id,revision_id:'current-gui-revision'});assert.equal(JSON.stringify([oldRuns,prior,layout,drc,run]),before);assert.equal(flow.data.runs.length,5);assert.equal(flow.selected().execution_status,'Completed');assert.equal(flow.selected().validation_status,'Failed');assert.equal(flow.selected().review_status,'Awaiting Review');assert.equal(find('lvs-repair-profile-prepare'),null);assert.equal(find('lvs-repair-profile-run').text,'Run LVS with prepared v7 profile');assert.equal(navigations.length,0);await flow.prepareRepairProfile();assert.equal(requests.length,1);
responder=async()=>({...project.envelope,lvs_workflow:{...flow.data,runs:[...flow.data.runs,{id:'qa-new-v7',execution_status:'Queued'}],latest_run_id:'qa-new-v7'}});await flow.start();assert.equal(requests.length,2);assert.equal(requests[1].route,'lvs-workflow/runs');assert.equal(gets,0);
""")

    def test_v7_rejects_incomplete_v6_failed_launch_and_preserves_old_failed_only_guards(self):
        self.client(r"""
const {failed,prior,upgrade}=installV7Upgrade();
for(const [object,key,value]of [[failed,'execution_status','Failed'],[failed,'execution_status','Running'],[failed,'validation_status','Passed'],[failed,'review_status','Accepted'],[failed,'freshness','Stale'],[upgrade,'eligible',false],[upgrade,'mode','upgrade_v8'],[upgrade,'profile_version','hullcirq-sky130-lvs-v8'],[prior,'profile_version','hullcirq-sky130-lvs-v5'],[prior,'bundle_sha256','0'.repeat(64)],[upgrade.source,'previous_profile_version','hullcirq-sky130-lvs-v5'],[upgrade.source,'historical_lvs_record_sha256','0'.repeat(64)],[failed,'record_hash','0'.repeat(64)]]){const saved=object[key];object[key]=value;assert.ok(flow.repairGate(),key);await flow.prepareRepairProfile();object[key]=saved;}
for(const key of ['readOnly','dirty','busy','conflict']){project[key]=key==='conflict'?'newer':true;await flow.prepareRepairProfile();project[key]=key==='conflict'?null:false;}
for(const install of [installUpgrade,installV5Upgrade,installV6Upgrade]){const old=install();assert.equal(flow.repairGate(),'');old.failed.execution_status='Completed';assert.ok(flow.repairGate(),'Earlier transition must remain executionFailed-only');await flow.prepareRepairProfile();}
assert.equal(requests.length,0);
""")

    def test_v7_late_completed_failure_upgrade_reply_is_source_bound(self):
        self.client(r"""
const {prior}=installV7Upgrade(),wait=deferred(),old=project.envelope;responder=async()=>{await wait.promise;return{...old,marker:'OLD_V7'};};const pending=flow.prepareRepairProfile();project.envelope={...old,lvs_repair_session:{...prior,bundle_sha256:'0'.repeat(64)}};wait.resolve();await pending;assert.equal(project.envelope.marker,undefined);assert.equal(toasts.length,0);assert.equal(notices.length,0);assert.equal(flow.busy,false);assert.equal(requests.length,1);assert.equal(requests[0].body.source_lvs_run_id,'qa-failed-v6');
""")

    def test_new_warning_source_prepares_latest_v7_directly_without_ancestors_or_tool_run(self):
        self.client(r"""
const initial=installInitialV7(),before=JSON.stringify([run,layout,drc]),oldPolicy=JSON.stringify(project.envelope.review_policy);assert.equal(flow.repairGate(),'');assert.equal(find('lvs-repair-profile-prepare').text,'Prepare corrected LVS extraction profile v7');assert.match(text(find('lvs-repair-profile-card')),/latest v7 profile directly/);assert.equal(flow.data.runs.length,1);assert.equal(requests.length,0);assert.equal(gets,0);
responder=async()=>({...project.envelope,lvs_repair_session:{configured:true,bundle_present:true,error:null,profile_version:'hullcirq-sky130-lvs-v7',preparation_kind:'direct_v7',bundle_sha256:'4'.repeat(64),source_identity:{historical_lvs_run_id:run.id,historical_lvs_record_sha256:initial.source.source_lvs_record_sha256}},lvs_repair_preparation:{...initial,eligible:false},lvs_workflow:{...flow.data,accepted_run_id:null,runs:[{...run,freshness:'Stale'}],runtime_configuration:{profile:{profile_version:'hullcirq-sky130-lvs-v7'}}}});
await flow.prepareRepairProfile();assert.deepEqual(normalized(requests),[{route:'lvs-workflow/repair-profile',body:{layout_run_id:layout.id,drc_run_id:drc.id,source_lvs_run_id:run.id,revision_id:'current-gui-revision'}}]);assert.equal(JSON.stringify([run,layout,drc]),before);assert.equal(JSON.stringify(project.envelope.review_policy),oldPolicy);assert.equal(flow.data.runs.length,1);assert.equal(project.envelope.lvs_repair_session.upgrade_identity,undefined);assert.equal(project.envelope.lvs_repair_session.previous_bundle_sha256,undefined);assert.equal(find('lvs-repair-profile-run').text,'Run LVS with prepared v7 profile');assert.equal(find('lvs-repair-profile-prepare'),null);assert.match(text(find('lvs-repair-profile-status')),/direct_v7/);assert.equal(navigations.length,0);await flow.prepareRepairProfile();assert.equal(requests.length,1);
responder=async()=>({...project.envelope,lvs_workflow:{...flow.data,runs:[...flow.data.runs,{id:'qa-direct-v7',execution_status:'Queued'}],latest_run_id:'qa-direct-v7'}});await flow.start();assert.equal(requests.length,2);assert.equal(requests[1].route,'lvs-workflow/runs');assert.equal(gets,0);
""")

    def test_initial_v7_requires_exact_original_v2_current_source_and_no_existing_bundle(self):
        self.client(r"""
const initial=installInitialV7();
for(const [object,key,value]of [[initial,'mode','initial_v6'],[initial,'profile_version','hullcirq-sky130-lvs-v6'],[initial,'mode',null],[initial.source,'source_lvs_run_id','other'],[initial.source,'source_lvs_record_hash','0'.repeat(64)],[initial.source,'revision_id','old-gui'],[run.runtime_configuration.profile,'profile_version','hullcirq-sky130-lvs-v6'],[run,'freshness','Stale'],[run,'review_status','Changes Requested'],[run,'validation_status','Failed'],[flow.data,'latest_run_id','other'],[flow.data,'accepted_run_id',null]]){const old=object[key];object[key]=value;assert.ok(flow.repairGate(),key);await flow.prepareRepairProfile();object[key]=old;}
for(const saved of [{configured:true,bundle_present:true,profile_version:'hullcirq-sky130-lvs-v6'},{configured:false,bundle_present:true,error:{message:'retained bundle'}},{configured:false,bundle_present:false,error:{message:'unresolved profile'}}]){project.envelope.lvs_repair_session=saved;assert.ok(flow.repairGate());assert.equal(flow.repairSource(),null);await flow.prepareRepairProfile();delete project.envelope.lvs_repair_session;}
for(const key of ['readOnly','dirty','conflict','busy']){project[key]=key==='conflict'?'newer':true;await flow.prepareRepairProfile();project[key]=key==='conflict'?null:false;}flow.data.runs.push({id:'active',execution_status:'Running'});await flow.prepareRepairProfile();flow.data.runs.pop();assert.equal(requests.length,0);assert.equal(gets,0);
""")

    def test_initial_v7_unreviewed_source_requires_no_adoption_and_does_not_adopt(self):
        self.client(r"""
installInitialV7();run.review_status='Awaiting Review';flow.data.accepted_run_id=null;
flow.refresh();assert.equal(flow.repairGate(),'');const before=JSON.stringify(run);
responder=async()=>({...project.envelope,lvs_repair_session:{...session,profile_version:'hullcirq-sky130-lvs-v7'}});
await flow.prepareRepairProfile();assert.equal(requests.length,1);assert.equal(requests[0].route,'lvs-workflow/repair-profile');
assert.equal(JSON.stringify(run),before);assert.equal(flow.data.reviews.length,0);assert.equal(flow.data.accepted_run_id,null);
""")

    def test_initial_v7_delayed_reply_cannot_cross_project_session_or_source_changes(self):
        self.client(r"""
installInitialV7();const wait=deferred(),old=project.envelope;responder=async()=>{await wait.promise;return{...old,marker:'OLD_DIRECT_V7'};};const pending=flow.prepareRepairProfile();project.envelope={...old,workspace_identity:{...old.workspace_identity,project_id:'other-project',session_id:'other-session'}};wait.resolve();await pending;assert.equal(project.envelope.marker,undefined);assert.equal(project.envelope.lvs_repair_session,undefined);assert.equal(notices.length,0);assert.equal(toasts.length,0);assert.equal(flow.busy,false);assert.equal(requests.length,1);assert.equal(requests[0].body.source_lvs_run_id,run.id);
""")

    def test_recognition_proof_is_readonly_and_only_uses_fixed_artifact_route(self):
        self.client(r"""
run.checks.summary.extraction.recognition_proof={model:'SOFTWARE QA fixed-model',device_count:4,model_sha256:'8'.repeat(64),pins:['G','B'],scope:'SOFTWARE QA only, not a waiver'};
const extensions={'extraction-model-proof':'json','extraction-raw-spice':'spice','extraction-models':'spice','extraction-deck':'tech','extraction-inventory-pre-gds':'json','extraction-inventory-post-gds':'json','extraction-inventory-post-annotation':'json'};
run.artifacts=[...Object.entries(extensions).map(([id,extension])=>({id,url:flow.artifactURL(run,id),sha256:'9'.repeat(64),bytes:123,content_type:extension==='json'?'application/json':'text/plain'})),{id:'extraction-model-proof',url:'/arbitrary/other.json'},{id:'extraction-deck',url:'/arbitrary/other.tech'},{id:'extraction-inventory-post-annotation',url:'/arbitrary/inventory.json'},{id:'unknown-waiver',url:'/arbitrary/waiver.json'}];
flow.refresh();assert.match(text(find('lvs-workflow-recognition-proof')),/fixed-model/);assert.match(text(find('lvs-workflow-recognition-proof')),/not a waiver/);assert.equal(flow.artifacts(run).length,7);
for(const [id,extension]of Object.entries(extensions)){assert.ok(find('lvs-workflow-download-'+id));assert.equal(vm.runInContext(`EXTENSIONS[${JSON.stringify(id)}]`,sandbox),extension);}
run.artifacts=[];flow.refresh();for(const id of Object.keys(extensions))assert.equal(find('lvs-workflow-download-'+id),null);
assert.equal(requests.length,0);assert.equal(gets,0);
""")


if __name__ == '__main__':
    unittest.main()

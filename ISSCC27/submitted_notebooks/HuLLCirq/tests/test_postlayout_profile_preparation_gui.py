"""Preparation-only S14 identities; isolated DOM/API doubles, no live tools."""
import shutil
import subprocess
import unittest

from test_postlayout_workflow_gui import CLIENT, PROJECT


PREPARATION = r"""
layout.record_hash='1'.repeat(64); drc.record_hash='2'.repeat(64); lvs.record_hash='3'.repeat(64);
layout.runtime_configuration_sha256='4'.repeat(64); layout.verification_plan_sha256='5'.repeat(64); layout.settings_sha256='6'.repeat(64);
layout.verification_plan={kind:'generic_cycle_vectors',vector_count:21};
const preparation={available:true,scope:'adopted_source_chain_for_explicit_profile_preparation_only',revision_id:project.envelope.revision.id,source_revision_id:layout.revision_id,layout_run_id:layout.id,drc_run_id:drc.id,lvs_run_id:lvs.id,layout_record_hash:layout.record_hash,drc_record_hash:drc.record_hash,lvs_record_hash:lvs.record_hash,physical_runtime_sha256:layout.runtime_configuration_sha256,verification_plan_sha256:layout.verification_plan_sha256,settings_sha256:layout.settings_sha256,blocked_reason:null};
flow.data={...flow.data,ready:false,tool_ready:true,layout_run_id:null,drc_run_id:null,lvs_run_id:null,source_inputs:null,profile_prepare_available:true,profile_prepare_needed:true,profile_preparation_sources:preparation,blocked_reason:'Saved S14 profile belongs to an earlier physical runtime.'};
project.envelope.postlayout_workflow=flow.data;flow.refresh();
"""


class PostlayoutProfilePreparationGuiTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated S14 preparation fixtures.')
        result = subprocess.run([node, '-e', CLIENT + PREPARATION + '\n(async()=>{\n' + body +
                                 '\n})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});'],
                                cwd=PROJECT, capture_output=True, text=True, encoding='utf-8', timeout=25)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_installed_old_profile_allows_explicit_prepare_but_not_run_or_repair(self):
        self.client(r"""
const before=JSON.stringify([layout,drc,lvs]),configuration=JSON.stringify(flow.data.runtime_configuration);
assert.equal(flow.sources(),null);assert.equal(flow.preparationSources().layout.id,layout.id);assert.equal(flow.prepareGate(),'');
assert.equal(find('postlayout-workflow-prepare').hidden,false);assert.equal(find('postlayout-workflow-prepare').disabled,false);assert.equal(find('postlayout-workflow-run').disabled,true);
assert.equal(flow.blocker().setup_action.testId,'postlayout-workflow-prepare');assert.match(text(find('postlayout-workflow-lineage')),new RegExp(layout.id));
flow.refresh();await flow.start();assert.equal(requests.length,0);assert.equal(flow.physicalRepairEligible(record()),false);
responder=async(route)=>{assert.equal(route,'postlayout-workflow/profile');return{...project.envelope,postlayout_workflow:{...flow.data,ready:true,profile_prepare_needed:false,profile_preparation_sources:null,layout_run_id:layout.id,drc_run_id:drc.id,lvs_run_id:lvs.id}};};
await flow.prepare();assert.equal(requests.length,1);assert.deepEqual(normalized(requests[0].body),{layout_run_id:layout.id,drc_run_id:drc.id,lvs_run_id:lvs.id,revision_id:project.envelope.revision.id});
assert.equal(JSON.stringify([layout,drc,lvs]),before);assert.equal(JSON.stringify(flow.data.runtime_configuration),configuration);assert.equal(flow.data.runs.length,0);assert.equal(find('postlayout-workflow-run').disabled,false);assert.match(toasts.at(-1),/No EDA, model or S14 verification attempt was started/);
""")

    def test_preparation_metadata_never_bypasses_exact_chain_hash_or_context_guards(self):
        self.client(r"""
for(const key of ['scope','revision_id','source_revision_id','layout_run_id','drc_run_id','lvs_run_id','layout_record_hash','drc_record_hash','lvs_record_hash','physical_runtime_sha256','verification_plan_sha256','settings_sha256']){
 const saved=preparation[key];preparation[key]='other-context-or-hash';flow.refresh();assert.equal(flow.preparationSources(),null,key);assert.ok(flow.prepareGate(),key);assert.equal(find('postlayout-workflow-prepare').disabled,true,key);await flow.prepare();preparation[key]=saved;
}
for(const [object,key,value] of [[preparation,'available',false],[layout,'freshness','Stale'],[drc,'review_status','Awaiting Review'],[lvs,'layout_run_id','old-layout'],[project.envelope.physical_workflow,'latest_run_id','new-layout'],[layout,'record_hash',null],[flow.data,'profile_prepare_available',false]]){
 const saved=object[key];object[key]=value;assert.equal(flow.preparationSources(),null,key);await flow.prepare();object[key]=saved;
}
for(const key of ['readOnly','dirty','busy','conflict']){project[key]=key==='conflict'?'newer':true;assert.ok(flow.prepareGate());await flow.prepare();project[key]=key==='conflict'?null:false;}
project.envelope.workspace_identity={read_only:true};await flow.prepare();project.envelope.workspace_identity={read_only:false};
flow.data.runs.push({id:'other-active',execution_status:'Running'});await flow.prepare();flow.data.runs=[];
preparation.available=false;preparation.blocked_reason='Current adopted source proof is unavailable.';assert.equal(flow.prepareGate(),preparation.blocked_reason);assert.equal(requests.length,0);
""")

    def test_adapter_metadata_save_uses_preparation_identity_without_enabling_execution(self):
        self.client(r"""
const contract={version:'external-port-functional-v1',testbench_module:'fixture_tb',dut_instance:'dut',clock_signal:'clock_i',clock_statement:'always #25 clock_i=~clock_i;',timeout_statement:'initial begin #1000;',output_prefix:'OUTPUT',pass_marker:'PASS',failure_markers:['FAIL']};
flow.data.adapter_contract_editable=true;flow.data.adapter_contract=contract;flow.data.adapter_contract_sha256='7'.repeat(64);flow.refresh();
const draft=flow.adapterDraft();draft.text=JSON.stringify({...contract,pass_marker:'PASS_EXACT'});flow.refresh();assert.equal(flow.adapterSaveGate(),'');assert.equal(flow.prepareGate(),'Save the project-specific adapter metadata before preparing S14.');assert.equal(flow.adapterBackup().length,1);
responder=async(route,body)=>{assert.equal(route,'postlayout-workflow/adapter-contract');return{...project.envelope,postlayout_workflow:{...flow.data,adapter_contract:body.contract,adapter_contract_sha256:'8'.repeat(64)}};};
await flow.saveAdapterContract();assert.equal(requests.length,1);assert.equal(requests[0].body.layout_run_id,layout.id);assert.equal(requests[0].body.contract.pass_marker,'PASS_EXACT');assert.equal(flow.adapterBackup().length,0);assert.equal(flow.data.ready,false);assert.equal(flow.sources(),null);assert.ok(flow.gate());assert.equal(find('postlayout-workflow-run').disabled,true);
assert.ok(requests.every(r=>!r.route.endsWith('/runs')&&!r.route.endsWith('/review')));
""")

    def test_presentation_revision_alias_prepares_current_request_without_rewriting_source_revision(self):
        self.client(r"""
const sourceRevision=layout.revision_id;project.envelope.revision.id='current-presentation-only-revision';preparation.revision_id=project.envelope.revision.id;
assert.equal(preparation.source_revision_id,sourceRevision);assert.notEqual(sourceRevision,project.envelope.revision.id);assert.equal(flow.sources(),null);assert.equal(flow.preparationSources().layout.revision_id,sourceRevision);assert.equal(flow.prepareGate(),'');
responder=async()=>project.envelope;await flow.prepare();assert.equal(requests.length,1);assert.equal(requests[0].body.revision_id,'current-presentation-only-revision');assert.equal(requests[0].body.layout_run_id,layout.id);assert.equal(layout.revision_id,sourceRevision);assert.ok(flow.gate());
preparation.source_revision_id=project.envelope.revision.id;assert.equal(flow.preparationSources(),null);
""")

    def test_delayed_profile_prepare_reply_or_error_from_other_context_is_ignored(self):
        self.client(r"""
for(const rejected of [false,true]){
 const wait=deferred(),old=project.envelope,noticesBefore=notices.length,toastsBefore=toasts.length;
 responder=async()=>{await wait.promise;if(rejected)throw Error('OLD_PROFILE_PREPARATION');return{...old,marker:'OLD_PREPARE_RESPONSE'};};
 const pending=flow.prepare();project.envelope={...old,workspace_identity:{project_id:'other-project',system_id:'other-system',session_id:'other-session'}};wait.resolve();await pending;
 assert.equal(project.envelope.marker,undefined);assert.equal(notices.length,noticesBefore);assert.equal(toasts.length,toastsBefore);assert.equal(flow.busy,false);project.envelope=old;
}
assert.equal(requests.length,2);assert.ok(requests.every(r=>r.route==='postlayout-workflow/profile'));
""")


if __name__ == '__main__':
    unittest.main()

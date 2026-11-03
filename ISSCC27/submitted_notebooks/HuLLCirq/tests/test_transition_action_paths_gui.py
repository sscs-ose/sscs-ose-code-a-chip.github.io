"""Actual DOM button handlers with an isolated API double, never real EDA/LLM."""
from pathlib import Path
import shutil
import subprocess
import unittest

from test_repair_prompt_console_gui import CLIENT

PROJECT = Path(__file__).resolve().parents[1]
SETUP = r"""
const names=[['generation.js','GenerationWorkspace'],['workflow.js','LocalWorkflow'],['implementation_specs.js','NodeImplementationSpecs'],['global_generation.js','GlobalGeneration'],['global_workflow.js','GlobalWorkflow'],['physical_workflow.js','PhysicalWorkflow'],['drc_workflow.js','DRCWorkflow'],['lvs_workflow.js','LVSWorkflow'],['postlayout_workflow.js','PostlayoutWorkflow']];
const types={};for(const [file,name]of names)types[name]=(await module(file))[name];
const stages=['global_settings','graph_editor','specifications','local_rtl_generation','local_synthesis','local_netlist_simulation','node_implementation_specs','global_rtl_generation','global_synthesis','global_netlist_simulation','layout','drc','lvs','post_layout_verification'];
document.activeElement=document.body;const routes=[];const flush=async()=>{for(let i=0;i<15;i++)await Promise.resolve()};
const createElement=document.createElement;document.createElement=tag=>{const node=createElement(tag);node.classList.toggle=(name,force)=>{if(force??!node.classList.contains(name))node.classList.add(name);else node.classList.remove(name);};return node;};
function change(input,value){assert.ok(input);input.value=value;for(const callback of input.listeners.change||[])callback({target:input,currentTarget:input});for(const callback of input.listeners.input||[])callback({target:input,currentTarget:input});}
async function click(input){assert.ok(input);assert.equal(input.disabled,false,'The requested UI action must be enabled');input.click();await flush();}
const meta={
 local_rtl_generation:['GenerationWorkspace','generation','jobs','generation-feedback','accept-candidate','return-candidate-stage','generation-return-stage','continue-local-synthesis','request-candidate-changes','cancel-generation','reconnect-generation'],
 local_synthesis:['LocalWorkflow',null,'workflow_runs','workflow-feedback','workflow-accept','workflow-return-rtl',null,'workflow-continue','workflow-request-changes','workflow-cancel','workflow-reconnect'],
 local_netlist_simulation:['LocalWorkflow',null,'workflow_runs','workflow-feedback','workflow-accept','workflow-return-rtl',null,'workflow-continue','workflow-request-changes','workflow-cancel','workflow-reconnect'],
 node_implementation_specs:['NodeImplementationSpecs',null,'implementation_specs','implementation-feedback','implementation-accept','implementation-return','implementation-return-stage','implementation-continue','implementation-request-changes',null,null],
 global_rtl_generation:['GlobalGeneration','global_generation','jobs','global-review-note','global-accept','global-return',null,'global-continue','global-request-changes','global-cancel','global-refresh'],
 global_synthesis:['GlobalWorkflow','global_workflow','runs','global-workflow-feedback','global-workflow-accept','global-workflow-return','global-workflow-return-target','global-workflow-continue','global-workflow-request-changes','global-workflow-cancel','global-workflow-reconnect'],
 global_netlist_simulation:['GlobalWorkflow','global_workflow','runs','global-workflow-feedback','global-workflow-accept','global-workflow-return','global-workflow-return-target','global-workflow-continue','global-workflow-request-changes','global-workflow-cancel','global-workflow-reconnect'],
 layout:['PhysicalWorkflow','physical_workflow','runs','physical-workflow-feedback','physical-workflow-accept','physical-workflow-return','physical-workflow-return-target','physical-workflow-continue','physical-workflow-request-changes','physical-workflow-cancel','physical-workflow-reconnect'],
 drc:['DRCWorkflow','drc_workflow','runs','drc-workflow-feedback','drc-workflow-accept','drc-workflow-return','drc-workflow-return-target','drc-workflow-continue','drc-workflow-request-changes','drc-workflow-cancel','drc-workflow-reconnect'],
 lvs:['LVSWorkflow','lvs_workflow','runs','lvs-workflow-feedback','lvs-workflow-accept','lvs-workflow-return','lvs-workflow-return-target','lvs-workflow-continue','lvs-workflow-request-changes','lvs-workflow-cancel','lvs-workflow-reconnect'],
 post_layout_verification:['PostlayoutWorkflow','postlayout_workflow','runs','postlayout-workflow-feedback','postlayout-workflow-accept','postlayout-workflow-return','postlayout-workflow-return-target',null,'postlayout-workflow-request-changes','postlayout-workflow-cancel','postlayout-workflow-reconnect']};
function factory(stage){
 project.stage=stage;Object.assign(project,{dirty:false,conflict:null,busy:false,readOnly:false,postlayoutRunning:false,lvsRunning:false});
 const record=(id,stage_id,extra={})=>({id,stage_id,node_id:'node-a',revision_id:'revision-a',requested_revision_id:'revision-a',input_hash:'input-a',rtl_sha256:'rtl-sha',netlist_sha256:'net-sha',execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',finished_at:'saved',checks:{interface:{validation_status:'Passed'},executed:true},rtl:'module qa_control;endmodule',netlist:'module net;endmodule',diagnostics:[],events:[],artifacts:[],...extra});
 const localJob=record('local-rtl','local_rtl_generation'),s05=record('local-s05','local_synthesis',{candidate_id:localJob.id}),s06=record('local-s06','local_netlist_simulation',{candidate_id:localJob.id,prior_run_id:s05.id}),spec=record('spec','node_implementation_specs',{candidate_id:localJob.id,source_run_id:s06.id}),global=record('global-rtl','global_rtl_generation'),s09=record('global-s09','global_synthesis',{global_job_id:global.id}),s10=record('global-s10','global_netlist_simulation',{global_job_id:global.id,synthesis_run_id:s09.id}),layout=record('layout','layout',{artifacts:[{id:'gds',sha256:'gds-sha'},{id:'netlist',sha256:'mapped-sha'}]}),drc=record('drc','drc',{layout_run_id:layout.id,input_gds_sha256:'gds-sha'}),lvs=record('lvs','lvs',{layout_run_id:layout.id,drc_run_id:drc.id,input_gds_sha256:'gds-sha',input_netlist_sha256:'mapped-sha'}),post=record('post','post_layout_verification',{layout_run_id:layout.id,drc_run_id:drc.id,lvs_run_id:lvs.id,execution_scope:'post_route_functional_plus_sta',runtime_configuration:{verification_supported:true}});
 const records={[stages[3]]:localJob,[stages[4]]:s05,[stages[5]]:s06,[stages[6]]:spec,[stages[7]]:global,[stages[8]]:s09,[stages[9]]:s10,[stages[10]]:layout,[stages[11]]:drc,[stages[12]]:lvs,[stages[13]]:post},run=records[stage];run.review_status='Awaiting Review';
 const family=(values)=>({implemented:true,ready:true,tool_ready:true,runs:values,reviews:[],latest_run_id:values.at(-1).id,accepted_run_id:values.at(-1).id});
 project.envelope={workspace_identity:{session_id:'isolated-session',read_only:false},revision:{id:'revision-a'},workflow:stages.map(id=>({id,implemented:true,review_status:'Accepted',freshness:'Current'})),review_policy:{mode:'manual',user_authorized:true},llm:{profile_revision_id:'profile-a'},generation:{implemented:true,jobs:[localJob],nodes:[{node_id:'node-a',latest_job_id:localJob.id,accepted_job_id:localJob.id,review_status:localJob.review_status,freshness:'Current'}],reviews:[]},workflow_runs:[s05,s06],workflow_reviews:[],implementation_specs:[spec],implementation_spec_nodes:[{node_id:spec.node_id,latest_spec_id:spec.id,accepted_spec_id:spec.id,source_run_id:s06.id,ready:true}],implementation_spec_reviews:[],global_generation:{implemented:true,ready:true,jobs:[global],reviews:[],accepted_job_id:global.id,latest_job_id:global.id},global_workflow:{...family([s09,s10]),stages:[{stage_id:'global_synthesis',accepted_run_id:s09.id,latest_run_id:s09.id},{stage_id:'global_netlist_simulation',accepted_run_id:s10.id,latest_run_id:s10.id}]},physical_workflow:family([layout]),drc_workflow:family([drc]),lvs_workflow:family([lvs]),postlayout_workflow:{...family([post]),verification_supported:true,execution_scope:'post_route_functional_plus_sta'}};
 const m=meta[stage],calls=[],nav=[],messages=[],original=JSON.stringify(records),source=structuredClone(project.envelope);let flow;
 const list=e=>m[1]?e[m[1]][m[2]]:e[m[2]];
 const cb={project:()=>project,chrome:()=>{},notify:x=>messages.push(x),toast:x=>messages.push(x),navigate:(...args)=>nav.push(args),connection:()=>{},request:async(route,body)=>{calls.push({route,body});const e=structuredClone(project.envelope);if(route.includes('/review')||route==='generation/review'||route==='implementation-specs/review'){const item=list(e).find(x=>x.id===run.id);item.review_status=body.decision==='accepted'?'Accepted':body.decision==='changes_requested'?'Changes Requested':'Returned';}if(route.includes('/cancel'))list(e).find(x=>x.id===run.id).execution_status='Cancelled';if(/^generation\/jobs\//.test(route)||/^workflow\/runs\//.test(route)||/^implementation-specs\//.test(route)&&route!=='implementation-specs/review')return structuredClone(run);if(route==='global-generation')return {global_generation:e.global_generation};return e;},envelope:e=>{Object.assign(project.envelope,e);flow.receive(project.envelope);}};
 flow=new types[m[0]](cb);flow.nodeId='node-a';flow.receive(project.envelope);if(m[0]==='GenerationWorkspace')flow.selectedJobId=run.id;
 const review=new DOMNode();flow.renderReview(review);
 return {stage,m,flow,run,records,original,source,review,calls,nav,messages,refresh:()=>flow.renderReview(review),selected:()=>m[0]==='GenerationWorkspace'?flow.selectedJob():flow.selected()};
}
"""


class TransitionActionPathsGuiTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node required for isolated UI action paths')
        result = subprocess.run([node, '--experimental-vm-modules', '-e', CLIENT + '\n(async()=>{\n' + SETUP + body + '\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});'], cwd=PROJECT, capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_return_destination_uses_real_field_and_button_handler(self):
        self.client(r"""
let count=0;for(const stage of stages.slice(3)){const sample=factory(stage),selector=sample.m[6]&&test(sample.review,sample.m[6]),targets=selector?selector.children.map(option=>option.value):[stage==='global_rtl_generation'?'node_implementation_specs':'local_rtl_generation'];const expected=stage==='local_rtl_generation'?stages.slice(0,3):['local_synthesis','local_netlist_simulation'].includes(stage)?['local_rtl_generation']:stage==='node_implementation_specs'?stages.slice(0,6):stage==='global_rtl_generation'?['node_implementation_specs']:stages.slice(0,stages.indexOf(stage));assert.deepEqual(targets,expected,stage+' exposes every required earlier destination');for(const target of targets){const x=factory(stage);change(test(x.review,x.m[3]),'  Correct the observed issue  ');if(x.m[6])change(test(x.review,x.m[6]),target);await click(test(x.review,x.m[5]));assert.equal(x.calls.length,1,stage+' / '+target);assert.equal(x.calls[0].body.decision,'return_to_stage');assert.equal(x.calls[0].body.target_stage,target);assert.match(x.calls[0].body.note,/Correct the observed issue/);assert.equal(x.nav.at(-1)[0],target);assert.equal(JSON.stringify(x.records),x.original);count++;}}
assert.equal(count,75);console.log('75 actual Return destination field/button routes Passed');
""")

    def test_all_eleven_controllers_adopt_then_continue_without_an_execution_request(self):
        self.client(r"""
for(const stage of stages.slice(3)){const x=factory(stage);await click(test(x.review,x.m[4]));assert.equal(x.calls.length,1,stage);assert.equal(x.calls[0].body.decision,'accepted');assert.equal(x.selected().review_status,'Accepted');assert.equal(JSON.stringify(x.records),x.original);x.refresh();assert.equal(test(x.review,x.m[4]).disabled,true,stage+' cannot repeat accepted adoption');if(x.m[7]){await click(test(x.review,x.m[7]));assert.equal(x.nav.at(-1)[0],stages[stages.indexOf(stage)+1]);assert.equal(x.calls.length,1,'Continue must only navigate');}}
console.log('11 adoption plus 10 Continue handlers Passed');
""")

    def test_failed_stale_dirty_active_and_nonlatest_results_disable_adoption(self):
        self.client(r"""
let count=0;for(const stage of stages.slice(3))for(const kind of ['failed','stale','dirty','active','nonlatest']){const x=factory(stage);if(kind==='failed'){x.run.validation_status='Failed';if(stage==='local_rtl_generation')x.run.checks.interface.validation_status='Failed';}if(kind==='stale')x.run.freshness='Stale';if(kind==='dirty')project.dirty=true;if(kind==='active')x.run.execution_status='Running';if(kind==='nonlatest'){const newer={...structuredClone(x.run),id:x.run.id+'-newer'};if(x.m[1]){x.flow.data?x.flow.data[x.m[2]].push(newer):x.flow.generation.jobs.push(newer);if(x.flow.data)x.flow.data.latest_run_id=newer.id;}else if(x.m[0]==='NodeImplementationSpecs'){x.flow.specs.push(newer);Object.assign(project.envelope.implementation_spec_nodes[0],{latest_spec_id:newer.id,accepted_spec_id:newer.id});}else x.flow.runs.push(newer);if(x.m[0]==='GenerationWorkspace'){x.flow.generation.nodes[0].latest_job_id=newer.id;x.flow.selectedJobId=x.run.id;}else if(x.m[0]==='NodeImplementationSpecs')x.flow.specId=x.run.id;else if(stage==='global_rtl_generation')x.flow.selectedId=x.run.id;else x.flow.runId=x.run.id;}x.refresh();const accept=test(x.review,x.m[4]);assert.ok(!accept||accept.disabled===true,stage+' '+kind);assert.equal(x.calls.length,0);count++;}assert.equal(count,55);
""")

    def test_empty_changes_and_return_reason_never_submit_or_change_saved_evidence(self):
        self.client(r"""
for(const stage of stages.slice(3))for(const index of [5,8]){const x=factory(stage);change(test(x.review,x.m[3]),'   ');await click(test(x.review,x.m[index]));assert.equal(x.calls.length,0,stage+' empty reason');assert.equal(JSON.stringify(x.records),x.original);assert.ok(x.messages.length,stage+' must explain required reason');if(stage==='global_rtl_generation'){const input=test(x.review,'global-review-note');assert.equal(input.focusCount,1);assert.equal(input.scrollCount,1);assert.match(x.messages.at(-1),/reason.*feedback/);}}
""")

    def test_cancel_buttons_send_only_exact_saved_run_identity(self):
        self.client(r"""
let count=0;for(const stage of stages.slice(3).filter(id=>id!=='node_implementation_specs')){const x=factory(stage);x.run.execution_status='Running';x.run.finished_at=null;const result=new DOMNode(),host=new DOMNode();const resultId=x.m[0]==='GenerationWorkspace'?'generation-result-content':stage==='global_rtl_generation'?'global-result':x.m[0]==='LocalWorkflow'?'workflow-result':x.m[1].replaceAll('_','-')+'-result';if(resultId==='generation-result-content')result.id=resultId;else result.setAttribute('data-testid',resultId);host.append(result);x.flow.host=host;x.flow.renderResult();await click(test(host,x.m[9]));assert.equal(x.calls.length,1,stage);assert.match(x.calls[0].route,/cancel$/);const body=x.calls[0].body;assert.ok(body.job_id===x.run.id||body.run_id===x.run.id||Object.keys(body).length===0);assert.equal(x.selected().execution_status,'Cancelled');assert.equal(x.run.execution_status,'Running','Original fixture record retained');count++;}assert.equal(count,10);
""")

    def test_reconnect_controls_only_read_saved_state_and_never_resubmit(self):
        self.client(r"""
let count=0;for(const stage of stages.slice(3).filter(id=>id!=='node_implementation_specs')){const x=factory(stage),host=new DOMNode();if(x.m[0]==='GenerationWorkspace'){const result=new DOMNode();result.id='generation-result-content';host.append(result);x.flow.host=host;x.flow.pollFailure='Lost observation';x.flow.renderResult();}else if(stage==='global_rtl_generation'){x.flow.render(host);}else if(x.m[0]==='LocalWorkflow'){const result=new DOMNode();result.setAttribute('data-testid','workflow-result');host.append(result);x.flow.host=host;x.flow.pollError='Lost observation';x.flow.renderResult();}else{ x.flow.pollError='Lost observation';x.flow.uncertainStart=true;host.append(x.flow.reconnectControl?x.flow.reconnectControl():x.flow.reconnect());}
const before=JSON.stringify(x.records);await click(test(host,x.m[10]));assert.ok(x.calls.length>=1,stage);for(const call of x.calls){assert.equal(call.body,undefined);assert.doesNotMatch(call.route,/start|cancel|review|context/);assert.ok(call.route==='project'||call.route==='global-generation'||/^(generation\/jobs|workflow\/runs)\//.test(call.route));}assert.equal(JSON.stringify(x.records),before,'Reconnect preserves saved records');count++;}assert.equal(count,10);
""")

    def test_s14_diagnostic_modes_cannot_be_adopted_as_completed_verification(self):
        self.client(r"""
for(const scope of ['compatibility_preflight_only','saved_dynamic_diagnostic_review','saved_event_diagnostic_review']){const x=factory('post_layout_verification');x.run.execution_scope=scope;x.run.runtime_configuration.verification_supported=false;x.refresh();assert.equal(test(x.review,x.m[4]).disabled,true);assert.equal(x.calls.length,0);assert.equal(x.selected().review_status,'Awaiting Review');}
""")

    def test_nonempty_changes_requests_are_saved_by_each_controller_without_navigation(self):
        self.client(r"""
for(const stage of stages.slice(3)){const x=factory(stage);change(test(x.review,x.m[3]),'Correct the recorded failure');await click(test(x.review,x.m[8]));assert.equal(x.calls.length,1,stage);assert.equal(x.calls[0].body.decision,'changes_requested');assert.equal(x.calls[0].body.note,'Correct the recorded failure');assert.equal(x.selected().review_status,'Changes Requested');assert.equal(x.nav.length,0);assert.equal(JSON.stringify(x.records),x.original);}
""")

    def test_ready_s08_through_s14_start_buttons_send_one_exact_source_request(self):
        self.client(r"""
for(const stage of stages.slice(7)){const x=factory(stage),host=new DOMNode();if(stage==='global_rtl_generation')x.flow.preview={context_id:'frozen-preview',revision_id:'revision-a',profile_revision_id:'profile-a',estimated_input_tokens:20,messages:[{role:'user',content:'Frozen original job'}],source_manifest:{nodes:[]}};x.flow.render(host);const runId=stage==='global_rtl_generation'?'global-generate':x.m[1].replaceAll('_','-')+'-run';assert.equal(x.flow.gate(),'',stage+' must be ready in this isolated fixture');await click(test(host,runId));assert.equal(x.calls.length,1,stage);assert.ok(/\/start$|\/runs$/.test(x.calls[0].route));assert.equal(x.calls[0].body.revision_id,'revision-a');if(stage==='global_rtl_generation')assert.equal(x.calls[0].body.context_id,'frozen-preview');if(['global_synthesis','global_netlist_simulation','layout'].includes(stage))assert.equal(x.calls[0].body.global_job_id,'global-rtl');if(stage==='global_netlist_simulation')assert.equal(x.calls[0].body.synthesis_run_id,'global-s09');if(stage==='layout')assert.equal(x.calls[0].body.netlist_run_id,'global-s10');if(['drc','lvs','post_layout_verification'].includes(stage))assert.equal(x.calls[0].body.layout_run_id,'layout');if(['lvs','post_layout_verification'].includes(stage))assert.equal(x.calls[0].body.drc_run_id,'drc');if(stage==='post_layout_verification')assert.equal(x.calls[0].body.lvs_run_id,'lvs');assert.equal(JSON.stringify(x.records),x.original);}
""")

    def test_s07_refresh_reads_saved_specification_then_project_without_extraction(self):
        self.client(r"""
const x=factory('node_implementation_specs'),host=new DOMNode(),result=new DOMNode();result.setAttribute('data-testid','implementation-result');host.append(result);x.flow.host=host;x.flow.renderResult();await click(test(host,'implementation-refresh'));assert.deepEqual(x.calls.map(call=>call.route),['implementation-specs/spec','project']);assert.ok(x.calls.every(call=>call.body===undefined));assert.equal(JSON.stringify(x.records),x.original);
""")

    def test_s08_already_accepted_button_and_delayed_duplicate_handler_send_no_second_review(self):
        self.client(r"""
const x=factory('global_rtl_generation'),originalButton=test(x.review,'global-accept');await click(originalButton);assert.equal(x.calls.length,1);x.refresh();const accepted=test(x.review,'global-accept');assert.equal(accepted.disabled,true);assert.equal(accepted.textContent,'Global RTL accepted');await click(originalButton);assert.equal(x.calls.length,1,'A delayed handler bound to the original job cannot post duplicate acceptance');assert.equal(JSON.stringify(x.records),x.original);
""")

    def test_s08_feedback_repair_button_prepares_a_fresh_context_without_sending_generation(self):
        self.client(r"""
const x=factory('global_rtl_generation'),host=new DOMNode();x.flow.render(host);x.flow.renderReview(x.review);change(test(x.review,'global-review-note'),'Correct the saved top-level wiring');x.flow.preview={context_id:'earlier-preview'};await click(test(x.review,'global-prepare-repair'));assert.equal(x.flow.operation,'repair');assert.equal(x.flow.baseId,x.run.id);assert.equal(x.flow.instruction,'Correct the saved top-level wiring');assert.equal(x.flow.preview,null);assert.equal(x.calls.length,0);assert.equal(test(host,'global-generate').disabled,true);
x.flow.callbacks.request=async(route,body)=>{x.calls.push({route,body});assert.equal(route,'global-generation/context');assert.equal(JSON.stringify(body),JSON.stringify({revision_id:'revision-a',operation:'repair',instruction:'Correct the saved top-level wiring',base_job_id:x.run.id}));return {context_id:'new-repair-preview',profile_revision_id:'profile-a',revision_id:'revision-a',estimated_input_tokens:20,messages:[{role:'user',content:'Exact original-source repair context'}],source_manifest:{nodes:[]}};};await click(test(host,'global-context-preview'));assert.equal(x.calls.length,1);assert.equal(x.flow.preview.context_id,'new-repair-preview');assert.equal(test(host,'global-generate').disabled,false);assert.equal(JSON.stringify(x.records),x.original);assert.equal(x.nav.length,0);
""")

    def test_s08_uncertain_start_blocks_resend_until_readonly_refresh_succeeds(self):
        self.client(r"""
const x=factory('global_rtl_generation'),host=new DOMNode();
x.flow.preview={context_id:'frozen-preview',revision_id:'revision-a',profile_revision_id:'profile-a',estimated_input_tokens:20,messages:[{role:'user',content:'Frozen original job'}],source_manifest:{nodes:[]}};
let startCalls=0,getCalls=0;
x.flow.callbacks.request=async(route,body)=>{
 x.calls.push({route,body});
 if(route==='global-generation/start'){startCalls++;throw new Error('SOFTWARE QA interrupted response');}
 if(route==='global-generation'){getCalls++;return {global_generation:structuredClone(project.envelope.global_generation)};}
 throw new Error('Unexpected route '+route);
};
x.flow.render(host);const originalStart=test(host,'global-generate');await click(originalStart);
assert.equal(startCalls,1);assert.equal(x.flow.uncertainStart,true);assert.match(x.flow.pollError,/interrupted response/);
assert.equal(test(host,'global-generate').disabled,true);assert.equal(test(host,'global-context-preview').disabled,true);
assert.equal(test(host,'global-reconnect').hidden,false);assert.match(test(host,'global-reconnect').textContent,/Refresh saved global jobs/);
originalStart.click();await flush();assert.equal(startCalls,1,'A delayed or repeated GUI handler cannot resend an uncertain S08 start');
await click(test(host,'global-refresh'));
assert.equal(getCalls,1);assert.equal(x.flow.uncertainStart,false);assert.equal(x.flow.pollError,null);
assert.equal(test(host,'global-reconnect').hidden,true);assert.equal(test(host,'global-generate').disabled,false);
assert.deepEqual(x.calls.map(call=>[call.route,call.body===undefined]),[['global-generation/start',false],['global-generation',true]]);
assert.equal(JSON.stringify(x.records),x.original);
""")

    def test_s08_normal_start_uses_one_mutating_request_and_neutral_empty_copy(self):
        self.client(r"""
const x=factory('global_rtl_generation'),host=new DOMNode();
x.flow.preview={context_id:'frozen-preview',revision_id:'revision-a',profile_revision_id:'profile-a',estimated_input_tokens:20,messages:[{role:'user',content:'Frozen original job'}],source_manifest:{nodes:[]}};
x.flow.render(host);const empty=new DOMNode();x.flow.data.jobs=[];x.flow.renderReview(empty);
assert.match(empty.textContent,/all required node specifications/);assert.doesNotMatch(empty.textContent,/all six/i);
x.flow.data.jobs=[x.run];await click(test(host,'global-generate'));
assert.equal(x.calls.length,1);assert.equal(x.calls[0].route,'global-generation/start');assert.equal(x.calls[0].body.context_id,'frozen-preview');
assert.equal(x.flow.uncertainStart,false);assert.equal(x.flow.pollError,null);
""")

    def test_s09_s10_poll_failure_blocks_duplicate_start_until_readonly_refresh(self):
        self.client(r"""
for(const stage of ['global_synthesis','global_netlist_simulation']){
 const x=factory(stage),host=new DOMNode();x.flow.render(host);
 const live=x.flow.data.runs.find(item=>item.id===x.run.id);live.execution_status='Running';live.review_status='Awaiting Review';live.finished_at=null;
 x.flow.callbacks.workflow=value=>{x.flow.data=value;x.flow.refresh();};
 let workflowGets=0,projectGets=0,startPosts=0;
 x.flow.callbacks.request=async(route,body)=>{
  x.calls.push({route,body});
  if(route==='global-workflow'){
   workflowGets++;const value=structuredClone(x.flow.data),updated=value.runs.find(item=>item.id===x.run.id);
   Object.assign(updated,{execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',finished_at:'saved'});
   return {global_workflow:value};
  }
  if(route==='project'){projectGets++;throw new Error('SOFTWARE QA project refresh interrupted');}
  if(route==='global-workflow/runs'){startPosts++;return structuredClone(project.envelope);}
  throw new Error('Unexpected route '+route);
 };
 const originalStart=test(host,'global-workflow-run');await x.flow.poll();
 assert.equal(workflowGets,1);assert.equal(projectGets,1);assert.match(x.flow.pollError,/project refresh interrupted/);
 assert.equal(test(host,'global-workflow-run').disabled,true,stage+' start remains blocked after partial terminal observation');
 originalStart.click();await flush();assert.equal(startPosts,0,'A delayed handler cannot append a duplicate after poll failure');
 x.flow.callbacks.request=async(route,body)=>{x.calls.push({route,body});assert.equal(route,'project');assert.equal(body,undefined);const saved=structuredClone(project.envelope),updated=saved.global_workflow.runs.find(item=>item.id===x.run.id);Object.assign(updated,{execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',finished_at:'saved'});return saved;};
 await click(test(host,'global-workflow-refresh'));
 assert.equal(x.flow.pollError,null);assert.equal(x.flow.uncertainStart,false);assert.equal(test(host,'global-workflow-run').disabled,false);
}
""")

    def test_s11_s13_poll_failure_blocks_duplicate_start_and_revalidation_until_readonly_refresh(self):
        self.client(r"""
for(const stage of ['layout','drc','lvs']){
 const x=factory(stage),host=new DOMNode(),key=x.m[1],route=key.replaceAll('_','-');x.flow.render(host);
 const live=x.flow.data.runs.find(item=>item.id===x.run.id);
 Object.assign(live,{execution_status:'Running',validation_status:'Not Checked',review_status:'Awaiting Review',finished_at:null,
  evidence_kind:stage==='layout'?'trusted_fixed_tool_execution':live.evidence_kind,
  checks:{...live.checks,executed:true,exit_code:0,cleanup_unresolved:false}});
 x.flow.refresh();const originalStart=test(host,route+'-run');
 x.flow.callbacks.workflow=value=>{x.flow.data=value;x.flow.refresh();};
 let stageGets=0,projectGets=0,mutationPosts=0;
 x.flow.callbacks.request=async(requestRoute,body)=>{
  x.calls.push({route:requestRoute,body});
  if(requestRoute===route){
   stageGets++;const value=structuredClone(x.flow.data),updated=value.runs.find(item=>item.id===x.run.id);
   Object.assign(updated,{execution_status:'Failed',validation_status:'Failed',review_status:'Awaiting Review',freshness:'Current',finished_at:'saved'});
   return {[key]:value};
  }
  if(requestRoute==='project'){projectGets++;throw new Error('SOFTWARE QA project refresh interrupted');}
  if(body!==undefined){mutationPosts++;return structuredClone(project.envelope);}
  throw new Error('Unexpected route '+requestRoute);
 };
 await x.flow.poll();
 assert.equal(stageGets,1);assert.equal(projectGets,1);assert.match(x.flow.pollError,/project refresh interrupted/);
 assert.equal(test(host,route+'-run').disabled,true,stage+' run remains blocked after partial terminal observation');
 originalStart.click();await flush();assert.equal(mutationPosts,0,stage+' delayed Run handler cannot append a duplicate');
 if(stage==='layout'){
  const recheck=test(host,'physical-workflow-revalidate');assert.equal(recheck.disabled,true);
  recheck.click();await flush();assert.equal(mutationPosts,0,'S11 saved-output recheck is also blocked by uncertain polling');
 }
 await click(test(host,route+'-reconnect'));
 assert.equal(projectGets,2);assert.match(x.flow.pollError,/project refresh interrupted/);
 assert.equal(test(host,route+'-run').disabled,true,stage+' failed reconnect cannot clear the gate');
 originalStart.click();await flush();assert.equal(mutationPosts,0);
 x.flow.callbacks.request=async(requestRoute,body)=>{
  x.calls.push({route:requestRoute,body});assert.equal(requestRoute,'project');assert.equal(body,undefined);projectGets++;
  const saved=structuredClone(project.envelope),updated=saved[key].runs.find(item=>item.id===x.run.id);
  Object.assign(updated,{execution_status:'Failed',validation_status:'Failed',review_status:'Awaiting Review',freshness:'Current',finished_at:'saved'});
  return saved;
 };
 await click(test(host,route+'-reconnect'));
 assert.equal(projectGets,3);assert.equal(x.flow.pollError,null);assert.equal(x.flow.uncertainStart,false);
 assert.equal(test(host,route+'-run').disabled,false,stage+' successful saved-project GET is the only gate release');
 assert.equal(mutationPosts,0);
}
""")

    def test_s13_continue_requires_latest_clean_reviewable_current_run(self):
        self.client(r"""
{
 const x=factory('lvs');x.run.review_status='Accepted';x.refresh();
 assert.equal(test(x.review,'lvs-workflow-continue').disabled,false);
 await click(test(x.review,'lvs-workflow-continue'));
 assert.deepEqual(x.nav,[['post_layout_verification']]);assert.equal(x.calls.length,0,'Continue only navigates');
}
for(const kind of ['nonlatest','dirty','conflict','busy','other-active']){
 const x=factory('lvs');x.run.review_status='Accepted';
 if(kind==='nonlatest'){
  const newer={...structuredClone(x.run),id:'lvs-newer'};x.flow.data.runs.push(newer);x.flow.data.latest_run_id=newer.id;x.flow.runId=x.run.id;
 }
 if(kind==='dirty')project.dirty=true;
 if(kind==='conflict')project.conflict={message:'newer saved design'};
 if(kind==='busy')project.busy=true;
 if(kind==='other-active')project.envelope.postlayout_workflow.runs[0].execution_status='Running';
 x.refresh();assert.equal(test(x.review,'lvs-workflow-continue').disabled,true,'S13 Continue '+kind);
 assert.equal(x.calls.length,0);assert.equal(x.nav.length,0);
}
""")

    def test_s11_manifest_driven_rtl_artifact_controls_support_eleven_and_legacy_nodes(self):
        self.client(r"""
const families=[
 ['node-control','node-buffer','node-scheduler','node-pe','node-post','node-fifo'],
 ['npu2-control','npu2-buffer','npu2-scheduler','npu2-dispatcher','npu2-pe00','npu2-pe01','npu2-pe10','npu2-pe11','npu2-collector','npu2-post','npu2-fifo'],
];
for(const ids of families){
 const x=factory('layout'),host=new DOMNode(),result=new DOMNode(),downloads=[];result.setAttribute('data-testid','physical-workflow-result');host.append(result);x.flow.host=host;
 x.run.source_manifest={nodes:ids.map(node_id=>({node_id}))};
 x.run.artifacts=ids.map(node_id=>{const id='rtl-'+node_id;return {id,url:x.flow.artifactURL(x.run,id),bytes:1,content_type:'text/plain; charset=utf-8'};});
 x.flow.downloadFile=async(run,item)=>downloads.push([run.id,item.id]);x.flow.renderResult();
 assert.deepEqual(x.flow.artifacts(x.run).map(item=>item.id),ids.map(id=>'rtl-'+id));
 for(const nodeId of ids)await click(test(host,'physical-workflow-download-rtl-'+nodeId));
 assert.deepEqual(downloads.map(item=>item[1]),ids.map(id=>'rtl-'+id));
}
{
 const x=factory('layout'),unsafe='rtl-../escape';x.run.source_manifest={nodes:[{node_id:'../escape'}]};
 x.run.artifacts=[{id:unsafe,url:x.flow.artifactURL(x.run,unsafe),bytes:1,content_type:'text/plain'}];
 assert.deepEqual(x.flow.artifacts(x.run),[],'unsafe manifest IDs never become artifact controls');
 x.run.source_manifest={nodes:[{node_id:'npu2-pe00'}]};
 x.run.artifacts=[{id:'rtl-npu2-pe00',url:'/api/artifacts/physical-workflow/another-run/rtl-npu2-pe00',bytes:1,content_type:'text/plain'}];
 assert.deepEqual(x.flow.artifacts(x.run),[],'artifact URL must remain bound to the selected saved run');
}
for(const ids of [['1node'],['node.ok'],['candidate_top'],['CaseNode','casenode']]){
 const x=factory('layout');x.run.source_manifest={nodes:ids.map(node_id=>({node_id}))};
 x.run.artifacts=ids.map(node_id=>{const id='rtl-'+node_id;return {id,url:x.flow.artifactURL(x.run,id),bytes:1,content_type:'text/plain'};});
 assert.deepEqual(x.flow.artifacts(x.run),[],JSON.stringify(ids)+' must follow the backend source filename rules');
}
{
 const x=factory('layout'),id='_safe_node';x.run.source_manifest={nodes:[{node_id:id}]};
 x.run.artifacts=[{id:'rtl-'+id,url:x.flow.artifactURL(x.run,'rtl-'+id),bytes:1,content_type:'text/plain'}];
 assert.deepEqual(x.flow.artifacts(x.run).map(item=>item.id),['rtl-'+id],'leading underscore is a valid backend source identifier');
}
""")

    def test_all_eleven_history_views_select_older_evidence_and_return_to_current_without_api(self):
        self.client(r"""
for(const stage of stages.slice(3)){const x=factory(stage),host=new DOMNode(),older={...structuredClone(x.run),id:x.run.id+'-historical',freshness:'Stale',review_status:'Accepted'};const values=x.m[0]==='GenerationWorkspace'?x.flow.generation.jobs:x.m[0]==='NodeImplementationSpecs'?x.flow.specs:x.m[0]==='LocalWorkflow'?x.flow.runs:x.flow.data[x.m[2]];values.unshift(older);const frozen=JSON.stringify(values);x.flow.render(host);const oldButton=host.querySelectorAll('button').find(button=>button.textContent.includes(older.id));await click(oldButton);assert.equal(x.selected().id,older.id,stage);x.refresh();const adoption=test(x.review,x.m[4]);assert.ok(!adoption||adoption.disabled===true,stage+' historical adoption blocked');
if(stage==='local_rtl_generation'){await click(test(host,'generation-latest-request'));}else{const currentButton=host.querySelectorAll('button').find(button=>button.querySelectorAll('code').some(code=>code.textContent===x.run.id));await click(currentButton);assert.equal(x.selected().id,x.run.id);x.flow.runId=null;x.flow.specId=null;x.flow.selectedId=null;x.flow.runPinned=false;x.flow.refresh();}
assert.equal(x.selected().id,x.run.id,stage+' latest view returns to current source');assert.equal(x.calls.length,0,stage+' '+JSON.stringify(x.calls));assert.equal(JSON.stringify(values),frozen);assert.equal(JSON.stringify(x.records),x.original);}
""")


if __name__ == '__main__':
    unittest.main()



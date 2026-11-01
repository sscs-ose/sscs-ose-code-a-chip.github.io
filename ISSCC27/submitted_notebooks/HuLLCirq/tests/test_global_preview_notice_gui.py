"""Scoped S08 preview-notice recovery; isolated DOM doubles, no API/model/EDA."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const element=(tag,attrs={},...children)=>({tag,...attrs,children,replaceChildren(...items){this.children=items;}});
function fixture(){
 const message=element('div',{hidden:true}),state={},requests=[],toasts=[];
 const p={design:{project:{id:'software-project'}},envelope:{revision:{id:'revision-a'},workspace_identity:{project_id:'software-project',system_id:'system-a',session_id:'session-a'}},dirty:false,conflict:false,stage:'global_rtl_generation'};
 const context={state,el:element,field(){},badge(){},byId:id=>{assert.equal(id,'message');return message;},console,JSON,setTimeout(){throw Error('No polling in preview software QA');},clearTimeout(){}};
 vm.createContext(context);
 const app=fs.readFileSync('src/gui/app.js','utf8'),notifySource=app.slice(app.indexOf('function notify('),app.indexOf('function toast('));
 vm.runInContext(notifySource+'\nglobalThis.noticeAPI={notify,resolveNotice};',context);
 const source=fs.readFileSync('src/gui/global_generation.js','utf8').replace(/^import[^\n]*\n/gm,'').replace('export class GlobalGeneration','class GlobalGeneration');
 vm.runInContext(source+'\nglobalThis.GlobalGeneration=GlobalGeneration;',context);
 let reply=async()=>({context_id:'preview-ok',estimated_input_tokens:28486,profile_revision_id:'software-profile'});
 const flow=new context.GlobalGeneration({project:()=>p,request:async(route,body)=>{requests.push({route,body});return reply(route,body);},notify:context.noticeAPI.notify,resolveNotice:context.noticeAPI.resolveNotice,toast:text=>toasts.push(text),envelope(){}});
 flow.data={ready:true,jobs:[],reviews:[]};flow.refresh=()=>{};flow.schedule=()=>{};
 const error=(code='global_context_budget',text='The complete compact integration prompt plus output budget exceeds the profile context; nothing was truncated.')=>Object.assign(new Error(text),{code});
 return {flow,p,message,state,requests,toasts,error,api:context.noticeAPI,setReply:value=>reply=value};
}
"""


class GlobalPreviewNoticeTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated preview notice checks.')
        result = subprocess.run([node, '-e', CLIENT + '\n(async()=>{\n' + body +
                                 '\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});'],
                                cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shortened_successful_preview_resolves_only_its_previous_budget_error(self):
        self.run_client(r"""
const f=fixture();f.flow.operation='repair';f.flow.baseId='saved-candidate';f.flow.instruction='Original long correction';
f.setReply(async()=>{throw f.error();});await f.flow.prepare();assert.equal(f.message.hidden,false);assert.equal(f.flow.preview,null);
const old=f.state.messageNotice;assert.equal(f.flow.previewBudgetNotice.notice,old);
f.flow.instruction='Shortened correction';f.setReply(async()=>({context_id:'fitting-preview',estimated_input_tokens:28486,profile_revision_id:'software-profile'}));
await f.flow.prepare();assert.equal(f.message.hidden,true);assert.equal(f.state.messageNotice,null);assert.equal(f.flow.previewBudgetNotice,null);
assert.equal(f.flow.preview.context_id,'fitting-preview');assert.ok(f.flow.preview.estimated_input_tokens+4000<32768);
assert.deepEqual(f.requests.map(x=>x.route),['global-generation/context','global-generation/context']);
assert.equal(f.requests[1].body.instruction,'Shortened correction');assert.equal(f.requests.some(x=>x.route.includes('start')),false);
""")

    def test_new_unrelated_error_is_not_dismissed_by_preview_success(self):
        self.run_client(r"""
const f=fixture();f.setReply(async()=>{throw f.error();});await f.flow.prepare();
const newer=f.api.notify('Another operation failed to read its source.','error');
f.setReply(async()=>({context_id:'ok'}));await f.flow.prepare();
assert.equal(f.message.hidden,false);assert.equal(f.state.messageNotice,newer);assert.equal(f.flow.preview.context_id,'ok');
""")

    def test_other_project_revision_operation_candidate_and_session_scopes_are_preserved(self):
        self.run_client(r"""
for(const change of [f=>f.p.design.project.id='other-project',f=>f.p.envelope.revision.id='other-revision',
 f=>f.flow.operation='repair',f=>{f.flow.operation='repair';f.flow.baseId='other-candidate';},
 f=>f.p.envelope.workspace_identity.system_id='other-system',f=>f.p.envelope.workspace_identity.session_id='other-session']){
 const f=fixture();f.setReply(async()=>{throw f.error();});await f.flow.prepare();const old=f.state.messageNotice;change(f);
 f.setReply(async()=>({context_id:'other-scope-preview'}));await f.flow.prepare();assert.equal(f.message.hidden,false);assert.equal(f.state.messageNotice,old);
}
const repair=fixture();repair.flow.operation='repair';repair.flow.baseId='first-candidate';
repair.setReply(async()=>{throw repair.error();});await repair.flow.prepare();const repairNotice=repair.state.messageNotice;
repair.flow.baseId='second-candidate';repair.setReply(async()=>({context_id:'different-candidate-preview'}));await repair.flow.prepare();
assert.equal(repair.message.hidden,false);assert.equal(repair.state.messageNotice,repairNotice);
""")

    def test_consecutive_budget_failures_replace_the_owned_notice_and_require_success(self):
        self.run_client(r"""
const f=fixture();f.setReply(async()=>{throw f.error();});await f.flow.prepare();const first=f.state.messageNotice;
await f.flow.prepare();const second=f.state.messageNotice;assert.notEqual(first,second);assert.equal(f.message.hidden,false);assert.equal(f.flow.previewBudgetNotice.notice,second);
assert.equal(f.api.resolveNotice(first),false);assert.equal(f.message.hidden,false);
f.setReply(async()=>({context_id:'ok'}));await f.flow.prepare();assert.equal(f.message.hidden,true);
""")

    def test_nonbudget_preview_errors_are_not_cleared_by_a_later_success(self):
        self.run_client(r"""
for(const code of ['source_conflict','global_context_unknown',undefined]){
 const f=fixture();f.setReply(async()=>{const e=f.error();e.code=code;throw e;});await f.flow.prepare();const notice=f.state.messageNotice;
 assert.equal(f.flow.previewBudgetNotice,null);f.setReply(async()=>({context_id:'ok'}));await f.flow.prepare();
 assert.equal(f.message.hidden,false);assert.equal(f.state.messageNotice,notice);
}
""")

    def test_start_errors_remain_after_refresh_and_later_preview(self):
        self.run_client(r"""
const f=fixture();f.setReply(async()=>{throw f.error();});await f.flow.prepare();
f.setReply(async()=>({context_id:'ok',profile_revision_id:'profile-a'}));await f.flow.prepare();assert.equal(f.message.hidden,true);
f.setReply(async()=>{throw f.error('transport_failure','Start response interrupted.');});await f.flow.start();
assert.equal(f.flow.uncertainStart,true);assert.equal(f.message.hidden,false);const startNotice=f.state.messageNotice;
const calls=f.requests.length;await f.flow.prepare();assert.equal(f.requests.length,calls,'Uncertain start must still block preview');
// Model the existing explicit read-only reconnect having cleared the gate.
f.flow.uncertainStart=false;f.flow.pollError=null;f.setReply(async()=>({context_id:'new-preview'}));await f.flow.prepare();
assert.equal(f.message.hidden,false);assert.equal(f.state.messageNotice,startNotice);
""")

    def test_notice_tokens_use_identity_not_matching_text_and_do_not_clear_information(self):
        self.run_client(r"""
const f=fixture(),first=f.api.notify('Same text','error'),second=f.api.notify('Same text','error');
assert.equal(f.api.resolveNotice(first),false);assert.equal(f.message.hidden,false);
assert.equal(f.api.resolveNotice({...second}),false);assert.equal(f.message.hidden,false);
assert.equal(f.api.resolveNotice(second),true);assert.equal(f.message.hidden,true);
const info=f.api.notify('Still useful information','info');assert.equal(f.api.resolveNotice(info),false);assert.equal(f.message.hidden,false);
""")


if __name__ == '__main__':
    unittest.main()

"""Bounded-observation recovery fixtures, without browser/network/EDA/state writes."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class DOMDouble{constructor(tag,attrs={}){this.tag=tag;this.children=[];this.isConnected=true;Object.assign(this,attrs);}append(...values){this.children.push(...values.flat(Infinity).filter(v=>v!=null&&v!==false));}replaceChildren(...values){this.children=[];this.append(...values);}}
const el=(tag,attrs={},...values)=>{const n=new DOMDouble(tag,attrs);n.append(...values);return n;};
const all=n=>[n,...n.children.filter(v=>v instanceof DOMDouble).flatMap(all)];
const source=fs.readFileSync('src/gui/drc_workflow.js','utf8').replace(/^import[^\n]*\n/gm,'').replace('export class DRCWorkflow','class DRCWorkflow');
const timers=[];const sandbox={el,badge:text=>el('span',{text}),field:()=>el('div'),console,setTimeout:callback=>{timers.push(callback);return timers.length;}};
vm.createContext(sandbox);vm.runInContext(source+'\nglobalThis.DRCWorkflow=DRCWorkflow;',sandbox);
const running={id:'software-drc',execution_status:'Running',validation_status:'Not Checked',review_status:'Awaiting Review',freshness:'Current',checks:{},diagnostics:[]};
function fixture(){const calls=[],notices=[],button=el('button'),result=el('div');const project={stage:'drc',envelope:{review_policy:{mode:'manual'}}};let handler;
 const flow=new sandbox.DRCWorkflow({project:()=>project,request:(route,body)=>{assert.equal(body,undefined,'Recovery must not POST');calls.push(route);return handler(route);},workflow:data=>{flow.data=data;},envelope:response=>{flow.data=response.drc_workflow;},notify:(...args)=>notices.push(args)});
 flow.data={runs:[structuredClone(running)],reviews:[],latest_run_id:running.id};flow.host={isConnected:true,querySelector:selector=>selector==='[data-testid="drc-workflow-refresh"]'?button:selector==='[data-testid="drc-workflow-result"]'?result:null};
 flow.refresh=()=>{button.disabled=flow.busy||flow.polling;};
 return{flow,calls,notices,button,result,setHandler:value=>{handler=value;}};
}
"""


class DrcReadRecoveryClientTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated read-recovery tests.')
        completed = subprocess.run([node, '-e', CLIENT + '\n(async()=>{\n' + body +
                                   '\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});'],
                                  cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_timeout_unlocks_refresh_preserves_saved_status_and_does_not_automatically_poll(self):
        self.client(r"""
const f=fixture(),before=JSON.stringify(f.flow.data),count=timers.length;
f.setHandler(async()=>{throw Object.assign(Error('Saved read timed out, not a circuit verification failure.'),{code:'read_timeout',read_only:true});});
await f.flow.poll();assert.equal(f.flow.polling,false);assert.equal(f.button.disabled,false);assert.equal(JSON.stringify(f.flow.data),before);
assert.match(f.flow.pollError,/timed out/);assert.equal(timers.length,count);assert.deepEqual(f.calls,['drc-workflow']);
const reconnect=f.flow.reconnect();assert.equal(all(reconnect).find(n=>n['data-testid']==='drc-workflow-reconnect').disabled,false);
f.flow.renderResult();assert.ok(all(f.result).find(n=>n['data-testid']==='drc-workflow-observation-unavailable'));
assert.equal(all(f.result).find(n=>n['data-testid']==='drc-workflow-cancel').disabled,false);
assert.equal(all(f.result).some(n=>n.class==='generation-spinner'),false);
""")

    def test_initial_poll_and_manual_refresh_render_exceptions_cannot_latch_polling(self):
        self.client(r"""
for(const method of ['poll','refreshSaved']){const f=fixture(),count=timers.length;f.flow.refresh=()=>{throw Error('SOFTWARE QA rendering failed');};
f.setHandler(()=>assert.fail('No request after the initial render failed'));await f.flow[method]();
assert.equal(f.flow.polling,false);assert.equal(f.button.disabled,false);assert.equal(f.calls.length,0);assert.equal(timers.length,count);
assert.match(f.flow.pollError,/rendering failed/);assert.ok(all(f.result).find(n=>n['data-testid']==='drc-workflow-reconnect'));}
""")

    def test_explicit_reconnect_reads_completed_result_once_without_resending_execution(self):
        self.client(r"""
const f=fixture();f.setHandler(async()=>{throw Error('SOFTWARE QA offline');});await f.flow.poll();
const completed={...structuredClone(running),execution_status:'Completed',validation_status:'Passed'};
f.setHandler(async route=>{assert.equal(route,'project');return {drc_workflow:{runs:[completed],reviews:[],latest_run_id:completed.id}};});
await f.flow.refreshSaved();assert.equal(f.flow.polling,false);assert.equal(f.flow.pollError,null);assert.equal(f.flow.uncertainStart,false);
assert.equal(f.flow.selected().execution_status,'Completed');assert.equal(f.flow.selected().validation_status,'Passed');assert.deepEqual(f.calls,['drc-workflow','project']);
""")

    def test_aggregate_read_timeout_does_not_regress_terminal_drc_evidence(self):
        self.client(r"""
const f=fixture(),completed={...structuredClone(running),execution_status:'Completed',validation_status:'Passed'};
f.setHandler(async route=>{if(route==='drc-workflow')return{drc_workflow:{runs:[completed],reviews:[],latest_run_id:completed.id}};throw Object.assign(Error('Aggregate progress read timeout'),{code:'read_timeout'});});
await f.flow.poll();assert.equal(f.flow.polling,false);assert.equal(f.button.disabled,false);assert.equal(f.flow.selected().validation_status,'Passed');
assert.equal(f.flow.selected().execution_status,'Completed');assert.deepEqual(f.calls,['drc-workflow','project']);assert.match(f.flow.pollError,/Aggregate progress/);
""")


if __name__ == '__main__':
    unittest.main()

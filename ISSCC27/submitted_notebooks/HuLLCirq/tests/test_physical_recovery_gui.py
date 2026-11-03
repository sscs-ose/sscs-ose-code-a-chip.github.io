"""Isolated shared recovery card tests, not live circuit evidence."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLIENT = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
class E {
 constructor(tag,attrs={}){this.tag=tag;Object.assign(this,attrs);this.children=[];}
 append(...xs){for(const x of xs.flat(Infinity))if(x!=null&&x!==false){this.children.push(x);if(typeof x==='object')x.parent=this;}}
 replaceChildren(...xs){this.children=[];this.append(...xs);}
 querySelector(q){const id=q.match(/data-testid="([^"]+)"/)[1];return all(this).find(x=>x['data-testid']===id)||null;}
 remove(){if(this.parent)this.parent.children=this.parent.children.filter(x=>x!==this);}
}
const all=e=>e.children.flatMap(x=>typeof x==='object'?[x,...all(x)]:[]);
const el=(t,a,...xs)=>{const e=new E(t,a);e.append(...xs);return e;};
const field=(label,value,onChange,attrs)=>el('field',{label,value,onChange,...attrs});
const sandbox={el,field,console};vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('src/gui/physical_recovery.js','utf8').replace(/^import[^\n]*\n/gm,'').replace('export class PhysicalRecovery','class PhysicalRecovery')+'\nglobalThis.R=PhysicalRecovery',sandbox);
let p={readOnly:false,dirty:false,conflict:null,busy:false,stage:'lvs',design:{nodes:[{id:'arbitrary',name:'Arbitrary'}]},envelope:{workspace_identity:{project_id:'project',system_id:'system',session_id:'session'},revision:{id:'rev'}}};
let run={id:'run',record_hash:'hash',freshness:'Current',execution_status:'Completed'},requests=[],opened=[];
let reply={id:'handoff',target:'node_rtl',target_stage:'local_rtl_generation',node_id:'arbitrary',instruction:'frozen diagnostic instruction',certainty:'hypothesis'};
let responder=async()=>reply;
const r=new sandbox.R({project:()=>p,selected:()=>run,request:async(route,body)=>{requests.push({route,body});return responder(route,body);},open:async result=>opened.push(result)}),host=new E('main');
r.render(host,'lvs',run);const find=id=>host.querySelector(`[data-testid="${id}"]`);
'''


class PhysicalRecoveryGuiTests(unittest.TestCase):
    def client(self, script):
        node = shutil.which('node')
        if not node: self.skipTest('Node needed for isolated GUI tests')
        result = subprocess.run([node, '-e', CLIENT + '\n(async()=>{\n' + script +
            '\n})().catch(e=>{console.error(e);process.exitCode=1;});'], cwd=ROOT,
            capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_view_edits_and_navigation_send_nothing_prepare_then_open_are_separate(self):
        self.client(r'''
assert.equal(requests.length,0);find('physical-recovery-target').onChange('node_rtl');
find('physical-recovery-node').onChange('arbitrary');find('physical-recovery-feedback').onChange('Inspect actual mismatch');
assert.equal(requests.length,0);await find('physical-recovery-prepare').onclick();
assert.equal(requests.length,1);assert.equal(requests[0].route,'physical-recovery/prepare');
assert.equal(requests[0].body.node_id,'arbitrary');assert.equal(opened.length,0);
await find('physical-recovery-open').onclick();assert.equal(requests[1].route,'physical-recovery/open');assert.equal(opened.length,1);
assert.ok(requests.every(x=>!/(generation|runs|review)/.test(x.route)));
''')

    def test_stale_project_reply_cannot_open_or_fill_another_project(self):
        self.client(r'''
let done;responder=()=>new Promise(resolve=>done=resolve);
const pending=find('physical-recovery-prepare').onclick();p.envelope.workspace_identity.project_id='other';done(reply);await pending;
assert.equal(opened.length,0);assert.equal(find('physical-recovery-open'),null);
''')

    def test_busy_double_click_sends_once_and_input_changes_clear_prepared_instruction(self):
        self.client(r'''
let done;responder=()=>new Promise(resolve=>done=resolve);
const pending=find('physical-recovery-prepare').onclick();await find('physical-recovery-prepare').onclick();
assert.equal(requests.length,1);done(reply);await pending;assert.ok(find('physical-recovery-open'));
find('physical-recovery-feedback').onChange('Different diagnosis');assert.equal(find('physical-recovery-open'),null);
''')

    def test_readonly_and_active_or_stale_sources_cannot_prepare(self):
        self.client(r'''
for(const change of [()=>p.readOnly=true,()=>{p.readOnly=false;run.execution_status='Running';},()=>{run.execution_status='Completed';run.freshness='Stale';}]){
 change();host.replaceChildren();r.render(host,'lvs',run);assert.equal(find('physical-recovery-prepare').disabled,true);await find('physical-recovery-prepare').onclick();
}assert.equal(requests.length,0);
''')

    def test_history_is_explicit_read_and_does_not_open_or_start_jobs(self):
        self.client(r'''
responder=async()=>({records:[]});await find('physical-recovery-history').onclick();
assert.equal(requests.length,1);assert.equal(requests[0].route,'physical-recovery/history');assert.equal(opened.length,0);
''')

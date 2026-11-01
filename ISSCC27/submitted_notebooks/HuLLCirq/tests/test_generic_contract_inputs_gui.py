"""Browser-only generic specification editors; no live API/model/EDA/data."""
from pathlib import Path
import shutil
import subprocess
import unittest

from test_visual_navigation import CLIENT as APP_CLIENT

PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
class DOMDouble {
 constructor(tag,attrs={}){this.tag=tag;this.children=[];Object.assign(this,attrs);}
 append(...children){this.children.push(...children.flat(Infinity).filter(v=>v!==null&&v!==undefined&&v!==false));}
 querySelector(selector){return descend(this).find(node=>selector==='textarea'?node.tag==='textarea':node['data-testid']===selector.match(/data-testid="([^"]+)"/)?.[1])||null;}
}
const descend=node=>node.children.flatMap(child=>child&&typeof child==='object'?[child,...descend(child)]:[]);
const el=(tag,attrs={},...children)=>{const node=new DOMDouble(tag,attrs);node.append(...children);return node;};
const field=(title,value,edit,attrs)=>el('div',{},el('textarea',{...attrs,value,oninput:edit}),el('small',{text:attrs.hint}));
const context=vm.createContext({el,field,console});
const source=fs.readFileSync('src/gui/verification_inputs.js','utf8').replace(/^import[^\n]*\n/gm,'').replace(/export /g,'');
vm.runInContext(source+'\nglobalThis.qa={parseExactJson,nodePhysicalPorts,cycleTemplate,parseCycleInput,parseIntegrationInput,evaluateStructuredDraft,structuredInput,SYSTEM_DRAFT_KEYS};',context);
const c=context.qa,plain=value=>JSON.parse(JSON.stringify(value));
const ports=[{name:'in_data',direction:'input',width:8,signed:false},{name:'out_data',direction:'output',width:8,signed:false}];
const contract=()=>({kind:'generic_cycle_vectors',version:1,cycles:[{reset:1,drive:{in_data:0},expect:{out_data:0}},{reset:0,drive:{in_data:4},expect:{out_data:7}}]});
const text=value=>JSON.stringify(value,null,2);
const settings={clock_name:'clock_i',reset_name:'reset_i'};
function editor(value=null){const drafts={},applies=[],changes=[],data={value},gate={reason:''};const host=c.structuredInput({key:'node',id:'qa-editor',title:'Independent vectors',value,drafts,parse:raw=>c.parseCycleInput(raw,ports),apply:value=>{applies.push(value);data.value=value;},changed:()=>changes.push(1),gate:()=>gate.reason,template:()=>c.cycleTemplate(ports),hint:'SOFTWARE QA ONLY'});return{host,drafts,applies,changes,data,gate,field:host.querySelector('textarea'),button:id=>host.querySelector(`[data-testid="qa-editor-${id}"]`)};}
"""


class GenericContractInputTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated browser-input fixtures.')
        result = subprocess.run([node, '-e', CLIENT + '\n' + body], cwd=PROJECT,
                                capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def app_client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated real-module display fixtures.')
        result = subprocess.run([node, '--experimental-vm-modules', '-e', APP_CLIENT +
                                 '\n(async()=>{const qa=await initialize();\n' + body +
                                 '\nassert.equal(requests.length,0);})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});'],
                                cwd=PROJECT, capture_output=True, text=True, encoding='utf-8', timeout=25)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_typing_and_rerender_preserve_raw_draft_without_design_mutation(self):
        self.client(r"""
const e=editor();assert.equal(e.applies.length,0);e.field.oninput(text(contract()));
assert.equal(e.applies.length,0);assert.equal(e.data.value,null);assert.equal(e.drafts.node.pending,true);assert.equal(e.button('apply').disabled,false);
const again=c.structuredInput({key:'node',id:'again',title:'Vectors',value:null,drafts:e.drafts,parse:raw=>c.parseCycleInput(raw,ports),apply:()=>{throw Error('No Apply while viewing');},changed(){}});
assert.equal(again.querySelector('textarea').value,e.drafts.node.text);assert.equal(e.applies.length,0);
""")

    def test_explicit_apply_only_updates_design_draft_not_network_or_tools(self):
        self.client(r"""
const e=editor();e.field.oninput(text(contract()));e.button('apply').onclick();assert.equal(e.applies.length,1);assert.deepEqual(plain(e.data.value),contract());assert.equal(Object.hasOwn(e.drafts,'node'),false);assert.equal(e.button('apply').disabled,true);
e.button('apply').onclick();assert.equal(e.applies.length,1);
""")

    def test_invalid_text_and_unfilled_example_cannot_apply_or_erase_old_contract(self):
        self.client(r"""
const original=contract(),e=editor(original);for(const bad of ['{broken','[]',text({...contract(),cycles:[]})]){e.field.oninput(bad);e.button('apply').onclick();assert.equal(e.applies.length,0);assert.equal(e.data.value,original);assert.equal(e.drafts.node.text,bad);assert.ok(e.drafts.node.error);}
e.button('template').onclick();assert.match(e.field.value,/null/);assert.equal(e.applies.length,0);assert.ok(e.drafts.node.error);assert.equal(e.button('apply').disabled,true);
""")

    def test_discard_only_clears_unapplied_text_and_empty_apply_explicitly_removes(self):
        self.client(r"""
const value=contract(),e=editor(value);e.field.oninput('{broken');e.button('discard').onclick();assert.equal(Object.hasOwn(e.drafts,'node'),false);assert.equal(e.field.value,text(value));assert.equal(e.applies.length,0);
e.field.oninput('');e.button('apply').onclick();assert.equal(e.applies.length,1);assert.equal(e.data.value,null);
""")

    def test_readonly_conflict_or_active_guard_prevents_apply_and_template_mutation(self):
        self.client(r"""
for(const reason of ['read-only','source conflict','active tool']){const e=editor();e.field.oninput(text(contract()));const before=e.drafts.node.text;e.gate.reason=reason;e.button('apply').onclick();e.button('discard').onclick();e.button('template').onclick();assert.equal(e.applies.length,0);assert.equal(e.drafts.node.text,before);}
""")

    def test_unsafe_json_numbers_are_rejected_but_exact_wide_strings_roundtrip(self):
        self.client(r"""
for(const raw of ['9007199254740992','9007199254740993','1e999','1.0000000000000001'])assert.throws(()=>c.parseExactJson('{"value":'+raw+'}'),/plain safe JSON integers/);
const p=[{name:'in_data',direction:'input',width:4096,signed:false},{name:'out_data',direction:'output',width:4096,signed:true}],wide=(1n<<4094n).toString(),value=contract();value.cycles[1].drive.in_data=wide;value.cycles[1].expect.out_data='-'+wide;
const parsed=c.parseCycleInput(text(value),p);assert.equal(parsed.cycles[1].drive.in_data,wide);assert.equal(parsed.cycles[1].expect.out_data,'-'+wide);assert.equal(text(parsed),text(value));
for(const bad of ['+1','01','-0',' 1','1.0']){value.cycles[1].drive.in_data=bad;assert.throws(()=>c.parseCycleInput(text(value),p),/exact integer/);}
""")

    def test_cycles_require_complete_pins_exact_width_reset_and_actual_input_changes(self):
        self.client(r"""
for(const change of [v=>{delete v.cycles[1].expect.out_data;},v=>{v.cycles[1].drive.extra=1;},v=>{v.cycles[0].reset=0;},v=>{v.cycles[1].reset=1;},v=>{v.cycles[1].drive.in_data=256;},v=>{v.cycles[1].expect.out_data=-1;},v=>{v.cycles[1].drive.in_data=0;},v=>{v.cycles[1].expect.out_data=null;}]){const v=contract();change(v);assert.throws(()=>c.parseCycleInput(text(v),ports));}
const v=contract();v.cycles[1].drive.in_data='0';assert.throws(()=>c.parseCycleInput(text(v),ports),/Change at least one/);
assert.deepEqual(plain(c.parseCycleInput(text(contract()),ports)),contract());
""")

    def test_stream_expansion_and_templates_include_every_ready_valid_signal(self):
        self.client(r"""
const p=c.nodePhysicalPorts({ports:[{name:'up',direction:'input',width:8,signed:false,protocol:'valid_ready'},{name:'down',direction:'output',width:8,signed:false,protocol:'valid_ready'},{name:'enable',direction:'input',width:1,signed:false,protocol:'raw'}]});
assert.deepEqual(plain(p.map(port=>[port.name,port.direction])),[['up','input'],['up_valid','input'],['up_ready','output'],['down','output'],['down_valid','output'],['down_ready','input'],['enable','input']]);
const v=c.cycleTemplate(p);assert.deepEqual(Object.keys(v.cycles[0].drive).sort(),['down_ready','enable','up','up_valid']);assert.deepEqual(Object.keys(v.cycles[0].expect).sort(),['down','down_valid','up_ready']);assert.throws(()=>c.parseCycleInput(text(v),p),/No null/);
""")

    def test_top_declaration_requires_physical_ports_behavior_and_automatic_clock_reset(self):
        self.client(r"""
const declaration={public_ports:ports,behavior:'Independent byte pipeline specification'};assert.deepEqual(plain(c.parseIntegrationInput(text(declaration),settings)),declaration);
for(const change of [v=>{v.behavior='';},v=>{v.public_ports.push({...ports[0]});},v=>{v.public_ports[0].name='clock_i';},v=>{v.public_ports[0].width=1.5;},v=>{v.public_ports[0].signed='false';},v=>{v.public_ports=[];}]){const v=structuredClone(declaration);change(v);assert.throws(()=>c.parseIntegrationInput(text(v),settings));}
""")

    def test_pending_global_drafts_block_save_and_survive_existing_browser_recovery_path(self):
        self.client(r"""
const app=fs.readFileSync('src/gui/app.js','utf8');const line=app.slice(app.indexOf('const invalidVerification ='),app.indexOf('const adapterDraftDirty ='));
const state={design:{nodes:[{id:'node',ports,verification:contract()}],settings},verificationDrafts:{}};const s=vm.createContext({state,...c});vm.runInContext(line+'\nglobalThis.invalid=invalidVerification;',s);
for(const key of ['node',...c.SYSTEM_DRAFT_KEYS]){state.verificationDrafts={[key]:{pending:true,text:'retained'}};assert.ok(s.invalid());state.verificationDrafts={[key]:{error:'bad',text:'retained'}};assert.ok(s.invalid());}
const changed=contract();changed.cycles[1].expect.out_data=9;state.verificationDrafts={node:{text:text(changed),pending:false,error:''}};assert.ok(s.invalid());state.design.nodes[0].verification=changed;assert.equal(s.invalid(),undefined);
state.verificationDrafts={removed_node:{pending:true}};assert.equal(s.invalid(),undefined);
assert.match(app,/verification_drafts: state.verificationDrafts/);assert.match(app,/state.verificationDrafts = draft.verification_drafts/);assert.match(app,/state\.busy \|\| !dirty\(\) \|\| invalidVerification\(\)/);
assert.match(app,/host.append\(systemVerificationFields\(\)\)/);assert.match(app,/parseCycleInput\(text, state.design.global_integration/);
assert.doesNotMatch(fs.readFileSync('src/gui/verification_inputs.js','utf8'),/\bfetch\s*\(|callbacks.request|sessionFetch|setTimeout\s*\(/);
""")

    def test_undo_redo_and_interface_changes_recompute_pending_and_errors_without_mutating_text(self):
        self.client(r"""
const original=contract(),e=editor(original);e.field.oninput(text(original));assert.equal(e.drafts.node.pending,false);
const alternate=contract();alternate.cycles[1].expect.out_data=9;
const render=value=>c.structuredInput({key:'node',id:'rerender',title:'Vectors',value,drafts:e.drafts,parse:raw=>c.parseCycleInput(raw,ports),apply(){},changed(){}});
let h=render(alternate);assert.equal(h.querySelector('[data-testid="rerender-apply"]').disabled,false);assert.equal(h.querySelector('textarea').value,text(original));
h=render(original);assert.equal(h.querySelector('[data-testid="rerender-apply"]').disabled,true);
const draft={text:text(original),pending:false,error:''},before=JSON.stringify(draft),newPorts=[...ports,{name:'new_output',direction:'output',width:1,signed:false}];
const result=c.evaluateStructuredDraft(draft,original,raw=>c.parseCycleInput(raw,newPorts));assert.ok(result.error);assert.equal(result.pending,true);assert.equal(JSON.stringify(draft),before);
""")

    def test_s08_generic_profile_and_direct_contract_settings_are_not_npu_or_execution(self):
        self.app_client(r"""
qa.state.stage='global_rtl_generation';qa.state.design.global_verification={kind:'generic_cycle_vectors'};
const flow=qa.globalGeneration;flow.data={ready:false,blocked_code:'generic_global_contract',blocked_reason:'Declare this design public ports.',jobs:[],reviews:[]};
const host=new DOMNode('main');flow.render(host);assert.match(host.textContent,/independently declared cycle vectors/);assert.doesNotMatch(host.textContent,/same original matrix job/);
const blocker=flow.blocker();assert.equal(blocker.kind,'input_required');assert.equal(blocker.setup_action.testId,'global-verification-settings');
host.querySelector('[data-testid="global-verification-settings"]').click();assert.deepEqual(visits,['specifications']);
flow.data.blocked_code='global_adoption_missing';assert.equal(flow.blocker(),null);
assert.equal(flow.generic({context:{verification_plan:{kind:'old_matrix_profile'}}}),false);assert.equal(flow.generic({context:{verification_plan:{kind:'generic_cycle_vectors'}}}),true);
""")

    def test_s10_signal_samples_are_labeled_from_frozen_plan_not_current_design(self):
        self.app_client(r"""
const flow=qa.globalFlow,checks={actual_output_transfers:[{cycle:0,signal:'result',value:0},{cycle:1,signal:'result',value:7}],actual_pe_lane_transfers:[],actual_public_stream_transfers:[],signal_sample_count:2,expected_signal_samples:2};
const summary=flow.checkSummary({verification_plan:{kind:'generic_cycle_vectors'},checks});assert.equal(summary.observed_signal_sample_count,2);assert.equal(summary.expected_signal_sample_count,2);assert.equal(Object.hasOwn(summary,'observed_output_count'),false);assert.equal(Object.hasOwn(summary,'observed_pe_count'),false);assert.match(summary.scope_note,/not stream transfers/);
qa.state.design.global_verification={kind:'generic_cycle_vectors'};const old=flow.checkSummary({verification_plan:{kind:'old_matrix_profile'},checks});assert.equal(old.observed_output_count,2);assert.equal(Object.hasOwn(old,'observed_signal_sample_count'),false);
""")


if __name__ == '__main__':
    unittest.main()

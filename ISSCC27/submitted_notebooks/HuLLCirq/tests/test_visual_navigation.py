"""Real GUI navigation rendering with isolated DOM; no live API, model, or EDA."""
from pathlib import Path
import shutil
import subprocess
import unittest


PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),fixtureCrypto=require('node:crypto');
// Positive app-display fixtures have the browser capabilities required by the
// common start controller. These helpers never fetch or create app records.
const fixtureExecutionVersion='execution-submission-v1';
const fixtureExecutionRoutes=['generation/batches/start','repair-analysis/start','workflow/start','workflow/batches/start','global-generation/start','global-workflow/runs','physical-workflow/runs','drc-workflow/runs','lvs-workflow/runs','postlayout-workflow/runs'];
const fixtureSorted=value=>Array.isArray(value)?value.map(fixtureSorted):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(key=>[key,fixtureSorted(value[key])])):value;
const fixtureHash=value=>fixtureCrypto.createHash('sha256').update(JSON.stringify(fixtureSorted(value))).digest('hex');
const fixtureExecutionConfigurations=Object.fromEntries(fixtureExecutionRoutes.map(route=>[route,fixtureHash({fixture:'isolated-display-configuration',route})]));
let fixtureUuid=0;
function fixtureMemoryStorage(){const values=new Map();return{
 get length(){return values.size;},key:index=>[...values.keys()][index]??null,
 getItem:key=>values.has(String(key))?values.get(String(key)):null,
 setItem(key,value){values.set(String(key),String(value));},removeItem(key){values.delete(String(key));},clear(){values.clear();}};}
// Explicit opt-in response builder for API-wrapper consumers of CLIENT. It
// decorates only their supplied synthetic positive record and exact wire body;
// it never manufactures a nonce, record ID, pass result, or rejection marker.
function fixtureExecutionReply(route,wireBody,response,{recordId=null,replayed=false}={}){
 assert.ok(fixtureExecutionRoutes.includes(route),'S04 single generation remains owned by its separate I16 fixture');
 assert.equal(typeof wireBody.submission_id,'string');assert.match(wireBody.submission_id,/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/);
 assert.equal(typeof wireBody.submission_configuration_fingerprint,'string');assert.equal(typeof replayed,'boolean');
 const result=structuredClone(response),groups={
  'generation/batches/start':result.generation_batches?.batches,'repair-analysis/start':result.repair_analysis?.jobs,
  'workflow/start':result.workflow_runs,'workflow/batches/start':result.workflow_batches,
  'global-generation/start':result.global_generation?.jobs,'global-workflow/runs':result.global_workflow?.runs,
  'physical-workflow/runs':result.physical_workflow?.runs,'drc-workflow/runs':result.drc_workflow?.runs,
  'lvs-workflow/runs':result.lvs_workflow?.runs,'postlayout-workflow/runs':result.postlayout_workflow?.runs};
 const rows=groups[route]||(route==='repair-analysis/start'&&result.id?[result]:[]);
 const matches=rows.filter(row=>recordId?row.id===recordId:!wireBody.stage_id||row.stage_id===wireBody.stage_id);
 assert.equal(matches.length,1,'Declare exactly one synthetic start record or its explicit recordId');
 const record=matches[0];assert.equal(typeof record.id,'string');assert.ok(record.id);
 if(Object.hasOwn(record,'submission_id'))assert.equal(record.submission_id,wireBody.submission_id);
 record.submission_id=wireBody.submission_id;
 if(Object.hasOwn(wireBody,'request_id')){if(Object.hasOwn(record,'request_id'))assert.equal(record.request_id,wireBody.request_id);record.request_id=wireBody.request_id;}
 const request=Object.fromEntries(Object.entries(structuredClone(wireBody)).filter(([key])=>key!=='submission_id'));
 result.execution_submission_protocol_version=fixtureExecutionVersion;
 result.execution_submission={version:fixtureExecutionVersion,route,submission_id:wireBody.submission_id,record_id:record.id,replayed};
 result.execution_submission_receipts={...(result.execution_submission_receipts||{}),[route]:{...(result.execution_submission_receipts?.[route]||{}),
  [wireBody.submission_id]:{route,request,binding_hash:fixtureHash({route,request}),record_id:record.id,rejection:null}}};
 return result;
}
class DOMNode {
 constructor(tag='div'){this.tag=tag;this.children=[];this.attributes={};this.dataset={};this.listeners={};this.style={};this.disabled=false;this.isConnected=true;this._text='';this.className='';
  this.classList={add:(...names)=>{this.className=[...new Set([...this.className.split(/\s+/),...names])].join(' ').trim();},remove:(...names)=>{this.className=this.className.split(/\s+/).filter(name=>!names.includes(name)).join(' ');},contains:name=>this.className.split(/\s+/).includes(name)};
 }
 set textContent(value){this._text=String(value);this.children=[];} get textContent(){return this._text+this.children.map(node=>node.textContent).join('');}
 setAttribute(key,value){this.attributes[key]=String(value);if(key==='class')this.className=String(value);if(key==='id')this.id=String(value);if(key.startsWith('data-'))this.dataset[key.slice(5).replace(/-([a-z])/g,(_,letter)=>letter.toUpperCase())]=String(value);}
 getAttribute(key){return key==='class'?this.className:this.attributes[key]??null;}
 hasAttribute(key){return this.getAttribute(key)!==null;}
 removeAttribute(key){delete this.attributes[key];}
 append(...nodes){for(const node of nodes.flat(Infinity)){if(node===null||node===undefined||node===false)continue;if(node instanceof DOMNode)this.children.push(node);else{const text=new DOMNode('#text');text.textContent=String(node);this.children.push(text);}}}
 replaceChildren(...nodes){this._text='';this.children=[];this.append(...nodes);}
 addEventListener(name,handler){(this.listeners[name]??=[]).push(handler);}
 click(){for(const handler of this.listeners.click||[])handler({currentTarget:this,preventDefault(){}});}
 focus(){} scrollIntoView(){}
 querySelectorAll(selector){return descendants(this).filter(node=>matches(node,selector));}
 querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
}
const descendants=node=>node.children.flatMap(child=>[child,...descendants(child)]);
function matches(node,selector){
 if(selector.startsWith('#'))return node.id===selector.slice(1);
 if(selector.startsWith('.'))return node.className.split(/\s+/).includes(selector.slice(1));
 const attr=selector.match(/^\[([^=\]]+)(?:="([^"]*)")?\]$/);if(attr)return attr[2]===undefined?node.hasAttribute(attr[1]):node.getAttribute(attr[1])===attr[2];
 return node.tag===selector;
}
const directory=path.resolve('src/gui'),html=fs.readFileSync(path.join(directory,'index.html'),'utf8');
const elements=new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(match=>{const node=new DOMNode();node.id=match[1];return[match[1],node];}));
const document={body:new DOMNode('body'),documentElement:new DOMNode('html'),activeElement:null,
 getElementById:id=>elements.get(id)||null,
 createElement:tag=>new DOMNode(tag),createElementNS:(_,tag)=>new DOMNode(tag),createTextNode:text=>{const node=new DOMNode('#text');node.textContent=text;return node;},
 querySelector:selector=>[...elements.values()].find(node=>matches(node,selector))||[...elements.values()].flatMap(descendants).find(node=>matches(node,selector))||null,
 querySelectorAll:selector=>[...elements.values()].flatMap(node=>[node,...descendants(node)]).filter(node=>matches(node,selector)),addEventListener(){}};
const requests=[],visits=[];
const context=vm.createContext({console,document,Node:DOMNode,structuredClone,URL,AbortSignal,Headers,Date,JSON,
 sessionStorage:fixtureMemoryStorage(),fixtureExecutionReply,
 crypto:{randomUUID:()=> 'isolated-display-qa-'+(++fixtureUuid)},location:{href:'http://localhost:9999/',origin:'http://localhost:9999'},
 setTimeout(){throw Error('Display QA must not schedule execution or polling');},clearTimeout(){},
 fetch(...args){requests.push(args);throw Error('Display QA must not call an API');}});
const modules=new Map();
function load(file){file=path.resolve(file);assert.ok(file.startsWith(directory+path.sep));if(modules.has(file))return modules.get(file);
 let source=fs.readFileSync(file,'utf8');if(path.basename(file)==='app.js'){
  assert.match(source,/\nstart\(\);\s*$/);
  source=source.replace(/\nstart\(\);\s*$/,'\nglobalThis.qa={state,STAGES,renderTabs,renderStageStatus,executionState,renderConnectionStatus,connectionMonitor,generation,localFlow,implementationSpecs,globalGeneration,globalFlow,physicalFlow,drcFlow,lvsFlow,postlayoutFlow,setStage,dirty,executionInputDirty,fixtureExecutionReply,setNavigate:callback=>{setStage=callback;}};');
 }
 const module=new vm.SourceTextModule(source,{context,identifier:file});modules.set(file,module);return module;
}
async function initialize(){const app=load(path.join(directory,'app.js'));await app.link((specifier,referrer)=>load(path.resolve(path.dirname(referrer.identifier),specifier)));await app.evaluate();
 const qa=context.qa,accepted={execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',implemented:true};
 qa.state.design={id:'display-only-design',project:{name:'Isolated display'},nodes:[{id:'node-a',name:'A',module_name:'a'},{id:'node-b',name:'B',module_name:'b'}],edges:[],hierarchy:[],layout:{nodes:{},viewport:{x:0,y:0,zoom:1}}};
 qa.state.saved=structuredClone(qa.state.design);
 qa.state.envelope={revision:{id:'display-only-revision'},execution_submission_protocol_version:fixtureExecutionVersion,execution_configuration_fingerprints:structuredClone(fixtureExecutionConfigurations),execution_submission_receipts:{},workflow:qa.STAGES.map(([id],index)=>({id,...(index<5?accepted:{execution_status:'Not Run',validation_status:'Not Checked',review_status:'Awaiting Review',freshness:'Current',implemented:true}),...(index>=3&&index<=6?{accepted_node_count:index<5?2:0,required_node_count:2}:{})})),
  generation:{jobs:[],nodes:[]},workflow_runs:[],workflow_nodes:[],implementation_specs:[],implementation_spec_nodes:[],
  global_generation:{jobs:[],ready:false,blocked_reason:'The integration checker does not support this design.'},global_workflow:{runs:[],stages:[],ready:false},
  physical_workflow:{runs:[],ready:false},drc_workflow:{runs:[],ready:false},lvs_workflow:{runs:[],ready:false},postlayout_workflow:{runs:[],ready:false,verification_supported:false}};
 qa.setNavigate(id=>visits.push(id));return qa;
}
"""


class VisualNavigationTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for isolated GUI rendering checks.")
        result = subprocess.run(
            [node, "--experimental-vm-modules", "-e", CLIENT +
             "\n(async()=>{const qa=await initialize();\n" + body +
             "\nassert.equal(requests.length,0);})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});"],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_all_stage_tabs_keep_their_real_navigation_targets_and_are_inspectable(self):
        self.run_client(r"""
qa.state.stage='local_synthesis';qa.renderTabs();
const nav=elements.get('stage-tabs'),tabs=nav.querySelectorAll('[data-stage-id]');
assert.equal(tabs.length,14);
assert.deepEqual(tabs.map(tab=>tab.getAttribute('data-stage-id')),Array.from(qa.STAGES,stage=>stage[0]));
assert.equal(tabs.filter(tab=>tab.getAttribute('aria-current')==='step').length,1);
assert.equal(tabs.find(tab=>tab.getAttribute('aria-current')==='step').getAttribute('data-stage-id'),'local_synthesis');
for(const tab of tabs){assert.equal(tab.tag,'button');assert.equal(tab.disabled,false);assert.equal(tab.getAttribute('data-testid'),'stage-'+tab.getAttribute('data-stage-id'));tab.click();}
assert.deepEqual(visits,Array.from(qa.STAGES,stage=>stage[0]));
""")

    def test_every_stage_has_identity_icon_and_status_symbol_separate_from_selection(self):
        self.run_client(r"""
qa.state.stage='local_synthesis';qa.renderTabs();
const nav=elements.get('stage-tabs'),tabs=nav.querySelectorAll('[data-stage-id]');
assert.equal(nav.querySelectorAll('.stage-group').length,4);
for(const tab of tabs){
 const id=tab.getAttribute('data-stage-id'),kind=tab.getAttribute('data-state');
 assert.ok(tab.querySelector(`[data-icon="${id}"]`));assert.ok(tab.querySelector(`[data-icon="${kind}"]`));
 assert.match(tab.getAttribute('title'),new RegExp(qa.STAGES.find(stage=>stage[0]===id)[1]));
 assert.ok(tab.querySelector('.stage-state-label').textContent.trim());
}
const selected=tabs.find(tab=>tab.getAttribute('aria-current')==='step');
assert.equal(selected.getAttribute('data-state'),'complete');assert.ok(selected.classList.contains('active'));
assert.equal(elements.get('stage-legend').children.length,5);
assert.match(elements.get('workflow-progress').textContent,/5 \/ 14 stages complete/);
assert.deepEqual(elements.get('stage-legend').children.map(node=>node.textContent),['Not run','Running','Complete','Review required','Failed']);
""")

    def test_partial_and_unsaved_inputs_do_not_inflate_whole_stage_progress(self):
        self.run_client(r"""
const local=qa.state.envelope.workflow.find(stage=>stage.id==='local_netlist_simulation');
Object.assign(local,{execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',accepted_node_count:1,required_node_count:2});
qa.renderTabs();const tab=elements.get('stage-tabs').querySelector('[data-stage-id="local_netlist_simulation"]');
assert.notEqual(tab.getAttribute('data-state'),'complete');
assert.match(elements.get('workflow-progress').textContent,/5 \/ 14 stages complete/);
qa.state.design.nodes[0].behavior='Unsaved functional behavior';
assert.equal(qa.executionInputDirty(),true,'functional behavior remains an execution input');
qa.renderTabs();
assert.equal(elements.get('stage-tabs').querySelectorAll('[data-state="complete"]').length,0);
assert.match(elements.get('workflow-progress').textContent,/0 \/ 14 stages complete/);
""")

    def test_canvas_view_change_and_stage_navigation_preserve_saved_completion(self):
        self.run_client(r"""
const accepted={execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',implemented:true};
qa.state.envelope.workflow=qa.STAGES.map(([id],index)=>index<13?{id,...accepted,...(index>=3&&index<=6?{accepted_node_count:2,required_node_count:2}:{})}:{id,implemented:true,execution_status:'Not Run',validation_status:'Not Checked',review_status:'Awaiting Review',freshness:'Current'});
qa.state.stage='lvs';qa.state.saved=structuredClone(qa.state.design);
qa.state.design.layout.viewport={x:-405.625,y:52.286,zoom:0.772478};
qa.state.design.layout.nodes={'node-a':{x:120,y:240},'node-b':{x:480,y:240}};
assert.equal(qa.dirty(),true,'canvas view remains saveable');
assert.equal(qa.executionInputDirty(),false,'canvas view is not a circuit-input edit');
const before=JSON.stringify(qa.state.envelope);
qa.setStage('global_synthesis');
const tabs=elements.get('stage-tabs').querySelectorAll('[data-stage-id]');
for(const id of ['layout','drc','lvs']){
 const tab=tabs.find(item=>item.getAttribute('data-stage-id')===id);
 assert.equal(tab.getAttribute('data-state'),'complete',id);
 assert.equal(tab.querySelector('.stage-state-label').textContent,'Complete',id);
}
assert.match(elements.get('workflow-progress').textContent,/13 \/ 14 stages complete/);
assert.match(elements.get('save-state').textContent,/Unsaved canvas view/);
assert.equal(JSON.stringify(qa.state.envelope),before);
assert.equal(requests.length,0);
""")

    def test_llm_header_footer_agree_and_click_only_opens_settings(self):
        self.run_client(r"""
const profile={id:'qa',name:'QA',api_type:'chat_completions',execution_location:'Network',base_url:'https://example.invalid/v1',model:'qa-model'};
qa.generation.llm={profile,profile_revision_id:'profile-a',probe:{status:'Connected',profile_revision_id:'profile-a',selected_model_available:true}};
qa.generation.profileDirty=()=>false;
qa.renderConnectionStatus();
const header=elements.get('llm-header-status'),footer=elements.get('llm-status-pill');
assert.ok(header.classList.contains('connection-complete'));assert.ok(footer.classList.contains('connection-complete'));
assert.equal(elements.get('llm-header-text').textContent,elements.get('llm-connection-state').textContent);
assert.match(header.getAttribute('aria-label'),/Connected/);header.onclick();assert.deepEqual(visits,['global_settings']);
qa.generation.profileDirty=()=>true;qa.renderConnectionStatus();
assert.ok(header.classList.contains('connection-attention'));assert.ok(footer.classList.contains('connection-attention'));
assert.match(elements.get('llm-header-text').textContent,/Unsaved settings/);
qa.generation.profileDirty=()=>false;qa.generation.llm.probe.profile_revision_id='old';qa.renderConnectionStatus();
assert.ok(header.classList.contains('connection-attention'));assert.match(elements.get('llm-header-text').textContent,/Not tested/);
""")

    def test_all_tabs_and_headers_change_before_a_saved_server_response(self):
        self.run_client(r"""
const before=JSON.stringify(qa.state.envelope);
for(const [index,[id]] of qa.STAGES.entries()) {
 qa.executionState.setScope('isolated-'+id);qa.state.stage=id;
 const token=qa.executionState.begin({stageId:id,kind:'execute'});
 qa.renderTabs();qa.renderStageStatus();
 const tabs=elements.get('stage-tabs').querySelectorAll('[data-stage-id]');
 assert.equal(tabs[index].getAttribute('data-state'),'working');
 assert.equal(tabs[index].querySelector('.stage-state-label').textContent,'Running');
 assert.equal(elements.get('stage-status').getAttribute('data-status'),'Running');
 for(const later of tabs.slice(index+1)) {
  assert.equal(later.getAttribute('data-state'),'pending');
  assert.equal(later.querySelector('.stage-state-label').textContent,'Not run');
 }
 qa.executionState.failure(token,{status:400,message:'Isolated execution rejected'});
 qa.renderTabs();qa.renderStageStatus();
 assert.equal(elements.get('stage-tabs').querySelector(`[data-stage-id="${id}"]`).getAttribute('data-state'),'error');
 assert.equal(elements.get('stage-status').getAttribute('data-status'),'Failed');
}
assert.equal(JSON.stringify(qa.state.envelope),before);
""")

    def test_runtime_error_without_old_runtime_is_visible_and_older_observation_cannot_erase_it(self):
        self.run_client(r"""
const profile={execution_location:'Local',base_url:'http://127.0.0.1:11435/v1',model:'qwen3:8b'};
qa.generation.llm={profile,profile_revision_id:'profile-a',probe:{status:'Connected',profile_revision_id:'profile-a',selected_model_available:true}};
qa.state.envelope.llm=qa.generation.llm;qa.state.envelope.workspace_identity={session_id:'display-session'};
qa.generation.profileDirty=()=>false;
// Polling has its own isolated timer/request tests; this exercises only the real paint callback.
qa.connectionMonitor.receive=()=>{};
qa.generation.callbacks.connection('Not tested',{runtime:null,checkedAt:200,error:'Local status unavailable'});
assert.ok(elements.get('llm-header-status').classList.contains('connection-error'));
assert.match(elements.get('llm-header-status').title,/Local status unavailable/);
qa.generation.callbacks.connection('Connected',{runtime:{state:'Running'},checkedAt:100,error:null});
assert.ok(elements.get('llm-header-status').classList.contains('connection-error'));
qa.generation.callbacks.connection('Connected',{runtime:{state:'Running'},checkedAt:300,error:null});
assert.ok(elements.get('llm-header-status').classList.contains('connection-complete'));
""")


if __name__ == "__main__":
    unittest.main()

"""Visible repair instructions and complete console, isolated software fixtures only."""
from pathlib import Path
import shutil
import subprocess
import unittest

PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
class DOMNode {
 constructor(tag='div'){this.tag=tag;this.children=[];this.attributes={};this.dataset={};this.listeners={};this.style={};this.disabled=false;this.isConnected=true;this._text='';this.className='';this.value='';this.type='';this.checked=false;this.id='';this.open=false;
 this.classList={add:(...names)=>{this.className=[...new Set([...this.className.split(/\s+/),...names])].join(' ').trim();},remove:(...names)=>{this.className=this.className.split(/\s+/).filter(name=>!names.includes(name)).join(' ');},contains:name=>this.className.split(/\s+/).includes(name)};}
 set textContent(value){this._text=String(value);this.children=[];}get textContent(){return this._text+this.children.map(node=>node.textContent).join('');}
 set innerHTML(_value){throw Error('Untrusted prompt/log must not be interpreted as HTML');}
 setAttribute(key,value){this.attributes[key]=String(value);if(key==='class')this.className=String(value);if(key==='id')this.id=String(value);if(key.startsWith('data-'))this.dataset[key.slice(5).replace(/-([a-z])/g,(_,letter)=>letter.toUpperCase())]=String(value);}
 getAttribute(key){return key==='class'?this.className:this.attributes[key]??null;}
 hasAttribute(key){return this.getAttribute(key)!==null;}
 append(...nodes){this.children.push(...nodes.flat(Infinity));}
 prepend(...nodes){this.children.unshift(...nodes.flat(Infinity));}
 replaceChildren(...nodes){this._text='';this.children=[];this.append(...nodes);}
 addEventListener(name,handler){(this.listeners[name]??=[]).push(handler);}
 click(){for(const handler of this.listeners.click||[])handler({currentTarget:this,target:this,preventDefault(){}});}
 focus(){this.focusCount=(this.focusCount||0)+1;}scrollIntoView(){this.scrollCount=(this.scrollCount||0)+1;}setSelectionRange(){}
 contains(node){return this===node||descendants(this).includes(node);}
 querySelectorAll(selector){return descendants(this).filter(node=>matches(node,selector));}
 querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
}
const descendants=node=>node.children.flatMap(child=>[child,...descendants(child)]);
function matches(node,selector){if(selector.startsWith('#'))return node.id===selector.slice(1);if(selector.startsWith('.'))return node.className.split(/\s+/).includes(selector.slice(1));const attr=selector.match(/^\[([^=\]]+)(?:="([^"]*)")?\]$/);if(attr)return attr[2]===undefined?node.hasAttribute(attr[1]):node.getAttribute(attr[1])===attr[2];return node.tag===selector;}
const document={body:new DOMNode('body'),activeElement:null,visibilityState:'visible',createElement:tag=>new DOMNode(tag),createTextNode:text=>{const node=new DOMNode('#text');node.textContent=text;return node;}};
const requests=[],notices=[],downloads=[],timers=[];
const context=vm.createContext({console,document,Node:DOMNode,structuredClone,URL,Date,JSON,Blob,TextEncoder,TextDecoder,crypto:{randomUUID:()=> 'isolated-display-qa'},location:{href:'http://localhost:9999/',origin:'http://localhost:9999'},setTimeout:callback=>{timers.push(callback);return timers.length;},clearTimeout(){},fetch(...args){requests.push(args);throw Error('Rendering QA must not call an API');}});
const directory=path.resolve('src/gui'),modules=new Map();
function load(file){file=path.resolve(file);assert.ok(file.startsWith(directory+path.sep));if(modules.has(file))return modules.get(file);const module=new vm.SourceTextModule(fs.readFileSync(file,'utf8'),{context,identifier:file});modules.set(file,module);return module;}
async function module(name){const value=load(path.join(directory,name));if(value.status==='unlinked')await value.link((specifier,referrer)=>load(path.resolve(path.dirname(referrer.identifier),specifier)));if(value.status==='linked')await value.evaluate();return value.namespace;}
const project={envelope:{workspace_identity:{session_id:'session-a',project_id:'project-a',system_id:'system-a',read_only:false},revision:{id:'revision-a'},llm:{profile_revision_id:'profile-a',profile:{execution_location:'Local',model:'qa-model',max_output_tokens:3072,context_window:16384}},workflow:['global_settings','graph_editor','specifications'].map(id=>({id,label:id,review_status:'Accepted',freshness:'Current'})),generation:{jobs:[],nodes:[]}},design:{id:'design-a',project:{name:'Isolated display'},nodes:[{id:'node-a',name:'Job control',module_name:'qa_control'}]},stage:'local_rtl_generation',dirty:false,conflict:null,busy:false};
const callbacks={project:()=>project,request:(...args)=>{requests.push(args);throw Error('Rendering QA must not call an API');},notify:message=>notices.push(message),toast:message=>notices.push(message)};
const test=(host,id)=>host.querySelector(`[data-testid="${id}"]`);
"""


class RepairPromptConsoleGuiTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for isolated GUI rendering checks.")
        result = subprocess.run(
            [node, "--experimental-vm-modules", "-e", CLIENT +
             "\n(async()=>{\n" + body +
             "\nassert.equal(requests.length,0);})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});"],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)



    def test_prompt_helpers_preserve_complete_literal_instruction_and_each_message(self):
        self.client(r"""
const {promptTranscript,promptMessagesView,instructionView}=await module('prompt_view.js');
const instruction='  Original correction\r\nMove declarations. <script>not executable</script>\n'+('未省略の修正指示\n'.repeat(1500))+'LAST_INSTRUCTION  ';
const messages=[{role:'system',content:'SYSTEM\r\nDo not alter source.'},{role:'assistant',content:'Previous actual answer\nmodule saved; endmodule'},{role:'user',content:instruction}];
const contextValue={messages},before=JSON.stringify(contextValue);
const prompt=promptMessagesView(contextValue,{prefix:'qa-saved',open:true}),display=instructionView(instruction,{prefix:'qa-instruction'});
assert.equal(prompt.open,true);assert.equal(test(display,'qa-instruction-instruction').textContent,instruction);
messages.forEach((message,index)=>{const pre=test(prompt,`qa-saved-message-${index}`);assert.equal(pre.textContent,message.content);assert.equal(pre.children.length,0);assert.equal(pre.getAttribute('tabindex'),'0');});
const transcript=promptTranscript(messages);for(const message of messages)assert.ok(transcript.includes(message.content));assert.ok(transcript.endsWith('LAST_INSTRUCTION  '));
assert.equal(JSON.stringify(contextValue),before);
""")

    def test_batch_preview_exposes_complete_per_node_instructions_separate_from_first_messages(self):
        self.client(r"""
const {GenerationBatchWorkspace}=await module('generation_batch.js'),batchUI=new GenerationBatchWorkspace(callbacks);
const instructionA='Fix actual driver error\n'+('preserve full required correction\n'.repeat(400))+'END_CORRECTION_A';
const instructionB='Fix another saved error <img src=x onerror=bad>\r\nEND_CORRECTION_B';
const firstMessages=[{role:'system',content:'Scoped Verilog-2005 generation.'},{role:'user',content:'Exact first provider request\r\n'+instructionA}];
const plan={plan_id:'plan-a',revision_id:'revision-a',profile_revision_id:'profile-a',mode:'synthesis_repair',ready_to_start:true,profile:project.envelope.llm.profile,items:[{node_id:'node-a',node_name:'Job control',operation:'repair',status:'Queued',base_job_id:'candidate-a',source_workflow_run_id:'synthesis-a',instruction:instructionA},{node_id:'node-b',node_name:'Other node',operation:'repair',status:'Queued',base_job_id:'candidate-b',source_workflow_run_id:'synthesis-b',instruction:instructionB}],first_request_context:{messages:firstMessages,estimated_input_tokens:6000}};
batchUI.plan=plan;batchUI.planSource=batchUI.sourceIdentity();batchUI.instruction='Different draft must not replace frozen instructions';
const before=JSON.stringify(plan),rendered=batchUI.renderPlan(),panel=test(rendered,'generation-batch-readable-request');
assert.ok(panel);assert.match(panel.textContent,/not sent/);assert.equal(test(panel,'generation-batch-instruction-node-a-instruction').textContent,instructionA);assert.equal(test(panel,'generation-batch-instruction-node-b-instruction').textContent,instructionB);
assert.equal(rendered.querySelectorAll('details').some(details=>details.contains(test(panel,'generation-batch-instruction-node-a-instruction'))),false,'Repair instructions need no JSON expansion');
firstMessages.forEach((message,index)=>assert.equal(test(panel,`generation-batch-request-message-${index}`).textContent,message.content));assert.equal(test(rendered,'generation-batch-start').disabled,false);
assert.equal(JSON.stringify(plan),before);assert.doesNotMatch(panel.textContent,/Different draft must not replace/);
""")


    def test_next_step_read_instructions_action_focuses_the_preview_without_submitting(self):
        self.client(r"""
const {GenerationBatchWorkspace}=await module('generation_batch.js'),batchUI=new GenerationBatchWorkspace(callbacks);
const plan={plan_id:'plan-a',revision_id:'revision-a',profile_revision_id:'profile-a',mode:'synthesis_repair',ready_to_start:true,profile:project.envelope.llm.profile,items:[{node_id:'node-a',node_name:'Job control',operation:'repair',status:'Queued',instruction:'Full required saved correction'}],first_request_context:{messages:[{role:'user',content:'Exact unsent first request'}],estimated_input_tokens:6000}};
batchUI.plan=plan;batchUI.planSource=batchUI.sourceIdentity();const host=new DOMNode();batchUI.generationHost=host;host.append(batchUI.renderPlan());const before=JSON.stringify(plan),guide=batchUI.guidance();assert.equal(guide.primary.label,'Start repair batch');assert.equal(guide.secondary.label,'Read repair instructions');
const panel=test(host,'generation-batch-readable-request');assert.equal(panel.getAttribute('tabindex'),'-1');guide.secondary.action();assert.equal(panel.focusCount,1);assert.equal(panel.scrollCount,1);assert.equal(batchUI.plan,plan);assert.equal(JSON.stringify(plan),before);assert.equal(batchUI.busy,false);
""")

    def test_saved_job_request_displays_its_original_instruction_not_unsent_draft_or_preview(self):
        self.client(r"""
const {GenerationWorkspace}=await module('generation.js'),workspace=new GenerationWorkspace(callbacks);
const instruction='Original saved correction\n'+('full exact correction\n'.repeat(800))+'END_SAVED_CORRECTION';
const messages=[{role:'system',content:'Actual saved system instruction'},{role:'user',content:'Actual saved user request\r\n'+instruction}];
const job={id:'actual-job-a',node_id:'node-a',operation:'repair',base_job_id:'earlier-a',instruction,context_id:'saved-context-a',context:{messages},execution_status:'Completed',validation_status:'Passed',freshness:'Current',rtl:'module qa_control; endmodule',checks:{interface:{validation_status:'Passed'}}};
workspace.instruction='Unsent future draft';workspace.preview={context_id:'preview-b',messages:[{role:'user',content:'Unsent future preview'}]};workspace.artifactTab='request';
const before=JSON.stringify(job),rendered=workspace.artifactView(job),panel=test(rendered,'generation-saved-request');
assert.ok(panel);assert.equal(test(panel,'generation-saved-request-instruction').textContent,instruction);assert.equal(test(panel,'generation-saved-request-messages').open,true);
messages.forEach((message,index)=>assert.equal(test(panel,`generation-saved-request-message-${index}`).textContent,message.content));assert.doesNotMatch(panel.textContent,/Unsent future/);assert.match(panel.textContent,/actual-job-a.*earlier-a.*saved-context-a/);
assert.ok(test(panel,'download-generation-request-text'));assert.equal(JSON.stringify(job),before);assert.equal(workspace.instruction,'Unsent future draft');assert.equal(workspace.preview.context_id,'preview-b');
""")


    def test_request_button_and_latest_job_navigation_change_only_the_inspected_record(self):
        self.client(r"""
const {GenerationWorkspace}=await module('generation.js'),workspace=new GenerationWorkspace(callbacks);
const job=id=>({id,node_id:'node-a',operation:'repair',base_job_id:'base-'+id,instruction:'Correction saved for '+id,context_id:'context-'+id,context:{messages:[{role:'user',content:'Actual saved messages for '+id}]},profile_revision_id:'profile-a',revision_id:'revision-a',execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',finished_at:'saved',rtl:'module qa_control; endmodule',checks:{interface:{validation_status:'Passed'}},events:[]});
const old=job('older-a'),latest=job('latest-a');workspace.generation={jobs:[old,latest],nodes:[{node_id:'node-a',latest_job_id:latest.id,accepted_job_id:latest.id}],reviews:[]};workspace.nodeId='node-a';workspace.selectedJobId=old.id;workspace.llm=project.envelope.llm;
const host=new DOMNode(),result=new DOMNode();result.id='generation-result-content';host.append(result);workspace.host=host;const before=JSON.stringify(workspace.generation);workspace.renderResult();
assert.ok(test(host,'generation-read-request'));assert.ok(test(host,'generation-latest-request'));assert.equal(test(host,'generation-tab-rtl').getAttribute('aria-selected'),'true');assert.equal(test(host,'generation-tab-request').getAttribute('aria-selected'),'false');test(host,'generation-read-request').click();assert.equal(workspace.artifactTab,'request');assert.equal(test(host,'generation-tab-request').getAttribute('aria-selected'),'true');assert.equal(test(host,'generation-tab-rtl').getAttribute('aria-selected'),'false');assert.equal(test(host,'generation-saved-request-instruction').textContent,'Correction saved for older-a');
test(host,'generation-latest-request').click();assert.equal(workspace.selectedJobId,'latest-a');assert.equal(test(host,'generation-saved-request-instruction').textContent,'Correction saved for latest-a');assert.equal(test(host,'generation-latest-request'),null);assert.equal(JSON.stringify(workspace.generation),before);
""")

    def test_missing_saved_messages_are_explicit_and_do_not_fabricate_the_next_request(self):
        self.client(r"""
const {GenerationWorkspace}=await module('generation.js'),workspace=new GenerationWorkspace(callbacks);
workspace.artifactTab='request';workspace.preview={messages:[{role:'user',content:'Future preview must not appear'}]};
const job={id:'legacy-verify-job',operation:'verify',provider_request_executed:false,instruction:'',context:{},execution_status:'Completed'};
const rendered=workspace.artifactView(job);assert.match(rendered.textContent,/verification-only record sent no model request/);assert.match(rendered.textContent,/No request messages were saved/);assert.doesNotMatch(rendered.textContent,/Future preview/);assert.match(test(rendered,'generation-saved-request-instruction').textContent,/No additional instruction/);
""")

    def test_synthesis_console_is_visible_complete_keyboard_focusable_and_safe_text(self):
        self.client(r"""
const {LocalWorkflow}=await module('workflow.js');project.stage='local_synthesis';
const stdout='FIRST_STDOUT\n'+('unabridged synthesis output <script>never execute</script> 日本語\r\n'.repeat(1300))+'\nLAST_STDOUT';
const stderr='FIRST_STDERR\r\n'+('driver warning <img src=x onerror=bad>\n'.repeat(700))+'\r\nLAST_STDERR';
const run={id:'synthesis-long',node_id:'node-a',stage_id:'local_synthesis',candidate_id:'candidate-a',revision_id:'revision-a',requested_revision_id:'revision-a',input_hash:'input-a',rtl_sha256:'rtl-a',execution_status:'Completed',validation_status:'Failed',review_status:'Awaiting Review',freshness:'Current',finished_at:'saved',checks:{executed:true,exit_code:1,commands:[{command:['yosys','-Q','-p','read_verilog candidate.v; check -assert'],status:'Completed',exit_code:1,stdout,stderr}],stdout,stderr},diagnostics:[]};
const before=JSON.stringify(run),local=new LocalWorkflow(callbacks);local.nodeId='node-a';local.runs=[run];local.runId=run.id;
const host=new DOMNode(),result=new DOMNode();result.setAttribute('data-testid','workflow-result');host.append(result);local.host=host;local.renderResult();
const consoleSection=test(host,'workflow-console'),output=test(host,'workflow-console-output');
assert.ok(consoleSection);assert.ok(output);assert.ok(output.textContent.includes(stdout));assert.ok(output.textContent.includes(stderr));
assert.ok(output.textContent.includes('LAST_STDOUT'));assert.ok(output.textContent.includes('LAST_STDERR'));assert.ok(output.textContent.includes('read_verilog candidate.v; check -assert'));
assert.equal(output.getAttribute('tabindex'),'0');assert.equal(output.getAttribute('role'),'region');assert.equal(output.children.length,0,'Tool output must be literal text');
assert.equal(host.querySelectorAll('details').some(details=>details.contains(consoleSection)),false,'Complete console is visible without opening JSON details');
for(const id of ['workflow-download-console','workflow-download-stdout','workflow-download-stderr'])assert.equal(test(host,id).disabled,false);
const exactText=output.textContent;output.scrollHeight=123456;output.scrollTop=40;test(host,'workflow-console-bottom').click();assert.equal(output.scrollTop,123456);assert.equal(output.focusCount,1);test(host,'workflow-console-top').click();assert.equal(output.scrollTop,0);assert.equal(output.focusCount,2);assert.equal(output.textContent,exactText);
assert.equal(JSON.stringify(run),before,'Rendering must not edit saved command output');
""")

    def test_simulation_console_retains_all_recorded_output_and_empty_stream_download_gates(self):
        self.client(r"""
const {LocalWorkflow}=await module('workflow.js');project.stage='local_netlist_simulation';
const stdout='simulation start\n'+('cycle values X 0 1 Z\n'.repeat(1500))+'HULLCIRQ_FAIL final cycle 99';
const run={id:'simulation-long',node_id:'node-a',stage_id:'local_netlist_simulation',candidate_id:'candidate-a',execution_status:'Completed',validation_status:'Failed',review_status:'Awaiting Review',freshness:'Current',finished_at:'saved',checks:{executed:true,commands:[],stdout,stderr:''},diagnostics:[]};
const before=JSON.stringify(run),local=new LocalWorkflow(callbacks);local.nodeId='node-a';local.runs=[run];local.runId=run.id;
const host=new DOMNode(),result=new DOMNode();result.setAttribute('data-testid','workflow-result');host.append(result);local.host=host;local.renderResult();
assert.ok(test(host,'workflow-console-output').textContent.includes(stdout));assert.equal(test(host,'workflow-download-stdout').disabled,false);assert.equal(test(host,'workflow-download-stderr').disabled,true);assert.equal(test(host,'workflow-download-console').disabled,false);
assert.equal(JSON.stringify(run),before);
""")


if __name__ == "__main__":
    unittest.main()

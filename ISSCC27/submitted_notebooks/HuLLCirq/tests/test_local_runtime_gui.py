"""Focused local-server client behavior; no process, inference or EDA execution."""
from pathlib import Path
import shutil
import subprocess
import unittest

PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
class DOMDouble {
  constructor(tag,attributes={}) {this.tag=tag;this.children=[];this.isConnected=true;Object.assign(this,attributes);}
  append(...children) {this.children.push(...children.flat(Infinity).filter(child=>child!==null&&child!==undefined&&child!==false));}
  replaceChildren(...children) {this.children=[];this.append(...children);}
  setAttribute(name,value) {this[name]=String(value);}
  querySelector(selector) {
    const matches=node=>node instanceof DOMDouble && (selector.startsWith('#') ? node.id===selector.slice(1) : node['data-testid']===selector.match(/^\[data-testid="([^"]+)"\]$/)?.[1]);
    for(const child of this.children) {if(matches(child))return child;const found=child instanceof DOMDouble&&child.querySelector(selector);if(found)return found;}
    return null;
  }
}
const el=(tag,attributes={},...children)=>{const node=new DOMDouble(tag,attributes);node.append(...children);return node;};
const requests=[],notices=[],timers=new Map();let timerID=0,responder=async()=>({runtime:{state:'Stopped',owned:false,can_start:true,can_stop:false}});
const project={envelope:{workspace_identity:{session_id:'session-a',project_id:'project-a',system_id:'system-a',read_only:false},revision:{id:'revision-a'},workflow:[]},design:{nodes:[]},stage:'global_settings'};
const sandbox={el,field:(label,value,change,options)=>el('div',options),badge:(text,tone)=>el('span',{text,tone}),downloadJsonResponse:()=>{},structuredClone,URL,
  setTimeout:callback=>{const id=++timerID;timers.set(id,callback);return id;},clearTimeout:id=>timers.delete(id)};
vm.createContext(sandbox);
const promptViewSource=fs.readFileSync('src/gui/prompt_view.js','utf8').replace(/^import[^\n]+\n/gm,'').replace(/export /g,'');
vm.runInContext(promptViewSource,sandbox);
let source=fs.readFileSync('src/gui/generation.js','utf8').replace(/^import[^\n]+\n/gm,'').replace('export class GenerationWorkspace','class GenerationWorkspace');
vm.runInContext(source+'\nglobalThis.qa={GenerationWorkspace,PROFILE_DEFAULTS};',sandbox);
const callbacks={project:()=>project,request:(...args)=>{requests.push(args);return responder(...args);},envelope:()=>assert.fail('No profile or circuit envelope should be adopted by runtime controls'),toast:message=>notices.push(message),notify:message=>notices.push(message)};
const workspace=new sandbox.qa.GenerationWorkspace(callbacks);
workspace.llm.profile={...sandbox.qa.PROFILE_DEFAULTS};workspace.llm.profile_revision_id='profile-a';workspace.profileDraft={...workspace.llm.profile};
const mount=()=>{const host=new DOMDouble('div');workspace.renderProvider(host);return host;};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const deferred=()=>{let resolve,reject;const promise=new Promise((r,j)=>{resolve=r;reject=j;});return{promise,resolve,reject};};
const status=(state,extra={})=>({runtime:{state,owned:false,endpoint:'http://127.0.0.1:11435/v1',model:'qwen3:8b',can_start:state==='Stopped',can_stop:false,...extra}});
const runTimer=()=>{const [id,callback]=timers.entries().next().value;timers.delete(id);callback();};
const text=node=>node instanceof DOMDouble?[node.text||node.textContent||'',...node.children.map(text)].join(' '):String(node||'');
"""


class LocalRuntimeGuiTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for isolated local-server UI checks.")
        result = subprocess.run(
            [node, "-e", CLIENT + "\n(async()=>{\n" + body +
             "\nconsole.log('Passed: local server UI behavior');\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});"],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mount_discovers_status_once_without_implicit_connection_or_generation(self):
        self.run_client(r"""
responder=async()=>status('Running',{owned:false,pid:202,log_path:'recorded server log'});
const host=mount();await tick();
assert.equal(requests.length,1);assert.equal(requests[0][0],'workspace/local-runtime');assert.equal(requests[0].length,1);
assert.equal(workspace.llm.probe,null);assert.equal(timers.size,0);
assert.equal(host.querySelector('[data-testid="local-runtime-start"]').disabled,true);
assert.equal(host.querySelector('[data-testid="local-runtime-stop"]').disabled,true);
assert.match(text(host.querySelector('[data-testid="local-runtime-status"]')),/outside HuLLCirq/);
assert.match(text(host.querySelector('[data-testid="local-runtime-status"]')),/recorded server log/);
workspace.refreshProviderActions();workspace.renderConnectionResult();assert.equal(requests.length,1);
""")

    def test_legacy_and_preserved_snapshot_do_not_mount_runtime_controls(self):
        self.run_client(r"""
delete project.envelope.workspace_identity;let host=mount();await tick();assert.equal(requests.length,0);
assert.equal(host.querySelector('[data-testid="local-runtime-panel"]'),null);
project.envelope.workspace_identity={session_id:'snapshot-session',project_id:'snapshot-project',system_id:'snapshot-system',read_only:true};
host=mount();await tick();assert.equal(requests.length,0);assert.equal(host.querySelector('[data-testid="local-runtime-panel"]'),null);
workspace.runtimeStatus=status('Running',{owned:true,can_stop:true}).runtime;
await workspace.requestRuntime('stop');assert.equal(requests.length,0);
""")

    def test_start_is_explicit_and_polls_only_during_transition(self):
        self.run_client(r"""
const host=mount();await tick();assert.match(text(host),/Start local LLM above/);
const gate=deferred();responder=route=>route.endsWith('/start')?gate.promise:Promise.resolve(status('Running',{owned:true,pid:204,can_stop:true}));
const start=workspace.requestRuntime('start');assert.equal(workspace.runtimeBusy,true);
const repeat=workspace.requestRuntime('start');assert.equal(repeat,start);assert.equal(requests.length,2);
assert.equal(requests[1][0],'workspace/local-runtime/start');assert.equal(JSON.stringify(requests[1][1]),'{}');
gate.resolve(status('Starting',{owned:true,pid:204}));await start;assert.equal(timers.size,1);
runTimer();await tick();assert.equal(workspace.runtimeStatus.state,'Running');assert.equal(timers.size,0);
assert.equal(host.querySelector('[data-testid="local-runtime-stop"]').disabled,false);
assert.equal(workspace.llm.probe,null);assert.equal(requests.some(([route])=>route.includes('llm/probe')||route.includes('generation')),false);
""")

    def test_saved_profile_and_supported_endpoint_are_required_for_start(self):
        self.run_client(r"""
mount();await tick();const count=requests.length;
for(const change of [profile=>profile.execution_location='Network',profile=>profile.base_url='https://example.invalid/v1',profile=>profile.model='other-model']) {
  workspace.llm.profile={...sandbox.qa.PROFILE_DEFAULTS};change(workspace.llm.profile);workspace.profileDraft={...workspace.llm.profile};
  workspace.renderRuntimeStatus();assert.match(workspace.runtimeStartGate(),/GUI startup supports/);
  await workspace.requestRuntime('start');assert.equal(requests.length,count);
}
for(const base_url of ['http://127.0.0.1:11435/v1?target=remote','http://localhost:11435/v1#fragment','http://name:secret@localhost:11435/v1','http://localhost:11434/v1','http://localhost:11435/other','https://localhost:11435/v1']) {
  workspace.llm.profile={...sandbox.qa.PROFILE_DEFAULTS,base_url};workspace.profileDraft={...workspace.llm.profile};
  await workspace.requestRuntime('start');assert.equal(requests.length,count);assert.match(workspace.runtimeStartGate(),/GUI startup supports/);
}
workspace.llm.profile={...sandbox.qa.PROFILE_DEFAULTS,base_url:'http://localhost:11435/v1/'};workspace.profileDraft={...workspace.llm.profile};
assert.equal(workspace.runtimeStartGate(),'');workspace.renderRuntimeStatus();assert.equal(workspace.providerHost.querySelector('[data-testid="local-runtime-start"]').disabled,false);
workspace.llm.profile={...sandbox.qa.PROFILE_DEFAULTS};workspace.profileDraft={...workspace.llm.profile,name:'Unsaved edit'};
await workspace.requestRuntime('start');assert.equal(requests.length,count);assert.match(workspace.runtimeStartGate(),/Save the provider profile/);
workspace.profileDraft={...workspace.llm.profile};workspace.llm.profile_revision_id=null;
await workspace.requestRuntime('start');assert.equal(requests.length,count);
""")

    def test_stop_only_targets_owned_process_and_never_runs_profile_probe(self):
        self.run_client(r"""
responder=async()=>status('Running',{owned:false,can_stop:true});mount();await tick();
await workspace.requestRuntime('stop');assert.equal(requests.length,1);
workspace.runtimeStatus=status('Running',{owned:true,can_stop:true}).runtime;
responder=async route=>route.endsWith('/stop')?status('Stopping',{owned:true}):status('Stopped');
await workspace.requestRuntime('stop');assert.equal(requests[1][0],'workspace/local-runtime/stop');assert.equal(timers.size,1);
runTimer();await tick();assert.equal(workspace.runtimeStatus.state,'Stopped');assert.equal(timers.size,0);
assert.equal(workspace.llm.probe,null);
""")

    def test_coder_saved_profile_cold_start_is_enabled_and_displays_launch_context_source(self):
        self.run_client(r"""
workspace.llm.profile={...sandbox.qa.PROFILE_DEFAULTS,model:'qwen2.5-coder:7b',context_window:32768};workspace.profileDraft={...workspace.llm.profile};
const host=mount();await tick();assert.equal(workspace.runtimeStartGate(),'');assert.equal(host.querySelector('[data-testid="local-runtime-start"]').disabled,false);
responder=async route=>{assert.equal(route,'workspace/local-runtime/start');return status('Running',{owned:true,can_stop:true,model:'qwen2.5-coder:7b',managed_environment:{OLLAMA_CONTEXT_LENGTH:'32768'},context_length_source:'saved_provider_profile'});};
await workspace.requestRuntime('start');assert.equal(requests.length,2);assert.equal(JSON.stringify(requests[1][1]),'{}');assert.equal(workspace.runtimeStatus.model,'qwen2.5-coder:7b');
assert.match(text(host.querySelector('[data-testid="local-runtime-context"]')),/32,768 tokens.*Saved provider profile/);
assert.match(text(host.querySelector('[data-testid="local-runtime-context"]')),/Restart the local server/);
assert.equal(workspace.llm.probe,null);assert.equal(requests.some(([route])=>route.includes('llm/probe')||route.includes('generation')),false);
""")

    def test_runtime_context_display_records_environment_override_without_changing_profile(self):
        self.run_client(r"""
workspace.llm.profile={...sandbox.qa.PROFILE_DEFAULTS,model:'qwen2.5-coder:7b',context_window:32768};workspace.profileDraft={...workspace.llm.profile};
responder=async()=>status('Running',{owned:true,can_stop:true,model:'qwen2.5-coder:7b',managed_environment:{OLLAMA_CONTEXT_LENGTH:'20480'},context_length_source:'parent_environment'});
const host=mount();await tick();assert.match(text(host.querySelector('[data-testid="local-runtime-context"]')),/20,480 tokens.*Server environment override/);assert.equal(workspace.llm.profile.context_window,32768);
responder=async()=>status('Running',{owned:false});await workspace.requestRuntime();assert.equal(host.querySelector('[data-testid="local-runtime-context"]'),null);
""")

    def test_late_response_is_ignored_after_session_change_and_new_mount_still_loads(self):
        self.run_client(r"""
const old=deferred();responder=()=>old.promise;const oldHost=mount();
project.envelope.workspace_identity.session_id='session-b';oldHost.isConnected=false;
responder=async()=>status('Stopped');const host=mount();await tick();assert.equal(requests.length,2);
old.resolve(status('Starting',{owned:true}));await tick();assert.equal(workspace.runtimeStatus.state,'Stopped');assert.equal(timers.size,0);
assert.equal(host.querySelector('[data-testid="local-runtime-start"]').disabled,false);
workspace.runtimeStatus=status('Starting',{owned:true}).runtime;responder=async()=>status('Starting',{owned:true});
await workspace.requestRuntime();assert.equal(timers.size,1);host.isConnected=false;runTimer();await tick();assert.equal(requests.length,3);assert.equal(timers.size,0);
""")

    def test_request_error_shows_summary_and_refresh_recovers_without_poll_loop(self):
        self.run_client(r"""
responder=async()=>{throw{summary:'Prepared executable is unavailable',message:'less useful detail'};};
const host=mount();await tick();assert.equal(workspace.runtimeBusy,false);assert.equal(timers.size,0);
assert.match(text(host.querySelector('[data-testid="local-runtime-error"]')),/Prepared executable is unavailable/);
responder=async()=>status('Failed',{error:{summary:'Server exited during startup'},log_path:'startup.log'});
await workspace.requestRuntime();assert.equal(timers.size,0);assert.match(text(host.querySelector('[data-testid="local-runtime-error"]')),/Server exited during startup/);
responder=async()=>status('Stopped');await workspace.requestRuntime();assert.equal(workspace.runtimeError,null);assert.equal(timers.size,0);
assert.equal(host.querySelector('[data-testid="local-runtime-start"]').disabled,false);
""")

    def test_workspace_switch_clears_previous_runtime_observations(self):
        self.run_client(r"""
workspace.receive({llm:workspace.llm});
workspace.runtimeStatus=status('Stopped').runtime;workspace.runtimeError='Previous system error';workspace.runtimeCheckedAt=1234;
project.envelope.workspace_identity.session_id='session-b';workspace.receive({llm:workspace.llm});
assert.equal(workspace.runtimeStatus,null);assert.equal(workspace.runtimeError,null);assert.equal(workspace.runtimeCheckedAt,null);
assert.equal(requests.length,0);assert.equal(timers.size,0);
""")

    def test_runtime_error_observer_receives_timestamp_and_no_generated_result(self):
        self.run_client(r"""
const observations=[];callbacks.connection=(label,observation)=>{if(observation)observations.push(observation);};
responder=async()=>{throw Error('Local status unavailable');};mount();await tick();
assert.equal(requests.length,1);assert.deepEqual(requests[0],['workspace/local-runtime']);
assert.ok(observations.at(-1).checkedAt);assert.equal(observations.at(-1).error,'Local status unavailable');
assert.equal(observations.at(-1).runtime,null);assert.equal(workspace.llm.probe,null);
""")


if __name__ == "__main__":
    unittest.main()

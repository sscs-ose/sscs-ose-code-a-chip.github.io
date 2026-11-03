"""Initial loading/recovery presentation only; no browser, API or saved writes."""
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('src/gui/index.html','utf8');
const source=fs.readFileSync('src/gui/app.js','utf8');
const bootstrap=fs.readFileSync('src/gui/bootstrap.js','utf8');
const startSource=source.slice(source.indexOf('async function start() {'),source.lastIndexOf('\nstart();'));
assert.ok(startSource.startsWith('async function start() {'));
function fixture(){
 const calls=[],elements=new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(x=>[x[1],{
   hidden:false,dataset:{},textContent:'',attributes:{},children:[],
   setAttribute(k,v){this.attributes[k]=v;},append(...v){this.children.push(...v);},
   addEventListener(){},replaceChildren(...v){this.children=v;}
 }]));
 const removed=[];const workspaceElement={hidden:false};
 const document={documentElement:{dataset:{}},body:{classList:{remove:x=>removed.push(x)}},
   getElementById:id=>{assert.ok(elements.has(id),'Missing DOM id '+id);return elements.get(id);},
   querySelector:selector=>{assert.equal(selector,'.workspace');return workspaceElement;}};
 const module=()=>({receive:()=>calls.push('receive')});
 const sandbox={executionSubmissions:{observeRead(){}},executionSubmissionScope:()=> 'software-project:software-system',document,console:{error(){}},location:{reload(){throw Error('No automatic reload');}},
   workspace:{initialize:async()=>({active:{project_id:'software-project',system_id:'software-system'}})},
   state:{},workspaceEnabled:false,activeWorkspace:null,
   attachCommands:()=>calls.push('attach'),configureBrowserScope:()=>calls.push('scope'),
   loadRecoveredDrafts:()=>calls.push('load-draft'),restoreBrowserDraft:()=>calls.push('restore-draft'),
   receiveExecution:()=>calls.push('receive-execution'),clone:structuredClone,
   generationBatches:module(),generation:module(),adoption:module(),localFlow:module(),implementationSpecs:module(),
   globalGeneration:module(),globalFlow:module(),physicalFlow:module(),drcFlow:module(),lvsFlow:module(),postlayoutFlow:module(),
   render:()=>calls.push('render'),notify:()=>calls.push('notify'),
   section:()=>({section:true}),el:()=>({button:true}),
   autosave(){throw Error('Loading screen must not save a draft');},
   saveDesign(){throw Error('Loading screen must not write a design');},
   fetch(){throw Error('No real network request in isolated QA');},
   api:async route=>{calls.push(route);return {design:{},revision:{id:'software-revision'}};}};
 sandbox.byId=document.getElementById;
 vm.createContext(sandbox);vm.runInContext(startSource+'\nglobalThis.start=start;',sandbox);
 return {sandbox,elements,calls,removed,workspaceElement};
}
function bootFixture(){
 const f=fixture();f.timers=[];
 f.sandbox.setTimeout=callback=>{f.timers.push(callback);return 1;};
 f.sandbox.clearTimeout=()=>{};
 f.sandbox.mockImport=()=>Promise.resolve();
 f.run=()=>vm.runInContext(bootstrap.replace("import('./app.js')",'mockImport()'),f.sandbox);
 return f;
}
"""


class GuiStartupScreenTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated loading-screen checks.')
        result = subprocess.run([node, '-e', CLIENT + '\n(async()=>{\n' + body +
                                 "\nconsole.log('Passed: loading screen software fixture');\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});"],
                                cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_static_loading_screen_precedes_app_and_works_before_javascript(self):
        self.run_client(r"""
assert.match(html,/<body class="is-opening">/);
assert.ok(html.indexOf('id="startup-screen"')<html.indexOf('<header class="app-header">'));
assert.match(html,/<section id="startup-screen"[^>]*aria-busy="true"[^>]*>/);
assert.doesNotMatch(html.match(/<section id="startup-screen"[\s\S]*?<\/section>/)[0],/hidden[^>]*>\s*<div class="startup-card"/);
assert.match(html,/id="startup-detail"[^>]*role="status"[^>]*aria-live="polite"/);
assert.match(html,/<a id="startup-retry"[^>]*href="\/"[^>]*hidden>/);
const css=fs.readFileSync('src/gui/styles.css','utf8');
assert.match(css,/\.startup-screen\[hidden\]\s*\{\s*display: none;/);
assert.match(css,/@media \(prefers-reduced-motion: reduce\)/);
""")

    def test_waiting_screen_stays_visible_until_project_has_rendered(self):
        self.run_client(r"""
const f=fixture();let resolve;
f.sandbox.api=route=>{f.calls.push(route);return new Promise(done=>resolve=done);};
const pending=f.sandbox.start();await new Promise(done=>setImmediate(done));
assert.equal(f.elements.get('startup-screen').hidden,false);
assert.match(f.elements.get('startup-detail').textContent,/Opening saved system records/);
assert.equal(f.calls.includes('render'),false);assert.deepEqual(f.calls.filter(x=>x==='bootstrap'),['bootstrap']);
resolve({design:{},revision:{id:'software-revision'}});await pending;
assert.equal(f.elements.get('startup-screen').hidden,true);assert.deepEqual(f.removed,['is-opening']);
assert.equal(f.calls.at(-1),'render');assert.equal(f.sandbox.document.documentElement.dataset.hullcirqReady,'true');
""")

    def test_workspace_home_removes_loading_screen_without_project_bootstrap(self):
        self.run_client(r"""
const f=fixture();f.sandbox.workspace.initialize=async()=>({active:null});
await f.sandbox.start();
assert.equal(f.elements.get('startup-screen').hidden,true);assert.deepEqual(f.removed,['is-opening']);
assert.equal(f.elements.get('project-title').textContent,'No project open');
assert.equal(f.calls.includes('bootstrap'),false);assert.equal(f.calls.includes('restore-draft'),false);
""")

    def test_bootstrap_failure_keeps_recovery_screen_and_never_retries_automatically(self):
        self.run_client(r"""
const f=fixture();f.sandbox.api=async route=>{f.calls.push(route);throw Error('Software QA service unavailable');};
await f.sandbox.start();
assert.equal(f.elements.get('startup-screen').hidden,false);
assert.equal(f.elements.get('startup-screen').dataset.state,'error');
assert.equal(f.elements.get('startup-screen').attributes['aria-busy'],'false');
assert.match(f.elements.get('startup-detail').textContent,/Software QA service unavailable/);
assert.equal(f.elements.get('startup-retry').hidden,false);assert.deepEqual(f.removed,[]);
assert.deepEqual(f.calls.filter(x=>x==='bootstrap'),['bootstrap']);assert.equal(f.calls.includes('render'),false);
""")

    def test_catalog_failure_also_leaves_visible_explicit_retry(self):
        self.run_client(r"""
const f=fixture();f.sandbox.workspace.initialize=async()=>{throw Error('Software QA catalog unavailable');};
await f.sandbox.start();assert.equal(f.elements.get('startup-screen').dataset.state,'error');
assert.equal(f.elements.get('startup-retry').hidden,false);assert.equal(f.calls.includes('bootstrap'),false);
""")

    def test_slow_startup_watchdog_updates_static_screen_without_another_request(self):
        self.run_client(r"""
const f=bootFixture();f.run();assert.equal(f.timers.length,1);f.timers[0]();
assert.equal(f.elements.get('startup-screen').dataset.state,'waiting');
assert.match(f.elements.get('startup-detail').textContent,/Keep waiting or retry/);
assert.equal(f.elements.get('startup-retry').hidden,false);
assert.deepEqual(f.calls,[]);
""")

    def test_module_load_failure_is_visible_and_finished_start_is_not_covered_again(self):
        self.run_client(r"""
const failed=bootFixture();failed.sandbox.mockImport=()=>Promise.reject(Error('Software QA missing import'));
failed.run();await Promise.resolve();
assert.equal(failed.elements.get('startup-screen').dataset.state,'error');
assert.equal(failed.elements.get('startup-retry').hidden,false);
const ready=bootFixture();ready.sandbox.document.documentElement.dataset.hullcirqReady='true';
ready.run();ready.timers[0]();assert.equal(ready.elements.get('startup-screen').dataset.state,undefined);
assert.deepEqual(ready.calls,[]);
""")


if __name__ == '__main__':
    unittest.main()

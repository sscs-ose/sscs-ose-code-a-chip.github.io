"""Terminal dependency reconciliation in isolated JS; no browser/tools/API."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('src/gui/dependent_stage_refresh.js','utf8');
const app=fs.readFileSync('src/gui/app.js','utf8');
const globalSource=fs.readFileSync('src/gui/global_generation.js','utf8');
const sandbox={Map,Set,Promise,JSON,console};vm.createContext(sandbox);
vm.runInContext(source.replaceAll('export ','')+'\nglobalThis.DependentStageRefresh=DependentStageRefresh;globalThis.terminalDependencyStamps=terminalDependencyStamps;',sandbox);
const Refresh=sandbox.DependentStageRefresh;
const job=(id,status='Completed',review='Accepted',freshness='Current')=>({id,execution_status:status,validation_status:'Passed',review_status:review,freshness,source_key:'source-'+id,acceptance_epoch:1});
const s08=record=>({global_generation:{jobs:[record]}});
const tools=(...records)=>({global_workflow:{runs:records,stages:records.map(record=>({stage_id:record.stage_id,latest_run_id:record.id}))}});
function fixture(){let scope='project:system:revision:session';const calls=[],notices=[];const refresh=new Refresh({scope:()=>scope,refresh:async()=>{calls.push('GET project');return true;},notify:(...args)=>notices.push(args)});return {refresh,calls,notices,setScope:value=>{scope=value;}};}
"""


class DependentStageRefreshGuiTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which("node")
        if not node: self.skipTest("Node is required for isolated client QA.")
        result = subprocess.run([node, "-e", CLIENT + "\n(async()=>{\n" + body +
                                 "\nconsole.log('Passed: isolated dependency refresh');})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});"],
                                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_running_and_repeated_views_create_no_additional_reads(self):
        self.run_client(r"""
const f=fixture();await f.refresh.observe(s08(job('a','Running')));assert.deepEqual(f.calls,[]);
const done=s08(job('a'));await f.refresh.observe(done);await f.refresh.observe(done);await f.refresh.observe(done);
assert.deepEqual(f.calls,['GET project']);assert.deepEqual(f.notices,[]);
""")

    def test_full_response_already_refreshes_dependencies_without_extra_read(self):
        self.run_client(r"""
const f=fixture(),done=s08(job('a'));f.refresh.rememberFull(done);await f.refresh.observe(done);assert.deepEqual(f.calls,[]);
f.refresh.rememberFull(tools({...job('syn'),stage_id:'global_synthesis'}));
await f.refresh.observe(tools({...job('syn'),stage_id:'global_synthesis'}));assert.deepEqual(f.calls,[]);
""")

    def test_terminal_adoption_or_source_changes_get_one_fresh_snapshot_each(self):
        self.run_client(r"""
const f=fixture();await f.refresh.observe(s08(job('a','Completed','Awaiting Review')));
await f.refresh.observe(s08(job('a')));await f.refresh.observe(s08({...job('a'),source_key:'changed-source'}));
await f.refresh.observe(s08({...job('a'),source_key:'changed-source'}));assert.equal(f.calls.length,3);
""")

    def test_s09_s10_and_physical_terminals_refresh_downstream_gates(self):
        self.run_client(r"""
const f=fixture(),syn={...job('syn'),stage_id:'global_synthesis'},sim={...job('sim'),stage_id:'global_netlist_simulation'};
await f.refresh.observe(tools(syn));await f.refresh.observe(tools(syn,sim));
for(const key of ['physical_workflow','drc_workflow','lvs_workflow'])await f.refresh.observe({[key]:{runs:[job(key)],latest_run_id:key}});
assert.equal(f.calls.length,5);await f.refresh.observe(tools(syn,sim));assert.equal(f.calls.length,5);
""")

    def test_context_change_discards_queued_old_scope_and_allows_new_scope(self):
        self.run_client(r"""
const f=fixture();const old=f.refresh.observe(s08(job('a')));f.setScope('different-project');await old;assert.deepEqual(f.calls,[]);
await f.refresh.observe(s08(job('a')));assert.equal(f.calls.length,1);
""")

    def test_new_context_does_not_wait_for_an_old_context_inflight_read(self):
        self.run_client(r"""
const f=fixture();let releaseOld;f.refresh.callbacks.refresh=()=>new Promise(resolve=>{f.calls.push('old GET');releaseOld=resolve;});
const old=f.refresh.observe(s08(job('a')));await Promise.resolve();assert.equal(f.calls.length,1);
f.setScope('new-project');f.refresh.callbacks.refresh=async()=>{f.calls.push('new GET');return true;};
await f.refresh.observe(s08(job('a')));assert.deepEqual(f.calls,['old GET','new GET']);releaseOld(false);await old;
""")

    def test_failed_read_does_not_resend_or_poll_but_explicit_read_can_retry(self):
        self.run_client(r"""
const f=fixture();f.refresh.callbacks.refresh=async()=>{f.calls.push('GET project');throw Error('Offline');};
await f.refresh.observe(s08(job('a')));assert.equal(f.calls.length,1);assert.equal(f.notices.length,1);
assert.match(f.notices[0][0],/no execution was resent/);
f.refresh.callbacks.refresh=async()=>{f.calls.push('GET project');return true;};
await f.refresh.observe(s08(job('a')));assert.equal(f.calls.length,2);
""")

    def test_new_stage_terminals_serialize_aggregate_reads(self):
        self.run_client(r"""
const f=fixture();let release;f.refresh.callbacks.refresh=()=>new Promise(resolve=>{f.calls.push('GET project');release=resolve;});
const first=f.refresh.observe(s08(job('a')));await Promise.resolve();const second=f.refresh.observe(tools({...job('syn'),stage_id:'global_synthesis'}));
assert.equal(f.calls.length,1);release(true);await first;await Promise.resolve();assert.equal(f.calls.length,2);release(true);await second;
""")

    def test_actual_S08_compact_poll_invokes_dependency_callback_without_write(self):
        self.run_client(r"""
const context={console,Set,JSON};vm.createContext(context);
vm.runInContext(globalSource.replace(/^import .*$/mg,'').replace('export class GlobalGeneration','class GlobalGeneration')+'\nglobalThis.GlobalGeneration=GlobalGeneration;',context);
const calls=[],envelope={workflow:[{id:'global_rtl_generation'}]};const controller=new context.GlobalGeneration({
project:()=>({envelope}),request:async(path,body)=>{calls.push([path,body]);return s08(job('a'));},chrome:()=>{},dependencies:async payload=>{calls.push(['dependencies',payload.global_generation.jobs[0].id]);},notify:()=>{throw Error('unexpected error');}});
controller.refresh=()=>{};controller.pollError='old reconnect notice';controller.uncertainStart=true;await controller.refreshSaved();
assert.equal(controller.pollError,null);assert.equal(controller.uncertainStart,false);assert.deepEqual(calls,[['global-generation',undefined],['dependencies','a']]);
""")

    def test_actual_app_aggregate_helper_is_read_only_and_preserves_context(self):
        self.run_client(r"""
const start=app.indexOf('async function refreshDependentStageSnapshot() {'),end=app.indexOf('\nfunction mergeGlobalWorkflow',start);
assert.ok(start>=0&&end>start);let scope='old',requests=[],merged=[];const context={executionScope:()=>scope,activeWorkspace:{session_id:'session'},state:{envelope:{}},executionState:{serial:0},api:async(...args)=>{requests.push(args);return {saved:'snapshot'};},mergeGenerationEnvelope:value=>merged.push(value)};
vm.createContext(context);vm.runInContext(app.slice(start,end)+'\nglobalThis.refresh=refreshDependentStageSnapshot;',context);
assert.equal(await context.refresh(),true);assert.deepEqual(requests,[['project']]);assert.equal(merged.length,1);
context.api=async()=>{scope='other';return {saved:'wrong-scope'};};assert.equal(await context.refresh(),false);assert.equal(merged.length,1);
for(const key of ['global_workflow','physical_workflow','drc_workflow','lvs_workflow'])assert.ok(app.includes('dependentStageRefresh.observe({ '+key+': data })'));
assert.ok(app.includes('dependentStageRefresh.rememberFull(envelope)'));
""")

    def test_late_dependency_snapshot_cannot_replace_a_new_run_or_newer_response(self):
        self.run_client(r"""
const start=app.indexOf('async function refreshDependentStageSnapshot() {'),end=app.indexOf('\nfunction mergeGlobalWorkflow',start);
let resolveRead;const merged=[],context={executionScope:()=> 'same-scope',activeWorkspace:{session_id:'session'},state:{envelope:{id:'before'}},executionState:{serial:0},api:()=>new Promise(resolve=>{resolveRead=resolve;}),mergeGenerationEnvelope:value=>merged.push(value)};
vm.createContext(context);vm.runInContext(app.slice(start,end)+'\nglobalThis.refresh=refreshDependentStageSnapshot;',context);
const beforeRun=context.refresh();context.executionState.serial++;resolveRead({saved:'before-new-run'});assert.equal(await beforeRun,false);assert.equal(merged.length,0);
const beforeNewerResponse=context.refresh();context.state.envelope={id:'newer-running-poll'};resolveRead({saved:'old-read'});assert.equal(await beforeNewerResponse,false);assert.equal(merged.length,0);
const unchanged=context.refresh();resolveRead({saved:'current'});assert.equal(await unchanged,true);assert.equal(merged.length,1);
""")

    def test_actual_full_merger_preserves_draft_and_uncertain_start_guards(self):
        self.run_client(r"""
const begin=app.indexOf('function mergeGenerationEnvelope(envelope) {'),end=app.indexOf('\nasync function refreshDependentStageSnapshot',begin);
const base={revision:{id:'saved-r1'},design:{text:'saved'},workflow:[]},draft={text:'unsaved browser draft'};
const module=()=>({receive(){},uncertainStart:true,pollError:'preserved reconnect requirement'});
const context={state:{envelope:base,design:draft,saved:base.design},clone:structuredClone,dependentStageRefresh:{rememberFull(){}},
executionSubmissions:{lastResolution:null},executionSubmissionScope:()=> 'software-scope',flushActiveField(){},receiveExecution(){},generationBatches:module(),generation:module(),adoption:module(),localFlow:module(),implementationSpecs:module(),globalGeneration:module(),globalFlow:module(),physicalFlow:module(),drcFlow:module(),lvsFlow:module(),postlayoutFlow:module(),autosave(){},syncChrome(){},renderReview(){},notify(){}};
const selection=app.slice(app.indexOf('function applyExecutionSelection('),app.indexOf('async function publishExecutionOutcome('));
vm.createContext(context);vm.runInContext(selection+app.slice(begin,end)+'\nglobalThis.merge=mergeGenerationEnvelope;',context);
context.merge({...base,global_workflow:{ready:true,blocked_reason:null}});assert.equal(context.state.design,draft);assert.equal(context.state.saved.text,'saved');
for(const key of ['globalFlow','physicalFlow','drcFlow','lvsFlow']){assert.equal(context[key].uncertainStart,true);assert.equal(context[key].pollError,'preserved reconnect requirement');}
context.merge({revision:{id:'saved-r2'},design:{text:'external edit'},workflow:[]});assert.equal(context.state.design,draft);assert.equal(context.state.envelope.revision.id,'saved-r1');assert.equal(context.state.saved.text,'saved');assert.equal(context.state.externalRevision,'saved-r2');
""")


if __name__ == "__main__": unittest.main()

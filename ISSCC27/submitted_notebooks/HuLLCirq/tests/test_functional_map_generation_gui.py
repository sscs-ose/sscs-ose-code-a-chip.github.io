"""Declared isolated DOM client tests; no browser, EDA or actual project writes.

These exercise the production derived-view controls and races, not real layout
generation or circuit validation. Real GUI execution is recorded separately.
"""
from pathlib import Path
import json
import shutil
import subprocess
import unittest


PROJECT = Path(__file__).resolve().parents[1]

FIXTURE = r"""
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const source = fs.readFileSync('src/gui/physical_workflow.js', 'utf8')
  .replace(/^import[^\n]*\n/gm, '').replace('export class PhysicalWorkflow', 'class PhysicalWorkflow');
class DOMDouble {
  constructor(tag = 'div', attrs = {}) { this.tag = tag; Object.assign(this, attrs); this.children = []; }
  append(...children) { this.children.push(...children.flat(Infinity).filter(x => x != null)); }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  querySelector(selector) {
    const id = selector.match(/^\[data-testid="(.+)"\]$/)?.[1];
    for (const node of this.children) {
      if (node && typeof node === 'object') {
        if (node['data-testid'] === id) return node;
        const found = node.querySelector?.(selector); if (found) return found;
      }
    }
    return null;
  }
}
const el = (tag, attrs = {}, ...children) => { const node = new DOMDouble(tag, attrs); node.append(...children); return node; };
const timers = new Map(); let timerId = 0;
const sandbox = { el, badge: text => el('span', {text}), field: () => el('div'), console,
  setTimeout(fn) { timers.set(++timerId, fn); return timerId; }, clearTimeout(id) {timers.delete(id);},
  AbortController, TextEncoder, Blob, URL, sessionFetch() {throw new Error('Unexpected artifact read');} };
vm.createContext(sandbox); vm.runInContext(source + '\nglobalThis.PhysicalWorkflow = PhysicalWorkflow;', sandbox);
const tick = () => new Promise(resolve => setImmediate(resolve));
const deferred = () => { let resolve, reject; const promise = new Promise((r,j) => {resolve=r; reject=j;}); return {promise,resolve,reject}; };
const hash = digit => digit.repeat(64);
const run = id => ({id, revision_id:'revision-qa',record_hash:hash('a'),execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current'});
const job = (runId, status, id='software-qa-map-1') => ({id,layout_run_id:runId,status,phase:status==='Completed'?'registered':'capturing',message:'Declared software fixture',error:null,created_at:'2026-10-21T00:00:00+00:00'});
const result = (runId,jobs=[],canGenerate=true,registered=false) => ({run_id:runId,jobs,latest_job:jobs.at(-1)||null,can_generate:canGenerate,registered});
function setup() {
  timers.clear();
  const record=run('software-qa-s11'), other=run('software-qa-other-s11'), calls=[], pending=[], notices=[];
  let p={stage:'layout',design:{name:'Declared software fixture'},dirty:false,busy:false,conflict:false,
    envelope:{revision:{id:'revision-qa'},workspace_identity:{project_id:'qa-project',system_id:'qa-system',session_id:'qa-session'}}};
  const host=new DOMDouble(); host.isConnected=true;
  const generation=el('div',{'data-testid':'functional-map-generation'}),content=el('div',{'data-testid':'functional-map-content'});
  host.append(generation,content);
  const counters={envelope:0,workflow:0,reloads:0};
  const flow=new sandbox.PhysicalWorkflow({project:()=>p,request:(route,body)=>{
    calls.push({route,body}); assert.ok(pending.length,'Unexpected request '+route); return pending.shift().promise;
  },envelope(){counters.envelope++;},workflow(){counters.workflow++;},toast:text=>notices.push(text),notify:text=>notices.push(text)});
  flow.host=host; flow.layoutView='functional';flow.data={runs:[other,record],reviews:[],latest_run_id:record.id,accepted_run_id:record.id};flow.runId=record.id;
  flow.refresh=()=>flow.renderMapGeneration();
  flow.renderFunctionalMap=()=>{counters.reloads++;};
  const queue=()=>{const x=deferred();pending.push(x);return x;};
  const lookup=async(value=result(record.id))=>{const x=queue();flow.renderMapGeneration();x.resolve(value);await tick();};
  return {flow,host,generation,content,record,other,calls,pending,queue,lookup,counters,notices,
    project:()=>p,setProject:value=>{p=value;},find:id=>host.querySelector(`[data-testid="${id}"]`)};
}
"""

CASES = {
    "presentation_revision_keeps_original_map_source_binding": r"""
  const f=setup();f.project().envelope.revision.id='display-only-request';
  await f.lookup(result(f.record.id,[],true,true));
  assert.equal(f.flow.mapGenerationGate(f.record),'');
  const start=f.queue(),promise=f.flow.startMapGeneration();
  assert.deepEqual(JSON.parse(JSON.stringify(f.calls.at(-1).body)),{revision_id:f.record.revision_id,record_hash:f.record.record_hash});
  start.resolve(result(f.record.id,[job(f.record.id,'Running')],false,true));await promise;
  f.flow.data.accepted_run_id=f.other.id;
  assert.ok(f.flow.mapGenerationGate(f.record));
  assert.equal(f.calls.filter(c=>c.body!==undefined).length,1);
""",
    "completed_job_has_readable_result_identity_and_times": r"""
  const f=setup(), completed=job(f.record.id,'Completed');
  completed.registration={final_cells:33681};completed.started_at='2026-10-21T04:28:55+00:00';completed.finished_at='2026-10-21T04:29:03+00:00';
  await f.lookup(result(f.record.id,[completed],true,true));
  const status=f.find('functional-map-generation-status');
  assert.match(status.children[1].text,/Generated and registered.*33,681 cells/);
  const attempt=f.find('functional-map-generation-attempt');
  assert.equal(attempt.children[0].text,completed.id);
  assert.match(attempt.children[1].text,/Started: 2026-10-21T04:28:55.*Finished: 2026-10-21T04:29:03/);
  assert.equal(f.calls.filter(c=>c.body!==undefined).length,0);
""",
    "explicit_start_preserves_map_and_polls_without_stage_mutation": r"""
  const f=setup(); await f.lookup(result(f.record.id,[],true,true));
  const old=el('iframe',{'data-testid':'functional-map-frame'});f.content.append(old);
  f.flow.renderMapGeneration();assert.match(f.find('functional-map-generate').text,/preserve current/);
  assert.equal(f.calls.length,1);assert.equal(f.calls[0].body,undefined);
  const start=f.queue();const promise=f.flow.startMapGeneration();
  assert.equal(f.find('functional-map-generate').disabled,true);
  assert.equal(f.find('functional-map-generation-refresh').disabled,true);
  await f.flow.startMapGeneration();assert.equal(f.calls.length,2,'Double click must not POST twice');
  assert.equal(f.calls[1].route,`physical-workflow/runs/${f.record.id}/functional-map-generation`);
  assert.deepEqual(JSON.parse(JSON.stringify(f.calls[1].body)),{revision_id:'revision-qa',record_hash:hash('a')});
  start.resolve(result(f.record.id,[job(f.record.id,'Running')],false,true));await promise;
  assert.equal(f.content.children[0],old);assert.equal(timers.size,1);
  const poll=f.queue();const callback=[...timers.values()][0];timers.clear();callback();
  poll.resolve(result(f.record.id,[job(f.record.id,'Completed')],true,true));await tick();
  assert.equal(f.calls.length,3);assert.equal(f.calls[2].body,undefined);
  assert.equal(f.content.children.length,0);assert.equal(f.counters.reloads,1);
  assert.equal(f.counters.envelope,0);assert.equal(f.counters.workflow,0);assert.equal(timers.size,0);
  assert.equal(f.record.execution_status,'Completed');assert.equal(f.record.review_status,'Accepted');
  assert.ok(f.find('functional-map-generate'),'Reloading map cannot erase generation controls');
  const refresh=f.queue();const refreshPromise=f.flow.readMapGeneration();
  refresh.resolve(result(f.record.id,[job(f.record.id,'Completed')],true,true));await refreshPromise;
  assert.equal(f.counters.reloads,1,'Same completion must not repeatedly reload the map');
""",
    "uncertain_start_refreshes_without_automatic_post_or_view_loss": r"""
  const f=setup();await f.lookup(result(f.record.id,[],true,true));
  const old=el('iframe',{'data-testid':'functional-map-frame'});f.content.append(old);
  const start=f.queue(),promise=f.flow.startMapGeneration();start.reject(new Error('Connection interrupted'));await promise;
  assert.match(f.find('functional-map-generation-gate').text,/unknown.*without resending/);
  assert.equal(f.find('functional-map-generate').disabled,true);assert.equal(f.content.children[0],old);assert.equal(timers.size,0);
  await f.flow.startMapGeneration();assert.equal(f.calls.filter(c=>c.body!==undefined).length,1);
  const refresh=f.queue(),reading=f.flow.readMapGeneration();
  refresh.resolve(result(f.record.id,[job(f.record.id,'Running')],false,true));await reading;
  assert.equal(f.calls.at(-1).body,undefined);assert.equal(f.calls.filter(c=>c.body!==undefined).length,1);
  assert.equal(f.flow.mapGeneration.uncertain,false);assert.equal(f.content.children[0],old);
  f.flow.clearMapGeneration();assert.equal(timers.size,0);
""",
    "failed_attempt_retains_view_and_retry_is_new_explicit_request": r"""
  const f=setup();const failed=job(f.record.id,'Failed');failed.error={code:'source_changed',message:'Retained source bytes differ'};
  await f.lookup(result(f.record.id,[failed],true,true));
  const old=el('iframe',{'data-testid':'functional-map-frame'});f.content.append(old);f.flow.renderMapGeneration();
  assert.match(f.find('functional-map-generate').text,/Retry.*new attempt/);
  assert.match(f.find('functional-map-generation-error').text,/source_changed.*Retained source/);
  const retry=f.queue(),promise=f.flow.startMapGeneration();
  retry.resolve(result(f.record.id,[failed,job(f.record.id,'Queued','software-qa-map-2')],false,true));await promise;
  assert.equal(f.content.children[0],old);assert.equal(f.flow.mapGeneration.result.jobs.length,2);
  assert.equal(f.calls.filter(c=>c.body!==undefined).length,1);assert.equal(f.counters.envelope,0);
  f.flow.clearMapGeneration();
""",
    "readonly_dirty_conflict_active_source_and_server_gates": r"""
  const f=setup();await f.lookup();
  for (const [target,key,value] of [[f.project(),'dirty',true],[f.project(),'conflict',true],[f.project(),'busy',true],
    [f.project(),'readOnly',true],[f.project().envelope.workspace_identity,'read_only',true],
    [f.project().envelope,'generation',{jobs:[{execution_status:'Running'}]}],
    [f.record,'review_status','Awaiting Review'],[f.record,'freshness','Stale'],
    [f.record,'validation_status','Failed'],[f.record,'execution_status','Running'],
    [f.record,'record_hash','invalid'],[f.record,'revision_id','other-revision']]) {
    const saved=target[key];target[key]=value;
    assert.ok(f.flow.mapGenerationGate(f.record),key);await f.flow.startMapGeneration();
    target[key]=saved;
  }
  assert.equal(f.calls.length,1,'Local safety gates must never POST');
  f.flow.mapGeneration.result.can_generate=false;f.flow.mapGeneration.result.blocked_reason='Source lineage unavailable';f.flow.renderMapGeneration();
  assert.equal(f.find('functional-map-generate').disabled,true);assert.match(f.find('functional-map-generation-gate').text,/Source lineage unavailable/);
  await f.flow.startMapGeneration();assert.equal(f.calls.length,1);
""",
    "late_responses_cannot_cross_run_project_revision_or_session": r"""
  for (const mode of ['run','design','revision','session','stage','disconnected']) {
    const f=setup(),pending=f.queue();f.flow.renderMapGeneration();const old=f.flow.mapGeneration;
    if(mode==='run')f.flow.runId=f.other.id;
    if(mode==='design')f.setProject({...f.project(),design:{name:'Other fixture'}});
    if(mode==='revision')f.project().envelope.revision.id='new-revision';
    if(mode==='session')f.project().envelope.workspace_identity.session_id='new-session';
    if(mode==='stage')f.project().stage='global_netlist_simulation';
    if(mode==='disconnected')f.host.isConnected=false;
    pending.resolve(result(f.record.id,[job(f.record.id,'Completed')],true,true));await tick();
    assert.equal(old.result,null,mode);assert.equal(f.counters.reloads,0,mode);assert.equal(timers.size,0,mode);
  }
  const f=setup();await f.lookup();const start=f.queue(),starting=f.flow.startMapGeneration();
  f.flow.runId=f.other.id;const newer=f.queue();f.flow.renderMapGeneration();
  start.resolve(result(f.record.id,[job(f.record.id,'Completed')],true,true));await starting;
  assert.equal(f.flow.mapGeneration.runId,f.other.id);assert.equal(f.counters.reloads,0);
  newer.resolve(result(f.other.id));await tick();assert.equal(f.flow.mapGeneration.result.run_id,f.other.id);
""",
    "malformed_or_foreign_history_fails_closed_and_manual_refresh_recovers": r"""
  for(const bad of [result('wrong-run'),{jobs:[],latest_job:null,can_generate:true},
    {...result('software-qa-s11'),latest_job:job('software-qa-s11','Completed')},
    result('software-qa-s11',[job('wrong-run','Completed')]),
    result('software-qa-s11',[job('software-qa-s11','Unrecognised')])]) {
    const f=setup();await f.lookup(bad);
    assert.match(f.find('functional-map-generation-gate').text,/does not match|do not match/);
    assert.equal(f.find('functional-map-generate').disabled,true);assert.equal(f.counters.reloads,0);assert.equal(timers.size,0);
    const refresh=f.queue(),promise=f.flow.readMapGeneration();refresh.resolve(result(f.record.id));await promise;
    assert.equal(f.find('functional-map-generate').disabled,false);assert.equal(f.calls.filter(c=>c.body!==undefined).length,0);
  }
""",
    "leaving_then_returning_restores_saved_job_by_get_only": r"""
  const f=setup();await f.lookup(result(f.record.id,[job(f.record.id,'Running')],false));
  assert.equal(timers.size,1);f.flow.clearMapGeneration();f.flow.layoutView='physical';assert.equal(timers.size,0);
  f.flow.layoutView='functional';const reopened=f.queue();f.flow.renderMapGeneration();
  reopened.resolve(result(f.record.id,[job(f.record.id,'Completed')],true,true));await tick();
  assert.equal(f.calls.length,2);assert.ok(f.calls.every(call=>call.body===undefined));assert.equal(f.counters.reloads,1);
""",
}


class FunctionalMapGenerationClientTests(unittest.TestCase):
    def run_case(self, name):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for isolated GUI software QA.")
        script = FIXTURE + "\n(async()=>{\n" + CASES[name] + r"""
  console.log(JSON.stringify({status:'Passed',software_qa_fixture:true,eda_calls:0,model_calls:0}));
})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});
"""
        completed = subprocess.run([node, "-e", script], cwd=PROJECT,
                                   capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(json.loads(completed.stdout.strip().splitlines()[-1])["status"], "Passed")


for _case in CASES:
    setattr(FunctionalMapGenerationClientTests, "test_" + _case,
            lambda self, name=_case: self.run_case(name))


if __name__ == "__main__":
    unittest.main()

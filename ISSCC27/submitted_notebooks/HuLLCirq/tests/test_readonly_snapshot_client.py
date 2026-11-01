"""Focused saved-snapshot client races; DOM double, no circuit/EDA/model run."""
from pathlib import Path
import shutil
import subprocess
import unittest

PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const all=fs.readFileSync('src/gui/app.js','utf8');
const source=all.slice(all.indexOf('// A preserved system opens'),all.indexOf('function navigateNode('));
const requests=[],adoptions=[],renders=[];
let session='session-a', readonly=true, responder=()=>Promise.resolve({});
const state={design:{id:'design-a'},envelope:{revision:{id:'revision-a'},readonly_snapshot:{compact:true},generation:{jobs:[]}},stage:'local_rtl_generation'};
class DOMDouble {constructor(tag,attrs={}){this.tag=tag;Object.assign(this,attrs);this.children=[];}replaceChildren(...children){this.children=children;}querySelector(){return this.result;}}
const el=(tag,attrs,...children)=>{const node=new DOMDouble(tag,attrs);node.children=children;return node;};
const makeModule=()=>({host:null,record:null,schedules:0,results:0,selected(){return this.record;},selectedJob(){return this.record;},renderResult(){this.results++;},schedule(){this.schedules++;}});
const modules=Object.fromEntries(['generation','localFlow','implementationSpecs','globalGeneration','globalFlow','physicalFlow','drcFlow','lvsFlow','postlayoutFlow'].map(name=>[name,makeModule()]));
const sandbox={...modules,state,readOnly:()=>readonly,workspaceSession:()=>session,el,
  api:route=>{requests.push(route);return responder(route);},
  adopt:envelope=>{adoptions.push(envelope);state.envelope=envelope;},render:()=>renders.push(state.stage)};
vm.createContext(sandbox);vm.runInContext(source+'\nglobalThis.qa={loadSavedStage,loadSavedRecord,mergeSavedSnapshot,stages:savedSnapshotStages,records:savedSnapshotRecords,views:evidenceViews};',sandbox);
const {qa}=sandbox;
const deferred=()=>{let resolve,reject;const promise=new Promise((r,j)=>{resolve=r;reject=j;});return{promise,resolve,reject};};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const envelope=()=>({...state.envelope,design:state.design});
"""


class ReadonlySnapshotClientTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for the isolated client checks.")
        result = subprocess.run([node, "-e", CLIENT + "\n(async()=>{\n" + body +
                                 "\nconsole.log('Passed: isolated saved snapshot client check');\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});"],
                                cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_initialization_requests_no_evidence_and_snapshot_schedules_no_polling(self):
        self.run_client(r"""
assert.equal(requests.length,0);
for(const module of Object.values(modules)) {module.schedule();assert.equal(module.schedules,0);}
readonly=false;modules.physicalFlow.schedule();assert.equal(modules.physicalFlow.schedules,1);
""")

    def test_stage_load_coalesces_and_preserves_previously_opened_records(self):
        self.run_client(r"""
const gate=deferred();responder=()=>gate.promise;
state.envelope.generation.jobs=[{id:'saved-rtl',rtl:'module original; endmodule'}];
qa.loadSavedStage(state.stage);qa.loadSavedStage(state.stage);
assert.deepEqual(requests,['workspace/stage/local_rtl_generation']);
gate.resolve({...envelope(),generation:{jobs:[{id:'saved-rtl',summary_only:true}]}});await tick();
assert.equal(adoptions.length,1);assert.equal(state.envelope.generation.jobs[0].rtl,'module original; endmodule');
qa.loadSavedStage(state.stage);assert.equal(requests.length,1);
""")

    def test_stage_response_ignored_after_navigation_or_session_change(self):
        self.run_client(r"""
for(const change of [()=>state.stage='graph_editor',()=>session='session-b']) {
  state.stage='local_rtl_generation';session='session-a';const gate=deferred();responder=()=>gate.promise;
  qa.loadSavedStage(state.stage);const response=envelope();change();gate.resolve(response);await tick();
  assert.equal(adoptions.length,0);assert.equal(qa.stages.size,0);
}
""")

    def test_wrong_revision_is_reported_without_adopting(self):
        self.run_client(r"""
responder=async()=>({...envelope(),revision:{id:'wrong-revision'}});
qa.loadSavedStage(state.stage);await tick();
assert.equal(adoptions.length,0);assert.equal([...qa.stages.values()][0].status,'error');assert.equal(renders.length,1);
""")

    def test_summary_history_selection_loads_one_full_record(self):
        self.run_client(r"""
const record={id:'history-job',summary_only:true};modules.generation.record=record;
modules.generation.host=new DOMDouble('div');modules.generation.host.result=new DOMDouble('div');
state.envelope.generation.jobs=[record];responder=async()=>({id:record.id,rtl:'original saved RTL'});
modules.generation.renderResult();modules.generation.renderResult();assert.equal(requests.length,1);
assert.equal(modules.generation.results,0);assert.equal(modules.generation.host.result.children[0]['data-testid'],'saved-snapshot-loading');
await tick();assert.equal(requests[0],'generation/jobs/history-job');assert.equal(state.envelope.generation.jobs[0].rtl,'original saved RTL');
""")

    def test_history_response_ignored_after_selection_changes(self):
        self.run_client(r"""
const view=qa.views[0],record={id:'history-a',summary_only:true},gate=deferred();
modules.generation.record=record;state.envelope.generation.jobs=[record];responder=()=>gate.promise;
qa.loadSavedRecord(view,record);modules.generation.record={id:'history-b',summary_only:true};
gate.resolve({id:record.id,rtl:'saved RTL'});await tick();assert.equal(adoptions.length,0);assert.equal(qa.records.size,0);
""")


if __name__ == "__main__":
    unittest.main()

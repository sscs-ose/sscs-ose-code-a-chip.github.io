"""Toolbar Save synchronizes draft-only floorplan views after busy ends; no live API."""
import shutil
import subprocess
import unittest

from test_array_block_client import CLIENT, ROOT


SETUP = r"""
const appSource=fs.readFileSync('src/gui/app.js','utf8');
const saveSource=appSource.slice(appSource.indexOf('async function saveDesign() {'),appSource.indexOf('async function loadDesign() {'));
vm.runInContext('{'+source('physical_workflow.js')+'\nglobalThis.PhysicalWorkflowClass=PhysicalWorkflow;}',sandbox);
function fixture(connected=true){
 const current=design();current.physical_design={version:'mixed-v1'};
 const state={design:current,saved:design(),envelope:{revision:{id:'saved-a'}},busy:false,externalRevision:null};
 const requests=[],notices=[],previewBusy=[],gateBusy=[];let resolve,reject;
 const host=el('div',{isConnected:connected});
 const planner=new c.BlockFloorplan({project:()=>({design:state.design,saved:state.saved,dirty:JSON.stringify(state.design)!==JSON.stringify(state.saved),busy:state.busy}),mutate:()=>assert.fail('View sync must not edit the draft'),save:()=>assert.fail('Planner Save is not used in this toolbar test')});
 planner.render(host);const originalPreview=planner.preview.bind(planner);planner.preview=()=>{previewBusy.push(state.busy);originalPreview();};
 const bodyButton=el('button'),gateLabel=el('p');
 const physical=Object.create(sandbox.PhysicalWorkflowClass.prototype);
 physical.host={isConnected:connected,querySelector:key=>key==='[data-testid="physical-workflow-run"]'?bodyButton:key==='[data-testid="physical-workflow-gate"]'?gateLabel:null};
 physical.busy=false;physical.project=()=>({stage:'layout'});physical.gate=()=>state.busy?'Wait for the current project operation to finish.':'';
 const refresh=physical.refreshDraftActions.bind(physical);physical.refreshDraftActions=()=>{gateBusy.push(state.busy);refresh();};physical.receive=()=>physical.refreshDraftActions();
 const module={receive(){}};
 Object.assign(sandbox,{state,blockFloorplan:planner,physicalFlow:physical,generationBatches:module,generation:module,adoption:module,localFlow:module,implementationSpecs:module,globalGeneration:module,globalFlow:module,drcFlow:module,lvsFlow:module,postlayoutFlow:module,
  flushActiveField(){},readOnly:()=>false,dirty:()=>JSON.stringify(state.design)!==JSON.stringify(state.saved),invalidVerification:()=>false,clone:structuredClone,equal:(a,b)=>JSON.stringify(a)===JSON.stringify(b),syncChrome(){},renderReview(){},autosave(){},toast(){},notify:(...args)=>notices.push(args),
  api:(route,body)=>{requests.push({route,body});return new Promise((yes,no)=>{resolve=yes;reject=no;});}});
 vm.runInContext(saveSource+'\nglobalThis.toolbarSave=saveDesign;',sandbox);
 const status=()=>descendants(planner.status).map(node=>node.text||'').join(' ');
 return {state,planner,host,bodyButton,gateLabel,requests,notices,previewBusy,gateBusy,status,save:()=>sandbox.toolbarSave(),resolve:()=>resolve({design:structuredClone(requests[0].body.design),revision:{id:'saved-b'}}),reject:()=>reject(Error('Software QA save failed'))};
}
"""


class FloorplanToolbarSaveTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated Save-state checks.')
        result = subprocess.run([node, '-e', CLIENT + SETUP + '\n(async()=>{\n' + body +
                                 '\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});'],
                                cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_toolbar_save_updates_saved_planner_badge_and_physical_action_after_busy_false(self):
        self.client(r"""
const f=fixture();assert.match(f.status(),/Unsaved placement draft/);assert.equal(f.planner.saveButton.disabled,false);
const pending=f.save();assert.equal(f.state.busy,true);assert.equal(f.requests.length,1);assert.equal(f.requests[0].route,'save');
f.resolve();await pending;
assert.equal(f.state.busy,false);assert.match(f.status(),/Saved placement mode/);assert.doesNotMatch(f.status(),/Unsaved placement draft/);
assert.equal(f.planner.saveButton.disabled,true);assert.equal(f.bodyButton.disabled,false);assert.match(f.gateLabel.textContent,/Ready/);
assert.deepEqual(f.previewBusy,[false]);assert.deepEqual(f.gateBusy,[true,false]);
assert.equal(f.state.saved.physical_design.version,'mixed-v1');assert.equal(f.requests.length,1);
""")

    def test_newer_draft_remains_unsaved_when_only_the_submitted_revision_was_saved(self):
        self.client(r"""
const f=fixture();const pending=f.save();
f.state.design.physical_design={version:'block-regions-v1',core_um:[10,10,1010,1010],regions:c.tiledRegions(f.state.design,[10,10,1010,1010])};
f.resolve();await pending;
assert.equal(f.state.saved.physical_design.version,'mixed-v1');assert.equal(f.state.design.physical_design.version,'block-regions-v1');
assert.match(f.status(),/Unsaved placement draft/);assert.equal(f.planner.saveButton.disabled,false);assert.equal(f.requests.length,1);
""")

    def test_failed_save_never_marks_the_draft_saved_and_still_updates_busy_state(self):
        self.client(r"""
const f=fixture(),before=JSON.stringify(f.state.saved);const pending=f.save();f.reject();await pending;
assert.equal(f.state.busy,false);assert.equal(JSON.stringify(f.state.saved),before);assert.match(f.status(),/Unsaved placement draft/);
assert.equal(f.planner.saveButton.disabled,false);assert.equal(f.notices.length,1);assert.deepEqual(f.previewBusy,[false]);assert.equal(f.requests.length,1);
""")

    def test_disconnected_planner_is_not_refreshed_or_remounted(self):
        self.client(r"""
const f=fixture(false);const pending=f.save();f.resolve();await pending;
assert.deepEqual(f.previewBusy,[]);assert.equal(f.host.isConnected,false);assert.equal(f.requests.length,1);
assert.equal(f.requests.some(request=>request.route!=='save'),false);
""")


if __name__ == '__main__':
    unittest.main()

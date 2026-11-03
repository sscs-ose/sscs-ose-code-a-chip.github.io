"""Declared client doubles only; not real browser rendering or circuit proof."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class DOMDouble{
 constructor(tag='div',attrs={}){this.tag=tag;this.children=[];this.attributes={};this.style={};this.isConnected=true;Object.assign(this,attrs);if(typeof this.style==='string')this.style={cssText:this.style};}
 append(...nodes){this.children.push(...nodes.flat(Infinity).filter(node=>node!==null&&node!==undefined&&node!==false));}
 replaceChildren(...nodes){this.children=[];this.append(...nodes);}
 setAttribute(key,value){this.attributes[key]=String(value);}
 focus(){this.focused=true;}
 querySelector(selector){return all(this).find(node=>selector.startsWith('#')?node.id===selector.slice(1):selector===`[data-testid="${node['data-testid']}"]`)||null;}
}
const all=node=>[node,...node.children.filter(n=>n instanceof DOMDouble).flatMap(all)];
const el=(tag,attrs={},...children)=>{const node=new DOMDouble(tag,attrs);node.append(...children);return node;};
const source=file=>fs.readFileSync('src/gui/'+file,'utf8').replace(/^import[^\n]*\n/gm,'').replace(/\bexport (?=(function|class|const)\b)/g,'');
let session='software-session-a';
const sandbox={el,svgElement:el,badge:text=>el('span',{text}),workspaceSession:()=>session,console,AbortController,setTimeout,clearTimeout};
vm.createContext(sandbox);vm.runInContext(source('block_placement_view.js')+'\n'+source('physical_workflow.js')+'\nglobalThis.qa={BlockPlacementView,PhysicalWorkflow,validateBlockPlacementProjection};',sandbox);
const plain=value=>JSON.parse(JSON.stringify(value)),H=letter=>letter.repeat(64);
const record=id=>({id,record_hash:H('a'),revision_id:'logical-software-revision',physical_design_revision_id:'physical-software-revision',
 global_job_id:'software-s08',synthesis_run_id:'software-s09',netlist_run_id:'software-s10',source_manifest_sha256:H('b'),runtime_configuration_sha256:H('c'),
 execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',
 runtime_configuration:{profile:{profile_version:'hullcirq-sky130-block-regions-v2'},block_plan_sha256:H('d')},
 artifacts:[{id:'def',sha256:H('1')},{id:'block-placement-proof',sha256:H('2')},{id:'block-ownership',sha256:H('3')}]});
const projection=run=>({version:'block-placement-view-v1',validation_status:'Passed',run_id:run.id,physical_run_id:run.id,record_hash:run.record_hash,
 revision_id:run.revision_id,physical_design_revision_id:run.physical_design_revision_id,profile_version:run.runtime_configuration.profile.profile_version,
 source:{global_job_id:run.global_job_id,synthesis_run_id:run.synthesis_run_id,netlist_run_id:run.netlist_run_id,source_manifest_sha256:run.source_manifest_sha256,plan_sha256:H('d'),final_def_sha256:H('1'),proof_sha256:H('2'),ownership_sha256:H('3')},
 scope:'SOFTWARE QA original mapped cells only',core_um:[10,10,110,110],regions:[{id:'region_a',targets:[{node_id:'pe',instance_index:[0,0]}],rect_um:[16,16,55,104]},{id:'region_b',targets:[{node_id:'pe',instance_index:[0,1]}],rect_um:[65,16,104,104]}],
 cells:[{name:'pe00/a',source_name:'pe00/a',odb_name:'pe00/a',master:'sky130_fd_sc_hd__buf_1',region_id:'region_a',bbox_um:[20,20,21,22]},
 {name:'pe00/b',source_name:'pe00/b',odb_name:'pe00/b',master:'sky130_fd_sc_hd__buf_1',region_id:'region_a',bbox_um:[25,20,26,22]},
 {name:'pe01/a',source_name:'pe01/a',odb_name:'pe01/a',master:'sky130_fd_sc_hd__buf_1',region_id:'region_b',bbox_um:[70,20,71,22]},
 {name:'pe01/b',source_name:'pe01/b',odb_name:'pe01/b',master:'sky130_fd_sc_hd__buf_1',region_id:'region_b',bbox_um:[75,20,76,22]}],
 counts:{original_owned_cells:4,regions:2,unclaimed_final_cells:8,original_mapped_ties:0,final_DEF_components:12},historical:false,status:{freshness:run.freshness},limits:['SOFTWARE QA ONLY']});
const defer=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return{promise,resolve,reject};};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function fixture(){
 let selected=record('software-layout-a'),active=true,project={stage:'layout',envelope:{workspace_identity:{project_id:'software-project-a',system_id:'software-system-a'}}};
 const host=el('div'),calls=[],queue=[];
 const callbacks={project:()=>project,run:()=>selected,active:()=>active,request:(route,body)=>{assert.equal(body,undefined,'Read-only lookup must not POST');calls.push(route);assert.ok(queue.length,'Unexpected read');return queue.shift().promise;}};
 const view=new sandbox.qa.BlockPlacementView(callbacks);
 return{view,host,calls,queue,callbacks,get selected(){return selected;},set selected(value){selected=value;},get project(){return project;},set project(value){project=value;},set active(value){active=value;},lookup:id=>host.querySelector(`[data-testid="${id}"]`),enqueue(){const pending=defer();queue.push(pending);return pending;},async load(){const pending=this.enqueue(),loading=view.activate(host);pending.resolve(projection(selected));await loading;}};
}
"""


class BlockPlacementViewClientTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated placement-view checks.')
        result = subprocess.run([node, '-e', CLIENT + '\n(async()=>{\n' + body +
                                 '\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});'],
                                cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=25)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mount_and_refresh_are_lazy_explicit_first_read_is_cached_without_navigation_reads(self):
        self.client(r"""
const f=fixture();f.view.mount(f.host);f.view.sync();assert.equal(f.calls.length,0);assert.ok(f.lookup('block-placement-retry'));
await f.load();assert.equal(f.calls.length,1);assert.equal(f.calls[0],'physical-workflow/runs/software-layout-a/block-placement');
f.view.sync();f.view.clear();f.view.mount(f.host);await f.view.activate(f.host);assert.equal(f.calls.length,1);
assert.equal(all(f.host).filter(node=>node['data-cell-name']).length,4);
""")

    def test_only_saved_cell_boxes_are_drawn_with_region_targets_and_explicit_scope(self):
        self.client(r"""
const f=fixture();await f.load();const cells=all(f.host).filter(node=>node['data-cell-name']);assert.equal(cells.length,4);
const first=cells.find(node=>node['data-cell-name']==='pe00/a');assert.deepEqual([first.x,first.y,first.width,first.height],[10,88,1,2]);
assert.match(f.lookup('block-placement-scope').text,/Original mapped cells only.*8 unclaimed.*excluded.*not full mask layout.*does not establish currentness/);
const text=all(f.host).map(node=>node.text||node.textContent||'').join(' ');assert.match(text,/region_a.*pe\[0,0\]/);assert.match(text,/SOFTWARE QA ONLY/);
assert.ok(f.lookup('block-placement-scroll'));assert.equal(f.calls.length,1);
""")

    def test_region_checkboxes_all_none_zoom_fit_and_scroll_never_read_or_write(self):
        self.client(r"""
const f=fixture();await f.load();const group=id=>all(f.host).find(node=>node['data-region-id']===id);
f.lookup('block-placement-region-region_a').onchange({target:{checked:false}});assert.equal(group('region_a').attributes.display,'none');assert.equal(group('region_b').display,'inline');
assert.match(f.lookup('block-placement-visible-count').textContent,/2 \/ 4 original mapped cells visible/);
f.lookup('block-placement-hide-all').onclick();assert.match(f.lookup('block-placement-visible-count').textContent,/0 of 2/);
f.lookup('block-placement-show-all').onclick();assert.equal(group('region_a').attributes.display,'inline');assert.match(f.lookup('block-placement-visible-count').textContent,/2 of 2/);
f.lookup('block-placement-zoom').oninput({target:{value:'400'}});assert.equal(f.lookup('block-placement-svg').style.width,'400%');
f.lookup('block-placement-scroll').scrollLeft=45;f.lookup('block-placement-fit').onclick();assert.equal(f.lookup('block-placement-svg').style.width,'100%');assert.equal(f.lookup('block-placement-scroll').scrollLeft,0);
f.lookup('block-placement-region-region_b').onchange({target:{checked:false}});f.view.clear();f.view.mount(f.host);
assert.equal(f.lookup('block-placement-region-region_b').checked,false);assert.equal(f.calls.length,1);
""")

    def test_late_success_or_error_after_run_project_session_or_artifact_change_is_dropped(self):
        self.client(r"""
for(const mode of ['run','project','session','artifact','record'])for(const rejected of [false,true]){
 const f=fixture(),pending=f.enqueue(),loading=f.view.activate(f.host),old=projection(f.selected);
 if(mode==='run')f.selected=record('software-layout-b');
 if(mode==='project')f.project={...f.project,envelope:{workspace_identity:{project_id:'software-project-b',system_id:'software-system-b'}}};
 if(mode==='session')session+='-next';
 if(mode==='artifact')f.selected={...f.selected,artifacts:f.selected.artifacts.map(item=>item.id==='def'?{...item,sha256:H('4')}:item)};
 if(mode==='record')f.selected={...f.selected,record_hash:H('9')};
 f.view.sync();const before=JSON.stringify(f.host.children);
 if(rejected)pending.reject(Error('Old read failed'));else pending.resolve(old);await loading;
 assert.equal(JSON.stringify(f.host.children),before,mode);assert.equal(all(f.host).filter(node=>node['data-cell-name']).length,0);assert.equal(f.calls.length,1);
}
""")

    def test_mismatched_binding_counts_duplicate_or_outside_cells_show_no_geometry(self):
        self.client(r"""
const mutations=[d=>d.run_id='wrong',d=>d.physical_run_id='wrong',d=>d.record_hash=H('9'),d=>d.revision_id='wrong',d=>d.physical_design_revision_id='wrong',d=>d.profile_version='wrong',
 d=>d.source.source_manifest_sha256=H('9'),d=>d.source.plan_sha256=H('9'),d=>d.source.global_job_id='wrong',d=>d.source.synthesis_run_id='wrong',d=>d.source.netlist_run_id='wrong',
 d=>d.source.proof_sha256=H('9'),d=>d.source.ownership_sha256=H('9'),d=>d.source.final_def_sha256=H('9'),d=>d.counts.original_owned_cells=99,d=>d.counts.final_DEF_components=99,d=>d.counts.final_DEF_components=12.1,
 d=>d.cells[0].bbox_um=[0,0,1,2],d=>d.cells[0].bbox_um=[20,20,Infinity,22],d=>d.cells[1].name=d.cells[0].name,d=>d.cells[1].odb_name=d.cells[0].odb_name,d=>d.regions=[]];
for(const mutate of mutations){const f=fixture(),data=projection(f.selected);mutate(data);const pending=f.enqueue(),loading=f.view.activate(f.host);pending.resolve(data);await loading;
 assert.equal(all(f.host).filter(node=>node['data-cell-name']).length,0);assert.match(JSON.stringify(f.lookup('block-placement-status').children),/Failed/);assert.equal(f.view.cache.size,0);
}
""")

    def test_historical_passed_result_is_viewable_without_currentness_or_adoption_changes(self):
        self.client(r"""
const f=fixture();f.selected={...f.selected,freshness:'Stale',review_status:'Awaiting Review'};const before=JSON.stringify(f.selected);
await f.load();assert.equal(all(f.host).filter(node=>node['data-cell-name']).length,4);assert.equal(JSON.stringify(f.selected),before);assert.equal(f.calls.length,1);
""")

    def test_unsupported_and_failed_refresh_never_fall_back_to_previous_cached_geometry(self):
        self.client(r"""
const f=fixture();await f.load();const next=f.enqueue(),refresh=f.lookup('block-placement-retry').onclick();
next.reject(Object.assign(Error('Mixed or failed layouts have no retained block proof.'),{code:'block_placement_view_unavailable'}));await refresh;
assert.match(JSON.stringify(f.lookup('block-placement-status').children),/Not available/);assert.equal(all(f.host).filter(node=>node['data-cell-name']).length,0);assert.equal(f.view.cache.size,0);
f.view.clear();f.view.mount(f.host);assert.equal(f.calls.length,2);assert.equal(all(f.host).filter(node=>node['data-cell-name']).length,0);
""")

    def test_explicit_view_activation_and_selected_run_navigation_keep_read_only_boundaries(self):
        self.client(r"""
const f=fixture(),flow=new sandbox.qa.PhysicalWorkflow({project:()=>f.project,blockPlacementRequest:f.callbacks.request,request:()=>assert.fail('Placement reads must bypass execution-state API')});
f.project={...f.project,stage:'layout'};const tabs=['physical-layout','functional-map','block-floorplan','block-placement'].map(id=>el('button',{id:id+'-tab'}));
const panels=['physical-layout','functional-map','block-floorplan','block-placement'].map(id=>el('div',{id:id+'-panel'}));
const content=el('div',{'data-testid':'block-placement-content'});flow.host=el('div',{},tabs,panels,content);flow.data={runs:[f.selected],reviews:[],latest_run_id:f.selected.id};flow.runId=f.selected.id;
flow.refresh=()=>flow.renderBlockPlacement();flow.refresh();assert.equal(f.calls.length,0);
const pending=f.enqueue();flow.setLayoutView('placement');pending.resolve(projection(f.selected));await tick();
assert.equal(f.calls.length,1);assert.equal(all(content).filter(node=>node['data-cell-name']).length,4);
flow.setLayoutView('physical');flow.setLayoutView('blocks');flow.setLayoutView('placement');await tick();assert.equal(f.calls.length,1);
const other=record('software-layout-b');flow.data.runs.push(other);flow.selectRun(other.id);assert.equal(f.calls.length,1);assert.equal(all(content).filter(node=>node['data-cell-name']).length,0);
assert.equal(flow.layoutView,'placement');assert.equal(flow.runId,other.id);
""")

    def test_default_transport_is_session_guarded_get_and_errors_stay_local(self):
        self.client(r"""
const f=fixture(),calls=[];sandbox.sessionFetch=async(url,options)=>{calls.push({url,options});return {ok:false,status:409,json:async()=>({error:{code:'workspace_session_changed',message:'Saved scope unavailable.'}})};};
const view=new sandbox.qa.BlockPlacementView({project:f.callbacks.project,run:f.callbacks.run,active:f.callbacks.active});
await view.activate(f.host);assert.equal(calls.length,1);assert.equal(calls[0].url,'/api/physical-workflow/runs/software-layout-a/block-placement');
assert.equal(calls[0].options.method,undefined);assert.equal(calls[0].options.body,undefined);assert.equal(calls[0].options.cache,'no-store');assert.equal(calls[0].options.credentials,'same-origin');
assert.match(JSON.stringify(f.lookup('block-placement-status').children),/Failed.*Saved scope unavailable/);
assert.doesNotMatch(JSON.stringify(f.host.children),/draft was preserved|Open Projects|reconnect explicitly/);assert.equal(f.calls.length,0);
for(const mode of ['unavailable','tampered','not-json']){
 const next=fixture();sandbox.sessionFetch=async()=>mode==='unavailable'?{ok:false,status:409,json:async()=>({error:{code:'block_placement_view_unavailable',message:'No saved block proof.'}})}
  :mode==='tampered'?{ok:true,status:200,json:async()=>({...projection(next.selected),run_id:'wrong'})}
  :{ok:true,status:200,json:async()=>{throw Error('Invalid JSON');}};
 const isolated=new sandbox.qa.BlockPlacementView({project:next.callbacks.project,run:next.callbacks.run,active:next.callbacks.active,notify:()=>assert.fail('No global notification'),envelope:()=>assert.fail('No execution envelope change')});
 await isolated.activate(next.host);assert.equal(all(next.host).filter(node=>node['data-cell-name']).length,0);assert.equal(next.calls.length,0);
 assert.match(JSON.stringify(next.lookup('block-placement-status').children),mode==='unavailable'?/Not available/:/Failed/);
}
""")


if __name__ == '__main__':
    unittest.main()

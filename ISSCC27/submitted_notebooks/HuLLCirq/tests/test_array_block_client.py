"""Isolated draft/graph software checks; no browser, API, model, EDA or real project writes."""
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class DOMDouble {
 constructor(tag,attrs={}){this.tag=tag;this.children=[];this.attributes={};this.listeners={};Object.assign(this,attrs);this.classList={add(){},remove(){}};}
 append(...children){this.children.push(...children.flat(Infinity).filter(child=>child!==null&&child!==undefined&&child!==false));}
 replaceChildren(...children){this.children=[];this.append(...children);}
 setAttribute(key,value){this.attributes[key]=String(value);}
 addEventListener(key,value){this.listeners[key]=value;}
 querySelector(){return null;}
}
const el=(tag,attrs={},...children)=>{const node=new DOMDouble(tag,attrs);node.append(...children);return node;};
const source=file=>fs.readFileSync('src/gui/'+file,'utf8').replace(/^import[^\n]*\n/gm,'').replace(/\bexport (?=(function|const|class)\b)/g,'');
const sandbox={el,element:el,svgElement:el,badge:text=>el('span',{text}),field:(label,value,change,options)=>el('field',{label,value,change,...options}),structuredClone,console,
 window:{addEventListener(){}},AbortController};
vm.createContext(sandbox);
vm.runInContext(source('design_instances.js')+'\n'+source('block_floorplan.js')+'\n'+source('external_io.js')+'\n'+source('graph.js')+'\nglobalThis.client={arrayShape,instanceIndices,instanceSuffix,endpointsFor,endpointValue,parseEndpoint,arrayResizeProblem,placementTargets,targetValue,parseTarget,validateFloorplan,tiledRegions,BlockFloorplan,GraphEditor};',sandbox);
const c=sandbox.client,plain=value=>JSON.parse(JSON.stringify(value));
const scalar={id:'scalar',name:'Controller',module_name:'controller',ports:[{id:'out',name:'data',direction:'output',width:32}]};
const pe={id:'pe',name:'PE',module_name:'pe',instance_array:{rows:2,columns:2},ports:[{id:'in',name:'pair_data',direction:'input',width:32},{id:'sum',name:'sum_data',direction:'output',width:64}]};
const design=()=>({nodes:structuredClone([scalar,pe]),edges:[],layout:{nodes:{scalar:{x:10,y:10},pe:{x:300,y:10}},viewport:{x:0,y:0,zoom:1}}});
const descendants=node=>[node,...node.children.filter(child=>child instanceof DOMDouble).flatMap(descendants)];
"""


class ArrayBlockClientTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated client checks.')
        completed = subprocess.run([node, '-e', CLIENT + '\n' + body], cwd=ROOT,
                                   capture_output=True, text=True, encoding='utf-8', timeout=25)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_shared_definition_has_four_indexed_member_endpoints(self):
        self.run_client(r"""
assert.deepEqual(plain(c.instanceIndices(pe)),[[0,0],[0,1],[1,0],[1,1]]);
const d=design(),before=JSON.stringify(d);
const inputs=c.endpointsFor(d,'input');assert.equal(inputs.length,4);
assert.equal(inputs[3][1],'PE[1,1].pair_data · 32 bits');
assert.deepEqual(plain(c.parseEndpoint(inputs[3][0])),{node_id:'pe',port_id:'in',instance_index:[1,1]});
assert.equal(c.endpointsFor(d,'output').length,5);assert.equal(d.nodes.length,2);
assert.equal(JSON.stringify(d),before);
""")

    def test_opaque_endpoint_ids_and_scalar_compatibility(self):
        self.run_client(r"""
for(const index of [null,[0,0],[15,15]]) {
 const value=c.endpointValue('node / [0]','port / , "x"',index),endpoint=c.parseEndpoint(value);
 assert.equal(endpoint.node_id,'node / [0]');assert.equal(endpoint.port_id,'port / , "x"');
 if(index)assert.deepEqual(plain(endpoint.instance_index),index);else assert.equal(Object.hasOwn(endpoint,'instance_index'),false);
}
assert.equal(c.instanceIndices(scalar).length,1);assert.equal(c.instanceIndices(scalar)[0],null);
assert.equal(c.arrayShape({...pe,instance_array:{rows:17,columns:2}}),null);
""")

    def test_shape_changes_never_silently_drop_connections_or_region_targets(self):
        self.run_client(r"""
const d=design();d.edges=[{source:{node_id:'scalar',port_id:'out'},target:{node_id:'pe',port_id:'in',instance_index:[1,1]}}];
assert.match(c.arrayResizeProblem(d,'pe',{rows:1,columns:1}),/reference/);
assert.match(c.arrayResizeProblem(d,'pe',null),/reference/);
assert.match(c.arrayResizeProblem(d,'scalar',{rows:2,columns:2}),/reference/);
assert.equal(c.arrayResizeProblem(d,'pe',{rows:3,columns:2}),'');
assert.match(c.arrayResizeProblem(d,'pe',{rows:1.5,columns:2}),/whole numbers/);
d.edges=[];d.physical_design={regions:[{targets:[{node_id:'pe',instance_index:[1,1]}]}]};
assert.match(c.arrayResizeProblem(d,'pe',{rows:1,columns:2}),/reference/);
""")

    def test_mixed_mode_and_complete_tile_plan_are_pure_and_valid(self):
        self.run_client(r"""
const d=design(),before=JSON.stringify(d);assert.deepEqual(plain(c.validateFloorplan(d)),[]);
const regions=c.tiledRegions(d,[10,10,1010,1010]);assert.equal(regions.length,5);
assert.equal(JSON.stringify(d),before);
d.physical_design={version:'block-regions-v1',core_um:[10,10,1010,1010],regions};
assert.deepEqual(plain(c.validateFloorplan(d)),[]);
assert.equal(new Set(regions.flatMap(region=>region.targets.map(c.targetValue))).size,5);
""")

    def test_missing_duplicate_overlap_outside_and_nonfinite_regions_are_rejected(self):
        self.run_client(r"""
const make=()=>{const d=design();d.physical_design={version:'block-regions-v1',core_um:[10,10,1010,1010],regions:c.tiledRegions(d,[10,10,1010,1010])};return d;};
let d=make();d.physical_design.regions.pop();assert.match(c.validateFloorplan(d).join(' '),/Unassigned/);
d=make();d.physical_design.regions[1].targets.push(d.physical_design.regions[0].targets[0]);assert.match(c.validateFloorplan(d).join(' '),/more than once/);
d=make();d.physical_design.regions[1].rect_um=d.physical_design.regions[0].rect_um;assert.match(c.validateFloorplan(d).join(' '),/overlap/);
d=make();d.physical_design.regions[0].rect_um[0]=-1;assert.match(c.validateFloorplan(d).join(' '),/inside/);
d=make();d.physical_design.core_um[2]=Infinity;assert.match(c.validateFloorplan(d).join(' '),/finite/);
d=make();d.physical_design.regions[0].targets=[{node_id:'pe',instance_index:[3,0]}];assert.match(c.validateFloorplan(d).join(' '),/no longer exists/);
""")

    def test_one_graph_node_exposes_real_indexed_ports_and_connection_endpoint(self):
        self.run_client(r"""
const host=el('div'),connections=[];const graph=new c.GraphEditor(host,{select(){},addEdge:(...args)=>connections.push(args)});
const d=design();graph.update(d,null);
const nodes=descendants(graph.viewport).filter(node=>node['data-node-id']);assert.equal(nodes.length,2);
const ports=descendants(nodes.find(node=>node['data-node-id']==='pe')).filter(node=>node['data-port-id']);assert.equal(ports.length,8);
const output=ports.find(node=>node['data-port-id']==='sum'&&node['data-instance-index']==='[1,1]');
const input=ports.find(node=>node['data-port-id']==='in'&&node['data-instance-index']==='[0,1]');
output.listeners.click({stopPropagation(){}});input.listeners.click({stopPropagation(){}});
assert.deepEqual(plain(connections[0]),[{node_id:'pe',port_id:'sum',instance_index:[1,1]},{node_id:'pe',port_id:'in',instance_index:[0,1]}]);
assert.equal(d.nodes.length,2);assert.equal(d.edges.length,0);
""")

    def test_floorplan_view_and_draft_actions_never_save_until_explicit_save(self):
        self.run_client(r"""
const d=design();let saved=structuredClone(d),saves=0,mutations=0;
const flow=new c.BlockFloorplan({project:()=>({design:d,saved,dirty:JSON.stringify(d)!==JSON.stringify(saved),busy:false,readOnly:false}),
 mutate:change=>{mutations++;change(d);},save:()=>{saves++;saved=structuredClone(d);}});
const host=el('div');flow.render(host);flow.preview();assert.equal(saves,0);assert.equal(mutations,0);assert.equal(Object.hasOwn(d,'physical_design'),false);
const lookup=id=>descendants(host).find(node=>node['data-testid']===id);
lookup('block-placement-mode').change('regions');lookup('apply-placement-mode').onclick();
assert.equal(saves,0);assert.equal(mutations,1);assert.equal(lookup('save-block-floorplan').disabled,true);
lookup('tile-block-regions').onclick();assert.equal(saves,0);assert.equal(lookup('save-block-floorplan').disabled,false);
lookup('save-block-floorplan').onclick().then(()=>{assert.equal(saves,1);assert.equal(lookup('save-block-floorplan').disabled,true);});
""")

    def test_mixed_switch_only_changes_draft_and_saved_plan_is_preserved_until_save(self):
        self.run_client(r"""
const d=design();d.physical_design={version:'block-regions-v1',core_um:[10,10,1010,1010],regions:c.tiledRegions(d,[10,10,1010,1010])};
const saved=structuredClone(d);let saves=0;
const flow=new c.BlockFloorplan({project:()=>({design:d,saved,dirty:JSON.stringify(d)!==JSON.stringify(saved)}),mutate:change=>change(d),save:()=>saves++});
const host=el('div');flow.render(host);
descendants(host).find(node=>node['data-testid']==='block-placement-mode').change('mixed');
descendants(host).find(node=>node['data-testid']==='apply-placement-mode').onclick();
assert.deepEqual(plain(d.physical_design),{version:'mixed-v1'});assert.equal(saved.physical_design.version,'block-regions-v1');assert.equal(saves,0);
""")

    def test_physical_only_draft_blocks_s11_plus_without_invalidating_logical_sources(self):
        self.run_client(r"""
const appSource=fs.readFileSync('src/gui/app.js','utf8');
const dirtySource=appSource.slice(appSource.indexOf('const executionInput ='),appSource.indexOf('const currentStage ='));
sandbox.state={design:design(),saved:design(),stage:'global_rtl_generation'};
sandbox.equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);sandbox.invalidVerification=()=>null;
vm.runInContext(dirtySource+'\nglobalThis.draftChecks={executionInputDirty,physicalDraftDirty,stageInputDirty};',sandbox);
const checks=sandbox.draftChecks,stages=['global_settings','graph_editor','specifications','local_rtl_generation','local_synthesis','local_netlist_simulation','node_implementation_specs','global_rtl_generation','global_synthesis','global_netlist_simulation'];
assert.equal(!!checks.executionInputDirty(),false);
sandbox.state.design.physical_design={version:'block-regions-v1',core_um:[0,0,1000,1000],regions:[]};
assert.equal(!!checks.physicalDraftDirty(),true);assert.equal(!!checks.executionInputDirty(),false);
for(const stage of stages)assert.equal(!!checks.stageInputDirty(stage),false,stage);
for(const stage of ['layout','drc','lvs','post_layout_verification'])assert.equal(!!checks.stageInputDirty(stage),true,stage);
sandbox.state.saved=structuredClone(sandbox.state.design);assert.equal(!!checks.stageInputDirty('layout'),false);
delete sandbox.state.design.physical_design;assert.equal(!!checks.executionInputDirty(),false);assert.equal(!!checks.stageInputDirty('layout'),true);
sandbox.state.design.nodes[0].behavior='New required behavior';
for(const stage of stages)assert.equal(!!checks.stageInputDirty(stage),true,stage);
""")

    def test_export_then_authorized_context_reload_keeps_backup_without_second_prompt(self):
        self.run_client(r"""
(async()=>{
const appSource=fs.readFileSync('src/gui/app.js','utf8'),backups=[],exports=[],reloads=[];let beforeUnload;
DOMDouble.prototype.showModal=function(){this.open=true;};
DOMDouble.prototype.close=function(value){this.returnValue=value;this.open=false;this.listeners.close?.();};
DOMDouble.prototype.remove=function(){this.removed=true;};
sandbox.state={design:{project:{name:'Software QA'},draft:'KEEP'},envelope:{revision:{id:'software-revision'}},busy:false,verificationDrafts:{},authorizedContextNavigation:false};
sandbox.document={body:el('body')};sandbox.activeWorkspace={project_id:'source',system_id:'system'};
sandbox.flushActiveField=()=>{};sandbox.dirty=()=>true;sandbox.readOnly=()=>false;sandbox.invalidVerification=()=>false;
sandbox.adapterDraftDirty=()=>false;
sandbox.autosave=()=>backups.push(structuredClone(sandbox.state.design));
sandbox.downloadJson=(data,name)=>exports.push({data:structuredClone(data),name});
sandbox.generation={profileBusy:false,requestBusy:false,profileDirty:()=>false,profileDraft:null};sandbox.adoption={busy:false,dirty:()=>false,draft:null};
for(const name of ['localFlow','globalGeneration','globalFlow','physicalFlow','drcFlow','lvsFlow','postlayoutFlow'])sandbox[name]={busy:false};
sandbox.notify=()=>{throw Error('Unexpected warning');};sandbox.setWorkspaceSession=value=>{sandbox.session=value;};
sandbox.window={addEventListener:(name,callback)=>{assert.equal(name,'beforeunload');beforeUnload=callback;}};
sandbox.location={reload:()=>{const event={preventDefault(){this.prevented=true;}};beforeUnload(event);reloads.push(event);}};
const preservation=appSource.slice(appSource.indexOf('async function preserveBeforeContextChange() {'),appSource.indexOf('function configureBrowserScope('));
const activation=appSource.slice(appSource.indexOf('  activate: result => {'),appSource.indexOf('  updated: (envelope, action) =>'));
const unload=appSource.match(/window.addEventListener\('beforeunload', event => \{[\s\S]*?\n  \}\);/)[0];
vm.runInContext(preservation+'\n'+unload+'\nglobalThis.leave=preserveBeforeContextChange;globalThis.activation=({'+activation+'}).activate;',sandbox);
const before=JSON.stringify(sandbox.state.design),pending=sandbox.leave();
const button=descendants(sandbox.document.body).find(node=>node['data-testid']==='workspace-export-and-continue');
assert.ok(button);button.onclick();assert.equal(await pending,true);
assert.equal(exports.length,1);assert.equal(exports[0].data.design.draft,'KEEP');assert.equal(sandbox.state.authorizedContextNavigation,false);
sandbox.activation({workspace:{active:{session_id:'new-session'}}});assert.equal(reloads.length,1);assert.equal(reloads[0].prevented,undefined);
assert.equal(sandbox.state.authorizedContextNavigation,false);assert.equal(sandbox.session,'new-session');
assert.ok(backups.length>=3);assert.ok(backups.every(item=>item.draft==='KEEP'));assert.equal(JSON.stringify(sandbox.state.design),before);
const manual={preventDefault(){this.prevented=true;}};beforeUnload(manual);assert.equal(manual.prevented,true);assert.equal(manual.returnValue,'');
})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});
""")

    def test_recommended_tiles_have_visible_inset_gaps_and_preserve_two_by_two_member_geometry(self):
        self.run_client(r"""
const d=design();d.nodes.push(...Array.from({length:6},(_,index)=>({...structuredClone(scalar),id:'other-'+index,name:'Other '+index})));
const before=JSON.stringify(d),core=[10,10,1010,1010],regions=c.tiledRegions(d,core);assert.equal(regions.length,11);
assert.equal(JSON.stringify(d),before);
for(const region of regions){const r=region.rect_um;assert.ok(r[0]>=core[0]+24);assert.ok(r[1]>=core[1]+24);assert.ok(r[2]<=core[2]-24+1e-9);assert.ok(r[3]<=core[3]-24+1e-9);}
for(let i=0;i<regions.length;i++)for(let j=i+1;j<regions.length;j++){
 const a=regions[i].rect_um,b=regions[j].rect_um;
 const xGap=Math.max(b[0]-a[2],a[0]-b[2]),yGap=Math.max(b[1]-a[3],a[1]-b[3]);
 assert.ok(xGap>=24-1e-9||yGap>=24-1e-9,'New default tiles need the explicit 24 um support gap');
}
const rect=(row,column)=>regions.find(region=>region.targets[0].node_id==='pe'&&region.targets[0].instance_index.join(',')===`${row},${column}`).rect_um;
assert.equal(rect(0,0)[1],rect(0,1)[1]);assert.equal(rect(1,0)[1],rect(1,1)[1]);
assert.equal(rect(0,0)[0],rect(1,0)[0]);assert.equal(rect(0,1)[0],rect(1,1)[0]);
assert.ok(rect(0,0)[0]<rect(0,1)[0]);assert.ok(rect(0,0)[1]>rect(1,0)[1],'Array row 0 is at the top');
d.physical_design={version:'block-regions-v1',core_um:core,regions};assert.deepEqual(plain(c.validateFloorplan(d)),[]);
""")

    def test_small_core_tiling_is_blocked_without_overwriting_manual_draft_or_saving(self):
        self.run_client(r"""
const d=design();d.physical_design={version:'block-regions-v1',core_um:[10,10,22,22],regions:[{id:'manual',targets:[{node_id:'scalar'}],rect_um:[10.5,10.5,20.5,20.5]}]};
const before=JSON.stringify(d);let mutations=0,saves=0,warnings=0;
assert.equal(c.tiledRegions(d,d.physical_design.core_um).length,0);
assert.match(c.validateFloorplan(d).join(' '),/greater than 12/);
const flow=new c.BlockFloorplan({project:()=>({design:d,saved:structuredClone(d),dirty:false}),mutate:change=>{mutations++;change(d);},save:()=>saves++,notify:()=>warnings++});
const host=el('div');flow.render(host);flow.preview();
descendants(host).find(node=>node['data-testid']==='tile-block-regions').onclick();
assert.equal(warnings,1);assert.equal(mutations,0);assert.equal(saves,0);assert.equal(JSON.stringify(d),before);
""")

    def test_historical_six_um_eleven_instance_tiles_use_integer_manufacturing_and_opendb_grids(self):
        self.run_client(r"""
const d=design();d.nodes.push(...Array.from({length:6},(_,index)=>({...structuredClone(scalar),id:'other-'+index,name:'Other '+index})));
const core=[10,10,1010,1010],before=JSON.stringify(d),regions=c.tiledRegions(d,core,6);
assert.equal(regions.length,11);assert.equal(JSON.stringify(d),before);
for(const region of regions)for(const coordinate of region.rect_um){
 assert.ok(Math.abs(coordinate*200-Math.round(coordinate*200))<1e-7,'0.005 um manufacturing grid');
 assert.ok(Math.abs(coordinate*1000-Math.round(coordinate*1000))<0.000001,'Existing frozen 1000 DBU guard');
}
const right=Math.max(...regions.map(region=>region.rect_um[2])),top=Math.max(...regions.map(region=>region.rect_um[3]));
assert.ok(core[2]-right>=6-1e-9);assert.ok(core[3]-top>=6-1e-9);
assert.ok(Math.abs((core[3]-6-top)-0.01)<1e-9,'Two leftover ticks stay as unused top margin');
d.physical_design={version:'block-regions-v1',core_um:core,regions};assert.deepEqual(plain(c.validateFloorplan(d)),[]);
assert.equal(new Set(regions.flatMap(region=>region.targets.map(c.targetValue))).size,11);
""")

    def test_non_grid_core_refuses_tiling_without_rounding_or_saving_manual_coordinates(self):
        self.run_client(r"""
const d=design();d.physical_design={version:'block-regions-v1',core_um:[10,10,1010,1010.001],regions:[{id:'manual',targets:[{node_id:'scalar'}],rect_um:[16,16,100,100]}]};
const before=JSON.stringify(d);let changes=0,saves=0;const warnings=[];
assert.equal(c.tiledRegions(d,d.physical_design.core_um).length,0);assert.match(c.validateFloorplan(d).join(' '),/core coordinate.*0\.005/);
const flow=new c.BlockFloorplan({project:()=>({design:d,saved:design(),dirty:true}),mutate:change=>{changes++;change(d);},save:()=>saves++,notify:message=>warnings.push(message)});
const host=el('div');flow.render(host);assert.equal(flow.saveButton.disabled,true);
descendants(host).find(node=>node['data-testid']==='tile-block-regions').onclick();
assert.equal(warnings.length,1);assert.match(warnings[0],/Nothing was rounded/);assert.equal(changes,0);assert.equal(saves,0);assert.equal(JSON.stringify(d),before);
""")

    def test_manual_grid_validation_preserves_values_and_accepts_only_representation_noise(self):
        self.run_client(r"""
const d=design(),core=[10,10,1010,1010];d.physical_design={version:'block-regions-v1',core_um:core,regions:c.tiledRegions(d,core)};
const manual=d.physical_design.regions[0].rect_um;manual[0]+=0.001;const bad=JSON.stringify(d);
assert.match(c.validateFloorplan(d).join(' '),/coordinate.*0\.005/);assert.equal(JSON.stringify(d),bad);
manual[0]-=0.001;manual[0]+=1e-12;const noisy=JSON.stringify(d);
assert.deepEqual(plain(c.validateFloorplan(d)),[]);assert.equal(JSON.stringify(d),noisy);
manual[0]+=1e-8;assert.match(c.validateFloorplan(d).join(' '),/coordinate.*0\.005/);
const noisyCore=[10,10,1010+1e-12,1010];assert.equal(c.tiledRegions(d,noisyCore).length,5);
assert.equal(c.tiledRegions(d,[10,10,1010+1e-8,1010]).length,0);
""")


if __name__ == '__main__':
    unittest.main()

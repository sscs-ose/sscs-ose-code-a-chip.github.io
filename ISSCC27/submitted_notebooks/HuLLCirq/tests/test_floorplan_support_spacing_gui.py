"""Browser-only support helper fixtures; no real browser/API/model/EDA calls."""
import shutil
import subprocess
import unittest

from test_array_block_client import CLIENT, ROOT


SETUP = r"""
const fullDesign=()=>{const d=design();d.nodes.push(...Array.from({length:6},(_,index)=>({...structuredClone(scalar),id:'other-'+index,name:'Other '+index})));return d;};
function fixture(core=[10,10,1010,1010]){
 const d=fullDesign();d.physical_design={version:'block-regions-v1',core_um:core,regions:c.tiledRegions(d,core,6)};
 let saved=structuredClone(d),mutations=0,saves=0;const warnings=[],submitted=[];
 const flow=new c.BlockFloorplan({project:()=>({design:d,saved,dirty:JSON.stringify(d)!==JSON.stringify(saved),busy:false,readOnly:false}),
  mutate:change=>{mutations++;change(d);},save:()=>{saves++;submitted.push(structuredClone(d));saved=structuredClone(d);},notify:message=>warnings.push(message)});
 const host=el('div');flow.render(host);
 return {d,flow,host,warnings,submitted,get saved(){return saved;},get mutations(){return mutations;},get saves(){return saves;},lookup:id=>descendants(host).find(node=>node['data-testid']===id)};
}
"""


class FloorplanSupportSpacingClientTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated support-spacing checks.')
        result = subprocess.run([node, '-e', CLIENT + SETUP + '\n(async()=>{\n' + body +
                                 '\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});'],
                                cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_new_default_and_explicit_spacing_keep_grid_gaps_coverage_and_pe_adjacency(self):
        self.client(r"""
const d=fullDesign(),before=JSON.stringify(d),core=[10,10,1010,1010];
for(const spacing of [24,40]){
 const regions=spacing===24?c.tiledRegions(d,core):c.tiledRegions(d,core,spacing);
 assert.equal(regions.length,11);assert.equal(JSON.stringify(d),before);
 for(const region of regions){const r=region.rect_um;
  assert.ok(r[0]>=core[0]+spacing&&r[1]>=core[1]+spacing);assert.ok(r[2]<=core[2]-spacing&&r[3]<=core[3]-spacing);
  for(const value of r){assert.ok(Math.abs(value*200-Math.round(value*200))<1e-7);assert.ok(Math.abs(value*1000-Math.round(value*1000))<1e-6);}
 }
 for(let i=0;i<regions.length;i++)for(let j=i+1;j<regions.length;j++){const a=regions[i].rect_um,b=regions[j].rect_um;
  assert.ok(Math.max(b[0]-a[2],a[0]-b[2])>=spacing-1e-9||Math.max(b[1]-a[3],a[1]-b[3])>=spacing-1e-9);
 }
 const rect=(r,col)=>regions.find(region=>region.targets[0].node_id==='pe'&&region.targets[0].instance_index.join(',')===`${r},${col}`).rect_um;
 assert.equal(rect(0,0)[0],rect(1,0)[0]);assert.equal(rect(0,1)[0],rect(1,1)[0]);
 assert.equal(rect(0,0)[1],rect(0,1)[1]);assert.equal(rect(1,0)[1],rect(1,1)[1]);
 assert.ok(rect(0,0)[0]<rect(0,1)[0]&&rect(0,0)[1]>rect(1,0)[1]);
 assert.equal(new Set(regions.flatMap(region=>region.targets.map(c.targetValue))).size,11);
 assert.deepEqual(plain(c.validateFloorplan({...d,physical_design:{version:'block-regions-v1',core_um:core,regions}})),[]);
 if(spacing===24){const r=regions[0].rect_um;assert.equal(r[2]-r[0],220);assert.ok(Math.abs(r[3]-r[1]-301.33)<1e-9);}
}
""")

    def test_helper_typing_preview_and_rerender_do_not_edit_or_save_old_six_um_plan(self):
        self.client(r"""
const f=fixture(),before=JSON.stringify(f.d),saved=JSON.stringify(f.saved);
assert.equal(f.lookup('block-tiling-support-spacing').value,'24');assert.match(f.lookup('block-tiling-support-note').textContent,/24 µm.*not part of the saved plan/);
f.lookup('block-tiling-support-spacing').change('40');
assert.match(f.lookup('block-tiling-support-note').textContent,/40 µm/);f.flow.preview();
f.lookup('validate-block-floorplan').onclick();f.flow.render(f.host);
assert.equal(f.lookup('block-tiling-support-spacing').value,'40');assert.equal(f.mutations,0);assert.equal(f.saves,0);
assert.equal(JSON.stringify(f.d),before);assert.equal(JSON.stringify(f.saved),saved);assert.equal(f.flow.saveButton.disabled,true);
assert.deepEqual(plain(c.validateFloorplan(f.d)),[]);
assert.match(descendants(f.flow.status).map(node=>node.text||'').join(' '),/Saved placement mode/);
""")

    def test_invalid_helper_and_tile_leave_every_existing_coordinate_unchanged(self):
        self.client(r"""
const f=fixture(),before=JSON.stringify(f.d);
for(const raw of ['', 'NaN', 'Infinity', '-1', '0', '5.995', '24.001']){
 const count=f.warnings.length;f.lookup('block-tiling-support-spacing').change(raw);f.lookup('tile-block-regions').onclick();
 assert.equal(f.warnings.length,count+1);assert.match(f.warnings.at(-1),/Existing draft regions were not changed/);
 assert.equal(f.mutations,0);assert.equal(f.saves,0);assert.equal(JSON.stringify(f.d),before);assert.equal(f.flow.saveButton.disabled,true);
}
""")

    def test_only_explicit_tile_applies_helper_and_only_explicit_save_persists_rectangles(self):
        self.client(r"""
const f=fixture(),old=JSON.stringify(f.saved);f.lookup('block-tiling-support-spacing').change('24');
assert.equal(f.mutations,0);f.lookup('tile-block-regions').onclick();assert.equal(f.mutations,1);assert.equal(f.saves,0);
assert.equal(JSON.stringify(f.saved),old);assert.notEqual(JSON.stringify(f.d),old);assert.equal(f.flow.saveButton.disabled,false);
assert.deepEqual(plain(f.d.physical_design.regions),plain(c.tiledRegions(f.d,f.d.physical_design.core_um,24)));
assert.match(descendants(f.flow.status).map(node=>node.text||'').join(' '),/Unsaved placement draft/);
await f.lookup('save-block-floorplan').onclick();assert.equal(f.saves,1);assert.equal(f.mutations,1);assert.equal(f.flow.saveButton.disabled,true);
assert.deepEqual(Object.keys(f.submitted[0].physical_design).sort(),['core_um','regions','version']);
assert.equal(JSON.stringify(f.saved).includes('supportSpacing'),false);
""")

    def test_invalid_helper_does_not_block_saving_an_independent_valid_manual_plan(self):
        self.client(r"""
const f=fixture();f.d.physical_design.regions[0].rect_um[0]+=0.005;f.flow.preview();assert.equal(f.flow.saveButton.disabled,false);
const manual=JSON.stringify(f.d);f.lookup('block-tiling-support-spacing').change('24.001');f.flow.preview();
assert.equal(f.flow.saveButton.disabled,false);assert.deepEqual(plain(c.validateFloorplan(f.d)),[]);
await f.lookup('save-block-floorplan').onclick();assert.equal(f.saves,1);assert.equal(f.mutations,0);assert.equal(JSON.stringify(f.saved),manual);
assert.equal(f.lookup('block-tiling-support-spacing').value,'24.001');
""")

    def test_small_core_rejects_new_spacing_without_invalidating_historical_six_um_plan(self):
        self.client(r"""
const f=fixture([10,10,60,60]),before=JSON.stringify(f.d);assert.equal(f.d.physical_design.regions.length,11);
assert.deepEqual(plain(c.validateFloorplan(f.d)),[]);f.lookup('tile-block-regions').onclick();
assert.equal(f.warnings.length,1);assert.match(f.warnings[0],/24 µm inset and 24 µm gaps/);
assert.equal(f.mutations,0);assert.equal(JSON.stringify(f.d),before);
f.lookup('block-tiling-support-spacing').change('6');f.lookup('tile-block-regions').onclick();
assert.equal(f.mutations,1);assert.equal(f.saves,0);assert.deepEqual(plain(c.validateFloorplan(f.d)),[]);
""")

    def test_spacing_grid_requires_finite_number_and_never_rounds_non_grid_input(self):
        self.client(r"""
const d=fullDesign(),core=[10,10,1010,1010],before=JSON.stringify(d);
for(const value of [NaN,Infinity,-1,0,5.995,24.001,24+1e-8,'24',null])assert.equal(c.tiledRegions(d,core,value).length,0);
assert.equal(c.tiledRegions(d,core,24.005).length,11);assert.equal(c.tiledRegions(d,core,24+1e-12).length,11);
assert.equal(JSON.stringify(d),before);
""")

    def test_helper_explicitly_does_not_claim_support_capacity_or_placement_success(self):
        self.client(r"""
const f=fixture();assert.match(f.lookup('block-tiling-support-note').textContent,/not a support-capacity or legalization proof/);
const text=descendants(f.host).map(node=>node.text||node.textContent||'').join(' ');
assert.match(text,/saved 6 µm plans remain unchanged and readable/);assert.match(text,/does not prove space for inserted clock\/support cells or successful placement/);
assert.equal(f.lookup('tile-block-regions').text,'Tile on 0.005 µm grid');assert.equal(f.saves,0);assert.equal(f.mutations,0);
""")


if __name__ == '__main__':
    unittest.main()

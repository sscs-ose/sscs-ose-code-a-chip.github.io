"""Isolated Node source-resolution QA; no browser, HTTP, model or EDA calls."""
from pathlib import Path
import shutil
import subprocess
import unittest

PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const constructors={};
for (const [file,name] of [['physical_workflow','PhysicalWorkflow'],['drc_workflow','DRCWorkflow'],['lvs_workflow','LVSWorkflow'],['postlayout_workflow','PostlayoutWorkflow']]) {
 const context={console,setTimeout:()=>1,clearTimeout(){}}; vm.createContext(context);
 const source=fs.readFileSync(`src/gui/${file}.js`,'utf8').replace(/^import[^\n]*\n/gm,'').replace(`export class ${name}`,`class ${name}`);
 vm.runInContext(source+`\nglobalThis.Constructor=${name};`,context); constructors[file]=context.Constructor;
}
const clone=x=>JSON.parse(JSON.stringify(x));
function fixture() {
 const accepted=(id,extra={})=>({id,revision_id:'original-source',execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',...extra});
 const job=accepted('s08'),synthesis=accepted('s09',{global_job_id:'s08'}),netlist=accepted('s10',{global_job_id:'s08',prior_run_id:'s09'});
 const layout=accepted('s11',{global_job_id:'s08',synthesis_run_id:'s09',netlist_run_id:'s10',artifacts:[{id:'gds',sha256:'gds-hash'},{id:'netlist',sha256:'netlist-hash'}]});
 const drc=accepted('s12',{layout_run_id:'s11',input_gds_sha256:'gds-hash'}),lvs=accepted('s13',{layout_run_id:'s11',drc_run_id:'s12',input_gds_sha256:'gds-hash',input_netlist_sha256:'netlist-hash'});
 const status=(record,extra={})=>({implemented:true,ready:true,tool_ready:true,runs:[record],reviews:[],latest_run_id:record.id,accepted_run_id:record.id,...extra});
 const e={revision:{id:'current-display-request'},workflow:['layout','drc','lvs','post_layout_verification'].map(id=>({id,implemented:true})),
  global_generation:{ready:true,jobs:[job],latest_job_id:job.id},global_workflow:{runs:[synthesis,netlist],stages:[{stage_id:'global_synthesis',accepted_run_id:'s09'},{stage_id:'global_netlist_simulation',accepted_run_id:'s10'}]},
  physical_workflow:status(layout),drc_workflow:status(drc,{layout_run_id:'s11'}),lvs_workflow:status(lvs,{layout_run_id:'s11',drc_run_id:'s12'}),
  postlayout_workflow:{implemented:true,ready:true,tool_ready:true,runs:[],reviews:[],layout_run_id:'s11',drc_run_id:'s12',lvs_run_id:'s13'}};
 const p={envelope:e,stage:'layout',dirty:false,busy:false,conflict:false},calls=[],flows={};
 for(const [key,Constructor] of Object.entries(constructors)) {
  const flow=new Constructor({project:()=>p,request:async(route,body)=>{calls.push({route,body:clone(body)});return e;},envelope(){},toast(){},notify(message){throw new Error(message);}});
  flow.data=e[key];flow.refresh=()=>{};flow.schedule=()=>{};flows[key]=flow;
 }
 return {e,p,calls,flows,job,synthesis,netlist,layout,drc,lvs};
}
"""


class PresentationSourceClientTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for isolated source-resolution QA.")
        result = subprocess.run([node, "-e", CLIENT + "\n(async()=>{\n" + body + "\n})().catch(error=>{console.error(error);process.exit(1);});"],
                                cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_original_source_chain_resolves_and_new_requests_keep_current_saved_revision(self):
        self.run_client(r"""
const f=fixture(),original=clone(f.e);
assert.equal(f.flows.drc_workflow.source().id,'s11');
assert.equal(f.flows.lvs_workflow.sources().drc.id,'s12');
assert.equal(f.flows.postlayout_workflow.sources().lvs.id,'s13');
assert.equal(f.flows.physical_workflow.sources().job.id,'s08');
for(const [key,stage] of [['physical_workflow','layout'],['drc_workflow','drc'],['lvs_workflow','lvs'],['postlayout_workflow','post_layout_verification']]) {
 f.p.stage=stage;assert.equal(f.flows[key].gate(),'');await f.flows[key].start();
 assert.equal(f.calls.at(-1).body.revision_id,'current-display-request');
}
assert.equal(f.calls.length,4);assert.deepEqual(f.e,original);
assert.deepEqual(f.calls.at(-1).body,{stage:'post_layout_verification',layout_run_id:'s11',drc_run_id:'s12',lvs_run_id:'s13',revision_id:'current-display-request'});
""")

    def test_s14_profile_preparation_is_available_when_only_the_tool_profile_is_missing(self):
        self.run_client(r"""
const f=fixture(),flow=f.flows.postlayout_workflow;f.p.stage='post_layout_verification';
Object.assign(flow.data,{ready:false,tool_ready:false,profile_prepare_available:true,layout_run_id:null,drc_run_id:null,lvs_run_id:null});
assert.ok(flow.sources());assert.equal(flow.prepareGate(),'');
await flow.prepare();assert.equal(f.calls.length,1);
assert.equal(f.calls[0].route,'postlayout-workflow/profile');
assert.equal(f.calls[0].body.revision_id,'current-display-request');
assert.ok(flow.gate());
for(const mutate of [()=>flow.data.profile_prepare_available=false,()=>flow.data.tool_ready=true,()=>flow.data.drc_run_id='s12']) {
 Object.assign(flow.data,{ready:false,tool_ready:false,profile_prepare_available:true,layout_run_id:null,drc_run_id:null,lvs_run_id:null});
 mutate();assert.equal(flow.sources(),null);assert.ok(flow.prepareGate());
}
""")

    def test_missing_partial_or_wrong_backend_source_ids_fail_closed(self):
        self.run_client(r"""
for(const [key,source] of [['drc_workflow','source'],['lvs_workflow','sources'],['postlayout_workflow','sources']]) {
 for(const value of [null,'other-source',undefined]) {
  const f=fixture(),flow=f.flows[key];flow.data.layout_run_id=value;
  assert.equal(flow[source](),null,key+' '+value);await flow.start();assert.equal(f.calls.length,0);
 }
 const f=fixture(),flow=f.flows[key];
 delete flow.data.layout_run_id;assert.equal(flow[source](),null,'Cross-revision cannot use missing source identity');
}
""")

    def test_mutual_revision_lineage_artifact_and_current_adoption_guards_remain(self):
        self.run_client(r"""
const mutations=[f=>f.drc.revision_id='mixed-original',f=>f.drc.layout_run_id='other-layout',f=>f.drc.input_gds_sha256='wrong-hash',
 f=>f.layout.freshness='Stale',f=>f.drc.review_status='Changes Requested',f=>f.e.physical_workflow.latest_run_id='new-layout'];
for(const mutate of mutations) {const f=fixture();mutate(f);assert.equal(f.flows.lvs_workflow.sources(),null);assert.equal(f.flows.postlayout_workflow.sources(),null);}
for(const mutate of [f=>f.lvs.revision_id='mixed-original',f=>f.lvs.drc_run_id='wrong-drc',f=>f.lvs.input_netlist_sha256='wrong-hash',f=>f.e.lvs_workflow.accepted_run_id=null]) {
 const f=fixture();mutate(f);assert.equal(f.flows.postlayout_workflow.sources(),null);
}
for(const mutate of [f=>f.synthesis.revision_id='mixed-original',f=>f.netlist.prior_run_id='wrong-s09',f=>f.e.global_generation.ready=false,f=>f.e.global_generation.latest_job_id='new-s08']) {
 const f=fixture();mutate(f);assert.equal(f.flows.physical_workflow.sources(),null);
}
""")

    def test_legacy_envelopes_are_supported_only_for_the_exact_current_revision(self):
        self.run_client(r"""
const f=fixture();f.e.revision.id='original-source';
for(const [key,method] of [['drc_workflow','source'],['lvs_workflow','sources'],['postlayout_workflow','sources']]) {
 for(const field of ['layout_run_id','drc_run_id','lvs_run_id']) delete f.flows[key].data[field];
 assert.ok(f.flows[key][method]());
}
f.e.revision.id='other-unverified-revision';
assert.equal(f.flows.drc_workflow.source(),null);assert.equal(f.flows.lvs_workflow.sources(),null);assert.equal(f.flows.postlayout_workflow.sources(),null);
""")

    def test_repair_controls_accept_only_the_exact_backend_current_original_source_chain(self):
        self.run_client(r"""
const f=fixture(),physical=f.flows.physical_workflow,post=f.flows.postlayout_workflow;
const failed={id:'failed-layout',revision_id:'original-source',global_job_id:'s08',synthesis_run_id:'s09',netlist_run_id:'s10',
 execution_status:'Completed',validation_status:'Failed',review_status:'Awaiting Review',freshness:'Current',error:null,evidence_kind:'trusted_fixed_tool_execution',
 runtime_configuration:{profile:{profile_version:'hullcirq-sky130-route-repair-npu2v1'}},diagnostics:[{code:'physical_checks_failed',severity:'error'}],
 checks:{origin:'trusted_fixed_tool_adapter',validation_status:'Failed',executed:true,exit_code:0,cleanup_unresolved:false,technology_mapping_executed:false,upstream_technology_mapping_reused:true,
 implementation_kind:'resumed_pre_CTS_route_repair',commands:[0,1].map(()=>({executed:true,status:'Completed',exit_code:0})),
 checks:Object.fromEntries(['configuration','source_identity','routing','timing','electrical'].map(key=>[key,{validation_status:key==='electrical'?'Failed':'Passed'}]))}};
physical.data.latest_run_id=failed.id;assert.equal(physical.fixedRepairEligible(failed),true);
failed.netlist_run_id='wrong-source';assert.equal(physical.fixedRepairEligible(failed),false);failed.netlist_run_id='s10';
const final={id:'failed-s14',revision_id:'original-source',layout_run_id:'s11',drc_run_id:'s12',lvs_run_id:'s13',
 execution_status:'Completed',validation_status:'Failed',freshness:'Current',error:null,evidence_kind:'trusted_fixed_postlayout_execution',verification_supported:true,execution_scope:'post_route_functional_plus_sta',
 checks:{origin:'trusted_fixed_postlayout_adapter',execution_scope:'post_route_functional_plus_sta',status:'Completed',validation_status:'Failed',executed:true,exit_code:0,
 commands:Array.from({length:11},()=>({executed:true,status:'Completed',exit_code:0})),checks:Object.fromEntries(['source_identity','configuration','functional','parasitics','constraints','setup_hold','electrical'].map(key=>[key,{validation_status:key==='electrical'?'Failed':'Passed'}]))}};
// Physical failure selection above is separate from S14's adopted S11 source.
physical.data.latest_run_id='s11';post.data.latest_run_id=final.id;
assert.equal(post.physicalRepairEligible(final),true);final.drc_run_id='wrong-source';assert.equal(post.physicalRepairEligible(final),false);
assert.equal(f.calls.length,0);
""")


if __name__ == "__main__":
    unittest.main()

"""S07 exact local source guards, isolated DOM scenarios without circuit execution."""
from pathlib import Path
import shutil
import subprocess
import unittest

from test_generation_recovery_gui import CLIENT

PROJECT = Path(__file__).resolve().parents[1]
SETUP = r"""
const implementationSource=fs.readFileSync('src/gui/implementation_specs.js','utf8').replace(/^import[^\n]+\n/gm,'').replace('export class NodeImplementationSpecs','class NodeImplementationSpecs');
vm.runInContext('{'+implementationSource+'\nglobalThis.NodeImplementationSpecs=NodeImplementationSpecs;}',sandbox);
project.stage='node_implementation_specs';project.design.project={name:'Isolated S07 source QA'};
project.envelope.workflow.push({id:'local_synthesis',implemented:true},{id:'local_netlist_simulation',implemented:true},{id:'node_implementation_specs',implemented:true});
project.envelope.global_generation={ready:true};
const candidate={...failed,id:'candidate-current',node_id:'node-a',execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',rtl_sha256:'current-rtl',input_hash:'current-input'};
project.envelope.generation={jobs:[candidate],nodes:[{node_id:'node-a',latest_job_id:candidate.id,accepted_job_id:candidate.id}]};
const synthesis={id:'s05-current',node_id:'node-a',stage_id:'local_synthesis',candidate_id:candidate.id,execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',netlist:'netlist',netlist_sha256:'net-hash',rtl_sha256:candidate.rtl_sha256,input_hash:candidate.input_hash,revision_id:candidate.revision_id,requested_revision_id:project.envelope.revision.id};
const simulation={...synthesis,id:'s06-current',stage_id:'local_netlist_simulation',prior_run_id:synthesis.id};
project.envelope.workflow_runs=[synthesis,simulation];
const spec={id:'s07-current',node_id:'node-a',source_run_id:simulation.id,candidate_id:candidate.id,execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',requested_revision_id:project.envelope.revision.id};
const view=new sandbox.NodeImplementationSpecs({project:()=>project,request:(...args)=>{requests.push(args);return responder(...args);},navigate:(...args)=>notices.push(args)});
view.nodeId='node-a';view.specs=[spec];view.nodes=[{node_id:'node-a',source_run_id:simulation.id,latest_spec_id:spec.id,accepted_spec_id:spec.id,ready:true}];
project.envelope.implementation_spec_nodes=view.nodes;
const reviewHost=new DOMDouble('div');
const reviewButton=id=>reviewHost.querySelector(`[data-testid="${id}"]`);
"""


class S07CurrentSourceGuiTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node required for isolated DOM source guards.")
        result = subprocess.run([node, "-e", CLIENT + SETUP + body], cwd=PROJECT,
                                capture_output=True, text=True, encoding="utf8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_exact_current_chain_allows_extraction_and_continuation(self):
        self.client(r"""
assert.equal(view.source().id,simulation.id);assert.equal(view.gate(),'');assert.equal(view.currentRun().id,spec.id);
view.renderReview(reviewHost);assert.equal(reviewButton('implementation-continue').disabled,false);
assert.equal(requests.length,0);
""")

    def test_legacy_current_old_candidate_cannot_supply_s07_source(self):
        self.client(r"""
const before=JSON.stringify(project.envelope.workflow_runs);candidate.id='new-candidate';project.envelope.generation.nodes[0].latest_job_id=candidate.id;project.envelope.generation.nodes[0].accepted_job_id=candidate.id;
assert.equal(view.source(),undefined);assert.equal(view.selected(),undefined);assert.match(view.gate(),/current.*Local Netlist Simulation/);
view.specId=spec.id;view.renderReview(reviewHost);assert.equal(view.selected().id,spec.id);
assert.equal(reviewButton('implementation-continue').disabled,true);assert.equal(reviewButton('implementation-accept').disabled,true);
assert.equal(JSON.stringify(project.envelope.workflow_runs),before);assert.equal(requests.length,0);
""")

    def test_later_s06_failure_does_not_fall_back_to_older_pass(self):
        self.client(r"""
project.envelope.workflow_runs.push({...simulation,id:'s06-later',validation_status:'Failed',review_status:'Awaiting Review'});
assert.equal(view.source(),undefined);assert.equal(view.runCurrent(spec),false);assert.match(view.gate(),/current.*accepted/);
assert.equal(requests.length,0);
""")

    def test_new_s05_netlist_requires_its_own_s06_result(self):
        self.client(r"""
const next={...synthesis,id:'s05-new',netlist_sha256:'new-net-hash'};project.envelope.workflow_runs.push(next);
assert.equal(view.source(),undefined);assert.equal(view.runCurrent(spec),false);
project.envelope.workflow_runs.push({...simulation,id:'s06-new',prior_run_id:next.id,netlist_sha256:next.netlist_sha256});
assert.equal(view.source().id,'s06-new');assert.equal(view.runCurrent(spec),false);
const fresh={...spec,id:'s07-new',source_run_id:'s06-new'};view.specs.push(fresh);Object.assign(view.nodes[0],{latest_spec_id:fresh.id,accepted_spec_id:fresh.id,source_run_id:'s06-new'});assert.equal(view.currentRun().id,fresh.id);
assert.equal(requests.length,0);
""")

    def test_new_presentation_revision_does_not_invalidate_unchanged_current_sources(self):
        self.client(r"""
project.envelope.revision.id='new-position-only-revision';
assert.equal(view.source().id,simulation.id);assert.equal(view.gate(),'');assert.equal(view.runCurrent(spec),true);
assert.equal(requests.length,0);
""")

    def test_source_hash_or_revision_mismatch_blocks_extraction(self):
        self.client(r"""
for(const field of ['rtl_sha256','input_hash','revision_id']){
 const original=simulation[field];simulation[field]='different-source';assert.equal(view.source(),undefined,field);simulation[field]=original;
}
simulation.netlist_sha256='different-netlist';assert.equal(view.source(),undefined);assert.equal(requests.length,0);
""")


if __name__ == "__main__":
    unittest.main()

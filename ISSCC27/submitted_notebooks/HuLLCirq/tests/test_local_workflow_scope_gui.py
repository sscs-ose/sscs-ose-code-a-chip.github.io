"""Pure client gate checks; synthetic software data, no browser or EDA execution."""
from pathlib import Path
import shutil
import subprocess
import unittest

PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('src/gui/workflow.js','utf8').replace(/^import .*;\s*$/gm,'').replace('export class LocalWorkflow','class LocalWorkflow');
const sandbox={};vm.createContext(sandbox);vm.runInContext('{'+fs.readFileSync('src/gui/availability.js','utf8').replace(/export /g,'')+'\nglobalThis.availabilityReason=availabilityReason;}',sandbox);vm.runInContext(source+'\nglobalThis.LocalWorkflow=LocalWorkflow;',sandbox);
vm.runInContext('{'+fs.readFileSync('src/gui/flow_guidance.js','utf8').replace(/^import[^\n]+\n/gm,'').replace(/export /g,'')+'\nglobalThis.resolve=resolveStageGuidance;}',sandbox);
const candidate={id:'candidate',node_id:'node',execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',checks:{interface:{validation_status:'Passed'}},verification_plan:null};
const readiness={status:'implementation_required',available:false,message:'The saved specification has no implemented behavioral checker.',stage_id:'local_netlist_simulation'};
const project={stage:'local_synthesis',dirty:false,conflict:false,envelope:{workflow:[{id:'local_synthesis',implemented:true},{id:'local_netlist_simulation',implemented:true}],generation:{jobs:[candidate],nodes:[{node_id:'node',latest_job_id:'candidate',accepted_job_id:'candidate',behavioral_verification:readiness}]}}};
const flow=new sandbox.LocalWorkflow({project:()=>project});flow.nodeId='node';
const synthesis={id:'synthesis',stage_id:'local_synthesis',node_id:'node',candidate_id:'candidate',execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',netlist:'original netlist'};
"""


class LocalWorkflowScopeGuiTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for pure client checks.")
        result = subprocess.run([node, "-e", CLIENT + body], cwd=PROJECT, capture_output=True,
                                text=True, encoding="utf-8", timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_s05_interface_candidate_needs_no_behavior_checker_or_plan(self):
        self.client("assert.equal(flow.gate(),'');assert.equal(flow.candidate().verification_plan,null);")

    def test_s06_first_requires_exact_adopted_s05_then_reports_checker_limit(self):
        self.client("project.stage='local_netlist_simulation';assert.match(flow.gate(),/same candidate must pass/);assert.equal(flow.blocker().kind,'synthesis_required');flow.runs=[synthesis];assert.equal(flow.blocker().kind,'implementation_required');assert.equal(flow.blocker().priorRunId,synthesis.id);assert.equal(flow.blocker().candidateId,candidate.id);assert.match(flow.gate(),/S05 synthesis is accepted.*S06 needs a behavioral checker/);")

    def test_s06_ready_checker_does_not_need_a_plan_on_s04_candidate(self):
        self.client("project.stage='local_netlist_simulation';flow.runs=[synthesis];readiness.available=true;readiness.status='ready';assert.equal(flow.gate(),'');")

    def test_a_synthesis_of_another_candidate_does_not_unlock_s06(self):
        self.client("project.stage='local_netlist_simulation';flow.runs=[{...synthesis,candidate_id:'other-candidate'}];assert.match(flow.gate(),/same candidate must pass/);")

    def test_only_current_accepted_successful_synthesis_precedes_checker_blocker(self):
        self.client(r"""
project.stage='local_netlist_simulation';
for(const changed of [{node_id:'other-node'},{candidate_id:'old-candidate'},{execution_status:'Running'},{validation_status:'Failed'},{review_status:'Awaiting Review'},{freshness:'Stale'}]) {
 flow.runs=[{...synthesis,...changed}];
 const blocker=flow.blocker();
 assert.equal(blocker.kind,changed.execution_status==='Running'?'active_operation':'synthesis_required');
 assert.ok(flow.gate());
}
flow.runs=[synthesis];assert.equal(flow.blocker().kind,'implementation_required');
""")

    def test_saved_s05_and_checker_blocker_feed_real_guidance_without_resynthesis(self):
        self.client(r"""
project.stage='local_netlist_simulation';
const context=()=>({stage:project.stage,implemented:true,nodeId:flow.nodeId,nodeName:'Output FIFO',prerequisite:'local_synthesis',gate:flow.gate(),blocker:flow.blocker(),runLabel:'Run netlist verification',runTestId:'workflow-run'});
const missing=sandbox.resolve(context());assert.equal(missing.primary.stage,'local_synthesis');
flow.runs=[synthesis];
readiness.message='Checker build support is absent.'; // No regex keywords: classification must be structural.
const blocked=sandbox.resolve(context());
assert.equal(blocked.title,'Not implemented · S06 behavioral checker');
assert.equal(blocked.primary.stage,'specifications');assert.equal(blocked.primary.nodeId,'node');
assert.equal(blocked.primary.label,'Inspect saved requirements');
assert.match(blocked.detail,/S05 synthesis is accepted/);assert.notEqual(blocked.primary.kind,'control');
assert.equal(blocked.secondary.label,'Inspect accepted S05 netlist');
assert.doesNotMatch(blocked.summary,/Regenerat|re-enter|must pass/);
readiness.available=true;readiness.status='ready';
assert.equal(flow.blocker(),null);assert.equal(sandbox.resolve(context()).primary.testId,'workflow-run');
""")

    def test_newest_matching_s05_failure_or_missing_netlist_cannot_fall_back_to_old_pass(self):
        self.client(r"""
project.stage='local_netlist_simulation';
for(const changed of [{execution_status:'Failed',validation_status:'Failed',review_status:'Awaiting Review'},{review_status:'Awaiting Review'},{freshness:'Stale'},{netlist:''},{netlist:null},{netlist:undefined}]) {
 flow.runs=[synthesis,{...synthesis,id:'newer-synthesis',...changed}];
 assert.equal(flow.prior(),undefined);
 assert.equal(flow.blocker().kind,'synthesis_required');
 const guide=sandbox.resolve({stage:project.stage,implemented:true,nodeId:flow.nodeId,blocker:flow.blocker(),gate:flow.gate()});
 assert.equal(guide.primary.stage,'local_synthesis');assert.doesNotMatch(guide.summary,/synthesis is accepted/);
}
""")

    def test_newest_eligible_s05_is_used_and_unrelated_candidates_do_not_shadow_it(self):
        self.client(r"""
project.stage='local_netlist_simulation';
flow.runs=[synthesis,{...synthesis,id:'newer-synthesis',netlist:'newer netlist'},{...synthesis,id:'unrelated-synthesis',candidate_id:'other-candidate',validation_status:'Failed'}];
assert.equal(flow.prior().id,'newer-synthesis');
assert.equal(flow.blocker().kind,'implementation_required');assert.equal(flow.blocker().priorRunId,'newer-synthesis');
""")

    def test_missing_candidate_and_readiness_causes_are_classified_without_widening_s05(self):
        self.client(r"""
project.stage='local_netlist_simulation';flow.runs=[synthesis];
for(const status of ['input_required','configuration_required','unexpected_future_status']) {
 readiness.status=status;assert.equal(flow.blocker().kind,status==='unexpected_future_status'?'verification_unavailable':status);
 assert.ok(flow.gate());
 project.stage='local_synthesis';assert.equal(flow.blocker(),null);assert.equal(flow.gate(),'');project.stage='local_netlist_simulation';
}
candidate.review_status='Awaiting Review';assert.equal(flow.blocker().kind,'candidate_required');
""")

    def test_checker_guidance_does_not_bypass_the_existing_execution_guard(self):
        self.client(r"""
project.stage='local_netlist_simulation';flow.runs=[synthesis];
let calls=0;flow.callbacks.request=()=>{calls++;throw Error('Blocked operation was sent');};
(async()=>{await flow.start();assert.equal(calls,0);assert.equal(flow.busy,false);})();
""")


if __name__ == '__main__':
    unittest.main()

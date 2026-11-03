"""Actual app presentation in an isolated DOM; no API/model/tool execution."""
import shutil
import subprocess
import unittest

from test_instant_execution_gui import HARNESS, PROJECT


class FirstRunGuidanceGuiTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required")
        script = HARNESS + r"""
(async()=>{const qa=await initialize();
qa.state.envelope.design=structuredClone(qa.state.design);
qa.state.envelope.workflow=qa.STAGES.map(([id],index)=>({id,implemented:true,
 execution_status:index<3?'Completed':'Not Run',validation_status:index<3?'Passed':'Not Checked',
 review_status:index<3?'Accepted':'Awaiting Review',freshness:'Current',
 ...(index<3?{latest_run_id:`first-${id}`}:{})}));
qa.receiveExecution();
""" + body + r"""
assert.equal(requests.length,0);
})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});
"""
        result = subprocess.run([node, "--experimental-vm-modules", "-e", script], cwd=PROJECT,
                                capture_output=True, text=True, encoding="utf-8", timeout=25)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_first_upstream_execution_does_not_invent_downstream_history(self):
        self.run_client(r"""
const token=qa.executionState.begin({kind:'execute',stageId:'specifications'});
qa.executionState.success(token,{runs:[{id:'first-specification-check',stage_id:'specifications',
 execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current'}]});
const before=JSON.stringify(qa.executionState.entries);
for(const [stage] of qa.STAGES.slice(3)){
 qa.state.stage=stage;
 const context=qa.guidanceContext();assert.equal(context.hasSavedEvidence,false,stage);
 const guide=qa.resolveStageGuidance(context);
 assert.doesNotMatch(guide.title+' '+guide.summary,/restarted|earlier results|earlier evidence|run this stage again/i,stage);
 qa.renderStageStatus();
 assert.doesNotMatch(elements.get('stage-status').textContent,/restarted|earlier saved evidence|previous evidence/i,stage);
 assert.equal(qa.stageVisual(stage).label,'Not run');
 assert.equal(qa.executionState.overlay(stage).invalidated,true,'Display fix must not change the invalidation guard');
}
assert.equal(JSON.stringify(qa.executionState.entries),before);
""")

    def test_existing_saved_stage_keeps_restart_and_earlier_evidence_explanation(self):
        self.run_client(r"""
const stage=qa.state.envelope.workflow.find(item=>item.id==='drc');
Object.assign(stage,{latest_run_id:'saved-drc',execution_status:'Completed',validation_status:'Passed',review_status:'Accepted'});
qa.receiveExecution();
const token=qa.executionState.begin({kind:'execute',stageId:'local_synthesis'});
qa.executionState.success(token,{workflow_runs:[{id:'new-synthesis',stage_id:'local_synthesis',
 execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current'}]});
qa.drcFlow.data.implemented=true;
qa.state.stage='drc';const context=qa.guidanceContext();assert.equal(context.hasSavedEvidence,true);
const guide=qa.resolveStageGuidance(context);assert.equal(guide.decisionId,'execution_invalidated');
assert.match(guide.summary,/earlier stage was restarted/i);
qa.renderStageStatus();assert.match(elements.get('stage-status').textContent,/Earlier saved evidence/);
assert.equal(qa.stageVisual('drc').label,'Not run');
""")

    def test_empty_stage_waits_for_running_upstream_without_claiming_restart(self):
        self.run_client(r"""
qa.executionState.begin({kind:'execute',stageId:'local_rtl_generation'});
qa.state.stage='drc';const context=qa.guidanceContext();
assert.equal(context.hasSavedEvidence,false);
const guide=qa.resolveStageGuidance(context);
assert.equal(guide.primary.kind,'navigate');assert.equal(guide.primary.stage,'local_rtl_generation');
assert.match(guide.summary,/has not run yet/);assert.doesNotMatch(guide.summary,/restarted|history/);
qa.renderStageStatus();assert.doesNotMatch(elements.get('stage-status').textContent,/restarted|earlier saved evidence/i);
assert.equal(qa.stageVisual('drc').label,'Not run');
""")


if __name__ == "__main__":
    unittest.main()

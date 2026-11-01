"""Actual app DOM cancellation labels in isolation; no live APIs or native tools."""
import shutil
import subprocess
import unittest
from test_instant_execution_gui import HARNESS, PROJECT

SETUP=r"""
(async()=>{const qa=await initialize();
qa.state.envelope.design=structuredClone(qa.state.design);
qa.state.envelope.workflow=qa.STAGES.map(([id])=>({id,implemented:true,execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current'}));
qa.state.envelope.global_generation={ready:true,jobs:[]};
qa.state.stage='layout';qa.executionState.overlay=()=>null;
function install(fields={}){
 const record={id:'software-qa-cancelled-layout',stage_id:'layout',execution_status:'Cancelled',validation_status:'Not Checked',review_status:'Awaiting Review',freshness:'Current',diagnostics:[],checks:{validation_status:'Not Checked',cleanup_unresolved:false,diagnostics:[{code:'physical_cancelled',severity:'info'}]},...fields};
 Object.assign(qa.state.envelope.workflow.find(item=>item.id==='layout'),record,{id:'layout'});
 qa.state.envelope.physical_workflow={implemented:true,ready:true,tool_ready:true,runs:[record]};
 qa.physicalFlow.data=qa.state.envelope.physical_workflow;
 qa.physicalFlow.selected=()=>record;qa.physicalFlow.currentRun=()=>record;
 qa.physicalFlow.runCurrent=()=>true;qa.physicalFlow.gate=()=>'';qa.physicalFlow.pollError=null;
 qa.executionState.overlay=()=>null;
 return record;
}
"""

class CancelledGuidanceGuiTests(unittest.TestCase):
    def run_client(self,body):
        node=shutil.which('node')
        if not node:self.skipTest('Node required for isolated DOM checks.')
        script=HARNESS+SETUP+body+r"""
assert.equal(requests.length,0);
})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});
"""
        result=subprocess.run([node,'--experimental-vm-modules','-e',script],cwd=PROJECT,
            capture_output=True,text=True,encoding='utf-8',timeout=25)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_clean_cancelled_header_changes_text_only_and_keeps_state_and_record(self):
        self.run_client(r"""
const record=install();const before=JSON.stringify(qa.state.envelope);
const epochs=JSON.stringify(qa.executionState.entries);
qa.renderStageStatus();
assert.equal(qa.stageVisual('layout').label,'Failed');
assert.equal(elements.get('stage-status').getAttribute('data-status'),'Failed');
assert.match(elements.get('stage-status').querySelector('[data-testid="stage-execution-status"]').textContent,/^Cancelled/);
assert.doesNotMatch(elements.get('stage-status').querySelector('[data-testid="stage-execution-status"]').textContent,/failed checks|repair/i);
assert.equal(qa.resolveStageGuidance(qa.guidanceContext()).decisionId,'cancelled');
assert.equal(JSON.stringify(qa.state.envelope),before);assert.equal(JSON.stringify(qa.executionState.entries),epochs);
assert.equal(record.execution_status,'Cancelled');assert.equal(record.validation_status,'Not Checked');
""")

    def test_true_errors_cleanup_history_sources_and_reconnect_never_gain_clean_cancel_label(self):
        self.run_client(r"""
const cases=[
 {execution_status:'Failed',error:{code:'tool_failed',message:'Real tool failure'}},
 {execution_status:'Completed',validation_status:'Unsupported'},
 {validation_status:'Passed'},
 {checks:{validation_status:'Not Checked',cleanup_unresolved:true}},
 {error:{code:'source_changed',message:'Real source mismatch'}},
 {diagnostics:[{severity:'error',message:'Real proof mismatch'}]},
 {checks:{validation_status:'Failed',diagnostics:[]}},
];
for(const fields of cases){install(fields);qa.renderStageStatus();const primary=elements.get('stage-status').querySelector('[data-testid="stage-execution-status"]').textContent;assert.match(primary,/^Failed/,JSON.stringify(fields));}
install();qa.physicalFlow.currentRun=()=>({id:'newer-result'});qa.renderStageStatus();assert.match(elements.get('stage-status').querySelector('[data-testid="stage-execution-status"]').textContent,/^Failed/);
install();qa.physicalFlow.runCurrent=()=>false;qa.renderStageStatus();assert.match(elements.get('stage-status').querySelector('[data-testid="stage-execution-status"]').textContent,/^Failed/);
install();qa.executionState.overlay=()=>({status:'Failed',reconnectRequired:true,detail:'Refresh the saved result.'});qa.renderStageStatus();assert.match(elements.get('stage-status').querySelector('[data-testid="stage-execution-status"]').textContent,/^Failed/);
install({freshness:'Stale'});qa.renderStageStatus();assert.match(elements.get('stage-status').querySelector('[data-testid="stage-execution-status"]').textContent,/^Not run/);
""")

if __name__=='__main__':unittest.main()

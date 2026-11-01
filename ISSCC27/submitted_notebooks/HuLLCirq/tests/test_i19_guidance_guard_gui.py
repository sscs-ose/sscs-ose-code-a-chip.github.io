"""Unavailable execution capability is not a running job; guards stay closed."""
import shutil
import subprocess
import unittest
from test_instant_execution_gui import HARNESS, PROJECT
from test_cancelled_guidance_gui import SETUP


class GuidanceCapabilityGuardTests(unittest.TestCase):
    def test_saved_cancellation_is_truthful_while_storage_protocol_still_blocks_actions(self):
        node=shutil.which('node')
        if not node:self.skipTest('Installed Node required; no dependency is installed.')
        harness=HARNESS.replace('api,receiveExecution,','executionSubmissions,api,receiveExecution,')
        self.assertNotEqual(harness,HARNESS)
        script=harness+SETUP+r"""
const record=install(),before=JSON.stringify(qa.state.envelope);
qa.executionSubmissions.storageError='SOFTWARE QA unavailable session storage';
assert.equal(qa.executionSubmissions.blocked(),true);
assert.equal(qa.physicalFlow.callbacks.project().busy,true,'Actual submission gate remains blocked');
assert.equal(qa.guidanceContext().busy,false,'Capability failure is not an active execution');
qa.renderStageStatus();
assert.match(elements.get('stage-status').querySelector('[data-testid="stage-execution-status"]').textContent,/^Cancelled/);
assert.equal(qa.resolveStageGuidance(qa.guidanceContext()).decisionId,'cancelled');
assert.equal(JSON.stringify(qa.state.envelope),before);assert.equal(record.execution_status,'Cancelled');
assert.equal(requests.length,0);
})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});
"""
        result=subprocess.run([node,'--experimental-vm-modules','-e',script],cwd=PROJECT,capture_output=True,text=True,encoding='utf-8',timeout=25)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

"""Real shared badge and stage header reasons; isolated DOM, no live execution."""
import shutil
import subprocess
import unittest

from test_visual_navigation import CLIENT, PROJECT


HARNESS = CLIENT.replace('setNavigate:callback=>{setStage=callback;}',
                         'badge,stageVisual,resolveStageGuidance,setNavigate:callback=>{setStage=callback;}')
assert HARNESS != CLIENT, "The isolated app fixture must expose the real badge/guidance helpers."


class ExplicitReasonGuiTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node required')
        result = subprocess.run([node, '--experimental-vm-modules', '-e', HARNESS +
                                 '\n(async()=>{const qa=await initialize();\n' + body +
                                 '\nassert.equal(requests.length,0);})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});'],
                                cwd=PROJECT, capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_old_status_badges_do_not_add_a_sixth_primary_state(self):
        self.run_client(r"""
const saved={status:'Blocked',counts:{Blocked:2}};const before=JSON.stringify(saved);
assert.equal(qa.badge(saved.status).textContent,'Not run');
assert.equal(qa.badge('Blocked: 2').textContent,'Not run: 2');
assert.equal(qa.badge('Failed').textContent,'Failed');
assert.equal(JSON.stringify(saved),before);
""")

    def test_not_implemented_and_missing_prerequisites_are_distinct_in_real_header(self):
        self.run_client(r"""
qa.state.envelope.global_generation={ready:false,jobs:[],blocked_reason:'S08 currently integrates the six declared NPU node types.'};
qa.state.stage='global_rtl_generation';qa.renderStageStatus();
assert.equal(elements.get('stage-status').getAttribute('data-status'),'Not run');
assert.match(elements.get('stage-status').textContent,/Not implemented:/);
qa.state.stage='layout';qa.state.envelope.physical_workflow={ready:false,runs:[],blocked_reason:'Adopt the latest current S11 layout before this operation.'};
qa.renderStageStatus();assert.match(elements.get('stage-status').textContent,/Prerequisites missing:/);
assert.doesNotMatch(elements.get('stage-status').textContent,/Blocked/i);
""")

    def test_tool_setup_is_not_misreported_as_missing_implementation(self):
        self.run_client(r"""
qa.state.stage='drc';qa.state.envelope.drc_workflow={ready:true,tool_ready:false,runs:[],tool_blocked_reason:'The fixed DRC runtime and PDK are not ready.'};
qa.renderStageStatus();assert.equal(elements.get('stage-status').getAttribute('data-status'),'Not run');
assert.match(elements.get('stage-status').textContent,/Tool setup required:/);
""")

    def test_upstream_restart_does_not_hide_existing_implementation_requirement(self):
        self.run_client(r"""
qa.state.stage='global_rtl_generation';qa.executionState.setScope('isolated-reasons');
qa.executionState.begin({kind:'execute',stageId:'local_rtl_generation'});
qa.state.envelope.global_generation={ready:false,jobs:[],blocked_reason:'S08 currently integrates the six declared NPU node types.'};
qa.renderStageStatus();assert.equal(elements.get('stage-status').getAttribute('data-status'),'Not run');
assert.match(elements.get('stage-status').textContent,/Not implemented:/);
const guide=qa.resolveStageGuidance({stage:'global_rtl_generation',executionOverlay:{invalidated:true,status:'Not run'},gate:qa.state.envelope.global_generation.blocked_reason});
assert.equal(guide.title,'Not implemented');assert.equal(guide.primary.kind,'navigate');assert.equal(guide.primary.stage,'specifications');
""")


if __name__ == '__main__':
    unittest.main()

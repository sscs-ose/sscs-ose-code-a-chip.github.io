"""Native details expansion survives redraws; isolated GUI, no model/EDA calls."""
import unittest

from test_generation_batch_gui import GenerationBatchGuiTests


FAILED_SOURCE = r"""
project.envelope.workflow_runs=[{id:'s05-failed',node_id:'node-a',stage_id:'local_synthesis',candidate_id:'candidate-a',execution_status:'Completed',validation_status:'Failed',freshness:'Current',finished_at:'saved',checks:{executed:true,stderr:'ERROR: unsupported language'}}];
batchUI.receive(project.envelope);
assert.equal(batchUI.failedSynthesis().length,1);
const selector=()=>batchTest('generation-batch-node-selection');
const instructions=()=>batchTest('generation-batch-node-instructions');
"""


class GenerationBatchDetailsGuiTests(unittest.TestCase):
    client = GenerationBatchGuiTests.client

    def test_checkbox_redraw_keeps_both_native_details_open_before_toggle_event(self):
        self.client(FAILED_SOURCE + r"""
selector().open=true;instructions().open=true;
// Native open properties change before the queued browser toggle event.
const checkbox=batchTest('generation-batch-select-node-b');
checkbox.checked=true;checkbox.onchange({target:checkbox});
assert.equal(selector().open,true);assert.equal(instructions().open,true);
assert.equal(batchUI.selected.has('node-b'),true);
assert.ok(batchTest('generation-batch-node-instruction-node-b'));
assert.equal(requests.length,0);
""")

    def test_background_receive_and_repeated_refresh_preserve_user_expansion(self):
        self.client(FAILED_SOURCE + r"""
selector().open=true;instructions().open=true;
project.envelope.llm.probe={status:'Connected'};
batchUI.receive(project.envelope);batchUI.refresh();batchUI.refresh();
assert.equal(selector().open,true);assert.equal(instructions().open,true);
selector().open=false;instructions().open=false;
batchUI.receive(project.envelope);batchUI.refresh();
assert.equal(selector().open,false);assert.equal(instructions().open,false);
assert.equal(requests.length,0);
""")

    def test_select_all_and_new_render_host_keep_open_state_and_instruction_draft(self):
        self.client(FAILED_SOURCE + r"""
selector().open=true;instructions().open=true;
batchTest('generation-batch-select-all').onclick();
assert.equal(selector().open,true);assert.equal(instructions().open,true);
batchTest('generation-batch-node-instruction-node-b').change('Keep this own-node instruction.');
const replacement=new DOMDouble('div');batchUI.renderGeneration(replacement);
assert.equal(replacement.querySelector('[data-testid="generation-batch-node-selection"]').open,true);
assert.equal(replacement.querySelector('[data-testid="generation-batch-node-instructions"]').open,true);
assert.equal(replacement.querySelector('[data-testid="generation-batch-node-instruction-node-b"]').value,'Keep this own-node instruction.');
assert.equal(requests.length,0);
""")

    def test_project_or_system_switch_does_not_inherit_previous_expansion(self):
        self.client(FAILED_SOURCE + r"""
for (const switchScope of [()=>project.envelope.workspace_identity.session_id='session-b',()=>project.design.id='design-b']) {
 selector().open=true;instructions().open=true;
 switchScope();batchUI.receive(project.envelope);
 // Failed S05 defaults closed; old DOM must not restore the previous scope.
 assert.equal(!!selector().open,false);assert.equal(!!instructions().open,false);
 assert.equal(batchUI.selectionOpen,null);assert.equal(batchUI.nodeInstructionsOpen,false);
}
assert.equal(requests.length,0);
""")


del GenerationBatchGuiTests


if __name__ == '__main__':
    unittest.main()

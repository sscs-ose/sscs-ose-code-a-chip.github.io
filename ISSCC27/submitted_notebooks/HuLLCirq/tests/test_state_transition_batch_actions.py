"""Exact batch controls on isolated DOM/API fixtures; no live model or EDA."""
import unittest

import test_generation_batch_gui as generation
import test_s05_batch_gui as synthesis


class StateTransitionBatchActionsGuiTests(unittest.TestCase):
    def test_s04_batch_cancel_and_reconnect_handlers_do_not_repeat_a_request(self):
        generation.GenerationBatchGuiTests().client(r"""
batchUI.receive(makeEnvelope([batch]));batchUI.renderGeneration(batchHost);
const before=JSON.stringify(batch);const cancel=batchTest('generation-batch-cancel');assert.ok(cancel);assert.equal(!!cancel.disabled,false);
responder=async(route,body)=>{assert.equal(route,'generation/batches/batch-a/cancel');assert.equal(Object.keys(body).length,0);return makeEnvelope([{...batch,execution_status:'Cancelled'}]);};
await cancel.onclick();assert.equal(requests.length,1);assert.equal(batchUI.activeBatch(),undefined);assert.equal(JSON.stringify(batch),before);
batchUI.pollError='Lost saved progress';batchUI.renderGeneration(batchHost);const reconnect=batchTest('generation-batch-reconnect');assert.ok(reconnect);assert.equal(!!reconnect.disabled,false);
responder=async(route,body)=>{assert.equal(route,'project');assert.equal(body,undefined);return makeEnvelope([{...batch,execution_status:'Cancelled'}]);};
await reconnect.onclick();assert.equal(requests.length,2);assert.deepEqual(requests.map(call=>call[0]),['generation/batches/batch-a/cancel','project']);assert.equal(JSON.stringify(batch),before);
""")

    def test_s05_batch_cancel_and_reconnect_handlers_preserve_child_records(self):
        synthesis.S05BatchGuiTests().client(r"""
const running={...batch,execution_status:'Running'};local.receive(makeEnvelope([running],[passed,failedRun]));local.render(localHost);
const before=JSON.stringify([passed,failedRun]);const cancel=localTest('workflow-batch-cancel');assert.ok(cancel);assert.equal(!!cancel.disabled,false);
responder=async(route,body)=>{assert.equal(route,'workflow/batches/batch-a/cancel');assert.equal(Object.keys(body).length,0);return makeEnvelope([{...batch,execution_status:'Cancelled'}],[passed,failedRun]);};
await cancel.onclick();assert.equal(requests.length,1);assert.equal(local.activeBatch(),undefined);
local.batchPollError='Lost saved progress';local.render(localHost);const reconnect=localTest('workflow-batch-reconnect');assert.ok(reconnect);assert.equal(!!reconnect.disabled,false);
responder=async(route,body)=>{assert.equal(route,'project');assert.equal(body,undefined);return makeEnvelope([{...batch,execution_status:'Cancelled'}],[passed,failedRun]);};
await reconnect.onclick();assert.equal(requests.length,2);assert.deepEqual(requests.map(call=>call[0]),['workflow/batches/batch-a/cancel','project']);assert.equal(JSON.stringify([passed,failedRun]),before);
""")


if __name__ == '__main__':
    unittest.main()

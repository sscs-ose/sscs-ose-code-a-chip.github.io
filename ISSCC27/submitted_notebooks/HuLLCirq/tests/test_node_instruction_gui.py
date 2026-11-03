"""I1 per-node NL editor routes; isolated DOM and HTTP, no model or EDA."""
import unittest
from unittest.mock import patch

import test_generalized_repair_gui as gui
import test_s05_batch_http as http


class NodeInstructionGuiTests(unittest.TestCase):
    client = gui.GeneralizedRepairGuiTests.client

    def test_collapsed_selected_node_fields_send_only_scoped_map_after_explicit_preview(self):
        self.client(r"""
project.design.nodes.push({...project.design.nodes[0],id:'node-b',name:'Other node'});
project.envelope.workflow_runs=[];batchUI.plan=null;batchUI.selected=new Set(['node-a','node-b']);batchUI.selectionEdited=true;batchUI.refresh();
const panel=test(host,'generation-batch-node-instructions');assert.ok(panel);assert.notEqual(panel.open,true);
assert.match(panel.textContent,/Per-node instructions \(2\)/);assert.match(panel.textContent,/previous turns are retained only within the context budget/);
const edit=(id,value)=>{const control=test(host,id);control.value=value;for(const listener of control.listeners.input||[])listener({target:control});};
edit('generation-batch-instruction','COMMON original interface');edit('generation-batch-node-instruction-node-a','A_ONLY use independent flags <script>literal</script>');edit('generation-batch-node-instruction-node-b','B_ONLY keep a pending word');
assert.equal(requests.length,0);assert.equal(batchUI.plan,null);
responder=async(route,body)=>{assert.equal(route,'generation/batches/preview');assert.equal(body.mode,'generate');assert.equal(body.instruction,'COMMON original interface');assert.equal(JSON.stringify(body.node_instructions),JSON.stringify({'node-a':'A_ONLY use independent flags <script>literal</script>','node-b':'B_ONLY keep a pending word'}));return {...plan,mode:'generate',items:[{...item,node_id:'node-a',operation:'generate'},{...item,node_id:'node-b',operation:'generate'}]};};
await test(host,'generation-batch-preview').listeners.click[0]();assert.equal(requests.length,1);assert.equal(requests.some(([route])=>route==='generation/batches/start'),false);
assert.equal(test(host,'generation-batch-node-instruction-node-a').value,'A_ONLY use independent flags <script>literal</script>');
""")

    def test_edit_invalidates_preview_and_rebuilds_same_selection_with_latest_own_instruction(self):
        self.client(r"""
project.envelope.workflow_runs=[];batchUI.plan=null;batchUI.selected=new Set(['node-a']);batchUI.selectionEdited=true;batchUI.nodeInstructions['node-a']='Initial own NL';
responder=async(route,body)=>{assert.equal(route,'generation/batches/preview');return {...plan,mode:'generate',items:[{...item,operation:'generate',instruction:body.node_instructions['node-a']}]};};
await batchUI.prepare('generate',['node-a'],false);const frozen=batchUI.plan,before=JSON.stringify(frozen),count=requests.length;
const editor=test(host,'generation-batch-node-instruction-node-a');editor.value='Revised own NL';for(const listener of editor.listeners.input||[])listener({target:editor});
assert.equal(batchUI.plan,null);assert.equal(JSON.stringify(frozen),before);assert.equal(requests.length,count);assert.equal(batchUI.guidance().primary.label,'Rebuild generation preview');
await batchUI.guidance().primary.action();assert.equal(requests.length,count+1);assert.equal(requests.at(-1)[1].node_instructions['node-a'],'Revised own NL');assert.equal(JSON.stringify(requests.at(-1)[1].node_ids),'["node-a"]');assert.equal(batchUI.plan.items[0].instruction,'Revised own NL');
""")

    def test_unselected_drafts_are_not_sent_and_project_switch_clears_them(self):
        self.client(r"""
project.envelope.workflow_runs=[];batchUI.plan=null;batchUI.nodeInstructions['node-a']='A scoped NL';batchUI.nodeInstructions['node-b']='B must not be sent';batchUI.selected=new Set(['node-a']);batchUI.selectionEdited=true;
responder=async(route,body)=>{assert.equal(JSON.stringify(body.node_instructions),'{"node-a":"A scoped NL"}');return {...plan,mode:'generate'};};
await batchUI.prepare('generate',['node-a'],false);assert.equal(requests.length,1);assert.equal(batchUI.nodeInstructions['node-b'],'B must not be sent');
project.design={...project.design,id:'another-system'};batchUI.receive(project.envelope);assert.equal(Object.keys(batchUI.nodeInstructions).length,0);assert.equal(batchUI.instruction,'');assert.equal(batchUI.plan,null);
""")

    def test_retry_and_repair_paths_do_not_inject_new_node_drafts(self):
        self.client(r"""
batchUI.nodeInstructions['node-a']='Do not inject into frozen retry';batchUI.plan=null;
responder=async(route,body)=>{assert.equal(route,'generation/batches/preview');assert.equal(Object.hasOwn(body,'node_instructions'),false);return {...plan,mode:body.mode};};
await batchUI.prepare('generate',['node-a'],false,'old-batch');assert.equal(requests.at(-1)[1].retry_batch_id,'old-batch');
await batchUI.prepare('synthesis_repair',['node-a'],false);assert.equal(requests.length,2);assert.equal(requests.some(([route])=>route==='generation/batches/start'),false);
""")


class NodeInstructionHttpTests(unittest.TestCase):
    setUp = http.S05BatchHttpTests.setUp
    tearDown = http.S05BatchHttpTests.tearDown
    mutation = http.S05BatchHttpTests.mutation
    create = http.S05BatchHttpTests.create
    request = http.S05BatchHttpTests.request

    def test_preview_forwards_optional_map_and_omits_it_for_legacy_clients(self):
        self.create()
        revision = self.server.store.envelope()["revision"]["id"]
        hints = {"node-a": "Natural-language implementation guidance"}
        with patch.object(self.server.generation_batches, "preview", return_value={"fixture": "unsent preview"}) as preview:
            status, result = self.request("POST", "/api/generation/batches/preview", {"revision_id": revision, "mode": "generate", "node_ids": ["node-a"], "instruction": "Shared NL", "node_instructions": hints})
        self.assertEqual(status, 200)
        self.assertEqual(result["fixture"], "unsent preview")
        preview.assert_called_once_with(revision, "generate", ["node-a"], "Shared NL", None, node_instructions=hints)
        with patch.object(self.server.generation_batches, "preview", return_value={}) as preview:
            status, _ = self.request("POST", "/api/generation/batches/preview", {"revision_id": revision})
        self.assertEqual(status, 200)
        preview.assert_called_once_with(revision, "generate", None, "", None)


if __name__ == "__main__":
    unittest.main()

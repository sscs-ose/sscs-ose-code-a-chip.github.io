"""I5 per-node S05/S06 repair hints; isolated sources/providers only."""
import copy
import json
import unittest
from unittest.mock import patch

import test_generation_batches as fixtures
import test_netlist_repair_batches as netlist
import test_generalized_repair_gui as gui
from hullcirq.domain import DomainError
from hullcirq.generation import GenerationManager
from hullcirq.generation_batches import GenerationBatchManager, REPAIR_NODE_INSTRUCTION_VERSION
from hullcirq.verification import object_hash


class RepairNodeInstructionTests(unittest.TestCase):
    setUp = fixtures.GenerationBatchTests.setUp
    close = fixtures.GenerationBatchTests.close
    response = fixtures.GenerationBatchTests.response
    run_batch = fixtures.GenerationBatchTests.run_batch

    def prepare_sources(self, mode):
        self.run_batch()
        if mode == "netlist_repair":
            self.addCleanup(self.workflow.close)
            self.workflow = netlist.SavedWorkflowFixture(self.generation._state["jobs"])
            self.manager.workflow = self.workflow
        else:
            def fail(rtl, module, config, directory, cancelled):
                return {"validation_status":"Failed","executed":True,"exit_code":1,"diagnostics":[{"code":"synthesis_failed","severity":"error","message":"candidate.v:2: ERROR: syntax error"}],"stdout":"candidate.v:2: ERROR: syntax error\n","stderr":""}
            with patch("hullcirq.workflow.synthesize_generic",fail):
                self.workflow.start_batch(self.revision,"isolated-I5-synthesis-source")
                self.workflow._batch_worker.join(10)
                self.assertFalse(self.workflow.is_active())

    def assert_scoped(self, plan):
        self.assertTrue(plan["ready_to_start"])
        self.assertEqual(plan["instruction_inputs"]["version"],REPAIR_NODE_INSTRUCTION_VERSION)
        for item in plan["items"]:
            own="PRODUCER_ONLY" if item["node_id"]=="node-producer" else "CONSUMER_ONLY"
            other="CONSUMER_ONLY" if own=="PRODUCER_ONLY" else "PRODUCER_ONLY"
            self.assertIn(own,item["instruction"]); self.assertNotIn(other,item["instruction"])
            self.assertIn("COMMON_KEEP",item["instruction"])
            self.assertIn(own,item["context"]["messages"][-1]["content"])
            self.assertNotIn(other,item["context"]["messages"][-1]["content"])
            self.assertNotIn("instruction_inputs",item["context"])
            self.assertEqual(item["operation"],"repair")
            self.assertTrue(item["source_workflow_run_id"])
            if plan["mode"]=="netlist_repair": self.assertIn("FAIL cycle 2",item["instruction"])
            else: self.assertIn("syntax error",item["instruction"])

    def test_s05_own_hint_enters_actual_guidance_context_and_separate_requests(self):
        self.prepare_sources("synthesis_repair")
        original=self.store.state_path.read_bytes(); old_plans=copy.deepcopy(self.manager._state["plans"])
        plan=self.manager.preview(self.revision,"synthesis_repair",instruction="COMMON_KEEP interface",node_instructions={"node-producer":"PRODUCER_ONLY correct module syntax","node-consumer":"CONSUMER_ONLY fix unmatched begin"})
        self.assert_scoped(plan)
        self.assertEqual(len(self.calls),2)
        result=self.run_batch(plan,"isolated-I5-S05-own-hints")
        self.assertEqual(result["validation_status"],"Passed")
        self.assertEqual(len(self.calls),4)
        for index,item in enumerate(plan["items"]):self.assertEqual(self.calls[index+2][-1],item["context"]["messages"][-1])
        self.assertEqual(self.manager._state["plans"][:len(old_plans)],old_plans)
        self.assertEqual(self.store.state_path.read_bytes(),original)
        self.assert_reopens_unchanged(plan)

    def test_s06_actual_failure_and_only_own_hint_reopen_without_rewriting_v1_plans(self):
        self.prepare_sources("netlist_repair")
        # Preserve an existing generation-v1 plan alongside new repair-v2.
        self.manager.preview(self.revision,node_ids=["node-producer"],node_instructions={"node-producer":"Older generation-v1 guidance"})
        old=copy.deepcopy(self.manager._state["plans"])
        plan=self.manager.preview(self.revision,"netlist_repair",instruction="COMMON_KEEP original tests",node_instructions={"node-producer":"PRODUCER_ONLY correct pending valid","node-consumer":"CONSUMER_ONLY keep independent ready"})
        self.assert_scoped(plan)
        self.assertEqual(self.manager._state["plans"][:len(old)],old)
        self.assert_reopens_unchanged(plan)

    def assert_reopens_unchanged(self, plan):
        before=(self.generation.path.read_bytes(),self.manager.path.read_bytes())
        loaded=GenerationManager(self.store)
        manager=GenerationBatchManager(self.store,loaded,self.workflow)
        self.addCleanup(loaded.close);self.addCleanup(manager.close)
        self.assertEqual(before,(loaded.path.read_bytes(),manager.path.read_bytes()))
        self.assertEqual(manager._plan(plan["plan_id"]),plan)

    def test_invalid_maps_all_modes_reject_before_appending_a_plan(self):
        self.prepare_sources("netlist_repair")
        for mode in ("synthesis_repair","netlist_repair"):
            for hints,selected in (({"unknown":"bad"},None),({"node-consumer":"unselected"},["node-producer"]),({"node-producer":8},None),({"node-producer":"あ"*2731},None),([],None)):
                before=self.manager.path.read_bytes()
                with self.subTest(mode=mode,hints=type(hints).__name__),self.assertRaises(DomainError) as caught:
                    self.manager.preview(self.revision,mode,node_ids=selected,node_instructions=hints)
                self.assertEqual(caught.exception.code,"invalid_node_instructions")
                self.assertEqual(self.manager.path.read_bytes(),before)
        self.assertEqual(len(self.calls),2)

    def test_retry_keeps_frozen_composite_and_new_maps_require_fresh_preview(self):
        self.prepare_sources("netlist_repair")
        plan=self.manager.preview(self.revision,"netlist_repair",node_instructions={"node-producer":"PRODUCER_ONLY original correction","node-consumer":"CONSUMER_ONLY original correction"})
        def partial(*args):
            answer=self.response(*args)
            if len(self.calls)==3:answer.update(execution_status="Failed",error={"code":"output_truncated","message":"isolated incomplete response"})
            return answer
        batch=self.run_batch(plan,"isolated-I5-repair-failure",partial)
        with self.assertRaises(DomainError) as caught:
            self.manager.preview(self.revision,"netlist_repair",retry_batch_id=batch["id"],node_instructions={"node-producer":"replacement draft forbidden"})
        self.assertEqual(caught.exception.code,"invalid_node_instructions")
        retry=self.manager.preview(self.revision,"netlist_repair",retry_batch_id=batch["id"])
        self.assertEqual(retry["items"][0]["instruction"],plan["items"][0]["instruction"])
        self.assertNotIn("instruction_inputs",retry)
        self.assert_reopens_unchanged(retry)

    def test_rehashed_map_tampering_cannot_relabel_frozen_repair_instruction(self):
        self.prepare_sources("netlist_repair")
        self.manager.preview(self.revision,"netlist_repair",node_instructions={"node-producer":"PRODUCER_ONLY frozen"})
        state=json.loads(self.manager.path.read_text(encoding="utf-8")); target=state["plans"][-1]
        target["instruction_inputs"]["nodes"]["node-producer"]="Changed own correction"
        target["plan_id"]="generation-plan-"+object_hash({key:value for key,value in target.items() if key!="plan_id"})
        self.manager.path.write_text(json.dumps(state),encoding="utf-8");before=self.manager.path.read_bytes()
        with self.assertRaises(DomainError) as caught:GenerationBatchManager(self.store,self.generation,self.workflow)
        self.assertEqual(caught.exception.code,"invalid_generation_batch_store")
        self.assertEqual(self.manager.path.read_bytes(),before)


class RepairNodeInstructionGuiTests(unittest.TestCase):
    client=gui.GeneralizedRepairGuiTests.client

    def test_s05_panel_editor_scopes_hint_and_edit_requires_rebuild(self):
        self.client(r"""
const edit=test(host,'synthesis-batch-node-instruction-node-a');assert.ok(edit);assert.equal(edit.disabled,false);
const frozen=JSON.stringify(batchUI.plan),before=requests.length;edit.value='S05_ONLY remove duplicate driver';for(const fn of edit.listeners.input||[])fn({target:edit});
assert.equal(batchUI.plan,null);assert.equal(JSON.stringify(plan),frozen);assert.equal(requests.length,before);
batchUI.nodeInstructions['node-a']='GENERATION_MUST_NOT_LEAK';batchUI.netlistNodeInstructions['node-a']='S06_MUST_NOT_LEAK';batchUI.synthesisNodeInstructions['unselected']='OMIT';
responder=async(route,body)=>{assert.equal(route,'generation/batches/preview');assert.equal(body.mode,'synthesis_repair');assert.equal(JSON.stringify(body.node_instructions),'{"node-a":"S05_ONLY remove duplicate driver"}');return plan;};
await batchUI.prepare('synthesis_repair',['node-a'],false);assert.equal(requests.length,before+1);assert.equal(requests.some(([route])=>route==='generation/batches/start'),false);
""")

    def test_s06_editor_scopes_hint_and_retry_does_not_replace_original_draft(self):
        self.client(r"""
project.envelope.generation_batches={netlist_repair_sources:[{node_id:'node-a',latest_job_id:'candidate-a',base_job_id:'candidate-a',source_workflow_run_id:'s06-a',netlist_repair_evidence:{first_failure:'HULLCIRQ_FAIL original mismatch'}}]};batchUI.refresh();
const edit=test(host,'netlist-batch-node-instruction-node-a');assert.ok(edit);edit.value='S06_ONLY reset pending output';for(const fn of edit.listeners.input||[])fn({target:edit});assert.equal(batchUI.plan,null);
batchUI.synthesisNodeInstructions['node-a']='S05_MUST_NOT_LEAK';responder=async(route,body)=>{assert.equal(body.mode,'netlist_repair');assert.equal(JSON.stringify(body.node_instructions),'{"node-a":"S06_ONLY reset pending output"}');return {...plan,mode:'netlist_repair'};};
await batchUI.prepare('netlist_repair',['node-a'],false);assert.equal(requests.length,1);
responder=async(route,body)=>{assert.equal(Object.hasOwn(body,'node_instructions'),false);assert.equal(body.retry_batch_id,'frozen-old-repair');return {...plan,mode:'netlist_repair'};};await batchUI.prepare('netlist_repair',['node-a'],false,'frozen-old-repair');assert.equal(requests.length,2);
assert.equal(batchUI.netlistNodeInstructions['node-a'],'S06_ONLY reset pending output');
""")

    def test_repair_drafts_clear_on_project_switch_and_active_operation_disables_fields(self):
        self.client(r"""
batchUI.synthesisNodeInstructions['node-a']='saved S05 draft';batchUI.netlistNodeInstructions['node-a']='saved S06 draft';batchUI.busy=true;batchUI.refresh();assert.equal(test(host,'synthesis-batch-node-instruction-node-a').disabled,true);
batchUI.busy=false;project.design={...project.design,id:'different-system'};batchUI.receive(project.envelope);assert.equal(Object.keys(batchUI.synthesisNodeInstructions).length,0);assert.equal(Object.keys(batchUI.netlistNodeInstructions).length,0);assert.equal(batchUI.plan,null);
""")


if __name__=="__main__":unittest.main()

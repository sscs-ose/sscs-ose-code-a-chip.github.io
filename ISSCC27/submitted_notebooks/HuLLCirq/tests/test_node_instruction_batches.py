"""I1 scoped natural-language batch guidance; isolated provider, no circuit runs."""
import copy
import json
import unittest

import test_generation_batches as fixtures
from hullcirq.domain import DomainError
from hullcirq.generation import GenerationManager
from hullcirq.generation_batches import GenerationBatchManager, NODE_INSTRUCTION_VERSION
from hullcirq.verification import object_hash


class NodeInstructionBatchTests(unittest.TestCase):
    setUp = fixtures.GenerationBatchTests.setUp
    close = fixtures.GenerationBatchTests.close
    response = fixtures.GenerationBatchTests.response
    run_batch = fixtures.GenerationBatchTests.run_batch

    def test_two_separate_requests_use_shared_and_only_target_guidance_in_current_context(self):
        original = self.store.state_path.read_bytes()
        hints = {"node-producer": "PRODUCER_ONLY: hold data until accepted.",
                 "node-consumer": "CONSUMER_ONLY: use an independent pending flag."}
        plan = self.manager.preview(self.revision, instruction="SHARED: retain the saved interface.", node_instructions=hints)
        self.assertTrue(plan["ready_to_start"])
        self.assertEqual(self.calls, [])
        self.assertEqual(plan["instruction_inputs"], {"version": NODE_INSTRUCTION_VERSION,
                         "shared": "SHARED: retain the saved interface.", "nodes": hints})
        hints["node-producer"] = "Draft changed after preview"
        for item in plan["items"]:
            text = item["context"]["messages"][-1]["content"]
            self.assertIn("SHARED:", text)
            self.assertIn("PRODUCER_ONLY:" if item["node_id"] == "node-producer" else "CONSUMER_ONLY:", text)
            self.assertNotIn("CONSUMER_ONLY:" if item["node_id"] == "node-producer" else "PRODUCER_ONLY:", text)
            self.assertNotIn("Draft changed", text)
        result = self.run_batch(plan)
        self.assertEqual(result["validation_status"], "Passed")
        self.assertEqual(len(self.calls), 2)
        for index, item in enumerate(plan["items"]):
            self.assertEqual(self.calls[index][-1], item["context"]["messages"][-1])
        # Exact earlier conversation remains explicitly retained, not merged
        # into the second node's current specification or instruction.
        self.assertIn(self.calls[0][-1], self.calls[1][:-1])
        self.assertEqual(original, self.store.state_path.read_bytes())
        before = (self.manager.path.read_bytes(), self.generation.path.read_bytes())
        loaded = GenerationManager(self.store)
        loaded_batches = GenerationBatchManager(self.store, loaded, self.workflow)
        self.addCleanup(loaded.close); self.addCleanup(loaded_batches.close)
        self.assertEqual(before, (loaded_batches.path.read_bytes(), loaded.path.read_bytes()))
        self.assertEqual(loaded_batches._plan(plan["plan_id"]), plan)

    def test_invalid_unknown_unselected_and_nonstring_node_instructions_are_rejected_without_saving(self):
        for hints, selected in (([], None), ({"node-producer": 7}, None), ({7: "text"}, None),
                                ({"unknown-node": "text"}, None),
                                ({"node-consumer": "text"}, ["node-producer"]),
                                ({"node-producer": "あ" * 2731}, None)):
            with self.subTest(hints_type=type(hints).__name__, selected=selected), self.assertRaises(DomainError) as caught:
                self.manager.preview(self.revision, node_ids=selected, node_instructions=hints)
            self.assertEqual(caught.exception.code, "invalid_node_instructions")
        self.assertEqual(self.manager._state["plans"], [])
        self.assertFalse(self.manager.path.exists())

    def test_optional_map_omitted_or_empty_preserves_legacy_plan_shape(self):
        legacy = self.manager.preview(self.revision, instruction="Shared legacy NL")
        empty = self.manager.preview(self.revision, instruction="Shared legacy NL", node_instructions={})
        self.assertNotIn("instruction_inputs", legacy)
        self.assertNotIn("instruction_inputs", empty)
        self.assertEqual(legacy["items"], empty["items"])
        self.assertEqual([item["instruction"] for item in legacy["items"]], ["Shared legacy NL"] * 2)
        raw = self.manager.path.read_bytes()
        loaded = GenerationBatchManager(self.store, self.generation, self.workflow)
        self.addCleanup(loaded.close)
        self.assertEqual(loaded.path.read_bytes(), raw)

    def test_map_requires_fresh_generation_and_explicit_inclusion_of_already_accepted_nodes(self):
        self.run_batch()
        for mode in ("synthesis_repair", "netlist_repair", "generate"):
            with self.subTest(mode=mode), self.assertRaises(DomainError) as caught:
                self.manager.preview(self.revision, mode, node_instructions={"node-producer": "Own NL"})
            self.assertEqual(caught.exception.code, "invalid_node_instructions")
        plan = self.manager.preview(self.revision, node_ids=["node-producer"], node_instructions={"node-producer": "Own NL"})
        self.assertTrue(plan["ready_to_start"])
        self.assertEqual(len(plan["items"]), 1)

    def test_retry_preserves_frozen_composite_and_rejects_new_map(self):
        plan = self.manager.preview(self.revision, node_instructions={"node-producer": "Original own guidance"})
        def partial(*args):
            result = self.response(*args)
            if len(self.calls) == 1:
                result.update(execution_status="Failed", error={"code": "output_truncated", "message": "Isolated partial answer"})
            return result
        old = self.run_batch(plan, response=partial)
        with self.assertRaises(DomainError) as caught:
            self.manager.preview(self.revision, retry_batch_id=old["id"], node_instructions={"node-producer": "Replacement own guidance"})
        self.assertEqual(caught.exception.code, "invalid_node_instructions")
        retry = self.manager.preview(self.revision, retry_batch_id=old["id"])
        self.assertEqual(retry["items"][0]["instruction"], plan["items"][0]["instruction"])
        self.assertNotIn("instruction_inputs", retry)
        new = self.run_batch(retry, "isolated-own-guidance-retry")
        self.assertEqual(new["validation_status"], "Passed")
        loaded = GenerationManager(self.store)
        loaded_batches = GenerationBatchManager(self.store, loaded, self.workflow)
        self.addCleanup(loaded.close); self.addCleanup(loaded_batches.close)
        self.assertEqual(loaded_batches._plan(plan["plan_id"]), plan)
        self.assertEqual(loaded_batches.batch(new["id"])["validation_status"], "Passed")

    def test_changed_guidance_rejects_rehashed_plan_with_inconsistent_frozen_instruction(self):
        plan = self.manager.preview(self.revision, node_instructions={"node-producer": "Frozen original NL"})
        raw = json.loads(self.manager.path.read_text(encoding="utf-8"))
        raw["plans"][0]["instruction_inputs"]["nodes"]["node-producer"] = "Altered guidance"
        changed = raw["plans"][0]
        changed["plan_id"] = "generation-plan-" + object_hash({key: value for key, value in changed.items() if key != "plan_id"})
        self.manager.path.write_text(json.dumps(raw), encoding="utf-8")
        before = self.manager.path.read_bytes()
        with self.assertRaises(DomainError) as caught:
            GenerationBatchManager(self.store, self.generation, self.workflow)
        self.assertEqual(caught.exception.code, "invalid_generation_batch_store")
        self.assertEqual(self.manager.path.read_bytes(), before)

    def test_guidance_budget_includes_complete_text_without_truncation(self):
        baseline = self.manager.preview(self.revision, node_ids=["node-producer"])
        hints = {"node-producer": "Preserve every condition. " * 250}
        profile = copy.deepcopy(self.generation._profile()["profile"])
        profile["context_window"] = baseline["items"][0]["context"]["provider_input_estimated_tokens"] + profile["max_output_tokens"] + 100
        self.generation.save_profile(profile, self.generation._profile()["revision_id"])
        plan = self.manager.preview(self.revision, node_ids=["node-producer"], node_instructions=hints)
        self.assertFalse(plan["ready_to_start"])
        self.assertEqual(plan["items"][0]["error"]["code"], "context_budget")
        self.assertIn(hints["node-producer"], plan["items"][0]["context"]["messages"][-1]["content"])
        self.assertFalse(plan["items"][0]["context_budget"]["fits"])
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()

"""I3 thinking settings reach new node prompts; no real provider or EDA runs."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_generation_batches as batch_fixtures
import test_generation_retry as retry_fixtures
from hullcirq.context import build_node_context
from hullcirq.domain import DomainError
from hullcirq.generation import GenerationManager
from hullcirq.generation_batches import GenerationBatchManager


ROOT = Path(__file__).resolve().parents[1]


class ThinkingContextTests(unittest.TestCase):
    def test_default_does_not_soft_disable_thinking_and_explicit_none_does(self):
        design = json.loads((ROOT / "examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))
        before = copy.deepcopy(design)
        default = build_node_context(design, "same", "npu2-control", "Exact human instruction.")
        disabled = build_node_context(design, "same", "npu2-control", "Exact human instruction.", reasoning_effort="none")
        legacy = build_node_context(design, "same", "npu2-control", "Exact human instruction.", template_version="node-verilog-2005-v9")
        self.assertEqual(default["prompt_template_version"], "node-verilog-2005-v10")
        self.assertNotIn("/no_think", default["prompt_text"])
        self.assertNotIn("/think", default["prompt_text"])
        self.assertEqual(disabled["messages"], legacy["messages"])
        self.assertIn("/no_think", disabled["messages"][0]["content"])
        self.assertTrue(disabled["messages"][-1]["content"].endswith("\n/no_think"))
        self.assertEqual(default["thinking_control"], {"reasoning_effort": None, "soft_directive": None})
        self.assertEqual(disabled["thinking_control"], {"reasoning_effort": "none", "soft_directive": "/no_think"})
        for key in ("context", "node_input_hash", "interface", "requested_module_header", "prompt_projection"):
            self.assertEqual(default[key], legacy[key], key)
        self.assertEqual(default["messages"][0]["content"], legacy["messages"][0]["content"].replace("node. /no_think\n", "node.\n", 1))
        self.assertEqual(default["messages"][-1]["content"], legacy["messages"][-1]["content"].removesuffix("\n/no_think"))
        self.assertEqual(default["estimated_input_tokens"], len(json.dumps(default["messages"], ensure_ascii=False, allow_nan=False).encode("utf-8")))
        self.assertEqual(design, before)

    def test_instruction_literal_is_not_rewritten_by_soft_directive_selection(self):
        design = json.loads((ROOT / "examples/m1_two_nodes.json").read_text(encoding="utf-8"))
        literal = "Treat '/no_think' in this sentence as literal saved evidence."
        context = build_node_context(design, "same", "node-producer", literal, reasoning_effort=None)
        self.assertIn(literal, context["messages"][-1]["content"])
        self.assertNotIn("/no_think", context["messages"][0]["content"])
        self.assertFalse(context["messages"][-1]["content"].endswith("\n/no_think"))

    def test_unsupported_new_thinking_modes_are_not_silently_selected(self):
        design = json.loads((ROOT / "examples/m1_two_nodes.json").read_text(encoding="utf-8"))
        for mode in ("high", "default", False, [], {}):
            with self.subTest(mode=mode), self.assertRaises(DomainError) as caught:
                build_node_context(design, "same", "node-producer", reasoning_effort=mode)
            self.assertEqual(caught.exception.code, "unsupported_thinking_control")


class ThinkingBatchTests(unittest.TestCase):
    setUp = batch_fixtures.GenerationBatchTests.setUp
    close = batch_fixtures.GenerationBatchTests.close
    response = batch_fixtures.GenerationBatchTests.response
    run_batch = batch_fixtures.GenerationBatchTests.run_batch

    def update_profile(self, mode):
        profile = copy.deepcopy(self.generation._profile()["profile"])
        profile["reasoning_effort"] = mode
        self.generation.save_profile(profile, self.generation._profile()["revision_id"])

    def test_profile_default_reaches_each_sequential_request_and_reload(self):
        self.update_profile(None)
        plan = self.manager.preview(self.revision, node_instructions={"node-producer": "Own saved NL"})
        result = self.run_batch(plan)
        self.assertEqual(result["validation_status"], "Passed")
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(all("/no_think" not in json.dumps(messages) for messages in self.calls))
        self.assertTrue(all(job["context"]["thinking_control"]["reasoning_effort"] is None for job in self.generation._state["jobs"]))
        before = (self.generation.path.read_bytes(), self.manager.path.read_bytes())
        loaded = GenerationManager(self.store)
        batches = GenerationBatchManager(self.store, loaded, self.workflow)
        self.addCleanup(loaded.close); self.addCleanup(batches.close)
        self.assertEqual(before, (loaded.path.read_bytes(), batches.path.read_bytes()))

    def test_explicit_none_reaches_node_prompt_and_provider_parameters(self):
        self.update_profile("none")
        plan = self.manager.preview(self.revision)
        result = self.run_batch(plan)
        self.assertEqual(result["validation_status"], "Passed")
        for job in self.generation._state["jobs"]:
            self.assertEqual(job["parameters"]["reasoning_effort"], "none")
            self.assertIn("/no_think", job["context"]["messages"][0]["content"])
            self.assertTrue(job["context"]["messages"][-1]["content"].endswith("\n/no_think"))

    def test_old_frozen_v9_plan_executes_with_v9_and_retries_without_template_upgrade(self):
        with patch("hullcirq.context.PROMPT_TEMPLATE_VERSION", "node-verilog-2005-v9"):
            old = self.manager.preview(self.revision)
        frozen = copy.deepcopy(old)
        def partial(*args):
            result = self.response(*args)
            if len(self.calls) == 1:
                result.update(execution_status="Failed", error={"code": "output_truncated", "message": "Isolated partial answer"})
            return result
        batch = self.run_batch(old, response=partial)
        self.assertEqual(self.generation._state["jobs"][0]["context"]["prompt_template_version"], "node-verilog-2005-v9")
        retry = self.manager.preview(self.revision, retry_batch_id=batch["id"])
        self.assertEqual(retry["items"][0]["context"]["messages"], old["items"][0]["context"]["messages"])
        self.assertEqual(retry["items"][0]["context"]["prompt_template_version"], "node-verilog-2005-v9")
        done = self.run_batch(retry, "isolated-v9-after-v10-retry")
        self.assertEqual(done["validation_status"], "Passed")
        self.assertEqual(self.manager._plan(old["plan_id"]), frozen)
        loaded = GenerationManager(self.store)
        batches = GenerationBatchManager(self.store, loaded, self.workflow)
        self.addCleanup(loaded.close); self.addCleanup(batches.close)
        self.assertEqual(batches.batch(done["id"])["validation_status"], "Passed")

    def test_v10_batch_retry_requires_fresh_generation_to_change_thinking_directive(self):
        self.update_profile("none")
        def partial(*args):
            result = self.response(*args)
            result.update(execution_status="Failed", error={"code": "output_truncated", "message": "Isolated partial answer"})
            return result
        batch = self.run_batch(response=partial)
        self.update_profile(None)
        with self.assertRaises(DomainError) as caught:
            self.manager.preview(self.revision, retry_batch_id=batch["id"])
        self.assertEqual(caught.exception.code, "generation_retry_profile_conflict")
        fresh = self.manager.preview(self.revision, node_ids=["node-producer"])
        self.assertTrue(fresh["ready_to_start"])
        self.assertNotIn("/no_think", json.dumps(fresh["items"][0]["context"]["messages"]))


class ThinkingIndividualRetryTests(unittest.TestCase):
    setUp = retry_fixtures.GenerationRetryTests.setUp
    answer = staticmethod(retry_fixtures.GenerationRetryTests.answer)
    preview = retry_fixtures.GenerationRetryTests.preview
    start_fixture = retry_fixtures.GenerationRetryTests.start_fixture
    update_profile = retry_fixtures.GenerationRetryTests.update_profile

    def test_frozen_v10_individual_retry_preserves_original_directive_across_profile_change(self):
        self.update_profile(reasoning_effort="none")
        original = self.start_fixture()
        self.update_profile(reasoning_effort=None)
        retried = self.start_fixture(retry_of_job_id=original["id"])
        self.assertEqual(original["context"]["messages"], retried["context"]["messages"])
        self.assertEqual(retried["context"]["thinking_control"]["reasoning_effort"], "none")
        self.assertIsNone(retried["profile"]["reasoning_effort"])
        before = self.manager.path.read_bytes()
        loaded = GenerationManager(self.store)
        self.addCleanup(loaded.close)
        self.assertEqual(loaded.path.read_bytes(), before)
        self.assertEqual(loaded.job(retried["id"])["context"]["thinking_control"], original["context"]["thinking_control"])
        fresh = self.manager.preview("node-producer", self.store.envelope()["revision"]["id"])
        self.assertNotIn("/no_think", json.dumps(fresh["messages"]))


if __name__ == "__main__":
    unittest.main()

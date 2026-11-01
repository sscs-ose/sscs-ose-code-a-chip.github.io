"""Software checks of request budgets and original-job freshness; no model."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.context import build_node_context, node_fingerprint
from hullcirq.domain import DomainError
from hullcirq.generation import scheduler_live_source_error
from hullcirq.provider import ChatCompletionsClient, estimate_message_input
from hullcirq.verification import build_verification_plan


class NodeBudgetGuardTests(unittest.TestCase):
    def test_transport_budget_counts_exact_serialization_including_unicode(self):
        messages = [{"role": "system", "content": "仕様: 入出力"}, {"role": "user", "content": "Return complete RTL."}]
        expected = len(json.dumps(messages, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        self.assertEqual(estimate_message_input(messages), expected)
        self.assertGreater(expected, len(json.dumps(messages, ensure_ascii=False, separators=(",", ":")).encode("utf-8")))

    def test_transport_rejects_one_byte_over_budget_before_connecting(self):
        from test_m2_provider import profile
        messages = [{"role": "user", "content": "a" * 80}]
        client = ChatCompletionsClient(profile(context_window=estimate_message_input(messages) + 31, max_output_tokens=32))
        with patch.object(client, "_connection") as connection:
            with self.assertRaises(DomainError) as error:
                client.generate(messages)
        self.assertEqual(error.exception.code, "context_limit")
        connection.assert_not_called()

    def test_old_context_preview_and_transport_share_the_budget_guard(self):
        from test_generation_retry import GenerationRetryTests
        fixture = GenerationRetryTests("test_omitted_or_null_retry_keeps_legacy_hash_and_schema")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        manager, store = fixture.manager, fixture.store
        envelope = store.envelope()
        context = build_node_context(envelope["design"], envelope["revision"]["id"], "node-producer", template_version="node-verilog-2005-v8")
        amount = estimate_message_input(context["messages"])
        record = manager.envelope()["llm"]
        candidate = copy.deepcopy(record["profile"])
        candidate["context_window"] = amount + candidate["max_output_tokens"] - 1
        manager.save_profile(candidate, record["profile_revision_id"])
        with patch("hullcirq.generation.build_node_context", return_value=context):
            with self.assertRaises(DomainError) as error:
                manager.preview("node-producer", envelope["revision"]["id"])
            self.assertEqual(error.exception.code, "context_budget")
            candidate["context_window"] += 1
            manager.save_profile(candidate, manager.envelope()["llm"]["profile_revision_id"])
            preview = manager.preview("node-producer", envelope["revision"]["id"])
        self.assertEqual(preview["provider_input_estimated_tokens"], amount)
        self.assertNotIn("provider_input_estimated_tokens", context)

    def test_changed_global_job_invalidates_derived_buffer_proof_even_with_same_node_hash(self):
        design = json.loads((ROOT / "examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))
        plan = build_verification_plan(design, "npu2-buffer")
        job = {"verification_plan": plan, "node_id": "npu2-buffer"}
        self.assertIsNone(scheduler_live_source_error(design, job))
        changed = copy.deepcopy(design)
        changed["verification_jobs"][0]["A"][0][0] += 1
        self.assertEqual(node_fingerprint(design, "npu2-buffer"), node_fingerprint(changed, "npu2-buffer"))
        self.assertIsNotNone(scheduler_live_source_error(changed, job))


if __name__ == "__main__":
    unittest.main()

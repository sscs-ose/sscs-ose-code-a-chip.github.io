"""Versioned completion guidance; software evidence, never generated RTL."""

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.context import build_node_context


class PromptCompletionTests(unittest.TestCase):
    def test_historical_v1_to_v9_context_bytes_remain_exact(self):
        # Captured from the pre-v9 implementation, including full source,
        # repair input, prompt rendering and projection metadata.
        hashes = [
            "206cada1ac565f6a02219859efe15e3daef13b05c3460396903827255ef21430",
            "b8cef82f24ff87d36add095574faea5bc1f9d650533112ea87c37bbd474aa886",
            "13f80c2b1e9dc2c1879e491dfbb6923fe40fd33ab15a621a33e9e037e888215c",
            "5a2360dd1a7febd131649da9cc6ca1ff9b49639853bac4b8ea34578fbfdc8fcc",
            "36606d4ed6eb6eef67185d56b3ea12b23ce2ba03b2289cb6fc55563a969c8aee",
            "01be7bae4e7afa2d2f7d121d2d5f1f7118479a13cb381c24bb09991d6c3fa4ab",
            "e5542fbfa042ee16b21557fba2a00e8fc7d519433cf486145ee6a4b7a9f427da",
            "685a6196aea1c3a707498bfae705de55245fb34e16302e65a70a08c7d1b29cd3",
            # Captured from the frozen pre-I3 V9 source, not from V10.
            "59c15bc600e01ad156e298b111a75ced63e1ce88d9c1e5ad3712b160e300b636",
        ]
        design = json.loads((ROOT / "examples/m1_two_nodes.json").read_text(encoding="utf-8"))
        for version, expected in enumerate(hashes, start=1):
            with self.subTest(version=version):
                context = build_node_context(
                    design, "historical-regression", "node-producer", "Keep original behavior.",
                    "  module prior;\n // newline retained\n endmodule\n",
                    [{"message": "Original diagnostic."}], f"node-verilog-2005-v{version}")
                actual = hashlib.sha256(json.dumps(context, sort_keys=True, separators=(",", ":"),
                                                   ensure_ascii=False).encode()).hexdigest()
                self.assertEqual(actual, expected)

    def test_historical_v9_preserves_buffer_hardware_requirements_and_exact_interface(self):
        design = json.loads((ROOT / "examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))
        original = copy.deepcopy(design)
        old = build_node_context(design, "unchanged-source", "npu2-buffer", template_version="node-verilog-2005-v8")
        new = build_node_context(design, "unchanged-source", "npu2-buffer", template_version="node-verilog-2005-v9")
        self.assertEqual(new["prompt_template_version"], "node-verilog-2005-v9")
        for field in ("context", "interface", "node_input_hash", "requested_module_header", "prompt_projection"):
            self.assertEqual(new[field], old[field], field)
        old_payload, _ = json.JSONDecoder().raw_decode(old["messages"][1]["content"])
        new_payload, _ = json.JSONDecoder().raw_decode(new["messages"][1]["content"])
        self.assertEqual(new_payload, old_payload)
        self.assertEqual(new_payload["design_context"]["node"]["behavior"],
                         next(node for node in design["nodes"] if node["id"] == "npu2-buffer")["behavior"])
        message = new["messages"][1]["content"]
        self.assertEqual(message.count(new["requested_module_header"]), 1)
        self.assertIn("implement the behavior body immediately", message)
        self.assertIn("Do not list hypothetical signals", message)
        self.assertIn("emit endmodule and the closing fence", message)
        self.assertEqual(design, original)

    def test_v9_budget_matches_provider_message_serialization(self):
        design = json.loads((ROOT / "examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))
        context = build_node_context(design, "unchanged-source", "npu2-buffer", "Keep all saved requirements. 回路", template_version="node-verilog-2005-v9")
        expected = len(json.dumps(context["messages"], ensure_ascii=False, allow_nan=False).encode("utf-8"))
        self.assertEqual(context["estimated_input_tokens"], expected)
        self.assertGreater(expected, len(context["prompt_text"].encode("utf-8")))

    def test_v9_repair_preserves_candidate_newlines_diagnostics_and_instruction_once(self):
        design = json.loads((ROOT / "examples/npu_project.json").read_text(encoding="utf-8"))
        previous = "  module prior;\n    // previous comment\n    wire used;\n endmodule\n"
        diagnostics = [{"code": "original-error", "message": "Retain the failure detail."}]
        instruction = "Apply the original correction without modifying the saved contract."
        new = build_node_context(design, "unchanged-source", "node-pe", instruction, previous, diagnostics, template_version="node-verilog-2005-v9")
        old = build_node_context(design, "unchanged-source", "node-pe", instruction, previous, diagnostics,
                                 template_version="node-verilog-2005-v8")
        payload, _ = json.JSONDecoder().raw_decode(new["messages"][1]["content"])
        self.assertEqual(payload["previous_rtl"], "\n".join(line.strip() for line in previous.split("\n")))
        self.assertEqual(payload["selected_diagnostics"], diagnostics)
        self.assertEqual(new["messages"][1]["content"].count(instruction), 1)
        self.assertEqual(new["context"], old["context"])
        self.assertEqual(new["prompt_projection"], old["prompt_projection"])
        self.assertEqual(new["messages"][1]["content"].removesuffix("\n/no_think").split("\nComplete-output requirements:")[0],
                         old["messages"][1]["content"].removesuffix("\n/no_think"))


if __name__ == "__main__":
    unittest.main()

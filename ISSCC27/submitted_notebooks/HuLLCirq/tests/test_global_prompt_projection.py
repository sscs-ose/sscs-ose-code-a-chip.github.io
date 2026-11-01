"""Versioned, lossless S08 prompt QA; all model/proof records are software fixtures."""
from __future__ import annotations
import copy
import json
import unittest
from unittest.mock import patch

import test_global_generation as qa
from hullcirq.context import physical_interface
from hullcirq.domain import DomainError
from hullcirq.global_generation import (ALGORITHM, PROMPT_TEMPLATE_V1, PROMPT_TEMPLATE_V2,
    PROMPT_TEMPLATE_V3, PROMPT_TEMPLATE_V4, PROMPT_PROJECTIONS, integration_messages,
    integration_projection, prompt_template)
from hullcirq.store import strict_loads
from hullcirq.verification import object_hash


class GlobalPromptProjectionTests(unittest.TestCase):
    def setUp(self):
        self.qa = qa.GlobalSoftwareTests("test_manifest_exact_sources_and_prompt_excludes_numeric_test_job")
        self.qa.setUp(); self.addCleanup(self.qa.doCleanups)

    def test_v1_golden_prompt_and_v2_preserve_headers_algorithm_and_plan(self):
        manifest = self.qa.manager.source_manifest(); original = copy.deepcopy(manifest)
        v1 = integration_messages(manifest, "", template_version=PROMPT_TEMPLATE_V1)
        self.assertEqual(object_hash(v1), "7da9ac412f99d405d1213cb0e32139dba265367bf54eebace4d13670c2661411")
        v2 = integration_messages(manifest, "", template_version=PROMPT_TEMPLATE_V2)
        a = integration_projection(manifest, PROMPT_TEMPLATE_V1)
        b = integration_projection(manifest, PROMPT_TEMPLATE_V2)
        self.assertEqual(a["top"], b["top"]); self.assertEqual(a["adopted_modules"], b["adopted_modules"])
        self.assertIn(ALGORITHM, v1[-1]["content"]); self.assertIn(ALGORITHM, v2[-1]["content"])
        self.assertEqual(manifest, original)
        self.assertLessEqual(len(json.dumps(v2, ensure_ascii=False).encode()), 7500)
        self.assertGreaterEqual(len(json.dumps(v1, ensure_ascii=False).encode()) - len(json.dumps(v2, ensure_ascii=False).encode()), 1500)
        preview = self.qa.manager.preview(self.qa.store.envelope()["revision"]["id"])
        self.assertEqual(preview["template_version"], PROMPT_TEMPLATE_V2)
        self.assertEqual(preview["verification_plan"]["kind"], PROMPT_TEMPLATE_V1)
        self.assertEqual(preview["prompt_projection_sha256"], object_hash(b))

    def test_edge_projection_lossless_full_language_protocol_endpoints_and_extensions(self):
        manifest = self.qa.manager.source_manifest(); manifest = copy.deepcopy(manifest)
        manifest["design"]["edges"][0]["behavior"] += "\n日本語; keep punctuation!  Spaces and newline remain."
        manifest["design"]["edges"][0]["integration_constraints"] = {"lanes": 16, "notes": ["Full custom semantics.", "No dropping."]}
        manifest["design"]["edges"][0]["source"]["annotation"] = {"keep": True, "typed": [4, 4.0, "four"], "language": "端点の意味"}
        manifest["design"]["edges"][0]["target"]["constraint"] = ["receiver extension", {"limit": 2}]
        before = object_hash(manifest); projection = integration_projection(manifest)
        nodes = {n["id"]: n for n in manifest["design"]["nodes"]}
        self.assertEqual(len(projection["edges"]), len(manifest["design"]["edges"]))
        for original, row in zip(manifest["design"]["edges"], projection["edges"]):
            for endpoint, reference in zip(row[:2], (original["source"], original["target"])):
                node = nodes[reference["node_id"]]
                port = next(p for p in node["ports"] if p["id"] == reference["port_id"])
                self.assertEqual(endpoint, node["module_name"] + "." + port["name"])
            self.assertEqual(row[2], original["protocol"])
            self.assertEqual("".join(projection["edge_language"][i] for i in row[3]), original["behavior"])
            expected = {k: v for k, v in original.items() if k not in ("id", "source", "target", "protocol", "behavior")}
            for side in ("source", "target"):
                extra = {k: v for k, v in original[side].items() if k not in ("node_id", "port_id")}
                if extra:
                    expected[side] = extra
            self.assertEqual(object_hash(row[4] if len(row) == 5 else {}), object_hash(expected))
        self.assertEqual(object_hash(manifest), before)
        self.assertLess(len(projection["edge_language"]), sum(len(row[3]) for row in projection["edges"]))

    def test_five_legacy_records_reopen_unchanged_then_v2_repair_reopens(self):
        with patch("hullcirq.global_generation.PROMPT_TEMPLATE", PROMPT_TEMPLATE_V1):
            for _ in range(5):
                job = self.qa.run_job()
        legacy = copy.deepcopy(self.qa.manager._state["jobs"])
        self.assertTrue(all(j["context"]["template_version"] == PROMPT_TEMPLATE_V1 for j in legacy))
        self.assertTrue(all("prompt_projection_sha256" not in j["context"] for j in legacy))
        restored = self.qa.new_manager(); self.qa.addCleanup(restored.close); self.qa.manager = restored
        self.assertEqual(object_hash(restored._state["jobs"]), object_hash(legacy))
        repaired = self.qa.run_job(operation="repair", base=job["id"], instruction="SOFTWARE QA explicit correction")
        self.assertEqual(repaired["context"]["template_version"], PROMPT_TEMPLATE_V2)
        final = self.qa.new_manager(); self.qa.addCleanup(final.close)
        self.assertEqual(object_hash(final._state["jobs"][:5]), object_hash(legacy))
        self.assertEqual(final.job(repaired["id"])["context"], repaired["context"])

    def test_repair_text_and_diagnostics_are_complete_and_budget_boundary_unchanged(self):
        base = self.qa.run_job()
        stored = self.qa.manager._job(base["id"])
        stored["diagnostics"] = [{"code": "software_qa", "message": "full diagnostic repeated\n日本語"}] * 7
        instruction = "Keep every diagnostic and the complete previous source."
        p = self.qa.sources.profile["profile"]; p["max_output_tokens"] = 2048
        expected = integration_messages(base["context"]["source_manifest"], instruction, stored)
        count = len(json.dumps(expected, ensure_ascii=False, allow_nan=False).encode())
        p["context_window"] = count + 2048
        preview = self.qa.manager.preview(base["revision_id"], "repair", base["id"], instruction)
        self.assertEqual(preview["estimated_input_tokens"], count)
        self.assertEqual(preview["token_estimate_method"], "conservative_one_UTF8_byte_per_token")
        self.assertEqual(preview["messages"], expected)
        self.assertIn(stored["rtl"], expected[-1]["content"])
        self.assertIn(json.dumps(stored["diagnostics"], ensure_ascii=False), expected[-1]["content"])
        self.assertEqual(expected[-1]["content"].count("full diagnostic repeated"), 7)
        p["context_window"] -= 1
        with self.assertRaises(DomainError) as raised:
            self.qa.manager.preview(base["revision_id"], "repair", base["id"], instruction)
        self.assertEqual(raised.exception.code, "global_context_budget")

    def test_explicit_v3_golden_is_unchanged_and_v4_ends_with_exact_repair_correction(self):
        design = json.loads((qa.PROJECT / "examples" / "npu_2x2_explicit_project.json").read_text(encoding="utf-8"))
        manifest = {"design": design, "nodes": [
            {"public_interface": physical_interface(design, node)} for node in design["nodes"]
        ]}
        base = {"rtl": "module retained_top; wire keep; endmodule\n", "diagnostics": [
            {"code": "implicit_net", "message": "Exact width lost."},
            {"code": "load_gate", "message": "Preserve buffer ready."},
        ]}
        instruction = "Use exact named ports."

        legacy = integration_messages(manifest, instruction, base, PROMPT_TEMPLATE_V3)
        self.assertEqual(object_hash(legacy), "9276c11067077ee7ad0ab94532aced493512529d8361fedb07a58d00ebc91228")
        self.assertLess(legacy[-1]["content"].index("Development-assistant/user correction:"),
                        legacy[-1]["content"].index("Previous top:"))

        current = integration_messages(manifest, instruction, base, PROMPT_TEMPLATE_V4)
        content = current[-1]["content"]
        final = "Development-assistant/user correction (final instruction): " + instruction
        self.assertEqual(prompt_template(design), PROMPT_TEMPLATE_V4)
        self.assertEqual(object_hash(integration_projection(manifest, PROMPT_TEMPLATE_V3)),
                         object_hash(integration_projection(manifest, PROMPT_TEMPLATE_V4)))
        self.assertIn(base["rtl"], content)
        self.assertIn(json.dumps(base["diagnostics"], ensure_ascii=False), content)
        self.assertEqual(content.count(instruction), 1)
        self.assertLess(content.index("Previous top:"), content.index("Recorded diagnostics:"))
        self.assertLess(content.index("Recorded diagnostics:"), content.index(final))
        self.assertTrue(content.endswith(final))

    def test_checksum_updated_prompt_version_projection_and_estimate_tampering_rejected(self):
        self.qa.run_job(); original = self.qa.manager.path.read_bytes()
        def alter_language(context):
            projection = json.loads(context["messages"][-1]["content"].split("\n", 1)[0])
            projection["edge_language"][0] = "Truncated or substituted edge language."
            context["prompt_projection_sha256"] = object_hash(projection)
            context["messages"][-1]["content"] = json.dumps(projection, separators=(",", ":"), ensure_ascii=False) + "\n" + context["messages"][-1]["content"].split("\n", 1)[1]
        for mutation in (alter_language,
            lambda c: c.update(template_version=PROMPT_TEMPLATE_V1, prompt_projection=PROMPT_PROJECTIONS[PROMPT_TEMPLATE_V1]),
            lambda c: c.update(template_version="unknown_prompt_v99"),
            lambda c: c.update(prompt_projection_sha256="forged"),
            lambda c: c.update(estimated_input_tokens=c["estimated_input_tokens"] + 1)):
            state = strict_loads(original.decode()); job = state["jobs"][0]; context = job["context"]; mutation(context)
            context["context_id"] = object_hash({k: v for k, v in context.items() if k != "context_id"}); job["context_id"] = context["context_id"]
            job["record_hash"] = object_hash({k: v for k, v in job.items() if k != "record_hash"})
            self.qa.manager.path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
            saved = self.qa.manager.path.read_bytes()
            with self.subTest(mutation=mutation), self.assertRaises(DomainError):
                self.qa.new_manager()
            self.assertEqual(self.qa.manager.path.read_bytes(), saved)
        self.qa.manager.path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()

"""Same saved GUI input across S06 builders; no model or live store mutation."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.context import node_fingerprint
from hullcirq.domain import DomainError
from hullcirq.verification import build_verification_plan, validate_plan, verification_template_version
from hullcirq.workflow import ensure_current_verification_plan


class Npu2VerificationIntegrationTests(unittest.TestCase):
    def source(self):
        return json.loads((ROOT / "examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))

    def test_all_eleven_plans_rebuild_from_one_unchanged_gui_job(self):
        source = self.source()
        original = copy.deepcopy(source)
        self.assertEqual(len(source["nodes"]), 11)
        for node in source["nodes"]:
            with self.subTest(node=node["id"]):
                plan = build_verification_plan(source, node["id"])
                validate_plan(plan)
                self.assertEqual(plan, build_verification_plan(source, node["id"], verification_template_version(plan)))
                self.assertEqual(plan["contract"]["source_job"], source["verification_jobs"][0])
                ensure_current_verification_plan(source, node["id"], plan)
        self.assertEqual(source, original)

    def test_changed_global_job_cannot_reuse_any_old_node_verification(self):
        original = self.source()
        changed = copy.deepcopy(original)
        changed["verification_jobs"][0]["A"][0][0] += 1
        for node in original["nodes"]:
            with self.subTest(node=node["id"]):
                # The historical S04 fingerprint intentionally does not cover
                # global numerical jobs. S06 must check that source separately.
                self.assertEqual(node_fingerprint(original, node["id"]), node_fingerprint(changed, node["id"]))
                plan = build_verification_plan(original, node["id"])
                with self.assertRaises(DomainError):
                    ensure_current_verification_plan(changed, node["id"], plan)

    def test_new_supported_nodes_reject_changed_behavior_and_wrong_template(self):
        source = self.source()
        for node in source["nodes"]:
            if node["id"] in ("npu2-control", "npu2-buffer", "npu2-fifo"):
                continue
            with self.subTest(node=node["id"]):
                plan = build_verification_plan(source, node["id"])
                changed = copy.deepcopy(source)
                next(n for n in changed["nodes"] if n["id"] == node["id"])["behavior"] += " Changed contract."
                with self.assertRaises(DomainError):
                    build_verification_plan(changed, node["id"])
                plan["testbench_template_version"] = "unknown-template"
                with self.assertRaises(DomainError):
                    verification_template_version(plan)
                with self.assertRaises(DomainError):
                    validate_plan(plan)


if __name__ == "__main__":
    unittest.main()

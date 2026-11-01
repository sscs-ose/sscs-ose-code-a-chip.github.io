"""S04 interface admission QA; providers are fixtures and no EDA tool runs."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.domain import IMPLEMENTED_STAGES, DomainError
from hullcirq.generation import GenerationManager, LOCAL_RTL_VALIDATION_SCOPE, request_hash
from hullcirq.rtl_checks import check_rtl
from hullcirq.store import ProjectStore
from test_adoption_policy import design_fixture, software_profile


class S04ScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".work")
        self.addCleanup(self.temp.cleanup)
        self.store = ProjectStore(self.temp.name)
        self.store.save(design_fixture(with_contract=False), self.store.envelope()["revision"]["id"])
        self.store.set_review_policy("accept_on_pass", True, "Software fixture authorization", self.store.review_policy()["id"])
        self.revision = self.store.envelope()["revision"]["id"]
        for stage in IMPLEMENTED_STAGES:
            self.store.validate(stage, self.revision)
        self.manager = GenerationManager(self.store)
        self.addCleanup(lambda: self.manager.close())
        self.manager.save_profile(software_profile())

    def generate(self, transform=lambda text: text):
        preview = self.manager.preview("node-producer", self.revision)
        rtl = transform(preview["requested_module_header"] + "endmodule\n")
        with patch("hullcirq.generation.ChatCompletionsClient") as provider, \
                patch("hullcirq.generation.verify_behavior") as behavior, \
                patch("hullcirq.rtl_checks._syntax_check") as compiler:
            provider.return_value.generate.return_value = {"execution_status": "Completed", "raw_content": "```verilog\n" + rtl + "```", "error": None}
            result = self.manager.start("node-producer", self.revision, preview["context_id"], preview["profile_revision_id"])
            self.manager._worker.join(10)
            self.assertFalse(self.manager._worker.is_alive())
            behavior.assert_not_called()
            compiler.assert_not_called()
        return self.manager.job(result["generation"]["latest_job_id"])

    def test_new_generation_requires_only_interface_without_compiler_or_behavior_adapter(self):
        job = self.generate()
        self.assertEqual((job["execution_status"], job["validation_status"], job["review_status"]), ("Completed", "Passed", "Accepted"))
        self.assertEqual(job["validation_scope"], LOCAL_RTL_VALIDATION_SCOPE)
        self.assertEqual(job["stage_validation"]["scope"], "external_interface")
        self.assertTrue(job["stage_validation"]["available"])
        self.assertIsNone(job["verification_plan"])
        self.assertIsNone(job["verification_plan_error"])
        self.assertEqual(job["checks"]["syntax"]["deferred_to_stage"], "local_synthesis")
        self.assertEqual(job["checks"]["behavioral"]["deferred_to_stage"], "local_netlist_simulation")
        self.assertEqual(job["checks"]["behavioral"]["validation_status"], "Not Run")
        self.assertEqual(self.manager._state["reviews"][-1]["validation_scope"], LOCAL_RTL_VALIDATION_SCOPE)
        before = self.manager.path.read_bytes()
        self.manager.close()
        loaded = GenerationManager(ProjectStore(self.temp.name))
        self.addCleanup(loaded.close)
        self.assertEqual(loaded.path.read_bytes(), before)
        self.assertEqual(loaded.job(job["id"])["review_status"], "Accepted")

    def test_port_name_mismatch_blocks_generation_adoption(self):
        job = self.generate(lambda rtl: rtl.replace("acc_data", "wrong_data"))
        self.assertEqual(job["checks"]["interface"]["validation_status"], "Failed")
        self.assertEqual(job["review_status"], "Awaiting Review")
        with self.assertRaises(DomainError) as error:
            self.manager.review(job["id"], "accepted", "Cannot override missing required ports")
        self.assertEqual(error.exception.code, "verification_failed")

    def test_interface_match_is_not_a_claim_of_syntax_or_behavior(self):
        job = self.generate(lambda rtl: rtl.replace("endmodule", "always @(posedge clk) begin broken <= ; end\nendmodule"))
        self.assertEqual(job["validation_status"], "Passed")
        self.assertEqual(job["checks"]["syntax"]["validation_status"], "Not Run")
        self.assertFalse(job["checks"]["syntax"]["executed"])
        self.assertFalse(job["checks"]["behavioral"]["executed"])

    def test_legacy_failed_behavior_keeps_raw_evidence_and_gets_scoped_review(self):
        self.store.set_review_policy("manual", False, "No automatic adoption", self.store.review_policy()["id"])
        generated = self.generate()
        job = self.manager._stored_job(generated["id"])
        # Construct a legacy record with no scoped request marker. Its saved
        # failure remains a behavioral result, not S04 external-interface proof.
        job.pop("validation_scope")
        job["context"].pop("validation_scope")
        job["context_id"] = request_hash(job["context"], job["profile_revision_id"], job["parameters"], job["operation"], job["base_job_id"])
        job["validation_status"] = "Failed"
        job["checks"]["syntax"] = {"validation_status": "Passed", "executed": True, "exit_code": 0}
        job["checks"]["behavioral"] = {"validation_status": "Failed", "executed": True, "exit_code": 1, "diagnostics": []}
        self.manager._persist()
        evidence = copy.deepcopy({key: job[key] for key in ("checks", "validation_status", "context", "rtl", "raw_content", "verification_plan")})
        before = self.manager.path.read_bytes()
        view = self.manager.job(job["id"])
        self.assertEqual(view["validation_status"], "Failed")
        self.assertEqual(view["effective_validation_status"], "Passed")
        self.assertEqual(self.manager.path.read_bytes(), before)
        self.manager.review(job["id"], "accepted", "Accept current S04 port contract; behavior remains S06 work")
        self.assertEqual({key: self.manager._stored_job(job["id"])[key] for key in evidence}, evidence)
        self.manager.close()
        loaded = GenerationManager(ProjectStore(self.temp.name))
        self.addCleanup(loaded.close)
        self.assertEqual(loaded.job(job["id"])["review_status"], "Accepted")
        self.assertEqual(loaded.job(job["id"])["validation_status"], "Failed")

    def test_new_scope_is_bound_to_context_hash(self):
        job = self.generate()
        self.manager.close()
        saved = json.loads(self.manager.path.read_text(encoding="utf-8"))
        saved["jobs"][0]["context"].pop("validation_scope")
        self.manager.path.write_text(json.dumps(saved), encoding="utf-8")
        before = self.manager.path.read_bytes()
        with self.assertRaises(DomainError) as error:
            GenerationManager(ProjectStore(self.temp.name))
        self.assertEqual(error.exception.code, "invalid_generation_store")
        self.assertEqual(self.manager.path.read_bytes(), before)

    def test_legacy_default_check_still_compiles_when_explicitly_requested(self):
        interface = {"ports": [{"name": "clk", "direction": "input", "width": 1, "signed": False}]}
        with patch("hullcirq.rtl_checks._syntax_check", return_value={"validation_status": "Passed", "executed": True, "exit_code": 0, "diagnostics": []}) as compiler:
            result = check_rtl("module dut(input clk); endmodule", interface, "dut", {"fixture": True})
        compiler.assert_called_once()
        self.assertEqual(result["validation_status"], "Passed")


if __name__ == "__main__":
    unittest.main()

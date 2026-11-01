"""Software QA of frozen contract continuity; fixtures are not model evidence."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.context import node_fingerprint
from hullcirq.domain import DomainError
from hullcirq.store import ProjectStore
from hullcirq.verification import build_verification_plan, content_hash, object_hash, reference_trace, validate_plan, verify_behavior, verification_template_version
from hullcirq.workflow import WorkflowManager, SCOPE_VERSION

SOFTWARE_FIXTURE_RTL = """module m2a_mac(
 input wire clk, input wire rst,
 input wire [15:0] pair_data, input wire pair_data_valid, output wire pair_data_ready,
 output wire signed [31:0] acc_data, output wire acc_data_valid, input wire acc_data_ready
);
 reg signed [31:0] accumulator; reg signed [31:0] data_reg; reg valid_reg;
 wire signed [7:0] a = pair_data[7:0]; wire signed [7:0] b = pair_data[15:8];
 wire signed [15:0] product = a * b;
 wire signed [31:0] next_acc = accumulator + {{16{product[15]}},product};
 assign pair_data_ready = !valid_reg || acc_data_ready;
 assign acc_data = data_reg; assign acc_data_valid = valid_reg;
 always @(posedge clk) begin
  if (rst) begin accumulator <= 0; data_reg <= 0; valid_reg <= 0; end
  else if (pair_data_valid && pair_data_ready) begin accumulator <= next_acc; data_reg <= next_acc; valid_reg <= 1; end
  else if (valid_reg && acc_data_ready) valid_reg <= 0;
 end
endmodule
"""


def original_design():
    design = json.loads((PROJECT / "examples" / "m2a_mac_node.json").read_text(encoding="utf-8"))
    node = design["nodes"][0]
    node["verification"] = {"kind": "int8_mac_stream", "version": 1, "input_port": "pair_data", "output_port": "acc_data",
                            "accumulator_width": 32, "initial_accumulator": 0,
                            "vectors": [{"reset": reset, "input_valid": valid, "output_ready": ready, "input_data": data}
                                        for reset, valid, ready, data in ((1, 0, 0, 0), (0, 1, 0, 0x0302), (0, 1, 0, 0x0504),
                                                                         (0, 1, 1, 0x07FD), (0, 0, 1, 0), (0, 1, 0, 0x8080),
                                                                         (1, 1, 0, 0x0101), (0, 1, 1, 0x807F))]}
    return design


class OriginalContractTests(unittest.TestCase):
    def test_signed_products_stalls_replacement_and_reset_match_independent_values(self):
        plan = build_verification_plan(original_design(), "node-mac")
        self.assertEqual([item["after"]["output_data"] for item in plan["reference_trace"]],
                         [0, 6, 6, 0xFFFFFFF1, 0xFFFFFFF1, 16369, 0, 0xFFFFC080])
        self.assertEqual([item["after"]["output_valid"] for item in plan["reference_trace"]], [0, 1, 1, 1, 0, 1, 0, 1])
        self.assertGreater(plan["coverage"]["stall_cycles"], 0)
        self.assertGreater(plan["coverage"]["simultaneous_transfers"], 0)
        self.assertEqual(plan["stimulus_origin"], "original_design_node.verification.vectors")
        validate_plan(plan)

    def test_layout_changes_do_not_change_original_vectors_or_testbench(self):
        design = original_design()
        plan = build_verification_plan(design, "node-mac")
        design["layout"]["nodes"]["node-mac"]["x"] += 50
        self.assertEqual(build_verification_plan(design, "node-mac"), plan)

    def test_modified_vector_changes_plan_and_tampered_frozen_testbench_is_rejected(self):
        design = original_design()
        plan = build_verification_plan(design, "node-mac")
        design["nodes"][0]["verification"]["vectors"][1]["input_data"] = 0x0402
        changed = build_verification_plan(design, "node-mac")
        self.assertNotEqual(changed["vector_hash"], plan["vector_hash"])
        self.assertNotEqual(changed["testbench_sha256"], plan["testbench_sha256"])
        plan["testbench"] += "// A stage-specific modification.\n"
        with self.assertRaises(DomainError):
            validate_plan(plan)

    def test_missing_malformed_or_unsupported_contract_never_becomes_passed(self):
        design = original_design()
        for change in (lambda contract: contract.update(version=2), lambda contract: contract.update(accumulator_width=16),
                       lambda contract: contract["vectors"][0].update(reset=0), lambda contract: contract["vectors"][1].update(input_data=65536),
                       lambda contract: contract["vectors"][1].update(input_valid="1")):
            changed = copy.deepcopy(design)
            change(changed["nodes"][0]["verification"])
            with self.subTest(contract=changed["nodes"][0]["verification"]), self.assertRaises(DomainError):
                build_verification_plan(changed, "node-mac")
        del design["nodes"][0]["verification"]
        with self.assertRaises(DomainError):
            build_verification_plan(design, "node-mac")

    def test_missing_compiler_is_unsupported_and_has_no_execution_evidence(self):
        result = verify_behavior(SOFTWARE_FIXTURE_RTL, build_verification_plan(original_design(), "node-mac"), None)
        self.assertEqual(result["validation_status"], "Unsupported")
        self.assertFalse(result["executed"])
        self.assertEqual(result["commands"], [])

    def test_frozen_initialization_templates_remain_readable_without_rewriting_evidence(self):
        design = original_design()
        for version in ("legacy-bootstrap-v1", "original-vectors-v1", "original-vectors-v2"):
            plan = build_verification_plan(design, "node-mac", version)
            original_bytes = json.dumps(plan, ensure_ascii=False, sort_keys=True).encode()
            restored = json.loads(original_bytes)
            validate_plan(restored)
            self.assertEqual(verification_template_version(restored), version)
            self.assertEqual(build_verification_plan(design, "node-mac", verification_template_version(restored)), restored)
            self.assertEqual(json.dumps(restored, ensure_ascii=False, sort_keys=True).encode(), original_bytes)
        latest = build_verification_plan(design, "node-mac")
        self.assertNotIn("// Initialize the synchronous state before checking the first vector.", latest["testbench"])
        self.assertNotIn("cycle=0 phase=before", latest["testbench"])
        self.assertIn("cycle=0 phase=after", latest["testbench"])
        self.assertEqual(latest["initialization_origin"], "first_original_design_vector_asserting_synchronous_reset")


class SoftwareGenerationFixture:
    """Explicit software fixture; no model or actual compiler claim."""
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        state = store.envelope()
        self.candidate = {"id": "software-fixture-candidate", "node_id": "node-mac", "revision_id": state["revision"]["id"],
                          "input_hash": node_fingerprint(state["design"], "node-mac"), "rtl": SOFTWARE_FIXTURE_RTL,
                          "verification_plan": build_verification_plan(state["design"], "node-mac"),
                          "execution_status": "Completed", "validation_status": "Passed", "review_status": "Accepted",
                          "checks": {"behavioral": {"validation_status": "Passed", "executed": True, "evidence": "software fixture only"}}}

    @property
    def _state(self):
        return {"jobs": [self.candidate]}

    def envelope(self):
        """Supply the actual generation read contract used by node summaries."""
        candidate = self.job(self.candidate["id"])
        return {"generation": {"nodes": [
            {"node_id": node["id"],
             "latest_job_id": candidate["id"] if node["id"] == candidate["node_id"] else None,
             "accepted_job_id": candidate["id"] if node["id"] == candidate["node_id"]
                 and candidate["freshness"] == "Current" and candidate["review_status"] == "Accepted" else None}
            for node in self.store.envelope()["design"]["nodes"]]}}

    def job(self, identifier):
        if identifier != self.candidate["id"]:
            raise DomainError("job_not_found", "Unknown software fixture candidate.", 404)
        result = copy.deepcopy(self.candidate)
        result["freshness"] = "Current" if result["input_hash"] == node_fingerprint(self.store.envelope()["design"], "node-mac") else "Stale"
        return result


class FrozenFlowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        input_path = Path(self.temporary.name) / "original.json"
        input_path.write_text(json.dumps(original_design()), encoding="utf-8")
        self.store = ProjectStore(Path(self.temporary.name) / "project", input_path)
        self.adopt_inputs()
        self.generation = SoftwareGenerationFixture(self.store)
        self.manager = WorkflowManager(self.store, self.generation)
        self.addCleanup(lambda: self.manager.close())

    def adopt_inputs(self):
        for stage in ("global_settings", "graph_editor", "specifications"):
            state = self.store.envelope()
            run = self.store.validate(stage, state["revision"]["id"])["runs"][-1]
            self.store.review(run["id"], "accepted", "Software fixture input review.")

    def start(self, stage):
        result = self.manager.start(stage, "node-mac", "software-fixture-candidate", self.store.envelope()["revision"]["id"])
        return result["workflow_runs"][-1]["id"]

    def wait(self, run_id):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            run = self.manager.run(run_id)
            if run["execution_status"] not in ("Queued", "Running") and run["finished_at"] and not self.manager._worker.is_alive():
                return run
            time.sleep(0.01)
        self.fail("Software fixture workflow did not settle.")

    @staticmethod
    def software_synthesis(rtl, module_name, *args):
        return {"validation_status": "Passed", "executed": True, "exit_code": 0, "diagnostics": [], "netlist": rtl,
                "netlist_sha256": content_hash(rtl), "scope": "software_fixture_no_actual_synthesis"}

    def test_original_testbench_is_frozen_at_netlist_stage_after_synthesis(self):
        seen = []
        def software_simulation(netlist, plan, *args, record_waveform=False):
            self.assertTrue(record_waveform, "S06 must request measured waveform capture.")
            seen.append(copy.deepcopy(plan))
            return {"validation_status": "Passed", "executed": True, "exit_code": 0, "diagnostics": [], "scope": "software_fixture_no_actual_simulation"}
        with patch("hullcirq.workflow.synthesize_generic", self.software_synthesis), patch("hullcirq.workflow.verify_behavior", software_simulation):
            synthesis = self.wait(self.start("local_synthesis"))
            self.assertEqual(synthesis["review_status"], "Awaiting Review")
            with self.assertRaises(DomainError):
                self.start("local_netlist_simulation")
            self.manager.review(synthesis["id"], "accepted", "Software fixture synthesis review.")
            netlist = self.wait(self.start("local_netlist_simulation"))
            original = self.generation.candidate["verification_plan"]
            self.assertEqual(seen, [original])
            self.assertEqual(synthesis["workflow_scope_version"], SCOPE_VERSION)
            self.assertIsNone(synthesis["verification_plan"])
            self.assertIsNone(synthesis["vector_hash"])
            self.assertIsNone(synthesis["testbench_sha256"])
            self.assertEqual(synthesis["module_name"], "m2a_mac")
            self.assertEqual(netlist["verification_plan"], original)
            self.assertEqual(netlist["vector_hash"], original["vector_hash"])
            self.assertEqual(netlist["testbench_sha256"], original["testbench_sha256"])
            self.assertEqual(netlist["prior_run_id"], synthesis["id"])
            self.assertEqual(netlist["rtl_sha256"], synthesis["rtl_sha256"])
            self.manager.review(netlist["id"], "accepted", "Software fixture netlist review.")
        self.manager.close()
        self.manager = WorkflowManager(self.store, self.generation)
        self.assertEqual(self.manager.run(netlist["id"])["review_status"], "Accepted")

    def test_worker_policy_adopts_durably_without_building_an_unused_history_view(self):
        self.store.set_review_policy("accept_on_pass", True, "Software fixture authorization", self.store.review_policy()["id"])
        with patch("hullcirq.workflow.synthesize_generic", self.software_synthesis), \
                patch.object(self.manager, "_result_envelope", wraps=self.manager._result_envelope) as views:
            run_id = self.start("local_synthesis")
            self.manager._worker.join(3)
            self.assertFalse(self.manager._worker.is_alive())
            run = self.manager.run(run_id)
            self.assertEqual(run["validation_status"], "Passed")
            self.assertEqual(run["review_status"], "Accepted")
            self.assertEqual(views.call_count, 1, "Only the explicit start response needs a full read view")
        self.manager.close()
        self.manager = WorkflowManager(self.store, self.generation)
        self.assertEqual(self.manager.run(run_id)["review_status"], "Accepted")

    def test_synthesis_needs_no_s04_behavior_or_verification_plan(self):
        self.generation.candidate["verification_plan"] = None
        self.generation.candidate["checks"] = {"interface": {"validation_status": "Passed"}}
        with patch("hullcirq.workflow.build_verification_plan", side_effect=AssertionError("S05 must not build a behavioral plan")), \
                patch("hullcirq.workflow.verify_behavior", side_effect=AssertionError("S05 must not simulate behavior")), \
                patch("hullcirq.workflow.synthesize_generic", side_effect=self.software_synthesis) as synthesize:
            synthesis = self.wait(self.start("local_synthesis"))
            self.manager.review(synthesis["id"], "accepted", "Software fixture S05 review.")
            self.assertEqual(synthesize.call_args.args[1], "m2a_mac")
            self.assertEqual(synthesis["validation_status"], "Passed")
            self.assertIsNone(synthesis["verification_plan"])
            self.manager.close()
            self.manager = WorkflowManager(self.store, self.generation)
            self.assertEqual(self.manager.run(synthesis["id"])["review_status"], "Accepted")

    def test_s06_builds_from_saved_input_even_when_s04_has_no_plan(self):
        self.generation.candidate["verification_plan"] = None
        self.generation.candidate["checks"] = {"interface": {"validation_status": "Passed"}}
        with patch("hullcirq.workflow.synthesize_generic", self.software_synthesis):
            synthesis = self.wait(self.start("local_synthesis"))
            self.manager.review(synthesis["id"], "accepted", "Software fixture S05 review.")
        expected = build_verification_plan(self.store.snapshot(self.generation.candidate["revision_id"]), "node-mac")
        def simulate(netlist, plan, *args):
            self.assertEqual(netlist, synthesis["netlist"])
            self.assertEqual(plan, expected)
            return {"validation_status": "Passed", "executed": True, "exit_code": 0, "diagnostics": [], "scope": "software_fixture_no_actual_simulation"}
        with patch("hullcirq.workflow.verify_behavior", simulate):
            simulation = self.wait(self.start("local_netlist_simulation"))
        self.assertEqual(simulation["verification_plan"], expected)
        self.assertEqual(simulation["prior_run_id"], synthesis["id"])
        self.manager.close()
        self.manager = WorkflowManager(self.store, self.generation)
        self.assertEqual(self.manager.run(simulation["id"])["verification_plan"], expected)

    def test_legacy_behavior_unsupported_candidate_uses_current_s04_interface_scope(self):
        self.generation.candidate.update(validation_status="Unsupported", verification_plan=None,
                                         stage_validation={"validation_status": "Passed", "scope": "external_interface"})
        self.generation.candidate["checks"] = {"interface": {"validation_status": "Passed"},
                                                "behavioral": {"validation_status": "Not Run", "executed": False}}
        with patch("hullcirq.workflow.synthesize_generic", self.software_synthesis):
            synthesis = self.wait(self.start("local_synthesis"))
        self.assertEqual(synthesis["validation_status"], "Passed")
        self.assertEqual(self.generation.candidate["validation_status"], "Unsupported", "Historical behavior scope is preserved")

    def test_missing_checker_is_s06_only_and_creates_no_unexecutable_run(self):
        self.generation.candidate["verification_plan"] = None
        self.generation.candidate["checks"] = {"interface": {"validation_status": "Passed"}}
        with patch("hullcirq.workflow.synthesize_generic", self.software_synthesis):
            synthesis = self.wait(self.start("local_synthesis"))
            self.manager.review(synthesis["id"], "accepted", "Software fixture S05 review.")
        original_bytes = self.manager.path.read_bytes()
        with patch("hullcirq.workflow.build_verification_plan", side_effect=DomainError("verification_contract_missing", "No checker for this saved specification.")), \
                patch("hullcirq.workflow.verify_behavior") as simulate, self.assertRaises(DomainError) as caught:
            self.start("local_netlist_simulation")
        self.assertEqual(caught.exception.code, "verification_contract_missing")
        self.assertIn("S06", caught.exception.message)
        simulate.assert_not_called()
        self.assertEqual(self.manager.path.read_bytes(), original_bytes)

    def test_legacy_synthesis_with_original_plan_remains_byte_readable(self):
        with patch("hullcirq.workflow.synthesize_generic", self.software_synthesis):
            synthesis = self.wait(self.start("local_synthesis"))
            self.manager.review(synthesis["id"], "accepted", "Software fixture old S05 review.")
        self.manager.close()
        state = json.loads(self.manager.path.read_text(encoding="utf-8"))
        run = state["runs"][0]
        del run["workflow_scope_version"]
        del run["module_name"]
        plan = self.generation.candidate["verification_plan"]
        run.update(verification_plan=copy.deepcopy(plan), vector_hash=plan["vector_hash"], testbench_sha256=plan["testbench_sha256"])
        run["record_hash"] = object_hash({key: value for key, value in run.items() if key != "record_hash"})
        self.manager.path.write_text(json.dumps(state), encoding="utf-8")
        historical_bytes = self.manager.path.read_bytes()
        self.manager = WorkflowManager(self.store, self.generation)
        self.assertEqual(self.manager.path.read_bytes(), historical_bytes)
        with patch("hullcirq.workflow.verify_behavior", return_value={"validation_status": "Passed", "executed": True, "exit_code": 0, "diagnostics": []}):
            simulation = self.wait(self.start("local_netlist_simulation"))
        self.assertEqual(simulation["verification_plan"], plan)
        self.assertEqual(simulation["prior_run_id"], synthesis["id"])

    def test_recomputed_hash_cannot_hide_changed_module_or_s06_vectors(self):
        self.generation.candidate["verification_plan"] = None
        with patch("hullcirq.workflow.synthesize_generic", self.software_synthesis):
            synthesis = self.wait(self.start("local_synthesis"))
            self.manager.review(synthesis["id"], "accepted", "Software fixture S05 review.")
        self.manager.close()
        clean = json.loads(self.manager.path.read_text(encoding="utf-8"))
        changed = copy.deepcopy(clean)
        changed["runs"][0]["module_name"] = "substituted_module"
        changed["runs"][0]["record_hash"] = object_hash({key: value for key, value in changed["runs"][0].items() if key != "record_hash"})
        self.manager.path.write_text(json.dumps(changed), encoding="utf-8")
        with self.assertRaises(DomainError):
            WorkflowManager(self.store, self.generation)
        self.manager.path.write_text(json.dumps(clean), encoding="utf-8")
        self.manager = WorkflowManager(self.store, self.generation)
        with patch("hullcirq.workflow.verify_behavior", return_value={"validation_status": "Passed", "executed": True, "exit_code": 0, "diagnostics": []}):
            self.wait(self.start("local_netlist_simulation"))
        self.manager.close()
        state = json.loads(self.manager.path.read_text(encoding="utf-8"))
        state["runs"][-1]["vector_hash"] = "invented-vector-hash"
        state["runs"][-1]["record_hash"] = object_hash({key: value for key, value in state["runs"][-1].items() if key != "record_hash"})
        self.manager.path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaises(DomainError):
            WorkflowManager(self.store, self.generation)

    def test_changed_initial_vector_stales_old_evidence_and_blocks_next_stage(self):
        with patch("hullcirq.workflow.synthesize_generic", self.software_synthesis):
            synthesis = self.wait(self.start("local_synthesis"))
            self.manager.review(synthesis["id"], "accepted", "Software fixture review.")
        state = self.store.envelope()
        design = copy.deepcopy(state["design"])
        design["nodes"][0]["verification"]["vectors"][1]["input_data"] = 0x0402
        self.store.save(design, state["revision"]["id"])
        stale = self.manager.run(synthesis["id"])
        self.assertEqual(stale["freshness"], "Stale")
        self.assertEqual(stale["netlist"], synthesis["netlist"])
        with self.assertRaises(DomainError):
            self.start("local_netlist_simulation")

    def test_failed_synthesis_cannot_be_adopted_or_simulated(self):
        run = self.wait(self.start("local_synthesis"))
        self.assertEqual(run["validation_status"], "Unsupported")
        with self.assertRaises(DomainError):
            self.manager.review(run["id"], "accepted", "Cannot adopt unexecuted synthesis.")
        with self.assertRaises(DomainError):
            self.start("local_netlist_simulation")

    def test_explicit_passed_policy_adopts_with_recorded_authorization(self):
        self.store.set_review_policy("accept_on_pass", True, "User-authorized software QA policy.")
        with patch("hullcirq.workflow.synthesize_generic", self.software_synthesis):
            synthesis = self.wait(self.start("local_synthesis"))
        self.assertEqual(synthesis["review_status"], "Accepted")
        review = self.manager.envelope()["workflow_reviews"][-1]
        self.assertEqual(review["actor"], "automation_policy")
        self.assertEqual(review["provenance"]["authorization"], "user_preapproved")
        self.assertTrue(review["provenance"]["policy"]["user_authorized"])
        self.manager.close()
        self.manager = WorkflowManager(self.store, self.generation)
        self.assertEqual(self.manager.run(synthesis["id"])["review_status"], "Accepted")

    def test_restoring_original_vectors_preserves_proof_but_does_not_restore_adoption(self):
        with patch("hullcirq.workflow.synthesize_generic", self.software_synthesis):
            synthesis = self.wait(self.start("local_synthesis"))
            self.manager.review(synthesis["id"], "accepted", "Software fixture original adoption.")
        original = copy.deepcopy(self.store.envelope()["design"])
        changed = copy.deepcopy(original)
        changed["nodes"][0]["verification"]["vectors"][1]["input_data"] = 0x0402
        self.store.save(changed, self.store.envelope()["revision"]["id"])
        self.manager.observe_design()
        self.store.save(original, self.store.envelope()["revision"]["id"])
        restored = self.manager.run(synthesis["id"])
        self.assertEqual(restored["freshness"], "Current")
        self.assertEqual(restored["validation_status"], "Passed")
        self.assertEqual(restored["review_status"], "Awaiting Review")
        self.assertEqual(restored["verification_plan"], synthesis["verification_plan"])

    def test_changed_prerequisites_during_tool_run_preserve_passed_proof_without_adoption(self):
        self.store.set_review_policy("accept_on_pass", True, "User-authorized software QA policy.")
        started, release = threading.Event(), threading.Event()
        def blocked_synthesis(*args):
            started.set()
            if not release.wait(3):
                raise AssertionError("Software synthesis fixture was not released.")
            return self.software_synthesis(*args)
        with patch("hullcirq.workflow.synthesize_generic", blocked_synthesis):
            run_id = self.start("local_synthesis")
            try:
                self.assertTrue(started.wait(2))
                current = self.store.envelope()
                design = copy.deepcopy(current["design"])
                design["nodes"][1]["behavior"] = "Changed private sink requirement during QA synthesis."
                self.store.save(design, current["revision"]["id"])
            finally:
                release.set()
            result = self.wait(run_id)
        self.assertEqual(result["execution_status"], "Completed")
        self.assertEqual(result["validation_status"], "Passed")
        self.assertEqual(result["review_status"], "Awaiting Review")
        self.assertIn("automatic_adoption_blocked", [item["code"] for item in result["diagnostics"]])

    def test_corrupt_saved_netlist_is_rejected_without_overwriting_original_history(self):
        with patch("hullcirq.workflow.synthesize_generic", self.software_synthesis):
            self.wait(self.start("local_synthesis"))
        self.manager.close()
        state = json.loads(self.manager.path.read_text(encoding="utf-8"))
        state["runs"][0]["netlist"] += "// changed evidence\n"
        self.manager.path.write_text(json.dumps(state), encoding="utf-8")
        before = self.manager.path.read_bytes()
        with self.assertRaises(DomainError) as caught:
            WorkflowManager(self.store, self.generation)
        self.assertEqual(caught.exception.code, "invalid_workflow_store")
        self.assertEqual(self.manager.path.read_bytes(), before)

    def test_embedded_automatic_policy_must_match_the_projects_authorization_history(self):
        self.store.set_review_policy("accept_on_pass", True, "User-authorized software QA policy.")
        with patch("hullcirq.workflow.synthesize_generic", self.software_synthesis):
            self.wait(self.start("local_synthesis"))
        self.manager.close()
        state = json.loads(self.manager.path.read_text(encoding="utf-8"))
        provenance = state["reviews"][-1]["provenance"]
        provenance["policy_id"] = "invented-unapproved-policy"
        provenance["policy"]["id"] = "invented-unapproved-policy"
        self.manager.path.write_text(json.dumps(state), encoding="utf-8")
        original_bytes = self.manager.path.read_bytes()
        with self.assertRaises(DomainError) as caught:
            WorkflowManager(self.store, self.generation)
        self.assertEqual(caught.exception.code, "invalid_workflow_store")
        self.assertEqual(self.manager.path.read_bytes(), original_bytes)


if __name__ == "__main__":
    unittest.main()

"""S07 software QA; saved actual proof is read-only input, not a new model run."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.domain import DomainError
from hullcirq.generation import GenerationManager
from hullcirq.implementation_specs import ImplementationSpecManager, build_node_implementation_spec
from hullcirq.verification import object_hash
from hullcirq.server import make_server
from hullcirq.store import ProjectStore
from hullcirq.workflow import WorkflowManager

SOURCE = PROJECT / "results" / "npu_pe_continuous_flow"


class SpecSoftwareQATests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "software-qa-project"
        self.path.mkdir()
        self.originals = {name: (SOURCE / name).read_bytes() for name in ("state.json", "generation.json", "workflow.json")}
        for name in self.originals:
            shutil.copyfile(SOURCE / name, self.path / name)
        self.store = ProjectStore(self.path)
        self.generation = GenerationManager(self.store)
        self.workflow = WorkflowManager(self.store, self.generation)
        self.addCleanup(self.generation.close)
        self.addCleanup(self.workflow.close)
        self.manager = ImplementationSpecManager(self.store, self.generation, self.workflow)

    def tearDown(self):
        for name, original in self.originals.items():
            self.assertEqual((SOURCE / name).read_bytes(), original, "Software QA must never rewrite original circuit evidence.")

    def start(self):
        result = self.manager.start("node-pe", self.store.envelope()["revision"]["id"])
        return result["implementation_specs"][-1]

    def scoped_fixture(self, *, legacy_synthesis=False):
        """Software-only schema adaptation of retained proof; no new tool run."""
        source = next(run for run in reversed(self.workflow._state["runs"])
                      if run["stage_id"] == "local_netlist_simulation")
        design, candidate, synthesis, simulation = self.manager._source(source["id"])
        module_name = simulation["verification_plan"]["module_name"]
        if not legacy_synthesis:
            candidate["validation_scope"] = "local_rtl_interface_v1"
            candidate["verification_plan"] = None
            candidate["checks"]["syntax"] = {"validation_status": "Not Run", "executed": False}
            candidate["checks"]["behavioral"] = {"validation_status": "Not Run", "executed": False}
            candidate["checks"]["functional_verification"] = {"validation_status": "Not Run", "executed": False}
        simulation.update(workflow_scope_version="stage-boundary-v2", module_name=module_name)
        if not legacy_synthesis:
            synthesis.update(workflow_scope_version="stage-boundary-v2", module_name=module_name,
                             verification_plan=None, vector_hash=None, testbench_sha256=None)
        self.rehash_fixture(synthesis)
        self.rehash_fixture(simulation)
        return design, candidate, synthesis, simulation

    @staticmethod
    def rehash_fixture(run):
        run["record_hash"] = object_hash({key: value for key, value in run.items()
                                         if key not in ("record_hash", "freshness", "artifacts")})

    def test_s07_uses_s06_plan_without_requiring_rtl_simulation(self):
        data = self.scoped_fixture()
        spec = build_node_implementation_spec(*data)
        self.assertEqual(spec["lineage"]["verification_plan_sha256"], object_hash(data[3]["verification_plan"]))
        self.assertIn("S04 checks the public interface", spec["checks"]["items"][1]["message"])
        self.assertEqual(data[1]["checks"]["behavioral"]["validation_status"], "Not Run")

    def test_s07_accepts_new_s06_with_matching_legacy_synthesis(self):
        data = self.scoped_fixture(legacy_synthesis=True)
        self.assertEqual(build_node_implementation_spec(*data)["checks"]["validation_status"], "Passed")

    def test_s07_rejects_s05_claiming_a_behavior_plan_in_new_scope(self):
        data = self.scoped_fixture()
        data[2]["verification_plan"] = copy.deepcopy(data[3]["verification_plan"])
        self.rehash_fixture(data[2])
        with self.assertRaises(DomainError) as caught:
            build_node_implementation_spec(*data)
        self.assertEqual(caught.exception.code, "workflow_provenance_conflict")

    def test_s07_still_requires_executed_passing_netlist_simulation(self):
        data = self.scoped_fixture()
        data[3]["checks"]["executed"] = False
        self.rehash_fixture(data[3])
        with self.assertRaises(DomainError) as caught:
            build_node_implementation_spec(*data)
        self.assertEqual(caught.exception.code, "workflow_not_verified")

    def test_s07_rejects_missing_s06_plan(self):
        data = self.scoped_fixture()
        data[3]["verification_plan"] = None
        self.rehash_fixture(data[3])
        with self.assertRaises(DomainError):
            build_node_implementation_spec(*data)

    def test_read_only_initialization_does_not_create_store_or_change_three_sources(self):
        extension = self.manager.envelope()
        self.assertEqual(extension["implementation_specs"], [])
        self.assertEqual(sum(node["ready"] for node in extension["implementation_spec_nodes"]), 1)
        self.assertFalse(self.manager.path.exists())
        for name, original in self.originals.items():
            self.assertEqual((self.path / name).read_bytes(), original)

    def test_policy_acceptance_is_atomic_and_preserves_source_history(self):
        spec = self.start()
        self.assertEqual(spec["review_status"], "Accepted")
        self.assertEqual(spec["freshness"], "Current")
        review = self.manager.envelope()["implementation_spec_reviews"][-1]
        self.assertEqual(review["actor"], "automation_policy")
        self.assertEqual(review["provenance"], self.store.policy_provenance())
        restored = ImplementationSpecManager(self.store, self.generation, self.workflow)
        self.assertEqual(restored.spec(spec["id"])["specification"], spec["specification"])
        for name, original in self.originals.items():
            self.assertEqual((self.path / name).read_bytes(), original)

    def test_manual_policy_does_not_claim_a_human_adoption_before_review(self):
        policy = self.store.review_policy()
        self.store.set_review_policy("manual", False, "Software QA manual policy.", policy["id"])
        spec = self.start()
        self.assertEqual(spec["review_status"], "Awaiting Review")
        self.assertEqual(self.manager.envelope()["implementation_spec_reviews"], [])
        accepted = self.manager.review(spec["id"], "accepted", "Software QA explicit review.", operator={"actor": "human"})
        self.assertEqual(accepted["implementation_specs"][-1]["review_status"], "Accepted")
        self.assertEqual(accepted["implementation_spec_reviews"][-1]["actor"], "human")

    def test_saved_spec_validation_reads_raw_reviews_and_rejects_missing_provenance(self):
        self.start()
        before = self.manager.path.read_bytes()
        with patch.object(self.generation, "envelope", side_effect=AssertionError("Historical review validation needs no generation view")), \
                patch.object(self.workflow, "envelope", side_effect=AssertionError("Historical review validation needs no workflow view")):
            restored = ImplementationSpecManager(self.store, self.generation, self.workflow)
            self.assertEqual(restored.path.read_bytes(), before)
            reviews = self.generation._state["reviews"]
            self.generation._state["reviews"] = []
            try:
                with self.assertRaises(DomainError) as caught:
                    ImplementationSpecManager(self.store, self.generation, self.workflow)
                self.assertEqual(caught.exception.code, "invalid_implementation_spec_store")
            finally:
                self.generation._state["reviews"] = reviews
        self.assertEqual(self.manager.path.read_bytes(), before)

    def test_revision_conflict_and_missing_node_source_create_no_attempt(self):
        for node, revision in (("node-pe", "wrong-revision"), ("node-control", self.store.envelope()["revision"]["id"])):
            with self.subTest(node=node, revision=revision), self.assertRaises(DomainError):
                self.manager.start(node, revision)
        self.assertFalse(self.manager.path.exists())

    def test_stale_feedback_can_return_without_accepting_or_changing_original_tools(self):
        spec = self.start()
        current = self.store.envelope()
        changed = copy.deepcopy(current["design"])
        changed["nodes"][0]["behavior"] += " Software QA changed specification."
        self.store.save(changed, current["revision"]["id"])
        self.assertEqual(self.manager.spec(spec["id"])["freshness"], "Stale")
        with self.assertRaises(DomainError):
            self.manager.review(spec["id"], "accepted", "Software QA must reject stale adoption.")
        extension = self.manager.review(spec["id"], "return_to_stage", "Software QA correct original requirements.", "specifications")
        self.assertEqual(extension["implementation_spec_reviews"][-1]["target_stage"], "specifications")
        self.assertEqual(extension["implementation_specs"][-1]["review_status"], "Changes Requested")
        restored = ImplementationSpecManager(self.store, self.generation, self.workflow)
        self.assertEqual(restored.spec(spec["id"])["specification"], spec["specification"])

    def test_new_adoption_of_source_does_not_resurrect_previous_specification(self):
        spec = self.start()
        run_id = spec["source_run_id"]
        self.workflow.review(run_id, "changes_requested", "Software QA withdraw adoption.")
        self.assertEqual(self.manager.spec(spec["id"])["freshness"], "Stale")
        self.workflow.review(run_id, "accepted", "Software QA new explicit source review.")
        self.assertEqual(self.manager.spec(spec["id"])["freshness"], "Stale")
        fresh = self.start()
        self.assertEqual(fresh["review_status"], "Accepted")
        self.assertEqual(fresh["specification"], spec["specification"])
        self.assertNotEqual(fresh["source_adoptions"], spec["source_adoptions"])

    def test_invalid_or_forward_return_target_and_empty_feedback_are_rejected(self):
        spec = self.start()
        for decision, note, target in (("changes_requested", " ", None), ("return_to_stage", "Software QA.", "global_rtl_generation"),
                                       ("accepted", "Software QA.", "specifications")):
            with self.subTest(decision=decision, target=target), self.assertRaises(DomainError):
                self.manager.review(spec["id"], decision, note, target)
        self.assertEqual(self.manager.spec(spec["id"])["review_status"], "Accepted")

    def test_attempted_unsupported_derivation_is_saved_and_never_auto_accepted(self):
        failure = DomainError("unsupported_public_interface", "Software QA injected unsupported literal range.", 409)
        with patch("hullcirq.implementation_specs.build_node_implementation_spec", side_effect=failure):
            spec = self.start()
            self.assertEqual(spec["validation_status"], "Unsupported")
            self.assertIsNone(spec["specification"])
            self.assertEqual(spec["review_status"], "Awaiting Review")
            self.assertEqual(spec["error"]["code"], failure.code)
            restored = ImplementationSpecManager(self.store, self.generation, self.workflow)
            with self.assertRaises(DomainError):
                restored.review(spec["id"], "accepted", "Software QA cannot accept unsupported.")
            self.assertEqual(restored.envelope()["implementation_spec_reviews"], [])

    def test_atomic_save_failure_rolls_back_and_reports_last_durable_state(self):
        spec = self.start()
        original = self.manager.path.read_bytes()
        with patch("hullcirq.implementation_specs.os.replace", side_effect=OSError("Software QA storage fault")):
            with self.assertRaises(OSError):
                self.manager.review(spec["id"], "changes_requested", "Software QA must not record success.")
        self.assertEqual(self.manager.path.read_bytes(), original)
        extension = self.manager.envelope()
        self.assertEqual(extension["implementation_specs"][-1]["review_status"], "Accepted")
        self.assertEqual(len(extension["implementation_spec_reviews"]), 1)
        self.assertEqual(extension["implementation_specs_storage_error"]["code"], "storage_error")

    def test_http_s07_routes_return_complete_project_and_per_node_counts(self):
        self.generation.close()
        self.workflow.close()
        server = make_server("127.0.0.1", 0, self.store, PROJECT)
        self.addCleanup(server.generation.close)
        self.addCleanup(server.workflow.close)
        self.addCleanup(server.server_close)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_address[1]}"
        def request(path, body=None):
            data = None if body is None else json.dumps(body).encode()
            with urlopen(Request(base + path, data=data, headers={"Content-Type": "application/json"} if body else {}), timeout=10) as response:
                return json.load(response)
        initial = request("/api/project")
        stage = next(stage for stage in initial["workflow"] if stage["id"] == "node_implementation_specs")
        self.assertTrue(stage["implemented"])
        self.assertEqual(stage["accepted_node_count"], 0)
        result = request("/api/implementation-specs/start", {"node_id": "node-pe", "revision_id": initial["revision"]["id"]})
        self.assertIn("design", result)
        stage = next(stage for stage in result["workflow"] if stage["id"] == "node_implementation_specs")
        self.assertEqual((stage["accepted_node_count"], stage["required_node_count"]), (1, 6))
        self.assertFalse(stage["all_nodes_accepted"])
        spec = result["implementation_specs"][-1]
        self.assertEqual(request("/api/implementation-specs/" + spec["id"])["specification"], spec["specification"])
        self.assertEqual(len(request("/api/implementation-specs")["implementation_specs"]), 1)
        with self.assertRaises(HTTPError) as caught:
            request("/api/implementation-specs/no-such-id")
        self.assertEqual(caught.exception.code, 404)
        result = request("/api/implementation-specs/review", {"spec_id": spec["id"], "decision": "changes_requested", "note": "Software QA feedback."})
        self.assertEqual(result["implementation_specs"][-1]["review_status"], "Changes Requested")


if __name__ == "__main__":
    unittest.main()

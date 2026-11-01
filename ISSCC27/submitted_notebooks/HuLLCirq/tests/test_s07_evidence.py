"""S07 independent QA against preserved actual PE evidence, never new stimuli.

Original results are read-only; all durable mutations use isolated copies.
No tool process, model, network, or replacement simulation is invoked here.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.context import node_fingerprint
from hullcirq.domain import DomainError, revision_hashes
from hullcirq.generation import GenerationManager
from hullcirq.implementation_specs import ImplementationSpecManager, build_node_implementation_spec
from hullcirq.store import ProjectStore
from hullcirq.verification import build_verification_plan, object_hash, verification_template_version
from hullcirq.workflow import WorkflowManager

EVIDENCE = PROJECT / "results/npu_pe_continuous_flow"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def checksum(record):
    record["record_hash"] = object_hash({key: value for key, value in record.items() if key != "record_hash"})


class PreservedActualEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = read(EVIDENCE / "manifest.json")
        for name, record in cls.manifest["files"].items():
            actual = hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest()
            if actual != record["sha256"]:
                raise AssertionError("Preserved original evidence changed: " + name)
        cls.original_hashes = {name: hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest()
                               for name in ("state.json", "generation.json", "workflow.json")}
        cls.design = read(EVIDENCE / "design.json")
        cls.raw_generation = read(EVIDENCE / "generation.json")
        cls.raw_workflow = read(EVIDENCE / "workflow.json")

    @classmethod
    def tearDownClass(cls):
        for name, expected in cls.original_hashes.items():
            if hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest() != expected:
                raise AssertionError("Original evidence was mutated: " + name)

    def sources(self):
        return (copy.deepcopy(self.design),
                copy.deepcopy(next(job for job in self.raw_generation["jobs"] if job["id"] == self.manifest["candidate_id"])),
                copy.deepcopy(next(run for run in self.raw_workflow["runs"] if run["id"] == self.manifest["synthesis_run_id"])),
                copy.deepcopy(next(run for run in self.raw_workflow["runs"] if run["id"] == self.manifest["netlist_run_id"])))

    def isolated(self):
        temporary = tempfile.TemporaryDirectory(prefix="hullcirq-s07-evidence-qa-")
        self.addCleanup(temporary.cleanup)
        target = Path(temporary.name)
        for name in ("state.json", "generation.json", "workflow.json"):
            shutil.copyfile(EVIDENCE / name, target / name)
        store = ProjectStore(target)
        generation = GenerationManager(store)
        workflow = WorkflowManager(store, generation)
        self.addCleanup(generation.close)
        self.addCleanup(workflow.close)
        manager = ImplementationSpecManager(store, generation, workflow)
        return target, store, generation, workflow, manager

    def started(self):
        values = self.isolated()
        _, store, _, _, manager = values
        result = manager.start("node-pe", store.envelope()["revision"]["id"], self.manifest["netlist_run_id"])
        return (*values, result["implementation_specs"][-1])

    def test_actual_same_gui_snapshot_preserves_requirements_and_finite_proof(self):
        payload = build_node_implementation_spec(*self.sources())
        required = payload["original_requirements"]
        self.assertEqual(required["node"], next(node for node in self.design["nodes"] if node["id"] == "node-pe"))
        self.assertEqual(required["settings"]["clock_period_ns"], 50)
        facts = payload["observed_facts"]
        self.assertEqual(facts["vector_count"], 42)
        self.assertEqual(facts["checked_assertion_count"], 249)
        self.assertEqual(facts["classification"], "assertions_checked_reference_trace")
        self.assertEqual(facts["coverage"], {"input_transfers": 16, "output_transfers": 16,
                                           "reset_cycles": 5, "stall_cycles": 12, "simultaneous_transfers": 12})
        self.assertIsNone(facts["trace"][0]["asserted_before"])
        self.assertEqual(payload["lineage"]["vector_hash"], "f18ef8c7fe0837108f8a3760ed0ad97fc5cf0b1524d1f09330c06c763c0f9954")
        for entry in facts["trace"]:
            self.assertNotIn("accumulator", entry["asserted_after"])
        # Independently check the four finite final PE sums against initial
        # GUI matrix input. Bias is deliberately not part of this PE proof.
        job = self.design["verification_jobs"][0]
        expected = [sum(job["A"][0][k] * job["B"][k][column] for k in range(job["k"])) for column in range(4)]
        consumed = [item["asserted_before"]["output_data"] for item in facts["trace"] if item["output_transfer"]]
        signed = [value - 2**32 if value >= 2**31 else value for value in consumed[3::4]]
        self.assertEqual(expected, [113, -122, -127, -1041])
        self.assertEqual(signed, expected)
        self.assertTrue(any("bias/ReLU" in item for item in payload["unverified_limits"]))
        self.assertEqual(facts["timing_claim"], "zero_delay_functional_assertions_only")

    def test_relinked_new_plan_metadata_does_not_reuse_old_execution_marker(self):
        design, candidate, synthesis, simulation = self.sources()
        next(node for node in design["nodes"] if node["id"] == "node-pe")["verification"]["vectors"][1]["input_data"] ^= 1
        plan = build_verification_plan(design, "node-pe", verification_template_version(candidate["verification_plan"]))
        source_hash = node_fingerprint(design, "node-pe")
        candidate.update(input_hash=source_hash, verification_plan=copy.deepcopy(plan))
        for result in (candidate["checks"]["behavioral"], simulation["checks"]):
            result.update({key: copy.deepcopy(plan[key]) for key in ("vector_hash", "testbench_sha256", "reference_trace_hash", "vector_count", "coverage")})
        for result in (synthesis, simulation):
            result.update(input_hash=source_hash, design_hash=revision_hashes(design)["semantic_hash"],
                          verification_plan=copy.deepcopy(plan), vector_hash=plan["vector_hash"], testbench_sha256=plan["testbench_sha256"])
            checksum(result)
        # Even when metadata hashes are relinked, saved original command logs
        # prove the old vector hash and cannot establish this changed input.
        with self.assertRaises(DomainError):
            build_node_implementation_spec(design, candidate, synthesis, simulation)

    def test_changed_and_reverted_semantics_keep_history_without_resurrecting_adoption(self):
        _, store, generation, workflow, manager, spec = self.started()
        original = copy.deepcopy(store.envelope()["design"])
        changed = copy.deepcopy(original)
        next(node for node in changed["nodes"] if node["id"] == "node-pe")["behavior"] += " Isolated QA specification correction."
        store.save(changed, store.envelope()["revision"]["id"])
        old = manager.spec(spec["id"])
        self.assertEqual(old["freshness"], "Stale")
        self.assertEqual(old["specification_sha256"], spec["specification_sha256"])
        reloaded = ImplementationSpecManager(store, generation, workflow)
        self.assertEqual(reloaded.spec(spec["id"])["specification_sha256"], spec["specification_sha256"])
        store.save(original, store.envelope()["revision"]["id"])
        reverted = reloaded.spec(spec["id"])
        self.assertEqual(reverted["review_status"], "Awaiting Review")
        self.assertIsNone(next(item for item in reloaded.envelope()["implementation_spec_nodes"] if item["node_id"] == "node-pe")["accepted_spec_id"])
        self.assertEqual(ImplementationSpecManager(store, generation, workflow).spec(spec["id"])["specification_sha256"], spec["specification_sha256"])

    def test_actual_public_boundary_keeps_source_semantics_and_yosys_lowering_separate(self):
        interface = build_node_implementation_spec(*self.sources())["public_interface"]
        ports = {port["name"]: port for port in interface["ports"]}
        self.assertEqual(set(ports), {"clk", "rst", "pair_data", "pair_data_valid", "pair_data_ready",
                                     "acc_data", "acc_data_valid", "acc_data_ready"})
        self.assertFalse(interface["internal_nets_exposed"])
        self.assertEqual(interface["global_integration_artifact"], "adopted_source_rtl")
        self.assertTrue(ports["acc_data"]["semantic_signed"])
        self.assertTrue(ports["acc_data"]["source_rtl_signed"])
        self.assertFalse(ports["acc_data"]["netlist_declared_signed"])
        self.assertEqual(ports["acc_data"]["logical_port_id"], "port-pe-acc_data")
        self.assertEqual(ports["acc_data"]["rtl_range"], {"msb": 31, "lsb": 0})
        self.assertEqual(ports["acc_data"]["netlist_range"], {"msb": 31, "lsb": 0})

    def test_changed_original_vector_cannot_reuse_old_frozen_proof(self):
        design, candidate, synthesis, simulation = self.sources()
        next(node for node in design["nodes"] if node["id"] == "node-pe")["verification"]["vectors"][1]["input_data"] ^= 1
        with self.assertRaises(DomainError):
            build_node_implementation_spec(design, candidate, synthesis, simulation)

    def test_exact_pass_marker_and_command_completion_are_required(self):
        for alteration in ("duplicate_marker", "suffix_marker", "noncompleted_command"):
            design, candidate, synthesis, simulation = self.sources()
            check = simulation["checks"]
            marker = "HULLCIRQ_PASS vectors=42 vector_hash=" + self.manifest["vector_hash"]
            if alteration == "duplicate_marker":
                check["stdout"] += marker + "\n"
                check["commands"][-1]["stdout"] += marker + "\n"
            elif alteration == "suffix_marker":
                check["stdout"] = check["stdout"].replace(marker, marker + "_WRONG")
                check["commands"][-1]["stdout"] = check["commands"][-1]["stdout"].replace(marker, marker + "_WRONG")
            else:
                check["commands"][-1]["status"] = "Timeout"
            checksum(simulation)
            with self.subTest(alteration=alteration), self.assertRaises(DomainError):
                build_node_implementation_spec(design, candidate, synthesis, simulation)

    def test_reversed_port_bits_do_not_become_an_identity_boundary_mapping(self):
        design, candidate, synthesis, simulation = self.sources()
        # A same-width reversed range must never be treated as exact bit order.
        synthesis["netlist"] = synthesis["netlist"].replace("output [31:0] acc_data;", "output [0:31] acc_data;")
        import hashlib
        new_hash = hashlib.sha256(synthesis["netlist"].encode()).hexdigest()
        synthesis["netlist_sha256"] = new_hash
        synthesis["checks"].update(netlist=synthesis["netlist"], netlist_sha256=new_hash)
        simulation.update(netlist=synthesis["netlist"], netlist_sha256=new_hash)
        simulation["checks"]["rtl_sha256"] = new_hash
        checksum(synthesis)
        checksum(simulation)
        with self.assertRaises(DomainError):
            build_node_implementation_spec(design, candidate, synthesis, simulation)

    def test_duplicate_source_adoption_with_updated_record_checksum_is_rejected(self):
        _, store, generation, workflow, manager, _ = self.started()
        saved = read(manager.path)
        record = saved["specs"][0]
        record["source_adoptions"] = [copy.deepcopy(record["source_adoptions"][0]) for _ in range(3)]
        checksum(record)
        manager.path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        corrupt = manager.path.read_bytes()
        with self.assertRaises(DomainError):
            ImplementationSpecManager(store, generation, workflow)
        self.assertEqual(manager.path.read_bytes(), corrupt)

    def test_saved_review_cannot_relink_to_wrong_node_or_source(self):
        for field, wrong in (("node_id", "node-control"), ("source_run_id", self.manifest["synthesis_run_id"])):
            _, store, generation, workflow, manager, _ = self.started()
            saved = read(manager.path)
            saved["reviews"][0][field] = wrong
            manager.path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
            corrupt = manager.path.read_bytes()
            with self.subTest(field=field), self.assertRaises(DomainError):
                ImplementationSpecManager(store, generation, workflow)
            self.assertEqual(manager.path.read_bytes(), corrupt)

    def test_withdrawn_source_keeps_history_and_blocks_effective_spec_adoption(self):
        _, store, generation, workflow, manager, spec = self.started()
        self.assertEqual(spec["review_status"], "Accepted")
        payload_hash = spec["specification_sha256"]
        workflow.review(self.manifest["synthesis_run_id"], "changes_requested", "Isolated QA withdrawal, never original evidence.")
        historical = manager.spec(spec["id"])
        self.assertEqual(historical["freshness"], "Stale")
        self.assertEqual(historical["review_status"], "Awaiting Review")
        self.assertEqual(historical["specification_sha256"], payload_hash)
        with self.assertRaises(DomainError):
            manager.review(spec["id"], "accepted", "Cannot accept while source adoption withdrawn.")
        reloaded = ImplementationSpecManager(store, generation, workflow)
        self.assertEqual(reloaded.spec(spec["id"])["specification_sha256"], payload_hash)

    def test_spec_payload_relink_with_recomputed_payload_and_record_hash_is_rejected(self):
        _, store, generation, workflow, manager, _ = self.started()
        saved = read(manager.path)
        record = saved["specs"][0]
        record["specification"]["public_interface"]["ports"][0]["name"] = "invented_public_clock"
        record["specification_sha256"] = object_hash(record["specification"])
        checksum(record)
        manager.path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        corrupt = manager.path.read_bytes()
        with self.assertRaises(DomainError):
            ImplementationSpecManager(store, generation, workflow)
        self.assertEqual(manager.path.read_bytes(), corrupt)


if __name__ == "__main__":
    unittest.main()

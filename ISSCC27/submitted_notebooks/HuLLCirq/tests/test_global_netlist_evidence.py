"""Software-only rejection tests for S09/S10 evidence and replay admission.

These disposable records are QA inputs, never actual circuit results. No
model, compiler, synthesizer, live history or immutable proof is modified.
"""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from collect_global_netlist_proof import (GLOBAL_HISTORY, HISTORIES, WORKFLOW_HISTORY,
    decode_workflow_history, latest_adopted, require_source_bytes, terminal_history, validate_lineage)
from replay_global_netlist_proof import actual_checks_passed, compare_observations, require_netlist_only
from hullcirq.verification import content_hash, object_hash


def qa_sources():
    plan = {"vector_hash": "vector", "testbench_sha256": "tb", "public_boundary_vector_hash": "public",
            "recipe": {"expected_outputs": [113, -112], "source_job": {"k": 4, "relu": False}}}
    manifest = {"nodes": [{"node_id": "qa-source", "rtl": "module qa; endmodule\n"}]}
    job = {"id": "qa-global", "revision_id": "qa-revision", "context_id": "qa-context", "rtl": "module qa_top; endmodule\n",
           "context": {"source_manifest": manifest, "verification_plan": plan}}
    job["rtl_sha256"] = content_hash(job["rtl"])
    base = {"revision_id": job["revision_id"], "global_job_id": job["id"], "global_context_id": job["context_id"],
        "global_rtl_sha256": job["rtl_sha256"], "source_manifest": copy.deepcopy(manifest),
        "source_manifest_sha256": object_hash(manifest), "verification_plan": copy.deepcopy(plan),
        "verification_plan_sha256": object_hash(plan), "vector_hash": plan["vector_hash"],
        "testbench_sha256": plan["testbench_sha256"], "public_boundary_vector_hash": plan["public_boundary_vector_hash"],
        "netlist": "module qa_top; wire qa_generic = 1'b0; endmodule\n", "execution_status": "Completed",
        "validation_status": "Passed", "review_status": "Accepted",
        "checks": {"validation_status": "Passed", "executed": True, "exit_code": 0}}
    base["netlist_sha256"] = content_hash(base["netlist"])
    synthesis = {**copy.deepcopy(base), "id": "qa-synthesis", "stage_id": "global_synthesis", "prior_run_id": None}
    simulation = {**copy.deepcopy(base), "id": "qa-netlist", "stage_id": "global_netlist_simulation", "prior_run_id": synthesis["id"]}
    simulation["checks"].update(source_rtl_linked=False, compiled_design_sources=[{"file": "netlist.v", "sha256": base["netlist_sha256"]}])
    return synthesis, simulation, job


class GlobalNetlistEvidenceRejectionTests(unittest.TestCase):
    def test_byte_exact_source_guard_rejects_profile_or_review_rewrite(self):
        original = {name: b'{"qa":"original"}\n' for name in (*HISTORIES, GLOBAL_HISTORY)}
        require_source_bytes(copy.deepcopy(original), original)
        for filename in original:
            changed = dict(original); changed[filename] += b" "
            with self.subTest(filename=filename), self.assertRaises(ValueError):
                require_source_bytes(changed, original)

    def test_original_plan_replacement_is_rejected_even_with_new_checksum(self):
        synthesis, simulation, job = qa_sources()
        validate_lineage(synthesis, simulation, job)
        for run in (synthesis, simulation):
            run["verification_plan"]["recipe"]["source_job"]["k"] = 4.0
            run["verification_plan_sha256"] = object_hash(run["verification_plan"])
        with self.assertRaises(ValueError):
            validate_lineage(synthesis, simulation, job)

    def test_source_RTL_substitution_is_rejected_after_resigning_source_manifest(self):
        synthesis, simulation, job = qa_sources()
        for run in (synthesis, simulation):
            run["source_manifest"]["nodes"][0]["rtl"] += "// substituted\n"
            run["source_manifest_sha256"] = object_hash(run["source_manifest"])
        with self.assertRaises(ValueError):
            validate_lineage(synthesis, simulation, job)

    def test_S10_must_use_exact_adopted_synthesis_id_and_netlist_bytes(self):
        for field, value in (("prior_run_id", "other-synth"), ("netlist", "module replacement; endmodule\n")):
            synthesis, simulation, job = qa_sources()
            simulation[field] = value
            simulation["netlist_sha256"] = content_hash(simulation["netlist"])
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_lineage(synthesis, simulation, job)

    def test_unexecuted_or_boolean_exit_status_cannot_claim_actual_tool_success(self):
        for fields in ({"executed": 1}, {"exit_code": False}, {"exit_code": 0.0}, {"validation_status": "Unsupported"}):
            synthesis, simulation, job = qa_sources()
            simulation["checks"].update(fields)
            self.assertFalse(actual_checks_passed(simulation["checks"]))
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                validate_lineage(synthesis, simulation, job)

    def test_stale_unadopted_latest_run_cannot_be_replaced_by_earlier_pass(self):
        accepted = {"id": "old", "stage_id": "global_synthesis", "execution_status": "Completed",
                    "validation_status": "Passed", "review_status": "Accepted", "freshness": "Current"}
        for change in ({"freshness": "Stale"}, {"review_status": "Changes Requested"}, {"validation_status": "Failed"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                latest_adopted([accepted, {**accepted, "id": "latest", **change}], "global_synthesis")

    def test_running_or_missing_history_cannot_be_frozen_as_final_proof(self):
        for value in ({"runs": [], "reviews": []}, {"runs": [{"execution_status": "Running"}], "reviews": []},
                      {"runs": [{"execution_status": "Queued"}], "reviews": []}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                terminal_history(json.dumps(value).encode())

    def test_bounded_lossless_history_decoder_rejects_bool_length_and_expansion_mismatch(self):
        with tempfile.TemporaryDirectory(prefix="hullcirq-s10-evidence-qa-") as temporary:
            path = Path(temporary) / (WORKFLOW_HISTORY + ".gz")
            raw = b'{"runs":[],"reviews":[]}'
            compressed = gzip.compress(raw, mtime=0); path.write_bytes(compressed)
            metadata = {"archive": path.name, "compression": "gzip", "archive_sha256": hashlib.sha256(compressed).hexdigest(),
                "archive_bytes": len(compressed), "decompressed_sha256": hashlib.sha256(raw).hexdigest(), "decompressed_bytes": len(raw)}
            self.assertEqual(decode_workflow_history(path.parent, metadata), raw)
            for change in ({"decompressed_bytes": True}, {"archive_bytes": True}, {"decompressed_bytes": len(raw)-1},
                           {"archive": "../global_workflow.json.gz"}, {"decompressed_sha256": "0"*64}):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    decode_workflow_history(path.parent, {**metadata, **change})

    def test_netlist_only_proof_rejects_RTL_relinking_and_wrong_input_hash(self):
        require_netlist_only({"source_rtl_linked": False, "compiled_design_sources": [{"file": "netlist.v", "sha256": "exact"}]}, "exact")
        for proof in ({"source_rtl_linked": True, "compiled_design_sources": [{"file": "netlist.v", "sha256": "exact"}]},
                      {"source_rtl_linked": False, "compiled_design_sources": [{"file": "candidate_top.v", "sha256": "exact"}]},
                      {"source_rtl_linked": False, "compiled_design_sources": [{"file": "netlist.v", "sha256": "different"}]}):
            with self.subTest(proof=proof), self.assertRaises(ValueError):
                require_netlist_only(proof, "exact")

    def test_replay_comparison_detects_changed_values_participation_and_numeric_types(self):
        keys = ("actual_output_transfers", "actual_public_stream_transfers", "actual_pe_lane_transfers", "elaborated_instance_counts",
                "vector_hash", "testbench_sha256", "verification_plan_sha256", "public_boundary_vector_hash", "public_monitor_sha256", "instrumented_testbench_sha256")
        original = dict.fromkeys(keys, "qa-exact")
        original["actual_output_transfers"] = [{"index": 0, "value": 113, "cycle": 87}]
        self.assertTrue(compare_observations(copy.deepcopy(original), original))
        for key in keys:
            changed = copy.deepcopy(original); changed[key] = "substituted"
            with self.subTest(key=key):
                self.assertFalse(compare_observations(changed, original))
        changed = copy.deepcopy(original); changed["actual_output_transfers"][0]["value"] = 113.0
        self.assertFalse(compare_observations(changed, original))


if __name__ == "__main__": unittest.main()

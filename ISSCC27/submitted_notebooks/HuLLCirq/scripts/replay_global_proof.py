"""Validate and replay a saved adopted S08 top using its immutable six sources.

Actual Icarus compilation/simulation is run in new ignored scratch space. No
LLM request, replacement matrix input, manual top edit or new review is made.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path

from collect_global_proof import (GLOBAL_HISTORY, JSON_EXPORTS, MAX_HISTORY_BYTES,
    RECORD_KIND, ROOT, TEXT_EXPORTS, attempt_metadata, check_gui_operations,
    exported_values, inspect_global_history, source_reference, validate_global_sources, validate_runtime_profiles)
from replay_all_nodes_proof import decode_histories, inspect_evidence, verify_manifest_files
from node_spec_evidence import load, sha, write_json
from collect_all_nodes_proof import require
from hullcirq.global_generation import GlobalGenerationManager, check_global_rtl
from hullcirq.store import strict_loads
from hullcirq.verification import object_hash


def decode_history(directory, metadata, name):
    fields = {"archive", "compression", "archive_sha256", "archive_bytes", "decompressed_sha256", "decompressed_bytes"}
    require(type(metadata) is dict and set(metadata) == fields and metadata["compression"] == "gzip"
            and name in (GLOBAL_HISTORY, "generation.json") and metadata["archive"] == name + ".gz", "Invalid fixed history descriptor.")
    path = Path(directory) / (name + ".gz")
    require(type(metadata["archive_bytes"]) is int and metadata["archive_bytes"] == path.stat().st_size
            and sha(path) == metadata["archive_sha256"], "Global compressed archive checksum/size differs.")
    length = metadata["decompressed_bytes"]
    require(type(length) is int and 0 < length <= MAX_HISTORY_BYTES, "Invalid or oversized global-history length.")
    with gzip.open(path, "rb") as stream: raw = stream.read(length + 1)
    require(len(raw) == length and hashlib.sha256(raw).hexdigest() == metadata["decompressed_sha256"],
            "Global original decompressed bytes differ.")
    strict_loads(raw.decode("utf-8"))
    return raw


def decode_global_history(directory, metadata):
    return decode_history(directory, metadata, GLOBAL_HISTORY)


def inspect_global_evidence(directory, nodes_evidence):
    directory, nodes_evidence = Path(directory), Path(nodes_evidence)
    manifest = load(directory / "manifest.json")
    require(manifest.get("record_kind") == RECORD_KIND, "Use the actual adopted S08 evidence manifest.")
    verify_manifest_files(directory, manifest["files"])
    require({GLOBAL_HISTORY + ".gz", "runtime/generation.json.gz", *JSON_EXPORTS, *TEXT_EXPORTS}.issubset(manifest["files"]),
            "Global history, saved source/context/plan/checks and Verilog exports are all mandatory.")
    require(sha(nodes_evidence / "manifest.json") == manifest["node_evidence_manifest_sha256"],
            "Immutable all-six source manifest differs from the S08 reference.")
    nodes_manifest, histories, selected = inspect_evidence(nodes_evidence)
    require(object_hash(manifest["source_reference"]) == object_hash(source_reference(nodes_manifest, selected)),
            "Global source IDs/RTL/spec/frozen-plan hashes differ from the immutable six-node evidence.")
    original_raw = decode_histories(nodes_evidence, "histories", nodes_manifest["compressed_histories"]["current"])
    node_raw = dict(original_raw)
    node_raw["generation.json"] = decode_history(directory / "runtime", manifest["runtime_generation_history"], "generation.json")
    require(object_hash(manifest["runtime_provider_changes"]) == object_hash(validate_runtime_profiles(node_raw, original_raw)),
            "Runtime profile/probe changes differ or local source evidence was modified.")
    raw = decode_global_history(directory, manifest["global_history"])
    history, job, effective = inspect_global_history(raw, node_raw)
    validate_global_sources(job, histories, selected)
    values, text = exported_values(job, effective)
    for filename, key in JSON_EXPORTS.items():
        require(object_hash(load(directory / filename)) == object_hash(values[key]),
                "Exported global original JSON differs, including numeric types: " + filename)
    for filename, value in text.items():
        require((directory / filename).read_bytes() == value.encode("utf-8"), "Exported original Verilog bytes differ: " + filename)
    operations, provenance = check_gui_operations(directory / "gui_operations", effective)
    gui_files = {path.relative_to(directory).as_posix() for folder, _, _ in operations for path in folder.iterdir() if path.is_file()}
    require(gui_files == set(manifest["gui_operation_files"]) and gui_files.issubset(manifest["files"])
            and object_hash(provenance) == object_hash(manifest["gui_observation_provenance"]),
            "Actual lossless S08 GUI observation/provenance differs.")
    plan, proof = job["context"]["verification_plan"], job["checks"]
    expected = {"current_global_job_id": job["id"], "context_id": job["context_id"],
        "source_key": job["source_key"], "rtl_sha256": job["rtl_sha256"],
        "verification_plan_sha256": object_hash(plan), "vector_hash": plan["vector_hash"],
        "public_boundary_vector_hash": plan["public_boundary_vector_hash"], "testbench_sha256": plan["testbench_sha256"],
        "public_monitor_sha256": proof["public_monitor_sha256"],
        "instrumented_testbench_sha256": proof["instrumented_testbench_sha256"],
        "actual_output_transfers": proof["actual_output_transfers"],
        "actual_public_stream_transfers": proof["actual_public_stream_transfers"],
        "actual_pe_lane_transfers": proof["actual_pe_lane_transfers"],
        "attempt_count": len(history["jobs"]), "attempts": attempt_metadata(history),
        "manual_human_reviews": sum(r["actor"] == "human" for r in history["reviews"])}
    require(object_hash({key: manifest[key] for key in expected}) == object_hash(expected),
            "Global identity, tool observations or full failed-attempt history metadata differs.")
    require(manifest["scope"] == "single_original_matrix_job_S08_RTL_zero_delay_public_boundary_functional_proof"
            and manifest["actual_local_model_origin"] is True and manifest["manual_RTL_modifications"] == []
            and all(manifest[key] is False for key in ("canonical_job_replaced", "node_sources_replaced", "S09_synthesis_verified",
                "PDK_mapping", "layout", "DRC", "LVS", "SDF", "software_QA_fixtures_are_actual_evidence")),
            "Manifest overstates or changes the finite S08 functional scope.")
    return manifest, nodes_manifest, job


def replay(evidence, nodes_evidence, compiler_path, output):
    evidence, nodes_evidence, output = Path(evidence), Path(nodes_evidence), Path(output).resolve()
    require(output.resolve().is_relative_to((ROOT / ".work").resolve()), "Replay must use new ignored .work scratch space.")
    require(not output.exists() or not any(output.iterdir()), "Use a new empty replay directory; previous results are preserved.")
    manifest_sha, nodes_sha = sha(evidence / "manifest.json"), sha(nodes_evidence / "manifest.json")
    manifest, nodes_manifest, job = inspect_global_evidence(evidence, nodes_evidence)
    config_raw = Path(compiler_path).read_bytes()
    compiler = strict_loads(config_raw.decode("utf-8-sig"))
    output.mkdir(parents=True, exist_ok=True)
    (output / "compiler_config.json").write_bytes(config_raw)
    replay_compiler = {**compiler, "working_directory": str(output / "tool-work")}
    context = job["context"]
    proof = check_global_rtl(job["rtl"], context["source_manifest"], context["verification_plan"], replay_compiler)
    replay_job = copy.deepcopy(job)
    replay_job["context"]["tool_configuration"] = replay_compiler
    replay_job["checks"] = proof
    proof_passed = GlobalGenerationManager._passed(replay_job)
    keys = ("actual_output_transfers", "actual_public_stream_transfers", "actual_pe_lane_transfers",
            "public_boundary_vector_hash", "vector_hash", "testbench_sha256", "public_monitor_sha256",
            "instrumented_testbench_sha256", "rtl_sha256", "source_manifest_sha256", "elaborated_instance_counts")
    original_observations_identical = all(object_hash(proof.get(key)) == object_hash(job["checks"].get(key)) for key in keys)
    passed = proof_passed and original_observations_identical
    write_json(output / "actual_replay_checks.json", proof)
    verify_manifest_files(evidence, manifest["files"])
    verify_manifest_files(nodes_evidence, nodes_manifest["files"])
    require(sha(evidence / "manifest.json") == manifest_sha and sha(nodes_evidence / "manifest.json") == nodes_sha
            and Path(compiler_path).read_bytes() == config_raw, "Saved source evidence or runtime configuration changed during replay.")
    report = {"record_kind": "actual_saved_S08_top_artifact_replay", "validation_status": "Passed" if passed else "Failed",
        "scope": manifest["scope"], "source_global_manifest_sha256": manifest_sha,
        "source_node_manifest_sha256": nodes_sha, "source_global_job_id": job["id"],
        "source_revision_id": job["revision_id"], "rtl_sha256": job["rtl_sha256"],
        "verification_plan_sha256": manifest["verification_plan_sha256"],
        "fixed_tool_public_boundary_proof_passed": proof_passed,
        "original_numeric_outputs_public_transfers_PE_participation_and_monitor_hashes_identical": original_observations_identical,
        "actual_output_transfers": proof.get("actual_output_transfers", []),
        "actual_public_stream_transfers": proof.get("actual_public_stream_transfers", []),
        "actual_pe_lane_transfers": proof.get("actual_pe_lane_transfers", []),
        "LLM_calls": 0, "replacement_vectors": False, "manual_RTL_modifications": [],
        "original_job_record_rewritten": False, "S09_synthesis_verified": False,
        "PDK_mapping": False, "layout": False, "DRC": False, "LVS": False, "SDF": False}
    write_json(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--nodes-evidence", type=Path, default=ROOT / "results/npu_all_nodes_continuous_flow")
    parser.add_argument("--compiler-config", type=Path, default=ROOT / ".work/m2/compiler.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = replay(args.evidence, args.nodes_evidence, args.compiler_config, args.output)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["validation_status"] == "Passed" else 1


if __name__ == "__main__": raise SystemExit(main())

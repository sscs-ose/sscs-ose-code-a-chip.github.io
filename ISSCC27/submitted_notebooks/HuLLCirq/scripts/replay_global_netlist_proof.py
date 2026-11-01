"""Replay preserved S09/S10 with real tools in fresh ignored scratch space.

Only the exact adopted top/six sources are synthesized. Simulation compiles
only the resulting whole netlist with the inherited original job testbench and
compiler-discovered public monitor. No model, live write or new review occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from collect_global_netlist_proof import (JSON_EXPORTS, RECORD_KIND, ROOT, SCOPE, TEXT_EXPORTS,
    WORKFLOW_HISTORY, decode_workflow_history, exported_values, inspect_workflow_history,
    original_source_histories, proof_metadata, require, require_netlist_only, validate_lineage)
from replay_all_nodes_proof import verify_manifest_files
from replay_global_proof import inspect_global_evidence
from node_spec_evidence import load, sha, write_json
from hullcirq.store import strict_loads
from hullcirq.verification import object_hash


def inspect_evidence(directory, global_evidence, nodes_evidence):
    directory, global_evidence, nodes_evidence = map(Path, (directory, global_evidence, nodes_evidence))
    manifest = load(directory / "manifest.json")
    require(manifest.get("record_kind") == RECORD_KIND, "Use the immutable actual S09/S10 whole-netlist proof.")
    verify_manifest_files(directory, manifest["files"])
    mandatory = {WORKFLOW_HISTORY + ".gz", *JSON_EXPORTS, *TEXT_EXPORTS,
                 *("sources/" + node + ".v" for node in ("node-control", "node-buffer", "node-scheduler", "node-pe", "node-post", "node-fifo"))}
    require(mandatory.issubset(manifest["files"]), "Saved workflow, exact sources, netlist, plan and tool records are mandatory.")
    require(sha(global_evidence / "manifest.json") == manifest["source_global_manifest_sha256"]
            and sha(nodes_evidence / "manifest.json") == manifest["source_node_manifest_sha256"],
            "Prior immutable S08 or six-node archive differs from the actual source reference.")
    global_manifest, nodes_manifest, global_job = inspect_global_evidence(global_evidence, nodes_evidence)
    source_raw = original_source_histories(global_evidence, nodes_evidence, global_manifest, nodes_manifest)
    expected_histories = {name: {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)} for name, raw in source_raw.items()}
    require(object_hash(manifest["unchanged_original_source_histories"]) == object_hash(expected_histories),
            "Preserved source-history byte identities differ.")
    raw = decode_workflow_history(directory, manifest["global_workflow_history"])
    history, synthesis, simulation, effective_synthesis, effective_simulation = inspect_workflow_history(raw, source_raw)
    values, text = exported_values(synthesis, simulation, effective_synthesis, effective_simulation, global_job)
    for filename, key in JSON_EXPORTS.items():
        require(object_hash(load(directory / filename)) == object_hash(values[key]),
                "Original exported JSON differs, including numeric types: " + filename)
    for filename, value in text.items():
        require((directory / filename).read_bytes() == value.encode("utf-8"), "Original exported source bytes differ: " + filename)
    metadata = proof_metadata(history, synthesis, simulation, global_job)
    require(object_hash({key: manifest[key] for key in metadata}) == object_hash(metadata),
            "Actual S09/S10 identity, failed attempts, outputs, monitor or adoption metadata differs.")
    require(manifest["scope"] == SCOPE and type(manifest["model_calls"]) is int and manifest["model_calls"] == 0
            and manifest["manual_RTL_modifications"] == [] and manifest["netlist_compile_sources"] == ["netlist.v"]
            and all(manifest[key] is True for key in ("independent_append_only_global_workflow_history", "technology_independent", "zero_delay"))
            and all(manifest[key] is False for key in ("canonical_job_replaced", "original_source_histories_rewritten",
                "source_RTL_relinked_during_S10", "formal_equivalence", "PDK_mapping", "STA", "layout", "DRC", "LVS", "SDF",
                "software_QA_fixtures_are_actual_evidence")),
            "Manifest changes or overstates the finite generic whole-netlist proof scope.")
    return manifest, global_manifest, nodes_manifest, global_job, synthesis, simulation


def actual_checks_passed(checks):
    return (type(checks) is dict and checks.get("validation_status") == "Passed" and checks.get("executed") is True
            and type(checks.get("exit_code")) is int and checks["exit_code"] == 0)


def compare_observations(proof, original):
    keys = ("actual_output_transfers", "actual_public_stream_transfers", "actual_pe_lane_transfers",
        "elaborated_instance_counts", "vector_hash", "testbench_sha256", "verification_plan_sha256",
        "public_boundary_vector_hash", "public_monitor_sha256", "instrumented_testbench_sha256")
    return all(key in proof and key in original and object_hash(proof[key]) == object_hash(original[key]) for key in keys)


def replay(evidence, global_evidence, nodes_evidence, compiler_path, synthesizer_path, output):
    # Import only after immutable-evidence inspection has admitted the inputs.
    evidence, global_evidence, nodes_evidence = map(Path, (evidence, global_evidence, nodes_evidence))
    output = Path(output).resolve()
    require(output.is_relative_to((ROOT / ".work").resolve()), "Replay must use fresh ignored .work scratch space.")
    require(not output.exists() or not any(output.iterdir()), "Use a new empty replay directory; previous attempts are preserved.")
    manifest_sha, global_sha, nodes_sha = [sha(path / "manifest.json") for path in (evidence, global_evidence, nodes_evidence)]
    manifest, global_manifest, nodes_manifest, job, original_synthesis, original_simulation = inspect_evidence(evidence, global_evidence, nodes_evidence)
    from hullcirq.global_workflow import synthesize_global_generic, check_global_netlist
    compiler_raw, synthesizer_raw = Path(compiler_path).read_bytes(), Path(synthesizer_path).read_bytes()
    compiler, synthesizer = strict_loads(compiler_raw.decode("utf-8-sig")), strict_loads(synthesizer_raw.decode("utf-8-sig"))
    output.mkdir(parents=True, exist_ok=True)
    (output / "compiler_config.json").write_bytes(compiler_raw)
    (output / "synthesizer_config.json").write_bytes(synthesizer_raw)
    source_manifest, plan = validate_lineage(original_synthesis, original_simulation, job)
    replay_synthesizer = {**synthesizer, "working_directory": str(output / "synthesis-work")}
    replay_compiler = {**compiler, "working_directory": str(output / "simulation-work")}
    synthesis = synthesize_global_generic(job["rtl"], source_manifest, replay_synthesizer)
    write_json(output / "actual_synthesis_checks.json", synthesis)
    simulation = None
    if actual_checks_passed(synthesis) and synthesis.get("netlist"):
        simulation = check_global_netlist(synthesis["netlist"], source_manifest, plan, replay_compiler)
        write_json(output / "actual_netlist_checks.json", simulation)
        if actual_checks_passed(simulation):
            require_netlist_only(simulation, synthesis["netlist_sha256"])
    identical_netlist = synthesis.get("netlist_sha256") == original_synthesis["netlist_sha256"]
    identical_observations = simulation is not None and compare_observations(simulation, original_simulation["checks"])
    passed = actual_checks_passed(synthesis) and actual_checks_passed(simulation) and identical_netlist and identical_observations
    for folder, saved in ((evidence, manifest), (global_evidence, global_manifest), (nodes_evidence, nodes_manifest)):
        verify_manifest_files(folder, saved["files"])
    require([sha(path / "manifest.json") for path in (evidence, global_evidence, nodes_evidence)] == [manifest_sha, global_sha, nodes_sha]
            and Path(compiler_path).read_bytes() == compiler_raw and Path(synthesizer_path).read_bytes() == synthesizer_raw,
            "Saved source evidence or runtime configuration changed during replay.")
    report = {"record_kind": "actual_saved_S09_S10_whole_netlist_artifact_replay", "validation_status": "Passed" if passed else "Failed",
        "scope": SCOPE, "source_evidence_manifest_sha256": manifest_sha,
        "source_global_manifest_sha256": global_sha, "source_node_manifest_sha256": nodes_sha,
        "source_global_job_id": job["id"], "source_revision_id": job["revision_id"],
        "source_synthesis_run_id": original_synthesis["id"], "source_netlist_run_id": original_simulation["id"],
        "global_rtl_sha256": job["rtl_sha256"], "verification_plan_sha256": manifest["verification_plan_sha256"],
        "generic_synthesis_passed": actual_checks_passed(synthesis), "whole_netlist_proof_passed": actual_checks_passed(simulation),
        "replayed_netlist_byte_identical": identical_netlist,
        "original_outputs_public_transfers_PE_participation_and_S10_monitor_hashes_identical": bool(identical_observations),
        "netlist_sha256": synthesis.get("netlist_sha256"),
        "actual_output_transfers": (simulation or {}).get("actual_output_transfers", []),
        "actual_public_stream_transfers": (simulation or {}).get("actual_public_stream_transfers", []),
        "actual_pe_lane_transfers": (simulation or {}).get("actual_pe_lane_transfers", []),
        "LLM_calls": 0, "replacement_vectors": False, "manual_RTL_modifications": [],
        "source_RTL_relinked_during_S10": False, "original_job_record_rewritten": False,
        "PDK_mapping": False, "STA": False, "layout": False, "DRC": False, "LVS": False, "SDF": False}
    write_json(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--global-evidence", type=Path, default=ROOT / "results/npu_global_continuous_flow")
    parser.add_argument("--nodes-evidence", type=Path, default=ROOT / "results/npu_all_nodes_continuous_flow")
    parser.add_argument("--compiler-config", type=Path, default=ROOT / ".work/m2/compiler.json")
    parser.add_argument("--synthesizer-config", type=Path, default=ROOT / ".work/m2b/synthesizer.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = replay(args.evidence, args.global_evidence, args.nodes_evidence, args.compiler_config, args.synthesizer_config, args.output)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["validation_status"] == "Passed" else 1


if __name__ == "__main__": raise SystemExit(main())

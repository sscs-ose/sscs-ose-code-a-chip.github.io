"""Replay six saved M2-E node candidates and rebuild their original S07 proof.

The compressed histories are decoded losslessly and independently validated
before any tool starts. No model request, replacement input, new review or live
project modification is performed. This is six-node evidence, not S08 success.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from collect_all_nodes_proof import (HISTORIES, JSON_ARTIFACTS, NODE_IDS, RECORD_KIND, ROOT, MAX_HISTORY_BYTES,
                                     check_gui_operations, gui_snapshot_provenance,
                                     gui_input_provenance, node_metadata, read_api_operations, require, validate_histories)
from node_spec_evidence import load, sha, write_json
from hullcirq.context import physical_interface
from hullcirq.implementation_specs import build_node_implementation_spec
from hullcirq.rtl_checks import check_rtl
from hullcirq.store import strict_loads
from hullcirq.verification import object_hash, verify_behavior
from hullcirq.workflow import synthesize_generic

def verify_manifest_files(directory, files):
    directory = Path(directory).resolve()
    require(type(files) is dict and files, "The manifest must identify all preserved files.")
    for relative, record in files.items():
        require(type(relative) is str and type(record) is dict and set(record) == {"sha256", "bytes"}, "Invalid file manifest entry.")
        path = (directory / relative).resolve()
        require(path.is_relative_to(directory) and path.is_file() and path.relative_to(directory).as_posix() == relative,
                "Unsafe or missing manifest file: " + relative)
        require(type(record["bytes"]) is int and record["bytes"] == path.stat().st_size and sha(path) == record["sha256"],
                "Preserved file checksum/size differs: " + relative)


def decode_histories(directory, section, metadata):
    require(section in ("histories", "original_runtime") and type(metadata) is dict and set(metadata) == set(HISTORIES), "All four compressed histories are mandatory.")
    raw = {}
    fields = {"archive", "compression", "archive_sha256", "archive_bytes", "decompressed_sha256", "decompressed_bytes"}
    for name in HISTORIES:
        record = metadata[name]
        require(type(record) is dict and set(record) == fields and record["compression"] == "gzip" and record["archive"] == name + ".gz", "Invalid fixed compressed-history descriptor: " + name)
        path = Path(directory) / section / (name + ".gz")
        require(type(record["archive_bytes"]) is int and record["archive_bytes"] == path.stat().st_size
                and sha(path) == record["archive_sha256"], "Compressed archive differs: " + name)
        length = record["decompressed_bytes"]
        require(type(length) is int and 0 < length <= MAX_HISTORY_BYTES, "Invalid or oversized decompressed-history length: " + name)
        # A bounded read avoids accepting an expanded archive larger than its
        # explicit recorded size. Fixed filenames avoid extraction-path input.
        with gzip.open(path, "rb") as stream:
            value = stream.read(length + 1)
        require(len(value) == length and hashlib.sha256(value).hexdigest() == record["decompressed_sha256"], "Decompressed original bytes differ: " + name)
        strict_loads(value.decode("utf-8"))
        raw[name] = value
    return raw


def inspect_evidence(directory):
    directory = Path(directory)
    manifest = load(directory / "manifest.json")
    require(manifest.get("record_kind") == RECORD_KIND, "Use the preserved actual M2-E six-node proof manifest.")
    verify_manifest_files(directory, manifest["files"])
    mandatory = {"design.json", *("histories/" + name + ".gz" for name in HISTORIES), *("original_runtime/" + name + ".gz" for name in HISTORIES)}
    mandatory |= {f"nodes/{node_id}/{name}" for node_id in NODE_IDS for name in (*JSON_ARTIFACTS, "verification_plan.json", "reference_trace.json", "vectors.json", "candidate.v", "netlist.v", "contract_tb.v")}
    require(mandatory.issubset(manifest["files"]) and set(manifest["nodes"]) == set(NODE_IDS), "Missing required node or original proof artifact.")
    require(type(manifest["compressed_histories"]) is dict and set(manifest["compressed_histories"]) == {"current", "baseline"}, "Current and original baseline histories are both mandatory.")
    source_raw = decode_histories(directory, "histories", manifest["compressed_histories"]["current"])
    baseline_raw = decode_histories(directory, "original_runtime", manifest["compressed_histories"]["baseline"])
    histories, selected = validate_histories(source_raw, baseline_raw)
    state = histories["state.json"]
    operations = check_gui_operations(directory / "gui_operations", selected, state["design"])
    require(object_hash(manifest["gui_snapshot_provenance"]) == object_hash(gui_snapshot_provenance(operations, selected)), "GUI authority/number-precision provenance differs.")
    require(object_hash(manifest["gui_input_provenance"]) == object_hash(gui_input_provenance(operations, state["design"])), "GUI input/recovered-import provenance differs.")
    gui_files = {path.relative_to(directory).as_posix() for folder, _ in operations for path in folder.iterdir() if path.is_file()}
    require(gui_files == set(manifest["gui_operation_files"]) and gui_files.issubset(manifest["files"]), "GUI operation files differ from the manifest.")
    api_operations = read_api_operations(directory / "api_operations", histories, selected)
    api_files = {record["file"] for _, _, record in api_operations}
    require(api_files == set(manifest["api_operation_files"]) and api_files.issubset(manifest["files"])
            and object_hash(manifest["api_operation_provenance"]) == object_hash([record for _, _, record in api_operations]),
            "API operator/current-result provenance differs or was presented as GUI operations.")
    require(object_hash(load(directory / "design.json")) == object_hash(state["design"]), "Exported design differs, including JSON numeric types.")
    require(manifest["project_id"] == state["design"]["project"]["id"] and manifest["current_revision_id"] == state["revision"]["id"]
            and manifest["current_design_semantic_hash"] == state["revision"]["semantic_hash"]
            and manifest["canonical_job_hash"] == object_hash(state["design"]["verification_jobs"]), "Manifest source identity differs.")
    require(type(manifest["accepted_current_nodes"]) is int and manifest["accepted_current_nodes"] == 6
            and type(manifest["required_nodes"]) is int and manifest["required_nodes"] == 6
            and manifest["PE_original_42_cycle_plan_identical"] is True and manifest["canonical_job_replaced"] is False
            and manifest["full_NPU_verified"] is False and manifest["S08_collected"] is False
            and manifest["scope"] == "all_six_node_types_S04_S07_in_one_final_GUI_revision_not_integrated_NPU"
            and manifest["PDK_mapping"] is False and manifest["SDF"] is False
            and manifest["all_selected_candidates_new_local_model_calls"] is True
            and manifest["original_baseline_history_prefix_and_snapshots_preserved"] is True
            and manifest["RTL_and_netlist_use_same_frozen_plan"] is True and manifest["manual_RTL_modifications"] == [],
            "Manifest overstates or changes the six-node proof scope.")
    require(object_hash(manifest["review_policy"]) == object_hash(state["review_policy"]), "Adoption policy differs from its preserved original.")
    generation = histories["generation.json"]
    original_generation = strict_loads(baseline_raw["generation.json"].decode("utf-8"))
    expected_attempts = [{key: job.get(key) for key in ("id", "node_id", "revision_id", "operation", "base_job_id", "origin", "execution_status", "validation_status", "review_status")} for job in generation["jobs"]]
    require(object_hash(manifest["attempts"]) == object_hash(expected_attempts)
            and type(manifest["historical_generation_attempts"]) is int and manifest["historical_generation_attempts"] == len(generation["jobs"])
            and type(manifest["new_generation_attempts"]) is int and manifest["new_generation_attempts"] == len(generation["jobs"]) - len(original_generation["jobs"]), "Generation attempt/failure history metadata differs.")
    require(type(manifest["historical_tool_runs"]) is int and manifest["historical_tool_runs"] == len(histories["workflow.json"]["runs"]), "Tool history metadata differs.")
    human_reviews = sum(review.get("actor") == "human" for history in histories.values() for review in history["reviews"])
    require(type(manifest["manual_human_reviews"]) is int and manifest["manual_human_reviews"] == human_reviews, "Manual review count differs.")
    for node_id, records in selected.items():
        require(object_hash(manifest["nodes"][node_id]) == object_hash(node_metadata(node_id, records)), "Node artifact identity differs: " + node_id)
        folder = directory / "nodes" / node_id
        for filename, key in JSON_ARTIFACTS.items():
            require(object_hash(load(folder / filename)) == object_hash(records[key]), "Exported record differs from exact original history: " + node_id + "/" + filename)
        plan = records["candidate"]["verification_plan"]
        vectors = plan.get("expanded_vectors", plan["contract"].get("vectors"))
        require(object_hash(load(folder / "verification_plan.json")) == object_hash(plan)
                and object_hash(load(folder / "reference_trace.json")) == object_hash(plan["reference_trace"])
                and object_hash(load(folder / "vectors.json")) == object_hash(vectors), "Exported frozen numeric inputs differ: " + node_id)
        for filename, value in (("candidate.v", records["candidate"]["rtl"]), ("netlist.v", records["synthesis"]["netlist"]), ("contract_tb.v", plan["testbench"])):
            require((folder / filename).read_bytes() == value.encode("utf-8"), "Exported Verilog bytes differ: " + node_id + "/" + filename)
    return manifest, histories, selected


def replay(evidence, compiler_path, synthesizer_path, output):
    evidence, output = Path(evidence), Path(output).resolve()
    require(output.resolve().is_relative_to((ROOT / ".work").resolve()), "Tool replay output must use a new ignored .work scratch directory.")
    require(not output.exists() or not any(output.iterdir()), "Use a new empty replay directory; previous results are preserved.")
    manifest_hash = sha(evidence / "manifest.json")
    manifest, histories, selected = inspect_evidence(evidence)
    compiler_source, synthesizer_source = Path(compiler_path).read_bytes(), Path(synthesizer_path).read_bytes()
    compiler = strict_loads(compiler_source.decode("utf-8-sig"))
    synthesizer = strict_loads(synthesizer_source.decode("utf-8-sig"))
    output.mkdir(parents=True, exist_ok=True)
    (output / "compiler_config.json").write_bytes(compiler_source)
    (output / "synthesizer_config.json").write_bytes(synthesizer_source)
    results, passed = {}, True
    for node_id, records in selected.items():
        candidate, original_synthesis, original_simulation = [records[key] for key in ("candidate", "synthesis", "netlist")]
        design = histories["state.json"]["snapshots"][candidate["revision_id"]]
        node = next(item for item in design["nodes"] if item["id"] == node_id)
        plan = candidate["verification_plan"]
        folder = output / node_id
        folder.mkdir()
        local_compiler = {**compiler, "working_directory": str(folder / "syntax")}
        checks = check_rtl(candidate["rtl"], physical_interface(design, node), node["module_name"], local_compiler)
        behavior = verify_behavior(candidate["rtl"], plan, local_compiler, folder / "rtl")
        synthesis = synthesize_generic(candidate["rtl"], node["module_name"], synthesizer, folder / "synthesis")
        netlist = verify_behavior(synthesis["netlist"], plan, local_compiler, folder / "netlist") if synthesis.get("validation_status") == "Passed" and synthesis.get("netlist") else None
        rebuilt = build_node_implementation_spec(design, candidate, original_synthesis, original_simulation)
        same_netlist = synthesis.get("netlist_sha256") == records["netlist"]["netlist_sha256"]
        same_spec = object_hash(rebuilt) == object_hash(records["specification"]) == records["spec_record"]["specification_sha256"]
        node_pass = checks["validation_status"] == "Passed" and all(item and item.get("validation_status") == "Passed" for item in (behavior, synthesis, netlist)) and same_netlist and same_spec
        passed &= node_pass
        report = {"node_id": node_id, "validation_status": "Passed" if node_pass else "Failed", "source_revision_id": candidate["revision_id"],
                  "candidate_id": candidate["id"], "vector_count": plan["vector_count"], "vector_hash": plan["vector_hash"],
                  "reference_trace_hash": plan["reference_trace_hash"], "testbench_sha256": plan["testbench_sha256"],
                  "candidate_checks": checks, "RTL_behavior": behavior, "generic_synthesis": synthesis, "netlist_behavior": netlist,
                  "replayed_netlist_byte_identical": same_netlist, "S07_original_saved_evidence_reconstruction_identical": same_spec,
                  "S07_new_tool_results_not_substituted_into_original_record": True, "specification_sha256": object_hash(rebuilt)}
        write_json(folder / "rebuilt_node_implementation_spec.json", rebuilt)
        write_json(folder / "report.json", report)
        results[node_id] = {key: report[key] for key in ("validation_status", "vector_count", "vector_hash", "reference_trace_hash", "testbench_sha256",
                                                       "replayed_netlist_byte_identical", "S07_original_saved_evidence_reconstruction_identical")}
    verify_manifest_files(evidence, manifest["files"])
    require(sha(evidence / "manifest.json") == manifest_hash and Path(compiler_path).read_bytes() == compiler_source
            and Path(synthesizer_path).read_bytes() == synthesizer_source, "Source evidence or runtime configuration changed during replay.")
    final = {"record_kind": "actual_saved_all_six_nodes_artifact_replay", "validation_status": "Passed" if passed else "Failed",
             "source_evidence_manifest_sha256": manifest_hash, "source_revision_id": manifest["current_revision_id"], "nodes": results,
             "LLM_calls": 0, "replacement_vectors": False, "manual_RTL_modifications": [], "PE_original_42_cycle_plan_identical": True,
             "full_NPU_verified": False, "S08_replayed": False, "PDK_mapping": False, "SDF": False}
    write_json(output / "report.json", final)
    return final


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--compiler-config", type=Path, default=ROOT / ".work/m2/compiler.json")
    parser.add_argument("--synthesizer-config", type=Path, default=ROOT / ".work/m2b/synthesizer.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = replay(args.evidence, args.compiler_config, args.synthesizer_config, args.output)
    print(json.dumps({**report, "report": str(args.output / "report.json")}, ensure_ascii=False))
    return 0 if report["validation_status"] == "Passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

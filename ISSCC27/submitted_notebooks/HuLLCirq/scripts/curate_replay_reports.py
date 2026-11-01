"""Copy actual replay reports losslessly, preserving earlier failed attempts.

This is report curation only. It never calls a model, compiler or synthesizer,
and never rewrites the original source evidence or replay scratch files.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shutil

from collect_all_nodes_proof import NODE_IDS, ROOT, require
from replay_all_nodes_proof import verify_manifest_files
from node_spec_evidence import load, sha, write_json
from hullcirq.verification import object_hash
from hullcirq.verification import content_hash
from hullcirq.global_generation import GlobalGenerationManager


def validate_report(kind, directory, source, source_sha, source_directory=None):
    report = load(directory / "report.json")
    require(report.get("validation_status") in ("Passed", "Failed")
            and type(report.get("LLM_calls")) is int and report["LLM_calls"] == 0
            and report.get("replacement_vectors") is False and report.get("manual_RTL_modifications") == []
            and report.get("PDK_mapping") is False and report.get("SDF") is False,
            "Replay report status, origin or scope is inconsistent: " + directory.name)
    if kind == "all-nodes":
        require(report.get("record_kind") == "actual_saved_all_six_nodes_artifact_replay"
                and report["source_evidence_manifest_sha256"] == source_sha
                and report["source_revision_id"] == source["current_revision_id"]
                and set(report["nodes"]) == set(NODE_IDS) and report.get("full_NPU_verified") is False
                and report.get("S08_replayed") is False and report.get("PE_original_42_cycle_plan_identical") is True,
                "Replay source hash/revision or six-node scope differs.")
        for node_id in NODE_IDS:
            node = load(directory / node_id / "report.json"); original = source["nodes"][node_id]
            require(node["node_id"] == node_id and node["candidate_id"] == original["candidate_id"]
                    and node["source_revision_id"] == original["source_revision_id"]
                    and object_hash({k: node[k] for k in ("vector_count", "vector_hash", "reference_trace_hash", "testbench_sha256")})
                        == object_hash({k: original[k] for k in ("vector_count", "vector_hash", "reference_trace_hash", "testbench_sha256")})
                    and object_hash({k: node[k] for k in report["nodes"][node_id]}) == object_hash(report["nodes"][node_id]),
                    "Per-node replay identity/summary differs: " + node_id)
            synthesis = node["generic_synthesis"]
            for key, rtl_sha in (("RTL_behavior", original["rtl_sha256"]), ("netlist_behavior", synthesis.get("netlist_sha256"))):
                result = node.get(key)
                if result is not None:
                    require(result["rtl_sha256"] == rtl_sha and object_hash({k: result[k] for k in (
                        "vector_count", "vector_hash", "reference_trace_hash", "testbench_sha256")})
                        == object_hash({k: original[k] for k in ("vector_count", "vector_hash", "reference_trace_hash", "testbench_sha256")}),
                        "Replayed RTL/netlist used different input bytes or frozen verification: " + node_id)
            rebuilt_sha = object_hash(load(directory / node_id / "rebuilt_node_implementation_spec.json"))
            require(synthesis["rtl_sha256"] == original["rtl_sha256"]
                    and node["specification_sha256"] == rebuilt_sha
                    and type(node["S07_original_saved_evidence_reconstruction_identical"]) is bool
                    and node["S07_original_saved_evidence_reconstruction_identical"] == (rebuilt_sha == original["specification_sha256"])
                    and type(node["replayed_netlist_byte_identical"]) is bool
                    and node["replayed_netlist_byte_identical"] == (synthesis.get("netlist_sha256") == original["netlist_sha256"]),
                    "Replayed synthesis source or reconstructed S07 document differs: " + node_id)
            if synthesis.get("netlist") is not None:
                require(content_hash(synthesis["netlist"]) == synthesis["netlist_sha256"], "Replayed generated netlist content/hash differs: " + node_id)
            if report["validation_status"] == "Passed" or node["validation_status"] == "Passed":
                require(node["validation_status"] == "Passed" and node["replayed_netlist_byte_identical"] is True
                        and node["S07_original_saved_evidence_reconstruction_identical"] is True
                        and all(node[key]["validation_status"] == "Passed" for key in (
                            "candidate_checks", "RTL_behavior", "generic_synthesis", "netlist_behavior")),
                        "A successful six-node replay needs all actual saved tool results: " + node_id)
    else:
        require(report.get("record_kind") == "actual_saved_S08_top_artifact_replay"
                and report["source_global_manifest_sha256"] == source_sha
                and report["source_node_manifest_sha256"] == source["node_evidence_manifest_sha256"]
                and report["source_global_job_id"] == source["current_global_job_id"]
                and report["source_revision_id"] == source["source_reference"]["current_revision_id"]
                and report["rtl_sha256"] == source["rtl_sha256"]
                and report["verification_plan_sha256"] == source["verification_plan_sha256"]
                and report.get("scope") == source["scope"] and report.get("original_job_record_rewritten") is False
                and all(report.get(key) is False for key in ("S09_synthesis_verified", "layout", "DRC", "LVS")),
                "S08 replay source/plan hashes or functional-only scope differs.")
        proof = load(directory / "actual_replay_checks.json")
        require(all(object_hash(report[key]) == object_hash(proof.get(key)) for key in (
            "actual_output_transfers", "actual_public_stream_transfers", "actual_pe_lane_transfers")),
            "S08 replay observations differ from its actual tool report.")
        if report["validation_status"] == "Passed":
            require(source_directory is not None, "S08 pass inspection needs its original global job record.")
            replay_job = copy.deepcopy(load(Path(source_directory) / "global_job_record.json"))
            replay_job["context"]["tool_configuration"] = proof["tool_configuration"]
            replay_job["checks"] = proof
            require(proof["validation_status"] == "Passed" and report["fixed_tool_public_boundary_proof_passed"] is True
                    and GlobalGenerationManager._passed(replay_job)
                    and report["original_numeric_outputs_public_transfers_PE_participation_and_monitor_hashes_identical"] is True
                    and all(object_hash(report[key]) == object_hash(source[key]) for key in (
                        "actual_output_transfers", "actual_public_stream_transfers", "actual_pe_lane_transfers")),
                    "A successful S08 replay needs exact original observations and public-boundary checks.")
    return report


def curate(kind, source_directory, attempts, output, failure_notes=()):
    require(kind in ("all-nodes", "global"), "Choose all-nodes or global report curation.")
    source_directory, output = Path(source_directory).resolve(), Path(output).resolve()
    require(output.is_relative_to((ROOT / "results").resolve()) and (not output.exists() or not any(output.iterdir())),
            "Use a new empty HuLLCirq results directory; previous evidence is preserved.")
    source_sha = sha(source_directory / "manifest.json"); source = load(source_directory / "manifest.json")
    require(source.get("record_kind") == ("actual_GUI_all_six_nodes_local_LLM_S04_S07_continuous_proof" if kind == "all-nodes"
            else "actual_local_LLM_S08_original_job_public_boundary_proof"), "Wrong original evidence archive kind.")
    verify_manifest_files(source_directory, source["files"])
    notes = {}
    for file in failure_notes:
        file = Path(file).resolve(); note = load(file)
        require(note.get("record_kind") == "development_assistant_observation_of_replay_launch_failure"
                and note.get("actor") == "development_assistant" and note.get("validation_status") == "Failed"
                and note.get("not_a_tool_execution_report") is True
                and type(note.get("reason")) is str and note["reason"].strip()
                and note.get("source_evidence_manifest_sha256") == source_sha,
                "Unreported failures need an explicit attributed observation, not a fabricated tool report.")
        path = (ROOT / note["attempt_directory"]).resolve()
        require(path not in notes, "Duplicate failure observation."); notes[path] = file
    paths = [Path(path).resolve() for path in attempts]
    require(paths and len({p.name for p in paths}) == len(paths) and all(
        p.is_dir() and p.is_relative_to((ROOT / ".work").resolve()) for p in paths),
        "Provide distinct existing ignored replay directories in execution order.")
    require(set(notes).issubset(paths), "A failure observation refers to an unselected replay directory.")
    planned, records, source_files = [], [], {}
    for directory in paths:
        report_path = directory / "report.json"
        if report_path.is_file():
            require(directory not in notes, "A saved tool report must not be replaced by a failure observation.")
            report = validate_report(kind, directory, source, source_sha, source_directory)
            status, classification = report["validation_status"], "actual_saved_replay_report"
        else:
            require(directory in notes, "Missing report needs an explicit failure observation: " + directory.name)
            status, classification = "Failed", "attributed_prior_launch_failure_no_tool_report"
        chosen = [path for path in sorted(directory.rglob("*")) if path.is_file() and (
            path.name in ("report.json", "actual_replay_checks.json", "compiler_config.json", "synthesizer_config.json",
                          "rebuilt_node_implementation_spec.json") or path.suffix.lower() in (".log", ".txt"))]
        require(chosen, "No report/config evidence exists: " + directory.name)
        attempt_files = []
        for path in chosen:
            target = Path("attempts") / directory.name / path.relative_to(directory)
            planned.append((path, target)); source_files[path] = sha(path); attempt_files.append(target.as_posix())
        if directory in notes:
            path = notes[directory]; target = Path("attempts") / directory.name / "failure-observation.json"
            planned.append((path, target)); source_files[path] = sha(path); attempt_files.append(target.as_posix())
        records.append({"attempt": directory.name, "original_scratch_directory": directory.relative_to(ROOT).as_posix(),
            "validation_status": status, "classification": classification, "files": attempt_files,
            "report_file": (Path("attempts") / directory.name / "report.json").as_posix() if report_path.is_file() else None})
    output.mkdir(parents=True, exist_ok=True)
    for original, relative in planned:
        destination = output / relative; destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, destination)
        require(sha(destination) == source_files[original], "Copied replay bytes differ.")
    latest = records[-1]
    if latest["report_file"]: shutil.copyfile(output / latest["report_file"], output / "report.json")
    scope = "Six individual saved node candidates; this does not establish integrated NPU operation." if kind == "all-nodes" else (
        "Saved S08 top RTL, six adopted public node contracts, one original matrix job, zero-delay functional/public-boundary checks.")
    lines = ["# HuLLCirq saved artifact replay", "", f"Latest attempt: **{latest['validation_status']}** (`{latest['attempt']}`).", "", scope,
        "", "No model request, replacement input or manual RTL edit is part of these replays. No PDK mapping, layout, DRC, LVS or SDF result is implied.", "",
        "Each attempt preserves original report/configuration bytes. Earlier failures remain failures. A launch failure without a saved report is identified as a development-assistant observation, never as tool output.", "",
        "| Attempt | Status | Record |", "| --- | --- | --- |"]
    lines.extend(f"| {r['attempt']} | {r['validation_status']} | {r['classification']} |" for r in records)
    (output / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    files = {p.relative_to(output).as_posix(): {"sha256": sha(p), "bytes": p.stat().st_size}
             for p in sorted(output.rglob("*")) if p.is_file()}
    manifest = {"record_kind": "preserved_actual_" + kind.replace("-", "_") + "_replay_attempt_reports",
        "validation_status": latest["validation_status"], "source_evidence_manifest_sha256": source_sha,
        "latest_attempt": latest["attempt"], "attempts": records,
        "preservation_scope": "Original JSON reports, rebuilt proof documents, runtime configurations and saved text logs; transient binaries/duplicate RTL/TB stay in ignored scratch or original evidence archive.",
        "LLM_calls_by_curation": 0, "EDA_calls_by_curation": 0, "original_source_modified": False,
        "S09_synthesis_verified": False, "PDK_mapping": False, "layout": False, "DRC": False, "LVS": False, "SDF": False,
        "files": files}
    verify_manifest_files(source_directory, source["files"])
    require(sha(source_directory / "manifest.json") == source_sha and all(sha(p) == digest for p, digest in source_files.items()),
            "Original evidence or replay reports changed during curation; no completed manifest was written.")
    write_json(output / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("all-nodes", "global"), required=True)
    parser.add_argument("--source-evidence", type=Path, required=True)
    parser.add_argument("--attempt", type=Path, action="append", required=True)
    parser.add_argument("--failure-note", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = curate(args.kind, args.source_evidence, args.attempt, args.output, args.failure_note)
    print(json.dumps({"validation_status": manifest["validation_status"], "attempts": len(manifest["attempts"]), "output": str(args.output)}))
    return 0


if __name__ == "__main__": raise SystemExit(main())

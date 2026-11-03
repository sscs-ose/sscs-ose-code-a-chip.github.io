"""Collect actual adopted S08 evidence against an immutable six-node archive.

The full global history (including failed attempts) is compressed byte exactly.
Only strict reads of disposable copies are performed; no model or EDA is run.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from collect_all_nodes_proof import HISTORIES, MAX_HISTORY_BYTES, ROOT, read_histories, require
from replay_all_nodes_proof import decode_histories, inspect_evidence, verify_manifest_files
from node_spec_evidence import load, sha, write_json
from hullcirq.context import physical_interface
from hullcirq.global_generation import (GlobalGenerationManager, NODE_IDS, build_global_plan,
    compiler_public_hierarchy, instrument_public_testbench)
from hullcirq.server import make_server
from hullcirq.store import ProjectStore, strict_loads
from hullcirq.verification import content_hash, object_hash

RECORD_KIND = "actual_local_LLM_S08_original_job_public_boundary_proof"
GLOBAL_HISTORY = "global_generation.json"
JSON_EXPORTS = {"global_job_record.json": "job", "global_effective_record.json": "effective",
                "context.json": "context", "source_manifest.json": "source_manifest",
                "verification_plan.json": "plan", "actual_checks.json": "checks"}
TEXT_EXPORTS = ("candidate_top.v", "original_job_tb.v", "instrumented_job_tb.v", "public_monitor.v")


def inspect_global_history(raw, node_raw):
    """Validate original histories through the product, without touching live data."""
    require(type(raw) is bytes and 0 < len(raw) <= MAX_HISTORY_BYTES, "Global history is empty or oversized.")
    original = strict_loads(raw.decode("utf-8"))
    require(type(original.get("jobs")) is list and original["jobs"]
            and all(j["execution_status"] not in ("Queued", "Running") for j in original["jobs"]),
            "Wait for all global attempts to terminate; preserve failures and cancellation history.")
    scratch = ROOT / ".work/m2e/global-evidence-checks"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="global-check-", dir=scratch) as temporary:
        directory = Path(temporary)
        for name in HISTORIES:
            (directory / name).write_bytes(node_raw[name])
        (directory / GLOBAL_HISTORY).write_bytes(raw)
        server = make_server("127.0.0.1", 0, ProjectStore(directory), ROOT)
        try:
            effective = server.global_generation.job(original["jobs"][-1]["id"])
            require(all(effective.get(key) == value for key, value in (
                ("execution_status", "Completed"), ("validation_status", "Passed"),
                ("review_status", "Accepted"), ("freshness", "Current"))),
                "The latest S08 job must be Passed, Accepted and Current against all six adopted sources.")
            job = copy.deepcopy(server.global_generation._state["jobs"][-1])
            require(GlobalGenerationManager._passed(job), "Saved whole-job/public-boundary tool proof is incomplete.")
            require(read_histories(directory) == node_raw and (directory / GLOBAL_HISTORY).read_bytes() == raw,
                    "Strict inspection changed a copied source history.")
            return original, job, effective
        finally:
            server.workflow.close(); server.generation.close(); server.server_close()


def validate_runtime_profiles(current_raw, original_raw):
    """Only append provider profiles/change active profile or probe after S07."""
    require(set(current_raw) == set(original_raw) == set(HISTORIES), "All four local source histories are mandatory.")
    require(all(type(value) is bytes and 0 < len(value) <= MAX_HISTORY_BYTES for value in current_raw.values()),
            "A current local history is empty or exceeds the bounded replay size.")
    require(all(current_raw[name] == original_raw[name] for name in HISTORIES if name != "generation.json"),
            "Input, local workflow or S07 history changed since the immutable all-six archive.")
    current = strict_loads(current_raw["generation.json"].decode("utf-8"))
    original = strict_loads(original_raw["generation.json"].decode("utf-8"))
    allowed = {"profiles", "active_profile_revision_id", "probe"}
    require(set(current) == set(original) and object_hash({k: v for k, v in current.items() if k not in allowed})
            == object_hash({k: v for k, v in original.items() if k not in allowed}),
            "Local candidates, failures, reviews, input hashes and epochs must remain unchanged after the all-six archive.")
    profiles, prior = current["profiles"], original["profiles"]
    require(type(profiles) is list and type(prior) is list and len(profiles) >= len(prior)
            and object_hash(profiles[:len(prior)]) == object_hash(prior),
            "Previously saved provider profiles must remain exact; only new profile versions may be appended.")
    return {"original_generation_sha256": hashlib.sha256(original_raw["generation.json"]).hexdigest(),
        "current_generation_sha256": hashlib.sha256(current_raw["generation.json"]).hexdigest(),
        "original_profile_count": len(prior), "current_profile_count": len(profiles),
        "appended_profile_revision_ids": [p["revision_id"] for p in profiles[len(prior):]],
        "active_profile_revision_id": current["active_profile_revision_id"],
        "current_probe_object_hash": object_hash(current["probe"]),
        "local_jobs_reviews_inputs_epochs_unchanged": True,
        "other_three_local_history_bytes_unchanged": True}


def source_reference(nodes_manifest, selected):
    return {"current_revision_id": nodes_manifest["current_revision_id"],
            "canonical_job_hash": nodes_manifest["canonical_job_hash"],
            "nodes": {node_id: {
                "candidate_id": records["candidate"]["id"], "synthesis_run_id": records["synthesis"]["id"],
                "netlist_run_id": records["netlist"]["id"], "spec_id": records["spec_record"]["id"],
                "rtl_sha256": records["candidate"]["rtl_sha256"],
                "specification_sha256": records["spec_record"]["specification_sha256"],
                "verification_plan_sha256": object_hash(records["candidate"]["verification_plan"])}
                for node_id, records in selected.items()}}


def validate_global_sources(job, histories, selected):
    state = histories["state.json"]; design = state["design"]
    context = job["context"]; manifest = context["source_manifest"]; plan = context["verification_plan"]
    require(job["origin"] == "local_llm" and job["profile"]["execution_location"] == "Local"
            and job["revision_id"] == state["revision"]["id"]
            and object_hash(manifest["design"]) == object_hash(design)
            and job["source_key"] == object_hash(manifest)
            and object_hash(plan) == object_hash(build_global_plan(design)),
            "S08 must preserve the current exact GUI job, frozen plan and actual Local model origin.")
    require([entry["node_id"] for entry in manifest["nodes"]] == list(NODE_IDS), "All six exact adopted source types are mandatory.")
    for entry in manifest["nodes"]:
        node_id = entry["node_id"]; records = selected[node_id]
        node = next(n for n in design["nodes"] if n["id"] == node_id)
        require(entry["candidate_id"] == records["candidate"]["id"]
                and entry["synthesis_run_id"] == records["synthesis"]["id"]
                and entry["netlist_run_id"] == records["netlist"]["id"]
                and entry["spec_id"] == records["spec_record"]["id"]
                and entry["rtl"] == records["candidate"]["rtl"]
                and entry["rtl_sha256"] == records["candidate"]["rtl_sha256"]
                and object_hash(entry["specification"]) == records["spec_record"]["specification_sha256"]
                and object_hash(entry["public_interface"]) == object_hash(physical_interface(design, node)),
                "Global adopted-source lineage differs from the immutable all-node archive: " + node_id)


def exported_values(job, effective):
    context = job["context"]; plan = context["verification_plan"]; proof = job["checks"]
    hierarchy = compiler_public_hierarchy(proof["hierarchy_scope_lines"], context["source_manifest"])
    instrumented, monitor = instrument_public_testbench(plan, hierarchy)
    values = {"job": job, "effective": effective, "context": context,
              "source_manifest": context["source_manifest"], "plan": plan, "checks": proof}
    text = dict(zip(TEXT_EXPORTS, (job["rtl"], plan["testbench"], instrumented, monitor)))
    return values, text


def check_gui_operations(directory, effective):
    operations = []
    for folder in sorted(Path(directory).iterdir()):
        if not folder.is_dir():
            continue
        records = [name for name in ("gui-operation.json", "gui-operation-failure.json") if (folder / name).is_file()]
        require(len(records) <= 1, "A GUI attempt cannot be both successful and failed: " + folder.name)
        if not records: continue
        filename = records[0]; action = load(folder / filename)
        require(action.get("actor") == "development_assistant_gui_automation"
                and action.get("phase") in ("preview", "generate", "repair", "observe", "cancel")
                and type(action.get("actions")) is list and type(action.get("downloads")) is list
                and type(action.get("page_errors")) is list, "Invalid actual S08 GUI operation: " + folder.name)
        if filename == "gui-operation.json":
            require(action["page_errors"] == [], "A successful GUI operation must have no page error.")
        else:
            require(type(action.get("error")) is str and action.get("mutation_retry") is False,
                    "Preserve a failed GUI attempt honestly, without an implicit retry.")
        require(all(a.get("actor") == "development_assistant_gui_automation" for a in action["actions"]),
                "GUI actions must not be presented as manual human work.")
        for download in action["downloads"]:
            name = download.get("filename")
            require(type(name) is str and Path(name).name == name and (folder / name).is_file()
                    and type(download.get("bytes")) is int and download["bytes"] == (folder / name).stat().st_size
                    and download.get("sha256") == sha(folder / name), "GUI download bytes/hash differ: " + folder.name)
        operations.append((folder, action, filename))
    observations = [(folder, action, filename) for folder, action, filename in operations
        if filename == "gui-operation.json" and action["phase"] in ("generate", "repair", "observe")
        and (folder / "job-api-original.json").is_file()]
    require(bool(observations), "A lossless current S08 GUI observation is mandatory.")
    folder, action, filename = observations[-1]
    context = effective["context"]
    for name, expected in (("job-api-original.json", effective), ("job.json", effective), ("context.json", context),
            ("source-manifest.json", context["source_manifest"]), ("verification-plan.json", context["verification_plan"])):
        require(object_hash(load(folder / name)) == object_hash(expected),
                "Latest S08 GUI download differs from the authoritative backend, including integer types: " + name)
    require((folder / "top.v").read_bytes() == effective["rtl"].encode("utf-8"), "S08 GUI top download differs from actual model RTL.")
    require((folder / "global-executed-checks.png").is_file(), "Current S08 GUI screenshot is missing.")
    source_ids = [{key: entry[key] for key in ("node_id", "candidate_id", "synthesis_run_id", "netlist_run_id", "spec_id")}
                  for entry in context["source_manifest"]["nodes"]]
    start = [(p, a, f) for p, a, f in operations if a["phase"] in ("generate", "repair") and any(event.get("action") == "inspected_complete_frozen_source_manifest_and_prompt"
        and event.get("context_id") == effective["context_id"] and event.get("revision_id") == effective["revision_id"]
        and object_hash(event.get("source_ids")) == object_hash(source_ids)
        and event.get("vector_hash") == context["verification_plan"]["vector_hash"]
        and event.get("public_boundary_vector_hash") == context["verification_plan"]["public_boundary_vector_hash"]
        for event in a["actions"]) and any(event.get("route") == "global-generation/start" and type(event.get("status")) is int
        and event["status"] == 200 for event in a["actions"])]
    require(bool(start), "The actual selected global start must be linked to its exact inspected GUI preview and six-source IDs.")
    provenance = {"phase": action["phase"], "actor": action["actor"],
        "actions_file": "gui_operations/" + folder.name + "/" + filename,
        "selected_start_actions_file": "gui_operations/" + start[-1][0].name + "/" + start[-1][2],
        "authoritative_record_file": "gui_operations/" + folder.name + "/job-api-original.json",
        "screenshot_file": "gui_operations/" + folder.name + "/global-executed-checks.png",
        "record_object_hash": object_hash(effective),
        "retained_failed_GUI_attempts": ["gui_operations/" + p.name + "/" + f for p, _, f in operations if f == "gui-operation-failure.json"],
        "classification": "development_assistant_GUI_automation_not_manual_human_review"}
    return operations, provenance


def history_descriptor(path, raw):
    return {"archive": path.name, "compression": "gzip", "archive_sha256": sha(path),
            "archive_bytes": path.stat().st_size, "decompressed_sha256": hashlib.sha256(raw).hexdigest(),
            "decompressed_bytes": len(raw)}


def attempt_metadata(history):
    return [{key: job.get(key) for key in ("id", "revision_id", "operation", "base_job_id", "origin",
        "profile_revision_id", "execution_status", "validation_status", "review_status")} for job in history["jobs"]]


def collect(data_directory, nodes_evidence, gui_directory, output):
    output, nodes_evidence = Path(output), Path(nodes_evidence)
    require(not output.exists() or not any(output.iterdir()), "Use a new empty result directory; previous evidence is preserved.")
    node_manifest_sha = sha(nodes_evidence / "manifest.json")
    nodes_manifest, histories, selected = inspect_evidence(nodes_evidence)
    original_raw = decode_histories(nodes_evidence, "histories", nodes_manifest["compressed_histories"]["current"])
    node_raw = read_histories(data_directory)
    runtime_changes = validate_runtime_profiles(node_raw, original_raw)
    global_path = Path(data_directory) / GLOBAL_HISTORY; raw = global_path.read_bytes()
    history, job, effective = inspect_global_history(raw, node_raw)
    validate_global_sources(job, histories, selected)
    operations, provenance = check_gui_operations(gui_directory, effective)
    values, text = exported_values(job, effective)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / (GLOBAL_HISTORY + ".gz"); archive.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    runtime = output / "runtime"; runtime.mkdir()
    generation_archive = runtime / "generation.json.gz"
    generation_archive.write_bytes(gzip.compress(node_raw["generation.json"], compresslevel=9, mtime=0))
    for filename, key in JSON_EXPORTS.items(): write_json(output / filename, values[key])
    for filename, value in text.items(): (output / filename).write_text(value, encoding="utf-8", newline="\n")
    gui_files = []
    for folder, _, _ in operations:
        destination = output / "gui_operations" / folder.name; destination.mkdir(parents=True)
        for path in sorted(folder.iterdir()):
            if path.is_file() and (path.suffix.lower() == ".png" or path.name in ("gui-operation.json", "gui-operation-failure.json",
                    "preview.json", "job.json", "job-api-original.json", "context.json", "source-manifest.json", "verification-plan.json", "top.v")):
                shutil.copyfile(path, destination / path.name)
                gui_files.append((destination / path.name).relative_to(output).as_posix())
    files = {path.relative_to(output).as_posix(): {"sha256": sha(path), "bytes": path.stat().st_size}
             for path in sorted(output.rglob("*")) if path.is_file()}
    proof, plan = job["checks"], job["context"]["verification_plan"]
    manifest = {"record_kind": RECORD_KIND, "scope": "single_original_matrix_job_S08_RTL_zero_delay_public_boundary_functional_proof",
        "node_evidence_manifest_sha256": node_manifest_sha, "source_reference": source_reference(nodes_manifest, selected),
        "global_history": history_descriptor(archive, raw), "current_global_job_id": job["id"],
        "runtime_generation_history": history_descriptor(generation_archive, node_raw["generation.json"]),
        "runtime_provider_changes": runtime_changes,
        "context_id": job["context_id"], "source_key": job["source_key"], "rtl_sha256": job["rtl_sha256"],
        "verification_plan_sha256": object_hash(plan), "vector_hash": plan["vector_hash"],
        "public_boundary_vector_hash": plan["public_boundary_vector_hash"],
        "testbench_sha256": plan["testbench_sha256"], "public_monitor_sha256": proof["public_monitor_sha256"],
        "instrumented_testbench_sha256": proof["instrumented_testbench_sha256"],
        "actual_output_transfers": proof["actual_output_transfers"],
        "actual_public_stream_transfers": proof["actual_public_stream_transfers"],
        "actual_pe_lane_transfers": proof["actual_pe_lane_transfers"],
        "attempt_count": len(history["jobs"]), "attempts": attempt_metadata(history),
        "manual_human_reviews": sum(r["actor"] == "human" for r in history["reviews"]),
        "manual_RTL_modifications": [], "actual_local_model_origin": True,
        "development_assistant_guidance": "Explicit integration/repair instructions and earlier model candidates may be model input; all exact messages, raw answers, failures and adoptions are retained. No autonomous-success claim.",
        "canonical_job_replaced": False, "node_sources_replaced": False, "S09_synthesis_verified": False,
        "PDK_mapping": False, "layout": False, "DRC": False, "LVS": False, "SDF": False,
        "software_QA_fixtures_are_actual_evidence": False,
        "gui_operation_files": gui_files, "gui_observation_provenance": provenance,
        "files": files}
    verify_manifest_files(nodes_evidence, nodes_manifest["files"])
    require(global_path.read_bytes() == raw and read_histories(data_directory) == node_raw
            and sha(nodes_evidence / "manifest.json") == node_manifest_sha, "Original source changed during export; no completed manifest was written.")
    write_json(output / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".work/projects/npu")
    parser.add_argument("--nodes-evidence", type=Path, default=ROOT / "results/npu_all_nodes_continuous_flow")
    parser.add_argument("--gui-operations", type=Path, default=ROOT / ".work/m2e/global-gui-operations")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = collect(args.data_dir, args.nodes_evidence, args.gui_operations, args.output)
    print(json.dumps({"validation_status": "Passed", "output": str(args.output),
        "current_global_job_id": manifest["current_global_job_id"], "attempt_count": manifest["attempt_count"]}))
    return 0


if __name__ == "__main__": raise SystemExit(main())

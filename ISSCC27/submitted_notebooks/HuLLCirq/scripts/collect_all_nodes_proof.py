"""Preserve the actual M2-E six-node S04-S07 proof, without running anything.

Full byte-exact backend histories, including failures and old prompts, are
losslessly compressed. Strict inspection occurs only on disposable copies.
This collector does not establish S08/global NPU or physical-design success.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from node_spec_evidence import ROOT, load, sha, write_json
from collect_scheduler_evidence import gui_snapshot_provenance, node_manifest, require, unique
from hullcirq.domain import revision_hashes
from hullcirq.implementation_specs import build_node_implementation_spec
from hullcirq.server import make_server, project_envelope
from hullcirq.store import ProjectStore, strict_loads
from hullcirq.verification import build_verification_plan, content_hash, object_hash, verification_template_version

HISTORIES = ("state.json", "generation.json", "workflow.json", "implementation_specs.json")
NODE_KINDS = {"node-control": "npu_control_stream", "node-buffer": "npu_buffer_stream",
              "node-scheduler": "npu_scheduler_stream", "node-pe": "int8_mac_stream",
              "node-post": "npu_post_stream", "node-fifo": "npu_fifo_stream"}
NODE_IDS = tuple(NODE_KINDS)
RECORD_KIND = "actual_GUI_all_six_nodes_local_LLM_S04_S07_continuous_proof"
MAX_HISTORY_BYTES = 512 * 1024 * 1024
JSON_ARTIFACTS = {"candidate_record.json": "candidate", "synthesis_record.json": "synthesis",
                  "netlist_record.json": "netlist", "implementation_spec_record.json": "spec_record",
                  "node_implementation_spec.json": "specification"}


def read_histories(directory):
    return {name: (Path(directory) / name).read_bytes() for name in HISTORIES}


def parse_histories(raw):
    return {name: strict_loads(value.decode("utf-8")) for name, value in raw.items()}


def inspect_copied_histories(raw):
    scratch = ROOT / ".work/m2e/evidence-checks"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="all-nodes-check-", dir=scratch) as temporary:
        directory = Path(temporary)
        for name, value in raw.items():
            (directory / name).write_bytes(value)
        server = make_server("127.0.0.1", 0, ProjectStore(directory), ROOT)
        try:
            envelope = project_envelope(server)
            require(read_histories(directory) == raw, "Strict inspection unexpectedly changed a terminal copied history.")
            return envelope
        finally:
            server.workflow.close()
            server.generation.close()
            server.server_close()


def latest_current(records, node_id, stage_id=None):
    matching = [record for record in records if record["node_id"] == node_id
                and (stage_id is None or record["stage_id"] == stage_id)]
    require(bool(matching), "No saved result for " + node_id + "/" + str(stage_id))
    latest = matching[-1]
    require(all(latest.get(key) == value for key, value in (("execution_status", "Completed"), ("validation_status", "Passed"),
                ("review_status", "Accepted"), ("freshness", "Current"))), "Latest result is not Passed/Accepted/Current: " + node_id + "/" + str(stage_id))
    return latest


def check_gui_operations(directory, selected, design):
    """Completed lossless observations, including recovery after a successful import."""
    operations = []
    for folder in sorted(Path(directory).iterdir()):
        if not folder.is_dir() or not (folder / "gui-actions.json").is_file():
            continue
        action = load(folder / "gui-actions.json")
        require(action.get("record_kind") == "actual_project_GUI_operations"
                and action.get("actor") == "development_assistant_gui_automation" and action.get("page_errors") == [],
                "Require truthful completed actual GUI operations: " + folder.name)
        operations.append((folder, action))
    inputs = [(folder, action) for folder, action in operations if action.get("phase") in ("specify", "verify-imported")]
    require(bool(inputs), "A successful GUI input save or explicit observation of its completed import is required.")
    folder, _ = inputs[-1]
    require(object_hash(load(folder / "gui-saved-design.json")) == object_hash(design), "GUI-saved input differs from the exact final backend design.")
    for node_id, records in selected.items():
        matching = [(folder, action) for folder, action in operations if action.get("node_id") == node_id
                    and action.get("phase") in ("implementation-specs", "observe-implementation-specs")]
        require(bool(matching), "Current S07 GUI observation is missing: " + node_id)
        folder, _ = matching[-1]
        require(object_hash(load(folder / "actual-spec-record.json")) == object_hash(records["effective_spec"]),
                "Latest GUI S07 record differs from the authoritative backend, including wide integers: " + node_id)
        require((folder / "actual-node-implementation-specs.png").is_file(), "Current S07 screenshot is missing: " + node_id)
    return operations


def gui_input_provenance(operations, design):
    folder, action = next((folder, action) for folder, action in reversed(operations) if action.get("phase") in ("specify", "verify-imported"))
    return {"phase": action["phase"], "actions_file": "gui_operations/" + folder.name + "/gui-actions.json",
            "saved_design_file": "gui_operations/" + folder.name + "/gui-saved-design.json", "design_object_hash": object_hash(design),
            "observation_of_successful_prior_import_without_repeating_mutation": action["phase"] == "verify-imported"}


def read_api_operations(directory, histories, selected):
    """Keep actual product API starts distinct from GUI observations."""
    records = []
    if not Path(directory).is_dir():
        return records
    candidates = {job["id"]: job for job in histories["generation.json"]["jobs"]}
    runs = {run["id"]: run for run in histories["workflow.json"]["runs"]}
    for path in sorted(Path(directory).glob("*.json")):
        raw = path.read_bytes()
        action = strict_loads(raw.decode("utf-8"))
        node_id = action.get("node_id")
        require(action.get("record_kind") == "actual_loopback_API_operations" and node_id in selected
                and type(action.get("operations")) is list and action["operations"], "Invalid actual loopback API operation record: " + path.name)
        linked = []
        for operation in action["operations"]:
            require(operation.get("actor") == "development_assistant_API_automation" and type(operation.get("status")) is int,
                    "API automation must not be represented as a human or GUI click: " + path.name)
            request = operation.get("request")
            require(type(request) is dict and request.get("node_id") == node_id, "API request node differs: " + path.name)
            current = selected[node_id]
            if operation.get("route") == "workflow/start":
                require(set(request) == {"stage_id", "node_id", "candidate_id", "revision_id"}
                        and request["stage_id"] in ("local_synthesis", "local_netlist_simulation") and operation["status"] == 202,
                        "Unexpected actual workflow API operation: " + path.name)
                candidate = candidates.get(request["candidate_id"])
                require(candidate is not None and candidate["node_id"] == node_id and candidate["revision_id"] == request["revision_id"], "API workflow source does not exist in raw history: " + path.name)
                if candidate["id"] == current["candidate"]["id"]:
                    result = current["synthesis"] if request["stage_id"] == "local_synthesis" else current["netlist"]
                    linked.append({"route": operation["route"], "stage_id": request["stage_id"], "current_result_id": result["id"]})
            elif operation.get("route") == "implementation-specs/start":
                require(set(request) == {"node_id", "revision_id", "source_run_id"} and operation["status"] == 200,
                        "Unexpected actual S07 API operation: " + path.name)
                source = runs.get(request["source_run_id"])
                require(source is not None and source["node_id"] == node_id and source["revision_id"] == request["revision_id"]
                        and source["stage_id"] == "local_netlist_simulation", "API S07 source is not in raw history: " + path.name)
                if source["id"] == current["netlist"]["id"]:
                    linked.append({"route": operation["route"], "current_result_id": current["spec_record"]["id"]})
            else:
                require(False, "Unsupported actual API operation: " + path.name)
        provenance = {"file": "api_operations/" + path.name, "node_id": node_id, "actor": "development_assistant_API_automation",
                      "operation_count": len(action["operations"]), "links_to_current_results": linked,
                      "classification": "actual_product_loopback_API_starts_not_GUI_clicks"}
        records.append((path, raw, provenance))
    return records


def validate_histories(source_raw, baseline_raw):
    histories, baseline = parse_histories(source_raw), parse_histories(baseline_raw)
    state, generation, workflow, specifications = [histories[name] for name in HISTORIES]
    design = state["design"]
    for name, fields in (("state.json", ("runs", "reviews", "policy_history")),
                         ("generation.json", ("jobs", "reviews", "profiles")),
                         ("workflow.json", ("runs", "reviews")),
                         ("implementation_specs.json", ("specs", "reviews"))):
        for field in fields:
            original, current = baseline[name][field], histories[name][field]
            require(type(original) is list and type(current) is list and len(current) >= len(original)
                    and all(object_hash(left) == object_hash(right) for left, right in zip(original, current)),
                    "A preserved baseline history entry was deleted or changed: " + name + "/" + field)
    require(all(identifier in state["snapshots"] and object_hash(snapshot) == object_hash(state["snapshots"][identifier])
                for identifier, snapshot in baseline["state.json"]["snapshots"].items()), "A preserved original input/version snapshot was deleted or changed.")
    require(design["project"]["id"] == baseline["state.json"]["design"]["project"]["id"] == "hullcirq-npu-4x4-int8", "Wrong original GUI project.")
    require({node["id"] for node in design["nodes"]} == set(NODE_IDS) and len(design["nodes"]) == 6, "Require exactly the six intended node types.")
    require(object_hash(design.get("verification_jobs")) == object_hash(baseline["state.json"]["design"].get("verification_jobs")), "The canonical original matrix job changed, including JSON numeric types.")
    require(all(record["execution_status"] not in ("Queued", "Running") for record in generation["jobs"] + workflow["runs"] + specifications["specs"]), "Wait for all model/tool/extraction operations to terminate.")
    original_pe = next((job for job in reversed(baseline["generation.json"]["jobs"]) if job["node_id"] == "node-pe" and job["validation_status"] == "Passed"), None)
    require(original_pe is not None and original_pe["verification_plan"]["vector_count"] == 42, "The preserved original 42-cycle PE plan is required.")
    envelope = inspect_copied_histories(source_raw)
    require(object_hash(envelope["design"]) == object_hash(design), "Strict current source differs from raw saved design.")
    for stage in envelope["workflow"]:
        if stage["id"] in ("global_settings", "graph_editor", "specifications"):
            require(all(stage.get(key) == value for key, value in (("validation_status", "Passed"), ("review_status", "Accepted"), ("freshness", "Current"))), "Current input checks must be Passed and adopted.")
    selected, old_ids = {}, {job["id"] for job in baseline["generation.json"]["jobs"]}
    for node_id, kind in NODE_KINDS.items():
        job = latest_current(envelope["generation"]["jobs"], node_id)
        synth = latest_current(envelope["workflow_runs"], node_id, "local_synthesis")
        simulation = latest_current(envelope["workflow_runs"], node_id, "local_netlist_simulation")
        effective_spec = latest_current(envelope["implementation_specs"], node_id)
        candidate = unique(generation["jobs"], job["id"])
        synthesis = unique(workflow["runs"], synth["id"])
        netlist = unique(workflow["runs"], simulation["id"])
        spec = unique(specifications["specs"], effective_spec["id"])
        generation_node = next(item for item in envelope["generation"]["nodes"] if item["node_id"] == node_id)
        spec_node = next(item for item in envelope["implementation_spec_nodes"] if item["node_id"] == node_id)
        require(generation_node["accepted_job_id"] == generation_node["latest_job_id"] == candidate["id"] and spec_node["accepted_spec_id"] == spec["id"], "Latest node adoption identity differs: " + node_id)
        for stage_id, record in (("local_synthesis", synthesis), ("local_netlist_simulation", netlist)):
            adopted = next(item for item in envelope["workflow_nodes"] if item["node_id"] == node_id and item["stage_id"] == stage_id)
            require(adopted["accepted_run_id"] == record["id"], "Adopted workflow result differs: " + node_id + "/" + stage_id)
        require(candidate["origin"] == "local_llm" and candidate["profile"]["execution_location"] == "Local" and candidate["id"] not in old_ids,
                "A newly executed local-model candidate is required for each current node: " + node_id)
        require(candidate["revision_id"] == state["revision"]["id"], "All six candidates must use the same final saved revision: " + node_id)
        source = state["snapshots"][candidate["revision_id"]]
        require(object_hash(source) == object_hash(design) and revision_hashes(source)["semantic_hash"] == state["revision"]["semantic_hash"], "Candidate snapshot differs from final saved design: " + node_id)
        require(synthesis["candidate_id"] == netlist["candidate_id"] == spec["candidate_id"] == candidate["id"]
                and netlist["prior_run_id"] == synthesis["id"] and spec["source_run_id"] == netlist["id"], "S04-S07 lineage differs: " + node_id)
        plan = candidate["verification_plan"]
        require(plan["kind"] == kind and object_hash(plan) == object_hash(build_verification_plan(source, node_id, verification_template_version(plan))), "Frozen plan cannot be exactly rebuilt: " + node_id)
        require(object_hash(plan) == object_hash(synthesis["verification_plan"]) == object_hash(netlist["verification_plan"]), "RTL and netlist did not inherit identical plans: " + node_id)
        require(content_hash(candidate["rtl"]) == candidate["rtl_sha256"] == synthesis["rtl_sha256"] == netlist["rtl_sha256"], "RTL hash lineage differs: " + node_id)
        require(synthesis["netlist"] == netlist["netlist"] and content_hash(netlist["netlist"]) == synthesis["netlist_sha256"] == netlist["netlist_sha256"], "Exact S05 netlist not used by S06: " + node_id)
        rebuilt = build_node_implementation_spec(source, candidate, synthesis, netlist)
        require(object_hash(rebuilt) == object_hash(spec["specification"]) == spec["specification_sha256"], "Original S07 proof cannot be reconstructed: " + node_id)
        if node_id == "node-pe":
            require(object_hash(plan) == object_hash(original_pe["verification_plan"]), "Original PE 42-cycle plan changed.")
        else:
            require(sum(object_hash(job) == object_hash(plan["contract"]["source_job"]) for job in design["verification_jobs"]) == 1,
                    "Projected contract does not reference one exact canonical job: " + node_id)
        selected[node_id] = {"candidate": candidate, "synthesis": synthesis, "netlist": netlist, "spec_record": spec,
                             "specification": rebuilt, "effective_spec": effective_spec}
    return histories, selected


def compress_histories(directory, raw):
    directory.mkdir(parents=True)
    metadata = {}
    for name, source in raw.items():
        require(0 < len(source) <= MAX_HISTORY_BYTES, "A history exceeds the bounded replay size: " + name)
        path = directory / (name + ".gz")
        path.write_bytes(gzip.compress(source, compresslevel=9, mtime=0))
        metadata[name] = {"archive": path.name, "compression": "gzip", "archive_sha256": sha(path), "archive_bytes": path.stat().st_size,
                          "decompressed_sha256": hashlib.sha256(source).hexdigest(), "decompressed_bytes": len(source)}
    return metadata


def node_metadata(node_id, records):
    candidate = records["candidate"]
    plan = candidate["verification_plan"]
    return {**node_manifest(node_id, records), "kind": plan["kind"], "coverage": plan["coverage"],
            "candidate_origin": candidate["origin"], "model": candidate["profile"]["model"],
            "generation_operation": candidate["operation"], "base_job_id": candidate["base_job_id"]}


def export_nodes(directory, selected):
    nodes = {}
    for node_id, records in selected.items():
        folder = directory / "nodes" / node_id
        folder.mkdir(parents=True)
        for filename, key in JSON_ARTIFACTS.items():
            write_json(folder / filename, records[key])
        plan = records["candidate"]["verification_plan"]
        vectors = plan.get("expanded_vectors", plan["contract"].get("vectors"))
        for filename, value in (("verification_plan.json", plan), ("reference_trace.json", plan["reference_trace"]), ("vectors.json", vectors)):
            write_json(folder / filename, value)
        for filename, value in (("candidate.v", records["candidate"]["rtl"]), ("netlist.v", records["synthesis"]["netlist"]), ("contract_tb.v", plan["testbench"])):
            (folder / filename).write_text(value, encoding="utf-8", newline="\n")
        nodes[node_id] = node_metadata(node_id, records)
    return nodes


def collect(data_directory, baseline_directory, gui_directory, output, api_directory=ROOT / ".work/m2e/api-operations"):
    output = Path(output)
    require(not output.exists() or not any(output.iterdir()), "Use a new empty result directory; existing evidence is never replaced.")
    source_raw, baseline_raw = read_histories(data_directory), read_histories(baseline_directory)
    histories, selected = validate_histories(source_raw, baseline_raw)
    operations = check_gui_operations(gui_directory, selected, histories["state.json"]["design"])
    provenance = gui_snapshot_provenance(operations, selected)
    api_operations = read_api_operations(api_directory, histories, selected)
    require(read_histories(data_directory) == source_raw and read_histories(baseline_directory) == baseline_raw, "Live/baseline source changed during strict inspection.")
    output.mkdir(parents=True, exist_ok=True)
    compressed = {"current": compress_histories(output / "histories", source_raw), "baseline": compress_histories(output / "original_runtime", baseline_raw)}
    write_json(output / "design.json", histories["state.json"]["design"])
    nodes = export_nodes(output, selected)
    gui_files = []
    for folder, _ in operations:
        destination = output / "gui_operations" / folder.name
        destination.mkdir(parents=True)
        for path in sorted(folder.iterdir()):
            if path.is_file() and (path.suffix.lower() == ".png" or path.name in ("gui-actions.json", "actual-spec-record.json", "gui-saved-design.json")):
                shutil.copyfile(path, destination / path.name)
                gui_files.append((destination / path.name).relative_to(output).as_posix())
    if api_operations:
        (output / "api_operations").mkdir()
        for path, raw, _ in api_operations:
            (output / "api_operations" / path.name).write_bytes(raw)
    files = {path.relative_to(output).as_posix(): {"sha256": sha(path), "bytes": path.stat().st_size} for path in sorted(output.rglob("*")) if path.is_file()}
    state, generation, workflow = [histories[name] for name in HISTORIES[:3]]
    baseline_generation = parse_histories(baseline_raw)["generation.json"]
    manifest = {"record_kind": RECORD_KIND, "scope": "all_six_node_types_S04_S07_in_one_final_GUI_revision_not_integrated_NPU",
                "project_id": state["design"]["project"]["id"], "current_revision_id": state["revision"]["id"],
                "current_design_semantic_hash": state["revision"]["semantic_hash"], "canonical_job_hash": object_hash(state["design"]["verification_jobs"]),
                "nodes": nodes, "accepted_current_nodes": 6, "required_nodes": 6, "compressed_histories": compressed,
                "historical_generation_attempts": len(generation["jobs"]), "new_generation_attempts": len(generation["jobs"]) - len(baseline_generation["jobs"]),
                "attempts": [{key: job.get(key) for key in ("id", "node_id", "revision_id", "operation", "base_job_id", "origin", "execution_status", "validation_status", "review_status")} for job in generation["jobs"]],
                "historical_tool_runs": len(workflow["runs"]), "review_policy": state["review_policy"],
                "manual_human_reviews": sum(review.get("actor") == "human" for history in histories.values() for review in history["reviews"]),
                "GUI_operator": "development_assistant_under_explicit_user_instruction", "manual_RTL_modifications": [],
                "development_assistant_guidance": "Specific hardware/control/wiring repair instructions and previous local-model candidates may be model input; all exact instructions, contexts, raw replies and failures remain in the compressed original generation history. No autonomous-success claim.",
                "canonical_job_replaced": False, "PE_original_42_cycle_plan_identical": True, "all_selected_candidates_new_local_model_calls": True,
                "original_baseline_history_prefix_and_snapshots_preserved": True,
                "RTL_and_netlist_use_same_frozen_plan": True, "full_NPU_verified": False, "S08_collected": False, "PDK_mapping": False, "SDF": False,
                "gui_operation_files": gui_files, "gui_snapshot_provenance": provenance,
                "gui_input_provenance": gui_input_provenance(operations, state["design"]),
                "api_operation_files": [record["file"] for _, _, record in api_operations],
                "api_operation_provenance": [record for _, _, record in api_operations],
                "execution_operator_scope": "Local-model starts were GUI operations; recorded loopback API tool/extraction starts and later GUI observations retain their distinct actors.",
                "authoritative_evidence": "Byte-exact decompressed backend histories, selected source records and latest lossless API GUI observations; software QA fixtures are not candidate evidence.",
                "file_budget": {"review_threshold_bytes": 10_000_000, "files_above_review_threshold": {name: item["bytes"] for name, item in files.items() if item["bytes"] > 10_000_000},
                                "total_archive_file_bytes": sum(item["bytes"] for item in files.values()), "total_original_history_bytes": sum(len(value) for value in source_raw.values())},
                "files": files}
    require(read_histories(data_directory) == source_raw and read_histories(baseline_directory) == baseline_raw, "Source changed during export; no completed manifest was written.")
    write_json(output / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".work/projects/npu")
    parser.add_argument("--baseline-dir", type=Path, default=ROOT / ".work/m2e/original_runtime")
    parser.add_argument("--gui-operations", type=Path, default=ROOT / ".work/m2e/gui-operations")
    parser.add_argument("--api-operations", type=Path, default=ROOT / ".work/m2e/api-operations")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = collect(args.data_dir, args.baseline_dir, args.gui_operations, args.output, args.api_operations)
    print(json.dumps({"validation_status": "Passed", "output": str(args.output), "nodes": manifest["nodes"], "file_budget": manifest["file_budget"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

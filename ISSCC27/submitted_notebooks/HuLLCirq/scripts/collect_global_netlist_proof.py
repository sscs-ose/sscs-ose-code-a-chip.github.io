"""Preserve adopted S09/S10 evidence without starting a model or EDA tool.

The independent workflow history is compressed byte exactly. The five prior
source histories and the immutable S08/six-node archives must remain exact.
Strict product validation operates only on disposable copies.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile

from collect_all_nodes_proof import HISTORIES, MAX_HISTORY_BYTES, ROOT, read_histories, require
from collect_global_proof import GLOBAL_HISTORY, history_descriptor
from replay_all_nodes_proof import decode_histories, verify_manifest_files
from replay_global_proof import decode_global_history, decode_history, inspect_global_evidence
from node_spec_evidence import load, sha, write_json
from hullcirq.global_generation import instrument_public_testbench
from hullcirq.server import make_server
from hullcirq.store import ProjectStore, strict_loads
from hullcirq.verification import content_hash, object_hash

WORKFLOW_HISTORY = "global_workflow.json"
STAGES = ("global_synthesis", "global_netlist_simulation")
RECORD_KIND = "actual_original_GUI_job_S09_S10_generic_whole_netlist_proof"
SCOPE = "single_original_matrix_job_technology_independent_zero_delay_whole_netlist_public_boundary_proof"
JSON_EXPORTS = {
    "synthesis_record.json": "synthesis", "synthesis_effective_record.json": "effective_synthesis",
    "netlist_record.json": "simulation", "netlist_effective_record.json": "effective_simulation",
    "source_manifest.json": "source_manifest", "verification_plan.json": "plan",
    "synthesis_checks.json": "synthesis_checks", "actual_netlist_checks.json": "simulation_checks",
}
TEXT_EXPORTS = ("candidate_top.v", "netlist.v", "original_job_tb.v", "instrumented_job_tb.v", "public_monitor.v", "synthesis.ys")


def decode_workflow_history(directory, metadata):
    """Decode one fixed filename with bounded expansion and strict JSON types."""
    fields = {"archive", "compression", "archive_sha256", "archive_bytes", "decompressed_sha256", "decompressed_bytes"}
    require(type(metadata) is dict and set(metadata) == fields and metadata["compression"] == "gzip"
            and metadata["archive"] == WORKFLOW_HISTORY + ".gz", "Invalid fixed global-workflow history descriptor.")
    path = Path(directory) / metadata["archive"]
    require(type(metadata["archive_bytes"]) is int and metadata["archive_bytes"] == path.stat().st_size
            and sha(path) == metadata["archive_sha256"], "Global-workflow compressed archive differs.")
    length = metadata["decompressed_bytes"]
    require(type(length) is int and 0 < length <= MAX_HISTORY_BYTES, "Invalid or oversized global-workflow expansion length.")
    with gzip.open(path, "rb") as stream:
        raw = stream.read(length + 1)
    require(len(raw) == length and hashlib.sha256(raw).hexdigest() == metadata["decompressed_sha256"],
            "Global-workflow decompressed original bytes differ.")
    strict_loads(raw.decode("utf-8"))
    return raw


def original_source_histories(global_evidence, nodes_evidence, global_manifest, nodes_manifest):
    """Read the exact five source histories bound by the prior actual proof."""
    raw = decode_histories(nodes_evidence, "histories", nodes_manifest["compressed_histories"]["current"])
    raw["generation.json"] = decode_history(Path(global_evidence) / "runtime", global_manifest["runtime_generation_history"], "generation.json")
    raw[GLOBAL_HISTORY] = decode_global_history(global_evidence, global_manifest["global_history"])
    return raw


def require_source_bytes(current, original):
    require(type(current) is dict and set(current) == set(original) == {*HISTORIES, GLOBAL_HISTORY}
            and all(type(value) is bytes and value == original[name] for name, value in current.items()),
            "The original GUI inputs, six sources, S08 candidates/reviews/profiles/epochs must remain byte exact.")


def read_sources(directory):
    return {**read_histories(directory), GLOBAL_HISTORY: (Path(directory) / GLOBAL_HISTORY).read_bytes()}


def terminal_history(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_HISTORY_BYTES, "Global-workflow history is empty or oversized.")
    history = strict_loads(raw.decode("utf-8"))
    require(type(history) is dict and type(history.get("runs")) is list and history["runs"]
            and type(history.get("reviews")) is list and all(type(run) is dict
                and run.get("execution_status") not in ("Queued", "Running") for run in history["runs"]),
            "Wait for all S09/S10 attempts to terminate; failures and cancellation history are retained.")
    return history


def latest_adopted(runs, stage):
    matches = [run for run in runs if run.get("stage_id") == stage]
    require(matches, "No actual saved workflow result for " + stage)
    run = matches[-1]
    require(all(run.get(key) == value for key, value in (("execution_status", "Completed"),
        ("validation_status", "Passed"), ("review_status", "Accepted"), ("freshness", "Current"))),
        "The latest actual result must be Passed/Accepted/Current: " + stage)
    return run


def inspect_workflow_history(raw, source_raw):
    history = terminal_history(raw)
    scratch = ROOT / ".work/m2f/evidence-checks"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="global-netlist-check-", dir=scratch) as name:
        folder = Path(name)
        for filename, value in source_raw.items():
            (folder / filename).write_bytes(value)
        (folder / WORKFLOW_HISTORY).write_bytes(raw)
        server = make_server("127.0.0.1", 0, ProjectStore(folder), ROOT)
        try:
            manager = server.global_workflow
            envelope = manager.envelope()["global_workflow"]
            effective = {stage: latest_adopted(envelope["runs"], stage) for stage in STAGES}
            selected = {}
            for stage, record in effective.items():
                matches = [run for run in history["runs"] if run["id"] == record["id"]]
                require(len(matches) == 1, "Selected workflow ID is missing or ambiguous.")
                selected[stage] = copy.deepcopy(matches[0])
            require_source_bytes(read_sources(folder), source_raw)
            require((folder / WORKFLOW_HISTORY).read_bytes() == raw,
                    "Strict inspection changed a copied terminal global workflow history.")
            return history, selected[STAGES[0]], selected[STAGES[1]], effective[STAGES[0]], effective[STAGES[1]]
        finally:
            server.workflow.close(); server.generation.close(); server.server_close()


def validate_lineage(synthesis, simulation, global_job):
    """Cross-stage checks independent of checksum strings in the new archive."""
    context = global_job["context"]
    manifest, plan = context["source_manifest"], context["verification_plan"]
    require(synthesis["stage_id"] == STAGES[0] and simulation["stage_id"] == STAGES[1]
            and simulation["prior_run_id"] == synthesis["id"], "S10 does not use the selected S09 result.")
    for run in (synthesis, simulation):
        require(run["global_job_id"] == global_job["id"] and run["revision_id"] == global_job["revision_id"]
                and run["global_rtl_sha256"] == global_job["rtl_sha256"] == content_hash(global_job["rtl"])
                and run["global_context_id"] == global_job["context_id"]
                and object_hash(run["source_manifest"]) == object_hash(manifest) == run["source_manifest_sha256"]
                and object_hash(run["verification_plan"]) == object_hash(plan) == run["verification_plan_sha256"]
                and run["vector_hash"] == plan["vector_hash"] and run["testbench_sha256"] == plan["testbench_sha256"]
                and run["public_boundary_vector_hash"] == plan["public_boundary_vector_hash"],
                "S09/S10 sources or frozen original GUI plan differ from adopted S08.")
        checks = run["checks"]
        require(run["execution_status"] == "Completed" and run["validation_status"] == "Passed"
                and run["review_status"] == "Accepted" and checks.get("validation_status") == "Passed"
                and checks.get("executed") is True and type(checks.get("exit_code")) is int and checks["exit_code"] == 0,
                "Required actual executed tool proof is incomplete.")
    require(type(synthesis["netlist"]) is str and synthesis["netlist"]
            and synthesis["netlist"] == simulation["netlist"]
            and content_hash(synthesis["netlist"]) == synthesis["netlist_sha256"] == simulation["netlist_sha256"],
            "S10 did not retain the exact synthesized whole netlist.")
    require_netlist_only(simulation["checks"], synthesis["netlist_sha256"])
    return manifest, plan


def require_netlist_only(checks, netlist_sha):
    require(checks.get("source_rtl_linked") is False
            and object_hash(checks.get("compiled_design_sources")) == object_hash([{"file": "netlist.v", "sha256": netlist_sha}]),
            "S10 must compile the whole synthesized netlist only, without source RTL relinking.")


def exported_values(synthesis, simulation, effective_synthesis, effective_simulation, global_job):
    from hullcirq.global_workflow import compiler_netlist_public_hierarchy
    manifest, plan = validate_lineage(synthesis, simulation, global_job)
    proof = simulation["checks"]
    hierarchy = compiler_netlist_public_hierarchy(proof["hierarchy_scope_lines"], manifest)
    instrumented, monitor = instrument_public_testbench(plan, hierarchy)
    require(content_hash(instrumented) == proof["instrumented_testbench_sha256"]
            and content_hash(monitor) == proof["public_monitor_sha256"]
            and monitor == proof["public_monitor_source"], "Saved S10 compiler-discovered monitor differs.")
    script = synthesis["checks"]["synthesis_script"]
    values = {"synthesis": synthesis, "simulation": simulation,
        "effective_synthesis": effective_synthesis, "effective_simulation": effective_simulation,
        "source_manifest": manifest, "plan": plan,
        "synthesis_checks": synthesis["checks"], "simulation_checks": proof}
    text = dict(zip(TEXT_EXPORTS, (global_job["rtl"], synthesis["netlist"], plan["testbench"], instrumented, monitor, script)))
    for entry in manifest["nodes"]:
        text["sources/" + entry["node_id"] + ".v"] = entry["rtl"]
    for stage, checks in (("synthesis", synthesis["checks"]), ("netlist", proof)):
        text["logs/" + stage + "_stdout.txt"] = checks["stdout"]
        text["logs/" + stage + "_stderr.txt"] = checks["stderr"]
        for index, command in enumerate(checks["commands"]):
            for stream in ("stdout", "stderr"):
                text[f"logs/{stage}_command_{index:02d}_{stream}.txt"] = command[stream]
    return values, text


def attempt_metadata(history):
    return [{key: run.get(key) for key in ("id", "stage_id", "revision_id", "global_job_id", "prior_run_id",
        "execution_status", "validation_status", "review_status")} for run in history["runs"]]


def proof_metadata(history, synthesis, simulation, global_job):
    plan, proof = global_job["context"]["verification_plan"], simulation["checks"]
    return {"source_global_job_id": global_job["id"], "source_revision_id": global_job["revision_id"],
        "source_context_id": global_job["context_id"], "global_rtl_sha256": global_job["rtl_sha256"],
        "source_manifest_sha256": object_hash(global_job["context"]["source_manifest"]),
        "synthesis_run_id": synthesis["id"], "netlist_run_id": simulation["id"],
        "netlist_sha256": synthesis["netlist_sha256"], "verification_plan_sha256": object_hash(plan),
        "vector_hash": plan["vector_hash"], "public_boundary_vector_hash": plan["public_boundary_vector_hash"],
        "testbench_sha256": plan["testbench_sha256"], "public_monitor_sha256": proof["public_monitor_sha256"],
        "instrumented_testbench_sha256": proof["instrumented_testbench_sha256"],
        "actual_output_transfers": proof["actual_output_transfers"],
        "actual_public_stream_transfers": proof["actual_public_stream_transfers"],
        "actual_pe_lane_transfers": proof["actual_pe_lane_transfers"],
        "elaborated_instance_counts": proof["elaborated_instance_counts"],
        "attempt_count": len(history["runs"]), "attempts": attempt_metadata(history),
        "manual_human_reviews": sum(review.get("actor") == "human" for review in history["reviews"])}


def collect(data_directory, global_evidence, nodes_evidence, output):
    output, global_evidence, nodes_evidence = map(Path, (output, global_evidence, nodes_evidence))
    require(not output.exists() or not any(output.iterdir()), "Use a new empty evidence directory; previous results are preserved.")
    global_sha, nodes_sha = sha(global_evidence / "manifest.json"), sha(nodes_evidence / "manifest.json")
    global_manifest, nodes_manifest, global_job = inspect_global_evidence(global_evidence, nodes_evidence)
    source_raw = original_source_histories(global_evidence, nodes_evidence, global_manifest, nodes_manifest)
    require_source_bytes(read_sources(data_directory), source_raw)
    path = Path(data_directory) / WORKFLOW_HISTORY; raw = path.read_bytes()
    history, synthesis, simulation, effective_synthesis, effective_simulation = inspect_workflow_history(raw, source_raw)
    values, text = exported_values(synthesis, simulation, effective_synthesis, effective_simulation, global_job)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / (WORKFLOW_HISTORY + ".gz")
    archive.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    for filename, key in JSON_EXPORTS.items():
        write_json(output / filename, values[key])
    for filename, value in text.items():
        target = output / filename; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value, encoding="utf-8", newline="\n")
    files = {path.relative_to(output).as_posix(): {"sha256": sha(path), "bytes": path.stat().st_size}
             for path in sorted(output.rglob("*")) if path.is_file()}
    manifest = {"record_kind": RECORD_KIND, "scope": SCOPE,
        "source_global_manifest_sha256": global_sha, "source_node_manifest_sha256": nodes_sha,
        "global_workflow_history": history_descriptor(archive, raw),
        "unchanged_original_source_histories": {name: {"sha256": hashlib.sha256(value).hexdigest(), "bytes": len(value)}
            for name, value in source_raw.items()},
        **proof_metadata(history, synthesis, simulation, global_job),
        "model_calls": 0, "manual_RTL_modifications": [], "canonical_job_replaced": False,
        "original_source_histories_rewritten": False, "independent_append_only_global_workflow_history": True,
        "netlist_compile_sources": ["netlist.v"], "source_RTL_relinked_during_S10": False,
        "technology_independent": True, "zero_delay": True, "formal_equivalence": False,
        "PDK_mapping": False, "STA": False, "layout": False, "DRC": False, "LVS": False, "SDF": False,
        "software_QA_fixtures_are_actual_evidence": False, "files": files}
    verify_manifest_files(global_evidence, global_manifest["files"])
    verify_manifest_files(nodes_evidence, nodes_manifest["files"])
    require_source_bytes(read_sources(data_directory), source_raw)
    require(path.read_bytes() == raw and sha(global_evidence / "manifest.json") == global_sha
            and sha(nodes_evidence / "manifest.json") == nodes_sha,
            "Source history/archive changed during export; no completed manifest was written.")
    write_json(output / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".work/projects/npu")
    parser.add_argument("--global-evidence", type=Path, default=ROOT / "results/npu_global_continuous_flow")
    parser.add_argument("--nodes-evidence", type=Path, default=ROOT / "results/npu_all_nodes_continuous_flow")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = collect(args.data_dir, args.global_evidence, args.nodes_evidence, args.output)
    print(json.dumps({"validation_status": "Passed", "output": str(args.output),
        "synthesis_run_id": manifest["synthesis_run_id"], "netlist_run_id": manifest["netlist_run_id"]}))
    return 0


if __name__ == "__main__": raise SystemExit(main())

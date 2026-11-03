"""Verify portable S13 archival evidence without models, EDA or live writes.

This checks saved raw bytes, reports, metrics, worker proofs and the original
S12/S11/GUI lineage. It does not perform an independent LVS execution. The report
distinguishes archive integrity from the selected circuit's LVS outcome.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import tempfile

from collect_lvs_proof import (LVS_HISTORY, MAX_HISTORY_BYTES, PHYSICAL_SOURCES, RECORD_KIND, SCOPE, SOURCE_HISTORIES,
    declared_files, digest, normalized_history_hashes, require, safe_relative, sha, terminal_history, validate_history_selection,
    validate_lineage, validate_reviews)
from replay_physical_proof import archive_path, decode_physical_history, inspect_evidence as inspect_layout_evidence, read_json, valid_sha, verify_files
from replay_drc_proof import decode_history as decode_drc_history, inspect_evidence as inspect_drc_evidence
from hullcirq.store import strict_loads
from hullcirq.verification import object_hash

ROOT = Path(__file__).resolve().parents[1]


def decode_history(directory, descriptor, filename):
    require(type(descriptor) is dict and set(descriptor) == {"archive", "compression", "archive_sha256", "archive_bytes", "decompressed_sha256", "decompressed_bytes"}
            and descriptor["archive"] == filename and descriptor["compression"] == "gzip"
            and valid_sha(descriptor["archive_sha256"]) and valid_sha(descriptor["decompressed_sha256"])
            and type(descriptor["archive_bytes"]) is int and descriptor["archive_bytes"] > 0
            and type(descriptor["decompressed_bytes"]) is int and 0 < descriptor["decompressed_bytes"] <= MAX_HISTORY_BYTES,
            "Invalid bounded lossless history descriptor.")
    path = archive_path(directory, filename)
    require(path.stat().st_size == descriptor["archive_bytes"] and sha(path) == descriptor["archive_sha256"], "Compressed history changed.")
    with gzip.open(path, "rb") as stream:
        raw = stream.read(descriptor["decompressed_bytes"] + 1)
    require(len(raw) == descriptor["decompressed_bytes"] and digest(raw) == descriptor["decompressed_sha256"], "History expansion or raw hash changed.")
    return raw


def verify_attempt(directory, entry, run, reviews):
    require(type(entry) is dict and entry.get("original_run_id") == run["id"]
            and entry.get("record_object_sha256") == object_hash(run) and entry.get("original_record_hash") == run["record_hash"]
            and all(entry.get(k) == run[k] for k in ("execution_status", "validation_status", "review_status"))
            and type(entry.get("files")) is list and type(entry.get("omitted_files")) is list,
            "Attempt export differs from its complete original LVS record.")
    prefix = "attempts/" + run["id"] + "/"
    require(object_hash(read_json(archive_path(directory, prefix + "run_record.json"))) == object_hash(run)
            and object_hash(read_json(archive_path(directory, prefix + "reviews.json"))) == object_hash([r for r in reviews if r["run_id"] == run["id"]]),
            "A per-attempt record or review was relabeled.")
    result = run["checks"]; declared = declared_files(result); seen = {}
    require(entry.get("directory") == (None if result.get("artifacts_directory") is None else str(Path(result["artifacts_directory"]).resolve())),
            "The original diagnostic-directory provenance changed.")
    for item in entry["files"]:
        require(type(item) is dict and valid_sha(item.get("sha256")) and type(item.get("bytes")) is int and item["bytes"] >= 0,
                "Invalid raw attempt-export descriptor.")
        relative = item.get("relative_path"); safe_relative(relative)
        require(relative not in seen, "Duplicate raw attempt-export path.")
        require(type(item.get("source_path")) is str and Path(item["source_path"]).resolve()
                == (Path(result["artifacts_directory"]) / Path(*safe_relative(relative).parts)).resolve(),
                "A raw attempt source path differs from its original run directory.")
        path = archive_path(directory, item.get("export_path"))
        require(path.stat().st_size == item["bytes"] and sha(path) == item["sha256"], "Raw attempted output bytes changed.")
        if relative in declared:
            require(all(declared[relative][k] == item[k] for k in ("sha256", "bytes"))
                    and item.get("original_recorded_raw_sha256") == declared[relative]["sha256"], "An originally declared raw hash changed.")
        seen[relative] = path
    require(set(declared) <= set(seen), "A declared original artifact is missing from its attempt archive.")
    commands = result.get("commands", [])
    require(object_hash(read_json(archive_path(directory, prefix + "logs/commands.json"))) == object_hash(commands), "Saved command export changed.")
    for field in ("stdout", "stderr"):
        require(archive_path(directory, prefix + "logs/adapter_" + field + ".txt").read_bytes() == result.get(field, "").encode("utf-8"),
                "Saved adapter output string changed.")
        for index, command in enumerate(commands):
            require(archive_path(directory, prefix + f"logs/command_{index:02d}_" + field + ".txt").read_bytes() == command[field].encode("utf-8"),
                    "Saved command output string changed.")
    if result.get("checks", {}).get("lvs", {}).get("completed") is True:
        from hullcirq.lvs_tools import validate_lvs_result
        # Rehydrate exact paths from deduplicated raw bytes. These disposable
        # copies are verification input only; no original path or tool is used.
        with tempfile.TemporaryDirectory(prefix="hullcirq-lvs-archive-check-") as name:
            root = Path(name)
            for relative, source in seen.items():
                target = root / Path(*safe_relative(relative).parts)
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(source.read_bytes())
            validate_lvs_result(result, run["drc_snapshot"], run["layout_snapshot"], run["runtime_configuration"], artifact_root=root)
    return seen


def inspect_evidence(directory):
    directory = Path(directory).resolve(); manifest = read_json(directory / "manifest.json")
    require(manifest.get("record_kind") == RECORD_KIND and manifest.get("scope") == SCOPE
            and manifest.get("collection_validation_status") == "Passed", "Use the actual preserved S13 evidence archive.")
    verify_files(directory, manifest["files"])
    baseline = read_json(directory / "source_baseline.json")
    require(sha(directory / "source_baseline.json") == manifest["source_baseline_sha256"], "The pre-S13 baseline changed.")
    hashes = normalized_history_hashes(baseline)
    layout_directory = directory.parent / "npu_layout_continuous_flow"
    drc_directory = directory.parent / "npu_drc_continuous_flow"
    layout_manifest, layout = inspect_layout_evidence(layout_directory)
    drc_manifest, drc = inspect_drc_evidence(drc_directory)
    require(sha(layout_directory / "manifest.json") == manifest["source_layout_manifest_sha256"]
            == baseline["preexisting_files"].get("results/npu_layout_continuous_flow/manifest.json")
            and sha(drc_directory / "manifest.json") == manifest["source_drc_manifest_sha256"]
            == baseline["preexisting_files"].get("results/npu_drc_continuous_flow/manifest.json")
            and layout["id"] == manifest["layout_run_id"] == drc["layout_run_id"]
            and drc["id"] == manifest["drc_run_id"]
            and object_hash(drc["layout_snapshot"]) == object_hash(layout), "The exact original S11/S12 proof chain was replaced.")
    physical_raw = decode_physical_history(layout_directory, layout_manifest["physical_workflow_history"])
    drc_raw = decode_drc_history(drc_directory, drc_manifest["drc_workflow_history"], "drc_workflow.json.gz")
    require(digest(physical_raw) == hashes["physical_workflow.json"], "The source S11 history differs from the pre-S13 baseline.")
    require(digest(drc_raw) == hashes["drc_workflow.json"], "The source S12 history differs from the pre-S13 baseline.")
    physical = strict_loads(physical_raw.decode("utf-8"))
    drc_history = strict_loads(drc_raw.decode("utf-8"))
    original = manifest.get("unchanged_original_source_histories")
    require(type(original) is dict and set(original) == set(SOURCE_HISTORIES), "All eight original source hashes are required.")
    for name in SOURCE_HISTORIES:
        expected = {"sha256": digest(drc_raw), "bytes": len(drc_raw)} if name == "drc_workflow.json" else drc_manifest["unchanged_original_source_histories"][name]
        require(object_hash(original[name]) == object_hash(expected) and original[name]["sha256"] == hashes[name], "Original GUI/S11/S12 lineage changed: " + name)
    prior = {k: v for k, v in baseline["preexisting_files"].items() if k.startswith("results/")}
    require(prior and object_hash(prior) == object_hash(manifest["unchanged_preexisting_result_files"]), "Prior result protection was weakened.")
    for relative, checksum in prior.items():
        require(sha(archive_path(directory.parent.parent, relative)) == checksum, "A prior immutable result changed: " + relative)
    require(object_hash(manifest["unchanged_default_histories"]) == object_hash(baseline["default_histories"]), "Default-project preservation summary changed.")
    state_raw = decode_history(directory, manifest["original_state_history"], "original_state.json.gz")
    require(digest(state_raw) == hashes["state.json"], "The original GUI state or policy history changed.")
    raw = decode_history(directory, manifest["lvs_workflow_history"], LVS_HISTORY + ".gz")
    history = terminal_history(raw); selected = validate_history_selection(history)
    validate_reviews(history, strict_loads(state_raw.decode("utf-8")))
    require(type(manifest.get("attempt_count")) is int and manifest["attempt_count"] == len(history["runs"])
            and type(manifest.get("attempts")) is list and len(manifest["attempts"]) == len(history["runs"]), "Every original LVS attempt must remain archived.")
    exported = {a.get("original_run_id"): a for a in manifest["attempts"]}
    require(len(exported) == len(history["runs"]), "Attempt IDs are duplicated or incomplete.")
    for run in history["runs"]:
        validate_lineage(run, layout, drc, physical, drc_history)
        verify_attempt(directory, exported[run["id"]], run, history["reviews"])
    for name, value in (("lvs_record.json", selected), ("lvs_checks.json", selected["checks"]), ("reviews.json", history["reviews"]),
                        ("layout_record.json", layout), ("drc_record.json", drc), ("source_identity.json", selected["source_identity"]),
                        ("source_inputs.json", selected["source_inputs"]),
                        ("lvs_runtime_configuration.json", selected["runtime_configuration"])):
        require(object_hash(read_json(directory / name)) == object_hash(value), "Saved JSON export differs: " + name)
    require(all(manifest.get(key) == selected[field] for key, field in (("lvs_run_id", "id"), ("layout_record_sha256", "layout_record_sha256"),
                ("drc_run_id", "drc_run_id"), ("drc_record_sha256", "drc_record_sha256"),
                ("input_netlist_sha256", "input_netlist_sha256"), ("input_powered_netlist_sha256", "input_powered_netlist_sha256"),
                ("input_gds_sha256", "input_gds_sha256"), ("configuration_sha256", "configuration_sha256"), ("source_revision_id", "revision_id"),
                ("selected_validation_status", "validation_status"), ("selected_execution_status", "execution_status"), ("selected_review_status", "review_status"))),
            "The selected result summary changed its actual status or source lineage.")
    require(object_hash(manifest.get("source_inputs")) == object_hash(selected["source_inputs"]),
            "The exact input descriptors or powered-netlist observation provenance changed.")
    selected_entries = {e["relative_path"]: e for e in exported[selected["id"]]["files"]}
    expected_artifacts = {a["id"]: {**a, "export_path": selected_entries[a["relative_path"]]["export_path"]} for a in selected["checks"].get("artifacts", [])}
    require(object_hash(manifest.get("artifacts")) == object_hash(expected_artifacts), "The download-artifact summary differs from original raw evidence.")
    require(all(type(manifest.get(k)) is int and manifest[k] == 0 for k in ("model_calls", "collection_tool_starts", "collection_live_store_writes"))
            and manifest.get("manual_RTL_modifications") == [] and manifest.get("canonical_job_replaced") is False
            and all(manifest.get(k) is False for k in ("independent_LVS_replay", "SDF_dynamic_simulation", "formal_equivalence", "software_QA_fixtures_are_actual_evidence")),
            "The archive overstates its scope or collection activity.")
    return manifest, selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=ROOT / "results/npu_lvs_continuous_flow")
    parser.add_argument("--verify-only", action="store_true", required=True,
                        help="Verify saved bytes and lineage only; this helper does not execute LVS.")
    args = parser.parse_args()
    manifest, selected = inspect_evidence(args.evidence)
    print(json.dumps({"archive_validation_status": "Passed", "selected_LVS_validation_status": selected["validation_status"],
        "verification_scope": "portable_saved_archive_only_no_independent_LVS_execution", "lvs_run_id": selected["id"],
        "layout_run_id": selected["layout_run_id"], "drc_run_id": selected["drc_run_id"], "archive_manifest_sha256": sha(args.evidence / "manifest.json"),
        "model_calls": 0, "tool_starts": 0, "live_store_writes": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Preserve the actual S13 LVS history and raw outputs without executing tools.

Collection success describes the integrity of the archive. The selected LVS
result may still be Failed; that status and every earlier attempt are retained.
Software fixtures are only used by separate rejection/byte-preservation tests.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from collect_global_proof import history_descriptor
from collect_physical_proof import MAX_HISTORY_BYTES, SOURCE_HISTORIES as PHYSICAL_SOURCES, export_logs
from node_spec_evidence import sha, write_json
from replay_physical_proof import (archive_path, decode_physical_history, inspect_evidence as inspect_layout_evidence,
                                  read_json, valid_sha, verify_files)
from replay_drc_proof import decode_history as decode_drc_history, inspect_evidence as inspect_drc_evidence
from hullcirq.store import strict_loads, validate_policy_history, validate_policy_review
from hullcirq.verification import object_hash

LVS_HISTORY = "lvs_workflow.json"
SOURCE_HISTORIES = (*PHYSICAL_SOURCES, "physical_workflow.json", "drc_workflow.json")
RECORD_KIND = "actual_original_GUI_job_S13_SKY130_LVS_evidence"
SCOPE = "same_adopted_S12_S11_GDS_and_mapped_netlist_fixed_SKY130_extraction_and_Netgen_LVS"
TERMINAL = {"Completed", "Failed", "Cancelled", "Interrupted"}
FILE_BYTES = 128 * 1024 * 1024
TOTAL_BYTES = 512 * 1024 * 1024
FILE_COUNT = 16384
DIAGNOSTIC_SUFFIXES = {".log", ".rpt", ".json", ".txt", ".py", ".tcl", ".xml", ".lyrdb", ".magicrc", ".gds", ".v", ".spice", ".sp", ".ext", ".lef", ".sdc"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def normalized_history_hashes(baseline):
    values = baseline.get("original_NPU_histories")
    require(type(values) is dict, "A pre-S13 source-history baseline is required.")
    result = {}
    for relative, checksum in values.items():
        require(type(relative) is str and valid_sha(checksum), "Invalid original-history baseline entry.")
        name = PurePosixPath(relative).name
        require(relative in (name, ".work/projects/npu/" + name) and name not in result,
                "Original-history baseline keys must be canonical and unique.")
        result[name] = checksum
    require(set(result) == set(SOURCE_HISTORIES), "All eight original NPU histories, including S11 and S12, must be frozen.")
    return result


def read_sources(directory):
    return {name: (Path(directory) / name).read_bytes() for name in SOURCE_HISTORIES}


def require_source_bytes(current, original):
    require(type(current) is dict and type(original) is dict
            and set(current) == set(original) == set(SOURCE_HISTORIES)
            and all(type(raw) is bytes and raw == original[name] for name, raw in current.items()),
            "All eight original GUI/model/functional/layout/DRC histories must remain byte exact.")


def load_baseline(path, original_directory):
    raw = Path(path).read_bytes(); baseline = strict_loads(raw.decode("utf-8"))
    require(type(baseline) is dict and type(baseline.get("preexisting_files")) is dict
            and type(baseline.get("default_histories")) is dict, "A complete pre-S13 baseline is required.")
    hashes = normalized_history_hashes(baseline); original = read_sources(original_directory)
    require(all(digest(value) == hashes[name] for name, value in original.items()),
            "Original runtime copies differ from the pre-S13 baseline.")
    return baseline, raw, original


def verify_prior_payloads(baseline, root=ROOT):
    root = Path(root).resolve(); protected = {}
    for relative, expected in baseline["preexisting_files"].items():
        require(type(relative) is str and valid_sha(expected), "Invalid prior-file baseline entry.")
        if not relative.startswith("results/"):
            continue
        path = archive_path(root, relative)
        require(sha(path) == expected, "A preexisting result payload changed: " + relative)
        protected[relative] = expected
    require(protected, "The baseline must bind prior result payloads.")
    return protected


def verify_default_histories(baseline, root=ROOT):
    values = baseline["default_histories"]
    require(type(values) is dict and values, "Protect the existing default-project histories.")
    for relative, expected in values.items():
        require(type(relative) is str and relative.startswith(".work/projects/default/")
                and PurePosixPath(relative).name.endswith(".json") and valid_sha(expected), "Invalid default-project baseline entry.")
        require(sha(archive_path(root, relative)) == expected, "A default-project history changed: " + relative)
    return copy.deepcopy(values)


def terminal_history(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_HISTORY_BYTES, "LVS history is empty or oversized.")
    history = strict_loads(raw.decode("utf-8"))
    require(type(history) is dict and history.get("lvs_workflow_store_version") == "0.1"
            and type(history.get("runs")) is list and history["runs"]
            and type(history.get("reviews")) is list
            and type(history.get("source_epoch")) is int and history["source_epoch"] >= 0
            and type(history.get("source_transitions")) is list,
            "A complete terminal LVS history is required.")
    ids = set()
    for run in history["runs"]:
        require(type(run) is dict and type(run.get("id")) is str
                and re.fullmatch(r"[A-Za-z0-9_-]+", run["id"]) and run["id"] not in ids
                and run.get("stage_id") == "lvs" and run.get("execution_status") in TERMINAL
                and run.get("validation_status") in ("Not Checked", "Passed", "Failed", "Unsupported")
                and run.get("review_status") in ("Awaiting Review", "Accepted", "Changes Requested")
                and type(run.get("source_epoch_at_start")) is int and run["source_epoch_at_start"] >= 0
                and type(run.get("source_key")) is str
                and type(run.get("checks")) is dict and type(run.get("runtime_configuration")) is dict
                and run.get("record_hash") == object_hash({k: v for k, v in run.items() if k != "record_hash"}),
                "Wait for all LVS attempts to terminate and preserve each complete checksummed record.")
        ids.add(run["id"])
    transitions = history["source_transitions"]
    require(all(type(t) is dict for t in transitions)
            and [t.get("epoch") for t in transitions] == list(range(1, history["source_epoch"] + 1))
            and all(type(t.get("epoch")) is int and type(t.get("source_key")) is str for t in transitions)
            and (transitions[-1]["source_key"] if transitions else None) == history.get("source_key"),
            "LVS source epochs/transitions are inconsistent.")
    require(all(type(r) is dict and r.get("run_id") in ids for r in history["reviews"]),
            "A LVS review references an unknown attempt.")
    return history


def require_real_origin(run):
    configuration = run["runtime_configuration"]
    origin = configuration.get("origin")
    if origin is None:
        origin = configuration.get("profile", {}).get("origin")
    require(run.get("evidence_kind") == "trusted_fixed_lvs_execution"
            and run["checks"].get("software_qa_fixture") is not True
            and type(origin) is str and bool(origin.strip()),
            "Software fixtures or an unidentified runtime cannot become actual LVS evidence.")


def validate_lineage(run, layout, drc, physical_history, drc_history):
    """Pure binding to both exact adopted sources, rather than a substituted circuit."""
    require_real_origin(run)
    from hullcirq.lvs_workflow import validate_source_snapshot
    validate_source_snapshot(run)
    require(run["layout_run_id"] == layout["id"] == drc["layout_run_id"]
            and object_hash(run["layout_snapshot"]) == object_hash(layout)
            and object_hash(run["drc_snapshot"]) == object_hash(drc)
            and object_hash(drc["layout_snapshot"]) == object_hash(layout)
            and run["drc_run_id"] == drc["id"]
            and run["revision_id"] == layout["revision_id"]
            and any(object_hash(run["layout_adoption"]) == object_hash(r) for r in physical_history["reviews"])
            and any(object_hash(run["drc_adoption"]) == object_hash(r) for r in drc_history["reviews"]),
            "LVS must inspect the exact original accepted S11/S12 records and original adoptions.")
    gds = [a for a in layout["checks"]["artifacts"] if a["id"] == "gds"]
    netlists = [a for a in layout["checks"]["artifacts"] if a["id"] == "netlist"]
    definitions = [a for a in layout["checks"]["artifacts"] if a["id"] == "def"]
    inputs = run["source_inputs"]
    require(len(gds) == len(netlists) == len(definitions) == 1
            and run["input_gds_sha256"] == gds[0]["sha256"] == drc["input_gds_sha256"]
            and run["input_netlist_sha256"] == netlists[0]["sha256"]
            and all(object_hash(inputs[key]) == object_hash(source) for key, source in
                    (("gds", gds[0]), ("netlist", netlists[0]), ("def", definitions[0])))
            and inputs["powered_netlist"]["sha256"] == run["input_powered_netlist_sha256"]
            and inputs["powered_netlist"].get("origin") == "original_S11_state_pointer_observed_at_S13_start",
            "LVS inputs must preserve original S11 GDS/DEF/netlist and explicitly identify the later powered-netlist observation.")


def validate_history_selection(history):
    """Do not fall back to an earlier pass after a later failure or withdrawal."""
    selected = history["runs"][-1]
    require(selected.get("source_key") == history["source_key"]
            and selected.get("source_epoch_at_start") == history["source_epoch"], "The latest LVS attempt is stale.")
    if selected.get("review_status") == "Accepted":
        require(selected.get("execution_status") == "Completed" and selected.get("validation_status") == "Passed"
                and selected.get("acceptance_epoch") == history["source_epoch"], "Only the current required Passed LVS may be adopted.")
        reviews = [r for r in history["reviews"] if r.get("run_id") == selected["id"]]
        require(reviews and reviews[-1].get("decision") == "accepted"
                and reviews[-1].get("source_key") == selected["source_key"]
                and reviews[-1].get("acceptance_epoch") == history["source_epoch"], "The selected adoption was withdrawn or changed.")
    return selected


def validate_reviews(history, state):
    policies = validate_policy_history(state)
    for run in history["runs"]:
        require(any(t["epoch"] == run.get("source_epoch_at_start") and t["source_key"] == run.get("source_key")
                    for t in history["source_transitions"]), "An attempt lost its original source epoch.")
        reviews = [r for r in history["reviews"] if r["run_id"] == run["id"]]
        expected = "Awaiting Review" if not reviews else "Accepted" if reviews[-1]["decision"] == "accepted" else "Changes Requested"
        require(run.get("review_status") == expected, "A saved LVS status contradicts its last decision.")
        for review in reviews:
            require(review.get("decision") in ("accepted", "changes_requested", "return_to_stage")
                    and review.get("source_key") == run["source_key"] and type(review.get("note")) is str,
                    "A review lost its original LVS source or decision.")
            validate_policy_review(review, policies)
            if review["decision"] == "accepted":
                require(run["execution_status"] == "Completed" and run["validation_status"] == "Passed"
                        and type(review.get("acceptance_epoch")) is int
                        and review["acceptance_epoch"] == run["source_epoch_at_start"] == run.get("acceptance_epoch")
                        and review.get("reviewed_revision_id") == run["revision_id"],
                        "Acceptance must bind the current Passed result, original epoch and GUI revision.")


def safe_relative(value):
    require(type(value) is str, "A retained file path must be a string.")
    path = PurePosixPath(value)
    require(path.parts and not path.is_absolute() and path.as_posix() == value
            and not any(p in (".", "..") for p in path.parts) and "\\" not in value and ":" not in value
            and not any(ord(c) < 32 for c in value), "Retained files need safe canonical relative paths.")
    return path


def declared_files(result):
    """Validate every raw file descriptor, including zero-byte diagnostic logs."""
    require(type(result) is dict and type(result.get("artifacts" , [])) is list
            and type(result.get("retained_files", [])) is list, "Invalid raw LVS file lists.")
    from hullcirq.lvs_workflow import FILE_IDS
    combined = {}; ids = set(); paths = set()
    for artifact in result.get("artifacts", []):
        require(type(artifact) is dict and artifact.get("id") in FILE_IDS and artifact["id"] not in ids
                and artifact.get("relative_path") not in paths and type(artifact.get("content_type")) is str
                and re.fullmatch(r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+(?:; charset=utf-8)?", artifact["content_type"])
                and type(artifact.get("bytes")) is int and artifact["bytes"] >= 0
                and (artifact["bytes"] > 0 or artifact["id"] == "extraction-feedback"),
                "Artifacts require unique fixed IDs/paths and media types; only extraction feedback may be empty.")
        ids.add(artifact["id"]); paths.add(artifact["relative_path"])
    for entry in (*result.get("artifacts", []), *result.get("retained_files", [])):
        require(type(entry) is dict and valid_sha(entry.get("sha256"))
                and type(entry.get("bytes")) is int and 0 <= entry["bytes"] <= FILE_BYTES, "Invalid raw LVS file descriptor.")
        safe_relative(entry.get("relative_path"))
        previous = combined.get(entry["relative_path"])
        require(previous is None or all(previous[k] == entry[k] for k in ("sha256", "bytes")),
                "Artifact and retained descriptors disagree at the same path.")
        combined[entry["relative_path"]] = {k: entry[k] for k in ("relative_path", "sha256", "bytes")}
    return combined


def attempt_inventory(run):
    """Bounded diagnostic retention includes failed/cancelled original attempts."""
    result = run["checks"]; declared = declared_files(result)
    value = result.get("artifacts_directory")
    commands = result.get("commands", [])
    require(type(commands) is list and all(type(c) is dict for c in commands), "Keep original command records.")
    if value is None:
        require(not declared and not commands and result.get("executed") is not True,
                "An executed attempt cannot lose its original output directory.")
        return {"directory": None, "files": [], "omitted_files": [], "unavailable_reason": "No output directory was created."}
    require(type(value) is str and Path(value).is_absolute(), "Retain the original absolute LVS output directory.")
    folder = Path(value).resolve(); parent = Path(run["runtime_configuration"]["working_directory"]).resolve()
    require(folder.is_dir() and folder.parent == parent and folder.name.startswith("hullcirq-lvs-"),
            "A LVS diagnostic directory is missing or outside its fixed runtime root.")
    files = []; omitted = []; total = 0; seen = set()
    for directory, subdirs, names in os.walk(folder, followlinks=False):
        subdirs.sort()
        for name in subdirs:
            p = Path(directory) / name
            require(not p.is_symlink() and p.resolve() == p.absolute() and p.resolve().is_relative_to(folder),
                    "Diagnostic directory aliases must not escape the run.")
        for name in sorted(names):
            path = Path(directory) / name; relative = path.relative_to(folder).as_posix()
            require(not path.is_symlink() and path.resolve().is_relative_to(folder) and path.is_file(),
                    "A raw diagnostic escaped the original run.")
            size = path.stat().st_size
            if relative not in declared and path.suffix.lower() not in DIAGNOSTIC_SUFFIXES and name != "cancel.request":
                omitted.append({"relative_path": relative, "bytes": size, "reason": "Excluded intermediate format; no proof inferred."}); continue
            require(size <= FILE_BYTES and total + size <= TOTAL_BYTES and len(files) < FILE_COUNT,
                    "Required LVS diagnostics exceed retention bounds; evidence must not be silently truncated.")
            total += size; checksum = sha(path)
            require(relative not in declared or declared[relative] == {"relative_path": relative, "sha256": checksum, "bytes": size},
                    "A declared raw LVS output changed: " + relative)
            files.append({"relative_path": relative, "source_path": str(path), "sha256": checksum, "bytes": size,
                          "original_recorded_raw_sha256": declared.get(relative, {}).get("sha256")})
            seen.add(relative)
    require(set(declared) <= seen, "A declared LVS artifact or raw diagnostic is missing.")
    return {"directory": str(folder), "files": files, "omitted_files": omitted, "unavailable_reason": None}


def copy_attempt(run, reviews, output, shared=None):
    inventory = attempt_inventory(run); destination = Path(output) / "attempts" / run["id"]
    destination.mkdir(parents=True, exist_ok=True)
    write_json(destination / "run_record.json", run)
    write_json(destination / "reviews.json", [r for r in reviews if r.get("run_id") == run["id"]])
    result = run["checks"]
    export_logs({"commands": result.get("commands", []), "stdout": result.get("stdout", ""), "stderr": result.get("stderr", "")}, destination)
    shared = shared if shared is not None else {}
    for entry in inventory["files"]:
        payload = Path(entry["source_path"]).read_bytes()
        require(len(payload) == entry["bytes"] and digest(payload) == entry["sha256"], "LVS raw bytes changed during collection.")
        identity = (entry["sha256"], entry["bytes"])
        if identity in shared:
            path = Path(output) / shared[identity]
            require(path.read_bytes() == payload, "Shared raw LVS files disagree.")
            entry.update(export_path=shared[identity], storage="shared_exact_raw_file")
        else:
            path = destination / "working_files" / Path(*safe_relative(entry["relative_path"]).parts)
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(payload)
            shared[identity] = path.relative_to(output).as_posix()
            entry.update(export_path=shared[identity], storage="original_raw_file_copy")
    return {"original_run_id": run["id"], "record_object_sha256": object_hash(run), "original_record_hash": run["record_hash"],
            "execution_status": run["execution_status"], "validation_status": run["validation_status"], "review_status": run["review_status"],
            "record_encoding": "JSON object export; exact complete history bytes are separately losslessly compressed.",
            "raw_hash_scope": "Collection-time raw hashes; original recorded hashes are identified separately.",
            "bounds": {"file_bytes": FILE_BYTES, "total_bytes": TOTAL_BYTES, "file_count": FILE_COUNT}, **inventory}


def verify_source_archives(layout_evidence, drc_evidence, baseline, original):
    layout_manifest, layout = inspect_layout_evidence(layout_evidence)
    drc_manifest, drc = inspect_drc_evidence(drc_evidence)
    for folder in (layout_evidence, drc_evidence):
        path = Path(folder) / "manifest.json"
        relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
        require(sha(path) == baseline["preexisting_files"].get(relative), "An original S11/S12 proof manifest changed.")
    require(drc["layout_run_id"] == layout["id"] and object_hash(drc["layout_snapshot"]) == object_hash(layout),
            "The original S12 archive identifies a different S11 result.")
    physical_raw = decode_physical_history(layout_evidence, layout_manifest["physical_workflow_history"])
    drc_raw = decode_drc_history(drc_evidence, drc_manifest["drc_workflow_history"], "drc_workflow.json.gz")
    require(physical_raw == original["physical_workflow.json"] and drc_raw == original["drc_workflow.json"],
            "Original S11/S12 histories differ from the frozen source archives.")
    for name in (*PHYSICAL_SOURCES, "physical_workflow.json"):
        require(drc_manifest["unchanged_original_source_histories"][name] == {"sha256": digest(original[name]), "bytes": len(original[name])},
                "An original source differs from the actual S12 proof: " + name)
    return layout_manifest, drc_manifest, layout, drc, strict_loads(physical_raw.decode("utf-8")), strict_loads(drc_raw.decode("utf-8"))


def collect(data_directory, baseline_path, original_directory, output, *, layout_evidence=None, drc_evidence=None):
    output = Path(output); data_directory = Path(data_directory)
    require(not output.exists() or output.is_dir() and not any(output.iterdir()), "Use a new empty result directory.")
    require(output.resolve().is_relative_to((ROOT / "results").resolve()), "Actual evidence belongs in a new HuLLCirq results directory.")
    require(not output.resolve().is_relative_to(data_directory.resolve()), "Archive output must be separate from the live store.")
    baseline, baseline_raw, original = load_baseline(baseline_path, original_directory)
    prior = verify_prior_payloads(baseline); default = verify_default_histories(baseline)
    require_source_bytes(read_sources(data_directory), original)
    layout_evidence = Path(layout_evidence or ROOT / "results/npu_layout_continuous_flow")
    drc_evidence = Path(drc_evidence or ROOT / "results/npu_drc_continuous_flow")
    _, _, layout, drc, physical, drc_history = verify_source_archives(layout_evidence, drc_evidence, baseline, original)
    raw = (data_directory / LVS_HISTORY).read_bytes(); history = terminal_history(raw)
    selected = validate_history_selection(history)
    validate_reviews(history, strict_loads(original["state.json"].decode("utf-8")))
    from hullcirq.lvs_tools import validate_lvs_result
    for run in history["runs"]:
        validate_lineage(run, layout, drc, physical, drc_history)
        if run["checks"].get("checks", {}).get("lvs", {}).get("completed") is True:
            validate_lvs_result(run["checks"], run["drc_snapshot"], run["layout_snapshot"], run["runtime_configuration"])
    output.mkdir(parents=True, exist_ok=True)
    archive = output / (LVS_HISTORY + ".gz"); archive.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    state_archive = output / "original_state.json.gz"
    state_archive.write_bytes(gzip.compress(original["state.json"], compresslevel=9, mtime=0))
    (output / "source_baseline.json").write_bytes(baseline_raw)
    for name, value in (("lvs_record.json", selected), ("lvs_checks.json", selected["checks"]), ("reviews.json", history["reviews"]),
                        ("layout_record.json", layout), ("drc_record.json", drc), ("source_identity.json", selected["source_identity"]),
                        ("source_inputs.json", selected["source_inputs"]),
                        ("lvs_runtime_configuration.json", selected["runtime_configuration"])):
        write_json(output / name, value)
    shared = {}; attempts = [copy_attempt(run, history["reviews"], output, shared) for run in history["runs"]]
    selected_files = next(a["files"] for a in attempts if a["original_run_id"] == selected["id"])
    by_relative = {e["relative_path"]: e for e in selected_files}
    artifacts = {a["id"]: {**a, "export_path": by_relative[a["relative_path"]]["export_path"]} for a in selected["checks"].get("artifacts", [])}
    files = {p.relative_to(output).as_posix(): {"sha256": sha(p), "bytes": p.stat().st_size} for p in sorted(output.rglob("*")) if p.is_file()}
    result = {"record_kind": RECORD_KIND, "scope": SCOPE, "collection_validation_status": "Passed",
        "selected_validation_status": selected["validation_status"], "selected_execution_status": selected["execution_status"],
        "selected_review_status": selected["review_status"], "lvs_run_id": selected["id"], "layout_run_id": layout["id"], "drc_run_id": drc["id"],
        "source_revision_id": layout["revision_id"], "source_layout_manifest_sha256": sha(layout_evidence / "manifest.json"),
        "source_drc_manifest_sha256": sha(drc_evidence / "manifest.json"), "drc_record_sha256": selected["drc_record_sha256"],
        "layout_record_sha256": selected["layout_record_sha256"], "input_gds_sha256": selected["input_gds_sha256"],
        "input_netlist_sha256": selected["input_netlist_sha256"],
        "input_powered_netlist_sha256": selected["input_powered_netlist_sha256"],
        "source_inputs": copy.deepcopy(selected["source_inputs"]),
        "configuration_sha256": selected["configuration_sha256"], "source_baseline_sha256": digest(baseline_raw),
        "unchanged_original_source_histories": {name: {"sha256": digest(value), "bytes": len(value)} for name, value in original.items()},
        "unchanged_preexisting_result_files": prior, "unchanged_default_histories": default,
        "lvs_workflow_history": history_descriptor(archive, raw),
        "original_state_history": history_descriptor(state_archive, original["state.json"]),
        "attempt_count": len(attempts), "attempts": attempts,
        "artifacts": artifacts, "model_calls": 0, "manual_RTL_modifications": [], "canonical_job_replaced": False,
        "collection_tool_starts": 0, "collection_live_store_writes": 0, "software_QA_fixtures_are_actual_evidence": False,
        "independent_LVS_replay": False, "SDF_dynamic_simulation": False, "formal_equivalence": False, "files": files}
    verify_prior_payloads(baseline); verify_default_histories(baseline); require_source_bytes(read_sources(data_directory), original)
    require((data_directory / LVS_HISTORY).read_bytes() == raw and Path(baseline_path).read_bytes() == baseline_raw,
            "Live LVS history or baseline changed during collection.")
    require(sha(layout_evidence / "manifest.json") == result["source_layout_manifest_sha256"], "Prior S11 proof changed during collection.")
    require(sha(drc_evidence / "manifest.json") == result["source_drc_manifest_sha256"], "Prior S12 proof changed during collection.")
    for attempt in attempts:
        for entry in attempt["files"]:
            path = Path(entry["source_path"])
            require(path.stat().st_size == entry["bytes"] and sha(path) == entry["sha256"], "Original LVS files changed before collection completed.")
    verify_files(output, files); write_json(output / "manifest.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".work/projects/npu")
    parser.add_argument("--baseline", type=Path, default=ROOT / ".work/m2i/baseline.json")
    parser.add_argument("--original-runtime", type=Path, default=ROOT / ".work/m2i/original_runtime/npu")
    parser.add_argument("--layout-evidence", type=Path, default=ROOT / "results/npu_layout_continuous_flow")
    parser.add_argument("--drc-evidence", type=Path, default=ROOT / "results/npu_drc_continuous_flow")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = collect(args.data_dir, args.baseline, args.original_runtime, args.output, layout_evidence=args.layout_evidence, drc_evidence=args.drc_evidence)
    print(json.dumps({"collection_validation_status": "Passed", "selected_validation_status": manifest["selected_validation_status"],
                      "lvs_run_id": manifest["lvs_run_id"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

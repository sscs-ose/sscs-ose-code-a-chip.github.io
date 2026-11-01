"""Verify a portable S11 evidence tree, or replay it in fresh ignored space.

Verification reads archived bytes and sibling prior proofs only. Original
absolute tool paths are provenance, never filesystem dependencies. Actual
replay uses the pinned adapter, without models, live writes or new adoption.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from collect_physical_proof import (MAX_HISTORY_BYTES, PHYSICAL_HISTORY, RECORD_KIND, SOURCE_HISTORIES, SCOPE,
    copy_artifacts, copy_legacy_execution_sources, copy_retained_files, decode_physical_history, digest, export_logs,
    require, require_real_origin, sha, terminal_history, valid_sha, validate_lineage, validate_revalidation_binding)
from hullcirq.global_generation import validate_global_plan
from hullcirq.global_workflow import source_bundle
from hullcirq.physical_tools import (IMAGE_SHA, PDK_REVISION, RELEASE, SDC_SHA, WORKER_V1_SHA, WORKER_V2_SHA,
    _check_artifact, configuration_projection, load_tool_json, metric_checks)
from hullcirq.store import strict_loads
from hullcirq.verification import content_hash, object_hash
from node_spec_evidence import write_json

PRIOR_FOLDERS = {"S04_S07": "npu_all_nodes_continuous_flow", "S08": "npu_global_continuous_flow",
                 "S09_S10": "npu_global_netlist_continuous_flow"}


def read_json(path):
    return strict_loads(Path(path).read_bytes().decode("utf-8"))


def archive_path(directory, relative):
    require(type(relative) is str, "An archive path must be a string.")
    value = PurePosixPath(relative)
    require(value.parts and not value.is_absolute() and value.as_posix() == relative
            and not any(p in (".", "..") for p in value.parts) and "\\" not in relative and ":" not in relative
            and not any(ord(c) < 32 for c in relative), "Unsafe or noncanonical archive path.")
    root = Path(directory).resolve(); path = (root / Path(*value.parts)).resolve()
    require(path.is_relative_to(root) and path.is_file() and path.relative_to(root).as_posix() == relative,
            "Missing or escaped archive file: " + relative)
    return path


def verify_files(directory, files):
    require(type(files) is dict and 0 < len(files) <= 65536, "A bounded complete archive file manifest is required.")
    for relative, entry in files.items():
        require(type(entry) is dict and set(entry) == {"sha256", "bytes"} and valid_sha(entry["sha256"])
                and type(entry["bytes"]) is int and entry["bytes"] >= 0, "Invalid typed raw archive file descriptor.")
        path = archive_path(directory, relative)
        require(path.stat().st_size == entry["bytes"] and sha(path) == entry["sha256"], "Archive raw bytes changed: " + relative)


def decode_prior(directory, prefix, descriptor):
    require(type(descriptor) is dict and type(descriptor.get("archive")) is str
            and descriptor.get("compression") == "gzip" and type(descriptor.get("decompressed_bytes")) is int
            and 0 < descriptor["decompressed_bytes"] <= MAX_HISTORY_BYTES, "Invalid bounded prior history descriptor.")
    path = archive_path(directory, prefix + descriptor["archive"])
    require(type(descriptor.get("archive_bytes")) is int and path.stat().st_size == descriptor["archive_bytes"]
            and sha(path) == descriptor.get("archive_sha256"), "Prior compressed history changed.")
    with gzip.open(path, "rb") as stream: raw = stream.read(descriptor["decompressed_bytes"] + 1)
    require(len(raw) == descriptor["decompressed_bytes"] and digest(raw) == descriptor.get("decompressed_sha256"),
            "Prior history expansion/hash differs.")
    return raw, strict_loads(raw.decode("utf-8"))


def prior_sources(directory, manifest, run, baseline):
    """Use submitted sibling proofs, never their original absolute tool paths."""
    archives = {}
    for label, name in PRIOR_FOLDERS.items():
        folder = Path(directory).parent / name; path = folder / "manifest.json"
        require(sha(path) == manifest["prior_actual_archives"][label]["manifest_sha256"], "Prior immutable archive manifest changed: " + label)
        value = read_json(path); verify_files(folder, value["files"])
        for relative in ("manifest.json", *value["files"]):
            require(sha(folder / relative) == baseline["preexisting_files"].get("results/" + name + "/" + relative),
                    "A prior archive payload differs from the pre-S11 immutable baseline.")
        archives[label] = (folder, value)
    nodes_dir, nodes = archives["S04_S07"]; global_dir, global_proof = archives["S08"]; net_dir, net = archives["S09_S10"]
    require(global_proof["node_evidence_manifest_sha256"] == sha(nodes_dir / "manifest.json")
            and net["source_global_manifest_sha256"] == sha(global_dir / "manifest.json")
            and net["source_node_manifest_sha256"] == sha(nodes_dir / "manifest.json"), "Prior archive chain changed.")
    job = read_json(global_dir / "global_job_record.json")
    synthesis = read_json(net_dir / "synthesis_record.json"); simulation = read_json(net_dir / "netlist_record.json")
    raw, history = decode_prior(global_dir, "", global_proof["global_history"])
    require(any(object_hash(j) == object_hash(job) for j in history["jobs"]), "S08 export differs from its original history.")
    raw_global = raw
    raw, workflow = decode_prior(net_dir, "", net["global_workflow_history"])
    require(all(any(object_hash(r) == object_hash(record) for r in workflow["runs"]) for record in (synthesis, simulation)),
            "S09/S10 exports differ from their original history.")
    source_raw = {"global_generation.json": raw_global, "global_workflow.json": raw}
    for name, descriptor in nodes["compressed_histories"]["current"].items():
        source_raw[name] = decode_prior(nodes_dir, "histories/", descriptor)[0]
    source_raw["generation.json"] = decode_prior(global_dir / "runtime", "", global_proof["runtime_generation_history"])[0]
    require(set(source_raw) == set(SOURCE_HISTORIES) and all(digest(raw) == baseline["original_NPU_histories"][name]
            and object_hash(manifest["unchanged_original_source_histories"][name]) == object_hash({"sha256": digest(raw), "bytes": len(raw)})
            for name, raw in source_raw.items()), "The six original source histories differ from the saved baseline.")
    validate_lineage(run, synthesis, simulation, job, baseline)
    for node in run["source_manifest"]["nodes"]:
        old = nodes["nodes"][node["node_id"]]
        require(all(node[key] == old[key] for key in ("candidate_id", "synthesis_run_id", "netlist_run_id", "spec_id", "rtl_sha256", "specification_sha256")),
                "A physical node source differs from its original adopted six-node proof.")
    identity = run["source_identity"]
    require(identity["synthesis_adoption"] == simulation["synthesis_adoption"]
            and any(object_hash(r) == object_hash(identity["synthesis_adoption"]) for r in workflow["reviews"])
            and any(object_hash(r) == object_hash(identity["netlist_adoption"]) for r in workflow["reviews"]), "Original S09/S10 adoption chain changed.")


def old_wsl_path(value):
    """Lexical conversion only: does not resolve/open old machine paths."""
    require(type(value) is str and not any(ord(c) < 32 for c in value), "Invalid archival absolute path.")
    if value.startswith("/mnt/"): return PurePosixPath(value).as_posix()
    path = PureWindowsPath(value)
    require(path.is_absolute() and len(path.drive) == 2 and path.drive[1] == ":", "Expected a retained Windows drive path.")
    return "/mnt/" + path.drive[0].lower() + "/" + "/".join(path.parts[1:])


def expected_config(run):
    config = run["runtime_configuration"]
    require(config.get("kind") == "wsl" and config.get("release") == RELEASE and config.get("appimage_sha256") == IMAGE_SHA
            and config.get("pdk_revision") == PDK_REVISION and config.get("base_sdc_sha256") == SDC_SHA
            and config.get("executable") == old_wsl_path(config["appimage_path"])
            and object_hash(config["profile"]) == object_hash(read_json(ROOT / "configs/physical_profile_sky130.json")),
            "Archived physical runtime/profile is not the pinned supported configuration.")
    bundle = source_bundle(run["global_rtl"], run["source_manifest"])
    value = copy.deepcopy(config["profile"]["config"])
    value.update(DESIGN_NAME=run["settings"]["top_module"], VERILOG_FILES=["dir::" + x["file"] for x in bundle],
        CLOCK_PORT=run["settings"]["clock_name"], CLOCK_PERIOD=run["settings"]["clock_period_ns"],
        PNR_SDC_FILE="dir::physical.sdc", SIGNOFF_SDC_FILE="dir::physical.sdc")
    return value, bundle


def verify_portable_result(directory, manifest, run):
    """Strict raw-byte/result validation through archive-relative file paths."""
    result = run["checks"]; config, bundle = expected_config(run); paths = {}; by_relative = {}
    require(result.get("origin") == "trusted_fixed_tool_adapter" and result.get("scope") == "SKY130_routed_layout_not_DRC_LVS_SDF"
            and object_hash(result.get("source_bundle")) == object_hash(bundle)
            and all(result.get(key) == run[key] for key in ("global_rtl_sha256", "source_manifest_sha256", "settings_sha256", "runtime_configuration_sha256"))
            and result.get("validation_status") == "Passed" and result.get("executed") is True and type(result.get("exit_code")) is int and result["exit_code"] == 0,
            "Archived physical execution/source proof is incomplete.")
    for entry in [*manifest["artifacts"].values(), *manifest["retained_files"]]:
        relative = entry["relative_path"]; exported = entry["export_path"]
        require(exported == "artifacts/" + relative and manifest["files"].get(exported) == {"sha256": entry["sha256"], "bytes": entry["bytes"]},
                "Collected physical file is not bound to its exact raw artifact descriptor.")
        by_relative[relative] = archive_path(directory, exported)
    saved_retained = {entry["relative_path"]: entry for entry in manifest["retained_files"]}
    require(len(saved_retained) == len(manifest["retained_files"]), "Duplicate collected retained-file path.")
    for entry in result["retained_files"]:
        saved = saved_retained.get(entry["relative_path"])
        require(type(saved) is dict and object_hash(entry) == object_hash({k: saved[k] for k in entry}), "Original retained raw-file manifest changed.")
    for entry in result["artifacts"]:
        saved = manifest["artifacts"].get(entry["id"])
        require(type(saved) is dict and object_hash(entry) == object_hash({k: saved[k] for k in entry}), "Original artifact manifest changed.")
        paths[entry["id"]] = by_relative[entry["relative_path"]]
    require(set(paths) == {"config", "sdc", "metrics", "def", "gds", "png", "netlist", "final-state", "tool-versions", "input-manifest", "rtl-top",
            *("rtl-" + n["node_id"] for n in run["source_manifest"]["nodes"])}, "Physical source/output artifact set is incomplete.")
    require(object_hash(read_json(paths["config"])) == object_hash(config) and sha(paths["sdc"]) == SDC_SHA
            and sha(by_relative["pdk-input-manifest.json"]) == run["runtime_configuration"]["pdk_manifest_sha256"], "Archived config/SDC/PDK inputs changed.")
    require(paths["rtl-top"].read_bytes() == run["global_rtl"].encode("utf-8"), "Archived top RTL bytes changed.")
    for node in run["source_manifest"]["nodes"]:
        require(paths["rtl-" + node["node_id"]].read_bytes() == node["rtl"].encode("utf-8"), "Archived node RTL bytes changed.")
    inputs = {"settings": run["settings"], "runtime_configuration": run["runtime_configuration"], "source_bundle": bundle,
        "source_manifest_sha256": run["source_manifest_sha256"], "global_rtl_sha256": run["global_rtl_sha256"]}
    require(object_hash(read_json(paths["input-manifest"])) == object_hash(inputs), "Archived source/input manifest changed.")
    metrics = load_tool_json(paths["metrics"]); state = load_tool_json(paths["final-state"])
    checks = metric_checks(metrics)
    require(object_hash(metrics) == object_hash(result["metrics"]) == object_hash(state["metrics"])
            and object_hash(checks) == object_hash(result["checks"]) and all(v["validation_status"] == "Passed" for v in checks.values()),
            "Archived finite routing/timing checks or raw metrics changed.")
    require("klayout-render" in PurePosixPath(next(e["relative_path"] for e in result["artifacts"] if e["id"] == "final-state")).parent.name.lower(),
            "The archived result did not reach KLayout.Render.")
    old_root = PurePosixPath(old_wsl_path(result["artifacts_directory"]))
    for identifier, key in (("def", "def"), ("gds", "gds"), ("png", "render"), ("netlist", "nl")):
        require(PurePosixPath(state[key]).relative_to(old_root).as_posix() == manifest["artifacts"][identifier]["relative_path"],
                "Archived terminal state points to another physical output.")
        _check_artifact(paths[identifier], identifier, run["settings"])
    versions = read_json(paths["tool-versions"])
    require(versions.get("librelane") == RELEASE and set(versions.get("tools", {})) == {"yosys", "openroad", "klayout", "magic", "ciel"},
            "Archived bundled tool versions are incomplete.")
    commands = result["commands"]; recipe = result.get("adapter_recipe", "v1")
    require(recipe in ("v1", "v2") and type(commands) is list and len(commands) == 2, "Require both original fixed commands.")
    old_folder = old_root.as_posix(); runtime = run["runtime_configuration"]
    legacy = {PureWindowsPath(e["source_path"]).name: e for e in manifest.get("legacy_execution_source_copies", [])}
    if recipe == "v1":
        for name, checksum in (("physical_worker.py", WORKER_V1_SHA), ("capture_physical_versions.py", "d1aa8290668ec384c2c556a5eec60d491f74696c83aa9cacdc3319dc93173ce1")):
            require(name in legacy and legacy[name]["sha256"] == checksum and legacy[name].get("pre_execution_snapshot") is False
                    and sha(archive_path(directory, legacy[name]["export_path"])) == checksum,
                    "Original legacy execution-source copy is missing or changed.")
    for index, record in enumerate(commands):
        operation = ("version", "layout")[index]; command = record["command"]
        require(type(command) is list and command[1:7] == ["-d", runtime["distribution"], "--cd", old_folder, "--exec", runtime["executable"]]
                and PureWindowsPath(command[0]).name.lower() == "wsl.exe" and record.get("executed") is True
                and record.get("status") == "Completed" and type(record.get("exit_code")) is int and record["exit_code"] == 0,
                "Original physical command/exit changed.")
        if index == 1:
            require(command[7:] == ["librelane", "--flow", "Classic", "--pdk", "sky130A", "--scl", "sky130_fd_sc_hd", "--pdk-root",
                old_wsl_path(runtime["pdk_root"]), "--jobs", "2", "--run-tag", "physical", "--to", "KLayout.Render", "--hide-progress-bar", old_folder + "/config.json"],
                "Original routed-layout command changed.")
        else:
            capture = old_folder + "/capture_physical_versions.py" if recipe == "v2" else old_wsl_path(legacy["capture_physical_versions.py"]["source_path"])
            require(len(command[7:]) == 3 and command[7] == "python3" and command[8] == capture
                    and command[9] == old_folder + "/tool-versions.json", "Original version command changed.")
        request_path = by_relative[operation + "/request.json"]; request = read_json(request_path)
        expected = {"version": "hullcirq-physical-worker-" + recipe, "argv": command[6:], "timeout_seconds": 120 if index == 0 else 7200}
        worker_hash = WORKER_V1_SHA if recipe == "v1" else WORKER_V2_SHA
        if recipe == "v2":
            expected.update(cwd=old_folder, worker_sha256=worker_hash)
            require(sha(by_relative[operation + "/worker.py"]) == worker_hash, "Archived frozen worker changed.")
        worker = old_folder + "/" + operation + "/worker.py" if recipe == "v2" else old_wsl_path(legacy["physical_worker.py"]["source_path"])
        supervisor = [*command[:6], "/usr/bin/python3", worker, old_folder + "/" + operation + "/request.json"]
        if recipe == "v2": supervisor += ["--request-sha256", sha(request_path), "--worker-sha256", worker_hash]
        require(object_hash(request) == object_hash(expected) and record.get("request_sha256") == sha(request_path)
                and record.get("worker_sha256") == worker_hash and record.get("supervisor_command") == supervisor,
                "Archived worker source/request/supervisor command changed.")
        exit_record = read_json(by_relative[operation + "/process-result.json"])
        require(all(k in record and object_hash(record[k]) == object_hash(v) for k, v in exit_record.items()), "Archived raw worker exit changed.")
        for field in ("stdout", "stderr"):
            require(record[field] == by_relative[operation + "/" + field + ".log"].read_text(encoding="utf-8", errors="replace"), "Archived raw worker log changed.")
    require(all(result[field] == "".join(c[field] for c in commands) for field in ("stdout", "stderr")), "Original combined tool log changed.")


def inspect_evidence(directory):
    directory = Path(directory); manifest = read_json(directory / "manifest.json")
    require(manifest.get("record_kind") == RECORD_KIND and manifest.get("scope") == SCOPE and manifest.get("validation_status") == "Passed",
            "Use the actual preserved S11 routed-layout proof.")
    verify_files(directory, manifest["files"])
    raw = decode_physical_history(directory, manifest["physical_workflow_history"]); history = terminal_history(raw)
    run = read_json(directory / "layout_record.json")
    require(object_hash(history["runs"][-1]) == object_hash(run) and run["id"] == manifest["layout_run_id"], "Selected layout export is not the latest original record.")
    for record in history["runs"]:
        require_real_origin(record)
        require(record.get("record_hash") == object_hash({k: v for k, v in record.items() if k != "record_hash"}), "Original physical record checksum changed.")
    validate_revalidation_binding(run, history["runs"])
    require(all(manifest.get(key) == run[field] for key, field in (("source_revision_id", "revision_id"), ("source_global_job_id", "global_job_id"),
            ("synthesis_run_id", "synthesis_run_id"), ("netlist_run_id", "netlist_run_id"), ("global_rtl_sha256", "global_rtl_sha256"),
            ("source_manifest_sha256", "source_manifest_sha256"), ("verification_plan_sha256", "verification_plan_sha256"),
            ("original_GUI_settings_sha256", "settings_sha256"), ("physical_runtime_configuration_sha256", "runtime_configuration_sha256")))
            and manifest.get("selected_execution_reused") is (run["evidence_kind"] == "trusted_saved_tool_revalidation")
            and (not manifest["selected_execution_reused"] or type(manifest.get("selected_new_tool_starts")) is int and manifest["selected_new_tool_starts"] == 0),
            "Archive summary changed its actual lineage or saved-output execution provenance.")
    effective = read_json(directory / "layout_effective_record.json")
    require(all(effective.get(k) == v for k, v in (("id", run["id"]), ("execution_status", "Completed"), ("validation_status", "Passed"),
            ("review_status", "Accepted"), ("freshness", "Current"))) and run["review_status"] == "Accepted"
            and any(r.get("run_id") == run["id"] and r.get("decision") == "accepted" for r in history["reviews"]), "Original layout adoption is incomplete.")
    baseline = read_json(directory / "source_baseline.json")
    require(sha(directory / "source_baseline.json") == manifest["source_baseline_sha256"], "Original source baseline changed.")
    prior_sources(directory, manifest, run, baseline)
    for filename, value in (("source_manifest.json", run["source_manifest"]), ("verification_plan.json", run["verification_plan"]),
            ("original_GUI_settings.json", run["settings"]), ("physical_runtime_configuration.json", run["runtime_configuration"]),
            ("layout_checks.json", run["checks"]), ("reviews.json", history["reviews"]), ("source_identity.json", run["source_identity"]),
            ("artifact_manifest.json", run["checks"]["artifacts"]), ("retained_files.json", run["checks"]["retained_files"])):
        require(object_hash(read_json(directory / filename)) == object_hash(value), "Saved exported JSON differs: " + filename)
    validate_global_plan(run["source_manifest"]["design"], run["verification_plan"])
    verify_portable_result(directory, manifest, run)
    require(type(manifest.get("model_calls")) is int and manifest["model_calls"] == 0 and manifest["manual_RTL_modifications"] == []
            and all(manifest.get(k) is False for k in ("signoff_DRC", "LVS", "formal_equivalence", "SDF_dynamic_simulation", "software_QA_fixtures_are_actual_evidence")),
            "Archive overstates the physical validation scope.")
    return manifest, run


def replay(evidence, physical_config, output):
    evidence = Path(evidence); output = Path(output).resolve()
    require(output.is_relative_to((ROOT / ".work").resolve()) and (not output.exists() or output.is_dir() and not any(output.iterdir())),
            "Physical replay requires a new empty ignored .work output directory.")
    manifest, original = inspect_evidence(evidence); archive_sha = sha(evidence / "manifest.json")
    configuration_raw = Path(physical_config).read_bytes(); configuration = strict_loads(configuration_raw.decode("utf-8-sig"))
    runtime = copy.deepcopy(configuration); runtime["working_directory"] = str(output / "physical-work")
    configuration_projection(original["settings"], runtime)
    output.mkdir(parents=True, exist_ok=True); (output / "provided_runtime_configuration.json").write_bytes(configuration_raw)
    write_json(output / "effective_runtime_configuration.json", runtime)
    # The only actual tool invocation in this helper occurs after admission.
    from hullcirq.physical_tools import run_layout, validate_layout_result
    result = run_layout(original["global_rtl"], original["source_manifest"], original["settings"], runtime)
    write_json(output / "actual_layout_checks.json", result)
    passed = result.get("validation_status") == "Passed" and result.get("executed") is True and type(result.get("exit_code")) is int and result["exit_code"] == 0
    if passed:
        validate_layout_result(result, original["global_rtl"], original["source_manifest"], original["settings"], runtime)
        copy_artifacts(result, output)
    if result.get("retained_files"): copy_retained_files(result, output)
    export_logs(result, output)
    report = {"record_kind": "independent_saved_source_physical_replay_not_live_adoption", "validation_status": "Passed" if passed else "Failed",
        "source_evidence_manifest_sha256": archive_sha, "source_layout_run_id": original["id"], "source_global_job_id": original["global_job_id"],
        "source_revision_id": original["revision_id"], "global_rtl_sha256": original["global_rtl_sha256"],
        "source_manifest_sha256": original["source_manifest_sha256"], "original_GUI_settings_sha256": original["settings_sha256"],
        "verification_plan_sha256": original["verification_plan_sha256"], "new_runtime_configuration_sha256": object_hash(runtime),
        "source_bundle": source_bundle(original["global_rtl"], original["source_manifest"]), "model_calls": 0, "live_store_writes": 0,
        "new_live_adoption": False, "physical_output_byte_identity_required": False, "signoff_DRC": False, "LVS": False,
        "formal_equivalence": False, "SDF_dynamic_simulation": False, "metrics": result.get("metrics", {})}
    require(sha(evidence / "manifest.json") == archive_sha, "Original evidence changed during independent replay.")
    verify_files(evidence, manifest["files"])
    write_json(output / "report.json", report)
    write_json(output / "manifest.json", {"record_kind": report["record_kind"], "files": {p.relative_to(output).as_posix():
        {"sha256": sha(p), "bytes": p.stat().st_size} for p in sorted(output.rglob("*"))
        if p.is_file() and not p.is_relative_to(output / "physical-work")}})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=ROOT / "results/npu_layout_continuous_flow")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--physical-config", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.verify_only:
        manifest, run = inspect_evidence(args.evidence)
        print(json.dumps({"validation_status": "Passed", "verification_scope": "portable_saved_archive_admission_no_tool_start",
            "layout_run_id": run["id"], "archive_manifest_sha256": sha(args.evidence / "manifest.json"), "model_calls": 0, "tool_starts": 0}))
        return 0
    parser.error("--physical-config and --output are required for actual replay") if args.physical_config is None or args.output is None else None
    report = replay(args.evidence, args.physical_config, args.output)
    print(json.dumps(report)); return 0 if report["validation_status"] == "Passed" else 1


if __name__ == "__main__": raise SystemExit(main())

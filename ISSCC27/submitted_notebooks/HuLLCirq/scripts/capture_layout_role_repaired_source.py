#!/usr/bin/env python3
"""Freeze the one GUI-adopted repaired NPU2 layout for a new read-only map.

This derivation reads completed, source-bound outputs. It starts no process,
EDA, model or workflow, changes no RTL/store, and never overwrites old bundles.
The upstream synthesis graph is reused from its pinned original archive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

from capture_layout_role_source import (CaptureError, RTL_INPUTS, TOP, _declared_bytes,
    _json_bytes, _one, _record, _recorded_artifact_root, _require, _checked_relative_path)
from hullcirq.domain import DomainError
from hullcirq.layout_roles import (bridge_synthesis, parse_def_components,
    parse_structural_verilog, source_profile_values)
from hullcirq.physical_repair import (NPU2_SOURCE_BINDING, NPU2_RETRY_SOURCE_BINDING,
    NPU2_RETRY_STATE_SHA, NPU2_RETRY_INPUT_SHA, NPU2_RETRY_INVENTORY_SHA,
    NPU2_RETRY_INVENTORY_ORIGIN, PROFILE_NPU2, PROFILE_NPU2_RETRY,
    NPU2_FINAL_SOURCE_BINDING, NPU2_FINAL_STATE_SHA, NPU2_FINAL_INPUT_SHA,
    NPU2_FINAL_INVENTORY_SHA, NPU2_FINAL_INVENTORY_ORIGIN, NPU2_FINAL_STEP, PROFILE_NPU2_FINAL)
from hullcirq.physical_tools import validate_layout_result, validate_failed_layout_result
from hullcirq.physical_workflow import validate_physical_proof, validate_failed_physical_proof
from hullcirq.postlayout_cleanup import execution_hash
from hullcirq.store import strict_loads
from hullcirq.verification import object_hash

RUN_ID = "physical-workflow-4e818ce3905c4bd1ad0e9b50033271cb"
RUNTIME_SHA256 = "ce7909e2bfd799bc9564f1dc644efe06603758d06c24c42eadd29fb1c5951042"
RETRY_START_STEP = NPU2_FINAL_STEP
INVENTORY_RELATIVE = "configs/npu2_final_checkpoint_inventory.json"
PRE_RETRY_INVENTORY_RELATIVE = "configs/npu2_retry_checkpoint_inventory.json"
ORIGINAL_SOURCE_ROOT = "results/npu2_layout_role_source_20261020"
ORIGINAL_MANIFEST_SHA256 = "585e3139b9f130b9db57d96e6635daee99d09b1a4c2524fa179bdabe6568d102"
OUTPUT_RELATIVE = "results/npu2_layout_repaired_source_20261021"
PROFILE_RELATIVE = "configs/layout_roles_npu2_repaired_source_20261021.json"
STORE_RELATIVE = ".work/projects/npu_2x2_explicit/systems/system-7df07952c6b64696813d14ab19837af8/physical_workflow.json"
LINEAGE_FIELDS = ("revision_id", "global_job_id", "global_context_id", "synthesis_run_id", "netlist_run_id",
                  "global_rtl_sha256", "source_manifest_sha256", "verification_plan_sha256", "vector_hash",
                  "testbench_sha256", "public_boundary_vector_hash", "settings_sha256")


def _checksum(value):
    _require(type(value) is dict and value.get("record_hash") == object_hash(
        {key: item for key, item in value.items() if key != "record_hash"}), "Saved physical record checksum changed")


def _original_archive():
    archive = (ROOT / ORIGINAL_SOURCE_ROOT).resolve()
    _require(archive.is_relative_to((ROOT / "results").resolve()), "Original archive is outside results")
    manifest_raw = (archive / "manifest.json").read_bytes()
    _require(hashlib.sha256(manifest_raw).hexdigest() == ORIGINAL_MANIFEST_SHA256,
             "The original immutable source archive manifest changed")
    manifest = strict_loads(manifest_raw.decode("utf-8"))
    _require(manifest.get("validation_status") == "Passed"
             and manifest.get("layout_run_id") == NPU2_SOURCE_BINDING["layout_run_id"]
             and type(manifest.get("files")) is dict, "The original source archive identity changed")
    pending = {}
    for relative in ("layout_record.json", "source_binding.json", "artifacts/synthesis.json", "artifacts/synthesis.v",
                     *("artifacts/" + filename for filename, _, _ in RTL_INPUTS)):
        expected = manifest["files"].get(relative)
        _require(type(expected) is dict, "Original archive input declaration is missing: " + relative)
        pending[relative] = _declared_bytes(archive, {"relative_path": relative, **expected})
    original = strict_loads(pending["layout_record.json"].decode("utf-8"))
    _checksum(original)
    _require(original["record_hash"] == NPU2_SOURCE_BINDING["layout_record_sha256"],
             "The original archived layout record identity changed")
    for key in ("revision_id", "global_job_id", "global_rtl_sha256", "source_manifest_sha256", "verification_plan_sha256", "settings_sha256"):
        _require(original.get(key) == NPU2_SOURCE_BINDING[key], "Original fixed source binding changed: " + key)
    return manifest_raw, pending, original


def _selected_run(store, original):
    _require(type(store) is dict and store.get("physical_workflow_store_version") == "0.1"
             and type(store.get("runs")) is list and store["runs"], "Require the original physical workflow store")
    run = _one(store["runs"], "id", RUN_ID, "fixed repaired S11 run")
    _checksum(run)
    _require(store["runs"][-1].get("id") == RUN_ID and run.get("execution_status") == "Completed"
             and run.get("validation_status") == "Passed" and run.get("review_status") == "Accepted"
             and run.get("evidence_kind") == "trusted_fixed_tool_execution" and run.get("error") is None,
             "Wait for the exact latest repaired S11 to be Completed / Passed / Accepted")
    _require(type(store.get("source_epoch")) is int and store["source_epoch"] > 0
             and run.get("source_key") == store.get("source_key")
             and run.get("source_epoch_at_start") == run.get("acceptance_epoch") == store["source_epoch"],
             "The repaired S11 must remain Current in its saved source epoch")
    reviews = [review for review in store.get("reviews", []) if review.get("run_id") == RUN_ID]
    _require(reviews and reviews[-1].get("decision") == "accepted"
             and reviews[-1].get("source_key") == run["source_key"]
             and reviews[-1].get("acceptance_epoch") == store["source_epoch"],
             "Retain the current authoritative repaired S11 adoption")
    _require(all(run.get(key) == original.get(key) for key in LINEAGE_FIELDS),
             "The repaired layout changed the original revision, S08 job, RTL, plan, settings or S09/S10 lineage")
    for key in ("global_rtl", "source_manifest", "verification_plan", "settings"):
        _require(object_hash(run.get(key)) == object_hash(original.get(key)), "Original design input changed: " + key)
    runtime = run.get("runtime_configuration")
    _require(type(runtime) is dict and type(runtime.get("profile")) is dict
             and runtime["profile"].get("profile_version") == PROFILE_NPU2_FINAL
             and object_hash(runtime) == run.get("runtime_configuration_sha256") == RUNTIME_SHA256
             and runtime.get("repair_source_binding") == NPU2_FINAL_SOURCE_BINDING
             and runtime.get("repair_checkpoint_inventory") == {"relative_path": INVENTORY_RELATIVE,
                 "sha256": NPU2_FINAL_INVENTORY_SHA, "origin": NPU2_FINAL_INVENTORY_ORIGIN}
             and type(runtime.get("resume")) is dict and runtime["resume"].get("initial_state_sha256") == NPU2_FINAL_STATE_SHA
             and runtime["resume"].get("source_input_manifest_sha256") == NPU2_FINAL_INPUT_SHA
             and runtime["resume"].get("from_step") == RETRY_START_STEP,
             "Only the fixed NPU2 v3 post-timing electrical correction runtime is supported")
    checks = run.get("checks")
    _require(type(checks) is dict and checks.get("origin") == "trusted_fixed_tool_adapter"
             and checks.get("technology_mapping_executed") is False
             and checks.get("upstream_technology_mapping_reused") is True
             and checks.get("implementation_kind") == "resumed_post_GRT_route_repair"
             and checks.get("cleanup_unresolved") is False,
             "The new map must retain the actual resumed repair and explicitly reused synthesis scope")
    validate_physical_proof(run, validate_layout_result)
    return run


def _first_repair_ancestry(store, original):
    """Keep the unadopted first correction distinct from the original mapping."""
    first = _one(store["runs"], "id", NPU2_RETRY_SOURCE_BINDING["layout_run_id"], "failed first-correction source")
    _checksum(first)
    runtime = first.get("runtime_configuration")
    _require(first.get("execution_status") == "Completed" and first.get("validation_status") == "Failed"
             and first.get("review_status") in ("Awaiting Review", "Changes Requested")
             and first.get("evidence_kind") == "trusted_fixed_tool_execution" and first.get("error") is None
             and execution_hash(first) == NPU2_RETRY_SOURCE_BINDING["layout_execution_sha256"]
             and type(runtime) is dict and runtime.get("profile", {}).get("profile_version") == PROFILE_NPU2
             and runtime.get("repair_source_binding") == NPU2_SOURCE_BINDING
             and object_hash(runtime) == first.get("runtime_configuration_sha256")
                 == NPU2_RETRY_SOURCE_BINDING["original_runtime_configuration_sha256"],
             "Retain the exact executed, unadopted first correction and its unchanged original ancestry")
    _require(all(first.get(key) == original.get(key) for key in LINEAGE_FIELDS)
             and all(object_hash(first.get(key)) == object_hash(original.get(key))
                     for key in ("global_rtl", "source_manifest", "verification_plan", "settings")),
             "The first correction changed the original GUI job, RTL, verification plan or mapped-source ancestry")
    validate_failed_physical_proof(first, validate_failed_layout_result)
    return first


def _second_repair_ancestry(store, original):
    """Retain the failed v2 source separately; never relabel either failure."""
    second = _one(store["runs"], "id", NPU2_FINAL_SOURCE_BINDING["layout_run_id"], "failed second-correction source")
    _checksum(second)
    runtime = second.get("runtime_configuration")
    _require(second.get("execution_status") == "Completed" and second.get("validation_status") == "Failed"
             and second.get("review_status") in ("Awaiting Review", "Changes Requested")
             and second.get("evidence_kind") == "trusted_fixed_tool_execution" and second.get("error") is None
             and execution_hash(second) == NPU2_FINAL_SOURCE_BINDING["layout_execution_sha256"]
             and type(runtime) is dict and runtime.get("profile", {}).get("profile_version") == PROFILE_NPU2_RETRY
             and runtime.get("repair_source_binding") == NPU2_RETRY_SOURCE_BINDING
             and object_hash(runtime) == second.get("runtime_configuration_sha256")
                 == NPU2_FINAL_SOURCE_BINDING["original_runtime_configuration_sha256"],
             "Retain the exact executed, unadopted second correction and its first-failure ancestry")
    _require(all(second.get(key) == original.get(key) for key in LINEAGE_FIELDS)
             and all(object_hash(second.get(key)) == object_hash(original.get(key))
                     for key in ("global_rtl", "source_manifest", "verification_plan", "settings")),
             "The second correction changed the original job, RTL, plan or source ancestry")
    validate_failed_physical_proof(second, validate_failed_layout_result)
    return second


def capture():
    """Write only the two new fixed derivation destinations after all checks."""
    root = ROOT.resolve()
    output = root / OUTPUT_RELATIVE
    profile_path = root / PROFILE_RELATIVE
    store_path = root / STORE_RELATIVE
    _require(not output.exists() and not profile_path.exists(), "Output exists; old archives and profiles are never overwritten")
    _require(output.resolve().is_relative_to(root) and profile_path.resolve().is_relative_to(root)
             and output.resolve().parent == (root / "results").resolve()
             and profile_path.resolve().parent == (root / "configs").resolve()
             and not output.is_symlink() and not output.is_junction()
             and not profile_path.is_symlink() and not profile_path.is_junction(), "Fixed output paths cannot be linked or redirected")
    original_manifest_raw, upstream, original = _original_archive()
    store_raw = store_path.read_bytes()
    store = strict_loads(store_raw.decode("utf-8"))
    run = _selected_run(store, original)
    first_repair = _first_repair_ancestry(store, original)
    second_repair = _second_repair_ancestry(store, original)
    checks = run["checks"]
    artifact_root = _recorded_artifact_root(checks["artifacts_directory"])
    _require(artifact_root.is_relative_to(root) and artifact_root.parent == (root / ".work/n2t/p").resolve()
             and artifact_root.parent == Path(run["runtime_configuration"]["working_directory"]).resolve()
             and re.fullmatch(r"hullcirq-layout-[A-Za-z0-9_-]+", artifact_root.name) is not None,
             "Use the exact new v3 corrected run directory below .work/n2t/p")
    artifacts = checks.get("artifacts")
    _require(type(artifacts) is list and len({entry.get("id") for entry in artifacts}) == len(artifacts),
             "Require unique repaired layout artifact IDs")
    pending, observed, bindings = {}, {}, []
    bundle = checks.get("source_bundle")
    _require(type(bundle) is list and len(bundle) == len(RTL_INPUTS), "Retain all twelve unchanged source RTL files")
    for filename, module_name, artifact_id in RTL_INPUTS:
        source = _one(bundle, "file", filename, "unchanged source RTL")
        entry = _one(artifacts, "id", artifact_id, "repaired RTL artifact")
        raw = _declared_bytes(artifact_root, entry, filename)
        _require(source.get("module_name") == module_name and source.get("sha256") == entry["sha256"]
                 and raw == upstream["artifacts/" + filename], "Repaired source RTL differs from the original archive: " + filename)
        target = "artifacts/" + filename
        pending[target] = raw; observed[entry["relative_path"]] = raw
        bindings.append({"artifact_id": artifact_id, "source_relative_path": entry["relative_path"], "target": target, **_record(raw)})
    for artifact_id, target in (("gds", "artifacts/final.gds"), ("def", "artifacts/final.def"), ("netlist", "artifacts/final.nl.v")):
        entry = _one(artifacts, "id", artifact_id, "new repaired layout artifact")
        raw = _declared_bytes(artifact_root, entry)
        pending[target] = raw; observed[entry["relative_path"]] = raw
        bindings.append({"artifact_id": artifact_id, "source_relative_path": entry["relative_path"], "target": target, **_record(raw)})
    for relative in ("artifacts/synthesis.json", "artifacts/synthesis.v"):
        pending[relative] = upstream[relative]
    for filename, expected_hash in (("resume-original-state.json", NPU2_FINAL_STATE_SHA),
                                    ("resume-original-input-manifest.json", NPU2_FINAL_INPUT_SHA),
                                    ("resume-manifest.json", checks.get("checkpoint_manifest_sha256"))):
        raw = _checked_relative_path(artifact_root, filename).read_bytes()
        _require(hashlib.sha256(raw).hexdigest() == expected_hash, "The frozen checkpoint proof changed: " + filename)
        pending["checkpoint/" + filename] = raw; observed[filename] = raw
    inventory_path = _checked_relative_path(root, INVENTORY_RELATIVE)
    inventory_raw = inventory_path.read_bytes()
    _require(hashlib.sha256(inventory_raw).hexdigest() == NPU2_FINAL_INVENTORY_SHA,
             "The fixed post-timing observation inventory changed")
    pending["checkpoint/pre_final_observation_inventory.json"] = inventory_raw
    pre_retry_inventory_path = _checked_relative_path(root, PRE_RETRY_INVENTORY_RELATIVE)
    pre_retry_inventory_raw = pre_retry_inventory_path.read_bytes()
    _require(hashlib.sha256(pre_retry_inventory_raw).hexdigest() == NPU2_RETRY_INVENTORY_SHA,
             "The fixed pre-retry observation inventory changed")
    pending["checkpoint/pre_retry_observation_inventory.json"] = pre_retry_inventory_raw
    pending["checkpoint/first_repair_failed_record.json"] = _json_bytes(first_repair)
    pending["checkpoint/second_repair_failed_record.json"] = _json_bytes(second_repair)
    pending["upstream/original_source_manifest.json"] = original_manifest_raw
    synthesis_document = strict_loads(pending["artifacts/synthesis.json"].decode("utf-8"))
    synthesis = parse_structural_verilog(pending["artifacts/synthesis.v"].decode("utf-8"))
    final = parse_structural_verilog(pending["artifacts/final.nl.v"].decode("utf-8"))
    components = parse_def_components(pending["artifacts/final.def"].decode("utf-8"))
    _require(synthesis["top"] == final["top"] == TOP and TOP in synthesis_document["modules"], "Retain the original NPU2 mapped top")
    _, bridge = bridge_synthesis(synthesis_document["modules"][TOP], synthesis)
    _require(set(final["cells"]) == set(components) and all(final["cells"][name]["master"] == master for name, master in components.items()),
             "New final mapped netlist and DEF instance/master sets differ")
    old_binding = strict_loads(upstream["source_binding.json"].decode("utf-8"))
    _require(len(synthesis["cells"]) == old_binding["structural_checks"]["synthesis_cells"] and len(final["cells"]) > 0,
             "Reused synthesis count or new layout cell inventory is inconsistent")
    pending["layout_record.json"] = _json_bytes(run)
    binding = {"schema_version": 1, "kind": "immutable_npu2_repaired_layout_role_source_binding",
        "layout_run_id": RUN_ID, "record_hash": run["record_hash"], "lineage": {key: run[key] for key in LINEAGE_FIELDS},
        "physical_store_snapshot": {"path": STORE_RELATIVE, **_record(store_raw)}, "artifact_bindings": bindings,
        "upstream_synthesis": {"archive": ORIGINAL_SOURCE_ROOT, "manifest_sha256": ORIGINAL_MANIFEST_SHA256,
            "layout_run_id": original["id"], "layout_record_sha256": original["record_hash"],
            "inputs": {relative: _record(upstream[relative]) for relative in ("artifacts/synthesis.json", "artifacts/synthesis.v")},
            "scope": "reused_original_technology_mapping_no_fresh_synthesis"},
        "checkpoint_proof": {"source_run_id": second_repair["id"], "source_validation_status": "Failed",
            "source_adopted": False, "source_execution_sha256": execution_hash(second_repair),
            "source_runtime_configuration_sha256": second_repair["runtime_configuration_sha256"],
            "resume_from_step": RETRY_START_STEP,
            "scope": "reused_second_correction_completed_all_corner_timing_then_one_extra_standard_electrical_repair",
            "state_sha256": NPU2_FINAL_STATE_SHA, "input_manifest_sha256": NPU2_FINAL_INPUT_SHA,
            "pre_final_inventory_sha256": NPU2_FINAL_INVENTORY_SHA,
            "checkpoint_view_hash_origin": NPU2_FINAL_INVENTORY_ORIGIN,
            "resume_manifest_sha256": checks["checkpoint_manifest_sha256"], "full_saved_physical_proof_revalidated_read_only": True},
        "prior_checkpoint_observation": {"source_run_id": first_repair["id"],
            "source_execution_sha256": execution_hash(first_repair),
            "inventory_relative_path": "checkpoint/pre_retry_observation_inventory.json",
            "inventory_sha256": NPU2_RETRY_INVENTORY_SHA,
            "checkpoint_view_hash_origin": NPU2_RETRY_INVENTORY_ORIGIN,
            "state_sha256": NPU2_RETRY_STATE_SHA, "input_manifest_sha256": NPU2_RETRY_INPUT_SHA},
        "failed_repair_ancestry": [{"run_id": item["id"], "validation_status": "Failed", "adopted": False,
            "execution_sha256": execution_hash(item), "record_sha256": item["record_hash"],
            "profile_version": item["runtime_configuration"]["profile"]["profile_version"],
            "runtime_configuration_sha256": item["runtime_configuration_sha256"],
            "full_saved_physical_proof_revalidated_read_only": True} for item in (first_repair, second_repair)],
        "structural_checks": {"top_module": TOP, "synthesis_cells": len(synthesis["cells"]), "final_cells": len(final["cells"]),
            "def_components": len(components), "synthesis_json_verilog_bridge": bridge,
            "final_netlist_def_exact_instance_master_match": True},
        "derivation_activity": {"model_calls": 0, "rtl_generations": 0, "rtl_edits": 0, "eda_runs": 0,
            "review_or_adoption_actions": 0, "saved_project_mutations": 0}}
    pending["source_binding.json"] = _json_bytes(binding)
    pending["README.md"] = ("# Repaired NPU2 Functional Map source\n\n"
        f"Immutable read-only derivation of `{RUN_ID}`. New GDS, DEF and mapped netlist are bound to the current accepted repair. "
        "The twelve RTL files and original finite GUI job are unchanged. Synthesis JSON/Verilog are reused from the checksum-pinned "
        "original source archive; no fresh synthesis is claimed. The v3 correction resumes the failed second correction's "
        "post-timing checkpoint and runs one additional standard electrical repair. Both earlier failures remain unadopted, "
        "with their complete saved proof revalidated and records archived separately. The nested checkpoint input manifest "
        "retains the earlier runtime/resume provenance without flattening it into the original mapping. "
        "Both fixed checkpoint inventories are retained separately: the pre-retry inventory was observed after the first failure, "
        "and the post-timing inventory after the second failure. Neither is claimed as an original retained hash. "
        "The complete saved physical/resume proof was revalidated without "
        "starting tools. Capture and rendering add no EDA/model runs, circuit verification, adoption or project mutation. "
        "Functional roles annotate actual cells; inferred roles do not establish recovered module ownership.\n").encode("utf-8")
    manifest = {"schema_version": 1, "kind": "immutable_npu2_repaired_layout_role_source", "validation_status": "Passed",
        "validation_scope": "archive_integrity_exact_repaired_S11_binding_and_read_only_saved_proof_only",
        "layout_run_id": RUN_ID, "files": {relative: _record(raw) for relative, raw in pending.items()}}
    manifest_raw = _json_bytes(manifest)
    profile = {"source_root": OUTPUT_RELATIVE, "source_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "layout_run_id": RUN_ID, "inputs": {"synthesis_json": "artifacts/synthesis.json", "synthesis_verilog": "artifacts/synthesis.v",
            "final_verilog": "artifacts/final.nl.v", "final_def": "artifacts/final.def"},
        "expected_final_cells": len(final["cells"]), "expected_synthesis_cells": len(synthesis["cells"]),
        "gds_relative_path": "artifacts/final.gds", "role_profile": "npu2_explicit_2x2_v1"}
    source_profile_values(profile)
    _require(store_path.read_bytes() == store_raw, "The physical store changed during read-only capture")
    _require((root / ORIGINAL_SOURCE_ROOT / "manifest.json").read_bytes() == original_manifest_raw, "Original archive changed during capture")
    _require(inventory_path.read_bytes() == inventory_raw, "The post-timing observation inventory changed during capture")
    _require(pre_retry_inventory_path.read_bytes() == pre_retry_inventory_raw,
             "The pre-retry observation inventory changed during capture")
    for relative, raw in observed.items():
        _require(_checked_relative_path(artifact_root, relative).read_bytes() == raw, "Repaired input changed during capture: " + relative)
    # Recheck the original reused inputs before creating either new destination.
    _, reread_upstream, _ = _original_archive()
    _require(reread_upstream == upstream, "Original archive inputs changed during capture")
    output.mkdir(parents=True)
    for relative, raw in {**pending, "manifest.json": manifest_raw}.items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream: stream.write(raw)
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    with profile_path.open("xb") as stream: stream.write(_json_bytes(profile))
    return {"layout_run_id": RUN_ID, "output": str(output), "source_profile": str(profile_path),
        "source_manifest_sha256": profile["source_manifest_sha256"], "files": len(pending) + 1,
        "final_cells": len(final["cells"]), "synthesis_cells": len(synthesis["cells"]),
        "additional_eda_runs": 0, "saved_project_mutations": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        result = capture()
    except (CaptureError, DomainError, OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

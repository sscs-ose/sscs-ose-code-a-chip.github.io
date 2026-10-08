"""Fresh identities and strict pure-helper reuse; no old checkpoint or history is read."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ENTRY = HERE.parent
WINDOWS = ENTRY / "layout_pvt45_windows"
sys.path.insert(0, str(WINDOWS))
sys.path.insert(0, str(WINDOWS / "supervised_v2"))
sys.path.insert(0, str(WINDOWS / "io_retry_v3"))

import windows_contract as old_windows
from collector_v1 import classify
from checkpoint_writer import CheckpointWriter
from clockguard import WorkerGuard, WindowExpired, clock_sample
from winjob import OwnedProcess

phase = old_windows.phase
require = old_windows.require
IntegrityError = old_windows.IntegrityError
sha256 = old_windows.sha256
canonical_sha256 = old_windows.canonical_sha256
write_json = old_windows.write_json
PROTOCOL = json.loads((HERE / "protocol.json").read_text())
STEPS = PROTOCOL["scientific_contract"]["steps_ps"]
DEADLINES = PROTOCOL["scientific_contract"]["reporting_deadlines_ns"]


def points(mode: str) -> list[dict]:
    require(mode in ("smoke", "full"), "Select explicit --smoke or --full")
    all_points = phase.build_matrix()["points"]
    selected = (all_points if mode == "full" else [
        p for p in all_points if p["point_id"] in PROTOCOL["smoke"]["point_ids"]])
    require(len(selected) == (360 if mode == "full" else 2), "Changed fresh matrix size")
    return selected


def initial_order(mode: str) -> list[tuple[str, float]]:
    selected = points(mode)
    schedule = []
    for condition in dict.fromkeys(p["condition_id"] for p in selected):
        group = [p for p in selected if p["condition_id"] == condition]
        for step in (10, 5):
            schedule.extend((p["point_id"], step) for p in group)
    require(len(schedule) == (720 if mode == "full" else 4), "Changed initial schedule")
    return schedule


def source_audit() -> dict:
    manifest = json.loads((HERE / "source-pins.json").read_text())
    observed = {}
    variants = {}
    for name, expected in manifest["files"].items():
        observed[name] = sha256(ENTRY / name)
        if observed[name] != expected:
            require(os.name == "nt" and observed[name] == manifest["exact_windows_variants"].get(name),
                    f"Reproduction source/input changed: {name}")
            variants[name] = observed[name]
    circuit = PROTOCOL["circuit"]
    for mode in ("schematic", "rc"):
        require(sha256(ENTRY / circuit[f"{mode}_path"]) == circuit[f"{mode}_sha256"],
                "Frozen native netlist changed")
    phase.historical.audit_source(ENTRY / circuit["schematic_path"])
    rc = phase.historical.read_spice(ENTRY / circuit["rc_path"])
    contract = phase.historical.check_netlist(rc, rc=True)
    require(rc["ports"] == circuit["ordered_ports"] and contract["device_count"] == 27,
            "Original27-device/15-port circuit contract changed")
    require(STEPS == phase.STEPS and DEADLINES == phase.DEADLINES,
            "Numerical policy or reporting deadlines changed")
    return {
        "source_sha256": observed, "explicit_windows_variants": variants,
        "fresh_source_pins_sha256": sha256(HERE / "source-pins.json"),
        "fresh_protocol_sha256": sha256(HERE / "protocol.json"),
        "rc_contract": contract,
        "native_sha256": {m: circuit[f"{m}_sha256"] for m in ("schematic", "rc")},
        "no_historical_checkpoint_or_old_job_receipt_required": True,
    }


def models_audit(directory: Path, guard=None) -> dict:
    manifest = json.loads((ENTRY / PROTOCOL["runtime"]["exact_raw_models_manifest"]).read_text())
    require(manifest["model_revision"] == PROTOCOL["runtime"]["model_commit"]
            and len(manifest["files"]) == 400, "Unpinned model source manifest")
    for name, record in manifest["files"].items():
        if guard:
            guard.check("model_hash_check", component=name)
        data = (directory / name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == record["actual_parent_sha256"],
                f"Raw Windows model hash mismatch: {name}")
        canonical = data if record["relation"] == "byte_identical" else data.replace(b"\r\n", b"\n")
        require(hashlib.sha256(canonical).hexdigest() == record["pinned_git_blob_sha256"],
                f"Canonical f62031 model content mismatch: {name}")
    return {
        "revision": manifest["model_revision"], "raw_model_file_count_including_license": 400,
        "raw_and_canonical_manifest_sha256": sha256(ENTRY / PROTOCOL["runtime"]["exact_raw_models_manifest"]),
        "parent_raw_bytes_never_normalized_or_changed": True,
    }


def devices() -> dict:
    return {
        "schematic": phase.historical.DEVICES,
        "rc": phase.historical.read_spice(ENTRY / PROTOCOL["circuit"]["rc_path"])["devices"],
    }


def make_deck(definition: dict, step: float) -> str:
    sys.path.insert(0, str(ENTRY))
    from comparator_atlas.spice import Point
    mode = definition["mode"]
    path = ENTRY / PROTOCOL["circuit"][f"{mode}_path"]
    point = Point(**definition["physical_point"], max_step_ps=step)
    deck = phase.native_simulator.make_deck(mode, point, path.read_text(),
                                           Path("../../model-source"), devices()[mode])
    command = f"tran {step:.12g}p 30n 19n {step:.12g}p\n"
    require(deck.count(command) == 1, "Ambiguous native transient statement")
    return deck.replace(command, "\n".join(PROTOCOL["runtime"]["control_before_tran"]) + "\n" + command, 1)


def cap(mode: str) -> int:
    return PROTOCOL[mode]["maximum_charged_transients"]


def check_charge(mode: str, attempts: list[dict], point_id: str, step: float) -> None:
    require(len(attempts) < cap(mode), "Fresh reproduction attempt cap exhausted")
    selected = {p["point_id"] for p in points(mode)}
    require(point_id in selected, "Unplanned point")
    require(not any(a["point_id"] == point_id and a["max_step_ps"] == step for a in attempts),
            "A charged point/step is never automatically retried")
    prior = [a["max_step_ps"] for a in attempts if a["point_id"] == point_id]
    require(prior == STEPS[:len(prior)] and len(prior) < len(STEPS) and step == STEPS[len(prior)],
            "Coarse restart or skipped refinement")
    if step not in (10, 5):
        require(mode == "full" and sum(a["max_step_ps"] in (10, 5) for a in attempts) == 720,
                "Smoke has no extra refinements; full requires all720initialattempts first")


def compare_reference(record: dict) -> dict:
    reference = json.loads((HERE / PROTOCOL["validation"]["smoke_reference"]).read_text())
    expected = next(r for r in reference["records"]
                    if r["mode"] == record["mode"] and r["max_step_ps"] == record["max_step_ps"])
    require(record["point"] == expected["point"], "Smoke/reference physical point differs")
    comparisons = phase.historical.compare_measurements(expected["measurements"], record["measurements"])
    selected = [d for d in comparisons["deadlines"] if d["deadline_ns"] in (1, 2)]
    return {
        "reference_attempt_id": expected["attempt_id"],
        "reference_record_sha256": expected["accepted_record_sha256"],
        "passed": all(d["passed"] for d in selected),
        "qualification_deadlines": selected, "all_reporting_comparisons": comparisons,
        "comparison_is_fixed_tolerance_not_floatingpoint_identity": True,
    }

"""Apply four real M2 bridges using the immutable nominal27 toolchain."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

HERE = Path(__file__).resolve().parent
ENTRY = HERE.parent
NOMINAL = ENTRY / "layout_nominal27"
sys.path.insert(0, str(NOMINAL))

import analyze as native_analysis
import layout as native_layout
from contract import (
    DEVICES, PROTOCOL as FIXED_PROTOCOL, audit_source, gds_bounds, inspect_mag,
    require, sha256, write_json,
)

PROTOCOL = json.loads((HERE / "protocol.json").read_text())
BASELINE = ENTRY / PROTOCOL["baseline"]["native_snapshot"]
GRID = PROTOCOL["geometry_delta"]["grid_um"]


def audit_inherited_inputs() -> dict:
    manifest = json.loads((HERE / "inherited-sha256.json").read_text())
    expected = manifest["committed_and_linux_sha256"]
    observed, windows_variants = {}, {}
    for name, digest in expected.items():
        observed[name] = sha256(ENTRY / name)
        if observed[name] != digest:
            require(os.name == "nt" and os.environ.get("GITHUB_ACTIONS") != "true"
                    and observed[name] == manifest["preserved_windows_preflight_worktree_sha256"].get(name),
                    f"Frozen inherited input changed: {name}")
            windows_variants[name] = {"exact_windows_sha256": observed[name],
                                      "exact_committed_linux_sha256": digest}
    fixed = PROTOCOL["fixed_contract"]
    require(sha256(ENTRY / fixed["path"]) == fixed["sha256"], "Frozen compact protocol changed")
    policy = {key: FIXED_PROTOCOL[key] for key in fixed["non_layout_keys"]}
    digest = hashlib.sha256(json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(digest == fixed["canonical_non_layout_sha256"], "Non-layout policy changed")
    require(FIXED_PROTOCOL["source"]["sha256"] == fixed["source_sha256"]
            and FIXED_PROTOCOL["source"]["ordered_ports"] == fixed["ordered_ports"],
            "Published source/port contract changed")
    schedule = PROTOCOL["simulation_schedule"]
    simulation, numerics = FIXED_PROTOCOL["simulation"], FIXED_PROTOCOL["numerics"]
    stimulus = simulation["stimulus"]
    for new_key, old_key in (
        ("clock_ns", "clock_period_ns"), ("edges_ps", "edge_ps"),
        ("common_mode_vdd", "common_mode_ratio"), ("external_load_ff_each", "load_ff_each"),
        ("primary_deadline_ns", "primary_deadline_ns"), ("differentials_mv", "differentials_mv"),
    ):
        require(schedule[new_key] == stimulus[old_key], f"Repair changed fixed stimulus: {new_key}")
    require(schedule["first_gate"] == simulation["first_gate"]
            and schedule["pilot"] == simulation["pilot"]
            and schedule["modes"] == FIXED_PROTOCOL["extraction"]["modes"]
            and schedule["rails_vdd"] == [stimulus["rail_high_vdd"], stimulus["rail_low_vdd"]]
            and schedule["initial_steps_ps"] == numerics["initial_max_steps_ps"]
            and schedule["sensitive_steps_ps"] == numerics["further_max_steps_ps"]
            and schedule["energy_relative_error_percent"] == numerics["maximum_energy_relative_error_percent"]
            and schedule["latency_error_ns"] == numerics["maximum_latency_error_ns"]
            and fixed["pair_skew"] == fixed["trim_code"] == 0
            and fixed["device_count"] == len(DEVICES) == 27,
            "Repair schedule differs from the fixed circuit or numerical contract")
    authorization = PROTOCOL["authorization"]
    require(authorization["maximum_new_jobs"] == 2 and authorization["maximum_minutes_each"] == 30
            and authorization["prior_preflight_jobs_used"] == authorization["prior_nominal27_jobs_used"] == 4,
            "Separate bounded repair authorization changed")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        require(os.environ.get("GITHUB_REPOSITORY") == PROTOCOL["authorization"]["repository"]
                and os.environ.get("GITHUB_REF") == "refs/heads/" + PROTOCOL["authorization"]["branch"],
                "Repair execution is outside its authorized repository/branch")
    return {"inherited_files_verified": len(expected), "inherited_sha256": observed,
            "offline_preserved_windows_line_endings": windows_variants,
            "fixed_non_layout_sha256": digest,
            "repair_protocol_sha256": sha256(HERE / "protocol.json"),
            "repair_source_sha256": {p.name: sha256(p) for p in sorted(HERE.iterdir())
                                     if p.is_file() and p.suffix in (".py", ".json", ".sh", ".yml")}}


def validate_placement(placement: dict) -> None:
    baseline = json.loads((BASELINE / "placement.json").read_text())
    require(set(placement) == set(baseline), "Repair changed the placed device set")
    # Native PCell save timestamps change their file hashes, not their geometry.
    fields = ("origin_um", "reflect_x", "pcell_gate_m1_area_um2", "pins_grid", "pins_um")
    for name in baseline:
        require(all(placement[name][key] == baseline[name][key] for key in fields),
                f"Repair changed native placement/pins/landing: {name}")


def append_bridges(out: Path, routing: dict) -> Path:
    baseline = json.loads((BASELINE / "routing.json").read_text())
    require(routing == baseline, "Compact routing changed before the four declared additions")
    delta = PROTOCOL["geometry_delta"]
    bridges = delta["bridges"]
    require(len(bridges) == 4 and {b["device"] for b in bridges}
            == {"Xrxp", "Xrxn", "Xrqp", "Xrqn"}, "Unexpected repair sites")
    lines = []
    for bridge in bridges:
        device = next(d for d in DEVICES if d["name"] == bridge["device"])
        require(device["model"] == "sky130_fd_pr__pfet_01v8" and device["nodes"][3] == "vdd"
                and bridge["terminal"] == "B" and bridge["net"] == "vdd",
                "Repair must preserve the original PFET VDD body connection")
        route = next(r for r in routing["terminal_routes"]
                     if (r["device"], r["terminal"]) == (bridge["device"], "B"))
        x = bridge["lane_x_um"]
        require(route["net"] == "vdd"
                and route["via1_um"] == [x, delta["original_body_via1_y_um"]]
                and route["via2_um"] == [x, delta["original_vdd_via2_y_um"]],
                f"Unexpected native body pad location: {bridge['device']}")
        rectangle = [coordinate * GRID for coordinate in bridge["rect_grid"]]
        require(math.isclose(rectangle[2] - rectangle[0], delta["bridge_width_um"], abs_tol=1e-9)
                and all(math.isclose(a, b, abs_tol=1e-9)
                        for a, b in zip((rectangle[1], rectangle[3]), delta["bridge_y_um"])),
                "Bridge differs from the frozen full-pad rectangle")
        lines.extend([
            "box_um " + " ".join(f"{value:.6f}" for value in rectangle),
            "paint metal2",
            f'puts "COMPACT_REPAIR_BRIDGE {bridge["device"]} B vdd"',
        ])
    original = (out / "route-request.tcl").read_text()
    path = out / "repair-request.tcl"
    path.write_text(original + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    write_json(out / "geometry-delta.json", {
        **delta, "revision": PROTOCOL["revision"],
        "unmodified_route_request_sha256": sha256(out / "route-request.tcl"),
        "repair_request_sha256": sha256(path),
        "baseline_routing_sha256": sha256(BASELINE / "routing.json"),
        "native_routing_report_unchanged": True,
    })
    return path


def equal_material_union(actual: list[list[int]], expected: list[list[int]], label: str) -> None:
    area = native_analysis.rectangle_union_area
    combined = area(actual + expected)
    require(area(actual) == area(expected) == combined,
            f"Actual native material changed outside declared repair: {label}")


def check_material_delta(actual: dict, baseline: dict) -> dict:
    require(actual["labels"] == baseline["labels"]
            and actual["label_positions"] == baseline["label_positions"],
            "Repair moved, removed or added native labels")
    old, new = baseline["rectangles"], actual["rectangles"]
    layers = set(old) | set(new)
    # Magic saves its DRC feedback in error_p. It is not mask material;
    # only the separate real DRC result may establish that violations cleared.
    material_layers = layers - {"metal2", "error_p"}
    for layer in material_layers:
        equal_material_union(new.get(layer, []), old.get(layer, []), layer)
    residues = ("metal2", "via1", "via2")
    old_m2 = [r for layer in residues for r in old.get(layer, [])]
    new_m2 = [r for layer in residues for r in new.get(layer, [])]
    patches = [b["rect_grid"] for b in PROTOCOL["geometry_delta"]["bridges"]]
    equal_material_union(new_m2, old_m2 + patches, "metal2 including native via residues")
    before = native_analysis.rectangle_union_area(old_m2)
    after = native_analysis.rectangle_union_area(new_m2)
    expected_delta = PROTOCOL["geometry_delta"]["expected_m2_material_union_added_grid2"]
    require(after - before == expected_delta, "Repair metal area differs from exact declared addition")
    return {"unchanged_material_layers": sorted(material_layers),
            "native_drc_feedback_rectangles": {
                "layer": "error_p", "before": len(old.get("error_p", [])),
                "after": len(new.get("error_p", [])), "not_a_drc_pass_assertion": True,
                "no_erase_command_used": True,
            },
            "native_contacts_and_labels_unchanged": True,
            "actual_m2_union_equals_baseline_plus_four_bridges": True,
            "added_grid2": after - before, "added_um2": (after - before) * GRID**2,
            "m2_before_um2": before * GRID**2, "m2_after_um2": after * GRID**2}


def audit_saved_delta(out: Path) -> dict:
    actual_path = out / "atlas.mag"
    require("\nmagscale 1 2\n" in actual_path.read_text(), "Unexpected native geometry units")
    result = check_material_delta(inspect_mag(actual_path), inspect_mag(BASELINE / "atlas.mag"))
    bounds, old_bounds = gds_bounds(out / "atlas.gds"), gds_bounds(BASELINE / "atlas.gds")
    require(bounds == old_bounds, "The four local bridges changed the physical GDS bounding box")
    log = (out / "logs" / "route-magic.log").read_text()
    for bridge in PROTOCOL["geometry_delta"]["bridges"]:
        require(log.count(f'COMPACT_REPAIR_BRIDGE {bridge["device"]} B vdd') == 1,
                "Missing or repeated actual bridge command evidence")
    result.update(actual_mag_sha256=sha256(actual_path), actual_gds_sha256=sha256(out / "atlas.gds"),
                  baseline_mag_sha256=sha256(BASELINE / "atlas.mag"), physical_bbox=bounds)
    write_json(out / "actual-geometry-delta.json", result)
    return result


def main(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    (out / "logs").mkdir(exist_ok=True)
    results = []

    def record(name: str, operation) -> bool:
        try:
            row = {"check": name, "status": "PASS", "detail": operation()}
        except (AssertionError, ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
            row = {"check": name, "status": "FAIL", "error": str(error),
                   "traceback": traceback.format_exc()}
        results.append(row)
        write_json(out / "structural-results.json", results)
        print(f'{row["status"]}: {name}' + (f' -- {row["error"]}' if row["status"] == "FAIL" else ""),
              flush=True)
        return row["status"] == "PASS"

    for name in ("protocol.json", "inherited-sha256.json"):
        shutil.copyfile(HERE / name, out / name)
    shutil.copyfile(NOMINAL / "protocol.json", out / "baseline-protocol.json")
    shutil.copyfile(NOMINAL / "devices.json", out / "devices.json")
    try:
        if not record("frozen inherited source and separate repair authorization", audit_inherited_inputs):
            return 1
        if not record("immutable nominal source and independent 27-device table", audit_source):
            return 1
        if not record("27 actual checked open_pdks PCells",
                      lambda: native_layout.magic(out, "pcells", native_layout.make_pcells_request(out))):
            return 1
        placement = {}

        def build():
            placement.update(native_layout.assemble(out))
            validate_placement(placement)
            routing = native_layout.make_routes(out, placement)
            request = append_bridges(out, routing)
            native_layout.magic(out, "route", request)
            return {"placed_devices": len(placement), "routed_nets": len(routing["buses"]),
                    "added_real_m2_bridges": 4}

        if not record("unchanged compact routing plus four native M2 bridges", build):
            return 1
        record("exact saved material delta and unchanged native contacts", lambda: audit_saved_delta(out))
        record("nonempty layers actual bbox and gate M1 area", lambda: native_layout.geometry(out, placement))
        record("full named-style repaired comparator DRC", lambda: native_layout.drc(out, "atlas"))
        record("spacing DRC negative control",
               lambda: native_layout.drc(out, "nominal27_spacing_bad", negative=True))
        if record("native top ports and exact device connectivity", lambda: native_layout.native_interface(out)):
            record("independent nominal Netgen LVS", lambda: native_layout.lvs(out))
            for mutation in ("connection", "bulk", "width", "flavor"):
                record(f"comparator LVS {mutation} negative control",
                       lambda m=mutation: native_layout.lvs(out, m))
        else:
            for name in ("positive", "connection", "bulk", "width", "flavor"):
                results.append({"check": f"Netgen LVS {name}", "status": "SKIP",
                                "reason": "Actual native top/port/device contract failed"})
        for mode in ("c", "rc"):
            record(f"actual {mode} extraction and connectivity",
                   lambda m=mode: native_layout.extraction(out, m))

        def analyze():
            report = native_analysis.analyze(out)
            report["repair_revision"] = PROTOCOL["revision"]
            report["actual_geometry_delta_sha256"] = sha256(out / "actual-geometry-delta.json")
            write_json(out / "parasitic-analysis.json", report)
            return {"report_sha256": sha256(out / "parasitic-analysis.json"),
                    "all_native_junctions_and_passive_attachments_checked": True}

        record("native junctions capacitance resistance and material accounting", analyze)
        return 0 if len(results) == 17 and all(r["status"] == "PASS" for r in results) else 1
    finally:
        qualified = len(results) == 17 and all(r["status"] == "PASS" for r in results)
        write_json(out / "structural-results.json", results)
        write_json(out / "structural-handoff.json", {
            "phase": PROTOCOL["phase"], "revision": PROTOCOL["revision"],
            "qualified": qualified, "checks": len(results), "expected_checks": 17,
            "simulation_not_yet_qualified": True,
        })
        print(f"COMPACT_REPAIR_STRUCTURAL_QUALIFIED {int(qualified)}", flush=True)
        native_layout.manifest(out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path, nargs="?")
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    if args.audit_only:
        report = audit_inherited_inputs()
        print(json.dumps(report, indent=2))
    elif args.out is not None:
        sys.exit(main(args.out.resolve()))
    else:
        parser.error("provide a fresh output directory or --audit-only")

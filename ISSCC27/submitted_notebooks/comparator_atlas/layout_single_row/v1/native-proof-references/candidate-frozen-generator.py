"""One private, bounded single-row guarded-PCell spacing experiment."""

import argparse
from collections import Counter
import copy
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import traceback

parser = argparse.ArgumentParser()
parser.add_argument("--entry", type=Path, required=True)
parser.add_argument("--r1", type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
parser.add_argument("--tools", type=Path, required=True)
args = parser.parse_args()
entry, r1, out, tools = map(Path.resolve, (args.entry, args.r1, args.out, args.tools))
out.mkdir(exist_ok=False)
(out / "logs").mkdir()
sys.path.insert(0, str(entry / "layout_nominal27"))
import layout as native
import analyze
import contract

pins = json.loads((r1 / "continuation-tool-pins.json").read_text())
assert all(contract.sha256(tools / name) == value for name, value in pins.items())
old_manifest = json.loads((r1 / "artifact-sha256.json").read_text())
assert all(contract.sha256(r1 / name) == value for name, value in old_manifest.items())
for name, commit in (
    ("magic", "4f53bb3091d1e4a9b2009a58f157a8a4331d4c84"),
    ("netgen", "e1528a797cdb155d6ebf8d91c5a55ed7d1713156"),
    ("open_pdks", "aa3fc215a80d32437b8cca1cb3fdee819d18c4c9"),
):
    import subprocess
    assert subprocess.check_output(
        ["git", "-C", str(tools / "src" / name), "rev-parse", "HEAD"], text=True
    ).strip() == commit
os.environ["PATH"] = str(tools / "install/bin") + os.pathsep + os.environ["PATH"]
os.environ["PDK_ROOT"] = str(tools / "src/open_pdks/sky130")
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
contract.audit_source()
original = copy.deepcopy(contract.PROTOCOL)
control_routing = json.loads(
    (entry / "layout_compact_repair/evidence/attempt1/routing.json").read_text()
)

envelopes = {}
for device in contract.DEVICES:
    name = f"pcell_{device['name'].lower()}.mag"
    path = r1 / "candidate" / name
    parsed = contract.inspect_mag(path)
    material = {layer: rectangles for layer, rectangles in parsed["rectangles"].items()
                if layer not in ("checkpaint", "error_p")}
    envelopes[device["name"]] = {
        "source_sha256": contract.sha256(path),
        "layers": {layer: [min(r[0] for r in rectangles) * .005,
                          min(r[1] for r in rectangles) * .005,
                          max(r[2] for r in rectangles) * .005,
                          max(r[3] for r in rectangles) * .005]
                   for layer, rectangles in material.items() if rectangles},
    }
    shutil.copyfile(path, out / name)
shutil.copyfile(r1 / "candidate/pcells.tsv", out / "pcells.tsv")
well_width = max(box[2] - box[0] for row in envelopes.values()
                 for layer, box in row["layers"].items() if layer in ("nwell", "pwell"))
tech = (tools / "src/open_pdks/sky130/sky130A/libs.tech/magic/sky130A.tech").read_text()
assert "spacing allnwell allnwell 1270 touching_ok" in tech
assert math.isclose(well_width, 2.96)
# Reserve 0.20um beyond the rule; round outward to a 0.1um planning track.
constraints = {
    "well_envelope_plus_nwell_rule_plus_safety_um": well_width + 1.27 + .20,
    "adjacent_escape_envelopes_plus_metal_spacing_plus_safety_um": 3.36 + .14 + .20,
}
pitch = math.ceil((max(constraints.values()) - 1e-9) * 10) / 10
assert pitch == 4.5 and pitch < original["layout"]["placement_pitch_um"]
layout = contract.PROTOCOL["layout"]
layout["placement_pitch_um"] = pitch
layout["revision"] = {"name": "single-row-spacing-20261003-a1",
                      "decision": "New user-directed single-row round; not a two-row repair allowance."}
rules = layout["routing"]
rules["balanced_outputs"]["bus_half_span_um"] = 5 * pitch + 1.4
rules["ground_shields"]["left_um"] = -(5 * pitch + 2.4)
rules["ground_shields"]["right_um"] = 5 * pitch + 2.4
rules["ground_shields"]["metal4_spine_x_um"] = [-(5 * pitch + 2), 5 * pitch + 2]
rules["description"] = (
    "Same single-row pair order/mirroring/y, guarded native PCells, local escape offsets, "
    "bus y tracks/widths and three grounded shields. Geometry-derived4.5um pitch replaces4.8um; "
    "M3 endpoints/output equal spans/shield endpoints and symmetric M4 spines follow placements. "
    "Retain the four legal full-pad PFET-body M2 bridges at translated lanes."
)
static = {
    "pcell_envelopes_um": envelopes, "excluded_nonmask_feedback": ["checkpaint", "error_p"],
    "constraints_um": constraints, "chosen_pitch_um": pitch,
    "minimum_well_edge_gap_um": pitch - well_width,
    "nwell_spacing_rule_um": 1.27, "well_rule_margin_um": pitch - well_width - 1.27,
    "adjacent_escape_gap_lower_bound_um": pitch - 3.36,
    "metal_spacing_rule_um": .14,
    "not_a_global_minimum_or_signoff_claim": True,
}
contract.write_json(out / "static-envelope-diagnosis.json", static)
comparison = copy.deepcopy(json.loads((r1 / "protocol.json").read_text())[
    "comparison_frozen_before_any_new_spice"])
comparison["steps_ps"] = [10, 5]
comparison["maximum_transients"] = 64
comparison["no_further_step_or_pvt_expansion"] = True
comparison["numeric_acceptance"] = copy.deepcopy(original["numerics"])
comparison["numeric_acceptance"]["bounded_round_override"] = (
    "Apply unchanged10/5ps qualification; if unqualified, stop. No finer runs authorized."
)
frozen = {
    "candidate": layout["revision"]["name"], "control_head": "a9d510417a7de2e9ae62316636483f03654a91bf",
    "authorization": "2026-10-03 03:49 UTC+8 user selected single-row spacing/local-routing round",
    "maximum_native_drc_attempts": 2, "attempt_number": 1, "layout": layout,
    "static_diagnosis": static, "unchanged_nonlayout_protocol": {
        key: original[key] for key in ("source", "structural_gates", "extraction", "simulation", "numerics")
    },
    "physical_acceptance": {
        "area_definition": "BBox of all nonempty GDS material polygons, excluding TEXT only",
        "control_bbox_um": [-64.8, -4.84, 64.8, 12.19], "control_area_um2": 2207.088,
        "maximum_area_um2_exclusive": 2207.088, "full_drc_regions": 0,
        "independent_lvs_and_five_negatives_required": True,
        "unchanged_27_devices_15_ports_junctions_bulk_types_w_l": True,
        "extract_after_structural_gates": True,
    },
    "comparison_frozen_before_any_new_spice": comparison,
    "qualification": "Archived RC-deck outcomes; model physical fidelity not yet qualified",
    "publication": "PRIVATE_ONLY; no commit/push/PR edit or45PVT expansion authorized",
}
contract.write_json(out / "protocol.json", frozen)
contract.write_json(out / "source-tool-pins.json", {
    "tool_pins": pins, "r1_manifest_sha256": contract.sha256(r1 / "artifact-sha256.json"),
    "new_generator_sha256": contract.sha256(Path(__file__)),
    "public_source_sha256": {name: contract.sha256(entry / name) for name in (
        "layout_nominal27/layout.py", "layout_nominal27/layout.tcl",
        "layout_nominal27/contract.py", "layout_nominal27/analyze.py",
        "layout_preflight/preflight.py", "layout_preflight/strict_setup.tcl",
        "layout_preflight/lvs.tcl", "results/study/selected_circuit.spice",
        "layout_compact_repair/evidence/attempt1/atlas.mag",
    )},
    "control_reused_not_rerun": {name: contract.sha256(r1 / "control" / name)
                               for name in ("atlas.mag", "atlas.gds", "atlas.lvs.spice",
                                            "atlas.c.spice", "atlas.rc.spice")},
})
shutil.copyfile(Path(__file__), out / "area_single_row.py")
shutil.copyfile(r1 / "area-layout.tcl", out / "area-layout.tcl")
placement = native.assemble(out)
routing = native.make_routes(out, placement)
assert all(placement[name]["origin_um"][1] == 0 for name in placement)
for name, placed in placement.items():
    baseline = json.loads((r1 / "control/placement.json").read_text())[name]
    assert placed["reflect_x"] == baseline["reflect_x"]
    for pin in ("D", "G", "S", "B"):
        assert math.isclose(placed["pins_um"][pin][1], baseline["pins_um"][pin][1])
        assert (placed["pins_grid"][pin][0] - round(placed["origin_um"][0] / .005)
                == baseline["pins_grid"][pin][0] - round(baseline["origin_um"][0] / .005))
old_routes = {(r["device"], r["terminal"]): r for r in control_routing["terminal_routes"]}
for route in routing["terminal_routes"]:
    old = old_routes[route["device"], route["terminal"]]
    assert all(math.isclose(route[key], old[key], abs_tol=1e-9) for key in (
        "metal1_centerline_um", "metal2_centerline_um", "metal2_series_path_um",
        "metal2_attached_stub_um", "metal2_bottom_y_um", "metal2_top_y_um"))
request = out / "route-request.tcl"
bridges = []
with request.open("a") as handle:
    for name in ("Xrxp", "Xrxn", "Xrqp", "Xrqn"):
        route = next(r for r in routing["terminal_routes"]
                     if r["device"] == name and r["terminal"] == "B")
        x = route["via1_um"][0]
        assert route["net"] == "vdd" and route["via1_um"][1] == -1.155
        rectangle = [x - .18, -1.8, x + .18, -.955]
        bridges.append({"device": name, "net": "vdd", "rect_um": rectangle})
        handle.write("box_um " + " ".join(f"{v:.6f}" for v in rectangle) + "\npaint metal2\n")
contract.write_json(out / "retained-body-pad-bridges.json", bridges)
contract.write_json(out / "pre-execution-geometry-delta.json", {
    "placement": placement, "all_local_escape_lengths_and_y_coordinates_equal_control": True,
    "route_request_sha256": contract.sha256(request), "protocol_sha256": contract.sha256(out / "protocol.json"),
    "old_bus_lengths_um": {n: r["metal3_centerline_um"] for n, r in control_routing["buses"].items()},
    "new_bus_lengths_um": {n: r["metal3_centerline_um"] for n, r in routing["buses"].items()},
})


def magic(mode):
    env = dict(os.environ, NOMINAL27_MODE=mode, NOMINAL27_REQUEST=str(request))
    text = native.run_logged(
        [str(tools / "install/bin/magic"), "-dnull", "-noconsole", "-rcfile",
         str(tools / "src/open_pdks/sky130/sky130A/libs.tech/magic/sky130A.magicrc")],
        out / "logs" / (mode + "-magic.log"), out, env,
        input_text=f"source {{{out / 'area-layout.tcl'}}}\n",
    )
    assert f"NOMINAL27_MAGIC_COMPLETE {mode}" in text


def junction_signature(path):
    result = []
    for card in analyze.device_cards(path).values():
        words = card.split()
        props = dict(re.findall(r"(\w+)=([^\s]+)", card))
        result.append((words[5], words[2], words[4], float(props["w"]), float(props["l"]),
                       tuple(sorted(((words[1], float(props["ad"]), float(props["pd"])),
                                     (words[3], float(props["as"]), float(props["ps"])))))))
    return Counter(result)


checks = []


def check(label, operation):
    try:
        row = {"check": label, "status": "PASS", "detail": operation()}
    except (AssertionError, ValueError, OSError, RuntimeError) as error:
        row = {"check": label, "status": "FAIL", "error": str(error),
               "traceback": traceback.format_exc()}
    checks.append(row)
    contract.write_json(out / "checks.json", checks)
    print(row["status"] + ": " + label + (": " + row["error"] if row["status"] == "FAIL" else ""), flush=True)
    return row["status"] == "PASS"


def smaller():
    bounds = contract.gds_bounds(out / "atlas.gds")
    assert bounds["bbox_area_um2"] < 2207.088
    return {"material_bbox": bounds, "unchanged_y_placement_and_local_routes": True}


def junctions():
    assert junction_signature(out / "atlas.lvs.spice") == junction_signature(r1 / "control/atlas.lvs.spice")
    return {"all_27_native_junction_geometries_equal_control": True}


qualified = False
try:
    magic("route")
    check("single-row smaller material bbox", smaller)
    if not check("full named-style DRC", lambda: native.drc(out, "atlas")):
        sys.exit(1)
    structural = check("spacing negative", lambda: native.drc(out, "nominal27_spacing_bad", negative=True))
    structural = check("real layers and connected gate landings", lambda: native.geometry(out, placement)) and structural
    structural = check("native 27MOS 15ports body/connectivity", lambda: native.native_interface(out)) and structural
    structural = check("independent positive LVS", lambda: native.lvs(out)) and structural
    for mutation in ("connection", "bulk", "width", "flavor"):
        structural = check("LVS negative " + mutation, lambda m=mutation: native.lvs(out, m)) and structural
    structural = check("actual junction parameters equal control", junctions) and structural
    if not structural or not all(row["status"] == "PASS" for row in checks):
        sys.exit(1)
    magic("extract")
    for mode in ("c", "rc"):
        check("fresh " + mode + " extraction/DC anchors/passives", lambda m=mode: native.extraction(out, m))
    check("native junction/passive/material audit", lambda: analyze.analyze(out))
    qualified = len(checks) == 14 and all(row["status"] == "PASS" for row in checks)
    sys.exit(0 if qualified else 1)
finally:
    contract.write_json(out / "structural-receipt.json", {
        "qualified": qualified, "checks": checks, "new_spice_runs": 0,
        "native_drc_attempts": 1, "control_proof_reused_not_rerun": True,
        "qualification": frozen["qualification"],
    })
    native.manifest(out)

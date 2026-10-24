"""Fixed b1 private adapter, complete recorded-mask/route preflight, native gates."""
import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import traceback

parser = argparse.ArgumentParser()
parser.add_argument("--entry", type=Path, required=True)
parser.add_argument("--private", type=Path, required=True)
parser.add_argument("--phase", choices=("preflight", "native", "verify-tools"), required=True)
args = parser.parse_args()
ENTRY = args.entry.resolve()
PRIVATE = args.private.resolve()
ROUND = PRIVATE / "local-pitch-20261003-b1"
OUT = Path("/home/a-vivianhsu/atlas-local-pitch-20261003-b1")
TOOLS = Path("/home/a-vivianhsu/atlas-parasitic-check-5fa3/tool-work")
BASE = ENTRY / "layout_single_row/v1/native-a1"
CONTROL = ENTRY / "layout_single_row/v1/native/candidate"
plan = json.loads((ROUND / "authorized-plan.json").read_bytes())
assert hashlib.sha256((ROUND / "authorized-plan.json").read_bytes()).hexdigest() == (
    "f5fda331cff71e78d09860247420b562d613515ff928a463a3d8aae164e1d87d")
sys.path.insert(0, str(ENTRY / "layout_nominal27"))
import contract
import layout as native
import analyze


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    contract.write_json(OUT / name, value)


def verify_tools():
    pins = json.loads((BASE / "source-tool-pins.json").read_bytes())["tool_pins"]
    assert len(pins) == 7 and all(sha(TOOLS / n) == h for n, h in pins.items())
    git = {}
    for name, expected in (
        ("magic", "4f53bb3091d1e4a9b2009a58f157a8a4331d4c84"),
        ("netgen", "e1528a797cdb155d6ebf8d91c5a55ed7d1713156"),
        ("open_pdks", "aa3fc215a80d32437b8cca1cb3fdee819d18c4c9"),
    ):
        git[name] = subprocess.check_output(
            ["git", "-C", str(TOOLS / "src" / name), "rev-parse", "HEAD"], text=True).strip()
        assert git[name] == expected
    pdk = TOOLS / "src/open_pdks/sky130/sky130A/libs.tech/magic"
    tcl = pdk / "sky130A.tcl"
    tech = (pdk / "sky130A.tech").read_text()
    for token in (
        'spacing allnwell allnwell 1270 touching_ok',
        'spacing allm1,m1fill allm1,*obsm1,m1fill 140 touching_ok',
        'spacing allm2  allm2,obsm2,m2fill 140 touching_ok',
        'spacing allm3 allm3,obsm3,m3fill  300 touching_ok',
    ):
        assert token in tech, token
    assert 'proc sky130::via1_draw' in tcl.read_text()
    return {"seven_tool_hashes": pins, "source_git_pins": git,
            "actual_via_script_sha256": sha(tcl),
            "native_tools_reused_not_installed": True}


tools = verify_tools()
if args.phase == "verify-tools":
    print(json.dumps(tools, indent=2))
    sys.exit(0)
os.environ["PATH"] = str(TOOLS / "install/bin") + os.pathsep + os.environ["PATH"]
os.environ["PDK_ROOT"] = str(TOOLS / "src/open_pdks/sky130")
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
contract.audit_source()
assert sha(CONTROL / "atlas.gds") == plan["baseline"]["GDS_sha256"]
assert sha(CONTROL / "atlas.mag") == plan["baseline"]["MAG_sha256"]
original = copy.deepcopy(contract.PROTOCOL)
layout = contract.PROTOCOL["layout"]
layout.update(copy.deepcopy(json.loads((BASE / "protocol.json").read_bytes())["layout"]))
layout["revision"] = {"name": plan["candidate_id"], "authority": "authorized-plan.json"}
layout.pop("placement_pitch_um")
geometry = plan["one_candidate_geometry"]
assert layout["mirror_pairs"] == geometry["mirror_pair_order"]
radii = geometry["positive_pair_radius_grid"]
assert radii == [760, 1520, 2280, 3040, 3800, 4640, 5480, 6320, 7160, 8000, 8840, 9680, 10520]
rules = layout["routing"]
rules["balanced_outputs"]["bus_half_span_um"] = 20.4
rules["ground_shields"].update(left_um=-21.4, right_um=21.4, metal4_spine_x_um=[-21., 21.])
rules["description"] = "Fixed authorized local pitch map; original local routes and tracks; endpoint updates only."


def fixed_placements():
    result = {"Xtail": {"origin_um": [0, 0], "reflect_x": 1}}
    for (left, right), radius in zip(layout["mirror_pairs"], radii):
        result[left] = {"origin_um": [-radius * .005, 0], "reflect_x": 1}
        result[right] = {"origin_um": [radius * .005, 0], "reflect_x": -1}
    assert len(result) == 27 and set(result) == {d["name"] for d in contract.DEVICES}
    return result


native.placements = fixed_placements


def grid(value):
    scaled = value / .005
    assert math.isclose(scaled, round(scaled), abs_tol=1e-8)
    return round(scaled)


def boxgrid(box):
    return [grid(v) for v in box]


def rectangle_gap(a, b):
    dx = max(a[0]-b[2], b[0]-a[2], 0)
    dy = max(a[1]-b[3], b[1]-a[3], 0)
    return math.hypot(dx, dy)


def route_shapes(request, placement):
    """Expand the read, pinned via helpers' exact rectangles, without tool execution."""
    shapes = []
    box = None
    terminal_index = 0
    terminal_names = [d["name"] for d in contract.DEVICES for _ in range(4)]
    via_layers = {
        "via1": (("via1", [0, 0, 0, 0]), ("metal2", [0, -10, 0, 10]),
                 ("metal1", [-10, 0, 10, 0])),
        "via2": (("via2", [0, 0, 0, 0]), ("metal2", [0, -10, 0, 10]),
                 ("metal3", [-10, -5, 10, 5])),
        "via3": (("via3", [0, 0, 0, 0]), ("metal4", [-1, -1, 1, 1]),
                 ("metal3", [-10, 0, 10, 0])),
        "mcon": (("viali", [0, 0, 0, 0]), ("metal1", [-12, -6, 12, 6])),
    }
    for line in request.read_text().splitlines():
        words = line.split()
        if not words:
            continue
        if words[0] == "box_um":
            box = boxgrid(list(map(float, words[1:])))
        elif words[0] == "paint":
            shapes.append({"layer": words[1], "rect_grid": box[:], "source": line,
                           "device": terminal_names[terminal_index] if terminal_index < 108 else None})
        elif words[0].startswith("sky130::"):
            name = words[0][8:].removesuffix("_draw")
            assert name in via_layers
            for layer, expansion in via_layers[name]:
                shapes.append({"layer": layer, "rect_grid": [v+e for v, e in zip(box, expansion)],
                               "source": line,
                               "device": terminal_names[terminal_index] if terminal_index < 108 else None})
            if name == "via2":
                terminal_index += 1
        else:
            assert words[0] in ("label", "port"), line
    return shapes


if args.phase == "preflight":
    assert not OUT.exists()
    assert shutil.disk_usage(OUT.parent).free > 2 * 1024**3
    OUT.mkdir()
    (OUT / "logs").mkdir()
    checks = []
    try:
        for d in contract.DEVICES:
            name = f"pcell_{d['name'].lower()}.mag"
            shutil.copyfile(BASE / name, OUT / name)
        for name in ("pcells.tsv", "area-layout.tcl"):
            shutil.copyfile(BASE / name, OUT / name)
        shutil.copyfile(ROUND / "authorized-plan.json", OUT / "authorized-plan.json")
        shutil.copyfile(Path(__file__), OUT / "local_pitch_native.py")
        placement = native.assemble(OUT)
        routing = native.make_routes(OUT, placement)
        old_place = json.loads((BASE / "placement.json").read_bytes())
        old_route = json.loads((BASE / "routing.json").read_bytes())
        for name, p in placement.items():
            old = old_place[name]
            assert p["reflect_x"] == old["reflect_x"]
            assert p["pcell_sha256"] == old["pcell_sha256"]
            assert p["origin_um"][1] == old["origin_um"][1] == 0
            x, oldx = grid(p["origin_um"][0]), grid(old["origin_um"][0])
            for pin in ("D", "G", "S", "B"):
                assert [p["pins_grid"][pin][i] - (x if i in (0, 2) else 0) for i in range(4)] == [
                    old["pins_grid"][pin][i] - (oldx if i in (0, 2) else 0) for i in range(4)]
        old_routes = {(r["device"], r["terminal"]): r for r in old_route["terminal_routes"]}
        lanes = set()
        for route in routing["terminal_routes"]:
            old = old_routes[route["device"], route["terminal"]]
            assert route["net"] == old["net"]
            for field in ("metal1_centerline_um", "metal2_centerline_um", "metal2_series_path_um",
                          "metal2_attached_stub_um", "metal2_bottom_y_um", "metal2_top_y_um"):
                assert grid(route[field]) == grid(old[field]), (route, field)
            name = route["device"]
            for field in ("contact_um", "via1_um", "via2_um"):
                newgrid, oldgrid = boxgrid(route[field]), boxgrid(old[field])
                assert newgrid[1] == oldgrid[1]
                assert newgrid[0]-grid(placement[name]["origin_um"][0]) == (
                    oldgrid[0]-grid(old_place[name]["origin_um"][0]))
            lanes.add(grid(route["via1_um"][0]))
        assert len(lanes) == len(routing["terminal_routes"]) == 108
        bridges = []
        with (OUT / "route-request.tcl").open("a") as handle:
            for name in ("Xrxp", "Xrxn", "Xrqp", "Xrqn"):
                route = old_routes[name, "B"]
                target = next(r for r in routing["terminal_routes"] if (r["device"], r["terminal"]) == (name, "B"))
                assert target["net"] == "vdd" and grid(target["via1_um"][1]) == -231
                x = target["via1_um"][0]
                box = [x-.18, -1.8, x+.18, -.955]
                old = next(b for b in json.loads((BASE / "retained-body-pad-bridges.json").read_bytes())
                           if b["device"] == name)
                assert [grid(v)-(grid(placement[name]["origin_um"][0]) if i in (0, 2) else 0)
                        for i, v in enumerate(box)] == [
                    grid(v)-(grid(old_place[name]["origin_um"][0]) if i in (0, 2) else 0)
                    for i, v in enumerate(old["rect_um"])]
                bridges.append({"device": name, "net": "vdd", "rect_um": box})
                handle.write("box_um " + " ".join(f"{v:.6f}" for v in box) + "\npaint metal2\n")
        save("retained-body-pad-bridges.json", bridges)
        assert routing["buses"]["qp"]["left_um"] == routing["buses"]["qn"]["left_um"] == -20.4
        assert routing["buses"]["qp"]["right_um"] == routing["buses"]["qn"]["right_um"] == 20.4
        assert rules["ground_shields"]["y_um"] == old_route["ground_shields"]["y_um"] == [1.6, 3.2, 4.8]
        for net, bus in routing["buses"].items():
            assert grid(bus["y_um"]) == grid(old_route["buses"][net]["y_um"])
            endpoints = [r["via2_um"][0] for r in routing["terminal_routes"] if r["net"] == net]
            if net not in ("qp", "qn"):
                assert grid(bus["left_um"]) == min(map(grid, endpoints))-80
                assert grid(bus["right_um"]) == max(map(grid, endpoints))+80
        save("relative-invariants.json", {"27_integer_grid_pin_contracts": True,
             "108_distinct_lanes": True, "all_local_route_lengths_y_widths_retained": True,
             "four_translated_full_pad_body_bridges": bridges, "all_ports_and_three_shields_retained": True})
        masks = {}
        for name, p in placement.items():
            parsed = contract.inspect_mag(OUT / f"pcell_{name.lower()}.mag")
            masks[name] = {layer: [native.transform_rect(r, p) for r in rects]
                           for layer, rects in parsed["rectangles"].items()
                           if layer not in ("checkpaint", "error_p")}
        layer_rows = []
        ordered = sorted(placement, key=lambda n: placement[n]["origin_um"][0])
        # Cross-device rules only: all copied inside-PCell shapes remain unchanged.
        rule_grid = {"nwell": 254, "pwell": 254, "poly": 42,
                     "metal1": 28, "locali": 34,
                     "ndiff": 54, "pdiff": 54, "ndiffc": 54, "pdiffc": 54,
                     "psubdiff": 54, "nsubdiff": 54, "psubdiffcont": 54, "nsubdiffcont": 54,
                     "viali": 34}
        intervals = []
        for left, right in zip(ordered, ordered[1:]):
            distance = grid(placement[right]["origin_um"][0])-grid(placement[left]["origin_um"][0])
            widths = []
            for name in (left, right):
                allwell = [r for layer, rs in masks[name].items() if layer in ("nwell", "pwell") for r in rs]
                width = (max(r[2] for r in allwell)-min(r[0] for r in allwell)) * .005
                assert math.isclose(width, 2.11) or math.isclose(width, 2.96), (name, width)
                widths.append(round(width, 2))
            assert widths != [2.96, 2.96], (left, right)
            expected = 840 if 2.96 in widths else 760
            assert distance == expected, (left, right, distance, expected)
            intervals.append({"left": left, "right": right, "distance_grid": distance, "well_widths_um": widths})
            for layer in set(masks[left]) & set(masks[right]):
                a, b = masks[left][layer], masks[right][layer]
                gap = min(rectangle_gap(x, y) for x in a for y in b)
                layer_rows.append({"left": left, "right": right, "layer": layer,
                                   "minimum_shape_distance_um": gap*.005,
                                   "recorded_conservative_rule_um": rule_grid.get(layer, 0)*.005})
                if layer in rule_grid:
                    assert gap >= rule_grid[layer]+40-1e-8, (left, right, layer, gap*.005)
        save("full-pcell-material-distances.json", layer_rows)
        shapes = route_shapes(OUT / "route-request.tcl", placement)
        save("complete-unexecuted-route-rectangles.json", shapes)
        # All changed M2 lanes: include native via2/via1 enclosure pads and body bridges.
        lane_shapes = defaultdict(list)
        for s in shapes:
            if s["layer"] == "metal2":
                rect = s["rect_grid"]
                center = (rect[0]+rect[2])/2
                assert center in lanes
                lane_shapes[center].append(rect)
        lane_rows = []
        for a, b in zip(sorted(lanes), sorted(lanes)[1:]):
            gap = min(rectangle_gap(x, y) for x in lane_shapes[a] for y in lane_shapes[b])
            lane_rows.append({"left_lane_grid": a, "right_lane_grid": b,
                              "shape_distance_um": gap*.005, "rule_um": .14,
                              "additional_margin_um": gap*.005-.14})
            assert gap >= 28+40-1e-8, (a, b, gap*.005)
        save("all-metal2-lane-pad-distances.json", lane_rows)
        # Cross-device M1/LI routes and complete underlying masks, not centerlines alone.
        cross_rows = []
        for layer, minimum in (("metal1", 28), ("locali", 34), ("viali", 34)):
            allshapes = []
            for name, layers in masks.items():
                allshapes.extend((name, r) for r in layers.get(layer, []))
            for s in shapes:
                if s["layer"] != layer:
                    continue
                rect = s["rect_grid"]
                name = s["device"]
                assert name in placement
                allshapes.append((name, rect))
            for left, right in zip(ordered, ordered[1:]):
                a = [r for n, r in allshapes if n == left]
                b = [r for n, r in allshapes if n == right]
                if not a or not b:
                    continue
                gap = min(rectangle_gap(x, y) for x in a for y in b)
                cross_rows.append({"left": left, "right": right, "layer": layer,
                                   "shape_distance_um": gap*.005, "rule_um": minimum*.005,
                                   "additional_margin_um": (gap-minimum)*.005})
                assert gap >= minimum+40-1e-8, (left, right, layer, gap*.005)
        save("all-local-metal1-li-pad-distances.json", cross_rows)
        # Inherited bus/shield vertical clearance is unchanged; not a claimed new 0.20um margin.
        save("inherited-global-tracks.json", {
            "bus_width_um": .34, "minimum_parallel_y_um": .8,
            "inherited_m3_strip_gap_um": .46, "rule_um": .30, "inherited_rule_margin_um": .16,
            "unchanged_in_this_trial": True,
            "planning_0_20_safety_applies_to_new_local_intervals_not_unmodified_bus_tracks": True,
            "spines": rules["ground_shields"]["metal4_spine_x_um"],
            "three_shield_rows": rules["ground_shields"]["y_um"],
            "all8_via3_contacts_preserved": sum(s["layer"] == "via3" for s in shapes) == 8})
        save("static-preflight.json", {"status": "passed", "intervals": intervals,
             "all_pcell_mask_layers_audited": sorted({l for layers in masks.values() for l in layers}),
             "changed_local_spacing_safety_um": .20, "complete_route_rectangles": len(shapes),
             "all_shield_spines_inside_vss_and_shield": True, "no_native_tool_run": True,
             "new_candidate_area": None, "area_projection_not_measurement": True})
        protocol = {"candidate": plan["candidate_id"], "authorized_plan_sha256": sha(OUT / "authorized-plan.json"),
                    "layout": layout, "fixed_geometry": geometry,
                    "comparison_frozen_before_any_new_spice": plan["limited_matched_simulation"],
                    "physical_acceptance": plan["area_objective"],
                    "maximum_native_drc_attempts": 2, "control_proof_reused_not_rerun": True,
                    "baseline": plan["baseline"], "qualification": plan["end_of_round"]["mandatory_caveat"],
                    "publication": "PRIVATE_ONLY_NOT_ADOPTED"}
        save("protocol.json", protocol)
        save("pre-execution-geometry-delta.json", {
            "control_placement_sha256": sha(BASE / "placement.json"),
            "new_placement": placement,
            "old_bus_lengths_um": {n: b["metal3_centerline_um"] for n, b in old_route["buses"].items()},
            "new_bus_lengths_um": {n: b["metal3_centerline_um"] for n, b in routing["buses"].items()},
            "centerlines_not_extracted_resistance": True, "relative_integer_grid_contracts_pass": True})
        sources = {p.relative_to(ENTRY).as_posix(): sha(p) for folder in
                   (ENTRY / "layout_nominal27", ENTRY / "layout_preflight")
                   for p in folder.iterdir() if p.is_file()}
        freeze = {"authorized_plan_sha256": sha(OUT / "authorized-plan.json"), "tools": tools,
                  "adapter_sha256": sha(Path(__file__)), "public_source_sha256": sources,
                  "control_reused_not_rerun": {p.name: sha(p) for p in CONTROL.iterdir() if p.is_file()},
                  "pre_native_files": {p.relative_to(OUT).as_posix(): sha(p) for p in OUT.rglob("*") if p.is_file()}}
        save("source-freeze.json", freeze)
        print("PASS fixed b1 static preflight/source freeze; actual candidate DRC attempts0/SPICE0", flush=True)
    except Exception as error:
        save("static-preflight-failure.json", {"status": "failed", "error": str(error),
              "traceback": traceback.format_exc(), "native_drc_attempts": 0, "new_transients": 0,
              "stop_no_pitch_retuning": True})
        raise
    finally:
        native.manifest(OUT)
elif args.phase == "native":
    freeze = json.loads((OUT / "source-freeze.json").read_bytes())
    assert all(sha(OUT / n) == h for n, h in freeze["pre_native_files"].items())
    assert freeze["adapter_sha256"] == sha(Path(__file__))
    assert freeze["tools"] == tools
    assert all(sha(ENTRY / n) == h for n, h in freeze["public_source_sha256"].items())
    assert not (OUT / "structural-receipt.json").exists()
    checks = []
    attempts = 0
    qualified = False

    def check(name, operation):
        try:
            detail = operation()
            row = {"check": name, "status": "PASS", "detail": detail}
        except Exception as error:
            row = {"check": name, "status": "FAIL", "error": str(error), "traceback": traceback.format_exc()}
        checks.append(row)
        save("checks.json", checks)
        print(row["status"], name, flush=True)
        return row["status"] == "PASS"

    def magic(mode):
        env = dict(os.environ, NOMINAL27_MODE=mode, NOMINAL27_REQUEST=str(OUT / "route-request.tcl"))
        text = native.run_logged([str(TOOLS / "install/bin/magic"), "-dnull", "-noconsole", "-rcfile",
            str(TOOLS / "src/open_pdks/sky130/sky130A/libs.tech/magic/sky130A.magicrc")],
            OUT / "logs" / f"{mode}-magic.log", OUT, env,
            input_text=f"source {{{OUT / 'area-layout.tcl'}}}\n")
        assert f"NOMINAL27_MAGIC_COMPLETE {mode}" in text

    def area():
        bounds = contract.gds_bounds(OUT / "atlas.gds")
        assert bounds["bbox_area_um2"] <= 1970.5413, bounds
        return {"actual_material_bbox": bounds, "baseline_um2": 2074.254,
                "incremental_reduction_percent": 100*(1-bounds["bbox_area_um2"]/2074.254)}

    def signature(path):
        result = []
        for card in analyze.device_cards(path).values():
            words = card.split()
            props = dict(re.findall(r"(\w+)=([^\s]+)", card))
            result.append((words[5], words[2], words[4], float(props["w"]), float(props["l"]),
                           tuple(sorted(((words[1], float(props["ad"]), float(props["pd"])),
                                         (words[3], float(props["as"]), float(props["ps"])))))))
        return Counter(result)

    def junctions():
        assert signature(OUT / "atlas.lvs.spice") == signature(CONTROL / "atlas.lvs.spice")
        return {"all27_equal_adopted_a1": True}

    try:
        attempts = 1
        save("actual-native-invocation.json", {"candidate_full_drc_attempt": 1,
             "fixed_source_freeze_sha256": sha(OUT / "source-freeze.json")})
        magic("route")
        if not check("actual all-material area <=1970.5413", area):
            sys.exit(1)
        if not check("full named-style DRC zero regions", lambda: native.drc(OUT, "atlas")):
            sys.exit(1)
        operations = [
            ("real spacing negative", lambda: native.drc(OUT, "nominal27_spacing_bad", negative=True)),
            ("actual layers and gate landings", lambda: native.geometry(OUT, json.loads((OUT / "placement.json").read_bytes()))),
            ("native27MOS15orderedports body connectivity", lambda: native.native_interface(OUT)),
            ("independent positive Netgen LVS", lambda: native.lvs(OUT)),
        ]
        operations += [(f"LVS {mutation} negative", lambda m=mutation: native.lvs(OUT, m))
                       for mutation in ("connection", "bulk", "width", "flavor")]
        operations += [("27 native junctions equal adopted baseline", junctions)]
        for name, operation in operations:
            if not check(name, operation):
                sys.exit(1)
        magic("extract")
        for mode in ("c", "rc"):
            if not check(f"fresh {mode} genuine scaling/DC/passives", lambda m=mode: native.extraction(OUT, m)):
                sys.exit(1)
        if not check("native junction/passive/material audit", lambda: analyze.analyze(OUT)):
            sys.exit(1)
        qualified = len(checks) == 14 and all(r["status"] == "PASS" for r in checks)
        assert qualified
    finally:
        save("structural-receipt.json", {"qualified": qualified, "checks": checks,
             "native_drc_attempts": attempts, "optional_second_attempt_not_used": True,
             "control_proof_reused_not_rerun": True, "new_spice_runs": 0,
             "tools_after": verify_tools(),
             "qualification": plan["end_of_round"]["mandatory_caveat"]})
        native.manifest(OUT)

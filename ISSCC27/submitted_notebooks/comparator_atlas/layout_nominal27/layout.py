"""Generate and inspect the real nominal 27-device Magic/Netgen experiment."""

from __future__ import annotations

from collections import defaultdict
import csv
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import traceback

from contract import (
    DEVICES, HERE, NETS, PORTS, PREFLIGHT, PROTOCOL, audit_source, check_netlist,
    gds_bounds, independent_reference, inspect_gds, inspect_mag, passive_metrics,
    read_spice, require, sha256, write_json,
)
from preflight import lvs_outcome, metal1_area_at_pin_um2

GRID_UM = 0.005


def gate_m1_area_um2(mag: dict, pin: str) -> float:
    # The pinned technology gives via1 metal1/metal2 residues. The frozen
    # primitive helper already includes viali, but routed cells also need via1.
    rectangles = mag["rectangles"]
    with_residue = {
        **mag, "rectangles": {
            **rectangles,
            "metal1": rectangles.get("metal1", []) + rectangles.get("via1", []),
        },
    }
    return metal1_area_at_pin_um2(with_residue, pin, GRID_UM)


def run_logged(command: list[str], path: Path, out: Path, env: dict,
               input_text: str | None = None) -> str:
    with path.open("w", encoding="utf-8") as handle:
        handle.write("COMMAND: " + " ".join(command) + "\n")
        handle.flush()
        try:
            result = subprocess.run(command, cwd=out, env=env, input=input_text,
                                    text=True, stdout=handle, stderr=subprocess.STDOUT,
                                    timeout=300)
        except subprocess.TimeoutExpired:
            handle.write("\nNOMINAL27_TOOL_TIMEOUT: exceeded 300 seconds\n")
            raise
    text = path.read_text(encoding="utf-8", errors="replace")
    require(result.returncode == 0, f"Tool failed with exit {result.returncode}; see {path}")
    require(not re.search(r"(?:NOMINAL27|PREFLIGHT)_\w*ERROR|command ignored|Error reading",
                          text, re.I), f"Tool reported an execution error; see {path}")
    return text


def placements() -> dict:
    pitch = PROTOCOL["layout"]["placement_pitch_um"]
    result = {"Xtail": {"origin_um": [0, 0], "reflect_x": 1}}
    for i, (left, right) in enumerate(PROTOCOL["layout"]["mirror_pairs"], 1):
        result[left] = {"origin_um": [-i*pitch, 0], "reflect_x": 1}
        result[right] = {"origin_um": [i*pitch, 0], "reflect_x": -1}
    require(set(result) == {d["name"] for d in DEVICES}, "Incomplete placement contract")
    return result


def transform_rect(rect: list[int], placement: dict) -> list[int]:
    ox, oy = (round(x / GRID_UM) for x in placement["origin_um"])
    sign = placement["reflect_x"]
    x1, y1, x2, y2 = rect
    return [min(sign*x1, sign*x2)+ox, y1+oy, max(sign*x1, sign*x2)+ox, y2+oy]


def make_pcells_request(out: Path) -> Path:
    path = out / "pcell-request.tcl"
    lines = ["set device_specs {"]
    for d in DEVICES:
        lines.append(f'    {{pcell_{d["name"].lower()} {d["model"]} {d["w_um"]} {d["l_um"]}}}')
    path.write_text("\n".join([*lines, "}", ""]))
    return path


def magic(out: Path, mode: str, request: Path) -> None:
    env = dict(os.environ, NOMINAL27_MODE=mode, NOMINAL27_REQUEST=str(request))
    rcfile = Path(env["PDK_ROOT"]) / "sky130A" / "libs.tech" / "magic" / "sky130A.magicrc"
    log = run_logged(["magic", "-dnull", "-noconsole", "-rcfile", str(rcfile)],
                     out / "logs" / f"{mode}-magic.log", out, env,
                     input_text=f"source {{{HERE / 'layout.tcl'}}}\n")
    require(f"NOMINAL27_MAGIC_COMPLETE {mode}" in log, f"Magic {mode} did not complete")
    require("deprecated" not in log.lower() and "ambiguous" not in log.lower(),
            "Magic command contract contains an ambiguous/deprecated command")


def assemble(out: Path) -> dict:
    placement = placements()
    native = defaultdict(list)
    with (out / "pcells.tsv").open() as handle:
        reports = list(csv.DictReader(handle, delimiter="\t"))
    require(len(reports) == 27, "Not all 27 real PCells were generated")
    for d, row in zip(DEVICES, reports):
        name = d["name"]
        require(row["cell"] == f"pcell_{name.lower()}" and row["model"] == d["model"],
                "PCell generator identity differs from the independent table")
        require(float(row["w_um"]) == d["w_um"] and float(row["l_um"]) == d["l_um"]
                and row["nf"] == row["m"] == "1", f"PCell geometry was clamped: {name}")
        require(math.isclose(float(row["grid_um"]), GRID_UM, abs_tol=1e-8),
                "Unexpected Magic geometry scale")
        path = out / (row["cell"] + ".mag")
        text = path.read_text()
        require("\nmagscale 1 2\n" in text and not re.search(r"^(use|tri) ", text, re.M),
                "PCell is not supported flat native rectangle geometry")
        parsed = inspect_mag(path)
        require(set(parsed["labels"]) == {"D", "G", "S", "B"}, "Incomplete real PCell terminals")
        require(not set(parsed["rectangles"]).intersection(
            {"metal2", "via1", "via2", "metal3", "via3", "metal4"}),
            "Over-device routing requires the verified M1-only native PCells")
        area = gate_m1_area_um2(parsed, "G")
        require(area >= PROTOCOL["layout"]["minimum_connected_gate_m1_area_um2"],
                f"Insufficient connected gate M1 area: {name}: {area}")
        placed = placement[name]
        placed["pcell_sha256"] = sha256(path)
        placed["pcell_gate_m1_area_um2"] = area
        placed["pins_grid"] = {
            pin: transform_rect(box, placed) for pin, box in parsed["label_positions"].items()
        }
        placed["pins_um"] = {
            pin: [(b[0]+b[2])*GRID_UM/2, (b[1]+b[3])*GRID_UM/2]
            for pin, b in placed["pins_grid"].items()
        }
        for layer, rectangles in parsed["rectangles"].items():
            native[layer].extend(transform_rect(rect, placed) for rect in rectangles)
    lines = ["magic", "tech sky130A", "magscale 1 2", "timestamp 0"]
    for layer, rectangles in sorted(native.items()):
        lines.append(f"<< {layer} >>")
        lines.extend("rect " + " ".join(map(str, rect)) for rect in rectangles)
    lines.extend(["<< end >>", ""])
    (out / "atlas.mag").write_text("\n".join(lines))
    write_json(out / "placement.json", placement)
    return placement


def make_routes(out: Path, placement: dict) -> dict:
    rules = PROTOCOL["layout"]["routing"]
    buses = rules["bus_y_um"]
    require(set(buses) == set(NETS), "Incomplete declared physical bus plan")
    balanced = rules["balanced_outputs"]
    lines, endpoints, routes = [], defaultdict(list), []
    occupied_lanes = {}

    def box(x1: float, y1: float, x2: float, y2: float) -> None:
        require(x2 >= x1 and y2 >= y1, "Inverted physical routing rectangle")
        lines.append("box_um " + " ".join(f"{v:.6f}" for v in (x1, y1, x2, y2)))

    def paint(layer: str, x1: float, y1: float, x2: float, y2: float) -> None:
        box(x1, y1, x2, y2)
        lines.append(f"paint {layer}")

    for device in DEVICES:
        placed = placement[device["name"]]
        ox = placed["origin_um"][0]
        sign = placed["reflect_x"]
        for pin, net in zip(("D", "G", "S", "B"), device["nodes"]):
            x, y = placed["pins_um"][pin]
            lane = ox + sign*{"D": -1.0, "G": 0.0, "S": 1.0, "B": -2.0}[pin]
            require(round(lane, 6) not in occupied_lanes, "Two terminals share a vertical M2 lane")
            occupied_lanes[round(lane, 6)] = (device["name"], pin)
            via_y = y + 0.20 if pin == "G" else y
            if pin == "B":
                paint("locali", x-0.15, y-0.15, x+0.15, y+0.15)
                box(x-0.085, y-0.085, x+0.085, y+0.085)
                lines.append("sky130::mcon_draw")
            half = rules["metal1_escape_width_um"]/2
            if pin == "G":
                paint("metal1", x-0.15, y-0.10, x+0.15, via_y+half)
            elif pin in ("D", "S"):
                # Escape outward without widening the contact toward the opposite diffusion.
                left, right = (lane-half, x+0.10) if lane < x else (x-0.10, lane+half)
                paint("metal1", left, y-half, right, y+half)
            else:
                paint("metal1", min(x, lane)-half, y-half, max(x, lane)+half, y+half)
            box(lane-0.13, via_y-0.13, lane+0.13, via_y+0.13)
            lines.append("sky130::via1_draw")
            half = rules["metal2_width_um"]/2
            top = balanced["metal2_top_y_um"] if net in balanced["nets"] else buses[net]
            if net in balanced["nets"]:
                require(top >= max(buses[net], via_y), "Output balancing misses its terminal/bus")
            low, high = min(via_y, buses[net], top), max(via_y, buses[net], top)
            series = abs(buses[net]-via_y)
            paint("metal2", lane-half, low-half, lane+half, high+half)
            box(lane-0.14, buses[net]-0.14, lane+0.14, buses[net]+0.14)
            lines.append("sky130::via2_draw")
            endpoints[net].append(lane)
            routes.append({"device": device["name"], "terminal": pin, "net": net,
                           "contact_um": [x, y], "via1_um": [lane, via_y],
                           "via2_um": [lane, buses[net]],
                           "metal1_centerline_um": abs(lane-x)+abs(via_y-y),
                           "metal2_centerline_um": high-low,
                           "metal2_series_path_um": series,
                           "metal2_attached_stub_um": high-low-series,
                           "metal2_bottom_y_um": low, "metal2_top_y_um": high})
    require(set(endpoints) == set(NETS), "Unrouted circuit net")
    bus_report = {}
    for net in NETS:
        y = buses[net]
        left, right = min(endpoints[net])-0.4, max(endpoints[net])+0.4
        if net in balanced["nets"]:
            span = balanced["bus_half_span_um"]
            require(left >= -span and right <= span, "Output bus extension misses an endpoint")
            left, right = -span, span
        for other, previous in bus_report.items():
            if y == previous["y_um"]:
                gap = max(left-previous["right_um"], previous["left_um"]-right)
                require(gap >= 0.30, f"Same-track nets touch or violate spacing: {net}/{other}")
        half = rules["metal3_width_um"]/2
        paint("metal3", left, y-half, right, y+half)
        center = round((left+right)/2/GRID_UM)*GRID_UM
        box(center, y, center, y)
        lines.append(f"label {net} c metal3")
        if net in PORTS:
            lines.append(f"port make {PORTS.index(net)+1}")
        bus_report[net] = {"left_um": left, "right_um": right, "y_um": y,
                           "metal3_centerline_um": right-left, "label_um": [center, y]}
    shields = rules["ground_shields"]
    require(shields["net"] == "vss" and shields["via3_box_um"] >= 0.32,
            "Shield contact differs from the real grounded via3 contract")
    shield_rows = shields["y_um"]
    for y in shield_rows:
        half = rules["metal3_width_um"]/2
        paint("metal3", shields["left_um"], y-half, shields["right_um"], y+half)
    for x in shields["metal4_spine_x_um"]:
        require(bus_report["vss"]["left_um"] < x < bus_report["vss"]["right_um"]
                and shields["left_um"] < x < shields["right_um"],
                "Ground shield spine is not over the connected VSS metal")
        half = shields["metal4_width_um"]/2
        paint("metal4", x-half, buses["vss"]-half, x+half, max(shield_rows)+half)
        for y in [buses["vss"], *shield_rows]:
            half = shields["via3_box_um"]/2
            box(x-half, y-half, x+half, y+half)
            lines.append("sky130::via3_draw")
    path = out / "route-request.tcl"
    path.write_text("\n".join([*lines, ""]))
    pairs = []
    for left, right in PROTOCOL["layout"]["mirror_pairs"]:
        totals = {}
        series = {}
        for name in (left, right):
            totals[name] = sum(r["metal1_centerline_um"] + r["metal2_centerline_um"]
                               for r in routes if r["device"] == name)
            series[name] = sum(r["metal1_centerline_um"] + r["metal2_series_path_um"]
                               for r in routes if r["device"] == name)
        pairs.append({"left": left, "right": right, "escape_lengths_um": totals,
                      "right_minus_left_um": totals[right]-totals[left],
                      "series_escape_lengths_um": series,
                      "series_right_minus_left_um": series[right]-series[left]})
    report = {"revision": PROTOCOL["layout"]["revision"]["name"],
              "method": rules["description"], "terminal_routes": routes,
              "buses": bus_report, "paired_escape_asymmetry": pairs,
              "ground_shields": shields,
              "output_balancing": balanced,
              "lengths_are_geometric_centerlines_not_extracted_effective_R": True}
    write_json(out / "routing.json", report)
    return report


def drc(out: Path, cell: str, *, negative: bool = False) -> dict:
    text = (out / f"{cell}.drc.txt").read_text()
    require("technology: sky130A\n" in text and "drc_style: drc(full)\n" in text,
            "DRC technology/style missing from raw report")
    log = (out / "logs" / "route-magic.log").read_text()
    require(f"NOMINAL27_DRC_STYLE {cell} drc(full)" in log, "Missing active-style tool evidence")
    count = int(re.search(r"^count: (\d+)$", text, re.M)[1])
    if negative:
        require(count > 0 and "met1.2" in text, "Spacing negative control was not detected")
    else:
        require(count == 0, f"Real {cell} DRC reports {count} error regions: {text}")
    return {"technology": "sky130A", "style": "drc(full)", "error_regions": count,
            "report_sha256": sha256(out / f"{cell}.drc.txt"), "negative": negative}


def geometry(out: Path, placement: dict) -> dict:
    mag = inspect_mag(out / "atlas.mag")
    gds = inspect_gds(out / "atlas.gds")
    require(set(mag["labels"]) == set(NETS), "Top labels differ from actual routed net contract")
    for layer in ("65/20", "66/20", "68/20", "69/20", "70/20", "71/20", "70/44",
                  "125/44", "64/20"):
        require(gds["geometry_by_layer"].get(layer, 0) > 0, f"Missing nonempty GDS layer {layer}")
    areas = {}
    for name, placed in placement.items():
        label = f"{name}.gate_measurement"
        mag["label_positions"][label] = placed["pins_grid"]["G"]
        areas[name] = gate_m1_area_um2(mag, label)
        require(areas[name] >= PROTOCOL["layout"]["minimum_connected_gate_m1_area_um2"],
                f"Gate landing lost actual connected area: {name}: {areas[name]}")
    return {"gds": gds, "physical_bbox": gds_bounds(out / "atlas.gds"),
            "metal1_residue_layers": ["metal1", "viali", "via1"],
            "gate_m1_connected_areas_um2": areas, "mag_sha256": sha256(out / "atlas.mag"),
            "gds_sha256": sha256(out / "atlas.gds")}


def native_interface(out: Path) -> dict:
    ports = re.findall(r'^port "([^"]+)" (\d+) ', (out / "atlas.ext").read_text(), re.M)
    ordered = sorted(ports, key=lambda item: int(item[1]))
    require(ordered == [(name, str(i)) for i, name in enumerate(PORTS, 1)],
            f"Actual extraction did not preserve the native 15-port contract: {ordered}")
    net = read_spice(out / "atlas.lvs.spice")
    detail = check_netlist(net)
    require(not net["resistors"] and not net["capacitors"], "LVS netlist contains parasitics")
    return {**detail, "native_ext_ports": ordered}


def lvs(out: Path, mutation: str | None = None) -> dict:
    suffix = mutation or "positive"
    reference = out / f"atlas-{suffix}.reference.spice"
    reference.write_text(independent_reference(mutation))
    env = dict(os.environ, PREFLIGHT_LAYOUT=str(out / "atlas.lvs.spice"),
               PREFLIGHT_REFERENCE=str(reference), PREFLIGHT_CELL="atlas",
               PREFLIGHT_SETUP=str(PREFLIGHT / "strict_setup.tcl"),
               PREFLIGHT_LVS_REPORT=str(out / f"atlas-{suffix}.lvs.txt"))
    logpath = out / "logs" / f"atlas-{suffix}-netgen.log"
    text = run_logged(["netgen", "-batch", "source", str(PREFLIGHT / "lvs.tcl")],
                      logpath, out, env)
    for circuit in (1, 2):
        for model, kind in (("sky130_fd_pr__nfet_01v8", "nmos"),
                            ("sky130_fd_pr__nfet_01v8_lvt", "nmos"),
                            ("sky130_fd_pr__pfet_01v8", "pmos")):
            require(f"PREFLIGHT_DEVICE_CLASS {circuit} {model} {kind}" in text,
                    f"Missing distinct primitive-class evidence: {circuit}, {model}")
    return {**lvs_outcome(text, mutation), "reference_sha256": sha256(reference),
            "log_sha256": sha256(logpath), "mutation": mutation}


def extraction(out: Path, mode: str) -> dict:
    path = out / f"atlas.{mode}.spice"
    net = read_spice(path)
    detail = check_netlist(net, rc=mode == "rc")
    require(any(c["value"] > 0 for c in net["capacitors"]), "No real extracted capacitance")
    if mode == "rc":
        require(any(r["value"] > 0 for r in net["resistors"]), "No real extracted resistance")
        require((out / "atlas.res.ext").stat().st_size > 0, "Missing actual resistance intermediate")
    return {**detail, **passive_metrics(net), "netlist_sha256": sha256(path)}


def manifest(out: Path) -> None:
    write_json(out / "artifact-sha256.json", {
        path.relative_to(out).as_posix(): sha256(path)
        for path in sorted(out.rglob("*"))
        if path.is_file() and path.name != "artifact-sha256.json"
    })


def main(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    (out / "logs").mkdir(exist_ok=True)
    results = []

    def record(name: str, operation) -> bool:
        try:
            detail = operation()
            row = {"check": name, "status": "PASS", "detail": detail}
        except (AssertionError, ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
            row = {"check": name, "status": "FAIL", "error": str(error),
                   "traceback": traceback.format_exc()}
        results.append(row)
        write_json(out / "structural-results.json", results)
        print(f'{row["status"]}: {name}' + (f' -- {row["error"]}' if row["status"] == "FAIL" else ""),
              flush=True)
        return row["status"] == "PASS"

    for name in ("protocol.json", "devices.json"):
        shutil.copyfile(HERE / name, out / name)
    write_json(out / "run-context.json", {
        "experimental_commit": os.environ.get("GITHUB_SHA"),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "source": PROTOCOL["source"], "scope": PROTOCOL["phase"],
        "protocol_sha256": sha256(HERE / "protocol.json"),
        "frozen_preflight_sha256": {name: sha256(PREFLIGHT / name) for name in (
            "build_toolchain.sh", "preflight.py", "strict_setup.tcl", "lvs.tcl", "pins.json")},
    })
    try:
        if not record("immutable nominal source and independent 27-device table", audit_source):
            return 1
        if not record("27 actual checked open_pdks PCells", lambda: magic(out, "pcells", make_pcells_request(out))):
            return 1
        placement = {}

        def build():
            placement.update(assemble(out))
            make_routes(out, placement)
            magic(out, "route", out / "route-request.tcl")
            return {"placed_devices": len(placement), "routed_nets": len(NETS)}

        if not record("real mirrored placement routing and three exports", build):
            return 1
        checks = [
            ("nonempty layers actual bbox and gate M1 area", lambda: geometry(out, placement)),
            ("full named-style comparator DRC", lambda: drc(out, "atlas")),
            ("spacing DRC negative control", lambda: drc(out, "nominal27_spacing_bad", negative=True)),
        ]
        for name, operation in checks:
            record(name, operation)
        if record("native top ports and exact device connectivity", lambda: native_interface(out)):
            record("independent nominal Netgen LVS", lambda: lvs(out))
            for mutation in ("connection", "bulk", "width", "flavor"):
                record(f"comparator LVS {mutation} negative control", lambda m=mutation: lvs(out, m))
        else:
            for name in ("positive", "connection", "bulk", "width", "flavor"):
                results.append({"check": f"Netgen LVS {name}", "status": "SKIP",
                                "reason": "Actual native top/port/device contract failed"})
            write_json(out / "structural-results.json", results)
        structural = all(row["status"] == "PASS" for row in results)
        write_json(out / "structural-handoff.json", {
            "qualified": structural, "device_count": 27,
            "checks": len(results), "simulation_not_yet_qualified": True,
            "geometry": next((row["detail"] for row in results
                              if row["check"].startswith("nonempty") and row["status"] == "PASS"), None),
        })
        print(f"NOMINAL27_STRUCTURAL_QUALIFIED {int(structural)}", flush=True)
        for mode in ("c", "rc"):
            record(f"actual {mode} extraction and connectivity", lambda m=mode: extraction(out, m))
        return 0 if all(row["status"] == "PASS" for row in results) else 1
    finally:
        manifest(out)


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve()))

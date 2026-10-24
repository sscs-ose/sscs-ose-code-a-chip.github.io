"""Read native exports without changing their geometry, devices, or passives."""

from __future__ import annotations

from collections import defaultdict
import heapq
import json
from pathlib import Path
import sys

from contract import (
    DEVICES, NETS, PORTS, check_netlist, gds_bounds, inspect_mag, passive_metrics,
    read_spice, require, sha256, signature, write_json,
)


def dc_network(net: dict) -> tuple[dict, dict]:
    graph = defaultdict(list)
    for item in net["resistors"]:
        a, b = item["nodes"]
        graph[a].append((b, item["value"], item["name"]))
        graph[b].append((a, item["value"], item["name"]))
    anchors = {}
    for anchor in NETS:
        pending = [anchor]
        while pending:
            node = pending.pop()
            if node in anchors:
                require(anchors[node] == anchor, f"Shorted intended nets at {node}")
                continue
            anchors[node] = anchor
            pending.extend(other for other, _, _ in graph[node])
    return graph, anchors


def shortest_resistor_path(graph: dict, start: str, target: str) -> dict:
    pending = [(0.0, start, ())]
    visited = set()
    while pending:
        resistance, node, path = heapq.heappop(pending)
        if node in visited:
            continue
        visited.add(node)
        if node == target:
            return {"from": start, "to": target, "sum_ohm": resistance,
                    "resistor_names": list(path),
                    "not_effective_parallel_network_resistance": True}
        for other, value, name in graph.get(node, []):
            heapq.heappush(pending, (resistance + value, other, (*path, name)))
    raise AssertionError(f"No real resistor path from {start} to {target}")


def capacitance_by_net(net: dict, anchors: dict) -> dict:
    incident = {name: defaultdict(float) for name in NETS}
    internal = defaultdict(float)
    for item in net["capacitors"]:
        a, b = (anchors[node] for node in item["nodes"])
        value_ff = item["value"] * 1e15
        if a == b:
            internal[a] += value_ff
        else:
            incident[a][b] += value_ff
            incident[b][a] += value_ff
    return {
        name: {
            "by_other_net_ff": dict(sorted(values.items())),
            "external_incident_sum_ff": sum(values.values()),
            "ground_vss_ff": values.get("vss", 0.0),
            "non_ground_incident_sum_ff": sum(value for other, value in values.items()
                                              if other != "vss"),
            "quiet_rail_sum_ff": sum(values.get(other, 0.0)
                                    for other in ("vss", "vdd", "vinp", "vinn")),
            "code_zero_constant_source_sum_ff": sum(
                values.get(other, 0.0) for other in PORTS if other not in ("clk", "qp", "qn")),
            "clock_ff": values.get("clk", 0.0),
            "same_net_distributed_capacitance_ff": internal[name],
        }
        for name, values in incident.items()
    }


def device_cards(path: Path) -> dict[str, str]:
    cards = {}
    current = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and line[0].lower() == "x":
            current = line.split()[0]
            cards[current] = " ".join(line.split())
        elif line.startswith("+"):
            require(current is not None, "Unexpected device continuation")
            cards[current] += " " + " ".join(line[1:].split())
        else:
            current = None
    return cards


def rectangle_union_area(rectangles: list[list[int]]) -> float:
    xs = sorted({x for rect in rectangles for x in (rect[0], rect[2])})
    total = 0
    for left, right in zip(xs, xs[1:]):
        spans = sorted((y1, y2) for x1, y1, x2, y2 in rectangles
                       if x1 < right and x2 > left)
        upper = None
        height = 0
        for low, high in spans:
            height += high-low if upper is None else max(0, high-max(low, upper))
            upper = high if upper is None else max(upper, high)
        total += (right-left)*height
    return total


def analyze(out: Path) -> dict:
    modes = {mode: read_spice(out / f"atlas.{mode}.spice") for mode in ("lvs", "c", "rc")}
    contracts = {mode: check_netlist(net, rc=mode == "rc") for mode, net in modes.items()}
    cards = {mode: device_cards(out / f"atlas.{mode}.spice") for mode in ("lvs", "c", "rc")}
    require(cards["lvs"] == cards["c"], "LVS/C comparison changes native MOS cards")
    report = {
        "protocol_sha256": sha256(out / "protocol.json"),
        "routing_sha256": sha256(out / "routing.json"),
        "netlist_sha256": {mode: sha256(out / f"atlas.{mode}.spice") for mode in modes},
        "lvs_and_c_native_mos_cards_identical": True,
        "all_three_modes_preserve_27_devices_full_flavors_bulk_w_l_m_and_15_ports": True,
        "capacitance_totals_are_listed_values_not_effective_capacitances": True,
        "same_net_distributed_capacitances_are_reported_not_deleted": True,
        "quiet_rail_definition": ["vss", "vdd", "vinp", "vinn"],
        "shortest_paths_include_native_contact_diffusion_poly_and_interconnect_resistance": True,
        "modes": {},
    }
    for mode, net in modes.items():
        graph, anchors = dc_network(net)
        by_net = defaultdict(list)
        for item in net["resistors"]:
            by_net[anchors[item["nodes"][0]]].append(item)
        devices = {}
        for expected in DEVICES:
            matches = [
                device for device in contracts[mode]["mapped_devices"]
                if signature(device, device["contracted_pins"])
                == signature(expected, expected["nodes"])
            ]
            require(len(matches) == 1, f"Ambiguous physical device: {expected['name']}")
            device = matches[0]
            swapped = device["contracted_pins"][0] != expected["nodes"][0]
            indexes = (2, 1, 0, 3) if swapped else (0, 1, 2, 3)
            physical = {pin: device["pins"][index]
                        for pin, index in zip(("D", "G", "S", "B"), indexes)}
            raw = dict(token.split("=", 1) for token in cards[mode][device["name"]].split()
                       if "=" in token)
            junctions = {}
            for pin, area, perimeter in (("D", "ad", "pd"), ("S", "as", "ps")):
                if swapped:
                    area, perimeter = {"ad": "as", "as": "ad"}[area], \
                        {"pd": "ps", "ps": "pd"}[perimeter]
                junctions[pin] = {"area_um2": float(raw[area]),
                                  "perimeter_um": float(raw[perimeter])}
            devices[expected["name"]] = {
                "native_name": device["name"], "physical_pins": physical,
                "logical_pins": dict(zip(("D", "G", "S", "B"), expected["nodes"])),
                "native_source_drain_swapped": swapped, "junctions": junctions,
                "anchor_to_terminal_paths": {
                    pin: shortest_resistor_path(graph, anchor, physical[pin])
                    for pin, anchor in zip(("D", "G", "S", "B"), expected["nodes"])
                },
            }
        report["modes"][mode] = {
            "metrics": passive_metrics(net),
            "capacitance_by_net": capacitance_by_net(net, anchors),
            "resistance_by_net": {
                name: {"resistor_count": len(items),
                       "sum_listed_ohm": sum(item["value"] for item in items),
                       "minimum_ohm": min(item["value"] for item in items),
                       "maximum_ohm": max(item["value"] for item in items)}
                for name, items in by_net.items()
            },
            "dc_anchored_passive_endpoints": True,
            "floating_annotations_retained": contracts[mode]["floating_annotations_retained"],
            "devices": devices,
        }
    routing = json.loads((out / "routing.json").read_text())
    material = inspect_mag(out / "atlas.mag")["rectangles"]
    residues = {
        "metal1": ["metal1", "viali", "via1"],
        "metal2": ["metal2", "via1", "via2"],
        "metal3": ["metal3", "via2", "via3"],
        "metal4": ["metal4", "via3"],
    }
    require("\nmagscale 1 2\n" in (out / "atlas.mag").read_text(),
            "Metal area requires the verified 0.005 um native grid")
    report["geometry"] = {
        "mag_sha256": sha256(out / "atlas.mag"), "gds_sha256": sha256(out / "atlas.gds"),
        "bbox": gds_bounds(out / "atlas.gds"),
        "measured_metal_union_area_um2": {
            name: rectangle_union_area([rect for layer in layers
                                        for rect in material.get(layer, [])]) * 0.005**2
            for name, layers in residues.items()
        },
        "actual_technology_residue_layers": residues,
        "metal_union_area_is_not_bbox_area": True,
    }
    report["routing"] = {
        "method": routing["method"],
        "by_net": {
            net: {
                "metal1_centerline_um": sum(r["metal1_centerline_um"] for r
                                          in routing["terminal_routes"] if r["net"] == net),
                "metal2_centerline_um": sum(r["metal2_centerline_um"] for r
                                          in routing["terminal_routes"] if r["net"] == net),
                "bus": routing["buses"][net],
            } for net in NETS
        },
        "paired_escape_asymmetry": routing["paired_escape_asymmetry"],
    }
    for key in ("revision", "ground_shields", "output_balancing"):
        if key in routing:
            report["routing"][key] = routing[key]
    return report


if __name__ == "__main__":
    source = Path(sys.argv[1])
    destination = Path(sys.argv[2]) if len(sys.argv) == 3 else source / "parasitic-analysis.json"
    write_json(destination, analyze(source))
    print(f"Native parasitic/connectivity/geometry analysis: {destination}")

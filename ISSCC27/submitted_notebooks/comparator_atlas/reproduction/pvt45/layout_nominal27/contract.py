"""Fail-closed source, connectivity, units, and numerical contracts."""

from __future__ import annotations

import ast
from collections import Counter
import copy
import hashlib
import json
import math
import operator
from pathlib import Path
import re
import struct
import sys

HERE = Path(__file__).resolve().parent
ENTRY = HERE.parent
PREFLIGHT = ENTRY / "layout_preflight"
sys.path.insert(0, str(PREFLIGHT))
from preflight import inspect_gds, inspect_mag, read_spice, require  # noqa: E402

PROTOCOL = json.loads((HERE / "protocol.json").read_text())
DEVICES = json.loads((HERE / "devices.json").read_text())
PORTS = PROTOCOL["source"]["ordered_ports"]
NETS = PROTOCOL["layout"]["routing"]["bus_order"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def logical_lines(text: str) -> list[str]:
    result = []
    for raw in text.splitlines():
        line = raw.partition(";")[0].strip()
        if line.startswith("+"):
            require(bool(result), "Orphan SPICE continuation")
            result[-1] += " " + line[1:].strip()
        elif line and not line.startswith("*"):
            result.append(line)
    return result


def nominal_number(expression: str) -> float:
    operations = {ast.Add: operator.add, ast.Sub: operator.sub,
                  ast.Mult: operator.mul, ast.Div: operator.truediv}

    def visit(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return float(node.value)
        if isinstance(node, ast.Name) and node.id == "pair_skew":
            return 0.0
        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            return operations[type(node.op)](visit(node.left), visit(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -visit(node.operand)
        raise AssertionError(f"Unsupported nominal expression: {expression}")

    value = visit(ast.parse(expression.strip("{}"), mode="eval").body)
    require(math.isfinite(value), "Nonfinite nominal geometry")
    return value


def audit_source(path: Path | None = None) -> dict:
    path = path or ENTRY / "results" / "study" / "selected_circuit.spice"
    data = path.read_bytes()
    source = PROTOCOL["source"]
    require(len(data) == source["bytes"] and hashlib.sha256(data).hexdigest() == source["sha256"],
            "Published source differs from the frozen immutable Git blob")
    lines = logical_lines(data.decode("utf-8"))
    top = lines[0].split()
    require(top == [".subckt", "atlas", *PORTS, "params:", "pair_skew=0"],
            "Published top/ports/nominal parameter contract changed")
    require(lines[-1] == ".ends atlas", "Missing published subcircuit ending")
    observed, junctions = [], {}
    for line in lines[1:-1]:
        tokens = line.split()
        require(tokens[0].startswith("X") and len(tokens) >= 8,
                f"Unexpected published primitive: {line}")
        properties = dict(re.findall(r"(\w+)=(\{[^}]*\}|[^\s]+)", line))
        require(set(properties) == {"w", "l", "ad", "as", "pd", "ps"},
                f"Unexpected published parameter set: {tokens[0]}")
        values = {key: nominal_number(value) for key, value in properties.items()}
        observed.append({"name": tokens[0], "nodes": tokens[1:5], "model": tokens[5],
                         "w_um": values["w"], "l_um": values["l"], "m": 1})
        junctions[tokens[0]] = {key: values[key] for key in ("ad", "as", "pd", "ps")}
    require(observed == DEVICES, "Independent device table differs from nominal published source")
    require(len(observed) == 27 and Counter(d["model"] for d in observed) == source["model_counts"],
            "Wrong device or threshold-flavor counts")
    require(set(NETS) == {n for d in DEVICES for n in d["nodes"]}, "Incomplete routing-net contract")
    return {"commit": source["commit"], "published_blob_sha256": source["sha256"],
            "worktree_bytes_sha256": hashlib.sha256(data).hexdigest(),
            "device_count": len(observed), "model_counts": source["model_counts"],
            "ordered_ports": PORTS, "pair_skew": 0, "source_junction_parameters": junctions}


def independent_reference(mutation: str | None = None) -> str:
    devices = copy.deepcopy(DEVICES)
    target = devices[0]
    if mutation == "connection":
        target["nodes"][1] = "vinn"
    elif mutation == "bulk":
        target["nodes"][3] = "vdd"
    elif mutation == "width":
        target["w_um"] *= 2
    elif mutation == "flavor":
        target["model"] = "sky130_fd_pr__nfet_01v8"
    else:
        require(mutation is None, f"Unknown LVS negative control: {mutation}")
    lines = ["* Independently declared nominal source table, not layout extraction.",
             ".subckt atlas " + " ".join(PORTS)]
    for d in devices:
        lines.append(f'{d["name"]} {" ".join(d["nodes"])} {d["model"]} '
                     f'w={d["w_um"]:.12g} l={d["l_um"]:.12g} m={d["m"]}')
    return "\n".join([*lines, ".ends atlas", ""])


def signature(device: dict, nodes: list[str]) -> tuple:
    return (device["model"], round(device["w_um"], 9), round(device["l_um"], 9),
            device["m"], nodes[1], nodes[3], tuple(sorted((nodes[0], nodes[2]))))


def check_netlist(net: dict, *, rc: bool = False) -> dict:
    require(net["cell"] == "atlas" and net["ports"] == PORTS,
            "Native top or ordered 15-port interface is wrong")
    require(len(net["devices"]) == 27, f'Expected 27 MOS devices, found {len(net["devices"])}')
    names = [d["name"].lower() for d in [*net["devices"], *net["resistors"], *net["capacitors"]]]
    require(len(names) == len(set(names)), "Duplicate SPICE element names")
    parent = {}

    def root(node: str) -> str:
        parent.setdefault(node, node)
        representative = node
        while parent[representative] != representative:
            representative = parent[representative]
        while parent[node] != node:
            previous = node
            node = parent[node]
            parent[previous] = representative
        return representative

    for resistor in net["resistors"]:
        require(rc, "Resistance appeared outside the RC mode")
        require(math.isfinite(resistor["value"]) and resistor["value"] >= 0,
                "Invalid extracted resistance")
        a, b = map(root, resistor["nodes"])
        parent[a] = b
    anchors = {}
    for name in NETS:
        representative = root(name)
        require(representative not in anchors, f"Resistive short involving {name}")
        anchors[representative] = name

    def node_name(node: str) -> str:
        representative = root(node)
        require(representative in anchors, f"No intended-net DC anchor for {node}")
        return anchors[representative]

    observed = []
    mapped = []
    for d in net["devices"]:
        require(all(math.isfinite(d[k]) and d[k] > 0 for k in ("w_um", "l_um", "m")),
                "Invalid extracted geometry")
        pins = [node_name(n) for n in d["pins"]]
        observed.append(signature(d, pins))
        mapped.append({**d, "contracted_pins": pins})
    expected = Counter(signature(d, d["nodes"]) for d in DEVICES)
    actual = Counter(observed)
    require(actual == expected,
            f"Model/W/L/m/gate/bulk/connectivity mismatch: missing={expected-actual}, extra={actual-expected}")
    floating = []
    for item in [*net["resistors"], *net["capacitors"]]:
        require(math.isfinite(item["value"]) and item["value"] >= 0,
                f'Invalid passive value: {item["name"]}')
        named = [node_name(n) for n in item["nodes"]]
        if "FLOATING" in item["annotation"].upper():
            floating.append({**item, "dc_anchors": named})
    return {"device_count": 27, "model_counts": dict(Counter(d["model"] for d in net["devices"])),
            "mapped_devices": mapped, "floating_annotations_retained": floating,
            "all_passive_endpoints_dc_anchored": True}


def passive_metrics(net: dict) -> dict:
    result = {}
    for kind, units in (("resistors", "ohm"), ("capacitors", "farad")):
        values = [item["value"] for item in net[kind]]
        result[kind] = {"count": len(values), "units": units,
                        "minimum": min(values) if values else None,
                        "maximum": max(values) if values else None,
                        "sum": sum(values), "positive_count": sum(v > 0 for v in values)}
    result["sum_is_not_effective_impedance"] = True
    return result


def real8(data: bytes) -> float:
    require(len(data) == 8, "Invalid GDS real")
    return (-1 if data[0] & 128 else 1) * 16.0 ** ((data[0] & 127) - 64) * int.from_bytes(data[1:]) / 2**56


def gds_bounds(path: Path) -> dict:
    data, offset, scale = path.read_bytes(), 0, None
    points, element, width = [], None, 0
    while offset < len(data):
        require(offset + 4 <= len(data), "Truncated GDS header")
        size, kind, _ = struct.unpack_from(">HBB", data, offset)
        require(size >= 4 and offset + size <= len(data), "Truncated GDS")
        payload = data[offset + 4:offset + size]
        if kind == 3:
            scale = real8(payload[8:16]) * 1e6
        elif kind in (8, 9):
            element, width = kind, 0
        elif kind in (10, 11):
            raise AssertionError("Expected flat GDS, not unmeasured hierarchical references")
        elif kind == 12:
            element = None
        elif kind == 15:
            width = abs(struct.unpack(">i", payload)[0]) / 2
        elif kind == 16 and element in (8, 9):
            for x, y in struct.iter_unpack(">ii", payload):
                pad = width if element == 9 else 0
                points.extend(((x-pad, y-pad), (x+pad, y+pad)))
        elif kind == 17:
            element = None
        offset += size
    require(scale is not None and scale > 0 and points, "GDS has no measured physical geometry")
    bounds = [min(p[0] for p in points)*scale, min(p[1] for p in points)*scale,
              max(p[0] for p in points)*scale, max(p[1] for p in points)*scale]
    width, height = bounds[2]-bounds[0], bounds[3]-bounds[1]
    require(width > 0 and height > 0, "Degenerate GDS bounds")
    return {"bounds_um": bounds, "width_um": width, "height_um": height,
            "bbox_area_um2": width*height, "database_unit_um": scale,
            "includes_nonempty_geometry_not_text": True}


def compare_measurements(coarse: list[dict], fine: list[dict]) -> dict:
    deadlines = PROTOCOL["numerics"]["reporting_deadlines_ns"]
    require([row["deadline_ns"] for row in coarse] == deadlines
            and [row["deadline_ns"] for row in fine] == deadlines,
            "Incomplete numerical endpoint set")
    rows = []
    for a, b in zip(coarse, fine):
        require(a["deadline_ns"] == b["deadline_ns"], "Different numerical deadlines")
        for row in (a, b):
            require(row["reset_ok"] is True and row["decision"] in (-1, 0, 1),
                    "Invalid measurement/reset evidence")
            require(math.isfinite(row["core_energy_fj"]) and row["core_energy_fj"] >= 0,
                    "Nonfinite or negative numerical energy")
            require(row["decision_time_ns"] is None
                    or (math.isfinite(row["decision_time_ns"]) and row["decision_time_ns"] >= 0),
                    "Invalid numerical latency")
        energy = b["core_energy_fj"]
        error = abs(a["core_energy_fj"] - energy) / energy * 100 if energy > 0 else math.inf
        delay = None
        if a["decision_time_ns"] is not None and b["decision_time_ns"] is not None:
            delay = abs(a["decision_time_ns"] - b["decision_time_ns"])
        passed = (a["outcome"] == b["outcome"] and a["decision"] == b["decision"]
                  and error <= 1.0 and (delay is None or delay <= 0.02))
        rows.append({"deadline_ns": b["deadline_ns"], "passed": passed,
                     "energy_error_percent": error if math.isfinite(error) else None,
                     "latency_error_ns": delay})
    return {"passed": all(row["passed"] for row in rows), "deadlines": rows}


def refinement_state(history: list[dict]) -> dict:
    require(len(history) >= 2, "Numerical audit needs two actual resolutions")
    identity = history[0]["physical_identity"]
    require(isinstance(identity, dict)
            and {"point", "mode", "netlist_sha256"} <= identity.keys()
            and "max_step_ps" not in identity["point"],
            "Missing timestep-independent physical experiment identity")
    require(all(row["physical_identity"] == identity for row in history),
            "Numerical refinement retuned the physical experiment")
    require(len({row["run_id"] for row in history}) == len(history),
            "Duplicate numerical run evidence")
    steps = [row["max_step_ps"] for row in history]
    require(steps == [10, 5, *PROTOCOL["numerics"]["further_max_steps_ps"]][:len(steps)],
            "Numerical evidence must advance monotonically without a coarse restart")
    comparisons = [compare_measurements(a["measurements"], b["measurements"])
                   for a, b in zip(history, history[1:])]
    sensitive = any(not row["passed"] for row in comparisons)
    streak = 0
    for comparison in reversed(comparisons):
        if not comparison["passed"]:
            break
        streak += 1
    qualified = comparisons[-1]["passed"] and (not sensitive or (streak >= 2 and steps[-1] <= 0.625))
    return {"qualified": qualified, "initially_sensitive": not comparisons[0]["passed"],
            "ever_sensitive": sensitive,
            "consecutive_passing_halvings": streak, "comparisons": comparisons,
            "finest_max_step_ps": steps[-1], "finest_run_id": history[-1]["run_id"],
            "finest_measurements": history[-1]["measurements"]}

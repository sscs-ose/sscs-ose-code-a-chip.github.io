"""Execute and fail-closed inspect actual SKY130 layout-preflight artifacts."""

from __future__ import annotations

import collections
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import traceback

HERE = Path(__file__).resolve().parent
MODELS = {
    "sky130_fd_pr__nfet_01v8": "nmos",
    "sky130_fd_pr__nfet_01v8_lvt": "nmos",
    "sky130_fd_pr__pfet_01v8": "pmos",
}
PRIMITIVE_PORTS = ["D", "G", "S", "B"]
ROUTE_PORTS = ["D", "G", "S", "B", "G2", "S2"]
ROUTE_DEVICE_PINS = [["D", "G", "S", "B"], ["D", "G2", "S2", "B"]]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def spice_number(token: str) -> float:
    match = re.fullmatch(r"([+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?)(meg|[tgkmunpf]?)",
                         token.lower())
    require(match is not None, f"Unsupported SPICE number: {token!r}")
    scales = {"": 1, "t": 1e12, "g": 1e9, "meg": 1e6, "k": 1e3,
              "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15}
    result = float(match[1]) * scales[match[2]]
    require(math.isfinite(result), f"Nonfinite SPICE number: {token}")
    return result


def read_spice(path: Path) -> dict:
    logical = []
    for raw in path.read_text().splitlines():
        code, _, annotation = raw.partition(";")
        line = code.strip()
        if line.startswith("+"):
            require(bool(logical), "SPICE continuation without an initial line")
            previous, comment = logical[-1]
            logical[-1] = (previous + " " + line[1:], comment + " " + annotation.strip())
        elif line and not line.startswith("*"):
            logical.append((line, annotation.strip()))
    result = {"devices": [], "resistors": [], "capacitors": [], "ports": []}
    inside, ended = False, False
    for line, annotation in logical:
        tokens = line.split()
        first = tokens[0].lower()
        require(not (first in (".scale", ".option", ".options") and
                     "scale" in line.lower()), "Unexpected geometry scale directive")
        if first == ".subckt":
            require(not result["ports"], "Expected one flat top-level subcircuit")
            result["ports"] = tokens[2:]
            result["cell"] = tokens[1]
            inside = True
        elif first == ".ends":
            require(inside and (len(tokens) == 1 or tokens[1:] == [result["cell"]]),
                    f"Incorrect subcircuit ending: {line}")
            inside, ended = False, True
        elif first.startswith("x"):
            require(inside, "Transistor outside the extracted .subckt")
            require(len(tokens) >= 8 and tokens[5] in MODELS,
                    f"Unexpected/non-four-terminal primitive: {line}")
            properties = dict(re.findall(r"(\w+)\s*=\s*([^\s]+)", " ".join(tokens[6:])))
            require({"w", "l"} <= properties.keys(), f"Missing geometry: {line}")
            result["devices"].append({
                "name": tokens[0], "pins": tokens[1:5], "model": tokens[5],
                "w_um": float(properties["w"]), "l_um": float(properties["l"]),
                "m": float(properties.get("m", "1")),
            })
        elif first.startswith(("r", "c")):
            require(inside, "Parasitic outside the extracted .subckt")
            require(len(tokens) == 4, f"Unexpected passive element: {line}")
            item = {"name": tokens[0], "nodes": tokens[1:3],
                    "value": spice_number(tokens[3]), "annotation": annotation}
            result["resistors" if first.startswith("r") else "capacitors"].append(item)
        elif not first.startswith("."):
            raise AssertionError(f"Unrecognized SPICE element: {line}")
    require(result["ports"], f"No subcircuit ports in {path}")
    require(ended and not inside, f"Unterminated extracted subcircuit in {path}")
    return result


def inspect_gds(path: Path) -> dict:
    data = path.read_bytes()
    offset, layer, datatype, element = 0, None, None, None
    layers = collections.Counter()
    end_library = False
    points = []
    while offset < len(data):
        require(offset + 4 <= len(data), "Truncated GDS record header")
        size, kind, _ = struct.unpack_from(">HBB", data, offset)
        require(size >= 4 and size % 2 == 0 and offset + size <= len(data),
                "Invalid/truncated GDS record")
        payload = data[offset + 4:offset + size]
        if kind in (8, 9):  # Boundary or path, not text/labels.
            element, layer, datatype, points = kind, None, None, []
        elif kind in (10, 11, 12):
            element = None
        elif kind == 13:
            layer = struct.unpack(">h", payload)[0]
        elif kind == 14:
            datatype = struct.unpack(">h", payload)[0]
        elif kind == 16 and element in (8, 9):
            require(len(payload) % 8 == 0, "Invalid GDS coordinates")
            points = list(struct.iter_unpack(">ii", payload))
        elif kind == 17 and element in (8, 9):
            require(layer is not None and datatype is not None and len(points) >= 2,
                    "GDS geometry has no layer/coordinates")
            require(len(set(points)) > 1, "Degenerate GDS geometry")
            layers[f"{layer}/{datatype}"] += 1
            element = None
        elif kind == 4:
            end_library = True
        offset += size
    require(end_library and layers, "Empty or incomplete GDS")
    return {"bytes": len(data), "geometry_by_layer": dict(sorted(layers.items()))}


def inspect_mag(path: Path) -> dict:
    layers = collections.Counter()
    labels = set()
    rectangles, positions = collections.defaultdict(list), {}
    current = None
    for line in path.read_text().splitlines():
        if line.startswith("<< "):
            current = line[3:-3]
        elif line.startswith("rect "):
            x1, y1, x2, y2 = map(int, line.split()[1:])
            require(x2 > x1 and y2 > y1, "Degenerate Magic rectangle")
            layers[current] += 1
            rectangles[current].append([x1, y1, x2, y2])
        elif line.startswith(("rlabel ", "flabel ")):
            fields = line.split()
            labels.add(fields[-1])
            positions[fields[-1]] = list(map(int, fields[2:6]))
    require(layers, "No painted Magic geometry")
    return {"rectangles_by_layer": dict(layers), "labels": sorted(labels),
            "rectangles": dict(rectangles), "label_positions": positions}


def metal1_area_at_pin_um2(mag: dict, pin: str, grid_um: float) -> float:
    """Measure the actual connected M1/contact component, not a bounding box."""
    require(math.isfinite(grid_um) and grid_um > 0, "Invalid layout grid")
    label = mag["label_positions"][pin]
    x, y = (label[0] + label[2]) / 2, (label[1] + label[3]) / 2
    boxes = mag["rectangles"].get("metal1", []) + mag["rectangles"].get("viali", [])
    reached = {i for i, b in enumerate(boxes) if b[0] <= x <= b[2] and b[1] <= y <= b[3]}
    require(reached, f"Pin {pin} has no actual metal1/contact landing")

    def connected(a, b):
        dx = min(a[2], b[2]) - max(a[0], b[0])
        dy = min(a[3], b[3]) - max(a[1], b[1])
        return dx >= 0 and dy >= 0 and (dx > 0 or dy > 0)

    while True:
        expanded = reached | {i for i, b in enumerate(boxes)
                              if any(connected(b, boxes[j]) for j in reached)}
        if expanded == reached:
            break
        reached = expanded
    component = [boxes[i] for i in reached]
    xs = sorted({x for b in component for x in (b[0], b[2])})
    area = 0
    for left, right in zip(xs, xs[1:]):
        intervals = sorted((b[1], b[3]) for b in component if b[0] <= left and b[2] >= right)
        length, end = 0, -math.inf
        for low, high in intervals:
            length += max(0, high - max(low, end))
            end = max(end, high)
        area += (right - left) * length
    return area * grid_um * grid_um


def independent_reference(spec: dict, mutation: str | None = None) -> str:
    pin_sets = [list(pins) for pins in spec.get("device_pins", [PRIMITIVE_PORTS])]
    require(mutation is None or len(pin_sets) == 1, "Mutations require a primitive reference")
    pins, width, model = pin_sets[0], spec["w_um"], spec["model"]
    if mutation == "connection":
        pins[1] = "S"
    elif mutation == "bulk":
        pins[3] = "S"
    elif mutation == "width":
        width *= 2
    elif mutation == "flavor":
        require(model.endswith("_lvt"), "Flavor control must start with LVT")
        model = "sky130_fd_pr__nfet_01v8"
    elif mutation is not None:
        raise ValueError(f"Unknown reference mutation: {mutation}")
    ports = spec.get("ports", PRIMITIVE_PORTS)
    devices = "".join(
        f"Xreference{i} {' '.join(pins)} {model} w={width} l={spec['l_um']} m=1\n"
        for i, pins in enumerate(pin_sets))
    return (f"* Independent device dimensions and declared topology; geometry in micrometres.\n"
            f".subckt {spec['cell']} {' '.join(ports)}\n"
            f"{devices}"
            f".ends {spec['cell']}\n")


def check_devices(net: dict, spec: dict, connectivity: bool = True) -> list[dict]:
    require(net["cell"] == spec["cell"], f"Wrong extracted top cell: {net['cell']}")
    require(net["ports"] == spec.get("ports", PRIMITIVE_PORTS),
            f"Wrong port order: {net['ports']}")
    expected_pins = list(spec.get("device_pins", [PRIMITIVE_PORTS]))
    require(len(net["devices"]) == len(expected_pins),
            f"Expected {len(expected_pins)} real transistor(s): {net['devices']}")
    for device in net["devices"]:
        for key in ("model", "w_um", "l_um", "m"):
            expected = spec.get(key, 1)
            actual = device[key]
            equal = actual == expected if key == "model" else math.isclose(
                actual, expected, rel_tol=1e-6, abs_tol=1e-9)
            require(equal, f"{key}: expected {expected}, extracted {actual}")
        if connectivity:
            d, g, s, b = device["pins"]
            matches = [pins for pins in expected_pins if
                       g == pins[1] and b == pins[3] and {d, s} == {pins[0], pins[2]}]
            require(len(matches) == 1,
                    f"Wrong gate/bulk/source/drain connectivity: {device['pins']}")
            expected_pins.remove(matches[0])
    if connectivity:
        require(not net["capacitors"] and not net["resistors"],
                "LVS output unexpectedly contains parasitics")
    return net["devices"]


def terminal_components(net: dict, spec: dict) -> dict:
    """Require each physical terminal and every parasitic node to be DC-anchored."""
    components = {}
    for port in net["ports"]:
        reached = {port}
        while True:
            expanded = reached | {
                node for resistor in net["resistors"]
                if reached.intersection(resistor["nodes"]) for node in resistor["nodes"]
            }
            if expanded == reached:
                break
            reached = expanded
        require(reached.intersection(net["ports"]) == {port},
                f"Unexpected resistive short between external ports on {port}")
        components[port] = reached
    expected_pins = list(spec.get("device_pins", [PRIMITIVE_PORTS]))
    require(len(net["devices"]) == len(expected_pins), "Wrong number of physical terminal loads")
    for device in net["devices"]:
        d, g, s, b = device["pins"]
        matches = [pins for pins in expected_pins if
                   g in components[pins[1]] and b in components[pins[3]] and
                   ((d in components[pins[0]] and s in components[pins[2]]) or
                    (s in components[pins[0]] and d in components[pins[2]]))]
        require(len(matches) == 1,
                f"Unanchored or misconnected physical transistor terminals: {device['pins']}")
        expected_pins.remove(matches[0])
    anchored = set().union(*components.values())
    for item in net["resistors"] + net["capacitors"]:
        require(set(item["nodes"]) <= anchored,
                f"Unanchored parasitic, including any FLOATING annotation: {item}")
    return components


def rc_metrics(net: dict, spec: dict) -> dict:
    require(len(net["resistors"]) >= 2 and net["capacitors"],
            "Missing actual distributed R or extracted C")
    for item in net["resistors"] + net["capacitors"]:
        require(item["value"] > 0, f"Nonpositive parasitic: {item}")
    components = terminal_components(net, spec)
    reached = components["D"]
    drain_r = [r for r in net["resistors"] if set(r["nodes"]) <= reached]
    require(len(drain_r) >= 2, "External D does not reach a distributed resistance network")
    degrees = collections.Counter(node for r in drain_r for node in r["nodes"])
    branch_nodes = sorted(node for node, degree in degrees.items() if degree >= 3)
    require(branch_nodes, "No extracted branch junction in the multi-contact drain network")
    transistor_pins = {pin for device in net["devices"] for pin in
                       (device["pins"][0], device["pins"][2])}
    require(len(reached & transistor_pins) == len(net["devices"]),
            "Routed D must reach a distinct drain endpoint for every physical transistor")
    require(bool(reached - set(net["ports"])), "No internal distributed RC nodes")
    drain_c = [c for c in net["capacitors"] if reached.intersection(c["nodes"])]
    require(drain_c, "No capacitance on the routed drain network")
    return {
        "resistor_count": len(net["resistors"]),
        "capacitor_count": len(net["capacitors"]),
        "resistance_min_ohm": min(r["value"] for r in net["resistors"]),
        "resistance_max_ohm": max(r["value"] for r in net["resistors"]),
        "capacitance_min_f": min(c["value"] for c in net["capacitors"]),
        "capacitance_max_f": max(c["value"] for c in net["capacitors"]),
        "drain_resistor_count": len(drain_r),
        "drain_external_port": "D",
        "drain_transistor_terminals": sorted(reached & transistor_pins),
        "drain_internal_nodes": sorted(reached - set(net["ports"])),
        "drain_branch_nodes": branch_nodes,
        "drain_resistor_names": [r["name"] for r in drain_r],
        "drain_resistance_sum_ohm": sum(r["value"] for r in drain_r),
        "drain_capacitance_sum_f": sum(c["value"] for c in drain_c),
        "total_capacitance_f": sum(c["value"] for c in net["capacitors"]),
        "floating_annotated_capacitors_checked": [
            c["name"] for c in net["capacitors"] if "FLOATING" in c.get("annotation", "").upper()
        ],
        "terminal_components": {port: sorted(nodes) for port, nodes in components.items()},
        "resistors": net["resistors"], "capacitors": net["capacitors"],
    }


def run_logged(command: list[str], path: Path, out: Path, env: dict,
               input_text: str | None = None) -> str:
    with path.open("w") as log:
        log.write("$ " + " ".join(command) + "\n")
        log.flush()
        result = subprocess.run(command, input=input_text, text=True, cwd=out,
                                env=env, stdout=log, stderr=subprocess.STDOUT, timeout=90)
    text = path.read_text()
    require(result.returncode == 0, f"Tool exited {result.returncode}; see {path.name}")
    require(not re.search(r"PREFLIGHT_\w+_ERROR|Error .*ignoring|errors reading the setup",
                          text, re.IGNORECASE), f"Tool/setup error in {path.name}")
    return text


def run_magic(out: Path, spec: dict, mode: str, route_length: int = 0) -> None:
    env = dict(os.environ, PREFLIGHT_CELL=spec["cell"], PREFLIGHT_MODE=mode,
               PREFLIGHT_MODEL=spec["model"], PREFLIGHT_WIDTH=str(spec["w_um"]),
               PREFLIGHT_LENGTH=str(spec["l_um"]), PREFLIGHT_ROUTE_LENGTH=str(route_length))
    rc = Path(env["PDK_ROOT"]) / "sky130A/libs.tech/magic/sky130A.magicrc"
    script = HERE / "preflight.tcl"
    text = run_logged(["magic", "-dnull", "-noconsole", "-rcfile", str(rc)],
                      out / "logs" / f"{spec['cell']}-magic.log", out, env,
                      f"source {{{script.as_posix()}}}\n")
    require(f"PREFLIGHT_MAGIC_COMPLETE {spec['cell']}" in text, "Magic did not finish")
    require("ambiguous" not in text.lower() and "deprecated" not in text.lower(),
            "Ambiguous/deprecated Magic command; inspect the raw tool log")


def check_layout(out: Path, cell: str, negative: bool = False,
                 ports: list[str] | None = None) -> dict:
    mag, gds = inspect_mag(out / f"{cell}.mag"), inspect_gds(out / f"{cell}.gds")
    report = (out / f"{cell}.drc.txt").read_text()
    match = re.search(r"^count: (\d+)$", report, re.MULTILINE)
    require(match is not None, "Missing DRC result")
    count = int(match[1])
    require("technology: sky130A" in report and "drc_style: drc(full)" in report,
            "Wrong/inactive DRC technology or style")
    log = (out / "logs" / f"{cell}-magic.log").read_text()
    require(f"PREFLIGHT_DRC_STYLE {cell} drc(full)" in log and
            'The current style is "drc(full)"' in log, "Missing raw DRC style confirmation")
    require(count > 0 if negative else count == 0, f"DRC count {count}: {report}")
    landings = {}
    if not negative:
        ports = PRIMITIVE_PORTS if ports is None else ports
        require(set(ports) <= set(mag["labels"]), f"Missing terminal labels: {ports}")
        require({"65/20", "66/20", "68/20"} <= gds["geometry_by_layer"].keys(),
                "GDS lacks active, poly, or metal1")
        scale = re.search(r"^grid_um: ([0-9.eE+-]+)$", report, re.MULTILINE)
        require(scale is not None, "Missing actual Magic grid scale")
        for gate in (pin for pin in ports if pin.startswith("G")):
            landing = metal1_area_at_pin_um2(mag, gate, float(scale[1]))
            require(landing >= 0.10,
                    f"Connected {gate} metal1 area lacks margin: {landing} um2")
            landings[gate] = landing
        if cell.startswith("route_"):
            require(gds["geometry_by_layer"].get("68/44", 0) >= 2 and
                    gds["geometry_by_layer"].get("69/20", 0) > 0,
                    "Branched probe lacks two physical via1 contacts and metal2")
    return {"drc_count": count, "drc_style": "drc(full)",
            "gate_metal1_area_um2": landings, "mag": mag, "gds": gds}


def lvs_outcome(text: str, mutation: str | None) -> dict:
    marker = re.search(r"PREFLIGHT_LVS_RESULT (-?\d+) (-?\d+)", text)
    require(marker is not None, "Missing explicit Netgen comparison result")
    equivalent, unique = map(int, marker.groups())
    require(equivalent != -1 and unique != -1, "No real LVS comparison or a black box")
    passed = equivalent == 1 and unique == 1
    require(passed if mutation is None else not passed,
            f"LVS {'positive' if mutation is None else mutation} control had wrong outcome")
    if mutation == "width":
        require(unique in (-3, -4), "Width control did not detect a property mismatch")
    return {"equivalent": equivalent, "unique": unique, "expected_match": mutation is None}


def run_lvs(out: Path, spec: dict, mutation: str | None = None) -> dict:
    cell = spec["cell"]
    layout = out / f"{cell}.lvs.spice"
    layout_devices = check_devices(read_spice(layout), spec)
    ports = re.findall(r'^port "([^"]+)" (\d+) ', (out / f"{cell}.ext").read_text(), re.MULTILINE)
    expected_ports = [(pin, str(i)) for i, pin in
                      enumerate(spec.get("ports", PRIMITIVE_PORTS), start=1)]
    require(sorted(ports, key=lambda p: int(p[1])) == expected_ports,
            f"Missing/misordered real extraction ports: {ports}")
    suffix = mutation or "positive"
    reference = out / f"{cell}-{suffix}.reference.spice"
    reference.write_text(independent_reference(spec, mutation))
    reference_net = read_spice(reference)
    env = dict(os.environ, PREFLIGHT_CELL=cell,
               PREFLIGHT_LAYOUT=str(layout),
               PREFLIGHT_REFERENCE=str(reference), PREFLIGHT_SETUP=str(HERE / "strict_setup.tcl"),
               PREFLIGHT_LVS_REPORT=str(out / f"{cell}-{suffix}.lvs.txt"))
    text = run_logged(["netgen", "-batch", "source", str(HERE / "lvs.tcl")],
                      out / "logs" / f"{cell}-{suffix}-netgen.log", out, env)
    for circuit, model in ((1, spec["model"]), (2, reference_net["devices"][0]["model"])):
        require(f"PREFLIGHT_DEVICE_CLASS {circuit} {model} {MODELS[model]}" in text,
                f"Distinct four-terminal primitive class not asserted: {circuit} {model}")
    return dict(lvs_outcome(text, mutation), layout_devices=layout_devices,
                independent_reference_devices=reference_net["devices"])


def main(out: Path) -> int:
    out = out.resolve()
    (out / "logs").mkdir(exist_ok=True)
    repository = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    context = {
        "scope": "toolchain preflight only; not a comparator layout",
        "commit": os.environ.get("GITHUB_SHA"),
        "run_url": f"https://github.com/{repository}/actions/runs/{run_id}"
        if repository and run_id else None,
        "geometry_units": "micrometres; Magic extract style ngspice()",
        "drc_style": "sky130A drc(full), Euclidean on",
        "pex_settings": {"threshold_milliohm": 0, "minresist_milliohm": 0,
                         "mindelay_ps": 0, "cthresh_ff": 0},
        "coordinate_settings": "units internal before snap internal and PCell calls",
        "route_topology": "two_distinct_transistor_drain_fork",
        "route_ports": ROUTE_PORTS,
        "route_device_pins": ROUTE_DEVICE_PINS,
        "route_device_spacing_um": 12,
        "route_spans_um": [20, 800],
        "prior_failed_receipt": "verification_receipt.json (attempts 1/2, unchanged)",
    }
    (out / "run-context.json").write_text(json.dumps(context, indent=2) + "\n")
    specs = json.loads((HERE / "devices.json").read_text())
    results = []

    def record(name, operation):
        try:
            detail = operation()
        except (AssertionError, OSError, ValueError, KeyError, subprocess.TimeoutExpired):
            detail = {"error": traceback.format_exc()}
            status = "FAIL"
        else:
            status = "PASS"
        print(f"{status}: {name}", flush=True)
        if status == "FAIL":
            print(detail["error"], file=sys.stderr, flush=True)
        results.append({"check": name, "status": status, "detail": detail})
        (out / "capabilities.json").write_text(json.dumps(results, indent=2) + "\n")
        return detail if status == "PASS" else None

    for spec in specs:
        cell = spec["cell"]
        generated = record(f"{cell}: generate/extract",
                           lambda s=spec: (run_magic(out, s, "device"), {"generated": True})[1])
        if generated is None:
            continue
        record(f"{cell}: geometry/DRC", lambda c=cell: check_layout(out, c))
        record(f"{cell}: transistor/model/W/L/body", lambda s=spec:
               check_devices(read_spice(out / f"{s['cell']}.lvs.spice"), s))
        record(f"{cell}: Netgen LVS", lambda s=spec: run_lvs(out, s))

    negative_spec = next(spec for spec in specs if spec["cell"] == "n_lvt042_l4")
    for mutation in ("connection", "bulk", "width", "flavor"):
        record(f"negative LVS: {mutation}", lambda m=mutation: run_lvs(out, negative_spec, m))

    spacing_spec = dict(specs[0], cell="spacing_bad")
    record("negative DRC: 0.07um metal1 spacing", lambda: (
        run_magic(out, spacing_spec, "spacing"), check_layout(out, "spacing_bad", True))[1])

    routes = {}
    for cell, length in (("route_short", 20), ("route_long", 800)):
        spec = dict(specs[0], cell=cell, ports=ROUTE_PORTS, device_pins=ROUTE_DEVICE_PINS)

        def make_route(s=spec, length=length):
            run_magic(out, s, "route", length)
            return {"route_span_um": length, "route_width_um": 0.36,
                    "topology": "two_distinct_transistor_drain_fork",
                    "device_count": 2, "physical_via1_contacts": 2}

        generated = record(f"{cell}: routed extraction", make_route)
        if generated is None:
            continue
        record(f"{cell}: geometry/DRC", lambda s=spec:
               check_layout(out, s["cell"], ports=s["ports"]))
        record(f"{cell}: connectivity LVS", lambda s=spec: run_lvs(out, s))

        def check_pex(s=spec):
            c_only = read_spice(out / f"{s['cell']}.c.spice")
            rc = read_spice(out / f"{s['cell']}.rc.spice")
            check_devices(c_only, s, connectivity=False)
            check_devices(rc, s, connectivity=False)
            terminal_components(c_only, s)
            require(c_only["capacitors"] and not c_only["resistors"],
                    "C-only result missing C or mixed with R")
            require((out / f"{s['cell']}.res.ext").stat().st_size > 0,
                    "No real extresist intermediate")
            metrics = rc_metrics(rc, s)
            metrics["c_only_capacitor_count"] = len(c_only["capacitors"])
            metrics["c_only_capacitors"] = c_only["capacitors"]
            metrics["route_geometry"] = (out / f"{s['cell']}.route.txt").read_text()
            return metrics

        metrics = record(f"{cell}: actual distributed RC", check_pex)
        if metrics is not None:
            routes[cell] = metrics

    def compare_routes():
        require(len(routes) == 2, "Both routed probes must have valid RC results")
        short, long = routes["route_short"], routes["route_long"]
        rr = long["drain_resistance_sum_ohm"] / short["drain_resistance_sum_ohm"]
        cr = long["drain_capacitance_sum_f"] / short["drain_capacitance_sum_f"]
        require(rr > 3 and cr > 3, f"Long route did not increase physical RC: R={rr}, C={cr}")
        return {"long_to_short_drain_r_ratio": rr, "long_to_short_drain_c_ratio": cr}

    record("layout-derived RC length dependence", compare_routes)
    manifest = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "artifact-sha256.json":
            manifest[str(path.relative_to(out))] = hashlib.sha256(path.read_bytes()).hexdigest()
    (out / "artifact-sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
    failed = [result["check"] for result in results if result["status"] == "FAIL"]
    print(json.dumps({"passed": len(results) - len(failed), "failed": failed}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))

"""Pure design-schema checks and stage-specific electrical-contract checks."""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

SCHEMA_VERSION = "0.1"
STAGES = (
    ("global_settings", "Global Settings"),
    ("graph_editor", "Node & Edge Editor"),
    ("specifications", "Specifications"),
    ("local_rtl_generation", "Local RTL Generation"),
    ("local_synthesis", "Local Synthesis"),
    ("local_netlist_simulation", "Local Netlist Simulation"),
    ("node_implementation_specs", "Node Implementation Specs"),
    ("global_rtl_generation", "Global RTL Generation"),
    ("global_synthesis", "Global Synthesis"),
    ("global_netlist_simulation", "Global Netlist Simulation"),
    ("layout", "Layout"),
    ("drc", "DRC"),
    ("lvs", "LVS"),
    ("post_layout_verification", "Post-layout Verification"),
)
IMPLEMENTED_STAGES = tuple(stage[0] for stage in STAGES[:3])
VERILOG_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
VERILOG_KEYWORDS = frozenset("""
always and assign automatic begin buf bufif0 bufif1 case casex casez cell
cmos config deassign default defparam design disable edge else end endcase
endconfig endfunction endgenerate endmodule endprimitive endspecify endtable
endtask event for force forever fork function generate genvar highz0 highz1
if ifnone incdir include initial inout input instance integer join large
liblist library localparam macromodule medium module nand negedge nmos nor
noshowcancelled not notif0 notif1 or output parameter pmos posedge primitive
pull0 pull1 pulldown pullup pulsestyle_onevent pulsestyle_ondetect rcmos real
realtime reg release repeat rnmos rpmos rtran rtranif0 rtranif1 scalared
showcancelled signed small specify specparam strong0 strong1 supply0 supply1
table task time tran tranif0 tranif1 tri tri0 tri1 triand trior trireg
unsigned use vectored wait wand weak0 weak1 while wire wor xnor xor
""".split())


class DomainError(Exception):
    """An expected request/schema failure with a safe HTTP representation."""

    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _require_type(value: Any, expected: type, path: str) -> None:
    if type(value) is not expected:
        raise DomainError("invalid_shape", f"{path} must be {expected.__name__}.")


def _field(obj: dict, name: str, expected: type, path: str) -> Any:
    if name not in obj:
        raise DomainError("invalid_shape", f"{path}.{name} is required.")
    _require_type(obj[name], expected, f"{path}.{name}")
    return obj[name]


def _number(value: Any, path: str) -> None:
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise DomainError("invalid_shape", f"{path} must be a finite number.")


def _json_values(value: Any, path: str = "design", depth: int = 0) -> None:
    if depth > 40:
        raise DomainError("invalid_shape", "Design nesting exceeds 40 levels.")
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise DomainError("invalid_shape", f"{path} keys must be strings.")
            _json_values(item, f"{path}.{key}", depth + 1)
    elif type(value) is list:
        for item in value:
            _json_values(item, path, depth + 1)
    elif type(value) is float:
        _number(value, path)
    elif value is not None and type(value) not in (str, int, bool):
        raise DomainError("invalid_shape", f"{path} contains a non-JSON value.")


def validate_shape(design: dict) -> None:
    """Reject malformed data; retain electrically invalid drafts for editing.

    Unknown fields in this schema version are preserved, never silently dropped.
    Unknown schema versions are rejected rather than migrated implicitly.
    """
    _require_type(design, dict, "design")
    _json_values(design)
    version = _field(design, "schema_version", str, "design")
    if version != SCHEMA_VERSION:
        raise DomainError("unsupported_schema", f"Supported schema_version is {SCHEMA_VERSION}.")
    project = _field(design, "project", dict, "design")
    for name in ("id", "name"):
        _field(project, name, str, "design.project")
    settings = _field(design, "settings", dict, "design")
    for name in ("top_module", "clock_name", "reset_name", "reset_active", "reset_kind",
                 "rtl_language", "pdk", "cell_library"):
        _field(settings, name, str, "design.settings")
    if "clock_period_ns" not in settings:
        raise DomainError("invalid_shape", "design.settings.clock_period_ns is required.")
    _number(settings["clock_period_ns"], "design.settings.clock_period_ns")
    nodes = _field(design, "nodes", list, "design")
    edges = _field(design, "edges", list, "design")
    if len(nodes) > 1000 or len(edges) > 10000:
        raise DomainError("design_limit", "M1 supports at most 1000 nodes and 10000 edges.")
    for index, node in enumerate(nodes):
        path = f"design.nodes[{index}]"
        _require_type(node, dict, path)
        for name in ("id", "name", "module_name", "behavior", "test_expectations"):
            _field(node, name, str, path)
        if "parent_id" not in node or node["parent_id"] is not None and type(node["parent_id"]) is not str:
            raise DomainError("invalid_shape", f"{path}.parent_id must be a string or null.")
        constraints = _field(node, "constraints", dict, path)
        _field(constraints, "latency_cycles", int, f"{path}.constraints")
        _field(constraints, "protocol", str, f"{path}.constraints")
        ports = _field(node, "ports", list, path)
        if "instance_array" in node:
            from .instance_arrays import array_shape
            array_shape(node)
        if len(ports) > 1000:
            raise DomainError("design_limit", f"{path} exceeds 1000 ports.")
        for port_index, port in enumerate(ports):
            port_path = f"{path}.ports[{port_index}]"
            _require_type(port, dict, port_path)
            for name in ("id", "name", "direction", "protocol", "clock", "reset"):
                _field(port, name, str, port_path)
            _field(port, "width", int, port_path)
            _field(port, "signed", bool, port_path)
            if "sideband" in port:
                sideband = _field(port, "sideband", dict, port_path)
                _field(sideband, "kind", str, f"{port_path}.sideband")
                association = sideband.get("associated_port_id")
                if "associated_port_id" not in sideband or association is not None and type(association) is not str:
                    raise DomainError("invalid_shape", f"{port_path}.sideband.associated_port_id must be a string or null.")
    for index, edge in enumerate(edges):
        path = f"design.edges[{index}]"
        _require_type(edge, dict, path)
        for name in ("id", "behavior", "protocol"):
            _field(edge, name, str, path)
        for name in ("source", "target"):
            endpoint = _field(edge, name, dict, path)
            for field in ("node_id", "port_id"):
                _field(endpoint, field, str, f"{path}.{name}")
            matches = [node for node in nodes if node["id"] == endpoint["node_id"]]
            if len(matches) == 1:
                from .instance_arrays import validate_endpoint
                validate_endpoint(matches[0], endpoint)
            elif "instance_index" in endpoint:
                index_value = endpoint["instance_index"]
                if type(index_value) is not list or len(index_value) != 2 or any(type(v) is not int for v in index_value):
                    raise DomainError("invalid_instance_array", "Array endpoints require an integer [row, column].")
    layout = _field(design, "layout", dict, "design")
    positions = _field(layout, "nodes", dict, "design.layout")
    for node_id, position in positions.items():
        _require_type(position, dict, f"design.layout.nodes.{node_id}")
        for name in ("x", "y"):
            if name not in position:
                raise DomainError("invalid_shape", f"Layout position {node_id}.{name} is required.")
            _number(position[name], f"design.layout.nodes.{node_id}.{name}")
    viewport = _field(layout, "viewport", dict, "design.layout")
    for name in ("x", "y", "zoom"):
        if name not in viewport:
            raise DomainError("invalid_shape", f"design.layout.viewport.{name} is required.")
        _number(viewport[name], f"design.layout.viewport.{name}")
    if viewport["zoom"] <= 0:
        raise DomainError("invalid_shape", "Viewport zoom must be positive.")
    if "physical_design" in design:
        from .block_layout import validate_block_plan
        validate_block_plan(design["physical_design"], design)
    if "external_io" in design:
        from .external_io import validate_shape as validate_external_io_shape
        validate_external_io_shape(design["external_io"])


def _hash(value: Any) -> str:
    def canonical_numbers(item: Any) -> Any:
        if type(item) is dict:
            return {key: canonical_numbers(child) for key, child in item.items()}
        if type(item) is list:
            return [canonical_numbers(child) for child in item]
        if type(item) is float and item.is_integer():
            return int(item)
        return item

    # JavaScript's JSON.stringify serializes 50.0 as 50. They denote the same
    # value and must preserve existing evidence; true remains distinct from 1.
    encoded = json.dumps(canonical_numbers(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def semantic_design(design: dict) -> dict:
    # Real physical constraints are bound independently by S11. They must not
    # regenerate logical RTL/S05/S06/S08 evidence when only a region is edited.
    return {key: value for key, value in design.items() if key not in ("layout", "project", "physical_design")} | {
        "project": {key: value for key, value in design["project"].items() if key != "name"}
    }


def revision_hashes(design: dict) -> dict:
    return {"semantic_hash": _hash(semantic_design(design)), "layout_hash": _hash(design["layout"])}


def fingerprint(design: dict, stage_id: str) -> str:
    if stage_id == "global_settings":
        return _hash({"schema_version": design["schema_version"], "project_id": design["project"]["id"], "settings": design["settings"]})
    if stage_id == "graph_editor":
        nodes = [{key: value for key, value in node.items()
                  if key not in ("behavior", "test_expectations", "constraints")} for node in design["nodes"]]
        edges = [{key: value for key, value in edge.items() if key != "behavior"} for edge in design["edges"]]
        settings = {key: design["settings"][key] for key in ("clock_name", "reset_name", "reset_kind", "reset_active")}
        value = {"schema_version": design["schema_version"], "project_id": design["project"]["id"], "nodes": nodes, "edges": edges, "settings": settings}
        if "external_io" in design:
            value["external_io"] = design["external_io"]
        return _hash(value)
    if stage_id in dict(STAGES):
        return _hash(semantic_design(design))
    raise DomainError("unknown_stage", f"Unknown stage: {stage_id}.")


def _identifier(name: str) -> bool:
    return bool(VERILOG_IDENTIFIER.fullmatch(name)) and name not in VERILOG_KEYWORDS


def sideband_findings(node: dict, port: dict) -> list[tuple[str, str]]:
    """Check explicitly declared raw control/metadata boundaries, not behavior.

    A raw boundary is one physical signal with no implicit handshake. Metadata
    must name its same-node stream; independent pulses explicitly use null.
    """
    findings = []
    sideband = port.get("sideband")
    if type(sideband) is not dict or sideband.get("kind") not in ("metadata", "pulse", "level"):
        return [("invalid_sideband", "Raw ports require a sideband declaration with kind metadata, pulse or level.")]
    if "associated_port_id" not in sideband:
        return [("invalid_sideband", "Raw ports must explicitly declare associated_port_id, or null for independent pulses.")]
    association = sideband["associated_port_id"]
    if sideband["kind"] == "pulse" and (port["width"] != 1 or port["signed"]):
        findings.append(("invalid_sideband_pulse", "A raw pulse must be a one-bit unsigned signal."))
    if sideband["kind"] == "level" and (port["width"] != 1 or port["signed"]):
        findings.append(("invalid_sideband_level", "A raw level must be a one-bit unsigned signal."))
    if association is None:
        if sideband["kind"] == "metadata":
            findings.append(("missing_sideband_association", "Raw metadata must associate with a same-node valid_ready stream."))
    else:
        streams = [item for item in node["ports"] if item["id"] == association]
        if len(streams) != 1 or streams[0]["protocol"] != "valid_ready":
            findings.append(("invalid_sideband_association", "The associated port must be one same-node valid_ready stream."))
        else:
            stream = streams[0]
            for field in ("direction", "clock", "reset"):
                if port[field] != stream[field]:
                    findings.append((f"sideband_{field}_mismatch", f"Raw sideband {field} must match its associated stream."))
    return findings


def validate_stage(design: dict, stage_id: str) -> list[dict]:
    """Run implemented deterministic checks; never emulate future EDA stages."""
    validate_shape(design)
    if stage_id not in dict(STAGES):
        raise DomainError("unknown_stage", f"Unknown stage: {stage_id}.")
    if stage_id not in IMPLEMENTED_STAGES:
        raise DomainError("unsupported_stage", "This stage has no execution adapter in M1.", 422)
    findings: list[dict] = []

    def add(code: str, message: str, severity: str = "error", **refs: str) -> None:
        findings.append({"code": code, "severity": severity, "message": message, **refs})

    settings = design["settings"]
    if stage_id == "global_settings":
        for name in ("top_module", "clock_name", "reset_name"):
            if not _identifier(settings[name]):
                add("invalid_identifier", f"{name} must be a non-keyword Verilog identifier.")
        if settings["clock_name"] == settings["reset_name"]:
            add("setting_name_collision", "Clock and reset names must be distinct.")
        if settings["clock_period_ns"] <= 0:
            add("invalid_clock_period", "Clock period must be greater than zero nanoseconds.")
        supported = {"reset_active": ("high", "low"), "reset_kind": ("synchronous",),
                     "rtl_language": ("verilog_2005",), "pdk": ("sky130A",),
                     "cell_library": ("sky130_fd_sc_hd",)}
        for name, choices in supported.items():
            if settings[name] not in choices:
                add("unsupported_setting", f"{name}: M1 checks support {', '.join(choices)}.")
        return findings

    if stage_id == "specifications":
        if not design["nodes"]:
            add("empty_design", "Add at least one node before checking specifications.")
        for node in design["nodes"]:
            for name in ("behavior", "test_expectations"):
                if not node[name].strip():
                    add("missing_specification", f"Node {node['name']} requires {name}.", node_id=node["id"])
            if node["constraints"]["latency_cycles"] < 0:
                add("invalid_latency", "Latency cycles cannot be negative.", node_id=node["id"])
            if node["constraints"]["protocol"] != "valid_ready":
                add("unsupported_protocol", "M1 specification checks support valid_ready.", node_id=node["id"])
            for port in node["ports"]:
                if port["protocol"] == "raw":
                    for code, message in sideband_findings(node, port):
                        add(code, message, node_id=node["id"], port_id=port["id"])
                elif port["protocol"] != node["constraints"]["protocol"]:
                    add("node_protocol_mismatch", "Port and node constraint protocols differ.",
                        node_id=node["id"], port_id=port["id"])
        for edge in design["edges"]:
            if not edge["behavior"].strip():
                add("missing_edge_rule", "Describe the edge's data-transfer and stall/reset rules.", edge_id=edge["id"])
        add("natural_language_limit", "Completeness checks do not prove the meaning of natural-language behavior or tests.", "info")
        return findings

    nodes = design["nodes"]
    if not nodes:
        add("empty_design", "Add at least one node before checking the graph.")
    used_ids: dict[str, str] = {}

    def register_id(value: str, kind: str, **refs: str) -> None:
        if not value.strip():
            add("empty_id", f"{kind} ID must not be empty.", **refs)
        elif value in used_ids:
            add("duplicate_id", f"ID {value} is already used by {used_ids[value]}.", **refs)
        else:
            used_ids[value] = kind

    node_map: dict[str, dict] = {}
    module_names: dict[str, str] = {}
    sibling_names: dict[tuple, str] = {}
    port_maps: dict[str, dict] = {}
    for node in nodes:
        node_id = node["id"]
        register_id(node_id, "node", node_id=node_id)
        node_map.setdefault(node_id, node)
        key = (node["parent_id"], node["name"])
        if not node["name"].strip():
            add("empty_node_name", "Node display name must not be empty.", node_id=node_id)
        elif key in sibling_names:
            add("duplicate_node_name", "Sibling nodes must have distinct display names.", node_id=node_id)
        sibling_names[key] = node_id
        if not _identifier(node["module_name"]):
            add("invalid_module_name", "Module name must be a non-keyword Verilog identifier.", node_id=node_id)
        if node["module_name"] == settings["top_module"]:
            add("top_module_collision", "A node module name must differ from the top module name.", node_id=node_id)
        if node["module_name"] in module_names:
            add("duplicate_module_name", "Node definitions require unique module names. Repeat one definition using instance_array.", node_id=node_id)
        module_names[node["module_name"]] = node_id
        port_names: set[str] = set()
        ports: dict[str, dict] = {}
        port_maps[node_id] = ports
        for port in node["ports"]:
            refs = {"node_id": node_id, "port_id": port["id"]}
            register_id(port["id"], "port", **refs)
            ports.setdefault(port["id"], port)
            if not _identifier(port["name"]):
                add("invalid_port_name", "Port name must be a non-keyword Verilog identifier.", **refs)
            if port["name"] in port_names:
                add("duplicate_port_name", "Port names must be unique within a node.", **refs)
            port_names.add(port["name"])
            if port["direction"] not in ("input", "output"):
                add("invalid_direction", "M1 ports must be input or output.", **refs)
            if not 1 <= port["width"] <= 4096:
                add("invalid_width", "Port width must be an integer from 1 to 4096.", **refs)
            if port["protocol"] not in ("valid_ready", "raw"):
                add("unsupported_protocol", "Graph checks support valid_ready streams and explicitly declared raw sidebands.", **refs)
            elif port["protocol"] == "raw":
                for code, message in sideband_findings(node, port):
                    add(code, message, **refs)
            for name, global_name in (("clock", "clock_name"), ("reset", "reset_name")):
                if port[name] != settings[global_name]:
                    add(f"{name}_domain", f"Port {name} must match the global {global_name} in this single-domain M1 design.", **refs)

        # Retain old valid_ready-only diagnostics unchanged. New raw boundaries
        # additionally check collisions against all expanded stream/clock names.
        if any(port["protocol"] == "raw" for port in node["ports"]):
            physical_names = [settings["clock_name"], settings["reset_name"]]
            for port in node["ports"]:
                physical_names.append(port["name"])
                if port["protocol"] == "valid_ready":
                    physical_names.extend((f"{port['name']}_valid", f"{port['name']}_ready"))
            if len(physical_names) != len(set(physical_names)):
                add("interface_collision", "Raw, stream, implicit handshake, clock and reset physical names must be distinct.", node_id=node_id)

    for node in nodes:
        parent_id = node["parent_id"]
        if parent_id is not None and parent_id not in node_map:
            add("missing_parent", "Parent node does not exist.", node_id=node["id"])
        seen = {node["id"]}
        while parent_id is not None and parent_id in node_map:
            if parent_id in seen:
                add("hierarchy_cycle", "Parent relationships contain a cycle.", node_id=node["id"])
                break
            seen.add(parent_id)
            parent_id = node_map[parent_id]["parent_id"]

    drivers: dict[tuple, str] = {}
    connected: set[tuple] = set()
    for edge in design["edges"]:
        edge_id = edge["id"]
        register_id(edge_id, "edge", edge_id=edge_id)
        endpoints: dict[str, dict] = {}
        for endpoint_name in ("source", "target"):
            endpoint = edge[endpoint_name]
            node_id, port_id = endpoint["node_id"], endpoint["port_id"]
            if node_id not in node_map:
                add("missing_node", f"Edge {endpoint_name} node does not exist.", edge_id=edge_id, node_id=node_id)
            elif port_id not in port_maps[node_id]:
                add("missing_port", f"Edge {endpoint_name} port does not exist on this node.",
                    edge_id=edge_id, node_id=node_id, port_id=port_id)
            else:
                endpoints[endpoint_name] = port_maps[node_id][port_id]
                connected.add((node_id, port_id, tuple(endpoint.get("instance_index", []))))
                required_direction = "output" if endpoint_name == "source" else "input"
                if endpoints[endpoint_name]["direction"] != required_direction:
                    add("edge_direction", f"Edge {endpoint_name} must be an {required_direction} port.",
                        edge_id=edge_id, node_id=node_id, port_id=port_id)
        target_key = (edge["target"]["node_id"], edge["target"]["port_id"], tuple(edge["target"].get("instance_index", [])))
        if "target" in endpoints:
            if target_key in drivers:
                add("multiple_drivers", "Input port has more than one driving edge.", edge_id=edge_id,
                    node_id=target_key[0], port_id=target_key[1])
            drivers[target_key] = edge_id
        if "source" in endpoints and "target" in endpoints:
            source, target = endpoints["source"], endpoints["target"]
            for field in ("width", "signed", "protocol", "clock", "reset"):
                if source[field] != target[field]:
                    add(f"edge_{field}_mismatch", f"Connected port {field} values differ.", edge_id=edge_id)
            if source["protocol"] != edge["protocol"] or target["protocol"] != edge["protocol"]:
                add("edge_protocol_mismatch", "Edge protocol must match both port protocols.", edge_id=edge_id)
            if source["protocol"] == target["protocol"] == "raw" and source.get("sideband", {}).get("kind") != target.get("sideband", {}).get("kind"):
                add("edge_sideband_kind_mismatch", "Connected raw sideband kinds must match.", edge_id=edge_id)
        if edge["protocol"] not in ("valid_ready", "raw"):
            add("unsupported_protocol", "Edges support valid_ready streams or matching raw sidebands.", edge_id=edge_id)

    if "external_io" in design:
        from .external_io import covered_endpoints, findings as external_io_findings
        findings.extend(external_io_findings(design))
        connected.update(covered_endpoints(design))

    for node in nodes:
        from .instance_arrays import instance_indices
        for port in node["ports"]:
            for member in instance_indices(node):
                if (node["id"], port["id"], tuple(member or [])) not in connected:
                    suffix = f" [{member[0]},{member[1]}]" if member is not None else ""
                    add("unconnected_port", f"Port{suffix} has no edge; check whether it is an intended external boundary.",
                        "warning", node_id=node["id"], port_id=port["id"])
    add("graph_check_limits", "M1 checks typed port contracts and hierarchy; it does not prove handshake behavior, combinational-loop absence, or RTL correctness.", "info")
    return findings

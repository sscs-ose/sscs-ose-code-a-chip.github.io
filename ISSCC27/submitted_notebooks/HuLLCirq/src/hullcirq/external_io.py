"""Explicit top boundaries, kept separate from synthesizable node definitions.

Version 1 binds one logical top port to one scalar node/member port. Stream
bindings expand data, valid and reverse-ready together. No names are inferred,
no legacy design is migrated, and no RTL or verification values are generated.
"""
from __future__ import annotations

from collections import Counter

from .domain import DomainError, _identifier
from .instance_arrays import validate_endpoint


def blank_external_io():
    return {"version": 1, "ports": [], "connections": []}


def _shape(condition, message):
    if not condition:
        raise DomainError("invalid_external_io", message)


def validate_shape(value):
    """Reject malformed records while retaining electrical mistakes as drafts."""
    _shape(type(value) is dict and set(value) == {"version", "ports", "connections"},
           "external_io requires version, ports and connections only.")
    _shape(type(value["version"]) is int and value["version"] == 1,
           "Only external_io version 1 is supported.")
    _shape(type(value["ports"]) is list and type(value["connections"]) is list
           and len(value["ports"]) <= 4096 and len(value["connections"]) <= 4096,
           "External ports and connections must be lists with at most 4096 records each.")
    for port in value["ports"]:
        _shape(type(port) is dict and set(port) == {"id", "name", "direction", "width", "signed", "protocol"},
               "Each external port requires id, name, direction, width, signed and protocol only.")
        _shape(all(type(port[key]) is str for key in ("id", "name", "direction", "protocol"))
               and type(port["width"]) is int and type(port["signed"]) is bool,
               "External port names/IDs/direction/protocol must be text, width an integer and signed a boolean.")
    for connection in value["connections"]:
        _shape(type(connection) is dict
               and {"id", "external_port_id", "node_id", "port_id"} <= set(connection)
               and set(connection) <= {"id", "external_port_id", "node_id", "port_id", "instance_index"},
               "Each external connection requires id, external_port_id, node_id and port_id, with optional instance_index.")
        _shape(all(type(connection[key]) is str for key in ("id", "external_port_id", "node_id", "port_id")),
               "External connection IDs and endpoints must be text.")
        if "instance_index" in connection:
            index = connection["instance_index"]
            _shape(type(index) is list and len(index) == 2 and all(type(item) is int for item in index),
                   "An external array endpoint requires an integer [row, column] index.")


def _expanded(port):
    fields = {key: port[key] for key in ("name", "direction", "width", "signed")}
    result = [fields]
    if port["protocol"] == "valid_ready":
        result.extend([
            {"name": port["name"] + "_valid", "direction": port["direction"], "width": 1, "signed": False},
            {"name": port["name"] + "_ready", "direction": "output" if port["direction"] == "input" else "input",
             "width": 1, "signed": False},
        ])
    return result


def _endpoint(value):
    return value["node_id"], value["port_id"], tuple(value.get("instance_index", []))


def _analyze(design):
    if "external_io" not in design:
        return [], [], [], set()
    value = design["external_io"]
    validate_shape(value)
    diagnostics, physical_ports, records, covered = [], [], [], set()

    def add(code, message, severity="error", **refs):
        diagnostics.append({"code": code, "severity": severity, "message": message, **refs})

    nodes = design.get("nodes", [])
    node_groups = {}
    for node in nodes:
        node_groups.setdefault(node["id"], []).append(node)
    graph_ids = {item["id"] for item in nodes}
    graph_ids.update(port["id"] for node in nodes for port in node["ports"])
    graph_ids.update(edge["id"] for edge in design.get("edges", []))
    ids = Counter([port["id"] for port in value["ports"]] + [c["id"] for c in value["connections"]])
    port_groups, expanded_by_id, invalid_ports = {}, {}, set()
    settings = design.get("settings", {})
    names = Counter([settings.get("clock_name"), settings.get("reset_name")])
    for port in value["ports"]:
        port_id = port["id"]
        port_groups.setdefault(port_id, []).append(port)
        before = len(diagnostics)
        refs = {"external_port_id": port_id}
        if not port_id.strip() or ids[port_id] != 1 or port_id in graph_ids:
            add("external_duplicate_id", "External port and connection IDs must be nonempty and unique across the graph.", **refs)
        if not _identifier(port["name"]):
            add("external_invalid_name", "External names must be non-keyword Verilog identifiers.", **refs)
        if port["direction"] not in ("input", "output"):
            add("external_direction", "An external port direction must be input or output.", **refs)
        if not 1 <= port["width"] <= 4096:
            add("external_width", "An external port width must be between 1 and 4096 bits.", **refs)
        if port["protocol"] not in ("valid_ready", "raw"):
            add("external_protocol", "External ports support valid_ready streams or raw signals.", **refs)
        if len(diagnostics) != before:
            invalid_ports.add(port_id)
        else:
            expanded_by_id[port_id] = _expanded(port)
            names.update(item["name"] for item in expanded_by_id[port_id])
    for port in value["ports"]:
        port_id = port["id"]
        if port_id in invalid_ports:
            continue
        if any(names[item["name"]] != 1 for item in expanded_by_id[port_id]):
            add("external_name_collision", "Expanded external data/valid/ready names must be unique and distinct from clock/reset.",
                external_port_id=port_id)
            invalid_ports.add(port_id)
        else:
            physical_ports.extend(dict(item) for item in expanded_by_id[port_id])

    external_usage = Counter(c["external_port_id"] for c in value["connections"])
    endpoint_usage = Counter(_endpoint(c) for c in value["connections"])
    internal_endpoints = {_endpoint(edge[side]) for edge in design.get("edges", []) for side in ("source", "target")}
    valid_external_ids = set()
    for connection in value["connections"]:
        refs = {"connection_id": connection["id"], "external_port_id": connection["external_port_id"],
                "node_id": connection["node_id"], "port_id": connection["port_id"]}
        before = len(diagnostics)
        key = _endpoint(connection)
        if not connection["id"].strip() or ids[connection["id"]] != 1 or connection["id"] in graph_ids:
            add("external_duplicate_id", "External port and connection IDs must be nonempty and unique across the graph.", **refs)
        candidates = port_groups.get(connection["external_port_id"], [])
        if len(candidates) != 1:
            add("external_missing_port", "External connection must name one existing external port.", **refs)
        if external_usage[connection["external_port_id"]] != 1 or endpoint_usage[key] != 1:
            add("external_multiple_binding", "External I/O v1 requires one external port per one logical node/member endpoint.", **refs)
        if key in internal_endpoints:
            add("external_internal_collision", "An external binding and an internal edge cannot share one logical endpoint in external I/O v1.", **refs)
        node_candidates = node_groups.get(connection["node_id"], [])
        if len(node_candidates) != 1:
            add("external_missing_node", "External connection must name one existing node.", **refs)
            continue
        node = node_candidates[0]
        try:
            validate_endpoint(node, connection)
        except DomainError:
            add("external_instance_index", "External connection must address the exact declared scalar or array member.", **refs)
        port_candidates = [p for p in node["ports"] if p["id"] == connection["port_id"]]
        if len(port_candidates) != 1:
            add("external_missing_node_port", "External connection must name one existing port on its node.", **refs)
            continue
        node_port = port_candidates[0]
        if not _identifier(node_port["name"]):
            add("external_node_port_name", "The bound node pin must be a non-keyword Verilog identifier.", **refs)
        expanded_node_names = Counter(item["name"] for p in node["ports"]
                                      for item in _expanded(p) if p["protocol"] in ("valid_ready", "raw"))
        expanded_node_names.update((settings.get("clock_name"), settings.get("reset_name")))
        if any(expanded_node_names[item["name"]] != 1 for item in _expanded(node_port)):
            add("external_node_name_collision", "The bound node's expanded data/valid/ready names must be distinct from other pins and clock/reset.", **refs)
        if len(candidates) == 1:
            external_port = candidates[0]
            for field in ("direction", "width", "signed", "protocol"):
                if external_port[field] != node_port[field]:
                    add("external_" + field + "_mismatch", f"External and node port {field} must match.", **refs)
            for field, global_key in (("clock", "clock_name"), ("reset", "reset_name")):
                if node_port[field] != settings.get(global_key):
                    add("external_" + field + "_mismatch", "External boundaries use the saved global clock/reset domain.", **refs)
        if len(diagnostics) != before or connection["external_port_id"] in invalid_ports:
            continue
        external_port = candidates[0]
        expanded_node = _expanded(node_port)
        for top_pin, node_pin in zip(expanded_by_id[external_port["id"]], expanded_node):
            record = {"external_name": top_pin["name"], "node_id": node["id"], "port_id": node_port["id"],
                      "node_pin": node_pin["name"], **{k: top_pin[k] for k in ("direction", "width", "signed")}}
            if "instance_index" in connection:
                record["instance_index"] = list(connection["instance_index"])
            records.append(record)
        covered.add(key)
        valid_external_ids.add(external_port["id"])
    for port in value["ports"]:
        if port["id"] not in invalid_ports and port["id"] not in valid_external_ids:
            add("external_unconnected_port", "External port has no valid explicit node connection.", "warning", external_port_id=port["id"])
    return diagnostics, physical_ports, records, covered


def findings(design):
    return _analyze(design)[0]


def covered_endpoints(design):
    """Only individually valid bindings suppress an unconnected-node warning."""
    return _analyze(design)[3]


def expanded_ports(design):
    """Return typed physical declarations, never clock/reset or DUT nodes."""
    diagnostics, ports, _, _ = _analyze(design)
    if any(item["severity"] == "error" for item in diagnostics):
        raise DomainError("external_io_invalid", "Correct external I/O errors before using the top interface.", 422)
    return ports


def bindings(design):
    """Return trustworthy exact pin bindings; unresolved boundaries cannot run."""
    diagnostics, _, records, _ = _analyze(design)
    if diagnostics:
        raise DomainError("external_io_invalid", "Every external port needs one valid explicit node/member connection.", 422)
    return records

"""Pure logical-instance addressing; not a physical-placement instruction.

An array node retains one public scalar module definition. Each endpoint names
one declared array element explicitly; no implicit broadcast or lane guessing.
"""
from __future__ import annotations

from .domain import DomainError


def _require(condition, message):
    if not condition:
        raise DomainError("invalid_instance_array", message, 422)


def array_shape(node):
    """Return ``None`` for an ordinary node or a strictly typed 2D shape."""
    _require(type(node) is dict, "An instance-array node must be an object.")
    if "instance_array" not in node:
        return None
    value = node["instance_array"]
    _require(type(value) is dict and set(value) == {"rows", "columns"},
             "Instance arrays require only rows and columns.")
    _require(all(type(value[key]) is int and 1 <= value[key] <= 16 for key in value),
             "Array rows and columns must be integers from 1 to 16.")
    return value["rows"], value["columns"]


def instance_indices(node):
    shape = array_shape(node)
    return [None] if shape is None else [[r, c] for r in range(shape[0]) for c in range(shape[1])]


def validate_endpoint(node, endpoint):
    """Reject undeclared/nonexistent element addresses, including bools."""
    shape = array_shape(node)
    _require(type(endpoint) is dict and endpoint.get("node_id") == node.get("id"),
             "An endpoint must address its declared graph node.")
    if shape is None:
        _require("instance_index" not in endpoint,
                 "Only an instance-array endpoint may declare instance_index.")
        return None
    index = endpoint.get("instance_index")
    _require(type(index) is list and len(index) == 2
             and all(type(value) is int for value in index)
             and 0 <= index[0] < shape[0] and 0 <= index[1] < shape[1],
             "Each array endpoint requires an in-range [row, column] instance_index.")
    return list(index)


def instance_name(node, index=None):
    shape = array_shape(node)
    if shape is None:
        _require(index is None, "Ordinary nodes have no array index.")
        return node["id"].replace("-", "_")
    validate_endpoint(node, {"node_id": node["id"], "instance_index": index})
    return f"pe{index[0]}{index[1]}" if node["id"] == "npu2-pe" else f"element_{index[0]}_{index[1]}"


def validate_design_arrays(design):
    nodes = design.get("nodes") if type(design) is dict else None
    _require(type(nodes) is list and all(type(node) is dict for node in nodes),
             "Instance addressing requires declared graph nodes.")
    by_id = {node.get("id"): node for node in nodes}
    _require(len(by_id) == len(nodes), "Instance addressing requires unique node IDs.")
    for node in nodes:
        array_shape(node)
    for edge in design.get("edges", []):
        for side in ("source", "target"):
            endpoint = edge.get(side) if type(edge) is dict else None
            _require(type(endpoint) is dict and endpoint.get("node_id") in by_id,
                     "An instance endpoint must reference an existing node.")
            validate_endpoint(by_id[endpoint["node_id"]], endpoint)

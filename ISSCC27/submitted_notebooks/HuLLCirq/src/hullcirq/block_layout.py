"""Versioned same-chip placement regions; pure planning and proof checks.

No Functional Map inference is used. Ownership comes from the hierarchy of the
technology-mapped Yosys JSON, before OpenROAD links that hierarchy into OpenDB.
The module is also copied unchanged into each fixed Linux execution directory.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from pathlib import Path

try:
    from .domain import DomainError
except ImportError:  # frozen standalone execution copy
    class DomainError(ValueError):
        def __init__(self, code, message, status=400):
            self.code, self.message, self.status = code, message, status
            super().__init__(message)

VERSION = "block-regions-v1"
MIXED_VERSION = "mixed-v1"
PROFILE_VERSION = "hullcirq-sky130-block-regions-v1"
FLOW = "HuLLCirqBlockRegionsV1"
LAUNCHER = "block_region_flow_v1.py"
OPENROAD_COMMIT = "dcf36133a369abc8f3c5e5738cd4d82e4903c0e0"
MAPPED_TIE_MASTER = "sky130_fd_sc_hd__conb_1"
BLOCK_ARTIFACTS = {"block-input", "block-plan", "block-synthesis", "block-ownership", "block-capacity", "block-placement-proof", "block-flow", "block-runtime"}
_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_-]{0,63}")
_INSTANCE = re.compile(r"[^\s/\\\x00-\x1f]+")


def require(condition, code, message):
    if not condition:
        raise DomainError(code, message)


def object_hash(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _rect(value, label):
    require(type(value) is list and len(value) == 4 and all(type(v) in (int, float) and math.isfinite(v) and abs(v) <= 1000000 for v in value),
            "block_region_geometry", label + " needs four finite micrometre coordinates.")
    require(value[0] < value[2] and value[1] < value[3], "block_region_geometry", label + " must have positive width and height.")
    return copy.deepcopy(value)


def contains(outer, inner):
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def overlaps(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def mapped_tie_names(ownership):
    """Exact owned mapped ties, not subsequently inserted support cells."""
    return sorted(cell["name"] for region in ownership["regions"] for cell in region["cells"]
                  if cell["master"] == MAPPED_TIE_MASTER)


def protect_mapped_ties(ownership, instances):
    """Explicit-run OpenDB operation; never invoked by planning or viewing.

    The pinned repair_tie_fanout otherwise replaces and deletes these original
    cells. Preserve their identity, without weakening final ownership checks or
    disabling sizing of ordinary logic. Floorplan/repair-inserted ties are not
    assigned invented source ownership or protected by this operation.
    """
    names = mapped_tie_names(ownership)
    for name in names:
        inst = instances.get(name)
        require(inst is not None and inst.getMaster().getName() == MAPPED_TIE_MASTER,
                "block_region_tie_protection", "Protect only the exact hierarchy-derived mapped tie cell.")
        inst.setDoNotTouch(True)
        require(inst.isDoNotTouch(), "block_region_tie_protection", "OpenDB did not retain the mapped tie protection.")
    return names


def expanded_targets(design):
    """Return exact node/index pairs, rejecting malformed array metadata."""
    require(type(design) is dict and type(design.get("nodes")) is list, "block_region_design", "Save a valid node graph before placement planning.")
    result = []
    seen = set()
    for node in design["nodes"]:
        identifier = node.get("id") if type(node) is dict else None
        require(type(identifier) is str and identifier not in seen, "block_region_design", "Placement requires unique logical node IDs.")
        seen.add(identifier)
        array = node.get("instance_array")
        if array is None:
            result.append({"node_id": identifier})
            continue
        require(type(array) is dict and set(array) == {"rows", "columns"}
                and all(type(array[k]) is int and 1 <= array[k] <= 16 for k in ("rows", "columns")),
                "block_region_array", "Instance arrays need integer rows and columns from 1 to 16.")
        result += [{"node_id": identifier, "instance_index": [r, c]} for r in range(array["rows"]) for c in range(array["columns"])]
    return result


def _target_key(target):
    return (target["node_id"], tuple(target.get("instance_index", [])))


def validate_block_plan(physical_design, design):
    """Validate without writes or tools. None is historical mixed placement."""
    if physical_design is None:
        return None
    require(type(physical_design) is dict, "block_region_plan", "Physical design must be a placement-mode object.")
    if physical_design.get("version") == MIXED_VERSION:
        require(set(physical_design) == {"version"}, "block_region_plan", "Mixed placement accepts only its explicit version.")
        return {"version": MIXED_VERSION}
    require(set(physical_design) == {"version", "core_um", "regions"} and physical_design["version"] == VERSION,
            "block_region_plan", "Use block-regions-v1 with core_um and regions, or mixed-v1.")
    core = _rect(physical_design["core_um"], "Core")
    require(core[0] >= 10 and core[1] >= 10, "block_region_geometry", "Keep at least 10 micrometres between the core and the die origin.")
    regions = physical_design["regions"]
    require(type(regions) is list and 1 <= len(regions) <= 128, "block_region_plan", "Specify between 1 and 128 placement regions.")
    expected = {_target_key(t) for t in expanded_targets(design)}
    ids, assigned, result = set(), set(), []
    for region in regions:
        require(type(region) is dict and set(region) == {"id", "targets", "rect_um"}
                and type(region["id"]) is str and _ID.fullmatch(region["id"]) is not None and region["id"] not in ids,
                "block_region_plan", "Regions need unique safe IDs, targets and rect_um.")
        ids.add(region["id"])
        rect = _rect(region["rect_um"], "Region " + region["id"])
        require(contains(core, rect), "block_region_outside_core", "Every region must stay inside the saved core.")
        require(not any(overlaps(rect, r["rect_um"]) for r in result), "block_region_overlap", "Placement regions must not overlap; touching boundaries are allowed.")
        targets = region["targets"]
        require(type(targets) is list and targets, "block_region_plan", "Each region requires at least one block instance.")
        saved_targets = []
        for target in targets:
            require(type(target) is dict and set(target) in ({"node_id"}, {"node_id", "instance_index"})
                    and type(target.get("node_id")) is str, "block_region_target", "Targets require an exact node ID and optional row/column index.")
            if "instance_index" in target:
                require(type(target["instance_index"]) is list and len(target["instance_index"]) == 2 and all(type(v) is int for v in target["instance_index"]),
                        "block_region_target", "Array indices must be two integers.")
            key = _target_key(target)
            require(key in expected and key not in assigned, "block_region_target", "Every target must exist and belong to exactly one region.")
            assigned.add(key)
            saved_targets.append(copy.deepcopy(target))
        result.append({"id": region["id"], "targets": saved_targets, "rect_um": rect})
    require(assigned == expected, "block_region_target_missing", "Assign every expanded block instance to a region before saving block placement.")
    return {"version": VERSION, "core_um": core, "regions": result}


def is_block_configuration(configuration):
    return type(configuration) is dict and configuration.get("profile", {}).get("profile_version") == PROFILE_VERSION


def effective_configuration(configuration, design, root=None):
    """Physical-only choice is read from the CURRENT design, never frozen S08."""
    plan = validate_block_plan(design.get("physical_design"), design)
    if plan is None or configuration is None:
        return copy.deepcopy(configuration)
    require(type(configuration) is dict, "physical_configuration_invalid", "Configure the pinned physical runtime first.")
    root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    result = copy.deepcopy(configuration)
    for key in ("resume", "repair_source_binding", "repair_checkpoint_inventory", "block_plan", "block_plan_sha256", "block_design"):
        result.pop(key, None)
    result["profile"] = json.loads((root / "configs" / ("physical_profile_sky130_block_regions_v1.json" if plan["version"] == VERSION else "physical_profile_sky130.json")).read_text(encoding="utf-8"))
    if plan["version"] == VERSION:
        result.update(block_plan=plan, block_plan_sha256=object_hash(plan),
                      block_design={"nodes": [{k: copy.deepcopy(n[k]) for k in ("id", "module_name", "instance_array") if k in n} for n in design["nodes"]]})
    return result


def source_input(configuration, manifest, top):
    require(is_block_configuration(configuration), "block_region_profile", "Use the pinned block-region profile.")
    design = configuration.get("block_design")
    plan = validate_block_plan(configuration.get("block_plan"), design)
    require(plan is not None and plan["version"] == VERSION and object_hash(plan) == configuration.get("block_plan_sha256"),
            "block_region_plan", "Retain the exact normalized placement plan and hash.")
    modules = {n["node_id"]: n["module_name"] for n in manifest["nodes"]}
    require(set(modules) == {n["id"] for n in design["nodes"]}
            and all(modules[n["id"]] == n["module_name"] for n in design["nodes"]),
            "block_region_source", "Region targets and adopted module sources must correspond exactly.")
    require(all(n.get("instance_array") is None or n["id"] == "npu2-pe" and n["instance_array"] == {"rows": 2, "columns": 2} for n in design["nodes"]),
            "block_region_array_unsupported", "This versioned physical array contract supports the explicit 2 by 2 npu2-pe lanes only.")
    return {"version": VERSION, "top_module": top, "plan": plan, "plan_sha256": object_hash(plan),
            "design": copy.deepcopy(design), "source_manifest_sha256": object_hash(manifest)}


def build_ownership(synthesis, inputs):
    """Expand exact mapped module instances, never connectivity-inferred roles."""
    modules = synthesis.get("modules") if type(synthesis) is dict else None
    top = inputs["top_module"]
    require(type(modules) is dict and top in modules, "block_region_hierarchy", "Mapped synthesis JSON must retain the requested top hierarchy.")
    cells = modules[top].get("cells", {})
    owned, targets = {}, {}
    def leaves(module, path, trail):
        require(module not in trail, "block_region_hierarchy", "Recursive synthesis hierarchy is not supported.")
        result = []
        for name, cell in modules[module].get("cells", {}).items():
            require(type(name) is str and _INSTANCE.fullmatch(name) is not None and type(cell) is dict and type(cell.get("type")) is str,
                    "block_region_hierarchy", "Mapped hierarchy uses an unsupported or ambiguous instance name.")
            instance = path + "/" + name if path else name
            master = cell["type"]
            blackbox = modules.get(master, {}).get("attributes", {}).get("blackbox", "0")
            blackbox = int(blackbox, 2) if type(blackbox) is str else int(blackbox)
            if master in modules and not blackbox:
                result += leaves(master, instance, trail + (module,))
            else:
                require(master.startswith("sky130_fd_sc_hd__"), "block_region_hierarchy", "Every region-owned leaf must be an actually mapped SKY130 standard cell.")
                result.append({"name": instance, "master": master})
        return result
    for node in inputs["design"]["nodes"]:
        matches = sorted(name for name, cell in cells.items() if cell.get("type") == node["module_name"])
        array = node.get("instance_array")
        expected = [t for t in expanded_targets({"nodes": [node]})]
        require(len(matches) == len(expected), "block_region_hierarchy", "The mapped top must instantiate every logical block exactly as declared.")
        for target in expected:
            if array is None:
                instance = matches[0]
            else:
                require(node["id"] == "npu2-pe", "block_region_array_unsupported", "The version-1 physical array contract uses explicit npu2-pe lane names.")
                instance = "pe" + "".join(str(v) for v in target["instance_index"])
                require(instance in matches, "block_region_hierarchy", "Mapped PE lane names must exactly match their saved array indices.")
            target_cells = leaves(node["module_name"], instance, ())
            require(target_cells, "block_region_empty", "A block was removed or has no mapped standard cells; do not fabricate a placement region.")
            key = _target_key(target)
            targets[key] = target_cells
    regions = []
    for region in inputs["plan"]["regions"]:
        entries = []
        for target in region["targets"]:
            for cell in targets[_target_key(target)]:
                require(cell["name"] not in owned, "block_region_hierarchy", "One mapped cell cannot belong to multiple logical blocks.")
                owned[cell["name"]] = region["id"]
                entries.append({**cell, "target": copy.deepcopy(target)})
        regions.append({**copy.deepcopy(region), "cells": sorted(entries, key=lambda v: v["name"])})
    return {"version": VERSION, "ownership_origin": "exact_preserved_technology_mapped_module_hierarchy",
            "plan_sha256": inputs["plan_sha256"], "source_manifest_sha256": inputs["source_manifest_sha256"],
            "synthesis_sha256": object_hash(synthesis), "regions": regions,
            "scope": "original_region_owned_mapped_cells; inserted clock/physical/interconnect support is not claimed as block ownership"}


def validate_placement(ownership, proof):
    require(type(proof) is dict and proof.get("version") == VERSION and proof.get("ownership_sha256") == object_hash(ownership),
            "block_region_proof", "Placement proof must bind the exact mapped ownership manifest.")
    expected = {cell["name"]: region for region in ownership["regions"] for cell in region["cells"]}
    ties = set(mapped_tie_names(ownership))
    cells = proof.get("cells")
    require(type(cells) is list and len(cells) == len(expected) and len({c.get("name") for c in cells if type(c) is dict}) == len(expected),
            "block_region_proof", "Retain exactly one final placement for every original region-owned mapped cell.")
    for cell in cells:
        require(type(cell) is dict and cell.get("name") in expected and cell.get("region_id") == expected[cell["name"]]["id"]
                and cell.get("placed") is True and cell.get("group_member") is True,
                "block_region_proof", "Final cells must remain placed in their exact saved region groups.")
        if cell["name"] in ties:
            require(cell.get("master") == MAPPED_TIE_MASTER and cell.get("mapped_tie_protected") is True,
                    "block_region_tie_protection", "Every original mapped tie must retain its exact master, identity and do-not-touch protection.")
        bbox = _rect(cell.get("bbox_um"), "Final cell")
        require(contains(expected[cell["name"]]["rect_um"], bbox), "block_region_containment", "A region-owned cell crosses its saved physical region.")
    require(proof.get("validation_status") == "Passed", "block_region_proof", "The actual final OpenDB containment check must complete successfully.")
    return None


def validate_capacity(ownership, capacity):
    require(type(capacity) is dict and capacity.get("version") == VERSION and capacity.get("ownership_sha256") == object_hash(ownership)
            and type(capacity.get("regions")) is list, "block_region_capacity", "Retain the actual source-bound OpenDB row-capacity check.")
    require(capacity.get("protected_mapped_ties", []) == mapped_tie_names(ownership),
            "block_region_tie_protection", "The applied tie-protection record must list every exact owned mapped tie.")
    regions = capacity["regions"]
    require(len(regions) == len(ownership["regions"]) and {r.get("id") for r in regions} == {r["id"] for r in ownership["regions"]},
            "block_region_capacity", "Every source-bound placement region needs exactly one capacity record.")
    for region in regions:
        require(all(type(region.get(k)) in (int, float) and math.isfinite(region[k]) and region[k] > 0 for k in ("cell_area_um2", "row_area_um2"))
                and region.get("maximum_utilization") == 0.7 and region["cell_area_um2"] <= 0.7 * region["row_area_um2"],
                "block_region_capacity", "Fixed 70 percent row capacity must be met without missing or fabricated numeric values.")
    return None


def validate_def_binding(text, ownership, proof):
    """Check final DEF identity/placement against the actual OpenDB proof."""
    validate_placement(ownership, proof)
    unit = re.search(r"\bUNITS\s+DISTANCE\s+MICRONS\s+([0-9]+)\s*;", text)
    body = re.search(r"\bCOMPONENTS\s+([0-9]+)\s*;(.*?)\bEND\s+COMPONENTS\b", text, re.S)
    require(unit is not None and body is not None and int(unit[1]) > 0
            and type(proof.get("database_units_per_micron")) is int and proof["database_units_per_micron"] > 0,
            "block_region_def", "Final DEF and checked OpenDB require positive exact units and complete components.")
    def_units, odb_units = int(unit[1]), proof["database_units_per_micron"]
    components = {}
    for statement in body[2].split(";"):
        if not statement.strip():
            continue
        match = re.match(r"\s*-\s+(\S+)\s+(\S+)(.*)", statement, re.S)
        require(match is not None and match[1] not in components, "block_region_def", "Final DEF components must have unique complete names.")
        placed = re.search(r"\+\s+(?:PLACED|FIXED|COVER)\s*\(\s*(-?[0-9]+)\s+(-?[0-9]+)\s*\)\s+(\S+)", match[3])
        components[match[1].replace("\\", "")] = (match[2], placed)
    require(len(components) == int(body[1]), "block_region_def", "Final DEF component count must match its complete section.")
    orientations = {"N": "R0", "S": "R180", "E": "R270", "W": "R90", "FN": "MY", "FS": "MX", "FE": "MYR90", "FW": "MXR90"}
    for cell in proof["cells"]:
        entry = components.get(cell["name"])
        require(entry is not None and entry[0] == cell.get("master") and entry[1] is not None,
                "block_region_def", "Final DEF must contain each exact checked block cell and final master.")
        placed = entry[1]
        origin = cell.get("origin_dbu")
        require(type(origin) is list and len(origin) == 2 and all(type(v) is int for v in origin)
                and int(placed[1]) * odb_units == origin[0] * def_units and int(placed[2]) * odb_units == origin[1] * def_units
                and orientations.get(placed[3], placed[3]) == cell.get("orient"),
                "block_region_def", "Final DEF cell placement and orientation differ from the actual containment proof.")
    return None

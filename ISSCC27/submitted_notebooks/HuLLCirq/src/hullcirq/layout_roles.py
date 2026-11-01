"""Read-only functional annotations of the retained, flattened S11 cell layout.

These are evidence annotations, not recovered RTL hierarchy or placement blocks.
Only the frozen structural Verilog/DEF subset is supported. No EDA is invoked.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re


class LayoutRoleError(ValueError):
    """The retained graph cannot be bound safely for annotation."""


def _require(condition, message):
    if not condition:
        raise LayoutRoleError(message)


_ID = r"(?:\\[^\s]+|[A-Za-z_$][\w$]*)"
_BASE = "results/npu_layout_continuous_flow"
_ARCHIVE_MANIFEST_SHA256 = "bc8431548dffe08c4f5c898f89ac9c6aeac3693a3432a75cc8c1054782b7599a"
_INPUTS = {
    "synthesis_json": "artifacts/runs/physical/06-yosys-synthesis/hullcirq_npu.nl.v.json",
    "synthesis_verilog": "attempts/physical-workflow-301f86d714ca4312ac087a9202d3d4d4/working_files/runs/physical/06-yosys-synthesis/hullcirq_npu.nl.v",
    "final_verilog": "artifacts/runs/physical/52-openroad-fillinsertion/hullcirq_npu.nl.v",
    "final_def": "artifacts/runs/physical/53-odb-cellfrequencytables/hullcirq_npu.def",
}
_COLORS = ["#f97316", "#06b6d4", "#8b5cf6", "#ec4899", "#22c55e"]
_PE_COLORS = ["#2563eb", "#0891b2", "#0d9488", "#16a34a", "#65a30d", "#ca8a04", "#ea580c", "#dc2626", "#db2777", "#c026d3", "#9333ea", "#7c3aed", "#4f46e5", "#0284c7", "#059669", "#b45309"]
_LEGACY_ROLE_PROFILE = "legacy_npu_4x4_v1"
_NPU2_ROLE_PROFILE = "npu2_explicit_2x2_v1"
GENERIC_ROLE_PROFILE = "generic_saved_source_v1"
BOUNDARY_INFERENCE_VERSION = "checked_external_output_boundary_v1"
_NPU2_ROLES = ("control", "buffer", "scheduler", "dispatcher", "pe00", "pe01", "pe10", "pe11", "collector", "post", "fifo")
_NPU2_SOURCE_FILES = ["candidate_top.v"] + [f"npu2-{role}.v" for role in _NPU2_ROLES]
_NPU2_COLORS = ("#f97316", "#06b6d4", "#8b5cf6", "#0ea5e9", "#2563eb", "#0891b2", "#16a34a", "#ca8a04", "#dc2626", "#ec4899", "#22c55e")


def _checked_role_profile(role_profile=None):
    selected = _LEGACY_ROLE_PROFILE if role_profile is None else role_profile
    _require(selected in (_LEGACY_ROLE_PROFILE, _NPU2_ROLE_PROFILE, GENERIC_ROLE_PROFILE), "Unsupported layout role profile")
    return selected


def generic_role_context(top_module, bundle, manifest, top_rtl):
    """Describe retained definitions and literal instances, without elaborating RTL.

    An unrecognized/generate declaration is not guessed. It can still produce
    an all-unknown geometry view. The catalogue is not a recovered hierarchy.
    """
    _require(type(bundle) is list and bundle and bundle[0]["module_name"] == top_module,
             "Generic roles require the exact retained source bundle")
    design_nodes = {n["id"]: n for n in manifest["design"]["nodes"]}
    definitions = []
    for node in manifest["nodes"]:
        design = design_nodes[node["node_id"]]
        definitions.append({"node_id": node["node_id"], "module_name": node["module_name"],
                            "file": node["node_id"] + ".v", "label": design.get("name") or node["node_id"],
                            "array_definition": design.get("instance_array") is not None})
    source = re.sub(r"/\*.*?\*/|//[^\n]*", " ", top_rtl, flags=re.S)
    instances = []
    # Source-only lane confirmation is intentionally disabled for generate/for
    # constructs: a lexical declaration is not an elaborated single instance.
    direct_scope = re.search(r"\b(?:generate|for)\b", source) is None
    for definition in definitions:
        module = re.escape(definition["module_name"])
        for match in re.finditer(r"(?<![\w$])" + module + r"\s+(?:#\s*\([^;]*?\)\s*)?(" + _ID + r")\s*\(", source):
            path = _name(match[1])
            if any(item["path"] == path for item in instances):
                # Repeated lexical names in generate scopes are ambiguous.
                continue
            instances.append({"id": "instance:" + path, "path": path,
                              "node_id": definition["node_id"], "module_name": definition["module_name"],
                              "file": definition["file"], "label": str(definition["label"]) + " · " + path,
                              "array_definition": definition["array_definition"],
                              "direct_source_scope": direct_scope})
    context = {"version": GENERIC_ROLE_PROFILE, "top_module": top_module,
            "source_files": [entry["file"] for entry in bundle], "definitions": definitions,
            "instances": sorted(instances, key=lambda item: item["path"]),
            "hierarchy_claim": "literal_retained_RTL_declarations_not_elaboration_or_recovered_ownership"}
    boundary = _generic_boundary_context(manifest, top_rtl, context) if direct_scope else None
    if boundary is not None:
        context["boundary_inference"] = boundary
    return context


def _generic_boundary_context(manifest, top_rtl, context):
    """Admit only the existing checked, direct external wiring subset.

    This establishes output dependency anchors, never recovered cell ownership.
    Unsupported saved designs retain the older named-net annotation behavior.
    """
    from . import generic_global_verification as global_check
    from .rtl_checks import _parse_interface, _strip_comments
    from .verification import content_hash, object_hash
    if 'external_io' not in manifest['design']:
        return None
    for node in manifest['nodes']:
        module, ports, errors = _parse_interface(_strip_comments(node['rtl']))
        if (errors or module != node['module_name'] or
                {p['name']: p for p in ports} != {p['name']: {k: p[k] for k in ('name', 'direction', 'width', 'signed')}
                                               for p in node.get('public_interface', {}).get('ports', [])}):
            return None
    proof = global_check.check_external_wiring(top_rtl, manifest)
    if proof['validation_status'] != 'Passed':
        return None
    roles = {item['path']: item['id'] for item in context['instances']}
    if set(roles) != {item['instance_name'] for item in proof['instances']}:
        return None
    ports = global_check.top_interface(manifest['design'])['ports']
    return {'version': BOUNDARY_INFERENCE_VERSION,
            'top_rtl_sha256': content_hash(top_rtl), 'source_manifest_sha256': object_hash(manifest),
            'wiring_proof_sha256': object_hash(proof), 'ports': ports,
            'connections': [{key: binding[key] for key in ('external_name', 'node_pin', 'direction', 'width', 'signed')} |
                            {'role': roles[binding['instance_name']]} for binding in proof['connections']],
            'scope': 'checked_external_output_dependency_cones_not_exclusive_module_ownership'}


def _checked_generic_context(context):
    _require(type(context) is dict and context.get("version") == GENERIC_ROLE_PROFILE
             and type(context.get("top_module")) is str and type(context.get("source_files")) is list
             and type(context.get("definitions")) is list and type(context.get("instances")) is list,
             "Invalid generic role context")
    _require(len(context["source_files"]) == len(set(context["source_files"]))
             and all(type(name) is str and re.fullmatch(r"[A-Za-z0-9_$.-]+\.v", name) for name in context["source_files"]),
             "Generic roles require unique safe retained source filenames")
    _require(len({item["id"] for item in context["instances"]}) == len(context["instances"]),
             "Duplicate generic instance role")
    boundary = context.get('boundary_inference')
    if boundary is not None:
        _require(type(boundary) is dict and boundary.get('version') == BOUNDARY_INFERENCE_VERSION
                 and type(boundary.get('ports')) is list and type(boundary.get('connections')) is list
                 and all(type(boundary.get(k)) is str and re.fullmatch(r'[0-9a-f]{64}', boundary[k])
                         for k in ('top_rtl_sha256', 'source_manifest_sha256', 'wiring_proof_sha256'))
                 and boundary.get('scope') == 'checked_external_output_dependency_cones_not_exclusive_module_ownership',
                 'Invalid checked boundary inference context')
        ports = {}
        for port in boundary['ports']:
            _require(type(port) is dict and type(port.get('name')) is str
                     and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', port['name'])
                     and port['name'] not in ports and port.get('direction') in ('input', 'output')
                     and type(port.get('width')) is int and 1 <= port['width'] <= 4096
                     and type(port.get('signed')) is bool, 'Invalid checked boundary port')
            ports[port['name']] = port
        known = {item['id'] for item in context['instances'] if item['direct_source_scope']}
        seen = set()
        for binding in boundary['connections']:
            _require(type(binding) is dict and binding.get('role') in known
                     and binding.get('direction') in ('input', 'output')
                     and type(binding.get('width')) is int and 1 <= binding['width'] <= 4096
                     and type(binding.get('signed')) is bool
                     and all(type(binding.get(k)) is str and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', binding[k])
                             for k in ('external_name', 'node_pin'))
                     and binding['external_name'] in ports
                     and all(binding[k] == ports[binding['external_name']][k] for k in ('direction', 'width', 'signed'))
                     and binding['external_name'] not in seen, 'Invalid or duplicate checked external boundary')
            seen.add(binding['external_name'])
    return context


def _boundary_output_seeds(module, mapping, directions, context):
    """Connect checked output bits to unique mapped drivers, without name guesses."""
    boundary = context.get('boundary_inference')
    if boundary is None:
        return {}, {}, None
    expected = {p['name']: p for p in boundary['ports']}
    actual = module.get('ports', {})
    _require(set(actual) == set(expected), 'Mapped top ports differ from checked boundary interface')
    for name, port in expected.items():
        mapped = actual[name]
        _require(mapped.get('direction') == port['direction'] and type(mapped.get('bits')) is list
                 and len(mapped['bits']) == port['width'] and bool(mapped.get('signed', 0)) == port['signed'],
                 'Mapped top port type differs from checked boundary interface')
        _require(module.get('netnames', {}).get(name, {}).get('bits') == mapped['bits'],
                 'Mapped top port bits disagree with its graph-bridged named net')
    drivers = defaultdict(list)
    for name, json_name in mapping.items():
        if name not in directions:
            continue
        cell = module['cells'][json_name]
        for pin, direction in directions[name].items():
            if direction == 'output':
                drivers[cell['connections'][pin][0]].append(name)
    seeds, evidence, skipped = defaultdict(set), defaultdict(list), 0
    for binding in boundary['connections']:
        if binding['direction'] != 'output':
            continue
        for index, bit in enumerate(actual[binding['external_name']]['bits']):
            matches = drivers.get(bit, []) if type(bit) is int else []
            if len(matches) != 1:
                skipped += 1
                continue
            name = matches[0]
            seeds[name].add(binding['role'])
            evidence[name].append({'kind': 'checked_external_output_dependency_anchor',
                                  'external_port': binding['external_name'], 'bit_position': index,
                                  'instance_role': binding['role'], 'node_pin': binding['node_pin'],
                                  'wiring_proof_sha256': boundary['wiring_proof_sha256'],
                                  'inferred_instance_not_source_ownership': True})
    return seeds, evidence, {'version': BOUNDARY_INFERENCE_VERSION, 'unique_driver_anchor_cells': len(seeds),
                            'withheld_output_bits_without_unique_eligible_driver': skipped,
                            'scope': boundary['scope']}


def role_definitions(role_profile=None, role_context=None):
    role_profile = _checked_role_profile(role_profile)
    if role_profile == GENERIC_ROLE_PROFILE:
        context = _checked_generic_context(role_context)
        roles = [{"id": item["id"], "label": item["label"], "color": _NPU2_COLORS[i % len(_NPU2_COLORS)],
                  "description": "Saved module " + item["module_name"] + ", literal instance " + item["path"] +
                      ". Attribution strength is stated separately for each cell; not a placement region.",
                  **({"group": "pe"} if item["array_definition"] else {})}
                 for i, item in enumerate(context["instances"])]
        roles += [{"id": name, "label": label, "color": color} for name, label, color in (
            ("integration", "Top integration", "#475569"), ("clock", "Clock tree", "#eab308"),
            ("physical", "Physical support", "#cbd5e1"), ("unknown", "Unassigned", "#64748b"),
            ("shared", "Shared inferred logic", "#94a3b8"))]
        return roles
    if role_profile == _NPU2_ROLE_PROFILE:
        labels = {
            "control": "Control", "buffer": "Buffer", "scheduler": "Scheduler", "dispatcher": "Dispatcher",
            "pe00": "PE 00 (row 0, column 0)", "pe01": "PE 01 (row 0, column 1)",
            "pe10": "PE 10 (row 1, column 0)", "pe11": "PE 11 (row 1, column 1)",
            "collector": "Collector", "post": "Post", "fifo": "FIFO",
        }
        descriptions = {
            "control": "Job control, configuration, start and completion sequencing.",
            "buffer": "Operand storage and read interfaces for the matrix job.",
            "scheduler": "Saved-K iteration and operand-batch scheduling.",
            "dispatcher": "Independent ready/valid delivery of each batch to four lanes.",
            "pe00": "Signed INT8 multiply and INT32 accumulation lane for row 0, column 0.",
            "pe01": "Signed INT8 multiply and INT32 accumulation lane for row 0, column 1.",
            "pe10": "Signed INT8 multiply and INT32 accumulation lane for row 1, column 0.",
            "pe11": "Signed INT8 multiply and INT32 accumulation lane for row 1, column 1.",
            "collector": "Ordered collection of the four explicit PE results.",
            "post": "Bias and selectable ReLU processing.",
            "fifo": "Output buffering and ready/valid backpressure.",
        }
        roles = [{"id": name, "label": labels[name], "color": color, "description": descriptions[name],
                  **({"group": "pe"} if name.startswith("pe") else {})}
                 for name, color in zip(_NPU2_ROLES, _NPU2_COLORS)]
        roles += [{"id": name, "label": label, "color": color} for name, label, color in (
            ("integration", "Top integration", "#475569"), ("clock", "Clock tree", "#eab308"),
            ("physical", "Physical support", "#cbd5e1"), ("unknown", "Unassigned", "#64748b"),
            ("shared", "Shared inferred logic", "#94a3b8"))]
        return roles
    roles = [{"id": name, "label": name.title(), "color": color} for name, color in
             zip(("control", "buffer", "scheduler", "post", "fifo"), _COLORS)]
    roles += [{"id": f"pe:{i}", "label": f"PE {i} (row {i // 4}, column {i % 4})", "color": color}
              for i, color in enumerate(_PE_COLORS)]
    roles += [{"id": name, "label": label, "color": color} for name, label, color in (
        ("integration", "Top integration", "#475569"), ("clock", "Clock tree", "#eab308"),
        ("physical", "Physical support", "#cbd5e1"), ("unknown", "Unassigned", "#64748b"),
        ("shared", "Shared inferred logic", "#94a3b8"))]
    return roles


def _name(value):
    return value.strip().removeprefix("\\")


def _net(expression):
    expression = expression.strip()
    constant = re.fullmatch(r"1\s*'\s*[bB]\s*([01xXzZ])", expression)
    if constant:
        return "const:" + constant[1].lower()
    if expression.startswith("\\"):
        _require(re.fullmatch(r"\\[^\s]+\s*", expression) is not None, "Unsupported escaped net expression")
        return _name(expression)
    _require(re.fullmatch(r"[A-Za-z_$][\w$]*(?:\s*\[\s*\d+\s*\])?", expression) is not None,
             "Only scalar named pin connections and individual bus bits are supported")
    return re.sub(r"\s+", "", expression)


def parse_structural_verilog(text):
    """Parse complete flat, scalar named-port cells and scalar wire aliases."""
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    _require(text.count("endmodule") == 1, "Require one complete flat module")
    text = text.replace("endmodule", "").strip()
    statements = text.split(";")
    _require(not statements[-1].strip(), "Unterminated structural statement")
    match = re.fullmatch(r"\s*module\s+(\w+)\s*\((.*?)\)\s*", statements[0], re.S)
    _require(match is not None, "Unsupported module header")
    top = match[1]
    cells, aliases, declarations = {}, [], set()
    for statement in statements[1:-1]:
        statement = statement.strip()
        declaration = re.fullmatch(r"(?:input|output|inout|wire)\s*(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*(" + _ID + r")\s*", statement)
        if declaration:
            hi, lo, name = declaration.groups()
            if hi is None:
                declarations.add(_name(name))
            else:
                declarations.update(f"{_name(name)}[{i}]" for i in range(min(int(hi), int(lo)), max(int(hi), int(lo)) + 1))
            continue
        assign = re.fullmatch(r"assign\s+(.+?)\s*=\s*(.+)", statement, re.S)
        if assign:
            left, right = _net(assign[1]), _net(assign[2])
            _require(not left.startswith("const:"), "An alias must drive a named wire")
            aliases.append((left, right))
            continue
        instance = re.fullmatch(r"(" + _ID + r")\s+(" + _ID + r")\s*\((.*)\)", statement, re.S)
        _require(instance is not None, "Unsupported structural statement")
        master, name, body = instance.groups()
        name, master = _name(name), _name(master)
        _require(name not in cells, "Duplicate structural instance")
        pins = {}
        for binding in body.split(",") if body.strip() else []:
            pin = re.fullmatch(r"\s*\.([A-Za-z_$][\w$]*)\s*\(([^()]*)\)\s*", binding, re.S)
            _require(pin is not None and pin[1] not in pins, "Invalid or duplicate named pin")
            pins[pin[1]] = _net(pin[2])
        cells[name] = {"master": master, "pins": pins}
    _require(cells, "Empty structural graph")
    parent = {}

    def find(value):
        parent.setdefault(value, value)
        if parent[value] != value:
            parent[value] = find(parent[value])
        return parent[value]

    for left, right in aliases:
        a, b = find(left), find(right)
        if a != b:
            parent[max(a, b)] = min(a, b)
    for cell in cells.values():
        cell["pins"] = {pin: find(net) for pin, net in cell["pins"].items()}
    return {"top": top, "cells": cells, "aliases": {net: find(net) for net in parent}, "declarations": declarations}


def parse_def_components(text):
    block = re.search(r"\bCOMPONENTS\s+(\d+)\s*;(.*?)\bEND\s+COMPONENTS\b", text, re.S)
    _require(block is not None, "Missing DEF component table")
    components = {}
    for statement in block[2].split(";"):
        if not statement.strip():
            continue
        match = re.match(r"\s*-\s+(\S+)\s+(\S+)(?:\s|$)", statement)
        _require(match is not None and _name(match[1]) not in components, "Malformed or duplicate DEF component")
        components[_name(match[1])] = _name(match[2])
    _require(len(components) == int(block[1]), "DEF component count mismatch")
    return components


def _json_graph(module):
    cells = {}
    for name, cell in module["cells"].items():
        pins = {}
        for pin, bits in cell["connections"].items():
            _require(len(bits) == 1, "Only mapped scalar cell pins are supported")
            bit = bits[0]
            _require(type(bit) in (int, str), "Invalid JSON bit identifier")
            pins[pin] = bit if type(bit) is int else "const:" + bit
        cells[name] = {"master": cell["type"], "pins": pins}
    labels = defaultdict(set)
    for name, net in module["netnames"].items():
        if net.get("hide_name"):
            continue
        bits = net["bits"]
        for index, bit in enumerate(bits):
            label = name if len(bits) == 1 else f"{name}[{net.get('offset', 0) + (len(bits) - 1 - index if net.get('upto') else index)}]"
            labels[bit if type(bit) is int else "const:" + bit].add(label)
    return cells, labels


def _signature(cell, net_map):
    if any(net not in net_map for net in cell["pins"].values()):
        return None
    return cell["master"], tuple(sorted((pin, net_map[net]) for pin, net in cell["pins"].items()))


def bridge_synthesis(module, synthesis):
    """Match graphs using named anchors and unique connectivity, never cell indices."""
    jc, labels = _json_graph(module)
    vc = synthesis["cells"]
    _require(len(jc) == len(vc) and Counter(c["master"] for c in jc.values()) == Counter(c["master"] for c in vc.values()),
             "Synthesis JSON/Verilog cell inventory mismatch")
    label_bits = {}
    for bit, names in labels.items():
        for name in names:
            _require(name not in label_bits or label_bits[name] == bit, "Ambiguous named JSON bit")
            label_bits[name] = bit
    aliases = synthesis["aliases"]
    anchors = {}
    for label, bit in label_bits.items():
        net = aliases.get(label, label)
        if label in synthesis["declarations"]:
            _require(net not in anchors or anchors[net] == bit, "Conflicting structural aliases")
            anchors[net] = bit
    graphs = [jc, vc]
    neighbors, net_colors = [], []
    for side, cells in enumerate(graphs):
        adjacent = defaultdict(list)
        for name, cell in cells.items():
            for pin, net in cell["pins"].items():
                adjacent[net].append((name, pin))
        neighbors.append(adjacent)
        net_colors.append({net: ("anchor", str(net)) if side == 0 and (net in labels or str(net).startswith("const:"))
                           else ("anchor", str(anchors.get(net, net))) if side == 1 and (net in anchors or str(net).startswith("const:"))
                           else ("unknown",) for net in adjacent})
    rounds = 0
    for rounds in range(1, 33):
        pool = {}

        def color(value):
            if value not in pool:
                pool[value] = len(pool)
            return pool[value]

        cell_colors = [{name: color((cell["master"], tuple(sorted((pin, net_colors[side][net]) for pin, net in cell["pins"].items()))))
                        for name, cell in cells.items()} for side, cells in enumerate(graphs)]
        new_colors = []
        for side, adjacent in enumerate(neighbors):
            new_colors.append({net: color((net_colors[side][net], tuple(sorted((pin, cell_colors[side][name]) for name, pin in links))))
                               for net, links in adjacent.items()})
        net_colors = new_colors
        groups = [defaultdict(list), defaultdict(list)]
        for side in (0, 1):
            for net, value in net_colors[side].items():
                groups[side][value].append(net)
        net_map = dict(anchors)
        for value, nets in groups[1].items():
            if len(nets) == 1 and len(groups[0].get(value, [])) == 1:
                net_map[nets[0]] = groups[0][value][0]
        if all(net in net_map for cell in vc.values() for net in cell["pins"].values()):
            break
    net_map.update({f"const:{v}": f"const:{v}" for v in "01xz"})
    identity = {net: net for cell in jc.values() for net in cell["pins"].values()}
    js, vs = defaultdict(list), defaultdict(list)
    for name, cell in jc.items():
        js[_signature(cell, identity)].append(name)
    for name, cell in vc.items():
        signature = _signature(cell, net_map)
        _require(signature is not None, "Anonymous net connectivity bridge is unresolved; no index mapping is guessed")
        vs[signature].append(name)
    _require({key: len(value) for key, value in js.items()} == {key: len(value) for key, value in vs.items()},
             "Synthesis JSON/Verilog full pin connectivity mismatch")
    mapping = {vs[key][0]: values[0] for key, values in js.items() if len(values) == len(vs[key]) == 1}
    return mapping, {"method": "named_anchor_graph_refinement_then_unique_full_master_pin_signature",
                     "cells_checked": len(jc), "uniquely_bridged_cells": len(mapping),
                     "ambiguous_cells": len(jc) - len(mapping), "net_bits_checked": len(identity), "refinement_rounds": rounds}


def _role(net, role_profile=None, role_context=None):
    role_profile = _checked_role_profile(role_profile)
    if role_profile == GENERIC_ROLE_PROFILE:
        matches = [item for item in role_context["instances"] if net.startswith(item["path"] + ".")]
        return max(matches, key=lambda item: len(item["path"]))["id"] if matches else None
    if role_profile == _NPU2_ROLE_PROFILE:
        # These flattened aliases name the receiving block (or only the top
        # wire), while the unchanged candidate_top.v establishes Scheduler as
        # their driver.  Match only the exact retained scalar-bit grammar.
        if re.fullmatch(r"(?:buffer\.read_index|batch_data)\[\d+\]", net):
            return "scheduler"
        if net.startswith("buffer.read_index") or net.startswith("batch_data"):
            return None
        match = re.match(r"^(control|buffer|scheduler|dispatcher|pe00|pe01|pe10|pe11|collector|post|fifo)\.", net)
        return match[1] if match else None
    match = re.match(r"^pe_inst\[(\d+)\]\.u_pe\.", net)
    if match and int(match[1]) < 16:
        return "pe:" + str(int(match[1]))
    match = re.match(r"^u_(control|buffer|scheduler|post|fifo)\.", net)
    return match[1] if match else None


def _source_role(source, role_profile=None, role_context=None):
    role_profile = _checked_role_profile(role_profile)
    if role_profile == GENERIC_ROLE_PROFILE:
        files = {name for name in role_context["source_files"]
                 if re.search(r"(?:^|[\\/|])" + re.escape(name) + r":\d", source)}
        if len(files) != 1:
            return None
        filename = next(iter(files))
        if filename == "candidate_top.v":
            return "integration"
        instances = [item for item in role_context["instances"] if item["file"] == filename]
        if len(instances) == 1 and instances[0]["direct_source_scope"]:
            return instances[0]["id"]
        return "definition:" + filename
    if role_profile == _NPU2_ROLE_PROFILE:
        files = re.findall(r"(?:^|[\\/|])((?:npu2-(?:control|buffer|scheduler|dispatcher|pe00|pe01|pe10|pe11|collector|post|fifo)|candidate_top)\.v):", source)
        roles = {"integration" if name == "candidate_top.v" else name[5:-2] for name in files}
        return next(iter(roles)) if len(roles) == 1 else None
    files = re.findall(r"(?:^|[\/|])((?:node-(?:control|buffer|scheduler|post|fifo|pe)|candidate_top)\.v):", source)
    roles = {"integration" if name == "candidate_top.v" else name[5:-2] for name in files}
    return next(iter(roles)) if len(roles) == 1 else None


def _sequential(master):
    return re.search(r"__(?:s?df[a-z]*|edf[a-z]*|dl[crsx][a-z]*)_\d+$", master) is not None


def annotate_cells(module, synthesis, final, components, role_profile=None, annotation_policy=None, role_context=None):
    """Pure graph annotation; all final instances must match the DEF inventory."""
    role_profile = _checked_role_profile(role_profile)
    generic = role_profile == GENERIC_ROLE_PROFILE
    if generic:
        _checked_generic_context(role_context)
    _require(annotation_policy in (None, "changed_family_unknown_v1"), "Unsupported layout annotation policy")
    _require(final["top"] == synthesis["top"], "Top module mismatch")
    fc, sc = final["cells"], synthesis["cells"]
    _require(set(fc) == set(components), "Final DEF/netlist instance set mismatch")
    _require(all(cell["master"] == components[name] for name, cell in fc.items()), "Final DEF/netlist master mismatch")
    _require(set(sc).issubset(fc), "Synthesis instance absent from final layout")
    family_changes = {}
    for name, original in sc.items():
        current = fc[name]
        same_family = re.sub(r"_\d+$", "", original["master"]) == re.sub(r"_\d+$", "", current["master"])
        _require(set(original["pins"]) == set(current["pins"]) and
                 (same_family or annotation_policy == "changed_family_unknown_v1"),
                 "Retained instance changed logical master family or pin interface")
        if not same_family:
            family_changes[name] = {"id": name, "synthesis_master": original["master"], "final_master": current["master"]}
    mapping, bridge = bridge_synthesis(module, synthesis)
    seeds, evidence, source_roles = {}, defaultdict(list), {}
    directions = {}
    resized = []
    for name, jc_name in mapping.items():
        # No source ownership, pin direction or fanin inference crosses this
        # boundary. Same pin names do NOT establish equivalent cell semantics.
        if name in family_changes:
            continue
        cell = module["cells"][jc_name]
        _require(name in fc, "Synthesis instance absent from final layout")
        original, current = sc[name], fc[name]
        family = lambda master: re.sub(r"_\d+$", "", master)
        _require(family(original["master"]) == family(current["master"]) and set(original["pins"]) == set(current["pins"]),
                 "Retained instance changed logical master family or pin interface")
        if original["master"] != current["master"]:
            resized.append({"id": name, "synthesis_master": original["master"], "final_master": current["master"]})
        directions[name] = cell["port_directions"]
        output_roles = {_role(net, role_profile, role_context) for pin, net in original["pins"].items() if cell["port_directions"].get(pin) == "output"}
        output_roles.discard(None)
        source = cell.get("attributes", {}).get("src")
        source_role = _source_role(source, role_profile, role_context) if source else None
        _require(generic or not source_role or not output_roles or all(
                 role.startswith("pe:") if source_role == "pe" else role == source_role for role in output_roles),
                 "Source-role and named-output role conflict")
        if source:
            # Generic published evidence retains file/line provenance, not the
            # private build host/account prefix present in Yosys src strings.
            shown_source = "|".join(re.sub(r"^.*[\\/]", "", part) for part in source.split("|")) if generic else source
            evidence[name].append({"kind": "unique_synthesis_src_attribute", "json_cell": jc_name, "src": shown_source})
        if source_role:
            source_roles[name] = source_role
        if generic and source_role and source_role.startswith("definition:"):
            filename = source_role.removeprefix("definition:")
            allowed = {item["id"] for item in role_context["instances"] if item["file"] == filename}
            selected = output_roles & allowed
            if selected:
                seeds[name] = selected
                evidence[name].append({"kind": "shared_definition_named_instance_output", "roles": sorted(selected),
                                       "source_file": filename, "inferred_instance_not_source_ownership": True})
        elif source_role and source_role != "pe":
            seeds[name] = {source_role}
        elif output_roles:
            seeds[name] = output_roles
            evidence[name].append({"kind": "role_named_output_net", "nets": sorted(net for pin, net in original["pins"].items()
                                  if cell["port_directions"].get(pin) == "output" and _role(net, role_profile, role_context))})
    boundary_summary = None
    if generic:
        boundary_seeds, boundary_evidence, boundary_summary = _boundary_output_seeds(module, mapping, directions, role_context)
        for name, candidates in boundary_seeds.items():
            source_role = source_roles.get(name)
            # Unique source provenance has priority over a downstream boundary
            # dependency. A pass-through output does not transfer ownership.
            if source_role and not source_role.startswith('definition:'):
                candidates &= {source_role}
            elif source_role:
                filename = source_role.removeprefix('definition:')
                candidates &= {item['id'] for item in role_context['instances'] if item['file'] == filename}
            if candidates:
                seeds.setdefault(name, set()).update(candidates)
                evidence[name].extend(item for item in boundary_evidence[name] if item['instance_role'] in candidates)
    # Infer only backward combinational cones ending at explicit role anchors.
    # Sequential outputs are boundaries; this is not recovered module hierarchy.
    drivers = defaultdict(list)
    for name, pins in directions.items():
        for pin, direction in pins.items():
            if direction == "output":
                drivers[sc[name]["pins"][pin]].append(name)
    inferred = defaultdict(set)
    for anchor, roles in seeds.items():
        pending = [net for pin, net in sc[anchor]["pins"].items() if directions[anchor].get(pin) == "input" and pin not in ("CLK", "GATE")]
        visited = set()
        while pending:
            net = pending.pop()
            for name in drivers.get(net, []):
                if name in visited or name in seeds or _sequential(sc[name]["master"]):
                    continue
                visited.add(name)
                inferred[name].update(roles)
                pending.extend(value for pin, value in sc[name]["pins"].items() if directions[name].get(pin) == "input")
    cells = []
    for name, cell in sorted(fc.items()):
        reasons = list(evidence[name])
        roles = seeds.get(name, inferred.get(name, set()))
        role, status = "unknown", "unknown"
        if name in family_changes:
            reasons.append({"kind": "changed_logical_family_attribution_withheld",
                            **family_changes[name], "same_pin_set": True,
                            "attribution_withheld": True})
        elif roles:
            role = next(iter(roles)) if len(roles) == 1 else "shared"
            status = "source_confirmed" if source_roles.get(name) == role else "source_and_connectivity" if (source_roles.get(name) == "pe" and role.startswith("pe:")) or (generic and source_roles.get(name, "").startswith("definition:") and role != "shared") else "connectivity_inferred"
            if name in inferred:
                reasons.append({"kind": "bounded_combinational_fanin_cone", "roles": sorted(roles), "sequential_boundaries": True})
        elif re.fullmatch(r"sky130_fd_sc_hd__(?:fill|decap|tapvpwrvgnd|diode)_\d+", cell["master"]):
            role, status = "physical", "physical_inferred"
            reasons.append({"kind": "physical_support_master", "master": cell["master"]})
        elif name.startswith(("clkbuf_", "clkload_")):
            role, status = "clock", "clock_inferred"
            reasons.append({"kind": "CTS_instance_prefix", "prefix": name.split("_")[0]})
        if name in mapping and name not in family_changes:
            reasons.append({"kind": "retained_synthesis_instance", "synthesis_master": sc[name]["master"], "final_master": cell["master"],
                            "same_logical_family_and_pin_set": True})
        if role == "unknown":
            reasons.append({"kind": "no_unique_supported_functional_attribution"})
        cells.append({"id": name, "master": cell["master"], "role": role, "status": status, "evidence": reasons})
    summary = {"final_cells": len(fc), "synthesis_cells": len(sc), "by_role": dict(sorted(Counter(c["role"] for c in cells).items())),
                   "by_status": dict(sorted(Counter(c["status"] for c in cells).items())), "bridge": bridge, "resized_cells": resized}
    if annotation_policy is not None:
        summary["annotation_policy"] = annotation_policy
        summary["unattributed_family_changes"] = list(family_changes.values())
    if boundary_summary is not None:
        summary['checked_boundary_inference'] = boundary_summary
    return cells, summary


def source_profile_values(profile=None):
    """Explicit immutable source bundle; old invocation keeps its exact pins."""
    if profile is None:
        return {'source_root': _BASE, 'source_manifest_sha256': _ARCHIVE_MANIFEST_SHA256,
                'layout_run_id': 'physical-workflow-f678bc2dd59949219132a7de80eb12af',
                'inputs': _INPUTS, 'expected_final_cells': 66315, 'expected_synthesis_cells': 9369,
                'gds_relative_path': 'artifacts/runs/physical/57-magic-streamout/hullcirq_npu.gds'}
    expected = {'source_root', 'source_manifest_sha256', 'layout_run_id', 'inputs',
                'expected_final_cells', 'expected_synthesis_cells', 'gds_relative_path'}
    valid_keys = set(profile) if type(profile) is dict else set()
    generic = type(profile) is dict and profile.get('role_profile') == GENERIC_ROLE_PROFILE
    if generic:
        _require(valid_keys == expected | {'role_profile', 'annotation_policy', 'role_context'}
                 and type(profile.get('inputs')) is dict
                 and set(profile['inputs']) in (set(_INPUTS), {'final_verilog', 'final_def'}),
                 'Require the complete generic immutable role-map source profile')
        _checked_generic_context(profile['role_context'])
    _require(generic or valid_keys in (expected, expected | {'role_profile'}, expected | {'role_profile', 'annotation_policy'}) and set(profile['inputs']) == set(_INPUTS),
             'Require the complete explicit immutable role-map source profile')
    if 'role_profile' in profile:
        _require(profile['role_profile'] in (_NPU2_ROLE_PROFILE, GENERIC_ROLE_PROFILE), 'Unsupported explicit layout role profile')
    if 'annotation_policy' in profile:
        _require(profile['annotation_policy'] == 'changed_family_unknown_v1', 'Unsupported layout annotation policy')
    _require(re.fullmatch(r'results/[A-Za-z0-9_-]+', profile['source_root']) is not None
             and re.fullmatch(r'[0-9a-f]{64}', profile['source_manifest_sha256']) is not None
             and re.fullmatch(r'physical-workflow-[0-9a-f]+', profile['layout_run_id']) is not None
             and type(profile['expected_final_cells']) is int and profile['expected_final_cells'] > 0
             and type(profile['expected_synthesis_cells']) is int
             and profile['expected_synthesis_cells'] >= (0 if generic else 1),
             'Invalid immutable role-map source profile')
    return profile


def collect_layout_roles(project_root: Path, source_profile=None) -> dict:
    """Read the adopted archive only, verifying every input against its manifest."""
    root = Path(project_root).resolve()
    profile = source_profile_values(source_profile)
    role_profile = _checked_role_profile(profile.get('role_profile'))
    base = profile['source_root']
    archive = root / base
    manifest_path = archive / "manifest.json"
    manifest_raw = manifest_path.read_bytes()
    _require(hashlib.sha256(manifest_raw).hexdigest() == profile['source_manifest_sha256'], "Adopted archive manifest identity mismatch")
    manifest = json.loads(manifest_raw)
    _require(manifest.get("validation_status") == "Passed", "Require the adopted Passed layout archive")
    if source_profile is not None:
        _require(manifest.get('layout_run_id') == profile['layout_run_id'], 'Role-map profile and archive layout disagree')
    inputs, provenance = {}, {}
    for key, relative in profile['inputs'].items():
        path = archive / relative
        _require(path.resolve().is_relative_to(archive.resolve()), "Input escapes the retained archive")
        raw = path.read_bytes()
        record = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        _require(record == manifest["files"].get(relative), "Retained input hash/size mismatch: " + key)
        inputs[key] = raw.decode("utf-8")
        provenance[key] = {"path": (base + "/" + relative), **record}
    source_rtl, source_texts = {}, {}
    generic = role_profile == GENERIC_ROLE_PROFILE
    context = profile.get('role_context')
    source_files = (context['source_files'] if generic else _NPU2_SOURCE_FILES if role_profile == _NPU2_ROLE_PROFILE else
                    ["candidate_top.v"] + [f"node-{name}.v" for name in ("control", "buffer", "scheduler", "post", "fifo", "pe")])
    for name in source_files:
        relative = "artifacts/" + name
        path = archive / relative
        _require(path.resolve().is_relative_to(archive.resolve()), "Source RTL escapes the retained archive")
        raw = path.read_bytes()
        record = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        _require(record == manifest["files"].get(relative), "Retained source RTL hash/size mismatch")
        source_rtl[name] = {"path": base + "/" + relative, **record}
        source_texts[name] = raw.decode('utf-8')
    top_module = context['top_module'] if generic else "hullcirq_npu2_top" if role_profile == _NPU2_ROLE_PROFILE else "hullcirq_npu"
    final = parse_structural_verilog(inputs["final_verilog"])
    components = parse_def_components(inputs["final_def"])
    _require(final['top'] == top_module, "Final mapped netlist top disagrees with retained source")
    if generic:
        binding_path = archive / 'source_binding.json'
        binding_raw = binding_path.read_bytes()
        _require(manifest['files'].get('source_binding.json') == {'bytes': len(binding_raw), 'sha256': hashlib.sha256(binding_raw).hexdigest()},
                 "Generic source binding hash changed")
        binding = json.loads(binding_raw)
        _require(binding.get('role_context') == context, "Generic role context differs from its pinned source binding")
        if 'boundary_inference' in context:
            raw = (archive / 'layout_record.json').read_bytes()
            _require(manifest['files'].get('layout_record.json') == {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
                     'Checked boundary original layout record hash changed')
            saved = json.loads(raw)
            _require(saved.get('id') == manifest['layout_run_id']
                     and saved.get('global_rtl') == source_texts['candidate_top.v']
                     and all(node['rtl'] == source_texts.get(node['node_id'] + '.v') for node in saved['source_manifest']['nodes']),
                     'Checked boundary original source bytes disagree')
            rebuilt = generic_role_context(top_module, saved['checks']['source_bundle'], saved['source_manifest'], saved['global_rtl'])
            _require(rebuilt == context, 'Checked boundary inference differs from exact retained source reconstruction')
    if 'synthesis_json' in inputs:
        document = json.loads(inputs["synthesis_json"])
        _require(top_module in document["modules"] and all(name == top_module or
                 int(value.get("attributes", {}).get("blackbox", "0"), 2) == 1
                 for name, value in document["modules"].items()), "Require one mapped top and only blackbox cell libraries")
        synthesis = parse_structural_verilog(inputs["synthesis_verilog"])
        cells, summary = annotate_cells(document["modules"][top_module], synthesis, final, components, role_profile,
                                        profile.get('annotation_policy'), context)
    else:
        _require(generic and set(final['cells']) == set(components)
                 and all(final['cells'][name]['master'] == master for name, master in components.items()),
                 "Final DEF/netlist instance/master inventory mismatch")
        cells = [{"id": name, "master": cell['master'], "role": "unknown", "status": "unknown",
                  "evidence": [{"kind": "no_retained_synthesis_attribution", "attribution_withheld": True}]}
                 for name, cell in sorted(final['cells'].items())]
        summary = {"final_cells": len(cells), "synthesis_cells": 0, "by_role": {"unknown": len(cells)},
                   "by_status": {"unknown": len(cells)}, "bridge": {"method": "unavailable_no_attribution_claimed"}, "resized_cells": []}
    _require(summary["final_cells"] == profile['expected_final_cells'] and summary["synthesis_cells"] == profile['expected_synthesis_cells'], "Frozen actual design cell count mismatch")
    result = {"schema_version": 1, "record_kind": "read_only_functional_annotations_of_actual_flattened_S11_cells",
              "layout_run_id": manifest["layout_run_id"], "top_module": top_module,
              "cells": cells, "roles": role_definitions(role_profile, context), "summary": summary,
              "provenance": {"archive_manifest": {"path": base + "/manifest.json", "sha256": hashlib.sha256(manifest_raw).hexdigest()}, "inputs": provenance, "source_rtl": source_rtl},
              "notes": ["Colors annotate actual final DEF-bound cells, not rectangular block placement or recovered hierarchy.",
                        "Only source_confirmed cells have a unique retained source attribute identifying that role; PE lane assignment also uses named connectivity.",
                        "Connectivity cones are an inference bounded by role anchors and sequential cells, not a proof of original module membership.",
                        "Clock/physical support classifications are explicit name/master inferences. Shared and unassigned cells remain visible.",
                        "S14 simulation, EDA execution, design changes and new placement are not performed."]}
    if role_profile == _NPU2_ROLE_PROFILE:
        result["role_profile"] = role_profile
        result["notes"][1] = "Only source_confirmed cells have a unique retained source attribute identifying one of the eleven explicit GUI nodes."
    if generic:
        result['role_profile'] = role_profile
        result['role_context'] = context
        result['notes'][1] = "Definition/file provenance is separate from instance attribution. Shared definitions need named-net evidence to infer individual instances; unproved correspondence stays unknown."
        if 'boundary_inference' in context:
            result['notes'][1] = "Definition/file provenance is separate from instance attribution. Checked direct external-output connections may anchor bounded dependency-cone inference; this is not exclusive cell/module ownership."
        result['notes'].append("The generic instance catalogue comes from literal saved RTL declarations, not RTL elaboration. Unsupported hierarchy/generate syntax never creates invented instance ownership.")
    if profile.get('annotation_policy'):
        result['notes'].append("Changed logical-family instances remain unknown; source attribution and fanin inference stop at them. Same pin names are not semantic equivalence.")
    return result

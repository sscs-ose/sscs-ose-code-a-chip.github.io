"""Immutable, version-pinned logical components; imported evidence is provenance.

Packages contain design data, never runnable commands. Instantiation expands a
graph with fresh node/port/edge/module identities and records a logical group.
It transfers no RTL candidate, tool run, verification result, or adoption.
"""
from __future__ import annotations

import copy
import base64
import gzip
import hashlib
import re
import zlib
from pathlib import Path

from .domain import DomainError, _identifier, revision_hashes, validate_shape, validate_stage
from .store import ProjectStore, strict_loads, utc_now, new_id, _validate_saved_state
from .workspace import canonical, checked_name, digest, write_json

_COMPONENT_ID = re.compile(r"^component-[0-9a-f]{32}$")
MAX_PACKAGE_BYTES = 128 * 1024 ** 2
MAX_SOURCE_HISTORY_BYTES = 512 * 1024 ** 2


def _project_external_io(snapshot, selected):
    """Keep only explicitly source-bound subset terminals, never infer others."""
    if "external_io" not in snapshot:
        return None
    value = copy.deepcopy(snapshot["external_io"])
    if selected == {node["id"] for node in snapshot["nodes"]}:
        return value
    value["connections"] = [connection for connection in value["connections"] if connection["node_id"] in selected]
    referenced = {connection["external_port_id"] for connection in value["connections"]}
    value["ports"] = [port for port in value["ports"] if port["id"] in referenced]
    return value


def validate_package(package):
    if type(package) is not dict or package.get("format") != "hullcirq-component" or package.get("version") != "1":
        raise DomainError("invalid_component", "Unsupported component package.")
    if len(canonical(package)) > MAX_PACKAGE_BYTES:
        raise DomainError("component_limit", "Component packages are limited to 128 MiB.", 413)
    component = package.get("component")
    if type(component) is not dict or type(component.get("id")) is not str or not _COMPONENT_ID.fullmatch(component["id"]) or type(component.get("version")) is not int or component["version"] < 1:
        raise DomainError("invalid_component", "Component identity or version is invalid.")
    checked_name(component.get("name"), "Component name")
    if package.get("sha256") != digest({k: v for k, v in package.items() if k != "sha256"}):
        raise DomainError("component_checksum", "Component package checksum does not match.")
    design = package.get("design")
    validate_shape(design)
    if not design["nodes"]:
        raise DomainError("empty_component", "A component must contain at least one node.")
    errors = [d for d in validate_stage(design, "graph_editor") if d["severity"] == "error"]
    if errors:
        raise DomainError("invalid_component_graph", errors[0]["message"])
    ports = package.get("public_ports")
    if type(ports) is not list or len(ports) > 100000:
        raise DomainError("invalid_component", "Public ports must be an array.")
    nodes = {node["id"]: node for node in design["nodes"]}
    names, endpoints = set(), set()
    used = {(edge[end]["node_id"], edge[end]["port_id"]) for edge in design["edges"] for end in ("source", "target")}
    for port in ports:
        if type(port) is not dict or type(port.get("name")) is not str or not _identifier(port["name"]) or port["name"] in names:
            raise DomainError("invalid_component_port", "Public port names must be unique Verilog identifiers.")
        node_id, port_id = port.get("node_id"), port.get("port_id")
        if type(node_id) is not str or type(port_id) is not str:
            raise DomainError("invalid_component_port", "Public port endpoints must be string IDs.")
        node = nodes.get(node_id)
        source = next((p for p in node["ports"] if p["id"] == port_id), None) if node else None
        endpoint = (node_id, port_id)
        if source is None or endpoint in endpoints:
            raise DomainError("invalid_component_port", "Public port refers to a missing or repeated graph endpoint.")
        for field in ("direction", "width", "signed", "protocol", "clock", "reset"):
            if type(port.get(field)) is not type(source[field]) or port[field] != source[field]:
                raise DomainError("component_contract_mismatch", "Public port contract must exactly match its source graph port.")
        if source.get("sideband") != port.get("sideband"):
            raise DomainError("component_contract_mismatch", "Public raw-sideband contract differs from the graph.")
        if endpoint in used:
            raise DomainError("invalid_component_port", "Public ports must be unconnected component boundary endpoints.")
        names.add(port["name"])
        endpoints.add(endpoint)
    boundaries = {(n["id"], p["id"]) for n in design["nodes"] for p in n["ports"]} - used
    if endpoints != boundaries:
        raise DomainError("component_boundary_incomplete", "Every unconnected component boundary must be declared as a public port.")
    provenance = package.get("source")
    if type(provenance) is not dict or provenance.get("evidence_scope") != "Source provenance only; target validation not run.":
        raise DomainError("invalid_component", "Component provenance must explicitly limit imported verification evidence.")
    for key in ("project_id", "system_id", "revision_id", "semantic_hash", "layout_hash", "captured_at"):
        if type(provenance.get(key)) is not str or not provenance[key]:
            raise DomainError("invalid_component", "Component source identity is incomplete.")
    snapshot = package.get("source_snapshot")
    validate_shape(snapshot)
    if revision_hashes(snapshot) != {k: provenance[k] for k in ("semantic_hash", "layout_hash")}:
        raise DomainError("component_source_mismatch", "Original source snapshot does not match recorded hashes.")
    # Never trust a graph detached from the claimed source snapshot.
    source_nodes = {n["id"]: n for n in snapshot["nodes"]}
    selected = set(nodes)
    for node in design["nodes"]:
        expected = copy.deepcopy(source_nodes.get(node["id"]))
        if expected is None:
            raise DomainError("component_source_mismatch", "Component node is absent from the source snapshot.")
        if expected["parent_id"] not in selected:
            expected["parent_id"] = None
        if expected != node:
            raise DomainError("component_source_mismatch", "Component node differs from the recorded source snapshot.")
    expected_edges = [e for e in snapshot["edges"] if e["source"]["node_id"] in selected and e["target"]["node_id"] in selected]
    if design["edges"] != expected_edges or design["settings"] != snapshot["settings"]:
        raise DomainError("component_source_mismatch", "Component edges or settings differ from their source snapshot.")
    expected_io = _project_external_io(snapshot, selected)
    if (("external_io" in design) != (expected_io is not None)
            or expected_io is not None and design["external_io"] != expected_io):
        raise DomainError("component_source_mismatch", "Component external connections differ from the exact source projection.")
    histories = package.get("source_history")
    if type(histories) is not list or not histories:
        raise DomainError("invalid_component_history", "Component source history snapshot is required.")
    actual_files, total = [], 0
    for entry in histories:
        if type(entry) is not dict or type(entry.get("file")) is not str or not re.fullmatch(r"[A-Za-z0-9_-]+\.json", entry["file"]) or entry.get("encoding") != "gzip+base64":
            raise DomainError("invalid_component_history", "Source history entries must be plain JSON filenames.")
        size = entry.get("size")
        if type(size) is not int or size < 0 or total + size > MAX_SOURCE_HISTORY_BYTES or any(f["file"] == entry["file"] for f in actual_files):
            raise DomainError("invalid_component_history", "Source history exceeds its limit or repeats a file.")
        try:
            compressed = base64.b64decode(entry.get("data"), validate=True)
            decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
            data = decoder.decompress(compressed, size + 1)
            if len(data) != size or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                raise ValueError("Invalid compressed size")
        except (TypeError, ValueError, zlib.error) as error:
            raise DomainError("invalid_component_history", "Source history compression is invalid.") from error
        if hashlib.sha256(data).hexdigest() != entry.get("sha256"):
            raise DomainError("component_history_checksum", "A source history checksum does not match.")
        if entry["file"] == "state.json":
            try:
                state = strict_loads(data.decode("utf-8"))
            except UnicodeError as error:
                raise DomainError("invalid_component_history", "Source state snapshot must be UTF-8 JSON.") from error
            if type(state) is not dict:
                raise DomainError("invalid_component_history", "Source state snapshot must be an object.")
            _validate_saved_state(state)
            if state.get("design") != snapshot or state.get("revision", {}).get("id") != provenance["revision_id"]:
                raise DomainError("component_source_mismatch", "Source history state differs from the captured graph and revision.")
        total += size
        actual_files.append({"file": entry["file"], "size": size, "sha256": entry["sha256"], "scope": "Source provenance reference only"})
    if not any(f["file"] == "state.json" for f in actual_files) or provenance.get("history_files") != actual_files:
        raise DomainError("component_source_mismatch", "Source history manifest does not match its preserved files.")
    return package


class ComponentLibrary:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def _path(self, component_id, version):
        if type(component_id) is not str or not _COMPONENT_ID.fullmatch(component_id) or type(version) is not int or version < 1:
            raise DomainError("invalid_component_id", "Select a valid component ID and positive integer version.")
        return self.root / component_id / f"v{version}.json"

    def metadata(self, package):
        return copy.deepcopy(package["component"]) | {"sha256": package["sha256"], "node_count": len(package["design"]["nodes"]),
                                                       "public_ports": copy.deepcopy(package["public_ports"]), "source": copy.deepcopy(package["source"])}

    def catalog(self):
        result = []
        if self.root.exists():
            for path in sorted(self.root.glob("component-*/v*.json")):
                if path.is_symlink():
                    raise DomainError("invalid_component_library", "Linked component files are not permitted.")
                package = validate_package(strict_loads(path.read_text(encoding="utf-8")))
                if path != self._path(package["component"]["id"], package["component"]["version"]):
                    raise DomainError("invalid_component_library", "Component filename and identity differ.")
                result.append(self.metadata(package))
        return result

    def package(self, component_id, version):
        path = self._path(component_id, version)
        if not path.is_file() or path.is_symlink():
            raise DomainError("component_not_found", "Component version does not exist.", 404)
        return validate_package(strict_loads(path.read_text(encoding="utf-8")))

    def import_package(self, package):
        validate_package(package)
        metadata = package["component"]
        path = self._path(metadata["id"], metadata["version"])
        if path.exists():
            old = self.package(metadata["id"], metadata["version"])
            if old != package:
                raise DomainError("component_version_conflict", "This immutable component version already exists with different contents.", 409)
            return self.metadata(old) | {"already_present": True}
        write_json(path, package)
        return self.metadata(package) | {"already_present": False}

    def publish(self, resolved, node_ids=None, name=None, public_ports=None, component_id=None):
        store = ProjectStore(resolved["path"])
        envelope = store.envelope()
        snapshot = envelope["design"]
        nodes = {n["id"]: n for n in snapshot["nodes"]}
        if node_ids is None:
            node_ids = list(nodes)
        if type(node_ids) is not list or not node_ids or any(type(n) is not str for n in node_ids) or len(set(node_ids)) != len(node_ids) or not set(node_ids) <= set(nodes):
            raise DomainError("invalid_component_selection", "Select one or more existing distinct nodes.")
        selected = set(node_ids)
        design = copy.deepcopy(snapshot)
        design["nodes"] = [copy.deepcopy(n) for n in snapshot["nodes"] if n["id"] in selected]
        for node in design["nodes"]:
            if node["parent_id"] not in selected:
                node["parent_id"] = None
        design["edges"] = [copy.deepcopy(e) for e in snapshot["edges"] if e["source"]["node_id"] in selected and e["target"]["node_id"] in selected]
        if "external_io" in snapshot:
            design["external_io"] = _project_external_io(snapshot, selected)
        design["layout"]["nodes"] = {k: v for k, v in design["layout"]["nodes"].items() if k in selected}
        used = {(e[end]["node_id"], e[end]["port_id"]) for e in design["edges"] for end in ("source", "target")}
        if public_ports is None:
            public_ports = []
            names = set()
            for node in design["nodes"]:
                for port in node["ports"]:
                    if (node["id"], port["id"]) in used:
                        continue
                    base = f"{node['module_name']}_{port['name']}"
                    alias, suffix = base, 2
                    while alias in names:
                        alias, suffix = f"{base}_{suffix}", suffix + 1
                    names.add(alias)
                    public_ports.append(copy.deepcopy(port) | {"node_id": node["id"], "port_id": port["id"], "name": alias})
        else:
            # UI may supply endpoint + alias; derive all contract fields from the source.
            if type(public_ports) is not list:
                raise DomainError("invalid_component_port", "Public ports must be an array.")
            derived = []
            for exposed in public_ports:
                if type(exposed) is not dict:
                    raise DomainError("invalid_component_port", "Public port entry is malformed.")
                if type(exposed.get("node_id")) is not str or type(exposed.get("port_id")) is not str:
                    raise DomainError("invalid_component_port", "Public port endpoints must be string IDs.")
                node = nodes.get(exposed.get("node_id"))
                port = next((p for p in node["ports"] if p["id"] == exposed.get("port_id")), None) if node else None
                if not port:
                    raise DomainError("invalid_component_port", "Public port endpoint is missing.")
                derived.append(copy.deepcopy(port) | exposed)
            public_ports = derived
        cid = component_id or new_id("component")
        versions = [m["version"] for m in self.catalog() if m["id"] == cid]
        version = max(versions, default=0) + 1
        name = checked_name(name or resolved["system"]["name"], "Component name")
        histories, retained_history = [], []
        for path in sorted(resolved["path"].glob("*.json")):
            data = path.read_bytes()
            histories.append({"file": path.name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "scope": "Source provenance reference only"})
            retained_history.append({"file": path.name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "encoding": "gzip+base64", "data": base64.b64encode(gzip.compress(data, mtime=0)).decode("ascii")})
        source = {"project_id": resolved["project_id"], "system_id": resolved["system_id"], "revision_id": envelope["revision"]["id"],
                  **revision_hashes(snapshot), "captured_at": utc_now(), "evidence_scope": "Source provenance only; target validation not run.",
                  "history_files": histories, "recorded_input_run_ids": [run["id"] for run in envelope["runs"]]}
        package = {"format": "hullcirq-component", "version": "1", "component": {"id": cid, "version": version, "name": name, "created_at": utc_now()},
                   "design": design, "source_snapshot": copy.deepcopy(snapshot), "source_history": retained_history, "public_ports": public_ports, "source": source}
        package["sha256"] = digest(package)
        return self.import_package(package)

    def instantiate(self, resolved, component_id, version, expected_revision_id, instance_name):
        if resolved["read_only"]:
            raise DomainError("read_only_system", "Duplicate this evidence system before editing.", 409)
        package = self.package(component_id, version)
        instance_name = checked_name(instance_name, "Instance name")
        store = ProjectStore(resolved["path"])
        envelope = store.envelope()
        if envelope["revision"]["id"] != expected_revision_id:
            raise DomainError("revision_conflict", "System changed; reload before importing a component.", 409)
        design = envelope["design"]
        if any(i.get("name", "").casefold() == instance_name.casefold() for i in design.get("component_instances", [])):
            raise DomainError("duplicate_instance_name", "A logical component instance with this name already exists.", 409)
        for key in ("reset_active", "reset_kind", "rtl_language"):
            if design["settings"][key] != package["design"]["settings"][key]:
                raise DomainError("component_settings_mismatch", f"Component {key} differs from this system. Adapt the source explicitly first.", 409)
        iid = new_id("instance")
        node_ids = {n["id"]: new_id("node") for n in package["design"]["nodes"]}
        port_ids = {p["id"]: new_id("port") for n in package["design"]["nodes"] for p in n["ports"]}
        modules = {n["module_name"] for n in design["nodes"]} | {design["settings"]["top_module"]}
        copied = []
        prefix = re.sub(r"[^A-Za-z0-9_]", "_", instance_name)
        if not prefix or not (prefix[0].isalpha() or prefix[0] == "_"):
            prefix = "instance_" + prefix
        for source in package["design"]["nodes"]:
            node = copy.deepcopy(source)
            node["id"] = node_ids[source["id"]]
            node["parent_id"] = node_ids.get(source["parent_id"])
            node["name"] = f"{instance_name} / {source['name']}"
            base = f"{prefix}_{source['module_name']}"
            module, count = base, 2
            while module in modules or not _identifier(module):
                module, count = f"{base}_{count}", count + 1
            node["module_name"] = module
            modules.add(module)
            node["component_ref"] = {"instance_id": iid, "component_id": component_id, "version": version, "package_sha256": package["sha256"], "source_node_id": source["id"]}
            for port in node["ports"]:
                port["id"] = port_ids[port["id"]]
                port["clock"], port["reset"] = design["settings"]["clock_name"], design["settings"]["reset_name"]
                if port.get("sideband", {}).get("associated_port_id") is not None:
                    port["sideband"]["associated_port_id"] = port_ids[port["sideband"]["associated_port_id"]]
            copied.append(node)
        offset = 80 * (len(design.get("component_instances", [])) + 1)
        for source_id, target_id in node_ids.items():
            old = package["design"]["layout"]["nodes"].get(source_id, {"x": 80, "y": 80})
            design["layout"]["nodes"][target_id] = {"x": old["x"] + offset, "y": old["y"] + offset}
        design["nodes"].extend(copied)
        for source in package["design"]["edges"]:
            edge = copy.deepcopy(source)
            edge["id"] = new_id("edge")
            for end in ("source", "target"):
                edge[end] = {"node_id": node_ids[edge[end]["node_id"]], "port_id": port_ids[edge[end]["port_id"]]}
            design["edges"].append(edge)
        public_ports = []
        for source in package["public_ports"]:
            exposed = copy.deepcopy(source)
            exposed["node_id"], exposed["port_id"] = node_ids[source["node_id"]], port_ids[source["port_id"]]
            exposed["id"] = exposed["port_id"]
            exposed["clock"], exposed["reset"] = design["settings"]["clock_name"], design["settings"]["reset_name"]
            if exposed.get("sideband", {}).get("associated_port_id") is not None:
                exposed["sideband"]["associated_port_id"] = port_ids[exposed["sideband"]["associated_port_id"]]
            public_ports.append(exposed)
        instance = {"id": iid, "name": instance_name, "component_id": component_id, "version": version, "package_sha256": package["sha256"],
                    "node_ids": list(node_ids.values()), "public_ports": public_ports, "imported_at": utc_now(), "source": copy.deepcopy(package["source"]),
                    "clock_reset_mapping": {"source_clock": package["design"]["settings"]["clock_name"], "source_reset": package["design"]["settings"]["reset_name"],
                                            "target_clock": design["settings"]["clock_name"], "target_reset": design["settings"]["reset_name"]},
                    "evidence_scope": "Source provenance only; target validation not run."}
        design.setdefault("component_instances", []).append(instance)
        validate_shape(design)
        errors = [d for d in validate_stage(design, "graph_editor") if d["severity"] == "error"]
        if errors:
            raise DomainError("invalid_component_combination", errors[0]["message"], 409)
        return {"envelope": store.save(design, expected_revision_id), "instance": instance,
                "project_id": resolved["project_id"], "system_id": resolved["system_id"]}

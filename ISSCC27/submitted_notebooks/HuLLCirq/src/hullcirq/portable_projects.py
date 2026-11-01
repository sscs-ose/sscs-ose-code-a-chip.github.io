"""Bounded, non-executable transfer of raw project evidence and derived maps.

This archive is not a host-runtime migration. Original absolute provenance is
opaque retained data; a separate manifest maps bytes to managed local objects.
"""
from __future__ import annotations

import base64
import copy
import gzip
import hashlib
import json
import os
import re
import stat
import zlib
from itertools import chain
from pathlib import Path

from .domain import DomainError
from .store import strict_loads, utc_now
from .workspace import archive_path, canonical, digest, write_json

FORMAT = "hullcirq-portable-evidence"
VERSION = "1"
MAX_FILES = 50000
MAX_FILE_BYTES = 512 * 1024 ** 2
MAX_TOTAL_BYTES = 2 * 1024 ** 3
MAX_PACKAGE_BYTES = 120 * 1024 ** 2  # Leaves room in the existing 128 MiB HTTP body.
STORES = ("state.json", "generation.json", "generation_batches.json", "workflow.json",
          "implementation_specs.json", "global_generation.json", "global_workflow.json",
          "physical_workflow.json", "drc_workflow.json", "lvs_workflow.json",
          "postlayout_workflow.json", "repair_analysis.json")
_HEX = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[a-z]+-[0-9a-f]{32}$")
_MAP_ID = re.compile(r"^functional-map-[0-9a-f]{32}$")
PREPARED_PROFILES = {
    "postlayout_runtime.json": "postlayout_workflow.json",
    "lvs_repair_direct_runtime_v7.json": "lvs_workflow.json",
    **{f"lvs_repair_runtime_v{version}.json": "lvs_workflow.json" for version in range(3, 8)},
    "physical_repair_runtime.json": "physical_workflow.json",
    "physical_repair_runtime_v2.json": "physical_workflow.json",
    "physical_repair_runtime_v3.json": "physical_workflow.json",
}
POLICY = ("Verified raw-byte archive only. Historical acceptance is provenance, not execution readiness on this host. "
          "Open a restored system read-only; Duplicate creates an editable design with no imported runs or policy. "
          "No tools, PDK, model weights, executable configuration or automatic jobs are installed.")


def require(condition, message, code="portable_evidence_invalid"):
    if not condition:
        raise DomainError(code, message, 409)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def io_path(path):
    """Keep archive/provenance paths unchanged; extend Windows I/O only."""
    value = os.path.abspath(os.fspath(path))
    if os.name == "nt" and not value.startswith("\\\\?\\"):
        value = "\\\\?\\UNC\\" + value[2:] if value.startswith("\\\\") else "\\\\?\\" + value
    return Path(value)


def safe_file(root, relative):
    """Check every component before resolving: junctions must not disappear."""
    parts = archive_path(relative)
    root = Path(root)
    require(".." not in root.parts, "Evidence roots must not contain parent traversal.")
    root = root.absolute()
    for item in (root, *root.parents):
        try:
            info = io_path(item).lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                "Linked evidence paths are not allowed.")
    cursor = root
    for part in parts:
        cursor = cursor / part
        try:
            info = io_path(cursor).lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                "Linked evidence paths are not allowed.")
    require(cursor.is_relative_to(root), "Evidence must remain below its managed root.")
    return cursor


def _read(root, relative, expected=None):
    path = safe_file(root, relative)
    handle = io_path(path)
    require(handle.is_file(), "A retained evidence file is missing.", "portable_evidence_missing")
    size = handle.stat().st_size
    require(size <= MAX_FILE_BYTES, "An evidence file exceeds the 512 MiB transfer limit.")
    raw = handle.read_bytes()
    require(len(raw) == size, "An evidence file changed while being read.")
    if expected is not None:
        require(expected.get("bytes") == len(raw) and expected.get("sha256") == sha(raw),
                "A retained evidence file does not match its recorded raw hash.", "portable_evidence_checksum")
    return raw


def _pack(path, raw, **metadata):
    return {"path": path, "encoding": "gzip+base64", "size": len(raw), "sha256": sha(raw),
            "data": base64.b64encode(gzip.compress(raw, mtime=0)).decode("ascii"), **metadata}


def _decode(entry):
    require(type(entry) is dict, "An evidence entry is malformed.")
    archive_path(entry.get("path"))
    size = entry.get("size")
    require(type(size) is int and 0 <= size <= MAX_FILE_BYTES and entry.get("encoding") == "gzip+base64"
            and type(entry.get("sha256")) is str and _HEX.fullmatch(entry["sha256"])
            and type(entry.get("data")) is str and len(entry["data"]) <= MAX_PACKAGE_BYTES,
            "An evidence entry has invalid limits or encoding.")
    try:
        compressed = base64.b64decode(entry["data"], validate=True)
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        raw = decoder.decompress(compressed, size + 1)
        require(len(raw) == size and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
                "Evidence compression has an invalid size or trailing stream.")
    except (ValueError, TypeError, zlib.error) as error:
        raise DomainError("portable_evidence_invalid", "Evidence compression is malformed.") from error
    require(sha(raw) == entry["sha256"], "An evidence checksum does not match.", "portable_evidence_checksum")
    return raw


def export_project(registry, project_id, project_root):
    """Copy only fixed stores and explicitly hash-bound retained artifacts."""
    from .components import ComponentLibrary
    from .workspace import component_references
    project_root = Path(project_root).resolve()
    with registry.lock:
        project = copy.deepcopy(registry._project(project_id))
        project.pop("directory", None)
        entries, records, missing, maps, dependencies = [], [], [], [], set()
        exported_paths = set()
        total = 0
        def add(path, raw, **metadata):
            nonlocal total
            archive_path(path)
            require(path.casefold() not in exported_paths, "Evidence files have a duplicate archive destination.")
            exported_paths.add(path.casefold())
            require(len(raw) <= MAX_FILE_BYTES and total + len(raw) <= MAX_TOTAL_BYTES and len(entries) < MAX_FILES,
                    "The project exceeds the evidence transfer limits.")
            total += len(raw)
            entry = _pack(path, raw, **metadata)
            entries.append(entry)
            return entry
        for system in project["systems"]:
            sid = system["id"]
            source = registry._system_path(project_id, sid)
            for name in STORES:
                path = safe_file(source, name)
                if not io_path(path).exists():
                    require(name != "state.json", "A system state snapshot is missing.")
                    continue
                raw = _read(source, name)
                value = strict_loads(raw.decode("utf-8"))
                dependencies.update(component_references(value))
                add(f"systems/{sid}/{name}", raw, kind="system_store", system_id=sid)
                for run in value.get("runs", []) if type(value) is dict else []:
                    if type(run) is dict and type(run.get("id")) is str:
                        records.append((sid, name, run))
        # Pinned logical components are data, never imported execution profiles.
        packages, seen = [], set()
        library = ComponentLibrary(registry.root / "components")
        while dependencies - seen:
            identity = sorted(dependencies - seen)[0]
            package = library.package(*identity)
            packages.append(package)
            seen.add(identity)
            dependencies.update(component_references(package))
        attachment = registry._project_path(project_id) / "evidence" / "manifest.json"
        if io_path(attachment).exists():
            retained = inspect_project(registry, project_id)
            systems = {system.get("origin", {}).get("source_system_id"): system["id"] for system in project["systems"]}
            def relocated(path):
                parts = archive_path(path)
                require(parts[1] in systems, "Attached evidence does not map to this restored project.")
                parts[1] = systems[parts[1]]
                return "/".join(parts)
            for entry in retained["entries"]:
                if entry.get("kind") == "system_store":
                    continue
                raw = _read(attachment.parent, entry["object"], {"bytes": entry["size"], "sha256": entry["sha256"]})
                metadata = {k: v for k, v in entry.items() if k not in {"path", "object", "file_id", "size", "sha256"}}
                metadata["system_id"] = systems[entry["system_id"]]
                add(relocated(entry["path"]), raw, **metadata)
            for mapping in retained["maps"]:
                maps.append({**mapping, "system_id": systems[mapping["system_id"]], "html_path": relocated(mapping["html_path"])})
            missing.extend(retained["unavailable"])
            records = []  # Foreign original paths are never reopened after restore.
        for sid, store, run in records:
            checks = run.get("checks", {})
            if type(checks) is not dict:
                continue
            root = checks.get("artifacts_directory")
            explicit = checks.get("artifacts", []) if type(checks.get("artifacts")) is list else []
            retained = checks.get("retained_files", []) if type(checks.get("retained_files")) is list else []
            pinned_files = {}
            for item in [*explicit, *retained]:
                if not (type(item) is dict and type(item.get("relative_path")) is str
                        and type(item.get("bytes")) is int and type(item.get("sha256")) is str):
                    continue  # API descriptors are not raw external file manifests.
                relative = item["relative_path"]
                archive_path(relative)
                if relative in pinned_files:
                    require(all(pinned_files[relative].get(field) == item.get(field) for field in ("bytes", "sha256")),
                            "Retained artifact declarations disagree about the same file.")
                else:
                    pinned_files[relative] = item
            for relative, item in pinned_files.items():
                label = {"system_id": sid, "store": store, "run_id": run["id"],
                         "artifact_id": str(item.get("id", relative)), "relative_path": relative}
                if type(root) is not str or not Path(root).is_absolute() or not io_path(root).exists():
                    missing.append({**label, "reason": "original_result_directory_unavailable"})
                    continue
                source_root = Path(root)
                # Do not use recorded paths as an arbitrary host-file reader.
                require(".." not in source_root.parts and source_root.is_relative_to(project_root / ".work")
                        and not any(part.casefold() in {"runtime", "models", "pdks", "pdk", "tools", ".ssh"}
                                    for part in source_root.relative_to(project_root).parts),
                        "An external artifact is not in a permitted retained-result directory.")
                if not io_path(safe_file(source_root, relative)).exists():
                    missing.append({**label, "reason": "original_artifact_unavailable"})
                    continue
                raw = _read(source_root, relative, item)
                add(f"artifacts/{sid}/{store}/{run['id']}/{relative}", raw, kind="eda_artifact", **label)
            if store == "physical_workflow.json":
                _export_maps(project_root, sid, run, add, missing, maps)
        if not io_path(attachment).exists():
            for system in project["systems"]:
                _export_prepared_profiles(registry, project_id, system["id"], records, add, missing)
        backup_files = [{k: value for k, value in entry.items() if k in {"path", "encoding", "size", "sha256", "data"}}
                        for entry in entries if entry["kind"] == "system_store"]
        base = {"format": "hullcirq-project-backup", "version": "1", "created_at": utc_now(), "project": project,
                "files": backup_files, "components": packages, "external_references": [], "restore_policy": POLICY}
        backup = base | {"checksum": digest(base)}
        value = {"format": FORMAT, "version": VERSION, "created_at": utc_now(), "project": project,
                 "design_backup": backup, "entries": [entry for entry in entries if entry["kind"] != "system_store"],
                 "maps": maps, "unavailable": missing, "restore_policy": POLICY,
                 "privacy_notice": "Private transfer: raw history may contain original host paths, prompts and proprietary design data. Inspect before sharing."}
        value["checksum"] = digest(value)
        require(len(canonical(value)) <= MAX_PACKAGE_BYTES, "Compressed evidence exceeds the 120 MiB GUI transfer limit.")
        return value


def _export_prepared_profiles(registry, project_id, sid, records, add, missing):
    """Archive fixed scoped profiles as inert source-bound history, never tools."""
    from .verification import object_hash
    identity = json.dumps([project_id, sid], ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    scope = hashlib.sha256(identity).hexdigest()[:32]
    for filename, store in PREPARED_PROFILES.items():
        relative = f"runtime_profiles/{scope}/{filename}"
        path = safe_file(registry.root, relative)
        if not io_path(path).exists():
            continue
        raw = _read(registry.root, relative)
        profile = strict_loads(raw.decode("utf-8"))
        require(type(profile) is dict, "A prepared profile is malformed.")
        configuration = profile.get("configuration", profile)
        if "configuration" in profile:
            require(profile.get("project_id") == project_id and profile.get("system_id") == sid
                    and profile.get("record_hash") == object_hash({k: v for k, v in profile.items() if k != "record_hash"}),
                    "The prepared profile source or checksum changed.", "portable_evidence_checksum")
        matches = [run for system_id, name, run in records if system_id == sid and name == store
                   and run.get("runtime_configuration") == configuration]
        if not matches:
            missing.append({"system_id": sid, "store": store, "kind": "prepared_profile", "relative_path": filename,
                            "reason": "prepared_profile_without_saved_execution"})
            continue
        add(f"profiles/{sid}/{filename}", raw, kind="prepared_profile", system_id=sid,
            store=store, source_run_ids=[run["id"] for run in matches],
            configuration_sha256=object_hash(configuration), executable=False)


def _export_maps(root, sid, run, add, missing, maps):
    from .layout_map_generation import projection_hash, read_registration, read_registration_version
    from .layout_role_view import _registration, _verified_bundle
    try:
        current = read_registration(root, run)
        registrations = []
        version_root = root / ".work" / "functional_maps" / "registrations" / projection_hash(run)
        if io_path(version_root).exists():
            for path in sorted(io_path(version_root).glob("*.json")):
                require(_MAP_ID.fullmatch(path.stem), "A Functional Map version identity is invalid.")
                registrations.append(read_registration_version(root, run, path.stem))
        if not registrations:
            registrations = [current] if current is not None else [_registration(run["id"])]
        for registration in registrations:
            if registration is None:
                continue
            payloads, binding = _verified_bundle(root, run, registration)
            key = binding.get("registration_job_id", "static")
            prefix = f"maps/{sid}/{run['id']}/{key}"
            staged = []
            for folder_key in ("view_root", "source_root"):
                folder = registration[folder_key]
                manifest_raw = _read(root, folder + "/manifest.json")
                manifest = strict_loads(manifest_raw.decode("utf-8"))
                category = "view" if folder_key == "view_root" else "source"
                staged.append((prefix + f"/{category}/manifest.json", manifest_raw))
                for relative, expected in manifest["files"].items():
                    raw = _read(root, folder + "/" + relative, expected)
                    staged.append((prefix + f"/{category}/{relative}", raw))
            if key != "static":
                require(_MAP_ID.fullmatch(key), "A Functional Map publication identity is invalid.")
                registration_relative = f".work/functional_maps/registrations/{projection_hash(run)}/{key}.json"
                staged.append((prefix + "/registration/version.json", _read(root, registration_relative)))
                if current is not None and current.get("job_id") == key:
                    staged.append((prefix + "/registration/current-pointer.json",
                                   _read(root, f".work/functional_maps/registrations/{projection_hash(run)}.json")))
                job_relative = f".work/functional_maps/jobs/{key}.json"
                if io_path(safe_file(root, job_relative)).exists():
                    staged.append((prefix + "/registration/job.json", _read(root, job_relative)))
                event_root = root / ".work" / "functional_maps" / "jobs" / key
                if io_path(event_root).exists():
                    for event in sorted(io_path(event_root).glob("*.json")):
                        require(re.fullmatch(r"[0-9]{6}\.json", event.name), "A Functional Map event filename is malformed.")
                        staged.append((prefix + "/registration/events/" + event.name,
                                       _read(root, (event_root / event.name).relative_to(root).as_posix())))
            for destination, raw in staged:
                add(destination, raw, kind="functional_map", system_id=sid, run_id=run["id"], map_id=key)
            maps.append({"system_id": sid, "layout_run_id": run["id"], "map_id": key,
                         "html_path": prefix + "/view/layout_roles.html", "binding": binding})
    except DomainError as error:
        if error.code in {"functional_map_unavailable", "functional_map_not_registered", "functional_map_not_available"}:
            return
        # Missing old map files are explicit, never presented as included.
        if error.code in {"functional_map_integrity_error", "portable_evidence_missing"}:
            missing.append({"system_id": sid, "run_id": run["id"], "kind": "functional_map", "reason": error.code})
            return
        raise


def validate_package(bundle, *, retain_store_bytes=True):
    try:
        return _validate_package(bundle, retain_store_bytes=retain_store_bytes)
    except DomainError:
        raise
    except (TypeError, KeyError, AttributeError, UnicodeError, ValueError, RecursionError) as error:
        raise DomainError("portable_evidence_invalid", "Evidence package data is malformed; no project was changed.") from error


def _validate_package(bundle, *, retain_store_bytes=True):
    from .workspace import checked_name, component_references
    from .store import _validate_saved_state
    from .components import validate_package as validate_component
    require(type(bundle) is dict and bundle.get("format") == FORMAT and bundle.get("version") == VERSION,
            "This is not a supported portable evidence package.")
    require(len(canonical(bundle)) <= MAX_PACKAGE_BYTES, "Evidence package exceeds the 120 MiB input limit.")
    require(bundle.get("checksum") == digest({k: v for k, v in bundle.items() if k != "checksum"}),
            "The evidence package checksum does not match.", "portable_evidence_checksum")
    backup, entries = bundle.get("design_backup"), bundle.get("entries")
    require(type(backup) is dict and type(backup.get("project")) is dict and type(backup.get("files")) is list
            and type(entries) is list and len(entries) <= MAX_FILES,
            "The evidence package manifest is malformed.")
    require(bundle.get("project") == backup["project"], "Evidence project metadata differs from its design snapshot.")
    require(backup.get("format") == "hullcirq-project-backup" and backup.get("version") == "1"
            and backup.get("checksum") == digest({k: v for k, v in backup.items() if k != "checksum"}),
            "The nested design backup checksum does not match.", "portable_evidence_checksum")
    checked_name(backup["project"].get("name"))
    systems = backup["project"].get("systems")
    require(type(systems) is list and all(type(item) is dict for item in systems), "Invalid archived system list.")
    require(all(type(item.get("id")) is str for item in systems), "Archived system IDs must be strings.")
    old_ids = {item.get("id") for item in systems}
    require(old_ids and all(type(sid) is str and _ID.fullmatch(sid) for sid in old_ids), "Invalid archived system IDs.")
    require(len(old_ids) == len(systems), "Archived system IDs are repeated.")
    for system in systems:
        checked_name(system.get("name"))
    all_entries = [*backup["files"], *entries]
    require(len(all_entries) <= MAX_FILES, "Evidence contains too many files.")
    packages = backup.get("components")
    require(type(packages) is list, "Pinned logical component data must be a list.")
    component_histories = []
    for component in packages:
        require(type(component) is dict and type(component.get("source_history")) is list,
                "Pinned component history is malformed.")
        component_histories.extend(component["source_history"])
    require(len(all_entries) + len(component_histories) <= MAX_FILES, "Evidence contains too many files including component histories.")
    declared_total = 0
    for entry in chain(all_entries, component_histories):
        require(type(entry) is dict and type(entry.get("size")) is int and 0 <= entry["size"] <= MAX_FILE_BYTES,
                "Evidence has an invalid declared decoded size.")
        declared_total += entry["size"]
        require(declared_total <= MAX_TOTAL_BYTES, "Declared decoded evidence exceeds the transfer limit.")
    # The complete size/count preflight above finishes before ANY decompression.
    paths, total, decoded, state_ids, dependencies = set(), 0, [], set(), set()
    for entry in all_entries:
        path = entry.get("path") if type(entry) is dict else None
        parts = archive_path(path)
        require(path.casefold() not in paths and len(parts) >= 3 and parts[0] in {"systems", "artifacts", "maps", "profiles"}
                and parts[1] in old_ids, "Repeated, conflicting or out-of-scope evidence path.")
        paths.add(path.casefold())
        if parts[0] == "systems":
            require(len(parts) == 3 and parts[2] in STORES, "Only fixed system stores can be restored for viewing.")
        else:
            expected_kind = {"artifacts": "eda_artifact", "maps": "functional_map", "profiles": "prepared_profile"}[parts[0]]
            require(entry.get("kind") == expected_kind and entry.get("system_id") == parts[1],
                    "Artifact metadata does not match its bounded manifest path.")
            if parts[0] == "profiles":
                require(len(parts) == 3 and parts[2] in PREPARED_PROFILES and entry.get("executable") is False,
                        "Only fixed inert prepared-profile snapshots can be archived.")
        raw = _decode(entry)
        total += len(raw)
        require(total <= MAX_TOTAL_BYTES and len(paths) <= MAX_FILES, "Decoded evidence exceeds transfer limits.")
        if parts[0] == "systems" and parts[2] == "state.json":
            state = strict_loads(raw.decode("utf-8"))
            _validate_saved_state(state)
            require(parts[1] not in state_ids, "An archived system state is repeated.")
            state_ids.add(parts[1])
            dependencies.update(component_references(state))
        if retain_store_bytes or parts[0] != "systems":
            decoded.append((entry, raw))
    # A file cannot be a directory prefix (Windows and POSIX agree).
    require(not any("/".join(path.split("/")[:i]) in paths for path in paths for i in range(1, len(path.split("/")))),
            "Evidence has a file/directory path conflict.")
    require(type(bundle.get("maps")) is list and type(bundle.get("unavailable")) is list, "Evidence view lists are malformed.")
    map_paths = set()
    by_path = {entry["path"]: entry for entry in entries}
    for mapping in bundle["maps"]:
        require(type(mapping) is dict and type(mapping.get("html_path")) is str, "A Functional Map entry is malformed.")
        path = mapping["html_path"]
        require(path in by_path and path not in map_paths and by_path[path].get("kind") == "functional_map"
                and mapping.get("system_id") == by_path[path].get("system_id")
                and type(mapping.get("layout_run_id")) is str and type(mapping.get("map_id")) is str
                and path == f"maps/{mapping['system_id']}/{mapping['layout_run_id']}/{mapping['map_id']}/view/layout_roles.html",
                "A Functional Map points outside its archived data scope.")
        map_paths.add(path)
    require(state_ids == old_ids, "Every archived system requires exactly one state snapshot.")
    identities = set()
    for component in packages:
        validate_component(component)
        identity = (component["component"]["id"], component["component"]["version"])
        require(identity not in identities, "Pinned logical component versions are repeated.")
        identities.add(identity)
        dependencies.update(component_references(component))
    require(not dependencies - identities, "A pinned logical dependency is missing from the evidence package.")
    return decoded


def restore_project(registry, bundle, name=None):
    # Do not keep all decoded stores while the legacy fresh-ID restore decodes
    # and validates them itself. Read those exact restored bytes one at a time
    # when creating attachment objects; non-store artifact bytes are retained.
    decoded = validate_package(bundle, retain_store_bytes=False)
    # Existing restore validates states/components before any catalog write and
    # assigns fresh project/system IDs with explicit read-only flags.
    with registry.lock:
        from .components import ComponentLibrary
        component_library = ComponentLibrary(registry.root / "components")
        added_components = []
        for package in bundle["design_backup"]["components"]:
            identity = (package["component"]["id"], package["component"]["version"])
            path = component_library._path(*identity)
            if not path.exists():
                added_components.append((path, identity, package))
        result = registry.restore_project(bundle["design_backup"], name)
        pid = result["project_id"]
        project_path = registry._project_path(pid)
        root = project_path / "evidence"
        try:
            entries = []
            system_mapping = {system["origin"]["source_system_id"]: system["id"] for system in result["project"]["systems"]}
            def stores():
                for entry in bundle["design_backup"]["files"]:
                    parts = archive_path(entry["path"])
                    destination_system = registry._system_path(pid, system_mapping[parts[1]])
                    raw = _read(destination_system, parts[2], {"bytes": entry["size"], "sha256": entry["sha256"]})
                    yield entry, raw
            for index, (entry, raw) in enumerate(chain(stores(), decoded)):
                object_name = f"objects/{index:06d}-{entry['sha256']}"
                destination = safe_file(root, object_name)
                io_path(destination.parent).mkdir(parents=True, exist_ok=True)
                with io_path(destination).open("xb") as stream:
                    stream.write(raw)
                metadata = {key: value for key, value in entry.items() if key not in {"data", "encoding"}}
                if entry["path"].startswith("systems/"):
                    metadata.update(kind="system_store", system_id=entry["path"].split("/")[1])
                entries.append(metadata | {"object": object_name, "file_id": str(index)})
            manifest = {"format": FORMAT, "version": VERSION, "package_sha256": bundle["checksum"],
                        "restore_policy": POLICY, "entries": entries, "maps": bundle["maps"],
                        "unavailable": bundle["unavailable"], "host_execution_ready": False,
                        "source_project_id": bundle["project"].get("id")}
            manifest["checksum"] = digest(manifest)
            write_json(root / "manifest.json", manifest)
        except Exception:
            from .workspace import remove_owned_tree
            catalog = copy.deepcopy(registry._registry)
            catalog["projects"] = [project for project in catalog["projects"] if project["id"] != pid]
            registry._save(catalog)
            remove_owned_tree(project_path, registry.root / "projects" / pid)
            for path, identity, package in added_components:
                if path.exists() and component_library.package(*identity) == package:
                    # Only exact immutable files introduced by this failed
                    # restore, never an existing shared version or directory.
                    safe_file(registry.root, path.relative_to(registry.root).as_posix()).unlink()
            raise
        return result


def inspect_project(registry, project_id):
    with registry.lock:
        root = registry._project_path(project_id) / "evidence"
        path = safe_file(root, "manifest.json")
        require(io_path(path).is_file(), "This project has no attached portable evidence package.", "portable_evidence_missing")
        value = strict_loads(_read(root, "manifest.json").decode("utf-8"))
        require(value.get("format") == FORMAT and value.get("checksum") == digest({k: v for k, v in value.items() if k != "checksum"}),
                "The restored evidence manifest checksum does not match.", "portable_evidence_checksum")
        require(type(value.get("entries")) is list and len(value["entries"]) <= MAX_FILES, "Invalid restored evidence manifest.")
        # Every inspect verifies object bytes; no historic adoption is inferred.
        for index, entry in enumerate(value["entries"]):
            require(type(entry) is dict and type(entry.get("size")) is int and 0 <= entry["size"] <= MAX_FILE_BYTES
                    and type(entry.get("sha256")) is str and _HEX.fullmatch(entry["sha256"])
                    and entry.get("file_id") == str(index) and entry.get("object") == f"objects/{index:06d}-{entry.get('sha256')}",
                    "Restored evidence object mapping is invalid.")
            _read(root, entry["object"], {"bytes": entry["size"], "sha256": entry["sha256"]})
        return value


def artifact_bytes(registry, project_id, file_id):
    require(type(file_id) is str and file_id.isdigit() and len(file_id) <= 6, "Invalid evidence file ID.")
    value = inspect_project(registry, project_id)
    index = int(file_id)
    require(index < len(value["entries"]), "Evidence file does not exist.", "portable_evidence_missing")
    entry = value["entries"][index]
    root = registry._project_path(project_id) / "evidence"
    return _read(root, entry["object"], {"bytes": entry["size"], "sha256": entry["sha256"]}), entry


def map_view_bytes(registry, project_id, file_id):
    """Render inert archived data with installed trusted code, never imported JS.

    Raw HTML remains separately downloadable unchanged. Rebuilding only this
    read-only presentation does not rewrite its historical artifact or proof.
    """
    import math

    raw, entry = artifact_bytes(registry, project_id, file_id)
    require(entry.get("kind") == "functional_map" and entry["path"].endswith("/view/layout_roles.html"),
            "Only an archived Functional Map data payload can be viewed.")
    require(len(raw) <= 64 * 1024 ** 2, "The archived map exceeds the interactive-view size limit.")
    payloads = re.findall(rb'<script\s+id="layout-data"\s+type="application/json"\s*>(.*?)</script\s*>', raw, re.S | re.I)
    require(len(payloads) == 1, "The archived map has no single inert embedded data payload.")
    try:
        payload = strict_loads(payloads[0].decode("utf-8"))
        require(type(payload) is dict, "Archived map data is malformed.")
        if payload.get("cell_encoding") == "string-table-v1":
            strings, rows = payload.get("strings"), payload.get("cell_rows")
            require("cells" not in payload and type(strings) is list and type(rows) is list
                    and all(type(value) is str for value in strings), "Archived compact map tables are malformed.")
            for row in rows:
                require(type(row) is list and len(row) == 6, "Archived compact map row is malformed.")
                indices = [row[0], row[1], row[3], row[4]]
                require(type(row[5]) is list, "Archived compact map evidence is malformed.")
                require(all(type(index) is int and 0 <= index < len(strings) for index in indices)
                        and all(type(index) is int and 0 <= index < len(strings) for index in row[5]),
                        "Archived compact map string index is out of bounds.")
                box = row[2]
                require(type(box) is list and len(box) == 4
                        and all(type(value) in (int, float) and math.isfinite(value) for value in box)
                        and box[2] >= box[0] and box[3] >= box[1], "Archived compact map cell bounds are malformed.")
        else:
            require("cell_encoding" not in payload and type(payload.get("cells")) is list,
                    "Archived map data encoding is unsupported or malformed.")
        encoded = json.dumps(payload, ensure_ascii=True, allow_nan=False, separators=(",", ":")).replace("<", "\\u003c")
    except (UnicodeError, ValueError, RecursionError, OverflowError) as error:
        raise DomainError("portable_evidence_invalid", "Archived map data is not valid bounded JSON.") from error
    template_root = Path(__file__).resolve().parents[2] / "scripts" / "templates"
    template = template_root / "layout_roles_viewer.html"
    html = template.read_text(encoding="utf-8")
    require(html.count("__LAYOUT_DATA_JSON__") == 1 and html.count("/*__LAYOUT_UNPACK__*/") == 1,
            "The installed map viewer template is invalid.")
    decoder = (template_root / "layout_roles_unpack.js").read_text(encoding="utf-8")
    return html.replace("/*__LAYOUT_UNPACK__*/", decoder).replace("__LAYOUT_DATA_JSON__", encoded).encode("utf-8")

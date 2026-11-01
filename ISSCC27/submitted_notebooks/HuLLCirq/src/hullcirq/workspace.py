"""Local project/system catalog and checked, non-executable backup packages.

Workspace IDs locate managed or explicitly selected project directories. Names
and archive paths never become filesystem destinations. Imported history is retained as provenance;
editable copies start with no runs, reviews, or adoption policy.
"""
from __future__ import annotations

import base64
import copy
import gzip
import hashlib
import json
import os
import re
import shutil
import tempfile
import threading
import zlib
from pathlib import Path, PurePosixPath

from .domain import DomainError, IMPLEMENTED_STAGES, _identifier, revision_hashes, validate_shape
from .store import ProjectStore, _io_path, _validate_saved_state, new_id, strict_loads, utc_now

_ID = re.compile(r"^[a-z]+-[0-9a-f]{32}$")
MAX_BUNDLE_BYTES = 2 * 1024 ** 3
MAX_BUNDLE_FILES = 100000
PROJECT_MANIFEST = "hullcirq.project.json"


def checked_directory(value):
    """Require an absolute real directory path, checking every existing ancestor."""
    if not isinstance(value, (str, os.PathLike)) or not str(value).strip() or "\x00" in str(value):
        raise DomainError("invalid_project_directory", "Select an absolute project folder path.")
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or path == Path(path.anchor):
        raise DomainError("invalid_project_directory", "The project folder must be absolute and cannot be a filesystem root.")
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if item.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
            raise DomainError("unsafe_project_directory", "Project folders cannot use symbolic links, junctions or reparse points.")
        if not item.is_dir():
            raise DomainError("invalid_project_directory", "The project folder or one of its parents is a file.")
    return path.resolve()


def remove_owned_tree(path, allowed_root):
    """Remove only the checked subtree owned by the current failed operation."""
    from .physical_tools import artifact_files, io_path
    path, allowed_root = checked_directory(Path(path)), checked_directory(Path(allowed_root))
    if not path.is_relative_to(allowed_root):
        raise DomainError("unsafe_project_cleanup", "Cleanup target escapes the created project folder.")
    if not io_path(path).exists():
        return
    try:
        # Validate every descendant, including long paths and linked directories,
        # before deleting only the explicitly owned and checked destination.
        list(artifact_files(path, reject_links=True))
    except DomainError as error:
        raise DomainError("unsafe_project_cleanup", "Cleanup stopped because an unsafe path appeared in the created folder.") from error
    shutil.rmtree(io_path(path))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def checked_name(value, label="name"):
    if type(value) is not str or not value.strip() or len(value) > 160 or any(ord(c) < 32 for c in value):
        raise DomainError("invalid_name", f"{label} must be 1–160 visible characters.")
    return value.strip()


def write_json(path: Path, value):
    # Keep the checked logical path unchanged; extend only OS I/O operands.
    destination = _io_path(path)
    _io_path(destination.parent).mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
    descriptor, temporary = tempfile.mkstemp(prefix=".workspace-", suffix=".tmp", dir=destination.parent)
    temporary_path = _io_path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, destination)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def blank_design(project_id, project_name, system_id, system_name, top_module):
    if type(top_module) is not str or not _identifier(top_module):
        raise DomainError("invalid_top_module", "Top module must be a non-keyword Verilog identifier.")
    return {"schema_version": "0.1", "project": {"id": project_id, "name": project_name},
            "system": {"id": system_id, "name": system_name},
            "settings": {"top_module": top_module, "clock_name": "clk", "clock_period_ns": 50,
                         "reset_name": "rst", "reset_active": "high", "reset_kind": "synchronous",
                         "rtl_language": "verilog_2005", "pdk": "sky130A", "cell_library": "sky130_fd_sc_hd"},
            "nodes": [], "edges": [], "external_io": {"version": 1, "ports": [], "connections": []},
            "layout": {"nodes": {}, "viewport": {"x": 0, "y": 0, "zoom": 1}}}


def new_state(design):
    validate_shape(design)
    revision = {"id": new_id("revision"), **revision_hashes(design), "created_at": utc_now()}
    return {"store_version": "0.1", "design": design, "revision": revision,
            "snapshots": {revision["id"]: copy.deepcopy(design)}, "runs": [], "reviews": [],
            "acceptance_epochs": {stage: 0 for stage in IMPLEMENTED_STAGES}}


def archive_path(value):
    if type(value) is not str or not value or any(c in value for c in '\\:\x00<>"|?*'):
        raise DomainError("unsafe_backup_path", "Backup paths must be relative POSIX paths.")
    parts = value.split("/")
    if any(p in ("", ".", "..") or p.rstrip(". ") != p for p in parts) or PurePosixPath(value).is_absolute():
        raise DomainError("unsafe_backup_path", "Backup paths cannot escape the managed project.")
    for part in parts:
        if part.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
            raise DomainError("unsafe_backup_path", "Backup paths contain a reserved device name.")
    return parts


def component_references(value):
    """Collect pinned logical dependencies, including retained older snapshots."""
    references = set()
    def visit(item):
        if type(item) is dict:
            if type(item.get("component_id")) is str and type(item.get("version")) is int:
                references.add((item["component_id"], item["version"]))
            for child in item.values():
                visit(child)
        elif type(item) is list:
            for child in item:
                visit(child)
    visit(value)
    return references


def external_path_references(value):
    paths = set()
    def visit(item):
        if type(item) is dict:
            for child in item.values():
                visit(child)
        elif type(item) is list:
            for child in item:
                visit(child)
        elif type(item) is str and len(item) < 4096 and "\n" not in item:
            if re.match(r"^[A-Za-z]:[\\/]", item) or item.startswith(("/home/", "/mnt/", "/opt/", "/usr/", "/nix/", "\\\\")):
                paths.add(item)
    visit(value)
    return sorted(paths)


class WorkspaceRegistry:
    """Managed projects with one independent ProjectStore directory per system."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.registry_path = self.root / "registry.json"
        self.lock = threading.RLock()
        if _io_path(self.registry_path).exists():
            value = strict_loads(_io_path(self.registry_path).read_text(encoding="utf-8"))
            if type(value) is not dict or value.get("workspace_version") != "1" or type(value.get("projects")) is not list:
                raise DomainError("invalid_workspace", "Workspace catalog is malformed; it was not overwritten.")
            self._registry = value
            self._validate_catalog()
        else:
            self._registry = {"workspace_version": "1", "projects": [], "recent": [], "trash": []}

    def _validate_catalog(self):
        seen, directories = set(), set()
        trash = self._registry.get("trash", [])
        if type(trash) is not list:
            raise DomainError("invalid_workspace", "Project Trash must be an array; it was not overwritten.")
        trash_ids = set()
        for entry in trash:
            if (type(entry) is not dict or type(entry.get("id")) is not str
                    or not _ID.fullmatch(entry["id"]) or entry["id"] in trash_ids
                    or type(entry.get("deleted_at")) is not str or not entry["deleted_at"]
                    or type(entry.get("project")) is not dict):
                raise DomainError("invalid_workspace", "Project Trash contains an invalid or duplicate entry.")
            trash_ids.add(entry["id"])
        for project in [*self._registry["projects"], *(entry["project"] for entry in trash)]:
            if type(project) is not dict or type(project.get("id")) is not str or not _ID.fullmatch(project["id"]) or project["id"] in seen:
                raise DomainError("invalid_workspace", "Invalid or duplicate project identity.")
            seen.add(project["id"])
            directory = self._entry_path(project)
            key = os.path.normcase(str(directory))
            if key in directories:
                raise DomainError("invalid_workspace", "Two catalog projects refer to the same folder.")
            directories.add(key)
            checked_name(project.get("name"))
            systems = project.get("systems")
            if type(systems) is not list:
                raise DomainError("invalid_workspace", "Project systems must be an array.")
            ids = set()
            for system in systems:
                if type(system) is not dict or type(system.get("id")) is not str or not _ID.fullmatch(system["id"]) or system["id"] in ids or type(system.get("read_only")) is not bool:
                    raise DomainError("invalid_workspace", "Invalid or duplicate system identity.")
                checked_name(system.get("name"))
                if type(system.get("top_module", "top")) is not str or not _identifier(system.get("top_module", "top")):
                    raise DomainError("invalid_workspace", "Invalid system top module.")
                ids.add(system["id"])

    def _save(self, value):
        # Each folder carries its own portable catalog entry. Write markers
        # before the workspace index: a crash can be recovered by Open folder.
        # Failed index writes roll back already replaced markers byte-for-byte.
        changed = []
        try:
            for project in value["projects"]:
                original = next((p for p in self._registry["projects"] if p["id"] == project["id"]), None)
                path = self._entry_path(project) / PROJECT_MANIFEST
                if _io_path(path).is_symlink() or (_io_path(path).exists() and getattr(_io_path(path).lstat(), "st_file_attributes", 0) & 0x400):
                    raise DomainError("unsafe_project_directory", "The project manifest cannot be a linked file.")
                if original == project and _io_path(path).is_file():
                    continue
                before = _io_path(path).read_bytes() if _io_path(path).exists() else None
                manifest = {"format": "hullcirq-project", "version": "1", "project": self._portable_project(project)}
                if before is not None and strict_loads(before.decode("utf-8")) == manifest:
                    continue
                write_json(path, manifest)
                changed.append((path, before))
            write_json(self.registry_path, value)
        except Exception:
            for path, before in reversed(changed):
                if before is None:
                    _io_path(path).unlink(missing_ok=True)
                else:
                    # The original marker is valid JSON; atomic write preserves
                    # its metadata. Raw formatting is retained on rollback too.
                    descriptor, temporary = tempfile.mkstemp(prefix=".workspace-", suffix=".tmp", dir=_io_path(path.parent))
                    try:
                        with os.fdopen(descriptor, "wb") as stream:
                            stream.write(before)
                            stream.flush()
                            os.fsync(stream.fileno())
                        os.replace(_io_path(temporary), _io_path(path))
                    finally:
                        if _io_path(temporary).exists():
                            _io_path(temporary).unlink()
            raise
        self._registry = value

    @staticmethod
    def _portable_project(project):
        return {k: copy.deepcopy(v) for k, v in project.items() if k not in ("directory", "available", "unavailable_reason", "management_revision")}

    def _all_projects(self):
        return [*self._registry["projects"], *(entry["project"] for entry in self._registry.get("trash", []))]

    def _entry_path(self, project):
        directory = project.get("directory")
        return checked_directory(directory) if directory is not None else checked_directory(self.root / "projects" / project["id"])

    def _project(self, project_id):
        project = next((p for p in self._registry["projects"] if p["id"] == project_id), None)
        if project is None:
            raise DomainError("project_not_found", "Project does not exist in this workspace.", 404)
        return project

    def _system(self, project, system_id):
        system = next((s for s in project["systems"] if s["id"] == system_id), None)
        if system is None:
            raise DomainError("system_not_found", "System does not exist in this project.", 404)
        return system

    def _project_path(self, project_id):
        if type(project_id) is not str or not _ID.fullmatch(project_id):
            raise DomainError("project_not_found", "Invalid project identity.", 404)
        project = next((p for p in self._registry["projects"] if p["id"] == project_id), None)
        return self._entry_path(project) if project is not None else checked_directory(self.root / "projects" / project_id)

    def _system_path(self, project_id, system_id):
        if type(system_id) is not str or not _ID.fullmatch(system_id):
            raise DomainError("system_not_found", "Invalid system identity.", 404)
        return checked_directory(self._project_path(project_id) / "systems" / system_id)

    def _result(self, project, system=None):
        displayed = self._display_project(project)
        result = {"project_id": project["id"], "project": displayed}
        if system is not None:
            result.update(system_id=system["id"], system=next(s for s in displayed["systems"] if s["id"] == system["id"]))
        return result

    def _display_project(self, project):
        """Read current top names without mutating state/history or catalog bytes."""
        displayed = copy.deepcopy(project)
        displayed["directory"] = str(self._entry_path(project))
        displayed["management_revision"] = digest(project)
        for system in displayed["systems"]:
            path = checked_directory(self._entry_path(project) / "systems" / system["id"])
            state_path = path / "state.json"
            try:
                if path.is_symlink() or state_path.is_symlink():
                    raise DomainError("unsafe_system_file", "Linked system files are not permitted.")
                state = strict_loads(_io_path(state_path).read_text(encoding="utf-8"))
                top = state["design"]["settings"]["top_module"]
                if type(top) is not str:
                    raise ValueError("Invalid top module")
                system.update(top_module=top, available=True)
            except (DomainError, OSError, KeyError, TypeError, ValueError):
                system.update(available=False, unavailable_reason="System state is missing or malformed; it was not overwritten.")
        return displayed

    def catalog(self):
        with self.lock:
            from .components import ComponentLibrary
            value = copy.deepcopy(self._registry)
            value["projects"] = [self._display_project(p) for p in self._registry["projects"]]
            value["trash"] = [entry | {"project": self._display_project(entry["project"])}
                              for entry in self._registry.get("trash", [])]
            return value | {"components": ComponentLibrary(self.root / "components").catalog()}

    def validate_delete_project(self, project_id, expected_project_revision):
        """Check the visible catalog identity before a runtime closes its context."""
        with self.lock:
            project = self._project(project_id)
            if type(expected_project_revision) is not str or digest(project) != expected_project_revision:
                raise DomainError("project_management_changed", "The project changed. Refresh Projects and confirm deletion again.", 409)
            return copy.deepcopy(project)

    def delete_project(self, project_id, expected_project_revision):
        """Move only catalog metadata to Trash. All project bytes stay in place."""
        with self.lock:
            project = self.validate_delete_project(project_id, expected_project_revision)
            entry = {"id": new_id("trash"), "project": project, "deleted_at": utc_now()}
            value = copy.deepcopy(self._registry)
            value["projects"] = [p for p in value["projects"] if p["id"] != project_id]
            value["recent"] = [r for r in value.get("recent", []) if r.get("project_id") != project_id]
            value.setdefault("trash", []).append(entry)
            # Unlike _save, deletion never refreshes portable folder manifests.
            write_json(self.registry_path, value)
            self._registry = value
            return copy.deepcopy(entry)

    def restore_deleted_project(self, trash_id, expected_project_revision):
        """Restore the same identities and path without executing or editing stores."""
        with self.lock:
            entry = next((item for item in self._registry.get("trash", []) if item["id"] == trash_id), None)
            if entry is None:
                raise DomainError("trash_not_found", "This project is no longer in Trash. Refresh the project list.", 404)
            project = entry["project"]
            if type(expected_project_revision) is not str or digest(project) != expected_project_revision:
                raise DomainError("project_management_changed", "The Trash entry changed. Refresh Trash before restoring it.", 409)
            path = self._entry_path(project)
            if any(p["id"] == project["id"] or path.is_relative_to(self._entry_path(p))
                   or self._entry_path(p).is_relative_to(path) for p in self._registry["projects"]):
                raise DomainError("project_identity_conflict", "Restore stopped because this project identity or folder is already in use.", 409)
            marker = path / PROJECT_MANIFEST
            try:
                if not _io_path(marker).is_file() or _io_path(marker).is_symlink() or getattr(_io_path(marker).lstat(), "st_file_attributes", 0) & 0x400:
                    raise ValueError("Unavailable project manifest")
                manifest = strict_loads(_io_path(marker).read_text(encoding="utf-8"))
                expected = {"format": "hullcirq-project", "version": "1", "project": self._portable_project(project)}
                if manifest != expected:
                    raise ValueError("Project manifest changed")
            except (OSError, UnicodeError, DomainError, ValueError) as error:
                raise DomainError("trash_project_unavailable", "The retained project folder is missing or its manifest changed. Restore did not overwrite any files.", 409) from error
            value = copy.deepcopy(self._registry)
            value["trash"] = [item for item in value.get("trash", []) if item["id"] != trash_id]
            value["projects"].append(copy.deepcopy(project))
            write_json(self.registry_path, value)
            self._registry = value
            return self._result(project)

    def resolve_system(self, project_id, system_id):
        with self.lock:
            project = self._project(project_id)
            system = self._system(project, system_id)
            path = self._system_path(project_id, system_id)
            state_path = path / "state.json"
            if not _io_path(state_path).is_file() or _io_path(state_path).is_symlink() or getattr(_io_path(state_path).lstat(), "st_file_attributes", 0) & 0x400:
                raise DomainError("system_missing", "System files are unavailable; the catalog was not modified.", 409)
            return self._result(project, system) | {"path": path, "read_only": system["read_only"]}

    def mark_opened(self, project_id, system_id):
        with self.lock:
            self.resolve_system(project_id, system_id)
            value = copy.deepcopy(self._registry)
            value["recent"] = [{"project_id": project_id, "system_id": system_id, "opened_at": utc_now()}] + [r for r in value.get("recent", []) if (r["project_id"], r["system_id"]) != (project_id, system_id)][:19]
            self._save(value)

    mark_recent = mark_opened

    def create_project(self, name, system_name="Main", top_module="top", project_directory=None):
        with self.lock:
            project_id, system_id, now = new_id("project"), new_id("system"), utc_now()
            name, system_name = checked_name(name, "Project name"), checked_name(system_name, "System name")
            design = blank_design(project_id, name, system_id, system_name, top_module)
            system = {"id": system_id, "name": system_name, "top_module": top_module, "created_at": now, "read_only": False, "origin": {"kind": "new"}}
            project = {"id": project_id, "name": name, "created_at": now, "updated_at": now, "systems": [system]}
            path = checked_directory(project_directory) if project_directory is not None else self._project_path(project_id)
            if any(path.is_relative_to(self._entry_path(p)) or self._entry_path(p).is_relative_to(path) for p in self._all_projects()):
                raise DomainError("project_directory_in_use", "Choose a separate folder outside existing project folders.", 409)
            if _io_path(path).exists() and any(_io_path(path).iterdir()):
                raise DomainError("project_directory_not_empty", "Choose a new or empty project folder; existing files will not be overwritten.", 409)
            existed = _io_path(path).exists()
            project["directory"] = str(path)
            try:
                write_json(path / "systems" / system_id / "state.json", new_state(design))
                value = copy.deepcopy(self._registry)
                value["projects"].append(project)
                self._save(value)
            except Exception:
                if _io_path(path).exists():
                    if existed:
                        systems = path / "systems"
                        if _io_path(systems).exists():
                            remove_owned_tree(systems, path)
                    else:
                        remove_owned_tree(path, path)
                raise
            return self._result(project, system)

    def register_project_directory(self, directory):
        """Open an explicit project folder without importing execution or evidence."""
        with self.lock:
            path = checked_directory(directory)
            if any(path == self._entry_path(entry["project"]) for entry in self._registry.get("trash", [])):
                raise DomainError("project_in_trash", "This project is in Trash. Restore it from Projects > Trash before opening its folder.", 409)
            marker = path / PROJECT_MANIFEST
            if not _io_path(marker).is_file() or _io_path(marker).is_symlink() or getattr(_io_path(marker).lstat(), "st_file_attributes", 0) & 0x400:
                raise DomainError("project_manifest_missing", "This folder does not contain a regular hullcirq.project.json file.", 409)
            try:
                manifest = strict_loads(_io_path(marker).read_text(encoding="utf-8"))
            except (OSError, UnicodeError, DomainError) as error:
                raise DomainError("invalid_project_manifest", "The project manifest cannot be read as strict UTF-8 JSON.") from error
            if type(manifest) is not dict or set(manifest) != {"format", "version", "project"} or manifest["format"] != "hullcirq-project" or manifest["version"] != "1" or type(manifest["project"]) is not dict:
                raise DomainError("invalid_project_manifest", "Unsupported project folder manifest.")
            project = copy.deepcopy(manifest["project"])
            project["directory"] = str(path)
            if any(entry["project"]["id"] == project.get("id") for entry in self._registry.get("trash", [])):
                raise DomainError("project_in_trash", "This project identity is in Trash. Restore the retained project from Projects > Trash.", 409)
            if type(project.get("systems")) is not list or not project["systems"]:
                raise DomainError("invalid_project_manifest", "The project requires at least one saved system.")
            existing = next((p for p in self._registry["projects"] if p["id"] == project.get("id")), None)
            if existing is not None:
                if self._entry_path(existing) != path:
                    raise DomainError("project_identity_conflict", "This project identity is already registered at another folder; use Duplicate for a copy.", 409)
                project = copy.deepcopy(existing)
            elif any(path.is_relative_to(self._entry_path(p)) or self._entry_path(p).is_relative_to(path) for p in self._all_projects()):
                raise DomainError("project_directory_in_use", "Choose a separate folder outside existing project folders.", 409)
            candidate = copy.deepcopy(self._registry)
            if existing is None:
                candidate["projects"].append(project)
            # Reuse catalog validation without changing the current registry.
            previous = self._registry
            try:
                self._registry = candidate
                self._validate_catalog()
            finally:
                self._registry = previous
            for system in project["systems"]:
                system_path = checked_directory(path / "systems" / system["id"])
                state_path = system_path / "state.json"
                if not _io_path(state_path).is_file() or _io_path(state_path).is_symlink() or getattr(_io_path(state_path).lstat(), "st_file_attributes", 0) & 0x400:
                    raise DomainError("invalid_project_state", "Every declared system requires a regular state.json file.")
                try:
                    _validate_saved_state(strict_loads(_io_path(state_path).read_text(encoding="utf-8")))
                except (OSError, UnicodeError, DomainError) as error:
                    raise DomainError("invalid_project_state", "A saved system state is invalid; no project was registered.") from error
            if existing is None:
                # Register only the local catalog. The folder's original marker
                # and all retained state/history bytes remain untouched.
                write_json(self.registry_path, candidate)
                self._registry = candidate
            return self._result(project, project["systems"][0])

    def refresh_project_manifest(self, project_id):
        """Persist display metadata after a saved design changes its top module."""
        with self.lock:
            self._project(project_id)
            value = copy.deepcopy(self._registry)
            project = next(p for p in value["projects"] if p["id"] == project_id)
            displayed = self._display_project(project)
            for system in project["systems"]:
                saved = next(s for s in displayed["systems"] if s["id"] == system["id"])
                if saved.get("available"):
                    system["top_module"] = saved["top_module"]
            project["updated_at"] = utc_now()
            self._save(value)

    def create_system(self, project_id, name, top_module="top"):
        with self.lock:
            original = self._project(project_id)
            name = checked_name(name, "System name")
            if any(s["name"].casefold() == name.casefold() for s in original["systems"]):
                raise DomainError("duplicate_system_name", "A system with this name already exists.", 409)
            sid, now = new_id("system"), utc_now()
            design = blank_design(project_id, original["name"], sid, name, top_module)
            system = {"id": sid, "name": name, "top_module": top_module, "created_at": now, "read_only": False, "origin": {"kind": "new"}}
            path = self._system_path(project_id, sid)
            try:
                write_json(path / "state.json", new_state(design))
                value = copy.deepcopy(self._registry)
                project = next(p for p in value["projects"] if p["id"] == project_id)
                project["systems"].append(system)
                project["updated_at"] = now
                self._save(value)
            except Exception:
                if _io_path(path).exists():
                    remove_owned_tree(path, self._project_path(project_id))
                raise
            return self._result(project, system)

    def rename_project(self, project_id, name):
        with self.lock:
            self._project(project_id)
            value = copy.deepcopy(self._registry)
            project = next(p for p in value["projects"] if p["id"] == project_id)
            project.update(name=checked_name(name, "Project name"), updated_at=utc_now())
            self._save(value)
            return self._result(project)

    def rename_system(self, project_id, system_id, name):
        with self.lock:
            project = self._project(project_id)
            self._system(project, system_id)
            name = checked_name(name, "System name")
            if any(s["id"] != system_id and s["name"].casefold() == name.casefold() for s in project["systems"]):
                raise DomainError("duplicate_system_name", "A system with this name already exists.", 409)
            value = copy.deepcopy(self._registry)
            project = next(p for p in value["projects"] if p["id"] == project_id)
            system = next(s for s in project["systems"] if s["id"] == system_id)
            system["name"] = name
            project["updated_at"] = utc_now()
            self._save(value)
            return self._result(project, system)

    def register_legacy(self, path, name=None, system_name="Legacy system"):
        """Copy JSON stores only. Original stores and external run artifacts stay untouched."""
        with self.lock:
            source = Path(path).resolve()
            if any(source.is_relative_to(self._entry_path(entry["project"])) for entry in self._registry.get("trash", [])) or any(system.get("origin", {}).get("kind") == "legacy_snapshot"
                   and system["origin"].get("original_path") == str(source)
                   for entry in self._registry.get("trash", []) for system in entry["project"]["systems"]):
                raise DomainError("project_in_trash", "This legacy snapshot is in Trash. Restore its retained project before registering it again.", 409)
            for project in self._registry["projects"]:
                for system in project["systems"]:
                    if system.get("origin", {}).get("kind") == "legacy_snapshot" and system["origin"].get("original_path") == str(source):
                        return self._result(project, system)
            raw = _io_path(source / "state.json").read_bytes()
            state = strict_loads(raw.decode("utf-8"))
            _validate_saved_state(state)
            project_id, system_id, now = new_id("project"), new_id("system"), utc_now()
            origin = {"kind": "legacy_snapshot", "original_path": str(source), "captured_at": now, "files": [],
                      "external_artifacts": "Referenced by their original recorded locations; not copied or re-executed."}
            system = {"id": system_id, "name": checked_name(system_name), "top_module": state["design"]["settings"]["top_module"], "created_at": now, "read_only": True, "origin": origin}
            project = {"id": project_id, "name": checked_name(name or state["design"]["project"]["name"]), "created_at": now, "updated_at": now, "systems": [system]}
            target = self._system_path(project_id, system_id)
            try:
                _io_path(target).mkdir(parents=True)
                for item in sorted(_io_path(source).glob("*.json")):
                    if item.is_symlink() or not item.is_file():
                        raise DomainError("unsafe_legacy_file", "Legacy snapshot cannot include linked files.")
                    data = _io_path(item).read_bytes()
                    _io_path(target / item.name).write_bytes(data)
                    origin["files"].append({"path": item.name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
                value = copy.deepcopy(self._registry)
                value["projects"].append(project)
                self._save(value)
            except Exception:
                if _io_path(target.parent.parent).exists():
                    remove_owned_tree(target.parent.parent, self._project_path(project_id))
                raise
            return self._result(project, system)

    def _duplicate_into(self, source, project, name):
        from .physical_tools import artifact_files, io_path, read_bytes
        old_path = self._system_path(source["project_id"], source["system_id"])
        try:
            retained = list(artifact_files(old_path, reject_links=True))
        except DomainError as error:
            raise DomainError("unsafe_system_file", "System copies cannot include linked files or directories.") from error
        raw = read_bytes(old_path / "state.json")
        state = strict_loads(raw.decode("utf-8"))
        _validate_saved_state(state)
        sid, now = new_id("system"), utc_now()
        design = copy.deepcopy(state["design"])
        design["project"] = {"id": project["id"], "name": project["name"]}
        design["system"] = {"id": sid, "name": checked_name(name)}
        design["copy_provenance"] = {"project_id": source["project_id"], "system_id": source["system_id"], "revision_id": state["revision"]["id"], "captured_at": now,
                                     "evidence_scope": "Source history only. No results or adoption transferred to this editable copy."}
        system = {"id": sid, "name": design["system"]["name"], "top_module": design["settings"]["top_module"], "created_at": now, "read_only": False,
                  "origin": {"kind": "duplicate", "project_id": source["project_id"], "system_id": source["system_id"], "revision_id": state["revision"]["id"], "history_snapshot": "provenance_snapshot"}}
        path = self._system_path(project["id"], sid)
        io_path(path).mkdir(parents=True)
        for item in retained:
            relative = item.relative_to(old_path)
            destination = path / "provenance_snapshot" / relative
            io_path(destination.parent).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(io_path(item), io_path(destination))
        write_json(path / "state.json", new_state(design))
        project["systems"].append(system)
        return system

    def duplicate_system(self, project_id, system_id, name=None, target_project_id=None):
        with self.lock:
            source = self.resolve_system(project_id, system_id)
            target_id = target_project_id or project_id
            self._project(target_id)
            value = copy.deepcopy(self._registry)
            project = next(p for p in value["projects"] if p["id"] == target_id)
            name = checked_name(name or source["system"]["name"] + " copy")
            if any(s["name"].casefold() == name.casefold() for s in project["systems"]):
                raise DomainError("duplicate_system_name", "A system with this name already exists.", 409)
            project_path = self._project_path(target_id)
            io_project_path = _io_path(project_path)
            before = {project_path / child.relative_to(io_project_path)
                      for child in io_project_path.glob("systems/*")}
            try:
                system = self._duplicate_into(source, project, name)
                project["updated_at"] = utc_now()
                self._save(value)
            except Exception:
                after = {project_path / child.relative_to(io_project_path)
                         for child in io_project_path.glob("systems/*")}
                for new_path in after - before:
                    remove_owned_tree(new_path, project_path)
                raise
            return self._result(project, system)

    def create_array_variant(self, project_id, system_id, name):
        """Explicit saved-design conversion into a separate result-free project.

        No candidate, tool run, review, provider profile or adoption policy is
        transferred. The source project and its histories remain untouched.
        """
        from .npu2_array_verification import collapse_explicit_design, recognize_design
        with self.lock:
            source = self.resolve_system(project_id, system_id)
            source_path = source["path"] / "state.json"
            raw = _io_path(source_path).read_bytes()
            state = strict_loads(raw.decode("utf-8"))
            _validate_saved_state(state)
            design = collapse_explicit_design(state["design"])
            pid, sid, now = new_id("project"), new_id("system"), utc_now()
            name = checked_name(name, "Project name")
            design["project"] = {"id": pid, "name": name}
            design["system"] = {"id": sid, "name": "Shared PE 2x2"}
            # Old explicit-node regions cannot address the new shared node.
            design.pop("physical_design", None)
            provenance = {"kind": "explicit_to_shared_pe_array_v1", "project_id": project_id,
                          "system_id": system_id, "revision_id": state["revision"]["id"],
                          "source_state_sha256": hashlib.sha256(raw).hexdigest(), "captured_at": now,
                          "evidence_scope": "Design conversion only. No runs, reviews or adoption transferred."}
            design["copy_provenance"] = copy.deepcopy(provenance)
            validate_shape(design)
            recognize_design(design)
            system = {"id": sid, "name": design["system"]["name"], "top_module": design["settings"]["top_module"],
                      "created_at": now, "read_only": False, "origin": copy.deepcopy(provenance)}
            project = {"id": pid, "name": name, "created_at": now, "updated_at": now,
                       "systems": [system], "origin": copy.deepcopy(provenance)}
            path = self._project_path(pid)
            try:
                write_json(path / "systems" / sid / "state.json", new_state(design))
                value = copy.deepcopy(self._registry)
                value["projects"].append(project)
                self._save(value)
            except Exception:
                if _io_path(path).exists():
                    remove_owned_tree(path, self.root / "projects" / pid)
                raise
            return self._result(project, system)

    def duplicate_project(self, project_id, name=None):
        with self.lock:
            source = self._project(project_id)
            pid, now = new_id("project"), utc_now()
            project = {"id": pid, "name": checked_name(name or source["name"] + " copy"), "created_at": now, "updated_at": now, "systems": [], "origin": {"kind": "duplicate", "project_id": project_id}}
            try:
                for system in source["systems"]:
                    self._duplicate_into(self._result(source, system), project, system["name"])
                value = copy.deepcopy(self._registry)
                value["projects"].append(project)
                self._save(value)
            except Exception:
                path = self._project_path(pid)
                if _io_path(path).exists():
                    remove_owned_tree(path, self.root / "projects" / pid)
                raise
            return self._result(project, project["systems"][0] if project["systems"] else None)

    def backup_project(self, project_id):
        with self.lock:
            from .components import ComponentLibrary
            project = copy.deepcopy(self._project(project_id))
            root = self._project_path(project_id)
            files, total, dependencies, external_paths = [], 0, set(), set()
            from .physical_tools import artifact_files
            try:
                retained_files = sorted(artifact_files(root, reject_links=True))
            except DomainError as error:
                raise DomainError("unsafe_system_file", "Backups cannot include linked or redirected files.") from error
            for path in retained_files:
                if _io_path(path).is_file():
                    relative = path.relative_to(root).as_posix()
                    if relative == PROJECT_MANIFEST:
                        continue
                    archive_path(relative)
                    data = _io_path(path).read_bytes()
                    total += len(data)
                    if total > MAX_BUNDLE_BYTES or len(files) >= MAX_BUNDLE_FILES:
                        raise DomainError("backup_limit", "Project exceeds the 2 GiB local backup limit; no data was changed.", 413)
                    files.append({"path": relative, "encoding": "gzip+base64", "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "data": base64.b64encode(gzip.compress(data, mtime=0)).decode("ascii")})
                    if path.name == "state.json":
                        state = strict_loads(data.decode("utf-8"))
                        dependencies.update(component_references(state))
                    if path.suffix == ".json":
                        try:
                            external_paths.update(external_path_references(strict_loads(data.decode("utf-8"))))
                        except (DomainError, UnicodeError):
                            # Opaque retained output is still backed up exactly.
                            pass
            library, packages, seen = ComponentLibrary(self.root / "components"), [], set()
            while dependencies - seen:
                cid, version = sorted(dependencies - seen)[0]
                package = library.package(cid, version)
                packages.append(package)
                seen.add((cid, version))
                dependencies.update(component_references(package))
            references = [{"system_id": s["id"], "origin": s["origin"], "scope": "Recorded external artifact and tool/PDK paths are references, not portable bundled dependencies."} for s in project["systems"]]
            references.append({"paths": sorted(external_paths), "scope": "Exact path strings retained from local history; no new existence/hash qualification and no external file copied."})
            value = {"format": "hullcirq-project-backup", "version": "1", "created_at": utc_now(), "project": project, "files": files,
                     "components": packages, "external_references": references, "restore_policy": "Read-only restored evidence. Duplicate a system to edit; no tool or configuration execution."}
            return value | {"checksum": digest(value)}

    def restore_project(self, bundle, name=None):
        with self.lock:
            from .components import ComponentLibrary, validate_package
            if type(bundle) is not dict or bundle.get("format") != "hullcirq-project-backup" or bundle.get("version") != "1":
                raise DomainError("invalid_backup", "Unsupported backup package.")
            content = {k: v for k, v in bundle.items() if k != "checksum"}
            if type(bundle.get("checksum")) is not str or digest(content) != bundle["checksum"]:
                raise DomainError("backup_checksum", "Backup checksum does not match.")
            original, entries = bundle.get("project"), bundle.get("files")
            if type(original) is not dict or type(original.get("systems")) is not list or not original["systems"] or type(entries) is not list or len(entries) > MAX_BUNDLE_FILES:
                raise DomainError("invalid_backup", "Backup manifest is malformed.")
            checked_name(original.get("name"))
            old_ids = []
            for system in original["systems"]:
                if type(system) is not dict or type(system.get("id")) is not str or not _ID.fullmatch(system["id"]) or system["id"] in old_ids:
                    raise DomainError("invalid_backup", "Backup has invalid system identities.")
                checked_name(system.get("name"))
                old_ids.append(system["id"])
            decoded, paths, total = [], set(), 0
            for entry in entries:
                if type(entry) is not dict:
                    raise DomainError("invalid_backup", "Backup file entry is malformed.")
                parts = archive_path(entry.get("path"))
                if len(parts) < 3 or parts[0] != "systems" or parts[1] not in old_ids or entry.get("encoding") != "gzip+base64" or entry["path"].casefold() in paths:
                    raise DomainError("invalid_backup", "Backup file path is invalid or repeated.")
                paths.add(entry["path"].casefold())
                size = entry.get("size")
                if type(size) is not int or size < 0 or total + size > MAX_BUNDLE_BYTES or type(entry.get("data")) is not str:
                    raise DomainError("backup_limit", "Backup exceeds the 2 GiB decoded limit.", 413)
                try:
                    compressed = base64.b64decode(entry["data"], validate=True)
                    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
                    data = decoder.decompress(compressed, size + 1)
                    if len(data) != size or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                        raise ValueError("Invalid compressed size")
                except (ValueError, TypeError, zlib.error) as error:
                    raise DomainError("invalid_backup", "Backup compressed data is malformed.") from error
                if hashlib.sha256(data).hexdigest() != entry.get("sha256"):
                    raise DomainError("backup_checksum", "A backup file checksum does not match.")
                total += size
                decoded.append((parts, data))
            for sid in old_ids:
                raw = next((data for parts, data in decoded if parts == ["systems", sid, "state.json"]), None)
                if raw is None:
                    raise DomainError("invalid_backup", "Every restored system requires a state snapshot.")
                try:
                    _validate_saved_state(strict_loads(raw.decode("utf-8")))
                except (UnicodeError, DomainError) as error:
                    raise DomainError("invalid_backup", "A restored state snapshot is invalid.") from error
            component_packages = bundle.get("components", [])
            if type(component_packages) is not list:
                raise DomainError("invalid_backup", "Backup components must be an array.")
            library, pinned = ComponentLibrary(self.root / "components"), {}
            for package in component_packages:
                validate_package(package)
                identity = (package["component"]["id"], package["component"]["version"])
                if identity in pinned:
                    raise DomainError("invalid_backup", "Backup repeats a component version.")
                pinned[identity] = package
                existing = library._path(*identity)
                if existing.exists() and library.package(*identity) != package:
                    raise DomainError("component_version_conflict", "A restored component conflicts with an immutable local version.", 409)
            dependencies = set()
            for parts, data in decoded:
                if parts[-1] == "state.json":
                    dependencies.update(component_references(strict_loads(data.decode("utf-8"))))
            for package in pinned.values():
                dependencies.update(component_references(package))
            if dependencies - set(pinned):
                raise DomainError("backup_dependency_missing", "Backup omits a pinned component dependency.")
            pid, now = new_id("project"), utc_now()
            mapping = {sid: new_id("system") for sid in old_ids}
            project = {"id": pid, "name": checked_name(name or original["name"] + " restored"), "created_at": now, "updated_at": now, "systems": [],
                       "origin": {"kind": "backup_restore", "source_project_id": original.get("id"), "source_directory": original.get("directory"), "backup_checksum": bundle["checksum"], "external_references": bundle.get("external_references", [])}}
            for old in original["systems"]:
                project["systems"].append({"id": mapping[old["id"]], "name": old["name"], "top_module": old.get("top_module", "top"), "created_at": now, "read_only": True,
                                           "origin": {"kind": "backup_restore", "source_system_id": old["id"], "backup_checksum": bundle["checksum"], "external_artifacts": "Original references only. Runtime configuration is not imported for execution."}})
            path = self._project_path(pid)
            added_components = []
            try:
                for parts, data in decoded:
                    destination = path / "systems" / mapping[parts[1]] / Path(*parts[2:])
                    _io_path(destination.parent).mkdir(parents=True, exist_ok=True)
                    _io_path(destination).write_bytes(data)
                for identity, package in pinned.items():
                    destination = library._path(*identity)
                    existed = _io_path(destination).exists()
                    library.import_package(package)
                    if not existed:
                        added_components.append(destination)
                value = copy.deepcopy(self._registry)
                value["projects"].append(project)
                self._save(value)
            except Exception:
                if _io_path(path).exists():
                    remove_owned_tree(path, self.root / "projects" / pid)
                for destination in added_components:
                    _io_path(destination).unlink(missing_ok=True)
                raise
            return self._result(project, project["systems"][0])

    def publish_component(self, project_id, system_id, node_ids=None, name=None, public_ports=None, component_id=None):
        from .components import ComponentLibrary
        with self.lock:
            resolved = self.resolve_system(project_id, system_id)
            return ComponentLibrary(self.root / "components").publish(resolved, node_ids, name, public_ports, component_id)

    def component_package(self, component_id, version):
        from .components import ComponentLibrary
        return ComponentLibrary(self.root / "components").package(component_id, version)

    def import_component_package(self, package):
        from .components import ComponentLibrary
        with self.lock:
            return ComponentLibrary(self.root / "components").import_package(package)

    def instantiate_component(self, project_id, system_id, component_id, version, expected_revision_id, instance_name):
        from .components import ComponentLibrary
        with self.lock:
            resolved = self.resolve_system(project_id, system_id)
            if resolved["read_only"]:
                raise DomainError("read_only_system", "Duplicate this evidence system before editing.", 409)
            return ComponentLibrary(self.root / "components").instantiate(resolved, component_id, version, expected_revision_id, instance_name)

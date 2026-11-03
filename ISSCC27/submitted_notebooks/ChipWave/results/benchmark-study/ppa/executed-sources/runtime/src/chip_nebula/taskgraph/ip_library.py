"""Immutable local IP packages, qualification evidence and dependency locks."""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import itertools
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

import yaml

from chip_nebula.taskgraph.tool_executor import DeterministicToolExecutor, ToolCommand
from chip_nebula.taskgraph.memory_generator import MemoryGenerator
from chip_nebula.taskgraph.generated_submodule import (
    GeneratedSubmoduleError, source_record,
)


_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
_SV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?$")
_HARD_MACRO_VIEWS = {
    "lef": "lef", "gds": "gds", "liberty": "liberty",
    "verilog_blackbox": "verilogBlackbox",
}


def _implementation_kind(manifest: Mapping[str, Any]) -> str:
    implementation = manifest.get("implementation", {})
    return implementation.get("kind", "soft_rtl") if isinstance(implementation, Mapping) else "invalid"


def _require_rtl_implementation(package: "IPPackage") -> None:
    if _implementation_kind(package.manifest) == "hard_macro":
        raise IPLibraryError(
            f"hard macro {package.key} has no supported physical integration flow; "
            "declared views alone do not qualify it for automatic RTL/GDS assembly"
        )


class IPLibraryError(ValueError):
    pass


@dataclass(frozen=True)
class IPPackage:
    package_id: str
    version: str
    content_digest: str
    root: Path
    manifest: dict[str, Any]

    @property
    def key(self) -> str:
        return f"{self.package_id}@{self.version}"

    def to_dict(self, *, evidence: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        review = self.manifest.get("source", {}).get("review", {})
        passed = [item for item in evidence or [] if item.get("verdict") == "passed"]
        implementation = self.manifest.get("implementation", {"kind": "soft_rtl"})
        if not isinstance(implementation, Mapping):
            implementation = {}
        hard_macro = _implementation_kind(self.manifest) == "hard_macro"
        return {
            "package_id": self.package_id,
            "version": self.version,
            "key": self.key,
            "content_digest": self.content_digest,
            "top_module": self.manifest["top_module"],
            "source_kind": self.manifest["source"]["kind"],
            "origin": self.manifest["source"]["origin"],
            "license": self.manifest["source"]["license"],
            "review_status": review.get("status", "pending"),
            "capabilities": list(self.manifest.get("capabilities", [])),
            "interfaces": copy.deepcopy(self.manifest.get("interfaces", [])),
            "ports": copy.deepcopy(self.manifest.get("ports", [])),
            "generator": copy.deepcopy(self.manifest.get("generator", {})),
            "parameters": copy.deepcopy(self.manifest.get("parameters", [])),
            "deprecated": bool(self.manifest.get("deprecated", False)),
            "implementation_kind": _implementation_kind(self.manifest),
            "technology": implementation.get("technology", ""),
            "corner": implementation.get("corner", ""),
            "physical_views": copy.deepcopy(implementation.get("views", {})),
            "physical_status": "declared_unintegrated" if hard_macro else "not_required",
            "qualification": (
                "pending_physical" if hard_macro else
                "qualified" if passed and review.get("status") == "approved"
                else "pending"
            ),
            "qualified_configurations": [item.get("parameters", {}) for item in passed],
            "evidence": evidence or [],
        }


@dataclass(frozen=True)
class IPResolution:
    lock: dict[str, Any]
    decisions: tuple[dict[str, Any], ...]


class IPLibrary:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.root = self.project_root / ".chip_nebula" / "ip-library"
        self.packages_root = self.root / "packages"
        self.evidence_root = self.root / "evidence"
        self.lock_path = self.project_root / "ip" / "nebula.lock.json"

    def import_package(
        self, source: Path, *, provenance: Mapping[str, Any] | None = None,
    ) -> IPPackage:
        source = source.expanduser().resolve()
        manifest_path = source / "chip-nebula-ip.yaml"
        if not manifest_path.is_file():
            raise IPLibraryError("IP package requires chip-nebula-ip.yaml")
        manifest = _load_manifest(manifest_path)
        package_id, version = _validate_manifest(source, manifest)
        digest = _package_digest(source, manifest)
        existing = self.find(package_id, version)
        if existing and existing.content_digest != digest:
            raise IPLibraryError(
                f"immutable package version conflict: {package_id}@{version}"
            )
        if existing:
            self.verify_package(existing)
            return existing
        target = (
            self.packages_root / _slug(package_id) / version
            / digest.removeprefix("sha256:")
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.mkdir(parents=True)
            shutil.copy2(manifest_path, target / "chip-nebula-ip.yaml")
            for item in manifest["files"]:
                relative = Path(_safe_relative(item["path"]))
                destination = target / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / relative, destination)
        (target / ".nebula-package.json").write_text(
            json.dumps({
                "package_id": package_id, "version": version,
                "content_digest": digest,
                "imported_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "provenance": dict(provenance or {}),
            }, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return IPPackage(package_id, version, digest, target, manifest)

    def import_git(
        self, repository: str, ref: str, *, subdirectory: str = "",
    ) -> IPPackage:
        """Import one explicitly requested Git revision without executing it."""
        if not repository.strip() or not ref.strip():
            raise IPLibraryError("Git repository and ref are required")
        if not shutil.which("git"):
            raise IPLibraryError("git is unavailable")
        relative = _safe_relative(subdirectory) if subdirectory else ""
        with tempfile.TemporaryDirectory(prefix="chip-nebula-ip-git-") as temporary:
            checkout = Path(temporary) / "checkout"
            commands = [
                ["git", "init", "--quiet", str(checkout)],
                ["git", "-C", str(checkout), "remote", "add", "origin", repository],
                ["git", "-C", str(checkout), "fetch", "--quiet", "--depth", "1", "origin", ref],
                ["git", "-C", str(checkout), "checkout", "--quiet", "--detach", "FETCH_HEAD"],
            ]
            try:
                for command in commands:
                    subprocess.run(
                        command, check=True, capture_output=True, text=True,
                        timeout=120, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                    )
                commit = subprocess.run(
                    ["git", "-C", str(checkout), "rev-parse", "HEAD"],
                    check=True, capture_output=True, text=True, timeout=15,
                ).stdout.strip()
            except (OSError, subprocess.SubprocessError) as exc:
                detail = getattr(exc, "stderr", "") or str(exc)
                raise IPLibraryError(f"cannot fetch requested Git revision: {detail.strip()}") from exc
            source = checkout / relative if relative else checkout
            return self.import_package(source, provenance={
                "kind": "git", "repository": repository, "requested_ref": ref,
                "commit": commit, "subdirectory": relative,
            })

    def import_builtins(self, configs_root: Path) -> list[IPPackage]:
        result: list[IPPackage] = []
        if not configs_root.is_dir():
            return result
        for manifest in sorted(configs_root.rglob("chip-nebula-ip.yaml")):
            result.append(self.import_package(manifest.parent))
        return result

    def packages(self) -> list[IPPackage]:
        result: list[IPPackage] = []
        if not self.packages_root.is_dir():
            return result
        for metadata in sorted(self.packages_root.rglob(".nebula-package.json")):
            try:
                record = json.loads(metadata.read_text(encoding="utf-8"))
                manifest = _load_manifest(metadata.parent / "chip-nebula-ip.yaml")
                result.append(IPPackage(
                    record["package_id"], record["version"],
                    record["content_digest"], metadata.parent, manifest,
                ))
            except (OSError, KeyError, json.JSONDecodeError, IPLibraryError):
                continue
        return result

    def catalog(self) -> list[dict[str, Any]]:
        result = []
        for package in self.packages():
            record = package.to_dict(evidence=self.evidence(package))
            try:
                self.verify_package(package)
                record["integrity"] = "valid"
            except IPLibraryError as exc:
                record.update({
                    "integrity": "corrupted", "qualification": "invalid",
                    "integrity_error": str(exc),
                })
            result.append(record)
        return result

    def find(self, package_id: str, version: str = "") -> IPPackage | None:
        matches = [
            item for item in self.packages()
            if item.package_id == package_id and (not version or item.version == version)
        ]
        return sorted(matches, key=lambda item: _version_key(item.version), reverse=True)[0] if matches else None

    def verify_package(self, package: IPPackage) -> None:
        try:
            package_id, version = _validate_manifest(package.root, package.manifest)
            digest = _package_digest(package.root, package.manifest)
        except (OSError, IPLibraryError) as exc:
            raise IPLibraryError(f"immutable IP package is corrupted: {package.key}: {exc}") from exc
        if (
            package_id != package.package_id
            or version != package.version
            or digest != package.content_digest
        ):
            raise IPLibraryError(f"immutable IP package digest changed: {package.key}")

    def dependency_closure(self, package: IPPackage) -> list[IPPackage]:
        """Return exact transitive dependencies in compile order."""
        ordered: list[IPPackage] = []
        completed: set[str] = set()

        def visit(current: IPPackage, trail: tuple[str, ...]) -> None:
            if current.key in trail:
                raise IPLibraryError(
                    "cyclic IP dependency: " + " -> ".join((*trail, current.key))
                )
            for declaration in current.manifest.get("dependencies", []):
                dependency = self._dependency_package(declaration)
                visit(dependency, (*trail, current.key))
                if dependency.key not in completed:
                    ordered.append(dependency)
                    completed.add(dependency.key)

        visit(package, ())
        return ordered

    def _dependency_package(self, declaration: Mapping[str, Any]) -> IPPackage:
        package_id = str(declaration.get("package_id", ""))
        version = str(declaration.get("version", ""))
        dependency = self.find(package_id, version)
        if dependency is None:
            raise IPLibraryError(f"missing exact IP dependency: {package_id}@{version}")
        self.verify_package(dependency)
        _require_rtl_implementation(dependency)
        expected = str(declaration.get("content_digest", ""))
        if expected and dependency.content_digest != expected:
            raise IPLibraryError(f"IP dependency digest mismatch: {dependency.key}")
        if dependency.manifest["source"]["review"].get("status") != "approved":
            raise IPLibraryError(f"IP dependency is not approved: {dependency.key}")
        return dependency

    def evidence(self, package: IPPackage) -> list[dict[str, Any]]:
        directory = self.evidence_root / package.content_digest.removeprefix("sha256:")
        result: list[dict[str, Any]] = []
        if directory.is_dir():
            for path in sorted(directory.glob("*.json")):
                try:
                    value = json.loads(path.read_text(encoding="utf-8"))
                    if value.get("content_digest") == package.content_digest:
                        result.append(value)
                except (OSError, json.JSONDecodeError):
                    continue
        return result

    def validate(
        self, package_id: str, version: str, parameters: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        package = self.find(package_id, version)
        if package is None:
            raise IPLibraryError(f"unknown IP package: {package_id}@{version}")
        self.verify_package(package)
        verification = package.manifest.get("verification", {})
        commands = verification.get("commands", [])
        if not isinstance(commands, list) or not commands:
            raise IPLibraryError("IP package has no verification commands")
        requested = dict(parameters or {})
        configurations = [requested] if parameters is not None else verification.get("parameter_sets", [])
        if not configurations:
            configurations = [_defaults(package.manifest)]
        records: list[dict[str, Any]] = []
        for configuration in configurations:
            normalized = _validate_parameters(package.manifest, configuration)
            with tempfile.TemporaryDirectory(prefix="chip-nebula-ip-") as temporary:
                workspace = Path(temporary) / "package"
                shutil.copytree(package.root, workspace)
                dependency_files: list[str] = []
                dependency_digests: list[str] = []
                for dependency in self.dependency_closure(package):
                    destination = workspace / "deps" / (
                        f"{_slug(dependency.package_id)}_{dependency.version}"
                    )
                    shutil.copytree(dependency.root, destination)
                    dependency_digests.append(dependency.content_digest)
                    dependency_files.extend(
                        (destination.relative_to(workspace) / item["path"]).as_posix()
                        for item in dependency.manifest["files"]
                        if item["type"] in {
                            "systemVerilogSource", "verilogSource", "include"
                        }
                    )
                format_values = {
                    **normalized,
                    "dependency_files": " ".join(
                        shlex.quote(item) for item in dependency_files
                    ),
                }
                prepared = []
                for index, item in enumerate(commands):
                    if isinstance(item, str):
                        name, shell = f"command-{index + 1}", item
                        success = ""
                    elif isinstance(item, dict):
                        name = str(item.get("name", f"command-{index + 1}"))
                        shell = str(item.get("command", ""))
                        success = str(item.get("success_pattern", ""))
                    else:
                        raise IPLibraryError("verification commands must be strings or mappings")
                    try:
                        shell = shell.format_map(_StrictFormat(format_values))
                    except KeyError as exc:
                        raise IPLibraryError(f"unknown verification parameter: {exc.args[0]}") from exc
                    prepared.append(ToolCommand(
                        name, shell, ".", int(verification.get("timeout", 120)), success,
                    ))
                result = DeterministicToolExecutor().execute(workspace, prepared)
            record = {
                "package_id": package.package_id,
                "version": package.version,
                "content_digest": package.content_digest,
                "parameters": normalized,
                "configuration_digest": _digest(normalized),
                "status": result.status,
                "verdict": result.verdict,
                "commands": [asdict(item) for item in result.commands],
                "tool_versions": result.tool_versions,
                "dependency_digests": dependency_digests,
                "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
            destination = self.evidence_root / package.content_digest.removeprefix("sha256:")
            destination.mkdir(parents=True, exist_ok=True)
            (destination / f"{record['configuration_digest'].removeprefix('sha256:')}.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            records.append(record)
            if result.verdict != "passed":
                break
        return {"package": package.to_dict(evidence=self.evidence(package)), "records": records}

    def resolve(
        self, compiled_spec: Mapping[str, Any], *, prefer_locked: bool = True,
    ) -> IPResolution:
        if not compiled_spec.get("valid") or not compiled_spec.get("frozen"):
            raise IPLibraryError("IP resolution requires a valid frozen specification")
        document = compiled_spec["document"]
        spec_digest = str(compiled_spec["spec_digest"])
        current = self.read_lock(optional=True) if prefer_locked else {}
        direct_entries: list[dict[str, Any]] = []
        dependency_entries: dict[str, dict[str, Any]] = {}
        decisions: list[dict[str, Any]] = []
        generated_entries: list[dict[str, Any]] = []
        generated = MemoryGenerator(self.project_root).current(compiled_spec)
        generated_by_instance = {
            item["instance"]: item for item in generated["modules"]
        } if generated else {}
        package_versions: dict[str, str] = {}
        modules: dict[str, str] = {}

        def register(package: IPPackage) -> None:
            self.verify_package(package)
            _require_rtl_implementation(package)
            previous = package_versions.get(package.package_id)
            if previous and previous != package.version:
                raise IPLibraryError(
                    f"multiple code versions of {package.package_id} are not supported"
                )
            package_versions[package.package_id] = package.version
            top = str(package.manifest["top_module"])
            if top in modules and modules[top] != package.key:
                raise IPLibraryError(
                    f"SystemVerilog module name collision: {top} "
                    f"({modules[top]}, {package.key})"
                )
            modules[top] = package.key

        def fields(package: IPPackage) -> dict[str, Any]:
            return {
                "package_id": package.package_id,
                "version": package.version,
                "content_digest": package.content_digest,
                "top_module": package.manifest["top_module"],
                "files": [item["path"] for item in package.manifest["files"]],
                "file_types": {
                    item["path"]: item["type"] for item in package.manifest["files"]
                },
                "defines": list(package.manifest.get("defines", [])),
                "include_dirs": list(package.manifest.get("include_dirs", [])),
                "dependencies": copy.deepcopy(package.manifest.get("dependencies", [])),
                "interfaces": copy.deepcopy(package.manifest.get("interfaces", [])),
                "ports": copy.deepcopy(package.manifest.get("ports", [])),
            }

        def add_dependencies(
            owner: IPPackage, *, required_by: str, trail: tuple[str, ...] = (),
        ) -> None:
            if owner.key in trail:
                raise IPLibraryError(
                    "cyclic IP dependency: " + " -> ".join((*trail, owner.key))
                )
            for declaration in owner.manifest.get("dependencies", []):
                dependency = self._dependency_package(declaration)
                register(dependency)
                add_dependencies(
                    dependency, required_by=dependency.key,
                    trail=(*trail, owner.key),
                )
                parameters, configurations = _resolve_instance_parameters(
                    dependency.manifest,
                    declaration.get("parameters", {}),
                    owner.manifest,
                )
                available = self.evidence(dependency)
                evidence = [
                    next((
                        item for item in available
                        if item.get("verdict") == "passed"
                        and item.get("parameters") == configuration
                    ), None)
                    for configuration in configurations
                ]
                if any(item is None for item in evidence):
                    raise IPLibraryError(
                        f"dependency {dependency.key} configuration has no qualification evidence"
                    )
                existing = dependency_entries.get(dependency.key)
                if existing is not None:
                    if existing["parameters"] != parameters:
                        raise IPLibraryError(
                            f"dependency configuration conflict: {dependency.key}"
                        )
                    existing["dependency_of"] = sorted(set([
                        *existing["dependency_of"], required_by,
                    ]))
                    continue
                dependency_entries[dependency.key] = {
                    "kind": "dependency", "instance": "",
                    **fields(dependency),
                    "parameters": parameters,
                    "dependency_of": [required_by],
                    "evidence_digest": _digest([
                        item for item in evidence if item is not None
                    ]),
                }

        for instance in document.get("instances", []):
            capability = str(instance.get("capability", ""))
            if capability == "generated-rtl":
                name = str(instance.get("name", ""))
                try:
                    record = source_record(self.project_root, compiled_spec, name)
                except GeneratedSubmoduleError as exc:
                    raise IPLibraryError(str(exc)) from exc
                top = record["module"]
                if top in modules:
                    raise IPLibraryError(
                        f"SystemVerilog module name collision: {top} "
                        f"({modules[top]}, generated:{name})"
                    )
                modules[top] = f"generated:{name}"
                generated_entries.append({
                    "kind": "generated_rtl", "instance": name,
                    "capability": capability, "top_module": top,
                    "spec_digest": record["spec_digest"],
                    "contract_digest": record["contract_digest"],
                    "generation_digest": record["generation_digest"],
                    "ports": record["ports"], "parameters": {},
                    "files": record["files"],
                    "file_hashes": record["file_hashes"],
                })
                decisions.append({
                    "instance": name, "selected": f"generated:{top}",
                    "reason": "冻结规格限定的自有 RTL 已按源码摘要固定；仍需独立系统验收",
                    "generation_digest": record["generation_digest"],
                })
                continue
            if capability in {"program-rom", "register-ram"} and not instance.get("package"):
                name = str(instance.get("name", ""))
                module = generated_by_instance.get(name)
                expected_kind = "rom" if capability == "program-rom" else "register_ram"
                if module is None or module["kind"] != expected_kind or generated is None:
                    raise IPLibraryError(
                        f"generated memory for instance {name} is missing or changed"
                    )
                top = str(module["module"])
                if top in modules:
                    raise IPLibraryError(
                        f"SystemVerilog module name collision: {top} "
                        f"({modules[top]}, generated:{name})"
                    )
                modules[top] = f"generated:{name}"
                files = [module["rtl"]]
                if module["image"]:
                    files.append(module["image"])
                generated_entries.append({
                    "kind": "generated", "instance": name,
                    "capability": capability, "top_module": top,
                    "generation_digest": generated["generation_digest"],
                    "generator_version": generated["generator_version"],
                    "size_bytes": module["size_bytes"], "base": module["base"],
                    "files": files,
                    "file_hashes": {
                        path: generated["file_hashes"][path] for path in files
                    },
                })
                decisions.append({
                    "instance": name, "selected": f"generated:{top}",
                    "reason": "冻结规格已生成内容校验通过的版本化存储器 RTL；仍需独立验收",
                    "generation_digest": generated["generation_digest"],
                })
                continue
            candidates = self._candidates(instance, document, current)
            if not candidates:
                requested = str(instance.get("package", ""))
                version = str(instance.get("version", ""))
                capability = str(instance.get("capability", ""))
                matching = [
                    package for package in self.packages()
                    if (not requested or package.package_id == requested)
                    and (not version or package.version == version)
                    and (not capability or supports_capability(capability, package.manifest))
                ]
                hard_matches = [
                    package for package in matching
                    if _implementation_kind(package.manifest) == "hard_macro"
                ]
                if hard_matches and (requested or len(hard_matches) == len(matching)):
                    _require_rtl_implementation(hard_matches[0])
                raise IPLibraryError(
                    f"no qualified IP satisfies instance {instance.get('name')}"
                )
            package, evidence = candidates[0]
            register(package)
            add_dependencies(package, required_by=package.key)
            parameters, _configurations = _resolve_instance_parameters(
                package.manifest, instance.get("parameters", {}), document,
            )
            entry = {
                "kind": "instance",
                "instance": instance["name"],
                **fields(package),
                "parameters": parameters,
                "evidence_digest": _digest(evidence),
            }
            direct_entries.append(entry)
            decisions.append({
                "instance": instance["name"], "selected": package.key,
                "reason": "当前配置已审核并通过真实工具验证",
                "candidates": [item[0].key for item in candidates],
            })
        body = {
            "schema_version": 1,
            "spec_digest": spec_digest,
            "packages": [*dependency_entries.values(), *direct_entries],
            "generated_modules": generated_entries,
            "decisions": copy.deepcopy(decisions),
        }
        body["lock_digest"] = _digest(body)
        return IPResolution(body, tuple(decisions))

    def save_lock(self, resolution: IPResolution) -> dict[str, Any]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path.write_text(
            json.dumps(resolution.lock, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return resolution.lock

    def read_lock(self, *, optional: bool = False) -> dict[str, Any]:
        if not self.lock_path.is_file():
            if optional:
                return {}
            raise IPLibraryError("project has no ip/nebula.lock.json")
        try:
            lock = json.loads(self.lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise IPLibraryError(f"invalid IP lock: {exc}") from exc
        digest = lock.get("lock_digest")
        body = {key: value for key, value in lock.items() if key != "lock_digest"}
        if digest != _digest(body):
            raise IPLibraryError("IP lock digest does not match its content")
        return lock

    def package_for_lock(self, entry: Mapping[str, Any]) -> IPPackage:
        package = self.find(str(entry["package_id"]), str(entry["version"]))
        if package is None or package.content_digest != entry.get("content_digest"):
            raise IPLibraryError(f"locked package is unavailable: {entry.get('package_id')}")
        self.verify_package(package)
        _require_rtl_implementation(package)
        return package

    def qualification_candidates(
        self, instance: Mapping[str, Any], spec: Mapping[str, Any],
        current: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        """Return compatible reviewed packages, including missing exact evidence.

        The order is identical to lock resolution: an existing pin first,
        then first-party packages, then the highest compatible version.
        Only the configurations required by this instance are listed.
        """
        candidates: list[dict[str, Any]] = []
        for package, configurations in self._eligible_candidates(instance, spec, current):
            records = self.evidence(package)
            passed = []
            missing = []
            for configuration in configurations:
                record = next((
                    item for item in records
                    if item.get("verdict") == "passed"
                    and item.get("parameters") == configuration
                ), None)
                (passed if record is not None else missing).append(
                    record if record is not None else configuration
                )
            candidates.append({
                "package": package,
                "configurations": configurations,
                "missing_configurations": missing,
                "evidence": passed,
            })
        return candidates

    def _eligible_candidates(
        self, instance: Mapping[str, Any], spec: Mapping[str, Any],
        current: Mapping[str, Any],
    ) -> list[tuple[IPPackage, list[dict[str, Any]]]]:
        requested = str(instance.get("package", ""))
        requested_version = str(instance.get("version", ""))
        capability = str(instance.get("capability", ""))
        parameters = dict(instance.get("parameters", {}))
        locked = {
            item.get("instance"): (item.get("package_id"), item.get("version"))
            for item in current.get("packages", [])
        }
        result: list[tuple[IPPackage, list[dict[str, Any]]]] = []
        for package in self.packages():
            if package.manifest.get("deprecated"):
                continue
            if _implementation_kind(package.manifest) == "hard_macro":
                continue
            if requested and package.package_id != requested:
                continue
            if requested_version and package.version != requested_version:
                continue
            if capability and not supports_capability(capability, package.manifest):
                continue
            if spec.get("design_kind") == "generic_module" and not supports_generic_named_port(package.manifest):
                continue
            self.verify_package(package)
            if package.manifest["source"]["review"].get("status") != "approved":
                continue
            try:
                _locked, configurations = _resolve_instance_parameters(
                    package.manifest, parameters, spec,
                )
            except IPLibraryError:
                continue
            required_interfaces = spec.get("interfaces", [])
            bound_ids = instance.get("interface_ids")
            if bound_ids is not None:
                if not isinstance(bound_ids, list):
                    continue
                required_interfaces = [
                    endpoint for endpoint in required_interfaces
                    if isinstance(endpoint, dict) and endpoint.get("id") in bound_ids
                ]
                if len(required_interfaces) != len(bound_ids):
                    continue
            if not _interfaces_compatible(required_interfaces, package.manifest.get("interfaces", [])):
                continue
            result.append((package, configurations))

        def priority(candidate: tuple[IPPackage, list[dict[str, Any]]]) -> tuple[int, int, tuple[int, ...]]:
            package = candidate[0]
            pinned = locked.get(instance.get("name")) == (package.package_id, package.version)
            first_party = package.manifest["source"]["kind"] == "first_party"
            return (int(pinned), int(first_party), _version_key(package.version))

        return sorted(result, key=priority, reverse=True)

    def _candidates(
        self, instance: Mapping[str, Any], spec: Mapping[str, Any], current: Mapping[str, Any],
    ) -> list[tuple[IPPackage, list[dict[str, Any]]]]:
        return [
            (item["package"], item["evidence"])
            for item in self.qualification_candidates(instance, spec, current)
            if not item["missing_configurations"]
        ]


class _StrictFormat(dict[str, Any]):
    def __missing__(self, key: str) -> Any:
        raise KeyError(key)


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise IPLibraryError(f"cannot load IP manifest: {exc}") from exc
    if not isinstance(value, dict):
        raise IPLibraryError("IP manifest root must be a mapping")
    return value


def _validate_manifest(root: Path, manifest: dict[str, Any]) -> tuple[str, str]:
    if manifest.get("schema_version") != 1:
        raise IPLibraryError("IP manifest schema_version must be 1")
    package = manifest.get("package")
    if not isinstance(package, dict):
        raise IPLibraryError("IP manifest requires package identity")
    parts = [package.get(name) for name in ("vendor", "library", "name")]
    if any(not isinstance(item, str) or not _NAME.fullmatch(item) for item in parts):
        raise IPLibraryError("package vendor/library/name are invalid")
    version = package.get("version")
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise IPLibraryError("package version must be semantic x.y.z")
    package_id = ":".join(parts)
    source = manifest.get("source")
    if not isinstance(source, dict) or source.get("kind") not in {"first_party", "third_party"}:
        raise IPLibraryError("source.kind must be first_party or third_party")
    for field in ("origin", "license"):
        if not isinstance(source.get(field), str) or not source[field].strip():
            raise IPLibraryError(f"source.{field} is required")
    review = source.get("review")
    if not isinstance(review, dict) or review.get("status") not in {"approved", "pending", "rejected"}:
        raise IPLibraryError("source.review.status must be approved, pending or rejected")
    top = manifest.get("top_module")
    if not isinstance(top, str) or not _SV_NAME.fullmatch(top):
        raise IPLibraryError("top_module is invalid")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise IPLibraryError("IP package must declare an ordered file list")
    seen: set[str] = set()
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise IPLibraryError("each IP file requires path and type")
        relative = _safe_relative(item["path"])
        if relative in seen:
            raise IPLibraryError(f"duplicate IP file: {relative}")
        seen.add(relative)
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise IPLibraryError(f"IP file is missing or is a symlink: {relative}")
        if item.get("type") not in {
            "systemVerilogSource", "verilogSource", "systemVerilogTestbench",
            "include", "script", "data", "lef", "gds", "liberty",
            "verilogBlackbox",
        }:
            raise IPLibraryError(f"unsupported IP file type: {item.get('type')}")
    implementation = manifest.get("implementation", {"kind": "soft_rtl"})
    if not isinstance(implementation, dict):
        raise IPLibraryError("implementation must be a mapping")
    kind = implementation.get("kind", "soft_rtl")
    if kind not in {"soft_rtl", "hard_macro"}:
        raise IPLibraryError("implementation.kind must be soft_rtl or hard_macro")
    if kind == "soft_rtl":
        if set(implementation) - {"kind"}:
            raise IPLibraryError("soft RTL IP cannot declare hard-macro physical views")
    else:
        for field in ("technology", "corner"):
            if not isinstance(implementation.get(field), str) or not implementation[field].strip():
                raise IPLibraryError(f"hard macro implementation.{field} is required")
        views = implementation.get("views")
        if not isinstance(views, dict) or set(views) != set(_HARD_MACRO_VIEWS):
            raise IPLibraryError(
                "hard macro requires lef, gds, liberty and verilog_blackbox views"
            )
        file_types = {item["path"]: item["type"] for item in files}
        for view, expected_type in _HARD_MACRO_VIEWS.items():
            path = views[view]
            if not isinstance(path, str) or _safe_relative(path) not in file_types:
                raise IPLibraryError(f"hard macro {view} view must name a declared file")
            if file_types[path] != expected_type:
                raise IPLibraryError(
                    f"hard macro {view} view must have file type {expected_type}"
                )
    dependencies = manifest.get("dependencies", [])
    if not isinstance(dependencies, list):
        raise IPLibraryError("IP dependencies must be a list")
    dependency_keys: set[tuple[str, str]] = set()
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            raise IPLibraryError("each IP dependency must be a mapping")
        dependency_id = dependency.get("package_id")
        dependency_version = dependency.get("version")
        if (
            not isinstance(dependency_id, str)
            or len(dependency_id.split(":")) != 3
            or any(not _NAME.fullmatch(part) for part in dependency_id.split(":"))
            or not isinstance(dependency_version, str)
            or not _VERSION.fullmatch(dependency_version)
        ):
            raise IPLibraryError("IP dependencies require exact package_id and version")
        key = (dependency_id, dependency_version)
        if key in dependency_keys:
            raise IPLibraryError(f"duplicate IP dependency: {dependency_id}@{dependency_version}")
        dependency_keys.add(key)
        digest = dependency.get("content_digest")
        if digest is not None and (
            not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest)
        ):
            raise IPLibraryError("dependency content_digest must be a sha256 digest")
        if "parameters" in dependency and not isinstance(dependency["parameters"], dict):
            raise IPLibraryError("dependency parameters must be a mapping")
    ports = manifest.get("ports", [])
    if not isinstance(ports, list):
        raise IPLibraryError("IP ports must be a list")
    port_names: set[str] = set()
    parameter_names = {
        item.get("name") for item in manifest.get("parameters", [])
        if isinstance(item, dict)
    }
    for port in ports:
        if not isinstance(port, dict) or not isinstance(port.get("name"), str):
            raise IPLibraryError("each IP port must be a mapping with a name")
        name = port["name"]
        if not _SV_NAME.fullmatch(name) or name in port_names:
            raise IPLibraryError(f"invalid or duplicate IP port: {name}")
        port_names.add(name)
        if port.get("direction") not in {"input", "output", "inout"}:
            raise IPLibraryError(f"invalid direction for IP port {name}")
        width = port.get("width", 1)
        if not (
            type(width) is int and width > 0
            or isinstance(width, str) and width in parameter_names
        ):
            raise IPLibraryError(f"invalid width for IP port {name}")
    _validate_parameters(manifest, {})
    return package_id, version


def _validate_parameters(manifest: Mapping[str, Any], supplied: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(supplied, Mapping):
        raise IPLibraryError("IP parameters must be a mapping")
    declarations = manifest.get("parameters", [])
    if not isinstance(declarations, list):
        raise IPLibraryError("IP manifest parameters must be a list")
    known = {item.get("name"): item for item in declarations if isinstance(item, dict)}
    unknown = sorted(set(supplied) - set(known))
    if unknown:
        raise IPLibraryError(f"unknown IP parameters: {', '.join(unknown)}")
    result: dict[str, Any] = {}
    for name, declaration in known.items():
        if not isinstance(name, str) or not _SV_NAME.fullmatch(name):
            raise IPLibraryError("IP parameter name is invalid")
        if declaration.get("type") != "integer":
            raise IPLibraryError("only integer IP parameters are supported")
        value = supplied.get(name, declaration.get("default"))
        if type(value) is not int:
            raise IPLibraryError(f"IP parameter {name} must be an integer")
        minimum, maximum = declaration.get("min"), declaration.get("max")
        allowed = declaration.get("allowed")
        if type(minimum) is not int or type(maximum) is not int or not minimum <= value <= maximum:
            raise IPLibraryError(f"IP parameter {name} is outside its range")
        if allowed is not None and value not in allowed:
            raise IPLibraryError(f"IP parameter {name} is not an allowed value")
        result[name] = value
    return result


def _resolve_instance_parameters(
    manifest: Mapping[str, Any], supplied: Mapping[str, Any],
    spec: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Resolve fixed values and spec-parameter bindings for a reusable IP.

    A dynamic binding is accepted only when every value allowed by the CSIR
    has its own qualification record. The lock preserves that binding and the
    exact qualified value set instead of pretending the default covers all
    configurations.
    """
    if not isinstance(supplied, Mapping):
        raise IPLibraryError("instance parameters must be a mapping")
    declarations = {
        item.get("name"): item
        for item in manifest.get("parameters", []) if isinstance(item, dict)
    }
    spec_parameters = {
        item.get("name"): item
        for item in spec.get("parameters", []) if isinstance(item, dict)
    }
    unknown = sorted(set(supplied) - set(declarations))
    if unknown:
        raise IPLibraryError(f"unknown IP parameters: {', '.join(unknown)}")
    locked: dict[str, Any] = {}
    value_sets: dict[str, list[int]] = {}
    for name, declaration in declarations.items():
        raw = supplied.get(name, declaration.get("default"))
        if isinstance(raw, str) and raw.startswith("$parameters."):
            spec_name = raw.removeprefix("$parameters.")
            spec_declaration = spec_parameters.get(spec_name)
            if spec_declaration is None:
                raise IPLibraryError(f"unknown CSIR parameter binding: {spec_name}")
            values = spec_declaration.get("allowed")
            if not isinstance(values, list) or not values:
                values = list(dict.fromkeys([
                    spec_declaration.get("min"), spec_declaration.get("default"),
                    spec_declaration.get("max"),
                ]))
            if any(type(value) is not int for value in values):
                raise IPLibraryError(f"CSIR parameter {spec_name} has no finite integer value set")
            for value in values:
                _validate_parameters(manifest, {**{
                    key: item.get("default") for key, item in declarations.items()
                }, name: value})
            value_sets[name] = list(values)
            locked[name] = {
                "bind": spec_name,
                "qualified_values": list(values),
                "default": spec_declaration.get("default"),
            }
        else:
            normalized = _validate_parameters(manifest, {name: raw})[name]
            value_sets[name] = [normalized]
            locked[name] = normalized
    configurations = [
        dict(zip(value_sets, values))
        for values in itertools.product(*(value_sets[name] for name in value_sets))
    ]
    for configuration in configurations:
        _validate_parameters(manifest, configuration)
    return locked, configurations


def _defaults(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        item["name"]: item["default"]
        for item in manifest.get("parameters", []) if isinstance(item, dict)
    }


def supports_generic_named_port(manifest: Mapping[str, Any]) -> bool:
    """Require an explicit, complete plain-pin contract for generic reuse.

    Protocol adapters have separate generators; a partial manifest of sideband
    pins must never be interpreted as a complete module interface.
    """
    generator = manifest.get("generator", {})
    return (
        isinstance(generator, Mapping)
        and generator.get("kind") == "generic-named-port-v1"
        and manifest.get("interfaces", []) == []
        and isinstance(manifest.get("ports"), list)
        and bool(manifest["ports"])
    )


def supports_capability(capability: str, manifest: Mapping[str, Any]) -> bool:
    """Match reviewed interface profiles without changing an immutable IP package.

    A GPIO register bank qualifies as an APB GPIO only when it advertises an
    APB4 completer. Parameter, protocol and run-evidence checks still apply in
    ``IPLibrary._candidates``; this alias alone never grants qualification.
    """
    capabilities = manifest.get("capabilities", [])
    if capability in capabilities:
        return True
    if capability != "apb-gpio" or "gpio-register-bank" not in capabilities:
        return False
    return any(
        isinstance(interface, Mapping)
        and interface.get("protocol") == "APB4"
        and interface.get("role") == "completer"
        for interface in manifest.get("interfaces", [])
    )


def _interfaces_compatible(required: Any, offered: Any) -> bool:
    if not isinstance(required, list) or not isinstance(offered, list):
        return False
    for need in required:
        if not isinstance(need, dict) or need.get("protocol") not in {
            "APB4", "PicoRV32-native",
        }:
            return False
        matches = [
            item for item in offered
            if isinstance(item, dict) and item.get("protocol") == need.get("protocol")
            and item.get("role") == need.get("role")
        ]
        if not matches:
            return False
        have = matches[0]
        if have.get("data_width") != need.get("data_width"):
            return False
        have_address = have.get("address_width")
        if type(have_address) is int and have_address < need.get("address_width", 0):
            return False
        need_cap, have_cap = need.get("capabilities", {}), have.get("capabilities", {})
        if need.get("protocol") == "APB4":
            if need_cap.get("pstrb") and not have_cap.get("pstrb"):
                return False
            if need_cap.get("pprot") == "enforced" and have_cap.get("pprot") != "enforced":
                return False
        else:
            if any(
                need_cap.get(key) is True and have_cap.get(key) is not True
                for key in ("byte_strobes", "instruction_tag", "valid_ready")
            ):
                return False
    return True


def _package_digest(root: Path, manifest: Mapping[str, Any]) -> str:
    digest = hashlib.sha256()
    normalized = copy.deepcopy(dict(manifest))
    normalized.pop("content_digest", None)
    digest.update(json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    for item in manifest["files"]:
        relative = _safe_relative(item["path"])
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update((root / relative).read_bytes())
    return "sha256:" + digest.hexdigest()


def _safe_relative(value: str) -> str:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise IPLibraryError(f"unsafe IP path: {value}")
    return path.as_posix()


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _version_key(value: str) -> tuple[int, ...]:
    return tuple(int(item) for item in value.split("-", 1)[0].split("."))


def _digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()

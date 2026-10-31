"""Load and check the pinned RTL-to-GDS toolchain requirements."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Mapping

import yaml


class ToolchainRequirementsError(ValueError):
    pass


def requirements_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "configs" / "toolchains" / "rtl-to-gds.requirements.yaml"
    )


def load_rtl_to_gds_requirements(path: Path | None = None) -> dict[str, Any]:
    source = path or requirements_path()
    try:
        document = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ToolchainRequirementsError(f"cannot load {source}: {exc}") from exc
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ToolchainRequirementsError("toolchain requirements schema_version must be 1")
    if document.get("profile") != "rtl-to-gds":
        raise ToolchainRequirementsError("toolchain requirements profile must be rtl-to-gds")
    tools = document.get("tools")
    orfs = document.get("orfs")
    if not isinstance(tools, dict) or not tools or not isinstance(orfs, dict):
        raise ToolchainRequirementsError("toolchain requirements need tools and orfs mappings")
    for name, spec in tools.items():
        if not isinstance(name, str) or not isinstance(spec, dict):
            raise ToolchainRequirementsError("each tool requirement must be a mapping")
        if not isinstance(spec.get("executable"), str) or not spec["executable"]:
            raise ToolchainRequirementsError(f"tool {name} has no executable")
        version = spec.get("version")
        if not isinstance(version, dict) or version.get("kind") not in {"contains", "minimum"}:
            raise ToolchainRequirementsError(f"tool {name} has an invalid version requirement")
        if not isinstance(version.get("value"), str) or not version["value"]:
            raise ToolchainRequirementsError(f"tool {name} has no version value")
        for capability in spec.get("capabilities", []):
            if not isinstance(capability, dict) or not capability.get("id"):
                raise ToolchainRequirementsError(f"tool {name} has an invalid capability")
            provider = capability.get("provider")
            if provider is not None and (
                not isinstance(provider, dict)
                or not re.fullmatch(r"[0-9a-f]{40}", str(provider.get("revision", "")))
            ):
                raise ToolchainRequirementsError(
                    f"tool {name} capability {capability['id']} provider must use a full Git commit"
                )
    revision = orfs.get("revision")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ToolchainRequirementsError("ORFS revision must be a full Git commit")
    if orfs.get("fetch_strategy") != "partial-sparse":
        raise ToolchainRequirementsError("ORFS fetch_strategy must be partial-sparse")
    return document


def check_rtl_to_gds_toolchain(
    *, toolchain_root: Path | None = None, orfs_root: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    requirements = load_rtl_to_gds_requirements()
    env = dict(os.environ if environment is None else environment)
    layout = requirements["layout"]
    configured_root = toolchain_root or _optional_path(env.get(layout["toolchain_root_env"], ""))
    if configured_root is None:
        configured_root = _discover_toolchain_root(env)
    configured_orfs = orfs_root or _optional_path(env.get(layout["orfs_root_env"], ""))
    if configured_orfs is None and configured_root is not None:
        configured_orfs = configured_root / "OpenROAD-flow-scripts"

    tool_results: dict[str, Any] = {}
    failures: list[str] = []
    for name, spec in requirements["tools"].items():
        executable = _resolve_executable(spec, configured_root, layout, env)
        version = _run(executable, list(map(str, spec.get("version_args", [])))) if executable else ""
        version_ready = bool(executable) and _version_matches(version, spec["version"])
        capabilities: list[dict[str, Any]] = []
        for capability in spec.get("capabilities", []):
            probes = capability.get("any_probe", []) if isinstance(capability, dict) else []
            attempts = []
            for probe in probes:
                if not isinstance(probe, Mapping):
                    continue
                arguments = list(map(str, probe.get("arguments", [])))
                passed, output = _probe(
                    executable,
                    arguments,
                    contains=list(map(str, probe.get("output_contains", []))),
                    excludes=list(map(str, probe.get("output_excludes", []))),
                ) if executable else (False, "")
                attempts.append({
                    "arguments": arguments,
                    "passed": passed,
                    "output": output,
                })
            passed = any(item["passed"] for item in attempts)
            capabilities.append({
                "id": str(capability.get("id", "")), "passed": passed,
                "attempts": attempts,
            })
            if not passed:
                failures.append(f"{name}: missing capability {capability.get('id', '')}")
        if executable is None:
            failures.append(f"{name}: executable not found")
        elif not version_ready:
            requirement = spec["version"]
            failures.append(
                f"{name}: requires {requirement['kind']} {requirement['value']}, "
                f"got {version or 'unknown'}"
            )
        tool_results[name] = {
            "path": str(executable) if executable else "",
            "version": version,
            "requirement": spec["version"],
            "version_ready": version_ready,
            "capabilities": capabilities,
        }

    orfs_result: dict[str, Any] = {
        "root": str(configured_orfs) if configured_orfs else "",
        "revision": "", "expected_revision": requirements["orfs"]["revision"],
        "missing_paths": [], "ready": False,
    }
    if configured_orfs is None or not configured_orfs.is_dir():
        failures.append("ORFS: checkout not found")
    else:
        revision = _orfs_revision(configured_orfs, requirements["orfs"])
        missing_paths = [
            relative for relative in requirements["orfs"].get("required_paths", [])
            if not (configured_orfs / relative).is_file()
        ]
        revision_ready = revision == requirements["orfs"]["revision"]
        if not revision_ready:
            failures.append(
                f"ORFS: requires {requirements['orfs']['revision']}, got {revision or 'unknown'}"
            )
        for relative in missing_paths:
            failures.append(f"ORFS: missing {relative}")
        orfs_result.update({
            "revision": revision, "missing_paths": missing_paths,
            "ready": revision_ready and not missing_paths,
        })
    return {
        "schema_version": 1,
        "profile": requirements["profile"],
        "requirements_file": str(requirements_path()),
        "ready": not failures,
        "toolchain_root": str(configured_root) if configured_root else "",
        "tools": tool_results,
        "orfs": orfs_result,
        "failures": failures,
    }


def _optional_path(value: str) -> Path | None:
    return Path(value).expanduser().resolve() if value.strip() else None


def _discover_toolchain_root(environment: Mapping[str, str]) -> Path | None:
    candidates: list[Path] = [
        Path.cwd() / "build" / "rtl2gds-tools",
        Path.home() / ".cache" / "chip-nebula" / "rtl2gds-tools",
    ]
    for origin in (Path(__file__).resolve(), Path(sys.executable).resolve()):
        start = origin if origin.is_dir() else origin.parent
        candidates.extend(parent / "build" / "rtl2gds-tools" for parent in (start, *start.parents))
    appimage = environment.get("APPIMAGE", "").strip()
    if appimage:
        origin = Path(appimage).expanduser().resolve()
        candidates.extend(parent / "build" / "rtl2gds-tools" for parent in (origin.parent, *origin.parents))
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_dir():
            return resolved
    return None


def _resolve_executable(
    spec: Mapping[str, Any], root: Path | None, layout: Mapping[str, Any],
    env: Mapping[str, str],
) -> Path | None:
    configured = env.get(str(spec.get("environment", "")), "")
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser())
    if root is not None:
        candidates.extend(
            root / relative / str(spec["executable"])
            for relative in layout.get("executable_directories", [])
        )
    if spec["executable"] == "klayout" and Path("/Applications/KLayout/klayout.app/Contents/MacOS/klayout").is_file():
        candidates.append(Path("/Applications/KLayout/klayout.app/Contents/MacOS/klayout"))
    found = shutil.which(str(spec["executable"]), path=env.get("PATH"))
    if found:
        candidates.append(Path(found))
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    return None


def _run(executable: Path | None, arguments: list[str]) -> str:
    if executable is None:
        return ""
    try:
        result = subprocess.run(
            [str(executable), *arguments], capture_output=True, text=True,
            errors="replace", timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    output = "\n".join(value.strip() for value in (result.stdout, result.stderr) if value.strip())
    return output.splitlines()[0][:500] if output else ""


def _probe(
    executable: Path, arguments: list[str], *, contains: list[str], excludes: list[str],
) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [str(executable), *arguments], capture_output=True, text=True,
            errors="replace", timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, ""
    output = "\n".join((result.stdout, result.stderr)).strip()
    passed = (
        result.returncode == 0
        and all(value in output for value in contains)
        and all(value not in output for value in excludes)
    )
    return passed, output[:1000]


def _version_matches(actual: str, requirement: Mapping[str, str]) -> bool:
    expected = requirement["value"]
    if requirement["kind"] == "contains":
        return expected in actual
    actual_version = _first_version(actual)
    expected_version = _first_version(expected)
    return bool(actual_version and expected_version and actual_version >= expected_version)


def _first_version(value: str) -> tuple[int, ...]:
    match = re.search(r"(?<![0-9])([0-9]+(?:\.[0-9]+)+)", value)
    return tuple(map(int, match.group(1).split("."))) if match else ()


def _git_revision(root: Path) -> str:
    if not (root / ".git").exists():
        return ""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, errors="replace", timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _orfs_revision(root: Path, requirement: Mapping[str, Any]) -> str:
    revision = _git_revision(root)
    if revision:
        return revision
    revision_file = root / str(requirement.get("revision_file", "ORFS_REVISION"))
    try:
        value = revision_file.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return value if re.fullmatch(r"[0-9a-f]{40}", value) else ""


def _run_checked(arguments: list[str], *, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            arguments, cwd=cwd, capture_output=True, text=True,
            errors="replace", timeout=1800,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ToolchainRequirementsError(
            f"command failed: {' '.join(arguments)}: {exc}"
        ) from exc
    if result.returncode:
        output = "\n".join(
            value.strip() for value in (result.stdout, result.stderr) if value.strip()
        )
        raise ToolchainRequirementsError(
            f"command failed ({result.returncode}): {' '.join(arguments)}"
            + (f"\n{output[-3000:]}" if output else "")
        )
    return result.stdout.strip()


def _orfs_sparse_patterns(
    requirements: Mapping[str, Any], include_components: tuple[str, ...],
) -> list[str]:
    known_components = requirements.get("optional_components", {})
    unknown = sorted(set(include_components) - set(known_components))
    if unknown:
        raise ToolchainRequirementsError(
            "unknown optional components: " + ", ".join(unknown)
        )
    paths = list(requirements["orfs"].get("runtime_paths", []))
    for component in include_components:
        paths.extend(known_components[component].get("required_paths", []))
    patterns: list[str] = []
    for value in dict.fromkeys(map(str, paths)):
        normalized = value.strip("/")
        if not normalized or normalized.startswith("../") or "/../" in normalized:
            raise ToolchainRequirementsError(f"unsafe ORFS runtime path: {value}")
        is_file = Path(normalized).name == "Makefile" or bool(Path(normalized).suffix)
        patterns.append(f"/{normalized}" if is_file else f"/{normalized}/")
    return patterns


def _write_toolchain_environment(root: Path) -> Path:
    environment_file = root / "env.sh"
    quoted_root = "'" + str(root).replace("'", "'\\''") + "'"
    environment_file.write_text(
        "# Generated by chip-nebula toolchain install.\n"
        f"export CHIP_NEBULA_RTL2GDS_TOOL_ROOT={quoted_root}\n"
        f"export ORFS_ROOT={quoted_root}/OpenROAD-flow-scripts\n"
        f"export PATH={quoted_root}/bin:$PATH\n",
        encoding="utf-8",
    )
    return environment_file


def _ensure_opensta_frontend(
    root: Path, requirements: Mapping[str, Any],
) -> Path | None:
    """Expose OpenROAD's embedded OpenSTA through the declared ``opensta`` tool.

    The pinned OpenROAD binary accepts the standalone OpenSTA command-line
    contract (including ``-version``, ``-exit`` and a Tcl command file).  A
    dedicated frontend name keeps Task permissions and agent discovery
    deterministic without building a second copy of the same STA engine.
    Existing standalone OpenSTA installations are preserved.
    """
    alias = root / "bin" / "opensta"
    if alias.is_file() and os.access(alias, os.X_OK):
        return alias
    if alias.exists() and not alias.is_symlink():
        raise ToolchainRequirementsError(
            f"OpenSTA frontend exists but is not executable: {alias}"
        )
    if alias.is_symlink():
        alias.unlink()

    openroad = _resolve_executable(
        requirements["tools"]["openroad"], root, requirements["layout"], os.environ,
    )
    if openroad is None:
        return None
    alias.parent.mkdir(parents=True, exist_ok=True)
    alias.symlink_to(Path(os.path.relpath(openroad, alias.parent)))
    return alias


def _runtime_path(root: Path, relative: str) -> Path:
    """Existing runtimes may already have unpacked a pinned compressed view."""
    path = root / relative
    if not path.exists() and relative.endswith(".gds.gz"):
        unpacked = path.with_suffix("")
        if unpacked.is_file():
            return unpacked
    return path


def install_rtl_to_gds_toolchain(
    toolchain_root: Path, *, include_components: tuple[str, ...] = (),
    replace: bool = False,
) -> dict[str, Any]:
    """Install the pinned ORFS runtime with a partial, sparse Git fetch.

    Large EDA executables remain external, versioned host prerequisites.  This
    function installs the reproducible ORFS/Sky130 runtime and then reports the
    complete toolchain check so callers never mistake a partial setup for a
    ready RTL-to-GDS environment.
    """
    requirements = load_rtl_to_gds_requirements()
    root = toolchain_root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / "OpenROAD-flow-scripts"
    expected = str(requirements["orfs"]["revision"])
    patterns = _orfs_sparse_patterns(requirements, include_components)
    required = list(requirements["orfs"].get("required_paths", []))
    for component in include_components:
        required.extend(
            requirements.get("optional_components", {})[component].get("required_paths", [])
        )

    if destination.is_dir() and not replace:
        revision = _orfs_revision(destination, requirements["orfs"])
        missing = [
            relative for relative in required
            if not _runtime_path(destination, relative).is_file()
        ]
        if revision == expected and not missing:
            _ensure_opensta_frontend(root, requirements)
            environment_file = _write_toolchain_environment(root)
            report = check_rtl_to_gds_toolchain(toolchain_root=root, orfs_root=destination)
            return {
                "toolchain_root": str(root), "orfs_root": str(destination),
                "revision": revision, "strategy": "existing-runtime",
                "sparse_paths": patterns, "components": list(include_components),
                "environment_file": str(environment_file), "check": report,
            }
        raise ToolchainRequirementsError(
            f"ORFS destination already exists but does not match the pinned runtime: {destination}; "
            "pass --replace to replace it atomically"
        )
    if destination.exists() and not destination.is_dir():
        raise ToolchainRequirementsError(f"ORFS destination is not a directory: {destination}")

    staging = root / f".orfs-sparse-{uuid.uuid4().hex}"
    backup = root / f".orfs-replaced-{uuid.uuid4().hex}"
    try:
        staging.mkdir()
        _run_checked(["git", "init", "--quiet"], cwd=staging)
        _run_checked([
            "git", "remote", "add", "origin", str(requirements["orfs"]["repository"]),
        ], cwd=staging)
        _run_checked(["git", "config", "core.sparseCheckout", "true"], cwd=staging)
        _run_checked(["git", "config", "remote.origin.promisor", "true"], cwd=staging)
        _run_checked([
            "git", "config", "remote.origin.partialclonefilter", "blob:none",
        ], cwd=staging)
        sparse_file = staging / ".git" / "info" / "sparse-checkout"
        sparse_file.parent.mkdir(parents=True, exist_ok=True)
        sparse_file.write_text("\n".join(patterns) + "\n", encoding="utf-8")
        _run_checked([
            "git", "fetch", "--quiet", "--no-tags", "--depth=1",
            "--filter=blob:none", "origin", expected,
        ], cwd=staging)
        _run_checked(["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"], cwd=staging)

        actual = _git_revision(staging)
        if actual != expected:
            raise ToolchainRequirementsError(
                f"ORFS fetch produced {actual or 'unknown'}; expected {expected}"
            )
        missing = [relative for relative in required if not (staging / relative).is_file()]
        if missing:
            raise ToolchainRequirementsError(
                "sparse ORFS checkout is missing required files: " + ", ".join(missing)
            )
        (staging / str(requirements["orfs"].get("revision_file", "ORFS_REVISION"))).write_text(
            expected + "\n", encoding="utf-8",
        )
        shutil.rmtree(staging / ".git")

        if destination.exists():
            destination.rename(backup)
        try:
            staging.rename(destination)
        except Exception:
            if backup.exists() and not destination.exists():
                backup.rename(destination)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    _ensure_opensta_frontend(root, requirements)
    environment_file = _write_toolchain_environment(root)
    report = check_rtl_to_gds_toolchain(toolchain_root=root, orfs_root=destination)
    return {
        "toolchain_root": str(root), "orfs_root": str(destination),
        "revision": expected, "strategy": "partial-sparse-fetch",
        "sparse_paths": patterns, "components": list(include_components),
        "environment_file": str(environment_file), "check": report,
    }


def compact_rtl_to_gds_toolchain(
    toolchain_root: Path, *, include_components: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Replace a development ORFS checkout with a verified runtime bundle."""
    requirements = load_rtl_to_gds_requirements()
    root = toolchain_root.expanduser().resolve()
    source = root / "OpenROAD-flow-scripts"
    if not source.is_dir():
        raise ToolchainRequirementsError(f"ORFS checkout not found: {source}")
    revision = _orfs_revision(source, requirements["orfs"])
    expected = requirements["orfs"]["revision"]
    if revision != expected:
        raise ToolchainRequirementsError(
            f"refusing to compact ORFS revision {revision or 'unknown'}; expected {expected}"
        )
    known_components = requirements.get("optional_components", {})
    unknown = sorted(set(include_components) - set(known_components))
    if unknown:
        raise ToolchainRequirementsError(
            "unknown optional components: " + ", ".join(unknown)
        )

    staging = root / f".orfs-runtime-{uuid.uuid4().hex}"
    backup = root / f".orfs-development-{uuid.uuid4().hex}"
    copied: list[str] = []
    try:
        staging.mkdir(parents=True)
        runtime_paths = list(requirements["orfs"].get("runtime_paths", []))
        for component in include_components:
            runtime_paths.extend(known_components[component].get("required_paths", []))
        for relative in dict.fromkeys(map(str, runtime_paths)):
            candidate = _runtime_path(source, relative)
            if not candidate.exists() and not candidate.is_symlink():
                raise ToolchainRequirementsError(f"runtime path is missing: {relative}")
            installed_relative = candidate.relative_to(source)
            destination = staging / installed_relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if candidate.is_dir():
                shutil.copytree(candidate, destination, symlinks=True)
            else:
                shutil.copy2(candidate, destination, follow_symlinks=False)
            copied.append(str(installed_relative))
        revision_file = staging / str(requirements["orfs"].get("revision_file", "ORFS_REVISION"))
        revision_file.write_text(expected + "\n", encoding="utf-8")

        # The development link normally points into the OpenROAD source/Bazel
        # tree that will be removed. Materialize the resolved binary first.
        openroad = root / "bin" / "openroad"
        if not openroad.is_file():
            raise ToolchainRequirementsError(f"OpenROAD executable not found: {openroad}")
        resolved_openroad = openroad.resolve()
        replacement = root / "bin" / f".openroad-runtime-{uuid.uuid4().hex}"
        shutil.copy2(resolved_openroad, replacement)
        replacement.chmod(replacement.stat().st_mode | 0o111)

        source.rename(backup)
        try:
            staging.rename(source)
            replacement.replace(openroad)
        except Exception:
            if source.exists():
                shutil.rmtree(source)
            backup.rename(source)
            replacement.unlink(missing_ok=True)
            raise
        shutil.rmtree(backup)
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    _ensure_opensta_frontend(root, requirements)
    return {
        "toolchain_root": str(root),
        "orfs_root": str(source),
        "revision": revision,
        "runtime_paths": copied,
        "components": list(include_components),
    }


def report_json(report: Mapping[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)

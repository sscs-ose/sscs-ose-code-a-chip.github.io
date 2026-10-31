"""Deterministic inventory of installed implementation platforms and macros."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from chip_nebula.env.toolchain import (
    check_rtl_to_gds_toolchain,
    load_rtl_to_gds_requirements,
)

from .memory_inventory import discover_memory_macros


def installed_platform_inventory(
    *,
    toolchain_state: Mapping[str, Any] | None = None,
    requirements: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return only facts proven by the pinned local toolchain installation.

    The returned document may include an unavailable platform so the UI can
    explain what is missing.  Consumers must use :func:`constraint_inventory`
    when deciding what a frozen constraint document is allowed to select.
    """

    declared = dict(requirements or load_rtl_to_gds_requirements())
    state = dict(toolchain_state or check_rtl_to_gds_toolchain())
    orfs = state.get("orfs", {})
    orfs_root = Path(str(orfs.get("root", ""))).expanduser()
    flow_home = (
        orfs_root / "flow" if str(orfs_root) not in {"", "."} else None
    )
    tool_results = state.get("tools", {})
    platforms: list[dict[str, Any]] = []
    memory_macros: list[dict[str, Any]] = []

    for platform_id, raw in sorted(declared.get("platforms", {}).items()):
        spec = raw if isinstance(raw, Mapping) else {}
        missing_paths = [
            str(relative)
            for relative in spec.get("required_paths", [])
            if not (orfs_root / str(relative)).is_file()
        ]
        missing_tools = [
            str(name)
            for name in spec.get("required_tools", [])
            if not _tool_ready(tool_results.get(str(name), {}))
        ]
        ready = bool(orfs.get("ready")) and not missing_paths and not missing_tools
        diagnostics = [
            *[f"missing platform file: {path}" for path in missing_paths],
            *[f"tool is unavailable or incompatible: {name}" for name in missing_tools],
        ]
        platform = {
            "id": str(platform_id),
            "ready": ready,
            "corners": [str(item) for item in spec.get("corners", [])],
            "flow_home": (
                str(flow_home.resolve())
                if flow_home is not None and flow_home.is_dir() else ""
            ),
            "diagnostics": diagnostics,
            "orfs_revision": str(orfs.get("revision", "")),
        }
        platforms.append(platform)
        if flow_home is not None and flow_home.is_dir():
            memory_macros.extend({
                **item, "platform": str(platform_id),
            } for item in discover_memory_macros(
                flow_home, platform=str(platform_id), requirements=declared,
            ))

    return {
        "schema_version": 1,
        "profile": str(declared.get("profile", "rtl-to-gds")),
        "toolchain_ready": bool(state.get("ready")),
        "tools": tool_results,
        "orfs": orfs,
        "platforms": platforms,
        "memory_macros": _unique_macros(memory_macros),
        "diagnostics": [str(item) for item in state.get("failures", [])],
    }


def constraint_inventory(inventory: Mapping[str, Any]) -> dict[str, Any]:
    """Translate installed facts into constraint-validator arguments."""

    platforms = [
        item for item in inventory.get("platforms", [])
        if isinstance(item, Mapping) and item.get("id") and item.get("ready")
    ]
    platform_ids = {str(item["id"]) for item in platforms}
    macros = [
        item for item in inventory.get("memory_macros", [])
        if isinstance(item, Mapping)
        and item.get("name")
        and item.get("pnr_ready")
        and str(item.get("platform", "")) in platform_ids
    ]
    return {
        "available_platforms": platform_ids,
        "available_corners": {
            str(item["id"]): {
                str(corner) for corner in item.get("corners", []) if corner
            }
            for item in platforms
        },
        "available_memory_macros": {str(item["name"]) for item in macros},
        "available_memory_macro_views": {
            str(item["name"]): {
                str(name): str(path)
                for name, path in item.get("views", {}).items()
            }
            for item in macros
        },
        "available_platform_details": {
            str(item["id"]): dict(item) for item in platforms
        },
    }


def _tool_ready(document: Any) -> bool:
    if not isinstance(document, Mapping) or not document.get("version_ready"):
        return False
    return all(
        isinstance(item, Mapping) and item.get("passed")
        for item in document.get("capabilities", [])
    )


def _unique_macros(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for item in items:
        key = (str(item.get("platform", "")), str(item.get("name", "")))
        unique[key] = item
    return [unique[key] for key in sorted(unique)]

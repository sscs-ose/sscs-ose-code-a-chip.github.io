"""Read installed memory views without copying or repairing PDK assets."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from chip_nebula.env.toolchain import load_rtl_to_gds_requirements, requirements_path


PNR_VIEWS = frozenset({"behavioral", "liberty", "lef", "gds"})


def _existing_file(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def _record(name: str, views: dict[str, str], **metadata: Any) -> dict[str, Any]:
    return {
        "name": name, "views": views,
        "pnr_ready": PNR_VIEWS.issubset(views),
        "signoff_ready": "lvs_spice" in views,
        "complete": "lvs_spice" in views,
        **metadata,
    }


def discover_memory_macros(
    flow_home: Path, *, platform: str = "sky130hd",
    requirements: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Discover complete, coherent bundles from installed and declared sources.

    Legacy installed bundles win by name. The bundled demo model is only paired
    with its explicitly declared physical views and matching Liberty/LEF hashes,
    never used to complete an unrelated macro having the same name.
    """
    if not flow_home.is_dir():
        return []
    macros: dict[str, dict[str, Any]] = {}
    macro_root = flow_home / "platforms" / "sky130ram"
    if platform.startswith("sky130") and macro_root.is_dir():
        for directory in sorted(item for item in macro_root.iterdir() if item.is_dir()):
            views: dict[str, str] = {}
            for name, suffixes in (
                ("behavioral", (".v", ".sv")), ("liberty", (".lib",)),
                ("lef", (".lef",)), ("gds", (".gds", ".gds.gz")),
                ("lvs_spice", (".lvs.sp",)), ("spice", (".sp",)),
            ):
                candidates = [directory / f"{directory.name}{suffix}" for suffix in suffixes]
                candidates.extend(path for suffix in suffixes for path in sorted(directory.glob(f"*{suffix}")))
                path = next((path for path in candidates if _existing_file(path)), None)
                if path is not None:
                    views[name] = str(path.resolve())
            if PNR_VIEWS.issubset(views):
                macros[directory.name] = _record(directory.name, views, source="installed-platform-bundle")

    requirements = requirements if requirements is not None else load_rtl_to_gds_requirements()
    orfs_root = flow_home.parent
    for component in requirements.get("optional_components", {}).values():
        declaration = component.get("memory_macro", {})
        if not declaration or declaration.get("platform") != platform:
            continue
        name = str(declaration.get("name", ""))
        if not name or name in macros:
            continue
        views = {}
        for view, relatives in declaration.get("views", {}).items():
            candidates = [orfs_root / relative for relative in relatives]
            path = next((path for path in candidates if _existing_file(path)), None)
            if path is not None:
                views[view] = str(path.resolve())
        model = requirements_path().parent / str(declaration.get("behavioral_model", ""))
        if _existing_file(model):
            views["behavioral"] = str(model.resolve())
        if not PNR_VIEWS.issubset(views):
            continue
        if any(
            hashlib.sha256(Path(views[view]).read_bytes()).hexdigest() != expected
            for view, expected in declaration.get("view_sha256", {}).items()
        ):
            continue
        macros[name] = _record(
            name, views, source=declaration.get("source", "declared-toolchain-bundle"),
            geometry=dict(declaration.get("geometry", {})),
            behavior=dict(declaration.get("behavior", {})),
            behavioral_source="chip-nebula-demo-model",
            limitations=["Functional demo model; no foundry timing or LVS qualification."]
            if "lvs_spice" not in views else [],
        )
    return [macros[name] for name in sorted(macros)]

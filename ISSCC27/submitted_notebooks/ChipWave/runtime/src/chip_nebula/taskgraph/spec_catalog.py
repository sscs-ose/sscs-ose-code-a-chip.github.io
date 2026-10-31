"""Read-only IP facts supplied to specification Agents.

Bundled source review is not qualification evidence.  The catalog snapshot
exposes that distinction and binds a specification plan to exact package
contents without importing packages into the user's project.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import chip_nebula
from chip_nebula.taskgraph.ip_library import (
    IPLibrary, IPLibraryError, IPPackage, _load_manifest, _package_digest,
    _validate_manifest,
)


def specification_catalog_context(project_root: Path) -> dict[str, Any]:
    """Return verified built-in and project IP contracts, with a stable digest."""
    library = IPLibrary(project_root)
    entries: list[dict[str, Any]] = []
    builtins = Path(chip_nebula.__file__).parent / "configs" / "ip"
    for path in sorted(builtins.rglob("chip-nebula-ip.yaml")):
        manifest = _load_manifest(path)
        package_id, version = _validate_manifest(path.parent, manifest)
        package = IPPackage(
            package_id, version, _package_digest(path.parent, manifest),
            path.parent, manifest,
        )
        entries.append(_entry(package, [], availability="bundled"))
    for package in library.packages():
        evidence = library.evidence(package)
        try:
            library.verify_package(package)
        except IPLibraryError as exc:
            entries.append({
                "package_id": package.package_id,
                "version": package.version,
                "content_digest": package.content_digest,
                "availability": "imported",
                "integrity": "invalid",
                "reason": str(exc),
            })
        else:
            entries.append(_entry(package, evidence, availability="imported"))
    entries.sort(key=lambda item: (
        item["package_id"], item["version"], item["availability"],
        item["content_digest"],
    ))
    body = {"schema_version": 1, "packages": entries}
    body["digest"] = "sha256:" + hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        .encode("utf-8")
    ).hexdigest()
    return body


def _entry(
    package: IPPackage, evidence: list[dict[str, Any]], *, availability: str,
) -> dict[str, Any]:
    manifest = package.manifest
    approved = manifest["source"]["review"]["status"] == "approved"
    passed = [
        record for record in evidence
        if record.get("verdict") == "passed"
        and record.get("content_digest") == package.content_digest
    ]
    return {
        "package_id": package.package_id,
        "version": package.version,
        "content_digest": package.content_digest,
        "availability": availability,
        "integrity": "valid",
        "source_kind": manifest["source"]["kind"],
        "review_status": manifest["source"]["review"]["status"],
        "qualification": "qualified" if approved and passed else "pending",
        "qualified_configurations": [item.get("parameters", {}) for item in passed],
        "top_module": manifest["top_module"],
        "capabilities": manifest.get("capabilities", []),
        "interfaces": manifest.get("interfaces", []),
        "ports": manifest.get("ports", []),
        "parameters": manifest.get("parameters", []),
        "dependencies": manifest.get("dependencies", []),
    }

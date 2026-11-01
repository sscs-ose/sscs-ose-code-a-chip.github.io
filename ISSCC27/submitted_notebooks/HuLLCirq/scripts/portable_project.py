#!/usr/bin/env python3
"""Transfer bounded raw evidence without executing imported configuration."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.domain import DomainError
from hullcirq.store import strict_loads
from hullcirq.workspace import WorkspaceRegistry
from hullcirq.portable_projects import export_project, restore_project, validate_package, inspect_project, MAX_PACKAGE_BYTES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("export", "verify", "restore", "inspect"))
    parser.add_argument("--workspace", type=Path, default=ROOT / ".work" / "workspace")
    parser.add_argument("--project-id")
    parser.add_argument("--package", type=Path)
    parser.add_argument("--name")
    args = parser.parse_args()
    try:
        if args.operation in {"verify", "restore"}:
            if args.package is None or args.package.stat().st_size > MAX_PACKAGE_BYTES:
                parser.error("Select a package of at most 120 MiB with --package.")
            bundle = strict_loads(args.package.read_text(encoding="utf-8"))
            if args.operation == "verify":
                entries = validate_package(bundle)
                print(json.dumps({"status": "Passed", "files": len(entries), "bytes": sum(len(raw) for _, raw in entries),
                                  "unavailable": len(bundle["unavailable"]), "executed": False}))
                return 0
            result = restore_project(WorkspaceRegistry(args.workspace), bundle, args.name)
            print(json.dumps({"project_id": result["project_id"], "system_id": result["system_id"], "read_only": True,
                              "host_execution_ready": False, "executed": False}))
            return 0
        if not args.project_id:
            parser.error("Select --project-id.")
        registry = WorkspaceRegistry(args.workspace)
        if args.operation == "inspect":
            print(json.dumps(inspect_project(registry, args.project_id), ensure_ascii=False))
            return 0
        if args.package is None:
            parser.error("Select a new output --package file.")
        value = export_project(registry, args.project_id, ROOT)
        with args.package.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            stream.write("\n")
        print(json.dumps({"status": "Passed", "checksum": value["checksum"], "unavailable": len(value["unavailable"]), "executed": False}))
        return 0
    except (DomainError, OSError, ValueError) as error:
        print(f"Evidence transfer stopped: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

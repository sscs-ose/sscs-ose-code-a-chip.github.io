#!/usr/bin/env python3
"""Create, verify or restore a local HuLLCirq source/data recovery baseline.

This utility does not run circuit tools, a model, or workflow adoption. Restore
always writes a new directory; it cannot replace an active project or checkout.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORIES = ("src", "tests", "scripts", "configs", "docs", "assets", "examples")
SOURCE_ROOT_FILES = (".gitignore", "AGENTS.md", "HuLLCirq.ipynb", "LICENSE", "README.md")
EXCLUDED_DIRECTORIES = {
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules",
    ".venv", "venv", ".git", "models", "model_weights", "checkpoints", "cache",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".gguf", ".safetensors", ".pt", ".pth"}
SECRET_FIELDS = {
    "apikey", "accesstoken", "refreshtoken", "password", "secret", "clientsecret",
    "bearertoken", "privatekey",
}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def contained_path(root: Path, relative: str) -> Path:
    """Reject absolute, parent, Windows drive and alternate-stream paths."""
    parsed = PurePosixPath(relative)
    if not relative or "\\" in relative or ":" in relative or parsed.is_absolute():
        raise ValueError("Invalid relative archive path")
    if any(part in {"", ".", ".."} for part in parsed.parts):
        raise ValueError("Invalid relative archive path")
    destination = root.joinpath(*parsed.parts).resolve()
    destination.relative_to(root.resolve())
    return destination


def source_files(root: Path) -> list[Path]:
    paths = [root / name for name in SOURCE_ROOT_FILES if (root / name).is_file()]
    for name in SOURCE_DIRECTORIES:
        folder = root / name
        if not folder.is_dir():
            continue
        paths.extend(
            path for path in folder.rglob("*")
            if path.is_file()
            and not any(part in EXCLUDED_DIRECTORIES for part in path.relative_to(folder).parts)
            and path.suffix.lower() not in EXCLUDED_SUFFIXES
        )
    return sorted(paths)


def scan_literal_credentials(path: Path) -> None:
    """Abort instead of copying a recognized literal credential into a ZIP."""
    if path.suffix.lower() != ".json":
        return
    document = json.loads(path.read_text(encoding="utf-8-sig"))

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = re.sub(r"[^a-z]", "", str(key).lower())
                http_authorization = (
                    normalized == "authorization"
                    and isinstance(child, str)
                    and child.lstrip().lower().startswith(("bearer ", "basic "))
                )
                if (normalized in SECRET_FIELDS and child not in (None, "", False)) or http_authorization:
                    raise ValueError(
                        f"Literal credential field detected in {path.name}; "
                        "use an environment reference before making a portable baseline."
                    )
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(document)


def local_input(root: Path, argument: str) -> Path:
    path = Path(argument)
    result = (root / path).resolve() if not path.is_absolute() else path.resolve()
    result.relative_to(root.resolve())
    if result.is_symlink():
        raise ValueError("Linked inputs are not supported")
    return result


def write_json(path: Path, document: object) -> None:
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def create(args: argparse.Namespace) -> dict:
    root = ROOT
    output = local_input(root, args.output)
    if output == root:
        raise ValueError("The project root cannot be the output directory")
    if output.exists():
        raise ValueError("Output already exists; choose a new baseline directory")
    if any(output == root / directory or (root / directory) in output.parents for directory in SOURCE_DIRECTORIES):
        raise ValueError("Store the baseline outside source directories")
    inputs: dict[str, tuple[str, Path]] = {}
    for path in source_files(root):
        inputs[path.relative_to(root).as_posix()] = ("source", path)
    stores = args.store or [".work/projects/npu"]
    for argument in stores:
        folder = local_input(root, argument)
        if not folder.is_dir():
            raise ValueError("Requested project store does not exist")
        if output.is_relative_to(folder):
            raise ValueError("A baseline cannot be written inside a live project store")
        for path in sorted(folder.rglob("*.json")):
            inputs[path.relative_to(root).as_posix()] = ("retained_live_project", path)
    runtimes = args.runtime_config
    if runtimes is None:
        runtimes = [".work/m2/compiler.json", ".work/m2b/synthesizer.json"]
        runtimes += [p.relative_to(root).as_posix() for p in sorted((root / ".work/m2m/v6").glob("*_runtime.json"))]
    for argument in runtimes:
        path = local_input(root, argument)
        if not path.is_file() or path.suffix.lower() != ".json":
            raise ValueError("Requested runtime configuration does not exist")
        inputs[path.relative_to(root).as_posix()] = ("runtime_configuration", path)
    for category, path in inputs.values():
        if path.is_symlink():
            raise ValueError("Linked inputs are not supported")
        if category != "source" or "configs" in path.relative_to(root).parts:
            scan_literal_credentials(path)
    output.mkdir(parents=True, exist_ok=False)
    entries = []
    archive = output / "recoverable_baseline.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as zipped:
        for relative, (category, path) in sorted(inputs.items()):
            before_hash = file_hash(path)
            size = path.stat().st_size
            zipped.write(path, relative)
            if file_hash(path) != before_hash:
                raise ValueError("An input changed during capture; discard this incomplete baseline")
            entries.append({"path": relative, "category": category, "bytes": size, "sha256": before_hash})
    manifest = {
        "schema_version": 1,
        "baseline_id": output.name,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Source, chosen project JSON stores and runtime settings; existing results retained in place.",
        "archive": {"path": archive.name, "bytes": archive.stat().st_size, "sha256": file_hash(archive)},
        "files": entries,
        "literal_credential_check": "Passed",
        "eda_executed": False,
        "llm_calls": 0,
        "end_to_end_validation_executed": False,
    }
    write_json(output / "manifest.json", manifest)
    results = []
    if args.inventory_results:
        for path in sorted((root / "results").rglob("*")):
            if path.is_file() and not path.is_relative_to(output):
                results.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": file_hash(path)})
        write_json(output / "retained_results_inventory.json", {
            "schema_version": 1, "baseline_id": output.name,
            "scope": "Existing result bytes retained in place; no copy of the result archive payload.",
            "files": results,
        })
    result = verify_baseline(output)
    result["retained_result_files_inventoried"] = len(results)
    return result


def verify_baseline(baseline: Path, *, check_retained_results: bool = False) -> dict:
    manifest = json.loads((baseline / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported baseline schema")
    archive_info = manifest["archive"]
    archive = contained_path(baseline, archive_info["path"])
    if archive.stat().st_size != archive_info["bytes"] or file_hash(archive) != archive_info["sha256"]:
        raise ValueError("Recovery ZIP hash/size mismatch")
    expected = manifest["files"]
    names = [entry["path"] for entry in expected]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate manifest paths")
    with zipfile.ZipFile(archive) as zipped:
        infos = zipped.infolist()
        if len(infos) != len(expected) or sorted(info.filename for info in infos) != sorted(names):
            raise ValueError("ZIP contents differ from manifest")
        for info in infos:
            contained_path(baseline, info.filename)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("Linked archive members are not supported")
        for entry in expected:
            digest = hashlib.sha256()
            size = 0
            with zipped.open(entry["path"]) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    size += len(chunk)
                    digest.update(chunk)
            if size != entry["bytes"] or digest.hexdigest() != entry["sha256"]:
                raise ValueError("Archive member hash/size mismatch")
    result_count = 0
    if check_retained_results:
        inventory = json.loads((baseline / "retained_results_inventory.json").read_text(encoding="utf-8"))
        for entry in inventory["files"]:
            path = contained_path(ROOT, entry["path"])
            if path.stat().st_size != entry["bytes"] or file_hash(path) != entry["sha256"]:
                raise ValueError("A retained result differs from the baseline inventory")
            result_count += 1
    return {
        "status": "Passed", "baseline_id": manifest["baseline_id"],
        "archive_files_verified": len(expected), "archive_sha256": archive_info["sha256"],
        "retained_result_files_verified": result_count,
        "eda_executed": False, "llm_calls": 0, "end_to_end_validation_executed": False,
    }


def restore(args: argparse.Namespace) -> dict:
    baseline = Path(args.baseline).resolve()
    result = verify_baseline(baseline)
    destination = Path(args.destination).resolve()
    if destination.exists():
        raise ValueError("Restore destination already exists; use a new empty path")
    manifest = json.loads((baseline / "manifest.json").read_text(encoding="utf-8"))
    destination.mkdir(parents=True, exist_ok=False)
    archive = contained_path(baseline, manifest["archive"]["path"])
    with zipfile.ZipFile(archive) as zipped:
        for entry in manifest["files"]:
            path = contained_path(destination, entry["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            with zipped.open(entry["path"]) as source, path.open("xb") as target:
                shutil.copyfileobj(source, target)
            if file_hash(path) != entry["sha256"]:
                raise ValueError("Restored file hash mismatch")
    result["restored_to"] = str(destination)
    result["restored_files_verified"] = len(manifest["files"])
    result["scope"] = "New-directory recovery only; retained result artifacts are not copied."
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    capture = actions.add_parser("create", help="Create a new local baseline without overwriting files")
    capture.add_argument("--output", required=True)
    capture.add_argument("--store", action="append", help="Project JSON store under HuLLCirq (repeatable)")
    capture.add_argument("--runtime-config", action="append", help="Runtime JSON under HuLLCirq (repeatable)")
    capture.add_argument("--inventory-results", action="store_true")
    verify = actions.add_parser("verify", help="Read back and hash an existing recovery ZIP")
    verify.add_argument("--baseline", required=True)
    verify.add_argument("--check-retained-results", action="store_true")
    recover = actions.add_parser("restore", help="Restore source/data into a new directory only")
    recover.add_argument("--baseline", required=True)
    recover.add_argument("--destination", required=True)
    args = parser.parse_args()
    try:
        if args.action == "create":
            report = create(args)
        elif args.action == "restore":
            report = restore(args)
        else:
            report = verify_baseline(Path(args.baseline).resolve(), check_retained_results=args.check_retained_results)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        print(json.dumps({"status": "Failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

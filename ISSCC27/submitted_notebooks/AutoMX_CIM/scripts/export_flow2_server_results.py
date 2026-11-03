#!/usr/bin/env python3
"""Mirror one Flow-2 sampler run into server_results/{build,results,physical}.

Source artifacts remain in their normal locations. The export is a compact,
hash-inventoried copy to download from the Linux server.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_flow2_precharge_leaf_layout as precharge  # noqa: E402

PILOT = Path("results/sky130/flow2_remaining_measurements/measured_cap_sampler_pilot")
EXPORT = Path("server_results")


def _sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sources(tag: str, include_measured_cap: bool) -> list[Path]:
    if not precharge.TAG_RE.fullmatch(tag):
        raise ValueError("invalid Flow-2 run tag")
    paths = [Path("build/flow2_periphery_leaf") / tag,
             Path("results/sky130/flow2_periphery_leaf") / tag,
             Path("physical/sky130/wrapper_prototype/leaf_cells") / tag]
    if include_measured_cap:
        paths.append(PILOT)
    return paths


def export(root: str | Path, *, tag: str,
           include_measured_cap: bool = True) -> dict:
    root = Path(root).resolve()
    destination_root = root / EXPORT
    if destination_root.is_symlink() or not destination_root.resolve().is_relative_to(root):
        raise ValueError("server_results must stay inside the repository")
    manifest_path = destination_root / f"flow2_sample_fet_{tag}_export.json"
    sources = _sources(tag, include_measured_cap)
    records = []
    missing = []
    for relative in sources:
        source_root = root / relative
        if source_root.is_symlink() or not source_root.resolve().is_relative_to(root):
            raise ValueError(f"refusing to export symlinked artifact folder: {source_root}")
        if not source_root.is_dir():
            missing.append(relative.as_posix())
            continue
        for source in sorted(source_root.rglob("*")):
            if source.is_symlink():
                raise ValueError(f"refusing to export symlink: {source}")
            if not source.is_file():
                continue
            resolved = source.resolve()
            if not resolved.is_relative_to(source_root.resolve()):
                raise ValueError(f"source escapes selected artifact folder: {source}")
            relative_file = source.relative_to(root)
            target = destination_root / relative_file
            if target.is_symlink() or not target.resolve().is_relative_to(destination_root.resolve()):
                raise ValueError(f"export target escapes server_results: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            source_hash = _sha(source)
            if not target.is_file() or _sha(target) != source_hash:
                shutil.copy2(source, target)
            if _sha(target) != source_hash:
                raise OSError(f"export copy changed: {target}")
            records.append({"path": relative_file.as_posix(),
                            "sha256": source_hash, "bytes": source.stat().st_size})
    report = {
        "format": "automx-cim-flow2-server-results-export-v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "EXPORTED" if records else "NOTHING_TO_EXPORT",
        "tag": tag,
        "source_roots": [path.as_posix() for path in sources],
        "missing_source_roots": missing,
        "file_count": len(records),
        "total_bytes": sum(item["bytes"] for item in records),
        "files": records,
        "download_root": EXPORT.as_posix(),
        "scope": "copied artifacts only; physical checks retain their original receipt statuses",
    }
    destination_root.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def verify(root: str | Path, *, tag: str) -> dict:
    """Verify a downloaded server_results folder without requiring source data."""
    root = Path(root).resolve()
    _sources(tag, True)  # validate the tag before constructing any path
    base = root / EXPORT
    manifest = base / f"flow2_sample_fet_{tag}_export.json"
    report = json.loads(manifest.read_text(encoding="utf-8"))
    if (report.get("format") != "automx-cim-flow2-server-results-export-v1" or
            report.get("tag") != tag or not isinstance(report.get("files"), list)):
        raise ValueError("server_results export manifest differs")
    allowed = _sources(tag, True)
    problems = []
    seen = set()
    for entry in report["files"]:
        rel = Path(entry.get("path", ""))
        if (rel.is_absolute() or rel in seen or
                not any(rel.is_relative_to(prefix) for prefix in allowed)):
            problems.append(f"unexpected export path: {rel}")
            continue
        seen.add(rel)
        target = base / rel
        if target.is_symlink() or not target.resolve().is_relative_to(base.resolve()):
            problems.append(f"export path escapes folder: {rel}")
        elif (not target.is_file() or target.stat().st_size != entry.get("bytes") or
              _sha(target) != entry.get("sha256")):
            problems.append(f"missing or changed export: {rel}")
    if len(seen) != report.get("file_count"):
        problems.append("manifest file count differs")
    return {"format": "automx-cim-flow2-server-results-verify-v1",
            "status": "PASS" if not problems else "FAIL",
            "tag": tag, "file_count": len(seen), "problems": problems}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--exclude-measured-cap", action="store_true")
    parser.add_argument("--verify", action="store_true",
                        help="check the downloaded export without original source folders")
    args = parser.parse_args()
    result = (verify(args.root, tag=args.tag) if args.verify else
              export(args.root, tag=args.tag,
                     include_measured_cap=not args.exclude_measured_cap))
    print(json.dumps({key: value for key, value in result.items() if key != "files"},
                     indent=2))
    if result["status"] == "FAIL":
        raise SystemExit(1)

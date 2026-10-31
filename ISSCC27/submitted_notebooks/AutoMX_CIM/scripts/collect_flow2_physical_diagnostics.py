#!/usr/bin/env python3
"""Archive an existing physical campaign's logs/geometry without running EDA.

The portable ZIP keeps build/, results/ and physical/ paths. In particular it
contains the acquisition layout.log and .mag, which cannot be replaced by
fanout files. Existing measurements and summary/history files are read only.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import re
import sys
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_flow2_acquisition_layout import CELL, drc_details
from scripts.run_flow2_remaining_measurements import _save, _sha

CAMPAIGNS = Path("results/sky130/flow2_physical_next")


def _relative(value: str) -> Path:
    # Receipt paths are repository-relative POSIX paths, on both host systems.
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or not path.parts or ".." in path.parts or ":" in value:
        raise ValueError(f"unsafe artifact path: {value}")
    return Path(*path.parts)


def collect(root: Path, *, tag: str) -> dict:
    root = root.resolve()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", tag):
        raise ValueError("safe campaign tag required")
    campaign = root / CAMPAIGNS / tag
    summary = campaign / "summary.json"
    saved = json.loads(summary.read_text(encoding="utf-8")) if summary.is_file() else {}
    if saved and saved.get("tag") != tag:
        raise ValueError("campaign summary tag differs")
    acq_tag, fanout_tag = tag + "_acq", tag + "_fanout"
    acq = saved.get("branches", {}).get("acquisition", {})
    for name, expected in (("acquisition", acq_tag), ("core_bound_fanout", fanout_tag)):
        observed = saved.get("branches", {}).get(name, {}).get("tag")
        if observed is not None and observed != expected:
            raise ValueError(f"unexpected {name} tag: {observed}")
    roots = [CAMPAIGNS / tag / name for name in ("summary.json", "history.log")]
    roots += [Path(base) / child for child, bases in (
        (acq_tag, ("build/flow2_periphery_leaf", "results/sky130/flow2_periphery_leaf",
                   "physical/sky130/wrapper_prototype/leaf_cells")),
        (fanout_tag, ("build/flow2_core_bound_fanout", "results/sky130/flow2_core_bound_fanout",
                      "physical/sky130/core_bound", "openlane/automx_cim_core_bound_demo/runs")))
        for base in bases]
    skipped = []
    # Preserve the actual imported child geometry as well as the assembled MAG.
    for item in acq.get("source_gds", {}).values():
        try:
            roots.append(_relative(item["path"]))
        except (KeyError, TypeError, ValueError):
            skipped.append(str(item))
    paths, missing = {}, []
    for relative in roots:
        source = root / relative
        if source.is_symlink() or not source.resolve().is_relative_to(root):
            skipped.append(relative.as_posix())
            continue
        if not source.exists():
            missing.append(relative.as_posix())
            continue
        files = sorted(source.rglob("*")) if source.is_dir() else [source]
        for path in files:
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                skipped.append(path.relative_to(root).as_posix())
            elif path.is_file():
                paths[path.relative_to(root).as_posix()] = path
    log_relative = Path("results/sky130/flow2_periphery_leaf") / acq_tag / "layout.log"
    mag_relative = Path("build/flow2_periphery_leaf") / acq_tag / "layout" / f"{CELL}.mag"
    required = {}
    for key, relative in (("layout_log", log_relative), ("layout_mag", mag_relative)):
        path = paths.get(relative.as_posix())
        required[key] = {"path": relative.as_posix(), "present": path is not None,
                         "sha256": _sha(path) if path else None}
    expected_hash = acq.get("layout", {}).get("log", {}).get("sha256")
    if expected_hash:
        required["layout_log"]["matches_campaign_receipt"] = (
            required["layout_log"]["sha256"] == expected_hash)
    log = paths.get(log_relative.as_posix())
    details = drc_details(log.read_text(encoding="utf-8", errors="replace")) if log else None
    complete = all(v["present"] for v in required.values())
    complete = complete and required["layout_log"].get("matches_campaign_receipt", True)
    report = {"format": "automx-cim-flow2-physical-diagnostics-v1", "tag": tag,
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "status": "EXPORTED" if complete else "EXPORTED_MISSING_OR_CHANGED_ACQUISITION_DIAGNOSTICS",
              "required_acquisition_diagnostics": required,
              "acquisition_drc": details, "missing_source_roots": missing,
              "skipped_unsafe_paths": skipped,
              "files": [{"path": rel, "sha256": _sha(path), "bytes": path.stat().st_size}
                        for rel, path in sorted(paths.items())],
              "scope": "artifact collection only; no EDA rerun and no change to physical check statuses"}
    destination = root / "server_results" / CAMPAIGNS / tag
    if destination.is_symlink() or not destination.resolve().is_relative_to(root):
        raise ValueError("diagnostic output must remain within the checkout")
    destination.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    archive = destination / f"diagnostics_{stamp}.zip"
    with ZipFile(archive, "x", compression=ZIP_DEFLATED) as output:
        for relative, path in sorted(paths.items()):
            output.write(path, relative)
        output.writestr("diagnostic_index.json", json.dumps(report, indent=2) + "\n")
    report["archive"] = {"path": archive.relative_to(root).as_posix(),
                         "sha256": _sha(archive), "bytes": archive.stat().st_size}
    _save(archive.with_suffix(".json"), report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--tag", default="physical_next_20261018_01")
    args = parser.parse_args()
    result = collect(args.root, tag=args.tag)
    print(json.dumps({key: value for key, value in result.items() if key != "files"}, indent=2))
    print(f"Archived {len(result['files'])} files; no EDA tools executed.")
    if result["status"] != "EXPORTED":
        raise SystemExit(1)

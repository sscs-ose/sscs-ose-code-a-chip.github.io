#!/usr/bin/env python3
"""Report all Magic DRC errors in an existing precharge leaf .mag build.

Read-only with respect to the layout. The output is a diagnostic log, not a
new DRC receipt or a replacement for the original layout run.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.physical import stage5  # noqa: E402
from scripts import run_flow2_precharge_leaf_layout as leaf  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402


def run(root: str | Path, *, pdk_root: str | Path, tag: str,
        timeout_s: int = 900) -> dict:
    root = Path(root).resolve()
    if not leaf.TAG_RE.fullmatch(tag) or timeout_s <= 0:
        raise ValueError("invalid tag or timeout")
    build = (root / "build/flow2_periphery_leaf" / tag).resolve()
    if not build.is_relative_to(root):
        raise ValueError("build directory escapes project root")
    mag = build / f"{leaf.CELL}.mag"
    if not mag.is_file():
        raise FileNotFoundError(f"existing Magic layout is required: {mag}")
    pdk = Path(pdk_root).expanduser().resolve()
    tech = pdk / "libs.tech/magic/sky130A.tech"
    if not tech.is_file():
        raise FileNotFoundError(f"Magic technology is required: {tech}")
    magic = stage5._find_tool("magic")
    if not magic:
        raise FileNotFoundError("magic is not on PATH")
    folder = root / leaf.OUTPUT / tag
    saved_path = folder / "drc_detail.json"
    if saved_path.is_file():
        saved = json.loads(saved_path.read_text(encoding="utf-8"))
        log = root / saved.get("log", "")
        if (saved.get("source_mag_sha256") != campaign._sha(mag) or
                saved.get("magic_technology_sha256") != campaign._sha(tech) or
                not log.is_file() or campaign._sha(log) != saved.get("log_sha256")):
            raise FileExistsError(f"existing DRC diagnostic differs: {saved_path}")
        return saved

    # Magic's `drc listall why` only returns errors intersecting the current
    # cursor box. The generating recipe left the box around the B label, which
    # explains why it printed 'No errors found' after a nonzero total count.
    tcl = ("crashbackups stop\n"
           f"load {leaf.CELL} -quiet\n"
           "select top cell\n"
           "box -10um -10um 10um 10um\n"
           "drc on\ndrc check\ndrc catchup\n"
           "puts \"AUTOMX_DRC_DETAIL_COUNT=[drc list count total]\"\n"
           "set rules [drc listall why]\n"
           "foreach {rule boxes} $rules {\n"
           "    puts \"AUTOMX_DRC_DETAIL_RULE: $rule COUNT=[llength $boxes]\"\n"
           "    foreach area $boxes {puts \"AUTOMX_DRC_DETAIL_BOX: $area\"}\n"
           "}\n"
           "quit -noprompt\n")
    result = stage5._magic(magic, tech, build, tcl, timeout_s)
    folder.mkdir(parents=True, exist_ok=True)
    log = folder / "drc_detail.log"
    if log.is_file():
        raise FileExistsError(f"DRC diagnostic log already exists: {log}")
    log.write_text(result.stdout + result.stderr, encoding="utf-8")
    marker = re.findall(r"(?m)^AUTOMX_DRC_DETAIL_COUNT=(\d+)\s*$",
                        result.stdout + result.stderr)
    rules = re.findall(r"(?m)^AUTOMX_DRC_DETAIL_RULE: (.*?) COUNT=(\d+)\s*$",
                       result.stdout + result.stderr)
    report = {
        "format": "automx-cim-precharge-leaf-drc-detail-v1",
        "status": "DIAGNOSTIC_READY" if result.returncode == 0 and len(marker) == 1
                  else "DIAGNOSTIC_FAILED",
        "tag": tag,
        "source_mag_sha256": campaign._sha(mag),
        "magic_technology_sha256": campaign._sha(tech),
        "magic_returncode": result.returncode,
        "drc_count": int(marker[0]) if len(marker) == 1 else None,
        "rules": [{"rule": rule, "count": int(count)} for rule, count in rules],
        "log": str(log.relative_to(root)).replace("\\", "/"),
        "log_sha256": campaign._sha(log),
    }
    if report["drc_count"] and not report["rules"]:
        report["status"] = "DIAGNOSTIC_INCOMPLETE"
    campaign._save(folder / "drc_detail.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--pdk-root", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--timeout-s", type=int, default=900)
    args = parser.parse_args()
    print(json.dumps(run(args.root, pdk_root=args.pdk_root, tag=args.tag,
                         timeout_s=args.timeout_s), indent=2))

#!/usr/bin/env python3
"""Extract RC from the verified four-terminal precharge leaf GDS on the server.

This measures one PFET leaf. It does not validate the sampler or wrapper.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.physical import stage5  # noqa: E402
from scripts import run_flow2_precharge_leaf_layout as leaf  # noqa: E402
from scripts import run_flow2_precharge_leaf_lvs as lvs  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402

FORMAT = "automx-cim-flow2-precharge-leaf-pex-v1"
EXPECTED_PINS = ("D", "G", "S", "B")


def _source(root: Path, tag: str) -> tuple[Path, Path, dict]:
    audit, gds = lvs._read_verified_leaf(root, tag, guarded=True)
    folder = root / leaf.OUTPUT / tag
    receipt_path = folder / "electrical_lvs.json"
    if not receipt_path.is_file():
        raise FileNotFoundError(f"completed guarded-leaf LVS is required: {receipt_path}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (receipt.get("format") != "automx-cim-flow2-precharge-leaf-lvs-guarded-v1" or
            receipt.get("status") != "LVS_PASS_PRECHARGE_LEAF_ONLY" or
            receipt.get("tag") != tag or receipt.get("cell") != leaf.CELL or
            receipt.get("view_audit_sha256") != campaign._sha(folder / "view_audit.json") or
            receipt.get("gds_sha256") != campaign._sha(gds) or
            receipt.get("magic_technology_sha256") != audit["magic_technology_sha256"] or
            receipt.get("reference_sha256") !=
            lvs.sha256(lvs.reference_spice(guarded=True).encode()).hexdigest() or
            receipt.get("magic_returncode") != 0 or
            receipt.get("netgen_returncode") != 0 or
            receipt.get("netgen_match") is not True or
            receipt.get("extracted_pfet_count") != 1 or
            set(receipt.get("extracted_pins", [])) != set(EXPECTED_PINS)):
        raise ValueError("current guarded-leaf DRC/LVS evidence is required")
    for key in ("extract_log", "netgen_log", "extracted_spice"):
        item = receipt.get(key)
        path = (root / item["path"]).resolve() if isinstance(item, dict) else None
        if (path is None or not path.is_relative_to(root) or not path.is_file() or
                campaign._sha(path) != item.get("sha256")):
            raise ValueError(f"LVS {key} is missing or changed")
    return gds, receipt_path, audit


def _parasitic_counts(path: Path) -> dict[str, int]:
    """Count SPICE resistor/capacitor elements, including nested subcircuits."""
    text = path.read_text(encoding="utf-8", errors="replace")
    counts = {"resistors": 0, "capacitors": 0}
    for line in text.splitlines():
        fields = line.strip().split()
        if len(fields) >= 4 and not line.lstrip().startswith(("*", ".", "+")):
            if fields[0][0].lower() == "r":
                counts["resistors"] += 1
            elif fields[0][0].lower() == "c":
                counts["capacitors"] += 1
    return counts


def _canonicalize(raw: Path, output: Path) -> tuple[str, ...]:
    name = f"{leaf.CELL}_pex"
    actual = stage5.parse_spice_subckt_pins(raw, name)
    if len(actual) != 4 or set(actual) != set(EXPECTED_PINS):
        raise ValueError(f"PEX pin contract differs: {actual}")
    source = raw.read_text(encoding="utf-8")
    source, changed = re.subn(
        rf"(?im)^(\s*\.subckt\s+){re.escape(name)}(?=\s)",
        lambda match: match.group(1) + f"{name}_raw", source, count=1)
    if changed != 1:
        raise ValueError("PEX top subcircuit missing")
    source = re.sub(rf"(?im)^(\s*\.ends\s+){re.escape(name)}(?=\s|$)",
                    lambda match: match.group(1) + f"{name}_raw", source, count=1)
    source = re.sub(r"(?im)^\s*\.end\s*$", "", source)
    wrapper = (f"\n* Ordered D G S B interface; B and S tie to VPWR in the parent.\n"
               f".subckt {name} {' '.join(EXPECTED_PINS)}\n"
               f"XPEX_RAW {' '.join(actual)} {name}_raw\n"
               f".ends {name}\n")
    output.write_text(source.rstrip() + "\n" + wrapper, encoding="utf-8")
    return actual


def run(root: str | Path, *, pdk_root: str | Path | None = None,
        tag: str = "precharge_leaf_guarded_20261017_03",
        execute: bool = False, timeout_s: int = 900) -> dict:
    root = Path(root).resolve()
    if not leaf.TAG_RE.fullmatch(tag) or timeout_s <= 0:
        raise ValueError("invalid leaf tag or timeout")
    gds, lvs_path, audit = _source(root, tag)
    pdk = leaf._pdk(root, Path(pdk_root) if pdk_root is not None else None)
    tech = pdk / "libs.tech/magic/sky130A.tech" if pdk else None
    magic = stage5._find_tool("magic")
    reasons = []
    if not tech or not tech.is_file() or campaign._sha(tech) != audit["magic_technology_sha256"]:
        reasons.append("Magic technology differs from DRC/LVS run")
    if not magic:
        reasons.append("Magic executable is missing")
    folder = root / leaf.OUTPUT / tag
    receipt_path = folder / "electrical_pex.json"
    report = {
        "format": FORMAT,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_PREREQUISITES" if reasons else "READY_TO_RUN",
        "scope": "one guarded 1.68 um precharge PFET; RC extraction from published GDS",
        "tag": tag,
        "cell": leaf.CELL,
        "gds_sha256": campaign._sha(gds),
        "lvs_receipt_sha256": campaign._sha(lvs_path),
        "magic_technology_sha256": campaign._sha(tech) if tech and tech.is_file() else None,
        "magic_executable": magic,
        "missing_prerequisites": reasons,
        "not_signoff": "leaf PEX only; no post-layout transfer, sampler, ADC, complete wrapper or PVT sign-off",
    }
    if reasons or not execute:
        return report
    if receipt_path.is_file():
        saved = json.loads(receipt_path.read_text(encoding="utf-8"))
        for key in ("format", "tag", "cell", "gds_sha256", "lvs_receipt_sha256",
                    "magic_technology_sha256"):
            if saved.get(key) != report[key]:
                raise FileExistsError(f"PEX input changed; use a new tag: {receipt_path}")
        for key in ("magic_log", "raw_pex", "pex"):
            item = saved.get(key)
            if item:
                path = (root / item["path"]).resolve()
                if (not path.is_relative_to(root) or not path.is_file() or
                        campaign._sha(path) != item["sha256"]):
                    raise FileExistsError(f"PEX artifact differs from receipt: {path}")
        return saved
    build = root / "build/flow2_periphery_leaf" / tag / "electrical_pex"
    if build.exists() and any(build.iterdir()):
        raise FileExistsError(f"interrupted PEX build needs inspection: {build}")
    build.mkdir(parents=True, exist_ok=True)
    raw = build / f"{leaf.CELL}.pex.raw.spice"
    canonical = build / f"{leaf.CELL}.pex.spice"
    tcl = ("crashbackups stop\n"
           f"gds read {{{gds.as_posix()}}}\n"
           f"load {leaf.CELL}\nselect top cell\n"
           f"flatten {leaf.CELL}_pex\nload {leaf.CELL}_pex\nselect top cell\n"
           "extract do local\nextract do unique\nextract do resistance\n"
           "extresist threshold 100\nextresist mindelay 0\nextresist minres 10\n"
           "extract all\nputs \"AUTOMX_PRECHARGE_PEX_EXTRACT_DONE\"\n"
           "ext2spice lvs\next2spice scale off\next2spice cthresh 0.1\n"
           "ext2spice extresist on\next2spice short resistor\n"
           "ext2spice subcircuit on\next2spice subcircuit top on\n"
           f"ext2spice -o {raw.name}\n"
           "puts \"AUTOMX_PRECHARGE_PEX_DONE\"\nquit -noprompt\n")
    result = stage5._magic(magic, tech, build, tcl, timeout_s)
    log = folder / "electrical_pex_magic.log"
    log.write_text(result.stdout + result.stderr, encoding="utf-8")
    report["magic_log"] = {"path": log.relative_to(root).as_posix(),
                           "sha256": campaign._sha(log)}
    report["magic_returncode"] = result.returncode
    output = result.stdout + result.stderr
    report["rc_nets_output"] = sum(int(n) for n in re.findall(
        r"(?m)^Nets output:\s*(\d+)", output))
    if (result.returncode or "AUTOMX_PRECHARGE_PEX_EXTRACT_DONE" not in output or
            "AUTOMX_PRECHARGE_PEX_DONE" not in output or
            not raw.is_file() or not raw.stat().st_size):
        report["status"] = "BLOCKED_MAGIC_PEX"
    else:
        report["raw_pex"] = {"path": raw.relative_to(root).as_posix(),
                             "sha256": campaign._sha(raw)}
        try:
            actual = _canonicalize(raw, canonical)
            devices = stage5._spice_device_count(canonical, f"{leaf.CELL}_pex",
                                                  "sky130_fd_pr__pfet_01v8")
            parasitics = _parasitic_counts(raw)
            if devices != 1:
                raise ValueError(f"expected one PFET in PEX, found {devices}")
            report["raw_pins"] = list(actual)
            report["extracted_pfet_count"] = devices
            report["parasitic_elements"] = parasitics
            if not sum(parasitics.values()):
                raise ValueError("PEX has no resistor or capacitor elements")
            published = (root / "physical/sky130/wrapper_prototype/leaf_cells" /
                         tag / f"{leaf.CELL}.pex.spice")
            published.parent.mkdir(parents=True, exist_ok=True)
            if published.is_file() and campaign._sha(published) != campaign._sha(canonical):
                raise FileExistsError(f"published PEX differs: {published}")
            if not published.is_file():
                shutil.copy2(canonical, published)
            report["pex"] = {"path": published.relative_to(root).as_posix(),
                             "sha256": campaign._sha(published)}
            report["status"] = "MEASURED_PRECHARGE_LEAF_PEX_ONLY"
        except (OSError, ValueError) as error:
            report["status"] = "BLOCKED_PEX_INTERFACE_OR_PARASITICS"
            report["error"] = str(error)
    campaign._save(receipt_path, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--tag", default="precharge_leaf_guarded_20261017_03")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=900)
    args = parser.parse_args()
    print(json.dumps(run(args.root, pdk_root=args.pdk_root, tag=args.tag,
                         execute=args.run, timeout_s=args.timeout_s), indent=2))

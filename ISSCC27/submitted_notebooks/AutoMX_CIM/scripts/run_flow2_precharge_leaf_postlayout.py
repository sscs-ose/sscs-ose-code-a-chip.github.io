#!/usr/bin/env python3
"""Compare schematic and GDS-extracted precharge leaf in one TT transient.

The isolated PFET charges an 820 fF bitline. This diagnostic does not model
the passive core, sampler, hold capacitor, sense circuit or ADC.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.physical import stage5  # noqa: E402
from automx_cim.spice import parse_measurements  # noqa: E402
from scripts import run_flow2_precharge_leaf_layout as leaf  # noqa: E402
from scripts import run_flow2_precharge_leaf_lvs as lvs  # noqa: E402
from scripts import run_flow2_precharge_leaf_pex as pex  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402

FORMAT = "automx-cim-flow2-precharge-leaf-postlayout-tt-v1"
MEASURES = ("bl_pre", "bl_on", "bl_before_off", "bl_after_off")


def _substrate_cap_count(path: Path) -> int:
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.strip().split()
        if (len(fields) >= 4 and fields[0].lower().startswith("c") and
                "VSUBS" in (fields[1].upper(), fields[2].upper())):
            count += 1
    return count


def _source(root: Path, tag: str) -> tuple[Path, Path, Path, dict]:
    gds, lvs_path, _ = pex._source(root, tag)
    receipt_path = root / leaf.OUTPUT / tag / "electrical_pex.json"
    if not receipt_path.is_file():
        raise FileNotFoundError(f"leaf PEX receipt is required: {receipt_path}")
    report = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (report.get("format") != pex.FORMAT or
            report.get("status") != "MEASURED_PRECHARGE_LEAF_PEX_ONLY" or
            report.get("tag") != tag or report.get("cell") != leaf.CELL or
            report.get("gds_sha256") != campaign._sha(gds) or
            report.get("lvs_receipt_sha256") != campaign._sha(lvs_path) or
            report.get("magic_returncode") != 0 or
            report.get("extracted_pfet_count") != 1 or
            set(report.get("raw_pins", [])) != set(pex.EXPECTED_PINS) or
            sum(report.get("parasitic_elements", {}).values()) <= 0):
        raise ValueError("current, nonempty guarded-leaf PEX is required")
    for key in ("magic_log", "raw_pex", "pex"):
        item = report.get(key)
        path = (root / item["path"]).resolve() if isinstance(item, dict) else None
        if (path is None or not path.is_relative_to(root) or not path.is_file() or
                campaign._sha(path) != item.get("sha256")):
            raise ValueError(f"leaf PEX {key} is missing or changed")
    view = (root / report["pex"]["path"]).resolve()
    if stage5.parse_spice_subckt_pins(view, f"{leaf.CELL}_pex") != pex.EXPECTED_PINS:
        raise ValueError("published PEX ordered interface changed")
    if _substrate_cap_count(view) == 0:
        raise ValueError("published PEX has no VSUBS capacitances to validate substrate tie")
    return view, receipt_path, lvs_path, report


def _deck(model: Path, netlist: Path, *, extracted: bool) -> str:
    name = f"{leaf.CELL}_pex" if extracted else leaf.CELL
    return (f".title precharge leaf {'PEX' if extracted else 'schematic'} TT\n"
            f'.lib "{model.as_posix()}" tt\n'
            ".global VSUBS\n"
            f'.include "{netlist.as_posix()}"\n'
            ".param VDD=1.8\n.temp 25\n"
            ".option method=gear reltol=1e-4 abstol=1e-12\n"
            "VVDD VPWR 0 {VDD}\nVVSUBS VSUBS 0 0\n"
            "VG G 0 PULSE({VDD} 0 0.2n 5p 5p 1n 5n)\n"
            f"XPRE BL G VPWR VPWR {name}\n"
            "CBL BL 0 820f\nRDC BL 0 100k\n"
            ".measure tran bl_pre FIND V(BL) AT=0.1n\n"
            ".measure tran bl_on FIND V(BL) AT=0.5n\n"
            ".measure tran bl_before_off FIND V(BL) AT=1.19n\n"
            ".measure tran bl_after_off FIND V(BL) AT=1.25n\n"
            ".tran 1p 1.5n\n.end\n")


def _item(root: Path, path: Path) -> dict[str, str]:
    return {"path": path.relative_to(root).as_posix(),
            "sha256": campaign._sha(path)}


def run(root: str | Path, *, pdk_root: str | Path | None = None,
        tag: str = "precharge_leaf_guarded_20261017_03",
        execute: bool = False, timeout_s: int = 900) -> dict:
    root = Path(root).resolve()
    if not leaf.TAG_RE.fullmatch(tag) or timeout_s <= 0:
        raise ValueError("invalid tag or timeout")
    view, pex_receipt, lvs_receipt, pex_report = _source(root, tag)
    pdk = leaf._pdk(root, Path(pdk_root) if pdk_root is not None else None)
    model = pdk / "libs.tech/ngspice/sky130.lib.spice" if pdk else None
    ngspice = shutil.which("ngspice")
    reasons = []
    if not model or not model.is_file():
        reasons.append("SKY130 ngspice model library is missing")
    if not ngspice:
        reasons.append("ngspice is missing")
    folder = root / leaf.OUTPUT / tag
    result_path = folder / "post_layout_precharge_tt.json"
    report = {
        "format": FORMAT,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_PREREQUISITES" if reasons else "READY_TO_RUN",
        "scope": "isolated 1.68 um PFET charging 820 fF at TT/1.8 V/25 C",
        "tag": tag,
        "lvs_receipt_sha256": campaign._sha(lvs_receipt),
        "pex_receipt_sha256": campaign._sha(pex_receipt),
        "pex_sha256": campaign._sha(view),
        "pex_substrate_capacitors": _substrate_cap_count(view),
        "substrate_assumption": "VSUBS declared global and driven to 0 V in both decks",
        "model_sha256": campaign._sha(model) if model and model.is_file() else None,
        "ngspice_executable": ngspice,
        "missing_prerequisites": reasons,
        "not_signoff": "isolated leaf TT diagnostic only; no core, sampler, sense/ADC, wrapper PEX, timing or PVT",
    }
    if reasons or not execute:
        return report
    if (report["pex_sha256"] != pex_report["pex"]["sha256"] or
            report["lvs_receipt_sha256"] != pex_report["lvs_receipt_sha256"]):
        raise ValueError("PEX source lineage changed")
    if result_path.is_file():
        saved = json.loads(result_path.read_text(encoding="utf-8"))
        for key in ("format", "tag", "lvs_receipt_sha256", "pex_receipt_sha256",
                    "pex_sha256", "model_sha256"):
            if saved.get(key) != report[key]:
                raise FileExistsError(f"post-layout input changed: {result_path}")
        for job in saved.get("jobs", {}).values():
            for key in ("deck", "log"):
                item = job.get(key)
                path = (root / item["path"]).resolve() if isinstance(item, dict) else None
                if (path is None or not path.is_relative_to(root) or not path.is_file() or
                        campaign._sha(path) != item.get("sha256")):
                    raise FileExistsError(f"post-layout {key} changed")
        return saved
    build = root / "build/flow2_periphery_leaf" / tag / "post_layout_tt"
    if build.exists() and any(build.iterdir()):
        raise FileExistsError(f"interrupted post-layout run needs inspection: {build}")
    build.mkdir(parents=True, exist_ok=True)
    reference = build / f"{leaf.CELL}.reference.spice"
    reference.write_text(lvs.reference_spice(guarded=True), encoding="utf-8")
    jobs = {}
    for name, netlist, extracted in (("schematic", reference, False), ("pex", view, True)):
        deck = build / f"{name}.spice"
        log = folder / f"post_layout_{name}.log"
        deck.write_text(_deck(model, netlist, extracted=extracted), encoding="utf-8")
        job = {"deck": _item(root, deck)}
        jobs[name] = job
        try:
            completed = stage5._run([ngspice, "-b", "-o", str(log), str(deck)],
                                    build, timeout_s)
            job["returncode"] = completed.returncode
            output = (log.read_text(encoding="utf-8", errors="replace")
                      if log.is_file() else completed.stdout + completed.stderr)
        except subprocess.TimeoutExpired:
            job["returncode"] = None
            output = f"ngspice timed out after {timeout_s}s\n"
        if not log.is_file():
            log.write_text(output, encoding="utf-8")
        job["log"] = _item(root, log)
        values = parse_measurements(output, expected=MEASURES)
        job["measurements_v"] = values
        if job["returncode"] != 0 or set(values) != set(MEASURES) or not all(
                math.isfinite(value) for value in values.values()):
            report["status"] = "BLOCKED_PRECHARGE_TRANSIENT"
            break
    report["jobs"] = jobs
    if report["status"] == "READY_TO_RUN":
        schematic = jobs["schematic"]["measurements_v"]
        extracted = jobs["pex"]["measurements_v"]
        report["comparison"] = {
            "absolute_pex_minus_schematic_v": {
                key: abs(extracted[key] - schematic[key]) for key in MEASURES},
            "schematic_turnoff_step_v": (schematic["bl_after_off"] -
                                          schematic["bl_before_off"]),
            "pex_turnoff_step_v": (extracted["bl_after_off"] -
                                    extracted["bl_before_off"]),
        }
        report["status"] = "MEASURED_PRECHARGE_LEAF_POSTLAYOUT_TT_DIAGNOSTIC"
    campaign._save(result_path, report)
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

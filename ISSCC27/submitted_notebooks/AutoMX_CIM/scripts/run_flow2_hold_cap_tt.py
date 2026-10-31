#!/usr/bin/env python3
"""Measure the isolated MIM3 hold-cap candidate at TT with schematic and PEX.

This measures charge per voltage ramp. It does not measure long-term retention,
sampler acquisition, ADC loading, or the composite wrapper.
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
from scripts import run_flow2_hold_cap_leaf as leaf  # noqa: E402
from scripts import run_flow2_hold_cap_pex as pex  # noqa: E402
from scripts import run_flow2_precharge_leaf_layout as precharge  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402

FORMAT = "automx-cim-flow2-hold-cap-tt-charge-v1"
DEFAULT_TAG = "hold_cap_charge_tt_20261017_01"
MEASURES = ("charge_c", "v_before", "v_after", "late_current_a")


def _item(root: Path, path: Path) -> dict[str, str]:
    return {"path": path.relative_to(root).as_posix(), "sha256": campaign._sha(path)}


def _verified_file(root: Path, item: object, name: str) -> Path:
    if not isinstance(item, dict) or not isinstance(item.get("path"), str):
        raise ValueError(f"{name} is absent from the PEX receipt")
    path = (root / item["path"]).resolve()
    if (not path.is_relative_to(root) or not path.is_file() or
            campaign._sha(path) != item.get("sha256")):
        raise ValueError(f"{name} file or SHA-256 differs")
    return path


def _source(root: Path, source_tag: str, pex_tag: str) -> tuple[Path, Path, Path]:
    gds, leaf_receipt, _ = pex._source(root, source_tag)
    receipt_path = root / leaf.OUTPUT / pex_tag / "hold_cap_pex.json"
    if not receipt_path.is_file():
        raise FileNotFoundError(f"hold-cap PEX receipt is required: {receipt_path}")
    report = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (report.get("format") != pex.FORMAT or
            report.get("status") != "MEASURED_HOLD_CAP_LEAF_PEX_ONLY" or
            report.get("tag") != pex_tag or
            report.get("source_tag") != source_tag or
            report.get("cell") != leaf.CELL or
            report.get("gds_sha256") != campaign._sha(gds) or
            report.get("lvs_receipt_sha256") != campaign._sha(leaf_receipt) or
            report.get("magic_returncode") != 0 or
            report.get("extracted_mim_device_count") != 1 or
            report.get("parasitic_elements", {}).get("capacitors", 0) < 1):
        raise ValueError("current, capacitor-containing hold-cap PEX is required")
    for key in ("magic_log", "raw_pex", "pex"):
        _verified_file(root, report.get(key), key)
    view = _verified_file(root, report["pex"], "pex")
    if stage5.parse_spice_subckt_pins(view, f"{leaf.CELL}_pex") != pex.PINS:
        raise ValueError("hold-cap PEX ordered interface changed")
    return view, receipt_path, leaf_receipt


def _deck(model: Path, netlist: Path, *, extracted: bool) -> str:
    cell = f"{leaf.CELL}_pex" if extracted else leaf.CELL
    return (f".title isolated hold-cap {'PEX' if extracted else 'schematic'} TT charge\n"
            f'.lib "{model.as_posix()}" tt\n'
            f'.include "{netlist.as_posix()}"\n'
            ".temp 25\n.option method=gear reltol=1e-5 abstol=1e-15\n"
            "VDRIVE HOLD 0 PWL(0 0 1n 0 2n 1.8 6n 1.8)\n"
            f"XCAP HOLD 0 {cell}\n"
            ".measure tran charge_c INTEG I(VDRIVE) FROM=1n TO=2n\n"
            ".measure tran v_before FIND V(HOLD) AT=1n\n"
            ".measure tran v_after FIND V(HOLD) AT=2n\n"
            ".measure tran late_current_a AVG I(VDRIVE) FROM=5n TO=6n\n"
            ".tran 2p 6n\n.end\n")


def run(root: str | Path, *, pdk_root: str | Path | None = None,
        source_tag: str = pex.DEFAULT_SOURCE_TAG,
        pex_tag: str = pex.DEFAULT_TAG, tag: str = DEFAULT_TAG,
        execute: bool = False, timeout_s: int = 900) -> dict:
    root = Path(root).resolve()
    if (not all(precharge.TAG_RE.fullmatch(value) for value in
                (source_tag, pex_tag, tag)) or len({source_tag, pex_tag, tag}) != 3 or
            timeout_s <= 0):
        raise ValueError("invalid hold-cap source, PEX or measurement tag")
    view, pex_receipt, leaf_receipt = _source(root, source_tag, pex_tag)
    pdk = precharge._pdk(root, Path(pdk_root) if pdk_root is not None else None)
    model = pdk / "libs.tech/ngspice/sky130.lib.spice" if pdk else None
    ngspice = shutil.which("ngspice")
    reasons = []
    if not model or not model.is_file():
        reasons.append("SKY130 ngspice model library is missing")
    if not ngspice:
        reasons.append("ngspice is missing")
    folder = root / leaf.OUTPUT / tag
    receipt_path = folder / "hold_cap_charge_tt.json"
    report = {
        "format": FORMAT,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_PREREQUISITES" if reasons else "READY_TO_RUN",
        "scope": "isolated MIM3 capacitor, TT/25 C, 0-to-1.8 V in 1 ns",
        "tag": tag, "source_tag": source_tag, "pex_tag": pex_tag,
        "leaf_receipt_sha256": campaign._sha(leaf_receipt),
        "pex_receipt_sha256": campaign._sha(pex_receipt),
        "pex_sha256": campaign._sha(view),
        "model_sha256": campaign._sha(model) if model and model.is_file() else None,
        "script_sha256": campaign._sha(Path(__file__)),
        "ngspice_executable": ngspice,
        "missing_prerequisites": reasons,
        "not_signoff": "one TT charge-ramp diagnostic; no sampler, realistic leakage/retention, ADC loading, composite LVS or PVT",
    }
    if reasons or not execute:
        return report
    if receipt_path.is_file():
        saved = json.loads(receipt_path.read_text(encoding="utf-8"))
        for key in ("format", "tag", "source_tag", "pex_tag", "leaf_receipt_sha256",
                    "pex_receipt_sha256", "pex_sha256", "model_sha256", "script_sha256"):
            if saved.get(key) != report[key]:
                raise FileExistsError(f"hold-cap TT inputs changed: {receipt_path}")
        for job in saved.get("jobs", {}).values():
            for key in ("deck", "log"):
                _verified_file(root, job.get(key), key)
        return saved
    build = root / "build/flow2_periphery_leaf" / tag / "charge_tt"
    if build.exists() and any(build.iterdir()):
        raise FileExistsError(f"interrupted hold-cap TT run needs inspection: {build}")
    build.mkdir(parents=True, exist_ok=True)
    folder.mkdir(parents=True, exist_ok=True)
    reference = build / f"{leaf.CELL}.reference.spice"
    reference.write_text(leaf.reference_spice(), encoding="utf-8")
    jobs = {}
    for name, netlist, extracted in (("schematic", reference, False),
                                     ("pex", view, True)):
        deck = build / f"{name}.spice"
        log = folder / f"hold_cap_{name}_tt.log"
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
        job["measurements"] = values
        if (job["returncode"] != 0 or set(values) != set(MEASURES) or
                not all(math.isfinite(value) for value in values.values())):
            report["status"] = "BLOCKED_HOLD_CAP_TT_SIMULATION"
            break
        delta_v = values["v_after"] - values["v_before"]
        if not 1.75 <= delta_v <= 1.85:
            report["status"] = "BLOCKED_HOLD_CAP_TT_VOLTAGE_RAMP"
            break
        job["charge_magnitude_c"] = abs(values["charge_c"])
        job["effective_capacitance_ff"] = abs(values["charge_c"]) / delta_v * 1e15
    report["jobs"] = jobs
    if report["status"] == "READY_TO_RUN":
        sch = jobs["schematic"]["effective_capacitance_ff"]
        post = jobs["pex"]["effective_capacitance_ff"]
        report["difference_ff"] = post - sch
        report["status"] = "MEASURED_HOLD_CAP_TT_CHARGE_DIAGNOSTIC"
    campaign._save(receipt_path, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--source-tag", default=pex.DEFAULT_SOURCE_TAG)
    parser.add_argument("--pex-tag", default=pex.DEFAULT_TAG)
    parser.add_argument("--tag", default=DEFAULT_TAG)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=900)
    args = parser.parse_args()
    print(json.dumps(run(args.root, pdk_root=args.pdk_root,
                         source_tag=args.source_tag, pex_tag=args.pex_tag,
                         tag=args.tag, execute=args.run,
                         timeout_s=args.timeout_s), indent=2))

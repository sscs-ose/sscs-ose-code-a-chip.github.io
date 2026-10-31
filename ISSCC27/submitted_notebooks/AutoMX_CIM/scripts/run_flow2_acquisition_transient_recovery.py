#!/usr/bin/env python3
"""Remeasure six acquisition transients using existing verified physical views.

No Magic, KLayout, Netgen, layout generation or PEX job is rerun. Old source
receipts stay read only, including the invalid _03 zero-valued measurements.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_flow2_acquisition_layout as acq
from scripts.run_flow2_remaining_measurements import _save, _sha

DEFAULT_PDK = Path("/home/nam/.volare/volare/sky130/versions/bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A")


def verify_physical_source(root: Path, tag: str) -> dict:
    receipt = root / acq.BASE / tag / "summary.json"
    source = json.loads(receipt.read_text(encoding="utf-8"))
    if source.get("format") != acq.FORMAT or source.get("tag") != tag:
        raise ValueError("source acquisition receipt differs")
    expected = {"nfet": 10, "pfet": 18, "mim3": 8}
    if source.get("layout_variant") == "FOUR_LOCAL_DIFFERENTIAL_BANKS_V1":
        if source.get("physical_bitline_capacitor_replicas_per_node") != 20:
            raise ValueError("banked acquisition must contain twenty physical MIMs per bitline")
        expected["mim3"] = 168
    if (any(source.get(k) != 0 for k in ("magic_drc_violations", "magic_gds_drc_violations", "klayout_drc_violations"))
            or source.get("transistor_lvs_match") is not True or source.get("extracted_devices") != expected):
        raise ValueError("source acquisition physical checks did not pass")
    artifacts = source.get("artifacts", [])
    indexed = {item["path"] for item in artifacts}
    if not artifacts or len(indexed) != len(artifacts):
        raise ValueError("source artifact inventory is missing or duplicated")
    for item in artifacts:
        acq._verified(root, item)
    folder = root / acq.BASE / tag
    build = root / "build/flow2_periphery_leaf" / tag
    physical = root / "physical/sky130/wrapper_prototype/leaf_cells" / tag

    def needed(path):
        if path.relative_to(root).as_posix() not in indexed:
            raise ValueError(f"unverified physical source file: {path}")
        return path

    layout_log = needed(folder / "layout.log").read_text(encoding="utf-8")
    extracted_log = needed(folder / "lvs_extract.log").read_text(encoding="utf-8")
    if acq.drc_details(layout_log)["count"] != 0 or not re.search(
            r"(?m)^AUTOMX_ACQUISITION_GDS_DRC=0\s*$", extracted_log):
        raise ValueError("source raw Magic DRC logs differ")
    xml = ET.parse(needed(folder / "klayout.xml")).getroot()
    if xml.tag != "report-database" or list(xml.iter("item")):
        raise ValueError("source raw KLayout DRC is not clean")
    if not acq.fet_lvs._netgen_match(needed(folder / "netgen.log").read_text(encoding="utf-8")):
        raise ValueError("source raw transistor LVS log does not match")
    lvs = needed(build / "lvs_extract" / f"{acq.CELL}.lvs.spice")
    for kind, count in expected.items():
        primitive = "sky130_fd_pr__cap_mim_m3_1" if kind == "mim3" else f"sky130_fd_pr__{kind}_01v8"
        if acq.stage5._spice_device_count(lvs, acq.CELL, primitive) != count:
            raise ValueError(f"source extracted device count differs: {kind}")
    raw = needed(build / "pex" / f"{acq.CELL}.pex.raw.spice")
    rc = acq._rc_audit(raw)
    parasitics = acq.precharge_pex._parasitic_counts(raw)
    if not rc["nonzero_resistors"] or rc["unreferenced_capacitive_nodes"] or not parasitics["capacitors"]:
        raise ValueError("source distributed RC/ground audit differs")
    paths = {"schematic": needed(physical / f"{acq.CELL}.reference.spice"),
             "pex": needed(physical / f"{acq.CELL}.pex.spice")}
    for path in paths.values():
        # Both canonical files expose the explicit ordered interface.
        cell = acq.CELL + ("_pex" if path == paths["pex"] else "")
        if acq.stage5.parse_spice_subckt_pins(path, cell) != acq.PINS:
            raise ValueError("source simulation port order differs")
    old_errors = []
    for job in source.get("jobs", []):
        log = acq._verified(root, job["log"]).read_text(encoding="utf-8", errors="replace")
        errors = re.findall(r"(?im)^\s*Error:[^\n]*", log)
        if errors:
            old_errors.append({"corner": job["corner"], "variant": job["variant"],
                               "error_count": len(errors), "first_error": errors[0].strip()})
    return {"receipt": receipt, "report": source, "netlists": paths,
            "physical_gate": {"status": "VERIFIED_DRC_LVS_DISTRIBUTED_RC_PEX",
                "magic_drc": 0, "klayout_drc": 0, "transistor_lvs": True,
                "devices": expected, "parasitics": parasitics, "substrate_rc_audit": rc},
            "old_measurement_errors": old_errors}


def _bundle(root: Path, tag: str, source: dict) -> Path:
    acq.exporter.export(root, tag=tag, include_measured_cap=False)
    paths = {}
    for item in source["report"]["artifacts"]:
        path = acq._verified(root, item)
        paths[item["path"]] = path
    paths[source["receipt"].relative_to(root).as_posix()] = source["receipt"]
    for base in (root / acq.BASE / tag, root / "build/flow2_periphery_leaf" / tag):
        for path in base.rglob("*"):
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError("diagnostic source escapes checkout")
            if path.is_file():
                paths[path.relative_to(root).as_posix()] = path
    destination = root / "server_results" / acq.BASE / tag
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    archive = destination / f"diagnostics_{stamp}.zip"
    index = {"format": "automx-cim-acquisition-transient-recovery-export-v1", "tag": tag,
             "files": [{"path": rel, "sha256": _sha(path)} for rel, path in sorted(paths.items())]}
    with ZipFile(archive, "x", compression=ZIP_DEFLATED) as output:
        for rel, path in sorted(paths.items()):
            output.write(path, rel)
        output.writestr("diagnostic_index.json", json.dumps(index, indent=2) + "\n")
    index["archive"] = {"path": archive.relative_to(root).as_posix(), "sha256": _sha(archive)}
    _save(archive.with_suffix(".json"), index)
    return archive


def run(root: Path, *, pdk_root: Path = DEFAULT_PDK,
        source_tag: str = "physical_next_20261018_03_acq",
        tag: str = "acquisition_transient_20261018_04", execute: bool = False,
        timeout_s: int = 900) -> dict:
    root = root.resolve()
    if (not all(acq.precharge.TAG_RE.fullmatch(s) for s in (tag, source_tag))
            or tag == source_tag or timeout_s <= 0):
        raise ValueError("distinct safe source/output tags and positive timeout required")
    source = verify_physical_source(root, source_tag)
    pdk = acq.precharge._pdk(root, pdk_root)
    model = pdk / "libs.tech/ngspice/sky130.lib.spice"
    if _sha(model) != source["report"]["model_sha256"]:
        raise ValueError("source and recovery PDK model hashes differ")
    report = {"format": "automx-cim-acquisition-transient-recovery-v1", "tag": tag,
              "source_tag": source_tag, "status": "READY_TO_REMEASURE_SIX_TRANSIENTS",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "physical_gate": source["physical_gate"],
              "source_receipt_sha256": _sha(source["receipt"]),
              "discarded_old_measurement_errors": source["old_measurement_errors"],
              "planned_sims": 6, "completed_sims": 0, "reused_checkpoints": 0,
              "capture_budget_v": 0.0008, "capture_budget_met_in_driven_cases": None,
              "post_sample_ns": acq.POST_SAMPLE_NS, "late_sample_ns": acq.LATE_SAMPLE_NS,
              "jobs": [], "not_signoff": "driven-bitline acquisition only; no core/ADC, fresh MHA holdout, full PVT, LIB/SPEF or wrapper STA"}
    if not execute:
        return report
    ngspice = acq.stage5._find_tool("ngspice")
    if not ngspice:
        raise FileNotFoundError("ngspice executable missing")
    version = acq.stage5._tool_version("ngspice", ngspice)
    if not version or version.startswith("ERROR:"):
        raise RuntimeError("ngspice version could not be recorded")
    frozen = {"source_receipt_sha256": report["source_receipt_sha256"],
              "script_sha256": _sha(Path(__file__)), "measurement_library_sha256": _sha(Path(acq.__file__)),
              "model_sha256": _sha(model), "ngspice_version": version}
    folder, build = root / acq.BASE / tag, root / "build/flow2_periphery_leaf" / tag
    snapshot = build / "inputs.json"
    if snapshot.is_file():
        if json.loads(snapshot.read_text(encoding="utf-8")) != frozen:
            raise FileExistsError("recovery inputs changed; retain this run and use a new tag")
    elif (build.exists() and any(build.iterdir())) or folder.exists():
        raise FileExistsError("untracked recovery artifacts exist; use a new tag")
    build.mkdir(parents=True, exist_ok=True)
    folder.mkdir(parents=True, exist_ok=True)
    if not snapshot.is_file():
        _save(snapshot, frozen)
    report["inputs"] = frozen

    def note(message):
        line = f"[{datetime.now(timezone.utc).isoformat()}] {message}"
        print(line, flush=True)
        with (folder / "history.log").open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")

    try:
        note("START six scalar-voltage transients; physical views reused without EDA regeneration")
        for corner in acq.CORNERS:
            for variant, netlist in source["netlists"].items():
                name = f"{corner}_{variant}"
                work = build / name
                work.mkdir(exist_ok=True)
                deck, cache, log = work / "capture.spice", work / "job.receipt.json", folder / f"{name}.log"
                text = acq._capture_deck(model, netlist, variant == "pex", corner)
                cached = json.loads(cache.read_text(encoding="utf-8")) if cache.is_file() else None
                valid = (cached and cached.get("returncode") == 0 and deck.is_file() and log.is_file()
                    and deck.read_text(encoding="utf-8") == text and cached.get("deck", {}).get("sha256") == _sha(deck)
                    and cached.get("log", {}).get("sha256") == _sha(log))
                if valid:
                    try:
                        analysis = acq._analyze_capture_log(log.read_text(encoding="utf-8"), corner)
                    except ValueError:
                        valid = False
                if valid:
                    entry = {**cached, **analysis}
                    report["reused_checkpoints"] += 1
                    note(f"REUSE {name}")
                else:
                    stale = [path for path in (deck, cache, log) if path.is_file()]
                    if stale:
                        archive = build / "stale" / (name + "_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f"))
                        archive.mkdir(parents=True)
                        for path in stale:
                            shutil.copy2(path, archive / path.name)
                        note(f"ARCHIVE interrupted/invalid {name}; rerun this job only")
                    deck.write_text(text, encoding="utf-8")
                    result = acq._call(acq.stage5._run, [ngspice, "-b", str(deck)], work, timeout_s)
                    log.write_text(result.stdout + result.stderr, encoding="utf-8")
                    entry = {"corner": corner, "variant": variant, "returncode": result.returncode,
                             "deck": acq._item(root, deck), "log": acq._item(root, log)}
                    if result.returncode:
                        report["jobs"].append(entry)
                        raise RuntimeError(f"ngspice failed/timed out: {name}; see {log}")
                    try:
                        entry.update(acq._analyze_capture_log(result.stdout + result.stderr, corner))
                    except ValueError as error:
                        entry["measurement_error"] = str(error)
                        report["jobs"].append(entry)
                        raise
                    _save(cache, entry)
                    note(f"MEASURED {name}: capture={entry['maximum_capture_error_v']:.6g} V")
                report["jobs"].append(entry)
                report["completed_sims"] += 1
                _save(folder / "summary.json", report)
        report["capture_budget_met_in_driven_cases"] = all(
            j["maximum_capture_error_v"] <= 0.0008 for j in report["jobs"] if j["variant"] == "pex")
        report["status"] = "MEASURED_ACQUISITION_DRIVEN_TRANSIENT_DIAGNOSTIC"
        report["conclusion"] = ("CAPTURE_BUDGET_MET_IN_DRIVEN_CASES_ONLY" if report["capture_budget_met_in_driven_cases"]
                                else "CAPTURE_BUDGET_EXCEEDED_IN_DRIVEN_CASES")
    except BaseException as error:
        report["status"] = "INTERRUPTED" if isinstance(error, KeyboardInterrupt) else "BLOCKED_TRANSIENT_MEASUREMENT"
        report["error"] = f"{type(error).__name__}: {error}"
        if not isinstance(error, Exception):
            raise
    finally:
        note(f"END {report['status']} {report['completed_sims']}/6")
        _save(folder / "summary.json", report)
        archive = _bundle(root, tag, source)
        print(f"Download diagnostics: {archive}", flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--pdk-root", type=Path, default=DEFAULT_PDK)
    parser.add_argument("--source-tag", default="physical_next_20261018_03_acq")
    parser.add_argument("--tag", default="acquisition_transient_20261018_04")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=900)
    args = parser.parse_args()
    result = run(args.root, pdk_root=args.pdk_root, source_tag=args.source_tag,
                 tag=args.tag, execute=args.run, timeout_s=args.timeout_s)
    print(json.dumps(result, indent=2))
    if args.run and result["status"] != "MEASURED_ACQUISITION_DRIVEN_TRANSIENT_DIAGNOSTIC":
        raise SystemExit(1)

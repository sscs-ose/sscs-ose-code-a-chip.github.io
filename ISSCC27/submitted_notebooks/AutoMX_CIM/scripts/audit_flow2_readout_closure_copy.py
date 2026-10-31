#!/usr/bin/env python3
"""Audit the downloaded closure bundle without executing or editing EDA evidence."""
from __future__ import annotations
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import flow2_waveforms as waves
from scripts import run_flow2_core_acquisition as core
from scripts import run_flow2_acquisition_transient_recovery as front
from scripts import audit_core_bound_clean as clean
from scripts import flow2_adc_dc as adc_dc
from scripts import flow2_adc_progress as adc_progress


def _adc_observation(folder, tag, result):
    base = folder/common.BUILD/tag
    adcbuild = base/"load_cm0900"
    if not (adcbuild/"ngspice.live.log").is_file():
        model_log = base/"pdk_model_smoke/ngspice.live.log"
        log = model_log.read_text() if model_log.is_file() else ""
        return {"status": result["status"], "error": result.get("error"),
            "model_smoke": {"KLU_selected": bool(re.search(r"Using\s+KLU\b", log)),
                "DC_returned": "AUTOMX_ADC_MODEL_PHASE=DONE" in log,
                "parser_errors": adc_dc.simulator_errors(log),
                "reported_resistance_ohms_not_validated": core.parse_measurements(log,
                    [f"r_{p}_{i}" for i in range(8) for p in ("pos", "neg")])},
            "full_ADC_transients": "NOT_LAUNCHED", "completed_conversions": 0,
            "runtime_diagnosis": "model parser gate stopped full ADC probes; DC completion alone is insufficient"}
    adc_log = (adcbuild/"ngspice.live.log").read_text()
    usage = [json.loads(l) for l in (adcbuild/"process.jsonl").read_text().splitlines()]
    adcdeck = (adcbuild/"adc.spice").read_text()
    observation = {"status": result["status"], "error": result.get("error"),
        "log_bytes": (adcbuild/"ngspice.live.log").stat().st_size,
        "phases": re.findall(r"AUTOMX_ADC_PHASE=(\w+)", adc_log),
        "BSTATE_present": bool(re.search(r"(?m)^BSTATE\s", adcdeck)),
        "last_resource_observation": usage[-1], "completed_conversions": 0,
        "runtime_diagnosis": ("RUN_ENTER reached; singular matrix/dynamic gmin in initial solve; no completed transient"
            if "AUTOMX_ADC_PHASE=RUN_ENTER" in adc_log and "singular matrix" in adc_log else
            "inspect phase markers; parsing/solve/transient completion are separate observations")}
    observation["transient_progress"] = adc_progress.observe(adc_log, adcbuild)
    if observation["transient_progress"]["last_transient_reference_s"]:
        observation["runtime_diagnosis"] = "transient time advances after DC initialization; timed out before the measurement stop time"
    if "AUTOMX_ADC_PHASE=DECK_PARSED" in adc_log:
        elapsed = re.search(r"Total elapsed time \(seconds\)\s*=\s*([\d.]+)", adc_log)
        observation["elapsed_at_DECK_PARSED_s"] = float(elapsed[1]) if elapsed else None
    singular = re.search(r"singular matrix:\s*check node\s+(\S+)", adc_log)
    if singular:
        name = singular[1].removeprefix("xadc.")
        netlist = base/"adc_top.dc_recovery.spice"
        if not netlist.is_file():
            netlist = base/"adc_top.equivalent_r.spice"
        cards = []
        for line in netlist.read_text(encoding="utf-8").splitlines():
            f = line.split()
            if f and f[0][0].upper() in "RCX" and name in f[1:]:
                cards.append(line)
        observation["singular_node"] = {"name": name, "cards": cards,
            "only_capacitor_connections": bool(cards) and all(c[0].upper() == "C" for c in cards)}
    return observation


def audit(folder):
    folder = Path(folder).resolve()
    index = json.loads((folder/"export.json").read_text(encoding="utf-8"))
    tag = index["tag"]
    common.tag_ok(tag)
    archive = folder/Path(index["archive"]["path"]).name
    if common._sha(archive) != index["archive"]["sha256"]:
        raise ValueError("download archive differs from the export manifest")
    with ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError("download archive CRC failure")
        for item in index["files"]:
            path = common._verified(folder, item)
            if sha256(z.read(item["path"])).hexdigest() != item["sha256"]:
                raise ValueError(f"archive payload differs: {path}")
    summary = json.loads((folder/"summary.json").read_text(encoding="utf-8"))
    tags = summary.get("child_tags", {"acquisition": tag+"_front", "core": tag+"_core",
        "adc": tag+"_adc", "adc_drc": tag+"_adcdrc", "fanout": tag+"_fanout"})
    report = {"format": "automx-cim-readout-closure-copy-review-v1", "tag": tag,
        "integrity": {"archive_sha256": common._sha(archive), "verified_payload_files": len(index["files"]),
                      "archive_crc": "PASS", "archive_and_mirror_hashes": "PASS"},
        "source_status": summary["status"], "branches": {}}
    mirrors = []
    for child_index in sorted(folder.parent.glob(tag+"_*/export.json")):
        child = child_index.parent
        ci = json.loads(child_index.read_text(encoding="utf-8"))
        ca = child/Path(ci["archive"]["path"]).name
        assert common._sha(ca) == ci["archive"]["sha256"]
        with ZipFile(ca) as z:
            assert z.testzip() is None
            for item in ci["files"]:
                common._verified(child, item)
                assert sha256(z.read(item["path"])).hexdigest() == item["sha256"]
                parent_item = folder/item["path"]
                if parent_item.is_file():
                    assert common._sha(parent_item) == item["sha256"]
        mirrors.append({"folder": child.name, "verified_files": len(ci["files"]), "archive_and_parent": "PASS"})
    report["integrity"]["child_mirrors"] = mirrors
    checked_front = front.verify_physical_source(folder, tags["acquisition"])
    report["branches"]["front"] = checked_front["physical_gate"]
    build = folder/common.BUILD/tags["core"]
    result = summary["branches"]["core"]
    lvs = build/"lvs_extract"/(core.CELL+".lvs.spice")
    devices = {k: core.acq.stage5._spice_device_count(lvs, core.CELL, p) for k, p in
        (("nfet", "sky130_fd_pr__nfet_01v8"), ("pfet", "sky130_fd_pr__pfet_01v8"),
         ("mim3", "sky130_fd_pr__cap_mim_m3_1"))}
    nlog = (build/"lvs/netgen.log").read_text(encoding="utf-8", errors="replace")
    assert core.acq.fet_lvs._netgen_match(nlog)
    assert devices == {"nfet": 138, "pfet": 18, "mim3": 168}
    assert not list(ET.parse(build/"klayout/klayout.xml").getroot().iter("item"))
    logbase = folder/common.BASE/tags["core"]
    assert re.search(r"(?m)^AUTOMX_COMPOSITE_DRC=0\s*$", (logbase/"layout.log").read_text())
    assert re.search(r"(?m)^AUTOMX_COMPOSITE_GDS_DRC=0\s*$", (logbase/"lvs_extract.log").read_text())
    pex = build/"pex"/(core.CELL+".raw.spice")
    rc = core.acq._rc_audit(pex)
    assert rc["nonzero_resistors"] > 0 and not rc["unreferenced_capacitive_nodes"]
    parsed = []
    for raw in sorted(build.glob("tt_*/core.raw")):
        name = raw.parent.name
        case = name.removeprefix("tt_").rsplit("_", 1)[0]
        step = json.loads((logbase/(name+".step.json")).read_text())
        assert step["returncode"] == 0
        for item in step["artifacts"]:
            common._verified(folder, item)
        log = (logbase/(name+".log")).read_text()
        assert "AUTOMX_CORE_PHASE=RAW_WRITTEN" in log
        vectors = waves.read_raw(raw)
        measurements = core.analyze(log, case)
        agreement = core.scalar_waveform_agreement(measurements["raw_measurements"], vectors)
        parsed.append({"case": case, "variant": name.rsplit("_", 1)[1],
            "points": len(vectors["time"]), "variables": len(vectors),
            "raw_sha256": common._sha(raw), "measurements": measurements, "scalar_waveform_agreement": agreement,
            "waveform": core.analyze_waveform(vectors)})
    report["branches"]["core"] = {"physical_gate": result["physical_gate"], "devices": devices,
        "parasitics": core.acq.precharge_pex._parasitic_counts(pex), "ground_rc": rc,
        "original_report_completed_sims": result["completed_sims"],
        "revalidated_completed_sims": len(parsed), "planned_sims": 6, "jobs": parsed}
    pex_jobs = [j for j in parsed if j["variant"] == "pex"]
    if pex_jobs:
        report["branches"]["core"]["revalidated_pilot"] = {
            "maximum_capture_error_v": max(j["measurements"]["maximum_capture_error_v"] for j in pex_jobs),
            "maximum_expected_zero_held_abs_v": max(j["measurements"]["maximum_expected_zero_held_abs_v"] for j in pex_jobs),
            "maximum_quiet_retention_drift_v": max(j["waveform"]["slow_adc_retention"]["maximum_differential_drift_v"] for j in pex_jobs),
            "held_node_range_v": [min(j["measurements"]["held_node_range_v"][0] for j in pex_jobs),
                                  max(j["measurements"]["held_node_range_v"][1] for j in pex_jobs)],
            "scope": "three selected TT PEX cases; matching first-control-run scalar/raw; ADC loading/PVT/holdout not covered"}
    abuild = folder/common.BUILD/tags["adc_drc"]
    alog = (folder/common.BASE/tags["adc_drc"]/"magic_drc.log").read_text()
    assert re.search(r"(?m)^AUTOMX_ADC_NATIVE_DRC=0\s*$", alog)
    assert not list(ET.parse(abuild/"klayout/klayout.xml").getroot().iter("item"))
    report["branches"]["adc_drc"] = {"status": "ADC_NATIVE_GDS_DRC_PASS_ONLY", "magic": 0, "klayout": 0}
    report["branches"]["adc"] = _adc_observation(folder, tags["adc"], summary["branches"]["adc"])
    run = folder/"openlane/automx_cim_core_bound_demo/runs"/tags["fanout"]
    with (run/"reports/metrics.csv").open(newline="", encoding="utf-8") as stream:
        metrics = next(csv.DictReader(stream))
    sta, reasons = clean._sta_reasons(run)
    gds = run/"results/final/gds/automx_cim_core_bound_demo.gds"
    if not gds.is_file():
        errors = []
        for path in sorted((run/"logs").rglob("*.log")):
            for line in path.read_text(errors="replace").splitlines():
                if re.match(r"\[ERROR\s+[A-Z]+-\d+\]", line):
                    errors.append({"path": path.relative_to(folder).as_posix(), "message": line})
        report["branches"]["fanout"] = {"status": "FLOW_FAILED_BEFORE_FINAL_CHECKS",
            "metrics": {k: metrics[k] for k in ("flow_status", *clean.ZERO_METRICS)},
            "metric_minus_one_meaning": "NOT_MEASURED", "tool_errors": errors,
            "sta": sta, "sta_reasons": reasons, "gds_sha256": None}
        report["not_signoff"] = "core/front and native ADC GDS DRC only; full ADC transient and final core-bound checks not completed"
        return report
    verilog = (run/"results/final/verilog/gl/automx_cim_core_bound_demo.v").read_text()
    connections = []
    for primitive, instance, ports in re.findall(r"(?ms)^\s*(sky130_\w+)\s+(\S+)\s*\((.*?)\);", verilog):
        for port, net in re.findall(r"\.(\w+)\(([^()]*)\)", ports):
            if net.strip() == "AUTOMX_FO_1_Y":
                connections.append({"primitive": primitive, "instance": instance, "port": port})
    diodes = [p for p in connections if "__diode_" in p["primitive"]]
    logic = [p for p in connections if p["instance"] != "AUTOMX_FO_1" and p not in diodes]
    gds = run/"results/final/gds/automx_cim_core_bound_demo.gds"
    graph = core.acq.fet_lvs.leaves._gds_hierarchy(gds)
    from scripts.run_stage8_core_bound_demo import _gds_reaches
    assert _gds_reaches(graph, "automx_cim_core_bound_demo", "automx_ternary_cim_4x4_core")
    antenna, antenna_reasons = clean._arc_reasons(run)
    endpoints = []
    for path in sorted((run/"reports/signoff").glob("*-antenna_violators.rpt")):
        for partial, required, area, net, pin, layer in re.findall(
                r"Partial/Required:\s*([\d.]+), Required:\s*([\d.]+), Partial:\s*([\d.]+), "
                r"Net:\s*(\S+), Pin:\s*(\S+), Layer:\s*(\S+)", path.read_text()):
            endpoints.append({"pin": pin, "net": net, "layer": layer,
                "partial_ratio": float(area), "required_ratio": float(required),
                "partial_over_required_rounded": float(partial),
                "report": path.relative_to(folder).as_posix(), "report_sha256": common._sha(path)})
    report["branches"]["fanout"] = {"metrics": {k: metrics[k] for k in ("flow_status", *clean.ZERO_METRICS)},
        "sta": sta, "sta_reasons": reasons, "antenna": antenna, "antenna_reasons": antenna_reasons,
        "antenna_endpoints": endpoints,
        "gds_sha256": common._sha(gds),
        "CIM_reachable": True, "witness_net": "AUTOMX_FO_1_Y", "logic_sinks": len(logic),
        "antenna_diode_sinks": len(diodes), "connections": connections,
        "witness_description": "final net terminals, including inserted antenna diode loads"}
    report["not_signoff"] = "intermediate core/front/native-ADC DRC; complete readout, ADC conversion, operating point, LIB/SPEF/STA and Stage6/8 remain pending"
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    p.add_argument("--report", type=Path)
    a = p.parse_args()
    result = audit(a.folder)
    if a.report:
        common._save(a.report, result)
    print(json.dumps({"tag": result["tag"], "integrity": result["integrity"],
        "core_revalidated_sims": result["branches"]["core"]["revalidated_completed_sims"],
        "ADC": result["branches"]["adc"]["status"], "fanout": result["branches"]["fanout"]["sta"]}, indent=2))

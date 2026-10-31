#!/usr/bin/env python3
"""Build the four-column physical acquisition front end from verified leaves.

Runs on the prepared Linux EDA host. GDS/LEF, independent GDS DRC/LVS,
distributed RC extraction and a small driven-bitline transient are separate
gates. This front end has no ADC, core or clocked wrapper abstraction yet.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.physical import stage5
from automx_cim.spice import parse_measurements
from scripts import export_flow2_server_results as exporter
from scripts import run_flow2_precharge_leaf_layout as precharge
from scripts import run_flow2_precharge_leaf_pex as precharge_pex
from scripts import run_flow2_hold_cap_pex as cap_pex
from scripts import run_flow2_sample_switch_fet_lvs as fet_lvs
from scripts.run_flow2_remaining_measurements import _sha, _save

CELL = "automx_cim_acquisition_4col_proto"
FORMAT = "automx-cim-flow2-acquisition-layout-v1"
RECIPE = Path("physical/sky130/wrapper_prototype/assemble_acquisition.tcl")
BASE = Path("results/sky130/flow2_periphery_leaf")
PINS = tuple([f"BL{pol}{c}" for c in range(4) for pol in ("P", "N")]
             + [f"H{pol}{c}" for c in range(4) for pol in ("P", "N")]
             + ["PRE_B", "TRACK", "VPWR", "VGND", "TRACK_B", "TRACK_N"])


def circuit() -> list[dict]:
    """Explicit physical netlist: 28 MOS, eight MIMs, two CMOS inverters."""
    devices = []
    for c in range(4):
        for pol in ("P", "N"):
            bl, held = f"BL{pol}{c}", f"H{pol}{c}"
            for suffix, kind, nets in (
                ("PRE", "pre", [bl, "PRE_B", "VPWR", "VPWR"]),
                ("SN", "nfet", [bl, "TRACK_N", held, "VGND"]),
                ("SP", "pfet", [bl, "TRACK_B", held, "VPWR"]),
                ("CH", "cap", [held, "VGND"]),
            ):
                devices.append({"name": f"{suffix}_{pol}{c}", "kind": kind,
                                "nets": nets})
    for index, gate, drain in ((1, "TRACK", "TRACK_B"),
                               (2, "TRACK_B", "TRACK_N")):
        devices += [
            {"name": f"DRV{index}_N", "kind": "nfet",
             "nets": [drain, gate, "VGND", "VGND"]},
            {"name": f"DRV{index}_P", "kind": "pfet",
             "nets": [drain, gate, "VPWR", "VPWR"]},
        ]
    return devices


def reference_spice() -> str:
    lines = ["* Physical acquisition prototype; no ideal hold capacitors.",
             f".subckt {CELL} {' '.join(PINS)}"]
    for d in circuit():
        if d["kind"] == "cap":
            primitive, params = "sky130_fd_pr__cap_mim_m3_1", "W=4.2 L=4.2"
        else:
            kind = "pfet" if d["kind"] == "pre" else d["kind"]
            primitive = f"sky130_fd_pr__{kind}_01v8"
            params = f"W={1.68 if d['kind'] == 'pre' else 3.36} L=0.15"
        lines.append(f"X{d['name']} {' '.join(d['nets'])} {primitive} {params}")
    return "\n".join([*lines, f".ends {CELL}", ""])


def _item(root: Path, path: Path) -> dict:
    return {"path": path.relative_to(root).as_posix(), "sha256": _sha(path)}


def _call(function, *args):
    """Keep partial tool output available for the normal log writer on timeout."""
    try:
        return function(*args)
    except subprocess.TimeoutExpired as error:
        def text(value):
            return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""
        return subprocess.CompletedProcess(error.cmd, 124, text(error.stdout),
            text(error.stderr) + f"\nTIMEOUT after {error.timeout}s\n")


def drc_details(text: str) -> dict:
    """Keep the original Magic rules/coordinates in a portable JSON receipt.

    Coordinates are preserved verbatim because their units come from Magic's
    technology/grid, not from the Python runner. Missing output is not zero.
    """
    counts = re.findall(r"(?m)^AUTOMX_ACQUISITION_DRC=(\d+)\s*$", text)
    rules = []
    for line in text.splitlines():
        rule = re.fullmatch(r"AUTOMX_ACQUISITION_RULE=(.*) COUNT=(\d+)", line.strip())
        if rule:
            rules.append({"rule": rule[1], "count": int(rule[2]), "boxes": []})
        elif line.startswith("AUTOMX_ACQUISITION_DRC_BOX=") and rules:
            rules[-1]["boxes"].append(line.split("=", 1)[1].strip())
    return {"count": int(counts[0]) if len(counts) == 1 else None,
            "rules": rules, "coordinate_units": "verbatim Magic log units"}


def _verified(root: Path, item: dict) -> Path:
    path = (root / item["path"]).resolve()
    if not path.is_relative_to(root) or not path.is_file() or _sha(path) != item["sha256"]:
        raise ValueError(f"changed source artifact: {path}")
    return path


def _sources(root: Path, fet_tag: str, pre_tag: str, cap_tag: str) -> tuple[dict, dict]:
    layout, layout_path = fet_lvs._verified_layout(root, fet_tag)
    lvs_path = root / BASE / fet_tag / "sample_fet_lvs.json"
    receipt = json.loads(lvs_path.read_text(encoding="utf-8"))
    if (receipt.get("status") != "LVS_PASS_SAMPLE_FET_LEAVES_ONLY" or
            receipt.get("layout_receipt_sha256") != _sha(layout_path) or
            receipt.get("script_sha256") != _sha(Path(fet_lvs.__file__)) or
            set(receipt.get("leaves", {})) != {"nfet", "pfet"}):
        raise ValueError("matching sampler FET LVS evidence is required")
    for kind in ("nfet", "pfet"):
        entry = receipt["leaves"][kind]
        if entry.get("netgen_match") is not True or entry.get("netgen_returncode") != 0:
            raise ValueError(f"{kind} leaf LVS is not a match")
        for field in ("reference", "extracted", "extract_log", "netgen_log"):
            _verified(root, entry[field])
    pre_gds, pre_receipt, pre_audit = precharge_pex._source(root, pre_tag)
    cap_gds, cap_receipt, cap_audit = cap_pex._source(root, cap_tag)
    techs = {layout["magic_technology_sha256"],
             pre_audit["magic_technology_sha256"], cap_audit["magic_technology_sha256"]}
    if len(techs) != 1:
        raise ValueError("physical leaves use different Magic technologies")
    views = {kind: {"cell": layout["leaves"][kind]["cell"],
                    "gds": _verified(root, layout["leaves"][kind]["gds"])}
             for kind in ("nfet", "pfet")}
    views["pre"] = {"cell": precharge.CELL, "gds": pre_gds}
    views["cap"] = {"cell": cap_pex.leaf.CELL, "gds": cap_gds}
    return views, {"fet_layout": _item(root, layout_path),
                   "fet_lvs": _item(root, lvs_path),
                   "precharge_lvs": _item(root, pre_receipt),
                   "cap_lvs": _item(root, cap_receipt),
                   "magic_technology_sha256": techs.pop()}


def _layout_tcl(root: Path, views: dict) -> str:
    lines = [f"set CELL {CELL}", f"set PINS {{{' '.join(PINS)}}}"]
    for kind, view in views.items():
        path = view["gds"].as_posix()
        if any(c in path for c in "{}\n\r"):
            raise ValueError("unsupported GDS path characters")
        lines += [f"set source_cell({kind}) {view['cell']}",
                  f"set source_gds({kind}) {{{path}}}"]
    lines.append("set components {")
    for d in circuit():
        lines.append(f"  {{{d['name']} {d['kind']} {{{' '.join(d['nets'])}}}}}")
    lines += ["}", (root / RECIPE).read_text(encoding="utf-8")]
    return "\n".join(lines)


def _canonical(raw: Path, target: Path) -> None:
    actual = stage5.parse_spice_subckt_pins(raw, CELL)
    if len(actual) != len(PINS) or set(actual) != set(PINS):
        raise ValueError(f"acquisition SPICE port contract differs: {actual}")
    source = raw.read_text(encoding="utf-8")
    source, n = re.subn(rf"(?im)^(\s*\.subckt\s+){CELL}(?=\s)",
                         rf"\g<1>{CELL}_raw", source, count=1)
    if n != 1:
        raise ValueError("missing acquisition SPICE header")
    source = re.sub(rf"(?im)^(\s*\.ends\s+){CELL}(?=\s|$)",
                    rf"\g<1>{CELL}_raw", source)
    source = re.sub(r"(?im)^\s*\.end\s*$", "", source)
    target.write_text(source.rstrip() + f"\n.subckt {CELL}_pex {' '.join(PINS)}\n"
                      + f"XRAW {' '.join(actual)} {CELL}_raw\n.ends {CELL}_pex\n",
                      encoding="utf-8")


def _rc_audit(path: Path) -> dict:
    """Reject C-only substrate islands and zero-R-only extraction results."""
    parent, anchored, capacitive = {}, set(PINS) | {"0"}, set()
    nonzero = 0

    def find(node):
        parent.setdefault(node, node)
        if parent[node] != node:
            parent[node] = find(parent[node])
        return parent[node]

    logical = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("+") and logical:
            logical[-1] += " " + line.lstrip()[1:].strip()
        else:
            logical.append(line)
    for raw in logical:
        f = raw.split()
        if len(f) < 4 or raw.lstrip().startswith(("*", ".", "+")):
            continue
        if f[0][0].lower() == "r":
            parent[find(f[1])] = find(f[2])
            number = re.fullmatch(r"([+-]?[\d.]+(?:[eE][+-]?\d+)?)([A-Za-z]*)", f[3])
            if number and float(number[1]) > 0:
                nonzero += 1
        elif f[0][0].lower() == "c":
            capacitive.update(f[1:3])
        elif f[0][0].lower() in ("x", "m"):
            positional = [v for v in f[1:] if "=" not in v]
            if positional and positional[-1].lower() in (
                    "sky130_fd_pr__nfet_01v8", "sky130_fd_pr__pfet_01v8"):
                anchored.update(positional[:4])
    good = {find(node) for node in anchored}
    floating = sorted(node for node in capacitive if find(node) not in good)
    return {"nonzero_resistors": nonzero, "unreferenced_capacitive_nodes": floating}


CORNERS = {"tt": (1.8, 25), "ss": (1.62, 85), "ff": (1.98, -40)}
INPUT_DIFFERENTIALS = (0.0, 0.002, 0.05, -0.10)
POST_SAMPLE_NS = 8.0
LATE_SAMPLE_NS = 12.0
RAW_MEASURES = tuple(f"{name}{pol}{c}" for c in range(4)
    for name in ("bl", "pre", "post", "late") for pol in ("p", "n")) + (
    "t_n_off", "t_p_off", "ctrl_p_post", "ctrl_n_post", "ctrl_p_late", "ctrl_n_late")
MEASURES = tuple([f"{name}{c}" for c in range(4)
                  for name in ("bl", "pre", "post", "late")] + ["t_n_off", "t_p_off"])


def _capture_deck(model: Path, netlist: Path, extracted: bool, corner: str) -> str:
    # Driven bitlines isolate acquisition/driver effects before the passive
    # core and ADC load are included. Held outputs have only physical MIM caps.
    cell = CELL + ("_pex" if extracted else "")
    vdd, temp = CORNERS[corner]
    ports = ["0" if p == "VGND" else p for p in PINS]
    lines = [f".title acquisition {corner} {'pex' if extracted else 'schematic'}",
             f'.lib "{model.as_posix()}" {corner}', f'.include "{netlist.as_posix()}"',
             f".temp {temp}", ".option method=gear reltol=1e-4 abstol=1e-13",
             f"VVDD VPWR 0 {vdd}",
             f"VPRE PRE_B 0 PWL(0 0 1n 0 1.05n {vdd} {LATE_SAMPLE_NS:g}n {vdd})",
             f"VTRACK TRACK 0 PWL(0 {vdd} 4n {vdd} 4.05n 0 {LATE_SAMPLE_NS:g}n 0)",
             f"XAFE {' '.join(ports)} {cell}"]
    for c in range(4):
        # Include zero, small signed differential and opposite polarity.
        delta = INPUT_DIFFERENTIALS[c]
        for pol, sign in (("P", -1), ("N", 1)):
            node = f"BL{pol}{c}"
            end = 0.90 * vdd + sign * delta / 2
            lines += [f"V{node} {node} 0 PWL(0 {vdd} 1.1n {vdd} 2.5n {end} {LATE_SAMPLE_NS:g}n {end})"]
        # ngspice 31 FIND rejects the two-node V(n,p) vector yet may print a
        # zero result and return 0. Measure scalar node voltages, subtract in
        # Python, and verify the known nonzero input stimulus independently.
        for name, prefix, at in (("bl", "BL", 3.95), ("pre", "H", 3.95),
                                 ("post", "H", POST_SAMPLE_NS), ("late", "H", LATE_SAMPLE_NS)):
            for pol in ("P", "N"):
                lines.append(f".measure tran {name}{pol.lower()}{c} FIND V({prefix}{pol}{c}) AT={at:g}n")
    lines += [f".measure tran t_n_off WHEN V(TRACK_N)={vdd / 2} FALL=1",
              f".measure tran t_p_off WHEN V(TRACK_B)={vdd / 2} RISE=1"]
    for name, at in (("post", POST_SAMPLE_NS), ("late", LATE_SAMPLE_NS)):
        for pol, node in (("p", "TRACK_B"), ("n", "TRACK_N")):
            lines.append(f".measure tran ctrl_{pol}_{name} FIND V({node}) AT={at:g}n")
    lines += [f".tran 5p {LATE_SAMPLE_NS:g}n", ".end", ""]
    return "\n".join(lines)


def _analyze_capture_log(text: str, corner: str) -> dict:
    errors = re.findall(r"(?im)^\s*(?:error\b[^\n]*|fatal\b[^\n]*)", text)
    if errors:
        raise ValueError(f"ngspice log error: {errors[0].strip()}")
    raw = parse_measurements(text, RAW_MEASURES)
    missing = set(RAW_MEASURES) - set(raw)
    if missing or not all(math.isfinite(v) for v in raw.values()):
        raise ValueError(f"missing/nonfinite scalar measurements: {sorted(missing)}")
    vdd = CORNERS[corner][0]
    for c, delta in enumerate(INPUT_DIFFERENTIALS):
        for pol, sign in (("p", -1), ("n", 1)):
            expected = 0.90 * vdd + sign * delta / 2
            if abs(raw[f"bl{pol}{c}"] - expected) > 1e-5:
                raise ValueError(f"driven input voltage differs: bl{pol}{c}")
    # The _03 PEX control half-rail crossings reach 5.873 ns at SS, so its
    # old 4.5 ns 'post' measurement preceded turnoff. Observe after 8 ns and
    # require the actual P/N driver voltages to be in their off-state rails.
    for key in ("t_n_off", "t_p_off"):
        if not 4e-9 <= raw[key] < POST_SAMPLE_NS * 1e-9:
            raise ValueError(f"physical control turnoff not complete before post sample: {key}")
    for at in ("post", "late"):
        if not (0.9 * vdd <= raw[f"ctrl_p_{at}"] <= 1.1 * vdd and
                -0.1 * vdd <= raw[f"ctrl_n_{at}"] <= 0.1 * vdd):
            raise ValueError(f"TG controls are not off at {at} sample")
    values = {f"{name}{c}": raw[f"{name}n{c}"] - raw[f"{name}p{c}"]
              for c in range(4) for name in ("bl", "pre", "post", "late")}
    values.update({key: raw[key] for key in ("t_n_off", "t_p_off")})
    return {"raw_measurements": raw, "measurements": values,
            "maximum_capture_error_v": max(abs(values[f"post{c}"] - values[f"bl{c}"]) for c in range(4)),
            "maximum_hold_drift_v": max(abs(values[f"late{c}"] - values[f"post{c}"]) for c in range(4)),
            "maximum_pre_turnoff_tracking_error_v": max(abs(values[f"pre{c}"] - values[f"bl{c}"]) for c in range(4)),
            "physical_control_skew_s": raw["t_n_off"] - raw["t_p_off"],
            "post_sample_ns": POST_SAMPLE_NS, "late_sample_ns": LATE_SAMPLE_NS,
            "known_input_stimulus_verified": True, "controls_off_at_hold_samples": True}


def run(root: str | Path, *, pdk_root: str | Path, tag: str,
        fet_tag: str = "sample_fet_20261017_03",
        pre_tag: str = "precharge_leaf_guarded_20261017_03",
        cap_tag: str = "hold_cap_mim3_20261017_02", execute: bool = False,
        timeout_s: int = 900) -> dict:
    root = Path(root).resolve()
    if not all(precharge.TAG_RE.fullmatch(s) for s in (tag, fet_tag, pre_tag, cap_tag)) or timeout_s <= 0:
        raise ValueError("invalid run tag or timeout")
    folder = root / BASE / tag
    build = root / "build/flow2_periphery_leaf" / tag
    physical = root / "physical/sky130/wrapper_prototype/leaf_cells" / tag
    saved_path = folder / "summary.json"
    report = {"format": FORMAT, "tag": tag, "status": "READY_TO_RUN",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "four-column physical precharge/TG/MIM/CMOS-driver acquisition front end",
              "expected_devices": {"nfet": 10, "pfet": 18, "mim3": 8},
              "script_sha256": _sha(Path(__file__)), "recipe_sha256": _sha(root / RECIPE),
              "remaining_wrapper_blocks": ["core connection", "ADC input conditioning",
                  "sense/ADC", "references", "decoder", "clocked interface", "LIB", "SPEF", "STA"],
              "not_signoff": "acquisition front end only; no complete core/ADC wrapper, ADC transfer, fresh MHA validation or Stage-6 v2 claim"}
    history = folder / "history.log"

    def note(message: str) -> None:
        line = f"[{datetime.now(timezone.utc).isoformat()}] {message}"
        print(line, flush=True)
        with history.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")

    def magic_step(name: str, tcl: str):
        work = build / name
        work.mkdir(parents=True, exist_ok=True)
        (work / "commands.tcl").write_text(tcl, encoding="utf-8")
        result = _call(stage5._magic, magic, tech, work, tcl, timeout_s)
        log = folder / f"{name}.log"
        log.write_text(result.stdout + result.stderr, encoding="utf-8")
        report[name] = {"returncode": result.returncode, "log": _item(root, log)}
        note(f"{name}: returncode={result.returncode}")
        return result, work

    if execute:
        folder.mkdir(parents=True, exist_ok=True)
    try:
        views, source = _sources(root, fet_tag, pre_tag, cap_tag)
        pdk = precharge._pdk(root, Path(pdk_root))
        tech, setup = pdk / "libs.tech/magic/sky130A.tech", pdk / "libs.tech/netgen/sky130A_setup.tcl"
        model = pdk / "libs.tech/ngspice/sky130.lib.spice"
        tools = {name: stage5._find_tool(name) for name in ("magic", "netgen", "klayout", "ngspice")}
        magic = tools["magic"]
        if not all(tools.values()) or not setup.is_file() or _sha(tech) != source["magic_technology_sha256"]:
            raise ValueError("matching SKY130 technology, Netgen setup and all four EDA tools required")
        report["sources"] = source
        report["source_gds"] = {key: _item(root, value["gds"]) for key, value in views.items()}
        report["netgen_setup_sha256"] = _sha(setup)
        report["model_sha256"] = _sha(model)
        if not execute:
            return report
        if saved_path.is_file():
            saved = json.loads(saved_path.read_text(encoding="utf-8"))
            for key in ("format", "tag", "sources", "source_gds", "script_sha256", "recipe_sha256", "netgen_setup_sha256", "model_sha256"):
                if saved.get(key) != report[key]:
                    raise FileExistsError("acquisition inputs changed; use a new tag")
            if saved.get("status") == "ACQUISITION_DRC_LVS_RC_PEX_MEASURED_PROTOTYPE":
                for item in saved["artifacts"]:
                    _verified(root, item)
                note("REUSE completed acquisition run; no EDA rerun")
                report = saved
                return report
            raise FileExistsError("existing blocked run retained; inspect its logs and use a new tag")
        if build.exists() and any(build.iterdir()):
            raise FileExistsError("interrupted acquisition build retained; use a new tag")
        note("START acquisition layout, DRC, transistor LVS, distributed RC and six transient jobs")
        result, work = magic_step("layout", _layout_tcl(root, views))
        report["magic_drc_details"] = drc_details(result.stdout + result.stderr)
        report["magic_drc_violations"] = report["magic_drc_details"]["count"]
        if result.returncode or report["magic_drc_violations"] != 0 or "AUTOMX_ACQUISITION_DONE" not in result.stdout:
            raise RuntimeError("BLOCKED_ACQUISITION_MAGIC_DRC_OR_LAYOUT")
        gds, lef = work / f"{CELL}.gds", work / f"{CELL}.lef"
        lef_text = lef.read_text(encoding="utf-8")
        if set(re.findall(r"(?m)^\s*PIN\s+(\S+)\s*$", lef_text)) != set(PINS):
            raise RuntimeError("BLOCKED_ACQUISITION_LEF_PORTS")
        if CELL not in fet_lvs.leaves._gds_hierarchy(gds):
            raise RuntimeError("BLOCKED_ACQUISITION_GDS_STRUCTURE")
        deck = stage5._klayout_deck(pdk)
        xml = folder / "klayout.xml"
        kr = _call(stage5._run, [tools["klayout"], "-b", "-r", str(deck), "-rd", f"input={gds}", "-rd", f"report={xml}"], work, timeout_s)
        (folder / "klayout.log").write_text(kr.stdout + kr.stderr, encoding="utf-8")
        xml_root = ET.parse(xml).getroot() if xml.is_file() else None
        report["klayout_drc_violations"] = (sum(1 for _ in xml_root.iter("item"))
                                            if xml_root is not None and xml_root.tag == "report-database" else None)
        report["klayout_deck_sha256"] = _sha(deck)
        if kr.returncode or report["klayout_drc_violations"] != 0:
            raise RuntimeError("BLOCKED_ACQUISITION_KLAYOUT_DRC")
        extract = (f"crashbackups stop\ngds read {{{gds.as_posix()}}}\nload {CELL}\nselect top cell\n"
                   f"box -5um -5um {len(circuit()) * 20 + 25}um 85um\n"
                   "drc on\ndrc check\ndrc catchup\n"
                   'puts "AUTOMX_ACQUISITION_GDS_DRC=[drc list count total]"\n'
                   'foreach {rule areas} [drc listall why] {puts "GDS_DRC_RULE=$rule BOXES=$areas"}\n'
                   "extract do local\nextract all\next2spice lvs\next2spice scale off\n"
                   "ext2spice subcircuit on\next2spice subcircuit top on\n"
                   f"ext2spice -o {CELL}.lvs.spice\nputs AUTOMX_ACQUISITION_LVS_DONE\nquit -noprompt\n")
        er, ework = magic_step("lvs_extract", extract)
        extracted = ework / f"{CELL}.lvs.spice"
        reference = ework / f"{CELL}.reference.spice"
        reference.write_text(reference_spice(), encoding="utf-8")
        gds_counts = re.findall(r"(?m)^AUTOMX_ACQUISITION_GDS_DRC=(\d+)\s*$", er.stdout + er.stderr)
        report["magic_gds_drc_violations"] = int(gds_counts[0]) if len(gds_counts) == 1 else None
        if report["magic_gds_drc_violations"] != 0:
            raise RuntimeError("BLOCKED_ACQUISITION_GDS_DRC")
        if (er.returncode or "AUTOMX_ACQUISITION_LVS_DONE" not in er.stdout + er.stderr or
                not extracted.is_file() or set(stage5.parse_spice_subckt_pins(extracted, CELL)) != set(PINS)):
            raise RuntimeError("BLOCKED_ACQUISITION_EXTRACTED_PORTS")
        report["extracted_devices"] = {kind: stage5._spice_device_count(extracted, CELL, primitive)
            for kind, primitive in (("nfet", "sky130_fd_pr__nfet_01v8"),
                ("pfet", "sky130_fd_pr__pfet_01v8"), ("mim3", "sky130_fd_pr__cap_mim_m3_1"))}
        if report["extracted_devices"] != report["expected_devices"]:
            raise RuntimeError("BLOCKED_ACQUISITION_DEVICE_COUNTS")
        nlog = folder / "netgen.log"
        nr = _call(stage5._run, [tools["netgen"], "-batch", "lvs", f"{extracted} {CELL}",
                          f"{reference} {CELL}", str(setup), str(nlog)], ework, timeout_s)
        if not nlog.is_file():
            nlog.write_text(nr.stdout + nr.stderr, encoding="utf-8")
        report["transistor_lvs_match"] = nr.returncode == 0 and fet_lvs._netgen_match(nlog.read_text(encoding="utf-8", errors="replace"))
        if not report["transistor_lvs_match"]:
            raise RuntimeError("BLOCKED_ACQUISITION_TRANSISTOR_LVS")
        pex_tcl = (f"crashbackups stop\ngds read {{{gds.as_posix()}}}\nload {CELL}\nselect top cell\n"
                   "extract do local\nextract do resistance\nextract all\n"
                   "ext2sim labels on\next2sim\nextresist tolerance 10\nextresist all\n"
                   "ext2spice lvs\next2spice scale off\next2spice cthresh 0.01\n"
                   "ext2spice extresist on\next2spice short resistor\n"
                   "ext2spice subcircuit on\next2spice subcircuit top on\n"
                   f"ext2spice -o {CELL}.pex.raw.spice\nputs AUTOMX_ACQUISITION_PEX_DONE\nquit -noprompt\n")
        pr, pwork = magic_step("pex", pex_tcl)
        raw, canonical = pwork / f"{CELL}.pex.raw.spice", pwork / f"{CELL}.pex.spice"
        if pr.returncode or "AUTOMX_ACQUISITION_PEX_DONE" not in pr.stdout + pr.stderr or not raw.is_file():
            raise RuntimeError("BLOCKED_ACQUISITION_RC_EXTRACTION")
        _canonical(raw, canonical)
        report["parasitics"] = precharge_pex._parasitic_counts(raw)
        report["substrate_rc_audit"] = _rc_audit(raw)
        if not report["substrate_rc_audit"]["nonzero_resistors"] or not report["parasitics"]["capacitors"]:
            raise RuntimeError("BLOCKED_ACQUISITION_NO_DISTRIBUTED_RC")
        if report["substrate_rc_audit"]["unreferenced_capacitive_nodes"]:
            raise RuntimeError("BLOCKED_ACQUISITION_FLOATING_SUBSTRATE_RC_NODE")
        physical.mkdir(parents=True, exist_ok=True)
        for path in (gds, lef, canonical, reference):
            shutil.copy2(path, physical / path.name)
        report["jobs"] = []
        sim = build / "transient"
        sim.mkdir()
        for corner in ("tt", "ss", "ff"):
            for variant, netlist in (("schematic", reference), ("pex", canonical)):
                spice = sim / f"{corner}_{variant}.spice"
                spice.write_text(_capture_deck(model, netlist, variant == "pex", corner), encoding="utf-8")
                log = folder / f"{corner}_{variant}.log"
                sr = _call(stage5._run, [tools["ngspice"], "-b", str(spice)], sim, timeout_s)
                log.write_text(sr.stdout + sr.stderr, encoding="utf-8")
                entry = {"corner": corner, "variant": variant, "returncode": sr.returncode,
                         "deck": _item(root, spice), "log": _item(root, log)}
                report["jobs"].append(entry)
                if sr.returncode:
                    raise RuntimeError(f"BLOCKED_ACQUISITION_TRANSIENT_{corner}_{variant}")
                try:
                    entry.update(_analyze_capture_log(sr.stdout + sr.stderr, corner))
                except ValueError as error:
                    entry["measurement_error"] = str(error)
                    raise RuntimeError(f"BLOCKED_ACQUISITION_MEASUREMENT_{corner}_{variant}: {error}") from error
                note(f"TRANSIENT {corner}/{variant}: capture={entry['maximum_capture_error_v']:.6g} V")
        report["capture_budget_v"] = 0.0008
        report["capture_budget_met_in_driven_cases"] = all(j["maximum_capture_error_v"] <= 0.0008 for j in report["jobs"] if j["variant"] == "pex")
        report["status"] = "ACQUISITION_DRC_LVS_RC_PEX_MEASURED_PROTOTYPE"
        report["artifacts"] = [_item(root, p) for base in (build, folder, physical) for p in sorted(base.rglob("*")) if p.is_file() and p.name not in ("history.log", "summary.json")]
        note("COMPLETE acquisition prototype; ADC/core wrapper and timing abstraction remain pending")
    except FileExistsError:
        # Never replace a frozen result with an input-conflict error receipt.
        raise
    except Exception as error:
        if saved_path.is_file():
            raise FileExistsError(f"frozen acquisition result cannot be reused: {error}") from error
        report["status"] = "BLOCKED_ACQUISITION_PHYSICAL" if execute else "BLOCKED_PREREQUISITES"
        report["error"] = f"{type(error).__name__}: {error}"
        if execute:
            note(report["error"])
    finally:
        if execute:
            if sys.exc_info()[0] is None:
                _save(folder / "summary.json", report)
            exporter.export(root, tag=tag, include_measured_cap=False)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--pdk-root", type=Path, required=True)
    parser.add_argument("--tag", default="acquisition_4col_20261018_01")
    parser.add_argument("--fet-tag", default="sample_fet_20261017_03")
    parser.add_argument("--pre-tag", default="precharge_leaf_guarded_20261017_03")
    parser.add_argument("--cap-tag", default="hold_cap_mim3_20261017_02")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=900)
    args = parser.parse_args()
    output = run(args.root, pdk_root=args.pdk_root, tag=args.tag, fet_tag=args.fet_tag,
                 pre_tag=args.pre_tag, cap_tag=args.cap_tag, execute=args.run, timeout_s=args.timeout_s)
    print(json.dumps(output, indent=2))
    if args.run and output["status"] != "ACQUISITION_DRC_LVS_RC_PEX_MEASURED_PROTOTYPE":
        raise SystemExit(1)

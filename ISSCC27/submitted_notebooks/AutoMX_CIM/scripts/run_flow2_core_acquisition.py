#!/usr/bin/env python3
"""Join the measured core and acquisition GDS; check the new physical boundary.

Native SKY130 Magic/KLayout DRC, transistor LVS, distributed RC and six TT
core-driven pilot jobs. ADC, physical BL load capacitors and timing views are
subsequent gates; this pilot must not be published as the final wrapper.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import shutil
import struct
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_flow2_acquisition_layout as acq
from scripts import run_flow2_acquisition_transient_recovery as recovery
from scripts import flow2_integration_common as common
from scripts import flow2_waveforms as wavetools
from automx_cim.spice import parse_measurements

CELL = "automx_cim_core_acquisition_proto"
RECIPE = Path("physical/sky130/wrapper_prototype/assemble_core_acquisition.tcl")
SHIELDED_RECIPE = RECIPE.with_name("assemble_core_acquisition_shielded.tcl")
BANKED_RECIPE = RECIPE.with_name("assemble_core_acquisition_banked.tcl")
CORE = acq.stage5.CORE
CORE_PINS = acq.stage5.core_pins()
CONTROLS = tuple(p for p in CORE_PINS if p.startswith(("WL", "WPOS_", "WNEG_")))
PINS = (*acq.PINS, *CONTROLS)
CURRENT_CORE_PEX = "3d4425cdc7dbf590f9ef99e57ddaa1725f6c17f54354fa5145ff7e36070827e1"
EXPECTED = {"nfet": 138, "pfet": 18, "mim3": 8}


def gds_pin_centers(data: bytes, top: str, pins: tuple[str, ...]) -> dict:
    """Read only TEXT elements in the named top structure, in microns.

    Looking up VGND recursively in Magic could select a repeated leaf label
    rather than the core's large ground landing. Native GDS top labels avoid
    that ambiguity and retain the database-unit conversion from UNITS.
    """
    def real8(value):
        if len(value) != 8:
            raise ValueError("bad GDS real")
        return (-1 if value[0] & 128 else 1) * (int.from_bytes(value[1:], "big") / 2**56) * 16.0**((value[0] & 127)-64)
    k, cell, element, unit, found = 0, None, None, None, {}
    while k < len(data):
        if k+4 > len(data):
            raise ValueError("truncated GDS record")
        n, kind, _ = struct.unpack(">HBB", data[k:k+4])
        if n < 4 or n % 2 or k+n > len(data):
            raise ValueError("invalid GDS record length")
        value, k = data[k+4:k+n], k+n
        if kind == 3:  # UNITS: meters per database unit is the second REAL8.
            if len(value) != 16:
                raise ValueError("invalid GDS UNITS")
            unit = real8(value[8:]) * 1e6
        elif kind == 6:
            cell = value.rstrip(b"\0").decode("ascii")
        elif kind == 7:
            cell = None
        elif kind == 12:
            element = {}
        elif element is not None:
            if kind == 13:
                element["layer"] = struct.unpack(">h", value)[0]
            elif kind == 16:
                if len(value) != 8:
                    raise ValueError("GDS TEXT must have one origin")
                element["xy"] = struct.unpack(">ii", value)
            elif kind == 25:
                element["text"] = value.rstrip(b"\0").decode("ascii")
            elif kind == 17:
                name = element.get("text")
                if cell == top and name in pins:
                    if name in found or not unit or not 0 < unit <= 1 or "xy" not in element:
                        raise ValueError(f"ambiguous/malformed GDS top pin: {name}")
                    layer = 69 if name.startswith(("WPOS_", "WNEG_")) else 70 if top == CORE and name.startswith("BL") else 71
                    if element.get("layer") != layer:
                        raise ValueError(f"unexpected native GDS label layer: {name}")
                    found[name] = [v * unit for v in element["xy"]]
                element = None
    if set(found) != set(pins):
        raise ValueError(f"missing GDS top labels: {sorted(set(pins)-set(found))}")
    return found


def sources(root: Path, source_tag: str, pdk: Path, *, banked=False) -> dict:
    acquisition = recovery.verify_physical_source(root, source_tag)
    summary = root / "results/receipts/physical/stage5_summary.json"
    core = json.loads(summary.read_text(encoding="utf-8"))
    if core.get("status") != "PASS" or core.get("macro") != CORE:
        raise ValueError("the existing Stage-5 core summary must be PASS")
    relative = {"gds": f"physical/sky130/macro/{CORE}.gds",
                "lef": f"physical/sky130/macro/{CORE}.lef",
                "extracted_spice": f"physical/sky130/macro/{CORE}.pex.spice",
                "spice": f"generated/sky130/spice/macro/{CORE}.spice"}
    views, items = {}, [acq._item(root, summary), acq._item(root, acquisition["receipt"])]
    for key, rel in relative.items():
        item = {"path": rel, "sha256": core["views"][key]["sha256"]}
        views[key] = acq._verified(root, item)
        items.append(item)
    if core["views"]["extracted_spice"]["sha256"] != CURRENT_CORE_PEX:
        raise ValueError("use the current server core (PEX 3d4425...); do not upload the old local results")
    for name in ("preflight.json", "layout.json", "magic_drc.json", "klayout_drc.json", "netgen_lvs.json", "pex.json"):
        path = root / "results/receipts/physical" / name
        item = {"path": path.relative_to(root).as_posix(), "sha256": core["receipts"][name]}
        checked = json.loads(acq._verified(root, item).read_text(encoding="utf-8"))
        if checked.get("status") != "PASS":
            raise ValueError(f"source core gate failed: {name}")
        if name == "preflight.json":
            native_tech = Path(checked["pdk"]) / "libs.tech/magic/sky130A.tech"
            if not native_tech.is_file() or common._sha(native_tech) != common._sha(pdk / "libs.tech/magic/sky130A.tech"):
                raise ValueError("core and acquisition must use the same native Magic technology")
        items.append(item)
    tech = pdk / "libs.tech/magic/sky130A.tech"
    if common._sha(tech) != acquisition["report"]["sources"]["magic_technology_sha256"]:
        raise ValueError("use the acquisition's native SKY130 technology")
    if acq.stage5.parse_spice_subckt_pins(views["spice"], CORE) != CORE_PINS:
        raise ValueError("core schematic port order changed")
    if acq.stage5._spice_device_count(views["spice"], CORE, "sky130_fd_pr__nfet_01v8") != 128:
        raise ValueError("core schematic must contain the 128 physical NFETs")
    items.extend(acquisition["report"]["artifacts"])
    acq_gds = root / f"physical/sky130/wrapper_prototype/leaf_cells/{source_tag}/{acq.CELL}.gds"
    if acq_gds.relative_to(root).as_posix() not in {v["path"] for v in items}:
        raise ValueError("acquisition GDS is not in its verified source inventory")
    locations = {"core": gds_pin_centers(views["gds"].read_bytes(), CORE, CORE_PINS),
                 "acq": gds_pin_centers(acq_gds.read_bytes(), acq.CELL, acq.PINS)}
    # This routing recipe uses the enlarged Stage-5 ground landing, not an
    # older narrow row rail. It never edits the source macro to fabricate one.
    if any(abs(a-b) > .01 for a, b in zip(locations["core"]["VGND"], (3.8, 11.45))):
        raise ValueError("current core GDS does not expose its enlarged VGND landing")
    if banked:
        from scripts.run_flow2_banked_acquisition import pin_locations
        expected_locations = pin_locations()
    else:
        expected_locations = {pin: (1.3, 30.+2*i) for i, pin in enumerate(acq.PINS)}
    for pin in acq.PINS:
        if any(abs(a-b) > .01 for a, b in zip(locations["acq"][pin], expected_locations[pin])):
            raise ValueError("acquisition pin geometry changed; adapt the assembly routing recipe first")
    return {"core": views, "acquisition": acquisition, "acq_gds": acq_gds, "items": items, "locations": locations}


def reference_spice(core_text: str, acquisition_text: str) -> str:
    # Keep independent S/B semantics. Only the already shorted core VSUBS
    # argument maps to parent VGND; PFET bodies/sources stay on VPWR.
    texts = [re.sub(r"(?im)^\s*\.end\s*$", "", t) for t in (core_text, acquisition_text)]
    core_nodes = ["VGND" if p == "VSUBS" else p for p in CORE_PINS]
    texts += [f".subckt {CELL} {' '.join(PINS)}",
              f"XCORE {' '.join(core_nodes)} {CORE}",
              f"XACQ {' '.join(acq.PINS)} {acq.CELL}", f".ends {CELL}", ""]
    return "\n".join(texts)


def layout_tcl(root: Path, core_gds: Path, acq_gds: Path, *, locations: dict, recipe: Path = RECIPE) -> str:
    lines = [f"set CELL {CELL}", f"set PINS {{{' '.join(PINS)}}}",
             f"set bitlines {{{' '.join(acq.PINS[:8])}}}"]
    for kind, cell, gds, pins in (("core", CORE, core_gds, CORE_PINS), ("acq", acq.CELL, acq_gds, acq.PINS)):
        path = gds.as_posix()
        if any(c in path for c in "{}\n\r"):
            raise ValueError("unsupported source path")
        lines += [f"set source_gds({kind}) {{{path}}}", f"set source_cell({kind}) {cell}",
                  f"set source_pins({kind}) {{{' '.join(pins)}}}"]
        for pin in pins:
            x, y = locations[kind][pin]
            if not all(math.isfinite(v) for v in (x, y)):
                raise ValueError("nonfinite source pin coordinate")
            lines += [f"set px({kind},{pin}) {x:.9g}", f"set py({kind},{pin}) {y:.9g}"]
    return "\n".join([*lines, (root / recipe).read_text(encoding="utf-8")])


def canonical(raw: Path, target: Path):
    actual = acq.stage5.parse_spice_subckt_pins(raw, CELL)
    if len(actual) != len(PINS) or set(actual) != set(PINS):
        raise ValueError(f"composite extracted ports differ: {actual}")
    text = raw.read_text(encoding="utf-8")
    text = re.sub(rf"(?im)^(\s*\.subckt\s+){CELL}(?=\s)", rf"\g<1>{CELL}_raw", text, count=1)
    text = re.sub(rf"(?im)^(\s*\.ends\s+){CELL}(?=\s|$)", rf"\g<1>{CELL}_raw", text)
    text = re.sub(r"(?im)^\s*\.end\s*$", "", text)
    target.write_text(text.rstrip() + f"\n.subckt {CELL}_pex {' '.join(PINS)}\n"
        + f"XRAW {' '.join(actual)} {CELL}_raw\n.ends {CELL}_pex\n", encoding="utf-8")


def pilot_deck(model: Path, netlist: Path, variant: str, case: str, *, waveform=False, physical_bl_load=False,
               retention_us=0.) -> str:
    # TT only. Both row pairs are measured in separate reset simulations.
    # 800fF BL loads are explicit testbench surrogates, not physical MIM views.
    if not math.isfinite(retention_us) or retention_us < 0 or retention_us > 10:
        raise ValueError("retention diagnostic must be between zero and ten microseconds")
    acts = {"zero": (0, 0, 0, 0), "pair_a": (6, -4, 0, 0), "pair_b": (0, 0, 6, -4)}[case]
    weights = ((1, -1, 1, 0), (1, -1, -1, 0), (1, -1, 1, 0), (1, -1, -1, 0))
    nodes = ["0" if p == "VGND" else p for p in PINS]
    lines = [f".title core plus physical acquisition TT {case}/{variant}",
             f'.lib "{model.as_posix()}" tt', f'.include "{netlist.as_posix()}"',
             ".temp 25", ".option method=gear reltol=1e-4 abstol=1e-13",
             "VVDD VPWR 0 1.8", "VPRE PRE_B 0 PWL(0 0 2n 0 2.05n 1.8 16n 1.8)",
             "VTRACK TRACK 0 PWL(0 1.8 8n 1.8 8.05n 0 16n 0)",
             f"XDUT {' '.join(nodes)} {CELL + ('_pex' if variant == 'pex' else '')}"]
    for c in range(4):
        if not physical_bl_load:
            for pol in ("P", "N"):
                lines.append(f"CBL{pol}{c} BL{pol}{c} 0 800f")
        for label, node, at in (("blpre", "BL", 7.95), ("heldpre", "H", 7.95),
                                ("held", "H", 12), ("late", "H", 16)):
            for pol in ("P", "N"):
                lines.append(f".measure tran {label}{pol.lower()}{c} FIND V({node}{pol}{c}) AT={at}n")
    for r, a in enumerate(acts):
        for phase, magnitude in (("WLP", max(a, 0)), ("WLN", max(-a, 0))):
            period = f"{retention_us*1000+20:g}n" if retention_us else "20n"
            pulse = f"PULSE(0 1.8 5n 5p 5p {magnitude * 50}p {period})" if magnitude else "0"
            lines.append(f"V{phase}{r} {phase}{r} 0 {pulse}")
        for c in range(4):
            for prefix, enabled in (("WPOS", weights[r][c] > 0), ("WNEG", weights[r][c] < 0)):
                lines.append(f"V{prefix}_{r}_{c} {prefix}_{r}_{c} 0 {1.8 if enabled else 0}")
    for control in ("TRACK_B", "TRACK_N"):
        lines.append(f".measure tran {control.lower()} FIND V({control}) AT=12n")
    saved = [f"v({p})" for p in (*acq.PINS[:16], "TRACK_B", "TRACK_N")]
    if waveform:
        saved += [f"v({p})" for p in ("PRE_B", "TRACK", "VPWR", *CORE_PINS[8:16])]
    lines += [".save " + " ".join(saved), f".tran 5p {retention_us:g}u 0 1n" if retention_us else ".tran 5p 16n"]
    if waveform:
        lines.append(wavetools.control_block(saved, filename="core.raw", phase="CORE"))
    return "\n".join([*lines, ".end", ""])


def analyze_waveform(vectors):
    """Separate precharge/PWM/turnoff contributions without retuning on MHA."""
    stages = (("precharge_on", 1.9), ("precharge_released", 2.3),
              ("before_pwm", 4.9), ("after_pwm", 5.8), ("before_turnoff", 7.95),
              ("after_turnoff", 8.8), ("held", 12.), ("late", 16.))
    result = {}
    for name, ns in stages:
        values = {p: wavetools.sample(vectors, f"v({p})", ns*1e-9)
                  for p in (*acq.PINS[:16], "PRE_B", "TRACK", "TRACK_B", "TRACK_N")}
        result[name] = {"time_ns": ns,
            "bitline_differential_v": [values[f"BLN{c}"]-values[f"BLP{c}"] for c in range(4)],
            "held_differential_v": [values[f"HN{c}"]-values[f"HP{c}"] for c in range(4)],
            "control_v": {p: values[p] for p in ("PRE_B", "TRACK", "TRACK_B", "TRACK_N")}}
    def delta(after, before, key):
        return [a-b for a, b in zip(result[after][key], result[before][key])]
    report = {"stage_samples": result,
        "precharge_release_bitline_shift_v": delta("precharge_released", "precharge_on", "bitline_differential_v"),
        "pwm_window_bitline_shift_v": delta("after_pwm", "before_pwm", "bitline_differential_v"),
        "turnoff_held_shift_v": delta("after_turnoff", "before_turnoff", "held_differential_v"),
        "late_held_drift_v": delta("late", "held", "held_differential_v"),
        "interpretation": "stage differences in a loaded nonlinear circuit; attribution by time, not a proof of a unique transistor-level cause"}
    if vectors["time"][-1] >= 3.999e-6:
        retention = {}
        for ns in (1000., 3000., 4000.):
            differential = [wavetools.sample(vectors, f"v(HN{c})", ns*1e-9)-wavetools.sample(vectors, f"v(HP{c})", ns*1e-9) for c in range(4)]
            retention[f"{ns:g}ns"] = {"held_differential_v": differential,
                "drift_from_12ns_v": [a-b for a, b in zip(differential, result["held"]["held_differential_v"])]}
        report["slow_adc_retention"] = {"quiet_unloaded_hold_samples": retention,
            "maximum_differential_drift_v": max(abs(d) for v in retention.values() for d in v["drift_from_12ns_v"]),
            "scope": "physical S/H hold with quiet wordlines; ADC/input-buffer loading is not included"}
    return report


def analyze(log: str, case: str) -> dict:
    selection = None
    if "AUTOMX_CORE_PHASE=" in log:
        log, selection = wavetools.completed_run_log(log, phase="CORE")
    expected = tuple(f"{label}{pol}{c}" for c in range(4) for label in ("blpre", "heldpre", "held", "late")
                     for pol in ("p", "n")) + ("track_b", "track_n")
    if re.search(r"(?im)^\s*(error\b|fatal\b)", log):
        raise ValueError("ngspice reported a simulator/measurement error")
    raw = parse_measurements(log, expected)
    if set(raw) != set(expected) or not all(math.isfinite(v) for v in raw.values()):
        raise ValueError("missing/nonfinite core-acquisition scalar measurements")
    if raw["track_b"] < 1.62 or abs(raw["track_n"]) > .18:
        raise ValueError("physical TG controls are not off at 12ns")
    if any(not -.2 <= raw[k] <= 2.1 for k in expected if k not in ("track_b", "track_n")):
        raise ValueError("core-acquisition voltage outside diagnostic range")
    differences = {label: [raw[f"{label}n{c}"] - raw[f"{label}p{c}"] for c in range(4)]
                   for label in ("blpre", "heldpre", "held", "late")}
    if case != "zero" and max(map(abs, differences["blpre"])) < .001:
        raise ValueError("nonzero core stimulus produced no measured bitline signal")
    error = max(abs(a-b) for a, b in zip(differences["held"], differences["blpre"]))
    expected = (0, 0, 0, 0) if case == "zero" else (2, -2, 10, 0)
    zero_columns = [c for c, value in enumerate(expected) if value == 0]
    held_values = [raw[f"held{pol}{c}"] for c in range(4) for pol in ("p", "n")]
    report = {"raw_measurements": raw, "differentials_v": differences,
            "maximum_capture_error_v": error, "capture_budget_met": error <= .0008,
            "expected_integer_sums": list(expected),
            "expected_zero_columns": zero_columns,
            "maximum_expected_zero_held_abs_v": max(abs(differences["held"][c]) for c in zero_columns),
            "unadjusted_zero_within_800uv": all(abs(differences["held"][c]) <= .0008 for c in zero_columns),
            "held_node_range_v": [min(held_values), max(held_values)],
            "held_node_above_nominal_vdd_v": max(0., max(held_values)-1.8),
            "maximum_hold_drift_v": max(abs(a-b) for a, b in zip(differences["late"], differences["held"]))}
    if selection:
        report["measurement_log_selection"] = selection
    return report


def scalar_waveform_agreement(measurements, vectors, *, tolerance_v=2e-6):
    """Check the scalar and waveform receipts describe the very same run."""
    samples = []
    for c in range(4):
        for label, node, at in (("blpre", "BL", 7.95), ("heldpre", "H", 7.95),
                                ("held", "H", 12.), ("late", "H", 16.)):
            for pol in ("P", "N"):
                key = f"{label}{pol.lower()}{c}"
                value = wavetools.sample(vectors, f"v({node}{pol}{c})", at*1e-9)
                samples.append(abs(measurements[key]-value))
    for pin in ("TRACK_B", "TRACK_N"):
        samples.append(abs(measurements[pin.lower()]-wavetools.sample(vectors, f"v({pin})", 12e-9)))
    error = max(samples)
    if error > tolerance_v:
        raise ValueError(f"scalar/raw waveform mismatch: {error:g} V exceeds {tolerance_v:g} V")
    return {"status": "MATCHED", "sample_count": len(samples),
            "maximum_absolute_difference_v": error, "tolerance_v": tolerance_v}


def run(root: Path, *, pdk_root: Path = recovery.DEFAULT_PDK, tag="core_acq_20261018_01",
        source_tag="physical_next_20261018_03_acq", execute=False, timeout_s=900, recipe: Path = RECIPE,
        waveform=False) -> dict:
    root, pdk = Path(root).resolve(), Path(pdk_root).expanduser().resolve()
    common.tag_ok(tag)
    common.tag_ok(source_tag)
    if timeout_s <= 0:
        raise ValueError("positive timeout required")
    if recipe not in (RECIPE, SHIELDED_RECIPE, BANKED_RECIPE):
        raise ValueError("choose an original, shielded or banked integration recipe")
    expected = dict(EXPECTED)
    if recipe == BANKED_RECIPE:
        expected["mim3"] = 168
    report = {"format": "automx-cim-flow2-core-acquisition-v1", "tag": tag,
              "status": "PREPARED", "physical_gate": "NOT_RUN", "planned_sims": 6,
              "completed_sims": 0, "jobs": [], "expected_devices": expected,
              "not_signoff": "core plus physical acquisition only; 800fF ideal BL loads; no ADC, physical BL loading, decoder, LIB/SPEF/STA or independent MHA signoff"}
    store, source_items = None, []
    try:
        source = (sources(root, source_tag, pdk, banked=True) if recipe == BANKED_RECIPE
                  else sources(root, source_tag, pdk))
        source_items = source["items"]
        tech, setup, model = (pdk / p for p in ("libs.tech/magic/sky130A.tech", "libs.tech/netgen/sky130A_setup.tcl", "libs.tech/ngspice/sky130.lib.spice"))
        tools = {name: acq.stage5._find_tool(name) for name in ("magic", "klayout", "netgen", "ngspice")}
        if not all(tools.values()):
            raise ValueError("Magic, KLayout, Netgen and ngspice are required on the EDA server")
        reference_text = reference_spice(source["core"]["spice"].read_text(encoding="utf-8"),
            source["acquisition"]["netlists"]["schematic"].read_text(encoding="utf-8"))
        # Tool evidence depends on actual inputs/commands, not the Python
        # parser's timestamp/hash. A later analysis fix can reread the same
        # checkpointed logs without rerunning layout or SPICE.
        identity = {"recipe": common._sha(root / recipe), "sources": source_items,
                    "reference_sha256": sha256(reference_text.encode()).hexdigest(),
                    "technology": common._sha(tech), "setup": common._sha(setup), "model": common._sha(model),
                    "klayout_deck": common._sha(acq.stage5._klayout_deck(pdk)),
                    "versions": {n: acq.stage5._tool_version(n, t) for n, t in tools.items()}}
        if waveform:
            identity["measurement_mode"] = "SCALAR_AND_ALIGNED_WAVEFORM_V1"
            if recipe == BANKED_RECIPE:
                identity["quiet_hold_stop_us"] = 4.
        report["sources"] = source_items
        report["analysis_runner_sha256"] = common._sha(Path(__file__))
        report["layout_variant"] = ("FOUR_LOCAL_DIFFERENTIAL_BANKS_V1" if recipe == BANKED_RECIPE else
            "GROUND_SHIELDED_BLN3_HP0_BOUNDARY" if recipe == SHIELDED_RECIPE else "ORIGINAL_UNSHIELDED")
        if recipe == BANKED_RECIPE:
            report["bitline_load"] = "20 physical MIM leaves per BLP/BLN; no ideal CBL in this testbench"
            report["not_signoff"] = "core plus banked physical acquisition/BL capacitors; no ADC conditioning/decoder/LIB/SPEF/STA or fresh-MHA signoff"
        report["body_mapping"] = {"core.VSUBS": "VGND", "core.VGND": "VGND", "nfet.B": "VGND", "pfet.B": "VPWR", "precharge.S": "VPWR"}
        if not execute:
            return report
        store = common.Store(root, tag, identity)
        def magic_step(name, text):
            return store.step(name, [tools["magic"], str(tech)], tcl=text,
                executor=lambda work: acq.stage5._magic(tools["magic"], tech, work, text, timeout_s))
        result, layout = magic_step("layout", layout_tcl(root, source["core"]["gds"], source["acq_gds"], locations=source["locations"], recipe=recipe))
        count = re.findall(r"(?m)^AUTOMX_COMPOSITE_DRC=(\d+)\s*$", result.stdout + result.stderr)
        report["magic_drc_violations"] = int(count[0]) if len(count) == 1 else None
        if result.returncode or report["magic_drc_violations"] != 0 or "AUTOMX_COMPOSITE_DONE" not in result.stdout:
            raise RuntimeError("composite Magic layout/DRC failed; inspect layout.log")
        gds, lef = layout / f"{CELL}.gds", layout / f"{CELL}.lef"
        pin_list = re.findall(r"(?m)^\s*PIN\s+(\S+)\s*$", lef.read_text(encoding="utf-8"))
        if len(pin_list) != len(PINS) or set(pin_list) != set(PINS):
            raise ValueError("composite LEF must expose 62 unique ports")
        hierarchy = acq.fet_lvs.leaves._gds_hierarchy(gds)
        if CELL not in hierarchy or set().union(*hierarchy.values()) - set(hierarchy):
            raise ValueError("composite GDS top or referenced structures are missing")
        deck = acq.stage5._klayout_deck(pdk)
        xml = store.build / "klayout/klayout.xml"
        command = [tools["klayout"], "-b", "-r", str(deck), "-rd", f"input={gds}", "-rd", f"report={xml}"]
        result, _ = store.step("klayout", command, executor=lambda work: acq.stage5._run(command, work, timeout_s))
        db = ET.parse(xml).getroot() if xml.is_file() else None
        report["klayout_drc_violations"] = len(list(db.iter("item"))) if db is not None and db.tag == "report-database" else None
        if result.returncode or report["klayout_drc_violations"] != 0:
            raise RuntimeError("composite KLayout DRC failed")
        bounds = "1005um 270um" if recipe == BANKED_RECIPE else "855um 230um"
        prefix = f"crashbackups stop\ngds read {{{gds.as_posix()}}}\nload {CELL}\nselect top cell\nbox -5um -5um {bounds}\n"
        # Keep 160 parallel BL MIM leaves visible in the extracted inventory;
        # ext2spice lvs otherwise enables conservative device merging.
        merge = "ext2spice merge none\n" if recipe == BANKED_RECIPE else ""
        er, work = magic_step("lvs_extract", prefix + "drc on\ndrc check\ndrc catchup\n"
            + 'puts "AUTOMX_COMPOSITE_GDS_DRC=[drc list count total]"\n'
            + "extract do local\nextract all\next2spice lvs\n" + merge + "ext2spice scale off\n"
            + f"ext2spice subcircuit on\next2spice subcircuit top on\next2spice -o {CELL}.lvs.spice\nputs COMPOSITE_LVS_DONE\nquit -noprompt\n")
        extracted = work / f"{CELL}.lvs.spice"
        if er.returncode or not re.search(r"(?m)^AUTOMX_COMPOSITE_GDS_DRC=0\s*$", er.stdout):
            raise RuntimeError("independent GDS extraction/DRC failed")
        report["magic_gds_drc_violations"] = 0
        report["extracted_devices"] = {kind: acq.stage5._spice_device_count(extracted, CELL, primitive)
            for kind, primitive in (("nfet", "sky130_fd_pr__nfet_01v8"), ("pfet", "sky130_fd_pr__pfet_01v8"), ("mim3", "sky130_fd_pr__cap_mim_m3_1"))}
        if report["extracted_devices"] != expected or set(acq.stage5.parse_spice_subckt_pins(extracted, CELL)) != set(PINS):
            raise ValueError("composite transistor count/port contract differs")
        reference = store.build / f"{CELL}.reference.spice"
        reference.write_text(reference_text, encoding="utf-8")
        nlog = store.build / "lvs/netgen.log"
        command = [tools["netgen"], "-batch", "lvs", f"{extracted} {CELL}", f"{reference} {CELL}", str(setup), str(nlog)]
        nr, _ = store.step("lvs", command, executor=lambda work: acq.stage5._run(command, work, timeout_s))
        report["transistor_lvs_match"] = nr.returncode == 0 and nlog.is_file() and acq.fet_lvs._netgen_match(nlog.read_text(encoding="utf-8", errors="replace"))
        if not report["transistor_lvs_match"]:
            raise RuntimeError("composite transistor LVS failed; S/B/VSUBS are not waived")
        pr, pwork = magic_step("pex", prefix + "extract do local\nextract do resistance\nextract all\n"
            + "ext2sim labels on\next2sim\nextresist tolerance 10\nextresist all\n"
            + "ext2spice lvs\n" + merge + "ext2spice scale off\next2spice cthresh 0.01\next2spice extresist on\n"
            + f"ext2spice short resistor\next2spice subcircuit on\next2spice subcircuit top on\next2spice -o {CELL}.raw.spice\nputs COMPOSITE_PEX_DONE\nquit -noprompt\n")
        raw, pex = pwork / f"{CELL}.raw.spice", store.build / f"{CELL}.pex.spice"
        if pr.returncode or "COMPOSITE_PEX_DONE" not in pr.stdout:
            raise RuntimeError("composite distributed RC extraction failed")
        canonical(raw, pex)
        report["parasitics"] = acq.precharge_pex._parasitic_counts(raw)
        report["ground_rc_audit"] = acq._rc_audit(raw)
        if not report["ground_rc_audit"]["nonzero_resistors"] or report["ground_rc_audit"]["unreferenced_capacitive_nodes"] or not report["parasitics"]["capacitors"]:
            raise ValueError("composite PEX has missing RC or floating substrate nodes")
        report["physical_gate"] = "CORE_ACQUISITION_DRC_TRANSISTOR_LVS_RC_PEX_PASS"
        store.physical.mkdir(parents=True, exist_ok=True)
        for path in (gds, lef, reference, pex):
            shutil.copy2(path, store.physical / path.name)
        for case in ("zero", "pair_a", "pair_b"):
            for variant, net in (("schematic", reference), ("pex", pex)):
                name = f"tt_{case}_{variant}"
                options = {}
                if waveform:
                    options["waveform"] = True
                if recipe == BANKED_RECIPE:
                    options["physical_bl_load"] = True
                    if waveform:
                        options["retention_us"] = 4.
                text = pilot_deck(model, net, variant, case, **options)
                command = [tools["ngspice"], "-b", name + ".spice"]
                def simulate(work, content=text, cmd=command, filename=name + ".spice"):
                    (work / filename).write_text(content, encoding="utf-8")
                    return acq.stage5._run(cmd, work, timeout_s)
                sr, work = store.step(name, command, tcl=text, executor=simulate)
                entry = {"case": case, "variant": variant, "returncode": sr.returncode}
                report["jobs"].append(entry)
                if sr.returncode:
                    raise RuntimeError(f"core-driven transient failed: {name}")
                entry.update(analyze(sr.stdout + sr.stderr, case))
                if waveform:
                    if "AUTOMX_CORE_PHASE=RAW_WRITTEN" not in sr.stdout:
                        raise ValueError("core waveform write did not finish")
                    raw_wave = work / "core.raw"
                    entry["waveform"] = acq._item(root, raw_wave)
                    vectors = wavetools.read_raw(raw_wave)
                    entry["scalar_waveform_agreement"] = scalar_waveform_agreement(entry["raw_measurements"], vectors)
                    entry["stage_diagnostic"] = analyze_waveform(vectors)
                report["completed_sims"] += 1
        report["capture_budget_v"] = .0008
        report["capture_budget_met_in_pilot"] = all(j["capture_budget_met"] for j in report["jobs"] if j["variant"] == "pex")
        report["maximum_expected_zero_held_abs_v"] = max(j["maximum_expected_zero_held_abs_v"] for j in report["jobs"] if j["variant"] == "pex")
        report["operating_point_gate"] = "PENDING_TRANSFER_CALIBRATION_AND_FRESH_MHA"
        report["status"] = "MEASURED_CORE_ACQUISITION_PROTOTYPE"
    except FileExistsError:
        raise
    except (Exception, KeyboardInterrupt) as error:
        report["status"] = "INTERRUPTED" if isinstance(error, KeyboardInterrupt) else "BLOCKED_CORE_ACQUISITION"
        report["error"] = f"{type(error).__name__}: {error}"
        if isinstance(error, KeyboardInterrupt):
            raise
    finally:
        if execute:
            folder = root / common.BASE / tag
            if store:
                if report.get("error"):
                    store.note(report["error"])
                store.note(f"END {report['status']}: {report['completed_sims']}/6")
            if sys.exc_info()[0] is not FileExistsError:
                common.save_summary(folder / "summary.json", report)
                common.bundle(root, tag, source_items)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--pdk-root", type=Path, default=recovery.DEFAULT_PDK)
    parser.add_argument("--tag", default="core_acq_20261018_01")
    parser.add_argument("--source-tag", default="physical_next_20261018_03_acq")
    parser.add_argument("--run", action="store_true")
    recipes = parser.add_mutually_exclusive_group()
    recipes.add_argument("--shielded", action="store_true")
    recipes.add_argument("--banked", action="store_true")
    parser.add_argument("--waveform", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=900)
    args = parser.parse_args()
    output = run(args.root, pdk_root=args.pdk_root, tag=args.tag, source_tag=args.source_tag, execute=args.run, timeout_s=args.timeout_s,
                 recipe=BANKED_RECIPE if args.banked else SHIELDED_RECIPE if args.shielded else RECIPE,
                 waveform=args.waveform)
    print(json.dumps(output, indent=2))
    if args.run and output["status"] != "MEASURED_CORE_ACQUISITION_PROTOTYPE":
        raise SystemExit(1)

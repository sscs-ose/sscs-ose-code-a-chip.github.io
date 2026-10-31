#!/usr/bin/env python3
"""Build/check four local acquisition banks using the existing verified leaves.

Keep the 28-MOS/eight-hold-MIM front end and add twenty physical MIM leaves
per bitline. Native Magic/KLayout DRC, transistor LVS, body connections and
distributed PEX precede connected-core electrical characterization.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_flow2_acquisition_layout as acq
from scripts import flow2_integration_common as common
from scripts.run_flow2_acquisition_transient_recovery import DEFAULT_PDK

RECIPE = Path("physical/sky130/wrapper_prototype/assemble_acquisition_banked.tcl")
BUILD = Path("build/flow2_periphery_leaf")
PHYSICAL = Path("physical/sky130/wrapper_prototype/leaf_cells")
BL_CAP_REPLICAS = 20
EXPECTED = {"nfet": 10, "pfet": 18, "mim3": 8+8*BL_CAP_REPLICAS}


def circuit():
    devices = acq.circuit()
    devices += [{"name": f"BLCH_{pol}{c}_{unit}", "kind": "cap", "nets": [f"BL{pol}{c}", "VGND"]}
                for c in range(4) for pol in ("P", "N") for unit in range(BL_CAP_REPLICAS)]
    return devices


def reference_spice():
    text = acq.reference_spice()
    extra = [f"X{d['name']} {' '.join(d['nets'])} sky130_fd_pr__cap_mim_m3_1 W=4.2 L=4.2"
             for d in circuit() if d["name"].startswith("BLCH_")]
    return text.replace(f".ends {acq.CELL}", "\n".join([*extra, f".ends {acq.CELL}"]))


def pin_locations():
    result = {f"{stem}{c}": [200.*c+1.3, 30.+4.*j]
        for c in range(4) for j, stem in enumerate(("BLP", "BLN", "HP", "HN"))}
    result.update({p: [1.3, 60.+6.*j] for j, p in enumerate(("VPWR", "VGND", "PRE_B", "TRACK_B", "TRACK_N", "TRACK"))})
    return result


def layout_tcl(root, views):
    # Keep the original recipe immutable and avoid replacing it in-place or
    # mutating module globals while a different branch is using them.
    original = (root/acq.RECIPE).read_text(encoding="utf-8")
    content = acq._layout_tcl(root, views)
    if not content.endswith(original):
        raise ValueError("unexpected acquisition Tcl preamble")
    preamble = content[:-len(original)]
    marker = "set components {\n"
    if preamble.count(marker) != 1:
        raise ValueError("unexpected component preamble")
    preamble = preamble[:preamble.index(marker)]
    rows = [f"  {{{d['name']} {d['kind']} {{{' '.join(d['nets'])}}}}}" for d in circuit()]
    return preamble+marker+"\n".join(rows)+"\n}\n"+(root/RECIPE).read_text(encoding="utf-8")


def run(root, *, pdk_root=DEFAULT_PDK, tag="banked_acquisition_20261018_01", execute=False, timeout_s=900):
    root, pdk = Path(root).resolve(), Path(pdk_root).expanduser().resolve()
    common.tag_ok(tag)
    if timeout_s <= 0:
        raise ValueError("positive timeout required")
    report = {"format": acq.FORMAT, "tag": tag, "status": "PREPARED",
        "layout_variant": "FOUR_LOCAL_DIFFERENTIAL_BANKS_V1", "jobs": [],
        "physical_bitline_capacitor_replicas_per_node": BL_CAP_REPLICAS,
        "bitline_load": "160 physical MIM leaves; exact effective C requires new extracted electrical characterization",
        "expected_devices": EXPECTED, "physical_gate": "NOT_RUN",
        "not_signoff": "acquisition routing prototype only; no electrical transfer, ADC, wrapper LIB/SPEF/STA or system claim"}
    store, source_items = None, []
    try:
        views, sources = acq._sources(root, "sample_fet_20261017_03", "precharge_leaf_guarded_20261017_03", "hold_cap_mim3_20261017_02")
        tech, setup, model = (pdk/p for p in ("libs.tech/magic/sky130A.tech", "libs.tech/netgen/sky130A_setup.tcl", "libs.tech/ngspice/sky130.lib.spice"))
        tools = {n: acq.stage5._find_tool(n) for n in ("magic", "netgen", "klayout")}
        if not all(tools.values()) or not setup.is_file() or not model.is_file() or common._sha(tech) != sources["magic_technology_sha256"]:
            raise ValueError("native tools/models/technology must match the passed leaves")
        source_items = [acq._item(root, v["gds"]) for v in views.values()]
        source_items += [item for item in sources.values() if isinstance(item, dict) and "path" in item]
        identity = {"sources": sources, "gds": source_items, "recipe": common._sha(root/RECIPE),
            "reference": reference_spice(), "tech": common._sha(tech), "setup": common._sha(setup),
            "versions": {k: acq.stage5._tool_version(k, v) for k, v in tools.items()}}
        report["sources"] = sources
        report["recipe_sha256"] = identity["recipe"]
        report["model_sha256"] = common._sha(model)
        if not execute:
            return report
        store = common.Store(root, tag, identity, result_base=acq.BASE, build_base=BUILD, physical_base=PHYSICAL)
        def magic_step(name, content):
            command = [tools["magic"], "-dnull", "-noconsole"]
            return store.step(name, command, tcl=content,
                executor=lambda work: acq.stage5._magic(tools["magic"], tech, work, content, timeout_s))
        result, work = magic_step("layout", layout_tcl(root, views))
        report["magic_drc_violations"] = acq.drc_details(result.stdout+result.stderr)["count"]
        if result.returncode or report["magic_drc_violations"] != 0 or "AUTOMX_ACQUISITION_DONE" not in result.stdout:
            raise RuntimeError("banked acquisition Magic layout/DRC failed")
        gds, lef = work/f"{acq.CELL}.gds", work/f"{acq.CELL}.lef"
        pins = re.findall(r"(?m)^\s*PIN\s+(\S+)\s*$", lef.read_text(encoding="utf-8"))
        if len(pins) != 22 or set(pins) != set(acq.PINS) or acq.CELL not in acq.fet_lvs.leaves._gds_hierarchy(gds):
            raise ValueError("banked GDS/LEF interface differs")
        deck = acq.stage5._klayout_deck(pdk)
        xml = store.build/"klayout/klayout.xml"
        command = [tools["klayout"], "-b", "-r", str(deck), "-rd", f"input={gds}", "-rd", f"report={xml}"]
        result, _ = store.step("klayout", command, executor=lambda work: acq.stage5._run(command, work, timeout_s))
        db = ET.parse(xml).getroot() if xml.is_file() else None
        report["klayout_drc_violations"] = len(list(db.iter("item"))) if db is not None and db.tag == "report-database" else None
        if result.returncode or report["klayout_drc_violations"] != 0:
            raise RuntimeError("banked acquisition KLayout DRC failed")
        shutil.copy2(xml, store.folder/"klayout.xml")
        prefix = f"crashbackups stop\ngds read {{{gds.as_posix()}}}\nload {acq.CELL}\nselect top cell\n"
        result, work = magic_step("lvs_extract", prefix+"box -5um -5um 905um 200um\ndrc on\ndrc check\ndrc catchup\n"
            + 'puts "AUTOMX_ACQUISITION_GDS_DRC=[drc list count total]"\n'
            + "extract do local\nextract all\next2spice lvs\next2spice merge none\next2spice scale off\next2spice subcircuit on\next2spice subcircuit top on\n"
            + f"ext2spice -o {acq.CELL}.lvs.spice\nputs AUTOMX_ACQUISITION_LVS_DONE\nquit -noprompt\n")
        count = re.findall(r"(?m)^AUTOMX_ACQUISITION_GDS_DRC=(\d+)\s*$", result.stdout+result.stderr)
        report["magic_gds_drc_violations"] = int(count[0]) if len(count) == 1 else None
        if result.returncode or report["magic_gds_drc_violations"] != 0:
            raise RuntimeError("banked GDS extraction/DRC failed")
        extracted = work/f"{acq.CELL}.lvs.spice"
        report["extracted_devices"] = {k: acq.stage5._spice_device_count(extracted, acq.CELL, p)
            for k, p in (("nfet", "sky130_fd_pr__nfet_01v8"), ("pfet", "sky130_fd_pr__pfet_01v8"), ("mim3", "sky130_fd_pr__cap_mim_m3_1"))}
        if report["extracted_devices"] != EXPECTED:
            raise ValueError("banked extracted device counts differ")
        reference = store.build/f"{acq.CELL}.reference.spice"
        reference.write_text(reference_spice(), encoding="utf-8")
        nlog = store.build/"lvs/netgen.log"
        command = [tools["netgen"], "-batch", "lvs", f"{extracted} {acq.CELL}", f"{reference} {acq.CELL}", str(setup), str(nlog)]
        result, _ = store.step("lvs", command, executor=lambda work: acq.stage5._run(command, work, timeout_s))
        report["transistor_lvs_match"] = result.returncode == 0 and nlog.is_file() and acq.fet_lvs._netgen_match(nlog.read_text(encoding="utf-8", errors="replace"))
        if not report["transistor_lvs_match"]:
            raise RuntimeError("banked transistor LVS failed; body/S/B are not waived")
        shutil.copy2(nlog, store.folder/"netgen.log")
        result, work = magic_step("pex", prefix+"extract do local\nextract do resistance\nextract all\next2sim labels on\next2sim\n"
            + "extresist tolerance 10\nextresist all\next2spice lvs\next2spice merge none\next2spice scale off\next2spice cthresh 0.01\n"
            + "ext2spice extresist on\next2spice short resistor\next2spice subcircuit on\next2spice subcircuit top on\n"
            + f"ext2spice -o {acq.CELL}.pex.raw.spice\nputs AUTOMX_ACQUISITION_PEX_DONE\nquit -noprompt\n")
        raw, pex = work/f"{acq.CELL}.pex.raw.spice", work/f"{acq.CELL}.pex.spice"
        if result.returncode or "AUTOMX_ACQUISITION_PEX_DONE" not in result.stdout:
            raise RuntimeError("banked RC extraction failed")
        acq._canonical(raw, pex)
        report["parasitics"] = acq.precharge_pex._parasitic_counts(raw)
        report["substrate_rc_audit"] = acq._rc_audit(raw)
        if not report["substrate_rc_audit"]["nonzero_resistors"] or report["substrate_rc_audit"]["unreferenced_capacitive_nodes"] or not report["parasitics"]["capacitors"]:
            raise RuntimeError("banked distributed RC/substrate audit failed")
        store.physical.mkdir(parents=True, exist_ok=True)
        for p in (gds, lef, reference, pex):
            shutil.copy2(p, store.physical/p.name)
        report["physical_gate"] = "BANKED_ACQUISITION_DRC_TRANSISTOR_LVS_RC_PEX_PASS"
        report["status"] = "BANKED_ACQUISITION_PHYSICAL_PROTOTYPE"
    except FileExistsError:
        raise
    except (Exception, KeyboardInterrupt) as error:
        report["status"] = "INTERRUPTED" if isinstance(error, KeyboardInterrupt) else "BLOCKED_BANKED_ACQUISITION"
        report["error"] = f"{type(error).__name__}: {error}"
        if isinstance(error, KeyboardInterrupt):
            raise
    finally:
        if execute and sys.exc_info()[0] is not FileExistsError:
            if store:
                store.note(f"END {report['status']}")
                report["artifacts"] = [acq._item(root, p) for base in (store.folder, store.build, store.physical)
                    for p in sorted(base.rglob("*")) if p.is_file() and p.name not in ("summary.json", "history.log") and not p.name.startswith("summary.prior_")]
            common.save_summary(root/acq.BASE/tag/"summary.json", report)
            source_items += [acq._item(root, p) for base in (acq.BASE, BUILD, PHYSICAL)
                for p in (root/base/tag).rglob("*") if p.is_file()]
            common.bundle(root, tag, source_items)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--pdk-root", type=Path, default=DEFAULT_PDK)
    p.add_argument("--tag", default="banked_acquisition_20261018_01")
    p.add_argument("--run", action="store_true")
    p.add_argument("--timeout-s", type=int, default=900)
    a = p.parse_args()
    result = run(a.root, pdk_root=a.pdk_root, tag=a.tag, execute=a.run, timeout_s=a.timeout_s)
    print(json.dumps(result, indent=2))
    if a.run and result["status"] != "BANKED_ACQUISITION_PHYSICAL_PROTOTYPE":
        raise SystemExit(1)

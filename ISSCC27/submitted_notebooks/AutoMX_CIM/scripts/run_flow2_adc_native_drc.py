#!/usr/bin/env python3
"""Check the published ADC GDS on the same native PDK as the CIM front end.

This is a real GDS geometry check independent of the SPICE runtime branch.
It does not waive the 57/81-port interface or claim composite transistor LVS.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_flow2_adc_ip as ip
from scripts import flow2_integration_common as common
from scripts import run_flow2_acquisition_layout as acq
from scripts.run_flow2_acquisition_transient_recovery import DEFAULT_PDK


def run(root, *, pdk_root=DEFAULT_PDK, tag="adc_native_drc_20261018_01", execute=False, timeout_s=900):
    root, pdk = Path(root).resolve(), Path(pdk_root).expanduser().resolve()
    common.tag_ok(tag)
    if timeout_s <= 0:
        raise ValueError("positive timeout required")
    report = {"format": "automx-cim-flow2-adc-native-drc-v1", "tag": tag, "status": "PREPARED",
        "not_signoff": "native ADC GDS DRC only; no analog pin adapter, transistor LVS, new PEX, ADC transfer or composite wrapper/LIB/SPEF/STA pass"}
    store, items = None, []
    try:
        source = root/ip.FILES["gds_gz"]
        if not source.is_file() or common._sha(source) != ip.EXPECTED_SHA256["gds_gz"]:
            raise ValueError("pinned ADC GDS is missing or changed")
        items = [acq._item(root, source)]
        tech = pdk/"libs.tech/magic/sky130A.tech"
        tools = {n: acq.stage5._find_tool(n) for n in ("magic", "klayout")}
        if not all(tools.values()) or not tech.is_file():
            raise ValueError("host Magic/KLayout and native PDK technology are required")
        deck = acq.stage5._klayout_deck(pdk)
        identity = {"source": items, "tech": common._sha(tech), "klayout_deck": common._sha(deck),
            "versions": {n: acq.stage5._tool_version(n, p) for n, p in tools.items()}}
        report["inputs"] = identity
        if not execute:
            return report
        store = common.Store(root, tag, identity)
        gds = store.build/"adc_top.source.gds"
        data = gzip.decompress(source.read_bytes())
        if gds.is_file() and gds.read_bytes() != data:
            raise FileExistsError("expanded ADC GDS changed; retain evidence and use a new tag")
        if not gds.is_file():
            gds.write_bytes(data)
        if "adc_top" not in acq.fet_lvs.leaves._gds_hierarchy(gds):
            raise ValueError("published ADC top structure is missing")
        report["gds"] = acq._item(root, gds)
        tcl = (f"crashbackups stop\ngds read {{{gds.as_posix()}}}\nload adc_top\nselect top cell\n"
            # Enclose the pinned 423x403um macro; do not check Magic's
            # unrelated initial 1um cursor box and accidentally report zero.
            "box -50um -50um 600um 600um\n"
            "drc on\ndrc check\ndrc catchup\n"
            'puts "AUTOMX_ADC_NATIVE_DRC=[drc list count total]"\n'
            'foreach {rule areas} [drc listall why] {puts "AUTOMX_ADC_NATIVE_RULE=$rule COUNT=[llength $areas] BOXES=$areas"}\n'
            "puts AUTOMX_ADC_NATIVE_DRC_DONE\nquit -noprompt\n")
        cmd = [tools["magic"], "-dnull", "-noconsole"]
        result, _ = store.step("magic_drc", cmd, tcl=tcl,
            executor=lambda work: acq.stage5._magic(tools["magic"], tech, work, tcl, timeout_s))
        values = re.findall(r"(?m)^AUTOMX_ADC_NATIVE_DRC=(\d+)\s*$", result.stdout+result.stderr)
        report["magic_drc_violations"] = int(values[0]) if len(values) == 1 else None
        report["magic_returncode"] = result.returncode
        report["magic_completed"] = "AUTOMX_ADC_NATIVE_DRC_DONE" in result.stdout
        # Run independent KLayout even after a Magic DRC violation, to keep
        # both diagnostic reports instead of hiding the second result.
        xml = store.build/"klayout/klayout.xml"
        cmd = [tools["klayout"], "-b", "-r", str(deck), "-rd", f"input={gds}", "-rd", f"report={xml}"]
        result, _ = store.step("klayout", cmd, executor=lambda work: acq.stage5._run(cmd, work, timeout_s))
        report["klayout_returncode"] = result.returncode
        db = ET.parse(xml).getroot() if xml.is_file() else None
        report["klayout_drc_violations"] = len(list(db.iter("item"))) if db is not None and db.tag == "report-database" else None
        passed = (report["magic_returncode"] == 0 and report["klayout_returncode"] == 0
            and report["magic_completed"]
            and report["magic_drc_violations"] == 0 and report["klayout_drc_violations"] == 0)
        report["status"] = "ADC_NATIVE_GDS_DRC_PASS_ONLY" if passed else "MEASURED_ADC_NATIVE_DRC_BLOCKED"
    except FileExistsError:
        raise
    except (Exception, KeyboardInterrupt) as error:
        report["status"] = "INTERRUPTED" if isinstance(error, KeyboardInterrupt) else "BLOCKED_ADC_NATIVE_DRC"
        report["error"] = f"{type(error).__name__}: {error}"
        if isinstance(error, KeyboardInterrupt):
            raise
    finally:
        if execute and sys.exc_info()[0] is not FileExistsError:
            if store:
                store.note(f"END {report['status']}")
            common.save_summary(root/common.BASE/tag/"summary.json", report)
            common.bundle(root, tag, items)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--pdk-root", type=Path, default=DEFAULT_PDK)
    p.add_argument("--tag", default="adc_native_drc_20261018_01")
    p.add_argument("--run", action="store_true")
    p.add_argument("--timeout-s", type=int, default=900)
    a = p.parse_args()
    result = run(a.root, pdk_root=a.pdk_root, tag=a.tag, execute=a.run, timeout_s=a.timeout_s)
    print(json.dumps(result, indent=2))
    if a.run and result["status"] != "ADC_NATIVE_GDS_DRC_PASS_ONLY":
        raise SystemExit(1)

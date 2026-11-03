"""Native physical checks for new wrapper blocks; no mocked PASS in production."""
from __future__ import annotations
import json
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET

from scripts import flow2_integration_common as common
from scripts import run_flow2_acquisition_layout as acq


def canonical(raw, target, cell, pins):
    actual = acq.stage5.parse_spice_subckt_pins(raw, cell)
    if len(actual) != len(pins) or set(actual) != set(pins):
        raise ValueError(f"extracted port mismatch: {actual}")
    text = raw.read_text(encoding="utf-8")
    text = re.sub(rf"(?im)^(\s*\.subckt\s+){re.escape(cell)}(?=\s)", rf"\g<1>{cell}_raw", text, count=1)
    text = re.sub(rf"(?im)^(\s*\.ends\s+){re.escape(cell)}(?=\s|$)", rf"\g<1>{cell}_raw", text)
    text = re.sub(r"(?im)^\s*\.end\s*$", "", text)
    target.write_text(text.rstrip()+f"\n.subckt {cell}_pex {' '.join(pins)}\n"
        +f"XRAW {' '.join(actual)} {cell}_raw\n.ends {cell}_pex\n", encoding="utf-8")


def physical(root, *, pdk, tag, cell, pins, layout_tcl, reference, sources, timeout_s=1800):
    root, pdk = Path(root).resolve(), Path(pdk).resolve()
    common.tag_ok(tag)
    tech, setup = (pdk/rel for rel in ("libs.tech/magic/sky130A.tech", "libs.tech/netgen/sky130A_setup.tcl"))
    tools = {n: acq.stage5._find_tool(n) for n in ("magic", "klayout", "netgen")}
    if not all(tools.values()) or not tech.is_file() or not setup.is_file():
        raise ValueError("native Magic/KLayout/Netgen and SKY130A required on server")
    from hashlib import sha256
    identity = {"cell": cell, "pins": list(pins), "sources": sources, "tech": common._sha(tech),
        "setup": common._sha(setup), "layout": sha256(layout_tcl.encode()).hexdigest(),
        "reference": sha256(reference.encode()).hexdigest(),
        "versions": {n: acq.stage5._tool_version(n, v) for n, v in tools.items()}}
    store = common.Store(root, tag, identity)
    report = {"format": "automx-cim-wrapper-physical-block-v1", "tag": tag, "cell": cell,
        "status": "STARTED", "pins": list(pins), "inputs": identity,
        "not_signoff": "block DRC/transistor LVS/PEX only; functional, loaded accuracy, STA/noise/PVT are separate"}

    def magic(name, text):
        r, work = store.step(name, [tools["magic"], str(tech)], tcl=text,
            executor=lambda work: acq.stage5._magic(tools["magic"], tech, work, text, timeout_s))
        if r.returncode:
            raise RuntimeError(f"Magic {name} exited {r.returncode}; inspect {name}.log")
        return r, work

    try:
        store.note("START native wrapper block " + cell)
        r, work = magic("layout", layout_tcl)
        hits = re.findall(r"(?m)^AUTOMX_WRAPPER_DRC=(\d+)\s*$", r.stdout+r.stderr)
        report["magic_drc_violations"] = int(hits[0]) if len(hits) == 1 else None
        if report["magic_drc_violations"] != 0 or "AUTOMX_WRAPPER_LAYOUT_DONE" not in r.stdout:
            raise RuntimeError("new layout DRC did not pass; original rule/coordinates retained in layout.log")
        gds, lef = work/f"{cell}.gds", work/f"{cell}.lef"
        actual = re.findall(r"(?m)^\s*PIN\s+(\S+)\s*$", lef.read_text(encoding="utf-8"))
        if len(actual) != len(pins) or set(actual) != set(pins):
            raise ValueError("LEF interface mismatch")
        if cell not in acq.fet_lvs.leaves._gds_hierarchy(gds):
            raise ValueError("GDS top is absent")
        xml = store.build/"klayout/klayout.xml"
        cmd = [tools["klayout"], "-b", "-r", str(acq.stage5._klayout_deck(pdk)),
               "-rd", f"input={gds}", "-rd", f"report={xml}"]
        r, _ = store.step("klayout", cmd, executor=lambda work: acq.stage5._run(cmd, work, timeout_s))
        db = ET.parse(xml).getroot() if xml.is_file() else None
        report["klayout_drc_violations"] = len(list(db.iter("item"))) if db is not None and db.tag == "report-database" else None
        if r.returncode or report["klayout_drc_violations"] != 0:
            raise RuntimeError("independent KLayout DRC failed")
        prefix = f"crashbackups stop\ndrc off\ngds read {{{gds.as_posix()}}}\nload {cell}\nselect top cell\n"
        # All generated blocks / the 3600x700-um wrapper fit this checked
        # window. Never check Magic's unrelated initial one-micron box.
        prefix += "box -100um -100um 10000um 5000um\ndrc on\ndrc check\ndrc catchup\n"
        lvs = (prefix+'puts "AUTOMX_WRAPPER_GDS_DRC=[drc list count total]"\n'
            +"extract do local\nextract all\next2spice lvs\next2spice merge none\next2spice scale off\n"
            +f"ext2spice subcircuit on\next2spice subcircuit top on\next2spice -o {cell}.lvs.spice\n"
            +"puts AUTOMX_WRAPPER_LVS_EXTRACT_DONE\nquit -noprompt\n")
        r, ework = magic("lvs_extract", lvs)
        if not re.search(r"(?m)^AUTOMX_WRAPPER_GDS_DRC=0\s*$", r.stdout):
            raise RuntimeError("independent GDS Magic DRC failed")
        extracted = ework/f"{cell}.lvs.spice"
        actual = acq.stage5.parse_spice_subckt_pins(extracted, cell)
        if len(actual) != len(pins) or set(actual) != set(pins):
            raise ValueError("transistor extraction lost/added ports")
        ref = store.build/f"{cell}.reference.spice"
        if ref.exists() and ref.read_text(encoding="utf-8") != reference:
            raise FileExistsError("reference differs; new tag required")
        ref.write_text(reference, encoding="utf-8")
        nlog = store.build/"lvs/netgen.log"
        cmd = [tools["netgen"], "-batch", "lvs", f"{extracted} {cell}", f"{ref} {cell}", str(setup), str(nlog)]
        r, _ = store.step("lvs", cmd, executor=lambda work: acq.stage5._run(cmd, work, timeout_s))
        report["transistor_lvs_match"] = (r.returncode == 0 and nlog.is_file() and
            acq.fet_lvs._netgen_match(nlog.read_text(encoding="utf-8", errors="replace")))
        if not report["transistor_lvs_match"]:
            raise RuntimeError("transistor LVS failed; body and source connections are not waived")
        pex_text = prefix+"extract do local\nextract do resistance\nextract all\next2sim labels on\next2sim\n"
        pex_text += "extresist tolerance 10\nextresist all\next2spice lvs\next2spice merge none\next2spice scale off\n"
        pex_text += "ext2spice cthresh 0.01\next2spice extresist on\next2spice short resistor\n"
        pex_text += f"ext2spice subcircuit on\next2spice subcircuit top on\next2spice -o {cell}.raw.spice\n"
        pex_text += "puts AUTOMX_WRAPPER_PEX_DONE\nquit -noprompt\n"
        r, pwork = magic("pex", pex_text)
        if "AUTOMX_WRAPPER_PEX_DONE" not in r.stdout:
            raise RuntimeError("PEX did not complete")
        raw, pex = pwork/f"{cell}.raw.spice", store.build/f"{cell}.pex.spice"
        canonical(raw, pex, cell, pins)
        report["parasitics"] = acq.precharge_pex._parasitic_counts(raw)
        if not report["parasitics"].get("capacitors") or not report["parasitics"].get("resistors"):
            raise ValueError("distributed R/C missing from extraction")
        store.physical.mkdir(parents=True, exist_ok=True)
        report["views"] = {}
        for key, path in (("gds", gds), ("lef", lef), ("schematic", ref), ("pex", pex), ("lvs", extracted)):
            dest = store.physical/path.name
            shutil.copy2(path, dest)
            report["views"][key] = acq._item(root, dest)
        report["status"] = "BLOCK_DRC_TRANSISTOR_LVS_RC_PEX_PASS"
    except FileExistsError:
        raise
    except KeyboardInterrupt:
        report["status"] = "INTERRUPTED"
        raise
    except Exception as error:
        report.update(status="BLOCKED_PHYSICAL_BLOCK", error=f"{type(error).__name__}: {error}")
    finally:
        if __import__('sys').exc_info()[0] is not FileExistsError:
            common.save_summary(store.folder/"summary.json", report)
            store.note("END " + report["status"])
            common.bundle(root, tag, sources)
    return report

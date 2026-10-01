"""Summarize the full-chip FEOL DRC into results/fullchip/feol_drc.json.

The full-chip layout is not published (README), so the KLayout report databases stay private; this
script records only the per-rule marker counts and where the markers lie. The runs it summarizes:
  * the signed-off chip GDS, with the 266 enabled FEOL rules of the SKY130 KLayout deck split into
    parallel jobs (rule vpp.5 excluded: the vpp layer 82/64 holds no shape, so it cannot fire);
  * the same GDS after scripts/implant_fix.py, which closes the sub-rule implant gaps inside the
    OpenRAM macros, checked with scripts/verify_untouched.py and the same split decks.
usage: python3 scripts/feol_summary.py <dir of the original reports> <dir of the fixed-chip reports>
       [<signed-off GDS> <corrected GDS>]   (their SHA-256 values are recorded when given)
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
DECKS = ["P1", "P2", "P3", "P4", "A2", "B", "C"]


def summarize(d: pathlib.Path, prefix: str) -> dict:
    per_rule, per_cell, wall = collections.Counter(), collections.Counter(), {}
    rules_run = set()
    for deck in DECKS:
        db = ET.parse(d / f"{prefix}{deck}.lyrdb").getroot()
        rules_run.update(c.findtext("name").strip("'") for c in db.iter("category") if c.findtext("name"))
        for it in db.iter("item"):
            rule = (it.findtext("category") or "").strip("'")
            cell = it.findtext("cell") or ""
            per_rule[rule] += 1
            per_cell["OpenRAM macro" if cell.startswith("sky130_sram_") else "rest of the chip"] += 1
        t = (d / f"{prefix}{deck}.time").read_text()
        assert "Exit status: 0" in t, f"{deck} did not finish cleanly"
        wall[deck] = re.search(r"Elapsed \(wall clock\).*?: (\S+)", t)[1]
    return {"rule_names_in_reports": len(rules_run), "markers_total": sum(per_rule.values()),
            "markers_by_rule": dict(per_rule.most_common()), "markers_by_location": dict(per_cell),
            "wall_time_per_job": wall}


def main() -> None:
    orig, fixed = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    out = {
        "deck": "SKY130 KLayout DRC runset (ORFS sky130hd), FEOL section, deep mode",
        "rule_checks_enabled": 266,
        "rule_not_run": {"vpp.5": "the vpp layer (82/64) holds no shape in the GDS, so the rule cannot fire"},
        "signed_off_gds": summarize(orig, "rest_"),
        "after_implant_fix": summarize(fixed, "chip_"),
        "implant_fix": "scripts/implant_fix.py closes nsdm/psdm gaps < 0.38 um and npc gaps < 0.27 um inside "
                       "the OpenRAM macros only; scripts/verify_untouched.py finds every other (cell, layer) "
                       "pair identical",
    }
    if len(sys.argv) > 4:
        for key, gds in (("signed_off_gds_sha256", sys.argv[3]), ("corrected_gds_sha256", sys.argv[4])):
            out[key] = hashlib.sha256(pathlib.Path(gds).read_bytes()).hexdigest()
    p = ROOT / "results/fullchip/feol_drc.json"
    p.write_text(json.dumps(out, indent=2) + "\n")
    print(p.read_text())


if __name__ == "__main__":
    main()

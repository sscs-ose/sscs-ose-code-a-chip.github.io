"""Collect the runs of rc_corners.sh into one JSON file. Every value is read from the STA logs, the SPEF files, the rule files or the
PDK's SPICE models.   usage: rc_collect.py <out dir of the runs> <result.json> <PDK dir> <ORFS rule file>
SPDX-License-Identifier: Apache-2.0"""
import json
import pathlib
import re
import sys

OUT, DST, PDK, ORFS = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[4])
RULES = PDK / "libs.tech/openlane"
SETS = {
    "orfs": "flow rules (rcx_patterns.rules), the sign-off extraction repeated as a control",
    "nom": "PDK rules.openrcx.sky130A.nom.spef_extractor", "min": "PDK rules.openrcx.sky130A.min.spef_extractor",
    "max": "PDK rules.openrcx.sky130A.max.spef_extractor",
    "mnom": "PDK rules.openrcx.sky130A.nom.magic", "mmin": "PDK rules.openrcx.sky130A.min.magic",
    "mmax": "PDK rules.openrcx.sky130A.max.magic",
    "hi10": "sign-off parasitics, R x1.11, C x1.10", "hi15": "sign-off parasitics, R x1.15, C x1.15",
    "hi20": "sign-off parasitics, R x1.18, C x1.20", "hi30": "sign-off parasitics, R x1.30, C x1.30",
    "lo20": "sign-off parasitics, R x0.82, C x0.80", "lo30": "sign-off parasitics, R x0.70, C x0.70",
}


def total_cap(p):
    c, n = 0.0, 0
    with open(p) as f:
        for line in f:
            if line.startswith("*D_NET"):
                c += float(line.split()[2])
                n += 1
    return round(c, 1), n


def met2_row(p):
    """the first row of the met2-over-met1 table: spacing, coupling, fringe (pF/um), resistance"""
    t = pathlib.Path(p).read_text()
    m = re.search(r"Metal 2 OVER 1\s*\nDIST count \d+ width ([\d.]+)\s*\n([\d.e+-]+) ([\d.e+-]+) ([\d.e+-]+) ([\d.e+-]+)", t)
    return {"width_um": float(m[1]), "spacing_um": float(m[2]), "coupling_pF_per_um": float(m[3]), "fringe_pF_per_um": float(m[4])}


def r_param(name, corner):
    t = (PDK / f"libs.tech/ngspice/r+c/{corner}.spice").read_text()
    return float(re.search(rf"^\+\s*{name}\s*=\s*([\d.]+)", t, re.M)[1])


res = {"sta": "flow/final_sta.tcl, SoC I/O model, SPICE macro views, 40 ns clock",
       "rule_tables_met2_over_met1": {"flow": met2_row(ORFS), "spef_extractor_nom": met2_row(RULES / "rules.openrcx.sky130A.nom.spef_extractor"),
                                      "magic_nom": met2_row(RULES / "rules.openrcx.sky130A.nom.magic")},
       "pdk_resistance_ratio_high_low": {m: [round(r_param(f"r{m}", "res_high__cap_high") / r_param(f"r{m}", "res_typical__cap_typical"), 3),
                                             round(r_param(f"r{m}", "res_low__cap_low") / r_param(f"r{m}", "res_typical__cap_typical"), 3)]
                                         for m in ("m1", "m2", "m3", "m4", "m5")},
       "sets": {}}
for tag, desc in SETS.items():
    d = OUT / tag
    cap, nets = total_cap(d / "6_final.spef")
    row = {"rules": desc, "total_net_cap_pF": cap, "nets": nets, "corners": {}}
    for f in sorted(d.glob("sta_*.log")):
        t = f.read_text(errors="replace")
        g = lambda k: float(re.search(rf"^RESULT {k} (-?[\d.]+)", t, re.M)[1])
        row["corners"][f.stem[4:]] = {"setup_wns": g("setup_wns"), "hold_wns": g("hold_wns"),
                                      "setup_violating_endpoints": int(g("setup_violating_endpoints")),
                                      "hold_violating_endpoints": int(g("hold_violating_endpoints"))}
    res["sets"][tag] = row
DST.write_text(json.dumps(res, indent=1) + "\n")
print(f"RC_CORNERS sets {len(res['sets'])} written to {DST}")

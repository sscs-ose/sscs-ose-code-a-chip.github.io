#!/usr/bin/env python3
"""Fail-closed physical-verification status reporter.

Code-a-Chip does not require final layout. This script never labels DRC/LVS/PEX
PASS unless retained result artifacts explicitly exist.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def status():
    layout=ROOT/"layout"
    expected={
        "gds":layout/"ptat_core.gds",
        "drc_report":layout/"results"/"drc.json",
        "lvs_report":layout/"results"/"lvs.json",
        "pex_netlist":layout/"results"/"ptat_core_pex.spice",
    }
    present={k:p.is_file() for k,p in expected.items()}
    reports={}
    for key in ("drc_report","lvs_report"):
        if present[key]:
            try: reports[key]=json.loads(expected[key].read_text(encoding="utf-8"))
            except Exception: reports[key]={"status":"INVALID"}
    drc=reports.get("drc_report",{}).get("status")=="PASS"
    lvs=reports.get("lvs_report",{}).get("status")=="PASS"
    pex=present["pex_netlist"]
    return {
        "layout_present":present["gds"],
        "drc_status":"PASS" if drc else "NOT_CLAIMED",
        "lvs_status":"PASS" if lvs else "NOT_CLAIMED",
        "pex_status":"PRESENT" if pex else "NOT_CLAIMED",
        "eligible_code_a_chip_without_layout":True,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--require-layout",action="store_true")
    args=ap.parse_args()
    r=status()
    print(json.dumps(r,indent=2))
    if args.require_layout and not (r["layout_present"] and r["drc_status"]=="PASS" and r["lvs_status"]=="PASS" and r["pex_status"]=="PRESENT"):
        return 1
    return 0
if __name__=="__main__":
    raise SystemExit(main())

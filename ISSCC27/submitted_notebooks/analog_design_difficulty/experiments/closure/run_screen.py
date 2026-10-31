#!/usr/bin/env python3
"""Screen a named design on the declared screening set (CLOSURE_BRIEF.md Section 5)."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import shbench as sb
import parent_metric as pm
import designs

OUT = sb.REPO / "results" / "closure" / "screen"

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="+")
    ap.add_argument("--pvt", default="screen", choices=["screen", "nominal", "final", "screen+hot"])
    ap.add_argument("--seq", default="cal_alt,pair")
    ap.add_argument("--stress", action="store_true", help="command step at switch closure (STRESS timing)")
    ap.add_argument("--legacy", action="store_true",
                    help="pre-amendment screening of Section 3.2 / Figure 4: supplies 1.62/1.98 V, tmax 10 ps, reltol 1e-4")
    a = ap.parse_args()
    pvts = {"screen": pm.SCREEN_PVT, "nominal": pm.SCREEN_PVT[:1], "final": pm.FINAL_PVT,
            "screen+hot": pm.SCREEN_PVT + pm.STRESS_EXTRA_PVT}[a.pvt]
    OUT.mkdir(parents=True, exist_ok=True)
    for n in a.names:
        t = time.time()
        tm = sb.STRESS if a.stress else sb.Timing()
        so = sb.SimOpts()
        if a.legacy:
            pvts = [sb.PVT(p.corner, {1.60: 1.62, 1.95: 1.98}.get(p.vdd, p.vdd), p.temp) for p in pvts]
            so = sb.SimOpts(tmax=10e-12, reltol=1e-4, tstep_out=10e-12)
        res = pm.evaluate_many(designs.DESIGNS[n], pvts, include=tuple(a.seq.split(",")), tm=tm, so=so)
        (OUT / f"{n}_{a.pvt}{'_stress' if a.stress else ''}.json").write_text(json.dumps(res, indent=1))
        print(f"## {n} ({a.pvt}, {a.seq}{', STRESS' if a.stress else ''}) {time.time()-t:.0f}s")
        print(pm.table(res), flush=True)

if __name__ == "__main__":
    main()

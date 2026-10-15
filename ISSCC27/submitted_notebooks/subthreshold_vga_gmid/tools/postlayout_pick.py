#!/usr/bin/env python3
"""Post-layout verification of the pick, outside the notebook (same functions, same cache names the notebook reads).

The extracted netlist of the layout (layout/reports/pex/vga_core_12t_pex.spice: every transistor finger as drawn, with
the drain/source areas and perimeters of the layout, and every extracted capacitor) goes through the flow's SPICE gate
at every corner, noise at tt:

  x1     the extracted netlist as it is                                  -> cache/postlayout_verify.json
  x1.5   the same netlist with every extracted capacitor scaled by 1.5   -> cache/postlayout_verify_c1p5.json
         (a margin for extraction error; the transistors and their junctions are unchanged)
  equiv  the lumped output capacitance that makes the schematic match the extracted netlist's bandwidth at its
         bandwidth-critical corner, to compare with the allowance the sizes were frozen with
                                                                         -> cache/postlayout_equiv_cwire.json

  python tools/postlayout_pick.py            # computes only the caches that are missing
  python tools/postlayout_pick.py --rerun    # recomputes all three (ngspice + SKY130, about 20 minutes)
SPDX-License-Identifier: Apache-2.0
"""
import sys, re, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "tools"))
import os; os.chdir(ROOT)
import vga_flow as vf, evaluator as ev, flow, run_flow as rf, layout_flow as lf, nbutil as nu

LUT = ROOT / "cache" / "lut_sky130.npz"
PEX = lf.REPORTS / "pex" / "vga_core_12t_pex.spice"


def scaled_caps(src, k, dst):
    """A copy of an extracted netlist with every capacitor value multiplied by k (transistors untouched)."""
    out = []
    for line in Path(src).read_text().splitlines():
        t = line.split()
        if len(t) >= 4 and t[0][:1].upper() == "C":
            line = " ".join(t[:3] + [f"{k * lf._si(t[3]):.6g}"])
        out.append(line)
    Path(dst).write_text("\n".join(out) + "\n")
    return dst


def summary(tag, v):
    worst = min(v["corners"], key=lambda r: r["bw_min"])
    print(f"{tag}: {'PASS' if v['passed'] else 'FAIL ' + str(v['fails'])}; min bandwidth {v['bw_min']/1e3:.2f} kHz at "
          f"{worst['corner']}; min V_DS {1e3*v['vds_min']:.0f} mV; range >= {v['range_min']:.1f} dB; "
          f"I+3sigma max {1e6*v['i_eff_max']:.3f} uA; noise at tt {1e6*v['vrms']:.2f} uV", flush=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--rerun", action="store_true")
    a = ap.parse_args()
    nu.CAN_RUN = True
    flow._verify_init()
    SPEC, BASE = rf.SPECS["wire"], dict(vf.BASELINE)
    R12 = flow.run_flow(SPEC, "12T", LUT, BASE, spice=False, log=lambda *x: None)
    PV = R12["pick"]
    PICK = ev.materialise(BASE, PV["point"])
    print("pick:", PV["point"], flush=True)
    v1 = nu.cached("postlayout_verify", lambda: lf.post_layout(PICK, SPEC, PEX), a.rerun)
    summary("extracted x1  ", v1)
    s15 = scaled_caps(PEX, 1.5, vf.WORK / "vga_core_12t_pex_c1p5.spice")
    v15 = nu.cached("postlayout_verify_c1p5", lambda: lf.post_layout(PICK, SPEC, s15), a.rerun)
    summary("caps x1.5     ", v15)
    # the final layout's wiring as a lumped output capacitance, at its bandwidth-critical corner (compare spec.c_wire)
    import wiring
    crit = min(v1["corners"], key=lambda r: r["bw_curve"][-1])["corner"].split("/")
    cor = (crit[0], float(crit[1]), float(crit[2][:-1]) if len(crit) > 2 else 1.8)
    eq = nu.cached("postlayout_equiv_cwire", lambda: dict(wiring.fit_to_netlist(PICK, SPEC, PEX, cor), point=PV["point"]), a.rerun)
    print(f"final layout = {1e15*eq['c_equiv']:.0f} fF of lumped output wiring at {eq['corner']} "
          f"(the sizes were frozen with an allowance of {1e15*eq['c_allowance']:.0f} fF)", flush=True)


if __name__ == "__main__":
    main()

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

  rc     the extraction with resistance (layout/reports/pex/vga_core_12t_pex_rc.spice, layout/generator/pex_rc.py): the
         same gate at the corners that bound the x1 result (lowest bandwidth, lowest headroom, lowest range, highest
         current), with ngspice's KLU solver, and the noise at tt      -> cache/postlayout_verify_rc.json

  python tools/postlayout_pick.py            # computes only the caches that are missing
  python tools/postlayout_pick.py --rerun    # recomputes x1, x1.5 and equiv (ngspice + SKY130, about 20 minutes)
  python tools/postlayout_pick.py --rc       # adds the RC check (several hours: about an hour per corner and process)
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
PEX_RC = lf.REPORTS / "pex" / "vga_core_12t_pex_rc.spice"


def bounding_corners(v):
    """{corner: what it bounds} for a gate result: the corners with the lowest bandwidth, headroom and range and the
    highest supply current."""
    out = {}
    for key, f, what in (("bw_min", min, "bandwidth"), ("vds_min", min, "headroom"), ("range_db", min, "control range"),
                         ("i_tot", max, "supply current")):
        out.setdefault(f(v["corners"], key=lambda r: r[key])["corner"], []).append(what)
    return out


def rc_check(pick, spec, v1, workers=3):
    """The gate's corner simulation (flow.spice_gate) on the RC netlist at the bounding corners of v1 (KLU solver), and
    the noise at tt where the gate takes it (ngspice's noise analysis runs only with its default solver)."""
    from dataclasses import asdict
    from multiprocessing import Pool
    sp = flow.Spec(**{**asdict(spec), "c_wire": 0.0})           # as layout_flow.post_layout: the extraction carries the wiring
    p = dict(pick, subckt=(str(PEX_RC), lf.TOP), klu=True)
    bounds = bounding_corners(v1)
    with Pool(workers, initializer=flow._verify_init) as pool:     # each worker its own ngspice directory
        out = pool.map(_rc_job, [(name, p, sp) for name in bounds] + [("noise", p, sp)])
    return dict(netlist=str(PEX_RC.relative_to(lf.ROOT)), bounds=bounds, corners=out[:-1], noise=out[-1])


def _rc_job(args):
    name, p, sp = args
    if name == "noise":
        nz = vf.noise(dict(p, corner="tt", temp=27), 0.3, *sp.band)
        return dict(corner="tt/27", vrms=nz["vrms"], vn_1k=nz["vn_1k"], vn_10k=nz["vn_10k"])
    c, t, *v = name.split("/")
    q = dict(p, vdd=float(v[0][:-1])) if v else p
    r = flow.spice_gate(q, c, float(t), sp, noise=False); r["corner"] = name
    return r


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
    ap.add_argument("--rc", action="store_true", help="also run the RC-extracted netlist at the bounding corners (hours)")
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
    if a.rc and PEX_RC.exists():
        vr = nu.cached("postlayout_verify_rc", lambda: rc_check(PICK, SPEC, v1), a.rerun)
        for r in vr["corners"]:
            c = next(x for x in v1["corners"] if x["corner"] == r["corner"])
            print(f"RC {r['corner']:12s} ({', '.join(vr['bounds'][r['corner']])}): bandwidth {r['bw_min']/1e3:.2f} kHz (C only "
                  f"{c['bw_min']/1e3:.2f}), headroom {1e3*r['vds_min']:.0f} mV ({1e3*c['vds_min']:.0f}), range {r['range_db']:.1f} dB "
                  f"({c['range_db']:.1f})", flush=True)
        print(f"RC noise at tt: {1e6*vr['noise']['vrms']:.3f} uV (C only {1e6*v1['vrms']:.3f})", flush=True)


if __name__ == "__main__":
    main()

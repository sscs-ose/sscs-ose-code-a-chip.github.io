#!/usr/bin/env python3
"""Layout in the loop, outside the notebook (same functions, same caches the notebook reads). The extracted netlist of
a first layout of the 12T supplies the wiring capacitance:

  --fit     the lumped output capacitance that reproduces the extraction's effect on the first pass's pick
            (bisection at its bandwidth-critical corner)                           -> cache/wire_fit.json
            tools/run_flow.py --spec wire then reruns the flow with it (flow.wire_spec).
  --sens    which extracted capacitors matter (groups added alone, one corner)    -> cache/wire_sensitivity.json
  --budget  the largest v_out wiring the first pass's pick tolerates              -> cache/wire_budget_table2.json
  --search  the extracted capacitors on the first pass's verified designs, in pick-rule order
                                                                                   -> cache/wire_search_table2.json
  default   for the pick of --spec (default: the wire-aware run): write the LVS netlist and the sizes file to --out,
            and rerun the 24-corner gate with every extracted capacitor added, scaled by --scale
                                                                                   -> cache/pick_wiring_cap[_<spec>].json

  python tools/freeze_pick.py --pex cache/prev_layout_pex.spice [--fit | --sens | --budget | --search]
  python tools/freeze_pick.py --pex cache/prev_layout_pex.spice [--spec wire] [--scale 1 1.5] [--out layout]
SPDX-License-Identifier: Apache-2.0
"""
import sys, json, time, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import os; os.chdir(ROOT)
import vga_flow as vf, evaluator as ev, flow, run_flow as rf, report as rep, layout_flow as lf, nbutil as nu

LUT = ROOT / "cache" / "lut_sky130.npz"


from wiring import caps_of, with_caps, rule_order, hot_corners, search, budget, fit_c_wire, sensitivity, check


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pex", required=True)
    ap.add_argument("--scale", type=float, nargs="+", default=[1.0, 2.0])
    ap.add_argument("--search", action="store_true")
    ap.add_argument("--budget", action="store_true")
    ap.add_argument("--fit", action="store_true", help="fit the lumped output wiring capacitance (cache/wire_fit.json)")
    ap.add_argument("--sens", action="store_true", help="which extracted capacitors matter (cache/wire_sensitivity.json)")
    ap.add_argument("--spec", default="wire", choices=list(rf.SPECS))
    ap.add_argument("--out", default="layout", help="where the LVS netlist and sizes file go")
    a = ap.parse_args()
    if a.search or a.budget or a.fit or a.sens:          # these study the first pass's pick (Table 2 spec)
        a.spec = "table2"
    nu.CAN_RUN = True
    flow._verify_init()                    # a private ngspice work directory: safe next to other runs
    SPEC, BASE = rf.SPECS[a.spec], dict(vf.BASELINE)
    sfx = "" if a.spec == "wire" else f"_{a.spec}"
    out = ROOT / a.out
    from dataclasses import asdict
    CHK = flow.Spec(**{**asdict(SPEC), "c_wire": 0.0})       # the extracted capacitors replace the lumped allowance
    R12 = flow.run_flow(SPEC, "12T", LUT, BASE, spice=False, log=lambda *x: None)
    if a.search:
        r = search(R12, SPEC, BASE, caps_of(a.pex))
        (ROOT / "cache" / "wire_search_table2.json").write_text(json.dumps(r, indent=1)); return
    if a.sens:
        PV = R12["pick"]; p = ev.materialise(BASE, PV["point"])
        crit = min(PV["corners"], key=lambda r: r["bw_curve"][-1])
        parts = crit["corner"].split("/")
        cor = (parts[0], float(parts[1]), float(parts[2][:-1]) if len(parts) > 2 else 1.8)
        r = sensitivity(p, CHK, caps_of(a.pex), cor); r["point"] = PV["point"]
        (ROOT / "cache" / "wire_sensitivity.json").write_text(json.dumps(r, indent=1)); return
    if a.fit:
        PV = R12["pick"]; p = ev.materialise(BASE, PV["point"])
        crit = min(PV["corners"], key=lambda r: r["bw_curve"][-1])          # where the lowest gain step is slowest
        parts = crit["corner"].split("/")
        cor = (parts[0], float(parts[1]), float(parts[2][:-1]) if len(parts) > 2 else 1.8)
        r = fit_c_wire(p, CHK, caps_of(a.pex), cor)
        r.update(point=PV["point"], source=a.pex)
        (ROOT / "cache" / "wire_fit.json").write_text(json.dumps(r, indent=1))
        print(f"lumped output wiring {1e15*r['c_wire']:.0f} fF reproduces the extraction at {r['corner']}: "
              f"{r['bw_extracted']/1e3:.2f} kHz extracted, {r['bw_lumped']/1e3:.2f} kHz lumped, {r['bw_schematic']/1e3:.2f} kHz schematic")
        return
    if a.budget:
        r = budget(R12["pick"], CHK, BASE, caps_of(a.pex))
        (ROOT / "cache" / "wire_budget_table2.json").write_text(json.dumps(r, indent=1)); return
    PV = R12["pick"]
    PICK = ev.materialise(BASE, PV["point"])
    out.mkdir(parents=True, exist_ok=True)
    NET = rep.subckt(PICK, "vga_core_12t")
    (out / "vga_core_12t.spice").write_text(NET)
    (out / "vga_core_12t_sizes.json").write_text(json.dumps(rep.sizes(PICK), indent=1))
    print(f"wrote {a.out}/vga_core_12t.spice and {a.out}/vga_core_12t_sizes.json for", PV["point"], flush=True)
    caps = caps_of(a.pex)
    node = {}
    for x, y, v in caps:
        for n in (x, y):
            node[n] = node.get(n, 0.0) + v
    print("extracted wiring capacitance per node (fF):", {n: round(1e15 * v, 1) for n, v in sorted(node.items())}, flush=True)
    res = check(PICK, SPEC, caps, a.scale, PV["corners"])
    res.update(source=str(a.pex), schematic=dict(bw_min=PV["bw_min"], vrms=PV["vrms"]))
    for k, r in res["runs"].items():
        print(f"wiring caps x{k}: {'PASS' if r['passed'] else 'FAIL ' + str(r['fails'])}; min bandwidth {r['bw_min']/1e3:.2f} kHz "
              f"at {r['worst_corner']}; noise {1e6*r['vrms']:.2f} uV", flush=True)
    (ROOT / "cache" / f"pick_wiring_cap{sfx}.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()

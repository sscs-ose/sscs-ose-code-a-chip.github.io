"""Error budget of HSKEM-2's energy per decapsulation (plan item 1.2): the point value and what each known source of error
can move it by, from the committed results.

    energy_budget.py <results/fullchip> <out.json> [--flop-annotated-logic-mw X] [--shadow-full-fix-logic-mw Y]
                     [--glitch-fraction G]

Terms (typical corner, 25 MHz, the first profiled decapsulation):
  logic, from power.json (zero-delay activity of the routed netlist through the shadow):
    * pin annotation: the change when every flip-flop data pin gets its measured activity instead of OpenSTA's default
      (--flop-annotated-logic-mw, from scripts/flop_pin_activity.py; plan item 1.4);
    * shadow mapping: the change after the shadow's two mapping fixes (--shadow-full-fix-logic-mw; plan item 1.3);
    * glitches: zero-delay activity counts none; plan item 2.1 measures them on routed blocks (timed simulation with
      the SDF delays, scripts/run_gls_power*.sh GLS_DELAY=sdf) as extra combinational power, a fraction of the
      zero-delay value; --glitch-fraction lo hi applies the measured range to the chip's combinational power;
  SRAM, from sram_energy.json: the macro types without their own flat layout use the mean wiring factor; the bound
    applies the smallest and the largest measured factor to the whole energy of those macros (conservative: the factor
    belongs to the access cycles only).
SPDX-License-Identifier: Apache-2.0
"""
import argparse
import json
import pathlib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results"); ap.add_argument("out")
    ap.add_argument("--flop-annotated-logic-mw", type=float)
    ap.add_argument("--shadow-full-fix-logic-mw", type=float)
    ap.add_argument("--glitch-fraction", type=float, nargs="+", help="extra combinational power from glitches as a fraction of the zero-delay value: one value or a low and a high")
    a = ap.parse_args()
    r = pathlib.Path(a.results)
    p = json.loads((r / "power.json").read_text()); s = json.loads((r / "sram_energy.json").read_text())
    t_us = p["window_cycles"] * p["clock_ns"] * 1e-3            # window duration in microseconds
    uj = lambda mw: mw * t_us * 1e-3                               # mW over the window -> uJ
    logic_mw = p["logic_power_mw"]; logic = uj(logic_mw)
    sram = s["sram_energy_per_decaps_uj"]
    wf = s["wiring_factor"]; mean = wf["mean"]["access"]
    fac = [v["access"] for v in wf["per_macro"].values()]
    part = sum(i["energy_uj"] for i in s["instances"].values()
               if s["masters"][i["master"]]["wiring_factor"].startswith("mean"))
    terms = []
    if a.flop_annotated_logic_mw is not None:      # measured on top of the fixed shadow when that run is given
        base = a.shadow_full_fix_logic_mw if a.shadow_full_fix_logic_mw is not None else logic_mw
        terms.append({"term": "flip-flop pins at OpenSTA defaults (now annotated)", "part": "logic",
                      "delta_uj": round(uj(a.flop_annotated_logic_mw - base), 4)})
    if a.shadow_full_fix_logic_mw is not None:
        terms.append({"term": "shadow mapping (array and one-hot fixes)", "part": "logic",
                      "delta_uj": round(uj(a.shadow_full_fix_logic_mw - logic_mw), 4)})
    comb = uj(p["power_mw"]["combinational"])
    g = {"term": "glitches (not in zero-delay activity)", "part": "logic",
         "uj_per_10pct_extra_combinational": round(0.1 * comb, 4)}
    if a.glitch_fraction is not None:
        gl, gh = min(a.glitch_fraction), max(a.glitch_fraction)
        g["glitch_fraction"] = [gl, gh]; g["delta_uj_range"] = [round(gl * comb, 4), round(gh * comb, 4)]
    terms.append(g)
    terms.append({"term": "SRAM wiring factor of the types without their own layout", "part": "sram",
                  "macros_share_of_sram": round(part / sram, 3),
                  "range_uj": [round(sram - part + part * min(fac) / mean, 4), round(sram - part + part * max(fac) / mean, 4)],
                  "factor_range": [round(min(fac), 3), round(max(fac), 3)], "factor_used": round(mean, 3)})
    total = logic + sram
    lo = total + sum(min(0, t.get("delta_uj", 0)) for t in terms if t["part"] == "logic") + (terms[-1]["range_uj"][0] - sram)
    hi = total + sum(max(0, t.get("delta_uj", 0)) for t in terms if t["part"] == "logic") + (terms[-1]["range_uj"][1] - sram)
    if "delta_uj_range" in g:                      # glitches only add energy
        lo, hi = lo + g["delta_uj_range"][0], hi + g["delta_uj_range"][1]
    res = {"corner": p["corner"], "clock_ns": p["clock_ns"], "window_cycles": p["window_cycles"],
           "point_uj": {"logic": round(logic, 3), "sram": round(sram, 3), "total": round(total, 3)},
           "terms": terms, "range_uj": [round(lo, 3), round(hi, 3)],
           "open": [] if a.glitch_fraction is not None else ["glitches: measured by plan item 2.1; the range excludes them"]}
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1) + "\n"); print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()

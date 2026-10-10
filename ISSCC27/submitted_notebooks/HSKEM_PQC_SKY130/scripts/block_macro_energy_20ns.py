"""Macro energy of the four block-level design points that use an SRAM macro, at the blocks' own 20 ns clock.

The block-level GLS summaries (results/gls_power/<point>/summary.json, scripts/run_gls_power.sh) price the macro's
accesses with the energies of results/fullchip/sram_energy.json, which were measured at the chip's 40 ns clock. A macro
cycle costs less at 20 ns (the part of its energy that is static current grows with the period), so those summaries
overstate the macro share of the blocks. This script prices the same access counts with transistor-level energies
measured at 20 ns: three writes, three reads at new addresses and three reads of one address of the schematic netlist
(ngspice, SRAM_ENERGY_T_NS=20), scaled by a wiring factor from a flat layout extraction simulated at 20 ns and, for the
same accesses, a schematic run (so that the data of the two runs are the same).
usage: python3 block_macro_energy_20ns.py <sram_sweep dir> <out.json>
  <sram_sweep dir> holds T20_distinct, T20_repeat, flat_T20 and sch_T20_n1 (<macro>/energy.json each)
SPDX-License-Identifier: Apache-2.0
"""
import json
import pathlib
import statistics as st
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sweep, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
load = lambda d, m: json.loads((sweep / d / m / "energy.json").read_text())
POINTS = {"ntt_macro_20ns": "sky130_sram_1rw_16x256_wpr8", "ntt_opt_pipe_macro_20ns": "sky130_sram_1rw_16x256_wpr8",
          "ntt_packed_20ns": "sky130_sram_1rw_24x128", "ntt_packed2_20ns": "sky130_sram_1rw_24x128"}
masters = {}
for m in sorted(set(POINTS.values())):
    s, r, f, s1 = load("T20_distinct", m), load("T20_repeat", m), load("flat_T20", m), load("sch_T20_n1", m)
    for x in (s, r, f, s1):
        assert all(x["reads_correct"]), f"{m}: wrong read data"
    acc = lambda x: st.mean(x["read_pj"] + x["write_pj"])
    fa, fi = acc(f) / acc(s1), min(f["idle_pj"]) / min(s1["idle_pj"])
    masters[m] = {"read_pj": st.mean(s["read_pj"]) * fa, "read_repeat_pj": st.mean(r["read_pj"]) * fa,
                  "write_pj": st.mean(s["write_pj"]) * fa, "idle_pj": min(s["idle_pj"]) * fi,
                  "wiring_factor": {"access": fa, "idle": fi},
                  "schematic_pj": {"read": st.mean(s["read_pj"]), "read_repeat": st.mean(r["read_pj"]),
                                   "write": st.mean(s["write_pj"]), "idle": min(s["idle_pj"])},
                  "flat_pj": {"write": f["write_pj"][0], "read": f["read_pj"][0], "idle": f["idle_pj"]},
                  "schematic_same_data_pj": {"write": s1["write_pj"][0], "read": s1["read_pj"][0], "idle": s1["idle_pj"]}}
res = {"clock_ns": 20.0, "supply_v": 1.8, "corner": "tt, 25 C",
       "method": "see the header of scripts/block_macro_energy_20ns.py", "masters": masters, "points": {}}
for point, m in POINTS.items():
    g = json.loads((ROOT / "results/gls_power" / point / "summary.json").read_text())
    a, e = g["macro_accesses"], masters[m]
    macro_nj = 1e-3 * (a["writes"] * e["write_pj"] + a["reads_new_address"] * e["read_pj"]
                       + a["reads_same_address"] * e["read_repeat_pj"] + a["idle"] * e["idle_pj"])
    res["points"][point] = {"logic_nj": g["logic_energy_per_forward_ntt_nj"], "macro_nj_at_40ns_energies": g["macro_energy_nj"],
                            "macro_nj_at_20ns": macro_nj, "total_nj_at_40ns_energies": g["energy_per_forward_ntt_nj"],
                            "total_nj_at_20ns": g["logic_energy_per_forward_ntt_nj"] + macro_nj,
                            "macro_share_at_40ns_energies": g["macro_energy_nj"] / g["energy_per_forward_ntt_nj"],
                            "macro_share_at_20ns": macro_nj / (g["logic_energy_per_forward_ntt_nj"] + macro_nj)}
out.write_text(json.dumps(res, indent=1) + "\n")
for p, v in res["points"].items():
    print(f"{p:26s} macro {v['macro_nj_at_40ns_energies']:6.1f} -> {v['macro_nj_at_20ns']:6.1f} nJ, total {v['total_nj_at_40ns_energies']:6.1f} -> {v['total_nj_at_20ns']:6.1f} nJ,"
          f" macro share {v['macro_share_at_40ns_energies']:.2f} -> {v['macro_share_at_20ns']:.2f}")
for m, e in masters.items():
    print(m, {k: round(v, 3) for k, v in e["wiring_factor"].items()}, {k: round(e[k], 2) for k in ("read_pj", "read_repeat_pj", "write_pj", "idle_pj")})

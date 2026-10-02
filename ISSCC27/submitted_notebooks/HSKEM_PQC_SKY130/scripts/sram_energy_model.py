"""Energy of the chip's SRAM macros over one decapsulation, from transistor-level simulation of the macros.

The macros' Liberty power views come from OpenRAM's analytical model and are not physical (notebook, Section 8).
Each macro was instead simulated whole in ngspice (scripts/sram_energy_spice.sh): idle cycles, three
writes and three reads at the chip's 25 MHz clock, with the energy of every cycle integrated from the
supply current (results/fullchip/sram_macro_spice.json). Per macro this gives
  E_read, E_write  mean of the three measured accesses (reads at new addresses);
  E_read_repeat    mean of three reads of one address, from a second run (the chip's macros mostly
                   read the same address again);
  E_idle           a deselected cycle (clock running, chip select inactive): the lower of the two idle
                   cycles measured, since the first can still hold the end of the power-up transient.
Macros without a finished simulation are interpolated linearly in the number of rows from the macros of
the same word width (the access energy depends mainly on the word width).
The simulations use the schematic netlist, which has no wiring. Macros simulated again from a flat
extraction of their layout (devices plus every net's capacitance; "flat_layout" in the results) give a
wiring factor, flat over schematic, for the access energies and for the idle cycle; the mean factor of
those macros scales every macro.

Every macro performs one access per cycle on the chip (chip select tied active), so the energy of a
decapsulation is reads x E_read + writes x E_write per macro (results/fullchip/sram_accesses.json), the
reads at a new address at E_read and the rest at E_read_repeat. The
projection with chip-select gating keeps the useful accesses (a write, or a read at a new address) and
charges E_idle for every other cycle.
usage: python3 sram_energy_model.py <sram_macro_spice.json> <sram_accesses.json> <out.json>
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import json
import re
import statistics
import sys


def shape(m: str) -> tuple[int, int]:
    w, r = re.search(r"1rw_(\d+)x(\d+)", m).groups()
    return int(w), int(r)


def per_access(sim: dict) -> dict:
    return {"read_pj": statistics.mean(sim["read_pj"]), "read_repeat_pj": statistics.mean(sim["read_repeat_pj"]),
            "write_pj": statistics.mean(sim["write_pj"]), "idle_pj": min(sim["idle_pj"]), "source": "simulated"}


def interpolate(m: str, known: dict) -> dict:
    w, r = shape(m)
    same = sorted((shape(k)[1], v) for k, v in known.items() if shape(k)[0] == w)
    if len(same) < 2:
        raise SystemExit(f"{m}: needs two simulated macros of word width {w}")
    (r0, a), (r1, b) = same[0], same[-1]
    f = (r - r0) / (r1 - r0)
    out = {k: a[k] + f * (b[k] - a[k]) for k in ("read_pj", "read_repeat_pj", "write_pj", "idle_pj")}
    out["source"] = f"interpolated in rows from {w}x{r0} and {w}x{r1}"
    return out


def wiring_factors(spice: dict) -> dict:
    per = {}
    for m, f in spice.get("flat_layout", {}).get("macros", {}).items():
        assert all(f["reads_correct"]), f"{m}: a simulated read of the flat layout returned wrong data"
        s = spice["macros"][m]
        acc = lambda x: statistics.mean(x["read_pj"] + x["write_pj"])
        per[m] = {"access": acc(f) / acc(s), "idle": min(f["idle_pj"]) / min(s["idle_pj"])}
    mean = {k: statistics.mean(v[k] for v in per.values()) if per else 1.0 for k in ("access", "idle")}
    return {"per_macro": per, "applied": mean}


def main(spice_file: str, acc_file: str, out: str) -> None:
    spice, acc = json.load(open(spice_file)), json.load(open(acc_file))
    for m, s in spice["macros"].items():
        assert all(s["reads_correct"]), f"{m}: a simulated read returned wrong data"
    known = {m: per_access(s) for m, s in spice["macros"].items()}
    masters = sorted({v["master"] for v in acc["instances"].values()})
    per = {m: dict(known[m]) if m in known else interpolate(m, known) for m in masters}
    wiring = wiring_factors(spice)
    for e in per.values():
        for k in ("read_pj", "read_repeat_pj", "write_pj"):
            e[k] *= wiring["applied"]["access"]
        e["idle_pj"] *= wiring["applied"]["idle"]
    tot = gated = 0.0
    inst = {}
    n = acc["window_cycles"]
    for name, v in acc["instances"].items():
        e = per[v["master"]]
        u = v["useful_accesses"]
        ea = ((u - v["writes"]) * e["read_pj"] + (v["reads"] - u + v["writes"]) * e["read_repeat_pj"]
              + v["writes"] * e["write_pj"])
        eg = (u - v["writes"]) * e["read_pj"] + v["writes"] * e["write_pj"] + (n - u) * e["idle_pj"]
        inst[name] = {"master": v["master"], "energy_uj": ea * 1e-6, "energy_with_chip_select_gating_uj": eg * 1e-6}
        tot += ea
        gated += eg
    res = {"window_cycles": n, "supply_v": spice["supply_v"], "clock_ns": spice["clock_ns"], "wiring_factor": wiring,
           "masters": {m: {k: (round(x, 3) if isinstance(x, float) else x) for k, x in e.items()} for m, e in per.items()},
           "instances": inst, "sram_energy_per_decaps_uj": tot * 1e-6,
           "sram_energy_with_chip_select_gating_uj": gated * 1e-6,
           "method": spice["method"] + "; per-instance access counts from the full-system simulation; "
                     "see scripts/sram_energy_model.py"}
    json.dump(res, open(out, "w"), indent=2)
    for m, e in per.items():
        print(f"{m:30s} read {e['read_pj']:6.1f} / {e['read_repeat_pj']:6.1f} pJ  write {e['write_pj']:6.1f} pJ  idle {e['idle_pj']:4.1f} pJ  ({e['source']})")
    for m, f in wiring["per_macro"].items():
        print(f"wiring factor {m}: access {f['access']:.3f}, idle {f['idle']:.3f}")
    print(f"SRAM energy per decapsulation: {tot * 1e-6:.1f} uJ; with chip-select gating {gated * 1e-6:.2f} uJ")


if __name__ == "__main__":
    main(*sys.argv[1:4])

"""Why the wiring lowers the access energy of an OpenRAM macro: one read cycle with and without wiring.

Two ngspice runs of the flat layout extraction of one macro (scripts/sram_energy_spice.sh with
SRAM_FLAT_NETLIST and SRAM_ENERGY_ACCESSES=1), one with every parasitic capacitor and one with them all
removed, are repeated with `ngspice -b -r energy.raw` and the supply current saved; this script splits
the read cycle of each into its two clock phases and measures the current that is still flowing at the
end of the phase in which the wordline is on (the mean over its last 8 ns, when every node has settled).
usage: python3 sram_wiring_diag.py <with_capacitance/energy.raw> <without/energy.raw> <macro> <out.json>
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import json
import sys

import numpy as np

_trapz = getattr(np, "trapezoid", None) or np.trapz      # NumPy 2 renamed it
VDD, T, SETTLE, READ = 1.8, 40e-9, 3, 5          # deck of scripts/sram_energy_deck.py, one write and one read


def read_raw(path: str) -> dict:
    with open(path, "rb") as f:
        names = []
        while True:
            line = f.readline().decode("latin-1")
            if line.startswith("Variables:"):
                while True:
                    line = f.readline().decode("latin-1")
                    if line.startswith("Binary:"):
                        break
                    names.append(line.split()[1].lower())
            if line.startswith("Binary:"):
                data = np.frombuffer(f.read(), dtype=np.float64)
                break
    data = data[: (len(data) // len(names)) * len(names)].reshape(-1, len(names))
    return {k: data[:, i] for i, k in enumerate(names)}


def read_cycle(path: str) -> dict:
    d = read_raw(path)
    t, i = d["time"], -d["i(vvdd)"]
    t0 = READ * T + T / 2                          # rising edge that starts the read
    def energy(a, b):
        m = (t >= a) & (t <= b)
        return float(_trapz(i[m], t[m]) * VDD * 1e12)
    m = (t >= t0 + T - 8e-9) & (t <= t0 + T)
    return {"read_pj": energy(t0, t0 + T), "clock_high_phase_pj": energy(t0, t0 + T / 2),
            "wordline_phase_pj": energy(t0 + T / 2, t0 + T),
            "settled_current_wordline_on_ma": float(_trapz(i[m], t[m]) / (t[m][-1] - t[m][0]) * 1e3)}


def waveforms(path: str, step: float = 0.05e-9) -> dict:
    """The read cycle resampled on a uniform grid: supply current and the probed control nets."""
    d = read_raw(path)
    t0 = READ * T + T / 2
    grid = t0 + np.arange(0, T + step / 2, step)
    keep = {"i_mA": -d["i(vvdd)"] * 1e3}
    for k in ("clk0", "x0.dg_wl3", "x0.dg_p_en_bar", "x0.dg_bl3", "x0.dg_br3"):
        if f"v({k})" in d:
            keep[k.replace("x0.dg_", "")] = d[f"v({k})"]
    return {"t_ns": (grid - t0) * 1e9, **{k: np.interp(grid, d["time"], v) for k, v in keep.items()}}


def main(with_c: str, without_c: str, macro: str, out: str) -> None:
    res = {"macro": macro, "clock_ns": T * 1e9,
           "note": "read cycle of the flat layout extraction with and without its parasitic capacitors; the "
                   "wordline phase is the low half of the clock, during which OpenRAM keeps the wordline on",
           "with_wiring": read_cycle(with_c), "without_wiring": read_cycle(without_c)}
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(res, indent=1))
    # the waveforms behind it, for the notebook's figure (CSV next to the JSON)
    rows = []
    for label, path in (("with wiring", with_c), ("without wiring", without_c)):
        w = waveforms(path)
        for i in range(len(w["t_ns"])):
            rows.append([label] + [f"{w[k][i]:.4g}" for k in w])
    cols = ["netlist"] + list(waveforms(with_c).keys())
    with open(out.replace(".json", "_read_cycle.csv"), "w") as f:
        f.write(",".join(cols) + "\n" + "\n".join(",".join(r) for r in rows) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:5])

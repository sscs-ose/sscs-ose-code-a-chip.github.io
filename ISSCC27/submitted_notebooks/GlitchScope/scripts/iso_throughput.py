"""Iso-throughput comparison with supply scaling: what if each placement's timing slack is spent on a lower VDD?

Uses the corner study (data/pvt/pvt.json): for each -40 C voltage family of the PDK's Liberty corners (ss: 1.28-1.76 V,
ff: 1.56-1.95 V), each placement of the 16x16 multiplier runs at the lowest supply at which its critical path still
meets the clock (log-interpolated between characterised voltages, never below the lowest one), and its energy per
cycle is interpolated at that supply.  The clock is set to the original design's critical path at each characterised
voltage, so the original always runs at that voltage.  Dynamic energy only (leakage is not modelled).

    python scripts/iso_throughput.py      -> data/pvt/iso_throughput.json
"""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DESIGNS = ("original", "timing_driven", "glitchscope")


def main():
    P = json.loads((ROOT / "data/pvt/pvt.json").read_text())
    out = {}
    for fam in ("ss_n40C", "ff_n40C"):
        rows = sorted([r for k, r in P.items() if k.startswith(fam)], key=lambda r: float(r["corner"][-4:].replace("v", ".")))
        V = np.array([float(r["corner"][-4:].replace("v", ".")) for r in rows])

        def at(d, T):
            c = np.array([r[d]["critical_path_ps"] for r in rows])
            e = np.array([r[d]["total"] for r in rows])
            v = V.min() if T >= c.max() else float(np.interp(np.log(T), np.log(c[::-1]), V[::-1]))
            return dict(vdd=round(v, 3), energy_pJ=round(float(np.interp(v, V, e)) / 1e3, 2), at_lowest=bool(T >= c.max()))
        res = []
        for r in rows:
            T = r["original"]["critical_path_ps"]
            row = dict(clock_ns=round(T / 1e3, 2), **{d: at(d, T) for d in DESIGNS})
            for d in DESIGNS[1:]:
                row[d]["saving"] = round(1 - row[d]["energy_pJ"] / row["original"]["energy_pJ"], 3)
            res.append(row)
            print(f"{fam} clock {row['clock_ns']:6.2f} ns: " + "  ".join(
                f"{d} {row[d]['vdd']:.2f} V {row[d]['energy_pJ']:6.1f} pJ" + (f" ({100 * row[d]['saving']:.0f} %)" if d != "original" else "")
                for d in DESIGNS))
        out[fam] = res
    (ROOT / "data/pvt/iso_throughput.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

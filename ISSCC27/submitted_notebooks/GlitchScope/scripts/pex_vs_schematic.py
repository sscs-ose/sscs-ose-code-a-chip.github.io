"""How much do the PDK's schematic cell netlists differ from parasitic-extracted ones?
Single-cell ngspice sweeps (section 2 method) with both netlists: delay t_pd, full-cycle
energy E_full and the normalised pulse-rejection threshold r_filter = w_filter / t_pd.

    python scripts/pex_vs_schematic.py [cells...]     -> data/pdk/pex/pex_vs_schematic.json
"""
import itertools
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.spice.pulse_sweep import Condition, default_widths, run_condition  # noqa: E402

PEX = "data/pdk/pex/sky130_fd_sc_hd_pex.spice"


def summarise(rows):
    ref = max(rows, key=lambda r: r["w_set_ps"])
    tpd, efull = ref["t_pd_ps"], ref["energy_fJ"]
    passed = sorted(r["w_in_ps"] for r in rows if r["n_out_cross"] >= 2 and r["w_set_ps"] < ref["w_set_ps"])
    failed = [r["w_in_ps"] for r in rows if r["n_out_cross"] < 2 and r["w_in_ps"] == r["w_in_ps"]]
    lo = max([w for w in failed if not passed or w < passed[0]], default=0.0)
    wf = 0.5 * (lo + passed[0]) if passed else float("nan")
    return dict(t_pd_ps=tpd, E_full_fJ=efull, w_filter_ps=wf, r_filter=wf / tpd)


def main():
    cells = sys.argv[1:] or ["inv_1", "nor2_1", "nand2_1", "xor2_1"]
    out = []
    for cell, pol, slew, load in itertools.product(cells, ("pos", "neg"), (20, 100), (2.0, 10.0)):
        row = dict(cell=cell, polarity=pol, slew_ps=slew, load_ff=load)
        for tag in ("schematic", "pex"):
            if tag == "pex":
                os.environ["GS_CELL_SPICE"] = PEX
            else:
                os.environ.pop("GS_CELL_SPICE", None)
            row[tag] = summarise(run_condition(Condition(cell, pol, slew, load), default_widths()))
        s, p = row["schematic"], row["pex"]
        row["ratio"] = {k: p[k] / s[k] for k in ("t_pd_ps", "E_full_fJ", "r_filter")}
        out.append(row)
        print(f"{cell:8s} {pol} slew {slew:3d} load {load:4.1f}:  t_pd {s['t_pd_ps']:6.1f} -> {p['t_pd_ps']:6.1f} ps  "
              f"E_full {s['E_full_fJ']:6.2f} -> {p['E_full_fJ']:6.2f} fJ  r_filter {s['r_filter']:.2f} -> {p['r_filter']:.2f}",
              flush=True)
    for k in ("t_pd_ps", "E_full_fJ", "r_filter"):
        v = np.array([r["ratio"][k] for r in out])
        print(f"PEX / schematic {k}: median {np.median(v):.3f}, range {v.min():.3f}-{v.max():.3f}")
    p = ROOT / "data/pdk/pex/pex_vs_schematic.json"
    p.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

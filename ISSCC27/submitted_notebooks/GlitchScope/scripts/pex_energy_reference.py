"""Full-cycle energy E_full of every M2 calibration condition (12 cells x 2 polarities x
3 slews x 2 loads), simulated on the parasitic-extracted cell netlists.

The PDK's schematic cell netlists have no diffusion or wiring capacitance, so their
E_full is 8-31 % below the extracted cells' (scripts/pex_vs_schematic.py).  GlitchScope's
per-cell SPICE energy scaling (``spice_scale=True``, data/m2/liberty_vs_spice_energy.csv)
is referenced to these extracted-cell energies (scripts/compare_liberty_energy.py --pex).

    python scripts/pex_energy_reference.py      -> column E_full_pex_fJ in data/m2/m2_conditions.csv
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.spice.pulse_sweep import CELLS, W_REF, Condition, ensure_cells, run_condition  # noqa: E402

os.environ["GS_CELL_SPICE"] = "data/pdk/pex/sky130_fd_sc_hd_pex.spice"


def main():
    from glitchscope.liberty import parse_liberty_file
    from glitchscope.test_support import lib_path_or_none
    p = ROOT / "data/m2/m2_conditions.csv"
    c = pd.read_csv(p)
    ensure_cells(parse_liberty_file(lib_path_or_none()), list(c.cell.unique()))

    def one(r):
        inv = CELLS[r.cell][3]
        pol = ("neg" if r.polarity == "positive" else "pos") if inv else ("pos" if r.polarity == "positive" else "neg")
        return run_condition(Condition(r.cell, pol, int(r.slew_ps), float(r.load_ff)), [W_REF])[0]["energy_fJ"]
    with ThreadPoolExecutor(2) as ex:
        c["E_full_pex_fJ"] = list(ex.map(one, [r for _, r in c.iterrows()]))
    c.to_csv(p, index=False)
    print((c.E_full_pex_fJ / c.E_full_fJ).describe().round(3).to_string())


if __name__ == "__main__":
    main()

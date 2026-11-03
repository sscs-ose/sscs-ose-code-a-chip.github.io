"""Compare Liberty (internal_power + C*V^2) full-cycle energy with SPICE E_full.

    python scripts/compare_liberty_energy.py <liberty> [--pex]
--pex: SPICE reference = parasitic-extracted cells (column E_full_pex_fJ, scripts/pex_energy_reference.py);
otherwise the PDK's schematic cell netlists.  Writes the per-cell ratios used by spice_scale=True."""
import sys; from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import pandas as pd
from glitchscope.liberty_power import read_internal_power, internal_energy_pj
from glitchscope.spice.pulse_sweep import CELLS
L = sys.argv[1]
c = pd.read_csv(ROOT / 'data/m2/m2_conditions.csv')
P = read_internal_power(L, ['sky130_fd_sc_hd__' + k for k in CELLS])
rows = []
for k, (inp, out, side, inv) in CELLS.items():
    tabs = P['sky130_fd_sc_hd__' + k][(out, inp)]
    for _, r in c[c.cell == k].drop_duplicates(['slew_ps', 'load_ff']).iterrows():
        Cpf, s = r.load_ff * 1e-3, r.slew_ps * 1e-3
        e_int = (internal_energy_pj(tabs, True, s, Cpf) + internal_energy_pj(tabs, False, s, Cpf)) * 1e3
        rows.append(dict(cell=k, slew_ps=r.slew_ps, load_ff=r.load_ff,
                         E_spice_fJ=r.E_full_pex_fJ if "--pex" in sys.argv else r.E_full_fJ,
                         E_lib_fJ=e_int + Cpf * 1e3 * 1.8 ** 2, CV2_fJ=Cpf * 1e3 * 1.8 ** 2))
d = pd.DataFrame(rows); d['ratio'] = d.E_lib_fJ / d.E_spice_fJ
d.to_csv(ROOT / 'data/m2/liberty_vs_spice_energy.csv', index=False)
d.to_csv(ROOT / 'glitchscope/data/liberty_vs_spice_energy.csv', index=False)
print(d.groupby('cell')[['E_spice_fJ', 'E_lib_fJ', 'ratio']].median().round(2).to_string())
print('overall median ratio', round(d.ratio.median(), 2), 'range', round(d.ratio.min(), 2), round(d.ratio.max(), 2))

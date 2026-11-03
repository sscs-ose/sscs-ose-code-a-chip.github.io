"""SPICE pulse-survival calibration of another PDK (ngspice) -> bundled M2 model.

    python scripts/calibrate_pdk.py gf180mcu_7t_3v3        (paths in tools.env)
    python scripts/calibrate_pdk.py my_pdk.json            (any PDK, see docs/USING_YOUR_OWN_PDK.md)

Writes data/pdk/<pdk>/pulse_sweep.csv and glitchscope/data/<liberty library name>/
{m2_model.json, liberty_vs_spice_energy.csv, m2_conditions.csv}; GlitchScope then
uses this calibration automatically for that library.
"""
import sys, time, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from glitchscope.liberty import parse_liberty_file
from glitchscope.spice import pdk_sweep as P
import json as _json
arg = sys.argv[1]
t = time.time()
if arg.endswith(".json"):        # your own PDK: {"name", "liberty", "cell_spice", "model_lines", "vdd", ...}
    spec = P.prepare(P.PdkSpec(**_json.loads(Path(arg).read_text())))
else:
    spec = P.prepare(P.pdk_spec(arg))
name = spec.name
csv = ROOT / f"data/pdk/{name}/pulse_sweep.csv"
if not csv.exists() or "--force" in sys.argv:
    rows = P.sweep(spec)
    P.write_csv(rows, csv)
    print(f"{name}: {len(rows)} SPICE runs in {time.time() - t:.0f}s")
libname = parse_liberty_file(spec.liberty).name
out = ROOT / "glitchscope/data" / libname
cdf, model = P.fit(csv, out, spec)
shutil.copy(out / "m2_conditions.csv", csv.parent / "m2_conditions.csv")
print(cdf.groupby(["cell", "polarity"])[["r_filter", "r_full"]].median().round(2).to_string())
print(f"-> {out}")

"""SPICE pulse-filtering calibration (M2) of SKY130 HD at another process corner.

    python scripts/calibrate_corner.py ss_n40C_1v28 [ss] [-40] [1.28]

The corner's Liberty (from the PDK) and the matching ngspice model section, supply and
temperature are used; the eight basic cell functions are swept exactly as for the other
PDKs (scripts/calibrate_pdk.py).  Writes data/pdk/sky130_<corner>/pulse_sweep.csv and
glitchscope/data/sky130_fd_sc_hd__<corner>/m2_model.json, which GlitchScope then uses
automatically for that corner's Liberty.  A typical-corner run of the same reduced sweep
(``tt_025C_1v80``) gives the like-for-like reference (written to data/pdk/, not used
automatically).
"""
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.liberty import parse_liberty_file  # noqa: E402
from glitchscope.spice import pdk_sweep as P  # noqa: E402

corner = sys.argv[1]
m = re.match(r"(tt|ss|ff)_(n?\d+)C_(\d)v(\d+)", corner)
section = sys.argv[2] if len(sys.argv) > 2 else m.group(1)
temp = float(sys.argv[3]) if len(sys.argv) > 3 else float(m.group(2).replace("n", "-"))
vdd = float(sys.argv[4]) if len(sys.argv) > 4 else float(f"{m.group(3)}.{m.group(4)}")
pdk = Path(P._env("GS_PDK_ROOT"))
name = f"sky130_{corner}"
spec = P.PdkSpec(name, str(pdk / f"libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__{corner}.lib"),
                 str(pdk / "libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice"),
                 [f'.lib "{pdk / "libs.tech/ngspice/sky130.lib.spice"}" {section}'], vdd, temp_c=temp,
                 scale_option=True)
t = time.time()
spec = P.prepare(spec)
csv = ROOT / f"data/pdk/{name}/pulse_sweep.csv"
if not csv.exists() or "--force" in sys.argv:
    rows = P.sweep(spec)
    P.write_csv(rows, csv)
    print(f"{name}: {len(rows)} SPICE runs in {time.time() - t:.0f}s")
libname = parse_liberty_file(spec.liberty).name
# the typical corner keeps the full 12-cell calibration (data/m2_model.json): its reduced
# like-for-like reference fit is stored next to the sweep and not picked up automatically
out = (csv.parent / "fit") if corner == "tt_025C_1v80" else ROOT / "glitchscope/data" / libname
cdf, model = P.fit(csv, out, spec)
shutil.copy(out / "m2_conditions.csv", csv.parent / "m2_conditions.csv")
print(cdf.groupby(["cell", "polarity"])[["r_filter", "r_full"]].median().round(2).to_string())
print(f"-> {out}")

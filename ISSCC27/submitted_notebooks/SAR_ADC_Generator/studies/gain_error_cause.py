"""Cause test for the 8-bit post-layout gain error: endpoint offset / gain (1/32 LSB) of the extracted unit-cell CDAC
with only its top-plate-to-pg/ng coupling capacitors removed (build/diag/gainfix/cdacu8b_pex_nopgng.spice, made by
deleting those C lines from build/8bit/layout/pex/cdacu8b_pex.spice). Run inside IIC-OSIC-TOOLS from the project folder."""
import json, sys
from pathlib import Path
sys.path.insert(0, ".")
sys.argv = ["x"]
import studies.endpoint_transitions as ep
from sargen import SarSpec, netlist as nl
from sargen.flow import simulate_codes
b, lay = 8, Path("build/8bit/layout")
spec, d = SarSpec(bits=8), json.loads(Path("build/8bit/design.json").read_text())
pins = nl.subckt_pins(lay / "cdacu8b_ref.spice", "cdacu8b")
kw = dict(cdacsw=(nl.wrap_extraction("build/diag/gainfix/cdacu8b_pex_nopgng.spice", "cdacsw", pins), pins))
lsb, top = spec.lsb, 255
t = {}
for k, centre in ((1, lsb), (top, top * lsb)):
    codes, vin, _ = simulate_codes(spec, d, "ramp", 2 * ep.SPAN * ep.STEPS, Path(f"build/diag/gainfix/t{k}"), 16,
                                   ramp=(centre - ep.SPAN * lsb, lsb / ep.STEPS), **kw)
    t[k] = ep.first_reach(vin, codes, k)
off = (t[1] - lsb) / lsb
print(f"unit-cell CDAC without top-pg/ng coupling: offset {off:+.3f} LSB  gain {(t[top] - top * lsb) / lsb - off:+.3f} LSB")

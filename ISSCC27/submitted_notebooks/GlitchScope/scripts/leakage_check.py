"""Leakage energy per clock cycle of the 16x16 multiplier's placements, from the PDK Liberty cell_leakage_power,
at the corners of the voltage-aware study (and 100 C for reference): is 'dynamic energy only' a real omission?

    python scripts/leakage_check.py <PDK lib dir>      -> data/pvt/leakage.json
"""
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGNS = {"original": "bench/layout/mul16_v0.v", "timing_driven": "data/glitchfix/mul16_r/timing_driven.v",
           "glitchscope": "data/glitchfix/mul16_r/best_milp.v", "glitchscope_vdd": "data/glitchfix/mul16_vdd/T5500_milp.v"}
CORNERS = {"ss_n40C_1v28": 72.8, "ss_n40C_1v76": 18.24, "ff_n40C_1v56": 11.3, "ff_n40C_1v95": 7.13, "tt_100C_1v80": 13.9}


def main():
    libdir = Path(sys.argv[1])
    out = {}
    for corner, clk_ns in CORNERS.items():
        t = (libdir / f"sky130_fd_sc_hd__{corner}.lib").read_text()
        unit = {"1nW": 1e-9, "1uW": 1e-6, "1pW": 1e-12}[re.search(r'leakage_power_unit\s*:\s*"(\w+)"', t).group(1)]
        leak = {m.group(1): float(m.group(2)) * unit for m in
                re.finditer(r'cell \("(sky130_fd_sc_hd__\w+)"\)\s*\{.*?cell_leakage_power\s*:\s*([\d.eE+-]+)', t, re.S)}
        row = {}
        for k, f in DESIGNS.items():
            cnt = collections.Counter(re.findall(r"(sky130_fd_sc_hd__\w+) ", (ROOT / f).read_text()))
            p = sum(leak.get(c, 0.0) * n for c, n in cnt.items())
            row[k] = dict(leakage_nW=p * 1e9, energy_fJ_per_cycle=p * clk_ns * 1e-9 * 1e15)
        out[corner] = dict(clock_ns=clk_ns, designs=row)
        print(corner, {k: round(v["energy_fJ_per_cycle"], 4) for k, v in row.items()}, "fJ/cycle")
    (ROOT / "data/pvt/leakage.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

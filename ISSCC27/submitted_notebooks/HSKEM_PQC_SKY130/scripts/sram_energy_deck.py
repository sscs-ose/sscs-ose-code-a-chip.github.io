"""Transistor-level energy of one OpenRAM SKY130 macro per clock cycle: the HSKEM entry point of
toolkit/openram_energy/openram_energy.py (same arguments and environment; see that file).

usage: sram_energy_deck.py <netlist> <macro> <deck.sp> <pdk sky130.lib.spice>
       sram_energy_deck.py --parse <log> <macro> <out.json>
Imported as a module, it exposes the toolkit's functions (tests/test_analysis_scripts.py).
SPDX-License-Identifier: Apache-2.0
"""
import pathlib
import runpy
import sys

_TOOL = pathlib.Path(__file__).resolve().parents[1] / "toolkit" / "openram_energy" / "openram_energy.py"
if __name__ == "__main__":
    sys.argv[0] = str(_TOOL)
    runpy.run_path(sys.argv[0], run_name="__main__")
else:
    globals().update({k: v for k, v in runpy.run_path(str(_TOOL), run_name="openram_energy").items() if not k.startswith("__")})

"""Transistor-level energy of one OpenRAM SKY130 macro per clock cycle: the HSKEM entry point of
toolkit/openram_energy/openram_energy.py (same arguments and environment; see that file).

usage: sram_energy_deck.py <netlist> <macro> <deck.sp> <pdk sky130.lib.spice>
       sram_energy_deck.py --parse <log> <macro> <out.json>
SPDX-License-Identifier: Apache-2.0
"""
import pathlib
import runpy
import sys

sys.argv[0] = str(pathlib.Path(__file__).resolve().parents[1] / "toolkit" / "openram_energy" / "openram_energy.py")
runpy.run_path(sys.argv[0], run_name="__main__")

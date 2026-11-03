#!/usr/bin/env python3
"""Small data files the notebook's figure cells read (inputs that take hours to simulate, or need KLayout):
  results/4bit/layout/cdac_unit_layers.json  polygons of the 4-bit CDAC unit cell per layer (from the GDS, via KLayout)
  results/pdk/ron_curves.json                transmission-gate R_on * W vs. input voltage, 4 PVT points (build/char/ron*)
  results/8bit/sweeps/fin_codes.json         8-bit output codes of the input-frequency sweep (studies/coverage8.py)
Run from the project folder inside IIC-OSIC-TOOLS:  python3 docs/figures/export_figure_data.py
"""
import json, re, subprocess, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# unit-cell polygons: KLayout batch script writes them
subprocess.run(["klayout", "-b", "-r", "docs/figures/export_unitcell.py"], check=True)
Path("results/4bit/layout/cdac_unit_layers.json").write_text(Path("build/figures/unitcell_layers.json").read_text())

# transmission-gate on-resistance: 5 mV across the gate, current measured -> R * W (NMOS W = 1 um)
ron = {}
for d, lab in (("ron", "tt, 27 °C, 1.80 V"), ("ron_tt_27C_0.9", "tt, 27 °C, 1.62 V"),
               ("ron_ss_125C_1", "ss, 125 °C, 1.80 V"), ("ron_ss_-40C_1", "ss, −40 °C, 1.80 V")):
    a = np.loadtxt(f"build/char/{d}/ron.txt", skiprows=1)
    vdd = float(re.search(r"Vdd vdd 0 ([0-9.]+)", Path(f"build/char/{d}/tb.cir").read_text()).group(1))
    ron[lab] = dict(vdd=vdd, vin=a[:, 0].round(4).tolist(), std_kohm_um=(5e-3 / np.abs(a[:, 1]) / 1e3).round(4).tolist(),
                    lvt_kohm_um=(5e-3 / np.abs(a[:, 2]) / 1e3).round(4).tolist())
Path("results/pdk").mkdir(parents=True, exist_ok=True)
Path("results/pdk/ron_curves.json").write_text(json.dumps(ron))

# 8-bit codes of the input-frequency sweep, in conversion order
from sargen import SarSpec
from sargen.flow import _codes_from_wave
from sargen.netlist import Timing
from sargen.spice import read_wrdata
spec, fft_n = SarSpec(bits=8), 128
tim, base = Timing(8, spec.tclk), Path("build/8bit/studies/coverage")
fin = {}
for d in sorted(base.glob("fin_*"), key=lambda p: int(p.name[4:])):
    codes = []
    for ch in sorted(d.glob("chunk_*")):
        codes += _codes_from_wave(read_wrdata(ch / "wave.txt"), tim, min(32, fft_n - len(codes)), 8, spec.vdd).tolist()
    fin[d.name[4:]] = codes
Path("results/8bit/sweeps").mkdir(parents=True, exist_ok=True)
Path("results/8bit/sweeps/fin_codes.json").write_text(json.dumps(dict(fs=spec.fs, fft_n=fft_n, codes=fin)))
print({k: len(v) for k, v in fin.items()})

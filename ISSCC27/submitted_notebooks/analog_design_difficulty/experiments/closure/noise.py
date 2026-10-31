#!/usr/bin/env python3
"""Sampled random noise (CLOSURE_BRIEF.md Section 3, separate random budget).

Track-mode noise on Cs, integrated over frequency, with the driver in unity-gain feedback and the
sampling switch on (bootstrapped switch: main device with its gate at V + VDD; transmission gate:
static clock levels). When the switch opens, the voltage on Cs freezes, so the integrated track-mode
noise is the standard estimate of the sampled noise (it contains kT/C of the switch and the driver's
noise filtered by the closed-loop and switch-Cs bandwidth). Also reports kT/C alone for comparison.
"""
from __future__ import annotations

import math

import numpy as np
import shutil
import subprocess

import shbench as sb
from stability import _load_lines

OUT = sb.GENERATED / "noise"
K_B = 1.380649e-23


F_LOW = "1m"   # declared lower integration bound (CLOSURE_BRIEF.md amendment A2): 1 mHz


def netlist(design: sb.Design, pvt: sb.PVT, level: float, outdir, ideal_driver: bool = False) -> str:
    L = [f"* noise: {design.name} {pvt.tag} {level} V{' ideal noiseless driver' if ideal_driver else ''}",
         f'.lib "{sb.pdk_library()}" {pvt.corner}', f".temp {pvt.temp}",
         f'.include "{outdir / design.driver_file}"', ".option reltol=1e-5 sparse",
         f"VDD vdd 0 {pvt.vdd}", ("RIBa iba 0 1k" if ideal_driver else "") + f"\nIREFa vdd iba {design.iref}",
         f"VCa vca 0 dc {level} ac 1",
         (f"EDa oa 0 vca 0 1" if ideal_driver else f"XDa vca oa oa iba vdd 0 {design.driver_subckt}")]
    L += _load_lines(design, pvt, level, True, "a")
    # KLU does not support .noise in ngspice-42; the integrated total is computed in Python from the spectrum
    L += [".control", "option sparse", f"noise v(sampa) VCa dec 40 {F_LOW} 50G", "setplot previous",
          f"wrdata {outdir / 'onoise.dat'} onoise_spectrum", ".endc", ".end"]
    return "\n".join(L) + "\n"


def _integrated(design: sb.Design, pvt: sb.PVT, level: float, ideal_driver: bool) -> float:
    outdir = OUT / design.name / f"{pvt.tag}_{level:.2f}{'_ideal' if ideal_driver else ''}"
    outdir.mkdir(parents=True, exist_ok=True)
    shutil.copy(sb.NETLISTS / design.driver_file, outdir / design.driver_file)
    text = netlist(design, pvt, level, outdir, ideal_driver)
    nl = outdir / "noise.spice"
    log = outdir / "ngspice.log"
    if not (nl.is_file() and log.is_file() and nl.read_text() == text):
        nl.write_text(text)
        p = subprocess.run(["ngspice", "-b", str(nl)], cwd=sb.HERE, capture_output=True, text=True)
        log.write_text(p.stdout + p.stderr)
    d = np.loadtxt(outdir / "onoise.dat", ndmin=2)
    f, sv = d[:, 0], d[:, 1]
    ok = np.isfinite(sv)
    return float(np.sqrt(np.trapezoid(sv[ok] ** 2, f[ok])))


def run(design: sb.Design, pvt: sb.PVT, level: float) -> dict:
    """Held-sample noise with the switch counted as exactly kT/C (amendment A2).

    The SKY130 MOS noise model gives about 0.8 kT/C for a switch at Vds = 0 (audit R3), whereas a passive
    conductance in equilibrium must give exactly kT/C. The switch's model contribution is measured with an
    ideal noiseless driver and replaced by kT/C: v^2 = v_model^2 - v_switch_model^2 + kT/C.
    """
    v_model = _integrated(design, pvt, level, False)
    v_sw = _integrated(design, pvt, level, True)
    ktc = math.sqrt(K_B * (pvt.temp + 273.15) / design.cs)
    vn = math.sqrt(max(v_model ** 2 - v_sw ** 2, 0.0) + ktc ** 2)
    return {"design": design.name, "tag": pvt.tag, "level": level, "noise_uV_rms": vn * 1e6,
            "model_total_uV_rms": v_model * 1e6, "switch_model_uV_rms": v_sw * 1e6,
            "driver_uV_rms": math.sqrt(max(v_model ** 2 - v_sw ** 2, 0.0)) * 1e6,
            "ktc_uV_rms": ktc * 1e6, "noise_LSB_rms": vn / (0.6 / 1024)}

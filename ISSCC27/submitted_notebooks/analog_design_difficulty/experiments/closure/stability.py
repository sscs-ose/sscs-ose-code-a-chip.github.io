#!/usr/bin/env python3
"""Driver loop stability and operating-point margins (CLOSURE_BRIEF.md Section 6).

For a design, a PVT condition and an input level, one ngspice run gives:
- loop gain with the loop broken at the inverting input (large inductor / capacitor), for the
  acquisition load (sampling switch on, Cs) and the hold load (switch off): unity-gain frequency,
  phase margin, gain margin, low-frequency loop gain;
- vds - vdsat of every driver transistor at the operating point (acquisition load).

For the bootstrapped switch the on state is represented by its main device with the gate held at
V + VDD (what the bootstrap provides) plus the bootstrap capacitor's bottom-plate parasitic at the
driver side; the off state by the main device with the gate at 0 V. For a transmission gate the
gates are at the static clock levels.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import shbench as sb

OUT = sb.GENERATED / "stability"


def _load_lines(design: sb.Design, pvt: sb.PVT, level: float, on: bool, sfx: str) -> list[str]:
    sw = design.switch
    s = f"samp{sfx}"
    o = f"o{sfx}"
    if sw.kind == "sub":  # bootstrapped NMOS (sw_bootab): main device W = WS*MS
        p = dict(sw.subckt_params)
        g = level + pvt.vdd if on else 0.0
        cbp = 0.05 * float(str(p["CB"]).replace("p", "e-12"))
        lines = [f"XMS{sfx} {o} g{sfx} {s} 0 sky130_fd_pr__nfet_01v8 W={p['WS']} L=0.15 m={p['MS']}",
                 f"VG{sfx} g{sfx} 0 {g}"]
        if on:
            lines.append(f"CBP{sfx} {o} 0 {cbp}")
    else:
        vn, vp = (pvt.vdd, 0.0) if on else (0.0, pvt.vdd)
        lp = sw.lp or sw.l
        lines = [f"XSN{sfx} {o} gn{sfx} {s} 0 {sw.nmodel} W={sw.wn} L={sw.l} m={sw.mn}",
                 f"XSP{sfx} {o} gp{sfx} {s} vdd {sw.pmodel} W={sw.wp} L={lp} m={sw.mp}",
                 f"VGN{sfx} gn{sfx} 0 {vn}", f"VGP{sfx} gp{sfx} 0 {vp}"]
    lines.append(f"CS{sfx} {s} 0 {design.cs}")
    if not on:
        lines.append(f".nodeset v({s})={level}")
    return lines


def netlist(design: sb.Design, pvt: sb.PVT, level: float, outdir: Path) -> str:
    L = [f"* stability: {design.name} {pvt.tag} {level} V",
         f'.lib "{sb.pdk_library()}" {pvt.corner}', f".temp {pvt.temp}",
         f'.include "{outdir / design.driver_file}"',
         ".option reltol=1e-5", f"VDD vdd 0 {pvt.vdd}"]
    for sfx, on in (("a", True), ("h", False)):
        L += [f"IREF{sfx} vdd ib{sfx} {design.iref}", f"VC{sfx} vc{sfx} 0 {level}",
              f"XD{sfx} vc{sfx} fb{sfx} o{sfx} ib{sfx} vdd 0 {design.driver_subckt}",
              f"LB{sfx} o{sfx} fb{sfx} 1G", f"CB{sfx} fb{sfx} inj{sfx} 1", f"VI{sfx} inj{sfx} 0 dc 0 ac 1"]
        L += _load_lines(design, pvt, level, on, sfx)
    L += [".control", "op", "show m : vds vdsat vgs id", "ac dec 50 1k 20G"]
    for sfx in ("a", "h"):
        L += [f"let lg{sfx} = -v(o{sfx})/v(fb{sfx})", f"let db{sfx} = db(lg{sfx})",
              f"let ph{sfx} = 180/pi*cph(lg{sfx})",
              f"meas ac fu_{sfx} when db{sfx}=0", f"meas ac pu_{sfx} find ph{sfx} when db{sfx}=0",
              f"meas ac a0_{sfx} find db{sfx} at=1e3", f"meas ac f180_{sfx} when ph{sfx}=-180",
              f"meas ac gm_{sfx} find db{sfx} when ph{sfx}=-180"]
    L += [".endc", ".end"]
    return "\n".join(L) + "\n"


def run(design: sb.Design, pvt: sb.PVT, level: float) -> dict:
    outdir = OUT / design.name / f"{pvt.tag}_{level:.2f}"
    outdir.mkdir(parents=True, exist_ok=True)
    shutil.copy(sb.NETLISTS / design.driver_file, outdir / design.driver_file)
    text = netlist(design, pvt, level, outdir)
    nl = outdir / "stab.spice"
    log = outdir / "ngspice.log"
    if not (nl.is_file() and log.is_file() and nl.read_text() == text):
        nl.write_text(text)
        p = subprocess.run(["ngspice", "-b", str(nl)], cwd=sb.HERE, capture_output=True, text=True)
        log.write_text(p.stdout + p.stderr)
    return parse(log.read_text(), design, pvt, level)


def parse(txt: str, design: sb.Design, pvt: sb.PVT, level: float) -> dict:
    vals = {}
    for m in re.finditer(r"^(\w+)\s*=\s*([-+0-9.eE]+)", txt, re.M):
        vals[m.group(1).lower()] = float(m.group(2))
    res = {"design": design.name, "tag": pvt.tag, "level": level}
    for sfx, mode in (("a", "acq"), ("h", "hold")):
        pu = vals.get(f"pu_{sfx}")
        res[mode] = {"ugf_MHz": vals.get(f"fu_{sfx}", float("nan")) / 1e6,
                     "pm_deg": (180 + pu) if pu is not None else float("nan"),
                     "gm_dB": -vals[f"gm_{sfx}"] if f"gm_{sfx}" in vals else float("inf"),
                     "a0_dB": vals.get(f"a0_{sfx}", float("nan"))}
    # "show m" prints blocks: a header line with device names, then rows 'vds', 'vdsat', ...
    margins = {}
    names: list[str] = []
    for line in txt.splitlines():
        t = line.split()
        if not t:
            continue
        if t[0] == "device":
            names = t[1:]
        elif t[0] in ("vds", "vdsat") and names:
            for n, v in zip(names, t[1:]):
                margins.setdefault(n, {})[t[0]] = float(v)
    drv = {}
    for n, d in margins.items():
        parts = n.lower().split(".")
        if len(parts) > 2 and parts[1] == "xda" and "vds" in d and "vdsat" in d:
            drv[parts[2]] = abs(d["vds"]) - abs(d["vdsat"])
    res["sat_margin_mV"] = {k: v * 1e3 for k, v in drv.items()}
    return res

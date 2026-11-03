"""Technology-independent M2 pulse-survival calibration (ngspice), for any PDK with
an ngspice model deck, standard-cell SPICE netlists and a Liberty file.

Same measurement as ``pulse_sweep`` (SKY130): a single input pulse of 50 %-to-50 %
width w through one sensitised arc, output peak excursion, delay, supply energy;
a very wide reference pulse per condition gives t_pd and E_full; the model is
fitted in normalised form r = w / t_pd.  Stimulus ranges (input slews, loads,
pulse widths, simulation times) are scaled from the SKY130 settings by the
library's own FO4 inverter slew and unit-inverter input capacitance, so every
node is probed at comparable *relative* conditions.

    spec = PdkSpec(...)            # or pdk_spec("gf180mcu_7t_3v3")
    rows = sweep(spec, cells)      # -> CSV rows
    fit(rows_csv, out_dir, spec)   # -> m2_model.json + liberty_vs_spice_energy.csv
"""
from __future__ import annotations

import csv
import itertools
import json
import os
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

import numpy as np

from ..liberty import parse_liberty_file, LibertyDelayProvider, read_liberty_text
from ..liberty_power import liberty_units, read_internal_power, internal_energy_pj
from ..logic import eval_primitive
from ..model import Cell
from ..pdk import pick_cells
from .pulse_sweep import _env, _crossings

SKY130_REF = dict(fo4_slew_ps=None, inv_cin_ff=None)   # filled lazily from the SKY130 Liberty
POWER_RE = re.compile(r"^(VDD|VPWR|VPB|VNW|VCC)$", re.I)
GROUND_RE = re.compile(r"^(VSS|VGND|VNB|VPW|GND|VEE)$", re.I)


@dataclass
class PdkSpec:
    name: str                       # short id, e.g. "gf180mcu_7t_3v3"
    liberty: str
    cell_spice: str
    model_lines: List[str]          # ngspice lines that load the device models
    vdd: float
    temp_c: float = 25.0
    scale_option: bool = False      # SKY130-style netlists in um without units
    fo4_slew_ps: float = 0.0        # filled by prepare()
    inv_cin_ff: float = 0.0
    slew_full_factor: float = 1.0   # Liberty slew -> 0-100 % ramp time
    cells: dict = field(default_factory=dict)   # short key -> (libcell, in_pin, out_pin, side, inverting)


def _fo4(lib, inv):
    dp = LibertyDelayProvider(lib)
    c = lib.cells[inv.name]
    cin = c.pin_capacitance.get(inv.inputs[0], 1.0)
    fn = next(p.function for p in c.pins.values() if p.direction == "output")
    cell = Cell("x", "LIB:" + fn, {inv.inputs[0]: "a"}, "y", 0, 0, inv.name, inv.output)
    slew = 20_000
    for _ in range(30):
        r = dp.delay(cell, 1, input_slew_fs=slew, load_ff=4 * cin, related_pin=inv.inputs[0],
                     pin_values={inv.inputs[0]: 0}, input_transition=(1, 0))
        f = dp.delay(cell, 0, input_slew_fs=slew, load_ff=4 * cin, related_pin=inv.inputs[0],
                     pin_values={inv.inputs[0]: 1}, input_transition=(0, 1))
        new = (r.output_slew_fs + f.output_slew_fs) / 2
        if abs(new - slew) < 50:
            break
        slew = new
    return new / 1000.0, cin


def _slew_factor(text):
    def g(k, d):
        m = re.search(r"\b" + k + r"\s*:\s*([0-9.]+)", text)
        return float(m.group(1)) if m else d
    lo, hi = g("slew_lower_threshold_pct_rise", 20.0), g("slew_upper_threshold_pct_rise", 80.0)
    der = g("slew_derate_from_library", 1.0)
    return der / ((hi - lo) / 100.0)


def sensitise(lc):
    """(input pin, output pin, side values, inverting) for the first sensitisable input."""
    outs = [p for p in lc.pins.values() if p.direction == "output" and p.function]
    ins = sorted(p.name for p in lc.pins.values() if p.direction == "input")
    pin, side_pins = ins[0], ins[1:]
    fn = "LIB:" + outs[0].function
    for vals in itertools.product([1, 0], repeat=len(side_pins)):
        side = dict(zip(side_pins, vals))
        y0 = eval_primitive(fn, {**side, pin: 0}); y1 = eval_primitive(fn, {**side, pin: 1})
        if y0 != y1:
            return pin, outs[0].name, side, y1 == 0
    raise ValueError(f"{lc.name}: pin {pin} cannot be sensitised")


def prepare(spec: PdkSpec, functions=("inv", "buf", "nand2", "nor2", "and2", "or2", "xor2", "xnor2")):
    lib = parse_liberty_file(spec.liberty)
    picked = pick_cells(lib, wanted=functions)
    spec.fo4_slew_ps, spec.inv_cin_ff = _fo4(lib, picked["inv"])
    spec.slew_full_factor = _slew_factor(read_liberty_text(spec.liberty)[:400_000])
    for k, ref in picked.items():
        pin, out, side, inv = sensitise(lib.cells[ref.name])
        spec.cells[ref.name.split("__")[-1]] = (ref.name, pin, out, side, inv)
    if not SKY130_REF["fo4_slew_ps"]:
        sl = parse_liberty_file(_env("GS_LIB"))
        SKY130_REF["fo4_slew_ps"], SKY130_REF["inv_cin_ff"] = _fo4(sl, pick_cells(sl, ("inv",))["inv"])
    return spec


def scales(spec):
    return spec.fo4_slew_ps / SKY130_REF["fo4_slew_ps"], spec.inv_cin_ff / SKY130_REF["inv_cin_ff"]


def _subckt_pins(path, name):
    pat = re.compile(r"^\.subckt\s+" + re.escape(name) + r"\s+(.*)$", re.I)
    lines = Path(path).read_text(errors="replace").splitlines()
    for i, line in enumerate(lines):
        m = pat.match(line.strip())
        if m:
            pins = m.group(1).split()
            j = i + 1
            while j < len(lines) and lines[j].startswith("+"):
                pins += lines[j][1:].split(); j += 1
            return [p for p in pins if "=" not in p]
    raise ValueError(f"subckt {name} not found in {path}")


def build_deck(spec, key, polarity, slew_ps, load_ff, widths_s, outdir):
    libcell, inp, out, side, _ = spec.cells[key]
    s, _ = scales(spec)
    conn = []
    for p in _subckt_pins(spec.cell_spice, libcell):
        if POWER_RE.match(p):
            conn.append("vdd")
        elif GROUND_RE.match(p):
            conn.append("0")
        elif p == inp:
            conn.append("a")
        elif p == out:
            conn.append("y")
        elif p in side:
            conn.append("vdd" if side[p] else "0")
        else:
            raise ValueError(f"{libcell}: unhandled pin {p}")
    V = spec.vdd
    tr = slew_ps * 1e-12 * spec.slew_full_factor
    v0, sgn = (0.0, 1.0) if polarity == "pos" else (V, -1.0)
    t0 = 0.4e-9 * s
    step = max(0.02e-12, 0.2e-12 * s)
    lines = [f"* GlitchScope M2 sweep {spec.name} {key} {polarity} {slew_ps} {load_ff}"]
    if spec.scale_option:
        lines.append(".option scale=1e-6")
    lines += spec.model_lines + [
        f'.include "{spec.cell_spice}"',
        f".temp {spec.temp_c}",
        f".param tr={tr:.6e} pw=100e-12",
        ".param ra={min(tr,(tr+pw)/2)} pl={max(0,pw-tr)}",
        f".param vpk={{{v0}+({sgn})*{V}*ra/tr}}",
        f"Vdd vdd 0 {V}",
        f"Vin a 0 PWL(0 {v0} {t0:.4e} {v0} {{{t0}+ra}} {{vpk}} {{{t0}+ra+pl}} {{vpk}} {{{t0}+2*ra+pl}} {v0})",
        f"X1 {' '.join(conn)} {libcell}",
        f"Cl y 0 {load_ff}f",
        ".control", "set wr_singlescale", "set wr_vecnames", "option numdgt=7"]
    for i, w in enumerate(widths_s):
        lines += [f"alterparam pw={w:.6e}", "reset",
                  f"tran {step:.3e} {t0 + 2 * tr + w + 2.0e-9 * s:.4e} 0 {5 * step:.3e}",
                  f"wrdata {outdir}/w{i:03d}.txt v(a) v(y) i(Vdd)"]
    lines += ["quit", ".endc", ".end"]
    return "\n".join(lines) + "\n"


def measure(path, V, t_pre):
    d = np.loadtxt(path, skiprows=1)
    t, va, vy, idd = d[:, 0], d[:, 1], d[:, 2], d[:, 3]
    half = V / 2
    ca = _crossings(t, va, half)
    pre = t < t_pre
    y0 = float(np.mean(vy[pre]))
    peak_frac = float(np.abs(vy - y0).max() / V)
    cy = _crossings(t, vy, half)
    p = -idd * V
    leak = float(np.mean(p[pre]))
    return dict(w_in_ps=float(ca[1] - ca[0]) * 1e12 if len(ca) >= 2 else float("nan"),
                peak_frac=peak_frac, w_out_ps=float(cy[1] - cy[0]) * 1e12 if len(cy) >= 2 else 0.0,
                t_pd_ps=float(cy[0] - ca[0]) * 1e12 if (cy and ca) else float("nan"),
                energy_fJ=float(np.trapezoid(p - leak, t)) * 1e15, n_out_cross=len(cy))


def run_condition(spec, key, polarity, slew_ps, load_ff, widths_s):
    ng = _env("GS_NGSPICE")
    s, _ = scales(spec)
    with tempfile.TemporaryDirectory(prefix="gs_pdk_") as td:
        tdp = Path(td)
        (tdp / "deck.sp").write_text(build_deck(spec, key, polarity, slew_ps, load_ff, widths_s, tdp))
        (tdp / ".spiceinit").write_text("set ngbehavior=hsa\nset ng_nomodcheck\nset num_threads=1\n"
                                        + "".join(f"osdi {o}\n" for o in os.environ.get("GS_OSDI", "").split(":") if o))
        r = subprocess.run([ng, "-b", "deck.sp"], capture_output=True, text=True, cwd=tdp)
        rows = []
        for i, w in enumerate(widths_s):
            f = tdp / f"w{i:03d}.txt"
            if not f.exists():
                raise RuntimeError(f"ngspice failed ({spec.name} {key}):\n{r.stdout[-2000:]}\n{r.stderr[-1500:]}")
            rows.append(dict(cell=key, libcell=spec.cells[key][0], polarity=polarity, slew_ps=slew_ps,
                             load_ff=load_ff, inverting=int(spec.cells[key][4]), w_set_ps=w * 1e12,
                             **measure(f, spec.vdd, 0.35e-9 * s)))
        return rows


def sweep(spec, keys=None, polarities=("pos", "neg"), workers=2):
    s, c = scales(spec)
    slews = [round(x * s, 3) for x in (20, 100, 300)]
    loads = [round(x * c, 4) for x in (2.0, 10.0)]
    widths = [float(x) * 1e-12 * s for x in np.unique(np.round(np.geomspace(3, 600, 26), 2))] + [3000e-12 * s]
    keys = keys or list(spec.cells)
    conds = list(itertools.product(keys, polarities, slews, loads))
    rows = []
    with ThreadPoolExecutor(workers) as ex:
        for res in ex.map(lambda k: run_condition(spec, *k, widths), conds):
            rows.extend(res)
    return rows


def write_csv(rows, path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def fit(csv_path, out_dir, spec):
    """Fit r_filter / r_full = a + b * slew/t_pd and median S_E(r) per (cell, output
    polarity); compare Liberty vs SPICE full-cycle energy.  Writes m2_model.json and
    liberty_vs_spice_energy.csv into ``out_dir``."""
    import pandas as pd
    df = pd.read_csv(csv_path)
    df["polarity"] = [("positive" if (p == "pos") != bool(i) else "negative") for p, i in zip(df.polarity, df.inverting)]
    keys = ["cell", "polarity", "slew_ps", "load_ff"]
    W_REF = df.w_set_ps.max()

    def first_cross(x, y, level):
        for i in range(1, len(y)):
            if y[i - 1] < level <= y[i]:
                return float(x[i - 1] + (level - y[i - 1]) * (x[i] - x[i - 1]) / (y[i] - y[i - 1]))
        return float("nan") if y[0] < level else float(x[0])

    cond, curves = [], []
    for k, g in df.groupby(keys):
        g = g.sort_values("w_set_ps")
        ref = g[g.w_set_ps == W_REF].iloc[0]
        sw = g[g.w_set_ps < W_REF].copy()
        sw["r"] = sw.w_in_ps / ref.t_pd_ps
        sw["S_E"] = sw.energy_fJ / ref.energy_fJ
        cond.append(dict(zip(keys, k), libcell=ref.libcell, t_pd_ref_ps=ref.t_pd_ps, E_full_fJ=ref.energy_fJ,
                         r_filter=first_cross(sw.r.values, sw.peak_frac.values, 0.5),
                         r_full=first_cross(sw.r.values, sw.peak_frac.values, 0.95),
                         slew_over_tpd=k[2] / ref.t_pd_ps))
        curves.append(sw.assign(**dict(zip(keys, k))))
    cdf = pd.DataFrame(cond)
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    cdf.to_csv(out_dir / "m2_conditions.csv", index=False)
    model = {"description": f"M2 CALIBRATED_EXPLORATORY: SPICE-native pulse survival, r = w_in/t_pd(SPICE), "
                            f"ngspice, {spec.name}, {spec.vdd} V, {spec.temp_c} C",
             "pdk": spec.name, "cells": {}}
    for (cell, pol), g in cdf.groupby(["cell", "polarity"]):
        A = np.vstack([np.ones(len(g)), g.slew_over_tpd]).T
        for name in ("r_filter", "r_full"):
            ok = np.isfinite(g[name].values)
            if ok.sum() < 2:
                continue
            coef, *_ = np.linalg.lstsq(A[ok], g[name].values[ok], rcond=None)
            model["cells"].setdefault(cell, {}).setdefault(pol, {})[name] = {
                "a": round(float(coef[0]), 4), "b": round(float(coef[1]), 4),
                "max_abs_resid": round(float(np.max(np.abs(A[ok] @ coef - g[name].values[ok]))), 4)}
    RG = np.round(np.arange(0.0, 3.01, 0.05), 2)
    allc = pd.concat(curves)
    for (cell, pol), g in allc.groupby(["cell", "polarity"]):
        per = [np.interp(RG, gg.sort_values("r").r, gg.sort_values("r").S_E, left=np.nan, right=1.0)
               for _, gg in g.groupby(["slew_ps", "load_ff"])]
        med = np.nanmedian(np.vstack(per), axis=0)
        first = np.flatnonzero(~np.isnan(med))[0]
        med[:first] = med[first]
        model["cells"].setdefault(cell, {}).setdefault(pol, {})["S_E_curve"] = {"r": RG.tolist(),
                                                                                "S": np.round(med, 4).tolist()}
    (out_dir / "m2_model.json").write_text(json.dumps(model, indent=1))
    # Liberty vs SPICE full-cycle energy
    u = liberty_units(spec.liberty)
    P = read_internal_power(spec.liberty, sorted({c[0] for c in spec.cells.values()}))
    rows = []
    for key, (libcell, inp, out, side, inv) in spec.cells.items():
        tabs = P.get(libcell, {}).get((out, inp))
        if not tabs:
            continue
        for _, r in cdf[cdf.cell == key].drop_duplicates(["slew_ps", "load_ff"]).iterrows():
            s_l, c_l = r.slew_ps / u["time_ps"], r.load_ff / u["cap_ff"]
            e_int = (internal_energy_pj(tabs, True, s_l, c_l) + internal_energy_pj(tabs, False, s_l, c_l)) * u["energy_fj"]
            e_lib = e_int + r.load_ff * u["vdd"] ** 2
            rows.append(dict(cell=key, slew_ps=r.slew_ps, load_ff=r.load_ff, E_spice_fJ=r.E_full_fJ,
                             E_lib_fJ=e_lib, ratio=e_lib / r.E_full_fJ))
    pd.DataFrame(rows).to_csv(out_dir / "liberty_vs_spice_energy.csv", index=False)
    return cdf, model


def pdk_spec(name):
    """Specs for the PDKs studied in the notebook (paths from tools.env / environment)."""
    libdir = Path(_env("GS_LIBDIR"))
    if name == "gf180mcu_7t_3v3":
        root = Path(_env("GS_PDK_GF180"))
        ng = root / "libs.tech/ngspice"
        return PdkSpec(name, str(libdir / f"{name}.lib"),
                       str(root / "libs.ref/gf180mcu_fd_sc_mcu7t5v0/spice/gf180mcu_fd_sc_mcu7t5v0.spice"),
                       [f'.include "{ng / "design.ngspice"}"', f'.lib "{ng / "sm141064.ngspice"}" typical'], 3.3)
    if name == "ihp_sg13g2_1v2":
        root = Path(_env("GS_PDK_IHP"))
        ng = root / "libs.tech/ngspice/models"
        return PdkSpec(name, str(libdir / f"{name}.lib"),
                       str(root / "libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"),
                       [f'.lib "{ng / "cornerMOSlv.lib"}" mos_tt'], 1.2)
    raise KeyError(name)

"""M2 pulse-survival characterisation with ngspice + SKY130 HD cells.

For one cell arc (input pin -> output pin, side inputs held at non-controlling
values) we inject a single input pulse of 50%-to-50% width ``w`` with a given
input slew, drive a capacitive load, and measure:

* output peak excursion (fraction of VDD) -> did the pulse "survive"?
* output 50%-to-50% pulse width
* delay of the leading edge (50% in -> 50% out)
* supply energy drawn from VPWR (leakage-corrected)

A very wide pulse (``W_REF``) is always included so every condition has its own
full-swing reference: SPICE delay t_pd and full-cycle energy E_full.  The fitted
model is expressed in normalised form  r = w / t_pd(SPICE),  so it does not rely
on the absolute Liberty/SPICE timing agreement (see B8 findings).
"""
from __future__ import annotations

import csv
import itertools
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

VDD = 1.8
LIB_SLEW_FRAC = 0.6  # SKY130 Liberty slew = 20%..80% transition time
W_REF = 3000e-12     # reference "infinitely wide" pulse


def _env(key: str) -> str:
    val = os.environ.get(key)
    if val:
        return val
    env_file = Path(__file__).resolve().parents[2] / "tools.env"
    for line in env_file.read_text().splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    raise KeyError(key)


# cell -> (input pin, output pin, side-pin values that sensitise the arc, inverting?)
CELLS = {
    "inv_1":   ("A", "Y", {}, True),
    "nand2_1": ("A", "Y", {"B": 1}, True),
    "nor2_1":  ("A", "Y", {"B": 0}, True),
    "xor2_1":  ("A", "X", {"B": 0}, False),
    "buf_1":   ("A", "X", {}, False),
    "xnor2_1": ("A", "Y", {"B": 0}, True),
    "and2_1":  ("A", "X", {"B": 1}, False),
    "or2_1":   ("A", "X", {"B": 0}, False),
    "a21oi_1": ("A1", "Y", {"A2": 1, "B1": 0}, True),
    "o21ai_0": ("A1", "Y", {"A2": 0, "B1": 1}, True),
}


def auto_cell_entry(lib, cell):
    """Derive (input pin, output pin, sensitising side values, inverting) from the
    Liberty function of ``sky130_fd_sc_hd__<cell>``: first input pin, first side
    assignment for which the output depends on that pin."""
    from ..logic import eval_primitive
    lc = lib.cells["sky130_fd_sc_hd__" + cell]
    outs = [p for p in lc.pins.values() if p.direction == "output" and p.function]
    if len(outs) != 1:
        raise ValueError(f"{cell}: need exactly one output with a function")
    ins = sorted(p.name for p in lc.pins.values() if p.direction == "input")
    pin, side_pins = ins[0], ins[1:]
    fn = "LIB:" + outs[0].function
    for vals in itertools.product([1, 0], repeat=len(side_pins)):
        side = dict(zip(side_pins, vals))
        y0 = eval_primitive(fn, {**side, pin: 0}); y1 = eval_primitive(fn, {**side, pin: 1})
        if y0 != y1:
            return (pin, outs[0].name, side, y1 == 0)
    raise ValueError(f"{cell}: pin {pin} cannot be sensitised")


def ensure_cells(lib, cells):
    for c in cells:
        if c not in CELLS:
            CELLS[c] = auto_cell_entry(lib, c)


CELLS_BATCH1 = ["inv_1", "nand2_1", "nor2_1", "xor2_1", "buf_1"]


@dataclass
class Condition:
    cell: str
    polarity: str      # "pos": input 0->1->0 ; "neg": input 1->0->1
    slew_ps: float     # Liberty-style 20-80 % input transition
    load_ff: float


def cell_spice_lib() -> Path:
    """The SKY130 HD cell SPICE library used by every ngspice run: the PDK's schematic netlists
    by default, or the file named by ``GS_CELL_SPICE`` (e.g. the parasitic-extracted cells
    written by scripts/extract_cells_pex.sh; a relative path is taken from the repository root)."""
    alt = os.environ.get("GS_CELL_SPICE")
    if alt:
        q = Path(alt)
        return q if q.is_absolute() else Path(__file__).resolve().parents[2] / q
    return Path(_env("GS_PDK_ROOT")) / "libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice"


def _cell_pins(spice_lib: Path, cell: str) -> list[str]:
    name = f"sky130_fd_sc_hd__{cell}"
    for line in spice_lib.read_text().splitlines():
        if line.lower().startswith(".subckt " + name + " "):
            return line.split()[2:]
    raise ValueError(f"cell {name} not found")


def build_deck(cond: Condition, widths_s: list[float], outdir: Path) -> str:
    pdk = Path(_env("GS_PDK_ROOT"))
    cell_lib = cell_spice_lib()
    model_lib = pdk / "libs.tech/ngspice/sky130.lib.spice"
    inp, out, side, _ = CELLS[cond.cell]
    pins = _cell_pins(cell_lib, cond.cell)
    conn = []
    for p in pins:
        if p in ("VGND", "VNB"):
            conn.append("0")
        elif p in ("VPWR", "VPB"):
            conn.append("vpwr")
        elif p == inp:
            conn.append("a")
        elif p == out:
            conn.append("y")
        elif p in side:
            conn.append("vpwr" if side[p] else "0")
        else:
            raise ValueError(f"unhandled pin {p}")
    tr = cond.slew_ps * 1e-12 / LIB_SLEW_FRAC  # full 0-100 % ramp time
    v0, sgn = (0.0, 1.0) if cond.polarity == "pos" else (VDD, -1.0)
    t0 = 0.4e-9
    lines = [
        f"* GlitchScope M2 pulse sweep {asdict(cond)}",
        ".option scale=1e-6",
        f'.lib "{model_lib}" tt',
        f'.include "{cell_lib}"',
        ".temp 25",
        f".param tr={tr:.6e} pw=100e-12",
        ".param ra={min(tr,(tr+pw)/2)} pl={max(0,pw-tr)}",
        f".param vpk={{{v0}+({sgn})*{VDD}*ra/tr}}",
        f"Vdd vpwr 0 {VDD}",
        f"Vin a 0 PWL(0 {v0} {t0:.4e} {v0} {{{t0}+ra}} {{vpk}} {{{t0}+ra+pl}} {{vpk}} {{{t0}+2*ra+pl}} {v0})",
        f"X1 {' '.join(conn)} sky130_fd_sc_hd__{cond.cell}",
        f"Cl y 0 {cond.load_ff}f",
        ".control",
        "set wr_singlescale",
        "set wr_vecnames",
        "option numdgt=7",
    ]
    for i, w in enumerate(widths_s):
        lines += [
            f"alterparam pw={w:.6e}",
            "reset",
            f"tran 0.2p {t0 + 2 * tr + w + 2.0e-9:.4e} 0 1p",
            f"wrdata {outdir}/w{i:03d}.txt v(a) v(y) i(Vdd)",
        ]
    lines += ["quit", ".endc", ".end"]
    return "\n".join(lines) + "\n"


def _crossings(t, v, level):
    s = np.sign(v - level)
    idx = np.where(np.diff(s) != 0)[0]
    out = []
    for k in idx:
        t1, t2, v1, v2 = t[k], t[k + 1], v[k], v[k + 1]
        out.append(t1 + (level - v1) * (t2 - t1) / (v2 - v1))
    return out


def measure(path: Path, cond: Condition) -> dict:
    d = np.loadtxt(path, skiprows=1)
    t, va, vy, idd = d[:, 0], d[:, 1], d[:, 2], d[:, 3]
    half = VDD / 2
    ca = _crossings(t, va, half)
    pre = t < 0.35e-9
    y0 = float(np.mean(vy[pre]))
    excursion = np.abs(vy - y0)
    peak_frac = float(excursion.max() / VDD)
    cy = _crossings(t, vy, half)
    w_out = (cy[1] - cy[0]) if len(cy) >= 2 else 0.0
    t_pd = (cy[0] - ca[0]) if (cy and ca) else float("nan")
    # supply energy: E = VDD * integral(-i) dt, leakage corrected
    p = -idd * VDD
    leak = float(np.mean(p[pre]))
    energy = float(np.trapezoid(p - leak, t))
    w_in = (ca[1] - ca[0]) if len(ca) >= 2 else float("nan")
    return dict(w_in_ps=float(w_in) * 1e12, peak_frac=peak_frac, w_out_ps=float(w_out) * 1e12,
                t_pd_ps=float(t_pd) * 1e12, energy_fJ=energy * 1e15,
                n_out_cross=len(cy))


def run_condition(cond: Condition, widths_s: list[float]) -> list[dict]:
    ng = _env("GS_NGSPICE")
    with tempfile.TemporaryDirectory(prefix="gs_m2_") as td:
        tdp = Path(td)
        deck = tdp / "deck.sp"
        deck.write_text(build_deck(cond, widths_s, tdp))
        (tdp / ".spiceinit").write_text("set ngbehavior=hsa\nset ng_nomodcheck\nset num_threads=1\n")
        r = subprocess.run([ng, "-b", str(deck)], capture_output=True, text=True, cwd=tdp)
        rows = []
        for i, w in enumerate(widths_s):
            f = tdp / f"w{i:03d}.txt"
            if not f.exists():
                raise RuntimeError(f"ngspice failed for {cond}:\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
            m = measure(f, cond)
            rows.append({**asdict(cond), "inverting": int(CELLS[cond.cell][3]), "w_set_ps": w * 1e12, **m})
        return rows


def default_widths() -> list[float]:
    w = np.unique(np.round(np.geomspace(3, 600, 26), 2)) * 1e-12
    return [float(x) for x in w] + [W_REF]


def sweep(cells, polarities=("pos", "neg"), slews_ps=(20, 100, 300),
          loads_ff=(2.0, 10.0), workers=2) -> list[dict]:
    conds = [Condition(c, p, s, l) for c, p, s, l in itertools.product(cells, polarities, slews_ps, loads_ff)]
    widths = default_widths()
    rows = []
    with ThreadPoolExecutor(workers) as ex:
        for res in ex.map(lambda c: run_condition(c, widths), conds):
            rows.extend(res)
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

"""nbutil.py - notebook plumbing: caching, the results registry, markdown tables, plot style.
Every number shown in the notebook, README and TL;DR is read from cache/results.json,
which only analysis code writes. SPDX-License-Identifier: Apache-2.0"""
from __future__ import annotations
import json, math, shutil, numpy as np
from pathlib import Path

ROOT = Path.cwd(); CACHE = ROOT / "cache"; FIGS = ROOT / "images"
for d in (CACHE, FIGS): d.mkdir(exist_ok=True)
RESULTS = CACHE / "results.json"

def _enc(o):
    if isinstance(o, np.ndarray): return o.tolist()
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.bool_,)): return bool(o)
    raise TypeError(type(o))

CAN_RUN = True   # set from the notebook's SPICE check

def cached(name: str, fn, rerun: bool):
    """Load cache/<name>.json; (re)compute it with fn() if rerun is set or the file is missing."""
    f = CACHE / f"{name}.json"
    if f.exists() and not rerun:
        return json.loads(f.read_text())
    if not CAN_RUN:
        raise FileNotFoundError(f"{f} is missing and ngspice/SKY130 is not available to regenerate it")
    val = fn(); f.write_text(json.dumps(val, default=_enc, indent=1)); return json.loads(f.read_text())

def record(**kv):
    """Add entries to the single results registry."""
    R = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    R.update(json.loads(json.dumps(kv, default=_enc))); RESULTS.write_text(json.dumps(R, indent=1, sort_keys=True))
    return R

def results(): return json.loads(RESULTS.read_text()) if RESULTS.exists() else {}

def md_table(header, rows, align=None):
    align = align or ["l"] + ["c"] * (len(header) - 1)
    sep = {"l": ":--", "c": ":--:", "r": "--:"}
    out = ["| " + " | ".join(map(str, header)) + " |", "|" + "|".join(sep[a] for a in align) + "|"]
    out += ["| " + " | ".join(map(str, r)) + " |" for r in rows]
    return "\n".join(out)

def show_md(text):
    from IPython.display import display, Markdown; display(Markdown(text))

def fmt(x, nd=2, unit=""):
    if x is None or (isinstance(x, float) and math.isnan(x)): return "—"
    return f"{x:.{nd}f}{(' ' + unit) if unit else ''}"

def plot_style():
    import matplotlib as mpl
    mpl.rcParams.update({"figure.dpi": 110, "savefig.dpi": 160, "axes.grid": True, "grid.alpha": 0.3,
                         "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
                         "legend.frameon": False, "figure.figsize": (6.0, 3.8)})

def spice_available(pdk_lib) -> bool:
    return shutil.which("ngspice") is not None and Path(pdk_lib).exists()


# ---- honest comparison of one design against a reference, computed (never typed) ----------------------
METRICS = [("control range", "range_db", +1), ("monotonic control range", "mono_range_db", +1),
           ("bandwidth at min gain", "f3db_lo", +1), ("bandwidth at max gain", "f3db_hi", +1),
           ("integrated noise at min gain", "vrms_lo", -1), ("integrated noise at max gain", "vrms_hi", -1),
           ("NEF at max gain", "nef_hi", -1), ("supply power", "power", -1),
           ("output swing at max gain", "swing_hi", +1)]

def compare(new: dict, ref: dict, tol: float = 0.03):
    """Metrics where `new` is better / worse than `ref` by more than `tol` (relative). Direction-aware:
    higher is better for range, bandwidth, swing; lower is better for noise, NEF, power."""
    better, worse = [], []
    for name, key, sgn in METRICS:
        a, b = new.get(key), ref.get(key)
        if a is None or b is None or a != a or b != b or b == 0: continue
        rel = (a - b) / abs(b) * sgn
        if rel > tol: better.append(name)
        elif rel < -tol: worse.append(name)
    return better, worse

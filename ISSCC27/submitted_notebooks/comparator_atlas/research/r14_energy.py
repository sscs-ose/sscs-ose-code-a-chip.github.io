"""r14: where the trim energy goes -- nominal (no mismatch) core energy and decision time per variant.

Variants separate input-pair width, trim bit count, unit-vs-binary trim sizing and the r12
gate-switched topology. +3 mV, 5 fF loads, 5 ps step, codes 0 and +full scale, three corners.
Local only.
  python -B r14_energy.py          # writes out/r14/energy.json
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r3_mismatch_mc as R3  # noqa: E402  (puts the entry root on sys.path)
import comparator_atlas.spice as S  # noqa: E402
from comparator_atlas.designs import DESIGNS, Design  # noqa: E402
from r3_mismatch_mc import HERE, Point, Trace  # noqa: E402
from r7_trim_dnl import unit_array  # noqa: E402
from r12_gate_trim import gate_switched  # noqa: E402

OUT = HERE / "out" / "r14"
# name: (input_w, trim_bits, trim style)
VARIANTS = {
    "binary4_w3_shipped": (3, 4, "binary"),
    "unit4_w3": (3, 4, "unit"),
    "binary4_w6": (6, 4, "binary"),
    "unit4_w6": (6, 4, "unit"),
    "unit5_w3": (3, 5, "unit"),
    "binary5_w6": (6, 5, "binary"),
    "unit5_w6_fix": (6, 5, "unit"),
    "gate5_w6_r12": (6, 5, "gate"),
}
CONDS = (("tt", 1.8, 27.0), ("ss", 1.62, -40.0), ("ff", 1.95, 125.0))
STYLE = {}
for _name, (_w, _bits, _style) in VARIANTS.items():
    DESIGNS[_name] = Design(_name, input_device="nfet_01v8_lvt", input_w=_w, tail_w=7, trim_bits=_bits)
    STYLE[_name] = _style
_orig = S.circuit_text


def _text(design):
    text = _orig(design)
    style = STYLE.get(design.name)
    if style in ("unit", "gate"):
        text = unit_array(text, design.trim_bits)
    if style == "gate":
        text = gate_switched(text, design.trim_bits)
    return text


S.circuit_text = _text


def one(job):
    name, cond, code = job
    sim = S.Simulator(HERE / "cache" / "r14_unused", workers=1)
    p = Point(design_name=name, corner=cond[0], vdd_v=cond[1], temperature_c=cond[2],
              differential_v=3e-3, pair_skew=0.0, trim_code=code, load_ff=5.0, max_step_ps=5.0)
    deck = "\n".join([sim._header(p), ".control", "set wr_singlescale", "set wr_vecnames", "set numdgt=15",
                      sim._analysis(p, "p0.tsv"), "quit 0", ".endc", ".end"]) + "\n"
    _, files = R3.ngspice(deck)
    m = R3.measure(Trace(p, np.loadtxt(files["p0.tsv"].splitlines(), skiprows=1), "e", OUT), 3.5)
    w, bits, style = VARIANTS[name]
    row = {"variant": name, "input_w": w, "trim_bits": bits, "trim_style": style, "cond": list(cond),
           "code": code, "decision_time_ns": m.decision_time_ns, "core_energy_fj": m.core_energy_fj,
           "gate_area_proxy_um2": DESIGNS[name].gate_area_um2}
    print(json.dumps(row), flush=True)
    return row


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (HERE / "cache").mkdir(exist_ok=True)
    jobs = [(n, c, code) for n in VARIANTS for c in CONDS for code in (0, DESIGNS[n].max_code)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(one, jobs))
    (OUT / "energy.json").write_text(json.dumps(rows, indent=1))

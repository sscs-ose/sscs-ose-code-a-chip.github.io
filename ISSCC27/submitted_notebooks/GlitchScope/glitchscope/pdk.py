"""Technology-independent helpers: find standard cells in any Liberty library by their
logic function, so the same circuit can be generated for every PDK.

    lib = parse_liberty_file(path)
    pick_cells(lib) -> {"inv": CellRef, "nor2": CellRef, "and2": CellRef, "dff": CellRef, ...}
"""
from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from .logic import eval_primitive

FUNCTIONS = {                      # name: (number of inputs, truth function)
    "inv": (1, lambda a: 1 - a),
    "buf": (1, lambda a: a),
    "nand2": (2, lambda a, b: 1 - (a & b)),
    "nor2": (2, lambda a, b: 1 - (a | b)),
    "and2": (2, lambda a, b: a & b),
    "or2": (2, lambda a, b: a | b),
    "xor2": (2, lambda a, b: a ^ b),
    "xnor2": (2, lambda a, b: 1 - (a ^ b)),
}


@dataclass
class CellRef:
    name: str
    inputs: List[str]            # in function-argument order
    output: str
    extra: Optional[dict] = None  # flip-flops: {"d", "clk", "q"}


def _drive_score(name):
    """Prefer unit-drive cells: *_1, X1, x1, xp33/xp5 (ASAP7 minimum), then anything."""
    n = name.lower()
    if re.search(r"(_1$|_x1\b|x1_|_x1$|xp33|xp5|x1$|_1_)", n):
        return 0
    if re.search(r"(_0$|_2$|x2)", n):
        return 1
    return 2


def _combinational(lc):
    outs = [p for p in lc.pins.values() if p.direction == "output" and p.function]
    ins = [p.name for p in lc.pins.values() if p.direction == "input"]
    return outs, ins


def pick_cells(lib, wanted=("inv", "nor2", "and2", "nand2", "xor2", "dff")) -> Dict[str, CellRef]:
    found: Dict[str, list] = {k: [] for k in wanted}
    for name, lc in lib.cells.items():
        if re.search(r"(?i)(fill|tap|decap|diode|antenna|clkbuf|clkinv|dly|lp|probe|hold|lv)", name):
            continue
        if lc.seq is not None:
            s = lc.seq
            if "dff" in found and s["kind"] == "ff" and not s.get("clear") and not s.get("preset") \
                    and re.fullmatch(r"[A-Za-z_]\w*", s.get("clocked_on", "")) \
                    and re.fullmatch(r"[A-Za-z_]\w*", s.get("next_state", "")):
                ins = [p.name for p in lc.pins.values() if p.direction == "input"]
                if len(ins) == 2:                 # plain D + clock (no scan, enable, reset)
                    q = [p.name for p in lc.pins.values() if p.direction == "output"
                         and (p.function or "").replace(" ", "").strip('"') == s["state"][0]]
                    qn = [p.name for p in lc.pins.values() if p.direction == "output"
                          and (p.function or "").replace(" ", "").strip('"') in (s["state"][-1], "!" + s["state"][0])]
                    found["dff"].append(CellRef(name, [s["next_state"]], (q or qn)[0],
                                                dict(d=s["next_state"], clk=s["clocked_on"], q=(q or [None])[0],
                                                     qn=(qn or [None])[0])))
            continue
        outs, ins = _combinational(lc)
        if len(outs) != 1:
            continue
        for key in wanted:
            if key == "dff" or key not in FUNCTIONS:
                continue
            n, fn = FUNCTIONS[key]
            if len(ins) != n:
                continue
            for perm in itertools.permutations(ins):
                ok = all(eval_primitive("LIB:" + outs[0].function, dict(zip(perm, bits))) == fn(*bits)
                         for bits in itertools.product((0, 1), repeat=n))
                if ok:
                    found[key].append(CellRef(name, list(perm), outs[0].name))
                    break
    best = {}
    for key, cands in found.items():
        if not cands:
            continue
        cands.sort(key=lambda c: (_drive_score(c.name),
                                  sum(lib.cells[c.name].pin_capacitance.get(p, 0.0) for p in c.inputs), c.name))
        best[key] = cands[0]
    return best

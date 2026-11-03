"""SPICE re-characterisation of cell timing with state-dependent arcs (ngspice + SKY130).

Liberty gives one timing arc per input pin and edge for most SKY130 HD cells, but a
complex gate's delay depends on its *side inputs*: in a21oi_1 (Y = !(A1 A2 + B1)) the
B1 -> Y rise pulls up through B1's PMOS in series with the parallel A1/A2 PMOS pair,
which is roughly twice as strong when both A1 and A2 are low.  The single Liberty arc
cannot express this, and in deep reconvergent logic the error moves glitch-generating
skews (section 5).

``characterise(cell)`` measures, with ngspice on the PDK's transistor models, the
50 %-50 % delay and the 20 %-80 % output transition for every input pin, every
sensitising state of the other inputs and both output edges, on the same 7x7
(input slew x load) grid as the original Liberty tables.  ``write_liberty`` writes a
Liberty file whose combinational arcs are replaced by these tables, with ``when``
conditions where a pin has more than one sensitising state; everything else (pins,
capacitances, internal power, flip-flops) is copied from the original.
"""
from __future__ import annotations

import itertools
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from ..liberty import parse_liberty_file, eval_when
from ..logic import eval_primitive
from .pulse_sweep import _env, _cell_pins, VDD, LIB_SLEW_FRAC

T0 = 200e-12


def _states(lc, outpin, func_kind, pin):
    """Side-input assignments under which ``pin`` controls the output."""
    others = [p for p in lc.pin_capacitance if p != pin and lc.pins[p].direction == "input"]
    out = []
    for bits in itertools.product((0, 1), repeat=len(others)):
        s = dict(zip(others, bits))
        y0 = eval_primitive(func_kind, {**s, pin: 0})
        y1 = eval_primitive(func_kind, {**s, pin: 1})
        if y0 != y1:
            out.append((s, "positive_unate" if y1 > y0 else "negative_unate"))
    return out


def _deck(cell, pins, pin, outpin, state, in_rise, slews_ps, loads_pf, outfile):
    pdk = Path(_env("GS_PDK_ROOT"))
    cell_lib = pdk / "libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice"
    model_lib = pdk / "libs.tech/ngspice/sky130.lib.spice"
    L = [".option scale=1e-6", f'.lib "{model_lib}" tt', f'.include "{cell_lib}"', ".temp 25", f"Vdd vpwr 0 {VDD}"]
    nodes, tmax = [], 0.0
    for i, s in enumerate(slews_ps):
        tr = s * 1e-12 / LIB_SLEW_FRAC
        a, b = (0.0, VDD) if in_rise else (VDD, 0.0)
        for j, c in enumerate(loads_pf):
            k = f"{i}_{j}"
            L.append(f"Vin{k} in{k} 0 PWL(0 {a} {T0:.4e} {a} {T0 + tr:.4e} {b})")
            conn = []
            for p in pins:
                if p in ("VGND", "VNB"):
                    conn.append("0")
                elif p in ("VPWR", "VPB"):
                    conn.append("vpwr")
                elif p == outpin:
                    conn.append(f"out{k}")
                elif p == pin:
                    conn.append(f"in{k}")
                else:
                    conn.append("vpwr" if state[p] else "0")
            L.append(f"X{k} {' '.join(conn)} sky130_fd_sc_hd__{cell}")
            L.append(f"C{k} out{k} 0 {c * 1e-12:.4e}")
            nodes.append(k)
        tmax = max(tmax, T0 + tr)
    tstop = tmax + 4e-9
    L += [".control", "set wr_singlescale", "set wr_vecnames", "option numdgt=7",
          f"tran 1p {tstop:.4e} 0 1p", "linearize",
          f"wrdata {outfile} " + " ".join(f"v(out{k})" for k in nodes), "quit", ".endc", ".end"]
    return "\n".join(L) + "\n", nodes


def _cross(t, v, level, rising):
    s = v - level
    idx = np.nonzero((s[:-1] < 0) & (s[1:] >= 0) if rising else (s[:-1] > 0) & (s[1:] <= 0))[0]
    if not len(idx):
        return None
    i = idx[0]
    return t[i] + (level - v[i]) * (t[i + 1] - t[i]) / (v[i + 1] - v[i])


def _measure_arc(cell, pin, outpin, state, out_rise, in_rise, slews_ps, loads_pf):
    ng = _env("GS_NGSPICE")
    pins = _cell_pins(Path(_env("GS_PDK_ROOT")) / "libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice", cell)
    with tempfile.TemporaryDirectory(prefix="gs_char_") as td:
        td = Path(td)
        deck, nodes = _deck(cell, pins, pin, outpin, state, in_rise, slews_ps, loads_pf, td / "w.txt")
        (td / "d.sp").write_text(deck)
        (td / ".spiceinit").write_text("set ngbehavior=hsa\nset ng_nomodcheck\n")
        r = subprocess.run([ng, "-b", "d.sp"], cwd=td, capture_output=True, text=True)
        if not (td / "w.txt").exists():
            raise RuntimeError(r.stdout[-1500:])
        d = np.loadtxt(td / "w.txt", skiprows=1)
    t = d[:, 0]
    delay = np.zeros((len(slews_ps), len(loads_pf)))
    tran = np.zeros_like(delay)
    for col, k in enumerate(nodes):
        i, j = map(int, k.split("_"))
        v = d[:, 1 + col]
        tr = slews_ps[i] * 1e-12 / LIB_SLEW_FRAC
        t_in = T0 + 0.5 * tr
        t50 = _cross(t, v, 0.5 * VDD, out_rise)
        t20 = _cross(t, v, 0.2 * VDD if out_rise else 0.8 * VDD, out_rise)
        t80 = _cross(t, v, 0.8 * VDD if out_rise else 0.2 * VDD, out_rise)
        if t50 is None or t20 is None or t80 is None:
            raise RuntimeError(f"{cell} {pin} {state}: output did not switch")
        delay[i, j] = (t50 - t_in) * 1e9          # ns (library time unit)
        tran[i, j] = (t80 - t20) * 1e9
    return delay, tran


def characterise(lib, cell, workers=2):
    """{pin: [(state, sense, {cell_rise, cell_fall, rise_transition, fall_transition})]} with
    the original table indices."""
    name = f"sky130_fd_sc_hd__{cell}"
    lc = lib.cells[name]
    outpin = next(p.name for p in lc.pins.values() if p.direction == "output")
    func = "LIB:" + lc.pins[outpin].function
    tmpl = lc.timing_arcs[0].cell_rise
    slews_ps = [x * lib.time_unit_ps for x in tmpl.index_1]
    loads_pf = [x * lib.capacitance_unit_ff / 1000.0 for x in tmpl.index_2]
    jobs = []
    for pin in [p for p in lc.pin_capacitance if lc.pins[p].direction == "input"]:
        for state, sense in _states(lc, outpin, func, pin):
            for out_rise in (True, False):
                in_rise = out_rise if sense == "positive_unate" else not out_rise
                jobs.append((pin, tuple(sorted(state.items())), sense, out_rise, in_rise))
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(lambda j: _measure_arc(cell, j[0], outpin, dict(j[1]), j[3], j[4], slews_ps, loads_pf),
                          jobs))
    arcs = {}
    for (pin, state, sense, out_rise, _), (dl, tr) in zip(jobs, res):
        e = arcs.setdefault((pin, state, sense), {})
        e["cell_rise" if out_rise else "cell_fall"] = dl
        e["rise_transition" if out_rise else "fall_transition"] = tr
    out = {}
    for (pin, state, sense), tabs in arcs.items():
        out.setdefault(pin, []).append((dict(state), sense, tabs))
    return dict(outpin=outpin, index_1=tmpl.index_1, index_2=tmpl.index_2, arcs=out)


def _table(kind, tmpl_name, i1, i2, vals):
    rows = ", \\\n".join('"' + ", ".join(f"{x:.7f}" for x in row) + '"' for row in vals)
    return (f'            {kind} ("{tmpl_name}") {{\n'
            f'                index_1 ("{", ".join(f"{x:.7f}" for x in i1)}");\n'
            f'                index_2 ("{", ".join(f"{x:.7f}" for x in i2)}");\n'
            f'                values ({rows});\n            }}\n')


def timing_groups(char, tmpl_name):
    """Liberty text of the re-characterised timing groups of one output pin."""
    out = []
    for pin, arcs in char["arcs"].items():
        senses = {}
        for state, sense, tabs in arcs:
            senses.setdefault(sense, []).append((state, tabs))
        for sense, lst in senses.items():
            for state, tabs in lst:
                when = ""
                if len(lst) > 1:      # several sensitising states: one arc per state
                    when = "&".join((p if v else "!" + p) for p, v in sorted(state.items()))
                g = ['        timing () {', f'            related_pin : "{pin}";', f'            timing_sense : "{sense}";',
                     '            timing_type : "combinational";']
                if when:
                    g.append(f'            when : "{when}";')
                for k in ("cell_fall", "cell_rise", "fall_transition", "rise_transition"):
                    g.append(_table(k, tmpl_name, char["index_1"], char["index_2"], tabs[k]).rstrip("\n"))
                g.append('        }')
                out.append("\n".join(g))
    return "\n".join(out)


def write_liberty(src_lib_path, chars, out_path, lib_name_suffix="_gsspice"):
    """Copy ``src_lib_path`` with the timing groups of the characterised cells replaced."""
    text = Path(src_lib_path).read_text()
    text = re.sub(r'(library\s*\(\s*"?)([\w.]+)("?\s*\))', lambda m: m.group(1) + m.group(2) + lib_name_suffix + m.group(3),
                  text, count=1)
    for cell, ch in chars.items():
        m = re.search(r'\n\s*cell\s*\(\s*"?sky130_fd_sc_hd__%s"?\s*\)\s*\{' % re.escape(cell), text)
        start, i, depth = m.end() - 1, m.end() - 1, 0
        while True:
            depth += text[i] == "{"; depth -= text[i] == "}"
            if depth == 0:
                break
            i += 1
        body = text[start:i + 1]
        pm = re.search(r'\n\s*pin\s*\(\s*"?%s"?\s*\)\s*\{' % ch["outpin"], body)
        ps, j, depth = pm.end() - 1, pm.end() - 1, 0
        while True:
            depth += body[j] == "{"; depth -= body[j] == "}"
            if depth == 0:
                break
            j += 1
        pbody = body[ps:j + 1]
        tm = re.search(r'cell_rise\s*\(\s*"?([\w]+)"?\s*\)', pbody)
        tmpl_name = tm.group(1) if tm else "del_1_7_7"
        # drop the original timing groups of this pin
        out, k = [], 0
        for g in re.finditer(r'\n\s*timing\s*\(\s*\)\s*\{', pbody):
            if g.start() < k:
                continue
            s0, s1, depth = g.end() - 1, g.end() - 1, 0
            while True:
                depth += pbody[s1] == "{"; depth -= pbody[s1] == "}"
                if depth == 0:
                    break
                s1 += 1
            out.append(pbody[k:g.start()])
            k = s1 + 1
        out.append(pbody[k:])
        new_pbody = "".join(out)
        new_pbody = new_pbody[:-1].rstrip() + "\n" + timing_groups(ch, tmpl_name) + "\n    }"
        new_body = body[:ps] + new_pbody + body[j + 1:]
        text = text[:start] + new_body + text[i + 1:]
    Path(out_path).write_text(text)
    return out_path

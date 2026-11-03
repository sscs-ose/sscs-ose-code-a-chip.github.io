"""Flip-flop and boundary-net energy from Liberty, so that designs with different
register counts and positions can be compared on total energy.

Per flip-flop and clock cycle:
  clock    E_int(CLK rise) + E_int(CLK fall)  (input-pin internal power)
           + (1 + k_tree) C_CLK VDD^2: the clock pin itself plus its share of the clock
           tree (buffers and wires).  k_tree = 9 is calibrated on the OpenROAD clock
           trees of the layout study (SKY130 HD, 64-127 flops: 48-61 fJ of clock-tree
           energy per flop and cycle, about 9x the pin's own C V^2).
  data     E_int(D rise/fall) per D toggle
  output   E_int(Q rise/fall, related to CLK, at the Q load) + 1/2 C_Q VDD^2 per Q toggle
Primary-input nets: 1/2 C VDD^2 per toggle.
Internal-power groups with ``when`` conditions are averaged.  Units follow the
library (``liberty_units``).
"""
from __future__ import annotations

import re
from collections import defaultdict

from .liberty import _strip_comments, _blocks, _csv, _TEMPLATES, bilinear, read_liberty_text, load_templates, _table
from .liberty_power import liberty_units


def _table1d(body, template):
    tv = _TEMPLATES.get((template or "").strip().strip('"'))
    try:
        idx = _csv(body, "index_1")
    except ValueError:
        idx = tv[2] if tv else None
    m = re.search(r"\bvalues\s*\((.*?)\)\s*;", body, re.S)
    vals = [float(x) for row in re.findall(r'"([^"]+)"', m.group(1)) for x in row.split(",")]
    if idx is None or len(idx) != len(vals):
        if len(vals) == 1:
            return (0.0, 1.0), (vals[0], vals[0])
        raise ValueError("1-D table shape")
    return tuple(idx), tuple(vals)


def _interp1(tab, x):
    xs, ys = tab
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i]) if xs[i + 1] != xs[i] else 0.0
            return ys[i] * (1 - t) + ys[i + 1] * t
    return ys[-1]


class FlopEnergy:
    def __init__(self, lib_path, lib, libcells, clock_tree_factor=9.0):
        self.k_tree = clock_tree_factor
        text = _strip_comments(read_liberty_text(lib_path))
        load_templates(text)
        u = liberty_units(lib_path)
        self.vdd, self.tu, self.cu, self.eu = u["vdd"], u["time_ps"], u["cap_ff"], u["energy_fj"]
        self.lib = lib
        self.tabs = {}
        for name in libcells:
            m = re.search(r'cell\s*\(\s*"?' + re.escape(name) + r'"?\s*\)\s*\{', text)
            depth, j = 0, m.end() - 1
            while True:
                depth += text[j] == "{"; depth -= text[j] == "}"
                if depth == 0:
                    break
                j += 1
            body = text[m.end():j]
            t = defaultdict(list)
            for pin, pb in _blocks(body, "pin"):
                pin = pin.strip('"')
                out = re.search(r'direction\s*:\s*"?output', pb) is not None
                for _, ip in _blocks(pb, "internal_power"):
                    for kind in ("rise_power", "fall_power"):
                        blk = list(_blocks(ip, kind))
                        if not blk:
                            continue
                        tmpl, tb = blk[0]
                        try:
                            tab = _table(tb, tmpl) if out else _table1d(tb, tmpl)
                        except ValueError:
                            try:
                                tab = _table1d(tb, tmpl)
                            except Exception:
                                continue
                        t[(pin, kind)].append(tab)
            self.tabs[name] = t

    def _e(self, cell, pin, kind, slew_ps, load_ff=None):
        tabs = self.tabs.get(cell, {}).get((pin, kind), [])
        if not tabs:
            return 0.0
        vals = []
        for tab in tabs:
            if isinstance(tab, tuple):
                vals.append(_interp1(tab, slew_ps / self.tu))
            else:
                vals.append(bilinear(tab, slew_ps / self.tu, (load_ff or 0.0) / self.cu))
        return sum(vals) / len(vals) * self.eu

    def per_flop(self, f, q_load_ff, clk_slew_ps=40.0, d_slew_ps=40.0):
        """(E_clock per cycle, E per D toggle, E per Q toggle) in fJ (averaged rise/fall)."""
        lc = self.lib.cells[f.libcell]
        c_clk = lc.pin_capacitance.get(f.clk_pin, 0.0)
        e_clk = (self._e(f.libcell, f.clk_pin, "rise_power", clk_slew_ps) +
                 self._e(f.libcell, f.clk_pin, "fall_power", clk_slew_ps) +
                 (1.0 + self.k_tree) * c_clk * self.vdd ** 2)
        e_d = 0.5 * (self._e(f.libcell, f.d_pin, "rise_power", d_slew_ps) +
                     self._e(f.libcell, f.d_pin, "fall_power", d_slew_ps))
        qp = f.q_pin or f.qn_pin
        e_q = 0.5 * (self._e(f.libcell, qp, "rise_power", clk_slew_ps, q_load_ff) +
                     self._e(f.libcell, qp, "fall_power", clk_slew_ps, q_load_ff)) + 0.5 * q_load_ff * self.vdd ** 2
        return e_clk, e_d, e_q


def sequential_energy(design, states, cycles_idx, loads, fe, clk_slew_ps=40.0):
    """Energy (fJ) of flip-flops and real-input nets over the listed cycles, from the
    functional per-cycle states (``states[c]``: settled values at the end of cycle c).
    Returns dict(clock, data, q, inputs, total, n_flops)."""
    out = dict(clock=0.0, data=0.0, q=0.0, inputs=0.0)
    per = {f.name: fe.per_flop(f, loads.get(f.q or f.qn, 0.0), clk_slew_ps) for f in design.flops}
    half_cv2 = {pi: 0.5 * loads.get(pi, 0.0) * fe.vdd ** 2 for pi in design.real_inputs}
    for c in cycles_idx:
        if c <= 0:
            continue
        a, b = states[c - 1], states[c]
        for f in design.flops:
            e_clk, e_d, e_q = per[f.name]
            out["clock"] += e_clk
            q = f.q or f.qn
            if a.get(q) != b.get(q):
                out["q"] += e_q
            if a.get(f.d) != b.get(f.d):
                out["data"] += e_d
        for pi, e in half_cv2.items():
            if a.get(pi) != b.get(pi):
                out["inputs"] += e
    out["total"] = sum(out.values())
    out["n_flops"] = len(design.flops)
    return out

"""Bring-your-own-design: sequential netlists driven by a testbench VCD.

The design is cut at its D flip-flops.  For every rising clock edge:
  * flop states update to the functional (zero-delay) D values captured at the edge;
  * each flop Q launches at edge + Liberty clock-to-Q delay (rise/fall, Q load);
  * primary inputs change at their actual VCD times inside the cycle.
All changes inside one cycle form one analysis step (same epoch id), so glitch
classification and energy are reported per clock cycle.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from .functional import evaluate_stable
from .logic import eval_primitive
from .liberty import _strip_comments, _blocks, _table, bilinear, read_liberty_text, load_templates

# ---------------------------------------------------------------- VCD


def read_vcd(path, scope=None):
    """Return ({bit_name: [(time_fs, value), ...]}, timescale_fs).

    Vectors are bit-blasted to 'name[i]'.  Only 0/1 values are kept (x/z -> 0).
    ``scope``: only variables declared directly in this module scope (default: first scope).
    """
    text = Path(path).read_text(errors="replace")
    ts = re.search(r"\$timescale\s+(\d+)\s*(fs|ps|ns|us|ms|s)\s+\$end", text)
    unit = {"fs": 1, "ps": 1e3, "ns": 1e6, "us": 1e9, "ms": 1e12, "s": 1e15}
    tsc = int(ts.group(1)) * unit[ts.group(2)] if ts else 1e3
    header, _, body = text.partition("$enddefinitions")
    ids = defaultdict(list)          # id -> [(name, width, lsb)]
    depth, cur_scope, first_scope = 0, None, None
    for tok in re.finditer(r"\$scope\s+\w+\s+(\S+)\s+\$end|\$upscope\s+\$end|"
                           r"\$var\s+\w+\s+(\d+)\s+(\S+)\s+(\S+)(?:\s+\[(\d+)(?::(\d+))?\])?\s+\$end", header):
        if tok.group(1):
            depth += 1; cur_scope = tok.group(1)
            first_scope = first_scope or cur_scope
            continue
        if tok.group(0).startswith("$upscope"):
            depth -= 1; continue
        if (scope or first_scope) != cur_scope:
            continue
        width, code, name = int(tok.group(2)), tok.group(3), tok.group(4)
        msb = int(tok.group(5)) if tok.group(5) else width - 1
        lsb = int(tok.group(6)) if tok.group(6) else (msb if width == 1 and tok.group(5) else 0)
        ids[code].append((name, width, lsb, tok.group(5) is not None))
    waves = defaultdict(list)
    t = 0
    for line in body.split("\n"):
        line = line.strip()
        if not line or line.startswith("$"):
            continue
        if line[0] == "#":
            t = int(int(line[1:]) * tsc); continue
        if line[0] in "01xzXZ":
            val, code = line[0], line[1:]
            for name, width, lsb, vec in ids.get(code, []):
                waves[f"{name}[{lsb}]" if vec else name].append((t, 1 if val == "1" else 0))
        elif line[0] in "bB":
            bits, code = line[1:].split()
            for name, width, lsb, vec in ids.get(code, []):
                bits_ = bits.rjust(width, "0" if bits[0] in "01" else bits[0])[-width:]
                for i, ch in enumerate(reversed(bits_)):
                    nm = f"{name}[{lsb + i}]" if (width > 1 or vec) else name
                    waves[nm].append((t, 1 if ch == "1" else 0))
    return dict(waves), tsc


# ---------------------------------------------------------------- clock-to-Q


def read_clk_to_q(lib_path, libcells):
    """{libcell: {output_pin: (cell_rise Table2D, cell_fall Table2D)}} for the clock->output
    rising_edge arcs of every output pin (Q, QN, ...)."""
    text = _strip_comments(read_liberty_text(lib_path))
    load_templates(text)
    out = {}
    for name in libcells:
        m = re.search(r'cell\s*\(\s*"?' + re.escape(name) + r'"?\s*\)\s*\{', text)
        depth, j = 0, m.end() - 1
        while True:
            depth += text[j] == "{"; depth -= text[j] == "}"
            if depth == 0:
                break
            j += 1
        body = text[m.end():j]
        for pin, pb in _blocks(body, "pin"):
            if not re.search(r'direction\s*:\s*"?output', pb):
                continue
            for _, tb in _blocks(pb, "timing"):
                if re.search(r'timing_type\s*:\s*"?rising_edge', tb):
                    rise = _table(*reversed(next(_blocks(tb, "cell_rise"))))
                    fall = _table(*reversed(next(_blocks(tb, "cell_fall"))))
                    out.setdefault(name, {})[pin.strip('"')] = (rise, fall)
    return out


# ---------------------------------------------------------------- cycles


def build_cycles(design, waves, lib, clk_to_q, loads, clock=None, clk_slew_ps=40.0,
                 input_delay_ps=None, start=0, init_state=None):
    """Return (initial_state, cycles) where cycles[k] = [(offset_fs, {net: value}), ...].

    Offsets are relative to the cycle's rising clock edge.  ``input_delay_ps``
    overrides VCD input timing (all inputs change at edge + input_delay).
    ``start``: begin at that rising edge; ``init_state``: the state just before it
    ({net: value} for the combinational inputs; default: inputs from the VCD, Q = 0)."""
    net = design.network
    clock = clock or (design.clocks[0] if design.clocks else None)
    if clock is None or clock not in waves:
        raise ValueError(f"clock not found in VCD (design clocks: {design.clocks})")
    cw = waves[clock]
    edges = [t for (t, v), (_, pv) in zip(cw[1:], cw[:-1]) if v == 1 and pv == 0]
    if cw and cw[0][1] == 1 and cw[0][0] > 0:
        edges = [cw[0][0]] + edges
    if len(edges) < 2:
        raise ValueError("need at least two rising clock edges")
    edges = edges[start:]

    def value_at(name, t):
        v = 0
        for tt, vv in waves.get(name, []):
            if tt > t:
                break
            v = vv
        return v

    t_start = edges[0]
    state = {n: v for n, v in net.initial_inputs.items() if n not in design.real_inputs}   # tie constants
    state.update({pi: value_at(pi, t_start) for pi in design.real_inputs})
    for f in design.flops:                       # state 0: Q = 0, QN = 1
        for qn_, _, inv in f.outputs:
            state[qn_] = inv
    if init_state is not None:
        state = {n: init_state.get(n, state.get(n, 0)) for n in set(state) | set(net.primary_inputs)}
    init = dict(state)
    cycles = []
    for k, te in enumerate(edges):
        tn = edges[k + 1] if k + 1 < len(edges) else te + (edges[-1] - edges[-2])
        steps = defaultdict(dict)
        # flops capture functional D values at the edge (state before the edge)
        settled = evaluate_stable(net, state)
        for f in design.flops:
            newq = settled[f.d] if f.d in settled else state.get(f.d, 0)
            if f.clear or f.preset:              # async set/reset, applied at the edge
                pv = {p: settled.get(n_, state.get(n_, 0)) for p, n_ in f.ctrl.items()}
                if f.clear and eval_primitive("LIB:" + f.clear, pv):
                    newq = 0
                elif f.preset and eval_primitive("LIB:" + f.preset, pv):
                    newq = 1
            for qnet, pin, inv in f.outputs:
                v = newq ^ inv
                if v != state[qnet]:
                    rise, fall = clk_to_q[f.libcell][pin]
                    tab = rise if v else fall
                    d_lib = bilinear(tab, clk_slew_ps / lib.time_unit_ps,
                                     loads.get(qnet, 0.0) / lib.capacitance_unit_ff)
                    off = int(round(d_lib * lib.time_unit_ps * 1000))
                    steps[off][qnet] = v
        # primary inputs: actual VCD changes inside (te, tn]  (or forced input delay)
        for pi in design.real_inputs:
            for tt, vv in waves.get(pi, []):
                if te <= tt < tn:
                    off = int(round(input_delay_ps * 1000)) if input_delay_ps is not None else tt - te
                    if off >= tn - te:
                        continue
                    steps[off][pi] = vv
        # apply in time order to the running state; drop no-op updates
        cyc = []
        for off in sorted(steps):
            upd = {n: v for n, v in steps[off].items() if state[n] != v}
            if upd:
                cyc.append((off, upd))
                state.update(upd)
        cycles.append(cyc)
    return init, cycles, edges


def random_waves(design, n_cycles, period_ps, seed=1, clock=None):
    """Synthetic testbench for designs without a VCD: a clock with ``n_cycles`` rising
    edges (period ``period_ps``, first edge at one period) and every real input set to
    a uniformly random value once per cycle, just after each rising edge (the exact
    instant is set by ``input_delay_ps`` in :func:`build_cycles`)."""
    import random as _random
    rnd = _random.Random(seed)
    clock = clock or (design.clocks[0] if design.clocks else "clk")
    P = int(round(period_ps * 1000))
    waves = {clock: [(0, 0)]}
    for k in range(1, n_cycles + 2):
        waves[clock] += [(k * P, 1), (k * P + P // 2, 0)]
    for pi in design.real_inputs:
        w = [(0, rnd.randint(0, 1))]
        for k in range(1, n_cycles + 1):
            w.append((k * P + 1000, rnd.randint(0, 1)))     # 1 ps after the edge
        waves[pi] = w
    return waves, clock

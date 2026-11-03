"""Register retiming and pipelining on a gate-level netlist (Leiserson-Saxe).

The design is a graph whose nodes are the combinational cells plus *sources*
(real inputs, outputs of fixed flip-flops, tie constants) and *sinks* (real
outputs, inputs of fixed flip-flops).  An edge per cell input pin (or sink)
carries ``w`` = the number of movable flip-flops between the driving node and
that pin.  Plain D flip-flops are movable; flip-flops with asynchronous
set/reset or only an inverted output stay where they are (as a source/sink
pair).

A retiming is an integer lag ``r(v)`` per node (sources 0, sinks ``L`` =
added latency).  Edge weights become ``w_r(u,v) = w(u,v) + r(v) - r(u)``; the
retiming is legal when all are >= 0.  Node ``v`` of the retimed circuit computes
at cycle t what the original computed at cycle ``t - r(v)``, so every output is
delayed by exactly ``L`` cycles and the function is otherwise unchanged
(feedback loops keep their register count).  ``rebuild`` writes the retimed
netlist (registers on a driver's fan-out edges are shared as a chain).

``thresholds_to_lags`` maps register positions given as arrival-time cuts to
lags and projects them onto the legal set (difference constraints).
"""
from __future__ import annotations

import math
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .liberty import bilinear


@dataclass
class RGraph:
    design: object
    cells: list                       # combinational Cell objects (node ids 0..C-1)
    sources: List[str]                # source nets (node ids C..C+S-1)
    sinks: List[Tuple[str, str]]      # (kind, name): ("po", port) | ("ffd", flop name) | ("ffc", "flop.pin")
    edges: List[Tuple[int, int, str, int]]   # (u, v, pin, w); v is a cell (pin = input pin) or a sink (pin = "")
    movable: list                     # movable Flop objects
    fixed: list                       # fixed Flop objects
    flop_libcell: str = ""
    out_net: Dict[int, str] = field(default_factory=dict)   # node -> driven net name
    lag_fixed: Dict[int, int] = field(default_factory=dict)  # sources / sinks with fixed lag (sinks: +L)

    @property
    def C(self):
        return len(self.cells)

    @property
    def n(self):
        return len(self.cells) + len(self.sources) + len(self.sinks)

    def is_sink(self, v):
        return v >= self.C + len(self.sources)

    def is_source(self, v):
        return self.C <= v < self.C + len(self.sources)


def build_rgraph(design, movable=None, keep_io=False):
    """Retiming graph of a design.  ``movable``: flop names allowed to move
    (default: every plain D flip-flop with a Q output and no async control).
    ``keep_io``: flip-flops fed directly by an input port or driving an output port
    stay in place (the block keeps registered inputs / outputs)."""
    net = design.network
    cells = list(net.cells)
    drv = {c.output: i for i, c in enumerate(cells)}

    def plain(f):
        return f.q is not None and f.qn is None and not f.clear and not f.preset and not f.ctrl

    io_in = set(design.real_inputs)
    io_out = set(design.port_net.values()) | set(design.real_outputs)
    mov = [f for f in design.flops if (plain(f) if movable is None else f.name in movable)
           and not (keep_io and (f.d in io_in or f.q in io_out))]
    fixed = [f for f in design.flops if f not in mov]
    by_q = {f.q: f for f in mov}
    sources, src_id = [], {}

    def source(nm):
        if nm not in src_id:
            src_id[nm] = len(sources)
            sources.append(nm)
        return src_id[nm]

    def trace(nm):
        w, seen = 0, set()
        while nm in by_q:
            if nm in seen:
                raise ValueError(f"register loop without logic at {nm}")
            seen.add(nm)
            w += 1
            nm = by_q[nm].d
        return ("c", drv[nm]) if nm in drv else ("s", source(nm)), w

    raw = []                                     # (kind, id, v_tag, pin, w)
    for i, c in enumerate(cells):
        for pin, nm in c.inputs.items():
            (k, u), w = trace(nm)
            raw.append((k, u, ("c", i), pin, w))
    sinks = []
    for port in design.output_ports:
        nm = design.port_net.get(port, port)
        (k, u), w = trace(nm)
        raw.append((k, u, ("t", len(sinks)), "", w))
        sinks.append(("po", port))
    for f in fixed:
        (k, u), w = trace(f.d)
        raw.append((k, u, ("t", len(sinks)), "", w))
        sinks.append(("ffd", f.name))
        for pin, nm in f.ctrl.items():
            (k, u), w = trace(nm)
            raw.append((k, u, ("t", len(sinks)), "", w))
            sinks.append(("ffc", f"{f.name}.{pin}"))
    C, S = len(cells), len(sources)

    def nid(tag):
        k, x = tag
        return x if k == "c" else (C + x if k == "s" else C + S + x)

    edges = [(nid((k, u)), nid(v), pin, w) for k, u, v, pin, w in raw]
    rg = RGraph(design, cells, sources, sinks, edges, mov, fixed)
    rg.flop_libcell = max({f.libcell for f in mov}, key=lambda x: sum(f.libcell == x for f in mov)) if mov else ""
    rg.out_net = {i: c.output for i, c in enumerate(cells)}
    rg.out_net.update({C + j: s for j, s in enumerate(sources)})
    return rg


# ----------------------------------------------------------------------------- lags
def fixed_lags(rg, latency=0):
    if latency and rg.fixed:
        raise ValueError("added latency needs every flip-flop to be movable (fixed flops would get out of step)")
    C, S = rg.C, len(rg.sources)
    lf = {C + j: 0 for j in range(S)}
    lf.update({C + S + j: latency for j in range(len(rg.sinks))})
    return lf


def retimed_weights(rg, r):
    return [w + r[v] - r[u] for u, v, _, w in rg.edges]


def is_legal(rg, r):
    return all(x >= 0 for x in retimed_weights(rg, r))


def legalize(rg, target, fixed, direction="down"):
    """Project lags onto the legal set.  ``down``: the greatest legal lags <= target;
    ``up``: the least legal lags >= target.  None if no such retiming exists."""
    r = list(target)
    for v, x in fixed.items():
        r[v] = x
    out_e, in_e = defaultdict(list), defaultdict(list)
    for u, v, _, w in rg.edges:
        out_e[u].append((v, w))
        in_e[v].append((u, w))
    q, inq = deque(range(rg.n)), [True] * rg.n
    it = 0
    while q:
        x = q.popleft(); inq[x] = False
        it += 1
        if it > 50 * rg.n + 1000:
            return None
        if direction == "down":         # r(u) <= r(v) + w for every edge u -> v
            for u, w in in_e[x]:
                if r[u] > r[x] + w:
                    if u in fixed:
                        return None
                    r[u] = r[x] + w
                    if not inq[u]:
                        q.append(u); inq[u] = True
        else:                           # r(v) >= r(u) - w
            for v, w in out_e[x]:
                if r[v] < r[x] - w:
                    if v in fixed:
                        return None
                    r[v] = r[x] - w
                    if not inq[v]:
                        q.append(v); inq[v] = True
    return r if is_legal(rg, r) else None


def loop_edges(rg):
    """Per edge: True if it carries registers and lies on a cycle (a loop register)."""
    n = rg.n
    adj = defaultdict(list)
    for u, v, _, w in rg.edges:
        adj[u].append(v)
    # iterative Tarjan SCC
    index, low, onst, comp = [None] * n, [0] * n, [False] * n, [-1] * n
    st, cnt, nc = [], 0, 0
    for s0 in range(n):
        if index[s0] is not None:
            continue
        work = [(s0, 0)]
        while work:
            v, i = work.pop()
            if i == 0:
                index[v] = low[v] = cnt; cnt += 1
                st.append(v); onst[v] = True
            recurse = False
            nb = adj[v]
            while i < len(nb):
                x = nb[i]; i += 1
                if index[x] is None:
                    work.append((v, i)); work.append((x, 0)); recurse = True
                    break
                if onst[x]:
                    low[v] = min(low[v], index[x])
            if recurse:
                continue
            if low[v] == index[v]:
                while True:
                    x = st.pop(); onst[x] = False; comp[x] = nc
                    if x == v:
                        break
                nc += 1
            if work:
                p = work[-1][0]
                low[p] = min(low[p], low[v])
    return [w > 0 and comp[u] == comp[v] for u, v, _, w in rg.edges]


def feedforward_registers(rg):
    """Per node: the most feedforward registers on any path from a source (loop
    registers not counted)."""
    if getattr(rg, "_wmax", None) is not None:
        return rg._wmax
    loop = loop_edges(rg)
    inc = defaultdict(list)
    for k, (u, v, _, w) in enumerate(rg.edges):
        if not loop[k]:
            inc[v].append((u, w))
    wmax = [0] * rg.n
    for v in comb_order(rg, loop):
        if inc[v]:
            wmax[v] = max(wmax[u] + w for u, w in inc[v])
    rg._wmax = wmax
    return wmax


def comb_order(rg, cut):
    indeg = [0] * rg.n
    outs = defaultdict(list)
    for k, (u, v, _, w) in enumerate(rg.edges):
        if not cut[k]:
            indeg[v] += 1
            outs[u].append(v)
    q = deque(v for v in range(rg.n) if indeg[v] == 0)
    order = []
    while q:
        x = q.popleft(); order.append(x)
        for v in outs[x]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    if len(order) != rg.n:
        raise ValueError("combinational loop")
    return order


# ----------------------------------------------------------------------------- timing
class Timing:
    """Static timing on the graph with Liberty NLDM delays (worst arc per input pin,
    worst-slew propagation).  Registers launch at clock-to-Q and need ``setup_ps``."""

    def __init__(self, rg, lib, dp, loads, clk_to_q_ps=None, setup_ps=100.0, input_slew_ps=40.0,
                 input_delay_ps=0.0):
        self.rg, self.lib = rg, lib
        tu, cu = lib.time_unit_ps, lib.capacitance_unit_ff
        self.setup, self.in_slew, self.in_delay = setup_ps, input_slew_ps, input_delay_ps
        self.c2q = clk_to_q_ps if clk_to_q_ps is not None else 300.0
        # per (cell, pin): list of arcs (delay tables, slew tables)
        self.arcs = {}
        for i, c in enumerate(rg.cells):
            lc = lib.cells[c.library_cell]
            for pin in c.inputs:
                arcs = [a for a in lc.timing_arcs if a.related_pin == pin and a.output_pin == c.library_output_pin]
                self.arcs[(i, pin)] = arcs
            self.load_ff = None
        self.loads = loads
        self.tu, self.cu = tu, cu
        self.loop = loop_edges(rg)

    def _topo(self, cut):
        """Topological order over the edges that are not cut by a register."""
        return comb_order(self.rg, cut)

    def _arc_out(self, i, pin, a_in, s_in):
        """Rise / fall arrival and slew at cell i's output from input pin ``pin``
        (a_in, s_in: (rise, fall) arrival and slew at the pin), Liberty unateness."""
        c = self.rg.cells[i]
        load = self.loads.get(c.output, 0.0) / self.cu
        tu = self.tu
        ar = af = -1.0
        sr = sf = 0.0
        for a in self.arcs[(i, pin)]:
            sense = (a.timing_sense or "").strip('"')
            srcs_r = (0,) if sense == "positive_unate" else (1,) if sense == "negative_unate" else (0, 1)
            srcs_f = (1,) if sense == "positive_unate" else (0,) if sense == "negative_unate" else (0, 1)
            if a.cell_rise is not None:
                for k in srcs_r:
                    x = s_in[k] / tu
                    t = a_in[k] + bilinear(a.cell_rise, x, load) * tu
                    if t > ar:
                        ar = t
                        sr = bilinear(a.rise_transition, x, load) * tu if a.rise_transition is not None else s_in[k]
            if a.cell_fall is not None:
                for k in srcs_f:
                    x = s_in[k] / tu
                    t = a_in[k] + bilinear(a.cell_fall, x, load) * tu
                    if t > af:
                        af = t
                        sf = bilinear(a.fall_transition, x, load) * tu if a.fall_transition is not None else s_in[k]
        return (ar, af), (sr, sf)

    def analyze(self, weights=None):
        """Arrival time (ps, max of rise/fall) at every node output, rise/fall-aware
        with Liberty timing senses.  ``weights=None``: registers are transparent
        (concatenated arrival, for placing cuts); otherwise an edge with w > 0
        restarts at clock-to-Q.  Returns (arrival, slew, period)."""
        rg, n = self.rg, self.rg.n
        s0 = (self.in_slew, self.in_slew)
        A, SL = [(0.0, 0.0)] * n, [s0] * n
        for j in range(len(rg.sources)):
            A[rg.C + j] = (self.in_delay, self.in_delay)
        period = 0.0
        inc = defaultdict(list)
        for k, (u, v, pin, w) in enumerate(rg.edges):
            inc[v].append((u, pin, w if weights is None else weights[k]))
        launch = (self.c2q, self.c2q)
        if weights is None:      # feedforward registers transparent, loop registers cut
            weights = [1 if lp else 0 for lp in self.loop]
            inc = defaultdict(list)
            for k, (u, v, pin, w) in enumerate(rg.edges):
                inc[v].append((u, pin, weights[k]))
            transparent = True
        else:
            transparent = False
        order = self._topo([w > 0 for w in weights])
        for v in order:
            if v < rg.C:
                ar = af = 0.0
                sr = sf = self.in_slew
                for u, pin, w in inc[v]:
                    if w > 0:
                        a_in, s_in = launch, s0
                    else:
                        a_in, s_in = A[u], SL[u]
                    (r_, f_), (rs, fs) = self._arc_out(v, pin, a_in, s_in)
                    if r_ > ar:
                        ar, sr = r_, rs
                    if f_ > af:
                        af, sf = f_, fs
                A[v], SL[v] = (ar, af), (sr, sf)
            elif rg.is_sink(v):
                A[v] = max((A[u] if w == 0 else launch for u, _, w in inc[v]), default=(0.0, 0.0), key=max)
        # period: every register input (setup) and every output, after all arrivals are known
        for v in range(n):
            if v < rg.C or rg.is_sink(v):
                po = rg.is_sink(v) and rg.sinks[v - rg.C - len(rg.sources)][0] == "po"
                for u, pin, w in inc[v]:
                    if w > 0:
                        period = max(period, max(A[u]) + self.setup)
                    elif rg.is_sink(v):
                        period = max(period, max(A[u]) + (0.0 if po else self.setup))
        if not transparent and any(w > 1 for w in weights):
            period = max(period, self.c2q + self.setup)    # register-to-register hop
        return [max(x) for x in A], SL, period


def thresholds_to_lags(rg, arrival, thresholds, base_w, latency=0, direction="down", window=0.0):
    """Lags that put register bank i at arrival time ``thresholds[i]`` (ps, sorted;
    0 = at the sources, inf = at the sinks), projected onto the legal retimings.
    ``window`` > 0: each inner bank may bend within +-window ps of its threshold to
    the position with the fewest registers (minimum cut, registers shared per net)."""
    n, C, S = rg.n, rg.C, len(rg.sources)
    fixed = fixed_lags(rg, latency)
    wmax = feedforward_registers(rg)
    pre = pre_loop(rg)
    th = sorted(thresholds)
    crossed = [0] * n
    for i, t in enumerate(th):
        if window > 0 and 0 < t < math.inf:
            gap_lo = t - (th[i - 1] if i > 0 else 0.0)
            gap_hi = (th[i + 1] if i + 1 < len(th) else math.inf) - t
            dlt = min(window, 0.45 * gap_lo, 0.45 * gap_hi)
            after = min_register_cut(rg, arrival, t - dlt, t + dlt, pre)
        else:
            after = [arrival[v] >= t for v in range(n)]
        for v in range(C):
            crossed[v] += bool(after[v])
    target = [0] * n
    for v in range(C):
        if pre[v]:
            target[v] = crossed[v] - wmax[v]
    return legalize(rg, target, fixed, direction)


def min_register_cut(rg, arrival, lo, hi, pre=None):
    """One register bank crossing every path between arrival times ``lo`` and ``hi``
    with the fewest registers (one per driving net).  Returns, per node, True if the
    node lies after the bank.  Nodes outside the feedforward region are after it."""
    n, C = rg.n, rg.C
    pre = pre if pre is not None else pre_loop(rg)
    INF = 1 << 30
    # node u -> u_in = 2u, u_out = 2u+1; s = 2n, t = 2n+1
    src, snk = 2 * n, 2 * n + 1
    rows, cols, caps = [], [], []

    def add(a, b, c):
        rows.append(a); cols.append(b); caps.append(c)
    for v in range(n):
        inside = (v < C and pre[v]) or rg.is_source(v)
        if not inside or rg.is_source(v) or arrival[v] < lo:
            if inside:
                add(src, 2 * v, INF)          # before the bank
            else:
                add(2 * v, snk, INF)          # after the bank
        elif arrival[v] > hi:
            add(2 * v, snk, INF)
        add(2 * v, 2 * v + 1, 1)              # a register on v's output net
    for u, v, _, w in rg.edges:
        add(2 * u + 1, 2 * v, INF)            # u after the bank => v after it
        add(2 * v, 2 * u, INF)                # v before => u before (fan-in closed)
    N = 2 * n + 2
    side = _min_cut_source_side(N, rows, cols, caps, src, snk)
    return [not side[2 * v] for v in range(n)]


def _min_cut_source_side(N, rows, cols, caps, s, t):
    """Source side of a minimum s-t cut (scipy's max-flow when available)."""
    try:
        import numpy as np
        from scipy.sparse import csr_matrix
        from scipy.sparse.csgraph import maximum_flow
        # merge parallel edges
        agg = {}
        for a, b, c in zip(rows, cols, caps):
            agg[(a, b)] = min(agg.get((a, b), 0) + c, 1 << 30)
        r = np.fromiter((k[0] for k in agg), dtype=np.int32, count=len(agg))
        c_ = np.fromiter((k[1] for k in agg), dtype=np.int32, count=len(agg))
        cap = np.fromiter(agg.values(), dtype=np.int32, count=len(agg))
        g = csr_matrix((cap, (r, c_)), shape=(N, N))
        res = maximum_flow(g, s, t)
        flow = res.flow.tocsr() if hasattr(res, "flow") else res.residual.tocsr()
        resid = (g - flow).tocsr()
        # also reverse residual capacity: flow on (a,b) allows b -> a
        rev = flow.transpose().tocsr()
        seen = np.zeros(N, dtype=bool)
        seen[s] = True
        stack = [s]
        while stack:
            x = stack.pop()
            for M in (resid, rev):
                for k in range(M.indptr[x], M.indptr[x + 1]):
                    y = M.indices[k]
                    if M.data[k] > 0 and not seen[y]:
                        seen[y] = True
                        stack.append(y)
        return seen.tolist()
    except ImportError:
        pass
    # pure-Python Edmonds-Karp fallback
    cap = defaultdict(int)
    adj = defaultdict(set)
    for a, b, c in zip(rows, cols, caps):
        cap[(a, b)] += c
        adj[a].add(b); adj[b].add(a)
    while True:
        par = {s: None}
        q = deque([s])
        while q and t not in par:
            x = q.popleft()
            for y in adj[x]:
                if y not in par and cap[(x, y)] > 0:
                    par[y] = x; q.append(y)
        if t not in par:
            return [x in par for x in range(N)]
        f, y = 1 << 30, t
        while par[y] is not None:
            f = min(f, cap[(par[y], y)]); y = par[y]
        y = t
        while par[y] is not None:
            cap[(par[y], y)] -= f; cap[(y, par[y])] += f; y = par[y]


def pre_loop(rg):
    """Per node: True if no register loop (strongly connected logic with registers)
    reaches it, i.e. it belongs to the feedforward logic in front of all loops."""
    if getattr(rg, "_pre", None) is not None:
        return rg._pre
    loop = loop_edges(rg)
    seeds = {rg.edges[k][0] for k in range(len(rg.edges)) if loop[k]} | \
            {rg.edges[k][1] for k in range(len(rg.edges)) if loop[k]}
    outs = defaultdict(list)
    for u, v, _, w in rg.edges:
        outs[u].append(v)
    reach = set(seeds)
    q = deque(seeds)
    while q:
        x = q.popleft()
        for v in outs[x]:
            if v not in reach:
                reach.add(v); q.append(v)
    rg._pre = [v not in reach for v in range(rg.n)]
    return rg._pre


def banks(rg, latency=0):
    """Register banks the cut positions describe: the most registers on a path
    from a source out of the feedforward logic in front of the loops, plus latency."""
    wmax, pre = feedforward_registers(rg), pre_loop(rg)
    m = 0
    for u, v, _, w in rg.edges:
        if (pre[u] or rg.is_source(u)) and not (pre[v] and v < rg.C):
            m = max(m, wmax[u] + w)
    return m + latency


# ----------------------------------------------------------------------------- netlist
def _esc(n):
    return n if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", n) else "\\" + n + " "


def _port_decls(names, kind):
    """One scalar declaration per port bit (as Yosys writes after ``splitnets -ports``):
    bit names such as ``a[3]`` become escaped identifiers ``\\a[3] ``, the same spelling the
    instance connections use, so ports and connections always refer to the same net."""
    return list(names), [f"  {kind} {_esc(nm)};" for nm in names]


def rebuild(rg, r, lib, header=""):
    """Verilog text of the retimed design.  Returns (text, chains) where
    chains[node] = list of register output nets (depth 1..D)."""
    d = rg.design
    wr = retimed_weights(rg, r)
    if min(wr, default=0) < 0:
        raise ValueError("illegal retiming")
    C, S = rg.C, len(rg.sources)
    depth = defaultdict(int)
    for (u, v, pin, w), x in zip(rg.edges, wr):
        depth[u] = max(depth[u], x)
    clk = d.clocks[0] if d.clocks else "clk"
    ff = rg.flop_libcell or _pick_dff(lib)
    flc = lib.cells[ff]
    dpin = flc.seq["next_state"]
    cpin = flc.seq["clocked_on"]
    qpin = next(p.name for p in flc.pins.values() if p.direction == "output"
                and (p.function or "").replace(" ", "").strip('"') == flc.seq.get("state", ("IQ",))[0])
    used = set(d.input_ports) | set(d.output_ports) | {c.output for c in rg.cells} | set(rg.sources)
    chains, lines, k = {}, [], 0
    out_net = dict(rg.out_net)

    def fresh(base):
        nm = f"{base}__gsr"
        i = 1
        while f"{nm}{i}" in used:
            i += 1
        used.add(f"{nm}{i}")
        return f"{nm}{i}"

    # an output port that is also a cell's output net but must now be driven from a
    # register: give the cell output an internal name
    ports = set(d.output_ports)
    for (u, v, pin, w), x in zip(rg.edges, wr):
        if rg.is_sink(v) and rg.sinks[v - C - S][0] == "po" and x > 0 and u < C and out_net[u] in ports:
            nm = out_net[u] + "__gsc"
            while nm in used:
                nm += "_"
            used.add(nm)
            out_net[u] = nm
    for u in sorted(depth):
        if depth[u] == 0:
            continue
        src = out_net[u]
        ch = []
        prev = src
        for j in range(depth[u]):
            q = fresh(re.sub(r"[^\w]", "_", src))
            lines.append(f"  {ff} gsreg_{k} (.{cpin}({_esc(clk)}), .{dpin}({_esc(prev)}), .{qpin}({_esc(q)}));")
            k += 1
            ch.append(q)
            prev = q
        chains[u] = ch

    def tap(u, x):
        return out_net[u] if x == 0 else chains[u][x - 1]

    pin_net = {}
    sink_net = {}
    for (u, v, pin, w), x in zip(rg.edges, wr):
        if v < C:
            pin_net[(v, pin)] = tap(u, x)
        else:
            sink_net[v - C - S] = tap(u, x)
    body = []
    for i, c in enumerate(rg.cells):
        conns = [f".{p}({_esc(pin_net[(i, p)])})" for p in c.inputs] + [f".{c.library_output_pin}({_esc(out_net[i])})"]
        body.append(f"  {c.library_cell} {_esc(c.name)} ({', '.join(conns)});")
    sink_of = {s: j for j, s in enumerate(rg.sinks)}
    for f in rg.fixed:
        conns = {f.clk_pin: clk, f.d_pin: sink_net[sink_of[("ffd", f.name)]]}
        for pin in f.ctrl:
            conns[pin] = sink_net[sink_of[("ffc", f"{f.name}.{pin}")]]
        if f.q:
            conns[f.q_pin] = f.q
        if f.qn:
            conns[f.qn_pin] = f.qn
        body.append(f"  {f.libcell} {_esc(f.name)} ({', '.join(f'.{p}({_esc(n)})' for p, n in conns.items())});")
    assigns = []
    const_src = {n_: v for n_, v in d.network.initial_inputs.items()
                 if n_ in set(rg.sources) and n_ not in d.tie_cells and n_ not in set(d.input_ports)
                 and n_ not in {q for f in d.flops for q, _, _ in f.outputs}}
    for net_, v in sorted(const_src.items()):
        assigns.append(f"  assign {_esc(net_)} = 1'b{v};")
    for net_, (libcell, pin) in sorted(d.tie_cells.items()):
        tname = "gstie_" + re.sub(r"[^\w]", "_", net_)
        body.append(f"  {libcell} {tname} (.{pin}({_esc(net_)}));")
    for j, (kind, name) in enumerate(rg.sinks):
        if kind == "po" and sink_net[j] != name:
            assigns.append(f"  assign {_esc(name)} = {_esc(sink_net[j])};")
    ins = list(d.input_ports)
    if d.clocks:
        pass
    elif any(depth.values()):
        ins = [clk] + ins
    in_order, in_decl = _port_decls(ins, "input")
    out_order, out_decl = _port_decls(d.output_ports, "output")
    wires = sorted({n for n in used if n not in set(ins) | set(d.output_ports)})
    text = [header or f"// retimed by GlitchScope (glitchscope/retime.py)",
            f"module {_esc(d.module)}({', '.join(_esc(x) for x in in_order + out_order)});"]
    text += in_decl + out_decl
    text += [f"  wire {_esc(w)};" for w in wires]
    text += lines + body + assigns + ["endmodule", ""]
    return "\n".join(text), chains


def _pick_dff(lib):
    cands = [n for n, c in lib.cells.items() if c.seq and c.seq.get("kind") == "ff" and not c.seq.get("clear")
             and not c.seq.get("preset") and re.fullmatch(r"[A-Za-z_]\w*", c.seq.get("next_state", "") or "")]
    if not cands:
        raise ValueError("no plain D flip-flop in the library")
    from .pdk import _drive_score
    return min(cands, key=lambda n: (_drive_score(n), len(lib.cells[n].pins), n))

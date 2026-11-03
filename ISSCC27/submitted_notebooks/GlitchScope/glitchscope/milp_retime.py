"""Measurement-calibrated MILP retiming (open solver: HiGHS through scipy.optimize.milp).

A retiming is chosen by a mixed-integer program over all lags r(v) — registers may
move anywhere, including inside loops — whose objective is a *glitch model calibrated
by measurement*, and every solution is then measured exactly by event simulation;
the measurements re-calibrate the model and the program is solved again.

Model.  The glitch energy a cell burns grows with how late, after the last register,
its inputs settle (the spread of arrival times grows with depth).  To first order

        E_glitch(v) ~= alpha_v * t_v

with t_v the cell's arrival time since the last register (a variable of the program)
and alpha_v (fJ per ps) fitted per cell from the measured glitch energy and the static
arrival time of every placement measured so far (least squares through the origin,
shrunk towards the design-wide ratio for cells with little data).  Registers cost
their measured energy per cycle each.

Program (n cells, e edges, one register chain per driving net):
    minimise   sum_v alpha_v t_v  +  E_reg * sum_u R_u
    subject to w(e) + r_v - r_u >= 0                                  (legal retiming)
               R_u >= w(e) + r_v - r_u                    for every edge leaving u
               t_v >= t_u + d_v - B (w(e) + r_v - r_u)    (arrival propagates through
                                                           register-free edges)
               t_c2q + d_v <= t_v <= T - t_setup           (launch, clock period)
               r_u + R_u <= H                              (register history available)
               r = 0 at sources, r = L at sinks, r integer.
"""
from __future__ import annotations

import os

import numpy as np

NODE_LIMIT = int(os.environ.get("GS_MILP_NODES", 200))        # deterministic branch-and-bound budget per solve
SAFETY_TIME_S = float(os.environ.get("GS_MILP_SAFETY_S", 1800))  # wall-time safety net only
LAST_STATS = {}


def solve(rg, delays, alpha, e_reg, T, c2q, setup, in_delay=0.0, latency=0, max_lag=4, max_hist=7,
          time_limit=120.0, fixed_lag=None, center=None, radius=None):
    """Lags minimising the calibrated model, or None if infeasible / no solution.

    ``center``/``radius``: search only lags within ``radius`` of ``center`` (a known legal
    retiming, e.g. the minimum-register one) — a neighbourhood that always contains a
    feasible point and that HiGHS solves quickly on designs where the full program
    finds no incumbent within the time limit (local branching)."""
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import coo_matrix
    C, S = rg.C, len(rg.sources)
    n = rg.n
    # variable layout: r[0..C), t[0..C), R[0..n)   (R for every node that drives an edge)
    drivers = sorted({u for u, _, _, _ in rg.edges})
    ridx = {u: 2 * C + k for k, u in enumerate(drivers)}
    nv = 2 * C + len(drivers)
    fl = {C + j: 0 for j in range(S)}
    fl.update({C + S + j: latency for j in range(len(rg.sinks))})
    if fixed_lag:
        fl.update(fixed_lag)
    B = T + max(delays) + c2q + 10.0
    rows, cols, vals, lo, hi = [], [], [], [], []
    k = 0

    def add(terms, lb, ub):
        nonlocal k
        for j, a in terms:
            rows.append(k); cols.append(j); vals.append(a)
        lo.append(lb); hi.append(ub)
        k += 1

    def lag(x):
        """(variable index or None, constant) of r(x)."""
        return (None, fl[x]) if x in fl else (x, 0)

    for u, v, _, w in rg.edges:
        (ju, cu), (jv, cv) = lag(u), lag(v)
        const = w + cv - cu                         # w_r = const + r_v - r_u
        # legality: r_v - r_u >= -const
        terms = [(jv, 1.0)] if jv is not None else []
        terms += [(ju, -1.0)] if ju is not None else []
        if terms:
            add(terms, -const, np.inf)
        elif const < 0:
            return None
        # register sharing: R_u - r_v + r_u >= const
        t2 = [(ridx[u], 1.0)] + [(j, -a) for j, a in terms]
        add(t2, const, np.inf)
        # arrival: t_v - t_u + B (r_v - r_u) >= d_v - B const    (v a cell)
        if v < C:
            t3 = [(C + v, 1.0)] + [(j, B * a) for j, a in terms]
            rhs = delays[v] - B * const
            if u < C:
                t3.append((C + u, -1.0))
            else:
                rhs += in_delay if rg.is_source(u) else 0.0
            add(t3, rhs, np.inf)
    # register history: r_u + R_u <= max_hist
    for u in drivers:
        ju, cu = lag(u)
        terms = [(ridx[u], 1.0)] + ([(ju, 1.0)] if ju is not None else [])
        add(terms, -np.inf, max_hist - cu)
    A = coo_matrix((vals, (rows, cols)), shape=(k, nv)).tocsr()
    cons = LinearConstraint(A, np.array(lo), np.array(hi))
    rlo, rhi = np.full(C, -max_lag, dtype=float), np.full(C, max_lag, dtype=float)
    if center is not None and radius is not None:
        c0 = np.asarray(center[:C], dtype=float)
        rlo, rhi = np.maximum(rlo, c0 - radius), np.minimum(rhi, c0 + radius)
    lb = np.concatenate([rlo, np.array([c2q + d for d in delays]), np.zeros(len(drivers))])
    ub = np.concatenate([rhi, np.full(C, T - setup), np.full(len(drivers), max_hist + max_lag)])
    if np.any(lb[C:2 * C] > ub[C:2 * C]):
        return None
    cost = np.concatenate([np.zeros(C), np.asarray(alpha, dtype=float), np.full(len(drivers), e_reg)])
    integ = np.concatenate([np.ones(C), np.zeros(C), np.zeros(len(drivers))])
    # A branch-and-bound node limit, not wall time, ends the search, so the result does not depend on machine
    # speed or load (reproducible); the time limit is only a safety net and is reported if it is ever reached.
    res = milp(cost, constraints=[cons], integrality=integ, bounds=Bounds(lb, ub),
               options=dict(node_limit=NODE_LIMIT, time_limit=max(time_limit, SAFETY_TIME_S), disp=False,
                            mip_rel_gap=1e-3))
    LAST_STATS.update(nodes=getattr(res, "mip_node_count", None), status=res.status, message=res.message)
    if "Time limit" in str(res.message):
        import warnings
        warnings.warn("MILP stopped by its safety time limit: result depends on machine speed")
    if res.x is None:
        return None
    r = [0] * n
    for v in range(C):
        r[v] = int(round(res.x[v]))
    for x, c in fl.items():
        r[x] = c
    return r


def fit_alpha(samples, C, prior=None, shrink=4.0):
    """Per-cell alpha (fJ/ps) from measured (t_v, g_v) pairs: least squares through the
    origin, shrunk towards the design-wide ratio."""
    st2 = np.zeros(C)
    sgt = np.zeros(C)
    for t, g in samples:
        t = np.asarray(t[:C]); g = np.asarray(g[:C])
        st2 += t * t
        sgt += g * t
    glob = sgt.sum() / st2.sum() if st2.sum() > 0 else 0.0
    m = st2 / max(1, len(samples))
    base = glob if prior is None else prior
    return (sgt + shrink * m.mean() * base) / (st2 + shrink * m.mean() + 1e-12)


def model_arrival(rg, delays, weights, c2q, in_delay=0.0):
    """Arrival time of every cell under the program's timing model (worst delay per cell,
    launch at clock-to-Q after a register, ``in_delay`` after an input)."""
    from collections import defaultdict, deque
    C = rg.C
    inc = defaultdict(list)
    indeg = [0] * rg.n
    outs = defaultdict(list)
    for k, (u, v, _, w) in enumerate(rg.edges):
        if weights[k] == 0:
            inc[v].append(u)
            indeg[v] += 1
            outs[u].append(v)
    t = [0.0] * rg.n
    for j in range(len(rg.sources)):
        t[C + j] = in_delay
    q = deque(v for v in range(rg.n) if indeg[v] == 0)
    seen = 0
    while q:
        x = q.popleft()
        seen += 1
        if x < C:
            t[x] = max([c2q + delays[x]] + [t[u] + delays[x] for u in inc[x]])
        elif rg.is_sink(x):
            t[x] = max([t[u] for u in inc[x]], default=0.0)
        for v in outs[x]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    if seen != rg.n:
        raise ValueError("combinational loop")
    return t


def feas(rg, delays, T, c2q, setup, in_delay=0.0, latency=0, max_iter=None):
    """Leiserson-Saxe FEAS under the program's timing model: lags meeting period T, or None."""
    C, S = rg.C, len(rg.sources)
    r = [0] * rg.n
    for j in range(len(rg.sinks)):
        r[C + S + j] = latency
    limit = T - setup
    for _ in range(max_iter or min(rg.n, 400)):
        w = [w0 + r[v] - r[u] for u, v, _, w0 in rg.edges]
        if min(w) < 0:
            return None
        t = model_arrival(rg, delays, w, c2q, in_delay)
        late = [v for v in range(C) if t[v] > limit + 1e-6]
        # sinks: outputs must be in time too (no register after them)
        bad_sink = any(t[v] > T + 1e-6 for v in range(C + S, rg.n))
        if not late and not bad_sink:
            return r
        if not late:
            return None
        for v in late:
            r[v] += 1
    return None


def wd_pairs(rg, delays, Tp, max_w=6):
    """Leiserson-Saxe period constraints without the full W/D matrices: for every node u,
    a search by register count W (levels) and longest combinational delay D, pruned at
    the first node where D > Tp.  Returns [(u, v, W(u,v))] meaning r(u) - r(v) <= W - 1;
    constraints further along a pruned path are implied by legality."""
    import heapq
    from collections import defaultdict
    n, C = rg.n, rg.C
    d = list(delays) + [0.0] * (n - C)
    out = defaultdict(list)
    for u, v, _, w in rg.edges:
        out[u].append((v, w))
    order = comb_topo_index(rg)
    INF = 10 ** 9
    pairs = []
    for s in range(n):
        if rg.is_sink(s) or not out[s]:
            continue
        if d[s] > Tp:
            return None
        seenW = {}
        levels = {0: {s: d[s]}}
        for W in range(max_w + 1):
            level = {y: dy for y, dy in levels.pop(W, {}).items() if seenW.get(y, INF) >= W}
            if not level:
                continue
            for y in level:
                seenW[y] = W
            D = dict(level)
            heap = [(order[x], x) for x in level]
            heapq.heapify(heap)
            done = set()
            while heap:
                _, x = heapq.heappop(heap)
                if x in done:
                    continue
                done.add(x)
                if D[x] > Tp and x != s:
                    pairs.append((s, x, W))
                    continue                      # pruned: further pairs are implied
                for y, w in out[x]:
                    dy = D[x] + d[y]
                    if w == 0:
                        if seenW.get(y, INF) < W:
                            continue
                        if dy > D.get(y, -1.0):
                            D[y] = dy
                            seenW[y] = W
                            heapq.heappush(heap, (order[y], y))
                    else:
                        W2 = W + w
                        if W2 > max_w or seenW.get(y, INF) < W2:
                            continue
                        lv = levels.setdefault(W2, {})
                        if dy > lv.get(y, -1.0):
                            lv[y] = dy
    return pairs


def comb_topo_index(rg):
    from .retime import comb_order
    cut = [w > 0 for _, _, _, w in rg.edges]
    return {x: i for i, x in enumerate(comb_order(rg, cut))}


def min_area(rg, delays, T, c2q, setup, latency=0, max_lag=4, max_hist=7, time_limit=300.0):
    """Exact Leiserson-Saxe minimum-register retiming (registers shared per net) meeting
    period T under the program's timing model.  All constraints are difference
    constraints (mirror variables m_u = r_u + R_u), so the LP optimum is integral."""
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import coo_matrix
    C, S = rg.C, len(rg.sources)
    Tp = T - setup - c2q
    pairs = wd_pairs(rg, delays, Tp, max_w=max_lag + 2)
    if pairs is None:
        return None
    fl = {C + j: 0 for j in range(S)}
    fl.update({C + S + j: latency for j in range(len(rg.sinks))})
    drivers = sorted({u for u, _, _, _ in rg.edges})
    midx = {u: C + k for k, u in enumerate(drivers)}
    nv = C + len(drivers)
    rows, cols, vals, lo, hi = [], [], [], [], []
    k = [0]

    def lag(x):
        return (None, fl[x]) if x in fl else (x, 0)

    def add(terms, lb, ub):
        for j, a in terms:
            rows.append(k[0]); cols.append(j); vals.append(a)
        lo.append(lb); hi.append(ub)
        k[0] += 1

    def diff(a, b, ub):
        """r(a) - r(b) <= ub with fixed lags folded in."""
        (ja, ca), (jb, cb) = lag(a), lag(b)
        terms = ([(ja, 1.0)] if ja is not None else []) + ([(jb, -1.0)] if jb is not None else [])
        rhs = ub - ca + cb
        if terms:
            add(terms, -np.inf, rhs)
            return True
        return rhs >= 0

    for u, v, _, w in rg.edges:
        if not diff(u, v, w):
            return None
        # sharing: m_u - r_v >= w   (m_u = r_u + R_u)
        jv, cv = lag(v)
        add([(midx[u], 1.0)] + ([(jv, -1.0)] if jv is not None else []), w + cv, np.inf)
    for u, v, W in pairs:
        if not diff(u, v, W - 1):
            return None
    # m_u >= r_u (R_u >= 0) and history m_u <= max_hist
    for u in drivers:
        ju, cu = lag(u)
        add([(midx[u], 1.0)] + ([(ju, -1.0)] if ju is not None else []), cu, np.inf)
    A = coo_matrix((vals, (rows, cols)), shape=(k[0], nv)).tocsr()
    cost = np.zeros(nv)
    for u in drivers:
        cost[midx[u]] += 1.0
        ju, _ = lag(u)
        if ju is not None:
            cost[ju] -= 1.0
    lb = np.concatenate([np.full(C, -max_lag), np.full(len(drivers), -max_lag)])
    ub = np.concatenate([np.full(C, max_lag), np.full(len(drivers), max_hist)])
    # difference constraints only: the LP optimum at a vertex is integral (dual simplex)
    from scipy.optimize import linprog
    lo_a, hi_a = np.array(lo), np.array(hi)
    up = np.isfinite(hi_a)
    dn = np.isfinite(lo_a)
    from scipy.sparse import vstack
    A_ub = vstack([A[up], -A[dn]]).tocsr()
    b_ub = np.concatenate([hi_a[up], -lo_a[dn]])
    res = linprog(cost, A_ub=A_ub, b_ub=b_ub, bounds=list(zip(lb, ub)), method="highs-ds",
                  options=dict(time_limit=time_limit))
    if res.x is None or res.status not in (0,):
        res = milp(cost, constraints=[LinearConstraint(A, lo_a, hi_a)], integrality=np.ones(nv),
                   bounds=Bounds(lb, ub), options=dict(time_limit=time_limit, disp=False))
        if res.x is None:
            return None
    if np.max(np.abs(res.x - np.round(res.x))) > 1e-6:
        res = milp(cost, constraints=[LinearConstraint(A, lo_a, hi_a)], integrality=np.ones(nv),
                   bounds=Bounds(lb, ub), options=dict(time_limit=time_limit, disp=False))
        if res.x is None:
            return None
    r = [0] * rg.n
    for v in range(C):
        r[v] = int(round(res.x[v]))
    for x, c in fl.items():
        r[x] = c
    return r


def _arrival_with_pred(rg, delays, weights, c2q, in_delay):
    """model_arrival plus, per node, the launching node of its critical path and the
    original register count along it."""
    from collections import defaultdict, deque
    C = rg.C
    inc = defaultdict(list)
    indeg = [0] * rg.n
    outs = defaultdict(list)
    for k, (u, v, _, w) in enumerate(rg.edges):
        if weights[k] == 0:
            inc[v].append((u, w))
            indeg[v] += 1
            outs[u].append(v)
    t = [0.0] * rg.n
    start = list(range(rg.n))
    worig = [0] * rg.n
    for j in range(len(rg.sources)):
        t[C + j] = in_delay
    q = deque(v for v in range(rg.n) if indeg[v] == 0)
    while q:
        x = q.popleft()
        if x < C:
            best, bs, bw = c2q + delays[x], x, 0
            for u, w0 in inc[x]:
                if t[u] + delays[x] > best:
                    best, bs, bw = t[u] + delays[x], start[u], worig[u] + w0
            t[x], start[x], worig[x] = best, bs, bw
        elif rg.is_sink(x):
            best, bs, bw = 0.0, x, 0
            for u, w0 in inc[x]:
                if t[u] > best:
                    best, bs, bw = t[u], start[u], worig[u] + w0
            t[x], start[x], worig[x] = best, bs, bw
        for v in outs[x]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return t, start, worig


def min_area_lazy(rg, delays, T, c2q, setup, latency=0, max_lag=4, max_hist=7, max_rounds=200, log=None):
    """Exact minimum-register retiming meeting T, by lazy constraint generation: solve the
    LP of legality + register sharing, add r(u) - r(v) <= w(p) - 1 for every critical
    path p (u -> v) that the solution leaves combinational and too long, repeat.  All
    constraints are difference constraints, so every LP vertex is integral, and the
    final solution is optimal for the full problem (it satisfies the omitted constraints)."""
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix
    C, S = rg.C, len(rg.sources)
    fl = {C + j: 0 for j in range(S)}
    fl.update({C + S + j: latency for j in range(len(rg.sinks))})
    drivers = sorted({u for u, _, _, _ in rg.edges})
    midx = {u: C + k for k, u in enumerate(drivers)}
    nv = C + len(drivers)
    base_rows = []           # (terms, ub) for A x <= ub

    def lag(x):
        return (None, fl[x]) if x in fl else (x, 0)

    def diff(a, b, ub):
        (ja, ca), (jb, cb) = lag(a), lag(b)
        terms = ([(ja, 1.0)] if ja is not None else []) + ([(jb, -1.0)] if jb is not None else [])
        return terms, ub - ca + cb

    for u, v, _, w in rg.edges:
        base_rows.append(diff(u, v, w))
        jv, cv = lag(v)                          # sharing: r_v - m_u <= -w
        base_rows.append((([(jv, 1.0)] if jv is not None else []) + [(midx[u], -1.0)], -w - cv))
    for u in drivers:                            # r_u - m_u <= 0
        ju, cu = lag(u)
        base_rows.append((([(ju, 1.0)] if ju is not None else []) + [(midx[u], -1.0)], -cu))
    cost = np.zeros(nv)
    for u in drivers:
        cost[midx[u]] += 1.0
        ju, _ = lag(u)
        if ju is not None:
            cost[ju] -= 1.0
    bounds = [(-max_lag, max_lag)] * C + [(-max_lag, max_hist)] * len(drivers)
    extra = {}
    limit = T - setup
    r = None
    for it in range(max_rounds):
        rows = base_rows + list(extra.values())
        ri, ci, va, ub = [], [], [], []
        for k, (terms, b) in enumerate(rows):
            if not terms:
                if b < 0:
                    return None
                terms = [(0, 0.0)]
            for j, a in terms:
                ri.append(k); ci.append(j); va.append(a)
            ub.append(b)
        A = coo_matrix((va, (ri, ci)), shape=(len(rows), nv)).tocsr()
        res = linprog(cost, A_ub=A, b_ub=np.array(ub), bounds=bounds, method="highs-ds")
        if res.status != 0:
            return None
        x = np.round(res.x).astype(int)
        r = [0] * rg.n
        for v in range(C):
            r[v] = int(x[v])
        for q_, c_ in fl.items():
            r[q_] = c_
        w = [w0 + r[v] - r[u] for u, v, _, w0 in rg.edges]
        t, st, wo = _arrival_with_pred(rg, delays, w, c2q, 0.0)
        viol = [v for v in range(rg.n) if (v < C and t[v] > limit + 1e-6) or (rg.is_sink(v) and t[v] > T + 1e-6)]
        if not viol:
            if log:
                log(f"  min-register retiming: {it + 1} LP rounds, {len(extra)} path constraints")
            return r
        new = 0
        for v in viol:
            u = st[v]
            if u == v:
                return None
            key = (u, v, wo[v])
            if key not in extra:
                extra[key] = diff(u, v, wo[v] - 1)
                new += 1
        if not new:
            return None
    return None

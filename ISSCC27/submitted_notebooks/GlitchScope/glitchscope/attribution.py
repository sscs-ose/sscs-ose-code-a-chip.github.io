"""Interventional glitch attribution and data attribution.

Glitch Suppression Potential (GSP) of a set S of cells:

    GSP(S) = E_glitch(baseline) - E_glitch(do(cells in S emit no excess transitions))

"do" is realised natively in the pulse simulator (``ideal_cells``): a cell in S
moves once, directly to its final value, at the first input event that logically
implies it -- no excess transitions and no filtered pulses at that cell.  GSP is evaluated exactly
by re-simulating only the steps (vectors / clock cycles) in which a cell of S was
active (made >1 output transition or had a filtered pulse); all other steps are
provably unchanged.

On top of single-cell GSP we report
  * Shapley values over the top-K candidates (permutation sampling): an additive,
    interaction-aware allocation whose sum equals the joint gain of the K cells;
  * a greedy joint fix set (largest marginal gain first), the practical answer to
    "which k gates should I fix together?".

Data attribution regresses per-step glitch energy on the toggle indicators of the
combinational inputs (primary inputs and flop outputs): fJ of glitch energy per
toggle of each input/state bit.
"""
from __future__ import annotations

import os
import random
import multiprocessing as mp
from collections import Counter, defaultdict

import numpy as np

from .analyze import analyze
from .classify import extract_pulses
from .functional import evaluate_stable
from .model import StimulusEpoch
from .sim import PulseSimulator


def _steps_prevs(steps, initial):
    prevs, p = [], dict(initial)
    for st in steps:
        prevs.append(dict(p))
        ups = st if isinstance(st, list) else [(0, st)]
        for _, u in ups:
            p.update(u)
    return prevs


_WORKER = {}


def _work(task):
    """Worker: glitch-energy reduction of intervention S over a chunk of steps."""
    S, ks = task
    ia = _WORKER["ia"]
    sims = _WORKER.setdefault("sims", {})
    sim = sims.get(S)
    if sim is None:
        if len(sims) > 8:
            sims.clear()
        sim = sims[S] = ia._sim_for(S)
    return S, [ia.eg[k] - ia._step_glitch(sim, k) for k in ks]


class InterventionalAttribution:
    """``workers``: processes used to evaluate interventions (1 = serial; 0/None =
    all CPUs).  Work is split per (intervention, chunk of steps); results are
    identical to the serial evaluation.  Parallel mode needs the 'fork' start
    method (Linux, Colab, macOS); elsewhere it falls back to serial."""

    def __init__(self, network, delay_provider, r_filter, energy, steps, initial=None, sim_kwargs=None,
                 workers=1, prevs=None):
        self.net, self.dp, self.m2, self.em = network, delay_provider, r_filter, energy
        self.workers = (os.cpu_count() or 1) if not workers else int(workers)
        if self.workers > 1 and "fork" not in mp.get_all_start_methods():
            self.workers = 1
        self._pool = None
        self.steps = steps
        self.initial = dict(initial or network.initial_inputs)
        self.kw = dict(sim_kwargs or {})
        self.prevs = list(prevs) if prevs is not None else _steps_prevs(steps, self.initial)
        self.active = defaultdict(set)

        def rec(k, res):
            cnt = Counter(e.source_instance for e in res["trace"] if e.source_instance != "$PI")
            for c, n in cnt.items():
                if n > 1:
                    self.active[c].add(k - 1)
            for s in res["suppressed"]:
                self.active[s.instance].add(k - 1)

        sim = PulseSimulator(network, delay_provider, "M2", r_filter=r_filter, **self.kw)
        self.base = analyze(sim, energy, steps, initial=self.initial, on_trace=rec, prevs=self.prevs)
        self.eg = [v["E_glitch"] for v in self.base["per_vector"]]
        self.cells = {c.name: c for c in network.cells}
        self.E = sum(self.eg) or 1.0
        self._cache = {}
        self._bounds = self._cone_bounds()

    def _step_glitch(self, sim, k):
        """Glitch energy (fJ) of step k under ``sim`` -- same accounting as analyze(M2)."""
        from dataclasses import replace
        prev = self.prevs[k]
        st = self.steps[k]
        ups = st if isinstance(st, list) else [(0, st)]
        cur = dict(prev)
        for _, u in ups:
            cur.update(u)
        sim.network = replace(self.net, initial_inputs=dict(prev))
        eps = [StimulusEpoch(100_000 + o, dict(u), 1) for o, u in ups] or [StimulusEpoch(100_000, {}, 1)]
        res = sim.run(eps)
        tr, meta, loads, em = res["trace"], res["meta"], res["loads"], self.em
        evm = {e.event_id: e for e in tr}
        pulses = extract_pulses(tr, {1: evaluate_stable(self.net, prev, sim.order)}, {1: evaluate_stable(self.net, cur, sim.order)})
        e_tot = 0.0
        for p in pulses:
            a, b = evm[p.start_event_id], evm[p.end_event_id]
            c = self.cells[a.source_instance]
            ma, mb = meta[a.event_id], meta[b.event_id]
            e = sum(em.transition_fj(c, ev.new_value == 1, meta[ev.event_id].related_pin,
                                     meta[ev.event_id].slew_in_fs, loads.get(ev.net, 0.0)) for ev in (a, b))
            r = (mb.cause_fs - ma.cause_fs) / ma.delay_fs if ma.delay_fs > 0 else 9.9
            e_tot += e * em.s_e(c, p.polarity, r)
        for s_ in res["suppressed"]:
            c = self.cells[s_.instance]
            pol = "positive" if s_.lead_value == 1 else "negative"
            e_cyc = sum(em.transition_fj(c, rise, s_.lead_related_pin, s_.slew_fs, loads.get(s_.net, 0.0))
                        for rise in (True, False))
            e_tot += em.s_e(c, pol, max(0.0, s_.width_in_fs / max(1, s_.delay_fs))) * e_cyc
        return e_tot

    def _sim_for(self, S):
        return PulseSimulator(self.net, self.dp, "M2", r_filter=self.m2, ideal_cells=S, **self.kw)

    def _steps_of(self, S):
        return sorted(set().union(*(self.active[c] for c in S)))

    def gain(self, S):
        """GSP(S) as a fraction of baseline glitch energy."""
        return self.gains([S])[0]

    def gains(self, sets):
        """GSP of several interventions; uncached ones are evaluated in parallel."""
        sets = [frozenset(S) for S in sets]
        todo = list(dict.fromkeys(S for S in sets if S and S not in self._cache))
        if todo:
            if self.workers <= 1:
                for S in todo:
                    sim = self._sim_for(S)
                    self._cache[S] = sum(self.eg[k] - self._step_glitch(sim, k) for k in self._steps_of(S)) / self.E
            else:
                tasks = []
                total = sum(len(self._steps_of(S)) for S in todo)
                chunk = max(1, -(-total // (4 * self.workers)))
                for S in todo:
                    ks = self._steps_of(S)
                    tasks += [(S, ks[i:i + chunk]) for i in range(0, len(ks), chunk)] or [(S, [])]
                # ordered, per-step results summed in step order: bit-identical to serial
                acc = defaultdict(list)
                for S, g in self._get_pool().imap(_work, tasks):
                    acc[S].extend(g)
                for S in todo:
                    self._cache[S] = sum(acc[S]) / self.E
        return [self._cache[S] if S else 0.0 for S in sets]

    def _get_pool(self):
        if self._pool is None:
            _WORKER.clear(); _WORKER["ia"] = self
            self._pool = mp.get_context("fork").Pool(self.workers)
        return self._pool

    def close(self):
        if self._pool is not None:
            self._pool.close(); self._pool.join(); self._pool = None

    def _cone_bounds(self):
        """do(c) can only change cells in c's transitive fan-out cone (c included), and
        only in steps where c was active, so GSP({c}) <= glitch energy of the cone in
        those steps.  Computed for all cells at once: B = rowsum(A o (C @ L^T))."""
        names = [c.name for c in self.net.cells]
        idx = {n: i for i, n in enumerate(names)}
        fanout = defaultdict(list)
        for c in self.net.cells:
            for n in set(c.inputs.values()):
                fanout[n].append(c.name)
        from .netlist import topo_cells
        cone = {}
        for c in reversed(topo_cells(self.net)):
            m = 1 << idx[c.name]
            for d in fanout.get(c.output, ()):
                m |= cone[d]
            cone[c.name] = m
        act = [c for c in names if c in self.active]
        if not act:
            return {}
        nsteps = len(self.steps)
        L = np.zeros((nsteps, len(names)))
        for k, v in enumerate(self.base["per_vector"]):
            for c, e in v.get("local", {}).items():
                if c in idx:
                    L[k, idx[c]] = e
        C = np.zeros((len(act), len(names)), dtype=np.float32)
        for r, c in enumerate(act):
            m, i = cone[c], 0
            while m:
                if m & 1:
                    C[r, i] = 1.0
                m >>= 1; i += 1
        CL = C @ L.T                                   # cone glitch energy per (cell, step)
        A = np.zeros_like(CL)
        for r, c in enumerate(act):
            A[r, sorted(self.active[c])] = 1.0
        b = (CL * A).sum(axis=1)
        return {c: float(min(b[r], sum(self.eg[k] for k in self.active[c]))) / self.E for r, c in enumerate(act)}

    def bound(self, c):
        """Upper bound on GSP({c}): glitch energy of c's fan-out cone in the steps where c is active."""
        return self._bounds.get(c, 0.0)

    def run(self, top_k=6, perms=12, greedy_k=None, candidates=8, seed=3, groups=None, max_screen=None):
        """Attribution over *units*: single cells (default) or named groups of cells
        (``groups={name: cells}``, e.g. from :func:`make_groups`).

        Cells: exact top-N single gains by branch-and-bound on the fan-out-cone bound;
        ``max_screen`` caps the number of exact evaluations for very large designs
        (``certified`` is then False if the cap, not the bound, ended the search)."""
        certified = True
        if groups:
            units = {g: frozenset(cs) for g, cs in groups.items() if cs}
            names = sorted(units)
            single = dict(zip(names, self.gains([units[n] for n in names])))
        else:
            units = None
            need = max(candidates, top_k)
            single = {}
            queue = sorted(self.active, key=lambda c: -self.bound(c))
            batch = max(1, self.workers)
            while queue:
                if len(single) >= need and self.bound(queue[0]) <= sorted(single.values(), reverse=True)[need - 1]:
                    break
                if max_screen and len(single) >= max_screen:
                    certified = False
                    break
                group, queue = queue[:batch], queue[batch:]
                for c, g in zip(group, self.gains([{c} for c in group])):
                    single[c] = g

        def U(ns):
            return frozenset().union(*(units[n] for n in ns)) if units else frozenset(ns)

        ranked = sorted(single, key=lambda c: -single[c])
        top = ranked[:top_k]
        rng = random.Random(seed)
        orders = []
        for _ in range(perms):
            order = top[:]; rng.shuffle(order); orders.append(order)
        self.gains([U(order[:i + 1]) for order in orders for i in range(len(order))])
        shap = defaultdict(float)
        for order in orders:
            S, prev = [], 0.0
            for c in order:
                S.append(c); g = self.gain(U(S))
                shap[c] += (g - prev) / perms; prev = g
        # greedy joint selection among the best single candidates
        pool = ranked[:max(candidates, top_k)]
        chosen, path = [], []
        for _ in range(greedy_k or top_k):
            rest = [c for c in pool if c not in chosen]
            if not rest:
                break
            gs = self.gains([U(chosen + [c]) for c in rest])
            best = rest[max(range(len(rest)), key=lambda i: gs[i])]
            chosen.append(best); path.append((best, self.gain(U(chosen))))
        self.close()
        gci = self.base["gci"]
        structural = ({g: sum(gci.get(c, 0.0) for c in cs) for g, cs in units.items()} if units else gci)
        return dict(single=single, top=top, shapley=dict(shap), joint_top=self.gain(U(top)),
                    sum_single_top=sum(single[c] for c in top), greedy=path,
                    structural=structural, E_glitch_fJ=self.E, evaluations=len(self._cache),
                    screened=len(single), active_cells=len(self.active), certified=certified,
                    units="groups" if units else "cells",
                    group_sizes={g: len(cs) for g, cs in units.items()} if units else None)


def make_groups(network, by="hier", pattern=None, bands=12):
    """Group cells for group-level attribution.

    by="hier"  : hierarchical prefix of the instance name (text before the last
                 '.', '/' or '_g<digits>' component) -- e.g. Yosys-flattened names;
    by="regex" : ``pattern`` with one capture group; the captured text is the group
                 (cells that do not match are left out);
    by="level" : ``bands`` equal bands of logic depth (glitch-free-stage what-if)."""
    import re
    groups = defaultdict(set)
    if by == "level":
        from .netlist import topo_cells
        prod = {c.output: c for c in network.cells}
        depth = {}
        for c in topo_cells(network):
            depth[c.name] = 1 + max((depth[prod[n].name] for n in c.inputs.values() if n in prod), default=0)
        dmax = max(depth.values()) if depth else 1
        w = max(1, -(-dmax // bands))
        for c, d in depth.items():
            lo = (d - 1) // w * w + 1
            groups[f"depth {lo:03d}-{min(dmax, lo + w - 1):03d}"].add(c)
    elif by == "regex":
        rx = re.compile(pattern)
        for c in network.cells:
            m = rx.search(c.name)
            if m:
                groups[m.group(1) if m.groups() else m.group(0)].add(c.name)
    else:
        for c in network.cells:
            n = c.name.lstrip("\\")
            m = re.match(r"(.+?)(?:[./][^./]+|_g\d+)$", n)
            groups[m.group(1) if m else "(top)"].add(c.name)
    return dict(groups)


def toggle_attribution(network, steps, initial, per_step_glitch_fJ, ridge=1e-3, prevs=None):
    """fJ of glitch energy per toggle of each combinational input (PI or flop Q):
    least-squares fit E_k = b0 + sum_i beta_i * toggled_i(k)."""
    names = list(network.primary_inputs)
    idx = {n: i for i, n in enumerate(names)}
    X = np.zeros((len(steps), len(names)))
    prev = dict(initial)
    for k, st in enumerate(steps):
        if prevs is not None:
            prev = dict(prevs[k])
        ups = st if isinstance(st, list) else [(0, st)]
        for _, u in ups:
            for n, v in u.items():
                if n in idx and prev.get(n) != v:
                    X[k, idx[n]] = 1.0
                prev[n] = v
    y = np.asarray(per_step_glitch_fJ, dtype=float)
    A = np.hstack([np.ones((len(y), 1)), X])
    reg = ridge * np.eye(A.shape[1]); reg[0, 0] = 0.0
    coef = np.linalg.solve(A.T @ A + reg, A.T @ y)
    rate = X.mean(axis=0)
    out = {n: dict(fJ_per_toggle=float(coef[i + 1]), toggle_rate=float(rate[i]),
                   share=float(coef[i + 1] * rate[i] / max(1e-12, y.mean())))
           for i, n in enumerate(names) if rate[i] > 0}
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["share"]))

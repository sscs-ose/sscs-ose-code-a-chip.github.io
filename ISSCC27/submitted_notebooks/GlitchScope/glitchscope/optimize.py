"""Closed-loop glitch-power reduction: measured, verified register placement.

``GlitchFix`` moves the design's registers (retiming, ``latency=0``) or adds
``latency`` register banks (pipelining) and keeps the placement that minimises
the *measured* total energy per cycle, under the clock-period constraint:

1. candidates: register banks placed at arrival-time cuts, projected onto the
   legal retimings (``retime.thresholds_to_lags``), searched by coordinate
   descent over the cut positions;
2. every candidate netlist is written, re-read and simulated with the same
   stimulus as the original: timing- and pulse-filtering-accurate event
   simulation (M2) for the combinational energy, plus Liberty energy of every
   flip-flop (clock, D, Q) and of the input nets (``seqpower``);
3. every candidate is verified: its outputs equal the original's, delayed by
   ``latency`` cycles, on every simulated cycle (initial register states are
   taken from the original's own history, so loops are covered too);
4. reference points, measured the same way: the original placement and classic
   timing-driven retiming (minimum clock period, then fewest registers).

The result is the chosen netlist (Verilog), a table of all measured candidates
and the before / after energy split.
"""
from __future__ import annotations

import json
import math
import tempfile
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

from .analyze import EnergyModel, analyze
from .functional import evaluate_stable
from .liberty import LibertyDelayProvider, parse_liberty_file
from .m2model import M2Model, calibration_for
from .model import ps_to_fs
from .netlist import topo_cells
from .retime import (Timing, build_rgraph, fixed_lags, is_legal, rebuild, retimed_weights,
                     thresholds_to_lags)
from .seq import build_cycles, read_clk_to_q, random_waves, read_vcd
from .seqpower import FlopEnergy, sequential_energy
from .sim import PulseSimulator
from .verilog import read_design


@dataclass
class Candidate:
    name: str
    lags: list
    weights: list
    period_ps: float
    n_flops: int
    thresholds: tuple = ()
    window: float = 0.0
    text: str = ""
    M: int = 1
    verified: bool = False
    mismatches: int = 0
    energy: dict = field(default_factory=dict)
    note: str = ""
    local: dict = field(default_factory=dict, repr=False)     # measured glitch energy per cell (fJ/cycle)

    def row(self):
        e = self.energy
        return dict(name=self.name, thresholds_ps=[None if math.isinf(t) else round(t, 1) for t in self.thresholds],
                    window_ps=round(self.window, 1),
                    period_ps=round(self.period_ps, 1), flops=self.n_flops, verified=self.verified,
                    **{k: round(v, 2) for k, v in e.items() if isinstance(v, float)}, note=self.note)


class GlitchFix:
    def __init__(self, netlist, lib_path, lib=None, vcd=None, random_vectors=None, period_ps=None,
                 latency=0, clock=None, input_delay_ps=None, sample=24, seed=1, model="M2",
                 input_slew_ps=40.0, setup_ps=100.0, grid=20, workdir=None, log=print, max_flops=None,
                 keep_io=False):
        self.lib_path, self.log = lib_path, log
        self.lib = lib or parse_liberty_file(lib_path)
        self.dp = LibertyDelayProvider(self.lib)
        self.design = read_design(netlist, self.lib)
        self.latency, self.model, self.input_slew_ps = int(latency), model, input_slew_ps
        self.cal = calibration_for(self.lib.name)
        self.m2 = M2Model(self.cal)
        self.max_flops = max_flops
        self.workdir = Path(workdir or tempfile.mkdtemp(prefix="glitchfix_"))
        self.workdir.mkdir(parents=True, exist_ok=True)
        d = self.design
        # stimulus (waves) shared by every candidate
        if vcd is not None:
            self.waves, _ = read_vcd(vcd)
            self.clock = clock or (d.clocks[0] if d.clocks else None)
            ce = [t for (t, v) in self.waves[self.clock] if v == 1]
            self.period_ps = period_ps or ((ce[2] - ce[1]) / 1000.0 if len(ce) > 2 else 2000.0)
            self.input_delay_ps = input_delay_ps
        else:
            if not random_vectors:
                raise ValueError("provide a VCD or random_vectors")
            self.period_ps = period_ps or 2000.0
            self.waves, self.clock = random_waves(d, int(random_vectors), self.period_ps, seed=seed,
                                                  clock=clock or (d.clocks[0] if d.clocks else "clk"))
            self.input_delay_ps = 100.0 if input_delay_ps is None else input_delay_ps
        self.rg = build_rgraph(d, keep_io=keep_io)
        if self.latency and self.rg.fixed:
            raise ValueError("pipelining needs all flip-flops movable (no async set/reset)")
        if not self.rg.movable and not self.latency:
            raise ValueError("no movable registers: use latency >= 1 to pipeline")
        self.ffcell = self.rg.flop_libcell or None
        self.c2q_tabs = None
        self.sample, self.seed = sample, seed
        self._orig_eval()
        self.timing = Timing(self.rg, self.lib, self.dp, self.loads0, clk_to_q_ps=self.c2q_ps,
                             setup_ps=setup_ps, input_slew_ps=input_slew_ps,
                             input_delay_ps=self.input_delay_ps or 0.0)
        self.arrival, _, _ = self.timing.analyze(None)
        self.dcrit = max(self.arrival[: self.rg.C], default=0.0)
        self.grid = grid
        self.cache = {}
        self.results = []

    # ------------------------------------------------------------------ helpers
    def _loads(self, design):
        sim = PulseSimulator(design.network, self.dp, "M1", default_input_slew_fs=ps_to_fs(self.input_slew_ps),
                             primary_output_load_ff_by_net=self._flop_d_cap(design), engine="python")
        return sim.loads

    def _flop_d_cap(self, design):
        cap = {}
        for f in design.flops:
            cap[f.d] = cap.get(f.d, 0.0) + self.lib.cells[f.libcell].pin_capacitance.get(f.d_pin, 0.0)
        return cap

    def _cycles(self, design, loads, start=0, init_state=None):
        libcells = {f.libcell for f in design.flops}
        c2q = read_clk_to_q(self.lib_path, libcells) if libcells else {}
        return build_cycles(design, self.waves, self.lib, c2q, loads, clock=self.clock,
                            input_delay_ps=self.input_delay_ps, start=start, init_state=init_state)

    @staticmethod
    def _states(design, init, cycles):
        order = topo_cells(design.network)
        st, out = dict(init), []
        for cyc in cycles:
            for _, u in cyc:
                st.update(u)
            s = evaluate_stable(design.network, st, order)
            out.append(s)
            st = {k: s[k] for k in st}
        return out

    def _orig_eval(self):
        d = self.design
        self.loads0 = self._loads(d)
        init, cycles, edges = self._cycles(d, self.loads0)
        self.init0, self.cycles0, self.edges0 = init, cycles, edges
        self.states0 = self._states(d, init, cycles)
        self.N = len(cycles)
        # clock-to-Q of the register cell (nominal, for timing)
        ff = self.rg.flop_libcell or None
        if ff is None:
            from .retime import _pick_dff
            ff = _pick_dff(self.lib)
        self.ffcell = ff
        c2q = read_clk_to_q(self.lib_path, {ff})[ff]
        from .liberty import bilinear
        tu, cu = self.lib.time_unit_ps, self.lib.capacitance_unit_ff
        self.c2q_ps = max(bilinear(t, self.input_slew_ps / tu, 5.0 / cu) for t in next(iter(c2q.values()))) * tu
        self.fe = FlopEnergy(self.lib_path, self.lib, {ff} | {f.libcell for f in d.flops})
        # evaluation window: cycles M_EVAL .. N-1 (M_EVAL leaves room for register history)
        self.M_EVAL = min(8, max(2, self.N // 4))
        import random
        rnd = random.Random(self.seed)
        pool = list(range(self.M_EVAL + 1 + self.latency, self.N))
        self.sample_idx = sorted(rnd.sample(pool, min(self.sample, len(pool))))

    def energy(self, design, states, cycles, offset, loads):
        """Per-cycle energy (fJ) of ``design`` on the sampled cycles; ``cycles[k]`` /
        ``states[k]`` are global cycle ``k + offset``."""
        sim = PulseSimulator(design.network, self.dp, self.model, r_filter=self.m2,
                             default_input_slew_fs=ps_to_fs(self.input_slew_ps),
                             primary_output_load_ff_by_net=self._flop_d_cap(design),
                             delay_scale=getattr(self, "delay_scale", None),      # local variation study
                             max_reruns=5000)
        em = EnergyModel(self.lib_path, design.network, m2_json=self.cal, spice_scale=True)
        idx = [g for g in self.sample_idx if g - offset - 1 >= 0]
        steps = [cycles[g - offset] for g in idx]
        pis = design.network.primary_inputs
        prevs = [{p: states[g - offset - 1].get(p, 0) for p in pis} for g in idx]
        res = analyze(sim, em, steps, initial=prevs[0], prevs=prevs)
        n = len(idx)
        st = {g: states[g - offset] for g in idx}
        st.update({g - 1: states[g - offset - 1] for g in idx})
        seq = sequential_energy(design, st, idx, sim.loads, self.fe)
        t = res["totals"]
        e = dict(functional=t["E_functional_fJ"] / n, glitch=t["E_glitch_fJ"] / n,
                 flop_clock=seq["clock"] / n, flop_data=(seq["data"] + seq["q"]) / n, inputs=seq["inputs"] / n)
        e["total"] = sum(e.values())
        e["cycles"] = float(n)
        self._last_local = {c: v / n for c, v in res["local"].items()}
        return e

    # ------------------------------------------------------------------ candidates
    def candidate(self, r, name, thresholds=()):
        w = retimed_weights(self.rg, r)
        key = tuple(w)
        if key in self.cache:
            c = self.cache[key]
            return c
        _, _, period = self.timing.analyze(w)
        depth = {}
        for (u, v, _, _), x in zip(self.rg.edges, w):
            depth[u] = max(depth.get(u, 0), x)
        nflops = sum(depth.values()) + len(self.rg.fixed)
        c = Candidate(name, list(r), w, period, nflops, tuple(thresholds))
        self.cache[key] = c
        return c

    def measure(self, c):
        """Write, re-read, verify and measure a candidate (in place)."""
        if c.energy:
            return c
        rg, r = self.rg, c.lags
        text, chains = rebuild(rg, r, self.lib, header=f"// {c.name}: retimed by GlitchScope (latency +{self.latency})")
        path = self.workdir / f"cand_{abs(hash(tuple(c.weights))) % 10**10}.v"
        path.write_text(text)
        c.text = text
        d2 = read_design(path, self.lib)
        loads2 = self._loads(d2)
        # register history: register j on node u holds u at cycle (M-1) - j - r(u)
        need = 1 + max((j + 1 + r[u] for u, ch in chains.items() for j in range(len(ch))), default=0)
        M = max(1, need)
        if M > self.M_EVAL:
            c.note = f"needs {M} warm-up cycles"
            c.energy = {}
            c.verified = False
            return c
        c.M = M
        prev = self.states0[M - 1]
        init = {}
        for p in d2.network.primary_inputs:
            if p in prev:
                init[p] = prev[p]
        for u, ch in chains.items():
            src = rg.out_net[u]
            for j, q in enumerate(ch, 1):
                init[q] = self.states0[M - 1 - j - r[u]][src]
        _, cycles, _ = self._cycles(d2, loads2, start=M, init_state=init)
        states = self._states(d2, init, cycles)
        # verification: outputs equal the original's delayed by `latency`, every cycle
        bad = 0
        L = self.latency
        for k, s in enumerate(states):
            g = M + k
            if g - L < 0:
                continue
            for port in self.design.output_ports:
                if s[d2.port_net[port]] != self.states0[g - L][self.design.port_net[port]]:
                    bad += 1
        c.mismatches, c.verified = bad, bad == 0
        if not c.verified:
            c.note = f"{bad} output mismatches"
            return c
        c.energy = self.energy(d2, states, cycles, M, loads2)
        c.local = dict(self._last_local)
        c.n_flops = len(d2.flops)
        return c

    def original(self):
        r = [0] * self.rg.n
        lf = fixed_lags(self.rg, 0)
        for v, x in lf.items():
            r[v] = x
        c = Candidate("original", r, retimed_weights(self.rg, r), self.timing.analyze(retimed_weights(self.rg, r))[2],
                      len(self.design.flops))
        c.verified = True
        c.energy = self.energy(self.design, self.states0, self.cycles0, 0, self.loads0)
        c.local = dict(self._last_local)
        return c

    def from_thresholds(self, th, name, window=0.0):
        cands = []
        for direction in ("down", "up"):
            r = thresholds_to_lags(self.rg, self.arrival, th, None, self.latency, direction, window=window)
            if r is not None:
                c = self.candidate(r, name, th)
                if not c.energy and c.window == 0.0:
                    c.window = window
                cands.append(c)
        return cands

    def windows(self):
        return [0.0] + [f * self.dcrit for f in (0.03, 0.06, 0.1, 0.15)]

    def _grid(self):
        D = self.dcrit
        g = [0.0] + [D * (k / self.grid) for k in range(1, self.grid)] + [math.inf]
        return g

    def n_banks(self):
        from .retime import banks
        return banks(self.rg, self.latency)

    def classic(self, T, objective="period"):
        """Conventional retiming over the same candidate space, by static timing only:
        ``period``: minimum clock period, then fewest registers;
        ``area``: fewest registers that meet the period ``T``, then shortest period."""
        m = self.n_banks()
        grid = self._grid()
        best = None

        def key(c):
            if objective == "period":
                return (round(c.period_ps, 1), c.n_flops)
            return (c.period_ps > T, c.n_flops, round(c.period_ps, 1))
        th = [grid[min(len(grid) - 2, round((i + 1) * len(grid) / (m + 1)))] for i in range(m)]
        starts = [th, [0.0] * (m - self.latency) + [math.inf] * self.latency] if objective == "area" else [th]
        label = "min-period" if objective == "period" else "min-register"
        for th in starts:
            for _ in range(3):
                for i in range(m):
                    for g in grid:
                        t2 = sorted(th[:i] + [g] + th[i + 1:])
                        for c in self.from_thresholds(t2, label):
                            if best is None or key(c) < key(best):
                                best, th = c, list(t2)
        # register-count shaping around the chosen cut positions (same objective)
        if best is not None and best.thresholds:
            for wdw in self.windows()[1:]:
                for c in self.from_thresholds(list(best.thresholds), label, window=wdw):
                    if key(c) < key(best):
                        best = c
        return best

    def search(self, T=None, rounds=2, log_every=True, method="both", milp_iters=3, milp_time=60.0):
        """``method``: "cuts" (coordinate descent over bank positions, shaped by minimum
        cuts), "milp" (measurement-calibrated MILP over all lags) or "both" (MILP
        calibrated also on the cut search's measurements); the lowest measured total
        energy wins."""
        T = T or self.period_ps
        t0 = time.time()
        base = self.original()
        self.log(f"  original      : {base.energy['total']:8.1f} fJ/cycle  period {base.period_ps:7.0f} ps  "
                 f"{base.n_flops} flops")
        refs = []
        for obj, label in (("area", "min-register  "), ("period", "min-period    ")):
            c = self.classic(T, obj)
            c = replace(c, name=label.strip()) if c is not None else None
            if c is not None:
                self.cache[tuple(c.weights)] = c
                self.measure(c)
                if c.energy:
                    self.log(f"  {label}: {c.energy['total']:8.1f} fJ/cycle  period {c.period_ps:7.0f} ps  "
                             f"{c.n_flops} flops")
            refs.append(c)
        self.min_register, classic = refs
        m = self.n_banks()
        grid = self._grid()
        ok = [c for c in refs if c is not None and c.energy and c.period_ps <= T]
        best = min(ok, key=lambda c: c.energy["total"]) if ok else None
        th = list(best.thresholds) if best is not None and best.thresholds else [grid[len(grid) // 2]] * m
        evaluated = 0
        wdw = 0.0
        plan = [0.0] * rounds + self.windows()[1:]
        if method == "milp":
            plan = []
        for rd, wdw in enumerate(plan):
            improved = False
            if wdw > 0:
                self.log(f"  cut shaping window +-{wdw:.0f} ps")
            for i in range(m):
                for g in grid:
                    t2 = sorted(th[:i] + [g] + th[i + 1:])
                    for c in self.from_thresholds(t2, "glitch-aware", window=wdw):
                        if c.period_ps > T or (self.max_flops and c.n_flops > self.max_flops):
                            continue
                        if not c.energy and c.verified is False and c.note:
                            continue
                        self.measure(c)
                        evaluated += 1
                        if c.energy and (best is None or c.energy["total"] < best.energy["total"] - 1e-9):
                            best, th, improved = c, list(t2), True
                            self.log(f"  better        : {c.energy['total']:8.1f} fJ/cycle  period "
                                     f"{c.period_ps:7.0f} ps  {c.n_flops} flops  cuts "
                                     f"{[('in' if t == 0 else 'out' if math.isinf(t) else round(t)) for t in t2]}")
            if not improved and wdw == 0.0 and rd + 1 < rounds:
                # coordinate descent converged at window 0: go on to the shaping windows
                plan[rd + 1:rounds] = []
        self.best_cuts = best
        if method in ("milp", "both"):
            start = [c for c in self.cache.values() if c.local] if method == "both" else []
            mb = self.milp_search(T, base=base, iters=milp_iters, time_limit=milp_time, start=start)
            self.best_milp = mb
            if mb is not None and (best is None or mb.energy["total"] < best.energy["total"]):
                best = mb
        if best is not None and all(best is not r for r in refs):
            best = replace(best, name="glitch-aware")
        self.log(f"  {len([c for c in self.cache.values() if c.energy])} placements measured in {time.time() - t0:.0f} s")
        self.results = [base, self.min_register, classic, best]
        return base, classic, best

    # ------------------------------------------------------------------ calibrated MILP
    def cell_delays(self, weights=None):
        """Worst pin-to-output delay of every cell (ps) at the slews of a static timing run."""
        _, SL, _ = self.timing.analyze(weights or [e[3] for e in self.rg.edges])
        inc = {}
        for u, v, pin, w in self.rg.edges:
            if v < self.rg.C:
                inc.setdefault(v, []).append((u, pin))
        d = []
        for v in range(self.rg.C):
            best = 0.0
            for u, pin in inc.get(v, []):
                (ar, af), _ = self.timing._arc_out(v, pin, (0.0, 0.0), SL[u])
                best = max(best, ar, af)
            d.append(best)
        return d

    def register_energy(self, base):
        """Energy of one flip-flop per cycle (fJ): measured on the design when it has flops."""
        if base.n_flops and base.energy.get("flop_clock"):
            return (base.energy["flop_clock"] + base.energy["flop_data"]) / base.n_flops
        from .verilog import Flop
        lc = self.lib.cells[self.ffcell]
        qp = next(p.name for p in lc.pins.values() if p.direction == "output")
        f = Flop("x", self.ffcell, "d", "q", "clk", d_pin=lc.seq["next_state"], clk_pin=lc.seq["clocked_on"], q_pin=qp)
        e_clk, e_d, e_q = self.fe.per_flop(f, 5.0)
        return e_clk + 0.25 * (e_d + e_q)

    def _milp(self, T, alpha, e_reg, time_limit=60.0):
        from .milp_retime import solve
        return solve(self.rg, self._delays, alpha, e_reg, T, self.c2q_ps, self.timing.setup,
                     in_delay=self.timing.in_delay, latency=self.latency, max_hist=self.M_EVAL - 1,
                     time_limit=time_limit)

    def min_period(self, lo=None, hi=None, tol=25.0):
        """Shortest clock period a legal retiming reaches under the MILP's timing model
        (bisection with Leiserson-Saxe FEAS).  Also keeps that retiming (``self.feas_lags``)."""
        from .milp_retime import feas
        self._delays = getattr(self, "_delays", None) or self.cell_delays()
        d, c2q, su, ind = self._delays, self.c2q_ps, self.timing.setup, self.timing.in_delay
        hi = hi or 4.0 * (self.timing.analyze([e[3] for e in self.rg.edges])[2] + su) + c2q
        lo = lo or max(d) + c2q + su
        r = feas(self.rg, d, hi, c2q, su, ind, self.latency)
        if r is None:
            return None
        best = r
        while hi - lo > tol:
            mid = 0.5 * (lo + hi)
            r = feas(self.rg, d, mid, c2q, su, ind, self.latency)
            if r is not None:
                hi, best = mid, r
            else:
                lo = mid
        self.feas_lags = best
        return hi

    def classic_min_area(self, T, time_limit=300.0):
        """Leiserson-Saxe minimum-register retiming under the clock period T (the
        conventional objective), solved exactly (``milp_retime.min_area``)."""
        from .milp_retime import min_area_lazy
        self._delays = getattr(self, "_delays", None) or self.cell_delays()
        r = min_area_lazy(self.rg, self._delays, T, self.c2q_ps, self.timing.setup, latency=self.latency,
                          max_hist=self.M_EVAL - 1, log=self.log)
        if r is None:
            return None
        c = self.candidate(r, "min-register retiming")
        if c.period_ps > T:
            c.note = "period"
            return None
        self.measure(c)
        return c

    def milp_search(self, T, base=None, iters=4, reg_weights=(1.0, 0.6, 1.6), time_limit=120.0, start=()):
        """Measurement-calibrated MILP retiming (``milp_retime``): solve, measure, re-fit,
        repeat.  ``start``: already measured candidates used as calibration data."""
        from .milp_retime import solve, fit_alpha
        rg = self.rg
        C = rg.C
        base = base or self.original()
        names = [c.name for c in rg.cells]
        delays = self._delays = getattr(self, "_delays", None) or self.cell_delays()
        e_reg = self.register_energy(base)
        samples = []

        def add_sample(c):
            if c.local:
                arr = self.timing.analyze(c.weights)[0]
                samples.append((arr[:C], [c.local.get(nm, 0.0) for nm in names]))
        for c in (base,) + tuple(start):
            add_sample(c)
        best = None
        t0 = time.time()
        local_only = False
        radii = (1, 2)
        for it in range(iters):
            ok = [c for c in (best,) + tuple(start) if c is not None and c.energy and c.lags]
            centre = min(ok, key=lambda c: c.energy["total"]) if ok else None
            alpha = fit_alpha(samples, C)
            new = 0
            for rw in (reg_weights if it == 0 else reg_weights[:1] + reg_weights[1:2]):
                kw = dict(in_delay=self.timing.in_delay, latency=self.latency, max_hist=self.M_EVAL - 1,
                          time_limit=time_limit)
                r = None if local_only else solve(rg, delays, alpha, e_reg * rw, T, self.c2q_ps,
                                                   self.timing.setup, **kw)
                if r is None and centre is not None:
                    # full program found no incumbent: search a neighbourhood of the best
                    # measured legal placement instead (local branching), widening it
                    for rad in radii:
                        r = solve(rg, delays, alpha, e_reg * rw, T, self.c2q_ps, self.timing.setup,
                                  center=centre.lags, radius=rad, **kw)
                        if r is not None:
                            self.log(f"  MILP (iteration {it + 1}, register weight {rw}): neighbourhood "
                                     f"+-{rad} of '{centre.name}'")
                            local_only = True          # the full program will not do better next time
                            break
                if r is None:
                    self.log(f"  MILP (iteration {it + 1}, register weight {rw}): no solution")
                    continue
                c = self.candidate(r, "calibrated MILP")
                if c.energy:                       # already measured (e.g. equals a reference)
                    if best is None or c.energy["total"] < best.energy["total"]:
                        best = c
                    continue
                if c.note:
                    continue
                if c.period_ps > T:
                    c.note = "period"
                    continue
                self.measure(c)
                new += 1
                if c.energy:
                    add_sample(c)
                    from .milp_retime import LAST_STATS
                    self.log(f"  MILP it {it + 1} (reg x{rw}): {c.energy['total']:8.1f} fJ/cycle  period "
                             f"{c.period_ps:7.0f} ps  {c.n_flops} flops  ({LAST_STATS.get('nodes')} B&B nodes)")
                    if best is None or c.energy["total"] < best.energy["total"]:
                        best = c
            if not new:
                break
        self.log(f"  calibrated MILP: {len(samples)} calibration points, {time.time() - t0:.0f} s")
        return best

    def remeasure(self, cands, sample):
        """Measure the reported designs again on a larger cycle sample."""
        import random
        rnd = random.Random(self.seed + 1)
        pool = list(range(self.M_EVAL + 1 + self.latency, self.N))
        self.sample_idx = sorted(rnd.sample(pool, min(sample, len(pool))))
        out = []
        for c in cands:
            if c is None:
                out.append(None)
                continue
            if c.name == "original":
                c2 = self.original()
            else:
                c2 = replace(c, energy={}, verified=False, text="")
                self.measure(c2)
            out.append(c2)
        return out

    def select(self, cands, tie=0.05):
        """Final choice among measured, verified placements: the fewest flip-flops among those whose total
        energy is within ``tie`` (a fraction) of the lowest.  Energy differences smaller than the model's own
        uncertainty on glitch-dominated logic are not trusted to be real (transistor-level SPICE finds GlitchScope's
        predicted savings on deep arrays 1.3-2x too large, and two 8x8 placements 1.5 % apart in prediction tie in
        SPICE), while fewer registers always save area and clock load.  The candidates include the reference
        retimings (minimum-register, timing-driven), so the tool returns one of them when glitch-aware placement
        does not pay by more than the tie.
        ``tie=0`` keeps the plain lowest-energy placement."""
        ok = [c for c in cands if c is not None and c.energy and c.verified is not False]
        if not ok:
            return None
        e0 = min(c.energy["total"] for c in ok)
        near = [c for c in ok if c.energy["total"] <= e0 * (1 + tie) + 1e-9]
        pick = min(near, key=lambda c: (c.n_flops, c.energy["total"]))
        return replace(pick, name="glitch-aware")

    def all_rows(self):
        return [c.row() for c in self.cache.values() if c.energy]


def write_result(fix, base, classic, best, out_dir, freq_mhz=None, min_register=None):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if best is not None and best.text:
        (out / "optimized.v").write_text(best.text)
    if classic is not None and classic.text:
        (out / "timing_driven.v").write_text(classic.text)
    f = freq_mhz or (1e6 / fix.period_ps)          # MHz

    summary = dict(period_ps=fix.period_ps, latency=fix.latency, sampled_cycles=len(fix.sample_idx),
                   original=base.row(), min_register=min_register.row() if min_register else None,
                   timing_driven=classic.row() if classic else None,
                   glitch_aware=best.row() if best else None,
                   candidates=sorted(fix.all_rows(), key=lambda r: r.get("total", 1e99)))
    for k in ("original", "min_register", "timing_driven", "glitch_aware"):
        if summary[k]:
            summary[k]["power_uW"] = round(summary[k].get("total", 0) * f * 1e-3, 2)   # fJ x MHz = nW
    (out / "optimize.json").write_text(json.dumps(summary, indent=1))
    return summary

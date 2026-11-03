"""What-if fix evaluation: HOW to fix a glitch source, not only where.

For a candidate cell, GlitchScope builds function-preserving netlist edits and
measures each one by exact re-simulation with the same M2 pulse model and energy
accounting as the baseline:

  * resize     -- swap the cell for the same logic function at another drive
                  strength (changes its delay/slew, its input-pin load on the
                  drivers, and its own internal energy);
  * pin swap   -- exchange the nets on two logically symmetric input pins (the
                  function is unchanged, but each pin has its own timing arc and
                  capacitance, so arrival alignment and therefore glitching changes).

Only steps (vectors / clock cycles) in which the edited cell or one of its
drivers made a transition or filtered a pulse can change; all other steps are
provably identical and are not re-simulated.  Reported per edit: change of
glitch, functional and total dynamic energy, and of the worst observed settling
time (latest transition after the step start; a timing proxy, not STA).

This is an evaluation aid -- the user decides which edit to apply.
"""
from __future__ import annotations

import itertools
import multiprocessing as mp
import os
import re
from collections import defaultdict
from dataclasses import replace
from types import SimpleNamespace

from .analyze import EnergyModel, analyze
from .logic import eval_primitive
from .sim import PulseSimulator

T0_FS = 100_000
_W = {}


def _drive(libcell):
    m = re.search(r"_(\d+)$", libcell)
    return int(m.group(1)) if m else 1


def _base(libcell):
    return re.sub(r"_\d+$", "", libcell)


def _steps_prevs(steps, initial):
    prevs, p = [], dict(initial)
    for st in steps:
        prevs.append(dict(p))
        for _, u in (st if isinstance(st, list) else [(0, st)]):
            p.update(u)
    return prevs


def _settle(res):
    ts = [e.time_fs for e in res["trace"] if e.source_instance != "$PI"]
    return (max(ts) - T0_FS) if ts else 0


def _eval_task(task):
    idx, ks = task
    w = _W["w"]
    cache = _W.setdefault("sims", {})
    if idx not in cache:
        cache.clear()
        cache[idx] = w._sim_for(w._edits[idx]["cells"])
    sim = cache[idx]
    fun, gl = [], []
    settle = 0
    for k in ks:
        box = {}
        r = analyze(sim, w.em, [w.steps[k]], initial=w.prevs[k], on_trace=lambda _k, res: box.setdefault("s", _settle(res)))
        fun.append(r["totals"]["E_functional_fJ"]); gl.append(r["totals"]["E_glitch_fJ"])
        settle = max(settle, box.get("s", 0))
    return idx, fun, gl, settle


class WhatIf:
    def __init__(self, network, lib, lib_path, delay_provider, r_filter, steps, initial=None,
                 sim_kwargs=None, spice_scale=True, workers=1, max_drive=4, m2_json="default", prevs=None):
        self.net, self.lib, self.dp, self.m2 = network, lib, delay_provider, r_filter
        self.steps = steps
        self.initial = dict(initial or network.initial_inputs)
        self.prevs = list(prevs) if prevs is not None else _steps_prevs(steps, self.initial)
        self.kw = dict(sim_kwargs or {})
        self.max_drive = max_drive
        self.workers = (os.cpu_count() or 1) if not workers else int(workers)
        if self.workers > 1 and "fork" not in mp.get_all_start_methods():
            self.workers = 1
        bases = {_base(c.library_cell) for c in network.cells}
        libcells = sorted(n for n in lib.cells if _base(n) in bases)
        from .m2model import DEFAULT as _M2D
        self.em = EnergyModel(lib_path, SimpleNamespace(cells=[SimpleNamespace(library_cell=n) for n in libcells]),
                              m2_json=_M2D if m2_json == "default" else m2_json, spice_scale=spice_scale)
        self.cells = {c.name: c for c in network.cells}
        self.driver = {c.output: c.name for c in network.cells}
        self.touched = defaultdict(set)
        self.settle = []

        def rec(k, res):
            for e in res["trace"]:
                if e.source_instance != "$PI":
                    self.touched[e.source_instance].add(k - 1)
            for s in res["suppressed"]:
                self.touched[s.instance].add(k - 1)
            self.settle.append(_settle(res))

        sim = self._sim_for({})
        self.base = analyze(sim, self.em, steps, initial=self.initial, on_trace=rec, prevs=self.prevs)
        self.base_fun = [v["E_fun"] for v in self.base["per_vector"]]
        self.base_gl = [v["E_glitch"] for v in self.base["per_vector"]]
        self.E_total = self.base["totals"]["E_total_fJ"] or 1.0
        self.E_glitch = self.base["totals"]["E_glitch_fJ"] or 1.0
        self._edits = []

    # ------------------------------------------------------------------
    def _sim_for(self, new_cells):
        net = self.net if not new_cells else replace(
            self.net, cells=[new_cells.get(c.name, c) for c in self.net.cells])
        return PulseSimulator(net, self.dp, "M2", r_filter=self.m2, **self.kw)

    def _affected(self, names):
        ks = set()
        for n in names:
            ks |= self.touched.get(n, set())
            for net in self.cells[n].inputs.values():
                d = self.driver.get(net)
                if d:
                    ks |= self.touched.get(d, set())
        return sorted(ks)

    def _resizes(self, name, owner, prefix=""):
        c = self.cells[name]
        lc = self.lib.cells.get(c.library_cell)
        out = []
        if lc is not None:
            pins = set(c.inputs)
            func = {p.name: p.function for p in lc.pins.values() if p.direction == "output"}
            vs = []
            for n in self.lib.cells:
                if _base(n) != _base(c.library_cell) or n == c.library_cell or _drive(n) > self.max_drive:
                    continue
                v = self.lib.cells[n]
                vin = {p.name for p in v.pins.values() if p.direction == "input"}
                vf = {p.name: p.function for p in v.pins.values() if p.direction == "output"}
                if vin == pins and vf == func:
                    vs.append(n)
            vs.sort(key=lambda n: (abs(_drive(n) - _drive(c.library_cell)), _drive(n)))
            for n in vs[:3]:
                out.append(dict(cell=owner, kind="driver resize" if prefix else "resize",
                                label=f"{prefix}resize {c.library_cell.split('__')[-1]} -> {n.split('__')[-1]}",
                                cells={name: replace(c, library_cell=n)}))
        return out

    def edits_for(self, name, drivers=True):
        """Function-preserving edits of one cell: resizes, symmetric pin swaps and
        (``drivers=True``) resizes of the cells driving its inputs."""
        c = self.cells[name]
        out = self._resizes(name, name)
        ins = sorted(c.inputs)
        for p, q in itertools.combinations(ins, 2):
            sym = all(eval_primitive(c.kind, dict(zip(ins, bits))) ==
                      eval_primitive(c.kind, {**dict(zip(ins, bits)), p: bits[ins.index(q)], q: bits[ins.index(p)]})
                      for bits in itertools.product((0, 1), repeat=len(ins)))
            if sym and c.inputs[p] != c.inputs[q]:
                new_in = dict(c.inputs); new_in[p], new_in[q] = c.inputs[q], c.inputs[p]
                out.append(dict(cell=name, kind="pin swap", label=f"swap pins {p}<->{q}",
                                cells={name: replace(c, inputs=new_in)}))
        if drivers:
            seen = set()
            for pin in ins:
                d = self.driver.get(c.inputs[pin])
                if d and d not in seen:
                    seen.add(d)
                    out += self._resizes(d, name, prefix=f"driver {d} (pin {pin}): ")
        return out

    def evaluate(self, edits):
        """Exact re-simulation of each edit on its affected steps (parallel over edits x steps)."""
        base_idx = len(self._edits)
        self._edits += edits
        tasks = []
        for i, e in enumerate(edits, base_idx):
            e["steps"] = self._affected(e["cells"])
            ks = e["steps"]
            ch = max(1, -(-len(ks) // max(1, 2 * self.workers))) if self.workers > 1 else max(1, len(ks))
            tasks += [(i, ks[j:j + ch]) for j in range(0, len(ks), ch)]
        acc = defaultdict(lambda: [[], [], 0])
        if self.workers > 1 and len(tasks) > 1:
            _W.clear(); _W["w"] = self
            with mp.get_context("fork").Pool(self.workers) as pool:
                results = list(pool.imap(_eval_task, tasks))
        else:
            _W.clear(); _W["w"] = self
            results = [_eval_task(t) for t in tasks]
        for i, f, g, s in results:          # in task (= step) order: identical to a serial run
            a = acc[i]; a[0] += f; a[1] += g; a[2] = max(a[2], s)
        worst = max(self.settle) if self.settle else 0
        rows = []
        for i, e in enumerate(edits, base_idx):
            ks = e["steps"]
            f, g, s = sum(acc[i][0]), sum(acc[i][1]), acc[i][2]
            bf = sum(self.base_fun[k] for k in ks); bg = sum(self.base_gl[k] for k in ks)
            kset = set(ks)
            others = max((self.settle[k] for k in range(len(self.steps)) if k not in kset), default=0)
            rows.append(dict(cell=e["cell"], libcell=self.cells[e["cell"]].library_cell.split("__")[-1] if e["cell"] in self.cells else "",
                             edit=e["label"], kind=e["kind"], steps_resimulated=len(ks),
                             dE_glitch_fJ=g - bg, dE_functional_fJ=f - bf, dE_total_fJ=(g + f) - (bg + bf),
                             dE_total_pct=100 * ((g + f) - (bg + bf)) / self.E_total,
                             dE_glitch_pct=100 * (g - bg) / self.E_glitch,
                             settle_before_ps=worst / 1000, settle_after_ps=max(others, s) / 1000))
        return rows

    def suggest(self, cells, settle_tolerance=0.0):
        """Evaluate all edits of ``cells``; return (all rows, best edit per cell, combined row).
        An edit qualifies when it lowers total dynamic energy and does not raise the
        worst observed settling time by more than ``settle_tolerance`` (fraction)."""
        edits = [e for c in cells for e in self.edits_for(c)]
        rows = self.evaluate(edits) if edits else []
        best = {}
        for e, r in zip(edits, rows):
            r["_cells"] = e["cells"]
            ok = r["dE_total_fJ"] < 0 and r["settle_after_ps"] <= r["settle_before_ps"] * (1 + settle_tolerance) + 1e-9
            r["qualifies"] = ok
            if ok and (r["cell"] not in best or r["dE_total_fJ"] < best[r["cell"]]["dE_total_fJ"]):
                best[r["cell"]] = r
        combined = None
        if len(best) > 1:
            merged = {}
            for r in sorted(best.values(), key=lambda r: r["dE_total_fJ"]):
                if any(k in merged and merged[k] != v for k, v in r["_cells"].items()):
                    continue        # conflicting edit of a shared driver: keep the better one
                merged.update(r["_cells"])
            combined = self.evaluate([dict(cell="+".join(best), kind="combined",
                                           label=" + ".join(f"{r['cell']}: {r['edit']}" for r in best.values()),
                                           cells=merged)])[0]
        for r in rows:
            r.pop("_cells", None)
        return rows, list(best.values()), combined


def recommend(best, combined):
    """The edit set to recommend: the combined set only if it beats the best single
    edit (edits can interfere), else the best single edit; None if nothing qualifies."""
    single = min(best, key=lambda r: r["dE_total_fJ"]) if best else None
    if combined is not None and single is not None and combined["dE_total_fJ"] < single["dE_total_fJ"] \
            and combined["settle_after_ps"] <= combined["settle_before_ps"] + 1e-9:
        return dict(combined, recommended_as="combined")
    return dict(single, recommended_as="single") if single else None


"""Per-vector glitch analysis: simulate, classify, attribute energy.

For every input vector k (applied from the settled state of vector k-1):
  1. simulate with the chosen pulse model (M0 / M1 / M2);
  2. split each net's transitions into the functionally required one (if the
     stable value changes) and excess pulse pairs (B-phase classify.extract_pulses);
  3. trace each pulse to its root(s) (lineage.classify_glitch_lineages);
  4. assign energy.

Energy convention (supply energy; Liberty internal energy in cap_unit x voltage_unit^2 -> fJ;
VDD = the library's nom_voltage):
  E(transition) = E_internal(Liberty rise/fall_power, input slew, load) + 1/2 C_load VDD^2
so a full output cycle costs C V^2 + E_int,rise + E_int,fall.
Energy accounting:
  "CONVENTIONAL" (M0, M1): every fired transition costs full energy, filtered pulses cost 0.
  "CALIBRATED"   (M2): a fired pulse pair costs S_E(r) * E_cycle and a filtered pulse
                 costs S_E(r) * E_cycle, with r = w_in / d and S_E the SPICE curve.
Causal attribution: a glitch with k roots gives 1/k of its energy to each root;
a filtered pulse is attributed to the roots of its causing pulses, or is its own root.
"""
from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict
from dataclasses import replace

import numpy as np

from .classify import extract_pulses
from .functional import evaluate_stable
from .lineage import classify_glitch_lineages
from .liberty_power import read_internal_power, internal_energy_pj, liberty_units
from .model import StimulusEpoch
from .m2model import DEFAULT as M2_DEFAULT

VDD = 1.8


from .m2model import proxy_key


class EnergyModel:
    def __init__(self, lib_path, network, m2_json=M2_DEFAULT, spice_scale=False):
        """spice_scale=True divides Liberty transition energy by the per-cell median
        Liberty/SPICE full-cycle ratio (data/m2/liberty_vs_spice_energy.csv)."""
        cells = sorted({c.library_cell for c in network.cells})
        self.scale = {}
        self._pk = {}
        if spice_scale and m2_json and (Path(m2_json).parent / "liberty_vs_spice_energy.csv").exists():
            import csv
            rows = list(csv.DictReader(open(Path(m2_json).parent / "liberty_vs_spice_energy.csv")))
            by = defaultdict(list)
            for r in rows:
                by[r["cell"]].append(float(r["ratio"]))
            self.scale = {k: 1.0 / float(np.median(v)) for k, v in by.items()}
        self.power = read_internal_power(lib_path, cells)
        u = liberty_units(lib_path)
        self.vdd, self._tu_fs, self._cu_ff, self._eu_fj = u["vdd"], u["time_ps"] * 1000.0, u["cap_ff"], u["energy_fj"]
        self.se = {k: {p: (np.array(v["S_E_curve"]["r"]), np.array(v["S_E_curve"]["S"]))
                       for p, v in d.items() if "S_E_curve" in v}
                   for k, d in (json.loads(open(m2_json).read())["cells"].items() if m2_json else ())}

    def transition_fj(self, c, rise, related_pin, slew_fs, load_ff):
        tabs = self.power[c.library_cell][(c.library_output_pin, related_pin)]
        e_int = internal_energy_pj(tabs, rise, slew_fs / self._tu_fs, load_ff / self._cu_ff) * self._eu_fj
        k = c.library_cell.split("__")[-1]
        sk = self._pk.get(("s", k))
        if sk is None:
            sk = self._pk[("s", k)] = (k if k in self.scale else proxy_key(k, self.scale)) or k
        return (e_int + 0.5 * load_ff * self.vdd ** 2) * self.scale.get(sk, 1.0)

    def s_e(self, c, out_pol, r):
        key = c.library_cell.split("__")[-1]
        if ("e", key) not in self._pk:
            self._pk[("e", key)] = (key if key in self.se else proxy_key(key, self.se)) or key
        key = self._pk[("e", key)]
        curve = self.se.get(key, {}).get(out_pol)
        if curve is None:
            return 1.0
        return float(np.interp(r, curve[0], curve[1]))


def analyze(sim, energy: EnergyModel, vectors, initial=None, t0_fs=100_000, on_trace=None, prevs=None):
    """Run every vector (or clock cycle) independently from the previous settled state.

    ``vectors[k]`` is either {net: value} (one atomic update) or a clock cycle
    [(offset_fs, {net: value}), ...] whose updates happen at t0 + offset.
    ``prevs[k]``: explicit starting state of step k (independent steps, e.g. a cycle
    sample); by default each step starts from the state left by the previous one."""
    net = sim.network
    cells = {c.name: c for c in net.cells}
    prev = dict(initial or net.initial_inputs)
    totals = defaultdict(float)
    local_by_cell = defaultdict(float)     # glitch energy consumed at a cell output
    causal_by_cell = defaultdict(float)    # glitch energy caused by roots born at a cell
    counts = defaultdict(int)
    per_vector = []
    base = net
    for k, vec in enumerate(vectors, 1):
        if prevs is not None:
            prev = dict(prevs[k - 1])
        steps = vec if isinstance(vec, list) else [(0, vec)]
        cur = dict(prev)
        for _, upd in steps:
            cur.update(upd)
        sim.network = replace(base, initial_inputs=dict(prev))
        # all sub-steps of one cycle share epoch id k (one analysis window)
        res = sim.run([StimulusEpoch(t0_fs + off, dict(upd), k) for off, upd in steps] or
                      [StimulusEpoch(t0_fs, {}, k)])
        tr, meta, loads = res["trace"], res["meta"], res["loads"]
        if on_trace is not None:
            on_trace(k, res)
        before, after = evaluate_stable(net, prev, sim.order), evaluate_stable(net, cur, sim.order)
        pulses = extract_pulses(tr, {k: before}, {k: after})
        recs, _ = classify_glitch_lineages(tr, pulses)
        rec_by_id = {r.glitch_id: r for r in recs}
        pulse_events = set()
        evmap = {e.event_id: e for e in tr}

        def e_of(ev):
            m = meta[ev.event_id]
            return energy.transition_fj(cells[ev.source_instance], ev.new_value == 1,
                                        m.related_pin, m.slew_in_fs, loads.get(ev.net, 0.0))

        root_cell = {}
        vec_glitch = 0.0
        vec_local = defaultdict(float)
        for p in pulses:
            a, b = evmap[p.start_event_id], evmap[p.end_event_id]
            pulse_events.update((a.event_id, b.event_id))
            e = e_of(a) + e_of(b)
            if sim.model == "M2":
                ma, mb = meta[a.event_id], meta[b.event_id]
                r = (mb.cause_fs - ma.cause_fs) / ma.delay_fs if ma.delay_fs > 0 else 9.9
                e *= energy.s_e(cells[a.source_instance], p.polarity, r)
            rec = rec_by_id[p.pulse_id]
            local_by_cell[a.source_instance] += e
            vec_local[a.source_instance] += e
            if rec.classification == "GENERATED":
                root_cell[rec.root_ids[0]] = a.source_instance
            counts[rec.classification] += 1
            vec_glitch += e
            totals["E_glitch_fired_fJ"] += e
            rec_e = e / len(rec.root_ids)
            for rid in rec.root_ids:
                totals.setdefault("_pending_roots", 0.0)
                causal_by_cell[("ROOT", k, rid)] += rec_e
        # resolve root ids -> origin cells (root ids are per-vector)
        for key in [kk for kk in causal_by_cell if isinstance(kk, tuple) and kk[1] == k]:
            causal_by_cell[root_cell[key[2]]] += causal_by_cell.pop(key)

        # filtered pulses
        boundary_owner = {}
        for r_ in recs:
            boundary_owner[r_.start_event_id] = r_
            boundary_owner[r_.end_event_id] = r_
        for s in res["suppressed"]:
            counts["FILTERED"] += 1
            if sim.model != "M2":
                continue
            c = cells[s.instance]
            pol = "positive" if s.lead_value == 1 else "negative"
            e_cyc = (energy.transition_fj(c, True, s.lead_related_pin, s.slew_fs, loads.get(s.net, 0.0)) +
                     energy.transition_fj(c, False, s.lead_related_pin, s.slew_fs, loads.get(s.net, 0.0)))
            e = energy.s_e(c, pol, max(0.0, s.width_in_fs / max(1, s.delay_fs))) * e_cyc
            totals["E_glitch_filtered_fJ"] += e
            vec_glitch += e
            local_by_cell[s.instance] += e
            vec_local[s.instance] += e
            owners = {boundary_owner[i].root_ids for i in (*s.lead_parents, *s.cancel_parents)
                      if i in boundary_owner}
            roots = sorted({rid for t in owners for rid in t})
            if roots:
                for rid in roots:
                    causal_by_cell[root_cell.get(rid, s.instance)] += e / len(roots)
            else:
                causal_by_cell[s.instance] += e
        # functional transitions
        e_fun = sum(e_of(ev) for ev in tr if ev.source_instance != "$PI" and ev.event_id not in pulse_events)
        totals["E_functional_fJ"] += e_fun
        counts["functional_transitions"] += sum(1 for ev in tr if ev.source_instance != "$PI"
                                                and ev.event_id not in pulse_events)
        counts["glitch_transitions"] += 2 * len(pulses)
        counts["reruns"] += res.get("reruns", 0)
        per_vector.append(dict(k=k, E_fun=e_fun, E_glitch=vec_glitch, n_pulses=len(pulses),
                               n_filtered=len(res["suppressed"]), local=dict(vec_local)))
        prev = cur
    totals.pop("_pending_roots", None)
    totals["E_glitch_fJ"] = totals["E_glitch_fired_fJ"] + totals["E_glitch_filtered_fJ"]
    totals["E_total_fJ"] = totals["E_glitch_fJ"] + totals["E_functional_fJ"]
    totals["glitch_fraction"] = totals["E_glitch_fJ"] / totals["E_total_fJ"] if totals["E_total_fJ"] else 0.0
    g = totals["E_glitch_fJ"] or 1.0
    gci = {c: v / g for c, v in sorted(causal_by_cell.items(), key=lambda x: -x[1])}
    return dict(totals=dict(totals), counts=dict(counts), local=dict(local_by_cell),
                causal=dict(causal_by_cell), gci=gci, per_vector=per_vector)

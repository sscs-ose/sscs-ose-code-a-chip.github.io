"""Arrival-skew vs rejection-window records (for hazard-window analysis).

For every two-pin hazard at a cell -- a pulse whose leading and trailing edges are
caused by different input pins -- record the arrival skew w between the two
causes, the cell delay d, the SPICE-calibrated rejection window R and whether the
pulse survived (fired) or was filtered.  Glitches are generated exactly when the
skew falls outside the cell's rejection window, so the spread of w across data
patterns tells whether delay balancing can work at all.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

import numpy as np

from .classify import extract_pulses
from .functional import evaluate_stable
from .model import StimulusEpoch


def collect_skew(sim, steps, initial):
    rows = []
    prev = dict(initial)
    for k, st in enumerate(steps):
        ups = st if isinstance(st, list) else [(0, st)]
        cur = dict(prev)
        for _, u in ups:
            cur.update(u)
        sim.network = replace(sim.network, initial_inputs=dict(prev))
        res = sim.run([StimulusEpoch(100_000 + o, dict(u), 1) for o, u in ups] or [StimulusEpoch(100_000, {}, 1)])
        tr, meta = res["trace"], res["meta"]
        ev = {e.event_id: e for e in tr}
        for p in extract_pulses(tr, {1: evaluate_stable(sim.network, prev, sim.order)}, {1: evaluate_stable(sim.network, cur, sim.order)}):
            a, b = ev[p.start_event_id], ev[p.end_event_id]
            ma, mb = meta[a.event_id], meta[b.event_id]
            if ma.related_pin != mb.related_pin:
                rows.append(dict(step=k, cell=a.source_instance, lead_pin=ma.related_pin, trail_pin=mb.related_pin,
                                 skew_ps=(mb.cause_fs - ma.cause_fs) / 1000, delay_ps=ma.delay_fs / 1000,
                                 reject_ps=ma.reject_fs / 1000, outcome="survived"))
        for s in res["suppressed"]:
            trail = {ev[i].net for i in s.cancel_parents if i in ev}
            rows.append(dict(step=k, cell=s.instance, lead_pin=s.lead_related_pin, trail_pin="|".join(sorted(trail)),
                             skew_ps=s.width_in_fs / 1000, delay_ps=s.delay_fs / 1000, reject_ps=s.reject_fs / 1000,
                             outcome="filtered"))
        prev = cur
    return rows


def balanceability(rows):
    """Per cell: median skew, interquartile spread and the 'spread ratio' IQR/median.
    A spread ratio >~0.5 means no single delay change can cancel the skew for most
    data patterns (path balancing cannot work)."""
    by = defaultdict(list)
    for r in rows:
        by[r["cell"]].append(r["skew_ps"])
    out = {}
    for c, v in by.items():
        v = np.asarray(v)
        q1, med, q3 = np.percentile(v, [25, 50, 75])
        out[c] = dict(n=len(v), median_ps=float(med), iqr_ps=float(q3 - q1),
                      spread_ratio=float((q3 - q1) / med) if med > 0 else float("inf"))
    return out

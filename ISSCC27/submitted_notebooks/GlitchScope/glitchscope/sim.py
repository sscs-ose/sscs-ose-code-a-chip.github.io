"""Unified pulse-aware event simulator (M0 / M1 / M2).

Semantics are inherited from the closed B3 (transport) and B4 (inertial)
engines, with three extensions needed for synthesised benchmark circuits:

* Simultaneous multi-input changes: instead of failing closed, the arc that
  produces the *earliest* output response (minimum Liberty delay) is selected
  and recorded (``multi_input_policy = MIN_DELAY_ARC``).
* M0 overtaking: a reversal whose output event would land at or before the
  still-pending opposite event is a non-positive-width pulse; both events are
  removed and recorded (``M0_NONPOSITIVE_WIDTH``).  Where no overtake occurs,
  M0 is event-for-event identical to the B3 TransportSimulator.
* M2 calibrated rejection: a pulse whose input-side width w (time between the
  causes of its leading and trailing edges) is below R = r_filter * d of the
  generating cell is removed.  For R <= d this is decided while the leading
  edge is still pending.  For R > d the leading edge has already fired, so the
  violation is recorded and the epoch is re-simulated with that edge rejected
  (earliest violation first; deterministic, therefore converges).

M1 (``pulse_model="M1"``) is identical to the B4 InertialSimulator.
"""
from __future__ import annotations

import heapq
import os
from .delay import DelayResult
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .model import ScheduledEvent, TraceEvent
from .logic import eval_primitive
from .netlist import build_fanout, topo_cells
from .functional import evaluate_stable
from .load import derive_net_loads


@dataclass
class _Pending:
    eid: int
    time_fs: int
    value: int
    cause_fs: int
    delay_fs: int
    reject_fs: int          # R in fs
    slew_fs: int
    epoch_id: int
    parents: Tuple[int, ...]
    doomed: bool = False
    key: Tuple = ()


@dataclass(frozen=True)
class Suppressed:
    instance: str
    net: str
    epoch_id: int
    lead_value: int          # value the cancelled leading edge would have set
    cause_fs: int            # cause time of the leading edge
    cancel_fs: int           # cause time of the reversal
    width_in_fs: int         # cancel_fs - cause_fs
    delay_fs: int            # d of the leading edge
    reject_fs: int
    slew_fs: int
    reason: str
    lead_parents: Tuple[int, ...] = ()
    cancel_parents: Tuple[int, ...] = ()
    lead_related_pin: str = ""


@dataclass
class EventMeta:
    cause_fs: int
    delay_fs: int
    slew_in_fs: int
    slew_out_fs: int
    related_pin: str
    reject_fs: int
    multi_input: bool


class EpochRejectError(RuntimeError):
    pass


class PulseSimulator:
    def __init__(self, network, delay_provider, pulse_model="M1",
                 r_filter: Optional[Callable] = None,
                 default_input_slew_fs=0, input_slew_fs_by_net=None, wire_cap_ff_by_net=None,
                 primary_output_load_ff_by_net=None, max_reruns=5000, ideal_cells=(),
                 rollback=True, checkpoint_every=None, engine=None, delay_scale=None, trail_slew_alpha=None):
        if pulse_model not in ("M0", "M1", "M2"):
            raise ValueError(pulse_model)
        if pulse_model == "M2" and r_filter is None:
            raise ValueError("M2 requires an r_filter(cell, out_polarity, slew_fs, delay_fs) callable")
        self.network = network
        self.dp = delay_provider
        self.model = pulse_model
        self.r_filter = r_filter
        self.default_input_slew_fs = int(default_input_slew_fs)
        self.input_slew_fs_by_net = {k: int(v) for k, v in (input_slew_fs_by_net or {}).items()}
        self.max_reruns = max_reruns
        self.rollback = bool(rollback)
        # optional per-instance delay/slew factors {cell name: factor} (local process variation)
        self.delay_scale = dict(delay_scale) if delay_scale else None
        # M2 trailing-edge slew: the input edge that ends a pulse acts alpha * (its slew - the
        # leading edge's slew) early, so a pulse of input-side width w counts as
        # w - alpha (s_trail - s_lead).  None: per cell and pulse polarity from the M2 calibration
        # (``trail_alpha``, measured by scripts/trail_slew_sweep.py; 0 where not calibrated);
        # a number: that alpha for every cell.
        if trail_slew_alpha is None and os.environ.get("GS_TRAIL_ALPHA"):     # e.g. 0: the model without it
            trail_slew_alpha = os.environ["GS_TRAIL_ALPHA"]
        self.trail_slew_alpha = None if trail_slew_alpha is None else float(trail_slew_alpha)
        # "auto": compiled core when available (identical results), else Python;
        # "native": compiled core required; "python": always the Python engine
        from .fastsim import engine_default
        self.engine = engine or engine_default()
        if self.engine not in ("auto", "native", "python"):
            raise ValueError(f"engine={engine!r}")
        self._core = None
        # checkpoint interval (time steps): a checkpoint copies O(cells) of state, a
        # rollback replays on average half an interval, so the interval grows with the
        # circuit (None = automatic; 3x faster M2 on a 16k-cell multiplier than a fixed 32)
        if checkpoint_every is None:
            checkpoint_every = max(32, len(network.cells) // 32)
        self.checkpoint_every = max(1, int(checkpoint_every))
        # do(.) intervention: these cells are glitch-free oracles -- their output moves
        # once, directly to the final value of the run, at the first input event that
        # logically implies it (no excess transitions, no filtered pulses).
        self.ideal = frozenset(ideal_cells)
        lib = getattr(delay_provider, "lib", None)
        self.loads = {} if lib is None else {n: q.total_ff for n, q in derive_net_loads(
            network, lib, wire_cap_ff_by_net=wire_cap_ff_by_net,
            primary_output_load_ff_by_net=primary_output_load_ff_by_net).items()}
        self.fanout, _ = build_fanout(network)
        self.order = topo_cells(network)
        self.topo_index = {c.name: i for i, c in enumerate(self.order)}

    # ------------------------------------------------------------------
    def run(self, epochs):
        """Simulate; for M2, iteratively reject leading edges of pulses found too
        narrow only after they fired (R > d).  Violations are resolved in order of
        DETECTION time; rejections that become stale (their pulse no longer
        reverses after an upstream change) are dropped again.

        ``self.rollback`` (default True) makes each re-simulation resume from a
        checkpoint taken before the earliest point the change can affect, and stop
        at the first time step that reports a violation (time-warp style); with
        ``rollback=False`` every re-simulation restarts from t = 0 and runs to the
        end (reference behaviour, kept for equivalence tests).

        With the compiled core (``engine``) the same result is computed in C++."""
        if self.engine != "python":
            res = self._run_native(epochs)
            if res is not None:
                return res
        reject: set = set()
        seen = set()
        ctx = {"snaps": [], "t_change": None} if (self.model == "M2" and self.rollback) else None
        for attempt in range(self.max_reruns + 1):
            res = self._run_once(epochs, reject, ctx)
            fc = res.get("first_cause", {})
            if res["stale"]:
                keys = set(res["stale"])
                reject -= keys
                change = [fc[k] for k in keys if k in fc]
            elif not res["violations"]:
                res["reruns"] = attempt
                res.pop("first_cause", None)
                return res
            else:
                v = min(res["violations"], key=lambda x: (x[3], x[1], x[0]))
                reject.add(v[:3])
                change = [fc[v[:3]]] if v[:3] in fc else []
            if ctx is not None:
                ctx["t_change"] = min(change) if change else None
            state = frozenset(reject)
            if state in seen:
                raise EpochRejectError("M2 rollback cycled")
            seen.add(state)
        raise EpochRejectError("M2 rollback did not converge")

    def _run_native(self, epochs):
        from . import fastsim
        core = self._core
        if core is None or core is False or not core.supports(self.network):
            if core is False and self.engine == "auto":
                return None
            try:
                core = self._core = fastsim.core_for(self)
            except Exception:
                if self.engine == "native":
                    raise
                self._core = False
                return None
            if not core.supports(self.network):
                if self.engine == "native":
                    raise RuntimeError("native core: network not supported (undriven nets without initial value)")
                return None
        return core.run(self, epochs)

    # ------------------------------------------------------------------
    def _trail_alpha(self, c, lead_value):
        if self.trail_slew_alpha is not None:
            return self.trail_slew_alpha
        f = getattr(self.r_filter, "trail_alpha", None)
        return f(c, "positive" if lead_value else "negative") if f else 0.0

    def _reject_fs(self, c, new_value, slew_fs, delay_fs):
        if self.model == "M0":
            return 0
        if self.model == "M1":
            return delay_fs
        r = self.r_filter(c, "positive" if new_value else "negative", slew_fs, delay_fs)
        return int(round(r * delay_fs))

    def _run_once(self, epochs, reject, ctx=None):
        net = self.network
        restoring = (ctx is not None and ctx["t_change"] is not None
                     and any(sn["T"] < ctx["t_change"] for sn in ctx["snaps"]))
        physical = {} if restoring else dict(evaluate_stable(net, net.initial_inputs, self.order))
        logical = {} if restoring else {c.name: physical[c.output] for c in net.cells}
        pending: Dict[str, List[_Pending]] = defaultdict(list)
        last_fired: Dict[str, Tuple[int, int, int, int]] = {}  # cell -> (time, value, cause, R)
        trace, suppressed, violations = [], [], []
        meta: Dict[int, EventMeta] = {}
        event_by_id, event_slew = {}, {}
        q, canceled = [], set()
        first_cause, cancel_log = {}, []   # rollback bookkeeping
        track = ctx is not None
        counters = {"eid": 1, "seq": 1}
        ordered = sorted(epochs, key=lambda e: (e.time_fs, e.epoch_id))
        for a, b in zip(ordered, ordered[1:]):
            if a.time_fs == b.time_fs:
                raise ValueError("same-time epochs must be merged into one atomic epoch")
        state = {"last_epoch": None}

        def any_pending():
            return any(pending.values())

        final_state = {}
        if self.ideal:
            pis = dict(net.initial_inputs)
            for ep in ordered:
                pis.update(ep.updates)
            final_state = evaluate_stable(net, pis, self.order)

        def stable_check(final=False):
            if self.ideal and not final:
                return
            exp = evaluate_stable(net, {pi: physical[pi] for pi in net.primary_inputs}, self.order)
            for n, v in exp.items():
                if physical.get(n) != v:
                    raise AssertionError(f"{self.model} timed/final mismatch net={n} "
                                         f"timed={physical.get(n)} functional={v}")

        def record_cancel(c, p: _Pending, t, reason, cancel_parents=()):
            canceled.add(p.eid)
            cancel_log.append(p.eid)
            suppressed.append(Suppressed(c.name, c.output, p.epoch_id, p.value, p.cause_fs, t,
                                         t - p.cause_fs, p.delay_fs, p.reject_fs, p.slew_fs, reason,
                                         p.parents, tuple(sorted(cancel_parents)),
                                         meta[p.eid].related_pin if p.eid in meta else ""))

        def choose_arc(c, new_value, pins, parent_ids, changed_nets):
            cands = []
            for pin, n in c.inputs.items():
                if n not in changed_nets:
                    continue
                pe = [event_by_id[i] for i in parent_ids if i in event_by_id and event_by_id[i].net == n]
                if len(pe) != 1:
                    raise ValueError(f"need exactly one causal event on {c.name}.{pin}")
                ev = pe[0]
                slew = event_slew[ev.event_id]
                try:
                    d = self.dp.delay(c, new_value, input_slew_fs=slew,
                                      load_ff=self.loads.get(c.output, 0.0), related_pin=pin,
                                      pin_values=pins, input_transition=(ev.old_value, ev.new_value))
                except (ValueError, KeyError):
                    continue
                if self.delay_scale:
                    f = self.delay_scale.get(c.name, 1.0)
                    d = DelayResult(int(math.floor(d.delay_fs * f + 0.5)), int(math.floor(d.output_slew_fs * f + 0.5)),
                                    d.model)
                cands.append((d.delay_fs, pin, ev, slew, d))
            if not cands:
                raise ValueError(f"no valid timing arc for {c.name} -> {new_value}")
            cands.sort(key=lambda x: (x[0], x[1]))
            return cands[0], len(cands) > 1

        def schedule_cell(c, t, parent_ids, changed_nets):
            pins = {p: physical[n] for p, n in c.inputs.items()}
            new_logical = eval_primitive(c.kind, pins)
            if c.name in self.ideal:
                tgt = final_state[c.output]
                logical[c.name] = new_logical
                if new_logical != tgt or physical[c.output] == tgt or pending[c.name]:
                    return
            elif new_logical == logical[c.name]:
                return
            logical[c.name] = new_logical
            plist = pending[c.name]
            if self.model == "M2":
                sl = [event_slew[i] for i in parent_ids if i in event_slew]
                s_tr = max(sl) if sl else self.default_input_slew_fs
            if plist:
                last = plist[-1]
                w = t - last.cause_fs
                if self.model == "M2":
                    a_tr = self._trail_alpha(c, last.value)
                    if a_tr:
                        w -= int(a_tr * (s_tr - last.slew_fs))
                if last.doomed or self.model == "M1" or w < last.reject_fs:
                    plist.pop()
                    record_cancel(c, last, t, "M2_REJECTED_ROLLBACK" if last.doomed else
                                  ("M1_INERTIAL" if self.model == "M1" else "M2_BELOW_REJECTION"), parent_ids)
                    if new_logical == (plist[-1].value if plist else physical[c.output]):
                        return
            elif self.model == "M2" and c.name in last_fired and c.name not in self.ideal:
                ft, fv, fcause, fR, fslew = last_fired[c.name]
                a_tr = self._trail_alpha(c, fv)
                wv = t - fcause - (int(a_tr * (s_tr - fslew)) if a_tr else 0)
                if fv == physical[c.output] and fv != new_logical and wv < fR:
                    violations.append((c.name, ft, fv, t))
            (dly, pin, ev, slew, dres), multi = choose_arc(c, new_logical, pins, parent_ids, changed_nets)
            eid = counters["eid"]; counters["eid"] += 1
            ev_time = t + dres.delay_fs
            if plist and ev_time <= plist[-1].time_fs:
                # non-positive-width pulse: remove the pending edge and this one
                prev = plist.pop()
                record_cancel(c, prev, t, "NONPOSITIVE_WIDTH", parent_ids)
                return
            R = self._reject_fs(c, new_logical, slew, dres.delay_fs)
            p = _Pending(eid, ev_time, new_logical, t, dres.delay_fs, R, slew, ev.epoch_id,
                         tuple(sorted(parent_ids)))
            meta[eid] = EventMeta(t, dres.delay_fs, slew, int(dres.output_slew_fs), pin, R, multi)
            if track:
                first_cause.setdefault((c.name, ev_time, new_logical), t)
            if (c.name, ev_time, new_logical) in reject:
                p.doomed = True
                p.key = (c.name, ev_time, new_logical)
            else:
                heapq.heappush(q, ScheduledEvent(ev_time, counters["seq"], eid, c.output,
                                                 new_logical, c.name, p.parents))
                counters["seq"] += 1
            event_slew[eid] = int(dres.output_slew_fs)
            plist.append(p)

        def fan(actual, t):
            affected, parents, changed = {}, defaultdict(set), defaultdict(set)
            for ev in actual:
                for c in self.fanout.get(ev.net, []):
                    affected[c.name] = c
                    parents[c.name].add(ev.event_id)
                    changed[c.name].add(ev.net)
            for n in sorted(affected, key=lambda x: self.topo_index[x]):
                schedule_cell(affected[n], t, parents[n], changed[n])

        def apply_epoch(ep):
            evs = []
            for n in sorted(ep.updates):
                if n not in net.primary_inputs:
                    raise ValueError(f"non-PI stimulus {n}")
                old, new = physical[n], int(ep.updates[n])
                if old != new:
                    eid = counters["eid"]; counters["eid"] += 1
                    te = TraceEvent(eid, ep.time_fs, ep.epoch_id, n, old, new, "$PI", ())
                    physical[n] = new
                    trace.append(te); event_by_id[eid] = te
                    event_slew[eid] = self.input_slew_fs_by_net.get(n, self.default_input_slew_fs)
                    evs.append(te)
            fan(evs, ep.time_fs)
            state["last_epoch"] = ep.epoch_id
            if not any_pending():
                stable_check()

        def process(t):
            batch = []
            while q and q[0].time_fs == t:
                e = heapq.heappop(q)
                if e.event_id not in canceled:
                    batch.append(e)
            batch.sort(key=lambda e: (e.net, e.sequence, e.event_id))
            actual = []
            for e in batch:
                plist = pending[e.source_instance]
                idx = next(i for i, p in enumerate(plist) if p.eid == e.event_id)
                p = plist.pop(idx)
                cur = physical[e.net]
                if e.new_value != cur:
                    te = TraceEvent(e.event_id, e.time_fs, p.epoch_id, e.net, cur, e.new_value,
                                    e.source_instance, e.parent_event_ids)
                    physical[e.net] = e.new_value
                    trace.append(te); event_by_id[te.event_id] = te
                    last_fired[e.source_instance] = (e.time_fs, e.new_value, p.cause_fs, p.reject_fs, p.slew_fs)
                    actual.append(te)
            fan(actual, t)
            if not any_pending():
                stable_check()

        i, step = 0, 0
        K = self.checkpoint_every
        snaps = ctx["snaps"] if track else None
        if track:
            tc = ctx["t_change"]
            if tc is None:
                snaps.clear()
            else:
                while snaps and snaps[-1]["T"] >= tc:
                    snaps.pop()
            if snaps:
                sn, prev = snaps[-1], ctx["live"]
                eid0 = sn["eid"]
                physical.clear(); physical.update(sn["physical"])
                logical.clear(); logical.update(sn["logical"])
                pending.clear(); pending.update({k: list(v) for k, v in sn["pending"].items()})
                last_fired.clear(); last_fired.update(sn["last_fired"])
                trace[:] = prev["trace"][:sn["ntrace"]]
                suppressed[:] = prev["suppressed"][:sn["nsup"]]
                cancel_log[:] = prev["cancel_log"][:sn["nsup"]]
                canceled.clear(); canceled.update(cancel_log)
                meta.update({k: v for k, v in prev["meta"].items() if k < eid0})
                event_by_id.update({k: v for k, v in prev["event_by_id"].items() if k < eid0})
                event_slew.update({k: v for k, v in prev["event_slew"].items() if k < eid0})
                first_cause.update({k: v for k, v in prev["first_cause"].items() if v < sn["T"]})
                q[:] = list(sn["q"])
                counters.update(eid=eid0, seq=sn["seq"])
                state["last_epoch"] = sn["last_epoch"]
                i, step = sn["i"], sn["step"]

        def snapshot(T):
            snaps.append(dict(T=T, step=step, i=i, physical=dict(physical), logical=dict(logical),
                              pending={k: list(v) for k, v in pending.items() if v},
                              last_fired=dict(last_fired), ntrace=len(trace), nsup=len(suppressed),
                              eid=counters["eid"], seq=counters["seq"], q=list(q),
                              last_epoch=state["last_epoch"]))

        def keep_live():
            if track:
                ctx["live"] = dict(trace=trace, suppressed=suppressed, cancel_log=cancel_log, meta=meta,
                                   event_by_id=event_by_id, event_slew=event_slew, first_cause=first_cause)

        while i < len(ordered) or q:
            while q and q[0].event_id in canceled:
                heapq.heappop(q)
            if i >= len(ordered) and not q:
                break
            nt = q[0].time_fs if q else None
            is_epoch = i < len(ordered) and (nt is None or ordered[i].time_fs <= nt)
            if track and step % K == 0 and (not snaps or snaps[-1]["step"] < step):
                snapshot(ordered[i].time_fs if is_epoch else nt)
            step += 1
            if is_epoch:
                apply_epoch(ordered[i]); i += 1
            else:
                process(nt)
            if track and violations:
                # earliest-detected violation is final for this attempt: stop here
                keep_live()
                return {"stale": [], "violations": violations, "first_cause": first_cause}
        keep_live()
        stale = [p.key for pl in pending.values() for p in pl if p.doomed]
        if stale:
            return {"stale": stale, "violations": violations, "first_cause": first_cause}
        if any_pending():
            raise AssertionError("non-doomed pending events left after queue drained")
        stable_check(final=True)
        return {"trace": trace, "final": physical, "suppressed": suppressed,
                "violations": violations, "stale": [], "meta": meta, "loads": self.loads,
                "model": self.model, "first_cause": first_cause}

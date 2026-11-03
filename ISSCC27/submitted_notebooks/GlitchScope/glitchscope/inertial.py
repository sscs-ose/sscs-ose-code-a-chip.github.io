from __future__ import annotations
import heapq
from dataclasses import dataclass
from collections import defaultdict
from typing import Tuple

from .model import ScheduledEvent, TraceEvent
from .logic import eval_primitive
from .netlist import build_fanout, topo_cells
from .functional import evaluate_stable
from .delay import ConstantDelayProvider
from .load import derive_net_loads

@dataclass(frozen=True)
class SuppressedTransition:
    event_id: int
    instance: str
    net: str
    target_value: int
    scheduled_time_fs: int
    cancel_time_fs: int
    epoch_id: int
    original_parent_event_ids: Tuple[int, ...]
    cancel_parent_event_ids: Tuple[int, ...]
    reason: str

class InertialSimulator:
    """
    M1 simple event-inertial simulator.

    Each cell may have at most one pending output transition. If the cell's
    logical output reverses before that pending transition fires, the pending
    transition is canceled. If the output transition has already fired, a
    later reversal schedules normally.

    This is deliberately an event-level inertial model, not a calibrated
    cell-specific pulse-width model. M2 calibration belongs to a later phase.
    """
    pulse_model = "M1_SIMPLE_EVENT_INERTIAL"

    def __init__(self, network, delay_provider=None, default_input_slew_fs=0,
                 load_ff_by_net=None, input_slew_fs_by_net=None,
                 auto_load_from_liberty=False, wire_cap_ff_by_net=None,
                 primary_output_load_ff_by_net=None, propagate_slew=True):
        self.network = network
        self.delay_provider = delay_provider or ConstantDelayProvider()
        self.default_input_slew_fs = int(default_input_slew_fs)
        self.input_slew_fs_by_net = {
            k: int(v) for k, v in dict(input_slew_fs_by_net or {}).items()
        }
        self.propagate_slew = bool(propagate_slew)

        bad_input_slew = sorted(
            set(self.input_slew_fs_by_net) - set(network.primary_inputs)
        )
        if bad_input_slew:
            raise ValueError(
                "input_slew_fs_by_net contains non-primary-input nets: "
                + ",".join(bad_input_slew)
            )
        if any(v < 0 for v in self.input_slew_fs_by_net.values()):
            raise ValueError("Input slew must be nonnegative")

        if auto_load_from_liberty and load_ff_by_net:
            raise ValueError(
                "Use either explicit load_ff_by_net or auto_load_from_liberty, not both"
            )

        self.load_breakdown_by_net = {}
        if auto_load_from_liberty:
            lib = getattr(self.delay_provider, "lib", None)
            if lib is None:
                raise ValueError(
                    "auto_load_from_liberty requires a delay provider with a Liberty library"
                )
            self.load_breakdown_by_net = derive_net_loads(
                network, lib,
                wire_cap_ff_by_net=wire_cap_ff_by_net,
                primary_output_load_ff_by_net=primary_output_load_ff_by_net,
            )
            self.load_ff_by_net = {
                net: q.total_ff for net, q in self.load_breakdown_by_net.items()
            }
        else:
            self.load_ff_by_net = {
                k: float(v) for k, v in dict(load_ff_by_net or {}).items()
            }
            if any(v < 0.0 for v in self.load_ff_by_net.values()):
                raise ValueError("Explicit net load must be nonnegative")

        self.fanout, _ = build_fanout(network)
        self.order = topo_cells(network)
        self.topo_index = {c.name: i for i, c in enumerate(self.order)}

        self.last_event_slew_fs = {}
        self.last_event_delay_model = {}
        self.last_net_load_ff = dict(self.load_ff_by_net)
        self.last_overlap_epoch_ids = ()
        self.last_settled_epoch_ids = ()
        self.last_trace_time_monotonic = True
        self.last_global_chronological_queue = True
        self.last_suppressed_transitions = ()
        self.last_suppressed_event_ids = ()
        self.last_inertial_tie_policy = "external_epoch_first_cancel_if_equal_time"

    def _initial(self):
        stable = evaluate_stable(self.network, self.network.initial_inputs)
        physical = dict(stable)
        logical = {c.name: stable[c.output] for c in self.network.cells}
        return physical, logical

    def run(self, epochs):
        physical, logical = self._initial()
        trace = []
        next_event_id = 1
        sequence = 1
        event_slew_fs = {}
        scheduled_slew_fs = {}
        scheduled_model = {}
        scheduled_epoch_id = {}
        scheduled_meta = {}
        event_by_id = {}

        ordered_epochs = sorted(epochs, key=lambda x: (x.time_fs, x.epoch_id))
        epoch_ids = [e.epoch_id for e in ordered_epochs]
        if len(set(epoch_ids)) != len(epoch_ids):
            raise ValueError("M1 requires unique epoch_id values")
        for a, b in zip(ordered_epochs, ordered_epochs[1:]):
            if a.time_fs == b.time_fs:
                raise ValueError(
                    "M1 ambiguous same-time stimulus epochs; combine updates into one "
                    f"atomic epoch: epoch_ids={a.epoch_id},{b.epoch_id} "
                    f"time_fs={a.time_fs}"
                )

        q = []
        canceled_event_ids = set()
        pending_by_cell = {}
        epoch_index = 0
        last_applied_epoch_id = None
        overlap_epoch_ids = []
        settled_epoch_ids = []
        suppressed = []

        def purge_canceled_head():
            while q and q[0].event_id in canceled_event_ids:
                heapq.heappop(q)

        def active_pending():
            return bool(pending_by_cell)

        def stable_check(epoch_id):
            pi_state = {
                pi: physical[pi] for pi in self.network.primary_inputs
            }
            expected = evaluate_stable(self.network, pi_state)
            for net, val in expected.items():
                if physical.get(net) != val:
                    raise AssertionError(
                        f"M1 timed/final mismatch epoch={epoch_id} net={net} "
                        f"timed={physical.get(net)} functional={val}"
                    )
            if epoch_id is not None:
                settled_epoch_ids.append(epoch_id)

        def cancel_pending(c, t_fs, cancel_parent_ids):
            eid = pending_by_cell.pop(c.name, None)
            if eid is None:
                return None
            canceled_event_ids.add(eid)
            meta = scheduled_meta[eid]
            suppressed.append(SuppressedTransition(
                event_id=eid,
                instance=c.name,
                net=c.output,
                target_value=meta["new_value"],
                scheduled_time_fs=meta["time_fs"],
                cancel_time_fs=t_fs,
                epoch_id=meta["epoch_id"],
                original_parent_event_ids=meta["parent_event_ids"],
                cancel_parent_event_ids=tuple(sorted(cancel_parent_ids)),
                reason="logical_reversal_before_pending_output_fired",
            ))
            return eid

        def schedule_cell(c, t_fs, parent_ids, changed_nets):
            nonlocal next_event_id, sequence
            pins = {pin: physical[net] for pin, net in c.inputs.items()}
            new_logical = eval_primitive(c.kind, pins)
            old_logical = logical[c.name]
            if new_logical == old_logical:
                return

            # M1 rule: a logical reversal invalidates the still-pending output.
            cancel_pending(c, t_fs, parent_ids)
            logical[c.name] = new_logical

            # If the cell has returned to its current physical output, no new
            # output transition is needed after cancellation.
            if new_logical == physical[c.output]:
                return

            changed_pins = sorted(
                pin for pin, net in c.inputs.items() if net in changed_nets
            )
            if len(changed_pins) != 1:
                if len(c.inputs) == 1 and len(changed_pins) == 0:
                    related_pin = next(iter(c.inputs))
                else:
                    raise ValueError(
                        "M1 ambiguous simultaneous multi-input timing event: "
                        f"instance={c.name} changed_pins={changed_pins}"
                    )
            else:
                related_pin = changed_pins[0]

            rnet = c.inputs[related_pin]
            pe = [
                event_by_id[i]
                for i in parent_ids
                if i in event_by_id and event_by_id[i].net == rnet
            ]
            if len(pe) != 1:
                raise ValueError(
                    "M1 requires exactly one causal transition on the related pin: "
                    f"instance={c.name} pin={related_pin} parents="
                    f"{[x.event_id for x in pe]}"
                )

            input_transition = (pe[0].old_value, pe[0].new_value)
            if self.propagate_slew:
                if pe[0].event_id not in event_slew_fs:
                    raise AssertionError(
                        f"Missing slew metadata for event {pe[0].event_id}"
                    )
                input_slew_fs = event_slew_fs[pe[0].event_id]
            else:
                input_slew_fs = self.default_input_slew_fs

            dres = self.delay_provider.delay(
                c, new_logical,
                input_slew_fs=input_slew_fs,
                load_ff=self.load_ff_by_net.get(c.output, 0.0),
                related_pin=related_pin,
                pin_values=pins,
                input_transition=input_transition,
            )

            eid = next_event_id
            ev_time = t_fs + dres.delay_fs
            parent_tuple = tuple(sorted(parent_ids))
            scheduled_slew_fs[eid] = int(dres.output_slew_fs)
            scheduled_model[eid] = str(dres.model)
            scheduled_epoch_id[eid] = pe[0].epoch_id
            scheduled_meta[eid] = {
                "time_fs": ev_time,
                "new_value": new_logical,
                "epoch_id": pe[0].epoch_id,
                "parent_event_ids": parent_tuple,
            }
            pending_by_cell[c.name] = eid

            heapq.heappush(
                q,
                ScheduledEvent(
                    ev_time, sequence, eid, c.output, new_logical,
                    c.name, parent_tuple
                )
            )
            sequence += 1
            next_event_id += 1

        def apply_epoch(epoch):
            nonlocal next_event_id, last_applied_epoch_id
            purge_canceled_head()
            if active_pending():
                overlap_epoch_ids.append(epoch.epoch_id)

            pi_events = []
            for net in sorted(epoch.updates):
                if net not in self.network.primary_inputs:
                    raise ValueError(
                        f"Stimulus update targets non-primary-input net {net}"
                    )
                oldv = physical[net]
                newv = int(epoch.updates[net])
                if newv not in (0, 1):
                    raise ValueError("Binary logic only.")
                if oldv != newv:
                    eid = next_event_id
                    ev = TraceEvent(
                        eid, epoch.time_fs, epoch.epoch_id,
                        net, oldv, newv, "$PI", ()
                    )
                    next_event_id += 1
                    physical[net] = newv
                    trace.append(ev)
                    event_by_id[eid] = ev
                    pi_events.append(ev)
                    event_slew_fs[eid] = self.input_slew_fs_by_net.get(
                        net, self.default_input_slew_fs
                    )

            affected = {}
            parents = defaultdict(set)
            changed = defaultdict(set)
            for ev in pi_events:
                for c in self.fanout.get(ev.net, []):
                    affected[c.name] = c
                    parents[c.name].add(ev.event_id)
                    changed[c.name].add(ev.net)

            for n in sorted(affected, key=lambda x: self.topo_index[x]):
                schedule_cell(
                    affected[n], epoch.time_fs, parents[n], changed[n]
                )

            last_applied_epoch_id = epoch.epoch_id
            purge_canceled_head()
            if not active_pending():
                stable_check(last_applied_epoch_id)

        def process_internal_time(t):
            batch = []
            while q and q[0].time_fs == t:
                ev = heapq.heappop(q)
                if ev.event_id in canceled_event_ids:
                    continue
                batch.append(ev)
            batch.sort(key=lambda e: (e.net, e.sequence, e.event_id))

            actual = []
            by_net = defaultdict(list)
            for ev in batch:
                by_net[ev.net].append(ev)

            for net in sorted(by_net):
                for ev in by_net[net]:
                    # This event is no longer pending once its physical time arrives.
                    if pending_by_cell.get(ev.source_instance) == ev.event_id:
                        pending_by_cell.pop(ev.source_instance)

                    cur = physical[net]
                    if ev.new_value != cur:
                        if ev.event_id not in scheduled_epoch_id:
                            raise AssertionError(
                                f"Missing scheduled epoch for event {ev.event_id}"
                            )
                        te = TraceEvent(
                            ev.event_id, ev.time_fs,
                            scheduled_epoch_id[ev.event_id],
                            ev.net, cur, ev.new_value,
                            ev.source_instance, ev.parent_event_ids
                        )
                        physical[net] = ev.new_value
                        trace.append(te)
                        event_by_id[te.event_id] = te
                        if ev.event_id not in scheduled_slew_fs:
                            raise AssertionError(
                                f"Missing scheduled slew for event {ev.event_id}"
                            )
                        event_slew_fs[te.event_id] = scheduled_slew_fs[
                            ev.event_id
                        ]
                        actual.append(te)

            affected = {}
            parents = defaultdict(set)
            changed = defaultdict(set)
            for ev in actual:
                for c in self.fanout.get(ev.net, []):
                    affected[c.name] = c
                    parents[c.name].add(ev.event_id)
                    changed[c.name].add(ev.net)

            for n in sorted(affected, key=lambda x: self.topo_index[x]):
                schedule_cell(affected[n], t, parents[n], changed[n])

            purge_canceled_head()
            if not active_pending():
                stable_check(last_applied_epoch_id)

        while epoch_index < len(ordered_epochs) or q:
            purge_canceled_head()
            if epoch_index >= len(ordered_epochs) and not q:
                break

            next_epoch_t = (
                ordered_epochs[epoch_index].time_fs
                if epoch_index < len(ordered_epochs) else None
            )
            next_internal_t = q[0].time_fs if q else None

            # Same boundary policy as B3: external PI epoch first. Under M1,
            # an input reversal exactly at a pending output event time cancels it.
            if (
                next_epoch_t is not None
                and (next_internal_t is None or next_epoch_t <= next_internal_t)
            ):
                epoch = ordered_epochs[epoch_index]
                apply_epoch(epoch)
                epoch_index += 1
                continue

            process_internal_time(next_internal_t)

        if last_applied_epoch_id is not None:
            stable_check(last_applied_epoch_id)

        times = [e.time_fs for e in trace]
        if times != sorted(times):
            raise AssertionError(
                "M1 global chronological scheduler produced non-monotonic trace"
            )

        self.last_event_slew_fs = dict(event_slew_fs)
        self.last_event_delay_model = {
            eid: scheduled_model[eid]
            for eid in event_slew_fs
            if eid in scheduled_model
        }
        self.last_net_load_ff = dict(self.load_ff_by_net)
        self.last_overlap_epoch_ids = tuple(overlap_epoch_ids)
        self.last_settled_epoch_ids = tuple(settled_epoch_ids)
        self.last_trace_time_monotonic = True
        self.last_global_chronological_queue = True
        self.last_suppressed_transitions = tuple(suppressed)
        self.last_suppressed_event_ids = tuple(x.event_id for x in suppressed)
        return trace, physical

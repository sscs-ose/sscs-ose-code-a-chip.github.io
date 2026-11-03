import heapq
from collections import defaultdict
from .model import ScheduledEvent, TraceEvent
from .logic import eval_primitive
from .netlist import build_fanout, topo_cells
from .functional import evaluate_stable
from .delay import ConstantDelayProvider
from .load import derive_net_loads

class TransportTemporalOrderError(RuntimeError):
    """Fail-closed M0 guard for same-cell output-event overtaking.

    With state-dependent rise/fall delays, a later logical output transition can
    sometimes be assigned an absolute event time that is earlier than (or equal
    to) an already-pending transition from the same cell. Pure event-transport
    is then not temporally well-defined without an additional pulse-resolution
    model. B7 rejects that unsupported corner explicitly instead of allowing a
    stale later event to corrupt the final state.
    """
    def __init__(self, instance, net, previous_event_id,
                 previous_time_fs, new_time_fs, previous_target, new_target):
        self.instance = instance
        self.net = net
        self.previous_event_id = int(previous_event_id)
        self.previous_time_fs = int(previous_time_fs)
        self.new_time_fs = int(new_time_fs)
        self.previous_target = int(previous_target)
        self.new_target = int(new_target)
        super().__init__(
            "M0 output-event temporal overtake: "
            f"instance={instance} net={net} "
            f"pending_event_id={previous_event_id} "
            f"pending_time_fs={previous_time_fs} "
            f"new_time_fs={new_time_fs} "
            f"pending_target={previous_target} new_target={new_target}"
        )

class TransportSimulator:
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
        self.last_temporal_order_guard_enabled = True
        self.last_temporal_order_rejection = None

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
        pending_by_cell = defaultdict(list)

        ordered_epochs = sorted(epochs, key=lambda x: (x.time_fs, x.epoch_id))
        epoch_ids = [e.epoch_id for e in ordered_epochs]
        if len(set(epoch_ids)) != len(epoch_ids):
            raise ValueError("B3 requires unique epoch_id values")
        for a, b in zip(ordered_epochs, ordered_epochs[1:]):
            if a.time_fs == b.time_fs:
                raise ValueError(
                    "B3 ambiguous same-time stimulus epochs; combine updates into one "
                    f"atomic epoch: epoch_ids={a.epoch_id},{b.epoch_id} "
                    f"time_fs={a.time_fs}"
                )

        q = []
        epoch_index = 0
        last_applied_epoch_id = None
        overlap_epoch_ids = []
        settled_epoch_ids = []

        def stable_check(epoch_id):
            pi_state = {
                pi: physical[pi] for pi in self.network.primary_inputs
            }
            expected = evaluate_stable(self.network, pi_state)
            for net, val in expected.items():
                if physical.get(net) != val:
                    raise AssertionError(
                        f"Timed/final mismatch epoch={epoch_id} net={net} "
                        f"timed={physical.get(net)} functional={val}"
                    )
            if epoch_id is not None:
                settled_epoch_ids.append(epoch_id)

        def schedule_cell(c, t_fs, parent_ids, changed_nets):
            nonlocal next_event_id, sequence
            pins = {pin: physical[net] for pin, net in c.inputs.items()}
            new_logical = eval_primitive(c.kind, pins)
            old_logical = logical[c.name]
            if new_logical == old_logical:
                return
            logical[c.name] = new_logical

            changed_pins = sorted(
                pin for pin, net in c.inputs.items() if net in changed_nets
            )

            if len(changed_pins) != 1:
                if len(c.inputs) == 1 and len(changed_pins) == 0:
                    related_pin = next(iter(c.inputs))
                else:
                    raise ValueError(
                        "B2 ambiguous simultaneous multi-input timing event: "
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
                    "B2 requires exactly one causal transition on the related pin: "
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

            ev_time = t_fs + dres.delay_fs
            pending = pending_by_cell[c.name]
            if pending:
                prev_id = pending[-1]
                prev = scheduled_meta[prev_id]
                if ev_time <= prev["time_fs"]:
                    err = TransportTemporalOrderError(
                        c.name, c.output, prev_id, prev["time_fs"], ev_time,
                        prev["new_value"], new_logical
                    )
                    self.last_temporal_order_rejection = {
                        "instance": c.name,
                        "net": c.output,
                        "previous_event_id": prev_id,
                        "previous_time_fs": prev["time_fs"],
                        "new_time_fs": ev_time,
                        "previous_target": prev["new_value"],
                        "new_target": new_logical,
                    }
                    raise err

            eid = next_event_id
            parent_tuple = tuple(sorted(parent_ids))
            scheduled_slew_fs[eid] = int(dres.output_slew_fs)
            scheduled_model[eid] = str(dres.model)
            scheduled_epoch_id[eid] = pe[0].epoch_id
            scheduled_meta[eid] = {
                "time_fs": ev_time,
                "new_value": new_logical,
                "instance": c.name,
                "net": c.output,
            }
            pending.append(eid)

            heapq.heappush(
                q,
                ScheduledEvent(
                    ev_time, sequence, eid,
                    c.output, new_logical, c.name,
                    parent_tuple
                )
            )
            sequence += 1
            next_event_id += 1

        def apply_epoch(epoch):
            nonlocal next_event_id, last_applied_epoch_id
            if q:
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

        def process_internal_time(t):
            batch = []
            while q and q[0].time_fs == t:
                batch.append(heapq.heappop(q))
            batch.sort(key=lambda e: (e.net, e.sequence, e.event_id))

            actual = []
            by_net = defaultdict(list)
            for ev in batch:
                by_net[ev.net].append(ev)

            for net in sorted(by_net):
                for ev in by_net[net]:
                    plist = pending_by_cell.get(ev.source_instance, [])
                    if ev.event_id in plist:
                        plist.remove(ev.event_id)
                    if not plist and ev.source_instance in pending_by_cell:
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

        while epoch_index < len(ordered_epochs) or q:
            next_epoch_t = (
                ordered_epochs[epoch_index].time_fs
                if epoch_index < len(ordered_epochs) else None
            )
            next_internal_t = q[0].time_fs if q else None

            # Deterministic B3 tie policy: external PI epoch first.
            if (
                next_epoch_t is not None
                and (next_internal_t is None or next_epoch_t <= next_internal_t)
            ):
                epoch = ordered_epochs[epoch_index]
                apply_epoch(epoch)
                epoch_index += 1
                if not q:
                    stable_check(last_applied_epoch_id)
                continue

            t = next_internal_t
            process_internal_time(t)
            if not q:
                stable_check(last_applied_epoch_id)

        if last_applied_epoch_id is not None:
            pi_state = {
                pi: physical[pi] for pi in self.network.primary_inputs
            }
            expected = evaluate_stable(self.network, pi_state)
            for net, val in expected.items():
                if physical.get(net) != val:
                    raise AssertionError(
                        f"Timed/final mismatch epoch={last_applied_epoch_id} "
                        f"net={net} timed={physical.get(net)} functional={val}"
                    )

        times = [e.time_fs for e in trace]
        if times != sorted(times):
            raise AssertionError(
                "B3 global chronological scheduler produced non-monotonic trace"
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
        self.last_temporal_order_guard_enabled = True
        return trace, physical

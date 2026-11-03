from __future__ import annotations
from dataclasses import dataclass, replace
from collections import defaultdict

@dataclass(frozen=True)
class Pulse:
    pulse_id: str
    epoch_id: int
    net: str
    start_event_id: int
    end_event_id: int
    start_fs: int
    end_fs: int
    width_fs: int
    polarity: str

def extract_pulses(trace, stable_before, stable_after):
    groups = defaultdict(list)
    for e in trace:
        if e.source_instance != "$PI":
            groups[(e.epoch_id, e.net)].append(e)
    raw = []
    for epoch, net in sorted(groups):
        evs = sorted(groups[(epoch,net)], key=lambda e:(e.time_fs,e.event_id))
        b = stable_before[epoch].get(net)
        a = stable_after[epoch].get(net)
        if b is None or a is None:
            continue
        if (len(evs) % 2) != (b ^ a):
            raise AssertionError(f"Transition parity violation epoch={epoch} net={net}")
        if b == a:
            excess = evs
        else:
            if not evs or evs[-1].new_value != a:
                raise AssertionError(f"Final transition mismatch epoch={epoch} net={net}")
            excess = evs[:-1]
        if len(excess) % 2:
            raise AssertionError(f"Odd excess transition count epoch={epoch} net={net}")
        for i in range(0,len(excess),2):
            e0,e1 = excess[i],excess[i+1]
            raw.append(Pulse("",epoch,net,e0.event_id,e1.event_id,
                             e0.time_fs,e1.time_fs,e1.time_fs-e0.time_fs,
                             "positive" if e0.new_value else "negative"))
    raw.sort(key=lambda p:(p.epoch_id,p.start_fs,p.end_fs,p.net,p.start_event_id))
    return [replace(p,pulse_id=f"G{i:04d}") for i,p in enumerate(raw,1)]

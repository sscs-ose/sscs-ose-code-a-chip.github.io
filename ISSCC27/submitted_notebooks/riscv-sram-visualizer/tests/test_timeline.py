from dataclasses import FrozenInstanceError

import pytest

from riscv_memory_visualizer.simulation.events import MemoryEvent, MemoryEventType as T
from riscv_memory_visualizer.simulation.timeline import EventTimeline


def test_event_creation_and_immutability():
    event = MemoryEvent(T.MEMORY_REQUEST, 5, 36, 2, 1, 1, "Read request")
    assert (event.cycle, event.address, event.row, event.column, event.value) == (5, 36, 2, 1, 1)
    assert event.event_type is T.MEMORY_REQUEST
    assert event.description == "Read request"
    with pytest.raises(FrozenInstanceError):
        event.value = 0


def test_timeline_order_filter_snapshot_clear():
    timeline = EventTimeline()
    assert len(timeline) == 0 and timeline.events() == ()
    events = tuple(MemoryEvent(T.MEMORY_REQUEST, cycle=c, description="Request") for c in (5, 2, 5, None))
    for event in events:
        timeline.add(event)
    snapshot = timeline.snapshot()
    assert snapshot == events == timeline.events()
    assert timeline.get_cycle(5) == (events[0], events[2])
    assert timeline.get_cycle(None) == (events[3],)
    assert timeline.get_cycle(99) == ()
    with pytest.raises(TypeError):
        snapshot[0] = events[1]
    timeline.clear()
    assert len(timeline) == 0 and snapshot == events


@pytest.mark.parametrize("kwargs", [dict(event_type="READ"), dict(cycle=-1), dict(cycle=True), dict(description=" ")])
def test_invalid_event(kwargs):
    arguments = dict(event_type=T.MEMORY_REQUEST, description="Request")
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        MemoryEvent(**arguments)


def test_timeline_rejects_non_event():
    with pytest.raises(ValueError):
        EventTimeline().add("request")

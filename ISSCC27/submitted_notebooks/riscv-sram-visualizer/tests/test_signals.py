"""Logical observations preserve actual values, cycle context and event order."""

from dataclasses import FrozenInstanceError

import pytest

from riscv_memory_visualizer.cpu.processor import Processor
from riscv_memory_visualizer.cpu.parser import InstructionParser
from riscv_memory_visualizer.memory.array import SRAMArray
from riscv_memory_visualizer.memory.sram8t import SRAMCell8T
from riscv_memory_visualizer.simulation.controller import MemoryEventEngine
from riscv_memory_visualizer.simulation.processor_memory import ProcessorEventMemory
from riscv_memory_visualizer.simulation.events import MemoryEvent, MemoryEventType as E
from riscv_memory_visualizer.simulation.signals import SignalSample, SignalTrace, SimulationTraceRecorder
from riscv_memory_visualizer.simulation.timeline import EventTimeline


def test_signal_samples_and_snapshots_are_immutable():
    trace = SignalTrace("Q")
    assert trace.snapshot() == trace.cycles() == trace.values() == ()
    assert trace.value_at(0) is None
    trace.append(1, 0)
    trace.append(3, 1)
    snapshot = trace.snapshot()
    with pytest.raises(FrozenInstanceError):
        snapshot[0].value = 1
    with pytest.raises(TypeError):
        snapshot[0] = SignalSample(0, 1)
    with pytest.raises(FrozenInstanceError):
        trace.series().name = "changed"
    trace.append(4, None)
    assert len(snapshot) == 2
    assert trace.cycles() == (1, 3, 4)
    assert trace.values() == (0, 1, None)
    assert trace.value_at(2) == 0 and trace.value_at(3) == 1 and trace.value_at(9) is None
    assert trace.filter_cycles(2, 3) == (SignalSample(3, 1),)


@pytest.mark.parametrize("cycle", [-1, True, 1.5, "1", None])
def test_invalid_cycle_is_rejected_atomically(cycle):
    trace = SignalTrace("Q")
    with pytest.raises(ValueError):
        trace.append(cycle, 1)
    assert trace.snapshot() == ()


@pytest.mark.parametrize("value", [2, -1, True, False, .5, "ACTIVE", [], {}])
def test_invalid_binary_values(value):
    trace = SignalTrace("WL")
    with pytest.raises(ValueError):
        trace.append(0, value)
    assert trace.snapshot() == ()


def test_domains_types_and_ordering():
    trace = SignalTrace("PC", "integer")
    trace.append(0, 0)
    trace.append(2, 8)
    for cycle in (0, 1, 2):
        with pytest.raises(ValueError, match="order"):
            trace.append(cycle, 12)
    with pytest.raises(ValueError):
        trace.append(3, "12")
    with pytest.raises(ValueError):
        trace.filter_cycles(3, 1)
    stage = SignalTrace("IF", "category")
    stage.append(1, "lw x5,8(x2)")
    with pytest.raises(ValueError):
        stage.append(2, 1)
    events = SignalTrace("READ", domain="event")
    events.append(4, 0, event_order=1)
    events.append(4, 1, event_order=2)
    events.append(None, 0, event_order=3)
    events.append(2, 0, event_order=4)
    assert events.cycles() == (4, 4, None, 2)
    assert len(events.filter_cycles(4, 4)) == 2
    with pytest.raises(ValueError):
        events.append(5, 0, event_order=4)
    with pytest.raises(ValueError):
        events.value_at(4)
    unavailable = SignalTrace("WL", available=False)
    unavailable.append(0, None)
    with pytest.raises(ValueError):
        unavailable.append(1, 0)


def test_event_conversion_preserves_sequence_same_cycle_and_setup():
    array = SRAMArray(4, 4)
    engine = MemoryEventEngine(array)
    recorder = SimulationTraceRecorder(engine.timeline)
    engine.write(8, 1)  # Setup has no CPU cycle.
    engine.read(8, cycle=4)
    recorder.record_events()
    snapshot = recorder.snapshot()
    events = snapshot.events
    assert [e.order for e in events] == list(range(1, len(engine.timeline)+1))
    assert all(e.event is original for e, original in zip(events, engine.timeline.events()))
    read_events = [e for e in events if e.event.cycle == 4]
    assert [e.event.event_type for e in read_events] == [E.MEMORY_REQUEST, E.ADDRESS_DECODE,
        E.ROW_SELECT, E.COLUMN_SELECT, E.WORD_LINE_ACTIVE, E.SRAM_READ, E.MEMORY_RESPONSE, E.OPERATION_COMPLETE]
    assert {s.cycle for s in recorder.event_traces["READ"].snapshot()} == {None, 4}
    assert recorder.event_traces["READ"].values().count(1) == 1
    assert recorder.event_traces["WRITE"].values().count(1) == 1
    assert not recorder.cycle_traces["CYCLE"].snapshot()  # No fake CPU cycles generated.
    before = recorder.snapshot()
    recorder.record_events()
    assert recorder.snapshot() == before


def test_read_write_snapshots_q_wl_and_selection_are_actual():
    array = SRAMArray(4, 4)
    engine = MemoryEventEngine(array)
    recorder = SimulationTraceRecorder(engine.timeline)
    recorder.record_cycle(0, array, cell=(0, 2))
    engine.write(8, 1, cycle=1)
    recorder.record_cycle(1, array, cell=(0, 2))
    engine.read(8, cycle=2)
    recorder.record_cycle(2, array, cell=(0, 2))
    assert recorder.cycle_traces["Q"].values() == (0, 1, 1)
    assert recorder.cycle_traces["Q_bar"].values() == (1, 0, 0)
    assert recorder.cycle_traces["WL"].values() == (0, 1, 1)
    assert recorder.cycle_traces["BL"].values() == (1, 1, 1)
    assert recorder.cycle_traces["BL_bar"].values() == (1, 0, 0)
    assert recorder.cycle_traces["READ"].values() == (0, 0, 1)
    assert recorder.cycle_traces["WRITE"].values() == (0, 1, 0)
    assert recorder.cycle_traces["ROW_SELECT"].values() == (None, 0, 0)
    assert recorder.cycle_traces["COLUMN_SELECT"].values() == (None, 2, 2)
    for ordered in recorder.snapshot().events:
        event = ordered.event
        if event.cell_state is not None:
            for name, field in (("Q", "q"), ("Q_bar", "q_bar"), ("WL", "word_line"), ("BL", "bit_line")):
                assert recorder.event_traces[name].snapshot()[ordered.order-1].value == getattr(event.cell_state, field)
    q = recorder.event_traces["Q"].snapshot()
    before_write = next(s for s, e in zip(q, engine.timeline.events()) if e.event_type == E.WORD_LINE_ACTIVE)
    after_write = next(s for s, e in zip(q, engine.timeline.events()) if e.event_type == E.SRAM_WRITE)
    assert before_write.cycle == after_write.cycle == 1
    assert before_write.value == 0 and after_write.value == 1


def test_different_cells_do_not_share_inferred_signal_history():
    array = SRAMArray(2, 3)
    engine = MemoryEventEngine(array)
    engine.write(0, 1, cycle=4)
    engine.read(20, cycle=4)
    recorder = SimulationTraceRecorder(engine.timeline)
    recorder.record_events()
    samples = recorder.event_traces["Q"].snapshot()
    for sample, event in zip(samples, engine.timeline.events()):
        if event.event_type in (E.MEMORY_REQUEST, E.ADDRESS_DECODE):
            assert sample.value is None
    assert recorder.event_traces["CELL"].values()[-1] == "(1, 2)"
    assert samples[-1].value == 0


def test_processor_pipeline_observation_has_no_side_effects():
    array = SRAMArray(4, 4)
    engine = MemoryEventEngine(array)
    cpu = Processor(engine)
    cpu.memory = ProcessorEventMemory(engine, cpu.state)
    cpu.load_program([InstructionParser().parse("lw x5,8(x2)")])
    engine.write(8, 1)
    recorder = SimulationTraceRecorder(engine.timeline)
    for cycle in range(5):
        before = (cpu.get_state(), cpu.pipeline.snapshot(), cpu.registers.get_all(), array.get_state(), engine.timeline.events())
        recorder.record_cycle(cycle, array, processor=cpu)
        recorder.record_cycle(cycle, array, processor=cpu)
        assert before == (cpu.get_state(), cpu.pipeline.snapshot(), cpu.registers.get_all(), array.get_state(), engine.timeline.events())
        if cycle < 4:
            cpu.step()
    assert recorder.cycle_traces["CYCLE"].values() == (0, 1, 2, 3, 4)
    assert recorder.cycle_traces["IF"].values() == ("EMPTY", "lw x5,8(x2)", "EMPTY", "EMPTY", "EMPTY")
    assert recorder.cycle_traces["ID_EX"].values()[2] == "lw x5,8(x2)"
    assert recorder.cycle_traces["MEM_WB"].values()[3] == "lw x5,8(x2)"
    assert recorder.cycle_traces["PC"].values() == (0, 4, 4, 4, 4)
    assert recorder.cycle_traces["MEMORY_ACCESS"].values() == (0, 0, 0, 0, 1)
    assert cpu.registers.read(5) == 1


def test_abstract_8t_has_no_fabricated_physical_signals():
    array = SRAMArray(4, 4, cell_type=SRAMCell8T)
    engine = MemoryEventEngine(array)
    recorder = SimulationTraceRecorder(engine.timeline, architecture=array.architecture_name, physical_signals=False)
    recorder.record_cycle(0, array, cell=(0, 2))
    engine.write(8, 1, cycle=1)
    recorder.record_cycle(1, array, cell=(0, 2))
    for traces in (recorder.cycle_traces, recorder.event_traces):
        for name in ("WL", "BL", "BL_bar"):
            assert not traces[name].available
            assert all(value is None for value in traces[name].values())
        assert "RWL" not in traces and "RBL" not in traces
    assert recorder.cycle_traces["SELECTED"].values() == (0, 1)
    assert recorder.cycle_traces["Q"].values() == (0, 1)


def test_clear_and_external_reset_detection():
    array = SRAMArray(1, 1)
    engine = MemoryEventEngine(array)
    recorder = SimulationTraceRecorder(engine.timeline)
    engine.read(0, cycle=1)
    recorder.record_cycle(1, array)
    snapshot = recorder.snapshot()
    with pytest.raises(ValueError, match="backwards"):
        recorder.record_cycle(0, array)
    engine.timeline.clear()
    with pytest.raises(ValueError, match="reset"):
        recorder.record_events()
    with pytest.raises(ValueError, match="reset"):
        recorder.snapshot()
    recorder.clear()
    assert not recorder.snapshot().events and recorder.current_cycle == 0
    assert all(not t.snapshot() for t in recorder.cycle_traces.values())
    assert len(snapshot.events) == 8


def test_non_monotonic_event_cycles_are_not_sorted_or_renumbered():
    timeline = EventTimeline()
    for cycle in (5, 2, None, 5):
        timeline.add(MemoryEvent(E.MEMORY_REQUEST, cycle=cycle, description="Request"))
    recorder = SimulationTraceRecorder(timeline)
    recorder.record_events()
    assert recorder.event_traces["READ"].cycles() == (5, 2, None, 5)
    assert [e.order for e in recorder.snapshot().events] == [1, 2, 3, 4]

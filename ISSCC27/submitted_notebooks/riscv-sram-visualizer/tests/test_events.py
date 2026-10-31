import pytest

from riscv_memory_visualizer.memory.array import SRAMArray
from riscv_memory_visualizer.memory.data_memory import DataMemory
from riscv_memory_visualizer.simulation.controller import MemoryEventEngine
from riscv_memory_visualizer.simulation.events import MemoryEventType as T
from riscv_memory_visualizer.simulation.timeline import EventTimeline


PREFIX = [T.MEMORY_REQUEST, T.ADDRESS_DECODE, T.ROW_SELECT, T.COLUMN_SELECT, T.WORD_LINE_ACTIVE]


@pytest.mark.parametrize("writing", [False, True])
def test_end_to_end_sequence_and_actual_cells(writing):
    array = SRAMArray(4, 4)
    if not writing:
        array.write(2, 1, 1)
    engine = MemoryEventEngine(array)
    if writing:
        assert engine.write(36, 1, cycle=5) is None
        suffix = [T.SRAM_WRITE, T.OPERATION_COMPLETE]
    else:
        assert engine.read(36, cycle=5) == 1
        suffix = [T.SRAM_READ, T.MEMORY_RESPONSE, T.OPERATION_COMPLETE]
    events = engine.timeline.events()
    assert [e.event_type for e in events] == PREFIX + suffix
    assert all(e.cycle == 5 and e.address == 36 and e.description for e in events)
    assert all((e.row, e.column) == (2, 1) for e in events[1:])
    access = events[5]
    assert access.value == 1
    assert access.cell_state == array.get_cell(2, 1).get_state()
    assert (access.cell_state.q, access.cell_state.q_bar) == (1, 0)
    assert events[4].cell_state.word_line == 1
    assert array.get_state().word_lines == (0, 0, 1, 0)
    assert (array.selected_row, array.selected_column) == (2, 1)
    assert all(array.get_cell(r, c).q == int((r, c) == (2, 1)) for r in range(4) for c in range(4))
    assert all(array.get_cell(r, c).bit_line == 1 and array.get_cell(r, c).bit_line_bar == 1
               for r in range(4) for c in range(4) if (r, c) != (2, 1))


@pytest.mark.parametrize("index", range(16))
def test_explicit_address_mapping(index):
    engine = MemoryEventEngine(SRAMArray(4, 4))
    assert engine.read(index * 4) == 0
    decoded = engine.timeline.events()[1]
    assert (decoded.row, decoded.column) == (index // 4, index % 4)
    assert all(e.cycle is None for e in engine.timeline.events())


@pytest.mark.parametrize("address", [-1, 1, 2, 63, 64, 264, True, 4.0, "4", None])
def test_bad_addresses_do_not_mutate(address):
    array = SRAMArray(4, 4)
    array.select_cell(1, 1)
    engine = MemoryEventEngine(array)
    before = array.get_state()
    for operation in (lambda: engine.read(address), lambda: engine.write(address, 1)):
        with pytest.raises(ValueError):
            operation()
        assert len(engine.timeline) == 0 and array.get_state() == before


@pytest.mark.parametrize("value", [2, -1, True, False, 1.0, "1", None])
def test_invalid_write_is_atomic(value):
    array = SRAMArray(4, 4)
    engine = MemoryEventEngine(array)
    before = array.get_state()
    with pytest.raises(ValueError):
        engine.write(8, value)
    assert len(engine.timeline) == 0 and array.get_state() == before


@pytest.mark.parametrize("context", [dict(cycle=-1), dict(cycle=True), dict(cycle=1.5), dict(instruction=4), dict(instruction=" ")])
def test_invalid_context_is_atomic(context):
    array = SRAMArray(1, 1)
    engine = MemoryEventEngine(array)
    before = array.get_state()
    with pytest.raises(ValueError):
        engine.read(0, **context)
    assert len(engine.timeline) == 0 and array.get_state() == before


def test_context_history_and_snapshot_stability():
    timeline = EventTimeline()
    array = SRAMArray(4, 4)
    engine = MemoryEventEngine(array, timeline=timeline)
    assert engine.timeline is timeline
    engine.write(8, 1, cycle=3, instruction="sw x6, 8(x0)")
    snapshot = timeline.snapshot()
    assert snapshot[0].event_type == T.INSTRUCTION
    assert all(e.instruction == "sw x6, 8(x0)" for e in snapshot)
    engine.read(8, cycle=4, instruction="lw x5, 8(x0)")
    engine.write(8, 0, cycle=4)
    assert snapshot[-2].cell_state.q == 1
    assert timeline.get_cycle(3) == snapshot
    assert not any(e.event_type == T.WRITEBACK for e in timeline.events())
    timeline.clear()
    assert array.get_cell(0, 2).q == 0


def test_behavioral_memory_records_no_fake_sram_events():
    memory = DataMemory()
    engine = MemoryEventEngine(memory, capacity_words=128)
    engine.write(0x108, 42, cycle=5)
    assert memory.read(0x108) == 42
    assert [e.event_type for e in engine.timeline.events()] == [T.MEMORY_REQUEST, T.OPERATION_COMPLETE]
    engine.timeline.clear()
    assert engine.read(0x108) == 42
    assert [e.event_type for e in engine.timeline.events()] == [T.MEMORY_REQUEST, T.MEMORY_RESPONSE, T.OPERATION_COMPLETE]
    assert all(e.row is None and e.column is None and e.cell_state is None for e in engine.timeline.events())
    with pytest.raises(ValueError):
        engine.read(512)


@pytest.mark.parametrize("size", [0, -1, True, 4.0])
def test_invalid_configuration(size):
    with pytest.raises(ValueError):
        MemoryEventEngine(SRAMArray(2, 2), word_size=size)
    with pytest.raises(ValueError):
        MemoryEventEngine(DataMemory(), capacity_words=size)


def test_configuration_and_non_square_mapping():
    with pytest.raises(ValueError):
        MemoryEventEngine(DataMemory())
    with pytest.raises(ValueError):
        MemoryEventEngine(SRAMArray(1, 1), capacity_words=4)
    engine = MemoryEventEngine(SRAMArray(3, 5), word_size=2)
    engine.write(28, 1)
    assert (engine.memory.selected_row, engine.memory.selected_column) == (2, 4)


def test_backend_failure_does_not_report_completion():
    class FailingMemory:
        def read(self, address):
            raise RuntimeError("backend unavailable")

        def write(self, address, value):
            raise RuntimeError("backend unavailable")

    engine = MemoryEventEngine(FailingMemory(), capacity_words=1)
    for operation in (lambda: engine.read(0), lambda: engine.write(0, 42)):
        engine.timeline.clear()
        with pytest.raises(RuntimeError, match="backend unavailable"):
            operation()
        assert [e.event_type for e in engine.timeline.events()] == [T.MEMORY_REQUEST]

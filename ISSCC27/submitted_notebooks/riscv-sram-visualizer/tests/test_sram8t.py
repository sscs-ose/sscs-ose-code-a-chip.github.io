"""Abstract fallback behavior and real CPU/event/array integration."""

from dataclasses import FrozenInstanceError

import pytest

from riscv_memory_visualizer.memory.base_cell import BaseMemoryCell
from riscv_memory_visualizer.memory.sram6t import SRAMCell6T, SRAMAccessResult
from riscv_memory_visualizer.memory.sram8t import SRAMCell8T, SRAMCell8TState
from riscv_memory_visualizer.memory.array import SRAMArray
from riscv_memory_visualizer.simulation.controller import MemoryEventEngine
from riscv_memory_visualizer.simulation.events import MemoryEventType as T


@pytest.mark.parametrize("initial", [0, 1])
def test_construction_access_and_reset(initial):
    cell = SRAMCell8T(initial)
    assert isinstance(cell, BaseMemoryCell)
    assert cell.get_state() == SRAMCell8TState(initial, 1-initial, 0)
    before = cell.get_state()
    assert not cell.read().success
    assert cell.write(1-initial).data is None
    assert cell.get_state() == before
    cell.set_selected(1)
    for value in (1, 0, 1):
        result = cell.write(value)
        assert isinstance(result, SRAMAccessResult)
        assert result.success and result.operation == "WRITE" and result.data == value
        assert result.state == SRAMCell8TState(value, 1-value, 1)
        state = cell.get_state()
        result = cell.read()
        assert result.success and result.operation == "READ" and result.data == value
        assert cell.get_state() == state
    cell.set_selected(0)
    assert cell.q == 1
    cell.reset()
    assert cell.get_state() == before
    # No physical control/data wires are invented.
    assert not hasattr(cell, "word_line") and not hasattr(cell, "bit_line")


@pytest.mark.parametrize("value", [-1, 2, True, False, 1.0, "1", None])
def test_validation_is_atomic(value):
    with pytest.raises(ValueError):
        SRAMCell8T(value)
    cell = SRAMCell8T(1)
    for selected in (0, 1):
        cell.set_selected(selected)
        before = cell.get_state()
        for action in (cell.set_selected, cell.write):
            with pytest.raises(ValueError):
                action(value)
            assert cell.get_state() == before


def test_snapshots_immutable_detached_and_properties_read_only():
    cell = SRAMCell8T()
    cell.set_selected(1)
    result = cell.write(1)
    with pytest.raises(FrozenInstanceError):
        result.state.q = 0
    with pytest.raises(FrozenInstanceError):
        result.data = 0
    for name in ("q", "q_bar", "selected"):
        with pytest.raises(AttributeError):
            setattr(cell, name, 0)
    cell.reset()
    assert result.state == SRAMCell8TState(1, 0, 1)


def test_array_selection_independence_default_and_reset():
    assert type(SRAMArray(1, 1).get_cell(0, 0)) is SRAMCell6T
    array = SRAMArray(3, 5, cell_type=SRAMCell8T)
    cells = [array.get_cell(r, c) for r in range(3) for c in range(5)]
    assert len({id(c) for c in cells}) == 15
    assert all(isinstance(c, SRAMCell8T) for c in cells)
    assert not array.uses_word_line and array.cell_type is SRAMCell8T
    array.write(2, 4, 1)
    assert array.read(2, 4).data == 1
    assert array.get_state().word_lines == (0, 0, 1)
    assert all(array.get_cell(r, c).selected == int(r == 2) for r in range(3) for c in range(5))
    assert sum(c.q for c in cells) == 1
    before = array.get_state()
    for action in (lambda: array.write(0, 0, 2), lambda: array.read(3, 0),
                   lambda: array.select_cell(0, 5)):
        with pytest.raises(ValueError):
            action()
        assert array.get_state() == before
    array.reset()
    assert array.selected_row is array.selected_column is None
    assert all(c.get_state() == SRAMCell8TState(0, 1, 0) for c in cells)
    assert cells == [array.get_cell(r, c) for r in range(3) for c in range(5)]


@pytest.mark.parametrize("cell_type", [object, None, SRAMCell8T()])
def test_invalid_cell_factory(cell_type):
    with pytest.raises(ValueError, match="cell_type"):
        SRAMArray(1, 1, cell_type=cell_type)


def test_future_cell_can_use_contract_without_cpu_changes():
    class FutureCell(SRAMCell8T):
        architecture_name = "Future abstract example"
    array = SRAMArray(1, 1, cell_type=FutureCell)
    engine = MemoryEventEngine(array)
    engine.write(0, 1)
    assert engine.read(0) == 1
    assert array.architecture_name == "Future abstract example"


def test_event_engine_actual_snapshots_and_no_physical_word_line_claim():
    array = SRAMArray(4, 4, cell_type=SRAMCell8T)
    engine = MemoryEventEngine(array)
    engine.write(36, 1, cycle=5)
    written = next(e for e in engine.timeline.events() if e.event_type == T.SRAM_WRITE)
    assert written.cell_state == SRAMCell8TState(1, 0, 1)
    engine.timeline.clear()
    assert engine.read(36, cycle=6) == 1
    events = engine.timeline.events()
    assert [e.event_type for e in events] == [T.MEMORY_REQUEST, T.ADDRESS_DECODE,
        T.ROW_SELECT, T.COLUMN_SELECT, T.CELL_SELECTED, T.SRAM_READ,
        T.MEMORY_RESPONSE, T.OPERATION_COMPLETE]
    assert all(e.cycle == 6 and e.address == 36 for e in events)
    assert all((e.row, e.column) == (2, 1) for e in events[1:])
    assert all("WL" not in e.description for e in events)
    before = (array.get_state(), engine.timeline.events())
    for action in (lambda: engine.write(36, 2), lambda: engine.read(64), lambda: engine.read(3)):
        with pytest.raises(ValueError):
            action()
        assert before == (array.get_state(), engine.timeline.events())
    array.reset()
    assert written.cell_state.q == 1

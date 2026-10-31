"""Logical SRAM organization, selection, accesses, and stable observations."""

from dataclasses import FrozenInstanceError

import pytest

from riscv_memory_visualizer.memory.array import SRAMArray
from riscv_memory_visualizer.memory.sram6t import SRAMCell6T, SRAMCellState


def cell_states(array):
    return tuple(tuple(array.get_cell(r, c).get_state() for c in range(array.columns))
                 for r in range(array.rows))


@pytest.mark.parametrize("rows, columns", [(4, 4), (8, 8), (3, 5), (1, 1)])
@pytest.mark.parametrize("value", [0, 1])
def test_construction_and_independent_cells(rows, columns, value):
    array = SRAMArray(rows, columns, value)
    cells = [array.get_cell(r, c) for r in range(rows) for c in range(columns)]
    assert len({id(cell) for cell in cells}) == rows * columns
    assert all(isinstance(cell, SRAMCell6T) for cell in cells)
    assert all(cell.get_state() == SRAMCellState(value, 1-value, 0, 1, 1) for cell in cells)
    state = array.get_state()
    assert (state.rows, state.columns) == (rows, columns)
    assert state.selected_row is state.selected_column is None
    assert state.word_lines == (0,) * rows
    assert state.cells == tuple((value,) * columns for _ in range(rows))


def test_row_selection_updates_every_underlying_word_line():
    array = SRAMArray(4, 4)
    for row in (2, 0, 3, 1):
        array.select_row(row)
        assert array.selected_row == row
        assert array.selected_column is None
        assert array.get_state().word_lines == array.row_decoder.get_state()
        for r in range(4):
            for c in range(4):
                assert array.get_cell(r, c).word_line == int(r == row)


def test_column_selection_only_changes_metadata():
    array = SRAMArray(4, 4)
    before = cell_states(array)
    array.select_column(3)
    assert array.selected_row is None
    assert array.selected_column == 3
    assert cell_states(array) == before
    array.select_cell(2, 3)
    before = cell_states(array)
    array.select_column(1)
    assert array.selected_row == 2
    assert array.selected_column == 1
    assert cell_states(array) == before


def test_cell_selection_and_inspection():
    array = SRAMArray(4, 4)
    array.select_cell(2, 3)
    assert array.get_state().word_lines == (0, 0, 1, 0)
    assert array.get_cell(2, 3).word_line == 1
    before = array.get_state()
    array.get_cell(0, 0)
    assert array.get_state() == before


def test_requested_independence_scenario():
    array = SRAMArray(4, 4)
    result = array.write(1, 2, 1)
    assert result.success and result.data == 1
    assert array.read(1, 2).data == 1
    for location in ((1, 1), (0, 2), (2, 2)):
        assert array.read(*location).data == 0
    for r in range(4):
        for c in range(4):
            assert array.get_cell(r, c).q == int((r, c) == (1, 2))


@pytest.mark.parametrize("value", [0, 1])
def test_read_write_and_complements(value):
    array = SRAMArray(4, 4, initial_value=1-value)
    for row, column in ((0, 0), (2, 3), (3, 1)):
        written = array.write(row, column, value)
        assert written.operation == "WRITE" and written.success
        assert written.data == value
        assert written.state == SRAMCellState(value, 1-value, 1, value, 1-value)
        before = array.get_state().cells
        result = array.read(row, column)
        assert result.operation == "READ" and result.success
        assert result.data == value
        assert result.state == written.state
        assert result.message
        assert array.get_state().cells == before
        assert array.selected_row == row and array.selected_column == column
        assert array.get_cell(row, column).word_line == 1


@pytest.mark.parametrize("operation", ["read", "write"])
def test_only_requested_cell_receives_access(operation):
    array = SRAMArray(3, 4)
    array.select_cell(1, 2)
    before = cell_states(array)
    if operation == "read":
        array.read(1, 2)
    else:
        array.write(1, 2, 1)
    after = cell_states(array)
    for r in range(3):
        for c in range(4):
            if (r, c) != (1, 2):
                assert after[r][c] == before[r][c]
    assert after[1][2] != before[1][2]


@pytest.mark.parametrize("initial", [0, 1])
def test_reset_preserves_objects_and_restores_initial_state(initial):
    array = SRAMArray(3, 2, initial)
    objects = [array.get_cell(r, c) for r in range(3) for c in range(2)]
    initial_state = array.get_state()
    array.write(1, 1, 1-initial)
    array.reset()
    assert array.get_state() == initial_state
    assert array.row_decoder.selected_row is None
    assert array.row_decoder.get_state() == (0, 0, 0)
    assert all(array.get_cell(r, c) is objects[r*2+c] for r in range(3) for c in range(2))
    assert all(cell.get_state() == SRAMCellState(initial, 1-initial, 0, 1, 1) for cell in objects)


def test_snapshot_is_immutable_stable_and_does_not_access_cells():
    array = SRAMArray(2, 2)
    before = cell_states(array)
    snapshot = array.get_state()
    assert cell_states(array) == before
    with pytest.raises(FrozenInstanceError):
        snapshot.selected_row = 1
    with pytest.raises(TypeError):
        snapshot.cells[0][0] = 1
    array.write(1, 1, 1)
    assert snapshot.cells == ((0, 0), (0, 0))
    assert snapshot.word_lines == (0, 0)


@pytest.mark.parametrize("dimension", ["rows", "columns"])
@pytest.mark.parametrize("value", [0, -1, True, False, 4.0, "4", None])
def test_invalid_dimensions(dimension, value):
    arguments = {"rows": 4, "columns": 4, dimension: value}
    with pytest.raises(ValueError, match=dimension):
        SRAMArray(**arguments)


@pytest.mark.parametrize("value", [2, -1, True, False, 1.0, "1", None])
def test_invalid_bits_do_not_change_array(value):
    with pytest.raises(ValueError, match="initial_value"):
        SRAMArray(2, 2, value)
    array = SRAMArray(2, 2)
    array.select_cell(0, 0)
    before, signals = array.get_state(), cell_states(array)
    with pytest.raises(ValueError, match="write value"):
        array.write(1, 1, value)
    assert array.get_state() == before
    assert cell_states(array) == signals


@pytest.mark.parametrize("axis", ["row", "column"])
@pytest.mark.parametrize("value", [-1, 4, True, False, 1.0, "1", None])
def test_invalid_locations_are_atomic(axis, value):
    array = SRAMArray(4, 4)
    array.select_cell(1, 2)
    before, signals = array.get_state(), cell_states(array)
    row, column = (value, 0) if axis == "row" else (0, value)
    for method in (array.get_cell, array.select_cell, array.read):
        with pytest.raises(ValueError, match=axis):
            method(row, column)
        assert array.get_state() == before
        assert cell_states(array) == signals
    with pytest.raises(ValueError, match=axis):
        array.write(row, column, 1)
    with pytest.raises(ValueError, match=axis):
        (array.select_row if axis == "row" else array.select_column)(value)
    assert array.get_state() == before
    assert cell_states(array) == signals

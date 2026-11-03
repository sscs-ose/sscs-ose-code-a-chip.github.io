"""Storage invariants, access gating, and immutable 6T cell observations."""

from dataclasses import FrozenInstanceError

import pytest

from riscv_memory_visualizer.memory.base_cell import BaseMemoryCell
from riscv_memory_visualizer.memory.sram6t import SRAMCell6T, SRAMCellState


def test_default_initialization():
    cell = SRAMCell6T()
    assert isinstance(cell, BaseMemoryCell)
    assert cell.get_state() == SRAMCellState(0, 1, 0, 1, 1)


@pytest.mark.parametrize("value", [0, 1])
def test_initial_value_and_reset(value):
    cell = SRAMCell6T(initial_value=value)
    initial = cell.get_state()
    assert initial == SRAMCellState(value, 1 - value, 0, 1, 1)
    cell.set_word_line(1)
    cell.write(1 - value)
    cell.reset()
    assert cell.get_state() == initial


def test_word_line_transitions_preserve_storage_and_lines():
    cell = SRAMCell6T(1)
    for wl in (1, 0, 1, 1, 0):
        cell.set_word_line(wl)
        assert cell.get_state() == SRAMCellState(1, 0, wl, 1, 1)


@pytest.mark.parametrize("initial", [0, 1])
@pytest.mark.parametrize("value", [0, 1])
def test_active_write(initial, value):
    cell = SRAMCell6T(initial)
    cell.set_word_line(1)
    result = cell.write(value)
    assert result.operation == "WRITE"
    assert result.success is True
    assert result.data == value
    assert result.state == cell.get_state() == SRAMCellState(value, 1 - value, 1, value, 1 - value)
    assert "WL=1" in result.message


def test_explicit_complement_sequence():
    cell = SRAMCell6T(initial_value=0)
    assert cell.q == 0
    assert cell.q_bar == 1
    cell.set_word_line(1)
    cell.write(1)
    assert cell.q == 1
    assert cell.q_bar == 0
    cell.write(0)
    assert cell.q == 0
    assert cell.q_bar == 1


@pytest.mark.parametrize("value", [0, 1])
def test_active_read_preserves_storage(value):
    cell = SRAMCell6T(value)
    cell.set_word_line(1)
    for _ in range(3):
        result = cell.read()
        assert result.operation == "READ"
        assert result.success is True
        assert result.data == value
        assert result.state == SRAMCellState(value, 1 - value, 1, value, 1 - value)
        assert cell.q == value
        assert cell.q_bar == 1 - value
        assert "unchanged" in result.message


@pytest.mark.parametrize("value", [0, 1])
@pytest.mark.parametrize("previous_access", [False, True])
def test_inactive_access_changes_no_signals(value, previous_access):
    cell = SRAMCell6T(value)
    if previous_access:
        cell.set_word_line(1)
        cell.read()
        cell.set_word_line(0)
    before = cell.get_state()
    for result in (cell.read(), cell.write(1 - value)):
        assert result.success is False
        assert result.data is None
        assert result.state == before
        assert "WL=0" in result.message
        assert cell.get_state() == before


@pytest.mark.parametrize("value", [2, -1, True, False, 0.0, 1.0, "1", None])
def test_invalid_initial_value(value):
    with pytest.raises(ValueError, match="initial_value must be integer 0 or 1"):
        SRAMCell6T(value)


@pytest.mark.parametrize("value", [2, -1, True, False, 0.0, 1.0, "1", None])
@pytest.mark.parametrize("wl", [0, 1])
def test_invalid_controls_and_write_do_not_mutate(value, wl):
    cell = SRAMCell6T(1)
    cell.set_word_line(wl)
    before = cell.get_state()
    with pytest.raises(ValueError, match="word_line must be integer 0 or 1"):
        cell.set_word_line(value)
    assert cell.get_state() == before
    with pytest.raises(ValueError, match="write value must be integer 0 or 1"):
        cell.write(value)
    assert cell.get_state() == before


def test_snapshots_and_results_are_immutable_and_stable():
    cell = SRAMCell6T()
    snapshot = cell.get_state()
    with pytest.raises(FrozenInstanceError):
        snapshot.q = 1
    cell.set_word_line(1)
    result = cell.read()
    with pytest.raises(FrozenInstanceError):
        result.success = False
    with pytest.raises(FrozenInstanceError):
        result.state.bit_line = 1
    cell.write(1)
    cell.reset()
    assert snapshot == SRAMCellState(0, 1, 0, 1, 1)
    assert result.state == SRAMCellState(0, 1, 1, 0, 1)
    assert result.data == 0


@pytest.mark.parametrize("name", ["q", "q_bar", "word_line", "bit_line", "bit_line_bar"])
def test_public_signals_cannot_bypass_validation(name):
    cell = SRAMCell6T()
    with pytest.raises(AttributeError):
        setattr(cell, name, 2)
    assert cell.get_state() == SRAMCellState(0, 1, 0, 1, 1)


def test_cells_have_independent_storage_and_controls():
    first, second = SRAMCell6T(), SRAMCell6T()
    first.set_word_line(1)
    first.write(1)
    assert second.get_state() == SRAMCellState(0, 1, 0, 1, 1)
    assert first.get_state() == SRAMCellState(1, 0, 1, 1, 0)

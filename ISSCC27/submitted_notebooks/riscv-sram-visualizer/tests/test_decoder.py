"""One-hot selection, arbitrary row counts, and validation."""

import pytest

from riscv_memory_visualizer.memory.decoder import RowDecoder


@pytest.mark.parametrize("rows", [1, 3, 4, 8])
def test_all_addresses_and_reset(rows):
    decoder = RowDecoder(rows)
    assert decoder.get_state() == (0,) * rows
    assert decoder.selected_row is None
    for address in range(rows):
        selection = decoder.decode(address)
        assert len(selection) == rows
        assert sum(selection) == 1
        assert selection[address] == 1
        assert decoder.selected_row == address
        assert [decoder.is_selected(row) for row in range(rows)] == list(selection)
    decoder.reset()
    assert decoder.get_state() == (0,) * rows
    assert decoder.selected_row is None
    assert not any(decoder.is_selected(row) for row in range(rows))


@pytest.mark.parametrize("rows", [0, -1, True, False, 4.0, "4", None])
def test_invalid_dimensions(rows):
    with pytest.raises(ValueError, match="rows must be a positive integer"):
        RowDecoder(rows)


@pytest.mark.parametrize("address", [-1, 3, 4, True, False, 1.0, "1", None])
def test_invalid_address_preserves_selection(address):
    decoder = RowDecoder(3)
    before = decoder.decode(1)
    for method in (decoder.decode, decoder.is_selected):
        with pytest.raises(ValueError, match="row address"):
            method(address)
        assert decoder.get_state() == before


def test_output_is_immutable_and_detached():
    decoder = RowDecoder(4)
    snapshot = decoder.decode(0)
    decoder.decode(3)
    assert snapshot == (1, 0, 0, 0)
    with pytest.raises(TypeError):
        snapshot[0] = 0

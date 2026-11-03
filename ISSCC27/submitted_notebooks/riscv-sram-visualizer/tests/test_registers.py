import pytest

from riscv_memory_visualizer.cpu.registers import RegisterFile


def test_register_initial_state():

    registers = RegisterFile()

    assert registers.read(0) == 0
    assert registers.read(5) == 0


def test_register_write_and_read():

    registers = RegisterFile()

    registers.write(2, 256)

    assert registers.read(2) == 256


def test_x0_cannot_change():

    registers = RegisterFile()

    registers.write(0, 500)

    assert registers.read(0) == 0


def test_invalid_register_negative():

    registers = RegisterFile()

    with pytest.raises(ValueError):
        registers.read(-1)


def test_invalid_register_large():

    registers = RegisterFile()

    with pytest.raises(ValueError):
        registers.write(32, 100)


def test_reset():

    registers = RegisterFile()

    registers.write(5, 123)

    registers.reset()

    assert registers.read(5) == 0


def test_get_all_returns_copy():

    registers = RegisterFile()

    values = registers.get_all()

    values[1] = 999

    assert registers.read(1) == 0


@pytest.mark.parametrize("index", [True, False, 1.0, "1", None])
def test_invalid_index_types_are_rejected_without_mutation(index):
    registers = RegisterFile()
    registers.write(1, 7)
    before = registers.get_all()
    for operation in (lambda: registers.read(index), lambda: registers.write(index, 99)):
        with pytest.raises(ValueError, match="integer between 0 and 31"):
            operation()
        assert registers.get_all() == before

from riscv_memory_visualizer.simulation.state import SimulationState


def test_initial_state():

    state = SimulationState()

    assert state.phase == "IDLE"
    assert state.bit_line == 1.0
    assert state.bit_line_bar == 1.0
    assert state.q == 0
    assert state.q_bar == 1


def test_memory_signal_reset():

    state = SimulationState()

    state.word_line = 1
    state.bit_line = 0.5
    state.bit_line_bar = 0.7
    state.sense_enable = 1
    state.write_enable = 1
    state.phase = "READ"

    state.reset_memory_signals()

    assert state.word_line == 0
    assert state.bit_line == 1.0
    assert state.bit_line_bar == 1.0
    assert state.sense_enable == 0
    assert state.write_enable == 0
    assert state.phase == "IDLE"


def test_cpu_state_not_reset():

    state = SimulationState()

    state.pc = 100
    state.cpu_cycle = 5

    state.reset_memory_signals()

    assert state.pc == 100
    assert state.cpu_cycle == 5
"""CPU adapter context and default SRAM address boundaries for both models."""

import pytest

from riscv_memory_visualizer.cpu.parser import InstructionParser
from riscv_memory_visualizer.cpu.processor import Processor
from riscv_memory_visualizer.memory.array import SRAMArray
from riscv_memory_visualizer.memory.sram6t import SRAMCell6T
from riscv_memory_visualizer.memory.sram8t import SRAMCell8T
from riscv_memory_visualizer.simulation.controller import MemoryEventEngine
from riscv_memory_visualizer.simulation.events import MemoryEventType as E
from riscv_memory_visualizer.simulation.processor_memory import ProcessorEventMemory


@pytest.mark.parametrize("cell_type", [SRAMCell6T, SRAMCell8T])
def test_final_address_load_context_and_rejected_next_address(cell_type):
    array = SRAMArray(4, 4, cell_type=cell_type)
    engine = MemoryEventEngine(array)
    cpu = Processor()
    cpu.memory = ProcessorEventMemory(engine, cpu.state)
    cpu.load_program([InstructionParser().parse("lw x5,60(x0)")])
    engine.write(60, 1)
    assert all(event.cycle is None for event in engine.timeline.events())
    for _ in range(4):
        cpu.step()
    assert cpu.finished and cpu.registers.read(5) == 1
    assert (array.selected_row, array.selected_column) == (3, 3)
    events = engine.timeline.get_cycle(4)
    assert all(event.instruction == "lw x5,60(x0)" for event in events)
    assert any(event.event_type == E.MEMORY_RESPONSE and event.value == 1 for event in events)
    before = array.get_state(), engine.timeline.events(), cpu.get_state()
    for access in (lambda: cpu.memory.read(64), lambda: cpu.memory.write(64, 1)):
        with pytest.raises(ValueError, match="capacity"):
            access()
        assert before == (array.get_state(), engine.timeline.events(), cpu.get_state())
    cpu.reset()
    assert cpu.memory.state is cpu.state and cpu.state.cpu_cycle == 0

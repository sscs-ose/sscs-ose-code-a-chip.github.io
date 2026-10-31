"""Behavioral execution and replaceable memory integration."""

import pytest

from riscv_memory_visualizer.cpu.instruction import Instruction
from riscv_memory_visualizer.cpu.parser import InstructionParser
from riscv_memory_visualizer.cpu.processor import Processor
from riscv_memory_visualizer.memory.data_memory import DataMemory
from riscv_memory_visualizer.simulation.state import SimulationState


def make_cpu(*texts, memory=None):
    cpu = Processor(memory=memory)
    cpu.load_program(map(InstructionParser().parse, texts))
    return cpu


def drain(cpu):
    for _ in range(len(cpu.instruction_memory) + 3):
        cpu.step()
    assert cpu.finished


@pytest.mark.parametrize("text, expected", [
    ("add x3,x1,x2", 17), ("sub x3,x1,x2", -3),
    ("addi x3,x1,-5", 2), ("addi x3,x1,+5", 12),
])
def test_alu_result_and_writeback_timing(text, expected):
    cpu = make_cpu(text)
    cpu.registers.write(1, 7)
    cpu.registers.write(2, 10)
    for _ in range(3):
        cpu.step()
        assert cpu.registers.read(3) == 0
    assert cpu.pipeline.mem_wb_stage.result == expected
    cpu.step()
    assert cpu.registers.read(3) == expected


class RecordingMemory:
    """Independent backend implementing only the required read/write methods."""

    def __init__(self):
        self.accesses = []

    def read(self, address):
        self.accesses.append(("read", address))
        return 42

    def write(self, address, value):
        self.accesses.append(("write", address, value))


@pytest.mark.parametrize("opcode, address", [("lw", 0x108), ("sw", 0x10C)])
def test_memory_address_latching_and_exactly_once_access(opcode, address):
    memory = RecordingMemory()
    cpu = make_cpu(f"{opcode} x5,{address - 0x100}(x2)", memory=memory)
    cpu.registers.write(2, 0x100)
    cpu.registers.write(5, 77)
    for _ in range(3):
        cpu.step()
    assert memory.accesses == []
    assert cpu.pipeline.mem_wb_stage.effective_address == address
    # A later external edit must not change the latched address/store data.
    cpu.registers.write(2, 999)
    cpu.registers.write(5, 88)
    state = cpu.step()
    assert state.instruction_text == str(cpu.instruction_memory[0])
    assert state.effective_address == address
    assert state.operation == ("READ" if opcode == "lw" else "WRITE")
    if opcode == "lw":
        assert cpu.registers.read(5) == 42
        assert memory.accesses == [("read", address)]
    else:
        assert memory.accesses == [("write", address, 77)]
    cpu.step()
    assert len(memory.accesses) == 1


def test_load_from_behavioral_memory():
    cpu = make_cpu("lw x5,8(x2)")
    cpu.registers.write(2, 0x100)
    cpu.memory.write(0x108, 42)
    drain(cpu)
    assert cpu.registers.read(5) == 42


def test_store_to_behavioral_memory():
    cpu = make_cpu("sw x6,12(x3)")
    cpu.registers.write(3, 0x100)
    cpu.registers.write(6, -42)
    drain(cpu)
    assert cpu.memory.read(0x10C) == -42


def test_writeback_before_operand_reads_for_dependent_program():
    cpu = make_cpu("addi x2,x0,256", "lw x5,8(x2)", "add x6,x5,x2",
                   "sw x6,12(x2)", "lw x7,12(x2)")
    cpu.memory.write(0x108, 42)
    drain(cpu)
    assert cpu.registers.read(2) == 256
    assert cpu.registers.read(5) == 42
    assert cpu.registers.read(6) == cpu.registers.read(7) == 298
    assert cpu.memory.read(0x10C) == 298
    assert cpu.state.cpu_cycle == 8


@pytest.mark.parametrize("text", ["addi x0,x0,5", "add x0,x1,x1", "sub x0,x0,x1", "lw x0,0(x0)"])
def test_x0_remains_zero(text):
    cpu = make_cpu(text)
    cpu.registers.write(1, 7)
    cpu.memory.write(0, 123)
    drain(cpu)
    assert cpu.registers.read(0) == 0


def test_reset_flushes_cpu_and_retains_program_and_memory():
    cpu = make_cpu("sw x1,0(x0)")
    cpu.registers.write(1, 9)
    cpu.memory.write(4, 55)
    state_reference = cpu.state
    for _ in range(3):
        cpu.step()
    cpu.reset()
    assert cpu.state is state_reference
    assert cpu.get_state() == SimulationState()
    assert cpu.registers.get_all() == [0] * 32
    assert cpu.pipeline.empty
    assert len(cpu.instruction_memory) == 1
    assert cpu.memory.read(4) == 55
    assert cpu.memory.read(0) == 0
    cpu.step()
    assert cpu.pipeline.if_stage.instruction.opcode == "sw"


def test_loading_new_program_flushes_pending_work_and_copies_input():
    cpu = make_cpu("sw x1,0(x0)")
    cpu.step()
    instruction = InstructionParser().parse("addi x3,x0,7")
    program = [instruction]
    cpu.load_program(program)
    program.clear()
    instruction.immediate = 99
    assert cpu.pc == 0
    assert cpu.pipeline.empty
    drain(cpu)
    assert cpu.registers.read(3) == 7


@pytest.mark.parametrize("instruction", [
    Instruction("mul"), Instruction("add"), Instruction("lw", rd=32, rs1=0, immediate=0),
    Instruction("sw", rd=1, rs1=0, rs2=2, immediate=0), "addi x1,x0,1",
])
def test_invalid_program_leaves_cpu_unchanged(instruction):
    cpu = make_cpu("addi x1,x0,1")
    cpu.step()
    before = cpu.get_state()
    with pytest.raises(ValueError):
        cpu.load_program([instruction])
    assert cpu.get_state() == before
    assert cpu.pipeline.if_stage.instruction.opcode == "addi"


def test_default_memory_is_sparse_and_instances_are_independent():
    first, second = DataMemory(), DataMemory()
    assert first.read(100) == 0
    first.write(100, -7)
    assert first.read(100) == -7
    assert second.read(100) == 0


def test_retirement_fields_clear_on_following_alu_cycle():
    cpu = make_cpu("lw x1,0(x0)", "addi x2,x0,3")
    for _ in range(4):
        cpu.step()
    assert cpu.state.operation == "READ"
    cpu.step()
    assert cpu.state.operation is None
    assert cpu.state.effective_address is None
    assert cpu.state.instruction_text == "addi x2,x0,3"

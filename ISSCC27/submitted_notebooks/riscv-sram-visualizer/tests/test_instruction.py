from riscv_memory_visualizer.cpu.instruction import Instruction


def test_instruction_creation():

    inst = Instruction(
        opcode="lw",
        rd=5,
        rs1=2,
        immediate=8,
        original_text="lw x5, 8(x2)"
    )

    assert inst.opcode == "lw"
    assert inst.rd == 5
    assert inst.rs1 == 2
    assert inst.immediate == 8


def test_instruction_string():

    inst = Instruction(
        opcode="lw",
        original_text="lw x5, 8(x2)"
    )

    assert str(inst) == "lw x5, 8(x2)"


def test_instruction_string_without_original():

    inst = Instruction(
        opcode="add"
    )

    assert str(inst) == "add"
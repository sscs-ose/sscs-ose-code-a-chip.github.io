"""Phase-2 decoding and syntax validation through the public parser API."""

import pytest

from riscv_memory_visualizer.cpu.instruction import Instruction
from riscv_memory_visualizer.cpu.parser import InstructionParser


@pytest.mark.parametrize(
    "text, opcode, rd, rs1, rs2, immediate",
    [
        ("lw x5, 8(x2)", "lw", 5, 2, None, 8),
        ("sw x6, 12(x3)", "sw", None, 3, 6, 12),
        ("add x3, x1, x2", "add", 3, 1, 2, None),
        ("sub x8, x5, x4", "sub", 8, 5, 4, None),
        ("addi x4, x4, 1", "addi", 4, 4, None, 1),
        ("add x0,x31,x0", "add", 0, 31, 0, None),
        ("sw x31, 0(x0)", "sw", None, 0, 31, 0),
        ("lw x31, -8(x0)", "lw", 31, 0, None, -8),
        ("sw x0, +5(x31)", "sw", None, 31, 0, 5),
        ("addi x0, x31, -1", "addi", 0, 31, None, -1),
        ("addi x31, x0, +5", "addi", 31, 0, None, 5),
        ("addi x4, x4, 0", "addi", 4, 4, None, 0),
        ("  lw   x5,8(x2)  ", "lw", 5, 2, None, 8),
        ("\tLW\tX5 , 8 ( X2 )\t", "lw", 5, 2, None, 8),
        ("ADD X3,X1,X2", "add", 3, 1, 2, None),
        ("SuB x8, X5,x4", "sub", 8, 5, 4, None),
        ("SW X6,12(X3)", "sw", None, 3, 6, 12),
        ("ADDI X4, X4, +1", "addi", 4, 4, None, 1),
    ],
)
def test_decoded_fields(text, opcode, rd, rs1, rs2, immediate):
    instruction = InstructionParser().parse(text)
    assert instruction == Instruction(
        opcode=opcode, rd=rd, rs1=rs1, rs2=rs2,
        immediate=immediate, original_text=text.strip(),
    )
    assert str(instruction) == text.strip()


@pytest.mark.parametrize("opcode", ["lw", "sw", "add", "sub", "addi"])
@pytest.mark.parametrize("operands", ["", "x1", "x1,", ",x2", "x1,x2,x3,x4"])
def test_invalid_operand_counts(opcode, operands):
    with pytest.raises(ValueError, match=f"Invalid {opcode} syntax.*Expected:"):
        InstructionParser().parse(f"{opcode} {operands}")


@pytest.mark.parametrize("text", [
    "add x1, x2", "sub x1, x2", "addi x1, x2",
    "sw x1, 4(x2), x3", "lw x1, 4(x2), x3",
    "add x1,,x3", "addi x1,x2,", "add x1 x2 x3",
])
def test_missing_extra_or_empty_operands(text):
    with pytest.raises(ValueError, match="syntax.*Expected:"):
        InstructionParser().parse(text)


@pytest.mark.parametrize("register", [
    "x32", "x33", "x-1", "abc", "r5", "x", "zero", "ra", "sp", "a0", "t0", "x01",
])
@pytest.mark.parametrize("template", [
    "add {},x1,x2", "add x1,{},x2", "sub x1,x2,{}",
    "addi x1,{},1", "lw x1,8({})", "sw {},8(x1)",
])
def test_invalid_registers(register, template):
    with pytest.raises(ValueError, match="Invalid register.*x0 through x31"):
        InstructionParser().parse(template.format(register))


@pytest.mark.parametrize("opcode", ["mul", "and", "beq", "nop", "LWU"])
def test_unsupported_opcode(opcode):
    with pytest.raises(ValueError, match="Unsupported opcode.*Supported:"):
        InstructionParser().parse(f"{opcode} x1,x2,x3")


@pytest.mark.parametrize("operand", [
    "8", "(x2)", "8()", "8(x2", "8x2)", "8((x2))", "8(x2)junk", "8(x2)(x3)",
])
@pytest.mark.parametrize("opcode", ["lw", "sw"])
def test_malformed_memory_operand(opcode, operand):
    with pytest.raises(ValueError, match="Invalid memory operand.*offset"):
        InstructionParser().parse(f"{opcode} x5,{operand}")


@pytest.mark.parametrize("immediate", ["abc", "0x8", "0b10", "1.5", "1_000", "+ 5", "--1"])
@pytest.mark.parametrize("template", ["addi x1,x2,{}", "lw x5,{}(x2)", "sw x6,{}(x3)"])
def test_invalid_immediate(immediate, template):
    with pytest.raises(ValueError, match="Invalid immediate.*signed decimal"):
        InstructionParser().parse(template.format(immediate))


@pytest.mark.parametrize("text", ["", "   ", "\t\n"])
def test_empty_instruction(text):
    with pytest.raises(ValueError, match="Instruction cannot be empty"):
        InstructionParser().parse(text)


def test_parser_reuse_does_not_retain_fields():
    parser = InstructionParser()
    first = parser.parse("sw x6,12(x3)")
    second = parser.parse("add x3,x1,x2")
    assert first == Instruction("sw", rs1=3, rs2=6, immediate=12, original_text="sw x6,12(x3)")
    assert second == Instruction("add", rd=3, rs1=1, rs2=2, original_text="add x3,x1,x2")

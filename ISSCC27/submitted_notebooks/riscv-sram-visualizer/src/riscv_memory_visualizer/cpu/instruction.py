from dataclasses import dataclass
from typing import Optional


@dataclass
class Instruction:
    """
    Represents a simplified RISC-V instruction.

    Example:
        lw x5, 8(x2)

    becomes:
        opcode = "lw"
        rd = 5
        rs1 = 2
        rs2 = None
        immediate = 8
    """

    opcode: str

    rd: Optional[int] = None
    rs1: Optional[int] = None
    rs2: Optional[int] = None

    immediate: Optional[int] = None

    original_text: str = ""

    def __str__(self):
        return self.original_text if self.original_text else self.opcode
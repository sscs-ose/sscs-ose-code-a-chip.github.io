import re

from riscv_memory_visualizer.cpu.instruction import Instruction


class InstructionParser:
    """Decode lw, sw, add, sub, and addi without executing them.

    Opcodes and x0-x31 registers are case-insensitive. Immediates are signed
    decimal integers, without an encoding-width restriction. Commas are required.
    Only surrounding whitespace is removed from the stored original text.
    """

    def parse(self, instruction_text: str) -> Instruction:
        """Convert one assembly instruction to fields, or raise ValueError."""
        instruction_text = instruction_text.strip()

        if not instruction_text:
            raise ValueError("Instruction cannot be empty")

        parts = instruction_text.split(maxsplit=1)

        opcode = parts[0].lower()
        formats = {
            "lw": "lw rd, offset(rs1)",
            "sw": "sw rs2, offset(rs1)",
            "add": "add rd, rs1, rs2",
            "sub": "sub rd, rs1, rs2",
            "addi": "addi rd, rs1, immediate",
        }
        if opcode not in formats:
            raise ValueError(
                f"Unsupported opcode '{parts[0]}'. Supported: lw, sw, add, sub, addi."
            )

        operands = [part.strip() for part in parts[1].split(",")] if len(parts) > 1 else []
        expected_count = 2 if opcode in ("lw", "sw") else 3
        if len(operands) != expected_count or not all(operands):
            raise ValueError(
                f"Invalid {opcode} syntax. Expected: {formats[opcode]} "
                f"({expected_count} non-empty, comma-separated operands)."
            )

        instruction = Instruction(opcode=opcode, original_text=instruction_text)
        first_register = self._parse_register(operands[0])
        if opcode in ("lw", "sw"):
            instruction.immediate, instruction.rs1 = self._parse_memory_operand(operands[1])
            if opcode == "lw":
                instruction.rd = first_register
            else:
                instruction.rs2 = first_register
        else:
            instruction.rd = first_register
            instruction.rs1 = self._parse_register(operands[1])
            if opcode == "addi":
                instruction.immediate = self._parse_immediate(operands[2])
            else:
                instruction.rs2 = self._parse_register(operands[2])
        return instruction

    def _parse_register(self, text: str) -> int:
        """Validate an x0-x31 register name and return its index."""
        if not re.fullmatch(r"[xX](?:[0-9]|[12][0-9]|3[01])", text):
            raise ValueError(
                f"Invalid register '{text}'. RISC-V integer registers must be x0 through x31."
            )
        return int(text[1:])

    def _parse_immediate(self, text: str) -> int:
        """Accept a decimal integer with an optional leading plus or minus."""
        if not re.fullmatch(r"[+-]?[0-9]+", text):
            raise ValueError(
                f"Invalid immediate '{text}'. Expected a signed decimal integer, such as -8 or +5."
            )
        return int(text)

    def _parse_memory_operand(self, text: str) -> tuple[int, int]:
        """Return (offset, base register) from an offset(rs1) operand."""
        match = re.fullmatch(r"([^()]+)\(\s*([^()]+?)\s*\)", text)
        if match is None:
            raise ValueError(
                f"Invalid memory operand '{text}'. Expected offset(rs1), such as 8(x2)."
            )
        offset = self._parse_immediate(match.group(1).strip())
        register = self._parse_register(match.group(2).strip())
        return offset, register

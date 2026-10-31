"""Behavioral CPU with IF, ID/EX, and MEM/WB stage latches."""

from collections.abc import Iterable
from dataclasses import fields, replace

from riscv_memory_visualizer.cpu.instruction import Instruction
from riscv_memory_visualizer.cpu.pipeline import Pipeline, PipelineStage
from riscv_memory_visualizer.cpu.registers import RegisterFile
from riscv_memory_visualizer.memory.data_memory import DataMemory, MemoryInterface
from riscv_memory_visualizer.simulation.state import SimulationState


class Processor:
    """Run parsed instructions with observable stage occupancy after each step.

    Each step retires the old MEM/WB instruction, reads operands and executes
    the old ID/EX instruction into MEM/WB, moves IF into ID/EX, then fetches.
    One instruction therefore takes four steps from an empty pipeline to
    retirement. N instructions drain in N+3 steps. Writeback precedes register
    reads in a step, so a following instruction sees the preceding result.
    This is an educational timing choice, not forwarding or hazard detection.

    Arithmetic uses Python integers without RV32 overflow/truncation. Reset
    clears CPU state and registers, retaining the program and external memory.
    """

    def __init__(self, memory: MemoryInterface | None = None) -> None:
        self.registers = RegisterFile()
        self.memory = memory if memory is not None else DataMemory()
        self.pipeline = Pipeline()
        self.state = SimulationState()
        self.instruction_memory: tuple[Instruction, ...] = ()

    @property
    def pc(self) -> int:
        """Byte address of the next fetch; stored only in SimulationState."""
        return self.state.pc

    @property
    def finished(self) -> bool:
        """Whether fetching has ended and every stage has drained."""
        return self.pc // 4 >= len(self.instruction_memory) and self.pipeline.empty

    def load_program(self, program: Iterable[Instruction]) -> None:
        """Validate/copy a program and reset the CPU, preserving data memory.

        Initialize registers after loading. Invalid programs leave the current
        CPU untouched. Instruction objects are copied to isolate caller edits.
        """
        instructions = []
        for instruction in program:
            self._validate_instruction(instruction)
            instructions.append(replace(instruction))
        self.instruction_memory = tuple(instructions)
        self.reset()

    def reset(self) -> None:
        """Restart the loaded program with zero registers and an empty pipeline."""
        self.registers.reset()
        self.pipeline.reset()
        initial_state = SimulationState()
        for item in fields(initial_state):
            setattr(self.state, item.name, getattr(initial_state, item.name))

    def get_state(self) -> SimulationState:
        """Return a detached state snapshot; inspect stages via pipeline.snapshot()."""
        return replace(self.state)

    def step(self) -> SimulationState:
        """Advance one cycle; stepping an empty or drained CPU is a no-op.

        State instruction_text/operation/effective_address describe the
        instruction retired this cycle. Stage results remain inspectable in
        pipeline.mem_wb_stage before retirement. SRAM signals are untouched.
        """
        if self.finished:
            return self.get_state()

        self.state.instruction_text = ""
        self.state.operation = None
        self.state.effective_address = None
        self._writeback(self.pipeline.mem_wb_stage)
        next_mem_wb = self._execute(self.pipeline.id_ex_stage)
        next_id_ex = replace(self.pipeline.if_stage, name="ID/EX")
        next_if = PipelineStage("IF")
        if self.pc // 4 < len(self.instruction_memory):
            next_if = PipelineStage("IF", self.instruction_memory[self.pc // 4], self.pc)
            self.state.pc += 4

        self.pipeline.mem_wb_stage = next_mem_wb
        self.pipeline.id_ex_stage = next_id_ex
        self.pipeline.if_stage = next_if
        self.state.cpu_cycle += 1
        self.state.phase = "IDLE" if self.finished else "RUNNING"
        self.state.explanation = (
            "Program complete; pipeline empty." if self.finished
            else "Pipeline advanced one cycle."
        )
        return self.get_state()

    def _execute(self, stage: PipelineStage) -> PipelineStage:
        """Read ID/EX operands and latch the result for later memory/writeback."""
        instruction = stage.instruction
        if instruction is None:
            return PipelineStage("MEM/WB")
        base = self.registers.read(instruction.rs1)
        if instruction.opcode in ("lw", "sw"):
            return PipelineStage(
                "MEM/WB", instruction, stage.pc,
                effective_address=base + instruction.immediate,
                store_data=(self.registers.read(instruction.rs2)
                            if instruction.opcode == "sw" else None),
            )
        operand = (instruction.immediate if instruction.opcode == "addi"
                   else self.registers.read(instruction.rs2))
        result = base - operand if instruction.opcode == "sub" else base + operand
        return PipelineStage("MEM/WB", instruction, stage.pc, result=result)

    def _writeback(self, stage: PipelineStage) -> None:
        """Retire an instruction once, accessing memory only in MEM/WB."""
        instruction = stage.instruction
        if instruction is None:
            return
        self.state.instruction_text = str(instruction)
        self.state.effective_address = stage.effective_address
        if instruction.opcode == "sw":
            self.memory.write(stage.effective_address, stage.store_data)
            self.state.operation = "WRITE"
        else:
            value = stage.result
            if instruction.opcode == "lw":
                value = self.memory.read(stage.effective_address)
                self.state.operation = "READ"
            self.registers.write(instruction.rd, value)

    @staticmethod
    def _validate_instruction(instruction: Instruction) -> None:
        """Reject malformed manually constructed instructions before execution."""
        if not isinstance(instruction, Instruction):
            raise ValueError("Programs must contain parsed Instruction objects.")
        required = {
            "lw": ("rd", "rs1", "immediate"),
            "sw": ("rs1", "rs2", "immediate"),
            "add": ("rd", "rs1", "rs2"),
            "sub": ("rd", "rs1", "rs2"),
            "addi": ("rd", "rs1", "immediate"),
        }
        if instruction.opcode not in required:
            raise ValueError(f"Unsupported opcode '{instruction.opcode}'.")
        for name in ("rd", "rs1", "rs2", "immediate"):
            value = getattr(instruction, name)
            if name in required[instruction.opcode]:
                if type(value) is not int:
                    raise ValueError(f"{instruction.opcode} requires an integer {name}.")
                if name != "immediate" and not 0 <= value <= 31:
                    raise ValueError(f"Invalid {name}: registers must be x0 through x31.")
            elif value is not None:
                raise ValueError(f"{instruction.opcode} does not use {name}.")

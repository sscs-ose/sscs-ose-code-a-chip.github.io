"""Inspectable stage latches for the educational three-stage processor."""

from dataclasses import dataclass, field

from riscv_memory_visualizer.cpu.instruction import Instruction


@dataclass(frozen=True)
class PipelineStage:
    """A stage's instruction, fetch address, and latched execution results."""

    name: str
    instruction: Instruction | None = None
    pc: int | None = None
    result: int | None = None
    effective_address: int | None = None
    store_data: int | None = None


@dataclass
class Pipeline:
    """Three stage latches; the processor controls their advancement."""

    if_stage: PipelineStage = field(default_factory=lambda: PipelineStage("IF"))
    id_ex_stage: PipelineStage = field(default_factory=lambda: PipelineStage("ID/EX"))
    mem_wb_stage: PipelineStage = field(default_factory=lambda: PipelineStage("MEM/WB"))

    def snapshot(self) -> dict[str, str | None]:
        """Return a detached mapping of stage names to instruction text."""
        return {
            stage.name: str(stage.instruction) if stage.instruction is not None else None
            for stage in (self.if_stage, self.id_ex_stage, self.mem_wb_stage)
        }

    @property
    def empty(self) -> bool:
        """Whether every stage is empty."""
        return all(value is None for value in self.snapshot().values())

    def reset(self) -> None:
        """Flush all instructions and execution results."""
        self.if_stage = PipelineStage("IF")
        self.id_ex_stage = PipelineStage("ID/EX")
        self.mem_wb_stage = PipelineStage("MEM/WB")

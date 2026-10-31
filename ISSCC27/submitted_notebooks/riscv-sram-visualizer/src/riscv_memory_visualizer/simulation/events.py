"""Immutable records for logical memory operations."""

from dataclasses import dataclass
from enum import Enum, auto

from riscv_memory_visualizer.memory.base_cell import CellState


class MemoryEventType(Enum):
    """Explicit trace vocabulary; WRITEBACK is reserved for CPU integration."""

    INSTRUCTION = auto()
    MEMORY_REQUEST = auto()
    ADDRESS_DECODE = auto()
    ROW_SELECT = auto()
    COLUMN_SELECT = auto()
    WORD_LINE_ACTIVE = auto()
    SRAM_READ = auto()
    SRAM_WRITE = auto()
    MEMORY_RESPONSE = auto()
    WRITEBACK = auto()
    OPERATION_COMPLETE = auto()
    CELL_SELECTED = auto()  # Logical selection without claiming a physical WL.


@dataclass(frozen=True)
class MemoryEvent:
    """One observation; cycle is caller context (None means unknown).

    Timeline insertion order defines event order, independently of cycle.
    cell_state captures actual signals when available, never a live cell.
    """

    event_type: MemoryEventType
    cycle: int | None = None
    address: int | None = None
    row: int | None = None
    column: int | None = None
    value: int | None = None
    description: str = ""
    instruction: str | None = None
    cell_state: CellState | None = None

    def __post_init__(self) -> None:
        """Require an explicit type, explanation, and valid optional cycle."""
        if not isinstance(self.event_type, MemoryEventType):
            raise ValueError("event_type must be a MemoryEventType.")
        if self.cycle is not None and (type(self.cycle) is not int or self.cycle < 0):
            raise ValueError("cycle must be a non-negative integer or None.")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("description must be non-empty text.")

"""Coordinate real memory accesses and record their logical milestones."""

from riscv_memory_visualizer.memory.array import SRAMArray
from riscv_memory_visualizer.memory.data_memory import MemoryInterface
from riscv_memory_visualizer.memory.base_cell import CellState
from riscv_memory_visualizer.simulation.events import MemoryEvent, MemoryEventType
from riscv_memory_visualizer.simulation.timeline import EventTimeline


class MemoryEventEngine:
    """Trace SRAMArray or an existing MemoryInterface backend.

    Addresses are non-negative byte addresses aligned to word_size (default
    4). For SRAM: index=address//word_size, (row,column)=divmod(index,columns).
    Each cell is a *one-bit placeholder* for a word-addressed location, not
    a 32-bit storage word. A 4x4 array accepts 0,4,...,60 and values 0/1 only.

    For behavioral memory, capacity_words is required and integer values are
    passed through. Only request/response/completion events are emitted;
    there is no invented row, column, or SRAM activity for that backend.

    read returns data and write returns None, matching MemoryInterface.
    Events accumulate in timeline. Optional cycle/instruction are caller
    context, not execution or event counters. No WRITEBACK is fabricated.
    SRAM selection remains active after access, preserving Phase 5 behavior.
    Invalid inputs change neither hardware nor history. Backend exceptions
    propagate, retaining the observed prefix without a completion event.
    """

    def __init__(
        self, memory: SRAMArray | MemoryInterface, *, word_size: int = 4,
        capacity_words: int | None = None, timeline: EventTimeline | None = None,
    ) -> None:
        if type(word_size) is not int or word_size <= 0:
            raise ValueError("word_size must be a positive integer.")
        if isinstance(memory, SRAMArray):
            if capacity_words is not None:
                raise ValueError("SRAM capacity is determined by its array dimensions.")
            capacity_words = memory.rows * memory.columns
        if type(capacity_words) is not int or capacity_words <= 0:
            raise ValueError("capacity_words must be a positive integer for behavioral memory.")
        self.memory = memory
        self.word_size = word_size
        self.capacity_words = capacity_words
        self.timeline = timeline if timeline is not None else EventTimeline()

    def read(self, address: int, *, cycle: int | None = None,
             instruction: str | None = None) -> int:
        """Perform one read and append its observations to the timeline."""
        return self._access(address, None, cycle, instruction)

    def write(self, address: int, value: int, *, cycle: int | None = None,
              instruction: str | None = None) -> None:
        """Perform one write, recording success only after the actual write."""
        if type(value) is not int:
            raise ValueError("write value must be an integer.")
        if isinstance(self.memory, SRAMArray) and value not in (0, 1):
            raise ValueError("SRAM write value must be integer 0 or 1.")
        self._access(address, value, cycle, instruction)

    def _access(self, address: int, value: int | None, cycle: int | None,
                instruction: str | None) -> int:
        """Validate first, then record milestones as backend actions occur."""
        if type(address) is not int or address < 0:
            raise ValueError("address must be a non-negative integer.")
        if address % self.word_size:
            raise ValueError(f"address must be aligned to {self.word_size} bytes.")
        if address // self.word_size >= self.capacity_words:
            raise ValueError("address is outside the configured memory capacity.")
        if cycle is not None and (type(cycle) is not int or cycle < 0):
            raise ValueError("cycle must be a non-negative integer or None.")
        if instruction is not None and (not isinstance(instruction, str) or not instruction.strip()):
            raise ValueError("instruction must be non-empty text or None.")
        row = column = None
        writing = value is not None
        operation = "Write" if writing else "Read"

        def emit(kind: MemoryEventType, description: str,
                 data: int | None = None, state: CellState | None = None) -> None:
            self.timeline.add(MemoryEvent(
                kind, cycle, address, row, column, data, description, instruction, state
            ))

        if instruction is not None:
            emit(MemoryEventType.INSTRUCTION, f"Instruction context: {instruction}")
        emit(MemoryEventType.MEMORY_REQUEST, f"{operation} request for address {address:#x}", value)
        if isinstance(self.memory, SRAMArray):
            row, column = divmod(address // self.word_size, self.memory.columns)
            emit(MemoryEventType.ADDRESS_DECODE,
                 f"Address {address:#x} decoded to row {row}, column {column}")
            self.memory.select_row(row)
            row_description = (f"WL{row} active" if self.memory.uses_word_line
                               else "logical row selection active; physical controls unspecified")
            emit(MemoryEventType.ROW_SELECT, f"Row {row} selected; {row_description}")
            self.memory.select_column(column)
            emit(MemoryEventType.COLUMN_SELECT, f"Column {column} selected")
            emit(MemoryEventType.WORD_LINE_ACTIVE if self.memory.uses_word_line else MemoryEventType.CELL_SELECTED,
                 f"WL{row} active for row {row}" if self.memory.uses_word_line
                 else f"Cell ({row}, {column}) logically selected; physical controls unspecified",
                 state=self.memory.get_cell(row, column).get_state())
            result = (self.memory.write(row, column, value) if writing
                      else self.memory.read(row, column))
            if not result.success:
                raise RuntimeError(f"SRAM access failed: {result.message}")
            data = result.data
            emit(MemoryEventType.SRAM_WRITE if writing else MemoryEventType.SRAM_READ,
                 f"{operation} cell ({row}, {column}): {data}. {result.message}", data, result.state)
        elif writing:
            self.memory.write(address, value)
            data = value
        else:
            data = self.memory.read(address)
        if not writing:
            emit(MemoryEventType.MEMORY_RESPONSE, f"Memory returned data {data}", data)
        emit(MemoryEventType.OPERATION_COMPLETE, f"{operation} operation complete", data)
        return data

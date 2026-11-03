"""Logical array organization with selectable independent cell implementations."""

from dataclasses import dataclass

from riscv_memory_visualizer.memory.decoder import RowDecoder
from riscv_memory_visualizer.memory.base_cell import BaseMemoryCell, SelectableMemoryCell
from riscv_memory_visualizer.memory.sram6t import SRAMAccessResult, SRAMCell6T


@dataclass(frozen=True)
class SRAMArrayState:
    """Immutable array state. word_lines retains the legacy API name.

    For non-6T cells, word_lines contains logical row selection flags, not
    physical word-line signals. Consult the array's uses_word_line property.
    """

    rows: int
    columns: int
    selected_row: int | None
    selected_column: int | None
    word_lines: tuple[int, ...]
    cells: tuple[tuple[int, ...], ...]


class SRAMArray:
    """A rows-by-columns array, defaulting to independent SRAMCell6T instances.

    Row selection activates every cell's WL in that row and deactivates all
    other rows. Column selection is metadata only; read/write accesses just
    the addressed cell. Selection and WL remain active after an operation
    until another row is selected or reset is called. Bit-line state remains
    local to each cell; no shared electrical bit-line behavior is modeled.

    Use array methods for mutation. row_decoder and get_cell expose objects
    for inspection/testing; changing them directly bypasses array selection.
    All input validation occurs before changing selection or cell state.

    For other BaseMemoryCell implementations, q/selected/set_selected provide
    the logical array interface. Selection is software metadata, not a claim
    about the cell's physical word lines. Read/write/reset delegate to cells.
    """

    def __init__(self, rows: int, columns: int, initial_value: int = 0,
                 *, cell_type: type[BaseMemoryCell] = SRAMCell6T) -> None:
        if not isinstance(cell_type, type) or not issubclass(cell_type, BaseMemoryCell):
            raise ValueError("cell_type must be a BaseMemoryCell implementation.")
        self._cell_type = cell_type
        self._row_decoder = RowDecoder(rows)
        if type(columns) is not int or columns <= 0:
            raise ValueError("columns must be a positive integer.")
        self._columns = columns
        self._selected_column: int | None = None
        # Construct every cell separately; the cell validates initial_value.
        self._cells = tuple(
            tuple(cell_type(initial_value) for _ in range(columns))
            for _ in range(rows)
        )
        if not self.uses_word_line and not all(
            isinstance(cell, SelectableMemoryCell) for row in self._cells for cell in row
        ):
            raise ValueError("cell_type must expose q, selected, and set_selected(value).")

    @property
    def cell_type(self) -> type[BaseMemoryCell]:
        """Cell implementation used for every independent storage location."""
        return self._cell_type

    @property
    def architecture_name(self) -> str:
        """Display name of the configured cell model, including abstraction labels."""
        return getattr(self.cell_type, "architecture_name", "6T" if self.uses_word_line else self.cell_type.__name__)

    @property
    def uses_word_line(self) -> bool:
        """Only the existing 6T contract establishes a physical WL here."""
        return issubclass(self.cell_type, SRAMCell6T)

    @property
    def rows(self) -> int:
        """Number of rows."""
        return self._row_decoder.rows

    @property
    def columns(self) -> int:
        """Number of columns."""
        return self._columns

    @property
    def row_decoder(self) -> RowDecoder:
        """Decoder for inspection; use select_row to change array selection."""
        return self._row_decoder

    @property
    def selected_row(self) -> int | None:
        """Selected row, held by the decoder without duplicate storage."""
        return self._row_decoder.selected_row

    @property
    def selected_column(self) -> int | None:
        """Column selected for logical access, or None initially."""
        return self._selected_column

    def get_cell(self, row: int, column: int) -> BaseMemoryCell:
        """Return the live cell for inspection/testing without selecting it.

        Prefer get_state for immutable observations. Calling cell mutation
        methods directly bypasses the array's row/column selection semantics.
        """
        self._validate_location(row, column)
        return self._cells[row][column]

    def select_row(self, row: int) -> None:
        """Drive all cells in one row with WL=1 and all other rows with WL=0."""
        selection = self._row_decoder.decode(row)
        for cells, word_line in zip(self._cells, selection):
            for cell in cells:
                if self.uses_word_line:
                    cell.set_word_line(word_line)
                else:
                    cell.set_selected(word_line)

    def select_column(self, column: int) -> None:
        """Select a column without changing WL, storage, or bit lines."""
        self._validate_index(column, self.columns, "column")
        self._selected_column = column

    def select_cell(self, row: int, column: int) -> None:
        """Select a location, validating both coordinates before any change."""
        self._validate_location(row, column)
        self.select_row(row)
        self.select_column(column)

    def read(self, row: int, column: int) -> SRAMAccessResult:
        """Select and read one cell, preserving storage and leaving WL active."""
        self.select_cell(row, column)
        return self._cells[row][column].read()

    def write(self, row: int, column: int, value: int) -> SRAMAccessResult:
        """Select and write one cell; expose the cell's success and signal state."""
        self._validate_location(row, column)
        if type(value) is not int or value not in (0, 1):
            raise ValueError("write value must be integer 0 or 1.")
        self.select_cell(row, column)
        return self._cells[row][column].write(value)

    def get_state(self) -> SRAMArrayState:
        """Capture selection, actual row WLs, and stored bits without accessing cells."""
        return SRAMArrayState(
            self.rows, self.columns, self.selected_row, self.selected_column,
            tuple(row[0].word_line if self.uses_word_line else row[0].selected for row in self._cells),
            tuple(tuple(cell.q for cell in row) for row in self._cells),
        )

    def reset(self) -> None:
        """Reset existing cells to initial values and clear all selection."""
        for row in self._cells:
            for cell in row:
                cell.reset()
        self._row_decoder.reset()
        self._selected_column = None

    def _validate_location(self, row: int, column: int) -> None:
        """Validate a complete location without altering the array."""
        self._validate_index(row, self.rows, "row")
        self._validate_index(column, self.columns, "column")

    @staticmethod
    def _validate_index(value: int, size: int, name: str) -> None:
        """Reject invalid indices, including booleans and float equivalents."""
        if type(value) is not int or not 0 <= value < size:
            raise ValueError(f"{name} must be an integer from 0 through {size - 1}.")

"""Logical 6T SRAM storage and access; no electrical or timing simulation."""

from dataclasses import dataclass
from typing import Literal

from riscv_memory_visualizer.memory.base_cell import BaseMemoryCell, CellState


@dataclass(frozen=True)
class SRAMCellState:
    """Immutable snapshot of storage nodes and binary access signals."""

    q: int
    q_bar: int
    word_line: int
    bit_line: int
    bit_line_bar: int


@dataclass(frozen=True)
class SRAMAccessResult:
    """An access outcome with its completed state and educational explanation.

    data is the read or successfully written bit, or None for inactive access.
    state is a snapshot at the time of the operation, not a live reference.
    """

    operation: Literal["READ", "WRITE"]
    success: bool
    data: int | None
    state: CellState
    message: str


class SRAMCell6T(BaseMemoryCell):
    """One bit stored by conceptual cross-coupled inverters and WL access.

    Defaults to Q=0, Q_bar=1, WL=0, and prepared BL=BL_bar=1. Q_bar is
    derived from Q, so stored nodes are always complementary. All public
    signal properties are read-only; use set_word_line and write to update.

    Reads and writes require WL=1 and leave WL unchanged. An inactive access
    returns failure without changing any signal. Active read abstracts the
    prepared bit lines and their resolved logical outcome into one operation:
    BL=Q, BL_bar=Q_bar. No precharge transient, voltage swing, sense amplifier,
    current, or read disturbance is simulated. Stored data is unchanged.

    Active write drives BL=value and BL_bar=1-value and updates Q. Lowering
    WL preserves the last bit-line values; reset restores the prepared pair.
    Only exact integer 0 and 1 are accepted, including for the initial value.
    """

    def __init__(self, initial_value: int = 0) -> None:
        self._validate_bit(initial_value, "initial_value")
        self._initial_value = initial_value
        self.reset()

    @property
    def q(self) -> int:
        """Stored logical bit at Q."""
        return self._q

    @property
    def q_bar(self) -> int:
        """Complementary storage node, always NOT Q."""
        return 1 - self._q

    @property
    def word_line(self) -> int:
        """WL: 1 enables access; 0 isolates the storage nodes."""
        return self._word_line

    @property
    def bit_line(self) -> int:
        """BL: the last modeled logical bit-line value."""
        return self._bit_line

    @property
    def bit_line_bar(self) -> int:
        """BL_bar: the complementary access line (also 1 when prepared)."""
        return self._bit_line_bar

    def set_word_line(self, value: int) -> None:
        """Set WL without performing an access or changing the bit lines."""
        self._validate_bit(value, "word_line")
        self._word_line = value

    def get_state(self) -> SRAMCellState:
        """Capture all five logical signals in an immutable snapshot."""
        return SRAMCellState(
            self.q, self.q_bar, self.word_line, self.bit_line, self.bit_line_bar
        )

    def read(self) -> SRAMAccessResult:
        """Resolve the logical read lines when selected, retaining Q/Q_bar."""
        if self.word_line == 0:
            return self._inactive_result("READ")
        self._bit_line = self.q
        self._bit_line_bar = self.q_bar
        return SRAMAccessResult(
            "READ", True, self.q, self.get_state(),
            "WL=1 enables the access transistors. The prepared bit lines "
            "resolve logically to BL=Q and BL_bar=Q_bar; stored data is unchanged.",
        )

    def write(self, value: int) -> SRAMAccessResult:
        """Drive complementary bit lines and store the bit only when WL=1."""
        self._validate_bit(value, "write value")
        if self.word_line == 0:
            return self._inactive_result("WRITE")
        self._bit_line = value
        self._bit_line_bar = 1 - value
        self._q = value
        return SRAMAccessResult(
            "WRITE", True, value, self.get_state(),
            "WL=1 enables the access transistors. Complementary BL/BL_bar "
            "drive the storage nodes to Q=value and Q_bar=1-value.",
        )

    def reset(self) -> None:
        """Restore the constructor's bit, WL=0, and prepared BL=BL_bar=1."""
        self._q = self._initial_value
        self._word_line = 0
        self._bit_line = 1
        self._bit_line_bar = 1

    def _inactive_result(self, operation: Literal["READ", "WRITE"]) -> SRAMAccessResult:
        """Describe a blocked access without changing the cell or its signals."""
        return SRAMAccessResult(
            operation, False, None, self.get_state(),
            "WL=0 isolates the storage nodes from BL/BL_bar. "
            "No access occurred; storage and bit lines are unchanged.",
        )

    @staticmethod
    def _validate_bit(value: int, name: str) -> None:
        """Reject booleans, floats, strings, and integers other than 0 or 1."""
        if type(value) is not int or value not in (0, 1):
            raise ValueError(f"{name} must be integer 0 or 1; got {value!r}.")

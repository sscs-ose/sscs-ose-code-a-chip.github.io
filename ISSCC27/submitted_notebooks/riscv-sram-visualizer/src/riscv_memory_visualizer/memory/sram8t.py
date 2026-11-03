"""Abstract 8T comparison fallback; no transistor topology is specified.

The supplied project contains no 8T connectivity source. Q/Q_bar and a
software selection gate implement a one-bit interface for comparison only.
Selection is NOT a physical word line. Read/write methods do NOT establish
separate physical ports. See docs/sram_architectures.md for the source audit.
"""

from dataclasses import dataclass
from typing import Literal

from riscv_memory_visualizer.memory.base_cell import BaseMemoryCell
from riscv_memory_visualizer.memory.sram6t import SRAMAccessResult


@dataclass(frozen=True)
class SRAMCell8TState:
    """Logical placeholder state; selected is software access metadata."""

    q: int
    q_bar: int
    selected: int


class SRAMCell8T(BaseMemoryCell):
    """Deterministic one-bit placeholder, explicitly not a verified 8T circuit.

    Assumptions: complementary logical storage, selection-gated operations,
    non-destructive read, and reset to the configured initial value. No WL,
    BL, read polarity, transistor roles, supplies or connectivity are modeled.
    """

    architecture_name = "8T (abstract)"

    def __init__(self, initial_value: int = 0) -> None:
        self._validate_bit(initial_value, "initial_value")
        self._initial_value = initial_value
        self.reset()

    @property
    def q(self) -> int:
        """Stored logical bit; no node voltage is modeled."""
        return self._q

    @property
    def q_bar(self) -> int:
        """Logical complement of Q under the abstract storage assumption."""
        return 1 - self._q

    @property
    def selected(self) -> int:
        """Software access gate, not a physical word line."""
        return self._selected

    def set_selected(self, value: int) -> None:
        """Set the software access gate without accessing storage."""
        self._validate_bit(value, "selected")
        self._selected = value

    def get_state(self) -> SRAMCell8TState:
        """Return an immutable snapshot without performing an access."""
        return SRAMCell8TState(self.q, self.q_bar, self.selected)

    def read(self) -> SRAMAccessResult:
        """Return the selected bit unchanged; no read circuitry is inferred."""
        return self._result("READ")

    def write(self, value: int) -> SRAMAccessResult:
        """Validate first, then store only when logically selected."""
        self._validate_bit(value, "write value")
        if self.selected:
            self._q = value
        return self._result("WRITE")

    def _result(self, operation: Literal["READ", "WRITE"]) -> SRAMAccessResult:
        message = ("Logical read returns Q without changing storage." if operation == "READ"
                   else "Logical write stores the supplied bit.") if self.selected else "Not selected; no access occurred."
        return SRAMAccessResult(operation, bool(self.selected), self.q if self.selected else None,
                                self.get_state(), message + " Abstract 8T placeholder; circuitry unspecified.")

    def reset(self) -> None:
        """Restore the initial stored bit and clear software selection."""
        self._q = self._initial_value
        self._selected = 0

    @staticmethod
    def _validate_bit(value: int, name: str) -> None:
        if type(value) is not int or value not in (0, 1):
            raise ValueError(f"{name} must be integer 0 or 1; got {value!r}.")

"""Small common interface for standalone behavioral memory cells."""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable


class CellState(Protocol):
    """Common logical storage observation; no physical signal assumptions."""

    @property
    def q(self) -> int:
        """Stored logical bit."""
        ...

    @property
    def q_bar(self) -> int:
        """Complementary logical storage observation."""
        ...


@runtime_checkable
class SelectableMemoryCell(Protocol):
    """Array selection contract for new cells, independent of physical word lines.

    Implement alongside BaseMemoryCell. The legacy 6T cell is adapted at the
    array boundary so its public controls and behavior remain unchanged.
    """

    @property
    def q(self) -> int:
        """Stored bit exposed to the array."""
        ...

    @property
    def selected(self) -> int:
        """Software selection flag, without physical signal assumptions."""
        ...

    def set_selected(self, value: int) -> None:
        """Set logical selection without accessing storage."""
        ...


class BaseMemoryCell(ABC):
    """Cell operations independent of a particular storage technology.

    Concrete cells define their own access controls, snapshots, and result
    types. This interface does not assume SRAM nodes or transistor topology.
    """

    @abstractmethod
    def read(self) -> object:
        """Attempt a read and report whether access occurred."""

    @abstractmethod
    def write(self, value: int) -> object:
        """Attempt to store a value and report whether access occurred."""

    @abstractmethod
    def get_state(self) -> object:
        """Return a snapshot without exposing mutable internal state."""

    @abstractmethod
    def reset(self) -> None:
        """Restore the configured initial value and inactive controls."""

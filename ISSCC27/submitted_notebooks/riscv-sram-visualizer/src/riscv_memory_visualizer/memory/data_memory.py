"""Behavioral data memory, independent of future SRAM implementations."""

from typing import Protocol


class MemoryInterface(Protocol):
    """The only operations a processor requires from its memory backend."""

    def read(self, address: int) -> int:
        """Read the integer stored at a byte address."""
        ...

    def write(self, address: int, value: int) -> None:
        """Store an integer at a byte address."""
        ...


class DataMemory:
    """Sparse address-to-integer storage; unwritten addresses read as zero.

    Addresses are byte addresses, but values are whole Python integers. This
    placeholder has no byte lanes, width wrapping, alignment checks, or timing.
    """

    def __init__(self) -> None:
        self._values: dict[int, int] = {}

    def read(self, address: int) -> int:
        """Return the stored integer, or zero for an unwritten address."""
        return self._values.get(address, 0)

    def write(self, address: int, value: int) -> None:
        """Store an integer without modeling electrical memory behavior."""
        self._values[address] = value

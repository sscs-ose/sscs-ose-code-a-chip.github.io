"""Attach CPU observation context to the existing memory interface."""

from riscv_memory_visualizer.simulation.controller import MemoryEventEngine
from riscv_memory_visualizer.simulation.state import SimulationState


class ProcessorEventMemory:
    """Delegate real accesses, using the CPU's in-progress retirement context.

    Processor increments cpu_cycle after writeback, so an access belongs to
    cpu_cycle + 1. No data, address mapping, or execution is duplicated here.
    Use the engine directly for initialization without CPU instruction context.
    """

    def __init__(self, engine: MemoryEventEngine, state: SimulationState) -> None:
        self.engine = engine
        self.state = state

    def read(self, address: int) -> int:
        """Return memory data, recording the in-progress retirement cycle."""
        return self.engine.read(address, cycle=self.state.cpu_cycle + 1,
                                instruction=self.state.instruction_text or None)

    def write(self, address: int, value: int) -> None:
        """Delegate a store with the CPU's retirement context; errors propagate."""
        self.engine.write(address, value, cycle=self.state.cpu_cycle + 1,
                          instruction=self.state.instruction_text or None)

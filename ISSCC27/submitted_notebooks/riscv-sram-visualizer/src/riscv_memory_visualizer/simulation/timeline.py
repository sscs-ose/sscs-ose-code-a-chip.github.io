"""Insertion-ordered event history, independent of visualization."""

from riscv_memory_visualizer.simulation.events import MemoryEvent


class EventTimeline:
    """Record events as observed without sorting caller-supplied cycles."""

    def __init__(self) -> None:
        self._events: list[MemoryEvent] = []

    def add(self, event: MemoryEvent) -> None:
        """Append one immutable event to the history."""
        if not isinstance(event, MemoryEvent):
            raise ValueError("timeline entries must be MemoryEvent objects.")
        self._events.append(event)

    def events(self) -> tuple[MemoryEvent, ...]:
        """Return a detached immutable sequence in insertion order."""
        return tuple(self._events)

    def snapshot(self) -> tuple[MemoryEvent, ...]:
        """Capture the current event history."""
        return self.events()

    def get_cycle(self, cycle: int | None) -> tuple[MemoryEvent, ...]:
        """Filter by supplied cycle; None selects events with unknown cycle."""
        return tuple(event for event in self._events if event.cycle == cycle)

    def clear(self) -> None:
        """Discard event history without resetting hardware."""
        self._events.clear()

    def __len__(self) -> int:
        """Number of recorded events."""
        return len(self._events)

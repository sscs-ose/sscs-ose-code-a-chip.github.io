"""Logical observations with separate CPU-cycle and event-order domains.

This module never executes a processor, selects a cell or accesses memory.
Unknown observations are None; unavailable signals are explicitly flagged.
"""

from dataclasses import dataclass
from typing import Literal

from riscv_memory_visualizer.memory.array import SRAMArray
from riscv_memory_visualizer.memory.sram6t import SRAMCellState
from riscv_memory_visualizer.memory.sram8t import SRAMCell8TState
from riscv_memory_visualizer.simulation.events import MemoryEvent, MemoryEventType as E
from riscv_memory_visualizer.simulation.timeline import EventTimeline

SignalValue = int | str | None


def _cycle(value: int) -> None:
    if type(value) is not int or value < 0:
        raise ValueError("cycle must be a non-negative integer.")


@dataclass(frozen=True)
class SignalSample:
    """One observation; event_order is insertion order, never an extra cycle."""

    cycle: int | None
    value: SignalValue
    event_order: int | None = None

    def __post_init__(self):
        if self.cycle is not None:
            _cycle(self.cycle)
        if self.event_order is not None and (type(self.event_order) is not int or self.event_order < 1):
            raise ValueError("event_order must be a positive integer.")
        if self.cycle is None and self.event_order is None:
            raise ValueError("A sample needs a cycle or an event order.")
        if self.value is not None and type(self.value) not in (int, str):
            raise ValueError("Signal values must be integers, text or None.")


@dataclass(frozen=True)
class SignalSeries:
    """Detached immutable trace for rendering or export."""

    name: str
    kind: str
    domain: str
    available: bool
    samples: tuple[SignalSample, ...]


class SignalTrace:
    """Append-only observations, ordered by cycle or by timeline insertion.

    Cycle-domain samples have strictly increasing cycles. Event-domain samples
    have strictly increasing event_order; their supplied cycles may repeat,
    be unknown, or arrive out of numeric order, exactly as in EventTimeline.
    """

    def __init__(self, name: str, kind: Literal["binary", "integer", "category"] = "binary",
                 *, domain: Literal["cycle", "event"] = "cycle", available: bool = True):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("A signal needs a non-empty name.")
        if kind not in ("binary", "integer", "category") or domain not in ("cycle", "event"):
            raise ValueError("Invalid signal kind or domain.")
        self.name, self.kind, self.domain, self.available = name, kind, domain, available
        self._samples: list[SignalSample] = []

    def append(self, cycle: int | None, value: SignalValue, *, event_order: int | None = None) -> None:
        """Append a validated observation in strictly increasing domain order."""
        sample = SignalSample(cycle, value, event_order)
        if value is not None:
            if not self.available:
                raise ValueError("Unavailable signals cannot have values.")
            if self.kind == "binary" and (type(value) is not int or value not in (0, 1)):
                raise ValueError("Binary values must be integer 0, 1 or None.")
            if self.kind == "integer" and type(value) is not int:
                raise ValueError("Integer signals require integer values.")
            if self.kind == "category" and type(value) is not str:
                raise ValueError("Categorical signals require text values.")
        if self.domain == "cycle":
            if cycle is None or event_order is not None:
                raise ValueError("Cycle traces require a cycle and no event order.")
            key = cycle
            previous = self._samples[-1].cycle if self._samples else -1
        else:
            if event_order is None:
                raise ValueError("Event traces require event_order.")
            key = event_order
            previous = self._samples[-1].event_order if self._samples else 0
        if key <= previous:
            raise ValueError("Samples must be appended in strictly increasing domain order.")
        self._samples.append(sample)

    def value_at(self, cycle: int) -> SignalValue:
        """Last observed value at/before a cycle; unknown before the first sample."""
        _cycle(cycle)
        if self.domain != "cycle":
            raise ValueError("Use event_order to inspect event traces; cycles are not unique.")
        return next((s.value for s in reversed(self._samples) if s.cycle <= cycle), None)

    def snapshot(self) -> tuple[SignalSample, ...]:
        """Return an immutable sequence detached from subsequent appends."""
        return tuple(self._samples)

    def filter_cycles(self, start: int, end: int) -> tuple[SignalSample, ...]:
        """Return observations in the inclusive cycle range, omitting unknown cycles."""
        _cycle(start)
        _cycle(end)
        if end < start:
            raise ValueError("end must be at least start.")
        return tuple(s for s in self._samples if s.cycle is not None and start <= s.cycle <= end)

    def cycles(self) -> tuple[int | None, ...]:
        """Return supplied cycles in observation order, including unknown context."""
        return tuple(s.cycle for s in self._samples)

    def values(self) -> tuple[SignalValue, ...]:
        """Return recorded values without exposing the internal sample list."""
        return tuple(s.value for s in self._samples)

    def series(self) -> SignalSeries:
        """Export immutable metadata and samples for rendering."""
        return SignalSeries(self.name, self.kind, self.domain, self.available, self.snapshot())


@dataclass(frozen=True)
class OrderedMemoryEvent:
    """An original event paired with its one-based timeline insertion order."""
    order: int
    event: MemoryEvent


@dataclass(frozen=True)
class SimulationTrace:
    """Detached cycle/event observations and their original immutable events."""
    architecture: str
    current_cycle: int
    cycle_traces: tuple[SignalSeries, ...]
    event_traces: tuple[SignalSeries, ...]
    events: tuple[OrderedMemoryEvent, ...]


MEMORY_SIGNALS = {
    "WL": "binary", "BL": "binary", "BL_bar": "binary", "Q": "binary", "Q_bar": "binary",
    "SELECTED": "binary", "READ": "binary", "WRITE": "binary", "MEMORY_ACCESS": "binary",
    "ROW_SELECT": "integer", "COLUMN_SELECT": "integer", "CELL": "category",
}
CPU_SIGNALS = {"IF": "category", "ID_EX": "category", "MEM_WB": "category", "PC": "integer", "CYCLE": "integer"}


def _cell_values(state) -> dict[str, SignalValue]:
    """Copy actual snapshot fields; never derive complementary storage/signals."""
    values = dict.fromkeys(("WL", "BL", "BL_bar", "Q", "Q_bar", "SELECTED"))
    if state is not None:
        values.update(Q=state.q, Q_bar=state.q_bar)
    if isinstance(state, SRAMCellState):
        values.update(WL=state.word_line, BL=state.bit_line, BL_bar=state.bit_line_bar)
    elif isinstance(state, SRAMCell8TState):
        values["SELECTED"] = state.selected
    return values


class SimulationTraceRecorder:
    """Observe cycle boundaries and immutable events from an existing timeline.

    Cycle traces show the selected cell (or an explicitly supplied fixed cell)
    at each observation; ROW/COLUMN identify its scope. Event traces show the
    accessed cell. Last observed cell signals are held only within an operation
    after a real snapshot; a new request clears them to unknown. READ/WRITE are
    occurrence markers, not modeled control voltages or durations.

    Explicitly clear after resetting/replacing a timeline or changing memory
    architecture. History grows with observations; rendering may window it.
    """

    def __init__(self, timeline: EventTimeline, *, architecture: str = "6T", physical_signals: bool = True):
        self.timeline = timeline
        self.clear(architecture=architecture, physical_signals=physical_signals)

    def clear(self, *, architecture: str | None = None, physical_signals: bool | None = None) -> None:
        """Discard observations, optionally changing the model's signal availability."""
        if architecture is not None:
            self.architecture = architecture
        if physical_signals is not None:
            self.physical_signals = physical_signals
        def make(spec, domain):
            return {name: SignalTrace(name, kind, domain=domain,
                                     available=(self.physical_signals if name in ("WL", "BL", "BL_bar")
                                                else not self.physical_signals if name == "SELECTED" else True))
                    for name, kind in spec.items()}
        self.cycle_traces = make(MEMORY_SIGNALS | CPU_SIGNALS, "cycle")
        self.event_traces = make(MEMORY_SIGNALS, "event")
        self.current_cycle = 0
        self._last_cycle = None
        self._event_count = 0
        self._last_event = None
        self._event_values = dict.fromkeys(MEMORY_SIGNALS)

    def record_events(self) -> None:
        """Consume new timeline records once; never assign cycles to setup events."""
        events = self.timeline.events()
        if len(events) < self._event_count or (self._event_count and events[self._event_count-1] is not self._last_event):
            raise ValueError("Timeline was reset/replaced; clear the recorder before recording.")
        for index in range(self._event_count, len(events)):
            event = events[index]
            values = self._event_values
            if event.event_type in (E.INSTRUCTION, E.MEMORY_REQUEST):
                values = dict.fromkeys(MEMORY_SIGNALS)
            if event.event_type == E.ROW_SELECT:
                values["ROW_SELECT"] = event.row
            if event.event_type == E.COLUMN_SELECT:
                values["COLUMN_SELECT"] = event.column
            if event.cell_state is not None:
                values.update(_cell_values(event.cell_state))
                values["CELL"] = f"({event.row}, {event.column})"
            values["READ"] = int(event.event_type == E.SRAM_READ)
            values["WRITE"] = int(event.event_type == E.SRAM_WRITE)
            values["MEMORY_ACCESS"] = int(event.event_type in (E.SRAM_READ, E.SRAM_WRITE))
            for name, trace in self.event_traces.items():
                trace.append(event.cycle, values[name] if trace.available else None, event_order=index + 1)
            self._event_values = values
            self._event_count = index + 1
            self._last_event = event

    def record_cycle(self, cycle: int, array: SRAMArray, *, processor=None,
                     cell: tuple[int, int] | None = None) -> None:
        """Capture one boundary. Repeated recording of the same cycle is a no-op.

        A fixed cell is useful for standalone before/after demonstrations. It
        is inspected with get_cell/get_state, never selected on the array.
        Otherwise unknown cell signals stay unknown until a cell is selected.
        """
        _cycle(cycle)
        if array.uses_word_line != self.physical_signals or array.architecture_name != self.architecture:
            raise ValueError("Architecture changed; clear the recorder with the new configuration.")
        if processor is not None and processor.state.cpu_cycle != cycle:
            raise ValueError("Supplied cycle does not match the processor.")
        if self._last_cycle is not None and cycle < self._last_cycle:
            raise ValueError("CPU cycle moved backwards; clear the recorder after reset.")
        row, column = cell if cell is not None else (array.selected_row, array.selected_column)
        state = array.get_cell(row, column).get_state() if row is not None and column is not None else None
        self.record_events()
        if cycle == self._last_cycle:
            return
        values = _cell_values(state)
        values["CELL"] = f"({row}, {column})" if state is not None else None
        values.update(ROW_SELECT=array.selected_row, COLUMN_SELECT=array.selected_column)
        events = self.timeline.get_cycle(cycle)
        values.update(READ=int(any(e.event_type == E.SRAM_READ for e in events)),
                      WRITE=int(any(e.event_type == E.SRAM_WRITE for e in events)))
        values["MEMORY_ACCESS"] = int(bool(values["READ"] or values["WRITE"]))
        values.update(dict.fromkeys(CPU_SIGNALS))
        values["CYCLE"] = cycle
        if processor is not None:
            stages = processor.pipeline.snapshot()
            values.update(IF=stages["IF"] or "EMPTY", ID_EX=stages["ID/EX"] or "EMPTY",
                          MEM_WB=stages["MEM/WB"] or "EMPTY", PC=processor.pc)
        for name, trace in self.cycle_traces.items():
            trace.append(cycle, values[name] if trace.available else None)
        self._last_cycle = self.current_cycle = cycle

    def snapshot(self) -> SimulationTrace:
        """Return detached observations and references to original immutable events."""
        events = self.timeline.events()
        if len(events) < self._event_count or (self._event_count and events[self._event_count-1] is not self._last_event):
            raise ValueError("Timeline was reset/replaced; clear the recorder before taking a snapshot.")
        return SimulationTrace(self.architecture, self.current_cycle,
                               tuple(t.series() for t in self.cycle_traces.values()),
                               tuple(t.series() for t in self.event_traces.values()),
                               tuple(OrderedMemoryEvent(i+1, e) for i, e in
                                     enumerate(events[:self._event_count])))

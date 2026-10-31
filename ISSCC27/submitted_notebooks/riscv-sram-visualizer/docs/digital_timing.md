# Digital timing and trace semantics

This waveform represents logical simulation state and event timing. It is
not an analog SPICE waveform. No voltages, currents, capacitances, physical
delays, precharge ramps or sense-amplifier timing are generated.

## Two distinct time domains

The upper panel uses **CPU cycles**. The application captures a baseline before
the first step and then one observation after every successful processor step.
IF, ID_EX and MEM_WB contain the actual pipeline snapshot text (EMPTY is an
observed empty stage); PC and CYCLE come from the processor. Rendering never
executes instructions, reads memory or changes selection.

The lower panel uses **event insertion order within a selected cycle**, with
the CPU cycle in its heading. Multiple events at cycle 4 remain at cycle 4;
they never become cycles 5, 6, etc. Event spacing has no duration meaning.
Setup events retain `cycle=None` and are labeled "Setup / unknown CPU cycle".
Events preserve the original MemoryEvent objects, metadata and order. Events
with out-of-order cycle context are not sorted or renumbered.

The lower panel defaults to the latest memory cycle in the visible range, or
setup events if there is no such cycle. With event-only traces it uses the last
known event cycle. It shows at most 12 events; its heading reports how many
are shown, and the existing timeline retains the complete event history.

## Observations, unknown values and scope

6T traces copy actual **WL, BL, BL_bar, Q and Q_bar** fields. Abstract 8T traces
copy **Q, Q_bar and software SELECTED** only; WL/BL/BL_bar show **N/A**. The
6T model has no separate SELECTED field, so that lane is N/A for 6T. No new
8T circuitry or physical control signals are implied. See the existing
[source audit](sram_architectures.md).

The application follows the currently selected cell. **CELL** identifies it,
while ROW_SELECT/COLUMN_SELECT show array selection. A change in displayed Q
can result from selecting a different cell; it need not indicate a write to
the previous cell. With no selected cell, its state is unknown (`?`), not zero.
Standalone recording can inspect a fixed cell before selection, without
activating its word line. ROW_SELECT/COLUMN_SELECT still report array selection.

Event traces copy cell snapshots only when present. A new request invalidates
the previous cell observations; subsequent values remain unknown until a real
snapshot arrives. Within that operation, the latest observed signals are held.
ADDRESS_DECODE gives a target but does not itself assert row/column selection;
those lanes update on the actual ROW_SELECT/COLUMN_SELECT events. Thus a write's
WORD_LINE_ACTIVE snapshot can show old Q, followed by the SRAM_WRITE snapshot's
new Q, both in the same CPU cycle.

READ/WRITE/MEMORY_ACCESS are **occurrence indicators**, not physical controls.
At a cycle boundary they indicate whether SRAM_READ/SRAM_WRITE occurred in
that cycle. In event detail they mark the corresponding event. They do not
claim a modeled access duration or invent idle cycles after completion.

Step segments hold recorded observations for presentation. Unavailable values
are N/A; unobserved values are None/`?`. Category/integer lanes show values or
instruction text, not analog amplitudes. Text may be abbreviated in the plot;
the snapshots retain complete strings.

## Reusable API

`SignalSample` is immutable. `SignalTrace` validates binary, integer and
categorical data. It offers append, value_at (cycle-domain only), filter_cycles,
cycles, values, immutable sample snapshots and immutable `SignalSeries` export.
Cycle samples are strictly increasing. Event samples are ordered by their
explicit insertion number; cycles may repeat or be unknown.

`SimulationTraceRecorder(timeline)` observes the existing EventTimeline. Call
`record_events()` for an event-only diagram, or
`record_cycle(cycle, array, processor=cpu)` after a step. For an abstract array,
pass `architecture=array.architecture_name, physical_signals=False` when
constructing or clearing the recorder. Pass `cell=(row, column)` to record a
fixed cell. Repeating the current cycle is a no-op for boundary observations;
new events are still consumed. Call after all intended activity for that cycle.

`snapshot()` returns a detached `SimulationTrace`. The view consumes this
snapshot, never the simulation. For example:

```python
view.update(recorder.snapshot(), start_cycle=0, end_cycle=6, event_cycle=4)
```

`event_cycle=None` selects setup events explicitly. The default view shows the
latest 12 CPU cycles and a bounded event detail panel. Figures, lines and text
pools are reused. Full history grows with recorded cycles/events and remains
available for inspection; no automatic history pruning is implemented.

## Application lifecycle

Step/Run extend history; Pause and refresh preserve it. Demo-data writes record
setup events without assigning a CPU cycle. Load, Reset and architecture
switching clear traces, annotations and the current cycle. The figure remains
the same object. Invalid program input preserves the old history. Stepping a
drained CPU adds no samples. If a caller resets the timeline or changes array
architecture outside the app, explicitly clear the recorder too; stale histories
are rejected rather than silently joined.

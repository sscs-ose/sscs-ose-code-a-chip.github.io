# SRAM architecture scope and source audit

## Material inspected

Phase 11's supplied implementation brief, the repository README, all sections
of `notebooks/00_launch_visualizer.ipynb`, the existing cell/array/decoder
models, event engine, views, application and tests were inspected. No lecture
PDF, slides, external source link, transistor netlist or 8T schematic was found
in the project. The Phase 7 notebook explicitly records that its lecture PDF
was not locally available. The pre-Phase-11 `sram8t.py` was empty.

**Source material does not specify enough 8T transistor connectivity to
implement a source-faithful 8T schematic.**

No unrelated topology from the web or general knowledge has been substituted.
This phase implements the brief's explicitly allowed **abstract placeholder**
fallback. A detailed circuit comparison remains pending the missing source.

## What is established, and what is assumed

| Item | Available project evidence | Phase 11 treatment |
| --- | --- | --- |
| 6T | Existing model and conceptual view: six devices, complementary Q/Q_bar, cross-coupled inverters, WL-gated BL/BL_bar access | Existing behavior preserved; the drawing is a project model, not a newly verified lecture schematic |
| 8T count | The supplied brief calls for eight devices | Count shown as a fact from the brief, without device symbols or assigned roles |
| 8T storage | Brief requests logical Q/Q_bar | Complementary one-bit storage implemented as an explicit software assumption |
| 8T device roles/connectivity | Not specified | No transistor wiring, PMOS/NMOS assignments, supplies or device numbering drawn |
| 8T read/write organization | Brief makes separate paths conditional on verified topology | No physical port separation, read polarity, WL or BL names assumed |
| 8T access | No physical controls established | `selected` is software metadata; selection gates both logical methods |
| Read/write/reset behavior | Required deterministic behavior, no circuit specified | Read preserves Q; write replaces Q; reset restores the initial bit and clears selection |

The abstract block diagram is deliberately **not an 8T transistor schematic**.
It cannot teach a specific eight-device read/write organization without the
missing connectivity source. The comparison marks physical paths as unknown
and makes no claims about area, speed, power, stability or read-disturb immunity.
Neither model performs analog, current, voltage or SPICE simulation. Phase 12
adds observation-based digital timing diagrams without changing this scope.

## Integration and extension

`SRAMArray(rows, columns, initial_value=0, cell_type=SRAMCell6T)` preserves
the default and existing positional arguments. Use `cell_type=SRAMCell8T`
for the abstract model. Each location gets an independent cell. The existing
6T class's execution logic is unchanged; only the shared access result's state
annotation was widened to a small structural `CellState` protocol.

New cell classes implement `BaseMemoryCell` plus `q`, `selected` and
`set_selected(value)`, as described by `SelectableMemoryCell`. The array adapts
the legacy 6T `word_line`/`set_word_line` controls at its boundary. This keeps
future cell types out of the CPU and memory adapter. The shared
`SRAMAccessResult` remains importable from `sram6t`; both snapshots are frozen.

The legacy array snapshot field `word_lines` is retained for compatibility:
for 6T it contains actual modeled WL values; for the abstract model it contains
software row-selection flags. `array.uses_word_line` distinguishes these cases.
The view labels abstract rows `SEL`, never `WL`, and identifies the architecture.

MemoryEventEngine still owns address mapping and access events. The 6T event
sequence is unchanged. New `CELL_SELECTED` records abstract selection where
claiming `WORD_LINE_ACTIVE` would imply unsupported physical controls; no
8T-specific physical read event is invented. Events carry the actual immutable
snapshot type, and the cell views reject snapshots of the wrong architecture.

Switching the application selector pauses Run, resets the same Processor,
retains its loaded program, replaces the array, clears history and register
highlighting, and selects a cached cell view. The same engine, adapter, pipeline
view, array figure and widget tree remain in use. Demo data must be explicitly
loaded again. The comparison view reuses both detailed views in Matplotlib
subfigures and never changes supplied model state.

## What completing a circuit-level 8T view requires

A project source must identify all eight devices, their connections to Q/Q_bar,
supplies and controls, the read and write paths, and relevant signal names and
logical behavior. Until then, the application supports selectable behavioral
memory, not a source-verified physical 8T implementation.

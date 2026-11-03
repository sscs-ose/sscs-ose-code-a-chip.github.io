# Extending and contributing

Install with `python -m pip install -e ".[notebook,test]"`. Run `pytest -q tests` and
`python scripts/validate_notebook.py` before submitting a change. Describe the
behavior changed and the evidence used to validate it. Do not commit environments,
caches, executed notebook output, generated package metadata or temporary images.
Keep the reviewed notebook's saved outputs and cell metadata intact.
For Jupyter Notebook, JupyterLab, or VS Code review, see
[Quick start](../README.md#quick-start).

## Layer contracts

The CPU imports memory protocols, not widgets or views. `ProcessorEventMemory`
adds retirement cycle/instruction context; `MemoryEventEngine` validates accesses
and emits observations of actual work. `SRAMArray` owns cells and selection.
`EventTimeline` preserves insertion order. The recorder copies existing snapshots;
views update display artists only. The UI wires these layers and owns execution.

`SimulationState` still has foundation-era SRAM placeholders for compatibility.
They are not synchronized with SRAM and must not be used as live signals.
Use cell/array snapshots and `SimulationTraceRecorder` instead.

## New instruction

1. Extend `cpu/parser.py` syntax and `Processor._validate_instruction` together.
2. Implement operand/result handling in `_execute` and retirement in `_writeback`.
   Preserve the existing writeback-before-operand-read timing unless changing the
   documented processor model intentionally.
3. Test parsing, invalid forms, stage timing, register/memory effects and x0.
4. Update stage explanations and the supported-instruction table. Views must not
   parse instructions again or implement their own execution semantics.

## New memory cell

1. Implement `BaseMemoryCell` read/write/get_state/reset operations and immutable
   state with q/q_bar. Array integration currently expects access results exposing
   success, data, state and message, compatible with `SRAMAccessResult`.
2. For non-6T cells, implement `SelectableMemoryCell`: q, selected and
   set_selected. Selection is software metadata unless a source defines more.
3. Test validation, inactive access, storage, reset and independent array cells.
4. Add a read-only view. Register the cell and its selector option/cached view in
   `ui/app.py`; update lifecycle tests. `CELL_TYPES` alone does not create UI options.
5. Extend the explicit snapshot mapping in `simulation/signals.py` for a genuinely
   new state type. The current recorder recognizes 6T and abstract 8T snapshots;
   arbitrary third-party state types do not automatically expose signal traces.

The current array/event engine intentionally accepts only one-bit values.
Multi-bit cells require coordinated contract changes and boundary tests. Keep
unsupported signals unavailable rather than deriving a fictional physical model.

## New view, event or control

- Views should expose draw/update over models or immutable snapshots, retain their
  figure/artists, use labels as well as color and never advance the simulation.
  Test rendering, repeated updates and unchanged input state.
- Add event kinds to `MemoryEventType`, emit them where the action really occurs,
  and extend recorder mappings only when meaningful. Preserve cycle=None for setup
  and distinguish event insertion order from CPU cycles. `WRITEBACK` is currently
  reserved, not an emitted event.
- Add widgets and callbacks in `ui/app.py`; keep execution in the processor/engine.
  Include new widgets in the owned widget tree so close releases them. Check Run,
  Pause, Reset, invalid input and architecture switching while a task is active.

## Larger arrays

Standalone `SRAMArray(rows, columns)` and `SRAMArrayView` support variable positive
dimensions. The dashboard defaults to 4 x 4; adding configurable dimensions requires
updating its constructor, capacity/help text and demo-data assumptions. Construct a
new event engine when capacity changes: its capacity is established at construction.
For default four-byte spacing, the last address is `(rows * columns - 1) * 4`.
Tests should include non-square arrays, final-cell accesses and out-of-range errors.

## More accurate SRAM models

First supply a circuit source defining device connectivity and signal semantics.
Preserve the existing 8T source limitation until that evidence exists. Electrical
quantities require an actual solver/model and units; changing a caption or drawing
analog-looking curves is not simulation. Keep those future models separate from
the current deterministic educational contracts.

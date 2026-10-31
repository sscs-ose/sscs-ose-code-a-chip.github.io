# RISC-V Memory Visualizer

An interactive SRAM lesson backed by a RISC-V processor, a logical 6T SRAM
array and immutable memory events. The main experience is a single visual
scene controlled with Previous, Next and Restart.

**Start with [Inside SRAM](notebooks/00_launch_visualizer.ipynb).** The earlier
detailed demonstrations are preserved in the
[development walkthrough](notebooks/01_development_walkthrough.ipynb).

**What this project demonstrates:** A source-rendered 6T circuit and an
18-step Read or Write lesson connect one RISC-V access to a decoded SRAM cell.
The main notebook runs four real-backend experiments covering both read bits
and both write transitions, with assertions for decoding and unselected cells.

This is a **behavioral/logical educational model**, not SPICE, a transistor-level
electrical simulator, an analog timing simulator or a physically accurate
semiconductor simulator. Waveforms show logical states, CPU cycles and event
ordering, not physical voltage, current or elapsed electrical time.

## Quick start

Clone this repository using its hosting page's clone URL, then enter its directory:

```sh
cd riscv-memory-visualizer
python -m venv .venv
```

Activate on macOS/Linux with `source .venv/bin/activate`, or on Windows PowerShell
with `.venv/Scripts/Activate.ps1`. Then, on either platform:

```sh
python -m pip install -e ".[notebook,test]"
```

### Jupyter Notebook

```sh
python -m notebook notebooks/00_launch_visualizer.ipynb
```

In the browser, select the project Python kernel and choose
**Restart Kernel and Run All Cells**.

### JupyterLab in a browser

JupyterLab is an optional alternative to Jupyter Notebook and VS Code. It is not
installed by the project's declared dependencies. If it is missing, install it
in the project environment:

```sh
python -m pip install jupyterlab
```

From the project root, start JupyterLab in an activated environment with
`python -m jupyter lab`. On Windows PowerShell, the tested command also works
without activating the environment:

```powershell
.\.venv\Scripts\python.exe -m jupyter lab
```

JupyterLab runs locally in your browser. Keep the terminal hosting the Jupyter
server open. In its file browser, open `notebooks/00_launch_visualizer.ipynb`,
select the project Python kernel, and choose **Restart Kernel and Run All Cells**.

### VS Code

Open `notebooks/00_launch_visualizer.ipynb`, select the project's `.venv` Python
kernel, and choose **Restart Kernel and Run All Cells**. The first executable
cells display the source-rendered architecture and 6T diagrams, run four
verification experiments, and show logical signal-state tables. The final
cell opens the lesson. Select Read or Write, then navigate one learning state
at a time. The final launch cell also runs alone in an installed environment.

## Manual SRAM Teaching Mode

The processor provides only a short memory-request context. The lesson then
moves through SRAM macro architecture, backend-derived address decoding, the
selected array bitcell, a six-transistor schematic, a branch-specific read or
write sequence, and an SRAM access summary. Read is selected by default. A
load drives the read story; a store drives the write story. The visual canvas
replaces its scene at each step and occupies most of one notebook output.

```python
from riscv_memory_visualizer.ui.teaching_app import SRAMTeachingApp

app = SRAMTeachingApp()
app.display()
```

The Read example explicitly initializes address 8 to one through the existing
memory event engine, then executes `lw x5,8(x2)`. The Write example executes
`addi x1,x0,1` and `sw x1,8(x2)`. The CPU's real access events supply the
address, row, column, selected cell, read result and stored state. Each teaching
step is a frozen snapshot, so Previous and Restart cannot change memory.

The notebook's experiment table is calculated on each run using fresh arrays
and `MemoryEventEngine`. The expected rows are Read 0 → 0, Read 1 → 1,
Write 0 → 1, and Write 1 → 0; all four also verify address `0x08` decodes
to `(0,2)` and that unselected cells retain their contents. Assertions stop
execution if a result differs. The logical Read/Write tables use the same
peripheral snapshots as the lesson and are **not SPICE or measured timing**.

The 6T diagram shows cross-coupled CMOS inverters and two WL-controlled NMOS
access devices. Peripheral sequence states describe logical precharge,
differential read sensing and complementary write driving. They do not model
analog voltage, transistor sizing, delays or SPICE behavior. The schematic
topology and simplifications are documented in
[the teaching model](docs/teaching_model.md). The optional Technical Details
section is collapsed by default. The earlier `RiscVMemoryVisualizerApp` remains
available as an advanced dashboard.

## Key features

- Manual, single-scene 6T SRAM lesson with branch-specific READ and WRITE paths.
- SVG schematics and immutable backend-derived teaching snapshots.
- Parsing of `lw`, `sw`, `add`, `sub`, and `addi`; 32 integer registers with x0 fixed at zero.
- Three pipeline stages: IF, ID/EX and MEM/WB, with observable occupancy and writeback.
- Sparse behavioral memory and an integrated array of logical single-bit SRAM cells.
- 6T SRAM model, abstract 8T fallback, row decoder and immutable memory events.
- Pipeline, array, cell, comparison and digital waveform views.
- Jupyter program editor, register display, timeline, architecture selector and
  Load Program / Step / Run / Pause / Reset / Speed controls.

## Architecture

```text
User Program
     |
Instruction Parser
     |
Processor + 3-Stage Pipeline
     |
Memory Interface (ProcessorEventMemory supplies CPU context)
     |
Memory Event Engine --------> EventTimeline
     |                            |
SRAM Array + Row Decoder     SimulationTraceRecorder <--- CPU snapshots
     |                            |
6T / Abstract 8T Cell        Logical signal traces
                                  |
Pipeline View -----------+    Waveform View
Array View --------------+         |
Cell View ---------------+---------+----> Jupyter UI
```

The CPU executes instructions; the event engine coordinates real memory accesses.
Views observe state and reuse figures/artists. Rendering does not execute the CPU
or read/write SRAM. Standalone `Processor()` uses `DataMemory`; the application
connects it to SRAM through the context adapter.

## Visualization layers

| View | What it shows |
| --- | --- |
| Pipeline | Stage instructions, PC, cycle and pending memory access |
| Array | Stored bits, selected row/column and selected-cell border |
| 6T cell | Conceptual six-device schematic and logical WL, BL/BL_bar, Q/Q_bar |
| Abstract 8T cell | Logical storage and software selection; no invented wiring |
| Comparison | Both model views and their documented assumptions |
| Waveform | Cycle-boundary observations and ordered events within one cycle |

Labels, numeric values, borders and line styles supplement color. Changed registers
are explicitly marked `(changed)`. The retained root-level preview PNGs are
listed in [the preview catalog](docs/previews.md).

## Supported RISC-V instructions

Only this educational subset is implemented; **this is not full RISC-V ISA support**.

| Instruction | Syntax | Operation |
| --- | --- | --- |
| `lw` | `lw rd, offset(rs1)` | Read memory into rd |
| `sw` | `sw rs2, offset(rs1)` | Store rs2 to memory |
| `add` | `add rd, rs1, rs2` | Integer addition |
| `sub` | `sub rd, rs1, rs2` | Integer subtraction |
| `addi` | `addi rd, rs1, immediate` | Add a signed decimal immediate |

Opcodes and x0-x31 names are case-insensitive; commas are required. ABI register
aliases and hexadecimal/binary immediates are unsupported. The application accepts
blank lines and `#` comments and reports invalid input with its line number.

A single instruction enters IF on cycle 1, ID/EX on cycle 2, MEM/WB on cycle 3,
and retires on cycle 4. N instructions drain in N+3 cycles. Writeback precedes
operand reads in each step; there is no forwarding, stall or hazard model.
Arithmetic uses Python integers without RV32 wrapping or immediate-width limits.

## SRAM model

The default **4 x 4 array contains 16 single-bit cells**, not sixteen 32-bit words.
Each logical location uses four-byte address spacing: 0, 4, 8, ..., 60.
`index = address // 4`, then `(row, column) = divmod(index, columns)`.
For `lw x5,8(x2)` in this lesson, `x2=0`, so base plus offset gives address
`0x08` (decimal 8), index 2 and zero-based cell (0, 2). Column 2 is the third
column. The four-byte slot spacing is an address-mapping convention; each
selected 6T cell stores one bit, not a 32-bit word.
Address 60 selects (3, 3); 64 is out of range. Unaligned/negative addresses and
stores other than integer 0 or 1 are rejected without changing memory/history.
Standalone `DataMemory` stores arbitrary Python integers and has no alignment model.

### 6T SRAM

Q/Q_bar store complementary bits. WL selects a row, and a column identifies the
accessed cell. Reads logically resolve BL/BL_bar; writes update storage. Selection
and WL remain active after an access until another selection or reset. There is
no shared electrical bit-line network or analog precharge/sense behavior in the
legacy cell model. The teaching layer adds inspectable logical access phases.

### Abstract 8T SRAM

**The available source material did not provide sufficient information for a
source-faithful detailed 8T transistor topology.** The project therefore uses an
**abstract 8T fallback**: Q/Q_bar, a software selection gate and logical read/write
methods. It claims no physical transistor connectivity, separate physical read/write
ports, performance superiority or electrical characteristics. See the
[source audit](docs/sram_architectures.md).

## Digital timing / waveforms

The upper panel records CPU cycles, PC, IF/ID_EX/MEM_WB occupancy, cell identity,
selection and logical SRAM signals. The lower panel shows ordered events within
one selected cycle. Multiple events do not become additional CPU cycles; setup
events keep `cycle=None`. READ/WRITE are occurrence indicators, not physical controls.

6T exposes modeled WL, BL/BL_bar and Q/Q_bar. Abstract 8T exposes Q/Q_bar and
software SELECTED; unsupported physical signals show **N/A**. Unknown observations
show `?`. The default window shows the last 12 cycles and at most 12 events in the
detail panel; full history is retained. See [trace semantics and API](docs/digital_timing.md).

## Installation and notebook execution

Python **3.10 or newer** is declared compatible; validation has been performed with
**Python 3.13.6**. Other Python versions have not yet been tested in a CI matrix.
Runtime dependencies are Matplotlib, ipywidgets and IPython. NumPy is only a
transitive Matplotlib dependency; the project does not import it directly.

`python -m pip install -e .` installs the library/UI dependencies. The `notebook`
extra adds Notebook, IPykernel, nbformat and nbclient; the `test` extra adds pytest.
`python -m pip install -r requirements.txt` is a convenience equivalent to the
full development installation in Quick start. Dependencies are declared in one place,
`pyproject.toml`; versions are not locked.

Use **Restart Kernel and Run All Cells** to run the launch notebook. Open the
separate development walkthrough for the earlier detailed demonstrations.
For optional browser review, follow the [JupyterLab instructions](#jupyterlab-in-a-browser).
To validate all cells without a browser:

```sh
python scripts/validate_notebook.py
```

The validator uses a fresh kernel from the current Python environment, checks the
schema and visual/widget output, and leaves the source notebook untouched.
To retain an executed copy for review, run
`python scripts/validate_notebook.py --output artifacts/submission_executed.ipynb`.
The `artifacts/` directory is ignored by Git.

### Google Colab

Clone the repository inside a Colab runtime, change into its root directory,
and run `%pip install -e ".[notebook,test]"` in a setup cell. Open
`notebooks/00_launch_visualizer.ipynb` from that checkout and restart/run all
cells. Uploading the notebook alone omits the Python package and leads to
`ModuleNotFoundError: No module named 'riscv_memory_visualizer'`. Colab's widget
display depends on its current frontend support; local VS Code/Jupyter is the
validated interactive route.

## Advanced dashboard

```python
from riscv_memory_visualizer.ui.app import RiscVMemoryVisualizerApp

app = RiscVMemoryVisualizerApp()
app.display()
```

Load Program parses before committing; invalid input preserves the previous
simulation. Load and Reset clear CPU, SRAM, selection, events and traces; Reset
retains the loaded program. Load Demo Data explicitly writes address 8 = 1 and
records setup events. Step advances one CPU cycle; Run yields between cycles using
the notebook's asyncio loop. Pause retains history. Speed changes the delay between
cycles, not simulated hardware timing. In scripts, use Step or Run inside an async
function. Switching 6T/8T pauses and resets execution/memory while retaining the
program. Reinitialize demo data afterward. Call `app.close()` before replacing it.

## Example program

The default program is also available as [examples/demo.s](examples/demo.s):

```asm
addi x2, x0, 0
lw x5, 8(x2)
add x6, x5, x2
```

After **Load Program**, click **Load Demo Data** to initialize address 8 to 1.
Six steps complete this program with x2=0, x5=1, x6=1 and selected cell (0, 2).
Without initialization, the SRAM reset value is 0. No data is silently injected.

## Project structure

```text
src/riscv_memory_visualizer/
    cpu/             Instructions, parser, registers, pipeline, processor
    memory/          Cell contracts, 6T/8T, decoder, array, sparse memory
    simulation/      CPU state, events, timeline, engine, adapter, traces
    visualization/   Read-only Matplotlib views
    ui/              Manual teaching app and optional dashboard
notebooks/           Concise launch notebook and development walkthrough
tests/              Unit, integration and headless rendering regressions
docs/               Model scope, timing, extension guide and validation record
examples/            Documented assembly demonstration
scripts/             Reproducible notebook validation
```

## Testing

```sh
pytest -q tests
python scripts/validate_notebook.py
```

Tests cover syntax/errors, CPU timing, memory boundaries, cell/array state, event
ordering, adapter context, every view and application lifecycle. Rendering checks
verify PNG output, labels, state preservation and bounded artist/widget reuse;
they are not browser screenshots or electrical validation. See
[the engineering audit](docs/validation.md) for results and environment caveats.
The notebook adds four executable acceptance experiments and verifies its own
assertions before opening the interactive app.

## Limitations

- No branches, caches, RV32 overflow semantics or additional ISA extensions.
- SRAM locations store one bit; no analog electrical behavior or physical timing.
- Abstract 8T is not a source-verified circuit.
- Timeline browsing/replay is not implemented; array/cell dashboard views are live.
- Complete trace/event history grows in memory; only rendering is windowed.
- PNG diagrams provide visible labels, but are not a full screen-reader interface.

## Extending the project

Keep models, execution, observations and rendering separate. The
[contributor guide](docs/extending.md) describes new instructions, cells, views,
events, controls and larger arrays, including the existing contracts and required
tests. More accurate SRAM models require appropriate circuit sources and explicit
new state, not inferred signals in the renderer.

## Open source / license

**Authors:** Fiza Khalid and Dayem Mujahid. See [AUTHORS.md](AUTHORS.md).

Copyright 2026 Fiza Khalid and Dayem Mujahid

This project's original work is licensed under the Apache License, Version 2.0
(Apache-2.0). The complete terms are in [LICENSE](LICENSE). Third-party
copyright notices and references remain with their respective materials;
see [the teaching model](docs/teaching_model.md) and
[architecture notes](docs/sram_architectures.md).

# Phase 13 engineering audit

Validated on 2026-09-24 using Windows and Python 3.13.6. This record distinguishes
executed checks from compatibility declarations and browser-level verification.
The results below are historical; current launch methods are in
[Quick start](../README.md#quick-start).

## Current local submission check (2026-10-31)

The source and staged packages each passed 501 tests. The targeted teaching,
decoder and event checks passed 83 tests. Both copies passed full-notebook and
standalone-launch validation in fresh kernels. The launch notebook has 15 cells,
including six code cells and nine saved outputs; its four experiment rows and
two saved SVG figures were checked. These checks leave the source notebook
unchanged.

## Results

| Check | Result |
| --- | --- |
| Baseline `python -m pytest -q` | 478 passed, 0 failed, 0 skipped, 1 warning |
| Final suite, existing environment | 486 passed, 0 failed, 0 skipped, 1 warning |
| Final suite, clean isolated environment | 486 passed, 0 failed, 0 skipped, 1 warning |
| Fresh editable install with notebook/test extras | Passed; no system site-packages inherited |
| `python -m pip check` in clean environment | No broken requirements |
| Notebook schema | Valid before and after execution |
| Complete notebook, fresh kernel | 20 code cells, 0 errors, 22 direct PNG outputs |
| Notebook dashboard output | 2 widget-view outputs; 7 PNGs in serialized widget output state |
| Final demo alone, separate fresh kernel | 1 code cell, 0 errors, 1 widget view, 3 widget PNGs |
| Documented `examples/demo.s` | 6 cycles; x2=0, x5=1, x6=1; selected cell (0, 2) |
| Source-level internal import graph | No cycles found |
| Source/docs/notebook portability scan | No private usernames or machine-specific absolute paths |

The suite was run without suppressing warnings. Its single warning is pytest's
inability to write the existing machine's cache directory; no project settings
were changed to accommodate that permission issue. Kernel startup also logged
non-fatal local profile-permission and unencrypted local TCP transport warnings.
Some standalone render checks logged a Matplotlib font-cache permission warning.
These did not cause code-cell or application failures. The earlier development
environment also emitted a Windows event-loop fallback warning during notebook
execution; it was not an application exception.

The clean environment was created with `python -m venv .venv-audit`, then installed
with `python -m pip install -e ".[notebook,test]"`. It is ignored and not required
to run the project. Installation initially failed because the execution sandbox
blocked network sockets; the authorized retry succeeded. No runtime workaround or
developer environment was copied into the clean environment.

Key versions resolved there: Matplotlib 3.11.2, ipywidgets 8.1.9, IPython 9.17.1,
Notebook 7.6.3, IPykernel 7.3.0, nbclient 0.11.0, nbformat 5.11.1, pytest 9.1.1.
These are tested versions, not a cross-platform lockfile or a claim that every
supported dependency/Python combination was exercised.

## Architecture and dependency audit

CPU, memory, simulation, visualization and UI remain separate. The CPU owns
execution; its adapter supplies retirement context; the event engine records real
accesses; the recorder observes immutable events and cell/pipeline snapshots;
Matplotlib views own presentation. No major architecture features were added.

Runtime dependencies now explicitly include Matplotlib, ipywidgets and IPython.
There are no direct NumPy imports, so its redundant direct requirement was removed;
Matplotlib still installs it transitively. Notebook/kernel/validation tools and
pytest are optional extras. `requirements.txt` delegates to those extras rather
than duplicating dependency lists. Metadata includes name, version, description,
README and Python >=3.10. Python 3.13.6 is the tested version; a wider CI matrix
remains future work.

## Behavioral coverage and application checklist

These are **executed Python/widget callback and kernel checks**, including actual
button callbacks where covered by tests. They are not a claim of manual browser
click testing: no browser automation tool was available in this session.

| Behavior | Evidence |
| --- | --- |
| Program loads; blank lines and comments work | `test_app.py`, parser tests, final notebook demo |
| Empty/invalid program reports useful errors and retains state | App invalid-load tests; parser invalid syntax/register/immediate tests |
| Empty, single and multi-instruction pipelines | `test_pipeline.py`, `test_processor.py` |
| Negative immediate and all five supported instructions | Parser/processor tests |
| Step and register/pipeline/array/cell/timeline/waveform updates | App end-to-end load and waveform tests |
| Run, Pause, resume and duplicate Run | Cooperative execution and cancellation tests |
| Speed control | Observed delays 0.1, 0.4 and 1.0 seconds; exactly three CPU cycles |
| Reset during Run; repeated loads/resets | App lifecycle and cancellation tests |
| 6T/8T switching during Run and reset afterward | App architecture-switch tests |
| Invalid SRAM selection, unaligned/out-of-range access | Decoder, array, event and app tests; mutation checks |
| Address 60 selects final cell; address 64 fails | All 16 mappings tested; new adapter regression for both 6T and abstract 8T |
| Empty timeline; one/multiple-cycle waveform | Timeline, signals and waveform tests |
| Repeated view updates reuse resources | Artist, figure and widget identity/count tests |
| Final notebook needs no prior state | Full walkthrough and standalone final cell executed in separate fresh kernels |

`lw x5,8(x2)` with x2=0 and address 8 initialized to 1 reaches IF, ID/EX and
MEM/WB, then returns 1 into x5 on cycle 4. Tests follow the real adapter, engine,
row/column (0, 2), cell snapshot, memory response and register update for both
architectures. The final-address regression also verifies the adapter retains
the same CPU state object after reset and rejects address 64 without mutation.

Eight new test cases cover five invalid register-index types, final-address
integration for two cell architectures, and changing the Run speed. Existing
tests additionally check the text indicator for changed registers and rendered
caption/footer separation. Previous phase tests remain passing.

## Visual and educational audit

Current notebook images for the pipeline, array, 6T cell, abstract 8T cell,
comparison and waveform were visually inspected. The array event caption
overlapped its footer; it now has enough space. The 6T caption was similarly
given more separation. Updated images were re-rendered and inspected, and existing
render tests now assert caption/footer bounds do not overlap for modeled events.

Labels identify stage occupancy, signal values, selection and model scope. Array
selection has a border and coordinates; 6T access uses line styles and text;
waveforms have numeric/category labels. Register updates now say `(changed)`
instead of relying on yellow highlighting alone. Small PNG text can still require
zooming, and these figures are not a complete screen-reader interface.

Notebook structure now follows a numbered educational progression, includes the
logical/analog distinction up front, and ends with an obvious standalone final
demo. At this audit's date, saved outputs, execution counts and widget metadata
were cleared from the source. The current launch notebook retains reviewed outputs;
the validator leaves its source unchanged and can save results only to a separate
artifact. Browser-specific layout and assistive-technology testing remain outside
the checks performed here; widget MIME output/state and callback behavior passed.

## Changed files

- `README.md`: complete overview, quick start, architecture diagram, instruction
  subset, model scope, controls, example, testing, extension and license sections.
- `pyproject.toml`, `requirements.txt`: accurate metadata and dependency extras.
- `.gitignore`: additional Python/test caches, isolated environments and transient
  validation artifacts; the normal pytest configuration remains unchanged.
- `notebooks/00_launch_visualizer.ipynb`: numbered walkthrough, introduction,
  corrected headings, clean outputs and standalone final demonstration.
- `examples/demo.s`: documented default program and required initialization.
- `scripts/validate_notebook.py`: schema/output checks and two fresh-kernel runs
  using the invoking interpreter, with optional separate executed output.
- `docs/extending.md`, `docs/previews.md`, `docs/validation.md`: extension contracts,
  intentional preview catalog and this audit. Existing SRAM/timing scope docs retained.
- `cpu/registers.py`: deterministic rejection of non-integer/boolean indices and
  return annotations; valid register behavior unchanged.
- `ui/app.py`: visible text for changed registers.
- `visualization/array_view.py`, `visualization/cell_view.py`: caption spacing.
- `memory/array.py`, `memory/base_cell.py`, `memory/sram8t.py`,
  `simulation/processor_memory.py`, `simulation/signals.py`,
  `visualization/cell8t_view.py`, `visualization/cell_comparison_view.py`,
  `visualization/waveform_view.py`: concise public API docstrings.
- `simulation/state.py`: clarify legacy SRAM placeholders are not live signals;
  retain compatibility with foundation tests and callers.
- `tests/test_registers.py`, `tests/test_app.py`, `tests/test_processor_memory.py`,
  `tests/test_array_view.py`, `tests/test_cell_view.py`: regression coverage above.
- Removed empty, unused `memory/electric_model.py` and `visualization/cpu_view.py`.
  Package `__init__.py` files were retained.

Production and test paths above are relative to `src/riscv_memory_visualizer/`
and the repository root respectively. Five existing root preview PNGs were retained
as documented assets. Local caches, package metadata, virtual environments and
`artifacts/` are generated/ignored and not project inputs. No private paths were
added to committed documentation or notebook source.

## License, limits and future work

At the time of this audit, no owner-selected license or LICENSE file was found.
The project is now licensed under Apache-2.0; see [LICENSE](../LICENSE).

The 6T model remains logical. The source material still does not establish an 8T
topology; the abstract fallback exposes Q/Q_bar and software selection, with
unsupported physical signals marked N/A. No physical ports, performance or
electrical claims were added. Event order remains distinct from CPU cycles.

Remaining debt: growing event/trace history, fixed dashboard dimensions, legacy
SimulationState signal placeholders, image-based accessibility, and untested
cross-platform/Python-version combinations. Useful next steps are CI across
supported environments, browser/accessibility testing, and
profiling long runs before considering history limits. Any future detailed 8T
model requires a circuit source. None of these future features was implemented.

## Reproduce

From the repository root in an activated virtual environment:

```sh
python -m pip install -e ".[notebook,test]"
python -m notebook notebooks/00_launch_visualizer.ipynb
```

For optional local browser review with JupyterLab, follow the
[README instructions](../README.md#jupyterlab-in-a-browser).

Run the final interactive demonstration, then Load Program and Load Demo Data.

```sh
pytest -q tests
python scripts/validate_notebook.py
```

For a separate executed notebook artifact:

```sh
python scripts/validate_notebook.py --output artifacts/validated-notebook.ipynb
```

Phase 13 complete. Phases 1-12 remain complete; no new major feature phase started.

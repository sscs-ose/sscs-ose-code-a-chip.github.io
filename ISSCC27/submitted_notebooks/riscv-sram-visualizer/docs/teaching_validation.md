# Manual SRAM Teaching Mode validation

This records an earlier teaching-mode validation. For current Jupyter Notebook,
JupyterLab, and VS Code launch steps, see [Quick start](../README.md#quick-start).

The 2026-10-31 local check confirmed 18 READ and 18 WRITE steps, with Step 3
showing the address-slot arithmetic for zero-based cell (0,2) in both stories.
The targeted teaching, decoder and event tests passed 83 checks.

Baseline before implementation: **486 passed** using the existing Python 3.13
virtual environment. The final suite passed **492 tests**. The new tests cover
backend-derived address and row/column, real read and write outcomes, phase
state, non-mutating manual navigation, six transistor symbols and widget reuse.

`scripts/validate_notebook.py` executed the concise launch notebook in a clean
kernel and its sole launch cell in a second clean kernel. Both had zero
code-cell errors, one widget view and an inline SVG scene in widget state.

Eight SVG and matching PNG previews were exported to
[`previews/teaching`](previews/teaching/README.md). Visual review at 960×540
found the selected row and column legible, six device labels and storage nodes
visible, operation colors distinct, and the summary readable. The peripheral
insets required an enlargement and a shift left to keep labels within the
canvas. This is a source and headless-render review, not a browser-based
accessibility audit.

The old dashboard, CPU and SRAM models, event engine, waveform code and all
previous tests remain in the repository. At the time of this validation,
no LICENSE file was present. The project is now licensed under Apache-2.0;
see [LICENSE](../LICENSE).

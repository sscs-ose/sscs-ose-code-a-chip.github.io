# OpenTCAD: An Open-Source Process-to-Device-to-Circuit TCAD Framework, Demonstrated on a Light-Powered Microrobot Controller

```
Submission to IEEE SSCS Open-Source Ecosystem “Code-a-Chip” Travel Grant Awards at ISSCC'27
SPDX-License-Identifier: Apache-2.0
```

|Name|Affiliation|IEEE Member|SSCS Member|
|:--:|:----------:|:----------:|:----------:|
|Abhineet Agarwal|IIT Bombay, India|No|No|

## Overview

OpenTCAD is a modular open-source Python framework that connects process simulation to
drift-diffusion device simulation through one shared data object (`MeshField`). This
submission extends it with prescribed optical generation, explicit 2-D to physical current
conversion, an ideal-diode photovoltaic compact model with maximum-power-point and SPICE
export, and a correction to the electron/hole source signs in the core solver. The notebook
runs the solver live (Section 4) and then uses the result in a case study (Section 5):
a light-powered microrobot controller inspired by Reynolds et al. (2022), whose SKY130 clock
macro is verified with DRC, LVS and extracted-parasitic comparisons.

Open `submission.ipynb` and run the cells in order. SETUP.md has the manual commands.

## What is in this folder

- `submission.ipynb`: the notebook, with saved outputs.
- `opentcad/`: the framework source, bundled so the notebook does not need to download it.
- `examples/microrobot/`: the case-study code, circuits, RTL and archived evidence.
- `docs/`: optical generation and photovoltaic compact-model documentation.
- `tests/`: a focused test subset (`python -m pytest -ra`).
- `SETUP.md`, `ATTRIBUTION.md`, `CHANGELOG.md`, `LICENSE`, `submission.json`.

## How to run

Use Python 3.12. The notebook's setup cell installs any missing pinned Python packages and,
on Debian/Ubuntu, the native BLAS/LAPACK and GLU libraries. Because `opentcad/` and
`examples/` are in this folder, the notebook uses them; only a copy of the notebook on its own
downloads OpenTCAD from GitHub.

Sections 5.9 and 5.10 rerun the clock transients and regenerate the compact clock layout with
ngspice, Magic and Netgen. On Linux x86-64 they install those tools into `eda_tools/` with
micromamba and download the SKY130A PDK (open_pdks 1.0.535); set `RERUN_EDA = False` in
Section 5.9 to skip them. The tool installs need network access. Delete `eda_tools/` after a run if
you do not need it again.

`python execute_notebooks.py .` re-executes the notebook into `examples/microrobot/local_runs/`
and verifies that no packaged input changed. `execution_validation.json` records the Python
version and platform of the packaged run. `python -m pytest -ra` runs the focused tests; they
need the setup in SETUP.md. Google Colab is untested.

## Status and limitations

Full transistor-coupled controller startup failed and remains unresolved. The TCAD structures
are conceptual and uncalibrated, mechanics are assumed, no walking is simulated, and physical
verification covers the clock macro, not a complete controller. Read
`examples/microrobot/SUBMISSION_STATUS.md` before interpreting plots.

Local PDFs, raw SPICE transients and externally supplied measurement CSVs of unverified
redistribution rights are excluded. Attribution, the intellectual-property notice disclosed
in the cited paper and data-licensing notes are in `ATTRIBUTION.md`. This work does not
authorize fabrication.

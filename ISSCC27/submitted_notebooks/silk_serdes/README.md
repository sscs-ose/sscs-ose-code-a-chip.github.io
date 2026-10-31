# Introducing Silk with a portable SerDes transmitter

**Team: Manar El-Chammas (representative)** · SSCS Code-a-Chip · ISSCC 2027

This notebook introduces Silk through a 600 Mb/s SerDes transmitter: circuit
hierarchy, registered tests and specifications, equalizer optimization, behavioral
calibration, PVT and mismatch, device stress, area and parasitic estimation,
CMOS/CML comparison, process portability and design history.

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/manar-c/sscs-ose-code-a-chip.github.io/blob/silk-serdes/ISSCC27/submitted_notebooks/silk_serdes/serdes_demo.ipynb)

## Run in Colab

Open the badge, connect to a hosted CPU runtime, and run the notebook cells in
order. The first code cell downloads this project, installs `circuitsilk==0.2.0`
from PyPI and ngspice, and downloads the pinned sky130 and GF180MCU models.
No ZIP upload is needed. Allow several GB for the models and simulation outputs.
GF180MCU is a preview integration.

The default `PVT_GROUPED = True` runs three paired operating points. Set it to
`False` in section 7.4 to run all 27 combinations. A previous full run with
27 points took 1 h 47 min, including 65 min for PVT; setup time is additional,
and hosted-machine timings vary.

## Run locally

The reference environment is Linux with Python 3.12 and ngspice 42. Install
ngspice first, then run these commands from this directory:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements.lock
PDK_ROOT="$PWD/.pdk" .venv/bin/python -m jupyterlab serdes_demo.ipynb
```

Run the setup cell to install the pinned PDK models into the local `.pdk`
directory. `environment.json` records the reference versions and model pins;
setup records the versions actually used in `artifacts/environment.json`.
Results are saved in a new folder under `artifacts/` for each execution.

For an automated run after installation:

```bash
PDK_ROOT="$PWD/.pdk" SILK_DEMO_CELL_TIMEOUT=7200 .venv/bin/python tools/execute_notebook.py
```

## Contents and verification

- `serdes_demo.ipynb`: the complete walkthrough.
- `circuits/`: reusable circuit definitions and process mapping.
- `characterization/`: the circuit's stimulus, tests, measurements and models.
- `tools/setup_notebook.py`: environment installation and checks.
- `tools/notebook_display.py`: table, eye-plot and viewer presentation.
- `tools/execute_notebook.py`: optional automated execution.
- `requirements.lock`, `environment.json`: software and model pins.
- `source_provenance.json`, `LICENSE`: source attribution and MIT license.

The published notebook contains outputs from the completed GitHub-to-Colab run
on 31 October 2026: all 34 code cells executed without exceptions, with nine
figures, three PVT points and 20 Monte Carlo samples. The run used Python 3.13.18,
Silk 0.2.0, ngspice 42, NumPy 2.1.3 and Matplotlib 3.10.0. The recorded circuit,
characterization and setup source hashes match this submission. Its elapsed
time was not recorded; the timing above is from the earlier 27-point run.
Interactive viewers and download buttons require a live notebook runtime. A baseline eye-height failure
is intentional; the equalizer optimization improves it. Device-stress findings
remain visible even when link specifications pass. Area and parasitic estimates
are early design estimates, not a completed physical layout.

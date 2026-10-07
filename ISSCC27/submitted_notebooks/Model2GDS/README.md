# Model2GDS: An Auditable Model-to-RTL Workflow for Reproducible Systolic-Array Design

Explore a parameterized **2×2 / 4×4 / 8×8 output-stationary systolic array**
with independent numerical and token-cycle models. Across
**441 accepted case/configuration executions**,
the models and captured RTL agree exactly on numerical results and cycle counts.

**[Open the executable Jupyter notebook](Model2GDS.ipynb)** to inspect the design,
replay the verification, and follow the reproducible
**raw evidence → parser → structured result → figure** workflow.
A separate tiny-counter design proves the open-source RTL-to-GDS toolchain.

This educational design workflow includes reusable Python/SystemVerilog sources,
preserved evidence and reproducible figures. Author and representative details
are in [TEAM.json](TEAM.json) and the notebook header.

## Offline reproduction

Use Python 3.12 with the recorded dependency versions. From this directory:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/build_submission.py --verify-package
python scripts/reproduce_figures.py --root . --portable --check
python scripts/build_submission.py --execute-notebook
```

On Windows, activate `.venv/Scripts/Activate.ps1`.
JupyterLab can also open the notebook and run all cells. The offline verification
needs only Python's standard library; display/plot dependencies are listed above.
Nothing in this workflow invokes a simulator, synthesis, P&R, STA or Docker.
`--execute-notebook` runs cells in memory and preserves the bundled source bytes.
The exact observed notebook dependency versions are in `support/notebook_runtime.json`.

The replay recomputes GEMM/token results from preserved inputs and compares them
with the recorded RTL observations. It reparses the tiny-counter raw evidence and
regenerates analysis/figures. It does not pretend to be a new simulator/ASIC run.
Raw command records retain historical machine paths solely as provenance.

## What is included

- `Model2GDS.ipynb`: the narrative and executable checks.
- `model/`, `rtl/`, `verification/`: independent references and synthesizable fabric/harness.
- `results/processed/`: immutable accepted functional/counter data and final analysis.
- `results/raw/`: captured simulation and counter RTL-to-GDS sources for displayed claims.
- `figures/final/`: deterministic figures and their source manifest.
- `file_manifest.json`: exact SHA256 and byte size of every package file, excluding itself.
- `environment/toolchain.lock.json`: observed tool/PDK/library identities, not guessed versions.
- `docs/`: arithmetic, cycle, workload and final-analysis contracts.

`REBUILD.md` supplies optional fresh Verilator and pinned OpenLane commands using
only bundled source/configuration. The portable RTL helper needs no historical
Git objects. Its outputs go to a new external work directory. Full forensic
qualification additionally uses the development repository's frozen history and
original runners; the basic notebook and rebuild demonstrations do not depend on
that repository being published or available.
The full forensic archive is available from the author using the contact in
`TEAM.json`. In research mode, `support/physical_evidence_inventory.json` lists
both bundled metric authorities and omitted bulky intermediates explicitly.

## Scope and submission

The tiny counter proves the ASIC toolchain; it is never an accelerator result.
Only a complete qualified set of implementations can support physical comparisons. The
notebook excludes rejected performance and makes no accelerator
ranking claim. No silicon Fmax, power/energy or process-variation result is claimed.

Apache-2.0 project license: `LICENSE`. GDS cell attribution: `NOTICE` and
`third_party/`. Primary references: `REFERENCES.md`.
Official rule provenance: `support/official_rules.json`. Place this entire folder
under `ISSCC27/submitted_notebooks/Model2GDS/` in the official fork; change no other
project. Team and contact details are in `TEAM.json`.

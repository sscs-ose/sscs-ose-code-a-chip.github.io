# Reproduction and portable export

SPDX-License-Identifier: Apache-2.0

Start with `submission.ipynb`. Section 4 runs OpenTCAD's drift-diffusion solver live on a small
illuminated silicon cell and exports a SPICE compact model. Section 5 executes the
mixed-abstraction microrobot system and checks numerical completion, refinement and an
all-dark negative control.

It does not establish an autonomous transistor controller; read
`examples/microrobot/SUBMISSION_STATUS.md` in an export.

From the repository, choose a fresh destination:

```sh
python tools/build_microrobot_submission.py --output build/ISSCC27/submitted_notebooks/opentcad_microrobot
```

The complete exported folder contains its own `opentcad` and application
packages. Move the whole folder, start Jupyter there and open
`submission.ipynb`. It does not search for a parent checkout, use an editable
install, download paper data or invoke git at runtime.

Use Python **3.12**. The notebook's setup cell installs any missing pinned Python packages and, on
Debian/Ubuntu, the native BLAS/LAPACK and GLU libraries, so opening the notebook and running the cells
is enough. The commands below are the manual route, for example for `execute_notebooks.py` or the tests
from a clean environment. The included `requirements-notebook.txt` is a universal Python-3.12 lock with
platform markers. On Debian/Ubuntu, native solver dependencies include BLAS/LAPACK and GLU:

```sh
sudo apt-get update
sudo apt-get install -y libblas3 liblapack3 libopenblas0-pthread libglu1-mesa
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-notebook.txt
.venv/bin/python execute_notebooks.py .
```

On Linux the notebook's setup cell sets `DEVSIM_MATH_LIBS` before DEVSIM is imported, because
DEVSIM looks for unversioned BLAS/LAPACK names while Debian/Ubuntu ship versioned ones. The
bundled tests need the same setting:

```sh
export DEVSIM_MATH_LIBS=libopenblas.so.0:liblapack.so.3:libblas.so.3
.venv/bin/python -m pytest -ra
```

If DEVSIM cannot start, Section 4 of the notebook falls back to the archived curves and says so.
Google Colab has not been tested.

On macOS use matching native BLAS/LAPACK and the Gmsh wheel's native runtime.
Select a Jupyter kernel from this environment. The lock includes ipykernel
and notebook execution libraries, but not a JupyterLab user interface.

Section 4 of the notebook reruns a small OpenTCAD/DEVSIM calculation. The Section 5 system
runner reads actual archived drift-diffusion tables and archived schematic clock
characterization. Notebook cells explicitly state which calculations are rerun. Reviewing archived transistor/layout
evidence is not rerunning ngspice, Magic or Netgen. To rerun those separate
flows, install ngspice 44.2, SKY130A/open_pdks 1.0.535, Magic 8.3.546 and
Netgen 1.5.325 and follow the evidence READMEs. No PDK is bundled.

Fresh outputs go only under `examples/microrobot/local_runs/`. The executor
verifies every packaged input hash before execution and checks all reference
hashes after execution. It records actual Python/platform, code-cell counts,
errors, output plots and archive changes in `execution_validation.json`.
Executed notebook outputs are then sealed explicitly into `submission.json`;
source and reference hashes cannot silently be refreshed to hide drift.
`local_runs/` is intentionally excluded from the immutable manifest; its
fresh summary and plotting outputs document that particular execution.

Run `python -m pytest -ra` for the curated focused tests. Read the actual
passed/skipped counts; historical full-suite counts are not a package promise.
Colab is untested. Each execution record applies only to its named notebook and environment.

The intended folder is `ISSCC27/submitted_notebooks/opentcad_microrobot/`.


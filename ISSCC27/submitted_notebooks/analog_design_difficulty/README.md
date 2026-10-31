# Why Analog Design Remains Difficult Even When the Equations Are Known

*A reproducible SKY130 sample-and-hold case study in coupling, revision, verification, and design closure*

Kazuki Fujita — Department of Electrical Engineering, Graduate School of Engineering, Tokyo University of Science (GitHub: 771-8bit)

An educational Jupyter notebook for analog designers who know the canonical circuits. It explains why analog design
remains difficult after the circuit equations are known: requirements can be written as a tree, while the physical
quantities that must satisfy them are coupled, with cycles, and depend on operating point, stored state, timing, and
process, supply, and temperature. It follows how engineers make that coupled problem tractable — provisional
requirements and allocations, characterization over conditions, representations adequate for a decision, circuit
changes that weaken a dependency, verification, and revision — and asks what changes as AI enters the development
process and what a junior designer needs to learn beyond the equations.

The running example is a single-ended SKY130 sample-and-hold (closed-loop driver, sampling switch, 1 pF hold capacitor,
0.6–1.2 V, 40 ns acquisition, ±1 LSB of a 10-bit-equivalent step). A first cut meets its local acquisition allocation
and fails the parent held-sample requirement; evidence leads to a bootstrapped sampling switch and a redesigned driver;
the selected design closes the deterministic requirement and a separate random-noise budget over a declared
schematic-level verification domain of repeated samples and 45 process/supply/temperature conditions. This is not
production sign-off; the circuit closure is evidence for the notebook's engineering argument, not its main contribution.

**Main notebook:** [`analog_design_difficulty.ipynb`](analog_design_difficulty.ipynb) (saved with the outputs of one complete run).

## Toolchain

Open-source only: Python 3.12 or later (tested: 3.14.6), ngspice (tested: ngspice-42), the SkyWater SKY130 PDK from
open_pdks (tested commit `c6d73a35f524070e85faff4a6a9eef49553ebc2b`), and Python dependencies declared in
`pyproject.toml` and pinned in `uv.lock` (managed with [uv](https://docs.astral.sh/uv/)). The SKY130 models are not
included; install them separately (for example with volare) and point `PDK_ROOT` at the folder that contains `sky130A/`.

## Folder

| Path | Contents |
|---|---|
| `analog_design_difficulty.ipynb` | the notebook |
| `experiments/closure/` | the pre-registered parent metric, budget and verification sets (`CLOSURE_BRIEF.md`), the sequential sample-and-hold bench, the stability, noise, and device-voltage checks, the final-verification and assembly scripts, and the netlists of the selected design and of the compared candidates |
| `experiments/experiment_a/` | the first-cut experiment: design brief, studies with their results, SKY130 netlists, scripts, and the reduced model |
| `results/closure/` | the first cut on the sequential bench and the final verification of the selected design (`results/closure/final/q1_boot2/final_closure.json`) |
| `results/figures/`, `results/data/` | simulation figures and compact first-cut data read by the notebook |
| `assets/diagrams/`, `scripts/draw_restart_diagrams.py`, `scripts/draw_diagrams.py` | explanatory diagrams and the scripts that draw them |
| `references/` | bibliography and the support recorded for each source |
| `scripts/reproduce.py` | reproduction |
| `pyproject.toml`, `uv.lock`, `.python-version` | Python environment (uv project) |

## Reproduce

Run on a copy of this folder: the script rewrites the results and the notebook in place, and `uv sync` creates `.venv/`.

```bash
uv sync --locked
export PDK_ROOT=$HOME/.volare                       # contains sky130A/libs.tech/ngspice/sky130.lib.spice
uv run python scripts/reproduce.py --no-spice       # figures and notebook from the committed results (minutes)
uv run python scripts/reproduce.py --skip-final     # all simulations except the final closure verification
uv run python scripts/reproduce.py                  # everything, including the final closure verification (hours)
```

`CLOSURE_WORKERS` sets the number of parallel ngspice runs.

## License

Apache-2.0 (`LICENSE`). Unless otherwise noted, project-owned material in this submission (code, documentation,
notebook, figures, diagrams, netlists, and data) is licensed under the Apache License 2.0. No third-party code, models,
or assets are bundled. The SkyWater SKY130 PDK (open_pdks), ngspice, and the Python packages listed in `uv.lock` are
external dependencies that are installed separately under their own licenses.

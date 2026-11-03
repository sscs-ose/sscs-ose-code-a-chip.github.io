# Why Analog Design Remains Difficult Even When the Equations Are Known

*Coupled physics, provisional requirements, and engineering evidence, with a reproducible SKY130 sample-and-hold as
the running example*

Kazuki Fujita — Department of Electrical Engineering, Graduate School of Engineering, Tokyo University of Science (GitHub: 771-8bit)

**Main notebook:** [`analog_design_difficulty.ipynb`](analog_design_difficulty.ipynb) (saved with the outputs of one complete run).

An educational Jupyter notebook for analog designers who know the canonical circuits. It explains why analog design
remains difficult after the circuit equations are known: the quantities those equations describe are physically
coupled, and which interaction dominates changes with operating point, signal level, stored state, timing, and
process, supply, and temperature. Requirements can be written as a tree for engineering management, while the
physical and design dependencies that must satisfy them are coupled, with cycles.

The notebook follows the established practices engineers use to make that coupled problem tractable — provisional
requirements and allocations, characterization over conditions, models and tests adequate for a particular decision,
circuit changes that weaken a dependency, choices of what to design jointly and where to place block boundaries,
verification, and revision when evidence shows that an assumption no longer holds. It argues that optimization and
search work inside a formulation that engineers choose and revise, asks what changes if AI lowers the cost of search,
verification, and coordination, and closes with what a junior designer needs to learn beyond the equations. The
practices are established; the notebook does not propose a new design methodology.

A single-ended sample-and-hold front end in the open SKY130 process, simulated with ngspice, serves as the running
example and as reproducible evidence for the argument. It is not the subject of the notebook, and its verification is
schematic-level, not production sign-off.

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
| `results/closure/` | sequential-bench results: the first cut at the screening conditions, the compared candidates, and the final verification of the selected design |
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

#!/usr/bin/env python3
"""Regenerate the simulation results and figures, then rebuild and re-execute the notebook.

Usage (from the folder that contains scripts/ and experiments/):
    uv run python scripts/reproduce.py              # everything (several hours on 12 cores)
    uv run python scripts/reproduce.py --skip-final # everything except the final closure verification
    uv run python scripts/reproduce.py --no-spice   # no ngspice: figures and notebook from the committed results

Stages
1. reduced model (first-cut evidence)                       experiments/experiment_a/ideal/run_experiment.py
2. first-cut SKY130 evidence                                experiments/experiment_a/sky130/run_sky130.py, run_followup.py
3. first cut on the sequential bench (Figure 3)             experiments/closure/run_screen.py f2 --pvt screen --legacy
4. final closure verification of the selected design       experiments/closure/run_final.py q1_nvt1
5. closure result, data figures, explanatory diagrams      assemble_final.py, figures.py, scripts/draw_restart_diagrams.py
6. notebook                                                 executed in place

Requirements: the uv environment of pyproject.toml / uv.lock (`uv sync --locked`); ngspice (tested: ngspice-42) and
SKY130A (default ~/.volare/sky130A, or set PDK_ROOT). CLOSURE_WORKERS sets the number of parallel ngspice runs.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
CL = "experiments/closure"
FINAL = "q1_nvt1"  # the selected design (experiments/closure/designs.py SELECTED)
SPICE = [
    ("first-cut SKY130 evidence", ["experiments/experiment_a/sky130/run_sky130.py"]),
    ("first-cut follow-up studies", ["experiments/experiment_a/sky130/run_followup.py"]),
    ("first cut on the sequential bench (pre-amendment screening)", [f"{CL}/run_screen.py", "f2", "--pvt", "screen", "--legacy"]),
]
FINAL_STAGE = ("final closure verification", [f"{CL}/run_final.py", FINAL])
ALWAYS = [
    ("reduced model", ["experiments/experiment_a/ideal/run_experiment.py"]),
]
POST = [
    ("closure result", [f"{CL}/assemble_final.py", FINAL]),
    ("data figures", [f"{CL}/figures.py"]),
    ("explanatory diagrams", ["scripts/draw_restart_diagrams.py"]),
]


def run(title: str, argv: list[str]) -> None:
    print(f"== {title}", flush=True)
    script = ROOT / argv[0]
    subprocess.run([sys.executable, str(script), *argv[1:]], cwd=script.parent if CL in argv[0] else ROOT, check=True)


def execute_notebook_in_place(nb_path: Path) -> None:
    import nbformat
    from nbconvert.preprocessors import ExecutePreprocessor

    nb = nbformat.read(nb_path, 4)
    ExecutePreprocessor(timeout=3600, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(nb_path.parent)}})
    nbformat.write(nb, nb_path)


def main() -> None:
    no_spice = "--no-spice" in sys.argv
    for t, a in ALWAYS:
        run(t, a)
    if not no_spice:
        for t, a in SPICE:
            run(t, a)
        if "--skip-final" not in sys.argv:
            run(*FINAL_STAGE)
        run(*POST[0])
    for t, a in POST[1:]:
        run(t, a)
    builder = ROOT / "notebook" / ("build" + "_notebook.py")  # development layout only: rebuild prose from notebook/text
    if builder.is_file():
        run("notebook build", ["notebook/" + builder.name])
    print("== notebook execution", flush=True)
    nb_path = next(p for p in (ROOT / "analog_design_difficulty.ipynb", ROOT / "notebook" / "code_a_chip.ipynb") if p.is_file())
    execute_notebook_in_place(nb_path)
    print(f"executed {nb_path.relative_to(ROOT)} in place\n== done")


if __name__ == "__main__":
    main()

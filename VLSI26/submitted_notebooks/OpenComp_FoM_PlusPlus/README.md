# OpenComp-FoM++ (VLSI'26 Code-a-Chip Submission)

OpenComp-FoM++ is a reproducible notebook workflow to compare **StrongARM** and **Double-Tail** dynamic comparators in SKY130 using:
- unified score optimization,
- full Pareto-front analysis,
- PVT + Monte Carlo robustness ranking,
- educational regeneration-dynamics animation.

## Team
- Team Lead: William Anthony
- Member: Benedictus Kenneth Setiadi

## Project Files
- `OpenComp_FoM_PlusPlus.ipynb` — main submission notebook.
- `artifacts/` — generated outputs after running the notebook:
  - `sweep_pvt.csv`
  - `sweep_mc.csv`
  - `ranking.csv`
  - `pareto.csv`
  - `summary.json`
  - `plots/pareto_fronts.png`
  - `plots/regeneration_dynamics.gif`

## Quick Start (Recommended)
1. Open `OpenComp_FoM_PlusPlus.ipynb` in Jupyter or VS Code Notebook.
2. Run all cells from top to bottom.
3. Keep `DEMO_MODE = True` for an immediate reproducible run.
4. Check `artifacts/` for generated tables and plots.

## Python Environment
Install dependencies:

```bash
pip install numpy pandas matplotlib seaborn tqdm pillow
```

## Running with Real ngspice (Optional)
By default, the notebook runs in demo/surrogate mode.

To use transistor-level simulation:
1. Install ngspice and make sure it is in your `PATH`.
2. Set `DEMO_MODE = False` in the configuration cell.
3. Update `generate_netlist(...)` model includes and comparator instantiations.
4. Update `parse_measure_output(...)` to match your `.measure` output format.

## Reproducibility Notes
- Random seed is fixed (`np.random.seed(42)`).
- PVT corners and Monte Carlo run count are declared in one config cell.
- All major outputs are exported as CSV/JSON/PNG/GIF.

## License
This project is intended for Apache License 2.0. Add a `LICENSE` file in this folder before PR submission.

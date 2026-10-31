# Simulation environment

Date: 2026-10-29 JST

| Item | Value |
|---|---|
| OS | Ubuntu 24.04.5 LTS under WSL2 (Linux 6.18, x86_64) |
| Simulator | ngspice-42 (KLU solver) |
| PDK | SKY130A from open_pdks commit `c6d73a35f524070e85faff4a6a9eef49553ebc2b`, installed with volare under `~/.volare/sky130A` |
| Model include | `.lib "<PDK_ROOT>/sky130A/libs.tech/ngspice/sky130.lib.spice" <corner>`; the path is filled in by `spice_runner.py` (override with `PDK_ROOT` or `SKY130_NGSPICE_LIB`) |
| ngspice settings | `.spiceinit` in this folder: `ngbehavior=hsa`, `skywaterpdk`, `ng_nomodcheck`, `option klu` (open_pdks recommendation); ngspice reads it because the runner executes from this folder |
| Corners | `tt`, `ss`, `ff`, `sf`, `fs` available; nominal `tt`, 27 °C |
| Python | 3.14.6 in a project-local virtual environment created with `uv` from `pyproject.toml` and `uv.lock` |

The environment printed by the notebook (`results/data/sky130_summary.json`, `environment`) is the one that produced the committed results.

## Smoke test

`netlists/tb_smoke_mos.spice`: operating points of `nfet_01v8` and `pfet_01v8` (W/L = 2/0.5) at |V_GS| = 0.9 V, |V_DS| = 1.8 V converge (38.9 µA and 0.23 µA). I–V sweeps at |V_DS| = 0.9 V (W/L = 5/0.5) indicate thresholds of about 0.6–0.65 V (`nfet_01v8`), 0.5 V (`nfet_01v8_lvt`), 1.0 V (`pfet_01v8`), and 0.5 V (`pfet_01v8_lvt`). The high `pfet_01v8` threshold shaped the driver (`DRIVER_DESIGN.md`).

## Reproduction

```bash
uv sync --locked
uv run python experiments/experiment_a/sky130/run_sky130.py
uv run python experiments/experiment_a/sky130/run_followup.py
```

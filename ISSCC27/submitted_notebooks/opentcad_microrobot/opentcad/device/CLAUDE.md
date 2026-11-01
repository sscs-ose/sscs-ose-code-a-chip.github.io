# device — Claude Code Context

## Purpose
Layer 3. Wraps DEVSIM for drift-diffusion simulation. Takes MeshField, returns IV curves.

## Files
- solver.py          — DeviceSolver class. Phase 0 implementation target.
- models/mobility.py — Lombardi, Klaassen, Canali models as DEVSIM node_model expressions.
- models/recombination.py — SRH, Auger as DEVSIM node_model expressions.
- models/contacts.py — Ohmic, Schottky boundary conditions.

## DEVSIM Conventions
- Coordinates in cm (DEVSIM CGS). MeshField is in um. Convert: um * 1e-4 = cm.
- Doping in cm^-3 (no conversion needed).
- DEVSIM device name: use meshfield.metadata["structure_name"].
- Use ds.create_gmsh_mesh() for meshes from Gmsh.
- Reference: https://devsim.net and devsim/testing/diode_2d.py in DEVSIM repo.

## Phase 0 Implementation Order
1. _convert_meshfield(): build DEVSIM mesh from MeshField grid
2. _setup_equations(): Poisson + DD equations, constant mobility
3. solve_equilibrium(): Gummel decoupled solver
4. iv_sweep(): voltage ramp with convergence handling

## Tests
pytest tests/device/ -v -m requires_devsim

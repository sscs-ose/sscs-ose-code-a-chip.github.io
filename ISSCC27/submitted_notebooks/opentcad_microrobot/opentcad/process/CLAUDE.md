# process — Claude Code Context

## Purpose
Layers 1-2. Topography simulation (ViennaPS) and doping simulation (FiPy + Iradina).

## Subdirectories
- topography/  — ViennaPS wrappers for etch, deposition, oxidation (Phase 1)
- doping/      — Implant (Pearson IV + Iradina) and diffusion (FiPy) (Phase 2)
- data/        — Pearson IV parameter tables (YAML), diffusivity tables

## Key Interfaces
Input:  MeshField from geometry layer
Output: MeshField with evolved topography and/or doping profiles
Bridge: process MeshField → bridge/process_to_device.py → device MeshField

## Topography Backend Conventions
- Uses `viennals` (ViennaLS) directly as the level-set backend. Do NOT
  import `viennaps` in the same process on macOS — the current 4.6 wheel
  statically links VTK and its duplicate vtkCocoa* classes collide with
  viennals's copy, segfaulting on any real level-set operation. Once
  ViennaPS ships a fixed macOS wheel we plug it back in as a source of
  physical process models (SF6O2Etching, MultiParticleProcess, …).
- All distances in um.
- Level-set domain: `viennals.d2.Domain(bounds, boundary_conditions, gridDelta)`.
- Deposit / etch: `GeometricAdvect` with `SphereDistribution(±thickness)`
  — Minkowski dilation for conformal deposit, erosion for isotropic etch.
- Recipe DSL: `opentcad.process.topography.Recipe`
  — `.deposit(material, thickness_um)`, `.etch(depth_um)`, `.oxidize(...)`.
- Level-set → MeshField: `topography_to_meshfield(state, mesh_size_um)`.
  Extracts each layer's top polyline via `ToSurfaceMesh`, hands the
  resulting polygons to gmsh for a triangular mesh tagged per material.

## Diffusion Conventions
- FiPy mesh from MeshField: fipy.GmshImporter2D or manual CellVariable construction
- All concentrations in cm^-3 (same as MeshField)
- Time in seconds; temperature in Kelvin
- Diffusivity in cm^2/s

## Tests
pytest tests/process/ -v
Slow tests (ViennaPS): pytest tests/process/ -v -m requires_viennaps
Fast tests (ViennaLS-backed topography): pytest tests/process/ -v

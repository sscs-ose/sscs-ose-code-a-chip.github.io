# bridge — Claude Code Context

## Purpose
THE core novel contribution. Connects process simulation output to device simulation input.
No existing open source project does this. See full design rationale below.

## Files
- field_interpolator.py  — Hybrid RBF+NN doping field transfer. IMPLEMENTED.
- process_to_device.py   — Full bridge pipeline (Phase 2). Create this file.
- region_tagger.py       — Extract material polygons from ViennaPS level-set (Phase 2).

## The Translation Problem
After process sim (ViennaPS + FiPy), we have:
  - ViennaPS level-set: implicit material boundary representation
  - FiPy process mesh: coarse, PDE-optimized, with Nd/Na fields

Device sim (DEVSIM) needs:
  - Explicit mesh conforming to material interfaces
  - Nd/Na interpolated onto the NEW device mesh
  - Named contact tags

## Junction Sharpness
The critical numerical issue: naive interpolation smears junctions by 1-2 elements.
Fix: RBF for bulk, nearest-neighbor within 30nm of junction.
Test: pytest tests/bridge/test_field_interpolator.py::test_junction_depth_preserved
Criterion: <5% junction depth error for Gaussian profile σ=50nm.

## Tests
pytest tests/bridge/ -v
Key test: test_junction_depth_preserved (Phase 2 exit criterion)

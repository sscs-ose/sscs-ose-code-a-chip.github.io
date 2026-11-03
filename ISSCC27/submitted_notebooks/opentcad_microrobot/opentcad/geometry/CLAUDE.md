# geometry — Claude Code Context

## Purpose
Layer 0. Defines device structure via DSL, generates meshes via Gmsh, produces MeshField.

## Files
- formats.py   — MeshField, Material enum, ContactTag. THE central data contract. Never modify lightly.
- structure.py — Structure class: the semiconductor geometry DSL.
- mesh.py      — Gmsh mesh generation. Gmsh uses mm; all inputs/outputs here in um.
- dsl.py       — Convenience constructors (mosfet_2d, pn_junction_1d) — create in Phase 0.

## Rules
1. MeshField is the ONLY object that leaves this module.
2. All coordinates in um. Gmsh conversion: um * 1e-3 = mm.
3. Material region IDs must be Material enum integers. No string region labels.
4. Mesh refinement must be finer at material interfaces.

## Tests
pytest tests/geometry/ -v   (no devsim or viennaps required)

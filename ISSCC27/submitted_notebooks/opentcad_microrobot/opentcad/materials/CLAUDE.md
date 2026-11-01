# materials — Claude Code Context

## Purpose
Layer 4. YAML material parameter database + calibration infrastructure.

## Files
- database.py      — load_material(symbol) → MaterialParams. IMPLEMENTED.
- calibration.py   — Parameter optimizer against measured IV data (Phase 3).
- params/Si.yaml   — Silicon parameters with literature citations. IMPLEMENTED.
- params/SiO2.yaml — Create in Phase 0.
- params/Si3N4.yaml — Create in Phase 1.
- params/hackerfab/ — Process-specific calibrated variants.

## YAML Schema Rules
Every parameter entry must have:
  - The value
  - A comment with units: # [cm^-3], # [eV], # [cm^2/Vs]
  - A Ref: citation (author, year, journal) for non-obvious values
  - An uncertainty_percent or uncertainty_abs where known

## Adding a New Material
1. Create params/{Symbol}.yaml following Si.yaml as template
2. Add to MATERIAL_NAMES in geometry/formats.py
3. Add Material enum entry in geometry/formats.py
4. Add test in tests/materials/test_database.py

## Tests
pytest tests/materials/ -v   (pure Python, no external deps)

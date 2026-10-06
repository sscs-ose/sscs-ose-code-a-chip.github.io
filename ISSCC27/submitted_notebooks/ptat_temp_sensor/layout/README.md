# Physical implementation and sign-off

The Code-a-Chip ISSCC 2027 rules encourage, but do not require, a final layout.
This directory therefore uses a strict evidence rule: **no DRC/LVS/PEX PASS is
claimed until the corresponding artifacts are retained here.**

## Intended physical boundary

The layout target is the PTAT sensing pair plus the PMOS mirror distribution.
`IREF` is an external bias input in the present release architecture; the
ideal current source used in the characterization testbench is not represented
as an on-chip current-reference circuit.

## Matching plan

- Keep the equal PMOS mirror output devices identical, symmetric, and adjacent.
- Use identical orientation and surroundings for matched PMOS devices.
- Use dummies at array edges where an array implementation is used.
- Keep the two NMOS sensing branches locally symmetric while preserving the
  intentional 1:8 effective width/current-density ratio.
- Route `pref`, `v1`, and `v2` compactly and symmetrically.
- Add well/substrate contacts and guard structures according to SKY130 rules.
- Keep sensitive PTAT nodes away from noisy digital routing.

## Sign-off evidence contract

When a layout is added, retain:

- `ptat_core.gds`
- `results/drc.json` with status PASS and zero unresolved violations
- `results/lvs.json` with status PASS and the compared top-cell names
- `results/ptat_core_pex.spice`
- post-layout temperature/calibration results generated from that extracted netlist

Status command:

    python physical_verification.py

Future tapeout/sign-off gate:

    python physical_verification.py --require-layout

The second command intentionally fails until all physical evidence exists.

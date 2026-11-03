# Final-layout GDS and report images

- control-storage.gds: exact copy of the frozen control/storage-tier GDS.
- compute.gds: exported directly from the final frozen compute-tier DEF, merged with the recorded SKY130 HD standard-cell GDS.
- L0.def / L1.def: unchanged frozen sources used for readback checks.
- result.json: conversion scope and input/output identities.
- inputs.json, export-technology.lyt and export/render logs/receipts: source identities and actual commands.

Both layouts have one top cell, a 1 × 1 mm boundary, nonempty referenced cells, matching per-master DEF instance counts and matching physical pin rectangles. These are export/readback checks. Existing routing, functional and timing evidence remains in evidence/ and portability/. Independent GDS DRC/LVS remains future work.

Figure 2 uses raw KLayout renders in data/gds/. Full-die views share the same scale and orientation; the two crops use explicit micron-coordinate boxes. Palette, visible layers, source GDS hashes and raw PNG hashes are recorded in data/gds/render.json. Explanatory arrows, interface-window boxes and scale bars are composed by review.gds_layout().

To regenerate only the raw graphics with KLayout 0.30.12, run from the package root:

    klayout -zz -r tools/render_gds.py

To compose Figure 2 from the saved graphics:

    python -c 'import review; review.gds_layout()'

The KLayout script uses the standalone LayoutView destructor in batch mode. API reference: https://www.klayout.de/doc-qt5/code/class_LayoutView.html

The export used the original flow def2stream.py identified in inputs.json; its recorded command and technology paths preserve local provenance. Full physical-flow regeneration remains a separate packaging task.

The two GDS files embed SKY130 HD standard-cell geometry under the existing Apache-2.0 license; see ../../licenses/SKY130-HD-Apache-2.0.txt. Project-owned placement/routing and manuscript materials use Apache-2.0 following the author's 2026-10-31 release confirmation. See ../../LICENSE-SCOPE.md and ../../THIRD-PARTY-NOTICES.md.

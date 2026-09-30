#!/usr/bin/env bash
# Render the HSKEM full-chip Run17 GDS (not part of the Colab path: 60 MB input).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PKG="$ROOT/../report/orfs_a3_p82/signoff/a3_r16_v14_run17_evidence_r1/final_design"
TMP=$(mktemp -d); gunzip -c "$PKG/6_final.gds.gz" > "$TMP/chip.gds"
klayout -zz -r "$ROOT/scripts/render_gds.py" -rd gds="$TMP/chip.gds" \
        -rd png="$ROOT/results/fullchip/fullchip_layout.png" -rd px=2400
rm -rf "$TMP"

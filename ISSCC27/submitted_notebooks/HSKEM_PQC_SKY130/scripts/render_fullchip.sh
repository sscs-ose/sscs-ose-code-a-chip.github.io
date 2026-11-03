#!/usr/bin/env bash
# Render the signed-off HSKEM full-chip GDS (not part of the Colab path: the layout is not published).
# usage: FULLCHIP_GDS=<6_final.gds of the chip run> scripts/render_fullchip.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GDS="${FULLCHIP_GDS:-$ROOT/../report/orfs_chip_v2_r2_a3grt/final_from_h1r/results/6_final.gds}"
klayout -zz -r "$ROOT/scripts/render_gds.py" -rd gds="$GDS" \
        -rd png="$ROOT/results/fullchip/fullchip_layout.png" -rd px=2400

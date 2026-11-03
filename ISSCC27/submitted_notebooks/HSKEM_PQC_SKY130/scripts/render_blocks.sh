#!/usr/bin/env bash
# Render layout.png for every finished ORFS point (needs KLayout).
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for g in "$ROOT"/results/asic/*/6_final.gds; do
  [ -f "$g" ] || continue
  klayout -zz -r "$ROOT/scripts/render_gds.py" -rd gds="$g" -rd png="$(dirname "$g")/layout.png" -rd px=1200 -rd layers=68/20,69/20,70/20,71/20,72/20
done

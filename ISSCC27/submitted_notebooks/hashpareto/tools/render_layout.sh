#!/usr/bin/env bash
# Render one GDS to PNG inside the LibreLane devshell (klayout batch mode).
# usage: tools/render_layout.sh <gds_in> <png_out> [width]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IN="$1"
OUT="$2"
W="${3:-1600}"
if [ ! -f "$IN" ]; then echo "missing GDS: $IN" >&2; exit 1; fi
mkdir -p "$(dirname "$OUT")"
bash "$ROOT/tools/run_librelane.sh" \
  "klayout -b -r $ROOT/tools/render_gds.rb -rd input=$IN -rd output=$OUT -rd width=$W"
ls -la "$OUT"

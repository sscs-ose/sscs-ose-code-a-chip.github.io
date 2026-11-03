#!/usr/bin/env bash
# Slim a FINISHED librelane run: delete reproducible intermediates (NN-* step
# dirs + tmp), keep final/ + flow.log/resolved.json/warning/error logs.
# Skips runs that have not produced final/metrics.json (in progress/failed).
# usage: tools/slim_run.sh <run_dir>
set -uo pipefail
run="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
[ -d "$run" ] || { echo "no such run: $run"; exit 1; }
if [ ! -f "$run/final/metrics.json" ]; then
  echo "skip (no final/metrics.json): $run"
  exit 2
fi
before() { du -sh "$run" | cut -f1; }
b0=$(before)
rm -rf "$run"/[0-9][0-9]-* "$run"/tmp
echo "slimmed: $run  $b0 -> $(before)"
echo "  kept: final/=$(du -sh "$run/final" | cut -f1), $(ls "$run" | tr '\n' ' ')"
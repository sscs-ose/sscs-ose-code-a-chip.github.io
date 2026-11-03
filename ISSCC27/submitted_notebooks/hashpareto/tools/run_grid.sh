#!/usr/bin/env bash
# Phase 2 grid driver (detached, self-healing): U16@300 first, then U1/U2/U4/U8@100.
# U16 is RESUMED from the last routing step if a grid300 run already exists
# (survives a killed/suspended batch). Otherwise a fresh run starts.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RV="$ROOT/tools/run_variant.sh"
echo "GRID START $(date)"
# --- U16 @ 300 ns : resume if a partial grid300 exists ----------------------
U16RUN="$ROOT/flow/variants/u16/runs/grid300"
if [ -d "$U16RUN" ] && [ ! -f "$U16RUN/final/metrics.json" ]; then
  echo "=== resuming u16 grid300 (from OpenROAD.DetailedRouting) at $(date) ==="
  if bash "$RV" 16 grid300 --from OpenROAD.DetailedRouting; then
    echo "=== u16 [grid300] OK at $(date) ==="
  else
    echo "=== u16 [grid300] FAILED rc=$? at $(date) ==="
  fi
else
  if bash "$RV" 16 grid300; then
    echo "=== u16 [grid300] OK at $(date) ==="
  else
    echo "=== u16 [grid300] FAILED rc=$? at $(date) ==="
  fi
fi
# --- U1/U2/U4/U8 @ 100 ns : fresh common-clock runs -------------------------
for u in 1 2 4 8; do
  echo "=== launching u$u tag=grid100 at $(date) ==="
  if bash "$RV" "$u" grid100; then
    echo "=== u$u [grid100] OK at $(date) ==="
  else
    echo "=== u$u [grid100] FAILED rc=$? at $(date) ==="
  fi
done
echo "GRID ALL DONE $(date)"
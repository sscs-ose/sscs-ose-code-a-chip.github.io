#!/usr/bin/env bash
# BEOL + OFFGRID DRC of a GDS with the unmodified ORFS sky130hd.lydrc rules, run as eight part decks
# (split_beol_deck.py), one fresh KLayout process per part, so that a chip whose deep-mode run outgrows the
# memory can still be checked. Every part writes its own report; the merged counts go to drc_result.json.
#   usage: run_split_drc.sh <in.gds> <output dir> [--full]
# --full also runs the unsplit deck once, for an equivalence check with compare_reports.py.
# Environment: ORFS_ROOT (default /opt/eda/orfs-6101364b), KLAYOUT (default klayout).
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
GDS="${1:?gds}"; OUT="${2:?output dir}"; FULL="${3:-}"
ORFS="${ORFS_ROOT:-/opt/eda/orfs-6101364b}"; KL="${KLAYOUT:-klayout}"
DECK="$ORFS/flow/platforms/sky130hd/drc/sky130hd.lydrc"
mkdir -p "$OUT"
python3 "$HERE/split_beol_deck.py" "$DECK" "$OUT/decks" || exit 2
for d in "$OUT"/decks/p*.lydrc; do
  p=$(basename "$d" .lydrc)
  /usr/bin/time -f "%e %M" -o "$OUT/$p.time" "$KL" -b -rd in_gds="$GDS" -rd report_file="$OUT/$p.lyrdb" -r "$d" > "$OUT/$p.log" 2>&1
  echo "$p rc=$? items=$(grep -c '<item>' "$OUT/$p.lyrdb" 2>/dev/null) s,kB=$(cat "$OUT/$p.time")"
done
if [ "$FULL" = --full ]; then
  sed -e 's/^FEOL    = true/FEOL    = false/' "$DECK" > "$OUT/decks/full_beol_offgrid.lydrc"
  /usr/bin/time -f "%e %M" -o "$OUT/full.time" "$KL" -b -rd in_gds="$GDS" -rd report_file="$OUT/full.lyrdb" \
     -r "$OUT/decks/full_beol_offgrid.lydrc" > "$OUT/full.log" 2>&1
  echo "full rc=$? items=$(grep -c '<item>' "$OUT/full.lyrdb" 2>/dev/null) s,kB=$(cat "$OUT/full.time")"
  python3 "$HERE/compare_reports.py" "$OUT/full.lyrdb" "$OUT"/p*.lyrdb | tee "$OUT/equivalence.txt"
fi

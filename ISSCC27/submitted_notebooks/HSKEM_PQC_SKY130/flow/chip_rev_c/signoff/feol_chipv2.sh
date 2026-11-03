#!/usr/bin/env bash
# Chip v2 FEOL DRC, the same procedure as the old chip (codeachip results/fullchip/feol_drc.json):
#   1. scripts/implant_fix.py closes the sub-rule nsdm/psdm/npc gaps inside the OpenRAM macros of the final
#      GDS (mask-preparation step), and scripts/verify_untouched.py proves that nothing else changed;
#   2. the FEOL section of the ORFS sky130hd.lydrc deck runs as the seven split decks of the old chip
#      (P1-P4, A2, B, C; rule vpp.5 left out because the vpp layer 82/64 is empty) on the final GDS and on
#      the fixed GDS, at most four KLayout jobs at a time, each timed with /usr/bin/time -v.
# The split decks are copied unchanged from the old run (/var/tmp/feol_drc_20260930); a gate checks that
# together they enable every FEOL output line of the parent deck exactly once, except vpp.5.
# usage: feol_chipv2.sh <final GDS> <output dir>
set -uo pipefail
readonly GDS_IN="${1:?final GDS}" OUT="${2:?output dir}"
readonly SCRIPTS=/mnt/d/TKVM_ATTT_2026_test/codeachip/scripts
readonly OLD=/var/tmp/feol_drc_20260930
readonly PARTS="P4 P3 P1 P2 B C A2"
readonly MAXJOBS=4
[[ -s "$GDS_IN" && ! -e "$OUT/FEOL_DONE" ]] || { echo "CHIPV2_FEOL_BLOCKED=args"; exit 64; }
if pgrep -x 'openroad|klayout' >/dev/null; then echo "CHIPV2_FEOL_BLOCKED=active_eda"; exit 66; fi
mkdir -p "$OUT/decks" "$OUT/orig" "$OUT/fixed"
(( $(df -Pk "$OUT" | awk 'NR==2 {print $4}') >= 10*1024*1024 )) || { echo "CHIPV2_FEOL_BLOCKED=disk"; exit 67; }
cp "$OLD/feol.lydrc" "$OUT/decks/feol.lydrc"
for p in $PARTS; do cp "$OLD/rest_$p.lydrc" "$OUT/decks/$p.lydrc"; done
python3 - "$OUT/decks" $PARTS <<'PY' || { echo "CHIPV2_FEOL_BLOCKED=deck_cover"; exit 68; }
import re, sys
from collections import Counter
from pathlib import Path
d, parts = Path(sys.argv[1]), sys.argv[2:]
parent = (d / 'feol.lydrc').read_text().split('\n')
assert re.search(r'^FEOL    = true', '\n'.join(parent), re.M)
feol, inside = set(), False
for i, l in enumerate(parent):
    if re.match(r'^if FEOL\b', l): inside = True
    elif re.match(r'^end #FEOL', l): inside = False
    elif inside and '.output(' in l and not l.lstrip().startswith('#'): feol.add(i)
cover = Counter()
for p in parts:
    lines = (d / f'{p}.lydrc').read_text().split('\n')
    assert len(lines) == len(parent), p
    for i, (a, b) in enumerate(zip(parent, lines)):
        if a != b:
            assert b == '# [split] ' + a, (p, i + 1)
        elif i in feol:
            cover[i] += 1
missing = sorted(i + 1 for i in feol if cover[i] == 0)
twice = sorted(i + 1 for i in feol if cover[i] > 1)
vpp5 = [i + 1 for i in feol if 'output("vpp.5"' in parent[i]]
assert twice == [], twice
assert missing == vpp5, (missing, vpp5)
print(f'CHIPV2_FEOL_DECK_COVER=PASS feol_output_lines={len(feol)} enabled_once={len(feol) - len(missing)} '
      f'left_out={missing} (vpp.5)')
PY
readonly FIXED="$OUT/chip_v2_final7_implantfix.gds"
sha256sum "$GDS_IN" "$SCRIPTS/implant_fix.py" "$SCRIPTS/verify_untouched.py" "$OUT"/decks/*.lydrc > "$OUT/INPUT_SHA256SUMS.txt"
echo "CHIPV2_FEOL_STEP IMPLANT_FIX $(date -Is)"
/usr/bin/time -v klayout -b -rd in_gds="$GDS_IN" -rd out_gds="$FIXED" -r "$SCRIPTS/implant_fix.py" \
  > "$OUT/implant_fix.log" 2> "$OUT/implant_fix.time" || { echo "CHIPV2_FEOL_FAIL implant_fix"; tail -5 "$OUT/implant_fix.log"; exit 1; }
[[ -s "$FIXED" ]] || { echo "CHIPV2_FEOL_FAIL implant_fix_no_output"; tail -5 "$OUT/implant_fix.log"; exit 1; }
tail -4 "$OUT/implant_fix.log"
echo "CHIPV2_FEOL_STEP VERIFY_UNTOUCHED $(date -Is)"
klayout -b -rd a="$GDS_IN" -rd b="$FIXED" -r "$SCRIPTS/verify_untouched.py" > "$OUT/verify_untouched.log" 2>&1
tail -3 "$OUT/verify_untouched.log"
grep -q 'RESULT: UNTOUCHED OK' "$OUT/verify_untouched.log" || { echo "CHIPV2_FEOL_FAIL verify_untouched"; exit 1; }
grep -q 'vpp 82/64 shapes: 0$' "$OUT/verify_untouched.log" || { echo "CHIPV2_FEOL_FAIL vpp_not_empty"; exit 1; }
sha256sum "$FIXED" >> "$OUT/INPUT_SHA256SUMS.txt"
echo "CHIPV2_FEOL_STEP DRC_JOBS $(date -Is)"
run_job() {   # <set> <gds> <part>
  /usr/bin/time -v klayout -b -rd in_gds="$2" -rd report_file="$OUT/$1/chip_$3.lyrdb" -r "$OUT/decks/$3.lydrc" \
    > "$OUT/$1/chip_$3.log" 2> "$OUT/$1/chip_$3.time"
  echo "CHIPV2_FEOL_JOB_END=$1/$3 rc=$? items=$(grep -c '<item>' "$OUT/$1/chip_$3.lyrdb" 2>/dev/null) $(date -Is)"
}
for set in fixed orig; do
  gds="$FIXED"; [[ "$set" == orig ]] && gds="$GDS_IN"
  for p in $PARTS; do
    while (( $(jobs -rp | wc -l) >= MAXJOBS )); do sleep 20; done
    echo "CHIPV2_FEOL_JOB_START=$set/$p $(date -Is)"
    run_job "$set" "$gds" "$p" &
    sleep 5
  done
done
wait
ok=1
for set in fixed orig; do for p in $PARTS; do
  grep -q 'Exit status: 0' "$OUT/$set/chip_$p.time" && [[ -s "$OUT/$set/chip_$p.lyrdb" ]] || { ok=0; echo "CHIPV2_FEOL_JOB_FAILED=$set/$p"; }
done; done
(( ok )) && touch "$OUT/FEOL_DONE"
echo "CHIPV2_FEOL_END ok=$ok $(date -Is)"

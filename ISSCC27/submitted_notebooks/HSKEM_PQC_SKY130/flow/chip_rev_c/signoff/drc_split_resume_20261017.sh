#!/usr/bin/env bash
# Chip v2 sign-off BEOL + OFFGRID DRC with the unmodified ORFS sky130hd.lydrc rules, run as eight part decks
# (drc_split/make_split_decks.py). In one run the deep-mode deck keeps every derived layer until the end and
# outgrew the WSL memory at rule m1.5 (2026-10-05 01:13, 2026-10-06 08:2x); the deck's tiled mode holds the
# chip flat and died earlier, at li.3 (2026-10-06 09:2x). Each part is a fresh KLayout process in the deck's
# own deep mode with threads(4); parts run one after another, a failed part is recorded and the rest still
# run. The result is PASS only when every part finished and wrote its report.
# usage: signoff_drc_split.sh run <final GDS> <output dir>
set -uo pipefail
readonly ACTION="${1:?run}" GDS_IN="${2:?final GDS}" OUT="${3:?output dir}"
readonly ORFS=/opt/eda/orfs-6101364b
readonly DECK="$ORFS/flow/platforms/sky130hd/drc/sky130hd.lydrc"
readonly KLAYOUT=/usr/bin/klayout WRAPPER="$ORFS/flow/scripts/klayout.sh"
readonly SPLIT=/mnt/d/TKVM_ATTT_2026_test/chip_v2/drc_split/make_split_decks.py
readonly ORDER="p3_m1 p2_ct p1_li p4_via_m2 p5_via2_m3 p6_via3_m4 p7_via4_m5_nsm_pad p8_offgrid"
[[ "$ACTION" == run && -s "$GDS_IN" && ! -e "$OUT/drc_result.json" ]] || { echo "CHIPV2_DRC_BLOCKED=args"; exit 64; }
if pgrep -x 'openroad|klayout' >/dev/null; then echo "CHIPV2_DRC_BLOCKED=active_eda"; exit 66; fi
cp "$OUT/INPUT_SHA256SUMS.txt" "$OUT/INPUT_SHA256SUMS.prev.txt" 2>/dev/null || true
mkdir -p "$OUT"
(( $(df -Pk "$OUT" | awk 'NR==2 {print $4}') >= 15*1024*1024 )) || { echo "CHIPV2_DRC_BLOCKED=disk"; exit 67; }
python3 "$SPLIT" "$DECK" "$OUT/decks" || { echo "CHIPV2_DRC_BLOCKED=split"; exit 68; }
readonly GDS_SHA="$(sha256sum "$GDS_IN" | cut -d ' ' -f1)"
sha256sum "$GDS_IN" "$DECK" "$KLAYOUT" "$WRAPPER" "$SPLIT" "$OUT"/decks/*.lydrc > "$OUT/INPUT_SHA256SUMS.txt"
echo "CHIPV2_DRC_START|mode=deep_split8|gds_sha256=$GDS_SHA|start=$(date -Is)"
for p in $ORDER; do
  # (resume copy 2026-10-17) a part that already finished with rc 0 and a report on the SAME inputs is kept
  if [[ -s "$OUT/$p.lyrdb" && "$(cat "$OUT/$p.rc" 2>/dev/null)" == 0 ]] && cmp -s "$OUT/INPUT_SHA256SUMS.prev.txt" "$OUT/INPUT_SHA256SUMS.txt"; then echo "CHIPV2_DRC_PART_KEPT=$p items=$(grep -c "<item>" "$OUT/$p.lyrdb")"; continue; fi
  echo "CHIPV2_DRC_PART_START=$p $(date -Is)"
  KLAYOUT_CMD="$KLAYOUT" "$WRAPPER" -zz -rd in_gds="$GDS_IN" -rd report_file="$OUT/$p.lyrdb" \
    -r "$OUT/decks/$p.lydrc" > "$OUT/$p.log" 2>&1
  rc=$?
  echo "$rc" > "$OUT/$p.rc"
  echo "CHIPV2_DRC_PART_END=$p rc=$rc items=$(grep -c '<item>' "$OUT/$p.lyrdb" 2>/dev/null || echo none) $(date -Is)"
done
python3 - "$OUT" "$GDS_SHA" $ORDER <<'PY'
import json, sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
out, sha, order = Path(sys.argv[1]), sys.argv[2], sys.argv[3:]
manifest = json.loads((out / 'decks' / 'split_manifest.json').read_text())
parts, total, failed = {}, Counter(), []
for p in order:
    rc = int((out / f'{p}.rc').read_text())
    rpt = out / f'{p}.lyrdb'
    if rc != 0 or not rpt.is_file():
        failed.append(p); parts[p] = {'rc': rc, 'report': rpt.is_file()}; continue
    root = ET.parse(rpt).getroot()
    assert root.tag == 'report-database' and root.findtext('top-cell') == 'trustedge_asic_core', p
    cats = Counter(i.findtext('category').strip("'") for i in root.find('items').findall('item'))
    names = set(manifest['parts'][p]['rule_names'])
    if names:
        assert set(cats) <= names, (p, set(cats) - names)
    parts[p] = {'rc': 0, 'drc_items': sum(cats.values()), 'by_category': dict(cats)}
    total.update(cats)
result = {'execution': 'PASS' if not failed else 'INCOMPLETE', 'top_cell': 'trustedge_asic_core',
          'drc_items': sum(total.values()), 'by_category': dict(total), 'failed_parts': failed,
          'deck_scope': 'ORFS sky130hd.lydrc rules unchanged (BEOL and OFFGRID sections, FEOL checked '
                        'separately), deep mode with threads(4), run as eight part decks that partition the '
                        'BEOL rule lines (scripts/split_beol_deck.py of the submission)',
          'parts': parts, 'gds_sha256': sha}
(out / 'drc_result.json').write_text(json.dumps(result, indent=2) + '\n')
print('CHIPV2_DRC_RESULT=' + json.dumps({k: result[k] for k in ('execution', 'drc_items', 'by_category',
                                         'failed_parts')}, separators=(',', ':')), flush=True)
PY
sha256sum "$OUT"/*.lyrdb "$OUT"/*.log "$OUT/drc_result.json" > "$OUT/OUTPUT_SHA256SUMS.txt" 2>/dev/null
echo "CHIPV2_DRC_DONE end=$(date -Is)"

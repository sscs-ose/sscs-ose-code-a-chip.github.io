#!/usr/bin/env bash
# Verify the two lane designs really used different RTL/netlists, and check GDS.
F=$HOME/orfs-src/flow
R=$F/results/nangate45
echo "== source wrappers =="
grep -h 'fa_lane #' $F/designs/src/fa_lane_b/*.v
grep -h 'fa_lane #' $F/designs/src/fa_lane_e/*.v
echo "== synthesized netlists (1_synth.v) =="
for d in fa_lane_b_top fa_lane_e_top; do
  n=$(grep -cE '^ [A-Z][A-Z0-9_]+_X[0-9]+ ' $R/$d/base/1_synth.v 2>/dev/null || echo NA)
  fa=$(grep -c ' FA_X1 ' $R/$d/base/1_synth.v 2>/dev/null || echo NA)
  echo "$d cells=$n FA=$fa md5=$(md5sum $R/$d/base/1_synth.v 2>/dev/null | cut -d' ' -f1)"
done
echo "== final netlists =="
for d in fa_lane_b_top fa_lane_e_top; do
  n=$(grep -cE '^ [A-Z][A-Z0-9_]+_X[0-9]+ ' $R/$d/base/6_final.v)
  fa=$(grep -c ' FA_X1 ' $R/$d/base/6_final.v)
  echo "$d cells=$n FA=$fa"
done
echo "== GDS / outputs =="
ls -la $R/fa_lane_b_top/base/6_final.gds $R/fa_lane_e_top/base/6_final.gds 2>&1
ls $R/fa_lane_b_top/base/ | tr '\n' ' '
echo
echo "== areas =="
grep -m2 -iE 'Design area|Chip area' $F/reports/nangate45/fa_lane_b_top/base/6_finish.rpt
grep -m2 -iE 'Design area|Chip area' $F/reports/nangate45/fa_lane_e_top/base/6_finish.rpt

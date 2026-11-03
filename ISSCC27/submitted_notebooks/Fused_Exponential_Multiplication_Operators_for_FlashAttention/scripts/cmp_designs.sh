#!/usr/bin/env bash
S=$HOME/flashattn_expmul/sim
F=$HOME/orfs-src/flow/results/nangate45
echo "== md5 =="
md5sum $S/fa_lane_top/6_final.v $S/fa_lane_b_top/6_final.v
echo "== instances =="
for d in fa_lane_top fa_lane_b_top; do
  n=$(grep -cE '^ [A-Z][A-Z0-9_]+_X[0-9]+ ' $F/$d/base/6_final.v)
  fa=$(grep -c ' FA_X1 ' $F/$d/base/6_final.v)
  mux=$(grep -c ' MUX2_X1 ' $F/$d/base/6_final.v)
  echo "$d instances=$n FA=$fa MUX2=$mux"
done
echo "== vcd size =="
ls -la $S/fa_lane_top/lane.vcd $S/fa_lane_b_top/lane.vcd

#!/usr/bin/env bash
F=$HOME/orfs-src/flow
echo "== exp wrapper =="
grep -n 'fa_lane #' $F/designs/src/fa_lane_exp/fa_lane_top.v
echo "== base wrapper =="
grep -n 'fa_lane #' $F/designs/src/fa_lane_base/fa_lane_top.v
echo "== areas =="
grep -iE 'Design area' $F/reports/nangate45/fa_lane_top/base/6_finish.rpt | head -2
grep -iE 'Design area' $F/reports/nangate45/fa_lane_b_top/base/6_finish.rpt | head -2
echo "== netlist mux count (exp) =="
grep -c 'MUX2_X1' $F/results/nangate45/fa_lane_top/base/6_final.v

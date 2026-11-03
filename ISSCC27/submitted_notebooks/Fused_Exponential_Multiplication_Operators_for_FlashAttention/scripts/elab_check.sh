#!/usr/bin/env bash
F=$HOME/orfs-src/flow
for d in fa_lane_exp fa_lane_base; do
  echo "=== $d ==="
  yosys -p "read_verilog $F/designs/src/$d/*.v; hierarchy -check -top fa_lane_top; proc; opt; stat" 2>&1 | grep -E "Number of cells|Number of wires" | tail -2
done

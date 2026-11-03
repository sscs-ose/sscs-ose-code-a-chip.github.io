#!/usr/bin/env bash
# Gate-level VCD for the bf16 lane designs.
set -eu
W=$HOME/flashattn_expmul
F=$HOME/orfs-src/flow
LIB=$F/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib

python3 "$W/scripts/gen_cell_models.py" "$LIB" "$W/sim/nangate45_cells.v"

for spec in "fa_bf16_b_top:$F/results/nangate45/fa_bf16_b_top/base" \
            "fa_bf16_e_top:$F/results/nangate45/fa_bf16_e_top/base"; do
  TOP=${spec%%:*}
  DIR=${spec##*:}
  OUT=$W/sim/$TOP
  mkdir -p "$OUT"
  cp "$DIR/6_final.v" "$DIR/6_final.sdc" "$DIR/6_final.spef" "$OUT"/
  cd "$OUT"
  if ! iverilog -g2005 -DTOP=$TOP -o sim \
      "$W/sim/nangate45_cells.v" "$W/rtl/tb_lane_gate16.v" 6_final.v > iverilog.log 2>&1; then
    echo "iverilog failed for $TOP"; tail -6 iverilog.log; exit 1
  fi
  timeout 1200 vvp sim > vvp.log 2>&1 || true
  ls -la lane.vcd
  echo "finished $TOP"
done

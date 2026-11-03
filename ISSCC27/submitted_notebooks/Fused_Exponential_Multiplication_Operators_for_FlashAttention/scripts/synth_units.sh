#!/usr/bin/env bash
# ============================================================================
#  synth_units.sh -- area of the individual datapath operators (nangate45)
#  Yosys + ABC, one small module per run (fast).
# ============================================================================
set -u
W=/work
LIB=/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
OUT=$W/syn/units
mkdir -p "$OUT"

run() {
  local top=$1
  local tag=$2
  local pre=$3
  yosys -q -p "
    read_verilog -I $W/rtl $W/rtl/fp32_mul.v $W/rtl/fp32_add.v $W/rtl/exp_pwl.v $W/rtl/expmul.v
    $pre
    synth -top $top -flatten
    abc -liberty $LIB
    opt_clean
    tee -o $OUT/$tag.stat stat -liberty $LIB
  " > "$OUT/$tag.log" 2>&1
  local area=$(grep "Chip area" "$OUT/$tag.stat" 2>/dev/null | tail -1 | awk '{print $NF}')
  local cells=$(grep "Number of cells" "$OUT/$tag.stat" 2>/dev/null | tail -1 | awk '{print $NF}')
  echo "$tag area=$area cells=$cells"
}

run fp32_mul_c mul ""
run fp32_add_c add ""
run exp_pwl exp_pwl ""
run rcp_pwl rcp ""
run expmul expmode0 "chparam -set MODE 0 expmul"
run expmul expmode1 "chparam -set MODE 1 expmul"

#!/usr/bin/env bash
# ============================================================================
#  power_units.sh -- gate-level power of the primitives (OpenROAD, nangate45)
#  Activity: 0.25 input toggle rate, 0.5 duty (documented assumption).
# ============================================================================
set -u
W=/work
LIB=/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
OUT=$W/syn/units
mkdir -p "$OUT"

for spec in "fp32_mul_c mul" "fp32_add_c add" "exp_pwl exp_pwl" "rcp_pwl rcp" "expmul expmode0"; do
  set -- $spec
  TOP=$1; TAG=$2
  PRE=""
  if [ "$TOP" = "expmul" ]; then PRE="chparam -set MODE 0 expmul"; fi
  yosys -q -p "
    read_verilog -I $W/rtl $W/rtl/fp32_mul.v $W/rtl/fp32_add.v $W/rtl/exp_pwl.v $W/rtl/expmul.v
    $PRE
    synth -top $TOP -flatten
    abc -liberty $LIB
    write_verilog -noattr $OUT/$TAG.v
  " > "$OUT/$TAG.synth.log" 2>&1
  /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit > "$OUT/$TAG.power.log" 2>&1 <<EOF
read_liberty $LIB
read_verilog $OUT/$TAG.v
link_design $TOP
set_power_activity -input -activity 0.25 -duty 0.5
report_power
EOF
  echo "--- $TAG ---"
  grep -E "Total|Internal|Switching|Leakage" "$OUT/$TAG.power.log" | head -6
done

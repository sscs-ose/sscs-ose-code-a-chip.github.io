#!/usr/bin/env bash
# Post-P&R power with gate-level VCD for base / exp lanes.
set -u
W=$HOME/flashattn_expmul
IMG=openroad/orfs:local
LIB=/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
TLEF=/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef
CLEF=/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef

for TOP in fa_lane_b_top fa_lane_e_top; do
  echo "===== $TOP ====="
  docker run --rm -v $W:/work -v $HOME/orfs-src/flow:/flow \
    -w /work/sim/$TOP \
    -e LIB=$LIB -e TECH_LEF=$TLEF -e CELL_LEF=$CLEF \
    -e NETLIST=6_final.v -e TOP=$TOP -e SDC=6_final.sdc -e SPEF=6_final.spef \
    -e VCD=lane.vcd -e SCOPE=tb/dut \
    $IMG /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad \
    -no_init -exit /work/scripts/power_vcd.tcl > $W/sim/$TOP/power.log 2>&1
  grep -E "Annotated|^Total|Chip area|Design area" $W/sim/$TOP/power.log | head -6
done

#!/usr/bin/env bash
# ============================================================================
#  synth_yosys.sh -- parameterised synthesis of fa_kernel (FP32 variants)
#  usage: synth_yosys.sh <D> <VARIANT:0=baseline,1=expmul> <MODE:0|1> <outdir>
#  Runs Yosys + ABC against the nangate45 typical library inside the ORFS
#  container; writes area/timing/cell reports and a gate-level netlist.
# ============================================================================
set -euo pipefail
D=${1:?D}; VAR=${2:?variant}; MODE=${3:?mode}; OUT=${4:?outdir}
WORK=/work
LIB=/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib

mkdir -p "$OUT"
yosys -q -p "
  read_verilog -I $WORK/rtl \
      $WORK/rtl/fp32_mul.v $WORK/rtl/fp32_add.v \
      $WORK/rtl/exp_pwl.v $WORK/rtl/expmul.v $WORK/rtl/fa_kernel.v
  chparam -set D $D -set VARIANT $VAR -set MODE $MODE fa_kernel
  synth -top fa_kernel -flatten
  abc -liberty $LIB
  opt_clean
  tee -o $OUT/stat.txt stat -liberty $LIB
  write_verilog -noattr $OUT/netlist.v
" 2>&1 | tee "$OUT/yosys.log"

echo "=== $OUT ==="
grep -E "Chip area|Number of cells|Number of wires" "$OUT/stat.txt" | tail -5

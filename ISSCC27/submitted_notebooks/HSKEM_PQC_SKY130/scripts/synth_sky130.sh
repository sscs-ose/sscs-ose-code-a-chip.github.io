#!/usr/bin/env bash
# Colab-friendly logic synthesis to the SKY130 HD library (Yosys + ABC only).
# usage: synth_sky130.sh <ntt_dp|ntt_sp|keccak_r1|keccak_s7> <clock_ns>
# Reports cell area and ABC's post-mapping combinational delay estimate.
# Post-route numbers (OpenROAD) are produced separately by run_orfs.sh.
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
V=$1; T=$2
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; R="$ROOT/rtl"
LIB="${SKY130_LIB:-$ROOT/pdk/sky130_fd_sc_hd__tt_025C_1v80.lib}"
if [ ! -f "$LIB" ]; then
  mkdir -p "$(dirname "$LIB")"
  curl -sL -o "$LIB" https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD-flow-scripts/master/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
fi
OUT="$ROOT/results/synth/${V}_${T/./p}ns"; mkdir -p "$OUT"
case $V in
  ntt_dp)    TOP=kyber_ntt_engine; DEF=""; PAR=""
             SRC="$R/kyber_pkg.sv $R/barrett_reduce.v $R/kyber_ntt_engine.sv";;
  ntt_sp)    TOP=kyber_ntt_engine; DEF="-D TRUSTEDGE_ASIC_SRAM"; PAR=""
             SRC="$R/kyber_pkg.sv $R/barrett_reduce.v $R/te_sram_models.sv $R/kyber_ntt_engine.sv";;
  keccak_r1) TOP=keccak_lane_wrapper; DEF=""; PAR="-G SERIAL_ROUND=0"
             SRC="$R/keccak_f1600_iter.sv $R/keccak_lane_wrapper.sv";;
  keccak_s7) TOP=keccak_lane_wrapper; DEF=""; PAR="-G SERIAL_ROUND=1"
             SRC="$R/keccak_f1600_iter.sv $R/keccak_lane_wrapper.sv";;
  ntt_opt_ref|ntt_opt_b1|ntt_opt_b1_w12|ntt_opt_pipe_w12)
             TOP=kyber_ntt_engine_opt; DEF=""
             case $V in
               ntt_opt_ref)      PAR="-G BARRETT_1C=0 -G PIPE_MUL=0 -G COEFF_W=16";;
               ntt_opt_b1)       PAR="-G BARRETT_1C=1 -G PIPE_MUL=0 -G COEFF_W=16";;
               ntt_opt_b1_w12)   PAR="-G BARRETT_1C=1 -G PIPE_MUL=0 -G COEFF_W=12";;
               ntt_opt_pipe_w12) PAR="-G BARRETT_1C=1 -G PIPE_MUL=1 -G COEFF_W=12";;
             esac
             SRC="$R/kyber_pkg.sv $R/barrett_reduce.v $R/barrett_reduce_1c.v $R/te_sram_models.sv $R/kyber_ntt_engine_opt.sv";;
  *) echo "unknown variant $V"; exit 2;;
esac
PS=$(python3 -c "print(int(float('$T')*1000))")
yosys -q -l "$OUT/yosys.log" -p "
  plugin -i slang
  read_slang --top $TOP $DEF $PAR $SRC
  synth -top $TOP -flatten
  dfflibmap -liberty $LIB
  abc -liberty $LIB -D $PS -script +strash;ifraig;scorr;dc2;dretime;strash;&get,-n;&dch,-f;&nf,{D};&put;buffer;upsize,{D};dnsize,{D};stime,-p
  opt_clean
  tee -o $OUT/stat.txt stat -liberty $LIB
  write_verilog -noattr $OUT/netlist.v
"
python3 - "$OUT" <<'PY'
import json, re, sys, pathlib
o = pathlib.Path(sys.argv[1]); log = (o / "yosys.log").read_text(); st = (o / "stat.txt").read_text()
area = float(re.findall(r"Chip area for (?:top )?module.*?:\s*([\d.]+)", st)[-1])
cells = int(re.findall(r"^\s*(\d+)\s+[\d.E+-]*\s*cells$|Number of cells:\s*(\d+)", st, re.M)[-1][0] or
            re.findall(r"Number of cells:\s*(\d+)", st)[-1])
delay = [float(x) for x in re.findall(r"Delay\s*=\s*([\d.]+)\s*ps", log)]
res = {"cell_area_um2": area, "cells": cells,
       "abc_comb_delay_ns": max(delay) / 1000 if delay else None}
(o / "summary.json").write_text(json.dumps(res, indent=2)); print(res)
PY

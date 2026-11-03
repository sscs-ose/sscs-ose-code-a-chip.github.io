#!/usr/bin/env bash
# Build + run the FIR DUT against a vector file pair.
#
#   build_and_run.sh <rtl.v> <module_name> <tb_icarus.v> <in.txt> <out.txt> <n_inputs> <out_width>
#
# Dispatches to:
#   * Verilator (fast, preferred when installed) via fir_tb.cpp, compiled with
#     `--prefix VFIR` so the C++ harness never needs to know the module name;
#   * Icarus Verilog (always available in the reference environment) via the
#     rendered testbench passed as <tb_icarus.v>.
#
# Both harnesses implement the same stimulus protocol, so verify_rtl.py's
# bit-exact comparison is identical either way.
#
# Licensed under the Apache License, Version 2.0. See the repo LICENSE file.
set -euo pipefail

RTL=$1
MODULE=$2
TB_V=$3
IN=$4
OUT=$5
N_IN=$6
OUT_WIDTH=$7

TB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TB_CPP="$TB_DIR/fir_tb.cpp"
WORKDIR="/tmp/pf_sim_${MODULE}"

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"

if command -v verilator >/dev/null 2>&1; then
    verilator --cc "$RTL" --top-module "$MODULE" --prefix VFIR \
        --exe "$TB_CPP" -Mdir "$WORKDIR" -Wno-fatal -O2 >/dev/null
    make -C "$WORKDIR" -f VFIR.mk >/dev/null
    "$WORKDIR/VFIR" "$IN" "$OUT" "$OUT_WIDTH"
    echo "verilator  $MODULE: $IN -> $OUT"
elif command -v iverilog >/dev/null 2>&1; then
    iverilog -g2012 -o "$WORKDIR/sim.vvp" "$TB_V" "$RTL"
    vvp "$WORKDIR/sim.vvp" "+in=$IN" "+out=$OUT" "+n=$N_IN" >/dev/null
    echo "icarus     $MODULE: $IN -> $OUT"
else
    echo "ERROR: neither verilator nor iverilog is installed" >&2
    exit 127
fi

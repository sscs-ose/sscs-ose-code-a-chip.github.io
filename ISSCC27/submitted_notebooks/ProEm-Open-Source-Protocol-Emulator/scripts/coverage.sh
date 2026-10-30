#!/bin/bash
# =============================================================================
# Project: ProEm - Open Source Protocol Emulator
# File: scripts/coverage.sh
# Type: Script: run the pin-level tests on a Verilator model and measure line and branch coverage
# Author: Paul Vincent Bezzina
# Language: Bash
# Description:
# =============================================================================
set -e
cd "$(dirname "$0")/.."
RTL=$(grep -v '^//' src/files.f | grep -v tt_um_ | tr '\n' ' ')
OUT=build/cov
VINC=$(verilator --getenv VERILATOR_ROOT)/include
mkdir -p $OUT/dat
rm -f $OUT/dat/*.dat
verilator --cc --coverage-line --coverage-user -Wno-fatal -Wno-lint -Wno-style --top-module protocol_emulator -O3 \
  --Mdir $OUT/obj $RTL > $OUT/verilate.log 2>&1
make -s -C $OUT/obj -f Vprotocol_emulator.mk -j2 > $OUT/make.log 2>&1
TESTS="t_control t_uart t_spi t_i2c t_ps2 t_ethernet t_manchester t_usb t_random t_i2c_target t_branch t_stream t_random_branch t_crc t_standards t_modes"
for t in $TESTS; do
  g++ -std=c++14 -O2 -Isim/verilator -I$OUT/obj -I$VINC -I$VINC/vltstd sim/$t.cpp $OUT/obj/libVprotocol_emulator.a $OUT/obj/libverilated.a -pthread -o $OUT/$t
done
n=0
run() { n=$((n+1)); PROEM_COV=$OUT/dat/$n.dat "$@" > $OUT/run_$n.log 2>&1 || { echo "FAIL: $*"; tail -5 $OUT/run_$n.log; }; }
for r in 16 7; do run $OUT/t_control $r; done
run $OUT/t_uart 16 40.8; run $OUT/t_uart 8 39.2
for d in 4 6 12; do run $OUT/t_spi $d; done
for d in 4 10 25; do run $OUT/t_i2c $d; done
for h in 40 12; do run $OUT/t_ps2 $h; done
for m in 50 60; do run $OUT/t_ethernet $m; done
for d in 6 10; do run $OUT/t_manchester $d; done
run $OUT/t_usb
for m in 0 1; do for s in 1 2 3 4 5 6; do run $OUT/t_random $s $m 150; done; done
for h in 60 25; do run $OUT/t_i2c_target $h; done
run $OUT/t_branch
run $OUT/t_stream
for m in 0 1; do for s in 1 2 3; do run $OUT/t_random_branch $s $m 100; done; done
run $OUT/t_crc 60
run $OUT/t_standards
for d in 3 6; do run $OUT/t_modes $d; done
verilator_coverage --write $OUT/merged.dat $OUT/dat/*.dat
rm -rf $OUT/annotated
verilator_coverage --annotate $OUT/annotated --annotate-min 1 $OUT/merged.dat > $OUT/summary.txt
cat $OUT/summary.txt

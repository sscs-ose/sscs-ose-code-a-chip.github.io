#!/bin/bash
# =============================================================================
# Project: ProEm - Open Source Protocol Emulator
# File: scripts/synth_ihp.sh
# Type: Script: synthesis to the IHP sg13cmos5l cells, area and logic depth per corner
# Author: Paul Vincent Bezzina
# Language: Bash
# Description:
# =============================================================================
set -e
cd "$(dirname "$0")/.."
PDK_ROOT=${PDK_ROOT:?set PDK_ROOT to a checkout of IHP-Open-PDK}
CORNER=${1:-typ_1p20V_25C}
LIBDIR=$PDK_ROOT/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/lib
TECH=$PDK_ROOT/ihp-sg13cmos5l/libs.tech/librelane/sg13cmos5l_stdcell
LIB=$LIBDIR/sg13cmos5l_stdcell_$CORNER.lib
RTL=$(grep -v '^//' src/files.f | tr '\n' ' ')
YOSYS=${YOSYS:-$(command -v yowasp-yosys || command -v yosys)}
PERIOD_PS=${PERIOD_PS:-20000}
OUT=build/ihp/$CORNER
mkdir -p $OUT
DONT=$(sed 's/^/-dont_use /' $TECH/synth_exclude.cells | tr '\n' ' ')
ABC="+strash;ifraig;scorr;dc2;dretime;strash;&get,-n;&dch,-f;&nf,-D,$PERIOD_PS;&put;buffer,-p;upsize,-D,$PERIOD_PS;dnsize,-D,$PERIOD_PS;topo;stime,-p"
$YOSYS -l $OUT/synth.log -p "read_liberty -lib $LIB; read_verilog -sv $RTL; synth -flatten -top tt_um_vertrex_star_proem; \
  techmap -map $TECH/mux4_map.v; techmap -map $TECH/mux2_map.v; \
  dfflibmap $DONT -liberty $LIB; abc $DONT -liberty $LIB -D $PERIOD_PS -script $ABC; \
  hilomap -singleton -hicell sg13cmos5l_tiehi L_HI -locell sg13cmos5l_tielo L_LO; opt_clean -purge; check -assert; \
  tee -o $OUT/area.txt stat -liberty $LIB; write_verilog -noattr -noexpr $OUT/netlist.v" > /dev/null
grep -E "Number of cells|Chip area" $OUT/area.txt
grep -E "Delay =" $OUT/synth.log | tail -1 | sed 's/.*Delay = *\([0-9.]*\) ps.*/longest register to register logic: \1 ps (no wires)/'
grep -E "Start-point" $OUT/synth.log | tail -1 | sed 's/^ABC: //'

#!/bin/bash
# =============================================================================
# Project: ProEm - Open Source Protocol Emulator
# File: scripts/sta.sh
# Type: Script: timing check
# Author: Paul Vincent Bezzina
# Language: Bash
# Description:
# =============================================================================
set -e
cd "$(dirname "$0")/.."
LIBERTY=${LIBERTY:?set LIBERTY to an IHP SG13G2 .lib file, e.g. sg13g2_stdcell_slow_1p08V_125C.lib}
PERIOD_PS=${PERIOD_PS:-20000}
YOSYS=${YOSYS:-$(command -v yosys || command -v yowasp-yosys)}
RTL=$(grep -v '^//' src/files.f | tr '\n' ' ')
TOP=${TOP:-protocol_emulator}
mkdir -p build
printf 'strash\ndch -f\nmap -D %s\ntopo\nbuffer -p\nupsize\ndnsize\nstime -p\n' "$PERIOD_PS" > build/sta.abc
$YOSYS -p "read_verilog -sv $RTL; synth -flatten -top $TOP; dfflibmap -liberty $LIBERTY; abc -D $PERIOD_PS -liberty $LIBERTY -script build/sta.abc; opt_clean" > build/sta.log 2>&1
grep -E "ABC: WireLoad" build/sta.log | tail -1
grep -E "ABC: Start-point" build/sta.log | tail -1

#!/bin/bash
# 쓰임: lvl.sh <a.mag.spice> <b.mag.spice> <out>
set -u
PDK_ROOT=$HOME/work/ep_dr/opensrc/pdk
$HOME/cac/env/bin/netgen -batch lvs "$1 chip_core" "$2 chip_core" $PDK_ROOT/sky130A/libs.tech/netgen/sky130A_setup.tcl $3 < /dev/null > $3.log 2>&1
echo "netgen exit=$?"; grep -E "^Final result" $3 | tail -1

#!/bin/bash
# Usage: synth_seq.sh <rtl.v> <top> [liberty]  -> netlists/<top>.v  (flat, dfxtp flops + basic cells)
set -e
here=$(cd "$(dirname "$0")" && pwd); root=$(dirname "$here"); source "$root/tools.env"
LIB=${3:-$here/basic_cells.lib}; top=$2; mkdir -p "$here/netlists"
$GS_YOSYS -q -l "$here/netlists/$top.yosys.log" -p "
read_verilog $1; synth -flatten -top $top
dfflibmap -liberty $LIB
abc -liberty $LIB
opt_clean -purge; splitnets -ports; rename -enumerate
stat -liberty $LIB
write_verilog -noattr -noexpr $here/netlists/$top.v"
grep -o 'sky130_fd_sc_hd__[a-z0-9_]*' "$here/netlists/$top.v" | sort | uniq -c | awk '{printf "%s×%s ",$2,$1}'; echo

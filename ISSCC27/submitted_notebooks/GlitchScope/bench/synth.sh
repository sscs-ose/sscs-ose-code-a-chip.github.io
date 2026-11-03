#!/bin/bash
# Usage: synth.sh <top>   -> netlists/<top>.v (SKY130 HD mapped, flat, combinational)
set -e
here=$(cd "$(dirname "$0")" && pwd); root=$(dirname "$here")
source "$root/tools.env"
LIB=${GS_LIB:-$here/basic_cells.lib}
top=$1; mkdir -p "$here/netlists"
$GS_YOSYS -q -l "$here/netlists/$top.yosys.log" -p "
read_verilog $here/rtl/adders.v $here/rtl/misc.v
hierarchy -top $top
proc; opt; techmap; opt
abc -liberty $LIB
flatten; opt_clean -purge
splitnets -ports; rename -enumerate
stat -liberty $LIB
write_verilog -noattr -noexpr $here/netlists/$top.v"
grep -E "Chip area|cells$|Number of cells" "$here/netlists/$top.yosys.log" | tail -2 | tr -s ' ' | sed "s/^/$top: /"

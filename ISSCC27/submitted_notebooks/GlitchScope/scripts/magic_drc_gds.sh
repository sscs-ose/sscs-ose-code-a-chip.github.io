#!/bin/bash
# Magic DRC (PDK sky130A.magicrc, drc(full) style, Euclidean spacing) of a GDS streamed by KLayout from the
# routed DEF (scripts/klayout_drc.sh, ORFS def2stream.py with the standard-cell GDS).
#
#   scripts/magic_drc_gds.sh <layout.gds> <top cell> <out.log>
set -euo pipefail
G=$(cd "$(dirname "$1")" && pwd)/$(basename "$1"); TOP=$2; OUT=$3
ROOT=$(cd "$(dirname "$0")/.." && pwd)
[ -f "$ROOT/tools.env" ] && set -a && . "$ROOT/tools.env" && set +a
W=$(mktemp -d)
cat > "$W/drc.tcl" <<TCL
gds readonly true
gds read $G
load $TOP
select top cell
drc euclidean on
drc style drc(full)
puts "BBOX [box values]  CHILDREN [llength [cellname list children $TOP]]"
drc check
drc catchup
puts "DRC_TOTAL [drc list count total]"
foreach {why boxes} [drc listall why] { puts "RULE [llength \$boxes] :: \$why" }
quit -noprompt
TCL
start=$(date +%s)
(cd "$W" && PDK_ROOT=$(dirname "$GS_PDK_ROOT") "$GS_MAGIC_TCL" -dnull -noconsole \
    -rcfile "$GS_PDK_ROOT/libs.tech/magic/sky130A.magicrc" drc.tcl > drc.log 2>&1) || true
{ grep -E "BBOX|DRC_TOTAL|^RULE" "$W/drc.log" || tail -5 "$W/drc.log"; echo "SECONDS $(( $(date +%s) - start ))"; } > "$OUT"
rm -rf "$W"

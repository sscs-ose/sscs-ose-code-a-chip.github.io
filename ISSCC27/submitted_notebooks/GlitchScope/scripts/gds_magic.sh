#!/bin/bash
# Routed DEF -> GDSII with Magic (SKY130A tech, standard-cell GDS from the PDK), plus a
# Magic DRC (Tcl Magic with the PDK magicrc).  NOTE: the DRC count is reported as-is; the layouts in this repository
# are not DRC-signed-off (see the notebook's limitations).
#
#   scripts/gds_magic.sh v2        -> data/layout/v2/mul16_v2.gds.gz, data/layout/v2/magic_drc.log
set -euo pipefail
V=${1:?variant}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
[ -f "$ROOT/tools.env" ] && set -a && . "$ROOT/tools.env" && set +a
PL=$GS_ORFS/flow/platforms/sky130hd; T=$GS_PDK_ROOT/libs.tech/magic/sky130A.tech
OUT=$ROOT/data/layout/$V; W=$(mktemp -d)
gunzip -c "$OUT/6_final.def.gz" > "$W/d.def"
cat > "$W/gds.cmd" <<CMD
:cif istyle sky130(vendor)
:gds readonly true
:gds rescale false
:gds read $PL/gds/sky130_fd_sc_hd.gds
:lef read $PL/lef/sky130_fd_sc_hd.tlef
:lef read $PL/lef/sky130_fd_sc_hd_merged.lef
:def read $W/d.def
:load mul16
:select top cell
:expand
:gds write $W/mul16_$V.gds
:quit -noprompt
CMD
(cd "$W" && "$GS_MAGIC" -dnull -rcfile /dev/null -T "$T" < gds.cmd > magic.log 2>&1)
gzip -c "$W/mul16_$V.gds" > "$OUT/mul16_$V.gds.gz"
# DRC with the PDK's own Magic setup (sky130A.magicrc, Euclidean spacing), Tcl-enabled Magic
cat > "$W/drc.tcl" <<TCL
gds read $W/mul16_$V.gds
load mul16
select top cell
drc euclidean on
drc style drc(full)
drc check
drc catchup
puts "DRC_TOTAL [drc list count total]"
foreach {why boxes} [drc listall why] { puts "RULE [llength \$boxes] :: \$why" }
quit -noprompt
TCL
(cd "$W" && PDK_ROOT=$(dirname "$GS_PDK_ROOT") "$GS_MAGIC_TCL" -dnull -noconsole \
    -rcfile "$GS_PDK_ROOT/libs.tech/magic/sky130A.magicrc" drc.tcl > drc.log 2>&1) || true
grep -E "DRC_TOTAL|^RULE" "$W/drc.log" > "$OUT/magic_drc.log" || true
ls -la "$OUT/mul16_$V.gds.gz"; head -3 "$OUT/magic_drc.log"
rm -rf "$W"

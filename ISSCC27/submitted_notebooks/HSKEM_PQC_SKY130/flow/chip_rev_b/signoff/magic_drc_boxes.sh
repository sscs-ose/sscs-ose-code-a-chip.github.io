#!/usr/bin/env bash
# C2 (rest): Magic DRC of HSKEM-2 revision B with the SKY130 Magic deck (drc(full), euclidean), on the GDS after the
# implant fix (the layout that passes the KLayout front-end rules). Output: per-rule counts in /root/magic_drc_revb/.
# usage: magic_drc_revb.sh [gds]
set -uo pipefail
MAGIC=/opt/eda/magic-8.3.629/install/bin/magic
PDKT=$(ls -d /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.tech/magic | head -1)
export PDK_ROOT=$(dirname $(dirname $(dirname $PDKT)))   # the magicrc loads $PDK_ROOT/sky130A/libs.tech/magic/sky130A.tech
GDS=${1:-/root/t3/feol_t3e_w1/chip_v2_final7_implantfix.gds}; TOP=${2:-trustedge_asic_core}
O=${3:-/root/magic_drc_revb}; mkdir -p $O; cd $O
cat > drc.tcl <<TCL
crashbackups stop
drc off
gds readonly true
gds read $GDS
load $TOP
select top cell
expand
drc euclidean on
drc style drc(full)
drc on
puts "MAGIC_DRC start"
drc check
drc catchup
set n [drc list count total]
puts "MAGIC_DRC total \$n"
set fh [open $O/drc_why.txt w]; set fb [open $O/drc_boxes.txt w]
foreach {why boxes} [drc listall why] { puts \$fh "[llength \$boxes]\t\$why"; foreach b \$boxes { puts \$fb "\$why\t\$b" } }
close \$fh; close \$fb
puts "MAGIC_DRC done"
quit -noprompt
TCL
/usr/bin/time -v $MAGIC -dnull -noconsole -rcfile $PDKT/sky130A.magicrc drc.tcl > magic.log 2>&1
grep -E "MAGIC_DRC|Maximum resident|Elapsed" magic.log; sort -rn drc_why.txt 2>/dev/null | head -20

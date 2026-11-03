#!/bin/sh
# Full physical verification of mag/ldo_top: Magic DRC (hierarchical), GDS export, KLayout SKY130 DRC (FEOL+BEOL+offgrid),
# Magic DRC on the flattened final GDS, extraction, Netgen LVS against mag/schematic.spice.
cd "$(dirname "$0")"
sh run.sh bash -c '
cd /w/mag
RC=/opt/pdk/sky130A/libs.tech/magic/sky130A.magicrc
magic -dnull -noconsole -rcfile $RC drc.tcl 2>&1 | grep DRCTOTAL | sed "s/DRCTOTAL/Magic DRC (hierarchical .mag):/"
magic -dnull -noconsole -rcfile $RC gds.tcl > gds.log 2>&1
klayout -b -rd input=ldo_top.gds -rd top_cell=ldo_top -rd report=klayout_drc.xml -rd thr=16 -rd feol=true -rd beol=true \
        -rd offgrid=true -r /opt/pdk/sky130A/libs.tech/klayout/drc/sky130A_mr.drc > klayout_drc.log 2>&1
python3 -c "
import xml.etree.ElementTree as ET, collections
t = ET.parse(\"klayout_drc.xml\").getroot()
c = collections.Counter(i.findtext(\"category\") for i in t.iter(\"item\"))
print(\"KLayout sky130A_mr DRC:\", sum(c.values()), dict(c))"
(cd gdsrt && magic -dnull -noconsole -rcfile $RC drc_gds.tcl 2>&1 | grep GDSFLATDRC | sed "s/GDSFLATDRC/Magic DRC (flattened final GDS):/")
magic -dnull -noconsole -rcfile $RC lvs_ext.tcl > lvs_ext.log 2>&1
netgen -batch lvs "ldo_top_lvs.spice ldo_top" "schematic.spice ldo_top" /opt/pdk/sky130A/libs.tech/netgen/sky130A_setup.tcl lvs_report.txt > netgen.log 2>&1
grep -E "Number of devices|Number of nets|Final result|Circuits match uniquely|Netlists match" lvs_report.txt | tail -5
'

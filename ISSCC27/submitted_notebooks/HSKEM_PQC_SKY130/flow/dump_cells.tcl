# Dump every placed instance of a routed design (master, bounding box) to CSV.
# env: ODB OUT
# SPDX-License-Identifier: Apache-2.0
read_db $::env(ODB)
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set fh [open $::env(OUT) w]
puts $fh "master,x0,y0,x1,y1,is_macro"
set die [$block getDieArea]
puts $fh "DIE,[expr {[$die xMin]/double($dbu)}],[expr {[$die yMin]/double($dbu)}],[expr {[$die xMax]/double($dbu)}],[expr {[$die yMax]/double($dbu)}],0"
foreach inst [$block getInsts] {
    set m [$inst getMaster]
    set b [$inst getBBox]
    set macro [expr {[$m getType] eq "BLOCK" ? 1 : 0}]
    puts $fh "[$m getName],[expr {[$b xMin]/double($dbu)}],[expr {[$b yMin]/double($dbu)}],[expr {[$b xMax]/double($dbu)}],[expr {[$b yMax]/double($dbu)}],$macro"
}
close $fh
exit

# Native floorplan rounds the origin; the frozen contract specifies a local site lattice.
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
lassign $::env(CORE_AREA) lx ly ux uy
foreach v {lx ly ux uy} {set $v [expr {round([set $v]*$dbu)}]}
set rows [$block getRows]
set site [[lindex $rows 0] getSite]
if {[$site getName] ne "unithd"} {error "Unexpected frozen placement site"}
set sw [$site getWidth]
set sh [$site getHeight]
if {($ux-$lx)%$sw || ($uy-$ly)%$sh} {error "Frozen core dimensions are not integral sites"}
foreach row $rows {odb::dbRow_destroy $row}
set columns [expr {($ux-$lx)/$sw}]
set count [expr {($uy-$ly)/$sh}]
for {set i 0} {$i<$count} {incr i} {
  set orient [expr {$i%2 ? "MX" : "R0"}]
  odb::dbRow_create $block NEBULA_ROW_$i $site $lx [expr {$ly+$i*$sh}] $orient HORIZONTAL $columns $sw
}
$block setCoreArea [odb::new_Rect $lx $ly $ux $uy]
set core [$block getCoreArea]
if {[$core xMin]!=$lx || [$core yMin]!=$ly || [$core xMax]!=$ux || [$core yMax]!=$uy} {error "Core does not equal the frozen rectangle"}
puts "FROZEN_CORE_ROWS_PASS origin=($lx,$ly) upper=($ux,$uy) rows=$count columns=$columns site=unithd"

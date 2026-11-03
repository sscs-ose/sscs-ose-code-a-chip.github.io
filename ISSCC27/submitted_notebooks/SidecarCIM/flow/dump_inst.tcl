# env ODB OUT : "name x0 y0 x1 y1 master" (um) for every instance except fill/tap/decap/phy-edge
read_db $::env(ODB)
set blk [ord::get_db_block]
set u [expr {double([$blk getDbUnitsPerMicron])}]
set f [open $::env(OUT) w]
foreach i [$blk getInsts] {
  set m [[$i getMaster] getName]
  if {[regexp {fill|FILL|tap|TAP|decap|PHY_EDGE} $m]} continue
  set bb [$i getBBox]
  puts $f "[$i getName] [expr {[$bb xMin]/$u}] [expr {[$bb yMin]/$u}] [expr {[$bb xMax]/$u}] [expr {[$bb yMax]/$u}] $m"
}
close $f

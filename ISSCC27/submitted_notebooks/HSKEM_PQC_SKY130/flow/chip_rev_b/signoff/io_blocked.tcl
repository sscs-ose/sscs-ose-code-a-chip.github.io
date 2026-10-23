# I/O pins of a chip v2 database that sit behind a macro (the macro's edge-facing side lies within
# GAP um of the die edge and the pin falls inside the macro's span along that edge), plus every macro's
# blocked edge segment, for place_pins -exclude. Inputs (env): ODB, GAP (default 120).
read_db $::env(ODB)
set block [ord::get_db_block]
set dbu [[$block getTech] getLefUnits]
set gap [expr {[info exists ::env(GAP)] ? $::env(GAP) : 120}]
set die [$block getDieArea]
set W [expr {[$die xMax] / double($dbu)}]; set H [expr {[$die yMax] / double($dbu)}]
set segs {}
foreach inst [$block getInsts] {
  if {![[$inst getMaster] isBlock]} { continue }
  set bb [$inst getBBox]
  set x0 [expr {[$bb xMin] / double($dbu)}]; set y0 [expr {[$bb yMin] / double($dbu)}]
  set x1 [expr {[$bb xMax] / double($dbu)}]; set y1 [expr {[$bb yMax] / double($dbu)}]
  if {$x0 < $gap} { lappend segs [list left $y0 $y1 [$inst getName]] }
  if {$W - $x1 < $gap} { lappend segs [list right $y0 $y1 [$inst getName]] }
  if {$y0 < $gap} { lappend segs [list bottom $x0 $x1 [$inst getName]] }
  if {$H - $y1 < $gap} { lappend segs [list top $x0 $x1 [$inst getName]] }
}
foreach s [lsort -index 1 -real $segs] { puts [format "BLOCKED_SEG %s %.1f %.1f %s" {*}$s] }
set nblk 0
foreach bt [$block getBTerms] {
  set bb [$bt getBBox]
  set x [expr {[$bb xMin] / double($dbu)}]; set y [expr {[$bb yMin] / double($dbu)}]
  set edge [expr {$x < 5 ? "left" : ($y < 5 ? "bottom" : ($x > $W - 5 ? "right" : "top"))}]
  set c [expr {($edge eq "left" || $edge eq "right") ? $y : $x}]
  foreach s $segs {
    lassign $s e lo hi name
    if {$e eq $edge && $c >= $lo && $c <= $hi} {
      incr nblk
      puts [format "BLOCKED_PIN %s %s %.1f behind %s" [$bt getName] $edge $c $name]
      break
    }
  }
}
puts "BLOCKED_PIN_COUNT $nblk of [llength [$block getBTerms]]"

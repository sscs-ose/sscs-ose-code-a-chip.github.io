# Rev C rebuild (revc2), pre-global-route hook: rev B's hook (0.13 layer adjustment, routing layers), then routing
# obstructions over the frame that the SRAM macros' LEF abstracts leave open. Every macro master obstructs met1/met2 only
# from 0.62 um inside its box and met3 only from 2.34 um inside its two edges that carry the vccd1 ring; the router used
# that frame for jogs at the ekPKE macro corner, the one spot neither rev B nor rev C closed without post-route halos.
# Here, for every placed macro: four strips on met1 and on met2 (box edge to the master's obstruction edge), and the two
# met3 strips along the ring edges. Inside the macro box, so placement is unaffected; stored in the odb, so the global
# route, the detailed route and every later session see them. Stops if a strip would cover a signal pin.
# SPDX-License-Identifier: Apache-2.0
source /mnt/d/TKVM_ATTT_2026_test/asic/orfs/pre_global_route_a3_013.tcl
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set before [llength [$block getObstructions]]
set nmacro 0; set nobs 0
foreach inst [$block getInsts] {
  set m [$inst getMaster]
  if {[$m getType] ne "BLOCK"} { continue }
  set W [$m getWidth]; set H [$m getHeight]
  # inner edge of the master's obstruction per layer, master coordinates
  foreach l {met1 met2 met3} { set in($l) {} }
  foreach b [$m getObstructions] {
    set tl [$b getTechLayer]
    if {$tl eq "NULL"} { continue }
    set l [$tl getName]
    if {![info exists in($l)]} { continue }
    if {$in($l) eq {}} { set in($l) [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]; continue }
    lassign $in($l) a0 b0 a1 b1
    set in($l) [list [expr {min($a0, [$b xMin])}] [expr {min($b0, [$b yMin])}] [expr {max($a1, [$b xMax])}] [expr {max($b1, [$b yMax])}]]
  }
  foreach l {met1 met2 met3} {
    if {$in($l) eq {}} { error "REVC2_FRAME [$m getName]: no $l obstruction" }
    lassign $in($l) a0 b0 a1 b1
    set ins($l) [list $a0 $b0 [expr {$W - $a1}] [expr {$H - $b1}]]   ;# left bottom right top, master coordinates
  }
  # no signal pin may lie in a strip: none on met1/met2 at all, none on met3 within the ring-edge strips
  lassign $ins(met3) - b3 - t3
  foreach mt [$m getMTerms] {
    if {[$mt getSigType] in {POWER GROUND}} { continue }
    foreach mp [$mt getMPins] {
      foreach g [$mp getGeometry] {
        set tl [$g getTechLayer]
        if {$tl eq "NULL"} { continue }
        set l [$tl getName]
        if {$l in {met1 met2}} { error "REVC2_FRAME [$m getName]/[$mt getName]: signal pin on $l" }
        if {$l eq "met3" && ([$g yMin] < $b3 || [$g yMax] > $H - $t3)} { error "REVC2_FRAME [$m getName]/[$mt getName]: met3 pin in a ring-edge strip" }
      }
    }
  }
  # master insets -> chip insets for the placed orientation
  set o [$inst getOrient]
  foreach l {met1 met2 met3} {
    lassign $ins($l) il ib ir it
    switch -- $o {
      R0   { set c($l) [list $il $ib $ir $it] }
      R180 { set c($l) [list $ir $it $il $ib] }
      MX   { set c($l) [list $il $it $ir $ib] }
      MY   { set c($l) [list $ir $ib $il $it] }
      default { error "REVC2_FRAME [$inst getName]: orientation $o not handled" }
    }
  }
  set bb [$inst getBBox]
  set X0 [$bb xMin]; set Y0 [$bb yMin]; set X1 [$bb xMax]; set Y1 [$bb yMax]
  foreach l {met1 met2} {
    lassign $c($l) cl cb cr ct
    set layer [$tech findLayer $l]
    odb::dbObstruction_create $block $layer $X0 $Y0 [expr {$X0 + $cl}] $Y1
    odb::dbObstruction_create $block $layer [expr {$X1 - $cr}] $Y0 $X1 $Y1
    odb::dbObstruction_create $block $layer [expr {$X0 + $cl}] $Y0 [expr {$X1 - $cr}] [expr {$Y0 + $cb}]
    odb::dbObstruction_create $block $layer [expr {$X0 + $cl}] [expr {$Y1 - $ct}] [expr {$X1 - $cr}] $Y1
    incr nobs 4
  }
  lassign $c(met3) - cb - ct
  set layer [$tech findLayer met3]
  odb::dbObstruction_create $block $layer $X0 $Y0 $X1 [expr {$Y0 + $cb}]
  odb::dbObstruction_create $block $layer $X0 [expr {$Y1 - $ct}] $X1 $Y1
  incr nobs 2
  incr nmacro
  if {[string match "*u_ekpke_pair_sram*" [$inst getName]]} {
    set dbu [$block getDefUnits]
    lassign $c(met1) cl cb cr ct
    puts [format "REVC2_FRAME ekPKE %s box (%.3f %.3f)-(%.3f %.3f) met1/met2 right strip x %.3f-%.3f, top strip y %.3f-%.3f" $o \
      [expr {double($X0)/$dbu}] [expr {double($Y0)/$dbu}] [expr {double($X1)/$dbu}] [expr {double($Y1)/$dbu}] \
      [expr {double($X1 - $cr)/$dbu}] [expr {double($X1)/$dbu}] [expr {double($Y1 - $ct)/$dbu}] [expr {double($Y1)/$dbu}]]
  }
}
puts "REVC2_FRAME macros=$nmacro obstructions_added=$nobs obstructions_before=$before obstructions_after=[llength [$block getObstructions]]"

# Targeted re-route ECO (tier-3 clone, after chip_v2/eco_ionet.tcl): a net whose detailed route keeps shorting at a
# spot the router does not leave (t3e: net2421, a 1.7 mm buffered wire that hugs the top-right corner of the ekPKE
# macro on met3 and shorts VDD there; three cleanup rounds and a routing blockage alone did not move it, because its
# global-route guide stays on that edge). For every net in CHIPV2_ECO_NETS the antenna diodes on it are removed (a
# netlist change, so the incremental global route plans the net again); CHIPV2_ROUTE_BLOCKAGE ("<layer> x0 y0 x1 y1",
# um), when given, is created first so that the new guide and the detailed route avoid the spot. Then legalization,
# the incremental global route and a detailed route from the existing routes. Antenna rounds follow separately.
# env: CHIPV2_IN, CHIPV2_OUT, CHIPV2_TAG, CHIPV2_ECO_NETS, [CHIPV2_ROUTE_BLOCKAGE], DETAILED_ROUTE_END_ITERATION
# SPDX-License-Identifier: Apache-2.0
source $::env(SCRIPTS_DIR)/load.tcl
load_design $::env(CHIPV2_IN) 5_1_grt.sdc
set_propagated_clock [all_clocks]
set tag $::env(CHIPV2_TAG)
set block [ord::get_db_block]
set dbu [[$block getTech] getLefUnits]
if {[info exists ::env(CHIPV2_ROUTE_BLOCKAGE)]} {
  lassign $::env(CHIPV2_ROUTE_BLOCKAGE) lname bx0 by0 bx1 by1
  set layer [[ord::get_db_tech] findLayer $lname]
  odb::dbObstruction_create $block $layer [expr {round($bx0*$dbu)}] [expr {round($by0*$dbu)}] [expr {round($bx1*$dbu)}] [expr {round($by1*$dbu)}]
  puts "CHIPV2_ECO=$tag routing_blockage=$lname ($bx0,$by0)-($bx1,$by1)"
}
# CHIPV2_ROUTE_BLOCKAGES: several blockages, "<layer> x0 y0 x1 y1; <layer> x0 y0 x1 y1; ..." (um): a routing halo
# around a macro edge where the macro's LEF obstruction stops short of its boundary (t3e: ekPKE top-right corner)
if {[info exists ::env(CHIPV2_ROUTE_BLOCKAGES)]} {
  foreach b [split $::env(CHIPV2_ROUTE_BLOCKAGES) ";"] {
    if {[string trim $b] eq ""} { continue }
    lassign [string trim $b] lname bx0 by0 bx1 by1
    set layer [[ord::get_db_tech] findLayer $lname]
    if {$layer eq "NULL"} { error "unknown layer $lname" }
    odb::dbObstruction_create $block $layer [expr {round($bx0*$dbu)}] [expr {round($by0*$dbu)}] [expr {round($bx1*$dbu)}] [expr {round($by1*$dbu)}]
    puts "CHIPV2_ECO=$tag routing_blockage=$lname ($bx0,$by0)-($bx1,$by1)"
  }
}
global_route -start_incremental
foreach nn $::env(CHIPV2_ECO_NETS) {
  set net [$block findNet $nn]
  if {$net eq "NULL"} { set net [$block findNet [string map {"[" "\\[" "]" "\\]"} $nn]] }
  if {$net eq "NULL"} { error "missing net $nn" }
  # CHIPV2_ECO_RIP=1: the net's detailed route is deleted, so the router routes it from scratch instead of keeping
  # its old wires (t3e x4: old wires of nets in the strip stayed inside the new halo and shorted it)
  set ripped 0
  if {[info exists ::env(CHIPV2_ECO_RIP)] && $::env(CHIPV2_ECO_RIP) == 1 && [$net getWire] ne "NULL"} {
    odb::dbWire_destroy [$net getWire]; set ripped 1
  }
  set n 0
  foreach it [$net getITerms] {
    set i [$it getInst]
    if {[string match "*diode*" [[$i getMaster] getName]]} { odb::dbInst_destroy $i; incr n }
  }
  # a net without diodes is marked changed for the incremental global route by disconnecting and reconnecting its
  # driver pin (the netlist is unchanged)
  set touched 0
  foreach it [$net getITerms] {
    if {[$it getIoType] eq "OUTPUT"} { $it disconnect; $it connect $net; incr touched; break }
  }
  puts "CHIPV2_ECO=$tag net=$nn removed_diodes=$n driver_touched=$touched ripped=$ripped remaining_iterms=[llength [$net getITerms]]"
}
detailed_placement
check_placement -verbose
global_route -end_incremental
set additional_args ""
append_env_var additional_args DETAILED_ROUTE_END_ITERATION -droute_end_iter 1
append additional_args " -verbose 1"
log_cmd detailed_route -output_drc $::env(REPORTS_DIR)/5_route_drc_${tag}.rpt \
  -output_maze $::env(RESULTS_DIR)/maze_${tag}.log {*}$additional_args -drc_report_iter_step 5
set ant [check_antennas -report_file $::env(REPORTS_DIR)/drt_antennas_${tag}.log]
puts "CHIPV2_ROUND=$tag antenna_violations_after=$ant"
if { ![design_is_routed] } { error "Design has unrouted nets." }
report_design_area
orfs_write_db $::env(RESULTS_DIR)/$::env(CHIPV2_OUT)
puts "CHIPV2_ROUND=$tag written=$::env(CHIPV2_OUT)"

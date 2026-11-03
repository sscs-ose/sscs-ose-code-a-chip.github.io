# Rev C rebuild (revc2), targeted fix after the antenna rounds, one session through `make run` (typical corner):
# (1) routing obstructions from CHIPV2_ROUTE_BLOCKAGES (26/10: met4 over the ekPKE macro's vccd1 met4 pin strip at the
#     corner, where the router kept a signal wire on the pin) - the frame obstructions of pre_grt_revc2.tcl stay;
# (2) the wires of CHIPV2_ECO_NETS ripped (diodes removed, driver re-connected so the global route redoes them);
# (3) slew / capacitance repair with the extracted parasitics of the final stage on the input (CHIPV2_SPEF), as rev B's
#     drv_spef_round_t3.tcl: the router-level DRV left 343 / 37 violations at tt after the antenna rounds;
# then legalization, incremental global route, detailed route from the existing routes, antenna check.
# env: CHIPV2_IN, CHIPV2_OUT, CHIPV2_TAG, CHIPV2_SPEF, CHIPV2_ROUTE_BLOCKAGES, CHIPV2_ECO_NETS, DETAILED_ROUTE_END_ITERATION
# SPDX-License-Identifier: Apache-2.0
source $::env(SCRIPTS_DIR)/load.tcl
load_design $::env(CHIPV2_IN) 5_1_grt.sdc
set_propagated_clock [all_clocks]
set tag $::env(CHIPV2_TAG)
set block [ord::get_db_block]
set dbu [[$block getTech] getLefUnits]
puts "CHIPV2_ECO=$tag obstructions_before=[llength [$block getObstructions]]"
foreach b [split $::env(CHIPV2_ROUTE_BLOCKAGES) ";"] {
  if {[string trim $b] eq ""} { continue }
  lassign [string trim $b] lname bx0 by0 bx1 by1
  set layer [[ord::get_db_tech] findLayer $lname]
  if {$layer eq "NULL"} { error "unknown layer $lname" }
  odb::dbObstruction_create $block $layer [expr {round($bx0*$dbu)}] [expr {round($by0*$dbu)}] [expr {round($bx1*$dbu)}] [expr {round($by1*$dbu)}]
  puts "CHIPV2_ECO=$tag routing_blockage=$lname ($bx0,$by0)-($bx1,$by1)"
}
global_route -start_incremental
foreach nn $::env(CHIPV2_ECO_NETS) {
  set net [$block findNet $nn]
  if {$net eq "NULL"} { set net [$block findNet [string map {"[" "\\[" "]" "\\]"} $nn]] }
  if {$net eq "NULL"} { error "missing net $nn" }
  set ripped 0
  if {[$net getWire] ne "NULL"} { odb::dbWire_destroy [$net getWire]; set ripped 1 }
  set n 0
  foreach it [$net getITerms] {
    set i [$it getInst]
    if {[string match "*diode*" [[$i getMaster] getName]]} { odb::dbInst_destroy $i; incr n }
  }
  set touched 0
  foreach it [$net getITerms] {
    if {[$it getIoType] eq "OUTPUT"} { $it disconnect; $it connect $net; incr touched; break }
  }
  puts "CHIPV2_ECO=$tag net=$nn removed_diodes=$n driver_touched=$touched ripped=$ripped"
}
read_spef $::env(CHIPV2_SPEF)
report_check_types -max_slew -max_capacitance -violators > $::env(REPORTS_DIR)/drv_${tag}_before.rpt
puts "CHIPV2_DRV=$tag before (extracted parasitics): [exec grep -c VIOLATED $::env(REPORTS_DIR)/drv_${tag}_before.rpt] violating pins"
repair_design -slew_margin 10 -cap_margin 10
report_check_types -max_slew -max_capacitance -violators > $::env(REPORTS_DIR)/drv_${tag}_after.rpt
puts "CHIPV2_DRV=$tag after repair_design: [exec grep -c VIOLATED $::env(REPORTS_DIR)/drv_${tag}_after.rpt] violating pins"
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

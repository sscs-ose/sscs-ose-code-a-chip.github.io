# ECO x6 of t3e (tier-3 clone), one session: (1) the routing halo of x5 at the ekPKE top-right corner is replaced by one
# whose top edge sits 0.21 um below the macro's top edge (x5 left a met1 spacing violation between the halo and a wire
# running just above the macro, where the real macro has no metal), and the nets in the last DRCs are ripped and
# routed again; (2) hold repair under the sign-off SoC I/O model (final_sta.tcl IO_MODE soc: virtual clock io_clk
# with the measured clock insertion delay, output min delay 0, input min 0.3, uncertainty 0.2) with the +-5 % cell
# derate at ff: h5 repaired hold against the SDC as written and left 9 output ports at -0.14 ns there.
# env: CHIPV2_IN, CHIPV2_OUT, CHIPV2_TAG, CHIPV2_SPEF, CHIPV2_ECO_NETS, CHIPV2_ROUTE_BLOCKAGES, CHIPV2_CLEAR_BOX
#      ("x0 y0 x1 y1": block obstructions inside it are deleted first), CHIPV2_HOLD_MARGIN, CHIPV2_HOLD_DERATE,
#      LIB_FILES (ff library), DETAILED_ROUTE_END_ITERATION
# SPDX-License-Identifier: Apache-2.0
source $::env(SCRIPTS_DIR)/load.tcl
load_design $::env(CHIPV2_IN) 5_1_grt.sdc
set_propagated_clock [all_clocks]
set tag $::env(CHIPV2_TAG)
set block [ord::get_db_block]
set dbu [[$block getTech] getLefUnits]
lassign $::env(CHIPV2_CLEAR_BOX) cx0 cy0 cx1 cy1
set cleared 0
foreach o [$block getObstructions] {
  set bb [$o getBBox]
  if {[$bb xMin] >= round($cx0*$dbu) && [$bb yMin] >= round($cy0*$dbu) && [$bb xMax] <= round($cx1*$dbu) && [$bb yMax] <= round($cy1*$dbu)} {
    odb::dbObstruction_destroy $o; incr cleared
  }
}
puts "CHIPV2_ECO=$tag cleared_blockages=$cleared"
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
set d $::env(CHIPV2_HOLD_DERATE)
set_timing_derate -cell_delay -early [expr {1.0 - $d}]
set_timing_derate -cell_delay -late [expr {1.0 + $d}]
sta::with_output_to_variable lat { report_clock_latency -clock core_clk }
if {![regexp {\n\s*([-\d.]+)\s+([-\d.]+) latency} $lat -> lmin lmax]} { error "no clock latency parsed" }
set ins [list]; set outs [list]
foreach p [all_inputs] {
  set n [get_full_name $p]
  if {[string match "spi_*" $n] || $n eq "clk_i" || $n eq "rst_ni"} { continue }
  lappend ins $p
}
foreach p [all_outputs] { if {![string match "spi_*" [get_full_name $p]]} { lappend outs $p } }
create_clock -name io_clk -period [get_property [get_clocks core_clk] period]
set_clock_latency -min $lmin [get_clocks io_clk]
set_clock_latency -max $lmax [get_clocks io_clk]
set_clock_uncertainty 0.200 [get_clocks io_clk]
set_input_delay -clock io_clk -max 2.0 $ins
set_input_delay -clock io_clk -min 0.3 $ins
set_output_delay -clock io_clk -max 2.0 $outs
set_output_delay -clock io_clk -min 0.0 $outs
puts "CHIPV2_HOLD=$tag soc io model: latency $lmin/$lmax, in [llength $ins] out [llength $outs], derate $d"
puts "CHIPV2_HOLD=$tag before"; report_worst_slack -min -digits 3; report_worst_slack -max -digits 3
repair_timing -hold -hold_margin $::env(CHIPV2_HOLD_MARGIN)
puts "CHIPV2_HOLD=$tag after"; report_worst_slack -min -digits 3; report_worst_slack -max -digits 3
unset_timing_derate
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

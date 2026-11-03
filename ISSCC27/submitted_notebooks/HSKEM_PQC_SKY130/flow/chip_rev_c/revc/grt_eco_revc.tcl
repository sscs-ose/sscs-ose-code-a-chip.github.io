# Rev C rebuild (revc2): timing repair on the global-route database, before any detailed route, so that the routed
# layout needs no post-route ECO (the post-route rounds of revc1 scattered >100 router markers and left the ekPKE corner
# stuck). Run through `make run` with LIB_FILES = the corner's Liberty and the matching macro views (revc_run_chip.sh,
# CHIPV2_MACRO_LIB_DIR). Global-route parasitics (estimate_parasitics -global_routing, as in flow_chip/grt_sta.tcl), the
# sign-off SoC I/O model of final_sta.tcl / eco_hold_io_t3.tcl, a +-d cell-delay derate, then
#   CHIPV2_GRT_MODE=setup: repair_timing -setup -setup_margin m     (slow corner)
#   CHIPV2_GRT_MODE=hold:  repair_timing -hold -hold_margin m       (fast corner)
#   CHIPV2_GRT_MODE=report: slacks only, nothing written
# followed by legalization and the incremental global route of the changed nets; writes CHIPV2_OUT (guides in the odb).
# env: CHIPV2_IN, CHIPV2_OUT, CHIPV2_TAG, CHIPV2_GRT_MODE, CHIPV2_DERATE, CHIPV2_MARGIN
# SPDX-License-Identifier: Apache-2.0
source $::env(SCRIPTS_DIR)/load.tcl
load_design $::env(CHIPV2_IN) 5_1_grt.sdc
set tag $::env(CHIPV2_TAG)
set mode $::env(CHIPV2_GRT_MODE)
source /mnt/d/TKVM_ATTT_2026_test/asic/orfs/pre_global_route_a3_013.tcl
set_placement_padding -global -left $::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT) -right $::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT)
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
set d $::env(CHIPV2_DERATE)
set_timing_derate -cell_delay -early [expr {1.0 - $d}]
set_timing_derate -cell_delay -late [expr {1.0 + $d}]
# sign-off SoC I/O model (final_sta.tcl IO_MODE soc)
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
proc slacks {when} {
  global tag
  puts "CHIPV2_GRT=$tag $when setup_wns [sta::format_time [sta::worst_slack_cmd max] 3] hold_wns [sta::format_time [sta::worst_slack_cmd min] 3] setup_viol [sta::endpoint_violation_count max] hold_viol [sta::endpoint_violation_count min]"
}
puts "CHIPV2_GRT=$tag mode $mode derate $d soc io model: latency $lmin/$lmax, in [llength $ins] out [llength $outs]"
slacks before
if {$mode eq "report"} {
  report_checks -path_delay min -group_path_count 5 -endpoint_path_count 1 -format end
  report_checks -path_delay max -group_path_count 5 -endpoint_path_count 1 -format end
  report_checks -path_delay min -fields {slew cap fanout} -digits 3
  exit
}
global_route -start_incremental
if {$mode eq "setup"} {
  repair_timing -setup -setup_margin $::env(CHIPV2_MARGIN) -verbose
} elseif {$mode eq "hold"} {
  # CHIPV2_REPAIR_ARGS: extra repair_timing options (e.g. -max_passes), for endpoints that one default pass leaves
  set extra [expr {[info exists ::env(CHIPV2_REPAIR_ARGS)] ? $::env(CHIPV2_REPAIR_ARGS) : ""}]
  repair_timing -hold -hold_margin $::env(CHIPV2_MARGIN) -verbose {*}$extra
} elseif {$mode eq "insbuf"} {
  # CHIPV2_INSBUF_PINS: load pins (inst/pin) that get a delay cell in front of them, placed at the pin; for the few hold
  # endpoints repair_timing leaves (direct flop-to-flop nets, an output-buffer input), all with tens of ns of setup slack
  set block [ord::get_db_block]
  # insert_buffer legalizes the new cell through the detailed placer, whose grid exists only after a first run
  # (without it: SIGFPE in dpl::Opendp::pointOffMacro); the placement is already legal, so this run moves nothing
  detailed_placement
  set k 0
  foreach p $::env(CHIPV2_INSBUF_PINS) {
    set pin [get_pins [string map {"[" "\\[" "]" "\\]"} $p]]
    if {[llength $pin] != 1} { error "CHIPV2_GRT=$tag no single pin $p" }
    set it [sta::sta_to_db_pin $pin]
    set net [[$it getNet] getName]
    lassign [$it getAvgXY] ok x y
    set dbu [$block getDefUnits]
    insert_buffer -buffer_cell $::env(CHIPV2_INSBUF_CELL) -net $net -load_pins $pin \
      -location [list [expr {double($x) / $dbu}] [expr {double($y) / $dbu}]] -buffer_name revc2_holddly_$k
    puts "CHIPV2_GRT=$tag inserted revc2_holddly_$k ($::env(CHIPV2_INSBUF_CELL)) on net $net before $p"
    incr k
  }
} else {
  error "unknown CHIPV2_GRT_MODE $mode"
}
detailed_placement
check_placement -verbose
global_route -end_incremental -congestion_report_file $::env(REPORTS_DIR)/congestion_grt_eco_${tag}.rpt
estimate_parasitics -global_routing
slacks after
unset_timing_derate
orfs_write_db $::env(RESULTS_DIR)/$::env(CHIPV2_OUT)
puts "CHIPV2_GRT=$tag written=$::env(CHIPV2_OUT)"

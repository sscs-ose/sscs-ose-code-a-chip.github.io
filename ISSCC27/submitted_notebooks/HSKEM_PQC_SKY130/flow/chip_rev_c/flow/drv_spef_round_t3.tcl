# Post-route DRV round of chip v2 with the extracted parasitics, run through `make run`: the resizer repairs
# the slew and capacitance violations that only the extracted parasitics show (estimated placement and
# global-route parasitics saw one; the RC extraction of the final stage saw 203 violating pins), then
# legalization, global route of the changed nets and a detailed route from the existing routes.
# env: CHIPV2_IN, CHIPV2_OUT (odb names in RESULTS_DIR), CHIPV2_TAG, CHIPV2_SPEF (the SPEF of the final
#      stage run on CHIPV2_IN), DETAILED_ROUTE_END_ITERATION
source $::env(SCRIPTS_DIR)/load.tcl
load_design $::env(CHIPV2_IN) 5_1_grt.sdc
set_propagated_clock [all_clocks]
set tag $::env(CHIPV2_TAG)
global_route -start_incremental
read_spef $::env(CHIPV2_SPEF)
report_check_types -max_slew -max_capacitance -violators > $::env(REPORTS_DIR)/drv_${tag}_before.rpt
puts "CHIPV2_DRV=$tag before (extracted parasitics): [exec grep -c VIOLATED $::env(REPORTS_DIR)/drv_${tag}_before.rpt] violating pins"
repair_design -slew_margin 10 -cap_margin 10
report_check_types -max_slew -max_capacitance -violators > $::env(REPORTS_DIR)/drv_${tag}_after.rpt
puts "CHIPV2_DRV=$tag after repair_design: [exec grep -c VIOLATED $::env(REPORTS_DIR)/drv_${tag}_after.rpt] violating pins"
if {[info exists ::env(CHIPV2_HOLD_MARGIN)]} {
  # final #4 (from a5r) showed hold -0.15 ns on an input-port path with the extracted parasitics; new hold
  # buffers have no extracted wire, so their delay is underestimated, which is the safe side for hold
  puts "CHIPV2_HOLD=$tag before"; report_worst_slack -min -digits 3
  # (tier-3 clone) CHIPV2_HOLD_DERATE: repair under the same +-d cell-delay derate as the sign-off STA, with a small
  # margin, instead of a large plain margin (0.2 ns at ff found 18,944 endpoints and inserted 19,434 buffers, h1)
  if {[info exists ::env(CHIPV2_HOLD_DERATE)]} {
    set_timing_derate -cell_delay -early [expr {1.0 - $::env(CHIPV2_HOLD_DERATE)}]
    set_timing_derate -cell_delay -late [expr {1.0 + $::env(CHIPV2_HOLD_DERATE)}]
    puts "CHIPV2_HOLD=$tag derate $::env(CHIPV2_HOLD_DERATE)"; report_worst_slack -min -digits 3
  }
  repair_timing -hold -hold_margin $::env(CHIPV2_HOLD_MARGIN)
  if {[info exists ::env(CHIPV2_HOLD_DERATE)]} { unset_timing_derate }
  puts "CHIPV2_HOLD=$tag after"; report_worst_slack -min -digits 3; report_worst_slack -max -digits 3
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

# Tier-3 clone: ONE session from the global-route database: main detailed route, then the antenna rounds in the same
# process (diodes, detailed_route again), writing a checkpoint odb after the main route and after every round.
# Reloading a routed odb loses the access point of one pin (DRT-1231, t3e), so nothing is reloaded; a killed session
# still leaves the last checkpoint. env: CHIPV2_TAG, CHIPV2_MAX_ANT_ROUNDS (default 8), DETAILED_ROUTE_END_ITERATION
source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_1_grt.odb 5_1_grt.sdc
set_propagated_clock [all_clocks]
set tag $::env(CHIPV2_TAG)

set additional_args ""
append_env_var additional_args dbProcessNode -db_process_node 1
append_env_var additional_args OR_SEED -or_seed 1
append_env_var additional_args OR_K -or_k 1
append_env_var additional_args VIA_IN_PIN_MIN_LAYER -via_in_pin_bottom_layer 1
append_env_var additional_args VIA_IN_PIN_MAX_LAYER -via_in_pin_top_layer 1
append_env_var additional_args DISABLE_VIA_GEN -disable_via_gen 0
append_env_var additional_args REPAIR_PDN_VIA_LAYER -repair_pdn_vias 1
append_env_var additional_args DETAILED_ROUTE_END_ITERATION -droute_end_iter 1
append additional_args " -verbose 1"

proc route {name} {
  global additional_args tag
  log_cmd detailed_route -output_drc $::env(REPORTS_DIR)/5_route_drc_${tag}_${name}.rpt \
    -output_maze $::env(RESULTS_DIR)/maze_${tag}_${name}.log {*}$additional_args -drc_report_iter_step 5
}
route main
set n [check_antennas -report_file $::env(REPORTS_DIR)/drt_antennas_${tag}_main.log]
puts "CHIPV2_FULL=$tag stage=main antenna_nets=$n"
orfs_write_db $::env(RESULTS_DIR)/5_2_route_${tag}_main.odb
puts "CHIPV2_FULL=$tag checkpoint=5_2_route_${tag}_main.odb"
set max [expr {[info exists ::env(CHIPV2_MAX_ANT_ROUNDS)] ? $::env(CHIPV2_MAX_ANT_ROUNDS) : 8}]
for {set k 1} {$n > 0 && $k <= $max} {incr k} {
  set ins [repair_antennas]
  puts "CHIPV2_FULL=$tag round=$k diodes_inserted=$ins"
  route a$k
  set n [check_antennas -report_file $::env(REPORTS_DIR)/drt_antennas_${tag}_a$k.log]
  puts "CHIPV2_FULL=$tag stage=a$k antenna_nets=$n"
  orfs_write_db $::env(RESULTS_DIR)/5_2_route_${tag}_a$k.odb
  puts "CHIPV2_FULL=$tag checkpoint=5_2_route_${tag}_a$k.odb"
}
if { ![design_is_routed] } { error "Design has unrouted nets." }
report_design_area
orfs_write_db $::env(RESULTS_DIR)/$::env(CHIPV2_OUT)
puts "CHIPV2_FULL=$tag written=$::env(CHIPV2_OUT) antenna_nets=$n"

# STA of the global-route database at one corner with global-route parasitics. env: RUN (results dir) CORNER OUT
set R $::env(RUN)
set P /opt/eda/orfs-6101364b/flow/platforms/sky130hd
set L [lindex [glob /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__$::env(CORNER).lib] 0]
read_liberty $L
set MLD [expr {[info exists ::env(MACRO_LIB_DIR)] ? $::env(MACRO_LIB_DIR) : "/mnt/d/TKVM_ATTT_2026_test/report/a2_macro_link_smoke/run.rjfysF/derived_liberty"}]
foreach f [glob $MLD/*.physical.lib] { read_liberty $f }
puts "RESULT macro_views $MLD"
read_db $R/5_1_grt.odb
read_sdc $R/5_1_grt.sdc
source $P/setRC.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
puts "RESULT setup_wns [sta::format_time [sta::worst_slack_cmd max] 3]"
puts "RESULT hold_wns [sta::format_time [sta::worst_slack_cmd min] 3]"
puts "RESULT setup_violating_endpoints [sta::endpoint_violation_count max]"
puts "RESULT hold_violating_endpoints [sta::endpoint_violation_count min]"
puts "SECTION SUMMARY"
report_checks -path_delay max -group_path_count 1500 -endpoint_path_count 1 -unique_paths_to_endpoint -slack_max 0 -format summary
puts "SECTION END"
exit

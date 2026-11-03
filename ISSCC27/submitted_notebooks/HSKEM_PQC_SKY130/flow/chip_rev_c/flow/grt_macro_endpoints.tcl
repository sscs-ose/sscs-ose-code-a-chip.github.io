# Every endpoint reached from each SRAM macro's dout with setup slack below SLACK_MAX (default 4 ns), not masked by other
# sources: one report per macro, worst path per endpoint. env: RUN CORNER [SLACK_MAX]
# SPDX-License-Identifier: Apache-2.0
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
set smax [expr {[info exists ::env(SLACK_MAX)] ? $::env(SLACK_MAX) : 4.0}]
foreach c [all_registers -cells] {
  if {![string match "sky130_sram*" [get_property $c ref_name]]} continue
  puts "SECTION [get_full_name $c]"
  report_checks -path_delay max -from $c -group_path_count 3000 -endpoint_path_count 1 -unique_paths_to_endpoint -slack_max $smax -format end
}
puts "SECTION END"
exit
